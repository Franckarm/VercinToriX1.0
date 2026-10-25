"""Les flottants quaternaires de Vercintorix (32, 64 et 128 bits), calculés exactement par fractions : c'est la référence.

Un format : un quit d'état (Belnap : 0 inconnu, 1 négatif, 2 positif, 3 variable), un exposant de `ebits` bits (sa valeur
maximale : l'infini), une mantisse de `nq` quits (2 × nq bits, le premier quit non nul sauf à l'exposant 0). Valeur :
mantisse × 4^(max(E, 1) − biais). Arrondi au plus proche, pair au milieu."""
from fractions import Fraction
import math


class Format:
    def __init__(self, nom, nq, ebits, biais):
        self.nom, self.nq, self.ebits, self.biais = nom, nq, ebits, biais
        self.P = 2 * nq                      # bits de mantisse
        self.taille = 2 + ebits + self.P
        self.emax = (1 << ebits) - 1
        self.masque = (1 << self.taille) - 1
        self.mant = (1 << self.P) - 1
        self.VARIABLE = 3 << (self.taille - 2)
        self.INCONNU = 0

    # --- forme
    def signe(self, s):
        return (1 if s else 2) << (self.taille - 2)

    def inf(self, s):
        return self.signe(s) | (self.emax << self.P)

    def etat(self, a):
        return (a >> (self.taille - 2)) & 3

    def ef(self, a):
        return (a >> self.P) & self.emax

    def est_nombre(self, a):
        return self.etat(a) in (1, 2)

    def est_inf(self, a):
        return self.est_nombre(a) and self.ef(a) == self.emax

    def est_zero(self, a):
        return self.est_nombre(a) and self.ef(a) != self.emax and a & self.mant == 0

    def valeur(self, a):
        """Fraction (signée) d'un nombre fini."""
        v = Fraction(a & self.mant) * Fraction(4) ** (max(self.ef(a), 1) - self.biais)
        return -v if self.etat(a) == 1 else v

    def arrondi(self, v):
        """v > 0 (Fraction) -> exposant << P | mantisse."""
        nq = self.nq
        e2 = v.numerator.bit_length() - v.denominator.bit_length()
        q = e2 // 2 - nq
        while Fraction(4) ** (q + nq) <= v:
            q += 1
        while Fraction(4) ** (q + nq - 1) > v:
            q -= 1
        q = max(q, 1 - self.biais)
        t = v / Fraction(4) ** q
        n = t.numerator // t.denominator
        r = t - n
        if r > Fraction(1, 2) or (r == Fraction(1, 2) and n & 1):
            n += 1
        if n == 1 << self.P:
            n, q = 1 << (self.P - 2), q + 1
        if n < 1 << (self.P - 2):
            return n
        if q + self.biais >= self.emax:
            return self.emax << self.P
        return ((q + self.biais) << self.P) | n

    def depuis(self, v, signe_zero=0):
        if v == 0:
            return self.signe(signe_zero)
        if v < 0:
            return self.signe(1) | self.arrondi(-v)
        return self.signe(0) | self.arrondi(v)

    # --- opérations
    def special(self, a, b):
        if self.etat(a) == 3 or self.etat(b) == 3:
            return self.VARIABLE
        if self.etat(a) == 0 or self.etat(b) == 0:
            return self.INCONNU
        return None

    def neg(self, a):
        return a ^ (3 << (self.taille - 2)) if self.est_nombre(a) else a

    def add(self, a, b):
        sp = self.special(a, b)
        if sp is not None:
            return sp
        if self.est_inf(a) and self.est_inf(b):
            return a if self.etat(a) == self.etat(b) else self.VARIABLE
        if self.est_inf(a):
            return a
        if self.est_inf(b):
            return b
        va, vb = self.valeur(a), self.valeur(b)
        v = va + vb
        if v == 0:
            if self.est_zero(a) and self.est_zero(b) and self.etat(a) == 1 and self.etat(b) == 1:
                return self.signe(1)
            return self.signe(0)
        return self.depuis(v)

    def sub(self, a, b):
        return self.add(a, self.neg(b))

    def mul(self, a, b):
        sp = self.special(a, b)
        if sp is not None:
            return sp
        s = self.etat(a) != self.etat(b)
        if self.est_inf(a) or self.est_inf(b):
            if self.est_zero(a) or self.est_zero(b):
                return self.VARIABLE
            return self.inf(s)
        v = self.valeur(a) * self.valeur(b)
        if v == 0:
            return self.signe(s)
        return self.signe(s) | self.arrondi(abs(v))

    def div(self, a, b):
        sp = self.special(a, b)
        if sp is not None:
            return sp
        s = self.etat(a) != self.etat(b)
        if self.est_inf(a):
            return self.VARIABLE if self.est_inf(b) else self.inf(s)
        if self.est_inf(b):
            return self.signe(s)
        if self.est_zero(b):
            return self.VARIABLE if self.est_zero(a) else self.inf(s)
        v = self.valeur(a) / self.valeur(b)
        if v == 0:
            return self.signe(s)
        return self.signe(s) | self.arrondi(abs(v))

    def racine(self, a):
        if not self.est_nombre(a) or self.est_zero(a):
            return a
        if self.etat(a) == 1:
            return self.VARIABLE
        if self.est_inf(a):
            return a
        v = self.valeur(a)
        k = 2 * self.biais + 4 * self.P + 64
        n = v * Fraction(4) ** k
        ni = n.numerator // n.denominator
        r = math.isqrt(ni)
        exact = r * r == ni and n.denominator == 1
        w = Fraction(r, 2 ** k) if exact else Fraction(2 * r + 1, 2 ** (k + 1))
        return self.signe(0) | self.arrondi(w)

    def cmp(self, a, b):
        """0 égaux, 1 a < b, 2 a > b, 3 sans ordre."""
        if self.special(a, b) is not None:
            return 3
        def cle(x):
            if self.est_inf(x):
                return (2 if self.etat(x) == 2 else -2, 0)
            return (0, self.valeur(x))
        ka, kb = cle(a), cle(b)
        return 0 if ka == kb else (1 if ka < kb else 2)

    # --- conversions
    def de_entier(self, n):
        return self.depuis(Fraction(n))

    def vers_entier(self, a, arrondir, bits=64):
        """Tronqué (ou arrondi au plus proche pair), saturé aux entiers signés de `bits` bits ; inconnu, variable : 0."""
        lim = 1 << (bits - 1)
        if not self.est_nombre(a):
            return 0
        if self.est_inf(a):
            n = lim - 1 if self.etat(a) == 2 else -lim
        else:
            v = self.valeur(a)
            if arrondir:
                n = math.floor(v)
                r = v - n
                if r > Fraction(1, 2) or (r == Fraction(1, 2) and n & 1):
                    n += 1
            else:
                n = abs(v.numerator) // v.denominator
                if v < 0:
                    n = -n
            n = max(-lim, min(lim - 1, n))
        return n % (1 << bits)

    def vers(self, autre, a):
        """Vers un autre format quaternaire (exact s'il est plus grand, arrondi sinon)."""
        if not self.est_nombre(a):
            return autre.VARIABLE if self.etat(a) == 3 else autre.INCONNU
        s = self.etat(a) == 1
        if self.est_inf(a):
            return autre.inf(s)
        v = self.valeur(a)
        if v == 0:
            return autre.signe(s)
        return autre.signe(s) | autre.arrondi(abs(v))


