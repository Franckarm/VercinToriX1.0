#!/usr/bin/env python3
"""Taranis : une boucle vtx « en segments » devient un noyau SPIR-V pour la carte graphique (un fil par tour de boucle).

Le sens est celui de Lugus et de la forge : un entier est un mot de 64 bits (calculé dans le noyau en deux mots de 32
bits : les retenues, le produit étendu, la division longue ; toutes les cartes savent le faire, et SwiftShader, le
Vulkan logiciel de la machine de travail, aussi : chaque noyau se vérifie avant de partir) (les opérations de Lugus à la largeur 64 ;
la division par zéro rend le plus grand entier, le reste par zéro rend le dividende) ; la mémoire est l'étage 2, vue
par une fenêtre de mots de 64 bits ; un accès hors de la fenêtre lève un drapeau, et le programme rejoue la boucle sur
le processeur (comme un cylindre rejoue) : le résultat est toujours celui de Lugus.

Ce que le noyau sait faire (sinon : PasPourLaCarte, et la boucle reste aux cylindres) : des entiers (le type entier),
les opérations + - * / % & | ^ << >> (et ./ .% .>> signées), les comparaisons (et .< .<= .> .>=), && || non, les
variables, soit, l'affectation, si / sinon, tantque, pour (au pas constant), les appels de fonctions vtx (recopiés dans
le noyau ; leur « retour » à la fin seulement), @2[adresse] en lecture et en écriture dans le corps de la boucle (une
adresse qui ne dépend que de la variable de boucle et de variables d'avant la boucle : la fenêtre se calcule).

Interface du noyau : liaison 0 = la fenêtre (mots de 64 bits) ; liaison 1 = les paramètres (mots de 64 bits) :
p[0] le drapeau (0 : tout va bien), p[1] le début de la boucle, p[2] le nombre de tours, p[3] la première adresse de la
fenêtre (dans l'étage), p[4] sa longueur, p[5] le nombre de fils d'une rangée de groupes, p[6...] les variables d'avant
la boucle que le corps lit."""
import os
import struct
import sys

ici = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ici)
from spirv import texte  # noqa: E402

OP = {
    "Capability": 17, "MemoryModel": 14, "EntryPoint": 15, "ExecutionMode": 16, "Decorate": 71, "MemberDecorate": 72,
    "TypeVoid": 19, "TypeBool": 20, "TypeInt": 21, "TypeVector": 23, "TypeRuntimeArray": 29, "TypeStruct": 30,
    "TypePointer": 32, "TypeFunction": 33, "Constant": 43, "Function": 54, "FunctionEnd": 56, "Variable": 59,
    "Load": 61, "Store": 62, "AccessChain": 65, "CompositeExtract": 81, "UConvert": 113, "IAdd": 128, "ISub": 130,
    "IMul": 132, "UDiv": 134, "SDiv": 135, "UMod": 137, "SRem": 138, "LogicalOr": 166, "LogicalAnd": 167,
    "LogicalNot": 168, "Select": 169, "IEqual": 170, "INotEqual": 171, "UGreaterThan": 172, "SGreaterThan": 173,
    "UGreaterThanEqual": 174, "SGreaterThanEqual": 175, "ULessThan": 176, "SLessThan": 177, "ULessThanEqual": 178,
    "SLessThanEqual": 179, "ShiftRightLogical": 194, "ShiftRightArithmetic": 195, "ShiftLeftLogical": 196,
    "BitwiseOr": 197, "BitwiseXor": 198, "BitwiseAnd": 199, "Not": 200, "Phi": 245, "LoopMerge": 246,
    "SelectionMerge": 247, "Label": 248, "Branch": 249, "BranchConditional": 250, "Return": 253,
    "LogicalNotEqual": 165, "UMulExtended": 151, "CompositeConstruct": 80,
}
M64 = (1 << 64) - 1
MASQUE62 = (1 << 62) - 1
LARGEUR = 64
CMP = {"==": "IEqual", "!=": "INotEqual", "<": "ULessThan", "<=": "ULessThanEqual", ">": "UGreaterThan",
       ">=": "UGreaterThanEqual", ".<": "SLessThan", ".<=": "SLessThanEqual", ".>": "SGreaterThan",
       ".>=": "SGreaterThanEqual"}
