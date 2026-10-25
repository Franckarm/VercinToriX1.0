#!/usr/bin/env python3
"""vtxc128 : le compilateur de Vercintorix écrit en vtx, pour Lugus (le SPU-128). Il doit donner exactement les mêmes mots
que vtx128.py (le langage de Lugus : flottant de 128 bits par défaut, point de matière), et se compiler lui-même.

 1. Point fixe : M0 = vtx128.py(vtxc128.vtx), M1 = M0(vtxc128.vtx), M2 = M1(vtxc128.vtx) sur la machine Rust de Lugus.
 2. La suite de vtx128.py (ses programmes, ceux du SPU-64 et ceux de Lugus), avec le prélude, sans et avec optimisation.
 3. Des programmes aléatoires (vtxc/hasard64.py) : prélude, optimisations, partition.
 4. Avec les optimisations, vtxc128 se compile comme vtx128.py ; le compilateur embarqué dans lugus est à jour.
 5. L'atelier sur Lugus (vtx-spu essai-pas128) : pas à pas ligne par ligne, par-dessus les fonctions et d'un coup, la
    vue du cube, sur les exemples de Lugus (exemples128).

    python3 vtxc/test_vtxc128.py [--complet] [--sans-point-fixe] [--seul MOT]"""
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, racine)
sys.path.insert(0, ici)
import vtx128  # noqa: E402
from hasard64 import G  # noqa: E402

COMPLET = "--complet" in sys.argv
EXE = os.path.join(racine, "vtx-rs", "target", "release", "lugus" + (".exe" if os.name == "nt" else ""))
TMP = tempfile.mkdtemp(prefix="vtxc128-")
echecs = []
vtx128.COMPAT_64 = False


def verifier(nom, ok, detail=""):
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok or not detail else " : " + detail), flush=True)
    if not ok:
        echecs.append(nom)


def ref(src, pr, op, pa=False, dossier=None):
    try:
        return vtx128.assembler(vtx128.compiler(src, prelude=pr, optim=op, partition=pa, dossier=dossier))
    except vtx128.VtxError as e:
        return "ERREUR " + str(e)


