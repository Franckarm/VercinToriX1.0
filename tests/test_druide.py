# 0.835 : le Druide, premier geste : il range le relevé d'Ésus dans son cube (les quatre points sur les quatre étages
# de la fréquence 4040) et compare en quatre valeurs avec ce qu'il savait : inconnu (nouvelle), vrai (pareil ou plus
# serré), faux (plus large), variable (déplacée). Le programme étudié n'est pas touché.
import os, shutil, subprocess, sys, tempfile
ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
WIN = os.name == "nt"
LUGUS = os.path.join(racine, "vtx-rs", "target", "release", "lugus" + (".exe" if WIN else ""))
d = tempfile.mkdtemp()
echecs = 0


def verifier(nom, ok, detail=""):
    global echecs
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok else " : " + str(detail)[:600]))
    if not ok:
        echecs += 1


PROG = """fonction principal() {
    soit s = 0;
    pour i dans 0..N {
        soit a = (i & 1023) * 2654435761;
        soit b = a % 1000003;
        s = s ^ (b * 7 + i / 3);
    }
    afficher(s);
}
"""
# le Druide dans une copie : son cube (sa mémoire) reste dans le dossier du test
dr = os.path.join(d, "druide")
os.makedirs(dr)
shutil.copy(os.path.join(racine, "druide", "druide.vtx"), dr)
etats = []
for n in ("1000", "1000", "500", "2000"):
    p = os.path.join(d, "essai_druide.vtx")
    open(p, "w", encoding="utf-8").write(PROG.replace("N", n))
    exe = os.path.join(d, "essai_druide" + (".exe" if WIN else ""))
    r = subprocess.run([sys.executable, os.path.join(racine, "forge", "forge128.py"), p, "-o", exe], capture_output=True, text=True)
    releve = os.path.join(d, "essai_druide.esus")
    r = subprocess.run([LUGUS, os.path.join(dr, "druide.vtx")], input=releve + "\n", capture_output=True, text=True)
    carnet = open(os.path.join(d, "essai_druide.druide"), encoding="utf-8").read() if os.path.exists(os.path.join(d, "essai_druide.druide")) else ""
    vu = {l.split()[1]: l.split()[2] for l in carnet.splitlines() if l.startswith("principal ")}
    etats.append(vu)
verifier("la première fois : toutes les variables sont nouvelles (inconnu)", set(etats[0].values()) == {"inconnu"}, etats[0])
verifier("la même forge : tout est pareil (vrai)", set(etats[1].values()) == {"vrai"}, etats[1])
verifier("la boucle raccourcie : i plus serré (vrai), les autres pareils (vrai)", etats[2].get("i") == "vrai" and set(etats[2].values()) == {"vrai"}, etats[2])
# a = (i & 1023) * … : après 500 tours, sa borne s'était resserrée avec i ; 2000 tours l'élargissent (faux) ; b reste
# plafonné par le reste (1000002 : vrai)
verifier("la boucle allongée : i et a plus larges (faux), b pareil (vrai)",
         etats[3].get("i") == "faux" and etats[3].get("a") == "faux" and etats[3].get("b") == "vrai", etats[3])
verifier("le Druide range dans son cube à lui (sous le cube mère du programme), pas à côté du programme",
         any(f.startswith("cube128-essai_druide-") for f in os.listdir(dr)) and not any(f.startswith("cube128-") for f in os.listdir(d)),
         os.listdir(dr))
shutil.rmtree(d, ignore_errors=True)
print("le Druide : " + ("tout est conforme" if echecs == 0 else f"{echecs} écart(s)"))
sys.exit(1 if echecs else 0)
