#!/usr/bin/env python3
"""multiplier_ajouter exact, en un seul arrondi (0.65, docs/vtx-reactions.md section 71).

a · b + c calculé sans arrondi (les mantisses en grands entiers), puis arrondi une seule fois au plus proche, pair au
milieu, comme la machine. Vérifié, au bit près d'une référence en fractions exactes (spu64/qflot.py) : Lugus (128, 64 et
32 bits) et Dunon (64 et 32 bits), tirés au hasard avec les bords (sous-normaux, exposants extrêmes, annulations, milieux
d'arrondi, débordements) ; compilé (Lugus : vtxc128 seul, 0.851) de chaque machine ; les états de Belnap et les
infinis comme a · b + c ; sur les entiers, a · b + c.

    python3 tests/test_fma.py [--complet]"""
import os
import random
import subprocess
import sys
import tempfile

os.environ["PYTHONUTF8"] = "1"
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, racine)
sys.path.insert(0, os.path.join(racine, "spu64"))
import vtx64  # noqa: E402
from qflot import Q32, Q64, Q128  # noqa: E402

X = ".exe" if os.name == "nt" else ""
BIN = os.path.join(racine, "vtx-rs", "target", "release")
LUGUS, DUNON = os.path.join(BIN, "lugus" + X), os.path.join(BIN, "vtx64" + X)
N = 400 if "--complet" in sys.argv else 120
d = tempfile.mkdtemp(prefix="vtx-fma-")
echecs = 0


def verifier(nom, ok, detail=""):
    global echecs
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok else f" : {detail}"), flush=True)
    echecs += 0 if ok else 1


def reference(F, a, b, c):
    if not all(F.est_nombre(x) for x in (a, b, c)) or any(F.est_inf(x) or F.est_zero(x) for x in (a, b, c)):
        return F.add(F.mul(a, b), c)
    v = F.valeur(a) * F.valeur(b) + F.valeur(c)
    return F.signe(0) if v == 0 else F.depuis(v)


