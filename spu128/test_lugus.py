#!/usr/bin/env python3
"""Lugus (le SPU-128) : la machine Rust (lugus) doit donner exactement les mêmes lignes que la machine de référence en
Python, sur des programmes aléatoires (entiers aux trois largeurs, quaternaire, mémoire et adresses, brin, flottants
quaternaires de 32, 64 et 128 bits et leurs conversions, voies, matière, sauts, appels). Les flottants de la machine
Python sont calculés par fractions exactes : l'accord des deux machines vaut vérification de l'arithmétique de la
machine Rust. Puis les cubes sur disque (écrits avec leur anti-cube et leur ombre, relus page par page).

    python3 spu128/test_lugus.py [NOMBRE] [GRAINE]
    python3 spu128/test_lugus.py --corpus     écrit le corpus de conformité (spu128/corpus128.txt et ses résultats)"""
import os
import random
import subprocess
import sys
import tempfile

ici = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ici)
import spu128 as S  # noqa: E402
from qflot import Q32, Q64, Q128  # noqa: E402

racine = os.path.dirname(ici)
cible = os.environ.get("CARGO_TARGET_DIR") or os.path.join(racine, "vtx-rs", "target")
EXE = os.path.join(cible, "release", "lugus" + (".exe" if os.name == "nt" else ""))
CORPUS = "--corpus" in sys.argv
args = [a for a in sys.argv[1:] if a != "--corpus"]
N = int(args[0]) if args else (600 if CORPUS else 300)
g = random.Random(int(args[1]) if len(args) > 1 else 1280)


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
        return F.signe(s) | g.getrandbits(g.randint(1, F.P - 2))
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
    if c < 0.2:
        return flottant(Q128)
    if c < 0.3:
        return flottant(Q64)
    if c < 0.38:
        return flottant(Q32)
    if c < 0.42:
        return sum(flottant(Q32) << (32 * k) for k in range(4))       # quatre flottants dans les voies
    if c < 0.58:
        return g.getrandbits(128)
    if c < 0.68:
        return g.getrandbits(64)
    if c < 0.8:
        return g.randint(0, 300)
    if c < 0.88:
        return (1 << 128) - g.randint(1, 300)
    return g.choice([0, 1, 1 << 127, (1 << 127) - 1, (1 << 128) - 1, 1 << 64, (1 << 64) - 1, 1 << 63, (1 << 32) - 1, 1 << 31])


LARG = ["", "", ".64", ".64", ".32"]
RRR_W = ["ADD", "SUB", "MUL", "MULHU", "MULHS", "DIV", "MOD", "DIVS", "MODS", "SHL", "SHR", "SAR", "AND", "OR", "XOR",
         "MIN", "MAX", "ADDM4", "QEGAL", "ET4", "OU4", "EXQ", "ADC", "SBC",
         "FADD", "FSUB", "FMUL", "FDIV", "FEQ", "FLT", "FLE", "FCMP"]
RRR = ["GDOT", "ETGX", "VADD", "VSUB", "VMUL", "VMIN", "VMAX", "VFADD", "VFSUB", "VFMUL", "VFDIV", "VEXT", "MATL"]
RR_W = ["SHL4", "SHR4", "CMP3", "ZEXT", "SEXT", "COMPTE", "NON4", "ANTI", "FSQRT", "FNEG", "FETAT", "FVIEEE", "FDIEEE"]
RR = ["MOV", "VBCAST", "ANTIPOINT"]
RRI_W = ["ITOF", "ITOFS", "FTOI", "FROUND", "FCONV"]
REGS = range(1, 10)     # R1 à R9 : calcul ; R10, R11 : adresses ; R12 : petit décalage ; R13 : cadre


