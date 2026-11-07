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
    cl: [u128; 16],
    pl: [*mut u128; 16],
    ce: [u128; 16],
    pe: [*mut u128; 16],
    // les tableaux rangés hors du cube (l'adaptation automatique) : leur recopie dans le cube, avant toute fin
    vider: fn(&mut Ctx),
    // la machine d'un cylindre (les segments joués ensemble) : elle lit le cube commun, et n'écrit que dans le sien
    ombre: Option<Box<Cylindre>>,
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

struct Cylindre {
    commun: *const Instantane,
    copiees: std::collections::HashSet<u128>,
    lues: std::collections::HashSet<u128>,
    danger: bool,
}

/// Ce qu'un cylindre rend : ses pages, les pages qu'il a lues, et s'il faut tout rejouer
struct Recolte {
    pages: Vec<(u128, Box<[u128]>)>,
    lues: Vec<u128>,
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

#[allow(dead_code)]
fn rendre(c: &mut Ctx) -> Recolte {
    let o = c.ombre.take().unwrap();
    let cles: Vec<u128> = o.copiees.iter().copied().collect();
    // seules les pages vraiment changées sont rendues ; la comparaison se fait ici, dans le fil, sur son cœur
    let inst = unsafe { &*o.commun };
    let zero = vec![0u128; MOTS_PAGE];
    let pages = c.m.rendre_pages(&cles).into_iter().filter(|(k, mots)| {
        let orig = inst.pages.get(k).map(|&(p, _)| p as *const u128).unwrap_or(zero.as_ptr());
        mots[..] != unsafe { std::slice::from_raw_parts(orig, MOTS_PAGE) }[..]
    }).collect();
    Recolte { pages, lues: o.lues.into_iter().collect(), danger: o.danger }
}

/// l'adresse du premier mot d'une page, depuis sa clé
fn adresse_page(k: u128) -> u128 {
    let e = k >> 120;
    let i = (k & ((1u128 << 120) - 1)) << 16;
    if i >> 48 == 0 { (e << 62) | i } else { (e << 126) | i }
}

/// Fond les cubes des cylindres dans le cube commun ; faux : il faut rejouer les segments l'un après l'autre
#[allow(dead_code)]
fn fusionner(c: &mut Ctx, _inst: &Instantane, recoltes: Vec<Recolte>) -> bool {
    if recoltes.iter().any(|r| r.danger) {
        rapport_cylindres(recoltes.len(), 0, 0, "un cylindre a touché ce qui n'est qu'au cube commun : rejoué");
        return false;
    }
    // les pages que chacun a vraiment changées (déjà triées dans les fils, par rendre)
    let ecrites: Vec<std::collections::HashSet<u128>> =
        recoltes.iter().map(|r| r.pages.iter().map(|(k, _)| *k).collect()).collect();
    // un cylindre a-t-il lu une page qu'un cylindre d'avant a écrite ?
    for t in 1..recoltes.len() {
        for k in &recoltes[t].lues {
            if ecrites[..t].iter().any(|e| e.contains(k)) {
                rapport_cylindres(recoltes.len(), 0, 0, "un cylindre a lu ce qu'un autre écrivait : rejoué");
                return false;
            }
        }
    }
    // chaque page du cube commun, avec ceux qui l'ont écrite, dans l'ordre des segments
    let nr = recoltes.len();
    let mut ordre: Vec<u128> = Vec::new();
    let mut auteurs: std::collections::HashMap<u128, Vec<Box<[u128]>>> = std::collections::HashMap::new();
    for r in recoltes {
        for (k, mots) in r.pages {
            auteurs.entry(k).or_insert_with(|| { ordre.push(k); Vec::new() }).push(mots);
        }
    }
    // une page écrite par un seul cylindre : sa copie devient la page commune (rien n'est recopié)
    struct Fonte { dst: usize, mots: Vec<Box<[u128]>> }
    let mut fontes: Vec<Fonte> = Vec::new();
    let mut anciennes: Vec<Box<[u128]>> = Vec::new();
    let pages = ordre.len();
    for k in &ordre {
        let mut m = auteurs.remove(k).unwrap();
        if m.len() == 1 {
            anciennes.extend(c.m.poser_page(adresse_page(*k), m.pop().unwrap()));
        } else {
            let (dst, _, _) = c.m.page_de(adresse_page(*k));
            fontes.push(Fonte { dst: dst as usize, mots: m });
        }
    }
    // les pages écrites par plusieurs : fondues mot à mot, une page par fil à la fois, sur tous les cœurs
    let nt = cylindres_voulus().min(fontes.len()).max(1);
    let suivante = std::sync::atomic::AtomicUsize::new(0);
    let variables: u64 = std::thread::scope(|sc| {
        let fils: Vec<_> = (0..nt).map(|_| sc.spawn(|| {
            let mut v = 0u64;
            loop {
                let n = suivante.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                if n >= fontes.len() {
                    break;
                }
                let f = &fontes[n];
                let d = unsafe { std::slice::from_raw_parts_mut(f.dst as *mut u128, MOTS_PAGE) };
                let o = d.to_vec();
                let mut deja = vec![false; MOTS_PAGE];
                for mots in &f.mots {
                    // un cylindre ne change qu'un coin de la page : les blocs de 64 mots intacts sont sautés d'un coup
                    for b in (0..MOTS_PAGE).step_by(64) {
                        if mots[b..b + 64] == o[b..b + 64] {
                            continue;
                        }
                        for j in b..b + 64 {
                            if mots[j] != o[j] {
                                if deja[j] && d[j] != mots[j] {
                                    v += 1;
                                }
                                d[j] = mots[j];
                                deja[j] = true;
                            }
                        }
                    }
                }
            }
            v
        })).collect();
        fils.into_iter().map(|h| h.join().unwrap()).sum()
    });
    drop(fontes); drop(anciennes);
    c.oublier_pages();
    rapport_cylindres(nr, pages, variables, "");
    true
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
            eprintln!("cylindres : {} ; {}", n, rejoue);
        }
    }
}

