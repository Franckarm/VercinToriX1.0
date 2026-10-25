// Lugus, le SPU-128 : la machine rapide (mêmes résultats que la machine de référence spu128/spu128.py). Spécification :
// docs/specification-spu128.md. Un mot = un point de matière #RRRRRRRR_VVVVVVVV_BBBBBBBB_MMMMMMMM ; un mot de code porte
// deux instructions de 64 bits (la première en haut) et PC compte les demi-mots ; chaque instruction a sa largeur w
// (128, 64, 32 bits). Adresse : étage (bits 127-126), type, état, fréquence (119-24), #RRGGBB (23-0). Mémoire en pages
// de 65 536 mots créées à la première écriture, chaque mot avec son quit de brin (libre, ADN, ARN).
use crate::qflot128::{format, Q128, Q32};
use std::collections::{HashMap, VecDeque};

const M120: u128 = (1u128 << 120) - 1;
const M64: u128 = 0xFFFF_FFFF_FFFF_FFFF;
const M32: u128 = 0xFFFF_FFFF;
const PAGE: usize = 65536;
pub const PILE: u128 = 0x7FFF_FFFF;
const V128: u128 = 0xAAAA_AAAA_AAAA_AAAA_AAAA_AAAA_AAAA_AAAA;
const F128: u128 = 0x5555_5555_5555_5555_5555_5555_5555_5555;
pub const ENTETE: &[u8; 8] = b"VTXCU128";
// la voie de matière : (décalage, nombre de bits) des codons 0 (l'état) à 5 (la rugosité)
const CODONS: [(u32, u32); 6] = [(30, 2), (24, 6), (18, 6), (12, 6), (6, 6), (0, 6)];

struct Page {
    mots: Box<[u128]>,
    brins: Option<Box<[u8]>>,
}

pub struct Spu128 {
    pub r: [u128; 16],
    pub pc: u128,
    z: bool,
    c: bool,
    pub arrete: bool,
    pages: [HashMap<u128, Box<Page>>; 4],
    cache: [(u128, *mut Page); 4],
    cache_code: (u128, *mut Page),
    a_des_adn: bool,
    pub entree: VecDeque<u128>,
    pub sortie: Vec<u128>,
    pub texte: Vec<u128>,
    pub texte_entree: VecDeque<u128>,
    fichiers: HashMap<u128, (bool, Vec<u128>, usize, String)>,
    pub dossier: Option<std::path::PathBuf>,
    pages_vues: std::collections::HashSet<(usize, u128)>,
    pub pas: u64,
    pub presenter: Option<Box<dyn FnMut(&Spu128) -> u128>>,
    // la console branchée ailleurs (l'atelier, un terminal) : ce que le programme écrit et lit sur le canal 1 passe
    // par elles au lieu du texte gardé ; arret : Maj+F5 de l'atelier ; parler : la voix (le canal « voix: »)
    pub console_ecrire: Option<Box<dyn FnMut(u128)>>,
    pub console_lire: Option<Box<dyn FnMut() -> u128>>,
    pub arret: Option<&'static std::sync::atomic::AtomicBool>,
    pub parler: Option<fn(&str)>,
}

pub type Resultat = Result<(), String>;

fn masque(l: u32) -> u128 {
    if l == 128 { u128::MAX } else { (1u128 << l) - 1 }
}

fn signe(v: u128, l: u32) -> i128 {
    let v = v & masque(l);
    if l == 128 { v as i128 } else if (v >> (l - 1)) & 1 == 1 { (v | !masque(l)) as i128 } else { v as i128 }
}

fn voies(x: u128) -> [u128; 4] {
    [x & M32, (x >> 32) & M32, (x >> 64) & M32, x >> 96]
}

/// Les quatre voies à la largeur l : de l / 4 bits chacune.
fn voies_l(x: u128, l: u32) -> [u128; 4] {
    if l == 128 {
        return voies(x);
    }
    let b = l / 4;
    let mk = (1u128 << b) - 1;
    [x & mk, (x >> b) & mk, (x >> (2 * b)) & mk, (x >> (3 * b)) & mk]
}

fn de_voies(v: [u128; 4]) -> u128 {
    (v[0] & M32) | ((v[1] & M32) << 32) | ((v[2] & M32) << 64) | ((v[3] & M32) << 96)
}

impl Spu128 {
    pub fn nouveau() -> Spu128 {
        let mut r = [0u128; 16];
        r[14] = PILE;
        Spu128 {
            r,
            pc: 0,
            z: false,
            c: false,
            arrete: false,
            pages: [HashMap::new(), HashMap::new(), HashMap::new(), HashMap::new()],
            cache: [(u128::MAX, std::ptr::null_mut()); 4],
            cache_code: (u128::MAX, std::ptr::null_mut()),
            a_des_adn: false,
            entree: VecDeque::new(),
            sortie: Vec::new(),
            texte: Vec::new(),
            texte_entree: VecDeque::new(),
            fichiers: HashMap::new(),
            dossier: None,
            pages_vues: std::collections::HashSet::new(),
            pas: 0,
            presenter: None,
            console_ecrire: None,
            console_lire: None,
            arret: None,
            parler: None,
        }
    }

