#!/usr/bin/env python3
"""Lugus, le SPU-128 : la machine de référence (Python) et son assembleur. Spécification : docs/specification-spu128.md.

Un mot = un point de matière #RRRRRRRR_VVVVVVVV_BBBBBBBB_MMMMMMMM (128 bits, 64 quits) : trois voies de couleur et la voie
de matière (l'état de Belnap, puis cinq codons : reflet, lumière, transparence, profondeur, rugosité). Un mot de code
porte deux instructions de 64 bits (opération 16 bits, d, s, t, w la largeur, imm 32 bits) ; PC compte les demi-mots.
Adresse : étage (bits 127-126), type, état, fréquence (119-24), #RRGGBB (23-0).

    python3 spu128.py asm  prog.s128      assemble et lance
    python3 spu128.py corpus FICHIER      une ligne par programme : « mots;entrées » -> « pas|sorties|mémoire »"""
import os
import re
import sys
from collections import deque

ici = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(ici), "spu64"))
from qflot import Q32, Q64, Q128, vers_ieee, de_ieee  # noqa: E402
from spu64 import ecrire_double, lire_double, noter_etat  # noqa: E402  (le miroir inversé et l'ombre)

M128 = (1 << 128) - 1
M120 = (1 << 120) - 1
M64 = (1 << 64) - 1
M32 = (1 << 32) - 1
PILE = 0x7FFFFFFF
LARGEUR = {0: 128, 1: 64, 2: 32}
FORMAT = {0: Q128, 1: Q64, 2: Q32}
ENTETE = b"VTXCU128"
# la voie de matière : (décalage, nombre de bits) de chaque codon ; 0 l'état, 1 à 5 les propriétés
CODONS = {0: (30, 2), 1: (24, 6), 2: (18, 6), 3: (12, 6), 4: (6, 6), 5: (0, 6)}

