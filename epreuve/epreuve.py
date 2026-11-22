#!/usr/bin/env python3
"""L'épreuve d'Alésia : un seul passage, parlant, sur tout ce que fait Vercintorix (0.69).

    python epreuve/epreuve.py

Huit chapitres, chacun dit ce qu'il montre puis le vérifie :
    I.   La forge       : créer une réaction à la paillasse d'Ogmios, case par case ; les deux compilateurs d'accord
    II.  Programmer     : structures, textes, tableaux, dictionnaires, fonctions passées en valeur
    III. Compter        : entiers de 128 bits exacts, flottants de 128 bits, le flottant quaternaire, multiplier_ajouter
    IV.  Douter         : la logique de Belnap (inconnu, faux, vrai, variable), le savoir qui garde la contradiction
    V.   Réagir         : les réactions (vagues sur plusieurs cœurs, la division par zéro réparée)
    VI.  Se souvenir    : ARNc -> ADN -> hex -> cube -> hex -> ADN -> ARN, et chaque forme redonne le même programme
    VII. Se défendre    : le juge des promesses, les types, la patrouille qui répare, l'apoptose qui refuse le faux
    VIII. Voir          : Belenos, le val des neiges ; la même image en vtx et en C, et le temps de chacun
Chaque vérification écrit [ok] ou [!!] ; à la fin, le bilan. Rien n'est écrit hors d'un dossier temporaire."""
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
from decimal import Decimal, getcontext

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, racine)
sys.path.insert(0, os.path.join(racine, "chimie"))
sys.setrecursionlimit(20000)
X = ".exe" if os.name == "nt" else ""
BIN = os.path.join(racine, "vtx-rs", "target", "release")
LUGUS = os.path.join(BIN, "lugus" + X)
VTX = os.path.join(BIN, "vtx" + X)
ALESIA = os.path.join(ici, "alesia.vtx")
d = tempfile.mkdtemp(prefix="epreuve-")
bilan = []      # (chapitre, réussies, total)
chapitre = [None, 0, 0]
debut = time.time()


def titre(t, dit):
    if chapitre[0]:
        bilan.append(tuple(chapitre))
    chapitre[:] = [t, 0, 0]
    print("\n" + "=" * 100)
    print(t)
    print("=" * 100)
    for l in dit.split("\n"):
        print("  " + l)
    print(flush=True)


def verifier(quoi, ok, detail=""):
    chapitre[2] += 1
    chapitre[1] += 1 if ok else 0
    print(("  [ok] " if ok else "  [!!] ") + quoi + ("" if ok or not detail else "\n       " + detail[-400:]), flush=True)
    return ok


def dire(t):
    print("       " + t, flush=True)


def lugus(*args, env=None, entree=None):
    e = dict(os.environ)
    e.pop("LUGUS_AVARIE", None)
    e.pop("VTX_FENETRE", None)
    e.update(env or {})
    r = subprocess.run([LUGUS, *args], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=d, env=e,
                       input=entree, timeout=900)
    return r.returncode, r.stdout.replace("\r\n", "\n"), r.stderr.replace("\r\n", "\n")


def ecrire(nom, texte):
    f = os.path.join(d, nom)
    open(f, "w", encoding="utf-8", newline="\n").write(texte)
    return f


if not os.path.exists(LUGUS):
    print("lugus n'est pas construit : cd vtx-rs puis cargo build --release ; l'épreuve n'a rien vérifié")
    sys.exit(1)

import adn     # noqa: E402  (chimie/adn.py : la référence de l'ADN, pour trouver les molécules à abîmer)
import vtx128  # noqa: E402  (le compilateur de référence, en Python)

# ================================================================================================= I. la forge
titre("I. LA FORGE : créer un programme, case par case, puis le compiler deux fois",
      "Ogmios a une paillasse : chaque case est un atome d'une réaction. Les quatre éléments de structure (H, O, N, C)\n"
      "viennent du nombre de liaisons et composent la molécule de registre ; les autres éléments disent ce que fait la\n"
      "case (S la logique, Fe la mémoire du cube, Mg les vagues, Zn la réparation…). On pose ici des cases depuis la\n"
      "palette, comme avec le menu Cases d'Ogmios, puis on vérifie que les deux compilateurs donnent les mêmes mots.")
