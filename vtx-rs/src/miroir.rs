// Les cubes sur disque : le miroir inversé et l'ombre (dans l'ordre des choses : cube, hex, ADN, ARN).
//
// Le miroir inversé. À côté de chaque fichier de cube (cube-E-F.cub au SPU-32, cube64-E-F.cub au SPU-64) s'écrit son
// anti-cube (anticube-E-F.cub, anticube64-E-F.cub, en-tête « VTXANS… ») : l'opposé complet du cube, celui de la
// figure du cube et de l'anti-cube, vu par son centre gris. Les valeurs sont opposées (chaque octet complémenté, comme
// 255 - c pour une couleur) et les places aussi : le mot #RRGGBB est rangé à #(FF-RR)(FF-GG)(FF-BB). Une panne qui
// frappe deux copies identiques de la même façon (une page remise à zéro, un fichier tronqué, le même bit inversé au
// même endroit des deux fichiers) les laisserait d'accord dans l'erreur ; ici, la même place des deux fichiers porte deux
// mots différents du cube (aucun point n'est son propre opposé : 256 est pair), donc toute panne « en mode commun »
// devient deux erreurs distinctes, que l'ombre rectifie. Bit par bit, la paire (copie, anti-copie) est un quit de Belnap.
//
// L'ombre : la troisième voix, qui tranche quand les deux copies se contredisent. Chaque page d'un cube (les mots
// #RRGGBB d'un même RR) a ses colonnes de liaison : pour chaque GG, la colonne des 256 mots BB = 00 à FF. L'ombre d'une
// colonne, ce sont neuf mots, en binaire (ou exclusif) :
//   o0 = le ou exclusif des 256 mots de la colonne ;
//   ok = le ou exclusif des mots dont la coordonnée hex BB a son bit k à 1 (k = 0 à 7).
// La formule intègre le hex : un mot abîmé à BB change o0 de son erreur e, et chaque ok de e ou de 0 selon les bits de
// BB. Relire l'ombre redonne donc à la fois l'erreur (o0) et l'adresse (les ok) : le mot est retrouvé et rectifié par un
// seul ou exclusif, sans autre copie. Une erreur par colonne se corrige ; davantage se voit. Coût : 9 mots par colonne
// de 256, soit 3,5 % du cube, dans un troisième fichier (ombre-E-F.cub, « VTXOMB… »).
//
// À la relecture (le passage de l'ADN rangé à l'ARN de travail), page par page et colonne par colonne :
//   vrai      les deux copies s'accordent (et l'ombre avec elles) ;
//   faux      quelque chose a été réparé : une copie manquante, tronquée ou abîmée, tranchée par l'autre copie ou par
//             l'ombre ; les trois fichiers sont réécrits ;
//   variable  une contradiction que rien ne tranche (pas d'ombre, ou plusieurs erreurs dans une même colonne des deux
//             copies) : la copie est gardée, la contradiction signalée ;
//   inconnu   ni l'une ni l'autre copie.
// etat_disque() (service 22) rend le pire état vu depuis son dernier appel (inconnu < vrai < faux < variable).
use std::collections::BTreeMap;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU8, Ordering};

pub const INCONNU: u8 = 0;
pub const FAUX: u8 = 1;
pub const VRAI: u8 = 2;
pub const VARIABLE: u8 = 3;

static ETAT: AtomicU8 = AtomicU8::new(INCONNU);

fn gravite(e: u8) -> u8 {
    match e {
        VRAI => 1,
        FAUX => 2,
        VARIABLE => 3,
        _ => 0,
    }
}

fn pire(etat: &mut u8, e: u8) {
    if gravite(e) > gravite(*etat) {
        *etat = e;
    }
}

/// Retient un état de lecture (le plus grave l'emporte).
pub fn noter(e: u8) {
    let mut v = ETAT.load(Ordering::Relaxed);
    while gravite(e) > gravite(v) {
        match ETAT.compare_exchange(v, e, Ordering::Relaxed, Ordering::Relaxed) {
            Ok(_) => break,
            Err(x) => v = x,
        }
    }
}

/// Le service 22 : l'état depuis le dernier appel, puis inconnu.
pub fn prendre_etat() -> u8 {
    ETAT.swap(INCONNU, Ordering::Relaxed)
}

