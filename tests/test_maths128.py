#!/usr/bin/env python3
"""La bibliothèque mathématique du flottant de 128 bits (vtx128, sur Lugus) contre une référence à 80 chiffres (module
decimal). L'écart se compte en ulps de 112 bits (un ulp de 111 bits, le pire cas du quaternaire, compte double) ; le
programme tourne sur la machine Rust de Lugus.

    python3 tests/test_maths128.py [nombre de valeurs par fonction]"""
import math
import os
import random
import subprocess
import sys
import tempfile
from decimal import Decimal, getcontext, ROUND_FLOOR
from fractions import Fraction

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, racine)
sys.path.insert(0, os.path.join(racine, "spu64"))
import vtx128 as V  # noqa: E402
from qflot import Q128  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 60
EXE = os.path.join(racine, "vtx-rs", "target", "release", "lugus" + (".exe" if os.name == "nt" else ""))
M64 = (1 << 64) - 1
getcontext().prec = 80
g = random.Random(128)


def D(fr):
    return Decimal(fr.numerator) / Decimal(fr.denominator)


def pi_d():
    def at(inv):
        x, s, k = Decimal(1) / inv, Decimal(0), 0
        t = x
        while True:
            terme = t / (2 * k + 1)
            if abs(terme) < Decimal(10) ** -85:
                return s
            s += terme if k % 2 == 0 else -terme
            t *= x * x
            k += 1
    return 16 * at(5) - 4 * at(239)


PI = pi_d()


def sin_d(x):
    k = (x / (PI / 2)).to_integral_value()
    r = x - k * PI / 2
    z = r * r
    s, c, t, n = Decimal(0), Decimal(0), r, 1
    while abs(t) > Decimal(10) ** -85:
        s += t
        t *= -z / ((n + 1) * (n + 2))
        n += 2
    t, n = Decimal(1), 0
    while abs(t) > Decimal(10) ** -85:
        c += t
        t *= -z / ((n + 1) * (n + 2))
        n += 2
    return [s, c, -s, -c][int(k) % 4]


def cos_d(x):
    return sin_d(x + PI / 2)


def atan_d(x):
    neg = x < 0
    x = abs(x)
    inv = x > 1
    if inv:
        x = 1 / x
    for _ in range(4):
        x = x / (1 + (1 + x * x).sqrt())
    z, s, t, n = x * x, Decimal(0), x, 0
    while abs(t) > Decimal(10) ** -85:
        s += t / (2 * n + 1) * (1 if n % 2 == 0 else -1)
        t *= z
        n += 1
    r = 16 * s
    if inv:
        r = PI / 2 - r
    return -r if neg else r


def asin_d(x):
    if abs(x) == 1:
        return PI / 2 * (1 if x > 0 else -1)
    return atan_d(x / (1 - x * x).sqrt())


def acos_d(x):
    return PI / 2 - asin_d(x)


fonctions = [
    ("exponentielle_128", lambda x: x.exp(), lambda: g.uniform(-11000, 11000) if g.random() < 0.3 else g.uniform(-30, 30)),
    ("logarithme_128", lambda x: x.ln(), lambda: math.exp(g.uniform(-700, 700)) if g.random() < 0.5 else g.uniform(0.5, 2)),
    ("sinus_128", sin_d, lambda: g.uniform(-100, 100) if g.random() < 0.7 else g.uniform(-1e6, 1e6)),
    ("cosinus_128", cos_d, lambda: g.uniform(-100, 100)),
    ("tangente_128", lambda x: sin_d(x) / cos_d(x), lambda: g.uniform(-1.5, 1.5)),
    ("arctangente_128", atan_d, lambda: g.uniform(-3, 3) if g.random() < 0.6 else math.exp(g.uniform(-40, 40))),
    ("arcsinus_128", asin_d, lambda: g.uniform(-1, 1)),
    ("arccosinus_128", acos_d, lambda: g.uniform(-1, 1)),
]


