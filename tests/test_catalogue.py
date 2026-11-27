#!/usr/bin/env python3
"""Le catalogue des modules et la vibration des molécules (0.62, docs/vtx-reactions.md section 66).

1. lister un dossier (le service 28) : lister_dossier et dossier_present, les mêmes sur Lugus et Dunon, en Rust et en
   Python, par les deux compilateurs de chaque machine (les mêmes mots) ;
2. les morceaux d'un programme et leur vibration : le lecteur en vtx (lugus morceaux) et chimie/adn.py, ligne pour ligne ;
3. le cube du catalogue (0.62c) : lugus cataloguer (écrit en vtx) et python3 chimie/adn.py cataloguer, le cube, son
   anti-cube, son ombre et sa lecture hex, octet pour octet ; le service 29 (choisir un cube par son chemin) sur les
   quatre machines ;
4. « importer empreinte "…"; » : le compilateur choisit le cube, puis lit le module à l'adresse de son empreinte (le
   dossier, bibliotheque/), les mêmes mots
   que par son chemin ; introuvable, ou deux modules : refusé par les quatre compilateurs ; retouché : refusé ;
5. la carte dit d'où vient chaque molécule, et voit une molécule retouchée depuis le catalogue.

    python3 tests/test_catalogue.py"""
import os
import shutil
import subprocess
import sys
import tempfile

# Windows : les Python lancés par ce test écrivent en UTF-8 (sinon en cp1252 : les accents se perdent, et la comparaison
# avec la sortie de Lugus, en UTF-8, échoue), et celui-ci aussi
os.environ["PYTHONUTF8"] = "1"
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
for p in (racine, os.path.join(racine, "chimie"), os.path.join(racine, "spu64"), os.path.join(racine, "spu128")):
    sys.path.insert(0, p)
import adn  # noqa: E402
import vtx64  # noqa: E402

X = ".exe" if os.name == "nt" else ""
BIN = os.path.join(racine, "vtx-rs", "target", "release")
LUGUS, DUNON = os.path.join(BIN, "lugus" + X), os.path.join(BIN, "vtx64" + X)
echecs = 0


def verifier(nom, ok, detail=""):
    global echecs
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok else f" : {detail}"), flush=True)
    echecs += 0 if ok else 1


def lancer(cmd, dossier=None):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=dossier)
    return r.returncode, r.stdout + r.stderr


def ecrire(chemin, texte):
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, "w", encoding="utf-8", newline="\n") as f:
        f.write(texte)
    return chemin


def mots_ou_refus(machine, chemin):
    """(les mots de la référence ou « refus », ceux de vtxc ou « refus »)"""
    src = open(chemin, encoding="utf-8").read()
    d = os.path.dirname(chemin)
    m = None   # 0.851 : sur Lugus, un seul compilateur (vtxc128, lugus) : il répond pour les deux
    try:
        if machine != "lugus":
            m = vtx64.assembler(vtx64.compiler(src, dossier=d))
    except vtx64.VtxError as e:
        m = "refus : " + str(e)
    sortie = os.path.join(tempfile.gettempdir(), f"catalogue-{os.getpid()}.mots")
    code, texte = lancer([LUGUS if machine == "lugus" else DUNON, "compiler", chemin, sortie])
    if code == 0:
        ml = [int(x) for x in open(sortie).read().split(";")[0].split(",") if x.strip()]
    else:
        ml = "refus : " + texte.strip()
    return (ml if m is None else m), ml


# 0.851 : la machine Python (le témoin) ne joue qu'à la main (VTX_TEMOIN=1, ou verifier.py --temoin)
TEMOIN = os.environ.get("VTX_TEMOIN") == "1"
d = tempfile.mkdtemp(prefix="vtx-catalogue-")

# --------------------------------------------------------------------------------------------- 1. lister un dossier
liste = os.path.join(d, "liste")
for n in ("b.txt", "a.vtx", "été.txt"):
    ecrire(os.path.join(liste, n), "x\n")
