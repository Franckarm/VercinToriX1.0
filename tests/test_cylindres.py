#!/usr/bin/env python3
"""Les cylindres (forge128 : « en segments » joués sur plusieurs cœurs, un cube par cylindre, fondus mot à mot) : le
programme forgé rend la même sortie que Lugus avec 1, 2 et 3 cylindres ; une boucle dépendante est vue et rejouée dans
l'ordre ; des segments qui écrivent les mêmes mots donnent des mots variables, résolus comme dans l'ordre.

    python3 tests/test_cylindres.py"""
import os
import subprocess
import sys
import tempfile

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
lugus = os.path.join(racine, "vtx-rs", "target", "release", "lugus" + (".exe" if os.name == "nt" else ""))
echecs = []


def verifier(nom, ok, detail=""):
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok or not detail else " : " + detail), flush=True)
    if not ok:
        echecs.append(nom)


d = tempfile.mkdtemp(prefix="cylindres-")
for prog, attendu in ((os.path.join(racine, "exemples128", "cylindres.vtx"), ["pages fondues ; 0 mots variables"]),
                      (os.path.join(ici, "cylindres_dependants.vtx"),
                       ["a lu ce qu'un autre écrivait : rejoué", "mots variables"])):
    nom = os.path.splitext(os.path.basename(prog))[0]
    exe = os.path.join(d, nom + (".exe" if os.name == "nt" else ""))
    f = subprocess.run([sys.executable, os.path.join(racine, "forge", "forge128.py"), prog, "-o", exe], capture_output=True,
                       text=True)
    verifier(f"{nom} : forgé", f.returncode == 0, f.stderr[-500:])
    if f.returncode:
        continue
    ref = subprocess.run([lugus, prog], capture_output=True, text=True, cwd=d).stdout.strip()
    for n in (1, 2, 3):
        env = dict(os.environ, VTX_COEURS=str(n), VTX_CYLINDRES="1")
        r = subprocess.run([exe], capture_output=True, text=True, cwd=d, env=env)
        verifier(f"{nom} sur {n} cylindre(s) : la sortie de Lugus", r.stdout.strip() == ref, f"{r.stdout.strip()} / {ref}")
        if n > 1:
            for a in attendu:
                verifier(f"{nom} sur {n} cylindres : « {a} »", a in r.stderr, r.stderr[-300:])
            if nom == "cylindres_dependants":
                verifier(f"{nom} : 3 mots variables (deux cylindres, deux valeurs)", "3 mots variables" in r.stderr or n > 2,
                         r.stderr[-300:])
print("cylindres : " + ("tout est conforme" if not echecs else f"{len(echecs)} échec(s)"))
sys.exit(1 if echecs else 0)
