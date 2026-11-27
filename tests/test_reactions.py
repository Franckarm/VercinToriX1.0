#!/usr/bin/env python3
"""Les réactions (docs/vtx-reactions.md), jouées par lugus seul (0.851 : un seul compilateur, vtxc128) : l'ordre des
lignes sans effet, le si sans sinon (la branche qui ne réagit pas), le rendez-vous, le pont vers le cube, une réaction
appelée comme une fonction, les contrats, les exemples, les unités, les erreurs, les tableaux, plusieurs résultats ; et
la forge de Lugus qui en tire les mêmes sorties. Ce que le lecteur de la forge en comprend (la molécule, les souvenirs,
la provenance) : tests/test_reactions_lecteur.py.

    python3 tests/test_reactions.py"""
import os
import random
import shutil
import subprocess
import sys
import tempfile

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, racine)
sys.path.insert(0, os.path.join(racine, "forge"))
from un_compilateur import LUGUS, compiler_texte  # noqa: E402

echecs = []
D = tempfile.mkdtemp(prefix="reactions-lugus-")


def verifier(nom, ok, detail=""):
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok or not detail else " : " + detail), flush=True)
    if not ok:
        echecs.append(nom)


def jouer(src, entrees=()):
    """(les valeurs de sortie(), le texte affiché) : lugus écrit les sorties en tête, sur une ligne, séparées par des
    virgules, puis le texte"""
    f = os.path.join(D, "p.vtx")
    open(f, "w", encoding="utf-8").write(src)
    r = subprocess.run([LUGUS, f] + [str(e) for e in entrees], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=D, stdin=subprocess.DEVNULL, timeout=600)
    t = r.stdout
    sorties = []
    if "sortie(" in src and t:
        l0 = t.split("\n")[0]
        if l0 and all(x.lstrip("-").isdigit() for x in l0.split(",")):
            sorties = [int(x) for x in l0.split(",")]
            t = t[len(l0) + 1:]
    return sorties, t


def refus(src):
    """le message de vtxc128 s'il refuse src, sinon None"""
    m, msg = compiler_texte(src, dossier=D)
    return None if m is not None else msg


PANEL = open(os.path.join(racine, "exemples128", "panel.vtx"), encoding="utf-8").read()

# 1. le panel : 42 affiché et rangé dans @2[0]
_, texte = jouer(PANEL)
verifier("le panel d'atomes : 42 affiché", texte.strip() == "42", repr(texte))
_, t0 = jouer(PANEL.replace("reaction principal()", "reaction panel()") + "\nfonction principal() { panel(); afficher(@2[0]); }\n")
verifier("le pont a rangé 42 dans @2[0]", t0.split() == ["42", "42"], repr(t0))

# 2. l'ordre des lignes ne compte pas : dix tirages au hasard, toujours le même résultat
entete, corps = PANEL.split("reaction principal() {")
lignes = [l for l in corps.split("}")[0].split("\n") if l.strip()]
memes = True
for k in range(10):
    random.Random(k).shuffle(lignes)
    src = entete + "reaction principal() {\n" + "\n".join(lignes) + "\n}\n"
    memes = memes and jouer(src)[1].strip() == "42"
verifier("l'ordre des lignes ne compte pas (10 ordres au hasard)", memes)

# 3. la molécule (vagues, formule) : tests/test_reactions_lecteur.py

# 4. le si sans sinon : la branche ne réagit pas (rien affiché, rien rangé)
_, texte = jouer(PANEL.replace("= 10 ", "= 13 "))
verifier("si faux : la suite de la branche ne réagit pas", texte == "", repr(texte))

# 5. une réaction appelée comme une fonction, avec un résultat
src = """reaction moyenne(a, b) -> m {
    = a + b      -> s
    = s / 2      -> m
}
fonction principal() { sortie(moyenne(4, 6)); sortie(moyenne(10, 20)); }
"""
verifier("une réaction rend un résultat (moyenne)", jouer(src)[0] == [5, 15])