fn prefixe(chemin: &Path, avant: &str) -> PathBuf {
    let nom = chemin.file_name().map(|n| n.to_string_lossy().into_owned()).unwrap_or_default();
    chemin.with_file_name(format!("{}{}", avant, nom))
}

/// Le chemin de l'anti-cube : « anti » devant le nom du fichier.
pub fn chemin_anti(chemin: &Path) -> PathBuf {
    prefixe(chemin, "anti")
}

/// Le chemin de l'ombre : « ombre » à la place de « cube » (ombre-1-262.cub, ombre64-1-42.cub).
pub fn chemin_ombre(chemin: &Path) -> PathBuf {
    let nom = chemin.file_name().map(|n| n.to_string_lossy().into_owned()).unwrap_or_default();
    chemin.with_file_name(nom.replacen("cube", "ombre", 1))
}

fn entete_avec(entete: &[u8], quoi: &[u8; 3]) -> Vec<u8> {
    let mut e = entete.to_vec();
    if e.len() >= 6 {
        e[3..6].copy_from_slice(quoi);
    }
    e
}

/// Le format d'un fichier de cube : la taille d'un mot et ce qui suit les mots dans une page (les brins au SPU-64).
#[derive(Clone, Copy)]
struct Format {
    mot: usize,
    suite: usize,
}

const MOTS: usize = 65536;

fn format_de(entete: &[u8]) -> Format {
    if entete == b"VTXCUB64" {
        Format { mot: 8, suite: MOTS / 4 }
    } else {
        Format { mot: 4, suite: 0 }
    }
}

impl Format {
    fn page(&self) -> usize {
        MOTS * self.mot + self.suite
    }
    fn lire_mot(&self, p: &[u8], j: usize) -> u64 {
        let o = j * self.mot;
        let mut v = 0u64;
        for (i, b) in p[o..o + self.mot].iter().enumerate() {
            v |= (*b as u64) << (8 * i);
        }
        v
    }
    fn ecrire_mot(&self, p: &mut [u8], j: usize, v: u64) {
        let o = j * self.mot;
        for i in 0..self.mot {
            p[o + i] = (v >> (8 * i)) as u8;
        }
    }
}

/// Une page vue par le centre du cube : le mot GGBB passe en #FFFF - GGBB (les brins du SPU-64 aussi, quit par quit).
/// Deux fois, la page revient : c'est l'opposé des adresses, comme 255 - c est l'opposé des couleurs.
fn retourner(p: &[u8], f: Format) -> Vec<u8> {
    let mut r = vec![0u8; p.len()];
    for j in 0..MOTS {
        let (o, d) = (j * f.mot, (MOTS - 1 - j) * f.mot);
        r[d..d + f.mot].copy_from_slice(&p[o..o + f.mot]);
    }
    if f.suite > 0 {
        let b = MOTS * f.mot;
        for j in 0..MOTS {
            let q = (p[b + j / 4] >> (2 * (j % 4))) & 3;
            let i = MOTS - 1 - j;
            r[b + i / 4] |= q << (2 * (i % 4));
        }
    }
    r
}

/// Les pages d'un fichier de cube (sans son en-tête) : numéro -> octets de la page.
fn pages_de(corps: &[u8], f: Format) -> BTreeMap<u32, Vec<u8>> {
    let mut m = BTreeMap::new();
    let t = 4 + f.page();
    let mut i = 0;
    while i + t <= corps.len() {
        let k = u32::from_le_bytes([corps[i], corps[i + 1], corps[i + 2], corps[i + 3]]);
        m.insert(k, corps[i + 4..i + t].to_vec());
        i += t;
    }
    m
}

/// L'ombre d'une page : pour chaque colonne GG, les neuf mots o0, o1…o8 (voir plus haut).
fn ombre_page(p: &[u8], f: Format) -> Vec<u64> {
    let mut o = vec![0u64; 256 * 9];
    for gg in 0..256 {
        let c = &mut o[gg * 9..gg * 9 + 9];
        for bb in 0..256 {
            let w = f.lire_mot(p, gg * 256 + bb);
            if w == 0 {
                continue;
            }
            c[0] ^= w;
            for k in 0..8 {
                if bb >> k & 1 == 1 {
                    c[1 + k] ^= w;
                }
            }
        }
    }
    o
}

