#!/usr/bin/env python3
"""La paillasse (vtx-rs/src/paillasse.rs), au centre d'Ogmios : la surface des réactions, dans les deux sens avec le
texte. Sans écran, par « vtx paillasse » (le même module que l'atelier, les gestes de la souris rejoués) :
  1. la lecture : les atomes, leurs liaisons et leurs vagues sont ceux du compilateur (vtx128.py), sur les exemples de
     Lugus et sur des réactions au hasard ;
  2. les gestes : tirer une liaison sur une entrée libre « _ », délier, ajouter un atome (double clic), le retirer
     (Suppr), déplacer une case (sa place gardée dans PROG.paillasse) ; le texte réécrit compile et donne le bon
     résultat ;
  3. les valeurs (Ctrl+P) : chaque liaison porte sa valeur et son état de Belnap (vrai, porte faux, jamais calculée).

    python3 tests/test_paillasse.py"""
import os
import random
import subprocess
import sys
import tempfile

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, racine)
sys.path.insert(0, os.path.join(racine, "vtxc"))
import vtx128  # noqa: E402
from hasard_reactions import R  # noqa: E402

vtx128.COMPAT_64 = False
EXE = os.path.join(racine, "vtx-rs", "target", "release", "vtx" + (".exe" if os.name == "nt" else ""))
LUGUS = os.path.join(racine, "vtx-rs", "target", "release", "lugus" + (".exe" if os.name == "nt" else ""))
D = tempfile.mkdtemp(prefix="paillasse-")
echecs = []


def verifier(nom, ok, detail=""):
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok or not detail else " : " + detail), flush=True)
    if not ok:
        echecs.append(nom)


