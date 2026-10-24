// Noyau des programmes vtx traduits en code natif (« vtx traduire ») : la mémoire du SPU, les entrées et sorties,
// les fichiers, et les opérations un peu longues. Ce fichier est recopié en tête de chaque traduction ; la fonction
// « programme » qui suit est le programme vtx lui-même, une branche par bloc d'instructions.
// Même sémantique que la machine Rust (vtx-spu) et que vtx.py.
#![allow(unused_mut, unused_variables, unused_assignments, unreachable_code, unused_parens, dead_code,
         clippy::all, non_snake_case, unused_imports)]
use std::fs;
use std::io::Write;

const MASK: u64 = 0xFFFF_FFFF;
const ADR: u32 = 0x00FF_FFFF;
const ETAGE: usize = 1 << 24;
const PILE_HAUT: u32 = 0x7F_FFFF;

/// Mémoire : quatre étages de 2^24 mots, en pages de 65 536 mots créées à la première écriture non nulle (lire une
/// page jamais écrite rend 0 sans rien réserver : un petit programme ne prend que quelques pages, pas 256 Mo).
/// Chaque étage regarde le cube de sa fréquence (0 au départ) : accorder un étage sur une autre fréquence range ses
/// 256 pages sous l'ancienne fréquence et sort celles du cube demandé (les autres cubes gardent leur contenu) ; les
/// cubes s'additionnent ainsi sans changer la taille des mots. En mode corpus, la liste des cases écrites permet de
/// rendre l'état final et de remettre la mémoire à zéro entre deux programmes. La mémoire est partagée par les
/// cylindres (fils d'exécution) qui jouent ensemble les tâches d'une même mesure : le compilateur a prouvé qu'elles
/// n'écrivent pas les mêmes cases, chaque fil a sa propre zone de pile.
struct Memoire {
    // l'étage 0 (le code et la pile, lu à chaque instruction) d'un seul bloc ; les étages 1 à 3 en pages
    base0: *mut u32,
    pages: Box<[std::sync::atomic::AtomicPtr<u32>; 4 * ETAGE / PAGE]>,
    cubes: std::sync::Mutex<std::collections::HashMap<(u32, u32), Vec<*mut u32>>>,
    frequences: [std::sync::atomic::AtomicU32; 4],
    ecrites: std::cell::UnsafeCell<Vec<u32>>,
    suivre: bool,
}

const PAGE: usize = 1 << 16;

unsafe impl Sync for Memoire {}
unsafe impl Send for Memoire {}

fn page_neuve() -> *mut u32 {
    Box::into_raw(vec![0u32; PAGE].into_boxed_slice()) as *mut u32
}

/// La page nulle, partagée : toute page jamais écrite la désigne, une lecture n'a donc rien à vérifier ; la première
/// écriture non nulle remplace ce pointeur par une vraie page.
fn page_nulle() -> *mut u32 {
    static NULLE: std::sync::OnceLock<usize> = std::sync::OnceLock::new();
    *NULLE.get_or_init(|| page_neuve() as usize) as *mut u32
}

fn rendre_page(p: *mut u32) {
    if !p.is_null() && p != page_nulle() {
        unsafe { drop(Box::from_raw(std::ptr::slice_from_raw_parts_mut(p, PAGE))) };
    }
}

