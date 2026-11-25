# 0.835 : Ésus (la forge) : la division et le reste d'un entier de 128 bits par une constante, changés en
# multiplication : la même sortie que Lugus (l'émulateur), et que la forge sans Ésus (VTX_ESUS=0).
import os, subprocess, sys, tempfile
ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
WIN = os.name == "nt"
LUGUS = os.path.join(racine, "vtx-rs", "target", "release", "lugus" + (".exe" if WIN else ""))
PROG = os.path.join(ici, "esus.vtx")
d = tempfile.mkdtemp()
echecs = 0


def verifier(nom, ok, detail=""):
    global echecs
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok else " : " + str(detail)[:600]))
    if not ok:
        echecs += 1


def forger(sortie, esus):
    env = dict(os.environ)
    env["VTX_ESUS"] = "1" if esus else "0"
    r = subprocess.run([sys.executable, os.path.join(racine, "forge", "forge128.py"), PROG, "-o", sortie],
                       capture_output=True, text=True, env=env)
    return r.returncode == 0, r.stdout + r.stderr


rl = subprocess.run([LUGUS, PROG], capture_output=True, text=True).stdout
for esus in (True, False):
    exe = os.path.join(d, "esus_" + ("oui" if esus else "non") + (".exe" if WIN else ""))
    ok, info = forger(exe, esus)
    rf = subprocess.run([exe], capture_output=True, text=True).stdout if ok else info
    verifier(("avec" if esus else "sans") + " Ésus : la forge donne la sortie de Lugus", ok and rf == rl, rf[-300:] + " / " + rl[-300:])
# 0.837 : la membrane des cellules : un paramètre reçoit ce que ses appelants y mettent ; un retour, ce qu'il prouve
rel = {}
for l in open(os.path.join(d, "esus_oui.esus"), encoding="utf-8"):
    m = l.split()
    if len(m) == 8:
        rel[(m[0], m[1])] = m[2:]
verifier("la membrane : brasser_mol a (appelé avec k de 0 à 100, et 3) borné", rel.get(("brasser_mol", "a"), [0, ""])[1] == "7f",
         rel.get(("brasser_mol", "a")))
verifier("la membrane : sommer_mol n (appelé avec j % 100) borné", rel.get(("sommer_mol", "n"), ["", ""])[5:] == ["63"],
         rel.get(("sommer_mol", "n")))
verifier("la membrane, récursive : descendre_mol acc borné par son reste (au moins 100002, élargi à une puissance de deux)",
         100002 <= int(rel.get(("descendre_mol", "acc"), ["", "0"])[1], 16) < 1 << 20, rel.get(("descendre_mol", "acc")))
verifier("la membrane du cube : v lu dans la table (fréquence 9) borné par ce qui y est écrit (au plus 1000002)",
         rel.get(("table_du_cube", "v"), ["", ""])[1] == "f4242", rel.get(("table_du_cube", "v")))
import shutil
shutil.rmtree(d, ignore_errors=True)
print("Ésus : " + ("tout est conforme" if echecs == 0 else f"{echecs} écart(s)"))
sys.exit(1 if echecs else 0)
