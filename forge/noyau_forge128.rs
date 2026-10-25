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
}

/// la case d'une page dans le petit cache : son numéro et son étage mêlés
#[inline(always)]
fn case(k: u128) -> usize {
    ((k as usize) ^ ((k >> 120) as usize).wrapping_mul(5)) & 15
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

fn lancer_programme(principal: fn(&mut Ctx) -> u128, mots: &[u128], fin_code: u128, nom: &str, entrees: &[String]) {
    let mut m = Spu128::nouveau();
    m.dossier = std::env::current_dir().ok();
    m.charger(mots);
    m.entree.extend(entrees.iter().filter_map(|x| x.parse::<u128>().ok()));
    let mut c = Ctx { m, sp: spu128::PILE, cl: [u128::MAX; 16], pl: [std::ptr::null_mut(); 16], ce: [u128::MAX; 16],
                      pe: [std::ptr::null_mut(); 16] };
    // le brin : le code, les textes écrits et les données du programme sont de l'ADN (comme au début du programme
    // compilé : MARQUE R0, FIN_CODE, 1), puis l'appel de principal (CALL : l'adresse de retour dans la pile)
    c.marquer(0, fin_code, 1);
    c.pousser(0);
    let debut = std::time::Instant::now();
    principal(&mut c);
    let duree = debut.elapsed();
    finir(&mut c);
    if std::env::var("FORGE_TEMPS").is_ok() {
        eprintln!("{} : {:.3} s", nom, duree.as_secs_f64());
    }
}
