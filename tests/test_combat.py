#!/usr/bin/env python3
"""Le combat (0.6, exemples128/combat.vtx) : un garde dont les quatre réactions (parer, attaquer, se garder, chercher)
suivent les quatre valeurs de la question « est-ce qu'il me frappe ? », lue par le codon avec ordre (vue, ouïe, flair),
avec ou sans tirage au sort devant la contradiction, contre des gardes sans codon et deux gardes binaires, face à un
légionnaire qui apprend, dans deux tournois de 500 combats (la garde tient, la garde est enfoncée). Mêmes mots par
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
verifier("le combat raconté : les réactions paraissent (pare, attaque, cherche), et le tirage au sort devant une feinte",
         all(any(mot in x for x in lignes) for mot in ("Brennos pare et riposte", "Brennos attaque", "Brennos cherche",
                                                       "Brennos tire au sort : ")), "")
verifier("une feinte percée par le flair est tranchée sans tirage ; une feinte non percée : il tire au sort",
         "        vue : oui ; ouïe : non ; flair : non\n        Brennos attaque" in a
         and "        vue : non ; ouïe : oui ; flair : rien\n        Brennos tire au sort : " in a, "")


def tournoi(titre):
    i = [k for k, x in enumerate(lignes) if x.startswith(titre)]
    if not i:
        return None
    t = []
    for x in lignes[i[0] + 1:i[0] + 7]:
        mots = x.replace(";", " ").split()
        t.append((int(mots[mots.index("gagnés") + 1]), int(mots[mots.index("perdus") + 1])))
    return t


# dans l'ordre : le codon et le hasard, le codon seul, la fusion et le hasard, la fusion seule, prudent, hardi
tient, enfoncee = tournoi("Le tournoi quand la garde tient"), tournoi("Le tournoi quand la garde est enfoncée")
verifier("quand la garde tient : le codon seul 499, avec le hasard 494, la fusion 479 et 457, les binaires 64 et 23",
         tient == [(494, 6), (499, 1), (457, 43), (479, 21), (64, 436), (23, 477)], str(tient))
verifier("quand la garde est enfoncée : le hasard passe devant (494 contre 474 ; la fusion 457 contre 199)",
         enfoncee == [(494, 6), (474, 26), (457, 43), (199, 301), (64, 436), (23, 477)], str(enfoncee))
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
