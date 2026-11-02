#!/usr/bin/env python3
"""Les réactions dans vtxc128 (le compilateur écrit en vtx, pour Lugus) : pour chaque programme, exactement les mêmes mots
que vtx128.py, avec le prélude, sans et avec optimisation, avec la partition des tâches. Les exemples de Lugus en
réactions, les programmes des tests des réactions (contrats, unités, souvenirs, ponts, pour chaque, les erreurs) et des
réactions tirées au hasard (vtxc/hasard_reactions.py), les lignes mélangées.

    python3 vtxc/test_reactions_vtxc128.py [N]          N réactions au hasard (40 par défaut)"""
import os
import random
import subprocess
import sys
import tempfile

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, racine)
sys.path.insert(0, ici)
import vtx128  # noqa: E402
from hasard_reactions import R  # noqa: E402

vtx128.COMPAT_64 = False
EXE = os.path.join(racine, "vtx-rs", "target", "release", "lugus" + (".exe" if os.name == "nt" else ""))
D = tempfile.mkdtemp(prefix="reactions-vtxc128-")
COMBOS = ((True, False, False), (True, True, False), (True, True, True))
echecs = []


def verifier(nom, ok, detail=""):
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok or not detail else " : " + detail), flush=True)
    if not ok:
        echecs.append(nom)


def ref(src, pr, op, pa):
    try:
        return vtx128.assembler(vtx128.compiler(src, prelude=pr, optim=op, partition=pa))
    except vtx128.VtxError as e:
        return "ERREUR " + str(e)


def vtxc(src, pr, op, pa):
    open(os.path.join(D, "source.vtx"), "w", encoding="utf-8").write(src)
    cm = os.path.join(D, "code.mots")
    if os.path.exists(cm):
        os.remove(cm)
    r = subprocess.run([EXE, "lancer", os.path.join(D, "c.mots"), "0", str(int(pr)), str(int(op)), str(int(pa))],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=D)
    if not os.path.exists(cm):
        return None, r.stdout + r.stderr
    return [int(x) for x in open(cm).read().strip().split(";")[0].split(",") if x], r.stdout


def pareils(src):
    """(nombre de compilations identiques, détail du premier écart)"""
    n, detail = 0, ""
    for pr, op, pa in COMBOS:
        a = ref(src, pr, op, pa)
        b, sortie = vtxc(src, pr, op, pa)
        if a == b or (isinstance(a, str) and b is None):
            n += 1
        elif not detail:
            detail = (f"{a if isinstance(a, str) else len(a)} mots / vtxc128 : "
                      f"{sortie[-200:] if b is None else len(b)} (prélude, optim, partition = {pr, op, pa})")
    return n, detail


src_c = open(os.path.join(ici, "vtxc128.vtx"), encoding="utf-8").read()
m0 = vtx128.assembler(vtx128.compiler(src_c, prelude=False, optim=False))
open(os.path.join(D, "c.mots"), "w").write(",".join(map(str, m0)) + ";\n")

# 1. les exemples de Lugus écrits en réactions
dex = os.path.join(racine, "exemples128")
for f in sorted(os.listdir(dex)):
    src = open(os.path.join(dex, f), encoding="utf-8").read() if f.endswith(".vtx") else ""
    if "reaction " in src:
        n, d = pareils(src)
        verifier(f"exemples128/{f} : {n}/{len(COMBOS)} compilations identiques", n == len(COMBOS), d)

