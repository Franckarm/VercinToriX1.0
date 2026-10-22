#!/usr/bin/env python3
"""Flottants binary32 et entiers de 64 bits dans vtx, contre des références indépendantes.
 1. Opérations flottantes sur des mots tirés au hasard (dont NaN, infinis, zéros signés, sous-normaux) contre numpy float32.
 2. Opérations sur les longs (signés, complément à deux) contre les entiers exacts de Python.
 3. Programmes typés : mélanges entier et flottant, fonctions typées, conversions ; et les erreurs de typage prévues."""
import importlib.util
import math
import os
import random
import struct
import warnings

import numpy as np

warnings.filterwarnings("ignore")
spec = importlib.util.spec_from_file_location("vtx", __import__("os").path.join(__import__("os").path.dirname(__import__("os").path.abspath(__file__)), "..", "vtx.py"))
vtx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vtx)
M = 0xFFFFFFFF
r = random.Random(64)


def nb(x):
    """float32 numpy -> mot, NaN unique."""
    x = np.float32(x)
    return 0x7FC00000 if np.isnan(x) else int(x.view(np.uint32))


def fv(w):
    return np.array([w], dtype=np.uint32).view(np.float32)[0]


def sat(t):
    return 0x7FFFFFFF if t >= 2 ** 31 else 0x80000000 if t < -2 ** 31 else t & M


def ref_f(a, b, k):
    x, y = fv(a), fv(b)
    with np.errstate(all="ignore"):
        res = [nb(x + y), nb(x - y), nb(x * y), nb(x / y), int(x == y), int(x < y), int(x <= y), nb(np.sqrt(x))]
    xf = float(x)
    res.append(0 if xf != xf else sat(math.trunc(xf)) if math.isfinite(xf) else (0x7FFFFFFF if xf > 0 else 0x80000000))
    res.append(0 if xf != xf else sat(int(np.rint(xf))) if math.isfinite(xf) else (0x7FFFFFFF if xf > 0 else 0x80000000))
    res.append(nb(np.float32(k)))
    res.append(nb(np.float32(k - 2 ** 32 if k >= 2 ** 31 else k)))
    return res


SRC_F = """
fonction principal() {
    soit n = entrée();
    pour i dans 0..n {
        soit x = comme_flottant(entrée());
        soit y = comme_flottant(entrée());
        soit k = entrée();
        sortie(x + y); sortie(x - y); sortie(x * y); sortie(x / y);
        sortie(x == y); sortie(x < y); sortie(x <= y); sortie(racine(x));
        sortie(entier(x)); sortie(arrondi(x)); sortie(flottant(k)); sortie(flottant_signe(k));
    }
}
"""
SPECIAUX = [0, 0x80000000, 0x3F800000, 0xBF800000, 0x7F800000, 0xFF800000, 0x7FC00000, 0x7FA00001, 0x00000001, 0x807FFFFF,
            0x7F7FFFFF, 0xFF7FFFFF, 0x4F000000, 0xCF000000, 0x4EFFFFFF, 0x3F000000, 0x3FC00000, 0x40200000, 0xBFC00000, 0x40100000]
paires = [(a, b, r.getrandbits(32)) for a in SPECIAUX for b in SPECIAUX]
for _ in range(2000):
    def tire():
        c = r.random()
        if c < 0.5:
            return struct.unpack("<I", struct.pack("<f", r.uniform(-1e6, 1e6)))[0]
        if c < 0.7:
            return struct.unpack("<I", struct.pack("<f", r.choice([-1, 1]) * r.uniform(0, 5)))[0]
        return r.getrandbits(32)
    paires.append((tire(), tire(), r.choice([r.getrandbits(32), r.randint(0, 100), (-r.randint(0, 2 ** 31)) & M])))
