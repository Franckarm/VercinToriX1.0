#!/usr/bin/env python3
"""Partition automatique des tâches : vérifie qu'elle ne change jamais le résultat et qu'elle repère les conflits.
 1. Démonstration : mesures attendues ; sorties et mémoire identiques sans partition, avec partition, et avec l'ordre
    mélangé au hasard dans chaque mesure (5 tirages).
 2. Paires de tâches dirigées : chaque sorte de conflit sépare les tâches, chaque absence de conflit les réunit.
 3. Programmes aléatoires (tableaux, adresses calculées, étage variable, sorties, appels imbriqués, boucles) :
    mêmes sorties et même mémoire dans tous les ordres permis par la partition.
 4. Mesure du temps sur la démonstration et analyse du jeu.
 5. Boucles en segments : cas indépendants et dépendants, programmes aléatoires, gain de la démonstration en segments.
 6. Tableaux cumulés (« en segments cumulant T ») : erreurs refusées, programmes aléatoires (histogrammes, sommes,
    structures, plusieurs tableaux), noms gaulois des segments, gain de la démonstration avec l'histogramme cumulé."""
import importlib.util
import os
import random

RAPIDE = os.environ.get("VTX_RAPIDE") == "1"      # vérification rapide : moins de tirages, pas de grands volumes
ici = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("vtx", os.path.join(ici, "..", "vtx.py"))
vtx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vtx)


def etat(src, dossier=None, **kw):
    """Sorties, mémoire non nulle (hors zone de travail des copies cumulées), nombre d'instructions."""
    cpu, _, mots = vtx.executer(src, (), max_pas=60_000_000, dossier=dossier, **kw)
    return cpu.sortie, {k: v for k, v in cpu.mem.items() if k[0] >= 1 and v and not (
        k[0] == 3 and vtx.COPIES_DEBUT <= k[1] < vtx.COPIES_FIN)}, cpu.pas


def mesures(src, dossier=None):
    vtx.compiler(src, dossier=dossier)
    return [[[nom for _t, _n, nom in m] for m in a["mesures"]] for a in vtx.DERNIERE_PARTITION["accords"]]


# --- 1. démonstration
demo = open(os.path.join(ici, "orchestre.vtx"), encoding="utf-8").read()
m = mesures(demo, ici)
print("1. Démonstration : partition", m)
assert m == [[["preparer_image", "preparer_memoire"], ["histogramme", "flou", "recherche"], ["contraste"]]], m
ref = etat(demo, ici, partition=False)
var = [etat(demo, ici)] + [etat(demo, ici, melange=g) for g in range(5)]
print(f"   sorties et mémoire identiques à l'ordre écrit : {sum(v[:2] == ref[:2] for v in var)}/{len(var)} "
      f"(avec partition, puis 5 ordres mélangés) ; instructions identiques : {sum(v[2] == ref[2] for v in var)}/{len(var)}")

# --- 2. paires dirigées
ENTETE = """
structure P { x; y; }
tableau a[16] @2[0];
tableau b[16] @2[100];
tableau c[16] @3[0];
tableau s[4] de P @1[500];
"""
CAS = [
    ("écriture et écriture du même tableau", "a[1] = 5;", "a[2] = 6;", False),
    ("écriture puis lecture du même tableau", "a[1] = 5;", "@2[900] = a[3];", False),
    ("lecture et lecture du même tableau", "@2[901] = a[1];", "@2[902] = a[2];", True),
    ("deux tableaux différents", "a[1] = 5;", "b[1] = 6;", True),
    ("même étage, cases constantes différentes", "@3[700] = 1;", "@3[701] = 2;", True),
    ("même case constante", "@3[700] = 1;", "@3[700] = 2;", False),
    ("adresse calculée dans le même étage", "soit k = 7; @2[k * 3] = 1;", "b[2] = 3;", False),
    ("adresse calculée dans un autre étage", "soit k = 7; @2[k * 3] = 1;", "c[2] = 3;", True),
    ("étage variable", "soit e = 1; @(e)[5] = 1;", "c[2] = 3;", False),
    ("deux sorties", "sortie(1);", "sortie(2);", False),
    ("champ de structure et autre tableau", "s[1].y = 4;", "a[1] = 2;", True),
    ("champ de structure et lecture du même tableau", "s[1].y = 4;", "@2[903] = s[0].x;", False),
    ("conflit à travers un appel imbriqué", "aide();", "a[4] = 1;", False),
    ("gemv et étage 2", "gemv(1, 1, 0, 100, 200);", "b[3] = 1;", False),
    ("gemv et étage 3", "gemv(1, 1, 0, 100, 200);", "c[3] = 1;", True),
]
bons = 0
for nom, ca, cb, ensemble in CAS:
    src = ENTETE + "fonction aide() { a[0] = 9; }\n" + f"fonction ta() {{ {ca} }}\nfonction tb() {{ {cb} }}\n" + "fonction principal() { ta(); tb(); }\n"
    m = mesures(src)
    trouve = m == [[["ta", "tb"]]]
    bon = trouve == ensemble
    bons += bon
    if not bon:
        print(f"   ÉCHEC {nom} : {m}")