# 2. les programmes des tests des réactions
CAS = {
    "moyenne": "reaction moyenne(a, b) -> m {\n    = a + b      -> s\n    = s / 2      -> m\n}\nfonction principal() { sortie(moyenne(4, 6)); sortie(moyenne(10, 20)); }\n",
    "si sinon": "reaction choisir(x) -> r {\n    = si x > 10 alors x - 10 sinon x + 100   -> r\n}\nfonction principal() { sortie(choisir(15)); sortie(choisir(3)); }\n",
    "ponts et apres": 'reaction principal() {\n    = afficher("b")   apres premier\n    premier = afficher("a")\n    = 1   -> x\n    = 2   -> y\n    = pont x vers @2[5]  -> x2\n    = pont y vers @2[5]  -> y2\n    = pont y vers @2[6]\n    = sortie(@2[5])\n}\n',
    "pour chaque, vague de lourds": "fonction carre_mod(i) { soit k = 0; soit x = i; tantque k < 20 { x = (x * x + 7) % 1000003; k = k + 1; } retour x; }\nfonction tranche(a, b) { soit s = 0; pour i dans a..b { s = s + carre_mod(i); } retour s; }\nreaction principal() {\n    total = somme pour chaque i dans 0..50000 : carre_mod(i)   -> t\n    petit = min pour chaque i dans 1..3000 : carre_mod(i)      -> m\n    grand = max pour chaque i dans 1..3000 : carre_mod(i)      -> g\n    haut  = tranche(0, 20000)                                 -> h\n    bas   = tranche(20000, 40000)                             -> b\n    = sortie(t)\n    = sortie(m)\n    = sortie(g)\n    = sortie(h + b)\n}\n",
    "contrats": "reaction moyenne(a, b, n) -> m {\n    exige n != 0\n    total = a + b      -> t\n    part  = t / n      -> m\n    garantit m <= t\n}\nreaction prudente(x: flottant) -> r: flottant {\n    = si x > 10.0 alors x - 10.0 -> r\n    garantit r < 5.0\n}\nexemple moyenne(4, 6, 2) == 5\nfonction principal() { sortie(moyenne(4, 6, 2)); afficher(prudente(3.0)); sortie(moyenne(4, 6, 0)); }\n",
    "unités": "reaction chute(h: flottant m, g: flottant m/s²) -> t: flottant s {\n    = 2.0 × h            -> double\n    = double ÷ g         -> carre\n    = racine(carre)      -> t\n}\nreaction trajet() -> d {\n    = 2 km               -> aller\n    = 500 m              -> rentree\n    = 3 min              -> duree\n    = aller + rentree    -> d: m\n    = d / duree          -> vitesse: m/s\n    garantit vitesse > 0 m/s\n}\nreaction energie(masse: kg, v: m/s) -> e: J {\n    = masse × v × v      -> e\n}\nfonction principal() { afficher(chute(20.0, 9.81)); sortie(trajet()); sortie(energie(2, 3)); }\n",
    "souvenirs et mémoire": "fonction lourd(n) { soit s = 0; pour i dans 0..n { s = s + (i * 7 + n) % 11; } retour s; }\nfonction moyenne(x: flottant, k): flottant { soit a = x; pour i dans 0..k { a = (a + 1.0) * 0.5; } retour a; }\nfonction lit(i) { soit s = 0; pour j dans 0..2 { s = s + @2[i]; } retour s; }\nreaction r(a, b, x: flottant) -> s {\n    = lourd(a)              -> u\n    = lourd(u % 30 + b)     -> v\n    = moyenne(x, a % 5)     -> m\n    = lit(a % 4)            -> w\n    = u + v + entier(m * 100.0) + w -> s\n}\nfonction principal() { soit t = 0; pour k dans 0..10 { @2[k % 4] = k; t = t + r(entrée(), entrée(), flottant(entrée()) * 0.25); } sortie(t); }\n",
    "unités à facteur sur des flottants": "reaction f() -> d { = 2.0 km -> a\n = 5.0 mm -> b\n = 1.5 min -> t\n = (a + b) / t -> d: m/s }\nfonction principal() { afficher(f()); }",
    "rendez-vous gardé": "reaction g(x) -> r: flottant {\n    = si x > 2 alors x × 2 -> d\n    = rendez-vous(d, x) -> d2, x2\n    = pont d2 vers @2[1] -> d3\n    = flottant(d3 + x2) -> r\n    = afficher(d3)\n}\nfonction principal() { afficher(g(5)); afficher(g(1)); }\n",
    "les erreurs (division par zéro, reparer, erreur())": 'reaction moyenne(a, b, n) -> m {\n    = a + b          -> t\n    = t / n          -> m\n}\nreaction sure(a, b, n) -> m {\n    = a + b          -> t\n    = reparer t / n par 0  -> m\n}\nreaction regarde(n) -> r {\n    = 100 / n        -> q\n    = si erreur(q) alors 0 sinon q + 1   -> r\n}\nreaction fl(x: flottant) -> y: flottant {\n    = 1.0 / x        -> y\n}\nfonction essais_a() {\n    sortie(sure(4, 6, 0)); sortie(sure(4, 6, 2));\n    sortie(regarde(0)); sortie(regarde(5));\n    afficher(fl(0.0)); afficher(fl(4.0));\n    sortie(moyenne(4, 6, 2));\n    sortie(moyenne(4, 6, 0));\n    sortie(99);\n}\nreaction tout(a, b, n) -> r {\n    = a / n                 -> q\n    = rendez-vous(q, b % n) -> q2, m2\n    = pont q2 vers @2[3]    -> q3\n    = afficher(b / n)\n    = reparer q3 + m2 par 7 -> r\n    garantit q >= 0\n}\nreaction lo(x) -> v: logique {\n    = logique(x / x > 0)    -> v\n}\nreaction petit(x: flottant_32) -> y: flottant_32 {\n    = 1.0S / x -> y\n}\nreaction cond(x) -> z {\n    = si x > 0 alors 10 / x sinon 0 -> z0\n    = reparer z0 par 0 -> z\n}\nfonction principal() {\n    sortie(tout(8, 5, 2)); sortie(cond(5)); sortie(cond(0));\n    afficher(lo(0)); afficher(lo(3)); afficher(petit(0.0S));\n    sortie(tout(8, 5, 0));\n}\n',    "les tableaux (pour chaque sans réduction, dans t, garder, flottant[])": 'reaction carres(n) -> t {\n    = pour chaque i dans 0..n : i × i -> t\n}\nreaction stats(t) -> s {\n    = somme pour chaque x dans t : x -> total\n    = max pour chaque x dans t : x -> grand\n    = garder x dans t si x % 2 == 0 -> pairs\n    = pour chaque x dans pairs : x + 1 -> plus\n    = longueur(plus) -> np\n    = total × 1000 + grand × 10 + np -> s\n}\nreaction moities(t) -> m: flottant[] {\n    = pour chaque x dans t : flottant(x) * 0.5 -> m: flottant[]\n}\nfonction principal() {\n    soit t = carres(6);\n    pour x dans t { sortie(x); }\n    sortie(stats(t));\n    soit m = moities(t);\n    pour y dans m { afficher(y); }\n}\nreaction grands(m: flottant[]) -> g: flottant[] {\n    = garder y dans m si y > 2.0 -> g\n}\nfonction principal_b() {\n    soit m = [1.5, 2.5, 0.5, 4.0];\n    soit g = grands(m);\n    sortie(longueur(g));\n    pour y dans g { afficher(y); }\n}\n',
    "plusieurs résultats et selon": 'reaction divmod(a, b) -> q, r {\n    = reparer a / b par 0  -> q\n    = reparer a % b par 0  -> r\n}\nreaction deux(x: flottant) -> m: flottant, v: logique {\n    = x * 0.5 -> m\n    = logique(x > 1.0) -> v\n}\nreaction usage(n) -> t {\n    = divmod(n, 7) -> q, r\n    = q × 100 + r -> t\n}\nreaction nom(c) -> t {\n    = selon c { 1: 10 ; 2, 3: 20 ; autre: 99 } -> t\n}\nreaction belnap(q: logique) -> n: flottant {\n    = selon q { vrai: 1.0 ; faux: 0.0 } -> n\n}\nreaction autre_usage(x: flottant) -> s: flottant {\n    = deux(x) -> m, v\n    = si v == vrai alors m sinon 0.0 - m -> s\n}\nfonction principal() {\n    sortie(usage(45)); sortie(divmod(45, 7));\n    sortie(nom(1)); sortie(nom(3)); sortie(nom(8));\n    afficher(belnap(vrai)); afficher(belnap(faux)); afficher(belnap(inconnu));\n    afficher(autre_usage(4.0)); afficher(autre_usage(0.5));\n}\n',
    "un résultat qui porte faux": "reaction garde(x: flottant) -> r: flottant {\n    = si x > 0.0 alors x × 2.0 -> r\n}\nreaction test(x) -> v: logique {\n    = logique(x > 3) -> c\n    = si x > 0 alors c -> v\n}\nfonction principal() { afficher(garde(2.0)); afficher(garde(-1.0)); afficher(test(5)); afficher(test(0)); }\n",
}
for nom, src in CAS.items():
    n, d = pareils(src)
    verifier(f"{nom} : {n}/{len(COMBOS)} compilations identiques", n == len(COMBOS), d)
