// Noyau des programmes forgés pour Lugus (forge/forge128.py) : la machine autour du programme vtx. La mémoire, le
// brin, les cubes sur disque, les canaux et les services sont ceux de la machine Rust de Lugus (spu128.rs, avec
// qflot128.rs pour les flottants quaternaires, miroir.rs et hote.rs), recopiés ici tels quels à la place de la ligne des modules
// (plus bas). Suivent les opérations de Lugus à la largeur 64 et 32 (le sens exact des instructions), puis le programme
// lui-même : une fonction Rust par fonction vtx.

// @MODULES@

use qflot128::{Q128, Q32, Q64};
use spu128::Spu128;

const M64: u128 = 0xFFFF_FFFF_FFFF_FFFF;
const M32: u128 = 0xFFFF_FFFF;
const V64: u64 = 0xAAAA_AAAA_AAAA_AAAA;
const F64: u64 = 0x5555_5555_5555_5555;

/// La machine : la mémoire de Lugus (et ses canaux), le sommet de la pile (R14).
struct Ctx {
    m: Spu128,
    sp: u128,
    // les pages vues : 16 cases (par le numéro de page), leur clé et le pointeur sur leur premier mot ; pour l'écriture,
    // seulement les pages sans brin (les autres passent par ecrire_mem, qui vérifie l'ADN)
    cl: [u128; 64],
    pl: [*mut u128; 64],
    ce: [u128; 64],
    pe: [*mut u128; 64],
    // 0.74b : pour un cylindre, la feuille de la page écrite (ses blocs ouverts) ; nul hors d'un cylindre
    pb: [*mut Feuille; 64],
    // 0.74c : pour un cylindre, les mots lus de la page (un bit par mot) ; nul hors d'un cylindre
    rb: [*mut u64; 64],
    // 0.77 : en bandes, les mots écrits directement dans le cube commun (un bit par mot) ; nul sinon
    wb: [*mut u64; 64],
    // les tableaux rangés hors du cube (l'adaptation automatique) : leur recopie dans le cube, avant toute fin
    vider: fn(&mut Ctx),
    // la machine d'un cylindre (les segments joués ensemble) : elle lit le cube commun, et n'écrit que dans le sien
    ombre: Option<Box<Cylindre>>,
    // 0.805 : la carte du vergobret : pour chaque page de l'étage 2 (là où vivent les données d'un programme), le
    // pointeur sur son premier mot, pour lire (c2l) et pour écrire (c2e) ; en bandes, les mots lus (r2) et écrits (w2),
    // un bit par mot (la promesse). Lire un mot de l'étage 2 n'est plus que : numéro de page, pointeur, mot. Une page
    // entre dans la carte à sa première lecture ou écriture ; la carte est oubliée avec le petit cache (oublier_pages)
    carte: Box<Carte>,
}

const CARTE: usize = 1024;     // 0.808 : les places de la carte (chaque page à la place que donne son numéro mêlé)

struct Carte {
    k: [u64; CARTE],           // 0.808 : l'étiquette de chaque place : le numéro de la page + 1 (0 : place libre)
    l: [*mut u128; CARTE],
    e: [*mut u128; CARTE],
    r: [*mut u64; CARTE],
    w: [*mut u64; CARTE],
}

/// 0.808 : la place d'une page de l'étage 2 dans la carte : son numéro mêlé (les pages des cubes de fréquences
/// différentes, qui ont les mêmes 8 bits bas, ne tombent pas à la même place)
#[inline(always)]
fn place_carte(pg: u64) -> usize {
    ((pg ^ (pg >> 8).wrapping_mul(0x9E37) ^ (pg >> 18)) as usize) & (CARTE - 1)
}

impl Carte {
    fn neuve() -> Box<Carte> {
        Box::new(Carte { k: [0; CARTE], l: [std::ptr::null_mut(); CARTE], e: [std::ptr::null_mut(); CARTE],
                         r: [std::ptr::null_mut(); CARTE], w: [std::ptr::null_mut(); CARTE] })
    }
    fn oublier(&mut self) {
        self.k = [0; CARTE];
    }
}

// ------------------------------------------------------------------ les cylindres : un cube par cœur
// « pour i dans a..b en segments { … } » forgé : chaque cylindre (un fil, un cœur) joue des segments qui se suivent,
// sur sa propre machine : il lit les pages du cube commun sans les copier (l'instantané), et ne copie une page qu'au
// moment où il y écrit (son cube à lui). Quand tous ont fini, les cubes sont fondus dans le cube commun, mot à mot, dans
// l'ordre des segments ; chaque mot a un état de Belnap : inconnu (personne n'y a touché : il reste), vrai (un seul
// cylindre l'a changé, ou plusieurs de la même valeur), variable (deux cylindres l'ont changé différemment : le dernier
// l'emporte, comme dans la boucle ordinaire, et le conflit est compté). Si un cylindre a lu une page qu'un cylindre
// d'avant a écrite (il aurait dû voir ce qu'il y a écrit), ou écrit hors de la pile dans l'étage 0, ou touché un cube
// sur disque ou une page d'ADN, tout est oublié et les segments sont rejoués l'un après l'autre : le résultat est
// toujours celui de la boucle ordinaire (et de Lugus).

/// L'instantané du cube commun : (clé de page) -> (premier mot, a des brins) ; lu par tous les cylindres, écrit par aucun
struct Instantane {
    pages: std::collections::HashMap<u128, (*mut u128, bool)>,
    disque: bool,
}
unsafe impl Sync for Instantane {}
unsafe impl Send for Instantane {}

/// 0.73 : un hachage rapide pour les clés de page (le hachage par défaut de Rust, fait contre les attaques, prenait
/// plus de la moitié du temps des cylindres)
#[derive(Default, Clone, Copy)]
struct Rapide(u64);
impl std::hash::Hasher for Rapide {
    fn finish(&self) -> u64 {
        self.0
    }
    fn write(&mut self, b: &[u8]) {
        for &x in b {
            self.0 = (self.0.rotate_left(5) ^ x as u64).wrapping_mul(0x51_7C_C1_B7_27_22_0A_95);
        }
    }
    fn write_u128(&mut self, v: u128) {
        self.0 = ((v as u64) ^ ((v >> 64) as u64).rotate_left(29)).wrapping_mul(0x9E37_79B9_7F4A_7C15);
    }
}
type Table<K, V> = std::collections::HashMap<K, V, std::hash::BuildHasherDefault<Rapide>>;
type Ensemble<K> = std::collections::HashSet<K, std::hash::BuildHasherDefault<Rapide>>;

/// 0.74b : une page qu'un cylindre écrit, ouverte bloc par bloc (64 mots) : au premier mot écrit dans un bloc, ce bloc
/// seul est recopié du cube commun (ou mis à zéro s'il n'y est pas) ; le cylindre ne rend que ses blocs ouverts, et la
/// fusion ne regarde qu'eux (avant, chaque cylindre recopiait et comparait la page entière, un mégaoctet)
struct Feuille {
    mots: Box<[u128]>,
    blocs: [u64; 16],
    commun: *const u128,
}
unsafe impl Send for Feuille {}
unsafe impl Sync for Feuille {}

/// 0.74b : la réserve des pages de feuilles : une page rendue sert de nouveau, sans être remise à zéro (seuls ses blocs
/// ouverts sont lus, et un bloc est toujours rempli à son ouverture)
static RESERVE: std::sync::Mutex<Vec<Box<[u128]>>> = std::sync::Mutex::new(Vec::new());

/// 0.74b : la réserve des machines des cylindres (une machine rendue sert au passage suivant)
struct EnvoiCtx(Box<Ctx>);
unsafe impl Send for EnvoiCtx {}
static CTX_RESERVE: std::sync::Mutex<Vec<EnvoiCtx>> = std::sync::Mutex::new(Vec::new());

#[allow(dead_code)]
fn remettre_ctx(c: Box<Ctx>) {
    let mut r = CTX_RESERVE.lock().unwrap();
    if r.len() < 64 {
        r.push(EnvoiCtx(c));
    }
}

