#!/usr/bin/env python3
"""SPU-64 : la machine de référence (Python) et son assembleur. Spécification : docs/specification-spu64.md.

Un mot = un point profond #RRRRGGGGBBBBAAAA (64 bits, 32 quits). Une instruction : opération (16 bits), d, s, t, u
(4 bits chacun), imm (32 bits). Adresse longue : étage (bits 63-62), fréquence (47-24), #RRGGBB (23-0).

    python3 spu64.py asm  prog.s64        assemble et lance
    python3 spu64.py corpus FICHIER       une ligne par programme : « mots;entrées » -> « pas|sorties|mémoire »"""
import os
import re
import sys
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qflot import Q32, Q64, vers_ieee64, de_ieee64  # noqa: E402

M64 = (1 << 64) - 1
M48 = (1 << 48) - 1
M32 = (1 << 32) - 1
PILE = 0x7FFFFFFF
TAILLE_X, TAILLE_Y = 14680058, 14680059      # taille de l'image (étage 3, fréquence 0), comme au SPU-32

OPS = {
    "NOP": (0x00, "none"), "ADD": (0x01, "rrr"), "SUB": (0x02, "rrr"), "MUL": (0x03, "rrr"),
    "SHL4": (0x04, "rr"), "SHR4": (0x05, "rr"), "ADDI": (0x06, "rri"), "SUBI": (0x07, "rri"),
    "SHL": (0x08, "rrr"), "SHR": (0x09, "rrr"), "LDI": (0x0A, "ldi"), "MOV": (0x0B, "rr"),
    "DIV": (0x0C, "rrr"), "MOD": (0x0D, "rrr"), "CMP": (0x0E, "cmp"), "CMPI": (0x0F, "cmpi"),
    "MIN": (0x10, "rrr"), "MAX": (0x11, "rrr"), "CMP3": (0x12, "rr"), "ADDM4": (0x13, "rrr"),
    "AND": (0x14, "rrr"), "OR": (0x15, "rrr"), "XOR": (0x16, "rrr"), "SAR": (0x17, "rrr"),
    "LDIS": (0x18, "ri"), "LDIU": (0x19, "ri"), "DIVS": (0x1A, "rrr"), "MODS": (0x1B, "rrr"),
    "ZEXT32": (0x1C, "rr"), "SEXT32": (0x1D, "rr"), "MULHS": (0x1E, "rrr"), "ETG": (0x1F, "rri"), "ETGX": (0x22, "rrr"),
    "LD": (0x20, "mem"), "ST": (0x21, "mem"), "IN": (0x23, "in"), "OUT": (0x24, "out"),
    "LDF": (0x25, "off"), "STF": (0x26, "off"), "PUSH": (0x27, "out"), "POP": (0x28, "in"),
    "LDX": (0x29, "rrr"), "STX": (0x2A, "rrr"),
    "JMP": (0x30, "jump"), "JZ": (0x31, "jump"), "JNZ": (0x32, "jump"), "CALL": (0x33, "jump"),
    "RET": (0x34, "none"), "JC": (0x35, "jump"), "JNC": (0x36, "jump"),
    "GDOT": (0x38, "rrr"), "GEMV": (0x39, "none"), "HALT": (0x3F, "none"),
    "FADD": (0x40, "rrr"), "FSUB": (0x41, "rrr"), "FMUL": (0x42, "rrr"), "FDIV": (0x43, "rrr"),
    "FEQ": (0x44, "rrr"), "FLT": (0x45, "rrr"), "FLE": (0x46, "rrr"), "FSQRT": (0x47, "rr"),
    "ITOF": (0x48, "rr"), "ITOFS": (0x49, "rr"), "FTOI": (0x4A, "rr"), "FROUND": (0x4B, "rr"),
    "ADC": (0x4C, "rrr"), "SBC": (0x4D, "rrr"), "MULHU": (0x4E, "rrr"), "QEGAL": (0x4F, "rrr"), "COMPTE": (0x50, "rr"),
    "ENTC": (0x51, "rr"), "SORC": (0x52, "rrr"), "SYS": (0x53, "rrr"),
    "LDQ": (0x54, "rrr"), "STQ": (0x55, "rrr"),
    "ET4": (0x56, "rrr"), "OU4": (0x57, "rrr"), "NON4": (0x58, "rr"), "ANTI": (0x59, "rr"), "EXQ": (0x5A, "rrr"),
    "FNEG": (0x5B, "rr"), "FETAT": (0x5C, "rr"), "FCMP": (0x5D, "rrr"), "MARQUE": (0x5E, "marque"), "BRIN": (0x5F, "rr"),
    "SADD": (0x60, "rrr"), "SSUB": (0x61, "rrr"), "SMUL": (0x62, "rrr"), "SDIV": (0x63, "rrr"),
    "SEQ": (0x64, "rrr"), "SLT": (0x65, "rrr"), "SLE": (0x66, "rrr"), "SSQRT": (0x67, "rr"),
    "STOF": (0x68, "rr"), "FTOS": (0x69, "rr"), "SNEG": (0x6A, "rr"),
    "FVIEEE": (0x6C, "rr"), "FDIEEE": (0x6D, "rr"),
}
NOMS = {code: nom for nom, (code, _) in OPS.items()}



