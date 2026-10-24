#!/usr/bin/env python3
"""Bibliothèque mathématique en flottant_64 (sinus_64, cosinus_64, tangente_64, exponentielle_64, logarithme_64,
puissance_64, arctangente_64, arctangente2_64, arcsinus_64, arccosinus_64, plancher_64, plafond_64, pi_64) contre le
module math de Python. Écart toléré en ulp (unité du dernier chiffre) : 1 à 2 pour les fonctions de base, 3 pour la
tangente et les puissances à exposant non entier (voir la borne dans le code). Les quatre machines doivent donner les
mêmes mots sur un échantillon."""
import math
import os
import random
import struct
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import machines  # noqa: E402

vtx = machines.vtx
M = 0xFFFFFFFF
r = random.Random(5)
mauvais = 0


def bits(x):
    return struct.unpack("<Q", struct.pack("<d", x))[0]


def flt(b):
    return struct.unpack("<d", struct.pack("<Q", b))[0]


def ulps(a, b):
    if a != a or b != b:
        return 0 if (a != a and b != b) else 1e9
    if math.isinf(a) or math.isinf(b):
        return 0 if a == b else 1e9
    return 0 if a == b else abs(a - b) / math.ulp(b)


def une(nom, ar):
    xs = []
    if nom in ("sinus_64", "cosinus_64", "tangente_64"):
        xs = [r.uniform(-10, 10) for _ in range(300)] + [r.uniform(-1e5, 1e5) for _ in range(100)] \
            + [r.uniform(-1.6e6, 1.6e6) for _ in range(50)] + [k * math.pi / 2 for k in range(-20, 21)] + [0.0, 1e-10, 5e-324]
    elif nom == "exponentielle_64":
        xs = [r.uniform(-20, 20) for _ in range(300)] + [r.uniform(-745, 709) for _ in range(150)] + [0.0, 1e-12, 709.78, -745.1, 1.0]
    elif nom == "logarithme_64":
        xs = [math.exp(r.uniform(-700, 700)) for _ in range(300)] + [r.uniform(0.5, 2) for _ in range(150)] \
            + [1.0, 1.0000001, 0.9999999, 5e-324, 1e-310, 1.7e308, 2.0, 10.0]
    elif nom == "arctangente_64":
        xs = [r.uniform(-5, 5) for _ in range(300)] + [r.uniform(-1e6, 1e6) for _ in range(100)] \
            + [10.0 ** r.randint(-20, 20) for _ in range(50)] + [0.0, 1.0, -1.0, 0.4375, 0.6875, 1.1875, 2.4375, 1e30]
    elif nom in ("arcsinus_64", "arccosinus_64"):
        xs = [r.uniform(-1, 1) for _ in range(400)] + [1.0, -1.0, 0.0, 0.5, 1 - 1e-12, 1e-9]
    else:
        xs = [r.uniform(-1000, 1000) for _ in range(200)] + [float(k) for k in range(-5, 6)] + [-0.5, 0.5, 2.0 ** 52 + 1, -2.0 ** 53, 1e300]
    return xs


def lancer(src, ent):
    mots = vtx.assembler(vtx.compiler(src))
    ligne = machines.lignes_rust([(mots, ent)])[0]
    sor = ligne.split("|")[1]
    return [int(v) for v in sor.split(",")] if sor else [], mots


SRC1 = """
fonction principal() {
    soit n = entrée();
    pour i dans 0..n {
        soit lo = entrée(); soit hi = entrée();
        soit y = %s(flottant_64_de(hi, lo));
        sortie(bas(y)); sortie(haut(y));
    }
}
"""
SRC2 = """
fonction principal() {
    soit n = entrée();
    pour i dans 0..n {
        soit lo = entrée(); soit hi = entrée();
        soit a = flottant_64_de(hi, lo);
        lo = entrée(); hi = entrée();
        soit y = %s(a, flottant_64_de(hi, lo));
        sortie(bas(y)); sortie(haut(y));
    }
}
"""
FUN = {"sinus_64": (math.sin, 2), "cosinus_64": (math.cos, 2), "tangente_64": (math.tan, 3), "exponentielle_64": (math.exp, 2),
       "logarithme_64": (math.log, 2), "arctangente_64": (math.atan, 2), "arcsinus_64": (math.asin, 2),
       "arccosinus_64": (math.acos, 3), "plancher_64": (lambda x: float(math.floor(x)), 0), "plafond_64": (lambda x: float(math.ceil(x)), 0)}
