#!/usr/bin/env python3
"""Le duel du binaire et du quaternaire (exemples128/duel.vtx, 0.5zy). Mêmes mots par vtx128.py et vtxc128 ; le binaire
juste, le binaire d'expert et le quaternaire prennent exactement les mêmes décisions (mêmes erreurs, mêmes portes à
vérifier, silences = inconnus, contradictions = variables) ; le binaire naïf se trompe bien plus ; le quaternaire joue
bien moins d'instructions que le binaire juste ; le .exe traduit dit la même chose que Lugus seul. Les rapports
d'instructions sont écrits tels qu'ils sont, y compris quand le binaire d'expert gagne."""
import os
import re
import subprocess
import sys
import tempfile

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, racine)
import vtx128  # noqa: E402

X = ".exe" if os.name == "nt" else ""
BIN = os.path.join(racine, "vtx-rs", "target", "release")
PROG = os.path.join(racine, "exemples128", "duel.vtx")
d = tempfile.mkdtemp()
echecs = 0


def verifier(nom, ok, detail=""):
    global echecs
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok else f" : {detail}"))
    echecs += 0 if ok else 1


src = open(PROG, encoding="utf-8").read()
ref = vtx128.assembler(vtx128.compiler(src, dossier=os.path.dirname(PROG)))
r = subprocess.run([os.path.join(BIN, "lugus" + X), "compiler", PROG, os.path.join(d, "q.mots")], capture_output=True,
                   text=True, encoding="utf-8")
m = [int(x) for x in open(os.path.join(d, "q.mots")).read().split(";")[0].split(",") if x.strip()] if r.returncode == 0 else None
verifier(f"vtx128.py et vtxc128 donnent les mêmes mots ({len(ref)})", m == ref, f"{len(ref)} contre {None if m is None else len(m)}")

o = subprocess.run([os.path.join(BIN, "lugus" + X), PROG], capture_output=True, text=True, encoding="utf-8").stdout
lignes = {l[:2]: l for l in o.splitlines() if re.match(r"^[ABCD]\. ", l)}


def nombres(l):
    return [int(x) for x in re.findall(r"\b\d+\b", l)]


try:
    A, B, C, D = (nombres(lignes[k]) for k in ("A.", "B.", "C.", "D."))
except KeyError:
    verifier("le duel écrit ses quatre lignes", False, o[-600:])
    sys.exit(1)
# A : erreurs, manquées, fausses, 0, instructions ; B, C, D : erreurs, manquées, fausses, à vérifier, silences, contra, instr
verifier("binaire juste, d'expert et quaternaire : les mêmes décisions", B[:6] == C[:6] == D[:6] and B[3] == B[4] + B[5], f"{B} {C} {D}")
verifier("le binaire naïf se trompe au moins cinq fois plus", A[0] >= 5 * max(D[0], 1), f"{A[0]} contre {D[0]}")
verifier("le quaternaire joue au moins cinq fois moins d'instructions que le binaire juste", D[6] * 5 <= B[6], f"{D[6]} contre {B[6]}")
verifier("le quaternaire (64 logiques par mot, boucles fondues) joue moins d'instructions que le binaire d'expert",
         D[6] < C[6], f"{D[6]} contre {C[6]}")
print(f"   instructions : naïf {A[4]:,}, juste {B[6]:,}, expert {C[6]:,}, quaternaire {D[6]:,}")
exe = os.path.join(d, "duel" + X)
subprocess.run([os.path.join(BIN, "vtx" + X), "exe128", PROG, exe], capture_output=True)
env = dict(os.environ, VTX_SANS_PAUSE="1", VTX_CONSOLE="1")
a = subprocess.run([exe], capture_output=True, text=True, encoding="utf-8", env=env, timeout=300).stdout
env["VTX_INTERPRETE"] = "1"
b = subprocess.run([exe], capture_output=True, text=True, encoding="utf-8", env=env, timeout=300).stdout
verifier("le .exe traduit écrit la même chose que Lugus seul", a == b and "D. quaternaire" in a, f"{a[-200:]!r} / {b[-200:]!r}")
print("le duel : " + ("tout est conforme" if echecs == 0 else f"{echecs} échec(s)"))
sys.exit(1 if echecs else 0)
