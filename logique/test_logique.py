#!/usr/bin/env python3
"""Logique à quatre valeurs de vtx : vérifie contre une référence Python écrite à partir de la définition (deux bits de
preuve par valeur : v, preuve du vrai ; f, preuve du faux).
 1. Tables complètes : et4, ou4, fusion, consensus (16 paires), non4, anti (4 valeurs), logique(), comme_logique().
 2. 16 logiques par mot : 300 paires de mots aléatoires, chaque quit comparé à la table.
 3. selon : une branche au plus, « autre », plusieurs valeurs par branche, valeur calculée une seule fois.
 4. Double sens de vrai et faux : entiers 1 et 0 comme avant, logiques là où un logique est attendu.
 5. Erreurs refusées à la compilation.
 6. Capteurs bruités : les trois façons de compter donnent le résultat de la référence ; coût de chacune."""
import importlib.util
import os
import random

ici = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("vtx", os.path.join(ici, "..", "vtx.py"))
vtx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vtx)
M32 = 0xFFFFFFFF
CODE = {"inconnu": 0, "faux": 1, "vrai": 2, "variable": 3}
NOM = {v: k for k, v in CODE.items()}


def vf(c):
    return (c >> 1) & 1, c & 1


def code(v, f):
    return (v << 1) | f


REF = {
    "et4": lambda a, b: code(vf(a)[0] & vf(b)[0], vf(a)[1] | vf(b)[1]),
    "ou4": lambda a, b: code(vf(a)[0] | vf(b)[0], vf(a)[1] & vf(b)[1]),
    "fusion": lambda a, b: code(vf(a)[0] | vf(b)[0], vf(a)[1] | vf(b)[1]),
    "consensus": lambda a, b: code(vf(a)[0] & vf(b)[0], vf(a)[1] & vf(b)[1]),
    "non4": lambda a: code(vf(a)[1], vf(a)[0]),
    "anti": lambda a: code(1 - vf(a)[1], 1 - vf(a)[0]),
}


def run(src, entrees=(), **kw):
    return vtx.executer(src, list(entrees), max_pas=50_000_000, **kw)[0].sortie


# --- 1. tables
corps = []
for op in ("et4", "ou4", "fusion", "consensus"):
    corps.append(f"pour a dans 0..4 {{ pour b dans 0..4 {{ sortie(entier({op}(comme_logique(a), comme_logique(b)))); }} }}")
for op in ("non4", "anti"):
    corps.append(f"pour a dans 0..4 {{ sortie(entier({op}(comme_logique(a)))); }}")
corps.append("sortie(entier(logique(0))); sortie(entier(logique(7))); sortie(entier(comme_logique(6)));")
obtenu = run("fonction principal() { " + " ".join(corps) + " }")
attendu = [REF[op](a, b) for op in ("et4", "ou4", "fusion", "consensus") for a in range(4) for b in range(4)]
attendu += [REF[op](a) for op in ("non4", "anti") for a in range(4)]
attendu += [CODE["faux"], CODE["vrai"], 2]
print(f"1. Tables complètes (et4, ou4, fusion, consensus : 16 paires ; non4, anti : 4 valeurs ; conversions) : "
      f"{sum(x == y for x, y in zip(obtenu, attendu))}/{len(attendu)} identiques à la référence")
assert obtenu == attendu
print("   tables :")
for op in ("et4", "ou4", "fusion"):
    print(f"   {op:9}" + "".join(f"{NOM[b][:3]:>5}" for b in range(4)))
    for a in range(4):
        print(f"   {NOM[a]:>9}" + "".join(f"{NOM[REF[op](a, b)][:3]:>5}" for b in range(4)))

# --- 2. 16 logiques par mot
r = random.Random(4)
mots = [(r.getrandbits(32), r.getrandbits(32)) for _ in range(300)]
src = ("fonction principal() { soit n = entrée(); pour k dans 0..n { soit x = entrée(); soit y = entrée(); "
       "sortie(et4(x, y)); sortie(ou4(x, y)); sortie(fusion(x, y)); sortie(consensus(x, y)); sortie(non4(x)); "
       "sortie(anti(x)); } }")
obtenu = run(src, [len(mots)] + [v for p in mots for v in p])


def par_quit(f, *ws):
    return sum(f(*[(w >> (2 * q)) & 3 for w in ws]) << (2 * q) for q in range(16))


attendu = []
for x, y in mots:
    attendu += [par_quit(REF[op], x, y) for op in ("et4", "ou4", "fusion", "consensus")]
    attendu += [par_quit(REF[op], x) for op in ("non4", "anti")]
print(f"2. 16 logiques par mot : {len(mots)} paires de mots, {len(attendu) * 16:,} opérations : "
      f"{sum(x == y for x, y in zip(obtenu, attendu))}/{len(attendu)} mots identiques")
assert obtenu == attendu

