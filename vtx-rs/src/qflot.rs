// Les flottants quaternaires de 32 et 64 bits du SPU-64, en entiers (u128) : mêmes résultats que la référence exacte
// en fractions (spu64/qflot.py). Un format : quit d'état (Belnap : 0 inconnu, 1 négatif, 2 positif, 3 variable),
// exposant de `ebits` bits (sa valeur maximale : l'infini), mantisse de `p` bits (p / 2 quits) ; valeur :
// mantisse × 4^(max(E, 1) − biais). Arrondi au plus proche, pair au milieu.

#[derive(Clone, Copy)]
pub struct Fmt {
    pub p: u32,
    pub ebits: u32,
    pub biais: i64,
    pub taille: u32,
}

pub const Q32: Fmt = Fmt { p: 22, ebits: 8, biais: 138, taille: 32 };
pub const Q64: Fmt = Fmt { p: 52, ebits: 10, biais: 537, taille: 64 };

fn bits(m: u128) -> i64 {
    128 - m.leading_zeros() as i64
}

impl Fmt {
    fn emax(&self) -> u64 {
        (1u64 << self.ebits) - 1
    }
    fn mant_masque(&self) -> u64 {
        (1u64 << self.p) - 1
    }
    pub fn etat(&self, a: u64) -> u64 {
        (a >> (self.taille - 2)) & 3
    }
    fn ef(&self, a: u64) -> u64 {
        (a >> self.p) & self.emax()
    }
    pub fn variable(&self) -> u64 {
        3u64 << (self.taille - 2)
    }
    pub fn signe(&self, s: bool) -> u64 {
        (if s { 1u64 } else { 2u64 }) << (self.taille - 2)
    }
    fn inf(&self, s: bool) -> u64 {
        self.signe(s) | (self.emax() << self.p)
    }
    fn est_nombre(&self, a: u64) -> bool {
        let e = self.etat(a);
        e == 1 || e == 2
    }
    fn est_inf(&self, a: u64) -> bool {
        self.est_nombre(a) && self.ef(a) == self.emax()
    }
    fn est_zero(&self, a: u64) -> bool {
        self.est_nombre(a) && self.ef(a) != self.emax() && a & self.mant_masque() == 0
    }
    fn negatif(&self, a: u64) -> bool {
        self.etat(a) == 1
    }
    /// la mantisse et l'exposant binaire de son bit 0
    fn decode(&self, a: u64) -> (u128, i64) {
        let e = self.ef(a).max(1) as i64;
        ((a & self.mant_masque()) as u128, 2 * (e - self.biais))
    }

    /// m × 2^ex arrondi (m > 0) : exposant << p | mantisse, sans l'état. collant : des bits non nuls sous m (m a alors
    /// au moins p + 2 bits).
    pub fn arrondir(&self, m: u128, ex: i64, collant: bool) -> u64 {
        let p = self.p as i64;
        if m == 0 {
            return 0;
        }
        let mut ex = ex;
        let mut k = bits(m) - p;
        if (ex + k) & 1 != 0 {
            k += 1;
        }
        let qmin = 2 * (1 - self.biais);
        if ex + k < qmin {
            k = qmin - ex;
        }
        let mut q: u128;
        if k > 0 {
            if k >= 129 {
                q = 0;
            } else {
                let (qq, bas) = if k == 128 { (0u128, m) } else { (m >> k, m & ((1u128 << k) - 1)) };
                q = qq;
                let demi = 1u128 << (k - 1);
                if bas > demi || (bas == demi && (collant || q & 1 == 1)) {
                    q += 1;
                }
            }
            ex += k;
            if q == 1u128 << p {
                q = 1u128 << (p - 2);
                ex += 2;
            }
        } else {
            q = m << (-k);
            ex += k;
        }
        if q < 1u128 << (p - 2) {
            return q as u64;
        }
        let e = ex / 2 + self.biais;
        if e >= self.emax() as i64 {
            return self.emax() << self.p;
        }
        ((e as u64) << self.p) | (q as u64)
    }

    fn depuis(&self, s: bool, m: u128, ex: i64, collant: bool) -> u64 {
        if m == 0 {
            return self.signe(s);
        }
        self.signe(s) | self.arrondir(m, ex, collant)
    }

    fn special(&self, a: u64, b: u64) -> Option<u64> {
        let (ea, eb) = (self.etat(a), self.etat(b));
        if ea == 3 || eb == 3 {
            return Some(self.variable());
        }
        if ea == 0 || eb == 0 {
            return Some(0);
        }
        None
    }

    pub fn neg(&self, a: u64) -> u64 {
        if self.est_nombre(a) { a ^ (3u64 << (self.taille - 2)) } else { a }
    }

