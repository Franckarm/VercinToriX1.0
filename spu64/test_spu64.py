#!/usr/bin/env python3
"""SPU-64 : la machine Rust (vtx64) doit donner exactement les mêmes lignes que la machine de référence en Python, sur
des milliers de programmes aléatoires (entiers, quaternaire, mémoire et adresses longues, brin, flottants quaternaires de
32 et 64 bits, conversions, sauts). Les flottants de la machine Python sont calculés par fractions exactes : l'accord des
deux machines vaut vérification de l'arithmétique de la machine Rust.

    python3 spu64/test_spu64.py [NOMBRE] [GRAINE]"""
import os
import random
import subprocess
import sys
import tempfile

ici = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ici)
import spu64 as S  # noqa: E402
from qflot import Q32, Q64  # noqa: E402

racine = os.path.dirname(ici)
EXE = os.path.join(racine, "vtx-rs", "target", "release", "vtx64" + (".exe" if os.name == "nt" else ""))
N = int(sys.argv[1]) if len(sys.argv) > 1 else 400
g = random.Random(int(sys.argv[2]) if len(sys.argv) > 2 else 64)


def flottant(F):
    c = g.random()
    s = g.getrandbits(1)
    if c < 0.04:
        return F.INCONNU
    if c < 0.07:
        return F.VARIABLE
    if c < 0.12:
        return F.signe(s)
    if c < 0.15:
        return F.inf(s)
    if c < 0.22:
        return F.signe(s) | g.getrandbits(g.randint(1, F.P - 2))          # sous-normal
    if c < 0.27:
        e = g.choice([1, 2, F.emax - 2, F.emax - 1])
    elif c < 0.7:
        e = F.biais - F.nq + g.randint(-20, 20)
    else:
        e = g.randint(1, F.emax - 1)
    k = g.random()
    if k < 0.4:
        m = g.getrandbits(F.P)
    elif k < 0.6:
        m = F.mant - g.getrandbits(g.randint(0, 12))
    elif k < 0.8:
        m = (1 << (F.P - 2)) | (g.getrandbits(g.randint(0, 12)) << g.randint(0, F.P - 16))
    else:
        m = g.getrandbits(F.P) & ~((1 << g.randint(0, F.P - 1)) - 1)
    if m < 1 << (F.P - 2):
        m |= 1 << g.choice([F.P - 2, F.P - 1])
    return F.signe(s) | (e << F.P) | (m & F.mant)


def valeur():
    c = g.random()
    if c < 0.25:
        return flottant(Q64)
    if c < 0.35:
        return flottant(Q32)
    if c < 0.55:
        return g.getrandbits(64)
    if c < 0.75:
        return g.randint(0, 300)
    if c < 0.85:
        return (1 << 64) - g.randint(1, 300)
    return g.choice([0, 1, 1 << 63, (1 << 63) - 1, (1 << 64) - 1, 1 << 32, (1 << 32) - 1, 0x8000000000000000])


RRR = ["ADD", "SUB", "MUL", "MULHU", "MULHS", "DIV", "MOD", "DIVS", "MODS", "SHL", "SHR", "SAR", "AND", "OR", "XOR",
       "MIN", "MAX", "ADDM4", "QEGAL", "ET4", "OU4", "EXQ", "GDOT", "ADC", "SBC",
       "FADD", "FSUB", "FMUL", "FDIV", "FEQ", "FLT", "FLE", "FCMP",
       "SADD", "SSUB", "SMUL", "SDIV", "SEQ", "SLT", "SLE", "ETGX"]
RR = ["SHL4", "SHR4", "MOV", "CMP3", "ZEXT32", "SEXT32", "COMPTE", "NON4", "ANTI", "FSQRT", "ITOF", "ITOFS", "FTOI",
      "FROUND", "FNEG", "FETAT", "FVIEEE", "FDIEEE", "SSQRT", "STOF", "FTOS", "SNEG"]
