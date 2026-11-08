#!/usr/bin/env python3
"""L'exécutable de Lugus (0.5zs, vtx exe128 et Ctrl+E d'Ogmios) : la machine, les mots et les cubes sur disque en un seul
fichier. Le .exe, lancé ailleurs, écrit ce qu'écrit « lugus PROG.vtx » ; il lit le clavier ; il pose à côté de lui les
cubes et les fichiers qu'il emporte (jamais par-dessus ceux qui y sont) et les relit comme sur Lugus."""
import os
import shutil
import subprocess
import sys
import tempfile

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
X = ".exe" if os.name == "nt" else ""
BIN = os.path.join(racine, "vtx-rs", "target", "release")
VTX = os.path.join(BIN, "vtx" + X)
LUGUS = os.path.join(BIN, "lugus" + X)
d = tempfile.mkdtemp()
echecs = 0
env = dict(os.environ, VTX_SANS_PAUSE="1")


def verifier(nom, ok, detail=""):
    global echecs
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok else f" : {detail}"))
    echecs += 0 if ok else 1


def lancer(args, entree="", cwd=None):
    r = subprocess.run(args, input=entree, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=cwd,
                       env=env)
    return r.returncode, r.stdout, r.stderr


# 1. un programme qui écrit, compte et rend des sorties : le même texte que lugus
a = os.path.join(d, "a")
os.makedirs(a)
p1 = os.path.join(a, "calcul.vtx")
open(p1, "w", encoding="utf-8").write("""// machine : lugus
fonction principal() {
    soit s = 0;
    pour i dans 0..1000 { s = s + i * i; }
    afficher("somme des carrés :", s, factorielle(10), est_premier(97));
    afficher(inverser_texte("Ogmios"), sinus(0.5));
    sortie(s);
    sortie(entree() + entree());
}
""")
exe1 = os.path.join(d, "calcul" + X)
c, o, e = lancer([VTX, "exe128", p1, exe1])
verifier("vtx exe128 fait l'exécutable", c == 0 and os.path.isfile(exe1), e)
c1, o1, e1 = lancer([LUGUS, p1, "3", "4"])
c2, o2, e2 = lancer([exe1, "3", "4"], cwd=d)
l1 = o1.split("\n", 1)
verifier("l'exécutable écrit ce qu'écrit lugus (le texte, puis les sorties)",
         c1 == c2 == 0 and len(l1) == 2 and o2 == l1[1] + l1[0] + "\n" and "somme des carrés" in o2, f"{o1!r} / {o2!r}")

# 2. le clavier : le loto, deux menus au clavier
loto = os.path.join(racine, "exemples", "premiers", "loto.vtx")
exe2 = os.path.join(d, "loto" + X)
c, o, e = lancer([VTX, "exe128", loto, exe2])
c, o, e = lancer([exe2], "5\n3\n2\n0\n", cwd=d)
grilles = [l for l in o.split("\n") if "grille " in l and "| chance" in l]
verifier("le loto au clavier : trois grilles choisies, puis les chances, puis quitter",
         c == 0 and len(grilles) == 3 and "Au revoir" in o and "grilles possibles" in o, o[-400:] + e)

# 3. les cubes sur disque et un fichier nommé : emportés, posés à côté de l'exécutable, relus
open(os.path.join(a, "ecrire.vtx"), "w", encoding="utf-8").write("""// machine : lugus
fonction principal() {
    pour i dans 0..10 { @[cube_adresse(2, 5, i)] = i * i + 7; }
    afficher("pages rangées :", ranger_cube(2, 5));
}
""")
p3 = os.path.join(a, "lire.vtx")
open(p3, "w", encoding="utf-8").write("""// machine : lugus
fonction principal() {
    soit s = 0;
    pour i dans 0..10 { s = s + @[cube_adresse(2, 5, i)]; }
    afficher("somme lue dans le cube :", s);
    afficher("état du disque :", etat_disque());
    soit c = ouvrir_lecture("notes.txt");
    afficher("première lettre des notes :", lire_car(c));
}
""")
open(os.path.join(a, "notes.txt"), "w", encoding="utf-8").write("Bonjour\n")
lancer([LUGUS, os.path.join(a, "ecrire.vtx")], cwd=a)
c, o, e = lancer([LUGUS, p3], cwd=a)
attendu = o
b = os.path.join(d, "ailleurs")
os.makedirs(b)
exe3 = os.path.join(b, "lire" + X)
c, o, e = lancer([VTX, "exe128", p3, exe3])
verifier("les cubes emportés : le cube, son anti-cube, son ombre et notes.txt",
         c == 0 and "2 cube(s)" not in o and "1 cube(s) sur disque, 4 fichier(s)" in o, o + e)
os.remove(p3)
for f in os.listdir(a):
    os.remove(os.path.join(a, f))
c, o, e = lancer([exe3], cwd=b)
verifier("lancé dans un autre dossier : il pose ses cubes et les relit comme lugus",
         c == 0 and o == attendu and "somme lue dans le cube : 355" in o and "vrai" in o
         and sorted(os.listdir(b)) == sorted(["lire" + X, "cube128-2-5.cub", "anticube128-2-5.cub", "ombre128-2-5.cub", "notes.txt"]),
         f"{o!r} attendu {attendu!r} ; {os.listdir(b)}")
# un fichier changé à côté de l'exécutable n'est pas remplacé par celui qu'il emporte
open(os.path.join(b, "notes.txt"), "w", encoding="utf-8").write("Salut\n")
c, o, e = lancer([exe3], cwd=b)
verifier("un fichier déjà là n'est jamais écrasé", "première lettre des notes : 83" in o, o)

# 4. la taille : la machine et le paquet, rien de plus
taille_socle = os.path.getsize(VTX)
verifier("taille : la machine plus le paquet", os.path.getsize(exe2) > taille_socle and os.path.getsize(exe2) < taille_socle + 200000,
         f"{os.path.getsize(exe2)} pour une machine de {taille_socle}")

# 5. une erreur de compilation est dite, rien n'est écrit
p5 = os.path.join(d, "faux.vtx")
open(p5, "w", encoding="utf-8").write("// machine : lugus\nfonction principal() {\n    soit x = ;\n}\n")
c, o, e = lancer([VTX, "exe128", p5, os.path.join(d, "faux" + X)])
verifier("une erreur de compilation : dite, aucun exécutable", c != 0 and "ligne" in e and not os.path.exists(os.path.join(d, "faux" + X)), e)

shutil.rmtree(d, ignore_errors=True)
print("exécutable de Lugus : " + ("tout est conforme" if echecs == 0 else f"{echecs} échec(s)"))
sys.exit(1 if echecs else 0)
