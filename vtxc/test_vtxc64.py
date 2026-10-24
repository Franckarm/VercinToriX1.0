#!/usr/bin/env python3
"""vtxc64 : le compilateur de Vercintorix écrit en vtx, pour le SPU-64. Il doit donner exactement les mêmes mots que
vtx64.py, et se compiler lui-même (point fixe).

 1. Point fixe : M0 = vtx64.py(vtxc64.vtx), M1 = M0(vtxc64.vtx), M2 = M1(vtxc64.vtx) sur la machine Rust : M0 = M1 = M2.
    Et avec les optimisations : vtxc64 compile vtxc64.vtx comme vtx64.py optimisé (le compilateur embarquable).
 2. La suite de vtx64.py (ses programmes de test), avec le prélude, sans et avec optimisation : mêmes mots.
 3. Les programmes de tests/test_vtx64.py et les exemples de exemples64 : mêmes mots (prélude, optimisations, partition).
 4. Des programmes aléatoires (entier, entier_32, flottant, flottant_32, entier_petuar, flottant_petuar, logique,
    structures, tableaux rangés, @[a], hypothèses, segments, accords, tous les littéraux) : mêmes mots.
 5. Le compilateur embarqué dans la machine Rust (vtx-rs/vtxc64.mots) est vtxc64 optimisé, à jour.
 6. « vtx64 PROG.vtx » (compilé par vtxc64 embarqué, sans Python) donne, sur exemples64, ce que donnent vtx64.py puis
    la machine.
 7. L'atelier sur la SPU-64 (vtx-spu essai-pas64) : pas à pas ligne par ligne, par-dessus les fonctions et d'un coup,
    même console et mêmes sorties ; la vue du cube (points de 32 bits) montre chaque mot.

Chaque étape s'annonce avant de commencer (le point fixe prend une à deux minutes) ; dans un terminal, un compteur
montre l'avancement des longues étapes.

    python3 vtxc/test_vtxc64.py [--complet] [--journal FICHIER]"""
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
import vtx64  # noqa: E402
from hasard64 import G  # noqa: E402

COMPLET = "--complet" in sys.argv
DEBUT = time.time()
TERMINAL = sys.stdout.isatty()
if "--journal" in sys.argv:
    # tout ce qui est écrit va aussi dans le fichier journal (essai.bat : la console et build.log)
    class _Double:
        def __init__(self, a, chemin):
            self.a, self.f = a, open(chemin, "a", encoding="utf-8")

        def write(self, t):
            self.a.write(t)
            # le compteur (retours chariot) reste à l'écran seulement
            if "\r" not in t:
                self.f.write(t)
                self.f.flush()

        def flush(self):
            self.a.flush()

        def isatty(self):
            return self.a.isatty()

    sys.stdout = _Double(sys.stdout, sys.argv[sys.argv.index("--journal") + 1])


def annoncer(t):
    """Ce que le test va faire, aussitôt écrit (un test muet ressemble à un test bloqué)."""
    print(f"[{time.time() - DEBUT:5.0f} s] {t}…", flush=True)


cargo = shutil.which("cargo")
if not cargo:
    print("cargo absent : vtxc64 n'est pas vérifié (il tourne sur la machine Rust)")
    sys.exit(0)
rs = os.path.join(racine, "vtx-rs")
cible = os.environ.get("CARGO_TARGET_DIR") or os.path.join(rs, "target")
annoncer("construction de la machine Rust (cargo build --release)")
subprocess.run([cargo, "build", "--release", "-q"], cwd=rs, check=True)
EXE = os.path.join(cible, "release", "vtx64" + (".exe" if os.name == "nt" else ""))
TMP = tempfile.mkdtemp(prefix="vtxc64-")
echecs = []


def compteur(k, n):
    if TERMINAL:
        print(f"\r        {k}/{n}", end="", flush=True)
        if k == n:
            print("\r" + " " * 24 + "\r", end="", flush=True)


def verifier(nom, ok, detail=""):
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok or not detail else " : " + detail), flush=True)
    if not ok:
        echecs.append(nom)


