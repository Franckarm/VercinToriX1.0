#!/usr/bin/env python3
"""Lugus (le SPU-128) : la machine de référence en Python, vérifiée par morceaux.

 1. Le flottant de 128 bits de la machine (format Q128 de qflot) donne exactement les résultats du flottant_petuar,
    tel que le prélude des SPU-32 et SPU-64 le calcule (référence : tests/ref_petuar.py) : + − × ÷, racine, comparaison,
    échange avec le binary128 de l'IEEE.
 2. Les instructions, programme par programme : la largeur (128, 64, 32 bits), les deux instructions par mot, LDI et
    LDIH, les sauts et les appels en demi-mots, le quaternaire sur 64 quits (64 bases d'ADN d'un coup), les voies, la
    matière (codons, mélange, anti-point), les flottants aux trois largeurs et leurs conversions.
 3. Le brin (un mot ADN refuse d'être réécrit), les cubes sur disque avec leur anti-cube et leur ombre (une avarie est
    réparée, etat_disque() dit « faux »)."""
import os
import random
import shutil
import struct
import sys
import tempfile

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, ici)
sys.path.insert(0, os.path.join(racine, "tests"))
import spu128 as S  # noqa: E402
from qflot import Q32, Q64, Q128, vers_ieee, de_ieee  # noqa: E402
import ref_petuar as P  # noqa: E402

echecs = []


def verifier(nom, ok, detail=""):
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok or not detail else " : " + str(detail)), flush=True)
    if not ok:
        echecs.append(nom)


# --- 1. le flottant de 128 bits contre la référence du flottant_petuar
g = random.Random(128)
N = 1500
faux = 0
for _ in range(N):
    a, b = P.hasard(g), P.hasard(g)
    for nom, x, y in (("add", Q128.add(a, b), P.add(a, b)), ("sub", Q128.sub(a, b), P.sub(a, b)),
                      ("mul", Q128.mul(a, b), P.mul(a, b)), ("div", Q128.div(a, b), P.div(a, b)),
                      ("racine", Q128.racine(a), P.racine(a)), ("cmp", Q128.cmp(a, b), P.cmp(a, b)),
                      ("ieee", vers_ieee(Q128, a, 128), P.vers_ieee(a))):
        if x != y:
            faux += 1
verifier(f"1. flottant de 128 bits = flottant_petuar du prélude : {N} paires, 7 opérations, {faux} écart(s)", faux == 0)


# --- 2. les instructions
def lancer(asm, entrees=()):
    cpu = S.CPU()
    cpu.charger(S.assembler(asm))
    cpu.entree.extend(entrees)
    cpu.executer(1_000_000)
    return cpu


M128, M64, M32 = (1 << 128) - 1, (1 << 64) - 1, (1 << 32) - 1
c = lancer("""
    LDIS R1, -1
    ADD R2, R1, R1          ; 128 bits : -2
    OUT R2
    ADD.64 R3, R1, R1       ; 64 bits : 2^64 - 2, retenue
    OUT R3
    JC a
    OUT R0
a:  ADD.32 R4, R1, R1
    OUT R4
    LDIS R5, 5
    SUB.64 R6, R0, R5       ; -5 sur 64 bits
    OUT R6
    SEXT.64 R7, R6          ; -5 sur 128 bits
    OUT R7
    DIVS.64 R8, R6, R5      ; -1
    OUT R8
    SAR.64 R9, R6, R5       ; -5 >> 5 = -1 (64 bits)
    OUT R9
    HALT
""")
att = [M128 - 1, M64 - 1, M32 - 1, (1 << 64) - 5, M128 - 4, M64, M64]
verifier("2a. largeurs 128, 64, 32 (retenue, signes, extension)", c.sortie == att, (c.sortie, att))

