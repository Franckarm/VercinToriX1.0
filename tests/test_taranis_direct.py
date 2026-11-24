"""0.821 : Taranis, le noyau de la carte : une boucle pleine de divisions (par des constantes, des puissances de deux,
des nombres qui tiennent en 32 bits ou non, signées, par 0 et par -1), jouée au processeur puis sur la carte par
Taranis (VTX_EPISSAGE=rapide) : la même empreinte. Une carte Vulkan est nécessaire (lavapipe ici)."""
import os
import subprocess
import sys
import tempfile

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
with tempfile.TemporaryDirectory() as d:
    exe = os.path.join(d, "div")
    subprocess.run([sys.executable, os.path.join(racine, "forge", "forge128.py"),
                    os.path.join(ici, "taranis_divisions.vtx"), "-o", exe], check=True, capture_output=True)
    env = dict(os.environ)
    env["VTX_CARTE"] = "0"
    cpu = subprocess.run([exe], env=env, capture_output=True, text=True).stdout.strip().splitlines()[-1]
    env["VTX_CARTE"] = "1"
    env["VTX_EPISSAGE"] = "rapide"
    env["VTX_TARANIS"] = "1"
    r = subprocess.run([exe], env=env, capture_output=True, text=True)
    carte = r.stdout.strip().splitlines()[-1]
    par_taranis = "noyau(x)" in r.stderr
    if cpu != carte or not par_taranis:
        print("taranis direct : DIFFÉRENT", cpu, carte, "(Taranis a joué)" if par_taranis else "(Taranis n'a pas joué)")
        print(r.stderr[-2000:])
        sys.exit(1)
print("taranis direct : tout est conforme (" + cpu + ")")
