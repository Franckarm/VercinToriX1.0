"""0.849 : presenter_cube(f) (le service 34) : l'image d'un cube de l'étage 2 posée à l'étage 1 et présentée, son
empreinte rendue ; la même sur Lugus, en « dunon; », sur Dunon, et forgée ; les mêmes mots par les deux compilateurs.

    python3 tests/test_presenter_cube.py"""
import os
import subprocess
import sys
import tempfile

ICI = os.path.dirname(os.path.abspath(__file__))
R = os.path.dirname(ICI)
REL = os.path.join(R, "vtx-rs", "target", "release")
EXE = ".exe" if os.name == "nt" else ""
echecs = []


def verifier(nom, ok, detail=""):
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok or not detail else " : " + str(detail)[:400]), flush=True)
    if not ok:
        echecs.append(nom)


src = open(os.path.join(ICI, "presenter_cube", "image.vtx"), encoding="utf-8").read()
empreintes = set()
with tempfile.TemporaryDirectory() as d:
    for nom, texte, machine, outil in (("Lugus", src, "lugus", "memes_mots128.py"),
                                       ("Lugus en dunon;", "dunon;\n" + src, "lugus", "memes_mots128.py"),
                                       ("Dunon", src.replace("// machine : lugus", "// machine : dunon"), "vtx64",
                                        "memes_mots64.py")):
        f = os.path.join(d, "image.vtx")
        open(f, "w", encoding="utf-8").write(texte)
        r = subprocess.run([os.path.join(REL, machine + EXE), f], capture_output=True, text=True)
        l = [x for x in r.stdout.strip().split("\n") if x]
        verifier(f"{nom} : l'empreinte rendue est celle de l'image posée à l'étage 1", len(l) == 2 and l[0] == "1",
                 r.stdout + r.stderr)
        if len(l) == 2:
            empreintes.add(int(l[1]) % (1 << 64))
        m = subprocess.run([sys.executable, os.path.join(R, "outils", outil), f], capture_output=True, text=True)
        verifier(f"{nom} : les mêmes mots par les deux compilateurs", "MEMES" in m.stdout, m.stdout + m.stderr)
    for nom, texte in (("forgé", src), ("forgé en dunon;", "dunon;\n" + src)):
        f = os.path.join(d, "image_f.vtx")
        open(f, "w", encoding="utf-8").write(texte)
        exe = os.path.join(d, "image_f" + EXE)
        fo = subprocess.run([sys.executable, os.path.join(R, "forge", "forge128.py"), f, "-o", exe], capture_output=True,
                            text=True)
        r = subprocess.run([exe], capture_output=True, text=True) if fo.returncode == 0 else None
        l = [x for x in r.stdout.strip().split("\n") if x] if r else []
        verifier(f"{nom} : la même empreinte", len(l) == 2 and l[0] == "1", fo.stderr[-300:] if r is None else r.stdout)
        if len(l) == 2:
            empreintes.add(int(l[1]) % (1 << 64))
verifier("une seule empreinte partout", len(empreintes) == 1, empreintes)
print("presenter_cube : tout est conforme" if not echecs else f"{len(echecs)} échec(s)")
sys.exit(1 if echecs else 0)