c = lancer("""
    LDI R1, 0xFEDCBA9876543210
    LDIH R1, 0x0123456789ABCDEF
    OUT R1
    LDI128 R2, 0xAAAA0000BBBB1111CCCC2222DDDD3333
    OUT R2
    CALL f
    OUT R3
    CALL f
    OUT R3
    HALT
f:  ADDI R3, R3, 1
    RET
""")
verifier("2b. LDI, LDIH, constantes de 128 bits, appels en demi-mots",
         c.sortie == [0x0123456789ABCDEFFEDCBA9876543210, 0xAAAA0000BBBB1111CCCC2222DDDD3333, 1, 2], c.sortie)
code = S.assembler("NOP\nHALT")
verifier("2c. deux instructions par mot (NOP en haut, HALT en bas)", code == [(0 << 64) | (0x3F << 48)], code)

adn = lambda t: sum("ACGT".index(ch) << (2 * (len(t) - 1 - i)) for i, ch in enumerate(t))
brin_a = "GATTACA" * 8 + "ACGTACGT"
brin_b = "GATTACA" * 7 + "GATTCCA" + "ACGTTCGC"
c = lancer(f"""
    LDI128 R1, {adn(brin_a)}
    LDI128 R2, {adn(brin_b)}
    QEGAL R3, R1, R2
    COMPTE R4, R3
    OUT R4
    QEGAL.64 R5, R1, R2
    COMPTE R6, R5
    OUT R6
    HALT
""")
egales = sum(x == y for x, y in zip(brin_a, brin_b))
egales32 = sum(x == y for x, y in zip(brin_a[-32:], brin_b[-32:]))
verifier(f"2d. 64 bases d'ADN comparées d'un coup : {egales} égales sur 64", c.sortie == [egales, egales32], (c.sortie, egales, egales32))

point = (0x40000000 << 96) | (0x80000000 << 64) | (0xC0000000 << 32) | (2 << 30) | (10 << 24) | (20 << 18) | (30 << 12) | (40 << 6) | 50
autre = (0xC0000000 << 96) | (0x00000000 << 64) | (0x40000000 << 32) | (1 << 30) | (50 << 24) | (40 << 18) | (30 << 12) | (20 << 6) | 10
c = lancer(f"""
    LDI128 R1, {point}
    LDI128 R2, {autre}
    LDIU R3, 0
    MATL R4, R1, R3         ; l'état : vrai (2)
    OUT R4
    LDIU R3, 4
    MATL R4, R1, R3         ; la profondeur : 40
    OUT R4
    LDIU R5, 63
    MATE R6, R1, R5, 2      ; la lumière à 63
    LDIU R3, 2
    MATL R4, R6, R3
    OUT R4
    MELANGE R7, R1, R2, 128 ; moitié, moitié
    OUT R7
    ANTIPOINT R8, R1
    OUT R8
    VEXT R9, R1, R3         ; la voie 2 : le vert
    OUT R9
    HALT
""")
moy = lambda x, y: (x * 128 + y * 128) >> 8
melange = (moy(0x40000000, 0xC0000000) << 96) | (moy(0x80000000, 0) << 64) | (moy(0xC0000000, 0x40000000) << 32) | \
          (3 << 30) | (moy(10, 50) << 24) | (moy(20, 40) << 18) | (moy(30, 30) << 12) | (moy(40, 20) << 6) | moy(50, 10)
anti = (0xBFFFFFFF << 96) | (0x7FFFFFFF << 64) | (0x3FFFFFFF << 32) | (point & M32)
att = [2, 40, 63, melange, anti, 0x80000000]
verifier("2e. la matière : codons, mélange (l'état par la fusion de Belnap : vrai et faux donnent variable), anti-point",
         c.sortie == att, [hex(x) for x in c.sortie])

un = Q32.depuis(1)
deux = Q32.depuis(2)
c = lancer(f"""
    LDIU R1, {un}
    VBCAST R2, R1           ; 1 dans les quatre voies
    LDIU R3, {deux}
    VBCAST R4, R3
    VFADD R5, R2, R4        ; 3 dans les quatre voies
    OUT R5
    LDIU R6, 7
    VBCAST R7, R6
    GDOT R8, R7, R7         ; 4 × 49
    OUT R8
    HALT
""")
trois = Q32.depuis(3)
verifier("2f. les voies : quatre flottants de 32 bits calculés ensemble, GDOT sur quatre voies",
         c.sortie == [sum(trois << (32 * k) for k in range(4)), 196], c.sortie)

