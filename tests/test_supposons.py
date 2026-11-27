#!/usr/bin/env python3
"""supposons X parmi [E1, …, En] { CORPS } [retenir R;] (0.6s) : chaque candidat est essayé dans X ; la lecture peut
l'écarter (écarter;) ou le noter (noter E;) ; ce qu'elle écrit en mémoire est défait (une hypothèse, seulement si elle
écrit). X garde le retenu, R dit comment : faux aucun, vrai un seul ou une meilleure note unique, inconnu plusieurs sans
note, variable des ex aequo. vtxc128 seul les compile et les refuse (0.851)."""
import os
import subprocess
import sys
import tempfile

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, racine)
from un_compilateur import compiler_texte  # noqa: E402  (0.851 : un seul compilateur)

X = ".exe" if os.name == "nt" else ""
LUGUS = os.path.join(racine, "vtx-rs", "target", "release", "lugus" + X)
d = tempfile.mkdtemp()
echecs = 0


def verifier(nom, ok, detail=""):
    global echecs
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok else f" : {detail}"), flush=True)
    echecs += 0 if ok else 1


def lugus(*args):
    return subprocess.run([LUGUS, *args], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=d,
                          timeout=600)


def ecrire(nom, texte):
    open(os.path.join(d, nom), "w", encoding="utf-8").write(texte)


def mots_py(texte):
    # 0.851 : un seul compilateur : vtxc128 (lugus) fait ce que faisait vtx128.py
    m, msg = compiler_texte(texte, dossier=d)
    return m, ("" if m is not None else msg)


def mots_lugus(nom):
    r = lugus("compiler", nom, "x.mots")
    if r.returncode != 0:
        return None, r.stdout + r.stderr
    return [int(x) for x in open(os.path.join(d, "x.mots")).read().split(";")[0].split(",") if x], ""


MELE = """fonction noter(a) { retour a + 1; }
fonction cout(t) {
    soit s = 0;
    pour i dans 0..longueur(t) { s = s + car(t, i); }
    retour s;
}
fonction principal() {
    soit k0 = noter(4);
    afficher(k0);
    supposons mot parmi ["chat", "chien", "loup"] {
        noter 0 - cout(mot);
    } retenir r;
    afficher(mot, r);
    supposons a parmi [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12] {
        pour j dans 0..3 {
            si j == 2 && a % 2 == 1 { ecarter; }
        }
        si a > 9 { ecarter; }
        supposons b parmi [a, a * 2] {
            si b > 8 { écarter; }
            noter b;
        } retenir rb;
        selon rb {
            vrai { noter b; }
            autre { ecarter; }
        }
    } retenir ra;
    afficher(a, ra);
    supposons p parmi [2.5, 1.5] { si p > 2.0 { ecarter; } } retenir rp;
    afficher(p, rp);
    @3[200] = 1;
    supposons q parmi [1, 2] {
        hypothèse { @3[200] = 50; valider; }
        @3[201] = q;
    }
    afficher(q, @3[200], @3[201]);
    supposons u parmi [5] { }
    afficher(u);
}
"""

# 1. l'exemple de Lugus : les mêmes mots, et ce qu'il affiche
texte = open(os.path.join(racine, "exemples128", "supposons.vtx"), encoding="utf-8").read()
ecrire("ex.vtx", texte)
m_l, err = mots_lugus("ex.vtx")
verifier("exemples128/supposons.vtx : compilé par vtxc128", m_l is not None, err)
r = lugus("ex.vtx")
attendu = ["le meilleur : 8 vrai ; la mémoire : 7", "chat vrai", "ex aequo : 4 variable", "sans note : 4 inconnu",
           "aucun : 4 faux", "5 0 2", "gardé : 80 vrai", "ex aequo, rien n'est fait : 4 variable"]
verifier("l'exemple : le meilleur noté, la mémoire défaite, les quatre verdicts", r.stdout.split("\n")[:8] == attendu,
         r.stdout + r.stderr)
verifier("une fonction « touche rien » qui suppose sans écrire tient sa promesse", "promesse" not in r.stderr, r.stderr)

# 2. le mélange : textes, flottants, boucles, supposons dans supposons, hypothèse dans la lecture, plus de 10 candidats,
#    une fonction utilisateur nommée noter
ecrire("mele.vtx", MELE)
m_l, err = mots_lugus("mele.vtx")
verifier("le mélange : compilé par vtxc128", m_l is not None, err)
r = lugus("mele.vtx")
verifier("le mélange : ce qu'il affiche", r.stdout.split("\n")[:6] == ["5", "chat vrai", "4 variable", "1.5 vrai", "1 1 0", "5"],
         r.stdout + r.stderr)