OPS = {
    "NOP": (0x00, "none"), "ADD": (0x01, "rrr"), "SUB": (0x02, "rrr"), "MUL": (0x03, "rrr"),
    "SHL4": (0x04, "rr"), "SHR4": (0x05, "rr"), "ADDI": (0x06, "rri"), "SUBI": (0x07, "rri"),
    "SHL": (0x08, "rrr"), "SHR": (0x09, "rrr"), "LDI": (0x0A, "ldi"), "MOV": (0x0B, "rr"),
    "DIV": (0x0C, "rrr"), "MOD": (0x0D, "rrr"), "CMP": (0x0E, "cmp"), "CMPI": (0x0F, "cmpi"),
    "MIN": (0x10, "rrr"), "MAX": (0x11, "rrr"), "CMP3": (0x12, "rr"), "ADDM4": (0x13, "rrr"),
    "AND": (0x14, "rrr"), "OR": (0x15, "rrr"), "XOR": (0x16, "rrr"), "SAR": (0x17, "rrr"),
    "LDIS": (0x18, "ri"), "LDIU": (0x19, "ri"), "DIVS": (0x1A, "rrr"), "MODS": (0x1B, "rrr"),
    "ZEXT": (0x1C, "rr"), "SEXT": (0x1D, "rr"), "MULHS": (0x1E, "rrr"), "ETG": (0x1F, "rri"), "ETGX": (0x22, "rrr"),
    "LD": (0x20, "mem"), "ST": (0x21, "mem"), "IN": (0x23, "in"), "OUT": (0x24, "out"),
    "LDF": (0x25, "off"), "STF": (0x26, "off"), "PUSH": (0x27, "out"), "POP": (0x28, "in"),
    "LDX": (0x29, "rrr"), "STX": (0x2A, "rrr"), "LDIH": (0x2B, "ldi"),
    "JMP": (0x30, "jump"), "JZ": (0x31, "jump"), "JNZ": (0x32, "jump"), "CALL": (0x33, "jump"),
    "RET": (0x34, "none"), "JC": (0x35, "jump"), "JNC": (0x36, "jump"),
    "GDOT": (0x38, "rrr"), "GEMV": (0x39, "none"), "HALT": (0x3F, "none"),
    "FADD": (0x40, "rrr"), "FSUB": (0x41, "rrr"), "FMUL": (0x42, "rrr"), "FDIV": (0x43, "rrr"),
    "FEQ": (0x44, "rrr"), "FLT": (0x45, "rrr"), "FLE": (0x46, "rrr"), "FSQRT": (0x47, "rr"),
    "ITOF": (0x48, "rri"), "ITOFS": (0x49, "rri"), "FTOI": (0x4A, "rri"), "FROUND": (0x4B, "rri"),
    "ADC": (0x4C, "rrr"), "SBC": (0x4D, "rrr"), "MULHU": (0x4E, "rrr"), "QEGAL": (0x4F, "rrr"), "COMPTE": (0x50, "rr"),
    "ENTC": (0x51, "rr"), "SORC": (0x52, "rrr"), "SYS": (0x53, "rrr"),
    "LDQ": (0x54, "rrr"), "STQ": (0x55, "rrr"),
    "ET4": (0x56, "rrr"), "OU4": (0x57, "rrr"), "NON4": (0x58, "rr"), "ANTI": (0x59, "rr"), "EXQ": (0x5A, "rrr"),
    "FNEG": (0x5B, "rr"), "FETAT": (0x5C, "rr"), "FCMP": (0x5D, "rrr"), "MARQUE": (0x5E, "marque"), "BRIN": (0x5F, "rr"),
    "FVIEEE": (0x6C, "rr"), "FDIEEE": (0x6D, "rr"), "FCONV": (0x6E, "rri"),
    "VADD": (0x80, "rrr"), "VSUB": (0x81, "rrr"), "VMUL": (0x82, "rrr"), "VMIN": (0x83, "rrr"), "VMAX": (0x84, "rrr"),
    "VFADD": (0x85, "rrr"), "VFSUB": (0x86, "rrr"), "VFMUL": (0x87, "rrr"), "VFDIV": (0x88, "rrr"),
    "VBCAST": (0x89, "rr"), "VEXT": (0x8A, "rrr"), "VINS": (0x8B, "rri"),
    "MATL": (0x90, "rrr"), "MATE": (0x91, "rrri"), "MELANGE": (0x92, "rrri"), "ANTIPOINT": (0x93, "rr"),
}
NOMS = {code: nom for nom, (code, _) in OPS.items()}


class Erreur(Exception):
    pass


def instr(op, d=0, s=0, t=0, imm=0, w=0):
    return (op << 48) | (d << 44) | (s << 40) | (t << 36) | (w << 32) | (imm & M32)


def entier(t):
    t = t.strip().lstrip("#").replace("_", "")
    if t.lower().startswith("0x"):
        return int(t, 16)
    if t.lower().startswith("0q"):
        return int(t[2:], 4)
    if t.lower().startswith("-"):
        return -entier(t[1:])
    return int(t)