impl Memoire {
    fn new(suivre: bool) -> Self {
        let base0 = unsafe { std::alloc::alloc_zeroed(std::alloc::Layout::array::<u32>(ETAGE).unwrap()) as *mut u32 };
        assert!(!base0.is_null(), "mémoire insuffisante");
        Memoire {
            base0,
            pages: Box::new(std::array::from_fn(|_| std::sync::atomic::AtomicPtr::new(page_nulle()))),
            cubes: std::sync::Mutex::new(std::collections::HashMap::new()),
            frequences: Default::default(),
            ecrites: std::cell::UnsafeCell::new(Vec::new()),
            suivre,
        }
    }
    #[inline(always)]
    fn lit_i(&self, i: usize) -> u32 {
        if i < ETAGE {
            return unsafe { *self.base0.add(i) };
        }
        // l'indice tient toujours dans la table (i < 2^26) : pas de contrôle de bornes
        unsafe { *self.pages[(i >> 16) & (4 * ETAGE / PAGE - 1)].load(std::sync::atomic::Ordering::Acquire).add(i & (PAGE - 1)) }
    }
    #[inline(always)]
    fn ecrit_i(&self, i: usize, v: u32) {
        use std::sync::atomic::Ordering::{AcqRel, Acquire};
        if i < ETAGE {
            unsafe { *self.base0.add(i) = v };
            return;
        }
        let case = &self.pages[(i >> 16) & (4 * ETAGE / PAGE - 1)];
        let mut p = case.load(Acquire);
        let nulle = page_nulle();
        if p == nulle {
            if v == 0 {
                return;
            }
            let neuve = page_neuve();
            p = match case.compare_exchange(nulle, neuve, AcqRel, Acquire) {
                Ok(_) => neuve,
                Err(autre) => {
                    rendre_page(neuve);
                    autre
                }
            };
        }
        unsafe { *p.add(i & (PAGE - 1)) = v };
    }
    fn effacer(&mut self) {
        let ec = std::mem::take(self.ecrites.get_mut());
        for &i in ec.iter() {
            self.ecrit_i(i as usize, 0);
        }
    }
    #[inline(always)]
    fn lit(&self, e: u32, a: u32) -> u32 {
        self.lit_i(((e as usize & 3) << 24) | (a & ADR) as usize)
    }
    #[inline(always)]
    fn ecrit(&self, e: u32, a: u32, v: u32) {
        let i = ((e as usize & 3) << 24) | (a & ADR) as usize;
        if self.suivre {
            unsafe { (*self.ecrites.get()).push(i as u32) };
        }
        self.ecrit_i(i, v);
    }
    fn etat(&mut self) -> Vec<(u32, u32)> {
        let mut ec = std::mem::take(self.ecrites.get_mut());
        ec.sort_unstable();
        ec.dedup();
        let r = ec.iter().filter(|&&i| i as usize >= ETAGE && self.lit_i(i as usize) != 0).map(|&i| (i, self.lit_i(i as usize))).collect();
        *self.ecrites.get_mut() = ec;
        r
    }
    /// L'étage e regarde désormais le cube de fréquence f (rend l'ancienne fréquence).
    fn accorder(&self, e: u32, f: u32) -> u32 {
        use std::sync::atomic::Ordering::{AcqRel, Release};
        let e = e & 3;
        if e == 0 {
            // l'étage 0 porte le code et la pile : il ne change pas de cube
            return 0xFFFF_FFFF;
        }
        let ancienne = self.frequences[e as usize].swap(f, AcqRel);
        if ancienne != f {
            let mut cubes = self.cubes.lock().unwrap();
            let debut = e as usize * (ETAGE / PAGE);
            let nulle = page_nulle();
            let rangees: Vec<*mut u32> = (0..ETAGE / PAGE).map(|k| self.pages[debut + k].swap(nulle, AcqRel)).collect();
            if rangees.iter().any(|&p| p != nulle) {
                cubes.insert((e, ancienne), rangees);
            }
            if let Some(v) = cubes.remove(&(e, f)) {
                for (k, p) in v.into_iter().enumerate() {
                    self.pages[debut + k].store(p, Release);
                }
            }
        }
        ancienne
    }
    fn frequence(&self, e: u32) -> u32 {
        self.frequences[(e & 3) as usize].load(std::sync::atomic::Ordering::Acquire)
    }
    /// Les pages réellement prises (toutes fréquences) : pour mesurer ce que coûte un programme.
    #[allow(dead_code)]
    fn pages_prises(&self) -> usize {
        let nulle = page_nulle();
        let actives = self.pages.iter().filter(|p| p.load(std::sync::atomic::Ordering::Acquire) != nulle).count();
        let rangees: usize = self.cubes.lock().unwrap().values().map(|v| v.iter().filter(|&&p| p != nulle).count()).sum();
        actives + rangees
    }
}