def ref(src, pr, op, pa=False, dossier=None):
    try:
        return vtx64.assembler(vtx64.compiler(src, prelude=pr, optim=op, partition=pa, dossier=dossier))
    except vtx64.VtxError as e:
        return "ERREUR " + str(e)


def vtxc(prog, src, pr=False, op=False, pa=False, base=""):
    """Compile src avec le compilateur prog (des mots) ; ses entrées : le dossier des fichiers importés, 0, puis le
    prélude, les optimisations et la partition. Rend les mots (None si la compilation échoue) et le texte affiché."""
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
    """Mêmes mots, ou les deux compilateurs refusent le programme."""
    return a == b or (isinstance(a, str) and b is None)


# 1. point fixe
annoncer("1. point fixe : vtx64.py compile vtxc64 (M0), M0 se recompile (M1), M1 aussi (M2) — une à deux minutes")
t0 = time.time()
src_c = open(os.path.join(ici, "vtxc64.vtx"), encoding="utf-8").read()
m0 = ref(src_c, False, False)
m1, o1 = vtxc(m0, src_c)
m2, o2 = vtxc(m1 or [], src_c)
verifier(f"point fixe : vtxc64 se compile lui-même ({len(m0)} mots, M0 = M1 = M2, {time.time() - t0:.0f} s)",
         m0 == m1 == m2, (o1 + o2)[-300:])
annoncer("   vtxc64 compile vtxc64.vtx avec les optimisations")
m_opt = ref(src_c, False, True)
m3, o3 = vtxc(m0, src_c, op=True)
verifier(f"avec les optimisations : vtxc64 compile vtxc64.vtx comme vtx64.py ({len(m_opt)} mots)", m3 == m_opt, o3[-300:])

# 2. la suite de vtx64.py
annoncer(f"2. la suite de vtx64.py : {2 * len(vtx64.TESTS)} compilations, par vtx64.py et par vtxc64")
ecarts = []
n = 0
for nom, src, *_ in vtx64.TESTS:
    for pr, op in ((True, False), (True, True)):
        n += 1
        compteur(n, 2 * len(vtx64.TESTS))
        if not pareil(ref(src, pr, op), vtxc(m0, src, pr, op)[0]):
            ecarts.append((nom, pr, op))
verifier(f"suite de vtx64.py : {n - len(ecarts)}/{n} compilations identiques (prélude, sans et avec optimisation)",
         not ecarts, str(ecarts[:5]))

# 3. programmes de test_vtx64 et exemples64
import re  # noqa: E402
texte = open(os.path.join(racine, "tests", "test_vtx64.py"), encoding="utf-8").read()
progs = [("SRC%d" % k, eval(m.group(1))) for k in range(2, 7)
         for m in [re.search(r'SRC%d = ("""[\s\S]*?""")' % k, texte)] if m]
dex = os.path.join(racine, "exemples64")
progs += [(f, open(os.path.join(dex, f), encoding="utf-8").read()) for f in sorted(os.listdir(dex)) if f.endswith(".vtx")]
annoncer(f"3. programmes de test_vtx64 et exemples64 : {3 * len(progs)} compilations")
ecarts = []
n = 0
for nom, src in progs:
    for pr, op, pa in ((True, False, False), (True, True, False), (True, True, True)):
        n += 1
        compteur(n, 3 * len(progs))
        if not pareil(ref(src, pr, op, pa, dex), vtxc(m0, src, pr, op, pa, dex)[0]):
            ecarts.append((nom, pr, op, pa))
verifier(f"programmes de test_vtx64 et exemples64 : {n - len(ecarts)}/{n} identiques (prélude, optimisations, partition)",
         not ecarts, str(ecarts[:5]))