/// la case d'une page dans le petit cache : son numéro et son étage mêlés, le numéro plié par quatre bits (comme case16 de spu128.rs)
#[inline(always)]
fn case(k: u128) -> usize {
    let n = k as usize;
    (n ^ (n >> 4) ^ (n >> 8) ^ ((k >> 120) as usize).wrapping_mul(5)) & 15
}

impl Ctx {
    #[inline(always)]
    fn lire(&mut self, a: u128) -> u128 {
        let (k, j) = Spu128::cle_page(a);
        let h = case(k);
        if k == self.cl[h] {
            return unsafe { *self.pl[h].add(j) };
        }
        self.lire_lent(a, k, j)
    }
    #[inline(never)]
    fn lire_lent(&mut self, a: u128, k: u128, j: usize) -> u128 {
        if self.ombre.is_some() && k >> 120 != 0 {
            let o = self.ombre.as_mut().unwrap();
            o.lues.insert(k);
            if !o.copiees.contains(&k) {
                let commun = unsafe { &*o.commun };
                if let Some(&(p, _)) = commun.pages.get(&k) {
                    // la page du cube commun, lue sans la copier
                    let h = case(k);
                    self.cl[h] = k;
                    self.pl[h] = p;
                    return unsafe { *p.add(j) };
                }
                if commun.disque {
                    o.danger = true;
                }
                // une page que le cube commun n'a pas : elle est vide ; elle devient la sienne
                o.copiees.insert(k);
            }
        }
        let (p, _, _) = self.m.page_de(a);
        let h = case(k);
        self.cl[h] = k;
        self.pl[h] = p;
        unsafe { *p.add(j) }
    }
    #[inline(always)]
    fn ecrire(&mut self, a: u128, v: u128) {
        let (k, j) = Spu128::cle_page(a);
        let h = case(k);
        if k == self.ce[h] {
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
            } else if !o.copiees.contains(&k) {
                // la première écriture dans une page : elle est copiée du cube commun dans le cube du cylindre
                o.copiees.insert(k);
                let commun = unsafe { &*o.commun };
                let source = commun.pages.get(&k).copied();
                if source.is_none() && commun.disque {
                    o.danger = true;
                }
                let (pd, _, _) = self.m.page_de(a);
                if let Some((ps, brins)) = source {
                    if brins {
                        o.danger = true;
                    }
                    unsafe { std::ptr::copy_nonoverlapping(ps as *const u128, pd, MOTS_PAGE) };
                }
                let h = case(k);
                if self.cl[h] == k {
                    self.cl[h] = u128::MAX;
                }
            }
        }
        let (p, _, brins) = self.m.page_de(a);
        if !brins {
            // une page sans brin : les écritures suivantes y vont directement
            let h = case(k);
            self.ce[h] = k;
            self.pe[h] = p;
        }
        if let Err(e) = self.m.ecrire_mem(a, v) {
            arreter(self, &e);
        }
    }
    /// un brin vient d'être posé : les écritures repassent par la vérification
    fn oublier_pages(&mut self) {
        self.ce = [u128::MAX; 16];
        self.cl = [u128::MAX; 16];
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

fn lancer_programme(principal: fn(&mut Ctx) -> u128, debuter: fn(&mut Ctx), vider: fn(&mut Ctx), mots: &[u128], fin_code: u128,
                    nom: &str, entrees: &[String]) {
    let mut m = Spu128::nouveau();
    m.dossier = std::env::current_dir().ok();
    m.charger(mots);
    m.entree.extend(entrees.iter().filter_map(|x| x.parse::<u128>().ok()));
    let mut c = Ctx { m, sp: spu128::PILE, cl: [u128::MAX; 16], pl: [std::ptr::null_mut(); 16], ce: [u128::MAX; 16],
                      pe: [std::ptr::null_mut(); 16], vider, ombre: None };
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
    let mut f = vec![0u64; len];
    for k in 0..len {
        let w = c.lire(etg((lo + k as u64) as u128, 2));
        if w >> 64 != 0 {
            return false;
        }
        f[k] = w as u64;
    }
    let orig = f.clone();
    let mut p = vec![0u64; 6 + ext.len()];
    p[1] = a as u64;
    p[2] = n;
    p[3] = lo;
    p[4] = len as u64;
    for (k, &v) in ext.iter().enumerate() {
        p[6 + k] = v as u64;
    }
    match carte.lancer(spv, &mut f, &mut p, n) {
        Ok(ms) => {
            if taranis_vk::bavard() {
                eprintln!("taranis : {} tours sur la carte, fenêtre de {} mots, {:.2} ms", n, len, ms);
            }
        }
        Err(e) => {
            if taranis_vk::bavard() {
                eprintln!("taranis : la carte refuse ({}) : les cylindres prennent la boucle", e);
            }
            return false;
        }
    }
    if p[0] != 0 {
        if taranis_vk::bavard() {
            eprintln!("taranis : un accès hors de la fenêtre : les cylindres rejouent la boucle");
        }
        return false;
    }
    for k in 0..len {
        if f[k] != orig[k] {
            c.ecrire(etg((lo + k as u64) as u128, 2), f[k] as u128);
        }
    }
    true
}