# 6. si … alors … sinon
src = """reaction choisir(x) -> r {
    = si x > 10 alors x - 10 sinon x + 100   -> r
}
fonction principal() { sortie(choisir(15)); sortie(choisir(3)); }
"""
verifier("si … alors … sinon", jouer(src)[0] == [5, 103])

# 7. les erreurs
for nom, src, attendu in [
    ("un cycle est refusé", "reaction principal() { = b + 1 -> a\n = a + 1 -> b\n }", "cycle"),
    ("une liaison donnée deux fois", "reaction principal() { = 1 -> a\n = 2 -> a\n }", "déjà donnée"),
    ("un rendez-vous donne autant qu'il reçoit", "reaction principal() { = 1 -> a\n = rendez-vous(a, a) -> b\n }", "rendez-vous"),
    ("une liaison inconnue", "reaction principal() { = z + 1 -> a\n = afficher(a)\n }", "inconnue"),
]:
    e = refus(src)
    verifier(nom, e is not None and attendu in e, str(e))

# 8. les ponts : ensemble, sauf ceux qui touchent la même chose (dans l'ordre des lignes) ; « apres » écrit
src = """reaction principal() {
    = afficher("b")   apres premier
    premier = afficher("a")
    = 1   -> x
    = 2   -> y
    = pont x vers @2[5]  -> x2
    = pont y vers @2[5]  -> y2
    = pont y vers @2[6]
    = sortie(@2[5])
}
"""
so, texte = jouer(src)
verifier("deux ponts sur la même case gardent l'ordre des lignes ; « apres » écrit ; la lecture vient après", so == [2] and texte == "a\nb\n",
         f"{so} {texte!r}")

# 9. somme pour chaque, et deux atomes lourds dans la même vague : forgés sur plusieurs cœurs, mêmes sorties que Lugus
# émulé
PARALLELE = """fonction carre_mod(i) { soit k = 0; soit x = i; tantque k < 20 { x = (x * x + 7) % 1000003; k = k + 1; } retour x; }
fonction tranche(a, b) { soit s = 0; pour i dans a..b { s = s + carre_mod(i); } retour s; }
reaction principal() {
    total = somme pour chaque i dans 0..50000 : carre_mod(i)   -> t
    petit = min pour chaque i dans 1..3000 : carre_mod(i)      -> m
    grand = max pour chaque i dans 1..3000 : carre_mod(i)      -> g
    haut  = tranche(0, 20000)                                 -> h
    bas   = tranche(20000, 40000)                             -> b
    = sortie(t)
    = sortie(m)
    = sortie(g)
    = sortie(h + b)
}
"""
# 11. les contrats : exige (avant toute réaction), garantit (à la fin) ; rompu, la machine s'arrête en le disant
CONTRAT = """
reaction moyenne(a, b, n) -> m {
    exige n != 0
    total = a + b      -> t
    part  = t / n      -> m
    garantit m <= t
}
reaction tordue(x) -> y {
    = x + 100          -> y
    garantit y < 50
}
reaction prudente(x: flottant) -> r: flottant {
    = si x > 10.0 alors x - 10.0 -> r
    garantit r < 5.0
}
fonction principal() {
    sortie(moyenne(4, 6, 2));
    sortie(entier(prudente(12.0)));
    sortie(prudente(3.0));
    sortie(MODE);
    sortie(99);
}
"""
s1, t1 = jouer(CONTRAT.replace("MODE", "moyenne(4, 6, 0)"))
verifier("exige rompu : la machine s'arrête et dit lequel", s1 == [5, 2, 0]
         and t1 == "contrat rompu : moyenne exige n != 0 (ligne 3)\n", f"{s1} {t1!r}")
