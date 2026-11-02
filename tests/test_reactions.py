#!/usr/bin/env python3
"""Les réactions (docs/vtx-reactions.md), premier temps, dans vtx128.py : les atomes rangés par vagues d'après leurs
liaisons, l'ordre des lignes sans effet, le si sans sinon (la branche qui ne réagit pas), le rendez-vous, le pont vers le
cube, une réaction appelée comme une fonction, la formule de la molécule, les erreurs ; et la forge de Lugus qui en tire
les mêmes sorties.

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
import vtx128  # noqa: E402

vtx128.COMPAT_64 = False
echecs = []


def verifier(nom, ok, detail=""):
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok or not detail else " : " + detail), flush=True)
    if not ok:
        echecs.append(nom)


def jouer(src, entrees=()):
    cpu, _, _ = vtx128.executer(src, list(entrees))
    return cpu.sortie, "".join(chr(c & 0x1FFFFF) for c in cpu.texte), cpu


PANEL = open(os.path.join(racine, "exemples128", "panel.vtx"), encoding="utf-8").read()

# 1. le panel : 42 affiché et rangé dans @2[0]
_, texte, cpu = jouer(PANEL)
verifier("le panel d'atomes : 42 affiché", texte.strip() == "42", repr(texte))
verifier("le pont a rangé 42 dans @2[0]", cpu.lire((2 << 62) | 0) == 42, str(cpu.lire((2 << 62) | 0)))

# 2. l'ordre des lignes ne compte pas : dix tirages au hasard, toujours le même résultat
entete, corps = PANEL.split("reaction principal() {")
lignes = [l for l in corps.split("}")[0].split("\n") if l.strip()]
memes = True
for k in range(10):
    random.Random(k).shuffle(lignes)
    src = entete + "reaction principal() {\n" + "\n".join(lignes) + "\n}\n"
    memes = memes and jouer(src)[1].strip() == "42"
verifier("l'ordre des lignes ne compte pas (10 ordres au hasard)", memes)

# 3. la molécule : vagues et formule
vtx128.REACTIONS.clear()
vtx128.compiler(PANEL)
m = vtx128.REACTIONS["principal"]
verifier("formule CH₄N₆O, masse 116 hex, 7 vagues, produit et somme dans la même vague",
         m.formule() == ("CH₄N₆O", 116) and len(m.vagues) == 7
         and {a.nom for a in m.vagues[1]} == {"produit", "somme"}, f"{m.formule()} {len(m.vagues)}")

# 4. le si sans sinon : la branche ne réagit pas (rien affiché, rien rangé)
_, texte, cpu = jouer(PANEL.replace("= 10 ", "= 13 "))
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
    try:
        vtx128.compiler(src)
        verifier(nom, False, "compilé sans erreur")
    except vtx128.VtxError as e:
        verifier(nom, attendu in str(e), str(e))

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
so, texte, _ = jouer(src)
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
s1, t1, _ = jouer(CONTRAT.replace("MODE", "moyenne(4, 6, 0)"))
verifier("exige rompu : la machine s'arrête et dit lequel", s1 == [5, 2, 0]
         and t1 == "contrat rompu : moyenne exige n != 0 (ligne 3)\n", f"{s1} {t1!r}")
s2, t2, _ = jouer(CONTRAT.replace("MODE", "tordue(1)"))
verifier("garantit rompu : idem, après la réaction", s2 == [5, 2, 0] and "tordue garantit y < 50 (ligne 10)" in t2, f"{s2} {t2!r}")
s3, t3, _ = jouer(CONTRAT.replace("MODE", "1"))
verifier("une branche qui n'a pas réagi ne promet rien ; tenus, les contrats ne changent rien", s3 == [5, 2, 0, 1, 99] and t3 == "",
         f"{s3} {t3!r}")
for nom, src, attendu in [
        ("exige sur autre chose qu'une entrée", "reaction f(a) -> b { = a + 1 -> b\n exige b > 0 }\nfonction principal() { sortie(f(1)); }",
         "ne parle que des entrées"),
        ("garantit sur une liaison absente", "reaction f(a) -> b { = a + 1 -> b\n garantit c > 0 }\nfonction principal() { sortie(f(1)); }",
         "qu'aucun atome ne donne")]:
    try:
        vtx128.compiler(src)
        verifier(f"erreur détectée : {nom}", False, "pas d'erreur")
    except vtx128.VtxError as e:
        verifier(f"erreur détectée : {nom}", attendu in str(e), str(e))

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
_, t4, _ = jouer(FAUX)
verifier("un résultat qui porte faux : faux pour une logique, inconnu pour un flottant", t4.split() == ["4.0", "inconnu", "vrai", "faux", "faux"], repr(t4))
try:
    vtx128.compiler("reaction g(x) -> r { = si x > 0 alors x -> r }\nfonction principal() { sortie(g(2)); }")
    verifier("un entier rendu qui peut porter faux est refusé", False, "pas d'erreur")
except vtx128.VtxError as e:
    verifier("un entier rendu qui peut porter faux est refusé", "écrivez un sinon" in str(e), str(e))

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
try:
    vtx128.compiler(EXEMPLE.replace("ATTENDU", "16"))
    verifier("un exemple faux arrête la compilation", False, "pas d'erreur")
except vtx128.VtxError as e:
    verifier("un exemple faux arrête la compilation, avec ce que vaut le côté gauche",
             str(e) == "ligne 7 : l'exemple « moyenne(10, 20) == 16 » est faux : le côté gauche vaut 15", str(e))

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
s_, t_, _ = jouer(UNITES)
verifier("les unités : 2 km + 500 m = 2500 m ; √(2h/g) en s ; kg·m²/s² = J", s_ == [2500, 18] and t_.startswith("2.0192751093846"),
         f"{s_} {t_!r}")
avant = vtx128.assembler(vtx128.compiler(UNITES.replace("garantit vitesse > 0 m/s", "")))
sans = UNITES.replace("garantit vitesse > 0 m/s", "").replace(" m/s²", "").replace(": flottant s", ": flottant").replace("flottant m,", "flottant,") \
    .replace("2 km", "2000").replace("500 m ", "500 ").replace("3 min", "180").replace(": m/s", "").replace("> 0 m/s", "> 0") \
    .replace("-> d: m", "-> d").replace("masse: kg, v: m/s) -> e: J", "masse, v) -> e")
verifier("les unités ne coûtent rien : les mêmes mots qu'écrit sans unités", vtx128.assembler(vtx128.compiler(sans)) == avant)
for nom, (de, vers), attendu in [
        ("des m + des s", ("= aller + rentree    -> d: m", "= aller + duree -> d"), "« + » entre des m et des s"),
        ("une liaison déclarée dans une autre unité", ("-> vitesse: m/s", "-> vitesse: m"), "déclarée en m, et porte des m/s"),
        ("un résultat déclaré dans une autre unité", ("-> e: J", "-> e: W"), "rend des kg·m²/s³ (déclaré), et son résultat porte des kg·m²/s²"),
        ("un argument dans la mauvaise unité", ("sortie(trajet());", "sortie(trajet());\n}\nreaction r() -> x { = energie(2 kg, 3 s) -> x"),
         "« energie » attend des m/s pour v, et reçoit des s"),
        ("la racine d'une unité impaire", ("= racine(carre)", "= racine(double)"), "ne tombe pas juste"),
        ("un entier qui ne tombe pas juste dans l'unité de base", ("= 500 m ", "= 500 g "), "écrivez-le à virgule"),
        ("un nombre sans unité ajouté à des m", ("= 2.0 × h", "= 2.0 + h"), "des nombres sans unité et des m")]:
    try:
        vtx128.compiler(UNITES.replace(de, vers))
        verifier(f"unités, erreur détectée : {nom}", False, "pas d'erreur")
    except vtx128.VtxError as e:
        verifier(f"unités, erreur détectée : {nom}", attendu in str(e), str(e))

CHUTE = open(os.path.join(racine, "exemples128", "chute.vtx"), encoding="utf-8").read()
s_, t_, _ = jouer(CHUTE)
verifier("l'exemple de la chute : unités, contrats et exemples ensemble ; le message cite le source tel qu'écrit",
         s_ == [2500] and t_.endswith("contrat rompu : chute exige h >= 0.0 (ligne 6)\n"), f"{s_} {t_!r}")

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

lugus = os.path.join(racine, "vtx-rs", "target", "release", "lugus" + (".exe" if os.name == "nt" else ""))
if shutil.which("rustc") and os.path.exists(lugus):
    tmp = tempfile.mkdtemp(prefix="reactions-")
    bons = True
    for src in [CONTRAT.replace("MODE", m) for m in ("moyenne(4, 6, 0)", "tordue(1)", "1")] + [UNITES, CHUTE, SCENE, ALTERNANCE]:
        prog = os.path.join(tmp, "c.vtx")
        open(prog, "w", encoding="utf-8").write(src)
        mots = os.path.join(tmp, "c.mots")
        open(mots, "w").write(",".join(map(str, vtx128.assembler(vtx128.compiler(src)))) + ";\n")
        emule = subprocess.run([lugus, "lancer", mots], capture_output=True, text=True).stdout
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
    mots = os.path.join(tmp, "p.mots")
    open(mots, "w").write(",".join(map(str, vtx128.assembler(vtx128.compiler(PARALLELE)))) + ";\n")
    emule = subprocess.run([lugus, "lancer", mots], capture_output=True, text=True).stdout.strip()
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
s16, t16, _ = jouer(ERREURS_A)
verifier("reparer et erreur() : 0, 5, 0, 21 ; un flottant rend variable ; puis l'erreur non réparée arrête la machine",
         s16 == [0, 5, 0, 21, 5] and t16 == "variable\n0.25\nerreur non réparée dans moyenne : division par zéro, ligne 3 (t / n)\n",
         f"{s16} {t16!r}")
s17, t17, _ = jouer(ERREURS_B)
verifier("le rendez-vous, le pont, le reste, la logique, le flottant de 32 bits ; l'effet arrête le premier (vague 1)",
         s17 == [5, 2, 0] and t17 == "2\nvariable\nvrai\nvariable\nerreur non réparée dans tout : division par zéro, ligne 5 (afficher(b / n))\n",
         f"{s17} {t17!r}")
sans = "reaction f(a) -> b {\n    = a / 4 -> b\n}\nfonction principal() { sortie(f(8)); }\n"
avec = sans.replace("a / 4", "a / a")
n_sans = len(vtx128.assembler(vtx128.compiler(sans)))
verifier("diviser par une valeur écrite non nulle ne coûte rien (aucun drapeau)", "__err" not in vtx128.compiler(sans, optim=False)
         and "__err" in vtx128.compiler(avec, optim=False), str(n_sans))
f16 = os.path.join(tempfile.mkdtemp(), "e.vtx")
open(f16, "w", encoding="utf-8").write("reaction g(n) -> r: flottant {\n    = 10.0 / flottant(n) -> q\n    = q + 1.0 -> r\n}\n"
                                       "fonction principal() { afficher(g(0)); }\n")
r16 = subprocess.run([sys.executable, os.path.join(racine, "vtx128.py"), "pourquoi", f16], capture_output=True, text=True, encoding="utf-8")
verifier("la provenance dit variable : l'erreur, la division par zéro, non réparée",
         "q variable (une erreur, une division par zéro, non réparée" in r16.stdout, r16.stdout[-400:])

# 17. les tableaux dans les réactions : pour chaque sans réduction (un tableau), pour chaque x dans t, garder, la somme
# d'un tableau ; des flottants avec -> t: flottant[]
TABLEAUX = 'reaction carres(n) -> t {\n    = pour chaque i dans 0..n : i × i -> t\n}\nreaction stats(t) -> s {\n    = somme pour chaque x dans t : x -> total\n    = max pour chaque x dans t : x -> grand\n    = garder x dans t si x % 2 == 0 -> pairs\n    = pour chaque x dans pairs : x + 1 -> plus\n    = longueur(plus) -> np\n    = total × 1000 + grand × 10 + np -> s\n}\nreaction moities(t) -> m: flottant[] {\n    = pour chaque x dans t : flottant(x) * 0.5 -> m: flottant[]\n}\nfonction principal() {\n    soit t = carres(6);\n    pour x dans t { sortie(x); }\n    sortie(stats(t));\n    soit m = moities(t);\n    pour y dans m { afficher(y); }\n}\n'
s18, t18, _ = jouer(TABLEAUX)
verifier("les carrés 0..6, puis 55 · 25 · 3 pairs (55253), puis les moitiés en flottants",
         s18 == [0, 1, 4, 9, 16, 25, 55253] and t18.split() == ["0.0", "0.5", "2.0", "4.5", "8.0", "12.5"], f"{s18} {t18!r}")
s19, t19, _ = jouer('reaction grands(m: flottant[]) -> g: flottant[] {\n    = garder y dans m si y > 2.0 -> g\n}\nfonction principal() {\n    soit m = [1.5, 2.5, 0.5, 4.0];\n    soit g = grands(m);\n    sortie(longueur(g));\n    pour y dans g { afficher(y); }\n}\n')
verifier("garder sur des flottants : la copie garde leur genre", s19 == [2] and t19.split() == ["2.5", "4.0"], f"{s19} {t19!r}")
try:
    vtx128.compiler("reaction f(n) -> t {\n    = pour chaque n dans 0..3 : n -> t\n}\nfonction principal() { sortie(f(1)); }\n")
    verifier("la variable d'un pour chaque ne porte pas le nom d'une liaison", False, "pas d'erreur")
except vtx128.VtxError as e:
    verifier("la variable d'un pour chaque ne porte pas le nom d'une liaison", "porte le nom d'une liaison" in str(e), str(e))

# 18. plusieurs résultats (-> q, r) et selon dans les réactions
s20, t20, _ = jouer('reaction divmod(a, b) -> q, r {\n    = reparer a / b par 0  -> q\n    = reparer a % b par 0  -> r\n}\nreaction deux(x: flottant) -> m: flottant, v: logique {\n    = x * 0.5 -> m\n    = logique(x > 1.0) -> v\n}\nreaction usage(n) -> t {\n    = divmod(n, 7) -> q, r\n    = q × 100 + r -> t\n}\nreaction nom(c) -> t {\n    = selon c { 1: 10 ; 2, 3: 20 ; autre: 99 } -> t\n}\nreaction belnap(q: logique) -> n: flottant {\n    = selon q { vrai: 1.0 ; faux: 0.0 } -> n\n}\nreaction autre_usage(x: flottant) -> s: flottant {\n    = deux(x) -> m, v\n    = si v == vrai alors m sinon 0.0 - m -> s\n}\nfonction principal() {\n    sortie(usage(45)); sortie(divmod(45, 7));\n    sortie(nom(1)); sortie(nom(3)); sortie(nom(8));\n    afficher(belnap(vrai)); afficher(belnap(faux)); afficher(belnap(inconnu));\n    afficher(autre_usage(4.0)); afficher(autre_usage(0.5));\n}\n')
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
    s_emu, _, _ = jouer(SOUV4)
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