print(f"\n2. Paires dirigées : {bons}/{len(CAS)} bien placées (même mesure si et seulement si aucun conflit)")


# --- 3. programmes aléatoires
def programme(r):
    tabs = [("t0", 1, 0), ("t1", 1, 200), ("t2", 2, 0), ("t3", 2, 300), ("t4", 3, 0), ("t5", 3, 500)]
    lignes = [f"tableau {n}[16] @{e}[{b}];" for n, e, b in tabs]
    nf = r.randint(3, 7)
    for i in range(nf):
        corps = [f"    soit v = p * {r.randint(1, 9)} + {r.randint(0, 9)};"]
        for _ in range(r.randint(1, 4)):
            k = r.random()
            src_t = r.choice(tabs)[0]
            lecture = f"{src_t}[(v + {r.randint(0, 15)}) & 15]"
            if k < 0.45:
                corps.append(f"    {r.choice(tabs)[0]}[(v + {r.randint(0, 15)}) & 15] = {lecture} + v;")
            elif k < 0.6:
                corps.append(f"    v = v + {lecture};")
            elif k < 0.7:
                e = r.randint(1, 3)
                corps.append(f"    @{e}[{r.choice([900, 901, 902, 0, 205, 310])}] = v + @{r.randint(1, 3)}[{r.choice([900, 0, 300])}];")
            elif k < 0.78:
                corps.append(f"    @{r.randint(1, 3)}[(v * 7) & 1023] = v;")
            elif k < 0.83:
                corps.append(f"    @(1 + v % 3)[(v * 3) & 63] = v;")
            elif k < 0.9:
                corps.append(f"    sortie({lecture});")
            elif i > 0:
                corps.append(f"    f{r.randrange(i)}(v & 7);")
        corps.append(f"    {r.choice(tabs)[0]}[p & 15] = v;")
        lignes.append(f"fonction f{i}(p) {{\n" + "\n".join(corps) + "\n}")
    run = "\n".join(f"        f{r.randrange(nf)}({r.randint(0, 9)} + j);" for _ in range(r.randint(3, 7)))
    lignes.append("fonction principal() {\n    pour j dans 0..3 {\n" + run + "\n    }\n" +
                  "    pour e dans 1..4 {\n        soit somme = 0;\n        pour q dans 0..1100 {\n            somme = somme * 31 + @(e)[q];\n        }\n        sortie(somme);\n    }\n}")
    return "\n".join(lignes)


