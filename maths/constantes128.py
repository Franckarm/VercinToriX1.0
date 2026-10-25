#!/usr/bin/env python3
"""Les constantes de la bibliothèque mathématique du flottant de 128 bits (prélude de vtx128) : les bits exacts, calculés
ici à 80 chiffres (module decimal), puis arrondis au plus proche par le format Q128 (spu64/qflot.py). Les parties
« hautes » (LN2_HAUT, PI2_1, PI2_2) sont tronquées à 80 bits : leur produit par un entier de 32 bits est exact.

    python3 maths/constantes128.py       écrit les lignes « constante » à recopier dans le prélude"""
import os
import sys
from decimal import Decimal, getcontext
from fractions import Fraction

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "spu64"))
from qflot import Q128  # noqa: E402

getcontext().prec = 90


def pi_dec():
    # Machin : pi = 16 atan(1/5) - 4 atan(1/239)
    def at(inv):
        x, s, k, p = Decimal(1) / inv, Decimal(0), 0, None
        t = x
        while True:
            terme = t / (2 * k + 1)
            if terme == 0 or (p is not None and abs(terme) < Decimal(10) ** -88):
                break
            s += terme if k % 2 == 0 else -terme
            t *= x * x
            k += 1
            p = terme
        return s
    return 16 * at(5) - 4 * at(239)


def frac(d):
    return Fraction(d)


def tronque(v, bits):
    """v > 0 (Fraction) tronqué à `bits` bits significatifs."""
    e = v.numerator.bit_length() - v.denominator.bit_length()
    while Fraction(2) ** e > v:
        e -= 1
    while Fraction(2) ** (e + 1) <= v:
        e += 1
    q = Fraction(2) ** (e - bits + 1)
    return (v / q).__floor__() * q


ln2 = frac(Decimal(2).ln())
pi = frac(pi_dec())
ln2_haut = tronque(ln2, 80)
pi2 = pi / 2
pi2_1 = tronque(pi2, 80)
pi2_2 = tronque(pi2 - pi2_1, 80)
pi2_3 = pi2 - pi2_1 - pi2_2
C = {
    "__X_LN2_HAUT": ln2_haut, "__X_LN2_BAS": ln2 - ln2_haut, "__X_INV_LN2": 1 / ln2,
    "__X_PI2_1": pi2_1, "__X_PI2_2": pi2_2, "__X_PI2_3": pi2_3, "__X_DEUX_SUR_PI": 2 / pi,
    "__X_PI": pi, "__X_PI2": pi2, "__X_RACINE2": frac(Decimal(2).sqrt()),
}
# l'arc tangente de 1/2 et de 3/2 (atan(1) = pi / 4) : les centres de la réduction de l'arc tangente


def atan_dec(x):
    neg, x = x < 0, abs(x)
    for _ in range(6):
        x = x / (1 + (1 + x * x).sqrt())
    z, t, n, r = x * x, x, 0, Decimal(0)
    while abs(t) > Decimal(10) ** -88:
        r += t / (2 * n + 1) * (1 if n % 2 == 0 else -1)
        t *= z
        n += 1
    return -64 * r if neg else 64 * r


C["__X_ATAN_DEMI"] = frac(atan_dec(Decimal(1) / 2))
C["__X_PI4"] = pi / 4
C["__X_ATAN_3DEMIS"] = frac(atan_dec(Decimal(3) / 2))
# les bornes de l'exponentielle : le logarithme du plus grand nombre fini, et du plus petit nombre non nul (dénormal)
plus_grand = Q128.valeur((Q128.emax - 1) << Q128.P | Q128.mant)
plus_petit = Q128.valeur(1)
C["__X_EXP_MAX"] = frac(Decimal(plus_grand.numerator).ln() - Decimal(plus_grand.denominator).ln())
C["__X_EXP_MIN"] = frac(Decimal(plus_petit.numerator).ln() - Decimal(plus_petit.denominator).ln())
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import vtx128  # noqa: E402
for nom, v in C.items():
    d = Decimal(v.numerator) / Decimal(v.denominator)
    mant, ex = f"{d:.40e}".split("e")
    t = f"{mant}e{int(ex)}"
    exact = Q128.depuis(v)
    lu = vtx128.bits_petuar_decimal(t.replace("-", "", 1) if t.startswith("-") else t)
    if t.startswith("-"):
        lu ^= 3 << 126
    assert lu == exact, (nom, t)
    print(f"constante {nom} = {t}Q;")
