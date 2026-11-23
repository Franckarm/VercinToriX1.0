#!/usr/bin/env python3
"""Les cylindres (forge128 : « en segments » joués sur plusieurs cœurs, un cube par cylindre, fondus mot à mot) : le
programme forgé rend la même sortie que Lugus avec 1, 2 et 3 cylindres ; une boucle dépendante est vue et rejouée dans
l'ordre ; des segments qui écrivent les mêmes mots de valeurs différentes donnent des mots variables : rejoués dans
l'ordre (0.73 : les segments sont donnés en alternance, l'ordre des cylindres n'est plus celui des segments).

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
                       ["a lu ce qu'un autre écrivait : rejoué", "mots variables ; deux cylindres ont écrit le même mot"])):
    nom = os.path.splitext(os.path.basename(prog))[0]
    exe = os.path.join(d, nom + (".exe" if os.name == "nt" else ""))
    f = subprocess.run([sys.executable, os.path.join(racine, "forge", "forge128.py"), prog, "-o", exe], capture_output=True,
                       text=True)
    verifier(f"{nom} : forgé", f.returncode == 0, f.stderr[-500:])
    if f.returncode:
        continue
    ref = subprocess.run([lugus, prog], capture_output=True, text=True, cwd=d).stdout.strip()
    # 0.816 : avec une carte graphique, ces boucles iraient à la carte (le mode pages) : ce test-ci est celui des
    # cylindres, ils se jouent sans la carte ; la carte, elle, doit rendre la même sortie
    carte = subprocess.run([exe], capture_output=True, text=True, cwd=d, env=dict(os.environ, VTX_COEURS="2"))
    verifier(f"{nom} avec la carte (s'il y en a une) : la sortie de Lugus", carte.stdout.strip() == ref,
             f"{carte.stdout.strip()} / {ref}")
    for n in (1, 2, 3):
        env = dict(os.environ, VTX_COEURS=str(n), VTX_CYLINDRES="1", VTX_CARTE="0")
        r = subprocess.run([exe], capture_output=True, text=True, cwd=d, env=env)
        verifier(f"{nom} sur {n} cylindre(s) : la sortie de Lugus", r.stdout.strip() == ref, f"{r.stdout.strip()} / {ref}")
        if n > 1:
            for a in attendu:
                verifier(f"{nom} sur {n} cylindres : « {a} »", a in r.stderr, r.stderr[-300:])
            if nom == "cylindres_dependants":
                verifier(f"{nom} : des mots variables (deux cylindres, deux valeurs), rejoués dans l'ordre",
                         "mots variables ; deux cylindres" in r.stderr and "rejoué dans l'ordre" in r.stderr, r.stderr[-300:])
# 0.77 : « en bandes » : les cœurs écrivent directement dans le cube commun ; une promesse non tenue arrête la machine
for nom, attendu_ok in (("bon", True), ("mauvais", False), ("lit", False)):
    prog = os.path.join(ici, "bandes", nom + ".vtx")
    exe = os.path.join(d, "bandes_" + nom + (".exe" if os.name == "nt" else ""))
    f = subprocess.run([sys.executable, os.path.join(racine, "forge", "forge128.py"), prog, "-o", exe], capture_output=True,
                       text=True)
    verifier(f"en bandes, {nom} : forgé", f.returncode == 0, f.stderr[-500:])
    if f.returncode:
        continue
    ref = subprocess.run([lugus, prog], capture_output=True, text=True, cwd=d).stdout.strip()
    un = subprocess.run([exe], capture_output=True, text=True, cwd=d, env=dict(os.environ, VTX_COEURS="1"))
    verifier(f"en bandes, {nom} sur 1 cœur : la sortie de Lugus", un.stdout.strip() == ref, un.stdout + un.stderr)
    r = subprocess.run([exe], capture_output=True, text=True, cwd=d, env=dict(os.environ, VTX_COEURS="3"))
    if attendu_ok:
        verifier(f"en bandes, {nom} sur 3 cœurs : la sortie de Lugus", r.stdout.strip() == ref, r.stdout + r.stderr)
    else:
        verifier(f"en bandes, {nom} sur 3 cœurs : la promesse non tenue arrête la machine et le dit",
                 r.returncode != 0 and "n'a pas tenu sa promesse" in r.stderr, r.stdout + r.stderr)
print("cylindres : " + ("tout est conforme" if not echecs else f"{len(echecs)} échec(s)"))
sys.exit(1 if echecs else 0)
