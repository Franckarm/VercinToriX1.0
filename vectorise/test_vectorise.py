#!/usr/bin/env python3
"""Réécriture automatique des boucles sur les tableaux de quits et de logiques (16 éléments d'un coup).
 1. 400 programmes aléatoires : bornes constantes ou lues à l'exécution (début et fin au hasard, mots incomplets,
    boucles vides), opérations quit par quit et opérations qui ne le sont pas, plusieurs écritures par boucle,
    tableau écrit et relu, boucles qui comptent (si … == / != … { n = n + 1; }) et qui somment (n = n + t[i]) :
    sorties et mémoire identiques avec et sans réécriture.
 2. Mesure : fusion de 4 096 témoignages, et comparaison de 16 384 bases, écrites élément par élément."""
import importlib.util
import os
import random

RAPIDE = os.environ.get("VTX_RAPIDE") == "1"      # vérification rapide : moins de tirages, pas de grands volumes
ici = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("vtx", os.path.join(ici, "..", "vtx.py"))
vtx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vtx)


def etat(src, entrees, vect):
    vtx.VECTORISER = vect
    try:
        cpu = vtx.executer(src, entrees, max_pas=20_000_000)[0]
    finally:
        vtx.VECTORISER = True
    return cpu.sortie, {k: v for k, v in cpu.mem.items() if k[0] >= 1 and v}, cpu.pas


OPS_Q = ["min4({a}, {b})", "max4({a}, {b})", "addm4({a}, {b})", "cmp3({a})", "({a} & {b})", "({a} | {b})",
         "({a} ^ {b})", "qegal({a}, {b})"]
OPS_L = ["et4({a}, {b})", "ou4({a}, {b})", "non4({a})", "anti({a})", "fusion({a}, {b})", "consensus({a}, {b})"]


def expr(r, sorte, noms, i, prof=0):
    if prof > 2 or r.random() < 0.35:
        if r.random() < 0.75:
            return f"{r.choice(noms)}[{i}]"
        return str(r.randrange(4)) if sorte == "quits" else r.choice(["vrai", "faux", "inconnu", "variable"])
    if r.random() < 0.08:                   # opération qui n'est pas quit par quit : la boucle reste élément par élément
        return (f"({expr(r, sorte, noms, i, prof + 1)} + 1)" if sorte == "quits"
                else f"comme_logique(entier({expr(r, sorte, noms, i, prof + 1)}) + 1)")
    if r.random() < 0.05:                   # indice décalé : pas de réécriture
        return f"{r.choice(noms)}[({i} + 1) % 200]"
    op = r.choice(OPS_Q if sorte == "quits" else OPS_L)
    return op.format(a=expr(r, sorte, noms, i, prof + 1), b=expr(r, sorte, noms, i, prof + 1))


def programme(r):
    sorte = r.choice(["quits", "logique"])
    noms = ["ta", "tb", "tc"]
    lignes = [f"tableau {n}[200] de {sorte} @{e}[{b}];" for n, e, b in zip(noms, (1, 1, 2), (0, 300, 7))]
    lignes += ["tableau va[13] @1[0];", "tableau vb[13] @1[300];", "tableau vc[13] @2[7];"]
    fins = []
    corps = ["    pour i dans 0..200 {"]
    for n in noms:
        if sorte == "quits":
            corps.append(f"        {n}[i] = (i * {r.randint(1, 97)} + {r.randint(0, 9)}) >> {r.randint(0, 3)};")
        else:
            corps.append(f"        {n}[i] = comme_logique((i * {r.randint(1, 97)}) >> {r.randint(0, 3)});")
    corps.append("    }")
    for nb in range(r.randint(1, 3)):
        v = f"j{nb}"
        if r.random() < 0.5:
            a, b = r.randint(0, 60), r.randint(0, 200)
            bornes = f"{a}..{b}"
        else:
            corps.append(f"    soit d{nb} = entrée();\n    soit f{nb} = entrée();")
            bornes = f"d{nb}..f{nb}"
        ecr = []
        for _ in range(r.randint(0 if r.random() < 0.4 else 1, 3)):
            ecr.append(f"        {r.choice(noms)}[{v}] = {expr(r, sorte, noms, v)};")
        for k in range(r.randint(0 if ecr else 1, 2)):      # boucles qui comptent ou qui somment
            acc = f"n{nb}_{k}"
            corps.append(f"    soit {acc} = {r.randint(0, 5)};")
            genre = r.choice(["egal", "different"] + (["somme"] if sorte == "quits" else []))
            if genre == "somme":
                ecr.append(f"        {acc} = {acc} + {expr(r, sorte, noms, v)};")
            else:
                op = "==" if genre == "egal" else "!="
                ecr.append(f"        si {expr(r, sorte, noms, v)} {op} {expr(r, sorte, noms, v)} {{ {acc} = {acc} + 1; }}")
            fins.append(acc)
        corps.append(f"    pour {v} dans {bornes} {{\n" + "\n".join(ecr) + "\n    }")
    corps.append("    pour w dans 0..13 { sortie(va[w]); sortie(vb[w]); sortie(vc[w]); }")
    corps += [f"    sortie({acc});" for acc in fins]
    return "\n".join(lignes) + "\nfonction principal() {\n" + "\n".join(corps) + "\n}\n"


