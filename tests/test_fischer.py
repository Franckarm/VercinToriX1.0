#!/usr/bin/env python3
"""Fischer (chimie/fischer.py) : le fil de Hilbert (chaque case mène à sa voisine, aller et retour exacts), la
signature d'une molécule (la même quels que soient les noms et l'ordre des lignes ; une autre pour une autre molécule),
et le cube des molécules : chaque molécule rangée est retrouvée à sa place par ce qu'elle est.

    python3 tests/test_fischer.py"""
import os
import random
import sys

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, racine)
sys.path.insert(0, os.path.join(racine, "chimie"))
import vtx128  # noqa: E402
import fischer  # noqa: E402

vtx128.COMPAT_64 = False
echecs = []


def verifier(nom, ok, detail=""):
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok or not detail else " : " + detail), flush=True)
    if not ok:
        echecs.append(nom)


# 1. le fil de Hilbert
b = 4
cases, ok = set(), True
prec = None
for h in range(1 << (3 * b)):
    c = fischer.case_du_fil(h, b)
    cases.add(c)
    ok = ok and fischer.rang_sur_le_fil(*c, b=b) == h and (prec is None or sum(abs(x - y) for x, y in zip(c, prec)) == 1)
    prec = c
verifier("le fil de Hilbert (16³) passe une fois par chaque case, toujours d'une case à sa voisine", ok and len(cases) == 4096)
r = random.Random(3)
ok = True
for _ in range(20000):
    h = r.getrandbits(24)
    c = fischer.case_du_fil(h)
    ok = ok and fischer.rang_sur_le_fil(*c) == h
    if h + 1 < 1 << 24:
        ok = ok and sum(abs(x - y) for x, y in zip(c, fischer.case_du_fil(h + 1))) == 1
verifier("le fil de Hilbert (256³) : 20 000 rangs au hasard, aller et retour, voisines", ok)


# 2. la signature : ce qu'est la molécule, sans les noms ni l'ordre des lignes
def sig(src):
    vtx128.REACTIONS.clear()
    vtx128.compiler(src)
    return fischer.signature(vtx128.REACTIONS["principal"])


A = """reaction principal() {
    = 6 -> a
    = 7 -> b
    = a × b -> p
    = a + b -> s
    = afficher(p - s)
}"""
B = """reaction principal() {
    = afficher(produit - somme)
    = x + y -> somme
    = x × y -> produit
    = 7 -> y
    = 6 -> x
}"""
C = A.replace("a × b", "a + b").replace("a + b -> s", "a × b -> s")
D = A.replace("= 6 -> a", "= 5 -> a")
verifier("même molécule, autres noms et autre ordre des lignes : même signature", sig(A) == sig(B))
verifier("une autre molécule (les opérations échangées) : une autre signature", sig(A) != sig(C))
verifier("une valeur écrite changée : une autre molécule, une autre signature", sig(A) != sig(D))

# les contrats et les unités font partie de ce qu'est la molécule
def sig_r(src, nom="f"):
    vtx128.REACTIONS.clear()
    vtx128.compiler(src + "\nfonction principal() { sortie(0); }")
    return fischer.signature(vtx128.REACTIONS[nom])


E = "reaction f(a, b) -> m {\n    = a + b -> s\n    = s / 2 -> m\n}"
E_EXIGE = "reaction f(a, b) -> m {\n    exige b != 0\n    = a + b -> s\n    = s / 2 -> m\n}"
E_EXIGE2 = "reaction f(x, y) -> r {\n    = y / 2 -> r\n    exige y != 0\n    = x + y -> y\n}".replace("= y / 2 -> r", "= t / 2 -> r").replace("= x + y -> y", "= x + y -> t")
E_GARANTIT = "reaction f(a, b) -> m {\n    = a + b -> s\n    = s / 2 -> m\n    garantit m <= s\n}"
verifier("un contrat ajouté : une autre signature", len({sig_r(E), sig_r(E_EXIGE), sig_r(E_GARANTIT)}) == 3)
verifier("le même contrat, autres noms et autre ordre des lignes : la même signature", sig_r(E_EXIGE) == sig_r(E_EXIGE2))
U = "reaction f(d: m, t: s) -> v {\n    = d / t -> v\n}"
U2 = "reaction f(d: m, t: m) -> v {\n    = d / t -> v\n}"
U0 = "reaction f(d, t) -> v {\n    = d / t -> v\n}"
U_KM = "reaction f() -> d {\n    = 2 km -> d\n}"
U_M = "reaction f() -> x {\n    = 2000 m -> x\n}"
U_S = "reaction f() -> x {\n    = 2000 s -> x\n}"
verifier("des mètres par seconde, des mètres par mètre, sans unité : trois signatures", len({sig_r(U), sig_r(U2), sig_r(U0)}) == 3)
verifier("2 km et 2000 m sont la même molécule ; 2000 s une autre", sig_r(U_KM) == sig_r(U_M) != sig_r(U_S))
verifier("sans contrat ni unité, la signature ne change pas (les places déjà rangées restent)", sig(A) == 0xF9D4FE53E55DC934, f"#{sig(A):016X}")

# 3. le cube des molécules : rangées puis retrouvées
res = fischer.essai(5000)
verifier(f"5000 molécules rangées et toutes retrouvées à leur place (ranger : {res['ranger_moyen']} cases regardées en "
         f"moyenne, retrouver : {res['retrouver_moyen']})", res["ranger_moyen"] < 10 and res["retrouver_moyen"] < 10)

print("Fischer : " + ("tout est conforme" if not echecs else f"{len(echecs)} échec(s)"))
sys.exit(1 if echecs else 0)
