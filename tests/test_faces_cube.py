#!/usr/bin/env python3
"""Les faces dans le cube (0.64, docs/vtx-reactions.md section 69).

Le programme rangé dans son cube : son code à l'étage Đ (le tau gallicum, l'étage 0), ses faces aux étages 1, 2, 3 de la
même fréquence, chaque molécule à la place de son début, un axe par étage (la face d'un côté dans la moitié basse du
point, la face opposée dans la haute). Lancé depuis son cube, le programme lit face(f, k) et centre(f). Vérifié :

1. les faces lues pendant qu'il tourne : celles de la carte rangée dans l'ADN, champ pour champ ;
2. le centre : vrai (son code est celui du cube), variable (une avarie pendant qu'il tourne), faux (le cube des faces
   réparé en le lisant), inconnu (lancé depuis son texte, sans cube) ;
3. les mêmes mots par les deux compilateurs de Lugus, et de Dunon ;
4. le cube mère : à l'adresse de la fréquence, le descripteur des quatre étages (Đ, 1, 2, 3) ;
5. un cube de la 0.63 (le programme à l'étage 1) se lance encore ; un cube des faces seul n'est pas un programme.

    python3 tests/test_faces_cube.py"""
import os
import shutil
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


def lancer(cmd, dossier, env=None):
    e = dict(os.environ, **(env or {}))
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=dossier, env=e)
    return r.returncode, r.stdout + r.stderr


PROG = """fonction carre(x) { retour x * x; }
reaction somme(a, b) -> s {
    exige a < 1000
    = a + b          -> s
    garantit s >= a
}
fonction principal() {
    soit g = carre;
    soit h = somme;
    pour k dans 0..6 {
        afficher(face(g, k));
    }
    pour k2 dans 0..6 {
        afficher(face(h, k2));
    }
    selon centre(g) {
        vrai { afficher("vrai"); }
        faux { afficher("faux"); }
        inconnu { afficher("inconnu"); }
        variable { afficher("variable"); }
    }
    afficher(g(7), h(2, 3));
}
"""


def faces_attendues(adn, nom):
    """les six faces de la molécule NOM, tirées de la carte rangée dans l'ADN (la section « faces »)"""
    lignes = open(adn, encoding="utf-8").read().split("\n")
    i = next(k for k, l in enumerate(lignes) if l.startswith("GU faces "))
    for l in lignes[i + 1:i + 1 + int(lignes[i].split()[2])]:
        c = l.split("|")
        if c[1] != nom:
            continue
        genre = {"tete": 1, "fonction": 2, "reaction": 3, "empruntee": 4}.get(c[2], 0)
        ld, le = (int(x) for x in c[3].split("-"))
        n = lambda x: int(x)
        est = genre | (min(n(c[4]), 16777215) << 4) | (min(ld, 262143) << 28) | (min(le, 262143) << 46)
        touche = (n(c[5]) & 3) | ((n(c[6]) & 3) << 2)
        prof = 65535 if c[7] == "-" else min(n(c[7]), 65535)
        ap = [int(x) for x in c[9].split(",") if x]
        racines = prof | (len(ap) << 16) | ((ap[0] + 1) << 32 if ap else 0)
        br = [int(x) for x in c[8].split(",") if x]
        branches = len(br) | (((br[0] + 1) << 16) | ((br[-1] + 1) << 40) if br else 0)
        promesses = n(c[10]) | (n(c[11]) << 16) | (n(c[12]) << 32) | ((n(c[13]) & 1) << 48)
        return [est, touche, racines, branches, promesses, int(c[14])]
    return None


d = tempfile.mkdtemp(prefix="vtx-faces-")
open(os.path.join(d, "faces.vtx"), "w", encoding="utf-8").write(PROG)
_, texte = lancer([LUGUS, "faces.vtx"], d)
verifier("lancé depuis son texte : pas de cube, les faces à 0 et le centre inconnu",
         texte.split("\n")[:12] == ["0"] * 12 and "inconnu" in texte and "49 5" in texte, texte[-300:])
lancer([LUGUS, "ranger", "faces.vtx"], d)
code, r = lancer([LUGUS, "cube", "faces.adn"], d)
verifier("lugus cube : le code à l'étage Đ, les faces aux étages 1 à 3, sous le cube mère",
         code == 0 and all(os.path.exists(os.path.join(d, f"{t}128-faces-{e}-440.cub"))
                           for t in ("cube", "anticube", "ombre") for e in ("Đ", "1", "2", "3"))
         and "les faces :" in r and "440/2" in r, r[-400:])
code, s = lancer([LUGUS, "cube128-faces.cub"], d)
lu = [l for l in s.split("\n") if not l.startswith("le cube")]
attendu = [str(x) for x in faces_attendues(os.path.join(d, "faces.adn"), "carre") + faces_attendues(os.path.join(d, "faces.adn"), "somme")]
verifier("lancé depuis son cube : les six faces de carre et de somme, celles de la carte rangée dans l'ADN",
         [str(int(x) % 2 ** 64) for x in lu[:12]] == attendu, f"{lu[:12]} / {attendu}")
