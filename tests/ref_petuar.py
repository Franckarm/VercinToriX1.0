"""Référence exacte du flottant_petuar (le flottant quaternaire de 128 bits de vtx), par fractions : sert aux tests."""
from fractions import Fraction
import math
import ref_ieee128 as I

INCONNU = 0
VARIABLE = 3 << 126
MANT = (1 << 112) - 1
BIAIS = 8247          # valeur = mantisse × 4^(exposant − 8247)

def signe(s):
    return (1 if s else 2) << 126

def inf(s):
    return signe(s) | (16383 << 112)

def etat(a): return a >> 126
def ef(a): return (a >> 112) & 16383

def arrondi(v):
    """exposant << 112 | mantisse, pour v > 0."""
    if v == 0:
        return 0
    q = None
    # plus grand q tel que v >= 4^(q+55)... : mantisse dans [4^55, 4^56)
    e2 = v.numerator.bit_length() - v.denominator.bit_length()
    q = (e2 // 2) - 56
    while Fraction(4) ** (q + 56) <= v:
        q += 1
    while Fraction(4) ** (q + 55) > v:
        q -= 1
    q = max(q, 1 - BIAIS)
    s = v / Fraction(4) ** q
    n = s.numerator // s.denominator
    r = s - n
    if r > Fraction(1, 2) or (r == Fraction(1, 2) and n & 1):
        n += 1
    if n == 1 << 112:
        n = 1 << 110
        q += 1
    if n < 1 << 110:
        return n
    e = q + BIAIS
    if e >= 16383:
        return 16383 << 112
    return (e << 112) | n

def valeur(a):
    s = -1 if etat(a) == 1 else 1
    e = ef(a)
    return s * Fraction(a & MANT) * Fraction(4) ** (max(e, 1) - BIAIS)

def est_nombre(a): return etat(a) in (1, 2)
def est_inf(a): return est_nombre(a) and ef(a) == 16383
def est_zero(a): return est_nombre(a) and ef(a) != 16383 and a & MANT == 0

def special(a, b):
    if etat(a) == 3 or etat(b) == 3: return VARIABLE
    if etat(a) == 0 or etat(b) == 0: return INCONNU
    return None

def depuis(v, sz=0):
    if v == 0: return signe(sz)
    if v < 0: return signe(1) | arrondi(-v)
    return signe(0) | arrondi(v)

def add(a, b):
    sp = special(a, b)
    if sp is not None: return sp
    if est_inf(a) and est_inf(b): return a if etat(a) == etat(b) else VARIABLE
    if est_inf(a): return a
    if est_inf(b): return b
    va, vb = valeur(a), valeur(b)
    v = va + vb
    if v == 0:
        if est_zero(a) and est_zero(b) and etat(a) == 1 and etat(b) == 1:
            return signe(1)
        return signe(0)
    return depuis(v)

def neg(a): return a ^ (3 << 126) if est_nombre(a) else a
def sub(a, b): return add(a, neg(b))

def mul(a, b):
    sp = special(a, b)
    if sp is not None: return sp
    s = etat(a) != etat(b)
    if est_inf(a) or est_inf(b):
        if est_zero(a) or est_zero(b): return VARIABLE
        return inf(s)
    v = valeur(a) * valeur(b)
    if v == 0: return signe(s)
    return signe(s) | arrondi(abs(v))

def div(a, b):
    sp = special(a, b)
    if sp is not None: return sp
    s = etat(a) != etat(b)
    if est_inf(a): return VARIABLE if est_inf(b) else inf(s)
    if est_inf(b): return signe(s)
    if est_zero(b): return VARIABLE if est_zero(a) else inf(s)
    v = valeur(a) / valeur(b)
    if v == 0: return signe(s)
    return signe(s) | arrondi(abs(v))

def racine(a):
    if not est_nombre(a): return a
    if est_zero(a): return a
    if etat(a) == 1: return VARIABLE
    if est_inf(a): return a
    v = valeur(a)
    k = 17000
    n = v * Fraction(4) ** k
    ni = n.numerator // n.denominator
    r = math.isqrt(ni)
    exact = r * r == ni and n.denominator == 1
    w = Fraction(r, 2 ** k) if exact else Fraction(2 * r + 1, 2 ** (k + 1))
    return signe(0) | arrondi(w)

def cmp(a, b):
    if special(a, b) is not None: return 3
    big = Fraction(10) ** 6000
    va = (-big if etat(a) == 1 else big) if est_inf(a) else valeur(a)
    vb = (-big if etat(b) == 1 else big) if est_inf(b) else valeur(b)
    return 0 if va == vb else (1 if va < vb else 2)

def de_d(d):
    s = d >> 63
    e = (d >> 52) & 2047
    m = d & ((1 << 52) - 1)
    if e == 2047: return VARIABLE if m else inf(s)
    v = Fraction(m) * Fraction(2) ** -1074 if e == 0 else Fraction(m | (1 << 52)) * Fraction(2) ** (e - 1075)
    if v == 0: return signe(s)
    return signe(s) | arrondi(v)

def vers_d(a):
    if not est_nombre(a): return 0x7FF8000000000000
    s = etat(a) == 1
    if est_inf(a): return 0x7FF0000000000000 | (s << 63)
    return I.arrondi(abs(valeur(a)), 53, 1023, 2047) | (s << 63)

def de_w(w):
    x = w - (1 << 128) if w >> 127 else w
    return depuis(Fraction(x))

def vers_w(a):
    if not est_nombre(a): return 0
    if est_inf(a) or abs(valeur(a)) >= Fraction(2) ** 127:
        return (1 << 127) if etat(a) == 1 else (1 << 127) - 1
    v = valeur(a)
    n = abs(v.numerator) // v.denominator
    return (-n if v < 0 else n) % (1 << 128)

def vers_ieee(a):
    if not est_nombre(a): return I.NAN
    s = etat(a) == 1
    if est_inf(a): return I.INF | (s << 127)
    return I.arrondi(abs(valeur(a))) | (s << 127)

def de_ieee(b):
    if I.est_nan(b): return VARIABLE
    s = b >> 127
    if I.est_inf(b): return inf(s)
    v = I.valeur(b)
    if v == 0: return signe(s)
    return signe(s) | arrondi(abs(v))

def hasard(g):
    c = g.random()
    s = g.getrandbits(1)
    if c < 0.03: return INCONNU
    if c < 0.05: return VARIABLE
    if c < 0.09: return signe(s)
    if c < 0.11: return inf(s)
    if c < 0.18:
        e = 0
        m = g.getrandbits(g.randint(1, 110))
        return signe(s) | m
    if c < 0.23: e = g.choice([1, 2, 16381, 16382])
    elif c < 0.6: e = 8247 - 55 + g.randint(-30, 30)
    else: e = g.randint(1, 16382)
    k = g.random()
    if k < 0.4: m = g.getrandbits(112)
    elif k < 0.6: m = MANT - g.getrandbits(g.randint(0, 20))
    elif k < 0.8: m = (1 << 110) | (g.getrandbits(g.randint(0, 20)) << g.randint(0, 88))
    else: m = g.getrandbits(112) & ~((1 << g.randint(0, 111)) - 1)
    if m < (1 << 110): m |= 1 << g.choice([110, 111])
    return signe(s) | (e << 112) | (m & MANT)
