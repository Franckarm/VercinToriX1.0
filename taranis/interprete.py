#!/usr/bin/env python3
"""0.854 : une carte de papier : le SPIR-V des noyaux de Taranis joué fil par fil, en Python (sans Vulkan). Pour
vérifier ici, sans carte graphique, ce que vtxc128 écrit pour la carte : le noyau est joué tour par tour sur un monde
rangé comme taranis_direct le range (la fréquence f d'un seul tenant : table[f] = sa place, table[256 + f] = sa taille,
en mots de 64 bits), et ce qu'il écrit se compare à ce que Lugus écrit pour la même boucle.

Ce qu'elle sait : les instructions des noyaux de Taranis (entiers de 32 et 64 bits, booléens, Select, Phi, les
branchements structurés, les variables de fonction, les tampons, UMulExtended/SMulExtended, AtomicUMin). Lente (un fil
après l'autre) : pour des boucles de quelques centaines de tours.

    jouer(mots, fenetre, params, table, fils) : fenetre (dict mot -> valeur), params (liste de 64 bits) modifiés"""
import struct

OPS = {17: "Capability", 14: "MemoryModel", 15: "EntryPoint", 16: "ExecutionMode", 71: "Decorate", 72: "MemberDecorate",
       19: "TypeVoid", 20: "TypeBool", 21: "TypeInt", 23: "TypeVector", 29: "TypeRuntimeArray", 30: "TypeStruct",
       32: "TypePointer", 33: "TypeFunction", 43: "Constant", 54: "Function", 56: "FunctionEnd", 59: "Variable",
       61: "Load", 62: "Store", 65: "AccessChain", 81: "CompositeExtract", 113: "UConvert", 114: "SConvert",
       128: "IAdd", 130: "ISub", 132: "IMul", 134: "UDiv", 135: "SDiv", 137: "UMod", 138: "SRem", 151: "UMulExtended",
       152: "SMulExtended", 165: "LogicalNotEqual", 166: "LogicalOr", 167: "LogicalAnd", 168: "LogicalNot", 169: "Select",
       170: "IEqual", 171: "INotEqual", 172: "UGreaterThan", 173: "SGreaterThan", 174: "UGreaterThanEqual",
       175: "SGreaterThanEqual", 176: "ULessThan", 177: "SLessThan", 178: "ULessThanEqual", 179: "SLessThanEqual",
       194: "ShiftRightLogical", 195: "ShiftRightArithmetic", 196: "ShiftLeftLogical", 197: "BitwiseOr",
       198: "BitwiseXor", 199: "BitwiseAnd", 200: "Not", 229: "AtomicExchange", 237: "AtomicUMin", 245: "Phi",
       246: "LoopMerge", 247: "SelectionMerge", 248: "Label", 249: "Branch", 250: "BranchConditional", 253: "Return"}