REGS = range(1, 10)     # R1 à R9 : calcul ; R10, R11 : adresses longues ; R12 : petit décalage ; R13 : cadre


def programme():
    L = []
    for r in REGS:
        L.append(f"LDI R{r},{valeur()}")
    for r in (10, 11):
        e = g.randint(1, 3)
        f = g.choice([0, 1, 262, g.getrandbits(24)])
        L.append(f"LDI R{r},{(e << 62) | (f << 24) | g.getrandbits(24) & 0xFFFF00}")
    L.append(f"LDIS R12,#{g.randint(0, 40)}")
    L.append("LDI R13,16777216")
    lab = 0
    for _ in range(g.randint(10, 60)):
        c = g.random()
        x, y, z = (g.choice(REGS) for _ in range(3))
        if c < 0.45:
            L.append(f"{g.choice(RRR)} R{x},R{y},R{z}")
        elif c < 0.62:
            L.append(f"{g.choice(RR)} R{x},R{y}")
        elif c < 0.68:
            L.append(f"{g.choice(['ADDI', 'SUBI'])} R{x},R{y},#{g.randint(-2**31, 2**31 - 1)}" if g.random() < 0.8
                     else f"ETG R{x},R{y},#{g.randint(-3, 7)}")
        elif c < 0.71:
            L.append(f"{g.choice(['LDIS', 'LDIU'])} R{x},#{g.randint(0, 2**31 - 1)}")
        elif c < 0.74:
            L.append(f"CMP R{x},R{y}" if g.random() < 0.5 else f"CMPI R{x},#{g.randint(-1000, 1000)}")
            L.append(f"LDIS R{z},#0")
            k = g.choice(["JZ", "JNZ", "JC", "JNC"])
            L.append(f"{k} saut{lab}")
            L.append(f"LDIS R{z},#7")
            L.append(f"saut{lab}:")
            lab += 1
        elif c < 0.82:
            a = g.choice([10, 11])
            op = g.choice(["LD", "ST", "LDX", "STX", "LDQ", "STQ"])
            if op in ("LD", "ST"):
                L.append(f"{op} R{x if op == 'LD' else a},R{a if op == 'LD' else x},#{g.randint(-8, 8)}")
            elif op == "LDX":
                L.append(f"LDX R{x},R{a},R12")
            elif op == "STX":
                L.append(f"STX R{a},R{x},R12")
            else:
                L.append(f"{op} R{x},R{a},R12")
        elif c < 0.86:
            L.append(f"STF R{x},#{g.randint(-5, 5)}" if g.random() < 0.5 else f"LDF R{x},#{g.randint(-5, 5)}")
        elif c < 0.89:
            L.append(f"PUSH R{x}")
            L.append(f"POP R{y}")
        elif c < 0.92:
            a = g.choice([10, 11])
            L.append(f"LDIS R12,#{g.randint(0, 6)}")
            L.append(f"MARQUE R{a},R12,#{g.choice([0, 1, 2, 2])}")
            L.append(f"BRIN R{x},R{a}")
        elif c < 0.95:
            L.append(f"LDIS R{y},#{g.choice([1, 3, 4, 11, 12, 99])}")
            L.append(f"SYS R{x},R{y},R{z}")
        elif c < 0.97:
            # une petite boucle comptée
            L.append(f"LDIS R12,#{g.randint(1, 5)}")
            L.append(f"boucle{lab}:")
            L.append(f"{g.choice(RRR)} R{x},R{y},R{z}")
            L.append("SUBI R12,R12,#1")
            L.append(f"JNZ boucle{lab}")
            lab += 1
        else:
            # GEMV : n, w, q, k, o empilés dans cet ordre
            a, b = 10, 11
            L.append(f"LDIS R12,#{g.randint(0, 3)}")
            L.append("PUSH R12")
            L.append(f"LDIS R12,#{g.randint(1, 3)}")
            L.append("PUSH R12")
            L.append(f"PUSH R{a}")
            L.append(f"PUSH R{b}")
            L.append(f"PUSH R{a}")
            L.append("GEMV")
            L.append("ADDI R14,R14,#5")
            L.append("LDIS R12,#3")
    for r in range(1, 13):
        L.append(f"OUT R{r}")
    L.append("HALT")
    return "\n".join(L) + "\n"