    pub fn charger(&mut self, mots: &[u128]) {
        for (i, &w) in mots.iter().enumerate() {
            let p = self.page_mut(0, i as u128);
            p.mots[i % PAGE] = w;
        }
    }

    // --- mémoire
    /// (étage, indice) : adresse courte si les 64 bits hauts sont nuls (étage 63-62, indice 47-0, celle du SPU-64),
    /// longue sinon (étage 127-126, indice 119-0).
    #[inline(always)]
    fn place(adr: u128) -> (usize, u128) {
        if adr >> 64 == 0 {
            ((adr >> 62) as usize, adr & ((1u128 << 48) - 1))
        } else {
            ((adr >> 126) as usize, adr & M120)
        }
    }

    fn page_disque(&mut self, e: usize, i: u128) {
        let dossier = match &self.dossier {
            Some(d) => d.clone(),
            None => return,
        };
        let cle = (e, i >> 16);
        if !self.pages_vues.insert(cle) {
            return;
        }
        let f = i >> 24;
        let b = match crate::miroir::lire_double(&dossier.join(format!("cube128-{}-{}.cub", e, f)), ENTETE) {
            Some(b) => b,
            None => return,
        };
        if b.len() < 8 || &b[..8] != ENTETE {
            return;
        }
        let voulue = (i >> 16) & 255;
        let taille = 4 + PAGE * 16 + PAGE / 4;
        let mut k = 8;
        while k + taille <= b.len() {
            let p = u32::from_le_bytes(b[k..k + 4].try_into().unwrap()) as u128;
            if p == voulue {
                let base = (f << 24) | (p << 16);
                if !self.pages[e].contains_key(&(base >> 16)) {
                    let mut mots = vec![0u128; PAGE].into_boxed_slice();
                    for j in 0..PAGE {
                        mots[j] = u128::from_le_bytes(b[k + 4 + 16 * j..k + 20 + 16 * j].try_into().unwrap());
                    }
                    let br = &b[k + 4 + PAGE * 16..k + taille];
                    let brins = if br.iter().any(|&x| x != 0) {
                        self.a_des_adn = true;
                        Some(br.to_vec().into_boxed_slice())
                    } else {
                        None
                    };
                    self.pages[e].insert(base >> 16, Box::new(Page { mots, brins }));
                    self.cache[e] = (u128::MAX, std::ptr::null_mut());
                    self.cache_code = (u128::MAX, std::ptr::null_mut());
                }
                return;
            }
            k += taille;
        }
    }

    fn page_mut(&mut self, e: usize, i: u128) -> &mut Page {
        let cle = i >> 16;
        if self.cache[e].0 == cle {
            return unsafe { &mut *self.cache[e].1 };
        }
        self.page_disque(e, i);
        let p = self.pages[e]
            .entry(cle)
            .or_insert_with(|| Box::new(Page { mots: vec![0u128; PAGE].into_boxed_slice(), brins: None }));
        let ptr: *mut Page = &mut **p;
        self.cache[e] = (cle, ptr);
        unsafe { &mut *ptr }
    }

    /// Pour la forge : la page d'une adresse (le pointeur sur son premier mot ; elle est créée au besoin), la clé de
    /// la page (étage et numéro) et si des mots de la page ont un brin (ADN ou ARN : l'écriture passe alors par
    /// ecrire_mem, qui les vérifie).
    pub fn page_de(&mut self, adr: u128) -> (*mut u128, u128, bool) {
        let (e, i) = Self::place(adr);
        let p = self.page_mut(e, i);
        let brins = p.brins.is_some();
        (p.mots.as_mut_ptr(), ((e as u128) << 120) | (i >> 16), brins)
    }

    /// La clé de page d'une adresse (étage et numéro de page), comme page_de.
    #[inline(always)]
    pub fn cle_page(adr: u128) -> (u128, usize) {
        let (e, i) = Self::place(adr);
        (((e as u128) << 120) | (i >> 16), (i as usize) & (PAGE - 1))
    }

    pub fn lire(&mut self, adr: u128) -> u128 {
        let (e, i) = Self::place(adr);
        let cle = i >> 16;
        if self.cache[e].0 == cle {
            return unsafe { (*self.cache[e].1).mots[(i as usize) & (PAGE - 1)] };
        }
        self.page_disque(e, i);
        match self.pages[e].get_mut(&cle) {
            Some(p) => {
                let ptr: *mut Page = &mut **p;
                self.cache[e] = (cle, ptr);
                unsafe { (*ptr).mots[(i as usize) & (PAGE - 1)] }
            }
            None => 0,
        }
    }

