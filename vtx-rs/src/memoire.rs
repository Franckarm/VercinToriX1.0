// La mémoire du SPU-32 : quatre étages de 2^24 mots, les cubes (fréquences), les cubes sur disque (avec leur miroir
// inversé et leur ombre, miroir.rs). La machine émulée s'en sert, et la forge (forge/forge.py) la recopie telle quelle
// dans chaque programme forgé : un programme forgé a exactement la mémoire de la machine.
#![allow(dead_code)]
use super::miroir;
use std::env;
use std::fs;

pub const ADR: u32 = 0x00FF_FFFF;
pub const ETAGE: usize = 1 << 24;
/// Mémoire : quatre étages de 2^24 mots, en pages de 65 536 mots créées à la première écriture non nulle (lire une
/// page jamais écrite rend 0 sans rien réserver : un petit programme ne prend que quelques pages, pas 256 Mo).
/// Chaque étage regarde le cube de sa fréquence (0 au départ) : accorder un étage sur une autre fréquence range ses
/// 256 pages sous l'ancienne fréquence et sort celles du cube demandé (les autres cubes gardent leur contenu) ; les
/// cubes s'additionnent ainsi sans changer la taille des mots. En mode corpus, la liste des cases écrites permet de
/// rendre l'état final et de remettre la mémoire à zéro entre deux programmes. La mémoire est partagée par les
/// cylindres (fils d'exécution) qui jouent ensemble les tâches d'une même mesure : le compilateur a prouvé qu'elles
/// n'écrivent pas les mêmes cases, chaque fil a sa propre zone de pile.
pub struct Memoire {
    // l'étage 0 (le code et la pile, lu à chaque instruction) d'un seul bloc ; les étages 1 à 3 en pages
    pub base0: *mut u32,
    pub pages: Box<[std::sync::atomic::AtomicPtr<u32>; 4 * ETAGE / PAGE]>,
    pub cubes: std::sync::Mutex<std::collections::HashMap<(u32, u32), Vec<*mut u32>>>,
    pub frequences: [std::sync::atomic::AtomicU32; 4],
    pub ecrites: std::cell::UnsafeCell<Vec<u32>>,
    pub suivre: bool,
}

pub const PAGE: usize = 1 << 16;

unsafe impl Sync for Memoire {}
unsafe impl Send for Memoire {}

pub fn page_neuve() -> *mut u32 {
    Box::into_raw(vec![0u32; PAGE].into_boxed_slice()) as *mut u32
}

/// La page nulle, partagée : toute page jamais écrite la désigne, une lecture n'a donc rien à vérifier ; la première
/// écriture non nulle remplace ce pointeur par une vraie page.
pub fn page_nulle() -> *mut u32 {
    static NULLE: std::sync::OnceLock<usize> = std::sync::OnceLock::new();
    *NULLE.get_or_init(|| page_neuve() as usize) as *mut u32
}

pub fn rendre_page(p: *mut u32) {
    if !p.is_null() && p != page_nulle() {
        unsafe { drop(Box::from_raw(std::ptr::slice_from_raw_parts_mut(p, PAGE))) };
    }
}

