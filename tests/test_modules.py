#!/usr/bin/env python3
"""Les modules promis par leur empreinte (0.61) : « importer "x.vtx" empreinte "16 chiffres hexadécimaux"; ». Les deux
compilateurs de Lugus et de Dunon calculent la même empreinte (FNV-1a de 64 bits sur les caractères, les retours chariot
sautés), comme « lugus empreinte » et « vtx64 empreinte » ; un module qui a changé est refusé, l'empreinte trouvée dite ;
la promesse ne change aucun mot ; un module promis peut en promettre un autre (la chaîne est vérifiée de bout en bout)."""
import os
import shutil
import subprocess
import sys
import tempfile

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
for p in (racine, os.path.join(racine, "spu64"), os.path.join(racine, "spu128")):
    sys.path.insert(0, p)
import vtx128  # noqa: E402
import vtx64  # noqa: E402

vtx128.COMPAT_64 = False
X = ".exe" if os.name == "nt" else ""
BIN = os.path.join(racine, "vtx-rs", "target", "release")
d = tempfile.mkdtemp()
echecs = 0


def verifier(nom, ok, detail=""):
    global echecs
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok else f" : {detail}"), flush=True)
    echecs += 0 if ok else 1


def ecrire(nom, texte, crlf=False):
    with open(os.path.join(d, nom), "w", encoding="utf-8", newline="") as f:
        f.write(texte.replace("\n", "\r\n") if crlf else texte)
    return os.path.join(d, nom)


def empreinte(machine, chemin):
    r = subprocess.run([os.path.join(BIN, machine + X), "empreinte", chemin], capture_output=True, text=True)
    return r.stdout.split()[0] if r.returncode == 0 and r.stdout else "?"


def compiler(machine, chemin):
    """(mots de la référence ou son refus, mots de vtxc ou son refus)."""
    src = open(chemin, encoding="utf-8").read()
    try:
        if machine == "lugus":
            m = vtx128.assembler(vtx128.compiler(src, dossier=d), True)[0]
        else:
            m = vtx64.assembler(vtx64.compiler(src, dossier=d))
    except vtx128.VtxError as e:
        m = "refus : " + str(e)
    except vtx64.VtxError as e:
        m = "refus : " + str(e)
    sortie = os.path.join(d, "x.mots")
    r = subprocess.run([os.path.join(BIN, machine + X), "compiler", chemin, sortie], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode == 0:
        ml = [int(x) for x in open(sortie).read().split(";")[0].split(",") if x.strip()]
    else:
        ml = "refus : " + (r.stdout + r.stderr).strip()
    return m, ml


def jouer(machine, chemin):
    r = subprocess.run([os.path.join(BIN, machine + X), chemin], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=d)
    return (r.stdout + r.stderr).strip()


OUTIL = "fonction double(x) { retour 2 * x; }\nfonction salut(): texte { retour \"Salut, Lugus !\"; }\n"
outil = ecrire("outil.vtx", OUTIL)
e = "%016x" % vtx128.empreinte_texte(open(outil, encoding="utf-8", newline="").read())
verifier("l'empreinte : vtx128.py, vtx64.py, lugus empreinte et vtx64 empreinte disent la même",
         e == "%016x" % vtx64.empreinte_texte(OUTIL) == empreinte("lugus", outil) == empreinte("vtx64", outil),
         f"{e} {empreinte('lugus', outil)} {empreinte('vtx64', outil)}")
crlf = ecrire("outil_crlf.vtx", OUTIL, crlf=True)
verifier("un module en \\r\\n a la même empreinte que le même en \\n", empreinte("lugus", crlf) == e)

ouvrage = ecrire("ouvrage.vtx", f'importer "outil.vtx" empreinte "{e}";\nfonction quadruple(x) {{ retour double(double(x)); }}\n',
                 crlf=True)
ea = empreinte("lugus", ouvrage)
PROMIS = ecrire("promis.vtx", f'importer "ouvrage.vtx" empreinte "{ea.upper()}";\n'
                              f'importer "outil.vtx" empreinte "{e}";\n'
                              "fonction principal() { afficher(salut(), quadruple(5)); }\n")
LIBRE = ecrire("libre.vtx", 'importer "outil.vtx";\nfonction quadruple(x) { retour double(double(x)); }\n'
                            "fonction principal() { afficher(salut(), quadruple(5)); }\n")
# le même programme, ses modules non promis : les mêmes mots que le programme promis (la promesse n'en change aucun)
LIBRE2 = ecrire("libre2.vtx", 'importer "ouvrage_libre.vtx";\nimporter "outil.vtx";\n'
                              "fonction principal() { afficher(salut(), quadruple(5)); }\n")
ecrire("ouvrage_libre.vtx", 'importer "outil.vtx";\nfonction quadruple(x) { retour double(double(x)); }\n')
for machine, nom_m in (("lugus", "Lugus"), ("vtx64", "Dunon")):
    mp, mlp = compiler(machine, PROMIS)
    ml_, mll = compiler(machine, LIBRE2)
    verifier(f"{nom_m} : un module promis, puis le module qu'il promet : les deux compilateurs, les mêmes mots, et les "
             "mêmes que sans promesse", isinstance(mp, list) and mp == mlp == ml_ == mll, f"{str(mp)[:120]} / {str(mlp)[:120]}")
    verifier(f"{nom_m} : le programme promis tourne", jouer(machine, PROMIS) == "Salut, Lugus ! 20", jouer(machine, PROMIS))

# le module change : une lettre de plus
ecrire("outil.vtx", OUTIL.replace("2 * x", "2 * x + 0"))
nouvelle = empreinte("lugus", outil)
for machine, nom_m in (("lugus", "Lugus"), ("vtx64", "Dunon")):
    mp, mlp = compiler(machine, PROMIS)
    ok = (isinstance(mp, str) and isinstance(mlp, str) and "n'est plus celui promis" in mp and "n'est plus celui promis" in mlp
          and nouvelle in mp and nouvelle in mlp and e in mp and e in mlp)
    verifier(f"{nom_m} : le module a changé (ouvrage.vtx le promettait) : refusé par les deux compilateurs, l'empreinte "
             "trouvée dite", ok, f"{mp[:200]} / {mlp[:200]}")
    ml_, mll = compiler(machine, LIBRE)
    verifier(f"{nom_m} : sans promesse, le module changé est pris tel quel (comme avant)",
             isinstance(ml_, list) and ml_ == mll and jouer(machine, LIBRE) == "Salut, Lugus ! 20", str(ml_)[:200])
    ma, mla = compiler(machine, LIBRE2)
    verifier(f"{nom_m} : par un module qui ne promet rien, le module changé passe aussi",
             isinstance(ma, list) and ma == mla, str(ma)[:200])
# un module promis absent : dit introuvable ; une promesse mal écrite n'est pas une ligne d'import
os.remove(outil)
for machine, nom_m in (("lugus", "Lugus"), ("vtx64", "Dunon")):
    mp, mlp = compiler(machine, PROMIS)
    verifier(f"{nom_m} : un module promis absent : introuvable, pour les deux",
             isinstance(mp, str) and "introuvable" in mp and isinstance(mlp, str) and "introuvable" in mlp, f"{mp} / {mlp}")

shutil.rmtree(d, ignore_errors=True)
print("les modules promis : " + ("tout est conforme" if echecs == 0 else f"{echecs} écart(s)"))
sys.exit(1 if echecs else 0)