# 3. les contrats d'une lecture (0.6t) : « exige » écarte le candidat qui ne le tient pas
CONTRAT = """fonction principal() {
    supposons n parmi [12, 7, 9, 15, 4] {
        exige n % 3 == 0;
        exige n > 5 && n < 14;
        noter n;
    } retenir r;
    afficher(n, r);
    supposons m parmi [1, 2] { exige m > 5; } retenir rm;
    afficher(m, rm);
    soit exige = 3;
    afficher(exige);
}
"""
ecrire("contrat.vtx", CONTRAT)
m_l, err = mots_lugus("contrat.vtx")
verifier("exige dans une lecture : compilé par vtxc128", m_l is not None, err)
r = lugus("contrat.vtx")
verifier("exige écarte : 12 retenu (9 aussi tient, moins bien noté) ; aucun ne tient : faux ; hors d'une lecture, exige est un nom",
         r.stdout.split("\n")[:3] == ["12 vrai", "1 faux", "3"], r.stdout + r.stderr)

# 3 bis. retenir r alors { … } sinon { … } (0.6u) : l'action du choix, jouée une fois, si le verdict est vrai
ALORS = open(os.path.join(ici, "supposons_alors.vtx"), encoding="utf-8").read()
ecrire("alors.vtx", ALORS)
m_l, err = mots_lugus("alors.vtx")
verifier("alors : compilé par vtxc128", m_l is not None, err)
r = lugus("alors.vtx")
verifier("alors : joué une fois pour le retenu (la lecture défaite, l'action gardée) ; sinon pour des ex aequo ; "
         "sans retenir ; « alors » reste un nom ailleurs",
         r.stdout.split("\n")[:5] == ["fait pour 8", "80 vrai", "pas sûr : 4 variable", "seul : 7", "3"], r.stdout + r.stderr)

# 4. la carte parle comme le texte : les rouages de l'hypothèse ne sont pas des branches, l'exige d'une lecture n'est pas
#    une promesse de la fonction
r = lugus("carte", "ex.vtx")
bloc_p = r.stderr[r.stderr.find("principal : une fonction"):].split("\n\n")[0]
bloc_d = r.stderr[r.stderr.find("diviseur : une fonction"):].split("\n\n")[0]
verifier("la carte : principal « suppose », sans les rouages __hyp_ dans ses branches",
         "suppose (supposons ou hypothèse" in bloc_p and "__hyp_" not in bloc_p, bloc_p)
verifier("la carte : l'exige d'une lecture n'est pas compté dans les promesses de diviseur",
         "ses promesses     : ne rien toucher (tenue)" in bloc_d, bloc_d)
VTX = os.path.join(racine, "vtx-rs", "target", "release", "vtx" + X)
lugus("ranger", "ex.vtx")
open(os.path.join(d, "g.txt"), "w").write("choisir principal\nexplique\n")
r = subprocess.run([VTX, "paillasse", os.path.join(d, "ex.vtx"), "--faces", os.path.join(d, "ex.adn"),
                    "--gestes", os.path.join(d, "g.txt")], capture_output=True, text=True, encoding="utf-8", errors="replace")
verifier("Ogmios : les branches de principal disent « suppose », sans les rouages",
         "Ses branches : appelle cout, diviseur" in r.stdout and "suppose (supposons" in r.stdout and "__hyp_" not in r.stdout,
         r.stdout[-1200:] + r.stderr[-300:])

# 5. les refus, les mêmes des deux côtés
REFUS = [("ecarter;", "écarter"),
         ("supposons x parmi [1] { arrêter; }", "supposons"),
         ("supposons x parmi [1] { retour; }", "supposons"),
         ("supposons x parmi [1] { annuler; }", "hypothèse"),
         ("soit x = 3;\n supposons x parmi [1, 2] { }", "déjà déclarée")]
for i, (corps, mot) in enumerate(REFUS):
    t = "fonction principal() {\n " + corps + "\n}\n"
    ecrire(f"r{i}.vtx", t)
    m_l, err = mots_lugus(f"r{i}.vtx")
    m_p, err_p = mots_py(t)
    verifier(f"refus : {corps.splitlines()[-1].strip()}", m_l is None and m_p is None and mot in err and mot in err_p,
             err[-200:] + " / " + err_p)

import shutil  # noqa: E402
shutil.rmtree(d, ignore_errors=True)
print("supposons : " + ("tout est conforme" if echecs == 0 else f"{echecs} écart(s)"))
sys.exit(1 if echecs else 0)