src_forge = "reaction principal() {\n    = [4, 8, 15, 16, 23, 42] -> t\n}\n"
f_forge = ecrire("forge.vtx", src_forge)
gestes = ecrire("forge.gestes", "poser somme\nposer reparer\nposer fusion\ndroit 900 560\ncase fin\npalette\n")
r = subprocess.run([VTX, "paillasse", f_forge, "--gestes", gestes, "--analyse"], capture_output=True, text=True,
                   encoding="utf-8", errors="replace", cwd=d)
sortie_forge = r.stdout.replace("\r\n", "\n")
texte = sortie_forge.split("--- le texte\n")[-1] if "--- le texte" in sortie_forge else ""
verifier("trois cases posées depuis la palette (somme, reparer, fusion) s'écrivent dans la réaction",
         "= somme pour chaque v dans _ : v -> l1" in texte and "= reparer _ / _ par 0 -> l2" in texte
         and "= fusion(_, _) -> l3" in texte, sortie_forge)
verifier("un clic droit dans le vide ouvre le menu des cases ; la case « fin » choisie s'y pose (la sortie du programme)",
         "le menu des cases, en (900, 560)" in sortie_forge and "= sortie(_)" in texte, sortie_forge[-500:])
familles = [l.split()[0] for l in sortie_forge.split("\n") if " — " in l and l[:1].isupper() and not l.startswith("Case")]
verifier(f"la palette expliquée : {len(familles)} familles ({' '.join(familles)})", len(familles) >= 15, sortie_forge[-600:])
for l in texte.strip().split("\n"):
    dire(l)
# 0.70 : la place d'une case dans les vagues décide de sa ligne ; une page neuve, et la suite qui y renvoie
VAGUES = ("reaction calcul(a, b) -> r {\n    = a + b -> s\n    = s * 2 -> d\n    = a * 3 -> t\n    = d + t -> r\n}\n"
          "fonction principal() { afficher(calcul(2, 5)); }\n")
f_v = ecrire("vagues.vtx", VAGUES)
g_v = ecrire("vagues.gestes", "bas 310 78\nbouge 470 260\nhaut 470 260\n")
r = subprocess.run([VTX, "paillasse", f_v, "--gestes", g_v], capture_output=True, text=True, encoding="utf-8",
                   errors="replace", cwd=d)
tv = r.stdout.replace("\r\n", "\n").split("--- le texte\n")[-1]
verifier("une case glissée de la vague 2 à la vague 3 : sa ligne passe à la place de la vague 3 dans le texte",
         tv.find("= s * 2 -> d") > tv.find("= d + t -> r") > 0, tv[-300:])
f_o = ecrire("ordre.vtx", VAGUES)
g_o = ecrire("ordre.gestes", "bas 150 190\nbouge 150 30\nhaut 150 30\n")
r = subprocess.run([VTX, "paillasse", f_o, "--gestes", g_o], capture_output=True, text=True, encoding="utf-8",
                   errors="replace", cwd=d)
to = r.stdout.replace("\r\n", "\n").split("--- le texte\n")[-1]
verifier("une case montée au-dessus d'une autre dans sa vague : sa ligne passe avant elle (la paillasse fait l'ordre du texte)",
         0 < to.find("= a * 3 -> t") < to.find("= a + b -> s"), to[-300:])
# 0.72 : la fenêtre d'édition d'une case (clic droit) : une entrée de plus, une sortie renommée partout
f_e = ecrire("edition.vtx", VAGUES)
g_e = ecrire("edition.gestes", "droit 150 100\nbas 785 115\nbas 800 230\ntouche 8\ncar somme_ab\ntouche 13\n")
subprocess.run([VTX, "paillasse", f_e, "--gestes", g_e, "--ecrire"], capture_output=True, cwd=d)
te = open(f_e, encoding="utf-8").read()
verifier("la fenêtre d'édition d'une case : une entrée libre de plus, la sortie renommée là où on la lisait",
         "= a + b + _ -> somme_ab" in te and "= somme_ab * 2 -> d" in te, te)
f_p = ecrire("pages.vtx", "reaction principal() {\n    = [3, 4, 5] -> t\n    = somme pour chaque v dans t : v -> s\n}\n")
g_p = ecrire("pages.gestes", "droit 600 300\ncase suite\necrire = sortie(page_2(s))\n")
subprocess.run([VTX, "paillasse", f_p, "--gestes", g_p, "--ecrire"], capture_output=True, cwd=d)
c, s, e = lugus(f_p)
tp = open(f_p, encoding="utf-8").read()
verifier("la case « suite » (Ne) crée la page 2 et y renvoie sa valeur : le programme à deux pages rend 12",
         "reaction page_2(entree) -> fin" in tp and s.strip() == "12", tp + s + e)
