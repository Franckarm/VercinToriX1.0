#!/usr/bin/env python3
"""vtx64 : le compilateur du SPU-64 (entier et flottant de 64 bits par défaut, entier_32 et flottant_32 au choix,
entier_petuar et flottant_petuar sur deux mots). Chaque résultat est comparé à une référence exacte en Python (fractions,
entiers de Python, spu64/qflot.py) ; les programmes tournent sur la machine Rust (vtx64), et la machine de référence en
Python doit donner exactement les mêmes lignes.

    python3 tests/test_vtx64.py"""
import math
import os
import random
import subprocess
import sys
import tempfile
from fractions import Fraction

sys.set_int_max_str_digits(0)
ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, racine)
sys.path.insert(0, ici)
sys.path.insert(0, os.path.join(racine, "spu64"))
sys.path.insert(0, os.path.join(racine, "spu128"))
import vtx128 as V  # noqa: E402
import spu128 as S  # noqa: E402
from qflot import Q32, Q64, Q128  # noqa: E402
import ref_petuar as R  # noqa: E402
import ref_ieee128 as I  # noqa: E402

EXE = os.path.join(racine, "vtx-rs", "target", "release", "lugus" + (".exe" if os.name == "nt" else ""))
M64 = (1 << 64) - 1
g = random.Random(64)
mauvais = 0


def verifier(nom, ok, detail=""):
    global mauvais
    print(("  ok  " if ok else "  ÉCART ") + nom + (f" : {detail}" if detail and not ok else ""))
    mauvais += not ok


def mots(src):
    return V.assembler(V.compiler(src))


def lignes_rust(progs):
    """progs : [(mots, entrées)] -> une ligne « pas|sorties|mémoire|B:…|T:… » par programme (machine Rust)."""
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        for m, e in progs:
            f.write(",".join(map(str, m)) + ";" + ",".join(map(str, e)) + "\n")
        nom = f.name
    r = subprocess.run([EXE, "corpus", nom], capture_output=True, text=True)
    os.unlink(nom)
    return r.stdout.rstrip("\n").split("\n")


def lancer(src, entrees=()):
    m = mots(src)
    ligne = lignes_rust([(m, entrees)])[0]
    if ligne.startswith("ERREUR"):
        raise RuntimeError(ligne)
    champs = ligne.split("|")
    sor = [int(v) for v in champs[1].split(",")] if champs[1] else []
    txt = ""
    for c in champs[3:]:
        if c.startswith("T:") and len(c) > 2:
            txt = "".join(map(chr, (int(v) for v in c[2:].split(","))))
    return sor, txt, m


def deux(x):
    return [x & M64, (x >> 64) & M64]


# ------------------------------------------------------------------ 1. la suite de tests du compilateur
import io
import contextlib
tampon = io.StringIO()
with contextlib.redirect_stdout(tampon):
    tout = V.tests()
fin = tampon.getvalue().strip().split("\n")[-1]
verifier(f"suite de vtx128 ({fin})", tout, "\n".join(l for l in tampon.getvalue().split("\n") if l.startswith("ÉCHEC")))

# ------------------------------------------------------------------ 2. entiers de 64 bits et entier_32, contre Python
def s64(x):
    x &= M64
    return x - (1 << 64) if x >> 63 else x


def s32(x):
    x &= 0xFFFFFFFF
    return x - (1 << 32) if x >> 31 else x


def tronc(a, b):
    q = abs(a) // abs(b)
    return -q if (a < 0) != (b < 0) else q


