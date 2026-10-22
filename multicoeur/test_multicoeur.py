#!/usr/bin/env python3
"""Machine Rust multicœur : les tâches d'une même mesure jouées sur plusieurs cœurs donnent exactement les mêmes sorties
qu'en séquence.
 1. Programmes aléatoires en segments (tableaux, adresses calculées, étages, appels) et cumulants (histogrammes) : sorties
    identiques sur 1, 2 et 3 cylindres ; ils sortent une somme de contrôle de chaque étage, donc la mémoire est comparée.
 2. Démonstrations : partition (orchestre en segments cumulés), rendu de l'ombre (64³) : sorties identiques, et durée.
Demande cargo (machine Rust)."""
import importlib.util
import os
import random
import shutil
import subprocess
import sys

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.join(ici, "..")
spec = importlib.util.spec_from_file_location("vtx", os.path.join(racine, "vtx.py"))
vtx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vtx)
RAPIDE = os.environ.get("VTX_RAPIDE") == "1"

cargo = shutil.which("cargo")
if not cargo:
    print("cargo absent : machine multicœur non vérifiée")
    sys.exit(0)
rs = os.path.join(racine, "vtx-rs")
cible = os.environ.get("CARGO_TARGET_DIR") or os.path.join(rs, "target")
subprocess.run([cargo, "build", "--release", "-q"], cwd=rs, check=True)
exe = os.path.join(cible, "release", "vtx-spu" + (".exe" if os.name == "nt" else ""))


def lancer(src, entrees, cylindres, dossier=None):
    mots, table = vtx.exporter(src, dossier)
    f = os.path.join(ici, "_multi.txt")
    with open(f, "w") as h:
        h.write(",".join(map(str, mots)) + ";" + ",".join(map(str, entrees)) + ";" + ",".join(map(str, table)) + "\n")
    out = subprocess.run([exe, "lancer", f, "20000000000", str(cylindres)], capture_output=True, text=True, check=True)
    os.remove(f)
    lignes = out.stdout.split("\n")
    duree = float(lignes[0].split(" en ")[1].split(" s")[0])
    return lignes[1], duree, table[0]


def prog_segments(r):
    tabs = [("a", 1, 0), ("b", 1, 300), ("c", 2, 0), ("d", 3, 0)]
    lignes = [f"tableau {n}[300] @{e}[{base}];" for n, e, base in tabs] + ["tableau h[16] @2[1000];"]
    lignes.append("fonction aide(k) { retour a[k % 300] * 3 + 1; }")
    corps = []
    for nx in range(r.randint(1, 3)):
        k = r.random()
        dst, src_ = r.choice(tabs)[0], r.choice(tabs)[0]
        if k < 0.5:
            corps.append(f"        {dst}[i + {r.choice([0, 0, 1])}] = {src_}[i + {r.randint(0, 3)}] * {r.randint(1, 5)} + aide(i);")
        elif k < 0.7:
            corps.append(f"        soit x{nx} = {src_}[(i * 7) % 250] + i;\n        {dst}[i] = x{nx};")
        elif k < 0.85:
            corps.append(f"        {dst}[{r.randint(0, 9)}] = i;")
        else:
            corps.append(f"        @{r.randint(1, 3)}[(i * 3) & 255] = i;")
    cum = r.random() < 0.4
    if cum:
        corps.append("        h[a[i] & 15] = h[a[i] & 15] + i;")
    n = r.choice(["", " 6", " 12", " 18"])
    lignes.append("fonction principal() {\n    pour q dans 0..300 {\n" + "".join(f"        {t[0]}[q] = q * {r.randint(1, 9)} + {r.randint(0, 50)};\n" for t in tabs)
                  + f"    }}\n    pour i dans {r.randint(0, 5)}..{r.randint(100, 290)} en{n} segments{' cumulant h' if cum else ''} {{\n"
                  + "\n".join(corps) + "\n    }\n"
                  + "    pour e dans 1..4 {\n        soit somme = 0;\n        pour q dans 0..1100 {\n            somme = somme * 31 + @(e)[q];\n        }\n        sortie(somme);\n    }\n}")
    return "\n".join(lignes)


r = random.Random(11)
N = 20 if RAPIDE else 80
ok = paralleles = 0
for n in range(N):
    src = prog_segments(r)
    ref = vtx.executer(src, (), max_pas=50_000_000)[0].sortie
    sorties = [lancer(src, [], c)[0] for c in (1, 2, 3)]
    attendu = ",".join(map(str, ref))
    vtx.compiler(src)
    paralleles += any(len(a["mesures"]) == 1 for a in vtx.DERNIERE_PARTITION["accords"] if a.get("segments"))
    if all(s_ == attendu for s_ in sorties):
        ok += 1
    else:
        print("ÉCHEC", n, sorties, attendu)
        print(src)
        break
print(f"1. {N} programmes aléatoires en segments : sorties identiques à l'émulateur Python sur 1, 2 et 3 cylindres "
      f"{ok}/{N} ; {paralleles} avec des segments joués ensemble")
assert ok == N

orch = open(os.path.join(racine, "partition", "orchestre_cumul.vtx"), encoding="utf-8").read()
s1, d1, na = lancer(orch, [], 1, os.path.join(racine, "partition"))
s3, d3, _ = lancer(orch, [], 3, os.path.join(racine, "partition"))
print(f"2. Orchestre en segments cumulés ({na} accords) : sorties identiques sur 1 et 3 cylindres : {s1 == s3}")
assert s1 == s3
spec2 = importlib.util.spec_from_file_location("tom", os.path.join(racine, "ombre", "test_ombre.py"))
src_o = open(os.path.join(racine, "ombre", "test_ombre.py"), encoding="utf-8").read()
ns = {"__file__": os.path.join(racine, "ombre", "test_ombre.py")}
exec(src_o[:src_o.index("SEULEMENT_GRANDS")], ns)
ombre = ns["gabarit"](64 if RAPIDE else 128)
o1, t1, _ = lancer(ombre, [0, 0], 1, os.path.join(racine, "ombre"))
o2, t2, _ = lancer(ombre, [0, 0], 2, os.path.join(racine, "ombre"))
print(f"   Ombre ({64 if RAPIDE else 128}³, image et ombres en segments) : sorties identiques : {o1 == o2} ; "
      f"{t1:.2f} s sur 1 cylindre, {t2:.2f} s sur 2 (gain {t1 / t2:.2f})")
assert o1 == o2