def programme_libre(r):
    """Tâches plus indépendantes : chaque fonction écrit surtout son propre tableau et lit parfois ceux des autres."""
    nf = r.randint(4, 8)
    lignes = [f"tableau t{i}[16] @{1 + i % 3}[{(i // 3) * 64}];" for i in range(nf)]
    for i in range(nf):
        corps = [f"    soit v = p + {r.randint(1, 9)};"]
        for _ in range(r.randint(1, 3)):
            k = r.random()
            if k < 0.5:
                corps.append(f"    t{i}[(v + {r.randint(0, 15)}) & 15] = v * {r.randint(1, 5)};")
            elif k < 0.85:
                corps.append(f"    v = v + t{r.randrange(nf)}[(v + {r.randint(0, 15)}) & 15];")
                corps.append(f"    t{i}[v & 15] = v;")
            elif k < 0.93:
                corps.append(f"    t{r.randrange(nf)}[{r.randint(0, 15)}] = v;")
            else:
                corps.append(f"    @{1 + i % 3}[(v * 5) & 255] = v;")
        lignes.append(f"fonction f{i}(p) {{\n" + "\n".join(corps) + "\n}")
    run = "\n".join(f"        f{r.randrange(nf)}({r.randint(0, 9)} + j);" for _ in range(r.randint(4, 9)))
    lignes.append("fonction principal() {\n    pour j dans 0..3 {\n" + run + "\n    }\n" +
                  "    pour e dans 1..4 {\n        soit somme = 0;\n        pour q dans 0..400 {\n            somme = somme * 31 + @(e)[q];\n        }\n        sortie(somme);\n    }\n}")
    return "\n".join(lignes)


r = random.Random(2026)
N = 30 if RAPIDE else 150
ok = reordonnes = taches = mesures_tot = 0
for n in range(N):
    src = programme(r)
    ref = etat(src, partition=False)
    m = mesures(src)
    taches += sum(len(x) for a in m for x in a)
    mesures_tot += sum(len(a) for a in m)
    vtx.compiler(src)
    ordre_ecrit = [nom for a in vtx.DERNIERE_PARTITION["accords"] for x in a["mesures"] for _t, _n, nom in x]
    variantes = [etat(src)] + [etat(src, melange=g) for g in range(3)]
    bon = all(v[:2] == ref[:2] for v in variantes)
    ok += bon
    if not bon:
        print("   ÉCHEC sur le programme", n)
        print(src)
        break
print(f"\n3. {N} programmes aléatoires : mêmes sorties et même mémoire dans les 4 ordres permis par la partition "
      f"{ok}/{N} ; {taches} tâches réparties en {mesures_tot} mesures")
ok2 = taches2 = mesures2 = multi = changes = 0
for n in range(N):
    src = programme_libre(r)
    ref = etat(src, partition=False)
    m = mesures(src)
    taches2 += sum(len(x) for a in m for x in a)
    mesures2 += sum(len(a) for a in m)
    multi += sum(1 for a in m for x in a if len(x) > 1)
    ecrit = [nom for a in m for x in a for nom in x]
    vtx.compiler(src, partition=False)
    variantes = [etat(src)] + [etat(src, melange=g) for g in range(4)]
    bon = all(v[:2] == ref[:2] for v in variantes)
    ok2 += bon
    if not bon:
        print("   ÉCHEC sur le programme libre", n)
        print(src)
        break
print(f"   {N} programmes à tâches souvent indépendantes : identiques dans les 5 ordres {ok2}/{N} ; {taches2} tâches en "
      f"{mesures2} mesures, dont {multi} mesures à plusieurs tâches")

# --- 4. temps
b = vtx.jouer(demo, (), ici)
print(f"\n4. Démonstration jouée : {b['seq']:,} instructions de tâches en séquence ; {b['par'][None]:,} si chaque mesure "
      f"joue ses tâches ensemble (gain {b['seq'] / b['par'][None]:.2f}) ; durée par tâche : "
      + ", ".join(f"{k} {v:,}" for k, v in b["duree_taches"].items()))
jeu = os.path.join(ici, "..", "jeu3")
vtx.compiler(open(os.path.join(jeu, "jeu3.vtx"), encoding="utf-8").read(), dossier=jeu)
acc = vtx.DERNIERE_PARTITION["accords"]
print(f"   jeu : {len(acc)} accord(s) trouvé(s) : " + "; ".join(
    f"{a['fonction']} : " + " / ".join(" + ".join(nom for _t, _n, nom in x) for x in a["mesures"]) for a in acc))