r = random.Random(2027)
ok = reecrits = 0
N = 100 if RAPIDE else 400
for n in range(N):
    src = programme(r)
    entrees = []
    for _ in range(3):
        a = r.randint(0, 200)
        entrees += [a, r.randint(a - 5 if a >= 5 else 0, 200)]
    sans, avec = etat(src, entrees, False), etat(src, entrees, True)
    if sans[:2] == avec[:2]:
        ok += 1
        reecrits += avec[2] < sans[2]
    else:
        print("ÉCHEC", n)
        print(src, entrees)
        break
print(f"1. {N} programmes aléatoires : sorties et mémoire identiques avec et sans réécriture {ok}/{N} ; "
      f"{reecrits} programmes où au moins une boucle a été réécrite")
assert ok == N and reecrits > N // 5

# --- 2. mesures
FUSION = """
tableau a[4096] de logique @1[0];
tableau b[4096] de logique @1[256];
tableau c[4096] de logique @1[512];
fonction principal() {
    soit mode = entrée();
    pour i dans 0..4096 {
        a[i] = comme_logique((i * 2654435761) >> 30);
        b[i] = comme_logique((i * 40503) >> 7);
    }
    si mode == 1 {
        pour j dans 0..4096 {
            c[j] = fusion(a[j], b[j]);
        }
    }
    soit s = 0;
    pour k dans 0..256 { s = s * 31 + @1[512 + k]; }
    sortie(s);
}
"""
BASES = """
tableau g[16384] de quits @1[0];
tableau m[16384] de quits @1[1024];
tableau e[16384] de quits @1[2048];
fonction principal() {
    soit mode = entrée();
    pour i dans 0..16384 {
        g[i] = (i * 2654435761) >> 30;
        m[i] = (i * 40503) >> 9;
    }
    si mode == 1 {
        pour j dans 0..16384 {
            e[j] = qegal(g[j], m[j]);
        }
    }
    soit s = 0;
    pour k dans 0..1024 { s = s * 31 + @1[2048 + k]; }
    sortie(s);
}
"""
ORD_FUSION = """
tableau a[4096] @1[0]; tableau b[4096] @1[4096]; tableau c[4096] @1[8192];
fonction principal() { soit mode = entrée();
 pour i dans 0..4096 { a[i] = (i * 2654435761) >> 30; b[i] = ((i * 40503) >> 7) & 3; }
 si mode == 1 { pour j dans 0..4096 { c[j] = entier(fusion(comme_logique(a[j]), comme_logique(b[j]))); } }
 sortie(c[5]); }
"""
ORD_BASES = """
tableau g[16384] @1[0]; tableau m[16384] @1[16384]; tableau e[16384] @1[32768];
fonction principal() { soit mode = entrée();
 pour i dans 0..16384 { g[i] = (i * 2654435761) >> 30; m[i] = ((i * 40503) >> 9) & 3; }
 si mode == 1 { pour j dans 0..16384 { e[j] = g[j] == m[j]; } }
 sortie(e[5]); }
"""
for nom, src, ordinaire in [("fusion de 4 096 paires de témoignages (tableaux de logique)", FUSION, ORD_FUSION),
                            ("comparaison de 16 384 bases (tableaux de quits)", BASES, ORD_BASES)]:
    base_s, base_a = etat(src, [0], False), etat(src, [0], True)
    sans, avec = etat(src, [1], False), etat(src, [1], True)
    assert sans[:2] == avec[:2]
    cs, ca = sans[2] - base_s[2], avec[2] - base_a[2]
    co = etat(ordinaire, [1], True)[2] - etat(ordinaire, [0], True)[2]
    print(f"2. {nom} : tableau ordinaire (un élément par mot) {co:,} instructions ; tableau rangé lu élément par élément "
          f"{cs:,} ; réécrit 16 d'un coup {ca:,} : gain {co / ca:.1f} sur le tableau ordinaire, {cs / ca:.1f} sur la "
          f"lecture élément par élément")

COMPTE_Q = """
tableau g[16384] de quits @1[0];
tableau m[16384] de quits @1[1024];
fonction principal() {
    soit mode = entrée();
    pour i dans 0..16384 {
        g[i] = (i * 2654435761) >> 30;
        m[i] = (i * 40503) >> 9;
    }
    soit n = 0;
    si mode == 1 {
        pour j dans 0..16384 {
            si g[j] == m[j] { n = n + 1; }
        }
    }
    sortie(n);
}
"""
COMPTE_O = """
tableau g[16384] @1[0]; tableau m[16384] @1[16384];
fonction principal() { soit mode = entrée();
 pour i dans 0..16384 { g[i] = (i * 2654435761) >> 30; m[i] = ((i * 40503) >> 9) & 3; }
 soit n = 0;
 si mode == 1 { pour j dans 0..16384 { si g[j] == m[j] { n = n + 1; } } }
 sortie(n); }
"""
sans, avec = etat(COMPTE_Q, [1], False), etat(COMPTE_Q, [1], True)
assert sans[:2] == avec[:2] and avec[0] == etat(COMPTE_O, [1], True)[0]
ca = avec[2] - etat(COMPTE_Q, [0], True)[2]
co = etat(COMPTE_O, [1], True)[2] - etat(COMPTE_O, [0], True)[2]
print(f"3. compter les bases égales sur 16 384 (si g[j] == m[j] {{ n = n + 1; }}) : {avec[0][0]} égales ; tableau ordinaire "
      f"{co:,} instructions, réécrit 16 d'un coup {ca:,} : gain {co / ca:.1f}")
