// SPU-64 : la machine rapide (mêmes résultats que la machine de référence spu64/spu64.py). Spécification :
// docs/specification-spu64.md. Un mot = un point profond #RRRRGGGGBBBBAAAA ; adresse longue : étage (bits 63-62),
// fréquence (47-24), #RRGGBB (23-0). Mémoire en pages de 65 536 mots créées à la première écriture, chaque mot avec
// son quit de brin (libre, ADN, ARN).
use crate::qflot::{self, Q32, Q64};
use std::collections::{HashMap, VecDeque};

const M48: u64 = (1u64 << 48) - 1;
const PAGE: usize = 65536;
pub const PILE: u64 = 0x7FFF_FFFF;

struct Page {
    mots: Box<[u64]>,
    brins: Option<Box<[u8]>>, // 4 quits par octet, le premier dans les bits bas
}

pub struct Spu64 {
    pub r: [u64; 16],
    pub pc: u64,
    z: bool,
    c: bool,
    pub arrete: bool,
    pages: [HashMap<u64, Box<Page>>; 4],
    cache: [(u64, *mut Page); 4],
    // la page du code (étage 0) a son propre cache : la pile, à l'étage 0 elle aussi, ne la chasse pas
    cache_code: (u64, *mut Page),
    a_des_adn: bool,
    pub entree: VecDeque<u64>,
    pub sortie: Vec<u64>,
    pub texte: Vec<u64>,
    pub texte_entree: VecDeque<u64>,
    fichiers: HashMap<u64, (bool, Vec<u64>, usize, String)>,
    pub dossier: Option<std::path::PathBuf>,
    pages_vues: std::collections::HashSet<(usize, u64)>,
    pub pas: u64,
    pub presenter: Option<Box<dyn FnMut(&Spu64) -> u64>>,
    // la console du programme (canal 1) branchée ailleurs (le terminal de l'atelier, le clavier) ; sinon, texte et
    // texte_entree
    pub console_ecrire: Option<Box<dyn FnMut(u64)>>,
    pub console_lire: Option<Box<dyn FnMut() -> u64>>,
    // demande d'arrêt (regardée toutes les 2^20 instructions) et voix de la machine hôte (le canal « voix: »)
    pub arret: Option<&'static std::sync::atomic::AtomicBool>,
    pub parler: Option<fn(&str)>,
}

pub type Resultat = Result<(), String>;