impl Drop for Memoire {
    fn drop(&mut self) {
        unsafe { std::alloc::dealloc(self.base0 as *mut u8, std::alloc::Layout::array::<u32>(ETAGE).unwrap()) };
        for p in self.pages.iter() {
            rendre_page(p.load(std::sync::atomic::Ordering::Acquire));
        }
        for v in self.cubes.lock().unwrap().values() {
            for &p in v {
                rendre_page(p);
            }
        }
    }
}

#[inline(always)]
fn f(w: u32) -> f32 {
    f32::from_bits(w)
}

#[inline(always)]
fn fb(v: f32) -> u32 {
    if v.is_nan() { 0x7FC0_0000 } else { v.to_bits() }
}

/// Flottants de 64 bits : une paire de registres (Rn, Rn+3), mot bas puis mot haut ; NaN unique 0x7FF8000000000000.
#[inline(always)]
fn d64(lo: u32, hi: u32) -> f64 {
    f64::from_bits(((hi as u64) << 32) | lo as u64)
}

#[inline(always)]
fn db(v: f64) -> u64 {
    if v.is_nan() { 0x7FF8_0000_0000_0000 } else { v.to_bits() }
}

#[inline(always)]
fn dot(x: u32, y: u32) -> u64 {
    ((x >> 24) as u64) * ((y >> 24) as u64)
        + (((x >> 16) & 255) as u64) * (((y >> 16) & 255) as u64)
        + (((x >> 8) & 255) as u64) * (((y >> 8) & 255) as u64)
        + ((x & 255) as u64) * ((y & 255) as u64)
}

fn quits(a: u32, b: u32, op: u32) -> u32 {
    let mut r = 0u32;
    for k in 0..16 {
        let x = (a >> (2 * k)) & 3;
        let y = (b >> (2 * k)) & 3;
        let v = match op {
            0x10 => x.min(y),
            0x11 => x.max(y),
            _ => (x + y) & 3,
        };
        r |= v << (2 * k);
    }
    r
}

struct Fichier {
    lecture: bool,
    car: Vec<u32>,
    pos: usize,
    chemin: std::path::PathBuf,
}

type Fichiers = std::sync::Arc<std::sync::Mutex<std::collections::HashMap<u32, Fichier>>>;

/// Entrées, sorties, console et fichiers d'un programme (ou d'une tâche jouée sur un autre cylindre).
struct Es {
    entrees: std::sync::Arc<Vec<u32>>,
    ie: usize,
    sorties: Vec<u32>,
    texte: Vec<u32>,
    fichiers: Fichiers,
    dossier: Option<std::path::PathBuf>,
    /// le clavier se lit (programme lancé par vtx) ; faux pour le corpus de conformité : rien à lire, comme l'interprète
    clavier: bool,
}

