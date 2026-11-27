#!/usr/bin/env python3
"""Les promesses (0.6r) : « touche rien | lecture | memoire | monde » dans l'en-tête d'une fonction ou d'une réaction. La
carte constate ce que la fonction touche, elle et ses appels ; une promesse rompue arrête la compilation (et le
rangement), avec le chemin qui la rompt. Le juge est le lecteur d'ADN écrit en vtx ; chimie/adn.py dit les mêmes mots.
vtxc128 accepte (0.851 : un seul compilateur) la promesse sans changer un mot du code, et une fonction qui promet garde sa molécule
(elle n'est pas recopiée en ligne), pour que sa promesse se vérifie à part."""
import os
import subprocess
import sys
import tempfile

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, racine)
sys.path.insert(0, os.path.join(racine, "chimie"))
import adn  # noqa: E402

X = ".exe" if os.name == "nt" else ""
LUGUS = os.path.join(racine, "vtx-rs", "target", "release", "lugus" + X)
VTX = os.path.join(racine, "vtx-rs", "target", "release", "vtx" + X)
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




def mots_lugus(nom):
    r = lugus("compiler", nom, "x.mots")
    if r.returncode != 0:
        return None, r.stderr
    return [int(x) for x in open(os.path.join(d, "x.mots")).read().split(";")[0].split(",") if x], r.stderr


def juge_py(texte):
    mots, mols, _, noms = adn.molecules_isotopes_noms(texte, d)
    return adn.promesses(mots, mols, noms, texte.split("\n"))


if not os.path.exists(LUGUS):
    print("lugus n'est pas construit (cargo build --release dans vtx-rs) : rien n'est vérifié")
    sys.exit(1)

TENU = """// des promesses tenues
fonction somme(n) touche rien {
    soit s = 0;
    pour i dans 0..n {
        s = s + i;
    }
    retour s;
}

fonction double(x) touche rien {
    retour 2 * x;
}

fonction remplir(t, n) touche memoire {
    pour i dans 0..n {
        t[i] = somme(i);
    }
}

fonction lire_case(t, i): entier touche lecture {
    retour t[i];
}

reaction moyenne(a, b) -> m touche rien {
    = (a + b) / 2 -> m
}

fonction parler(x): entier touche monde {
    afficher(x);
    retour x;
}

fonction principal() touche monde {
    soit t = [0, 0, 0, 0];
    remplir(t, 4);
    afficher(lire_case(t, 3), double(4), moyenne(4, 6), parler(7));
}
"""
ecrire("tenu.vtx", TENU)
SANS = TENU.replace(" touche rien", "").replace(" touche memoire", "").replace(" touche lecture", "") \
    .replace(" touche monde", "")
ecrire("sans.vtx", SANS)

# 1. vtxc128 : la promesse acceptée ; le programme tourne
m_l, err = mots_lugus("tenu.vtx")
verifier("des promesses tenues : compilé par vtxc128 (0.851 : un seul compilateur) ; aucune note",
         m_l is not None and "promesse" not in err, err[-400:])
r = lugus("tenu.vtx")
verifier("le programme qui tient ses promesses tourne", r.returncode == 0 and "7" in r.stdout, r.stdout + r.stderr[-300:])
verifier("le juge de référence (Python) : rien à redire", juge_py(TENU) == [], repr(juge_py(TENU)))
m_s, _ = mots_lugus("sans.vtx")
verifier("une fonction qui promet garde sa molécule (double n'est plus recopiée en ligne) ; sans promesse, recopiée",
         m_s is not None
         and "double : une fonction" in lugus("carte", "tenu.vtx").stderr
         and "double : une fonction" not in lugus("carte", "sans.vtx").stderr)

# 2. les promesses rompues : la compilation et le rangement refusés, les messages de la référence, le chemin
ROMPU = TENU.replace("fonction remplir(t, n) touche memoire", "fonction remplir(t, n) touche rien") \
    .replace("fonction double(x) touche rien {\n    retour 2 * x;", "fonction double(x) touche rien {\n    retour parler(2 * x);") \
    .replace("fonction lire_case(t, i): entier touche lecture {\n    retour t[i];",
             "fonction lire_case(t, i): entier touche lecture {\n    t[0] = 1;\n    retour t[i];")
