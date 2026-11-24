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

/// 0.820 : les pages de l'étage 2 changées par le processeur depuis leur dernière montée sur la carte (un bit par page,
/// pages 0 à 65535) : le modèle classique sait ce qui a changé sans comparer (marqué à l'entrée d'une page dans le chemin
/// d'écriture d'une machine, et à la fusion des cylindres ; la carte oublie les chemins de la machine à chaque lancement)
static SALES: [std::sync::atomic::AtomicU64; 1024] = [const { std::sync::atomic::AtomicU64::new(0) }; 1024];

#[inline(always)]
fn salir(k: u128) {
    if k >> 120 == 2 {
        let pg = (k & ((1u128 << 120) - 1)) as u64;
        if pg < 65536 {
            SALES[(pg >> 6) as usize].fetch_or(1u64 << (pg & 63), std::sync::atomic::Ordering::Relaxed);
        }
    }
}

#[allow(dead_code)]
fn sale(pg: u64) -> bool {
    SALES[(pg >> 6) as usize].load(std::sync::atomic::Ordering::Relaxed) >> (pg & 63) & 1 == 1
}

#[allow(dead_code)]
fn nettoyer(pg: u64) {
    SALES[(pg >> 6) as usize].fetch_and(!(1u64 << (pg & 63)), std::sync::atomic::Ordering::Relaxed);
}

// 0.830 : le gène « carte_directe » de Gutuater (choisi à la forge : @CARTE_DIRECTE@) : vrai, la carte a une place
// par page des 256 premières fréquences (65 536 places : la page f << 8 | q à la place f << 8 | q, sans mêler ni
// chasser : l'épissage rapide du processeur, comme le monde d'un seul tenant de Taranis) ; faux, 1 024 places mêlées.
const CARTE_DIRECTE: bool = false;
const CARTE: usize = if CARTE_DIRECTE { 65536 } else { 1024 };

struct Carte {
    k: [u64; CARTE],           // 0.808 : l'étiquette de chaque place : le numéro de la page + 1 (0 : place libre) ; 0.830 :
                               // plus la génération (oublier la carte ne la remet plus à zéro : la génération change)
    gen: u64,
    l: [*mut u128; CARTE],
    e: [*mut u128; CARTE],
    r: [*mut u64; CARTE],
    w: [*mut u64; CARTE],
}

/// 0.808 : la place d'une page de l'étage 2 dans la carte : son numéro mêlé (les pages des cubes de fréquences
/// différentes, qui ont les mêmes 8 bits bas, ne tombent pas à la même place)
#[inline(always)]
fn place_carte(pg: u64) -> usize {
    if CARTE_DIRECTE {
        return (pg as usize) & (CARTE - 1);
    }
    ((pg ^ (pg >> 8).wrapping_mul(0x9E37) ^ (pg >> 18)) as usize) & (CARTE - 1)
}

