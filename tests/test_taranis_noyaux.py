#!/usr/bin/env python3
"""Taranis, les noyaux : des boucles en segments tirées au hasard (toutes les opérations entières, leurs cas limites,
si, tantque, pour, des appels de fonctions), forgées : chaque boucle part sur la carte graphique (le SPIR-V de
taranis/noyau_vtx.py, par Vulkan ; ici SwiftShader, le Vulkan logiciel), et le programme doit rendre les mêmes mots
que Lugus. Sans Vulkan : sauté (et dit).
    python3 tests/test_taranis_noyaux.py [BOUCLES] [GRAINE]"""
import glob
import os
import random
import subprocess
import sys
import tempfile

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
WIN = os.name == "nt"
NB = int(sys.argv[1]) if len(sys.argv) > 1 else 24
GRAINE = int(sys.argv[2]) if len(sys.argv) > 2 else 2026
rnd = random.Random(GRAINE)
M64 = (1 << 64) - 1
LIMITES = [0, 1, 2, 3, 31, 32, 33, 63, 64, 65, 127, 255, 4294967295, 4294967296, (1 << 63), (1 << 63) - 1, M64, M64 - 1,
           2654435761, 1099511628211]
OPS = ["+", "-", "*", "/", "%", "&", "|", "^", "<<", ">>", "./", ".%", ".>>"]
CMPS = ["==", "!=", "<", "<=", ">", ">=", ".<", ".<=", ".>", ".>="]


def nombre():
    v = rnd.choice(LIMITES) if rnd.random() < 0.6 else rnd.getrandbits(rnd.choice((4, 16, 32, 64)))
    return str(v)


def expr(vars_, p):
    if p <= 0 or rnd.random() < 0.25:
        return rnd.choice(vars_) if rnd.random() < 0.6 else nombre()
    k = rnd.random()
    if k < 0.75:
        return f"({expr(vars_, p - 1)} {rnd.choice(OPS)} {expr(vars_, p - 1)})"
    if k < 0.85:
        return f"({expr(vars_, p - 1)} {rnd.choice(CMPS)} {expr(vars_, p - 1)})"
    if k < 0.92:
        return f"non ({expr(vars_, p - 1)})"
    return f"aide({expr(vars_, p - 1)}, {expr(vars_, p - 1)})"


def cond(vars_):
    return f"{expr(vars_, 2)} {rnd.choice(CMPS)} {expr(vars_, 2)}"


COMPTE = [0]


def unique(nom):
    COMPTE[0] += 1
    return f"{nom}{COMPTE[0]}_"


def corps(vars_, n, profondeur, nom):
    nom = unique(nom)
    lignes = []
    locales = []
    for k in range(n):
        r = rnd.random()
        v = vars_ + locales
        if r < 0.35 or not locales:
            x = f"{nom}{len(locales)}"
            lignes.append(f"soit {x} = {expr(v, 3)};")
            locales.append(x)
        elif r < 0.6:
            lignes.append(f"{rnd.choice(locales)} = {expr(v, 3)};")
        elif r < 0.75 and profondeur > 0:
            a = corps(v, 2, profondeur - 1, nom + "s")
            b = corps(v, 2, profondeur - 1, nom + "n")
            lignes.append(f"si {cond(v)} {{\n{a[0]}\n}} sinon {{\n{b[0]}\n}}")
            locales += []
        elif r < 0.88 and profondeur > 0:
            j = f"{nom}j{k}"
            c = corps(v + [j], 2, profondeur - 1, nom + "p")
            cible = rnd.choice(locales)
            lignes.append(f"pour {j} dans 0..{rnd.randint(0, 9)} {{\n{c[0]}\n{cible} = {cible} + {j} * {nombre()};\n}}")
        elif profondeur > 0:
            t = f"{nom}t{k}"
            lignes.append(f"soit {t} = {rnd.randint(0, 6)};")
            cible = rnd.choice(locales)
            lignes.append(f"tantque {t} > 0 {{\n{cible} = ({cible} ^ {expr(v, 2)}) + {t};\n{t} = {t} - 1;\n}}")
    return "\n".join(lignes), locales