ERREURS = {
    "un cycle": "reaction principal() { = b + 1 -> a\n = a + 1 -> b\n }",
    "une liaison donnée deux fois": "reaction principal() { = 1 -> a\n = 2 -> a\n }",
    "un rendez-vous de travers": "reaction principal() { = 1 -> a\n = rendez-vous(a, a) -> b\n }",
    "apres un inconnu": "reaction principal() { = 1 -> a apres zut\n }",
    "exige sur une liaison": "reaction f(a) -> b { = a + 1 -> b\n exige b > 0 }\nfonction principal() { sortie(f(1)); }",
    "un résultat absent": "reaction f(a) -> z { = a + 1 -> b }\nfonction principal() { sortie(f(1)); }",
    "des m + des s": "reaction f() -> d { = 2 m -> a\n = 3 s -> b\n = a + b -> d }\nfonction principal() { sortie(f()); }",
    "une liaison déclarée dans une autre unité": "reaction f() -> v { = 2 m -> a\n = 3 s -> b\n = a / b -> v: m }\nfonction principal() { sortie(f()); }",
    "un argument dans la mauvaise unité": "reaction g(x: m) -> y { = x + 1 m -> y }\nreaction f() -> z { = g(3 s) -> z }\nfonction principal() { sortie(f()); }",
    "la racine d'une unité impaire": "reaction f(x: flottant m) -> y { = racine(x) -> y }\nfonction principal() { afficher(f(4.0)); }",
    "un entier rendu qui peut porter faux": "reaction g(x) -> r { = si x > 0 alors x -> r }\nfonction principal() { sortie(g(2)); }",
    "un facteur sans écriture décimale (km/h)": "reaction f() -> v { = 2.0 km/h -> v }\nfonction principal() { afficher(f()); }",
}
for nom, src in ERREURS.items():
    b, sortie = vtxc(src, True, True, False)
    verifier(f"erreur vue par les deux : {nom}", isinstance(ref(src, True, True, False), str) and b is None, sortie[-200:])

