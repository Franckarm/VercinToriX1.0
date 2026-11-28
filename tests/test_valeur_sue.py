"""0.848 : la valeur sue. « selon » sur un entier (la réponse d'un service) : -1 inconnu, -2 faux, -3 variable, toute
autre valeur vrai, et dans la branche vrai la variable est la valeur. Les mêmes mots par les deux compilateurs de Lugus
(en 128 et en « dunon; ») et de Dunon, la même sortie ; un « selon » sur un logique garde ses mots d'avant.

    python3 tests/test_valeur_sue.py"""
import os
import subprocess
import sys
import tempfile

ICI = os.path.dirname(os.path.abspath(__file__))
R = os.path.dirname(ICI)
REL = os.path.join(R, "vtx-rs", "target", "release")
EXE = ".exe" if os.name == "nt" else ""
echecs = []
ATTENDU = ["vrai 5", "inconnu : pas de fichier", "variable -3", "logique vrai"]


def verifier(nom, ok, detail=""):
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok or not detail else " : " + str(detail)[:400]), flush=True)
    if not ok:
        echecs.append(nom)


src = open(os.path.join(ICI, "valeur_sue", "sue.vtx"), encoding="utf-8").read()
with tempfile.TemporaryDirectory() as d:
    for nom, texte, machine, outil in (("Lugus", src, "lugus", "memes_mots128.py"),
                                       ("Lugus en dunon;", "dunon;\n" + src, "lugus", "memes_mots128.py"),
                                       ("Dunon", src.replace("// machine : lugus", "// machine : dunon"), "vtx64",
                                        "memes_mots64.py")):
        f = os.path.join(d, "sue.vtx")
        open(f, "w", encoding="utf-8").write(texte)
        r = subprocess.run([os.path.join(REL, machine + EXE), f], capture_output=True, text=True)
        sortie = [l for l in r.stdout.strip().split("\n") if l]
        verifier(f"{nom} : la sortie attendue", sortie == ATTENDU, r.stdout + r.stderr)
        # 0.858a : un seul compilateur par machine (vtx64.py retiré) : plus de « mêmes mots »
    # la forge : le même résultat que Lugus (en 128 et en « dunon; »)
    for nom, texte in (("forgé", src), ("forgé en dunon;", "dunon;\n" + src)):
        f = os.path.join(d, "sue_forge.vtx")
        open(f, "w", encoding="utf-8").write(texte)
        exe = os.path.join(d, "sue_forge" + EXE)
        fo = subprocess.run([sys.executable, os.path.join(R, "forge", "forge128.py"), f, "-o", exe], capture_output=True,
                            text=True)
        r = subprocess.run([exe], capture_output=True, text=True) if fo.returncode == 0 else None
        verifier(f"{nom} : la sortie attendue", r is not None and [l for l in r.stdout.strip().split("\n") if l] == ATTENDU,
                 fo.stderr[-300:] if r is None else r.stdout + r.stderr)
print("La valeur sue : tout est conforme" if not echecs else f"{len(echecs)} échec(s)")
sys.exit(1 if echecs else 0)