# --- 5. segments
print("\n5. Boucles en segments")
SEG = [
    ("écriture à l'indice", "t[i] = u[i] * 2;", True),
    ("écriture à l'indice décalé", "t[i + 3] = i;", True),
    ("lecture et écriture du même tableau (pochoir)", "t[i] = t[i + 1] + 1;", False),
    ("deux décalages sur le même tableau", "t[i] = 1; t[i + 1] = 2;", False),
    ("écriture à une case fixe", "t[0] = i;", False),
    ("adresse calculée", "@2[i * 2] = i;", False),
    ("sortie", "sortie(i);", False),
    ("appel qui écrit le même tableau", "aide(i);", False),
    ("appel qui écrit un autre tableau à un indice passé en paramètre (pris en entier, par prudence)", "autre(i);", False),
    ("appel qui ne fait que lire", "t[i] = lecture(i);", True),
    ("champ de structure à l'indice", "s[i].y = i;", False),
]
bons = 0
for nom, corps, libre in SEG:
    src = ("structure P { x; y; }\ntableau t[80] @2[0];\ntableau u[80] @2[100];\ntableau v[80] @3[0];\ntableau s[80] de P @1[0];\n"
           "fonction aide(k) { t[k] = 5; }\nfonction autre(k) { v[k] = 5; }\nfonction lecture(k) { retour u[k] + v[k]; }\n"
           f"fonction principal() {{\n    pour i dans 0..64 en segments {{ {corps} }}\n}}\n")
    vtx.compiler(src)
    acc = [a for a in vtx.DERNIERE_PARTITION["accords"] if a.get("segments")]
    trouve = len(acc[0]["mesures"]) == 1
    bon = trouve == libre
    bons += bon
    if not bon:
        print(f"   ÉCHEC {nom} : {len(acc[0]['mesures'])} mesure(s)")
print(f"   cas dirigés : {bons}/{len(SEG)} (une seule mesure si et seulement si les segments sont indépendants)")


def prog_segments(r):
    tabs = [("a", 1, 0), ("b", 1, 300), ("c", 2, 0), ("d", 3, 0)]
    lignes = [f"tableau {n}[300] @{e}[{base}];" for n, e, base in tabs]
    corps = []
    for nx in range(r.randint(1, 3)):
        k = r.random()
        dst, src_ = r.choice(tabs)[0], r.choice(tabs)[0]
        off = r.choice([0, 0, 0, 1, 2])
        if k < 0.6:
            corps.append(f"        {dst}[i + {off}] = {src_}[i + {r.randint(0, 3)}] * {r.randint(1, 5)} + i;")
        elif k < 0.8:
            corps.append(f"        soit x{nx} = {src_}[(i * 7) % 250] + i;\n        {dst}[i] = x{nx};")
        elif k < 0.9:
            corps.append(f"        {dst}[{r.randint(0, 9)}] = i;")
        else:
            corps.append(f"        @{r.randint(1, 3)}[(i * 3) & 255] = i;")
    n = r.choice(["", " 2", " 8", " 16"])
    debut, fin = r.randint(0, 5), r.randint(40, 200)
    lignes.append("fonction principal() {\n    pour q dans 0..300 {\n" + "".join(f"        {t[0]}[q] = q * {r.randint(1, 9)} + {r.randint(0, 50)};\n" for t in tabs)
                  + f"    }}\n    pour i dans {debut}..{fin} en{n} segments {{\n" + "\n".join(corps) + "\n    }\n"
                  + "    pour e dans 1..4 {\n        soit somme = 0;\n        pour q dans 0..700 {\n            somme = somme * 31 + @(e)[q];\n        }\n        sortie(somme);\n    }\n}")
    return "\n".join(lignes)


r5 = random.Random(77)
ok5 = libres = 0
N5 = 30 if RAPIDE else 120
for n in range(N5):
    src = prog_segments(r5)
    ref = etat(src, partition=False)
    vtx.compiler(src)
    acc = [a for a in vtx.DERNIERE_PARTITION["accords"] if a.get("segments")]
    libres += len(acc[0]["mesures"]) == 1
    variantes = [etat(src)] + [etat(src, melange=g) for g in range(4)]
    bon = all(v[:2] == ref[:2] for v in variantes)
    ok5 += bon
    if not bon:
        print("   ÉCHEC programme", n)
        print(src)
        break
print(f"   {N5} programmes aléatoires en segments : identiques à la boucle ordinaire dans les 5 ordres {ok5}/{N5} ; "
      f"{libres} boucles reconnues indépendantes, {120 - libres} jouées segment après segment")