progs = []
for _ in range(N):
    progs.append(S.assembler(programme()))
attendu = [S.lancer(m, []) for m in progs]
with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
    for m in progs:
        f.write(",".join(map(str, m)) + ";\n")
    nom = f.name
r = subprocess.run([EXE, "corpus", nom], capture_output=True, text=True)
os.unlink(nom)
obtenu = r.stdout.strip("\n").split("\n")
ecarts = [i for i, (a, b) in enumerate(zip(attendu, obtenu)) if a != b]
erreurs = sum(a.startswith("ERREUR") for a in attendu)
print(f"SPU-64 : {N} programmes aléatoires ({erreurs} arrêtés par une erreur, comme « écriture dans un mot ADN ») : "
      f"{N - len(ecarts)}/{N} identiques entre la machine de référence et la machine Rust")
for i in ecarts[:3]:
    a, b = attendu[i], obtenu[i]
    k = next((j for j in range(min(len(a), len(b))) if a[j] != b[j]), 0)
    print(f"  écart au programme {i} : … {a[max(0, k - 80):k + 80]}\n  contre … {b[max(0, k - 80):k + 80]}")
mauvais = bool(ecarts or len(obtenu) != N)

# ------------------------------------------------------------------ cubes sur disque : écrits, puis relus page par page
ECRIT = """
    LDI R1,0x4000000106000000      ; étage 1, fréquence 262, #000000
    LDIS R2,#0
    LDIS R3,#3000
remplir:
    ADDI R2,R2,#7
    ST R1,R2,#0
    ADDI R1,R1,#20
    SUBI R3,R3,#1
    JNZ remplir
    LDI R1,0x4000000106000000
    LDIS R4,#5
    MARQUE R1,R4,#1                ; cinq mots en ADN
    LDIS R5,#11
    SYS R6,R5,R1                   ; ranger le cube sur disque
    OUT R6
    HALT
"""
RELU = """
    LDI R1,0x4000000106000000
    LD R2,R1,#0
    OUT R2
    LD R2,R1,#59980
    OUT R2
    BRIN R3,R1
    OUT R3
    LDIS R4,#99
    ST R1,R4,#100                  ; un mot libre : permis
    LD R2,R1,#100
    OUT R2
    ST R1,R4,#2                    ; un mot ADN : refusé
    HALT
"""
with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
    sorties = []
    for d, rust in ((d1, False), (d2, True)):
        lignes = []
        for src in (ECRIT, RELU):
            m = S.assembler(src)
            if rust:
                f = os.path.join(d, "p.mots")
                open(f, "w").write(",".join(map(str, m)) + ";")
                r = subprocess.run([EXE, "lancer", f], capture_output=True, text=True)
                lignes.append(r.stdout.strip() + " / " + (r.stderr.strip().split("\n")[0] if r.returncode else ""))
            else:
                cpu = S.CPU(dossier=d)
                cpu.charger(m)
                try:
                    cpu.executer(10_000_000)
                    err = ""
                except S.Erreur as e:
                    err = "erreur : " + str(e)
                lignes.append(",".join(map(str, cpu.sortie)) + " / " + err)
        sorties.append(lignes)
attendu_disque = ["1 / ", "7,21000,1,99 / erreur : écriture dans un mot ADN (fixé) à l'adresse étage 1, #000106000002"]
ok = sorties[0] == sorties[1] == attendu_disque
print(f"cubes sur disque (écrits, relus page par page au premier accès, brin ADN gardé) : {'identiques' if ok else 'ÉCART'}"
      + ("" if ok else f" {sorties}"))
mauvais |= not ok
print("Tout est conforme." if not mauvais else "ÉCART")
sys.exit(1 if mauvais else 0)
