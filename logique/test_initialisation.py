#!/usr/bin/env python3
"""Analyse d'initialisation à quatre valeurs (initialisation.vtx) : inconnu et variable mis à l'épreuve.
 1. L'exemple : un si dont une seule branche initialise c (variable), une boucle qui initialise d après sa lecture
    (variable), e jamais initialisée (faux), un bloc mort (inconnu). Chaque réponse est vérifiée.
 2. Graphes aléatoires (boucles, jonctions, blocs morts) : l'état de chaque variable lue, les comptes et le nombre de
    tours identiques à une référence Python écrite d'après la définition (fusion = réunion des preuves).
 3. Ce qu'un booléen « initialisée sur tous les chemins ? » aurait confondu.
 4. Coût : le comptage final réécrit 16 variables à la fois.
 5. Sans Python : le même programme compilé par vtxc (le compilateur écrit en vtx) et exécuté par la machine Rust."""
import os, random, shutil, subprocess, sys, tempfile
ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, racine)
import vtx  # noqa: E402

RAPIDE = os.environ.get("VTX_RAPIDE") == "1"
SRC = open(os.path.join(ici, "initialisation.vtx"), encoding="utf-8").read()
NOMS = {0: "inconnu", 1: "faux", 2: "vrai", 3: "variable"}


def entrees(nb, affecte, lit, preds):
    e = [nb]
    for b in range(nb):
        e += [affecte[b], lit[b], len(preds[b])] + preds[b]
    return e


def reference(nb, affecte, lit, preds):
    """Codes : inconnu 0, faux 1, vrai 2, variable 3 (bit 1 : preuve du vrai, bit 0 : preuve du faux)."""
    ent = [[0] * 16 for _ in range(nb)]
    sor = [[0] * 16 for _ in range(nb)]
    change, tours = True, 0
    while change:
        change, tours = False, tours + 1
        for b in range(nb):
            e = [1] * 16 if b == 0 else [0] * 16
            for p in preds[b]:
                e = [x | y for x, y in zip(e, sor[p])]                  # fusion : on réunit les preuves des chemins
            s = [2 if (affecte[b] >> v) & 1 and e[v] != 0 else e[v] for v in range(16)]
            ent[b] = e
            if s != sor[b]:
                sor[b], change = s, True
    lus = [ent[b][v] for b in range(nb) for v in range(16) if (lit[b] >> v) & 1]
    tout = [x for b in range(nb) for x in ent[b]]
    return lus + [tout.count(2), tout.count(1), tout.count(0), tout.count(3), tours]


def lancer(e):
    cpu = vtx.executer(SRC, e, max_pas=50_000_000)[0]
    return cpu.sortie, "".join(chr(c) for c in cpu.texte), cpu.pas


# 1. l'exemple
#   B0 : a = …; b = …;        B1 : si b … (lit b)        B2 : c = a + 1 (lit a)      B3 : rien
#   B4 : jonction de B2 et B3 : lit a et c                B5 : tête de boucle (préd. B4, B6) : lit d
#   B6 : d = … ; retour en B5  B7 : sortie de boucle : lit e   B8 : aucun prédécesseur : lit a
affecte = [0b11, 0, 0b100, 0, 0, 0, 0b1000, 0, 0]
lit = [0, 0b10, 0b1, 0, 0b101, 0b1000, 0, 0b10000, 0b1]
preds = [[], [0], [1], [1], [2, 3], [4, 6], [5], [5], []]
EX = entrees(9, affecte, lit, preds)
sortie, texte, pas_ex = lancer(EX)
attendu = {"bloc 1, b": "vrai", "bloc 2, a": "vrai", "bloc 4, a": "vrai", "bloc 4, c": "variable",
           "bloc 5, d": "variable", "bloc 7, e": "faux", "bloc 8, a": "inconnu"}
obtenu = dict(zip(attendu, (NOMS[c] for c in sortie[:7])))
ok1 = obtenu == attendu and sortie == reference(9, affecte, lit, preds)
print("1. Exemple :")
for k in attendu:
    print(f"   {k} : {obtenu.get(k)} (attendu {attendu[k]})")
print(f"   identique à la référence : {ok1}")

# 2. graphes aléatoires
r = random.Random(1789)
N = 60 if RAPIDE else 300
ok2, vus = 0, {0: 0, 1: 0, 2: 0, 3: 0}
cas = []
for n in range(N):
    nb = r.randint(1, 16)
    aff = [r.getrandbits(16) & r.getrandbits(16) for _ in range(nb)]
    li = [r.getrandbits(16) for _ in range(nb)]
    pr = []
    for b in range(nb):
        k = 0 if (b > 0 and r.random() < .1) else r.randint(1 if b > 0 else 0, 3)
        pr.append([r.randrange(nb) for _ in range(k)])           # boucles, jonctions, blocs morts
    e = entrees(nb, aff, li, pr)
    ref = reference(nb, aff, li, pr)
    cas.append((e, ref))
    s = lancer(e)[0]
    ok2 += s == ref
    for c in ref[:-5]:
        vus[c] += 1
print(f"2. {N} graphes aléatoires : identiques à la référence {ok2}/{N} ; lectures rencontrées : "
      + ", ".join(f"{NOMS[c]} {vus[c]}" for c in (2, 1, 3, 0)))

# 3. le booléen
conf = vus[1] + vus[3] + vus[0]
print(f"3. Un booléen « initialisée sur tous les chemins ? » répondrait « non » à {conf} lectures, sans distinguer "
      f"l'erreur certaine ({vus[1]}), le bogue qui dépend du chemin ({vus[3]}) et le code mort ({vus[0]}).")

# 4. coût
vtx.VECTORISER = False
pas_sans = lancer(EX)[2]
vtx.VECTORISER = True
print(f"4. Exemple : {pas_ex:,} instructions ; {pas_sans:,} si le comptage n'était pas réécrit 16 à la fois")

# 5. sans Python
ok5 = None
cargo = shutil.which("cargo")
if cargo:
    rs = os.path.join(racine, "vtx-rs")
    cible = os.environ.get("CARGO_TARGET_DIR") or os.path.join(rs, "target")
    subprocess.run([cargo, "build", "--release", "-q"], cwd=rs, check=True)
    VTX = os.path.join(cible, "release", "vtx" + (".exe" if os.name == "nt" else ""))
    tmp = tempfile.mkdtemp(prefix="init-")
    prog = os.path.join(tmp, "init.prog")
    subprocess.run([VTX, "compiler", os.path.join(ici, "initialisation.vtx"), prog], check=True, capture_output=True)
    champs = open(prog).read().strip().split(";")      # « mots;entrées;table des accords »
    mots, table = champs[0], (champs[2] if len(champs) > 2 else "")
    ok5 = 0
    for e, ref in cas:
        p = os.path.join(tmp, "cas.txt")
        with open(p, "w") as f:
            f.write(mots + ";" + ",".join(map(str, e)) + ";" + table + "\n")
        out = subprocess.run([VTX, "lancer", p, "1000000000", "1"], capture_output=True, text=True,
                             encoding="utf-8", errors="replace").stdout.splitlines()
        ok5 += out[1] == ",".join(map(str, ref))
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"5. Compilé par vtxc et exécuté par la machine Rust, sans Python : identiques {ok5}/{N}")
else:
    print("5. cargo absent : la version sans Python n'est pas essayée")
sys.exit(0 if ok1 and ok2 == N and ok5 in (None, N) and min(vus.values()) > 0 else 1)
