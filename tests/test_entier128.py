#!/usr/bin/env python3
"""entier_128 (quatre mots de 32 bits dans R1, R3, R4, R6) au niveau du langage : opérateurs, comparaisons, conversions,
mélange de types, fonctions (paramètres, retours, récursion), affichage décimal, erreurs de typage. Les résultats sont
calculés à part avec les entiers de Python (complément à deux sur 128 bits) ; les quatre machines doivent s'accorder."""
import math
import os
import random
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import machines  # noqa: E402

vtx = machines.vtx
r = random.Random(128)
M = 0xFFFFFFFF
W = 2 ** 128
mauvais = 0


def signe(x):
    x %= W
    return x - W if x >= W // 2 else x


def mots4(x):
    x %= W
    return [(x >> (32 * k)) & M for k in range(4)]


def verifier(nom, ok, detail=""):
    global mauvais
    print(("  ok  " if ok else "  ÉCART ") + nom + (f" : {detail}" if detail and not ok else ""))
    mauvais += not ok


def mots(src, optim=True):
    return vtx.assembler(vtx.compiler(src, prelude=True, optim=optim, partition=False))


def lancer(src, entrees, optim=True):
    m = mots(src, optim)
    ligne = machines.lignes_rust([(m, entrees)])[0].split("|")
    sor = [int(v) for v in ligne[1].split(",")] if ligne[1] else []
    txt = "".join(map(chr, [int(v) for v in ligne[3][2:].split(",")])) if len(ligne) > 3 and ligne[3].startswith("T:") else ""
    return sor, txt, m


SRC = """
fonction lire_w(): entier_128 {
    soit w0 = entrée(); soit w1 = entrée(); soit w2 = entrée(); soit w3 = entrée();
    retour entier_128_de(long_de(w3, w2), long_de(w1, w0));
}
fonction sortir(x: entier_128) { sortie(x); }
fonction principal() {
    soit n = entrée();
    pour i dans 0..n {
        soit a = lire_w();
        soit b = lire_w();
        soit k = entrée();
        sortir(a + b); sortir(a - b); sortir(a * b);
        sortir(a & b); sortir(a | b); sortir(a ^ b); sortir(~a); sortir(0 - a);
        sortir(a << k); sortir(a >> k);
        si b != 0 { sortir(a / b); sortir(a % b); } sinon { sortir(0); sortir(0); }
        sortie(a == b); sortie(a != b); sortie(a < b); sortie(a <= b); sortie(a > b); sortie(a >= b);
        sortir(abs(a)); sortir(min(a, b)); sortir(max(a, b));
        sortie(bas(bas(a))); sortie(haut(bas(a))); sortie(bas(haut(a))); sortie(haut(haut(a)));
        sortie(bas(long(a))); sortie(haut(long(a)));
        sortie(bas(bas(entier_128(long(b))))); sortie(haut(haut(entier_128(long(b)))));
        si a { sortie(1); } sinon { sortie(0); }
    }
}
"""


def tire():
    c = r.random()
    if c < 0.2:
        return r.getrandbits(r.randint(1, 128))
    if c < 0.4:
        return signe(r.getrandbits(r.randint(1, 127)) * r.choice([-1, 1]))
    if c < 0.55:
        return r.choice([0, 1, -1, 2 ** 127 - 1, -2 ** 127, 2 ** 64, 2 ** 64 - 1, -2 ** 63, 2 ** 63, 2 ** 32, 10 ** 38, -10 ** 38, 3])
    return r.getrandbits(128)


def attendu(a, b, k):
    a, b = signe(a), signe(b)
    out = []

    def p(x):
        out.extend(mots4(x))
    p(a + b)
    p(a - b)
    p(a * b)
    p(a & b)
    p(a | b)
    p(a ^ b)
    p(~a)
    p(-a)
    p(a << (k & 127))
    p(a >> (k & 127))
    if b != 0:
        q = abs(a) // abs(b)
        q = -q if (a < 0) != (b < 0) else q
        p(q)
        p(a - q * b)
    else:
        p(0)
        p(0)
    out += [int(a == b), int(a != b), int(a < b), int(a <= b), int(a > b), int(a >= b)]
    p(abs(a))
    p(b if b < a else a)
    p(b if a < b else a)
    out += mots4(a)
    out += mots4(a)[:2]
    lb = signe_l(b)
    out += mots4(lb)[:1] + [mots4(lb)[3]]
    out.append(int(a != 0))
    return out


