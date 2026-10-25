#!/usr/bin/env python3
"""Fiche des performances de Lugus (le SPU-128) : les programmes des mesures (mesures/src), en C et en Rust pour
référence, et en vtx de quatre façons : forgé pour Lugus (forge/forge128.py), forgé pour le SPU-32 (forge/forge.py),
Lugus émulé (lugus), le SPU-64 émulé (vtx64). Pour mandel, qui calcule en flottants, aussi les autres largeurs : le C en
double et en __float128 (logiciel, libquadmath), Lugus forgé en flottant de 64 bits (1.5D).

Chaque programme est construit d'abord (non chronométré), puis lancé R fois ; on garde la médiane du temps réel,
lancement du processus compris. Le résultat est comparé à celui de Lugus émulé (le même langage : les flottants de
128 bits de Lugus ne donnent pas le même mandel que les flottants de 32 bits du C).

    python3 mesures/mesurer128.py [R]          écrit mesures/mesures-lugus.json"""
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(ICI)
S = os.path.join(ICI, "src")
V = os.path.join(RACINE, "vtx-rs", "target", "release")
R = int(sys.argv[1]) if len(sys.argv) > 1 else 5
BENCH = [("fib", "Fibonacci récursif (appels)"), ("crible", "Crible d'Ératosthène (mémoire)"),
         ("mandel", "Mandelbrot (flottants)"), ("tri", "Tri rapide (mémoire, comparaisons)"),
         ("adn", "Deux brins d'ADN comparés base par base")]
T = tempfile.mkdtemp(prefix="mesures128-")


def lancer(cmd):
    t = time.perf_counter()
    r = subprocess.run(cmd, cwd=T, capture_output=True, text=True, timeout=900)
    d = time.perf_counter() - t
    sortie = [l for l in r.stdout.strip().split("\n") if l]
    return d, (sortie[-1] if sortie else r.stderr.strip()[-80:])


def construire(b):
    c = {}
    src = os.path.join(S, b + ".vtx")
    subprocess.run(["gcc", "-O2", "-o", os.path.join(T, b + ".gcc"), os.path.join(S, b + ".c")], check=True)
    c["C (gcc -O2)"] = ("compilé", [os.path.join(T, b + ".gcc")])
    subprocess.run(["rustc", "-O", "-o", os.path.join(T, b + ".rust"), os.path.join(S, b + ".rs")], check=True,
                   capture_output=True)
    c["Rust (rustc -O)"] = ("compilé", [os.path.join(T, b + ".rust")])
    if b == "crible":
        # le plancher d'un mot de 128 bits : le même Rust, sur un tableau de u128 (16 octets par case, comme Lugus)
        r = open(os.path.join(S, "crible.rs")).read().replace("0u32", "0u128").replace("n: u32", "n: u128")
        open(os.path.join(T, "crible128.rs"), "w").write(r)
        subprocess.run(["rustc", "-O", "-o", os.path.join(T, "crible128.rust"), os.path.join(T, "crible128.rs")],
                       check=True, capture_output=True)
        c["Rust, cases de 128 bits (u128)"] = ("compilé", [os.path.join(T, "crible128.rust")])
    if b == "mandel":
        c_ = open(os.path.join(S, "mandel.c")).read()
        open(os.path.join(T, "mandel_d.c"), "w").write(re.sub(r"(\d)f\b", r"\1", c_.replace("float", "double")))
        open(os.path.join(T, "mandel_q.c"), "w").write(re.sub(r"(\d)f\b", r"\1Q", c_.replace("float", "__float128")))
        subprocess.run(["gcc", "-O2", "-o", os.path.join(T, "mandel_d.gcc"), os.path.join(T, "mandel_d.c")], check=True)
        subprocess.run(["gcc", "-O2", "-o", os.path.join(T, "mandel_q.gcc"), os.path.join(T, "mandel_q.c"), "-lquadmath"],
                       check=True)
        c["C, en double (64 bits, matériel)"] = ("compilé", [os.path.join(T, "mandel_d.gcc")])
        c["C, en __float128 (113 bits, logiciel)"] = ("compilé", [os.path.join(T, "mandel_q.gcc")])
    subprocess.run([sys.executable, os.path.join(RACINE, "forge", "forge128.py"), src, "-o", os.path.join(T, b + ".lugus")],
                   check=True, capture_output=True)
    c["vtx, forgé pour Lugus (forge128 → Rust → natif)"] = ("vtx", [os.path.join(T, b + ".lugus")])
    if b == "mandel":
        v = open(src).read()
        v = re.sub(r"(\d)\.(\d+)", r"\1.\2D", v).replace("flottant(", "flottant_64(")
        open(os.path.join(T, "mandel_d.vtx"), "w").write(v)
        subprocess.run([sys.executable, os.path.join(RACINE, "forge", "forge128.py"), os.path.join(T, "mandel_d.vtx"),
                        "-o", os.path.join(T, "mandel_d.lugus")], check=True, capture_output=True)
        c["vtx, forgé pour Lugus, en flottant de 64 bits (1.5D)"] = ("vtx", [os.path.join(T, "mandel_d.lugus")])
    subprocess.run([sys.executable, os.path.join(RACINE, "forge", "forge.py"), src, "-o", os.path.join(T, b + ".forge")],
                   check=True, capture_output=True)
    c["vtx, forgé pour le SPU-32 (forge → Rust → natif)"] = ("vtx", [os.path.join(T, b + ".forge")])
    subprocess.run([os.path.join(V, "lugus"), "compiler", src, os.path.join(T, b + ".mots128")], check=True,
                   capture_output=True)
    c["vtx, Lugus émulé (lugus)"] = ("vtx", [os.path.join(V, "lugus"), "lancer", os.path.join(T, b + ".mots128")])
    subprocess.run([os.path.join(V, "vtx64"), "compiler", src, os.path.join(T, b + ".mots64")], check=True,
                   capture_output=True)
    c["vtx, SPU-64 émulé (vtx64)"] = ("vtx", [os.path.join(V, "vtx64"), "lancer", os.path.join(T, b + ".mots64")])
    return c


lignes = []
for b, titre in BENCH:
    cmds = construire(b)
    ref = lancer(cmds["vtx, Lugus émulé (lugus)"][1])[1]
    for nom, (famille, cmd) in cmds.items():
        temps, sortie = [], ""
        for _ in range(R):
            d, sortie = lancer(cmd)
            temps.append(d)
        s = statistics.median(temps)
        lignes.append({"programme": b, "titre": titre, "langage": nom, "famille": famille, "secondes": round(s, 4),
                       "resultat": sortie, "meme_resultat": sortie == ref})
        print(f"{b:7s} {nom:58s} {s:8.3f} s  {sortie}{'' if sortie == ref else '  (autre résultat)'}", flush=True)
json.dump(lignes, open(os.path.join(ICI, "mesures-lugus.json"), "w"), ensure_ascii=False, indent=1)
shutil.rmtree(T, ignore_errors=True)
print("-> mesures/mesures-lugus.json")
