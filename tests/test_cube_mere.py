#!/usr/bin/env python3
"""Les cubes mères (0.63, docs/vtx-reactions.md section 68).

Un cube mère est nommé comme un fichier (cube128-NOM.cub) et n'occupe aucune fréquence ; ses sous-cubes portent son nom
comme indicatif (cube128-NOM-ÉTAGE-FRÉQUENCE.cub) : chaque programme a toutes les fréquences à lui. Vérifié :

1. cube_mere(nom) (le service 30), ranger_cube, la relecture : les mêmes fichiers (sous-cubes, cube mère, anti-cubes,
   ombres) sur Lugus et Dunon, en Rust et en Python, octet pour octet ; les mêmes mots par les deux compilateurs ;
2. le cube mère, le squelette : à l'adresse de chaque fréquence, le sous-cube qu'elle porte ; lu par le service 29 ;
3. les noms refusés (ambigus, ou des caractères interdits) ;
4. deux programmes du même dossier, chacun à sa fréquence 440 : aucun ne gêne l'autre ;
5. le chemin : lugus cube PROG.adn range sous le cube mère du programme ; relancé par son sous-cube ou son cube mère.

    python3 tests/test_cube_mere.py"""
import hashlib
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
sys.path.insert(0, racine)
import vtx128  # noqa: E402
import vtx64  # noqa: E402

vtx128.COMPAT_64 = False
X = ".exe" if os.name == "nt" else ""
BIN = os.path.join(racine, "vtx-rs", "target", "release")
LUGUS, DUNON = os.path.join(BIN, "lugus" + X), os.path.join(BIN, "vtx64" + X)
echecs = 0


def verifier(nom, ok, detail=""):
    global echecs
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok else f" : {detail}"), flush=True)
    echecs += 0 if ok else 1


def lancer(cmd, dossier):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=dossier)
    return r.returncode, r.stdout + r.stderr


def sortie_py(texte):
    return "".join(l + "\n" for l in texte.split("\n") if l and "instructions exécutées" not in l)


def empreintes(dossier):
    return {f: hashlib.sha256(open(os.path.join(dossier, f), "rb").read()).hexdigest()
            for f in sorted(os.listdir(dossier)) if f.endswith(".cub")}


ECRIT = """fonction principal() {
    afficher(cube_mere("labyrinthe"));
    @[cube_adresse(1, 440, 5)] = 1234;
    @[cube_adresse(1, 440, 70000)] = 99;
    @[cube_adresse(1, 7, 1)] = 42;
    afficher(ranger_cube(1, 440), ranger_cube(1, 7));
    afficher(cube_mere("1-440"), cube_mere("a b"), cube_mere("jeu-2"), cube_mere("salle_été"));
}
"""
RELIT = {"lugus": """fonction principal() {
    cube_mere("labyrinthe");
    afficher(@[cube_adresse(1, 440, 5)], @[cube_adresse(1, 440, 70000)], @[cube_adresse(1, 7, 1)]);
    soit g = __service(29, "cube128-labyrinthe.cub");
    soit q: entier_128 = @[cube_adresse(1, g, 16777215)];
    soit d: entier_128 = @[cube_adresse(1, g, 440)];
    afficher(g, bas(q), bas(d) & 1023, haut(d) == haut(q));
}
""", "dunon": """fonction principal() {
    cube_mere("labyrinthe");
    afficher(@[cube_adresse(1, 440, 5)], @[cube_adresse(1, 440, 70000)], @[cube_adresse(1, 7, 1)]);
    soit g = __service(29, "cube64-labyrinthe.cub");
    afficher(g, @[cube_adresse(1, g, 16777215)], @[cube_adresse(1, g, 440)] & 1023);
}
"""}

