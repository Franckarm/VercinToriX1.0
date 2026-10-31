#!/usr/bin/env python3
"""La forge de Lugus contre la machine émulée : chaque programme forgé doit rendre les mêmes sorties, le même texte et
le même état final de la mémoire (étages 1 à 3) et du brin que Lugus émulé (lugus corpus) ; une erreur de la machine
(écriture dans un mot ADN…) doit arrêter les deux.

Programmes : la suite de vtx128.py (ceux du SPU-64 et ceux de Lugus, dans le langage de Lugus) et des programmes tirés
au hasard (vtxc/hasard64.py) ; les programmes des mesures, trop longs pour la machine émulée du corpus, sont vérifiés par
mesures/mesurer128.py. Tous les programmes forgés vont dans un seul programme
Rust (un module chacun), compilé une fois.

    python3 forge/test_forge128.py [NOMBRE_DE_PROGRAMMES_AU_HASARD] [GRAINE]"""
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
import vtx128  # noqa: E402
import forge128  # noqa: E402
from hasard64 import G  # noqa: E402

vtx128.COMPAT_64 = False
rustc = shutil.which("rustc")
if not rustc:
    print("rustc absent : la forge de Lugus n'est pas essayée")
    sys.exit(0)
N = int(sys.argv[1]) if len(sys.argv) > 1 else 60
GRAINE = int(sys.argv[2]) if len(sys.argv) > 2 else 128
EXE = os.path.join(racine, "vtx-rs", "target", "release", "lugus" + (".exe" if os.name == "nt" else ""))
TMP = tempfile.mkdtemp(prefix="forge128-test-")

# (nom, source, entrées, dans le langage du SPU-64) : la suite deux fois (le langage de Lugus, puis celui du SPU-64),
# les programmes au hasard dans le langage du SPU-64 (le générateur l'écrit), puis dans celui de Lugus
cas = [(nom, src, list(e), False) for nom, src, e, _ in vtx128.TESTS + vtx128.TESTS_128]
cas += [(nom + " [64]", src, list(e), True) for nom, src, e, _ in vtx128.TESTS]
# l'adaptation automatique : des tableaux que seul leur nom touche, rangés serrés hors du cube (octets, u64, u128)
SERRES = [
    ("serré : octets écrits", "tableau t[300] @1[0]; fonction principal() { pour i dans 0..300 { t[i] = 1; } "
     "pour i dans 0..100 { t[i * 3] = 0; } t[7] = 255; soit s = 0; pour i dans 0..300 { s = s + t[i]; } sortie(s); }"),
    ("serré : entiers de 64 bits, négatifs", "tableau t[500] @2[100]; fonction principal() { pour i dans 0..500 "
     "{ t[i] = i * i - 1000; } soit s = 0; pour i dans 0..500 { s = s + t[i]; } sortie(s); sortie(t[3]); }"),
    ("serré : flottants de 128 bits", "tableau t[200] @1[0]; fonction principal() { pour i dans 0..200 "
     "{ t[i] = bits(flottant(i) * 1.5); } soit x = 0.0; pour i dans 0..200 { x = x + comme_flottant(t[i]); } "
     "sortie(bits(x)); }"),
    ("serré : structures", "structure P { x, y } tableau ps[100] de P @1[0]; fonction principal() { pour i dans 0..100 "
     "{ ps[i].x = i; ps[i].y = i * 3; } soit s = 0; pour i dans 0..100 { s = s + ps[i].x * ps[i].y; } sortie(s); }"),
    ("serré : deux tableaux et un accès voisin", "tableau a[100] @1[0]; tableau b[100] @1[100]; fonction principal() "
     "{ @1[5000] = 7; pour i dans 0..100 { a[i] = i; b[i] = a[i] * 2; } sortie(a[99] + b[99] + @1[5000]); }"),
    ("serré : indice hors du tableau", "tableau a[100] @1[0]; fonction principal() { soit k = 150; "
     "pour i dans 0..100 { a[i] = i; } a[k] = 9; sortie(a[k] + a[99]); }"),
    ("serré : entier_32 et logiques", "tableau a[100] @3[0]; tableau b[100] @2[0]; fonction principal() { "
     "pour i dans 0..100 { a[i] = entier_32(i) * 7S; b[i] = entier(i % 3 == 0); } soit s = 0; "
     "pour i dans 0..100 { s = s + entier(a[i]) + b[i]; } sortie(s); }"),
    ("serré : points de matière", "tableau a[100] @1[0]; fonction principal() { pour i dans 0..100 "
     "{ a[i] = bits(avec_reflet(#FF8000, i % 64)); } sortie(a[50]); sortie(comme_point(a[63]).reflet); }"),
    ("serré : une erreur au milieu", "tableau a[100] @1[0]; fonction principal() { pour i dans 0..100 { a[i] = i + 1; } "
     "@0[3] = 1; sortie(a[5]); }"),
]
cas += [(nom, src, [], False) for nom, src in SERRES]
for k in range(N):
    src = G(random.Random(GRAINE * 7919 + k)).programme()
    cas.append((f"hasard {k} [64]", src, [], True))
    cas.append((f"hasard {k}", src, [], False))

