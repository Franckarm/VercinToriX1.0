#!/usr/bin/env python3
"""Vérifie l'installation de vtx : tests du langage, puis les tests complémentaires, puis la conformité des machines
Rust et JavaScript si cargo et node sont installés.
Utilisation : python3 verifier.py            (rapide : moins de tirages aléatoires, sans les grands volumes)
              python3 verifier.py --complet  (tout, plusieurs dizaines de minutes)"""
import os
import shutil
import subprocess
import sys

ici = os.path.dirname(os.path.abspath(__file__))
# Windows : sans cela, les sorties capturées sont encodées en cp1252, qui ne connaît pas « → », « ³ » ou « ≥ ».
COMPLET = "--complet" in sys.argv
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1", VTX_RAPIDE="0" if COMPLET else "1")
TEXTE = dict(capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENV)
try:
    sys.stdout.reconfigure(errors="replace")
except (AttributeError, ValueError):
    pass
etapes = [
    ("tests du langage", [sys.executable, "vtx.py", "test"]),
    ("débogueur", [sys.executable, os.path.join("debogueur", "test_debogueur.py")]),
    ("partition des tâches", [sys.executable, os.path.join("partition", "test_partition.py")]),
    ("logique à quatre valeurs", [sys.executable, os.path.join("logique", "test_logique.py")]),
    ("logique : analyse d'initialisation (vrai, faux, inconnu, variable)", [sys.executable, os.path.join("logique", "test_initialisation.py")]),
    ("génomique : QEGAL, COMPTE, tableaux de quits", [sys.executable, os.path.join("genomique", "test_genomique.py")]),
    ("réécriture des boucles en 16 éléments d'un coup", [sys.executable, os.path.join("vectorise", "test_vectorise.py")]),
    ("compression du cube (grands volumes si cargo est présent)", [sys.executable, os.path.join("compression", "test_compression.py")]),
    ("bibliothèque du cube", [sys.executable, os.path.join("bibliotheque", "test_bibliotheque.py")]),
    ("virgule fixe et 64 bits", [sys.executable, os.path.join("bibliotheque", "test_fixe.py")]),
    ("correction d'erreur diamant", [sys.executable, os.path.join("bibliotheque", "test_diamant.py")]),
    ("mathématiques, hasard et afficher", [sys.executable, os.path.join("maths", "test_maths.py")]),
    ("priorités des opérateurs", [sys.executable, os.path.join("tests", "test_priorites.py")]),
    ("test différentiel", [sys.executable, os.path.join("tests", "test_differentiel.py"), "300" if COMPLET else "100"]),
]
try:
    import numpy  # noqa: F401
    etapes.append(("flottants et longs (numpy)", [sys.executable, os.path.join("tests", "test_types.py")]))
    etapes.append(("flottants 64 bits : machine (numpy, quatre machines)", [sys.executable, os.path.join("tests", "test_flottant64_machine.py")]))
    etapes.append(("flottants 64 bits : langage (opérateurs, conversions, affichage exact)", [sys.executable, os.path.join("tests", "test_flottant64.py")]))
    etapes.append(("flottants 64 bits : bibliothèque mathématique (sinus_64, exponentielle_64…)", [sys.executable, os.path.join("tests", "test_maths64.py")]))
    etapes.append(("entiers de 128 bits (entier_128)", [sys.executable, os.path.join("tests", "test_entier128.py")]))
    etapes.append(("ombre binaire du cube (numpy ; grands volumes si cargo est présent)",
                   [sys.executable, os.path.join("ombre", "test_ombre.py")]))
    etapes.append(("feu de camp : scène, ombre quaternaire, rendu PBR (rendu si cargo est présent)",
                   [sys.executable, os.path.join("feu", "test_feu.py")]))
except ImportError:
    print("numpy absent : les tests des flottants, des longs et de l'ombre sont sautés (pip install numpy pour l'ajouter)")