def programme():
    s = ["// machine : lugus", "constante BASE = 50000;",
         "fonction aide(a, b) {", "    soit x = a ^ (b << 7);", "    pour r dans 0..3 { x = x * 6364136223846793005 + r; }",
         "    retour (x >> 11) ^ b;", "}"]
    for k in range(NB):
        lignes, locales = corps(["i", "k"], rnd.randint(2, 6), 2, f"v{k}_")
        res = " ^ ".join(locales) if locales else "i"
        s += [f"fonction f{k}(i, k) {{", lignes, f"    retour {res};", "}"]
    s.append("fonction principal() {")
    s.append("    soit k = entrée();")
    for k in range(NB):
        s.append(f"    pour i dans 0..{rnd.choice((64, 100, 257, 1000))} en segments {{ @2[BASE + {k * 2000} + i] = f{k}(i, k); }}")
    s.append("    soit h = 1469598103934665603;")
    s.append(f"    pour j dans 0..{NB * 2000} {{ h = (h ^ @2[BASE + j]) * 1099511628211; }}")
    s.append("    sortie(h);")
    s.append("}")
    return "\n".join(s)


env = dict(os.environ)
if not WIN and "VK_ICD_FILENAMES" not in env:
    icd = sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux64/vk_swiftshader_icd.json"))
    if icd:
        env["VK_ICD_FILENAMES"] = icd[-1]
src = programme()
tmp = tempfile.mkdtemp(prefix="taranis_noyaux_")
chemin = os.path.join(tmp, "noyaux.vtx")
open(chemin, "w", encoding="utf-8").write(src)
exe = os.path.join(tmp, "noyaux" + (".exe" if WIN else ""))
r = subprocess.run([sys.executable, os.path.join(racine, "forge", "forge128.py"), chemin, "-o", exe],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", env=dict(env, VTX_TARANIS="1"))
refus = [l for l in r.stderr.splitlines() if "reste au processeur" in l]
echecs = []
if r.returncode != 0:
    print("ÉCHEC la forge :", (r.stdout + r.stderr)[-1500:])
    sys.exit(1)
lugus = os.path.join(racine, "vtx-rs", "target", "release", "lugus" + (".exe" if WIN else ""))
attendu = subprocess.run([lugus, chemin, "12345"], capture_output=True, text=True, timeout=1200).stdout.strip()
r = subprocess.run([exe, "12345"], capture_output=True, text=True, encoding="utf-8", errors="replace",
                   env=dict(env, VTX_TARANIS="1"), timeout=1200)
sur_carte = sum(1 for l in r.stderr.splitlines() if "tours sur la carte" in l)
sans = "pas de carte" in r.stderr
print(f"{NB} boucles tirées au hasard (graine {GRAINE}) ; {len(refus)} restées au processeur à la forge ; "
      f"{sur_carte} jouées sur la carte")
for l in refus[:5]:
    print("   ", l)
for l in r.stderr.splitlines():
    if "refuse" in l or "hors de la fenêtre" in l:
        print("   ", l)
if sans:
    print("sauté : pas de Vulkan ici (ni carte, ni SwiftShader)")
    sys.exit(0)
ok = r.stdout.strip() == attendu and attendu != ""
print(("OK   " if ok else "ÉCHEC ") + f"la carte et Lugus : {'les mêmes mots' if ok else r.stdout.strip() + ' contre ' + attendu}")
if not ok:
    open(os.path.join(ici, "taranis_noyaux_echec.vtx"), "w", encoding="utf-8").write(src)
    print("   le programme est gardé dans tests/taranis_noyaux_echec.vtx")
if sur_carte < NB - len(refus):
    print(f"ÉCHEC des boucles compilées pour la carte n'y sont pas allées ({sur_carte} sur {NB - len(refus)})")
    ok = False
print("noyaux : tout est conforme" if ok else "noyaux : écart")
sys.exit(0 if ok else 1)
