#!/usr/bin/env python3
"""Taranis : l'écrivain de SPIR-V de vtx (le langage des cartes graphiques, par Vulkan), sans aucune bibliothèque.

Un module SPIR-V est une suite de mots de 32 bits : l'en-tête (le nombre magique 0x07230203, la version, le plus grand
identifiant), puis des instructions (le nombre de mots << 16 | le code de l'opération, puis ses opérandes). Ce fichier
écrit le noyau de la sonde (étape zéro) : chaque fil de la carte prend son numéro i et le brasse en TOURS tours de
xorshift et de multiplication, sur des entiers de 32 bits, puis le range dans t[i]. Le même brassage est refait par le
processeur (ici en Python, et en Rust dans taranis.rs) : les deux doivent donner les mêmes mots.

    python3 taranis/spirv.py [sortie.spv]      écrit le noyau (par défaut : vtx-rs/taranis_sonde.spv) et le relit
"""
import os
import struct
import sys

# ------------------------------------------------------------------ les codes de SPIR-V (la spécification, 1.0)
OP = {
    "Capability": 17, "MemoryModel": 14, "EntryPoint": 15, "ExecutionMode": 16, "Decorate": 71, "MemberDecorate": 72,
    "TypeVoid": 19, "TypeInt": 21, "TypeVector": 23, "TypeRuntimeArray": 29, "TypeStruct": 30, "TypePointer": 32,
    "TypeFunction": 33, "Constant": 43, "Function": 54, "FunctionEnd": 56, "Variable": 59, "Load": 61, "Store": 62,
    "AccessChain": 65, "CompositeExtract": 81, "IAdd": 128, "IMul": 132, "ShiftRightLogical": 194,
    "ShiftLeftLogical": 196, "BitwiseXor": 198, "Label": 248, "Return": 253,
}
NOM_OP = {v: k for k, v in OP.items()}
SHADER, LOGIQUE, GLSL450, GLCOMPUTE, LOCALSIZE = 1, 0, 1, 5, 17
BUFFERBLOCK, ARRAYSTRIDE, BUILTIN, BINDING, DESCRIPTORSET, OFFSET = 3, 6, 11, 33, 34, 35
GLOBALINVOCATIONID = 28
INPUT, UNIFORM, FONCTION = 1, 2, 7

TOURS = 64          # les tours du brassage (de quoi occuper la carte : 6 opérations par tour)
LARGEUR = 64        # les fils d'un groupe


