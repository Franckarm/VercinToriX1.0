#!/usr/bin/env python3
"""Le vocabulaire étendu (0.61) : les mots tirés de Rust, de ses extensions, d'Arduino, d'UE5 et de Blender, sur Lugus et
sur Dunon. Pour chaque machine, ses deux compilateurs donnent les mêmes mots ; chaque mot rend ce qu'il doit (les
valeurs gardées, et les fonctions de Python, math, pour les flottants) ; Dunon rend ce que rend Lugus (à la précision de
son flottant de 64 bits) ; une fonction du programme qui porte le nom d'un mot garde la main."""
import math
import os
import subprocess
import sys
import tempfile

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
for p in (racine, os.path.join(racine, "spu64"), os.path.join(racine, "spu128")):
    sys.path.insert(0, p)
import vtx64  # noqa: E402

X = ".exe" if os.name == "nt" else ""
BIN = os.path.join(racine, "vtx-rs", "target", "release")
VOC = os.path.join(ici, "vocabulaire")
d = tempfile.mkdtemp()
echecs = 0


def verifier(nom, ok, detail=""):
    global echecs
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok else f" : {detail}"), flush=True)
    echecs += 0 if ok else 1


def jouer(machine, chemin):
    env = dict(os.environ)
    env["VTX_SANS_CLAVIER"] = "1"
    r = subprocess.run([os.path.join(BIN, machine + X), chemin], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=d, timeout=900, env=env)
    return r.stdout + r.stderr


