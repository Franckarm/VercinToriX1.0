#!/usr/bin/env python3
"""Essai mesuré (expérimental) : des neutrons quaternaires à la place du CRC-8 ?

Un neutron garde 8 bits par mot de 128 bits, soit 4 quits. Il ne répare rien : il désigne le mot abîmé, pour que
l'ombre (Reed-Solomon) répare jusqu'à 4 mots désignés par colonne au lieu de 2 mots cherchés. Ce qui compte : la part
des mots abîmés qu'il voit, selon le genre de l'avarie, et ce qu'il coûte sur Lugus.

Candidats (8 bits chacun) :
  crc8       le CRC-8 d'aujourd'hui (polynôme 0x07, les seize octets, le plus faible d'abord)
  crc8_ordonné  le même polynôme, les bits lus dans le sens des octets (pour une comparaison juste)
  crc_gf4    un CRC quaternaire : le mot lu comme 64 quits, divisé par un générateur de degré 4 sur GF(4)
             (le meilleur des 192 générateurs, choisi ici sur les erreurs d'un et deux quits, puis de deux bits)
  pli_z4     les 64 quits pliés en 4 par l'addition modulo 4 (addm4) : quatre instructions sur Lugus, sans table
  pli_gf4    pli pondéré sur GF(4) : chaque quart de mot multiplié par ω avant d'être ajouté (expérimental)

    python3 chimie/essai_neutrons.py [N]      N tirages par genre au hasard (100 000 par défaut)
"""
import itertools
import random
import sys

M64 = (1 << 64) - 1
M128 = (1 << 128) - 1

# ------------------------------------------------------------------ CRC-8 (comme chimie/adn.py)
T8 = []
for k in range(256):
    c = k
    for _ in range(8):
        c = ((c << 1) ^ 7) & 255 if c & 128 else (c << 1) & 255
    T8.append(c)


def crc8(w):
    c = 0
    for k in range(16):
        c = T8[c ^ ((w >> (8 * k)) & 255)]
    return c


# le même polynôme, les bits lus dans le sens des octets (le plus faible d'abord) : une rafale reste contiguë
T8R = []
for k in range(256):
    c = k
    for _ in range(8):
        c = (c >> 1) ^ 0xE0 if c & 1 else c >> 1
    T8R.append(c)


def crc8_ordonne(w):
    c = 0
    for k in range(16):
        c = T8R[c ^ ((w >> (8 * k)) & 255)]
    return c


# ------------------------------------------------------------------ GF(4) : 0, 1, ω = 2, ω² = 3 ; addition = XOR
def gf4_mul(a, b):
    if a == 0 or b == 0:
        return 0
    lg = {1: 0, 2: 1, 3: 2}
    return [1, 2, 3][(lg[a] + lg[b]) % 3]


def quits(w):
    return [(w >> (2 * i)) & 3 for i in range(64)]


def crc_gf4_avec(gen):
    """gen : les coefficients g3, g2, g1, g0 de x^4 + g3 x^3 + g2 x^2 + g1 x + g0 (sur GF(4)). Le reste de q(x)·x^4."""
    def f(w):
        r = [0, 0, 0, 0]                  # r[0] le coefficient de x^3
        for q in reversed(quits(w)):      # le quit le plus fort d'abord
            t = q ^ r[0]
            r = [r[1] ^ gf4_mul(t, gen[0]), r[2] ^ gf4_mul(t, gen[1]), r[3] ^ gf4_mul(t, gen[2]), gf4_mul(t, gen[3])]
        return r[0] << 6 | r[1] << 4 | r[2] << 2 | r[3]
    return f


# ------------------------------------------------------------------ les plis quaternaires
def addm4(a, b, n):
    """l'addition modulo 4 quit par quit, sur n quits (l'instruction ADDM4 de Lugus)"""
    r = 0
    for i in range(n):
        r |= ((((a >> 2 * i) & 3) + ((b >> 2 * i) & 3)) & 3) << (2 * i)
    return r


def pli_z4(w):
    h, b = w >> 64, w & M64
    x = addm4(h, b, 32)
    x = addm4(x, x >> 32, 16)
    x = addm4(x, x >> 16, 8)
    x = addm4(x, x >> 8, 4)
    return x & 255


def fois_omega(x, n):
    """ω fois chaque quit (GF(4)) : (b1, b0) -> (b1 ^ b0, b1), en une fois sur le mot"""
    hi = (x >> 1) & int("01" * n, 2)
    lo = x & int("01" * n, 2)
    return ((hi ^ lo) << 1) | hi