seg = open(os.path.join(ici, "orchestre_segments.vtx"), encoding="utf-8").read()
ref = ref_demo = etat(demo, ici, partition=False)
avec = etat(seg, ici)
b2 = vtx.jouer(seg, (), ici)
print(f"   démonstration en segments : mêmes sorties et même mémoire que sans segments : {avec[:2] == ref[:2]} ; "
      f"{b2['seq']:,} instructions de tâches, {b2['par'][None]:,} jouées ensemble (gain {b2['seq'] / b2['par'][None]:.2f} contre "
      f"{b['seq'] / b['par'][None]:.2f} sans segments)")

# --- 6. tableaux cumulés
print("\n6. Tableaux cumulés")
TETE = ("structure P { n; s; }\ntableau h[16] @2[0];\ntableau g[16] @2[100];\ntableau ps[8] de P @1[500];\n"
        "tableau img[64] @1[0];\nfonction touche(k) { h[k] = 1; }\n")
ERR = [
    ("écriture qui n'est pas une addition", "h[i % 16] = i;"),
    ("addition à une autre case", "h[i % 16] = h[(i + 1) % 16] + 1;"),
    ("valeur moins le tableau", "h[i % 16] = 5 - h[i % 16];"),
    ("lecture du tableau cumulé dans la valeur ajoutée", "h[i % 16] = h[i % 16] + h[0];"),
    ("lecture ailleurs", "soit x = h[3];"),
    ("lecture dans une condition", "si h[2] > 1 { g[i % 16] = 1; }"),
    ("fonction appelée qui touche le tableau", "touche(i % 16);"),
    ("adresse calculée sur le tableau", "@2[i % 16] = 1;"),
]
refus = 0
for nom, corps in ERR:
    src = TETE + f"fonction principal() {{\n    pour i dans 0..64 en segments cumulant h {{ {corps} }}\n}}\n"
    try:
        vtx.compiler(src)
        print(f"   ÉCHEC accepté : {nom}")
    except vtx.VtxError:
        refus += 1
try:
    vtx.compiler("tableau h[16] @3[14680060];\nfonction principal() {\n    pour i dans 0..64 en segments cumulant h { h[i % 16] = h[i % 16] + 1; }\n}\n")
    print("   ÉCHEC accepté : tableau dans la zone des copies")
except vtx.VtxError:
    refus += 1
print(f"   erreurs refusées : {refus}/{len(ERR) + 1}")

src = TETE + ("fonction principal() {\n    pour i dans 0..64 en 6 segments cumulant h, ps {\n"
              "        h[i % 16] = h[i % 16] + i;\n        ps[i % 8].n = 1 + ps[i % 8].n;\n        ps[i % 8].s = ps[i % 8].s + i * i;\n"
              "        img[i] = i;\n    }\n}\n")
vtx.compiler(src)
acc = [a for a in vtx.DERNIERE_PARTITION["accords"] if a.get("segments")][0]
noms = [nom for m in acc["mesures"] for _t, _n, nom in m]
print(f"   six segments : {len(acc['mesures'])} mesure ; noms {', '.join(noms)} ; même résultat : "
      f"{etat(src, partition=False)[:2] == etat(src)[:2]}")
assert len(acc["mesures"]) == 1 and noms[0] == "principal·cintux" and noms[3] == "principal·petuarios"


