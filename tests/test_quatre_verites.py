#!/usr/bin/env python3
"""Les quatre vérités (exemples128/quatre_verites.vtx, 0.5zx) : la démonstration visible de la logique de Belnap. Les
deux compilateurs de Lugus (vtx128.py et vtxc128) donnent les mêmes mots ; le programme écrit les tables de fusion et
de et4 justes, et le conseil d'Alésia décide comme il faut pour chaque porte (vrai, faux, inconnu, variable) ; son .exe,
traduit en x86-64, écrit la même chose que Lugus seul."""
import os
import subprocess
import sys
import tempfile

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, racine)
import vtx128  # noqa: E402

X = ".exe" if os.name == "nt" else ""
BIN = os.path.join(racine, "vtx-rs", "target", "release")
PROG = os.path.join(racine, "exemples128", "quatre_verites.vtx")
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

r = subprocess.run([os.path.join(BIN, "lugus" + X), PROG], capture_output=True, text=True, encoding="utf-8")
o = r.stdout
noms = ["inconnu", "faux", "vrai", "variable"]
# la fusion : les preuves s'additionnent (v = v1 ou v2, f = f1 ou f2) ; et4 : v = v1 et v2, f = f1 ou f2
fus = lambda a, b: a | b  # noqa: E731
et = lambda a, b: (a & b & 2) | ((a | b) & 1)  # noqa: E731
lignes = o.splitlines()


def table(titre, op):
    i = next(k for k, l in enumerate(lignes) if l.startswith(titre))
    debut = i + 2 if titre.startswith("=== Rassembler") else i + 1
    for a in range(4):
        mots = lignes[debut + a].split()
        if mots[1:] != [noms[op(a, b)] for b in range(4)]:
            return False
    return True


verifier("la table de fusion : vrai et faux donnent variable, inconnu ne change rien", table("=== Rassembler", fus), o[:900])
verifier("la table de et4", table("=== et4", et), o[:1400])
attendu = {"porte du nord": ("vrai", "remparts"), "porte du sud": ("faux", "tranquille"),
           "porte de l'est": ("inconnu", "éclaireur"), "porte du gué": ("variable", "conseil")}
for p, (v, mot) in attendu.items():
    l = [x for x in lignes if x.startswith(p)]
    verifier(f"{p} : {v}, {mot}", len(l) == 1 and f"-> {v}" in l[0] and mot in l[0], str(l))
verifier("seize fusions d'un coup : 9 contradictions, comme dans la table",
         "9 contradictions sur 16" in o and sum(fus(a, b) == 3 for a in range(4) for b in range(4)) == 9, o[-300:])

exe = os.path.join(d, "quatre_verites" + X)
subprocess.run([os.path.join(BIN, "vtx" + X), "exe128", PROG, exe], capture_output=True)
env = dict(os.environ, VTX_SANS_PAUSE="1", VTX_CONSOLE="1")
a = subprocess.run([exe], capture_output=True, text=True, encoding="utf-8", env=env, timeout=120).stdout
env["VTX_INTERPRETE"] = "1"
b = subprocess.run([exe], capture_output=True, text=True, encoding="utf-8", env=env, timeout=120).stdout
verifier("le .exe traduit écrit la même chose que Lugus seul", a == b and "porte du gué" in a, f"{a[-200:]!r} / {b[-200:]!r}")
print("les quatre vérités : " + ("tout est conforme" if echecs == 0 else f"{echecs} échec(s)"))
sys.exit(1 if echecs else 0)
