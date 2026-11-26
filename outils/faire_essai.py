"""0.848 : écrit essai-VERSION.bat depuis outils/essai_modele.bat (CRLF, ASCII, sans accents) et le vérifie.

    python3 outils/faire_essai.py 0.848 "le titre (ASCII)" [FICHIER_EXTRA] -o DOSSIER

Vérifié : ASCII seulement, fins de ligne CRLF, chaque « call :x » et « goto :x » a son étiquette, les « ( » et « ) »
s'équilibrent sur chaque ligne de commande, le zip et le journal portent la version."""
import os
import re
import sys

ici = os.path.dirname(os.path.abspath(__file__))
args = sys.argv[1:]
sortie = "."
if "-o" in args:
    i = args.index("-o")
    sortie = args[i + 1]
    del args[i:i + 2]
v, titre = args[0], args[1]
extra = open(args[2], encoding="ascii").read() if len(args) > 2 else ""
t = open(os.path.join(ici, "essai_modele.bat"), encoding="ascii").read()
t = t.replace("@V@", v).replace("@TITRE@", titre).replace("@EXTRA@", extra.rstrip("\n"))
t = t.replace("\r\n", "\n")
erreurs = []
try:
    t.encode("ascii")
except UnicodeEncodeError as e:
    erreurs.append(f"un caractère hors ASCII : {e}")
etiquettes = set(re.findall(r"^:(\w+)", t, re.M))
for cible in re.findall(r"(?:call|goto)\s+:(\w+)", t, re.I):
    if cible.lower() != "eof" and cible not in etiquettes:
        erreurs.append(f"l'étiquette « :{cible} » manque")
for n, l in enumerate(t.split("\n"), 1):
    if l.lower().startswith("rem") or l.startswith("echo"):
        continue
    if l.count("(") != l.count(")") and "for /f" not in l:
        erreurs.append(f"ligne {n} : parenthèses déséquilibrées")
if "@" in t.replace("@echo off", "").replace("@(", ""):
    erreurs.append("un « @…@ » n'est pas remplacé")
if erreurs:
    print("\n".join(erreurs))
    sys.exit(1)
f = os.path.join(sortie, f"essai-{v}.bat")
open(f, "w", encoding="ascii", newline="\r\n").write(t)
print(f"{f} : écrit et vérifié ({t.count(chr(10))} lignes)")