SIMPLES = {"+": "IAdd", "-": "ISub", "*": "IMul", "&": "BitwiseAnd", "|": "BitwiseOr", "^": "BitwiseXor"}
DECALAGES = {"<<": "ShiftLeftLogical", ">>": "ShiftRightLogical", ".>>": "ShiftRightArithmetic"}


class PasPourLaCarte(Exception):
    pass


def libres(st, vus=None):
    """les variables lues par un morceau d'arbre"""
    vus = set() if vus is None else vus
    if isinstance(st, tuple):
        if len(st) >= 2 and st[0] == "var" and isinstance(st[1], str):
            vus.add(st[1])
        for x in st:
            libres(x, vus)
    elif isinstance(st, list):
        for x in st:
            libres(x, vus)
    return vus


def declarees(corps, acc=None):
    """les variables déclarées dans un corps (soit, pour)"""
    acc = set() if acc is None else acc
    for s in corps:
        if not isinstance(s, tuple):
            continue
        if s[0] == "soit":
            acc.add(s[1])
        elif s[0] == "pour":
            acc.add(s[1])
            declarees(s[4], acc)
        elif s[0] == "si":
            declarees(s[2], acc)
            if s[3]:
                declarees(s[3], acc)
        elif s[0] == "tantque":
            declarees(s[2], acc)
        elif s[0] == "bloc":
            declarees(s[1], acc)
    return acc


def acces_memoire(st, acc):
    """les lectures et écritures de la mémoire dans un morceau d'arbre : (genre, étage, adresse)"""
    if isinstance(st, tuple):
        if st and st[0] == "lire":
            acc.append(("L", st[1], st[2]))
        elif st and st[0] == "ecrire":
            acc.append(("E", st[1], st[2]))
        elif st and st[0] in ("ecrire_champ", "champ_ref"):
            acc.append(("?", None, None))
        for x in st:
            acces_memoire(x, acc)
    elif isinstance(st, list):
        for x in st:
            acces_memoire(x, acc)
    return acc


