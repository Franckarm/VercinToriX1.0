#!/usr/bin/env python3
"""Vérifie l'installation de vtx : tests du langage, puis les tests complémentaires, puis la conformité des machines
Rust et JavaScript si cargo et node sont installés.
Utilisation : python3 verifier.py            (rapide : moins de tirages aléatoires, sans les grands volumes)
              python3 verifier.py --complet  (tout, plusieurs dizaines de minutes)
              python3 verifier.py --deux     (0.851 : ajoute les anciens contrôles mot pour mot contre vtx128.py)
              python3 verifier.py --temoin   (0.851 : ajoute le témoin, la machine Python de vtx128.py)

0.851 (décidé avec le créateur, 27 novembre) : un seul compilateur à terme, vtxc128 (écrit en vtx). Dunon est
« dunon; » (ses règles de 64 bits, ses services, sur la machine de Lugus) ; la machine SPU-64 séparée est gelée, comme
Senos. 0.858 (décidé avec le créateur) : les machines gelées et leurs tests sont retirés (Senos en Python, les
machines JavaScript, les tests du SPU-32 et du SPU-64 séparé) ; ils restent dans l'historique git."""
import os
import shutil
import subprocess
import sys

ici = os.path.dirname(os.path.abspath(__file__))
# Windows : sans cela, les sorties capturées sont encodées en cp1252, qui ne connaît pas « → », « ³ » ou « ≥ ».
COMPLET = "--complet" in sys.argv
# 0.851 : « --deux » : les anciens contrôles des deux compilateurs de Lugus (mot pour mot contre vtx128.py)
DEUX = "--deux" in sys.argv or COMPLET
# 0.851 : « --temoin » : la machine Python de vtx128.py comme témoin (la décision du créateur : petit, à la main)
TEMOIN = "--temoin" in sys.argv
if TEMOIN:
    ENV["VTX_TEMOIN"] = "1"
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1", VTX_RAPIDE="0" if COMPLET else "1")
TEXTE = dict(capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENV)
try:
    sys.stdout.reconfigure(errors="replace")
except (AttributeError, ValueError):
    pass