impl Es {
    fn new(entrees: Vec<u32>, dossier: Option<std::path::PathBuf>) -> Self {
        Es { entrees: std::sync::Arc::new(entrees), ie: 0, sorties: Vec::new(), texte: Vec::new(),
             fichiers: Default::default(), dossier, clavier: true }
    }
    /// Pour une tâche sur un autre cylindre : mêmes entrées et fichiers, sorties à part.
    fn fil(&self) -> Self {
        Es { entrees: self.entrees.clone(), ie: self.ie, sorties: Vec::new(), texte: Vec::new(),
             fichiers: self.fichiers.clone(), dossier: self.dossier.clone(), clavier: self.clavier }
    }
    #[inline(always)]
    fn entree(&mut self) -> u32 {
        if self.ie < self.entrees.len() {
            self.ie += 1;
            self.entrees[self.ie - 1]
        } else {
            0
        }
    }
    fn entc(&mut self, canal: u32) -> u32 {
        match canal {
            0 => self.entree(),
            1 if !self.clavier => 0xFFFF_FFFF,
            1 => {
                // le clavier : le texte en attente est montré d'abord (la question avant la réponse)
                use std::io::{Read, Write};
                let mut o = std::io::stdout();
                if !self.texte.is_empty() {
                    let t: String = self.texte.iter().filter_map(|&v| char::from_u32(v & 0x1F_FFFF)).collect();
                    let _ = write!(o, "{}", t);
                    self.texte.clear();
                }
                let _ = o.flush();
                let mut entree = std::io::stdin().lock();
                let mut b = [0u8; 4];
                if entree.read(&mut b[..1]).unwrap_or(0) == 0 {
                    return 0xFFFF_FFFF;
                }
                let n = match b[0] { 0x00..=0x7F => 1, 0xC0..=0xDF => 2, 0xE0..=0xEF => 3, _ => 4 };
                for k in 1..n {
                    if entree.read(&mut b[k..k + 1]).unwrap_or(0) == 0 {
                        return 0xFFFF_FFFF;
                    }
                }
                std::str::from_utf8(&b[..n]).ok().and_then(|s| s.chars().next()).map(|c| c as u32).unwrap_or(0xFFFD)
            }
            k => match self.fichiers.lock().unwrap().get_mut(&k) {
                Some(fi) if fi.lecture && fi.pos < fi.car.len() => {
                    fi.pos += 1;
                    fi.car[fi.pos - 1]
                }
                _ => 0xFFFF_FFFF,
            },
        }
    }
    fn sorc(&mut self, v: u32, canal: u32) {
        match canal {
            0 => self.sorties.push(v),
            1 => self.texte.push(v),
            k => {
                if let Some(fi) = self.fichiers.lock().unwrap().get_mut(&k) {
                    if !fi.lecture {
                        fi.car.push(v);
                    }
                }
            }
        }
    }
    fn sys(&mut self, mem: &Memoire, service: u32, arg: u32) -> u32 {
        let mut fichiers = self.fichiers.lock().unwrap();
        match service {
            1 | 2 => match &self.dossier {
                None => 0xFFFF_FFFF,
                Some(d) => {
                    let chemin = d.join(texte_memoire(mem, arg));
                    let canal = fichiers.keys().copied().max().unwrap_or(1).max(1) + 1;
                    if service == 1 {
                        match fs::read_to_string(&chemin) {
                            Ok(t) => {
                                fichiers.insert(canal, Fichier { lecture: true, car: t.chars().map(|c| c as u32).collect(), pos: 0, chemin });
                                canal
                            }
                            Err(_) => 0xFFFF_FFFF,
                        }
                    } else {
                        fichiers.insert(canal, Fichier { lecture: false, car: Vec::new(), pos: 0, chemin });
                        canal
                    }
                }
            },
            3 => match fichiers.remove(&arg) {
                None => 0xFFFF_FFFF,
                Some(fi) => {
                    if !fi.lecture {
                        let t: String = fi.car.iter().filter_map(|&v| char::from_u32(v & 0x1F_FFFF)).collect();
                        if fi.chemin.file_name().map(|n| n == "voix:").unwrap_or(false) {
                            // le canal « voix: » : le texte est dit par la synthèse vocale de la machine hôte
                            parler_hote(&t);
                        } else {
                            let _ = fs::write(&fi.chemin, t);
                        }
                    }
                    0
                }
            },
            5 => bruit_hote(),
            8 => mem.accorder(arg & 3, arg >> 2),
            10 => {
                eprintln!("erreur : mémoire pleine : le tas ne peut plus grandir, même après avoir ramassé les miettes");
                std::process::exit(1);
            }
            9 => mem.frequence(arg & 3),
            6 | 7 => match &self.dossier {
                None => 0xFFFF_FFFF,
                Some(d) => {
                    let chemin = d.join(texte_memoire(mem, mem.lit(3, 14_680_060)));
                    let (a, n) = (mem.lit(3, 14_680_061), mem.lit(3, 14_680_062));
                    let (e, o) = ((a >> 24) & 3, a & ADR);
                    if service == 6 {
                        let mut b = Vec::with_capacity(n as usize * 4);
                        for i in 0..n {
                            b.extend_from_slice(&mem.lit(e, o.wrapping_add(i)).to_le_bytes());
                        }
                        fs::write(&chemin, b).map(|_| n).unwrap_or(0xFFFF_FFFF)
                    } else {
                        match fs::read(&chemin) {
                            Ok(b) => {
                                let k = (b.len() / 4).min(n as usize);
                                for i in 0..k {
                                    mem.ecrit(e, o.wrapping_add(i as u32), u32::from_le_bytes([b[4 * i], b[4 * i + 1], b[4 * i + 2], b[4 * i + 3]]));
                                }
                                k as u32
                            }
                            Err(_) => 0xFFFF_FFFF,
                        }
                    }
                }
            },
            4 => match fichiers.get(&arg) {
                Some(fi) if fi.lecture && fi.pos < fi.car.len() => 0,
                _ => 1,
            },
            _ => 0xFFFF_FFFF,
        }
    }
}