# 3. des réactions au hasard
N = int(sys.argv[1]) if len(sys.argv) > 1 else 40
graine = random.randrange(1 << 30)
ecarts = []
for k in range(N):
    src = R(random.Random(graine + k)).programme()
    n, d = pareils(src)
    if n != len(COMBOS):
        ecarts.append((graine + k, d))
verifier(f"{N} réactions au hasard (graine {graine}) : {N - len(ecarts)}/{N} identiques sous les trois réglages", not ecarts,
         str(ecarts[:3]))
# 4. avec la provenance (la trace de chaque liaison) : les mêmes mots que vtx128.py
def avec_trace(src):
    vtx128.PROVENANCE = True
    try:
        a = ref(src, True, True, True)
    finally:
        vtx128.PROVENANCE = False
    open(os.path.join(D, "source.vtx"), "w", encoding="utf-8").write(src)
    cm = os.path.join(D, "code.mots")
    if os.path.exists(cm):
        os.remove(cm)
    subprocess.run([EXE, "lancer", os.path.join(D, "c.mots"), "0", "1", "1", "1", "0", "1"], capture_output=True, cwd=D)
    b = [int(x) for x in open(cm).read().strip().split(";")[0].split(",") if x] if os.path.exists(cm) else None
    return a == b or (isinstance(a, str) and b is None)


