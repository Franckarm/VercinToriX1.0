#!/usr/bin/env python3
"""Le type d'une fonction passée en valeur (0.6x) : « fonction(T1, T2): R ». Le compilateur vérifie qu'une fonction
nommée a bien ce type, compte les arguments d'un appel par valeur et convertit chacun ; un appel rend le type écrit
(un texte reste un texte). vtx128.py et vtxc128 : les mêmes mots, et les mêmes refus."""
import os
import subprocess
import sys
import tempfile

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, racine)
import vtx128  # noqa: E402

vtx128.COMPAT_64 = False
WIN = os.name == "nt"
X = ".exe" if WIN else ""
LUGUS = os.path.join(racine, "vtx-rs", "target", "release", "lugus" + X)
d = tempfile.mkdtemp()
echecs = 0


def verifier(nom, ok, detail=""):
    global echecs
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok else f" : {detail}"), flush=True)
    echecs += 0 if ok else 1


def lugus(*args, entree=None):
    env = dict(os.environ)
    if entree is None:
        env["VTX_SANS_CLAVIER"] = "1"
    return subprocess.run([LUGUS, *args], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=d,
                          input=entree or "", timeout=600, env=env)


def memes_mots(chemin):
    texte = open(chemin, encoding="utf-8").read()
    try:
        m, _ = vtx128.assembler(vtx128.compiler(texte, dossier=os.path.dirname(chemin)), True)
    except vtx128.VtxError as e:
        return False, str(e)
    r = lugus("compiler", chemin, os.path.join(d, "x.mots"))
    if r.returncode != 0:
        return False, r.stdout + r.stderr
    ml = [int(x) for x in open(os.path.join(d, "x.mots")).read().split(";")[0].split(",") if x]
    return m == ml, f"{len(m)} contre {len(ml)}"



TF = os.path.join(racine, "exemples128", "types_fonction.vtx")
ok, det = memes_mots(TF)
verifier("types_fonction.vtx : vtxc128 et vtx128.py donnent les mêmes mots", ok, det)
r = lugus(TF)
verifier("appliquer, plier, un flottant, une fonction rendue, un texte, une structure",
         r.stdout.split("\n")[:6] == ["49 16", "1.5", "25", "Par Toutatis !", "4", ""], r.stdout + r.stderr)

TETE = """fonction carre(x) { retour x * x; }
fonction plus(a, b) { retour a + b; }
fonction moitie(x: flottant): flottant { retour x / 2.0; }
fonction appliquer(f: fonction(entier): entier, x) { retour f(x); }
fonction principal() {
"""
REFUS = [
    ("une fonction à deux paramètres là où l'on en attend un", "afficher(appliquer(plus, 7));",
     "ligne 6 : « plus » ne convient pas à fonction(entier): entier : elle est fonction(entier, entier): entier"),
    ("une fonction de flottants là où l'on attend des entiers", "soit g: fonction(entier): entier = moitie;",
     "ligne 6 : « moitie » ne convient pas à fonction(entier): entier : elle est fonction(flottant): flottant"),
    ("trop d'arguments à un appel par valeur", "soit g: fonction(entier): entier = carre; afficher(g(1, 2));",
     "ligne 6 : « g » (fonction(entier): entier) attend 1 argument(s), pas 2"),
    ("un type de fonction dans un type de fonction", "soit g: fonction(entier): fonction(entier) = carre;",
     "ligne 6 : un type de fonction dans un type de fonction : pas encore"),
]
for nom, ligne, attendu in REFUS:
    chemin = os.path.join(d, "refus.vtx")
    open(chemin, "w", encoding="utf-8").write(TETE + " " + ligne + "\n}\n")
    try:
        vtx128.compiler(open(chemin, encoding="utf-8").read(), dossier=d)
        mp = "(accepté)"
    except vtx128.VtxError as e:
        mp = str(e)
    rl = lugus("compiler", chemin, os.path.join(d, "x.mots"))
    verifier(f"refus : {nom} (les deux compilateurs, le même message)",
             attendu in mp and attendu in rl.stdout + rl.stderr and rl.returncode != 0, mp + " / " + rl.stdout + rl.stderr)

# sans type écrit, rien ne change : un appel par valeur reste libre (0.6w)
LIBRE = os.path.join(d, "libre.vtx")
open(LIBRE, "w", encoding="utf-8").write("fonction carre(x) { retour x * x; }\nfonction app(f, x) { retour f(x); }\n"
                                         "fonction principal() { afficher(app(carre, 6)); }\n")
ok, det = memes_mots(LIBRE)
r = lugus(LIBRE)
verifier("sans type écrit : l'appel par valeur de 0.6w, inchangé", ok and r.stdout.startswith("36"), det + r.stdout)

import shutil  # noqa: E402
shutil.rmtree(d, ignore_errors=True)
print("les types de fonction : " + ("tout est conforme" if echecs == 0 else f"{echecs} écart(s)"))
sys.exit(1 if echecs else 0)