    /// la demi-instruction n° p : la moitié haute du mot p / 2 si p est pair, la basse sinon
    #[inline]
    fn demi(&mut self, p: u128) -> u64 {
        let i = (p >> 1) & M120;
        let cle = i >> 16;
        let w = if self.cache_code.0 == cle {
            unsafe { (*self.cache_code.1).mots[(i as usize) & (PAGE - 1)] }
        } else {
            self.page_disque(0, i);
            match self.pages[0].get_mut(&cle) {
                Some(pg) => {
                    let ptr: *mut Page = &mut **pg;
                    self.cache_code = (cle, ptr);
                    unsafe { (*ptr).mots[(i as usize) & (PAGE - 1)] }
                }
                None => 0,
            }
        };
        if p & 1 == 0 { (w >> 64) as u64 } else { w as u64 }
    }

    /// Les pages écrites de l'étage e : (le premier indice de la page, ses mots), dans l'ordre (pour les vues).
    pub fn pages_etage(&self, e: usize) -> Vec<(u128, &[u128])> {
        let mut v: Vec<(u128, &[u128])> = self.pages[e].iter().map(|(k, p)| (k << 16, &p.mots[..])).collect();
        v.sort_by_key(|x| x.0);
        v
    }

    pub fn drapeaux(&self) -> (bool, bool) {
        (self.z, self.c)
    }

    /// Un mot lu sans rien changer : pour les vues.
    pub fn regarder(&self, adr: u128) -> u128 {
        let (e, i) = Self::place(adr);
        self.pages[e].get(&(i >> 16)).map(|p| p.mots[(i as usize) & (PAGE - 1)]).unwrap_or(0)
    }

    pub fn brin(&mut self, adr: u128) -> u128 {
        let (e, i) = Self::place(adr);
        self.page_disque(e, i);
        match self.pages[e].get(&(i >> 16)) {
            Some(p) => match &p.brins {
                Some(b) => {
                    let j = (i as usize) & (PAGE - 1);
                    ((b[j / 4] >> (2 * (j % 4))) & 3) as u128
                }
                None => 0,
            },
            None => 0,
        }
    }

    pub fn ecrire_mem(&mut self, adr: u128, v: u128) -> Resultat {
        let (e, i) = Self::place(adr);
        let a_des_adn = self.a_des_adn;
        let p = self.page_mut(e, i);
        let j = (i as usize) & (PAGE - 1);
        if a_des_adn {
            if let Some(b) = &p.brins {
                if (b[j / 4] >> (2 * (j % 4))) & 3 == 1 {
                    return Err(format!("écriture dans un mot ADN (fixé) à l'adresse étage {}, #{:030X}", e, i));
                }
            }
        }
        p.mots[j] = v;
        Ok(())
    }

    pub fn marquer(&mut self, adr: u128, q: u8) {
        let (e, i) = Self::place(adr);
        if q == 1 {
            self.a_des_adn = true;
        }
        let p = self.page_mut(e, i);
        if p.brins.is_none() {
            if q == 0 {
                return;
            }
            p.brins = Some(vec![0u8; PAGE / 4].into_boxed_slice());
        }
        let b = p.brins.as_mut().unwrap();
        let j = (i as usize) & (PAGE - 1);
        b[j / 4] = (b[j / 4] & !(3 << (2 * (j % 4)))) | (q << (2 * (j % 4)));
    }

    // --- registres et drapeaux
    fn ecrire(&mut self, d: usize, v: u128) {
        if d != 0 {
            self.r[d] = v;
        }
    }
    fn poser(&mut self, d: usize, v: u128, c: bool, l: u32) {
        let v = v & masque(l);
        self.ecrire(d, v);
        self.z = v == 0;
        self.c = c;
    }

