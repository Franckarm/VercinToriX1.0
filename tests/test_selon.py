#!/usr/bin/env python3
"""selon sur plusieurs lectures (0.6l) : « selon (a, b, c) » (la place compte) et « selon {a, b, c} » (sans ordre).
Des selon tirés au hasard (2 à 4 lectures, motifs avec _ et |, plusieurs motifs par branche, avec ou sans autre) :
mêmes mots par vtx128.py et vtxc128 (et par vtx64.py et vtxc64 pour Dunon), et sur toutes les combinaisons de
lectures, la branche jouée est celle que calcule une référence écrite ici ; les branches inatteignables refusées par
les deux compilateurs ; un selon dans une branche ; « selon (x) » garde son sens ; et les tables du codon écrites en
selon décident comme les tables en deux entiers, pour les 64 codons."""
import itertools
import os
import random
import subprocess
import sys
import tempfile

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, racine)
import vtx128  # noqa: E402
import vtx64  # noqa: E402

X = ".exe" if os.name == "nt" else ""
BIN = os.path.join(racine, "vtx-rs", "target", "release")
d = tempfile.mkdtemp()
echecs = 0
NOMS = ["inconnu", "faux", "vrai", "variable"]


def verifier(nom, ok, detail=""):
    global echecs
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok else f" : {detail}"), flush=True)
    echecs += 0 if ok else 1


