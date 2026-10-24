#!/usr/bin/env python3
"""flottant_petuar : le flottant quaternaire de 128 bits de vtx (quatre points du cube #RRGGBBAA, 32 chiffres hex, 64 quits ;
quit 63 l'état de Belnap, 7 quits d'exposant en base 4, 56 quits de mantisse). Chaque résultat est comparé à une référence
exacte (fractions de Python, tests/ref_petuar.py) ; les quatre machines doivent s'accorder ; vtxc (vtx.exe) doit produire
les mêmes mots que vtx.py ; les littéraux décimaux sont lus exactement, l'écriture décimale est la plus courte qui redonne le
nombre ; les textes ADN, ARN et cube sont vérifiés ; les erreurs de typage sont refusées par les deux compilateurs."""
import os
import random
import subprocess
import sys
import tempfile
from fractions import Fraction

sys.set_int_max_str_digits(0)

ici = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ici)
import machines  # noqa: E402
import ref_petuar as R  # noqa: E402
import ref_ieee128 as I  # noqa: E402

vtx = machines.vtx
racine = machines.racine
VTX = os.path.join(racine, "vtx-rs", "target", "release", "vtx" + (".exe" if os.name == "nt" else ""))
g = random.Random(4)
mauvais = 0
M = 0xFFFFFFFF


def verifier(nom, ok, detail=""):
    global mauvais
    print(("  ok  " if ok else "  ÉCART ") + nom + (f" : {detail}" if detail and not ok else ""))
    mauvais += not ok


def mots4(x):
    return [(x >> (32 * k)) & M for k in range(4)]


def mots(src, optim=True, partition=False):
    return vtx.assembler(vtx.compiler(src, prelude=True, optim=optim, partition=partition))


def lancer(src, entrees):
    m = mots(src)
    ligne = machines.lignes_rust([(m, entrees)])[0].split("|")
    sor = [int(v) for v in ligne[1].split(",")] if ligne[1] else []
    txt = "".join(map(chr, [int(v) for v in ligne[3][2:].split(",")])) if len(ligne) > 3 and ligne[3].startswith("T:") else ""
    return sor, txt, m


def vtxc_mots(src):
    """Les mots de vtx.exe (vtxc embarqué : prélude, optimisations, partition), ou None s'il refuse le programme."""
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "p.vtx")
        with open(p, "w", encoding="utf-8") as f:
            f.write(src)
        q = os.path.join(d, "p.mots")
        subprocess.run([VTX, "compiler", p, q], capture_output=True, text=True)
        if not os.path.exists(q):
            return None
        return [int(x) for x in open(q).read().strip().split(";")[0].split(",")]


def py_mots_partition(src):
    try:
        return mots(src, True, True)
    except vtx.VtxError:
        return None


# ------------------------------------------------------------------ 1. opérations, contre la référence exacte
SRC1 = """
fonction lire_w(): entier_petuar {
    soit w0 = entrée(); soit w1 = entrée(); soit w2 = entrée(); soit w3 = entrée();
    retour entier_128_de(long_de(w3, w2), long_de(w1, w0));
}
fonction sx(x: flottant_petuar) { sortie(bits(x)); }
fonction principal() {
    soit n = entrée();
    pour i dans 0..n {
        soit a = comme_flottant_petuar(lire_w());
        soit b = comme_flottant_petuar(lire_w());
        soit w = lire_w();
        soit dlo = entrée();
        soit dhi = entrée();
        soit e = entrée();
        sx(a + b); sx(a - b); sx(a * b); sx(a / b); sx(racine(a)); sx(-a);
        sortie(a == b); sortie(a != b); sortie(a < b); sortie(a <= b); sortie(a > b); sortie(a >= b);
        sx(abs(a)); sx(min(a, b)); sx(max(a, b));
        sortie(entier(etat(a)));
        soit d = flottant_64(a);
        sortie(bas(d)); sortie(haut(d));
        sortie(entier_128(a));
        sortie(vers_ieee128(a));
        sx(de_ieee128(w));
        sx(flottant_petuar(flottant_64_de(dhi, dlo)));
        sx(flottant_petuar(e));
        sx(flottant_petuar(w));
        sx(a + e);
        sx(a * 2.5);
        sortie(bits(flottant(a)));
        sx(a + 1.0D);
    }
}
"""


