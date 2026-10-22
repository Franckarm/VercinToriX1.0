#!/usr/bin/env python3
"""Traduction en code natif (vtx traduire) : le programme du SPU devient du Rust, compilé par rustc (LLVM).
 1. Corpus de conformité : chaque programme traduit, compilé, exécuté ; nombre d'instructions, sorties et mémoire
    identiques à ceux attendus (les mêmes que pour toutes les machines).
 2. Programmes du paquet : sorties identiques à celles de la machine Rust interprétée ; temps de l'un et de l'autre.
Il faut cargo et rustc. Utilisation : python3 natif/test_natif.py"""
import os, shutil, subprocess, sys, tempfile, time
ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
RAPIDE = os.environ.get("VTX_RAPIDE") == "1"
cargo, rustc = shutil.which("cargo"), shutil.which("rustc")
if not (cargo and rustc):
    print("cargo ou rustc absent : la traduction en code natif n'est pas essayée")
    sys.exit(0)
rs = os.path.join(racine, "vtx-rs")
cible = os.environ.get("CARGO_TARGET_DIR") or os.path.join(rs, "target")
subprocess.run([cargo, "build", "--release", "-q"], cwd=rs, check=True)
ext = ".exe" if os.name == "nt" else ""
VTX = os.path.join(cible, "release", "vtx" + ext)
SPU = os.path.join(cible, "release", "vtx-spu" + ext)
TMP = tempfile.mkdtemp(prefix="natif-")

# 1. corpus
lignes = [l for l in open(os.path.join(racine, "conformite", "corpus_conformite.txt")).read().split("\n") if l.strip()]
attendu = open(os.path.join(racine, "conformite", "corpus_attendu.txt")).read().strip().split("\n")
if RAPIDE:
    choix = list(range(0, len(lignes), 6))
    lignes, attendu = [lignes[i] for i in choix], [attendu[i] for i in choix]
cp = os.path.join(TMP, "corpus.txt")
with open(cp, "w") as f:
    f.write("\n".join(lignes) + "\n")
subprocess.run([SPU, "traduire-corpus", cp, os.path.join(TMP, "corpus.rs")], check=True)
t0 = time.time()
subprocess.run([rustc, "--edition", "2021", "-C", "opt-level=1", "-C", "panic=abort", "-o", os.path.join(TMP, "corpus" + ext),
                os.path.join(TMP, "corpus.rs")], check=True)
tc = time.time() - t0
obtenu = subprocess.run([os.path.join(TMP, "corpus" + ext), cp], capture_output=True, text=True).stdout.strip().split("\n")
ec = sum(a != b for a, b in zip(attendu, obtenu)) + abs(len(attendu) - len(obtenu))
print(f"1. Corpus de conformité traduit en code natif : {len(attendu)} programmes, {ec} écart(s) "
      f"(instructions, sorties et mémoire) ; compilation par rustc en {tc:.0f} s")

# 2. programmes du paquet : natif contre interprète
cas = [("logique", "capteurs.vtx", ["1"]), ("logique", "capteurs.vtx", ["2"]), ("genomique", "motif.vtx", ["1"]),
       ("genomique", "motif.vtx", ["3"]), ("genomique", "motif.vtx", ["4"]), ("logique", "initialisation.vtx", "9 3 0 0 0 2 1 0 4 1 1 1 0 0 1 1 0 5 2 2 3 0 8 2 4 6 8 0 1 5 0 16 1 5 0 1 0".split()),
       ("ombre", "ombre.vtx", ["0", "0"]), ("ombre", "ombre.vtx", ["2", "0"]),
       ("feu", "feu.vtx", ["1", "0", "16" if RAPIDE else "256", "1"])]
ok, ti, tn = 0, 0.0, 0.0
traduits = {}
for d, nom, e in cas:
    dd = os.path.join(racine, d)
    exe = os.path.join(TMP, nom[:-4] + ext)
    if nom not in traduits:
        r = subprocess.run([VTX, "traduire", nom, exe], cwd=dd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        traduits[nom] = r.returncode == 0
        if r.returncode:
            print("   traduction en échec :", nom, r.stderr[-300:])
    t0 = time.time()
    a = subprocess.run([VTX, nom] + e, cwd=dd, capture_output=True, text=True, env=dict(os.environ, VTX_ROTOS="1")).stdout
    t1 = time.time()
    b = subprocess.run([exe] + e, cwd=dd, capture_output=True, text=True).stdout if traduits[nom] else None
    t2 = time.time()
    ti, tn = ti + t1 - t0, tn + t2 - t1
    ok += a == b and len(a) > 0
    if a != b:
        print("   écart :", nom, e)
print(f"2. Programmes du paquet (capteurs, génomique, initialisation, ombre, feu de camp) : sorties identiques à la machine "
      f"interprétée {ok}/{len(cas)} ; temps total {ti:.2f} s interprété, {tn:.2f} s natif (rapport {ti / max(tn, 1e-9):.1f})")

# 3. accords sur plusieurs cylindres : programmes aléatoires de la partition (suites d'appels, segments, cumulants)
import random, re  # noqa: E402
sys.path.insert(0, racine)
import vtx  # noqa: E402
tp = open(os.path.join(racine, "partition", "test_partition.py"), encoding="utf-8").read()
gp = {"__name__": "p", "vtx": vtx, "__file__": os.path.join(racine, "partition", "x.py")}
code = "\n".join(l for l in tp.split("def etat(")[0].splitlines() if "spec" not in l and not l.startswith("vtx =")
                 and not l.startswith("import importlib"))
for nm in ("programme", "prog_segments", "prog_cumul"):
    code += "\n" + re.search(r"^def " + nm + r"\(r\):.*?(?=^\S)", tp, re.S | re.M).group(0)
exec(code, gp)
r3, ok3, n3, accords = random.Random(11), 0, 0, 0
for nm in ("programme", "prog_segments", "prog_cumul"):
    for _ in range(2 if RAPIDE else 5):
        src = gp[nm](r3)
        src = src[0] if isinstance(src, tuple) else src
        p_ = os.path.join(TMP, "acc.vtx")
        with open(p_, "w", encoding="utf-8") as f:
            f.write(src)
        exe = os.path.join(TMP, "acc" + ext)
        if subprocess.run([VTX, "traduire", p_, exe], capture_output=True).returncode:
            continue
        n3 += 1
        accords += vtx.exporter(src)[1][0] > 0
        att = subprocess.run([VTX, p_], capture_output=True, text=True, env=dict(os.environ, VTX_ROTOS="1")).stdout
        obt = [subprocess.run([exe], capture_output=True, text=True, env=dict(os.environ, VTX_ROTOS=k)).stdout
               for k in ("1", "2", "3")]
        ok3 += all(o == att for o in obt) and len(att) > 0
# l'ombre en segments : temps natif sur 1 et 2 cylindres
dd = os.path.join(racine, "ombre")
exe = os.path.join(TMP, "ombre" + ext)
temps = []
for k in ("1", "2"):
    t0 = time.time()
    subprocess.run([exe, "0", "0"], cwd=dd, capture_output=True, env=dict(os.environ, VTX_ROTOS=k))
    temps.append(time.time() - t0)
print(f"3. Accords joués par le code natif sur 1, 2 et 3 cylindres : {n3} programmes aléatoires (dont {accords} avec des "
      f"accords), sorties identiques à la machine interprétée {ok3}/{n3} ; ombre {temps[0]:.3f} s sur 1 cylindre, "
      f"{temps[1]:.3f} s sur 2")
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(0 if ec == 0 and ok == len(cas) and ok3 == n3 and n3 > 0 else 1)
