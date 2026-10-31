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
lugus = os.path.join(racine, "vtx-rs", "target", "release", "lugus" + (".exe" if os.name == "nt" else ""))
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
