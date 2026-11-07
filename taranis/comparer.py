#!/usr/bin/env python3
"""Taranis : le même calcul sur chaque système que la machine sait faire tourner, et la table des temps.

Le calcul : n nombres (16 777 216 par défaut), chacun brassé en 64 tours de xorshift et de multiplication sur 32 bits
(8 opérations par tour). Chaque système doit rendre la même somme des n mots ; un système trop lent (Python, Lugus
émulé) tourne sur moins de nombres, et son temps est ramené à n (une règle de trois, dite dans la table).
  - vtx sur la carte : taranis (le SPIR-V écrit par taranis/spirv.py, par Vulkan) ; le calcul seul (horodaté par la
    carte), et tout compris (lancement, copie vers le processeur, attente) ;
  - C : brassage.c, compilé ici (cl /O2 /openmp sous Windows, gcc -O2 -fopenmp ailleurs), un cœur puis tous ;
  - vtx sur le processeur : brassage.vtx forgé (forge128 -> Rust -> natif), un cœur puis tous (le programme entier :
    il range aussi les n mots dans le cube et en fait la somme) ;
  - vtx forgé, la boucle sur la carte : le même programme, dont la forge a écrit la boucle en SPIR-V (taranis/
    noyau_vtx.py, les entiers de 64 bits de Lugus en deux mots de 32) ; le temps de la carte (monter, calculer,
    redescendre), et le programme entier (il range aussi les mots dans le cube, et fait la somme sur le processeur) ;
  - Rust : le brassage de taranis, un cœur puis tous ;
  - vtx sur Lugus émulé, et Python : sur une partie, ramenés à n.
    python taranis/comparer.py [n]"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, ici)
import spirv  # noqa: E402

WIN = os.name == "nt"
EXE = ".exe" if WIN else ""
n = int(sys.argv[1]) if len(sys.argv) > 1 else 1 << 24
bin_rs = os.path.join(racine, "vtx-rs", "target", "release")
tmp = tempfile.mkdtemp(prefix="taranis_")
lignes = []          # (système, millisecondes pour n, somme juste, remarque)
somme_ref = None


def ajouter(nom, ms, somme, remarque=""):
    lignes.append((nom, ms, somme, remarque))


def chrono(cmd, env=None):
    t = time.perf_counter()
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=3600)
    return time.perf_counter() - t, r


env = dict(os.environ)
if not WIN and "VK_ICD_FILENAMES" not in env:
    import glob
    icd = sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux64/vk_swiftshader_icd.json"))
    if icd:
        env["VK_ICD_FILENAMES"] = icd[-1]

print(f"le calcul : {n} nombres brassés en 64 tours ({n * 64 * 8 / 1e9:.1f} milliards d'opérations sur 32 bits)", flush=True)

# ------------------------------------------------------------------ la carte (et Rust, que taranis mesure aussi)
taranis = os.path.join(bin_rs, "taranis" + EXE)
carte = "?"
if os.path.exists(taranis):
    print("taranis (la carte, puis Rust sur le processeur) ...", flush=True)
    _, r = chrono([taranis, str(n)], env)
    o = r.stdout
    m = re.search(r"carte 0 : (.*)", o)
    carte = m.group(1) if m else "?"
    s = re.search(r"SOMME (\d+)", o)
    somme_carte = int(s.group(1)) if s else None
    somme_ref = somme_carte
    mc = re.search(r"CALCUL_MS ([\d.]+)", o)
    mt = re.search(r"carte, tout compris\s*:\s*([\d.]+) ms", o)
    if mc:
        ajouter(f"vtx sur la carte, le calcul ({carte.split(' (')[0]})", float(mc.group(1)), r.returncode == 0)
    if mt:
        ajouter("vtx sur la carte, tout compris (lancement, copie, attente)", float(mt.group(1)), r.returncode == 0)
    m1 = re.search(r"processeur, 1 cœur\s*:\s*([\d.]+) ms", o)
    mn = re.search(r"processeur, (\d+) cœurs\s*:\s*([\d.]+) ms", o)
    if m1:
        ajouter("Rust, 1 cœur", float(m1.group(1)), r.returncode == 0, "en comparant aussi chaque mot")
    if mn:
        ajouter(f"Rust, {mn.group(1)} cœurs", float(mn.group(2)), r.returncode == 0)
    if r.returncode != 0:
        print(o[-600:])
else:
    print("taranis n'est pas construit (cargo build --release dans vtx-rs)")

# ------------------------------------------------------------------ C
src = os.path.join(ici, "brassage.c")
exe_c = os.path.join(tmp, "brassage_c" + EXE)
compile_c = None
if WIN and shutil.which("cl"):
    compile_c = (["cl", "/nologo", "/O2", "/openmp", src, "/Fe:" + exe_c, "/Fo:" + tmp + os.sep], "MSVC cl /O2")
elif shutil.which("gcc"):
    compile_c = (["gcc", "-O2", "-fopenmp", src, "-o", exe_c], "gcc -O2")
elif shutil.which("clang"):
    compile_c = (["clang", "-O2", src, "-o", exe_c], "clang -O2")
if compile_c:
    print(f"C ({compile_c[1]}) ...", flush=True)
    r = subprocess.run(compile_c[0], capture_output=True, text=True, cwd=tmp)
    if r.returncode == 0 and os.path.exists(exe_c):
        _, r = chrono([exe_c, str(n)])
        p = r.stdout.split()
        if len(p) >= 4:
            somme = int(p[1])
            ok = somme_ref is None or somme == somme_ref
            somme_ref = somme_ref or somme
            ajouter(f"C ({compile_c[1]}), 1 cœur", float(p[2]), ok)
            ajouter(f"C ({compile_c[1]}, OpenMP), tous les cœurs", float(p[3]), ok)
    else:
        print("la compilation du C a échoué :", (r.stdout + r.stderr)[-300:])
else:
    print("pas de compilateur C (ni cl, ni gcc, ni clang) : le C est sauté")

# ------------------------------------------------------------------ vtx forgé, sur le processeur
exe_v = os.path.join(tmp, "brassage_vtx" + EXE)
print("vtx forgé (forge128 -> Rust -> natif) ...", flush=True)
r = subprocess.run([sys.executable, os.path.join(racine, "forge", "forge128.py"), os.path.join(ici, "brassage.vtx"),
                    "-o", exe_v], capture_output=True, text=True)
if r.returncode == 0 and os.path.exists(exe_v):
    for coeurs, nom in (("1", "vtx forgé, 1 cœur"), (None, "vtx forgé, tous les cœurs"),
                        ("carte", "vtx forgé, la boucle sur la carte : le programme entier")):
        e = dict(env)
        if coeurs == "carte":
            e["VTX_TARANIS"] = "1"
        else:
            e["VTX_CARTE"] = "0"
            if coeurs:
                e["VTX_COEURS"] = coeurs
        d, r = chrono([exe_v, str(n)], e)
        try:
            somme = int(r.stdout.strip().split()[-1].rstrip(","))
        except (ValueError, IndexError):
            somme = None
        juste = somme is not None and (somme_ref is None or somme == somme_ref)
        if coeurs == "carte":
            m = re.search(r"tours sur la carte, fenêtre de \d+ mots, ([\d.]+) ms", r.stderr)
            if not m:
                print("la boucle n'est pas allée sur la carte :", r.stderr[-300:])
                continue
            ajouter("vtx forgé, la boucle sur la carte : la carte (monter, calculer, redescendre)", float(m.group(1)), juste,
                    "les mots de 64 bits en deux mots de 32")
        ajouter(nom, d * 1e3, juste, "le programme entier (ranger les mots dans le cube, la somme)")
else:
    print("la forge a échoué :", (r.stdout + r.stderr)[-300:])

# ------------------------------------------------------------------ Lugus émulé et Python : sur une partie
petit = 16384
ref_petit = sum(spirv.brasser_python(i) for i in range(petit))
lugus = os.path.join(bin_rs, "lugus" + EXE)
if os.path.exists(lugus):
    print("vtx sur Lugus émulé (une partie) ...", flush=True)
    d, r = chrono([lugus, os.path.join(ici, "brassage.vtx"), str(petit)])
    try:
        somme = int(r.stdout.strip().split()[-1].rstrip(","))
    except (ValueError, IndexError):
        somme = None
    ajouter("vtx sur Lugus émulé (la machine quaternaire en logiciel)", d * 1e3 * n / petit, somme == ref_petit,
            f"{petit} nombres, ramenés à n")
print("Python (une partie) ...", flush=True)
t = time.perf_counter()
s = sum(spirv.brasser_python(i) for i in range(petit))
ajouter("Python 3, 1 cœur", (time.perf_counter() - t) * 1e3 * n / petit, s == ref_petit, f"{petit} nombres, ramenés à n")

# ------------------------------------------------------------------ la table
lignes.sort(key=lambda l: l[1])
base = next((l[1] for l in lignes if l[0].startswith("vtx sur la carte, le calcul")), lignes[0][1] if lignes else 1)
print()
print(f"{'système':<66} {'temps':>12} {'× la carte':>11}  somme")
for nom, ms, ok, rem in lignes:
    temps = f"{ms:,.1f} ms".replace(",", " ") if ms < 100000 else f"{ms / 1000:,.1f} s".replace(",", " ")
    print(f"{nom:<66} {temps:>12} {ms / base:>11.1f}  {'juste' if ok else 'FAUSSE'}" + (f"   ({rem})" if rem else ""))
print()
print("repère : sur la RTX 3070, le noyau de la sonde (écrit à la main en SPIR-V, sur 32 bits) a calculé environ")
print("10 000 milliards d'opérations par seconde (0.5zj) ; le noyau que la forge écrit depuis vtx calcule en 64 bits")
print("(deux mots de 32 : 3 à 6 opérations pour une), et monte et redescend la fenêtre du cube.")
faux = [l for l in lignes if not l[2]]
shutil.rmtree(tmp, ignore_errors=True)
print("comparaison : toutes les sommes sont justes" if not faux else f"comparaison : {len(faux)} somme(s) fausse(s)")
sys.exit(1 if faux else 0)