# 4. programmes aléatoires
N = 80 if COMPLET else 12
graine = random.randrange(1 << 30)
annoncer(f"4. {N} programmes aléatoires (graine {graine}) : {3 * N} compilations")
ecarts = []
n = 0
for k in range(N):
    src = G(random.Random(graine + k)).programme()
    for pr, op, pa in ((True, False, False), (True, True, False), (True, True, True)):
        n += 1
        compteur(n, 3 * N)
        if not pareil(ref(src, pr, op, pa), vtxc(m0, src, pr, op, pa)[0]):
            ecarts.append((graine + k, pr, op, pa))
verifier(f"{N} programmes aléatoires (graine {graine}) : {n - len(ecarts)}/{n} compilations identiques", not ecarts,
         str(ecarts[:5]))

# 5. le compilateur embarqué
annoncer("5. le compilateur embarqué dans la machine Rust")


def lire_mots(f):
    return [int(x) for x in open(f).read().split(";")[0].replace("\n", "").split(",") if x.strip()]


emb = lire_mots(os.path.join(rs, "vtxc64.mots"))
arbre_mots = lire_mots(os.path.join(ici, "vtxc64.mots"))
verifier(f"vtx-rs/vtxc64.mots (embarqué) = vtxc/vtxc64.mots = vtxc64 optimisé ({len(emb)} mots)", emb == arbre_mots == m_opt,
         f"embarqué {len(emb)}, vtxc {len(arbre_mots)}, attendu {len(m_opt)} : refaire « vtx64 renouveler vtxc/vtxc64.vtx »")

# 6. vtx64 PROG.vtx, sans Python
annoncer("6. « vtx64 PROG.vtx » sur exemples64 (vtxc64 embarqué), comparé à vtx64.py puis la machine")
ecarts = []
exs = [f for f in sorted(os.listdir(dex)) if f.endswith(".vtx")]
for f in exs:
    src = open(os.path.join(dex, f), encoding="utf-8").read()
    # chacun dans un dossier vide : un programme qui range un cube sur disque ne touche pas exemples64
    da, db = tempfile.mkdtemp(dir=TMP), tempfile.mkdtemp(dir=TMP)
    shutil.copy(os.path.join(dex, f), da)
    a = subprocess.run([EXE, f], cwd=da, capture_output=True, text=True, encoding="utf-8", errors="replace")
    mots = ref(src, True, True, True, dex)
    with open(os.path.join(db, "p.mots"), "w") as g:
        g.write(",".join(map(str, mots)) + ";\n")
    b = subprocess.run([EXE, "lancer", os.path.join(db, "p.mots")], capture_output=True, text=True, encoding="utf-8", errors="replace")
    # seul le message est comparé (« vtx64 lancer » avec VTX64_OU y ajoute l'adresse)
    erreur = lambda r: [x.split(" (à l'adresse")[0] for x in r.stderr.splitlines() if x.startswith("erreur")]  # noqa: E731
    if a.stdout != b.stdout or a.returncode != b.returncode or erreur(a) != erreur(b):
        ecarts.append(f)
verifier(f"vtx64 PROG.vtx : {len(exs) - len(ecarts)}/{len(exs)} exemples comme vtx64.py + machine", not ecarts, str(ecarts))

# 7. l'atelier sur la SPU-64
annoncer("7. l'atelier sur la SPU-64 : pas à pas (F7, F8, F5) et vue du cube, sur exemples64")
spu = os.path.join(cible, "release", "vtx-spu" + (".exe" if os.name == "nt" else ""))
ecarts = []
for f in exs:
    r = subprocess.run([spu, "essai-pas64", os.path.join(dex, f)], cwd=TMP, capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    if r.returncode != 0 or not r.stdout.rstrip().endswith("conforme") or "NON CONFORME" in r.stdout:
        ecarts.append(f)
verifier(f"atelier SPU-64 : {len(exs) - len(ecarts)}/{len(exs)} exemples, pas à pas et vue conformes", not ecarts, str(ecarts))

shutil.rmtree(TMP, ignore_errors=True)
print(f"[{time.time() - DEBUT:5.0f} s] fin")
print("Tout est conforme." if not echecs else f"{len(echecs)} échec(s)")
sys.exit(1 if echecs else 0)
