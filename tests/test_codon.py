#!/usr/bin/env python3
"""Le codon (0.6, bibliotheque/codon.vtx) : une contradiction en suspens garde trois lectures à quatre valeurs.
Vérifié contre une référence écrite ici en Python, pour les 64 codons : le numéro de situation (20 en tout, le même
dans tout ordre), le verdict (les deux entiers de la table contre la règle), le penchant ; puis la vie d'un dossier :
recoupé, tranché, échu au bout du délai, rouvert ; jamais de retour à inconnu ; le codon avec ordre (deux lectures de
premier rang, puis le recoupement) : sa table, ses cases pleines, ses 40 situations. Mêmes mots par vtx128.py et vtxc128 ;
exemples128/codon.vtx traduit en x86-64 comme joué par Lugus seul."""
import itertools
import os
import shutil
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


def memes_mots(fic):
    src = open(fic, encoding="utf-8").read()
    ref = vtx128.assembler(vtx128.compiler(src, dossier=os.path.dirname(fic)))
    sortie = os.path.join(d, os.path.basename(fic) + ".mots")
    r = subprocess.run([os.path.join(BIN, "lugus" + X), "compiler", fic, sortie], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    m = [int(x) for x in open(sortie).read().split(";")[0].split(",") if x.strip()] if r.returncode == 0 else None
    return m == ref, f"{len(ref)} contre {None if m is None else len(m)} {r.stdout[-200:]} {r.stderr[-200:]}"


def jouer(fic, interprete=False):
    env = dict(os.environ)
    env.pop("VTX_INTERPRETE", None)
    if interprete:
        env["VTX_INTERPRETE"] = "1"
    return subprocess.run([os.path.join(BIN, "lugus" + X), fic], capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=env, timeout=120).stdout


# --- la référence : les mêmes règles, écrites en Python
def lettres(c):
    return [c & 3, (c >> 2) & 3, (c >> 4) & 3]


def ref_verdict(c):
    L = lettres(c)
    oui, non, partages = L.count(2), L.count(1), L.count(3)
    return 2 if oui > non + partages else 1 if non > oui + partages else 0 if oui + non + partages == 0 else 3


def ref_penche(c):
    L = lettres(c)
    return 2 if L.count(2) > L.count(1) else 1 if L.count(1) > L.count(2) else 0


def ref_ordonne(c):
    m, n, r = lettres(c)
    b = m | n
    return b if b in (1, 2) else (r if r in (1, 2) else 3) if b == 3 else r


sortes = sorted(set(tuple(sorted(lettres(c))) for c in range(64)), key=lambda t: (t[2], t[1], t[0]))
verifier("trois lettres à quatre valeurs, sans ordre : 20 situations", len(sortes) == 20, str(len(sortes)))

shutil.copy(os.path.join(racine, "bibliotheque", "codon.vtx"), os.path.join(d, "codon.vtx"))
cas = os.path.join(d, "cas.vtx")
open(cas, "w", encoding="utf-8").write("""// machine : lugus
importer "codon.vtx";
fonction principal() {
    pour c dans 0..64 {
        afficher(situation(c), entier(verdict(c)), entier(penche(c)), absents(c), entier(verdict_ordonne(c)), case_pleine(c), situation_ordonnee(c));
    }
    // la vie d'un dossier : un oui, un non, un absent
    soit a = codon(vrai, faux, inconnu);
    afficher(a, etat(a), age(a));
    a = consolider(a);
    a = consolider(a);
    afficher(etat(a), age(a), entier(verdict(a)));
    a = consolider(a);
    afficher(etat(a), age(a), entier(verdict(a)));
    a = consolider(a);
    afficher(etat(a), age(a));
    soit m = recouper(a, 1, faux);
    afficher(m == a);
    a = recouper(a, 2, faux);
    afficher(etat(a), age(a), situation(a), entier(verdict(a)));
    a = consolider(a);
    afficher(etat(a), entier(verdict(a)));
    // un témoin qui se contredit devient un témoin partagé ; aucune lecture ne revient à inconnu
    soit b = codon(vrai, vrai, inconnu);
    b = consolider(b);
    afficher(etat(b), entier(verdict(b)));
    b = recouper(b, 0, faux);
    afficher(etat(b), entier(lettre(b, 0)), entier(lettre(b, 1)), entier(lettre(b, 2)), entier(verdict(b)));
    b = recouper(b, 0, inconnu);
    afficher(entier(lettre(b, 0)), age(b));
    // un vieillissement interrompu par une lecture nouvelle repart de zéro
    soit e = codon(vrai, faux, inconnu);
    e = consolider(e);
    e = consolider(e);
    e = recouper(e, 2, variable);
    afficher(etat(e), age(e), situation(e));
    // le silence ne vieillit pas
    soit s = consolider(consolider(consolider(consolider(codon(inconnu, inconnu, inconnu)))));
    afficher(s, etat(s), age(s));
    // avec ordre : la mémoire dit oui, la lecture nouvelle dit non ; le recoupement tranche
    soit o = consolider_ordonne(codon(vrai, faux, inconnu));
    afficher(etat(o), age(o));
    o = consolider_ordonne(recouper(o, 2, faux));
    afficher(etat(o), entier(verdict_ordonne(o)), entier(verdict(o)));
    // une réponse franche des deux premières places : le recoupement contraire n'y change rien
    soit p = consolider_ordonne(codon(vrai, inconnu, faux));
    afficher(etat(p), entier(verdict_ordonne(p)), entier(verdict(p)));
}
""")
ok, detail = memes_mots(cas)
verifier("vtx128.py et vtxc128 donnent les mêmes mots (les cas)", ok, detail)
o = jouer(cas).splitlines()
tete = [[int(x) for x in ligne.split()] for ligne in o[:64]]
verifier("situation : le même numéro dans tout ordre, 20 numéros de 0 à 19",
         len(tete) == 64 and all(tete[c][0] == sortes.index(tuple(sorted(lettres(c)))) for c in range(64)), "")
verifier("verdict : les deux entiers de la table disent la règle, pour les 64 codons",
         len(tete) == 64 and all(tete[c][1] == ref_verdict(c) for c in range(64)),
         str([c for c in range(64) if len(tete) == 64 and tete[c][1] != ref_verdict(c)]))
verifier("penche et absents, pour les 64 codons",
         len(tete) == 64 and all(tete[c][2] == ref_penche(c) and tete[c][3] == lettres(c).count(0) for c in range(64)), "")
perm = all(len(set(tete[x + 4 * y + 16 * z][1] for x, y, z in itertools.permutations(t))) == 1 for t in sortes) if len(tete) == 64 else False
verifier("le verdict ne dépend pas de l'ordre des trois lettres", perm, "")
verifier("verdict avec ordre : les deux entiers de la table disent la règle, pour les 64 codons",
         len(tete) == 64 and all(tete[c][4] == ref_ordonne(c) for c in range(64)), "")
verifier("case pleine : la troisième lettre ne change rien, exactement dans ces cases (6 sur 16)",
         len(tete) == 64 and sum(tete[c][5] for c in range(16)) == 6
         and all((len(set(tete[(c & 15) + 16 * r][4] for r in range(4))) == 1) == (tete[c][5] == 1) for c in range(64)), "")
verifier("situation avec ordre : 40 numéros, les deux premières places sans ordre entre elles",
         len(tete) == 64 and len(set(tete[c][6] for c in range(64))) == 40
         and all(tete[c][6] == tete[((c >> 2) & 3) + 4 * (c & 3) + (c & 48)][6] for c in range(64)), "")
attendu = ["6 0 0", "0 2 3", "2 0 3", "2 0", "1", "0 0 6 1", "1 1", "1 2", "0 3 2 0 3", "3 0", "0 0 14", "0 0 0", "0 1", "1 1 1", "1 2 3"]
noms = ["un dossier neuf : en suspens, âge zéro", "deux tris sans rien de neuf : il vieillit, toujours en suspens",
        "au troisième tri : échu, la contradiction est fixée", "un dossier fixé ne vieillit plus",
        "une lecture qui n'apprend rien le laisse tel quel", "une lecture nouvelle le rouvre (deux non contre un oui)",
        "puis il est tranché : faux", "deux oui, un absent : tranché vrai au premier tri",
        "le premier témoin se dédit : il devient partagé, le dossier est rouvert, en suspens",
        "une lecture inconnue n'efface rien", "un vieillissement interrompu repart de zéro",
        "le silence ne vieillit pas", "avec ordre : oui contre non, pas de recoupement : en suspens, il vieillit",
        "avec ordre : le recoupement dit non, tranché faux",
        "avec ordre : un oui de premier rang, un non au recoupement : tranché vrai (sans ordre : en suspens)"]
for i, (n, a) in enumerate(zip(noms, attendu)):
    verifier(n, 64 + i < len(o) and o[64 + i] == a, f"{o[64 + i] if 64 + i < len(o) else None!r} attendu {a!r}")
verifier("les cas : traduits en x86-64 comme joués par Lugus seul", jouer(cas) == jouer(cas, True), "")

demo = os.path.join(racine, "exemples128", "codon.vtx")
ok, detail = memes_mots(demo)
verifier("exemples128/codon.vtx : mêmes mots par les deux compilateurs", ok, detail)
a, b = jouer(demo), jouer(demo, True)
verifier("codon.vtx : 49 « variable » par la fusion seule, 26 tranchés et 37 en suspens par le codon ; traduit = Lugus seul",
         a == b and "pour 49 ;" in a and "tranche 26 de ces cas et en laisse 37 en suspens" in a
         and "le conseil prudent, devant « deux oui contre un non » : demander un témoin de plus" in a, a[-400:])
verifier("codon.vtx : le tableau avec ordre (6 cases pleines, 44 tranchés) et la mesure par place (82, 82, 102)",
         "C     CCCC   CCCC   UCGU   UCGU" in a and "pleines (la 3e lettre est libre) : 6 sur 16" in a
         and "tranche 44 codons" in a and "avec ordre : place 1 : 82 ; place 2 : 82 ; place 3 : 102" in a, "")
print("Le codon : tout est conforme." if echecs == 0 else f"{echecs} échec(s).")
sys.exit(1 if echecs else 0)
