#!/usr/bin/env python3
"""Test différentiel de vtx : programmes aléatoires, trois résultats comparés.

  oracle           : un interpréteur de l'arbre syntaxique qui applique la sémantique du langage (mots de 32 bits,
                     division par zéro définie, priorités, court-circuit), sans passer par le compilateur
  compilé optimisé : élagage, sauts directs, pas de pile pour les feuilles
  compilé simple   : aucune de ces optimisations
Comparés : suite des sorties et contenu final des étages 1 à 3. Les programmes sont toujours terminants (boucles à
bornes littérales, pas de récursion) et n'écrivent que dans les étages 1 à 3.
"""
import importlib.util
import random
import sys

spec = importlib.util.spec_from_file_location("vtx", __import__("os").path.join(__import__("os").path.dirname(__import__("os").path.abspath(__file__)), "..", "vtx.py"))
vtx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vtx)
MASK = 0xFFFFFFFF
LITS = ["0", "1", "2", "3", "5", "7", "10", "31", "32", "100", "255", "256", "1000", "65535", "65536",
        "2147483648", "4294967295", "#3A7F1C80", "#00FF00FF", "0q0123"]
BIN = ["+", "-", "*", "/", "%", "<<", ">>", "&", "|", "^", "==", "!=", "<", "<=", ">", ">=", "&&", "||", "<<q", ">>q"]


class Gen:
    def __init__(self, r):
        self.r = r
        self.funcs = []  # (nom, arité)

    def expr(self, vs, d):
        r = self.r
        if d == 0 or r.random() < .25:
            return r.choice(vs) if vs and r.random() < .6 else r.choice(LITS)
        k = r.random()
        e = lambda: self.expr(vs, d - 1)
        if k < .42:
            return f"({e()} {r.choice(BIN)} {e()})"
        if k < .50:
            return f"({r.choice(['~', '!', '-'])}{e()})"
        if k < .58:
            return f"({e()}).{r.choice(['r', 'v', 'b', 'a'])}" if r.random() < .6 else f"({e()}).q(({e()}) & 15)"
        if k < .68:
            return f"@{r.randint(1, 3)}[({e()}) & 255]" if r.random() < .6 else f"@(1 + (({e()}) % 3))[({e()}) & 255]"
        if k < .80 and self.funcs:
            nom, n = r.choice(self.funcs)
            return f"{nom}({', '.join(e() for _ in range(n))})"
        b = r.choice(["min4", "max4", "addm4", "gdot", "cmp3", "abs", "inf", "sup", "min", "max", "poids"])
        if b in ("cmp3", "abs"):
            return f"{b}({e()})"
        if b == "poids":
            return f"poids({e()}, ({e()}) & 15)"
        return f"{b}({e()}, {e()})"

    def stmt(self, vs, d, ld, ret, lv=()):
        r, ind = self.r, "    " * (1 + d)
        k = r.random()
        e = lambda: self.expr(vs + list(lv), 2)
        if k < .30 and vs:
            return f"{ind}{r.choice(vs)} = {e()};"
        if k < .48:
            return f"{ind}sortie({e()});"
        if k < .62:
            tgt = f"@{r.randint(1, 3)}[({e()}) & 255]" if r.random() < .6 else f"@(1 + (({e()}) % 3))[({e()}) & 255]"
            return f"{ind}{tgt} = {e()};"
        if k < .78 and d < 2:
            a = "\n".join(self.stmt(vs, d + 1, ld, ret, lv) for _ in range(r.randint(1, 3)))
            s = f"{ind}si {e()} {{\n{a}\n{ind}}}"
            if r.random() < .6:
                s += " sinon {\n" + "\n".join(self.stmt(vs, d + 1, ld, ret, lv) for _ in range(r.randint(1, 2))) + f"\n{ind}}}"
            return s
        if k < .88 and d < 2 and ld < 2:
            body = "\n".join(self.stmt(vs, d + 1, ld + 1, ret, tuple(lv) + (f"i{ld}",)) for _ in range(r.randint(1, 3)))
            return f"{ind}pour i{ld} dans 0..{r.randint(0, 5)} {{\n{body}\n{ind}}}"
        if k < .93 and d < 2 and ld < 2:
            body = "\n".join(self.stmt(vs, d + 1, ld + 1, ret, tuple(lv)) for _ in range(r.randint(1, 2)))
            return f"{ind}c{ld} = 0;\n{ind}tantque c{ld} < {r.randint(0, 4)} {{\n{body}\n{ind}    c{ld} = c{ld} + 1;\n{ind}}}"
        if k < .97 and ret:
            return f"{ind}si {e()} {{\n{ind}    retour {e()};\n{ind}}}"
        if self.funcs:
            nom, n = r.choice(self.funcs)
            return f"{ind}{nom}({', '.join(e() for _ in range(n))});"
        return f"{ind}sortie({e()});"

    def fonction(self, nom, params, principal=False):
        r = self.r
        vs = list(params)
        decl = []
        for j in range(r.randint(2, 4)):
            decl.append(f"    soit v{j} = {self.expr(vs, 2)};")
            vs.append(f"v{j}")
        decl += ["    soit c0 = 0;", "    soit c1 = 0;"]
        corps = [self.stmt(vs, 0, 0, not principal) for _ in range(r.randint(3, 7))]
        fin = "".join(f"    sortie({v});\n" for v in vs[-2:]) if principal else f"    retour {self.expr(vs, 2)};\n"
        return f"fonction {nom}({', '.join(params)}) {{\n" + "\n".join(decl) + "\n" + "\n".join(corps) + "\n" + fin + "}\n"

    def programme(self):
        r, out = self.r, []
        for j in range(r.randint(0, 2)):
            n = r.randint(1, 2)
            out.append(self.fonction(f"f{j}", [f"p{k}" for k in range(n)]))
            self.funcs.append((f"f{j}", n))
        out.append(self.fonction("principal", [], True))
        return "\n".join(out)