def signe_l(x):
    x %= 2 ** 64
    return x - 2 ** 64 if x >= 2 ** 63 else x


cas = [(tire(), tire(), r.randint(0, 200)) for _ in range(300)]
cas += [(2 ** 127, -1, 1), (-2 ** 127, -1, 127), (-2 ** 127, 1, 0), (5, 3, 0), (-5, 3, 1), (5, -3, 2), (-5, -3, 3), (W - 1, 2, 128)]
ent = [len(cas)]
att = []
for a, b, k in cas:
    ent += mots4(a) + mots4(b) + [k]
    att += attendu(a, b, k)
for optim in (True, False):
    sor, _, m = lancer(SRC, ent, optim)
    ec = [i for i, (u, v) in enumerate(zip(sor, att)) if u != v]
    par_cas = len(att) // len(cas)
    verifier(f"opérateurs, comparaisons et conversions contre les entiers de Python ({len(cas)} cas, optim={optim})",
             not ec and len(sor) == len(att), f"{len(ec)} écart(s), premier au mot {ec[0] if ec else '-'} (cas {ec[0] // par_cas if ec else '-'}, "
             f"offset {ec[0] % par_cas if ec else '-'}) ; longueurs {len(sor)}/{len(att)}")
res = machines.lancer_toutes([(m, ent[:1 + 13 * 40])])
res[next(iter(res))]
ent2 = [40] + ent[1:1 + 13 * 40]
res = machines.lancer_toutes([(m, ent2)])
ec = machines.comparer(res)
verifier("les quatre machines s'accordent sur ce programme", not any(ec.values()), str(ec))

# ------------------------------------------------------------------ affichage, conversions vers et depuis flottant_64, fonctions
SRC2 = """
fonction fact(n): entier_128 {
    si n <= 1 { retour 1; }
    retour n * fact(n - 1);
}
fonction fib(n): entier_128 {
    soit a: entier_128 = 0;
    soit b: entier_128 = 1;
    pour i dans 0..n {
        soit t = a + b;
        a = b;
        b = t;
    }
    retour a;
}
fonction somme(a: entier_128, n, b: entier_128): entier_128 { retour a + n + b; }
constante GRAND = 170141183460469231731687303715884105727LL;
constante NEG = -5LL;
fonction principal() {
    afficher(fact(30));
    afficher(fib(150));
    afficher(somme(10LL, 5, -20LL));
    afficher(GRAND);
    afficher(0 - GRAND - 1);
    afficher(NEG);
    afficher(0LL);
    afficher(flottant_64(fact(30)));
    afficher(flottant_64(0 - fact(30)));
    afficher(flottant_64(GRAND));
    afficher(entier_128(1.0e30D));
    afficher(entier_128(-1.0e30D));
    afficher(entier_128(2.5D));
    afficher(entier_128(1.0e40D));
    afficher(entier_128(-1.0e40D));
    afficher(texte(fact(25)));
    soit x: entier_128 = entier_128_signe(0 - 7);
    afficher(x);
    afficher(entier_128(long_signe(0 - 9)));
    afficher(0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFLL);
}
"""
sor, txt, m = lancer(SRC2, [])
f30 = math.factorial(30)
fib = [0, 1]
for _ in range(150):
    fib.append(fib[-1] + fib[-2])


def fl(x):
    x = float(x)
    return repr(x)


def fmt64(x):
    # même écriture que afficher(flottant_64) : repr() de Python, avec « .0 » ou exposant à un chiffre décimal au moins
    t = repr(float(x))
    return t