Q32 = Format("flottant_32", 11, 8, 138)
Q64 = Format("flottant", 26, 10, 537)
Q128 = Format("flottant_petuar", 56, 14, 8247)


# --- binary64 de l'IEEE (échange)
def ieee64_arrondi(v):
    """Bits (sans signe) du binary64 le plus proche de v > 0."""
    p, b, emax = 53, 1023, 2047
    qmin = 2 - b - p
    e = v.numerator.bit_length() - v.denominator.bit_length()
    if Fraction(2) ** e > v:
        e -= 1
    if Fraction(2) ** (e + 1) <= v:
        e += 1
    q = max(e - (p - 1), qmin)
    t = v / Fraction(2) ** q
    n = t.numerator // t.denominator
    r = t - n
    if r > Fraction(1, 2) or (r == Fraction(1, 2) and n & 1):
        n += 1
    if n == 1 << p:
        n, q = n >> 1, q + 1
    if n >= 1 << (p - 1):
        be = q + (p - 1) + b
        if be >= emax:
            return emax << (p - 1)
        return (be << (p - 1)) | (n - (1 << (p - 1)))
    return n


def vers_ieee64(a):
    F = Q64
    if not F.est_nombre(a):
        return 0x7FF8000000000000
    s = F.etat(a) == 1
    if F.est_inf(a):
        return 0x7FF0000000000000 | (s << 63)
    v = abs(F.valeur(a))
    return (ieee64_arrondi(v) if v else 0) | (s << 63)