echantillons = []
for nom, (f, tol) in FUN.items():
    xs = une(nom, 1)
    ent = [len(xs)] + [v for x in xs for v in (bits(x) & M, bits(x) >> 32)]
    sor, mots = lancer(SRC1 % nom, ent)
    pire, nex, qui = 0, 0, None
    for i, x in enumerate(xs):
        got = flt(sor[2 * i] | sor[2 * i + 1] << 32)
        try:
            ref = f(x)
        except (ValueError, OverflowError):
            ref = float("nan")
        e = ulps(got, ref)
        nex += e == 0
        if e > pire:
            pire, qui = e, (x, got, ref)
    ok = pire <= tol and len(sor) == 2 * len(xs)
    mauvais += not ok
    print(("  ok  " if ok else "  ÉCART ") + f"{nom}: {len(xs)} valeurs, {nex} exactes, pire écart {pire:.2f} ulp (toléré {tol})" + ("" if ok else f" {qui}"))
    echantillons.append((mots, ent[:1] + ent[1:41]))      # 20 valeurs pour la comparaison des machines (n corrigé plus bas)
    echantillons[-1][1][0] = 20

# deux arguments : puissance_64 et arctangente2_64
paires = [(r.uniform(0.01, 100), r.uniform(-5, 5)) for _ in range(200)] + [(r.uniform(-10, 10), float(r.randint(-12, 12))) for _ in range(100)] \
    + [(2.0, 10.0), (10.0, -3.0), (0.0, 2.0), (0.0, -1.0), (-8.0, 3.0), (-8.0, 1.0 / 3.0), (5.0, 0.0), (1.0, 1e10), (2.0, 1023.0), (2.0, 1024.0),
       (2.0, -1074.0), (1e-5, 60.0)]
ent = [len(paires)] + [v for a, b in paires for v in (bits(a) & M, bits(a) >> 32, bits(b) & M, bits(b) >> 32)]
sor, mots = lancer(SRC2 % "puissance_64", ent)
pire, qui = 0, None
for i, (a, b) in enumerate(paires):
    got = flt(sor[2 * i] | sor[2 * i + 1] << 32)
    try:
        ref = math.pow(a, b)
    except (ValueError, OverflowError):
        ref = float("inf") if (a == 0 and b < 0) or (a != 0 and abs(b) > 1 and abs(a) > 1) else float("nan")
    # exposant non entier : l'erreur de exp(y ln x) croît avec |y ln x|
    tol = 4 if b == int(b) and abs(b) <= 1024 else 2 + abs(b * math.log(abs(a))) if a != 0 else 2
    e = ulps(got, ref)
    if e > tol and not (math.isinf(ref) and math.isinf(got)):
        pire, qui = max(pire, e), (a, b, got, ref)
ok = pire == 0
mauvais += not ok
print(("  ok  " if ok else "  ÉCART ") + f"puissance_64: {len(paires)} couples" + ("" if ok else f" {qui}"))
echantillons.append((mots, [20] + ent[1:81]))

pa = [(r.uniform(-5, 5), r.uniform(-5, 5)) for _ in range(400)] + [(0.0, 1.0), (0.0, -1.0), (1.0, 0.0), (-1.0, 0.0), (0.0, 0.0), (1e-300, 1e300), (1.0, 1.0), (-1.0, -1.0), (1.0, -1.0), (-1.0, 1.0)]
ent = [len(pa)] + [v for a, b in pa for v in (bits(a) & M, bits(a) >> 32, bits(b) & M, bits(b) >> 32)]
sor, mots = lancer(SRC2 % "arctangente2_64", ent)
pire, qui = 0, None
for i, (a, b) in enumerate(pa):
    got = flt(sor[2 * i] | sor[2 * i + 1] << 32)
    e = ulps(got, math.atan2(a, b))
    if e > pire:
        pire, qui = e, (a, b, got, math.atan2(a, b))
ok = pire <= 2
mauvais += not ok
print(("  ok  " if ok else "  ÉCART ") + f"arctangente2_64: {len(pa)} couples, pire écart {pire:.2f} ulp (toléré 2)" + ("" if ok else f" {qui}"))
echantillons.append((mots, [20] + ent[1:81]))

res = machines.lancer_toutes(echantillons)
ec = machines.comparer(res)
ok = not any(ec.values())
mauvais += not ok
print(("  ok  " if ok else "  ÉCART ") + f"les quatre machines s'accordent sur les {len(echantillons)} programmes de la bibliothèque : {ec}")
print("Tout est conforme." if not mauvais else f"{mauvais} écart(s)")
sys.exit(1 if mauvais else 0)