def texte(s):
    """une chaîne littérale : ses octets, un zéro, complétés à un mot"""
    b = s.encode("utf-8") + b"\0"
    b += b"\0" * (-len(b) % 4)
    return list(struct.unpack("<%dI" % (len(b) // 4), b))


class Module:
    def __init__(self):
        self.prochain = 1
        self.tete, self.decor, self.types, self.corps = [], [], [], []

    def id(self):
        self.prochain += 1
        return self.prochain - 1

    @staticmethod
    def instr(liste, op, *mots):
        liste.append(((len(mots) + 1) << 16) | OP[op])
        liste.extend(mots)

    def binaire(self):
        mots = [0x07230203, 0x00010000, 0, self.prochain, 0] + self.tete + self.decor + self.types + self.corps
        return struct.pack("<%dI" % len(mots), *mots)


def brasser_python(i):
    """la référence : le même brassage que le noyau, en Python"""
    m = 0xFFFFFFFF
    x = i & m
    for _ in range(TOURS):
        x ^= (x << 13) & m
        x ^= x >> 17
        x ^= (x << 5) & m
        x = (x * 0x9E3779B1 + i) & m
    return x


def noyau_sonde():
    """le noyau : t[i] = brasser(i), i étant le numéro du fil (GlobalInvocationId.x)"""
    M = Module()
    I = M.instr
    principal, gid = M.id(), M.id()
    t_void, t_fn, t_u32, t_v3, t_pv3 = M.id(), M.id(), M.id(), M.id(), M.id()
    t_tab, t_bloc, t_pbloc, t_pu32 = M.id(), M.id(), M.id(), M.id()
    tampon = M.id()
    c = {}

    def cst(v):
        if v not in c:
            c[v] = M.id()
            I(M.types, "Constant", t_u32, c[v], v)
        return c[v]

    I(M.tete, "Capability", SHADER)
    I(M.tete, "MemoryModel", LOGIQUE, GLSL450)
    I(M.tete, "EntryPoint", GLCOMPUTE, principal, *texte("main"), gid)
    I(M.tete, "ExecutionMode", principal, LOCALSIZE, LARGEUR, 1, 1)
    I(M.decor, "Decorate", gid, BUILTIN, GLOBALINVOCATIONID)
    I(M.decor, "Decorate", t_tab, ARRAYSTRIDE, 4)
    I(M.decor, "MemberDecorate", t_bloc, 0, OFFSET, 0)
    I(M.decor, "Decorate", t_bloc, BUFFERBLOCK)
    I(M.decor, "Decorate", tampon, DESCRIPTORSET, 0)
    I(M.decor, "Decorate", tampon, BINDING, 0)
    I(M.types, "TypeVoid", t_void)
    I(M.types, "TypeFunction", t_fn, t_void)
    I(M.types, "TypeInt", t_u32, 32, 0)
    I(M.types, "TypeVector", t_v3, t_u32, 3)
    I(M.types, "TypePointer", t_pv3, INPUT, t_v3)
    I(M.types, "TypeRuntimeArray", t_tab, t_u32)
    I(M.types, "TypeStruct", t_bloc, t_tab)
    I(M.types, "TypePointer", t_pbloc, UNIFORM, t_bloc)
    I(M.types, "TypePointer", t_pu32, UNIFORM, t_u32)
    I(M.types, "Variable", t_pv3, gid, INPUT)
    I(M.types, "Variable", t_pbloc, tampon, UNIFORM)
    c0, c13, c17, c5, cmul = cst(0), cst(13), cst(17), cst(5), cst(0x9E3779B1)

    I(M.corps, "Function", t_void, principal, 0, t_fn)
    I(M.corps, "Label", M.id())
    v = M.id()
    I(M.corps, "Load", t_v3, v, gid)
    i = M.id()
    I(M.corps, "CompositeExtract", t_u32, i, v, 0)
    x = i
    for _ in range(TOURS):
        for op, k in (("ShiftLeftLogical", c13), ("ShiftRightLogical", c17), ("ShiftLeftLogical", c5)):
            d, y = M.id(), M.id()
            I(M.corps, op, t_u32, d, x, k)
            I(M.corps, "BitwiseXor", t_u32, y, x, d)
            x = y
        p, s = M.id(), M.id()
        I(M.corps, "IMul", t_u32, p, x, cmul)
        I(M.corps, "IAdd", t_u32, s, p, i)
        x = s
    case = M.id()
    I(M.corps, "AccessChain", t_pu32, case, tampon, c0, i)
    I(M.corps, "Store", case, x)
    I(M.corps, "Return")
    I(M.corps, "FunctionEnd")
    return M.binaire()


def relire(b):
    """une relecture : l'en-tête, chaque instruction de la bonne longueur, chaque identifiant défini une fois et sous la
    borne ; rend la liste des opérations (une erreur sinon)"""
    assert len(b) % 4 == 0, "pas un nombre entier de mots"
    mots = struct.unpack("<%dI" % (len(b) // 4), b)
    assert mots[0] == 0x07230203, "nombre magique"
    borne = mots[3]
    k, ops, definis = 5, [], set()
    while k < len(mots):
        n, op = mots[k] >> 16, mots[k] & 0xFFFF
        assert n >= 1 and k + n <= len(mots), f"longueur fausse au mot {k}"
        assert op in NOM_OP, f"opération inconnue {op} au mot {k}"
        nom = NOM_OP[op]
        # l'identifiant défini par l'instruction : le premier opérande pour les types, le second pour les valeurs
        if nom.startswith("Type") or nom == "Label":
            r = mots[k + 1]
        elif nom in ("Constant", "Variable", "Load", "CompositeExtract", "IAdd", "IMul", "ShiftRightLogical",
                     "ShiftLeftLogical", "BitwiseXor", "AccessChain", "Function"):
            r = mots[k + 2]
        else:
            r = None
        if r is not None:
            assert 0 < r < borne, f"identifiant {r} hors de la borne {borne}"
            assert r not in definis, f"identifiant {r} défini deux fois"
            definis.add(r)
        ops.append(nom)
        k += n
    return ops


if __name__ == "__main__":
    ici = os.path.dirname(os.path.abspath(__file__))
    sortie = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(ici), "vtx-rs", "taranis_sonde.spv")
    b = noyau_sonde()
    ops = relire(b)
    open(sortie, "wb").write(b)
    print(f"{sortie} : {len(b) // 4} mots, {len(ops)} instructions ; brasser(0..3) = "
          + ", ".join(str(brasser_python(i)) for i in range(4)))