ecrire("rompu.vtx", ROMPU)
attendus = juge_py(ROMPU)
r = lugus("rompu.vtx")
msgs = [l for l in r.stderr.split("\n") if l.startswith("promesse")]
verifier("trois promesses rompues : la compilation est refusée, rien n'est lancé",
         r.returncode != 0 and r.stdout == "" and len(msgs) == 3, r.stdout + r.stderr[-600:])
verifier("le lecteur en vtx et la référence disent les mêmes mots", msgs == attendus, repr((msgs, attendus)))
verifier("le chemin qui rompt la promesse : elle-même, ou d'appel en appel (double → parler → afficher)",
         any("remplir (ligne 14) promet de ne rien toucher, mais elle écrit la mémoire : elle-même" in m for m in msgs)
         and any("double (ligne 10) promet de ne rien toucher, mais elle touche le monde : par parler → afficher" in m
                 for m in msgs)
         and any("lire_case" in m and "promet de lire la mémoire au plus, mais elle écrit la mémoire : elle-même" in m
                 for m in msgs), repr(msgs))
r = lugus("ranger", "rompu.vtx")
verifier("le rangement aussi est refusé : aucun ADN n'est écrit",
         r.returncode != 0 and not os.path.exists(os.path.join(d, "rompu.adn")), r.stderr[-300:])
r = lugus("arnc", "rompu.vtx")
verifier("ni ARNc", r.returncode != 0 and not os.path.exists(os.path.join(d, "rompu.arn")), r.stderr[-300:])

# 3. la carte montre la promesse et dit qu'elle est tenue ; la paillasse d'Ogmios aussi
r = lugus("carte", "tenu.vtx")
verifier("lugus carte : la promesse dans la face des promesses, tenue",
         "ses promesses     : ne rien toucher (tenue)" in r.stderr
         and "ses promesses     : ne pas toucher le monde (tenue)" in r.stderr
         and "ses promesses     : lire la mémoire au plus (tenue)" in r.stderr
         and "ses promesses     : dit qu'elle touche le monde" in r.stderr, r.stderr[-1200:])
lugus("ranger", "tenu.vtx")
ecrire("g.txt", "choisir somme\nexplique\nchoisir moyenne\nexplique\n")
r = subprocess.run([VTX, "paillasse", os.path.join(d, "tenu.vtx"), "--faces", os.path.join(d, "tenu.adn"), "--gestes",
                    os.path.join(d, "g.txt")], capture_output=True, text=True, encoding="utf-8", errors="replace")
verifier("Ogmios : la paillasse montre la promesse tenue, d'une fonction et d'une réaction",
         r.stdout.count("ne rien toucher (tenue)") >= 2, r.stdout[-800:])

# 4. une promesse mal écrite : refusée
MAL = TENU.replace("fonction double(x) touche rien", "fonction double(x) touche partout")
ecrire("mal.vtx", MAL)
m_m, err = mots_lugus("mal.vtx")
verifier("« touche partout » : refusé par vtxc128",
         m_m is None and "après « touche »" in err, err[-300:])

# 5. sans promesse, rien ne change : les exemples de Lugus compilent comme avant, sans juge (pas de note)
for nom in ("chute", "panel", "codon"):
    texte = open(os.path.join(racine, "exemples128", nom + ".vtx"), encoding="utf-8").read()
    verifier(f"{nom} : sans promesse, pas de juge (a_des_promesses faux)",
             not any(l.startswith(("fonction ", "reaction ")) and " touche " in l[l.rfind(")"):]
                     for l in texte.split("\n") if ")" in l))

import shutil  # noqa: E402
shutil.rmtree(d, ignore_errors=True)
print("les promesses : " + ("tout est conforme" if echecs == 0 else f"{echecs} écart(s)"))
sys.exit(1 if echecs else 0)
