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
# relier : la forge compte le travail de chaque molécule (VTX_DRUIDE=poids) : principal porte ses 1000 tours
p = os.path.join(d, "poids_druide.vtx")
open(p, "w", encoding="utf-8").write(PROG.replace("N", "1000"))
exe = os.path.join(d, "poids_druide" + (".exe" if WIN else ""))
env = dict(os.environ, VTX_DRUIDE="poids")
subprocess.run([sys.executable, os.path.join(racine, "forge", "forge128.py"), p, "-o", exe], capture_output=True, env=env)
subprocess.run([exe], capture_output=True)
poids = {}
if os.path.exists(os.path.join(d, "poids_druide.poids")):
    for l in open(os.path.join(d, "poids_druide.poids"), encoding="utf-8"):
        m = l.split()
        if len(m) == 2:
            poids[m[0]] = int(m[1])
verifier("relier : le travail de principal compté (ses 1000 tours et son appel)", poids.get("principal") == 1001, poids)
# adapter : l'ARN du Druide déconnecte Ésus d'une molécule : la forge ne la taille plus (et le résultat ne change pas)
sys.path.insert(0, os.path.join(racine, "forge"))
import forge128  # noqa: E402
src = open(p, encoding="utf-8").read()
sortie = os.path.join(d, "arn_druide")
code1, _ = forge128.source_rust(src, d, "arn_druide", sortie)
open(sortie + ".arn", "w", encoding="utf-8").write("esus principal 0\n")
code0, _ = forge128.source_rust(src, d, "arn_druide", sortie)


def corps_principal(code):
    i = code.find("fn f_principal(")
    return code[i:code.find("\n}\n", i)]


verifier("adapter : sans ARN, Ésus taille principal (le reste par une constante sans division)",
         "modk128(" in corps_principal(code1) or "as u64) %" in corps_principal(code1), corps_principal(code1)[:400])
verifier("adapter : « esus principal 0 » : Ésus déconnecté de principal", "modk128(" not in corps_principal(code0)
         and "as u64) %" not in corps_principal(code0), corps_principal(code0)[:400])
shutil.rmtree(d, ignore_errors=True)
print("le Druide : " + ("tout est conforme" if echecs == 0 else f"{echecs} écart(s)"))
sys.exit(1 if echecs else 0)
