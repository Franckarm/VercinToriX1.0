#!/usr/bin/env python3
"""Belenos, le tableau (belenos/auvergne.vtx) : le programme forgé peint l'image et l'écrit lui-même en PNG ; le fichier
est un PNG juste (la signature, les CRC-32 de chaque morceau, le zlib et son Adler-32 relus par Python), de 2048 × 1080
points, et ses points donnent l'empreinte que le programme a sortie. Avec --lugus : Lugus peint la même image, octet
pour octet (environ deux minutes).

    python3 tests/test_tableau.py [--lugus]"""
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
echecs = []


def verifier(nom, ok, detail=""):
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok or not detail else " : " + detail), flush=True)
    if not ok:
        echecs.append(nom)


def lire_png(chemin):
    """(largeur, hauteur, les points 0xRRGGBB) ; une erreur si un CRC ou le zlib est faux"""
    b = open(chemin, "rb").read()
    assert b[:8] == b"\x89PNG\r\n\x1a\n", "signature"
    k, idat, l, h = 8, b"", 0, 0
    while k < len(b):
        n, t = struct.unpack(">I4s", b[k:k + 8])
        donnees = b[k + 8:k + 8 + n]
        assert struct.unpack(">I", b[k + 8 + n:k + 12 + n])[0] == zlib.crc32(t + donnees), f"CRC de {t}"
        if t == b"IHDR":
            l, h = struct.unpack(">II", donnees[:8])
            assert donnees[8:13] == bytes([8, 2, 0, 0, 0]), "format"
        elif t == b"IDAT":
            idat += donnees
        k += 12 + n
    brut = zlib.decompress(idat)                     # vérifie aussi l'Adler-32
    assert len(brut) == h * (1 + 3 * l), "taille"
    points = []
    for y in range(h):
        ligne = brut[y * (1 + 3 * l):(y + 1) * (1 + 3 * l)]
        assert ligne[0] == 0, "filtre"
        points.extend((ligne[1 + 3 * x] << 16) | (ligne[2 + 3 * x] << 8) | ligne[3 + 3 * x] for x in range(l))
    return l, h, points


d = tempfile.mkdtemp(prefix="tableau-")
src = os.path.join(d, "auvergne.vtx")
shutil.copy(os.path.join(racine, "belenos", "auvergne.vtx"), src)
exe = os.path.join(d, "auvergne" + (".exe" if os.name == "nt" else ""))
f = subprocess.run([sys.executable, os.path.join(racine, "forge", "forge128.py"), src, "-o", exe], capture_output=True,
                   text=True)
verifier("le tableau est forgé", f.returncode == 0, f.stderr[-300:])
if f.returncode == 0:
    r = subprocess.run([exe], capture_output=True, text=True, cwd=d)
    png = os.path.join(d, "auvergne.png")
    verifier("le programme forgé écrit auvergne.png", os.path.exists(png), r.stderr[-200:])
    if os.path.exists(png):
        try:
            l, h, points = lire_png(png)
            verifier(f"un PNG juste (CRC, zlib, Adler-32), {l} × {h}", (l, h) == (2048, 1080))
            e = 0
            for c in points:
                e = ((e ^ c) * 1099511628211) & ((1 << 64) - 1)
            verifier("les points donnent l'empreinte sortie par le programme", str(e) == r.stdout.strip(), r.stdout)
        except AssertionError as x:
            verifier("un PNG juste", False, str(x))
        if "--lugus" in sys.argv:
            lugus = os.path.join(racine, "vtx-rs", "target", "release", "lugus" + (".exe" if os.name == "nt" else ""))
            forge_png = open(png, "rb").read()
            os.remove(png)
            r2 = subprocess.run([lugus, src], capture_output=True, text=True, cwd=d)
            verifier("Lugus peint la même image, octet pour octet",
                     os.path.exists(png) and open(png, "rb").read() == forge_png and r2.stdout.strip() == r.stdout.strip())

print("tableau : " + ("tout est conforme" if not echecs else f"{len(echecs)} échec(s)"))
sys.exit(1 if echecs else 0)