def vers_f(a):
    if not R.est_nombre(a):
        return 0x7FC00000
    s = R.etat(a) == 1
    if R.est_inf(a):
        return 0x7F800000 | (s << 31)
    return I.arrondi(abs(R.valeur(a)), 24, 127, 255) | (s << 31)


def pq_min(a, b):
    sp = R.special(a, b)
    if sp is not None:
        return sp
    return b if R.cmp(b, a) == 1 else a


def pq_max(a, b):
    sp = R.special(a, b)
    if sp is not None:
        return sp
    return b if R.cmp(a, b) == 1 else a


def attendu1(a, b, w, d, e):
    out = []
    p = lambda x: out.extend(mots4(x))
    p(R.add(a, b)); p(R.sub(a, b)); p(R.mul(a, b)); p(R.div(a, b)); p(R.racine(a)); p(R.neg(a))
    c = R.cmp(a, b)
    out += [int(c == 0), int(c != 0), int(c == 1), int(c in (0, 1)), int(c == 2), int(c in (0, 2))]
    p(a ^ (3 << 126) if R.etat(a) == 1 else a); p(pq_min(a, b)); p(pq_max(a, b))
    out.append(a >> 126)
    dd = R.vers_d(a)
    out += [dd & M, dd >> 32]
    p(R.vers_w(a))
    p(R.vers_ieee(a))
    p(R.de_ieee(w))
    p(R.de_d(d))
    p(R.de_w(e))
    p(R.de_w(w))
    p(R.add(a, R.de_w(e)))
    p(R.mul(a, R.de_d(0x4004000000000000)))
    out.append(vers_f(a))
    p(R.add(a, R.de_d(0x3FF0000000000000)))
    return out


cas = []
for _ in range(400):
    a, b = R.hasard(g), R.hasard(g)
    if g.random() < 0.3 and R.est_nombre(a) and R.est_nombre(b) and 0 < R.ef(a) < 16383 and 0 < R.ef(b) < 16383:
        b = (b & ~(0x3FFF << 112)) | (a & (0x3FFF << 112))
    w = I.hasard_x(g) if g.random() < 0.5 else g.getrandbits(g.randint(1, 128))
    d = g.getrandbits(64)
    e = g.getrandbits(32)
    cas.append((a, b, w, d, e))
cas += [(R.signe(0), R.signe(1), 0, 0, 0), (R.inf(0), R.inf(1), I.NAN, 0x7FF8000000000000, 0),
        (R.depuis(Fraction(1)), R.depuis(Fraction(3)), I.INF, 0xFFF0000000000000, 1),
        (R.INCONNU, R.VARIABLE, 0, 0, 2), (R.signe(1), R.signe(1), 1, 1, M)]
ent = [len(cas)]
att = []
for a, b, w, d, e in cas:
    ent += mots4(a) + mots4(b) + mots4(w) + [d & M, d >> 32, e]
    att += attendu1(a, b, w, d, e)
sor, _, m1 = lancer(SRC1, ent)
par = len(att) // len(cas)
ec = [i for i, (u, v) in enumerate(zip(sor, att)) if u != v]
verifier(f"opérations, comparaisons, état et conversions contre la référence exacte ({len(cas)} cas)",
         not ec and len(sor) == len(att),
         f"{len(ec)} écart(s), premier au cas {ec[0] // par if ec else '-'}, place {ec[0] % par if ec else '-'} ; longueurs {len(sor)}/{len(att)}")
ent40 = [40] + ent[1:1 + 15 * 40]
res = machines.lancer_toutes([(m1, ent40)])
ecm = machines.comparer(res)
verifier("les quatre machines s'accordent (Python, Rust, JS interprété, JS traduit)", not any(ecm.values()), str(ecm))