fn page_de_reserve() -> Box<[u128]> {
    match RESERVE.lock().unwrap().pop() {
        Some(p) => p,
        None => vec![0u128; MOTS_PAGE].into_boxed_slice(),
    }
}

fn rendre_a_la_reserve(p: Box<[u128]>) {
    let mut r = RESERVE.lock().unwrap();
    if r.len() < 256 {
        r.push(p);
    }
}

impl Feuille {
    #[inline(always)]
    fn ouvert(&self, b: usize) -> bool {
        (self.blocs[b >> 6] >> (b & 63)) & 1 == 1
    }
    #[inline(never)]
    fn ouvrir(&mut self, b: usize) {
        let d = &mut self.mots[b * 64..b * 64 + 64];
        if self.commun.is_null() {
            d.fill(0);
        } else {
            d.copy_from_slice(unsafe { std::slice::from_raw_parts(self.commun.add(b * 64), 64) });
        }
        self.blocs[b >> 6] |= 1 << (b & 63);
    }
    #[inline(always)]
    fn lire(&self, j: usize) -> u128 {
        if self.ouvert(j >> 6) {
            self.mots[j]
        } else if self.commun.is_null() {
            0
        } else {
            unsafe { *self.commun.add(j) }
        }
    }
}

struct Cylindre {
    commun: *const Instantane,
    feuilles: Table<u128, Box<Feuille>>,
    /// 0.74c : les mots lus, page par page (un bit par mot) : un conflit n'est vu que si un autre cylindre a
    /// vraiment changé un mot que celui-ci a lu (avant, une page lue et écrite par deux cylindres, même à des mots
    /// différents, faisait tout rejouer)
    lus: Table<u128, Box<[u64; 1024]>>,
    /// 0.77 : en bandes, le cylindre écrit directement dans le cube commun ; les mots écrits, page par page
    partage: bool,
    ecrits: Table<u128, Box<[u64; 1024]>>,
    /// 0.73 : les pages déjà vues par ce cylindre et leur premier mot (celle du cube commun, ou la sienne) : une
    /// page n'est cherchée et notée qu'une fois
    vues: Table<u128, *mut u128>,
    danger: bool,
}

/// Ce qu'un cylindre rend : ses pages, les pages qu'il a lues, et s'il faut tout rejouer
struct Recolte {
    pages: Vec<(u128, Box<Feuille>)>,
    ecrits: Vec<(u128, Box<[u64; 1024]>)>,
    lues: Vec<(u128, Box<[u64; 1024]>)>,
    danger: bool,
}

const MOTS_PAGE: usize = 65536;
const PILE_BAS: u128 = spu128::PILE - (1u128 << 24);

#[allow(dead_code)]
fn instantane(c: &mut Ctx) -> Instantane {
    let disque = c.m.a_des_cubes_sur_disque();
    Instantane { pages: c.m.instantane().into_iter().map(|(k, p, b)| (k, (p, b))).collect(), disque }
}

#[allow(dead_code)]
fn cylindres_voulus() -> usize {
    static COEURS: std::sync::OnceLock<usize> = std::sync::OnceLock::new();
    *COEURS.get_or_init(|| std::env::var("VTX_COEURS").ok().and_then(|v| v.parse().ok())
        .unwrap_or_else(|| std::thread::available_parallelism().map(|n| n.get()).unwrap_or(1)))
}

/// 0.810 : le vergobret mesure : une règle sans rien savoir du processeur (ni ses cœurs réels, ni ses fils jumeaux, ni sa
/// mémoire). Chaque boucle « en bandes » a son réglage : elle essaie tous les fils que la machine offre, puis la moitié,
/// le quart… (deux passages chacun, le temps de chaque passage) tant que c'est plus rapide ; puis elle garde le
/// meilleur. Le résultat ne dépend pas du nombre de cœurs (la promesse des bandes) : seul le temps change.
/// 0.812 : le vergobret apprend (une petite intelligence, honnêtement nommée : une mémoire et un plus proche voisin).
/// - il se souvient : ce qu'il a appris est rangé dans `vergobret.savoir`, à côté du programme (une ligne par boucle :
///   sa clé, le nombre de fils de la machine, le meilleur nombre de cœurs, son temps, le temps sur tous les fils) ;
///   au lancement suivant, la boucle prend tout de suite ce qu'il sait ;
/// - il devine : une boucle jamais vue est d'abord mesurée sur tous les fils ; s'il connaît une boucle qui coûtait à
///   peu près autant (sur la même machine), il essaie directement son choix ;
/// - il doute en quatre valeurs : inconnu (jamais vu), variable (deviné par un voisin, à confirmer), vrai (mesuré ici,
///   ou souvenu et confirmé), faux (un souvenir démenti : le temps n'est plus celui retenu ; il oublie et réapprend).
/// VTX_COEURS=n impose n ; VTX_REGLAGE=1 dit ce qu'il fait ; VTX_VERGOBRET=0 : sans mémoire.
#[allow(dead_code)]
#[derive(Clone, Copy, PartialEq)]
enum Confiance { Inconnu, Variable, Vrai, Faux }

#[allow(dead_code)]
struct EtatReglage {
    essai: usize,        // le nombre de cœurs essayé maintenant
    mesures: u32,        // les passages mesurés de cet essai
    temps: f64,          // le meilleur temps de cet essai
    meilleur: usize,     // le meilleur nombre trouvé
    t_meilleur: f64,
    t_tous: f64,         // le temps sur tous les fils (ce qui caractérise la boucle : sa « signature » de coût)
    fige: bool,
    confiance: Confiance,
    deviner: usize,      // le nombre deviné par un voisin (0 : aucun)
    pret: bool,          // la mémoire a été consultée
}

#[allow(dead_code)]
pub struct Reglage {
    cle: u64,
    etat: std::sync::Mutex<EtatReglage>,
}

/// une ligne du savoir : (clé, fils de la machine, meilleur nombre, son temps, temps sur tous les fils)
type Souvenir = (u64, usize, usize, f64, f64);

#[allow(dead_code)]
fn savoir() -> &'static std::sync::Mutex<Vec<Souvenir>> {
    static S: std::sync::OnceLock<std::sync::Mutex<Vec<Souvenir>>> = std::sync::OnceLock::new();
    S.get_or_init(|| {
        let mut v = Vec::new();
        if let Some(f) = fichier_savoir() {
            if let Ok(t) = std::fs::read_to_string(&f) {
                for l in t.lines() {
                    let m: Vec<&str> = l.split_whitespace().collect();
                    if m.len() == 5 {
                        if let (Ok(a), Ok(b), Ok(c), Ok(d), Ok(e)) = (u64::from_str_radix(m[0], 16), m[1].parse(), m[2].parse(),
                                                                       m[3].parse(), m[4].parse()) {
                            v.push((a, b, c, d, e));
                        }
                    }
                }
            }
        }
        std::sync::Mutex::new(v)
    })
}

#[allow(dead_code)]
fn fichier_savoir() -> Option<std::path::PathBuf> {
    if std::env::var("VTX_VERGOBRET").map_or(false, |v| v == "0") {
        return None;
    }
    std::env::current_exe().ok().and_then(|e| e.parent().map(|d| d.join("vergobret.savoir")))
}

#[allow(dead_code)]
fn retenir(sv: Souvenir) {
    let mut v = savoir().lock().unwrap();
    v.retain(|x| !(x.0 == sv.0 && x.1 == sv.1));
    v.push(sv);
    if let Some(f) = fichier_savoir() {
        let mut t = String::from("# vergobret : ce qu'il a appris (clé de la boucle, fils de la machine, meilleur nombre de cœurs, son temps, le temps sur tous les fils)\n");
        for x in v.iter() {
            t += &format!("{:016x} {} {} {:e} {:e}\n", x.0, x.1, x.2, x.3, x.4);
        }
        let _ = std::fs::write(f, t);
    }
}

#[allow(dead_code)]
fn dire_reglage(m: String) {
    if std::env::var("VTX_REGLAGE").is_ok() {
        eprintln!("vergobret : {}", m);
    }
}