d = tempfile.mkdtemp(prefix="vtx-cube-mere-")
for machine, b, py in (("lugus", LUGUS, "vtx128.py"), ("dunon", DUNON, "vtx64.py")):
    t = "128" if machine == "lugus" else "64"
    rs, ref = os.path.join(d, machine + "-rs"), os.path.join(d, machine + "-py")
    for x in (rs, ref):
        os.makedirs(x)
        open(os.path.join(x, "ecrit.vtx"), "w", encoding="utf-8").write(ECRIT)
        open(os.path.join(x, "relit.vtx"), "w", encoding="utf-8").write(RELIT[machine])
    _, e1 = lancer([b, "ecrit.vtx"], rs)
    _, r1 = lancer([b, "relit.vtx"], rs)
    _, e2 = lancer([sys.executable, os.path.join(racine, py), "run", "ecrit.vtx"], ref)
    _, r2 = lancer([sys.executable, os.path.join(racine, py), "run", "relit.vtx"], ref)
    attendus = [f"cube{t}-labyrinthe.cub", f"cube{t}-labyrinthe-1-440.cub", f"cube{t}-labyrinthe-1-7.cub"]
    f1, f2 = empreintes(rs), empreintes(ref)
    verifier(f"{machine.capitalize()} : cube_mere puis ranger_cube : le cube mère et ses deux sous-cubes, chacun avec son "
             "anti-cube et son ombre", all(a in f1 for a in attendus) and len(f1) == 9, sorted(f1))
    verifier(f"{machine.capitalize()} : les mêmes fichiers en Rust et en Python, octet pour octet", f1 == f2 and f1 != {},
             f"{sorted(f1)} / {sorted(f2)}")
    verifier(f"{machine.capitalize()} : la même sortie en Rust et en Python ; les noms ambigus ou interdits refusés",
             e1 == sortie_py(e2) and r1 == sortie_py(r2) and "\n2 1\n-2 -2 -2 " in e1 and not e1.rstrip().endswith("-2"),
             f"{e1!r} / {e2!r}")
    verifier(f"{machine.capitalize()} : relus sous le cube mère, les points reviennent ; le cube mère (service 29) dit "
             "deux sous-cubes, et à l'adresse 440 le sous-cube de l'étage 1, deux pages (5 et 70 000)",
             r1.startswith("1234 99 42\n16777215 2 514") and r1 == sortie_py(r2), f"{r1!r} / {r2!r}")
    for f in ("ecrit.vtx", "relit.vtx"):
        src = open(os.path.join(rs, f), encoding="utf-8").read()
        if machine == "lugus":
            m = vtx128.assembler(vtx128.compiler(src, dossier=rs), True)[0]
        else:
            m = vtx64.assembler(vtx64.compiler(src, dossier=rs))
        sortie = os.path.join(d, "m.mots")
        lancer([b, "compiler", f, sortie], rs)
        ml = [int(x) for x in open(sortie).read().split(";")[0].split(",") if x.strip()]
        verifier(f"{machine.capitalize()} : {f}, les mêmes mots par les deux compilateurs", m == ml)

# deux programmes du même dossier, chacun à sa fréquence 440
deux = os.path.join(d, "deux")
os.makedirs(deux)
for nom, v in (("alpha", 111), ("beta", 222)):
    open(os.path.join(deux, nom + ".vtx"), "w", encoding="utf-8").write(f"""fonction principal() {{
    cube_mere("{nom}");
    si @[cube_adresse(1, 440, 3)] == 0 {{
        @[cube_adresse(1, 440, 3)] = {v};
        ranger_cube(1, 440);
    }}
    afficher(@[cube_adresse(1, 440, 3)]);
}}
""")
_, a1 = lancer([LUGUS, "alpha.vtx"], deux)
_, b1 = lancer([LUGUS, "beta.vtx"], deux)
_, a2 = lancer([LUGUS, "alpha.vtx"], deux)
verifier("deux programmes du même dossier, chacun sa fréquence 440 : chacun relit la sienne",
         a1 == a2 == "111\n" and b1 == "222\n" and os.path.exists(os.path.join(deux, "cube128-alpha-1-440.cub"))
         and os.path.exists(os.path.join(deux, "cube128-beta-1-440.cub")), f"{a1!r} {b1!r} {a2!r}")

# le chemin : lugus cube PROG.adn, sous le cube mère du programme
ch = os.path.join(d, "chemin")
os.makedirs(ch)
shutil.copy(os.path.join(racine, "exemples128", "bonjour128.vtx"), ch)
_, attendu = lancer([LUGUS, "bonjour128.vtx"], ch)
lancer([LUGUS, "ranger", "bonjour128.vtx"], ch)
code, texte = lancer([LUGUS, "cube", "bonjour128.adn"], ch)
verifier("le chemin : lugus cube PROG.adn range le programme dans cube128-PROG-1-440.cub, sous le cube mère cube128-PROG.cub",
         code == 0 and os.path.exists(os.path.join(ch, "cube128-bonjour128-1-440.cub"))
         and os.path.exists(os.path.join(ch, "cube128-bonjour128.cub")) and "sous le cube mère" in texte, texte[-300:])
_, s1 = lancer([LUGUS, "cube128-bonjour128-1-440.cub"], ch)
_, s2 = lancer([LUGUS, "cube128-bonjour128.cub"], ch)
fin = attendu.strip().split("\n")[-1]
verifier("le chemin : relancé par son sous-cube et par son cube mère, la sortie du programme",
         fin in s1 and fin in s2 and "le cube : vrai" in s1 and "le cube : vrai" in s2, f"{s1[-200:]!r} / {s2[-200:]!r}")

shutil.rmtree(d, ignore_errors=True)
print("les cubes mères : " + ("tout est conforme" if echecs == 0 else f"{echecs} écart(s)"))
sys.exit(1 if echecs else 0)
