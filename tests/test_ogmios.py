#!/usr/bin/env python3
"""Ogmios écrit en vtx (ogmios/ogmios.vtx, l'étape 6, premier temps) : l'atelier tourne sur Lugus, dessine dans la toile
et lit le clavier et la souris. Sans écran : « vtx toile128 … --scenario » rejoue des touches image par image, et les
images sont écrites en PNG. On vérifie : les deux compilateurs donnent les mêmes mots ; une édition (flèches, Fin,
caractères accentués, Entrée qui garde le retrait, retour arrière, Suppr, Tab, Début, la souris) puis Ctrl+S donnent le
fichier attendu, fins de ligne \\r\\n gardées ; F5 lance le programme sur une machine fille (vtxc128, exemples rejoués) et
son compte rendu est écrit en bas ; un exemple faux y est dit ; la durée d'une touche, mesurée.

    python3 tests/test_ogmios.py"""
import os
import shutil
import subprocess
import sys
import tempfile
import time

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, racine)
import vtx128  # noqa: E402

vtx128.COMPAT_64 = False
EXE = os.path.join(racine, "vtx-rs", "target", "release", "vtx" + (".exe" if os.name == "nt" else ""))
LUGUS = os.path.join(racine, "vtx-rs", "target", "release", "lugus" + (".exe" if os.name == "nt" else ""))
OGMIOS = os.path.join(racine, "ogmios", "ogmios.vtx")
D = tempfile.mkdtemp(prefix="ogmios-")
echecs = []


def verifier(nom, ok, detail=""):
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok or not detail else " : " + detail), flush=True)
    if not ok:
        echecs.append(nom)


def jouer(fichier, gestes, images=30):
    """Ogmios sur fichier, avec des gestes (image, geste, valeurs…) ; rend la durée"""
    sc = os.path.join(D, "gestes.scenario")
    with open(sc, "w", encoding="utf-8") as f:
        for g in gestes:
            f.write(" ".join(str(x) for x in g) + "\n")
    im = os.path.join(D, "images")
    shutil.rmtree(im, ignore_errors=True)
    t0 = time.time()
    r = subprocess.run([EXE, "toile128", OGMIOS, "--fichier", fichier, "--images", im, "--max", str(images), "--pas",
                        str(images), "--scenario", sc], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=D)
    return time.time() - t0, r


# 1. les deux compilateurs
src = open(OGMIOS, encoding="utf-8").read()
a = vtx128.assembler(vtx128.compiler(src))
r = subprocess.run([LUGUS, "compiler", OGMIOS, os.path.join(D, "o.mots")], capture_output=True, text=True)
b = [int(x) for x in open(os.path.join(D, "o.mots")).read().split(";")[0].split(",") if x] if r.returncode == 0 else None
verifier(f"ogmios.vtx : les mêmes mots par vtx128.py et vtxc128 ({len(a)} mots)", a == b, r.stdout + r.stderr)

# 2. une édition, puis Ctrl+S
ESSAI = ("// un essai pour Ogmios\r\nreaction moyenne(a, b) -> m {\r\n    total = a + b     -> t\r\n    = t / 2           -> m\r\n"
         "}\r\nexemple moyenne(4, 6) == 5\r\nfonction principal() {\r\n    afficher(\"bonjour\");\r\n    sortie(moyenne(10, 20));\r\n}\r\n")
f = os.path.join(D, "essai.vtx")
open(f, "w", encoding="utf-8", newline="").write(ESSAI)
BAS, FIN, DEBUT, GAUCHE, SUPPR = 65576, 65571, 65572, 65573, 65582
gestes = [(1, "touche", BAS), (2, "touche", BAS), (3, "touche", FIN)]
gestes += [(4 + i, "touche", ord(c)) for i, c in enumerate(" // été")]
gestes += [(12, "touche", 13), (13, "touche", ord("x")), (14, "touche", 8), (15, "touche", ord("="))]
gestes += [(16, "touche", 32), (17, "touche", ord("7")), (18, "touche", DEBUT), (19, "touche", 9), (20, "touche", SUPPR),
           (21, "touche", SUPPR), (22, "touche", SUPPR), (23, "touche", SUPPR)]
# la souris : un clic sur la ligne 1, colonne 3 (la gouttière fait 5 colonnes de 6 points, une ligne fait 10 points)
gestes += [(24, "souris", (5 + 3) * 6 + 2, 0 * 10 + 4, 1), (25, "souris", 50, 4, 0), (25, "touche", ord("!")), (26, "touche", 19)]
duree, r = jouer(f, gestes)
attendu = ESSAI.replace("-> t\r\n", "-> t // été\r\n    = 7\r\n", 1).replace("// un", "// !un", 1)
obtenu = open(f, encoding="utf-8", newline="").read()
verifier("une édition puis Ctrl+S : le fichier attendu, fins de ligne \\r\\n gardées", obtenu == attendu,
         repr(obtenu[:200]) + " / " + r.stderr[-200:])

# 3. F5 : la machine fille compile (vtxc128, exemples rejoués) et lance ; le compte rendu vient en bas
open(f, "w", encoding="utf-8", newline="").write(ESSAI)
duree5, r = jouer(f, [(2, "touche", 65652)], images=6)
im = os.path.join(D, "images")
verifier("F5 : la machine fille compile et lance ; son compte rendu (aussi écrit dans la console) : bonjour, 15",
         r.returncode == 0 and os.listdir(im) and r.stdout.splitlines()[:2] == ["bonjour", "sorties : 15"], r.stdout + r.stderr[-300:])
faux = ESSAI.replace("== 5", "== 6")
open(f, "w", encoding="utf-8", newline="").write(faux)
_, r = jouer(f, [(2, "touche", 65652)], images=6)
verifier("un exemple faux : F5 le dit, la compilation s'arrête", "l'exemple « moyenne(4, 6) == 6 » est faux : le côté gauche vaut 5"
         in r.stdout and "sorties" not in r.stdout, r.stdout + r.stderr)

# 4. la durée d'une touche (Ogmios sur son propre texte, 200 fois la flèche du bas)
g = os.path.join(D, "propre.vtx")
shutil.copy(OGMIOS, g)
t_vide, _ = jouer(g, [], images=2)
t_200, _ = jouer(g, [(i + 1, "touche", BAS) for i in range(200)], images=202)
ms = (t_200 - t_vide) / 200 * 1000
print(f"     une touche (le défilement, l'écran redessiné) : {ms:.0f} ms ; F5 complet : {duree5:.2f} s")
verifier("une touche coûte moins de 100 ms (Lugus émulé)", ms < 100, f"{ms:.0f} ms")

print("Ogmios : " + ("tout est conforme" if not echecs else f"{len(echecs)} échec(s)"))
sys.exit(1 if echecs else 0)
