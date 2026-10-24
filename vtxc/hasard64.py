# Programmes aléatoires pour comparer vtxc64 et vtx64.py (mots identiques exigés)
import random

LIT_E = ["0", "1", "7", "42", "255", "65535", "4294967295", "4294967296", "123456789012", "18446744073709551615",
         "0x2A", "0xFFFF_FFFF_FFFF", "0q0123", "0q3333_2222", "#FF8000", "#12345678", "#0123456789ABCDEF", "42L",
         "'a'", "adn\"ACGT\"", "adn\"TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT\"", "9223372036854775808", "2147483647",
         "2147483648", "N1", "N2"]
LIT_I = ["0S", "5S", "4000000000S", "0x7FFFFFFFS", "4294967295S", "N3"]
LIT_F = ["0.0", "1.5", "0.1", "2.5e10", "1e-5", "3.14159", "1e300", "7D", "123.456e-7", "2.0", "F1", "F2"]
LIT_S = ["1.5S", "0.25S", "3e8S", "1e-3S", "F3"]
LIT_W = ["5LL", "0xFFFFFFFFFFFFFFFFFFLL", "#0123456789ABCDEF_FEDCBA9876543210", "#01020304_05060708_090A0B0C_0D0E0F10",
         "adn\"ACGTACGTACGTACGTACGTACGTACGTACGTACGT\"", "W1"]
LIT_X = ["1.5Q", "0.1Q", "2Q", "1e-30Q", "X1"]
CONSTS = """constante N1 = 1234567;
constante N2 = 0 - 77;
constante N3 = 0 - 5S;
constante F1 = 0 - 2.5;
constante F2 = 1e10;
constante F3 = 0 - 0.5S;
constante W1 = 0 - 3LL;
constante X1 = 0 - 0.75Q;
constante K = 3 << 4 | 1;
"""


