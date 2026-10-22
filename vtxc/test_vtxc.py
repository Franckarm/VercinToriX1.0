#!/usr/bin/env python3
"""vtxc : le compilateur de vtx écrit en vtx.
 1. Point fixe : M0 = vtx.py(vtxc) ; M1 = M0 compilant vtxc sur la machine Rust ; M2 = M1 compilant vtxc. M0 = M1 = M2 exigé.
 2. Juge : des programmes aléatoires du noyau, compilés par vtxc et par vtx.py (sans optimisation) : mêmes mots exigés ;
    de même pour des programmes aléatoires de logique à quatre valeurs et de quits (gen_logique.py), et capteurs.vtx ;
    de même pour des programmes de tableaux de quits et de logiques (générateur de vectorise/), où vtx.py réécrit une
    partie des boucles 16 éléments à la fois : vtxc doit faire exactement la même réécriture ; et initialisation.vtx.
 2 bis. Flottants et longs : des milliers de flottants écrits en décimal (sous-normaux, bords, milieux exacts) lus au bit
    près comme Python ; avec le prélude, le test différentiel complet, les programmes typés et les programmes du paquet ;
    importer (chemins relatifs, fichier importé deux fois) et donnees.
 2 ter. Optimisations et partition : avec les optimisations de vtx.py (élagage, sauts directs, feuilles sans pile), puis
    avec la partition des tâches en accords, code et table des accords identiques à « vtx.py exporter ».
 3. Erreurs : vtxc refuse les programmes faux, avec la ligne, sans écrire de code.
 4. vtx.exe : le compilateur embarqué (vtx-rs/vtxc.mots) est bien vtxc.vtx compilé, et « vtx PROG.vtx » compile et exécute.
Il faut cargo (la machine Rust). Utilisation : python3 vtxc/test_vtxc.py [N]"""
import os, random, re, shutil, struct, subprocess, sys, tempfile
ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, racine)
import vtx  # noqa: E402

cargo = shutil.which("cargo")
if not cargo:
    print("cargo absent : vtxc n'est pas essayé (il tourne sur la machine Rust)")
    sys.exit(0)
rs = os.path.join(racine, "vtx-rs")
cible = os.environ.get("CARGO_TARGET_DIR") or os.path.join(rs, "target")
subprocess.run([cargo, "build", "--release", "-q"], cwd=rs, check=True)
SPU = os.path.join(cible, "release", "vtx-spu" + (".exe" if os.name == "nt" else ""))
TMP = tempfile.mkdtemp(prefix="vtxc-")


def mots_py(src, prelude=False, dossier=None, optim=False):
    return vtx.assembler(vtx.compiler(src, prelude=prelude, optim=optim, dossier=dossier, partition=False))


PROGS = {}


def prog(mots, nom):
    p = os.path.join(TMP, nom)
    with open(p, "w") as f:
        f.write(",".join(map(str, mots)) + ";\n")
    PROGS[p] = mots
    return p


