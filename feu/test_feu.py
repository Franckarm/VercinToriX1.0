#!/usr/bin/env python3
"""Feu de camp en vtx : vérifications.
 1. La scène générée en vtx est identique à la référence Python (somme de contrôle de tous les voxels) — émulateur Python
    en vérification complète, machine Rust sinon.
 2. Parcours des rayons : pour 400 pixels, le voxel plein touché et la face d'entrée sont ceux d'une référence Python en
    flottants 32 bits (mêmes opérations, dans le même ordre).
 3. L'analyse à la demande (ombre quaternaire, état « inconnu » levé au premier passage d'un rayon) donne la même image que
    l'analyse de tout le volume ; aucune normale retenue ne tourne le dos au rayon (les faces ne sont jamais confondues).
 4. Animation : pour chaque image, les 8 paramètres du feu rappelés par la mémoire du cube (6 souvenirs, comme Pégase)
    et le volume complet sont identiques à la référence.
Les parties 2 à 4 demandent la machine Rust (cargo)."""
import importlib.util
import os
import random
import shutil
import subprocess
import sys

import numpy as np

ici = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ici)
import reference  # noqa: E402

spec = importlib.util.spec_from_file_location("vtx", os.path.join(ici, "..", "vtx.py"))
vtx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vtx)
RAPIDE = os.environ.get("VTX_RAPIDE") == "1"
f32 = np.float32

vol, _blocs = reference.scene()
attendu = reference.somme_scene(vol)

cargo = shutil.which("cargo")
exe = None
if cargo:
    rs = os.path.join(ici, "..", "vtx-rs")
    cible = os.environ.get("CARGO_TARGET_DIR") or os.path.join(rs, "target")
    subprocess.run([cargo, "build", "--release", "-q"], cwd=rs, check=True)
    exe = os.path.join(cible, "release", "vtx-spu" + (".exe" if os.name == "nt" else ""))


def lancer(src, entrees):
    mots = vtx.assembler(vtx.compiler(src, dossier=ici))
    f = os.path.join(ici, "_feu.txt")
    with open(f, "w") as h:
        h.write(",".join(map(str, mots)) + ";" + ",".join(map(str, entrees)) + "\n")
    out = subprocess.run([exe, "lancer", f], capture_output=True, text=True, check=True).stdout.split("\n")
    os.remove(f)
    return int(out[0].split()[0]), [int(v) for v in out[1].split(",")] if out[1] else []


# --- 1. scène
essai = 'importer "scene.vtx";\nfonction principal() { construire_scene(); soit s = 0; soit c = 0; ' \
        'pour v dans 0..2097152 { soit w = @1[v]; si w != 0 { s = s * 31 + w + v; c = c + 1; } } sortie(c); sortie(s); }'
if exe and RAPIDE:
    _p, obtenu = lancer(essai, [])
    machine = "machine Rust"
else:
    obtenu = vtx.executer(essai, (), max_pas=500_000_000, dossier=ici)[0].sortie
    machine = "émulateur Python"
print(f"1. Scène ({machine}) : {attendu[0]:,} voxels non vides, somme de contrôle identique à la référence : "
      f"{obtenu == list(attendu)}")
assert obtenu == list(attendu)
if not exe:
    print("2-3. cargo absent : parcours des rayons et rendu non vérifiés")
    sys.exit(0)

# --- 2. parcours des rayons contre une référence en flottants 32 bits
plein = (vol & 255) >= 128
N = 128


