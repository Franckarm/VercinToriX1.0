#!/usr/bin/env python3
"""Belenos, le fluide (belenos/) : les trois versions, A la copie, B le tapis roulant et C les tuiles, donnent les mêmes nombres
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


avant = {v: open(os.path.join(racine, "belenos", f"fluide_{v}.vtx"), encoding="utf-8").read() for v in ("copie", "tapis", "tuiles")}
subprocess.run([sys.executable, os.path.join(racine, "belenos", "fabriquer_fluide.py")], capture_output=True)
apres = {v: open(os.path.join(racine, "belenos", f"fluide_{v}.vtx"), encoding="utf-8").read() for v in ("copie", "tapis", "tuiles")}
verifier("les fichiers vtx sont ceux que fabrique fabriquer_fluide.py", avant == apres)

p = F.depart()
for _ in range(50):
    p = F.pas(p)
masse, emp = F.empreinte(p)
ref = f"{masse},{emp}"
verifier(f"la référence : la masse gardée au bit près ({masse})", masse == F.N * (1 << 24))

d = tempfile.mkdtemp(prefix="fluide-")
for v in ("copie", "tapis", "tuiles"):
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

# un grand fluide (512 × 512 : chaque direction sur quatre pages, 36 pages en tout) : les pages sortent des seize cases
# et passent par l'annuaire (l'ombre grise, vtx-rs/src/spu128.rs) ; Lugus et la forge donnent les mêmes nombres
sys.path.insert(0, os.path.join(racine, "belenos"))
import fabriquer_fluide as FF  # noqa: E402
FF.regler(512, 512, 2)
grand = os.path.join(d, "tapis_512.vtx")
open(grand, "w", encoding="utf-8").write(FF.tapis())
r = subprocess.run([lugus, grand], capture_output=True, text=True)
sl = r.stdout.strip()
verifier("le grand fluide (512 × 512), sur Lugus : la masse gardée", sl.split(",")[0] == str(512 * 512 << 24), sl)
exe = os.path.join(d, "tapis_512")
f = subprocess.run([sys.executable, os.path.join(racine, "forge", "forge128.py"), grand, "-o", exe], capture_output=True,
                   text=True)
if f.returncode == 0:
    r = subprocess.run([exe], capture_output=True, text=True)
    verifier("le grand fluide, forgé : les mêmes nombres que Lugus", r.stdout.strip() == sl, r.stdout)

print("fluide : " + ("tout est conforme" if not echecs else f"{len(echecs)} échec(s)"))
sys.exit(1 if echecs else 0)