attl = [str(f30), str(fib[150]), "-5", str(2 ** 127 - 1), str(-2 ** 127), "-5", "0"]
lignes = txt.split("\n")
verifier("afficher() d'entiers de 128 bits, constantes et fonctions", lignes[:7] == attl, f"{lignes[:7]} contre {attl}")
fl30 = float(f30)
suite = lignes[7:]
attf = [None, None, None, str(int(1e30)), str(int(-1e30)), "2", str(2 ** 127 - 1), str(-2 ** 127), str(math.factorial(25)), "-7", "-9",
        "-1"]
bon = len(suite) >= 12
for i, v in enumerate(attf):
    if v is not None and suite[i] != v:
        bon = False
verifier("flottant_64 -> entier_128 (troncature, saturation), texte(), entier_128_signe", bon, f"{suite[:12]} contre {attf}")
# flottant_64(entier_128) : même valeur que Python
fl_ok = True
for i, x in enumerate([f30, -f30, 2 ** 127 - 1]):
    t = suite[i] if i < len(suite) else ""
    try:
        fl_ok &= float(t) == float(x)
    except ValueError:
        fl_ok = False
verifier("entier_128 -> flottant_64 (arrondi au plus proche pair)", fl_ok, str(suite[:3]))

# ------------------------------------------------------------------ conversion entier_128 -> flottant_64 sur de nombreux cas
SRC3 = """
fonction principal() {
    soit n = entrée();
    pour i dans 0..n {
        soit w0 = entrée(); soit w1 = entrée(); soit w2 = entrée(); soit w3 = entrée();
        soit a = entier_128_de(long_de(w3, w2), long_de(w1, w0));
        soit d = flottant_64(a);
        sortie(bas(d)); sortie(haut(d));
        soit b = entier_128(d);
        sortie(b == a);
    }
}
"""
vals = [tire() for _ in range(300)] + [2 ** 63 + 1, 2 ** 64 + 2 ** 11, 2 ** 64 + 2 ** 11 + 1, 2 ** 53 + 1, 2 ** 100 + 2 ** 47, 2 ** 100 + 2 ** 47 + 1,
                                      -2 ** 127, 2 ** 127 - 1, 1, 0, -1]
ent3 = [len(vals)]
for v in vals:
    ent3 += mots4(v)
sor, _, m3 = lancer(SRC3, ent3)
mal = 0
for i, v in enumerate(vals):
    x = float(signe(v))
    got = struct.unpack("<d", struct.pack("<Q", sor[3 * i] | sor[3 * i + 1] << 32))[0]
    mal += got != x
verifier(f"flottant_64(entier_128) contre float(int) de Python ({len(vals)} valeurs, arrondi au plus proche pair)", mal == 0, f"{mal} écart(s)")

# ------------------------------------------------------------------ erreurs de typage
ERREURS = {
    "entier_128 + long": "fonction principal() { soit a: entier_128 = 1; soit b = 2L; sortie(a + b); }",
    "entier_128 + flottant_64": "fonction principal() { soit a: entier_128 = 1; sortie(a + 1.5D); }",
    "entier_128 + flottant": "fonction principal() { soit a: entier_128 = 1; sortie(a + 1.5); }",
    "champ de structure": "structure P { x }\\nfonction principal() { soit a: entier_128 = 1; soit p = P { x: a }; sortie(p.x); }",
    "écriture mémoire": "fonction principal() { soit a: entier_128 = 1; @2[0] = a; }",
    "trop grand": "fonction principal() { soit a = 340282366920938463463374607431768211456LL; sortie(a); }",
    "entier_128_de d'entiers": "fonction principal() { soit a = entier_128_de(1, 2); sortie(a); }",
    "entier_128 d'un flottant": "fonction principal() { soit a = entier_128(1.5); sortie(a); }",
}
for nom, src in ERREURS.items():
    try:
        mots(src.replace("\\n", "\n"))
        verifier("erreur attendue : " + nom, False, "compilé sans erreur")
    except vtx.VtxError:
        verifier("erreur attendue : " + nom, True)

print("Tout est conforme." if not mauvais else f"{mauvais} écart(s)")
sys.exit(1 if mauvais else 0)
