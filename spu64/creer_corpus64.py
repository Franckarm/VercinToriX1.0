#!/usr/bin/env python3
"""Crée le corpus de conformité du SPU-64 (spu64/corpus64.txt) et ses résultats attendus, calculés par la machine de
référence (spu64/corpus64_attendu.txt) : des programmes aléatoires fixés (graine 640) et les exemples écrits à la main."""
import os
import random
import sys

ici = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ici)
import spu64 as S  # noqa: E402

sys.argv = [sys.argv[0], "0", "640"]
src = open(os.path.join(ici, "test_spu64.py"), encoding="utf-8").read().split("progs = []")[0]
exec(src)
progs = [S.assembler(programme()) for _ in range(500)]
for nom in sorted(os.listdir(os.path.join(ici, "exemples"))):
    if nom.endswith(".s64"):
        progs.append(S.assembler(open(os.path.join(ici, "exemples", nom), encoding="utf-8").read()))
with open(os.path.join(ici, "corpus64.txt"), "w") as f:
    for m in progs:
        f.write(",".join(map(str, m)) + ";\n")
with open(os.path.join(ici, "corpus64_attendu.txt"), "w") as f:
    for m in progs:
        f.write(S.lancer(m, []) + "\n")
print(len(progs), "programmes")