    // --- canaux et services
    pub fn lire_canal(&mut self, c: u128) -> u128 {
        if c == 0 {
            return self.entree.pop_front().unwrap_or(0);
        }
        if c == 1 {
            if let Some(f) = self.console_lire.as_mut() {
                return f();
            }
            return self.texte_entree.pop_front().unwrap_or(u128::MAX);
        }
        match self.fichiers.get_mut(&c) {
            Some(f) if f.0 && f.2 < f.1.len() => {
                f.2 += 1;
                f.1[f.2 - 1]
            }
            _ => u128::MAX,
        }
    }
    pub fn ecrire_canal(&mut self, c: u128, v: u128) {
        if c == 0 {
            self.sortie.push(v);
        } else if c == 1 {
            match self.console_ecrire.as_mut() {
                Some(f) => f(v),
                None => self.texte.push(v),
            }
        } else if let Some(f) = self.fichiers.get_mut(&c) {
            if !f.0 {
                f.1.push(v);
            }
        }
    }
    fn texte_memoire(&mut self, adr: u128) -> String {
        let n = self.lire(adr).min(4096);
        (0..n).map(|k| char::from_u32((self.lire(adr.wrapping_add(1 + k)) & 0x1F_FFFF) as u32).unwrap_or('?')).collect()
    }
    pub fn service(&mut self, code: u128, arg: u128) -> Result<u128, String> {
        match code {
            1 | 2 => {
                let d = match &self.dossier {
                    Some(d) => d.clone(),
                    None => return Ok(u128::MAX),
                };
                let chemin = d.join(self.texte_memoire(arg));
                let canal = self.fichiers.keys().copied().chain(std::iter::once(1)).max().unwrap() + 1;
                if code == 1 {
                    match std::fs::read_to_string(&chemin) {
                        Ok(t) => {
                            self.fichiers.insert(canal, (true, t.chars().map(|c| c as u128).collect(), 0, String::new()));
                        }
                        Err(_) => return Ok(u128::MAX),
                    }
                } else {
                    self.fichiers.insert(canal, (false, Vec::new(), 0, chemin.to_string_lossy().into_owned()));
                }
                Ok(canal)
            }
            3 => {
                if let Some(f) = self.fichiers.remove(&arg) {
                    if !f.0 {
                        let t: String = f.1.iter().map(|&c| char::from_u32((c & 0x1F_FFFF) as u32).unwrap_or('?')).collect();
                        if std::path::Path::new(&f.3).file_name().map(|n| n == "voix:").unwrap_or(false) {
                            // le canal « voix: » : le texte est dit par la voix de la machine hôte (jamais écrit)
                            if let Some(p) = self.parler {
                                p(&t);
                            }
                            return Ok(0);
                        }
                        if std::fs::write(&f.3, t).is_err() {
                            return Ok(u128::MAX);
                        }
                    }
                }
                Ok(0)
            }
            4 => Ok(match self.fichiers.get(&arg) {
                Some(f) if f.0 && f.2 < f.1.len() => 0,
                _ => 1,
            }),
            5 => {
                use std::hash::{BuildHasher, Hasher};
                let mut h = std::collections::hash_map::RandomState::new().build_hasher();
                h.write_u64(self.pas);
                h.write_u128(std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map(|d| d.as_nanos()).unwrap_or(0));
                let a = h.finish();
                h.write_u64(a);
                Ok(((a as u128) << 64) | h.finish() as u128)
            }
            6 | 7 => {
                let d = match &self.dossier {
                    Some(d) => d.clone(),
                    None => return Ok(u128::MAX),
                };
                let e3 = 3u128 << 126;
                let nom = self.lire(e3 | 14680060);
                let chemin = d.join(self.texte_memoire(nom));
                let a = self.lire(e3 | 14680061);
                let n = self.lire(e3 | 14680062);
                if code == 6 {
                    let mut b = Vec::new();
                    for k in 0..n {
                        b.extend_from_slice(&self.lire(a.wrapping_add(k)).to_le_bytes());
                    }
                    return Ok(if std::fs::write(&chemin, b).is_ok() { n } else { u128::MAX });
                }
                let b = match std::fs::read(&chemin) {
                    Ok(b) => b,
                    Err(_) => return Ok(u128::MAX),
                };
                let k = ((b.len() / 16) as u128).min(n);
                for j in 0..k as usize {
                    let v = u128::from_le_bytes(b[16 * j..16 * j + 16].try_into().unwrap());
                    self.ecrire_mem(a.wrapping_add(j as u128), v)?;
                }
                Ok(k)
            }
            10 => Err("mémoire pleine".into()),
            11 => Ok(self.ranger_cube(arg)),
            13 => Ok(self.jeter_cube(arg)),
            16..=21 | 23 => Ok(crate::hote::service(code as u64, arg as u64, u64::MAX).unwrap_or(0) as u128),
            22 => Ok(crate::miroir::prendre_etat() as u128),
            12 => {
                if let Some(mut f) = self.presenter.take() {
                    let r = f(self);
                    self.presenter = Some(f);
                    Ok(r)
                } else {
                    Ok(0)
                }
            }
            _ => Ok(u128::MAX),
        }
    }

    fn jeter_cube(&mut self, adr: u128) -> u128 {
        let (e, i) = Self::place(adr);
        let f = i >> 24;
        let avant = self.pages[e].len();
        self.pages[e].retain(|k, _| (*k >> 8) != f);
        self.cache_code = (u128::MAX, std::ptr::null_mut());
        for p in 0..256u128 {
            self.pages_vues.insert((e, (f << 8) | p));
        }
        self.cache[e] = (u128::MAX, std::ptr::null_mut());
        (avant - self.pages[e].len()) as u128
    }

    fn ranger_cube(&mut self, adr: u128) -> u128 {
        let (e, i) = Self::place(adr);
        let f = i >> 24;
        let d = match &self.dossier {
            Some(d) => d.clone(),
            None => return u128::MAX,
        };
        let mut cles: Vec<u128> = self.pages[e]
            .iter()
            .filter(|(k, p)| (*k >> 8) == f && (p.mots.iter().any(|&v| v != 0) || p.brins.as_ref().map_or(false, |b| b.iter().any(|&x| x != 0))))
            .map(|(k, _)| *k)
            .collect();
        cles.sort();
        let mut b: Vec<u8> = ENTETE.to_vec();
        for k in &cles {
            let p = &self.pages[e][k];
            b.extend_from_slice(&((k & 255) as u32).to_le_bytes());
            for &v in p.mots.iter() {
                b.extend_from_slice(&v.to_le_bytes());
            }
            match &p.brins {
                Some(br) => b.extend_from_slice(br),
                None => b.extend(std::iter::repeat(0u8).take(PAGE / 4)),
            }
        }
        if crate::miroir::ecrire_double(&d.join(format!("cube128-{}-{}.cub", e, f)), &b).is_err() {
            return u128::MAX;
        }
        cles.len() as u128
    }