/// Une colonne relue contre son ombre : juste, rectifiable (le mot BB et son erreur), ou fausse.
enum Colonne {
    Juste,
    Rectifiable(usize, u64),
    Fausse,
}

fn juger(calc: &[u64], lue: &[u64]) -> Colonne {
    let d: Vec<u64> = (0..9).map(|k| calc[k] ^ lue[k]).collect();
    if d.iter().all(|&x| x == 0) {
        return Colonne::Juste;
    }
    if d[0] == 0 {
        // l'erreur est dans l'ombre elle-même si un seul de ses mots diffère
        return if d.iter().filter(|&&x| x != 0).count() == 1 { Colonne::Juste } else { Colonne::Fausse };
    }
    let mut bb = 0;
    for k in 0..8 {
        if d[1 + k] == d[0] {
            bb |= 1 << k;
        } else if d[1 + k] != 0 {
            return Colonne::Fausse;
        }
    }
    Colonne::Rectifiable(bb, d[0])
}

/// Écrit le cube (en-tête de 8 octets, puis les pages), son anti-cube et son ombre.
pub fn ecrire_double(chemin: &Path, octets: &[u8]) -> std::io::Result<()> {
    std::fs::write(chemin, octets)?;
    let entete = &octets[..8.min(octets.len())];
    let f = format_de(entete);
    // l'anti-cube : chaque page à sa place opposée (255 - k), chaque mot à la sienne (#FFFF - GGBB), le tout complémenté
    let mut corps_anti: Vec<u8> = Vec::new();
    let pages = pages_de(&octets[8.min(octets.len())..], f);
    for (k, p) in pages.iter().rev() {
        corps_anti.extend_from_slice(&(255 - (*k & 255)).to_le_bytes());
        corps_anti.extend_from_slice(&retourner(p, f));
    }
    let mut a = entete_avec(entete, b"ANS");
    a.extend(corps_anti.iter().map(|b| !b));
    std::fs::write(chemin_anti(chemin), a)?;
    let mut o = entete_avec(entete, b"OMB");
    for (k, p) in pages_de(&octets[8.min(octets.len())..], f) {
        o.extend_from_slice(&k.to_le_bytes());
        for v in ombre_page(&p, f) {
            o.extend_from_slice(&v.to_le_bytes());
        }
    }
    std::fs::write(chemin_ombre(chemin), o)
}