if shutil.which("cargo"):
    etapes.append(("machine Rust", None))
    etapes.append(("machine Rust multicœur", [sys.executable, os.path.join("multicoeur", "test_multicoeur.py")]))
    etapes.append(("vtxc : le compilateur écrit en vtx se compile lui-même", [sys.executable, os.path.join("vtxc", "test_vtxc.py")]))
    etapes.append(("cubes sur disque en miroir inversé (anti-cube, état de Belnap, réparation ; quatre machines)", [sys.executable, os.path.join("tests", "test_miroir.py")]))
    etapes.append(("appels en série « f(a): x, y; » (quatre compilateurs, mêmes mots)", [sys.executable, os.path.join("tests", "test_serie.py")]))
    etapes.append(("Gobatix interactif : souris, touches, cadence, anti-couleur, GIF (32 et 64 bits)", [sys.executable, os.path.join("tests", "test_gobatix.py")]))
    etapes.append(("SPU-64 : les deux machines identiques (programmes aléatoires, flottants quaternaires, brin, cubes sur disque)",
                   [sys.executable, os.path.join("spu64", "test_spu64.py"), "3000" if COMPLET else "1000"]))
    etapes.append(("SPU-64 : corpus de conformité", [sys.executable, os.path.join("spu64", "verifier_corpus64.py")]))
    etapes.append(("vtx64 : le compilateur du SPU-64 (entier et flottant quaternaire de 64 bits, 32 et 128 au choix, brin)",
                   [sys.executable, os.path.join("tests", "test_vtx64.py")]))
    etapes.append(("vtxc64 : le compilateur écrit en vtx pour le SPU-64 (point fixe, mêmes mots que vtx64.py)", [sys.executable, os.path.join("vtxc", "test_vtxc64.py")] + (["--complet"] if COMPLET else [])))
    etapes.append(("Lugus (SPU-128) : la machine de référence (flottant de 128 bits = flottant_petuar, largeurs, matière, voies, brin, cubes)",
                   [sys.executable, os.path.join("spu128", "test_spu128.py")]))
    etapes.append(("Lugus : les deux machines identiques (programmes aléatoires)", [sys.executable, os.path.join("spu128", "test_lugus.py"), "3000" if COMPLET else "1000"]))
    etapes.append(("Lugus : corpus de conformité", [sys.executable, os.path.join("spu128", "verifier_corpus128.py")]))
    etapes.append(("vtx128 : le langage du SPU-64 sur Lugus (suite de vtx64, types, bibliothèque, deux machines)",
                   [sys.executable, os.path.join("tests", "test_vtx128.py")]))
    etapes.append(("vtx128 : la bibliothèque mathématique du flottant de 128 bits (référence à 80 chiffres)",
                   [sys.executable, os.path.join("tests", "test_maths128.py"), "300" if COMPLET else "60"]))
    etapes.append(("vtx128 : mêmes sorties que le SPU-64 (programmes au hasard, exemples)",
                   [sys.executable, os.path.join("tests", "test_vtx128_differentiel.py"), "300" if COMPLET else "60"]))
    etapes.append(("flottant_petuar : le flottant quaternaire de 128 bits (référence exacte, quatre machines, vtxc, ADN et cube)",
                   [sys.executable, os.path.join("tests", "test_petuar.py")]))
    etapes.append(("type texte et afficher (vtx.py et vtxc)", [sys.executable, os.path.join("vtxc", "test_textes.py")]))
    etapes.append(("tableaux, dictionnaires, vocabulaire, lire_ligne (vtx.py et vtxc)", [sys.executable, os.path.join("vtxc", "test_tableaux.py")]))
    etapes.append(("mémoire qui se libère et mémoire qui dure (ramasser, sauver_tas)", [sys.executable, os.path.join("vtxc", "test_memoire.py")]))
    etapes.append(("ScoR v0 (spirale, sommeil, épissage à quatre valeurs)", [sys.executable, os.path.join("scor", "test_scor.py")]))
    etapes.append(("traduction en code natif (rustc)", [sys.executable, os.path.join("natif", "test_natif.py")]))
    etapes.append(("atelier en console (pseudo-terminal)", [sys.executable, os.path.join("atelier", "test_atelier.py")]))
else:
    print("cargo absent : la machine Rust n'est pas vérifiée (voir vtx-rs/LISEZMOI.md)")
if shutil.which("node"):
    etapes.append(("machines JavaScript", ["node", os.path.join("machines", "conformite.js"),
                                          os.path.join("conformite", "corpus_conformite.txt"),
                                          os.path.join("conformite", "corpus_attendu.txt")]))
else:
    print("node absent : les machines JavaScript ne sont pas vérifiées")
echecs = 0
noms_echecs = []
for nom, cmd in etapes:
    print(f"\n=== {nom}")
    if nom == "machine Rust":
        b = subprocess.run(["cargo", "build", "--release", "--quiet"], cwd=os.path.join(ici, "vtx-rs"), **TEXTE)
        exe = os.path.join(ici, "vtx-rs", "target", "release", "vtx-spu" + (".exe" if os.name == "nt" else ""))
        if b.returncode != 0 or not os.path.exists(exe):
            print("compilation Rust en échec :", b.stderr[-800:])
            echecs += 1
            noms_echecs.append(nom)
            continue
        r = subprocess.run([exe, "corpus", os.path.join("conformite", "corpus_conformite.txt")], cwd=ici, **TEXTE)
        attendu = open(os.path.join(ici, "conformite", "corpus_attendu.txt")).read().strip().split("\n")
        obtenu = r.stdout.strip().split("\n")
        ec = sum(a_ != b_ for a_, b_ in zip(attendu, obtenu)) + abs(len(attendu) - len(obtenu))
        print(f"Rust : {len(attendu)} programmes, {ec} écart(s)")
        if r.returncode != 0 or ec > 0:
            echecs += 1
            noms_echecs.append(nom)
        continue
    r = subprocess.run(cmd, cwd=ici, **TEXTE)
    sortie = (r.stdout + r.stderr).strip().split("\n")
    print("\n".join(sortie[-6:]))
    if r.returncode != 0:
        echecs += 1
        noms_echecs.append(nom)
print("\n" + ("Tout est conforme." if not echecs else f"{echecs} étape(s) en échec : " + " ; ".join(noms_echecs)))
if not COMPLET:
    print("(vérification rapide ; « verifier.py --complet » refait tout, grands volumes compris)")
sys.exit(1 if echecs else 0)
