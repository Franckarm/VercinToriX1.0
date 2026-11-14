#!/usr/bin/env python3
"""Le gène (0.6m, bibliotheque/codon.vtx) : une chaîne de témoins lue par codons de trois, puis relue trois par trois.
Des chaînes tirées au hasard (0 à 30 lectures) : gene_lire, gene_lire_ordonne, gene_plat et gene_suspens contre une
référence écrite ici ; mêmes mots par les deux compilateurs de Lugus et de Dunon ; Dunon écrit ce que Lugus écrit ;
exemples128/gene.vtx traduit comme joué par Lugus seul, et sa mesure."""
import os
import random
import shutil
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


def memes_mots(fic, mod, exe):
    src = open(fic, encoding="utf-8").read()
    ref = mod.assembler(mod.compiler(src, dossier=os.path.dirname(fic)))
    sortie = fic + "." + exe + ".mots"
    r = subprocess.run([os.path.join(BIN, exe + X), "compiler", fic, sortie], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    m = [int(x) for x in open(sortie).read().split(";")[0].split(",") if x.strip()] if r.returncode == 0 else None
    return m == ref, f"{len(ref)} contre {None if m is None else len(m)}"


def jouer(fic, exe="lugus", env=None):
    e = dict(os.environ)
    e.pop("VTX_INTERPRETE", None)
    e.update(env or {})
    return subprocess.run([os.path.join(BIN, exe + X), fic], capture_output=True, text=True, encoding="utf-8",
                          errors="replace", cwd=d, timeout=300, stdin=subprocess.DEVNULL, env=e).stdout


# --- la référence
def verdict(L):
    o, n, p = L.count(2), L.count(1), L.count(3)
    return 2 if o > n + p else 1 if n > o + p else 0 if o + n + p == 0 else 3


def verdict_ordonne(L):
    m, n_, r = L
    b = m | n_
    return b if b in (1, 2) else (r if r in (1, 2) else 3) if b == 3 else r


def gene(g, ordonne):
    if not g:
        return 0
    taire = False
    while len(g) > 1:
        cod = [(g[i:i + 3] + [0, 0, 0])[:3] for i in range(0, len(g), 3)]
        if taire:
            cod = [[0 if x == 3 else x for x in c] for c in cod]
        g = [verdict_ordonne(c) if ordonne else verdict(c) for c in cod]
        taire = True
    return g[0]


def suspens(g):
    r = []
    for i in range(0, len(g), 3):
        v = verdict((g[i:i + 3] + [0, 0, 0])[:3])
        r.append(2 if v == 3 else 0 if v == 0 else 1)
    return r


rng = random.Random(1114)
chaines = [[rng.choice([0, 0, 1, 2, 2, 3]) for _ in range(rng.randint(0, 30))] for _ in range(80)]
chaines += [[], [3], [2, 1], [3, 3, 3, 2, 2, 0, 1, 1, 0]]
os.makedirs(os.path.join(d, "bibliotheque"), exist_ok=True)
shutil.copy(os.path.join(racine, "bibliotheque", "codon.vtx"), os.path.join(d, "bibliotheque", "codon.vtx"))
for machine, mod, exe in (("lugus", vtx128, "lugus"), ("dunon", vtx64, "vtx64")):
    lignes = [f"// machine : {machine}", 'importer "bibliotheque/codon.vtx";', "fonction montrer(g: logique[]) {",
              "    ecrire(entier(gene_lire(g)));", '    ecrire(" ");', "    ecrire(entier(gene_lire_ordonne(g)));",
              '    ecrire(" ");', "    ecrire(entier(gene_plat(g)));", '    ecrire(" :");',
              '    pour s dans gene_suspens(g) { ecrire(" "); ecrire(entier(s)); }', '    afficher("");', "}",
              "fonction principal() {"]
    for k, ch in enumerate(chaines):
        lignes.append(f"    soit g{k}: logique[] = tableau(0);")
        for v in ch:
            lignes.append(f"    ajouter(g{k}, {NOMS[v]});")
        lignes.append(f"    montrer(g{k});")
    lignes.append("}")
    fic = os.path.join(d, f"chaines_{machine}.vtx")
    open(fic, "w", encoding="utf-8").write("\n".join(lignes) + "\n")
    ok, detail = memes_mots(fic, mod, exe)
    verifier(f"{machine} : {len(chaines)} chaînes, mêmes mots par les deux compilateurs", ok, detail)
    att = "".join(f"{gene(ch, False)} {gene(ch, True)} {verdict(ch)} :" + "".join(f" {s}" for s in suspens(ch)) + "\n"
                  for ch in chaines)
    o = jouer(fic, exe)
    verifier(f"{machine} : gene_lire, gene_lire_ordonne, gene_plat et gene_suspens comme la référence, sur toutes",
             o == att, next((f"chaîne {i} : {a!r} contre {b!r}" for i, (a, b) in
                             enumerate(zip(o.splitlines(), att.splitlines())) if a != b), o[-200:]))

demo = os.path.join(racine, "exemples128", "gene.vtx")
for mod, exe, nom in ((vtx128, "lugus", "Lugus"), (vtx64, "vtx64", "Dunon")):
    ok, detail = memes_mots(demo, mod, exe)
    verifier(f"gene.vtx : mêmes mots par les deux compilateurs de {nom}", ok, detail)
a = jouer(demo)
verifier("gene.vtx : Dunon écrit ce que Lugus écrit", a == jouer(demo, "vtx64") and len(a) > 300, a[-200:])
exe_demo = os.path.join(d, "gene" + X)
subprocess.run([os.path.join(BIN, "vtx" + X), "exe128", demo, exe_demo], capture_output=True)
envx = {"VTX_CONSOLE": "1", "VTX_SANS_PAUSE": "1"}
t = subprocess.run([exe_demo], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=d,
                   env=dict(os.environ, **envx), timeout=300).stdout
s_ = subprocess.run([exe_demo], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=d,
                    env=dict(os.environ, VTX_INTERPRETE="1", **envx), timeout=300).stdout
verifier("gene.vtx en .exe : traduit comme joué par Lugus seul, et comme lugus", t == s_ == a, t[-200:])
verifier("gene.vtx : les portes 2 et 5 se contredisent ; le compte de tous décide mieux (394 contre 384 justes sur "
         "400 ; 371 contre 361 avec des familles achetées)",
         "portes qui se contredisent : 2 5" in a and "le compte de tous : justes 394 ; fausses 4" in a
         and "le gène           : justes 384 ; fausses 6" in a and "le compte de tous : justes 371" in a
         and "le gène           : justes 361" in a, a[-500:])
print("le gène : " + ("tout est conforme" if echecs == 0 else f"{echecs} échec(s)"))
sys.exit(1 if echecs else 0)