os.makedirs(os.path.join(liste, "sous"))
PROG_LISTE = """fonction dire(l: logique) {
    selon l { vrai { afficher("vrai"); } faux { afficher("faux"); } inconnu { afficher("inconnu"); } variable { afficher("variable"); } }
}
fonction principal() {
    pour n dans lister_dossier("") {
        afficher(n);
    }
    afficher(longueur(lister_dossier("rien")));
    dire(dossier_present("sous"));
    dire(dossier_present("b.txt"));
    dire(dossier_present("rien"));
}
"""
f_liste = ecrire(os.path.join(liste, "liste.vtx"), PROG_LISTE)
attendu = "a.vtx\nb.txt\nliste.vtx\nsous/\nété.txt\n0\nvrai\nfaux\ninconnu\n"
for nom, cmd in (("Lugus", [LUGUS, "liste.vtx"]), ("Dunon", [DUNON, "liste.vtx"])) + (
        (("vtx128.py", [sys.executable, os.path.join(racine, "vtx128.py"), "run", "liste.vtx"]),
         ("vtx64.py", [sys.executable, os.path.join(racine, "vtx64.py"), "run", "liste.vtx"])) if TEMOIN else ()):
    code, texte = lancer(cmd, liste)
    lu = "".join(l + "\n" for l in texte.split("\n") if l and "instructions exécutées" not in l)
    verifier(f"lister un dossier, {nom} : les noms triés, un sous-dossier finit par « / » ; vrai, faux, inconnu",
             lu == attendu, repr(lu))
for machine in ("lugus", "dunon"):
    m, ml = mots_ou_refus(machine, f_liste)
    verifier(f"lister un dossier : les deux compilateurs de {machine.capitalize()} donnent les mêmes mots", m == ml,
             f"{str(m)[:80]} / {str(ml)[:80]}")

# --------------------------------------------------------------------------------------------- 2. les morceaux
for f in ("exemples128/bonjour128.vtx", "exemples128/panel.vtx", "exemples128/codon.vtx", "chimie/adn.vtx"):
    chemin = os.path.join(racine, f)
    code, texte = lancer([LUGUS, "morceaux", chemin])
    mots, _, _, _ = adn.molecules_isotopes_noms(open(chemin, encoding="utf-8").read(), os.path.dirname(chemin))
    ref = "".join(f"{p} {q} {n} {masse} {v:016x}\n" for p, q, n, masse, v in adn.morceaux(mots))
    verifier(f"les morceaux de {f} et leur vibration : le lecteur en vtx et chimie/adn.py ({ref.count(chr(10))})",
             code == 0 and texte == ref, texte[:200])

# --------------------------------------------------------------------------------------------- 3. le catalogue
monde = os.path.join(d, "monde")
bib = os.path.join(monde, "bibliotheque")
shutil.copytree(os.path.join(racine, "tests", "modules"), bib)
shutil.copy(os.path.join(racine, "bibliotheque", "codon.vtx"), bib)
ecrire(os.path.join(bib, "programme.vtx"), "fonction principal() { afficher(1); }\n")   # un programme : pas un module
CUBES = ("cube128-1-392.cub", "anticube128-1-392.cub", "ombre128-1-392.cub")


def fichiers_du_cube(dossier):
    return [open(os.path.join(dossier, f), "rb").read() if os.path.exists(os.path.join(dossier, f)) else b""
            for f in CUBES]


code, texte = lancer([LUGUS, "cataloguer", bib])
vtx_cat = open(os.path.join(bib, "catalogue.vtxcat"), encoding="utf-8").read() if code == 0 else ""
vtx_cubes = fichiers_du_cube(bib)
ref_cat = adn.cataloguer(bib)
ref_cubes = fichiers_du_cube(bib)
verifier("le cube du catalogue : lugus cataloguer (en vtx) et chimie/adn.py, le cube, son anti-cube et son ombre, "
         "octet pour octet", code == 0 and all(vtx_cubes) and vtx_cubes == ref_cubes, texte[:200])
verifier("le cube du catalogue : sa lecture hex (catalogue.vtxcat), la même par les deux", vtx_cat == ref_cat and code == 0,
         texte[:200])
verifier("le catalogue : trois modules (le programme écarté), leurs empreintes, leurs molécules, leurs places",
         vtx_cat.count("\nmodule|") == 3 and "module|outil.vtx|f62defeb8b893235|2|#" in vtx_cat
         and "programme.vtx" not in vtx_cat and "molecule|double|" in vtx_cat, vtx_cat[:300])
