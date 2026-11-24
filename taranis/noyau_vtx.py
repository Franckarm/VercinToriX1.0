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

0.816 : le mode « pages » (la carte du vergobret sur la carte graphique), quand la fenêtre ne se calcule pas : le
noyau lit et écrit tout l'étage 2 par une table des pages (liaison 2 : pour chaque page p < 65536, sa place + 1 dans
le tampon des pages, 0 : absente) ; les adresses peuvent dépendre de tout, les fonctions appelées lire la mémoire, et
un « retour » se trouver n'importe où (changé en un drapeau : la fonction finit, ses boucles s'arrêtent). La promesse
est vérifiée sur la carte : chaque mot écrit garde l'auteur de son écriture (liaison 4 : le tour + 1, échangé d'un
coup) ; deux tours qui écrivent le même mot : drapeau 2 ; une page absente : drapeau 1 ; chaque page note qu'elle a
été lue ou écrite (liaison 3), et une page à la fois lue et écrite fait rejouer la boucle au processeur. Liaison 0 =
les pages (mots de 64 bits), liaison 1 = les paramètres (p[0] le drapeau, p[1] le début, p[2] le nombre de tours,
p[5] le nombre de fils d'une rangée, p[6...] les variables d'avant la boucle).

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
    "LogicalNotEqual": 165, "UMulExtended": 151, "SMulExtended": 152, "SConvert": 114, "CompositeConstruct": 80, "AtomicExchange": 229,
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


def sans_retours(corps, fini, rv):
    """0.816 : un corps de fonction sans « retour » avant la fin : « retour e » devient rv = e ; fini = 1 ; ce qui suit un
    morceau qui a pu finir ne se fait que si fini == 0 ; une boucle qui contient un retour s'arrête dès fini == 1.
    -> (le nouveau corps, s'il a pu finir)"""
    pas_fini = ("bin", "==", ("var", fini, 0), ("nombre", 0))

    def instr(s):
        g = s[0]
        if g == "retour":
            e = s[1] if len(s) > 1 and s[1] is not None else ("nombre", 0)
            return [("affecter", rv, e, 0), ("affecter", fini, ("nombre", 1), 0)], True
        if g == "si":
            a, ra = liste(s[2])
            b, rb = liste(s[3]) if s[3] else (s[3], False)
            return [("si", s[1], a, b) + tuple(s[4:])], ra or rb
        if g == "tantque":
            c, r = liste(s[2])
            if r:
                return [("tantque_fini", s[1], c, fini)], True
            return [s], False
        if g == "pour" and len(s) > 4 and isinstance(s[4], list):
            c, r = liste(s[4])
            if r:
                return [s[:4] + ([("si", pas_fini, c, None, 0)],) + s[5:]], True
            return [s], False
        if g == "bloc":
            c, r = liste(s[1])
            return [("bloc", c) + tuple(s[2:])], r
        return [s], False

    def liste(stmts):
        out = []
        for k, st in enumerate(stmts):
            if not isinstance(st, tuple):
                out.append(st)
                continue
            n, r = instr(st)
            out.extend(n)
            if r:
                reste = stmts[k + 1:]
                if reste:
                    rr, _ = liste(reste)
                    out.append(("si", pas_fini, rr, None, 0))
                return out, True
        return out, False

    return liste(list(corps))


