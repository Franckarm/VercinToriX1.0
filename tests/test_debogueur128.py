#!/usr/bin/env python3
"""Le débogueur de Lugus par les noms : vtxc128 écrit code.sym en pas à pas, l'atelier remonte la pile des appels et
écrit les variables comme le programme les entend. vtx-spu regarder128 montre la même vue que le panneau de l'atelier,
arrêté à une ligne (la n-ième fois)."""
import os
import subprocess
import sys
import tempfile

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
EXE = os.path.join(racine, "vtx-rs", "target", "release", "vtx-spu" + (".exe" if os.name == "nt" else ""))
echecs = 0


def verifier(nom, ok, detail=""):
    global echecs
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok else f" : {detail}"))
    echecs += 0 if ok else 1


PROG = """fonction saluer(nom: texte, fois): texte {
    soit s = "Bonjour " + nom;
    soit poids = 2.5;
    soit grille = [3, 12, 25, 31, 44];
    soit noms = ["Vercingétorix", "Ogmios"];
    soit l: logique = inconnu;
    pour i dans 0..fois {
        s = s + "!";
    }
    retour s;
}

fonction compter(n) {
    si n == 0 {
        retour 0;
    }
    retour 1 + compter(n - 1);
}

fonction principal() {
    soit n = 42;
    soit message = saluer("Lugus", 3);
    afficher(message, compter(3), n);
}
"""
d = tempfile.mkdtemp()
f = os.path.join(d, "essai.vtx")
open(f, "w", encoding="utf-8").write(PROG)


def regarder(ligne, fois=1):
    r = subprocess.run([EXE, "regarder128", f, str(ligne), str(fois)], capture_output=True, text=True, encoding="utf-8")
    return r.stdout + r.stderr


o = regarder(10)
lignes = [l.strip() for l in o.splitlines()]
verifier("la pile : saluer (ligne 10), appelée par principal (ligne 22)",
         "▶ saluer, ligne 10" in lignes and "· principal, ligne 22" in lignes, o)
for attendu in ['nom    = "Lugus"', "fois   = 3", 's      = "Bonjour Lugus!!!"', "poids  = 2.5",
                "grille = [3, 12, 25, 31, 44]", 'noms   = ["Vercingétorix", "Ogmios"]', "l      = inconnu", "i      = 3"]:
    verifier(f"saluer : {attendu}", attendu in lignes, o)
verifier("principal : n = 42, message pas encore donné", "n       = 42" in lignes and "message = (pas encore de texte)" in lignes, o)
o = regarder(8, 2)
verifier("la deuxième fois à la ligne 8 : i = 1, s = \"Bonjour Lugus!\"",
         "i      = 1" in o and 's      = "Bonjour Lugus!"' in o, o)
# la récursion : quatre fois compter dans la pile, chacune avec son n
o = regarder(15, 1)
pile = [l.strip() for l in o.splitlines() if l.strip().startswith(("▶ compter", "· compter"))]
verifier("compter(3) au fond de la récursion : 4 étapes compter dans la pile", len(pile) == 4, o)
ns = [l.strip() for l in o.splitlines() if l.strip().startswith("n =") or l.strip().startswith("n       =")]
verifier("chaque étape garde son n : 0, 1, 2, 3, puis 42 dans principal",
         [x.split("=")[1].strip() for x in ns] == ["0", "1", "2", "3", "42"], o)
# Maj+F8 : sortir de la fonction en cours ; l'on revient dans l'appelante, au milieu de sa ligne
r = subprocess.run([EXE, "regarder128", f, "15", "1", "--sortir"], capture_output=True, text=True, encoding="utf-8")
pile = [l.strip() for l in r.stdout.splitlines() if l.strip().startswith(("▶", "·"))]
verifier("sortir du fond de compter : 3 compter et principal dans la pile",
         pile == ["▶ compter, ligne 17", "· compter, ligne 17", "· compter, ligne 17", "· principal, ligne 23"], r.stdout)
r = subprocess.run([EXE, "regarder128", f, "10", "1", "--sortir"], capture_output=True, text=True, encoding="utf-8")
verifier("sortir de saluer : de retour dans principal, ligne 22, message pas encore rangé",
         "▶ principal, ligne 22" in r.stdout and "message = (pas encore de texte)" in r.stdout, r.stdout)
print("débogueur de Lugus : tout est conforme" if echecs == 0 else f"débogueur de Lugus : {echecs} échec(s)")
sys.exit(1 if echecs else 0)