vibs = [l.split("|")[4] for l in vtx_cat.split("\n") if l.startswith("molecule|")]
# le service 29 : choisir le cube par son chemin, puis lire sa queue à son adresse (Dunon : en deux moitiés)
cube = os.path.join(bib, "cube128-1-392.cub").replace("\\", "/")
P29 = {"lugus": f'''fonction principal() {{
    soit g = __service(29, "{cube}");
    soit w: entier_128 = @[cube_adresse(1, g, 16777215)];
    afficher(g, haut(w), bas(w) >> 32, __service(29, "{cube}"), __service(29, "rien.cub"));
}}
''', "dunon": f'''fonction principal() {{
    soit g = __service(29, "{cube}");
    afficher(g, @[cube_adresse(1, g + 1, 16777215)], @[cube_adresse(1, g, 16777215)] >> 32, __service(29, "{cube}"), __service(29, "rien.cub"));
}}
'''}
for machine, b, py in (("lugus", LUGUS, "vtx128.py"), ("dunon", DUNON, "vtx64.py")):
    f29 = ecrire(os.path.join(d, "s29", machine + ".vtx"), P29[machine])
    _, t1 = lancer([b, f29])
    t2 = t1
    if TEMOIN:
        # 0.851 : le témoin (la machine Python), à la main seulement
        _, t2 = lancer([sys.executable, os.path.join(racine, py), "run", f29])
        t2 = "".join(l + "\n" for l in t2.split("\n") if l and "instructions exécutées" not in l)
    suivante = "393" if machine == "lugus" else "394"
    verifier(f"le service 29 sur {machine.capitalize()} : le cube choisi à sa fréquence, sa queue lue "
             f"à son adresse, le second à la suivante ; pas un cube : faux" + (" (et le témoin Python)" if TEMOIN else ""),
             t1 == t2 and t1.startswith(f"392 {adn.QUEUE_CATALOGUE} 3 {suivante} -2"), f"{t1!r} / {t2!r}")
verifier(f"le catalogue : {len(vibs)} molécules, autant de vibrations différentes", len(set(vibs)) == len(vibs))
h_outil = next(l.split("|")[2] for l in vtx_cat.split("\n") if l.startswith("module|outil.vtx|"))

# --------------------------------------------------------------------------------------------- 4. importer empreinte
prog = os.path.join(monde, "p")
f_emp = ecrire(os.path.join(prog, "emp.vtx"),
               f'importer empreinte "{h_outil}";\nfonction principal() {{\n    afficher(double(21));\n    afficher(salut());\n}}\n')
f_chem = ecrire(os.path.join(prog, "chemin.vtx"),
                '// le même, par son chemin\nimporter "../bibliotheque/outil.vtx";\n'
                'fonction principal() {\n    afficher(double(21));\n    afficher(salut());\n}\n')
for machine, b in (("lugus", LUGUS), ("dunon", DUNON)):
    m, ml = mots_ou_refus(machine, f_emp)
    m2, _ = mots_ou_refus(machine, f_chem)
    verifier(f"importer empreinte, {machine.capitalize()} : trouvé dans ../bibliotheque/, les mêmes mots par les deux "
             "compilateurs (Lugus : vtxc128 seul), et que par son chemin", m == ml == m2 and isinstance(m, list), f"{str(m)[:80]} / {str(ml)[:80]}")
    code, texte = lancer([b, f_emp])
    verifier(f"importer empreinte, {machine.capitalize()} : le programme tourne", "42" in texte and "Salut" in texte, texte)
f_rien = ecrire(os.path.join(prog, "rien.vtx"), 'importer empreinte "0123456789abcdef";\nfonction principal() { afficher(1); }\n')
for machine in ("lugus", "dunon"):
    m, ml = mots_ou_refus(machine, f_rien)
    verifier(f"importer empreinte inconnue, {machine.capitalize()} : refusé par les deux compilateurs, et dit",
             str(m).startswith("refus") and str(ml).startswith("refus") and "aucun cube de catalogue" in str(m) + str(ml),
             f"{m} / {ml}")
