#!/usr/bin/env python3
"""Recopie le prélude de vtx64.py dans vtxc64.vtx (la fonction texte_prelude), mot pour mot.

    python3 vtxc/prelude128.py"""
import os
import sys

ici = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(ici))
import vtx64  # noqa: E402

chemin = os.path.join(ici, "vtxc64.vtx")
src = open(chemin, encoding="utf-8").read()
debut = src.index("fonction texte_prelude() {")
fin = src.index("\n}\n", debut) + 3
lit = vtx64.PRELUDE.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t")
nouveau = 'fonction texte_prelude() {\n    retour "' + lit + '";\n}\n'
if src[debut:fin] != nouveau:
    open(chemin, "w", encoding="utf-8").write(src[:debut] + nouveau + src[fin:])
    print("vtxc64.vtx : prélude recopié")
else:
    print("vtxc64.vtx : prélude déjà à jour")