def bits_au_hasard(x):
    """Un flottant de 128 bits proche de x, dont les 112 bits de mantisse sont tous tirés (pas seulement les 53 de x)."""
    v = Q128.depuis(Fraction(x))
    return v ^ g.getrandbits(50)


def ulps(v, ref):
    if not Q128.est_nombre(v) or Q128.est_inf(v):
        return 10 ** 9
    if ref == 0:
        return 0 if Q128.est_zero(v) else 10 ** 9
    e = int((abs(ref).ln() / Decimal(2).ln()).to_integral_value(rounding=ROUND_FLOOR))
    ecart = abs(D(Q128.valeur(v)) - ref)
    return float(ecart / Decimal(2) ** (e - 111))


src = "fonction lire(): flottant_petuar { soit b = entrée(); soit h = entrée(); retour comme_flottant_petuar(entier_petuar_de(h, b)); }\n"
src += "fonction principal() {\n    soit n = entrée();\n"
for nom, _, _ in fonctions:
    src += f"    pour i dans 0..n {{ sortie(bits({nom}(lire()))); }}\n"
src += "}\n"
xs = [[bits_au_hasard(gen()) for _ in range(N)] for _, _, gen in fonctions]
entrees = [N]
for col in xs:
    for v in col:
        entrees += [v & M64, v >> 64]
mots = V.assembler(V.compiler(src))
with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
    f.write(",".join(map(str, mots)) + ";" + ",".join(map(str, entrees)) + "\n")
    nomf = f.name
ligne = subprocess.run([EXE, "corpus", nomf], capture_output=True, text=True).stdout.strip()
os.unlink(nomf)
sor = [int(v) for v in ligne.split("|")[1].split(",")]
pas = int(ligne.split("|")[0])
mauvais = 0
for k, (nom, ref, _) in enumerate(fonctions):
    res = sor[k * N:(k + 1) * N]
    pires = [ulps(v, ref(D(Q128.valeur(x)))) for x, v in zip(xs[k], res)]
    pire = max(pires)
    ok = pire < 4
    mauvais += not ok
    print(f"  {'ok  ' if ok else 'ÉCART'} {nom} : pire écart {pire:.2f} ulp, moyen {sum(pires) / len(pires):.2f} ({N} valeurs)")
# puissance(x, y) = exp(y log x), avec y log x en deux parties (sinon l'erreur du logarithme serait multipliée par |y log x|)
src_p = src.split("fonction principal")[0] + "fonction principal() { soit n = entrée(); pour i dans 0..n { soit x = lire(); soit y = lire(); sortie(bits(puissance_128(x, y))); } }\n"
paires = [(bits_au_hasard(g.uniform(0.1, 10)), bits_au_hasard(g.uniform(-10, 10))) for _ in range(N)]
ent_p = [N]
for x, y in paires:
    ent_p += [x & M64, x >> 64, y & M64, y >> 64]
with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
    f.write(",".join(map(str, V.assembler(V.compiler(src_p)))) + ";" + ",".join(map(str, ent_p)) + "\n")
    nomf = f.name
lp = subprocess.run([EXE, "corpus", nomf], capture_output=True, text=True).stdout.strip()
os.unlink(nomf)
res_p = [int(v) for v in lp.split("|")[1].split(",")]
ep = [ulps(v, (D(Q128.valeur(y)) * D(Q128.valeur(x)).ln()).exp()) for (x, y), v in zip(paires, res_p)]
okp = max(ep) < 8
mauvais += not okp
print(f"  {'ok  ' if okp else 'ÉCART'} puissance_128 (x de 0,1 à 10, y de -10 à 10) : pire écart {max(ep):.2f} ulp, moyen "
      f"{sum(ep) / len(ep):.2f} (y log x et le logarithme en deux parties ; exigé : moins de 8)")
print(f"{len(fonctions) * N} appels, {pas} instructions de Lugus ({pas // (len(fonctions) * N)} par appel en moyenne)")
print("Tout est conforme." if not mauvais else f"{mauvais} fonction(s) au-delà de 4 ulps")
sys.exit(1 if mauvais else 0)
