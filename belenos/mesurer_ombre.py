#!/usr/bin/env python3
"""L'ombre comme cache : le fluide (le tapis roulant et la copie) forgé sur des grilles de plus en plus grandes, le
temps par cellule et par pas. Tant que les pages du fluide tiennent dans les seize cases (l'ombre noire), le temps reste
le même ; au-delà, elles passent par l'annuaire (l'ombre grise, vtx-rs/src/spu128.rs). Environ quatre millions de
cellules calculées par mesure ; le départ et le compte sont inclus (sensibles sur les grandes grilles, peu de pas).

    python3 belenos/mesurer_ombre.py [dossier de travail]"""
import os
import subprocess
import sys
import tempfile
import time

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, ici)
import fabriquer_fluide as F  # noqa: E402

d = sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp(prefix="ombre-")
os.makedirs(d, exist_ok=True)
for nx, ny in ((128, 64), (256, 256), (512, 512), (1024, 1024)):
    pas = max(2, 4_000_000 // (nx * ny))
    F.regler(nx, ny, pas)
    for v, fab in (("copie", F.copie), ("tapis", F.tapis)):
        src = os.path.join(d, f"{v}_{nx}.vtx")
        open(src, "w", encoding="utf-8").write(fab())
        exe = os.path.join(d, f"{v}_{nx}") + (".exe" if os.name == "nt" else "")
        r = subprocess.run([sys.executable, os.path.join(racine, "forge", "forge128.py"), src, "-o", exe],
                           capture_output=True, text=True)
        if r.returncode:
            print(f"{nx}x{ny} {v} : la forge n'a pas pu construire : {r.stderr[-200:]}")
            continue
        meilleur = 1e9
        for _ in range(5):
            t = time.perf_counter()
            subprocess.run([exe], capture_output=True)
            meilleur = min(meilleur, time.perf_counter() - t)
        pages = (18 if v == "copie" else 9) * nx * ny // 65536
        print(f"{nx:5d} x {ny:<5d} {v}  {pas:4d} pas  {meilleur * 1e3:8.1f} ms  {meilleur * 1e9 / (pas * nx * ny):7.1f} ns par "
              f"cellule  ({max(pages, 1)} pages)", flush=True)