impl Memoire {
    pub fn new(suivre: bool) -> Self {
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
    pub fn lit_i(&self, i: usize) -> u32 {
        if i < ETAGE {
            return unsafe { *self.base0.add(i) };
        }
        // l'indice tient toujours dans la table (i < 2^26) : pas de contrôle de bornes
        unsafe { *self.pages[(i >> 16) & (4 * ETAGE / PAGE - 1)].load(std::sync::atomic::Ordering::Acquire).add(i & (PAGE - 1)) }
    }
    #[inline(always)]
    pub fn ecrit_i(&self, i: usize, v: u32) {
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
    pub fn effacer(&mut self) {
        let ec = std::mem::take(self.ecrites.get_mut());
        for &i in ec.iter() {
            self.ecrit_i(i as usize, 0);
        }
    }
    /// L'étage 0 (le code, la pile), sans détour : il est d'un seul bloc ; ses écritures ne sont pas suivies (l'état
    /// comparé par le corpus ne porte que sur les étages 1 à 3). Les programmes forgés y rangent leurs cadres.
    #[inline(always)]
    pub fn lit0(&self, a: u32) -> u32 {
        unsafe { *self.base0.add((a & ADR) as usize) }
    }
    #[inline(always)]
    pub fn ecrit0(&self, a: u32, v: u32) {
        unsafe { *self.base0.add((a & ADR) as usize) = v };
    }
    #[inline(always)]
    pub fn lit(&self, e: u32, a: u32) -> u32 {
        self.lit_i(((e as usize & 3) << 24) | (a & ADR) as usize)
    }
    #[inline(always)]
    pub fn ecrit(&self, e: u32, a: u32, v: u32) {
        let i = ((e as usize & 3) << 24) | (a & ADR) as usize;
        if self.suivre {
            unsafe { (*self.ecrites.get()).push(i as u32) };
        }
        self.ecrit_i(i, v);
    }
    pub fn etat(&mut self) -> Vec<(u32, u32)> {
        let mut ec = std::mem::take(self.ecrites.get_mut());
        ec.sort_unstable();
        ec.dedup();
        let r = ec.iter().filter(|&&i| i as usize >= ETAGE && self.lit_i(i as usize) != 0).map(|&i| (i, self.lit_i(i as usize))).collect();
        *self.ecrites.get_mut() = ec;
        r
    }
    /// L'étage e regarde désormais le cube de fréquence f (rend l'ancienne fréquence).
    pub fn accorder(&self, e: u32, f: u32, dossier: Option<&std::path::Path>) -> u32 {
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
                // au-delà du budget de pages en mémoire (VTX_CUBES_PAGES, sans limite par défaut), le cube quitté va au disque
                if let (Some(d), Some(max)) = (dossier, budget_cubes()) {
                    let en_memoire: usize = cubes.values().map(|v| v.iter().filter(|&&p| p != nulle).count()).sum();
                    if en_memoire > max && ecrire_cube(&chemin_cube(d, e, ancienne), &cubes[&(e, ancienne)]).is_ok() {
                        for p in cubes.remove(&(e, ancienne)).unwrap() {
                            rendre_page(p);
                        }
                    }
                }
            }
            if let Some(v) = cubes.remove(&(e, f)) {
                for (k, p) in v.into_iter().enumerate() {
                    self.pages[debut + k].store(p, Release);
                }
            } else if let Some(v) = dossier.and_then(|d| lire_cube(&chemin_cube(d, e, f))) {
                // le cube n'est plus en mémoire : on le retrouve dans son fichier (cube-ÉTAGE-FRÉQUENCE.cub)
                for (k, p) in v.into_iter().enumerate() {
                    self.pages[debut + k].store(p, Release);
                }
            }
        }
        ancienne
    }
    /// Écrit sur disque le cube (e, f) : celui que regarde l'étage, ou un cube rangé (qui quitte alors la mémoire).
    /// Rend le nombre de pages écrites, ou 0xFFFFFFFF.
    pub fn ranger_cube(&self, e: u32, f: u32, dossier: Option<&std::path::Path>) -> u32 {
        let (e, d) = (e & 3, match dossier { Some(d) => d, None => return 0xFFFF_FFFF });
        if e == 0 {
            return 0xFFFF_FFFF;
        }
        let nulle = page_nulle();
        let mut cubes = self.cubes.lock().unwrap();
        let debut = e as usize * (ETAGE / PAGE);
        if self.frequence(e) == f {
            let v: Vec<*mut u32> = (0..ETAGE / PAGE).map(|k| self.pages[debut + k].load(std::sync::atomic::Ordering::Acquire)).collect();
            return match ecrire_cube(&chemin_cube(d, e, f), &v) {
                Ok(n) => n as u32,
                Err(_) => 0xFFFF_FFFF,
            };
        }
        match cubes.get(&(e, f)) {
            None => 0xFFFF_FFFF,
            Some(v) => match ecrire_cube(&chemin_cube(d, e, f), v) {
                Ok(n) => {
                    for p in cubes.remove(&(e, f)).unwrap() {
                        rendre_page(p);
                    }
                    let _ = nulle;
                    n as u32
                }
                Err(_) => 0xFFFF_FFFF,
            },
        }
    }
    /// Les cubes rangés en mémoire (étage, fréquence, pages prises), en plus de ceux que regardent les étages.
    pub fn cubes_rangees(&self) -> Vec<(u32, u32, usize)> {
        let nulle = page_nulle();
        let mut v: Vec<(u32, u32, usize)> =
            self.cubes.lock().unwrap().iter().map(|(&(e, f), p)| (e, f, p.iter().filter(|&&q| q != nulle).count())).collect();
        v.sort_unstable();
        v
    }
    pub fn frequence(&self, e: u32) -> u32 {
        self.frequences[(e & 3) as usize].load(std::sync::atomic::Ordering::Acquire)
    }
    /// Les pages réellement prises (toutes fréquences) : pour mesurer ce que coûte un programme.
    #[allow(dead_code)]
    pub fn pages_prises(&self) -> usize {
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

pub fn budget_cubes() -> Option<usize> {
    env::var("VTX_CUBES_PAGES").ok().and_then(|v| v.parse().ok())
}

/// Le nom de la note quand la fréquence (en hertz) tombe à un demi-ton près sur une note du tempérament égal (la = 440) :
/// 262 donne « do4 », 330 « mi4 », 392 « sol4 ».
pub fn nom_note(f: u32) -> Option<String> {
    if f < 16 {
        return None;
    }
    let demi = 12.0 * (f as f64 / 440.0).log2();
    let n = demi.round();
    if (demi - n).abs() > 0.2 {
        return None;
    }
    let k = n as i32 + 57;                        // demi-tons depuis do0 (la4 = 57)
    let noms = ["do", "do#", "ré", "ré#", "mi", "fa", "fa#", "sol", "sol#", "la", "la#", "si"];
    Some(format!("{}{}", noms[k.rem_euclid(12) as usize], k.div_euclid(12)))
}

/// Les cubes écrits dans un dossier (cube-ÉTAGE-FRÉQUENCE.cub) : (étage, fréquence, octets), triés.
pub fn cubes_sur_disque(d: &std::path::Path) -> Vec<(u32, u32, u64)> {
    let mut v = Vec::new();
    if let Ok(rd) = fs::read_dir(d) {
        for en in rd.flatten() {
            let nom = en.file_name().to_string_lossy().to_string();
            if let Some(r) = nom.strip_prefix("cube-").and_then(|r| r.strip_suffix(".cub")) {
                let mut it = r.splitn(2, '-');
                if let (Some(Ok(e)), Some(Ok(f))) = (it.next().map(|x| x.parse::<u32>()), it.next().map(|x| x.parse::<u32>())) {
                    v.push((e, f, en.metadata().map(|m| m.len()).unwrap_or(0)));
                }
            }
        }
    }
    v.sort_unstable();
    v
}

/// Le tableau des cubes pour l'atelier (commande « cubes ») et pour « vtx cubes DOSSIER ».
pub fn texte_cubes(mem: Option<&Memoire>, d: &std::path::Path) -> String {
    let note = |f: u32| nom_note(f).map(|n| format!(" ({})", n)).unwrap_or_default();
    let mut t = String::new();
    if let Some(m) = mem {
        for e in 1..4u32 {
            t.push_str(&format!("étage {} regarde le cube {}{}\n", e, m.frequence(e), note(m.frequence(e))));
        }
        for (e, f, p) in m.cubes_rangees() {
            t.push_str(&format!("en mémoire : étage {} · cube {}{} · {} page(s) de 65 536 mots\n", e, f, note(f), p));
        }
    }
    for (e, f, o) in cubes_sur_disque(d) {
        t.push_str(&format!("sur disque : cube-{}-{}.cub · étage {} · cube {}{} · {} Ko\n", e, f, e, f, note(f), o / 1024));
    }
    if t.is_empty() {
        t.push_str("aucun cube\n");
    }
    t
}

pub fn chemin_cube(d: &std::path::Path, e: u32, f: u32) -> std::path::PathBuf {
    d.join(format!("cube-{}-{}.cub", e, f))
}

/// Un cube sur disque : « VTXCUB01 », puis pour chaque page non nulle son numéro (u32) et ses 65 536 mots (u32, petit
/// boutiste). Les pages jamais écrites ne prennent pas de place.
pub fn ecrire_cube(chemin: &std::path::Path, pages: &[*mut u32]) -> std::io::Result<usize> {
    use std::io::Write;
    let nulle = page_nulle();
    // le cube est écrit avec son anti-cube (miroir inversé, miroir.rs)
    let mut f: Vec<u8> = Vec::new();
    f.write_all(b"VTXCUB01")?;
    let mut n = 0;
    for (k, &p) in pages.iter().enumerate() {
        if p == nulle || p.is_null() {
            continue;
        }
        let mots = unsafe { std::slice::from_raw_parts(p, PAGE) };
        if mots.iter().all(|&m| m == 0) {
            continue;
        }
        f.write_all(&(k as u32).to_le_bytes())?;
        for &m in mots {
            f.write_all(&m.to_le_bytes())?;
        }
        n += 1;
    }
    miroir::ecrire_double(chemin, &f)?;
    Ok(n)
}

pub fn lire_cube(chemin: &std::path::Path) -> Option<Vec<*mut u32>> {
    let b = miroir::lire_double(chemin, b"VTXCUB01")?;
    if b.len() < 8 || &b[..8] != b"VTXCUB01" {
        return None;
    }
    let mut v = vec![page_nulle(); ETAGE / PAGE];
    let mut i = 8;
    let taille = 4 + PAGE * 4;
    while i + taille <= b.len() {
        let k = u32::from_le_bytes([b[i], b[i + 1], b[i + 2], b[i + 3]]) as usize;
        if k < v.len() {
            let p = page_neuve();
            for j in 0..PAGE {
                let o = i + 4 + 4 * j;
                unsafe { *p.add(j) = u32::from_le_bytes([b[o], b[o + 1], b[o + 2], b[o + 3]]) };
            }
            v[k] = p;
        }
        i += taille;
    }
    Some(v)
}
