#!/usr/bin/env python3
"""flottant_64 au niveau du langage : opérateurs, comparaisons, conversions, mélange de types, fonctions (paramètres,
retours, récursion), constantes, abs/min/max/racine, affichage décimal exact, erreurs de typage. Les résultats sont
calculés à part avec les flottants de Python ; les quatre machines doivent donner les mêmes mots."""
import math
import os
import random
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import machines  # noqa: E402

vtx = machines.vtx
r = random.Random(64)
M = 0xFFFFFFFF
mauvais = 0


def bits(x):
    return 0x7FF8000000000000 if x != x else struct.unpack("<Q", struct.pack("<d", x))[0]


def flt(b):
    return struct.unpack("<d", struct.pack("<Q", b))[0]


def mots(src, optim=True):
    return vtx.assembler(vtx.compiler(src, prelude=True, optim=optim, partition=False))


def verifier(nom, ok, detail=""):
    global mauvais
    print(("  ok  " if ok else "  ÉCART ") + nom + (f" : {detail}" if detail and not ok else ""))
    if not ok:
        mauvais += 1


def sorties(src, entrees, optim=True):
    m = mots(src, optim)
    cpu = vtx.CPU()
    cpu.charger(m)
    cpu.entree.extend(entrees)
    cpu.executer(500_000_000)
    return cpu.sortie, "".join(map(chr, cpu.texte)), m


# ------------------------------------------------------------------ 1. opérateurs et comparaisons contre Python
SRC_OPS = """
fonction principal() {
    soit n = entrée();
    pour i dans 0..n {
        soit lo = entrée(); soit hi = entrée();
        soit x = flottant_64_de(hi, lo);
        lo = entrée(); hi = entrée();
        soit y = flottant_64_de(hi, lo);
        soit s = x + y; sortie(bas(s)); sortie(haut(s));
        s = x - y; sortie(bas(s)); sortie(haut(s));
        s = x * y; sortie(bas(s)); sortie(haut(s));
        s = x / y; sortie(bas(s)); sortie(haut(s));
        s = -x; sortie(bas(s)); sortie(haut(s));
        s = abs(x); sortie(bas(s)); sortie(haut(s));
        s = min(x, y); sortie(bas(s)); sortie(haut(s));
        s = max(x, y); sortie(bas(s)); sortie(haut(s));
        sortie(x == y); sortie(x != y); sortie(x < y); sortie(x <= y); sortie(x > y); sortie(x >= y);
        si x { sortie(1); } sinon { sortie(0); }
        s = x + 1; sortie(bas(s)); sortie(haut(s));
        s = 2.5 * y; sortie(bas(s)); sortie(haut(s));
    }
}
"""
SPEC = [0, 1 << 63, 0x3FF0000000000000, 0xBFF0000000000000, 0x7FF0000000000000, 0xFFF0000000000000, 0x7FF8000000000000, 1,
        0x7FEFFFFFFFFFFFFF, 0x4004000000000000, 0x3FD0000000000000, 0x4330000000000000]


def tire():
    c = r.random()
    if c < 0.5:
        return bits(r.uniform(-1e6, 1e6))
    if c < 0.7:
        return bits(r.choice([-1, 1]) * r.uniform(0, 1) * 10.0 ** r.randint(-300, 300))
    return r.getrandbits(64)


def attendu_ops(a, b):
    x, y = flt(a), flt(b)
    out = []

    def p(v):
        out.extend([bits(v) & M, bits(v) >> 32])

    def sûr(f):
        try:
            return f()
        except ZeroDivisionError:
            return None
    p(x + y)
    p(x - y)
    p(x * y)
    if y == 0:
        p(float("nan") if x == 0 or x != x else math.copysign(math.inf, x) * math.copysign(1.0, y))
    else:
        p(x / y)
    out += [a & M, (a >> 32) ^ 0x80000000]                 # -x : le bit de signe change, NaN compris
    out += [a & M, (a >> 32) & 0x7FFFFFFF]                 # abs(x) : le bit de signe s'efface
    # min(x, y) : y si y < x, sinon x ; max(x, y) : y si x < y, sinon x
    p(y if y < x else x)
    p(y if x < y else x)
    out += [int(x == y), int(x != y), int(x < y), int(x <= y), int(x > y), int(x >= y)]
    out.append(int(not (x == 0)))   # faux pour ±0 ; un NaN est vrai
    p(x + 1.0)
    p(2.5 * y)
    return out