/// Dire un texte à voix haute : la voix de Windows (System.Speech, en français si une voix française est installée) ;
/// ailleurs espeak-ng ou espeak s'il est là ; sinon rien. L'appel attend la fin de la phrase.
fn parler_hote(t: &str) {
    if t.trim().is_empty() {
        return;
    }
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        let script = "Add-Type -AssemblyName System.Speech; $v = New-Object System.Speech.Synthesis.SpeechSynthesizer; \
            try { $v.SelectVoiceByHints('NotSet', 'NotSet', 0, [Globalization.CultureInfo]'fr-FR') } catch {}; $v.Speak($env:VTX_VOIX)";
        let _ = std::process::Command::new("powershell").args(["-NoProfile", "-NonInteractive", "-Command", script])
            .env("VTX_VOIX", t).creation_flags(0x0800_0000).status();
    }
    #[cfg(not(windows))]
    {
        for prog in ["espeak-ng", "espeak"] {
            if std::process::Command::new(prog).args(["-v", "fr", t]).stdout(std::process::Stdio::null())
                .stderr(std::process::Stdio::null()).status().is_ok() {
                return;
            }
        }
    }
}

fn texte_memoire(mem: &Memoire, adr: u32) -> String {
    let (e, a) = ((adr >> 24) & 3, adr & ADR);
    let n = mem.lit(e, a).min(4096);
    (0..n).filter_map(|i| char::from_u32(mem.lit(e, a.wrapping_add(1 + i)) & 0x1F_FFFF)).collect()
}

fn gemv(mem: &Memoire, sp: u32) {
    let lit0 = |t: u32| mem.lit(0, sp.wrapping_add(4 - t));
    let (n, w_, qb, kb, ob) = (lit0(0), lit0(1), lit0(2), lit0(3), lit0(4));
    let q: Vec<u32> = (0..w_).map(|j| mem.lit(2, qb.wrapping_add(j))).collect();
    for i in 0..n {
        let mut s: u64 = 0;
        for j in 0..w_ {
            let adr = (kb as u64 + i as u64 * w_ as u64 + j as u64) as u32;
            s += dot(q[j as usize], mem.lit(2, adr));
        }
        mem.ecrit(2, ob.wrapping_add(i), s as u32);
    }
}

fn nombres(s: &str) -> Vec<u32> {
    s.split(',').filter(|t| !t.trim().is_empty()).map(|t| t.trim().parse::<u64>().expect("nombre attendu") as u32).collect()
}

fn charger(mem: &mut Memoire, mots: &[u32]) {
    for (i, &w) in mots.iter().enumerate() {
        mem.ecrit(0, i as u32, w);
    }
}

/// Registres d'un fil d'exécution.
#[derive(Clone)]
struct Regs {
    r: [u32; 16],
    pc: u32,
    z: bool,
    c: bool,
}

/// La table des accords produite par le compilateur : pour chaque accord, son adresse de fin et ses mesures (tâches :
/// adresse de début, adresse de fin).
struct Accord {
    fin: u32,
    mesures: Vec<Vec<(u32, u32)>>,
}

struct Partition {
    accords: Vec<Accord>,
    cylindres: usize,
}

fn lire_partition(t: &[u32], cylindres: usize) -> Partition {
    let mut it = t.iter().copied();
    let n = it.next().unwrap_or(0);
    let mut accords = Vec::new();
    for _ in 0..n {
        let _debut = it.next().unwrap();
        let fin = it.next().unwrap();
        let nm = it.next().unwrap();
        let mut mesures = Vec::new();
        for _ in 0..nm {
            let nt = it.next().unwrap();
            mesures.push((0..nt).map(|_| (it.next().unwrap(), it.next().unwrap())).collect());
        }
        accords.push(Accord { fin, mesures });
    }
    Partition { accords, cylindres }
}