    pub fn add(&self, a: u64, b: u64) -> u64 {
        if let Some(s) = self.special(a, b) {
            return s;
        }
        if self.est_inf(a) && self.est_inf(b) {
            return if self.etat(a) == self.etat(b) { a } else { self.variable() };
        }
        if self.est_inf(a) {
            return a;
        }
        if self.est_inf(b) {
            return b;
        }
        let (sa, sb) = (self.negatif(a), self.negatif(b));
        let (ma0, xa0) = self.decode(a);
        let (mb0, xb0) = self.decode(b);
        if ma0 == 0 && mb0 == 0 {
            return self.signe(sa && sb);
        }
        // x + 0 et 0 + x : x sous sa forme normalisée (comme le calcul exact)
        if ma0 == 0 {
            return self.depuis(sb, mb0, xb0, false);
        }
        if mb0 == 0 {
            return self.depuis(sa, ma0, xa0, false);
        }
        let (mut ma, mut xa, mut sa, mut mb, mut xb, mut sb) = (ma0, xa0, sa, mb0, xb0, sb);
        if xa < xb {
            std::mem::swap(&mut ma, &mut mb);
            std::mem::swap(&mut xa, &mut xb);
            std::mem::swap(&mut sa, &mut sb);
        }
        // un mot peut ne pas être normalisé (mantisse courte) : la somme est exacte quand l'écart le permet ; sinon b est
        // bien plus petit que a (moins d'un 256e), et a reçoit 64 bits de garde
        let d = xa - xb;
        let (m_a, m_b, ex) = if d <= 60 {
            (ma << d, mb, xb)
        } else {
            let sh = d - 64;
            let b = if sh >= 128 {
                1
            } else if sh > 0 {
                let q = mb >> sh;
                if q << sh != mb { q | 1 } else { q }
            } else {
                mb << (-sh)
            };
            (ma << 64, b, xa - 64)
        };
        let (m, s) = if sa == sb {
            (m_a + m_b, sa)
        } else if m_a < m_b {
            (m_b - m_a, sb)
        } else {
            (m_a - m_b, sa)
        };
        if m == 0 {
            return self.signe(false);
        }
        self.depuis(s, m, ex, false)
    }

    pub fn sub(&self, a: u64, b: u64) -> u64 {
        self.add(a, self.neg(b))
    }

    pub fn mul(&self, a: u64, b: u64) -> u64 {
        if let Some(s) = self.special(a, b) {
            return s;
        }
        let s = self.etat(a) != self.etat(b);
        if self.est_inf(a) || self.est_inf(b) {
            if self.est_zero(a) || self.est_zero(b) {
                return self.variable();
            }
            return self.inf(s);
        }
        let (ma, xa) = self.decode(a);
        let (mb, xb) = self.decode(b);
        self.depuis(s, ma * mb, xa + xb, false)
    }

    pub fn div(&self, a: u64, b: u64) -> u64 {
        if let Some(s) = self.special(a, b) {
            return s;
        }
        let s = self.etat(a) != self.etat(b);
        if self.est_inf(a) {
            return if self.est_inf(b) { self.variable() } else { self.inf(s) };
        }
        if self.est_inf(b) {
            return self.signe(s);
        }
        if self.est_zero(b) {
            return if self.est_zero(a) { self.variable() } else { self.inf(s) };
        }
        if self.est_zero(a) {
            return self.signe(s);
        }
        let (ma, xa) = self.decode(a);
        let (mb, xb) = self.decode(b);
        let sh = 127 - bits(ma);
        let n = ma << sh;
        let q = n / mb;
        let r = n % mb;
        self.depuis(s, q, xa - xb - sh, r != 0)
    }

    pub fn racine(&self, a: u64) -> u64 {
        if !self.est_nombre(a) || self.est_zero(a) {
            return a;
        }
        if self.negatif(a) {
            return self.variable();
        }
        if self.est_inf(a) {
            return a;
        }
        let (mut m, mut ex) = self.decode(a);
        if ex & 1 != 0 {
            m <<= 1;
            ex -= 1;
        }
        let j = (126 - bits(m)) / 2;
        let n = m << (2 * j);
        let r = isqrt(n);
        self.depuis(false, r, (ex - 2 * j) / 2, r * r != n)
    }

    /// 0 égaux, 1 a < b, 2 a > b, 3 sans ordre
    pub fn cmp(&self, a: u64, b: u64) -> u64 {
        if self.special(a, b).is_some() {
            return 3;
        }
        let (na, nb) = (self.negatif(a), self.negatif(b));
        // les grandeurs : 0 pour zéro, 3 pour l'infini, sinon par la valeur exacte (un mot peut ne pas être normalisé)
        let rang = |x: u64| -> u8 {
            if self.est_inf(x) { 3 } else if self.est_zero(x) { 0 } else { 1 }
        };
        let (ra, rb) = (rang(a), rang(b));
        if ra == 0 && rb == 0 {
            return 0;
        }
        let ordre = if ra != rb {
            ra.cmp(&rb)
        } else if ra == 3 {
            std::cmp::Ordering::Equal
        } else {
            let (ma, xa) = self.decode(a);
            let (mb, xb) = self.decode(b);
            let (ha, hb) = (bits(ma) + xa, bits(mb) + xb);
            if ha != hb {
                ha.cmp(&hb)
            } else {
                let x = xa.min(xb);
                (ma << (xa - x)).cmp(&(mb << (xb - x)))
            }
        };
        // ordre : la grandeur de a devant celle de b ; les signes décident ensuite
        use std::cmp::Ordering::*;
        if na != nb {
            return if na { 1 } else { 2 };
        }
        match (ordre, na) {
            (Equal, _) => 0,
            (Less, false) | (Greater, true) => 1,
            _ => 2,
        }
    }

