"""Tableaux dynamiques, dictionnaires, vocabulaire et lire_ligne : vtx.py et vtxc donnent les mêmes mots, et le texte attendu."""
import glob, os, re, shutil, subprocess, sys, tempfile
ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, racine)
import vtx  # noqa: E402

rs = os.path.join(racine, "vtx-rs")
cible = os.environ.get("CARGO_TARGET_DIR") or os.path.join(rs, "target")
subprocess.run([shutil.which("cargo") or "cargo", "build", "--release", "-q"], cwd=rs, check=True)
VTX = os.path.join(cible, "release", "vtx" + (".exe" if os.name == "nt" else ""))
RAPIDE = os.environ.get("VTX_RAPIDE") == "1"


def mots_vtxc(f):
    p = f + ".prog"
    r = subprocess.run([VTX, "compiler", f, p], capture_output=True, text=True)
    if r.returncode:
        return "ERREUR " + (r.stdout + r.stderr)[-300:]
    m = [int(x) for x in open(p).read().split(";")[0].split(",")]
    os.remove(p)
    return m



ATTENDU_TAB = """longueur : 5 somme : 25
1 3 5 7 9 
100 9 4 0
3 9 4
81 10
499500 1000
LE
CUBE
CHROMATIQUE
DE
VERCINTORIX
cube!
un : 3 deux : 2 quatre : 0 1
deux, un, trois
a + b + c espace| ababab
1 1 12 0
deux;un;trois;
"""
ATTENDU_Q = "Ton nom ? Salut Ambiorix, ton nom a 8 lettres\nUn nombre ? 12 au carré : 144\n"

ATTENDU_FL = 'somme 16.25 moyenne 3.25\n-2.0 0.5 5.0 8.0 21.0 \n1.414214 10.5 4 3\n6.0\n5.0 2.0\n1.414214;0.25;2.5;4.0;\n'
ATTENDU_SV = 'ciel vrai affirmé\nmer variable contredit\nlune faux nié\nsoleil variable contredit\nterre inconnu hors de portée\nvrai faux inconnu\n37 vrai 41\n'


def essai(nom, attendu, entree=""):
    src = open(os.path.join(racine, "exemples", "premiers", nom), encoding="utf-8").read()
    f = os.path.join(tmp, nom)
    open(f, "w", encoding="utf-8").write(src)
    py = vtx.assembler(vtx.compiler(src, dossier=tmp))
    vc = mots_vtxc(f)
    r = subprocess.run([VTX, f], capture_output=True, text=True, encoding="utf-8", input=entree)
    ok = py == vc and r.stdout == attendu
    if not ok:
        print(nom, "mêmes mots" if py == vc else "MOTS DIFFÉRENTS", repr(r.stdout[-400:]), r.stderr[-300:])
    return ok


tmp = tempfile.mkdtemp()
try:
    ok1 = essai("tableaux.vtx", ATTENDU_TAB)
    print(f"Tableaux dynamiques ([..], t[i], pour x dans t, ajouter, trier), dico, textes (decouper, remplacer…) : "
          f"{'mêmes mots et texte attendu' if ok1 else 'ÉCART'}")
    ok2 = essai("questions.vtx", ATTENDU_Q, "Ambiorix\n12\n")
    print(f"lire_ligne au clavier : {'mêmes mots et réponses attendues' if ok2 else 'ÉCART'}")
    ok3 = essai("flottants.vtx", ATTENDU_FL)
    print(f"Tableaux de flottants (littéral, flottant[], somme, trier, pour x dans t) : {'mêmes mots et texte attendu' if ok3 else 'ÉCART'}")
    ok4 = essai("savoir.vtx", ATTENDU_SV)
    print(f"Savoir à quatre valeurs (affirmer, nier, savoir, nommer, dico ouvert et fermé) : "
          f"{'mêmes mots et texte attendu' if ok4 else 'ÉCART'}")
    # l'arbre des liaisons (vtx arbre) : le dico ouvert, ses quatre états, et les textes partagés
    r = subprocess.run([VTX, "arbre", os.path.join(racine, "exemples", "premiers", "savoir.vtx")], capture_output=True, text=True,
                       encoding="utf-8")
    ok5 = all(x in r.stdout for x in ['dico de 4 clés (ouvert : absent = inconnu)', '"mer" = 2', '[variable]', '"lune" = 0',
                                      '[faux]', 'texte "soleil"', '[1] texte "nié"'])
    print(f"Arbre des liaisons (vtx arbre) : {'objets, états et textes reconnus' if ok5 else 'ÉCART'}")
    if not ok5:
        print(r.stdout[-1500:])
finally:
    shutil.rmtree(tmp, ignore_errors=True)
sys.exit(0 if ok1 and ok2 and ok3 and ok4 and ok5 else 1)
