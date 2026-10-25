// Les flottants quaternaires de Lugus (le SPU-128) : 32, 64 et 128 bits, en entiers. Mêmes résultats que la référence
// exacte en fractions (spu64/qflot.py, formats Q32, Q64, Q128). Le format de 128 bits est celui du flottant_petuar :
// quit d'état (Belnap : 0 inconnu, 1 négatif, 2 positif, 3 variable), exposant de 14 bits (16383 : l'infini), mantisse de
// 112 bits ; valeur : mantisse × 4^(max(E, 1) − 8247). Arrondi au plus proche, pair au milieu. Les calculs intermédiaires
// se font sur 256 bits (U256) : un produit de deux mantisses de 112 bits en a 224.

#[derive(Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Debug, Default)]
pub struct U256 {
    pub hi: u128,
    pub lo: u128,
}

impl U256 {
    pub const ZERO: U256 = U256 { hi: 0, lo: 0 };
    pub fn de(v: u128) -> U256 {
        U256 { hi: 0, lo: v }
    }
    pub fn est_nul(&self) -> bool {
        self.hi == 0 && self.lo == 0
    }
    pub fn bits(&self) -> i64 {
        if self.hi != 0 { 256 - self.hi.leading_zeros() as i64 } else { 128 - self.lo.leading_zeros() as i64 }
    }
    pub fn shl(&self, n: i64) -> U256 {
        if n <= 0 {
            return if n == 0 { *self } else { self.shr(-n) };
        }
        if n >= 256 {
            return U256::ZERO;
        }
        if n >= 128 {
            return U256 { hi: self.lo << (n - 128), lo: 0 };
        }
        U256 { hi: (self.hi << n) | (self.lo >> (128 - n)), lo: self.lo << n }
    }
    pub fn shr(&self, n: i64) -> U256 {
        if n <= 0 {
            return if n == 0 { *self } else { self.shl(-n) };
        }
        if n >= 256 {
            return U256::ZERO;
        }
        if n >= 128 {
            return U256 { hi: 0, lo: self.hi >> (n - 128) };
        }
        U256 { hi: self.hi >> n, lo: (self.lo >> n) | (self.hi << (128 - n)) }
    }
    /// les k bits bas
    pub fn bas(&self, k: i64) -> U256 {
        if k >= 256 {
            return *self;
        }
        if k <= 0 {
            return U256::ZERO;
        }
        if k >= 128 {
            let m = if k == 256 { u128::MAX } else { (1u128 << (k - 128)) - 1 };
            return U256 { hi: self.hi & m, lo: self.lo };
        }
        U256 { hi: 0, lo: self.lo & ((1u128 << k) - 1) }
    }
    pub fn puissance(k: i64) -> U256 {
        U256::de(1).shl(k)
    }
    pub fn add(&self, b: &U256) -> U256 {
        let (lo, c) = self.lo.overflowing_add(b.lo);
        U256 { hi: self.hi.wrapping_add(b.hi).wrapping_add(c as u128), lo }
    }
    pub fn sub(&self, b: &U256) -> U256 {
        let (lo, e) = self.lo.overflowing_sub(b.lo);
        U256 { hi: self.hi.wrapping_sub(b.hi).wrapping_sub(e as u128), lo }
    }
    pub fn mul(a: u128, b: u128) -> U256 {
        let (a1, a0) = (a >> 64, a & 0xFFFF_FFFF_FFFF_FFFF);
        let (b1, b0) = (b >> 64, b & 0xFFFF_FFFF_FFFF_FFFF);
        let p00 = a0 * b0;
        let p01 = a0 * b1;
        let p10 = a1 * b0;
        let p11 = a1 * b1;
        let r = U256 { hi: p11, lo: p00 };
        r.add(&U256::de(p01).shl(64)).add(&U256::de(p10).shl(64))
    }
    pub fn mul_256(&self, b: &U256) -> U256 {
        // les 256 bits bas du produit (assez pour les carrés de la racine)
        let r = U256::mul(self.lo, b.lo);
        let h = self.lo.wrapping_mul(b.hi).wrapping_add(self.hi.wrapping_mul(b.lo));
        U256 { hi: r.hi.wrapping_add(h), lo: r.lo }
    }
    /// quotient et reste (d non nul)
    pub fn divrem(&self, d: &U256) -> (U256, U256) {
        if self < d {
            return (U256::ZERO, *self);
        }
        let mut q = U256::ZERO;
        let mut r = U256::ZERO;
        for i in (0..self.bits()).rev() {
            r = r.shl(1);
            if self.shr(i).lo & 1 == 1 {
                r.lo |= 1;
            }
            if r >= *d {
                r = r.sub(d);
                q = q.add(&U256::puissance(i));
            }
        }
        (q, r)
    }
    /// quotient et reste par d < 2^127 (d non nul), par morceaux : à chaque pas le reste (plus petit que d) reçoit les
    /// bits suivants du dividende, autant qu'il en tient dans 128 bits, et une division de u128 donne le chiffre suivant
    pub fn divrem_u128(&self, d: u128) -> (U256, u128) {
        let k = (d.leading_zeros() as i64).max(1);       // bits libres au-dessus de d
        let n = self.bits();
        let mut q = U256::ZERO;
        let mut r = 0u128;
        let mut i = n;
        while i > 0 {
            let t = k.min(i);
            i -= t;
            let morceau = self.shr(i).bas(t).lo;
            let x = (r << t) | morceau;
            q = q.shl(t).add(&U256::de(x / d));
            r = x % d;
        }
        (q, r)
    }
    pub fn isqrt(&self) -> U256 {
        if self.est_nul() {
            return U256::ZERO;
        }
        // chiffre par chiffre, en base 4
        let mut x = *self;
        let mut r = U256::ZERO;
        let mut b = U256::puissance(((self.bits() + 1) & !1) - 2);
        while !b.est_nul() {
            let t = r.add(&b);
            if x >= t {
                x = x.sub(&t);
                r = r.shr(1).add(&b);
            } else {
                r = r.shr(1);
            }
            b = b.shr(2);
        }
        r
    }
}