etapes = [
]
if shutil.which("cargo"):
    etapes.append(("cubes sur disque en miroir inversé (anti-cube, état de Belnap, réparation ; quatre machines)", [sys.executable, os.path.join("tests", "test_miroir.py")]))
    etapes.append(("appels en série « f(a): x, y; » (quatre compilateurs, mêmes mots)", [sys.executable, os.path.join("tests", "test_serie.py")]))
    etapes.append(("la toile interactif : souris, touches, cadence, anti-couleur, GIF (32 et 64 bits)", [sys.executable, os.path.join("tests", "test_toile.py")]))
    etapes.append(("Lugus (SPU-128) : la machine de référence (flottant de 128 bits = flottant_petuar, largeurs, matière, voies, brin, cubes)",
                   [sys.executable, os.path.join("spu128", "test_spu128.py")]))
    etapes.append(("Lugus : les deux machines identiques (programmes aléatoires)", [sys.executable, os.path.join("spu128", "test_lugus.py"), "3000" if COMPLET else "1000"]))
    etapes.append(("Lugus : corpus de conformité", [sys.executable, os.path.join("spu128", "verifier_corpus128.py")]))
    if DEUX:
        # 0.851 : la suite de vtx128.py elle-même (son compilateur, sa machine Python) ; ses programmes sont rejoués par
        # vtxc128 seul dans « vtxc128 seul »
        etapes.append(("vtx128 : le langage du SPU-64 sur Lugus (suite de vtx64, types, bibliothèque, deux machines)",
                       [sys.executable, os.path.join("tests", "test_vtx128.py")]))
    etapes.append(("vtx128 : la bibliothèque mathématique du flottant de 128 bits (référence à 80 chiffres)",
                   [sys.executable, os.path.join("tests", "test_maths128.py"), "300" if COMPLET else "60"]))
    etapes.append(("les réactions jouées par lugus seul : l'ordre des lignes sans effet, contrats, unités, erreurs, la forge de Lugus",
                   [sys.executable, os.path.join("tests", "test_reactions.py")]))
    etapes.append(("les réactions, ce qu'en lit le lecteur de la forge (vtx128.py) : la molécule, les souvenirs, la provenance",
                   [sys.executable, os.path.join("tests", "test_reactions_lecteur.py")]))
    etapes.append(("la provenance : pourquoi une liaison vaut ce qu'elle vaut (lugus pourquoi)",
                   [sys.executable, os.path.join("tests", "test_provenance.py")]))
    etapes.append(("la fiabilité de l'ADN : signature, ombre, neutrons (avaries réparées, jamais de travers)",
                   [sys.executable, os.path.join("tests", "test_adn.py")]))
    etapes.append(("l'ADN vivant : patrouille, isotopes relus à l'entrée et à la sortie, apoptose, ARN (coiffe), la patrouille éteinte par défaut",
                   [sys.executable, os.path.join("tests", "test_patrouille.py")]))
    etapes.append(("le lecteur d'ADN écrit en vtx (chimie/adn.vtx, lugus relire) : lit comme Python, avarie pour avarie",
                   [sys.executable, os.path.join("tests", "test_adn_vtx.py")]))
    etapes.append(("Belenos, le fluide : la copie, le tapis roulant et les tuiles, les mêmes nombres que la référence, sur Lugus et forgés",
                   [sys.executable, os.path.join("tests", "test_fluide.py")]))
    etapes.append(("Belenos, le tableau (belenos/auvergne.vtx) : forgé, il peint l'image et l'écrit lui-même en PNG juste",
                   [sys.executable, os.path.join("tests", "test_tableau.py")]))
    etapes.append(("les cylindres (forge128 : « en segments » sur plusieurs cœurs, un cube par cylindre, fondus mot à mot ; "
                   "une boucle dépendante rejouée dans l'ordre)", [sys.executable, os.path.join("tests", "test_cylindres.py")]))
    etapes.append(("la paillasse d'Ogmios : lue comme le compilateur, gestes rejoués (lier, délier, ajouter, retirer), valeurs",
                   [sys.executable, os.path.join("tests", "test_paillasse.py")]))
    etapes.append(("la carte du programme sur la paillasse : une case par fonction, une liaison par appel",
                   [sys.executable, os.path.join("tests", "test_carte.py")]))
    etapes.append(("Ogmios écrit en vtx : Ogmios sur Lugus (édition rejouée, Ctrl+S, F5 sur une machine fille)",
                   [sys.executable, os.path.join("tests", "test_ogmios.py")]))
    etapes.append(("Fischer : le fil de Hilbert, la signature des molécules, le cube des molécules",
                   [sys.executable, os.path.join("tests", "test_fischer.py")]))
    etapes.append(("vtxc128 seul : le compilateur de Lugus sans Python (point fixe, les mêmes sorties que le témoin, trois réglages)",
                   [sys.executable, os.path.join("vtxc", "test_vtxc128_seul.py")]))
    if DEUX:
        etapes.append(("vtxc128 : le compilateur écrit en vtx pour Lugus (point fixe, mêmes mots que vtx128.py)",
                       [sys.executable, os.path.join("vtxc", "test_vtxc128.py")] + (["--complet"] if COMPLET else [])))
    etapes.append(("le vocabulaire du prélude sur les trois machines : mêmes mots par les deux compilateurs de chacune",
                   [sys.executable, os.path.join("tests", "test_vocabulaire.py")]))
    etapes.append(("le débogueur de Lugus par les noms : la pile des appels, les variables, sortir d'une fonction",
                   [sys.executable, os.path.join("tests", "test_debogueur128.py")]))
    etapes.append(("l'exécutable de Lugus : la machine, le programme et ses cubes sur disque en un fichier (vtx exe128)",
                   [sys.executable, os.path.join("tests", "test_exe128.py")]))
    etapes.append(("la traduction de Lugus en x86-64 : traduit et joué par Lugus, mêmes texte, sorties et instructions",
                   [sys.executable, os.path.join("tests", "test_natif128.py")]))
    etapes.append(("les quatre vérités : la logique de Belnap montrée (fusion, et4, le conseil d'Alésia, seize d'un coup)",
                   [sys.executable, os.path.join("tests", "test_quatre_verites.py")]))
    etapes.append(("le duel du binaire et du quaternaire : mêmes décisions, erreurs du naïf, instructions mesurées",
                   [sys.executable, os.path.join("tests", "test_duel.py")]))
    etapes.append(("les tableaux de quits et de logiques de Lugus : 64 par mot, boucles fondues, contre Python",
                   [sys.executable, os.path.join("tests", "test_rangees128.py"), "200" if COMPLET else "60"]))
    etapes.append(("les quatre valeurs aux bords du monde : le clavier, les textes lus, les fichiers (Lugus)",
                   [sys.executable, os.path.join("tests", "test_bords128.py")]))
    etapes.append(("les tableaux dynamiques de logiques, logique[] (Lugus)",
                   [sys.executable, os.path.join("tests", "test_logiques128.py")]))
    etapes.append(("le chemin de l'ADN en vtx : ranger, transcrire, l'ARNc et les anciennes isoformes, l'intron du compilateur",
                   [sys.executable, os.path.join("tests", "test_adn_chemin.py")]))
    etapes.append(("le chemin dans les deux sens : ARN → ADN (l'ADNc), ADN → hex → cube et retour, en vtx",
                   [sys.executable, os.path.join("tests", "test_adn_deux_sens.py")]))
    etapes.append(("la carte du programme : ce qu'est chaque molécule, ce qu'elle touche, ses racines, ses promesses",
                   [sys.executable, os.path.join("tests", "test_carte_arn.py")]))
    etapes.append(("les promesses : touche rien, lecture, memoire, monde ; une promesse rompue arrête la compilation",
                   [sys.executable, os.path.join("tests", "test_promesses.py")]))
    etapes.append(("supposons … parmi … retenir : essayer chaque candidat, écarter, noter, garder le meilleur",
                   [sys.executable, os.path.join("tests", "test_supposons.py")]))
    etapes.append(("Gobannos : les mots de Lugus traduits en exécutable par vtx lui-même (les mêmes sorties que Lugus)",
                   [sys.executable, os.path.join("tests", "test_gobannos.py")]))
    etapes.append(("Gobannos : les flottants par la bibliothèque écrite en vtx (au bit près, les mêmes sorties que Lugus)",
                   [sys.executable, os.path.join("tests", "test_gobannos_flottants.py")]))
    etapes.append(("les fonctions passées en valeur : les mêmes mots, la carte, le juge, Gobannos",
                   [sys.executable, os.path.join("tests", "test_valeurs.py")]))
    etapes.append(("le type d'une fonction passée en valeur : vérifié, les mêmes mots et les mêmes refus",
                   [sys.executable, os.path.join("tests", "test_types_fonction.py")]))
    etapes.append(("le vocabulaire des nombres : un mot pour les cinq types, les mêmes mots, les états gardés",
                   [sys.executable, os.path.join("tests", "test_nombres.py")]))
    etapes.append(("le vocabulaire étendu (Rust, Arduino, UE5, Blender) : Lugus et Dunon, les mêmes mots, les bonnes valeurs",
                   [sys.executable, os.path.join("tests", "test_vocabulaire_etendu.py")]))
    etapes.append(("les modules promis par leur empreinte : la même empreinte partout, un module changé refusé, la chaîne",
                   [sys.executable, os.path.join("tests", "test_modules.py")]))
    etapes.append(("reste : le reste exact des flottants, au bit près, sur Lugus et Dunon",
                   [sys.executable, os.path.join("tests", "test_reste.py")]))
    etapes.append(("le catalogue des modules et la vibration des molécules : lister un dossier, importer par l'empreinte seule, la carte",
                   [sys.executable, os.path.join("tests", "test_catalogue.py")]))
    etapes.append(("les cubes mères : un nom comme un fichier, ses sous-cubes à leurs fréquences, sur Lugus et Dunon",
                   [sys.executable, os.path.join("tests", "test_cube_mere.py")]))
    etapes.append(("les faces dans le cube : le code à l'étage Đ, les faces aux étages 1 à 3, lues pendant qu'il tourne",
                   [sys.executable, os.path.join("tests", "test_faces_cube.py")]))
    etapes.append(("multiplier_ajouter exact, un seul arrondi : cinq flottants au bit près, Lugus et Dunon",
                   [sys.executable, os.path.join("tests", "test_fma.py")]))
    etapes.append(("le glossaire d'une ligne par mot, à la fin des messages de Lugus",
                   [sys.executable, os.path.join("tests", "test_glossaire.py")]))
    etapes.append(("le gène : plus de trois témoins, lus par codons (Lugus et Dunon)",
                   [sys.executable, os.path.join("tests", "test_gene.py")]))
    etapes.append(("selon sur plusieurs lectures, avec et sans ordre (Lugus et Dunon)",
                   [sys.executable, os.path.join("tests", "test_selon.py")]))
    etapes.append(("le codon : trois lectures pour une contradiction en suspens, 20 situations, les trois sorties (Lugus)",
                   [sys.executable, os.path.join("tests", "test_codon.py")]))
    etapes.append(("le combat : un garde à quatre réactions contre la fusion seule et deux gardes binaires (Lugus)",
                   [sys.executable, os.path.join("tests", "test_combat.py")] + (["python"] if COMPLET or TEMOIN else [])))
    if TEMOIN:
        etapes.append(("le témoin : une poignée de programmes, joués par lugus et par la machine Python de vtx128.py",
                       [sys.executable, os.path.join("tests", "test_temoin_python.py")]))
    if DEUX:
        etapes.append(("les réactions dans vtxc128 : les mêmes mots que vtx128.py (exemples, contrats, unités, souvenirs, hasard)",
                       [sys.executable, os.path.join("vtxc", "test_reactions_vtxc128.py"), "40" if COMPLET else "12"]))
    etapes.append(("forge de Lugus : vtx -> Rust -> natif, mêmes sorties et même mémoire que Lugus émulé",
                   [sys.executable, os.path.join("forge", "test_forge128.py"), "40" if COMPLET else "12"]))
    etapes.append(("la forge écrite en vtx : le Rust de vtxc128, mêmes sorties et même mémoire que Lugus émulé",
                   [sys.executable, os.path.join("forge", "test_forge_vtx.py"), "40" if COMPLET else "12"]))
    etapes.append(("Taranis écrit par vtxc128, joué sur la carte de papier (les entiers de 64 bits, le quaternaire)",
                   [sys.executable, os.path.join("tests", "test_taranis_vtx.py")]))
    etapes.append(("Ésus : la division par une constante et les codons de 64 bits dans la forge, comme Lugus",
                   [sys.executable, os.path.join("tests", "test_esus.py")]))
    etapes.append(("le Druide : le relevé d'Ésus rangé dans son cube, comparé en quatre valeurs",
                   [sys.executable, os.path.join("tests", "test_druide.py")]))
    etapes.append(("Taranis et le 128 : un programme Lugus reste au processeur, un programme dunon peut aller à la carte",
                   [sys.executable, os.path.join("tests", "test_taranis128.py")]))
    etapes.append(("les cubes nommés : les mêmes mots, la même sortie et les mêmes refus, sur Lugus et sur Dunon",
                   [sys.executable, os.path.join("tests", "test_cubes_nommes.py")]))
    etapes.append(("presenter_cube : l'image d'un cube présentée, son empreinte, sur Lugus et Dunon, et forgée",
                   [sys.executable, os.path.join("tests", "test_presenter_cube.py")]))
    etapes.append(("la valeur sue : « selon » sur la réponse d'un service, les mêmes mots sur Lugus et Dunon, et forgée",
                   [sys.executable, os.path.join("tests", "test_valeur_sue.py")]))
    etapes.append(("le Druide conseiller : les mêmes mots, et ses conseils (« lugus druide »)",
                   [sys.executable, os.path.join("tests", "test_druide_conseiller.py")]))
    etapes.append(("Taranis, la sonde : le SPIR-V de vtx sur une carte par Vulkan (ou SwiftShader), les mêmes mots que le processeur",
                   [sys.executable, os.path.join("tests", "test_taranis.py")]))
    etapes.append(("Taranis, les noyaux : des boucles en segments tirées au hasard, forgées pour la carte (SPIR-V), les mêmes mots que Lugus",
                   [sys.executable, os.path.join("tests", "test_taranis_noyaux.py"), "40" if COMPLET else "16"]))
    etapes.append(("Ogmios en console (pseudo-terminal)", [sys.executable, os.path.join("tests", "test_ogmios_console.py")]))