def compiler_les_deux(fic, machine):
    """(mots de la référence ou son erreur, mots de vtxc ou son erreur)"""
    mod, exe = (vtx128, "lugus") if machine == "lugus" else (vtx64, "vtx64")
    src = open(fic, encoding="utf-8").read()
    try:
        ref = mod.assembler(mod.compiler(src, dossier=os.path.dirname(fic)))
    except Exception as e:  # noqa: BLE001
        ref = "refusé : " + str(e).split(" : ", 1)[-1]
    sortie = fic + ".mots"
    if os.path.exists(sortie):
        os.remove(sortie)
    r = subprocess.run([os.path.join(BIN, exe + X), "compiler", fic, sortie], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode == 0 and os.path.exists(sortie):
        m = [int(x) for x in open(sortie).read().split(";")[0].split(",") if x.strip()]
    else:
        m = "refusé : " + (r.stdout + r.stderr)
    return ref, m


def jouer(fic, machine):
    exe = "lugus" if machine == "lugus" else "vtx64"
    return subprocess.run([os.path.join(BIN, exe + X), fic], capture_output=True, text=True, encoding="utf-8",
                          errors="replace", cwd=d, timeout=120, stdin=subprocess.DEVNULL).stdout


def prend(motif, t, ordre):
    if ordre:
        return all(t[i] in motif[i] for i in range(len(t)))
    return all(t.count(v) >= sum(1 for c in motif if c == {v}) for v in range(4))


def ecrire_motif(motif, ordre):
    places = []
    for c in motif:
        if len(c) == 4:
            places.append("_")
        else:
            places.append("|".join(NOMS[v] for v in sorted(c)))
    return ("(" if ordre else "{") + ", ".join(places) + (")" if ordre else "}")


def tirer(rng):
    n = rng.randint(2, 4)
    ordre = rng.random() < 0.5
    branches = []
    for _ in range(rng.randint(1, 6)):
        motifs = []
        for _ in range(rng.randint(1, 2)):
            m = []
            for _ in range(n):
                x = rng.random()
                if x < 0.3:
                    m.append({0, 1, 2, 3})
                elif ordre and x < 0.5:
                    m.append(set(rng.sample(range(4), rng.randint(2, 3))))
                else:
                    m.append({rng.randrange(4)})
            motifs.append(m)
        branches.append(motifs)
    return n, ordre, branches, rng.random() < 0.5


def programme(n, ordre, branches, autre, machine):
    params = ", ".join(f"p{i}: logique" for i in range(n))
    lect = ", ".join(f"p{i}" for i in range(n))
    lignes = [f"// machine : {machine}", f"fonction choisir({params}) {{",
              f"    selon {'(' if ordre else '{'}{lect}{')' if ordre else '}'} {{"]
    for k, motifs in enumerate(branches):
        lignes.append("        " + ", ".join(ecrire_motif(m, ordre) for m in motifs) + f" {{ retour {k + 1}; }}")
    if autre:
        lignes.append("        autre { retour 99; }")
    lignes += ["    }", "    retour 0;", "}", "fonction principal() {", f"    pour t dans 0..{4 ** n} {{"]
    args = ", ".join(f"comme_logique((t >> {2 * i}) & 3)" for i in range(n))
    lignes += [f"        ecrire(choisir({args}));", '        ecrire(" ");', "    }", '    afficher("");', "}", ""]
    return "\n".join(lignes)


def attendu(n, ordre, branches, autre):
    """les choix sur toutes les combinaisons, ou None si une branche est inatteignable"""
    tous = list(itertools.product(range(4), repeat=n))
    couverts = set()
    for motifs in branches:
        pris = {t for t in tous if any(prend(m, t, ordre) for m in motifs)}
        if not pris - couverts:
            return None
        couverts |= pris
    res = []
    for code in range(4 ** n):
        t = tuple((code >> (2 * i)) & 3 for i in range(n))
        k = next((j + 1 for j, motifs in enumerate(branches) if any(prend(m, t, ordre) for m in motifs)), 99 if autre else 0)
        res.append(str(k))
    return " ".join(res) + " \n"


for machine in ("lugus", "dunon"):
    rng = random.Random(2026 if machine == "lugus" else 1114)
    joues = refuses = ecarts = 0
    for k in range(60 if machine == "lugus" else 30):
        n, ordre, branches, autre = tirer(rng)
        f = os.path.join(d, f"h_{machine}_{k}.vtx")
        open(f, "w", encoding="utf-8").write(programme(n, ordre, branches, autre, machine))
        ref, m = compiler_les_deux(f, machine)
        att = attendu(n, ordre, branches, autre)
        if att is None:
            refuses += 1
            ok = isinstance(ref, str) and isinstance(m, str) and "jamais atteinte" in ref and "jamais atteinte" in m
        else:
            joues += 1
            ok = isinstance(ref, list) and ref == m and jouer(f, machine) == att
        if not ok:
            ecarts += 1
            if ecarts <= 3:
                print("   écart :", f, str(ref)[:120], str(m)[:120])
    verifier(f"{machine} : {joues} selon au hasard joués sur toutes leurs lectures, {refuses} refusés (une branche "
             f"inatteignable) : mêmes mots, mêmes refus, les branches attendues", ecarts == 0, f"{ecarts} écarts")

# un selon dans une branche d'un autre (les variables cachées sont numérotées après les branches, dans les deux)
imbrique = os.path.join(d, "imbrique.vtx")
open(imbrique, "w", encoding="utf-8").write("""// machine : lugus
fonction f(a: logique, b: logique, c: logique) {
    selon (a, b) {
        (vrai, _) {
            selon {b, c} {
                {vrai, vrai} { retour 1; }
                {faux, _} { retour 2; }
                autre { retour 3; }
            }
        }
        (_, vrai) {
            selon c {
                vrai { retour 4; }
                autre { retour 5; }
            }
        }
        autre {
            selon (x_de(c), c) {
                (faux, faux) { retour 6; }
            }
        }
    }
    retour 7;
}
fonction x_de(c: logique): logique { retour non4(c); }
fonction principal() {
    soit x: logique = vrai;
    selon (x) {
        vrai { ecrire("(x) "); }
    }
    pour t dans 0..64 {
        ecrire(f(comme_logique(t & 3), comme_logique((t >> 2) & 3), comme_logique((t >> 4) & 3)));
    }
    afficher("");
}
""")


def f_ref(a, b, c):
    if a == 2:
        if sorted((b, c)) == [2, 2]:
            return 1
        if 1 in (b, c):
            return 2
        return 3
    if b == 2:
        return 4 if c == 2 else 5
    non = {0: 0, 1: 2, 2: 1, 3: 3}[c]
    if non == 1 and c == 1:
        return 6
    return 7


ref, m = compiler_les_deux(imbrique, "lugus")
att = "(x) " + "".join(str(f_ref(t & 3, (t >> 2) & 3, (t >> 4) & 3)) for t in range(64)) + "\n"
verifier("selon imbriqués (avec ordre, sans ordre, ordinaire) et « selon (x) » : mêmes mots, mêmes choix",
         isinstance(ref, list) and ref == m and jouer(imbrique, "lugus") == att, jouer(imbrique, "lugus")[:80])

# les tables du codon, écrites en selon, décident comme les tables en deux entiers
tables = os.path.join(d, "tables.vtx")
os.makedirs(os.path.join(d, "bibliotheque"), exist_ok=True)
open(os.path.join(d, "bibliotheque", "codon.vtx"), "w", encoding="utf-8").write(
    open(os.path.join(racine, "bibliotheque", "codon.vtx"), encoding="utf-8").read())
open(tables, "w", encoding="utf-8").write("""// machine : lugus
importer "bibliotheque/codon.vtx";
// le verdict avec ordre : deux lectures de premier rang, puis le recoupement
fonction verdict_en_selon(m: logique, l: logique, r: logique): logique {
    selon (m, l, r) {
        (vrai, vrai|inconnu, _), (inconnu, vrai, _) { retour vrai; }
        (faux, faux|inconnu, _), (inconnu, faux, _) { retour faux; }
        (inconnu, inconnu, _) { retour r; }
        (_, _, vrai) { retour vrai; }
        (_, _, faux) { retour faux; }
    }
    retour variable;
}
// le verdict sans ordre : les oui francs contre tout le reste exprimé
fonction verdict_sans_ordre(a: logique, b: logique, c: logique): logique {
    selon {a, b, c} {
        {vrai, vrai, _}, {vrai, inconnu, inconnu} { retour vrai; }
        {faux, faux, _}, {faux, inconnu, inconnu} { retour faux; }
        {inconnu, inconnu, inconnu} { retour inconnu; }
    }
    retour variable;
}
fonction principal() {
    soit pareils = 0;
    soit pareils2 = 0;
    pour d dans 0..64 {
        soit a = lettre(d, 0);
        soit b = lettre(d, 1);
        soit c = lettre(d, 2);
        si verdict_en_selon(a, b, c) == verdict_ordonne(d) { pareils = pareils + 1; }
        si verdict_sans_ordre(a, b, c) == verdict(d) { pareils2 = pareils2 + 1; }
    }
    afficher(pareils, pareils2);
}
""")
ref, m = compiler_les_deux(tables, "lugus")
verifier("les deux verdicts du codon écrits en selon : mêmes mots, et les mêmes décisions que les tables en deux entiers "
         "(64 codons sur 64, avec et sans ordre)", isinstance(ref, list) and ref == m and jouer(tables, "lugus") == "64 64\n",
         jouer(tables, "lugus"))
# le conseil prudent de exemples128/codon.vtx, écrit en selon {a, b, c}, donne la même action que l'ancienne table
# de 20 cases (indexée par le numéro de situation), sur les 64 lectures
ex = open(os.path.join(racine, "exemples128", "codon.vtx"), encoding="utf-8").read()
i = ex.index("fonction conseil_prudent(")
fonction = ex[i:ex.index("\n}\n", i) + 3]
conseil = os.path.join(d, "conseil.vtx")
open(conseil, "w", encoding="utf-8").write("""// machine : lugus
importer "bibliotheque/codon.vtx";
""" + fonction + """
fonction principal() {
    soit prudent = [0, 2, 2, 2, 1, 3, 3, 1, 3, 1, 3, 3, 3, 3, 0, 3, 3, 0, 0, 0];
    soit noms = ["attendre", "agir", "renoncer", "demander un témoin de plus"];
    soit pareils = 0;
    pour d dans 0..64 {
        si noms[prudent[situation(d)]] == conseil_prudent(lettre(d, 0), lettre(d, 1), lettre(d, 2)) {
            pareils = pareils + 1;
        }
    }
    afficher(pareils);
}
""")
ref, m = compiler_les_deux(conseil, "lugus")
verifier("le conseil prudent de codon.vtx, écrit en selon : la même action que l'ancienne table, 64 lectures sur 64",
         isinstance(ref, list) and ref == m and jouer(conseil, "lugus") == "64\n", jouer(conseil, "lugus"))
print("selon sur plusieurs lectures : " + ("tout est conforme" if echecs == 0 else f"{echecs} échec(s)"))
sys.exit(1 if echecs else 0)
