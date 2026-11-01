#!/usr/bin/env python3
"""Des réactions tirées au hasard (pour comparer vtxc128 à vtx128.py) : des atomes de chaque genre (calcul, appel d'une
fonction lourde, légère ou impure, si … alors [sinon], rendez-vous, pont, effets, pour chaque), des liaisons qui ne
reviennent jamais sur elles-mêmes, des « apres », des contrats, des unités, et les lignes mélangées."""
import random

TETE = """fonction lourd(n) { soit s = 0; pour i dans 0..n % 50 { s = s + (i * 7 + n) % 11; } retour s; }
fonction leger(x) { retour x * 3 + 1; }
fonction lit(i) { soit s = 0; pour j dans 0..2 { s = s + @2[i % 8]; } retour s; }
fonction flou(x: flottant, k): flottant { soit a = x; pour i dans 0..k % 4 { a = (a + 1.0) * 0.5; } retour a; }
"""


class R:
    def __init__(self, g):
        self.g = g

    def reaction(self, nom, n_atomes, principal=False):
        g = self.g
        params = [] if principal else ["a", "b"]
        dispo = list(params) or []
        lignes, noms_atomes = [], []
        gardees = set()   # les liaisons qui peuvent porter faux (un si sans sinon, et ce qui en dépend)
        k = 0
        if not dispo:
            for v in ("a", "b"):
                lignes.append(f"= {g.randrange(1, 40)} -> {v}")
                dispo.append(v)
        for i in range(n_atomes):
            lues = []

            def pris():
                x = g.choice(dispo)
                lues.append(x)
                return x
            s = f"l{k}"
            genre = g.choice(["bin", "bin", "lourd", "leger", "lit", "si", "sinon", "rdv", "pont", "effet", "chaque",
                              "flou", "unite"])
            nom_at = f"n{i}" if g.random() < 0.25 else None
            pref = f"{nom_at} = " if nom_at else "= "
            apres = ""
            if noms_atomes and g.random() < 0.15:
                apres = f" apres {g.choice(noms_atomes)}"
            if genre == "bin":
                op = g.choice(["+", "-", "×", "*", "&", "|", "^", "%"])
                droite = pris() if op != "%" else str(g.randrange(1, 9))
                lignes.append(f"{pref}{pris()} {op} {droite} -> {s}{apres}")
                dispo.append(s)
            elif genre in ("lourd", "leger", "lit"):
                lignes.append(f"{pref}{genre}({pris()}) -> {s}{apres}")
                dispo.append(s)
            elif genre == "flou":
                lignes.append(f"{pref}entier(flou(flottant({pris()} % 100), {pris()})) -> {s}{apres}")
                dispo.append(s)
            elif genre == "si":
                lignes.append(f"{pref}si {pris()} > {g.randrange(0, 30)} alors {pris()} -> {s}{apres}")
                dispo.append(s)
            elif genre == "sinon":
                lignes.append(f"{pref}si {pris()} < {pris()} alors {pris()} sinon {pris()} + 1 -> {s}{apres}")
                dispo.append(s)
            elif genre == "rdv":
                x, y = pris(), pris()
                lignes.append(f"{pref}rendez-vous({x}, {y}) -> {s}, {s}b{apres}")
                dispo += [s, s + "b"]
            elif genre == "pont":
                case = str(g.randrange(0, 4)) if g.random() < 0.7 else f"{pris()} % 4"
                sortie = f" -> {s}" if g.random() < 0.6 else ""
                lignes.append(f"{pref}pont {pris()} vers @2[{case}]{sortie}{apres}")
                if sortie:
                    dispo.append(s)
            elif genre == "effet":
                lignes.append(f"{pref}{g.choice(['sortie', 'afficher'])}({pris()}){apres}")
            elif genre == "chaque":
                red = g.choice(["somme", "min", "max"])
                lignes.append(f"{pref}{red} pour chaque i dans 0..{g.randrange(2, 9)} : i * {pris()} -> {s}{apres}")
                dispo.append(s)
            elif genre == "unite":
                # une liaison avec unité ne se mêle pas aux autres liaisons, sans unité
                lignes.append(f"{pref}{g.randrange(1, 9)} {g.choice(['km', 'm', 'min', 'h', 's', 'm/s', 'kg·m/s²'])} -> {s}{apres}")
                lignes.append(f"= sortie({s})")
            if genre == "si" or any(x in gardees for x in lues):
                gardees.update(x for x in dispo[len(dispo) - 2:] if x.startswith(s))
            if nom_at:
                noms_atomes.append(nom_at)
            k += 1
        if not principal and g.random() < 0.5:
            lignes.append(f"exige a {g.choice(['>=', '!=', '<'])} {g.randrange(0, 5)}")
        if not principal and g.random() < 0.5:
            lignes.append(f"garantit {g.choice(dispo)} >= 0")
        lignes.append(f"= sortie({g.choice(dispo)})")
        g.shuffle(lignes)
        # le résultat : une liaison toujours là (une réaction qui rend une liaison pouvant porter faux doit la rendre
        # dans un type qui sait le dire, une logique ou un flottant ; ici tout est entier)
        res = "" if principal else f" -> {g.choice([x for x in dispo if x not in gardees])}"
        tete = f"reaction {nom}({', '.join(params)}){res} {{"
        return tete + "\n" + "\n".join("    " + l for l in lignes) + "\n}\n"

    def programme(self):
        g = self.g
        src = TETE
        src += self.reaction("r", g.randrange(3, 14))
        if g.random() < 0.5:
            src += self.reaction("principal", g.randrange(2, 8), principal=True)[:-2] + "    = sortie(r(3, 4))\n}\n"
        else:
            appels = " ".join(f"sortie(r({g.randrange(0, 20)}, {g.randrange(0, 20)}));" for _ in range(g.randrange(1, 4)))
            src += f"fonction principal() {{ {appels} }}\n"
        return src


if __name__ == "__main__":
    print(R(random.Random(1)).programme())