f_a = ecrire("appel.vtx", "reaction principal() {\n    = [3, 4, 5] -> t\n    = somme pour chaque v dans t : v -> s\n}\n")
g_a = ecrire("appel.gestes", "droit 600 300\ncase appeler\necrire = page_2(s) -> d\n")
subprocess.run([VTX, "paillasse", f_a, "--gestes", g_a, "--ecrire"], capture_output=True, cwd=d)
ta = open(f_a, encoding="utf-8").read().replace("    = page_2(s) -> d\n", "    = page_2(s) -> d\n    = sortie(d * 2)\n")
open(f_a, "w", encoding="utf-8").write(ta)
c, s, e = lugus(f_a)
verifier("la case « appeler » : la page 2 comme sous-programme, son résultat revient ((3 + 4 + 5) × 2 = 24)",
         s.strip() == "24", ta + s + e)
# la réaction complétée à la main (les « _ » deviennent des liaisons) : elle compile et réagit
src_complete = ("reaction principal() {\n"
                "    = [4, 8, 15, 16, 23, 42] -> t\n"
                "    = somme pour chaque v dans t : v -> l1\n"
                "    = reparer l1 / 6 par 0 -> l2\n"
                "    = sortie(l2)\n"
                "}\n")
f_complete = ecrire("forge2.vtx", src_complete)
c, s, e = lugus(f_complete)
verifier("les « _ » reliés (t -> somme -> partage par 6) : la réaction réagit, la moyenne des six nombres vaut 18",
         c == 0 and s.strip() == "18", s + e)
src = open(ALESIA, encoding="utf-8").read()
t0 = time.time()
ref = vtx128.assembler(vtx128.compiler(src, dossier=ici))
t_py = time.time() - t0
f_mots = os.path.join(d, "alesia.mots")
t0 = time.time()
lugus("compiler", ALESIA, f_mots)
t_vtx = time.time() - t0
mots = [int(x) for x in open(f_mots).read().split(";")[0].split(",") if x.strip()] if os.path.exists(f_mots) else []
verifier(f"alesia.vtx compilé deux fois : par vtx128.py (Python, {t_py:.1f} s) et par vtxc128 (écrit en vtx, "
         f"{t_vtx:.1f} s) : les mêmes {len(ref)} mots de 128 bits", ref == mots and len(ref) > 1000,
         f"{len(ref)} contre {len(mots)}")

# ================================================================================================= II à V
c, s, e = lugus(ALESIA)
lignes = [l for l in s.split("\n") if l.strip()]
if lignes and lignes[0] == "52":       # la sortie du programme vient d'abord
    lignes = lignes[1:]


def ligne(debut):
    return next((l for l in lignes if l.startswith(debut)), "(absente)")


def montrer(debut, attendu, quoi):
    l = ligne(debut)
    ok = l == debut + attendu
    verifier(quoi + (" : " + l[len(debut):].strip() if ok else ""), ok, f"lu : {l!r}\n       attendu : {debut + attendu!r}")


getcontext().prec = 60
fib = [0, 1]
while len(fib) < 152:
    fib.append(fib[-1] + fib[-2])
racine2 = str(Decimal(2).sqrt())[:35]

titre("II. PROGRAMMER : ce qu'écrit un druide",
      "Le programme epreuve/alesia.vtx est lancé sur Lugus (la machine de 128 bits). Structures, textes accentués,\n"
      "tableaux, dictionnaires, et des fonctions passées en valeur qui promettent ce qu'elles touchent.")
verifier("alesia.vtx se lance sur Lugus et rend sa sortie (52)", c == 0 and s.split("\n")[0].strip() == "52", e[-300:])
montrer("structure :", " Astérix 7 vrai", "une structure Guerrier, son nom, sa force, sa potion (une logique)")
montrer("texte :", " Astérix gagne / ALÉSIA", "les textes : concaténer, comparer, majuscules accentuées")
montrer("tableau trié :", " 1 3 5 7 9 somme 25", "un tableau trié et sommé")
montrer("fonction en valeur :", " 25 144", "plier(t, plus, 0) et appliquer(carre, 12) : des fonctions passées en valeur")
montrer("dictionnaire :", " 52 0", "un dictionnaire fermé : Alésia y est (52), Rome n'y est pas (0)")