class Noyau:
    """Une valeur entière du noyau est une paire (bas, haut) d'identifiants SPIR-V de mots de 32 bits."""

    def __init__(self, forge, var, corps):
        self.fo = forge
        self.var, self.corps = var, corps
        self.prochain = 1
        self.tete, self.decor, self.types, self.vars_decl, self.code = [], [], [], [], []
        self.consts = {}
        self.portees = []          # la pile des portées : {nom vtx: (variable du bas, variable du haut)}
        self.pile_appels = []
        self.bloc = None           # l'étiquette du bloc courant

    # ------------------------------------------------------------ l'écriture
    def id(self):
        self.prochain += 1
        return self.prochain - 1

    @staticmethod
    def i(liste, op, *mots):
        liste.append(((len(mots) + 1) << 16) | OP[op])
        liste.extend(mots)

    def e(self, op, *mots):
        self.i(self.code, op, *mots)

    def v(self, op, *args, t=None):
        r = self.id()
        self.e(op, self.t32 if t is None else t, r, *args)
        return r

    def b(self, op, *args):
        return self.v(op, *args, t=self.tbool)

    def c32(self, v):
        v &= 0xFFFFFFFF
        k = ("u", v)
        if k not in self.consts:
            self.consts[k] = self.id()
            self.i(self.types, "Constant", self.t32, self.consts[k], v)
        return self.consts[k]

    def cst(self, v):
        v &= M64
        return (self.c32(v & 0xFFFFFFFF), self.c32(v >> 32))

    def etiquette(self, lab):
        self.e("Label", lab)
        self.bloc = lab

    def aller(self, lab):
        self.e("Branch", lab)

    # ------------------------------------------------------------ l'arithmétique sur 64 bits, en deux mots
    def sel(self, c, x, y):
        return (self.v("Select", c, x[0], y[0]), self.v("Select", c, x[1], y[1]))

    def bits(self, op, x, y):
        return (self.v(op, x[0], y[0]), self.v(op, x[1], y[1]))

    def add(self, x, y):
        lo = self.v("IAdd", x[0], y[0])
        retenue = self.v("Select", self.b("ULessThan", lo, x[0]), self.c32(1), self.c32(0))
        return (lo, self.v("IAdd", self.v("IAdd", x[1], y[1]), retenue))

    def sub(self, x, y):
        lo = self.v("ISub", x[0], y[0])
        emprunt = self.v("Select", self.b("ULessThan", x[0], y[0]), self.c32(1), self.c32(0))
        return (lo, self.v("ISub", self.v("ISub", x[1], y[1]), emprunt))

    def mul(self, x, y):
        r = self.v("UMulExtended", x[0], y[0], t=self.tpaire)
        lo = self.v("CompositeExtract", r, 0)
        h = self.v("CompositeExtract", r, 1)
        h = self.v("IAdd", h, self.v("IMul", x[0], y[1]))
        h = self.v("IAdd", h, self.v("IMul", x[1], y[0]))
        return (lo, h)

    def eq(self, x, y):
        return self.b("LogicalAnd", self.b("IEqual", x[0], y[0]), self.b("IEqual", x[1], y[1]))

    def ult(self, x, y, signe=False):
        haut = self.b("SLessThan" if signe else "ULessThan", x[1], y[1])
        meme = self.b("IEqual", x[1], y[1])
        return self.b("LogicalOr", haut, self.b("LogicalAnd", meme, self.b("ULessThan", x[0], y[0])))

    def comparer(self, op, x, y):
        if op == "==":
            return self.eq(x, y)
        if op == "!=":
            return self.b("LogicalNot", self.eq(x, y))
        signe = op.startswith(".")
        o = op[1:] if signe else op
        if o == "<":
            return self.ult(x, y, signe)
        if o == ">":
            return self.ult(y, x, signe)
        if o == "<=":
            return self.b("LogicalNot", self.ult(y, x, signe))
        return self.b("LogicalNot", self.ult(x, y, signe))

    def decaler(self, op, x, n):
        """x décalé de n & 63 (op : <<, >>, .>>)"""
        s = self.v("BitwiseAnd", n[0], self.c32(63))
        s5 = self.v("BitwiseAnd", s, self.c32(31))
        grand = self.b("UGreaterThanEqual", s, self.c32(32))
        nul = self.b("IEqual", s5, self.c32(0))
        comp = self.v("BitwiseAnd", self.v("ISub", self.c32(32), s5), self.c32(31))
        if op == "<<":
            lo_p = self.v("ShiftLeftLogical", x[0], s5)
            fuite = self.v("Select", nul, self.c32(0), self.v("ShiftRightLogical", x[0], comp))
            hi_p = self.v("BitwiseOr", self.v("ShiftLeftLogical", x[1], s5), fuite)
            return (self.v("Select", grand, self.c32(0), lo_p), self.v("Select", grand, self.v("ShiftLeftLogical", x[0], s5), hi_p))
        arith = op == ".>>"
        dr = "ShiftRightArithmetic" if arith else "ShiftRightLogical"
        hi_p = self.v(dr, x[1], s5)
        fuite = self.v("Select", nul, self.c32(0), self.v("ShiftLeftLogical", x[1], comp))
        lo_p = self.v("BitwiseOr", self.v("ShiftRightLogical", x[0], s5), fuite)
        signe = self.v("ShiftRightArithmetic", x[1], self.c32(31)) if arith else self.c32(0)
        return (self.v("Select", grand, hi_p, lo_p), self.v("Select", grand, signe, hi_p))

    def neg(self, x):
        return self.sub(self.cst(0), x)

    def divmod_u(self, a, b):
        """la division longue (64 tours) : (quotient, reste) ; b non nul"""
        qv, rv, kv = self.locale(), self.locale(), self.var32()
        self.ranger(qv, self.cst(0))
        self.ranger(rv, self.cst(0))
        self.e("Store", kv, self.c32(63))
        tete, test, dedans, suite, fin = self.id(), self.id(), self.id(), self.id(), self.id()
        self.aller(tete)
        self.etiquette(tete)
        self.e("LoopMerge", fin, suite, 0)
        self.aller(test)
        self.etiquette(test)
        k = self.v("Load", kv)
        self.e("BranchConditional", self.b("SLessThanEqual", self.c32(0), k), dedans, fin)
        self.etiquette(dedans)
        r = self.charger(rv)
        bit = self.v("BitwiseAnd", self.decaler(">>", a, (k, self.c32(0)))[0], self.c32(1))
        r = self.decaler("<<", r, self.cst(1))
        r = (self.v("BitwiseOr", r[0], bit), r[1])
        assez = self.b("LogicalNot", self.ult(r, b))
        r = self.sel(assez, self.sub(r, b), r)
        q = self.charger(qv)
        un = self.decaler("<<", self.cst(1), (k, self.c32(0)))
        q = self.sel(assez, self.bits("BitwiseOr", q, un), q)
        self.ranger(rv, r)
        self.ranger(qv, q)
        self.aller(suite)
        self.etiquette(suite)
        self.e("Store", kv, self.v("ISub", self.v("Load", kv), self.c32(1)))
        self.aller(tete)
        self.etiquette(fin)
        return self.charger(qv), self.charger(rv)

    # ------------------------------------------------------------ les variables (deux mots de 32 bits chacune)
    def var32(self):
        v = self.id()
        self.i(self.vars_decl, "Variable", self.tpf, v, 7)
        return v

    def locale(self):
        return (self.var32(), self.var32())

    def ranger(self, var, x):
        self.e("Store", var[0], x[0])
        self.e("Store", var[1], x[1])

    def charger(self, var):
        return (self.v("Load", var[0]), self.v("Load", var[1]))

    def nouvelle(self, nom):
        v = self.locale()
        self.portees[-1][nom] = v
        return v

    def cherche(self, nom):
        v = self.portees[-1].get(nom)
        if v is None:
            raise PasPourLaCarte(f"variable « {nom} » inconnue du noyau")
        return v

    def verifier_type(self, e):
        t = self.fo.typ(e)
        if t != "e":
            raise PasPourLaCarte(f"type {t} : le noyau ne connaît que l'entier")

    # ------------------------------------------------------------ la mémoire : la fenêtre, deux mots de 32 bits par mot
    def acces(self, adr):
        court = (adr[0], self.v("BitwiseAnd", adr[1], self.c32(0x3FFFFFFF)))
        idx = self.sub(court, self.base)
        dedans = self.ult(idx, self.longueur)
        return self.v("ShiftLeftLogical", idx[0], self.c32(1)), dedans

    def case(self, tampon, k):
        return self.v("AccessChain", tampon, self.c32(0), k, t=self.tpu)

    def drapeau(self):
        self.e("Store", self.case(self.parametres, self.c32(0)), self.c32(1))

    def lire(self, et, adr):
        if et != 2:
            raise PasPourLaCarte("une lecture hors de l'étage 2")
        k, dedans = self.acces(self.expr(adr))
        oui, non, fin = self.id(), self.id(), self.id()
        self.e("SelectionMerge", fin, 0)
        self.e("BranchConditional", dedans, oui, non)
        self.etiquette(oui)
        lo = self.v("Load", self.case(self.fenetre, k))
        hi = self.v("Load", self.case(self.fenetre, self.v("IAdd", k, self.c32(1))))
        b_oui = self.bloc
        self.aller(fin)
        self.etiquette(non)
        self.drapeau()
        b_non = self.bloc
        self.aller(fin)
        self.etiquette(fin)
        return (self.v("Phi", lo, b_oui, self.c32(0), b_non), self.v("Phi", hi, b_oui, self.c32(0), b_non))

    def ecrire(self, et, adr, valeur):
        if et != 2:
            raise PasPourLaCarte("une écriture hors de l'étage 2")
        a = self.expr(adr)
        x = self.expr(valeur)
        k, dedans = self.acces(a)
        oui, non, fin = self.id(), self.id(), self.id()
        self.e("SelectionMerge", fin, 0)
        self.e("BranchConditional", dedans, oui, non)
        self.etiquette(oui)
        self.e("Store", self.case(self.fenetre, k), x[0])
        self.e("Store", self.case(self.fenetre, self.v("IAdd", k, self.c32(1))), x[1])
        self.aller(fin)
        self.etiquette(non)
        self.drapeau()
        self.aller(fin)
        self.etiquette(fin)

    # ------------------------------------------------------------ les expressions
    def booleen(self, e):
        """une condition : un booléen SPIR-V"""
        if e[0] == "bin" and e[1] in ("&&", "||"):
            if self.contient_appel(e):
                raise PasPourLaCarte("&& ou || autour d'un appel (le court-circuit)")
            a, b = self.booleen(e[2]), self.booleen(e[3])
            return self.b("LogicalAnd" if e[1] == "&&" else "LogicalOr", a, b)
        if e[0] == "non_log":
            return self.b("LogicalNot", self.booleen(e[1]))
        if e[0] == "bin" and e[1] in CMP:
            for x in (e[2], e[3]):
                self.verifier_type(x)
            return self.comparer(e[1], self.expr(e[2]), self.expr(e[3]))
        self.verifier_type(e)
        return self.b("LogicalNot", self.eq(self.expr(e), self.cst(0)))

    @staticmethod
    def contient_appel(e):
        if isinstance(e, tuple):
            if e and e[0] in ("appel", "lire"):
                return True
            return any(Noyau.contient_appel(x) for x in e)
        if isinstance(e, list):
            return any(Noyau.contient_appel(x) for x in e)
        return False

    def expr(self, e):
        g = e[0]
        if g in ("nombre", "inombre"):
            return self.cst(e[1])
        if g == "var":
            return self.charger(self.cherche(e[1]))
        if g == "lire":
            return self.lire(e[1], e[2])
        if g == "appel":
            return self.appel(e)
        if g == "non_log" or (g == "bin" and (e[1] in CMP or e[1] in ("&&", "||"))):
            return self.sel(self.booleen(e), self.cst(1), self.cst(0))
        if g == "non":
            self.verifier_type(e[1])
            x = self.expr(e[1])
            return (self.v("Not", x[0]), self.v("Not", x[1]))
        if g == "bin":
            self.verifier_type(e)
            op = e[1]
            a, b = self.expr(e[2]), self.expr(e[3])
            if op == "+":
                return self.add(a, b)
            if op == "-":
                return self.sub(a, b)
            if op == "*":
                return self.mul(a, b)
            if op in ("&", "|", "^"):
                return self.bits({"&": "BitwiseAnd", "|": "BitwiseOr", "^": "BitwiseXor"}[op], a, b)
            if op in ("<<", ">>", ".>>"):
                return self.decaler(op, a, b)
            zero = self.eq(b, self.cst(0))
            if op in ("/", "%"):
                q, r = self.divmod_u(a, self.sel(zero, self.cst(1), b))
                return self.sel(zero, self.cst(M64) if op == "/" else a, q if op == "/" else r)
            if op in ("./", ".%"):
                moins1 = self.eq(b, self.cst(M64))
                special = self.b("LogicalOr", zero, moins1)
                na = self.b("SLessThan", a[1], self.c32(0))
                nb = self.b("SLessThan", b[1], self.c32(0))
                b1 = self.sel(special, self.cst(1), b)
                aa = self.sel(na, self.neg(a), a)
                bb = self.sel(nb, self.neg(b1), b1)
                q, r = self.divmod_u(aa, bb)
                if op == "./":
                    q = self.sel(self.b("LogicalNotEqual", na, nb), self.neg(q), q)
                    q = self.sel(moins1, self.neg(a), q)
                    return self.sel(zero, self.cst(M64), q)
                r = self.sel(na, self.neg(r), r)
                r = self.sel(moins1, self.cst(0), r)
                return self.sel(zero, a, r)
            raise PasPourLaCarte(f"l'opération « {op} »")
        raise PasPourLaCarte(f"l'expression « {g} »")

    # ------------------------------------------------------------ les appels : la fonction recopiée dans le noyau
    def appel(self, e):
        nom, args = e[1], e[2]
        f = self.fo.fonctions.get(nom)
        if f is None:
            raise PasPourLaCarte(f"« {nom} » n'est pas une fonction vtx du programme")
        if nom in self.pile_appels:
            raise PasPourLaCarte(f"« {nom} » s'appelle elle-même")
        if len(args) != len(f.params) or any(t != "e" for t in f.ptypes) or f.rtype != "e":
            raise PasPourLaCarte(f"« {nom} » : des paramètres ou un retour qui ne sont pas des entiers")
        corps = list(f.corps)
        fin = None
        if corps and corps[-1][0] == "retour":
            fin = corps.pop()
        if any(x[0] == "retour" for x in self.instructions(corps)):
            raise PasPourLaCarte(f"« {nom} » : un retour avant la fin")
        if acces_memoire(corps, []) or (fin and acces_memoire(fin, [])):
            raise PasPourLaCarte(f"« {nom} » touche la mémoire (seul le corps de la boucle y a droit)")
        valeurs = [self.expr(a) for a in args]
        vtypes = self.types_de(f)
        if any(t != "e" for t in vtypes.values()):
            raise PasPourLaCarte(f"« {nom} » a des variables qui ne sont pas des entiers")
        ancien = self.fo.vtypes
        self.fo.vtypes = vtypes
        self.portees.append({})
        self.pile_appels.append(nom)
        try:
            for p, v in zip(f.params, valeurs):
                self.ranger(self.nouvelle(p), v)
            for s in corps:
                self.instr(s)
            r = self.expr(fin[1]) if fin is not None and len(fin) > 1 and fin[1] is not None else self.cst(0)
        finally:
            self.pile_appels.pop()
            self.portees.pop()
            self.fo.vtypes = ancien
        return r

    def instructions(self, corps):
        for s in corps:
            if not isinstance(s, tuple):
                continue
            yield s
            for k in (2, 3, 4):
                if len(s) > k and isinstance(s[k], list):
                    yield from self.instructions(s[k])
            if s[0] == "bloc":
                yield from self.instructions(s[1])

    def types_de(self, f):
        """les types des variables d'une fonction, comme Generateur.fonction les trouve"""
        sauve = self.fo.vtypes
        vt = dict(zip(f.params, f.ptypes))
        self.fo.vtypes = vt
        try:
            loc = []
            self.fo.locales(f.corps, loc)
            for nom, _l, kind, st in loc:
                if kind == "pour":
                    vt[nom] = "e" if st[0] == "pour" else "?"
                else:
                    vt[nom] = st[4] if len(st) > 4 and st[4] else self.fo.typ(st[2])
        finally:
            self.fo.vtypes = sauve
        return vt

    # ------------------------------------------------------------ les instructions
    def instr(self, s):
        g = s[0]
        if g == "soit":
            if len(s) > 4 and s[4] not in (None, "e"):
                raise PasPourLaCarte(f"« {s[1]} » n'est pas un entier")
            self.verifier_type(s[2])
            v = self.expr(s[2])
            var = self.portees[-1].get(s[1]) or self.nouvelle(s[1])
            self.ranger(var, v)
        elif g == "affecter":
            self.verifier_type(s[2])
            self.ranger(self.cherche(s[1]), self.expr(s[2]))
        elif g == "ecrire":
            self.ecrire(s[1], s[2], s[3])
        elif g == "expr":
            if s[1][0] != "appel":
                raise PasPourLaCarte("une expression seule")
            self.expr(s[1])
        elif g == "si":
            c = self.booleen(s[1])
            oui, fin = self.id(), self.id()
            non = self.id() if s[3] else fin
            self.e("SelectionMerge", fin, 0)
            self.e("BranchConditional", c, oui, non)
            self.etiquette(oui)
            for x in s[2]:
                self.instr(x)
            self.aller(fin)
            if s[3]:
                self.etiquette(non)
                for x in s[3]:
                    self.instr(x)
                self.aller(fin)
            self.etiquette(fin)
        elif g in ("tantque", "pour"):
            if g == "pour":
                if len(s) < 6 or not isinstance(s[4], list):
                    raise PasPourLaCarte("une boucle « pour » sur un tableau")
                var = self.portees[-1].get(s[1]) or self.nouvelle(s[1])
                self.verifier_type(s[2])
                self.ranger(var, self.expr(s[2]))
                corps = s[4]
                cond = ("bin", "<", ("var", s[1], s[5]), s[3])
            else:
                corps, cond = s[2], s[1]
            tete, test, dedans, suite, fin = self.id(), self.id(), self.id(), self.id(), self.id()
            self.aller(tete)
            self.etiquette(tete)
            self.e("LoopMerge", fin, suite, 0)
            self.aller(test)
            self.etiquette(test)
            c = self.booleen(cond)
            self.e("BranchConditional", c, dedans, fin)
            self.etiquette(dedans)
            for x in corps:
                self.instr(x)
            self.aller(suite)
            self.etiquette(suite)
            if g == "pour":
                pas = s[6] if len(s) > 6 else 1
                self.ranger(var, self.add(self.charger(var), self.cst(pas)))
            self.aller(tete)
            self.etiquette(fin)
        elif g == "bloc":
            if len(s) > 2 and s[2] is not None:
                raise PasPourLaCarte("un bloc particulier (chaque, vague, souvenirs)")
            for x in s[1]:
                self.instr(x)
        else:
            raise PasPourLaCarte(f"l'instruction « {g} »")

    # ------------------------------------------------------------ le module
    def compiler(self):
        """-> (les mots SPIR-V, les variables d'avant la boucle lues par le corps, les accès du corps)"""
        acces = acces_memoire(self.corps, [])
        if any(k == "?" for k, _, _ in acces):
            raise PasPourLaCarte("les champs de structure")
        interieur = declarees(self.corps) | {self.var}
        dehors = sorted(libres(self.corps) - interieur)
        for nom in dehors + [self.var]:
            if self.fo.vtypes.get(nom, "e") != "e":
                raise PasPourLaCarte(f"« {nom} » n'est pas un entier")
        for _k, et, adr in acces:
            if libres(adr) & (interieur - {self.var}):
                raise PasPourLaCarte("une adresse qui dépend d'une variable du corps (la fenêtre ne se calcule pas)")
            if et != 2:
                raise PasPourLaCarte("un accès hors de l'étage 2")
            if self.contient_appel(adr):
                raise PasPourLaCarte("une adresse qui lit la mémoire ou appelle une fonction")
        I = self.i
        principal, gid = self.id(), self.id()
        self.t_void, t_fn, self.tbool, self.t32 = self.id(), self.id(), self.id(), self.id()
        self.tpaire, t_v3, t_pv3 = self.id(), self.id(), self.id()
        t_tab, t_bloc, t_pbloc, self.tpu, self.tpf = self.id(), self.id(), self.id(), self.id(), self.id()
        self.fenetre, self.parametres = self.id(), self.id()
        I(self.tete, "Capability", 1)
        I(self.tete, "MemoryModel", 0, 1)
        I(self.tete, "EntryPoint", 5, principal, *texte("main"), gid)
        I(self.tete, "ExecutionMode", principal, 17, LARGEUR, 1, 1)
        I(self.decor, "Decorate", gid, 11, 28)
        I(self.decor, "Decorate", t_tab, 6, 4)
        I(self.decor, "MemberDecorate", t_bloc, 0, 35, 0)
        I(self.decor, "Decorate", t_bloc, 3)
        I(self.decor, "Decorate", self.fenetre, 34, 0)
        I(self.decor, "Decorate", self.fenetre, 33, 0)
        I(self.decor, "Decorate", self.parametres, 34, 0)
        I(self.decor, "Decorate", self.parametres, 33, 1)
        I(self.types, "TypeVoid", self.t_void)
        I(self.types, "TypeFunction", t_fn, self.t_void)
        I(self.types, "TypeBool", self.tbool)
        I(self.types, "TypeInt", self.t32, 32, 0)
        I(self.types, "TypeStruct", self.tpaire, self.t32, self.t32)
        I(self.types, "TypeVector", t_v3, self.t32, 3)
        I(self.types, "TypePointer", t_pv3, 1, t_v3)
        I(self.types, "TypeRuntimeArray", t_tab, self.t32)
        I(self.types, "TypeStruct", t_bloc, t_tab)
        I(self.types, "TypePointer", t_pbloc, 2, t_bloc)
        I(self.types, "TypePointer", self.tpu, 2, self.t32)
        I(self.types, "TypePointer", self.tpf, 7, self.t32)
        I(self.types, "Variable", t_pv3, gid, 1)
        I(self.types, "Variable", t_pbloc, self.fenetre, 2)
        I(self.types, "Variable", t_pbloc, self.parametres, 2)

        entree = self.id()
        self.portees.append({})

        def param(k):
            return (self.v("Load", self.case(self.parametres, self.c32(2 * k))),
                    self.v("Load", self.case(self.parametres, self.c32(2 * k + 1))))

        self.bloc = entree
        v3 = self.v("Load", gid, t=t_v3)
        gx = self.v("CompositeExtract", v3, 0)
        gy = self.v("CompositeExtract", v3, 1)
        idx = (self.v("IAdd", gx, self.v("IMul", gy, param(5)[0])), self.c32(0))
        n = param(2)
        dans = self.ult(idx, n)
        travail, fin = self.id(), self.id()
        self.e("SelectionMerge", fin, 0)
        self.e("BranchConditional", dans, travail, fin)
        self.etiquette(travail)
        self.base, self.longueur = param(3), param(4)
        self.ranger(self.nouvelle(self.var), self.add(param(1), idx))
        for k, nom in enumerate(dehors):
            self.ranger(self.nouvelle(nom), param(6 + k))
        for s in self.corps:
            self.instr(s)
        self.aller(fin)
        self.etiquette(fin)
        self.e("Return")
        corps = self.code
        self.code = []
        self.i(self.code, "Function", self.t_void, principal, 0, t_fn)
        self.i(self.code, "Label", entree)
        mots = [0x07230203, 0x00010000, 0, self.prochain, 0] + self.tete + self.decor + self.types + self.code \
            + self.vars_decl + corps
        mots.append((1 << 16) | OP["FunctionEnd"])
        return struct.pack("<%dI" % len(mots), *mots), dehors, acces
