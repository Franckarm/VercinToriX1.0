#!/usr/bin/env python3
"""Flottants binary64 au niveau de la machine : les 17 instructions DADD à DTOLR sur des valeurs spéciales et tirées au
hasard, contre numpy float64 (référence indépendante), sur les quatre machines (Python, Rust, JavaScript interprété et
traduit). Les mots rendus doivent être identiques bit à bit, NaN compris (tout NaN rendu sous la forme 0x7FF8000000000000)."""
import math
import os
import random
import struct
import sys
import warnings

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import machines  # noqa: E402

vtx = machines.vtx
warnings.filterwarnings("ignore")
M = 0xFFFFFFFF
r = random.Random(64)

ASM = """
    IN R9
boucle:
    IN R1
    IN R4
    IN R2
    IN R5
    IN R3
    IN R6
    DADD R7,R1,R2
    OUT R7
    OUT R10
    DSUB R7,R1,R2
    OUT R7
    OUT R10
    DMUL R7,R1,R2
    OUT R7
    OUT R10
    DDIV R7,R1,R2
    OUT R7
    OUT R10
    DSQRT R7,R1
    OUT R7
    OUT R10
    DEQ R8,R1,R2
    OUT R8
    DLT R8,R1,R2
    OUT R8
    DLE R8,R1,R2
    OUT R8
    ITOD R7,R3
    OUT R7
    OUT R10
    ITODS R7,R3
    OUT R7
    OUT R10
    DTOI R8,R1
    OUT R8
    DROUND R8,R1
    OUT R8
    FTOD R7,R3
    OUT R7
    OUT R10
    DTOF R8,R1
    OUT R8
    LTOD R7,R3
    OUT R7
    OUT R10
    DTOL R7,R1
    OUT R7
    OUT R10
    DTOLR R7,R1
    OUT R7
    OUT R10
    SUBI R9,R9,#1
    JNZ boucle
    HALT
"""


def fv(bits):
    return np.array([bits], dtype=np.uint64).view(np.float64)[0]


def nb(x):
    x = np.float64(x)
    return 0x7FF8000000000000 if np.isnan(x) else int(x.view(np.uint64))


def f32v(w):
    return np.array([w], dtype=np.uint32).view(np.float32)[0]


def sat32(t):
    return 0x7FFFFFFF if t >= 2 ** 31 else 0x80000000 if t < -2 ** 31 else t & M


def sat64(t):
    return 0x7FFFFFFFFFFFFFFF if t >= 2 ** 63 else 0x8000000000000000 if t < -2 ** 63 else t & 0xFFFFFFFFFFFFFFFF


def cut(v):
    return [v & M, (v >> 32) & M]


def ref(a, b, k):
    x, y = fv(a), fv(b)
    out = []
    with np.errstate(all="ignore"):
        for v in (x + y, x - y, x * y, x / y, np.sqrt(x)):
            out += cut(nb(v))
    out += [int(x == y), int(x < y), int(x <= y)]
    klo = k & M
    out += cut(nb(np.float64(klo)))
    out += cut(nb(np.float64(klo - 2 ** 32 if klo >= 2 ** 31 else klo)))
    xf = float(x)
    for rnd in (False, True):
        out.append(0 if xf != xf else (0x7FFFFFFF if xf > 0 else 0x80000000) if math.isinf(xf)
                   else sat32(int(np.rint(xf)) if rnd else math.trunc(xf)))
    with np.errstate(all="ignore"):
        out += cut(nb(np.float64(f32v(klo))))
        out.append(0x7FC00000 if np.isnan(np.float32(x)) else int(np.float32(x).view(np.uint32)))
    n = k - 2 ** 64 if k >= 2 ** 63 else k
    out += cut(nb(np.float64(n)) if abs(n) < 2 ** 53 else nb(np.float64(float(n))))
    for rnd in (False, True):
        out += cut(0 if xf != xf else (0x7FFFFFFFFFFFFFFF if xf > 0 else 0x8000000000000000) if math.isinf(xf)
                   else sat64(int(np.rint(xf)) if rnd else math.trunc(xf)))
    return out


def tire():
    c = r.random()
    if c < 0.4:
        return struct.unpack("<Q", struct.pack("<d", r.uniform(-1e6, 1e6)))[0]
    if c < 0.55:
        return struct.unpack("<Q", struct.pack("<d", r.choice([-1, 1]) * r.uniform(0, 5)))[0]
    if c < 0.65:
        return struct.unpack("<Q", struct.pack("<d", r.choice([-1, 1]) * r.uniform(0, 1) * 10.0 ** r.randint(-30, 30)))[0]
    if c < 0.75:
        return struct.unpack("<Q", struct.pack("<d", float(r.randint(-2 ** 70, 2 ** 70))))[0]
    return r.getrandbits(64)


SPECIAUX = [0, 1 << 63, 0x3FF0000000000000, 0xBFF0000000000000, 0x7FF0000000000000, 0xFFF0000000000000, 0x7FF8000000000000,
            0x7FF4000000000001, 1, 0x800FFFFFFFFFFFFF, 0x7FEFFFFFFFFFFFFF, 0xFFEFFFFFFFFFFFFF, 0x43E0000000000000,
            0xC3E0000000000000, 0x43DFFFFFFFFFFFFF, 0x3FE0000000000000, 0x3FF8000000000000, 0x4004000000000000,
            0xBFF8000000000000, 0x4002000000000000, 0x41DFFFFFFFC00000, 0xC1E0000000000000, 0x4330000000000000,
            0x3FD0000000000000]
cas = [(a, b, r.getrandbits(64)) for a in SPECIAUX for b in SPECIAUX]
for _ in range(1500):
    cas.append((tire(), tire(), r.choice([r.getrandbits(64), r.randint(0, 100), (-r.randint(0, 2 ** 63)) & (2 ** 64 - 1),
                                           struct.unpack("<Q", struct.pack("<d", r.uniform(-1e30, 1e30)))[0] & M | r.getrandbits(32) << 32])))
entrees = [len(cas)]
for a, b, k in cas:
    entrees += [a & M, a >> 32, b & M, b >> 32, k & M, k >> 32]
mots = vtx.assembler(ASM)
att = [v for a, b, k in cas for v in ref(a, b, k)]
# l'une des deux : la machine Python sert de référence aux autres, numpy sert de référence à la machine Python
res = machines.lancer_toutes([(mots, entrees)])
cpu = vtx.CPU()
cpu.charger(mots)
cpu.entree.extend(entrees)
cpu.executer(500_000_000)
ecarts = [i for i, (x, y) in enumerate(zip(cpu.sortie, att)) if x != y]
noms = ["DADD", "DSUB", "DMUL", "DDIV", "DSQRT"] * 1
print(f"1. Machine Python contre numpy float64 : {len(cas)} cas ({len(SPECIAUX) ** 2} entre valeurs spéciales), "
      f"{len(att)} mots rendus : {len(ecarts)} écart(s)")
for i in ecarts[:5]:
    print("   écart au mot", i, "cas", i // 40, [hex(v) for v in cas[i // 40]], hex(cpu.sortie[i]), "attendu", hex(att[i]))
ec = machines.comparer(res)
print("2. Les autres machines contre la machine Python (instructions, sorties, mémoire) :", ec)
mauvais = len(ecarts) + sum(ec.values())
if len(att) != len(cpu.sortie):
    print("   nombre de sorties différent :", len(cpu.sortie), len(att))
    mauvais += 1
print("Tout est conforme." if not mauvais else f"{mauvais} écart(s)")
sys.exit(1 if mauvais else 0)