titre("III. COMPTER : exact quand il le faut",
      "Les entiers de 128 bits ne débordent pas là où ceux de 64 bits débordent ; le flottant de 128 bits donne 34\n"
      "chiffres ; le flottant quaternaire (base 4) est montré tel qu'il est ; chaque valeur est vérifiée par Python.")
montrer("30! en 128 bits :", f" {math.factorial(30)}", "30! (33 chiffres, au-delà des 64 bits), vérifié par Python")
montrer("fibonacci(150) :", f" {fib[150]}", "fibonacci(150), vérifié par Python")
montrer("entier de 128 bits, le plus grand :", f" {2 ** 127 - 1}", "le plus grand entier de 128 bits : 2^127 - 1")
montrer("un tiers en flottant de 128 bits :", " 0." + "3" * 34, "1/3 en flottant de 128 bits : 34 chiffres")
montrer("0.1 en flottant quaternaire de 64 bits :", " 0.1 ; plus lui-même : 0.19999999999999996",
        "le flottant quaternaire (base 4) de 64 bits")
dire("0.1 n'a pas d'écriture exacte en base 4 (ni en base 2) : le plus proche s'affiche « 0.1 », et doublé il montre")
dire("sa vraie valeur, 0.19999999999999996 : la même chose que 0.1 + 0.2 = 0.30000000000000004 en IEEE. Le doute")
dire("est dit, pas caché ; multiplier_ajouter et le flottant de 128 bits sont là quand il faut plus juste.")
montrer("multiplier_ajouter(3, 4, 5) :", f" 17.0 ; racine de 2 : {racine2}",
        "multiplier_ajouter (un seul arrondi) et la racine de 2 sur 34 chiffres, vérifiée par Python")

titre("IV. DOUTER : quatre valeurs, pas deux",
      "Inconnu (aucune preuve), faux, vrai, variable (des preuves des deux côtés). Deux témoignages contraires ne\n"
      "s'écrasent pas : ils donnent variable, et le programme le sait.")
montrer("fusion(vrai, faux) :", " variable ; fusion(vrai, inconnu) : vrai",
        "fusion : vrai et faux ensemble donnent variable ; vrai et inconnu donnent vrai")
montrer("savoir potion :", " vrai ; savoir sanglier : inconnu", "un savoir ouvert : ce qu'on n'a jamais dit est inconnu, pas faux")
montrer("puis nier potion :", " variable", "affirmer puis nier : la contradiction est gardée (variable)")

titre("V. RÉAGIR : des réactions plutôt que des boucles",
      "Une réaction dit ce qui est indépendant : une vague de 10 000 atomes réduite en une somme, partagée entre les\n"
      "cœurs ; une division par zéro ne plante pas, elle rend variable, et « reparer … par 0 » la répare.")
montrer("somme des carrés de 0 à 9999 :", f" {sum(k * k for k in range(10000))}",
        "une vague de 10 000 carrés réduite en une somme, vérifiée par Python")
montrer("partage 84 / 2 :", " 42 ; 84 / 0 réparé : 0", "84 / 2 puis 84 / 0 réparé par 0")
montrer("moyenne de 2.5 et 4.5 :", " 3.5", "une réaction de flottants")
t0 = time.time()
rp = subprocess.run([sys.executable, os.path.join(racine, "vtx128.py"), "run", ALESIA], capture_output=True, text=True,
                    encoding="utf-8", errors="replace", cwd=d, env=dict(os.environ, PYTHONIOENCODING="utf-8"))
lp = [l for l in rp.stdout.replace("\r\n", "\n").split("\n") if l.strip() and not l.startswith(("52", "4064 mots"))]
lp = [l for l in lp if "instructions exécutées" not in l and not l.startswith("sortie :")]
verifier(f"la machine de référence en Python ({time.time() - t0:.1f} s) rend les mêmes {len(lignes)} lignes que Lugus en Rust",
         lp == lignes, "\n".join(x for x in lp if x not in lignes)[:300])