def pli_gf4(w):
    # Horner sur les quatre quarts de 32 bits : ((q3·ω + q2)·ω + q1)·ω + q0, puis le pli XOR en 4 quits
    m32 = (1 << 32) - 1
    q = [(w >> (32 * k)) & m32 for k in range(4)]
    x = q[3]
    for k in (2, 1, 0):
        x = fois_omega(x, 16) ^ q[k]
    x = x ^ (x >> 16)
    x = (x ^ (x >> 8)) & 255
    return x


# ------------------------------------------------------------------ le choix du générateur GF(4)
def choisir_generateur():
    meilleurs = []
    for g in itertools.product(range(4), repeat=4):
        if g[3] == 0:
            continue
        f = crc_gf4_avec(g)
        # les erreurs d'un quit : toujours vues si g0 != 0 ; deux quits : on compte les manquées
        manque = 0
        for i, j in itertools.combinations(range(64), 2):
            for a in (1, 2, 3):
                for b in (1, 2, 3):
                    if f((a << 2 * i) ^ (b << 2 * j)) == 0:
                        manque += 1
        m2b = sum(1 for i, j in itertools.combinations(range(128), 2) if f((1 << i) ^ (1 << j)) == 0)
        meilleurs.append((manque, m2b, g))
    meilleurs.sort()
    return meilleurs[0]


# ------------------------------------------------------------------ les genres d'erreurs
def erreurs_exhaustives():
    """(nom, liste des masques d'erreur)"""
    un_bit = [1 << i for i in range(128)]
    deux_bits = [(1 << i) | (1 << j) for i, j in itertools.combinations(range(128), 2)]
    un_quit = [a << 2 * i for i in range(64) for a in (1, 2, 3)]
    rafales = []
    for L in range(3, 9):          # une rafale de L bits : les deux bouts changés, l'intérieur au choix
        for p in range(0, 129 - L):
            for mid in range(1 << (L - 2)):
                rafales.append((1 << p) | (mid << (p + 1)) | (1 << (p + L - 1)))
    return [("un bit (128)", un_bit), ("deux bits (8 128)", deux_bits), ("un quit (192)", un_quit),
            (f"rafale de 3 à 8 bits ({len(rafales)})", rafales)]


def erreurs_au_hasard(g, n):
    def k_bits(k):
        return lambda: sum(1 << i for i in g.sample(range(128), k))

    def deux_quits():
        i, j = g.sample(range(64), 2)
        return (g.randint(1, 3) << 2 * i) | (g.randint(1, 3) << 2 * j)

    def octet():
        return g.randint(1, 255) << (8 * g.randrange(16))

    def mot():
        return g.randint(1, M128)
    return [("trois bits", k_bits(3)), ("quatre bits", k_bits(4)), ("huit bits épars", k_bits(8)),
            ("deux quits", deux_quits), ("un octet remplacé", octet), ("le mot remplacé", mot)]


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100_000
    manque, m2b, gen = choisir_generateur()
    print(f"générateur GF(4) choisi : x^4 + {gen[0]}x^3 + {gen[1]}x^2 + {gen[2]}x + {gen[3]} "
          f"(ω = 2, ω² = 3) ; deux quits manqués : {manque}, deux bits manqués : {m2b}")
    cand = [("crc8", crc8), ("crc8_ordonné", crc8_ordonne), ("crc_gf4", crc_gf4_avec(gen)), ("pli_z4", pli_z4), ("pli_gf4", pli_gf4)]
    g = random.Random(20261103)
    print(f"\n{'genre':34s}" + "".join(f"{c:>14s}" for c, _ in cand) + "     (part des erreurs vues)")
    for nom, masques in erreurs_exhaustives():
        mots = [g.randint(0, M128) for _ in masques]
        lignes = []
        for _, f in cand:
            # vue : le neutron du mot abîmé diffère de celui du mot (le pli z4 n'est pas linéaire sur GF(2) : le
            # mot compte, à cause de la retenue dans le quit ; un mot au hasard par erreur)
            vues = sum(1 for w, e in zip(mots, masques) if f(w) != f(w ^ e))
            lignes.append(f"{100 * vues / len(masques):13.3f}%")
        print(f"{nom:34s}" + "".join(lignes))
    for nom, tirer in erreurs_au_hasard(g, n):
        es = [(g.randint(0, M128), tirer()) for _ in range(n)]
        lignes = [f"{100 * sum(1 for w, e in es if f(w) != f(w ^ e)) / n:13.3f}%" for _, f in cand]
        print(f"{nom + f' ({n})':34s}" + "".join(lignes))
    print("\n(au hasard, l'idéal pour 8 bits est 99,609 % : une chance sur 256 de tomber juste)")


if __name__ == "__main__":
    main()