class Noyau:
    """Une valeur entière du noyau est une paire (bas, haut) d'identifiants SPIR-V de mots de 32 bits."""

    def __init__(self, forge, var, corps, pages=False):
        self.fo = forge
        self.var, self.corps = var, corps
        self.pages = pages         # 0.816 : la mémoire par la table des pages
        self.nappels = 0
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
        try:
            t = self.fo.typ(e)
        except Exception as x:
            raise PasPourLaCarte(f"un type que le noyau ne sait pas lire ({x})")
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

    def acces_page(self, adr):
        """0.816 : (l'indice du mot bas dans le tampon des pages, la page est-elle là, la place de la page)"""
        hi16 = self.v("BitwiseAnd", adr[1], self.c32(0xFFFF))
        petit = self.b("IEqual", hi16, self.c32(0))
        pg = self.v("Select", petit, self.v("ShiftRightLogical", adr[0], self.c32(16)), self.c32(0))
        place1 = self.v("Load", self.case(self.table, pg))
        dedans = self.b("LogicalAnd", petit, self.b("INotEqual", place1, self.c32(0)))
        place = self.v("ISub", self.v("Select", dedans, place1, self.c32(1)), self.c32(1))
        mot = self.v("IAdd", self.v("ShiftLeftLogical", place, self.c32(16)), self.v("BitwiseAnd", adr[0], self.c32(0xFFFF)))
        # la demande d'une page absente : marques[p3 + page] (p3 : après les marques des pages) ; une adresse hors de la
        # table : la case 65536 de la demande
        dem = self.v("IAdd", self.demandes, self.v("Select", petit, pg, self.c32(65536)))
        self.derniere_demande = dem
        return mot, dedans, place

    def marquer_lue(self, place):
        """0.817 : la marque « page lue », écrite seulement quand la page change (la dernière lue est gardée par le fil) :
        tous les fils écrivaient sans cesse les mêmes mots, la carte les faisait passer un par un"""
        autre = self.b("INotEqual", place, self.v("Load", self.derniere))
        oui, fin = self.id(), self.id()
        self.e("SelectionMerge", fin, 0)
        self.e("BranchConditional", autre, oui, fin)
        self.etiquette(oui)
        self.e("Store", self.case(self.marques, self.v("ShiftLeftLogical", place, self.c32(1))), self.c32(1))
        self.e("Store", self.derniere, place)
        self.aller(fin)
        self.etiquette(fin)

    def drapeau_n(self, n):
        self.e("Store", self.case(self.parametres, self.c32(0)), self.c32(n))

    def lire_page(self, adr):
        mot, dedans, place = self.acces_page(self.expr(adr))
        oui, non, fin = self.id(), self.id(), self.id()
        self.e("SelectionMerge", fin, 0)
        self.e("BranchConditional", dedans, oui, non)
        self.etiquette(oui)
        k = self.v("ShiftLeftLogical", mot, self.c32(1))
        lo = self.v("Load", self.case(self.fenetre, k))
        hi = self.v("Load", self.case(self.fenetre, self.v("IAdd", k, self.c32(1))))
        self.marquer_lue(place)
        b_oui = self.bloc
        self.aller(fin)
        self.etiquette(non)
        self.drapeau_n(1)
        self.e("Store", self.case(self.marques, self.derniere_demande), self.c32(1))
        b_non = self.bloc
        self.aller(fin)
        self.etiquette(fin)
        return (self.v("Phi", lo, b_oui, self.c32(0), b_non), self.v("Phi", hi, b_oui, self.c32(0), b_non))

    def ecrire_page(self, adr, valeur):
        a = self.expr(adr)
        x = self.expr(valeur)
        mot, dedans, place = self.acces_page(a)
        oui, non, fin, conflit, apres = self.id(), self.id(), self.id(), self.id(), self.id()
        self.e("SelectionMerge", fin, 0)
        self.e("BranchConditional", dedans, oui, non)
        self.etiquette(oui)
        ancien = self.v("AtomicExchange", self.case(self.auteurs, mot), self.c32(1), self.c32(0), self.moi)
        autre = self.b("LogicalAnd", self.b("INotEqual", ancien, self.c32(0)), self.b("INotEqual", ancien, self.moi))
        self.e("SelectionMerge", apres, 0)
        self.e("BranchConditional", autre, conflit, apres)
        self.etiquette(conflit)
        self.drapeau_n(2)
        self.aller(apres)
        self.etiquette(apres)
        k = self.v("ShiftLeftLogical", mot, self.c32(1))
        self.e("Store", self.case(self.fenetre, k), x[0])
        self.e("Store", self.case(self.fenetre, self.v("IAdd", k, self.c32(1))), x[1])
        self.e("Store", self.case(self.marques, self.v("IAdd", self.v("ShiftLeftLogical", place, self.c32(1)), self.c32(1))),
               self.c32(1))
        self.aller(fin)
        self.etiquette(non)
        self.drapeau_n(1)
        self.e("Store", self.case(self.marques, self.derniere_demande), self.c32(1))
        self.aller(fin)
        self.etiquette(fin)

    def lire(self, et, adr):
        if et != 2:
            raise PasPourLaCarte("une lecture hors de l'étage 2")
        if self.pages:
            return self.lire_page(adr)
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
        if self.pages:
            return self.ecrire_page(adr, valeur)
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
            return self.pas(self.expr(e[1]))
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
            if op in ("/", "%", "./", ".%"):
                return self.diviser(op, a, b)
            raise PasPourLaCarte(f"l'opération « {op} »")
        raise PasPourLaCarte(f"l'expression « {g} »")

    def pas(self, x):
        return (self.v("Not", x[0]), self.v("Not", x[1]))

    def negatif(self, x):
        return self.b("SLessThan", x[1], self.c32(0))

    def diviser(self, op, a, b):
        """/ % ./ .% au sens de Lugus (par zéro : le plus grand entier, ou le dividende)"""
        zero = self.eq(b, self.cst(0))
        if op in ("/", "%"):
            q, r = self.divmod_u(a, self.sel(zero, self.cst(1), b))
            return self.sel(zero, self.cst(M64) if op == "/" else a, q if op == "/" else r)
        if op in ("./", ".%"):
            moins1 = self.eq(b, self.cst(M64))
            special = self.b("LogicalOr", zero, moins1)
            na = self.negatif(a)
            nb = self.negatif(b)
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
        fini = rv = None
        if corps and corps[-1][0] == "retour":
            fin = corps.pop()
        if any(x[0] == "retour" for x in self.instructions(corps)):
            if not self.pages:
                raise PasPourLaCarte(f"« {nom} » : un retour avant la fin")
            # 0.816 : les retours au milieu changés en un drapeau
            self.nappels += 1
            fini, rv = f"__fini{self.nappels}", f"__rv{self.nappels}"
            if fin is not None:
                corps.append(fin)
            corps, _ = sans_retours(corps, fini, rv)
            fin = ("retour", ("var", rv, 0))
        if not self.pages and (acces_memoire(corps, []) or (fin and acces_memoire(fin, []))):
            raise PasPourLaCarte(f"« {nom} » touche la mémoire (seul le corps de la boucle y a droit)")
        valeurs = [self.expr(a) for a in args]
        vtypes = self.types_de(f)
        if fini is not None:
            vtypes[fini] = vtypes[rv] = "e"
        if any(t != "e" for t in vtypes.values()):
            raise PasPourLaCarte(f"« {nom} » a des variables qui ne sont pas des entiers")
        ancien = self.fo.vtypes
        self.fo.vtypes = vtypes
        self.portees.append({})
        self.pile_appels.append(nom)
        try:
            for p, v in zip(f.params, valeurs):
                self.ranger(self.nouvelle(p), v)
            if fini is not None:
                self.ranger(self.nouvelle(fini), self.cst(0))
                self.ranger(self.nouvelle(rv), self.cst(0))
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
        # 0.818 : locales se souvient des corps de boucle déjà vus (les segments d'une boucle partagent un corps) ; ici,
        # la fonction est relue en entier : ce souvenir repart de zéro le temps de la lecture
        vus = self.fo.__dict__.get("_corps_vus")
        self.fo._corps_vus = set()
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
            if vus is None:
                del self.fo._corps_vus
            else:
                self.fo._corps_vus = vus
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
        elif g == "tantque_fini":
            # 0.816 : une boucle qui s'arrête aussi quand la fonction a fini (son retour)
            tete, test, dedans, suite, fin = self.id(), self.id(), self.id(), self.id(), self.id()
            self.aller(tete)
            self.etiquette(tete)
            self.e("LoopMerge", fin, suite, 0)
            self.aller(test)
            self.etiquette(test)
            c = self.booleen(s[1])
            pas_fini = self.eq(self.charger(self.cherche(s[3])), self.cst(0))
            self.e("BranchConditional", self.b("LogicalAnd", c, pas_fini), dedans, fin)
            self.etiquette(dedans)
            for x in s[2]:
                self.instr(x)
            self.aller(suite)
            self.etiquette(suite)
            self.aller(tete)
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
            if et != 2:
                raise PasPourLaCarte("un accès hors de l'étage 2")
            if self.pages:
                continue
            if libres(adr) & (interieur - {self.var}):
                raise PasPourLaCarte("une adresse qui dépend d'une variable du corps (la fenêtre ne se calcule pas)")
            if self.contient_appel(adr):
                raise PasPourLaCarte("une adresse qui lit la mémoire ou appelle une fonction")
        I = self.i
        principal, gid = self.id(), self.id()
        self.t_void, t_fn, self.tbool, self.t32 = self.id(), self.id(), self.id(), self.id()
        self.tpaire, t_v3, t_pv3 = self.id(), self.id(), self.id()
        t_tab, t_bloc, t_pbloc, self.tpu, self.tpf = self.id(), self.id(), self.id(), self.id(), self.id()
        self.fenetre, self.parametres = self.id(), self.id()
        self.table, self.marques, self.auteurs = self.id(), self.id(), self.id()
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
        if self.pages:
            for k, t in ((2, self.table), (3, self.marques), (4, self.auteurs)):
                I(self.decor, "Decorate", t, 34, 0)
                I(self.decor, "Decorate", t, 33, k)
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
        if self.pages:
            for t in (self.table, self.marques, self.auteurs):
                I(self.types, "Variable", t_pbloc, t, 2)

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
        self.demandes = param(3)[0]
        # 0.816 : l'auteur d'une écriture : le tour + 1 (sur 31 bits)
        self.moi = self.v("IAdd", self.v("BitwiseAnd", idx[0], self.c32(0x7FFFFFFF)), self.c32(1))
        # 0.817 : la dernière page lue par ce fil
        self.derniere = self.var32()
        self.e("Store", self.derniere, self.c32(0xFFFFFFFF))
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
        if self.pages:
            # l'interface du noyau : toutes les variables globales nommées par le point d'entrée n'est pas exigé en
            # SPIR-V 1.0 (seules les entrées et sorties) ; rien à ajouter
            pass
        mots = [0x07230203, 0x00010000, 0, self.prochain, 0] + self.tete + self.decor + self.types + self.code \
            + self.vars_decl + corps
        mots.append((1 << 16) | OP["FunctionEnd"])
        return struct.pack("<%dI" % len(mots), *mots), dehors, acces