# ================================================================================================= VI. la mémoire
titre("VI. SE SOUVENIR : le chemin ARNc -> ADN -> hex -> cube -> hex -> ADN -> ARN",
      "L'ARNc est le travail (le programme et son texte), l'ADN la mémoire gardée (avec ses témoins, qui réparent),\n"
      "le hex les adresses, le cube la mémoire vivante (étage Đ, sa coiffe, sa queue, son anti-cube et son ombre).\n"
      "Le programme fait tout le tour ; à chaque étape on le relance : il doit redire exactement les mêmes lignes.")
shutil.copy(ALESIA, os.path.join(d, "alesia.vtx"))
etapes = [("ARNc (le travail)", ["arnc", "alesia.vtx", "alesia.arn"], "alesia.arn"),
          ("ADN (la mémoire gardée)", ["ranger", "alesia.arn", "alesia.adn"], "alesia.adn"),
          ("hex (les adresses)", ["hex", "alesia.adn", "alesia.hex"], "alesia.hex"),
          ("cube (la mémoire vivante)", ["cube", "alesia.hex", "52"], "cube128-alesia-Đ-52.cub"),
          ("hex relu du cube", ["hex", "cube128-alesia-Đ-52.cub", "retour.hex"], "retour.hex"),
          ("ADN rangé de nouveau", ["ranger", "retour.hex", "retour.adn"], "retour.adn"),
          ("ARN transcrit", ["transcrire", "retour.adn", "retour.arn"], "retour.arn")]
for nom, args, fichier in etapes:
    c1, s1, e1 = lugus(*args)
    c2, s2, e2 = lugus(fichier)
    l2 = [l for l in s2.split("\n") if l.strip()]
    taille = os.path.getsize(os.path.join(d, fichier)) if os.path.exists(os.path.join(d, fichier)) else 0
    verifier(f"{nom:<28} {fichier:<26} {taille:>8} octets : relancé, les mêmes lignes",
             c1 == 0 and c2 == 0 and l2[1:] == lignes and l2[:1] == ["52"], (s1 + e1 + e2)[-300:])
verifier("le hex revenu du cube est le même, octet pour octet",
         open(os.path.join(d, "alesia.hex"), "rb").read() == open(os.path.join(d, "retour.hex"), "rb").read())
pres = [f for f in os.listdir(d) if f.endswith(".cub")]
verifier(f"le cube est posé avec ses gardiens : {', '.join(sorted(pres))}",
         any(f.startswith("anticube128") for f in pres) and any(f.startswith("ombre128") for f in pres))

# ================================================================================================= VII. se défendre
titre("VII. SE DÉFENDRE : refuser ce qui ment, réparer ce qui s'abîme, s'arrêter plutôt que rendre le faux",
      "Le juge lit les promesses (« touche rien ») et les types avant de compiler ; la patrouille relit l'ADN pendant\n"
      "qu'il tourne et répare avec ses témoins ; abîmé au-delà de ce qui se répare, le programme meurt (l'apoptose)\n"
      "plutôt que de rendre un résultat faux. Les avaries sont posées exprès (LUGUS_AVARIE=PAS:MOT:BIT).")


def refus(nom, texte, mot, les_deux=True):
    """lugus refuse (rien ne tourne) ; les_deux : le compilateur de référence en Python refuse aussi"""
    f = ecrire(nom, texte)
    c1, s1, e1 = lugus(f)
    try:
        vtx128.compiler(texte, dossier=d)
        py = "accepté"
    except Exception as x:   # noqa: BLE001
        py = str(x)
    return (c1 != 0 and s1.strip() == "" and mot in e1 and (mot in py or not les_deux),
            (e1.strip().split("\n") or [""])[0], py)


ok, m, py = refus("menteur.vtx", "fonction calme(x) touche rien { @3[5] = x; retour x; }\n"
                                 "fonction principal() { afficher(calme(3)); }\n", "promesse rompue", False)
verifier("une fonction qui promet « touche rien » mais écrit le cube : refusée par le juge (la carte, écrite en vtx), "
         "rien ne tourne", ok, m)
dire(m)
ok, m, py = refus("passeur.vtx", "fonction ecrit(x) { @3[1] = x; retour x; }\n"
                                 "fonction appliquer(f: fonction(entier): entier touche rien, x) touche rien { retour f(x); }\n"
                                 "fonction principal() { afficher(appliquer(ecrit, 3)); }\n", "ne convient pas")
