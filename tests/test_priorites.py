#!/usr/bin/env python3
"""Test des priorités d'opérateurs de vtx, sans parenthèses, contre un évaluateur indépendant.

L'évaluateur ci-dessous ne partage rien avec l'analyseur de vtx : jetons par expression régulière, table de priorité
recopiée de la documentation (du plus faible au plus fort : || ; && ; comparaisons ; | ; ^ ; & ; décalages ; + - ; * / %),
opérateurs binaires associatifs à gauche, opérateurs unaires ~ ! - plus forts que tous les binaires, court-circuit de
&& et ||, mots de 32 bits, division par zéro définie (x / 0 = 0xFFFFFFFF, x % 0 = x).
"""
import importlib.util
import random
import re

spec = importlib.util.spec_from_file_location("vtx", __import__("os").path.join(__import__("os").path.dirname(__import__("os").path.abspath(__file__)), "..", "vtx.py"))
vtx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vtx)
MASK = 0xFFFFFFFF
PREC = {"||": 0, "&&": 1, "==": 2, "!=": 2, "<": 2, "<=": 2, ">": 2, ">=": 2, "|": 3, "^": 4, "&": 5,
        "<<": 6, ">>": 6, "<<q": 6, ">>q": 6, "+": 7, "-": 7, "*": 8, "/": 8, "%": 8}


def jetons(s):
    return re.findall(r"<<q|>>q|<<|>>|<=|>=|==|!=|&&|\|\||[-+*/%&|^~!<>]|\d+", s)


def analyse(t):
    pos = [0]

    def unaire():
        x = t[pos[0]]
        pos[0] += 1
        if x in ("~", "!", "-"):
            return ("u", x, unaire())
        return ("n", int(x))

    def expr(minp):
        g = unaire()
        while pos[0] < len(t) and t[pos[0]] in PREC and PREC[t[pos[0]]] >= minp:
            op = t[pos[0]]
            pos[0] += 1
            g = ("b", op, g, expr(PREC[op] + 1))
        return g

    return expr(0)


def ev(n):
    if n[0] == "n":
        return n[1] & MASK
    if n[0] == "u":
        v = ev(n[2])
        return {"~": (~v) & MASK, "!": int(v == 0), "-": (-v) & MASK}[n[1]]
    op = n[1]
    if op == "&&":
        return int(ev(n[2]) != 0 and ev(n[3]) != 0)
    if op == "||":
        return int(ev(n[2]) != 0 or ev(n[3]) != 0)
    a, b = ev(n[2]), ev(n[3])
    return {"+": (a + b) & MASK, "-": (a - b) & MASK, "*": (a * b) & MASK, "/": a // b if b else MASK,
            "%": a % b if b else a, "<<": (a << (b & 31)) & MASK, ">>": a >> (b & 31), "&": a & b, "|": a | b,
            "^": a ^ b, "==": int(a == b), "!=": int(a != b), "<": int(a < b), "<=": int(a <= b), ">": int(a > b),
            ">=": int(a >= b), "<<q": (a << ((2 * b) & 31)) & MASK, ">>q": a >> ((2 * b) & 31)}[op]


LITS = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "12", "15", "16", "31", "100", "255", "256", "65535",
        "2147483648", "4294967295"]
r = random.Random(2026)
N, bad, premier, par_op = 3000, 0, None, {}
for n in range(N):
    k = r.randint(2, 8)
    parts = []
    for i in range(k):
        pre = "".join(r.choice(["~ ", "! ", "- "]) for _ in range(r.choice([0, 0, 0, 1, 2])))
        parts.append(pre + r.choice(LITS))
        if i < k - 1:
            parts.append(r.choice(list(PREC)))
    src = " ".join(parts)
    attendu = ev(analyse(jetons(src)))
    cpu, _, _ = vtx.executer(f"fonction principal() {{ sortie({src}); }}")
    for op in set(jetons(src)) & set(PREC):
        par_op[op] = par_op.get(op, 0) + 1
    if cpu.sortie != [attendu]:
        bad += 1
        premier = premier or (src, cpu.sortie, attendu)
print(f"{N} expressions sans parenthèses, {len(par_op)} opérateurs binaires couverts, écarts : {bad}")
print("occurrences par opérateur : " + " ".join(f"{o}:{c}" for o, c in sorted(par_op.items(), key=lambda x: PREC[x[0]])))
if premier:
    print("premier écart :", premier)