class NoyauI64(Noyau):
    """0.817 : le mode pages en entiers de 64 bits de la carte (la capacité Int64 : la carte et son pilote font les
    opérations de 64 bits, au lieu des deux mots de 32 bits de Noyau ; une division est une instruction, et non plus 64
    tours de boucle). Une valeur est un seul identifiant SPIR-V. Le sens reste celui de Lugus (les mêmes mots)."""

    def __init__(self, forge, var, corps, rapide=False):
        super().__init__(forge, var, corps, pages=True)
        # 0.820 : l'épissage rapide (le modèle classique) : la promesse n'est pas vérifiée sur la carte (pas d'auteur
        # échangé à chaque mot écrit) ; le programme répond de ses écritures, comme sur toute carte graphique
        self.rapide = rapide

    # ------------------------------------------------------------ les nombres de 64 bits
    def v64(self, op, *args):
        return self.v(op, *args, t=self.t64)

    def cst(self, v):
        v &= M64
        k = ("q", v)
        if k not in self.consts:
            self.consts[k] = self.id()
            self.i(self.types, "Constant", self.t64, self.consts[k], v & 0xFFFFFFFF, v >> 32)
        return self.consts[k]

    def sel(self, c, x, y):
        return self.v64("Select", c, x, y)

    def bits(self, op, x, y):
        return self.v64(op, x, y)

    def add(self, x, y):
        return self.v64("IAdd", x, y)

    def sub(self, x, y):
        return self.v64("ISub", x, y)

    def mul(self, x, y):
        return self.v64("IMul", x, y)

    def eq(self, x, y):
        return self.b("IEqual", x, y)

    def ult(self, x, y, signe=False):
        return self.b("SLessThan" if signe else "ULessThan", x, y)

    def decaler(self, op, x, n):
        s = self.v64("BitwiseAnd", n, self.cst(63))
        return self.v64({"<<": "ShiftLeftLogical", ">>": "ShiftRightLogical", ".>>": "ShiftRightArithmetic"}[op], x, s)

    def pas(self, x):
        return self.v64("Not", x)

    def negatif(self, x):
        return self.b("SLessThan", x, self.cst(0))

    def diviser(self, op, a, b):
        zero = self.eq(b, self.cst(0))
        if op in ("/", "%"):
            bb = self.sel(zero, self.cst(1), b)
            if op == "/":
                return self.sel(zero, self.cst(M64), self.v64("UDiv", a, bb))
            return self.sel(zero, a, self.v64("UMod", a, bb))
        moins1 = self.eq(b, self.cst(M64))
        special = self.b("LogicalOr", zero, moins1)
        bb = self.sel(special, self.cst(1), b)
        if op == "./":
            q = self.sel(moins1, self.neg(a), self.v64("SDiv", a, bb))
            return self.sel(zero, self.cst(M64), q)
        r = self.sel(moins1, self.cst(0), self.v64("SRem", a, bb))
        return self.sel(zero, a, r)

    # ------------------------------------------------------------ les variables
    def locale(self):
        v = self.id()
        self.i(self.vars_decl, "Variable", self.tpf64, v, 7)
        return v

    def ranger(self, var, x):
        self.e("Store", var, x)

    def charger(self, var):
        return self.v64("Load", var)

    # ------------------------------------------------------------ la mémoire par la table des pages
    def case64(self, tampon, k):
        return self.v("AccessChain", tampon, self.c32(0), k, t=self.tp64)

    def moities(self, x):
        lo = self.v("UConvert", x)
        hi = self.v("UConvert", self.v64("ShiftRightLogical", x, self.cst(32)))
        return (lo, hi)

    def drapeau_n(self, n):
        self.e("Store", self.case64(self.parametres, self.c32(0)), self.cst(n))

    def lire_page(self, adr):
        mot, dedans, place = self.acces_page(self.moities(self.expr(adr)))
        oui, non, fin = self.id(), self.id(), self.id()
        self.e("SelectionMerge", fin, 0)
        self.e("BranchConditional", dedans, oui, non)
        self.etiquette(oui)
        x = self.v64("Load", self.case64(self.fenetre, mot))
        self.marquer_lue(place)
        b_oui = self.bloc
        self.aller(fin)
        self.etiquette(non)
        self.drapeau_n(1)
        self.e("Store", self.case(self.marques, self.derniere_demande), self.c32(1))
        b_non = self.bloc
        self.aller(fin)
        self.etiquette(fin)
        return self.v64("Phi", x, b_oui, self.cst(0), b_non)

    def ecrire_page(self, adr, valeur):
        a = self.expr(adr)
        x = self.expr(valeur)
        mot, dedans, place = self.acces_page(self.moities(a))
        oui, non, fin, conflit, apres = self.id(), self.id(), self.id(), self.id(), self.id()
        self.e("SelectionMerge", fin, 0)
        self.e("BranchConditional", dedans, oui, non)
        self.etiquette(oui)
        if not self.rapide:
            ancien = self.v("AtomicExchange", self.case(self.auteurs, mot), self.c32(1), self.c32(0), self.moi)
            autre = self.b("LogicalAnd", self.b("INotEqual", ancien, self.c32(0)), self.b("INotEqual", ancien, self.moi))
            self.e("SelectionMerge", apres, 0)
            self.e("BranchConditional", autre, conflit, apres)
            self.etiquette(conflit)
            self.drapeau_n(2)
            self.aller(apres)
            self.etiquette(apres)
        self.e("Store", self.case64(self.fenetre, mot), x)
        self.e("Store", self.case(self.marques, self.v("IAdd", self.v("ShiftLeftLogical", place, self.c32(1)), self.c32(1))),
               self.c32(1))
        self.aller(fin)
        self.etiquette(non)
        self.drapeau_n(1)
        self.e("Store", self.case(self.marques, self.derniere_demande), self.c32(1))
        self.aller(fin)
        self.etiquette(fin)

    # ------------------------------------------------------------ le module
    def compiler(self):
        acces = acces_memoire(self.corps, [])
        if any(k == "?" for k, _, _ in acces):
            raise PasPourLaCarte("les champs de structure")
        interieur = declarees(self.corps) | {self.var}
        dehors = sorted(libres(self.corps) - interieur)
        for nom in dehors + [self.var]:
            if self.fo.vtypes.get(nom, "e") != "e":
                raise PasPourLaCarte(f"« {nom} » n'est pas un entier")
        for _k, et, _adr in acces:
            if et != 2:
                raise PasPourLaCarte("un accès hors de l'étage 2")
        I = self.i
        principal, gid = self.id(), self.id()
        self.t_void, t_fn, self.tbool, self.t32 = self.id(), self.id(), self.id(), self.id()
        self.t64 = self.id()
        self.tpaire, t_v3, t_pv3 = self.id(), self.id(), self.id()
        t_tab, t_bloc, t_pbloc, self.tpu, self.tpf = self.id(), self.id(), self.id(), self.id(), self.id()
        t_tab64, t_bloc64, t_pbloc64, self.tp64, self.tpf64 = self.id(), self.id(), self.id(), self.id(), self.id()
        self.fenetre, self.parametres = self.id(), self.id()
        self.table, self.marques, self.auteurs = self.id(), self.id(), self.id()
        I(self.tete, "Capability", 1)
        I(self.tete, "Capability", 11)       # Int64
        I(self.tete, "MemoryModel", 0, 1)
        I(self.tete, "EntryPoint", 5, principal, *texte("main"), gid)
        I(self.tete, "ExecutionMode", principal, 17, LARGEUR, 1, 1)
        I(self.decor, "Decorate", gid, 11, 28)
        I(self.decor, "Decorate", t_tab, 6, 4)
        I(self.decor, "MemberDecorate", t_bloc, 0, 35, 0)
        I(self.decor, "Decorate", t_bloc, 3)
        I(self.decor, "Decorate", t_tab64, 6, 8)
        I(self.decor, "MemberDecorate", t_bloc64, 0, 35, 0)
        I(self.decor, "Decorate", t_bloc64, 3)
        for k, t in ((0, self.fenetre), (1, self.parametres), (2, self.table), (3, self.marques), (4, self.auteurs)):
            I(self.decor, "Decorate", t, 34, 0)
            I(self.decor, "Decorate", t, 33, k)
        I(self.types, "TypeVoid", self.t_void)
        I(self.types, "TypeFunction", t_fn, self.t_void)
        I(self.types, "TypeBool", self.tbool)
        I(self.types, "TypeInt", self.t32, 32, 0)
        I(self.types, "TypeInt", self.t64, 64, 0)
        I(self.types, "TypeStruct", self.tpaire, self.t32, self.t32)
        I(self.types, "TypeVector", t_v3, self.t32, 3)
        I(self.types, "TypePointer", t_pv3, 1, t_v3)
        I(self.types, "TypeRuntimeArray", t_tab, self.t32)
        I(self.types, "TypeStruct", t_bloc, t_tab)
        I(self.types, "TypePointer", t_pbloc, 2, t_bloc)
        I(self.types, "TypePointer", self.tpu, 2, self.t32)
        I(self.types, "TypePointer", self.tpf, 7, self.t32)
        I(self.types, "TypeRuntimeArray", t_tab64, self.t64)
        I(self.types, "TypeStruct", t_bloc64, t_tab64)
        I(self.types, "TypePointer", t_pbloc64, 2, t_bloc64)
        I(self.types, "TypePointer", self.tp64, 2, self.t64)
        I(self.types, "TypePointer", self.tpf64, 7, self.t64)
        I(self.types, "Variable", t_pv3, gid, 1)
        I(self.types, "Variable", t_pbloc64, self.fenetre, 2)
        I(self.types, "Variable", t_pbloc64, self.parametres, 2)
        for t in (self.table, self.marques, self.auteurs):
            I(self.types, "Variable", t_pbloc, t, 2)

        entree = self.id()
        self.portees.append({})

        def param(k):
            # 0.824 : chaque noyau d'un lot lit ses paramètres dans sa région (64 mots)
            return self.v64("Load", self.case64(self.parametres, self.c32(getattr(self, "region", 0) * 64 + k)))

        self.bloc = entree
        v3 = self.v("Load", gid, t=t_v3)
        gx = self.v("CompositeExtract", v3, 0)
        gy = self.v("CompositeExtract", v3, 1)
        idx = self.add(self.v("UConvert", gx, t=self.t64), self.mul(self.v("UConvert", gy, t=self.t64), param(5)))
        dans = self.ult(idx, param(2))
        travail, fin = self.id(), self.id()
        self.e("SelectionMerge", fin, 0)
        self.e("BranchConditional", dans, travail, fin)
        self.etiquette(travail)
        self.demandes = self.v("UConvert", param(3))
        idx32 = self.v("UConvert", idx)
        self.moi = self.v("IAdd", self.v("BitwiseAnd", idx32, self.c32(0x7FFFFFFF)), self.c32(1))
        self.derniere = self.var32()
        self.e("Store", self.derniere, self.c32(0xFFFFFFFF))
        self.ranger(self.nouvelle(self.var), self.add(param(1), idx))
        for k, nom in enumerate(dehors):
            self.ranger(self.nouvelle(nom), param(6 + k))
        for st in self.corps:
            self.instr(st)
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


