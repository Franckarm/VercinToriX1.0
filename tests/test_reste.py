#!/usr/bin/env python3
"""reste (0.61b) : le reste exact de deux flottants quaternaires (le fmod de C, le % de Rust sur les flottants), du signe
du dividende, sur Lugus et sur Dunon, aux trois largeurs. Le résultat est toujours exact (il tient dans le format) : il
est comparé à une référence en fractions exactes, au bit près. Les cas de Belnap : un inconnu donne inconnu, un variable
variable ; reste(∞, b) et reste(a, 0) donnent variable ; reste(a, ∞) rend a. Les deux compilateurs de chaque machine
donnent les mêmes mots. Les entiers : le reste signé (celui de Rust), x par zéro rend x."""
import os
import random
import subprocess
import sys
import tempfile
from fractions import Fraction

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
for p in (racine, os.path.join(racine, "spu64"), os.path.join(racine, "spu128")):
    sys.path.insert(0, p)
import vtx128  # noqa: E402
import vtx64  # noqa: E402

vtx128.COMPAT_64 = False
X = ".exe" if os.name == "nt" else ""
BIN = os.path.join(racine, "vtx-rs", "target", "release")
d = tempfile.mkdtemp()
echecs = 0

# taille, bits de mantisse, exposant maximal (l'infini), biais
FORMATS = {128: (128, 112, 16383, 8247), 64: (64, 52, 1023, 537), 32: (32, 22, 255, 138)}


def verifier(nom, ok, detail=""):
    global echecs
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok else f" : {detail}"), flush=True)
    echecs += 0 if ok else 1


def decoder(w, f):
    t, p, emax, _ = FORMATS[f]
    return w >> (t - 2), (w >> p) & emax, w & ((1 << p) - 1)


def valeur(w, f):
    _, _, _, biais = FORMATS[f]
    st, e, m = decoder(w, f)
    return Fraction(m) * Fraction(4) ** (max(e, 1) - biais)


def coder(st, r, f):
    """r ≥ 0, exactement représentable : ses bits (canoniques)."""
    t, p, emax, biais = FORMATS[f]
    q = p // 2
    if r == 0:
        return st << (t - 2)
    e = 1
    m = r / Fraction(4) ** (e - biais)
    while m >= 4 ** q:
        e += 1
        m /= 4
    assert m.denominator == 1, "non représentable"
    m = int(m)
    if m < 4 ** (q - 1):
        e = 0
    assert e < emax
    return (st << (t - 2)) | (e << p) | m