cas = [(a, b) for a in SPEC for b in SPEC] + [(tire(), tire()) for _ in range(400)]
ent = [len(cas)]
att = []
for a, b in cas:
    ent += [a & M, a >> 32, b & M, b >> 32]
    att += attendu_ops(a, b)
for optim in (True, False):
    sort, _, m = sorties(SRC_OPS, ent, optim)
    ec = [i for i, (u, v) in enumerate(zip(sort, att)) if u != v]
    verifier(f"opérateurs et comparaisons contre Python ({len(cas)} cas, optim={optim})", not ec and len(sort) == len(att),
             f"{len(ec)} écart(s), premier au mot {ec[0] if ec else '-'} cas {ec[0] // 30 if ec else '-'}")
res = machines.lancer_toutes([(m, ent)])
verifier("les quatre machines s'accordent sur ce programme", not any(machines.comparer(res).values()), str(machines.comparer(res)))

# ------------------------------------------------------------------ 2. conversions, constantes, mélanges
SRC_CONV = """
constante PI = 3.14159265358979D;
constante MOINS = -2.5D;
fonction demi(x: flottant_64): flottant_64 { retour x / 2; }
fonction somme(a: flottant_64, n, b: flottant_64): flottant_64 { retour a + n + b; }
fonction fact(n): flottant_64 {
    si n <= 1 { retour 1; }
    retour n * fact(n - 1);
}
fonction principal() {
    soit i = entrée();
    soit f: flottant = 1.5;
    soit d = PI;
    sortie(bas(d)); sortie(haut(d));
    d = MOINS; sortie(bas(d)); sortie(haut(d));
    d = i; sortie(bas(d)); sortie(haut(d));            // entier -> flottant_64
    d = f; sortie(bas(d)); sortie(haut(d));            // flottant -> flottant_64
    d = f * 2 + d;                                     // flottant_64 = flottant + flottant_64
    sortie(bas(d)); sortie(haut(d));
    sortie(entier(d)); sortie(arrondi(d)); sortie(flottant(d) == 6.5);
    soit l = long(d * 1000000000000.0D); sortie(bas(l)); sortie(haut(l));
    sortie(bas(arrondi_long(d * 1.0e12D)));
    sortie(bas(flottant_64(l)));
    sortie(bas(flottant_64_signe(0 - 7))); sortie(haut(flottant_64_signe(0 - 7)));
    sortie(bas(demi(5))); sortie(haut(demi(5)));
    sortie(bas(somme(0.5D, 2, 0.25))); sortie(haut(somme(0.5D, 2, 0.25)));
    sortie(bas(fact(20))); sortie(haut(fact(20)));
    sortie(bas(racine(2.0D))); sortie(haut(racine(2.0D)));
    sortie(bas(comme_flottant_64(bits(1.0D)))); sortie(haut(comme_flottant_64(bits(1.0D))));
    afficher(PI); afficher(1.0e22D); afficher(0.1D + 0.2D); afficher(fact(20)); afficher(5.0e-324D);
    afficher(racine(2.0D)); afficher(-0.0D); afficher(1.0D / 3.0D);
}
"""
sort, texte, m = sorties(SRC_CONV, [7])
pi = 3.14159265358979


def deux(v):
    return [bits(v) & M, bits(v) >> 32]


d = 1.5 * 2 + 1.5
attc = (deux(pi) + deux(-2.5) + deux(7.0) + deux(1.5) + deux(d) + [int(d), round(d) & M, 0] + [])
# (flottant(d) == 6.5 : d = 4.5 ici, donc 0)
verifier("constantes, conversions, entier/arrondi", sort[:len(attc) - 1] == attc[:-1] and sort[len(attc) - 1] == 0,
         f"{sort[:len(attc)]} contre {attc}")
