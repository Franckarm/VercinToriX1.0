#!/usr/bin/env python3
"""Recherche d'un motif de 16 bases dans un génome, avec au plus 2 différences : vérifie motif.vtx contre une référence
Python indépendante, dans les quatre modes, et mesure le coût de chacun. Vérifie aussi les tableaux de quits et de
logiques (rangement 16 par mot) et les instructions QEGAL et COMPTE."""
import importlib.util
import os
import random

ici = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("vtx", os.path.join(ici, "..", "vtx.py"))
vtx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vtx)
M32 = 0xFFFFFFFF


def tirage(i, s):
    x = (i * 2654435761 + s * 2246822519) & M32
    x ^= x >> 15
    x = (x * 2246822519) & M32
    x ^= x >> 13
    return x >> 8


# --- 1. QEGAL et COMPTE
r = random.Random(5)
paires = [(r.getrandbits(32), r.getrandbits(32)) for _ in range(200)] + [(x, x) for x in (0, M32, 0x12345678)]
src = ("fonction principal() { soit n = entrée(); pour k dans 0..n { soit a = entrée(); soit b = entrée(); "
       "sortie(qegal(a, b)); sortie(nb_bits(a)); } }")
obtenu = vtx.executer(src, [len(paires)] + [v for p in paires for v in p], max_pas=10_000_000)[0].sortie
attendu = []
for a, b in paires:
    attendu += [sum(1 << (2 * q) for q in range(16) if (a >> 2 * q) & 3 == (b >> 2 * q) & 3), bin(a).count("1")]
print(f"1. QEGAL et COMPTE : {len(paires)} paires, identiques à la référence : {obtenu == attendu}")
assert obtenu == attendu

# --- 2. tableaux de quits et de logiques
src = """
tableau q[50] de quits @1[100];
tableau vue[4] @1[100];
tableau l[20] de logique @2[0];
fonction principal() {
    soit n = entrée();
    pour k dans 0..n {
        soit i = entrée();
        q[i] = entrée();
    }
    pour j dans 0..50 { sortie(q[j]); }
    pour w dans 0..4 { sortie(vue[w]); }
    l[2] = vrai; l[7] = variable; l[19] = faux;
    sortie(entier(l[2])); sortie(entier(l[7])); sortie(entier(l[19])); sortie(entier(l[0]));
    sortie(l[7] == variable);
}
"""
ecr = [(r.randrange(50), r.getrandbits(5)) for _ in range(300)]
obtenu = vtx.executer(src, [len(ecr)] + [v for p in ecr for v in p], max_pas=10_000_000)[0].sortie
etat = [0] * 64
for i, v in ecr:
    etat[i] = v & 3
attendu = etat[:50] + [sum(etat[w * 16 + q] << (2 * q) for q in range(16)) for w in range(4)] + [2, 3, 1, 0, 1]
print(f"2. Tableaux de quits (300 écritures au hasard, relecture case par case et mot par mot) et de logiques : "
      f"{obtenu == attendu}")
assert obtenu == attendu, (obtenu, attendu)
for nom, mauvais in [("indice qui appelle une fonction", "tableau q[8] de quits @1[0]; fonction f() { retour 1; } "
                      "fonction principal() { sortie(q[f()]); }"),
                     ("entier rangé dans un tableau de logique", "tableau l[8] de logique @1[0]; "
                      "fonction principal() { l[0] = 2; }"),
                     ("tableau de quits cumulé", "tableau q[32] de quits @1[0]; fonction principal() { "
                      "pour i dans 0..8 en segments cumulant q { q[i] = q[i] + 1; } }")]:
    try:
        vtx.compiler(mauvais)
        raise SystemExit(f"   ÉCHEC accepté : {nom}")
    except vtx.VtxError:
        pass
print("   erreurs refusées : 3/3")

# --- 3. génome
N = 16384
motif = [tirage(k, 99) & 3 for k in range(16)]
g = []
for i in range(N):
    c = tirage(i, 1) & 3
    p = i % 997
    if p < 16 and i + 16 - p <= N:
        c = motif[p]
        if p < (i // 997) & 3:
            c = (c + 1) & 3
    g.append(c)
nb, somme = 0, 0
for p in range(N - 15):
    if sum(g[p + k] == motif[k] for k in range(16)) >= 14:
        nb += 1
        somme = (somme * 31 + p) & M32
src = open(os.path.join(ici, "motif.vtx"), encoding="utf-8").read()
pas = {}
for mode in range(5):
    cpu = vtx.executer(src, [mode], max_pas=100_000_000, dossier=ici)[0]
    pas[mode] = cpu.pas
    if mode:
        assert cpu.sortie == [nb, somme], (mode, cpu.sortie, nb, somme)
c = {m: pas[m] - pas[0] for m in (1, 2, 3, 4)}
print(f"3. Génome de {N:,} bases, motif de 16 bases, au plus 2 différences : {nb} positions trouvées, identiques à la "
      f"référence dans les quatre modes")
print(f"   instructions : une base par mot {c[1]:,} ; tableau de quits lu base par base {c[2]:,} "
      f"({c[1] / c[2]:.2f}) ; 16 bases d'un coup sans instruction nouvelle {c[3]:,} ({c[1] / c[3]:.2f}) ; "
      f"avec QEGAL et COMPTE {c[4]:,} ({c[1] / c[4]:.2f})")
print(f"   mémoire du génome : {N:,} mots en une base par mot, {N // 16:,} mots en quits")
