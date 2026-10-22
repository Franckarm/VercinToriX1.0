// Émulateur du SPU à cube chromatique pour Vercintorix (vtx 0.4), sans dépendance.
// Même sémantique que vtx.py, Vtx.java et les machines JavaScript : mots de 32 bits #RRGGBBAA, quatre étages de
// 2^24 mots, flottants IEEE 754 binary32 (NaN rendu sous la forme 0x7FC00000), instructions 64 bits ADC, SBC, MULHU.
//
// Utilisation :
//   vtx-spu corpus FICHIER            une ligne par programme « mots;entrées », écrit « instructions|sorties|mémoire »
//   vtx-spu session FICHIER [N]       ligne 1 : les mots ; lignes suivantes : entrées d'appels successifs qui partagent
//                                     la mémoire ; la dernière ligne est rejouée N fois et chronométrée
//   vtx-spu PROG.vtx [ENTRÉES…]       compile PROG.vtx avec vtxc (le compilateur écrit en vtx, embarqué) puis l'exécute
//   vtx-spu compiler PROG.vtx [SORTIE] compile seulement ; écrit « mots; » dans SORTIE (par défaut PROG.prog)
//   vtx-spu renouveler VTXC.vtx       vtxc se recompile lui-même et remplace le compilateur embarqué (vtxc.mots)
//   vtx-spu traduire PROG.vtx [SORTIE] traduit en code natif : un exécutable (rustc doit être installé)
//   vtx-spu traduire-corpus FICHIER SORTIE.rs   tout un corpus en un seul programme Rust (vérification)
use std::env;
use std::fs;
use std::io::{self, Write};
use std::process;
#[allow(unused_imports)]
use std::path::PathBuf;
use std::time::Instant;

mod traduction;
mod atelier;
mod arbre;
mod cube;
#[cfg(windows)]
mod fenetre;

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

/// Table des accords exportée par le compilateur : pour chaque accord, l'adresse où il commence, celle où il finit,
/// et ses mesures (chaque tâche : adresse de début, adresse de fin).
struct Accord {
    fin: u32,
    mesures: Vec<Vec<(u32, u32)>>,
}

struct Partition {
    marques: Vec<u32>,          // adresse de code -> numéro d'accord + 1 (0 : rien)
    accords: Vec<Accord>,
    cylindres: usize,
}

fn lire_partition(nombres_: &[u32], cylindres: usize) -> Partition {
    let mut it = nombres_.iter().copied();
    let n = it.next().unwrap_or(0);
    let mut accords = Vec::new();
    let mut marques: Vec<u32> = Vec::new();
    for k in 0..n {
        let debut = it.next().unwrap();
        let fin = it.next().unwrap();
        let nm = it.next().unwrap();
        let mut mesures = Vec::new();
        for _ in 0..nm {
            let nt = it.next().unwrap();
            mesures.push((0..nt).map(|_| (it.next().unwrap(), it.next().unwrap())).collect());
        }
        if marques.len() <= debut as usize {
            marques.resize(debut as usize + 1, 0);
        }
        marques[debut as usize] = k + 1;
        accords.push(Accord { fin, mesures });
    }
    Partition { marques, accords, cylindres }
}

/// État d'un fil d'exécution : registres, compteur, drapeaux, entrées lues, sorties.
#[derive(Clone)]
struct Etat {
    r: [u32; 16],
    pc: u32,
    z: bool,
    c: bool,
    pas: u64,
    ie: usize,
    sorties: Vec<u32>,
    texte: Vec<u32>,
}

struct Resultat {
    pas: u64,
    sorties: Vec<u32>,
    texte: Vec<u32>,
}

/// Fichier ouvert par SYS : lecture (caractères déjà lus) ou écriture (caractères à écrire à la fermeture).
struct Fichier {
    lecture: bool,
    car: Vec<u32>,
    pos: usize,
    chemin: std::path::PathBuf,
}

/// Texte rangé en mémoire à l'adresse globale adr (étage dans les bits 24 et 25) : longueur, puis un caractère par mot.
fn texte_memoire(mem: &Memoire, adr: u32) -> String {
    let (e, a) = ((adr >> 24) & 3, adr & ADR);
    let n = mem.lit(e, a).min(4096);
    (0..n).filter_map(|i| char::from_u32(mem.lit(e, a.wrapping_add(1 + i)) & 0x1F_FFFF)).collect()
}

#[inline(always)]
fn f(w: u32) -> f32 {
    f32::from_bits(w)
}

