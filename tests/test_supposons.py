#!/usr/bin/env python3
"""supposons X parmi [E1, …, En] { CORPS } [retenir R;] (0.6s) : chaque candidat est essayé dans X ; la lecture peut
l'écarter (écarter;) ou le noter (noter E;) ; ce qu'elle écrit en mémoire est défait (une hypothèse, seulement si elle
écrit). X garde le retenu, R dit comment : faux aucun, vrai un seul ou une meilleure note unique, inconnu plusieurs sans
note, variable des ex aequo. vtx128.py et vtxc128 donnent les mêmes mots, et les mêmes refus."""
import os
import subprocess
import sys
import tempfile

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, racine)
import vtx128  # noqa: E402

vtx128.COMPAT_64 = False
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
    try:
        m, _ = vtx128.assembler(vtx128.compiler(texte, dossier=d), True)
        return m, ""
    except vtx128.VtxError as e:
        return None, str(e)


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
verifier("exemples128/supposons.vtx : vtxc128 et vtx128.py donnent les mêmes mots", m_l is not None and m_l == mots_py(texte)[0], err)
r = lugus("ex.vtx")
attendu = ["le meilleur : 8 vrai ; la mémoire : 7", "chat vrai", "ex aequo : 4 variable", "sans note : 4 inconnu",
           "aucun : 4 faux", "5 0 2"]
verifier("l'exemple : le meilleur noté, la mémoire défaite, les quatre verdicts", r.stdout.split("\n")[:6] == attendu,
         r.stdout + r.stderr)
verifier("une fonction « touche rien » qui suppose sans écrire tient sa promesse", "promesse" not in r.stderr, r.stderr)

# 2. le mélange : textes, flottants, boucles, supposons dans supposons, hypothèse dans la lecture, plus de 10 candidats,
#    une fonction utilisateur nommée noter
ecrire("mele.vtx", MELE)
m_l, err = mots_lugus("mele.vtx")
verifier("le mélange : les mêmes mots", m_l is not None and m_l == mots_py(MELE)[0], err)
r = lugus("mele.vtx")
verifier("le mélange : ce qu'il affiche", r.stdout.split("\n")[:6] == ["5", "chat vrai", "4 variable", "1.5 vrai", "1 1 0", "5"],
         r.stdout + r.stderr)

# 3. les refus, les mêmes des deux côtés
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