def assembler(texte):
    """Assemble ; rend les mots de 128 bits (deux instructions par mot, la première en haut).

    Une ligne : « étiquette: OP args ; commentaire ». OP.64 ou OP.32 choisit la largeur (128 sans suffixe).
    « LDI rd, v » range une constante de 64 bits ; « LDI128 rd, v » une constante de 128 bits (LDI puis LDIH).
    « .MOT v, v… » range des mots entiers de 128 bits (alignés sur un mot) ; l'étiquette d'une ligne .MOT donne l'indice
    du mot, celle d'une instruction l'indice de la demi-instruction (pour les sauts)."""
    def taille(ligne):
        t0 = ligne.split()[0].upper().split(".")[0]
        if t0 == "LDI128":
            return 4
        return 2 if t0 in ("LDI", "LDIH") else 1

    etiquettes, lignes, h = {}, [], 0
    for brut in texte.splitlines():
        ligne = brut.split(";")[0].strip()
        noms = []
        while ":" in ligne:
            nom, ligne = ligne.split(":", 1)
            noms.append(nom.strip().upper())
            ligne = ligne.strip()
        if ligne and ligne.split()[0].upper() == ".MOT":
            h += h & 1
            for n in noms:
                etiquettes[n] = h // 2
            lignes.append(ligne)
            h += 2 * len(ligne.split(None, 1)[1].split(","))
            continue
        for n in noms:
            etiquettes[n] = h
        if ligne:
            lignes.append(ligne)
            h += taille(ligne)

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

    demis = []
    for ligne in lignes:
        parts = ligne.split(None, 1)
        mn = parts[0].upper()
        args = [a.strip() for a in parts[1].split(",")] if len(parts) > 1 else []
        if mn == ".MOT":
            if len(demis) & 1:
                demis.append(0)
            for a in args:
                v = val(a) & M128
                demis += [v >> 64, v & M64]
            continue
        nom, _, suffixe = mn.partition(".")
        w = {"": 0, "128": 0, "64": 1, "32": 2}.get(suffixe)
        if w is None:
            raise Erreur(f"largeur inconnue : {mn}")
        if nom == "LDI128":
            v = val(args[1]) & M128
            demis += [instr(0x0A, reg(args[0])), v & M64, instr(0x2B, reg(args[0])), v >> 64]
            continue
        if nom not in OPS:
            raise Erreur(f"instruction inconnue : {nom}")
        code, forme = OPS[nom]
        if forme == "none":
            demis.append(instr(code, w=w))
        elif forme == "rrr":
            demis.append(instr(code, reg(args[0]), reg(args[1]), reg(args[2]), w=w))
        elif forme == "rrri":
            demis.append(instr(code, reg(args[0]), reg(args[1]), reg(args[2]), imm32(val(args[3]), False), w=w))
        elif forme in ("rri", "mem"):
            signe = code not in (0x48, 0x49, 0x4A, 0x4B, 0x6E, 0x8B)
            demis.append(instr(code, reg(args[0]), reg(args[1]), 0, imm32(val(args[2]) if len(args) > 2 else 0, signe), w=w))
        elif forme == "rr":
            demis.append(instr(code, reg(args[0]), reg(args[1]), w=w))
        elif forme == "ri":
            demis.append(instr(code, reg(args[0]), 0, 0, imm32(val(args[1]), code == 0x18), w=w))
        elif forme == "cmp":
            demis.append(instr(code, 0, reg(args[0]), reg(args[1]), w=w))
        elif forme == "cmpi":
            demis.append(instr(code, 0, reg(args[0]), 0, imm32(val(args[1]), True), w=w))
        elif forme == "marque":
            demis.append(instr(code, 0, reg(args[0]), reg(args[1]), imm32(val(args[2]), True)))
        elif forme == "in":
            demis.append(instr(code, reg(args[0]), w=w))
        elif forme == "out":
            demis.append(instr(code, 0, reg(args[0]), w=w))
        elif forme == "off":
            demis.append(instr(code, reg(args[0]), 0, 0, imm32(val(args[1]), True)))
        elif forme == "jump":
            demis.append(instr(code, imm=imm32(val(args[0]), False)))
        elif forme == "ldi":
            demis.append(instr(code, reg(args[0])))
            demis.append(val(args[1]) & M64)
    if len(demis) & 1:
        demis.append(0)
    return [(demis[k] << 64) | demis[k + 1] for k in range(0, len(demis), 2)]


def signe(v, L):
    v &= (1 << L) - 1
    return v - (1 << L) if v >> (L - 1) else v


def quits(f, a, b, n):
    return sum(f((a >> (2 * k)) & 3, (b >> (2 * k)) & 3) << (2 * k) for k in range(n))


V128, F128 = int("AA" * 16, 16), int("55" * 16, 16)


def voies(x):
    return [(x >> (32 * k)) & M32 for k in range(4)]