type Prog = fn(&Memoire, &mut Es, u64, &mut Regs, u32, Option<&Partition>, u32) -> Result<u64, String>;

/// Joue un accord : mesure après mesure ; les tâches d'une mesure sur plusieurs cylindres quand il y en a plusieurs.
/// Même règle que la machine Rust interprétée : chaque fil reçoit une copie du cadre courant dans sa propre zone de pile.
fn jouer_accord(prog: Prog, mem: &Memoire, es: &mut Es, et: &mut Regs, numero: u32, max_pas: u64, part: &Partition) -> Result<u64, String> {
    let ac = &part.accords[(numero - 1) as usize];
    let mut pas = 0u64;
    for mesure in &ac.mesures {
        if mesure.len() == 1 || part.cylindres <= 1 {
            for &(d, f) in mesure {
                et.pc = d;
                pas += prog(mem, es, max_pas, et, f, Some(part), numero)?;
            }
            continue;
        }
        let suivante = std::sync::atomic::AtomicUsize::new(0);
        let resultats: Vec<std::sync::Mutex<Option<Result<(u64, Es), String>>>> = mesure.iter().map(|_| std::sync::Mutex::new(None)).collect();
        let nfils = part.cylindres.min(mesure.len());
        let base: &Regs = et;
        let es_base: &Es = es;
        std::thread::scope(|sc| {
            for fil in 0..nfils {
                let (suivante, resultats) = (&suivante, &resultats);
                sc.spawn(move || {
                    let haut_zone = 0x40_0000u32 + (fil as u32 + 1) * 0x2_0000 - 16;
                    loop {
                        let k = suivante.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        if k >= mesure.len() {
                            break;
                        }
                        let (d, f) = mesure[k];
                        let mut e2 = Regs { pc: d, ..base.clone() };
                        let bas = base.r[14];
                        let haut = (base.r[13].saturating_add(64)).min(PILE_HAUT);
                        let n = haut.saturating_sub(bas) + 1;
                        let neuf = haut_zone - n;
                        for i in 0..n {
                            mem.ecrit(0, neuf + i, mem.lit(0, bas + i));
                        }
                        e2.r[13] = base.r[13].wrapping_sub(bas).wrapping_add(neuf);
                        e2.r[14] = neuf;
                        let mut es2 = es_base.fil();
                        let r_ = prog(mem, &mut es2, max_pas, &mut e2, f, None, 0).map(|p| (p, es2));
                        *resultats[k].lock().unwrap() = Some(r_);
                    }
                });
            }
        });
        for res in resultats {
            let (p, es2) = res.into_inner().unwrap().unwrap()?;
            pas += p;
            es.ie = es.ie.max(es2.ie);
            es.sorties.extend(es2.sorties);
            es.texte.extend(es2.texte);
        }
    }
    et.pc = ac.fin;
    Ok(pas)
}

/// VTX_ROTOS (rotos : la roue, en gaulois) fixe le nombre de cylindres ; sinon les cœurs de la machine moins un.
fn cylindres_machine() -> usize {
    if let Some(n) = std::env::var("VTX_ROTOS").or_else(|_| std::env::var("VTX_CYLINDRES")).ok().and_then(|v| v.parse().ok()) {
        return n;
    }
    let coeurs = std::thread::available_parallelism().map(|n| n.get()).unwrap_or(1);
    coeurs.saturating_sub(1).max(1)
}

/// SYS 5 : 32 bits imprévisibles de la machine hôte (aléa du système, heure, compteur), pour bruit().
fn bruit_hote() -> u32 {
    use std::hash::{BuildHasher, Hasher};
    static COMPTEUR: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
    let mut h = std::collections::hash_map::RandomState::new().build_hasher();
    h.write_u128(std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map(|d| d.as_nanos()).unwrap_or(0));
    h.write_u64(COMPTEUR.fetch_add(1, std::sync::atomic::Ordering::Relaxed));
    let x = h.finish();
    (x ^ (x >> 32)) as u32
}
