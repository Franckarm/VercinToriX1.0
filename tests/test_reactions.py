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
reaction prudente(x) -> r {
    = si x > 10 alors x - 10 -> r
    garantit r < 5
}
fonction principal() {
    sortie(moyenne(4, 6, 2));
    sortie(prudente(3));
    sortie(prudente(12));
    sortie(MODE);
    sortie(99);
}
"""
s1, t1, _ = jouer(CONTRAT.replace("MODE", "moyenne(4, 6, 0)"))
verifier("exige rompu : la machine s'arrête et dit lequel", s1 == [5, (1 << 64) - 7, 2]
         and t1 == "contrat rompu : moyenne exige n != 0 (ligne 3)\n", f"{s1} {t1!r}")
s2, t2, _ = jouer(CONTRAT.replace("MODE", "tordue(1)"))
verifier("garantit rompu : idem, après la réaction", s2 == [5, (1 << 64) - 7, 2] and "tordue garantit y < 50 (ligne 10)" in t2, f"{s2} {t2!r}")
s3, t3, _ = jouer(CONTRAT.replace("MODE", "1"))
verifier("une branche qui n'a pas réagi ne promet rien ; tenus, les contrats ne changent rien", s3 == [5, (1 << 64) - 7, 2, 1, 99] and t3 == "",
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

lugus = os.path.join(racine, "vtx-rs", "target", "release", "lugus" + (".exe" if os.name == "nt" else ""))
if shutil.which("rustc") and os.path.exists(lugus):
    tmp = tempfile.mkdtemp(prefix="reactions-")
    bons = True
    for src in [CONTRAT.replace("MODE", m) for m in ("moyenne(4, 6, 0)", "tordue(1)", "1")] + [UNITES, CHUTE]:
        prog = os.path.join(tmp, "c.vtx")
        open(prog, "w", encoding="utf-8").write(src)
        mots = os.path.join(tmp, "c.mots")
        open(mots, "w").write(",".join(map(str, vtx128.assembler(vtx128.compiler(src)))) + ";\n")
        emule = subprocess.run([lugus, "lancer", mots], capture_output=True, text=True).stdout
        exe = os.path.join(tmp, "c" + (".exe" if os.name == "nt" else ""))
        subprocess.run([sys.executable, os.path.join(racine, "forge", "forge128.py"), prog, "-o", exe], capture_output=True, text=True)
        forge = subprocess.run([exe], capture_output=True, text=True).stdout
        bons = bons and emule == forge and emule != ""
    verifier("contrats et unités : Lugus (Rust) et la forge disent la même chose", bons)
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

# 10. la forge de Lugus : mêmes sorties
if shutil.which("rustc"):
    tmp = tempfile.mkdtemp(prefix="reactions-")
    exe = os.path.join(tmp, "panel" + (".exe" if os.name == "nt" else ""))
    r = subprocess.run([sys.executable, os.path.join(racine, "forge", "forge128.py"),
                        os.path.join(racine, "exemples128", "panel.vtx"), "-o", exe], capture_output=True, text=True)
    sortie = subprocess.run([exe], capture_output=True, text=True).stdout if r.returncode == 0 else r.stderr
    verifier("forgé pour Lugus : le même 42", sortie.strip() == "42", sortie[-300:])
    shutil.rmtree(tmp, ignore_errors=True)

print("réactions : " + ("tout est conforme" if not echecs else f"{len(echecs)} échec(s)"))
sys.exit(1 if echecs else 0)
