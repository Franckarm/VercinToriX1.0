#!/usr/bin/env python3
"""Le vocabulaire des nombres (0.6za) : signe, est_positif, est_negatif, est_nul, est_entier, est_infini, est_su,
partie_entiere, partie_decimale, entre, ecart, borne, arrondi(x, n). Un mot pour les cinq types ; le compilateur choisit
la variante par le type des arguments. vtxc128 seul (0.851) : compilé ; une fonction du programme qui porte le
même nom garde la main."""
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




ATTENDU = "prix arrondi au centime : 12.46 ; à la dizaine : 10.0\npartie entière et décimale : 12.0 0.4566999999999999999999999999999996\n  température -3.5 : positive ? faux gel ? vrai sue ? vrai dans [-1, 3] ? faux\n  température 0.0 : positive ? faux gel ? faux sue ? vrai dans [-1, 3] ? vrai\n  température 2.25 : positive ? vrai gel ? faux sue ? vrai dans [-1, 3] ? vrai\n  température variable : positive ? variable gel ? variable sue ? faux dans [-1, 3] ? variable\nune case jamais écrite : inconnu positive ? inconnu sue ? faux\nentiers : -1 vrai 7 10 vrai\nentier de 128 bits : -1 vrai 1\n64 et 32 bits : -7.0 -0.25 -7.3 1.0 faux\nl'infini : vrai faux 0.0\nun tiers : 1.0 vrai faux 0.0 0.3333333333333333333333333333333333\n"

EX = os.path.join(racine, "exemples128", "nombres.vtx")
ok, det = memes_mots(EX)
verifier("nombres.vtx : compilé par vtxc128", ok, det)
r = lugus(EX)
verifier("nombres.vtx : la sortie attendue (arrondi, parties, états inconnu et variable, cinq types, l'infini)",
         r.stdout == ATTENDU, r.stdout + r.stderr)

PR = os.path.join(ici, "nombres", "proprietes.vtx")
ok, det = memes_mots(PR)
verifier("proprietes.vtx : les mêmes mots", ok, det)
r = lugus(PR)
verifier("161 valeurs, cinq types : partie entière + décimale = x, signe * |x| = x, entre, ecart, borne, arrondi",
         r.stdout.strip() == "161 valeurs, 0 faute(s)", r.stdout + r.stderr)

# un programme qui définit son propre « entre » ou « ecart » le garde : le vocabulaire ne vole pas les noms
PROPRE = os.path.join(d, "propre.vtx")
open(PROPRE, "w", encoding="utf-8").write(
    "fonction entre(a, b, c) { retour a + b + c; }\n"
    "fonction ecart(x: flottant, y: flottant): flottant { retour x * y; }\n"
    "fonction principal() { afficher(entre(1, 2, 3), ecart(2.0, 4.0), signe(0.0 - 2.0)); }\n")
ok, det = memes_mots(PROPRE)
verifier("ses propres entre et ecart : les mêmes mots", ok, det)
r = lugus(PROPRE)
verifier("ses propres entre et ecart : ils gardent leur sens (6 8.0), signe reste du vocabulaire (-1.0)",
         r.stdout.strip() == "6 8.0 -1.0", r.stdout + r.stderr)

import shutil  # noqa: E402
shutil.rmtree(d, ignore_errors=True)
print("le vocabulaire des nombres : " + ("tout est conforme" if echecs == 0 else f"{echecs} écart(s)"))
sys.exit(1 if echecs else 0)
