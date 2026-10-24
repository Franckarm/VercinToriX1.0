"""Référence exacte du binary128 (IEEE 754), par fractions : arrondi au plus proche, pair en cas d'égalité."""
from fractions import Fraction
import math, random

P, BIAIS, EMAX = 113, 16383, 32767
QMIN = 2 - BIAIS - P
SIGNE = 1 << 127
NAN = 0x7FFF8000000000000000000000000000
INF = 0x7FFF0000000000000000000000000000
FRAC = (1 << 112) - 1


def arrondi(v, p=P, b=BIAIS, emax=EMAX):
    """Bits (sans signe) du flottant le plus proche de v >= 0."""
    if v == 0:
        return 0
    qmin = 2 - b - p
    e = v.numerator.bit_length() - v.denominator.bit_length()
    if Fraction(2) ** e > v:
        e -= 1
    if Fraction(2) ** (e + 1) <= v:
        e += 1
    q = max(e - (p - 1), qmin)
    s = v / Fraction(2) ** q
    n = s.numerator // s.denominator
    r = s - n
    if r > Fraction(1, 2) or (r == Fraction(1, 2) and n & 1):
        n += 1
    if n == 1 << p:
        n >>= 1
        q += 1
    if n >= 1 << (p - 1):
        be = q + (p - 1) + b
        if be >= emax:
            return emax << (p - 1)
        return (be << (p - 1)) | (n - (1 << (p - 1)))
    return n


def est_nan(a):
    return (a >> 112) & 0x7FFF == 0x7FFF and a & FRAC != 0


def est_inf(a):
    return (a >> 112) & 0x7FFF == 0x7FFF and a & FRAC == 0


def valeur(a):
    s = -1 if a >> 127 else 1
    e = (a >> 112) & 0x7FFF
    m = a & FRAC
    if e == 0:
        return s * Fraction(m) * Fraction(2) ** QMIN
    return s * Fraction(m | (1 << 112)) * Fraction(2) ** (e - 16495)


def depuis(v, signe_zero=0):
    if v == 0:
        return SIGNE if signe_zero else 0
    if v < 0:
        return arrondi(-v) | SIGNE
    return arrondi(v)


def add(a, b):
    if est_nan(a) or est_nan(b):
        return NAN
    if est_inf(a) and est_inf(b):
        return a if a == b else NAN
    if est_inf(a):
        return a
    if est_inf(b):
        return b
    va, vb = valeur(a), valeur(b)
    v = va + vb
    if v == 0:
        if va == 0 and vb == 0:
            return SIGNE if (a >> 127) and (b >> 127) else 0
        return 0
    return depuis(v)


def sub(a, b):
    return add(a, b ^ SIGNE)


def mul(a, b):
    s = (a ^ b) >> 127
    if est_nan(a) or est_nan(b):
        return NAN
    if est_inf(a) or est_inf(b):
        if (a << 1) & ((1 << 128) - 1) == 0 or (b << 1) & ((1 << 128) - 1) == 0:
            return NAN
        return INF | (s << 127)
    v = valeur(a) * valeur(b)
    if v == 0:
        return s << 127
    return arrondi(abs(v)) | (s << 127)


def div(a, b):
    s = (a ^ b) >> 127
    if est_nan(a) or est_nan(b):
        return NAN
    if est_inf(a):
        return NAN if est_inf(b) else INF | (s << 127)
    if est_inf(b):
        return s << 127
    if valeur(b) == 0:
        return NAN if valeur(a) == 0 else INF | (s << 127)
    v = valeur(a) / valeur(b)
    if v == 0:
        return s << 127
    return arrondi(abs(v)) | (s << 127)


def racine(a):
    if est_nan(a):
        return NAN
    if valeur(a) == 0 and not est_inf(a):
        return a
    if a >> 127:
        return NAN
    if est_inf(a):
        return a
    v = valeur(a)
    k = 17000
    n = v * Fraction(4) ** k
    n = n.numerator // n.denominator
    r = math.isqrt(n)
    exact = r * r == n and (v * Fraction(4) ** k).denominator == 1
    w = Fraction(r, 2 ** k) if exact else Fraction(2 * r + 1, 2 ** (k + 1))
    return arrondi(w)


def cmp(a, b):
    if est_nan(a) or est_nan(b):
        return 3
    va = valeur(a) if not est_inf(a) else (-1 if a >> 127 else 1) * Fraction(10) ** 6000
    vb = valeur(b) if not est_inf(b) else (-1 if b >> 127 else 1) * Fraction(10) ** 6000
    return 0 if va == vb else (1 if va < vb else 2)


def de_d(d):
    s = d >> 63
    e = (d >> 52) & 2047
    m = d & ((1 << 52) - 1)
    if e == 2047:
        return NAN if m else INF | (s << 127)
    v = Fraction(m) * Fraction(2) ** -1074 if e == 0 else Fraction(m | (1 << 52)) * Fraction(2) ** (e - 1075)
    if v == 0:
        return s << 127
    return arrondi(v) | (s << 127)


def vers_d(a):
    s = a >> 127
    if est_nan(a):
        return 0x7FF8000000000000
    if est_inf(a):
        return 0x7FF0000000000000 | (s << 63)
    v = abs(valeur(a))
    return arrondi(v, 53, 1023, 2047) | (s << 63)


def de_w(w):
    x = w - (1 << 128) if w >> 127 else w
    return depuis(Fraction(x))


def vers_w(a):
    if est_nan(a):
        return 0
    if est_inf(a) or abs(valeur(a)) >= Fraction(2) ** 127:
        return (1 << 127) if a >> 127 else (1 << 127) - 1
    v = valeur(a)
    n = abs(v.numerator) // v.denominator
    if v < 0:
        n = -n
    return n % (1 << 128)


def hasard_x(g):
    c = g.random()
    s = g.getrandbits(1) << 127
    if c < 0.04:
        return s
    if c < 0.06:
        return INF | s
    if c < 0.07:
        return NAN
    if c < 0.15:
        e = 0
    elif c < 0.2:
        e = g.choice([1, 2, 32765, 32766])
    elif c < 0.6:
        e = 16383 + g.randint(-60, 60)
    else:
        e = g.randint(1, 32766)
    k = g.random()
    if k < 0.3:
        m = g.getrandbits(112)
    elif k < 0.5:
        m = (1 << 112) - 1 - g.getrandbits(g.randint(0, 20))
    elif k < 0.7:
        m = g.getrandbits(g.randint(0, 20)) << g.randint(0, 90)
    else:
        m = g.getrandbits(112) & ~((1 << g.randint(0, 111)) - 1)
    return s | (e << 112) | (m & FRAC)
