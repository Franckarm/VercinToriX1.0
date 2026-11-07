#!/usr/bin/env python3
"""Belenos, le fluide (belenos/) : les deux propagations, A la copie et B le tapis roulant, donnent les mêmes nombres
que la référence en Python (la même arithmétique entière), sur Lugus et forgées ; la masse est gardée au bit près ; les
fichiers vtx sont ceux que fabrique belenos/fabriquer_fluide.py.

    python3 tests/test_fluide.py"""
import os
import subprocess
import sys
import tempfile

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, os.path.join(racine, "belenos"))
import fluide_ref as F  # noqa: E402

echecs = []
lugus = os.path.join(racine, "vtx-rs", "target", "release", "lugus" + (".exe" if os.name == "nt" else ""))


def verifier(nom, ok, detail=""):
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok or not detail else " : " + detail), flush=True)
    if not ok:
        echecs.append(nom)


avant = {v: open(os.path.join(racine, "belenos", f"fluide_{v}.vtx"), encoding="utf-8").read() for v in ("copie", "tapis")}
subprocess.run([sys.executable, os.path.join(racine, "belenos", "fabriquer_fluide.py")], capture_output=True)
apres = {v: open(os.path.join(racine, "belenos", f"fluide_{v}.vtx"), encoding="utf-8").read() for v in ("copie", "tapis")}
verifier("les fichiers vtx sont ceux que fabrique fabriquer_fluide.py", avant == apres)

p = F.depart()
for _ in range(50):
    p = F.pas(p)
masse, emp = F.empreinte(p)
ref = f"{masse},{emp}"
verifier(f"la référence : la masse gardée au bit près ({masse})", masse == F.N * (1 << 24))

d = tempfile.mkdtemp(prefix="fluide-")
for v in ("copie", "tapis"):
    src = os.path.join(racine, "belenos", f"fluide_{v}.vtx")
    r = subprocess.run([lugus, src], capture_output=True, text=True)
    verifier(f"{v}, sur Lugus : les mêmes nombres que la référence", r.stdout.strip() == ref, r.stdout + r.stderr[-200:])
    exe = os.path.join(d, v)
    f = subprocess.run([sys.executable, os.path.join(racine, "forge", "forge128.py"), src, "-o", exe], capture_output=True,
                       text=True)
    if f.returncode == 0:
        r = subprocess.run([exe], capture_output=True, text=True)
        verifier(f"{v}, forgé : les mêmes nombres", r.stdout.strip() == ref, r.stdout)
    else:
        print(f"     ({v} : la forge n'a pas pu construire : {f.stderr[-150:]})")

print("fluide : " + ("tout est conforme" if not echecs else f"{len(echecs)} échec(s)"))
sys.exit(1 if echecs else 0)