def prog_cumul(r):
    lignes = ["structure P { n; s; }", "tableau a[200] @1[0];", "tableau h[32] @2[0];", "tableau k[8] @2[100];",
              "tableau ps[8] de P @3[0];", "tableau o[200] @1[300];"]
    cum = r.sample(["h", "k", "ps"], r.randint(1, 3))
    corps = []
    for nx in range(r.randint(1, 4)):
        t = r.choice(cum)
        v = r.choice(["1", "i", "a[i]", "a[i] * 3 - i", f"(a[i] >> {r.randint(0, 3)}) & 7", f"0 - {r.randint(1, 9)}"])
        if t == "h":
            e = r.choice(["a[i] & 31", "i % 32", "(a[i] * 7 + i) & 31"])
            q = r.random()
            corps.append(f"h[{e}] = h[{e}] + ({v});" if q < 0.5 else f"h[{e}] = ({v}) + h[{e}];" if q < 0.8 else f"h[{e}] = h[{e}] - ({v});")
        elif t == "k":
            corps.append(f"si a[i] > {r.randint(0, 99)} {{ k[i & 7] = k[i & 7] + ({v}); }}")
        else:
            c = r.choice(["n", "s"])
            corps.append(f"ps[a[i] & 7].{c} = ps[a[i] & 7].{c} + ({v});")
    if r.random() < 0.5:
        corps.append("o[i] = a[i] + 1;")
    if r.random() < 0.3:
        corps.append("soit z = a[i] * 2;\n        h[z & 31] = h[z & 31] + z;" if "h" in cum else "o[i] = 2;")
    n = r.choice(["", " 2", " 3", " 8", " 16"])
    debut, fin = r.randint(0, 9), r.randint(30, 200)
    lignes.append("fonction principal() {\n    pour q dans 0..200 {\n        a[q] = (q * 37 + 11) % 101;\n    }\n"
                  "    pour q dans 0..32 {\n        h[q] = q;\n    }\n"
                  f"    pour i dans {debut}..{fin} en{n} segments cumulant {', '.join(cum)} {{\n        "
                  + "\n        ".join(corps) + "\n    }\n"
                  "    pour e dans 1..4 {\n        soit somme = 0;\n        pour q dans 0..400 {\n"
                  "            somme = somme * 31 + @(e)[q];\n        }\n        sortie(somme);\n    }\n}")
    return "\n".join(lignes)


r6 = random.Random(2026)
ok6 = libres6 = 0
N6 = 30 if RAPIDE else 150
for n in range(N6):
    src = prog_cumul(r6)
    ref = etat(src, partition=False)
    vtx.compiler(src)
    acc = [a for a in vtx.DERNIERE_PARTITION["accords"] if a.get("segments")]
    libres6 += len(acc[0]["mesures"]) == 1
    variantes = [etat(src)] + [etat(src, melange=g) for g in range(4)]
    bon = all(v[:2] == ref[:2] for v in variantes)
    ok6 += bon
    if not bon:
        print("   ÉCHEC programme", n)
        print(src)
        break
print(f"   {N6} programmes aléatoires cumulants : identiques à la boucle ordinaire dans les 5 ordres {ok6}/{N6} ; "
      f"{libres6} boucles jouées en une seule mesure")
cum = open(os.path.join(ici, "orchestre_cumul.vtx"), encoding="utf-8").read()
avec = etat(cum, ici)
b3 = vtx.jouer(cum, (), ici)
print(f"   démonstration avec l'histogramme cumulé : même résultat que l'ordre écrit : {avec[:2] == ref_demo[:2]} ; "
      f"{b3['seq']:,} instructions de tâches, {b3['par'][None]:,} jouées ensemble ; gain {b['seq'] / b3['par'][None]:.2f} "
      f"par rapport au programme d'origine joué en séquence (segments seuls : {b['seq'] / b2['par'][None]:.2f})")
assert refus == len(ERR) + 1 and ok6 == N6 and avec[:2] == ref_demo[:2]

# --- 7. simulation des cylindres partagés
print("\n7. Cylindres partagés entre les niveaux (accords imbriqués)")
cyl = list(range(1, 9))
b7 = vtx.jouer(cum, (), ici, canaux=[None] + cyl)
p = b7["par"]
regles = [("un cylindre : durée = séquence", p[1] == b7["seq"]),
          ("jamais moins que séquence / cylindres", all(p[c] * c >= b7["seq"] for c in cyl)),
          ("plus de cylindres, jamais plus lent", all(p[c] >= p[c + 1] for c in cyl[:-1])),
          ("jamais moins que sans limite", all(p[c] >= p[None] for c in cyl))]
for nom, ok in regles:
    if not ok:
        print("   ÉCHEC", nom)
print(f"   règles tenues : {sum(ok for _n, ok in regles)}/{len(regles)} ; gain selon les cylindres : "
      + ", ".join(f"{c} → {b7['seq'] / p[c]:.2f}" for c in cyl))
assert all(ok for _n, ok in regles)
