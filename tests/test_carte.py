#!/usr/bin/env python3
"""La carte du programme sur la paillasse d'Ogmios : un programme sans réaction (le loto) devient une molécule, une case
par fonction, une liaison par appel ; les vagues sont la profondeur des appels.
    python3 tests/test_carte.py"""
import os
import subprocess
import sys
import tempfile

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
vtx = os.path.join(racine, "vtx-rs", "target", "release", "vtx" + (".exe" if os.name == "nt" else ""))
echecs = []


def verifier(nom, ok, detail=""):
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok else " : " + detail[:300]))
    if not ok:
        echecs.append(nom)


r = subprocess.run([vtx, "paillasse", os.path.join(racine, "exemples", "premiers", "loto.vtx"), "--plan"],
                   capture_output=True, text=True, encoding="utf-8")
o = r.stdout
verifier("le loto : une carte de 14 fonctions en 4 vagues", "La carte du programme : 14 fonctions, 4 vagues" in o, o[-400:])
verifier("un onglet « le programme »", "onglet le programme" in o, o[-400:])
cases = [l for l in o.splitlines() if l.startswith("case ")]
verifier("14 cases", len(cases) == 14, "\n".join(cases))
# principal appelle cinq fonctions : cinq entrées
ligne_p = 1 + next(k for k, l in enumerate(open(os.path.join(racine, "exemples", "premiers", "loto.vtx"), encoding="utf-8"))
                   if l.startswith("fonction principal"))
p = [l for l in cases if l.split()[1] == str(ligne_p)]
verifier("principal : 5 entrées (lire_grille, jouer, lire_chance, montrer_chances, simuler)",
         len(p) == 1 and len(p[0].split("|")[1].split()) == 5, str(p))
# un texte où une fonction s'appelle elle-même : pas de cycle annoncé, la case reste
d = tempfile.mkdtemp()
f = os.path.join(d, "rec.vtx")
open(f, "w", encoding="utf-8").write("fonction fact(n) {\n    si n < 2 { retour 1; }\n    retour n * fact(n - 1);\n}\n"
                                     "fonction principal() {\n    afficher(fact(5));\n}\n")
r = subprocess.run([vtx, "paillasse", f, "--plan"], capture_output=True, text=True, encoding="utf-8")
verifier("une fonction récursive : 2 fonctions, 2 vagues, pas d'erreur", "2 fonctions, 2 vagues" in r.stdout
         and "À corriger" not in r.stdout, r.stdout[-300:])
print("carte : tout est conforme" if not echecs else f"carte : {len(echecs)} échec(s)")
sys.exit(1 if echecs else 0)
