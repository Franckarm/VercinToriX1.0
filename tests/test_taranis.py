#!/usr/bin/env python3
"""Taranis, la sonde : le SPIR-V écrit par taranis/spirv.py est celui que la machine embarque (vtx-rs/taranis_sonde.spv),
il se relit, et, s'il y a un Vulkan (une carte, ou SwiftShader, le Vulkan logiciel livré avec Chromium), la carte rend
les mêmes mots que le processeur. Sans Vulkan, la dernière vérification est sautée (et dite).
    python3 tests/test_taranis.py"""
import glob
import os
import subprocess
import sys
import tempfile

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, os.path.join(racine, "taranis"))
import spirv  # noqa: E402

echecs = []


def verifier(nom, ok, detail=""):
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok or not detail else " : " + detail), flush=True)
    if not ok:
        echecs.append(nom)


b = spirv.noyau_sonde()
ops = spirv.relire(b)
verifier(f"le noyau se relit ({len(ops)} instructions)", len(ops) > 100)
emb = open(os.path.join(racine, "vtx-rs", "taranis_sonde.spv"), "rb").read()
verifier("vtx-rs/taranis_sonde.spv est le noyau que spirv.py écrit", emb == b,
         "refaire : python3 taranis/spirv.py, puis cargo build --release")
exe = os.path.join(racine, "vtx-rs", "target", "release", "taranis" + (".exe" if os.name == "nt" else ""))
env = dict(os.environ)
if os.name != "nt" and "VK_ICD_FILENAMES" not in env:
    icd = sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux64/vk_swiftshader_icd.json"))
    if icd:
        env["VK_ICD_FILENAMES"] = icd[-1]
if not os.path.exists(exe):
    verifier("taranis est construit", False, "cargo build --release dans vtx-rs")
else:
    r = subprocess.run([exe, "262144"], capture_output=True, text=True, env=env, timeout=600)
    sortie = r.stdout + r.stderr
    if "pas de Vulkan" in sortie or "VkResult -9" in sortie or "aucune carte" in sortie:
        print("sauté : pas de Vulkan ici (ni carte, ni SwiftShader)")
    else:
        carte = [l for l in sortie.splitlines() if l.startswith("carte 0")]
        verifier("la carte rend les mêmes mots que le processeur" + (f" ({carte[0][8:]})" if carte else ""),
                 r.returncode == 0 and "les mêmes" in sortie, sortie[-400:])
print("taranis : tout est conforme" if not echecs else f"taranis : {len(echecs)} échec(s)")
sys.exit(1 if echecs else 0)
