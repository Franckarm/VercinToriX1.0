# Générateur de programmes aléatoires avec la logique à quatre valeurs et les quits.
import random
LITS = ["0", "1", "2", "3", "7", "255", "256", "65535", "4294967295", "#3A7F1C80", "0q0123", "0xAAAA5555"]
INT_OPS = ["+", "-", "*", "&", "|", "^", "<<", ">>", "<<q", ">>q", "==", "!=", "<", ">=", ".<", ".>=", "&&", "||"]
NOMS = ["vrai", "faux", "inconnu", "variable"]


class GenLogique:
    def __init__(self, r):
        self.r = r
        self.fl = []   # fonctions : (nom, types des paramètres, type rendu)

    def ie(self, iv, lv, d):
        r = self.r
        if d == 0 or r.random() < .3:
            return r.choice(iv) if iv and r.random() < .5 else r.choice(LITS)
        k = r.random()
        e = lambda: self.ie(iv, lv, d - 1)
        if k < .30:
            return f"({e()} {r.choice(INT_OPS)} {e()})"
        if k < .40:
            return f"entier({self.le(iv, lv, d - 1)})"
        if k < .48:
            return f"({self.le(iv, lv, d - 1)} {r.choice(['==', '!='])} {r.choice(NOMS + lv) if lv else 'vrai'})"
        if k < .58:
            return f"{r.choice(['et4', 'ou4', 'fusion', 'consensus'])}({e()}, {e()})"
        if k < .64:
            return f"{r.choice(['non4', 'anti', 'cmp3', 'nb_bits'])}({e()})"
        if k < .72:
            return f"{r.choice(['min4', 'max4', 'addm4', 'qegal'])}({e()}, {e()})"
        if k < .78:
            return f"({e()}).q(({e()}) & 15)"
        if k < .82:
            return f"(vrai {r.choice(['+', '*', '|'])} faux)"
        fs = [f for f in self.fl if f[2] == "e"]
        if fs:
            nom, ps, _ = r.choice(fs)
            return f"{nom}({', '.join(self.arg(t, iv, lv, d - 1) for t in ps)})"
        return f"({e()} + 1)"

    def arg(self, t, iv, lv, d):
        return self.le(iv, lv, d) if t == "logique" else self.ie(iv, lv, d)

    def le(self, iv, lv, d):
        r = self.r
        if d == 0 or r.random() < .3:
            return r.choice(lv) if lv and r.random() < .5 else r.choice(NOMS)
        k = r.random()
        e = lambda: self.le(iv, lv, d - 1)
        if k < .40:
            return f"{r.choice(['et4', 'ou4', 'fusion', 'consensus'])}({e()}, {e()})"
        if k < .60:
            return f"{r.choice(['non4', 'anti'])}({e()})"
        if k < .75:
            return f"{r.choice(['logique', 'comme_logique'])}({self.ie(iv, lv, d - 1)})"
        fs = [f for f in self.fl if f[2] == "logique"]
        if fs:
            nom, ps, _ = r.choice(fs)
            return f"{nom}({', '.join(self.arg(t, iv, lv, d - 1) for t in ps)})"
        return e()

    def stmt(self, iv, lv, d, rt, ind):
        r = self.r
        k = r.random()
        if k < .15 and lv:
            return f"{ind}{r.choice(lv)} = {self.le(iv, lv, 2)};"
        if k < .25 and iv:
            return f"{ind}{r.choice(iv)} = {self.ie(iv, lv, 2)};"
        if k < .45:
            return f"{ind}sortie({self.ie(iv, lv, 2)});"
        if k < .65 and d < 2:
            noms = NOMS[:]
            r.shuffle(noms)
            out, i = [], 0
            while i < len(noms) and r.random() < .8:
                n = r.randint(1, 2)
                grp = noms[i:i + n]
                i += n
                corps = "\n".join(self.stmt(iv, lv, d + 1, rt, ind + "    ") for _ in range(r.randint(1, 2)))
                out.append(f"{ind}    {', '.join(grp)} {{\n{corps}\n{ind}    }}")
            if r.random() < .5:
                corps = "\n".join(self.stmt(iv, lv, d + 1, rt, ind + "    ") for _ in range(r.randint(0, 2)))
                out.append(f"{ind}    autre {{\n{corps}\n{ind}    }}")
            r.shuffle(out)
            return f"{ind}selon {self.le(iv, lv, 2)} {{\n" + "\n".join(out) + f"\n{ind}}}"
        if k < .75 and d < 2:
            corps = "\n".join(self.stmt(iv, lv, d + 1, rt, ind + "    ") for _ in range(r.randint(1, 2)))
            return f"{ind}si {self.le(iv, lv, 2)} == {r.choice(NOMS)} {{\n{corps}\n{ind}}}"
        if k < .85 and rt:
            v = self.le(iv, lv, 2) if rt == "logique" else self.ie(iv, lv, 2)
            return f"{ind}si {self.ie(iv, lv, 1)} {{\n{ind}    retour {v};\n{ind}}}"
        return f"{ind}sortie(entier({self.le(iv, lv, 2)}));"

    def fonction(self, nom, ps, rt):
        r = self.r
        iv = [p for p, t in ps if t == "e"]
        lv = [p for p, t in ps if t == "logique"]
        decl = []
        for j in range(r.randint(1, 3)):
            if r.random() < .5:
                decl.append(f"    soit l{j}: logique = {self.le(iv, lv, 2)};")
                lv.append(f"l{j}")
            else:
                decl.append(f"    soit m{j} = {self.ie(iv, lv, 2)};")
                iv.append(f"m{j}")
        corps = [self.stmt(iv, lv, 0, rt, "    ") for _ in range(r.randint(2, 6))]
        if rt is None:
            fin = "".join(f"    sortie(entier({v}));\n" for v in lv[-2:])
        else:
            fin = f"    retour {self.le(iv, lv, 2) if rt == 'logique' else self.ie(iv, lv, 2)};\n"
        sig = ", ".join(f"{p}: logique" if t == "logique" else p for p, t in ps)
        rs = ": logique" if rt == "logique" else ""
        return f"fonction {nom}({sig}){rs} {{\n" + "\n".join(decl + corps) + "\n" + fin + "}\n"

    def programme(self):
        r, out = self.r, []
        for j in range(r.randint(0, 2)):
            ps = [(f"p{k}", r.choice(["e", "logique"])) for k in range(r.randint(1, 2))]
            rt = r.choice(["e", "logique"])
            out.append(self.fonction(f"f{j}", ps, rt))
            self.fl.append((f"f{j}", [t for _, t in ps], rt))
        out.append(self.fonction("principal", [], None))
        return "\n".join(out)
