#!/usr/bin/env python3
"""Essai mesuré (expérimental) : la signature d'une molécule par ses vibrations, et la parade aux isospectraux.

Le spectre d'une molécule (les fréquences de ses modes de vibration) ne dépend pas de la façon dont on numérote ses
atomes : c'est une empreinte. Mais deux molécules différentes peuvent avoir le même spectre (isospectrales). La parade
(idée de l'utilisateur : un atome se retrouve d'un code à l'autre ; une vibration commune fait une accroche ; la
vibration totale garde l'intégrité de chaque groupe de blocs) :

  - la vibration locale d'un atome : ses chemins fermés de longueur 1 à n, (A^k)_ii, sa part dans chaque mode pondérée
    par la fréquence du mode ; en entiers, donc la même dans tous les compilateurs ;
  - son élément (sa masse : C 12, H 1, O 16, N 14) ;
  - la vibration se propage le long des liaisons : à chaque tour, un atome prend la vibration de ses voisins (un
    mélange d'entiers, splitmix64) ;
  - la signature : l'ensemble trié des vibrations finales, et leur total (la vibration totale) ;
  - l'accroche de deux molécules : les vibrations locales qu'elles ont en commun.

Mesuré sur tous les graphes de 1 à 7 sommets (les 1 253 sans doublon), sans éléments puis avec des éléments tirés au
hasard ; une collision est une paire de molécules différentes (non isomorphes) qui ont la même signature.

    python3 chimie/essai_vibrations.py
"""
import itertools
import random

import networkx as nx
import numpy as np

M64 = (1 << 64) - 1
MASSE = {"C": 12, "H": 1, "O": 16, "N": 14}


def brasser(z):
    z = (z + 0x9E3779B97F4A7C15) & M64
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & M64
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & M64
    return z ^ (z >> 31)


def melanger(*xs):
    h = 0
    for x in xs:
        h = brasser(h ^ (x & M64))
    return h


def collisions(graphes, signature, meme):
    """les paires de graphes différents (meme(a, b) faux) qui ont la même signature"""
    groupes = {}
    for g in graphes:
        groupes.setdefault(signature(g), []).append(g)
    n = 0
    for gs in groupes.values():
        for a, b in itertools.combinations(gs, 2):
            if not meme(a, b):
                n += 1
    return n


def spectre(g):
    """le spectre ordinaire (les valeurs propres de la matrice d'adjacence, arrondies)"""
    if g.number_of_nodes() == 0:
        return ()
    a = nx.to_numpy_array(g, nodelist=sorted(g.nodes()))
    return tuple(np.round(np.sort(np.linalg.eigvalsh(a)), 6)) + (g.number_of_nodes(),)


def spectre_masse(g):
    """le spectre des vibrations avec les masses : M^-1/2 L M^-1/2 (le laplacien est la raideur des liaisons)"""
    if g.number_of_nodes() == 0:
        return ()
    ns = sorted(g.nodes())
    lap = nx.laplacian_matrix(g, nodelist=ns).toarray().astype(float)
    m = np.array([MASSE[g.nodes[v].get("el", "C")] for v in ns], dtype=float) ** -0.5
    return tuple(np.round(np.sort(np.linalg.eigvalsh(m[:, None] * lap * m[None, :])), 6)) + (len(ns),)


def vibrations_locales(g):
    """(A^k)_ii pour k = 1..n, en entiers : la vibration locale de chaque atome"""
    ns = sorted(g.nodes())
    n = len(ns)
    idx = {v: i for i, v in enumerate(ns)}
    a = [[0] * n for _ in range(n)]
    for u, v in g.edges():
        a[idx[u]][idx[v]] = a[idx[v]][idx[u]] = 1
    p = [[int(i == j) for j in range(n)] for i in range(n)]
    loc = {v: [] for v in ns}
    for _ in range(max(n, 1)):
        p = [[sum(p[i][k] * a[k][j] for k in range(n)) for j in range(n)] for i in range(n)]
        for v in ns:
            loc[v].append(p[idx[v]][idx[v]])
    return loc


def signature_vibrations(g, tours=3, avec_element=False):
    """la parade : la vibration locale (et l'élément), propagée le long des liaisons ; l'ensemble trié et le total"""
    loc = vibrations_locales(g)
    lab = {v: melanger(len(loc[v]), *loc[v], MASSE[g.nodes[v].get("el", "C")] if avec_element else 0) for v in g}
    for _ in range(tours):
        lab = {v: melanger(lab[v], *sorted(lab[u] for u in g.neighbors(v))) for v in g}
    finale = tuple(sorted(lab.values()))
    return finale + (sum(finale) & M64, g.number_of_nodes(), g.number_of_edges())


