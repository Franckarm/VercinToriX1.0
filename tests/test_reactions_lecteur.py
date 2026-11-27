#!/usr/bin/env python3
"""0.851 : ce que lit le lecteur de la forge dans les réactions (vtx128.py : il reste le lecteur de la forge et de
Taranis jusqu'à l'étape 2 de docs/vtx-un-compilateur.md) : la molécule (vagues, formule), les souvenirs des atomes
lourds (et ce qu'ils épargnent), la provenance (« vtx128.py pourquoi »), le drapeau d'erreur d'une division. Le
comportement des réactions (ce qu'elles affichent, leurs refus) est vérifié par lugus seul : tests/test_reactions.py.

    python3 tests/test_reactions_lecteur.py"""
import os
import subprocess
import sys
import tempfile

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, racine)
import vtx128  # noqa: E402

vtx128.COMPAT_64 = False
echecs = []


def verifier(nom, ok, detail=""):
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok or not detail else " : " + detail), flush=True)
    if not ok:
        echecs.append(nom)


PANEL = open(os.path.join(racine, "exemples128", "panel.vtx"), encoding="utf-8").read()

# 3. la molécule : vagues et formule
vtx128.REACTIONS.clear()
vtx128.compiler(PANEL)
m = vtx128.REACTIONS["principal"]
verifier("formule CH₄N₆O, masse 116 hex, 7 vagues, produit et somme dans la même vague",
         m.formule() == ("CH₄N₆O", 116) and len(m.vagues) == 7
         and {a.nom for a in m.vagues[1]} == {"produit", "somme"}, f"{m.formule()} {len(m.vagues)}")

# 14. le calcul incrémental : les souvenirs des atomes lourds
SCENE = open(os.path.join(racine, "exemples128", "scene_incrementale.vtx"), encoding="utf-8").read()


def pas_de(src, souvenirs):
    vtx128.SOUVENIRS = souvenirs
    try:
        cpu, _, _ = vtx128.executer(src, max_pas=10 ** 9)
    finally:
        vtx128.SOUVENIRS = True
    return cpu.sortie, cpu.pas


avec, sans = pas_de(SCENE, True), pas_de(SCENE, False)
verifier(f"la scène rappelée 60 fois : même résultat, {sans[1]} instructions sans souvenirs, {avec[1]} avec (10 fois moins)",
         avec[0] == sans[0] == [382460] and avec[1] * 8 < sans[1], f"{avec} {sans}")
vtx128.REACTIONS.clear()
vtx128.compiler(SCENE)
sc = vtx128.REACTIONS["scene"]
verifier("les trois atomes lourds ont un souvenir, pas l'atome léger (leger : pas de boucle)",
         len(sc.souvenirs) == 3 and "souvenirs" in sc.rapport(), sc.rapport())
HASARD = """
fonction lourd(n) { soit s = 0; pour i dans 0..n { s = s + (i * 7 + n) % 11; } retour s; }
fonction moyenne(x: flottant, k): flottant { soit a = x; pour i dans 0..k { a = (a + 1.0) * 0.5; } retour a; }
fonction lit(i) { soit s = 0; pour j dans 0..2 { s = s + @2[i]; } retour s; }
reaction r(a, b, x: flottant) -> s {
    = lourd(a)              -> u
    = lourd(u % 30 + b)     -> v
    = moyenne(x, a % 5)     -> m
    = lit(a % 4)            -> w
    = u + v + entier(m * 100.0) + w -> s
}
fonction principal() {
    soit t = 0;
    pour k dans 0..ENTREES {
        @2[k % 4] = k;
        t = t + r(entree(), entree(), flottant(entree()) * 0.25);
    }
    sortie(t);
}
"""
import random as _r
g = _r.Random(7)
entrees = [g.choice([3, 5, 40, 41]) for _ in range(90)]
src_h = HASARD.replace("ENTREES", str(len(entrees) // 3)).replace("entree()", "entrée()")
vtx128.REACTIONS.clear()
memes = True
for souv in (True, False):
    vtx128.SOUVENIRS = souv
    cpu, _, _ = vtx128.executer(src_h, entrees, max_pas=10 ** 9)
    memes = memes and (souv or cpu.sortie == premier)
    premier = cpu.sortie
vtx128.SOUVENIRS = True
vtx128.REACTIONS.clear()
vtx128.compiler(src_h)
verifier("30 rappels aux entrées tirées au hasard (souvent les mêmes) : mêmes sorties avec et sans souvenirs ; la "
         "fonction qui lit la mémoire n'a pas de souvenir", memes and len(vtx128.REACTIONS["r"].souvenirs) == 3)

# 15. les souvenirs rangés comme Fischer : seize places par atome, deux choix ; des entrées qui alternent sont retrouvées
ALTERNANCE = open(os.path.join(racine, "exemples128", "alternance.vtx"), encoding="utf-8").read()
vtx128.PROVENANCE = True
cpu_a, _, _ = vtx128.executer(ALTERNANCE, max_pas=10 ** 9)
vtx128.PROVENANCE = False
mol_a = vtx128.REACTIONS["image"]
reagi = cpu_a.lire((3 << 62) | (mol_a.traces["fond"] + 1))
sans_a = pas_de(ALTERNANCE, False)
verifier(f"cinq décors qui alternent : le calcul lourd réagit {reagi} fois sur 60 appels (une seule place : 60)",
         reagi == 5 and cpu_a.sortie == sans_a[0], f"{reagi} {cpu_a.sortie} {sans_a[0]}")

sans = "reaction f(a) -> b {\n    = a / 4 -> b\n}\nfonction principal() { sortie(f(8)); }\n"
avec = sans.replace("a / 4", "a / a")
verifier("diviser par une valeur écrite non nulle ne coûte rien (aucun drapeau)", "__err" not in vtx128.compiler(sans, optim=False)
         and "__err" in vtx128.compiler(avec, optim=False))
f16 = os.path.join(tempfile.mkdtemp(), "e.vtx")
open(f16, "w", encoding="utf-8").write("reaction g(n) -> r: flottant {\n    = 10.0 / flottant(n) -> q\n    = q + 1.0 -> r\n}\n"
                                       "fonction principal() { afficher(g(0)); }\n")
r16 = subprocess.run([sys.executable, os.path.join(racine, "vtx128.py"), "pourquoi", f16], capture_output=True, text=True, encoding="utf-8")
verifier("la provenance dit variable : l'erreur, la division par zéro, non réparée",
         "q variable (une erreur, une division par zéro, non réparée" in r16.stdout, r16.stdout[-400:])

print("réactions, le lecteur de la forge : " + ("tout est conforme" if not echecs else f"{len(echecs)} échec(s)"))
sys.exit(1 if echecs else 0)
