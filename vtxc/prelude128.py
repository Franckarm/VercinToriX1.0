#!/usr/bin/env python3
"""Recopie le prélude de vtx128.py dans vtxc128.vtx (la fonction texte_prelude), mot pour mot.

    python3 vtxc/prelude128.py"""
import os
import sys

ici = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(ici))
import vtx128  # noqa: E402

chemin = os.path.join(ici, "vtxc128.vtx")
src = open(chemin, encoding="utf-8").read()
debut = src.index("fonction texte_prelude() {")
fin = src.index("\n}\n", debut) + 3
lit = vtx128.PRELUDE.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t")
nouveau = 'fonction texte_prelude() {\n    retour "' + lit + '";\n}\n'
if src[debut:fin] != nouveau:
    open(chemin, "w", encoding="utf-8").write(src[:debut] + nouveau + src[fin:])
    print("vtxc128.vtx : prélude recopié")
else:
    print("vtxc128.vtx : prélude déjà à jour")