def de_voies(v):
    return sum((x & M32) << (32 * k) for k, x in enumerate(v))


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
        self.pages_vues = set()
        self.pas = 0
        self.presenter = None

    def charger(self, mots):
        for i, w in enumerate(mots):
            self.mem[(0, i)] = w & M128

    # --- mémoire
    @staticmethod
    def place(adr):
        adr &= M128
        return adr >> 126, adr & M120

    def page_disque(self, e, i):
        if self.dossier is None:
            return
        cle = (e, i >> 16)
        if cle in self.pages_vues:
            return
        self.pages_vues.add(cle)
        f = i >> 24
        b, etat = lire_double(os.path.join(self.dossier, f"cube128-{e}-{f}.cub"), ENTETE)
        noter_etat(self, etat)
        if b is None:
            return
        k, voulue = 8, (i >> 16) & 255
        taille = 4 + 65536 * 16 + 16384
        while k + taille <= len(b):
            p = int.from_bytes(b[k:k + 4], "little")
            if p == voulue:
                base = (f << 24) | (p << 16)
                for j in range(65536):
                    v = int.from_bytes(b[k + 4 + 16 * j:k + 20 + 16 * j], "little")
                    q = (b[k + 4 + 65536 * 16 + j // 4] >> (2 * (j % 4))) & 3
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
            raise Erreur(f"écriture dans un mot ADN (fixé) à l'adresse étage {e}, #{i:030X}")
        self.mem[(e, i)] = v & M128

    def ecrire(self, d, v):
        if d:
            self.r[d] = v & M128

    def poser(self, d, v, c=False, L=128):
        v &= (1 << L) - 1
        self.ecrire(d, v)
        self.z, self.n, self.c = v == 0, (v >> (L - 1)) == 1, c

    # --- canaux et services
    def lire_canal(self, c):
        if c == 0:
            return self.entree.popleft() if self.entree else 0
        if c == 1:
            return self.texte_entree.popleft() if self.texte_entree else M128
        f = self.fichiers.get(c)
        if f is None or f[0] != "l" or f[2] >= len(f[1]):
            return M128
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
                return M128
            chemin = os.path.join(self.dossier, self.texte_memoire(arg))
            canal = max([1] + list(self.fichiers)) + 1
            if code == 1:
                try:
                    with open(chemin, encoding="utf-8") as h:
                        self.fichiers[canal] = ["l", [ord(ch) for ch in h.read()], 0, chemin]
                except OSError:
                    return M128
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
                    return M128
            return 0
        if code == 4:
            f = self.fichiers.get(arg)
            return 1 if f is None or f[0] != "l" or f[2] >= len(f[1]) else 0
        if code == 5:
            return int.from_bytes(os.urandom(16), "little")
        if code in (6, 7):
            if self.dossier is None:
                return M128
            e3 = 3 << 126
            chemin = os.path.join(self.dossier, self.texte_memoire(self.lire(e3 | 14680060)))
            a, n = self.lire(e3 | 14680061), self.lire(e3 | 14680062)
            try:
                if code == 6:
                    with open(chemin, "wb") as h:
                        h.write(b"".join(self.lire(a + k).to_bytes(16, "little") for k in range(n)))
                    return n
                with open(chemin, "rb") as h:
                    b = h.read()
            except OSError:
                return M128
            k = min(len(b) // 16, n)
            for j in range(k):
                self.ecrire_mem(a + j, int.from_bytes(b[16 * j:16 * j + 16], "little"))
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
            return 0
        if code == 22:
            etat = getattr(self, "_etat_disque", 0)
            self._etat_disque = 0
            return etat
        if code == 19:
            ancienne = self.__dict__.get("_cadence", 16)
            self._cadence = min(arg, 60000)
            return ancienne
        if code == 18:
            import time
            debut = self.__dict__.setdefault("_debut", time.monotonic())
            return int((time.monotonic() - debut) * 1000)
        return M128

    def jeter_cube(self, adr):
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
            return M128
        pages = {}
        for (ee, j), v in self.mem.items():
            if ee == e and j >> 24 == f and v:
                pages.setdefault((j >> 16) & 255, None)
        for (ee, j), q in self.brin.items():
            if ee == e and j >> 24 == f and q:
                pages.setdefault((j >> 16) & 255, None)
        h = [ENTETE]
        for p in sorted(pages):
            base = (f << 24) | (p << 16)
            h.append(p.to_bytes(4, "little"))
            h.append(b"".join(self.mem.get((e, base | j), 0).to_bytes(16, "little") for j in range(65536)))
            br = bytearray(16384)
            for j in range(65536):
                q = self.brin.get((e, base | j), 0)
                if q:
                    br[j // 4] |= q << (2 * (j % 4))
            h.append(bytes(br))
        try:
            ecrire_double(os.path.join(self.dossier, f"cube128-{e}-{f}.cub"), b"".join(h))
        except OSError:
            return M128
        return len(pages)

    # --- exécution
    def demi(self, p):
        """La demi-instruction n° p : la moitié haute du mot p / 2 si p est pair, la basse sinon."""
        w = self.mem.get((0, (p >> 1) & M120), 0)
        return (w >> 64) if p & 1 == 0 else w & M64

    def pas_unique(self):
        h = self.demi(self.pc)
        op, d, s, t, wl = h >> 48, (h >> 44) & 15, (h >> 40) & 15, (h >> 36) & 15, (h >> 32) & 15
        imm = h & M32
        si = imm - (1 << 32) if imm >> 31 else imm
        if wl not in LARGEUR:
            raise Erreur(f"largeur {wl} refusée à la demi-instruction {self.pc}")
        L = LARGEUR[wl]
        m = (1 << L) - 1
        S, T, D = self.r[s], self.r[t], self.r[d]
        Sm, Tm = S & m, T & m
        suivant = (self.pc + 1) & M120
        nq = L // 2
        if op == 0x00:
            pass
        elif op in (0x01, 0x06):
            y = Tm if op == 0x01 else si & m
            x = Sm + y
            self.poser(d, x, x > m, L)
        elif op in (0x02, 0x07, 0x0E, 0x0F):
            y = Tm if op in (0x02, 0x0E) else si & m
            x = (Sm - y) & m
            if op in (0x02, 0x07):
                self.ecrire(d, x)
            self.z, self.n, self.c = x == 0, (x >> (L - 1)) == 1, Sm < y
        elif op == 0x03:
            self.poser(d, Sm * Tm, False, L)
        elif op == 0x4E:
            self.poser(d, (Sm * Tm) >> L, False, L)
        elif op == 0x1E:
            self.poser(d, (signe(Sm, L) * signe(Tm, L)) >> L, False, L)
        elif op in (0x0C, 0x0D):
            if Tm == 0:
                self.poser(d, m if op == 0x0C else Sm, False, L)
            else:
                self.poser(d, Sm // Tm if op == 0x0C else Sm % Tm, False, L)
        elif op in (0x1A, 0x1B):
            a, b = signe(Sm, L), signe(Tm, L)
            if b == 0:
                self.poser(d, m if op == 0x1A else Sm, False, L)
            else:
                q = abs(a) // abs(b)
                if (a < 0) != (b < 0):
                    q = -q
                self.poser(d, q if op == 0x1A else a - q * b, False, L)
        elif op == 0x04:
            self.poser(d, Sm << 2, False, L)
        elif op == 0x05:
            self.poser(d, Sm >> 2, False, L)
        elif op == 0x08:
            self.poser(d, Sm << (T & (L - 1)), False, L)
        elif op == 0x09:
            self.poser(d, Sm >> (T & (L - 1)), False, L)
        elif op == 0x17:
            self.poser(d, signe(Sm, L) >> (T & (L - 1)), False, L)
        elif op in (0x14, 0x15, 0x16):
            self.poser(d, {0x14: Sm & Tm, 0x15: Sm | Tm, 0x16: Sm ^ Tm}[op], False, L)
        elif op == 0x12:
            self.poser(d, ~Sm, False, L)
        elif op == 0x1C:
            self.poser(d, Sm)
        elif op == 0x1D:
            self.poser(d, signe(Sm, L))
        elif op == 0x4C:
            x = Sm + Tm + int(self.c)
            self.poser(d, x, x > m, L)
        elif op == 0x4D:
            y = Tm + int(self.c)
            self.poser(d, Sm - y, Sm < y, L)
        elif op == 0x50:
            self.poser(d, bin(Sm).count("1"))
        elif op in (0x0A, 0x2B):
            k = self.demi(suivant)
            self.poser(d, k if op == 0x0A else (k << 64) | (D & M64))
            suivant = (suivant + 1) & M120
        elif op == 0x18:
            self.poser(d, si)
        elif op == 0x19:
            self.poser(d, imm)
        elif op == 0x0B:
            self.ecrire(d, S)
        elif op == 0x1F:
            self.ecrire(d, (S & ~(3 << 126)) | ((imm & 3) << 126))
        elif op == 0x22:
            self.ecrire(d, (S & ~(3 << 126)) | ((T & 3) << 126))
        # --- quaternaire
        elif op in (0x10, 0x11, 0x13):
            f = {0x10: min, 0x11: max, 0x13: lambda x, y: (x + y) & 3}[op]
            self.poser(d, quits(f, Sm, Tm, nq), False, L)
        elif op == 0x4F:
            x = Sm ^ Tm
            self.poser(d, ~(x | (x >> 1)) & F128 & m, False, L)
        elif op == 0x56:
            self.poser(d, ((Sm & Tm) & V128) | ((Sm | Tm) & F128), False, L)
        elif op == 0x57:
            self.poser(d, ((Sm | Tm) & V128) | ((Sm & Tm) & F128), False, L)
        elif op in (0x58, 0x59):
            v = ((Sm & V128) >> 1) | ((Sm & F128) << 1)
            self.poser(d, v ^ m if op == 0x59 else v, False, L)
        elif op == 0x5A:
            self.poser(d, (Sm >> ((T & (nq - 1)) * 2)) & 3)
        elif op == 0x54:
            self.poser(d, (self.lire(S + (T >> 6)) >> ((T & 63) * 2)) & 3)
        elif op == 0x55:
            a, k = (S + (T >> 6)) & M128, (T & 63) * 2
            self.ecrire_mem(a, (self.lire(a) & ~(3 << k)) | ((D & 3) << k))
        elif op == 0x38:
            self.poser(d, sum(x * y for x, y in zip(voies(S), voies(T))))
        elif op == 0x39:
            sp = self.r[14]
            n, wd, q, k, o = [self.mem.get((0, (sp + 4 - j) & M120), 0) for j in range(5)]
            qs = [voies(self.lire(q + j)) for j in range(wd)]
            for i in range(n):
                acc = 0
                for j in range(wd):
                    acc += sum(x * y for x, y in zip(qs[j], voies(self.lire(k + i * wd + j))))
                self.ecrire_mem(o + i, acc & M128)
        # --- mémoire, pile, sauts, canaux, brin
        elif op == 0x20:
            self.poser(d, self.lire(S + si))
        elif op == 0x21:
            self.ecrire_mem(D + si, S)
        elif op == 0x29:
            self.poser(d, self.lire(S + T))
        elif op == 0x2A:
            self.ecrire_mem(D + T, S)
        elif op == 0x25:
            self.poser(d, self.lire((self.r[13] + si) & M120))
        elif op == 0x26:
            self.ecrire_mem((self.r[13] + si) & M120, D)
        elif op == 0x27:
            self.r[14] = (self.r[14] - 1) & M120
            self.ecrire_mem(self.r[14], S)
        elif op == 0x28:
            v = self.lire(self.r[14])
            self.r[14] = (self.r[14] + 1) & M120
            self.ecrire(d, v)
        elif op in (0x30, 0x31, 0x32, 0x35, 0x36, 0x33):
            saut = {0x30: True, 0x31: self.z, 0x32: not self.z, 0x35: self.c, 0x36: not self.c, 0x33: True}[op]
            if op == 0x33:
                self.r[14] = (self.r[14] - 1) & M120
                self.ecrire_mem(self.r[14], suivant)
            if saut:
                suivant = imm
        elif op == 0x34:
            suivant = self.lire(self.r[14]) & M120
            self.r[14] = (self.r[14] + 1) & M120
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
        # --- flottants quaternaires
        elif 0x40 <= op <= 0x4B or op in (0x5B, 0x5C, 0x5D, 0x6C, 0x6D, 0x6E):
            self.flottant(op, d, S, T, wl, imm)
        # --- les voies
        elif 0x80 <= op <= 0x8B:
            a, b = voies(S), voies(T)
            if op == 0x80:
                v = de_voies([x + y for x, y in zip(a, b)])
            elif op == 0x81:
                v = de_voies([x - y for x, y in zip(a, b)])
            elif op == 0x82:
                v = de_voies([x * y for x, y in zip(a, b)])
            elif op == 0x83:
                v = de_voies([min(x, y) for x, y in zip(a, b)])
            elif op == 0x84:
                v = de_voies([max(x, y) for x, y in zip(a, b)])
            elif 0x85 <= op <= 0x88:
                f = {0x85: Q32.add, 0x86: Q32.sub, 0x87: Q32.mul, 0x88: Q32.div}[op]
                v = de_voies([f(x, y) for x, y in zip(a, b)])
            elif op == 0x89:
                v = de_voies([S & M32] * 4)
            elif op == 0x8A:
                v = a[T & 3]
            else:
                c = voies(D)
                c[imm & 3] = S & M32
                v = de_voies(c)
            self.poser(d, v)
        # --- la matière
        elif op == 0x90:
            k = T & 7
            self.poser(d, (S >> CODONS[k][0]) & ((1 << CODONS[k][1]) - 1) if k in CODONS else 0)
        elif op == 0x91:
            k = imm & 7
            if k in CODONS:
                dec, nb = CODONS[k]
                mk = ((1 << nb) - 1) << dec
                self.poser(d, (S & ~mk) | ((T << dec) & mk))
            else:
                self.poser(d, S)
        elif op == 0x92:
            p = min(imm & 511, 256)
            a, b = voies(S), voies(T)
            coul = [(a[k] * (256 - p) + b[k] * p) >> 8 for k in (1, 2, 3)]
            mat = (((a[0] >> 30) | (b[0] >> 30)) & 3) << 30
            for k in range(1, 6):
                dec, nb = CODONS[k]
                x, y = (a[0] >> dec) & 63, (b[0] >> dec) & 63
                mat |= ((x * (256 - p) + y * p) >> 8) << dec
            self.poser(d, de_voies([mat] + coul))
        elif op == 0x93:
            self.poser(d, S ^ (((1 << 96) - 1) << 32))
        elif op == 0x3F:
            self.arrete = True
        else:
            raise Erreur(f"code d'opération inconnu : {op:#06x} à la demi-instruction {self.pc}")
        self.pc = suivant
        self.pas += 1

    def flottant(self, op, d, S, T, wl, imm):
        F = FORMAT[wl]
        brut = S                                   # S tel quel : la source d'une conversion
        S, T = S & F.masque, T & F.masque
        li = LARGEUR.get(imm & 3, 128)
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
        elif op in (0x48, 0x49):
            x = brut & ((1 << li) - 1)
            v = F.de_entier(signe(x, li) if op == 0x49 else x)
        elif op in (0x4A, 0x4B):
            v = F.vers_entier(S, op == 0x4B, li)
        elif op == 0x6E:
            G = FORMAT.get(imm & 3, Q128)
            v = G.vers(F, brut & G.masque)
        elif op == 0x6C:
            v = vers_ieee(F, S, F.taille)
        else:
            v = de_ieee(F, brut & ((1 << F.taille) - 1), F.taille)
        self.poser(d, v)

    def executer(self, max_pas=5_000_000):
        while not self.arrete:
            if self.pas >= max_pas:
                raise Erreur(f"limite de {max_pas} instructions atteinte")
            self.pas_unique()

    def ligne_corpus(self):
        mem = sorted(((e << 120) | i, v) for (e, i), v in self.mem.items() if e >= 1 and v)
        br = sorted(((e << 120) | i, q) for (e, i), q in self.brin.items() if q)
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
