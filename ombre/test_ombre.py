#!/usr/bin/env python3
"""Ombre binaire du cube : vérifie ombre.vtx contre une référence Python (numpy) indépendante.
 1. Petit volume (32³) sur l'émulateur Python : ombre fine, ombre grossière et image identiques à la référence, pixel par
    pixel ; les trois modes de rendu donnent la même image.
 2. 15 scènes aléatoires (voxels semés au hasard, alphas autour du seuil) : mêmes résultats dans les trois modes et
    identiques à la référence.
 3. Volumes 64³, 128³ et 256³ sur la machine Rust (si cargo est présent) : sommes de contrôle identiques à la référence
    et coût du rendu dans chaque mode."""
import importlib.util
import os
import random
import shutil
import subprocess
import sys

import numpy as np

RAPIDE = os.environ.get("VTX_RAPIDE") == "1"      # vérification rapide : moins de tirages, pas de grands volumes
ici = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("vtx", os.path.join(ici, "..", "vtx.py"))
vtx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vtx)
M32 = 0xFFFFFFFF
SEUIL = 128
SOURCE = open(os.path.join(ici, "ombre.vtx"), encoding="utf-8").read()


def gabarit(n):
    log = n.bit_length() - 1
    nb = n // 8
    s = SOURCE
    for nom, v in [("N", n), ("LOGN", log), ("NB", nb), ("NMOTS", n ** 3 // 32), ("NG", max(1, nb ** 3 // 32)),
                   ("NPIX", n * n)]:
        debut = s.index(f"constante {nom} = ")
        fin = s.index(";", debut)
        s = s[:debut] + f"constante {nom} = {v}" + s[fin:]
    return s


def somme(mots):
    s = 0
    for w in mots:
        s = (s * 31 + int(w)) & M32
    return s


def reference(n, extra=()):
    vol = np.zeros(n ** 3, dtype=np.uint64)
    sommet, sol = n * 5 // 8, n // 16
    for z in range(n):
        for x in range(n):
            d = abs(x - n // 2) + abs(z - n // 2)
            pente = d * 5 // 8
            h = sol
            if pente < sommet and sommet - pente > sol:
                h = sommet - pente
            bruit = (((x * 73856093) & M32) ^ ((z * 19349663) & M32)) & 3
            h += bruit
            for y in range(h):
                c = 0xDDE3EEFF
                if y > sommet * 55 // 100:
                    c = 0xF4F7FFFF
                elif y > sol + 3:
                    c = (0x7A7068FF + (bruit << 24)) & M32
                vol[(z * n + y) * n + x] = c
    cx, cy, cz, r = n * 3 // 4, n * 11 // 16, n // 4, n // 10
    for z in range(cz - r, cz + r + 1):
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                if (x - cx) ** 2 + (y - cy) ** 2 + (z - cz) ** 2 <= r * r:
                    vol[(z * n + y) * n + x] = 0xC03020FF
    for adr, mot in extra:
        vol[adr] = mot
    plein = (vol & 255) >= SEUIL
    poids = (np.uint64(1) << np.arange(32, dtype=np.uint64))
    ombre = (plein.reshape(-1, 32).astype(np.uint64) * poids).sum(axis=1)
    nb = n // 8
    blocs = plein.reshape(nb, 8, nb, 8, nb, 8).any(axis=(1, 3, 5)).reshape(-1)     # (bz, by, bx)
    if blocs.size < 32:
        blocs = np.concatenate([blocs, np.zeros(32 - blocs.size, dtype=bool)])
    gros = (blocs.reshape(-1, 32).astype(np.uint64) * poids).sum(axis=1)
    # rayons : tous les pixels à la fois, un pas en z à la fois
    py, px = np.divmod(np.arange(n * n, dtype=np.int64), n)
    x = (px << 16) + 32768
    y = ((n - 1 - py) + n // 4) << 16
    dx = (2 * px - n) * 16384 // n
    dy = (n - 2 * py) * 16384 // n - 16384
    touche = np.full(n * n, -1, dtype=np.int64)
    for k in range(n):
        vx, vy = (x + k * dx) >> 16, (y + k * dy) >> 16
        dedans = (vx >= 0) & (vx < n) & (vy >= 0) & (vy < n) & (touche < 0)
        a = np.where(dedans, (k * n + np.clip(vy, 0, n - 1)) * n + np.clip(vx, 0, n - 1), 0)
        neuf = dedans & plein[a]
        touche[neuf] = k
    image = np.zeros(n * n, dtype=np.uint64)
    for i in range(n * n):
        k = touche[i]
        if k < 0:
            p = int(py[i])
            image[i] = ((100 + p * 100 // n) << 24) | ((120 + p * 80 // n) << 16) | (200 << 8) | 255
        else:
            vx, vy = (int(x[i]) + k * int(dx[i])) >> 16, (int(y[i]) + k * int(dy[i])) >> 16
            c = int(vol[(k * n + vy) * n + vx])
            l = 256 - k * 160 // n
            image[i] = ((((c >> 24) * l) >> 8) << 24) | (((((c >> 16) & 255) * l) >> 8) << 16) | \
                       (((((c >> 8) & 255) * l) >> 8) << 8) | 255
    return {"ombre": ombre, "gros": gros, "image": image, "plein": int(plein.sum()), "blocs": int(blocs.sum())}


def entrees(mode, extra=()):
    return [mode, len(extra)] + [v for p in extra for v in p]


SEULEMENT_GRANDS = "--grands" in sys.argv     # pour ne refaire que la partie 3
if not SEULEMENT_GRANDS:
    # --- 1. petit volume, émulateur Python
    n = 32
    src = gabarit(n)
    ref = reference(n)
    attendu = [somme(ref["ombre"]), somme(ref["gros"]), somme(ref["image"])]
    resultats = {}
    for mode in (0, 1, 2):
        cpu, _, _ = vtx.executer(src, entrees(mode + 16), max_pas=100_000_000, dossier=ici)
        resultats[mode] = cpu
    bons = sum(c.sortie[:3] == attendu and c.sortie[3:] == [int(v) for v in ref["image"]] for c in resultats.values())
    print(f"1. Volume {n}³ ({ref['plein']:,} voxels pleins sur {n ** 3:,}, {ref['blocs']} blocs pleins sur {(n // 8) ** 3}) : "
          f"ombre, ombre grossière et image identiques à la référence, pixel par pixel, dans {bons}/3 modes")
    assert bons == 3

    # --- 2. scènes aléatoires
    r = random.Random(2026)
    ok = 0
    N_ALEA = 4 if RAPIDE else 15
    for essai in range(N_ALEA):
        extra = [(r.randrange(n ** 3), (r.getrandbits(24) << 8) | r.choice([0, 1, 127, 128, 129, 255]))
                 for _ in range(r.randint(1, 120))]
        ref = reference(n, extra)
        attendu = [somme(ref["ombre"]), somme(ref["gros"]), somme(ref["image"])]
        sorties = [vtx.executer(src, entrees(mode, extra), max_pas=100_000_000, dossier=ici)[0].sortie for mode in (0, 1, 2)]
        if all(s == attendu for s in sorties):
            ok += 1
        else:
            print("   ÉCHEC scène", essai, sorties, attendu)
            break
    print(f"2. {N_ALEA} scènes aléatoires (voxels semés, alphas 0, 1, 127, 128, 129, 255) : identiques à la référence dans les "
          f"trois modes {ok}/{N_ALEA}")
    assert ok == N_ALEA

# --- 3. grands volumes, machine Rust
cargo = shutil.which("cargo")
if RAPIDE:
    print("3. Grands volumes : sautés en vérification rapide (python verifier.py --complet)")
    sys.exit(0)
if not cargo:
    print("3. cargo absent : grands volumes non essayés")
    sys.exit(0)
rs = os.path.join(ici, "..", "vtx-rs")
cible = os.environ.get("CARGO_TARGET_DIR") or os.path.join(rs, "target")
subprocess.run([cargo, "build", "--release", "-q"], cwd=rs, check=True)
exe = os.path.join(cible, "release", "vtx-spu" + (".exe" if os.name == "nt" else ""))
print("3. Grands volumes sur la machine Rust")
for n in (64, 128, 256):
    src = gabarit(n)
    mots = vtx.assembler(vtx.compiler(src, dossier=ici))
    ref = reference(n)
    attendu = [somme(ref["ombre"]), somme(ref["gros"]), somme(ref["image"])]
    pas = {}
    for mode in (3, 0, 1, 2):
        f = os.path.join(ici, f"_ombre_{n}.txt")
        with open(f, "w") as h:
            h.write(",".join(map(str, mots)) + ";" + ",".join(map(str, entrees(mode))) + "\n")
        out = subprocess.run([exe, "lancer", f], capture_output=True, text=True, check=True).stdout.split("\n")
        os.remove(f)
        pas[mode] = int(out[0].split()[0])
        sorties = [int(v) for v in out[1].split(",")] if out[1] else []
        assert sorties[:2] == attendu[:2] and (mode == 3 or sorties[2] == attendu[2]), (n, mode, sorties, attendu)
    rendu = {m: pas[m] - pas[3] for m in (0, 1, 2)}
    vide = 100 * (1 - ref["plein"] / n ** 3)
    print(f"   {n}³ : {vide:.0f} % de vide, {ref['blocs']:,} blocs pleins sur {(n // 8) ** 3:,} ; ombre {n ** 3 // 32:,} mots ; "
          f"sommes identiques à la référence ; rendu {n}×{n} : volume {rendu[0]:,} instructions, ombre fine "
          f"{rendu[1]:,}, ombre grossière {rendu[2]:,} (gain {rendu[0] / rendu[2]:.2f}) ; construction des ombres "
          f"{pas[3]:,} (génération comprise)")
