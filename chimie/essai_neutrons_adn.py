#!/usr/bin/env python3
"""Essai mesuré : la puissance des neutrons sur les avaries de l'ADN (les genres de chimie/adn.py), version 3 (CRC-8)
contre version 4 (CRC quaternaire), les mêmes programmes et les mêmes avaries tirées dans le même ordre.

Ce qu'on compte, pour chaque genre : la part des mots abîmés que les neutrons désignent (un mot désigné devient un
effacement : l'ombre en répare quatre par colonne au lieu de deux cherchés), et l'issue de la lecture (réparé, ou
variable : abîmé au-delà des témoins). « jamais de travers » : un ADN lu vrai ou réparé redonne exactement les mots.

    python3 chimie/essai_neutrons_adn.py [N]      N avaries par genre et par programme (200 par défaut)"""
import os
import random
import subprocess
import sys
import tempfile

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, ici)
import adn  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 200
lugus = os.path.join(racine, "vtx-rs", "target", "release", "lugus" + (".exe" if os.name == "nt" else ""))
d = tempfile.mkdtemp(prefix="neutrons-adn-")
programmes = []
for f in ("freinage.vtx", "chute.vtx", "scene_incrementale.vtx", "panel.vtx"):
    sortie = os.path.join(d, f.replace(".vtx", ".adn"))
    subprocess.run([lugus, "ranger", os.path.join(racine, "exemples128", f), sortie], capture_output=True)
    programmes.append(sortie)


def en_version(t, mots, v):
    t = adn.copie_temoins(t)
    t["version"] = v
    t["neutrons"] = {i: adn.neutron(mots[i], v) for i in t["neutrons"]}
    return t


print(f"{'genre':30s} {'version':>8s} {'désignés':>10s} {'réparé':>8s} {'variable':>9s}  de travers")
for genre in adn.GENRES:
    for v in (3, 4):
        g = random.Random(20261103)
        abimes = designes = rep = var = travers = 0
        for f in programmes:
            mots0, mols, t0 = adn.lire_adn(f)
            t0 = en_version(t0, mots0, v)
            for _ in range(N):
                mots, t = list(mots0), adn.copie_temoins(t0)
                adn.avarie(genre, mots, t, mols, g)
                touches = [i for i in t["neutrons"] if mots[i] != mots0[i]]
                abimes += len(touches)
                designes += sum(1 for i in touches if adn.neutron(mots[i], v) != t["neutrons"][i])
                etat, _ = adn.lire(mots, mols, t)
                if etat == adn.VARIABLE:
                    var += 1
                else:
                    rep += etat == adn.FAUX
                    travers += mots != mots0
        n = N * len(programmes)
        part = f"{100 * designes / abimes:9.2f}%" if abimes else "        —"
        print(f"{genre:30s} {('v' + str(v)):>8s} {part:>10s} {100 * rep / n:7.1f}% {100 * var / n:8.1f}%  {travers}")