    // --- exécution
    pub fn executer(&mut self, max_pas: u64) -> Resultat {
        while !self.arrete {
            if self.pas >= max_pas {
                return Err(format!("limite de {} instructions atteinte", max_pas));
            }
            if self.pas & 0xF_FFFF == 0 {
                if let Some(a) = self.arret {
                    if a.load(std::sync::atomic::Ordering::Relaxed) {
                        return Err("programme arrêté".into());
                    }
                }
            }
            self.pas_unique()?;
        }
        Ok(())
    }

    /// Une opération entière à la largeur 64, calculée en u64 ; faux si elle n'est pas de celles-là (chemin général).
    #[inline(always)]
    fn court64(&mut self, op: u16, d: usize, s: usize, t: usize, h: u64) -> bool {
        let sv = self.r[s] as u64;
        let tv = self.r[t] as u64;
        let si = (h as u32 as i32) as i64 as u64;
        let (v, c) = match op {
            0x01 => sv.overflowing_add(tv),
            0x06 => sv.overflowing_add(si),
            0x02 | 0x07 | 0x0E | 0x0F => {
                let y = if op == 0x02 || op == 0x0E { tv } else { si };
                let x = sv.wrapping_sub(y);
                if (op == 0x02 || op == 0x07) && d != 0 {
                    self.r[d] = x as u128;
                }
                self.z = x == 0;
                self.c = sv < y;
                return true;
            }
            0x03 => (sv.wrapping_mul(tv), false),
            0x14 => (sv & tv, false),
            0x15 => (sv | tv, false),
            0x16 => (sv ^ tv, false),
            0x08 => (sv << (tv & 63), false),
            0x09 => (sv >> (tv & 63), false),
            0x17 => (((sv as i64) >> (tv & 63)) as u64, false),
            0x18 => (si, false),
            0x19 => (h & 0xFFFF_FFFF, false),
            _ => return false,
        };
        if d != 0 {
            self.r[d] = v as u128;
        }
        self.z = v == 0;
        self.c = c;
        true
    }