reste = sort[len(attc):]
l = int(d * 1e12) & (2 ** 64 - 1)
attr = [l & M, l >> 32, round(d * 1e12) & M] + [bits(float(l if l < 2 ** 63 else l - 2 ** 64)) & M] + deux(-7.0) + deux(2.5) + deux(2.75) + deux(float(math.factorial(20))) \
    + deux(math.sqrt(2)) + deux(1.0)
verifier("long(), arrondi_long(), flottant_64(), fonctions, récursion, racine", reste == attr, f"{reste} contre {attr}")
lignes = texte.split("\n")
attt = ["3.14159265358979", "1.0e22", "0.30000000000000004", "2.43290200817664e18", "5.0e-324", "1.4142135623730951", "-0.0",
        "0.3333333333333333"]
verifier("afficher() : écriture attendue sur des cas choisis", lignes[:len(attt)] == attt, f"{lignes[:len(attt)]} contre {attt}")

# ------------------------------------------------------------------ 2 bis. affichage décimal : aller-retour et chiffres les plus courts
from decimal import Decimal  # noqa: E402
SRC_AFF = """
fonction principal() {
    soit n = entrée();
    pour i dans 0..n {
        soit lo = entrée(); soit hi = entrée();
        afficher(flottant_64_de(hi, lo));
    }
}
"""
vals = [tire() for _ in range(1500)] + [bits(10.0 ** k) for k in range(-30, 31)] + [bits(float(k) / 7) for k in range(1, 60)] \
    + [1, 0x000FFFFFFFFFFFFF, 0x0010000000000000, 0x7FEFFFFFFFFFFFFF, 0x7FF0000000000000, 0xFFF0000000000000, 0x7FF8000000000000]
e2 = [len(vals)]
for b in vals:
    e2 += [b & M, b >> 32]
ligne = machines.lignes_rust([(mots(SRC_AFF), e2)])[0]           # la machine Rust : le calcul décimal exact est long en Python
txt = "".join(map(chr, [int(v) for v in ligne.split("|T:")[1].split(",")]))
ls = txt.strip("\n").split("\n")
mal = 0
for b, t in zip(vals, ls):
    x = flt(b)
    if x != x:
        mal += t not in ("nan", "-nan")
    elif math.isinf(x):
        mal += t != ("inf" if x > 0 else "-inf")
    else:
        mal += not (bits(float(t)) == b and Decimal(t) == Decimal(repr(x)))
verifier(f"afficher() : {len(vals)} valeurs, aller-retour exact et mêmes chiffres que repr() de Python", mal == 0 and len(ls) == len(vals),
         f"{mal} mauvaise(s), {len(ls)} lignes")

# ------------------------------------------------------------------ 3. erreurs de typage
ERREURS = {
    "long + flottant_64": "fonction principal() { soit a: flottant_64 = 1.0D; soit b = 2L; sortie(bas(a + b)); }",
    "reste": "fonction principal() { soit a = 1.0D; sortie(bas(a % a)); }",
    "bit à bit": "fonction principal() { soit a = 1.0D; sortie(bas(a & a)); }",
    "décalage": "fonction principal() { soit a = 1.0D; sortie(bas(a << 1)); }",
    "complément": "fonction principal() { soit a = 1.0D; sortie(bas(~a)); }",
    "vers entier implicite": "fonction principal() { soit a = 1.0D; soit i: entier = 0; i = a; sortie(i); }",
    "flottant_64 vers flottant implicite": "fonction principal() { soit a = 1.0D; soit f = 1.5; f = a; sortie(bas(comme_flottant(f))); }",
    "trop grand": "fonction principal() { soit a = 1.0e309D; sortie(bas(a)); }",
    "champ de structure": "structure P { x }\nfonction principal() { soit a = 1.0D; soit p = P { x: a }; sortie(p.x); }",
}
for nom, src in ERREURS.items():
    try:
        mots(src)
        verifier("erreur attendue : " + nom, False, "compilé sans erreur")
    except vtx.VtxError:
        verifier("erreur attendue : " + nom, True)

print("Tout est conforme." if not mauvais else f"{mauvais} écart(s)")
sys.exit(1 if mauvais else 0)
