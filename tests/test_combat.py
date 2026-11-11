#!/usr/bin/env python3
"""Le combat (0.6, exemples128/combat.vtx) : un garde dont les quatre réactions (parer, attaquer, se garder, chercher)
suivent les quatre valeurs de la question « est-ce qu'il me frappe ? », lue par le codon avec ordre (vue, ouïe, flair),
contre un garde à quatre valeurs sans codon et deux gardes binaires, dans les mêmes 500 combats. Mêmes mots par
vtx128.py et vtxc128 ; traduit en x86-64 comme joué par Lugus seul ; et, avec l'argument « python », comme la machine
de référence en Python (une demi-minute)."""
import os
import subprocess
import sys
import tempfile

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, racine)
import vtx128  # noqa: E402

X = ".exe" if os.name == "nt" else ""
BIN = os.path.join(racine, "vtx-rs", "target", "release")
d = tempfile.mkdtemp()
echecs = 0


def verifier(nom, ok, detail=""):
    global echecs
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok else f" : {detail}"), flush=True)
    echecs += 0 if ok else 1


def jouer(fic, interprete=False):
    env = dict(os.environ)
    env.pop("VTX_INTERPRETE", None)
    if interprete:
        env["VTX_INTERPRETE"] = "1"
    return subprocess.run([os.path.join(BIN, "lugus" + X), fic], capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=env, timeout=300).stdout


demo = os.path.join(racine, "exemples128", "combat.vtx")
src = open(demo, encoding="utf-8").read()
ref = vtx128.assembler(vtx128.compiler(src, dossier=os.path.dirname(demo)))
sortie = os.path.join(d, "combat.mots")
r = subprocess.run([os.path.join(BIN, "lugus" + X), "compiler", demo, sortie], capture_output=True, text=True,
                   encoding="utf-8", errors="replace")
m = [int(x) for x in open(sortie).read().split(";")[0].split(",") if x.strip()] if r.returncode == 0 else None
verifier("combat.vtx : mêmes mots par vtx128.py et vtxc128", m == ref, f"{len(ref)} contre {None if m is None else len(m)}")
a, b = jouer(demo), jouer(demo, True)
verifier("traduit en x86-64 comme joué par Lugus seul", a == b and len(a) > 500, a[-300:])
lignes = a.splitlines()
verifier("le combat raconté : les quatre réactions paraissent (pare, attaque, se garde, cherche)",
         all(any(("Brennos " + mot) in x for x in lignes) for mot in ("pare et riposte", "attaque", "se garde", "cherche")), "")
verifier("une feinte percée par le flair est tranchée ; une feinte non percée : il se garde",
         "        vue : non ; ouïe : oui ; flair : non\n        Brennos attaque" in a
         and "        vue : non ; ouïe : oui ; flair : rien\n        Brennos se garde" in a, "")


def score(nom):
    x = [l for l in lignes if l.startswith(nom)]
    if not x:
        return None
    mots = x[0].replace(";", " ").split()
    return int(mots[mots.index("gagnés") + 1]), int(mots[mots.index("perdus") + 1]), int(mots[-1])


q, f, h, p = score("Brennos"), score("quatre valeurs, la fusion"), score("le binaire hardi"), score("le binaire prudent")
verifier("le tournoi : codon 499 gagnés, fusion seule 495, binaire prudent 418, binaire hardi 200",
         (q, f, h, p) == ((499, 1, 15), (495, 5, 13), (200, 300, 2), (418, 82, 7)), str((q, f, h, p)))
# un tableau de textes écrit, rangé dans une variable : ses cases sont des textes (corrigé en 0.6f)
cas = os.path.join(d, "textes.vtx")
open(cas, "w", encoding="utf-8").write("""// machine : lugus
fonction principal() {
    soit actions = ["attendre", "agir", "fuir"];
    soit p = [1, 0];
    afficher(actions[1], actions[p[1]]);
    soit i = 2;
    afficher(actions[i] + " !", actions[i] == "fuir", longueur(actions));
    pour a dans actions { ecrire(a); ecrire(" "); }
    afficher("");
    soit nombres = [3, 4];
    afficher(nombres[0] + nombres[1]);
}
""")
srcc = open(cas, encoding="utf-8").read()
refc = vtx128.assembler(vtx128.compiler(srcc, dossier=d))
sortie = os.path.join(d, "textes.mots")
r = subprocess.run([os.path.join(BIN, "lugus" + X), "compiler", cas, sortie], capture_output=True, text=True,
                   encoding="utf-8", errors="replace")
m = [int(x) for x in open(sortie).read().split(";")[0].split(",") if x.strip()] if r.returncode == 0 else None
verifier("un tableau de textes écrit dans une variable : mêmes mots par les deux compilateurs", m == refc, "")
o = jouer(cas)
verifier("ses cases s'affichent, s'ajoutent et se comparent comme des textes",
         o == "agir attendre\nfuir ! 1 3\nattendre agir fuir \n7\n" and o == jouer(cas, True), repr(o))
if "python" in sys.argv[1:]:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    py = subprocess.run([sys.executable, os.path.join(racine, "vtx128.py"), "run", demo], capture_output=True, text=True,
                        encoding="utf-8", errors="replace", env=env, timeout=600).stdout
    py = "".join(x for x in py.splitlines(True) if "instructions exécutées" not in x)
    verifier("la machine de référence en Python donne la même sortie", py == a and len(a) > 500, py[-200:])
print("Le combat : tout est conforme." if echecs == 0 else f"{echecs} échec(s).")
sys.exit(1 if echecs else 0)