def main():
    tous = [g for g in nx.graph_atlas_g() if g.number_of_nodes() > 0]
    iso = nx.is_isomorphic
    print(f"{len(tous)} molécules (tous les graphes de 1 à 7 sommets, sans doublon)\n")
    print("sans éléments : paires de molécules différentes qui ont la même signature")
    print(f"  le spectre ordinaire (adjacence)                  {collisions(tous, spectre, iso):6d}")
    print(f"  les vibrations (laplacien, masses égales)         {collisions(tous, spectre_masse, iso):6d}")
    print(f"  les vibrations locales seules (0 tour)            {collisions(tous, lambda g: signature_vibrations(g, 0), iso):6d}")
    print(f"  la parade : locales, propagées (3 tours)          {collisions(tous, signature_vibrations, iso):6d}")

    # avec des éléments : chaque graphe en trois molécules aux éléments tirés au hasard
    rnd = random.Random(20261104)
    mols = []
    for g in tous:
        for _ in range(3):
            h = g.copy()
            for v in h:
                h.nodes[v]["el"] = rnd.choice("CHON")
            mols.append(h)

    def iso_el(a, b):
        return nx.is_isomorphic(a, b, node_match=lambda x, y: x["el"] == y["el"])
    print(f"\navec des éléments ({len(mols)} molécules) :")
    print(f"  les vibrations avec les masses (spectre)          {collisions(mols, spectre_masse, iso_el):6d}")
    print(f"  la parade avec les éléments (3 tours)             "
          f"{collisions(mols, lambda g: signature_vibrations(g, 3, True), iso_el):6d}")

    # l'intégrité : une liaison ajoutée, retirée ou déplacée change-t-elle la signature ?
    vues = total = 0
    for g in mols[::7]:
        if g.number_of_nodes() < 3:
            continue
        s0 = signature_vibrations(g, 3, True)
        for _ in range(4):
            h = g.copy()
            u, v = rnd.sample(sorted(h.nodes()), 2)
            if h.has_edge(u, v):
                h.remove_edge(u, v)
            else:
                h.add_edge(u, v)
            total += 1
            vues += signature_vibrations(h, 3, True) != s0 or iso_el(g, h)
    print(f"\nl'intégrité : une liaison changée, vue par la signature : {vues}/{total}")

    # l'accroche : deux molécules qui partagent un groupe (le même fragment greffé sur deux corps différents)
    def vibrations_finales(g, tours=2):
        loc = vibrations_locales(g)
        lab = {v: melanger(len(loc[v]), MASSE[g.nodes[v]["el"]]) for v in g}
        for _ in range(tours):
            lab = {v: melanger(lab[v], *sorted(lab[u] for u in g.neighbors(v))) for v in g}
        return lab
    fragment = nx.Graph([(0, 1), (1, 2), (2, 3), (3, 0), (1, 4)])
    for v, e in zip(range(5), "COCNH"):
        fragment.nodes[v]["el"] = e
    accroches, sans = [], []
    for k in range(40):
        def corps():
            c = nx.gnm_random_graph(8, 10, seed=rnd.randrange(1 << 30))
            for v in c:
                c.nodes[v]["el"] = rnd.choice("CHON")
            return c
        a, b = corps(), corps()
        a2 = nx.disjoint_union(a, fragment)
        a2.add_edge(0, 8)
        b2 = nx.disjoint_union(b, fragment)
        b2.add_edge(0, 8)
        la, lb = vibrations_finales(a2), vibrations_finales(b2)
        communs = len(set(la.values()) & set(lb.values()))
        accroches.append(communs)
        sans.append(len(set(vibrations_finales(a).values()) & set(vibrations_finales(b).values())))
    print(f"l'accroche : deux codes qui partagent un groupe de 5 atomes : {sum(accroches) / 40:.1f} vibrations communes "
          f"en moyenne ; sans le groupe : {sum(sans) / 40:.1f}")

    # la limite connue : deux graphes fortement réguliers de mêmes paramètres (16 sommets, degré 6) : la tour 4×4 et
    # le graphe de Shrikhande ; chaque sommet y vibre exactement de la même façon
    tour = nx.cartesian_product(nx.complete_graph(4), nx.complete_graph(4))
    tour = nx.convert_node_labels_to_integers(tour)
    shri = nx.Graph()
    for x, y in itertools.product(range(4), range(4)):
        for dx, dy in ((1, 0), (0, 1), (1, 1)):
            shri.add_edge(4 * x + y, 4 * ((x + dx) % 4) + (y + dy) % 4)
    meme_sig = signature_vibrations(tour, 3) == signature_vibrations(shri, 3)
    print(f"\nla limite connue (la tour 4×4 et le graphe de Shrikhande, non isomorphes) : même signature : "
          f"{'oui' if meme_sig else 'non'} ; mêmes vibrations locales : "
          f"{'oui' if sorted(map(tuple, vibrations_locales(tour).values())) == sorted(map(tuple, vibrations_locales(shri).values())) else 'non'}")
    # la parade de la parade : compter les groupes de quatre atomes tous liés (la tour en a, Shrikhande non)
    def k4(g):
        return sum(1 for c in nx.enumerate_all_cliques(g) if len(c) == 4)
    print(f"  ce qui les sépare : les groupes de quatre atomes tous liés : {k4(tour)} contre {k4(shri)}")


if __name__ == "__main__":
    main()