cpu, _, mots = vtx.executer(SRC_F, [len(paires)] + [v for p in paires for v in p], max_pas=50_000_000)
att = [v for a, b, k in paires for v in ref_f(a, b, k)]
noms = ["+", "-", "*", "/", "==", "<", "<=", "racine", "entier", "arrondi", "flottant", "flottant_signe"]
ecarts = [i for i, (x, y) in enumerate(zip(cpu.sortie, att)) if x != y]
print(f"1. Flottants : {len(paires)} paires (400 entre valeurs spéciales), {len(att)} résultats contre numpy float32 : {len(ecarts)} écart(s)")
for i in ecarts[:5]:
    a, b, k = paires[i // 12]
    print(f"   écart {noms[i % 12]} a={a:#010x} b={b:#010x} : vtx {cpu.sortie[i]:#010x}, numpy {att[i]:#010x}")

# --- longs
S64 = lambda v: v - 2 ** 64 if v >= 2 ** 63 else v
U64 = lambda v: v % 2 ** 64


def tdiv(a, b):
    q = abs(a) // abs(b)
    return q if (a < 0) == (b < 0) else -q


def ref_l(a, b, k):
    sa, sb = S64(a), S64(b)
    q = U64(-1) if sb == 0 else U64(tdiv(sa, sb))
    rm = a if sb == 0 else U64(sa - tdiv(sa, sb) * sb)
    out = [U64(sa + sb), U64(sa - sb), U64(sa * sb), q, rm, a & b, a | b, a ^ b, U64(~sa), U64(sa << (k & 63)), U64(sa >> (k & 63))]
    res = []
    for v in out:
        res += [v & M, v >> 32]
    res += [int(sa == sb), int(sa != sb), int(sa < sb), int(sa <= sb), int(sa > sb), int(sa >= sb)]
    for v in (U64(-sa), U64(abs(sa)), U64(min(sa, sb)), U64(max(sa, sb))):
        res += [v & M, v >> 32]
    return res


SRC_L = """
fonction principal() {
    soit n = entrée();
    pour i dans 0..n {
        soit ah = entrée(); soit al = entrée(); soit bh = entrée(); soit bl = entrée(); soit k = entrée();
        soit a = long_de(ah, al);
        soit b = long_de(bh, bl);
        sortie(a + b); sortie(a - b); sortie(a * b); sortie(a / b); sortie(a % b);
        sortie(a & b); sortie(a | b); sortie(a ^ b); sortie(~a); sortie(a << k); sortie(a >> k);
        sortie(a == b); sortie(a != b); sortie(a < b); sortie(a <= b); sortie(a > b); sortie(a >= b);
        sortie(-a); sortie(abs(a)); sortie(min(a, b)); sortie(max(a, b));
    }
}
"""
BORDS = [0, 1, 2, 2 ** 31, 2 ** 32 - 1, 2 ** 32, 2 ** 63 - 1, 2 ** 63, 2 ** 64 - 1, 2 ** 64 - 2, 12345678901234, U64(-12345678901234)]
lp = [(a, b, r.randint(0, 70)) for a in BORDS for b in BORDS]
for _ in range(300):
    a = r.choice([r.getrandbits(64), r.getrandbits(20), U64(-r.getrandbits(40)), r.getrandbits(40)])
    b = r.choice([r.getrandbits(64), r.getrandbits(20) + 1, U64(-r.getrandbits(30) - 1), r.getrandbits(36)])
    lp.append((a, b, r.randint(0, 70)))
ent = [len(lp)] + [v for a, b, k in lp for v in (a >> 32, a & M, b >> 32, b & M, k)]
cpu, _, mots = vtx.executer(SRC_L, ent, max_pas=200_000_000)
att = [v for a, b, k in lp for v in ref_l(a, b, k)]
ec = [i for i, (x, y) in enumerate(zip(cpu.sortie, att)) if x != y]
print(f"\n2. Longs : {len(lp)} paires (144 entre bords : 0, ±1, 2^31, 2^32, 2^63, −2^63…), {len(att)} mots comparés aux entiers de Python : {len(ec)} écart(s) ; {cpu.pas // len(lp):,} instructions par paire (21 opérations)")
for i in ec[:5]:
    print("   écart à l'indice", i % 36, "paire", [hex(v) for v in lp[i // 36][:2]])

# --- programmes typés
PROGS = [
    ("mélange entier et flottant", "fonction principal() { soit x = 1.5; soit y = x * 2 + 1; sortie(entier(y * 100.0)); sortie(entier(7 / 2.0 * 10)); }", [], [400, 35]),
    ("fonctions typées", "fonction moyenne(a: flottant, b: flottant): flottant { retour (a + b) / 2.0; } "
     "fonction principal() { sortie(arrondi(moyenne(3, 4) * 10.0)); sortie(entier(moyenne(-1.5, 0.5) * 100.0)); }", [], [35, (-50) & M]),
    ("flottants négatifs et comparaison", "fonction principal() { soit a = -2.5; soit b = 0.0 - 2.5; sortie(a == b); sortie(a < 1); "
     "sortie(arrondi(a)); sortie(arrondi(3.5)); sortie(entier(-3.9)); sortie(bits(-0.0)); }", [], [1, 1, (-2) & M, 4, (-3) & M, 0x80000000]),
    ("racine et constante", "constante PI = 3.1415927; fonction principal() { sortie(arrondi(racine(2.0) * 10000.0)); sortie(arrondi(PI * 1000.0)); }", [], [14142, 3142]),
    ("long : grandes valeurs", "fonction principal() { soit x = 4000000000L; soit y = x * 3 + 7; sortie(y); soit z: long = 5; sortie(z << 40); sortie(-1L >> 63); }",
     [], [12000000007 & M, 12000000007 >> 32, 0, 5 << 8, M, M]),
    ("long : fonction et boucle", "fonction fact(n): long { soit p: long = 1; pour i dans 1..n + 1 { p = p * i; } retour p; } "
     "fonction principal() { soit f = fact(20); sortie(f); sortie(f / 1000000L); sortie(bas(f % 7L)); }", [],
     [2432902008176640000 & M, 2432902008176640000 >> 32, (2432902008176640000 // 10 ** 6) & M, (2432902008176640000 // 10 ** 6) >> 32, 2432902008176640000 % 7]),
    ("flottant en mémoire", "fonction principal() { @2[0] = 0.25; soit v = comme_flottant(@2[0]) * 8; sortie(arrondi(v)); }", [], [2]),
    ("condition sur flottant et long", "fonction principal() { soit f = 0.0; soit l = 0L; si f { sortie(1); } sinon { sortie(2); } "
     "si l + 1 { sortie(3); } si !f && !l { sortie(4); } }", [], [2, 3, 4]),
    ("min, max, abs flottants", "fonction principal() { sortie(arrondi(min(2.5, -1.0) * 10.0)); sortie(arrondi(max(2, 7.25) * 4.0)); sortie(arrondi(abs(-6.5) * 2.0)); }",
     [], [(-10) & M, 29, 13]),
]
ok = 0
for nom, src, ent, att_ in PROGS:
    try:
        cpu, _, _ = vtx.executer(src, ent)
        bon = cpu.sortie == att_
    except vtx.VtxError as e:
        bon, cpu = False, None
        print("   erreur :", e)
    ok += bon
    if not bon:
        print(f"   ÉCHEC {nom} : {cpu.sortie if cpu else '-'} attendu {att_}")
print(f"\n3. Programmes typés : {ok}/{len(PROGS)}")
ERR = [("reste flottant", "fonction principal() { sortie(entier(1.5 % 2.0)); }", "reste"),
       ("flottant vers entier implicite", "fonction principal() { soit a = 1; a = 2.5; }", "conversion implicite"),
       ("mélange flottant et long", "fonction principal() { soit a = 1.5 + 2L; }", "mélange"),
       ("long en mémoire", "fonction principal() { @2[0] = 5L; }", "deux mots"),
       ("décalage de flottant", "fonction principal() { soit a = 1.5 << 2; }", "décalage"),
       ("arrondi d'entier", "fonction principal() { sortie(arrondi(3)); }", "ne s'applique pas"),
       ("type inconnu", "fonction principal() { soit a: double = 1; }", "type attendu")]
ok = 0
for nom, src, attendu in ERR:
    try:
        vtx.compiler(src)
        print(f"   ÉCHEC {nom} : aucune erreur")
    except vtx.VtxError as e:
        bon = attendu in str(e) and "ligne" in str(e)
        ok += bon
        if not bon:
            print(f"   ÉCHEC {nom} : {e}")
print(f"   erreurs de typage détectées avec un message en français et la ligne : {ok}/{len(ERR)}")
