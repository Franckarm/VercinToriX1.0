#!/usr/bin/env python3
"""Lugus fait tourner le langage du SPU-64 : chaque programme compilé par vtx64.py (machine SPU-64) et par vtx128.py
(machine Lugus) doit écrire exactement les mêmes sorties et le même texte. Les programmes : la suite de vtx64, les
exemples du SPU-64 et des programmes tirés au hasard (vtxc/hasard64.py : tous les types, les conversions, les
littéraux). Les deux machines Rust (vtx64 et lugus) jouent les programmes.

    python3 tests/test_vtx128_differentiel.py [nombre de programmes au hasard] [graine]"""
import os
import random
import subprocess
import sys
import tempfile

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, racine)
sys.path.insert(0, os.path.join(racine, "vtxc"))
import vtx64 as V64  # noqa: E402
import vtx128 as V128  # noqa: E402
from hasard64 import G  # noqa: E402

V128.SORTIE_DEUX_MOTS = True    # un entier_128 ou un flottant de 128 bits sort en deux mots, comme au SPU-64

N = int(sys.argv[1]) if len(sys.argv) > 1 else 300
GRAINE = int(sys.argv[2]) if len(sys.argv) > 2 else 128
EXT = ".exe" if os.name == "nt" else ""
EXE64 = os.path.join(racine, "vtx-rs", "target", "release", "vtx64" + EXT)
EXE128 = os.path.join(racine, "vtx-rs", "target", "release", "lugus" + EXT)


def jouer(exe, progs):
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        for m, e in progs:
            f.write(",".join(map(str, m)) + ";" + ",".join(map(str, e)) + "\n")
        nom = f.name
    r = subprocess.run([exe, "corpus", nom], capture_output=True, text=True)
    os.unlink(nom)
    return r.stdout.rstrip("\n").split("\n")


def visible(ligne):
    """Ce que le programme montre : les sorties et le texte (ou l'erreur), sans le nombre de pas ni la mémoire."""
    if ligne.startswith("ERREUR"):
        return "ERREUR"
    ch = ligne.split("|")
    return ch[1] + "|" + "".join(c for c in ch[3:] if c.startswith("T:"))


sources = [(nom, src, list(e)) for nom, src, e, _ in V64.TESTS]
for d in ("exemples64",):
    for f in sorted(os.listdir(os.path.join(racine, d))):
        if f.endswith(".vtx"):
            sources.append((f, open(os.path.join(racine, d, f), encoding="utf-8").read(), []))
g = random.Random(GRAINE)
for k in range(N):
    sources.append((f"hasard {k}", G(random.Random(GRAINE * 100003 + k)).programme(), []))

p64, p128, noms, refus = [], [], [], 0
mots64 = mots128 = 0
for nom, src, e in sources:
    try:
        a = V64.assembler(V64.compiler(src))
    except V64.VtxError:
        refus += 1
        try:
            V128.assembler(V128.compiler(src))
            print(f"  ÉCART {nom} : refusé par vtx64, accepté par vtx128")
        except V128.VtxError:
            pass
        continue
    b = V128.assembler(V128.compiler(src))
    p64.append((a, e))
    p128.append((b, e))
    noms.append(nom)
    mots64 += len(a)
    mots128 += len(b)
r64, r128 = jouer(EXE64, p64), jouer(EXE128, p128)
ecarts = [i for i, (x, y) in enumerate(zip(r64, r128)) if visible(x) != visible(y)]
for i in ecarts[:5]:
    print(f"  ÉCART {noms[i]}\n    SPU-64 : {r64[i][:300]}\n    Lugus  : {r128[i][:300]}")
pas64 = sum(int(x.split("|")[0]) for x in r64 if not x.startswith("ERREUR"))
pas128 = sum(int(x.split("|")[0]) for x in r128 if not x.startswith("ERREUR"))
print(f"{len(p64)} programmes ({refus} refusés par les deux compilateurs) : {len(p64) - len(ecarts)} identiques entre le "
      f"SPU-64 et Lugus ; {mots64} mots de 64 bits contre {mots128} mots de 128 bits ; {pas64} pas contre {pas128}")
ok = not ecarts and len(r64) == len(r128) == len(p64)
print("Lugus parle le langage du SPU-64 : conforme." if ok else f"{len(ecarts)} écart(s)")
sys.exit(0 if ok else 1)