SRC2 = """
fonction principal() {
    soit n = entrée();
    pour i dans 0..n {
        soit a = entrée(); soit b = entrée(); soit k = entrée() & 63;
        sortie(a + b); sortie(a - b); sortie(a * b); sortie(a / b); sortie(a % b); sortie(a ./ b); sortie(a .% b);
        sortie(a << k); sortie(a >> k); sortie(a .>> k); sortie(a & b); sortie(a | b); sortie(a ^ b); sortie(~a);
        sortie(a < b); sortie(a <= b); sortie(a .< b); sortie(a .>= b); sortie(a == b);
        soit x: entier_32 = entier_32(a); soit y: entier_32 = entier_32(b); soit j = k & 31;
        sortie(x + y); sortie(x - y); sortie(x * y); sortie(x / y); sortie(x % y); sortie(x ./ y); sortie(x .% y);
        sortie(x << j); sortie(x >> j); sortie(x .>> j); sortie(~x); sortie(x .< y); sortie(x .> y); sortie(x < y);
        sortie(abs(x)); sortie(min(x, y)); sortie(max(x, y)); sortie(x + a);
    }
}
"""


def attendu2(a, b, k):
    o = []
    sa, sb = s64(a), s64(b)
    o += [(a + b) & M64, (a - b) & M64, (a * b) & M64, a // b if b else M64, a % b if b else a]
    o += [(tronc(sa, sb) & M64) if b else M64, ((sa - tronc(sa, sb) * sb) & M64) if b else a]
    o += [(a << k) & M64, a >> k, (sa >> k) & M64, a & b, a | b, a ^ b, ~a & M64]
    o += [int(a < b), int(a <= b), int(sa < sb), int(sa >= sb), int(a == b)]
    x, y, j = a & 0xFFFFFFFF, b & 0xFFFFFFFF, k & 31
    sx, sy = s32(x), s32(y)
    M = 0xFFFFFFFF
    o += [(x + y) & M, (x - y) & M, (x * y) & M, x // y if y else M, x % y if y else x]
    o += [(tronc(sx, sy) & M) if y else M, ((sx - tronc(sx, sy) * sy) & M) if y else x]
    o += [(x << j) & M, x >> j, (sx >> j) & M, ~x & M, int(sx < sy), int(sx > sy), int(x < y)]
    o += [abs(sx) & M, (sx if sx <= sy else sy) & M, (sx if sx >= sy else sy) & M, (x + a) & M64]
    return o


def ent_hasard():
    c = g.random()
    if c < 0.3:
        return g.getrandbits(64)
    if c < 0.5:
        return g.randint(0, 100)
    if c < 0.65:
        return M64 - g.randint(0, 100)
    if c < 0.8:
        return g.getrandbits(32)
    return g.choice([0, 1, 1 << 63, (1 << 63) - 1, 1 << 31, (1 << 31) - 1, 1 << 32, 0xFFFFFFFF, 0x80000000])


cas2 = [(ent_hasard(), ent_hasard(), g.randint(0, 63)) for _ in range(300)]
ent2 = [len(cas2)]
att2 = []
for a, b, k in cas2:
    ent2 += [a, b, k]
    att2 += attendu2(a, b, k)
sor2, _, m2 = lancer(SRC2, ent2)
ec = [i for i, (u, v) in enumerate(zip(sor2, att2)) if u != v]
par = len(att2) // len(cas2)
verifier(f"entier (64 bits) et entier_32 : opérations, signées comprises ({len(cas2)} cas)",
         not ec and len(sor2) == len(att2),
         f"{len(ec)} écart(s) ; premier : cas {ec[0] // par if ec else '-'}, place {ec[0] % par if ec else '-'}, "
         f"{sor2[ec[0]] if ec else ''} au lieu de {att2[ec[0]] if ec else ''} ; longueurs {len(sor2)}/{len(att2)}")

# ------------------------------------------------------------------ 3. flottants quaternaires de 64 et 32 bits
SRC3 = """
fonction principal() {
    soit n = entrée();
    pour i dans 0..n {
        soit a = comme_flottant(entrée()); soit b = comme_flottant(entrée()); soit e = entrée();
        sortie(bits(a + b)); sortie(bits(a - b)); sortie(bits(a * b)); sortie(bits(a / b)); sortie(bits(racine(a)));
        sortie(bits(-a)); sortie(a == b); sortie(a != b); sortie(a < b); sortie(a <= b); sortie(a > b); sortie(a >= b);
        sortie(bits(abs(a))); sortie(bits(min(a, b))); sortie(bits(max(a, b)));
        sortie(entier(a)); sortie(arrondi(a)); sortie(bits(flottant(e))); sortie(bits(flottant_signe(e))); sortie(bits(a + e));
        soit x: flottant_32 = flottant_32(a); soit y: flottant_32 = flottant_32(b);
        sortie(bits(x)); sortie(bits(x + y)); sortie(bits(x * y)); sortie(bits(x / y)); sortie(bits(racine(x)));
        sortie(x < y); sortie(bits(flottant(x))); sortie(bits(x + a)); sortie(bits(flottant_32(e)));
        sortie(vers_ieee64(a)); sortie(bits(de_ieee64(e)));
    }
}
"""


def f_hasard(F):
    c = g.random()
    s = g.getrandbits(1)
    if c < 0.03:
        return F.INCONNU
    if c < 0.05:
        return F.VARIABLE
    if c < 0.09:
        return F.signe(s)
    if c < 0.12:
        return F.inf(s)
    if c < 0.17:
        return F.signe(s) | g.getrandbits(g.randint(1, F.P - 2))
    if c < 0.6:
        e = F.biais - F.nq + g.randint(-12, 12)
    else:
        e = g.randint(1, F.emax - 1)
    m = g.getrandbits(F.P) | (1 << g.choice([F.P - 2, F.P - 1]))
    return F.signe(s) | (e << F.P) | (m & F.mant)


def sq(F, a):
    """Q64 -> Q32 (un seul arrondi)."""
    return Q64.vers(Q32, a)


def attendu3(a, b, e):
    F = Q64
    c = F.cmp(a, b)
    o = [F.add(a, b), F.sub(a, b), F.mul(a, b), F.div(a, b), F.racine(a), F.neg(a)]
    o += [int(c == 0), int(c != 0), int(c == 1), int(c in (0, 1)), int(c == 2), int(c in (0, 2))]
    o.append(F.neg(a) if F.etat(a) == 1 else a)
    sp = 3 if F.etat(a) == 3 or F.etat(b) == 3 else None
    mn = b if F.cmp(b, a) == 1 else a          # min : b si b < a (FLT), sinon a
    mx = b if F.cmp(a, b) == 1 else a
    o += [mn, mx]
    o += [F.vers_entier(a, False), F.vers_entier(a, True), F.de_entier(e), F.de_entier(s64(e)), F.add(a, F.de_entier(e))]
    x, y = Q64.vers(Q32, a), Q64.vers(Q32, b)
    o += [x, Q32.add(x, y), Q32.mul(x, y), Q32.div(x, y), Q32.racine(x), int(Q32.cmp(x, y) == 1), Q32.vers(Q64, x),
          Q64.add(Q32.vers(Q64, x), a), Q64.vers(Q32, Q64.de_entier(e))]
    from qflot import vers_ieee64, de_ieee64
    o += [vers_ieee64(a), de_ieee64(e)]
    return o


cas3 = [(f_hasard(Q64), f_hasard(Q64), ent_hasard()) for _ in range(300)]
ent3 = [len(cas3)]
att3 = []
for a, b, e in cas3:
    ent3 += [a, b, e]
    att3 += attendu3(a, b, e)
sor3, _, m3 = lancer(SRC3, ent3)
ec = [i for i, (u, v) in enumerate(zip(sor3, att3)) if u != v]
par = len(att3) // len(cas3)
verifier(f"flottant (quaternaire, 64 bits) et flottant_32 : opérations, conversions, IEEE ({len(cas3)} cas)",
         not ec and len(sor3) == len(att3),
         f"{len(ec)} écart(s) ; premier : cas {ec[0] // par if ec else '-'}, place {ec[0] % par if ec else '-'}, "
         f"{hex(sor3[ec[0]]) if ec else ''} au lieu de {hex(att3[ec[0]]) if ec else ''} ; longueurs {len(sor3)}/{len(att3)}")

# ------------------------------------------------------------------ 4. écriture décimale la plus courte (64 et 32 bits)
def relire(F, t):
    neg = t.startswith("-")
    u = t[1:] if neg else t
    mant, _, ex = u.partition("e")
    ent_, _, fr = mant.partition(".")
    val = Fraction(int(ent_ + fr)) * Fraction(10) ** (int(ex or 0) - len(fr))
    return neg, val, (ent_ + fr).lstrip("0").rstrip("0") or "0"


def juste(F, v, t):
    if not F.est_nombre(v):
        return t == ("inconnu" if F.etat(v) == 0 else "variable")
    if F.est_inf(v):
        return t == ("-inf" if F.etat(v) == 1 else "inf")
    if F.est_zero(v):
        return t in ("0.0", "-0.0")
    try:
        neg, val, chiffres = relire(F, t)
    except ValueError:
        return False
    if F.depuis(-val if neg else val) & ~(3 << (F.taille - 2)) != F.arrondi(abs(F.valeur(v))) or neg != (F.etat(v) == 1):
        return False
    # le plus court : avec un chiffre de moins, aucun nombre ne redonne v
    n = len(chiffres) - 1
    if n < 1:
        return True
    vv = abs(F.valeur(v))
    e10 = math.floor(math.log10(vv.numerator) - math.log10(vv.denominator))
    for ee in range(e10 - n - 2, e10 - n + 3):
        q = vv / Fraction(10) ** ee
        for cand in (q.numerator // q.denominator, q.numerator // q.denominator + 1):
            if cand and len(str(cand)) <= n and F.arrondi(Fraction(cand) * Fraction(10) ** ee) == F.arrondi(vv):
                return False
    return True


vals64 = [f_hasard(Q64) for _ in range(150)] + [Q64.depuis(Fraction(1, 10)), Q64.depuis(Fraction(1)), Q64.depuis(Fraction(1, 3)),
                                               Q64.depuis(Fraction(2) ** 60), Q64.signe(0) | 1, Q64.inf(1)]
vals32 = [f_hasard(Q32) for _ in range(150)] + [Q32.depuis(Fraction(1, 10)), Q32.depuis(Fraction(7, 3)), Q32.signe(0) | 1]
SRC4 = """
fonction principal() {
    soit n = entrée();
    pour i dans 0..n { afficher(comme_flottant(entrée())); }
    soit m = entrée();
    pour i dans 0..m { afficher(comme_flottant_32(entrée())); }
}
"""
_, txt4, _ = lancer(SRC4, [len(vals64)] + vals64 + [len(vals32)] + vals32)
l4 = txt4.split("\n")
b64 = [juste(Q64, v, t) for v, t in zip(vals64, l4)]
b32 = [juste(Q32, v, t) for v, t in zip(vals32, l4[len(vals64):])]
det = [f"{v:016x} -> {t}" for v, t, b in zip(vals64, l4, b64) if not b][:3]
verifier(f"afficher(flottant) : les chiffres les plus courts qui redonnent exactement le nombre ({len(vals64)} valeurs)",
         all(b64) and len(b64) == len(vals64), f"{sum(b64)}/{len(vals64)} {det}")
verifier(f"afficher(flottant_32) : idem ({len(vals32)} valeurs)", all(b32) and len(b32) == len(vals32),
         f"{sum(b32)}/{len(vals32)}")

# ------------------------------------------------------------------ 5. flottant_petuar sur deux mots, contre la référence
SRC5 = """
fonction lire_w(): entier_petuar { soit w0 = entrée(); soit w1 = entrée(); retour entier_petuar_de(w1, w0); }
fonction sx(x: flottant_petuar) { sortie(bits(x)); }
fonction principal() {
    soit n = entrée();
    pour i dans 0..n {
        soit a = comme_flottant_petuar(lire_w());
        soit b = comme_flottant_petuar(lire_w());
        soit w = lire_w();
        soit d = comme_flottant(entrée());
        soit e = entrée();
        sx(a + b); sx(a - b); sx(a * b); sx(a / b); sx(racine(a)); sx(-a);
        sortie(a == b); sortie(a != b); sortie(a < b); sortie(a <= b); sortie(a > b); sortie(a >= b);
        sx(abs(a)); sx(min(a, b)); sx(max(a, b));
        sortie(entier(etat(a)));
        sortie(bits(flottant(a)));
        sortie(entier_petuar(a));
        sortie(vers_ieee128(a));
        sx(de_ieee128(w));
        sx(flottant_petuar(d));
        sx(flottant_petuar(e));
        sx(flottant_petuar(w));
        sx(a + e);
        sx(a * 2.5);
        sortie(bits(flottant_32(a)));
        sx(a + 1.0);
    }
}
"""


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


def attendu5(a, b, w, d, e):
    out = []
    p = lambda x: out.extend(deux(x))
    p(R.add(a, b)); p(R.sub(a, b)); p(R.mul(a, b)); p(R.div(a, b)); p(R.racine(a)); p(R.neg(a))
    c = R.cmp(a, b)
    out += [int(c == 0), int(c != 0), int(c == 1), int(c in (0, 1)), int(c == 2), int(c in (0, 2))]
    p(a ^ (3 << 126) if R.etat(a) == 1 else a); p(pq_min(a, b)); p(pq_max(a, b))
    out.append(a >> 126)
    out.append(Q128.vers(Q64, a))
    p(R.vers_w(a))
    p(R.vers_ieee(a))
    p(R.de_ieee(w))
    p(Q64.vers(Q128, d))
    p(R.de_w(e))
    p(R.de_w(w))
    p(R.add(a, R.de_w(e)))
    p(R.mul(a, R.depuis(Fraction(5, 2))))
    out.append(Q128.vers(Q32, a))
    p(R.add(a, R.depuis(Fraction(1))))
    return out


cas5 = []
for _ in range(250):
    a, b = R.hasard(g), R.hasard(g)
    if g.random() < 0.3 and R.est_nombre(a) and R.est_nombre(b) and 0 < R.ef(a) < 16383 and 0 < R.ef(b) < 16383:
        b = (b & ~(0x3FFF << 112)) | (a & (0x3FFF << 112))
    w = I.hasard_x(g) if g.random() < 0.5 else g.getrandbits(g.randint(1, 128))
    cas5.append((a, b, w, f_hasard(Q64), ent_hasard()))
cas5 += [(R.signe(0), R.signe(1), 0, 0, 0), (R.inf(0), R.inf(1), I.NAN, Q64.inf(1), 0),
         (R.depuis(Fraction(1)), R.depuis(Fraction(3)), I.INF, Q64.VARIABLE, 1), (R.INCONNU, R.VARIABLE, 0, 0, 2)]
ent5 = [len(cas5)]
att5 = []
for a, b, w, d, e in cas5:
    ent5 += deux(a) + deux(b) + deux(w) + [d, e]
    att5 += attendu5(a, b, w, d, e)
sor5, _, m5 = lancer(SRC5, ent5)
ec = [i for i, (u, v) in enumerate(zip(sor5, att5)) if u != v]
par = len(att5) // len(cas5)
verifier(f"flottant_petuar (deux mots) : opérations, comparaisons, conversions contre la référence exacte ({len(cas5)} cas)",
         not ec and len(sor5) == len(att5),
         f"{len(ec)} écart(s) ; premier : cas {ec[0] // par if ec else '-'}, place {ec[0] % par if ec else '-'} ; "
         f"longueurs {len(sor5)}/{len(att5)}")

# ------------------------------------------------------------------ 6. entier_petuar : opérations, contre Python
M128 = (1 << 128) - 1


def s128(x):
    x &= M128
    return x - (1 << 128) if x >> 127 else x


SRC6 = """
fonction lire_w(): entier_petuar { soit w0 = entrée(); soit w1 = entrée(); retour entier_petuar_de(w1, w0); }
fonction principal() {
    soit n = entrée();
    pour i dans 0..n {
        soit a = lire_w(); soit b = lire_w(); soit k = entrée() & 127;
        sortie(a + b); sortie(a - b); sortie(a * b); sortie(a / b); sortie(a % b); sortie(a << k); sortie(a >> k);
        sortie(a & b); sortie(a | b); sortie(a ^ b); sortie(~a); sortie(a < b); sortie(a == b); sortie(a >= b);
        sortie(abs(a)); sortie(min(a, b)); sortie(max(a, b)); sortie(bas(a)); sortie(haut(a));
        sortie(a + k); sortie(entier_petuar_signe(0 - k));
        afficher(a);
    }
}
"""


def attendu6(a, b, k):
    o = []
    sa, sb = s128(a), s128(b)
    p = lambda x: o.extend(deux(x & M128))
    p(a + b); p(a - b); p(a * b)
    if b:
        q = tronc(sa, sb)
        p(q); p(sa - q * sb)
    else:
        p(M128 if sa >= 0 else 1); p(a)      # la division par zéro : quotient tout à un (signe corrigé), reste a
    p(a << k); p(sa >> k); p(a & b); p(a | b); p(a ^ b); p(~a)
    o += [int(sa < sb), int(a == b), int(sa >= sb)]
    p(abs(sa)); p(min(sa, sb)); p(max(sa, sb))
    o += [a & M64, a >> 64]
    p(a + k); p(-k)
    return o


def w_hasard():
    c = g.random()
    if c < 0.4:
        return g.getrandbits(128)
    if c < 0.6:
        return g.getrandbits(g.randint(1, 70))
    if c < 0.8:
        return M128 - g.getrandbits(g.randint(1, 70))
    return g.choice([0, 1, 1 << 127, (1 << 127) - 1, 1 << 64, M64])


cas6 = [(w_hasard(), w_hasard(), g.randint(0, 127)) for _ in range(150)]
ent6 = [len(cas6)]
att6, txt_att6 = [], []
for a, b, k in cas6:
    ent6 += deux(a) + deux(b) + [k]
    att6 += attendu6(a, b, k)
    txt_att6.append(str(s128(a)))
sor6, txt6, _ = lancer(SRC6, ent6)
# la division par zéro n'est pas comparée (convention du prélude) : on retire les places 6 à 9 des cas à b nul
par = len(att6) // len(cas6)
ec = [i for i, (u, v) in enumerate(zip(sor6, att6)) if u != v and not (cas6[i // par][1] == 0 and 6 <= i % par < 10)]
verifier(f"entier_petuar : opérations, décalages, comparaisons signées ({len(cas6)} cas)", not ec and len(sor6) == len(att6),
         f"{len(ec)} écart(s) ; premier : cas {ec[0] // par if ec else '-'}, place {ec[0] % par if ec else '-'}")
verifier("afficher(entier_petuar) : écriture décimale signée", txt6.split("\n")[:len(cas6)] == txt_att6,
         str([(a, b) for a, b in zip(txt6.split("\n"), txt_att6) if a != b][:2]))

# ------------------------------------------------------------------ 7. bibliothèque mathématique (précision en ulps)
def ulps(v, x):
    """Écart de v (Q64) à la valeur réelle x (float de Python, ou Fraction), en unités du dernier quit... de bit."""
    if not Q64.est_nombre(v) or Q64.est_inf(v):
        return 0 if (math.isinf(x) and Q64.est_inf(v)) else 10 ** 9
    if x == 0:
        return 0 if Q64.est_zero(v) else 10 ** 9
    val = Q64.valeur(v)
    ex = Fraction(x)
    p = math.floor(math.log2(abs(x))) - 50      # un ulp de 51 bits (le pire cas du quaternaire)
    return float(abs(val - ex) / Fraction(2) ** p)


# référence : la bibliothèque de Python (binary64, à moins d'un ulp de 53 bits : un quart d'ulp du quaternaire)
fonctions = [("sinus", math.sin, lambda: g.uniform(-50, 50)), ("cosinus", math.cos, lambda: g.uniform(-50, 50)),
             ("tangente", math.tan, lambda: g.uniform(-1.5, 1.5)), ("exponentielle", math.exp, lambda: g.uniform(-700, 700)),
             ("logarithme", math.log, lambda: math.exp(g.uniform(-700, 700))),
             ("arctangente", math.atan, lambda: g.uniform(-100, 100)), ("arcsinus", math.asin, lambda: g.uniform(-1, 1)),
             ("arccosinus", math.acos, lambda: g.uniform(-1, 1))]
src7 = "fonction principal() {\n    soit n = entrée();\n    pour i dans 0..n {\n        soit x = comme_flottant(entrée());\n"
src7 += "".join(f"        sortie(bits({nom}(x)));\n" for nom, _, _ in fonctions[:3])
src7 += "    }\n"
for k, (nom, _, _) in enumerate(fonctions[3:]):
    src7 += f"    pour i dans 0..n {{ sortie(bits({nom}(comme_flottant(entrée())))); }}\n"
src7 += "}\n"
N7 = 120
xs = [[Q64.depuis(Fraction(gen())) for _ in range(N7)] for _, _, gen in fonctions]
ent7 = [N7]
for i in range(N7):
    ent7 += [xs[0][i]]
for k in range(3, len(fonctions)):
    ent7 += xs[k]
# les trois premières lisent le même x
xs[1], xs[2] = xs[0], xs[0]
sor7, _, _ = lancer(src7, ent7)
pires = {}
pos = 0
res = {nom: [] for nom, _, _ in fonctions}
for i in range(N7):
    for k in range(3):
        res[fonctions[k][0]].append(sor7[pos])
        pos += 1
for k in range(3, len(fonctions)):
    res[fonctions[k][0]] = sor7[pos:pos + N7]
    pos += N7
for k, (nom, f, _) in enumerate(fonctions):
    pire = 0
    for x, v in zip(xs[k], res[nom]):
        pire = max(pire, ulps(v, f(float(Q64.valeur(x)))))
    pires[nom] = pire
verifier("bibliothèque mathématique : sinus … arccosinus à moins de 4 ulps du vrai résultat (" +
         ", ".join(f"{n} {p:.2f}" for n, p in pires.items()) + ")", all(p < 4 for p in pires.values()))

# ------------------------------------------------------------------ 8. la machine de référence et la machine Rust s'accordent
progs = []
for nom, src, entrees, _ in V.TESTS:
    progs.append((mots(src), list(entrees)))
progs.append((m2, ent2[:1 + 3 * 20]))
progs[-1] = (m2, [20] + ent2[1:1 + 3 * 20])
progs.append((m3, [15] + ent3[1:1 + 3 * 15]))
progs.append((m5, [6] + ent5[1:1 + 8 * 6]))
rust = lignes_rust(progs)
py = [S.lancer(m, e, 200_000_000) for m, e in progs]
ecarts = [i for i, (a, b) in enumerate(zip(py, rust)) if a != b]
verifier(f"programmes compilés : la machine de référence (Python) et la machine Rust identiques ({len(progs)} programmes)",
         not ecarts and len(rust) == len(py), f"écarts aux programmes {ecarts[:5]}")

print("Tout est conforme." if not mauvais else f"{mauvais} écart(s)")
sys.exit(1 if mauvais else 0)
