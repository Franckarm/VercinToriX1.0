#!/usr/bin/env python3
"""Le lecteur d'ADN écrit en vtx (chimie/adn.vtx, embarqué dans lugus : « lugus relire ») lit comme chimie/adn.py :
sur chaque avarie, le même état, le même compte rendu et le même ADN relu, octet pour octet. Les deux compilateurs
donnent ses mêmes mots, et lugus embarque les mots d'aujourd'hui.

    python3 tests/test_adn_vtx.py [N]      N avaries par genre et par programme (3 par défaut)"""
import os
import random
import subprocess
import sys
import tempfile
import time

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, os.path.join(racine, "chimie"))
sys.path.insert(0, racine)
import adn  # noqa: E402

echecs = []
lugus = os.path.join(racine, "vtx-rs", "target", "release", "lugus" + (".exe" if os.name == "nt" else ""))
LECTEUR = os.path.join(racine, "chimie", "adn.vtx")
EMBARQUE = os.path.join(racine, "vtx-rs", "lecteur_adn.mots")


def verifier(nom, ok, detail=""):
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok or not detail else " : " + detail), flush=True)
    if not ok:
        echecs.append(nom)


if not os.path.exists(lugus):
    print("lugus n'est pas construit (cargo build --release dans vtx-rs) : rien n'est vérifié")
    sys.exit(1)

d = tempfile.mkdtemp(prefix="adn-vtx-")

# 1. les mêmes mots par les deux compilateurs, et ceux que lugus embarque
f1, f2 = os.path.join(d, "a.mots"), os.path.join(d, "b.mots")
subprocess.run([lugus, "compiler", LECTEUR, f1], capture_output=True)
subprocess.run([sys.executable, os.path.join(racine, "vtx128.py"), "mots", LECTEUR, f2], capture_output=True)
lu = [open(f, encoding="utf-8").read().strip().rstrip(";") for f in (f1, f2, EMBARQUE)]
verifier(f"le lecteur en vtx : vtxc128 et vtx128.py donnent les mêmes mots ({len(lu[0].split(','))}), ceux que lugus embarque",
         lu[0] == lu[1] == lu[2] and len(lu[0]) > 0,
         "embarqués périmés : lugus compiler ../chimie/adn.vtx lecteur_adn.mots, puis cargo build --release"
         if lu[0] == lu[1] else "les compilateurs diffèrent")


def relire_vtx(f_adn, f_relu):
    if os.path.exists(f_relu):
        os.remove(f_relu)
    r = subprocess.run([lugus, "relire", f_adn, f_relu], capture_output=True, text=True, encoding="utf-8")
    return r.returncode, r.stderr


def relire_python(f_adn, f_relu):
    mots, mols, t = adn.lire_adn(f_adn)
    etat, rapport = adn.lire(mots, mols, t)
    lignes = [f"  {m.nom} : {adn.NOM_ETAT[e]}, {quoi}" for m, e, quoi in rapport if e != adn.VRAI]
    lignes.append(f"l'ADN : {adn.NOM_ETAT[etat]}")
    if etat == adn.VARIABLE:
        lignes.append("rien n'est relu : l'ADN est gardé tel qu'il a été lu, pour la preuve")
    else:
        adn.ecrire_adn(f_relu, mots, mols, t)
    return etat, "\n".join(lignes) + "\n"


# 2. un ADN intact, avec ses introns (isotopes, texte) : relu tel quel
programmes = [os.path.join(racine, "exemples128", f) for f in ("freinage.vtx", "chute.vtx", "scene_incrementale.vtx")]
adns = []
for p in programmes:
    f = os.path.join(d, os.path.basename(p).replace(".vtx", ".adn"))
    subprocess.run([lugus, "ranger", p, f], capture_output=True)
    adns.append(f)
f_relu = os.path.join(d, "relu.adn")
c, e = relire_vtx(adns[0], f_relu)
verifier("un ADN intact (avec les introns isotopes et source) : vrai, relu octet pour octet",
         c == 0 and e.strip() == "l'ADN : vrai" and open(f_relu, "rb").read() == open(adns[0], "rb").read(), e)

# 3. les avaries : le même état, le même compte rendu, le même ADN relu que chimie/adn.py
n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
g = random.Random(20261102)
ecarts, total, etats = [], 0, {}
t0 = time.time()
for f in adns:
    mots0, mols0, t_0 = adn.lire_adn(f)
    for genre in adn.GENRES:
        for k in range(n):
            mots, t = list(mots0), adn.copie_temoins(t_0)
            adn.avarie(genre, mots, t, mols0, g)
            f_abime = os.path.join(d, "abime.adn")
            adn.ecrire_adn(f_abime, mots, mols0, t)
            e_py, cr_py = relire_python(f_abime, os.path.join(d, "relu_py.adn"))
            c, cr_vtx = relire_vtx(f_abime, f_relu)
            total += 1
            etats[e_py] = etats.get(e_py, 0) + 1
            meme_adn = (e_py == adn.VARIABLE and not os.path.exists(f_relu)) or \
                (e_py != adn.VARIABLE and os.path.exists(f_relu)
                 and open(f_relu, "rb").read() == open(os.path.join(d, "relu_py.adn"), "rb").read())
            if cr_vtx != cr_py or not meme_adn or (c == 0) != (e_py != adn.VARIABLE):
                ecarts.append(f"{os.path.basename(f)} / {genre} / {k} :\n{cr_py}---\n{cr_vtx}")
verifier(f"le lecteur en vtx lit comme Python : {total - len(ecarts)}/{total} avaries, même état, même compte rendu, "
         f"même ADN relu ({etats.get(adn.VRAI, 0)} vrais, {etats.get(adn.FAUX, 0)} réparés, "
         f"{etats.get(adn.VARIABLE, 0)} variables ; {time.time() - t0:.0f} s)", not ecarts, "\n".join(ecarts[:3]))

# 4. un fichier qui n'est pas un ADN, un ADN tronqué : illisibles (0), rien n'est écrit
f_faux = os.path.join(d, "faux.adn")
open(f_faux, "w", encoding="utf-8").write("bonjour\n")
c1, e1 = relire_vtx(f_faux, f_relu)
texte = open(adns[1], encoding="utf-8").read()
f_tronque = os.path.join(d, "tronque.adn")
open(f_tronque, "w", encoding="utf-8", newline="\n").write(texte[:texte.index("GU ombres")] + "GU ombres 1\n1,2,3,4\nAG\n")
c2, e2 = relire_vtx(f_tronque, f_relu)
verifier("un fichier qui n'est pas un ADN, un ADN aux témoins tronqués : refusés, rien n'est écrit",
         c1 != 0 and c2 != 0 and "pas un ADN" in e1 and ("manque" in e2 or "correspondent" in e2)
         and not os.path.exists(f_relu), e1 + e2)

print("lecteur d'ADN en vtx : " + ("tout est conforme" if not echecs else f"{len(echecs)} échec(s)"))
sys.exit(1 if echecs else 0)