#[allow(dead_code)]
impl Reglage {
    pub const fn neuf(cle: u64) -> Reglage {
        Reglage { cle, etat: std::sync::Mutex::new(EtatReglage { essai: 0, mesures: 0, temps: f64::MAX, meilleur: 0,
            t_meilleur: f64::MAX, t_tous: 0.0, fige: false, confiance: Confiance::Inconnu, deviner: 0, pret: false }) }
    }
    pub fn coeurs(&self) -> usize {
        if std::env::var("VTX_COEURS").is_ok() {
            return cylindres_voulus();
        }
        let tous = cylindres_voulus().max(1);
        let mut e = self.etat.lock().unwrap();
        if !e.pret {
            e.pret = true;
            e.essai = tous;
            // se souvenir : cette boucle, sur une machine qui offre autant de fils
            if let Some(sv) = savoir().lock().unwrap().iter().find(|x| x.0 == self.cle && x.1 == tous).copied() {
                e.essai = sv.2.max(1).min(tous);
                e.meilleur = e.essai;
                e.t_meilleur = sv.3;
                e.t_tous = sv.4;
                e.confiance = Confiance::Variable;
                e.deviner = usize::MAX; // un souvenir : à confirmer par la mesure
            }
        }
        if e.fige { e.meilleur } else { e.essai }
    }
    pub fn noter(&self, nt: usize, duree: std::time::Duration, _tours: u64, ligne: u32) {
        if std::env::var("VTX_COEURS").is_ok() {
            return;
        }
        let tous = cylindres_voulus().max(1);
        let mut e = self.etat.lock().unwrap();
        if e.fige || nt != e.essai {
            return;
        }
        let t = duree.as_secs_f64();
        e.mesures += 1;
        if t < e.temps {
            e.temps = t;
        }
        if e.mesures < 2 {
            return;
        }
        let (essai, temps) = (e.essai, e.temps);
        e.mesures = 0;
        e.temps = f64::MAX;
        // un souvenir mis à l'épreuve : le temps doit rester celui retenu (à 30 % près)
        if e.deviner == usize::MAX {
            if temps <= e.t_meilleur * 1.3 {
                e.confiance = Confiance::Vrai;
                e.fige = true;
                dire_reglage(format!("la boucle de la ligne {} : se souvient, {} cœur(s) (sur {} fils) ; confirmé", ligne, essai, tous));
            } else {
                // démenti : il oublie et réapprend, depuis tous les fils
                e.confiance = Confiance::Faux;
                dire_reglage(format!("la boucle de la ligne {} : souvenir démenti ({:.1} ms au lieu de {:.1}) ; il réapprend", ligne,
                                     temps * 1e3, e.t_meilleur * 1e3));
                e.deviner = 0;
                e.meilleur = 0;
                e.t_meilleur = f64::MAX;
                e.essai = tous;
            }
            return;
        }
        if essai == tous && e.meilleur == 0 {
            e.t_tous = temps;
            e.meilleur = tous;
            e.t_meilleur = temps;
            // deviner : la boucle connue (même machine) dont le coût sur tous les fils est le plus proche (à un facteur 2)
            let voisin = savoir().lock().unwrap().iter().filter(|x| x.1 == tous && x.0 != self.cle && x.4 > 0.0)
                .map(|x| ((x.4 / temps).ln().abs(), x.2)).filter(|x| x.0 < std::f64::consts::LN_2)
                .min_by(|a, b| a.0.partial_cmp(&b.0).unwrap()).map(|x| x.1);
            if let Some(n) = voisin {
                if n < tous {
                    e.confiance = Confiance::Variable;
                    e.deviner = n;
                    e.essai = n;
                    dire_reglage(format!("la boucle de la ligne {} : devine {} cœur(s) d'après une boucle semblable", ligne, n));
                    return;
                }
            }
            if tous > 1 {
                e.essai = (tous / 2).max(1);
                return;
            }
        } else if e.deviner > 0 && essai == e.deviner {
            // la devinette mise à l'épreuve
            if temps < e.t_meilleur * 0.97 {
                e.meilleur = essai;
                e.t_meilleur = temps;
                dire_reglage(format!("la boucle de la ligne {} : la devinette tient ({} cœurs)", ligne, essai));
            } else {
                dire_reglage(format!("la boucle de la ligne {} : la devinette ne tient pas ; tous les fils", ligne));
            }
            e.deviner = 0;
        } else if temps < e.t_meilleur * 0.97 {
            e.meilleur = essai;
            e.t_meilleur = temps;
            if essai > 1 {
                e.essai = (essai / 2).max(1);
                return;
            }
        }
        e.fige = true;
        e.confiance = Confiance::Vrai;
        let sv = (self.cle, tous, e.meilleur, e.t_meilleur, e.t_tous);
        drop(e);
        retenir(sv);
        dire_reglage(format!("la boucle de la ligne {} : apprend, {} cœur(s) (sur {} fils offerts) ; retenu", ligne, sv.2, tous));
    }
}

#[allow(dead_code)]
fn rendre(c: &mut Ctx) -> Recolte {
    let o = c.ombre.take().unwrap();
    // seuls les blocs vraiment changés restent ouverts ; la comparaison se fait ici, dans le fil, sur son cœur
    let mut pages = Vec::new();
    for (k, mut f) in o.feuilles.into_iter() {
        for b in 0..1024 {
            if f.ouvert(b) {
                let pareil = if f.commun.is_null() {
                    f.mots[b * 64..b * 64 + 64].iter().all(|&w| w == 0)
                } else {
                    f.mots[b * 64..b * 64 + 64] == *unsafe { std::slice::from_raw_parts(f.commun.add(b * 64), 64) }
                };
                if pareil {
                    f.blocs[b >> 6] &= !(1 << (b & 63));
                }
            }
        }
        if f.blocs.iter().any(|&w| w != 0) {
            pages.push((k, f));
        } else {
            rendre_a_la_reserve(f.mots);
        }
    }
    Recolte { pages, ecrits: o.ecrits.into_iter().collect(), lues: o.lus.into_iter().collect(), danger: o.danger }
}

/// l'adresse du premier mot d'une page, depuis sa clé
fn adresse_page(k: u128) -> u128 {
    let e = k >> 120;
    let i = (k & ((1u128 << 120) - 1)) << 16;
    if i >> 48 == 0 { (e << 62) | i } else { (e << 126) | i }
}

