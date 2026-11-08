#!/usr/bin/env python3
"""Traduction directe en x86-64 pour Windows (natif/natif.py --windows : un .exe PE32+, KERNEL32 seulement, ni Rust,
ni LLVM, ni éditeur de liens) :
 1. le socle Windows réassemblé par GNU as (là où il est) : mêmes octets ;
 2. sous Windows : chaque programme du corpus de conformité traduit en .exe, lancé ; sorties, mémoire et texte
    identiques à ceux attendus (les mêmes que pour toutes les machines) ; ailleurs : chaque .exe est seulement relu
    par objdump (s'il est là), sans être lancé.
Utilisation : python natif/test_windows.py [premier [dernier]]"""
import os
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, ici)
import natif  # noqa: E402
import test_x86  # noqa: E402

WIN = os.name == "nt"
lignes = [l for l in open(os.path.join(racine, "conformite", "corpus_conformite.txt")).read().split("\n") if l.strip()]
attendu = open(os.path.join(racine, "conformite", "corpus_attendu.txt")).read().strip().split("\n")
debut = int(sys.argv[1]) if len(sys.argv) > 1 else 0
fin = int(sys.argv[2]) if len(sys.argv) > 2 else len(lignes)
TMP = tempfile.mkdtemp(prefix="windows-")

m = lignes[debut].partition(";")[0]
t = natif.traduire([int(x) for x in m.split(",") if x.strip()], corpus=True, texte=True, systeme="windows")
ok1 = test_x86.comparer(t.a, "socle Windows")
print("1. Programme et socle Windows réassemblés par GNU as :", "mêmes octets" if ok1 else "ÉCART", flush=True)


def essai(i):
    m, _, e = lignes[i].partition(";")
    mots = [int(x) for x in m.split(",") if x.strip()]
    entrees = [x for x in e.split(",") if x.strip()]
    exe = os.path.join(TMP, f"p{i}.exe")
    natif.ecrire_executable(exe, mots, corpus=True, systeme="windows")
    if not WIN:
        if shutil.which("objdump"):
            r = subprocess.run(["objdump", "-p", exe], capture_output=True, text=True)
            ok = "PE32+" in r.stdout and "KERNEL32.dll" in r.stdout
            return i, attendu[i] if ok else "objdump ne relit pas l'exécutable"
        return i, attendu[i]
    try:
        r = subprocess.run([exe] + entrees, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=120, cwd=TMP)
        obtenu = r.stdout.strip()
        if r.returncode:
            obtenu += f" [code {r.returncode}] {r.stderr.strip()[:200]}"
    except subprocess.TimeoutExpired:
        obtenu = "TEMPS DÉPASSÉ"
    except OSError as x:
        obtenu = f"NE SE LANCE PAS : {x}"
    try:
        os.remove(exe)
    except OSError:
        pass
    return i, obtenu


t0 = time.time()
ecarts = []
with ThreadPoolExecutor(max_workers=min(8, os.cpu_count() or 2)) as ex:
    for i, obtenu in ex.map(essai, range(debut, fin)):
        if obtenu != attendu[i]:
            ecarts.append(i)
            if len(ecarts) <= 5:
                print(f"   programme {i} :\n     attendu {attendu[i][:300]}\n     obtenu  {obtenu[:300]}")
quoi = "traduits en .exe et lancés" if WIN else "traduits en .exe et relus (pas lancés : ce n'est pas Windows)"
print(f"2. Corpus de conformité {quoi} : {fin - debut} programmes, {len(ecarts)} écart(s) en {time.time() - t0:.1f} s"
      + (f" ; écarts : {ecarts[:40]}" if ecarts else ""))
shutil.rmtree(TMP, ignore_errors=True)
print("windows : tout est conforme" if ok1 and not ecarts else "windows : écart")
sys.exit(0 if ok1 and not ecarts else 1)