# --- 3. selon
src = """
fonction compte(): logique { @2[0] = @2[0] + 1; retour comme_logique(@2[1]); }
fonction principal() {
    pour c dans 0..4 {
        @2[1] = c;
        soit r = 0;
        selon compte() {
            vrai { r = 10; }
            faux, inconnu { r = 20; }
            autre { r = 30; }
        }
        sortie(r);
        soit r2 = 5;
        selon comme_logique(c) {
            variable { r2 = 6; }
        }
        sortie(r2);
    }
    sortie(@2[0]);
}
"""
obtenu = run(src)
attendu = [20, 5, 20, 5, 10, 5, 30, 6, 4]
print(f"3. selon (plusieurs valeurs par branche, autre, branche absente, valeur calculée une fois) : {obtenu == attendu}")
assert obtenu == attendu, obtenu

# --- 4. double sens de vrai et faux
src = """
fonction ouvre(p: logique): logique { retour non4(p); }
fonction principal() {
    soit k = 0;
    tantque vrai { k = k + 1; si k > 2 { arrêter; } }
    sortie(k);
    sortie(vrai + faux);
    soit p: logique = vrai;
    sortie(entier(p));
    sortie(p == vrai);
    sortie(p != faux);
    sortie(entier(fusion(vrai, faux)));
    sortie(entier(ouvre(faux)));
    soit q: logique = inconnu;
    sortie(entier(anti(q)));
    sortie(q == variable);
}
"""
obtenu = run(src)
attendu = [3, 1, 2, 1, 1, 3, 2, 3, 0]
print(f"4. vrai et faux : entiers 1 et 0 comme avant (tantque vrai, vrai + faux), logiques là où un logique est attendu : "
      f"{obtenu == attendu}")
assert obtenu == attendu, obtenu

# --- 5. erreurs
ERREURS = [
    ("logique comme condition", "fonction principal() { soit p: logique = vrai; si p { sortie(1); } }"),
    ("arithmétique sur un logique", "fonction principal() { soit p: logique = vrai; sortie(p + 1); }"),
    ("&& sur des logiques", "fonction principal() { soit p: logique = vrai; soit q: logique = faux; sortie(p && q); }"),
    ("entier rangé dans un logique", "fonction principal() { soit p: logique = 1; }"),
    ("mélange logique et entier", "fonction principal() { soit p: logique = vrai; sortie(entier(et4(p, 5))); }"),
    ("~ sur un logique", "fonction principal() { soit p: logique = vrai; sortie(entier(~p)); }"),
    ("non sur un logique", "fonction principal() { soit p: logique = vrai; sortie(non p); }"),
    ("nom réservé", "fonction principal() { soit inconnu = 3; }"),
    ("branche en double", "fonction principal() { selon vrai { vrai { } vrai { } } }"),
    ("branche inconnue", "fonction principal() { selon vrai { peut_etre { } } }"),
    ("comparaison logique / entier", "fonction principal() { soit p: logique = vrai; sortie(p == 2); }"),
]
refus = 0
for nom, src in ERREURS:
    try:
        vtx.compiler(src)
        print("   ÉCHEC accepté :", nom)
    except vtx.VtxError as e:
        refus += 1
print(f"5. Erreurs refusées à la compilation : {refus}/{len(ERREURS)}")
assert refus == len(ERREURS)

# --- 6. capteurs bruités


def tirage(i, s):
    x = (i * 2654435761 + s * 2246822519) & M32
    x ^= x >> 15
    x = (x * 2246822519) & M32
    x ^= x >> 13
    return x >> 8


def lecture(i, s):
    vraie = tirage(i, 7) & 1
    h = tirage(i, s) & 15
    if h >= 14:
        return 0
    if h >= 12:
        vraie = 1 - vraie
    return 1 + vraie


compte = [0] * 4
for i in range(4096):
    compte[REF["fusion"](lecture(i, 1), lecture(i, 2))] += 1
attendu = [compte[2], compte[1], compte[0], compte[3]]
src = open(os.path.join(ici, "capteurs.vtx"), encoding="utf-8").read()
pas = {}
for mode in range(4):
    cpu = vtx.executer(src, [mode], max_pas=50_000_000, dossier=ici)[0]
    pas[mode] = cpu.pas
    if mode:
        assert cpu.sortie == attendu, (mode, cpu.sortie, attendu)
cout = {m: pas[m] - pas[0] for m in (1, 2, 3)}
print(f"6. Capteurs bruités, 4 096 portes : vrai {attendu[0]}, faux {attendu[1]}, inconnu {attendu[2]}, variable {attendu[3]} "
      f"(identique à la référence dans les trois modes)")
print(f"   instructions : booléens à l'ancienne {cout[3]:,} ; un logique par porte {cout[1]:,} ; 16 portes par mot "
      f"{cout[2]:,} (gain {cout[3] / cout[2]:.2f} sur les booléens)")