# ---------------------------------------------------------------- 0.821 : Taranis, le noyau de la carte
M63 = 1 << 63


def magie_non_signee(d):
    """la multiplication qui remplace la division par d (d > 1, pas une puissance de deux) : (m, l) ; le quotient est
    (t + ((a - t) >> 1)) >> (l - 1), t = haut(m × a) (Granlund et Montgomery ; vérifié sur des millions de cas)"""
    l = (d - 1).bit_length()
    return (((1 << 64) * ((1 << l) - d)) // d + 1) & M64, l


def magie_signee(d):
    """(m, s) pour la division signée par la constante d (|d| > 1, pas une puissance de deux ; Hacker's Delight 10-1)"""
    ad = abs(d)
    t = M63 + ((d & M64) >> 63)
    anc = t - 1 - t % ad
    p = 63
    q1, r1 = M63 // anc, M63 - (M63 // anc) * anc
    q2, r2 = M63 // ad, M63 - (M63 // ad) * ad
    while True:
        p += 1
        q1, r1 = q1 * 2, r1 * 2
        if r1 >= anc:
            q1, r1 = q1 + 1, r1 - anc
        q2, r2 = q2 * 2, r2 * 2
        if r2 >= ad:
            q2, r2 = q2 + 1, r2 - ad
        delta = ad - r2
        if not (q1 < delta or (q1 == delta and r1 == 0)):
            break
    m = q2 + 1
    if d < 0:
        m = -m
    return m & M64, p - 64


class NoyauTaranis(NoyauI64):
    """0.821 : Taranis, le noyau de la carte (et non plus Lugus imité sur la carte). La mémoire est le monde rangé une
    fois sur la carte, chaque fréquence de l'étage 2 d'un seul tenant : l'adresse (f << 24) + i se lit au mot base[f] + i,
    sans table de pages, sans marque, sans demande (une adresse hors du monde lit 0, comme une case jamais écrite de
    Lugus). Une écriture note sa fréquence (ce qui redescend). Les entiers restent de 64 bits ; Taranis y ajoute ce qui
    leur manque sur une carte : la division par une constante devient une multiplication exacte (le haut du produit de
    128 bits), par une puissance de deux un décalage ; les autres divisions passent en 32 bits quand les deux nombres y
    tiennent (la carte divise en 32 bits bien plus vite), sinon en 64 bits."""

    def __init__(self, forge, var, corps, region=0):
        super().__init__(forge, var, corps, rapide=True)
        self.valeur_de = {}
        self.t_prod = None
        # 0.824 : la région de ses paramètres (sa place dans le lot de la carte)
        self.region = region

    def drapeau_n(self, n):
        self.e("Store", self.case64(self.parametres, self.c32(self.region * 64)), self.cst(n))

    def cst(self, v):
        r = super().cst(v)
        self.valeur_de[r] = v & M64
        return r

    # ------------------------------------------------------------ la mémoire : le monde d'un seul tenant
    def direct(self, a):
        f = self.v64("ShiftRightLogical", a, self.cst(24))
        ok_f = self.ult(f, self.cst(256))
        f32 = self.v("UConvert", self.v64("BitwiseAnd", f, self.cst(255)))
        i32 = self.v("UConvert", self.v64("BitwiseAnd", a, self.cst(0xFFFFFF)))
        base = self.v("Load", self.case(self.table, f32))
        taille = self.v("Load", self.case(self.table, self.v("IAdd", f32, self.c32(256))))
        ok = self.b("LogicalAnd", ok_f, self.b("ULessThan", i32, taille))
        mot = self.v("Select", ok, self.v("IAdd", base, i32), self.c32(0))
        return mot, ok, f32

    def lire_page(self, adr):
        mot, _ok, _f = self.direct(self.expr(adr))
        # le mot 0 du monde est toujours nul : une adresse hors du monde y lit 0, sans embranchement
        return self.v64("Load", self.case64(self.fenetre, mot))

    def ecrire_page(self, adr, valeur):
        a = self.expr(adr)
        x = self.expr(valeur)
        mot, ok, f32 = self.direct(a)
        oui, non, fin = self.id(), self.id(), self.id()
        self.e("SelectionMerge", fin, 0)
        self.e("BranchConditional", ok, oui, non)
        self.etiquette(oui)
        self.e("Store", self.case64(self.fenetre, mot), x)
        self.e("Store", self.case(self.marques, f32), self.c32(1))
        self.aller(fin)
        self.etiquette(non)
        self.drapeau_n(1)
        self.aller(fin)
        self.etiquette(fin)

    # ------------------------------------------------------------ les divisions
    def haut(self, op, x, y):
        if self.t_prod is None:
            self.t_prod = self.id()
            self.i(self.types, "TypeStruct", self.t_prod, self.t64, self.t64)
        p = self.v(op, x, y, t=self.t_prod)
        return self.v64("CompositeExtract", p, 1)

    def par_constante(self, op, a, d):
        """la division (ou le reste) par la constante d non nulle, au sens de Lugus ; None : pas de raccourci"""
        if op in ("/", "%"):
            if d & (d - 1) == 0:
                k = d.bit_length() - 1
                if op == "/":
                    return self.v64("ShiftRightLogical", a, self.cst(k)) if k else a
                return self.v64("BitwiseAnd", a, self.cst(d - 1))
            m, l = magie_non_signee(d)
            t = self.haut("UMulExtended", self.cst(m), a)
            q = self.v64("ShiftRightLogical", self.add(t, self.v64("ShiftRightLogical", self.sub(a, t), self.cst(1))),
                         self.cst(l - 1))
            return q if op == "/" else self.sub(a, self.mul(q, self.cst(d)))
        ds = d - (1 << 64) if d >> 63 else d
        if ds in (1, -1):
            return None
        ad = abs(ds)
        if ad & (ad - 1) == 0:
            k = ad.bit_length() - 1
            signe = self.v64("ShiftRightArithmetic", a, self.cst(63))
            biais = self.v64("ShiftRightLogical", signe, self.cst(64 - k))
            q = self.v64("ShiftRightArithmetic", self.add(a, biais), self.cst(k))
        else:
            m, sh = magie_signee(ds)
            q = self.haut("SMulExtended", self.cst(m), a)
            ms = m - (1 << 64) if m >> 63 else m
            if ds > 0 and ms < 0:
                q = self.add(q, a)
            if ds < 0 and ms > 0:
                q = self.sub(q, a)
            if sh:
                q = self.v64("ShiftRightArithmetic", q, self.cst(sh))
            q = self.add(q, self.v64("ShiftRightLogical", q, self.cst(63)))
            if ad & (ad - 1) == 0:
                pass
        if ad & (ad - 1) == 0 and ds < 0:
            q = self.neg(q)
        if op == "./":
            return q
        return self.sub(a, self.mul(q, self.cst(d)))

    def diviser(self, op, a, b):
        d = self.valeur_de.get(b)
        if d is not None and d != 0:
            r = self.par_constante(op, a, d)
            if r is not None:
                return r
        # en 32 bits quand les deux nombres y tiennent (et le diviseur n'est ni 0 ni -1) ; sinon en 64 bits
        if op in ("/", "%"):
            petit = self.eq(self.v64("ShiftRightLogical", self.v64("BitwiseOr", a, b), self.cst(32)), self.cst(0))
            vite_ok = self.b("LogicalAnd", petit, self.b("INotEqual", b, self.cst(0)))
            op32 = "UDiv" if op == "/" else "UMod"
            conv = "UConvert"
        else:
            def dans32(x):
                return self.eq(self.v64("ShiftRightLogical", self.add(x, self.cst(1 << 31)), self.cst(32)), self.cst(0))
            vite_ok = self.b("LogicalAnd", self.b("LogicalAnd", dans32(a), dans32(b)),
                             self.b("LogicalAnd", self.b("INotEqual", b, self.cst(0)), self.b("INotEqual", b, self.cst(M64))))
            op32 = "SDiv" if op == "./" else "SRem"
            conv = "SConvert"
        vite, lent, fin = self.id(), self.id(), self.id()
        self.e("SelectionMerge", fin, 0)
        self.e("BranchConditional", vite_ok, vite, lent)
        self.etiquette(vite)
        r32 = self.v(op32, self.v("UConvert", a), self.v("UConvert", b))
        r1 = self.v64(conv, r32)
        b1 = self.bloc
        self.aller(fin)
        self.etiquette(lent)
        r2 = NoyauI64.diviser(self, op, a, b)
        b2 = self.bloc
        self.aller(fin)
        self.etiquette(fin)
        return self.v64("Phi", r1, b1, r2, b2)