verifier("une fonction qui écrit, passée là où l'on attend une fonction qui ne touche rien : refusée par les deux "
         "compilateurs", ok, m + " / " + py)
dire(m)
ok, m, py = refus("faute.vtx", "fonction principal() { soit guerrier = 3; afficher(guerier); }\n", "inconnue")
verifier("une faute de frappe (guerier pour guerrier) : refusée par les deux compilateurs, avant de tourner", ok,
         m + " / " + py)
dire(m)

# 0.69b : les deux brèches de la 0.69, fermées
f = ecrire("hors.vtx", "fonction principal() {\n    soit t = [1, 2, 3];\n    soit i = 7;\n    afficher(t[i]);\n}\n")
c, s, e = lugus(f)
verifier("lire t[7] dans un tableau de 3 : la machine s'arrête et dit la ligne, l'indice et la longueur ; rien n'est rendu",
         c != 0 and s.strip() == "" and "ligne 4 : t[7] est hors du tableau (sa longueur : 3" in e, s + e)
dire(next((l for l in e.split("\n") if "hors du tableau" in l), "").strip()[:150])
f = ecrire("hors2.vtx", "fonction principal() {\n    soit t = tableau(3);\n    soit k = 0 - 1;\n    t[k] = 5;\n"
                        "    afficher(t[0]);\n}\n")
c, s, e = lugus(f)
verifier("écrire t[-1] : arrêtée aussi, avant d'écrire à côté du tableau", c != 0 and s.strip() == "" and "t[-1]" in e, s + e)
rp = subprocess.run([sys.executable, os.path.join(racine, "vtx128.py"), "run", os.path.join(d, "hors.vtx")],
                    capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=d,
                    env=dict(os.environ, PYTHONIOENCODING="utf-8"))
verifier("la machine de référence en Python s'arrête au même endroit, avec le même message",
         "ligne 4 : t[7] est hors du tableau (sa longueur : 3" in rp.stdout + rp.stderr, (rp.stdout + rp.stderr)[-300:])
f = ecrire("champ.vtx", "structure Sac { contenu }\nfonction principal() {\n    soit s = Sac { contenu: [1, 2] };\n"
                        "    afficher(s.contenu[5]);\n}\n")
c, s, e = lugus(f)
verifier("un tableau rangé dans le champ d'une structure : s.contenu[5] arrêté de même", c != 0 and "hors du tableau" in e,
         s + e)
d64 = subprocess.run([os.path.join(BIN, "vtx64" + X), os.path.join(d, "hors.vtx")], capture_output=True, text=True,
                     encoding="utf-8", errors="replace", cwd=d)
verifier("Dunon, la machine de 64 bits, s'arrête aussi sur t[7]", d64.returncode != 0 and "t[7] est hors du tableau"
         in d64.stdout + d64.stderr, (d64.stdout + d64.stderr)[-300:])


def instructions(*args):
    c, s, e = lugus(*args, env={"LUGUS_TEMPS": "1"})
    n = next((l.split()[0] for l in e.split("\n") if "instructions en" in l), "0")
    return c, s.strip(), int(n), e


BOUCLE = ("fonction principal() {{\n    soit t = tableau(1000);\n    pour i dans 0..{b} {{ t[i] = i * 7 % 13; }}\n"
          "    soit s = 0;\n    pour k dans 0..100 {{\n        pour i dans 0..{b} {{ s = s + t[i]; }}\n    }}\n"
          "    afficher(s);\n}}\n")
_, s1, n_verif, _ = instructions(ecrire("boucle1.vtx", BOUCLE.format(b="1000")))
# 0.70 : la machine vérifie t[i] elle-même (LDT, STT) ; l'ancienne lecture sans vérification prenait 1 115 214
# instructions pour cette boucle (0.69c, __SANS_BORNES), et 3 640 214 avec __borne
verifier(f"t[i] vérifié par la machine (LDT, STT : une instruction) : {n_verif} instructions pour cent tours d'un tableau "
         f"de 1000 cases ; sans aucune vérification, l'ancienne lecture en prenait 1115214", s1 == "600000"
         and n_verif < 1115214, f"{s1} {n_verif}")
d64b = subprocess.run([os.path.join(BIN, "vtx64" + X), os.path.join(d, "boucle1.vtx")], capture_output=True, text=True,
                      encoding="utf-8", errors="replace", cwd=d)