def programme():
    L = []
    for r in REGS:
        L.append(f"LDI128 R{r},{valeur()}")
    for r in (10, 11):
        e = g.randint(1, 3)
        f = g.choice([0, 1, 262, g.getrandbits(24), g.getrandbits(96)])
        L.append(f"LDI128 R{r},{(e << 126) | (f << 24) | g.getrandbits(24) & 0xFFFF00}")
    L.append(f"LDIS R12,{g.randint(0, 40)}")
    L.append("LDI R13,16777216")
    lab = 0
    for _ in range(g.randint(10, 60)):
        c = g.random()
        x, y, z = (g.choice(REGS) for _ in range(3))
        w = g.choice(LARG)
        if c < 0.36:
            L.append(f"{g.choice(RRR_W)}{w} R{x},R{y},R{z}")
        elif c < 0.44:
            L.append(f"{g.choice(RRR)} R{x},R{y},R{z}")
        elif c < 0.54:
            L.append(f"{g.choice(RR_W)}{w} R{x},R{y}")
        elif c < 0.57:
            L.append(f"{g.choice(RR)} R{x},R{y}")
        elif c < 0.62:
            L.append(f"{g.choice(RRI_W)}{w} R{x},R{y},{g.randint(0, 2)}")
        elif c < 0.65:
            op = g.choice(["MATE", "MELANGE", "VINS"])
            if op == "VINS":
                L.append(f"VINS R{x},R{y},{g.randint(0, 3)}")
            else:
                L.append(f"{op} R{x},R{y},R{z},{g.randint(0, 300) if op == 'MELANGE' else g.randint(0, 7)}")
        elif c < 0.69:
            L.append(f"{g.choice(['ADDI', 'SUBI'])}{w} R{x},R{y},{g.randint(-2**31, 2**31 - 1)}" if g.random() < 0.8
                     else f"ETG R{x},R{y},{g.randint(-3, 7)}")
        elif c < 0.71:
            L.append(f"{g.choice(['LDIS', 'LDIU'])} R{x},{g.randint(0, 2**31 - 1)}")
        elif c < 0.74:
            L.append(f"CMP{w} R{x},R{y}" if g.random() < 0.5 else f"CMPI{w} R{x},{g.randint(-1000, 1000)}")
            L.append(f"LDIS R{z},0")
            L.append(f"{g.choice(['JZ', 'JNZ', 'JC', 'JNC'])} saut{lab}")
            L.append(f"LDIS R{z},7")
            L.append(f"saut{lab}:")
            lab += 1
        elif c < 0.81:
            a = g.choice([10, 11])
            op = g.choice(["LD", "ST", "LDX", "STX", "LDQ", "STQ"])
            if op in ("LD", "ST"):
                L.append(f"{op} R{x if op == 'LD' else a},R{a if op == 'LD' else x},{g.randint(-8, 8)}")
            elif op == "LDX":
                L.append(f"LDX R{x},R{a},R12")
            elif op == "STX":
                L.append(f"STX R{a},R{x},R12")
            else:
                L.append(f"{op} R{x},R{a},R12")
        elif c < 0.85:
            L.append(f"STF R{x},{g.randint(-5, 5)}" if g.random() < 0.5 else f"LDF R{x},{g.randint(-5, 5)}")
        elif c < 0.88:
            L.append(f"PUSH R{x}")
            L.append(f"POP R{y}")
        elif c < 0.91:
            a = g.choice([10, 11])
            L.append(f"LDIS R12,{g.randint(0, 6)}")
            L.append(f"MARQUE R{a},R12,{g.choice([0, 1, 2, 2])}")
            L.append(f"BRIN R{x},R{a}")
        elif c < 0.94:
            L.append(f"LDIS R{y},{g.choice([1, 3, 4, 11, 12, 99])}")
            L.append(f"SYS R{x},R{y},R{z}")
        elif c < 0.97:
            L.append(f"LDIS R12,{g.randint(1, 5)}")
            L.append(f"boucle{lab}:")
            L.append(f"{g.choice(RRR_W)}{w} R{x},R{y},R{z}")
            L.append("SUBI R12,R12,1")
            L.append(f"JNZ boucle{lab}")
            lab += 1
        elif c < 0.985:
            L.append(f"CALL appel{lab}")
            L.append(f"JMP apres{lab}")
            L.append(f"appel{lab}: {g.choice(RRR_W)}{w} R{x},R{y},R{z}")
            L.append("RET")
            L.append(f"apres{lab}:")
            lab += 1
        else:
            L.append(f"LDIS R12,{g.randint(0, 3)}")
            L.append("PUSH R12")
            L.append(f"LDIS R12,{g.randint(1, 3)}")
            L.append("PUSH R12")
            L.append("PUSH R10")
            L.append("PUSH R11")
            L.append("PUSH R10")
            L.append("GEMV")
            L.append("ADDI R14,R14,5")
            L.append("LDIS R12,3")
    for r in range(1, 13):
        L.append(f"OUT R{r}")
    L.append("HALT")
    return "\n".join(L) + "\n"