    pub fn pas_unique(&mut self) -> Resultat {
        let h = self.demi(self.pc);
        let op = (h >> 48) as u16;
        let d = ((h >> 44) & 15) as usize;
        let s = ((h >> 40) & 15) as usize;
        let t = ((h >> 36) & 15) as usize;
        let wl = ((h >> 32) & 15) as u32;
        // le chemin court : les opérations entières à la largeur 64 (l'entier par défaut du langage), en u64
        if wl == 1 && self.court64(op, d, s, t, h) {
            self.pc = (self.pc + 1) & M120;
            self.pas += 1;
            return Ok(());
        }
        let imm = (h & 0xFFFF_FFFF) as u128;
        let si = (imm as u32 as i32) as i128 as u128;
        let l: u32 = match wl {
            0 => 128,
            1 => 64,
            2 => 32,
            _ => return Err(format!("largeur {} refusée à la demi-instruction {}", wl, self.pc)),
        };
        let m = masque(l);
        let (sv, tv, dv) = (self.r[s], self.r[t], self.r[d]);
        let (sm, tm) = (sv & m, tv & m);
        let nq = l / 2;
        let mut suivant = (self.pc + 1) & M120;
        match op {
            0x00 => {}
            0x01 | 0x06 => {
                let y = if op == 0x01 { tm } else { si & m };
                let (x, c) = if l == 128 { sm.overflowing_add(y) } else { let x = sm + y; (x & m, x > m) };
                self.poser(d, x, c, l);
            }
            0x02 | 0x07 | 0x0E | 0x0F => {
                let y = if op == 0x02 || op == 0x0E { tm } else { si & m };
                let x = sm.wrapping_sub(y) & m;
                if op == 0x02 || op == 0x07 {
                    self.ecrire(d, x);
                }
                self.z = x == 0;
                self.c = sm < y;
            }
            0x03 => self.poser(d, sm.wrapping_mul(tm), false, l),
            0x4E => {
                let v = if l == 128 { U256mulhi(sm, tm) } else if l == 64 { (sm * tm) >> 64 } else { (sm * tm) >> 32 };
                self.poser(d, v, false, l);
            }
            0x1E => {
                let (a, b) = (signe(sm, l), signe(tm, l));
                let v = if l == 128 { mulhs128(a, b) } else { ((a * b) >> l) as u128 };
                self.poser(d, v, false, l);
            }
            0x0C => self.poser(d, if tm == 0 { m } else { sm / tm }, false, l),
            0x0D => self.poser(d, if tm == 0 { sm } else { sm % tm }, false, l),
            0x1A | 0x1B => {
                let (a, b) = (signe(sm, l), signe(tm, l));
                let r = if b == 0 {
                    if op == 0x1A { m } else { sm }
                } else {
                    let min = if l == 128 { i128::MIN } else { -(1i128 << (l - 1)) };
                    if a == min && b == -1 {
                        if op == 0x1A { a as u128 } else { 0 }
                    } else if op == 0x1A {
                        (a / b) as u128
                    } else {
                        (a % b) as u128
                    }
                };
                self.poser(d, r, false, l);
            }
            0x04 => self.poser(d, sm << 2, false, l),
            0x05 => self.poser(d, sm >> 2, false, l),
            0x08 => self.poser(d, sm << (tv & (l as u128 - 1)), false, l),
            0x09 => self.poser(d, sm >> (tv & (l as u128 - 1)), false, l),
            0x17 => self.poser(d, (signe(sm, l) >> (tv & (l as u128 - 1))) as u128, false, l),
            0x14 => self.poser(d, sm & tm, false, l),
            0x15 => self.poser(d, sm | tm, false, l),
            0x16 => self.poser(d, sm ^ tm, false, l),
            0x12 => self.poser(d, !sm, false, l),
            0x1C => self.poser(d, sm, false, 128),
            0x1D => self.poser(d, signe(sm, l) as u128, false, 128),
            0x4C => {
                let (x1, c1) = sm.overflowing_add(tm);
                let (x2, c2) = x1.overflowing_add(self.c as u128);
                if l == 128 {
                    self.poser(d, x2, c1 || c2, l);
                } else {
                    let x = sm + tm + self.c as u128;
                    self.poser(d, x, x > m, l);
                }
            }
            0x4D => {
                let c = self.c as u128;
                // l'emprunt : S < T + C (T + C peut valoir 2^128)
                let emprunt = if c == 1 && tm == u128::MAX { true } else { sm < tm + c };
                self.poser(d, sm.wrapping_sub(tm).wrapping_sub(c), emprunt, l);
            }
            0x50 => self.poser(d, sm.count_ones() as u128, false, 128),
            0x0A | 0x2B => {
                let k = self.demi(suivant) as u128;
                let v = if op == 0x0A { k } else { (k << 64) | (dv & M64) };
                self.poser(d, v, false, 128);
                suivant = (suivant + 1) & M120;
            }
            0x18 => self.poser(d, si, false, l),
            0x19 => self.poser(d, imm, false, l),
            0x0B => self.ecrire(d, sv),
            0x1F | 0x22 => {
                let e = if op == 0x1F { imm & 3 } else { tv & 3 };
                self.ecrire(d, (sm & !(3u128 << (l - 2))) | (e << (l - 2)));
            }
            0x10 | 0x11 | 0x13 => {
                let mut r = 0u128;
                for k in 0..nq {
                    let (x, y) = ((sm >> (2 * k)) & 3, (tm >> (2 * k)) & 3);
                    let q = match op {
                        0x10 => x.min(y),
                        0x11 => x.max(y),
                        _ => (x + y) & 3,
                    };
                    r |= q << (2 * k);
                }
                self.poser(d, r, false, l);
            }
            0x4F => {
                let x = sm ^ tm;
                self.poser(d, !(x | (x >> 1)) & F128 & m, false, l);
            }
            0x56 => self.poser(d, ((sm & tm) & V128) | ((sm | tm) & F128), false, l),
            0x57 => self.poser(d, ((sm | tm) & V128) | ((sm & tm) & F128), false, l),
            0x58 | 0x59 => {
                let v = ((sm & V128) >> 1) | ((sm & F128) << 1);
                self.poser(d, if op == 0x59 { v ^ m } else { v }, false, l);
            }
            0x5A => self.poser(d, (sm >> ((tv & (nq as u128 - 1)) * 2)) & 3, false, 128),
            0x54 => {
                let n = nq as u128;
                let v = (self.lire(sv.wrapping_add(tv / n)) >> ((tv % n) * 2)) & 3;
                self.poser(d, v, false, 128);
            }
            0x55 => {
                let n = nq as u128;
                let a = sv.wrapping_add(tv / n);
                let k = (tv % n) * 2;
                let v = (self.lire(a) & !(3u128 << k)) | ((dv & 3) << k);
                self.ecrire_mem(a, v)?;
            }
            0x38 => {
                let (a, b) = (voies_l(sv, l), voies_l(tv, l));
                let v = (0..4).fold(0u128, |acc, k| acc.wrapping_add(a[k] * b[k]));
                self.poser(d, v, false, l);
            }
            0x39 => {
                let sp = self.r[14];
                let lit = |mm: &mut Spu128, j: u128| mm.lire(sp.wrapping_add(4).wrapping_sub(j) & M120);
                let (n, wd, q, k, o) = (lit(self, 0), lit(self, 1), lit(self, 2), lit(self, 3), lit(self, 4));
                let qs: Vec<[u128; 4]> = (0..wd).map(|j| voies_l(self.lire(q.wrapping_add(j)), l)).collect();
                for i in 0..n {
                    let mut acc = 0u128;
                    for j in 0..wd {
                        let p = voies_l(self.lire(k.wrapping_add(i.wrapping_mul(wd)).wrapping_add(j)), l);
                        for mm in 0..4 {
                            acc = acc.wrapping_add(qs[j as usize][mm] * p[mm]);
                        }
                    }
                    self.ecrire_mem(o.wrapping_add(i), acc & m)?;
                }
            }
            0x20 => {
                let v = self.lire(sv.wrapping_add(si));
                self.poser(d, v, false, 128);
            }
            0x21 => self.ecrire_mem(dv.wrapping_add(si), sv)?,
            0x29 => {
                let v = self.lire(sv.wrapping_add(tv));
                self.poser(d, v, false, 128);
            }
            0x2A => self.ecrire_mem(dv.wrapping_add(tv), sv)?,
            0x25 => {
                let v = self.lire(self.r[13].wrapping_add(si) & M120);
                self.poser(d, v, false, 128);
            }
            0x26 => self.ecrire_mem(self.r[13].wrapping_add(si) & M120, dv)?,
            0x27 => {
                self.r[14] = self.r[14].wrapping_sub(1) & M120;
                self.ecrire_mem(self.r[14], sv)?;
            }
            0x28 => {
                let v = self.lire(self.r[14]);
                self.r[14] = (self.r[14] + 1) & M120;
                self.ecrire(d, v);
            }
            0x30 | 0x31 | 0x32 | 0x35 | 0x36 | 0x33 => {
                let saut = match op {
                    0x31 => self.z,
                    0x32 => !self.z,
                    0x35 => self.c,
                    0x36 => !self.c,
                    _ => true,
                };
                if op == 0x33 {
                    self.r[14] = self.r[14].wrapping_sub(1) & M120;
                    self.ecrire_mem(self.r[14], suivant)?;
                }
                if saut {
                    suivant = imm;
                }
            }
            0x34 => {
                suivant = self.lire(self.r[14]) & M120;
                self.r[14] = (self.r[14] + 1) & M120;
            }
            0x23 => {
                let v = self.entree.pop_front().unwrap_or(0);
                self.ecrire(d, v);
            }
            0x24 => self.sortie.push(sv),
            0x51 => {
                let v = self.lire_canal(sv);
                self.poser(d, v, false, l);
            }
            0x52 => self.ecrire_canal(tv, sv),
            0x53 => {
                let v = self.service(sv, tv)?;
                self.poser(d, v, false, l);
            }
            0x5E => {
                let q = (si & 3) as u8;
                let mut k = 0u128;
                while k < tv {
                    self.marquer(sv.wrapping_add(k), q);
                    k += 1;
                }
            }
            0x5F => {
                let v = self.brin(sv);
                self.poser(d, v, false, 128);
            }
            // --- flottants quaternaires (le format par la largeur)
            0x40..=0x4B | 0x5B | 0x5C | 0x5D | 0x6C | 0x6D | 0x6E => {
                let f = format(wl);
                let (a, b) = (sv & f.masque(), tv & f.masque());
                let li = match imm & 3 {
                    1 => 64,
                    2 => 32,
                    _ => 128,
                };
                let v = match op {
                    0x40 => f.add(a, b),
                    0x41 => f.sub(a, b),
                    0x42 => f.mul(a, b),
                    0x43 => f.div(a, b),
                    0x47 => f.racine(a),
                    0x44 => (f.cmp(a, b) == 0) as u128,
                    0x45 => (f.cmp(a, b) == 1) as u128,
                    0x46 => (f.cmp(a, b) < 2) as u128,
                    0x5D => f.cmp(a, b),
                    0x5B => f.neg(a),
                    0x5C => f.etat(a),
                    0x48 => f.de_entier(sv, li, false),
                    0x49 => f.de_entier(sv, li, true),
                    0x4A => f.vers_entier(a, false, li),
                    0x4B => f.vers_entier(a, true, li),
                    0x6E => {
                        let g = format((imm & 3) as u32);
                        g.vers(&f, sv & g.masque())
                    }
                    0x6C => f.vers_ieee(a),
                    _ => f.de_ieee(sv & f.masque()),
                };
                self.poser(d, v, false, 128);
            }
            // --- les voies
            0x80..=0x8B => {
                let (a, b) = (voies(sv), voies(tv));
                let v = match op {
                    0x80 => de_voies([a[0] + b[0], a[1] + b[1], a[2] + b[2], a[3] + b[3]]),
                    0x81 => de_voies([0, 1, 2, 3].map(|k| a[k].wrapping_sub(b[k]))),
                    0x82 => de_voies([0, 1, 2, 3].map(|k| a[k] * b[k])),
                    0x83 => de_voies([0, 1, 2, 3].map(|k| a[k].min(b[k]))),
                    0x84 => de_voies([0, 1, 2, 3].map(|k| a[k].max(b[k]))),
                    0x85 => de_voies([0, 1, 2, 3].map(|k| Q32.add(a[k], b[k]))),
                    0x86 => de_voies([0, 1, 2, 3].map(|k| Q32.sub(a[k], b[k]))),
                    0x87 => de_voies([0, 1, 2, 3].map(|k| Q32.mul(a[k], b[k]))),
                    0x88 => de_voies([0, 1, 2, 3].map(|k| Q32.div(a[k], b[k]))),
                    0x89 => de_voies([sv & M32; 4]),
                    0x8A => a[(tv & 3) as usize],
                    _ => {
                        let mut c = voies(dv);
                        c[(imm & 3) as usize] = sv & M32;
                        de_voies(c)
                    }
                };
                self.poser(d, v, false, 128);
            }
            // --- la matière
            0x90 => {
                let k = (tv & 7) as usize;
                let v = if k < 6 { (sv >> CODONS[k].0) & ((1u128 << CODONS[k].1) - 1) } else { 0 };
                self.poser(d, v, false, 128);
            }
            0x91 => {
                let k = (imm & 7) as usize;
                let v = if k < 6 {
                    let (dec, nb) = CODONS[k];
                    let mk = ((1u128 << nb) - 1) << dec;
                    (sv & !mk) | ((tv << dec) & mk)
                } else {
                    sv
                };
                self.poser(d, v, false, 128);
            }
            0x92 => {
                let p = (imm & 511).min(256);
                let (a, b) = (voies(sv), voies(tv));
                let mel = |x: u128, y: u128| (x * (256 - p) + y * p) >> 8;
                let mut mat = (((a[0] >> 30) | (b[0] >> 30)) & 3) << 30;
                for k in 1..6 {
                    let (dec, _) = CODONS[k];
                    mat |= mel((a[0] >> dec) & 63, (b[0] >> dec) & 63) << dec;
                }
                self.poser(d, de_voies([mat, mel(a[1], b[1]), mel(a[2], b[2]), mel(a[3], b[3])]), false, 128);
            }
            0x93 => self.poser(d, sv ^ (((1u128 << 96) - 1) << 32), false, 128),
            0x3F => self.arrete = true,
            _ => return Err(format!("code d'opération inconnu : {:#06x} à la demi-instruction {}", op, self.pc)),
        }
        self.pc = suivant;
        self.pas += 1;
        Ok(())
    }