verifier("Dunon a les mêmes instructions (LDT, STT) et rend la même somme", d64b.stdout.strip() == "600000",
         (d64b.stdout + d64b.stderr)[-200:])
lugus("ranger", os.path.join(d, "boucle1.vtx"), "boucle1.adn")
c, s5, e = lugus("boucle1.adn", "--rapide")
verifier("--rapide n'a plus rien à retirer, et le dit", s5.strip() == "600000" and "rien à retirer" in e, e[-300:])

ok, m, py = refus("texte.vtx", "fonction principal() {\n    soit n = 3;\n    n = n + 1;\n    soit m: texte = n;\n"
                               "    afficher(m);\n}\n", "est un texte")
verifier("« soit m: texte = n » avec n un entier : refusé par les deux compilateurs (avant, la machine s'emballait)",
         ok, m + " / " + py)
dire(m)
ok, m, py = refus("texte2.vtx", "fonction titre(t: texte): texte { retour t + \"!\"; }\n"
                                "fonction principal() { afficher(titre(42)); }\n", "attend un texte")
verifier("un nombre passé là où une fonction attend un texte : refusé par les deux compilateurs", ok, m + " / " + py)
dire(m)

FREIN = """// machine : lugus
reaction freinage(v: flottant, d: flottant) -> a: flottant {
    = v * v / (2.0 * d)   -> a lourd
}
fonction bilan(s: flottant): flottant {
    retour s / 1000.0 + 0.5;
}
fonction principal() {
    soit s = 0.0;
    pour k dans 0..40000 { s = s + freinage(flottant(k % 50), 45.0); }
    afficher(bilan(s));
}
"""
f_frein = ecrire("freinage.vtx", FREIN)
lugus("ranger", f_frein, "freinage.adn")
lugus("transcrire", "freinage.adn", "freinage-rapide.arn")
f_adn = os.path.join(d, "freinage.adn")
c, juste, e = lugus(f_adn)
juste = juste.strip()
verifier(f"freinage.adn (un isotope lourd : « -> a lourd ») rangé et lancé sous la patrouille : {juste}",
         c == 0 and juste.startswith("359.83"), e[-300:])
mots_adn, mols, _t = adn.lire_adn(f_adn)
lourde = next(m for m in mols if m.isotope)
froide = next(m for m in mols if m.debut == lourde.fin)


def avarie(fichier, av, *args, **env):
    c, s, e = lugus(fichier, *args, env=dict(env, LUGUS_AVARIE=av))
    return c, s.strip(), e


# une avarie qui fausse vraiment le résultat quand personne ne veille (l'ARN lancé --rapide : ni témoins, ni patrouille)
fausse = None
for place in range(froide.debut + 1, froide.fin):
    for bit in (70, 40, 100, 6):
        av = f"100000:{place}:{bit}"
        if avarie("freinage-rapide.arn", av, "--rapide")[1] != juste:
            fausse = av
            break
    if fausse:
        break
if verifier(f"une avarie trouvée (pas:mot:bit = {fausse}) qui fausse le résultat quand personne ne veille", fausse is not None):
    _c, s_sans, _e = avarie(f_adn, fausse, LUGUS_PATROUILLE="0")
    verifier(f"la même avarie sans la patrouille (LUGUS_PATROUILLE=0) : le résultat n'est plus le bon ({s_sans})",
             s_sans != juste)
    c, s_avec, e = avarie(f_adn, fausse)
    verifier("la même avarie sous la patrouille : la molécule est réparée par ses témoins, le résultat est juste",
             c == 0 and s_avec == juste and "réparé" in e, e[-300:])
    rep = next((l for l in e.split("\n") if "réparé" in l), "")
    dire(rep.strip()[:150])
neuf = ",".join(f"100000:{i}:{b}" for i in range(froide.debut, froide.debut + 9) for b in (3, 70))
c, s, e = avarie(f_adn, neuf)
verifier("neuf mots voisins abîmés, au-delà de ce que les témoins réparent : l'apoptose, aucun résultat rendu",
         c != 0 and s == "" and "apoptose" in e, (s + e)[-300:])
dire(next((l for l in e.split("\n") if "apoptose" in l), "").strip()[:150])
c, s, e = lugus("freinage-rapide.arn", "--veille")
verifier("l'ARN coiffé est vérifié avant de servir (sa coiffe, ses témoins) : il donne le même résultat",
         c == 0 and s.strip() == juste, e[-200:])