s2, t2 = jouer(CONTRAT.replace("MODE", "tordue(1)"))
verifier("garantit rompu : idem, après la réaction", s2 == [5, 2, 0] and "tordue garantit y < 50 (ligne 10)" in t2, f"{s2} {t2!r}")
s3, t3 = jouer(CONTRAT.replace("MODE", "1"))
verifier("une branche qui n'a pas réagi ne promet rien ; tenus, les contrats ne changent rien", s3 == [5, 2, 0, 1, 99] and t3 == "",
         f"{s3} {t3!r}")
for nom, src, attendu in [
        ("exige sur autre chose qu'une entrée", "reaction f(a) -> b { = a + 1 -> b\n exige b > 0 }\nfonction principal() { sortie(f(1)); }",
         "ne parle que des entrées"),
        ("garantit sur une liaison absente", "reaction f(a) -> b { = a + 1 -> b\n garantit c > 0 }\nfonction principal() { sortie(f(1)); }",
         "qu'aucun atome ne donne")]:
    e = refus(src)
    verifier(f"erreur détectée : {nom}", e is not None and attendu in e, str(e))

# une réaction qui rend une liaison portant faux le dit avec son type : une logique rend faux, un flottant inconnu (la
# valeur n'est jamais arrivée) ; un entier ne sait pas le dire, le compilateur demande un sinon
FAUX = """
reaction garde(x: flottant) -> r: flottant {
    = si x > 0.0 alors x × 2.0 -> r
}
reaction test(x) -> v: logique {
    = logique(x > 3) -> c
    = si x > 0 alors c -> v
}
fonction principal() { afficher(garde(2.0)); afficher(garde(-1.0)); afficher(test(5)); afficher(test(1)); afficher(test(0)); }
"""
_, t4 = jouer(FAUX)
verifier("un résultat qui porte faux : faux pour une logique, inconnu pour un flottant", t4.split() == ["4.0", "inconnu", "vrai", "faux", "faux"], repr(t4))
e = refus("reaction g(x) -> r { = si x > 0 alors x -> r }\nfonction principal() { sortie(g(2)); }")
verifier("un entier rendu qui peut porter faux est refusé", e is not None and "écrivez un sinon" in e, str(e))

# 12. les exemples vérifiés : rejoués à chaque compilation
EXEMPLE = """
reaction moyenne(a, b) -> m {
    total  = a + b     -> t
    moitie = t / 2     -> m
}
exemple moyenne(4, 6) == 5
exemple moyenne(10, 20) == ATTENDU
exemple moyenne(1, 1) > 0
fonction principal() { sortie(moyenne(1, 3)); }
"""
verifier("des exemples justes : la compilation passe", jouer(EXEMPLE.replace("ATTENDU", "15"))[0] == [2])
# (les exemples se rejouent avant de lancer le programme : « lugus PROG.vtx » s'arrête)
f_ex = os.path.join(D, "ex.vtx")
open(f_ex, "w", encoding="utf-8").write(EXEMPLE.replace("ATTENDU", "16"))
r_ex = subprocess.run([LUGUS, f_ex], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=D)
verifier("un exemple faux arrête la compilation, avec ce que vaut le côté gauche",
         r_ex.returncode != 0 and "ligne 7 : l'exemple « moyenne(10, 20) == 16 » est faux : le côté gauche vaut 15"
         in r_ex.stdout + r_ex.stderr, r_ex.stdout + r_ex.stderr)

# 13. les unités physiques : suivies le long des liaisons, vérifiées à la compilation, effacées à l'exécution
UNITES = """
reaction chute(h: flottant m, g: flottant m/s²) -> t: flottant s {
    = 2.0 × h            -> double
    = double ÷ g         -> carre
    = racine(carre)      -> t
}
reaction trajet() -> d {
    = 2 km               -> aller
    = 500 m              -> rentree
    = 3 min              -> duree
    = aller + rentree    -> d: m
    = d / duree          -> vitesse: m/s
    garantit vitesse > 0 m/s
}
reaction energie(masse: kg, v: m/s) -> e: J {
    = masse × v × v      -> e
}
fonction principal() {
    afficher(chute(20.0, 9.81));
    sortie(trajet());
    sortie(energie(2, 3));
}
"""
s_, t_ = jouer(UNITES)
verifier("les unités : 2 km + 500 m = 2500 m ; √(2h/g) en s ; kg·m²/s² = J", s_ == [2500, 18] and t_.startswith("2.0192751093846"),
         f"{s_} {t_!r}")
