#!/usr/bin/env python3
"""vtx 0.3 : chaîne Vercintorix (langage, compilateur, assembleur, émulateur du SPU).

Nouveautés de la 0.2 (voir vtx-carnet.md) :
  - étage variable  @(e)[a]          - opérateurs && || ! avec court-circuit, moins unaire
  - boucle          pour i dans a..b - constantes   constante N = 5;
  - données         donnees @2[0] = { ... };  (écrites une seule fois au premier lancement)
  - prélude         abs inf sup min max poids gdotn copier melange (inclus seulement s'ils sont appelés)
  - gemv(n, w, q, k, o) : produit matrice × vecteur en une instruction (étage 2)
  - division par zéro : x / 0 = 0xFFFFFFFF et x % 0 = x (comme RISC-V), plus d'arrêt brutal
  - priorité : les opérateurs bit à bit lient plus fort que les comparaisons (comme en Rust)
  - instrumentation : commande profil (histogramme des instructions, GDOT, accès par étage)
  - compilateur : fonctions inutiles élaguées, conditions compilées en sauts directs

Utilisation :
  python3 vtx.py run prog.vtx [entrées...]     python3 vtx.py profil prog.vtx [entrées...]
  python3 vtx.py compile prog.vtx              python3 vtx.py asm prog.vtx        python3 vtx.py test
  python3 vtx.py trace prog.vtx [entrées...] [--de N] [--max N] [--arret ADRESSE] [--regs]   (une ligne par instruction)
  python3 vtx.py deboguer prog.vtx [entrées...]   (débogueur interactif au niveau du source : pas, points d'arrêt, variables)
  python3 vtx.py partition prog.vtx [entrées...]  (partition automatique des tâches : accords, mesures, notes, temps gagné)
"""
import bisect
import math
import os
import random
import re
import struct
import sys
from collections import deque, Counter

MASK = 0xFFFFFFFF
STACK_TOP = 0x7FFFFF
FLAG = 16777215  # drapeau d'initialisation des données : étage 3, dernière adresse

OPS = {
    "NOP": (0x00, "none"), "ADD": (0x01, "rrr"), "SUB": (0x02, "rrr"), "MUL": (0x03, "rrr"),
    "SHL4": (0x04, "rr"), "SHR4": (0x05, "rr"), "ADDI": (0x06, "rri"), "SUBI": (0x07, "rri"),
    "SHL": (0x08, "rrr"), "SHR": (0x09, "rrr"), "LDI": (0x0A, "ldi"), "MOV": (0x0B, "rr"),
    "DIV": (0x0C, "rrr"), "MOD": (0x0D, "rrr"), "CMP": (0x0E, "cmp"),
    "MIN": (0x10, "rrr"), "MAX": (0x11, "rrr"), "CMP3": (0x12, "rr"), "ADDM4": (0x13, "rrr"),
    "AND": (0x14, "rrr"), "OR": (0x15, "rrr"), "XOR": (0x16, "rrr"),
    "LD": (0x20, "mem"), "ST": (0x21, "mem"), "DMA": (0x22, "mem"), "IN": (0x23, "in"),
    "OUT": (0x24, "out"), "LDF": (0x25, "off"), "STF": (0x26, "off"), "PUSH": (0x27, "out"),
    "POP": (0x28, "in"), "LDX": (0x29, "rrr"), "STX": (0x2A, "rrr"),
    "JMP": (0x30, "jump"), "JZ": (0x31, "jump"), "JNZ": (0x32, "jump"), "CALL": (0x33, "jump"),
    "RET": (0x34, "none"), "JC": (0x35, "jump"), "JNC": (0x36, "jump"),
    "GDOT": (0x38, "rrr"), "GEMV": (0x39, "none"), "HALT": (0x3F, "none"),
    # flottants IEEE 754 binary32 (arrondi au plus proche pair, NaN rendu sous la forme 0x7FC00000)
    "FADD": (0x40, "rrr"), "FSUB": (0x41, "rrr"), "FMUL": (0x42, "rrr"), "FDIV": (0x43, "rrr"),
    "FEQ": (0x44, "rrr"), "FLT": (0x45, "rrr"), "FLE": (0x46, "rrr"), "FSQRT": (0x47, "rr"),
    "ITOF": (0x48, "rr"), "ITOFS": (0x49, "rr"), "FTOI": (0x4A, "rr"), "FROUND": (0x4B, "rr"),
    # 64 bits par paires de mots : addition et soustraction avec retenue, partie haute du produit non signé
    "ADC": (0x4C, "rrr"), "SBC": (0x4D, "rrr"), "MULHU": (0x4E, "rrr"),
    # quaternaire : égalité quit par quit (1 dans le bit bas de chaque quit égal), nombre de bits à 1
    "QEGAL": (0x4F, "rrr"), "COMPTE": (0x50, "rr"),
    # canaux d'entrée et de sortie (0 : nombres, comme IN et OUT ; 1 : console en texte ; 2 et suivants : fichiers)
    # et services de la machine hôte (SYS : 1 ouvrir en lecture, 2 ouvrir en écriture, 3 fermer, 4 fin atteinte ?,
    # 5 bruit : 32 bits imprévisibles de la machine hôte)
    "ENTC": (0x51, "rr"), "SORC": (0x52, "rrr"), "SYS": (0x53, "rrr"),
    # quaternaire : un quit d'un tableau rangé (16 quits par mot, le quit 0 dans les bits bas) ; adresse du mot :
    # Rs + (Rt >> 4), place dans le mot : (Rt & 15) × 2. LDQ Rd,Rs,Rt,@e lit le quit dans Rd ; STQ y écrit Rd & 3
    "LDQ": (0x54, "memq"), "STQ": (0x55, "memq"),
    # logique de Belnap sur les 16 quits d'un mot (bit haut de chaque quit : la preuve du vrai, bit bas : celle du faux) :
    # ET4 (v = v1 & v2, f = f1 | f2), OU4 (l'inverse), NON4 (échange v et f), ANTI (NON4 puis complément) ;
    # EXQ Rd,Rs,Rt : le quit Rt & 15 de Rs
    "ET4": (0x56, "rrr"), "OU4": (0x57, "rrr"), "NON4": (0x58, "rr"), "ANTI": (0x59, "rr"), "EXQ": (0x5A, "rrr"),
    # flottants IEEE 754 binary64 : un flottant de 64 bits occupe une paire de registres (Rn, Rn+3), mot bas puis mot
    # haut, comme les longs du compilateur (R1:R4, R2:R5). Arrondi au plus proche pair ; tout NaN rendu sous la forme
    # 0x7FF8000000000000. DEQ, DLT, DLE, DTOI et DROUND rendent un seul mot ; les autres écrivent une paire.
    "DADD": (0x5B, "rrr"), "DSUB": (0x5C, "rrr"), "DMUL": (0x5D, "rrr"), "DDIV": (0x5E, "rrr"), "DSQRT": (0x5F, "rr"),
    "DEQ": (0x60, "rrr"), "DLT": (0x61, "rrr"), "DLE": (0x62, "rrr"),
    "ITOD": (0x63, "rr"), "ITODS": (0x64, "rr"), "DTOI": (0x65, "rr"), "DROUND": (0x66, "rr"),
    "FTOD": (0x67, "rr"), "DTOF": (0x68, "rr"), "LTOD": (0x69, "rr"), "DTOL": (0x6A, "rr"), "DTOLR": (0x6B, "rr"),
}
NOMS = {code: nom for nom, (code, _) in OPS.items()}


class VtxError(Exception):
    pass


def mot(op, g, b, etage=0):
    return (op << 24) | (g << 16) | (b << 8) | 0x10 | ((etage & 3) << 6)


def quits(w):
    q = [(w >> (30 - 2 * i)) & 3 for i in range(16)]
    return " ".join("".join(str(d) for d in q[k:k + 4]) for k in range(0, 16, 4))


def entier(s):
    s = s.strip().lstrip("#")
    signe = -1 if s.startswith("-") else 1
    s = s.lstrip("-")
    if s.lower().startswith("0x"):
        return signe * int(s[2:], 16)
    if s.lower().startswith("0q"):
        return signe * int(s[2:], 4)
    return signe * int(s)


DIRECTIVES = (".LIGNE", ".FONCTION", ".VAR", ".TACHE", ".ACCORD_FIN")


def assembler(texte):
    return _assembler(texte)[0]


def _assembler(texte):
    """Assemble ; rend aussi les directives de débogage (adresse, texte) et les étiquettes."""
    etiquettes, lignes, adr, infos = {}, [], 0, []
    for brut in texte.splitlines():
        ligne = brut.split(";")[0].strip()
        if ligne and ligne.split()[0].upper() in DIRECTIVES:
            infos.append((adr, ligne))
            continue
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
            raise VtxError(f"registre invalide : {s}")
        return int(m.group(1))

    mots = []
    for ligne in lignes:
        parts = ligne.split(None, 1)
        nom = parts[0].upper()
        args = [a.strip() for a in parts[1].split(",")] if len(parts) > 1 else []
        if nom == ".MOT":
            mots.extend(entier(a) & MASK for a in args)
            continue
        if nom not in OPS:
            raise VtxError(f"instruction inconnue : {nom}")
        code, forme = OPS[nom]
        if forme == "none":
            mots.append(mot(code, 0, 0))
        elif forme == "rrr":
            mots.append(mot(code, (reg(args[0]) << 4) | reg(args[1]), reg(args[2]) << 4))
        elif forme == "rri":
            imm = entier(args[2])
            if not 0 <= imm <= 255:
                raise VtxError(f"immédiat hors de 0 à 255 : {imm}")
            mots.append(mot(code, (reg(args[0]) << 4) | reg(args[1]), imm))
        elif forme == "rr":
            mots.append(mot(code, (reg(args[0]) << 4) | reg(args[1]), 0))
        elif forme == "cmp":
            mots.append(mot(code, reg(args[0]), reg(args[1]) << 4))
        elif forme == "mem":
            etage = int(args[2].lstrip("@")) if len(args) == 3 else 0
            mots.append(mot(code, (reg(args[0]) << 4) | reg(args[1]), 0, etage))
        elif forme == "memq":
            etage = int(args[3].lstrip("@")) if len(args) == 4 else 0
            mots.append(mot(code, (reg(args[0]) << 4) | reg(args[1]), reg(args[2]) << 4, etage))
        elif forme == "in":
            mots.append(mot(code, reg(args[0]) << 4, 0))
        elif forme == "out":
            mots.append(mot(code, reg(args[0]), 0))
        elif forme == "off":
            off = entier(args[1])
            if not -128 <= off <= 127:
                raise VtxError(f"décalage hors de -128 à 127 : {off}")
            mots.append(mot(code, reg(args[0]) << 4, off & 255))
        elif forme == "jump":
            cible = etiquettes.get(args[0].upper())
            if cible is None:
                cible = entier(args[0])
            if not 0 <= cible < 1 << 20:
                raise VtxError(f"saut hors de portée (plus d'un million de mots de code) : {cible}")
            # adresse sur 20 bits : g et b, puis les 4 bits bas du dernier octet (le code dépasse 65 536 mots)
            mots.append(mot(code, (cible >> 8) & 255, cible & 255) | (cible >> 16))
        elif forme == "ldi":
            mots.append(mot(code, reg(args[0]) << 4, 0))
            mots.append((etiquettes[args[1].upper()] if args[1].upper() in etiquettes else entier(args[1])) & MASK)
    return mots, infos, etiquettes


F32_MAX_LIM = 2.0 ** 128 - 2.0 ** 103   # au-delà, l'arrondi vers binary32 donne l'infini


def f32(bits):
    """Mot de 32 bits -> valeur flottante binary32 (exacte en double)."""
    return struct.unpack("<f", struct.pack("<I", bits & MASK))[0]


def bits32(x):
    """Double -> mot binary32 arrondi au plus proche pair ; NaN unique 0x7FC00000.
    Pour +, -, *, / et la racine, calculer en double puis arrondir une fois donne le résultat binary32 exact."""
    if x != x:
        return 0x7FC00000
    try:
        return struct.unpack("<I", struct.pack("<f", x))[0]
    except OverflowError:
        return 0xFF800000 if x < 0 else 0x7F800000


NAN64 = 0x7FF8000000000000


def f64(lo, hi):
    """Deux mots (bas, haut) -> valeur flottante binary64."""
    return struct.unpack("<d", struct.pack("<Q", ((hi & MASK) << 32) | (lo & MASK)))[0]


def bits64(x):
    """Flottant binary64 -> entier de 64 bits ; NaN unique 0x7FF8000000000000."""
    if x != x:
        return NAN64
    return struct.unpack("<Q", struct.pack("<d", x))[0]


# ---- flottant_petuar : le flottant quaternaire de 128 bits (4 points du cube #RRGGBBAA, 32 chiffres hex, 64 quits)
# quit 63 : l'état en logique de Belnap (A 0 inconnu, C 1 négatif, G 2 positif, T/U 3 variable) ; quits 62 à 56 :
# l'exposant en base 4 (biais 8192 ; 16383 : l'infini) ; quits 55 à 0 : la mantisse, 56 chiffres en base 4, le premier
# non nul (sauf à l'exposant 0, les sous-normaux). Valeur : mantisse × 4^(exposant − 8247).
PQ_VARIABLE = 3 << 126


def petuar_signe(s):
    return (1 if s else 2) << 126


def petuar_arrondi(v):
    """Fraction v > 0 -> exposant << 112 | mantisse, au plus proche (pair au milieu)."""
    from fractions import Fraction
    q = (v.numerator.bit_length() - v.denominator.bit_length()) // 2 - 56
    while Fraction(4) ** (q + 56) <= v:
        q += 1
    while Fraction(4) ** (q + 55) > v:
        q -= 1
    q = max(q, 1 - 8247)
    t = v / Fraction(4) ** q
    n = t.numerator // t.denominator
    r = t - n
    if r > Fraction(1, 2) or (r == Fraction(1, 2) and n & 1):
        n += 1
    if n == 1 << 112:
        n, q = 1 << 110, q + 1
    if n < 1 << 110:
        return n
    if q + 8247 >= 16383:
        return 16383 << 112
    return ((q + 8247) << 112) | n


def bits_petuar_decimal(t, ligne=0):
    """Nombre décimal écrit (sans le Q) -> les 128 bits du flottant_petuar le plus proche."""
    from fractions import Fraction
    m = re.fullmatch(r"(\d+)(?:\.(\d+))?(?:[eE]([-+]?\d+))?", t)
    chiffres = m.group(1) + (m.group(2) or "")
    k = int(m.group(3) or 0) - len(m.group(2) or "")
    n = int(chiffres)
    if n == 0:
        return petuar_signe(0)
    ordre = k + len(str(n))
    if ordre > 5000:
        raise VtxError(f"ligne {ligne} : nombre flottant_petuar trop grand")
    if ordre < -5000:
        return petuar_signe(0)
    v = Fraction(n) * Fraction(10) ** k
    b = petuar_arrondi(v)
    if b >> 112 == 16383:
        raise VtxError(f"ligne {ligne} : nombre flottant_petuar trop grand")
    return petuar_signe(0) | b


def petuar_neg(b):
    return b ^ (3 << 126) if (b >> 126) in (1, 2) else b


def petuar_valeur(b):
    """Les 128 bits -> (état, Fraction ou None) : pour le débogueur et les tests."""
    from fractions import Fraction
    et, e, m = b >> 126, (b >> 112) & 16383, b & ((1 << 112) - 1)
    if et in (0, 3):
        return et, None
    if e == 16383:
        return et, None
    v = Fraction(m) * Fraction(4) ** (max(e, 1) - 8247)
    return et, (-v if et == 1 else v)


def sature64(t):
    """Entier signé -> 64 bits (complément à deux), saturé à l'intervalle des entiers signés de 64 bits."""
    if t >= 2 ** 63:
        return 0x7FFFFFFFFFFFFFFF
    if t < -2 ** 63:
        return 0x8000000000000000
    return t & 0xFFFFFFFFFFFFFFFF


def sature32(t):
    """Entier signé -> mot, saturé à l'intervalle des entiers signés de 32 bits."""
    if t >= 2 ** 31:
        return 0x7FFFFFFF
    if t < -2 ** 31:
        return 0x80000000
    return t & MASK


class CPU:
    def __init__(self):
        self.r = [0] * 16
        self.r[14] = STACK_TOP
        self.pc = 0
        self.z = self.c = self.n = False
        self.halted = False
        self.mem = {}
        self.entree = deque()
        self.sortie = []
        self.pas = 0
        self.ops = Counter()
        self.ld = [0, 0, 0, 0]
        self.st = [0, 0, 0, 0]
        self.mac = 0
        self.sur_pas = None
        self.texte = []                   # canal 1 : caractères écrits sur la console
        self.texte_entree = deque()       # canal 1 : caractères à lire
        self.fichiers = {}                # canal -> [mode, caractères, position, nom]
        self.dossier_fichiers = None      # None : pas d'accès aux fichiers (corpus, tests)
        self.frequences = [0, 0, 0, 0]    # la fréquence (le cube) que regarde chaque étage
        self.cubes = {}                   # (étage, fréquence) -> cases rangées

    def charger(self, mots):
        for i, w in enumerate(mots):
            self.mem[(0, i)] = w

    # --- canaux et services (instructions ENTC, SORC, SYS)
    def lire_canal(self, c):
        if c == 0:
            return self.entree.popleft() if self.entree else 0
        if c == 1:
            return self.texte_entree.popleft() if self.texte_entree else MASK
        f = self.fichiers.get(c)
        if f is None or f[0] != "l" or f[2] >= len(f[1]):
            return MASK
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
        et, off = (adr >> 24) & 3, adr & 0xFFFFFF
        n = self.mem.get((et, off), 0)
        return "".join(chr(self.mem.get((et, (off + 1 + i) & 0xFFFFFF), 0) & 0x1FFFFF) for i in range(min(n, 4096)))

    def chemin_cube(self, e, f):
        return os.path.join(self.dossier_fichiers, f"cube-{e}-{f}.cub")

    def cube_vers_disque(self, e, f, mots):
        """Un cube sur disque : « VTXCUB01 », puis pour chaque page non nulle son numéro (u32) et ses 65 536 mots."""
        pages = {}
        for (_, a), v in mots.items():
            if v:
                pages.setdefault(a >> 16, []).append((a & 0xFFFF, v))
        try:
            with open(self.chemin_cube(e, f), "wb") as h:
                h.write(b"VTXCUB01")
                for k in sorted(pages):
                    page = [0] * 65536
                    for o, v in pages[k]:
                        page[o] = v
                    h.write(k.to_bytes(4, "little") + b"".join(v.to_bytes(4, "little") for v in page))
        except OSError:
            return None
        return len(pages)

    def cube_depuis_disque(self, e, f):
        if self.dossier_fichiers is None:
            return None
        try:
            with open(self.chemin_cube(e, f), "rb") as h:
                b = h.read()
        except OSError:
            return None
        if b[:8] != b"VTXCUB01":
            return None
        r, i = {}, 8
        while i + 4 + 262144 <= len(b):
            k = int.from_bytes(b[i:i + 4], "little")
            for j in range(65536):
                v = int.from_bytes(b[i + 4 + 4 * j:i + 8 + 4 * j], "little")
                if v:
                    r[(e, (k << 16) | j)] = v
            i += 4 + 262144
        return r

    def service(self, code, arg):
        if code in (1, 2):
            if self.dossier_fichiers is None:
                return MASK
            nom = self.texte_memoire(arg)
            chemin = os.path.join(self.dossier_fichiers, nom)
            if code == 1:
                try:
                    with open(chemin, encoding="utf-8") as h:
                        contenu = [ord(c) for c in h.read()]
                except OSError:
                    return MASK
                canal = max([1] + list(self.fichiers)) + 1
                self.fichiers[canal] = ["l", contenu, 0, chemin]
            else:
                canal = max([1] + list(self.fichiers)) + 1
                self.fichiers[canal] = ["e", [], 0, chemin]
            return canal
        if code == 5:
            return int.from_bytes(os.urandom(4), "little")
        if code == 8:
            # accorder l'étage e sur la fréquence f (argument f * 4 + e) : ses cases sont rangées sous l'ancienne
            # fréquence, celles du cube f reviennent
            e, f = arg & 3, arg >> 2
            if e == 0:
                return MASK                   # l'étage 0 porte le code et la pile : il ne change pas de cube
            ancienne = self.frequences[e]
            if ancienne != f:
                rangees = {k: v for k, v in self.mem.items() if k[0] == e}
                for k in rangees:
                    del self.mem[k]
                if rangees:
                    self.cubes[(e, ancienne)] = rangees
                    budget = os.environ.get("VTX_CUBES_PAGES")
                    if budget and self.dossier_fichiers is not None:
                        # au-delà du budget de pages en mémoire, le cube quitté va au disque (comme la machine Rust)
                        pages = sum(len({k[1] >> 16 for k, v in c.items() if v}) for c in self.cubes.values())
                        if pages > int(budget) and self.cube_vers_disque(e, ancienne, self.cubes[(e, ancienne)]) is not None:
                            del self.cubes[(e, ancienne)]
                retrouve = self.cubes.pop((e, f), None)
                if retrouve is None:
                    retrouve = self.cube_depuis_disque(e, f)
                self.mem.update(retrouve or {})
                self.frequences[e] = f
            return ancienne
        if code == 9:
            return self.frequences[arg & 3]
        if code == 11:
            # écrire sur disque le cube de fréquence f de l'étage e (argument f * 4 + e) ; un cube rangé quitte la mémoire
            e, f = arg & 3, arg >> 2
            if e == 0 or self.dossier_fichiers is None:
                return MASK
            if self.frequences[e] == f:
                n = self.cube_vers_disque(e, f, {k: v for k, v in self.mem.items() if k[0] == e})
            elif (e, f) in self.cubes:
                n = self.cube_vers_disque(e, f, self.cubes[(e, f)])
                if n is not None:
                    del self.cubes[(e, f)]
            else:
                n = None
            return MASK if n is None else n
        if code == 12:
            return 0                          # présenter l'image : la machine de référence n'a pas de fenêtre
        if code in (16, 17, 20, 21):
            return 0                          # souris, touche, molette, appuyee : pas de fenêtre ici
        if code == 19:
            ancienne = self.__dict__.get("_cadence", 16)   # cadence : gardée, sans effet sans fenêtre
            self._cadence = min(arg, 60000)
            return ancienne
        if code == 18:
            import time                       # horloge : millisecondes depuis le lancement
            debut = self.__dict__.setdefault("_debut", time.monotonic())
            return int((time.monotonic() - debut) * 1000) & MASK
        if code == 10:
            raise VtxError("mémoire pleine : le tas ne peut plus grandir, même après avoir ramassé les miettes")
        if code in (6, 7):
            # écrire ou lire un bloc de mots (nom, adresse globale et nombre en @3[14680060..14680062])
            if self.dossier_fichiers is None:
                return MASK
            chemin = os.path.join(self.dossier_fichiers, self.texte_memoire(self.mem.get((3, 14680060), 0)))
            a, n = self.mem.get((3, 14680061), 0), self.mem.get((3, 14680062), 0)
            e, o = (a >> 24) & 3, a & 0xFFFFFF
            try:
                if code == 6:
                    with open(chemin, "wb") as h:
                        h.write(b"".join(self.mem.get((e, (o + i) & 0xFFFFFF), 0).to_bytes(4, "little") for i in range(n)))
                    return n
                with open(chemin, "rb") as h:
                    b = h.read()
            except OSError:
                return MASK
            k = min(len(b) // 4, n)
            for i in range(k):
                v = int.from_bytes(b[4 * i:4 * i + 4], "little")
                if v:
                    self.mem[(e, (o + i) & 0xFFFFFF)] = v
                else:
                    self.mem.pop((e, (o + i) & 0xFFFFFF), None)
            return k
        if code == 3:
            f = self.fichiers.pop(arg, None)
            if f is None:
                return MASK
            if f[0] == "e" and os.path.basename(f[3]) == "voix:":
                # le canal « voix: » : la machine Python écrit ce qu'elle dirait
                print("[voix] " + "".join(chr(v & 0x1FFFFF) for v in f[1]), file=sys.stderr)
            elif f[0] == "e":
                with open(f[3], "w", encoding="utf-8") as h:
                    h.write("".join(chr(v & 0x1FFFFF) for v in f[1]))
            return 0
        if code == 4:
            f = self.fichiers.get(arg)
            return 1 if f is None or f[0] != "l" or f[2] >= len(f[1]) else 0
        return MASK

    def ecrire(self, i, v):
        if i:
            self.r[i] = v & MASK

    def drapeaux(self, r, c=False):
        self.z, self.n, self.c = r == 0, (r >> 31) == 1, c

    def paire(self, i):
        """La paire de registres (Ri, Ri+3) : mot bas, mot haut."""
        return self.r[i], self.r[(i + 3) & 15]

    def ecrire_paire(self, i, v):
        self.ecrire(i, v & MASK)
        self.ecrire((i + 3) & 15, (v >> 32) & MASK)
        self.drapeaux((v & MASK) | ((v >> 32) & MASK))

    def flottant64(self, op, rd, rs, rt):
        """Instructions flottantes de 64 bits (0x5B à 0x6B)."""
        if op in (0x5B, 0x5C, 0x5D, 0x5E, 0x60, 0x61, 0x62):
            x, y = f64(*self.paire(rs)), f64(*self.paire(rt))
            if op == 0x5B:
                v = x + y
            elif op == 0x5C:
                v = x - y
            elif op == 0x5D:
                v = x * y
            elif op == 0x5E:
                if y == 0.0:
                    v = float("nan") if x == 0.0 or x != x else math.copysign(math.inf, x) * math.copysign(1.0, y)
                else:
                    v = x / y
            else:
                r = int(x == y) if op == 0x60 else int(x < y) if op == 0x61 else int(x <= y)
                self.ecrire(rd, r)
                self.drapeaux(r)
                return
            self.ecrire_paire(rd, bits64(v))
        elif op == 0x5F:
            x = f64(*self.paire(rs))
            self.ecrire_paire(rd, bits64(math.sqrt(x) if x >= 0 else (x if x == 0 else float("nan"))))
        elif op in (0x63, 0x64):
            a = self.r[rs]
            self.ecrire_paire(rd, bits64(float(a if op == 0x63 or a < 2 ** 31 else a - 2 ** 32)))
        elif op in (0x65, 0x66):
            x = f64(*self.paire(rs))
            if x != x:
                r = 0
            elif x in (math.inf, -math.inf):
                r = 0x7FFFFFFF if x > 0 else 0x80000000
            else:
                r = sature32(math.trunc(x) if op == 0x65 else round(x))
            self.ecrire(rd, r)
            self.drapeaux(r)
        elif op == 0x67:
            x = f32(self.r[rs])
            self.ecrire_paire(rd, bits64(x))
        elif op == 0x68:
            x = f64(*self.paire(rs))
            r = bits32(x)
            self.ecrire(rd, r)
            self.drapeaux(r)
        elif op == 0x69:
            lo, hi = self.paire(rs)
            n = (hi << 32) | lo
            self.ecrire_paire(rd, bits64(float(n - 2 ** 64 if n >= 2 ** 63 else n)))
        else:                                    # 0x6A, 0x6B : flottant vers long signé, tronqué ou arrondi, saturé
            x = f64(*self.paire(rs))
            if x != x:
                r = 0
            elif x in (math.inf, -math.inf):
                r = 0x7FFFFFFFFFFFFFFF if x > 0 else 0x8000000000000000
            else:
                r = sature64(math.trunc(x) if op == 0x6A else round(x))
            self.ecrire_paire(rd, r)

    def pas_unique(self):
        w = self.mem.get((0, self.pc), 0)
        op, g, b, a = w >> 24, (w >> 16) & 255, (w >> 8) & 255, w & 255
        rd, rs, rt = g >> 4, g & 15, b >> 4
        A, B = self.r[rs], self.r[rt]
        etage = a >> 6
        suivant = (self.pc + 1) & 0xFFFFFF
        decal = b - 256 if b > 127 else b
        self.ops[op] += 1
        if op == 0x00:
            pass
        elif op in (0x01, 0x06):
            s = A + (B if op == 0x01 else b)
            self.ecrire(rd, s)
            self.drapeaux(s & MASK, s > MASK)
        elif op in (0x02, 0x07, 0x0E):
            y = B if op != 0x07 else b
            r = (A - y) & MASK
            if op != 0x0E:
                self.ecrire(rd, r)
            self.drapeaux(r, A < y)
        elif op == 0x03:
            r = (A * B) & MASK
            self.ecrire(rd, r)
            self.drapeaux(r)
        elif op in (0x04, 0x05, 0x08, 0x09):
            if op == 0x04:
                r = (A << 2) & MASK
            elif op == 0x05:
                r = A >> 2
            elif op == 0x08:
                r = (A << (B & 31)) & MASK
            else:
                r = A >> (B & 31)
            self.ecrire(rd, r)
            self.drapeaux(r)
        elif op == 0x0A:
            v = self.mem.get((0, suivant), 0)
            self.ecrire(rd, v)
            self.drapeaux(v)
            suivant = (suivant + 1) & 0xFFFFFF
        elif op == 0x0B:
            self.ecrire(rd, A)
        elif op in (0x0C, 0x0D):
            if B == 0:
                r = MASK if op == 0x0C else A
            else:
                r = A // B if op == 0x0C else A % B
            self.ecrire(rd, r)
            self.drapeaux(r)
        elif op in (0x10, 0x11, 0x13):
            f = {0x10: min, 0x11: max, 0x13: lambda x, y: (x + y) & 3}[op]
            r = sum(f((A >> (2 * k)) & 3, (B >> (2 * k)) & 3) << (2 * k) for k in range(16))
            self.ecrire(rd, r)
            self.drapeaux(r)
        elif op in (0x12, 0x14, 0x15, 0x16):
            r = {0x12: ~A, 0x14: A & B, 0x15: A | B, 0x16: A ^ B}[op] & MASK
            self.ecrire(rd, r)
            self.drapeaux(r)
        elif op == 0x20:
            v = self.mem.get((etage, A & 0xFFFFFF), 0)
            self.ld[etage] += 1
            self.ecrire(rd, v)
            self.drapeaux(v)
        elif op == 0x21:
            self.mem[(etage, self.r[rd] & 0xFFFFFF)] = A
            self.st[etage] += 1
        elif op == 0x29:
            e = B & 3
            v = self.mem.get((e, A & 0xFFFFFF), 0)
            self.ld[e] += 1
            self.ecrire(rd, v)
            self.drapeaux(v)
        elif op == 0x2A:
            e = B & 3
            self.mem[(e, self.r[rd] & 0xFFFFFF)] = A
            self.st[e] += 1
        elif op == 0x54:
            v = (self.mem.get((etage, (A + (B >> 4)) & 0xFFFFFF), 0) >> ((B & 15) * 2)) & 3
            self.ld[etage] += 1
            self.ecrire(rd, v)
            self.drapeaux(v)
        elif op == 0x55:
            adr, d = (etage, (A + (B >> 4)) & 0xFFFFFF), (B & 15) * 2
            self.mem[adr] = (self.mem.get(adr, 0) & ~(3 << d) & MASK) | ((self.r[rd] & 3) << d)
            self.ld[etage] += 1
            self.st[etage] += 1
        elif op in (0x56, 0x57, 0x58, 0x59, 0x5A):
            V, F = 0xAAAAAAAA, 0x55555555
            if op == 0x56:
                v = ((A & B) & V) | ((A | B) & F)
            elif op == 0x57:
                v = ((A | B) & V) | ((A & B) & F)
            elif op == 0x5A:
                v = (A >> ((B & 15) * 2)) & 3
            else:
                v = ((A & V) >> 1) | ((A & F) << 1)
                if op == 0x59:
                    v ^= MASK
            self.ecrire(rd, v)
            self.drapeaux(v)
        elif 0x5B <= op <= 0x6B:
            self.flottant64(op, rd, rs, rt)
        elif op == 0x22:
            raise VtxError("DMA non implémentée (utiliser copier du prélude)")
        elif op == 0x23:
            self.ecrire(rd, self.entree.popleft() if self.entree else 0)
        elif op == 0x24:
            self.sortie.append(A)
        elif op == 0x25:
            self.ecrire(rd, self.mem.get((0, (self.r[13] + decal) & 0xFFFFFF), 0))
        elif op == 0x26:
            self.mem[(0, (self.r[13] + decal) & 0xFFFFFF)] = self.r[rd]
        elif op == 0x27:
            self.r[14] = (self.r[14] - 1) & 0xFFFFFF
            self.mem[(0, self.r[14])] = A
        elif op == 0x28:
            v = self.mem.get((0, self.r[14]), 0)
            self.r[14] = (self.r[14] + 1) & 0xFFFFFF
            self.ecrire(rd, v)
        elif op in (0x30, 0x31, 0x32, 0x35, 0x36, 0x33):
            cible = ((w & 15) << 16) | (g << 8) | b
            saut = {0x30: True, 0x31: self.z, 0x32: not self.z, 0x35: self.c, 0x36: not self.c, 0x33: True}[op]
            if op == 0x33:
                self.r[14] = (self.r[14] - 1) & 0xFFFFFF
                self.mem[(0, self.r[14])] = suivant
            if saut:
                suivant = cible
        elif op == 0x34:
            suivant = self.mem.get((0, self.r[14]), 0)
            self.r[14] = (self.r[14] + 1) & 0xFFFFFF
        elif op == 0x38:
            x, p = A.to_bytes(4, "big"), B.to_bytes(4, "big")
            r = sum(x[k] * p[k] for k in range(4)) & MASK
            self.ecrire(rd, r)
            self.drapeaux(r)
        elif op == 0x39:
            # GEMV : score toutes les entrées d'un coup. Arguments empilés : n, w, q, k, o (étage 2).
            # Pour i < n : mem[o + i] = somme sur j < w de gdot(mem[q + j], mem[k + i·w + j]).
            sp = self.r[14]
            n, w, qb, kb, ob = [self.mem.get((0, (sp + 4 - t) & 0xFFFFFF), 0) for t in range(5)]
            q = [self.mem.get((2, (qb + j) & 0xFFFFFF), 0).to_bytes(4, "big") for j in range(w)]
            for i in range(n):
                s = 0
                for j in range(w):
                    p = self.mem.get((2, (kb + i * w + j) & 0xFFFFFF), 0).to_bytes(4, "big")
                    s += q[j][0] * p[0] + q[j][1] * p[1] + q[j][2] * p[2] + q[j][3] * p[3]
                self.mem[(2, (ob + i) & 0xFFFFFF)] = s & MASK
            self.mac += n * w * 4
            self.ld[2] += w + n * w
            self.st[2] += n
        elif 0x40 <= op <= 0x43:
            x, y = f32(A), f32(B)
            if op == 0x40:
                v = x + y
            elif op == 0x41:
                v = x - y
            elif op == 0x42:
                v = x * y
            elif y == 0.0:
                v = float("nan") if x == 0.0 or x != x else math.copysign(math.inf, x) * math.copysign(1.0, y)
            else:
                v = x / y
            r = bits32(v)
            self.ecrire(rd, r)
            self.drapeaux(r)
        elif op in (0x44, 0x45, 0x46):
            x, y = f32(A), f32(B)
            r = int(x == y) if op == 0x44 else int(x < y) if op == 0x45 else int(x <= y)
            self.ecrire(rd, r)
            self.drapeaux(r)
        elif op == 0x47:
            x = f32(A)
            r = bits32(math.sqrt(x) if x >= 0 else (x if x == 0 else float("nan")))
            self.ecrire(rd, r)
            self.drapeaux(r)
        elif op in (0x48, 0x49):
            r = bits32(float(A if op == 0x48 or A < 2 ** 31 else A - 2 ** 32))
            self.ecrire(rd, r)
            self.drapeaux(r)
        elif op in (0x4A, 0x4B):
            x = f32(A)
            if x != x:
                r = 0
            elif x in (math.inf, -math.inf):
                r = 0x7FFFFFFF if x > 0 else 0x80000000
            else:
                r = sature32(math.trunc(x) if op == 0x4A else round(x))
            self.ecrire(rd, r)
            self.drapeaux(r)
        elif op == 0x4C:
            s = A + B + (1 if self.c else 0)
            self.ecrire(rd, s)
            self.drapeaux(s & MASK, s > MASK)
        elif op == 0x4D:
            y = B + (1 if self.c else 0)
            r = (A - y) & MASK
            self.ecrire(rd, r)
            self.drapeaux(r, A < y)
        elif op == 0x4E:
            r = (A * B) >> 32
            self.ecrire(rd, r)
            self.drapeaux(r)
        elif op == 0x4F:
            x = A ^ B
            r = ~(x | (x >> 1)) & 0x55555555
            self.ecrire(rd, r)
            self.drapeaux(r)
        elif op == 0x50:
            r = bin(A).count("1")
            self.ecrire(rd, r)
            self.drapeaux(r)
        elif op == 0x51:
            r = self.lire_canal(A)
            self.ecrire(rd, r)
            self.drapeaux(r)
        elif op == 0x52:
            self.ecrire_canal(B, A)
        elif op == 0x53:
            r = self.service(A, B) & MASK
            self.ecrire(rd, r)
            self.drapeaux(r)
        elif op == 0x3F:
            self.halted = True
        else:
            raise VtxError(f"code d'opération inconnu : {op:#04x} à l'adresse {self.pc}")
        self.pc = suivant
        self.pas += 1

    def executer(self, max_pas=5_000_000):
        while not self.halted:
            if self.pas >= max_pas:
                raise VtxError("limite de pas atteinte (boucle infinie ?)")
            if self.sur_pas is not None and self.sur_pas(self):
                break
            self.pas_unique()


MOTS_CLES = {"fonction", "soit", "si", "sinon", "tantque", "retour", "constante", "pour", "dans", "donnees", "arrêter", "continuer", "hypothèse", "annuler", "valider", "selon"}
# alias lisibles : et, ou, non pour && || ! ; entree, données, arreter pour les formes accentuées ou ASCII
ALIAS = {"et": ("op", "&&"), "ou": ("op", "||"), "non": ("op", "!"), "entree": ("id", "entrée"),
         "données": ("kw", "donnees"), "arreter": ("kw", "arrêter"), "hypothese": ("kw", "hypothèse")}
JETON = re.compile(
    r"""(?P<ws>\s+)|(?P<comment>//[^\n]*)
    |(?P<cube4>\#[0-9A-Fa-f]{8}(?:_[0-9A-Fa-f]{8}){3})(?![0-9A-Za-z_])
    |(?P<cube>\#(?:[0-9A-Fa-f]{8}|[0-9A-Fa-f]{6}))(?![0-9A-Za-z_])
    |(?P<quat>0q[0-3_]+)
    |(?P<dbl>(?:\d[\d_]*\.\d[\d_]*(?:[eE][-+]?\d+)?|\d[\d_]*[eE][-+]?\d+|\d[\d_]*)D)(?![0-9A-Za-z_])
    |(?P<pqf>(?:\d[\d_]*\.\d[\d_]*(?:[eE][-+]?\d+)?|\d[\d_]*[eE][-+]?\d+|\d[\d_]*)Q)(?![0-9A-Za-z_])
    |(?P<wlg>(?:0x[0-9A-Fa-f_]+|\d[\d_]*)LL)(?![0-9A-Za-z_])
    |(?P<lng>(?:0x[0-9A-Fa-f_]+|\d[\d_]*)L)(?![0-9A-Za-z_])|(?P<hex>0x[0-9A-Fa-f_]+)
    |(?P<flt>\d[\d_]*\.\d[\d_]*(?:[eE][-+]?\d+)?|\d[\d_]*[eE][-+]?\d+)|(?P<dec>\d[\d_]*)
    |(?P<car>'(?:\\.|[^'\\\n])')|(?P<str>"(?:\\.|[^"\\\n])*")
    |(?P<id>[^\W\d]\w*)
    |(?P<op><<q|>>q|<<|>>|<=|>=|==|!=|&&|\|\||\.>>|\.<=|\.>=|\.<|\.>|\./|\.%|\.\.|[-+*/%&|^~<>=@\[\](){};,.!:])""",
    re.X,
)


ADN_LIT = re.compile(r'adn"([ACGTUacgtu]{1,64})"')


def _adn_valeur(m):
    """adn"ACGT" : lettres vers quits (A = 0, C = 1, G = 2, T = U = 3), la première lettre est la plus forte."""
    v = 0
    for lettre in m.group(1).upper():
        v = v * 4 + "ACGT".index("T" if lettre == "U" else lettre)
    return str(v) + ("LL" if len(m.group(1)) > 16 else "")       # plus de 16 bases : un entier_petuar (64 au plus)


ECHAPPEMENTS = {"n": "\n", "t": "\t", "\\": "\\", "'": "'", '"': '"', "0": "\0"}


def echappements(t, ligne):
    """Texte entre guillemets ou apostrophes : \\n, \\t, \\\\, \\', \\", \\0."""
    out, i = [], 0
    while i < len(t):
        if t[i] == "\\":
            if i + 1 >= len(t) or t[i + 1] not in ECHAPPEMENTS:
                raise VtxError(f"ligne {ligne} : échappement inconnu dans « {t} »")
            out.append(ECHAPPEMENTS[t[i + 1]])
            i += 2
        else:
            out.append(t[i])
            i += 1
    return "".join(out)


def lexer(src):
    src = ADN_LIT.sub(_adn_valeur, src)
    jetons, pos, ligne = [], 0, 1
    while pos < len(src):
        m = JETON.match(src, pos)
        if not m:
            raise VtxError(f"ligne {ligne} : caractère inattendu {src[pos]!r}")
        genre, texte = m.lastgroup, m.group()
        pos = m.end()
        if genre in ("ws", "comment"):
            ligne += texte.count("\n")
            continue
        if genre == "id":
            if texte in ALIAS:
                k2, v2 = ALIAS[texte]
                jetons.append((k2, v2, ligne))
            else:
                jetons.append(("kw" if texte in MOTS_CLES else "id", texte, ligne))
        elif genre == "op":
            jetons.append(("op", texte, ligne))
        elif genre == "car":
            jetons.append(("num", ord(echappements(texte[1:-1], ligne)), ligne))
        elif genre == "str":
            jetons.append(("str", echappements(texte[1:-1], ligne), ligne))
        elif genre == "flt":
            x = float(texte.replace("_", ""))
            b = bits32(x)
            if b & 0x7FFFFFFF == 0x7F800000:
                raise VtxError(f"ligne {ligne} : nombre flottant trop grand")
            jetons.append(("flt", b, ligne))
        elif genre == "dbl":
            x = float(texte[:-1].replace("_", ""))
            b = bits64(x)
            if b & 0x7FFFFFFFFFFFFFFF == 0x7FF0000000000000:
                raise VtxError(f"ligne {ligne} : nombre flottant_64 trop grand")
            jetons.append(("dbl", b, ligne))
        elif genre == "pqf":
            jetons.append(("pqf", bits_petuar_decimal(texte[:-1].replace("_", ""), ligne), ligne))
        elif genre == "cube4":
            jetons.append(("wlg", int(texte[1:].replace("_", ""), 16), ligne))
        elif genre == "wlg":
            t = texte[:-2].replace("_", "")
            v = int(t[2:], 16) if t.startswith("0x") else int(t)
            if v >= 2 ** 128:
                raise VtxError(f"ligne {ligne} : nombre trop grand pour 128 bits")
            jetons.append(("wlg", v, ligne))
        elif genre == "lng":
            t = texte[:-1].replace("_", "")
            v = int(t[2:], 16) if t.startswith("0x") else int(t)
            if v >= 2 ** 64:
                raise VtxError(f"ligne {ligne} : nombre trop grand pour 64 bits")
            jetons.append(("lng", v, ligne))
        else:
            if genre == "cube":
                v = int(texte[1:], 16) << (8 if len(texte) == 7 else 0)
            elif genre == "quat":
                v = int(texte[2:].replace("_", ""), 4)
            elif genre == "hex":
                v = int(texte[2:].replace("_", ""), 16)
            else:
                v = int(texte.replace("_", ""))
            if v > MASK:
                raise VtxError(f"ligne {ligne} : nombre trop grand pour 32 bits")
            jetons.append(("num", v, ligne))
    jetons.append(("eof", None, ligne))
    return jetons


# priorité (du plus faible au plus fort) : comme en Rust, le bit à bit lie plus fort que les comparaisons
NIVEAUX = [["||"], ["&&"], ["==", "!=", "<", "<=", ">", ">=", ".<", ".<=", ".>", ".>="], ["|"], ["^"], ["&"],
           ["<<", ">>", "<<q", ">>q", ".>>"], ["+", "-"], ["*", "/", "%", "./", ".%"]]


TYPES = {"entier": "e", "flottant": "f", "long": "l", "logique": "q", "texte": "t", "flottant_64": "d", "entier_64": "l",
         "entier_128": "w", "petuar": "w", "entier_petuar": "w", "flottant_petuar": "x", "flottant_128": "x"}
# types de plusieurs mots : long et flottant_64 (paire R1:R4) ; entier_petuar et flottant_petuar, quatre points du cube
# (quadruplet R1, R3, R4, R6)
LARGES2 = ("l", "d", "w", "x")
QUATRE = ("w", "x")
REGS_T = {"l": ("R1", "R4"), "d": ("R1", "R4"), "w": ("R1", "R3", "R4", "R6"), "x": ("R1", "R3", "R4", "R6")}  # mot bas d'abord
REGS_B = {"l": ("R2", "R5"), "d": ("R2", "R5"), "w": ("R2", "R5", "R7", "R8"), "x": ("R2", "R5", "R7", "R8")}  # 2e opérande


class _NomsTypes(dict):
    def __missing__(self, t):
        return f"référence à {t[2:]}" if isinstance(t, str) and t.startswith("r:") else str(t)


NOM_TYPE = _NomsTypes({"e": "entier", "f": "flottant", "l": "long", "q": "logique", "d": "flottant_64", "w": "entier_128",
                       "x": "flottant_petuar"})
TAS_DEBUT, TAS_FIN, TAS_POINTEUR = 0x800000, 0xDFFFF0, 0xDFFFF8   # étage 3 : le tas (nouveau, nouveau_de)


def est_ref(t):
    return isinstance(t, str) and t.startswith("r:")

# Logique à quatre valeurs (Belnap) : un quit = deux bits de preuve, v (bit 1 : preuve du vrai) et f (bit 0 : preuve du faux).
LOGIQUES = {"inconnu": 0, "faux": 1, "vrai": 2, "variable": 3}
NOM_LOGIQUE = {v: k for k, v in LOGIQUES.items()}
OPS_LOGIQUES = {"et4": 2, "ou4": 2, "non4": 1, "anti": 1, "fusion": 2, "consensus": 2}
BITS_V, BITS_F = 0xAAAAAAAA, 0x55555555
RANGES = ("quits", "logique")      # tableaux rangés 16 par mot
VECTORISER = True                  # réécrire les boucles élément par élément en boucles de 16 éléments d'un coup


def contient_appel(e):
    if isinstance(e, tuple):
        return (bool(e) and e[0] == "appel") or any(contient_appel(x) for x in e[1:])
    if isinstance(e, list):
        return any(contient_appel(x) for x in e)
    return False


class Fonction:
    def __init__(self, nom, params, corps, ligne, ptypes=None, rtype="e"):
        self.nom, self.params, self.corps, self.ligne = nom, params, corps, ligne
        self.ptypes = ptypes or ["e"] * len(params)
        self.rtype = rtype


class Analyseur:
    def __init__(self, jetons):
        self.t, self.i = jetons, 0
        self.consts, self.donnees = {"vrai": 1, "faux": 0, "CPU": 0, "GPU": 1, "PARTAGE": 2, "DISQUE": 3, "nul": 0}, []
        self.textes = {}                  # texte littéral -> numéro de son étiquette
        self.types_champs = {}            # structure -> {champ : type}
        self.structs, self.tableaux = {}, {}
        self.ctx, self.nhyp = [], 0

    def regard(self, k=0):
        return self.t[min(self.i + k, len(self.t) - 1)]

    def suivant(self):
        j = self.t[self.i]
        self.i += 1
        return j

    def est_op(self, *ops):
        k, v, _ = self.regard()
        return k == "op" and v in ops

    def attendre(self, op):
        k, v, l = self.suivant()
        if not (k == "op" and v == op):
            raise VtxError(f"ligne {l} : « {op} » attendu")

    def fin_possible(self):
        return self.est_op(";")

    def fin(self):
        """Fin d'une instruction : « ; »."""
        self.attendre(";")

    def selon(self, l):
        """selon x { vrai { … } faux, inconnu { … } autre { … } } : la valeur est calculée une fois, puis une branche au plus
        est jouée ; « autre » prend les valeurs non nommées. Rendu comme une suite de si / sinon si."""
        e = self.expr()
        self.attendre("{")
        branches, vus, autre = [], set(), None
        while not self.est_op("}"):
            k2, v2, l2 = self.suivant()
            if k2 == "id" and v2 == "autre":
                if autre is not None:
                    raise VtxError(f"ligne {l2} : « autre » apparaît deux fois")
                autre = self.bloc()
                continue
            noms = [(v2, l2, k2)]
            while self.est_op(","):
                self.suivant()
                noms.append(self.suivant()[1:] + (None,))
                noms[-1] = (noms[-1][0], noms[-1][1], "id")
            codes = []
            for n_, ln, kn in noms:
                if kn != "id" or n_ not in LOGIQUES:
                    raise VtxError(f"ligne {ln} : branche de « selon » attendue : vrai, faux, inconnu, variable ou autre")
                if n_ in vus:
                    raise VtxError(f"ligne {ln} : la valeur « {n_} » a déjà sa branche")
                vus.add(n_)
                codes.append(LOGIQUES[n_])
            branches.append((codes, self.bloc(), l2))
        self.attendre("}")
        self.nselon = getattr(self, "nselon", 0) + 1
        tmp = f"__selon{self.nselon}"
        chaine = autre
        for codes, corps, lb in reversed(branches):
            cond = None
            for c in codes:
                t = ("bin", "==", ("var", tmp, lb), ("qnombre", c))
                cond = t if cond is None else ("bin", "||", cond, t)
            chaine = [("si", cond, corps, chaine, lb)]
        return [("soit", tmp, e, l, "q")] + (chaine or [])

    def identifiant(self):
        k, v, l = self.suivant()
        if k != "id":
            raise VtxError(f"ligne {l} : identifiant attendu")
        if v in LOGIQUES or v in OPS_LOGIQUES or v in ("logique", "comme_logique"):
            raise VtxError(f"ligne {l} : « {v} » est un nom réservé de la logique à quatre valeurs")
        return v

    def nom_variable(self):
        """Le nom d'une variable ou d'un paramètre : ni un nom réservé, ni celui d'une constante (sinon chaque lecture
        rendrait la constante, pas la variable)."""
        l = self.regard()[2]
        v = self.identifiant()
        if v in self.consts:
            raise VtxError(f"ligne {l} : « {v} » est une constante : une variable ne peut pas porter son nom")
        return v

    def type_opt(self):
        """Annotation de type facultative : « : flottant », « : long » ou « : entier »."""
        if not self.est_op(":"):
            return None
        self.suivant()
        k, v, l = self.suivant()
        if k == "id" and v in self.structs:
            return "r:" + v                    # référence à une structure : adresse d'un bloc (le tas)
        if k != "id" or v not in TYPES:
            raise VtxError(f"ligne {l} : type attendu (entier, flottant, long, logique, texte ou nom de structure)")
        if v == "flottant" and self.est_op("["):
            # flottant[] : un tableau dynamique de flottants
            self.suivant()
            self.attendre("]")
            return "F"
        return TYPES[v]

    def cval(self, e, l):
        """Valeur d'une constante : entier, ou ('f', bits) pour un flottant, ou ('l', valeur) pour un long."""
        neg = e[0] == "bin" and e[1] == "-" and e[2] == ("nombre", 0)
        x = e[3] if neg else e
        if x[0] == "fnombre":
            return ("f", x[1] ^ (0x80000000 if neg else 0))
        if x[0] == "lnombre":
            return ("l", ((-x[1]) if neg else x[1]) % 2 ** 64)
        if x[0] == "dnombre":
            return ("d", x[1] ^ (0x8000000000000000 if neg else 0))
        if x[0] == "wnombre":
            return ("w", ((-x[1]) if neg else x[1]) % 2 ** 128)
        if x[0] == "xnombre":
            return ("x", petuar_neg(x[1]) if neg else x[1])
        return self.ce(e, l)

    def ce(self, e, l=0):
        """Évalue une expression constante."""
        g = e[0]
        if g == "nombre":
            return e[1]
        if g == "blit":
            return e[2]
        if g == "fnombre":
            return e[1]
        if g == "bin" and e[1] == "-" and e[2] == ("nombre", 0) and e[3][0] == "fnombre":
            return e[3][1] ^ 0x80000000
        if g == "non":
            return (~self.ce(e[1], l)) & MASK
        if g == "bin":
            a, b, op = self.ce(e[2], l), self.ce(e[3], l), e[1]
            f = {"+": lambda: (a + b) & MASK, "-": lambda: (a - b) & MASK, "*": lambda: (a * b) & MASK,
                 "/": lambda: a // b if b else MASK, "%": lambda: a % b if b else a,
                 "<<": lambda: (a << (b & 31)) & MASK, ">>": lambda: a >> (b & 31),
                 "&": lambda: a & b, "|": lambda: a | b, "^": lambda: a ^ b,
                 "<<q": lambda: (a << (2 * b)) & MASK, ">>q": lambda: a >> (2 * b)}
            if op in f:
                return f[op]()
        raise VtxError(f"ligne {l} : expression constante attendue")

    def programme(self):
        fonctions = []
        while self.regard()[0] != "eof":
            k, v, l = self.regard()
            if k == "kw" and v == "constante":
                self.suivant()
                self.une_constante(l)
                continue
            if k == "kw" and v == "donnees":
                self.suivant()
                m = self.acces()
                if not isinstance(m[1], int):
                    raise VtxError(f"ligne {l} : étage constant attendu dans donnees")
                self.attendre("=")
                self.attendre("{")
                vals = []
                while not self.est_op("}"):
                    vals.append(self.ce(self.expr(), l))
                    if self.est_op(","):
                        self.suivant()
                self.attendre("}")
                self.fin()
                self.donnees.append((m[1], self.ce(m[2], l), vals))
                continue
            if k == "id" and v == "structure":
                self.suivant()
                nom = self.identifiant()
                self.attendre("{")
                champs = []
                self.structs[nom] = champs        # connue dès maintenant : un champ peut désigner la structure elle-même
                types = self.types_champs.setdefault(nom, {})
                while not self.est_op("}"):
                    c = self.identifiant()
                    champs.append(c)
                    types[c] = self.type_opt() or "e"
                    if self.est_op(";", ","):
                        self.suivant()
                self.attendre("}")
                if self.est_op(";"):
                    self.suivant()
                self.structs[nom] = champs
                continue
            if k == "id" and v == "tableau":
                self.suivant()
                self.un_tableau(l)
                continue
            self.suivant()
            if not (k == "kw" and v == "fonction"):
                raise VtxError(f"ligne {l} : « fonction » attendu")
            nom = self.identifiant()
            self.attendre("(")
            params, ptypes = [], []
            while not self.est_op(")"):
                params.append(self.nom_variable())
                ptypes.append(self.type_opt() or "e")
                if self.est_op(","):
                    self.suivant()
            self.attendre(")")
            rtype = self.type_opt() or "e"
            corps = self.bloc()
            if VECTORISER:
                corps = self.vectoriser(corps)
            fonctions.append(Fonction(nom, params, self.abaisser(corps), l, ptypes, rtype))
        if getattr(self, "cumul_utilise", False):
            for nom, (et, base, taille, struct) in self.tableaux.items():
                n_mots = self.mots_tableau(taille, struct)
                if et == 3 and base < COPIES_FIN and base + n_mots > COPIES_DEBUT:
                    raise VtxError(f"le tableau « {nom} » occupe @3[{COPIES_DEBUT}..{COPIES_FIN}], réservé aux copies des "
                                   f"tableaux cumulés")
        return fonctions

    def une_constante(self, l):
        nom = self.identifiant()
        self.attendre("=")
        e = self.expr()
        self.fin()
        self.consts[nom] = self.cval(e, l)

    def un_tableau(self, l):
        nom = self.identifiant()
        self.attendre("[")
        taille = self.ce(self.expr(), l)
        self.attendre("]")
        struct = None
        k2, v2, l2 = self.regard()
        if k2 == "id" and v2 == "de":
            self.suivant()
            if self.regard()[0] == "id" and self.regard()[1] in RANGES:
                struct = self.suivant()[1]       # 16 quits ou 16 logiques par mot
            else:
                struct = self.identifiant()
            if struct not in self.structs and struct not in RANGES:
                raise VtxError(f"ligne {l2} : structure « {struct} » inconnue")
        m = self.acces()
        if not isinstance(m[1], int):
            raise VtxError(f"ligne {l} : étage constant attendu pour un tableau")
        self.fin()
        self.tableaux[nom] = (m[1], self.ce(m[2], l), taille, struct)

    def bloc(self):
        self.attendre("{")
        instr = []
        while not self.est_op("}"):
            if self.regard()[0] == "eof":
                raise VtxError("« } » manquant en fin de fichier")
            st = self.instruction()
            if isinstance(st, list):
                instr.extend(st)
            else:
                instr.append(st)
        self.attendre("}")
        return instr

    def instruction(self):
        k, v, l = self.regard()
        if k == "kw":
            self.suivant()
            if v == "soit":
                nom = self.nom_variable()
                t = self.type_opt()
                self.attendre("=")
                e = self.expr()
                self.fin()
                return ("soit", nom, e, l, t)
            if v == "si":
                cond = self.expr()
                alors = self.bloc()
                sinon = None
                if self.regard()[:2] == ("kw", "sinon"):
                    self.suivant()
                    sinon = [self.instruction()] if self.regard()[:2] == ("kw", "si") else self.bloc()
                return ("si", cond, alors, sinon, l)
            if v == "selon":
                return self.selon(l)
            if v == "tantque":
                cond = self.expr()
                self.ctx.append(("boucle",))
                corps = self.bloc()
                self.ctx.pop()
                return ("tantque", cond, corps, l)
            if v == "pour":
                nom = self.nom_variable()
                annot = self.type_opt()
                k2, v2, l2 = self.suivant()
                if not (k2 == "kw" and v2 == "dans"):
                    raise VtxError(f"ligne {l2} : « dans » attendu")
                a = self.expr()
                if not self.est_op(".."):
                    # pour x dans t { … } : chaque case d'un tableau dynamique, dans l'ordre
                    self.niter = getattr(self, "niter", 0) + 1
                    tt, kk = f"__it{self.niter}", f"__ik{self.niter}"
                    self.ctx.append(("boucle",))
                    corps = self.bloc()
                    self.ctx.pop()
                    if annot not in (None, "t", "f"):
                        raise VtxError(f"ligne {l} : la variable d'une boucle « pour … dans » est un entier, un flottant ou un texte")
                    el = self.element(("var", tt, l), ("var", kk, l))
                    if annot == "f":
                        el = ("appel", "comme_flottant", [el], l)
                    x = ("soit", nom, el, l, annot, "chaque")
                    return [("soit", tt, a, l, None),
                            ("pour", kk, ("nombre", 0), ("appel", "longueur", [("var", tt, l)], l), [x] + corps, l, 1)]
                if annot is not None:
                    raise VtxError(f"ligne {l} : une boucle entre deux bornes compte en entiers : pas de type ici")
                self.attendre("..")
                b = self.expr()
                pas = 1
                if self.regard()[:2] == ("id", "par"):
                    self.suivant()
                    pas = self.ce(self.expr(), l)
                    if not 1 <= pas <= 0x7FFFFFFF:
                        raise VtxError(f"ligne {l} : pas de boucle invalide")
                nseg = 0
                if self.regard()[:2] == ("id", "en"):
                    self.suivant()
                    nseg = SEGMENTS_DEFAUT
                    if self.regard()[0] == "num":
                        nseg = self.suivant()[1]
                    k3, v3, l3 = self.suivant()
                    if not (k3 == "id" and v3 == "segments"):
                        raise VtxError(f"ligne {l3} : « segments » attendu après « en »")
                    if not 2 <= nseg <= MAX_SEGMENTS:
                        raise VtxError(f"ligne {l} : nombre de segments entre 2 et {MAX_SEGMENTS}")
                    nseg = -(-nseg // CANAUX) * CANAUX   # multiple du nombre de cylindres : pas de cylindre à vide
                    if pas != 1:
                        raise VtxError(f"ligne {l} : une boucle en segments avance de 1 en 1")
                cumul = []
                if nseg and self.regard()[:2] == ("id", "cumulant"):
                    self.suivant()
                    while True:
                        k4, v4, l4 = self.suivant()
                        if k4 != "id" or v4 not in self.tableaux:
                            raise VtxError(f"ligne {l4} : nom de tableau attendu après « cumulant »")
                        et, base, taille, struct = self.tableaux[v4]
                        if struct in RANGES:
                            raise VtxError(f"ligne {l4} : un tableau de quits ou de logiques ne peut pas être cumulé")
                        n_mots = self.mots_tableau(taille, struct)
                        cumul.append((v4, (et, base, base + n_mots), et, base, n_mots))
                        if not self.est_op(","):
                            break
                        self.suivant()
                self.ctx.append(("segment",) if nseg else ("boucle",))
                corps = self.bloc()
                self.ctx.pop()
                if nseg:
                    self.verifier_segment(nom, corps, l)
                    if cumul:
                        verifier_cumul(corps, cumul, l)
                        self.cumul_utilise = True
                    self.nseg_id = getattr(self, "nseg_id", 0) + 1
                    return ("segments", nom, a, b, corps, l, nseg, self.nseg_id, tuple(cumul))
                return ("pour", nom, a, b, corps, l, pas)
            if v == "arrêter" or v == "continuer":
                self.fin()
                if self.ctx and self.ctx[-1][0] == "hyp":
                    raise VtxError(f"ligne {l} : « {v} » ne peut pas sortir d'une hypothèse : utilisez annuler ou valider")
                return ("arreter" if v == "arrêter" else "continuer", l)
            if v == "hypothèse":
                if any(c[0] == "segment" for c in self.ctx):
                    raise VtxError(f"ligne {l} : pas d'hypothèse dans une boucle en segments")
                self.nhyp += 1
                n = self.nhyp
                self.ctx.append(("hyp", n))
                corps = self.bloc()
                self.ctx.pop()
                return self.abaisser_hypothese(n, self.abaisser(corps), l)
            if v == "annuler" or v == "valider":
                self.fin()
                if not (self.ctx and self.ctx[-1][0] == "hyp"):
                    raise VtxError(f"ligne {l} : « {v} » doit être directement dans une hypothèse, hors de toute boucle")
                return (v, l)
            if v == "retour":
                if any(c[0] == "hyp" for c in self.ctx):
                    raise VtxError(f"ligne {l} : « retour » interdit dans une hypothèse : validez ou annulez d'abord")
                e = None if self.fin_possible() else self.expr()
                self.fin()
                return ("retour", e, l)
            raise VtxError(f"ligne {l} : « {v} » inattendu ici")
        if k == "id" and v == "tableau" and self.regard(1)[0] == "id" and self.regard(2)[:2] == ("op", "["):
            # tableau t[n]; dans une fonction : un tableau dynamique de n cases (sur le tas)
            self.suivant()
            nom = self.nom_variable()
            self.attendre("[")
            n = self.expr()
            self.attendre("]")
            self.fin()
            return ("soit", nom, ("appel", "tableau", [n], l), l, None)
        if k == "op" and v == "@":
            m = self.acces()
            self.attendre("=")
            e = self.expr()
            self.fin()
            return ("ecrire", m[1], m[2], e, l)
        if k == "id" and v in self.tableaux and self.regard(1)[:2] == ("op", "[") and self.tableaux[v][3] in RANGES:
            self.suivant()
            return self.ecrire_rangee(v, l)
        if k == "id" and v in self.tableaux and self.regard(1)[:2] == ("op", "["):
            self.suivant()
            et, adr, zone = self.case_tableau(v, l)
            self.attendre("=")
            e = self.expr()
            self.fin()
            return ("ecrire", et, adr, e, l, zone)
        if k == "id" and self.regard(1)[:2] == ("op", "="):
            self.suivant()
            self.suivant()
            e = self.expr()
            self.fin()
            return ("affecter", v, e, l)
        e = self.expr()
        if self.est_op("="):
            self.suivant()
            val = self.expr()
            self.fin()
            if e[0] == "champ_ref" or (e[0] == "champ" and len(e) == 3):
                return ("ecrire_champ", e[1], e[2], val, l)
            if e[0] == "lire" and len(e) == 3:
                return ("ecrire", e[1], e[2], val, l)
            raise VtxError(f"ligne {l} : on ne peut affecter qu'une variable, une case, un champ ou @étage[adresse]")
        self.fin()
        return ("expr", e, l)

    def verifier_segment(self, var, corps, l):
        """Un segment doit être indépendant des autres : il ne modifie aucune variable déclarée hors de la boucle,
        ni sa variable de boucle, et n'en sort pas (arrêter, retour, hypothèse)."""
        internes = set()

        def declarees(lst):
            for st in lst:
                if st[0] == "soit":
                    internes.add(st[1])
                elif st[0] in ("pour", "segments"):
                    internes.add(st[1])
                    declarees(st[4])
                elif st[0] == "si":
                    declarees(st[2])
                    if st[3]:
                        declarees(st[3])
                elif st[0] == "tantque":
                    declarees(st[2])

        def verifier(lst, profondeur):
            for st in lst:
                g = st[0]
                if g == "affecter" and (st[1] not in internes or st[1] == var):
                    raise VtxError(f"ligne {st[3]} : un segment ne peut pas modifier « {st[1]} », déclarée hors de la boucle "
                                   f"(chaque segment doit être indépendant : écrivez plutôt dans un tableau, à la case de l'indice)")
                if g == "arreter" and profondeur == 0:
                    raise VtxError(f"ligne {st[1]} : « arrêter » ne peut pas sortir d'une boucle en segments")
                if g == "retour":
                    raise VtxError(f"ligne {st[2]} : « retour » interdit dans une boucle en segments")
                if g == "si":
                    verifier(st[2], profondeur)
                    if st[3]:
                        verifier(st[3], profondeur)
                elif g in ("tantque",):
                    verifier(st[2], profondeur + 1)
                elif g in ("pour", "segments"):
                    verifier(st[4], profondeur + 1)

        declarees(corps)
        internes.discard(var)
        verifier(corps, 0)

    def abaisser_hypothese(self, n, corps, l):
        """Bloc d'hypothèse -> boucle à un tour. Les écritures mémoire écrites dans le bloc sont journalisées :
        annuler les défait, valider (ou la fin du bloc) les garde. Les variables locales ne sont pas défaites."""
        cpt = [0]

        def tmp():
            cpt[0] += 1
            return f"__t{n}_{cpt[0]}"

        def liste(bloc):
            out = []
            for st in bloc:
                out.extend(stm(st))
            return out

        def stm(st):
            g = st[0]
            if g == "ecrire":
                et, adr, v, ll = st[1], st[2], st[3], st[4]
                if isinstance(et, int) and et == 0:
                    raise VtxError(f"ligne {ll} : écriture dans l'étage 0 interdite dans une hypothèse")
                ta = tmp()
                out = [("soit", ta, adr, ll)]
                if isinstance(et, int):
                    out.append(("expr", ("appel", "__hyp_noter", [("nombre", et), ("var", ta, ll)], ll), ll))
                    out.append(("ecrire", et, ("var", ta, ll), v, ll))
                else:
                    te = tmp()
                    out.append(("soit", te, et, ll))
                    out.append(("expr", ("appel", "__hyp_noter", [("var", te, ll), ("var", ta, ll)], ll), ll))
                    out.append(("ecrire", ("var", te, ll), ("var", ta, ll), v, ll))
                return out
            if g == "annuler":
                return [("expr", ("appel", "__hyp_annuler", [("var", f"__h{n}", st[1])], st[1]), st[1]), ("arreter", st[1])]
            if g == "valider":
                return [("expr", ("appel", "__hyp_valider", [], st[1]), st[1]), ("arreter", st[1])]
            if g == "si":
                return [("si", st[1], liste(st[2]), None if st[3] is None else liste(st[3]), st[4])]
            if g == "tantque":
                return [("tantque", st[1], liste(st[2]), st[3])]
            if g == "pour":
                return [("pour", st[1], st[2], st[3], liste(st[4]), st[5], st[6] if len(st) > 6 else 1)]
            return [st]

        entree = ("soit", f"__h{n}", ("appel", "__hyp_debut", [], l), l)
        fin = ("expr", ("appel", "__hyp_valider", [], l), l)
        return ("pour", f"__hk{n}", ("nombre", 0), ("nombre", 1), [entree] + liste(corps) + [fin], l, 1)

    def mots_tableau(self, taille, struct):
        if struct in RANGES:
            return (taille + 15) // 16
        return taille * (len(self.structs[struct]) if struct else 1)

    def case_rangee(self, nom, l):
        """Case d'un tableau de quits ou de logiques (16 par mot) : rend (étage, adresse du mot, décalage, zone, indice)."""
        et, base, taille, struct = self.tableaux[nom]
        zone = (et, base, base + self.mots_tableau(taille, struct))
        self.attendre("[")
        idx = self.expr()
        self.attendre("]")
        if idx[0] == "nombre" and idx[1] >= taille:
            raise VtxError(f"ligne {l} : indice {idx[1]} hors du tableau {nom} (taille {taille})")
        return et, base, zone, idx

    @staticmethod
    def mot_et_decalage(base, idx):
        adr = ("bin", ">>", idx, ("nombre", 4))
        if base:
            adr = ("bin", "+", ("nombre", base), adr)
        return adr, ("bin", "*", ("bin", "&", idx, ("nombre", 15)), ("nombre", 2))

    def lire_rangee(self, nom, l):
        """Forme haute ("rangee_lire", nom, indice, ligne) : traduite après la lecture de la fonction (abaisser), une fois
        les boucles réécrites 16 éléments à la fois (vectoriser)."""
        _et, _base, _zone, idx = self.case_rangee(nom, l)
        if contient_appel(idx):
            raise VtxError(f"ligne {l} : l'indice d'un tableau de {self.tableaux[nom][3]} ne doit pas appeler de fonction : "
                           f"rangez-le d'abord dans une variable")
        return ("rangee_lire", nom, idx, l)

    def lire_rangee_basse(self, nom, idx, l):
        et, base, taille, struct = self.tableaux[nom]
        zone = (et, base, base + self.mots_tableau(taille, struct))
        if contient_appel(idx):
            raise VtxError(f"ligne {l} : l'indice d'un tableau de {self.tableaux[nom][3]} ne doit pas appeler de fonction : "
                           f"rangez-le d'abord dans une variable")
        adr, dec = self.mot_et_decalage(base, idx)
        v = ("bin", "&", ("bin", ">>", ("lire", et, adr, zone), dec), ("nombre", 3))
        return ("appel", "comme_logique", [v], l) if self.tableaux[nom][3] == "logique" else v

    def ecrire_rangee(self, nom, l):
        _et, _base, _zone, idx = self.case_rangee(nom, l)
        self.attendre("=")
        v = self.expr()
        self.fin()
        return ("rangee_ecrire", nom, idx, v, l)

    def ecrire_rangee_basse(self, nom, idx, v, l):
        """t[i] = v pour un tableau de quits ou de logiques : lecture du mot, remplacement du quit, écriture."""
        et, base, taille, struct = self.tableaux[nom]
        zone = (et, base, base + self.mots_tableau(taille, struct))
        if self.tableaux[nom][3] == "logique":
            v = ("appel", "__code_logique", [v], l)
        self.nrangee = getattr(self, "nrangee", 0) + 1
        qi, qv = f"__qi{self.nrangee}", f"__qv{self.nrangee}"
        adr, dec = self.mot_et_decalage(base, ("var", qi, l))
        nouveau = ("bin", "|", ("bin", "&", ("lire", et, adr, zone), ("non", ("bin", "<<", ("nombre", 3), dec))),
                   ("bin", "<<", ("bin", "&", ("var", qv, l), ("nombre", 3)), dec))
        return [("soit", qi, idx, l, "e"), ("soit", qv, v, l, "e"), ("ecrire", et, adr, nouveau, l, zone)]

    def abaisser(self, x):
        """Traduit les accès aux tableaux rangés (16 par mot) en lectures et écritures de mots."""
        if isinstance(x, list):
            out = []
            for y in x:
                if isinstance(y, tuple) and y and y[0] == "rangee_ecrire":
                    out.extend(self.ecrire_rangee_basse(y[1], self.abaisser(y[2]), self.abaisser(y[3]), y[4]))
                else:
                    out.append(self.abaisser(y))
            return out
        if isinstance(x, tuple) and x:
            if x[0] == "rangee_lire":
                return self.lire_rangee_basse(x[1], self.abaisser(x[2]), x[3])
            return tuple(self.abaisser(y) for y in x)
        return x

    def vectoriser(self, x):
        """Réécrit les boucles « pour i dans a..b { T[i] = … ; } » sur des tableaux rangés, quand chaque élément ne dépend
        que des éléments de même indice par des opérations quit par quit : les mots entiers sont traités 16 éléments
        d'un coup, les éléments du début et de la fin qui ne remplissent pas un mot restent traités un par un."""
        if isinstance(x, list):
            out = []
            for y in x:
                v = self.vectoriser(y)
                out.extend(v) if isinstance(v, list) else out.append(v)
            return out
        if not (isinstance(x, tuple) and x):
            return x
        if x[0] == "pour" and len(x) == 7 and x[6] == 1:
            r = self.boucle_vectorielle(x)
            if r is not None:
                return r
        return tuple(self.vectoriser(y) if isinstance(y, (list, tuple)) else y for y in x)

    @staticmethod
    def noms_lus(x, acc):
        if isinstance(x, tuple) and x:
            if x[0] == "var":
                acc.add(x[1])
            for y in x[1:]:
                Analyseur.noms_lus(y, acc)
        elif isinstance(x, list):
            for y in x:
                Analyseur.noms_lus(y, acc)
        return acc

    def sortes_lues(self, x, acc):
        if isinstance(x, tuple) and x:
            if x[0] == "rangee_lire":
                acc.add(self.tableaux[x[1]][3])
            for y in x[1:]:
                self.sortes_lues(y, acc)
        elif isinstance(x, list):
            for y in x:
                self.sortes_lues(y, acc)
        return acc

    def reduction(self, s_, var):
        """Reconnaît « n = n + E » (somme des éléments) et « si E1 == E2 { n = n + 1; } » (ou !=) : rend
        (n, sorte d'opération, expressions) ou None."""
        if s_[0] == "affecter" and s_[2][0] == "bin" and s_[2][1] == "+" and s_[2][2][:2] == ("var", s_[1]):
            return s_[1], "somme", [s_[2][3]]
        if (s_[0] == "si" and s_[3] is None and len(s_[2]) == 1 and s_[1][0] == "bin" and s_[1][1] in ("==", "!=")
                and s_[2][0][0] == "affecter" and s_[2][0][2][0] == "bin" and len(s_[2][0][2]) == 4
                and isinstance(s_[2][0][2][2], tuple) and len(s_[2][0][2][2]) >= 3
                and s_[2][0][2] == ("bin", "+", ("var", s_[2][0][1], s_[2][0][2][2][2]), ("nombre", 1))):
            return s_[2][0][1], s_[1][1], [s_[1][2], s_[1][3]]
        return None

    def boucle_vectorielle(self, st):
        _g, var, a, b, corps, l, _pas = st
        if not corps:
            return None
        ecritures, reductions = [], []
        for s_ in corps:
            if s_[0] == "rangee_ecrire" and s_[2][:2] == ("var", var):
                ecritures.append(s_)
                continue
            r_ = self.reduction(s_, var)
            if r_ is None or r_[0] == var:
                return None
            reductions.append(r_)
        accus = [r_[0] for r_ in reductions]
        if len(set(accus)) != len(accus):
            return None
        for s_ in corps:                         # un accumulateur n'est lu que par sa propre mise à jour
            lus = self.noms_lus(s_, set())
            r_ = self.reduction(s_, var) if s_[0] != "rangee_ecrire" else None
            if any(n_ in lus for n_ in accus if not (r_ and r_[0] == n_)):
                return None
        sortes = {self.tableaux[s_[1]][3] for s_ in ecritures} | self.sortes_lues(corps, set())
        if len(sortes) != 1:
            return None
        sorte = sortes.pop()
        mots = []
        for s_ in ecritures:
            w = self.mot_vectoriel(s_[3], var, sorte)
            if w is None:
                return None
            mots.append((s_[1], w, s_[4]))
        sommes = []
        for n_, genre, es in reductions:
            ws = [self.mot_vectoriel(e_, var, sorte) for e_ in es]
            if None in ws or not any(self.sortes_lues(e_, set()) for e_ in es) or not all(self.propre(e_) for e_ in es):
                return None
            if genre == "somme":
                if sorte != "quits":
                    return None
                w = ws[0]                        # somme des 16 quits : bits bas + 2 × bits hauts
                c = ("bin", "+", ("appel", "nb_bits", [("bin", "&", w, ("nombre", 0x55555555))], l),
                     ("bin", "*", ("nombre", 2), ("appel", "nb_bits", [("bin", "&", w, ("nombre", 0xAAAAAAAA))], l)))
            else:
                c = ("appel", "nb_bits", [("appel", "qegal", ws, l)], l)
                if genre == "!=":
                    c = ("bin", "-", ("nombre", 16), c)
            sommes.append(("affecter", n_, ("bin", "+", ("var", n_, l), c), l))
        self.nvect = getattr(self, "nvect", 0) + 1
        n = self.nvect
        va, vb, vh, vt, vk = (f"__v{c}{n}" for c in "abhtk")
        V = lambda nom: ("var", nom, l)
        corps_mots = []
        for nom, w, ln in mots:
            et, base, taille, struct = self.tableaux[nom]
            zone = (et, base, base + self.mots_tableau(taille, struct))
            corps_mots.append(("ecrire", et, ("bin", "+", ("nombre", base), V(vk)) if base else V(vk), w, ln, zone))
        return [
            ("soit", va, a, l, "e"),
            ("soit", vb, b, l, "e"),
            ("soit", vh, ("bin", "&", ("bin", "+", V(va), ("nombre", 15)), ("non", ("nombre", 15))), l, "e"),
            ("si", ("bin", ">", V(vh), V(vb)), [("affecter", vh, V(vb), l)], None, l),
            ("soit", vt, ("bin", "&", V(vb), ("non", ("nombre", 15))), l, "e"),
            ("si", ("bin", "<", V(vt), V(vh)), [("affecter", vt, V(vh), l)], None, l),
            ("pour", var, V(va), V(vh), corps, l, 1),
            ("pour", vk, ("bin", ">>", V(vh), ("nombre", 4)), ("bin", ">>", V(vt), ("nombre", 4)), corps_mots + sommes, l, 1),
            ("pour", var, V(vt), V(vb), corps, l, 1),   # abaisser en fait une copie distincte du corps
        ]

    def propre(self, e):
        """Vrai si la valeur d'un élément ne tient que dans son quit (les 15 autres quits du mot restent à 0) : condition
        pour qu'une somme ou une comparaison d'éléments se calcule 16 à la fois. cmp3 et qegal remplissent les autres
        quits (3 ou 1) ; une constante doit valoir 0 à 3."""
        g = e[0]
        if g in ("rangee_lire", "qnombre", "blit"):
            return True
        if g == "nombre":
            return e[1] <= 3
        if g == "appel":
            if e[1] == "comme_logique":
                return True
            if e[1] in ("cmp3", "qegal"):
                return False
            return all(self.propre(a_) for a_ in e[2])
        if g == "bin":
            return self.propre(e[2]) and self.propre(e[3])
        return False

    def mot_vectoriel(self, e, var, sorte):
        """Le même calcul sur 16 éléments à la fois, ou None si un élément pourrait dépendre d'un autre."""
        g = e[0]
        if g == "rangee_lire":
            if e[2][:2] != ("var", var) or self.tableaux[e[1]][3] != sorte:
                return None
            et, base, taille, struct = self.tableaux[e[1]]
            zone = (et, base, base + self.mots_tableau(taille, struct))
            k = ("var", f"__vk{getattr(self, 'nvect', 0) + 1}", e[3])
            return ("lire", et, ("bin", "+", ("nombre", base), k) if base else k, zone)
        if sorte == "logique" and g in ("qnombre", "blit"):
            return ("nombre", e[1] * 0x55555555)
        if sorte == "quits" and g == "nombre":
            return ("nombre", (e[1] & 3) * 0x55555555)
        if g == "appel":
            nom, args = e[1], e[2]
            if nom in ("comme_logique", "entier") and len(args) == 1:
                return self.mot_vectoriel(args[0], var, sorte)
            quit_par_quit = OPS_LOGIQUES if sorte == "logique" else ("min4", "max4", "addm4", "cmp3", "qegal")
            if nom in quit_par_quit:
                ws = [self.mot_vectoriel(a, var, sorte) for a in args]
                return None if None in ws else ("appel", nom, ws, e[3])
            return None
        if sorte == "quits" and g == "bin" and e[1] in ("&", "|", "^"):
            wa, wb = self.mot_vectoriel(e[2], var, sorte), self.mot_vectoriel(e[3], var, sorte)
            return None if None in (wa, wb) else ("bin", e[1], wa, wb)
        return None

    def case_tableau(self, nom, l):
        """Case de tableau (ou champ de structure) : rend (étage, expression d'adresse, zone (étage, début, fin))."""
        et, base, taille, struct = self.tableaux[nom]
        zone = (et, base, base + self.mots_tableau(taille, struct))
        self.attendre("[")
        idx = self.expr()
        self.attendre("]")
        if idx[0] == "nombre" and idx[1] >= taille:
            raise VtxError(f"ligne {l} : indice {idx[1]} hors du tableau {nom} (taille {taille})")
        if struct is None:
            return et, (idx if base == 0 else ("bin", "+", ("nombre", base), idx)), zone
        self.attendre(".")
        k, champ, l2 = self.suivant()
        champs = self.structs[struct]
        if k != "id" or champ not in champs:
            raise VtxError(f"ligne {l2} : champ inconnu « {champ} » dans la structure {struct}")
        pos = idx if len(champs) == 1 else ("bin", "*", idx, ("nombre", len(champs)))
        return et, ("bin", "+", ("nombre", base + champs.index(champ)), pos), zone

    def acces(self):
        self.attendre("@")
        if self.est_op("("):
            self.suivant()
            e = self.expr()
            self.attendre(")")
            l = self.regard()[2]
        else:
            k, e, l = self.suivant()
            if k == "id" and e in self.consts:
                k, e = "num", self.consts[e]
            if k != "num" or e > 3:
                raise VtxError(f"ligne {l} : numéro d'étage attendu (0 à 3)")
        self.attendre("[")
        a = self.expr()
        self.attendre("]")
        return ("mem", e, a, l)

    def expr(self, niveau=0):
        if niveau == len(NIVEAUX):
            return self.unaire()
        gauche = self.expr(niveau + 1)
        while self.est_op(*NIVEAUX[niveau]):
            j = self.suivant()
            gauche = self.binaire(j[1], gauche, self.expr(niveau + 1), j[2])
        return gauche

    def binaire(self, op, a, b, l):
        """Opérateurs signés (complément à deux) : comparaisons par XOR du bit de signe, le reste par le prélude."""
        if not op.startswith("."):
            return ("bin", op, a, b)
        bascule = lambda x: ("bin", "^", x, ("nombre", 2147483648))
        if op in (".<", ".<=", ".>", ".>="):
            return ("bin", op[1:], bascule(a), bascule(b))
        return ("appel", {"./": "divs", ".%": "mods", ".>>": "asr"}[op], [a, b], l)

    def unaire(self):
        if self.est_op("~"):
            self.suivant()
            return ("non", self.unaire())
        if self.est_op("!"):
            self.suivant()
            return ("non_log", self.unaire())
        if self.est_op("-"):
            self.suivant()
            return ("bin", "-", ("nombre", 0), self.unaire())
        e = self.primaire()
        while self.est_op(".", "["):
            if self.est_op("["):
                # t[i] d'un tableau dynamique (tableau(n), [a, b, c]) : la case i de son bloc de données
                self.suivant()
                i = self.expr()
                self.attendre("]")
                e = self.element(e, i)
                continue
            self.suivant()
            k, v, l = self.suivant()
            if k != "id":
                raise VtxError(f"ligne {l} : champ attendu après « . »")
            if v == "q":
                self.attendre("(")
                i = self.expr()
                self.attendre(")")
                e = ("quit", e, i)
            elif v in ("r", "v", "b", "a"):
                e = ("champ", e, v)
            else:
                e = ("champ_ref", e, v, l)     # champ d'une structure désignée par une référence
        return e

    @staticmethod
    def element(h, i):
        """La case i d'un tableau dynamique : la poignée h (étage 3) contient la longueur, la capacité et l'adresse
        des données ; les données sont dans l'étage 3."""
        d = ("lire", 3, ("bin", "+", ("bin", "&", h, ("nombre", 16777215)), ("nombre", 2)))
        return ("lire", 3, ("bin", "+", d, i))

    def primaire(self):
        k, v, l = self.regard()
        if k == "num":
            self.suivant()
            return ("nombre", v)
        if k == "flt":
            self.suivant()
            return ("fnombre", v)
        if k == "dbl":
            self.suivant()
            return ("dnombre", v)
        if k == "wlg":
            self.suivant()
            return ("wnombre", v)
        if k == "pqf":
            self.suivant()
            return ("xnombre", v)
        if k == "lng":
            self.suivant()
            return ("lnombre", v)
        if k == "str":
            self.suivant()
            n = self.textes.setdefault(v, len(self.textes))
            return ("etiq", f"TEXTE{n}")
        if k == "id":
            self.suivant()
            if v in ("vrai", "faux"):
                # double sens : entier 1 / 0 (comme avant), ou logique là où un logique est attendu
                return ("blit", LOGIQUES[v], 1 if v == "vrai" else 0)
            if v in LOGIQUES:
                return ("qnombre", LOGIQUES[v])
            if v in self.tableaux and self.est_op("[") and self.tableaux[v][3] in RANGES:
                return self.lire_rangee(v, l)
            if v in self.tableaux and self.est_op("["):
                et, adr, zone = self.case_tableau(v, l)
                return ("lire", et, adr, zone)
            if v in self.structs and self.est_op("{"):
                # construction : Nom { champ: valeur, … } ; les champs non nommés valent 0 (nul)
                self.suivant()
                valeurs = []
                while not self.est_op("}"):
                    k3, champ, l3 = self.suivant()
                    if k3 != "id" or champ not in self.structs[v]:
                        raise VtxError(f"ligne {l3} : champ inconnu « {champ} » dans la structure {v}")
                    if champ in [c for c, _e in valeurs]:
                        raise VtxError(f"ligne {l3} : le champ « {champ} » est donné deux fois")
                    self.attendre(":")
                    valeurs.append((champ, self.expr()))
                    if self.est_op(","):
                        self.suivant()
                self.attendre("}")
                return ("construire", v, valeurs, ("appel", "nouveau", [("nombre", len(self.structs[v]))], l), l)
            if v == "nouveau_de" and self.est_op("("):
                self.suivant()
                k2, nom, l2 = self.suivant()
                if k2 != "id" or nom not in self.structs:
                    raise VtxError(f"ligne {l2} : nom de structure attendu dans nouveau_de()")
                self.attendre(")")
                return ("nouveau_de", nom, ("appel", "nouveau", [("nombre", len(self.structs[nom]))], l), l)
            if self.est_op("("):
                self.suivant()
                args = []
                while not self.est_op(")"):
                    args.append(self.expr())
                    if self.est_op(","):
                        self.suivant()
                self.attendre(")")
                return ("appel", v, args, l)
            if v in self.consts:
                c = self.consts[v]
                if isinstance(c, tuple):
                    return {"f": "fnombre", "l": "lnombre", "d": "dnombre", "w": "wnombre", "x": "xnombre"}[c[0]], c[1]
                return ("nombre", c)
            return ("var", v, l)
        if k == "op" and v == "(":
            self.suivant()
            e = self.expr()
            self.attendre(")")
            return e
        if k == "op" and v == "@":
            m = self.acces()
            return ("lire", m[1], m[2])
        if k == "op" and v == "[":
            # [a, b, c] : un tableau dynamique neuf, rempli
            self.suivant()
            vals = []
            while not self.est_op("]"):
                vals.append(self.expr())
                if self.est_op(","):
                    self.suivant()
            self.attendre("]")
            t = ("appel", "tableau", [("nombre", len(vals))], l)
            for j, x in enumerate(vals):
                t = ("appel", "__remplir", [t, ("nombre", j), x], l)
            return t
        raise VtxError(f"ligne {l} : expression attendue")


PRELUDE = """
fonction abs(x) { si x >= 2147483648 { retour 0 - x; } retour x; }
fonction inf(a, b) { retour (a ^ 2147483648) < (b ^ 2147483648); }
fonction sup(a, b) { retour (b ^ 2147483648) < (a ^ 2147483648); }
fonction __hyp_debut() {
    soit d = @3[16777201];
    si d == 0 { @3[16777200] = 15728640; }
    @3[16777201] = d + 1;
    retour @3[16777200];
}
fonction __hyp_noter(e, a) {
    soit p = @3[16777200];
    @3[p] = e;
    @3[p + 1] = a;
    @3[p + 2] = @(e)[a];
    @3[16777200] = p + 3;
}
fonction __hyp_valider() { @3[16777201] = @3[16777201] - 1; }
fonction __hyp_annuler(p0) {
    soit p = @3[16777200];
    tantque p > p0 {
        p = p - 3;
        @(@3[p])[@3[p + 1]] = @3[p + 2];
    }
    @3[16777200] = p0;
    @3[16777201] = @3[16777201] - 1;
}
fonction divs(a, b) {
    soit n = 0;
    si a >= 2147483648 { a = 0 - a; n = 1; }
    si b >= 2147483648 { b = 0 - b; n = 1 - n; }
    soit q = a / b;
    si n == 1 { retour 0 - q; }
    retour q;
}
fonction mods(a, b) {
    soit n = 0;
    si a >= 2147483648 { a = 0 - a; n = 1; }
    si b >= 2147483648 { b = 0 - b; }
    soit r = a % b;
    si n == 1 { retour 0 - r; }
    retour r;
}
fonction asr(a, n) {
    soit k = n & 31;
    soit r = a >> k;
    si a >= 2147483648 && k > 0 { r = r | (4294967295 << (32 - k)); }
    retour r;
}
fonction signe(x) { si x == 0 { retour 0; } si x >= 2147483648 { retour 4294967295; } retour 1; }
fonction exp2(x: flottant): flottant {
    si x < -126.0 { retour 0.0; }
    si x >= 128.0 { retour comme_flottant(2139095040); }
    soit n = entier(x);
    si flottant_signe(n) > x { n = n - 1; }
    soit f = x - flottant_signe(n);
    soit p = 1.0 + f * (0.6931472 + f * (0.2402265 + f * (0.05550411 + f * (0.009618129 + f * (0.001333355
        + f * (0.0001540353 + f * 0.00001525273))))));
    retour comme_flottant(bits(p) + (n << 23));
}
fonction __lshl(a: long, n): long {
    soit k = n & 63;
    si k == 0 { retour a; }
    si k >= 32 { retour long_de(bas(a) << (k - 32), 0); }
    retour long_de((haut(a) << k) | (bas(a) >> (32 - k)), bas(a) << k);
}
fonction __lsar(a: long, n): long {
    soit k = n & 63;
    soit h = haut(a);
    si k == 0 { retour a; }
    soit s = 0;
    si h >= 2147483648 { s = 4294967295; }
    si k >= 32 { retour long_de(s, asr(h, k - 32)); }
    retour long_de(asr(h, k), (bas(a) >> k) | (h << (32 - k)));
}
fonction __ldivu(ah, al, bh, bl, reste): long {
    soit qh = 0; soit ql = 0; soit rh = 0; soit rl = 0;
    pour i dans 0..64 {
        soit bit = 0;
        si i < 32 { bit = (ah >> (31 - i)) & 1; } sinon { bit = (al >> (63 - i)) & 1; }
        soit dessus = rh >> 31;
        rh = (rh << 1) | (rl >> 31);
        rl = (rl << 1) | bit;
        qh = (qh << 1) | (ql >> 31);
        ql = ql << 1;
        si dessus == 1 || rh > bh || (rh == bh && rl >= bl) {
            soit emprunt = 0;
            si rl < bl { emprunt = 1; }
            rl = rl - bl;
            rh = rh - bh - emprunt;
            ql = ql | 1;
        }
    }
    si reste == 1 { retour long_de(rh, rl); }
    retour long_de(qh, ql);
}
fonction __ldiv(a: long, b: long, reste): long {
    si b == 0L { si reste == 1 { retour a; } retour 0L - 1L; }
    soit na = 0;
    soit nb = 0;
    soit x = a;
    soit y = b;
    si a < 0L { x = 0L - a; na = 1; }
    si b < 0L { y = 0L - b; nb = 1; }
    soit q = __ldivu(haut(x), bas(x), haut(y), bas(y), reste);
    si reste == 1 { si na == 1 { retour 0L - q; } retour q; }
    si na != nb { retour 0L - q; }
    retour q;
}
fonction min(a, b) { si a < b { retour a; } retour b; }
fonction max(a, b) { si a > b { retour a; } retour b; }
fonction poids(ecart, temperature) {
    soit d = ecart >> temperature;
    si d < 16 { retour 65536 >> d; }
    retour 0;
}
fonction gdotn(ea, a, eb, b, n) {
    soit s = 0;
    pour i dans 0..n { s = s + gdot(@(ea)[a + i], @(eb)[b + i]); }
    retour s;
}
fonction copier(ed, d, es, s, n) {
    pour i dans 0..n { @(ed)[d + i] = @(es)[s + i]; }
}
fonction melange(ev, bv, ep, bp, decalage, n) {
    soit s = 0;
    pour i dans 0..n { s = s + @(ep)[bp + i] * ((@(ev)[bv + i] >> decalage) & 255); }
    retour s;
}
fonction longueur(t) {
    retour @(t >> 24)[t & 16777215];
}
fonction car(t, i) {
    retour @(t >> 24)[(t & 16777215) + 1 + i];
}
fonction changer_car(t, i, c) {
    @(t >> 24)[(t & 16777215) + 1 + i] = c;
}
fonction texte_egal(a, b) {
    soit n = longueur(a);
    si n != longueur(b) {
        retour 0;
    }
    pour i dans 0..n {
        si car(a, i) != car(b, i) {
            retour 0;
        }
    }
    retour 1;
}
fonction nouveau(n) {
    // chaque bloc a un mot d'en-tête (sa taille) juste avant lui ; un bloc libéré de la bonne taille est repris
    // d'abord (listes par taille en @3[14680064 + taille], la liste 0 pour les grands blocs)
    si n == 0 {
        n = 1;
    }
    si n <= 64 {
        soit t = @3[14680064 + n];
        si t != 0 {
            @3[14680064 + n] = @3[t];
            @3[t - 1] = n;
            pour i dans 0..n {
                @3[t + i] = 0;
            }
            retour 50331648 + t;
        }
    }
    // un grand bloc libre (premier assez grand) ; ce qui dépasse redevient un bloc libre
    soit prec = 0;
    soit g = @3[14680064];
    tantque g != 0 {
        soit taille = @3[g - 1] & 16777215;
        si taille >= n {
            si prec == 0 {
                @3[14680064] = @3[g];
            } sinon {
                @3[prec] = @3[g];
            }
            si taille >= n + 2 {
                __rendre_suite(g + n, g + taille);
                taille = n;
            }
            @3[g - 1] = taille;
            pour j dans 0..taille {
                @3[g + j] = 0;
            }
            retour 50331648 + g;
        }
        prec = g;
        g = @3[g];
    }
    soit p = @3[14680056];
    si p == 0 {
        p = 8388608;
    }
    si p + n + 1 > 14080048 {
        // le tas est plein (les 600 000 derniers mots restent au ramasse-miettes) : une purge, puis un second essai
        @3[14680056] = p;
        // pas de purge automatique si la dernière n'a rendu presque rien (le tas est vraiment plein : on ne s'acharne
        // pas, nouveau rend nul) ; une purge demandée (ramasser) lève cette interdiction
        si @3[14680252] == 0 && @3[14680253] == 0 {
            @3[14680252] = 1;
            soit libres = ramasser();
            @3[14680252] = 0;
            si libres < 355715 {
                @3[14680253] = 1;
            }
            si libres > n {
                retour nouveau(n);
            }
        }
        retour 0;
    }
    @3[p] = n;
    @3[14680056] = p + n + 1;
    pour k dans 0..n {
        @3[p + 1 + k] = 0;
    }
    retour 50331649 + p;
}
// un bloc libre d'en-tête h0, qui s'étend jusqu'à h1 (exclu) : rangé dans la liste de sa taille
fonction __rendre_suite(h0, h1) {
    soit taille = h1 - h0 - 1;
    @3[h0] = taille | 2147483648;
    soit k = taille;
    si k > 64 {
        k = 0;
    }
    @3[h0 + 1] = @3[14680064 + k];
    @3[14680064 + k] = h0 + 1;
}
// le tas est plein : le programme s'arrête avec un message clair (au lieu d'écrire à l'adresse 0)
fonction __verifier(h) {
    si h == 0 {
        __service(10, 0);
    }
    retour h;
}
fonction liberer(h) {
    soit p = h & 16777215;
    si p <= 8388608 || p >= @3[14680056] {
        retour;
    }
    soit taille = @3[p - 1];
    si taille >= 2147483648 {
        retour;
    }
    @3[p - 1] = taille | 2147483648;
    soit k = taille;
    si k > 64 {
        k = 0;
    }
    @3[p] = @3[14680064 + k];
    @3[14680064 + k] = p;
}
fonction tas_marque() {
    soit p = @3[14680056];
    si p == 0 {
        p = 8388608;
    }
    retour p;
}
fonction tas_retour(m) {
    @3[14680056] = m;
    pour k dans 0..65 {
        @3[14680064 + k] = 0;
    }
}
fonction tas_utilise() {
    soit p = @3[14680056];
    si p == 0 {
        retour 0;
    }
    retour p - 8388608;
}
fonction __marquer(v, deb, mar, pil, np, cap, haut) {
    soit e = v >> 24;
    si e != 3 && e != 0 {
        retour np;
    }
    soit p = v & 16777215;
    si p <= 8388608 || p >= haut {
        retour np;
    }
    soit k = p - 8388608;
    si ((@3[deb + k / 32] >> (k % 32)) & 1) == 0 || ((@3[mar + k / 32] >> (k % 32)) & 1) == 1 {
        retour np;
    }
    @3[mar + k / 32] = @3[mar + k / 32] | (1 << (k % 32));
    si np < cap {
        @3[pil + np] = p;
        retour np + 1;
    }
    @3[14680063] = 1;
    retour np;
}
fonction ramasser() {
    // ramasse-miettes : ce que tiennent les variables (la pile) et les poignées protégées reste ; tout bloc qu'on
    // ne peut plus atteindre est libéré. Rend le nombre de mots libérés.
    soit haut = @3[14680056];
    si haut == 0 {
        retour 0;
    }
    @3[14680254] = @3[14680254] + 1;
    si @3[14680252] == 0 {
        @3[14680253] = 0;
    }
    soit nm = (haut - 8388608) / 32 + 1;
    soit deb = haut;
    soit mar = haut + nm;
    soit pil = haut + 2 * nm;
    si pil + 1024 > 14680048 {
        retour 0;
    }
    soit cap = 14680048 - pil;
    pour i dans 0..(2 * nm) {
        @3[deb + i] = 0;
    }
    soit h = 8388608;
    tantque h < haut {
        soit kb = h + 1 - 8388608;
        @3[deb + kb / 32] = @3[deb + kb / 32] | (1 << (kb % 32));
        h = h + 1 + (@3[h] & 16777215);
    }
    @3[14680063] = 0;
    soit np = 0;
    pour a dans pile()..8388608 {
        np = __marquer(@0[a], deb, mar, pil, np, cap, haut);
    }
    pour r dans 0..@3[14680200] {
        np = __marquer(@3[14680201 + r], deb, mar, pil, np, cap, haut);
    }
    tantque np > 0 {
        np = np - 1;
        soit p = @3[pil + np];
        soit taille = @3[p - 1];
        si taille < 2147483648 {
            pour j dans 0..taille {
                np = __marquer(@3[p + j], deb, mar, pil, np, cap, haut);
            }
        }
    }
    si @3[14680063] == 1 {
        retour 0;
    }
    // balayage : les listes de blocs libres sont refaites ; des blocs libres voisins sont fondus en un seul ; une suite
    // libre qui touche le sommet fait redescendre le tas
    pour k2 dans 0..65 {
        @3[14680064 + k2] = 0;
    }
    soit libres = 0;
    soit debut_libre = 0;
    h = 8388608;
    tantque h < haut {
        soit b = h + 1;
        soit t2 = @3[h];
        soit kb2 = b - 8388608;
        si t2 >= 2147483648 || ((@3[mar + kb2 / 32] >> (kb2 % 32)) & 1) == 0 {
            si t2 < 2147483648 {
                libres = libres + t2;
            }
            si debut_libre == 0 {
                debut_libre = h;
            }
        } sinon si debut_libre != 0 {
            __rendre_suite(debut_libre, h);
            debut_libre = 0;
        }
        h = b + (t2 & 16777215);
    }
    si debut_libre != 0 {
        @3[14680056] = debut_libre;
    }
    retour libres;
}
fonction purges() {
    retour @3[14680254];
}
fonction proteger(h) {
    soit n = @3[14680200];
    si n < 50 {
        @3[14680201 + n] = h;
        @3[14680200] = n + 1;
    }
}
fonction sauver_bloc(nom, adr, n) {
    @3[14680060] = nom;
    @3[14680061] = adr;
    @3[14680062] = n;
    retour __service(6, 0);
}
fonction charger_bloc(nom, adr, n) {
    @3[14680060] = nom;
    @3[14680061] = adr;
    @3[14680062] = n;
    retour __service(7, 0);
}
fonction __nom_ent(nom) {
    soit n = longueur(nom);
    soit t = texte_neuf(n + 4);
    pour i dans 0..n {
        changer_car(t, i, car(nom, i));
    }
    changer_car(t, n, 46);
    changer_car(t, n + 1, 101);
    changer_car(t, n + 2, 110);
    changer_car(t, n + 3, 116);
    retour t;
}
fonction sauver_tas(nom, racine) {
    // tout le tas dans le fichier « nom », et son en-tête (sommet, listes libres, racine, format) dans « nom.ent »
    @3[14680063] = racine;
    @3[14680255] = 3;
    soit haut = tas_marque();
    soit e = __nom_ent(nom);
    soit r = sauver_bloc(e, 50331648 + 14680056, 200);
    si r == 4294967295 {
        retour r;
    }
    retour sauver_bloc(nom, 50331648 + 8388608, haut - 8388608);
}
fonction charger_tas(nom) {
    // rend la racine rangée par sauver_tas, ou 0 si le fichier n'existe pas
    // l'en-tête est lu à part (dans la réserve du ramasse-miettes) : un fichier absent, ou d'un autre format, ne
    // touche à rien et rend 0
    soit e = __nom_ent(nom);
    si charger_bloc(e, 50331648 + 14400000, 200) != 200 || @3[14400199] != 3 {
        retour 0;
    }
    pour i dans 0..200 {
        @3[14680056 + i] = @3[14400000 + i];
    }
    charger_bloc(nom, 50331648 + 8388608, @3[14680056] - 8388608);
    retour @3[14680063];
}
fonction ecrire_texte(c, t) {
    pour i dans 0..longueur(t) {
        ecrire_car(c, car(t, i));
    }
}
fonction ecrire_nombre(c, n) {
    si n >= 10 {
        ecrire_nombre(c, n / 10);
    }
    ecrire_car(c, 48 + n % 10);
}
fonction texte_neuf(n) {
    soit t = __verifier(nouveau(n + 1));
    @(t >> 24)[t & 16777215] = n;
    retour t;
}
fonction __texte_tas(t): texte {
    // un texte rangé dans le tas (champ, tableau, dictionnaire) : un texte écrit dans le programme (gardé avec le code, à
    // l'étage 0) est recopié dans le tas, pour qu'une mémoire sauvée (sauver_tas) reste juste quand le programme change
    si t == 0 || (t >> 24) != 0 {
        retour t;
    }
    soit n = longueur(t);
    soit r = texte_neuf(n);
    pour i dans 0..n {
        changer_car(r, i, car(t, i));
    }
    retour r;
}
fonction __mettre(c, x) {
    si c < 65536 {
        ecrire_car(c, x);
    } sinon {
        soit e = c >> 24;
        soit a = c & 16777215;
        soit n = @(e)[a];
        @(e)[a + 1 + n] = x;
        @(e)[a] = n + 1;
    }
}
fonction __mettre_nombre(c, n) {
    si n >= 10 {
        __mettre_nombre(c, n / 10);
    }
    __mettre(c, 48 + n % 10);
}
fonction ecrire_entier(c, n) {
    si n >= 2147483648 {
        __mettre(c, 45);
        n = 0 - n;
    }
    __mettre_nombre(c, n);
}
fonction ecrire_hexa(c, n) {
    __mettre(c, 35);
    pour i dans 0..8 {
        soit k = (n >> (28 - 4 * i)) & 15;
        si k < 10 { __mettre(c, 48 + k); } sinon { __mettre(c, 55 + k); }
    }
}
fonction __ecrire_chiffres(c, q, d) {
    si d > 1 {
        __ecrire_chiffres(c, q / 10, d - 1);
    }
    __mettre(c, 48 + q % 10);
}
fonction ecrire_flottant(c, x: flottant, d) {
    soit b = bits(x);
    si b >= 2147483648 {
        __mettre(c, 45);
        b = b & 2147483647;
    }
    si b >= 2139095040 {
        si b == 2139095040 {
            __mettre(c, 105); __mettre(c, 110); __mettre(c, 102);
        } sinon {
            __mettre(c, 110); __mettre(c, 97); __mettre(c, 110);
        }
        retour;
    }
    soit y = comme_flottant(b);
    soit auto = 0;
    si d == 4294967295 { auto = 1; d = 6; }
    si d > 9 { d = 9; }
    soit e = 0;
    soit eneg = 0;
    si y >= 10000000.0 || (auto == 1 && y < 0.0001 && b != 0) {
        tantque y >= 10.0 { y = y / 10.0; e = e + 1; }
        tantque y < 1.0 { y = y * 10.0; e = e + 1; eneg = 1; }
    }
    soit ip = entier(y);
    si auto == 1 {
        soit nc = 1;
        soit t = ip / 10;
        tantque t > 0 { nc = nc + 1; t = t / 10; }
        si nc >= 7 { d = 1; } sinon { d = 7 - nc; }
    }
    soit pe = 1;
    pour i dans 0..d { pe = pe * 10; }
    soit q = arrondi((y - flottant(ip)) * flottant(pe));
    si q >= pe { ip = ip + 1; q = q - pe; }
    si auto == 1 {
        tantque d > 1 && q % 10 == 0 { q = q / 10; d = d - 1; }
    }
    __mettre_nombre(c, ip);
    si d > 0 {
        __mettre(c, 46);
        __ecrire_chiffres(c, q, d);
    }
    si e > 0 {
        __mettre(c, 101);
        si eneg == 1 { __mettre(c, 45); }
        __mettre_nombre(c, e);
    }
}
fonction ecrire_long(c, a: long) {
    si a < 0L {
        __mettre(c, 45);
        a = 0L - a;
    }
    si a >= 10L {
        ecrire_long(c, a / 10L);
    }
    __mettre(c, 48 + bas(a % 10L));
}
// ---- grands entiers (limbes de 16 bits, mot bas d'abord) pour l'écriture décimale exacte des flottants
fonction __bn_neuf(v) {
    soit t = tableau(0);
    si v != 0 {
        ajouter(t, v & 65535);
        si (v >> 16) != 0 { ajouter(t, v >> 16); }
    }
    retour t;
}
fonction __bn_copie(a) {
    soit r = tableau(0);
    pour i dans 0..longueur(a) { ajouter(r, a[i]); }
    retour r;
}
fonction __bn_mul(a, m) {
    soit c = 0;
    pour i dans 0..longueur(a) {
        soit p = a[i] * m + c;
        a[i] = p & 65535;
        c = p >> 16;
    }
    si c != 0 { ajouter(a, c); }
}
fonction __bn_mul10(a, n) {
    tantque n >= 4 { __bn_mul(a, 10000); n = n - 4; }
    tantque n > 0 { __bn_mul(a, 10); n = n - 1; }
}
fonction __bn_cmp(a, b) {
    soit na = longueur(a);
    soit nb = longueur(b);
    si na != nb {
        si na > nb { retour 1; }
        retour 2;
    }
    soit i = na;
    tantque i > 0 {
        i = i - 1;
        si a[i] != b[i] {
            si a[i] > b[i] { retour 1; }
            retour 2;
        }
    }
    retour 0;
}
fonction __bn_ajouter(a, b) {
    soit n = longueur(b);
    si longueur(a) > n { n = longueur(a); }
    soit c = 0;
    pour i dans 0..n {
        soit x = c;
        soit na = longueur(a);
        si i < na { x = x + a[i]; }
        si i < longueur(b) { x = x + b[i]; }
        si i < na { a[i] = x & 65535; } sinon { ajouter(a, x & 65535); }
        c = x >> 16;
    }
    si c != 0 { ajouter(a, c); }
}
fonction __bn_sub(a, b) {
    soit emprunt = 0;
    pour i dans 0..longueur(a) {
        soit y = emprunt;
        si i < longueur(b) { y = y + b[i]; }
        si a[i] >= y { a[i] = a[i] - y; emprunt = 0; } sinon { a[i] = a[i] + 65536 - y; emprunt = 1; }
    }
    tantque longueur(a) > 0 && a[longueur(a) - 1] == 0 { retirer(a); }
}
fonction __bn_decaler(a, k) {
    si longueur(a) == 0 { retour; }
    soit q = k >> 4;
    soit b = k & 15;
    si b != 0 {
        soit c = 0;
        pour i dans 0..longueur(a) {
            soit x = (a[i] << b) | c;
            a[i] = x & 65535;
            c = x >> 16;
        }
        si c != 0 { ajouter(a, c); }
    }
    si q != 0 {
        soit n = longueur(a);
        pour i dans 0..q { ajouter(a, 0); }
        soit j = n;
        tantque j > 0 { j = j - 1; a[j + q] = a[j]; }
        pour i dans 0..q { a[i] = 0; }
    }
}
fonction __bn_bits(a) {
    soit n = longueur(a);
    si n == 0 { retour 0; }
    soit h = a[n - 1];
    soit b = 0;
    tantque h != 0 { b = b + 1; h = h >> 1; }
    retour 16 * (n - 1) + b;
}
// chiffres décimaux les plus courts qui redonnent le flottant f * 2^e (Burger et Dybvig) : le tableau rendu contient
// k + 20000 (la valeur vaut 0,d1d2d3... fois 10^k) puis les chiffres ; bord vaut 1 si l'écart inférieur est la moitié,
// 2 s'il est le quart (le bas d'une puissance de 4 du flottant_petuar)
fonction __dragon(f, e, bord) {
    soit pair = 1;
    si f[0] & 1 { pair = 0; }
    soit r = __bn_copie(f);
    soit s = __bn_neuf(1);
    soit mp = __bn_neuf(1);
    soit mm = __bn_neuf(1);
    si e < 2147483648 {
        si bord == 0 {
            __bn_decaler(r, e + 1);
            s = __bn_neuf(2);
            __bn_decaler(mp, e);
            __bn_decaler(mm, e);
        } sinon si bord == 1 {
            __bn_decaler(r, e + 2);
            s = __bn_neuf(4);
            __bn_decaler(mp, e + 1);
            __bn_decaler(mm, e);
        } sinon {
            __bn_decaler(r, e + 3);
            s = __bn_neuf(8);
            __bn_decaler(mp, e + 2);
            __bn_decaler(mm, e);
        }
    } sinon {
        soit n = 0 - e;
        si bord == 0 {
            __bn_decaler(r, 1);
            __bn_decaler(s, n + 1);
        } sinon si bord == 1 {
            __bn_decaler(r, 2);
            __bn_decaler(s, n + 2);
            mp = __bn_neuf(2);
        } sinon {
            __bn_decaler(r, 3);
            __bn_decaler(s, n + 3);
            mp = __bn_neuf(4);
        }
    }
    // estimation par défaut de l'exposant décimal : log10(2) = 0,30103 ; le reste est corrigé par la boucle
    soit x = e + __bn_bits(f) - 1;
    soit est = 0;
    si x < 2147483648 {
        est = x * 30102 / 100000;
        __bn_mul10(s, est);
    } sinon {
        soit m = 0 - x;
        est = (m * 30104 + 99999) / 100000;
        __bn_mul10(r, est);
        __bn_mul10(mp, est);
        __bn_mul10(mm, est);
        est = 0 - est;
    }
    soit k = est;
    soit encore = 1;
    tantque encore == 1 {
        soit t1 = __bn_copie(r);
        __bn_ajouter(t1, mp);
        soit c = __bn_cmp(t1, s);
        si (pair == 1 && c != 2) || (pair == 0 && c == 1) {
            __bn_mul(s, 10);
            k = k + 1;
        } sinon {
            encore = 0;
        }
    }
    __bn_mul(r, 10);
    __bn_mul(mp, 10);
    __bn_mul(mm, 10);
    soit dig = tableau(0);
    ajouter(dig, k + 20000);
    soit fini = 0;
    tantque fini == 0 {
        soit d = 0;
        tantque __bn_cmp(r, s) != 2 {
            __bn_sub(r, s);
            d = d + 1;
        }
        soit c1 = __bn_cmp(r, mm);
        soit tc1 = 0;
        si (pair == 1 && c1 != 1) || (pair == 0 && c1 == 2) { tc1 = 1; }
        soit t = __bn_copie(r);
        __bn_ajouter(t, mp);
        soit c2 = __bn_cmp(t, s);
        soit tc2 = 0;
        si (pair == 1 && c2 != 2) || (pair == 0 && c2 == 1) { tc2 = 1; }
        si tc1 == 0 && tc2 == 0 {
            ajouter(dig, d);
            __bn_mul(r, 10);
            __bn_mul(mp, 10);
            __bn_mul(mm, 10);
        } sinon {
            si tc1 == 1 && tc2 == 0 {
                ajouter(dig, d);
            } sinon si tc1 == 0 && tc2 == 1 {
                ajouter(dig, d + 1);
            } sinon {
                __bn_mul(r, 2);
                si __bn_cmp(r, s) == 2 { ajouter(dig, d); } sinon { ajouter(dig, d + 1); }
            }
            fini = 1;
        }
    }
    retour dig;
}
fonction __ecrire_chiffres_dec(c, dig, de, a) {
    pour i dans de..a { __mettre(c, 48 + dig[i]); }
}
fonction __bn_divpetit(a, m) {
    soit r = 0;
    soit i = longueur(a);
    tantque i > 0 {
        i = i - 1;
        soit x = (r << 16) | a[i];
        a[i] = x / m;
        r = x % m;
    }
    tantque longueur(a) > 0 && a[longueur(a) - 1] == 0 { retirer(a); }
    retour r;
}
fonction __bn_bit(a, i) {
    si (i >> 4) >= longueur(a) { retour 0; }
    retour (a[i >> 4] >> (i & 15)) & 1;
}
fonction __bn_bas_nul(a, n) {
    soit q = n >> 4;
    pour i dans 0..q {
        si i < longueur(a) && a[i] != 0 { retour 0; }
    }
    si (n & 15) != 0 && q < longueur(a) {
        si (a[q] & ((1 << (n & 15)) - 1)) != 0 { retour 0; }
    }
    retour 1;
}
fonction __bn_droite(a, n) {
    soit q = n >> 4;
    soit b = n & 15;
    soit m = longueur(a);
    pour i dans 0..m {
        soit lo = 0;
        si i + q < m { lo = a[i + q] >> b; }
        soit hi = 0;
        si b != 0 && i + q + 1 < m { hi = (a[i + q + 1] << (16 - b)) & 65535; }
        a[i] = lo | hi;
    }
    tantque longueur(a) > 0 && a[longueur(a) - 1] == 0 { retirer(a); }
}
// f * 2^e écrit avec d décimales exactes (arrondi au plus proche, pair en cas d'égalité, comme printf)
fonction __ecrire_fixe(c, f, e, d) {
    soit x = __bn_copie(f);
    __bn_mul10(x, d);
    si e < 2147483648 {
        __bn_decaler(x, e);
    } sinon {
        soit n = 0 - e;
        soit demi = __bn_bit(x, n - 1);
        soit reste = 1 - __bn_bas_nul(x, n - 1);
        soit impair = __bn_bit(x, n);
        __bn_droite(x, n);
        si demi == 1 && (reste == 1 || impair == 1) { __bn_ajouter(x, __bn_neuf(1)); }
    }
    soit dd = tableau(0);
    tantque longueur(x) > 0 {
        soit q = __bn_divpetit(x, 10000);
        ajouter(dd, q % 10);
        ajouter(dd, (q / 10) % 10);
        ajouter(dd, (q / 100) % 10);
        ajouter(dd, q / 1000);
    }
    tantque longueur(dd) > d + 1 && dd[longueur(dd) - 1] == 0 { retirer(dd); }
    tantque longueur(dd) < d + 1 { ajouter(dd, 0); }
    soit i = longueur(dd);
    tantque i > d {
        i = i - 1;
        __mettre(c, 48 + dd[i]);
    }
    si d > 0 {
        __mettre(c, 46);
        tantque i > 0 {
            i = i - 1;
            __mettre(c, 48 + dd[i]);
        }
    }
}
// d décimales, ou 4294967295 pour les chiffres les plus courts qui redonnent exactement le nombre
fonction ecrire_flottant_64(c, x: flottant_64, d) {
    soit b = bits(x);
    soit lo = bas(b);
    soit hi = haut(b);
    soit ex = (hi >> 20) & 2047;
    soit mh = hi & 1048575;
    si ex == 2047 && (mh != 0 || lo != 0) {
        __mettre(c, 110); __mettre(c, 97); __mettre(c, 110);
        retour;
    }
    si hi >= 2147483648 {
        __mettre(c, 45);
    }
    si ex == 2047 {
        __mettre(c, 105); __mettre(c, 110); __mettre(c, 102);
        retour;
    }
    soit f = tableau(0);
    ajouter(f, lo & 65535);
    ajouter(f, lo >> 16);
    ajouter(f, mh & 65535);
    soit t3 = mh >> 16;
    soit e = 0;
    si ex == 0 {
        e = 0 - 1074;
    } sinon {
        t3 = t3 | 16;
        e = ex - 1075;
    }
    ajouter(f, t3);
    tantque longueur(f) > 0 && f[longueur(f) - 1] == 0 { retirer(f); }
    si d != 4294967295 {
        si d > 40 { d = 40; }
        __ecrire_fixe(c, f, e, d);
        retour;
    }
    si longueur(f) == 0 {
        __mettre(c, 48); __mettre(c, 46); __mettre(c, 48);
        retour;
    }
    soit bord = 0;
    si ex > 1 && mh == 0 && lo == 0 { bord = 1; }
    __ecrire_dragon(c, __dragon(f, e, bord));
}
// écrit les chiffres rendus par __dragon (en fixe de 10^-3 à 10^16, sinon avec un exposant)
fonction __ecrire_dragon(c, dig) {
    soit n = longueur(dig) - 1;
    soit k = dig[0];
    si k >= 19997 && k <= 20016 {
        si k <= 20000 {
            __mettre(c, 48); __mettre(c, 46);
            pour i dans 0..(20000 - k) { __mettre(c, 48); }
            __ecrire_chiffres_dec(c, dig, 1, n + 1);
        } sinon {
            soit ent = k - 20000;
            pour i dans 0..ent {
                si i < n { __mettre(c, 48 + dig[1 + i]); } sinon { __mettre(c, 48); }
            }
            __mettre(c, 46);
            si n > ent { __ecrire_chiffres_dec(c, dig, 1 + ent, n + 1); } sinon { __mettre(c, 48); }
        }
    } sinon {
        __mettre(c, 48 + dig[1]);
        __mettre(c, 46);
        si n > 1 { __ecrire_chiffres_dec(c, dig, 2, n + 1); } sinon { __mettre(c, 48); }
        __mettre(c, 101);
        si k < 20001 {
            __mettre(c, 45);
            __mettre_nombre(c, 20001 - k);
        } sinon {
            __mettre_nombre(c, k - 20001);
        }
    }
}
fonction ecrire_logique(c, l: logique) {
    selon l {
        vrai { __mettre(c, 118); __mettre(c, 114); __mettre(c, 97); __mettre(c, 105); }
        faux { __mettre(c, 102); __mettre(c, 97); __mettre(c, 117); __mettre(c, 120); }
        inconnu {
            __mettre(c, 105); __mettre(c, 110); __mettre(c, 99); __mettre(c, 111);
            __mettre(c, 110); __mettre(c, 110); __mettre(c, 117);
        }
        variable {
            __mettre(c, 118); __mettre(c, 97); __mettre(c, 114); __mettre(c, 105);
            __mettre(c, 97); __mettre(c, 98); __mettre(c, 108); __mettre(c, 101);
        }
    }
}
// ---- la frontière avec le binaire : Belnap reste le cœur de Vercintorix ; binaire() donne le code d'échange
// 0 non, 1 oui, 2 inconnu, 3 variable (le bit fort dit « pas binaire ») ; quaternaire() fait le chemin inverse
fonction binaire(l: logique) {
    soit c = entier(l);
    soit v = c >> 1;
    retour ((((v ^ c) & 1) ^ 1) << 1) | v;
}
fonction quaternaire(b): logique {
    soit lo = b & 1;
    soit hi = (b >> 1) & 1;
    retour comme_logique((lo << 1) | (1 - (hi ^ lo)));
}
// les mêmes sur 16 logiques rangés dans un mot (un par quit)
fonction binaire16(x) {
    soit v = (x >> 1) & 1431655765;
    soit f = x & 1431655765;
    retour ((~(v ^ f) & 1431655765) << 1) | v;
}
fonction quaternaire16(b) {
    soit lo = b & 1431655765;
    soit hi = (b >> 1) & 1431655765;
    retour (lo << 1) | (~(hi ^ lo) & 1431655765);
}
fonction afficher(x) {
    ecrire_entier(1, x);
    ecrire_car(1, 10);
}
fonction __afficher_f(x: flottant) {
    ecrire_flottant(1, x, 4294967295);
    ecrire_car(1, 10);
}
fonction __afficher_l(x: long) {
    ecrire_long(1, x);
    ecrire_car(1, 10);
}
fonction __afficher_d(x: flottant_64) {
    ecrire_flottant_64(1, x, 4294967295);
    ecrire_car(1, 10);
}
fonction __afficher_q(x: logique) {
    ecrire_logique(1, x);
    ecrire_car(1, 10);
}
fonction __afficher_t(t) {
    ecrire_texte(1, t);
    ecrire_car(1, 10);
}
fonction ecrire(x) {
    ecrire_entier(1, x);
}
fonction __ecrire_f(x: flottant) {
    ecrire_flottant(1, x, 4294967295);
}
fonction __ecrire_l(x: long) {
    ecrire_long(1, x);
}
fonction __ecrire_d(x: flottant_64) {
    ecrire_flottant_64(1, x, 4294967295);
}
fonction __ecrire_q(x: logique) {
    ecrire_logique(1, x);
}
fonction __ecrire_t(t) {
    ecrire_texte(1, t);
}
fonction __texte_t(t): texte {
    retour t;
}
fonction __texte_fin(t): texte {
    // le dernier bloc du tas prend juste la place du texte écrit ; un bloc repris ailleurs garde sa taille
    soit p = t & 16777215;
    si p + (@3[p - 1] & 16777215) == @3[14680056] {
        @3[p - 1] = 1 + longueur(t);
        @3[14680056] = p + 1 + longueur(t);
    }
    retour t;
}
fonction texte(n): texte {
    soit t = __verifier(nouveau(16));
    ecrire_entier(t, n);
    retour __texte_fin(t);
}
fonction __texte_f(x: flottant): texte {
    soit t = __verifier(nouveau(40));
    ecrire_flottant(t, x, 4294967295);
    retour __texte_fin(t);
}
fonction __texte_l(x: long): texte {
    soit t = __verifier(nouveau(24));
    ecrire_long(t, x);
    retour __texte_fin(t);
}
fonction __texte_d(x: flottant_64): texte {
    soit t = __verifier(nouveau(40));
    ecrire_flottant_64(t, x, 4294967295);
    retour __texte_fin(t);
}
fonction __texte_q(x: logique): texte {
    soit t = __verifier(nouveau(12));
    ecrire_logique(t, x);
    retour __texte_fin(t);
}
fonction __texte_plus(a, b): texte {
    soit na = longueur(a);
    soit nb = longueur(b);
    soit t = texte_neuf(na + nb);
    pour i dans 0..na {
        changer_car(t, i, car(a, i));
    }
    pour i dans 0..nb {
        changer_car(t, na + i, car(b, i));
    }
    retour t;
}
fonction sous_texte(t, debut, fin): texte {
    si fin > longueur(t) {
        fin = longueur(t);
    }
    si debut >= fin {
        retour texte_neuf(0);
    }
    soit r = texte_neuf(fin - debut);
    pour i dans debut..fin {
        changer_car(r, i - debut, car(t, i));
    }
    retour r;
}
fonction position(t, motif) {
    soit n = longueur(t);
    soit m = longueur(motif);
    si m > n {
        retour 4294967295;
    }
    pour i dans 0..n - m + 1 {
        soit k = 0;
        tantque k < m && car(t, i + k) == car(motif, k) {
            k = k + 1;
        }
        si k == m {
            retour i;
        }
    }
    retour 4294967295;
}
fonction nombre(t) {
    soit r = 0;
    soit i = 0;
    soit neg = 0;
    si longueur(t) > 0 && car(t, 0) == 45 {
        neg = 1;
        i = 1;
    }
    tantque i < longueur(t) && car(t, i) >= 48 && car(t, i) <= 57 {
        r = r * 10 + car(t, i) - 48;
        i = i + 1;
    }
    si neg == 1 {
        retour 0 - r;
    }
    retour r;
}
fonction pi(): flottant { retour 3.1415927; }
fonction plancher(x: flottant): flottant {
    si !(abs(x) < 8388608.0) { retour x; }
    soit t = flottant_signe(entier(x));
    si t > x { t = t - 1.0; }
    retour t;
}
fonction plafond(x: flottant): flottant {
    soit t = plancher(x);
    si t < x { t = t + 1.0; }
    retour t;
}
fonction __sin_cos(x: flottant, decale): flottant {
    si !(abs(x) < 100000000.0) { retour comme_flottant(2143289344); }
    soit k = arrondi(x * 0.63661975);
    soit fk = flottant_signe(k);
    soit r = ((x - fk * 1.5703125) - fk * 0.00048382679) - fk * 0.0000000000025632829;
    soit s = r * r;
    soit q = (k + decale) & 3;
    soit v = 0.0;
    si (q & 1) == 0 {
        v = r * (1.0 - s * (0.16666667 - s * (0.0083333333 - s * (0.0001984127 - s * 0.0000027557319))));
    } sinon {
        v = 1.0 - s * (0.5 - s * (0.041666667 - s * (0.0013888889 - s * (0.000024801587 - s * 0.00000027557319))));
    }
    si q >= 2 { retour 0.0 - v; }
    retour v;
}
fonction sinus(x: flottant): flottant { retour __sin_cos(x, 0); }
fonction cosinus(x: flottant): flottant { retour __sin_cos(x, 1); }
fonction tangente(x: flottant): flottant { retour __sin_cos(x, 0) / __sin_cos(x, 1); }
fonction exponentielle(x: flottant): flottant {
    si x > 88.72284 { retour comme_flottant(2139095040); }
    si x < -103.97208 { retour 0.0; }
    soit n = arrondi(x * 1.442695);
    soit fn = flottant_signe(n);
    soit r = (x - fn * 0.69314575) - fn * 0.0000014286068;
    soit p = 1.0 + r * (1.0 + r * (0.5 + r * (0.16666667 + r * (0.041666667 + r * (0.0083333333
        + r * (0.0013888889 + r * 0.0001984127))))));
    si n .< 0 - 125 {
        retour comme_flottant(bits(p) + ((n + 64) << 23)) * 0.0000000000000000000542101086242752217;
    }
    si n .> 127 {
        retour comme_flottant(bits(p) + ((n - 1) << 23)) * 2.0;
    }
    retour comme_flottant(bits(p) + (n << 23));
}
fonction logarithme(x: flottant): flottant {
    si x != x || x < 0.0 { retour comme_flottant(2143289344); }
    si x == 0.0 { retour comme_flottant(4286578688); }
    si x > 340282350000000000000000000000000000000.0 { retour x; }
    soit b = bits(x);
    soit e = 0;
    si b < 8388608 {
        b = bits(x * 8388608.0);
        e = 0 - 23;
    }
    e = e + (b >> 23) - 127;
    soit m = comme_flottant((b & 8388607) | 1065353216);
    si m > 1.4142135 {
        m = m * 0.5;
        e = e + 1;
    }
    soit f = (m - 1.0) / (m + 1.0);
    soit s = f * f;
    soit lm = 2.0 * f * (1.0 + s * (0.33333333 + s * (0.2 + s * (0.14285714 + s * (0.11111111 + s * 0.09090909)))));
    soit fe = flottant_signe(e);
    retour fe * 0.69314575 + (fe * 0.0000014286068 + lm);
}
fonction puissance(x: flottant, y: flottant): flottant {
    si y == 0.0 { retour 1.0; }
    si x == 0.0 {
        si y < 0.0 { retour comme_flottant(2139095040); }
        retour 0.0;
    }
    si x < 0.0 {
        si plancher(y) != y { retour comme_flottant(2143289344); }
        soit r = exponentielle(y * logarithme(0.0 - x));
        si abs(y) < 16777216.0 && (entier(abs(y)) & 1) == 1 { retour 0.0 - r; }
        retour r;
    }
    retour exponentielle(y * logarithme(x));
}
fonction arctangente(x: flottant): flottant {
    si x != x { retour x; }
    soit a = abs(x);
    soit inv = 0;
    si a > 1.0 { a = 1.0 / a; inv = 1; }
    soit ajout = 0.0;
    si a > 0.26794919 {
        a = (a * 1.7320508 - 1.0) / (a + 1.7320508);
        ajout = 0.52359878;
    }
    soit s = a * a;
    soit v = ajout + a * (1.0 - s * (0.33333333 - s * (0.2 - s * (0.14285714 - s * (0.11111111 - s * 0.09090909)))));
    si inv == 1 { v = 1.5707964 - v; }
    si x < 0.0 { retour 0.0 - v; }
    retour v;
}
fonction arctangente2(y: flottant, x: flottant): flottant {
    si x > 0.0 { retour arctangente(y / x); }
    si x < 0.0 {
        si y < 0.0 { retour arctangente(y / x) - 3.1415927; }
        retour arctangente(y / x) + 3.1415927;
    }
    si y > 0.0 { retour 1.5707964; }
    si y < 0.0 { retour 0.0 - 1.5707964; }
    retour 0.0;
}
fonction arcsinus(x: flottant): flottant {
    si !(abs(x) <= 1.0) { retour comme_flottant(2143289344); }
    si abs(x) == 1.0 {
        si x > 0.0 { retour 1.5707964; }
        retour 0.0 - 1.5707964;
    }
    retour arctangente(x / racine(1.0 - x * x));
}
fonction arccosinus(x: flottant): flottant {
    si !(abs(x) <= 1.0) { retour comme_flottant(2143289344); }
    retour 1.5707964 - arcsinus(x);
}
fonction pi_64(): flottant_64 { retour 3.141592653589793D; }
fonction __nan_64(): flottant_64 { retour comme_flottant_64(0x7FF8000000000000L); }
fonction __inf_64(): flottant_64 { retour comme_flottant_64(0x7FF0000000000000L); }
fonction __p2_64(n): flottant_64 { retour flottant_64_de((n + 1023) << 20, 0); }
fonction plancher_64(x: flottant_64): flottant_64 {
    si !(abs(x) < 4503599627370496.0D) || x == 0.0D { retour x; }
    soit t = flottant_64(long(x));
    si t > x { t = t - 1.0D; }
    retour t;
}
fonction plafond_64(x: flottant_64): flottant_64 {
    soit t = plancher_64(x);
    si t < x { t = t + 1.0D; }
    retour t;
}
fonction __sin_cos_64(x: flottant_64, decale): flottant_64 {
    soit ax = abs(x);
    si !(ax < 1647099.0D) { retour __nan_64(); }
    soit k = 0;
    soit y0 = x;
    soit y1 = 0.0D;
    si ax > 0.7853981633974483D {
        k = arrondi(x * 0.6366197723675814D);
        soit fk = flottant_64_signe(k);
        soit r = x - fk * 1.57079632673412561417D;
        soit w = fk * 6.07710050650619224932e-11D;
        y0 = r - w;
        soit j = (haut(x) >> 20) & 2047;
        soit i = j - ((haut(y0) >> 20) & 2047);
        si i > 16 {
            soit t = r;
            w = fk * 6.07710050630396597660e-11D;
            r = t - w;
            w = fk * 2.02226624879595063154e-21D - ((t - r) - w);
            y0 = r - w;
            i = j - ((haut(y0) >> 20) & 2047);
            si i > 49 {
                t = r;
                w = fk * 2.02226624871116645580e-21D;
                r = t - w;
                w = fk * 8.47842766036889956997e-32D - ((t - r) - w);
                y0 = r - w;
            }
        }
        y1 = (r - y0) - w;
    }
    soit q = (k + decale) & 3;
    soit z = y0 * y0;
    soit v = 0.0D;
    si (q & 1) == 0 {
        soit vv = z * y0;
        soit rr = 8.33333333332248946124e-03D + z * (-1.98412698298579493134e-04D + z * (2.75573137070700676789e-06D
            + z * (-2.50507602534068634195e-08D + z * 1.58969099521155010221e-10D)));
        v = y0 - ((z * (0.5D * y1 - vv * rr) - y1) - vv * -1.66666666666666324348e-01D);
    } sinon {
        soit rc = z * (4.16666666666666019037e-02D + z * (-1.38888888888741095749e-03D + z * (2.48015872894767294178e-05D
            + z * (-2.75573143513906633035e-07D + z * (2.08757232129817482790e-09D + z * -1.13596475577881948265e-11D)))));
        soit hz = 0.5D * z;
        soit w1 = 1.0D - hz;
        v = w1 + (((1.0D - w1) - hz) + (z * rc - y0 * y1));
    }
    si q >= 2 { retour -v; }
    retour v;
}
fonction sinus_64(x: flottant_64): flottant_64 { retour __sin_cos_64(x, 0); }
fonction cosinus_64(x: flottant_64): flottant_64 { retour __sin_cos_64(x, 1); }
fonction tangente_64(x: flottant_64): flottant_64 { retour __sin_cos_64(x, 0) / __sin_cos_64(x, 1); }
fonction exponentielle_64(x: flottant_64): flottant_64 {
    si x != x { retour x; }
    si x > 709.782712893384D { retour __inf_64(); }
    si x < -745.1332191019411D { retour 0.0D; }
    si abs(x) < 3.725290298461914e-09D { retour 1.0D + x; }
    soit k = arrondi(x * 1.44269504088896338700D);
    soit fk = flottant_64_signe(k);
    soit hi = x - fk * 6.93147180369123816490e-01D;
    soit lo = fk * 1.90821492927058770002e-10D;
    soit r = hi - lo;
    soit t = r * r;
    soit c = r - t * (1.66666666666666019037e-01D + t * (-2.77777777770155933842e-03D + t * (6.61375632143793436117e-05D
        + t * (-1.65339022054652515390e-06D + t * 4.13813679705723846039e-08D))));
    soit y = 1.0D - ((lo - (r * c) / (2.0D - c)) - hi);
    si k .> 1023 {
        retour y * __p2_64(1023) * __p2_64(k - 1023);
    }
    si k .< 0 - 1021 {
        retour y * __p2_64(k + 1000) * __p2_64(0 - 1000);
    }
    retour y * __p2_64(k);
}
fonction logarithme_64(x: flottant_64): flottant_64 {
    si x != x { retour x; }
    si x < 0.0D { retour __nan_64(); }
    si x == 0.0D { retour -__inf_64(); }
    si x == __inf_64() { retour x; }
    soit k = 0;
    soit hx = haut(x);
    si hx < 1048576 {
        k = 0 - 54;
        x = x * 18014398509481984.0D;
        hx = haut(x);
    }
    k = k + (hx >> 20) - 1023;
    hx = hx & 1048575;
    soit i = (hx + 614244) & 1048576;
    x = flottant_64_de(hx | (i ^ 1072693248), bas(x));
    k = k + (i >> 20);
    soit f = x - 1.0D;
    soit s = f / (2.0D + f);
    soit dk = flottant_64_signe(k);
    soit z = s * s;
    soit w = z * z;
    soit t1 = w * (3.999999999940941908e-01D + w * (2.222219843214978396e-01D + w * 1.531383769920937332e-01D));
    soit t2 = z * (6.666666666666735130e-01D + w * (2.857142874366239149e-01D + w * (1.818357216161805012e-01D + w * 1.479819860511658591e-01D)));
    soit rr = t2 + t1;
    soit hfsq = 0.5D * f * f;
    retour dk * 6.93147180369123816490e-01D - ((hfsq - (s * (hfsq + rr) + dk * 1.90821492927058770002e-10D)) - f);
}
fonction puissance_64(x: flottant_64, y: flottant_64): flottant_64 {
    si y == 0.0D { retour 1.0D; }
    si x != x || y != y { retour __nan_64(); }
    soit entiere = plancher_64(y) == y;
    soit impaire = 0;
    si entiere && abs(y) < 9007199254740992.0D {
        impaire = (long(abs(y)) & 1L) != 0L;
    }
    si x == 0.0D {
        si y < 0.0D { retour __inf_64(); }
        retour 0.0D;
    }
    si entiere && abs(y) <= 1024.0D {
        soit n = entier(abs(y));
        soit b = x;
        soit r = 1.0D;
        tantque n != 0 {
            si (n & 1) == 1 { r = r * b; }
            b = b * b;
            n = n >> 1;
        }
        si y < 0.0D { retour 1.0D / r; }
        retour r;
    }
    si x < 0.0D {
        si !entiere { retour __nan_64(); }
        soit e2 = exponentielle_64(y * logarithme_64(-x));
        si impaire { retour -e2; }
        retour e2;
    }
    retour exponentielle_64(y * logarithme_64(x));
}
fonction arctangente_64(x: flottant_64): flottant_64 {
    si x != x { retour x; }
    soit ax = abs(x);
    soit id = 0 - 1;
    soit u = ax;
    si ax >= 7.378697629483821e+19D {
        si x < 0.0D { retour -1.5707963267948966D; }
        retour 1.5707963267948966D;
    }
    si ax >= 0.4375D {
        si ax < 1.1875D {
            si ax < 0.6875D {
                id = 0;
                u = (2.0D * ax - 1.0D) / (2.0D + ax);
            } sinon {
                id = 1;
                u = (ax - 1.0D) / (ax + 1.0D);
            }
        } sinon {
            si ax < 2.4375D {
                id = 2;
                u = (ax - 1.5D) / (1.0D + 1.5D * ax);
            } sinon {
                id = 3;
                u = -1.0D / ax;
            }
        }
    } sinon {
        si ax < 7.450580596923828e-09D { retour x; }
        u = x;
    }
    soit z = u * u;
    soit w = z * z;
    soit s1 = z * (3.33333333333329318027e-01D + w * (1.42857142725034663711e-01D + w * (9.09088713343650656196e-02D
        + w * (6.66107313738753120669e-02D + w * (4.97687799461593236017e-02D + w * 1.62858201153657823623e-02D)))));
    soit s2 = w * (-1.99999999998764832476e-01D + w * (-1.11111104054623557880e-01D + w * (-7.69187620504482999495e-02D
        + w * (-5.83357013379057348645e-02D + w * -3.65315727442169155270e-02D))));
    si id .< 0 { retour u - u * (s1 + s2); }
    soit hi = 0.0D;
    soit lo = 0.0D;
    si id == 0 { hi = 4.63647609000806093515e-01D; lo = 2.26987774529616870924e-17D; }
    si id == 1 { hi = 7.85398163397448278999e-01D; lo = 3.06161699786838301793e-17D; }
    si id == 2 { hi = 9.82793723247329054082e-01D; lo = 1.39033110312309984516e-17D; }
    si id == 3 { hi = 1.57079632679489655800e+00D; lo = 6.12323399573676603587e-17D; }
    soit r = hi - ((u * (s1 + s2) - lo) - u);
    si x < 0.0D { retour -r; }
    retour r;
}
fonction arctangente2_64(y: flottant_64, x: flottant_64): flottant_64 {
    si x != x || y != y { retour __nan_64(); }
    si x == 0.0D {
        si y > 0.0D { retour 1.5707963267948966D; }
        si y < 0.0D { retour -1.5707963267948966D; }
        retour 0.0D;
    }
    soit z = arctangente_64(abs(y / x));
    si x > 0.0D {
        si y < 0.0D { retour -z; }
        retour z;
    }
    si y < 0.0D { retour (z - 1.2246467991473531772e-16D) - 3.141592653589793D; }
    retour 3.141592653589793D - (z - 1.2246467991473531772e-16D);
}
fonction arcsinus_64(x: flottant_64): flottant_64 {
    si !(abs(x) <= 1.0D) { retour __nan_64(); }
    retour arctangente2_64(x, racine((1.0D - x) * (1.0D + x)));
}
fonction arccosinus_64(x: flottant_64): flottant_64 {
    si !(abs(x) <= 1.0D) { retour __nan_64(); }
    retour 2.0D * arctangente2_64(racine(1.0D - x), racine(1.0D + x));
}
fonction __qlt(a: entier_128, b: entier_128) {
    soit x = haut(haut(a)) ^ 2147483648;
    soit y = haut(haut(b)) ^ 2147483648;
    si x != y { retour x < y; }
    x = bas(haut(a));
    y = bas(haut(b));
    si x != y { retour x < y; }
    x = haut(bas(a));
    y = haut(bas(b));
    si x != y { retour x < y; }
    retour bas(bas(a)) < bas(bas(b));
}
fonction __qltu(a: entier_128, b: entier_128) {
    soit x = haut(haut(a));
    soit y = haut(haut(b));
    si x != y { retour x < y; }
    x = bas(haut(a));
    y = bas(haut(b));
    si x != y { retour x < y; }
    x = haut(bas(a));
    y = haut(bas(b));
    si x != y { retour x < y; }
    retour bas(bas(a)) < bas(bas(b));
}
fonction __qshl(a: entier_128, n): entier_128 {
    soit k = n & 127;
    soit w0 = bas(bas(a));
    soit w1 = haut(bas(a));
    soit w2 = bas(haut(a));
    soit w3 = haut(haut(a));
    tantque k >= 32 {
        w3 = w2;
        w2 = w1;
        w1 = w0;
        w0 = 0;
        k = k - 32;
    }
    si k > 0 {
        w3 = (w3 << k) | (w2 >> (32 - k));
        w2 = (w2 << k) | (w1 >> (32 - k));
        w1 = (w1 << k) | (w0 >> (32 - k));
        w0 = w0 << k;
    }
    retour entier_128_de(long_de(w3, w2), long_de(w1, w0));
}
fonction __qshr_rempli(a: entier_128, n, s): entier_128 {
    soit k = n & 127;
    soit w0 = bas(bas(a));
    soit w1 = haut(bas(a));
    soit w2 = bas(haut(a));
    soit w3 = haut(haut(a));
    tantque k >= 32 {
        w0 = w1;
        w1 = w2;
        w2 = w3;
        w3 = s;
        k = k - 32;
    }
    si k > 0 {
        w0 = (w0 >> k) | (w1 << (32 - k));
        w1 = (w1 >> k) | (w2 << (32 - k));
        w2 = (w2 >> k) | (w3 << (32 - k));
        w3 = (w3 >> k) | (s << (32 - k));
    }
    retour entier_128_de(long_de(w3, w2), long_de(w1, w0));
}
fonction __qshr(a: entier_128, n): entier_128 { retour __qshr_rempli(a, n, 0); }
fonction __qsar(a: entier_128, n): entier_128 {
    si haut(haut(a)) >= 2147483648 { retour __qshr_rempli(a, n, 4294967295); }
    retour __qshr_rempli(a, n, 0);
}
fonction __qmul(a: entier_128, b: entier_128): entier_128 {
    soit al = bas(a);
    soit ah = haut(a);
    soit bl = bas(b);
    soit bh = haut(b);
    soit a0 = long(bas(al));
    soit a1 = long(haut(al));
    soit b0 = long(bas(bl));
    soit b1 = long(haut(bl));
    soit r = entier_128_de(0L, a0 * b0);
    r = r + (entier_128_de(0L, a0 * b1) << 32) + (entier_128_de(0L, a1 * b0) << 32) + entier_128_de(a1 * b1, 0L);
    retour r + entier_128_de(ah * bl + al * bh, 0L);
}
fonction __qdivu(a: entier_128, b: entier_128, reste): entier_128 {
    soit q = 0LL;
    soit r = 0LL;
    pour i dans 0..128 {
        soit dessus = haut(haut(a)) >> 31;
        soit rtop = haut(haut(r)) >> 31;
        a = a + a;
        r = r + r + entier_128(dessus);
        q = q + q;
        si rtop == 1 || !__qltu(r, b) {
            r = r - b;
            q = q + 1;
        }
    }
    si reste == 1 { retour r; }
    retour q;
}
fonction __qdiv(a: entier_128, b: entier_128, reste): entier_128 {
    soit na = haut(haut(a)) >> 31;
    soit nb = haut(haut(b)) >> 31;
    si na == 1 { a = 0 - a; }
    si nb == 1 { b = 0 - b; }
    soit q = __qdivu(a, b, reste);
    si reste == 1 {
        si na == 1 { retour 0 - q; }
        retour q;
    }
    si na != nb { retour 0 - q; }
    retour q;
}
fonction __qabs(a: entier_128): entier_128 {
    si haut(haut(a)) >= 2147483648 { retour 0 - a; }
    retour a;
}
fonction __qmin(a: entier_128, b: entier_128): entier_128 {
    si __qlt(b, a) { retour b; }
    retour a;
}
fonction __qmax(a: entier_128, b: entier_128): entier_128 {
    si __qlt(a, b) { retour b; }
    retour a;
}
fonction __qtod(x: entier_128): flottant_64 {
    soit neg = haut(haut(x)) >> 31;
    si neg == 1 { x = 0 - x; }
    soit w3 = haut(haut(x));
    soit w2 = bas(haut(x));
    soit w1 = haut(bas(x));
    soit w0 = bas(bas(x));
    soit n = 0;
    soit top = w0;
    si w3 != 0 { n = 96; top = w3; } sinon si w2 != 0 { n = 64; top = w2; } sinon si w1 != 0 { n = 32; top = w1; }
    tantque top != 0 {
        n = n + 1;
        top = top >> 1;
    }
    soit d = 0.0D;
    si n < 64 {
        d = flottant_64(bas(x));
    } sinon {
        soit s = n - 63;
        soit q = __qshr(x, s);
        soit t = bas(q);
        si __qshl(q, s) != x { t = t | 1L; }
        d = flottant_64(t) * __p2_64(s);
    }
    si neg == 1 { retour -d; }
    retour d;
}
fonction __dtoq(x: flottant_64): entier_128 {
    si x != x { retour 0LL; }
    soit neg = haut(x) >> 31;
    soit ax = abs(x);
    si ax < 9223372036854775808.0D { retour entier_128(long(x)); }
    si ax >= 170141183460469231731687303715884105728.0D {
        si neg == 1 { retour 0x80000000000000000000000000000000LL; }
        retour 0x7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFLL;
    }
    soit e = ((haut(x) >> 20) & 2047) - 1023;
    soit m = long_de((haut(x) & 1048575) | 1048576, bas(x));
    soit r = __qshl(entier_128_de(0L, m), e - 52);
    si neg == 1 { retour 0 - r; }
    retour r;
}
fonction ecrire_entier_128(c, a: entier_128) {
    si a < 0 {
        __mettre(c, 45);
        a = 0 - a;
    }
    soit t0 = 0;
    soit t1 = 0;
    soit t2 = 0;
    soit t3 = 0;
    soit t4 = 0;
    soit k = 0;
    tantque k == 0 || a != 0 {
        soit q = __qdivu(a, 1000000000, 0);
        soit r = bas(bas(a - q * 1000000000));
        si k == 0 { t0 = r; } sinon si k == 1 { t1 = r; } sinon si k == 2 { t2 = r; } sinon si k == 3 { t3 = r; } sinon { t4 = r; }
        a = q;
        k = k + 1;
    }
    soit premier = 1;
    tantque k > 0 {
        k = k - 1;
        soit v = t0;
        si k == 1 { v = t1; } sinon si k == 2 { v = t2; } sinon si k == 3 { v = t3; } sinon si k == 4 { v = t4; }
        si premier == 1 {
            __mettre_nombre(c, v);
            premier = 0;
        } sinon {
            __ecrire_chiffres(c, v, 9);
        }
    }
}
fonction __afficher_w(x: entier_128) {
    ecrire_entier_128(1, x);
    ecrire_car(1, 10);
}
fonction __ecrire_w(x: entier_128) {
    ecrire_entier_128(1, x);
}
fonction __texte_w(x: entier_128): texte {
    soit t = __verifier(nouveau(48));
    ecrire_entier_128(t, x);
    retour __texte_fin(t);
}
// ---- arrondi binaire et produit de 64 bits (pour le flottant_petuar et ses échanges avec l'IEEE 754)
// ---- flottant_128 (binary128 de l'IEEE 754 : 1 bit de signe, 15 d'exposant, 112 de fraction), calculé sur ses bits
// rangés comme un entier_128 ; arrondi au plus proche, pair en cas d'égalité, comme le matériel des flottants
fonction __xbits(m: entier_128) {
    soit top = bas(bas(m));
    soit n = 0;
    si haut(haut(m)) != 0 { n = 96; top = haut(haut(m)); } sinon si bas(haut(m)) != 0 { n = 64; top = bas(haut(m)); } sinon si haut(bas(m)) != 0 { n = 32; top = haut(bas(m)); }
    si top >= 65536 { n = n + 16; top = top >> 16; }
    si top >= 256 { n = n + 8; top = top >> 8; }
    si top >= 16 { n = n + 4; top = top >> 4; }
    si top >= 4 { n = n + 2; top = top >> 2; }
    si top >= 2 { retour n + 2; }
    retour n + top;
}
// arrondi de m × 2^E (E signé) à p bits de mantisse ; b : le biais, emax : l'exposant de l'infini ; collant : des bits non
// nuls sous m (m a alors au moins p + 2 bits). Rend les bits sans le signe : exposant << (p - 1), plus la fraction.
fonction __xarrondi(m: entier_128, ex, collant, p, b, emax): entier_128 {
    si m == 0LL { retour 0LL; }
    soit n = __xbits(m);
    soit qmin = 2 - b - p;
    soit k = n - p;
    si (ex + k) .< qmin { k = qmin - ex; }
    soit q = 0LL;
    si k .> 0 {
        si k <= 128 {
            soit bas_ = m;
            si k < 128 {
                q = __qshr(m, k);
                bas_ = m - __qshl(q, k);
            }
            soit demi = __qshl(1LL, k - 1);
            si __qltu(demi, bas_) || (bas_ == demi && (collant != 0 || (bas(bas(q)) & 1) == 1)) {
                q = q + 1LL;
            }
        }
        ex = ex + k;
        si q == __qshl(1LL, p) {
            q = __qshr(q, 1);
            ex = ex + 1;
        }
    } sinon {
        q = __qshl(m, 0 - k);
        ex = ex + k;
    }
    soit cache = __qshl(1LL, p - 1);
    si __qltu(q, cache) { retour q; }
    soit be = ex + p - 1 + b;
    si be .>= emax { retour __qshl(entier_128(emax), p - 1); }
    retour __qshl(entier_128(be), p - 1) | (q - cache);
}
// produit de deux entiers de 64 bits sans signe, sur 128 bits
fonction __xmul64(a: long, b: long): entier_128 {
    soit a0 = long(bas(a));
    soit a1 = long(haut(a));
    soit b0 = long(bas(b));
    soit b1 = long(haut(b));
    soit m = entier_128_de(0L, a0 * b1) + entier_128_de(0L, a1 * b0);
    retour entier_128_de(a1 * b1, a0 * b0) + entier_128_de(long_de(bas(haut(m)), haut(bas(m))), long_de(bas(bas(m)), 0));
}
// ---- flottant_petuar : le flottant quaternaire de 128 bits de Vercintorix (4 points du cube, 32 chiffres hex, 64 quits)
// quit 63 : l'état, en logique de Belnap (A 0 inconnu, C 1 négatif, G 2 positif, T/U 3 variable) ; quits 62 à 56 :
// l'exposant en base 4 (7 quits, biais 8192, 16383 : l'infini) ; quits 55 à 0 : la mantisse, 56 chiffres en base 4, le
// premier non nul (sauf sous l'exposant 0). Valeur : mantisse × 4^(exposant − 8247). Arrondi au plus proche, pair au milieu.
fonction __pq_etat(a: entier_128) { retour haut(haut(a)) >> 30; }
fonction __pq_ef(a: entier_128) { retour (haut(haut(a)) >> 16) & 16383; }
fonction __pq_mant(a: entier_128): entier_128 { retour a & 0x0000FFFFFFFFFFFFFFFFFFFFFFFFFFFFLL; }
// l'exposant binaire du quit 0 de la mantisse : 2 × (exposant − 8247), l'exposant 0 compté comme 1 (sous-normaux)
fonction __pq_ex2(a: entier_128) {
    soit e = __pq_ef(a);
    si e == 0 { e = 1; }
    retour 2 * (e - 8247);
}
fonction __pq_variable(): entier_128 { retour 0xC0000000000000000000000000000000LL; }
fonction __pq_signe(s): entier_128 {
    si s == 1 { retour 0x40000000000000000000000000000000LL; }
    retour 0x80000000000000000000000000000000LL;
}
fonction __pq_inf(s): entier_128 { retour __pq_signe(s) | 0x3FFF0000000000000000000000000000LL; }
// inconnu l'emporte sur un nombre, variable sur tout : 1LL quand les deux sont des nombres (zéros et infinis compris)
fonction __pq_special(a: entier_128, b: entier_128): entier_128 {
    soit ea = __pq_etat(a);
    soit eb = __pq_etat(b);
    si ea == 3 || eb == 3 { retour __pq_variable(); }
    si ea == 0 || eb == 0 { retour 0LL; }
    retour 1LL;
}
// m × 2^ex (ex signé) arrondi : exposant << 112, plus la mantisse (sans l'état) ; collant : des bits non nuls sous m
fonction __pq_arrondi(m: entier_128, ex, collant): entier_128 {
    si m == 0LL { retour 0LL; }
    soit n = __xbits(m);
    soit k = n - 112;
    si ((ex + k) & 1) == 1 { k = k + 1; }
    si (ex + k) .< 0 - 16492 { k = 0 - 16492 - ex; }
    soit q = 0LL;
    si k .> 0 {
        si k <= 128 {
            soit bas_ = m;
            si k < 128 {
                q = __qshr(m, k);
                bas_ = m - __qshl(q, k);
            }
            soit demi = __qshl(1LL, k - 1);
            si __qltu(demi, bas_) || (bas_ == demi && (collant != 0 || (bas(bas(q)) & 1) == 1)) {
                q = q + 1LL;
            }
        }
        ex = ex + k;
        si q == 0x00010000000000000000000000000000LL {
            q = 0x00004000000000000000000000000000LL;
            ex = ex + 2;
        }
    } sinon {
        q = __qshl(m, 0 - k);
        ex = ex + k;
    }
    si __qltu(q, 0x00004000000000000000000000000000LL) { retour q; }
    soit h = 0;
    si ex .< 0 { h = 0 - ((0 - ex) >> 1); } sinon { h = ex >> 1; }
    soit e = h + 8247;
    si e .>= 16383 { retour 0x3FFF0000000000000000000000000000LL; }
    retour __qshl(entier_128(e), 112) | q;
}
fonction __pq_de_mag(m: entier_128, ex, s): entier_128 {
    retour __pq_signe(s) | __pq_arrondi(m, ex, 0);
}
// la mantisse ramenée à 112 bits, et son exposant binaire
fonction __pq_norm(m: entier_128) { retour 112 - __xbits(m); }
fonction __pq_add(a: entier_128, b: entier_128): entier_128 {
    soit sp = __pq_special(a, b);
    si sp != 1LL { retour sp; }
    soit sa = __pq_etat(a) & 1;
    soit sb = __pq_etat(b) & 1;
    soit fa = __pq_ef(a);
    soit fb = __pq_ef(b);
    si fa == 16383 || fb == 16383 {
        si fa == 16383 && fb == 16383 && sa != sb { retour __pq_variable(); }
        si fa == 16383 { retour a; }
        retour b;
    }
    soit ma = __pq_mant(a);
    soit mb = __pq_mant(b);
    si ma == 0LL {
        si mb == 0LL && sa != sb { retour __pq_signe(0); }
        retour b;
    }
    si mb == 0LL { retour a; }
    soit xa = __pq_ex2(a);
    soit xb = __pq_ex2(b);
    si xa .< xb {
        soit t = ma; ma = mb; mb = t;
        soit u = xa; xa = xb; xb = u;
        soit v = sa; sa = sb; sb = v;
    }
    ma = __qshl(ma, 4);
    mb = __qshl(mb, 4);
    soit d = xa - xb;
    si d > 120 {
        mb = 1LL;
    } sinon si d != 0 {
        soit q = __qshr(mb, d);
        si __qshl(q, d) != mb { q = q | 1LL; }
        mb = q;
    }
    soit s = sa;
    soit m = ma + mb;
    si sa != sb {
        si __qltu(ma, mb) {
            m = mb - ma;
            s = sb;
        } sinon {
            m = ma - mb;
        }
        si m == 0LL { retour __pq_signe(0); }
    }
    retour __pq_signe(s) | __pq_arrondi(m, xa - 4, 0);
}
fonction __pq_neg(a: entier_128): entier_128 {
    soit e = __pq_etat(a);
    si e == 1 || e == 2 { retour a ^ 0xC0000000000000000000000000000000LL; }
    retour a;
}
fonction __pq_sub(a: entier_128, b: entier_128): entier_128 { retour __pq_add(a, __pq_neg(b)); }
fonction __pq_mul(a: entier_128, b: entier_128): entier_128 {
    soit sp = __pq_special(a, b);
    si sp != 1LL { retour sp; }
    soit s = 1;
    si __pq_etat(a) == __pq_etat(b) { s = 0; }
    soit ma = __pq_mant(a);
    soit mb = __pq_mant(b);
    soit fa = __pq_ef(a);
    soit fb = __pq_ef(b);
    si fa == 16383 || fb == 16383 {
        si (fa != 16383 && ma == 0LL) || (fb != 16383 && mb == 0LL) { retour __pq_variable(); }
        retour __pq_inf(s);
    }
    si ma == 0LL || mb == 0LL { retour __pq_signe(s); }
    soit ka = __pq_norm(ma);
    soit kb = __pq_norm(mb);
    ma = __qshl(ma, ka);
    mb = __qshl(mb, kb);
    soit al = bas(ma);
    soit ah = haut(ma);
    soit bl = bas(mb);
    soit bh = haut(mb);
    soit lo = __xmul64(al, bl);
    soit mi = __xmul64(ah, bl) + __xmul64(al, bh);
    soit hi = __xmul64(ah, bh) + entier_128_de(0L, haut(mi));
    soit lo2 = lo + entier_128_de(bas(mi), 0L);
    si __qltu(lo2, lo) { hi = hi + 1LL; }
    soit m = __qshl(hi, 29) | __qshr(lo2, 99);
    soit collant = 0;
    si __qshl(lo2, 29) != 0LL { collant = 1; }
    retour __pq_signe(s) | __pq_arrondi(m, __pq_ex2(a) - ka + __pq_ex2(b) - kb + 99, collant);
}
fonction __pq_div(a: entier_128, b: entier_128): entier_128 {
    soit sp = __pq_special(a, b);
    si sp != 1LL { retour sp; }
    soit s = 1;
    si __pq_etat(a) == __pq_etat(b) { s = 0; }
    soit ma = __pq_mant(a);
    soit mb = __pq_mant(b);
    soit fa = __pq_ef(a);
    soit fb = __pq_ef(b);
    si fa == 16383 {
        si fb == 16383 { retour __pq_variable(); }
        retour __pq_inf(s);
    }
    si fb == 16383 { retour __pq_signe(s); }
    si mb == 0LL {
        si ma == 0LL { retour __pq_variable(); }
        retour __pq_inf(s);
    }
    si ma == 0LL { retour __pq_signe(s); }
    soit ka = __pq_norm(ma);
    soit kb = __pq_norm(mb);
    ma = __qshl(ma, ka);
    mb = __qshl(mb, kb);
    soit r = ma;
    soit q = 0LL;
    pour i dans 0..117 {
        q = q + q;
        si !__qltu(r, mb) {
            r = r - mb;
            q = q + 1LL;
        }
        r = r + r;
    }
    soit collant = 0;
    si r != 0LL { collant = 1; }
    retour __pq_signe(s) | __pq_arrondi(q, (__pq_ex2(a) - ka) - (__pq_ex2(b) - kb) - 116, collant);
}
fonction __pq_racine(a: entier_128): entier_128 {
    soit st = __pq_etat(a);
    si st == 0 || st == 3 { retour a; }
    soit m = __pq_mant(a);
    soit f0 = __pq_ef(a);
    si f0 != 16383 && m == 0LL { retour a; }
    si st == 1 { retour __pq_variable(); }
    si f0 == 16383 { retour a; }
    soit k = __pq_norm(m);
    m = __qshl(m, k);
    soit x = __pq_ex2(a) - k;
    si (x & 1) == 1 {
        m = m + m;
        x = x - 1;
    }
    soit nb = __xbits(m);
    soit paires = (nb + 121) / 2;
    soit f = __qshl(m, 248 - 2 * paires);
    soit res = 0LL;
    soit reste = 0LL;
    pour j dans 0..paires {
        soit deux = haut(haut(f)) >> 30;
        f = f + f;
        f = f + f;
        reste = reste + reste;
        reste = reste + reste + entier_128(deux);
        soit t = res + res;
        t = t + t + 1LL;
        res = res + res;
        si !__qltu(reste, t) {
            reste = reste - t;
            res = res + 1LL;
        }
    }
    soit collant = 0;
    si reste != 0LL { collant = 1; }
    soit y = x - 120;
    si y .< 0 { y = 0 - ((0 - y) >> 1); } sinon { y = y >> 1; }
    retour __pq_signe(0) | __pq_arrondi(res, y, collant);
}
// 0 : égaux, 1 : a < b, 2 : a > b, 3 : sans ordre (inconnu ou variable)
fonction __pq_cmp(a: entier_128, b: entier_128) {
    si __pq_special(a, b) != 1LL { retour 3; }
    soit ma = a & 0x3FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFLL;
    soit mb = b & 0x3FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFLL;
    soit na = __pq_etat(a) & 1;
    soit nb = __pq_etat(b) & 1;
    si ma == 0LL && mb == 0LL { retour 0; }
    si na != nb {
        si na == 1 { retour 1; }
        retour 2;
    }
    si ma == mb { retour 0; }
    si __qltu(ma, mb) != na { retour 1; }
    retour 2;
}
fonction __pq_lt(a: entier_128, b: entier_128) { retour __pq_cmp(a, b) == 1; }
fonction __pq_le(a: entier_128, b: entier_128) { retour __pq_cmp(a, b) < 2; }
fonction __pq_gt(a: entier_128, b: entier_128) { retour __pq_cmp(a, b) == 2; }
fonction __pq_ge(a: entier_128, b: entier_128) { retour (__pq_cmp(a, b) & 1) == 0; }
fonction __pq_eq(a: entier_128, b: entier_128) { retour __pq_cmp(a, b) == 0; }
fonction __pq_ne(a: entier_128, b: entier_128) { retour __pq_cmp(a, b) != 0; }
// conversions
fonction __pq_de_e(x): entier_128 {
    si x == 0 { retour __pq_signe(0); }
    retour __pq_de_mag(entier_128_de(0L, long(x)), 0, 0);
}
fonction __pq_de_w(w: entier_128): entier_128 {
    si w == 0LL { retour __pq_signe(0); }
    si (haut(haut(w)) >> 31) == 1 { retour __pq_de_mag(0LL - w, 0, 1); }
    retour __pq_de_mag(w, 0, 0);
}
fonction __pq_de_l(x: long): entier_128 { retour __pq_de_w(entier_128(x)); }
fonction __pq_de_d(dx: flottant_64): entier_128 {
    soit lo = bas(dx);
    soit hi = haut(dx);
    soit e = (hi >> 20) & 2047;
    soit s = hi >> 31;
    soit m = entier_128_de(0L, long_de(hi & 1048575, lo));
    si e == 2047 {
        si m != 0LL { retour __pq_variable(); }
        retour __pq_inf(s);
    }
    si e == 0 && m == 0LL { retour __pq_signe(s); }
    soit x = 0 - 1074;
    si e != 0 {
        m = m | 0x10000000000000LL;
        x = e - 1075;
    }
    retour __pq_de_mag(m, x, s);
}
// vers binary64 (les 64 bits dans la moitié basse) : inconnu et variable donnent le NaN
fonction __pq_vers_d(a: entier_128): flottant_64 {
    soit st = __pq_etat(a);
    si st == 0 || st == 3 { retour comme_flottant_64(0x7FF8000000000000L); }
    soit r = 0x7FF0000000000000LL;
    si __pq_ef(a) != 16383 { r = __xarrondi(__pq_mant(a), __pq_ex2(a), 0, 53, 1023, 2047); }
    si st == 1 { r = r | 0x8000000000000000LL; }
    retour comme_flottant_64(bas(r));
}
// vers binary32, en un seul arrondi
fonction __pq_vers_f(a: entier_128): flottant {
    soit st = __pq_etat(a);
    si st == 0 || st == 3 { retour comme_flottant(2143289344); }
    soit r = 2139095040;
    si __pq_ef(a) != 16383 { r = bas(bas(__xarrondi(__pq_mant(a), __pq_ex2(a), 0, 24, 127, 255))); }
    si st == 1 { r = r | 2147483648; }
    retour comme_flottant(r);
}
// vers entier_128 en tronquant vers zéro, saturé aux bornes ; inconnu et variable donnent 0
fonction __pq_vers_w(a: entier_128): entier_128 {
    soit st = __pq_etat(a);
    si st == 0 || st == 3 { retour 0LL; }
    soit m = __pq_mant(a);
    soit x = __pq_ex2(a);
    si __pq_ef(a) == 16383 || (m != 0LL && x .>= 0 && x + __xbits(m) > 127) {
        si st == 1 { retour 0x80000000000000000000000000000000LL; }
        retour 0x7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFLL;
    }
    si m == 0LL { retour 0LL; }
    si x .>= 0 {
        m = __qshl(m, x);
    } sinon si (0 - x) >= 128 {
        m = 0LL;
    } sinon {
        m = __qshr(m, 0 - x);
    }
    si st == 1 { retour 0LL - m; }
    retour m;
}
// échange avec le binary128 de l'IEEE 754 : vers lui c'est exact, depuis lui on arrondit (111 à 112 bits ici, 113 là-bas)
fonction __pq_vers_ieee(a: entier_128): entier_128 {
    soit st = __pq_etat(a);
    si st == 0 || st == 3 { retour 0x7FFF8000000000000000000000000000LL; }
    soit r = 0x7FFF0000000000000000000000000000LL;
    si __pq_ef(a) != 16383 { r = __xarrondi(__pq_mant(a), __pq_ex2(a), 0, 113, 16383, 32767); }
    si st == 1 { retour r | 0x80000000000000000000000000000000LL; }
    retour r;
}
fonction __pq_de_ieee(b: entier_128): entier_128 {
    soit s = haut(haut(b)) >> 31;
    soit e = (haut(haut(b)) >> 16) & 32767;
    soit f = b & 0x0000FFFFFFFFFFFFFFFFFFFFFFFFFFFFLL;
    si e == 32767 {
        si f != 0LL { retour __pq_variable(); }
        retour __pq_inf(s);
    }
    si e == 0 && f == 0LL { retour __pq_signe(s); }
    si e == 0 { retour __pq_de_mag(f, 0 - 16494, s); }
    retour __pq_de_mag(f | 0x00010000000000000000000000000000LL, e - 16495, s);
}
fonction __pq_abs(a: entier_128): entier_128 {
    si __pq_etat(a) == 1 { retour a ^ 0xC0000000000000000000000000000000LL; }
    retour a;
}
fonction __pq_min(a: entier_128, b: entier_128): entier_128 {
    soit sp = __pq_special(a, b);
    si sp != 1LL { retour sp; }
    si __pq_cmp(b, a) == 1 { retour b; }
    retour a;
}
fonction __pq_max(a: entier_128, b: entier_128): entier_128 {
    soit sp = __pq_special(a, b);
    si sp != 1LL { retour sp; }
    si __pq_cmp(a, b) == 1 { retour b; }
    retour a;
}
// l'état d'un flottant_petuar, en logique de Belnap : inconnu, faux (négatif), vrai (positif), variable (contradiction)
fonction etat(x: flottant_petuar): logique { retour comme_logique(__pq_etat(bits(x))); }
fonction pi_petuar(): flottant_petuar { retour 3.14159265358979323846264338327950288419716939937510582Q; }
fonction inconnu_petuar(): flottant_petuar { retour comme_flottant_petuar(0LL); }
fonction variable_petuar(): flottant_petuar { retour comme_flottant_petuar(0xC0000000000000000000000000000000LL); }
// écriture décimale : les chiffres les plus courts qui redonnent exactement le nombre (d = 4294967295), ou d décimales
fonction ecrire_flottant_petuar(c, x: flottant_petuar, d) {
    soit a = bits(x);
    soit st = __pq_etat(a);
    si st == 0 {
        __mettre(c, 105); __mettre(c, 110); __mettre(c, 99); __mettre(c, 111); __mettre(c, 110); __mettre(c, 110); __mettre(c, 117);
        retour;
    }
    si st == 3 {
        __mettre(c, 118); __mettre(c, 97); __mettre(c, 114); __mettre(c, 105); __mettre(c, 97); __mettre(c, 98); __mettre(c, 108);
        __mettre(c, 101);
        retour;
    }
    si st == 1 { __mettre(c, 45); }
    soit ef = __pq_ef(a);
    si ef == 16383 {
        __mettre(c, 105); __mettre(c, 110); __mettre(c, 102);
        retour;
    }
    soit m = __pq_mant(a);
    soit f = tableau(0);
    soit w0 = bas(bas(m));
    soit w1 = haut(bas(m));
    soit w2 = bas(haut(m));
    soit w3 = haut(haut(m));
    ajouter(f, w0 & 65535); ajouter(f, w0 >> 16);
    ajouter(f, w1 & 65535); ajouter(f, w1 >> 16);
    ajouter(f, w2 & 65535); ajouter(f, w2 >> 16);
    ajouter(f, w3 & 65535);
    tantque longueur(f) > 0 && f[longueur(f) - 1] == 0 { retirer(f); }
    soit e = __pq_ex2(a);
    si d != 4294967295 {
        si d > 60 { d = 60; }
        __ecrire_fixe(c, f, e, d);
        retour;
    }
    si longueur(f) == 0 {
        __mettre(c, 48); __mettre(c, 46); __mettre(c, 48);
        retour;
    }
    // au bas d'une puissance de 4, le voisin du dessous est quatre fois plus près
    soit bord = 0;
    si ef > 1 && m == 0x00004000000000000000000000000000LL { bord = 2; }
    __ecrire_dragon(c, __dragon(f, e, bord));
}
fonction __afficher_x(x: flottant_petuar) {
    ecrire_flottant_petuar(1, x, 4294967295);
    ecrire_car(1, 10);
}
fonction __ecrire_x(x: flottant_petuar) {
    ecrire_flottant_petuar(1, x, 4294967295);
}
fonction __texte_x(x: flottant_petuar): texte {
    soit t = __verifier(nouveau(48));
    ecrire_flottant_petuar(t, x, 4294967295);
    retour __texte_fin(t);
}
// les 64 quits d'un entier_petuar en bases (A C G T, ou U pour l'ARN), le quit 63 d'abord ; et ses quatre points du cube
fonction ecrire_adn(c, w: entier_128, arn) {
    pour i dans 0..64 {
        soit k = 63 - i;
        soit mot = bas(bas(w));
        si k >= 48 { mot = haut(haut(w)); } sinon si k >= 32 { mot = bas(haut(w)); } sinon si k >= 16 { mot = haut(bas(w)); }
        soit q = (mot >> ((k & 15) * 2)) & 3;
        si q == 0 { __mettre(c, 65); } sinon si q == 1 { __mettre(c, 67); } sinon si q == 2 { __mettre(c, 71); }
        sinon si arn == 1 { __mettre(c, 85); } sinon { __mettre(c, 84); }
    }
}
fonction __hexa8(c, n) {
    pour i dans 0..8 {
        soit k = (n >> (28 - 4 * i)) & 15;
        si k < 10 { __mettre(c, 48 + k); } sinon { __mettre(c, 55 + k); }
    }
}
fonction ecrire_cube(c, w: entier_128) {
    ecrire_hexa(c, haut(haut(w)));
    __mettre(c, 95); __hexa8(c, bas(haut(w)));
    __mettre(c, 95); __hexa8(c, haut(bas(w)));
    __mettre(c, 95); __hexa8(c, bas(bas(w)));
}
fonction texte_adn(w: entier_128): texte {
    soit t = __verifier(nouveau(68));
    ecrire_adn(t, w, 0);
    retour __texte_fin(t);
}
fonction texte_arn(w: entier_128): texte {
    soit t = __verifier(nouveau(68));
    ecrire_adn(t, w, 1);
    retour __texte_fin(t);
}
fonction texte_cube(w: entier_128): texte {
    soit t = __verifier(nouveau(40));
    ecrire_cube(t, w);
    retour __texte_fin(t);
}
fonction graine(n) {
    soit x = n ^ 2463534242;
    si x == 0 { x = 1; }
    @3[14680057] = x;
    pour i dans 0..8 { hasard_mot(); }
}
fonction hasard_mot() {
    soit x = @3[14680057];
    si x == 0 { x = 2463534242; }
    x = x ^ (x << 13);
    x = x ^ (x >> 17);
    x = x ^ (x << 5);
    @3[14680057] = x;
    retour x;
}
fonction hasard(n) {
    si n == 0 { retour hasard_mot(); }
    retour hasard_mot() % n;
}
fonction hasard_entre(a, b) {
    retour a + hasard(b - a + 1);
}
fonction hasard_flottant(): flottant {
    retour flottant(hasard_mot() >> 8) * 0.000000059604645;
}
fonction graine_bruit() {
    graine(bruit());
}
fonction bruit_logique(): logique {
    retour comme_logique(bruit());
}
fonction tableau(n) {
    soit h = __verifier(nouveau(3));
    soit p = h & 16777215;
    soit cap = n;
    si cap < 4 {
        cap = 4;
    }
    @3[p] = n;
    @3[p + 1] = cap;
    @3[p + 2] = __verifier(nouveau(cap)) & 16777215;
    retour h;
}
fonction __remplir(t, i, v) {
    @3[@3[(t & 16777215) + 2] + i] = v;
    retour t;
}
fonction __ajouter(t, v) {
    soit p = t & 16777215;
    soit n = @3[p];
    soit cap = @3[p + 1];
    soit d = @3[p + 2];
    si n == cap {
        soit d2 = __verifier(nouveau(2 * cap)) & 16777215;
        pour i dans 0..n {
            @3[d2 + i] = @3[d + i];
        }
        liberer(50331648 + d);
        d = d2;
        @3[p + 1] = 2 * cap;
        @3[p + 2] = d;
    }
    @3[d + n] = v;
    @3[p] = n + 1;
}
fonction ajouter(t, v) {
    __ajouter(t, v);
}
fonction retirer(t) {
    soit p = t & 16777215;
    soit n = @3[p];
    si n == 0 {
        retour 0;
    }
    @3[p] = n - 1;
    retour @3[@3[p + 2] + n - 1];
}
fonction inserer(t, i, v) {
    __ajouter(t, 0);
    soit p = t & 16777215;
    soit d = @3[p + 2];
    soit k = @3[p] - 1;
    tantque k > i {
        @3[d + k] = @3[d + k - 1];
        k = k - 1;
    }
    @3[d + i] = v;
}
fonction enlever(t, i) {
    soit p = t & 16777215;
    soit d = @3[p + 2];
    soit n = @3[p];
    soit v = @3[d + i];
    pour k dans i..n - 1 {
        @3[d + k] = @3[d + k + 1];
    }
    @3[p] = n - 1;
    retour v;
}
fonction vider(t) {
    @3[t & 16777215] = 0;
}
fonction indice(t, v) {
    soit p = t & 16777215;
    soit d = @3[p + 2];
    pour k dans 0..@3[p] {
        si @3[d + k] == v {
            retour k;
        }
    }
    retour 4294967295;
}
fonction contient(t, v) {
    retour indice(t, v) != 4294967295;
}
fonction somme(t) {
    soit p = t & 16777215;
    soit d = @3[p + 2];
    soit s = 0;
    pour k dans 0..@3[p] {
        s = s + @3[d + k];
    }
    retour s;
}
fonction accorder(etage, f) {
    // l'étage regarde désormais le cube de fréquence f (les autres cubes gardent leur contenu) ; rend l'ancienne
    retour __service(8, (f << 2) | (etage & 3));
}
fonction frequence(etage) {
    retour __service(9, etage & 3);
}
fonction presenter() {
    // Gobatix : montre l'image préparée par ecran(l, h) ; rend 0 tant que tout va bien (la machine sans fenêtre rend toujours 0),
    // 1 quand la fenêtre a été fermée, 4294967295 si le programme n'a pas préparé d'image
    retour __service(12, 0);
}
fonction ranger_cube(etage, f) {
    // écrit sur disque le cube de fréquence f de l'étage (fichier cube-ÉTAGE-FRÉQUENCE.cub, à côté du programme) ; un cube
    // qui n'est pas regardé quitte la mémoire, accorder(étage, f) le retrouve dans son fichier ; rend le nombre de pages
    retour __service(11, (f << 2) | (etage & 3));
}
fonction parler(t) {
    soit c = ouvrir_ecriture("voix:");
    si c != 4294967295 {
        ecrire_texte(c, t);
        fermer(c);
    }
}
fonction ecran(l, h) {
    @3[14680058] = l;
    @3[14680059] = h;
    pour i dans 0..(l * h) {
        @1[i] = 0;
    }
}
fonction rgb(r, g, b) {
    retour ((r & 255) << 24) | ((g & 255) << 16) | ((b & 255) << 8) | 255;
}
fonction pixel(x, y, c) {
    soit l = @3[14680058];
    si x < l && y < @3[14680059] {
        @1[y * l + x] = c;
    }
}
fonction rectangle(x, y, l, h, c) {
    pour j dans 0..h {
        pour i dans 0..l {
            pixel(x + i, y + j, c);
        }
    }
}
fonction disque(cx, cy, r, c) {
    pour j dans 0..(2 * r + 1) {
        pour i dans 0..(2 * r + 1) {
            soit dx = i - r;
            soit dy = j - r;
            si dx * dx + dy * dy <= r * r {
                pixel(cx + dx, cy + dy, c);
            }
        }
    }
}
fonction trait(x0, y0, x1, y1, c) {
    soit dx = abs(x1 - x0);
    soit dy = abs(y1 - y0);
    soit sx = 1;
    si x1 .< x0 {
        sx = 0 - 1;
    }
    soit sy = 1;
    si y1 .< y0 {
        sy = 0 - 1;
    }
    soit err = dx - dy;
    soit fini = 0;
    tantque fini == 0 {
        pixel(x0, y0, c);
        si x0 == x1 && y0 == y1 {
            fini = 1;
        } sinon {
            soit e2 = 2 * err;
            si e2 .> 0 - dy {
                err = err - dy;
                x0 = x0 + sx;
            }
            si e2 .< dx {
                err = err + dx;
                y0 = y0 + sy;
            }
        }
    }
}
// triangle plein dont la couleur se fond d'un sommet à l'autre (ombrage de Gouraud) : chaque sommet a sa couleur #RRGGBBAA
fonction triangle(x0, y0, c0, x1, y1, c1, x2, y2, c2) {
    soit l = @3[14680058];
    soit h = @3[14680059];
    soit aire = (x1 - x0) * (y2 - y0) - (y1 - y0) * (x2 - x0);
    si aire == 0 { retour; }
    si aire .< 0 {
        soit tx = x1; x1 = x2; x2 = tx;
        soit ty = y1; y1 = y2; y2 = ty;
        soit tc = c1; c1 = c2; c2 = tc;
        aire = 0 - aire;
    }
    // la boîte du triangle, coupée aux bords de l'image
    soit xa = x0; si x1 .< xa { xa = x1; } si x2 .< xa { xa = x2; } si xa .< 0 { xa = 0; }
    soit ya = y0; si y1 .< ya { ya = y1; } si y2 .< ya { ya = y2; } si ya .< 0 { ya = 0; }
    soit xb = x0; si x1 .> xb { xb = x1; } si x2 .> xb { xb = x2; } si xb .>= l { xb = l - 1; }
    soit yb = y0; si y1 .> yb { yb = y1; } si y2 .> yb { yb = y2; } si yb .>= h { yb = h - 1; }
    si xa .> xb || ya .> yb { retour; }
    // les trois poids (fonctions d'arête), qui avancent d'un pas constant d'un point au suivant
    soit r0 = c0 >> 24; soit g0 = (c0 >> 16) & 255; soit b0 = (c0 >> 8) & 255;
    soit r1 = c1 >> 24; soit g1 = (c1 >> 16) & 255; soit b1 = (c1 >> 8) & 255;
    soit r2 = c2 >> 24; soit g2 = (c2 >> 16) & 255; soit b2 = (c2 >> 8) & 255;
    soit a0 = y1 - y2; soit b0p = x2 - x1;
    soit a1 = y2 - y0; soit b1p = x0 - x2;
    soit a2 = y0 - y1; soit b2p = x1 - x0;
    soit w0l = (x2 - x1) * (ya - y1) - (y2 - y1) * (xa - x1);
    soit w1l = (x0 - x2) * (ya - y2) - (y0 - y2) * (xa - x2);
    soit w2l = (x1 - x0) * (ya - y0) - (y1 - y0) * (xa - x0);
    soit y = ya;
    tantque y .<= yb {
        soit w0 = w0l;
        soit w1 = w1l;
        soit w2 = w2l;
        soit p = y * l + xa;
        soit x = xa;
        tantque x .<= xb {
            si (w0 | w1 | w2) < 2147483648 {
                soit r = (w0 * r0 + w1 * r1 + w2 * r2) / aire;
                soit g = (w0 * g0 + w1 * g1 + w2 * g2) / aire;
                soit b = (w0 * b0 + w1 * b1 + w2 * b2) / aire;
                @1[p] = (r << 24) | (g << 16) | (b << 8) | 255;
            }
            w0 = w0 + a0;
            w1 = w1 + a1;
            w2 = w2 + a2;
            p = p + 1;
            x = x + 1;
        }
        w0l = w0l + b0p;
        w1l = w1l + b1p;
        w2l = w2l + b2p;
        y = y + 1;
    }
}
// ---- l'interactif (une fenêtre : Gobatix ou l'atelier ; sans fenêtre, souris, touche et molette rendent 0)
fonction cadence(ms) {
    // presenter() attend au moins ms millisecondes depuis l'image précédente (16 par défaut : 60 images par seconde ; 0 : sans
    // attendre) ; c'est aussi la durée de chaque image d'une animation GIF ; rend l'ancienne cadence
    retour __service(19, ms);
}
fonction horloge() {
    // les millisecondes écoulées depuis le lancement du programme
    retour __service(18, 0);
}
fonction souris() {
    // la souris dans l'image du programme, en un mot : x (bits 0 à 11), y (12 à 23), boutons (24 à 26 : gauche 1, droit 2,
    // milieu 4), dans l'image (27) ; voir souris_x, souris_y, souris_boutons, souris_dedans
    retour __service(16, 0);
}
fonction souris_x(m) {
    retour m & 4095;
}
fonction souris_y(m) {
    retour (m >> 12) & 4095;
}
fonction souris_boutons(m) {
    retour (m >> 24) & 7;
}
fonction souris_dedans(m) {
    retour (m >> 27) & 1;
}
fonction molette() {
    // les crans de molette depuis le dernier appel (vers l'avant : positif)
    retour __service(20, 0);
}
fonction touche() {
    // la prochaine touche appuyée, sans attendre : un caractère, ou 65536 + le code d'une touche sans caractère (les
    // flèches : touche_gauche()…) ; 0 s'il n'y en a pas
    retour __service(17, 0);
}
fonction appuyee(t) {
    // 1 si la touche t (un caractère, ou touche_gauche()…) est enfoncée en ce moment, sinon 0 : pour un jeu
    retour __service(21, t);
}
fonction touche_gauche() {
    retour 65573;
}
fonction touche_haut() {
    retour 65574;
}
fonction touche_droite() {
    retour 65575;
}
fonction touche_bas() {
    retour 65576;
}
fonction touche_entree() {
    retour 13;
}
fonction touche_echap() {
    retour 27;
}
fonction touche_espace() {
    retour 32;
}
// ---- l'anti-cube des couleurs : anti(c) = 255 - c sur chaque voie (symétrie par le gris du centre du cube), l'alpha gardé ;
// anti(anti(c)) = c : un curseur ou une sélection se pose et s'enlève sans garder le fond
fonction anti_couleur(c) {
    retour c ^ 4294967040;
}
fonction pixel_anti(x, y) {
    soit l = @3[14680058];
    si x < l && y < @3[14680059] {
        @1[y * l + x] = @1[y * l + x] ^ 4294967040;
    }
}
fonction rectangle_anti(x, y, l, h) {
    pour j dans 0..h {
        pour i dans 0..l {
            pixel_anti(x + i, y + j);
        }
    }
}
fonction __somme_f(t): flottant {
    soit p = t & 16777215;
    soit d = @3[p + 2];
    soit s = 0.0;
    pour k dans 0..@3[p] {
        s = s + comme_flottant(@3[d + k]);
    }
    retour s;
}
fonction __cle_f(b) {
    si b >= 2147483648 {
        retour ~b;
    }
    retour b | 2147483648;
}
fonction __trier_f(t) {
    soit p = t & 16777215;
    soit d = @3[p + 2];
    soit n = @3[p];
    soit ecart = n / 2;
    tantque ecart > 0 {
        pour i dans ecart..n {
            soit x = @3[d + i];
            soit j = i;
            tantque j >= ecart && __cle_f(@3[d + j - ecart]) > __cle_f(x) {
                @3[d + j] = @3[d + j - ecart];
                j = j - ecart;
            }
            @3[d + j] = x;
        }
        ecart = ecart / 2;
    }
}
fonction inverser(t) {
    soit p = t & 16777215;
    soit d = @3[p + 2];
    soit a = 0;
    soit b = @3[p] - 1;
    tantque a .< b {
        soit x = @3[d + a];
        @3[d + a] = @3[d + b];
        @3[d + b] = x;
        a = a + 1;
        b = b - 1;
    }
}
fonction copie(t) {
    soit n = @3[t & 16777215];
    soit r = tableau(n);
    soit ds = @3[(t & 16777215) + 2];
    soit dr = @3[(r & 16777215) + 2];
    pour k dans 0..n {
        @3[dr + k] = @3[ds + k];
    }
    retour r;
}
fonction trier(t) {
    soit p = t & 16777215;
    soit d = @3[p + 2];
    soit n = @3[p];
    soit ecart = n / 2;
    tantque ecart > 0 {
        pour i dans ecart..n {
            soit x = @3[d + i];
            soit j = i;
            tantque j >= ecart && (@3[d + j - ecart] ^ 2147483648) > (x ^ 2147483648) {
                @3[d + j] = @3[d + j - ecart];
                j = j - ecart;
            }
            @3[d + j] = x;
        }
        ecart = ecart / 2;
    }
}
fonction __hache(t) {
    soit h = 2166136261;
    pour i dans 0..longueur(t) {
        h = (h ^ car(t, i)) * 16777619;
    }
    retour h;
}
fonction __dico(ouvert) {
    soit h = __verifier(nouveau(6));
    soit p = h & 16777215;
    @3[p + 1] = 16;
    @3[p + 2] = __verifier(nouveau(16)) & 16777215;
    @3[p + 3] = __verifier(nouveau(16)) & 16777215;
    @3[p + 4] = __verifier(nouveau(16)) & 16777215;
    @3[p + 5] = ouvert;
    retour h;
}
fonction dico() {
    retour __dico(0);
}
fonction dico_ouvert() {
    retour __dico(1);
}
fonction __place(d, cle) {
    soit p = d & 16777215;
    soit cap = @3[p + 1];
    soit ks = @3[p + 2];
    soit i = __hache(cle) & (cap - 1);
    tantque @3[ks + i] != 0 && texte_egal(@3[ks + i], cle) == 0 {
        i = (i + 1) & (cap - 1);
    }
    retour i;
}
fonction __remettre(d, cle, v, q) {
    soit p = d & 16777215;
    soit i = __place(d, cle);
    si @3[@3[p + 2] + i] == 0 {
        @3[@3[p + 2] + i] = cle;
        @3[p] = @3[p] + 1;
    }
    @3[@3[p + 3] + i] = v;
    @3[@3[p + 4] + i] = q;
}
fonction __case(d, cle) {
    soit p = d & 16777215;
    si (@3[p] + 1) * 4 > @3[p + 1] * 3 {
        soit cap = @3[p + 1];
        soit ks = @3[p + 2];
        soit vs = @3[p + 3];
        soit qs = @3[p + 4];
        @3[p] = 0;
        @3[p + 1] = 2 * cap;
        @3[p + 2] = __verifier(nouveau(2 * cap)) & 16777215;
        @3[p + 3] = __verifier(nouveau(2 * cap)) & 16777215;
        @3[p + 4] = __verifier(nouveau(2 * cap)) & 16777215;
        pour k dans 0..cap {
            si @3[ks + k] != 0 {
                __remettre(d, @3[ks + k], @3[vs + k], @3[qs + k]);
            }
        }
        liberer(50331648 + ks);
        liberer(50331648 + vs);
        liberer(50331648 + qs);
    }
    soit i = __place(d, cle);
    si @3[@3[p + 2] + i] == 0 {
        @3[@3[p + 2] + i] = cle;
        @3[p] = @3[p] + 1;
    }
    retour i;
}
fonction ranger(d, cle, v) {
    soit p = d & 16777215;
    soit i = __case(d, cle);
    @3[@3[p + 3] + i] = v;
    @3[@3[p + 4] + i] = 2;
}
fonction affirmer(d, cle, v) {
    soit p = d & 16777215;
    soit neuf = existe(d, cle) == 0;
    soit i = __case(d, cle);
    soit q = @3[@3[p + 4] + i];
    si neuf {
        q = 2;
    } sinon si q == 1 || (q == 2 && @3[@3[p + 3] + i] != v) {
        q = 3;
    }
    @3[@3[p + 3] + i] = v;
    @3[@3[p + 4] + i] = q;
}
fonction nier(d, cle) {
    soit p = d & 16777215;
    soit neuf = existe(d, cle) == 0;
    soit i = __case(d, cle);
    soit q = @3[@3[p + 4] + i];
    si neuf {
        q = 1;
    } sinon si q == 2 {
        q = 3;
    }
    @3[@3[p + 4] + i] = q;
}
fonction trouver(d, cle) {
    soit p = d & 16777215;
    soit i = __place(d, cle);
    retour @3[@3[p + 3] + i];
}
fonction existe(d, cle) {
    soit p = d & 16777215;
    retour @3[@3[p + 2] + __place(d, cle)] != 0;
}
fonction savoir(d, cle): logique {
    si d == 0 {
        retour inconnu;
    }
    soit p = d & 16777215;
    soit i = __place(d, cle);
    si @3[@3[p + 2] + i] == 0 {
        si @3[p + 5] == 1 {
            retour inconnu;
        }
        retour faux;
    }
    retour comme_logique(@3[@3[p + 4] + i]);
}
fonction nommer(l: logique, noms): texte {
    retour @3[@3[(noms & 16777215) + 2] + entier(l)];
}
fonction cles(d) {
    soit p = d & 16777215;
    soit r = tableau(0);
    soit ks = @3[p + 2];
    pour k dans 0..@3[p + 1] {
        si @3[ks + k] != 0 {
            __ajouter(r, @3[ks + k]);
        }
    }
    retour r;
}
fonction majuscules(t): texte {
    soit n = longueur(t);
    soit r = texte_neuf(n);
    pour i dans 0..n {
        soit c = car(t, i);
        si (c >= 97 && c <= 122) || (c >= 224 && c <= 254 && c != 247) {
            c = c - 32;
        }
        changer_car(r, i, c);
    }
    retour r;
}
fonction minuscules(t): texte {
    soit n = longueur(t);
    soit r = texte_neuf(n);
    pour i dans 0..n {
        soit c = car(t, i);
        si (c >= 65 && c <= 90) || (c >= 192 && c <= 222 && c != 215) {
            c = c + 32;
        }
        changer_car(r, i, c);
    }
    retour r;
}
fonction commence_par(t, debut) {
    soit n = longueur(debut);
    si n > longueur(t) {
        retour 0;
    }
    pour i dans 0..n {
        si car(t, i) != car(debut, i) {
            retour 0;
        }
    }
    retour 1;
}
fonction finit_par(t, fin) {
    soit n = longueur(fin);
    soit m = longueur(t);
    si n > m {
        retour 0;
    }
    pour i dans 0..n {
        si car(t, m - n + i) != car(fin, i) {
            retour 0;
        }
    }
    retour 1;
}
fonction car_texte(c): texte {
    soit t = texte_neuf(1);
    changer_car(t, 0, c);
    retour t;
}
fonction repeter(t, n): texte {
    soit m = longueur(t);
    soit r = texte_neuf(m * n);
    pour k dans 0..n {
        pour i dans 0..m {
            changer_car(r, k * m + i, car(t, i));
        }
    }
    retour r;
}
fonction nettoyer(t): texte {
    soit a = 0;
    soit b = longueur(t);
    tantque a < b && (car(t, a) == 32 || car(t, a) == 9 || car(t, a) == 10 || car(t, a) == 13) {
        a = a + 1;
    }
    tantque b > a && (car(t, b - 1) == 32 || car(t, b - 1) == 9 || car(t, b - 1) == 10 || car(t, b - 1) == 13) {
        b = b - 1;
    }
    retour sous_texte(t, a, b);
}
fonction decouper(t, sep) {
    soit r = tableau(0);
    soit n = longueur(t);
    soit m = longueur(sep);
    soit debut = 0;
    soit i = 0;
    tantque i + m <= n && m > 0 {
        soit egal = 1;
        pour k dans 0..m {
            si car(t, i + k) != car(sep, k) {
                egal = 0;
            }
        }
        si egal == 1 {
            __ajouter(r, sous_texte(t, debut, i));
            i = i + m;
            debut = i;
        } sinon {
            i = i + 1;
        }
    }
    __ajouter(r, sous_texte(t, debut, n));
    retour r;
}
fonction assembler(tab, sep): texte {
    soit p = tab & 16777215;
    soit d = @3[p + 2];
    soit n = @3[p];
    soit total = 0;
    pour k dans 0..n {
        total = total + longueur(@3[d + k]);
    }
    si n > 0 {
        total = total + (n - 1) * longueur(sep);
    }
    soit r = texte_neuf(total);
    soit j = 0;
    pour k dans 0..n {
        si k > 0 {
            pour i dans 0..longueur(sep) {
                changer_car(r, j, car(sep, i));
                j = j + 1;
            }
        }
        soit x = @3[d + k];
        pour i dans 0..longueur(x) {
            changer_car(r, j, car(x, i));
            j = j + 1;
        }
    }
    retour r;
}
fonction remplacer(t, ancien, neuf): texte {
    retour assembler(decouper(t, ancien), neuf);
}
fonction lire_ligne(): texte {
    soit t = __verifier(nouveau(257));
    soit c = lire_car(1);
    si c == 4294967295 {
        retour __texte_fin(t);
    }
    tantque c != 10 && c != 4294967295 {
        si c != 13 {
            si longueur(t) < 256 {
                __mettre(t, c);
            }
        }
        c = lire_car(1);
    }
    retour __texte_fin(t);
}
fonction pgcd(a, b) {
    tantque b != 0 {
        soit r = a % b;
        a = b;
        b = r;
    }
    retour a;
}
fonction borne(x, a, b) {
    si x .< a {
        retour a;
    }
    si x .> b {
        retour b;
    }
    retour x;
}
"""

INTEGRES = {"flottant_petuar": 1, "flottant_128": 1, "comme_flottant_petuar": 1, "vers_ieee128": 1, "de_ieee128": 1,
            "entier_128": 1, "entier_128_signe": 1, "entier_128_de": 2, "flottant_64": 1, "flottant_64_signe": 1, "flottant_64_de": 2, "comme_flottant_64": 1, "arrondi_long": 1,
            "lire_car": 1, "ecrire_car": 2, "ouvrir_lecture": 1, "ouvrir_ecriture": 1, "fermer": 1, "fin_de": 1, "bruit": 0, "pile": 0, "__service": 2,
            "sortie": 1, "entrée": 0, "min4": 2, "max4": 2, "addm4": 2, "cmp3": 1, "gdot": 2, "gemv": 5, "qegal": 2,
            "nb_bits": 1,
            "flottant": 1, "flottant_signe": 1, "entier": 1, "arrondi": 1, "racine": 1, "comme_flottant": 1, "bits": 1,
            "long": 1, "long_signe": 1, "long_de": 2, "bas": 1, "haut": 1}
RETOURS = {"flottant_petuar": "x", "flottant_128": "x", "comme_flottant_petuar": "x", "vers_ieee128": "w", "de_ieee128": "x",
           "entier_128": "w", "entier_128_signe": "w", "entier_128_de": "w", "flottant": "f", "flottant_signe": "f", "racine": "f", "comme_flottant": "f",
           "long": "l", "long_signe": "l", "long_de": "l",
           "flottant_64": "d", "flottant_64_signe": "d", "flottant_64_de": "d", "comme_flottant_64": "d", "arrondi_long": "l"}
SURCHARGES = ("abs", "min", "max")
PQ_DEPUIS = {"e": "__pq_de_e", "f": "__pq_de_d", "d": "__pq_de_d", "l": "__pq_de_l", "w": "__pq_de_w"}
BINAIRES = {"+": "ADD", "-": "SUB", "*": "MUL", "/": "DIV", "%": "MOD", "&": "AND", "|": "OR", "^": "XOR",
            "<<": "SHL", ">>": "SHR"}
FBINAIRES = {"+": "FADD", "-": "FSUB", "*": "FMUL", "/": "FDIV"}
DBINAIRES = {"+": "DADD", "-": "DSUB", "*": "DMUL", "/": "DDIV"}
COMPARAISONS = {"==": ("R1,R2", "JZ"), "!=": ("R1,R2", "JNZ"), "<": ("R1,R2", "JC"), ">=": ("R1,R2", "JNC"),
                ">": ("R2,R1", "JC"), "<=": ("R2,R1", "JNC")}
COMP_FAUX = {"==": ("R1,R2", "JNZ"), "!=": ("R1,R2", "JZ"), "<": ("R1,R2", "JNC"), ">=": ("R1,R2", "JC"),
             ">": ("R2,R1", "JNC"), "<=": ("R2,R1", "JC")}
CHAMPS = {"r": 24, "v": 16, "b": 8, "a": 0}
ARITH = ("+", "-", "*", "/", "%")
BITS_OPS = ("&", "|", "^")


POS_LIGNE = {"soit": 3, "affecter": 3, "ecrire": 4, "si": 4, "tantque": 3, "pour": 5, "segments": 5, "arreter": 1, "continuer": 1,
             "retour": 2, "expr": 2}


ORDINAUX = ["cintux", "allos", "tritios", "petuarios", "pinpetos", "suexos", "sextametos", "oxtumetos", "nametos",
            "decametos"]   # ordinaux gaulois des comptes de fournées des potiers de La Graufesenque


CANAUX = 6           # cylindres du SPU : canaux qui jouent ensemble (moteur V6)
MAX_SEGMENTS = 18    # 6 cylindres x 3 temps
SEGMENTS_DEFAUT = 12  # se partage aussi bien sur 2, 3, 4 ou 6 cœurs


def nom_segment(k, n=CANAUX):
    """Segment k sur n : jusqu'à 6, le nom du cylindre ; au-delà, cylindre·temps (ex. tritios·allos : 3e cylindre, 2e temps)."""
    if n <= CANAUX:
        return ORDINAUX[k]
    return f"{ORDINAUX[k % CANAUX]}·{ORDINAUX[k // CANAUX]}"


def sans_lignes(e):
    """Expression sans ses numéros de ligne (pour comparer deux adresses)."""
    if isinstance(e, tuple):
        if e and e[0] == "var":
            return ("var", e[1])
        return tuple(sans_lignes(x) for x in e)
    return e


def verifier_cumul(corps, cumul, l):
    """Chaque tableau cumulé ne doit servir qu'à des additions de la forme T[e] = T[e] + v (v sans T), pour que la
    somme des copies des segments redonne exactement le même résultat."""
    zones = {c[1]: c[0] for c in cumul}

    def lit_t(e):
        return isinstance(e, tuple) and e and e[0] == "lire" and len(e) > 3 and e[3] in zones

    def interdit(e, ligne):
        if isinstance(e, list):
            for x in e:
                interdit(x, ligne)
            return
        if not isinstance(e, tuple) or not e:
            return
        if lit_t(e):
            raise VtxError(f"ligne {ligne} : le tableau cumulé « {zones[e[3]]} » ne peut être lu que dans « {zones[e[3]]}[x] = "
                           f"{zones[e[3]]}[x] + valeur »")
        for x in e[1:]:
            interdit(x, ligne)

    def marche(lst):
        for st in lst:
            g = st[0]
            if g == "ecrire" and len(st) > 5 and st[5] in zones:
                nom, val = zones[st[5]], st[3]
                ok = False
                if val[0] == "bin" and val[1] in ("+", "-"):
                    paires = ((val[2], val[3]), (val[3], val[2])) if val[1] == "+" else ((val[2], val[3]),)
                    for t_, v_ in paires:
                        if lit_t(t_) and t_[3] == st[5] and sans_lignes(t_[2]) == sans_lignes(st[2]):
                            interdit(v_, st[4])
                            ok = True
                            break
                if not ok:
                    raise VtxError(f"ligne {st[4]} : un tableau cumulé ne s'écrit que sous la forme « {nom}[x] = {nom}[x] + valeur » (ou « - valeur »)")
                interdit(st[2], st[4])
            elif g in ("si",):
                interdit(st[1], st[4])
                marche(st[2])
                if st[3]:
                    marche(st[3])
            elif g == "tantque":
                interdit(st[1], st[3])
                marche(st[2])
            elif g in ("pour", "segments"):
                interdit(st[2], st[5])
                interdit(st[3], st[5])
                marche(st[4])
            else:
                ligne = ligne_instr(st) or l
                interdit(st[1:], ligne)

    marche(corps)


def remplacer_cumul(e, copies):
    """Redirige les accès aux tableaux cumulés vers la copie du segment : copies = {zone: (base, base_copie, n_mots)}."""
    if isinstance(e, list):
        return [remplacer_cumul(x, copies) for x in e]
    if not isinstance(e, tuple) or not e:
        return e
    if e[0] == "lire" and len(e) > 3 and e[3] in copies:
        base, cb, n = copies[e[3]]
        adr = ("bin", "+", ("nombre", (cb - base) & MASK), remplacer_cumul(e[2], copies))
        return ("lire", 3, adr, (3, cb, cb + n))
    if e[0] == "ecrire" and len(e) > 5 and e[5] in copies:
        base, cb, n = copies[e[5]]
        adr = ("bin", "+", ("nombre", (cb - base) & MASK), remplacer_cumul(e[2], copies))
        return ("ecrire", 3, adr, remplacer_cumul(e[3], copies), e[4], (3, cb, cb + n))
    return tuple(remplacer_cumul(x, copies) for x in e)


def deplier_segments(st):
    """Boucle en segments -> (instructions qui fixent les bornes, une boucle « pour » par segment)."""
    _g, var, a, b, corps, l, n, sid = st[:8]
    sa, sb = f"__sa{sid}", f"__sb{sid}"
    pre = [("soit", sa, a, l, "e"), ("soit", sb, b, l, "e")]
    va, vb = ("var", sa, l), ("var", sb, l)
    etendue = ("bin", "-", vb, va)

    def borne(k):
        if k == 0:
            return va
        if k == n:
            return vb
        return ("bin", "+", va, ("bin", "/", ("bin", "*", etendue, ("nombre", k)), ("nombre", n)))

    return pre, [("pour", var, borne(k), borne(k + 1), corps, l, 1) for k in range(n)]


def ligne_instr(s):
    """Numéro de ligne source d'une instruction (0 si elle est engendrée par le compilateur)."""
    k = POS_LIGNE.get(s[0])
    if k is None or len(s) <= k or not isinstance(s[k], int):
        return 0
    return s[k]


def ligne_de(e):
    """Numéro de ligne le plus proche dans une expression (pour les messages d'erreur)."""
    if isinstance(e, tuple):
        if e and e[0] in ("var", "appel") and isinstance(e[-1], int):
            return e[-1]
        for x in e:
            l = ligne_de(x)
            if l:
                return l
    return 0


# Variables en registres : les 4 variables les plus utilisées d'une fonction (le poids d'un usage est multiplié par 8 à
# chaque niveau de boucle) vivent dans R9 à R12 au lieu de leur case du cadre. La fonction garde ces registres dans des
# cases cachées de son cadre à l'entrée et les remet à la sortie. Pas pour les longs, ni pour les variables cachées des
# tableaux rangés, ni dans les fonctions qui ont des accords, des segments ou une hypothèse, ni au pas à pas (le
# débogueur lit les variables dans le cadre : REGISTRES est alors faux).
REGISTRES = True
REGS_VARIABLES = (9, 10, 11, 12)


def poids_boucle(d):
    return 1 << (3 * min(d, 3))


def compter_usages(x, d, sc):
    """Usages pondérés des variables : lecture, écriture, variable de boucle (4 usages par tour)."""
    if isinstance(x, list):
        for y in x:
            compter_usages(y, d, sc)
        return
    if not isinstance(x, tuple) or not x:
        return
    g = x[0]
    if g == "var":
        sc[x[1]] = sc.get(x[1], 0) + poids_boucle(d)
        return
    if g in ("soit", "affecter"):
        sc[x[1]] = sc.get(x[1], 0) + poids_boucle(d)
        compter_usages(x[2], d, sc)
        return
    if g == "tantque":
        compter_usages(x[1], d + 1, sc)
        compter_usages(x[2], d + 1, sc)
        return
    if g == "pour":
        sc[x[1]] = sc.get(x[1], 0) + poids_boucle(d) + 3 * poids_boucle(d + 1)
        compter_usages(x[2], d, sc)
        compter_usages(x[3], d + 1, sc)
        compter_usages(x[4], d + 1, sc)
        return
    for y in x[1:]:
        if isinstance(y, (list, tuple)):
            compter_usages(y, d, sc)


def sans_registres(x):
    """Une fonction dont les variables doivent rester dans le cadre : accords, segments, hypothèses."""
    if isinstance(x, list):
        return any(sans_registres(y) for y in x)
    if not isinstance(x, tuple) or not x:
        return False
    if x[0] in ("accord", "segments") or (x[0] == "appel" and isinstance(x[1], str) and x[1].startswith("__hyp")):
        return True
    return any(sans_registres(y) for y in x[1:] if isinstance(y, (list, tuple)))


def appelle_pile(x):
    """Une fonction qui lit la pile (le ramasse-miettes) : ses appelants gardent peut-être des adresses dans R9 à R12,
    elle range donc les quatre registres dans son cadre, où la lecture de la pile les trouve."""
    if isinstance(x, list):
        return any(appelle_pile(y) for y in x)
    if not isinstance(x, tuple) or not x:
        return False
    if x[0] == "appel" and x[1] == "pile":
        return True
    return any(appelle_pile(y) for y in x[1:] if isinstance(y, (list, tuple)))


# ------------------------------------------------------------------------------------------------ épissage
# Après la génération d'une fonction, ses instructions sont relues comme une suite d'opérations simples (la
# représentation intermédiaire) et « épissées », comme un ARN : on retire les introns, ces instructions qui ne servent
# qu'à déplacer une valeur. Quatre règles, essayées dans cet ordre à chaque instruction, jusqu'à ce que rien ne change :
#   pile       PUSH R1 ; S ; MOV R2,R1 ; POP R1  ->  S (R1 y devient Rf) ; MOV R2,Rf   (la pile devient un registre libre)
#   constante  ADDI Rk,R0,#c ; ADD Rd,Ra,Rk       ->  ADDI Rd,Ra,#c                    (de même SUB -> SUBI)
#   relecture  STF Ra,#o ; LDF Rb,#o              ->  STF Ra,#o, puis MOV Rb,Ra si Rb n'est pas Ra
#   copie      OP Rx,… ; MOV Ry,Rx                ->  OP Ry,…
# Chaque règle demande qu'un registre soit « mort » : sa valeur ne sera plus lue, sur aucun chemin. On le sait par
# l'analyse de vie des registres R1 à R8 sur le graphe de la fonction (sauts compris), refaite après chaque changement :
# un appel détruit R1 à R8, un retour lit R1 et R4, une instruction inconnue (barrière) les lit tous. vtxc fait exactement
# la même chose sur ses mots ; les deux compilateurs produisent toujours les mêmes mots.
EPISSAGE = True
RI_RRR = {"ADD", "SUB", "MUL", "SHL", "SHR", "DIV", "MOD", "MIN", "MAX", "ADDM4", "AND", "OR", "XOR", "GDOT", "FADD", "FSUB",
          "FMUL", "FDIV", "FEQ", "FLT", "FLE", "MULHU", "QEGAL", "LDX", "LDQ", "ET4", "OU4", "EXQ"}
RI_RR = {"SHL4", "SHR4", "MOV", "CMP3", "FSQRT", "ITOF", "ITOFS", "FTOI", "FROUND", "COMPTE", "ADDI", "SUBI", "LD", "NON4",
         "ANTI"}
RI_DEST = RI_RRR | RI_RR | {"LDI", "LDF"}          # le premier registre est seulement écrit
RI_SAUTS = {"JMP", "JZ", "JNZ", "JC", "JNC", "CALL", "RET", "HALT"}
RI_TOUS = 0x1FE                                     # R1 à R8


def ri_reg(a):
    a = a.strip().upper()
    if len(a) >= 2 and a[0] == "R" and a[1:].isdigit():
        return int(a[1:])
    return None


def ri_acces(op, args):
    """(registres écrits, registres lus) d'une instruction simple ; None si elle fait autre chose (barrière)."""
    r = [ri_reg(a) for a in args]
    if op in RI_RRR:
        return {r[0]}, {r[1], r[2]}
    if op in RI_RR:
        return {r[0]}, {r[1]}
    if op in ("LDI", "LDF", "IN", "POP"):
        return {r[0]}, set()
    if op in ("STF", "OUT", "PUSH"):
        return set(), {r[0]}
    if op in ("CMP", "ST"):
        return set(), {r[0], r[1]}
    if op in ("STX", "STQ"):
        return set(), {r[0], r[1], r[2]}
    return None


def ri_masque(regs):
    m = 0
    for r in regs:
        if 1 <= r <= 8:
            m |= 1 << r
    return m


def ri_vie(ins, etiq):
    """Pour chaque instruction : le masque des registres R1 à R8 vivants après elle."""
    n = len(ins)
    lus, ecr, succ = [0] * n, [0] * n, []
    for k, (op, args) in enumerate(ins):
        if op in ("JMP", "JZ", "JNZ", "JC", "JNC"):
            t = etiq.get(args[0].upper())
            s = ([] if op == "JMP" else [k + 1]) + ([t] if t is not None else [])
            if t is None:
                lus[k] = RI_TOUS
        elif op == "CALL":
            s, ecr[k] = [k + 1], RI_TOUS
        elif op == "RET":
            s, lus[k] = [], (1 << 1) | (1 << 4)
        elif op == "HALT":
            s = []
        else:
            s = [k + 1]
            ac = ri_acces(op, args)
            if ac is None:
                lus[k] = RI_TOUS
            else:
                ecr[k], lus[k] = ri_masque(ac[0]), ri_masque(ac[1])
        succ.append([x for x in s if x < n])
    apres, avant = [0] * n, [0] * n
    change = True
    while change:
        change = False
        for k in range(n - 1, -1, -1):
            a = 0
            for x in succ[k]:
                a |= avant[x]
            v = lus[k] | (a & ~ecr[k])
            if a != apres[k] or v != avant[k]:
                apres[k], avant[k], change = a, v, True
    return apres


def epissage(lignes):
    """Épisse le code d'une fonction (lignes d'assembleur) ; rend les nouvelles lignes."""
    el = []                         # [genre, op, args, vivants après] ; genre : "e" étiquette, "d" directive, "i" instruction
    for l in lignes:
        t = l.strip()
        if t.endswith(":") and not t.startswith("."):
            el.append(["e", t, None, 0])
        elif t.startswith(".") or not t:
            el.append(["d", l, None, 0])
        else:
            p = t.split(None, 1)
            el.append(["i", p[0].upper(), [a.strip() for a in p[1].split(",")] if len(p) > 1 else [], 0])
    # seules les étiquettes visées par un saut séparent deux instructions (une étiquette que rien ne vise est transparente)
    cibles = {e[2][0].upper() for e in el if e[0] == "i" and e[1] in ("JMP", "JZ", "JNZ", "JC", "JNC")}
    for e in el:
        if e[0] == "e" and e[1][:-1].upper() not in cibles:
            e[0] = "d"

    def analyser():
        ins, etiq, place = [], {}, []
        for i, (g, op, args, _) in enumerate(el):
            if g == "e":
                etiq[op[:-1].upper()] = len(ins)
            elif g == "i":
                place.append(i)
                ins.append((op, args))
        for i, v in zip(place, ri_vie(ins, etiq)):
            el[i][3] = v

    def suivant(j):
        """L'instruction après j, s'il n'y a ni étiquette ni fin avant : son indice, sinon -1."""
        j += 1
        while j < len(el) and el[j][0] == "d":
            j += 1
        return j if j < len(el) and el[j][0] == "i" else -1

    def mort_apres(j, r):
        return not (el[j][3] >> r) & 1

    def regle_pile(i):
        if el[i][1] != "PUSH" or ri_reg(el[i][2][0]) != 1:
            return False
        s, j = [], suivant(i)
        while j >= 0 and not (el[j][1] == "MOV" and [ri_reg(x) for x in el[j][2]] == [2, 1]):
            op = el[j][1]
            if op in RI_SAUTS or op in ("PUSH", "POP") or ri_acces(op, el[j][2]) is None:
                return False
            s.append(j)
            j = suivant(j)
        if j < 0 or not s:
            return False
        jp = suivant(j)
        if jp < 0 or el[jp][1] != "POP" or ri_reg(el[jp][2][0]) != 1:
            return False
        vus = set()
        for k in s:
            ecr, lus = ri_acces(el[k][1], el[k][2])
            vus |= ecr | lus
        if 13 in vus or 14 in vus:                # la pile ou le cadre lus directement (pile()) : on n'y touche pas
            return False
        for k in s:                               # R1 doit être écrit dans S avant d'y être lu
            ecr, lus = ri_acces(el[k][1], el[k][2])
            if 1 in lus:
                return False
            if 1 in ecr:
                break
        else:
            return False
        for f in (3, 5, 6, 7, 8):
            if f not in vus and mort_apres(jp, f):
                break
        else:
            return False
        for k in s:
            el[k][2] = [f"R{f}" if ri_reg(x) == 1 else x for x in el[k][2]]
        el[j][2] = ["R2", f"R{f}"]
        # la vie des registres dans le passage réécrit : refaite en remontant depuis la fin (le reste reste prudent)
        vivants = el[jp][3]
        for k in [j] + s[::-1]:
            el[k][3] = vivants
            ecr, lus = ri_acces(el[k][1], el[k][2])
            vivants = (vivants & ~ri_masque(ecr)) | ri_masque(lus)
        el[i][0] = el[jp][0] = "x"            # retirées
        return True

    def regle_constante(i):
        j = suivant(i)
        if el[i][1] != "ADDI" or j < 0 or el[j][1] not in ("ADD", "SUB"):
            return False
        k, z, c = ri_reg(el[i][2][0]), ri_reg(el[i][2][1]), el[i][2][2]
        d, a, b = (ri_reg(x) for x in el[j][2])
        if z != 0 or k == 0:
            return False
        if b == k and a != k:
            src = a
        elif el[j][1] == "ADD" and a == k and b != k:
            src = b
        else:
            return False
        if k != d and not mort_apres(j, k):
            return False
        el[j] = ["i", "ADDI" if el[j][1] == "ADD" else "SUBI", [f"R{d}", f"R{src}", c], el[j][3]]
        el[i][0] = "x"
        return True

    def regle_relecture(i):
        j = suivant(i)
        if el[i][1] != "STF" or j < 0 or el[j][1] != "LDF" or el[i][2][1] != el[j][2][1]:
            return False
        a, b = ri_reg(el[i][2][0]), ri_reg(el[j][2][0])
        if a == b:
            el[j][0] = "x"
        else:
            el[j] = ["i", "MOV", [f"R{b}", f"R{a}"], el[j][3]]
        return True

    def regle_copie(i):
        j = suivant(i)
        if el[i][1] not in RI_DEST or j < 0 or el[j][1] != "MOV":
            return False
        x = ri_reg(el[i][2][0])
        y, x2 = ri_reg(el[j][2][0]), ri_reg(el[j][2][1])
        if x2 != x or y == x or not 1 <= x <= 8 or y in (0, 13, 14, 15) or not mort_apres(j, x):
            return False
        el[i][2] = [f"R{y}"] + el[i][2][1:]
        el[i][3] = el[j][3]
        el[j][0] = "x"
        return True

    # chaque tour refait l'analyse de vie, puis essaie les règles d'un bout à l'autre ; une règle appliquée laisse
    # l'analyse juste (ou prudente) pour la suite du tour
    change = True
    while change:
        change = False
        analyser()
        i = 0
        while i < len(el):
            if el[i][0] == "i" and (regle_pile(i) or regle_constante(i) or regle_relecture(i) or regle_copie(i)):
                change = True
                el = [e for e in el if e[0] != "x"]
                continue
            i += 1
    return [op if g in ("e", "d") else "    " + op + (" " + ",".join(args) if args else "") for g, op, args, _ in el]


# ------------------------------------------------------------------------------------------------ quits rangés
# Un tableau de quits ou de logiques range 16 éléments par mot. Le compilateur traduit t[i] en
#   (@e[base + (i >> 4)] >> ((i & 15) * 2)) & 3
# et t[i] = v en lecture du mot, remplacement du quit, écriture. Avec les optimisations, ces formes deviennent les
# instructions quaternaires LDQ et STQ, quand l'indice est simple : un nombre, une variable, ou a + b, a - b, a × b de
# ceux-là (le même indice, écrit pareil, à chaque place) ; vtxc fait exactement le même test. Calculer l'indice une
# seule fois au lieu de deux ne change rien : il n'appelle pas de fonction.
def indice_simple(x):
    feuille = lambda y: y[0] in ("nombre", "var")
    return feuille(x) or (x[0] == "bin" and x[1] in ("+", "-", "*") and feuille(x[2]) and feuille(x[3]))


def motif_place(et, adr, dec):
    """(étage, base, indice) si adr est base + (i >> 4) (ou i >> 4) et dec (i & 15) * 2, avec le même indice simple."""
    if not (dec[0] == "bin" and dec[1] == "*" and dec[3] == ("nombre", 2) and dec[2][0] == "bin" and dec[2][1] == "&"
            and dec[2][3] == ("nombre", 15)):
        return None
    idx = dec[2][2]
    if not indice_simple(idx):
        return None
    if adr[0] == "bin" and adr[1] == ">>" and adr[2] == idx and adr[3] == ("nombre", 4):
        return et, 0, idx
    if (adr[0] == "bin" and adr[1] == "+" and adr[2][0] == "nombre" and adr[3][0] == "bin" and adr[3][1] == ">>"
            and adr[3][2] == idx and adr[3][3] == ("nombre", 4)):
        return et, adr[2][1], idx
    return None


def motif_quit(e):
    """(étage, base, indice) si e est la lecture d'un quit rangé, sinon None."""
    if not (e[0] == "bin" and e[1] == "&" and e[3] == ("nombre", 3) and e[2][0] == "bin" and e[2][1] == ">>"):
        return None
    lu, dec = e[2][2], e[2][3]
    if not (lu[0] == "lire" and len(lu) >= 3 and isinstance(lu[1], int)):
        return None
    return motif_place(lu[1], lu[2], dec)


def motif_ecriture_quit(s):
    """(étage, base, indice, valeur) si s est l'écriture d'un quit rangé, sinon None."""
    et, adr, nv = s[1], s[2], s[3]
    if not (isinstance(et, int) and nv[0] == "bin" and nv[1] == "|" and nv[2][0] == "bin" and nv[2][1] == "&"
            and nv[3][0] == "bin" and nv[3][1] == "<<"):
        return None
    lu, garde, mis = nv[2][2], nv[2][3], nv[3]
    if not (lu[0] == "lire" and lu[1] == et and garde[0] == "non" and garde[1][0] == "bin" and garde[1][1] == "<<"
            and garde[1][2] == ("nombre", 3) and mis[2][0] == "bin" and mis[2][1] == "&" and mis[2][3] == ("nombre", 3)):
        return None
    q = motif_place(et, adr, garde[1][3])
    if q is None or motif_place(et, lu[2], garde[1][3]) != q or motif_place(et, adr, mis[3]) != q:
        return None
    return q + (mis[2][2],)

class Generateur:
    def __init__(self, fonctions, optim=True, blobs=None, reserve=None):
        self.structs, self.types_champs, self.textes = {}, {}, {}
        self.regs = {}
        self.optim = optim
        self.blobs = blobs or []
        self.fonctions = {}
        self.reserve = reserve or {}
        self.a_generer = []
        for f in fonctions:
            if f.nom in self.fonctions or f.nom in INTEGRES:
                raise VtxError(f"ligne {f.ligne} : fonction « {f.nom} » déjà définie")
            self.fonctions[f.nom] = f
        if "principal" not in self.fonctions:
            raise VtxError("la fonction « principal » est absente")
        if self.fonctions["principal"].params:
            raise VtxError("la fonction « principal » ne prend aucun paramètre")
        self.sortie, self.n = [], 0
        self.vtypes, self.vhaut = {}, {}

    def emettre(self, texte):
        self.sortie.append("    " + texte)

    def etiquette(self, nom):
        self.sortie.append(nom + ":")

    def nouvelle(self, base):
        self.n += 1
        return f"{base}{self.n}"

    def generer(self):
        self.sortie.append("; programme généré par vtx 0.5")
        self.emettre(f"LDI R14,{STACK_TOP}")
        self.emettre("CALL F_principal")
        self.emettre("HALT")
        for f in list(self.fonctions.values()):
            self.fonction(f)
        while self.a_generer:
            self.fonction(self.a_generer.pop(0))
        for i, (et, adr, vals) in enumerate(self.blobs):
            self.etiquette(f"DONNEES{i}")
            for k in range(0, len(vals), 8):
                self.emettre(".mot " + ",".join(str(v) for v in vals[k:k + 8]))
        for texte, n in sorted(self.textes.items(), key=lambda x: x[1]):
            self.etiquette(f"TEXTE{n}")                 # longueur, puis un caractère par mot (numéro Unicode)
            vals = [len(texte)] + [ord(c) for c in texte]
            for k in range(0, len(vals), 8):
                self.emettre(".mot " + ",".join(str(v) for v in vals[k:k + 8]))
        return "\n".join(self.sortie) + "\n"

    def signature(self, nom, ligne):
        """Fonction appelée : définie, ou prise dans le prélude à la demande (division et décalages des longs)."""
        if nom in self.fonctions:
            return self.fonctions[nom]
        if nom in self.reserve:
            f = self.reserve.pop(nom)
            self.fonctions[nom] = f
            self.a_generer.append(f)
            return f
        raise VtxError(f"ligne {ligne} : fonction « {nom} » inconnue")

    # ---------------------------------------------------------------- types
    def joindre(self, a, b, ligne, op):
        if a == b:
            return a
        if "x" in (a, b):
            if {a, b} <= {"x", "e", "f", "d"}:
                return "x"                   # un entier, un flottant ou un flottant_64 s'élargit en flottant_petuar
            raise VtxError(f"ligne {ligne} : « {op} » mélange un {NOM_TYPE[a]} et un {NOM_TYPE[b]} : convertissez avec "
                           f"flottant_petuar()")
        if {a, b} == {"e", "f"}:
            return "f"
        if {a, b} == {"e", "l"}:
            return "l"
        if {a, b} == {"e", "w"}:
            return "w"                       # un entier s'élargit en entier_128 (zéros à gauche, comme vers long)
        if "w" in (a, b):
            raise VtxError(f"ligne {ligne} : « {op} » mélange un {NOM_TYPE[a]} et un {NOM_TYPE[b]} : convertissez avec "
                           f"entier_128()")
        if "d" in (a, b) and {a, b} <= {"e", "f", "d"}:
            return "d"                       # un entier ou un flottant s'élargit en flottant_64 (sans perte)
        if "d" in (a, b):
            raise VtxError(f"ligne {ligne} : « {op} » mélange un {NOM_TYPE[a]} et un {NOM_TYPE[b]} : convertissez avec "
                           f"flottant_64() ou long()")
        raise VtxError(f"ligne {ligne} : « {op} » mélange un flottant et un long : convertissez avec flottant(), long() ou entier()")

    def typ(self, e):
        g = e[0]
        if g == "non_log" and self.typ(e[1]) == "q":
            raise VtxError(f"ligne {ligne_de(e)} : « ! » ne s'applique pas à un logique : utilisez non4() ou anti()")
        if g in ("nombre", "etiq", "lire", "non_log", "blit"):
            return "e"
        if g == "fnombre":
            return "f"
        if g == "lnombre":
            return "l"
        if g == "dnombre":
            return "d"
        if g == "wnombre":
            return "w"
        if g == "xnombre":
            return "x"
        if g == "qnombre":
            return "q"
        if g == "var":
            if e[1] not in self.vtypes:
                raise VtxError(f"ligne {e[2]} : variable « {e[1]} » inconnue")
            return self.vtypes[e[1]]
        if g in ("nouveau_de", "construire"):
            return "r:" + e[1]
        if g == "champ_ref" or (g == "champ" and est_ref(self.typ(e[1]))):
            return self.champ_de(e)[2]
        if g in ("champ", "quit"):
            if self.typ(e[1]) != "e":
                raise VtxError(f"ligne {ligne_de(e)} : les champs et les quits s'appliquent à un entier")
            return "e"
        if g == "non":
            t = self.typ(e[1])
            if t in ("f", "d", "x"):
                raise VtxError(f"ligne {ligne_de(e)} : « ~ » ne s'applique pas à un flottant")
            if t == "q":
                raise VtxError(f"ligne {ligne_de(e)} : « ~ » ne s'applique pas à un logique : utilisez non4() ou anti()")
            return t
        if g == "bin":
            op, ta, tb, l = e[1], self.typ(e[2]), self.typ(e[3]), ligne_de(e)
            if est_ref(ta) or est_ref(tb):
                nul_a, nul_b = e[2] == ("nombre", 0), e[3] == ("nombre", 0)
                if op in ("==", "!=") and (ta == tb or (est_ref(ta) and nul_b) or (est_ref(tb) and nul_a)):
                    return "e"
                raise VtxError(f"ligne {l} : « {op} » ne s'applique pas à une {NOM_TYPE[ta if est_ref(ta) else tb]} : "
                               f"comparez seulement (== ou !=) à une référence de même structure ou à nul")
            if "q" in (ta, tb):
                if op in ("==", "!=") and (ta == tb or e[2][0] == "blit" or e[3][0] == "blit"):
                    return "e"
                if op in ("==", "!=", "&&", "||"):
                    raise VtxError(f"ligne {l} : « {op} » entre un logique et un {NOM_TYPE[ta if ta != 'q' else tb]} : "
                                   f"utilisez logique() ou entier()" if ta != tb else
                                   f"ligne {l} : « {op} » sur des logiques : utilisez et4(), ou4(), fusion()")
                raise VtxError(f"ligne {l} : « {op} » ne s'applique pas à un logique : utilisez et4(), ou4(), non4(), anti(), "
                               f"fusion(), consensus()")
            if op in ("&&", "||") or op in COMPARAISONS:
                self.joindre(ta, tb, l, op)
                return "e"
            if op in ARITH:
                t = self.joindre(ta, tb, l, op)
                if t in ("f", "d", "x") and op == "%":
                    raise VtxError(f"ligne {l} : le reste « % » n'est pas défini pour les flottants")
                return t
            if op in BITS_OPS:
                t = self.joindre(ta, tb, l, op)
                if t in ("f", "d", "x"):
                    raise VtxError(f"ligne {l} : « {op} » ne s'applique pas à un flottant (voir bits())")
                return t
            if op in ("<<", ">>"):
                if ta in ("f", "d", "x") or tb != "e":
                    raise VtxError(f"ligne {l} : décalage d'un entier ou d'un long par un entier seulement")
                return ta
            if ta != "e" or tb != "e":
                raise VtxError(f"ligne {l} : « {op} » s'applique aux entiers seulement")
            return "e"
        if g == "appel":
            nom = e[1]
            if nom in OPS_LOGIQUES:
                ts = ["q" if a[0] == "blit" else self.typ(a) for a in e[2]]
                if len(ts) != OPS_LOGIQUES[nom]:
                    raise VtxError(f"ligne {e[3]} : « {nom} » attend {OPS_LOGIQUES[nom]} argument(s)")
                if any(t not in ("q", "e") for t in ts) or len(set(ts)) != 1:
                    raise VtxError(f"ligne {e[3]} : « {nom} » prend des logiques, ou des entiers qui rangent 16 logiques "
                                   f"(un par quit), sans mélange")
                return ts[0]
            if nom in ("logique", "comme_logique"):
                return "q"
            if nom == "__code_logique":
                return "e"
            if nom in ("racine", "bits") and len(e[2]) == 1 and self.typ(e[2][0]) == "x":
                return "x" if nom == "racine" else "w"      # bits(x) : les quatre points, comme un entier_petuar
            if nom in ("racine", "bits") and len(e[2]) == 1 and self.typ(e[2][0]) == "d":
                return "d" if nom == "racine" else "l"      # racine d'un flottant_64 ; bits(x) : ses 64 bits, comme long
            if nom in ("bas", "haut") and len(e[2]) == 1 and self.typ(e[2][0]) == "w":
                return "l"                                  # les deux moitiés de 64 bits d'un entier_128
            if nom in RETOURS:
                return RETOURS[nom]
            if nom in INTEGRES:
                return "e"
            if nom in SURCHARGES:
                ts = [self.typ(a) for a in e[2]]
                if "f" in ts or "l" in ts or "d" in ts or "w" in ts or "x" in ts:
                    t = ts[0]
                    for x in ts[1:]:
                        t = self.joindre(t, x, e[3], nom)
                    return t
            if nom in self.fonctions:
                return self.fonctions[nom].rtype
            if nom in self.reserve:
                return self.reserve[nom].rtype
            raise VtxError(f"ligne {e[3]} : fonction « {nom} » inconnue")
        raise VtxError(f"expression inconnue : {g}")

    def champ_de(self, e):
        """(structure, position, type) du champ e = ("champ_ref" ou "champ", référence, nom, …)."""
        t = self.typ(e[1])
        if not est_ref(t):
            raise VtxError(f"ligne {ligne_de(e)} : « .{e[2]} » : il faut une référence à une structure, pas un {NOM_TYPE[t]}")
        st = t[2:]
        if e[2] not in self.structs.get(st, []):
            raise VtxError(f"ligne {ligne_de(e)} : champ inconnu « {e[2]} » dans la structure {st}")
        return st, self.structs[st].index(e[2]), self.types_champs.get(st, {}).get(e[2], "e")

    def adresse_champ(self, base, pos):
        """R1 = adresse dans l'étage, R2 = étage, pour le champ pos du bloc dont l'adresse globale est base."""
        self.expr(base)
        self.emettre("MOV R2,R1")
        self.emettre("ADDI R6,R0,#24")
        self.emettre("SHR R2,R2,R6")
        if pos:
            self.emettre(f"ADDI R1,R1,#{pos}")

    def conv(self, t, voulu, ligne):
        if t == voulu:
            return
        if (t, voulu) == ("e", "f"):
            self.emettre("ITOF R1,R1")
        elif (t, voulu) == ("e", "l"):
            self.emettre("ADDI R4,R0,#0")
        elif (t, voulu) == ("e", "w"):
            for r in ("R3", "R4", "R6"):
                self.emettre(f"ADDI {r},R0,#0")
        elif (t, voulu) == ("e", "d"):
            self.emettre("ITOD R1,R1")
        elif (t, voulu) == ("f", "d"):
            self.emettre("FTOD R1,R1")
        else:
            raise VtxError(f"ligne {ligne} : conversion implicite impossible de {NOM_TYPE[t]} vers {NOM_TYPE[voulu]} : "
                           f"utilisez entier(), flottant(), long() ou logique()")

    def charger(self, reg, v):
        if v <= 255:
            self.emettre(f"ADDI {reg},R0,#{v}")
        else:
            self.emettre(f"LDI {reg},{v}")

    # ---------------------------------------------------------------- fonctions et variables
    def locales(self, instr, acc):
        for s in instr:
            if s[0] == "soit":
                # la variable d'une boucle « pour x dans t » se redéclare comme celle d'une boucle ordinaire
                acc.append((s[1], s[3], "pour" if len(s) > 5 and s[5] == "chaque" else "soit", s))
            elif s[0] == "pour":
                acc.append((s[1], s[5], "pour", s))
                vus = self.__dict__.setdefault("_corps_vus", set())
                copie = len(s) > 7 and s[7] == "copie"   # segments suivants : mêmes variables que le premier
                if id(s[4]) not in vus and not copie:    # les segments d'une boucle partagent le même corps
                    vus.add(id(s[4]))
                    self.locales(s[4], acc)
            elif s[0] == "bloc":
                self.locales(s[1], acc)
            elif s[0] == "segments":
                acc.append((f"__sa{s[7]}", s[5], "soit", ("soit", f"__sa{s[7]}", ("nombre", 0), s[5], "e")))
                acc.append((f"__sb{s[7]}", s[5], "soit", ("soit", f"__sb{s[7]}", ("nombre", 0), s[5], "e")))
                acc.append((s[1], s[5], "pour", s))
                self.locales(s[4], acc)
            elif s[0] == "accord":
                for mesure in s[2]:
                    for st, _n, _nom in mesure:
                        self.locales([st], acc)
            elif s[0] == "si":
                self.locales(s[2], acc)
                if s[3]:
                    self.locales(s[3], acc)
            elif s[0] == "tantque":
                self.locales(s[2], acc)

    def fonction(self, f):
        debut = len(self.sortie)
        self._corps_vus = set()
        self.f, self.vars = f, {}
        self.vtypes, self.vhaut = {}, {}
        self.boucles = []
        o = 2
        for p, t in reversed(list(zip(f.params, f.ptypes))):
            if p in self.vars:
                raise VtxError(f"ligne {f.ligne} : paramètre « {p} » en double")
            if t in QUATRE:
                self.vhaut[p], self.vars[p] = o + 2, o + 3     # le mot k est à vars - k
                o += 4
            elif t in LARGES2:
                self.vhaut[p], self.vars[p] = o, o + 1
                o += 2
            else:
                self.vars[p] = o
                o += 1
            self.vtypes[p] = t
        loc = []
        self.locales(f.corps, loc)
        kinds, nl = {}, 0
        for nom, l, kind, st in loc:
            chaque = st[0] == "soit"
            if nom in self.vars:
                if kinds.get(nom) == "pour" and kind == "pour":
                    t2 = (st[4] or self.typ(st[2])) if chaque else "e"
                    if t2 != self.vtypes.get(nom, "e"):
                        raise VtxError(f"ligne {l} : la variable de boucle « {nom} » change de type : donnez-lui un autre nom")
                    continue
                raise VtxError(f"ligne {l} : variable « {nom} » déjà déclarée")
            kinds[nom] = kind
            if kind == "pour":
                # la variable d'un « pour x dans t » a le type de ses valeurs (flottant pour un tableau de flottants)
                t = (st[4] or self.typ(st[2])) if chaque else "e"
            else:
                t = st[4] if len(st) > 4 and st[4] else self.typ(st[2])
            self.vtypes[nom] = t
            nl += 1
            self.vars[nom] = -nl
            if t in LARGES2:
                nl += 1
                self.vhaut[nom] = -nl
                if t in QUATRE:
                    nl += 2
        # les variables en registres (voir REGISTRES) : par usages pondérés, à égalité la plus haute dans le cadre
        self.regs = {}
        if REGISTRES and self.optim and not sans_registres(f.corps):
            sc = {}
            compter_usages(f.corps, 0, sc)
            cand = [n for n in self.vars if sc.get(n, 0) >= 16 and self.vtypes.get(n, "e") not in LARGES2 and not n.startswith("__q")]
            cand.sort(key=lambda n: (-sc[n], -self.vars[n]))
            for k, n in enumerate(cand[:len(REGS_VARIABLES)]):
                self.regs[n] = REGS_VARIABLES[k]
        gardes = sorted(self.regs.values())
        if REGISTRES and self.optim and appelle_pile(f.corps):
            gardes = list(REGS_VARIABLES)
        if o > 128 or nl + len(gardes) > 127:
            raise VtxError(f"ligne {f.ligne} : trop de paramètres ou de variables")
        self.etiquette(f"F_{f.nom}")
        self.emettre(f".fonction {f.nom} {getattr(f, 'origine', '') or '-'}")
        for nom, off in self.vars.items():
            t = self.vtypes.get(nom, "e")
            self.emettre(f".var {nom} {off} {t} {self.vhaut.get(nom, 0)}")
        self.emettre("PUSH R13")
        self.emettre("MOV R13,R14")
        if nl + len(gardes):
            self.emettre(f"SUBI R14,R14,#{nl + len(gardes)}")
        # les registres gardés dans des cases cachées, puis les paramètres en registres chargés
        for k, r in enumerate(gardes):
            self.emettre(f"STF R{r},#{-(nl + 1 + k)}")
        for n, r in sorted(self.regs.items(), key=lambda x: x[1]):
            if self.vars[n] > 0:
                self.emettre(f"LDF R{r},#{self.vars[n]}")
        self.fin = f"F_{f.nom}_fin"
        for s in f.corps:
            self.instr(s)
        self.emettre("ADDI R1,R0,#0")
        if f.rtype in LARGES2:
            for r in REGS_T[f.rtype][1:]:
                self.emettre(f"ADDI {r},R0,#0")
        self.etiquette(self.fin)
        for k, r in enumerate(gardes):
            self.emettre(f"LDF R{r},#{-(nl + 1 + k)}")
        self.emettre("MOV R14,R13")
        self.emettre("POP R13")
        self.emettre("RET")
        # l'épissage (voir EPISSAGE) : pas au pas à pas, ni dans __init (ses copies gardent des registres au-delà d'une
        # étiquette), ni avec des accords, des segments ou une hypothèse
        if EPISSAGE and REGISTRES and self.optim and f.nom != "__init" and not sans_registres(f.corps):
            self.sortie[debut:] = epissage(self.sortie[debut:])

    def variable(self, nom, ligne):
        if nom not in self.vars:
            raise VtxError(f"ligne {ligne} : variable « {nom} » inconnue")
        return self.vars[nom]

    def ranger(self, nom, t, ligne):
        off = self.variable(nom, ligne)
        if nom in self.regs:
            self.emettre(f"MOV R{self.regs[nom]},R1")
            return
        self.emettre(f"STF R1,#{off}")
        if t in LARGES2:
            for k, r in enumerate(REGS_T[t][1:], 1):
                self.emettre(f"STF {r},#{off - k}")

    # ---------------------------------------------------------------- conditions
    def refuser_logique(self, e):
        if self.typ(e) == "q":
            raise VtxError(f"ligne {ligne_de(e)} : un logique a quatre valeurs et ne sert pas de condition : utilisez "
                           f"« selon », ou comparez (x == vrai)")

    def expr_bool(self, e):
        """Valeur de vérité dans R1 (non nulle = vrai) : un flottant est vrai s'il n'est pas ±0, un long s'il n'est pas nul."""
        self.refuser_logique(e)
        if self.typ(e) == "x":
            raise VtxError(f"ligne {ligne_de(e)} : un flottant_petuar a un état à quatre valeurs et ne sert pas de condition : "
                           f"comparez-le, ou utilisez « selon etat(x) »")
        t = self.expr(e)
        if t == "f":
            self.emettre("LDI R2,2147483647")
            self.emettre("AND R1,R1,R2")
        elif t == "l":
            self.emettre("OR R1,R1,R4")
        elif t == "d":
            self.emettre("LDI R2,2147483647")
            self.emettre("AND R4,R4,R2")
            self.emettre("OR R1,R1,R4")
        elif t == "w":
            self.emettre("OR R1,R1,R3")
            self.emettre("OR R4,R4,R6")
            self.emettre("OR R1,R1,R4")

    def saut_faux(self, e, lab):
        """Saute à lab si la condition est fausse, sans fabriquer de booléen."""
        self.refuser_logique(e)
        if not self.optim:
            self.expr_bool(e)
            self.emettre("CMP R1,R0")
            self.emettre(f"JZ {lab}")
        elif e[0] == "bin" and e[1] in COMP_FAUX and ("q" in (self.typ(e[2]), self.typ(e[3]))
                                                    or est_ref(self.typ(e[2])) or est_ref(self.typ(e[3]))):
            regs, jmp = COMP_FAUX[e[1]]
            ta, tb = self.typ(e[2]), self.typ(e[3])
            self.paire(e[2], e[3], "q" if "q" in (ta, tb) else (ta if est_ref(ta) else tb))
            self.emettre(f"CMP {regs}")
            self.emettre(f"{jmp} {lab}")
        elif e[0] == "bin" and e[1] in COMP_FAUX and self.joindre(self.typ(e[2]), self.typ(e[3]), ligne_de(e), e[1]) == "e":
            regs, jmp = COMP_FAUX[e[1]]
            ra, rb = self.deux_ops(e[2], e[3])
            self.emettre(f"CMP {self.regs_comp(regs, ra, rb)}")
            self.emettre(f"{jmp} {lab}")
        elif e[0] == "bin" and e[1] == "&&":
            self.saut_faux(e[2], lab)
            self.saut_faux(e[3], lab)
        elif e[0] == "bin" and e[1] == "||":
            lb, lt = self.nouvelle("Lou"), self.nouvelle("Lvrai")
            self.saut_faux(e[2], lb)
            self.emettre(f"JMP {lt}")
            self.etiquette(lb)
            self.saut_faux(e[3], lab)
            self.etiquette(lt)
        elif e[0] == "non_log":
            lc = self.nouvelle("Lnon")
            self.saut_faux(e[1], lc)
            self.emettre(f"JMP {lab}")
            self.etiquette(lc)
        else:
            self.expr_bool(e)
            self.emettre("CMP R1,R0")
            self.emettre(f"JZ {lab}")

    # ---------------------------------------------------------------- instructions
    def marque(self, s):
        """Directive de débogage : début de l'instruction source s (ignorée par l'assembleur)."""
        l = ligne_instr(s)
        if l:
            self.emettre(f".ligne {l}")

    def instr(self, s):
        self.marque(s)
        g = s[0]
        if g in ("soit", "affecter") and self.optim and s[1] in self.regs and self.vtypes.get(s[1]) == "e":
            x = s[2]
            if (x[0] == "bin" and x[1] in BINAIRES and self.typ(x) == "e" and self.typ(x[2]) == "e"
                    and self.typ(x[3]) == "e"):
                # x = a op b, x en registre : le calcul va directement dans le registre de x
                self.variable(s[1], s[3])
                rt = f"R{self.regs[s[1]]}"
                if (x[1] in ("+", "-") and x[2][0] == "var" and x[2][1] == s[1] and x[3][0] == "nombre"
                        and x[3][1] <= 255):
                    self.emettre(f"{'ADDI' if x[1] == '+' else 'SUBI'} {rt},{rt},#{x[3][1]}")
                    return
                ra, rb = self.deux_ops(x[2], x[3])
                self.emettre(f"{BINAIRES[x[1]]} {rt},{ra},{rb}")
                return
        if g == "soit":
            t = self.vtypes[s[1]]
            if est_ref(t) and len(s) > 4 and s[4] == t and s[2][0] in ("var", "appel") and self.typ(s[2]) == "e":
                # soit x: Structure = entier : la déclaration explicite vaut conversion (la racine d'une mémoire
                # rechargée, par exemple)
                self.expr(s[2])
            else:
                self.expr(s[2], t)
            self.ranger(s[1], t, s[3])
        elif g == "affecter":
            self.variable(s[1], s[3])
            t = self.vtypes[s[1]]
            self.expr(s[2], t)
            self.ranger(s[1], t, s[3])
        elif g == "ecrire_champ":
            _st, pos, t = self.champ_de(("champ_ref", s[1], s[2], s[4]))
            if t in LARGES2:
                raise VtxError(f"ligne {s[4]} : un champ ne peut pas contenir un {NOM_TYPE[t]}")
            self.expr(s[3], t)
            self.emettre("PUSH R1")
            self.adresse_champ(s[1], pos)
            self.emettre("POP R7")
            self.emettre("STX R1,R7,R2")
        elif g == "ecrire":
            if self.typ(s[3]) in LARGES2:
                raise VtxError(f"ligne {s[4]} : un {NOM_TYPE[self.typ(s[3])]} occupe deux mots : écrivez bas(x) et haut(x) séparément")
            et = s[1]
            q = motif_ecriture_quit(s) if self.optim else None
            if q:
                # STQ : le quit i d'un tableau rangé reçoit la valeur, en une instruction
                et, base, idx, v = q
                self.deux(v, idx)
                if base:
                    self.charger("R3", base)
                self.emettre(f"STQ R1,{'R3' if base else 'R0'},R2,@{et}")
            elif isinstance(et, int):
                self.expr(s[2], "e")
                self.emettre("PUSH R1")
                self.expr(s[3])
                self.emettre("MOV R2,R1")
                self.emettre("POP R1")
                self.emettre(f"ST R1,R2,@{et}")
            else:
                self.expr(s[2], "e")
                self.emettre("PUSH R1")
                self.expr(et, "e")
                self.emettre("PUSH R1")
                self.expr(s[3])
                self.emettre("POP R2")
                self.emettre("POP R3")
                self.emettre("STX R3,R1,R2")
        elif g == "si":
            sinon, fin = self.nouvelle("Lsinon"), self.nouvelle("Lfin")
            self.saut_faux(s[1], sinon)
            for x in s[2]:
                self.instr(x)
            if s[3] is not None:
                self.emettre(f"JMP {fin}")
            self.etiquette(sinon)
            if s[3] is not None:
                for x in s[3]:
                    self.instr(x)
                self.etiquette(fin)
        elif g == "tantque":
            haut, fin = self.nouvelle("Lhaut"), self.nouvelle("Lfin")
            self.etiquette(haut)
            self.saut_faux(s[1], fin)
            self.boucles.append((haut, fin))
            for x in s[2]:
                self.instr(x)
            self.boucles.pop()
            self.emettre(f"JMP {haut}")
            self.etiquette(fin)
        elif g == "pour":
            off = self.variable(s[1], s[5])
            reg = self.regs.get(s[1])
            haut, suite, fin = self.nouvelle("Lhaut"), self.nouvelle("Lsuite"), self.nouvelle("Lfin")
            self.expr(s[2], "e")
            self.emettre(f"MOV R{reg},R1" if reg else f"STF R1,#{off}")
            self.etiquette(haut)
            self.marque(s)
            self.saut_faux(("bin", "<", ("var", s[1], s[5]), s[3]), fin)
            self.boucles.append((suite, fin))
            for x in s[4]:
                self.instr(x)
            self.boucles.pop()
            self.etiquette(suite)
            pas = s[6] if len(s) > 6 else 1
            if reg:
                # la variable de boucle en registre : un seul pas
                if pas <= 255:
                    self.emettre(f"ADDI R{reg},R{reg},#{pas}")
                else:
                    self.emettre(f"LDI R2,{pas}")
                    self.emettre(f"ADD R{reg},R{reg},R2")
            else:
                self.emettre(f"LDF R1,#{off}")
                if pas <= 255:
                    self.emettre(f"ADDI R1,R1,#{pas}")
                else:
                    self.emettre(f"LDI R2,{pas}")
                    self.emettre("ADD R1,R1,R2")
                self.emettre(f"STF R1,#{off}")
            self.emettre(f"JMP {haut}")
            self.etiquette(fin)
        elif g == "asm":
            self.sortie.extend(s[1])
        elif g == "bloc":
            for x in s[1]:
                self.instr(x)
        elif g == "segments":
            pre, _ = deplier_segments(s)
            for x in pre:
                self.instr(x)
            self.instr(("pour", s[1], ("var", f"__sa{s[7]}", s[5]), ("var", f"__sb{s[7]}", s[5]), s[4], s[5], 1))
        elif g == "accord":
            for k, mesure in enumerate(s[2], 1):
                for st, note, nom in mesure:
                    self.emettre(f".tache {s[1]} {k} {nom} {note}")
                    self.instr(st)
            self.emettre(f".accord_fin {s[1]}")
        elif g in ("arreter", "continuer"):
            if not self.boucles:
                raise VtxError(f"ligne {s[1]} : « {'arrêter' if g == 'arreter' else 'continuer'} » hors d'une boucle")
            self.emettre(f"JMP {self.boucles[-1][1 if g == 'arreter' else 0]}")
        elif g == "retour":
            if s[1] is None:
                self.emettre("ADDI R1,R0,#0")
                if self.f.rtype in LARGES2:
                    for r in REGS_T[self.f.rtype][1:]:
                        self.emettre(f"ADDI {r},R0,#0")
            else:
                self.expr(s[1], self.f.rtype)
            self.emettre(f"JMP {self.fin}")
        else:
            self.expr(s[1])

    # ---------------------------------------------------------------- expressions
    def deux(self, a, b):
        """Évalue a dans R1 et b dans R2 (entiers) ; évite la pile quand b est une feuille."""
        self.paire(a, b, "e")

    def reg_var(self, e):
        """Le registre d'une variable entière qui vit en registre (« R9 »…), sinon None."""
        if self.optim and e[0] == "var" and e[1] in self.regs and self.vtypes.get(e[1]) == "e":
            return f"R{self.regs[e[1]]}"
        return None

    def deux_ops(self, a, b):
        """Les deux opérandes entiers d'une opération : un opérande en registre est lu sur place (aucune copie) ;
        rend les registres à utiliser (gauche, droite)."""
        ra, rb = self.reg_var(a), self.reg_var(b)
        if ra and rb:
            return ra, rb
        if ra:
            if self.optim and b[0] == "blit":
                self.charger("R2", b[2])
            elif self.optim and b[0] in ("nombre", "qnombre"):
                self.charger("R2", b[1])
            elif self.optim and b[0] == "var" and self.vtypes.get(b[1]) == "e":
                self.emettre(f"LDF R2,#{self.variable(b[1], b[2])}")
            else:
                self.expr(b, "e")
                self.emettre("MOV R2,R1")
            return ra, "R2"
        if rb:
            self.expr(a, "e")
            return "R1", rb
        self.deux(a, b)
        return "R1", "R2"

    @staticmethod
    def regs_comp(regs, ra, rb):
        return ",".join(ra if r == "R1" else rb for r in regs.split(","))

    def paire(self, a, b, t):
        """Évalue a et b convertis au type t : R1 et R2 (entier, flottant) ou R1:R4 et R2:R5 (long, mot bas d'abord)."""
        self.expr(a, t)
        if t in LARGES2:
            for r in REGS_T[t]:
                self.emettre(f"PUSH {r}")
            self.expr(b, t)
            for rb, ra in zip(REGS_B[t], REGS_T[t]):
                self.emettre(f"MOV {rb},{ra}")
            for r in reversed(REGS_T[t]):
                self.emettre(f"POP {r}")
            return
        if self.optim and b[0] == "blit" and t in ("e", "q"):
            self.charger("R2", b[2] if t == "e" else b[1])
        elif self.optim and b[0] in ("nombre", "qnombre") and t in ("e", "q"):
            self.charger("R2", b[1])
        elif self.optim and b[0] == "fnombre" and t == "f":
            self.charger("R2", b[1])
        elif self.optim and b[0] == "var" and self.vtypes.get(b[1]) == t:
            off = self.variable(b[1], b[2])
            self.emettre(f"MOV R2,R{self.regs[b[1]]}" if b[1] in self.regs else f"LDF R2,#{off}")
        else:
            self.emettre("PUSH R1")
            self.expr(b, t)
            self.emettre("MOV R2,R1")
            self.emettre("POP R1")

    def booleen(self, saut):
        """Écrit 1 dans R1 si le saut conditionnel `saut` (déjà émis vers l'étiquette rendue) est pris, sinon 0."""
        vrai, fin = self.nouvelle("Lvrai"), self.nouvelle("Lfin")
        saut(vrai)
        self.emettre("ADDI R1,R0,#0")
        self.emettre(f"JMP {fin}")
        self.etiquette(vrai)
        self.emettre("ADDI R1,R0,#1")
        self.etiquette(fin)

    def saut_long(self, op, vrai, g=("R1", "R4"), d=("R2", "R5")):
        """Saute à vrai si (g op d) sur des longs signés ; registres de travail R6, R7, R8."""
        if op in ("==", "!="):
            self.emettre(f"XOR R6,{g[0]},{d[0]}")
            self.emettre(f"XOR R7,{g[1]},{d[1]}")
            self.emettre("OR R6,R6,R7")
            self.emettre("CMP R6,R0")
            self.emettre(f"{'JZ' if op == '==' else 'JNZ'} {vrai}")
            return
        if op in (">", ">="):
            g, d, op = d, g, {">": "<", ">=": "<="}[op]
        faux = self.nouvelle("Lfaux")
        self.emettre("LDI R8,2147483648")
        self.emettre(f"XOR R6,{g[1]},R8")
        self.emettre(f"XOR R7,{d[1]},R8")
        self.emettre("CMP R6,R7")
        self.emettre(f"JC {vrai}")
        self.emettre("CMP R7,R6")
        self.emettre(f"JC {faux}")
        if op == "<":
            self.emettre(f"CMP {g[0]},{d[0]}")
            self.emettre(f"JC {vrai}")
        else:
            self.emettre(f"CMP {d[0]},{g[0]}")
            self.emettre(f"JNC {vrai}")
        self.etiquette(faux)

    def expr(self, e, voulu=None):
        """Émet e ; rend son type. Avec voulu, convertit le résultat (entier vers flottant ou long)."""
        if e[0] == "blit":
            e = ("qnombre", e[1]) if voulu == "q" else ("nombre", e[2])
        if est_ref(voulu) and e == ("nombre", 0):
            self.emettre("ADDI R1,R0,#0")            # nul
            return voulu
        t = self.typ(e)
        if est_ref(t):
            if e[0] == "nouveau_de":
                self.expr_e(e[2])
            elif e[0] == "construire":
                self.expr_e(e[3])                       # adresse du bloc neuf, gardée sur la pile
                self.emettre("PUSH R1")
                for champ, val in e[2]:
                    pos = self.structs[e[1]].index(champ)
                    tc = self.types_champs.get(e[1], {}).get(champ, "e")
                    if tc in LARGES2:
                        raise VtxError(f"ligne {e[4]} : un champ ne peut pas contenir un {NOM_TYPE[tc]}")
                    self.expr(val, tc)
                    self.emettre("MOV R7,R1")
                    self.emettre("POP R1")
                    self.emettre("PUSH R1")
                    self.emettre("MOV R2,R1")
                    self.emettre("ADDI R6,R0,#24")
                    self.emettre("SHR R2,R2,R6")
                    if pos:
                        self.emettre(f"ADDI R1,R1,#{pos}")
                    self.emettre("STX R1,R7,R2")
                self.emettre("POP R1")
            elif e[0] in ("champ_ref", "champ"):
                _st, pos, _t = self.champ_de(e)
                self.adresse_champ(e[1], pos)
                self.emettre("LDX R1,R1,R2")
            else:
                self.expr_e(e)
            if voulu is not None and voulu != t:
                self.conv(t, voulu, ligne_de(e))
            return t
        if voulu == "x" and t in ("e", "f", "d"):
            self.conversion("flottant_petuar", [e], ligne_de(e))      # élargi en flottant_petuar par le prélude
            return "x"
        if t == "e":
            self.expr_e(e)
        elif t == "f":
            self.expr_f(e)
        elif t == "q":
            if e[0] == "qnombre":
                self.charger("R1", e[1])
            else:
                self.expr_e(e)
        elif t == "d":
            self.expr_d(e)
        elif t == "w":
            self.expr_w(e)
        elif t == "x":
            self.expr_x(e)
        else:
            self.expr_l(e)
        if voulu is not None and voulu != t:
            self.conv(t, voulu, ligne_de(e))
            return voulu
        return t

    def expr_e(self, e):
        g = e[0]
        q = motif_quit(e) if self.optim and g == "bin" and e[1] == "&" else None
        if q:
            # LDQ : le quit i d'un tableau rangé, en une instruction
            et, base, idx = q
            self.expr(idx, "e")
            if base:
                self.charger("R2", base)
            self.emettre(f"LDQ R1,{'R2' if base else 'R0'},R1,@{et}")
            return
        if g == "nombre":
            self.charger("R1", e[1])
        elif g == "var":
            off = self.variable(e[1], e[2])
            self.emettre(f"MOV R1,R{self.regs[e[1]]}" if e[1] in self.regs else f"LDF R1,#{off}")
        elif g == "etiq":
            self.emettre(f"LDI R1,{e[1]}")
        elif g == "non":
            self.expr(e[1])
            self.emettre("CMP3 R1,R1")
        elif g == "non_log":
            vrai, fin = self.nouvelle("Lvrai"), self.nouvelle("Lfin")
            self.expr_bool(e[1])
            self.emettre("CMP R1,R0")
            self.emettre(f"JZ {vrai}")
            self.emettre("ADDI R1,R0,#0")
            self.emettre(f"JMP {fin}")
            self.etiquette(vrai)
            self.emettre("ADDI R1,R0,#1")
            self.etiquette(fin)
        elif g == "bin":
            op = e[1]
            if op == "&&":
                faux, fin = self.nouvelle("Lfaux"), self.nouvelle("Lfin")
                self.saut_faux(e[2], faux)
                self.saut_faux(e[3], faux)
                self.emettre("ADDI R1,R0,#1")
                self.emettre(f"JMP {fin}")
                self.etiquette(faux)
                self.emettre("ADDI R1,R0,#0")
                self.etiquette(fin)
                return
            if op == "||":
                lb, lt, faux, fin = (self.nouvelle("Lou"), self.nouvelle("Lvrai"),
                                     self.nouvelle("Lfaux"), self.nouvelle("Lfin"))
                self.saut_faux(e[2], lb)
                self.emettre(f"JMP {lt}")
                self.etiquette(lb)
                self.saut_faux(e[3], faux)
                self.etiquette(lt)
                self.emettre("ADDI R1,R0,#1")
                self.emettre(f"JMP {fin}")
                self.etiquette(faux)
                self.emettre("ADDI R1,R0,#0")
                self.etiquette(fin)
                return
            if op in COMPARAISONS:
                ta_, tb_ = self.typ(e[2]), self.typ(e[3])
                if "q" in (ta_, tb_) or est_ref(ta_) or est_ref(tb_):
                    self.paire(e[2], e[3], "q" if "q" in (ta_, tb_) else (ta_ if est_ref(ta_) else tb_))
                    regs, saut = COMPARAISONS[op]
                    vrai, fin = self.nouvelle("Lvrai"), self.nouvelle("Lfin")
                    self.emettre(f"CMP {regs}")
                    self.emettre(f"{saut} {vrai}")
                    self.emettre("ADDI R1,R0,#0")
                    self.emettre(f"JMP {fin}")
                    self.etiquette(vrai)
                    self.emettre("ADDI R1,R0,#1")
                    self.etiquette(fin)
                    return
                t = self.joindre(self.typ(e[2]), self.typ(e[3]), ligne_de(e), op)
                if t == "x":
                    nom = {"==": "__pq_eq", "!=": "__pq_ne", "<": "__pq_lt", "<=": "__pq_le", ">": "__pq_gt", ">=": "__pq_ge"}[op]
                    self.appel(("appel", nom, [self.bits_x(e[2]), self.bits_x(e[3])], ligne_de(e)))
                    return
                if t == "f":
                    self.paire(e[2], e[3], "f")
                    instr = {"==": "FEQ R1,R1,R2", "!=": "FEQ R1,R1,R2", "<": "FLT R1,R1,R2", "<=": "FLE R1,R1,R2",
                             ">": "FLT R1,R2,R1", ">=": "FLE R1,R2,R1"}[op]
                    self.emettre(instr)
                    if op == "!=":
                        self.emettre("ADDI R2,R0,#1")
                        self.emettre("XOR R1,R1,R2")
                    return
                if t == "l":
                    self.paire(e[2], e[3], "l")
                    self.booleen(lambda vrai: self.saut_long(op, vrai))
                    return
                if t == "w":
                    if op in ("==", "!="):
                        self.paire(e[2], e[3], "w")
                        for ra, rb in zip(REGS_T["w"], REGS_B["w"]):
                            self.emettre(f"XOR {ra},{ra},{rb}")
                        self.emettre("OR R1,R1,R3")
                        self.emettre("OR R4,R4,R6")
                        self.emettre("OR R1,R1,R4")
                        vrai, fin = self.nouvelle("Lvrai"), self.nouvelle("Lfin")
                        self.emettre("CMP R1,R0")
                        self.emettre(f"{'JZ' if op == '==' else 'JNZ'} {vrai}")
                        self.emettre("ADDI R1,R0,#0")
                        self.emettre(f"JMP {fin}")
                        self.etiquette(vrai)
                        self.emettre("ADDI R1,R0,#1")
                        self.etiquette(fin)
                        return
                    a_, b_ = (e[2], e[3]) if op in ("<", ">=") else (e[3], e[2])
                    self.appel(("appel", "__qlt", [a_, b_], ligne_de(e)))      # a < b ; a >= b : l'inverse
                    if op in ("<=", ">="):
                        self.emettre("ADDI R2,R0,#1")
                        self.emettre("XOR R1,R1,R2")
                    return
                if t == "d":
                    self.paire(e[2], e[3], "d")
                    instr = {"==": "DEQ R1,R1,R2", "!=": "DEQ R1,R1,R2", "<": "DLT R1,R1,R2", "<=": "DLE R1,R1,R2",
                             ">": "DLT R1,R2,R1", ">=": "DLE R1,R2,R1"}[op]
                    self.emettre(instr)
                    if op == "!=":
                        self.emettre("ADDI R2,R0,#1")
                        self.emettre("XOR R1,R1,R2")
                    return
            if op in ("<<q", ">>q"):
                self.deux(e[2], e[3])
                self.emettre("ADD R2,R2,R2")
                self.emettre(f"{'SHL' if op == '<<q' else 'SHR'} R1,R1,R2")
                return
            ra, rb = self.deux_ops(e[2], e[3])
            if op in BINAIRES:
                self.emettre(f"{BINAIRES[op]} R1,{ra},{rb}")
            else:
                regs, saut = COMPARAISONS[op]
                vrai, fin = self.nouvelle("Lvrai"), self.nouvelle("Lfin")
                self.emettre(f"CMP {self.regs_comp(regs, ra, rb)}")
                self.emettre(f"{saut} {vrai}")
                self.emettre("ADDI R1,R0,#0")
                self.emettre(f"JMP {fin}")
                self.etiquette(vrai)
                self.emettre("ADDI R1,R0,#1")
                self.etiquette(fin)
        elif g == "champ_ref" or (g == "champ" and est_ref(self.typ(e[1]))):
            _st, pos, _t = self.champ_de(e)
            self.adresse_champ(e[1], pos)
            self.emettre("LDX R1,R1,R2")
        elif g == "champ":
            self.expr(e[1])
            if CHAMPS[e[2]]:
                self.emettre(f"ADDI R2,R0,#{CHAMPS[e[2]]}")
                self.emettre("SHR R1,R1,R2")
            self.emettre("ADDI R2,R0,#255")
            self.emettre("AND R1,R1,R2")
        elif g == "quit":
            self.expr(e[1])
            self.emettre("PUSH R1")
            self.expr(e[2], "e")
            self.emettre("MOV R2,R1")
            self.emettre("POP R1")
            self.emettre("EXQ R1,R1,R2")
        elif g == "lire":
            if isinstance(e[1], int):
                self.expr(e[2], "e")
                self.emettre(f"LD R1,R1,@{e[1]}")
            else:
                self.expr(e[2], "e")
                self.emettre("PUSH R1")
                self.expr(e[1], "e")
                self.emettre("MOV R2,R1")
                self.emettre("POP R1")
                self.emettre("LDX R1,R1,R2")
        elif g == "appel":
            self.appel(e)

    def expr_f(self, e):
        g = e[0]
        if g == "fnombre":
            self.charger("R1", e[1])
        elif g == "var":
            off = self.variable(e[1], e[2])
            self.emettre(f"MOV R1,R{self.regs[e[1]]}" if e[1] in self.regs else f"LDF R1,#{off}")
        elif g == "bin":
            op = e[1]
            if op == "-" and e[2] in (("nombre", 0), ("fnombre", 0)):
                self.expr(e[3], "f")
                self.emettre("LDI R2,2147483648")
                self.emettre("XOR R1,R1,R2")
                return
            self.paire(e[2], e[3], "f")
            self.emettre(f"{FBINAIRES[op]} R1,R1,R2")
        elif g == "appel":
            self.appel(e)
        elif g in ("champ_ref", "champ"):              # champ flottant d'une structure
            self.expr_e(e)
        else:
            raise VtxError(f"ligne {ligne_de(e)} : expression flottante inattendue")

    def expr_d(self, e):
        """Flottant de 64 bits : mot bas dans R1, mot haut dans R4 (la paire de registres des instructions D)."""
        g = e[0]
        if g == "dnombre":
            self.charger("R1", e[1] & MASK)
            self.charger("R4", e[1] >> 32)
        elif g == "var":
            self.emettre(f"LDF R1,#{self.variable(e[1], e[2])}")
            self.emettre(f"LDF R4,#{self.vhaut[e[1]]}")
        elif g == "bin":
            op = e[1]
            if op == "-" and e[2] in (("nombre", 0), ("fnombre", 0), ("dnombre", 0)):
                self.expr(e[3], "d")
                self.emettre("LDI R2,2147483648")
                self.emettre("XOR R4,R4,R2")
                return
            self.paire(e[2], e[3], "d")
            self.emettre(f"{DBINAIRES[op]} R1,R1,R2")
        elif g == "appel":
            self.appel(e)
        else:
            raise VtxError(f"ligne {ligne_de(e)} : expression flottante_64 inattendue")

    def expr_w(self, e):
        """Entier de 128 bits : quatre mots dans R1, R3, R4, R6 (le mot bas d'abord) ; deuxième opérande dans R2, R5, R7, R8."""
        g = e[0]
        if g == "wnombre":
            for k, r in enumerate(REGS_T["w"]):
                self.charger(r, (e[1] >> (32 * k)) & MASK)
        elif g == "var":
            off = self.variable(e[1], e[2])
            for k, r in enumerate(REGS_T["w"]):
                self.emettre(f"LDF {r},#{off - k}")
        elif g == "non":
            self.expr(e[1], "w")
            for r in REGS_T["w"]:
                self.emettre(f"CMP3 {r},{r}")
        elif g == "bin":
            op, l = e[1], ligne_de(e)
            if op in ("*", "/", "%"):
                if op == "*":
                    self.appel(("appel", "__qmul", [e[2], e[3]], l))
                else:
                    self.appel(("appel", "__qdiv", [e[2], e[3], ("nombre", 1 if op == "%" else 0)], l))
                return
            if op in ("<<", ">>"):
                self.appel(("appel", "__qshl" if op == "<<" else "__qsar", [e[2], e[3]], l))
                return
            self.paire(e[2], e[3], "w")
            if op in ("+", "-"):
                for k, (ra, rb) in enumerate(zip(REGS_T["w"], REGS_B["w"])):
                    self.emettre(f"{('ADD' if op == '+' else 'SUB') if k == 0 else ('ADC' if op == '+' else 'SBC')} {ra},{ra},{rb}")
            elif op in BITS_OPS:
                for ra, rb in zip(REGS_T["w"], REGS_B["w"]):
                    self.emettre(f"{BINAIRES[op]} {ra},{ra},{rb}")
            else:
                raise VtxError(f"ligne {l} : « {op} » ne s'applique pas à un entier_128")
        elif g == "appel":
            self.appel(e)
        else:
            raise VtxError(f"ligne {ligne_de(e)} : expression entier_128 inattendue")

    def bits_x(self, a):
        """Les quatre points d'un flottant_petuar (élargi d'abord s'il le faut), vus comme un entier_petuar."""
        l = ligne_de(a)
        if self.typ(a) != "x":
            a = ("appel", "flottant_petuar", [a], l)
        return ("appel", "bits", [a], l)

    def expr_x(self, e):
        """flottant_petuar : quatre points du cube dans R1, R3, R4, R6 (le point bas d'abord) ; le calcul par le prélude."""
        g = e[0]
        if g == "xnombre":
            for k, r in enumerate(REGS_T["x"]):
                self.charger(r, (e[1] >> (32 * k)) & MASK)
        elif g == "var":
            off = self.variable(e[1], e[2])
            for k, r in enumerate(REGS_T["x"]):
                self.emettre(f"LDF {r},#{off - k}")
        elif g == "bin":
            op, l = e[1], ligne_de(e)
            if op == "-" and e[2] in (("nombre", 0), ("fnombre", 0), ("dnombre", 0)):
                self.appel(("appel", "__pq_neg", [self.bits_x(e[3])], l))
                return
            if op not in ("+", "-", "*", "/"):
                raise VtxError(f"ligne {l} : « {op} » ne s'applique pas à un flottant_petuar")
            nom = {"+": "__pq_add", "-": "__pq_sub", "*": "__pq_mul", "/": "__pq_div"}[op]
            self.appel(("appel", nom, [self.bits_x(e[2]), self.bits_x(e[3])], l))
        elif g == "appel":
            self.appel(e)
        else:
            raise VtxError(f"ligne {ligne_de(e)} : expression flottant_petuar inattendue")

    def expr_l(self, e):
        g = e[0]
        if g == "lnombre":
            self.charger("R1", e[1] & MASK)
            self.charger("R4", e[1] >> 32)
        elif g == "var":
            self.emettre(f"LDF R1,#{self.variable(e[1], e[2])}")
            self.emettre(f"LDF R4,#{self.vhaut[e[1]]}")
        elif g == "non":
            self.expr(e[1], "l")
            self.emettre("CMP3 R1,R1")
            self.emettre("CMP3 R4,R4")
        elif g == "bin":
            op, l = e[1], ligne_de(e)
            if op in ("/", "%"):
                self.appel(("appel", "__ldiv", [e[2], e[3], ("nombre", 1 if op == "%" else 0)], l))
                return
            if op in ("<<", ">>"):
                self.appel(("appel", "__lshl" if op == "<<" else "__lsar", [e[2], e[3]], l))
                return
            self.paire(e[2], e[3], "l")
            if op == "+":
                self.emettre("ADD R1,R1,R2")
                self.emettre("ADC R4,R4,R5")
            elif op == "-":
                self.emettre("SUB R1,R1,R2")
                self.emettre("SBC R4,R4,R5")
            elif op == "*":
                self.emettre("MUL R6,R1,R2")
                self.emettre("MULHU R7,R1,R2")
                self.emettre("MUL R8,R1,R5")
                self.emettre("ADD R7,R7,R8")
                self.emettre("MUL R8,R4,R2")
                self.emettre("ADD R7,R7,R8")
                self.emettre("MOV R1,R6")
                self.emettre("MOV R4,R7")
            elif op in BITS_OPS:
                self.emettre(f"{BINAIRES[op]} R1,R1,R2")
                self.emettre(f"{BINAIRES[op]} R4,R4,R5")
            else:
                raise VtxError(f"ligne {l} : « {op} » ne s'applique pas à un long")
        elif g == "appel":
            self.appel(e)
        else:
            raise VtxError(f"ligne {ligne_de(e)} : expression longue inattendue")

    def logique(self, nom, args, ligne):
        """Opérations de la logique à quatre valeurs : de simples ET / OU sur les deux bits de chaque quit, donc la même
        instruction traite un logique ou 16 logiques rangés dans un entier."""
        t = self.typ(("appel", nom, args, ligne))
        if nom in ("logique", "comme_logique"):
            if len(args) != 1:
                raise VtxError(f"ligne {ligne} : « {nom} » attend 1 argument")
            ta = "q" if args[0][0] == "blit" else self.typ(args[0])
            if ta == "q":
                self.expr(args[0], "q")
                return
            if ta != "e":
                raise VtxError(f"ligne {ligne} : « {nom} » prend un entier")
            self.expr(args[0])
            if nom == "comme_logique":           # le code 0 à 3 lu comme un logique
                self.emettre("ADDI R2,R0,#3")
                self.emettre("AND R1,R1,R2")
            else:                                # 0 -> faux, autre -> vrai
                lz, lf = self.nouvelle("Llog"), self.nouvelle("Llogf")
                self.emettre("CMP R1,R0")
                self.emettre(f"JZ {lz}")
                self.emettre("ADDI R1,R0,#2")
                self.emettre(f"JMP {lf}")
                self.emettre(f"{lz}:")
                self.emettre("ADDI R1,R0,#1")
                self.emettre(f"{lf}:")
            return
        if OPS_LOGIQUES[nom] == 2:
            self.paire(args[0], args[1], t)
        else:
            self.expr(args[0], t)
        if nom in ("et4", "ou4"):                # et4 : v = v1 & v2, f = f1 | f2 ; ou4 : l'inverse (16 quits d'un coup)
            self.emettre(f"{nom.upper()} R1,R1,R2")
        elif nom == "fusion":                    # rassembler les preuves : v = v1 | v2, f = f1 | f2
            self.emettre("OR R1,R1,R2")
        elif nom == "consensus":                 # garder les preuves communes
            self.emettre("AND R1,R1,R2")
        elif nom == "anti" and t != "q":         # anti : non puis complément (v = ~f, f = ~v), sur les 16 quits
            self.emettre("ANTI R1,R1")
        else:                                    # non : échange v et f ; anti d'un seul logique : non puis xor 3
            self.emettre("NON4 R1,R1")
            if nom == "anti":
                self.emettre("ADDI R2,R0,#3")
                self.emettre("XOR R1,R1,R2")

    def appel(self, e):
        nom, args, ligne = e[1], e[2], e[3]
        if nom == "__code_logique":
            ta = "q" if args[0][0] == "blit" else self.typ(args[0])
            if ta != "q":
                raise VtxError(f"ligne {ligne} : un tableau de logique reçoit des logiques (vrai, faux, inconnu, variable), "
                               f"pas un {NOM_TYPE[ta]} : utilisez logique() ou comme_logique()")
            self.expr(args[0], "q")
            return
        if nom in OPS_LOGIQUES or nom in ("logique", "comme_logique"):
            self.logique(nom, args, ligne)
            return
        if nom in INTEGRES:
            if len(args) != INTEGRES[nom]:
                raise VtxError(f"ligne {ligne} : « {nom} » attend {INTEGRES[nom]} argument(s)")
            if nom == "sortie":
                t = self.expr(args[0])
                self.emettre("OUT R1")
                if t in LARGES2:
                    for r in REGS_T[t][1:]:
                        self.emettre(f"OUT {r}")
            elif nom == "entrée":
                self.emettre("IN R1")
            elif nom == "cmp3":
                self.expr(args[0], "e")
                self.emettre("CMP3 R1,R1")
            elif nom == "lire_car":
                self.expr(args[0], "e")
                self.emettre("ENTC R1,R1")
            elif nom == "ecrire_car":
                self.deux(args[1], args[0])
                self.emettre("SORC R0,R1,R2")
                self.emettre("ADDI R1,R0,#0")
            elif nom in ("ouvrir_lecture", "ouvrir_ecriture", "fermer", "fin_de"):
                self.expr(args[0], "e")
                self.emettre("MOV R2,R1")
                code = {"ouvrir_lecture": 1, "ouvrir_ecriture": 2, "fermer": 3, "fin_de": 4}[nom]
                self.emettre(f"ADDI R1,R0,#{code}")
                self.emettre("SYS R1,R1,R2")
            elif nom == "bruit":
                self.emettre("ADDI R1,R0,#5")
                self.emettre("SYS R1,R1,R0")
            elif nom == "pile":
                # le sommet de la pile (R14) : pour le ramasse-miettes, les variables vivantes sont au-dessus
                self.emettre("MOV R1,R14")
            elif nom == "__service":
                # un service de la machine hôte : SYS code, argument
                self.deux(args[0], args[1])
                self.emettre("SYS R1,R1,R2")
            elif nom == "nb_bits":
                self.expr(args[0], "e")
                self.emettre("COMPTE R1,R1")
            elif nom == "qegal":
                self.deux(args[0], args[1])
                self.emettre("QEGAL R1,R1,R2")
            elif nom == "gemv":
                for a in args:
                    self.expr(a, "e")
                    self.emettre("PUSH R1")
                self.emettre("GEMV")
                self.emettre("ADDI R14,R14,#5")
                self.emettre("ADDI R1,R0,#0")
            elif nom in ("min4", "max4", "addm4", "gdot"):
                self.deux(args[0], args[1])
                self.emettre(f"{ {'min4': 'MIN', 'max4': 'MAX', 'addm4': 'ADDM4', 'gdot': 'GDOT'}[nom] } R1,R1,R2")
            else:
                self.conversion(nom, args, ligne)
            return
        if nom in SURCHARGES and self.typ(e) == "w":
            self.appel(("appel", "__q" + nom, args, ligne))
            return
        if nom in SURCHARGES and self.typ(e) == "x":
            self.appel(("appel", "__pq_" + nom, [self.bits_x(a) for a in args], ligne))
            return
        if nom in SURCHARGES and self.typ(e) in ("f", "l", "d"):
            self.surcharge(nom, args, self.typ(e), ligne)
            return
        if nom in ("afficher", "ecrire", "texte") and len(args) == 1:
            # afficher(x), ecrire(x), texte(x) : la version du prélude qui convient au type de x (flottant, long,
            # logique ; les textes ont été reconnus avant, par typer_textes)
            pf = self.fonctions.get(nom) or self.reserve.get(nom)
            if pf is not None and getattr(pf, "origine", "") == "prélude":
                a0 = args[0]
                ta = "q" if a0[0] == "blit" else self.typ(a0)
                if ta in ("f", "l", "q", "d", "w", "x"):
                    nom = "__" + nom + "_" + ta
        f = self.signature(nom, ligne)
        if len(args) != len(f.params):
            raise VtxError(f"ligne {ligne} : « {nom} » attend {len(f.params)} argument(s)")
        mots = 0
        for a, t in zip(args, f.ptypes):
            self.expr(a, t)
            self.emettre("PUSH R1")
            mots += 1
            if t in LARGES2:
                for r in REGS_T[t][1:]:
                    self.emettre(f"PUSH {r}")
                    mots += 1
        self.emettre(f"CALL F_{nom}")
        if mots:
            self.emettre(f"ADDI R14,R14,#{mots}")

    def conversion(self, nom, args, ligne):
        x = args[0]
        t = self.typ(x)
        def interdit():
            raise VtxError(f"ligne {ligne} : « {nom} » ne s'applique pas à un {NOM_TYPE[t]}")
        if nom in ("flottant_petuar", "flottant_128"):
            if t == "x":
                self.expr(x)
            elif t in PQ_DEPUIS:
                if t == "f":
                    x = ("appel", "flottant_64", [x], ligne)
                self.appel(("appel", PQ_DEPUIS[t], [x], ligne))
            else:
                interdit()
            return
        if nom == "comme_flottant_petuar":
            if t != "w":
                interdit()
            self.expr(x)
            return
        if nom == "vers_ieee128":
            if t != "x":
                interdit()
            self.appel(("appel", "__pq_vers_ieee", [self.bits_x(x)], ligne))
            return
        if nom == "de_ieee128":
            if t != "w":
                interdit()
            self.appel(("appel", "__pq_de_ieee", [x], ligne))
            return
        if t == "x":
            # un flottant_petuar vers les autres types : par le prélude
            if nom == "bits":
                self.expr(x)
            elif nom == "racine":
                self.appel(("appel", "__pq_racine", [self.bits_x(x)], ligne))
            elif nom == "flottant_64":
                self.appel(("appel", "__pq_vers_d", [self.bits_x(x)], ligne))
            elif nom == "flottant":
                self.appel(("appel", "__pq_vers_f", [self.bits_x(x)], ligne))
            elif nom in ("entier_128", "long", "entier"):
                self.appel(("appel", "__pq_vers_w", [self.bits_x(x)], ligne))
                if nom == "long":
                    self.emettre("MOV R4,R3")
            else:
                interdit()
            return
        if nom == "flottant":
            if t == "l":
                interdit()
            self.expr(x)
            if t == "e":
                self.emettre("ITOF R1,R1")
            elif t == "d":
                self.emettre("DTOF R1,R1")
        elif nom == "flottant_signe":
            if t != "e":
                interdit()
            self.expr(x)
            self.emettre("ITOFS R1,R1")
        elif nom == "entier":
            self.expr(x)
            if t == "f":
                self.emettre("FTOI R1,R1")
            elif t == "d":
                self.emettre("DTOI R1,R1")
            # un logique donne son code : inconnu 0, faux 1, vrai 2, variable 3
        elif nom == "arrondi":
            if t not in ("f", "d"):
                interdit()
            self.expr(x)
            self.emettre("FROUND R1,R1" if t == "f" else "DROUND R1,R1")
        elif nom == "arrondi_long":
            if t != "d":
                interdit()
            self.expr(x)
            self.emettre("DTOLR R1,R1")
        elif nom == "racine":
            if t == "d":
                self.expr(x)
                self.emettre("DSQRT R1,R1")
            else:
                self.expr(x, "f")
                self.emettre("FSQRT R1,R1")
        elif nom in ("comme_flottant", "bits"):
            if t == "l" or (t == "d" and nom == "comme_flottant"):
                interdit()
            self.expr(x)             # bits(flottant_64) : les 64 bits, vus comme un long (même paire de registres)
        elif nom == "entier_128":
            if t not in ("e", "l", "w", "d"):
                interdit()
            if t == "d":
                self.appel(("appel", "__dtoq", [x], ligne))
                return
            self.expr(x)
            if t == "e":
                for r in ("R3", "R4", "R6"):
                    self.emettre(f"ADDI {r},R0,#0")
            elif t == "l":                       # d'un long : le signe se recopie sur les mots hauts
                self.emettre("MOV R3,R4")
                self.emettre("ADDI R2,R0,#31")
                self.emettre("SHR R4,R4,R2")
                self.emettre("SUB R4,R0,R4")
                self.emettre("MOV R6,R4")
        elif nom == "entier_128_signe":
            if t != "e":
                interdit()
            self.expr(x)
            self.emettre("ADDI R2,R0,#31")
            self.emettre("SHR R4,R1,R2")
            self.emettre("SUB R4,R0,R4")
            self.emettre("MOV R3,R4")
            self.emettre("MOV R6,R4")
        elif nom == "entier_128_de":
            if t != "l" or self.typ(args[1]) != "l":
                raise VtxError(f"ligne {ligne} : entier_128_de(haut, bas) prend deux longs")
            self.paire(args[0], args[1], "l")
            self.emettre("MOV R6,R4")
            self.emettre("MOV R3,R5")
            self.emettre("MOV R4,R1")
            self.emettre("MOV R1,R2")
        elif nom == "flottant_64" and t == "w":
            self.appel(("appel", "__qtod", [x], ligne))
        elif nom == "flottant_64":
            if t not in ("e", "f", "d", "l"):
                interdit()
            self.expr(x)
            if t != "d":
                self.emettre({"e": "ITOD R1,R1", "f": "FTOD R1,R1", "l": "LTOD R1,R1"}[t])
        elif nom == "flottant_64_signe":
            if t != "e":
                interdit()
            self.expr(x)
            self.emettre("ITODS R1,R1")
        elif nom == "flottant_64_de":
            if t != "e" or self.typ(args[1]) != "e":
                raise VtxError(f"ligne {ligne} : flottant_64_de(haut, bas) prend deux entiers")
            self.deux(args[0], args[1])
            self.emettre("MOV R4,R1")
            self.emettre("MOV R1,R2")
        elif nom == "comme_flottant_64":
            if t != "l":
                interdit()
            self.expr(x)
        elif nom == "long":
            if t == "f":
                interdit()
            if t == "d":
                self.expr(x)
                self.emettre("DTOL R1,R1")
            elif t == "w":
                self.expr(x)
                self.emettre("MOV R4,R3")
            else:
                self.expr(x, "l")
        elif nom == "long_signe":
            if t != "e":
                interdit()
            self.expr(x)
            self.emettre("ADDI R2,R0,#31")
            self.emettre("SHR R4,R1,R2")
            self.emettre("SUB R4,R0,R4")
        elif nom == "long_de":
            if t != "e" or self.typ(args[1]) != "e":
                raise VtxError(f"ligne {ligne} : long_de(haut, bas) prend deux entiers")
            self.deux(args[0], args[1])
            self.emettre("MOV R4,R1")
            self.emettre("MOV R1,R2")
        elif nom in ("bas", "haut") and t == "w":
            self.expr(x)
            if nom == "bas":
                self.emettre("MOV R4,R3")             # le long du bas : R1:R3 -> R1:R4
            else:
                self.emettre("MOV R1,R4")             # le long du haut : R4:R6 -> R1:R4
                self.emettre("MOV R4,R6")
        elif nom in ("bas", "haut"):
            if t not in LARGES2:
                interdit()
            self.expr(x)
            if nom == "haut":
                self.emettre("MOV R1,R4")

    def surcharge(self, nom, args, t, ligne):
        """abs, min et max pour les flottants et les longs, en ligne."""
        if nom == "abs":
            if len(args) != 1:
                raise VtxError(f"ligne {ligne} : « abs » attend 1 argument")
            self.expr(args[0], t)
            if t == "f":
                self.emettre("LDI R2,2147483647")
                self.emettre("AND R1,R1,R2")
            elif t == "d":
                self.emettre("LDI R2,2147483647")
                self.emettre("AND R4,R4,R2")
            else:
                fin = self.nouvelle("Lfin")
                self.emettre("LDI R8,2147483648")
                self.emettre("AND R6,R4,R8")
                self.emettre("CMP R6,R0")
                self.emettre(f"JZ {fin}")
                self.emettre("SUB R1,R0,R1")
                self.emettre("SBC R4,R0,R4")
                self.etiquette(fin)
            return
        if len(args) != 2:
            raise VtxError(f"ligne {ligne} : « {nom} » attend 2 arguments")
        self.paire(args[0], args[1], t)
        prendre, fin = self.nouvelle("Lprendre"), self.nouvelle("Lfin")
        if t == "f":
            self.emettre("FLT R3,R2,R1" if nom == "min" else "FLT R3,R1,R2")
            self.emettre("CMP R3,R0")
            self.emettre(f"JNZ {prendre}")
        elif t == "d":
            self.emettre("DLT R3,R2,R1" if nom == "min" else "DLT R3,R1,R2")
            self.emettre("CMP R3,R0")
            self.emettre(f"JNZ {prendre}")
        else:
            if nom == "min":
                self.saut_long("<", prendre, ("R2", "R5"), ("R1", "R4"))
            else:
                self.saut_long("<", prendre, ("R1", "R4"), ("R2", "R5"))
        self.emettre(f"JMP {fin}")
        self.etiquette(prendre)
        self.emettre("MOV R1,R2")
        if t in LARGES2:
            self.emettre("MOV R4,R5")
        self.etiquette(fin)


def appels(n, acc):
    if isinstance(n, tuple):
        if len(n) >= 3 and n[0] == "appel":
            acc.add(n[1])
        for x in n:
            appels(x, acc)
    elif isinstance(n, list):
        for x in n:
            appels(x, acc)


def elaguer(fs):
    par = {f.nom: f for f in fs}
    if "principal" not in par:
        return fs
    vus, pile = set(), ["principal"]
    while pile:
        n = pile.pop()
        if n in vus or n not in par:
            continue
        vus.add(n)
        acc = set()
        appels(par[n].corps, acc)
        pile.extend(acc)
    return [f for f in fs if f.nom in vus]


def injecter_donnees(fs, donnees):
    """Les données vont dans un segment après le code ; l'initialisation les copie (une boucle par bloc)."""
    lignes = []
    for i, (et, adr, vals) in enumerate(donnees):
        if vals:  # copie en assembleur : 6 instructions par donnée, comme avant, mais sans 3 mots de code par donnée
            lignes += [f"    LDI R1,DONNEES{i}", f"    LDI R2,{adr}", f"    LDI R3,{len(vals)}", f"    ADDI R4,R0,#{et}",
                       f"LCOPIE{i}:", "    LD R5,R1,@0", "    STX R2,R5,R4", "    ADDI R1,R1,#1",
                       "    ADDI R2,R2,#1", "    SUBI R3,R3,#1", f"    JNZ LCOPIE{i}"]
    corps = [("asm", lignes)]
    corps.append(("ecrire", 3, ("nombre", FLAG), ("nombre", 1), 0))
    cond = ("bin", "==", ("lire", 3, ("nombre", FLAG)), ("nombre", 0))
    for f in fs:
        if f.nom == "principal":
            f.corps = [("expr", ("appel", "__init", [], 0), 0)] + f.corps
    return fs + [Fonction("__init", [], [("si", cond, corps, None, 0)], 0)]


IMPORT = re.compile(r'^[ \t]*importer[ \t]+"([^"]+)"[ \t]*;[ \t]*$', re.M)


def chemin_import(m, dossier):
    """Le fichier d'une ligne « importer » : (chemin tel qu'écrit, chemin complet)."""
    if dossier is None:
        raise VtxError("« importer » exige un dossier de base")
    return m.group(1), os.path.normpath(os.path.join(dossier, m.group(1)))


def resoudre_imports(src, dossier, vus=None):
    """Remplace chaque ligne « importer "fichier.vtx"; » par le contenu du fichier (une seule fois par fichier)."""
    vus = set() if vus is None else vus

    def remplace(m):
        nom, chemin = chemin_import(m, dossier)
        if chemin in vus:
            return ""
        vus.add(chemin)
        try:
            texte = open(chemin, encoding="utf-8").read()
        except OSError:
            raise VtxError(f"importer : fichier introuvable « {nom} »")
        return resoudre_imports(texte, os.path.dirname(chemin), vus)

    return IMPORT.sub(remplace, src)


def resoudre_carte(src, dossier, nom="programme", vus=None, racine=None):
    """Comme resoudre_imports, ligne à ligne ; rend le texte assemblé et, pour chaque ligne, (fichier, ligne d'origine).
    Les fichiers importés sont nommés par leur chemin relatif au dossier du programme principal."""
    vus = set() if vus is None else vus
    racine = racine or dossier
    lignes, carte = [], []
    for i, l in enumerate(src.split("\n"), 1):
        m = IMPORT.match(l)
        if not m:
            lignes.append(l)
            carte.append((nom, i))
            continue
        nom_f, chemin = chemin_import(m, dossier)
        if chemin in vus:
            lignes.append("")
            carte.append((nom, i))
            continue
        vus.add(chemin)
        try:
            texte = open(chemin, encoding="utf-8").read()
        except OSError:
            raise VtxError(f"importer : fichier introuvable « {nom_f} »")
        sl, sc = resoudre_carte(texte, os.path.dirname(chemin), os.path.relpath(chemin, racine), vus, racine)
        lignes += sl
        carte += sc
    return lignes, carte


def compiler(src, prelude=True, optim=True, dossier=None, partition=True, melange=None):
    return compiler_complet(src, prelude, optim, dossier, partition=partition, melange=melange)[0]


def compiler_complet(src, prelude=True, optim=True, dossier=None, nom="programme", partition=True, melange=None):
    """Compile ; rend l'assembleur, la carte des lignes (fichier, ligne) et les lignes du texte assemblé."""
    if "importer" in src:
        lignes, carte = resoudre_carte(src, dossier, nom)
        src = "\n".join(lignes)
    else:
        lignes = src.split("\n")
        carte = [(nom, i) for i in range(1, len(lignes) + 1)]
    try:
        asm = _compiler(src, prelude, optim, partition, melange)
    except VtxError as e:
        m = re.match(r"ligne (\d+)", str(e))
        if m and 1 <= int(m.group(1)) <= len(carte) and carte[int(m.group(1)) - 1][0] != nom:
            f, l = carte[int(m.group(1)) - 1]
            raise VtxError(str(e).replace(f"ligne {m.group(1)}", f"{f}, ligne {l}", 1)) from None
        raise
    return asm, carte, lignes


DERNIERE_PARTITION = {"accords": [], "notes": {}}


# ---------------------------------------------------------------------------------------------------------------
# Le type texte. Un texte est l'adresse d'un bloc (longueur, puis un caractère par mot) : pour la machine, un entier.
# Avant l'élagage et la partition, une passe reconnaît les expressions de texte (littéral, variable ou paramètre
# déclaré texte ou initialisé par un texte, fonction qui rend un texte, champ déclaré texte, somme où entre un texte)
# et réécrit en appels du prélude : « a + b » devient __texte_plus(texte(a), texte(b)), « a == b » texte_egal(a, b),
# afficher et ecrire d'un texte leurs versions de texte, « afficher(a, b, c) » une suite d'écritures. Ensuite le type
# texte redevient « entier » : la génération du code ne le voit plus. La partition voit les appels : les tâches qui
# fabriquent des textes écrivent dans le tas, et ne sont pas jouées ensemble par erreur.

def typer_textes(fs, types_champs):
    rtexte = {f.nom for f in fs if f.rtype == "t"}
    du_prelude = {f.nom for f in fs if getattr(f, "origine", "") == "prélude"}
    champs = {}
    for _st, cs in types_champs.items():
        for c, t in cs.items():
            champs.setdefault(c, set()).add(t == "t")
    champs_texte = {c for c, v in champs.items() if v == {True}}

    TABLEAUX_DE_TEXTES = {"decouper", "cles"}
    TEXTES_RANGES = {"ajouter", "inserer", "ranger", "affirmer", "nier", "__remplir"}   # rangent leurs arguments
    tabtextes = set()
    tabflot = set()
    rtabflot = {f.nom for f in fs if f.rtype == "F"}

    def literal_flottant(e):
        # [a, b, c] avec au moins un flottant écrit en chiffres : un tableau de flottants
        while isinstance(e, tuple) and e and e[0] == "appel" and e[1] == "__remplir" and "__remplir" in du_prelude:
            if flottant_ecrit(e[2][2]):
                return True
            e = e[2][0]
        return False

    def tableau_flottant(h):
        if not isinstance(h, tuple) or not h:
            return False
        if h[0] == "var":
            return h[1] in tabflot
        if h[0] == "appel":
            if h[1] == "copie" and "copie" in du_prelude and len(h[2]) == 1:
                return tableau_flottant(h[2][0])
            return h[1] in rtabflot or literal_flottant(h)
        return False

    def poignee(e):
        # t[i] : (« lire », 3, (+, (« lire », 3, (+, (&, t, masque), 2)), i)) : rend t, sinon None
        if (isinstance(e, tuple) and len(e) == 3 and e[0] == "lire" and e[1] == 3 and e[2][0] == "bin" and e[2][1] == "+"
                and e[2][2][0] == "lire" and len(e[2][2]) == 3 and e[2][2][2][0] == "bin" and e[2][2][2][2][0] == "bin"
                and e[2][2][2][2][1] == "&"):
            return e[2][2][2][2][2]
        return None

    def adresse_poignee(a):
        # l'adresse de t[i] dans une écriture : (+, (« lire », 3, (+, (&, t, masque), 2)), i)
        if (isinstance(a, tuple) and a[0] == "bin" and a[1] == "+" and a[2][0] == "lire" and len(a[2]) == 3
                and a[2][2][0] == "bin" and a[2][2][2][0] == "bin" and a[2][2][2][1] == "&"):
            return a[2][2][2][2]
        return None

    def tableau_de_textes(h):
        return ((h[0] == "var" and h[1] in tabtextes)
                or (h[0] == "appel" and h[1] in TABLEAUX_DE_TEXTES and h[1] in du_prelude))

    def est_texte(e, env):
        if not isinstance(e, tuple) or not e:
            return False
        g = e[0]
        if poignee(e) is not None:
            # t[i] d'un tableau de textes (decouper, cles)
            return tableau_de_textes(poignee(e))
        if g == "etiq":
            return True
        if g == "var":
            return env.get(e[1], False)
        if g == "appel":
            return e[1] in rtexte
        if g in ("champ_ref", "champ") and len(e) >= 3 and isinstance(e[2], str):
            return e[2] in champs_texte
        if g == "bin" and e[1] == "+":
            return est_texte(e[2], env) or est_texte(e[3], env)
        return False

    def soits(x, acc):
        if isinstance(x, list):
            for y in x:
                soits(y, acc)
        elif isinstance(x, tuple) and x:
            if x[0] == "soit":
                acc.append(x)
            for y in x[1:]:
                if isinstance(y, (list, tuple)):
                    soits(y, acc)

    def vers_texte(e, env):
        return e if est_texte(e, env) else ("appel", "texte", [e], ligne_de(e))

    def rw(x, env):
        if (isinstance(x, tuple) and x and x[0] == "soit" and len(x) > 4 and x[4] == "F" and isinstance(x[2], tuple)
                and x[2][0] == "appel" and x[2][1] == "__remplir" and "__remplir" in du_prelude):
            x = x[:2] + (en_bits_litteral(x[2]),) + x[3:]
        if isinstance(x, tuple) and x and x[0] == "appel" and x[1] == "__remplir" and literal_flottant(x):
            # un littéral de flottants : chaque valeur rangée par ses bits (les entiers écrits deviennent des flottants)
            x = en_bits_litteral(x)
        if isinstance(x, list):
            r = []
            for y in x:
                y = rw(y, env)
                # afficher(a, b, c) : écrire a, une espace, b, une espace, puis afficher c (avec le retour à la ligne)
                if (isinstance(y, tuple) and y[0] == "expr" and y[1][0] == "appel" and y[1][1] == "afficher"
                        and len(y[1][2]) >= 2 and "afficher" in du_prelude):
                    args, l = y[1][2], y[1][3]
                    for a in args[:-1]:
                        r.append(("expr", ("appel", "__ecrire_t" if est_texte(a, env) else "ecrire", [a], l), y[2]))
                        r.append(("expr", ("appel", "ecrire_car", [("nombre", 1), ("nombre", 32)], l), y[2]))
                    der = args[-1]
                    r.append(("expr", ("appel", "__afficher_t" if est_texte(der, env) else "afficher", [der], l), y[2]))
                    continue
                r.append(y)
            return r
        if not isinstance(x, tuple) or not x:
            return x
        x = tuple(rw(y, env) if isinstance(y, (list, tuple)) else y for y in x)
        g = x[0]
        # les tableaux de flottants : lus comme flottants, écrits par leurs bits
        h = poignee(x)
        if h is not None and tableau_flottant(h):
            return ("appel", "comme_flottant", [x], ligne_de(x))
        if g == "ecrire" and x[1] == 3 and tableau_flottant(adresse_poignee(x[2])):
            return x[:3] + (en_bits(x[3]),) + x[4:]
        if g == "appel" and x[2] and tableau_flottant(x[2][0]) and x[1] in du_prelude:
            if x[1] in ("ajouter", "inserer", "indice", "contient") and len(x[2]) >= 2:
                return ("appel", x[1], x[2][:-1] + [en_bits(x[2][-1])], x[3])
            if x[1] in ("retirer", "enlever"):
                return ("appel", "comme_flottant", [x], x[3])
            if x[1] in ("somme", "trier") and len(x[2]) == 1:
                return ("appel", "__" + x[1] + "_f", x[2], x[3])
        if g == "bin" and x[1] == "+" and (est_texte(x[2], env) or est_texte(x[3], env)):
            return ("appel", "__texte_plus", [vers_texte(x[2], env), vers_texte(x[3], env)], ligne_de(x))
        if g == "bin" and x[1] in ("==", "!=") and est_texte(x[2], env) and est_texte(x[3], env):
            c = ("appel", "texte_egal", [x[2], x[3]], ligne_de(x))
            return c if x[1] == "==" else ("bin", "==", c, ("nombre", 0))
        if g == "appel" and len(x[2]) == 1 and est_texte(x[2][0], env):
            if x[1] in ("afficher", "ecrire") and x[1] in du_prelude:
                return ("appel", "__" + x[1] + "_t", x[2], x[3])
            if x[1] == "texte" and "texte" in du_prelude:
                return ("appel", "__texte_t", x[2], x[3])
        # un texte rangé dans le tas y est recopié s'il est écrit dans le programme (voir __texte_tas)
        tas = lambda v, l: ("appel", "__texte_tas", [v], l) if est_texte(v, env) and "__texte_tas" in du_prelude else v
        if g == "construire":
            return x[:2] + ([(ch, tas(v, x[4])) for ch, v in x[2]],) + x[3:]
        if g == "ecrire_champ":
            return x[:3] + (tas(x[3], x[4]),) + x[4:]
        if g == "ecrire" and x[1] == 3 and adresse_poignee(x[2]) is not None:
            return x[:3] + (tas(x[3], x[4]),) + x[4:]
        if g == "appel" and x[1] in TEXTES_RANGES and x[1] in du_prelude and len(x[2]) >= 2:
            return ("appel", x[1], [x[2][0]] + [tas(a, x[3]) for a in x[2][1:]], x[3])
        return x

    for f in fs:
        tabtextes.clear()
        tabflot.clear()
        tabflot.update(p for p, t in zip(f.params, f.ptypes) if t == "F")
        env = {p: t == "t" for p, t in zip(f.params, f.ptypes)}
        if getattr(f, "origine", "") != "prélude":
            liste = []
            soits(f.corps, liste)
            change = True
            while change:
                change = False
                for st in liste:
                    t = st[4] == "t" if len(st) > 4 and st[4] else est_texte(st[2], env)
                    if t and not env.get(st[1]):
                        env[st[1]] = True
                        change = True
                    if st[1] not in tabtextes and tableau_de_textes(st[2]):
                        tabtextes.add(st[1])
                        change = True
                    if st[1] not in tabflot and ((len(st) > 4 and st[4] == "F") or tableau_flottant(st[2])):
                        tabflot.add(st[1])
                        change = True
            f.corps = rw(f.corps, env)
        # pour la génération du code, un texte (et la poignée d'un tableau de flottants) est un entier
        f.ptypes = ["e" if t in ("t", "F") else t for t in f.ptypes]
        if f.rtype in ("t", "F"):
            f.rtype = "e"
        f.corps = sans_type_texte(f.corps)
    for cs in types_champs.values():
        for c in cs:
            if cs[c] == "t":
                cs[c] = "e"


def bits_flottant(n):
    """Les bits du flottant de 32 bits le plus proche de l'entier n (exact pour |n| < 2^24)."""
    return struct.unpack("<I", struct.pack("<f", float(n)))[0]


def en_bits(v):
    """Une valeur rangée dans un tableau de flottants : ses bits ; un nombre écrit est converti dès la compilation."""
    if v[0] == "fnombre":
        return ("nombre", v[1])
    if v[0] == "bin" and v[1] == "-" and v[2] == ("nombre", 0) and v[3][0] == "fnombre":
        return ("nombre", v[3][1] ^ 2147483648)
    if v[0] == "nombre" and v[1] < 16777216:
        return ("nombre", bits_flottant(v[1]))
    if v[0] == "bin" and v[1] == "-" and v[2] == ("nombre", 0) and v[3][0] == "nombre" and v[3][1] < 16777216:
        return ("nombre", bits_flottant(-v[3][1]))
    l = ligne_de(v)
    return ("appel", "bits", [("appel", "flottant", [v], l)], l)


def en_bits_litteral(x):
    if isinstance(x, tuple) and x and x[0] == "appel" and x[1] == "__remplir":
        return ("appel", "__remplir", [en_bits_litteral(x[2][0]), x[2][1], en_bits(x[2][2])], x[3])
    return x


def flottant_ecrit(v):
    return v[0] == "fnombre" or (v[0] == "bin" and v[1] == "-" and v[2] == ("nombre", 0) and v[3][0] == "fnombre")


def sans_type_texte(x):
    if isinstance(x, list):
        return [sans_type_texte(y) for y in x]
    if isinstance(x, tuple) and x:
        if x[0] == "soit" and len(x) > 4 and x[4] in ("t", "F"):
            x = x[:4] + ("e",) + x[5:]
        return tuple(sans_type_texte(y) if isinstance(y, (list, tuple)) else y for y in x)
    return x


def _compiler(src, prelude=True, optim=True, partition=True, melange=None):
    a = Analyseur(lexer(src))
    fs = a.programme()
    if a.donnees:
        fs = injecter_donnees(fs, a.donnees)
    if prelude:
        noms = {f.nom for f in fs}
        # le prélude continue la numérotation des textes du programme (un texte écrit dans le prélude a sa propre
        # étiquette, et pas celle d'un texte du programme)
        ap = Analyseur(lexer(PRELUDE))
        ap.textes = a.textes
        pre = [f for f in ap.programme() if f.nom not in noms]
        for f in pre:
            f.origine = "prélude"
        fs = fs + pre
    typer_textes(fs, a.types_champs)
    gardees = elaguer(fs) if optim else fs
    reserve = {f.nom: f for f in fs if f not in gardees}
    DERNIERE_PARTITION["accords"], DERNIERE_PARTITION["notes"] = [], {}
    if optim and partition:
        DERNIERE_PARTITION["accords"], DERNIERE_PARTITION["notes"] = partitionner(gardees, melange)
    g = Generateur(gardees, optim, a.donnees, reserve)
    g.structs, g.types_champs, g.textes = a.structs, a.types_champs, a.textes
    return g.generer()


# ---------------------------------------------------------------------------------------------------------------
# Partition automatique des tâches. Une suite d'au moins deux appels de fonctions écrits comme instructions forme un
# accord ; le compilateur calcule ce que chaque appel lit et écrit (zones mémoire, entrées et sorties), range dans une
# même mesure les tâches sans conflit et donne à chaque fonction une note (sa fréquence signature). L'ordre d'exécution
# devient celui de la partition : mesure après mesure. Rien n'est à écrire dans le programme.

TOUT = (None, 0, 1 << 24)          # zone inconnue : tous les étages
COPIES_DEBUT, COPIES_FIN = 0xE00000, 0xF00000   # étage 3 : copies des tableaux cumulés par les segments
ZONE_COPIES = (3, COPIES_DEBUT, COPIES_FIN)
ES = ("es", 0, 1)                   # entrées et sorties : leur ordre compte
NOTES_NOMS = ["la", "la#", "si", "do", "do#", "ré", "ré#", "mi", "fa", "fa#", "sol", "sol#"]


def nom_note(k):
    """Touche k du piano (0 = la0, 48 = la4) : nom, fréquence sonore, canal optique (grille de 50 GHz depuis 191,30 THz)."""
    octave = (k + 9) // 12
    return f"{NOTES_NOMS[k % 12]}{octave}", 27.5 * 2 ** (k / 12), 191.30 + 0.05 * k


def zone_lire(n):
    et, adr = n[1], n[2]
    if len(n) > 3 and n[3]:
        return n[3]
    if isinstance(et, int):
        if adr[0] == "nombre":
            return (et, adr[1], adr[1] + 1)
        return (et, 0, 1 << 24)
    return TOUT


def zones_conflit(a, b):
    ea, la, ha = a
    eb, lb, hb = b
    if ea == "es" or eb == "es":
        return ea == eb
    if ea is not None and eb is not None and ea != eb:
        return False
    return la < hb and lb < ha


def ensembles_conflit(za, zb):
    return any(zones_conflit(x, y) for x in za for y in zb)


class Effets:
    """Lectures et écritures (zones) de chaque fonction, appels compris (point fixe)."""

    INTEGRES_EFFETS = {"sortie": ({ES}, {ES}), "entrée": ({ES}, {ES}), "bruit": ({ES}, {ES}), "pile": ({ES}, {ES}), "__service": ({ES, TOUT}, {ES, TOUT}), "gemv": ({(2, 0, 1 << 24)}, {(2, 0, 1 << 24)}),
                       **{n: ({ES, TOUT}, {ES}) for n in ("lire_car", "ecrire_car", "ouvrir_lecture", "ouvrir_ecriture",
                                                          "fermer", "fin_de")}}

    def __init__(self, fonctions):
        self.f = {f.nom: f for f in fonctions}
        self.eff = {n: (set(), set()) for n in self.f}
        change = True
        while change:
            change = False
            for n, f in self.f.items():
                r, w = set(), set()
                self.parcourir(f.corps, r, w)
                if r - self.eff[n][0] or w - self.eff[n][1]:
                    self.eff[n][0].update(r)
                    self.eff[n][1].update(w)
                    change = True

    def appel(self, nom, r, w):
        if nom in self.INTEGRES_EFFETS:
            a, b = self.INTEGRES_EFFETS[nom]
            r |= a
            w |= b
        elif nom in self.f:
            r |= self.eff[nom][0]
            w |= self.eff[nom][1]
        elif nom not in INTEGRES:
            r.add(TOUT)
            w.add(TOUT)

    def parcourir(self, n, r, w):
        if isinstance(n, list):
            for x in n:
                self.parcourir(x, r, w)
            return
        if not isinstance(n, tuple) or not n:
            return
        g = n[0]
        if g == "lire":
            r.add(zone_lire(n))
        elif g == "ecrire":
            et, adr = n[1], n[2]
            if len(n) > 5 and n[5]:
                w.add(n[5])
            elif isinstance(et, int):
                w.add((et, adr[1], adr[1] + 1) if adr[0] == "nombre" else (et, 0, 1 << 24))
            else:
                w.add(TOUT)
        elif g == "asm":
            r.add(TOUT)
            w.add(TOUT)
        elif g == "champ_ref":
            r.add(TOUT)
        elif g == "ecrire_champ":
            w.add(TOUT)
        elif g in ("nouveau_de", "construire"):
            r.add(TOUT)
            w.add(TOUT)
        elif g == "segments" and len(n) > 8 and n[8]:
            r.add(ZONE_COPIES)               # les copies des tableaux cumulés
            w.add(ZONE_COPIES)
        elif g == "appel":
            self.appel(n[1], r, w)
        for x in n[1:]:
            if isinstance(x, (tuple, list)):
                self.parcourir(x, r, w)

    def tache(self, st):
        r, w = set(), set()
        self.parcourir(st, r, w)
        return r, w


def indice_de(adr, var):
    """Si l'adresse d'une case de tableau est base + var + c (ou var + c), rend c ; sinon None."""
    def decalage(e):
        if e[0] == "var" and e[1] == var:
            return 0
        if e[0] == "bin" and e[1] in ("+", "-") and e[2][0] == "var" and e[2][1] == var and e[3][0] == "nombre":
            return e[3][1] if e[1] == "+" else -e[3][1]
        return None
    c = decalage(adr)
    if c is not None:
        return c
    if adr[0] == "bin" and adr[1] == "+" and adr[2][0] == "nombre":
        return decalage(adr[3])
    return None


def segments_independants(eff, st):
    """Deux segments d'une même boucle sont-ils indépendants ? Les écritures tableau[i + c] d'un segment ne touchent que
    ses propres indices ; les tableaux cumulés ont une copie par segment ; tout le reste est pris en entier."""
    var, corps = st[1], st[4]
    privees = {c[1]: c[0] for c in (st[8] if len(st) > 8 else ())}
    r, w, wi = set(), set(), set()

    def marche(n):
        if isinstance(n, list):
            for x in n:
                marche(x)
            return
        if not isinstance(n, tuple) or not n:
            return
        if n[0] in ("lire", "ecrire") and len(n) > 3 and n[-1] in privees and isinstance(n[-1], tuple):
            for x in n[2:-1]:
                marche(x)
            return
        if n[0] == "ecrire" and len(n) > 5 and n[5] and isinstance(n[1], int):
            c = indice_de(n[2], var)
            if c is not None:
                wi.add((n[5], c))
                marche(n[2])
                marche(n[3])
                return
        if n[0] in ("lire", "ecrire", "asm", "appel", "champ_ref", "ecrire_champ", "nouveau_de", "construire"):
            eff.parcourir(n, r, w)
            return
        for x in n[1:]:
            if isinstance(x, (tuple, list)):
                marche(x)

    marche(corps)
    for z, nom in privees.items():
        if ensembles_conflit({z}, r | w | {zz for zz, _c in wi}):
            raise VtxError(f"ligne {st[5]} : le tableau cumulé « {nom} » est aussi atteint autrement que par son nom dans la "
                           f"boucle (fonction appelée ou adresse calculée) : la somme des segments ne serait pas sûre")
    zones_i = {z for z, _c in wi}
    if ensembles_conflit(w, w) or ensembles_conflit(w, r) or ensembles_conflit(w, zones_i):
        return False
    if ensembles_conflit(zones_i, r):
        return False
    par_zone = {}
    for z, c in wi:
        par_zone.setdefault(z, set()).add(c)
    for z, cs in par_zone.items():
        if len(cs) > 1:
            return False
        for z2 in par_zone:
            if z2 != z and zones_conflit(z, z2):
                return False
    return True


def est_tache(st, fonctions):
    return (st[0] == "expr" and st[1][0] == "appel" and st[1][1] in fonctions and not st[1][1].startswith("__"))


def partitionner(fonctions, melange=None):
    """Remplace chaque suite d'au moins deux appels de tâches par un accord ordonné mesure par mesure.
    Rend la liste des accords (pour le rapport). melange : graine pour mélanger l'ordre dans chaque mesure (tests)."""
    eff = Effets(fonctions)
    noms = {f.nom for f in fonctions}
    copie_libre = [COPIES_DEBUT]
    notes, accords = {}, []
    hasard = random.Random(melange) if melange is not None else None

    def note_de(nom):
        if nom not in notes:
            notes[nom] = 48 + len(notes)
        return notes[nom]

    def bloc(lst, fn):
        out, i = [], 0
        while i < len(lst):
            st = lst[i]
            if est_tache(st, noms):
                j = i
                while j < len(lst) and est_tache(lst[j], noms):
                    j += 1
                if j - i >= 2:
                    taches = lst[i:j]
                    ef = [eff.tache(t) for t in taches]
                    niveau = []
                    for k in range(len(taches)):
                        nv = 1
                        for m in range(k):
                            rk, wk = ef[k]
                            rm, wm = ef[m]
                            if ensembles_conflit(wk, wm) or ensembles_conflit(wk, rm) or ensembles_conflit(rk, wm):
                                nv = max(nv, niveau[m] + 1)
                        niveau.append(nv)
                    mesures = []
                    for nv in range(1, max(niveau) + 1):
                        m = [(t, note_de(t[1][1]), t[1][1]) for t, n_ in zip(taches, niveau) if n_ == nv]
                        if hasard:
                            hasard.shuffle(m)
                        mesures.append(m)
                    rid = len(accords)
                    accords.append({"id": rid, "fonction": fn, "ligne": ligne_instr(taches[0]), "mesures": mesures})
                    out.append(("accord", rid, mesures))
                    i = j
                    continue
            if st[0] == "segments":
                corps = bloc(st[4], fn)
                st = st[:4] + (corps,) + tuple(st[5:])
                pre, morceaux = deplier_segments(st)
                out.extend(pre)
                n = len(morceaux)
                libres = segments_independants(eff, st)
                noms_s = [f"{fn}·{nom_segment(k, n)}" for k in range(n)]
                cumul = st[8] if len(st) > 8 else ()
                reduction = []
                if cumul:
                    sid, l = st[7], st[5]
                    bases = []
                    for k in range(n):
                        copies = {}
                        for nom_t, zone, et_t, base_t, n_mots in cumul:
                            copies[zone] = (base_t, copie_libre[0], n_mots)
                            copie_libre[0] += n_mots
                        bases.append(copies)
                    if copie_libre[0] > COPIES_FIN:
                        raise VtxError(f"ligne {l} : plus de place pour les copies des tableaux cumulés")
                    neufs = []
                    for k, (m_, copies) in enumerate(zip(morceaux, bases)):
                        jk = f"__cz{sid}"
                        mise_a_zero = [("pour", jk, ("nombre", 0), ("nombre", nm), [
                            ("ecrire", 3, ("bin", "+", ("nombre", cb), ("var", jk, l)), ("nombre", 0), l, (3, cb, cb + nm))],
                            l, 1, "copie" if k else "") for (_b, cb, nm) in copies.values()]
                        boucle = m_[:4] + (remplacer_cumul(m_[4], copies),) + (m_[5], 1, "copie" if k else "")
                        neufs.append(("bloc", mise_a_zero + [boucle]))
                    morceaux = neufs
                    for zone, (nom_t, z_, et_t, base_t, n_mots) in zip([c[1] for c in cumul], cumul):
                        jr = f"__cr{sid}"
                        somme = ("lire", et_t, ("bin", "+", ("nombre", base_t), ("var", jr, l)), z_)
                        for copies in bases:
                            _b, cb, nm = copies[zone]
                            somme = ("bin", "+", somme, ("lire", 3, ("bin", "+", ("nombre", cb), ("var", jr, l)), (3, cb, cb + nm)))
                        reduction.append(("pour", jr, ("nombre", 0), ("nombre", n_mots), [
                            ("ecrire", et_t, ("bin", "+", ("nombre", base_t), ("var", jr, l)), somme, l, z_)], l, 1,
                            "copie" if len(reduction) else ""))
                if libres:
                    mesure = [(m_, note_de(nm), nm) for m_, nm in zip(morceaux, noms_s)]
                    if hasard:
                        hasard.shuffle(mesure)
                    mesures = [mesure]
                else:
                    mesures = [[(m_, note_de(nm), nm)] for m_, nm in zip(morceaux, noms_s)]
                rid = len(accords)
                accords.append({"id": rid, "fonction": fn, "ligne": st[5], "mesures": mesures, "segments": n,
                                "cumul": [c[0] for c in cumul]})
                out.append(("accord", rid, mesures))
                out.extend(reduction)
                i += 1
                continue
            if st[0] == "si":
                st = (st[0], st[1], bloc(st[2], fn), None if st[3] is None else bloc(st[3], fn)) + tuple(st[4:])
            elif st[0] == "tantque":
                st = (st[0], st[1], bloc(st[2], fn)) + tuple(st[3:])
            elif st[0] == "pour":
                st = st[:4] + (bloc(st[4], fn),) + tuple(st[5:])
            out.append(st)
            i += 1
        return out

    for f in fonctions:
        if getattr(f, "origine", "") != "prélude":
            f.corps = bloc(f.corps, f.nom)
    return accords, notes


def partition_texte(accords, notes, carte=None):
    """La partition lisible : une ligne par mesure, une note par tâche. carte : (fichier, ligne) de chaque ligne assemblée."""
    lignes = []
    for a in accords:
        n_t = sum(len(m) for m in a["mesures"])
        ou = f"ligne {a['ligne']}"
        if carte and 1 <= a["ligne"] <= len(carte):
            ou = f"{carte[a['ligne'] - 1][0]}, ligne {carte[a['ligne'] - 1][1]}"
        lignes.append(f"accord {a['id']} dans {a['fonction']} ({ou}) : {n_t} tâches en {len(a['mesures'])} mesure(s)")
        for k, m in enumerate(a["mesures"], 1):
            cases = []
            for _t, note, nom in m:
                nm, hz, thz = nom_note(note)
                cases.append(f"{nm} {nom}")
            lignes.append(f"  mesure {k} : " + " | ".join(cases))
    if notes:
        lignes.append("notes : " + ", ".join(f"{nom} = {nom_note(k)[0]} ({nom_note(k)[1]:.1f} Hz, canal {nom_note(k)[2]:.2f} THz)"
                                         for nom, k in notes.items()))
    return "\n".join(lignes)


CŒURS_LAISSES = 1   # cœurs laissés au système, au navigateur et à l'affichage


def coeurs_machine():
    try:
        return max(1, len(os.sched_getaffinity(0)))
    except (AttributeError, OSError):
        return max(1, os.cpu_count() or 1)


def cylindres_machine(laisser=CŒURS_LAISSES):
    """Cylindres pris sur la machine hôte : ses cœurs moins ceux qu'on laisse tranquilles, au moins un
    (le SPU optique, lui, aura autant de cylindres que de canaux)."""
    return max(1, coeurs_machine() - laisser)


def simuler_accord(acc, cn):
    """Durée d'un accord sur cn cylindres (None : autant qu'il en faut), tous les niveaux partageant les mêmes cylindres.
    Ordonnancement glouton : une tâche prête prend un cylindre libre, la plus longue d'abord ; une tâche qui ouvre un
    accord imbriqué rend son cylindre et attend la fin de l'accord ; les mesures d'un accord se suivent."""
    import heapq
    libres = cn if cn is not None else 1 << 30
    prets, en_cours, numero = [], [], [0]

    def travail(t):
        return sum(x[1] if x[0] == "calc" else sum(travail(u) for m in x[1]["mesures"].values() for u in m)
                   for x in t["items"])

    def ouvrir(a, parent):
        etat = {"a": a, "cles": sorted(a["mesures"]), "m": 0, "reste": 0, "parent": parent}
        lancer(etat)

    def lancer(etat):
        if etat["m"] == len(etat["cles"]):
            if etat["parent"] is not None:
                avancer(etat["parent"])
            return
        taches = etat["a"]["mesures"][etat["cles"][etat["m"]]]
        etat["reste"] = len(taches)
        for t in taches:
            avancer({"t": t, "i": 0, "etat": etat})

    def avancer(fil):
        items = fil["t"]["items"]
        if fil["i"] == len(items):
            e = fil["etat"]
            e["reste"] -= 1
            if e["reste"] == 0:
                e["m"] += 1
                lancer(e)
        elif items[fil["i"]][0] == "calc":
            numero[0] += 1
            heapq.heappush(prets, (-travail(fil["t"]), numero[0], fil))
        else:
            fil["i"] += 1
            ouvrir(items[fil["i"] - 1][1], fil)

    ouvrir(acc, None)
    temps = 0
    while True:
        while libres and prets:
            _p, _n, fil = heapq.heappop(prets)
            libres -= 1
            d = fil["t"]["items"][fil["i"]][1]
            fil["i"] += 1
            numero[0] += 1
            heapq.heappush(en_cours, (temps + d, numero[0], fil))
        if not en_cours:
            return temps
        temps, _n, fil = heapq.heappop(en_cours)
        libres += 1
        avancer(fil)


def jouer(src, entrees=(), dossier=None, canaux=(None, CANAUX), max_pas=200_000_000):
    """Exécute le programme partitionné en mesurant chaque tâche (en instructions) ; rend le temps séquentiel et le temps
    avec les tâches d'une même mesure jouées ensemble, sur un nombre illimité de cylindres ou sur n cylindres.
    Les accords imbriqués (segments d'une boucle dans une tâche) partagent les cylindres de l'accord qui les contient."""
    asm, _carte, _l = compiler_complet(src, dossier=dossier)
    mots, infos, _e = _assembler(asm)
    taches, fins = {}, {}
    for adr, d in infos:
        t = d.split()
        if t[0].upper() == ".TACHE":
            taches[adr] = (int(t[1]), int(t[2]), t[3])
        elif t[0].upper() == ".ACCORD_FIN":
            fins[adr] = int(t[1])
    cpu = CPU()
    cpu.charger(mots)
    cpu.entree.extend(entrees)
    bilan = {"seq": 0, "par": {c: 0 for c in canaux}, "executions": 0, "duree_taches": Counter(), "gain_imbrique": 0}
    pile = []   # accords en cours : {"cadre", "rid", "debut", "mesures" {k: [tâches]}, "ouverte": tâche}
                # tâche : {"nom", "debut", "dernier", "items": [("calc", durée) | ("accord", accord)]}

    def fermer(acc, pas):
        t = acc["ouverte"]
        if t is not None:
            t["items"].append(("calc", pas - t["dernier"]))
            bilan["duree_taches"][t["nom"]] += pas - t["debut"]
            acc["ouverte"] = None

    def crochet(c):
        pc = c.pc
        if pc not in taches and pc not in fins:
            return False
        cadre, pas = c.r[13], c.pas
        haut = pile[-1] if pile else None
        if pc in taches:
            rid, k, nom = taches[pc]
            if haut is not None and haut["rid"] == rid and haut["cadre"] == cadre:
                fermer(haut, pas)
                acc = haut
            else:
                acc = {"cadre": cadre, "rid": rid, "debut": pas, "mesures": {}, "ouverte": None}
                if haut is not None and haut["ouverte"] is not None:
                    t = haut["ouverte"]
                    t["items"].append(("calc", pas - t["dernier"]))
                    t["items"].append(("accord", acc))
                pile.append(acc)
            tache = {"nom": nom, "debut": pas, "dernier": pas, "items": []}
            acc["mesures"].setdefault(k, []).append(tache)
            acc["ouverte"] = tache
        elif haut is not None and haut["rid"] == fins[pc] and haut["cadre"] == cadre:
            fermer(haut, pas)
            pile.pop()
            brut = pas - haut["debut"]
            if pile and pile[-1]["ouverte"] is not None:
                pile[-1]["ouverte"]["dernier"] = pas
                bilan["gain_imbrique"] += brut - simuler_accord(haut, None)
            else:
                bilan["seq"] += brut
                for cn in canaux:
                    bilan["par"][cn] += simuler_accord(haut, cn)
                bilan["executions"] += 1
        return False

    cpu.sur_pas = crochet
    cpu.executer(max_pas)
    bilan["total"] = cpu.pas
    bilan["sortie"] = cpu.sortie
    return bilan


def exporter(src, dossier=None):
    """Code machine et table des accords pour la machine Rust multicœur : [nombre d'accords, puis pour chacun l'adresse
    de début, l'adresse de fin, le nombre de mesures, et pour chaque mesure le nombre de tâches puis (début, fin)]."""
    asm, _carte, _l = compiler_complet(src, dossier=dossier)
    mots, infos, _e = _assembler(asm)
    marques = []                                     # (adresse, genre, rid, mesure)
    for adr, d in infos:
        t = d.split()
        if t[0].upper() == ".TACHE":
            marques.append((adr, "t", int(t[1]), int(t[2])))
        elif t[0].upper() == ".ACCORD_FIN":
            marques.append((adr, "f", int(t[1]), 0))
    accords = {}
    for i, (adr, genre, rid, k) in enumerate(marques):
        a = accords.setdefault(rid, {"mesures": {}, "fin": None, "debut": None})
        if genre == "f":
            a["fin"] = adr
            continue
        if a["debut"] is None:
            a["debut"] = adr
        fin = next(m[0] for m in marques[i + 1:] if m[2] == rid)
        a["mesures"].setdefault(k, []).append((adr, fin))
    table = [len(accords)]
    for rid in sorted(accords):
        a = accords[rid]
        table += [a["debut"], a["fin"], len(a["mesures"])]
        for k in sorted(a["mesures"]):
            taches = a["mesures"][k]
            table.append(len(taches))
            for d_, f_ in taches:
                table += [d_, f_]
    return mots, table


def executer(src, entrees=(), max_pas=5_000_000, mem=None, optim=True, dossier=None, partition=True, melange=None):
    asm = compiler(src, optim=optim, dossier=dossier, partition=partition, melange=melange)
    mots = assembler(asm)
    cpu = CPU()
    if mem is not None:
        cpu.mem = mem
    cpu.charger(mots)
    cpu.entree.extend(entrees)
    cpu.executer(max_pas)
    return cpu, asm, mots


TESTS = [
    ("frontière binaire : binaire, quaternaire et leurs formes sur 16 quits",
     "fonction principal() { sortie(binaire(faux)); sortie(binaire(vrai)); sortie(binaire(inconnu)); "
     "sortie(binaire(variable)); sortie(entier(quaternaire(0))); sortie(entier(quaternaire(1))); "
     "sortie(entier(quaternaire(2))); sortie(entier(quaternaire(3))); sortie(binaire16(0q0123)); "
     "sortie(quaternaire16(binaire16(0q3210_0123_2301_1032))); }",
     (), [0, 1, 2, 3, 1, 2, 0, 3, 2863311495, 3827020110]),
    ("somme de 1 à 10",
     "fonction principal() { soit t = 0; soit i = 10; tantque i != 0 { t = t + i; i = i - 1; } sortie(t); }",
     (), [55]),
    ("cube, champs et quits",
     "fonction principal() { soit p = #3A7F1C80; sortie(p.r); sortie(p.v); sortie(p.b); sortie(p.a); "
     "sortie(p.q(3)); sortie(0q0123); sortie(#3A7F1C); }",
     (), [58, 127, 28, 128, 2, 27, 0x3A7F1C00]),
    ("complément et produit scalaire",
     "fonction principal() { sortie(~27); sortie(gdot(#01020304, #0A0B0C0D)); sortie(min4(27, 39)); "
     "sortie(max4(27, 39)); sortie(addm4(27, 27)); }",
     (), [4294967268, 120, 23, 43, 34]),
    ("mémoire étagée",
     "fonction principal() { @2[7] = 99; @0[100] = 5; soit y = @2[7]; sortie(y); sortie(@0[100] + @2[7]); }",
     (), [99, 104]),
    ("comparaisons non signées",
     "fonction principal() { sortie(3 < 5); sortie(5 < 3); sortie(5 > 3); sortie(3 <= 3); sortie(4 >= 5); "
     "sortie(0 < 0xFFFFFFFF); sortie(7 == 7); sortie(7 != 7); }",
     (), [1, 0, 1, 1, 0, 1, 1, 0]),
    ("opérations bit à bit et division",
     "fonction principal() { sortie(0xF0 & 0x3C); sortie(0xF0 | 0x0F); sortie(0xFF ^ 0x0F); sortie(1 << 10); "
     "sortie(1024 >> 3); sortie(3 <<q 2); sortie(48 >>q 1); sortie(100 / 7); sortie(100 % 7); }",
     (), [48, 255, 240, 1024, 128, 48, 12, 14, 2]),
    ("récursion : fibonacci et factorielle",
     "fonction fib(n) { si n < 2 { retour n; } retour fib(n - 1) + fib(n - 2); } "
     "fonction fact(n) { si n == 0 { retour 1; } retour n * fact(n - 1); } "
     "fonction principal() { sortie(fib(10)); sortie(fact(6)); }",
     (), [55, 720]),
    ("si, sinon et tantque imbriqués",
     "fonction principal() { soit i = 1; soit c = 0; tantque i <= 20 { si i % 3 == 0 { c = c + 1; } "
     "sinon si i == 7 { c = c + 100; } i = i + 1; } sortie(c); }",
     (), [106]),
    ("entrée et sortie",
     "fonction principal() { sortie(entrée() + entrée()); }",
     (5, 7), [12]),
    ("interpolation à 4 coins écrite en vtx",
     "fonction voie(a, b, c, d, u, v, s) { soit wa = (256 - u) * (256 - v); soit wb = u * (256 - v); "
     "soit wc = (256 - u) * v; soit wd = u * v; "
     "retour ((wa * ((a >> s) & 255) + wb * ((b >> s) & 255) + wc * ((c >> s) & 255) + wd * ((d >> s) & 255)) >> 16) & 255; } "
     "fonction interp(a, b, c, d, u, v) { retour (voie(a, b, c, d, u, v, 24) << 24) | (voie(a, b, c, d, u, v, 16) << 16) "
     "| (voie(a, b, c, d, u, v, 8) << 8) | voie(a, b, c, d, u, v, 0); } "
     "fonction principal() { sortie(interp(#00102030, #FF8040C0, #10203040, #80FF00FF, 64, 192)); "
     "sortie(interp(#00102030, #FF8040C0, #10203040, #80FF00FF, 0, 0)); "
     "sortie(interp(#00102030, #FF8040C0, #10203040, #80FF00FF, 256, 256)); }",
     (), None),
    ("constantes, données et boucles pour",
     "constante N = 5; donnees @2[0] = { 10, 20, 30, 40, 50 }; "
     "fonction principal() { soit s = 0; pour i dans 0..N { s = s + @2[i]; } pour i dans 0..2 { s = s + 1; } sortie(s); }",
     (), [152]),
    ("étage variable",
     "fonction lire_e(e, a) { retour @(e)[a]; } "
     "fonction principal() { @(3)[7] = 99; @(2)[7] = 5; sortie(lire_e(3, 7)); sortie(lire_e(2, 7)); sortie(@3[7] + @2[7]); }",
     (), [99, 5, 104]),
    ("logique à court-circuit",
     "fonction f() { sortie(7); retour 1; } "
     "fonction principal() { sortie(0 && f()); sortie(1 || f()); sortie(1 && f()); sortie(!0); sortie(!5); "
     "sortie((3 < 5) && (5 < 9)); sortie((3 > 5) || (2 == 2)); }",
     (), [0, 1, 7, 1, 1, 0, 1, 1]),
    ("prélude : abs, inf, sup, min, max",
     "fonction principal() { sortie(abs(0 - 5)); sortie(inf(0 - 1, 1)); sortie(inf(1, 0 - 1)); "
     "sortie(min(3, 9)); sortie(max(3, 9)); sortie(sup(1, 0 - 1)); }",
     (), [5, 1, 0, 3, 9, 1]),
    ("prélude : gdotn et copier",
     "fonction principal() { @2[0] = #01020304; @2[1] = #05060708; @1[0] = #01010101; @1[1] = #02020202; "
     "sortie(gdotn(2, 0, 1, 0, 2)); copier(3, 10, 2, 0, 2); sortie(@3[10]); sortie(@3[11]); }",
     (), [62, 0x01020304, 0x05060708]),
    ("prélude : mélange et poids",
     "fonction principal() { @2[0] = 1; @2[1] = 3; @1[0] = #0A000000; @1[1] = #14000000; "
     "sortie(melange(1, 0, 2, 0, 24, 2)); sortie(poids(0, 13)); sortie(poids(8192, 13)); sortie(poids(1000000, 13)); }",
     (), [70, 65536, 32768, 0]),
    ("gemv : produit matrice × vecteur en une instruction",
     "fonction principal() { @2[0] = #01020304; @2[1] = #01010101; @2[10] = #01010101; @2[11] = #02020202; "
     "@2[12] = #00000001; @2[13] = #00000001; gemv(2, 2, 0, 10, 100); sortie(@2[100]); sortie(@2[101]); }",
     (), [18, 5]),
    ("arrêter et continuer",
     "fonction principal() { soit s = 0; pour i dans 0..10 { si i == 3 { continuer; } si i == 7 { arrêter; } s = s + i; } "
     "sortie(s); soit k = 0; tantque vrai { k = k + 1; si k > 4 { arrêter; } } sortie(k); }",
     (), [18, 5]),
    ("alias et, ou, non, étages nommés",
     "fonction principal() { sortie(1 et 0); sortie(1 ou 0); sortie(non 5); sortie(non 0); @PARTAGE[3] = 9; "
     "sortie(@2[3]); sortie(vrai + faux + DISQUE); }",
     (), [0, 1, 0, 1, 9, 4]),
    ("alias entree et données",
     "données @2[0] = { 7 }; fonction principal() { sortie(entree() + @2[0]); }",
     (5,), [12]),
    ("données en segment",
     "donnees @2[10] = { 5, 6, 7 }; fonction principal() { sortie(@2[10] + @2[11] + @2[12]); }", (), [18]),
    ("opérateurs signés",
     "fonction principal() { sortie(-7 ./ 2); sortie(-7 .% 2); sortie(-8 .>> 1); sortie(-1 .< 0); sortie(3 .> -2); "
     "sortie(-5 .<= -5); sortie(2 .>= 3); sortie(7 ./ -2); sortie(-9 .% -4); sortie(signe(-3)); }",
     (), [4294967293, 4294967295, 4294967292, 1, 1, 1, 0, 4294967293, 4294967295, 4294967295]),
    ("tableaux et structures",
     "structure Point { x; y; } tableau pts[4] de Point @PARTAGE[100]; tableau v[8] @2[200]; "
     "fonction principal() { pour i dans 0..4 { pts[i].x = i * 10; pts[i].y = i + 1; v[i] = pts[i].x + pts[i].y; } "
     "sortie(v[3]); sortie(pts[2].y); sortie(@2[105]); }",
     (), [34, 3, 3]),
    ("pas de boucle", "fonction principal() { pour i dans 0..10 par 3 { sortie(i); } }", (), [0, 3, 6, 9]),
    ("grande table en segment",
     "donnees @1[0] = { %s }; fonction principal() { sortie(@1[2999] + @1[1234]); }" % "0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 211, 212, 213, 214, 215, 216, 217, 218, 219, 220, 221, 222, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 234, 235, 236, 237, 238, 239, 240, 241, 242, 243, 244, 245, 246, 247, 248, 249, 250, 251, 252, 253, 254, 255, 256, 257, 258, 259, 260, 261, 262, 263, 264, 265, 266, 267, 268, 269, 270, 271, 272, 273, 274, 275, 276, 277, 278, 279, 280, 281, 282, 283, 284, 285, 286, 287, 288, 289, 290, 291, 292, 293, 294, 295, 296, 297, 298, 299, 300, 301, 302, 303, 304, 305, 306, 307, 308, 309, 310, 311, 312, 313, 314, 315, 316, 317, 318, 319, 320, 321, 322, 323, 324, 325, 326, 327, 328, 329, 330, 331, 332, 333, 334, 335, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362, 363, 364, 365, 366, 367, 368, 369, 370, 371, 372, 373, 374, 375, 376, 377, 378, 379, 380, 381, 382, 383, 384, 385, 386, 387, 388, 389, 390, 391, 392, 393, 394, 395, 396, 397, 398, 399, 400, 401, 402, 403, 404, 405, 406, 407, 408, 409, 410, 411, 412, 413, 414, 415, 416, 417, 418, 419, 420, 421, 422, 423, 424, 425, 426, 427, 428, 429, 430, 431, 432, 433, 434, 435, 436, 437, 438, 439, 440, 441, 442, 443, 444, 445, 446, 447, 448, 449, 450, 451, 452, 453, 454, 455, 456, 457, 458, 459, 460, 461, 462, 463, 464, 465, 466, 467, 468, 469, 470, 471, 472, 473, 474, 475, 476, 477, 478, 479, 480, 481, 482, 483, 484, 485, 486, 487, 488, 489, 490, 491, 492, 493, 494, 495, 496, 497, 498, 499, 500, 501, 502, 503, 504, 505, 506, 507, 508, 509, 510, 511, 512, 513, 514, 515, 516, 517, 518, 519, 520, 521, 522, 523, 524, 525, 526, 527, 528, 529, 530, 531, 532, 533, 534, 535, 536, 537, 538, 539, 540, 541, 542, 543, 544, 545, 546, 547, 548, 549, 550, 551, 552, 553, 554, 555, 556, 557, 558, 559, 560, 561, 562, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 573, 574, 575, 576, 577, 578, 579, 580, 581, 582, 583, 584, 585, 586, 587, 588, 589, 590, 591, 592, 593, 594, 595, 596, 597, 598, 599, 600, 601, 602, 603, 604, 605, 606, 607, 608, 609, 610, 611, 612, 613, 614, 615, 616, 617, 618, 619, 620, 621, 622, 623, 624, 625, 626, 627, 628, 629, 630, 631, 632, 633, 634, 635, 636, 637, 638, 639, 640, 641, 642, 643, 644, 645, 646, 647, 648, 649, 650, 651, 652, 653, 654, 655, 656, 657, 658, 659, 660, 661, 662, 663, 664, 665, 666, 667, 668, 669, 670, 671, 672, 673, 674, 675, 676, 677, 678, 679, 680, 681, 682, 683, 684, 685, 686, 687, 688, 689, 690, 691, 692, 693, 694, 695, 696, 697, 698, 699, 700, 701, 702, 703, 704, 705, 706, 707, 708, 709, 710, 711, 712, 713, 714, 715, 716, 717, 718, 719, 720, 721, 722, 723, 724, 725, 726, 727, 728, 729, 730, 731, 732, 733, 734, 735, 736, 737, 738, 739, 740, 741, 742, 743, 744, 745, 746, 747, 748, 749, 750, 751, 752, 753, 754, 755, 756, 757, 758, 759, 760, 761, 762, 763, 764, 765, 766, 767, 768, 769, 770, 771, 772, 773, 774, 775, 776, 777, 778, 779, 780, 781, 782, 783, 784, 785, 786, 787, 788, 789, 790, 791, 792, 793, 794, 795, 796, 797, 798, 799, 800, 801, 802, 803, 804, 805, 806, 807, 808, 809, 810, 811, 812, 813, 814, 815, 816, 817, 818, 819, 820, 821, 822, 823, 824, 825, 826, 827, 828, 829, 830, 831, 832, 833, 834, 835, 836, 837, 838, 839, 840, 841, 842, 843, 844, 845, 846, 847, 848, 849, 850, 851, 852, 853, 854, 855, 856, 857, 858, 859, 860, 861, 862, 863, 864, 865, 866, 867, 868, 869, 870, 871, 872, 873, 874, 875, 876, 877, 878, 879, 880, 881, 882, 883, 884, 885, 886, 887, 888, 889, 890, 891, 892, 893, 894, 895, 896, 897, 898, 899, 900, 901, 902, 903, 904, 905, 906, 907, 908, 909, 910, 911, 912, 913, 914, 915, 916, 917, 918, 919, 920, 921, 922, 923, 924, 925, 926, 927, 928, 929, 930, 931, 932, 933, 934, 935, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 950, 951, 952, 953, 954, 955, 956, 957, 958, 959, 960, 961, 962, 963, 964, 965, 966, 967, 968, 969, 970, 971, 972, 973, 974, 975, 976, 977, 978, 979, 980, 981, 982, 983, 984, 985, 986, 987, 988, 989, 990, 991, 992, 993, 994, 995, 996, 997, 998, 999, 1000, 1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008, 1009, 1010, 1011, 1012, 1013, 1014, 1015, 1016, 1017, 1018, 1019, 1020, 1021, 1022, 1023, 1024, 1025, 1026, 1027, 1028, 1029, 1030, 1031, 1032, 1033, 1034, 1035, 1036, 1037, 1038, 1039, 1040, 1041, 1042, 1043, 1044, 1045, 1046, 1047, 1048, 1049, 1050, 1051, 1052, 1053, 1054, 1055, 1056, 1057, 1058, 1059, 1060, 1061, 1062, 1063, 1064, 1065, 1066, 1067, 1068, 1069, 1070, 1071, 1072, 1073, 1074, 1075, 1076, 1077, 1078, 1079, 1080, 1081, 1082, 1083, 1084, 1085, 1086, 1087, 1088, 1089, 1090, 1091, 1092, 1093, 1094, 1095, 1096, 1097, 1098, 1099, 1100, 1101, 1102, 1103, 1104, 1105, 1106, 1107, 1108, 1109, 1110, 1111, 1112, 1113, 1114, 1115, 1116, 1117, 1118, 1119, 1120, 1121, 1122, 1123, 1124, 1125, 1126, 1127, 1128, 1129, 1130, 1131, 1132, 1133, 1134, 1135, 1136, 1137, 1138, 1139, 1140, 1141, 1142, 1143, 1144, 1145, 1146, 1147, 1148, 1149, 1150, 1151, 1152, 1153, 1154, 1155, 1156, 1157, 1158, 1159, 1160, 1161, 1162, 1163, 1164, 1165, 1166, 1167, 1168, 1169, 1170, 1171, 1172, 1173, 1174, 1175, 1176, 1177, 1178, 1179, 1180, 1181, 1182, 1183, 1184, 1185, 1186, 1187, 1188, 1189, 1190, 1191, 1192, 1193, 1194, 1195, 1196, 1197, 1198, 1199, 1200, 1201, 1202, 1203, 1204, 1205, 1206, 1207, 1208, 1209, 1210, 1211, 1212, 1213, 1214, 1215, 1216, 1217, 1218, 1219, 1220, 1221, 1222, 1223, 1224, 1225, 1226, 1227, 1228, 1229, 1230, 1231, 1232, 1233, 1234, 1235, 1236, 1237, 1238, 1239, 1240, 1241, 1242, 1243, 1244, 1245, 1246, 1247, 1248, 1249, 1250, 1251, 1252, 1253, 1254, 1255, 1256, 1257, 1258, 1259, 1260, 1261, 1262, 1263, 1264, 1265, 1266, 1267, 1268, 1269, 1270, 1271, 1272, 1273, 1274, 1275, 1276, 1277, 1278, 1279, 1280, 1281, 1282, 1283, 1284, 1285, 1286, 1287, 1288, 1289, 1290, 1291, 1292, 1293, 1294, 1295, 1296, 1297, 1298, 1299, 1300, 1301, 1302, 1303, 1304, 1305, 1306, 1307, 1308, 1309, 1310, 1311, 1312, 1313, 1314, 1315, 1316, 1317, 1318, 1319, 1320, 1321, 1322, 1323, 1324, 1325, 1326, 1327, 1328, 1329, 1330, 1331, 1332, 1333, 1334, 1335, 1336, 1337, 1338, 1339, 1340, 1341, 1342, 1343, 1344, 1345, 1346, 1347, 1348, 1349, 1350, 1351, 1352, 1353, 1354, 1355, 1356, 1357, 1358, 1359, 1360, 1361, 1362, 1363, 1364, 1365, 1366, 1367, 1368, 1369, 1370, 1371, 1372, 1373, 1374, 1375, 1376, 1377, 1378, 1379, 1380, 1381, 1382, 1383, 1384, 1385, 1386, 1387, 1388, 1389, 1390, 1391, 1392, 1393, 1394, 1395, 1396, 1397, 1398, 1399, 1400, 1401, 1402, 1403, 1404, 1405, 1406, 1407, 1408, 1409, 1410, 1411, 1412, 1413, 1414, 1415, 1416, 1417, 1418, 1419, 1420, 1421, 1422, 1423, 1424, 1425, 1426, 1427, 1428, 1429, 1430, 1431, 1432, 1433, 1434, 1435, 1436, 1437, 1438, 1439, 1440, 1441, 1442, 1443, 1444, 1445, 1446, 1447, 1448, 1449, 1450, 1451, 1452, 1453, 1454, 1455, 1456, 1457, 1458, 1459, 1460, 1461, 1462, 1463, 1464, 1465, 1466, 1467, 1468, 1469, 1470, 1471, 1472, 1473, 1474, 1475, 1476, 1477, 1478, 1479, 1480, 1481, 1482, 1483, 1484, 1485, 1486, 1487, 1488, 1489, 1490, 1491, 1492, 1493, 1494, 1495, 1496, 1497, 1498, 1499, 1500, 1501, 1502, 1503, 1504, 1505, 1506, 1507, 1508, 1509, 1510, 1511, 1512, 1513, 1514, 1515, 1516, 1517, 1518, 1519, 1520, 1521, 1522, 1523, 1524, 1525, 1526, 1527, 1528, 1529, 1530, 1531, 1532, 1533, 1534, 1535, 1536, 1537, 1538, 1539, 1540, 1541, 1542, 1543, 1544, 1545, 1546, 1547, 1548, 1549, 1550, 1551, 1552, 1553, 1554, 1555, 1556, 1557, 1558, 1559, 1560, 1561, 1562, 1563, 1564, 1565, 1566, 1567, 1568, 1569, 1570, 1571, 1572, 1573, 1574, 1575, 1576, 1577, 1578, 1579, 1580, 1581, 1582, 1583, 1584, 1585, 1586, 1587, 1588, 1589, 1590, 1591, 1592, 1593, 1594, 1595, 1596, 1597, 1598, 1599, 1600, 1601, 1602, 1603, 1604, 1605, 1606, 1607, 1608, 1609, 1610, 1611, 1612, 1613, 1614, 1615, 1616, 1617, 1618, 1619, 1620, 1621, 1622, 1623, 1624, 1625, 1626, 1627, 1628, 1629, 1630, 1631, 1632, 1633, 1634, 1635, 1636, 1637, 1638, 1639, 1640, 1641, 1642, 1643, 1644, 1645, 1646, 1647, 1648, 1649, 1650, 1651, 1652, 1653, 1654, 1655, 1656, 1657, 1658, 1659, 1660, 1661, 1662, 1663, 1664, 1665, 1666, 1667, 1668, 1669, 1670, 1671, 1672, 1673, 1674, 1675, 1676, 1677, 1678, 1679, 1680, 1681, 1682, 1683, 1684, 1685, 1686, 1687, 1688, 1689, 1690, 1691, 1692, 1693, 1694, 1695, 1696, 1697, 1698, 1699, 1700, 1701, 1702, 1703, 1704, 1705, 1706, 1707, 1708, 1709, 1710, 1711, 1712, 1713, 1714, 1715, 1716, 1717, 1718, 1719, 1720, 1721, 1722, 1723, 1724, 1725, 1726, 1727, 1728, 1729, 1730, 1731, 1732, 1733, 1734, 1735, 1736, 1737, 1738, 1739, 1740, 1741, 1742, 1743, 1744, 1745, 1746, 1747, 1748, 1749, 1750, 1751, 1752, 1753, 1754, 1755, 1756, 1757, 1758, 1759, 1760, 1761, 1762, 1763, 1764, 1765, 1766, 1767, 1768, 1769, 1770, 1771, 1772, 1773, 1774, 1775, 1776, 1777, 1778, 1779, 1780, 1781, 1782, 1783, 1784, 1785, 1786, 1787, 1788, 1789, 1790, 1791, 1792, 1793, 1794, 1795, 1796, 1797, 1798, 1799, 1800, 1801, 1802, 1803, 1804, 1805, 1806, 1807, 1808, 1809, 1810, 1811, 1812, 1813, 1814, 1815, 1816, 1817, 1818, 1819, 1820, 1821, 1822, 1823, 1824, 1825, 1826, 1827, 1828, 1829, 1830, 1831, 1832, 1833, 1834, 1835, 1836, 1837, 1838, 1839, 1840, 1841, 1842, 1843, 1844, 1845, 1846, 1847, 1848, 1849, 1850, 1851, 1852, 1853, 1854, 1855, 1856, 1857, 1858, 1859, 1860, 1861, 1862, 1863, 1864, 1865, 1866, 1867, 1868, 1869, 1870, 1871, 1872, 1873, 1874, 1875, 1876, 1877, 1878, 1879, 1880, 1881, 1882, 1883, 1884, 1885, 1886, 1887, 1888, 1889, 1890, 1891, 1892, 1893, 1894, 1895, 1896, 1897, 1898, 1899, 1900, 1901, 1902, 1903, 1904, 1905, 1906, 1907, 1908, 1909, 1910, 1911, 1912, 1913, 1914, 1915, 1916, 1917, 1918, 1919, 1920, 1921, 1922, 1923, 1924, 1925, 1926, 1927, 1928, 1929, 1930, 1931, 1932, 1933, 1934, 1935, 1936, 1937, 1938, 1939, 1940, 1941, 1942, 1943, 1944, 1945, 1946, 1947, 1948, 1949, 1950, 1951, 1952, 1953, 1954, 1955, 1956, 1957, 1958, 1959, 1960, 1961, 1962, 1963, 1964, 1965, 1966, 1967, 1968, 1969, 1970, 1971, 1972, 1973, 1974, 1975, 1976, 1977, 1978, 1979, 1980, 1981, 1982, 1983, 1984, 1985, 1986, 1987, 1988, 1989, 1990, 1991, 1992, 1993, 1994, 1995, 1996, 1997, 1998, 1999, 2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034, 2035, 2036, 2037, 2038, 2039, 2040, 2041, 2042, 2043, 2044, 2045, 2046, 2047, 2048, 2049, 2050, 2051, 2052, 2053, 2054, 2055, 2056, 2057, 2058, 2059, 2060, 2061, 2062, 2063, 2064, 2065, 2066, 2067, 2068, 2069, 2070, 2071, 2072, 2073, 2074, 2075, 2076, 2077, 2078, 2079, 2080, 2081, 2082, 2083, 2084, 2085, 2086, 2087, 2088, 2089, 2090, 2091, 2092, 2093, 2094, 2095, 2096, 2097, 2098, 2099, 2100, 2101, 2102, 2103, 2104, 2105, 2106, 2107, 2108, 2109, 2110, 2111, 2112, 2113, 2114, 2115, 2116, 2117, 2118, 2119, 2120, 2121, 2122, 2123, 2124, 2125, 2126, 2127, 2128, 2129, 2130, 2131, 2132, 2133, 2134, 2135, 2136, 2137, 2138, 2139, 2140, 2141, 2142, 2143, 2144, 2145, 2146, 2147, 2148, 2149, 2150, 2151, 2152, 2153, 2154, 2155, 2156, 2157, 2158, 2159, 2160, 2161, 2162, 2163, 2164, 2165, 2166, 2167, 2168, 2169, 2170, 2171, 2172, 2173, 2174, 2175, 2176, 2177, 2178, 2179, 2180, 2181, 2182, 2183, 2184, 2185, 2186, 2187, 2188, 2189, 2190, 2191, 2192, 2193, 2194, 2195, 2196, 2197, 2198, 2199, 2200, 2201, 2202, 2203, 2204, 2205, 2206, 2207, 2208, 2209, 2210, 2211, 2212, 2213, 2214, 2215, 2216, 2217, 2218, 2219, 2220, 2221, 2222, 2223, 2224, 2225, 2226, 2227, 2228, 2229, 2230, 2231, 2232, 2233, 2234, 2235, 2236, 2237, 2238, 2239, 2240, 2241, 2242, 2243, 2244, 2245, 2246, 2247, 2248, 2249, 2250, 2251, 2252, 2253, 2254, 2255, 2256, 2257, 2258, 2259, 2260, 2261, 2262, 2263, 2264, 2265, 2266, 2267, 2268, 2269, 2270, 2271, 2272, 2273, 2274, 2275, 2276, 2277, 2278, 2279, 2280, 2281, 2282, 2283, 2284, 2285, 2286, 2287, 2288, 2289, 2290, 2291, 2292, 2293, 2294, 2295, 2296, 2297, 2298, 2299, 2300, 2301, 2302, 2303, 2304, 2305, 2306, 2307, 2308, 2309, 2310, 2311, 2312, 2313, 2314, 2315, 2316, 2317, 2318, 2319, 2320, 2321, 2322, 2323, 2324, 2325, 2326, 2327, 2328, 2329, 2330, 2331, 2332, 2333, 2334, 2335, 2336, 2337, 2338, 2339, 2340, 2341, 2342, 2343, 2344, 2345, 2346, 2347, 2348, 2349, 2350, 2351, 2352, 2353, 2354, 2355, 2356, 2357, 2358, 2359, 2360, 2361, 2362, 2363, 2364, 2365, 2366, 2367, 2368, 2369, 2370, 2371, 2372, 2373, 2374, 2375, 2376, 2377, 2378, 2379, 2380, 2381, 2382, 2383, 2384, 2385, 2386, 2387, 2388, 2389, 2390, 2391, 2392, 2393, 2394, 2395, 2396, 2397, 2398, 2399, 2400, 2401, 2402, 2403, 2404, 2405, 2406, 2407, 2408, 2409, 2410, 2411, 2412, 2413, 2414, 2415, 2416, 2417, 2418, 2419, 2420, 2421, 2422, 2423, 2424, 2425, 2426, 2427, 2428, 2429, 2430, 2431, 2432, 2433, 2434, 2435, 2436, 2437, 2438, 2439, 2440, 2441, 2442, 2443, 2444, 2445, 2446, 2447, 2448, 2449, 2450, 2451, 2452, 2453, 2454, 2455, 2456, 2457, 2458, 2459, 2460, 2461, 2462, 2463, 2464, 2465, 2466, 2467, 2468, 2469, 2470, 2471, 2472, 2473, 2474, 2475, 2476, 2477, 2478, 2479, 2480, 2481, 2482, 2483, 2484, 2485, 2486, 2487, 2488, 2489, 2490, 2491, 2492, 2493, 2494, 2495, 2496, 2497, 2498, 2499, 2500, 2501, 2502, 2503, 2504, 2505, 2506, 2507, 2508, 2509, 2510, 2511, 2512, 2513, 2514, 2515, 2516, 2517, 2518, 2519, 2520, 2521, 2522, 2523, 2524, 2525, 2526, 2527, 2528, 2529, 2530, 2531, 2532, 2533, 2534, 2535, 2536, 2537, 2538, 2539, 2540, 2541, 2542, 2543, 2544, 2545, 2546, 2547, 2548, 2549, 2550, 2551, 2552, 2553, 2554, 2555, 2556, 2557, 2558, 2559, 2560, 2561, 2562, 2563, 2564, 2565, 2566, 2567, 2568, 2569, 2570, 2571, 2572, 2573, 2574, 2575, 2576, 2577, 2578, 2579, 2580, 2581, 2582, 2583, 2584, 2585, 2586, 2587, 2588, 2589, 2590, 2591, 2592, 2593, 2594, 2595, 2596, 2597, 2598, 2599, 2600, 2601, 2602, 2603, 2604, 2605, 2606, 2607, 2608, 2609, 2610, 2611, 2612, 2613, 2614, 2615, 2616, 2617, 2618, 2619, 2620, 2621, 2622, 2623, 2624, 2625, 2626, 2627, 2628, 2629, 2630, 2631, 2632, 2633, 2634, 2635, 2636, 2637, 2638, 2639, 2640, 2641, 2642, 2643, 2644, 2645, 2646, 2647, 2648, 2649, 2650, 2651, 2652, 2653, 2654, 2655, 2656, 2657, 2658, 2659, 2660, 2661, 2662, 2663, 2664, 2665, 2666, 2667, 2668, 2669, 2670, 2671, 2672, 2673, 2674, 2675, 2676, 2677, 2678, 2679, 2680, 2681, 2682, 2683, 2684, 2685, 2686, 2687, 2688, 2689, 2690, 2691, 2692, 2693, 2694, 2695, 2696, 2697, 2698, 2699, 2700, 2701, 2702, 2703, 2704, 2705, 2706, 2707, 2708, 2709, 2710, 2711, 2712, 2713, 2714, 2715, 2716, 2717, 2718, 2719, 2720, 2721, 2722, 2723, 2724, 2725, 2726, 2727, 2728, 2729, 2730, 2731, 2732, 2733, 2734, 2735, 2736, 2737, 2738, 2739, 2740, 2741, 2742, 2743, 2744, 2745, 2746, 2747, 2748, 2749, 2750, 2751, 2752, 2753, 2754, 2755, 2756, 2757, 2758, 2759, 2760, 2761, 2762, 2763, 2764, 2765, 2766, 2767, 2768, 2769, 2770, 2771, 2772, 2773, 2774, 2775, 2776, 2777, 2778, 2779, 2780, 2781, 2782, 2783, 2784, 2785, 2786, 2787, 2788, 2789, 2790, 2791, 2792, 2793, 2794, 2795, 2796, 2797, 2798, 2799, 2800, 2801, 2802, 2803, 2804, 2805, 2806, 2807, 2808, 2809, 2810, 2811, 2812, 2813, 2814, 2815, 2816, 2817, 2818, 2819, 2820, 2821, 2822, 2823, 2824, 2825, 2826, 2827, 2828, 2829, 2830, 2831, 2832, 2833, 2834, 2835, 2836, 2837, 2838, 2839, 2840, 2841, 2842, 2843, 2844, 2845, 2846, 2847, 2848, 2849, 2850, 2851, 2852, 2853, 2854, 2855, 2856, 2857, 2858, 2859, 2860, 2861, 2862, 2863, 2864, 2865, 2866, 2867, 2868, 2869, 2870, 2871, 2872, 2873, 2874, 2875, 2876, 2877, 2878, 2879, 2880, 2881, 2882, 2883, 2884, 2885, 2886, 2887, 2888, 2889, 2890, 2891, 2892, 2893, 2894, 2895, 2896, 2897, 2898, 2899, 2900, 2901, 2902, 2903, 2904, 2905, 2906, 2907, 2908, 2909, 2910, 2911, 2912, 2913, 2914, 2915, 2916, 2917, 2918, 2919, 2920, 2921, 2922, 2923, 2924, 2925, 2926, 2927, 2928, 2929, 2930, 2931, 2932, 2933, 2934, 2935, 2936, 2937, 2938, 2939, 2940, 2941, 2942, 2943, 2944, 2945, 2946, 2947, 2948, 2949, 2950, 2951, 2952, 2953, 2954, 2955, 2956, 2957, 2958, 2959, 2960, 2961, 2962, 2963, 2964, 2965, 2966, 2967, 2968, 2969, 2970, 2971, 2972, 2973, 2974, 2975, 2976, 2977, 2978, 2979, 2980, 2981, 2982, 2983, 2984, 2985, 2986, 2987, 2988, 2989, 2990, 2991, 2992, 2993, 2994, 2995, 2996, 2997, 2998, 2999", (), [4233]),
    ("hypothèse : annuler et valider",
     "fonction principal() { @2[0] = 7; @2[1] = 8; hypothèse { @2[0] = 100; @2[1] = 200; annuler; } sortie(@2[0]); sortie(@2[1]); "
     "hypothèse { @2[0] = 100; @2[1] = 200; } sortie(@2[0]); sortie(@2[1]); }",
     (), [7, 8, 100, 200]),
    ("hypothèse : condition, valider anticipé, appel de fonction",
     "fonction essayer(x) { hypothèse { @2[5] = x; si x > 10 { annuler; } @2[6] = x * 2; valider; } } "
     "fonction principal() { @2[5] = 1; @2[6] = 2; essayer(3); sortie(@2[5]); sortie(@2[6]); essayer(50); sortie(@2[5]); sortie(@2[6]); }",
     (), [3, 6, 3, 6]),
    ("hypothèse : imbriquées",
     "fonction principal() { @2[0] = 1; hypothèse { @2[0] = 2; hypothèse { @2[0] = 3; } sortie(@2[0]); annuler; } sortie(@2[0]); "
     "hypothèse { @2[0] = 5; hypothèse { @2[0] = 6; annuler; } sortie(@2[0]); } sortie(@2[0]); }",
     (), [3, 1, 5, 5]),
    ("hypothèse : tableaux, étage variable, boucle dans le bloc",
     "tableau t[4] @2[20]; fonction principal() { t[1] = 9; hypothèse { t[1] = 4; t[2] = 5; pour i dans 0..3 { @(1 + (i % 3))[7] = i + 40; } annuler; } "
     "sortie(t[1]); sortie(t[2]); sortie(@1[7] + @2[7] + @3[7]); }",
     (), [9, 0, 0]),
    ("littéral ADN",
     'fonction principal() { sortie(adn"ACGT"); sortie(adn"TTTTTTTTTTTTTTTT"); sortie(adn"U"); sortie(adn"gattaca"); }',
     (), [27, 4294967295, 3, 9156]),
    ("boucle en segments",
     "tableau t[10] @2[0]; fonction principal() { soit k = 3; pour i dans 0..10 en segments { soit x = i * k; t[i] = x + 1; } "
     "pour j dans 0..10 { sortie(t[j]); } pour i dans 5..5 en 16 segments { t[0] = 99; } sortie(t[0]); }",
     (), [1, 4, 7, 10, 13, 16, 19, 22, 25, 28, 1]),
    ("texte, caractères, tas et références",
     "structure P { v; suite: P; } fonction principal() { soit t = \"vtx\"; sortie(longueur(t)); sortie(car(t, 1)); "
     "sortie('\\n'); sortie(texte_egal(t, \"vtx\")); soit a: P = nouveau_de(P); a.v = 7; soit b: P = nouveau_de(P); "
     "b.v = 9; b.suite = a; sortie(b.suite.v + b.v); sortie(a.suite == nul); }",
     (), [3, 116, 10, 1, 16, 1]),
    ("construction de structures",
     "structure N { valeur, gauche: N, droite: N } fonction somme(n: N) { si n == nul { retour 0; } "
     "retour n.valeur + somme(n.gauche) + somme(n.droite); } fonction principal() { "
     "soit a = N { valeur: 1, gauche: N { valeur: 2 }, droite: N { valeur: 3, droite: N { valeur: 4 } } }; "
     "sortie(somme(a)); sortie(a.gauche.gauche == nul); soit b = N {}; sortie(b.valeur); }",
     (), [10, 1, 0]),
    ("logique à quatre valeurs",
     "fonction principal() { soit a: logique = vrai; soit b: logique = faux; soit c = fusion(a, b); "
     "selon c { variable { sortie(1); } autre { sortie(0); } } sortie(entier(anti(inconnu))); sortie(entier(et4(a, c))); "
     "sortie(entier(fusion(#00000002, #00000001))); sortie(vrai + faux); }",
     (), [1, 3, 3, 3, 1]),
    ("segments cumulant un tableau",
     "tableau h[4] @2[0]; fonction principal() { h[1] = 100; pour i dans 0..20 en 3 segments cumulant h { "
     "soit c = i % 4; h[c] = h[c] + i; } pour j dans 0..4 { sortie(h[j]); } }",
     (), [40, 145, 50, 55]),
    ("division par zéro, moins unaire, priorité",
     "fonction principal() { sortie(5 / 0); sortie(5 % 0); sortie(-1); sortie(6 & 3 == 2); }",
     (), [4294967295, 5, 4294967295, 1]),
]

ERREURS = [
    ("champ inconnu dans une construction", "structure P { v } fonction principal() { soit a = P { w: 1 }; }"),
    ("champ donné deux fois", "structure P { v } fonction principal() { soit a = P { v: 1, v: 2 }; }"),
    ("champ inconnu d'une référence", "structure P { v; } fonction principal() { soit a: P = nouveau_de(P); sortie(a.w); }"),
    ("arithmétique sur une référence", "structure P { v; } fonction principal() { soit a: P = nouveau_de(P); sortie(a + 1); }"),
    ("entier rangé dans une référence", "structure P { v; } fonction principal() { soit a: P = 5; }"),
    ("références de structures différentes", "structure P { v; } structure Q { w; } fonction principal() { "
     "soit a: P = nouveau_de(P); soit b: Q = nouveau_de(Q); sortie(a == b); }"),
    ("logique comme condition", "fonction principal() { soit p: logique = vrai; si p { sortie(1); } }"),
    ("tableau cumulé écrit autrement que par addition",
     "tableau h[4] @2[0]; fonction principal() { pour i dans 0..8 en segments cumulant h { h[i % 4] = i; } }"),
    ("variable inconnue", "fonction principal() { sortie(x); }"),
    ("variable au nom d'une constante", "constante K = 3; fonction principal() { soit K = 5; sortie(K); }"),
    ("variable au nom d'une valeur logique", "fonction principal() { soit faux = 0; sortie(faux); }"),
    ("paramètre au nom d'une valeur logique", "fonction f(vrai) { retour vrai; } fonction principal() { sortie(f(4)); }"),
    ("boucle sur un nom de constante", "constante N = 4; fonction principal() { pour N dans 0..3 { sortie(N); } }"),
    ("fonction inconnue", "fonction principal() { f(1); }"),
    ("mauvais nombre d'arguments", "fonction f(a) { retour a; } fonction principal() { f(1, 2); }"),
    ("principal absente", "fonction f() { retour 1; }"),
    ("variable déjà déclarée", "fonction principal() { soit a = 1; soit a = 2; }"),
    ("syntaxe : point-virgule manquant", "fonction principal() { soit a = 1 }"),
    ("nombre trop grand", "fonction principal() { sortie(4294967296); }"),
    ("constante non constante", "constante A = 1 + x; fonction principal() { }"),
    ("étage invalide", "fonction principal() { @5[0] = 1; }"),
    ("arrêter hors d'une boucle", "fonction principal() { arrêter; }"),
    ("annuler hors d'une hypothèse", "fonction principal() { annuler; }"),
    ("retour dans une hypothèse", "fonction principal() { hypothèse { retour 1; } }"),
    ("écriture étage 0 dans une hypothèse", "fonction principal() { hypothèse { @0[5] = 1; } }"),
    ("arrêter sort d'une hypothèse", "fonction principal() { pour i dans 0..3 { hypothèse { arrêter; } } }"),
    ("annuler dans une boucle de l'hypothèse", "fonction principal() { hypothèse { pour i dans 0..3 { annuler; } } }"),
    ("littéral ADN trop long", 'fonction principal() { sortie(adn"' + "ACGT" * 16 + 'A"); }'),
    ("segment qui modifie une variable extérieure", "fonction principal() { soit s = 0; pour i dans 0..8 en segments { s = s + i; } }"),
    ("retour dans un segment", "fonction principal() { pour i dans 0..8 en segments { retour; } }"),
    ("arrêter dans un segment", "fonction principal() { pour i dans 0..8 en segments { arrêter; } }"),
    ("hypothèse dans un segment", "fonction principal() { pour i dans 0..8 en segments { hypothèse { @2[i] = 1; } } }"),
    ("trop de segments", "fonction principal() { pour i dans 0..8 en 65 segments { } }"),
    ("indice hors du tableau", "tableau v[4] @2[0]; fonction principal() { v[9] = 1; }"),
    ("champ inconnu", "structure P { x; } tableau t[2] de P @2[0]; fonction principal() { t[0].z = 1; }"),
    ("structure inconnue", "tableau t[2] de Q @2[0]; fonction principal() { }"),
]


def interp_reference(a, b, c, d, u, v):
    out = 0
    for s in (24, 16, 8, 0):
        va, vb, vc, vd = [(x >> s) & 255 for x in (a, b, c, d)]
        w = ((256 - u) * (256 - v) * va + u * (256 - v) * vb + (256 - u) * v * vc + u * v * vd) >> 16
        out |= (w & 255) << s
    return out


def tests():
    ok = 0
    for nom, src, entrees, attendu in TESTS:
        try:
            cpu, _, mots = executer(src, entrees)
            if attendu is None:
                coins = (0x00102030, 0xFF8040C0, 0x10203040, 0x80FF00FF)
                attendu = [interp_reference(*coins, 64, 192), interp_reference(*coins, 0, 0),
                           interp_reference(*coins, 256, 256)]
            statut = cpu.sortie == attendu
            print(f"{'OK ' if statut else 'ÉCHEC'}  {nom}  ({len(mots)} mots, {cpu.pas} pas)")
            if not statut:
                print(f"      obtenu  : {cpu.sortie}\n      attendu : {attendu}")
            ok += statut
        except VtxError as e:
            print(f"ÉCHEC  {nom} : {e}")
    for nom, src in ERREURS:
        try:
            executer(src)
            print(f"ÉCHEC  erreur non détectée : {nom}")
        except VtxError as e:
            print(f"OK   erreur détectée : {nom} -> {e}")
            ok += 1
    import tempfile
    extra = []
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "outil.vtx"), "w", encoding="utf-8").write("fonction double(x) { retour x + x; }\n")
        try:
            cpu, _, _ = executer('importer "outil.vtx";\nfonction principal() { sortie(double(21)); }', dossier=d)
            extra.append(("importer un fichier", cpu.sortie == [42]))
        except VtxError as e:
            extra.append((f"importer un fichier ({e})", False))
    _, _, mots = executer("donnees @1[0] = { %s }; fonction principal() { sortie(1); }" % ", ".join(str(i) for i in range(3000)))
    extra.append((f"3 000 données tiennent en {len(mots)} mots (moins de 3 200)", len(mots) < 3200))
    for nom, bon in extra:
        print(f"{'OK ' if bon else 'ÉCHEC'}  {nom}")
        ok += bon
    total = len(TESTS) + len(ERREURS) + len(extra)
    print(f"\n{ok}/{total} tests réussis")
    return ok == total


def profil(cpu, mots):
    n = cpu.pas
    print(f"{len(mots)} mots, {n} instructions exécutées")
    g = cpu.ops.get(0x38, 0)
    print(f"GDOT : {g} ({100 * g / n:.1f} % des instructions)" if n else "")
    print(f"lectures par étage : {cpu.ld} · écritures par étage : {cpu.st}")
    print("instructions les plus fréquentes :")
    for op, c in cpu.ops.most_common(8):
        print(f"  {NOMS.get(op, '?'):6s} {c:8d}  {100 * c / n:5.1f} %")


def desassembler(cpu):
    """Une instruction lisible à l'adresse courante : adresse, mot, nom, opérandes."""
    w = cpu.mem.get((0, cpu.pc), 0)
    op, g, b, a = w >> 24, (w >> 16) & 255, (w >> 8) & 255, w & 255
    nom = NOMS.get(op, f"?{op:02X}")
    rd, rs, rt = g >> 4, g & 15, b >> 4
    if nom in ("JMP", "JZ", "JNZ", "JC", "JNC", "CALL"):
        ops = f"@{((w & 15) << 16) | (g << 8) | b:04X}"
    elif nom == "LDI":
        ops = f"R{rd}, #{cpu.mem.get((0, cpu.pc + 1), 0):08X}"
    elif nom in ("LD", "ST"):
        ops = f"R{rd}, R{rs}, @{a >> 6}"
    elif nom in ("LDQ", "STQ"):
        ops = f"R{rd}, R{rs}, R{rt}, @{a >> 6}"
    elif nom in ("ADDI", "SUBI"):
        ops = f"R{rd}, R{rs}, #{b}"
    elif nom in ("LDF", "STF"):
        ops = f"R{rd}, #{b - 256 if b > 127 else b}"
    elif nom in ("HALT", "NOP", "RET", "GEMV"):
        ops = ""
    else:
        ops = f"R{rd}, R{rs}, R{rt}"
    return f"{cpu.pc:04X}  #{w:08X}  {nom:5s} {ops}"


def tracer(src, entrees, dossier, de=0, maxl=200, arret=None, regs=False):
    """Débogueur : exécute le programme et affiche une ligne par instruction (à partir du pas `de`, au plus `maxl` lignes).
    S'arrête et montre l'état quand le compteur ordinal atteint `arret`."""
    asm = compiler(src, dossier=dossier)
    mots = assembler(asm)
    cpu = CPU()
    cpu.charger(mots)
    cpu.entree.extend(entrees)
    etat = {"lignes": 0}

    def montre(c):
        ligne = f"{c.pas:7d}  {desassembler(c)}"
        if regs:
            ligne += "   " + " ".join(f"R{i}={v:X}" for i, v in enumerate(c.r) if v and i not in (14,))
            ligne += f"   Z={int(c.z)} C={int(c.c)}"
        return ligne

    def crochet(c):
        if arret is not None and c.pc == arret:
            print("--- arrêt à l'adresse demandée ---")
            print(montre(c).replace("   ", "\n  ", 1) if not regs else montre(c))
            print("registres :", " ".join(f"R{i}={v:X}" for i, v in enumerate(c.r) if v), f"  pile : {STACK_TOP - c.r[14]} mots")
            return True
        if c.pas >= de and etat["lignes"] < maxl:
            print(montre(c))
            etat["lignes"] += 1
            if etat["lignes"] == maxl:
                print(f"... ({maxl} lignes affichées, l'exécution continue sans affichage)")
        return False

    cpu.sur_pas = crochet
    cpu.executer(50_000_000)
    print(f"fin : {cpu.pas} instructions, sorties : {cpu.sortie}")
    return cpu


class Debogueur:
    """Débogueur au niveau du source : pas à pas, pas par-dessus les appels, sortie de fonction, points d'arrêt par ligne,
    lecture des variables (entier, flottant, long), pile d'appels et mémoire. S'utilise en ligne de commande
    (`vtx.py deboguer`) ou depuis Python (méthodes pas, suivant, sortir, continuer, voir, pile)."""

    def __init__(self, src, entrees=(), dossier=None, nom="programme", max_pas=50_000_000):
        global REGISTRES
        ancien, REGISTRES = REGISTRES, False      # le débogueur lit les variables dans le cadre
        try:
            asm, self.carte, self.texte = compiler_complet(src, dossier=dossier, nom=nom)
        finally:
            REGISTRES = ancien
        mots, infos, self.etiquettes = _assembler(asm)
        self.nom, self.max_pas = nom, max_pas
        self.cpu = CPU()
        self.cpu.charger(mots)
        self.cpu.entree.extend(entrees)
        self.debut = {}                        # adresse -> (ligne du texte assemblé, prélude ?)
        self.fonctions = []                    # (adresse, nom, origine, variables {nom: (décalage, type, haut)})
        prelude = PRELUDE.split("\n")
        courante = None
        for adr, d in infos:
            t = d.split()
            if t[0].upper() == ".FONCTION":
                courante = (adr, t[1], t[2] if t[2] != "-" else "", {})
                self.fonctions.append(courante)
            elif t[0].upper() == ".VAR" and courante:
                courante[3][t[1]] = (int(t[2]), t[3], int(t[4]))
            elif t[0].upper() == ".LIGNE" and adr not in self.debut:
                self.debut[adr] = (int(t[1]), bool(courante and courante[2] == "prélude"))
        self.fonctions.sort()
        self.adr_f = [f[0] for f in self.fonctions]
        self.debuts = sorted(self.debut)
        self.prelude = prelude
        self.arrets = set()
        self.vues = 0

    # ------------------------------------------------------------ localisation
    def lieu(self, adr):
        """(fichier, ligne, texte) d'une adresse de début d'instruction source."""
        n, pre = self.debut[adr]
        if pre:
            return "prélude", n, self.prelude[n - 1].strip() if n <= len(self.prelude) else ""
        f, l = self.carte[n - 1] if n <= len(self.carte) else (self.nom, n)
        return f, l, self.texte[n - 1].strip() if n <= len(self.texte) else ""

    def fonction_de(self, pc):
        i = bisect.bisect_right(self.adr_f, pc) - 1
        return self.fonctions[i] if i >= 0 else None

    def instruction_de(self, adr):
        """Début de l'instruction source qui contient l'adresse (pour une adresse de retour)."""
        f = self.fonction_de(adr)
        i = bisect.bisect_right(self.debuts, adr - 1) - 1
        if i >= 0 and f and self.debuts[i] >= f[0]:
            return self.debuts[i]
        return None

    def ici_brut(self):
        d = self.instruction_de(self.cpu.pc + 1)
        return self.ici() if self.cpu.pc in self.debut or d is None else "{}, ligne {}".format(*self.lieu(d)[:2])

    def ici(self):
        if self.cpu.halted:
            return f"fin du programme après {self.cpu.pas} instructions"
        if self.cpu.pc not in self.debut:
            return f"adresse {self.cpu.pc:04X} (hors du source)"
        f, l, t = self.lieu(self.cpu.pc)
        fn = self.fonction_de(self.cpu.pc)
        return f"{f}, ligne {l} (dans {fn[1] if fn else '?'}) : {t}"

    # ------------------------------------------------------------ exécution
    def _avance(self, condition):
        cpu = self.cpu
        depart = cpu.pas
        while not cpu.halted:
            if cpu.pas - depart >= self.max_pas:
                raise VtxError(f"{self.max_pas} instructions sans atteindre l'arrêt demandé (boucle infinie ?) ; arrêté à : {self.ici_brut()}")
            cpu.pas_unique()
            if cpu.pc in self.debut and not self.debut[cpu.pc][1] and condition(cpu.pc):
                return True
        return False

    def demarrer(self):
        """Va jusqu'à la première instruction du programme."""
        return self._avance(lambda pc: True)

    def pas(self):
        """Instruction source suivante, en entrant dans les fonctions appelées (le prélude est traversé sans arrêt)."""
        return self._avance(lambda pc: True)

    def suivant(self):
        """Instruction source suivante dans la même fonction, sans entrer dans les appels."""
        cadre = self.cpu.r[13]
        return self._avance(lambda pc: self.cpu.r[13] >= cadre)

    def sortir(self):
        """Termine la fonction en cours et s'arrête dans l'appelant."""
        cadre = self.cpu.r[13]
        return self._avance(lambda pc: self.cpu.r[13] > cadre)

    def continuer(self):
        """Jusqu'au prochain point d'arrêt ou la fin."""
        return self._avance(lambda pc: pc in self.arrets)

    def arreter_a(self, ligne, fichier=None):
        """Pose un point d'arrêt ; rend le nombre d'adresses concernées (0 si aucune instruction à cette ligne)."""
        fichier = fichier or self.nom
        adr = [a for a, (n, pre) in self.debut.items() if not pre and self.carte[n - 1] == (fichier, ligne)]
        self.arrets.update(adr)
        return len(adr)

    def enlever(self, ligne, fichier=None):
        fichier = fichier or self.nom
        avant = len(self.arrets)
        self.arrets = {a for a in self.arrets if self.debut[a][1] or self.carte[self.debut[a][0] - 1] != (fichier, ligne)}
        return avant - len(self.arrets)

    # ------------------------------------------------------------ lecture de l'état
    def valeur(self, nom, cadre=None, fonction=None):
        """Valeur d'une variable de la fonction en cours (ou du cadre donné) : (texte, valeur brute)."""
        fn = fonction or self.fonction_de(self.cpu.pc)
        cadre = self.cpu.r[13] if cadre is None else cadre
        if not fn or nom not in fn[3]:
            raise VtxError(f"variable « {nom} » inconnue ici")
        off, t, haut = fn[3][nom]
        lit = lambda o: self.cpu.mem.get((0, (cadre + o) & 0xFFFFFF), 0)
        v = lit(off)
        if t == "f":
            x = f32(v)
            return f"{x!r} (flottant, #{v:08X})", x
        if t == "l":
            w = (lit(haut) << 32) | v
            sv = w - 2 ** 64 if w >= 2 ** 63 else w
            return f"{sv} (long, #{w:016X})", sv
        if t == "d":
            w = (lit(haut) << 32) | v
            x = f64(v, w >> 32)
            return f"{x!r} (flottant_64, #{w:016X})", x
        if t == "w":
            w = (lit(off - 3) << 96) | (lit(off - 2) << 64) | (lit(haut) << 32) | v
            sv = w - 2 ** 128 if w >= 2 ** 127 else w
            return f"{sv} (entier_128, #{w:032X})", sv
        if t == "x":
            w = (lit(off - 3) << 96) | (lit(off - 2) << 64) | (lit(haut) << 32) | v
            et, val = petuar_valeur(w)
            pts = "_".join(f"{(w >> (32 * k)) & MASK:08X}" for k in (3, 2, 1, 0))
            adn = "".join("ACGT"[(w >> (2 * (63 - i))) & 3] for i in range(64))
            if val is None:
                nom = {0: "inconnu", 3: "variable"}.get(et, "-inf" if et == 1 else "inf")
                return f"{nom} (flottant_petuar, #{pts}, {adn})", nom
            return f"{float(val)!r} (flottant_petuar, #{pts}, {adn})", val
        if t == "q":
            return f"{NOM_LOGIQUE.get(v & 3, '?')} (logique, code {v})", v
        sv = v - 2 ** 32 if v >= 2 ** 31 else v
        signe = f", signé {sv}" if sv < 0 else ""
        return f"{v} (#{v:08X}{signe})", v

    def variables(self):
        fn = self.fonction_de(self.cpu.pc)
        if not fn:
            return []
        return [(n, self.valeur(n)[0]) for n in sorted(fn[3], key=lambda n: -fn[3][n][0]) if not n.startswith("__")]

    def pile(self):
        """Pile d'appels, de la fonction en cours jusqu'à principal : (fonction, fichier, ligne)."""
        cpu, cadres = self.cpu, []
        pc, r13 = cpu.pc, cpu.r[13]
        for _ in range(256):
            fn = self.fonction_de(pc)
            debut = pc if pc in self.debut else self.instruction_de(pc)
            f, l, _t = self.lieu(debut) if debut is not None else ("?", 0, "")
            cadres.append((fn[1] if fn else "?", f, l))
            if not fn or fn[1] == "principal":
                break
            pc, r13 = cpu.mem.get((0, (r13 + 1) & 0xFFFFFF), 0), cpu.mem.get((0, r13), 0)
        return cadres

    def memoire(self, etage, adr, n=8):
        return [self.cpu.mem.get((etage, (adr + k) & 0xFFFFFF), 0) for k in range(n)]


AIDE_DEBOGUEUR = """Commandes :
  p, pas              instruction suivante (entre dans les fonctions)
  s, suivant          instruction suivante sans entrer dans les appels
  f, sortir           termine la fonction en cours
  c, continuer        jusqu'au prochain point d'arrêt
  a, arrêt LIGNE      point d'arrêt (ou arrêt fichier.vtx:LIGNE pour un fichier importé)
  e, enlever LIGNE    retire un point d'arrêt
  v, voir NOM         valeur d'une variable          vars, variables   toutes les variables
  pile                pile d'appels                  mem @E[A] [N]     N mots de l'étage E à partir de A
  regs, registres     registres et drapeaux          où                emplacement actuel
  sorties             valeurs sorties jusqu'ici      q, quitter        fin"""


def deboguer(src, entrees, dossier, nom, commandes):
    """Boucle interactive ; `commandes` est un itérable de lignes (l'entrée standard en usage normal)."""
    d = Debogueur(src, entrees, dossier, nom)
    d.demarrer()
    print(AIDE_DEBOGUEUR.split("\n")[0] + " (tapez « aide »)")
    print("→", d.ici())
    vues = 0
    for brute in commandes:
        ligne = brute.strip()
        if not ligne:
            continue
        print(f"(vtx) {ligne}")
        mots_c = ligne.split()
        c, args = mots_c[0], mots_c[1:]
        try:
            if c in ("q", "quitter"):
                break
            elif c == "aide":
                print(AIDE_DEBOGUEUR)
            elif c in ("p", "pas", "s", "suivant", "f", "sortir", "c", "continuer"):
                {"p": d.pas, "pas": d.pas, "s": d.suivant, "suivant": d.suivant, "f": d.sortir, "sortir": d.sortir,
                 "c": d.continuer, "continuer": d.continuer}[c]()
                if len(d.cpu.sortie) > vues:
                    print("  sortie :", ", ".join(str(v) for v in d.cpu.sortie[vues:]))
                    vues = len(d.cpu.sortie)
                print("→", d.ici())
            elif c in ("a", "arrêt", "arret", "e", "enlever"):
                cible = args[0]
                fichier, l = (cible.rsplit(":", 1) if ":" in cible else (None, cible))
                if c in ("e", "enlever"):
                    print(f"  {d.enlever(int(l), fichier)} point(s) d'arrêt retiré(s)")
                else:
                    n = d.arreter_a(int(l), fichier)
                    print(f"  point d'arrêt à la ligne {l}" + (f" de {fichier}" if fichier else "") if n else
                          f"  aucune instruction à la ligne {l}")
            elif c in ("v", "voir"):
                print(f"  {args[0]} = {d.valeur(args[0])[0]}")
            elif c in ("vars", "variables"):
                for n_, v in d.variables():
                    print(f"  {n_} = {v}")
            elif c == "pile":
                for i, (fn, f, l) in enumerate(d.pile()):
                    print(f"  #{i} {fn}  ({f}, ligne {l})")
            elif c == "mem":
                m = re.fullmatch(r"@(\d)\[(\d+)\]", args[0])
                n = int(args[1]) if len(args) > 1 else 8
                e, a = int(m.group(1)), int(m.group(2))
                print("  " + " ".join(f"#{w:08X}" for w in d.memoire(e, a, n)))
            elif c in ("regs", "registres"):
                print("  " + " ".join(f"R{i}={v:X}" for i, v in enumerate(d.cpu.r)) + f"  Z={int(d.cpu.z)} C={int(d.cpu.c)}")
            elif c in ("où", "ou"):
                print("→", d.ici())
            elif c == "sorties":
                print("  ", d.cpu.sortie)
            else:
                print("  commande inconnue (tapez « aide »)")
        except (VtxError, IndexError, ValueError, AttributeError) as ex:
            print(f"  erreur : {ex}")
    return d



def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]
    if cmd == "test":
        sys.exit(0 if tests() else 1)
    if len(sys.argv) < 3:
        print(__doc__)
        return
    try:
        src = open(sys.argv[2], encoding="utf-8").read()
        dossier = os.path.dirname(os.path.abspath(sys.argv[2]))
        if cmd == "compile":
            print(compiler(src, dossier=dossier), end="")
        elif cmd == "asm":
            mots = assembler(compiler(src, dossier=dossier))
            litteral = False
            for i, w in enumerate(mots):
                if litteral:
                    print(f"{i:04X}  #{w:08X}  {quits(w)}  (littéral)")
                    litteral = False
                    continue
                nom = NOMS.get(w >> 24, "?")
                print(f"{i:04X}  #{w:08X}  {quits(w)}  {nom}")
                litteral = nom == "LDI"
        elif cmd == "exporter":
            # programme pour la machine Rust : « mots;entrées;table des accords » (vtx-spu lancer FICHIER)
            mots, table = exporter(src, dossier)
            print(",".join(map(str, mots)) + ";" + ",".join(sys.argv[3:]) + ";" + ",".join(map(str, table)))
        elif cmd == "partition":
            _a, carte, _l = compiler_complet(src, dossier=dossier, nom=os.path.basename(sys.argv[2]))
            print(partition_texte(DERNIERE_PARTITION["accords"], DERNIERE_PARTITION["notes"], carte)
                  or "aucun accord : pas de suite d'appels de tâches")
            if DERNIERE_PARTITION["accords"]:
                args = sys.argv[3:]
                laisser = CŒURS_LAISSES
                if "--laisser" in args:
                    k = args.index("--laisser")
                    laisser = int(args[k + 1])
                    del args[k:k + 2]
                cyl = cylindres_machine(laisser)
                if "--cylindres" in args:
                    k = args.index("--cylindres")
                    cyl = int(args[k + 1])
                    del args[k:k + 2]
                b = jouer(src, [int(x, 0) for x in args], dossier, canaux=(None, cyl))
                print(f"exécution : {b['total']:,} instructions ; dans les accords : {b['seq']:,} en séquence, "
                      f"{b['par'][cyl]:,} sur {cyl} cylindres (gain {b['seq'] / max(1, b['par'][cyl]):.2f}), "
                      f"{b['par'][None]:,} avec autant de cylindres que de tâches ({b['executions']} exécution(s) d'accords)")
                for v in b["sortie"]:
                    print(f"sortie : {v}  (#{v:08X})")
        elif cmd == "deboguer":
            deboguer(src, [int(x, 0) for x in sys.argv[3:]], dossier, os.path.basename(sys.argv[2]), sys.stdin)
        elif cmd == "trace":
            args = sys.argv[3:]
            opt = {"--de": 0, "--max": 200, "--arret": None}
            entrees, regs, i = [], False, 0
            while i < len(args):
                if args[i] == "--regs":
                    regs = True
                elif args[i] in opt:
                    opt[args[i]] = int(args[i + 1], 0)
                    i += 1
                else:
                    entrees.append(int(args[i], 0))
                i += 1
            tracer(src, entrees, dossier, opt["--de"], opt["--max"], opt["--arret"], regs)
        elif cmd in ("run", "profil"):
            cpu, _, mots = executer(src, [int(x, 0) for x in sys.argv[3:]], dossier=dossier)
            if cmd == "profil":
                profil(cpu, mots)
            else:
                print(f"{len(mots)} mots, {cpu.pas} instructions exécutées")
            for v in cpu.sortie:
                print(f"sortie : {v}  (#{v:08X})")
            if cpu.texte:
                print("".join(chr(c & 0x1FFFFF) for c in cpu.texte), end="")
        else:
            print(__doc__)
    except VtxError as e:
        print(f"erreur : {e}", file=sys.stderr)
        m = re.match(r"ligne (\d+)", str(e))
        if m:
            lignes = open(sys.argv[2], encoding="utf-8").read().splitlines()
            if 1 <= int(m.group(1)) <= len(lignes):
                print(f"    {lignes[int(m.group(1)) - 1].strip()}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