verifier("les faces disent la promesse (somme : exige 1, garantit 1) et le genre (une réaction, une fonction)",
         len(lu) > 12 and int(lu[10]) & 0xFFFF == 1 and (int(lu[10]) >> 16) & 0xFFFF == 1 and int(lu[6]) & 15 == 3
         and int(lu[0]) & 15 == 2, lu[:12])
verifier("le centre : vrai (son code est celui du cube), et le programme tourne", lu[12:14] == ["vrai", "49 5"], lu[12:14])

# une avarie pendant qu'il tourne : un bit du code de carre change ; son centre devient variable
adn_l = open(os.path.join(d, "faces.adn"), encoding="utf-8").read().split("\n")
i = next(k for k, l in enumerate(adn_l) if l.startswith("GU faces "))
place = next(int(l.split("|")[0][1:]) for l in adn_l[i + 1:] if l.split("|")[1:2] == ["carre"])
_, s = lancer([LUGUS, "cube128-faces.cub"], d, {"LUGUS_AVARIE": f"1:{place + 1}:3"})
verifier("une avarie dans son code pendant qu'il tourne : son centre est variable", "variable" in s, s[-200:])

# le cube des faces abîmé : réparé à la lecture (faux), puis vrai une fois réécrit
f1 = os.path.join(d, "cube128-faces-1-440.cub")
b = bytearray(open(f1, "rb").read())
b[8 + 4 + 16 * place + 2] ^= 0x5A
open(f1, "wb").write(bytes(b))
_, s1 = lancer([LUGUS, "cube128-faces.cub"], d)
_, s2 = lancer([LUGUS, "cube128-faces.cub"], d)
verifier("le cube des faces abîmé : réparé en le lisant, les mêmes faces, le centre faux ; relu ensuite : vrai",
         "faux" in s1 and s1.split("\n")[:12] == s2.split("\n")[:12] and s2.split("\n")[12] == "vrai", f"{s1[-150:]!r} {s2[-150:]!r}")

# le cube mère : le descripteur des quatre étages à l'adresse 440
SQ = """fonction principal() {
    soit g = __service(29, "cube128-faces.cub");
    soit d: entier_128 = @[cube_adresse(1, g, 440)];
    pour e dans 0..4 {
        afficher((bas(d) >> (16 * e)) & 1023);
    }
}
"""
open(os.path.join(d, "squelette.vtx"), "w", encoding="utf-8").write(SQ)
_, s = lancer([LUGUS, "squelette.vtx"], d)
v = [int(x) for x in s.split("\n")[:4] if x.strip().isdigit()]
verifier("le cube mère : à l'adresse 440, les quatre étages présents (Đ le code, 1, 2, 3 les faces)",
         len(v) == 4 and all(x >= 512 for x in v), s[-200:])

# les mêmes mots par les deux compilateurs
for machine, b, src in (("lugus", LUGUS, PROG), ("dunon", DUNON, "fonction principal() {\n    afficher(face(10, 3));\n"
                                                                 "    selon centre(10) { inconnu { afficher(0); } vrai { afficher(1); } faux { afficher(2); } variable { afficher(3); } }\n}\n")):
    open(os.path.join(d, "m.vtx"), "w", encoding="utf-8").write(src)
    if machine == "lugus":
        m = vtx128.assembler(vtx128.compiler(src, dossier=d), True)[0]
    else:
        m = vtx64.assembler(vtx64.compiler(src, dossier=d))
    lancer([b, "compiler", "m.vtx", "m.mots"], d)
    ml = [int(x) for x in open(os.path.join(d, "m.mots")).read().split(";")[0].split(",") if x.strip()]
    verifier(f"{machine.capitalize()} : face et centre, les mêmes mots par les deux compilateurs", m == ml)
    if machine == "dunon":
        _, s = lancer([b, "m.vtx"], d)
        verifier("Dunon : pas lancé depuis un cube de programme, la face à 0 et le centre inconnu", s.split("\n")[:2] == ["0", "0"], s)

# un cube de la 0.63 : le programme à l'étage 1 (les faces ôtées, le code déplacé), lancé par son cube mère
vieux = os.path.join(d, "vieux")
os.makedirs(vieux)
for t in ("cube", "anticube", "ombre"):
    shutil.copy(os.path.join(d, f"{t}128-faces-Đ-440.cub"), os.path.join(vieux, f"{t}128-faces-1-440.cub"))
    shutil.copy(os.path.join(d, f"{t}128-faces.cub"), os.path.join(vieux, f"{t}128-faces.cub"))
_, s = lancer([LUGUS, "cube128-faces.cub"], vieux)
verifier("un cube de la 0.63 (le programme à l'étage 1) se lance encore par son cube mère", "49 5" in s and "le cube : vrai" in s, s[-200:])
_, s = lancer([LUGUS, "cube128-faces-1-440.cub"], d)
verifier("un cube des faces lancé seul : refusé (les mots sont à l'étage Đ)", "faces d'un programme" in s, s[-200:])

shutil.rmtree(d, ignore_errors=True)
print("les faces dans le cube : " + ("tout est conforme" if echecs == 0 else f"{echecs} écart(s)"))
sys.exit(1 if echecs else 0)