# ------------------------------------------------------------------ 2. littéraux décimaux : lus exactement, mêmes mots par vtxc
def dec_hasard():
    c = g.random()
    if c < 0.25:
        return f"{g.randint(0, 10 ** g.randint(1, 40))}.{g.randint(0, 10 ** g.randint(1, 40))}"
    if c < 0.45:
        return f"{g.randint(1, 9)}.{g.randint(0, 10 ** 30)}e{g.randint(-4960, 4930)}"
    if c < 0.6:
        return f"{g.randint(1, 10 ** 36)}e{g.randint(-4990, -4900)}"         # sous-normaux et bord
    if c < 0.7:
        return f"{g.randint(1, 10 ** 36)}e{g.randint(4890, 4895)}"            # près du plus grand
    if c < 0.85:
        # milieux exacts entre deux flottant_petuar : mantisse impaire de 113 bits (sur une puissance paire de 2)
        mm = (g.getrandbits(111) | (1 << 111)) * 2 + 1
        ex = -2 * g.randint(1, 60) - 1
        v = Fraction(mm) * Fraction(2) ** ex
        # écriture décimale exacte du milieu
        den = v.denominator
        k = den.bit_length() - 1
        num = v.numerator * 5 ** k
        t = str(num)
        return (t[:-k] or "0") + "." + t[-k:].rjust(k, "0") if k else t
    return str(g.randint(0, 2 ** 120))


lits = [dec_hasard() for _ in range(240)] + ["0", "1", "0.1", "1e-4966", "1e4932", "3.5e-4965", "1.18973149535723176508575932662800702e4932"]
lits_ok = []
for t in lits:
    try:
        lits_ok.append((t, vtx.bits_petuar_decimal(t)))
    except vtx.VtxError:
        pass
justes = 0
for t, b in lits_ok:
    m_ = __import__("re").fullmatch(r"(\d+)(?:\.(\d+))?(?:[eE]([-+]?\d+))?", t)
    v = Fraction(int(m_.group(1) + (m_.group(2) or ""))) * Fraction(10) ** (int(m_.group(3) or 0) - len(m_.group(2) or ""))
    justes += b == (R.signe(0) | R.arrondi(v) if v else R.signe(0))
verifier(f"littéraux décimaux lus exactement par vtx.py ({len(lits_ok)} nombres, sous-normaux, bords, milieux exacts)",
         justes == len(lits_ok), f"{justes}/{len(lits_ok)}")
idem = 0
paquets = [lits_ok[i:i + 40] for i in range(0, len(lits_ok), 40)]
for pq in paquets:
    s = "fonction principal() {\n" + "".join(f"    sortie(bits({t}Q));\n" for t, _ in pq) + "}\n"
    idem += vtxc_mots(s) == py_mots_partition(s)
verifier(f"littéraux : vtxc (vtx.exe) donne les mêmes mots que vtx.py ({len(paquets)} programmes)", idem == len(paquets),
         f"{idem}/{len(paquets)}")
trop = vtxc_mots("fonction principal() { sortie(bits(1.2e4933Q)); }") is None
try:
    vtx.bits_petuar_decimal("1.2e4933")
    trop_py = False
except vtx.VtxError:
    trop_py = True
verifier("littéral trop grand refusé par les deux compilateurs", trop and trop_py)

# ------------------------------------------------------------------ 3. écriture décimale la plus courte
def hasard_moyen():
    v = R.hasard(g)
    if R.est_nombre(v) and R.ef(v) < 16383 and v & R.MANT and g.random() < 0.95:
        v = (v & ~(0x3FFF << 112)) | ((8247 - 55 + g.randint(-200, 200)) << 112)
        if v & R.MANT < 1 << 110:
            v |= 1 << 110
    return v


vals = [hasard_moyen() for _ in range(120)] + [R.depuis(Fraction(1, 10)), R.depuis(Fraction(1)), R.depuis(Fraction(4) ** 30),
                                            R.signe(0) | (2 << 112) | (1 << 110), R.signe(0) | 1]
SRC3 = """
fonction principal() {
    soit n = entrée();
    pour i dans 0..n {
        soit w0 = entrée(); soit w1 = entrée(); soit w2 = entrée(); soit w3 = entrée();
        afficher(comme_flottant_petuar(entier_128_de(long_de(w3, w2), long_de(w1, w0))));
    }
}
"""
ent3 = [len(vals)]
for v in vals:
    ent3 += mots4(v)