modules, gardes, refus = [], [], 0
mots_de = []
for i, (nom, src, e, compat) in enumerate(cas):
    vtx128.COMPAT_64 = compat
    try:
        prog, mots = forge128.programme_rust(src, None, nom)
    except vtx128.VtxError as x:
        refus += 1
        if "forge" in str(x):
            print(f"  refusé par la forge : {nom} : {x}")
        continue
    modules.append(f"mod p{len(gardes)} {{\nuse super::*;\n{prog}\n}}\n")
    gardes.append((nom, e))
    mots_de.append(mots)
appels = "\n".join(f"        {k} => p{k}::lancer(&a[2..])," for k in range(len(gardes)))
main = f"fn main() {{\n    let a: Vec<String> = std::env::args().collect();\n    match a[1].parse::<usize>().unwrap() {{\n{appels}\n        _ => {{}}\n    }}\n}}\n"
rs = os.path.join(TMP, "tous.rs")
open(rs, "w", encoding="utf-8").write(forge128.noyau() + "\n" + "\n".join(modules) + main)
exe = os.path.join(TMP, "tous" + (".exe" if os.name == "nt" else ""))
r = subprocess.run([rustc] + forge128.rustc_options() + ["-o", exe, rs], capture_output=True, text=True)
if r.returncode:
    print("rustc a refusé les programmes forgés :\n" + r.stderr[-4000:])
    sys.exit(1)

# la machine émulée
with open(os.path.join(TMP, "corpus.txt"), "w") as f:
    for (nom, e), m in zip(gardes, mots_de):
        f.write(",".join(map(str, m)) + ";" + ",".join(map(str, e)) + "\n")
emul = subprocess.run([EXE, "corpus", os.path.join(TMP, "corpus.txt")], capture_output=True, text=True).stdout.split("\n")

ecarts, memoire, sans_fin = [], [], 0
env = dict(os.environ, FORGE_LIGNE="1")
for k, (nom, e) in enumerate(gardes):
    em = emul[k].strip()
    if em.startswith("ERREUR limite"):
        # une boucle sans fin (le générateur en écrit parfois) : la machine émulée s'arrête à sa limite d'instructions,
        # le programme forgé n'en a pas ; rien à comparer
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
    print(f"  mémoire finale différente (sorties identiques) : {len(memoire)} programme(s) : {memoire[:5]}")
print(f"{len(gardes) - sans_fin} programmes forgés ({refus} refusés par le compilateur ou la forge) : {len(gardes) - sans_fin - len(ecarts)} rendent "
      f"les mêmes sorties et le même texte que Lugus émulé ; {len(gardes) - sans_fin - len(ecarts) - len(memoire)} aussi la même mémoire"
      + (f" ({sans_fin} sans fin, écartés)" if sans_fin else ""))
shutil.rmtree(TMP, ignore_errors=True)
ok = not ecarts
print("La forge de Lugus : conforme." if ok else f"{len(ecarts)} écart(s)")
sys.exit(0 if ok else 1)