/// Fond les cubes des cylindres dans le cube commun ; faux : il faut rejouer les segments l'un après l'autre.
/// 0.73 : les segments sont donnés aux cylindres en alternance (0, n, 2n… au premier ; 1, n + 1… au second), pour que
/// chacun ait sa part du travail où qu'il soit dans la boucle ; l'ordre des segments n'est donc plus celui des
/// cylindres, et la fusion devient stricte : si un cylindre a lu une page qu'un autre écrivait, ou si deux cylindres ont
/// écrit le même mot de deux valeurs différentes (un mot variable), rien n'est posé et les segments sont rejoués dans
/// l'ordre. Le résultat reste toujours celui de Lugus.
#[allow(dead_code)]
fn fusionner(c: &mut Ctx, _inst: &Instantane, recoltes: Vec<Recolte>) -> bool {
    if recoltes.iter().any(|r| r.danger) {
        rapport_cylindres(recoltes.len(), 0, 0, "un cylindre a touché ce qui n'est qu'au cube commun : rejoué");
        return false;
    }
    // un cylindre a-t-il lu un mot qu'un autre cylindre a changé ? (au mot près : les blocs que l'autre a ouverts et
    // changés, les mots que celui-ci a lus)
    let ecrites: Vec<std::collections::HashMap<u128, &Feuille>> =
        recoltes.iter().map(|r| r.pages.iter().map(|(k, f)| (*k, &**f)).collect()).collect();
    for t in 0..recoltes.len() {
        for (k, bits) in &recoltes[t].lues {
            for (s_, e) in ecrites.iter().enumerate() {
                if s_ == t {
                    continue;
                }
                let f = match e.get(k) {
                    Some(f) => f,
                    None => continue,
                };
                for b in 0..1024 {
                    if bits[b] == 0 || !f.ouvert(b) {
                        continue;
                    }
                    for i in 0..64 {
                        if (bits[b] >> i) & 1 == 1 {
                            let j = b * 64 + i;
                            let orig = if f.commun.is_null() { 0 } else { unsafe { *f.commun.add(j) } };
                            if f.mots[j] != orig {
                                rapport_cylindres(recoltes.len(), 0, 0, "un cylindre a lu ce qu'un autre écrivait : rejoué");
                                return false;
                            }
                        }
                    }
                }
            }
        }
    }
    drop(ecrites);
    // chaque page du cube commun, avec ceux qui l'ont écrite
    let nr = recoltes.len();
    let mut ordre: Vec<u128> = Vec::new();
    let mut auteurs: std::collections::HashMap<u128, Vec<Box<Feuille>>> = std::collections::HashMap::new();
    for r in recoltes {
        for (k, f) in r.pages {
            auteurs.entry(k).or_insert_with(|| { ordre.push(k); Vec::new() }).push(f);
        }
    }
    let pages = ordre.len();
    // les pages du cube commun où poser, puis le travail en tranches de 64 blocs (4 096 mots), partagé entre les cœurs
    let cibles: Vec<(usize, usize)> = ordre.iter().enumerate()
        .map(|(n, k)| (n, c.m.page_de(adresse_page(*k)).0 as usize)).collect();
    let feuilles: Vec<&Vec<Box<Feuille>>> = ordre.iter().map(|k| &auteurs[k]).collect();
    let tranches: Vec<(usize, usize)> = (0..ordre.len()).flat_map(|n| (0..16).map(move |t| (n, t))).collect();
    let nt = cylindres_voulus().max(1).min(tranches.len().max(1));
    let travail = |faire: &(dyn Fn(usize, usize) -> u64 + Sync)| -> u64 {
        let suivante = std::sync::atomic::AtomicUsize::new(0);
        std::thread::scope(|sc| {
            let fils: Vec<_> = (0..nt).map(|_| sc.spawn(|| {
                let mut v = 0;
                loop {
                    let q = suivante.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    if q >= tranches.len() {
                        break;
                    }
                    v += faire(tranches[q].0, tranches[q].1);
                }
                v
            })).collect();
            fils.into_iter().map(|h| h.join().unwrap()).sum()
        })
    };
    // d'abord, sans rien poser : deux cylindres ont-ils changé le même mot de deux valeurs ? (seuls les blocs ouverts
    // par plusieurs sont regardés)
    let verifier = |n: usize, t: usize| -> u64 {
        let fs = feuilles[n];
        if fs.len() < 2 {
            return 0;
        }
        let d = unsafe { std::slice::from_raw_parts(cibles[n].1 as *const u128, MOTS_PAGE) };
        let mut v = 0;
        for b in t * 64..t * 64 + 64 {
            if fs.iter().filter(|f| f.ouvert(b)).count() < 2 {
                continue;
            }
            for j in b * 64..b * 64 + 64 {
                let mut vu: Option<u128> = None;
                for f in fs.iter().filter(|f| f.ouvert(b)) {
                    let w = f.mots[j];
                    if w != d[j] {
                        match vu {
                            Some(x) if x != w => v += 1,
                            _ => vu = Some(w),
                        }
                    }
                }
            }
        }
        v
    };
    let variables = travail(&verifier);
    // 0.807 : sur demande (VTX_CYLINDRES), l'état de chaque mot après le passage, en quaternaire : vrai (une seule
    // valeur nouvelle, d'un cylindre ou de plusieurs d'accord), variable (deux valeurs) ; le reste est inchangé
    // (inconnu ; « faux », écrit puis rendu à sa valeur d'avant, ne se distingue pas d'un mot jamais touché)
    if std::env::var("VTX_CYLINDRES").is_ok() {
        let compter = |n: usize, t: usize| -> u64 {
            let fs = feuilles[n];
            let d = unsafe { std::slice::from_raw_parts(cibles[n].1 as *const u128, MOTS_PAGE) };
            let mut vrai = 0u64;
            for b in t * 64..t * 64 + 64 {
                if !fs.iter().any(|f| f.ouvert(b)) {
                    continue;
                }
                for j in b * 64..b * 64 + 64 {
                    if fs.iter().filter(|f| f.ouvert(b)).any(|f| f.mots[j] != d[j]) {
                        vrai += 1;
                    }
                }
            }
            vrai
        };
        let changes = travail(&compter);
        eprintln!("mots : vrai {} (une valeur nouvelle), variable {} (deux valeurs), le reste inconnu (inchangé)",
                  changes - variables.min(changes), variables);
    }
    if variables > 0 {
        for (_, fs) in auteurs {
            for f in fs {
                rendre_a_la_reserve(f.mots);
            }
        }
        rapport_cylindres(nr, 0, variables, "deux cylindres ont écrit le même mot de deux valeurs (variable) : rejoué dans l'ordre");
        return false;
    }
    // tout est sûr : chaque bloc ouvert est posé dans le cube commun (chaque tranche par un seul cœur)
    let poser = |n: usize, t: usize| -> u64 {
        let fs = feuilles[n];
        let d = unsafe { std::slice::from_raw_parts_mut(cibles[n].1 as *mut u128, MOTS_PAGE) };
        for b in t * 64..t * 64 + 64 {
            let nb = fs.iter().filter(|f| f.ouvert(b)).count();
            if nb == 0 {
                continue;
            }
            if nb == 1 {
                // un seul l'a ouvert : son bloc part de ce même bloc du cube commun, il est posé tel quel
                let f = fs.iter().find(|f| f.ouvert(b)).unwrap();
                d[b * 64..b * 64 + 64].copy_from_slice(&f.mots[b * 64..b * 64 + 64]);
                continue;
            }
            let mut avant = [0u128; 64];
            avant.copy_from_slice(&d[b * 64..b * 64 + 64]);
            for f in fs.iter().filter(|f| f.ouvert(b)) {
                for i in 0..64 {
                    let w = f.mots[b * 64 + i];
                    if w != avant[i] {
                        d[b * 64 + i] = w;
                    }
                }
            }
        }
        0
    };
    travail(&poser);
    drop(feuilles);
    for (_, fs) in auteurs {
        for f in fs {
            rendre_a_la_reserve(f.mots);
        }
    }
    c.oublier_pages();
    rapport_cylindres(nr, pages, 0, "");
    true
}

/// 0.77 : l'équipe des cœurs, gardée vivante : les fils sont créés une fois ; à chaque passage, le fil t joue la part t
/// (le fil 0 est celui du programme) ; le même fil reprend la même part d'un passage à l'autre (ses données restent
/// près de lui). Créer des fils à chaque passage coûtait cher, sous Windows surtout.
type Tache = dyn Fn(usize) -> Recolte + Sync;
struct Envoi(*const Tache);
unsafe impl Send for Envoi {}
struct Equipe {
    ordre: std::sync::Mutex<(u64, usize, Envoi)>,
    cv: std::sync::Condvar,
    fin: std::sync::Mutex<(usize, Vec<Option<Recolte>>)>,
    cv_fin: std::sync::Condvar,
    fils: std::sync::Mutex<usize>,
}
static EQUIPE: std::sync::OnceLock<Equipe> = std::sync::OnceLock::new();

fn equipe() -> &'static Equipe {
    EQUIPE.get_or_init(|| Equipe {
        ordre: std::sync::Mutex::new((0, 0, Envoi(std::ptr::null::<fn(usize) -> Recolte>() as *const Tache))),
        cv: std::sync::Condvar::new(),
        fin: std::sync::Mutex::new((0, Vec::new())),
        cv_fin: std::sync::Condvar::new(),
        fils: std::sync::Mutex::new(1),
    })
}

