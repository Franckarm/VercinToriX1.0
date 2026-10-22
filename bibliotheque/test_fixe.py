#!/usr/bin/env python3
"""Teste fixe.vtx (64 bits par paires de mots, virgule fixe 16.16) contre l'arithmétique entière de Python."""
import importlib.util
import os
import random

ici = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("vtx", os.path.join(ici, "..", "vtx.py"))
vtx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vtx)
M = 0xFFFFFFFF
sg = lambda x: x - (1 << 32) if x >= 1 << 31 else x


def ref(a, b):
    p = a * b
    fm = (sg(a) * sg(b)) >> 16
    if b == 0:
        fd = M
    else:
        neg = (sg(a) < 0) != (sg(b) < 0)
        q = (abs(sg(a)) << 16) // abs(sg(b))
        fd = (0x80000000 if neg else 0x7FFFFFFF) if q >= 1 << 31 else (-q if neg else q)
    s = (a << 32 | b) + (b << 32 | a)
    d = (a << 32 | b) - (b << 32 | a)
    return [p >> 32, p & M, p >> 32, fm & M, fd & M, s & M, (s >> 32) & M, d & M, (d >> 32) & M]


r = random.Random(4)
bords = [0, 1, 2, 65535, 65536, 0x7FFFFFFF, 0x80000000, 0x80000001, M, M - 1, 0x00010000, 0xFFFF0000, 0x00018000]
paires = [(a, b) for a in bords for b in bords] + [(r.getrandbits(32), r.getrandbits(32)) for _ in range(300)]
paires += [(r.getrandbits(20), r.getrandbits(18)) for _ in range(100)] + [((-r.getrandbits(24)) & M, r.getrandbits(20)) for _ in range(100)]
src = open(os.path.join(ici, "essai_fixe.vtx"), encoding="utf-8").read()
cpu, _, mots = vtx.executer(src, [len(paires)] + [v for p in paires for v in p], max_pas=30_000_000, dossier=ici)
att = [v for a, b in paires for v in ref(a, b)]
ecarts = [i for i, (x, y) in enumerate(zip(cpu.sortie, att)) if x != y]
noms = ["mulhi", "mul64 bas", "mul64 haut", "fx_mul", "fx_div", "add64 bas", "add64 haut", "sub64 bas", "sub64 haut"]
print(f"{len(paires)} paires (dont les bords 0, 1, 2^16, 2^31, 2^32 − 1), {len(att)} valeurs comparées : {len(ecarts)} écart(s)")
print(f"programme : {len(mots)} mots ; {cpu.pas / len(paires):,.0f} instructions par paire (9 opérations)")
if ecarts:
    i = ecarts[0]
    a, b = paires[i // 9]
    print("premier écart :", noms[i % 9], f"a={a:#x} b={b:#x} obtenu {cpu.sortie[i]:#x} attendu {att[i]:#x}")
    print("nombre d'écarts par opération :", {noms[k]: sum(1 for j in ecarts if j % 9 == k) for k in range(9) if any(j % 9 == k for j in ecarts)})