class Module:
    def __init__(self, mots):
        if isinstance(mots, (bytes, bytearray)):
            mots = list(struct.unpack("<%dI" % (len(mots) // 4), mots))
        assert mots[0] == 0x07230203
        self.types, self.consts, self.liaisons, self.code, self.blocs = {}, {}, {}, [], {}
        self.ctypes = {}
        self.globales = {}
        k = 5
        dans_fonction = False
        while k < len(mots):
            n, op = mots[k] >> 16, mots[k] & 0xFFFF
            a = mots[k + 1:k + n]
            nom = OPS[op]
            if nom == "TypeInt":
                self.types[a[0]] = ("int", a[1], a[2])
            elif nom == "TypeBool":
                self.types[a[0]] = ("bool",)
            elif nom == "TypeStruct":
                self.types[a[0]] = ("struct", list(a[1:]))
            elif nom == "TypePointer":
                self.types[a[0]] = ("ptr", a[1], a[2])
            elif nom in ("TypeVector", "TypeRuntimeArray", "TypeVoid", "TypeFunction"):
                self.types[a[0]] = (nom,) + tuple(a[1:])
            elif nom == "Constant":
                t = self.types[a[0]]
                v = a[2] if t[1] == 32 else a[2] | (a[3] << 32)
                self.consts[a[1]] = v
                self.ctypes[a[1]] = a[0]
            elif nom == "Decorate" and a[1] == 33:
                self.liaisons[a[0]] = a[2]
            elif nom == "Variable" and not dans_fonction:
                self.globales[a[1]] = a[2]
            elif nom == "Function":
                dans_fonction = True
            if dans_fonction:
                if nom == "Label":
                    self.blocs[a[0]] = len(self.code)
                self.code.append((nom, a))
            k += n

    def largeur(self, t):
        x = self.types[t]
        return x[1] if x[0] == "int" else None


def masque(v, w):
    return v & ((1 << w) - 1)


def signe(v, w):
    v = masque(v, w)
    return v - (1 << w) if v >> (w - 1) else v


def jouer(mots, fenetre, params, table, fils, marques=None):
    """joue le noyau pour les fils 0..fils-1 (gx = le fil, gy = 0 ; params[5] doit valoir au moins fils)"""
    m = Module(mots)
    marques = marques if marques is not None else {}
    tampons = {0: fenetre, 1: params, 2: table, 3: marques, 4: {}}
    for gx in range(fils):
        jouer_fil(m, tampons, gx)
    return tampons


class Pointeur:
    __slots__ = ("tampon", "indice", "cellule")

    def __init__(self, tampon=None, indice=None, cellule=None):
        self.tampon, self.indice, self.cellule = tampon, indice, cellule

    def lire(self):
        if self.cellule is not None:
            return self.cellule[0]
        t = self.tampon
        if isinstance(t, list):
            return t[self.indice] if self.indice < len(t) else 0
        return t.get(self.indice, 0)

    def ecrire(self, v):
        if self.cellule is not None:
            self.cellule[0] = v
            return
        t = self.tampon
        if isinstance(t, list):
            while len(t) <= self.indice:
                t.append(0)
            t[self.indice] = v
        else:
            t[self.indice] = v


def jouer_fil(m, tampons, gx):
    val = dict(m.consts)
    typ = dict(m.ctypes)
    for vid, cls in m.globales.items():
        if vid in m.liaisons:
            val[vid] = ("tampon", tampons[m.liaisons[vid]])
        else:
            val[vid] = ("gid",)
    pc = 0
    prec, courant = None, None
    pas = 0
    while True:
        pas += 1
        if pas > 50_000_000:
            raise RuntimeError("le fil ne finit pas")
        nom, a = m.code[pc]
        pc += 1
        if nom in ("Function", "LoopMerge", "SelectionMerge"):
            continue
        if nom == "Label":
            prec, courant = courant, a[0]
            continue
        if nom == "Return":
            return
        if nom == "Branch":
            pc = m.blocs[a[0]]
            continue
        if nom == "BranchConditional":
            pc = m.blocs[a[1] if val[a[0]] else a[2]]
            continue
        if nom == "Variable":
            val[a[1]] = Pointeur(cellule=[0])
            continue
        if nom == "Store":
            val[a[0]].ecrire(val[a[1]])
            continue
        t, r = a[0], a[1]
        w = m.largeur(t)
        x = [val.get(i) for i in a[2:]]
        if nom == "Load":
            p = val[a[2]]
            if isinstance(p, tuple) and p[0] == "gid":
                v = (gx, 0, 0)
            else:
                v = p.lire()
        elif nom == "AccessChain":
            base = val[a[2]]
            indice = val[a[4]]
            v = Pointeur(tampon=base[1], indice=indice)
        elif nom == "CompositeExtract":
            v = x[0][a[3]]
        elif nom == "Phi":
            v = None
            for k in range(2, len(a), 2):
                if a[k + 1] == prec:
                    v = val[a[k]]
            assert v is not None, "Phi sans son bloc"
        elif nom == "Select":
            v = x[1] if x[0] else x[2]
        elif nom in ("UConvert", "SConvert"):
            wi = m.largeur(typ.get(a[2])) if a[2] in typ else None
            src = x[0]
            if nom == "SConvert":
                wi = wi or 32
                v = masque(signe(src, wi), w)
            else:
                v = masque(src, w)
        elif nom in ("IAdd", "ISub", "IMul", "BitwiseAnd", "BitwiseOr", "BitwiseXor"):
            f = {"IAdd": lambda p, q: p + q, "ISub": lambda p, q: p - q, "IMul": lambda p, q: p * q,
                 "BitwiseAnd": lambda p, q: p & q, "BitwiseOr": lambda p, q: p | q,
                 "BitwiseXor": lambda p, q: p ^ q}[nom]
            v = masque(f(x[0], x[1]), w)
        elif nom == "Not":
            v = masque(~x[0], w)
        elif nom in ("UDiv", "UMod"):
            v = x[0] // x[1] if nom == "UDiv" else x[0] % x[1]
        elif nom in ("SDiv", "SRem"):
            p, q = signe(x[0], w), signe(x[1], w)
            quo = abs(p) // abs(q) * (1 if (p < 0) == (q < 0) else -1)
            v = masque(quo if nom == "SDiv" else p - quo * q, w)
        elif nom in ("ShiftLeftLogical", "ShiftRightLogical", "ShiftRightArithmetic"):
            s = x[1] % w
            if nom == "ShiftLeftLogical":
                v = masque(x[0] << s, w)
            elif nom == "ShiftRightLogical":
                v = x[0] >> s
            else:
                v = masque(signe(x[0], w) >> s, w)
        elif nom in ("UMulExtended", "SMulExtended"):
            wi = m.largeur(m.types[t][1][0])
            if nom == "UMulExtended":
                p = x[0] * x[1]
            else:
                p = signe(x[0], wi) * signe(x[1], wi)
            p = masque(p, 2 * wi)
            v = (masque(p, wi), p >> wi)
        elif nom in ("IEqual", "INotEqual", "ULessThan", "ULessThanEqual", "UGreaterThan", "UGreaterThanEqual"):
            p, q = x[0], x[1]
            v = {"IEqual": p == q, "INotEqual": p != q, "ULessThan": p < q, "ULessThanEqual": p <= q,
                 "UGreaterThan": p > q, "UGreaterThanEqual": p >= q}[nom]
        elif nom in ("SLessThan", "SLessThanEqual", "SGreaterThan", "SGreaterThanEqual"):
            wi = m.largeur(typ[a[2]])
            p, q = signe(x[0], wi), signe(x[1], wi)
            v = {"SLessThan": p < q, "SLessThanEqual": p <= q, "SGreaterThan": p > q, "SGreaterThanEqual": p >= q}[nom]
        elif nom in ("LogicalAnd", "LogicalOr", "LogicalNotEqual"):
            v = {"LogicalAnd": x[0] and x[1], "LogicalOr": x[0] or x[1], "LogicalNotEqual": x[0] != x[1]}[nom]
        elif nom == "LogicalNot":
            v = not x[0]
        elif nom == "AtomicUMin":
            p = val[a[2]]
            ancien = p.lire()
            p.ecrire(min(ancien, x[3]))
            v = ancien
        elif nom == "AtomicExchange":
            p = val[a[2]]
            ancien = p.lire()
            p.ecrire(x[3])
            v = ancien
        else:
            raise NotImplementedError(nom)
        val[r] = v
        typ[r] = t
    # (jamais atteint)