impl Spu64 {
    pub fn nouveau() -> Spu64 {
        let mut r = [0u64; 16];
        r[14] = PILE;
        Spu64 {
            r,
            pc: 0,
            z: false,
            c: false,
            arrete: false,
            pages: [HashMap::new(), HashMap::new(), HashMap::new(), HashMap::new()],
            cache: [(u64::MAX, std::ptr::null_mut()); 4],
            cache_code: (u64::MAX, std::ptr::null_mut()),
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

    pub fn charger(&mut self, mots: &[u64]) {
        for (i, &w) in mots.iter().enumerate() {
            let p = self.page_mut(0, i as u64);
            p.mots[i % PAGE] = w;
        }
    }

    // --- mémoire
    fn place(adr: u64) -> (usize, u64) {
        ((adr >> 62) as usize, adr & M48)
    }

    fn page_disque(&mut self, e: usize, i: u64) {
        let dossier = match &self.dossier {
            Some(d) => d.clone(),
            None => return,
        };
        let cle = (e, i >> 16);
        if !self.pages_vues.insert(cle) {
            return;
        }
        let f = i >> 24;
        let b = match std::fs::read(dossier.join(format!("cube64-{}-{}.cub", e, f))) {
            Ok(b) => b,
            Err(_) => return,
        };
        if b.len() < 8 || &b[..8] != b"VTXCUB64" {
            return;
        }
        let voulue = (i >> 16) & 255;
        let taille = 4 + PAGE * 8 + PAGE / 4;
        let mut k = 8;
        while k + taille <= b.len() {
            let p = u32::from_le_bytes(b[k..k + 4].try_into().unwrap()) as u64;
            if p == voulue {
                let base = (f << 24) | (p << 16);
                let existe = self.pages[e].contains_key(&(base >> 16));
                if !existe {
                    let mut mots = vec![0u64; PAGE].into_boxed_slice();
                    for j in 0..PAGE {
                        mots[j] = u64::from_le_bytes(b[k + 4 + 8 * j..k + 12 + 8 * j].try_into().unwrap());
                    }
                    let br = &b[k + 4 + PAGE * 8..k + taille];
                    let brins = if br.iter().any(|&x| x != 0) {
                        self.a_des_adn = true;
                        Some(br.to_vec().into_boxed_slice())
                    } else {
                        None
                    };
                    self.pages[e].insert(base >> 16, Box::new(Page { mots, brins }));
                    self.cache[e] = (u64::MAX, std::ptr::null_mut());
                    self.cache_code = (u64::MAX, std::ptr::null_mut());
                }
                return;
            }
            k += taille;
        }
    }

    fn page_mut(&mut self, e: usize, i: u64) -> &mut Page {
        let cle = i >> 16;
        if self.cache[e].0 == cle {
            return unsafe { &mut *self.cache[e].1 };
        }
        self.page_disque(e, i);
        let p = self.pages[e]
            .entry(cle)
            .or_insert_with(|| Box::new(Page { mots: vec![0u64; PAGE].into_boxed_slice(), brins: None }));
        let ptr: *mut Page = &mut **p;
        self.cache[e] = (cle, ptr);
        unsafe { &mut *ptr }
    }

    pub fn lire(&mut self, adr: u64) -> u64 {
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

    #[inline]
    fn lire_code(&mut self, pc: u64) -> u64 {
        let cle = pc >> 16;
        if self.cache_code.0 == cle {
            return unsafe { (*self.cache_code.1).mots[(pc as usize) & (PAGE - 1)] };
        }
        self.page_disque(0, pc);
        match self.pages[0].get_mut(&cle) {
            Some(p) => {
                let ptr: *mut Page = &mut **p;
                self.cache_code = (cle, ptr);
                unsafe { (*ptr).mots[(pc as usize) & (PAGE - 1)] }
            }
            None => 0,
        }
    }

    /// Les pages écrites de l'étage e : (adresse longue de leur premier mot, leurs 65 536 mots), pour les vues de
    /// l'atelier.
    pub fn pages_etage(&self, e: usize) -> Vec<(u64, &[u64])> {
        let mut v: Vec<(u64, &[u64])> = self.pages[e].iter().map(|(k, p)| (((e as u64) << 62) | (k << 16), &p.mots[..])).collect();
        v.sort_by_key(|x| x.0);
        v
    }

    /// Un mot lu sans rien changer (ni cache, ni page sortie du disque) : pour le panneau du pas à pas.
    pub fn regarder(&self, adr: u64) -> u64 {
        let (e, i) = Self::place(adr);
        self.pages[e].get(&(i >> 16)).map(|p| p.mots[(i as usize) & (PAGE - 1)]).unwrap_or(0)
    }

    pub fn drapeaux(&self) -> (bool, bool) {
        (self.z, self.c)
    }

    pub fn brin(&mut self, adr: u64) -> u64 {
        let (e, i) = Self::place(adr);
        self.page_disque(e, i);
        match self.pages[e].get(&(i >> 16)) {
            Some(p) => match &p.brins {
                Some(b) => {
                    let j = (i as usize) & (PAGE - 1);
                    ((b[j / 4] >> (2 * (j % 4))) & 3) as u64
                }
                None => 0,
            },
            None => 0,
        }
    }

    pub fn ecrire_mem(&mut self, adr: u64, v: u64) -> Resultat {
        let (e, i) = Self::place(adr);
        let a_des_adn = self.a_des_adn;
        let p = self.page_mut(e, i);
        let j = (i as usize) & (PAGE - 1);
        if a_des_adn {
            if let Some(b) = &p.brins {
                if (b[j / 4] >> (2 * (j % 4))) & 3 == 1 {
                    return Err(format!("écriture dans un mot ADN (fixé) à l'adresse étage {}, #{:012X}", e, i));
                }
            }
        }
        p.mots[j] = v;
        Ok(())
    }

    fn marquer(&mut self, adr: u64, q: u8) {
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
    fn ecrire(&mut self, d: usize, v: u64) {
        if d != 0 {
            self.r[d] = v;
        }
    }
    fn poser(&mut self, d: usize, v: u64) {
        self.ecrire(d, v);
        self.z = v == 0;
        self.c = false;
    }
    fn poser_c(&mut self, d: usize, v: u64, c: bool) {
        self.ecrire(d, v);
        self.z = v == 0;
        self.c = c;
    }

    // --- canaux et services
    fn lire_canal(&mut self, c: u64) -> u64 {
        if c == 0 {
            return self.entree.pop_front().unwrap_or(0);
        }
        if c == 1 {
            if let Some(f) = self.console_lire.as_mut() {
                return f();
            }
            return self.texte_entree.pop_front().unwrap_or(u64::MAX);
        }
        match self.fichiers.get_mut(&c) {
            Some(f) if f.0 && f.2 < f.1.len() => {
                f.2 += 1;
                f.1[f.2 - 1]
            }
            _ => u64::MAX,
        }
    }
    fn ecrire_canal(&mut self, c: u64, v: u64) {
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
    fn texte_memoire(&mut self, adr: u64) -> String {
        let n = self.lire(adr).min(4096);
        (0..n).map(|k| char::from_u32((self.lire(adr.wrapping_add(1 + k)) & 0x1F_FFFF) as u32).unwrap_or('?')).collect()
    }
    fn service(&mut self, code: u64, arg: u64) -> Result<u64, String> {
        match code {
            1 | 2 => {
                let d = match &self.dossier {
                    Some(d) => d.clone(),
                    None => return Ok(u64::MAX),
                };
                let chemin = d.join(self.texte_memoire(arg));
                let canal = self.fichiers.keys().copied().chain(std::iter::once(1)).max().unwrap() + 1;
                if code == 1 {
                    match std::fs::read_to_string(&chemin) {
                        Ok(t) => {
                            self.fichiers.insert(canal, (true, t.chars().map(|c| c as u64).collect(), 0, String::new()));
                        }
                        Err(_) => return Ok(u64::MAX),
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
                            // le canal « voix: » : le texte est dit par la voix de la machine hôte (jamais écrit sur
                            // le disque : « : » est interdit dans un nom de fichier Windows)
                            if let Some(p) = self.parler {
                                p(&t);
                            }
                            return Ok(0);
                        }
                        if std::fs::write(&f.3, t).is_err() {
                            return Ok(u64::MAX);
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
                Ok(h.finish())
            }
            6 | 7 => {
                // écrire ou lire un bloc de mots (nom, adresse longue et nombre en @3[14680060..14680062]) ; huit octets
                // par mot, petit-boutiste
                let d = match &self.dossier {
                    Some(d) => d.clone(),
                    None => return Ok(u64::MAX),
                };
                let e3 = 3u64 << 62;
                let nom = self.lire(e3 | 14680060);
                let chemin = d.join(self.texte_memoire(nom));
                let a = self.lire(e3 | 14680061);
                let n = self.lire(e3 | 14680062);
                if code == 6 {
                    let mut b = Vec::with_capacity((n as usize).min(1 << 26) * 8);
                    for k in 0..n {
                        b.extend_from_slice(&self.lire(a.wrapping_add(k)).to_le_bytes());
                    }
                    return Ok(if std::fs::write(&chemin, b).is_ok() { n } else { u64::MAX });
                }
                let b = match std::fs::read(&chemin) {
                    Ok(b) => b,
                    Err(_) => return Ok(u64::MAX),
                };
                let k = ((b.len() / 8) as u64).min(n);
                for j in 0..k as usize {
                    let v = u64::from_le_bytes(b[8 * j..8 * j + 8].try_into().unwrap());
                    self.ecrire_mem(a.wrapping_add(j as u64), v)?;
                }
                Ok(k)
            }
            10 => Err("mémoire pleine".into()),
            11 => Ok(self.ranger_cube(arg)),
            13 => Ok(self.jeter_cube(arg)),
            12 => {
                if let Some(mut f) = self.presenter.take() {
                    let r = f(self);
                    self.presenter = Some(f);
                    Ok(r)
                } else {
                    Ok(0)
                }
            }
            _ => Ok(u64::MAX),
        }
    }

    // le cube de transfert jetable : ses pages quittent la mémoire d'un coup, sans être relues du disque
    fn jeter_cube(&mut self, adr: u64) -> u64 {
        let (e, i) = Self::place(adr);
        let f = i >> 24;
        let avant = self.pages[e].len();
        self.pages[e].retain(|k, _| (*k >> 8) != f);
        self.cache_code = (u64::MAX, std::ptr::null_mut());
        for p in 0..256u64 {
            self.pages_vues.insert((e, (f << 8) | p));
        }
        self.cache[e] = (u64::MAX, std::ptr::null_mut());
        (avant - self.pages[e].len()) as u64
    }

    fn ranger_cube(&mut self, adr: u64) -> u64 {
        let (e, i) = Self::place(adr);
        let f = i >> 24;
        let d = match &self.dossier {
            Some(d) => d.clone(),
            None => return u64::MAX,
        };
        let mut cles: Vec<u64> = self.pages[e]
            .iter()
            .filter(|(k, p)| (*k >> 8) == f && (p.mots.iter().any(|&v| v != 0) || p.brins.as_ref().map_or(false, |b| b.iter().any(|&x| x != 0))))
            .map(|(k, _)| *k)
            .collect();
        cles.sort();
        let mut b: Vec<u8> = b"VTXCUB64".to_vec();
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
        if std::fs::write(d.join(format!("cube64-{}-{}.cub", e, f)), b).is_err() {
            return u64::MAX;
        }
        cles.len() as u64
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

    pub fn pas_unique(&mut self) -> Resultat {
        let w = self.lire_code(self.pc);
        let op = (w >> 48) as u16;
        let d = ((w >> 44) & 15) as usize;
        let s = ((w >> 40) & 15) as usize;
        let t = ((w >> 36) & 15) as usize;
        let imm = w & 0xFFFF_FFFF;
        let si = (imm as u32 as i32) as i64 as u64;
        let (sv, tv, dv) = (self.r[s], self.r[t], self.r[d]);
        let mut suivant = (self.pc + 1) & M48;
        match op {
            0x00 => {}
            0x01 | 0x06 => {
                let y = if op == 0x01 { tv } else { si };
                let (x, c) = sv.overflowing_add(y);
                self.poser_c(d, x, c);
            }
            0x02 | 0x07 | 0x0E | 0x0F => {
                let y = if op == 0x02 || op == 0x0E { tv } else { si };
                let x = sv.wrapping_sub(y);
                if op == 0x02 || op == 0x07 {
                    self.ecrire(d, x);
                }
                self.z = x == 0;
                self.c = sv < y;
            }
            0x03 => self.poser(d, sv.wrapping_mul(tv)),
            0x4E => self.poser(d, ((sv as u128 * tv as u128) >> 64) as u64),
            0x1E => self.poser(d, (((sv as i64 as i128) * (tv as i64 as i128)) >> 64) as u64),
            0x0C => self.poser(d, if tv == 0 { u64::MAX } else { sv / tv }),
            0x0D => self.poser(d, if tv == 0 { sv } else { sv % tv }),
            0x1A | 0x1B => {
                let (a, b) = (sv as i64, tv as i64);
                let r = if b == 0 {
                    if op == 0x1A { u64::MAX } else { sv }
                } else if op == 0x1A {
                    a.wrapping_div(b) as u64
                } else {
                    a.wrapping_rem(b) as u64
                };
                self.poser(d, r);
            }
            0x04 => self.poser(d, sv << 2),
            0x05 => self.poser(d, sv >> 2),
            0x08 => self.poser(d, sv << (tv & 63)),
            0x09 => self.poser(d, sv >> (tv & 63)),
            0x17 => self.poser(d, ((sv as i64) >> (tv & 63)) as u64),
            0x14 => self.poser(d, sv & tv),
            0x15 => self.poser(d, sv | tv),
            0x16 => self.poser(d, sv ^ tv),
            0x12 => self.poser(d, !sv),
            0x0A => {
                let v = self.lire(suivant);
                self.poser(d, v);
                suivant = (suivant + 1) & M48;
            }
            0x18 => self.poser(d, si),
            0x19 => self.poser(d, imm),
            0x0B => self.ecrire(d, sv),
            0x1F => self.ecrire(d, (sv & !(3u64 << 62)) | ((imm as u64 & 3) << 62)),
            0x22 => self.ecrire(d, (sv & !(3u64 << 62)) | ((tv & 3) << 62)),
            0x1C => self.poser(d, sv & 0xFFFF_FFFF),
            0x1D => self.poser(d, (sv as u32 as i32) as i64 as u64),
            0x4C => {
                let x = sv as u128 + tv as u128 + self.c as u128;
                self.poser_c(d, x as u64, x >> 64 != 0);
            }
            0x4D => {
                let y = tv as u128 + self.c as u128;
                self.poser_c(d, (sv as u128).wrapping_sub(y) as u64, (sv as u128) < y);
            }
            0x50 => self.poser(d, sv.count_ones() as u64),
            0x10 | 0x11 | 0x13 => {
                let mut r = 0u64;
                for k in 0..32 {
                    let (x, y) = ((sv >> (2 * k)) & 3, (tv >> (2 * k)) & 3);
                    let q = match op {
                        0x10 => x.min(y),
                        0x11 => x.max(y),
                        _ => (x + y) & 3,
                    };
                    r |= q << (2 * k);
                }
                self.poser(d, r);
            }
            0x4F => {
                let x = sv ^ tv;
                self.poser(d, !(x | (x >> 1)) & 0x5555_5555_5555_5555);
            }
            0x56 => self.poser(d, ((sv & tv) & 0xAAAA_AAAA_AAAA_AAAA) | ((sv | tv) & 0x5555_5555_5555_5555)),
            0x57 => self.poser(d, ((sv | tv) & 0xAAAA_AAAA_AAAA_AAAA) | ((sv & tv) & 0x5555_5555_5555_5555)),
            0x58 | 0x59 => {
                let v = ((sv & 0xAAAA_AAAA_AAAA_AAAA) >> 1) | ((sv & 0x5555_5555_5555_5555) << 1);
                self.poser(d, if op == 0x59 { !v } else { v });
            }
            0x5A => self.poser(d, (sv >> ((tv & 31) * 2)) & 3),
            0x54 => {
                let v = (self.lire(sv.wrapping_add(tv >> 5)) >> ((tv & 31) * 2)) & 3;
                self.poser(d, v);
            }
            0x55 => {
                let a = sv.wrapping_add(tv >> 5);
                let k = (tv & 31) * 2;
                let v = (self.lire(a) & !(3u64 << k)) | ((dv & 3) << k);
                self.ecrire_mem(a, v)?;
            }
            0x38 => {
                let mut acc = 0u64;
                for k in 0..4 {
                    acc = acc.wrapping_add(((sv >> (16 * k)) & 0xFFFF) * ((tv >> (16 * k)) & 0xFFFF));
                }
                self.poser(d, acc);
            }
            0x39 => {
                let sp = self.r[14];
                let lit = |m: &mut Spu64, j: u64| m.lire(sp.wrapping_add(4 - j) & M48);
                let (n, wd, q, k, o) = (lit(self, 0), lit(self, 1), lit(self, 2), lit(self, 3), lit(self, 4));
                let qs: Vec<u64> = (0..wd).map(|j| self.lire(q.wrapping_add(j))).collect();
                for i in 0..n {
                    let mut acc = 0u64;
                    for j in 0..wd {
                        let p = self.lire(k.wrapping_add(i.wrapping_mul(wd)).wrapping_add(j));
                        for m in 0..4 {
                            acc = acc.wrapping_add(((qs[j as usize] >> (16 * m)) & 0xFFFF) * ((p >> (16 * m)) & 0xFFFF));
                        }
                    }
                    self.ecrire_mem(o.wrapping_add(i), acc)?;
                }
            }
            0x20 => {
                let v = self.lire(sv.wrapping_add(si));
                self.poser(d, v);
            }
            0x21 => self.ecrire_mem(dv.wrapping_add(si), sv)?,
            0x29 => {
                let v = self.lire(sv.wrapping_add(tv));
                self.poser(d, v);
            }
            0x2A => self.ecrire_mem(dv.wrapping_add(tv), sv)?,
            0x25 => {
                let v = self.lire(self.r[13].wrapping_add(si) & M48);
                self.poser(d, v);
            }
            0x26 => self.ecrire_mem(self.r[13].wrapping_add(si) & M48, dv)?,
            0x27 => {
                self.r[14] = self.r[14].wrapping_sub(1) & M48;
                self.ecrire_mem(self.r[14], sv)?;
            }
            0x28 => {
                let v = self.lire(self.r[14]);
                self.r[14] = (self.r[14] + 1) & M48;
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
                    self.r[14] = self.r[14].wrapping_sub(1) & M48;
                    self.ecrire_mem(self.r[14], suivant)?;
                }
                if saut {
                    suivant = imm;
                }
            }
            0x34 => {
                suivant = self.lire(self.r[14]) & M48;
                self.r[14] = (self.r[14] + 1) & M48;
            }
            0x23 => {
                let v = self.entree.pop_front().unwrap_or(0);
                self.ecrire(d, v);
            }
            0x24 => self.sortie.push(sv),
            0x51 => {
                let v = self.lire_canal(sv);
                self.poser(d, v);
            }
            0x52 => self.ecrire_canal(tv, sv),
            0x53 => {
                let v = self.service(sv, tv)?;
                self.poser(d, v);
            }
            0x5E => {
                let q = (si & 3) as u8;
                for k in 0..tv {
                    self.marquer(sv.wrapping_add(k), q);
                }
            }
            0x5F => {
                let v = self.brin(sv);
                self.poser(d, v);
            }
            0x40 => self.poser(d, Q64.add(sv, tv)),
            0x41 => self.poser(d, Q64.sub(sv, tv)),
            0x42 => self.poser(d, Q64.mul(sv, tv)),
            0x43 => self.poser(d, Q64.div(sv, tv)),
            0x47 => self.poser(d, Q64.racine(sv)),
            0x44 => self.poser(d, (Q64.cmp(sv, tv) == 0) as u64),
            0x45 => self.poser(d, (Q64.cmp(sv, tv) == 1) as u64),
            0x46 => self.poser(d, (Q64.cmp(sv, tv) < 2) as u64),
            0x5D => self.poser(d, Q64.cmp(sv, tv)),
            0x5B => self.poser(d, Q64.neg(sv)),
            0x5C => self.poser(d, Q64.etat(sv)),
            0x48 => self.poser(d, Q64.de_entier(sv, false)),
            0x49 => self.poser(d, Q64.de_entier(sv, true)),
            0x4A => self.poser(d, Q64.vers_entier(sv, false)),
            0x4B => self.poser(d, Q64.vers_entier(sv, true)),
            0x6C => self.poser(d, qflot::vers_ieee64(sv)),
            0x6D => self.poser(d, qflot::de_ieee64(sv)),
            0x60..=0x6A => {
                let (a, b) = (sv & 0xFFFF_FFFF, tv & 0xFFFF_FFFF);
                let v = match op {
                    0x60 => Q32.add(a, b),
                    0x61 => Q32.sub(a, b),
                    0x62 => Q32.mul(a, b),
                    0x63 => Q32.div(a, b),
                    0x67 => Q32.racine(a),
                    0x64 => (Q32.cmp(a, b) == 0) as u64,
                    0x65 => (Q32.cmp(a, b) == 1) as u64,
                    0x66 => (Q32.cmp(a, b) < 2) as u64,
                    0x6A => Q32.neg(a),
                    0x68 => Q32.vers(&Q64, a),
                    _ => Q64.vers(&Q32, sv),
                };
                self.poser(d, v);
            }
            0x3F => self.arrete = true,
            _ => return Err(format!("code d'opération inconnu : {:#06x} à l'adresse {}", op, self.pc)),
        }
        self.pc = suivant;
        self.pas += 1;
        Ok(())
    }

    /// « pas|sorties|mémoire (étages 1 à 3)|B:brins|T:texte », comme la machine de référence
    pub fn ligne_corpus(&self) -> String {
        let mut mem: Vec<(u64, u64)> = Vec::new();
        let mut br: Vec<(u64, u64)> = Vec::new();
        for e in 0..4usize {
            for (k, p) in &self.pages[e] {
                for j in 0..PAGE {
                    let cle = ((e as u64) << 48) | (k << 16) | j as u64;
                    if e >= 1 && p.mots[j] != 0 {
                        mem.push((cle, p.mots[j]));
                    }
                    if let Some(b) = &p.brins {
                        let q = (b[j / 4] >> (2 * (j % 4))) & 3;
                        if q != 0 {
                            br.push((cle, q as u64));
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
