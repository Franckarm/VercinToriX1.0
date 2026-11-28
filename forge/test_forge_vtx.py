#!/usr/bin/env python3
"""0.852 : la forge écrite en vtx (forge_vtx.py : le Rust écrit par vtxc128) contre la machine émulée : chaque programme
que vtxc128 sait forger doit rendre les mêmes sorties, le même texte et le même état final que Lugus émulé (lugus
corpus) sur ses propres mots. Ceux qu'il ne sait pas encore forger sont comptés, par raison (l'ancienne forge les garde).

    python3 forge/test_forge_vtx.py [NOMBRE_DE_PROGRAMMES_AU_HASARD] [GRAINE]"""
import collections
import os
import random
import shutil
import subprocess
import sys
import tempfile

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, racine)
sys.path.insert(0, ici)
sys.path.insert(0, os.path.join(racine, "vtxc"))
import vtx128  # noqa: E402  (seulement pour ses programmes d'essai)
import forge128  # noqa: E402
import forge_vtx  # noqa: E402
from hasard64 import G  # noqa: E402

rustc = shutil.which("rustc")
if not rustc:
    print("rustc absent : la forge en vtx n'est pas essayée")
    sys.exit(0)
N = int(sys.argv[1]) if len(sys.argv) > 1 else 60
GRAINE = int(sys.argv[2]) if len(sys.argv) > 2 else 852
EXE = forge_vtx.LUGUS
TMP = tempfile.mkdtemp(prefix="forge-vtx-test-")

PROPRES = [
    ("carrés", "fonction carre(x) { retour x * x; } fonction principal() { soit s = 0; pour i dans 0..10 "
     "{ s = s + carre(i); } si s > 100 { sortie(s); } sinon { sortie(0); } }", []),
    ("fibonacci récursif", "fonction fib(n) { si n < 2 { retour n; } retour fib(n - 1) + fib(n - 2); } "
     "fonction principal() { sortie(fib(20)); }", []),
    ("tantque, arrêter, continuer", "fonction principal() { soit i = 0; soit s = 0; tantque i < 100 { i = i + 1; "
     "si i % 3 == 0 { continuer; } si i > 50 { arrêter; } s = s + i; } sortie(s); sortie(i); }", []),
    ("décalages et masques", "fonction principal() { soit x = 1; pour k dans 0..130 { x = (x << 1) | (k & 1); } "
     "sortie(x); sortie(x >> 100); sortie(x ^ 12345); sortie(x & 255); }", []),
    ("débordement de 128 bits", "fonction principal() { soit x = 1; pour k dans 0..200 { x = x * 3 + 1; } "
     "sortie(x); sortie(x / 7); sortie(x % 1000); soit z = 0; sortie(z - 1); }", []),
    ("entrées", "fonction principal() { sortie(entrée() + entrée()); }", [20, 22]),
    ("et, ou", "fonction principal() { soit n = 0; pour i dans 0..50 { si (i > 10 && i < 20) || i == 42 "
     "{ n = n + 1; } } sortie(n); }", []),
    ("pas de boucle", "fonction principal() { soit s = 0; pour i dans 0..100 pas 7 { s = s + i; } sortie(s); }", []),
]

cas = list(PROPRES)
cas += [(nom, src, list(e)) for nom, src, e, _ in vtx128.TESTS + vtx128.TESTS_128]
for k in range(N):
    cas.append((f"hasard {k}", G(random.Random(GRAINE * 7919 + k)).programme(), []))

modules, gardes, mots_de = [], [], []
laisses = collections.Counter()
for nom, src, e in cas:
    prog, mots = forge_vtx.programme_rust_vtx(src, None, nom)
    if prog is None:
        laisses[mots.split(" (ligne")[0]] += 1
        continue
    modules.append(f"mod p{len(gardes)} {{\nuse super::*;\n{prog}\n}}\n")
    gardes.append((nom, e))
    mots_de.append(mots)
print(f"{len(gardes)} programmes forgés par vtxc128, {sum(laisses.values())} laissés à l'ancienne forge :")
for r, n in laisses.most_common(30):
    print(f"  {n:4d}  {r}")
if not gardes:
    print("aucun programme forgé")
    sys.exit(1)
appels = "\n".join(f"        {k} => p{k}::lancer(&a[2..])," for k in range(len(gardes)))
main = f"fn main() {{\n    let a: Vec<String> = std::env::args().collect();\n    match a[1].parse::<usize>().unwrap() {{\n{appels}\n        _ => {{}}\n    }}\n}}\n"
rs = os.path.join(TMP, "tous.rs")
open(rs, "w", encoding="utf-8").write(forge128.noyau() + "\n" + "\n".join(modules) + main)
exe = os.path.join(TMP, "tous" + (".exe" if os.name == "nt" else ""))
r = subprocess.run([rustc] + forge128.rustc_options() + ["-o", exe, rs], capture_output=True, text=True)
if r.returncode:
    print("rustc a refusé les programmes forgés :\n" + r.stderr[-4000:])
    sys.exit(1)

with open(os.path.join(TMP, "corpus.txt"), "w") as f:
    for (nom, e), m in zip(gardes, mots_de):
        f.write(",".join(map(str, m)) + ";" + ",".join(map(str, e)) + "\n")
emul = subprocess.run([EXE, "corpus", os.path.join(TMP, "corpus.txt")], capture_output=True, text=True).stdout.split("\n")

ecarts, memoire, sans_fin = [], [], 0
env = dict(os.environ, FORGE_LIGNE="1")
for k, (nom, e) in enumerate(gardes):
    em = emul[k].strip()
    if em.startswith("ERREUR limite"):
        sans_fin += 1
        continue
    fo = subprocess.run([exe, str(k)] + [str(x) for x in e], capture_output=True, text=True, env=env, cwd=TMP,
                        timeout=120).stdout.strip()
    if em.startswith("ERREUR") or fo.startswith("ERREUR"):
        if not (em.startswith("ERREUR") and fo.startswith("ERREUR")):
            ecarts.append((nom, em[:200], fo[:200]))
        continue
    em = em[em.index("|"):]
    a, b = em.split("|"), fo.split("|")
    if a[1] != b[1] or [x for x in a if x.startswith("T:")] != [x for x in b if x.startswith("T:")]:
        ecarts.append((nom, em[:200], fo[:200]))
    elif em != fo:
        memoire.append(nom)
for x in ecarts[:6]:
    print("  ÉCART", x)
if memoire:
    print(f"  mémoire finale différente (sorties identiques) : {len(memoire)} : {memoire[:5]}")
print(f"{len(gardes) - sans_fin} programmes forgés en vtx : {len(gardes) - sans_fin - len(ecarts)} rendent les mêmes sorties "
      f"et le même texte que Lugus émulé ; {len(gardes) - sans_fin - len(ecarts) - len(memoire)} aussi la même mémoire"
      + (f" ({sans_fin} sans fin, écartés)" if sans_fin else ""))
shutil.rmtree(TMP, ignore_errors=True)
ok = not ecarts and not memoire
print("La forge en vtx : conforme." if ok else f"{len(ecarts)} écart(s), {len(memoire)} mémoire(s)")
sys.exit(0 if ok else 1)