# ---- les cubes sur disque : le miroir inversé et l'ombre (comme vtx-rs/src/miroir.rs). À côté de chaque cube, son
# anti-cube (« anti » devant le nom : l'opposé par le centre, valeurs complémentées et places opposées, #FFFFFF - adresse) et son ombre (« ombre » à la place de
# « cube ») : pour chaque page et chaque colonne GG, neuf mots en ou exclusif, o0 sur les 256 mots BB, ok sur ceux dont
# le bit k de BB vaut 1 ; une erreur par colonne s'y retrouve (o0) et s'y situe (les ok). À la lecture : vrai (2) tout
# s'accorde, faux (1) réparé, variable (3) contradiction que rien ne tranche, inconnu (0) rien.
_MOTS = 65536


def _prefixe(chemin, avant):
    d, n = os.path.split(chemin)
    return os.path.join(d, avant + n)


def _chemin_ombre(chemin):
    d, n = os.path.split(chemin)
    return os.path.join(d, n.replace("cube", "ombre", 1))


def _entete_avec(entete, quoi):
    return entete[:3] + quoi + entete[6:]


def _format(entete):
    if entete == b"VTXCU128":
        return (16, _MOTS // 4)          # Lugus, le SPU-128 : mots de 16 octets, et leurs brins
    return (8, _MOTS // 4) if entete == b"VTXCUB64" else (4, 0)


def _taille_ombre(mot):
    """Les mots de l'ombre : 8 octets (comme ceux du SPU-64, et pour le SPU-32), 16 pour Lugus."""
    return 16 if mot == 16 else 8


def _pages(corps, fmt):
    mot, suite = fmt
    t = 4 + _MOTS * mot + suite
    m, i = {}, 0
    while i + t <= len(corps):
        m[int.from_bytes(corps[i:i + 4], "little")] = bytes(corps[i + 4:i + t])
        i += t
    return m


def _retourner(page, fmt):
    """La page vue par le centre du cube : le mot GGBB passe en #FFFF - GGBB (les brins aussi) ; deux fois, elle revient."""
    mot, suite = fmt
    n = _MOTS * mot
    mots = [page[j * mot:(j + 1) * mot] for j in range(_MOTS)]
    r = bytearray(b"".join(reversed(mots)))
    if suite:
        br = page[n:]
        nb = bytearray(suite)
        for j in range(_MOTS):
            q = (br[j // 4] >> (2 * (j % 4))) & 3
            if q:
                i = _MOTS - 1 - j
                nb[i // 4] |= q << (2 * (i % 4))
        r += nb
    return bytes(r)


def _mots(page, mot):
    return [int.from_bytes(page[j * mot:(j + 1) * mot], "little") for j in range(_MOTS)]


def _ombre_page(page, mot):
    w = _mots(page, mot)
    o = [0] * (256 * 9)
    for gg in range(256):
        b = gg * 9
        for bb in range(256):
            v = w[gg * 256 + bb]
            if v:
                o[b] ^= v
                for k in range(8):
                    if bb >> k & 1:
                        o[b + 1 + k] ^= v
    return o


def _juger(calc, lue):
    d = [calc[k] ^ lue[k] for k in range(9)]
    if not any(d):
        return ("juste",)
    if d[0] == 0:
        return ("juste",) if sum(1 for x in d if x) == 1 else ("fausse",)
    bb = 0
    for k in range(8):
        if d[1 + k] == d[0]:
            bb |= 1 << k
        elif d[1 + k]:
            return ("fausse",)
    return ("rectifiable", bb, d[0])


def ecrire_double(chemin, octets):
    with open(chemin, "wb") as h:
        h.write(octets)
    mot, suite = _format(octets[:8])
    # l'anti-cube : chaque page à sa place opposée (255 - k), chaque mot à la sienne (#FFFF - GGBB), tout complémenté
    pages = _pages(octets[8:], (mot, suite))
    corps = b"".join((255 - (k & 255)).to_bytes(4, "little") + _retourner(pg, (mot, suite)) for k, pg in sorted(pages.items(), reverse=True))
    with open(_prefixe(chemin, "anti"), "wb") as h:
        h.write(_entete_avec(octets[:8], b"ANS") + bytes(255 - x for x in corps))
    o = [_entete_avec(octets[:8], b"OMB")]
    for k, p in sorted(_pages(octets[8:], (mot, suite)).items()):
        o.append(k.to_bytes(4, "little") + b"".join(v.to_bytes(_taille_ombre(mot), "little") for v in _ombre_page(p, mot)))
    with open(_chemin_ombre(chemin), "wb") as h:
        h.write(b"".join(o))


def lire_double(chemin, entete):
    """Rend (contenu retenu ou None, état de Belnap) ; ce qui a été réparé est réécrit."""
    def lire(c, e):
        try:
            with open(c, "rb") as h:
                b = h.read()
        except OSError:
            return None
        return b if b[:8] == e else None
    fmt = _format(entete)
    mot, suite = fmt
    p = lire(chemin, entete)
    a = lire(_prefixe(chemin, "anti"), _entete_avec(entete, b"ANS"))
    if p is None and a is None:
        return None, 0
    ob = lire(_chemin_ombre(chemin), _entete_avec(entete, b"OMB"))
    ombres = None
    if ob is not None:
        oz = _taille_ombre(mot)
        ombres, t, i = {}, 4 + 256 * 9 * oz, 8
        while i + t <= len(ob):
            k = int.from_bytes(ob[i:i + 4], "little")
            ombres[k] = [int.from_bytes(ob[i + 4 + oz * j:i + 4 + oz * (j + 1)], "little") for j in range(256 * 9)]
            i += t
    pp = _pages(p[8:], fmt) if p is not None else {}
    pa = {}
    if a is not None:
        # l'anti-cube relu : complémenté, puis chaque page et chaque mot remis à leur place
        pa = {255 - (k & 255): _retourner(pg, fmt) for k, pg in _pages(bytes(255 - x for x in a[8:]), fmt).items()}
    rang = {0: 0, 2: 1, 1: 2, 3: 3}
    etat = 2
    ombre_fausse = ombres is None and p is not None and a is not None

    def pire(e):
        nonlocal etat
        if rang[e] > rang[etat]:
            etat = e
    corps = [entete]
    for k in sorted(set(pp) | set(pa)):
        x, y = pp.get(k), pa.get(k)
        o = ombres.get(k) if ombres is not None else None
        if x is not None and x == y:
            if o is not None and _ombre_page(x, mot) != o:
                ombre_fausse = True
            page = x
        else:
            pire(1)
            if o is None:
                if x is not None and y is not None:
                    pire(3)
                page = x if x is not None else y
            else:
                cx = _ombre_page(x, mot) if x is not None else None
                cy = _ombre_page(y, mot) if y is not None else None
                r = bytearray(x if x is not None else y)
                for gg in range(256):
                    lue = o[gg * 9:gg * 9 + 9]
                    jx = _juger(cx[gg * 9:gg * 9 + 9], lue) if cx is not None else None
                    jy = _juger(cy[gg * 9:gg * 9 + 9], lue) if cy is not None else None
                    d0, d1 = gg * 256 * mot, (gg + 1) * 256 * mot
                    if jx and jx[0] == "juste":
                        r[d0:d1] = x[d0:d1]
                    elif jy and jy[0] == "juste":
                        r[d0:d1] = y[d0:d1]
                    elif (jx and jx[0] == "rectifiable") or (jy and jy[0] == "rectifiable"):
                        src, j = (x, jx) if jx and jx[0] == "rectifiable" else (y, jy)
                        r[d0:d1] = src[d0:d1]
                        q = (gg * 256 + j[1]) * mot
                        v = int.from_bytes(r[q:q + mot], "little") ^ j[2]
                        r[q:q + mot] = v.to_bytes(mot, "little")
                    else:
                        pire(3)
                if x is not None and y is not None and x[_MOTS * mot:] != y[_MOTS * mot:]:
                    pire(3)
                page = bytes(r)
        corps.append(k.to_bytes(4, "little") + page)
    corps = b"".join(corps)
    if etat == 2 and ombre_fausse and ombres is not None:
        etat = 1
    if etat == 1 or (etat == 2 and ombre_fausse):
        try:
            ecrire_double(chemin, corps)
        except OSError:
            pass
    return corps, etat


def noter_etat(machine, etat):
    """Le pire état vu depuis le dernier etat_disque() (inconnu < vrai < faux < variable)."""
    rang = {0: 0, 2: 1, 1: 2, 3: 3}
    if rang[etat] > rang[getattr(machine, "_etat_disque", 0)]:
        machine._etat_disque = etat

class Erreur(Exception):
    pass


def instr(op, d=0, s=0, t=0, imm=0):
    return (op << 48) | (d << 44) | (s << 40) | (t << 36) | (imm & M32)


def entier(t):
    t = t.strip().lstrip("#").replace("_", "")
    if t.lower().startswith("0x"):
        return int(t, 16)
    if t.lower().startswith("0q"):
        return int(t[2:], 4)
    return int(t)


def assembler(texte):
    """Assemble ; rend les mots. Une ligne : « étiquette: OP args ; commentaire ». « .MOT v, v… » range des mots."""
    etiquettes, lignes, adr = {}, [], 0
    for brut in texte.splitlines():
        ligne = brut.split(";")[0].strip()
        while ":" in ligne:
            nom, ligne = ligne.split(":", 1)
            etiquettes[nom.strip().upper()] = adr
            ligne = ligne.strip()
        if ligne:
            lignes.append(ligne)
            t0 = ligne.split()[0].upper()
            adr += 2 if t0 == "LDI" else (len(ligne.split(None, 1)[1].split(",")) if t0 == ".MOT" else 1)

    def reg(s):
        m = re.fullmatch(r"[Rr](\d+)", s.strip())
        if not m or int(m.group(1)) > 15:
            raise Erreur(f"registre invalide : {s}")
        return int(m.group(1))

    def val(s):
        u = s.strip().upper()
        return etiquettes[u] if u in etiquettes else entier(s)

    def imm32(v, signe):
        if signe and not -(1 << 31) <= v < (1 << 31):
            raise Erreur(f"immédiat hors de 32 bits signés : {v}")
        if not signe and not 0 <= v <= M32:
            raise Erreur(f"immédiat hors de 32 bits : {v}")
        return v & M32

    mots = []
    for ligne in lignes:
        parts = ligne.split(None, 1)
        nom = parts[0].upper()
        args = [a.strip() for a in parts[1].split(",")] if len(parts) > 1 else []
        if nom == ".MOT":
            mots.extend(val(a) & M64 for a in args)
            continue
        if nom not in OPS:
            raise Erreur(f"instruction inconnue : {nom}")
        code, forme = OPS[nom]
        if forme == "none":
            mots.append(instr(code))
        elif forme == "rrr":
            mots.append(instr(code, reg(args[0]), reg(args[1]), reg(args[2])))
        elif forme == "rri" or forme == "mem":
            mots.append(instr(code, reg(args[0]), reg(args[1]), 0, imm32(val(args[2]) if len(args) > 2 else 0, True)))
        elif forme == "rr":
            mots.append(instr(code, reg(args[0]), reg(args[1])))
        elif forme == "ri":
            mots.append(instr(code, reg(args[0]), 0, 0, imm32(val(args[1]), code == 0x18)))
        elif forme == "cmp":
            mots.append(instr(code, 0, reg(args[0]), reg(args[1])))
        elif forme == "cmpi":
            mots.append(instr(code, 0, reg(args[0]), 0, imm32(val(args[1]), True)))
        elif forme == "marque":
            mots.append(instr(code, 0, reg(args[0]), reg(args[1]), imm32(val(args[2]), True)))
        elif forme == "in":
            mots.append(instr(code, reg(args[0])))
        elif forme == "out":
            mots.append(instr(code, 0, reg(args[0])))
        elif forme == "off":
            mots.append(instr(code, reg(args[0]), 0, 0, imm32(val(args[1]), True)))
        elif forme == "jump":
            mots.append(instr(code, imm=imm32(val(args[0]), False)))
        elif forme == "ldi":
            mots.append(instr(code, reg(args[0])))
            mots.append(val(args[1]) & M64)
    return mots


def sext32(v):
    v &= M32
    return v - (1 << 32) if v >> 31 else v


def signe64(v):
    return v - (1 << 64) if v >> 63 else v


def quits(f, a, b, n=32):
    return sum(f((a >> (2 * k)) & 3, (b >> (2 * k)) & 3) << (2 * k) for k in range(n))


V64, F64 = 0xAAAAAAAAAAAAAAAA, 0x5555555555555555


class CPU:
    def __init__(self, dossier=None):
        self.r = [0] * 16
        self.r[14] = PILE
        self.pc = 0
        self.z = self.c = self.n = False
        self.arrete = False
        self.mem = {}                 # (étage, indice) -> mot
        self.brin = {}                # (étage, indice) -> 1 ADN, 2 ARN (absent : libre)
        self.entree = deque()
        self.sortie = []
        self.texte = []
        self.texte_entree = deque()
        self.fichiers = {}
        self.dossier = dossier         # None : ni fichiers ni cubes sur disque (corpus, tests)
        self.pages_vues = set()        # (étage, page) déjà cherchées sur disque
        self.pas = 0
        self.presenter = None          # rappel du service 12 (la fenêtre de la toile), ou None

    def charger(self, mots):
        for i, w in enumerate(mots):
            self.mem[(0, i)] = w & M64

    # --- mémoire
    @staticmethod
    def place(adr):
        adr &= M64
        return adr >> 62, adr & M48

    def page_disque(self, e, i):
        if self.dossier is None:
            return
        cle = (e, i >> 16)
        if cle in self.pages_vues:
            return
        self.pages_vues.add(cle)
        f = i >> 24
        chemin = os.path.join(self.dossier, f"cube64-{e}-{f}.cub")
        b, etat = lire_double(chemin, b"VTXCUB64")
        noter_etat(self, etat)
        if b is None:
            return
        k, voulue = 8, (i >> 16) & 255
        taille = 4 + 65536 * 8 + 16384
        while k + taille <= len(b):
            p = int.from_bytes(b[k:k + 4], "little")
            if p == voulue:
                base = (f << 24) | (p << 16)
                for j in range(65536):
                    v = int.from_bytes(b[k + 4 + 8 * j:k + 12 + 8 * j], "little")
                    q = (b[k + 4 + 524288 + j // 4] >> (2 * (j % 4))) & 3
                    if v and (e, base | j) not in self.mem:
                        self.mem[(e, base | j)] = v
                    if q and (e, base | j) not in self.brin:
                        self.brin[(e, base | j)] = q
                return
            k += taille

    def lire(self, adr):
        e, i = self.place(adr)
        self.page_disque(e, i)
        return self.mem.get((e, i), 0)

    def ecrire_mem(self, adr, v):
        e, i = self.place(adr)
        self.page_disque(e, i)
        if self.brin.get((e, i)) == 1:
            raise Erreur(f"écriture dans un mot ADN (fixé) à l'adresse étage {e}, #{i:012X}")
        self.mem[(e, i)] = v & M64

    def ecrire(self, d, v):
        if d:
            self.r[d] = v & M64

    def drapeaux(self, v, c=False):
        self.z, self.n, self.c = v == 0, (v >> 63) == 1, c

    def poser(self, d, v, c=False):
        v &= M64
        self.ecrire(d, v)
        self.drapeaux(v, c)

    # --- canaux et services
    def lire_canal(self, c):
        if c == 0:
            return self.entree.popleft() if self.entree else 0
        if c == 1:
            return self.texte_entree.popleft() if self.texte_entree else M64
        f = self.fichiers.get(c)
        if f is None or f[0] != "l" or f[2] >= len(f[1]):
            return M64
        f[2] += 1
        return f[1][f[2] - 1]

    def ecrire_canal(self, c, v):
        if c == 0:
            self.sortie.append(v)
        elif c == 1:
            self.texte.append(v)
        elif c in self.fichiers and self.fichiers[c][0] == "e":
            self.fichiers[c][1].append(v)

    def texte_memoire(self, adr):
        n = self.lire(adr)
        return "".join(chr(self.lire(adr + 1 + k) & 0x1FFFFF) for k in range(min(n, 4096)))

    def service(self, code, arg):
        if code in (1, 2):
            if self.dossier is None:
                return M64
            chemin = os.path.join(self.dossier, self.texte_memoire(arg))
            canal = max([1] + list(self.fichiers)) + 1
            if code == 1:
                try:
                    with open(chemin, encoding="utf-8") as h:
                        self.fichiers[canal] = ["l", [ord(ch) for ch in h.read()], 0, chemin]
                except OSError:
                    return M64
            else:
                self.fichiers[canal] = ["e", [], 0, chemin]
            return canal
        if code == 3:
            f = self.fichiers.pop(arg, None)
            if f and f[0] == "e":
                try:
                    with open(f[3], "w", encoding="utf-8") as h:
                        h.write("".join(chr(c & 0x1FFFFF) for c in f[1]))
                except OSError:
                    return M64
            return 0
        if code == 4:
            f = self.fichiers.get(arg)
            return 1 if f is None or f[0] != "l" or f[2] >= len(f[1]) else 0
        if code == 5:
            return int.from_bytes(os.urandom(8), "little")
        if code in (6, 7):
            # écrire ou lire un bloc de mots (nom, adresse longue et nombre de mots en @3[14680060..14680062], comme au
            # SPU-32) ; huit octets par mot, petit-boutiste
            if self.dossier is None:
                return M64
            e3 = 3 << 62
            chemin = os.path.join(self.dossier, self.texte_memoire(self.lire(e3 | 14680060)))
            a, n = self.lire(e3 | 14680061), self.lire(e3 | 14680062)
            try:
                if code == 6:
                    with open(chemin, "wb") as h:
                        h.write(b"".join(self.lire(a + k).to_bytes(8, "little") for k in range(n)))
                    return n
                with open(chemin, "rb") as h:
                    b = h.read()
            except OSError:
                return M64
            k = min(len(b) // 8, n)
            for j in range(k):
                self.ecrire_mem(a + j, int.from_bytes(b[8 * j:8 * j + 8], "little"))
            return k
        if code == 10:
            raise Erreur("mémoire pleine")
        if code == 11:
            return self.ranger_cube(arg)
        if code == 12:
            return self.presenter(self) if self.presenter else 0
        if code == 13:
            return self.jeter_cube(arg)
        if code in (16, 17, 20, 21, 23):
            return 0                          # souris, touche, molette, appuyee, glisse : pas de fenêtre ici
        if code == 22:
            etat = getattr(self, "_etat_disque", 0)   # l'état des cubes lus sur disque (miroir inversé)
            self._etat_disque = 0
            return etat
        if code == 19:
            ancienne = self.__dict__.get("_cadence", 16)   # cadence : gardée, sans effet sans fenêtre
            self._cadence = min(arg, 60000)
            return ancienne
        if code == 18:
            import time                       # horloge : millisecondes depuis le lancement
            debut = self.__dict__.setdefault("_debut", time.monotonic())
            return int((time.monotonic() - debut) * 1000)
        return M64

    def jeter_cube(self, adr):
        """Le cube de transfert jetable : toutes les pages du cube (étage, fréquence) quittent la mémoire d'un coup, sans
        être relues du disque ; rend le nombre de pages jetées."""
        e, i = self.place(adr)
        f = i >> 24
        pages = {(j >> 16) & 255 for (ee, j) in list(self.mem) + list(self.brin) if ee == e and j >> 24 == f}
        self.mem = {k: v for k, v in self.mem.items() if not (k[0] == e and k[1] >> 24 == f)}
        self.brin = {k: v for k, v in self.brin.items() if not (k[0] == e and k[1] >> 24 == f)}
        for p in range(256):
            self.pages_vues.add((e, (f << 8) | p))
        return len(pages)

    def ranger_cube(self, adr):
        e, i = self.place(adr)
        f = i >> 24
        if self.dossier is None:
            return M64
        pages = {}
        for (ee, j), v in self.mem.items():
            if ee == e and j >> 24 == f and v:
                pages.setdefault((j >> 16) & 255, None)
        for (ee, j), q in self.brin.items():
            if ee == e and j >> 24 == f and q:
                pages.setdefault((j >> 16) & 255, None)
        h = [b"VTXCUB64"]
        for p in sorted(pages):
            base = (f << 24) | (p << 16)
            h.append(p.to_bytes(4, "little"))
            h.append(b"".join(self.mem.get((e, base | j), 0).to_bytes(8, "little") for j in range(65536)))
            br = bytearray(16384)
            for j in range(65536):
                q = self.brin.get((e, base | j), 0)
                if q:
                    br[j // 4] |= q << (2 * (j % 4))
            h.append(bytes(br))
        try:
            ecrire_double(os.path.join(self.dossier, f"cube64-{e}-{f}.cub"), b"".join(h))
        except OSError:
            return M64
        return len(pages)

    # --- exécution
    def pas_unique(self):
        w = self.mem.get((0, self.pc), 0)
        op, d, s, t = w >> 48, (w >> 44) & 15, (w >> 40) & 15, (w >> 36) & 15
        imm = w & M32
        si = sext32(imm)
        S, T, D = self.r[s], self.r[t], self.r[d]
        suivant = (self.pc + 1) & M48
        if op == 0x00:
            pass
        elif op in (0x01, 0x06):
            y = T if op == 0x01 else si & M64
            x = S + y
            self.poser(d, x, x > M64)
        elif op in (0x02, 0x07, 0x0E, 0x0F):
            y = T if op in (0x02, 0x0E) else si & M64
            x = (S - y) & M64
            if op in (0x02, 0x07):
                self.ecrire(d, x)
            self.drapeaux(x, S < y)
        elif op == 0x03:
            self.poser(d, S * T)
        elif op == 0x4E:
            self.poser(d, (S * T) >> 64)
        elif op == 0x1E:
            self.poser(d, (signe64(S) * signe64(T)) >> 64)
        elif op in (0x0C, 0x0D):
            if T == 0:
                self.poser(d, M64 if op == 0x0C else S)
            else:
                self.poser(d, S // T if op == 0x0C else S % T)
        elif op in (0x1A, 0x1B):
            a, b = signe64(S), signe64(T)
            if b == 0:
                self.poser(d, M64 if op == 0x1A else S)
            else:
                q = abs(a) // abs(b)
                if (a < 0) != (b < 0):
                    q = -q
                self.poser(d, q if op == 0x1A else a - q * b)
        elif op == 0x04:
            self.poser(d, S << 2)
        elif op == 0x05:
            self.poser(d, S >> 2)
        elif op == 0x08:
            self.poser(d, S << (T & 63))
        elif op == 0x09:
            self.poser(d, S >> (T & 63))
        elif op == 0x17:
            self.poser(d, signe64(S) >> (T & 63))
        elif op in (0x14, 0x15, 0x16):
            self.poser(d, {0x14: S & T, 0x15: S | T, 0x16: S ^ T}[op])
        elif op == 0x12:
            self.poser(d, ~S)
        elif op == 0x0A:
            self.poser(d, self.mem.get((0, suivant), 0))
            suivant = (suivant + 1) & M48
        elif op == 0x18:
            self.poser(d, si)
        elif op == 0x19:
            self.poser(d, imm)
        elif op == 0x0B:
            self.ecrire(d, S)
        elif op == 0x1F:
            self.ecrire(d, (S & ~(3 << 62)) | ((imm & 3) << 62))
        elif op == 0x22:
            self.ecrire(d, (S & ~(3 << 62)) | ((T & 3) << 62))
        elif op == 0x1C:
            self.poser(d, S & M32)
        elif op == 0x1D:
            self.poser(d, sext32(S))
        elif op == 0x4C:
            x = S + T + int(self.c)
            self.poser(d, x, x > M64)
        elif op == 0x4D:
            y = T + int(self.c)
            self.poser(d, S - y, S < y)
        elif op == 0x50:
            self.poser(d, bin(S).count("1"))
        elif op in (0x10, 0x11, 0x13):
            f = {0x10: min, 0x11: max, 0x13: lambda x, y: (x + y) & 3}[op]
            self.poser(d, quits(f, S, T))
        elif op == 0x4F:
            x = S ^ T
            self.poser(d, ~(x | (x >> 1)) & F64)
        elif op == 0x56:
            self.poser(d, ((S & T) & V64) | ((S | T) & F64))
        elif op == 0x57:
            self.poser(d, ((S | T) & V64) | ((S & T) & F64))
        elif op in (0x58, 0x59):
            v = ((S & V64) >> 1) | ((S & F64) << 1)
            self.poser(d, v ^ M64 if op == 0x59 else v)
        elif op == 0x5A:
            self.poser(d, (S >> ((T & 31) * 2)) & 3)
        elif op == 0x54:
            self.poser(d, (self.lire(S + (T >> 5)) >> ((T & 31) * 2)) & 3)
        elif op == 0x55:
            a, k = (S + (T >> 5)) & M64, (T & 31) * 2
            self.ecrire_mem(a, (self.lire(a) & ~(3 << k)) | ((D & 3) << k))
        elif op == 0x38:
            self.poser(d, sum(((S >> (16 * k)) & 0xFFFF) * ((T >> (16 * k)) & 0xFFFF) for k in range(4)))
        elif op == 0x39:
            sp = self.r[14]
            n, wd, q, k, o = [self.mem.get((0, (sp + 4 - j) & M48), 0) for j in range(5)]
            qs = [self.lire(q + j) for j in range(wd)]
            for i in range(n):
                acc = 0
                for j in range(wd):
                    p = self.lire(k + i * wd + j)
                    acc += sum(((qs[j] >> (16 * m)) & 0xFFFF) * ((p >> (16 * m)) & 0xFFFF) for m in range(4))
                self.ecrire_mem(o + i, acc & M64)
        elif op == 0x20:
            self.poser(d, self.lire(S + si))
        elif op == 0x21:
            self.ecrire_mem(D + si, S)
        elif op == 0x29:
            self.poser(d, self.lire(S + T))
        elif op == 0x2A:
            self.ecrire_mem(D + T, S)
        elif op == 0x25:
            self.poser(d, self.lire((self.r[13] + si) & M48))
        elif op == 0x26:
            self.ecrire_mem((self.r[13] + si) & M48, D)
        elif op == 0x27:
            self.r[14] = (self.r[14] - 1) & M48
            self.ecrire_mem(self.r[14], S)
        elif op == 0x28:
            v = self.lire(self.r[14])
            self.r[14] = (self.r[14] + 1) & M48
            self.ecrire(d, v)
        elif op in (0x30, 0x31, 0x32, 0x35, 0x36, 0x33):
            saut = {0x30: True, 0x31: self.z, 0x32: not self.z, 0x35: self.c, 0x36: not self.c, 0x33: True}[op]
            if op == 0x33:
                self.r[14] = (self.r[14] - 1) & M48
                self.ecrire_mem(self.r[14], suivant)
            if saut:
                suivant = imm
        elif op == 0x34:
            suivant = self.lire(self.r[14]) & M48
            self.r[14] = (self.r[14] + 1) & M48
        elif op == 0x23:
            self.ecrire(d, self.entree.popleft() if self.entree else 0)
        elif op == 0x24:
            self.sortie.append(S)
        elif op == 0x51:
            self.poser(d, self.lire_canal(S))
        elif op == 0x52:
            self.ecrire_canal(T, S)
        elif op == 0x53:
            self.poser(d, self.service(S, T))
        elif op == 0x5E:
            q = si & 3
            for k in range(T):
                e, i = self.place(S + k)
                if q:
                    self.brin[(e, i)] = q
                else:
                    self.brin.pop((e, i), None)
        elif op == 0x5F:
            e, i = self.place(S)
            self.page_disque(e, i)
            self.poser(d, self.brin.get((e, i), 0))
        elif 0x40 <= op <= 0x4B or op in (0x5B, 0x5C, 0x5D, 0x6C, 0x6D):
            self.flottant(op, d, S, T)
        elif op == 0x69:
            self.poser(d, Q64.vers(Q32, S))
        elif 0x60 <= op <= 0x6A:
            self.flottant32(op, d, S & M32, T & M32)
        elif op == 0x3F:
            self.arrete = True
        else:
            raise Erreur(f"code d'opération inconnu : {op:#06x} à l'adresse {self.pc}")
        self.pc = suivant
        self.pas += 1

    def flottant(self, op, d, S, T):
        F = Q64
        if op == 0x40:
            v = F.add(S, T)
        elif op == 0x41:
            v = F.sub(S, T)
        elif op == 0x42:
            v = F.mul(S, T)
        elif op == 0x43:
            v = F.div(S, T)
        elif op == 0x47:
            v = F.racine(S)
        elif op in (0x44, 0x45, 0x46):
            c = F.cmp(S, T)
            v = int(c == 0) if op == 0x44 else int(c == 1) if op == 0x45 else int(c in (0, 1))
        elif op == 0x5D:
            v = F.cmp(S, T)
        elif op == 0x5B:
            v = F.neg(S)
        elif op == 0x5C:
            v = F.etat(S)
        elif op == 0x48:
            v = F.de_entier(S)
        elif op == 0x49:
            v = F.de_entier(signe64(S))
        elif op in (0x4A, 0x4B):
            v = F.vers_entier(S, op == 0x4B)
        elif op == 0x6C:
            v = vers_ieee64(S)
        else:
            v = de_ieee64(S)
        self.poser(d, v)

    def flottant32(self, op, d, S, T):
        F = Q32
        if op == 0x60:
            v = F.add(S, T)
        elif op == 0x61:
            v = F.sub(S, T)
        elif op == 0x62:
            v = F.mul(S, T)
        elif op == 0x63:
            v = F.div(S, T)
        elif op == 0x67:
            v = F.racine(S)
        elif op in (0x64, 0x65, 0x66):
            c = F.cmp(S, T)
            v = int(c == 0) if op == 0x64 else int(c == 1) if op == 0x65 else int(c in (0, 1))
        elif op == 0x6A:
            v = F.neg(S)
        elif op == 0x68:
            v = Q32.vers(Q64, S)
        else:
            raise Erreur(f"code d'opération inconnu : {op:#06x}")
        self.poser(d, v)

    def executer(self, max_pas=5_000_000):
        while not self.arrete:
            if self.pas >= max_pas:
                raise Erreur(f"limite de {max_pas} instructions atteinte")
            self.pas_unique()

    def ligne_corpus(self):
        mem = sorted(((e << 48) | i, v) for (e, i), v in self.mem.items() if e >= 1 and v)
        br = sorted(((e << 48) | i, q) for (e, i), q in self.brin.items() if q)
        s = f"{self.pas}|{','.join(map(str, self.sortie))}|{','.join(f'{k}:{v}' for k, v in mem)}"
        s += "|B:" + ",".join(f"{k}:{q}" for k, q in br)
        if self.texte:
            s += "|T:" + ",".join(map(str, self.texte))
        return s


def lancer(mots, entrees=(), max_pas=50_000_000):
    cpu = CPU()
    cpu.charger(mots)
    cpu.entree.extend(entrees)
    try:
        cpu.executer(max_pas)
    except Erreur as e:
        return f"ERREUR {e}"
    return cpu.ligne_corpus()


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "asm":
        mots = assembler(open(sys.argv[2], encoding="utf-8").read())
        print(lancer(mots, [int(x) for x in sys.argv[3:]]))
    elif len(sys.argv) >= 3 and sys.argv[1] == "corpus":
        for ligne in open(sys.argv[2]):
            ligne = ligne.strip()
            if not ligne:
                continue
            m, e = ligne.split(";")
            print(lancer([int(x) for x in m.split(",")], [int(x) for x in e.split(",")] if e else []))
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