    pub fn de_entier(&self, v: u64, signe: bool) -> u64 {
        let neg = signe && (v as i64) < 0;
        let mag = if neg { (v as i64).unsigned_abs() } else { v };
        self.depuis(neg, mag as u128, 0, false)
    }

    /// vers entier signé de 64 bits, tronqué ou arrondi au plus proche pair, saturé ; inconnu, variable : 0
    pub fn vers_entier(&self, a: u64, arrondir: bool) -> u64 {
        if !self.est_nombre(a) {
            return 0;
        }
        let neg = self.negatif(a);
        let satur = if neg { 0x8000_0000_0000_0000u64 } else { 0x7FFF_FFFF_FFFF_FFFFu64 };
        if self.est_inf(a) {
            return satur;
        }
        let (m, ex) = self.decode(a);
        if m == 0 {
            return 0;
        }
        let mag: u128 = if ex >= 0 {
            if bits(m) + ex > 64 {
                return satur;
            }
            m << ex
        } else {
            let k = -ex;
            if k >= 128 {
                0
            } else {
                let q = m >> k;
                if !arrondir {
                    q
                } else {
                    let bas = m & ((1u128 << k) - 1);
                    let demi = 1u128 << (k - 1);
                    if bas > demi || (bas == demi && q & 1 == 1) { q + 1 } else { q }
                }
            }
        };
        if neg {
            if mag >= 1u128 << 63 {
                return satur;
            }
            (mag as u64).wrapping_neg()
        } else {
            if mag >= 1u128 << 63 {
                return satur;
            }
            mag as u64
        }
    }

    /// vers un autre format quaternaire
    pub fn vers(&self, autre: &Fmt, a: u64) -> u64 {
        if !self.est_nombre(a) {
            return if self.etat(a) == 3 { autre.variable() } else { 0 };
        }
        let s = self.negatif(a);
        if self.est_inf(a) {
            return autre.inf(s);
        }
        let (m, ex) = self.decode(a);
        autre.depuis(s, m, ex, false)
    }
}

pub fn isqrt(n: u128) -> u128 {
    if n == 0 {
        return 0;
    }
    let mut x = (n as f64).sqrt() as u128;
    for _ in 0..3 {
        if x == 0 {
            break;
        }
        x = (x + n / x) / 2;
    }
    while x * x > n {
        x -= 1;
    }
    while (x + 1) * (x + 1) <= n {
        x += 1;
    }
    x
}

/// vers les bits d'un binary64 de l'IEEE (exact pour le flottant de 64 bits) ; inconnu et variable : le NaN
pub fn vers_ieee64(a: u64) -> u64 {
    let f = Q64;
    if !f.est_nombre(a) {
        return 0x7FF8_0000_0000_0000;
    }
    let s = (f.negatif(a) as u64) << 63;
    if f.est_inf(a) {
        return 0x7FF0_0000_0000_0000 | s;
    }
    let (m, ex) = f.decode(a);
    if m == 0 {
        return s;
    }
    // arrondi binaire à 53 bits, exposants de −1074 à 1023
    let mut ex = ex;
    let mut k = bits(m) - 53;
    if ex + k < -1074 {
        k = -1074 - ex;
    }
    let mut q: u128;
    if k > 0 {
        if k >= 128 {
            q = 0;
        } else {
            q = m >> k;
            let bas = m & ((1u128 << k) - 1);
            let demi = 1u128 << (k - 1);
            if bas > demi || (bas == demi && q & 1 == 1) {
                q += 1;
            }
        }
        ex += k;
        if q == 1u128 << 53 {
            q >>= 1;
            ex += 1;
        }
    } else {
        q = m << (-k);
        ex += k;
    }
    if q < 1u128 << 52 {
        return s | q as u64;
    }
    let be = ex + 52 + 1023;
    if be >= 2047 {
        return s | 0x7FF0_0000_0000_0000;
    }
    s | ((be as u64) << 52) | ((q as u64) & ((1u64 << 52) - 1))
}

/// depuis les bits d'un binary64 de l'IEEE (NaN : variable)
pub fn de_ieee64(d: u64) -> u64 {
    let f = Q64;
    let s = d >> 63 == 1;
    let e = (d >> 52) & 2047;
    let m = d & ((1u64 << 52) - 1);
    if e == 2047 {
        return if m != 0 { f.variable() } else { f.inf(s) };
    }
    if e == 0 {
        return f.depuis(s, m as u128, -1074, false);
    }
    f.depuis(s, (m | (1u64 << 52)) as u128, e as i64 - 1075, false)
}