x15 = Q128.depuis(__import__("fractions").Fraction(3, 2))
c = lancer(f"""
    LDI128 R1, {x15}
    FMUL R2, R1, R1          ; 2,25 en 128 bits
    OUT R2
    LDIU R3, 10
    ITOF.64 R4, R3, 2        ; 10 (entier de 32 bits) vers flottant_64
    OUT R4
    FCONV R5, R4, 1          ; flottant_64 vers flottant de 128 bits
    OUT R5
    FSQRT R6, R5             ; racine de 10
    FCONV.32 R7, R6, 0       ; vers flottant_32 (arrondi)
    OUT R7
    FTOI R8, R2, 1           ; 2,25 tronqué : 2 (64 bits)
    OUT R8
    FVIEEE.64 R9, R4         ; 10 en binary64
    OUT R9
    HALT
""")
from fractions import Fraction  # noqa: E402
att = [Q128.depuis(Fraction(9, 4)), Q64.depuis(10), Q128.depuis(10), Q128.vers(Q32, Q128.racine(Q128.depuis(10))), 2,
       struct.unpack("<Q", struct.pack("<d", 10.0))[0]]
verifier("2g. flottants aux trois largeurs, conversions, échange IEEE", c.sortie == att, c.sortie)

# --- 3. le brin, les cubes sur disque
ok = False
try:
    lancer("""
    LDI128 R1, 0x40000000000000000000000000000100
    LDIU R2, 3
    MARQUE R1, R2, 1        ; trois mots fixés (ADN)
    ST R1, R2, 1
    HALT
""")
except S.Erreur as e:
    ok = "ADN" in str(e)
verifier("3a. le brin : écrire dans un mot ADN arrête la machine", ok)

d = tempfile.mkdtemp(prefix="lugus-")
prog_ecrire = """
    LDI128 R1, 0x40000000000000000000000000000000
    LDIU R2, 1000
    LDIU R3, 0
b:  MUL R4, R3, R3
    ADDI R4, R4, 7
    STX R1, R4, R3
    ADDI R3, R3, 1
    CMP R3, R2
    JC b
    LDIU R5, 11
    SYS R6, R5, R1
    OUT R6
    HALT
"""
prog_lire = """
    LDI128 R1, 0x40000000000000000000000000000000
    LDIU R2, 1000
    LDIU R3, 0
    LDIU R7, 0
b:  LDX R4, R1, R3
    ADD R7, R7, R4
    ADDI R3, R3, 1
    CMP R3, R2
    JC b
    LDIU R5, 22
    SYS R6, R5, R0
    OUT R6
    OUT R7
    HALT
"""


def avec_dossier(asm):
    cpu = S.CPU(dossier=d)
    cpu.charger(S.assembler(asm))
    cpu.executer(10_000_000)
    return cpu.sortie


somme = sum(i * i + 7 for i in range(1000))
e = avec_dossier(prog_ecrire)
fichiers = sorted(os.listdir(d))
r1 = avec_dossier(prog_lire)
chemin = os.path.join(d, "cube128-1-0.cub")
b = bytearray(open(chemin, "rb").read())
b[8 + 4 + 16 * 500] ^= 0x20          # un mot abîmé dans la copie
open(chemin, "wb").write(bytes(b))
r2 = avec_dossier(prog_lire)
r3 = avec_dossier(prog_lire)
verifier(f"3b. cube sur disque avec anti-cube et ombre ({', '.join(fichiers)}) : relu vrai, abîmé puis réparé (faux), "
         f"puis d'accord (vrai)", e == [1] and r1 == [2, somme] and r2 == [1, somme] and r3 == [2, somme], (e, r1, r2, r3))
shutil.rmtree(d, ignore_errors=True)

print()
print("Lugus (référence Python) : " + ("tout est conforme" if not echecs else f"{len(echecs)} échec(s)"))
sys.exit(1 if echecs else 0)
