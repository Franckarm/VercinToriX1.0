"""0.825 : Gutuater, son carnet et son ARN (gutuater/gutuater.vtx, gutuater/synapse.vtx).

    python3 tests/test_gutuater.py

1. les mêmes mots par vtx128.py et vtxc128 ;
2. les quatre états de la synapse (Belnap) : inconnu, vrai, faux, variable ; 0.826 : le seuil qui tremble (la
   résonance stochastique) : le bruit pur n'est jamais pris pour un gain, un vrai petit gain finit par se voir ;
3. l'usure : au-delà d'un poids de 24, les compteurs sont divisés par 2 (une croyance peut se renverser) ;
4. les mesures lues sont effacées (chacune ne compte qu'une fois)."""
import os
import subprocess
import sys
import tempfile

racine = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, racine)
import vtx128  # noqa: E402

vtx128.COMPAT_64 = False
LUGUS = os.path.join(racine, "vtx-rs", "target", "release", "lugus" + (".exe" if os.name == "nt" else ""))
GUT = os.path.join(racine, "gutuater", "gutuater.vtx")
D = tempfile.mkdtemp(prefix="gutuater-")
echecs = []


def verifier(nom, ok, detail=""):
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok or not detail else " : " + detail), flush=True)
    if not ok:
        echecs.append(nom)


def digerer(mesures):
    with open(os.path.join(D, "gutuater.mesures"), "w", encoding="utf-8") as f:
        f.write(mesures)
    r = subprocess.run([LUGUS, GUT], input=D + "\n", capture_output=True, text=True, encoding="utf-8")
    arn = {}
    for l in open(os.path.join(D, "gutuater.arn"), encoding="utf-8"):
        m = l.split()
        if len(m) == 3 and not m[0].startswith("#"):
            arn[(m[0], int(m[1]))] = m[2]
    carnet = {}
    for l in open(os.path.join(D, "gutuater.carnet"), encoding="utf-8"):
        m = l.split()
        if len(m) == 6 and m[0] == "gene":
            carnet[(m[1], int(m[2]))] = (int(m[3]), int(m[4]))
    return r, arn, carnet


# 1. les deux compilateurs
src = open(GUT, encoding="utf-8").read()
a = vtx128.assembler(vtx128.compiler(src, dossier=os.path.dirname(GUT)))
mo = os.path.join(D, "g.mots")
r = subprocess.run([LUGUS, "compiler", GUT, mo], capture_output=True, text=True)
b = [int(x) for x in open(mo).read().split(";")[0].split(",") if x] if r.returncode == 0 else None
verifier(f"gutuater.vtx : les mêmes mots par vtx128.py et vtxc128 ({len(a)} mots)", a == b, r.stdout + r.stderr)

# 2. les quatre états
r, arn, carnet = digerer("mesure lot 10 8000 9500\nmesure lot 10 8100 9400\n"   # le lot gagne 15 % : vrai
                         + "mesure lot 20 9500 8000\n"                           # il perd : faux
                         + "mesure lot 30 5000 5100\nmesure lot 30 5100 5000\n" * 10  # le bruit pur (±2 %)
                         + "mesure lot 60 9600 10000\n" * 20                     # un vrai gain de 4 %, sous le seuil
                         + "mesure lot 40 8000 9500\nmesure lot 40 9500 8000\n")   # pour et contre : variable
verifier("un gain de 15 %, deux fois : vrai", arn.get(("lot", 10)) == "vrai", str(arn))
verifier("une perte : faux", arn.get(("lot", 20)) == "faux", str(arn))
verifier("le bruit pur (±2 %, vingt fois) : jamais pris pour un gain ni une perte (inconnu ou variable)",
         arn.get(("lot", 30)) in ("inconnu", "variable"), str(carnet.get(("lot", 30))))
verifier("un vrai gain de 4 % (sous l'ancien seuil fixe de 5 %), vingt fois : le seuil qui tremble le voit (vrai)",
         arn.get(("lot", 60)) == "vrai" and carnet.get(("lot", 60))[1] == 0, str(carnet.get(("lot", 60))))
verifier("une preuve pour, une contre : variable", arn.get(("lot", 40)) == "variable", str(arn))
verifier("les mesures lues sont effacées", os.path.getsize(os.path.join(D, "gutuater.mesures")) == 0)

# 3. le carnet se garde d'un passage à l'autre, et l'usure renverse une vieille croyance
r, arn, carnet = digerer("")
verifier("sans mesure, le carnet reste", carnet.get(("lot", 10)) == (6, 0) and arn.get(("lot", 10)) == "vrai", str(carnet))
r, arn, carnet = digerer("mesure lot 10 9500 8000\n" * 7)        # 6 pour, 7 pertes fortes (21) : 27 > 24, usés en 3 et 10
verifier("l'usure : 6 pour + 21 contre, divisés par 2 : faux", carnet.get(("lot", 10)) == (3, 10) and arn.get(("lot", 10)) == "faux",
         str(carnet))

# 4. 0.826 : une variante infidèle (la garde l'a vue) : tue pour toujours, l'usure n'y touche pas
r, arn, carnet = digerer("infidele fondre 50\n")
verifier("infidèle : faux, 64 preuves contre", arn.get(("fondre", 50)) == "faux" and carnet.get(("fondre", 50)) == (0, 64), str(carnet))
r, arn, carnet = digerer("mesure fondre 50 100 900\n" * 3)
verifier("puis trois gains : toujours faux (l'usure ne touche pas une infidélité)",
         arn.get(("fondre", 50)) == "faux" and carnet.get(("fondre", 50)) == (9, 64), str(carnet))

print("Tout est conforme" if not echecs else f"{len(echecs)} échec(s)")
sys.exit(1 if echecs else 0)