def reference(a, b, f):
    t, p, emax, _ = FORMATS[f]
    sa, ea, ma = decoder(a, f)
    sb, eb, mb = decoder(b, f)
    if sa == 3 or sb == 3:
        return 3 << (t - 2)
    if sa == 0 or sb == 0:
        return 0
    if ea == emax or (eb != emax and mb == 0):
        return 3 << (t - 2)
    if eb == emax or ma == 0:
        return a
    x, y = valeur(a, f), valeur(b, f)
    r = x - y * (x // y)
    return coder(sa, r, f)


def tirer(f, rnd):
    """Un flottant canonique du format f : des nombres ordinaires surtout, et les bords."""
    t, p, emax, _ = FORMATS[f]
    q = p // 2
    k = rnd.random()
    st = rnd.choice((1, 2))
    if k < 0.03:
        return rnd.choice((0, 3)) << (t - 2)                       # inconnu, variable
    if k < 0.06:
        return (st << (t - 2)) | (emax << p)                         # l'infini
    if k < 0.09:
        return st << (t - 2)                                         # zéro
    if k < 0.16:
        return (st << (t - 2)) | rnd.randrange(1, 4 ** (q - 1))      # sous-normal
    m = rnd.randrange(4 ** (q - 1), 4 ** q)
    if rnd.random() < 0.2:
        m = (m >> (2 * (q - 3))) << (2 * (q - 3))                    # une mantisse courte
    return (st << (t - 2)) | (rnd.randrange(1, emax) << p) | m


def paires(f, n, graine):
    rnd = random.Random(graine)
    t, p, emax, _ = FORMATS[f]
    out = []
    for i in range(n):
        a, b = tirer(f, rnd), tirer(f, rnd)
        k = rnd.random()
        sa, ea, ma = decoder(a, f)
        sb, eb, mb = decoder(b, f)
        if k < 0.4 and 1 <= ea < emax and 1 <= eb < emax:
            # des exposants proches : là où la division longue a le plus de chiffres à garder
            e2 = min(emax - 1, max(1, ea - rnd.randrange(0, 4)))
            b = (sb << (t - 2)) | (e2 << p) | mb
        elif k < 0.5 and 1 <= eb < emax and mb:
            # un multiple exact de b (le reste est zéro), s'il tient
            try:
                a = coder(rnd.choice((1, 2)), valeur(b, f) * rnd.randrange(1, 9), f)
            except AssertionError:
                pass
        out.append((a, b))
    return out


def texte128(w):
    return f"0x{w:032X}LL"


def lancer(machine, src):
    chemin = os.path.join(d, "r.vtx")
    open(chemin, "w", encoding="utf-8").write(src)
    env = dict(os.environ)
    env["VTX_SANS_CLAVIER"] = "1"
    r = subprocess.run([os.path.join(BIN, machine + X), chemin], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=d, timeout=900, env=env)
    return r.stdout + r.stderr, chemin


def memes_mots(machine, chemin):
    src = open(chemin, encoding="utf-8").read()
    if machine == "lugus":
        m, _ = vtx128.assembler(vtx128.compiler(src, dossier=d), True)
    else:
        m = vtx64.assembler(vtx64.compiler(src, dossier=d))
    sortie = os.path.join(d, "x.mots")
    subprocess.run([os.path.join(BIN, machine + X), "compiler", chemin, sortie], capture_output=True)
    ml = [int(x) for x in open(sortie).read().split(";")[0].split(",") if x.strip()]
    return m == ml


def cube(t):
    return int(t.replace("#", "").replace("_", ""), 16)


# ---------------------------------------------------------------------------------------------- Lugus, les trois largeurs
pq = paires(128, 700, 7)
lignes = []
for i, (a, b) in enumerate(pq):
    lignes.append(f"    a = comme_flottant_petuar({texte128(a)}); b = comme_flottant_petuar({texte128(b)});\n"
                  f"    afficher(texte_cube(bits(reste(a, b))));\n"
                  f"    soit a{i}: flottant_64 = flottant_64(a); soit b{i}: flottant_64 = flottant_64(b);\n"
                  f"    afficher(bits(a{i}), bits(b{i}), bits(reste(a{i}, b{i})));\n"
                  f"    soit c{i}: flottant_32 = flottant_32(a); soit e{i}: flottant_32 = flottant_32(b);\n"
                  f"    afficher(bits(c{i}), bits(e{i}), bits(reste(c{i}, e{i})));\n")
src = ("fonction principal() {\n    soit a: flottant_petuar = 0.0Q;\n    soit b: flottant_petuar = 0.0Q;\n"
       + "".join(lignes) + "}\n")
sortie, chemin = lancer("lugus", src)
ls = sortie.split("\n")
ecarts = {128: 0, 64: 0, 32: 0}
premier = ""
try:
    for i, (a, b) in enumerate(pq):
        r = cube(ls[3 * i])
        if r != reference(a, b, 128):
            ecarts[128] += 1
            premier = premier or f"Q128 {a:032x} % {b:032x} : {r:032x} au lieu de {reference(a, b, 128):032x}"
        for f, k in ((64, 1), (32, 2)):
            x, y, z = (int(v) % (1 << 64) for v in ls[3 * i + k].split())
            if z != reference(x, y, f):
                ecarts[f] += 1
                premier = premier or f"Q{f} {x:x} % {y:x} : {z:x} au lieu de {reference(x, y, f):x}"
    verifier(f"Lugus : {len(pq)} restes de 128 bits, et autant de 64 et de 32 bits, au bit près de la référence exacte",
             not any(ecarts.values()), f"{ecarts} ; {premier}")
except (ValueError, IndexError) as e:
    verifier("Lugus : les restes", False, f"{e} ; {sortie[:400]}")
verifier("Lugus : les deux compilateurs, les mêmes mots", memes_mots("lugus", chemin))

# ---------------------------------------------------------------------------------------------- Dunon, 64 et 32 bits
pd = paires(64, 700, 11)
lignes = []
for i, (a, b) in enumerate(pd):
    lignes.append(f"    a = comme_flottant({a}); b = comme_flottant({b});\n"
                  f"    afficher(bits(reste(a, b)));\n"
                  f"    soit c{i}: flottant_32 = flottant_32(a); soit e{i}: flottant_32 = flottant_32(b);\n"
                  f"    afficher(bits(c{i}), bits(e{i}), bits(reste(c{i}, e{i})));\n")
src = "fonction principal() {\n    soit a = 0.0;\n    soit b = 0.0;\n" + "".join(lignes) + "}\n"
sortie, chemin = lancer("vtx64", src)
ls = sortie.split("\n")
ecarts = {64: 0, 32: 0}
premier = ""
try:
    for i, (a, b) in enumerate(pd):
        r = int(ls[2 * i]) % (1 << 64)
        if r != reference(a, b, 64):
            ecarts[64] += 1
            premier = premier or f"Q64 {a:x} % {b:x} : {r:x} au lieu de {reference(a, b, 64):x}"
        x, y, z = (int(v) % (1 << 64) for v in ls[2 * i + 1].split())
        if z != reference(x, y, 32):
            ecarts[32] += 1
            premier = premier or f"Q32 {x:x} % {y:x} : {z:x} au lieu de {reference(x, y, 32):x}"
    verifier(f"Dunon : {len(pd)} restes de 64 bits et autant de 32 bits, au bit près de la référence exacte",
             not any(ecarts.values()), f"{ecarts} ; {premier}")
except (ValueError, IndexError) as e:
    verifier("Dunon : les restes", False, f"{e} ; {sortie[:400]}")
verifier("Dunon : les deux compilateurs, les mêmes mots", memes_mots("vtx64", chemin))

# ---------------------------------------------------------------------------------------------- ce qu'on lit
LISIBLE = """fonction principal() {
    afficher(reste(7.5, 2.0), reste(0.0 - 7.5, 2.0), reste(7.5, 0.0 - 2.0), reste(6.0, 2.0), reste(0.0 - 6.0, 2.0));
    afficher(reste(7.5, 0.0), reste(1.0 / 0.0, 2.0), reste(7.5, 1.0 / 0.0), reste(0.0 / 0.0, 2.0));
    afficher(reste(17, 5), reste(0 - 17, 5), reste(17, 0), reste(17S, 5S), reste(17LL, 0LL - 5LL));
}
"""
ATTENDU = ["1.5 -1.5 1.5 0.0 -0.0", "variable variable 7.5 variable", "2 -2 17 2 2"]
for machine, nom in (("lugus", "Lugus"), ("vtx64", "Dunon")):
    sortie, chemin = lancer(machine, LISIBLE)
    verifier(f"{nom} : les cas qu'on lit (le signe du dividende, -0.0, ∞, zéro, les entiers signés)",
             sortie.split("\n")[:3] == ATTENDU, sortie[:300])
    verifier(f"{nom} : les cas qu'on lit, les mêmes mots", memes_mots(machine, chemin))

# une fonction du programme nommée reste garde la main
PROPRE = ("fonction reste(a: flottant, b: flottant): flottant { retour 42.0; }\n"
          "fonction principal() { afficher(reste(7.5, 2.0), reste(7, 2)); }\n")
for machine, nom in (("lugus", "Lugus"), ("vtx64", "Dunon")):
    sortie, _ = lancer(machine, PROPRE)
    verifier(f"{nom} : une fonction du programme nommée reste garde la main", sortie.startswith("42.0 42.0"), sortie[:200])

print("reste : tout est conforme" if echecs == 0 else f"reste : {echecs} échec(s)")
sys.exit(1 if echecs else 0)
