#!/usr/bin/env python3
"""Les fonctions passées en valeur (0.6w) : un nom de fonction sans parenthèses est sa valeur ; f(…) par une variable
qui porte une fonction est un appel par valeur (le trampoline __appeler). vtx128.py et vtxc128 : les mêmes mots ; la
carte et le juge des promesses voient où mène un appel par valeur (le monde, par prudence) ; Gobannos le traduit."""
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


EX = os.path.join(racine, "exemples128", "valeurs.vtx")
MELE = os.path.join(ici, "valeurs_mele.vtx")
for nom, chemin in (("exemples128/valeurs.vtx", EX), ("le mélange", MELE)):
    ok, det = memes_mots(chemin)
    verifier(f"{nom} : vtxc128 et vtx128.py donnent les mêmes mots", ok, det)

r = lugus(EX)
verifier("l'exemple : pour_chacun, plier, une fonction qui rend une fonction, une structure qui porte une fonction",
         r.stdout.split("\n")[:6] == ["1 4 9 16 25 ", "2 4 6 8 10 ", "somme : 15 ; produit : 120", "le choix pour -3 : 20",
                                      "carré de 7 : 49", "double de 7 : 14"], r.stdout + r.stderr)
r = lugus(MELE)
verifier("le mélange : choisir rend une fonction, la récursion par valeur, une fonction du prélude (longueur), "
         "une variable qui ressemble à un nom de fonction, une boucle en segments à côté",
         r.stdout.split("\n")[:5] == ["81 18 1024 256", "factorielle 3628800", "6", "5 25", "132"], r.stdout + r.stderr)

# la promesse : un appel par valeur peut toucher n'importe quoi (le juge le dit) ; une fonction écrite sur une ligne
PROM = """fonction carre(x) touche rien { retour x * x; }
fonction appliquer(f, x) touche rien { retour f(x); }
fonction principal() {
    afficher(appliquer(carre, 6));
}
"""
p = os.path.join(d, "prom.vtx")
open(p, "w", encoding="utf-8").write(PROM)
r = lugus(p)
verifier("une fonction « touche rien » qui appelle par valeur : refusée (le monde, par __appeler)",
         r.returncode != 0 and "promesse rompue : appliquer (ligne 2)" in r.stdout + r.stderr and "36" not in r.stdout,
         r.stdout + r.stderr)
UNE = "fonction parler(x) touche rien { afficher(x); }\nfonction principal() { parler(3); }\n"
p = os.path.join(d, "une.vtx")
open(p, "w", encoding="utf-8").write(UNE)
r = lugus(p)
verifier("une promesse sur une fonction écrite en une ligne (corrigé : l'en-tête s'arrête à l'accolade)",
         r.returncode != 0 and "promesse rompue : parler (ligne 1)" in r.stdout + r.stderr, r.stdout + r.stderr)

# la carte : une fonction passée en valeur a sa molécule, appelée par __appeler
open(os.path.join(d, "ex.vtx"), "w", encoding="utf-8").write(open(EX, encoding="utf-8").read())
r = lugus("carte", "ex.vtx")
bloc = r.stderr[r.stderr.find("carre : une fonction"):].split("\n\n")[0]
verifier("la carte : carre a sa molécule, « appelée par __appeler »", "appelée par __appeler" in bloc, r.stderr[:1500])

# Gobannos : l'appel par valeur traduit (sous Linux, l'exécutable est lancé ; sous Windows aussi)
GOB = os.path.join(racine, "gobannos", "gobannos.vtx")
mots = os.path.join(d, "ex.mots")
# 0.833 : Gobannos traduit les programmes en Dunon (la division de 128 bits n'est pas encore traduite)
open(os.path.join(d, "ex.vtx"), "w", encoding="utf-8").write("dunon;\n" + open(EX, encoding="utf-8").read())
lugus("compiler", os.path.join(d, "ex.vtx"), mots)
exe = os.path.join(d, "ex" + (".exe" if WIN else ".elf"))
r = lugus(GOB, entree=f"{mots}\n{exe}\n{'windows' if WIN else 'linux'}\n")
ok = os.path.exists(exe)
if ok:
    if not WIN:
        os.chmod(exe, 0o755)
    rg = subprocess.run([exe], capture_output=True, timeout=60)
    rl = lugus(os.path.join(d, "ex.vtx"))
    ok = rg.returncode == 0 and rg.stdout.decode("utf-8").replace("\r\n", "\n") == rl.stdout
verifier("Gobannos : l'exemple traduit en exécutable, la même sortie que Lugus", ok, r.stdout[-300:])

import shutil  # noqa: E402
shutil.rmtree(d, ignore_errors=True)
print("les fonctions en valeur : " + ("tout est conforme" if echecs == 0 else f"{echecs} écart(s)"))
sys.exit(1 if echecs else 0)
