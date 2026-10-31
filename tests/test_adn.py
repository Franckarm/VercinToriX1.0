#!/usr/bin/env python3
"""La fiabilité de l'ADN (chimie/adn.py ; docs/vtx-reactions.md, étape 5) : les trois témoins (la signature de chaque
molécule, l'ombre des colonnes entrelacées, les neutrons des frontières) réparent les avaries d'un programme rangé ; ce
qu'ils ne réparent pas est vu (variable), et rien n'est jamais réparé de travers.

    python3 tests/test_adn.py"""
import os
import random
import subprocess
import sys
import tempfile

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, os.path.join(racine, "chimie"))
import adn  # noqa: E402
import rs  # noqa: E402

echecs = []


def verifier(nom, ok, detail=""):
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok or not detail else " : " + detail), flush=True)
    if not ok:
        echecs.append(nom)


# 1. le code de Reed-Solomon : dans sa capacité (2 erreurs + effacements <= 4), toujours juste
g = random.Random(5)
faux = 0
for _ in range(1500):
    msg = [g.randrange(256) for _ in range(g.randrange(5, 251))]
    cw = msg + rs.coder(msg, 4)
    nf = g.randrange(0, 5)
    ne = g.randrange(0, (4 - nf) // 2 + 1)
    pos = g.sample(range(len(cw)), nf + ne)
    ab = list(cw)
    for p in pos:
        ab[p] ^= g.randrange(1, 256)
    faux += rs.decoder(ab, 4, pos[:nf]) != cw
verifier("Reed-Solomon : 1 500 mots de code abîmés dans sa capacité, tous rendus", faux == 0, str(faux))

# 2. les avaries, sur un programme d'environ 2 000 mots et sur un petit
dex = os.path.join(racine, "exemples128")
lignes = []
r = adn.essai([os.path.join(dex, "chute.vtx"), os.path.join(dex, "panel.vtx")], n=40, graine=11, ecrire=lignes.append)
print("\n".join(lignes))
muettes = sum(c["muet"] for c in r.values())
verifier("aucune erreur muette (rien n'est réparé de travers, rien ne passe sans être vu)", muettes == 0, str(muettes))
toutes = ["un bit", "un mot", "un mot effacé", "deux mots échangés", "deux mots d'une molécule", "une rafale de quatre mots",
          "une rafale de huit mots", "un témoin", "un mot et sa signature"]
verifier("chute.vtx (1 929 mots, 5,6 % de témoins) : tout réparé, jusqu'aux rafales de huit mots",
         all(r[("chute.vtx", gnr)]["réparé"] == 40 for gnr in toutes), str({gnr: r[("chute.vtx", gnr)] for gnr in toutes}))
verifier("panel.vtx (89 mots, une seule colonne) : un ou deux mots abîmés, un témoin : réparés",
         all(r[("panel.vtx", gnr)]["réparé"] == 40 for gnr in toutes[:5] + toutes[7:]))
verifier("au-delà de l'ombre (trois mots d'une colonne, seize au hasard) : vu ou réparé, jamais muet",
         all(r[(f, gnr)]["vu"] + r[(f, gnr)]["réparé"] == 40 for f in ("chute.vtx", "panel.vtx")
             for gnr in ("trois mots d'une colonne", "seize mots au hasard")))

# 3. le fichier : ranger, abîmer, transcrire (l'ARN = les mots seuls, comme vtx128.py mots)
d = tempfile.mkdtemp(prefix="adn-")
f_adn = os.path.join(d, "chute.adn")
py = [sys.executable, os.path.join(racine, "chimie", "adn.py")]
subprocess.run(py + ["ranger", os.path.join(dex, "chute.vtx"), f_adn], capture_output=True, text=True, check=True)
mots, molecules, t = adn.lire_adn(f_adn)
abime = list(mots)
for i in (100, 101, 102, 900):
    abime[i] ^= 0xDEADBEEF << (i % 60)
adn.ecrire_adn(f_adn, abime, molecules, t)
s = subprocess.run(py + ["transcrire", f_adn, os.path.join(d, "chute.mots")], capture_output=True, text=True)
arn = [int(x) for x in open(os.path.join(d, "chute.mots")).read().split(";")[0].split(",")] if s.returncode == 0 else []
s2 = subprocess.run(py + ["transcrire", f_adn, os.path.join(d, "chute2.mots")], capture_output=True, text=True)
verifier("ranger, abîmer quatre mots, transcrire : l'ARN est le programme d'origine, l'ADN réparé réécrit",
         arn == mots and "faux (réparé)" in s.stdout and "l'ADN : vrai" in s2.stdout, s.stdout + s.stderr)
print("ADN : " + ("tout est conforme" if not echecs else f"{len(echecs)} échec(s)"))
sys.exit(1 if echecs else 0)