def de_ieee64(d):
    F = Q64
    s = d >> 63
    e = (d >> 52) & 2047
    m = d & ((1 << 52) - 1)
    if e == 2047:
        return F.VARIABLE if m else F.inf(s)
    v = Fraction(m) * Fraction(2) ** -1074 if e == 0 else Fraction(m | (1 << 52)) * Fraction(2) ** (e - 1075)
    if v == 0:
        return F.signe(s)
    return F.signe(s) | F.arrondi(v)


# --- binary32, binary64, binary128 de l'IEEE : l'échange, pour toutes les tailles (Lugus, le SPU-128)
IEEE = {32: (24, 127, 255), 64: (53, 1023, 2047), 128: (113, 16383, 32767)}     # précision, biais, exposant maximal


def ieee_arrondi(v, k):
    """Bits (sans signe) du binary de k bits le plus proche de v > 0."""
    p, b, emax = IEEE[k]
    qmin = 2 - b - p
    e = v.numerator.bit_length() - v.denominator.bit_length()
    if Fraction(2) ** e > v:
        e -= 1
    if Fraction(2) ** (e + 1) <= v:
        e += 1
    q = max(e - (p - 1), qmin)
    t = v / Fraction(2) ** q
    n = t.numerator // t.denominator
    r = t - n
    if r > Fraction(1, 2) or (r == Fraction(1, 2) and n & 1):
        n += 1
    if n == 1 << p:
        n, q = n >> 1, q + 1
    if n >= 1 << (p - 1):
        be = q + (p - 1) + b
        if be >= emax:
            return emax << (p - 1)
        return (be << (p - 1)) | (n - (1 << (p - 1)))
    return n


def vers_ieee(F, a, k):
    """Le flottant quaternaire a (format F) vers les bits du binary de k bits ; inconnu et variable : le NaN canonique."""
    p, b, emax = IEEE[k]
    if not F.est_nombre(a):
        return ((emax << (p - 1)) | (1 << (p - 2)))
    s = F.etat(a) == 1
    if F.est_inf(a):
        return (emax << (p - 1)) | (s << (k - 1))
    v = abs(F.valeur(a))
    return (ieee_arrondi(v, k) if v else 0) | (s << (k - 1))


def de_ieee(F, d, k):
    """Les bits d'un binary de k bits vers le format F (un NaN donne variable)."""
    p, b, emax = IEEE[k]
    s = (d >> (k - 1)) & 1
    e = (d >> (p - 1)) & emax
    m = d & ((1 << (p - 1)) - 1)
    if e == emax:
        return F.VARIABLE if m else F.inf(s)
    v = Fraction(m) * Fraction(2) ** (2 - b - p) if e == 0 else Fraction(m | (1 << (p - 1))) * Fraction(2) ** (e - b - p + 1)
    if v == 0:
        return F.signe(s)
    return F.signe(s) | F.arrondi(v)

