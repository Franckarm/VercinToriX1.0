#!/usr/bin/env python3
"""Les quatre valeurs aux bords du monde sur Dunon, le SPU-64 (0.6h) : de_preuves, vers_logique, lire_logique,
nombre_su, fichier_present, temoins, les mêmes que sur Lugus. Mêmes mots par vtx64.py et vtxc64 ; chaque cas comme
attendu ; exemples64/bords_du_monde.vtx au clavier écrit sur Dunon exactement ce que le même programme écrit sur Lugus."""
import os
import subprocess
import sys
import tempfile

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, racine)
import vtx64  # noqa: E402

X = ".exe" if os.name == "nt" else ""
BIN = os.path.join(racine, "vtx-rs", "target", "release")
d = tempfile.mkdtemp()
echecs = 0


def verifier(nom, ok, detail=""):
    global echecs
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok else f" : {detail}"), flush=True)
    echecs += 0 if ok else 1


def memes_mots(fic):
    src = open(fic, encoding="utf-8").read()
    ref = vtx64.assembler(vtx64.compiler(src, dossier=os.path.dirname(fic)))
    sortie = os.path.join(d, os.path.basename(fic) + ".mots")
    r = subprocess.run([os.path.join(BIN, "vtx64" + X), "compiler", fic, sortie], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    m = [int(x) for x in open(sortie).read().split(";")[0].split(",") if x.strip()] if r.returncode == 0 else None
    return m == ref, f"{len(ref)} contre {None if m is None else len(m)} {r.stdout[-200:]} {r.stderr[-200:]}"


def jouer(fic, entree):
    return subprocess.run([os.path.join(BIN, "vtx64" + X), fic], input=entree, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", cwd=d, timeout=120).stdout


def sur_lugus(fic, entree):
    # le même programme, en exécutable de Lugus (c'est lui qui lit le clavier)
    e = os.path.join(d, "lugus_" + os.path.splitext(os.path.basename(fic))[0] + X)
    if not os.path.exists(e):
        subprocess.run([os.path.join(BIN, "vtx" + X), "exe128", fic, e], capture_output=True)
    env = dict(os.environ, VTX_SANS_PAUSE="1", VTX_CONSOLE="1")
    return subprocess.run([e], input=entree, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          cwd=d, env=env, timeout=120).stdout


cas = os.path.join(d, "cas.vtx")
open(cas, "w", encoding="utf-8").write("""// machine : dunon
fonction principal() {
    afficher(de_preuves(0, 0), de_preuves(3, 0), de_preuves(0, 2), de_preuves(1, 1));
    afficher(vers_logique(" Oui "), vers_logique("NON"), vers_logique(""), vers_logique("les deux"), vers_logique("peut-être"),
             vers_logique("o"), vers_logique("0"), vers_logique("oui et non"));
    afficher(nombre_su("42"), nombre_su("-7"), nombre_su("4x2"), nombre_su("   "), nombre_su("+"), nombre_su(" 12 "));
    afficher(fichier_present("cas.vtx"), fichier_present("absent.txt"));
    afficher(temoins([0, 2, 0]), temoins([1, 1]), temoins([]), temoins([2, 1]), temoins([0, 3]), temoins([0, 0]));
    afficher(lire_logique(), lire_logique(), lire_logique(), lire_logique(), lire_logique());
}
""")
ok, detail = memes_mots(cas)
verifier("vtx64.py et vtxc64 donnent les mêmes mots (les cas)", ok, detail)
o = jouer(cas, "oui\n\nles deux\nnon\n").splitlines()
attendu = ["inconnu vrai faux variable",
           "vrai faux inconnu variable inconnu vrai faux variable",
           "vrai vrai faux inconnu faux vrai",
           "vrai faux",
           "vrai faux inconnu variable variable inconnu",
           "vrai inconnu variable faux inconnu"]
noms = ["de_preuves : aucune, des oui, des non, les deux", "vers_logique : oui, non, rien, les deux, incompris",
        "nombre_su : un nombre, un signe, autre chose, rien", "fichier_present : là, absent",
        "temoins : la fusion d'un tableau de réponses", "lire_logique : au clavier, la fin de l'entrée reste inconnue"]
for i, (n, a) in enumerate(zip(noms, attendu)):
    verifier(n, i < len(o) and o[i] == a, f"{o[i] if i < len(o) else None!r} attendu {a!r}")

demo = os.path.join(racine, "exemples64", "bords_du_monde.vtx")
ok, detail = memes_mots(demo)
verifier("bords_du_monde : mêmes mots par les deux compilateurs", ok, detail)
for reponses, sait in (("oui\n\nnon\n", "variable"), ("oui\noui\n\n", "vrai"), ("\n\n\n", "inconnu"), ("non\nn\nfaux\n", "faux")):
    a = jouer(demo, reponses)
    b = sur_lugus(demo, reponses)
    verifier(f"bords_du_monde, réponses {reponses.split(chr(10))[:3]} : le conseil sait {sait} ; Dunon écrit comme Lugus",
             a == b and f"ce que le conseil sait : {sait}" in a and "lus : 4 ; total : 21 ; vides (inconnus) : 1" in a,
             a[-400:])
print("les quatre valeurs aux bords du monde, sur Dunon : " + ("tout est conforme" if echecs == 0 else f"{echecs} échec(s)"))
sys.exit(1 if echecs else 0)