# deux modules de même empreinte (une copie dans le dossier du programme, cataloguée aussi)
shutil.copy(os.path.join(bib, "outil.vtx"), prog)
lancer([LUGUS, "cataloguer", prog])
for machine in ("lugus", "dunon"):
    m, ml = mots_ou_refus(machine, f_emp)
    verifier(f"importer empreinte de deux modules, {machine.capitalize()} : refusé par les deux compilateurs, et dit",
             "deux modules" in str(m) and "deux modules" in str(ml), f"{m} / {ml}")
for f in CUBES + ("catalogue.vtxcat", "outil.vtx"):
    os.remove(os.path.join(prog, f))
# le module retouché après son catalogue : sa promesse ne tient plus
brut = open(os.path.join(bib, "outil.vtx"), encoding="utf-8").read()
ecrire(os.path.join(bib, "outil.vtx"), brut.replace("2 * x", "3 * x"))
for machine in ("lugus", "dunon"):
    m, ml = mots_ou_refus(machine, f_emp)
    verifier(f"importer empreinte d'un module retouché, {machine.capitalize()} : refusé (l'empreinte trouvée dite)",
             "n'est plus celui promis" in str(m) and "n'est plus celui promis" in str(ml), f"{m} / {ml}")
ecrire(os.path.join(bib, "outil.vtx"), brut)

# --------------------------------------------------------------------------------------------- 5. la carte
f_carte = os.path.join(prog, "carte.vtx")
shutil.copy(os.path.join(racine, "exemples128", "codon.vtx"), f_carte)     # il importe ../bibliotheque/codon.vtx
code, texte = lancer([LUGUS, "carte", f_carte])
verifier("la carte : les molécules du module catalogué disent d'où elles viennent",
         code == 0 and "elle vient du module codon.vtx (empreinte " in texte and "d'un module catalogué" in texte, texte[:400])
brut = open(os.path.join(bib, "codon.vtx"), encoding="utf-8").read()
ecrire(os.path.join(bib, "codon.vtx"), brut.replace("fonction penche(d): logique {",
                                                     "fonction penche(d): logique {\n    soit z = d + 1;"))
code, texte = lancer([LUGUS, "carte", f_carte])
verifier("la carte : une molécule retouchée depuis le catalogue se voit (sa vibration a changé)",
         code == 0 and "retouchée, ou compilée autrement" in texte, texte[:400])
ecrire(os.path.join(bib, "codon.vtx"), brut)

# --------------------------------------------------------------------------------------------- 6. sortie(f)
# vtxc128 ne finissait pas de compiler « sortie(f) » d'une fonction écrite seule (est_sig prenait « son propre type »
# pour un type de fonction) : corrigé en 0.62
f_sortie = ecrire(os.path.join(d, "sortie", "sortie_f.vtx"),
                  "fonction f(x) { retour 2 * x; }\nfonction principal() {\n    sortie(f);\n}\n")
m, ml = mots_ou_refus("lugus", f_sortie)
verifier("sortie(f) d'une fonction écrite seule : vtxc128 le compile",
         isinstance(m, list) and m == ml, f"{str(m)[:80]} / {str(ml)[:80]}")

# --------------------------------------------------------------------------------------------- 7. le cube abîmé
# un octet changé dans le cube du catalogue : l'anti-cube et l'ombre le réparent quand il est choisi (le compilateur, la
# carte), et la carte le dit
c = os.path.join(bib, "cube128-1-392.cub")
b = bytearray(open(c, "rb").read())
b[8 + 4 + 16 * 0x0400 + 9] ^= 0x5A
open(c, "wb").write(bytes(b))
code, texte = lancer([LUGUS, "carte", f_carte])
verifier("le cube abîmé : la carte le dit réparé par son anti-cube et son ombre, et lit encore d'où viennent les molécules",
         "réparé par son anti-cube et son ombre" in texte and "elle vient du module codon.vtx" in texte, texte[:300])
m, ml = mots_ou_refus("lugus", f_emp)
verifier("le cube abîmé : importer empreinte le lit encore (réparé), les mêmes mots", isinstance(m, list) and m == ml,
         f"{str(m)[:80]} / {str(ml)[:80]}")

shutil.rmtree(d, ignore_errors=True)
print("le catalogue et la vibration : " + ("tout est conforme" if echecs == 0 else f"{echecs} écart(s)"))
sys.exit(1 if echecs else 0)