class Ret(Exception):
    pass


def oracle(src):
    fs = {f.nom: f for f in vtx.Analyseur(vtx.lexer(vtx.PRELUDE)).programme()}
    fs.update({f.nom: f for f in vtx.Analyseur(vtx.lexer(src)).programme()})
    mem, out, pas = {}, [], [0]
    L = lambda x: [(x >> (2 * k)) & 3 for k in range(16)]
    quit4 = lambda a, b, f: sum(f(x, y) << (2 * k) for k, (x, y) in enumerate(zip(L(a), L(b))))

    def bi(op, a, b):
        return {"+": (a + b) & MASK, "-": (a - b) & MASK, "*": (a * b) & MASK,
                "/": a // b if b else MASK, "%": a % b if b else a, "<<": (a << (b & 31)) & MASK, ">>": a >> (b & 31),
                "&": a & b, "|": a | b, "^": a ^ b, "==": int(a == b), "!=": int(a != b), "<": int(a < b),
                "<=": int(a <= b), ">": int(a > b), ">=": int(a >= b), "<<q": (a << ((2 * b) & 31)) & MASK,
                ">>q": a >> ((2 * b) & 31)}[op]

    def ev(e, env):
        pas[0] += 1
        if pas[0] > 400000:
            raise RuntimeError("trop long")
        g = e[0]
        if g == "nombre":
            return e[1]
        if g == "var":
            return env[e[1]]
        if g == "non":
            return ~ev(e[1], env) & MASK
        if g == "non_log":
            return int(ev(e[1], env) == 0)
        if g == "bin":
            if e[1] == "&&":
                return int(ev(e[2], env) != 0 and ev(e[3], env) != 0)
            if e[1] == "||":
                return int(ev(e[2], env) != 0 or ev(e[3], env) != 0)
            a = ev(e[2], env)
            return bi(e[1], a, ev(e[3], env))
        if g == "champ":
            return (ev(e[1], env) >> {"r": 24, "v": 16, "b": 8, "a": 0}[e[2]]) & 255
        if g == "quit":
            x = ev(e[1], env)
            return (x >> ((2 * ev(e[2], env)) & 31)) & 3
        if g == "lire":
            a = ev(e[2], env)
            et = e[1] if isinstance(e[1], int) else ev(e[1], env) & 3
            return mem.get((et, a & 0xFFFFFF), 0)
        if g == "appel":
            return appel(e[1], [ev(x, env) for x in e[2]])
        raise RuntimeError(g)

    def appel(nom, a):
        if nom == "sortie":
            out.append(a[0])
            return a[0]
        if nom == "min4":
            return quit4(a[0], a[1], min)
        if nom == "max4":
            return quit4(a[0], a[1], max)
        if nom == "addm4":
            return quit4(a[0], a[1], lambda x, y: (x + y) & 3)
        if nom == "cmp3":
            return ~a[0] & MASK
        if nom == "gdot":
            x, y = a[0].to_bytes(4, "big"), a[1].to_bytes(4, "big")
            return sum(p * q for p, q in zip(x, y)) & MASK
        f = fs[nom]
        env = dict(zip(f.params, a))
        try:
            ex(f.corps, env)
        except Ret as r:
            return r.args[0]
        return 0

    def ex(bloc, env):
        for s in bloc:
            g = s[0]
            if g == "soit" or g == "affecter":
                env[s[1]] = ev(s[2], env)
            elif g == "ecrire":
                a = ev(s[2], env)
                et = s[1] if isinstance(s[1], int) else ev(s[1], env) & 3
                v = ev(s[3], env)
                mem[(et, a & 0xFFFFFF)] = v
            elif g == "si":
                if ev(s[1], env) != 0:
                    ex(s[2], env)
                elif s[3] is not None:
                    ex(s[3], env)
            elif g == "tantque":
                while ev(s[1], env) != 0:
                    ex(s[2], env)
            elif g == "pour":
                env[s[1]] = ev(s[2], env)
                while env[s[1]] < ev(s[3], env):
                    ex(s[4], env)
                    env[s[1]] = (env[s[1]] + 1) & MASK
            elif g == "retour":
                raise Ret(0 if s[1] is None else ev(s[1], env))
            else:
                ev(s[1], env)

    appel("principal", [])
    return out, {k: v for k, v in mem.items() if v}


