#!/usr/bin/env python3
"""Compression du cube par blocs et palettes : vérifie compression.vtx contre une référence Python indépendante.
 1. Volume 32³ sur l'émulateur Python : répertoire et données identiques à la référence (somme de contrôle), formes des
    blocs identiques, et chaque bloc transcrit redonne exactement le volume.
 2. Scènes aléatoires (voxels de couleurs variées semés au hasard, pour obtenir toutes les formes de bloc).
 3. Volumes 64³, 128³ et 256³ sur la machine Rust (si cargo est présent) : mêmes vérifications et taux de compression."""
import importlib.util
import os
import random
import shutil
import subprocess
import sys

RAPIDE = os.environ.get("VTX_RAPIDE") == "1"      # vérification rapide : moins de tirages, pas de grands volumes
ici = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("vtx", os.path.join(ici, "..", "vtx.py"))
vtx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vtx)
M32 = 0xFFFFFFFF
SOURCE = open(os.path.join(ici, "compression.vtx"), encoding="utf-8").read()


def gabarit(n):
    s = SOURCE
    for nom, v in [("N", n), ("NB", n // 8), ("NBLOC", (n // 8) ** 3)]:
        debut = s.index(f"constante {nom} = ")
        fin = s.index(";", debut)
        s = s[:debut] + f"constante {nom} = {v}" + s[fin:]
    return s


def volume(n, extra=()):
    """Même volume que ombre/volume.vtx (montagne, neige, sphère), écrit indépendamment."""
    vol = [0] * n ** 3
    sommet, sol = n * 5 // 8, n // 16
    for z in range(n):
        for x in range(n):
            d = abs(x - n // 2) + abs(z - n // 2)
            pente = d * 5 // 8
            h = sommet - pente if pente < sommet and sommet - pente > sol else sol
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
    return vol


def reference(n, extra=()):
    vol = volume(n, extra)
    nb = n // 8
    rep, donnees, formes = [], [], [0] * 5
    for b in range(nb ** 3):
        bx, by, bz = b % nb, (b // nb) % nb, b // (nb * nb)
        mots = [vol[((bz * 8 + (j >> 6)) * n + by * 8 + ((j >> 3) & 7)) * n + bx * 8 + (j & 7)] for j in range(512)]
        pal = list(dict.fromkeys(mots))
        if len(pal) == 1:
            forme = 0 if pal[0] == 0 else 1
        else:
            forme = 2 if len(pal) <= 4 else 3 if len(pal) <= 16 else 4
        formes[forme] += 1
        rep.append((forme << 28) | len(donnees))
        if forme == 1:
            donnees.append(pal[0])
        elif forme == 2:
            donnees += pal + [0] * (4 - len(pal))
            idx = {c: i for i, c in enumerate(pal)}
            donnees += [sum(idx[mots[w * 16 + q]] << (2 * q) for q in range(16)) for w in range(32)]
        elif forme == 3:
            donnees += pal + [0] * (16 - len(pal))
            idx = {c: i for i, c in enumerate(pal)}
            donnees += [sum(idx[mots[w * 8 + q]] << (4 * q) for q in range(8)) for w in range(64)]
        elif forme == 4:
            donnees += mots
    return rep, donnees, formes, vol


def somme(mots):
    s = 0
    for w in mots:
        s = (s * 31 + w) & M32
    return s


def entrees(extra=()):
    return [len(extra)] + [v for p in extra for v in p]


def attendu(n, extra=()):
    rep, donnees, formes, _vol = reference(n, extra)
    return [len(donnees), somme(rep + donnees)] + formes + [0], len(rep), len(donnees)


SEULEMENT_GRANDS = "--grands" in sys.argv
if not SEULEMENT_GRANDS:
    # --- 1. volume 32³
    n = 32
    src = gabarit(n)
    att, nrep, ndon = attendu(n)
    cpu, _, _ = vtx.executer(src, entrees(), max_pas=300_000_000, dossier=ici)
    print(f"1. Volume {n}³ : {cpu.sortie == att} ; blocs vides {att[2]}, uniformes {att[3]}, 4 couleurs {att[4]}, "
          f"16 couleurs {att[5]}, bruts {att[6]} ; {nrep + ndon:,} mots au lieu de {n ** 3:,} (taux {n ** 3 / (nrep + ndon):.1f}) ; "
          f"blocs transcrits faux : {cpu.sortie[7]}")
    assert cpu.sortie == att, (cpu.sortie, att)

    # --- 2. scènes aléatoires
    r = random.Random(7)
    ok, vues = 0, [0] * 5
    N_ALEA = 3 if RAPIDE else 8
    for essai in range(N_ALEA):
        couleurs = [r.getrandbits(32) for _ in range(r.choice([2, 5, 20]))]
        extra = []
        if essai < 2:                                    # garantir les formes rares : un bloc brut, un bloc uniforme
            b0 = r.randrange((n // 8) ** 3)
            nb0 = n // 8
            x0, y0, z0 = b0 % nb0 * 8, (b0 // nb0) % nb0 * 8, b0 // (nb0 * nb0) * 8
            teintes = [r.getrandbits(32) | 1 for _ in range(40)]
            for j in range(512):
                c0 = teintes[j % 40] if essai == 0 else teintes[0]
                extra.append(((z0 + (j >> 6)) * n * n + (y0 + ((j >> 3) & 7)) * n + x0 + (j & 7), c0))
        for _ in range(r.randint(1, 6)):
            b = r.randrange((n // 8) ** 3)
            nbx = n // 8
            bx, by, bz = b % nbx, (b // nbx) % nbx, b // (nbx * nbx)
            plein = r.random() < 0.3                     # bloc entier d'une seule couleur : forme uniforme
            uni = r.choice(couleurs)
            for k in range(512 if plein else r.choice([1, 40, 512])):
                j = k if plein else r.randrange(512)
                extra.append(((bz * 8 + (j >> 6)) * n * n + (by * 8 + ((j >> 3) & 7)) * n + bx * 8 + (j & 7),
                              uni if plein else r.choice(couleurs + [0])))
        att, _nr, _nd = attendu(n, extra)
        sortie = vtx.executer(src, entrees(extra), max_pas=300_000_000, dossier=ici)[0].sortie
        vues = [v + (a > 0) for v, a in zip(vues, att[2:7])]
        if sortie == att:
            ok += 1
        else:
            print("   ÉCHEC scène", essai, sortie, att)
            break
    print(f"2. {N_ALEA} scènes aléatoires : identiques à la référence et transcription exacte {ok}/{N_ALEA} ; "
          f"scènes contenant chaque forme (vide, uniforme, 4, 16, brut) : {vues}")
    assert ok == N_ALEA and all(vues)

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
    mots = vtx.assembler(vtx.compiler(gabarit(n), dossier=ici))
    att, nrep, ndon = attendu(n)
    f = os.path.join(ici, f"_compression_{n}.txt")
    with open(f, "w") as h:
        h.write(",".join(map(str, mots)) + ";" + ",".join(map(str, entrees())) + "\n")
    out = subprocess.run([exe, "lancer", f], capture_output=True, text=True, check=True).stdout.split("\n")
    os.remove(f)
    sortie = [int(v) for v in out[1].split(",")]
    assert sortie == att, (n, sortie, att)
    print(f"   {n}³ : identique à la référence, transcription exacte ; blocs vides {att[2]:,}, uniformes {att[3]:,}, "
          f"4 couleurs {att[4]:,}, 16 couleurs {att[5]:,}, bruts {att[6]:,} ; {nrep + ndon:,} mots au lieu de {n ** 3:,} "
          f"(taux {n ** 3 / (nrep + ndon):.1f}) ; {out[0]}")