def tirer(F, rnd):
    P, E = F.P, F.emax
    s = rnd.choice([1, 2])
    k = rnd.random()
    if k < 0.05:
        e = 0
    elif k < 0.1:
        e = rnd.choice([1, 2, E - 2, E - 1])
    elif k < 0.7:
        e = F.biais + rnd.randint(-20, 20)
    else:
        e = rnd.randint(0, E - 1)
    m = rnd.randint(1, (1 << (P - 2)) - 1) if e == 0 else rnd.randint(1 << (P - 2), (1 << P) - 1)
    if e and rnd.random() < 0.2:
        m = (1 << (P - 2)) | rnd.choice([0, 1, 1 << (P // 3)])
    return (s << (F.taille - 2)) | (e << P) | m


def cas_de(F, graine):
    rnd = random.Random(graine)
    r = []
    for _ in range(N):
        a, b = tirer(F, rnd), tirer(F, rnd)
        if rnd.random() < 0.3:
            c = F.neg(F.mul(a, b)) ^ rnd.choice([0, 1, 2, 3])       # une annulation
            if not F.est_nombre(c) or F.est_inf(c) or F.est_zero(c):
                c = tirer(F, rnd)
        else:
            c = tirer(F, rnd)
        r.append((a, b, c))
    # les états de Belnap, les infinis, les zéros : comme a · b + c
    un = F.depuis(1)
    for sp in (F.INCONNU, F.VARIABLE, F.inf(0), F.inf(1), F.signe(0), F.signe(1)):
        r += [(sp, un, un), (un, sp, un), (un, un, sp)]
    return r


def programme(machine, largeur, cas):
    """le programme qui calcule multiplier_ajouter sur chaque cas et écrit les bits du résultat"""
    if largeur == 128:
        lignes = ", ".join(f"{v >> 64}, {v & (2 ** 64 - 1)}" for t in cas for v in t)
        return ("fonction prendre(t, i): flottant_petuar { retour comme_flottant_petuar(entier_128_de(t[2 * i], "
                "t[2 * i + 1])); }\nfonction principal() {\n    soit t = [" + lignes + "];\n"
                "    pour i dans 0..longueur(t) / 6 {\n        soit r: entier_128 = bits(multiplier_ajouter(prendre(t, 3 * i), "
                "prendre(t, 3 * i + 1), prendre(t, 3 * i + 2)));\n        afficher(haut(r), bas(r));\n    }\n}\n")
    if machine == "lugus" and largeur == 64:
        # sur Lugus, un programme lit les bits d'un flottant de 128 bits : le flottant de 64 bits y passe exactement
        lignes = ", ".join(f"{w >> 64}, {w & (2 ** 64 - 1)}" for t in cas for w in (Q64.vers(Q128, v) for v in t))
        return ("fonction prendre(t, i): flottant_64 { retour flottant_64(comme_flottant_petuar(entier_128_de(t[2 * i], "
                "t[2 * i + 1]))); }\nfonction principal() {\n    soit t = [" + lignes + "];\n"
                "    pour i dans 0..longueur(t) / 6 {\n        soit r = bits(multiplier_ajouter(prendre(t, 3 * i), "
                "prendre(t, 3 * i + 1), prendre(t, 3 * i + 2)));\n        afficher(r);\n    }\n}\n")
    ty, cf = ("flottant_32", "comme_flottant_32") if largeur == 32 else ("flottant", "comme_flottant")
    lignes = ", ".join(str(v) for t in cas for v in t)
    return (f"fonction prendre(t, i): {ty} {{ retour {cf}(t[i]); }}\nfonction principal() {{\n    soit t = [" + lignes
            + "];\n    pour i dans 0..longueur(t) / 3 {\n        soit r = bits(multiplier_ajouter(prendre(t, 3 * i), "
            "prendre(t, 3 * i + 1), prendre(t, 3 * i + 2)));\n        afficher(r);\n    }\n}\n")


def lire(sortie, largeur):
    r = []
    for l in sortie.split("\n"):
        if not l.strip():
            continue
        if largeur == 128:
            h, b = l.split()
            r.append(((int(h) % 2 ** 64) << 64) | (int(b) % 2 ** 64))
        else:
            r.append(int(l) % 2 ** 64)
    return r


for machine, largeur, F, graine in (("lugus", 128, Q128, 1), ("lugus", 64, Q64, 2), ("lugus", 32, Q32, 3),
                                    ("dunon", 64, Q64, 4), ("dunon", 32, Q32, 5)):
    cas = cas_de(F, graine)
    chemin = os.path.join(d, f"fma_{machine}_{largeur}.vtx")
    src = programme(machine, largeur, cas)
    open(chemin, "w", encoding="utf-8").write(src)
    b = LUGUS if machine == "lugus" else DUNON
    # les mots comparés sur un programme court (la référence en Python lit les longues listes en profondeur)
    court = programme(machine, largeur, cas[:12])
    open(os.path.join(d, "court.vtx"), "w", encoding="utf-8").write(court)
    m = None   # 0.851 : sur Lugus, un seul compilateur (vtxc128, lugus)
    if machine != "lugus":
        m = vtx64.assembler(vtx64.compiler(court, dossier=d))
    subprocess.run([b, "compiler", os.path.join(d, "court.vtx"), os.path.join(d, "x.mots")], capture_output=True)
    ml = [int(x) for x in open(os.path.join(d, "x.mots")).read().split(";")[0].split(",") if x.strip()]
    if m is None:
        m = ml
    nom = "Lugus" if machine == "lugus" else "Dunon"
    verifier(f"{nom}, {largeur} bits : compilé (Lugus : vtxc128 seul, 0.851)", m == ml)
    r = subprocess.run([b, chemin], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=d)
    lu = lire(r.stdout, largeur)
    attendu = [reference(F, *t) for t in cas]
    ecarts = sum(1 for x, y in zip(lu, attendu) if x != y)
    deux = sum(1 for (a, bb, c), y in zip(cas, attendu) if F.add(F.mul(a, bb), c) != y)
    verifier(f"{nom}, {largeur} bits : {len(cas)} multiplier_ajouter au bit près de la référence exacte "
             f"(deux arrondis se seraient trompés {deux} fois)", len(lu) == len(cas) and ecarts == 0,
             f"{len(lu)} lus, {ecarts} écarts ; {r.stderr[-300:]}")

# les entiers
src = "fonction principal() {\n    afficher(multiplier_ajouter(3, 4, 5), multiplier_ajouter(7, 0 - 2, 1));\n}\n"
chemin = os.path.join(d, "entiers.vtx")
open(chemin, "w", encoding="utf-8").write(src)
for machine, b in (("Lugus", LUGUS), ("Dunon", DUNON)):
    r = subprocess.run([b, chemin], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=d)
    verifier(f"{machine} : sur les entiers, a · b + c", r.stdout.startswith("17 -13"), r.stdout + r.stderr)

print("multiplier_ajouter : " + ("tout est conforme" if echecs == 0 else f"{echecs} écart(s)"))
sys.exit(1 if echecs else 0)