/// Lit un cube, son anti-cube et son ombre, les accorde page par page et colonne par colonne (voir plus haut) et rend
/// le contenu retenu (en-tête compris), ou None ; ce qui a été réparé est réécrit.
pub fn lire_double(chemin: &Path, entete: &[u8]) -> Option<Vec<u8>> {
    let f = format_de(entete);
    let p = std::fs::read(chemin).ok().filter(|b| b.len() >= 8 && &b[..8] == entete);
    let ea = entete_avec(entete, b"ANS");
    let a = std::fs::read(chemin_anti(chemin)).ok().filter(|b| b.len() >= 8 && b[..8] == ea[..]);
    if p.is_none() && a.is_none() {
        noter(INCONNU);
        return None;
    }
    let eo = entete_avec(entete, b"OMB");
    let ombres: Option<BTreeMap<u32, Vec<u64>>> = std::fs::read(chemin_ombre(chemin)).ok()
        .filter(|b| b.len() >= 8 && b[..8] == eo[..])
        .map(|b| {
            let mut m = BTreeMap::new();
            let t = 4 + 256 * 9 * 8;
            let mut i = 8;
            while i + t <= b.len() {
                let k = u32::from_le_bytes([b[i], b[i + 1], b[i + 2], b[i + 3]]);
                let v = (0..256 * 9).map(|j| u64::from_le_bytes(b[i + 4 + 8 * j..i + 12 + 8 * j].try_into().unwrap())).collect();
                m.insert(k, v);
                i += t;
            }
            m
        });
    let pp = p.as_ref().map(|b| pages_de(&b[8..], f)).unwrap_or_default();
    // l'anti-cube relu : complémenté, puis chaque page et chaque mot remis à leur place (l'opposée de l'opposée)
    let pa: BTreeMap<u32, Vec<u8>> = a.as_ref()
        .map(|b| pages_de(&b[8..].iter().map(|x| !x).collect::<Vec<u8>>(), f).into_iter()
            .map(|(k, p)| (255 - (k & 255), retourner(&p, f))).collect())
        .unwrap_or_default();
    let mut etat = VRAI;
    let mut ombre_fausse = ombres.is_none() && p.is_some() && a.is_some();
    let mut numeros: Vec<u32> = pp.keys().chain(pa.keys()).copied().collect();
    numeros.sort_unstable();
    numeros.dedup();
    let mut corps: Vec<u8> = entete.to_vec();
    for k in numeros {
        let ombre = ombres.as_ref().and_then(|m| m.get(&k));
        let page = match (pp.get(&k), pa.get(&k)) {
            (Some(x), Some(y)) if x == y => {
                if let Some(o) = ombre {
                    if ombre_page(x, f) != *o {
                        ombre_fausse = true; // les deux copies s'accordent : c'est l'ombre qui est refaite
                    }
                }
                x.clone()
            }
            (x, y) => {
                pire(&mut etat, FAUX);
                match ombre {
                    None => match (x, y) {
                        (Some(x), Some(_)) => {
                            pire(&mut etat, VARIABLE);
                            x.clone()
                        }
                        (Some(x), None) => x.clone(),
                        (None, Some(y)) => y.clone(),
                        (None, None) => continue,
                    },
                    Some(o) => {
                        // colonne par colonne : la copie juste, sinon la copie que l'ombre rectifie
                        let cx = x.map(|x| ombre_page(x, f));
                        let cy = y.map(|y| ombre_page(y, f));
                        let mut r = x.or(y).unwrap().clone();
                        for gg in 0..256 {
                            let lue = &o[gg * 9..gg * 9 + 9];
                            let jx = cx.as_ref().map(|c| juger(&c[gg * 9..gg * 9 + 9], lue));
                            let jy = cy.as_ref().map(|c| juger(&c[gg * 9..gg * 9 + 9], lue));
                            let copier = |r: &mut Vec<u8>, s: &[u8]| {
                                let d = gg * 256 * f.mot;
                                r[d..d + 256 * f.mot].copy_from_slice(&s[d..d + 256 * f.mot]);
                            };
                            match (jx, jy) {
                                (Some(Colonne::Juste), _) => copier(&mut r, x.unwrap()),
                                (_, Some(Colonne::Juste)) => copier(&mut r, y.unwrap()),
                                (Some(Colonne::Rectifiable(bb, e)), _) => {
                                    copier(&mut r, x.unwrap());
                                    let j = gg * 256 + bb;
                                    let v = f.lire_mot(&r, j) ^ e;
                                    f.ecrire_mot(&mut r, j, v);
                                }
                                (_, Some(Colonne::Rectifiable(bb, e))) => {
                                    copier(&mut r, y.unwrap());
                                    let j = gg * 256 + bb;
                                    let v = f.lire_mot(&r, j) ^ e;
                                    f.ecrire_mot(&mut r, j, v);
                                }
                                _ => pire(&mut etat, VARIABLE),
                            }
                        }
                        // ce qui suit les mots (les brins) : celui de la copie, sinon de l'anti-copie
                        if let (Some(x), Some(y)) = (x, y) {
                            if x[MOTS * f.mot..] != y[MOTS * f.mot..] {
                                pire(&mut etat, VARIABLE);
                            }
                        }
                        r
                    }
                }
            }
        };
        corps.extend_from_slice(&k.to_le_bytes());
        corps.extend_from_slice(&page);
    }
    if etat == VRAI && ombre_fausse && ombres.is_some() {
        etat = FAUX;
    }
    // ce qui a été réparé est réécrit : les trois fichiers redeviennent d'accord (une ombre absente est ajoutée) ; une
    // contradiction que rien n'a tranchée est laissée sur le disque, telle quelle, pour qu'on puisse l'examiner
    if etat == FAUX || (etat == VRAI && ombre_fausse) {
        let _ = ecrire_double(chemin, &corps);
    }
    noter(etat);
    Some(corps)
}
