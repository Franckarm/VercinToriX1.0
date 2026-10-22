"""La correction d'erreur diamant (bibliotheque/diamant.vtx) contre une référence Python indépendante :
1. toute erreur d'un niveau sur un quit (+1 ou -1, sur l'un des 16 quits) est corrigée : état faux, donnée retrouvée ;
2. le damier détecte toute erreur d'un niveau ;
3. deux erreurs : part détectée (variable) et part mal corrigée, mesurées ;
4. un canal bruité (probabilité d'erreur par quit) : intact, corrigé, détecté, trompé, avec et sans diamant."""
import os, random, shutil, subprocess, sys, tempfile
ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, racine)
import vtx  # noqa: E402

def quit(m, k): return (m >> (2 * k)) & 3
def poser(m, k, v): return (m & ~(3 << (2 * k)) & 0xFFFFFFFF) | ((v & 3) << (2 * k))
CONTROLE = (0, 3, 15)
DONNEES = [k for k in range(16) if k not in CONTROLE]
def signature(m): return sum((k + 1) * quit(m, k) for k in range(16)) % 33
def proteger(d):
    m = 0
    for j, k in enumerate(DONNEES):
        m = poser(m, k, (d >> (2 * j)) & 3)
    t = (33 - signature(m)) % 33
    return poser(poser(poser(m, 0, t & 3), 3, (t >> 2) & 3), 15, t >> 4)
def etat(m):
    if m == 0: return "inconnu"
    s = signature(m)
    if s == 0: return "vrai"
    k, sens = (s - 1, -1) if s <= 16 else (32 - s, +1)
    if (sens == -1 and quit(m, k) == 0) or (sens == 1 and quit(m, k) == 3): return "variable"
    return "faux"
def corriger(m):
    s = signature(m)
    if s == 0: return m
    k, sens = (s - 1, -1) if s <= 16 else (32 - s, +1)
    v = quit(m, k) + sens
    return m if v < 0 or v > 3 else poser(m, k, v)
def donnee(m): return sum(quit(m, k) << (2 * j) for j, k in enumerate(DONNEES))
def bruiter(m, k, e):
    v = quit(m, k) + e
    return None if v < 0 or v > 3 else poser(m, k, v)

hasard = random.Random(3)
RAPIDE = os.environ.get("VTX_RAPIDE") == "1"
# cas : (donnée, mot lu)
cas = []
for _ in range(40 if RAPIDE else 150):
    d = hasard.randrange(1, 1 << 26)
    m = proteger(d)
    cas.append((d, m))
    for k in range(16):
        for e in (1, -1):
            b = bruiter(m, k, e)
            if b is not None:
                cas.append((d, b))
    for _ in range(4):                              # deux erreurs
        b, ks = m, hasard.sample(range(16), 2)
        for k in ks:
            b2 = bruiter(b, k, hasard.choice((1, -1)))
            b = b2 if b2 is not None else b
        cas.append((d, b))
# le programme vtx : pour chaque mot lu, l'état, le mot corrigé, la donnée ; puis le damier
NOMS = {0: "inconnu", 1: "faux", 2: "vrai", 3: "variable"}
src = 'importer "diamant.vtx";\nfonction principal() {\n    soit n = entrée();\n    pour i dans 0..n {\n' \
      '        soit m = entrée();\n        sortie(entier(diamant_etat(m)));\n        soit c = diamant_corriger(m);\n' \
      '        sortie(c);\n        sortie(diamant_donnee(c));\n        soit p = damier_proteger(entrée());\n' \
      '        sortie(p);\n        sortie(entier(damier_etat(p)));\n        sortie(entier(damier_etat(p ^ entrée())));\n    }\n}\n'
entrees = [len(cas)]
erreurs_damier = []
for d, m in cas:
    x = hasard.randrange(1 << 30)
    p = (x & 0x3FFFFFFF) << 2
    p |= sum(quit(p, k) for k in range(1, 16)) & 1
    k = hasard.randrange(16)
    q = quit(p, k)
    e = 1 if q < 3 else -1
    masque = p ^ poser(p, k, q + e)
    erreurs_damier.append((x, p, masque))
    entrees += [m, x, masque]
cpu, _, _ = vtx.executer(src, entrees, max_pas=500_000_000, dossier=ici)
s = cpu.sortie
bons = 0
stats = {"vrai": 0, "faux": 0, "variable": 0, "trompé": 0}
for i, ((d, m), (x, p, masque)) in enumerate(zip(cas, erreurs_damier)):
    e_, c_, d_, p_, dv, dd = s[6 * i: 6 * i + 6]
    ok = (NOMS[e_] == etat(m) and c_ == corriger(m) and d_ == donnee(corriger(m)) and p_ == p
          and NOMS[dv] == "vrai" and NOMS[dd] == "variable")
    bons += ok
total = len(cas)
print(f"Diamant en vtx contre la référence : {bons}/{total} lectures identiques (état, mot corrigé, donnée, damier)")
# 1. erreurs simples
un = [(d, m) for d, m in cas if m != proteger(d) and sum(quit(m, k) != quit(proteger(d), k) for k in range(16)) == 1]
ok1 = all(etat(m) == "faux" and donnee(corriger(m)) == d for d, m in un)
print(f"1. Une erreur d'un niveau, sur n'importe quel quit : {len(un)} cas, tous corrigés : {'oui' if ok1 else 'NON'}")
# 3. deux erreurs
deux = [(d, m) for d, m in cas if sum(quit(m, k) != quit(proteger(d), k) for k in range(16)) == 2]
for d, m in deux:
    e = etat(m)
    if e == "variable": stats["variable"] += 1
    elif donnee(corriger(m)) != d: stats["trompé"] += 1
    else: stats["faux"] += 1
print(f"3. Deux erreurs ({len(deux)} cas) : détectées sans correction {stats['variable']}, trompé {stats['trompé']}, "
      f"retrouvées {stats['faux']}")
# 4. canal bruité
print("4. Canal bruité (probabilité d'erreur d'un niveau par quit), 20 000 mots :")
for p in (0.001, 0.005, 0.01, 0.03):
    r = {"intact": 0, "corrigé": 0, "détecté": 0, "trompé": 0}
    brut_faux = 0
    for _ in range(20000):
        d = hasard.randrange(1, 1 << 26)
        m = proteger(d)
        b = m
        for k in range(16):
            if hasard.random() < p:
                b2 = bruiter(b, k, hasard.choice((1, -1)))
                b = b2 if b2 is not None else bruiter(b, k, 1 if quit(b, k) == 0 else -1)
        brut_faux += any(quit(b, k) != quit(m, k) for k in DONNEES)
        e = etat(b)
        if e == "vrai" and b == m: r["intact"] += 1
        elif e == "variable": r["détecté"] += 1
        elif donnee(corriger(b)) == d: r["corrigé"] += 1
        else: r["trompé"] += 1
    print(f"   p = {p:<6} sans code : {brut_faux / 200:.2f} % de mots faux ; avec diamant : corrigés {r['corrigé'] / 200:.2f} %, "
          f"détectés {r['détecté'] / 200:.3f} %, trompés {r['trompé'] / 200:.3f} %")
sys.exit(0 if bons == total and ok1 else 1)