avant = compiler_texte(UNITES.replace("garantit vitesse > 0 m/s", ""), dossier=D)[0]
sans = UNITES.replace("garantit vitesse > 0 m/s", "").replace(" m/s²", "").replace(": flottant s", ": flottant").replace("flottant m,", "flottant,") \
    .replace("2 km", "2000").replace("500 m ", "500 ").replace("3 min", "180").replace(": m/s", "").replace("> 0 m/s", "> 0") \
    .replace("-> d: m", "-> d").replace("masse: kg, v: m/s) -> e: J", "masse, v) -> e")
verifier("les unités ne coûtent rien : les mêmes mots qu'écrit sans unités", avant is not None and compiler_texte(sans, dossier=D)[0] == avant)
for nom, (de, vers), attendu in [
        ("des m + des s", ("= aller + rentree    -> d: m", "= aller + duree -> d"), "« + » entre des m et des s"),
        ("une liaison déclarée dans une autre unité", ("-> vitesse: m/s", "-> vitesse: m"), "déclarée en m, et porte des m/s"),
        ("un résultat déclaré dans une autre unité", ("-> e: J", "-> e: W"), "rend des kg·m²/s³ (déclaré), et son résultat porte des kg·m²/s²"),
        ("un argument dans la mauvaise unité", ("sortie(trajet());", "sortie(trajet());\n}\nreaction r() -> x { = energie(2 kg, 3 s) -> x"),
         "« energie » attend des m/s pour v, et reçoit des s"),
        ("la racine d'une unité impaire", ("= racine(carre)", "= racine(double)"), "ne tombe pas juste"),
        ("un entier qui ne tombe pas juste dans l'unité de base", ("= 500 m ", "= 500 g "), "écrivez-le à virgule"),
        ("un nombre sans unité ajouté à des m", ("= 2.0 × h", "= 2.0 + h"), "des nombres sans unité et des m")]:
    e = refus(UNITES.replace(de, vers))
    verifier(f"unités, erreur détectée : {nom}", e is not None and attendu in e, str(e))

CHUTE = open(os.path.join(racine, "exemples128", "chute.vtx"), encoding="utf-8").read()
s_, t_ = jouer(CHUTE)
verifier("l'exemple de la chute : unités, contrats et exemples ensemble ; le message cite le source tel qu'écrit",
         s_ == [2500] and t_.endswith("contrat rompu : chute exige h >= 0.0 (ligne 6)\n"), f"{s_} {t_!r}")

# 14. le calcul incrémental : les souvenirs des atomes lourds (ce qu'ils épargnent, qui en a :
# tests/test_reactions_lecteur.py) ; ici, ce que la scène et l'alternance rendent
SCENE = open(os.path.join(racine, "exemples128", "scene_incrementale.vtx"), encoding="utf-8").read()
s_sc, _ = jouer(SCENE)
verifier("la scène rappelée 60 fois : 382460", s_sc == [382460], str(s_sc))
ALTERNANCE = open(os.path.join(racine, "exemples128", "alternance.vtx"), encoding="utf-8").read()