fn equipier(i: usize) {
    let e = equipe();
    let mut vu = 0u64;
    loop {
        let (nt, f) = {
            let mut o = e.ordre.lock().unwrap();
            while o.0 == vu {
                o = e.cv.wait(o).unwrap();
            }
            vu = o.0;
            (o.1, o.2 .0)
        };
        if i < nt {
            let r = unsafe { (*f)(i) };
            let mut fin = e.fin.lock().unwrap();
            fin.1[i] = Some(r);
            fin.0 -= 1;
            if fin.0 == 0 {
                e.cv_fin.notify_all();
            }
        }
    }
}

#[allow(dead_code)]
fn equipe_jouer<'a>(nt: usize, f: &'a (dyn Fn(usize) -> Recolte + Sync + 'a)) -> Vec<Recolte> {
    let e = equipe();
    {
        let mut n = e.fils.lock().unwrap();
        while *n < nt {
            let i = *n;
            std::thread::spawn(move || equipier(i));
            *n += 1;
        }
    }
    {
        let mut fin = e.fin.lock().unwrap();
        fin.0 = nt - 1;
        fin.1 = (0..nt).map(|_| None).collect();
    }
    if nt > 1 {
        let mut o = e.ordre.lock().unwrap();
        o.0 += 1;
        o.1 = nt;
        // la tâche ne vit que le temps de ce passage : on attend que tous l'aient jouée avant de rendre la main
        o.2 = Envoi(unsafe { std::mem::transmute::<&'a (dyn Fn(usize) -> Recolte + Sync + 'a), &'static Tache>(f) } as *const Tache);
        e.cv.notify_all();
    }
    let r0 = f(0);
    let mut fin = e.fin.lock().unwrap();
    while fin.0 > 0 {
        fin = e.cv_fin.wait(fin).unwrap();
    }
    fin.1[0] = Some(r0);
    std::mem::take(&mut fin.1).into_iter().map(|r| r.unwrap()).collect()
}

/// 0.77 : après une boucle « en bandes » : un cœur a-t-il écrit un mot qu'un autre a lu ou écrit ? (un bit par mot).
/// 0.806 : en un seul passage, quel que soit le nombre de cœurs : pour chaque page, les mots écrits par au moins un cœur
/// (w1), par au moins deux (w2), et lus par un cœur qui ne les a pas écrits lui-même (rx) ; la promesse est rompue là
/// où w2, ou w1 et rx à la fois. Rend la première page touchée.
#[allow(dead_code)]
fn bandes_touchees(recoltes: &[Recolte]) -> Option<u128> {
    let mut pages: Vec<(u128, Box<[[u64; 1024]; 3]>)> = Vec::new();
    fn place(pages: &mut Vec<(u128, Box<[[u64; 1024]; 3]>)>, k: u128) -> usize {
        match pages.iter().position(|x| x.0 == k) {
            Some(i) => i,
            None => {
                pages.push((k, Box::new([[0u64; 1024]; 3])));
                pages.len() - 1
            }
        }
    }
    for r in recoltes {
        for (k, w) in &r.ecrits {
            let i = place(&mut pages, *k);
            let p = &mut pages[i].1;
            for j in 0..1024 {
                p[1][j] |= p[0][j] & w[j];
                p[0][j] |= w[j];
            }
        }
    }
    for r in recoltes {
        for (k, l) in &r.lues {
            // une page lue que personne n'a écrite ne peut rien rompre
            let Some(i) = pages.iter().position(|x| x.0 == *k) else { continue };
            let propre = r.ecrits.iter().find(|x| x.0 == *k).map(|x| &x.1);
            let p = &mut pages[i].1;
            for j in 0..1024 {
                p[2][j] |= l[j] & !propre.map_or(0, |w| w[j]);
            }
        }
    }
    for (k, p) in &pages {
        if let Some(j) = (0..1024).find(|&j| p[1][j] | (p[0][j] & p[2][j]) != 0) {
            if std::env::var("VTX_CYLINDRES").is_ok() {
                let b = (p[1][j] | (p[0][j] & p[2][j])).trailing_zeros() as usize;
                eprintln!("bandes : la promesse rompue à la page {:#x}, mot {} ({})", k, j * 64 + b,
                          if p[1][j] >> b & 1 == 1 { "écrit par deux cœurs" } else { "écrit par l'un, lu par l'autre" });
            }
            return Some(*k);
        }
    }
    None
}

#[allow(dead_code)]
fn chrono_cylindres(t0: std::time::Instant, t1: std::time::Instant) {
    if std::env::var("VTX_CYLINDRES").is_ok() {
        static DEBUT: std::sync::OnceLock<std::time::Instant> = std::sync::OnceLock::new();
        let d = *DEBUT.get_or_init(|| t0);
        eprintln!("    à {:.0} ms : en fils {:.1} ms, fusion {:.1} ms", (t0 - d).as_secs_f64() * 1e3, (t1 - t0).as_secs_f64() * 1e3, t1.elapsed().as_secs_f64() * 1e3);
    }
}

fn rapport_cylindres(n: usize, pages: usize, variables: u64, rejoue: &str) {
    if std::env::var("VTX_CYLINDRES").is_ok() {
        if rejoue.is_empty() {
            eprintln!("cylindres : {} ; {} pages fondues ; {} mots variables (deux cylindres, deux valeurs)", n, pages, variables);
        } else {
            if variables > 0 {
                eprintln!("cylindres : {} ; {} mots variables ; {}", n, variables, rejoue);
            } else {
                eprintln!("cylindres : {} ; {}", n, rejoue);
            }
        }
    }
}

/// la case d'une page dans le petit cache (0.73 : 64 cases) : son numéro et son étage mêlés
#[inline(always)]
fn case(k: u128) -> usize {
    let n = k as usize;
    ((n ^ (n >> 6) ^ (n >> 12)).wrapping_add(((k >> 120) as usize).wrapping_mul(37))) & 63
}

impl Ctx {
    /// 0.805 : lire un mot de l'étage 2 (a : son adresse dans l'étage) par la carte du vergobret
    #[inline(always)]
    fn lire2(&mut self, a: u128) -> u128 {
        let idx = (a as u64) & 0xFFFF_FFFF_FFFF;
        let pg = idx >> 16;
        let h = place_carte(pg);
        if self.carte.k[h] == pg + 1 {
            let p = self.carte.l[h];
            if !p.is_null() {
                let j = (idx & 65535) as usize;
                let b = self.carte.r[h];
                if !b.is_null() {
                    unsafe { *b.add(j >> 6) |= 1u64 << (j & 63) };
                }
                return unsafe { *p.add(j) };
            }
        }
        self.lire2_lent(idx)
    }
    #[inline(never)]
    fn lire2_lent(&mut self, idx: u64) -> u128 {
        let a = etg(idx as u128, 2);
        let v = self.lire(a);
        // la page vient d'entrer dans le petit cache (sauf une feuille de cylindre, ou une page absente) : elle entre
        // dans la carte (à sa place : la page qui l'occupait en sort) ; hors des bandes, un cylindre (en segments) garde
        // son chemin
        let pg = idx >> 16;
        if self.ombre.as_ref().map_or(true, |o| o.partage) {
            let (k, _) = Spu128::cle_page(a);
            let h = case(k);
            if self.cl[h] == k {
                let q = place_carte(pg);
                if self.carte.k[q] != pg + 1 {
                    self.carte.k[q] = pg + 1;
                    self.carte.e[q] = std::ptr::null_mut();
                    self.carte.w[q] = std::ptr::null_mut();
                }
                self.carte.l[q] = self.pl[h];
                self.carte.r[q] = self.rb[h];
            }
        }
        v
    }
    /// 0.805 : écrire un mot de l'étage 2 par la carte du vergobret
    #[inline(always)]
    fn ecrire2(&mut self, a: u128, v: u128) {
        let idx = (a as u64) & 0xFFFF_FFFF_FFFF;
        let pg = idx >> 16;
        let h = place_carte(pg);
        if self.carte.k[h] == pg + 1 {
            let p = self.carte.e[h];
            if !p.is_null() {
                let j = (idx & 65535) as usize;
                let w = self.carte.w[h];
                if !w.is_null() {
                    unsafe { *w.add(j >> 6) |= 1u64 << (j & 63) };
                }
                unsafe { *p.add(j) = v };
                return;
            }
        }
        self.ecrire2_lent(idx, v)
    }
    #[inline(never)]
    fn ecrire2_lent(&mut self, idx: u64, v: u128) {
        let a = etg(idx as u128, 2);
        self.ecrire(a, v);
        // une page écrite directement (sans brin, pas une feuille de cylindre) entre dans la carte
        let pg = idx >> 16;
        if self.ombre.as_ref().map_or(true, |o| o.partage) {
            let (k, _) = Spu128::cle_page(a);
            let h = case(k);
            if self.ce[h] == k && self.pb[h].is_null() {
                let q = place_carte(pg);
                if self.carte.k[q] != pg + 1 {
                    self.carte.k[q] = pg + 1;
                    self.carte.l[q] = std::ptr::null_mut();
                    self.carte.r[q] = std::ptr::null_mut();
                }
                self.carte.e[q] = self.pe[h];
                self.carte.w[q] = self.wb[h];
            }
        }
    }
    #[inline(always)]
    fn lire(&mut self, a: u128) -> u128 {
        let (k, j) = Spu128::cle_page(a);
        let h = case(k);
        if k == self.cl[h] {
            let b = self.rb[h];
            if !b.is_null() {
                unsafe { *b.add(j >> 6) |= 1u64 << (j & 63) };
            }
            return unsafe { *self.pl[h].add(j) };
        }
        self.lire_lent(a, k, j)
    }
    #[inline(never)]
    fn lire_lent(&mut self, a: u128, k: u128, j: usize) -> u128 {
        if self.ombre.is_some() && k >> 120 != 0 {
            let o = self.ombre.as_mut().unwrap();
            // 0.74c : le mot lu est noté
            let bits: *mut u64 = o.lus.entry(k).or_insert_with(|| Box::new([0u64; 1024])).as_mut_ptr();
            unsafe { *bits.add(j >> 6) |= 1u64 << (j & 63) };
            // 0.74b : une page que ce cylindre écrit : bloc par bloc (les siens, ouverts ; les autres, du cube commun)
            if let Some(f) = o.feuilles.get(&k) {
                return f.lire(j);
            }
            // 0.73 : une page déjà vue : son premier mot est connu, rien à chercher
            if let Some(&p) = o.vues.get(&k) {
                let h = case(k);
                self.cl[h] = k;
                self.pl[h] = p;
                self.rb[h] = bits;
                return unsafe { *p.add(j) };
            }
            let commun = unsafe { &*o.commun };
            if let Some(&(p, _)) = commun.pages.get(&k) {
                // la page du cube commun, lue sans la copier
                o.vues.insert(k, p);
                let h = case(k);
                self.cl[h] = k;
                self.pl[h] = p;
                self.rb[h] = bits;
                return unsafe { *p.add(j) };
            }
            if commun.disque {
                o.danger = true;
            }
            // une page que le cube commun n'a pas : elle est vide
            return 0;
        }
        let (p, _, _) = self.m.page_de(a);
        let h = case(k);
        self.cl[h] = k;
        self.pl[h] = p;
        self.rb[h] = std::ptr::null_mut();
        unsafe { *p.add(j) }
    }
    #[inline(always)]
    fn ecrire(&mut self, a: u128, v: u128) {
        let (k, j) = Spu128::cle_page(a);
        let h = case(k);
        if k == self.ce[h] {
            let w = self.wb[h];
            if !w.is_null() {
                unsafe { *w.add(j >> 6) |= 1u64 << (j & 63) };
            }
            let f = self.pb[h];
            if !f.is_null() {
                let f = unsafe { &mut *f };
                if !f.ouvert(j >> 6) {
                    f.ouvrir(j >> 6);
                }
            }
            unsafe { *self.pe[h].add(j) = v };
            return;
        }
        self.ecrire_lent(a, v, k);
    }
    #[inline(never)]
    fn ecrire_lent(&mut self, a: u128, v: u128, k: u128) {
        if self.ombre.is_some() {
            let o = self.ombre.as_mut().unwrap();
            if k >> 120 == 0 {
                // l'étage 0 d'un cylindre est à lui (sa pile) ; une donnée écrite ailleurs y serait perdue
                if a > spu128::PILE || a < PILE_BAS {
                    o.danger = true;
                }
            } else {
                // 0.77 : en bandes, une page du cube commun s'écrit directement (le mot écrit est noté)
                if o.partage && !o.feuilles.contains_key(&k) {
                    let commun = unsafe { &*o.commun };
                    if let Some(&(p, false)) = commun.pages.get(&k) {
                        let bits: *mut u64 = o.ecrits.entry(k).or_insert_with(|| Box::new([0u64; 1024])).as_mut_ptr();
                        let (_, j) = Spu128::cle_page(a);
                        let h = case(k);
                        self.ce[h] = k;
                        self.pe[h] = p;
                        self.pb[h] = std::ptr::null_mut();
                        self.wb[h] = bits;
                        unsafe {
                            *bits.add(j >> 6) |= 1u64 << (j & 63);
                            *p.add(j) = v;
                        }
                        return;
                    }
                }
                // 0.74b : une page du cube : sa feuille (créée à la première écriture), ouverte bloc par bloc
                if !o.feuilles.contains_key(&k) {
                    let commun = unsafe { &*o.commun };
                    let source = commun.pages.get(&k).copied();
                    if source.is_none() && commun.disque {
                        o.danger = true;
                    }
                    if source.map_or(false, |s| s.1) {
                        o.danger = true;
                    }
                    let f = Box::new(Feuille { mots: page_de_reserve(), blocs: [0; 16],
                                               commun: source.map_or(std::ptr::null(), |s| s.0 as *const u128) });
                    o.feuilles.insert(k, f);
                    o.vues.remove(&k);
                    let h = case(k);
                    if self.cl[h] == k {
                        self.cl[h] = u128::MAX;
                    }
                }
                let f: *mut Feuille = &mut **o.feuilles.get_mut(&k).unwrap();
                let (_, j) = Spu128::cle_page(a);
                let h = case(k);
                self.ce[h] = k;
                self.pe[h] = unsafe { (*f).mots.as_mut_ptr() };
                self.pb[h] = f;
                self.wb[h] = std::ptr::null_mut();
                unsafe {
                    if !(*f).ouvert(j >> 6) {
                        (*f).ouvrir(j >> 6);
                    }
                    *(*f).mots.as_mut_ptr().add(j) = v;
                }
                return;
            }
        }
        let (p, _, brins) = self.m.page_de(a);
        if !brins {
            // une page sans brin : les écritures suivantes y vont directement
            let h = case(k);
            self.ce[h] = k;
            self.pe[h] = p;
            self.pb[h] = std::ptr::null_mut();
            self.wb[h] = std::ptr::null_mut();
        }
        if let Err(e) = self.m.ecrire_mem(a, v) {
            arreter(self, &e);
        }
    }
    /// un brin vient d'être posé : les écritures repassent par la vérification
    fn oublier_pages(&mut self) {
        self.ce = [u128::MAX; 64];
        self.cl = [u128::MAX; 64];
        self.carte.oublier();
    }
    #[inline(always)]
    fn pousser(&mut self, v: u128) {
        self.sp = self.sp.wrapping_sub(1) & ((1u128 << 120) - 1);
        let sp = self.sp;
        self.ecrire(sp, v);
    }
    #[inline(always)]
    fn poser(&mut self, a: u128, v: u128) {
        self.ecrire(a, v);
    }
    fn sys(&mut self, code: u128, arg: u128) -> u128 {
        match self.m.service(code, arg) {
            Ok(v) => v & M64,
            Err(e) => {
                arreter(self, &e);
                0
            }
        }
    }
    fn marquer(&mut self, a: u128, n: u128, q: u8) {
        self.oublier_pages();
        let mut k = 0u128;
        while k < n {
            self.m.marquer(a.wrapping_add(k), q);
            k += 1;
        }
    }
}

/// Une erreur de la machine (écriture dans un mot ADN…) : la ligne du corpus « ERREUR … », ou le message.
fn arreter(c: &mut Ctx, e: &str) -> ! {
    (c.vider)(c);
    if std::env::var("FORGE_LIGNE").is_ok() {
        println!("ERREUR {}", e);
    } else {
        finir(c);
        eprintln!("erreur : {}", e);
    }
    std::process::exit(1);
}

// --- les entiers à la largeur 64 et 32 (le sens des instructions de Lugus)
#[inline(always)]
fn etg(a: u128, e: u32) -> u128 {
    ((a as u64 & !(3u64 << 62)) | ((e as u64 & 3) << 62)) as u128
}
#[inline(always)]
fn divu64(a: u128, b: u128) -> u128 {
    let (a, b) = (a as u64, b as u64);
    (if b == 0 { u64::MAX } else { a / b }) as u128
}
#[inline(always)]
fn modu64(a: u128, b: u128) -> u128 {
    let (a, b) = (a as u64, b as u64);
    (if b == 0 { a } else { a % b }) as u128
}
#[inline(always)]
fn divs64(a: u128, b: u128) -> u128 {
    let (a, b) = (a as u64 as i64, b as u64 as i64);
    (if b == 0 { u64::MAX } else { a.wrapping_div(b) as u64 }) as u128
}
#[inline(always)]
fn mods64(a: u128, b: u128) -> u128 {
    let (x, y) = (a as u64 as i64, b as u64 as i64);
    (if y == 0 { a as u64 } else { x.wrapping_rem(y) as u64 }) as u128
}
#[inline(always)]
fn sar64(a: u128, b: u128) -> u128 {
    ((a as u64 as i64) >> ((b as u64) & 63)) as u64 as u128
}
/// l'entier_32 étendu par le signe sur 64 bits (SEXT.32 puis ZEXT.64)
#[inline(always)]
fn sext32(a: u128) -> u128 {
    (a as u32 as i32 as i64 as u64) as u128
}
#[inline(always)]
fn divs32(a: u128, b: u128) -> u128 {
    divs64(sext32(a), sext32(b)) & M32
}
#[inline(always)]
fn mods32(a: u128, b: u128) -> u128 {
    mods64(sext32(a), sext32(b)) & M32
}
#[inline(always)]
fn sar32(a: u128, b: u128) -> u128 {
    sar64(sext32(a), b) & M32
}
#[inline(always)]
fn divs128(a: u128, b: u128) -> u128 {
    if b == 0 { u128::MAX } else { (a as i128).wrapping_div(b as i128) as u128 }
}
#[inline(always)]
fn mods128(a: u128, b: u128) -> u128 {
    if b == 0 { a } else { (a as i128).wrapping_rem(b as i128) as u128 }
}

// --- le quaternaire à la largeur 64 (32 quits)
#[inline(always)]
fn et4_64(a: u128, b: u128) -> u128 {
    let (a, b) = (a as u64, b as u64);
    (((a & b) & V64) | ((a | b) & F64)) as u128
}
#[inline(always)]
fn ou4_64(a: u128, b: u128) -> u128 {
    let (a, b) = (a as u64, b as u64);
    (((a | b) & V64) | ((a & b) & F64)) as u128
}
#[inline(always)]
fn non4_64(a: u128) -> u128 {
    let a = a as u64;
    (((a & V64) >> 1) | ((a & F64) << 1)) as u128
}
#[inline(always)]
fn anti_64(a: u128) -> u128 {
    non4_64(a) ^ M64
}
#[inline(always)]
fn qegal_64(a: u128, b: u128) -> u128 {
    let x = (a as u64) ^ (b as u64);
    (!(x | (x >> 1)) & F64) as u128
}
fn quits_64(a: u128, b: u128, op: u32) -> u128 {
    let mut r = 0u128;
    for k in 0..32 {
        let (x, y) = ((a >> (2 * k)) & 3, (b >> (2 * k)) & 3);
        let q = match op {
            0 => x.min(y),
            1 => x.max(y),
            _ => (x + y) & 3,
        };
        r |= q << (2 * k);
    }
    r
}
#[inline(always)]
fn gdot_64(a: u128, b: u128) -> u128 {
    let mut s = 0u128;
    for k in 0..4 {
        s = s.wrapping_add(((a >> (16 * k)) & 0xFFFF) * ((b >> (16 * k)) & 0xFFFF));
    }
    s & M64
}

// --- le point de matière
#[inline(always)]
fn mate(p: u128, v: u128, dec: u32, nb: u32) -> u128 {
    let mk = ((1u128 << nb) - 1) << dec;
    (p & !mk) | ((v << dec) & mk)
}
fn melange(s: u128, t: u128, p: u128) -> u128 {
    let voies = |x: u128| [x & M32, (x >> 32) & M32, (x >> 64) & M32, x >> 96];
    let (a, b) = (voies(s), voies(t));
    let mel = |x: u128, y: u128| (x * (256 - p) + y * p) >> 8;
    let mut mat = (((a[0] >> 30) | (b[0] >> 30)) & 3) << 30;
    for dec in [24u32, 18, 12, 6, 0] {
        mat |= mel((a[0] >> dec) & 63, (b[0] >> dec) & 63) << dec;
    }
    (mat & M32) | ((mel(a[1], b[1]) & M32) << 32) | ((mel(a[2], b[2]) & M32) << 64) | ((mel(a[3], b[3]) & M32) << 96)
}

/// Ce qui est montré à la fin : la ligne du corpus de Lugus (FORGE_LIGNE), ou les sorties et le texte.
fn finir(c: &mut Ctx) {
    if std::env::var("FORGE_LIGNE").is_ok() {
        let l = c.m.ligne_corpus();
        // sans le nombre de pas (la forge n'exécute pas d'instructions de Lugus)
        println!("{}", &l[l.find('|').unwrap_or(0)..]);
        return;
    }
    if !c.m.sortie.is_empty() {
        println!("{}", c.m.sortie.iter().map(|v| v.to_string()).collect::<Vec<_>>().join(","));
    }
    let t: String = c.m.texte.iter().filter_map(|&v| char::from_u32((v & 0x1F_FFFF) as u32)).collect();
    print!("{}", t);
}

/// 0.78 : l'image de l'étage 1 (l'écran), prise en un bloc, page par page, et montrée (la fenêtre, ou les fichiers)
fn point_forge(v: u128) -> u32 {
    if v >> 64 == 0 {
        let v = v as u64;
        return (((v >> 56) & 0xFF) << 16 | ((v >> 40) & 0xFF) << 8 | ((v >> 24) & 0xFF)) as u32;
    }
    (((v >> 120) & 0xFF) << 16 | ((v >> 88) & 0xFF) << 8 | ((v >> 56) & 0xFF)) as u32
}

fn presenter_forge(s: &Spu128) -> u128 {
    let (l, h) = (s.regarder((3u128 << 62) | 14_680_058), s.regarder((3u128 << 62) | 14_680_059));
    if !((1..=4096).contains(&l) && (1..=4096).contains(&h) && l * h <= 1 << 24) {
        return u64::MAX as u128;
    }
    let (l, h) = (l as usize, h as usize);
    let mut px = vec![0u32; l * h];
    for (k, morceau) in px.chunks_mut(65536).enumerate() {
        if let Some(mots) = s.page_vue(1, k as u128) {
            for (d, &v) in morceau.iter_mut().zip(mots.iter()) {
                *d = point_forge(v);
            }
        }
    }
    if sortie::montrer(l, h, &px) { 0 } else { 1 }
}

fn lancer_programme(principal: fn(&mut Ctx) -> u128, debuter: fn(&mut Ctx), vider: fn(&mut Ctx), mots: &[u128], fin_code: u128,
                    nom: &str, entrees: &[String]) {
    let mut m = Spu128::nouveau();
    m.dossier = std::env::current_dir().ok();
    // 0.78 : la fenêtre du programme (ou VTX_IMAGES=DOSSIER : les images en fichiers PNG), ouverte à la première image
    hote::remettre();
    // 0.808 : VTX_GIF=FICHIER : les images en une animation GIF (au délai de la cadence du programme ; l'horloge reste la
    // vraie : un film se mesure)
    match (std::env::var("VTX_GIF"), std::env::var("VTX_IMAGES")) {
        (Ok(g), _) => {
            sortie::installer(Some(sortie::animation(&g, 1, sortie::MAX_IMAGES)));
        }
        (_, Ok(d)) => {
            hote::HORLOGE_IMAGES.store(true, std::sync::atomic::Ordering::Relaxed);
            sortie::installer(Some(sortie::fichiers(&d, 1, usize::MAX)));
        }
        _ => sortie::installer(sortie::fenetre(nom)),
    }
    m.presenter = Some(Box::new(presenter_forge));
    // VTX_SCENARIO=FICHIER : les touches d'un scénario (« N appui CODE », « N touche CODE »…), comme vtx toile128
    if let Ok(f) = std::env::var("VTX_SCENARIO") {
        match std::fs::read_to_string(&f).map_err(|e| e.to_string()).and_then(|t| hote::charger_scenario(&t)) {
            Ok(_) => {}
            Err(e) => eprintln!("scénario {} : {}", f, e),
        }
    }
    m.charger(mots);
    m.entree.extend(entrees.iter().filter_map(|x| x.parse::<u128>().ok()));
    let mut c = Ctx { m, sp: spu128::PILE, cl: [u128::MAX; 64], pl: [std::ptr::null_mut(); 64], ce: [u128::MAX; 64], carte: Carte::neuve(),
                      pe: [std::ptr::null_mut(); 64], pb: [std::ptr::null_mut(); 64], rb: [std::ptr::null_mut(); 64],
                      wb: [std::ptr::null_mut(); 64],
                      vider, ombre: None };
    debuter(&mut c);
    // le brin : le code, les textes écrits et les données du programme sont de l'ADN (comme au début du programme
    // compilé : MARQUE R0, FIN_CODE, 1), puis l'appel de principal (CALL : l'adresse de retour dans la pile)
    c.marquer(0, fin_code, 1);
    c.pousser(0);
    let debut = std::time::Instant::now();
    principal(&mut c);
    let duree = debut.elapsed();
    vider(&mut c);
    finir(&mut c);
    // la fenêtre reste ouverte jusqu'à ce qu'on la ferme (l'animation est écrite)
    sortie::finir();
    if std::env::var("FORGE_TEMPS").is_ok() {
        eprintln!("{} : {:.3} s", nom, duree.as_secs_f64());
    }
}

// ------------------------------------------------------------------ Taranis : une boucle en segments sur la carte
/// La boucle de a à b sur la carte graphique (le noyau spv, écrit par taranis/noyau_vtx.py). Chaque accès du corps à
/// l'étage 2 est donné par son adresse aux tours a, a + 1 et b - 1 (son genre : écriture ou lecture ; sa clé : la même
/// pour la même expression) : il doit avancer d'un pas constant (sinon : non). Une lecture qui croise l'écriture d'une
/// autre expression, ou toutes les écritures sur le même mot, et la boucle reste aux cylindres (l'ordre compterait).
/// La fenêtre monte en mots de 64 bits (un mot plus large : non), redescend, et seuls les mots changés sont écrits.
#[allow(dead_code)]
fn taranis_boucle(c: &mut Ctx, spv: &[u32], a: u128, b: u128, acces: &[(bool, u128, u128, u128, u32)], ext: &[u128]) -> bool {
    const M62: u64 = (1u64 << 62) - 1;
    let n = (b as u64).wrapping_sub(a as u64);
    if n == 0 || n > (1u64 << 40) || ext.iter().any(|&v| v >> 64 != 0) {
        return false;
    }
    let carte = match taranis_vk::carte() {
        Some(k) => k,
        None => return false,
    };
    let mut fen: Vec<(bool, u64, u64, u32)> = Vec::new();
    let (mut lo, mut hi) = (u64::MAX, 0u64);
    for &(ecrit, x0, x1, xl, cle) in acces {
        let (s0, s1, sl) = ((x0 as u64) & M62, (x1 as u64) & M62, (xl as u64) & M62);
        let d = if n > 1 { s1.wrapping_sub(s0) } else { 0 };
        if n > 1 && s0.wrapping_add(d.wrapping_mul(n - 1)) != sl {
            return false;
        }
        if ecrit && d == 0 && n > 1 {
            return false;
        }
        let (mn, mx) = if (d as i64) >= 0 { (s0, sl) } else { (sl, s0) };
        lo = lo.min(mn);
        hi = hi.max(mx + 1);
        fen.push((ecrit, mn, mx, cle));
    }
    for x in &fen {
        for y in &fen {
            if x.0 && (x.3 != y.3) && x.1 <= y.2 && y.1 <= x.2 {
                return false;
            }
        }
    }
    if fen.is_empty() {
        lo = 0;
        hi = 0;
    }
    let len = (hi - lo) as usize;
    if len > (1usize << 31) {
        return false;
    }
    if c.m.a_des_cubes_sur_disque() {
        return false;
    }
    // la fenêtre montée page par page (une page absente : des zéros) ; un mot de plus de 64 bits, ou un brin : non
    let t_cube = std::time::Instant::now();
    let mut f = vec![0u64; len];
    let mut vide = true;
    let mut k = 0usize;
    while k < len {
        let adr = lo + k as u64;
        let dans_page = (65536 - (adr & 65535)) as usize;
        let m = dans_page.min(len - k);
        if let Some((mots, brins)) = c.m.page_si(etg(adr as u128, 2)) {
            if brins {
                return false;
            }
            let src = unsafe { std::slice::from_raw_parts(mots.add((adr & 65535) as usize), m) };
            for (j, &w) in src.iter().enumerate() {
                if w >> 64 != 0 {
                    return false;
                }
                f[k + j] = w as u64;
                vide &= w == 0;
            }
        }
        k += m;
    }
    let monte_cube = t_cube.elapsed().as_secs_f64() * 1e3;
    let orig = f.clone();
    let mut p = vec![0u64; 6 + ext.len()];
    p[1] = a as u64;
    p[2] = n;
    p[3] = lo;
    p[4] = len as u64;
    for (k, &v) in ext.iter().enumerate() {
        p[6 + k] = v as u64;
    }
    let temps = match carte.lancer(spv, &mut f, &mut p, n, vide) {
        Ok(t) => t,
        Err(e) => {
            if taranis_vk::bavard() {
                eprintln!("taranis : la carte refuse ({}) : les cylindres prennent la boucle", e);
            }
            return false;
        }
    };
    if p[0] != 0 {
        if taranis_vk::bavard() {
            eprintln!("taranis : un accès hors de la fenêtre : les cylindres rejouent la boucle");
        }
        return false;
    }
    // les mots changés, rangés dans le cube page par page
    let t_cube = std::time::Instant::now();
    let mut k = 0usize;
    while k < len {
        let adr = lo + k as u64;
        let m = ((65536 - (adr & 65535)) as usize).min(len - k);
        if f[k..k + m] != orig[k..k + m] {
            let (mots, _, _) = c.m.page_de(etg(adr as u128, 2));
            let dst = unsafe { std::slice::from_raw_parts_mut(mots.add((adr & 65535) as usize), m) };
            for j in 0..m {
                if f[k + j] != orig[k + j] {
                    dst[j] = f[k + j] as u128;
                }
            }
        }
        k += m;
    }
    c.oublier_pages();
    if taranis_vk::bavard() {
        eprintln!("taranis : {} tours sur la carte, fenêtre de {} mots{} ; lire le cube {:.1} ms, monter {:.1} ms, \
                   la carte {:.1} ms, redescendre {:.1} ms, ranger dans le cube {:.1} ms",
                  n, len, if vide { " (vide : remplie sur la carte)" } else { "" }, monte_cube, temps[0], temps[1],
                  temps[2], t_cube.elapsed().as_secs_f64() * 1e3);
    }
    true
}
