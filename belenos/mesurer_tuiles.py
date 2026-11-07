#!/usr/bin/env python3
"""Les tuiles (C) contre le fluide entier (A la copie, B le tapis roulant) : 128 × 64 cellules, plusieurs tailles de
tuile ; les instructions de Lugus (50 pas) et le temps forgé (488 pas, le meilleur de cinq). Une tuile refait la
collision de sa marge : (tx + 2)(ty + 2) / (tx · ty) cellules calculées par cellule rendue.

    python3 belenos/mesurer_tuiles.py [dossier de travail]"""
import os
import re
import subprocess
import sys
import tempfile
import time

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, ici)
import fabriquer_fluide as F  # noqa: E402

lugus = os.path.join(racine, "vtx-rs", "target", "release", "lugus" + (".exe" if os.name == "nt" else ""))
d = sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp(prefix="tuiles-")
os.makedirs(d, exist_ok=True)
versions = [("A copie", F.copie, 1.0), ("B tapis", F.tapis, 1.0)]
for tx, ty in ((8, 8), (16, 16), (32, 16), (64, 32)):
    versions.append((f"C tuiles {tx}x{ty}", (lambda tx=tx, ty=ty: F.tuiles(tx, ty)), (tx + 2) * (ty + 2) / (tx * ty)))
print(f"{'version':18s} {'calcul':>7s} {'instructions Lugus':>19s} {'forgé':>10s}  résultat")
for nom, fab, surcoût in versions:
    base = nom.split()[1] + ("_" + nom.split()[2] if len(nom.split()) > 2 else "")
    F.regler(128, 64, 50)
    src = os.path.join(d, base + ".vtx")
    open(src, "w", encoding="utf-8").write(fab())
    r = subprocess.run([lugus, src], capture_output=True, text=True, env=dict(os.environ, LUGUS_TEMPS="1"))
    m = re.search(r"([\d  ]+) instructions", r.stderr + r.stdout)
    instr = m.group(1).replace(" ", "").replace(" ", "") if m else "?"
    F.regler(128, 64, 488)
    src2 = os.path.join(d, base + "_488.vtx")
    open(src2, "w", encoding="utf-8").write(fab())
    exe = os.path.join(d, base) + (".exe" if os.name == "nt" else "")
    f = subprocess.run([sys.executable, os.path.join(racine, "forge", "forge128.py"), src2, "-o", exe],
                       capture_output=True, text=True)
    meilleur, sortie = 1e9, "?"
    if f.returncode == 0:
        for _ in range(5):
            t = time.perf_counter()
            o = subprocess.run([exe], capture_output=True, text=True)
            meilleur = min(meilleur, time.perf_counter() - t)
            sortie = o.stdout.strip()
    instr_m = f"{int(instr) / 1e6:.1f} M" if instr.isdigit() else instr
    print(f"{nom:18s} {surcoût:6.2f}× {instr_m:>19s} {meilleur * 1e3:8.1f} ms  {sortie}", flush=True)
