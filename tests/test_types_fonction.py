#!/usr/bin/env python3
"""Le type d'une fonction passée en valeur (0.6x) : « fonction(T1, T2): R ». Le compilateur vérifie qu'une fonction
nommée a bien ce type, compte les arguments d'un appel par valeur et convertit chacun ; un appel rend le type écrit
(un texte reste un texte). vtxc128 seul (0.851) : compilé, et les refus."""
import os
import subprocess
import sys
import tempfile

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, racine)
sys.path.insert(0, os.path.join(racine, "chimie"))
import adn  # noqa: E402

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
    # 0.851 : un seul compilateur : ce qui reste des « mêmes mots », vtxc128 (lugus) le compile
    r = lugus("compiler", chemin, os.path.join(d, "x.mots"))
    if r.returncode != 0:
        return False, r.stdout + r.stderr
    ml = [int(x) for x in open(os.path.join(d, "x.mots")).read().split(";")[0].split(",") if x]
    return len(ml) > 0, f"{len(ml)} mots"



TF = os.path.join(racine, "exemples128", "types_fonction.vtx")
ok, det = memes_mots(TF)
verifier("types_fonction.vtx : compilé par vtxc128", ok, det)
r = lugus(TF)
verifier("appliquer, plier, un flottant, une fonction rendue, un texte, une structure",
         r.stdout.split("\n")[:6] == ["49 16", "1.5", "25", "Par Toutatis !", "4", ""], r.stdout + r.stderr)

# 0.849 : un type de fonction dans un type de fonction
FI = os.path.join(racine, "exemples128", "fonctions_imbriquees.vtx")
ok, det = memes_mots(FI)
verifier("fonctions_imbriquees.vtx : les mêmes mots par les deux compilateurs", ok, det)
r = lugus(FI)
verifier("une fonction qui reçoit une fonction qui reçoit une fonction : 7, puis 42", r.stdout.split("\n")[:2] == ["7", "42"],
         r.stdout + r.stderr)

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
    # 0.849 : un type de fonction dans un type de fonction est permis ; il est vérifié comme les autres
    ("une fonction qui rend un entier là où l'on attend une fonction qui rend une fonction",
     "soit g: fonction(entier): fonction(entier) = carre;",
     "ligne 6 : « carre » ne convient pas à fonction(entier): fonction(entier): entier : elle est fonction(entier): entier"),
]
for nom, ligne, attendu in REFUS:
    chemin = os.path.join(d, "refus.vtx")
    open(chemin, "w", encoding="utf-8").write(TETE + " " + ligne + "\n}\n")
    rl = lugus("compiler", chemin, os.path.join(d, "x.mots"))
    verifier(f"refus : {nom} (vtxc128, le message attendu)",
             attendu in rl.stdout + rl.stderr and rl.returncode != 0, rl.stdout + rl.stderr)

# sans type écrit, rien ne change : un appel par valeur reste libre (0.6w)
LIBRE = os.path.join(d, "libre.vtx")
open(LIBRE, "w", encoding="utf-8").write("fonction carre(x) { retour x * x; }\nfonction app(f, x) { retour f(x); }\n"
                                         "fonction principal() { afficher(app(carre, 6)); }\n")
ok, det = memes_mots(LIBRE)
r = lugus(LIBRE)
verifier("sans type écrit : l'appel par valeur de 0.6w, inchangé", ok and r.stdout.startswith("36"), det + r.stdout)

# 0.6y : la promesse dans le type
PT = os.path.join(racine, "exemples128", "promesse_type.vtx")
ok, det = memes_mots(PT)
verifier("promesse_type.vtx : les mêmes mots par les deux compilateurs", ok, det)
r = lugus(PT)
verifier("des promesses tenues par des fonctions passées en valeur : 49 16 42 16", r.stdout.startswith("49 16 42 16"),
         r.stdout + r.stderr)
texte = open(PT, encoding="utf-8").read()
mts, mols, _, noms = adn.molecules_isotopes_noms(texte, os.path.dirname(PT))
verifier("le juge de référence (Python) : rien à redire", adn.promesses(mts, mols, noms, texte.split("\n")) == [])

TETE2 = """fonction carre(x) touche rien { retour x * x; }
fonction lire(i) touche lecture { retour @3[100 + i]; }
fonction parler(x) { afficher(x); retour x; }
fonction appliquer(f: fonction(entier): entier touche rien, x) touche rien { retour f(x); }
fonction principal() {
"""
REFUS2 = [
    ("une fonction qui ne promet rien", "afficher(appliquer(parler, 7));",
     "ligne 6 : « parler » ne convient pas à fonction(entier): entier touche rien : elle ne promet rien"),
    ("une fonction qui promet moins", "afficher(appliquer(lire, 7));",
     "ligne 6 : « lire » ne convient pas à fonction(entier): entier touche rien : elle promet seulement « touche "
     "lecture »"),
    ("un entier là où l'on a promis", "soit n = 5; afficher(appliquer(n, 7));",
     "ligne 6 : un entier ne va pas là où l'on attend fonction(entier): entier touche rien : seule une fonction qui "
     "le promet y va"),
    ("une valeur typée qui promet moins", "soit g: fonction(entier): entier touche lecture = lire; afficher(appliquer(g, 1));",
     "ligne 6 : une valeur de type fonction(entier): entier touche lecture ne va pas là où l'on attend "
     "fonction(entier): entier touche rien : elle promet moins"),
]
for nom, ligne, attendu in REFUS2:
    chemin = os.path.join(d, "refus2.vtx")
    open(chemin, "w", encoding="utf-8").write(TETE2 + " " + ligne + "\n}\n")
    rl = lugus("compiler", chemin, os.path.join(d, "x.mots"))
    verifier(f"refus : {nom} (vtxc128, le message attendu)",
             attendu in rl.stdout + rl.stderr and rl.returncode != 0, rl.stdout + rl.stderr)

# le juge croit la promesse du type, et pas plus : une fonction qui promet rien ne peut appeler une valeur qui lit
JUGE = os.path.join(d, "juge.vtx")
tj = ("fonction lire(i) touche lecture { retour @3[100 + i]; }\n"
      "fonction voir(f: fonction(entier): entier touche lecture, x) touche rien { retour f(x); }\n"
      "fonction principal() { afficher(voir(lire, 1)); }\n")
open(JUGE, "w", encoding="utf-8").write(tj)
rl = lugus(JUGE)
msgs = [l for l in (rl.stdout + rl.stderr).split("\n") if l.startswith("promesse")]
mts, mols, _, noms = adn.molecules_isotopes_noms(tj, d)
ref = adn.promesses(mts, mols, noms, tj.split("\n"))
verifier("une promesse plus forte que le type : refusée, « elle lit la mémoire : par __appeler_lecture », comme la "
         "référence", msgs == ref and len(msgs) == 1 and "elle lit la mémoire : par __appeler_lecture" in msgs[0],
         repr((msgs, ref)))

import shutil  # noqa: E402
shutil.rmtree(d, ignore_errors=True)
print("les types de fonction : " + ("tout est conforme" if echecs == 0 else f"{echecs} écart(s)"))
sys.exit(1 if echecs else 0)