progs = [S.assembler(programme()) for _ in range(N)]
for nom in sorted(os.listdir(os.path.join(ici, "exemples"))) if os.path.isdir(os.path.join(ici, "exemples")) else []:
    if nom.endswith(".s128"):
        progs.append(S.assembler(open(os.path.join(ici, "exemples", nom), encoding="utf-8").read()))
attendu = [S.lancer(m, []) for m in progs]
texte = "".join(",".join(map(str, m)) + ";\n" for m in progs)
if CORPUS:
    open(os.path.join(ici, "corpus128.txt"), "w").write(texte)
    open(os.path.join(ici, "corpus128_attendu.txt"), "w").write("\n".join(attendu) + "\n")
    print(f"corpus de Lugus : {len(progs)} programmes écrits")
    sys.exit(0)
with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
    f.write(texte)
    nom = f.name
r = subprocess.run([EXE, "corpus", nom], capture_output=True, text=True)
os.unlink(nom)
obtenu = r.stdout.strip("\n").split("\n")
ecarts = [i for i, (a, b) in enumerate(zip(attendu, obtenu)) if a != b]
erreurs = sum(a.startswith("ERREUR") for a in attendu)
print(f"Lugus : {len(progs)} programmes aléatoires ({erreurs} arrêtés par une erreur, comme « écriture dans un mot ADN ») : "
      f"{len(progs) - len(ecarts)}/{len(progs)} identiques entre la machine de référence et la machine Rust")
for i in ecarts[:3]:
    a, b = attendu[i], obtenu[i]
    k = next((j for j in range(min(len(a), len(b))) if a[j] != b[j]), 0)
    print(f"  écart au programme {i} : … {a[max(0, k - 100):k + 100]}\n  contre … {b[max(0, k - 100):k + 100]}")
    open(os.path.join(tempfile.gettempdir(), f"lugus_ecart_{i}.s128"), "w").write(str(progs[i]))
mauvais = bool(ecarts or len(obtenu) != len(progs))

# ------------------------------------------------------------------ cubes sur disque : écrits, puis relus page par page
ECRIT = """
    LDI128 R1,0x40000000000000000000000106000000
    LDIS R2,0
    LDIS R3,3000
remplir:
    ADDI R2,R2,7
    ST R1,R2,0
    ADDI R1,R1,20
    SUBI R3,R3,1
    JNZ remplir
    LDI128 R1,0x40000000000000000000000106000000
    LDIS R4,5
    MARQUE R1,R4,1
    LDIS R5,11
    SYS R6,R5,R1
    OUT R6
    HALT
"""
RELU = """
    LDI128 R1,0x40000000000000000000000106000000
    LD R2,R1,0
    OUT R2
    LD R2,R1,59980
    OUT R2
    BRIN R3,R1
    OUT R3
    LDIS R4,99
    ST R1,R4,100
    LD R2,R1,100
    OUT R2
    ST R1,R4,2
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
attendu_disque = ["1 / ", "7,21000,1,99 / erreur : écriture dans un mot ADN (fixé) à l'adresse étage 1, #000000000000000000000106000002"]
ok = sorties[0] == sorties[1] == attendu_disque
print(f"cubes sur disque (écrits avec anti-cube et ombre, relus page par page, brin ADN gardé) : {'identiques' if ok else 'ÉCART'}"
      + ("" if ok else f" {sorties}"))
mauvais |= not ok
print("Lugus : tout est conforme." if not mauvais else "Lugus : ÉCART")
sys.exit(1 if mauvais else 0)