    /// « pas|sorties|mémoire (étages 1 à 3)|B:brins|T:texte », comme la machine de référence
    pub fn ligne_corpus(&self) -> String {
        let mut mem: Vec<(u128, u128)> = Vec::new();
        let mut br: Vec<(u128, u128)> = Vec::new();
        for e in 0..4usize {
            for (k, p) in &self.pages[e] {
                for j in 0..PAGE {
                    let cle = ((e as u128) << 120) | (k << 16) | j as u128;
                    if e >= 1 && p.mots[j] != 0 {
                        mem.push((cle, p.mots[j]));
                    }
                    if let Some(b) = &p.brins {
                        let q = (b[j / 4] >> (2 * (j % 4))) & 3;
                        if q != 0 {
                            br.push((cle, q as u128));
                        }
                    }
                }
            }
        }
        mem.sort();
        br.sort();
        let mut s = format!(
            "{}|{}|{}|B:{}",
            self.pas,
            self.sortie.iter().map(|v| v.to_string()).collect::<Vec<_>>().join(","),
            mem.iter().map(|(k, v)| format!("{}:{}", k, v)).collect::<Vec<_>>().join(","),
            br.iter().map(|(k, v)| format!("{}:{}", k, v)).collect::<Vec<_>>().join(",")
        );
        if !self.texte.is_empty() {
            s.push_str("|T:");
            s.push_str(&self.texte.iter().map(|v| v.to_string()).collect::<Vec<_>>().join(","));
        }
        s
    }
}

/// les 128 bits hauts du produit sans signe de deux mots de 128 bits
#[allow(non_snake_case)]
fn U256mulhi(a: u128, b: u128) -> u128 {
    crate::qflot128::U256::mul(a, b).hi
}

/// les 128 bits hauts du produit signé
fn mulhs128(a: i128, b: i128) -> u128 {
    let neg = (a < 0) != (b < 0);
    let p = crate::qflot128::U256::mul(a.unsigned_abs(), b.unsigned_abs());
    if !neg {
        return p.hi;
    }
    // l'opposé sur 256 bits : complément et un
    let lo = (!p.lo).wrapping_add(1);
    let hi = (!p.hi).wrapping_add((lo == 0) as u128);
    hi
}

#[allow(dead_code)]
pub fn q128() -> crate::qflot128::Fmt {
    Q128
}