else:
    print("cargo absent : la machine Rust n'est pas vérifiée (voir vtx-rs/LISEZMOI.md)")
# 0.847 : « verifier.py --depuis TEXTE » reprend à la première étape dont le nom contient TEXTE
if "--depuis" in sys.argv and sys.argv.index("--depuis") + 1 < len(sys.argv):
    _m = sys.argv[sys.argv.index("--depuis") + 1]
    _k = next((k for k, (n, _) in enumerate(etapes) if _m in n), 0)
    etapes = etapes[_k:]
echecs = 0
noms_echecs = []
import time
_debut = time.time()
_durees = []
for nom, cmd in etapes:
    print(f"\n=== {nom}")
    _t0 = time.time()
    r = subprocess.run(cmd, cwd=ici, stdin=subprocess.DEVNULL, **TEXTE)   # pas de clavier : une lecture est la fin de l'entrée
    sortie = (r.stdout + r.stderr).strip().split("\n")
    print("\n".join(sortie[-6:]))
    _durees.append((time.time() - _t0, nom))
    print(f"({time.time() - _t0:.0f} s)")
    if r.returncode != 0:
        echecs += 1
        noms_echecs.append(nom)
print(f"\n{(time.time() - _debut) / 60:.0f} minutes ; les plus longues : "
      + " ; ".join(f"{n} ({d / 60:.0f} min)" for d, n in sorted(_durees, reverse=True)[:5]))
print("\n" + ("Tout est conforme." if not echecs else f"{echecs} étape(s) en échec : " + " ; ".join(noms_echecs)))
if not COMPLET:
    print("(vérification rapide ; « verifier.py --complet » refait tout, grands volumes compris)")
sys.exit(1 if echecs else 0)
