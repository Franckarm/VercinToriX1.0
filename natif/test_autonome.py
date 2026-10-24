#!/usr/bin/env python3
"""Traduction directe en x86-64 (natif/natif.py), sans Rust :
 1. l'assembleur x86-64 maison contre GNU as (mêmes octets) ;
 2. le corpus de conformité : chaque programme traduit en exécutable Linux, lancé ; nombre d'instructions, sorties,
    mémoire et texte identiques à ceux attendus (les mêmes que pour toutes les machines) ;
 3. le code d'un programme du corpus réassemblé par GNU as : mêmes octets.
Linux x86-64 seulement. Utilisation : python3 natif/test_autonome.py [premier [dernier]]"""
import os, platform, shutil, subprocess, sys, tempfile, time
from concurrent.futures import ThreadPoolExecutor

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, ici)
import natif, test_x86

if platform.system() != "Linux" or platform.machine() not in ("x86_64", "AMD64"):
    print("traduction directe : essai sur Linux x86-64 seulement")
    sys.exit(0)

ok = test_x86.comparer(test_x86.batterie(), "batterie")
print("1. Assembleur x86-64 :", "identique à GNU as" if ok else "ÉCART")

lignes = [l for l in open(os.path.join(racine, "conformite", "corpus_conformite.txt")).read().split("\n") if l.strip()]
attendu = open(os.path.join(racine, "conformite", "corpus_attendu.txt")).read().strip().split("\n")
debut = int(sys.argv[1]) if len(sys.argv) > 1 else 0
fin = int(sys.argv[2]) if len(sys.argv) > 2 else len(lignes)
TMP = tempfile.mkdtemp(prefix="autonome-")


def essai(i):
    m, _, e = lignes[i].partition(";")
    mots = [int(x) for x in m.split(",") if x.strip()]
    entrees = [x for x in e.split(",") if x.strip()]
    exe = os.path.join(TMP, f"p{i}")
    natif.ecrire_executable(exe, mots, corpus=True)
    try:
        r = subprocess.run([exe] + entrees, capture_output=True, text=True, timeout=120)
        obtenu = r.stdout.strip()
        if r.returncode:
            obtenu += f" [code {r.returncode}] {r.stderr.strip()[:200]}"
    except subprocess.TimeoutExpired:
        obtenu = "TEMPS DÉPASSÉ"
    os.remove(exe)
    return i, obtenu


t0 = time.time()
ecarts = []
with ThreadPoolExecutor(max_workers=os.cpu_count() or 2) as ex:
    for i, obtenu in ex.map(essai, range(debut, fin)):
        if obtenu != attendu[i]:
            ecarts.append(i)
            if len(ecarts) <= 5:
                print(f"   programme {i} :\n     attendu {attendu[i][:300]}\n     obtenu  {obtenu[:300]}")
print(f"2. Corpus de conformité traduit en x86-64 : {fin - debut} programmes, {len(ecarts)} écart(s) "
      f"en {time.time() - t0:.1f} s" + (f" ; écarts : {ecarts[:40]}" if ecarts else ""))

# 3. un programme entier réassemblé par GNU as
m = lignes[debut].partition(";")[0]
t = natif.traduire([int(x) for x in m.split(",") if x.strip()], corpus=True, texte=True)
ok3 = test_x86.comparer(t.a, "programme")
print("3. Programme traduit réassemblé par GNU as :", "mêmes octets" if ok3 else "ÉCART")
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(0 if ok and ok3 and not ecarts else 1)
