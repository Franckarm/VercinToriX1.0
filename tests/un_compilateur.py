"""0.851 : un seul compilateur (docs/vtx-un-compilateur.md). Les tests compilent par lugus (vtxc128, embarqué), plus par
vtx128.py. Ce module rassemble les gestes communs."""
import os
import subprocess
import tempfile

racine = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
X = ".exe" if os.name == "nt" else ""
LUGUS = os.path.join(racine, "vtx-rs", "target", "release", "lugus" + X)
_D = tempfile.mkdtemp(prefix="un-compilateur-")


def lire_mots(f):
    return [int(x) for x in open(f).read().split(";")[0].replace("\n", "").split(",") if x.strip()]


def compiler_fichier(fic, sortie=None):
    """(les mots de fic compilés par lugus, ou None ; le message de lugus)"""
    sortie = sortie or os.path.join(_D, os.path.basename(fic) + ".mots")
    if os.path.exists(sortie):
        os.remove(sortie)
    r = subprocess.run([LUGUS, "compiler", fic, sortie], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", stdin=subprocess.DEVNULL)
    if r.returncode != 0 or not os.path.exists(sortie):
        return None, (r.stdout + r.stderr).strip()
    return lire_mots(sortie), (r.stdout + r.stderr).strip()


def compiler_texte(src, dossier=None, nom="prog.vtx"):
    """compile un texte (écrit dans dossier, pour que ses importer s'y trouvent) : (mots ou None, message)"""
    d = dossier or _D
    f = os.path.join(d, nom)
    with open(f, "w", encoding="utf-8") as fh:
        fh.write(src)
    return compiler_fichier(f, os.path.join(_D, nom + ".mots"))


def se_compile(fic):
    """(vrai si lugus le compile, le détail) : ce qui reste de « les mêmes mots que vtx128.py »"""
    m, msg = compiler_fichier(fic)
    return m is not None, (f"{len(m)} mots" if m is not None else msg[-300:])
