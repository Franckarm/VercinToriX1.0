#!/usr/bin/env python3
"""Les fonctions passées en valeur sur Dunon (0.65, docs/vtx-reactions.md section 70), comme sur Lugus (0.6w, 0.6x).

Vérifié : les exemples des valeurs et des types de fonction (exemples128/valeurs.vtx, exemples128/types_fonction.vtx),
un mélange, les mêmes mots par vtx64.py et vtxc64, la sortie attendue ; les refus, le même message des deux côtés ; une
fonction passée sans appel par valeur (sa molécule à elle) ; face et centre d'une fonction passée (inconnu sur Dunon).

    python3 tests/test_valeurs64.py"""
import os
import subprocess
import sys
import tempfile

os.environ["PYTHONUTF8"] = "1"
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, racine)
import vtx64  # noqa: E402

X = ".exe" if os.name == "nt" else ""
DUNON = os.path.join(racine, "vtx-rs", "target", "release", "vtx64" + X)
d = tempfile.mkdtemp(prefix="vtx-valeurs64-")
echecs = 0


def verifier(nom, ok, detail=""):
    global echecs
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok else f" : {detail}"), flush=True)
    echecs += 0 if ok else 1


def dunon(*args):
    env = dict(os.environ, VTX_SANS_CLAVIER="1")
    return subprocess.run([DUNON, *args], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=d,
                          timeout=600, env=env)


def memes_mots(chemin):
    texte = open(chemin, encoding="utf-8").read()
    try:
        m = vtx64.assembler(vtx64.compiler(texte, dossier=os.path.dirname(chemin)))
    except vtx64.VtxError as e:
        return False, str(e)
    r = dunon("compiler", chemin, os.path.join(d, "x.mots"))
    if r.returncode != 0:
        return False, r.stdout + r.stderr
    ml = [int(x) for x in open(os.path.join(d, "x.mots")).read().split(";")[0].split(",") if x]
    return m == ml, f"{len(m)} contre {len(ml)}"


def ecrire(nom, texte):
    chemin = os.path.join(d, nom)
    open(chemin, "w", encoding="utf-8").write(texte)
    return chemin


VAL = os.path.join(racine, "exemples128", "valeurs.vtx")
ok, det = memes_mots(VAL)
verifier("valeurs.vtx sur Dunon : vtxc64 et vtx64.py donnent les mêmes mots", ok, det)
r = dunon(VAL)
verifier("pour_chacun, plier, une fonction qui choisit une fonction, une structure qui porte une fonction",
         r.stdout.split("\n")[:6] == ["1 4 9 16 25 ", "2 4 6 8 10 ", "somme : 15 ; produit : 120", "le choix pour -3 : 20",
                                      "carré de 7 : 49", "double de 7 : 14"], r.stdout + r.stderr)

TF = os.path.join(racine, "exemples128", "types_fonction.vtx")
ok, det = memes_mots(TF)
verifier("types_fonction.vtx sur Dunon : les mêmes mots", ok, det)
r = dunon(TF)
verifier("appliquer, plier, un flottant, une fonction rendue, un texte, une structure",
         r.stdout.split("\n")[:5] == ["49 16", "1.5", "25", "Par Toutatis !", "4"], r.stdout + r.stderr)

MELE = ecrire("mele.vtx", """fonction carre(x) { retour x * x; }
fonction plus(a, b) { retour a + b; }
fonction fact(f, n) {
    si n <= 1 { retour 1; }
    retour n * f(f, n - 1);
}
fonction composer(f: fonction(entier): entier, g: fonction(entier): entier, x) { retour f(g(x)); }
fonction principal() {
    soit outils = [carre, carre];
    soit o = outils[1];
    afficher(o(6), fact(fact, 5), composer(carre, carre, 3));
    soit t = [3, 1, 2];
    soit s = 0;
    pour v dans t { s = plus(s, v); }
    afficher(s);
}
""")
ok, det = memes_mots(MELE)
r = dunon(MELE)
verifier("un tableau de fonctions, la récursion par valeur, une composition : les mêmes mots, la sortie",
         ok and r.stdout.split("\n")[:2] == ["36 120 81", "6"], det + " " + r.stdout + r.stderr)