def memes_mots(machine, chemin):
    src = open(chemin, encoding="utf-8").read()
    dossier = os.path.dirname(chemin)
    try:
        m = None   # 0.851 : sur Lugus, un seul compilateur (vtxc128, lugus)
        if machine != "lugus":
            m = vtx64.assembler(vtx64.compiler(src, dossier=dossier))
    except Exception as e:  # noqa: BLE001
        return False, str(e)
    sortie = os.path.join(d, "x.mots")
    r = subprocess.run([os.path.join(BIN, machine + X), "compiler", chemin, sortie], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        return False, r.stdout + r.stderr
    ml = [int(x) for x in open(sortie).read().split(";")[0].split(",") if x.strip()]
    if m is None:
        m = ml
    return m == ml and len(ml) > 0, f"{len(m)} contre {len(ml)}"


def nombre(t):
    try:
        return float(t)
    except ValueError:
        return None


def proches(a, b, rel, absolu=1e-15):
    la, lb = a.split("\n"), b.split("\n")
    if len(la) != len(lb):
        return False, f"{len(la)} lignes contre {len(lb)}"
    for x, y in zip(la, lb):
        tx, ty = x.split(" "), y.split(" ")
        if len(tx) != len(ty):
            return False, f"« {x} » contre « {y} »"
        for u, v in zip(tx, ty):
            if u == v:
                continue
            fu, fv = nombre(u), nombre(v)
            if fu is None or fv is None or abs(fu - fv) > max(absolu, rel * max(abs(fu), abs(fv))):
                return False, f"« {x} » contre « {y} »"
    return True, ""


for machine, fichiers in (("lugus", ("commun", "variantes", "valeurs")), ("vtx64", ("commun", "dunon"))):
    nom_m = "Lugus" if machine == "lugus" else "Dunon"
    for f in fichiers:
        ok, det = memes_mots(machine, os.path.join(VOC, f + ".vtx"))
        verifier(f"{nom_m}, {f}.vtx : les deux compilateurs donnent les mêmes mots", ok, det)

attendu = open(os.path.join(VOC, "commun.attendu"), encoding="utf-8").read()
sortie_l = jouer("lugus", os.path.join(VOC, "commun.vtx"))
verifier("Lugus : chaque mot rend la valeur gardée (plus de 190 mots, 113 lignes)", sortie_l == attendu,
         next((f"« {a} » au lieu de « {b} »" for a, b in zip(sortie_l.split("\n"), attendu.split("\n")) if a != b), ""))
sortie_d = jouer("vtx64", os.path.join(VOC, "commun.vtx"))
# 0.833 : l'entier de Lugus a 128 bits, celui de Dunon 64 : Dunon a son attendu (les entiers à 64 bits)
ok, det = proches(sortie_d, open(os.path.join(VOC, "commun64.attendu"), encoding="utf-8").read(), 1e-13)
verifier("Dunon : le même programme rend ce qu'il rendait (à 10⁻¹³ près : son flottant a 52 bits ; ses entiers de 64 bits)", ok, det)

# les flottants, contre la bibliothèque de Python (à la précision du flottant de 64 bits de Python)
lignes = {l.split(" ")[0]: [nombre(t) for t in l.split(" ")[1:]] for l in sortie_l.split("\n") if l}
REF = {
    "racine_cubique": [3.0, -2.0, 2 ** (1 / 3)],
    "hypotenuse": [5.0, math.sqrt(2)],
    "logarithmes": [3.0, 3.0, 4.0, math.log2(10)],
    "hyperboliques": [math.sinh(1), math.sinh(0.1), math.cosh(1), math.tanh(0.5), 1.0],
    "arghyp": [math.asinh(1), math.asinh(0.2), math.acosh(2), math.atanh(0.5), math.atanh(0.25)],
    "degres": [180.0, math.pi / 2],
    "scalaire": [32.0, 5.0, 14.0, math.sqrt(27)],
    "angle": [math.pi / 2, None],
    "quaternion": [math.cos(math.pi / 4), 0.0, 0.0, math.sin(math.pi / 4)],
    "q_slerp": [math.cos(math.pi / 8), 0.0, 0.0, math.sin(math.pi / 8)],
    "srgb": [((0.5 + 0.055) / 1.055) ** 2.4, 0.5, 1.0],
    "pas_lisse": [0.5, 0.15625, 0.103515625],
    "lire_flottant": [3.25, -150.0, None, None, 0.002],
}
faux = []
for cle, vals in REF.items():
    lu = lignes.get(cle, [])
    for k, v in enumerate(vals):
        if v is None:
            continue
        if k >= len(lu) or lu[k] is None or abs(lu[k] - v) > 4e-15 * max(1.0, abs(v)):
            faux.append(f"{cle}[{k}] : {lu[k] if k < len(lu) else '?'} au lieu de {v!r}")
verifier("les flottants comme math de Python (racine cubique, hypoténuse, logarithmes, hyperboliques, slerp, sRGB…)",
         not faux, "; ".join(faux))

for f, machine in (("variantes", "lugus"), ("valeurs", "lugus"), ("dunon", "vtx64")):
    att = open(os.path.join(VOC, f + ".attendu"), encoding="utf-8").read()
    s = jouer(machine, os.path.join(VOC, f + ".vtx"))
    quoi = {"variantes": "les variantes : 64 et 32 bits, entiers de 32 et de 128 bits",
            "valeurs": "les mots qui prennent une fonction (transformer, filtrer, plier, trier_par…)",
            "dunon": "Dunon : le vocabulaire des nombres de 0.6za et les variantes de 32 bits"}[f]
    verifier(quoi, s == att, repr(s[:300]))

# une fonction du programme qui porte le nom d'un mot garde la main, sur les deux machines
PROPRE = os.path.join(d, "propre.vtx")
open(PROPRE, "w", encoding="utf-8").write(
    "fonction carre(x) { retour x + 1; }\n"
    "fonction premier(t) { retour 99; }\n"
    "fonction distance(a, b) { retour a * 10 + b; }\n"
    "fonction principal() { afficher(carre(5), premier([1, 2]), distance(3, 4), racine_entiere(81)); }\n")
for machine, nom_m in (("lugus", "Lugus"), ("vtx64", "Dunon")):
    ok, det = memes_mots(machine, PROPRE)
    s = jouer(machine, PROPRE)
    verifier(f"{nom_m} : ses propres carre, premier, distance gardent leur sens ; le vocabulaire reste là (9)",
             ok and s.strip() == "6 99 34 9", det + " " + s)

import shutil  # noqa: E402
shutil.rmtree(d, ignore_errors=True)
print("le vocabulaire étendu : " + ("tout est conforme" if echecs == 0 else f"{echecs} écart(s)"))
sys.exit(1 if echecs else 0)