_, txt3, _ = lancer(SRC3, ent3)
lignes = txt3.split("\n")
bons = 0
details = []
for v, t in zip(vals, lignes):
    if not R.est_nombre(v):
        ok = t == ("inconnu" if R.etat(v) == 0 else "variable")
    elif R.est_inf(v):
        ok = t == ("-inf" if R.etat(v) == 1 else "inf")
    elif R.est_zero(v):
        ok = t in ("0.0", "-0.0")
    else:
        neg = t.startswith("-")
        u = t[1:] if neg else t
        mant, _, ex = u.partition("e")
        ent_, _, fr = mant.partition(".")
        chiffres = (ent_ + fr).lstrip("0").rstrip("0") or "0"
        k = int(ex or 0) - len(fr)
        val = Fraction(int(ent_ + fr)) * Fraction(10) ** k
        relu = (R.signe(1) if neg else R.signe(0)) | R.arrondi(val)
        ok = relu == v
        # le plus court : avec un chiffre de moins, aucun nombre ne redonne v
        if ok and len(chiffres) > 1:
            n = len(chiffres) - 1
            vv = abs(R.valeur(v))
            e10 = len(str(vv.numerator // vv.denominator)) if vv >= 1 else -len(str(vv.denominator // vv.numerator))
            for ee in range(e10 - n - 3, e10 - n + 4):
                q = vv / Fraction(10) ** ee
                for cand in (q.numerator // q.denominator, q.numerator // q.denominator + 1):
                    if cand and len(str(cand)) <= n and R.arrondi(Fraction(cand) * Fraction(10) ** ee) == v & ~(3 << 126):
                        ok = False
    bons += ok
    if not ok and len(details) < 3:
        details.append(f"{v:032x} -> {t}")
verifier(f"afficher : les chiffres les plus courts qui redonnent exactement le nombre ({len(vals)} valeurs)",
         bons == len(vals) and len(lignes) >= len(vals), f"{bons}/{len(vals)} {details}")

# ------------------------------------------------------------------ 4. ADN, ARN, cube
SRC4 = """
fonction principal() {
    soit n = entrée();
    pour i dans 0..n {
        soit w0 = entrée(); soit w1 = entrée(); soit w2 = entrée(); soit w3 = entrée();
        soit w = entier_128_de(long_de(w3, w2), long_de(w1, w0));
        afficher(texte_adn(w));
        afficher(texte_arn(w));
        afficher(texte_cube(w));
    }
    afficher(adn"GATTACAGATTACAGATTACA");
    afficher(comme_flottant_petuar(adn"GGAAAAAACAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA") == 1Q);
    afficher(texte_cube(#A000C90F_DAA22168_C234C4C6_628B80DC));
}
"""
ws = [g.getrandbits(128) for _ in range(30)] + [0, (1 << 128) - 1]
ent4 = [len(ws)]
for w in ws:
    ent4 += mots4(w)
_, txt4, m4 = lancer(SRC4, ent4)
att4 = []
for w in ws:
    q = [(w >> (2 * (63 - i))) & 3 for i in range(64)]
    att4 += ["".join("ACGT"[x] for x in q), "".join("ACGU"[x] for x in q),
             "#" + "_".join(f"{(w >> (32 * k)) & M:08X}" for k in (3, 2, 1, 0))]
v_adn = 0
for x in "GATTACAGATTACAGATTACA":
    v_adn = v_adn * 4 + "ACGT".index(x)
att4 += [str(v_adn), "1", "#A000C90F_DAA22168_C234C4C6_628B80DC"]
l4 = txt4.split("\n")
verifier("texte_adn, texte_arn, texte_cube ; adn\"…\" de plus de 16 bases ; littéral de quatre points", l4[:len(att4)] == att4,
         str([(a, b) for a, b in zip(l4, att4) if a != b][:2]))

# ------------------------------------------------------------------ 5. vtxc : mêmes mots que vtx.py
def prog_x(r):
    def lit():
        t = r.choice(["1.5", "0.1", "3", "2.5e10", "7e-300", "123456789.123456789", "1e4000", "4e-4950"])
        return f"{t}Q" if r.random() < .8 else f"(-{t}Q)"
    v = ["a", "b", "c"]
    L = ["fonction aide(p: flottant_petuar, q: flottant_petuar): flottant_petuar {", "    retour p * q - p / (q + 1Q);", "}",
         "fonction principal() {"]
    for x in v:
        L.append(f"    soit {x}: flottant_petuar = {lit()};")
    for _ in range(r.randint(4, 8)):
        x, y, z = (r.choice(v) for _ in range(3))
        e = r.choice([f"{y} + {z}", f"{y} - {z}", f"{y} * {z}", f"{y} / {z}", f"racine(abs({y}))", f"aide({y}, {z})",
                      f"min({y}, {z})", f"max({y}, 2)", f"-{y}", f"{y} + 1", f"{y} * 0.5", f"{y} - 2.0D",
                      f"flottant_petuar(entier_128({z}))", f"de_ieee128(vers_ieee128({y}))"])
        L.append(f"    {x} = {e};")
        c = r.choice(["<", ">", "<=", ">=", "==", "!="])
        L.append(f"    si {x} {c} {r.choice(v)} {{ afficher(1); }} sinon {{ afficher(0); }}")
    L.append("    afficher(a); afficher(texte(b)); afficher(flottant_64(c)); afficher(long(a)); afficher(entier(b));")
    L.append("    selon etat(a / b) { vrai { afficher(2); } faux { afficher(1); } inconnu { afficher(0); } variable { afficher(3); } }")
    L.append("    afficher(texte_adn(bits(c))); afficher(pi_petuar()); afficher(flottant(a));")
    L.append("}")
    return "\n".join(L) + "\n"


rx = random.Random(77)
NX = 12
okx = sum(vtxc_mots(s) == py_mots_partition(s) for s in (prog_x(rx) for _ in range(NX)))
exd = os.path.join(racine, "exemples", "petuar")
exs = sorted(n for n in os.listdir(exd) if n.endswith(".vtx")) if os.path.isdir(exd) else []
okex = sum(vtxc_mots(open(os.path.join(exd, n), encoding="utf-8").read()) ==
           py_mots_partition(open(os.path.join(exd, n), encoding="utf-8").read()) for n in exs)
verifier(f"vtxc (vtx.exe) : mêmes mots que vtx.py sur {NX} programmes aléatoires et {len(exs)} exemples", okx == NX and okex == len(exs),
         f"{okx}/{NX}, exemples {okex}/{len(exs)}")

# ------------------------------------------------------------------ 6. erreurs de typage, refusées par les deux compilateurs
ERREURS = {
    "flottant_petuar + long": "fonction principal() { soit a = 1Q; soit b = 2L; afficher(a + b); }",
    "flottant_petuar + entier_128": "fonction principal() { soit a = 1Q; afficher(a + 2LL); }",
    "reste": "fonction principal() { soit a = 1Q % 2Q; }",
    "bit à bit": "fonction principal() { soit a = 1Q & 2Q; }",
    "décalage": "fonction principal() { soit a = 1Q << 2; }",
    "non": "fonction principal() { soit a = ~1Q; }",
    "condition": "fonction principal() { soit a = 1Q; si a { afficher(1); } }",
    "vers entier implicite": "fonction principal() { soit a = 1Q; soit n: entier = a; }",
    "vers flottant_64 implicite": "fonction principal() { soit a = 1Q; soit d: flottant_64 = 1.0D; d = a; }",
    "champ": "structure P { x: flottant_petuar }\nfonction principal() { soit p = P { x: 1Q }; }",
    "écriture mémoire": "fonction principal() { @2[0] = 1Q; }",
    "trop grand": "fonction principal() { soit a = 2e4932Q; }",
    "comme_flottant_petuar d'un entier": "fonction principal() { soit a = comme_flottant_petuar(3); }",
}
for nom, src in ERREURS.items():
    try:
        mots(src)
        py = False
    except vtx.VtxError:
        py = True
    verifier("erreur attendue : " + nom, py and vtxc_mots(src) is None, f"vtx.py {py}")

print("Tout est conforme." if not mauvais else f"{mauvais} écart(s)")
sys.exit(1 if mauvais else 0)