def paillasse(fichier, *args, gestes=None):
    a = [EXE, "paillasse", fichier] + list(args)
    if gestes is not None:
        g = os.path.join(D, "gestes.txt")
        open(g, "w", encoding="utf-8").write("\n".join(gestes) + "\n")
        a += ["--gestes", g]
    r = subprocess.run(a, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout + r.stderr


def lecture(fichier):
    """{(réaction, ligne): (élément, vague, entrées, sorties)} lu par la paillasse"""
    out = {}
    for l in paillasse(fichier, "--analyse").splitlines():
        if l.startswith("atome "):
            r, ligne, _nom, el, v, e, s = l[6:].split("|")
            out[(r, int(ligne))] = (el, int(v), [x for x in e.split(",") if x], [x for x in s.split(",") if x])
    return out


def du_compilateur(src):
    vtx128.REACTIONS.clear()
    vtx128.compiler(src)
    out = {}
    for nom, m in vtx128.REACTIONS.items():
        for k, v in enumerate(m.vagues):
            for a in v:
                out[(nom, a.ligne)] = (k + 1, list(dict.fromkeys(a.entrees)), list(a.sorties))
    return out


# 1. la lecture, comme le compilateur
def comparer(src, nom):
    f = os.path.join(D, "lu.vtx")
    open(f, "w", encoding="utf-8").write(src)
    p = lecture(f)
    c = du_compilateur(src)
    ecarts = [k for k in c if k not in p or (p[k][1], sorted(p[k][2]), p[k][3]) != (c[k][0], sorted(c[k][1]), c[k][2])]
    ecarts += [k for k in p if k not in c]
    return ecarts, p, c


dex = os.path.join(racine, "exemples128")
for f in sorted(os.listdir(dex)):
    src = open(os.path.join(dex, f), encoding="utf-8").read() if f.endswith(".vtx") else ""
    if "reaction " in src:
        ecarts, p, c = comparer(src, f)
        verifier(f"exemples128/{f} : {len(p)} atomes lus comme le compilateur (vagues, entrées, sorties)", not ecarts,
                 str([(k, p.get(k), c.get(k)) for k in ecarts[:3]]))
graine = random.randrange(1 << 30)
mauvais = []
for k in range(30):
    src = R(random.Random(graine + k)).programme()
    ecarts, p, c = comparer(src, "hasard")
    if ecarts:
        mauvais.append((graine + k, [(e, p.get(e), c.get(e)) for e in ecarts[:2]]))
verifier(f"30 réactions au hasard (graine {graine}) lues comme le compilateur", not mauvais, str(mauvais[:2]))
el = lecture(os.path.join(dex, "panel.vtx"))
verifier("le panel : six H, somme N, rdv C, rangement O (l'élément d'après la valence)",
         el[("principal", 15)][0] == "H" and el[("principal", 11)][0] == "N" and el[("principal", 9)][0] == "C"
         and el[("principal", 7)][0] == "O", str(el))


# 2. les gestes
def plan(f):
    cases, entrees = {}, {}
    for l in paillasse(f, "--plan").splitlines():
        if l.startswith("case "):
            tete, ent, sor = l[5:].split("|")
            n, x, y, lg, h = map(int, tete.split())
            pt = lambda t: [tuple(map(int, p.split(","))) for p in t.split()]  # noqa: E731
            cases[n] = {"x": x, "y": y, "l": lg, "h": h, "e": pt(ent), "s": pt(sor)}
        elif l.startswith("entree "):
            _, nom, p = l.split()
            entrees[nom] = tuple(map(int, p.split(",")))
    return cases, entrees


R_SRC = ("// une réaction à compléter sur la paillasse\nreaction r(x) -> z {\n    = x + 1 -> a\n    double = _ × 2 -> b\n"
         "    = a + b -> z\n}\nfonction principal() { sortie(r(3)); }\n")
f = os.path.join(D, "r.vtx")
open(f, "w", encoding="utf-8").write(R_SRC)
lancer = lambda f: subprocess.run([LUGUS, f], capture_output=True, text=True, encoding="utf-8").stdout.strip()  # noqa: E731
verifier("avant : l'entrée libre « _ » empêche la compilation", lancer(f) == "", lancer(f))
c, _ = plan(f)
sx, sy = c[3]["s"][0]                                  # la sortie a
cible = (c[4]["x"] + c[4]["l"] // 2, c[4]["y"] + c[4]["h"] // 2)
paillasse(f, "--ecrire", gestes=[f"bas {sx} {sy}", f"bouge {cible[0]} {cible[1]}", f"haut {cible[0]} {cible[1]}"])
t = open(f, encoding="utf-8").read()
verifier("tirer la sortie a sur la case « double » : son entrée libre devient a", "double = a × 2 -> b" in t, t)
verifier("le texte réécrit compile : r(3) = 4 + 8 = 12", lancer(f) == "12", lancer(f))
c, _ = plan(f)
ex, ey = c[5]["e"][1]                                  # l'entrée b de « a + b »
paillasse(f, "--ecrire", gestes=[f"bas {ex} {ey}", f"bouge {ex + 200} {ey + 300}", f"haut {ex + 200} {ey + 300}"])
t = open(f, encoding="utf-8").read()
verifier("tirer l'entrée b vers le vide : elle redevient libre", "= a + _ -> z" in t, t)
c, _ = plan(f)
ex, ey = c[5]["e"][1]                                  # l'entrée libre, là où elle est maintenant
bx, by = c[4]["s"][0]
paillasse(f, "--ecrire", gestes=[f"bas {bx} {by}", f"bouge {ex} {ey}", f"haut {ex} {ey}"])
t = open(f, encoding="utf-8").read()
verifier("tirer la sortie b sur l'entrée libre : relié de nouveau, 12", "= a + b -> z" in t and lancer(f) == "12", t)
paillasse(f, "--ecrire", gestes=["double 700 400"])
t = open(f, encoding="utf-8").read()
verifier("double clic dans le vide : « = _ -> l1 » s'écrit à la fin de la réaction", "    = _ -> l1\n}" in t, t)
c, _ = plan(f)
n = max(c)
cx, cy = c[n]["x"] + 5, c[n]["y"] + 5
paillasse(f, "--ecrire", gestes=[f"bas {cx} {cy}", f"haut {cx} {cy}", "touche 46"])
t = open(f, encoding="utf-8").read()
verifier("Suppr : l'atome choisi est retiré, le texte redevient celui d'avant", "l1" not in t and lancer(f) == "12", t)
c, _ = plan(f)
x0, y0 = c[3]["x"] + 10, c[3]["y"] + 8
paillasse(f, gestes=[f"bas {x0} {y0}", f"bouge {x0 + 40} {y0 + 120}", f"haut {x0 + 40} {y0 + 120}"])
c2, _ = plan(f)
place = os.path.join(D, "r.paillasse")
verifier("déplacer une case : elle reste où on l'a posée (r.paillasse), le texte ne change pas",
         (c2[3]["x"], c2[3]["y"]) == (c[3]["x"] + 40, c[3]["y"] + 120) and os.path.exists(place)
         and open(f, encoding="utf-8").read() == t, f"{c[3]} -> {c2[3]}")
cx, cy = c2[5]["x"] + 6, c2[5]["y"] + 6
sortie = paillasse(f, gestes=[f"bas {cx} {cy}", f"haut {cx} {cy}"])
verifier("un clic sur une case : l'éditeur va à sa ligne", "aller à la ligne 5" in sortie, sortie[:300])
r2 = os.path.join(D, "deux.vtx")
open(r2, "w", encoding="utf-8").write("reaction f() -> y {\n    = 6 -> x\n    = x × 7 -> y\n}\nreaction g() -> z {\n    = f() -> z\n}\n"
                                     "fonction principal() { sortie(g()); }\n")
sortie = paillasse(r2, "--analyse", gestes=["ligne 6", "plan"])
verifier("le curseur du texte dans la réaction g : la paillasse montre g", "case 6 " in sortie and "case 2 " not in sortie.split("--- expl")[0],
         sortie[:400])
erreur = os.path.join(D, "cycle.vtx")
open(erreur, "w", encoding="utf-8").write("reaction c() {\n    = b + 1 -> a\n    = a + 1 -> b\n}\n")
verifier("un cycle est dit dans les explications", "cycle" in paillasse(erreur), paillasse(erreur))

# 3. les valeurs (Ctrl+P)
s = paillasse(os.path.join(dex, "chute.vtx"), "--valeurs", gestes=["ligne 10"])
verifier("Ctrl+P : la liaison t porte sa valeur et son unité (vrai : arrivée)", "t = 2.01927510938461 s (vrai" in s, s[:500])
gardee = os.path.join(D, "garde.vtx")
open(gardee, "w", encoding="utf-8").write("reaction g(x: flottant) -> r: flottant {\n    = x × 3.0 -> t\n    = si t > 10.0 alors t - 10.0 -> r\n}\n"
                                         "fonction principal() { afficher(g(2.0)); }\n")
s = paillasse(gardee, "--valeurs", "--png", os.path.join(D, "garde.png"), gestes=["ligne 3"])
verifier("une branche qui n'a pas réagi : r porte faux, avec la valeur calculée", "r porte faux" in s and os.path.exists(os.path.join(D, "garde.png")), s[:500])

print("paillasse : " + ("tout est conforme" if not echecs else f"{len(echecs)} échec(s)"))
sys.exit(1 if echecs else 0)