# 5. les exemples rejoués par Lugus : vtxc128 écrit code.ex (la ligne, l'égalité, le texte de chaque exemple) et compile
# le programme des exemples, mot pour mot comme vtx128.py ; un exemple faux arrête « lugus PROG.vtx » avec le même message
def ex_vtxc(src, pr, op, ex):
    open(os.path.join(D, "source.vtx"), "w", encoding="utf-8").write(src)
    for f in ("code.mots", "code.ex"):
        if os.path.exists(os.path.join(D, f)):
            os.remove(os.path.join(D, f))
    subprocess.run([EXE, "lancer", os.path.join(D, "c.mots"), "0", str(pr), str(op), "0", "0", "0", str(ex)],
                   capture_output=True, cwd=D)
    cm, ce = os.path.join(D, "code.mots"), os.path.join(D, "code.ex")
    mots = [int(x) for x in open(cm).read().strip().split(";")[0].split(",") if x] if os.path.exists(cm) else None
    return mots, (open(ce, encoding="utf-8").read() if os.path.exists(ce) else "")


AVEC_EXEMPLES = {"chute": open(os.path.join(dex, "chute.vtx"), encoding="utf-8").read(), "contrats": CAS["contrats"],
                 "trois exemples": "reaction moyenne(a, b) -> m {\n    total = a + b -> t\n    moitie = t / 2 -> m\n}\n"
                                   "exemple moyenne(4, 6) == 5\nexemple moyenne(10, 20) == 15;\nexemple moyenne(1, 1) > 0\n"
                                   "fonction principal() { sortie(moyenne(1, 3)); }\n"}
for nom, src in AVEC_EXEMPLES.items():
    an = vtx128.Analyseur(vtx128.lexer(src))
    an.programme()
    attendu = "".join(f"{l}|{int(e[0] == 'bin' and e[1] == '==')}|{t}\n" for e, l, t in an.exemples)
    _, ex = ex_vtxc(src, 1, 1, 0)
    pareils_ = True
    for pr, op in ((1, 1), (1, 0)):
        a = vtx128.assembler(vtx128.programme_des_exemples(src, bool(pr), bool(op)))
        b, _ = ex_vtxc(src, pr, op, 1)
        pareils_ = pareils_ and a == b
    verifier(f"exemples ({nom}) : code.ex juste, le programme des exemples identique (optimisé ou non)",
             ex == attendu and pareils_, f"{ex!r} / {attendu!r}")
faux_ex = AVEC_EXEMPLES["trois exemples"].replace("== 15", "== 16")
open(os.path.join(D, "faux.vtx"), "w", encoding="utf-8").write(faux_ex)
r = subprocess.run([EXE, os.path.join(D, "faux.vtx")], capture_output=True, text=True, encoding="utf-8", errors="replace")
try:
    vtx128.compiler(faux_ex)
    msg_py = "?"
except vtx128.VtxError as e:
    msg_py = str(e)
verifier("lugus refuse un exemple faux, avec le message de vtx128.py", msg_py in r.stdout + r.stderr
         and "sortie" not in r.stdout, (r.stdout + r.stderr)[-300:] + " / " + msg_py)

progs = [open(os.path.join(dex, f), encoding="utf-8").read() for f in sorted(os.listdir(dex))
         if f.endswith(".vtx") and "reaction " in open(os.path.join(dex, f), encoding="utf-8").read()]
progs += [R(random.Random(graine + 1000 + k)).programme() for k in range(max(4, N // 3))]
bons = sum(avec_trace(p) for p in progs)
verifier(f"avec la provenance : {bons}/{len(progs)} programmes, les mêmes mots", bons == len(progs))
print("réactions dans vtxc128 : " + ("tout est conforme" if not echecs else f"{len(echecs)} échec(s)"))
sys.exit(1 if echecs else 0)
