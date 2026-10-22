#!/usr/bin/env python3
"""Test du débogueur au niveau du source : séquences de pas, pas par-dessus, sortie de fonction, points d'arrêt,
valeurs des variables (entier, flottant, long), pile d'appels ; puis un essai sur le jeu complet (8 000 mots)."""
import importlib.util
import os

ici = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("vtx", os.path.join(ici, "..", "vtx.py"))
vtx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vtx)
src = open(os.path.join(ici, "demo.vtx"), encoding="utf-8").read()
ok, total = 0, 0


def verifie(nom, obtenu, attendu):
    global ok, total
    total += 1
    bon = obtenu == attendu
    ok += bon
    if not bon:
        print(f"ÉCHEC {nom} : obtenu {obtenu!r}, attendu {attendu!r}")


def ou(d):
    return d.lieu(d.cpu.pc)[:2] if d.cpu.pc in d.debut else None


nouveau = lambda: vtx.Debogueur(src, (), ici, "demo.vtx")
# 1. pas à pas : entre dans norme puis dans carre (fichier importé)
d = nouveau()
d.demarrer()
suite = [ou(d)]
for _ in range(6):
    d.pas()
    suite.append(ou(d))
verifie("pas à pas", suite, [("demo.vtx", 9), ("demo.vtx", 10), ("demo.vtx", 11), ("demo.vtx", 4), ("outils.vtx", 3),
                             ("outils.vtx", 4), ("outils.vtx", 3)])
verifie("pile d'appels", d.pile(), [("carre", "outils.vtx", 3), ("norme", "demo.vtx", 4), ("principal", "demo.vtx", 11)])
verifie("flottant x (deuxième appel de carre)", d.valeur("x")[1], -4.0)
# 2. sortir, puis pas par-dessus
d.sortir()
verifie("sortie de carre", ou(d), ("demo.vtx", 5))
verifie("c = 3² + 4²", d.valeur("c")[1], 25.0)
d.suivant()
d.suivant()
verifie("pas par-dessus norme et la sortie", (ou(d), d.cpu.sortie), (("demo.vtx", 13), [500]))
# 3. point d'arrêt dans un fichier importé, à l'intérieur d'une boucle
verifie("pose du point d'arrêt", d.arreter_a(10, "outils.vtx") > 0, True)
vus = []
for _ in range(4):
    d.continuer()
    vus.append((d.valeur("i")[1], d.valeur("total")[1]))
verifie("point d'arrêt dans la boucle", vus, [(1, 0), (2, 1), (3, 5), (4, 14)])
verifie("aucune instruction à une ligne vide", d.arreter_a(6, "outils.vtx"), 0)
d.enlever(10, "outils.vtx")
d.sortir()
verifie("long de 64 bits", d.valeur("grand")[1], sum(i * i for i in range(1, 3001)))
d.suivant()
d.suivant()
d.suivant()
verifie("entier négatif", (d.valeur("k")[1], "signé -3" in d.valeur("k")[0]), (4294967293, True))
d.continuer()
verifie("fin et sorties", (d.cpu.halted, d.cpu.sortie), (True, [500, 9004500500 & 0xFFFFFFFF, 9004500500 >> 32, 4294967293]))
# 4. le débogage ne change pas l'exécution (au pas à pas, les variables restent dans le cadre : on compare au même
# programme sans variables en registres ; avec elles, il en faut moins)
ancien, vtx.REGISTRES = vtx.REGISTRES, False
cpu, _, _ = vtx.executer(src, (), dossier=ici)
vtx.REGISTRES = ancien
verifie("même nombre d'instructions qu'en exécution normale", d.cpu.pas, cpu.pas)
cpu2, _, _ = vtx.executer(src, (), dossier=ici)
verifie("les registres gardent les sorties et font moins d'instructions", (cpu2.sortie, cpu2.pas < cpu.pas),
        (cpu.sortie, True))
# 5. session en ligne de commande
import io
import contextlib
tampon = io.StringIO()
with contextlib.redirect_stdout(tampon):
    vtx.deboguer(src, (), ici, "demo.vtx", ["a 16", "c", "v k", "pile", "mem @2[0] 2", "regs", "aide", "zzz", "v inconnue", "c", "q"])
texte = tampon.getvalue()
verifie("session : arrêt ligne 16 et valeur", ("demo.vtx, ligne 16" in texte, "k = 7 (#00000007)" in texte), (True, True))
verifie("session : commandes inconnues signalées", ("commande inconnue" in texte, "variable « inconnue » inconnue ici" in texte), (True, True))
verifie("session : fin", "fin du programme" in texte, True)
print(f"débogueur, programme de démonstration : {ok}/{total} vérifications")

# 6. jeu complet : point d'arrêt dans blesser() quand un ennemi touche le joueur
jeu = os.path.join(ici, "..", "jeu3")
jsrc = open(os.path.join(jeu, "jeu3.vtx"), encoding="utf-8").read()
dj = vtx.Debogueur(jsrc, [0, 1, 2, 3, 4, 5, 6] + [0] * 10 + [13, 6, 0], jeu, "jeu3.vtx")
dj.demarrer()
dj.continuer()
store = dj.cpu.mem
lignes = open(os.path.join(jeu, "monde3.vtx"), encoding="utf-8").read().split("\n")
ligne_perte = next(i for i, l in enumerate(lignes, 1) if "soit perte = coups * degat;" in l)
dj2 = vtx.Debogueur(jsrc, [1], jeu, "jeu3.vtx")
dj2.cpu.mem = store
dj2.cpu.mem[(2, 220)], dj2.cpu.mem[(2, 221)] = 22 * 256 + 128, 6 * 256 + 128
for k in range(8):
    m = store[(2, k)]
    if (m >> 24, (m >> 16) & 255) == (22, 5):
        store[(2, k)] = (m & ~(255 << 8)) | (2 << 8)
n = dj2.arreter_a(ligne_perte, "monde3.vtx")
dj2.demarrer()
dj2.continuer()
arrete = ou(dj2)
coups = dj2.valeur("coups")[1] if arrete else None
print(f"jeu complet ({len(dj2.debuts)} instructions source repérées, {len(dj2.fonctions)} fonctions) : "
      f"arrêt en {arrete} avec coups = {coups} ; pile : {[f for f, _, _ in dj2.pile()]}")