def vtxc(p, src, base=None, prelude=False, optim=False, partition=False):
    """Compile src avec le compilateur p ; ses entrées : le dossier des fichiers importés, 0, puis trois drapeaux :
    prélude, optimisations, partition. Rend les mots (et la table des accords, avec la partition)."""
    if base is not None or prelude or optim or partition:
        e = [ord(ch) for ch in (base or "")] + [0] + [1 if x else 0 for x in (prelude, optim, partition)]
        q = os.path.join(TMP, "entrees.prog")
        with open(q, "w") as f:
            f.write(",".join(map(str, PROGS[p])) + ";" + ",".join(map(str, e)) + "\n")
        p = q
    d = os.path.join(TMP, "travail")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "source.vtx"), "w", encoding="utf-8") as f:
        f.write(src)
    cm = os.path.join(d, "code.mots")
    if os.path.exists(cm):
        os.remove(cm)
    r = subprocess.run([SPU, "lancer", p, "50000000000", "1"], cwd=d, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if not os.path.exists(cm):
        return None, r.stdout + r.stderr
    t = open(cm).read().strip()
    lire = lambda u: [int(x) for x in u.split(",")] if u else []
    if ";" in t:
        a, b = t.split(";")
        return (lire(a), lire(b)), r.stdout
    return lire(t), r.stdout


src_c = open(os.path.join(ici, "vtxc.vtx"), encoding="utf-8").read()
m0 = mots_py(src_c)
p0 = prog(m0, "m0.prog")
m1, o1 = vtxc(p0, src_c)
m2, o2 = vtxc(prog(m1 or [], "m1.prog"), src_c)
print(f"1. Point fixe : M0 {len(m0):,} mots ; M0 = M1 : {m0 == m1} ; M1 = M2 : {m1 == m2} ; "
      f"{o1.splitlines()[0] if o1 else ''}")
ok1 = m0 == m1 == m2

# 2. Juge : générateur du test différentiel, réduit au noyau (sans <<q, >>q, .q() ni fonctions du prélude)
g = {"__name__": "diff"}
d_src = open(os.path.join(racine, "tests", "test_differentiel.py"), encoding="utf-8").read().split("class Ret(Exception)")[0]
d_src = "\n".join(l for l in d_src.splitlines() if "spec" not in l and not l.startswith("vtx ="))
exec(d_src, g)
BIN = [b for b in g["BIN"] if b not in ("<<q", ">>q")]


class GenNoyau(g["Gen"]):
    def expr(self, vs, d):
        r = self.r
        if d == 0 or r.random() < .25:
            return r.choice(vs) if vs and r.random() < .6 else r.choice(g["LITS"])
        k, e = r.random(), (lambda: self.expr(vs, d - 1))
        if k < .45:
            return f"({e()} {r.choice(BIN)} {e()})"
        if k < .55:
            return f"({r.choice(['~', '!', '-'])}{e()})"
        if k < .62:
            return f"({e()}).{r.choice(['r', 'v', 'b', 'a'])}"
        if k < .74:
            return f"@{r.randint(1, 3)}[({e()}) & 255]" if r.random() < .6 else f"@(1 + (({e()}) % 3))[({e()}) & 255]"
        if k < .88 and self.funcs:
            nom, n = r.choice(self.funcs)
            return f"{nom}({', '.join(e() for _ in range(n))})"
        return f"'{r.choice('aZ0é')}'" if r.random() < .5 else f'longueur("t{r.randint(0, 3)}")'


PRE = "fonction longueur(t) {\n    retour @(t >> 24)[t & 16777215];\n}\n"
N = int(sys.argv[1]) if len(sys.argv) > 1 else (100 if os.environ.get("VTX_RAPIDE") == "1" else 1000)
ok = 0
for n in range(N):
    s = PRE + GenNoyau(random.Random(7000 + n)).programme()
    if vtxc(p0, s)[0] == mots_py(s):
        ok += 1
print(f"2. {N} programmes aléatoires du noyau : code de vtxc identique à celui de vtx.py, mot pour mot : {ok}/{N}")
sys.path.insert(0, ici)
from gen_logique import GenLogique  # noqa: E402
okl = 0
for n in range(N):
    s = GenLogique(random.Random(9000 + n)).programme()
    if vtxc(p0, s)[0] == mots_py(s):
        okl += 1
cap = open(os.path.join(racine, "logique", "capteurs.vtx"), encoding="utf-8").read()
okc = vtxc(p0, cap)[0] == mots_py(cap)
print(f"   {N} programmes aléatoires de logique à quatre valeurs et de quits (logique, selon, et4, ou4, non4, anti, "
      f"fusion, consensus, <<q, .q(), min4, qegal…) : identiques {okl}/{N} ; logique/capteurs.vtx identique : {okc}")
ok = ok if okl == N and okc else -1
gv = {"__name__": "v", "__file__": os.path.join(racine, "vectorise", "x.py")}
v_src = open(os.path.join(racine, "vectorise", "test_vectorise.py"), encoding="utf-8").read().split("r = random.Random(2027)")[0]
exec("\n".join(l for l in v_src.splitlines() if "spec" not in l and not l.startswith("vtx =")), gv)
rv, okv, reecrits = random.Random(4242), 0, 0
for n in range(N):
    s = gv["programme"](rv)
    att = mots_py(s)
    vtx.VECTORISER = False
    reecrits += mots_py(s) != att
    vtx.VECTORISER = True
    okv += vtxc(p0, s)[0] == att
ini = open(os.path.join(racine, "logique", "initialisation.vtx"), encoding="utf-8").read()
oki = vtxc(p0, ini)[0] == mots_py(ini)
print(f"   {N} programmes de tableaux de quits et de logiques : identiques {okv}/{N} (dont {reecrits} où vtx.py réécrit "
      f"des boucles 16 éléments à la fois) ; logique/initialisation.vtx identique : {oki}")
ok = ok if okv == N and oki else -1

# 2 bis. flottants, longs, prélude, importer, donnees
rf = random.Random(31415)


def litteral():
    k = rf.random()
    if k < .2:
        return f"{rf.randint(0, 99999)}.{rf.randint(0, 99999)}"
    if k < .4:
        return f"{rf.randint(1, 9)}.{rf.randint(0, 10 ** rf.randint(1, 20))}e{rf.choice(['', '-', '+'])}{rf.randint(0, 50)}"
    if k < .55:
        w = rf.choice([rf.randint(1, 0x7FFFFF), rf.randint(0x7F000000, 0x7F7FFFFF), rf.randint(0x00800000, 0x3F800000)])
        x = repr(float(struct.unpack("<f", struct.pack("<I", w))[0]))
        return x if ("e" in x or "." in x) else x + ".0"
    if k < .7:
        w = rf.randint(0x3F800000, 0x4B000000)
        a, b = (struct.unpack("<f", struct.pack("<I", v))[0] for v in (w, w + 1))
        return repr((a + b) / 2)
    if k < .85:
        return f"{rf.randint(1, 9)}e{rf.randint(-46, 39)}"
    return "0." + "0" * rf.randint(0, 50) + str(rf.randint(1, 10 ** rf.randint(1, 30)))


NF = max(1, N // 100)
okf = 0
for _ in range(NF):
    lits = []
    while len(lits) < 300:
        t = litteral()
        try:
            vtx.lexer(f"x = {t};")
            lits.append(t)
        except vtx.VtxError:
            pass
    s = "fonction principal() {\n" + "".join(f"    sortie(bits({t}));\n" for t in lits) + "}\n"
    okf += vtxc(p0, s)[0] == mots_py(s)
tt = open(os.path.join(racine, "tests", "test_types.py"), encoding="utf-8").read()
src_f = tt.split('SRC_F = """')[1].split('"""')[0]
oktf = vtxc(p0, src_f)[0] == mots_py(src_f)
typés = [re.sub(r'"\s*"', "", m) for m in re.findall(r'\("[^"]+", "(fonction[^"]*(?:"\s*"[^"]*)*)"', tt)]
acceptes = []
for s in typés:
    try:
        acceptes.append((s, mots_py(s, True)))
    except vtx.VtxError:
        pass                                         # les programmes faux du test des types
typés = acceptes
okt = sum(vtxc(p0, s, prelude=True)[0] == att for s, att in typés)
gd = {"__name__": "d"}
d_src2 = open(os.path.join(racine, "tests", "test_differentiel.py"), encoding="utf-8").read().split("class Ret(Exception)")[0]
exec("\n".join(l for l in d_src2.splitlines() if "spec" not in l and not l.startswith("vtx =")), gd)
okd = 0
for n in range(N):
    s = gd["Gen"](random.Random(1000 + n)).programme()
    okd += vtxc(p0, s, prelude=True)[0] == mots_py(s, True)
print(f"   {NF * 300} flottants écrits en décimal, lus au bit près comme Python : programmes identiques {okf}/{NF} ; "
      f"opérations flottantes de test_types : {oktf}")
print(f"   avec le prélude : test différentiel complet {okd}/{N} ; programmes typés (flottants, longs) {okt}/{len(typés)}")
# programmes du paquet (sauf ceux qui utilisent des parties pas encore portées)
okp, totp = 0, 0
for dossier, _, fichiers in sorted(os.walk(racine)):
    for nom in sorted(fichiers):
        if not nom.endswith(".vtx") or nom == "vtxc.vtx":
            continue
        chemin = os.path.join(dossier, nom)
        s = open(chemin, encoding="utf-8").read()
        try:
            att = mots_py(s, True, dossier)
        except vtx.VtxError:
            continue                                 # morceau importé par un autre (sans principal)
        totp += 1
        okp += vtxc(p0, s, base=dossier, prelude=True)[0] == att
print(f"   programmes du paquet (feu de camp, ombre, jeu, orchestres en segments…), avec le prélude et leurs fichiers "
      f"importés : identiques {okp}/{totp}")
# les tests et les erreurs de vtx.py, et les programmes en segments (cumulant, hypothèses) du test de partition
okT = sum(vtxc(p0, s, prelude=True)[0] == mots_py(s, True) for _, s, _, _ in vtx.TESTS)
okE = 0
for _, s in vtx.ERREURS:
    r_ = vtxc(p0, s, prelude=True)
    okE += r_[0] is None and "erreur" in r_[1]
tp = open(os.path.join(racine, "partition", "test_partition.py"), encoding="utf-8").read()
gp = {"__name__": "p", "vtx": vtx, "__file__": os.path.join(racine, "partition", "x.py")}
code = "\n".join(l for l in tp.split("def etat(")[0].splitlines() if "spec" not in l and not l.startswith("vtx =")
                 and not l.startswith("import importlib"))
for nom in ("programme", "prog_segments", "prog_cumul"):
    code += "\n" + re.search(r"^def " + nom + r"\(r\):.*?(?=^\S)", tp, re.S | re.M).group(0)
exec(code, gp)
rs_, oks, tots = random.Random(5), 0, 0
for nom in ("programme", "prog_segments", "prog_cumul"):
    for _ in range(max(10, N // 10)):
        s = gp[nom](rs_)
        s = s[0] if isinstance(s, tuple) else s
        tots += 1
        oks += vtxc(p0, s, prelude=True)[0] == mots_py(s, True)
print(f"   tests de vtx.py : {okT}/{len(vtx.TESTS)} identiques ; ses {len(vtx.ERREURS)} erreurs refusées : {okE} ; "
      f"programmes aléatoires en segments (cumulant, accords) : identiques {oks}/{tots}")
# importer et donnees
dimp = os.path.join(TMP, "imp")
os.makedirs(os.path.join(dimp, "lib"), exist_ok=True)
fichiers = {"lib/aide.vtx": "constante TROIS = 3;\nfonction triple(x) {\n    retour x * TROIS;\n}\n",
            "lib/outil.vtx": 'importer "aide.vtx";\nimporter "../lib/./aide.vtx";\nfonction double(x) {\n    retour x * 2;\n}\n',
            "main.vtx": 'importer "lib/outil.vtx";\nimporter "lib/outil.vtx";\ndonnees @2[10] = { 5, 6, 7, -1, ~0, 1 << 4, vrai, 0q33 <<q 1, -2.5 };\n'
                        'donnees @2[100] = { };\nfonction principal() {\n    sortie(double(21) + triple(2));\n'
                        '    sortie(@2[10] + @2[11] + @2[12]);\n}\n',
            "faute.vtx": 'importer "lib/faux.vtx";\nfonction principal() { }\n',
            "lib/faux.vtx": "fonction g() {\n    retour 1\n}\n"}
for k, v in fichiers.items():
    with open(os.path.join(dimp, k), "w", encoding="utf-8") as f:
        f.write(v)
main = fichiers["main.vtx"]
oki2 = vtxc(p0, main, base=dimp, prelude=True)[0] == mots_py(main, True, dimp)
r_faute = vtxc(p0, fichiers["faute.vtx"], base=dimp)
okf2 = r_faute[0] is None and "lib/faux.vtx, ligne 3" in r_faute[1]
print(f"   importer (chemins relatifs, fichier importé deux fois) et donnees : identiques {oki2} ; "
      f"erreur située dans le fichier importé : {okf2}")
ok = ok if (okf == NF and oktf and okd == N and okt == len(typés) and okp == totp and oki2 and okf2
            and okT == len(vtx.TESTS) and okE == len(vtx.ERREURS) and oks == tots) else -1

# 3. Erreurs
fautes = ["fonction principal() { sortie(x); }", "fonction principal() { soit a = 1; soit a = 2; }",
          "fonction principal() { inconnue(3); }", "fonction principal() { sortie(1) }", "fonction autre() { }",
          "fonction principal() {\n  sortie(1.5 + 2L);\n}",
          "fonction principal() { soit p: logique = vrai; si p { sortie(1); } }",
          "fonction principal() { soit p: logique = vrai; sortie(~p); }",
          "fonction principal() { soit p: logique = vrai; sortie(p + 1); }",
          "fonction principal() { soit p: logique = vrai; sortie(p == 3); }",
          "fonction principal() { soit p: logique = vrai; selon p { vrai { } vrai { } } }",
          "fonction principal() { selon inconnu { bleu { } } }",
          "tableau t[10] de logique @1[0];\nfonction principal() { t[1] = 3; }",
          "tableau t[10] de quits @1[0];\nfonction f(x) { retour x; }\nfonction principal() { sortie(t[f(1)]); }",
          "tableau t[10] @1[0];\nfonction principal() { sortie(t[12]); }",
          "fonction principal() { sortie(entier(1.5 % 2.0)); }",
          "fonction principal() { soit a = 1; a = 2.5; }",
          "fonction principal() { soit a = 1.5 + 2L; }",
          "fonction principal() { @2[0] = 5L; }",
          "fonction principal() { soit a = 1.5 << 2; }",
          "fonction principal() { sortie(arrondi(3)); }",
          "fonction principal() { sortie(1e39); }",
          "fonction f() { }\nfonction f() { }\nfonction principal() { }",
          "fonction principal(x) { }",
          "fonction sortie(x) { }\nfonction principal() { }"]
ref = sum(1 for s in fautes if vtxc(p0, s)[0] is None and "erreur ligne" in vtxc(p0, s)[1])
print(f"3. Programmes faux refusés avec la ligne : {ref}/{len(fautes)}")

# 2 ter. optimisations, puis partition des tâches
sources = [PRE + GenNoyau(random.Random(7000 + n)).programme() for n in range(N // 4)]
sources_p = [GenLogique(random.Random(9000 + n)).programme() for n in range(N // 4)]
rv2 = random.Random(4242)
sources_p += [gv["programme"](rv2) for _ in range(N // 4)]
sources_p += [gd["Gen"](random.Random(1000 + n)).programme() for n in range(N // 4)]
sources_p += [s for _, s, _, _ in vtx.TESTS]
paquet = []
for dossier, _, fichiers in sorted(os.walk(racine)):
    for nom in sorted(fichiers):
        if nom.endswith(".vtx") and nom != "vtxc.vtx":
            paquet.append((open(os.path.join(dossier, nom), encoding="utf-8").read(), dossier))
oko = koo = 0
for s in sources:
    koo += 1
    oko += vtxc(p0, s, optim=True)[0] == mots_py(s, optim=True)
for s, d in [(x, None) for x in sources_p] + paquet:
    try:
        att = mots_py(s, True, d, optim=True)
    except vtx.VtxError:
        continue
    koo += 1
    oko += vtxc(p0, s, base=d, prelude=True, optim=True)[0] == att
for nm in ("programme", "prog_segments", "prog_cumul"):
    for _ in range(max(5, N // 20)):
        s = gp[nm](rs_)
        sources_p.append(s[0] if isinstance(s, tuple) else s)
okq = koq = 0
for s, d in [(x, None) for x in sources_p] + paquet:
    try:
        att = vtx.exporter(s, d)
    except vtx.VtxError:
        continue
    koq += 1
    g_ = vtxc(p0, s, base=d, prelude=True, optim=True, partition=True)[0]
    okq += g_ is not None and tuple(g_) == tuple(att)
print(f"2 ter. Optimisations (élagage, sauts directs, feuilles sans pile) : identiques {oko}/{koo} ; avec la partition des "
      f"tâches en accords, code et table des accords identiques à vtx.py exporter : {okq}/{koq}")
ok = ok if oko == koo and okq == koq else -1

# 4. vtx.exe
emb = [int(x) for x in open(os.path.join(rs, "vtxc.mots")).read().strip().split(",")]
VTX = os.path.join(cible, "release", "vtx" + (".exe" if os.name == "nt" else ""))
essai = ("fonction carre(x) {\n    retour x * x;\n}\nfonction principal() {\n    soit s = 0;\n"
         "    pour i dans 0..10 {\n        s = s + carre(i);\n    }\n    sortie(s);\n    sortie(entrée() + 1);\n"
         "    ecrire_car(1, 'o');\n    ecrire_car(1, 'k');\n}\n")
pe = os.path.join(TMP, "essai.vtx")
with open(pe, "w", encoding="utf-8") as f:
    f.write(essai)
r = subprocess.run([VTX, pe, "41"], capture_output=True, text=True, encoding="utf-8", errors="replace")
cpu, _, _ = vtx.executer(essai, entrees=[41], optim=False)
attendu = ",".join(map(str, cpu.sortie)) + "\nok"
m_opt = mots_py(src_c, optim=True)
# un programme à accords, sur 1 et 2 cylindres : mêmes sorties que vtx.py
orch = os.path.join(racine, "partition", "orchestre_cumul.vtx")
att_o = ",".join(map(str, vtx.executer(open(orch, encoding="utf-8").read(), dossier=os.path.dirname(orch),
                                       max_pas=500_000_000)[0].sortie))
sorties_o = [subprocess.run([VTX, orch], capture_output=True, text=True, encoding="utf-8", errors="replace",
                            env=dict(os.environ, VTX_ROTOS=k)).stdout.split("\n")[0] for k in ("1", "2")]
ok4 = emb == m_opt and r.stdout == attendu and sorties_o == [att_o, att_o]
print(f"4. vtx.exe : compilateur embarqué = vtxc.vtx compilé (optimisé) : {emb == m_opt} ; « vtx essai.vtx 41 » : "
      f"{r.stdout.split()} (attendu {attendu.split()}) : {r.stdout == attendu} ; orchestre_cumul.vtx sur 1 et 2 cylindres, "
      f"sorties de vtx.py : {sorties_o == [att_o, att_o]}")
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(0 if ok1 and ok == N and ref == len(fautes) and ok4 else 1)