lugus = LUGUS
if shutil.which("rustc") and os.path.exists(lugus):
    tmp = tempfile.mkdtemp(prefix="reactions-")
    bons = True
    for src in [CONTRAT.replace("MODE", m) for m in ("moyenne(4, 6, 0)", "tordue(1)", "1")] + [UNITES, CHUTE, SCENE, ALTERNANCE]:
        prog = os.path.join(tmp, "c.vtx")
        open(prog, "w", encoding="utf-8").write(src)
        emule = subprocess.run([lugus, prog], capture_output=True, text=True).stdout
        exe = os.path.join(tmp, "c" + (".exe" if os.name == "nt" else ""))
        subprocess.run([sys.executable, os.path.join(racine, "forge", "forge128.py"), prog, "-o", exe], capture_output=True, text=True)
        forge = subprocess.run([exe], capture_output=True, text=True).stdout
        bons = bons and emule == forge and emule != ""
    verifier("contrats, unités et souvenirs : Lugus (Rust) et la forge disent la même chose", bons)
    shutil.rmtree(tmp, ignore_errors=True)
if shutil.which("rustc") and os.path.exists(lugus):
    tmp = tempfile.mkdtemp(prefix="reactions-")
    prog = os.path.join(tmp, "parallele.vtx")
    open(prog, "w", encoding="utf-8").write(PARALLELE)
    emule = subprocess.run([lugus, prog], capture_output=True, text=True).stdout.strip()
    exe = os.path.join(tmp, "p" + (".exe" if os.name == "nt" else ""))
    rs = os.path.join(tmp, "p.rs")
    subprocess.run([sys.executable, os.path.join(racine, "forge", "forge128.py"), prog, "-o", exe, "--rs", rs],
                   capture_output=True, text=True)
    forge = subprocess.run([exe], capture_output=True, text=True).stdout.strip()
    code = open(rs, encoding="utf-8").read() if os.path.exists(rs) else ""
    verifier("somme / min / max pour chaque, et la vague de deux atomes lourds : forgés sur plusieurs cœurs, mêmes sorties",
             emule == forge and emule != "" and code.count("thread::scope") >= 4, f"émulé {emule!r} ; forgé {forge!r}")
    shutil.rmtree(tmp, ignore_errors=True)

# 16. les erreurs (2.8) : une division par zéro donne une liaison variable avec sa cause ; reparer, erreur() ; un effet ou
# un résultat entier qui la reçoit arrête la machine avec son message ; un flottant, une logique rendent variable
ERREURS_A = 'reaction moyenne(a, b, n) -> m {\n    = a + b          -> t\n    = t / n          -> m\n}\nreaction sure(a, b, n) -> m {\n    = a + b          -> t\n    = reparer t / n par 0  -> m\n}\nreaction regarde(n) -> r {\n    = 100 / n        -> q\n    = si erreur(q) alors 0 sinon q + 1   -> r\n}\nreaction fl(x: flottant) -> y: flottant {\n    = 1.0 / x        -> y\n}\nfonction principal() {\n    sortie(sure(4, 6, 0)); sortie(sure(4, 6, 2));\n    sortie(regarde(0)); sortie(regarde(5));\n    afficher(fl(0.0)); afficher(fl(4.0));\n    sortie(moyenne(4, 6, 2));\n    sortie(moyenne(4, 6, 0));\n    sortie(99);\n}\n'
ERREURS_B = 'reaction tout(a, b, n) -> r {\n    = a / n                 -> q\n    = rendez-vous(q, b % n) -> q2, m2\n    = pont q2 vers @2[3]    -> q3\n    = afficher(b / n)\n    = reparer q3 + m2 par 7 -> r\n    garantit q >= 0\n}\nreaction lo(x) -> v: logique {\n    = logique(x / x > 0)    -> v\n}\nreaction petit(x: flottant_32) -> y: flottant_32 {\n    = 1.0S / x -> y\n}\nreaction cond(x) -> z {\n    = si x > 0 alors 10 / x sinon 0 -> z0\n    = reparer z0 par 0 -> z\n}\nfonction principal() {\n    sortie(tout(8, 5, 2)); sortie(cond(5)); sortie(cond(0));\n    afficher(lo(0)); afficher(lo(3)); afficher(petit(0.0S));\n    sortie(tout(8, 5, 0));\n}\n'
s16, t16 = jouer(ERREURS_A)
verifier("reparer et erreur() : 0, 5, 0, 21 ; un flottant rend variable ; puis l'erreur non réparée arrête la machine",
         s16 == [0, 5, 0, 21, 5] and t16 == "variable\n0.25\nerreur non réparée dans moyenne : division par zéro, ligne 3 (t / n)\n",
         f"{s16} {t16!r}")