class G:
    def __init__(self, r):
        self.r = r
        self.n = 0

    def nv(self):
        self.n += 1
        return self.n

    def lit(self, t):
        return self.r.choice({"e": LIT_E, "i": LIT_I, "f": LIT_F, "s": LIT_S, "w": LIT_W, "x": LIT_X}[t])

    def var(self, t, env):
        vs = [v for v, tt in env if tt == t]
        return self.r.choice(vs) if vs else self.lit(t)

    def e(self, t, env, d=0):
        r = self.r
        k = r.random()
        if d > 3 or k < 0.3:
            return self.lit(t) if r.random() < 0.4 else self.var(t, env)
        if t == "e":
            op = r.choice(["+", "-", "*", "/", "%", "&", "|", "^", "<<", ">>", "./", ".%", ".>>", "<<q", ">>q"])
            if r.random() < 0.1:
                return f"({self.e('e', env, d + 1)} {r.choice(['<', '==', '!=', '.<', '>=', '<=', '.>='])} {self.e('e', env, d + 1)})"
            if r.random() < 0.08:
                return f"entier({self.e(r.choice('fs'), env, d + 1)})"
            if r.random() < 0.06:
                return f"{self.e('e', env, d + 1)}.{r.choice('rvba')}"
            if r.random() < 0.06:
                return f"mul_haut({self.e('e', env, d + 1)}, {self.e('e', env, d + 1)})"
            if r.random() < 0.05:
                return f"bas({self.e('w', env, d + 1)})"
            if r.random() < 0.05:
                return f"q[{r.randrange(0, 60)}]"
            if r.random() < 0.05:
                return f"@2[{r.randrange(0, 30)}]"
            if r.random() < 0.04:
                return f"bits({self.e('f', env, d + 1)})"
            if r.random() < 0.04:
                return f"f2({self.e('e', env, d + 1)}, {self.e('e', env, d + 1)})"
            if r.random() < 0.12:
                # les petites fonctions que l'expansion en ligne recopie (ou refuse de recopier)
                g = r.choice(["g1", "g3", "g4", "g6", "g7", "g9", "g11", "g12"])
                if g in ("g1", "g4", "g12"):
                    return f"{g}({self.e('e', env, d + 1)}, {self.e('e', env, d + 1)})"
                return f"{g}({self.e('e', env, d + 1)})"
            if r.random() < 0.03:
                return f"entier(g5({self.e('f', env, d + 1)}))"
            if r.random() < 0.03:
                return f"entier(g8({self.e('i', env, d + 1)}))"
            return f"({self.e('e', env, d + 1)} {op} {self.e(r.choice('ei'), env, d + 1)})"
        if t == "i":
            op = r.choice(["+", "-", "*", "/", "%", "&", "|", "^", "<<", ">>", "./", ".%", ".>>"])
            if r.random() < 0.1:
                return f"entier_32({self.e('e', env, d + 1)})"
            return f"({self.e('i', env, d + 1)} {op} {self.e('i', env, d + 1)})"
        if t in "fs":
            op = r.choice(["+", "-", "*", "/"])
            if r.random() < 0.1:
                return f"racine({self.e(t, env, d + 1)})"
            if r.random() < 0.1:
                return f"{'flottant' if t == 'f' else 'flottant_32'}({self.e('e', env, d + 1)})"
            if r.random() < 0.08:
                return f"{r.choice(['abs', 'min', 'max'])}({self.e(t, env, d + 1)}{', ' + self.e(t, env, d + 1) if r.random() < 0.6 else ''})".replace("abs(", "abs(") if False else f"abs({self.e(t, env, d + 1)})"
            if r.random() < 0.06 and t == "f":
                return f"(0.0 - {self.e('f', env, d + 1)})"
            return f"({self.e(t, env, d + 1)} {op} {self.e(t, env, d + 1)})"
        if t == "w":
            op = r.choice(["+", "-", "*", "&", "|", "^", "/", "%", "<<", ">>"])
            if op in ("<<", ">>"):
                return f"({self.e('w', env, d + 1)} {op} {r.randrange(0, 130)})"
            return f"({self.e('w', env, d + 1)} {op} {self.e(r.choice('wwe'), env, d + 1)})"
        if t == "x":
            op = r.choice(["+", "-", "*", "/"])
            return f"({self.e('x', env, d + 1)} {op} {self.e(r.choice('xxf'), env, d + 1)})"

    def cond(self, env):
        r = self.r
        t = r.choice("eeeifsw")
        o = r.choice(["<", "<=", ">", ">=", "==", "!="] + ([".<", ".>="] if t in "ei" else []))
        c = f"{self.e(t, env, 2)} {o} {self.e(t, env, 2)}"
        if r.random() < 0.2:
            c = f"{c} && {self.e('e', env, 3)} != 0"
        if r.random() < 0.1:
            c = f"!({c}) || {self.e('e', env, 3)} < 5"
        return c

    def bloc(self, env, n, d=0):
        r = self.r
        out = []
        for _ in range(n):
            k = r.random()
            if k < 0.25 or d > 2:
                t = r.choice("eeeiifswx")
                v = f"v{self.nv()}"
                annot = {"i": ": entier_32", "s": ": flottant_32", "w": ": entier_petuar", "x": ": flottant_petuar"}.get(t, "")
                if t == "e" and r.random() < 0.3:
                    annot = ": entier"
                out.append(f"soit {v}{annot} = {self.e(t, env)};")
                env.append((v, t))
            elif k < 0.40 and env:
                v, t = r.choice(env)
                out.append(f"{v} = {self.e(t, env)};")
            elif k < 0.48:
                out.append(f"si {self.cond(env)} {{ {' '.join(self.bloc(list(env), 2, d + 1))} }} sinon {{ {' '.join(self.bloc(list(env), 1, d + 1))} }}")
            elif k < 0.56:
                i = f"i{r.randrange(1000)}"
                e2 = list(env) + [(i, "e")]
                out.append(f"pour {i} dans 0..{r.randrange(1, 6)} {{ {' '.join(self.bloc(e2, 2, d + 1))} }}")
            elif k < 0.62:
                i = f"j{r.randrange(1000)}"
                out.append(f"pour {i} dans 0..60 {{ q[{i}] = (q[{i}] + {r.randrange(4)}) % 4; }}")
            elif k < 0.66:
                out.append(f"@2[{r.randrange(30)}] = {self.e('e', env, 2)};")
            elif k < 0.70:
                u = self.nv()
                out.append(f"soit a{u} = cube_adresse(2, {r.randrange(3)}, {r.randrange(100)}); @[a{u}] = {self.e('e', env, 2)}; sortie(@[a{u}]);")
            elif k < 0.75 and env:
                v, t = r.choice(env)
                out.append(f"sortie({v});")
            elif k < 0.80 and env:
                v, t = r.choice(env)
                if t in "eifswx":
                    out.append(f"afficher({v});")
            elif k < 0.84:
                u = self.nv()
                out.append(f"soit p{u} = P {{ x: {self.e('e', env, 2)}, y: {self.e('e', env, 2)} }}; sortie(p{u}.x + p{u}.y);"
                           + (f" t4(p{u}, {self.e('e', env, 2)}); sortie(g2(p{u}) + g2(p{u}));" if r.random() < 0.6 else "")
                           + (f" t3({self.e('e', env, 2)}, {self.e('e', env, 2)}); g1({self.e('e', env, 2)}, 1);"
                              if r.random() < 0.5 else ""))
            elif k < 0.88:
                n2 = r.randrange(2, 5)
                out.append(f"t1({self.e('e', env, 2)}); t2({self.e('e', env, 2)});" if r.random() < 0.5 else
                           f"hypothèse {{ @3[{r.randrange(100, 200)}] = {self.e('e', env, 2)}; si {self.cond(env)} {{ annuler; }} }}")
            elif k < 0.92:
                u = self.nv()
                lg = r.choice(["vrai", "faux", "inconnu", "variable"])
                out.append(f"soit l{u}: logique = {lg}; selon et4(l{u}, {r.choice(['vrai', 'faux'])}) {{ vrai {{ sortie(1); }} faux, inconnu {{ sortie(2); }} autre {{ sortie(3); }} }}")
            else:
                i = f"k{r.randrange(1000)}"
                out.append(f"pour {i} dans 0..48 en 6 segments {{ @2[100 + {i}] = {i} * 3; }}")
        return out

    def programme(self):
        r = self.r
        corps = self.bloc([], r.randrange(4, 12))
        return (CONSTS + "structure P { x, y }\ntableau q[64] de quits @2[1000];\n"
                "fonction f2(a, b) { soit s = 0; pour i dans 0..a % 7 { s = s + b * i; } retour s; }\n"
                "fonction t1(x) { @2[500] = x; }\nfonction t2(x) { @2[600] = x + 1; }\n"
                "fonction g1(a, b) { retour a * 3 + b; }\n"
                "fonction g2(p: P) { retour p.x + p.y; }\n"
                "fonction g3(a) { retour f2(a, a) + 1; }\n"
                "fonction g4(a, b) { retour a / (b | 1); }\n"
                "fonction g5(x: flottant): flottant { retour x * 2.0 + 1.0; }\n"
                "fonction g6(a) { retour q[a % 64]; }\n"
                "fonction g7(a) { retour g1(a, a + 1) & 255; }\n"
                "fonction g8(a: entier_32): entier_32 { retour a + 1S; }\n"
                "fonction g9(a) { retour @2[a % 30] + a; }\n"
                "fonction g11(a) { retour g9(a) ^ g1(a, 2); }\n"
                "fonction g12(a, b) { retour (a < b) && @2[b % 30] != 0; }\n"
                "fonction t3(a, b) { @2[a % 30] = b; }\nfonction t4(p: P, v) { p.x = v; }\n"
                "fonction principal() {\n    " + "\n    ".join(corps) + "\n}\n")
