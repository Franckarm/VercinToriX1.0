#!/usr/bin/env python3
"""Le vocabulaire du prélude (0.5zr) sur les trois machines : chaque compilateur de référence (vtx.py, vtx64.py,
vtx128.py) et son compilateur écrit en vtx (vtxc, vtxc64, vtxc128, embarqués dans vtx, vtx64, lugus) donnent les mêmes
mots pour exemples/premiers/vocabulaire.vtx, et le programme écrit ce qu'on attend."""
import os
import subprocess
import sys
import tempfile

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, racine)
import vtx  # noqa: E402
import vtx64  # noqa: E402
import vtx128  # noqa: E402

X = ".exe" if os.name == "nt" else ""
BIN = os.path.join(racine, "vtx-rs", "target", "release")
PROG = os.path.join(racine, "exemples", "premiers", "vocabulaire.vtx")
src = open(PROG, encoding="utf-8").read()
d = tempfile.mkdtemp()
echecs = 0


def verifier(nom, ok, detail=""):
    global echecs
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok else f" : {detail}"))
    echecs += 0 if ok else 1


def mots_rust(exe, sortie):
    r = subprocess.run([os.path.join(BIN, exe + X), "compiler", PROG, sortie], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        return None
    return [int(x) for x in open(sortie).read().split(";")[0].split(",") if x.strip()]


attendu = ["max 9 min 1 combien 9 2", "tranche 3 9 1  sans doublons 5 3 9 1 ", "[xirotégnicreV] 2",
           "[  7][ab  ][  ok  ]", "1 0 1 0", "3628800 1906884 1 0 12 1594323"]
for nom, mod, exe in (("Senos", vtx, "vtx"), ("Dunon", vtx64, "vtx64"), ("Lugus", vtx128, "lugus")):
    ref = mod.assembler(mod.compiler(src, dossier=os.path.dirname(PROG)))
    m = mots_rust(exe, os.path.join(d, nom + ".mots"))
    verifier(f"{nom} : {mod.__name__}.py et le compilateur en vtx donnent les mêmes mots ({len(ref)})",
             m is not None and m[:len(ref)] == ref and len(m) == len(ref), f"{len(ref)} contre {None if m is None else len(m)}")
    r = subprocess.run([os.path.join(BIN, exe + X), PROG], capture_output=True, text=True, encoding="utf-8")
    lignes = r.stdout.splitlines()
    verifier(f"{nom} : ce que le programme écrit", all(a in lignes for a in attendu), r.stdout[-500:])
    brasse = [l for l in lignes if l.startswith("brassé")]
    verifier(f"{nom} : brasser garde chaque nombre (somme 36)", len(brasse) == 1 and brasse[0].endswith("somme 36"), str(brasse))
    tir = [l for l in lignes if l.startswith("pioché 42 tirage")]
    ok = False
    if tir:
        t = [int(x) for x in tir[0].split()[3:]]
        ok = len(t) == 5 and t == sorted(t) and len(set(t)) == 5 and all(1 <= x <= 49 for x in t)
    verifier(f"{nom} : tirage(5, 1, 49) : cinq numéros différents, rangés", ok, str(tir))
# la dernière fonction du prélude de Lugus se lit aussi (elle prenait la suite du texte avec elle)
f = os.path.join(d, "borne.vtx")
open(f, "w", encoding="utf-8").write("fonction principal() { afficher(borne(5, 1, 3), puissance_entiere(2, 10)); }\n")
r = subprocess.run([os.path.join(BIN, "lugus" + X), f], capture_output=True, text=True, encoding="utf-8")
verifier("Lugus : borne et puissance_entiere (en fin de prélude) se compilent", r.stdout.strip().endswith("3 1024"), r.stdout + r.stderr)
print("vocabulaire : tout est conforme" if echecs == 0 else f"vocabulaire : {echecs} échec(s)")
sys.exit(1 if echecs else 0)