def vtxc(prog, src, pr=False, op=False, pa=False, base=""):
    d = os.path.join(TMP, "travail")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "c.mots"), "w") as f:
        f.write(",".join(map(str, prog)) + ";\n")
    with open(os.path.join(d, "source.vtx"), "w", encoding="utf-8") as f:
        f.write(src)
    cm = os.path.join(d, "code.mots")
    if os.path.exists(cm):
        os.remove(cm)
    e = [str(ord(c)) for c in base] + ["0", str(int(pr)), str(int(op)), str(int(pa))]
    r = subprocess.run([EXE, "lancer", os.path.join(d, "c.mots")] + e, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if not os.path.exists(cm):
        return None, r.stdout + r.stderr
    t = open(cm).read().strip()
    return [int(x) for x in t.split(";")[0].split(",") if x], r.stdout


def pareil(a, b):
    return a == b or (isinstance(a, str) and b is None)


def premier_ecart(a, b):
    if isinstance(a, str) or b is None:
        return f"vtx128 : {a if isinstance(a, str) else len(a)} ; vtxc128 : {b if b is None else len(b)}"
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return f"mot {i} : #{x:032X} au lieu de #{y:032X} ({len(a)} / {len(b)} mots)"
    return f"longueurs {len(a)} / {len(b)}"


src_c = open(os.path.join(ici, "vtxc128.vtx"), encoding="utf-8").read()
t0 = time.time()
m0 = ref(src_c, False, False)
if isinstance(m0, str):
    print(m0)
    sys.exit(1)
print(f"vtx128.py compile vtxc128 : {len(m0)} mots ({time.time() - t0:.0f} s)", flush=True)

seul = sys.argv[sys.argv.index("--seul") + 1] if "--seul" in sys.argv else None
cas = [(f"{nom} [64]", src) for nom, src, *_ in vtx128.TESTS] + [(nom, src) for nom, src, *_ in vtx128.TESTS_128]
if seul:
    cas = [x for x in cas if seul in x[0]]
ecarts = []
n = 0
for nom, src in cas:
    for pr, op in ((False, False), (True, False), (True, True)):
        n += 1
        a = ref(src, pr, op)
        b, sortie = vtxc(m0, src, pr, op)
        if not pareil(a, b):
            ecarts.append((nom, pr, op, premier_ecart(a, b), sortie[-200:]))
for e in ecarts[:8]:
    print("   ", e)
verifier(f"la suite de vtx128.py : {n - len(ecarts)}/{n} compilations identiques", not ecarts)

if not seul:
    N = 60 if COMPLET else 12
    graine = random.randrange(1 << 30)
    ecarts = []
    n = 0
    for k in range(N):
        src = G(random.Random(graine + k)).programme()
        for pr, op, pa in ((True, False, False), (True, True, False), (True, True, True)):
            n += 1
            a = ref(src, pr, op, pa)
            b, sortie = vtxc(m0, src, pr, op, pa)
            if not pareil(a, b):
                ecarts.append((graine + k, pr, op, pa, premier_ecart(a, b)))
    for e in ecarts[:5]:
        print("   ", e)
    verifier(f"{N} programmes aléatoires (graine {graine}) : {n - len(ecarts)}/{n} compilations identiques", not ecarts)

if not seul and "--sans-point-fixe" not in sys.argv:
    t0 = time.time()
    m1, o1 = vtxc(m0, src_c)
    m2, o2 = vtxc(m1 or [], src_c)
    verifier(f"point fixe : vtxc128 se compile lui-même ({len(m0)} mots, M0 = M1 = M2, {time.time() - t0:.0f} s)",
             m0 == m1 == m2, (o1 + o2)[-300:])

if not seul and "--sans-point-fixe" not in sys.argv:
    m_opt = ref(src_c, False, True)
    m3, o3 = vtxc(m0, src_c, op=True)
    verifier(f"avec les optimisations : vtxc128 compile vtxc128.vtx comme vtx128.py ({len(m_opt)} mots)", m3 == m_opt, o3[-300:])
    lire = lambda f: [int(x) for x in open(f).read().split(";")[0].replace("\n", "").split(",") if x.strip()]
    emb = lire(os.path.join(racine, "vtx-rs", "vtxc128.mots"))
    arbre = lire(os.path.join(ici, "vtxc128.mots"))
    verifier(f"vtx-rs/vtxc128.mots (embarqué dans lugus) = vtxc/vtxc128.mots = vtxc128 optimisé ({len(emb)} mots)",
             emb == arbre == m_opt, "refaire : lugus renouveler vtxc/vtxc128.vtx, puis copier vtxc/vtxc128.mots dans vtx-rs")

if not seul:
    spu = os.path.join(racine, "vtx-rs", "target", "release", "vtx-spu" + (".exe" if os.name == "nt" else ""))
    dex = os.path.join(racine, "exemples128")
    exs = sorted(f for f in os.listdir(dex) if f.endswith(".vtx"))
    ecarts = []
    for f in exs:
        r = subprocess.run([spu, "essai-pas128", os.path.join(dex, f)], cwd=TMP, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if r.returncode != 0 or not r.stdout.rstrip().endswith("conforme") or "NON CONFORME" in r.stdout:
            ecarts.append(f)
    verifier(f"atelier sur Lugus : {len(exs) - len(ecarts)}/{len(exs)} exemples, pas à pas et vue conformes", not ecarts,
             str(ecarts))

shutil.rmtree(TMP, ignore_errors=True)
print("vtxc128 : " + ("tout est conforme" if not echecs else f"{len(echecs)} échec(s)"))
sys.exit(1 if echecs else 0)