SANS = ecrire("sans.vtx", """fonction carre(x) { retour x * x; }
fonction double(x) { retour x + x; }
fonction montrer(f) { afficher(f > 0); }
fonction principal() {
    montrer(carre);
    montrer(double);
}
""")
ok, det = memes_mots(SANS)
verifier("deux fonctions passées sans appel par valeur (un accord) : les mêmes mots (la table leur donne leur molécule)",
         ok, det)

FC = ecrire("faces.vtx", """fonction carre(x) { retour x * x; }
fonction principal() {
    afficher(face(carre, 0));
    selon centre(carre) { inconnu { afficher("inconnu"); } vrai { afficher("vrai"); } faux { afficher("faux"); }
                          variable { afficher("variable"); } }
}
""")
ok, det = memes_mots(FC)
r = dunon(FC)
verifier("face et centre d'une fonction passée sur Dunon : les mêmes mots ; 0 et inconnu (pas de cube de programme)",
         ok and r.stdout.split("\n")[:2] == ["0", "inconnu"], det + " " + r.stdout + r.stderr)

VOC = ecrire("vocabulaire.vtx", """fonction carre(x) { retour x * x; }
fonction pair(x) { retour x % 2 == 0; }
fonction plus(a, b) { retour a + b; }
fonction principal() {
    soit t = [1, 2, 3, 4, 5];
    soit c = transformer(t, carre);
    afficher(c[0], c[4], longueur(filtrer(t, pair)), plier(t, plus, 0), compter_si(t, pair), rang_si(t, pair));
    trier_par(t, carre);
    afficher(tous(t, pair), au_moins_un(t, pair));
}
""")
ok, det = memes_mots(VOC)
r = dunon(VOC)
verifier("les mots du vocabulaire qui prennent une fonction (transformer, filtrer, plier, compter_si…) sur Dunon",
         ok and r.stdout.split("\n")[:2] == ["1 25 2 15 2 1", "0 1"], det + " " + r.stdout + r.stderr)

TETE = """fonction carre(x) { retour x * x; }
fonction plus(a, b) { retour a + b; }
fonction moitie(x: flottant): flottant { retour x / 2.0; }
fonction appliquer(f: fonction(entier): entier, x) { retour f(x); }
fonction principal() {
"""
REFUS = [
    ("une fonction à deux paramètres là où l'on en attend un", "afficher(appliquer(plus, 7));",
     "ligne 6 : « plus » ne convient pas à fonction(entier): entier : elle est fonction(entier, entier): entier"),
    ("une fonction de flottants là où l'on attend des entiers", "soit g: fonction(entier): entier = moitie;",
     "ligne 6 : « moitie » ne convient pas à fonction(entier): entier : elle est fonction(flottant): flottant"),
    ("trop d'arguments à un appel par valeur", "soit g: fonction(entier): entier = carre; afficher(g(1, 2));",
     "ligne 6 : « g » (fonction(entier): entier) attend 1 argument(s), pas 2"),
    ("un type de fonction dans un type de fonction", "soit g: fonction(entier): fonction(entier) = carre;",
     "ligne 6 : un type de fonction dans un type de fonction : pas encore"),
    ("deux types de fonction différents", "soit g: fonction(entier): entier = carre; soit h: fonction(entier, entier): "
     "entier = g;", "ligne 6 : une valeur de fonction ne va pas là où l'on attend un autre type"),
    ("une valeur de 128 bits passée par valeur", "soit g: fonction(flottant_petuar): entier = carre;",
     "ligne 6 : « carre » ne convient pas à fonction(flottant_petuar): entier : elle est fonction(entier): entier"),
]
for nom, ligne, attendu in REFUS:
    chemin = ecrire("refus.vtx", TETE + " " + ligne + "\n}\n")
    try:
        vtx64.compiler(open(chemin, encoding="utf-8").read(), dossier=d)
        mp = "(accepté)"
    except vtx64.VtxError as e:
        mp = str(e)
    rl = dunon("compiler", chemin, os.path.join(d, "x.mots"))
    verifier(f"refus : {nom} (les deux compilateurs, le même message)",
             attendu in mp and attendu in rl.stdout + rl.stderr and rl.returncode != 0, mp + " / " + rl.stdout + rl.stderr)

print("les fonctions en valeur sur Dunon : " + ("tout est conforme" if echecs == 0 else f"{echecs} écart(s)"))
sys.exit(1 if echecs else 0)