def premier_plein(px, py):
    ox, oy, oz = f32(64.0), f32(40.0), f32(0.0) - f32(34.0)
    u = (f32(px) + f32(0.5)) / f32(128.0) - f32(1.0)
    w = f32(1.0) - (f32(py) + f32(0.5)) / f32(128.0)
    fy, fz = f32(0.0) - f32(0.2), f32(0.98)
    fl = np.sqrt(fy * fy + fz * fz)
    fy, fz = fy / fl, fz / fl
    dx = u * f32(0.55)
    dy = fy + w * f32(0.55) * fz
    dz = fz - w * f32(0.55) * fy
    dl = np.sqrt(dx * dx + dy * dy + dz * dz)
    dx, dy, dz = dx / dl, dy / dl, dz / dl
    big = f32(1000000.0)
    inx = f32(1.0) / dx if dx != 0 else big
    iny = f32(1.0) / dy if dy != 0 else big
    inz = f32(1.0) / dz if dz != 0 else big
    ax, bx = (f32(0.0) - ox) * inx, (f32(128.0) - ox) * inx
    ay, by = (f32(0.0) - oy) * iny, (f32(128.0) - oy) * iny
    az, bz = (f32(0.0) - oz) * inz, (f32(128.0) - oz) * inz
    t0 = max(max(min(ax, bx), min(ay, by)), min(az, bz))
    t1 = min(min(max(ax, bx), max(ay, by)), max(az, bz))
    face = 2 if min(az, bz) >= max(min(ax, bx), min(ay, by)) else (1 if min(ay, by) >= min(ax, bx) else 0)
    if not (t1 > t0 and t1 > 0):
        return None
    tc = max(t0, f32(0.0)) + f32(0.0001)
    ix, iy, iz = (min(int(o + d * tc), 127) for o, d in ((ox, dx), (oy, dy), (oz, dz)))
    pas, prochain, delta = [1, 1, 1], [big] * 3, [big] * 3
    for a, (i, o, d, inv) in enumerate(((ix, ox, dx, inx), (iy, oy, dy, iny), (iz, oz, dz, inz))):
        if d > 0:
            prochain[a], delta[a] = (f32(i + 1) - o) * inv, inv
        elif d < 0:
            pas[a], prochain[a], delta[a] = -1, (f32(i) - o) * inv, f32(0.0) - inv
    fs = int((dx, dy, dz)[face] < 0)
    idx = [ix, iy, iz]
    while all(0 <= c < N for c in idx):
        v = (idx[2] * N + idx[1]) * N + idx[0]
        if plein[v]:
            return v, face * 2 + fs
        tx, ty, tz = prochain
        a = 0 if (tx < ty and tx < tz) else (1 if ty < tz else 2)
        prochain[a] = prochain[a] + delta[a]
        idx[a] += pas[a]
        face, fs = a, int((dx, dy, dz)[a] < 0)
    return None


r = random.Random(3)
pixels = [(r.randrange(256), r.randrange(256)) for _ in range(100 if RAPIDE else 400)]
src = open(os.path.join(ici, "feu.vtx"), encoding="utf-8").read()
_p, sortie = lancer(src, [3, 0, 0, 0, len(pixels)] + [c for p in pixels for c in p])
bons = touches = 0
for k, (px, py) in enumerate(pixels):
    v, fc = sortie[2 * k], sortie[2 * k + 1]
    if v == 0xFFFFFFFF:
        continue
    touches += 1
    bons += premier_plein(px, py) == (v, fc)
print(f"2. Parcours des rayons : {touches} pixels qui touchent un voxel plein sur {len(pixels)} ; voxel et face d'entrée "
      f"identiques à la référence en flottants 32 bits : {bons}/{touches}")
assert bons == touches and touches > len(pixels) // 3

# --- 3. analyse à la demande contre analyse complète
p1, s1 = lancer(src, [1, 0, 256, 0])
p2, s2 = lancer(src, [2, 0, 256, 0])
print(f"3. Image 256 × 256 : analyse à la demande {s1[1]:,} voxels analysés sur 2 097 152, {p1:,} instructions ; "
      f"analyse de tout le volume {p2:,} instructions ; images identiques : {s1[0] == s2[0]} ; normales tournées vers "
      f"le rayon : {s1[2]}")
assert s1[0] == s2[0] and s1[2] == 0 and s2[2] == 0

# --- 4. animation par la mémoire du cube
n = 3 if RAPIDE else 8
_p, sortie = lancer(src, [4, n, 0, 2])
bons = 0
for f in range(n):
    p, s = sortie[f * 9:f * 9 + 8], sortie[f * 9 + 8]
    pr = reference.rappeler(reference.requete(f))
    bons += p == pr and s == reference.somme_scene(reference.scene(pr, f)[0])[1]
print(f"4. Animation : {n} images ; paramètres rappelés par la mémoire du cube et volume complet de chaque image "
      f"identiques à la référence : {bons}/{n}")
assert bons == n