#[derive(Clone, Copy)]
pub struct Fmt {
    pub p: i64,
    pub ebits: u32,
    pub biais: i64,
    pub taille: u32,
}

pub const Q32: Fmt = Fmt { p: 22, ebits: 8, biais: 138, taille: 32 };
pub const Q64: Fmt = Fmt { p: 52, ebits: 10, biais: 537, taille: 64 };
pub const Q128: Fmt = Fmt { p: 112, ebits: 14, biais: 8247, taille: 128 };

pub fn format(w: u32) -> Fmt {
    match w {
        1 => Q64,
        2 => Q32,
        _ => Q128,
    }
}

impl Fmt {
    pub fn masque(&self) -> u128 {
        if self.taille == 128 { u128::MAX } else { (1u128 << self.taille) - 1 }
    }
    fn emax(&self) -> u128 {
        (1u128 << self.ebits) - 1
    }
    fn mant_masque(&self) -> u128 {
        (1u128 << self.p) - 1
    }
    pub fn etat(&self, a: u128) -> u128 {
        (a >> (self.taille - 2)) & 3
    }
    fn ef(&self, a: u128) -> u128 {
        (a >> self.p) & self.emax()
    }
    pub fn variable(&self) -> u128 {
        3u128 << (self.taille - 2)
    }
    pub fn signe(&self, s: bool) -> u128 {
        (if s { 1u128 } else { 2u128 }) << (self.taille - 2)
    }
    fn inf(&self, s: bool) -> u128 {
        self.signe(s) | (self.emax() << self.p)
    }
    fn est_nombre(&self, a: u128) -> bool {
        let e = self.etat(a);
        e == 1 || e == 2
    }
    fn est_inf(&self, a: u128) -> bool {
        self.est_nombre(a) && self.ef(a) == self.emax()
    }
    fn est_zero(&self, a: u128) -> bool {
        self.est_nombre(a) && self.ef(a) != self.emax() && a & self.mant_masque() == 0
    }
    fn negatif(&self, a: u128) -> bool {
        self.etat(a) == 1
    }
    /// la mantisse et l'exposant binaire de son bit 0
    fn decode(&self, a: u128) -> (U256, i64) {
        let e = (self.ef(a) as i64).max(1);
        (U256::de(a & self.mant_masque()), 2 * (e - self.biais))
    }

