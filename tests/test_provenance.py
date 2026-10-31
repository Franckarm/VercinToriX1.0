#!/usr/bin/env python3
"""La provenance (docs/vtx-reactions.md, étape 5) : « vtx128.py pourquoi » remonte chaque liaison jusqu'aux constantes et
aux entrées, avec sa dernière valeur, son unité, le nombre de réactions (et, pour un atome à souvenir, combien de fois
il a vraiment réagi), et dit quand une branche n'a pas réagi. Compilée sans provenance, une réaction garde ses mots.

    python3 tests/test_provenance.py"""
import os
import subprocess
import sys

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, racine)
import vtx128  # noqa: E402

echecs = []


def verifier(nom, ok, detail=""):
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok or not detail else " : " + detail), flush=True)
    if not ok:
        echecs.append(nom)


def pourquoi(fichier, *args):
    r = subprocess.run([sys.executable, os.path.join(racine, "vtx128.py"), "pourquoi", fichier] + list(args),
                       capture_output=True, text=True, encoding="utf-8")
    return r.stdout + r.stderr


ex = lambda f: os.path.join(racine, "exemples128", f)  # noqa: E731
t = pourquoi(ex("panel.vtx"))
lignes = [l.strip() for l in t.splitlines()]
verifier("le panel : r2 = 42 vient du pont, de la garde, du rendez-vous, du produit de 6 et 7",
         any(l.startswith("r2 = 42   ← rangement : pont r vers @2[0]") for l in lignes)
         and any(l.startswith("p = 42   ← produit : a × b") for l in lignes)
         and any(l.startswith("a = 6   ← six : 6") for l in lignes) and "[vu plus haut]" in t, t)
t = pourquoi(ex("chute.vtx"))
verifier("la chute : les valeurs avec leurs unités (t en s, g en m/s², 2 km = 2000 m)",
         "t = 2.01927510938461 s   ← racine(carre)" in t and "g = 9.81 m/s²   ← une entrée de la réaction chute" in t
         and "aller = 2000 m   ← 2 km" in t, t)
t = pourquoi(ex("scene_incrementale.vtx"), "scene.fond")
verifier("la scène : le souvenir du décor a réagi 6 fois sur 60 appels", "souvenir : réagi 6 fois sur 60 appels" in t, t)
src = os.path.join(racine, "tests", "_provenance_si.vtx")
open(src, "w", encoding="utf-8").write("""reaction garde(x) -> r {
    = x × 3                  -> t
    = si t > 10 alors t - 10 -> r
}
fonction principal() { sortie(garde(2)); }
""")
t = pourquoi(src)
os.remove(src)
verifier("une branche qui n'a pas réagi : « porte faux », avec la valeur calculée",
         "r porte faux (sa branche n'a pas réagi" in t and "t = 6   ← x × 3" in t, t)
vtx128.COMPAT_64 = False
panel = open(ex("panel.vtx"), encoding="utf-8").read()
avant = vtx128.assembler(vtx128.compiler(panel))
vtx128.PROVENANCE = True
avec = vtx128.assembler(vtx128.compiler(panel))
vtx128.PROVENANCE = False
verifier("sans la provenance, les mêmes mots ; avec, la trace en plus", vtx128.assembler(vtx128.compiler(panel)) == avant
         and len(avec) > len(avant))
print("provenance : " + ("tout est conforme" if not echecs else f"{len(echecs)} échec(s)"))
sys.exit(1 if echecs else 0)
