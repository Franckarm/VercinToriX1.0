#!/usr/bin/env python3
"""Teste bibliotheque/cube.vtx et adn.vtx (via essai.vtx) contre une référence Python indépendante."""
import importlib.util
import os
import random

ici = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("vtx", os.path.join(ici, "..", "vtx.py"))
vtx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vtx)
MASK = 0xFFFFFFFF
lanes = lambda m: [(m >> 24) & 255, (m >> 16) & 255, (m >> 8) & 255, m & 255]
pack4 = lambda l: (l[0] << 24) | (l[1] << 16) | (l[2] << 8) | l[3]


def ref(m, x):
    L, X = lanes(m), lanes(x)
    mean = (sum(L) + 2) >> 2
    b = (m >> 2) & 3
    s = 24 - (b - 1) * 8
    return [*L, (m & ~(255 << 16) & MASK) | ((x & 255) << 16), (L[0] + L[1] + L[2]) // 3,
            sum((a - c) ** 2 for a, c in zip(L, X)), pack4([(a * 192 + c * 64) >> 8 for a, c in zip(L, X)]),
            pack4([(v + 256 - mean) >> 1 for v in L]), b, m & 1,
            m if (m & 1) == 1 or b == 0 else (m & ~(255 << s) & MASK) | ((x & 255) << s),
            (m & ~15 & MASK) | (2 << 2) | 1, m & ~1 & MASK, m | 1,
            (m & ~1 & MASK) if b == 0 else (m & ~1 & ~(255 << s) & MASK) | ((x & 255) << s)]


r = random.Random(11)
paires = [(0, 0), (MASK, MASK), (0xFF8040C5, 0x102030FF), (0x12345679, 0xABCDEF01), (0x00FF00FD, 0x7F7F7F7F)]
paires += [(r.getrandbits(32), r.getrandbits(32)) for _ in range(295)]
entrees = [len(paires)] + [v for p in paires for v in p]
src = open(os.path.join(ici, "essai.vtx"), encoding="utf-8").read()
cpu, _, mots = vtx.executer(src, entrees, max_pas=20_000_000, dossier=ici)
attendu = [v for m, x in paires for v in ref(m, x)]
ecarts = [i for i, (a, b) in enumerate(zip(cpu.sortie, attendu)) if a != b]
print(f"{len(paires)} paires de mots, {len(attendu)} valeurs comparées ({len(cpu.sortie)} obtenues) : {len(ecarts)} écart(s)")
print(f"programme : {len(mots)} mots ; {cpu.pas / len(paires):,.0f} instructions par paire (16 sorties)")
if ecarts:
    i = ecarts[0]
    print("premier écart : paire", i // 16, "valeur", i % 16, "obtenu", cpu.sortie[i], "attendu", attendu[i])