    /// le même arrondi, quand m tient dans 128 bits (le cas le plus courant) : sans U256
    fn arrondir_u(&self, m: u128, ex: i64, collant: bool) -> u128 {
        let p = self.p;
        if m == 0 {
            return 0;
        }
        let mut ex = ex;
        let mut k = (128 - m.leading_zeros() as i64) - p;
        if (ex + k) & 1 != 0 {
            k += 1;
        }
        let qmin = 2 * (1 - self.biais);
        if ex + k < qmin {
            k = qmin - ex;
        }
        let mut q: u128;
        if k > 0 {
            if k > 128 {
                q = 0;
            } else if k == 128 {
                // q = 0 ; le reste est m, la moitié 2^127
                let demi = 1u128 << 127;
                q = (m > demi || (m == demi && collant)) as u128;
            } else {
                q = m >> k;
                let bas = m & ((1u128 << k) - 1);
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
            return q;
        }
        let e = ex / 2 + self.biais;
        if e >= self.emax() as i64 {
            return self.emax() << p;
        }
        ((e as u128) << p) | q
    }

    /// m × 2^ex arrondi (m > 0) : exposant << p | mantisse, sans l'état. collant : des bits non nuls sous m.
    pub fn arrondir(&self, m: U256, ex: i64, collant: bool) -> u128 {
        if m.hi == 0 {
            return self.arrondir_u(m.lo, ex, collant);
        }
        let p = self.p;
        if m.est_nul() {
            return 0;
        }
        let mut ex = ex;
        let mut k = m.bits() - p;
        if (ex + k) & 1 != 0 {
            k += 1;
        }
        let qmin = 2 * (1 - self.biais);
        if ex + k < qmin {
            k = qmin - ex;
        }
        let mut q: U256;
        if k > 0 {
            if k > 256 {
                q = U256::ZERO;
            } else {
                q = m.shr(k);
                let bas = m.bas(k);
                let demi = U256::puissance(k - 1);
                if bas > demi || (bas == demi && (collant || q.lo & 1 == 1)) {
                    q = q.add(&U256::de(1));
                }
            }
            ex += k;
            if q == U256::puissance(p) {
                q = U256::puissance(p - 2);
                ex += 2;
            }
        } else {
            q = m.shl(-k);
            ex += k;
        }
        let q = q.lo;
        if q < 1u128 << (p - 2) {
            return q;
        }
        let e = ex / 2 + self.biais;
        if e >= self.emax() as i64 {
            return self.emax() << p;
        }
        ((e as u128) << p) | q
    }

    fn depuis(&self, s: bool, m: U256, ex: i64, collant: bool) -> u128 {
        if m.est_nul() {
            return self.signe(s);
        }
        self.signe(s) | self.arrondir(m, ex, collant)
    }

    fn special(&self, a: u128, b: u128) -> Option<u128> {
        let (ea, eb) = (self.etat(a), self.etat(b));
        if ea == 3 || eb == 3 {
            return Some(self.variable());
        }
        if ea == 0 || eb == 0 {
            return Some(0);
        }
        None
    }

    pub fn neg(&self, a: u128) -> u128 {
        if self.est_nombre(a) { a ^ (3u128 << (self.taille - 2)) } else { a }
    }

    pub fn add(&self, a: u128, b: u128) -> u128 {
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
        if ma0.est_nul() && mb0.est_nul() {
            return self.signe(sa && sb);
        }
        if ma0.est_nul() {
            return self.depuis(sb, mb0, xb0, false);
        }
        if mb0.est_nul() {
            return self.depuis(sa, ma0, xa0, false);
        }
        let (mut ma, mut xa, mut sa, mut mb, mut xb, mut sb) = (ma0, xa0, sa, mb0, xb0, sb);
        if xa < xb {
            std::mem::swap(&mut ma, &mut mb);
            std::mem::swap(&mut xa, &mut xb);
            std::mem::swap(&mut sa, &mut sb);
        }
        // l'écart permet la somme exacte sur 256 bits ; sinon b est bien plus petit que a, et a reçoit 128 bits de garde
        let d = xa - xb;
        if ma.bits() + d <= 126 {
            // tout tient dans 128 bits : la somme exacte en u128
            let (a_, b_) = (ma.lo << d, mb.lo);
            let (m, s) = if sa == sb {
                (a_ + b_, sa)
            } else if a_ < b_ {
                (b_ - a_, sb)
            } else {
                (a_ - b_, sa)
            };
            if m == 0 {
                return self.signe(false);
            }
            return self.signe(s) | self.arrondir_u(m, xb, false);
        }
        if d < 250 {
            // b est loin sous a : a reçoit g bits de garde (tout tient dans 127 bits), b est décalé et ses bits perdus
            // se résument en un bit collé (le bit 0, toujours 1 s'il en manque). Le résultat garde au moins g - 1 bits
            // sous la mantisse, et le vrai résultat et le résultat collé ne sont séparés par aucune limite d'arrondi
            // (des entiers pairs) : l'arrondi est le même.
            let g = 126 - ma.bits();
            let a_ = ma.lo << g;
            let sh = d - g;
            let b_ = if sh >= 128 { 1 } else { (mb.lo >> sh) | ((mb.lo & ((1u128 << sh) - 1) != 0) as u128) };
            let (m, s) = if sa == sb { (a_ + b_, sa) } else { (a_ - b_, sa) };
            return self.signe(s) | self.arrondir_u(m, xa - g, false);
        }
        let (m_a, m_b, ex) = if d <= 120 {
            (ma.shl(d), mb, xb)
        } else {
            let sh = d - 128;
            let b = if sh >= 256 {
                U256::de(1)
            } else if sh > 0 {
                let q = mb.shr(sh);
                if q.shl(sh) != mb { U256 { hi: q.hi, lo: q.lo | 1 } } else { q }
            } else {
                mb.shl(-sh)
            };
            (ma.shl(128), b, xa - 128)
        };
        let (m, s) = if sa == sb {
            (m_a.add(&m_b), sa)
        } else if m_a < m_b {
            (m_b.sub(&m_a), sb)
        } else {
            (m_a.sub(&m_b), sa)
        };
        if m.est_nul() {
            return self.signe(false);
        }
        self.depuis(s, m, ex, false)
    }

    pub fn sub(&self, a: u128, b: u128) -> u128 {
        self.add(a, self.neg(b))
    }

    pub fn mul(&self, a: u128, b: u128) -> u128 {
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
        if self.p <= 63 {
            // deux mantisses de 52 bits au plus : le produit tient dans 128 bits
            let m = ma.lo * mb.lo;
            if m == 0 {
                return self.signe(s);
            }
            return self.signe(s) | self.arrondir_u(m, xa + xb, false);
        }
        let m = U256::mul(ma.lo, mb.lo);
        if m.est_nul() {
            return self.signe(s);
        }
        // le produit ramené à 126 bits, les bits perdus collés au bit 0 (comme pour l'addition) : au moins 12 bits sous
        // la mantisse, le même arrondi
        let n = m.bits();
        if n <= 126 {
            return self.signe(s) | self.arrondir_u(m.lo, xa + xb, false);
        }
        let sh = n - 126;              // de 1 à 100 : m.hi n'est pas nul
        let q = (m.hi << (128 - sh)) | (m.lo >> sh) | ((m.lo & ((1u128 << sh) - 1) != 0) as u128);
        self.signe(s) | self.arrondir_u(q, xa + xb + sh, false)
    }

    pub fn div(&self, a: u128, b: u128) -> u128 {
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
        let sh = 255 - ma.bits();
        let n = ma.shl(sh);
        let (q, r) = n.divrem_u128(mb.lo);
        self.depuis(s, q, xa - xb - sh, r != 0)
    }

    pub fn racine(&self, a: u128) -> u128 {
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
            m = m.shl(1);
            ex -= 1;
        }
        let j = (254 - m.bits()) / 2;
        let n = m.shl(2 * j);
        let r = n.isqrt();
        self.depuis(false, r, (ex - 2 * j) / 2, r.mul_256(&r) != n)
    }