#[inline(always)]
fn fb(v: f32) -> u32 {
    if v.is_nan() { 0x7FC0_0000 } else { v.to_bits() }
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

/// Exécute le programme chargé à l'adresse 0 de l'étage 0, registres remis à zéro, mémoire conservée.
fn executer(mem: &mut Memoire, entrees: &[u32], max_pas: u64) -> Result<Resultat, String> {
    executer_dans(mem, entrees, max_pas, None, None)
}

type Fichiers = std::sync::Mutex<std::collections::HashMap<u32, Fichier>>;

/// dossier : où ouvrir les fichiers (None : pas d'accès aux fichiers, comme pour le corpus).
/// partition : la table des accords et le nombre de cylindres (None : tout en séquence).
fn executer_dans(mem: &Memoire, entrees: &[u32], max_pas: u64, dossier: Option<&std::path::Path>,
                 partition: Option<&Partition>) -> Result<Resultat, String> {
    let fichiers: Fichiers = std::sync::Mutex::new(std::collections::HashMap::new());
    let mut et = Etat { r: [0u32; 16], pc: 0, z: false, c: false, pas: 0, ie: 0, sorties: Vec::new(), texte: Vec::new() };
    et.r[14] = PILE_HAUT;
    boucle(mem, &mut et, entrees, max_pas, dossier, &fichiers, u32::MAX, partition, 0)?;
    Ok(Resultat { pas: et.pas, sorties: et.sorties, texte: et.texte })
}

/// Joue un accord : mesure après mesure ; les tâches d'une mesure sur plusieurs cylindres quand il y en a plusieurs.
fn jouer_accord(mem: &Memoire, et: &mut Etat, numero: u32, entrees: &[u32], max_pas: u64, dossier: Option<&std::path::Path>,
                fichiers: &Fichiers, partition: &Partition) -> Result<(), String> {
    let ac = &partition.accords[(numero - 1) as usize];
    for mesure in &ac.mesures {
        if mesure.len() == 1 || partition.cylindres <= 1 {
            for &(d, f) in mesure {
                et.pc = d;
                boucle(mem, et, entrees, max_pas, dossier, fichiers, f, Some(partition), numero)?;
            }
            continue;
        }
        let suivante = std::sync::atomic::AtomicUsize::new(0);
        let resultats: Vec<std::sync::Mutex<Option<Result<Etat, String>>>> = mesure.iter().map(|_| std::sync::Mutex::new(None)).collect();
        let nfils = partition.cylindres.min(mesure.len());
        let base: &Etat = et;
        std::thread::scope(|sc| {
            for fil in 0..nfils {
                let (suivante, resultats) = (&suivante, &resultats);
                sc.spawn(move || {
                    // pile propre au fil : copie du cadre courant (variables locales et arguments)
                    let haut_zone = 0x40_0000u32 + (fil as u32 + 1) * 0x2_0000 - 16;
                    loop {
                        let k = suivante.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        if k >= mesure.len() {
                            break;
                        }
                        let (d, f) = mesure[k];
                        let mut e2 = Etat { pc: d, pas: 0, sorties: Vec::new(), texte: Vec::new(), ..base.clone() };
                        let bas = base.r[14];
                        let haut = (base.r[13].saturating_add(64)).min(PILE_HAUT);
                        let n = haut.saturating_sub(bas) + 1;
                        let neuf = haut_zone - n;
                        for i in 0..n {
                            mem.ecrit(0, neuf + i, mem.lit(0, bas + i));
                        }
                        e2.r[13] = base.r[13].wrapping_sub(bas).wrapping_add(neuf);
                        e2.r[14] = neuf;
                        let r_ = boucle(mem, &mut e2, entrees, max_pas, dossier, fichiers, f, None, 0).map(|_| e2);
                        *resultats[k].lock().unwrap() = Some(r_);
                    }
                });
            }
        });
        for res in resultats {
            let e2 = res.into_inner().unwrap().unwrap()?;
            et.pas += e2.pas;
            et.ie = et.ie.max(e2.ie);
            et.sorties.extend(e2.sorties);
            et.texte.extend(e2.texte);
        }
    }
    et.pc = ac.fin;
    Ok(())
}

/// La boucle d'exécution : de et.pc jusqu'à HALT, ou jusqu'à l'adresse arret (fin d'une tâche).
/// actif : l'accord (numéro + 1) que cette boucle est en train de jouer ; sa marque est ignorée (une tâche peut
/// commencer à l'adresse de l'accord, ou y revenir par une boucle).
fn boucle(mem: &Memoire, et: &mut Etat, entrees: &[u32], max_pas: u64, dossier: Option<&std::path::Path>,
          fichiers: &Fichiers, arret: u32, partition: Option<&Partition>, actif: u32) -> Result<(), String> {
    let mut r = et.r;
    let (mut pc, mut z, mut c) = (et.pc, et.z, et.c);
    let mut pas = et.pas;
    let mut ie = et.ie;
    let mut sorties = std::mem::take(&mut et.sorties);
    let mut texte = std::mem::take(&mut et.texte);
    loop {
        if pc == arret {
            break;
        }
        if let Some(p) = partition {
            if (pc as usize) < p.marques.len() && p.marques[pc as usize] != 0 && p.marques[pc as usize] != actif {
                let numero = p.marques[pc as usize];
                *et = Etat { r, pc, z, c, pas, ie, sorties: std::mem::take(&mut sorties), texte: std::mem::take(&mut texte) };
                jouer_accord(mem, et, numero, entrees, max_pas, dossier, fichiers, p)?;
                r[13] = et.r[13];
                r[14] = et.r[14];
                pc = et.pc;
                pas = et.pas;
                ie = et.ie;
                sorties = std::mem::take(&mut et.sorties);
                texte = std::mem::take(&mut et.texte);
                continue;
            }
        }
        if pas >= max_pas || (pas & 0xF_FFFF == 0 && ARRET.load(std::sync::atomic::Ordering::Relaxed)) {
            // l'état est gardé : le pas à pas de l'atelier reprend d'ici
            *et = Etat { r, pc, z, c, pas, ie, sorties: std::mem::take(&mut sorties), texte: std::mem::take(&mut texte) };
            if pas < max_pas {
                return Err("programme arrêté".to_string());
            }
            return Err(format!("limite de {} instructions atteinte", max_pas));
        }
        let w = mem.lit(0, pc);
        let op = w >> 24;
        let g = (w >> 16) & 255;
        let b = (w >> 8) & 255;
        let etage = (w & 255) >> 6;
        let rd = (g >> 4) as usize;
        let ra = r[(g & 15) as usize];
        let rb = r[(b >> 4) as usize];
        let decal = if b > 127 { b as i32 - 256 } else { b as i32 };
        let mut suivant = (pc + 1) & ADR;
        pas += 1;
        // écrit un registre (R0 reste nul) et pose les drapeaux
        macro_rules! ecrire { ($v:expr) => {{ let v: u32 = $v; if rd != 0 { r[rd] = v; } }}; }
        macro_rules! res { ($v:expr) => {{ let v: u32 = $v; if rd != 0 { r[rd] = v; } z = v == 0; c = false; }}; }
        match op {
            0x00 => {}
            0x01 | 0x06 => {
                let s = ra as u64 + if op == 0x01 { rb as u64 } else { b as u64 };
                ecrire!(s as u32);
                z = (s & MASK) == 0;
                c = s > MASK;
            }
            0x02 | 0x07 | 0x0E => {
                let y = if op == 0x07 { b } else { rb };
                let v = ra.wrapping_sub(y);
                if op != 0x0E {
                    ecrire!(v);
                }
                z = v == 0;
                c = ra < y;
            }
            0x03 => res!(ra.wrapping_mul(rb)),
            0x04 => res!(ra << 2),
            0x05 => res!(ra >> 2),
            0x08 => res!(ra << (rb & 31)),
            0x09 => res!(ra >> (rb & 31)),
            0x0A => {
                let v = mem.lit(0, suivant);
                res!(v);
                suivant = (suivant + 1) & ADR;
            }
            0x0B => ecrire!(ra),
            0x0C => res!(if rb == 0 { u32::MAX } else { ra / rb }),
            0x0D => res!(if rb == 0 { ra } else { ra % rb }),
            0x10 | 0x11 | 0x13 => res!(quits(ra, rb, op)),
            0x12 => res!(!ra),
            0x14 => res!(ra & rb),
            0x15 => res!(ra | rb),
            0x16 => res!(ra ^ rb),
            0x20 => res!(mem.lit(etage, ra)),
            0x21 => mem.ecrit(etage, r[rd], ra),
            0x22 => return Err("DMA non implémentée".into()),
            0x23 => {
                let v = if ie < entrees.len() { ie += 1; entrees[ie - 1] } else { 0 };
                ecrire!(v);
            }
            0x24 => sorties.push(ra),
            0x51 => {
                // ENTC : un mot du canal ra
                let v = match ra {
                    0 => if ie < entrees.len() { ie += 1; entrees[ie - 1] } else { 0 },
                    1 => lire_console(&mut texte),
                    k => match fichiers.lock().unwrap().get_mut(&k) {
                        Some(fi) if fi.lecture && fi.pos < fi.car.len() => { fi.pos += 1; fi.car[fi.pos - 1] }
                        _ => 0xFFFF_FFFF,
                    },
                };
                res!(v);
            }
            0x52 => match rb {
                // SORC : le mot ra sur le canal rb
                0 => sorties.push(ra),
                1 => ecrire_console(&mut texte, ra),
                k => { if let Some(fi) = fichiers.lock().unwrap().get_mut(&k) { if !fi.lecture { fi.car.push(ra); } } }
            },
            0x53 => {
                // SYS : service ra, argument rb
                let mut fichiers = fichiers.lock().unwrap();
                let v: u32 = match ra {
                    1 | 2 => match dossier {
                        None => 0xFFFF_FFFF,
                        Some(d) => {
                            let chemin = d.join(texte_memoire(mem, rb));
                            let canal = fichiers.keys().copied().max().unwrap_or(1).max(1) + 1;
                            if ra == 1 {
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
                    3 => match fichiers.remove(&rb) {
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
                    // 8 : accorder un étage sur une fréquence (argument : fréquence × 4 + étage) ; 9 : sa fréquence
                    8 => mem.accorder(rb & 3, rb >> 2),
                    10 => return Err("mémoire pleine : le tas ne peut plus grandir, même après avoir ramassé les miettes".to_string()),
                    9 => mem.frequence(rb & 3),
                    // 6 et 7 : écrire ou lire un bloc de mots dans un fichier (nom, adresse globale et nombre de mots
                    // rangés en @3[14680060..14680062]) ; rend le nombre de mots, ou 4294967295
                    6 | 7 => match dossier {
                        None => 0xFFFF_FFFF,
                        Some(d) => {
                            let chemin = d.join(texte_memoire(mem, mem.lit(3, 14_680_060)));
                            let (a, n) = (mem.lit(3, 14_680_061), mem.lit(3, 14_680_062));
                            let (e, o) = ((a >> 24) & 3, a & ADR);
                            if ra == 6 {
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
                    4 => match fichiers.get(&rb) {
                        Some(fi) if fi.lecture && fi.pos < fi.car.len() => 0,
                        _ => 1,
                    },
                    _ => 0xFFFF_FFFF,
                };
                res!(v);
            }
            0x25 => ecrire!(mem.lit(0, (r[13] as i64 + decal as i64) as u32)),
            0x26 => mem.ecrit(0, (r[13] as i64 + decal as i64) as u32, r[rd]),
            0x27 => {
                r[14] = r[14].wrapping_sub(1) & ADR;
                mem.ecrit(0, r[14], ra);
            }
            0x28 => {
                let v = mem.lit(0, r[14]);
                r[14] = (r[14] + 1) & ADR;
                ecrire!(v);
            }
            0x29 => res!(mem.lit(rb & 3, ra)),
            // quaternaire : un quit d'un tableau rangé (mot Rs + (Rt >> 4), place (Rt & 15) × 2)
            0x54 => res!((mem.lit(etage, ra.wrapping_add(rb >> 4) & ADR) >> ((rb & 15) * 2)) & 3),
            0x55 => {
                let adr = ra.wrapping_add(rb >> 4) & ADR;
                let d = (rb & 15) * 2;
                let v = (mem.lit(etage, adr) & !(3 << d)) | ((r[rd] & 3) << d);
                mem.ecrit(etage, adr, v);
            }
            0x2A => mem.ecrit(rb & 3, r[rd], ra),
            0x30 | 0x31 | 0x32 | 0x33 | 0x35 | 0x36 => {
                let saut = match op {
                    0x31 => z,
                    0x32 => !z,
                    0x35 => c,
                    0x36 => !c,
                    _ => true,
                };
                if op == 0x33 {
                    r[14] = r[14].wrapping_sub(1) & ADR;
                    mem.ecrit(0, r[14], suivant);
                }
                if saut {
                    suivant = ((w & 15) << 16) | (g << 8) | b;
                }
            }
            0x34 => {
                suivant = mem.lit(0, r[14]);
                r[14] = (r[14] + 1) & ADR;
            }
            0x38 => res!(dot(ra, rb) as u32),
            0x39 => {
                let sp = r[14];
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
            0x3F => {
                pc = arret;                 // HALT : fin du programme (ou d'une tâche, par sécurité)
                break;
            }
            0x40 => res!(fb(f(ra) + f(rb))),
            0x41 => res!(fb(f(ra) - f(rb))),
            0x42 => res!(fb(f(ra) * f(rb))),
            0x43 => res!(fb(f(ra) / f(rb))),
            0x44 => res!((f(ra) == f(rb)) as u32),
            0x45 => res!((f(ra) < f(rb)) as u32),
            0x46 => res!((f(ra) <= f(rb)) as u32),
            0x47 => res!(fb(f(ra).sqrt())),
            0x48 => res!(fb(ra as f32)),
            0x49 => res!(fb(ra as i32 as f32)),
            0x4A => res!(f(ra) as i32 as u32),
            0x4B => res!(f(ra).round_ties_even() as i32 as u32),
            0x4C => {
                let s = ra as u64 + rb as u64 + c as u64;
                ecrire!(s as u32);
                z = (s & MASK) == 0;
                c = s > MASK;
            }
            0x4D => {
                let y = rb as u64 + c as u64;
                let v = (ra as u64).wrapping_sub(y) as u32;
                ecrire!(v);
                z = v == 0;
                c = (ra as u64) < y;
            }
            0x4E => res!(((ra as u64 * rb as u64) >> 32) as u32),
            0x4F => {
                let x = ra ^ rb;
                res!(!(x | (x >> 1)) & 0x5555_5555)
            }
            0x50 => res!(ra.count_ones()),
            _ => return Err(format!("code d'opération inconnu {:#04x} à l'adresse {}", op, pc)),
        }
        pc = suivant;
    }
    *et = Etat { r, pc, z, c, pas, ie, sorties, texte };
    Ok(())
}

fn nombres(s: &str) -> Vec<u32> {
    s.split(',').filter(|t| !t.trim().is_empty()).map(|t| t.trim().parse::<u64>().expect("nombre attendu") as u32).collect()
}

fn charger(mem: &mut Memoire, mots: &[u32]) {
    for (i, &w) in mots.iter().enumerate() {
        mem.ecrit(0, i as u32, w);
    }
}

fn corpus(fichier: &str) {
    let texte = fs::read_to_string(fichier).expect("lecture du corpus impossible");
    let sortie = io::stdout();
    let mut out = io::BufWriter::new(sortie.lock());
    let mut mem = Memoire::new(true);
    for ligne in texte.lines().filter(|l| !l.trim().is_empty()) {
        let (m, e) = ligne.split_once(';').unwrap_or((ligne, ""));
        mem.effacer(); // mémoire neuve pour chaque programme : on remet à zéro tout ce qui a été écrit
        charger(&mut mem, &nombres(m));
        match executer(&mut mem, &nombres(e), 500_000_000) {
            Ok(r) => {
                let s: Vec<String> = r.sorties.iter().map(|v| v.to_string()).collect();
                let etat: Vec<String> = mem.etat().iter().map(|(k, v)| format!("{}:{}", k, v)).collect();
                let t: Vec<String> = r.texte.iter().map(|v| v.to_string()).collect();
                if t.is_empty() {
                    writeln!(out, "{}|{}|{}", r.pas, s.join(","), etat.join(",")).unwrap();
                } else {
                    writeln!(out, "{}|{}|{}|T:{}", r.pas, s.join(","), etat.join(","), t.join(",")).unwrap();
                }
            }
            Err(e) => writeln!(out, "ERREUR {}", e).unwrap(),
        }
    }
}

fn session(fichier: &str, n: usize) {
    let texte = fs::read_to_string(fichier).expect("lecture de la session impossible");
    let lignes: Vec<&str> = texte.lines().filter(|l| !l.trim().is_empty()).collect();
    let mut mem = Memoire::new(false);
    charger(&mut mem, &nombres(lignes[0]));
    for l in &lignes[1..lignes.len() - 1] {
        if let Err(e) = executer(&mut mem, &nombres(l), 500_000_000) {
            eprintln!("erreur : {}", e);
            process::exit(1);
        }
    }
    let derniere = nombres(lignes[lignes.len() - 1]);
    let debut = Instant::now();
    let mut total = 0u64;
    let mut dernier = None;
    for _ in 0..n {
        let r = executer(&mut mem, &derniere, 500_000_000).unwrap_or_else(|e| {
            eprintln!("erreur : {}", e);
            process::exit(1)
        });
        total += r.pas;
        dernier = Some(r);
    }
    let duree = debut.elapsed().as_secs_f64();
    let r = dernier.unwrap();
    println!("{} appels de {} instructions : {:.3} ms par appel, {:.0} millions d'instructions par seconde",
             n, r.pas, duree * 1000.0 / n as f64, total as f64 / duree / 1e6);
    let s: Vec<String> = r.sorties.iter().map(|v| v.to_string()).collect();
    println!("sorties du dernier appel : [{}]", s.join(", "));
}

/// Un programme : « mots;entrées » sur une ligne ; affiche le nombre d'instructions, la durée, puis les sorties.
fn lancer(fichier: &str, max_pas: u64, cylindres: usize) {
    let texte = fs::read_to_string(fichier).expect("lecture du programme impossible");
    let ligne = texte.lines().find(|l| !l.trim().is_empty()).expect("programme vide");
    let mut morceaux = ligne.split(';');
    let m = morceaux.next().unwrap_or("");
    let e = morceaux.next().unwrap_or("");
    let t = morceaux.next().unwrap_or("");
    let mut mem = Memoire::new(false);
    charger(&mut mem, &nombres(m));
    let partition = if t.trim().is_empty() || cylindres <= 1 { None } else { Some(lire_partition(&nombres(t), cylindres)) };
    let debut = Instant::now();
    let ici = std::env::current_dir().unwrap_or_default();
    match executer_dans(&mem, &nombres(e), max_pas, Some(&ici), partition.as_ref()) {
        Ok(r) => {
            let duree = debut.elapsed().as_secs_f64();
            println!("{} instructions en {:.3} s ({:.0} millions par seconde)", r.pas, duree, r.pas as f64 / duree / 1e6);
            let s: Vec<String> = r.sorties.iter().map(|v| v.to_string()).collect();
            println!("{}", s.join(","));
            let t: String = r.texte.iter().filter_map(|&v| char::from_u32(v & 0x1F_FFFF)).collect();
            print!("{}", t);
        }
        Err(e) => {
            eprintln!("erreur : {}", e);
            process::exit(1);
        }
    }
}

/// Le compilateur vtxc, déjà compilé (par lui-même) : ses mots machine, embarqués dans l'exécutable.
const VTXC: &str = include_str!("../vtxc.mots");

/// Fait tourner un compilateur (ses mots) sur un texte vtx ; rend les mots produits, ou les messages d'erreur.
/// vtxc lit « source.vtx » et écrit « code.mots » : on lui prépare un dossier de travail temporaire. Ses entrées : le
/// dossier du programme (un caractère par entrée, puis 0), où il cherche les fichiers importés.
/// Ce que vtxc fait : ajouter le prélude, optimiser, partitionner les tâches en accords (comme vtx.py par défaut).
#[derive(Clone, Copy)]
struct Mode {
    prelude: bool,
    optim: bool,
    partition: bool,
}

const COMPLET: Mode = Mode { prelude: true, optim: true, partition: true };
/// Le pas à pas de l'atelier : comme COMPLET, sans partition (l'exécution reste en séquence, ligne après ligne).
const PAS_A_PAS: Mode = Mode { prelude: true, optim: true, partition: false };
/// vtxc lui-même : sans prélude (il a ses propres outils), optimisé, sans partition.
const COMPILATEUR: Mode = Mode { prelude: false, optim: true, partition: false };

/// Rend les mots du programme et la table des accords (vide sans partition).
fn compiler_avec(compilateur: &[u32], source: &str, base: &str, mode: Mode) -> Result<(Vec<u32>, Vec<u32>), String> {
    compiler_lignes(compilateur, source, base, mode, false).map(|(m, t, _)| (m, t))
}

/// Comme compiler_avec ; avec lignes, rend aussi la table du pas à pas : adresse, ligne du fichier, adresse, ligne…
fn compiler_lignes(compilateur: &[u32], source: &str, base: &str, mode: Mode, lignes: bool)
                   -> Result<(Vec<u32>, Vec<u32>, Vec<u32>), String> {
    let dossier = env::temp_dir().join(format!("vtxc-{}-{}", process::id(), Instant::now().elapsed().as_nanos()));
    fs::create_dir_all(&dossier).map_err(|e| e.to_string())?;
    fs::write(dossier.join("source.vtx"), source).map_err(|e| e.to_string())?;
    let mut mem = Memoire::new(false);
    charger(&mut mem, compilateur);
    let mut entrees: Vec<u32> = base.chars().map(|c| c as u32).collect();
    entrees.push(0);
    for drapeau in [mode.prelude, mode.optim, mode.partition, lignes] {
        entrees.push(if drapeau { 1 } else { 0 });
    }
    let r = executer_dans(&mem, &entrees, 100_000_000_000, Some(&dossier), None);
    let code = fs::read_to_string(dossier.join("code.mots"));
    let _ = fs::remove_dir_all(&dossier);
    let r = r?;
    let messages: String = r.texte.iter().filter_map(|&v| char::from_u32(v & 0x1F_FFFF)).collect();
    match code {
        Ok(t) => {
            let mut morceaux = t.split(';');
            let mots = nombres(morceaux.next().unwrap_or(""));
            let table = nombres(morceaux.next().unwrap_or(""));
            let dbg = nombres(morceaux.next().unwrap_or(""));
            Ok((mots, table, dbg))
        }
        Err(_) => Err(messages),
    }
}

fn lire_source(fichier: &str) -> String {
    match fs::read_to_string(fichier) {
        Ok(t) => t,
        Err(e) => {
            eprintln!("lecture de {} impossible : {}", fichier, e);
            process::exit(1);
        }
    }
}

/// Le dossier absolu d'un fichier (les fichiers importés sont cherchés à partir de lui).
fn dossier_de(fichier: &str) -> String {
    let chemin = env::current_dir().unwrap_or_default().join(fichier);
    chemin.parent().map(|p| p.to_string_lossy().into_owned()).unwrap_or_default()
}

fn compiler_ou_sortir(fichier: &str, mode: Mode) -> (Vec<u32>, Vec<u32>) {
    match compiler_avec(&nombres(VTXC), &lire_source(fichier), &dossier_de(fichier), mode) {
        Ok(m) => m,
        Err(e) => {
            // « erreur ligne N » : on nomme le fichier, pour que l'éditeur retrouve l'endroit
            let nom = std::path::Path::new(fichier).file_name().map(|n| n.to_string_lossy().into_owned()).unwrap_or_default();
            eprint!("{}", e.replace("erreur ligne ", &format!("erreur {}, ligne ", nom)));
            process::exit(1);
        }
    }
}

// ------------------------------------------------------------------------------------------------ la console du programme
// Le canal 1 : ce que le programme écrit (ecrire_texte, afficher) et ce qu'il lit (lire_car(1), lire_ligne()).
// Par défaut, le texte écrit est gardé et montré à la fin, et rien n'est à lire. vtx PROG.vtx lit le clavier : dès la
// première lecture, le texte en attente est montré et la suite est écrite au fur et à mesure (une question avant sa
// réponse). La fenêtre de l'atelier branche ses propres canaux (DIRECT, CANAL_ENTREE, CANAL_SORTIE).
use std::sync::atomic::{AtomicBool, AtomicU8, Ordering};
/// 0 : rien à lire ; 1 : le clavier ; 2 : la fenêtre de l'atelier
static CLAVIER: AtomicU8 = AtomicU8::new(0);
static ECHO: AtomicBool = AtomicBool::new(false);
static DIRECT: AtomicBool = AtomicBool::new(false);
/// demande d'arrêt (bouton Arrêter de l'atelier) : vue toutes les 2^20 instructions
static ARRET: AtomicBool = AtomicBool::new(false);
/// Temps passé à attendre le clavier pendant l'exécution (nanosecondes), retiré du temps de calcul affiché.
static ATTENTE_NS: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
static CANAL_ENTREE: std::sync::Mutex<Option<std::sync::mpsc::Receiver<u32>>> = std::sync::Mutex::new(None);
static CANAL_SORTIE: std::sync::Mutex<Option<std::sync::mpsc::Sender<u32>>> = std::sync::Mutex::new(None);

fn ecrire_console(texte: &mut Vec<u32>, v: u32) {
    if DIRECT.load(Ordering::Relaxed) {
        if let Some(s) = CANAL_SORTIE.lock().unwrap().as_ref() {
            let _ = s.send(v);
        }
        texte.push(v);
    } else if ECHO.load(Ordering::Relaxed) {
        let mut o = io::stdout();
        if let Some(c) = char::from_u32(v & 0x1F_FFFF) {
            let _ = write!(o, "{}", c);
        }
        if v == 10 {
            let _ = o.flush();
        }
    } else {
        texte.push(v);
    }
}

fn lire_console(texte: &mut Vec<u32>) -> u32 {
    match CLAVIER.load(Ordering::Relaxed) {
        1 => {
            let mut o = io::stdout();
            if !ECHO.swap(true, Ordering::Relaxed) {
                let t: String = texte.iter().filter_map(|&v| char::from_u32(v & 0x1F_FFFF)).collect();
                let _ = write!(o, "{}", t);
                texte.clear();
            }
            let _ = o.flush();
            lire_car_clavier()
        }
        2 => {
            let t0 = std::time::Instant::now();
            let r = CANAL_ENTREE.lock().unwrap();
            let v = match r.as_ref().map(|c| c.recv()) {
                Some(Ok(v)) => v,
                _ => 0xFFFF_FFFF,
            };
            ATTENTE_NS.fetch_add(t0.elapsed().as_nanos() as u64, Ordering::Relaxed);
            v
        }
        _ => 0xFFFF_FFFF,
    }
}

/// Un caractère du clavier (UTF-8), ou 4294967295 à la fin de l'entrée.
fn lire_car_clavier() -> u32 {
    use std::io::Read;
    let mut entree = io::stdin().lock();
    let mut o = [0u8; 4];
    if entree.read(&mut o[..1]).unwrap_or(0) == 0 {
        return 0xFFFF_FFFF;
    }
    let n = match o[0] {
        0x00..=0x7F => 1,
        0xC0..=0xDF => 2,
        0xE0..=0xEF => 3,
        _ => 4,
    };
    for k in 1..n {
        if entree.read(&mut o[k..k + 1]).unwrap_or(0) == 0 {
            return 0xFFFF_FFFF;
        }
    }
    std::str::from_utf8(&o[..n]).ok().and_then(|s| s.chars().next()).map(|c| c as u32).unwrap_or(0xFFFD)
}

// ------------------------------------------------------------------------------------------------ installer
/// vtx installer : les fichiers .vtx deviennent des « programmes Vercintorix », avec l'icône du cube, et s'ouvrent dans
/// l'atelier d'un double-clic. Sous Windows : le registre de l'utilisateur (sans droits d'administrateur). Sous Linux :
/// un type de fichier, une application et une icône dans ~/.local/share. vtx desinstaller retire tout.
pub fn installer(poser: bool) -> Result<String, String> {
    let exe = env::current_exe().expect("chemin de l'exécutable inconnu");
    let dossier = exe.parent().map(|p| p.to_path_buf()).unwrap_or_default();
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        let atelier = dossier.join("atelier.exe");
        let icone = dossier.join("vtx.ico");
        let reg = |args: &[&str]| {
            let r = process::Command::new("reg").args(args).creation_flags(0x0800_0000).output();
            matches!(r, Ok(o) if o.status.success())
        };
        let ok = if poser {
            let _ = fs::write(&icone, cube::ico(&[16, 32, 48, 256]));
            let commande = format!("\"{}\" \"%1\"", atelier.display());
            reg(&["add", r"HKCU\Software\Classes\.vtx", "/ve", "/d", "Vercintorix.Programme", "/f"])
                && reg(&["add", r"HKCU\Software\Classes\Vercintorix.Programme", "/ve", "/d", "Programme Vercintorix", "/f"])
                && reg(&["add", r"HKCU\Software\Classes\Vercintorix.Programme\DefaultIcon", "/ve", "/d", &icone.display().to_string(), "/f"])
                && reg(&["add", r"HKCU\Software\Classes\Vercintorix.Programme\shell\open\command", "/ve", "/d", &commande, "/f"])
        } else {
            reg(&["delete", r"HKCU\Software\Classes\.vtx", "/f"]) & reg(&["delete", r"HKCU\Software\Classes\Vercintorix.Programme", "/f"])
        };
        #[link(name = "shell32")]
        extern "system" {
            fn SHChangeNotify(evenement: i32, drapeaux: u32, a: *const core::ffi::c_void, b: *const core::ffi::c_void);
        }
        unsafe {
            SHChangeNotify(0x0800_0000, 0, std::ptr::null(), std::ptr::null());
        }
        if poser && ok {
            Ok(format!("Les fichiers .vtx s'ouvrent maintenant dans {} (icône : {}).\nSi Windows propose encore une autre \
                        application : clic droit sur un .vtx, « Ouvrir avec », atelier.exe, « Toujours ».", atelier.display(), icone.display()))
        } else if ok {
            Ok("Association des fichiers .vtx retirée.".to_string())
        } else {
            Err("Le registre n'a pas pu être modifié (commande reg).".to_string())
        }
    }
    #[cfg(not(windows))]
    {
        let maison = PathBuf::from(env::var("HOME").expect("HOME inconnu"));
        let partage = maison.join(".local/share");
        let app = partage.join("applications/vercintorix-atelier.desktop");
        let mime = partage.join("mime/packages/vercintorix.xml");
        let icones = [partage.join("icons/hicolor/64x64/apps/vercintorix.png"),
                      partage.join("icons/hicolor/64x64/mimetypes/text-x-vtx.png"),
                      partage.join("icons/hicolor/256x256/apps/vercintorix.png"),
                      partage.join("icons/hicolor/256x256/mimetypes/text-x-vtx.png")];
        let lancer = |cmd: &str, args: &[&str]| { let _ = process::Command::new(cmd).args(args).output(); };
        if poser {
            for f in [&app, &mime] {
                let _ = fs::create_dir_all(f.parent().unwrap());
            }
            let vtx = dossier.join("vtx");
            let _ = fs::write(&app, format!("[Desktop Entry]\nType=Application\nName=Atelier vtx\nComment=Écrire, lancer et voir le cube : Vercintorix\n\
                Exec=\"{}\" atelier %f\nTerminal=true\nIcon=vercintorix\nMimeType=text/x-vtx;\nCategories=Development;\n", vtx.display()));
            let _ = fs::write(&mime, "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<mime-info xmlns=\"http://www.freedesktop.org/standards/shared-mime-info\">\n\
                  <mime-type type=\"text/x-vtx\">\n    <comment>Programme Vercintorix</comment>\n    <sub-class-of type=\"text/plain\"/>\n\
                    <glob pattern=\"*.vtx\"/>\n  </mime-type>\n</mime-info>\n");
            for (i, f) in icones.iter().enumerate() {
                let _ = fs::create_dir_all(f.parent().unwrap());
                let _ = fs::write(f, cube::png(if i < 2 { 64 } else { 256 }));
            }
            lancer("update-mime-database", &[&partage.join("mime").to_string_lossy()]);
            lancer("update-desktop-database", &[&partage.join("applications").to_string_lossy()]);
            lancer("xdg-mime", &["default", "vercintorix-atelier.desktop", "text/x-vtx"]);
            Ok(format!("Les fichiers .vtx sont maintenant des « programmes Vercintorix » : un double-clic ouvre l'atelier (dans un \
                        terminal).\nFichiers posés : {}, {} et les icônes dans {}.", app.display(), mime.display(),
                       partage.join("icons/hicolor").display()))
        } else {
            for f in [&app, &mime].into_iter().chain(icones.iter()) {
                let _ = fs::remove_file(f);
            }
            lancer("update-mime-database", &[&partage.join("mime").to_string_lossy()]);
            lancer("update-desktop-database", &[&partage.join("applications").to_string_lossy()]);
            Ok("Association des fichiers .vtx retirée.".to_string())
        }
    }
}

/// vtx-spu PROG.vtx [ENTRÉES…] : compile puis exécute, les fichiers du programme étant ouverts dans le dossier courant ;
/// les accords sont joués sur les cœurs de la machine moins un.
fn executer_vtx(fichier: &str, entrees: &[u32], montrer_arbre: bool) {
    let (mots, table) = compiler_ou_sortir(fichier, COMPLET);
    CLAVIER.store(1, Ordering::Relaxed);
    let mut mem = Memoire::new(false);
    charger(&mut mem, &mots);
    let ici = env::current_dir().unwrap_or_default();
    let cylindres = cylindres_voulus(None);
    let partition = if table.first().copied().unwrap_or(0) == 0 || cylindres <= 1 { None } else { Some(lire_partition(&table, cylindres)) };
    match executer_dans(&mem, entrees, 10_000_000_000, Some(&ici), partition.as_ref()) {
        Ok(r) => {
            if !r.sorties.is_empty() {
                let s: Vec<String> = r.sorties.iter().map(|v| v.to_string()).collect();
                println!("{}", s.join(","));
            }
            let t: String = r.texte.iter().filter_map(|&v| char::from_u32(v & 0x1F_FFFF)).collect();
            print!("{}", t);
            if montrer_arbre {
                println!("──────────");
                print!("{}", arbre::ecrire(&arbre::arbre(&|e, a| mem.lit(e, a))));
            }
        }
        Err(e) => {
            eprintln!("erreur : {}", e);
            process::exit(1);
        }
    }
}

/// vtxc se recompile lui-même ; le nouveau compilateur doit se reproduire à l'identique (point fixe) avant d'être gardé.
fn renouveler(fichier: &str) {
    let source = lire_source(fichier);
    // l'ancien compilateur compile le nouveau (m1) ; m1 le recompile (m2), qui produit alors exactement le code du
    // nouveau compilateur ; m2 se recompile (m3) : m2 = m3 exigé
    let (m1, _) = compiler_ou_sortir(fichier, COMPILATEUR);
    let etape = |m: &[u32]| match compiler_avec(m, &source, &dossier_de(fichier), COMPILATEUR) {
        Ok((x, _)) => x,
        Err(e) => {
            eprint!("le nouveau compilateur échoue sur lui-même : {}", e);
            process::exit(1);
        }
    };
    let m2 = etape(&m1);
    let m3 = etape(&m2);
    let (m1, m2) = (m2, m3);
    if m1 != m2 {
        eprintln!("pas de point fixe : le nouveau compilateur ne se reproduit pas à l'identique ; rien n'est remplacé");
        process::exit(1);
    }
    let s: Vec<String> = m2.iter().map(|v| v.to_string()).collect();
    fs::write("vtxc.mots", s.join(",")).expect("écriture de vtxc.mots impossible");
    println!("point fixe atteint ({} mots) : vtxc.mots écrit ; recompilez la machine (cargo build --release) pour l'embarquer", m2.len());
}

/// vtx traduire PROG.vtx [SORTIE] : vtxc compile, la traduction donne du Rust, rustc en fait un exécutable natif.
fn traduire_programme(fichier: &str, sortie: Option<&String>) {
    let (mots, table) = compiler_ou_sortir(fichier, COMPLET);
    let source = match traduction::programme_complet(&mots, &table) {
        Ok(t) => t,
        Err(e) => {
            eprintln!("traduction impossible : {}", e);
            process::exit(1);
        }
    };
    let base = fichier.trim_end_matches(".vtx").to_string();
    let exe = sortie.cloned().unwrap_or_else(|| base.clone() + if cfg!(windows) { ".exe" } else { "" });
    let rs = env::temp_dir().join(format!("vtx-natif-{}.rs", process::id()));
    fs::write(&rs, source).expect("écriture du programme traduit impossible");
    let debut = Instant::now();
    let r = process::Command::new("rustc")
        .args(["--edition", "2021", "-C", "opt-level=3", "-C", "panic=abort", "-o", &exe])
        .arg(&rs)
        .status();
    let _ = fs::remove_file(&rs);
    match r {
        Ok(st) if st.success() => println!("{} : {} mots traduits en code natif en {:.1} s", exe, mots.len(), debut.elapsed().as_secs_f64()),
        Ok(_) => {
            eprintln!("rustc a échoué");
            process::exit(1);
        }
        Err(_) => {
            eprintln!("rustc introuvable : la traduction en code natif passe par le compilateur Rust (rustup.rs)");
            process::exit(1);
        }
    }
}

fn main() {
    let args: Vec<String> = env::args().collect();
    // atelier.exe (le même programme sous ce nom) : l'atelier, sur le fichier donné ou en commençant par « ouvrir ».
    // Un double-clic sur atelier.exe, ou « Ouvrir avec » sur un fichier .vtx, arrive ici.
    let nom = std::path::Path::new(&args[0]).file_stem().map(|n| n.to_string_lossy().to_lowercase()).unwrap_or_default();
    if nom == "atelier" {
        // sous Windows, la fenêtre ; ailleurs, l'atelier en console
        #[cfg(windows)]
        fenetre::lancer_fenetre(args.get(1).map(|s| s.as_str()));
        #[cfg(not(windows))]
        atelier::atelier(args.get(1).map(|s| s.as_str()));
        return;
    }
    match args.get(1).map(|s| s.as_str()) {
        Some("corpus") if args.len() > 2 => corpus(&args[2]),
        Some("lancer") if args.len() > 2 => {
            // cylindres : par défaut, les cœurs de la machine moins un (laissé au système), au moins un
            let cyl = cylindres_voulus(args.get(4).and_then(|s| s.parse().ok()));
            lancer(&args[2], args.get(3).map(|s| s.parse().unwrap()).unwrap_or(10_000_000_000), cyl)
        }
        Some("compiler") if args.len() > 2 => {
            let (mots, table) = compiler_ou_sortir(&args[2], COMPLET);
            let sortie = args.get(3).cloned().unwrap_or_else(|| args[2].trim_end_matches(".vtx").to_string() + ".prog");
            let s: Vec<String> = mots.iter().map(|v| v.to_string()).collect();
            let t: Vec<String> = table.iter().map(|v| v.to_string()).collect();
            // « mots;entrées;table » : le format de « lancer »
            fs::write(&sortie, s.join(",") + ";;" + &t.join(",") + "\n").expect("écriture impossible");
            println!("{} : {} mots", sortie, mots.len());
        }
        Some("renouveler") if args.len() > 2 => renouveler(&args[2]),
        Some("image") => cube::image(&args[2..]),
        Some("dessin") => cube::dessin(&args[2..]),
        Some("icone") if args.len() > 2 => {
            let f = &args[2];
            let o = if f.ends_with(".ico") { cube::ico(&[16, 32, 48, 256]) } else { cube::png(args.get(3).and_then(|t| t.parse().ok()).unwrap_or(64)) };
            fs::write(f, o).expect("écriture impossible");
        }
        Some(c @ ("installer" | "desinstaller")) => match installer(c == "installer") {
            Ok(m) => println!("{}", m),
            Err(e) => {
                eprintln!("{}", e);
                process::exit(1);
            }
        },
        Some("atelier") => atelier::atelier(args.get(2).map(|s| s.as_str())),
        Some("traduire") if args.len() > 2 => traduire_programme(&args[2], args.get(3)),
        Some("traduire-corpus") if args.len() > 3 => {
            let texte = fs::read_to_string(&args[2]).expect("lecture du corpus impossible");
            let lignes: Vec<(Vec<u32>, Vec<u32>)> = texte.lines().filter(|l| !l.trim().is_empty()).map(|l| {
                let (m, e) = l.split_once(';').unwrap_or((l, ""));
                (nombres(m), nombres(e))
            }).collect();
            fs::write(&args[3], traduction::corpus_complet(&lignes).expect("traduction impossible")).expect("écriture impossible");
        }
        Some("arbre") if args.len() > 2 => {
            // le programme, puis l'arbre des liaisons de sa mémoire
            let e: Vec<u32> = args[3..].iter().flat_map(|t| t.split_whitespace()).filter_map(|t| t.parse::<u64>().ok()).map(|x| x as u32).collect();
            executer_vtx(&args[2], &e, true)
        }
        Some(f) if f.ends_with(".vtx") => {
            // les entrées : des nombres, séparés par des espaces (un seul argument peut en contenir plusieurs)
            let e: Vec<u32> = args[2..].iter().flat_map(|t| t.split_whitespace())
                .map(|t| t.parse::<u64>().unwrap_or_else(|_| { eprintln!("entrée : un nombre attendu, pas « {} »", t); process::exit(2) }) as u32)
                .collect();
            executer_vtx(f, &e, false)
        }
        Some("session") if args.len() > 2 => session(&args[2], args.get(3).map(|s| s.parse().unwrap()).unwrap_or(100)),
        _ => {
            eprintln!("utilisation : vtx-spu PROG.vtx [ENTRÉES…] | vtx-spu atelier PROG.vtx | vtx-spu compiler PROG.vtx [SORTIE] | vtx-spu renouveler VTXC.vtx | vtx-spu corpus FICHIER | vtx-spu session FICHIER [N] | vtx-spu lancer FICHIER [MAX_PAS] [CYLINDRES]");
            process::exit(2);
        }
    }
}

/// Le nombre de cylindres (fils d'exécution) pour les accords : 2 par défaut, jamais plus de 8 ni plus que de cœurs.
/// VTX_ROTOS (ou VTX_CYLINDRES) le change, dans ces limites.
const CYLINDRES_DEFAUT: usize = 2;
const CYLINDRES_MAX: usize = 8;
fn cylindres_voulus(demande: Option<usize>) -> usize {
    let coeurs = std::thread::available_parallelism().map(|n| n.get()).unwrap_or(1);
    let voulu = demande
        .or_else(|| env::var("VTX_ROTOS").or_else(|_| env::var("VTX_CYLINDRES")).ok().and_then(|v| v.parse().ok()))
        .unwrap_or(CYLINDRES_DEFAUT);
    voulu.clamp(1, CYLINDRES_MAX.min(coeurs.max(1)))
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
        let _ = process::Command::new("powershell").args(["-NoProfile", "-NonInteractive", "-Command", script])
            .env("VTX_VOIX", t).creation_flags(0x0800_0000).status();
    }
    #[cfg(not(windows))]
    {
        for prog in ["espeak-ng", "espeak"] {
            if process::Command::new(prog).args(["-v", "fr", t]).stdout(process::Stdio::null())
                .stderr(process::Stdio::null()).status().is_ok() {
                return;
            }
        }
    }
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