def vm(src, optim):
    cpu, _, mots = vtx.executer(src, max_pas=3_000_000, optim=optim)
    return cpu.sortie, {k: v for k, v in cpu.mem.items() if k[0] >= 1 and v}, len(mots), cpu.pas


import time
T0 = time.time()
N = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
ecarts, taille, pas, couv, premier = [0, 0, 0], [0, 0], [0, 0], {}, None
for n in range(N):
    src = Gen(random.Random(1000 + n)).programme()
    try:
        o = oracle(src)
        a = vm(src, True)
        b = vm(src, False)
    except Exception as e:  # compilation ou exécution en échec
        ecarts[0] += 1
        premier = premier or (src, f"exception : {e}")
        continue
    taille[0] += b[2]
    taille[1] += a[2]
    pas[0] += b[3]
    pas[1] += a[3]
    for nom, cond in (("&& ou ||", "&&" in src or "||" in src), ("pour", " pour " in src), ("tantque", "tantque" in src),
                      ("étage variable", "@(" in src), ("prélude", any(f in src for f in ("abs(", "inf(", "sup(", "poids("))),
                      ("retour anticipé", "retour" in src.split("principal")[0] and "    si " in src), ("fonctions", "fonction f" in src)):
        couv[nom] = couv.get(nom, 0) + bool(cond)
    for i, (x, y) in enumerate(((a[:2], o), (b[:2], o), (a[:2], b[:2]))):
        if x != y:
            ecarts[i] += 1
            premier = premier or (src, f"cas {i}: sorties {x[0][:6]} / {y[0][:6]}")
print(f"{N} programmes aléatoires")
print(f"écarts : optimisé contre oracle {ecarts[0]} · simple contre oracle {ecarts[1]} · optimisé contre simple {ecarts[2]}")
print("couverture : " + ", ".join(f"{k} {100 * v / N:.0f} %" for k, v in couv.items()))
print(f"taille moyenne : {taille[0] / N:.0f} mots (simple) -> {taille[1] / N:.0f} (optimisé), soit {100 * (1 - taille[1] / taille[0]):.0f} % en moins")
print(f"instructions moyennes : {pas[0] / N:.0f} (simple) -> {pas[1] / N:.0f} (optimisé), soit {100 * (1 - pas[1] / pas[0]):.0f} % en moins")
if premier:
    print("\nPremier écart :\n" + premier[0][:1500] + "\n" + premier[1])

print(f"durée : {time.time() - T0:.0f} s")