s17, t17 = jouer(ERREURS_B)
verifier("le rendez-vous, le pont, le reste, la logique, le flottant de 32 bits ; l'effet arrête le premier (vague 1)",
         s17 == [5, 2, 0] and t17 == "2\nvariable\nvrai\nvariable\nerreur non réparée dans tout : division par zéro, ligne 5 (afficher(b / n))\n",
         f"{s17} {t17!r}")
# (le drapeau d'erreur d'une division, la provenance : tests/test_reactions_lecteur.py)

# 17. les tableaux dans les réactions : pour chaque sans réduction (un tableau), pour chaque x dans t, garder, la somme
# d'un tableau ; des flottants avec -> t: flottant[]
TABLEAUX = 'reaction carres(n) -> t {\n    = pour chaque i dans 0..n : i × i -> t\n}\nreaction stats(t) -> s {\n    = somme pour chaque x dans t : x -> total\n    = max pour chaque x dans t : x -> grand\n    = garder x dans t si x % 2 == 0 -> pairs\n    = pour chaque x dans pairs : x + 1 -> plus\n    = longueur(plus) -> np\n    = total × 1000 + grand × 10 + np -> s\n}\nreaction moities(t) -> m: flottant[] {\n    = pour chaque x dans t : flottant(x) * 0.5 -> m: flottant[]\n}\nfonction principal() {\n    soit t = carres(6);\n    pour x dans t { sortie(x); }\n    sortie(stats(t));\n    soit m = moities(t);\n    pour y dans m { afficher(y); }\n}\n'
s18, t18 = jouer(TABLEAUX)
verifier("les carrés 0..6, puis 55 · 25 · 3 pairs (55253), puis les moitiés en flottants",
         s18 == [0, 1, 4, 9, 16, 25, 55253] and t18.split() == ["0.0", "0.5", "2.0", "4.5", "8.0", "12.5"], f"{s18} {t18!r}")
s19, t19 = jouer('reaction grands(m: flottant[]) -> g: flottant[] {\n    = garder y dans m si y > 2.0 -> g\n}\nfonction principal() {\n    soit m = [1.5, 2.5, 0.5, 4.0];\n    soit g = grands(m);\n    sortie(longueur(g));\n    pour y dans g { afficher(y); }\n}\n')
verifier("garder sur des flottants : la copie garde leur genre", s19 == [2] and t19.split() == ["2.5", "4.0"], f"{s19} {t19!r}")
e = refus("reaction f(n) -> t {\n    = pour chaque n dans 0..3 : n -> t\n}\nfonction principal() { sortie(f(1)); }\n")
verifier("la variable d'un pour chaque ne porte pas le nom d'une liaison", e is not None and "porte le nom d'une liaison" in e, str(e))

