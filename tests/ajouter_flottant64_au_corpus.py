#!/usr/bin/env python3
"""Ajoute au corpus de conformité les programmes flottant_64 : les exemples (exemples/flottant64), un tour de toutes les
instructions D sur des valeurs choisies, et les opérateurs du langage. Les quatre machines doivent s'accorder avant l'ajout.
À lancer une seule fois par jeu de programmes (il ajoute à la fin du corpus)."""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import machines  # noqa: E402

vtx = machines.vtx
racine = machines.racine
M = 0xFFFFFFFF
progs = []


def compiler(src, dossier=None):
    return vtx.assembler(vtx.compiler(src, dossier=dossier))     # prélude, optimisations, partition : comme le corpus


def b(x):
    return struct.unpack("<Q", struct.pack("<d", x))[0]


d = os.path.join(racine, "exemples", "flottant64")
sqrt_ent = [3]
for x in (2.0, 6.25, 0.0):
    sqrt_ent += [b(x) & M, b(x) >> 32]
for nom, ent in (("precision.vtx", []), ("mandelbrot64.vtx", []), ("newton64.vtx", sqrt_ent)):
    progs.append((compiler(open(os.path.join(d, nom), encoding="utf-8").read(), d), ent))

# un tour des instructions D sur des valeurs spéciales (même programme que test_flottant64_machine, 12 valeurs)
sys.argv = [sys.argv[0]]
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_flottant64_machine.py"), encoding="utf-8").read()
asm = src.split('ASM = """')[1].split('"""')[0]
spec = [0, 1 << 63, 0x3FF0000000000000, 0xBFF0000000000000, 0x7FF0000000000000, 0xFFF0000000000000, 0x7FF8000000000000, 1,
        0x7FEFFFFFFFFFFFFF, 0x4004000000000000, 0x43E0000000000000, 0xC3E0000000000000]
cas = [(a, c, (a ^ c) * 3 & (2 ** 64 - 1)) for a in spec for c in spec]
ent = [len(cas)]
for a, c, k in cas:
    ent += [a & M, a >> 32, c & M, c >> 32, k & M, k >> 32]
progs.append((vtx.assembler(asm), ent))

res = machines.ajouter_au_corpus(progs)
print(len(progs), "programmes ajoutés au corpus ; premières lignes :")
for ligne in res:
    print("  ", ligne[:100])
