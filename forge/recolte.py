#!/usr/bin/env python3
"""Récolte les programmes (et leurs entrées) que les tests de vtx.py exécutent sur la machine Python : de quoi
confronter la forge aux mêmes cas. Utilisation : python3 forge/recolte.py SORTIE.json test_types.py …"""
import sys, os, runpy, io, contextlib, json
racine = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, racine); sys.path.insert(0, os.path.join(racine, "tests"))
import vtx
dernier = [None]
par_mots = {}            # les mots d'un programme compilé -> sa source (les tests compilent tout, puis exécutent)
orig_cc = vtx.compiler_complet
def cc(src, prelude=True, optim=True, dossier=None, nom="programme", partition=True, melange=None):
    dernier[0] = (src, dossier) if prelude else None
    return orig_cc(src, prelude, optim, dossier, nom, partition, melange)
vtx.compiler_complet = cc
orig_as = vtx.assembler
def asm(texte):
    m = orig_as(texte)
    if dernier[0] is not None:
        par_mots[tuple(m)] = dernier[0]
    return m
vtx.assembler = asm
orig_ch = vtx.CPU.charger
def charger(self, mots):
    self._source = par_mots.get(tuple(mots))
    return orig_ch(self, mots)
vtx.CPU.charger = charger
vus, recolte = set(), []
orig_ex = vtx.CPU.executer
def ex(self, max_pas=5_000_000):
    s = getattr(self, "_source", None)
    if s is not None and self.dossier_fichiers is None:
        cle = (s[0], tuple(self.entree))
        if cle not in vus and len(recolte) < 4000:
            vus.add(cle); recolte.append((s[0], list(self.entree), s[1], nom_test))
    return orig_ex(self, max_pas)
vtx.CPU.executer = ex
# les tests chargent vtx.py par importlib (un module à eux) : on leur rend le module surveillé
import importlib.util, importlib.abc
_spec = importlib.util.spec_from_file_location
class _Chargeur(importlib.abc.Loader):
    def create_module(self, spec):
        return vtx
    def exec_module(self, module):
        pass
def _spec_vtx(nom, chemin, *a, **k):
    if nom == "vtx":
        return importlib.util.spec_from_loader("vtx", _Chargeur())
    return _spec(nom, chemin, *a, **k)
importlib.util.spec_from_file_location = _spec_vtx
for nom_test in sys.argv[2:]:
    n0 = len(recolte)
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            runpy.run_path(os.path.join(racine, "tests", nom_test), run_name="__main__")
    except SystemExit:
        pass
    except Exception as e:
        print(nom_test, "exception", e, file=sys.stderr)
    print(nom_test, len(recolte) - n0, file=sys.stderr)
json.dump(recolte, open(sys.argv[1], "w"))
