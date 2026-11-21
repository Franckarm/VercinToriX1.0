#!/usr/bin/env python3
"""Le glossaire d'une ligne par mot (0.67, docs/vtx-reactions.md section 73).

Les mots propres à vtx qui paraissent dans les messages de Lugus (molécule, coiffe, cube, ADN…) sont expliqués à la fin,
une ligne chacun, une seule fois : quand les messages vont à la console, ou avec VTX_GLOSSAIRE=1 ; VTX_GLOSSAIRE=0 le tait.
Lus par un tube (les tests), les messages restent tels quels.

    python3 tests/test_glossaire.py"""
import os
import shutil
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
X = ".exe" if os.name == "nt" else ""
LUGUS = os.path.join(racine, "vtx-rs", "target", "release", "lugus" + X)
echecs = 0


def verifier(nom, ok, detail=""):
    global echecs
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok else f" : {detail}"), flush=True)
    echecs += 0 if ok else 1


def lugus(d, *args, glossaire=None):
    env = dict(os.environ)
    env.pop("VTX_GLOSSAIRE", None)
    if glossaire is not None:
        env["VTX_GLOSSAIRE"] = glossaire
    r = subprocess.run([LUGUS, *args], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=d, env=env)
    return r.stderr


d = tempfile.mkdtemp(prefix="vtx-glossaire-")
shutil.copy(os.path.join(racine, "exemples128", "faces.vtx"), d)
lugus(d, "ranger", "faces.vtx")
avec = lugus(d, "cube", "faces.adn", glossaire="1")
sans = lugus(d, "cube", "faces.adn")
tait = lugus(d, "cube", "faces.adn", glossaire="0")
tete = "le glossaire (les mots de ces messages"
verifier("VTX_GLOSSAIRE=1 : le glossaire à la fin, une ligne par mot paru (cube, ADN, coiffe, molécule, faces, étage)",
         tete in avec and all(f"\n  {m} : " in avec for m in ("cube", "ADN", "coiffe", "molécule", "faces", "étage")),
         avec[-800:])
verifier("chaque mot une seule fois, et seulement ceux qui ont paru (ni patrouille ni apoptose ici)",
         avec.count("\n  cube : ") == 1 and "\n  patrouille : " not in avec and "\n  apoptose : " not in avec)
verifier("lus par un tube, ou avec VTX_GLOSSAIRE=0 : les messages tels quels, sans glossaire",
         tete not in sans and tete not in tait and sans == tait and avec.startswith(sans.rstrip("\n")), sans[-300:])
erreur = os.path.join(d, "faute.vtx")
open(erreur, "w", encoding="utf-8").write("fonction principal() {\n    afficher(x);\n}\n")
r = lugus(d, "faute.vtx", glossaire="1")
verifier("un message sans mot propre à vtx : pas de glossaire", tete not in r and "inconnue" in r, r[-300:])
shutil.rmtree(d, ignore_errors=True)
print("le glossaire : " + ("tout est conforme" if echecs == 0 else f"{echecs} écart(s)"))
sys.exit(1 if echecs else 0)