impl Carte {
    fn neuve() -> Box<Carte> {
        Box::new(Carte { k: [0; CARTE], gen: 1, l: [std::ptr::null_mut(); CARTE], e: [std::ptr::null_mut(); CARTE],
                         r: [std::ptr::null_mut(); CARTE], w: [std::ptr::null_mut(); CARTE] })
    }
    fn oublier(&mut self) {
        self.gen += 1;
        if self.gen >= 1 << 23 {
            self.k = [0; CARTE];
            self.gen = 1;
        }
    }
    #[inline(always)]
    fn etiquette(&self, pg: u64) -> u64 {
        (pg + 1) | (self.gen << 40)
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
    pire: f64,           // le pire temps de cet essai (0.814 : un travail qui change d'un passage à l'autre)
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
        Reglage { cle, etat: std::sync::Mutex::new(EtatReglage { essai: 0, mesures: 0, temps: f64::MAX, pire: 0.0, meilleur: 0,
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
        if t > e.pire {
            e.pire = t;
        }
        if e.mesures < 2 {
            return;
        }
        let (essai, temps, pire) = (e.essai, e.temps, e.pire);
        e.mesures = 0;
        e.temps = f64::MAX;
        e.pire = 0.0;
        // 0.814 : deux passages du même essai à plus du double l'un de l'autre : le travail de cette boucle change d'un
        // passage à l'autre (une même boucle qui joue des étages différents) ; le temps ne peut pas juger : variable ;
        // il garde tous les fils (ce qui ne perd jamais beaucoup) et ne retient rien
        if pire > 2.0 * temps && e.deviner != usize::MAX {
            e.confiance = Confiance::Variable;
            e.fige = true;
            e.meilleur = tous;
            dire_reglage(format!("la boucle de la ligne {} : son travail change d'un passage à l'autre ({:.1} à {:.1} ms) ; \
                                  le temps ne peut pas juger : tous les fils ({})", ligne, temps * 1e3, pire * 1e3, tous));
            return;
        }
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

/// 0.816 : le vergobret choisit entre la carte graphique et le processeur, pour chaque boucle qui sait aller à la
/// carte (le mode pages) : un passage sur la carte pour la chauffer (le noyau se prépare, les pages se créent), un
/// passage sur la carte mesuré, un au processeur mesuré ; puis le plus rapide. VTX_CARTE=1 : toujours la carte ;
/// VTX_CARTE=0 : jamais ; VTX_REGLAGE=1 : il dit son choix.
#[allow(dead_code)]
pub struct Choix {
    etat: std::sync::Mutex<(u8, f64, f64)>, // (le passage : 0 chauffer, 1 la carte, 2 le processeur, 3 choisi ; carte ; processeur)
}

#[allow(dead_code)]
impl Choix {
    pub const fn neuf() -> Choix {
        Choix { etat: std::sync::Mutex::new((0, 0.0, 0.0)) }
    }
    pub fn carte_voulue(&self) -> bool {
        match std::env::var("VTX_CARTE").as_deref() {
            Ok("0") => return false,
            Ok("1") => return true,
            _ => {}
        }
        let e = self.etat.lock().unwrap();
        match e.0 {
            0 | 1 => true,
            2 => false,
            _ => e.1 < e.2,
        }
    }
    /// 0.824 : une boucle d'un lot de la carte : le lot ne se coupe pas (chacune de ses boucles mesurée seule ne dit
    /// rien : celles qui attendent ne coûtent rien, la dernière porte tout le lot) : avec Taranis, elle reste à la carte
    pub fn carte_voulue_lot(&self) -> bool {
        match std::env::var("VTX_CARTE").as_deref() {
            Ok("0") => return false,
            Ok("1") => return true,
            _ => {}
        }
        if epissage_rapide() && std::env::var("VTX_LOT").map_or(true, |v| v != "0") {
            return true;
        }
        self.carte_voulue()
    }
    pub fn noter(&self, carte: bool, duree: std::time::Duration, ligne: u32) {
        let t = duree.as_secs_f64();
        let mut e = self.etat.lock().unwrap();
        match (e.0, carte) {
            (0, true) => e.0 = 1,
            (0, false) => e.0 = 3, // pas de carte : rien à choisir
            (1, true) => {
                e.1 = t;
                e.0 = 2;
            }
            (2, false) => {
                e.2 = t;
                e.0 = 3;
                let tc = e.1;
                let la_carte = tc < e.2 * 0.97;
                if !la_carte {
                    e.1 = f64::MAX;
                }
                dire_reglage(format!("la boucle de la ligne {} : la carte {:.1} ms, le processeur {:.1} ms : {}", ligne,
                                     tc * 1e3, e.2 * 1e3, if la_carte { "la carte" } else { "le processeur" }));
            }
            _ => {}
        }
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
    for k in &ordre {
        salir(*k);
    }
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

/// 0.815 : le diagnostic VTX_SANS_PROMESSE=1 (les lectures des bandes non notées ; dit une fois)
#[allow(dead_code)]
fn sans_promesse() -> bool {
    static S: std::sync::OnceLock<bool> = std::sync::OnceLock::new();
    *S.get_or_init(|| {
        let b = std::env::var("VTX_SANS_PROMESSE").map_or(false, |v| v == "1");
        if b {
            eprintln!("diagnostic : VTX_SANS_PROMESSE=1 : les lectures des bandes ne sont pas notées ; la promesse n'est pas vérifiée");
        }
        b
    })
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
        if self.carte.k[h] == self.carte.etiquette(pg) {
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
                if self.carte.k[q] != self.carte.etiquette(pg) {
                    self.carte.k[q] = self.carte.etiquette(pg);
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
        if self.carte.k[h] == self.carte.etiquette(pg) {
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
                if self.carte.k[q] != self.carte.etiquette(pg) {
                    self.carte.k[q] = self.carte.etiquette(pg);
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
            // 0.74c : le mot lu est noté ; 0.815 : VTX_SANS_PROMESSE=1 (un diagnostic, pour mesurer ce que coûte la
            // promesse) : dans les bandes, les lectures ne sont plus notées (la promesse n'est plus vérifiée)
            let bits: *mut u64 = if o.partage && sans_promesse() {
                std::ptr::null_mut()
            } else {
                o.lus.entry(k).or_insert_with(|| Box::new([0u64; 1024])).as_mut_ptr()
            };
            if !bits.is_null() {
                unsafe { *bits.add(j >> 6) |= 1u64 << (j & 63) };
            }
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
        salir(k);
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
    // 0.830 : un gène choisi à la forge (la carte directe) : le temps du programme entier, pour Gutuater, qui le mettra
    // en face de celui de l'autre variante (« temps GENE LIEU VARIANTE MICROSECONDES »)
    if let Some(d) = dossier_gutuater() {
        if std::env::var("VTX_GUTUATER_TEMPS").map_or(false, |v| v == "1") {
            use std::io::Write;
            if let Ok(mut f) = std::fs::OpenOptions::new().create(true).append(true).open(d.join("gutuater.mesures")) {
                let _ = writeln!(f, "temps carte_directe 0 {} {}", if CARTE_DIRECTE { 1 } else { 0 }, duree.as_micros());
            }
        }
    }
}

// ------------------------------------------------------------------ Taranis : une boucle en segments sur la carte
/// La boucle de a à b sur la carte graphique (le noyau spv, écrit par taranis/noyau_vtx.py). Chaque accès du corps à
/// l'étage 2 est donné par son adresse aux tours a, a + 1 et b - 1 (son genre : écriture ou lecture ; sa clé : la même
/// pour la même expression) : il doit avancer d'un pas constant (sinon : non). Une lecture qui croise l'écriture d'une
/// autre expression, ou toutes les écritures sur le même mot, et la boucle reste aux cylindres (l'ordre compterait).
/// La fenêtre monte en mots de 64 bits (un mot plus large : non), redescend, et seuls les mots changés sont écrits.
#[allow(dead_code)]
/// 0.816 : Taranis en mode pages : la boucle entière sur la carte, l'étage 2 monté page par page (la carte du vergobret
/// sur la carte graphique : une table des pages) ; la promesse vérifiée là-bas (deux tours qui écrivent le même mot, une
/// page absente : la carte le dit) et ici (une page à la fois lue et écrite : refusé) ; si quelque chose manque, la
/// boucle reste au processeur (fait reste faux : le résultat est toujours celui de Lugus).
#[allow(dead_code)]
fn taranis_boucle_pages(c: &mut Ctx, spv: &[u32], spv64: &[u32], spv64r: &'static [u32], a: u128, b: u128, ext: &[u128],
                        region: usize, differe: bool, lieu: u32) -> bool {
    // 0.817 : le noyau en entiers de 64 bits de la carte, si elle les fait
    let k = match taranis_vk::carte() {
        Some(k) => k,
        None => return false,
    };
    // 0.820 : l'épissage rapide (VTX_EPISSAGE=rapide : le modèle classique), avec le 64 bits de la carte
    let rapide = k.int64 && epissage_rapide();
    if rapide {
        // 0.821 : Taranis, le noyau de la carte
        // 0.824 : VTX_LOT=0 : chaque boucle part seule (sans lot)
        let differe = differe && std::env::var("VTX_LOT").map_or(true, |v| v != "0");
        // 0.825 : le gène « lot » : Gutuater (son ARN) dit s'il s'exprime ; inconnu ou variable : le vergobret mesure
        // le lot avec et sans, et note ses mesures pour Gutuater
        if lieu == 0 {
            return taranis_direct(c, spv64r, a, b, ext, region, differe);
        }
        let dernier = !differe;
        let avec = gene_lot_debut(lieu, region == 0);
        let fait = taranis_direct(c, spv64r, a, b, ext, region, differe && avec);
        if dernier {
            gene_lot_fin(lieu);
        }
        return fait;
    }
    let choisi = if k.int64 { spv64 } else { spv };
    taranis_boucle_pages_(c, choisi, a, b, ext, true, false)
}

/// 0.825 : Gutuater, le gène « lot ». Son ARN (gutuater.arn, à côté du programme) dit, pour chaque lot (la ligne de
/// sa première boucle) : vrai, le lot s'exprime ; faux, il est tu (chaque boucle part seule) ; inconnu ou variable, le
/// vergobret le mesure : un passage pour chauffer, puis sans, avec, sans, avec (le meilleur de chaque), et il garde le
/// plus rapide pour la suite ; ses mesures vont dans gutuater.mesures, que Gutuater lira. VTX_GUTUATER=0 : rien de
/// tout cela (le lot, toujours, comme en 0.824).
#[allow(dead_code)]
struct GeneLot {
    passe: u32,
    avec: bool,             // ce passage : le lot exprimé ?
    t0: Option<std::time::Instant>,
    t_avec: f64,
    t_sans: f64,
    choisi: Option<bool>,   // le choix pour ce qui reste de l'exécution
    inverse: bool,          // 0.826 : l'ordre des mesures, tiré au hasard
}

/// 0.826 : un bit tiré au hasard (le temps de la machine, à la nanoseconde)
#[allow(dead_code)]
fn bit_au_hasard() -> bool {
    std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map_or(false, |d| (d.subsec_nanos() >> 7) & 1 == 1)
}

#[allow(dead_code)]
fn dossier_gutuater() -> Option<std::path::PathBuf> {
    if std::env::var("VTX_GUTUATER").map_or(false, |v| v == "0") {
        return None;
    }
    std::env::current_exe().ok().and_then(|e| e.parent().map(|d| d.to_path_buf()))
}

/// l'ARN : (gène, lieu) → l'état (0 inconnu, 1 faux, 2 vrai, 3 variable)
#[allow(dead_code)]
fn arn_gutuater() -> &'static std::collections::HashMap<(String, u32), u8> {
    static A: std::sync::OnceLock<std::collections::HashMap<(String, u32), u8>> = std::sync::OnceLock::new();
    A.get_or_init(|| {
        let mut a = std::collections::HashMap::new();
        if let Some(d) = dossier_gutuater() {
            if let Ok(t) = std::fs::read_to_string(d.join("gutuater.arn")) {
                for l in t.lines() {
                    let m: Vec<&str> = l.split_whitespace().collect();
                    if m.len() >= 3 && !m[0].starts_with('#') {
                        if let Ok(lieu) = m[1].parse::<u32>() {
                            let e = match m[2] { "faux" => 1, "vrai" => 2, "variable" => 3, _ => 0 };
                            a.insert((m[0].to_string(), lieu), e);
                        }
                    }
                }
            }
        }
        a
    })
}

#[allow(dead_code)]
fn genes_lot() -> &'static std::sync::Mutex<std::collections::HashMap<u32, GeneLot>> {
    static G: std::sync::OnceLock<std::sync::Mutex<std::collections::HashMap<u32, GeneLot>>> = std::sync::OnceLock::new();
    G.get_or_init(|| std::sync::Mutex::new(std::collections::HashMap::new()))
}

/// au début de chaque boucle d'un lot : le lot s'exprime-t-il à ce passage ? (décidé à sa première boucle)
#[allow(dead_code)]
fn gene_lot_debut(lieu: u32, premiere: bool) -> bool {
    if dossier_gutuater().is_none() {
        return true;
    }
    let mut gs = genes_lot().lock().unwrap();
    let g = gs.entry(lieu).or_insert_with(|| {
        let e = arn_gutuater().get(&("lot".to_string(), lieu)).copied().unwrap_or(0);
        let choisi = match e { 2 => Some(true), 1 => Some(false), _ => None };
        match e {
            2 => dire_reglage(format!("le lot de la ligne {} : Gutuater dit vrai : il s'exprime, sans essai", lieu)),
            1 => dire_reglage(format!("le lot de la ligne {} : Gutuater dit faux : il est tu, sans essai", lieu)),
            3 => dire_reglage(format!("le lot de la ligne {} : Gutuater dit variable : je mesure encore", lieu)),
            _ => dire_reglage(format!("le lot de la ligne {} : Gutuater ne sait pas : je mesure", lieu)),
        }
        GeneLot { passe: 0, avec: true, t0: None, t_avec: f64::MAX, t_sans: f64::MAX, choisi, inverse: bit_au_hasard() }
    });
    if premiere {
        g.avec = match g.choisi {
            Some(x) => x,
            // 0 chauffer (avec), puis sans et avec en alternance ; 0.826 : l'ordre tiré au hasard (au temps de la
            // machine), pour qu'aucune variante ne passe toujours la première (un biais : le cache, la chaleur)
            None => g.passe == 0 || ((g.passe % 2 == 0) != g.inverse),
        };
        g.t0 = Some(std::time::Instant::now());
    }
    g.avec
}

/// à la fin de la dernière boucle d'un lot : la mesure de ce passage
#[allow(dead_code)]
fn gene_lot_fin(lieu: u32) {
    if dossier_gutuater().is_none() {
        return;
    }
    let mut gs = genes_lot().lock().unwrap();
    let g = match gs.get_mut(&lieu) {
        Some(g) => g,
        None => return,
    };
    if g.choisi.is_some() {
        return;
    }
    let t = match g.t0.take() {
        Some(t0) => t0.elapsed().as_secs_f64(),
        None => return,
    };
    if g.passe >= 1 {
        if g.avec {
            g.t_avec = g.t_avec.min(t);
        } else {
            g.t_sans = g.t_sans.min(t);
        }
    }
    g.passe += 1;
    if g.passe == 5 {
        let avec = g.t_avec <= g.t_sans;
        g.choisi = Some(avec);
        dire_reglage(format!("le lot de la ligne {} : avec {:.1} ms, sans {:.1} ms : {} ; noté pour Gutuater", lieu,
                             g.t_avec * 1e3, g.t_sans * 1e3, if avec { "le lot" } else { "chaque boucle seule" }));
        if let Some(d) = dossier_gutuater() {
            use std::io::Write;
            if let Ok(mut f) = std::fs::OpenOptions::new().create(true).append(true).open(d.join("gutuater.mesures")) {
                let _ = writeln!(f, "mesure lot {} {} {}", lieu, (g.t_avec * 1e6) as u64, (g.t_sans * 1e6) as u64);
            }
        }
    }
}

/// 0.826 : le gène « fondre » : le lot de la ligne `lieu` en un seul noyau. Comme pour le lot : l'ARN de Gutuater dit
/// vrai (fondu, sans essai), faux (séparé, sans essai) ; inconnu ou variable : le vergobret mesure (séparé pour chauffer,
/// fondu pour chauffer, puis séparé, fondu, séparé, fondu) et garde le meilleur. Le noyau fondu ne va qu'à la carte, avec
/// l'épissage rapide (Taranis) ; sinon, le lot séparé.
static FONDRE_LIEU: std::sync::atomic::AtomicU32 = std::sync::atomic::AtomicU32::new(0);

#[allow(dead_code)]
fn taranis_fondre(c: &mut Ctx, spv: &'static [u32], a: u128, b: u128, ext: &[u128], lieu: u32) -> bool {
    match taranis_vk::carte() {
        Some(k) if k.int64 && epissage_rapide() => {}
        _ => return false,
    }
    if std::env::var("VTX_CARTE").map_or(false, |v| v == "0") {
        return false;
    }
    taranis_vider(c);
    FONDRE_LIEU.store(lieu, std::sync::atomic::Ordering::Relaxed);
    taranis_direct(c, spv, a, b, ext, 0, false)
}

#[allow(dead_code)]
fn genes_fondre() -> &'static std::sync::Mutex<std::collections::HashMap<u32, GeneLot>> {
    static G: std::sync::OnceLock<std::sync::Mutex<std::collections::HashMap<u32, GeneLot>>> = std::sync::OnceLock::new();
    G.get_or_init(|| std::sync::Mutex::new(std::collections::HashMap::new()))
}

/// ce passage : fondu ? (vrai : le noyau fondu est essayé ; s'il refuse, le lot séparé se joue)
#[allow(dead_code)]
fn gene_fondre_debut(lieu: u32) -> bool {
    if dossier_gutuater().is_none() || !epissage_rapide() || std::env::var("VTX_CARTE").map_or(false, |v| v == "0") {
        return false;
    }
    let mut gs = genes_fondre().lock().unwrap();
    let g = gs.entry(lieu).or_insert_with(|| {
        let e = arn_gutuater().get(&("fondre".to_string(), lieu)).copied().unwrap_or(0);
        let choisi = match e { 2 => Some(true), 1 => Some(false), _ => None };
        match e {
            2 => dire_reglage(format!("le lot de la ligne {} : Gutuater dit fondre vrai : un seul noyau, sans essai", lieu)),
            1 => dire_reglage(format!("le lot de la ligne {} : Gutuater dit fondre faux : les étages séparés, sans essai", lieu)),
            3 => dire_reglage(format!("le lot de la ligne {} : Gutuater dit fondre variable : je mesure encore", lieu)),
            _ => dire_reglage(format!("le lot de la ligne {} : fondre, Gutuater ne sait pas : je mesure", lieu)),
        }
        GeneLot { passe: 0, avec: false, t0: None, t_avec: f64::MAX, t_sans: f64::MAX, choisi, inverse: bit_au_hasard() }
    });
    g.avec = match g.choisi {
        Some(x) => x,
        // 0 séparé (chauffer), 1 fondu (chauffer), puis l'un et l'autre en alternance, dans un ordre tiré au hasard
        None => if g.passe < 2 { g.passe == 1 } else { (g.passe % 2 == 1) != g.inverse },
    };
    g.t0 = Some(std::time::Instant::now());
    g.avec
}

#[allow(dead_code)]
fn gene_fondre_fin(lieu: u32, fondu: bool) {
    if dossier_gutuater().is_none() {
        return;
    }
    let mut gs = genes_fondre().lock().unwrap();
    let g = match gs.get_mut(&lieu) {
        Some(g) => g,
        None => return,
    };
    let t = match g.t0.take() {
        Some(t0) => t0.elapsed().as_secs_f64(),
        None => return,
    };
    if g.avec && !fondu {
        // le noyau fondu a été refusé (la carte, un tour trop grand…) : les étages séparés, pour la suite
        if g.choisi != Some(false) {
            dire_reglage(format!("le lot de la ligne {} : le noyau fondu est refusé ; les étages séparés", lieu));
        }
        g.choisi = Some(false);
        return;
    }
    if g.choisi.is_some() {
        return;
    }
    if g.passe >= 2 {
        if g.avec {
            g.t_avec = g.t_avec.min(t);
        } else {
            g.t_sans = g.t_sans.min(t);
        }
    }
    g.passe += 1;
    if g.passe == 6 {
        let fondre = g.t_avec <= g.t_sans;
        g.choisi = Some(fondre);
        dire_reglage(format!("le lot de la ligne {} : fondu {:.1} ms, séparé {:.1} ms : {} ; noté pour Gutuater", lieu,
                             g.t_avec * 1e3, g.t_sans * 1e3, if fondre { "un seul noyau" } else { "les étages séparés" }));
        if let Some(d) = dossier_gutuater() {
            use std::io::Write;
            if let Ok(mut f) = std::fs::OpenOptions::new().create(true).append(true).open(d.join("gutuater.mesures")) {
                let _ = writeln!(f, "mesure fondre {} {} {}", lieu, (g.t_avec * 1e6) as u64, (g.t_sans * 1e6) as u64);
            }
        }
    }
}

/// 0.821 : Taranis. Le monde (l'étage 2) rangé sur la carte, chaque fréquence d'un seul tenant (la place 0 : une page de
/// zéros, où lit toute adresse hors du monde) ; la table dit, pour chaque fréquence f, son premier mot (table[f]) et sa
/// taille (table[256 + f]) ; ne montent que les pages marquées (SALES) ; ne redescendent que les fréquences écrites.
struct EtatTaranis {
    res: Option<taranis_vk::Residence>,
    freq: Vec<(u32, u32)>,          // pour chaque fréquence : (première place, nombre de places) ; (0, 0) : absente
    pret: bool,
    // 0.823 : la page du processeur de chaque place (pour redescendre sans relire toutes les pages)
    pages: Vec<usize>,
    // 0.823 : les fréquences de la carte (200 et plus) écrites par la carte et pas encore redescendues
    perimees: Vec<bool>,
    // 0.824 : le lot qui attend : (noyau, sa longueur, ses tours, sa région) ; les pages à monter ; la table ; les
    // paramètres de toutes les régions ; le temps de préparer
    lot: Vec<(usize, usize, u64, usize)>,
    lot_montees: Vec<u32>,
    table_lot: Vec<u32>,
    params_lot: Vec<u64>,
    t_monte: f64,
}

/// 0.823 : les fréquences 200 et plus sont celles de la carte : ce qu'elle y écrit reste sur la carte
const FREQ_CARTE: usize = 200;
unsafe impl Send for EtatTaranis {}

#[allow(dead_code)]
fn etat_taranis() -> &'static std::sync::Mutex<EtatTaranis> {
    static R: std::sync::OnceLock<std::sync::Mutex<EtatTaranis>> = std::sync::OnceLock::new();
    R.get_or_init(|| std::sync::Mutex::new(EtatTaranis { res: None, freq: vec![(0, 0); 256], pret: false, pages: Vec::new(),
        perimees: vec![false; 256], lot: Vec::new(), lot_montees: Vec::new(), table_lot: Vec::new(), params_lot: vec![0; 512],
        t_monte: 0.0 }))
}

/// 0.823 : avant qu'une boucle ne se joue au processeur, ce que la carte tient seule (les fréquences de la carte
/// qu'elle a écrites) redescend : le processeur lit alors ce que la carte a fait
#[allow(dead_code)]
fn taranis_rapatrier(c: &mut Ctx) {
    taranis_vider(c);
    let mut g = etat_taranis().lock().unwrap();
    if !g.pret || !g.perimees.iter().any(|&x| x) {
        return;
    }
    let carte = match taranis_vk::carte() {
        Some(k) => k,
        None => return,
    };
    let fs: Vec<usize> = (0..256).filter(|&f| g.perimees[f]).collect();
    let places: Vec<u32> = fs.iter().flat_map(|&f| (0..g.freq[f].1).map(move |q| (f, q))).map(|(f, q)| g.freq[f].0 + q).collect();
    let ok = {
        let EtatTaranis { res, .. } = &mut *g;
        carte.redescendre(res.as_mut().unwrap(), &places).is_ok()
    };
    let miroir = g.res.as_ref().unwrap().miroir as usize;
    for &f in &fs {
        for q in 0..g.freq[f].1 {
            let s = (g.freq[f].0 + q) as usize;
            let pg = ((f as u64) << 8) | q as u64;
            let src = unsafe { std::slice::from_raw_parts((miroir as *const u64).add(s * 65536), 65536) };
            let p = if g.pages[s] != 0 { g.pages[s] as *mut u128 } else { c.m.page_de(adresse_page((2u128 << 120) | pg as u128)).0 };
            let dst = unsafe { std::slice::from_raw_parts_mut(p, 65536) };
            for (d, &w) in dst.iter_mut().zip(src) {
                *d = if ok { w as u128 } else { *d };
            }
        }
        g.perimees[f] = false;
    }
    if !ok {
        g.pret = false;
    }
    c.oublier_pages();
}

#[allow(dead_code)]
fn taranis_direct(c: &mut Ctx, spv: &'static [u32], a: u128, b: u128, ext: &[u128], region: usize, differe: bool) -> bool {
    let n = (b as u64).wrapping_sub(a as u64);
    if n == 0 || n > (1u64 << 31) || ext.iter().any(|&v| v >> 64 != 0) {
        return false;
    }
    let carte = match taranis_vk::carte() {
        Some(k) => k,
        None => return false,
    };
    if c.m.a_des_cubes_sur_disque() {
        return false;
    }
    // 0.831 : un noyau qui garde le minimum (Capability Int64Atomics) ne va qu'à une carte qui le sait
    if !carte.atomique64 && spv.windows(2).take(16).any(|w| w[0] == ((2 << 16) | 17) && w[1] == 12) {
        if taranis_vk::bavard() {
            eprintln!("taranis : la carte ne garde pas le minimum de 64 bits : la boucle reste au processeur");
        }
        return false;
    }
    let bavard = taranis_vk::bavard();
    let t0 = std::time::Instant::now();
    c.oublier_pages();
    let mut g = etat_taranis().lock().unwrap();
    // 0.823 : rien de changé depuis le dernier lancement (aucune page marquée) : rien à relire, rien ne monte
    let rien = g.pret && SALES.iter().all(|w| w.load(std::sync::atomic::Ordering::Relaxed) == 0);
    // les pages de l'étage 2 du processeur, par fréquence
    let mut liste: Vec<(u64, *mut u128)> = Vec::new();
    for (k, p, brins) in if rien { Vec::new() } else { c.m.instantane() } {
        if k >> 120 != 2 {
            continue;
        }
        let pg = (k & ((1u128 << 120) - 1)) as u64;
        if pg >= 65536 {
            continue;
        }
        if brins {
            return false;
        }
        liste.push((pg, p));
    }
    let mut besoin = vec![0u32; 256];
    for &(pg, _) in &liste {
        let (f, q) = ((pg >> 8) as usize, (pg & 255) as u32);
        besoin[f] = besoin[f].max(q + 1);
    }
    // le rangement : refait (tout monte) si une fréquence est nouvelle ou a grandi
    let refaire = !rien && (!g.pret || (0..256).any(|f| besoin[f] > g.freq[f].1));
    if refaire && !g.lot.is_empty() {
        drop(g);
        taranis_vider(c);
        return taranis_direct(c, spv, a, b, ext, region, differe);
    }
    if refaire && g.pret && g.perimees.iter().any(|&x| x) {
        // le rangement va être refait (tout remonte du processeur) : ce que la carte tient seule redescend d'abord
        drop(g);
        taranis_rapatrier(c);
        return taranis_direct(c, spv, a, b, ext, region, differe);
    }
    let mut montees: Vec<u32> = Vec::new();
    if refaire {
        let mut place = 1u32;
        for f in 0..256 {
            if besoin[f] > 0 {
                g.freq[f] = (place, besoin[f]);
                place += besoin[f];
            } else {
                g.freq[f] = (0, 0);
            }
        }
        let cap = place as usize;
        let EtatTaranis { res, .. } = &mut *g;
        if let Err(e) = carte.residence(res, cap) {
            if bavard {
                eprintln!("taranis : {}", e);
            }
            return false;
        }
        let mir = g.res.as_ref().unwrap().miroir;
        unsafe { std::ptr::write_bytes(mir, 0, cap * 65536) };
        montees = (0..cap as u32).collect();
        g.pret = true;
        g.pages = vec![0; cap];
        g.perimees = vec![false; 256];
    }
    let miroir = g.res.as_ref().unwrap().miroir as usize;
    let mut a_copier: Vec<(usize, *mut u128)> = Vec::new();
    for &(pg, p) in &liste {
        let (f, q) = ((pg >> 8) as usize, (pg & 255) as u32);
        let s = (g.freq[f].0 + q) as usize;
        if s < g.pages.len() {
            g.pages[s] = p as usize;
        }
        if refaire || sale(pg) {
            if f >= FREQ_CARTE && g.perimees[f] && !refaire {
                // le processeur a écrit une page de la carte qu'il n'avait pas : la carte la prend telle quelle
                g.perimees[f] = false;
            }
            a_copier.push((s, p));
            if !refaire {
                montees.push(s as u32);
            }
        }
        nettoyer(pg);
    }
    // la copie vers le miroir, sur tous les cœurs (un mot de plus de 64 bits : la boucle reste au processeur)
    let nt = cylindres_voulus().max(1).min(a_copier.len().max(1));
    let morceau = a_copier.len().div_ceil(nt).max(1);
    let a_copier_u: Vec<(usize, usize)> = a_copier.iter().map(|&(s, p)| (s, p as usize)).collect();
    let bon = std::thread::scope(|sc| {
        let fils: Vec<_> = a_copier_u.chunks(morceau).map(|ch| sc.spawn(move || {
            for &(s, p) in ch {
                let src = unsafe { std::slice::from_raw_parts(p as *const u128, 65536) };
                let dst = unsafe { std::slice::from_raw_parts_mut((miroir as *mut u64).add(s * 65536), 65536) };
                for (d, &w) in dst.iter_mut().zip(src) {
                    if w >> 64 != 0 {
                        return false;
                    }
                    *d = w as u64;
                }
            }
            true
        })).collect();
        fils.into_iter().all(|h| h.join().unwrap())
    });
    if !bon {
        g.pret = false;
        return false;
    }
    let mut table = vec![0u32; 512];
    for f in 0..256 {
        table[f] = g.freq[f].0.wrapping_mul(65536);
        table[256 + f] = g.freq[f].1.wrapping_mul(65536);
    }
    let t_monte = t0.elapsed().as_secs_f64() * 1e3;
    // 0.824 : la boucle entre dans le lot (ses paramètres dans sa région) ; elle part maintenant, avec celles qui
    // attendaient, sauf si une autre boucle de la carte la suit (differe)
    let base = region * 64;
    for k in 0..64 {
        g.params_lot[base + k] = 0;
    }
    g.params_lot[base + 1] = a as u64;
    g.params_lot[base + 2] = n;
    for (k, &v) in ext.iter().enumerate() {
        g.params_lot[base + 6 + k] = v as u64;
    }
    g.lot.push((spv.as_ptr() as usize, spv.len(), n, region));
    g.lot_montees.extend(montees);
    g.table_lot = table;
    g.t_monte += t_monte;
    if differe {
        return true;
    }
    let seul = g.lot.len() == 1;
    match taranis_envoyer(c, &mut *g, bavard) {
        Some(true) => true,
        Some(false) if seul => false,
        _ => {
            eprintln!("taranis : un lot de la carte a échoué (une écriture hors du monde) ; relancer avec VTX_LOT=0");
            std::process::exit(3);
        }
    }
}

/// 0.824 : vide le lot de la carte (s'il attend) : il part, ce qu'il a écrit redescend
#[allow(dead_code)]
fn taranis_vider(c: &mut Ctx) {
    let mut g = etat_taranis().lock().unwrap();
    if g.lot.is_empty() {
        return;
    }
    let bavard = taranis_vk::bavard();
    if taranis_envoyer(c, &mut *g, bavard) != Some(true) {
        eprintln!("taranis : un lot de la carte a échoué (une écriture hors du monde) ; relancer avec VTX_LOT=0");
        std::process::exit(3);
    }
}

/// 0.824 : envoie le lot (un envoi, une attente) ; Some(vrai) : fait ; Some(faux) : une boucle a écrit hors du monde ;
/// None : la carte a refusé
#[allow(dead_code)]
fn taranis_envoyer(c: &mut Ctx, g: &mut EtatTaranis, bavard: bool) -> Option<bool> {
    let carte = taranis_vk::carte()?;
    let lot: Vec<(usize, usize, u64, usize)> = std::mem::take(&mut g.lot);
    let montees: Vec<u32> = std::mem::take(&mut g.lot_montees);
    let t_monte = std::mem::replace(&mut g.t_monte, 0.0);
    let items: Vec<(&[u32], u64, usize)> = lot.iter()
        .map(|&(p, l, n, r)| (unsafe { std::slice::from_raw_parts(p as *const u32, l) }, n, r)).collect();
    let mut params = g.params_lot.clone();
    let table = g.table_lot.clone();
    let lance = {
        let EtatTaranis { res, .. } = &mut *g;
        carte.lancer_lot(res.as_mut().unwrap(), &items, &montees, &table, &mut params)
    };
    let (ms, marques) = match lance {
        Ok(x) => x,
        Err(e) => {
            if bavard {
                eprintln!("taranis : {}", e);
            }
            g.pret = false;
            return None;
        }
    };
    // 0.826 : le noyau fondu n'a pas tenu sa garde (un fil a touché la case d'un autre dans ce que les étages
    // écrivent) : il n'est pas fidèle ; Gutuater le saura (une preuve contre définitive), et l'image n'est pas sûre
    if lot.iter().any(|&(_, _, _, r)| params[r * 64] == 2) {
        let lieu = FONDRE_LIEU.load(std::sync::atomic::Ordering::Relaxed);
        if let Some(d) = dossier_gutuater() {
            use std::io::Write;
            if let Ok(mut f) = std::fs::OpenOptions::new().create(true).append(true).open(d.join("gutuater.mesures")) {
                let _ = writeln!(f, "infidele fondre {}", lieu);
            }
        }
        eprintln!("gutuater : le lot de la ligne {} fondu en un noyau n'est pas fidèle (un fil a touché la case d'un \
                   autre) ; noté pour Gutuater, qui le taira ; relancer", lieu);
        std::process::exit(3);
    }
    if lot.iter().any(|&(_, _, _, r)| params[r * 64] != 0) {
        if bavard {
            eprintln!("taranis : la boucle revient au processeur (une écriture hors du monde)");
        }
        g.pret = false;
        return Some(false);
    }
    let miroir = g.res.as_ref().unwrap().miroir as usize;
    // ce qui redescend : les fréquences écrites (celles de la carte restent sur la carte)
    let mut ecrites: Vec<u32> = Vec::new();
    let mut fs: Vec<usize> = Vec::new();
    for f in 0..256 {
        if marques[f] != 0 && g.freq[f].1 > 0 && f >= FREQ_CARTE {
            g.perimees[f] = true;
            continue;
        }
        if marques[f] != 0 && g.freq[f].1 > 0 {
            fs.push(f);
            for q in 0..g.freq[f].1 {
                ecrites.push(g.freq[f].0 + q);
            }
        }
    }
    let t_desc = {
        let EtatTaranis { res, .. } = &mut *g;
        match carte.redescendre(res.as_mut().unwrap(), &ecrites) {
            Ok(x) => x,
            Err(e) => {
                if bavard {
                    eprintln!("taranis : {}", e);
                }
                g.pret = false;
                return None;
            }
        }
    };
    let t1 = std::time::Instant::now();
    for &f in &fs {
        for q in 0..g.freq[f].1 {
            let s = (g.freq[f].0 + q) as usize;
            let pg = ((f as u64) << 8) | q as u64;
            let src = unsafe { std::slice::from_raw_parts((miroir as *const u64).add(s * 65536), 65536) };
            let connue = g.pages.get(s).copied().unwrap_or(0);
            let p = if connue != 0 {
                connue as *mut u128
            } else {
                if src.iter().all(|&w| w == 0) {
                    continue;
                }
                let p = c.m.page_de(adresse_page((2u128 << 120) | pg as u128)).0;
                if s < g.pages.len() {
                    g.pages[s] = p as usize;
                }
                p
            };
            let dst = unsafe { std::slice::from_raw_parts_mut(p, 65536) };
            for (d, &w) in dst.iter_mut().zip(src) {
                *d = w as u128;
            }
        }
    }
    if bavard {
        eprintln!("taranis : {} noyau(x), {} tours, Taranis ({} places, {} montées, {} redescendues) : préparer {:.1} ms, lancer {:.1} ms, la carte {:.1} ms, redescendre {:.1} + {:.1} ms",
                  lot.len(), lot.iter().map(|x| x.2).sum::<u64>(), g.res.as_ref().unwrap().cap, montees.len(), ecrites.len(),
                  t_monte, ms[0], ms[1], t_desc, t1.elapsed().as_secs_f64() * 1e3);
    }
    Some(true)
}

/// 0.820 : VTX_EPISSAGE=rapide : sur la carte, la promesse n'est pas vérifiée (le programme répond de ses écritures)
/// et rien n'est comparé : ne montent que les pages que le processeur a changées (SALES). VTX_CARTE_VERIF=1 compare
/// tout de même, et dit chaque page changée qui n'était pas marquée (le filet).
#[allow(dead_code)]
fn epissage_rapide() -> bool {
    static R: std::sync::OnceLock<bool> = std::sync::OnceLock::new();
    *R.get_or_init(|| std::env::var("VTX_EPISSAGE").map_or(false, |v| v == "rapide"))
}

#[allow(dead_code)]
fn verif_carte() -> bool {
    static R: std::sync::OnceLock<bool> = std::sync::OnceLock::new();
    *R.get_or_init(|| std::env::var("VTX_CARTE_VERIF").map_or(false, |v| v == "1"))
}

/// 0.817 : la résidence (le cube gardé sur la carte) : quelles pages ont une place sur la carte, lesquelles le miroir
/// connaît (sa copie est exactement celle de la carte), et quand le noyau a lu ou écrit chacune pour la dernière fois
#[allow(dead_code)]
struct EtatResidence {
    res: Option<taranis_vk::Residence>,
    places: std::collections::HashMap<u64, u32>,
    pages_de: Vec<u64>,
    connu: Vec<bool>,
    vu: std::collections::HashMap<u64, u32>,
    appel: u32,
    premier: bool,
}
unsafe impl Send for EtatResidence {}

#[allow(dead_code)]
fn residence() -> &'static std::sync::Mutex<EtatResidence> {
    static R: std::sync::OnceLock<std::sync::Mutex<EtatResidence>> = std::sync::OnceLock::new();
    R.get_or_init(|| std::sync::Mutex::new(EtatResidence { res: None, places: std::collections::HashMap::new(),
        pages_de: Vec::new(), connu: Vec::new(), vu: std::collections::HashMap::new(), appel: 0, premier: true }))
}

/// la page du processeur (mots de 128 bits) diffère-t-elle du miroir (mots de 64 bits) ? None : un mot de plus de 64 bits
#[allow(dead_code)]
fn page_differe(cpu: *const u128, mir: *const u64) -> Option<bool> {
    let c = unsafe { std::slice::from_raw_parts(cpu, 65536) };
    let m = unsafe { std::slice::from_raw_parts(mir, 65536) };
    let mut diff = false;
    for k in 0..65536 {
        let w = c[k];
        if w >> 64 != 0 {
            return None;
        }
        if w as u64 != m[k] {
            diff = true;
            break;
        }
    }
    if diff {
        if c.iter().any(|&w| w >> 64 != 0) {
            return None;
        }
    }
    Some(diff)
}

#[allow(dead_code)]
fn taranis_boucle_pages_(c: &mut Ctx, spv: &[u32], a: u128, b: u128, ext: &[u128], encore: bool, rapide: bool) -> bool {
    let n = (b as u64).wrapping_sub(a as u64);
    if n == 0 || n > (1u64 << 31) || ext.iter().any(|&v| v >> 64 != 0) {
        return false;
    }
    let carte = match taranis_vk::carte() {
        Some(k) => k,
        None => return false,
    };
    if c.m.a_des_cubes_sur_disque() {
        return false;
    }
    let bavard = taranis_vk::bavard();
    let t0 = std::time::Instant::now();
    // 0.820 : les chemins d'écriture de la machine sont oubliés : la prochaine écriture de chaque page la marque
    c.oublier_pages();
    let mut g = residence().lock().unwrap();
    g.appel += 1;
    let appel = g.appel;
    let mut liste: Vec<(u64, *mut u128)> = Vec::new();
    for (k, p, brins) in c.m.instantane() {
        if k >> 120 != 2 {
            continue;
        }
        let pg = (k & ((1u128 << 120) - 1)) as u64;
        if pg >= 65536 {
            continue;
        }
        if brins {
            return false;
        }
        liste.push((pg, p));
    }
    liste.sort_by_key(|x| x.0);
    for &(pg, _) in &liste {
        if !g.places.contains_key(&pg) {
            let s = g.pages_de.len() as u32;
            g.places.insert(pg, s);
            g.pages_de.push(pg);
            g.connu.push(false);
        }
    }
    let np = g.pages_de.len();
    let neuve = {
        let EtatResidence { res, .. } = &mut *g;
        match carte.residence(res, np) {
            Ok(x) => x,
            Err(e) => {
                if bavard {
                    eprintln!("taranis : {}", e);
                }
                return false;
            }
        }
    };
    if neuve {
        for x in g.connu.iter_mut() {
            *x = false;
        }
    }
    let cap = g.res.as_ref().unwrap().cap;
    let miroir = g.res.as_ref().unwrap().miroir as usize;
    // les pages suivies : celles que le noyau a lues ou écrites dans ses 32 derniers lancements (toutes, la première fois ;
    // assez pour les places du tapis, qui reviennent toutes les cinq images)
    let premier = g.premier;
    let suivies: Vec<(u64, usize, usize, bool)> = liste.iter().filter(|(pg, _)| premier || g.vu.get(pg)
        .map_or(false, |&v| v + 32 >= appel)).map(|&(pg, p)| {
            let s = g.places[&pg] as usize;
            (pg, p as usize, s, g.connu[s])
        }).collect();
    // le miroir comparé à la mémoire, sur tous les cœurs ; une page changée (ou inconnue) y est recopiée et montera
    let nt = cylindres_voulus().max(1).min(suivies.len().max(1));
    let morceau = suivies.len().div_ceil(nt).max(1);
    let verif = verif_carte();
    let resultats: Vec<Option<Vec<u32>>> = std::thread::scope(|sc| {
        let fils: Vec<_> = suivies.chunks(morceau).map(|ch| sc.spawn(move || {
            let mut montees = Vec::new();
            for &(pg, p, s, connu) in ch {
                let mir = (miroir as *mut u64).wrapping_add(s * 65536);
                let diff = if !connu {
                    true
                } else if rapide {
                    let marquee = sale(pg);
                    if !marquee && verif {
                        let d = page_differe(p as *const u128, mir)?;
                        if d {
                            eprintln!("taranis : le filet : la page {:#x} a changé sans être marquée", pg);
                        }
                        d
                    } else {
                        marquee
                    }
                } else {
                    page_differe(p as *const u128, mir)?
                };
                if diff {
                    let src = unsafe { std::slice::from_raw_parts(p as *const u128, 65536) };
                    let dst = unsafe { std::slice::from_raw_parts_mut(mir, 65536) };
                    for (d, &w) in dst.iter_mut().zip(src) {
                        if w >> 64 != 0 {
                            return None;
                        }
                        *d = w as u64;
                    }
                    montees.push(s as u32);
                }
            }
            Some(montees)
        })).collect();
        fils.into_iter().map(|h| h.join().unwrap()).collect()
    });
    let mut montees = Vec::new();
    for r in resultats {
        match r {
            Some(v) => montees.extend(v),
            None => return false,
        }
    }
    for &s in &montees {
        g.connu[s as usize] = true;
    }
    for &(pg, _, _, _) in &suivies {
        nettoyer(pg);
    }
    let mut table = vec![0u32; 65536];
    for &(pg, _, s, _) in &suivies {
        table[pg as usize] = s as u32 + 1;
    }
    let t_monte = t0.elapsed().as_secs_f64() * 1e3;
    let mut params = vec![0u64; 6 + ext.len()];
    params[1] = a as u64;
    params[2] = n;
    params[3] = 2 * cap as u64;
    for (k, &v) in ext.iter().enumerate() {
        params[6 + k] = v as u64;
    }
    let lance = {
        let EtatResidence { res, .. } = &mut *g;
        carte.lancer_resident(res.as_mut().unwrap(), spv, &montees, &table, &mut params, n)
    };
    let (ms, marques) = match lance {
        Ok(x) => x,
        Err(e) => {
            if bavard {
                eprintln!("taranis : {}", e);
            }
            // ce que la carte a pu écrire n'est plus connu du miroir
            for x in g.connu.iter_mut() {
                *x = false;
            }
            return false;
        }
    };
    let ecrites: Vec<u32> = (0..np as u32).filter(|&s| marques[2 * s as usize + 1] != 0).collect();
    for s in 0..np {
        if marques[2 * s] != 0 || marques[2 * s + 1] != 0 {
            let pg = g.pages_de[s];
            g.vu.insert(pg, appel);
        }
    }
    let lue_et_ecrite = !rapide && ecrites.iter().any(|&s| marques[2 * s as usize] != 0);
    if params[0] != 0 || lue_et_ecrite {
        // la carte a pu écrire : ces places ne sont plus celles du miroir
        for &s in &ecrites {
            g.connu[s as usize] = false;
        }
        if params[0] == 1 && encore {
            let d0 = 2 * cap;
            let manquent: Vec<u64> = (0..65536u64).filter(|&pg| marques.get(d0 + pg as usize).map_or(false, |&m| m != 0)).collect();
            if !manquent.is_empty() && marques.get(d0 + 65536).map_or(true, |&m| m == 0) {
                for &pg in &manquent {
                    let _ = c.m.page_de(etg((pg << 16) as u128, 2));
                    g.vu.insert(pg, appel);
                }
                if bavard {
                    eprintln!("taranis : {} pages manquaient à la carte : la boucle relancée", manquent.len());
                }
                drop(g);
                return taranis_boucle_pages_(c, spv, a, b, ext, false, rapide);
            }
        }
        if bavard {
            eprintln!("taranis : la boucle revient au processeur ({})", if lue_et_ecrite { "une page lue et écrite" }
                      else if params[0] == 2 { "deux tours ont écrit le même mot" } else { "une page manquait à la carte" });
        }
        return false;
    }
    let t_desc = {
        let EtatResidence { res, .. } = &mut *g;
        match carte.redescendre(res.as_mut().unwrap(), &ecrites) {
            Ok(x) => x,
            Err(e) => {
                if bavard {
                    eprintln!("taranis : {}", e);
                }
                for &s in &ecrites {
                    g.connu[s as usize] = false;
                }
                return false;
            }
        }
    };
    let t1 = std::time::Instant::now();
    for &s in &ecrites {
        let pg = g.pages_de[s as usize];
        if let Some(&(_, p)) = liste.iter().find(|x| x.0 == pg) {
            let dst = unsafe { std::slice::from_raw_parts_mut(p, 65536) };
            let src = unsafe { std::slice::from_raw_parts((miroir as *const u64).add(s as usize * 65536), 65536) };
            for (d, &w) in dst.iter_mut().zip(src) {
                *d = w as u128;
            }
        }
    }
    g.premier = false;
    if bavard {
        eprintln!("taranis : {} tours sur la carte{} ({} pages suivies, {} montées, {} écrites) : comparer et préparer {:.1} ms, lancer {:.1} ms, la carte {:.1} ms, redescendre {:.1} + {:.1} ms",
                  n, if carte.int64 { ", en 64 bits" } else { "" }, suivies.len(), montees.len(), ecrites.len(), t_monte,
                  ms[0], ms[1], t_desc, t1.elapsed().as_secs_f64() * 1e3);
    }
    true
}

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