# 18. plusieurs résultats (-> q, r) et selon dans les réactions
s20, t20 = jouer('reaction divmod(a, b) -> q, r {\n    = reparer a / b par 0  -> q\n    = reparer a % b par 0  -> r\n}\nreaction deux(x: flottant) -> m: flottant, v: logique {\n    = x * 0.5 -> m\n    = logique(x > 1.0) -> v\n}\nreaction usage(n) -> t {\n    = divmod(n, 7) -> q, r\n    = q × 100 + r -> t\n}\nreaction nom(c) -> t {\n    = selon c { 1: 10 ; 2, 3: 20 ; autre: 99 } -> t\n}\nreaction belnap(q: logique) -> n: flottant {\n    = selon q { vrai: 1.0 ; faux: 0.0 } -> n\n}\nreaction autre_usage(x: flottant) -> s: flottant {\n    = deux(x) -> m, v\n    = si v == vrai alors m sinon 0.0 - m -> s\n}\nfonction principal() {\n    sortie(usage(45)); sortie(divmod(45, 7));\n    sortie(nom(1)); sortie(nom(3)); sortie(nom(8));\n    afficher(belnap(vrai)); afficher(belnap(faux)); afficher(belnap(inconnu));\n    afficher(autre_usage(4.0)); afficher(autre_usage(0.5));\n}\n')
verifier("divmod(45, 7) -> 6, 3 ; selon : 10, 20, 99 ; selon logique sans autre : faux devient inconnu ; deux résultats flottant et logique",
         s20 == [603, 6, 10, 20, 99] and t20.split() == ["1.0", "0.0", "inconnu", "2.0", "-0.25"], f"{s20} {t20!r}")

# 10. la forge de Lugus : mêmes sorties
if shutil.which("rustc"):
    tmp = tempfile.mkdtemp(prefix="reactions-")
    exe = os.path.join(tmp, "panel" + (".exe" if os.name == "nt" else ""))
    r = subprocess.run([sys.executable, os.path.join(racine, "forge", "forge128.py"),
                        os.path.join(racine, "exemples128", "panel.vtx"), "-o", exe], capture_output=True, text=True)
    sortie = subprocess.run([exe], capture_output=True, text=True).stdout if r.returncode == 0 else r.stderr
    verifier("forgé pour Lugus : le même 42", sortie.strip() == "42", sortie[-300:])
    # les souvenirs et les cœurs : quatre atomes lourds d'une vague gardent chacun un souvenir ; la forge fait réagir
    # sur plusieurs cœurs ceux qui l'ont oublié. Le même total que la machine émulée, sur un cœur comme sur plusieurs.
    SOUV4 = ("fonction lourd(n) {\n    soit s = 0;\n    pour i dans 0..n { s = s + (i * i) % 7; }\n    retour s;\n}\n"
             "reaction scene(decor) -> r {\n    = lourd(decor) -> a\n    = lourd(decor + 1) -> b\n    = lourd(decor + 2) -> c\n"
             "    = lourd(decor + 3) -> d\n    = a + b + c + d -> r\n}\nfonction principal() {\n    soit total = 0;\n"
             "    pour k dans 0..60 { total = total + scene(300 + (k / 10) * 7); }\n    sortie(total);\n}\n")
    s_emu, _ = jouer(SOUV4)
    f_s4 = os.path.join(tmp, "souv4.vtx")
    open(f_s4, "w", encoding="utf-8").write(SOUV4)
    exe = os.path.join(tmp, "souv4" + (".exe" if os.name == "nt" else ""))
    r = subprocess.run([sys.executable, os.path.join(racine, "forge", "forge128.py"), f_s4, "-o", exe, "--rs",
                        os.path.join(tmp, "souv4.rs")], capture_output=True, text=True)
    rs_txt = open(os.path.join(tmp, "souv4.rs"), encoding="utf-8").read() if r.returncode == 0 else ""
    plusieurs = subprocess.run([exe], capture_output=True, text=True).stdout.strip() if r.returncode == 0 else r.stderr
    un = subprocess.run([exe], capture_output=True, text=True, env=dict(os.environ, VTX_COEURS="1")).stdout.strip() \
        if r.returncode == 0 else ""
    verifier("les souvenirs et les cœurs : la vague de quatre atomes à souvenir partagée entre les cœurs, le même total "
             "(émulé, forgé sur un cœur, sur plusieurs)",
             "n_oublies" in rs_txt and plusieurs == un == str(s_emu[0]), f"{s_emu} {plusieurs!r} {un!r}")
    shutil.rmtree(tmp, ignore_errors=True)

print("réactions : " + ("tout est conforme" if not echecs else f"{len(echecs)} échec(s)"))
sys.exit(1 if echecs else 0)