# ================================================================================================= VIII. voir
titre("VIII. VOIR : Belenos, le val des neiges (une scène 3D en entiers : relief, soleil, ombres portées, brume)",
      "La même scène, calculée en vtx et en C, doit donner la même image au point près : son empreinte (FNV-1a sur\n"
      "les 129 600 points). Puis le temps d'une image, traduite en x86-64, face au C.")
EMPREINTE = "4817037499302952394"
banc_exe = os.path.join(d, "val_banc" + X)
r = subprocess.run([VTX, "exe128", os.path.join(racine, "belenos", "val_banc.vtx"), banc_exe], capture_output=True,
                   text=True, encoding="utf-8", errors="replace", cwd=d)
t0 = time.time()
rb = subprocess.run([banc_exe], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=d, timeout=600) \
    if r.returncode == 0 else r
t_banc = time.time() - t0
verifier(f"le banc du val (préparer le relief, 12 images, le soleil qui tourne) en .exe traduit ({t_banc:.2f} s) : "
         f"l'empreinte attendue", EMPREINTE in rb.stdout, (rb.stdout + rb.stderr)[-300:])
dire("vtx : " + (rb.stdout.strip().split("\n") + [""])[1][:150])
cc = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
if cc:
    ref = os.path.join(d, "val_ref" + X)
    rc = subprocess.run([cc, "-O2", "-o", ref, os.path.join(racine, "belenos", "val_ref.c")], capture_output=True, text=True)
    rr = subprocess.run([ref], capture_output=True, text=True, encoding="utf-8", errors="replace") if rc.returncode == 0 else rc
    verifier("la même scène écrite en C (val_ref.c, -O2) : la même empreinte, au point près", EMPREINTE in rr.stdout,
             (rr.stdout + rr.stderr)[-300:])
    dire("le C : " + rr.stderr.strip()[:150])
else:
    dire("pas de compilateur C ici : la comparaison avec val_ref.c est sautée (cc -O2 belenos/val_ref.c pour la faire)")
images = os.path.join(d, "val_images")
sc = ecrire("val.sc", "1 appui 112\n8 relache 112\n9 touche 27\n")
rt = subprocess.run([VTX, "toile128", os.path.join(racine, "belenos", "val.vtx"), "--scenario", sc, "--images", images,
                     "--pas", "1"], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=d, timeout=600)
vues = sorted(os.listdir(images)) if os.path.isdir(images) else []
verifier(f"val.vtx parcouru sans fenêtre (le soleil tourné, puis Échap) : {len(vues)} images peintes",
         rt.returncode == 0 and len(vues) == 9, (rt.stdout + rt.stderr)[-300:])

# ================================================================================================= IX. les brèches
bilan.append(tuple(chapitre))
chapitre[0] = None
titre("IX. LES BRÈCHES CONNUES : ce que l'épreuve a trouvé et qui reste à fermer (montré, pas compté)",
      "Une épreuve honnête dit aussi où le rempart est bas. Ces lignes ne comptent pas dans le bilan ; elles disent\n"
      "le prochain travail.")
print("  [..] t[i] est vérifié pour une variable, t[i][j] et s.champ[i] ; une poignée calculée (f()[i]) ne l'est pas")
print("       encore (la vérifier la calculerait deux fois). Le message nomme toujours t, pas le vrai nom du tableau.")
print("  [..] l'épreuve vaut pour les entrées données : un programme éprouvé avec d'autres entrées peut encore déborder ;")
print("       l'épissage rapide est un choix, à faire en connaissance de cause.")

# ================================================================================================= le bilan
print("\n" + "=" * 100)
print("BILAN DE L'ÉPREUVE D'ALÉSIA")
print("=" * 100)
total = sum(t for _, _, t in bilan)
reussies = sum(r for _, r, _ in bilan)
for nom, r, t in bilan:
    if nom is None:
        continue
    print(f"  {'[ok]' if r == t else '[!!]'} {nom.split(':')[0]:<16} {r}/{t}")
print(f"\n  {reussies}/{total} vérifications réussies en {time.time() - debut:.0f} s.")
print("  " + ("Tout est conforme : Vercintorix a tenu le siège." if reussies == total else
              "Des vérifications ont échoué : voir les lignes [!!] plus haut."))
shutil.rmtree(d, ignore_errors=True)
sys.exit(0 if reussies == total else 1)
