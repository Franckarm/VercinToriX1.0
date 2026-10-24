#!/usr/bin/env python3
"""Ajoute au corpus de conformité les exemples entier_128 (exemples/entier128). Les quatre machines doivent s'accorder.
À lancer une seule fois (il ajoute à la fin du corpus)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import machines  # noqa: E402

vtx = machines.vtx
d = os.path.join(machines.racine, "exemples", "entier128")
progs = []
for nom in sorted(os.listdir(d)):
    if nom.endswith(".vtx"):
        progs.append((vtx.assembler(vtx.compiler(open(os.path.join(d, nom), encoding="utf-8").read(), dossier=d)), []))
res = machines.ajouter_au_corpus(progs)
print(len(progs), "programmes ajoutés au corpus ; premières lignes :")
for l in res:
    print("  ", l[:100])