    /// 0 égaux, 1 a < b, 2 a > b, 3 sans ordre
    pub fn cmp(&self, a: u128, b: u128) -> u128 {
        if self.special(a, b).is_some() {
            return 3;
        }
        let (na, nb) = (self.negatif(a), self.negatif(b));
        let rang = |x: u128| -> u8 {
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
            let (ha, hb) = (ma.bits() + xa, mb.bits() + xb);
            if ha != hb {
                ha.cmp(&hb)
            } else {
                let x = xa.min(xb);
                ma.shl(xa - x).cmp(&mb.shl(xb - x))
            }
        };
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

    /// un entier de `l` bits (sans signe, ou signé) vers ce format
    pub fn de_entier(&self, v: u128, l: u32, signe: bool) -> u128 {
        let v = if l == 128 { v } else { v & ((1u128 << l) - 1) };
        let neg = signe && (v >> (l - 1)) & 1 == 1;
        let mag = if neg { (if l == 128 { v } else { v | !((1u128 << l) - 1) }).wrapping_neg() } else { v };
        self.depuis(neg, U256::de(mag), 0, false)
    }

    /// vers un entier signé de `l` bits, tronqué ou arrondi au plus proche pair, saturé ; inconnu, variable : 0
    pub fn vers_entier(&self, a: u128, arrondir: bool, l: u32) -> u128 {
        let masque = if l == 128 { u128::MAX } else { (1u128 << l) - 1 };
        if !self.est_nombre(a) {
            return 0;
        }
        let neg = self.negatif(a);
        let satur = if neg { 1u128 << (l - 1) } else { (1u128 << (l - 1)) - 1 };
        if self.est_inf(a) {
            return satur;
        }
        let (m, ex) = self.decode(a);
        if m.est_nul() {
            return 0;
        }
        let mag: U256 = if ex >= 0 {
            if m.bits() + ex > l as i64 {
                return satur;
            }
            m.shl(ex)
        } else {
            let k = -ex;
            if k >= 256 {
                U256::ZERO
            } else {
                let q = m.shr(k);
                if !arrondir {
                    q
                } else {
                    let bas = m.bas(k);
                    let demi = U256::puissance(k - 1);
                    if bas > demi || (bas == demi && q.lo & 1 == 1) { q.add(&U256::de(1)) } else { q }
                }
            }
        };
        let lim = U256::puissance(l as i64 - 1);
        if mag >= lim {
            return satur;
        }
        if neg { mag.lo.wrapping_neg() & masque } else { mag.lo }
    }

    /// vers un autre format quaternaire
    pub fn vers(&self, autre: &Fmt, a: u128) -> u128 {
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

    /// vers les bits du binary de l'IEEE de même taille (inconnu et variable : le NaN canonique)
    pub fn vers_ieee(&self, a: u128) -> u128 {
        let k = self.taille;
        let (pp, b, emax): (i64, i64, u128) = match k {
            32 => (24, 127, 255),
            64 => (53, 1023, 2047),
            _ => (113, 16383, 32767),
        };
        if !self.est_nombre(a) {
            return (emax << (pp - 1)) | (1u128 << (pp - 2));
        }
        let s = (self.negatif(a) as u128) << (k - 1);
        if self.est_inf(a) {
            return (emax << (pp - 1)) | s;
        }
        let (m, ex) = self.decode(a);
        if m.est_nul() {
            return s;
        }
        let e = m.bits() - 1 + ex;
        let q = (e - (pp - 1)).max(2 - b - pp);
        let mut q = q;
        let mut n: U256 = if ex >= q {
            m.shl(ex - q)
        } else {
            let k2 = q - ex;
            if k2 > 256 {
                U256::ZERO
            } else {
                let t = m.shr(k2);
                let bas = m.bas(k2);
                let demi = U256::puissance(k2 - 1);
                if bas > demi || (bas == demi && t.lo & 1 == 1) { t.add(&U256::de(1)) } else { t }
            }
        };
        if n == U256::puissance(pp) {
            n = n.shr(1);
            q += 1;
        }
        let n = n.lo;
        if n >= 1u128 << (pp - 1) {
            let be = q + (pp - 1) + b;
            if be >= emax as i64 {
                return (emax << (pp - 1)) | s;
            }
            return ((be as u128) << (pp - 1)) | (n - (1u128 << (pp - 1))) | s;
        }
        n | s
    }

    /// depuis les bits du binary de l'IEEE de même taille (un NaN donne variable)
    pub fn de_ieee(&self, d: u128) -> u128 {
        let k = self.taille;
        let (pp, b, emax): (i64, i64, u128) = match k {
            32 => (24, 127, 255),
            64 => (53, 1023, 2047),
            _ => (113, 16383, 32767),
        };
        let s = (d >> (k - 1)) & 1 == 1;
        let e = (d >> (pp - 1)) & emax;
        let m = d & ((1u128 << (pp - 1)) - 1);
        if e == emax {
            return if m != 0 { self.variable() } else { self.inf(s) };
        }
        let (mm, ex) = if e == 0 { (m, 2 - b - pp) } else { (m | (1u128 << (pp - 1)), e as i64 - b - pp + 1) };
        if mm == 0 {
            return self.signe(s);
        }
        self.depuis(s, U256::de(mm), ex, false)
    }
}
