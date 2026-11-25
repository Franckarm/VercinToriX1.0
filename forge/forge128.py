#!/usr/bin/env python3
"""La forge de Lugus : un programme vtx (le langage de Lugus : flottant de 128 bits par défaut, point de matière) devient
un programme Rust, que rustc (LLVM) change en exécutable natif.

Comme la forge du SPU-32 (forge/forge.py), elle part de l'arbre du programme tel que vtx128.py le lit et le type :
chaque fonction vtx devient une fonction Rust, chaque variable une variable Rust. Autour du programme, la machine
elle-même : spu128.rs de vtx-rs (la mémoire de Lugus, ses pages, le brin, les cubes sur disque, les canaux et les
services), recopié tel quel. Chaque opération garde le sens qu'elle a sur Lugus : un mot a 128 bits ; une opération
entière se fait à la largeur 64 (l'entier par défaut) ou 32 (entier_32) comme l'instruction de Lugus à la largeur
w = 1 ou 2, et les mots lus en mémoire gardent leurs 128 bits tant qu'aucune opération ne les ramène à 64.

Les flottants quaternaires (de 32, 64 et 128 bits) n'existent pas dans le processeur hôte : ils sont calculés par
qflot128.rs, la même arithmétique exacte que la machine Rust de Lugus (arrondi au plus proche, quatre états).

Le ramasse-miettes du prélude cherche les références vivantes dans la pile de Lugus : une fonction forgée qui peut,
de près ou de loin, ramasser les miettes a donc un cadre dans cette pile, où ses variables sont recopiées avant chaque
appel qui peut ramasser (comme la forge du SPU-32).

Utilisation : python3 forge/forge128.py PROG.vtx [-o EXE] [--rs FICHIER.rs] [--natif]
L'exécutable prend les entrées du programme sur sa ligne de commande ; avec FORGE_LIGNE=1 dans l'environnement, il
écrit la ligne du corpus de Lugus (sorties, mémoire, brin, texte) au lieu des sorties."""
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, racine)
import vtx128 as V  # noqa: E402
sys.path.insert(0, os.path.join(racine, "taranis"))
import noyau_vtx  # noqa: E402
from vtx128 import VtxError, est_ref, ligne_de, INTEGRES, OPS_LOGIQUES, SURCHARGES, NOM_TYPE, CHAMPS  # noqa: E402

MARQUE = "/*R*/"          # dans le code d'une expression : un appel qui peut ramasser les miettes
SIMPLE = re.compile(r"^(v_\w+|t\d+|\d+u128)$")
M64 = (1 << 64) - 1
M32 = (1 << 32) - 1
# les formats des flottants (qflot128.rs) et leur masque
FMT = {"f": "Q64", "s": "Q32", "x": "Q128"}
OP_RS = {"==": "==", "!=": "!=", "<": "<", "<=": "<=", ">": ">", ">=": ">="}


def L():
    """0.833 : l'entier par défaut du programme forgé a 128 bits (Lugus) ; 64 avec « dunon; »"""
    return V.ENTIER_LARGE


def esus_diviser(op, c):
    """0.835 : Ésus (le bûcheron, qui taille l'arbre) : la division ou le reste d'un entier de 128 bits par une
    constante c, sans division : un décalage pour une puissance de deux, sinon la multiplication de Granlund et
    Montgomery (1994, figure 4.1) : l = le nombre de bits de c, m = floor(2^128 (2^l - c) / c) + 1 ; q = (t + (n - t) / 2)
    >> (l - 1), t = les 128 bits hauts de m n. Exact pour tout n (vérifié par tests/test_esus.py)."""
    if c == 1:
        return "{0}" if op == "/" else "(({0}) & 0)"
    if c & (c - 1) == 0:
        k = c.bit_length() - 1
        return f"({{0}} >> {k})" if op == "/" else f"({{0}} & {c - 1}u128)"
    l = c.bit_length()
    m = ((1 << 128) * ((1 << l) - c)) // c + 1
    if op == "/":
        return f"divk128({{0}}, {m}u128, {l})"
    return f"modk128({{0}}, {m}u128, {l}, {c}u128)"


ESUS_VARIABLES = [None]   # 0.835 : les quatre points d'une variable de la fonction en cours (posé par fonction_rs)
ESUS_RELEVE = [[]]        # 0.835 : les quatre points de chaque variable entière du programme forgé (le fichier .esus)
DRUIDE_OBS = [[]]         # 0.836 : les variables observées (VTX_DRUIDE=poids) : (molécule, variable), leur rang dans OBS
DRUIDE_NOMS = [[]]        # 0.835 : les molécules comptées (VTX_DRUIDE=poids à la forge) : leur rang dans POIDS
DEPLIER = [{}]            # 0.837 : l'ARN du Druide, l'arrangement : molécule -> 1 (dépliée) ou 0 (à part)
ESUS_ETEINT = [set()]     # 0.835 : les molécules où l'ARN du Druide déconnecte Ésus (PROG.arn : « esus MOL 0 »)
ESUS_ICI = [True]         # 0.835 : Ésus est-il connecté dans la molécule en cours de forge ?
G128 = (1 << 128) - 1
SMIN, SMAX = -(1 << 127), (1 << 127) - 1
# 0.836 : six points : les quatre (le plus bas, le plus haut sans signe, les bits sûrs à 0, à 1), puis le plus petit et
# le plus grand lus avec le signe (les valeurs négatives : 0 - 5 vaut -5, pas 2^128 - 5)
INCONNU4 = (0, G128, 0, 0, SMIN, SMAX)   # rien de prouvé


def signe_de(b, h):
    """0.836 : l'intervalle signé que donne un intervalle sans signe (le mot de 128 bits lu en complément à deux)"""
    if h <= SMAX:
        return b, h
    if b > SMAX:
        return b - (1 << 128), h - (1 << 128)
    return SMIN, SMAX


def esus_six(b, h, z, o, sb=SMIN, sh=SMAX):
    """0.836 : les six points accordés : le signé croisé avec ce que dit le sans signe, et le sans signe resserré par le
    signé (un intervalle signé tout positif, ou tout négatif, borne aussi le sans signe)"""
    db, dh = signe_de(b, h)
    sb, sh = max(sb, db), min(sh, dh)
    if sb > sh:
        sb, sh = db, dh
    if sb >= 0:
        b, h = max(b, sb), min(h, sh)
    elif sh < 0:
        b, h = max(b, sb + (1 << 128)), min(h, sh + (1 << 128))
    if b > h:
        return INCONNU4
    z, o = esus_haut(h, z, o)
    return b, h, z, o, sb, sh


def sdans(a, b):
    return SMIN <= a and b <= SMAX


def esus_haut(h, z, o):
    """les bits au-dessus du plus haut sont sûrement à 0"""
    return z | (G128 ^ ((1 << h.bit_length()) - 1)), o


MEMBRANE = [{}]   # 0.837 : la membrane des cellules : molécule -> ({paramètre: six points}, six points du retour)
BAS6 = (G128, 0, G128, G128, SMAX, SMIN)   # rien encore : pas une seule valeur


def joindre6(a, b):
    return (min(a[0], b[0]), max(a[1], b[1]), a[2] & b[2], a[3] & b[3], min(a[4], b[4]), max(a[5], b[5]))


def dans6(a, b):
    """a ⊆ b : six points de a tenus par ceux de b"""
    return (a[0] >= b[0] and a[1] <= b[1] and (a[2] & b[2]) == b[2] and (a[3] & b[3]) == b[3]
            and a[4] >= b[4] and a[5] <= b[5])


def elargir6(h, j):
    """après le premier tour : le haut au nombre de bits, le bas à 0 s'il bouge encore ; en signé de même (pour finir)"""
    if j[0] > j[1]:
        return j
    hh = (1 << j[1].bit_length()) - 1
    sh = j[5] if j[5] <= h[5] else min(SMAX, (1 << j[5].bit_length()) - 1)
    sb = j[4] if j[4] >= h[4] else max(SMIN, -(1 << (-j[4]).bit_length()) if j[4] < 0 else 0)
    return (0 if j[0] < h[0] else j[0], hh) + esus_haut(hh, j[2], j[3]) + (sb, sh)


def sans_lignes(x):
    """0.838 : un arbre sans ses numéros de ligne (le dernier entier d'un nœud, sauf d'un nombre) : déplacer une molécule
    dans son fichier ne change pas son empreinte (au pire, deux molécules presque pareilles se confondent : la cellule
    n'apporte que des choix sans risque, Ésus exact et le dépliage, jamais un résultat)"""
    if isinstance(x, list):
        return [sans_lignes(y) for y in x]
    if isinstance(x, tuple):
        if x and x[0] != "nombre" and len(x) > 2 and isinstance(x[-1], int) and not isinstance(x[-1], bool):
            x = x[:-1]
        return tuple(sans_lignes(y) for y in x)
    return x


def membrane(fonctions):
    """0.837 : la membrane des cellules. Une molécule appelée seulement par des appels visibles (jamais passée en valeur,
    jamais du prélude, pas principal) reçoit sur ses paramètres entiers ce que ses appelants y mettent (les six points
    joints sur tous les appels) ; toute molécule du programme rend par son retour ce que ses retours prouvent (0 compris,
    si elle finit sans retour). Le tout tourne jusqu'à tenir (élargi après le premier tour) ; s'il ne tient pas, rien."""
    MEMBRANE[0] = {}
    CELLULES[0] = {}
    user = {f.nom: f for f in fonctions if getattr(f, "origine", "") != "prélude"}
    refs, nappels = set(), {n: 0 for n in user}

    def scan(x):
        if isinstance(x, list):
            for y in x:
                scan(y)
            return
        if not isinstance(x, tuple) or not x:
            return
        if x[0] in ("fref", "appelv") and len(x) > 1 and isinstance(x[1], str):
            refs.add(x[1])
        if x[0] == "appel" and len(x) > 2 and isinstance(x[1], str) and x[1] in nappels:
            nappels[x[1]] += 1
        for y in (x[1:] if isinstance(x[0], str) else x):
            if isinstance(y, (list, tuple)):
                scan(y)
    for f in fonctions:
        scan(f.corps)
    ouverts = {n for n in user if n not in refs and nappels[n] > 0 and n != "principal"}
    graphe = {n: set() for n in user}

    def appels_de(x, n):
        if isinstance(x, list):
            for y in x:
                appels_de(y, n)
            return
        if not isinstance(x, tuple) or not x:
            return
        if x[0] == "appel" and len(x) > 1 and isinstance(x[1], str) and x[1] in user:
            graphe[n].add(x[1])
        for y in (x[1:] if isinstance(x[0], str) else x):
            if isinstance(y, (list, tuple)):
                appels_de(y, n)
    for n, f in user.items():
        appels_de(f.corps, n)
    # 0.838 : l'empreinte de chaque molécule (son arbre, sans les numéros de ligne) et de chaque cellule (elle et
    # celles qu'elle appelle, de proche en proche) : la même cellule se reconnaît d'un programme à l'autre
    emp_m = {n: hashlib.sha256(repr(sans_lignes(f.corps)).encode("utf-8") + repr((f.params, f.ptypes, f.rtype)).encode("utf-8"))
             .hexdigest()[:16] for n, f in user.items()}

    def fermeture(n, vus):
        if n in vus:
            return
        vus.add(n)
        for a in graphe.get(n, ()):
            fermeture(a, vus)
    emp_c = {}
    for n in user:
        vus = set()
        fermeture(n, vus)
        emp_c[n] = hashlib.sha256(" ".join(sorted(m + ":" + emp_m[m] for m in vus)).encode("utf-8")).hexdigest()[:16]
    CELLULES[0] = {n: (False, graphe[n], emp_c[n]) for n in user}
    if not L() or os.environ.get("VTX_MEMBRANE") == "0" or os.environ.get("VTX_ESUS") == "0":
        return
    hyp = {n: ({p: (BAS6 if n in ouverts and t == "e" else INCONNU4) for p, t in zip(f.params, f.ptypes)},
               BAS6 if f.rtype == "e" else INCONNU4) for n, f in user.items()}
    sauve = ESUS_VARIABLES[0]
    tient = False
    for tour in range(60):
        MEMBRANE[0] = hyp
        neuf = {n: ({p: BAS6 for p in f.params}, BAS6) for n, f in user.items()}

        def marcher(x):
            if isinstance(x, list):
                for y in x:
                    marcher(y)
                return
            if not isinstance(x, tuple) or not x:
                return
            if x[0] == "appel" and len(x) > 2 and isinstance(x[1], str) and x[1] in ouverts and isinstance(x[2], list):
                g = user[x[1]]
                if len(x[2]) != len(g.params):
                    ouverts.discard(x[1])
                else:
                    for pnom, a in zip(g.params, x[2]):
                        neuf[x[1]][0][pnom] = joindre6(neuf[x[1]][0][pnom], points(a))
            if x[0] == "retour" and len(x) > 1 and CELLULE[0] in neuf:
                pr, r = neuf[CELLULE[0]]
                neuf[CELLULE[0]] = (pr, joindre6(r, (0, 0, G128, 0, 0, 0) if x[1] is None else points(x[1])))
            for y in (x[1:] if isinstance(x[0], str) else x):
                if isinstance(y, (list, tuple)):
                    marcher(y)
        for f in user.values():
            CELLULE[0] = f.nom
            ESUS_VARIABLES[0] = esus_definitions(f.corps, f.params, f.nom)
            marcher(f.corps)
            pr, r = neuf[f.nom]
            neuf[f.nom] = (pr, joindre6(r, (0, 0, G128, 0, 0, 0)))   # finir sans retour : 0
        # ce qui ne s'ouvre pas : tout l'intervalle
        for n, f in user.items():
            for p, t in zip(f.params, f.ptypes):
                if n not in ouverts or t != "e":
                    neuf[n][0][p] = INCONNU4
            if f.rtype != "e":
                neuf[n] = (neuf[n][0], INCONNU4)
        if tour > 0 and all(dans6(neuf[n][1], hyp[n][1]) and all(dans6(neuf[n][0][p], hyp[n][0][p]) for p in neuf[n][0])
                            for n in user):
            tient = True
            break
        nh = {}

        def suivant(h, nv):
            # ce qui bouge encore après huit tours devient tout l'intervalle (sûr, et la membrane finit par tenir)
            if dans6(nv, h):
                return h
            if tour >= 8:
                return INCONNU4
            j = joindre6(h, nv)
            return elargir6(h, j) if tour > 0 else j
        for n in user:
            pr = {p: suivant(hyp[n][0][p], neuf[n][0][p]) for p in neuf[n][0]}
            nh[n] = (pr, suivant(hyp[n][1], neuf[n][1]))
        hyp = nh
    ESUS_VARIABLES[0] = sauve
    CELLULE[0] = None
    if tient:
        # ce qui reste vide (jamais atteint) : tout l'intervalle, par prudence
        for n in hyp:
            pr, r = hyp[n]
            hyp[n] = ({p: (INCONNU4 if v[0] > v[1] else v) for p, v in pr.items()}, INCONNU4 if r[0] > r[1] else r)
    MEMBRANE[0] = hyp if tient else {}
    CELLULES[0] = {n: (n in ouverts and tient, graphe[n], emp_c[n]) for n in user}


CELLULE = [None]   # 0.837 : la molécule dont la membrane se calcule


def esus_definitions(corps, params, nom_f=None):
    """0.835 : Ésus : chaque affectation d'une variable dans la fonction (où qu'elle soit : sous un si, une boucle…) ;
    rend la fonction nom -> ses quatre points (le plus bas, le plus haut, les bits sûrement à 0, sûrement à 1),
    prudente : un paramètre, une définition qu'Ésus ne lit pas, ou une variable qui dépend d'elle-même : rien de
    prouvé (INCONNU4)."""
    defs, inconnues = {}, set(params)
    # 0.837 : la membrane : un paramètre reçoit ce que ses appelants y mettent
    mb = MEMBRANE[0].get(nom_f) if nom_f else None
    if mb:
        for p in params:
            if p in mb[0] and mb[0][p] != INCONNU4:
                inconnues.discard(p)
                defs.setdefault(p, []).append(("fixe", mb[0][p]))

    def parcourir(x):
        if isinstance(x, list):
            for y in x:
                parcourir(y)
            return
        if not isinstance(x, tuple) or not x:
            return
        g = x[0]
        if g in ("soit", "affecter") and len(x) > 2 and isinstance(x[1], str):
            defs.setdefault(x[1], []).append(("expr", x[2]))
        elif g == "pour" and len(x) > 4 and isinstance(x[1], str):
            pas = x[6] if len(x) > 6 and isinstance(x[6], int) else None
            defs.setdefault(x[1], []).append(("pour", x[2], x[3], pas))
        elif isinstance(g, str) and len(x) > 1 and isinstance(x[1], str) and g not in ("var", "appel", "nombre", "bin",
                                                                                     "texte", "champ", "tnombre"):
            inconnues.add(x[1])   # une autre façon d'écrire une variable (pour … dans, selon…) : Ésus ne la lit pas
        for y in (x[1:] if isinstance(x[0], str) else x):
            if isinstance(y, (list, tuple)):
                parcourir(y)

    parcourir(corps)
    vues, en_cours, hyp = {}, {}, {}
    lu_hyp = [0]   # combien de fois une hypothèse a été lue (un résultat qui en dépend ne se garde pas)
    BAS = (G128, 0, G128, G128, SMAX, SMIN)   # rien encore : pas une seule valeur

    def calculer(nom):
        bas, haut, z, o, sb, sh = BAS
        for d in defs[nom]:
            if d[0] == "fixe":
                b2, h2, z2, o2, sb2, sh2 = d[1]
            elif d[0] == "expr":
                b2, h2, z2, o2, sb2, sh2 = points(d[1])
            else:
                _, a, fin, pas = d
                if pas is None or pas < 1:
                    b2, h2, z2, o2, sb2, sh2 = INCONNU4
                else:
                    pa, pf = points(a), points(fin)
                    if pa[0] > pa[1] or pf[0] > pf[1]:
                        continue   # rien encore
                    b2, h2 = pa[0], min(G128, max(pa[1], pf[1] + pas))
                    z2, o2 = esus_haut(h2, 0, 0)
                    sb2, sh2 = signe_de(b2, h2)
            bas, haut, z, o, sb, sh = min(bas, b2), max(haut, h2), z & z2, o & o2, min(sb, sb2), max(sh, sh2)
        return bas, haut, z, o, sb, sh

    def dedans(a, b):
        # a ⊆ b : l'intervalle de a dans celui de b, et b ne sait pas plus de bits que a
        return (a[0] >= b[0] and a[1] <= b[1] and (a[2] & b[2]) == b[2] and (a[3] & b[3]) == b[3]
                and a[4] >= b[4] and a[5] <= b[5])

    def pv(nom):
        if nom in vues:
            return vues[nom]
        if nom in inconnues or nom not in defs:
            return INCONNU4
        if nom in en_cours:
            # 0.835 : une variable qui dépend d'elle-même (s = s ^ x…) : son hypothèse du moment
            lu_hyp[0] += 1
            return hyp.get(nom, BAS)
        avant_lu = lu_hyp[0]
        en_cours[nom] = True
        hyp[nom] = BAS
        r = INCONNU4
        for tour in range(140):
            res = calculer(nom)
            if tour > 0 and dedans(res, hyp[nom]):
                r = hyp[nom]   # la borne tient d'un tour à l'autre : elle est prouvée
                break
            h = hyp[nom]
            j = (min(h[0], res[0]), max(h[1], res[1]), h[2] & res[2], h[3] & res[3], min(h[4], res[4]),
                 max(h[5], res[5]))
            if tour > 0:
                # élargir : le haut au nombre de bits, le bas à 0 s'il bouge encore (pour finir à coup sûr) ; en signé,
                # de même vers le haut et vers le bas (une puissance de deux de plus)
                hh = (1 << j[1].bit_length()) - 1
                sh = j[5] if j[5] <= h[5] else min(SMAX, (1 << j[5].bit_length()) - 1)
                sb = j[4] if j[4] >= h[4] else max(SMIN, -(1 << (-j[4]).bit_length()) if j[4] < 0 else 0)
                j = (0 if j[0] < h[0] else j[0], hh) + esus_haut(hh, j[2], j[3]) + (sb, sh)
            hyp[nom] = j
            if lu_hyp[0] == avant_lu:
                r = res   # elle ne dépend pas d'elle-même : le premier calcul suffit
                break
        del en_cours[nom]
        hyp.pop(nom, None)
        if lu_hyp[0] == avant_lu or not en_cours:
            vues[nom] = r   # ne garder que ce qui ne dépend pas de l'hypothèse d'une autre variable
        return r
    return pv


def points(e):
    """0.835 : Ésus : les points de l'entier e (sur 128 bits) que l'arbre prouve : le plus bas, le plus haut, les bits
    sûrement à 0, les bits sûrement à 1 ; 0.836 : et le plus petit, le plus grand lus avec le signe. Bit à bit, c'est
    Belnap : à 0 et à 1 à la fois serait un chemin qui se contredit (jamais atteint) ; ni l'un ni l'autre, inconnu."""
    r = points_bruts(e)
    if r is INCONNU4 or r[0] > r[1]:
        return r   # 0.837 : vide (pas encore une seule valeur, pendant qu'une borne se cherche) : il reste vide
    return esus_six(*r)


def points_bruts(e):
    G = G128
    if not isinstance(e, tuple) or not e:
        return INCONNU4
    if e[0] == "nombre" and isinstance(e[1], int):
        v = e[1] & G
        sv = v - (1 << 128) if v > SMAX else v
        return v, v, G ^ v, v, sv, sv
    if e[0] == "var" and len(e) > 1 and ESUS_VARIABLES[0] is not None:
        return ESUS_VARIABLES[0](e[1])
    if e[0] == "appel" and len(e) > 1 and isinstance(e[1], str) and e[1] in MEMBRANE[0]:
        return MEMBRANE[0][e[1]][1]   # 0.837 : ce que la molécule rend, prouvé par ses retours
    if e[0] != "bin" or len(e) < 4:
        return INCONNU4
    op = e[1]
    if op in V.COMPARAISONS or op in V.SIGNEES_COMP or op in ("&&", "||"):
        return 0, 1, G ^ 1, 0, 0, 1
    pa6, pb6 = points(e[2]), points(e[3])
    if pa6[0] > pa6[1] or pb6[0] > pb6[1]:
        return BAS6   # 0.837 : une opération sur rien encore : rien encore
    ba, ha, za, oa, sa0, sa1 = pa6
    bb, hb, zb, ob, sb0, sb1 = pb6
    k = e[3][1] if e[3][0] == "nombre" else None
    if op == "&":
        h = min(ha, hb)
        return (0, h) + esus_haut(h, za | zb, oa & ob)
    if op == "|":
        h = (1 << max(ha.bit_length(), hb.bit_length())) - 1
        return (max(ba, bb), h) + esus_haut(h, za & zb, oa | ob)
    if op == "^":
        h = (1 << max(ha.bit_length(), hb.bit_length())) - 1
        return (0, h) + esus_haut(h, (za & zb) | (oa & ob), (za & ob) | (oa & zb))
    if op == ">>" and k is not None:
        k = min(k, 127)
        return ba >> k, ha >> k, (za >> k) | (G ^ (G >> k)), oa >> k
    if op == ".>>" and k is not None and k < 128:
        # le décalage signé : l'arrondi vers le bas, comme >> de Python sur un entier signé
        return (0, G, 0, 0, sa0 >> k, sa1 >> k)
    if op == "<<" and k is not None and k < 128:
        zb_ = ((za << k) | ((1 << k) - 1)) & G
        if (ha << k) <= G:
            return ba << k, ha << k, zb_, (oa << k) & G
        return 0, G, zb_, (oa << k) & G
    if op == "%" and k is not None and k > 0:
        if ha < k:
            return ba, ha, za, oa
        h = k - 1
        return (0, h) + esus_haut(h, 0, 0)
    if op == "/" and k is not None and k > 0:
        h = ha // k
        return (ba // k, h) + esus_haut(h, 0, 0)
    if op in ("./", ".%") and k is not None:
        ks = k - (1 << 128) if k > SMAX else k
        if ks == 0 or (ks == -1 and sa0 == SMIN):
            return INCONNU4
        if op == "./":
            q = sorted((abs(x) // abs(ks)) * (1 if (x < 0) == (ks < 0) else -1) for x in (sa0, sa1))
            return (0, G, 0, 0, q[0], q[1])
        m = abs(ks) - 1   # le reste a le signe du dividende (comme Rust et le C)
        return (0, G, 0, 0, -m if sa0 < 0 else 0, m if sa1 > 0 else 0)
    if op == "+":
        s0, s1 = sa0 + sb0, sa1 + sb1
        s0, s1 = (s0, s1) if sdans(s0, s1) else (SMIN, SMAX)
        if ha + hb <= G:
            h = ha + hb
            return (ba + bb, h) + esus_haut(h, 0, 0) + (s0, s1)
        return (0, G, 0, 0, s0, s1)
    if op == "-":
        # 0.836 : la soustraction : sans signe, juste si elle ne passe pas sous 0 ; en signé, les écarts extrêmes
        s0, s1 = sa0 - sb1, sa1 - sb0
        s0, s1 = (s0, s1) if sdans(s0, s1) else (SMIN, SMAX)
        if ba >= hb:
            h = ha - bb
            return (ba - hb, h) + esus_haut(h, 0, 0) + (s0, s1)
        return (0, G, 0, 0, s0, s1)
    if op == "*":
        c = [x * y for x in (sa0, sa1) for y in (sb0, sb1)]
        s0, s1 = (min(c), max(c)) if sdans(min(c), max(c)) else (SMIN, SMAX)
        if ha * hb <= G:
            h = ha * hb
            return (ba * bb, h) + esus_haut(h, 0, 0) + (s0, s1)
        return (0, G, 0, 0, s0, s1)
    return INCONNU4


def esus_actif():
    """0.835 : Ésus travaille-t-il ici ? (VTX_ESUS=0 l'éteint partout ; l'ARN du Druide, molécule par molécule)"""
    return os.environ.get("VTX_ESUS") != "0" and ESUS_ICI[0]


def druide_mode():
    """0.835 : VTX_DRUIDE à la forge : « poids » (compter le travail de chaque molécule, et le temps), « 1 » (le temps
    seul : les générations du Druide, sans compteurs qui pèseraient), sinon rien"""
    return os.environ.get("VTX_DRUIDE", "")


def lire_deplier(chemin):
    """0.837 : l'arrangement dans l'ARN du Druide : « deplier MOLÉCULE 1|0 »"""
    d = {}
    try:
        for l in open(chemin, encoding="utf-8"):
            m = l.split()
            if len(m) == 3 and m[0] == "deplier" and m[2] in ("0", "1"):
                d[m[1]] = m[2] == "1"
    except OSError:
        pass
    return d


def lire_arn_druide(chemin):
    """0.835 : l'ARN du Druide (PROG.arn, à côté de l'exécutable) : « esus MOLÉCULE 0 » déconnecte Ésus de la molécule"""
    eteint = set()
    try:
        for l in open(chemin, encoding="utf-8"):
            m = l.split()
            if len(m) == 3 and m[0] == "esus" and m[2] == "0":
                eteint.add(m[1])
    except OSError:
        pass
    return eteint


def borne(e):
    """0.835 : Ésus : la plus grande valeur prouvée de l'entier e (le deuxième des quatre points)"""
    r = points(e)
    return G128 if r[0] > r[1] else r[1]   # vide : par prudence, tout l'intervalle


def lit(v):
    return f"{v & ((1 << 128) - 1)}u128"


def ident(nom):
    return "".join(ch if (ch.isascii() and (ch.isalnum() or ch == "_")) else f"_u{ord(ch):x}_" for ch in nom)


# ------------------------------------------------------------------------------------------------------------------
def compiler_arbre(src, dossier=None, partition=True):
    """La compilation de vtx128.py, pas à pas, pour garder l'arbre des fonctions (celui du Generateur)."""
    if "importer" in src:
        lignes, _ = V.resoudre_carte(src, dossier, "programme")
        src = "\n".join(lignes)
    V.regler_largeur(V.ENTIER_LARGE_DEFAUT and not V.COMPAT_64)
    a = V.Analyseur(V.lexer(src))
    a.compat = V.COMPAT_64
    fs = a.programme()
    if a.donnees:
        fs = V.injecter_donnees(fs, a.donnees)
    noms = {f.nom for f in fs}
    ap = V.Analyseur(V.lexer(V.PRELUDE, True))
    ap.textes = a.textes
    pre = [f for f in ap.programme() if f.nom not in noms]
    for f in pre:
        f.origine = "prélude"
    fs = fs + pre
    V.typer_textes(fs, a.types_champs)
    if not V.COMPAT_64:
        V.vers_lugus(fs)
    gardees = V.elaguer(fs)
    reserve = {f.nom: f for f in fs if f not in gardees}
    V.DERNIERE_PARTITION["accords"], V.DERNIERE_PARTITION["notes"] = [], {}
    if partition:
        V.DERNIERE_PARTITION["accords"], V.DERNIERE_PARTITION["notes"] = V.partitionner(gardees, None)
    g = V.Generateur(gardees, True, a.donnees, reserve)
    g.structs, g.types_champs, g.textes = a.structs, a.types_champs, a.textes
    asm = g.generer()
    mots, etiquettes = V.assembler(asm, True)
    return g, mots, etiquettes


# ------------------------------------------------------------------------------------------------------------------
def appels_dans(e, acc=None):
    """0.826 : les noms des fonctions appelées dans un morceau d'arbre"""
    if acc is None:
        acc = set()
    if isinstance(e, tuple):
        if e and e[0] == "appel" and isinstance(e[1], str):
            acc.add(e[1])
        for x in e:
            appels_dans(x, acc)
    elif isinstance(e, list):
        for x in e:
            appels_dans(x, acc)
    return acc


class Forge(V.Generateur):
    """Le Generateur de vtx128.py pour les types et les règles ; chaque expression devient une expression Rust sur des
    mots de 128 bits (u128)."""

    def __init__(self, g, etiquettes):
        super().__init__(list(g.fonctions.values()), True, g.blobs, dict(g.reserve))
        self.structs, self.types_champs, self.textes = g.structs, g.types_champs, g.textes
        self.etiq = etiquettes
        self.ramasse = None
        self.graphe = {}
        self.forgees = []
        # l'adaptation automatique (les tableaux rangés selon ce qu'on y écrit) : ce que le premier passage a vu écrire
        # dans chaque zone, puis le plan (zone -> (numéro, type Rust)) ; None au premier passage
        self.ecrits = {}
        self.plan = None
        # les noyaux de la carte graphique (Taranis) : le SPIR-V de chaque boucle en segments qui sait y aller
        self.noyaux = []

    def signature(self, nom, ligne):
        f = super().signature(nom, ligne)
        if f not in self.forgees and nom not in {x.nom for x in self.forgees}:
            self.forgees.append(f)
        return f

    # ------------------------------------------------------------ outils
    def tmp(self):
        self.ntmp += 1
        return f"t{self.ntmp}"

    def peut_ramasser(self, nom):
        return self.ramasse is not None and nom in self.ramasse

    def bloc(self, parts, fin):
        """Évalue les parties dans l'ordre, chacune dans une variable ; fin(noms) donne le résultat. Une valeur gardée
        pendant un appel qui peut ramasser les miettes est posée dans la pile de Lugus, comme Lugus l'empile."""
        noms, lets, pousses = [], [], 0
        for i, code in enumerate(parts):
            if SIMPLE.match(code):
                noms.append(code)
                continue
            n = self.tmp()
            lets.append(f"let {n}: u128 = {code};")
            noms.append(n)
            if any(MARQUE in c for c in parts[i + 1:]):
                lets.append(f"c.pousser({n});")
                pousses += 1
        res = fin(noms)
        if not lets:
            return f"({res})"
        marque = MARQUE if any(MARQUE in c for c in parts) or MARQUE in res else ""
        if pousses:
            return f"{{ {' '.join(lets)} let r_ = {res}; c.sp = c.sp.wrapping_add({pousses}); r_ }}{marque}"
        return f"{{ {' '.join(lets)} {res} }}{marque}"

    def b(self, parts, forme):
        return self.bloc(parts, lambda n: forme.format(*n))

    def ligne(self, t):
        self.lignes.append("    " * self.niveau + t)

    # ------------------------------------------------------------ fonctions
    def fonction_rs(self, f):
        self.f, self.vars, self.vtypes, self.vhaut, self.regs = f, {}, {}, {}, {}
        self._corps_vus = set()
        self.boucles, self.ntmp, self.nboucle = [], 0, 0
        self.appelees = set()
        params = []
        for p, t in zip(f.params, f.ptypes):
            if p in self.vars:
                raise VtxError(f"ligne {f.ligne} : paramètre « {p} » en double")
            self.vars[p], self.vtypes[p] = 1, t
            params.append(p)
        loc = []
        self.locales(f.corps, loc)
        ESUS_VARIABLES[0] = esus_definitions(f.corps, f.params, f.nom)
        ESUS_ICI[0] = f.nom not in ESUS_ETEINT[0]
        self.poids_ligne = ""
        self.mol_druide = f.nom
        if druide_mode() == "poids":
            # 0.835 : le compteur de la molécule (un appel, un tour de boucle : son travail, pour le Druide)
            if f.nom not in DRUIDE_NOMS[0]:
                DRUIDE_NOMS[0].append(f.nom)
            self.poids_ligne = f"POIDS[{DRUIDE_NOMS[0].index(f.nom)}].fetch_add(1, std::sync::atomic::Ordering::Relaxed);"
        kinds, locales = {}, []
        for nom, l, kind, st in loc:
            chaque = st[0] == "soit"
            if nom in self.vars:
                if kinds.get(nom) == "pour" and kind == "pour":
                    continue
                raise VtxError(f"ligne {l} : variable « {nom} » déjà déclarée")
            kinds[nom] = kind
            if kind == "pour":
                t = (st[4] or self.typ(st[2])) if chaque else "e"
            else:
                t = st[4] if len(st) > 4 and st[4] else self.typ(st[2])
            self.vtypes[nom] = t
            self.vars[nom] = -1
            locales.append(nom)
        self.toutes = params + locales
        self.places = {v: k for k, v in enumerate(self.toutes)}
        n = len(self.toutes)
        self.cadre_actif = (self.ramasse is not None and n > 0
                            and any(x in self.ramasse for x in self.graphe.get(f.nom, ())))
        self.lignes, self.niveau = [], 1
        # 0.824 : le lot de la carte : des boucles en segments qui se suivent dans le corps d'une fonction (rien entre
        # elles) partent sur la carte d'un seul envoi ; chacune sa place dans le lot (lot_pos), et toutes sauf la
        # dernière attendent (lot_suite) ; tout autre code vide le lot d'abord (taranis_vider)
        corps_f = list(f.corps)
        pos = 0
        # 0.826 : le gène « fondre » de Gutuater : un lot dont les boucles ont le même intervalle devient aussi un seul
        # noyau (les corps à la suite) ; le vergobret choisit entre les deux d'après l'ARN, ou les mesure
        groupes = self.groupes_du_lot(corps_f) if os.environ.get("VTX_FONDRE") != "0" else {}
        passer = set()
        for k, s in enumerate(corps_f):
            if k in passer:
                continue
            if k in groupes and self.fondre(corps_f, groupes[k]):
                passer.update(range(k, groupes[k][-1] + 1))
                continue
            # le suivant : par-dessus les « soit » purs (les bornes d'une boucle, sans mémoire ni appel)
            j = k + 1
            while j < len(corps_f) and corps_f[j][0] == "soit" and self.pur(corps_f[j][2], set()):
                j += 1
            suivant = corps_f[j] if j < len(corps_f) else None
            if s[0] == "accord":
                self.lot_pos = pos
                self.lot_suite = (suivant is not None and self.accord_carte(suivant) and self.accord_carte(s) and pos < 7)
            elif not (s[0] == "soit" and self.pur(s[2], set())):
                self.lot_pos, self.lot_suite, pos = 0, False, 0
            self.instr(s)
            if s[0] == "accord":
                pos = pos + 1 if self.lot_suite else 0
        self.lot_pos, self.lot_suite = 0, False
        corps = self.lignes
        if self.poids_ligne:
            corps = ["    " + self.poids_ligne] + corps
        if druide_mode() == "poids" and L():
            # 0.837 : la membrane observée : ce que les paramètres reçoivent vraiment, à l'entrée de la molécule
            avant_l = self.lignes
            self.lignes = []
            for p in params:
                self.observer(p)
            corps = ["    " + x.strip() for x in self.lignes] + corps
            self.lignes = avant_l
        self.graphe[f.nom] = self.appelees
        if L() and ESUS_VARIABLES[0] is not None:
            # 0.835 : les quatre points de chaque variable entière de la molécule (le relevé d'Ésus, pour le Druide)
            for v in list(params) + list(locales):
                if self.vtypes.get(v) == "e":
                    r6 = ESUS_VARIABLES[0](v)
                    ESUS_RELEVE[0].append((f.nom, v) + (INCONNU4 if r6[0] > r6[1] else r6))
        nom = ident(f.nom)
        sig = ", ".join(f"mut v_{ident(p)}: u128" for p in params)
        sig = "c: &mut Ctx" + (", " + sig if sig else "")
        out = []
        # 0.837 : l'arrangement des molécules, choisi par le Druide (son ARN : « deplier MOL 1 » : la molécule fondue
        # dans celles qui l'appellent ; « deplier MOL 0 » : gardée à part) ; sans ARN, le compilateur décide
        dpl = DEPLIER[0].get(f.nom)
        if dpl is not None:
            out.append("#[inline(always)]" if dpl else "#[inline(never)]")
        if self.cadre_actif:
            noms = ", ".join(f"v_{ident(p)}" for p in params)
            sig0 = ", ".join(["c: &mut Ctx"] + [f"v_{ident(p)}: u128" for p in params])
            out.append(f"fn f_{nom}({sig0}) -> u128 {{")
            out.append(f"    let sp0 = c.sp; c.sp = sp0.wrapping_sub({n});")
            out.append(f"    let r = fc_{nom}(c{', ' + noms if noms else ''}); c.sp = sp0; r")
            out.append("}")
            out.append("#[inline(always)]")
            out.append(f"fn fc_{nom}({sig}) -> u128 {{")
            out.append("    let fp = c.sp;")
        else:
            out.append(f"fn f_{nom}({sig}) -> u128 {{")
        for v in locales:
            out.append(f"    let mut v_{ident(v)}: u128 = 0;")
        # les tableaux serrés : leur adresse lue une fois (nulle s'ils restent dans le cube) ; une écriture d'octet ne
        # peut pas la changer, la boucle reste serrée
        for k in sorted({k for k, _ in (self.plan or {}).values()}):
            if any(f"z{k}." in l for l in corps):
                out.append(f"    let z{k} = unsafe {{ if ZA{k} {{ Z{k} }} else {{ std::ptr::null_mut() }} }};")
        out += corps
        out.append("    0")
        out.append("}")
        return "\n".join(out)

    def recopier_cadre(self):
        if not getattr(self, "cadre_actif", False):
            return ""
        return " ".join(f"c.poser(fp.wrapping_add({self.places[v]}), v_{ident(v)});" for v in self.toutes) + " "

    # ------------------------------------------------------------ instructions
    def observer(self, nom):
        """0.836 : la passe de mesure du Druide (VTX_DRUIDE=poids) : chaque valeur prise par une variable entière est
        observée (la plus petite, la plus grande, sans signe et avec) : le troisième témoin de son codon"""
        if druide_mode() != "poids" or not L() or self.vtypes.get(nom) != "e":
            return
        cle = (getattr(self, "mol_druide", "?"), nom)
        if cle not in DRUIDE_OBS[0]:
            DRUIDE_OBS[0].append(cle)
        self.ligne(f"observer({DRUIDE_OBS[0].index(cle)}, v_{ident(nom)});")

    def instr(self, s):
        g = s[0]
        if g == "soit":
            t = self.vtypes[s[1]]
            if est_ref(t) and len(s) > 4 and s[4] == t and s[2][0] in ("var", "appel") and self.typ(s[2]) == "e":
                code = self.val(s[2])
            else:
                code = self.val(s[2], t)
            self.ligne(f"v_{ident(s[1])} = {code};")
            self.observer(s[1])
        elif g == "affecter":
            self.variable(s[1], s[3])
            self.ligne(f"v_{ident(s[1])} = {self.val(s[2], self.vtypes[s[1]])};")
            self.observer(s[1])
        elif g == "ecrire_champ":
            _st, pos, t = self.champ_de(("champ_ref", s[1], s[2], s[4]))
            b = self.val(s[1])
            v = self.val(s[3], t)
            self.ligne(self.b([b, v], "c.ecrire({0}.wrapping_add(" + str(pos) + "), {1})") + ";")
        elif g == "ecrire":
            et, adr, val = s[1], s[2], s[3]
            zone = s[5] if len(s) > 5 else None
            if zone is not None and self.plan is None:
                self.ecrits.setdefault(zone, []).append(val[1] if val[0] == "nombre" else self.typ(val))
            if zone is not None and self.plan and zone in self.plan:
                k, ty = self.plan[zone]
                a = self.val(adr, "e")
                v = self.val(val)
                self.ligne(self.b([a, v], gabarit(f"{{ let a = @0; let v = @1; let i = ((a as u64) & 0xFFFF_FFFF_FFFF)"
                                                  f".wrapping_sub({zone[1]}) as usize; if !z{k}.is_null() && i < "
                                                  f"{zone[2] - zone[1]} {{ unsafe {{ *z{k}.add(i) = v as {ty}; }} }} else "
                                                  f"{{ c.ecrire(etg(a, {et}), v); }} }}")) + ";")
            elif et == 2:
                # 0.805 : l'étage 2 par la carte du vergobret
                a = self.val(adr, "e")
                v = self.val(val)
                self.ligne(self.b([a, v], "c.ecrire2({0}, {1})") + ";")
            elif isinstance(et, int) and adr[0] == "nombre":
                a = lit((adr[1] & ~(3 << 62) & M64) | (et << 62))
                self.ligne(self.b([self.val(val)], "c.ecrire(" + a + ", {0})") + ";")
            else:
                a = self.adresse(et, adr)
                v = self.val(val)
                self.ligne(self.b([a, v], "c.ecrire({0}, {1})") + ";")
        elif g == "si":
            self.ligne(f"if {self.cond(s[1])} {{")
            self.niveau += 1
            for x in s[2]:
                self.instr(x)
            self.niveau -= 1
            if s[3] is not None:
                self.ligne("} else {")
                self.niveau += 1
                for x in s[3]:
                    self.instr(x)
                self.niveau -= 1
            self.ligne("}")
        elif g == "tantque":
            self.nboucle += 1
            lb = f"'b{self.nboucle}"
            self.ligne(f"{lb}: loop {{")
            self.niveau += 1
            self.ligne(f"if !{self.cond(s[1])} {{ break; }}")
            if self.poids_ligne:
                self.ligne(self.poids_ligne)
            self.boucles.append((f"continue {lb}", f"break {lb}"))
            for x in s[2]:
                self.instr(x)
            self.boucles.pop()
            self.niveau -= 1
            self.ligne("}")
        elif g == "pour":
            self.variable(s[1], s[5])
            self.nboucle += 1
            lb, lc = f"'b{self.nboucle}", f"'c{self.nboucle}"
            v = f"v_{ident(s[1])}"
            self.ligne(f"{v} = {self.val(s[2], 'e')};")
            self.ligne(f"{lb}: loop {{")
            self.niveau += 1
            self.ligne(f"if !{self.cond(('bin', '<', ('var', s[1], s[5]), s[3]))} {{ break; }}")
            if self.poids_ligne:
                self.ligne(self.poids_ligne)
            self.ligne(f"{lc}: {{")
            self.niveau += 1
            self.boucles.append((f"break {lc}", f"break {lb}"))
            for x in s[4]:
                self.instr(x)
            self.boucles.pop()
            self.niveau -= 1
            self.ligne("}")
            pas = s[6] if len(s) > 6 else 1
            self.ligne(f"{v} = (({v} as u64).wrapping_add({pas & M64}u64)) as u128;")
            self.niveau -= 1
            self.ligne("}")
        elif g == "asm":
            if self.f.nom != "__init":
                raise VtxError("la forge ne traduit pas l'assembleur écrit dans le programme")
            # la copie des données (injecter_donnees) : de l'image du programme vers leur étage
            for i, (et, adr, vals) in enumerate(self.blobs):
                if vals:
                    src = self.etiq[f"DONNEES{i}"]
                    dst = (adr & ~(3 << 62) & M64) | (et << 62)
                    self.ligne(f"for k in 0..{len(vals)}u128 {{ let v = c.lire({src}u128 + k); c.ecrire({dst}u128 + k, v); }}")
        elif g == "bloc":
            if len(s) > 2 and isinstance(s[2], tuple) and s[2][0] == "chaque" and self.parallele_possible(s[2]):
                self.chaque_parallele(s)
            elif len(s) > 2 and isinstance(s[2], tuple) and s[2][0] == "vague" and all(
                    self.typ(e) == "e" and self.pur(e, set()) for _, e in s[2][1]):
                self.vague_parallele(s[2][1])
            elif len(s) > 2 and isinstance(s[2], tuple) and s[2][0] == "souvenirs" and self.souvenirs_paralleles(s[2][1]):
                if s[2][2] == 0:
                    self.vague_de_souvenirs(s[2][1])
            else:
                for x in s[1]:
                    self.instr(x)
        elif g == "segments":
            pre, _ = V.deplier_segments(s)
            for x in pre:
                self.instr(x)
            self.instr(("pour", s[1], ("var", f"__sa{s[7]}", s[5]), ("var", f"__sb{s[7]}", s[5]), s[4], s[5], 1))
        elif g == "accord":
            # 0.824 : ce qui reste du lot de la carte part avant tout autre travail (sauf une boucle du lot elle-même)
            if not (getattr(self, "lot_pos", 0) > 0 or getattr(self, "lot_suite", False)):
                self.ligne("taranis_vider(c);")
            # les segments d'une boucle : la partition les range en mesures (une par segment quand elle ne prouve pas
            # qu'ils sont indépendants, par exemple quand ils écrivent le cube à une adresse calculée) ; les cylindres
            # le vérifient en jouant (fusionner), et rejouent dans l'ordre si besoin : toutes les notes, dans l'ordre
            toutes = [st for mesure in s[2] for st, _note, _nom in mesure]
            ligne_acc = V.DERNIERE_PARTITION["accords"][s[1]]["ligne"] if s[1] < len(V.DERNIERE_PARTITION["accords"]) else None
            if ligne_acc in V.LIGNES_BANDES and self.cylindres_possibles(toutes):
                self.notes_en_bandes(toutes, ligne_acc)
            elif self.cylindres_possibles(toutes):
                self.notes_en_cylindres(toutes)
            else:
                for mesure in s[2]:
                    for st, _note, _nom in mesure:
                        self.instr(st)
        elif g in ("arreter", "continuer"):
            if not self.boucles:
                raise VtxError(f"ligne {s[1]} : « {'arrêter' if g == 'arreter' else 'continuer'} » hors d'une boucle")
            self.ligne(self.boucles[-1][1 if g == "arreter" else 0] + ";")
        elif g == "retour":
            if s[1] is None:
                self.ligne("return 0;")
            else:
                self.ligne(f"return {self.val(s[1], self.f.rtype)};")
        else:
            self.ligne(f"let _ = {self.val(s[1])};")

    # ------------------------------------------------------------ les vagues sur plusieurs cœurs
    # « somme (min, max) pour chaque i dans a..b : f(i) -> s » : quand chaque atome de la vague est pur (il ne lit ni
    # n'écrit la mémoire, ne touche pas le monde) et rend un entier de 64 bits, la vague est partagée entre les cœurs ;
    # chaque fil a sa propre machine (pile comprise), et la réduction (associative sur les entiers) donne le même
    # résultat que la machine émulée, dans n'importe quel ordre.
    EFFETS = {"__rompre", "sortie", "afficher", "entrée", "lire_car", "ecrire_car", "__service", "ouvrir_lecture", "ouvrir_ecriture",
              "fermer", "fin_de", "bruit", "pile", "marquer_adn", "marquer_arn", "liberer_brin", "brin", "gemv", "tableau",
              "nouveau", "nouveau_de", "ecrire", "texte", "presenter", "ecran", "pixel"}
    INTERDITS = {"lire", "ecrire", "champ_ref", "ecrire_champ", "asm", "accord", "segments", "mem", "rangee_lire",
                 "rangee_ecrire", "hyp"}

    def pur(self, n, vus):
        """Ni mémoire (hors de la pile), ni effet, ni appel impur, dans n et dans les fonctions qu'il appelle."""
        if isinstance(n, list):
            return all(self.pur(x, vus) for x in n)
        if not isinstance(n, tuple) or not n:
            return True
        if isinstance(n[0], str):
            if n[0] in self.INTERDITS:
                return False
            if n[0] == "appel" and len(n) > 2 and isinstance(n[1], str):
                nom = n[1]
                if nom in self.EFFETS:
                    return False
                f = self.fonctions.get(nom) or (self.reserve.get(nom) if hasattr(self, "reserve") else None)
                if f is not None and nom not in vus:
                    vus.add(nom)
                    if not self.pur(f.corps, vus):
                        return False
            return all(self.pur(x, vus) for x in n[1:])
        return all(self.pur(x, vus) for x in n)

    def locales(self, instr, acc):
        super().locales(instr, acc)
        for s in instr:
            # les souvenirs et les cœurs : le drapeau « oublié » de chaque atome (il n'est que dans la forge)
            if s[0] == "bloc" and len(s) > 2 and isinstance(s[2], tuple) and s[2][0] == "souvenirs":
                p = s[2][1][s[2][2]]
                acc.append((p["oublie"], p["ligne"], "soit", ("soit", p["oublie"], ("nombre", 0), p["ligne"], "e")))

    def souvenirs_paralleles(self, groupe):
        return len(groupe) >= 2 and all(self.typ(p["appel"]) == "e" and self.pur(p["appel"], set()) for p in groupe)

    def vague_de_souvenirs(self, groupe):
        """Les souvenirs et les cœurs : chaque atome lourd de la vague regarde son souvenir ; ceux qui l'ont oublié
        réagissent ensemble, chacun sur son cœur (un seul : sur le fil principal) ; puis chacun range le sien."""
        for p in groupe:
            for x in p["regarder"]:
                self.instr(x)
        oub = [f"v_{ident(p['oublie'])}" for p in groupe]
        sorties = [f"v_{ident(p['sortie'])}" for p in groupe]
        exprs = [self.val(p["appel"], "e") for p in groupe]
        self.ligne("{")
        self.niveau += 1
        self.ligne("let n_oublies = " + " + ".join(f"({o} != 0) as u32" for o in oub) + ";")
        # VTX_COEURS=1 : tout sur le fil principal (pour mesurer) ; sinon les cœurs de la machine
        self.ligne("static COEURS: std::sync::OnceLock<usize> = std::sync::OnceLock::new();")
        self.ligne("let coeurs = *COEURS.get_or_init(|| std::env::var(\"VTX_COEURS\").ok().and_then(|v| v.parse().ok())"
                   ".unwrap_or_else(|| std::thread::available_parallelism().map(|n| n.get()).unwrap_or(1)));")
        self.ligne("if n_oublies >= 2 && coeurs > 1 {")
        self.niveau += 1
        self.ligne("let r = std::thread::scope(|sc| {")
        for k, (o, x) in enumerate(zip(oub, exprs)):
            self.ligne(f"    let h{k} = if {o} != 0 {{ Some(sc.spawn(move || {{ let mut c_fils = ctx_fils(); let c = &mut c_fils; "
                       f"({x}) as u128 }})) }} else {{ None }};")
        self.ligne("    (" + ", ".join(f"h{k}.map(|h| h.join().unwrap())" for k in range(len(exprs))) + ",)")
        self.ligne("});")
        for k, sv in enumerate(sorties):
            self.ligne(f"if let Some(v) = r.{k} {{ {sv} = v; }}")
        self.niveau -= 1
        self.ligne("} else {")
        self.niveau += 1
        for o, sv, x in zip(oub, sorties, exprs):
            self.ligne(f"if {o} != 0 {{ {sv} = ({x}) as u128; }}")
        self.niveau -= 1
        self.ligne("}")
        self.niveau -= 1
        self.ligne("}")
        for p in groupe:
            for x in p["ranger"]:
                self.instr(x)

    # ------------------------------------------------------------ les cylindres : les segments sur plusieurs cœurs
    SANS_CUBE = INTERDITS - {"lire", "ecrire", "mem"}

    def sans_effet(self, n, vus):
        """Comme pur, mais le cube est permis (lu et écrit) : ni monde, ni tas, ni assembleur, ni accord imbriqué."""
        if isinstance(n, list):
            return all(self.sans_effet(x, vus) for x in n)
        if not isinstance(n, tuple) or not n:
            return True
        if isinstance(n[0], str):
            if n[0] in self.SANS_CUBE:
                return False
            if n[0] == "appel" and len(n) > 2 and isinstance(n[1], str):
                nom = n[1]
                if nom in self.EFFETS:
                    return False
                f = self.fonctions.get(nom) or (self.reserve.get(nom) if hasattr(self, "reserve") else None)
                if f is not None and nom not in vus:
                    vus.add(nom)
                    if not self.sans_effet(f.corps, vus):
                        return False
            return all(self.sans_effet(x, vus) for x in n[1:])
        return all(self.sans_effet(x, vus) for x in n)

    def groupes_du_lot(self, corps):
        """0.826 : les lots de la carte d'un corps : {première place : [places des accords]} (deux accords au moins,
        huit au plus, rien entre eux que des « soit » purs)"""
        groupes = {}
        k = 0
        while k < len(corps):
            if not self.accord_carte(corps[k]):
                k += 1
                continue
            g = [k]
            j = k + 1
            while j < len(corps) and len(g) < 8:
                if corps[j][0] == "soit" and self.pur(corps[j][2], set()):
                    j += 1
                    continue
                if self.accord_carte(corps[j]):
                    g.append(j)
                    j += 1
                    continue
                break
            if len(g) >= 2:
                groupes[k] = g
            k = g[-1] + 1
        return groupes

    def fondre(self, corps, places):
        """0.826 : le lot (les accords aux places dites) fondu en un noyau, si la forge sait le faire : le même intervalle
        pour toutes les boucles ; chaque écriture à une fréquence connue ((F << 24) + x) ; le noyau fondu se compile pour
        Taranis. Il est écrit à côté du lot séparé ; le vergobret choisit (gene_fondre_debut). Faux : rien n'est écrit."""
        if os.environ.get("VTX_CARTE") == "0" or L():
            return False                         # 0.833 : Taranis compte en 64 bits : seul un programme « dunon; » y va
        valeurs = {}
        for s in corps[:places[-1] + 1]:
            if s[0] == "soit" and self.pur(s[2], set()):
                valeurs[s[1]] = s[2]

        def norme(e):
            if isinstance(e, tuple):
                if len(e) >= 2 and e[0] == "var":
                    return norme(valeurs[e[1]]) if e[1] in valeurs else ("var", e[1])
                return tuple(norme(x) for x in e if not isinstance(x, int) or e[0] == "nombre")
            if isinstance(e, list):
                return [norme(x) for x in e]
            return e

        membres = []
        for k in places:
            notes = [st for mesure in corps[k][2] for st, _n, _m in mesure]
            membres.append(notes)
        tete = membres[0]
        intervalle = (norme(tete[0][2]), norme(tete[-1][3]))
        if any((norme(n[0][2]), norme(n[-1][3])) != intervalle for n in membres):
            return False
        var = tete[0][1]

        def renommer(e, ancien):
            if isinstance(e, tuple):
                if len(e) >= 2 and e[0] == "var" and e[1] == ancien:
                    return ("var", var) + tuple(e[2:])
                return tuple(renommer(x, ancien) for x in e)
            if isinstance(e, list):
                return [renommer(x, ancien) for x in e]
            return e

        corps_fondu = []
        for n in membres:
            corps_fondu += renommer(list(n[0][4]), n[0][1])
        # les écritures, par tout l'arbre des appels : chacune à une fréquence connue
        garde, vues, a_voir = set(), set(), [corps_fondu]
        while a_voir:
            morceau = a_voir.pop()
            for genre, et, adr in noyau_vtx.acces_memoire(morceau, []):
                if genre == "?":
                    return False
                if genre == "E":
                    if not (isinstance(adr, tuple) and adr[0] == "bin" and adr[1] == "+" and adr[2][0] == "bin"
                            and adr[2][1] == "<<" and adr[2][2][0] == "nombre" and adr[2][3] == ("nombre", 24)):
                        return False
                    # 0.831 : et à une case nommée (le tour, ou le paramètre qui le reçoit) : une case calculée (la
                    # projection des points, qui écrit où tombe le point) ne se fond pas
                    if not (isinstance(adr[3], tuple) and adr[3][0] == "var"):
                        return False
                    garde.add(adr[2][2][1])
            for nom in appels_dans(morceau):
                g = self.fonctions.get(nom)
                if g is not None and nom not in vues:
                    vues.add(nom)
                    a_voir.append(list(g.corps))
        if not garde:
            return False
        try:
            spv, dehors, _ = noyau_vtx.NoyauTaranis(self, var, corps_fondu, region=0, garde=garde).compiler()
        except noyau_vtx.PasPourLaCarte as e:
            if os.environ.get("VTX_TARANIS"):
                print(f"taranis : le lot de la ligne {tete[0][5]} ne se fond pas : {e}", file=sys.stderr)
            return False
        lieu = tete[0][5]
        if os.environ.get("VTX_TARANIS"):
            print(f"taranis : le lot de la ligne {lieu} se fond aussi en un noyau ({len(places)} boucles ; la garde : "
                  f"{sorted(garde)})", file=sys.stderr)
        k = len(self.noyaux)
        self.noyaux.append(spv)
        # les « soit » purs du lot d'abord (les bornes des boucles), puis l'une ou l'autre forme
        for s in corps[places[0]:places[-1] + 1]:
            if s[0] == "soit":
                self.instr(s)
        self.ligne("taranis_vider(c);")
        self.ligne("{")
        self.niveau += 1
        self.ligne("let mut fondu = false;")
        self.ligne(f"if gene_fondre_debut({lieu}) {{")
        self.niveau += 1
        self.ligne(f"let ta: u128 = {self.val(tete[0][2], 'e')};")
        self.ligne(f"let tb: u128 = {self.val(tete[-1][3], 'e')};")
        ext = ", ".join(f"v_{ident(n)}" for n in dehors)
        self.ligne(f"fondu = (tb as u64) > (ta as u64) && taranis_fondre(c, &SPV{k}, ta, tb, &[{ext}], {lieu});")
        self.niveau -= 1
        self.ligne("}")
        self.ligne("if !fondu {")
        self.niveau += 1
        for j, k2 in enumerate(places):
            self.lot_pos, self.lot_suite = j, j < len(places) - 1
            self.instr(corps[k2])
        self.lot_pos, self.lot_suite = 0, False
        self.niveau -= 1
        self.ligne("}")
        self.ligne(f"gene_fondre_fin({lieu}, fondu);")
        self.niveau -= 1
        self.ligne("}")
        return True

    def accord_carte(self, s):
        """0.824 : un accord qui peut aller à la carte dans un lot : des segments d'une même boucle (pas une boucle en
        bandes, qui reste aux cœurs du processeur)"""
        if s[0] != "accord":
            return False
        ligne_acc = V.DERNIERE_PARTITION["accords"][s[1]]["ligne"] if s[1] < len(V.DERNIERE_PARTITION["accords"]) else None
        if ligne_acc in V.LIGNES_BANDES:
            return False
        toutes = [st for mesure in s[2] for st, _note, _nom in mesure]
        return self.cylindres_possibles(toutes)

    def cylindres_possibles(self, notes):
        """Une mesure jouée par des cylindres : au moins deux notes, toutes des segments d'une même boucle (la même
        variable, le même corps), et un corps qui ne touche que le cube."""
        if len(notes) < 2 or self.plan or any(st[0] != "pour" for st in notes):
            return False
        if any(st[1] != notes[0][1] or st[4] != notes[0][4] for st in notes):
            return False
        return self.sans_effet(notes[0][4], set())

    def part_des_coeurs(self, notes, bandes):
        """La part de chaque cœur : un fil par cœur et par passage (std::thread::scope), pour les cylindres en segments et
        les bandes dont les notes ne sont pas les segments d'une même boucle. 0.806 : les bandes d'une même boucle vont à
        l'équipe du vergobret (equipe_en_morceaux) ; l'alourdissement vu en 0.77 venait des variables prises par la tâche
        sans être copiées : copiées (move), la fonction jouée sur un seul cœur ne s'alourdit plus."""
        m = len(notes)
        self.ligne("let recoltes: Vec<Recolte> = std::thread::scope(|sc| {")
        self.niveau += 1
        self.ligne("let inst = &inst;")
        self.ligne("let fils: Vec<_> = (0..nt).map(|t| sc.spawn(move || {")
        self.niveau += 1
        self.ligne(f"let mut c_fils = {'ctx_bande' if bandes else 'ctx_cylindre'}(inst); let c = &mut c_fils;")
        # les variables de la fonction, recopiées dans le fil (locales, elles vont dans les registres)
        if self.toutes:
            self.ligne(" ".join(f"let mut v_{ident(v)} = v_{ident(v)};" for v in self.toutes))
        if bandes:
            # chaque cœur sa bande : des segments contigus (les mêmes données d'un pas à l'autre)
            self.ligne(f"for q in (t * {m} / nt)..((t + 1) * {m} / nt) {{")
        else:
            # les segments en alternance (chaque cylindre a sa part du travail où qu'il soit dans la boucle)
            self.ligne(f"for q in (t..{m}).step_by(nt) {{")
        self.niveau += 1
        self.ligne("match q {")
        self.niveau += 1
        for k, st in enumerate(notes):
            self.ligne(f"{k} => {{")
            self.niveau += 1
            self.instr(st)
            self.niveau -= 1
            self.ligne("}")
        self.ligne("_ => {}")
        self.niveau -= 1
        self.ligne("}")
        self.niveau -= 1
        self.ligne("}")
        self.ligne("let r = rendre(c); remettre_ctx(c_fils); r")
        self.niveau -= 1
        self.ligne("})).collect();")
        self.ligne("fils.into_iter().map(|h| h.join().unwrap()).collect()")
        self.niveau -= 1
        self.ligne("});")

    def equipe_en_morceaux(self, notes):
        """0.806 : le vergobret : la boucle entière [a, b) coupée à l'exécution en morceaux (quatre par cœur, alignés sur
        le pas) ; l'équipe de cœurs (créée une fois, gardée vivante : equipe_jouer) les prend l'un après l'autre (un
        compteur partagé) : chaque cœur libre prend le suivant, quel que soit le nombre de cœurs ou le coût de chaque
        morceau. Les variables de la fonction sont copiées dans la tâche (move) : la fonction jouée sur un seul cœur garde
        les siennes dans les registres."""
        st0 = notes[0]
        var, corps, ln = st0[1], st0[4], st0[5]
        pas = (st0[6] if len(st0) > 6 else 1) & M64
        self.ligne(f"let ta: u64 = {self.val(st0[2], 'e')} as u64;")
        self.ligne(f"let tb: u64 = {self.val(notes[-1][3], 'e')} as u64;")
        self.ligne(f"let compte: u64 = if tb > ta {{ (tb - ta + {pas - 1}) / {pas} }} else {{ 0 }};")
        self.ligne("let nk: u64 = ((nt as u64) * 4).min(compte).max(1);")
        self.ligne("let suivant = std::sync::atomic::AtomicU64::new(0);")
        self.ligne("let recoltes: Vec<Recolte> = {")
        self.niveau += 1
        self.ligne("let inst = &inst; let suivant = &suivant;")
        if self.toutes:
            self.ligne(" ".join(f"let w_{ident(v)} = v_{ident(v)};" for v in self.toutes))
        self.ligne("let tache = move |_t: usize| -> Recolte {")
        self.niveau += 1
        self.ligne("let mut c_fils = ctx_bande(inst); let c = &mut c_fils;")
        if self.toutes:
            self.ligne(" ".join(f"let mut v_{ident(v)} = w_{ident(v)};" for v in self.toutes))
        self.ligne("loop {")
        self.niveau += 1
        self.ligne("let q = suivant.fetch_add(1, std::sync::atomic::Ordering::Relaxed);")
        self.ligne("if q >= nk { break; }")
        self.ligne(f"let lo = ta + compte * q / nk * {pas}; let hi = (ta + compte * (q + 1) / nk * {pas}).min(tb);")
        self.variable(var, ln)
        self.nboucle += 1
        lb, lc = f"'b{self.nboucle}", f"'c{self.nboucle}"
        v = f"v_{ident(var)}"
        self.ligne(f"{v} = lo as u128;")
        self.ligne(f"{lb}: loop {{")
        self.niveau += 1
        self.ligne(f"if ({v} as u64) >= hi {{ break; }}")
        self.ligne(f"{lc}: {{")
        self.niveau += 1
        self.boucles.append((f"break {lc}", f"break {lb}"))
        for x in corps:
            self.instr(x)
        self.boucles.pop()
        self.niveau -= 1
        self.ligne("}")
        self.ligne(f"{v} = (({v} as u64).wrapping_add({pas}u64)) as u128;")
        self.niveau -= 1
        self.ligne("}")
        self.niveau -= 1
        self.ligne("}")
        if self.toutes:
            self.ligne(" ".join(f"let _ = v_{ident(v)};" for v in self.toutes))
        self.ligne("let r = rendre(c); remettre_ctx(c_fils); r")
        self.niveau -= 1
        self.ligne("};")
        self.ligne("equipe_jouer(nt, &tache)")
        self.niveau -= 1
        self.ligne("};")

    def notes_en_cylindres(self, notes):
        """Les notes d'une mesure jouées ensemble : un cylindre par cœur, chacun des notes qui se suivent, sur son propre
        cube ; puis la fusion (noyau : fusionner) ; si elle refuse, les notes l'une après l'autre."""
        m = len(notes)
        self.ligne("{")
        self.niveau += 1
        self.ligne("let mut fait = false;")
        choix = self.vers_la_carte(notes)
        # 0.824 : la boucle se joue au processeur : le lot de la carte part, et ce qu'elle tient seule redescend
        self.ligne("if !fait { taranis_rapatrier(c); }")
        self.ligne("if !fait && cylindres_voulus() > 1 {")
        self.niveau += 1
        self.ligne("let t0 = std::time::Instant::now();")
        self.ligne("let inst = instantane(c);")
        self.ligne(f"let nt = cylindres_voulus().min({m});")
        self.part_des_coeurs(notes, False)
        self.ligne("let t1 = std::time::Instant::now();")
        self.ligne("fait = fusionner(c, &inst, recoltes);")
        self.ligne("chrono_cylindres(t0, t1);")
        self.niveau -= 1
        self.ligne("}")
        self.ligne("if !fait {")
        self.niveau += 1
        for st in notes:
            self.instr(st)
        self.niveau -= 1
        self.ligne("}")
        if choix:
            self.ligne(f"if c.ombre.is_none() {{ {choix[0]}.noter(choix_carte, choix_t0.elapsed(), {choix[1]}); }}")
        self.niveau -= 1
        self.ligne("}")

    def notes_en_bandes(self, notes, ligne):
        """0.77 : une boucle « en bandes » : chaque cœur sa bande (des segments qui se suivent), et tous écrivent
        directement dans le cube commun ; chacun note les mots qu'il lit et écrit ; après, si un cœur a écrit un mot
        qu'un autre a lu ou écrit, la promesse n'est pas tenue : la machine s'arrête et le dit (comme t[i] hors du
        tableau). Une page absente du cube commun passe par une feuille, fondue ensuite."""
        m = len(notes)
        # 0.806 : les notes sont les segments d'une même boucle (même variable, même corps) : la boucle est coupée à
        # l'exécution, en petits morceaux (quatre par cœur), pris par l'équipe au fur et à mesure
        meme = all(st[0] == "pour" and st[1] == notes[0][1] and repr(st[4]) == repr(notes[0][4])
                   and (st[6] if len(st) > 6 else 1) == (notes[0][6] if len(notes[0]) > 6 else 1) for st in notes)
        self.ligne("{")
        self.niveau += 1
        # 0.810 : le réglage de cette boucle (le vergobret mesure : combien de cœurs lui vont le mieux)
        self.nreglages = getattr(self, "nreglages", 0) + 1
        site = f"REGLAGE_{self.nreglages}"
        # 0.812 : la clé de la boucle pour la mémoire du vergobret : son programme, sa ligne et son corps
        h = 14695981039346656037
        for o in f"{getattr(self, 'nom_programme', '')}:{ligne}:{notes!r}".encode("utf-8"):
            h = ((h ^ o) * 1099511628211) & M64
        self.reglages = getattr(self, "reglages", []) + [(site, h)]
        self.ligne(f"let nt_voulu = if c.ombre.is_none() {{ {site}.coeurs() }} else {{ 1 }};")
        self.ligne("let t_reglage = std::time::Instant::now();")
        self.ligne("if nt_voulu > 1 {")
        self.niveau += 1
        self.ligne("let t0 = std::time::Instant::now();")
        self.ligne("let inst = instantane(c);")
        if meme:
            self.ligne("let nt = nt_voulu;")
            self.equipe_en_morceaux(notes)
        else:
            self.ligne(f"let nt = nt_voulu.min({m});")
            self.part_des_coeurs(notes, True)
        self.ligne("let t1 = std::time::Instant::now();")
        self.ligne("if recoltes.iter().any(|r| r.danger) || bandes_touchees(&recoltes).is_some() {")
        self.ligne(f"    arreter(c, \"ligne {ligne} : la boucle « en bandes » n'a pas tenu sa promesse : deux cœurs ont touché le "
                   f"même mot (l'un l'écrivait, l'autre le lisait ou l'écrivait) ; écrivez « en segments »\");")
        self.ligne("}")
        self.ligne("if !fusionner(c, &inst, recoltes) {")
        self.ligne(f"    arreter(c, \"ligne {ligne} : la boucle « en bandes » n'a pas tenu sa promesse ; écrivez « en segments »\");")
        self.ligne("}")
        self.ligne("c.oublier_pages();")
        self.ligne("chrono_cylindres(t0, t1);")
        self.niveau -= 1
        self.ligne("} else {")
        self.niveau += 1
        for st in notes:
            self.instr(st)
        self.niveau -= 1
        self.ligne("}")
        self.ligne(f"if c.ombre.is_none() {{ {site}.noter(nt_voulu, t_reglage.elapsed(), 1, {ligne}); }}")
        self.niveau -= 1
        self.ligne("}")

    def vers_la_carte(self, notes):
        """Taranis : la boucle entière (toutes les notes) sur la carte graphique, si son corps sait y aller (le SPIR-V
        de taranis/noyau_vtx.py) ; la fenêtre de l'étage 2 se calcule ici, aux tours a, a + 1 et b - 1 ; si la carte
        manque ou refuse, ou si un accès sort de la fenêtre, les cylindres prennent la boucle (fait reste faux)."""
        if os.environ.get("VTX_CARTE") == "0" or L():
            return                               # 0.833 : Taranis compte en 64 bits : seul un programme « dunon; » y va
        st = notes[0]
        var, corps = st[1], st[4]
        pages = False
        try:
            spv, dehors, acces = noyau_vtx.Noyau(self, var, corps).compiler()
        except noyau_vtx.PasPourLaCarte as e:
            # 0.816 : sinon, le mode pages (tout l'étage 2 par la table des pages)
            if os.environ.get("VTX_PAGES") == "0":
                if os.environ.get("VTX_TARANIS"):
                    print(f"taranis : la boucle de la ligne {st[5]} reste au processeur : {e}", file=sys.stderr)
                return
            try:
                spv, dehors, acces = noyau_vtx.Noyau(self, var, corps, pages=True).compiler()
                # 0.817 : le même noyau en entiers de 64 bits de la carte (pris si la carte les fait)
                spv64, dehors64, _ = noyau_vtx.NoyauI64(self, var, corps).compiler()
                assert dehors64 == dehors
                # 0.820 : l'épissage rapide (le modèle classique : la promesse n'est pas vérifiée sur la carte)
                # 0.821 : c'est Taranis, le noyau de la carte (le monde d'un seul tenant, les divisions épissées)
                region = min(getattr(self, "lot_pos", 0), 7)
                # 0.825 : le lieu du lot (la ligne de sa première boucle) : c'est là que Gutuater et le vergobret le
                # reconnaissent, d'un passage à l'autre
                if getattr(self, "lot_pos", 0) == 0:
                    self.lot_tete = st[5]
                spv64r, dehors64r, _ = noyau_vtx.NoyauTaranis(self, var, corps, region=region, atomique=True).compiler()
                assert dehors64r == dehors
                pages = True
            except noyau_vtx.PasPourLaCarte as e2:
                if os.environ.get("VTX_TARANIS"):
                    print(f"taranis : la boucle de la ligne {st[5]} reste au processeur : {e} ; en pages : {e2}",
                          file=sys.stderr)
                return
            if os.environ.get("VTX_TARANIS"):
                print(f"taranis : la boucle de la ligne {st[5]} va à la carte, en pages", file=sys.stderr)
        if pages:
            k = len(self.noyaux)
            self.noyaux.append(spv)
            self.noyaux.append(spv64)
            self.noyaux.append(spv64r)
            v = f"v_{ident(var)}"
            ext = ", ".join(f"v_{ident(n)}" for n in dehors)
            # 0.816 : le vergobret choisit la carte ou le processeur en mesurant (Choix) ; le temps se note à la fin de
            # la boucle (notes_en_cylindres), quel que soit le chemin
            self.nchoix = getattr(self, "nchoix", 0) + 1
            site = f"CHOIX_{self.nchoix}"
            self.choix = getattr(self, "choix", []) + [site]
            self.ligne(f"let choix_t0 = std::time::Instant::now();")
            dans_lot = getattr(self, "lot_pos", 0) > 0 or getattr(self, "lot_suite", False)
            self.ligne(f"let choix_carte = {site}.{'carte_voulue_lot' if dans_lot else 'carte_voulue'}();")
            self.ligne("if choix_carte {")
            self.niveau += 1
            self.ligne(f"let ta: u128 = {self.val(st[2], 'e')};")
            self.ligne(f"let tb: u128 = {self.val(notes[-1][3], 'e')};")
            self.ligne(f"if (tb as u64) > (ta as u64) && taranis_boucle_pages(c, &SPV{k}, &SPV{k + 1}, &SPV{k + 2}, ta, tb, &[{ext}], {region}, {'true' if getattr(self, 'lot_suite', False) else 'false'}, {getattr(self, 'lot_tete', 0) if dans_lot else 0}) {{")
            self.ligne(f"    fait = true;")
            self.ligne(f"    {v} = tb;")
            self.ligne("}")
            self.niveau -= 1
            self.ligne("}")
            return (site, st[5])
        # 0.832 : avec l'épissage rapide, une boucle simple va aussi à Taranis (et pas au vieux chemin de la fenêtre) :
        # les fréquences de la carte (200 et plus) n'y vivent que sur la carte ; la fenêtre écrivait dans la copie du
        # processeur, et la carte ne le voyait pas (la projection ne vidait pas ses pixels : l'image coulait)
        try:
            spv_p, dehors_p, _ = noyau_vtx.Noyau(self, var, corps, pages=True).compiler()
            spv64_p, _, _ = noyau_vtx.NoyauI64(self, var, corps).compiler()
            region = min(getattr(self, "lot_pos", 0), 7)
            if getattr(self, "lot_pos", 0) == 0:
                self.lot_tete = st[5]
            spv64r_p, dehors_r, _ = noyau_vtx.NoyauTaranis(self, var, corps, region=region, atomique=True).compiler()
            rapide_ok = dehors_p == dehors and dehors_r == dehors
        except noyau_vtx.PasPourLaCarte:
            rapide_ok = False
        v = f"v_{ident(var)}"
        if rapide_ok:
            kr = len(self.noyaux)
            self.noyaux += [spv_p, spv64_p, spv64r_p]
            dans_lot = getattr(self, "lot_pos", 0) > 0 or getattr(self, "lot_suite", False)
            ext_r = ", ".join(f"v_{ident(n)}" for n in dehors)
            self.ligne("if epissage_rapide() {")
            self.niveau += 1
            self.ligne(f"let ta: u128 = {self.val(st[2], 'e')};")
            self.ligne(f"let tb: u128 = {self.val(notes[-1][3], 'e')};")
            self.ligne(f"if (tb as u64) > (ta as u64) && taranis_boucle_pages(c, &SPV{kr}, &SPV{kr + 1}, &SPV{kr + 2}, ta, tb, &[{ext_r}], {region}, {'true' if getattr(self, 'lot_suite', False) else 'false'}, {getattr(self, 'lot_tete', 0) if dans_lot else 0}) {{")
            self.ligne(f"    fait = true;")
            self.ligne(f"    {v} = tb;")
            self.ligne("}")
            self.niveau -= 1
            self.ligne("}")
            self.ligne("if !fait {")
            self.niveau += 1
        k = len(self.noyaux)
        self.noyaux.append(spv)
        cles = []
        self.ligne("taranis_rapatrier(c);")
        self.ligne("{")
        self.niveau += 1
        self.ligne(f"let ta: u128 = {self.val(st[2], 'e')};")
        self.ligne(f"let tb: u128 = {self.val(notes[-1][3], 'e')};")
        self.ligne("if (tb as u64) > (ta as u64) {")
        self.niveau += 1
        self.ligne(f"let sauve = {v};")
        noms = []
        for j, (genre, et, adr) in enumerate(acces):
            cle = repr(adr)
            if cle not in cles:
                cles.append(cle)
            for q, point in enumerate(("ta", "((ta as u64).wrapping_add(1)) as u128", "((tb as u64).wrapping_sub(1)) as u128")):
                self.ligne(f"{v} = {point};")
                self.ligne(f"let x{j}_{q}: u128 = {self.adresse(et, adr)};")
            noms.append(f"({'true' if genre == 'E' else 'false'}, x{j}_0, x{j}_1, x{j}_2, {cles.index(cle)}u32)")
        self.ligne(f"{v} = sauve;")
        ext = ", ".join(f"v_{ident(n)}" for n in dehors)
        self.ligne(f"fait = taranis_boucle(c, &SPV{k}, ta, tb, &[{', '.join(noms)}], &[{ext}]);")
        self.ligne(f"if fait {{ {v} = tb; }}")
        self.niveau -= 1
        self.ligne("}")
        self.niveau -= 1
        self.ligne("}")
        if rapide_ok:
            self.niveau -= 1
            self.ligne("}")

    def parallele_possible(self, meta):
        _, red, var, a_, b_, corps_, s_ = meta
        return self.typ(corps_) == "e" and self.pur(corps_, set()) and self.pur(a_, set()) and self.pur(b_, set())

    def vague_parallele(self, items):
        """Les atomes lourds d'une même vague : chacun sur son cœur (le dernier sur le fil principal)."""
        noms = [f"v_{ident(n)}" for n, _ in items]
        exprs = [self.val(e, "e") for _, e in items]
        self.ligne("{")
        self.niveau += 1
        self.ligne("let r = std::thread::scope(|sc| {")
        for k, x in enumerate(exprs[:-1]):
            self.ligne(f"    let h{k} = sc.spawn(move || {{ let mut c_fils = ctx_fils(); let c = &mut c_fils; ({x}) as u128 }});")
        self.ligne(f"    let dernier: u128 = ({exprs[-1]}) as u128;")
        self.ligne("    (" + ", ".join(f"h{k}.join().unwrap()" for k in range(len(exprs) - 1)) + ", dernier)")
        self.ligne("});")
        for k, n in enumerate(noms):
            self.ligne(f"{n} = r.{k};")
        self.niveau -= 1
        self.ligne("}")

    def chaque_parallele(self, s):
        _, red, var, a_, b_, corps_, s_ = s[2]
        init = {"somme": "0u64", "min": "u64::MAX", "max": "0u64"}[red]
        op = {"somme": "acc.wrapping_add(x)", "min": "acc.min(x)", "max": "acc.max(x)"}[red]
        pli = {"somme": "parts.iter().fold(0u64, |a, &b| a.wrapping_add(b))", "min": "parts.iter().fold(u64::MAX, |a, &b| a.min(b))",
               "max": "parts.iter().fold(0u64, |a, &b| a.max(b))"}[red]
        va, vb = self.val(a_, "e"), self.val(b_, "e")
        self.ligne(f"let a0 = ({va}) as u64; let b0 = ({vb}) as u64;")
        self.ligne("let nt = std::thread::available_parallelism().map(|n| n.get() as u64).unwrap_or(1).min(64);")
        self.ligne("if b0.saturating_sub(a0) < 2048 || nt <= 1 {")
        self.niveau += 1
        for x in s[1]:
            self.instr(x)
        self.niveau -= 1
        self.ligne("} else {")
        self.niveau += 1
        self.ligne("let morceau = (b0 - a0 + nt - 1) / nt;")
        corps_rs = self.val(corps_, "e")
        vv = f"v_{ident(var)}"
        self.ligne("let parts: Vec<u64> = std::thread::scope(|sc| {")
        self.ligne("    let fils: Vec<_> = (0..nt).map(|k| sc.spawn(move || {")
        self.ligne("        let mut c_fils = ctx_fils(); let c = &mut c_fils;")
        self.ligne(f"        let mut acc: u64 = {init}; let lo = a0.saturating_add(k * morceau); let hi = lo.saturating_add(morceau).min(b0);")
        self.ligne(f"        let mut i = lo; while i < hi {{ let {vv}: u128 = i as u128; let x: u64 = ({corps_rs}) as u64; acc = {op}; i += 1; }}")
        self.ligne("        acc")
        self.ligne("    })).collect();")
        self.ligne("    fils.into_iter().map(|h| h.join().unwrap()).collect()")
        self.ligne("});")
        self.ligne(f"v_{ident(s_)} = ({pli}) as u128;")
        self.niveau -= 1
        self.ligne("}")

    # ------------------------------------------------------------ adresses
    def adresse(self, et, adr):
        """L'adresse de @et[adr] (comme Generateur.adresse : ETG à la largeur 64, l'adresse courte)."""
        if et is None:
            return self.val(adr, "e")
        if isinstance(et, int):
            return self.b([self.val(adr, "e")], "etg({0}, " + str(et) + ")")
        return self.b([self.val(adr, "e"), self.val(et, "e")], "etg({0}, ({1} & 3) as u32)")

    # ------------------------------------------------------------ conditions
    def cond(self, e):
        self.refuser_logique(e)
        if e[0] == "bin" and e[1] in ("&&", "||"):
            return f"({self.cond(e[2])} {e[1]} {self.cond(e[3])})"
        if e[0] == "non_log":
            return f"!{self.cond(e[1])}"
        if e[0] == "bin" and (e[1] in V.COMPARAISONS or e[1] in V.SIGNEES_COMP):
            return self.comparaison(e)
        t = self.typ(e)
        if t == "p":
            raise VtxError(f"ligne {ligne_de(e)} : un point ne sert pas de condition : comparez-le, ou regardez son état (p.etat)")
        if t == "x":
            raise VtxError(f"ligne {ligne_de(e)} : un flottant_petuar a un état à quatre valeurs et ne sert pas de condition")
        v = self.val(e)
        if t == "f":
            return f"(({v} as u64) & 0x3FFF_FFFF_FFFF_FFFF != 0)"
        if t == "s":
            return f"(({v} as u64) & 0x3FFF_FFFF != 0)"
        if t == "w" or (L() and t != "i"):
            return f"({v} != 0)"
        return f"(({v} as u64) != 0)"

    def comparaison(self, e):
        """Une comparaison : une expression Rust booléenne, avec le sens de Lugus (CMP à la largeur 64 pour les entiers,
        à toute la largeur pour l'entier_128 et le point, FEQ FLT FLE pour les flottants)."""
        op, a, b = e[1], e[2], e[3]
        ta, tb = self.typ(a), self.typ(b)
        if "q" in (ta, tb) or est_ref(ta) or est_ref(tb):
            t = "q" if "q" in (ta, tb) else (ta if est_ref(ta) else tb)
            return self.b([self.val(a, t), self.val(b, t)], "({0} as u64) " + OP_RS[op] + " ({1} as u64)")
        signe = op in V.SIGNEES_COMP
        o = op[1:] if signe else op
        t = self.joindre(ta, tb, ligne_de(e), op)
        pa, pb = self.val(a, t), self.val(b, t)
        if t in FMT:
            F = FMT[t]
            c_ = {"==": "{F}.cmp({0}, {1}) == 0", "!=": "{F}.cmp({0}, {1}) != 0", "<": "{F}.cmp({0}, {1}) == 1",
                  "<=": "{F}.cmp({0}, {1}) < 2", ">": "{F}.cmp({1}, {0}) == 1", ">=": "{F}.cmp({1}, {0}) < 2"}[o]
            return self.bloc([pa, pb], lambda n: c_.format(f"({n[0]} & {F}.masque())", f"({n[1]} & {F}.masque())", F=F))
        if t == "p":
            return self.b([pa, pb], "{0} " + OP_RS[o] + " {1}")
        if t == "w":
            if o in ("==", "!="):
                return self.b([pa, pb], "{0} " + OP_RS[o] + " {1}")
            return self.b([pa, pb], "({0} as i128) " + OP_RS[o] + " ({1} as i128)")
        if signe and t == "i":
            return self.b([pa, pb], "({0} as u32 as i32) " + OP_RS[o] + " ({1} as u32 as i32)")
        if L():
            if signe:
                return self.b([pa, pb], "({0} as i128) " + OP_RS[o] + " ({1} as i128)")
            return self.b([pa, pb], "{0} " + OP_RS[o] + " {1}")
        if signe:
            return self.b([pa, pb], "({0} as u64 as i64) " + OP_RS[o] + " ({1} as u64 as i64)")
        return self.b([pa, pb], "({0} as u64) " + OP_RS[o] + " ({1} as u64)")

    # ------------------------------------------------------------ expressions
    def conv_rs(self, code, t, voulu, ligne):
        if t == voulu or (voulu == "e" and t == "i") or (voulu == "w" and t in V.ENTIERS):
            return code
        if voulu == "f" and t in V.ENTIERS:
            if L() and t != "i":
                return f"Q64.de_entier({code}, 128, false)"
            return f"Q64.de_entier(({code}) & M64, 64, false)"
        if voulu == "f" and t == "s":
            return f"Q32.vers(&Q64, ({code}) & M32)"
        if voulu == "s" and t in V.ENTIERS:
            if L() and t != "i":
                return f"Q64.vers(&Q32, Q64.de_entier({code}, 128, false))"
            return f"Q64.vers(&Q32, Q64.de_entier(({code}) & M64, 64, false))"
        if voulu == "i" and t == "e":
            return code
        raise VtxError(f"ligne {ligne} : conversion implicite impossible de {NOM_TYPE[t]} vers {NOM_TYPE[voulu]}")

    def val(self, e, voulu=None):
        if e[0] == "blit":
            e = ("qnombre", e[1]) if voulu == "q" else ("nombre", e[2])
        if est_ref(voulu) and e == ("nombre", 0):
            return "0u128"
        t = self.typ(e)
        if est_ref(t):
            if e[0] == "nouveau_de":
                code = self.val_e(e[2])
            elif e[0] == "construire":
                parts = [self.val_e(e[3])]
                champs = []
                for champ, v in e[2]:
                    pos = self.structs[e[1]].index(champ)
                    tc = self.types_champs.get(e[1], {}).get(champ, "e")
                    parts.append(self.val(v, tc))
                    champs.append(pos)
                code = self.construire_rs(parts, champs)
            elif e[0] in ("champ_ref", "champ"):
                _st, pos, _t = self.champ_de(e)
                code = self.b([self.val(e[1])], "c.lire({0}.wrapping_add(" + str(pos) + "))")
            else:
                code = self.val_e(e)
            if voulu is not None and voulu != t:
                return self.conv_rs(code, t, voulu, ligne_de(e))
            return code
        if voulu == "x" and t in ("e", "i", "f", "s"):
            return self.conversion("flottant_petuar", [e], ligne_de(e))
        if t in ("e", "i", "q"):
            code = lit(e[1]) if e[0] == "qnombre" else self.val_e(e)
        elif t in FMT:
            code = self.val_fl(e, t)
        elif t == "w":
            code = self.val_w(e)
        elif t == "p":
            code = lit(e[1]) if e[0] == "pnombre" else self.val_e(e)
        else:
            raise VtxError(f"ligne {ligne_de(e)} : type inattendu pour la forge ({t})")
        if voulu is not None and voulu != t:
            return self.conv_rs(code, t, voulu, ligne_de(e))
        return code

    def construire_rs(self, parts, champs):
        n0 = self.tmp()
        s = [f"let {n0}: u128 = {parts[0]};"]
        reste = parts[1:]
        garde = any(MARQUE in c for c in reste)
        if garde:
            s.append(f"c.pousser({n0});")
        for code, p in zip(reste, champs):
            n = self.tmp()
            s.append(f"let {n}: u128 = {code}; c.ecrire({n0}.wrapping_add({p}), {n});")
        if garde:
            s.append("c.sp = c.sp.wrapping_add(1);")
        marque = MARQUE if any(MARQUE in c for c in parts) else ""
        return f"{{ {' '.join(s)} {n0} }}{marque}"

    def var_rs(self, e):
        self.variable(e[1], e[2])
        return f"v_{ident(e[1])}"

    def val_e(self, e):
        """Entier (64 bits), entier_32, logique : le sens des instructions de Lugus à la largeur 64."""
        g = e[0]
        if g in ("nombre", "inombre"):
            return lit(e[1])
        if g == "var":
            return self.var_rs(e)
        if g == "etiq":
            return lit(self.etiq[e[1].upper()])
        if g == "non":
            t = self.typ(e[1])
            v = self.val(e[1])
            if L() and t != "i":
                return f"(!{v})"
            return f"((!({v} as u64) & {'0xFFFF_FFFF' if t == 'i' else 'u64::MAX'}) as u128)"
        if g == "non_log":
            return f"({self.cond(e[1])} as u128 ^ 1)"
        if g == "bin":
            op = e[1]
            if op in ("&&", "||"):
                return f"({self.cond(e)} as u128)"
            if op in V.COMPARAISONS or op in V.SIGNEES_COMP:
                ta, tb = self.typ(e[2]), self.typ(e[3])
                t = None if ("q" in (ta, tb) or est_ref(ta) or est_ref(tb)) else self.joindre(ta, tb, ligne_de(e), op)
                return f"({self.comparaison(e)} as u128)"
            t = self.typ(e)
            a, b = self.val(e[2], "e"), self.val(e[3], "e")
            if op in ("<<q", ">>q"):
                sh = "<<" if op == "<<q" else ">>"
                forme = "((({0} as u64) " + sh + " ((({1} as u64).wrapping_add({1} as u64)) & 63)) as u128)"
                if L() and t != "i":
                    forme = "({0} " + sh + " ({1}.wrapping_add({1}) & 127))"
                if t == "i" and op == "<<q":
                    forme = "(" + forme + " & M32)"
                return self.b([a, b], forme)
            if t == "i" and op in ("./", ".%", ".>>"):
                f_ = {"./": "divs32({0}, {1})", ".%": "mods32({0}, {1})", ".>>": "sar32({0}, {1})"}[op]
                return self.b([a, b], f_)
            forme = {"+": "(({0} as u64).wrapping_add({1} as u64) as u128)",
                     "-": "(({0} as u64).wrapping_sub({1} as u64) as u128)",
                     "*": "(({0} as u64).wrapping_mul({1} as u64) as u128)",
                     "/": "divu64({0}, {1})", "%": "modu64({0}, {1})",
                     "&": "((({0} as u64) & ({1} as u64)) as u128)", "|": "((({0} as u64) | ({1} as u64)) as u128)",
                     "^": "((({0} as u64) ^ ({1} as u64)) as u128)",
                     "<<": "((({0} as u64) << (({1} as u64) & 63)) as u128)",
                     ">>": "((({0} as u64) >> (({1} as u64) & 63)) as u128)",
                     "./": "divs64({0}, {1})", ".%": "mods64({0}, {1})", ".>>": "sar64({0}, {1})"}[op]
            if L() and t != "i":
                forme = {"+": "{0}.wrapping_add({1})", "-": "{0}.wrapping_sub({1})", "*": "{0}.wrapping_mul({1})",
                         "/": "divu128({0}, {1})", "%": "modu128({0}, {1})",
                         "&": "({0} & {1})", "|": "({0} | {1})", "^": "({0} ^ {1})",
                         "<<": "({0} << ({1} & 127))", ">>": "({0} >> ({1} & 127))",
                         "./": "divs128l({0}, {1})", ".%": "mods128l({0}, {1})", ".>>": "sar128({0}, {1})"}[op]
                if esus_actif() and op in ("+", "*", "/", "%"):
                    # 0.835 : Ésus : le codon synonyme : tout tient en 64 bits (prouvé par les bornes) : l'opération de 64
                    # bits, le même résultat (la division et le reste : par une constante non nulle seulement)
                    M64_ = (1 << 64) - 1
                    if borne(e[2]) <= M64_ and borne(e[3]) <= M64_ and borne(e) <= M64_ and (
                            op in ("+", "*") or (e[3][0] == "nombre" and e[3][1] > 0)):
                        f64 = {"+": "(({0} as u64) + ({1} as u64)) as u128", "*": "(({0} as u64) * ({1} as u64)) as u128",
                               "/": "(({0} as u64) / ({1} as u64)) as u128", "%": "(({0} as u64) % ({1} as u64)) as u128"}[op]
                        return self.b([a, b], "(" + f64 + ")")
                if esus_actif() and op in ("+", "-", "*", "./", ".%"):
                    # 0.836 : Ésus en signé : les deux opérandes et le résultat tiennent entre -2^63 et 2^63 - 1
                    # (prouvé) : l'opération de 64 bits signée, puis le signe étendu à 128 bits ; le même résultat
                    pa_, pb_, pe_ = points(e[2]), points(e[3]), points(e)
                    I64 = (-(1 << 63), (1 << 63) - 1)
                    if all(I64[0] <= x[4] and x[5] <= I64[1] for x in (pa_, pb_, pe_)) and (
                            op in ("+", "-", "*") or (e[3][0] == "nombre" and pb_[4] == pb_[5] and pb_[4] not in (0, -1))):
                        g64 = {"+": "wrapping_add", "-": "wrapping_sub", "*": "wrapping_mul", "./": "wrapping_div",
                               ".%": "wrapping_rem"}[op]
                        return self.b([a, b], "(((({0} as u64) as i64)." + g64 + "(({1} as u64) as i64)) as i128 as u128)")
                if op in ("/", "%") and e[3][0] == "nombre" and 0 < e[3][1] < 1 << 128 and esus_actif():
                    return self.b([a], esus_diviser(op, e[3][1]))   # 0.835 : Ésus
            if t == "i" and op in ("+", "-", "*", "<<", "/"):
                forme = "(" + forme + " & M32)"
            return self.b([a, b], forme)
        if g in ("champ", "champ_ref") and isinstance(e[2], str) and self.typ(e[1]) == "p":
            genre, k = V.CHAMPS_POINT[e[2]]
            p = self.val(e[1], "p")
            if genre == "v":
                return self.b([p], "(({0} >> " + str(32 * k) + ") & M32)")
            dec, nb = ((30, 2), (24, 6), (18, 6), (12, 6), (6, 6), (0, 6))[k]
            return self.b([p], "(({0} >> " + str(dec) + ") & " + str((1 << nb) - 1) + ")")
        if g == "champ_ref" or (g == "champ" and est_ref(self.typ(e[1]))):
            _st, pos, _t = self.champ_de(e)
            return self.b([self.val(e[1])], "c.lire({0}.wrapping_add(" + str(pos) + "))")
        if g == "champ":
            x = self.val(e[1])
            dec = CHAMPS[e[2]]
            return self.b([x], "((({0} as u64) >> " + str(dec) + ") & 65535) as u128")
        if g == "quit":
            return self.b([self.val(e[1]), self.val(e[2], "e")], "((({0} as u64) >> ((({1} as u64) & 31) * 2)) & 3) as u128")
        if g == "lire":
            zone = e[3] if len(e) > 3 else None
            if zone is not None and self.plan and zone in self.plan:
                k, ty = self.plan[zone]
                return self.b([self.val(e[2], "e")], gabarit(f"{{ let a = @0; let i = ((a as u64) & 0xFFFF_FFFF_FFFF)"
                                                            f".wrapping_sub({zone[1]}) as usize; if !z{k}.is_null() && i < "
                                                            f"{zone[2] - zone[1]} {{ unsafe {{ *z{k}.add(i) as u128 }} }} else "
                                                            f"{{ c.lire(etg(a, {e[1]})) }} }}"))
            # 0.805 : l'étage 2 par la carte du vergobret
            if e[1] == 2:
                return self.b([self.val(e[2], "e")], "c.lire2({0})")
            if isinstance(e[1], int) and e[2][0] == "nombre":
                return f"c.lire({lit((e[2][1] & ~(3 << 62) & M64) | (e[1] << 62))})"
            return self.b([self.adresse(e[1], e[2])], "c.lire({0})")
        if g == "appel":
            return self.appel(e)
        raise VtxError(f"ligne {ligne_de(e)} : expression inattendue pour la forge ({g})")

    def val_fl(self, e, t):
        """Un flottant quaternaire (32, 64 ou 128 bits), calculé par qflot128.rs comme par Lugus."""
        F = FMT[t]
        g = e[0]
        if g in ("fnombre", "snombre", "xnombre"):
            return lit(e[1])
        if g == "var":
            return self.var_rs(e)
        if g == "bin":
            op = e[1]
            if op == "-" and e[2] in (("nombre", 0), ("fnombre", 0)):
                return self.b([self.val(e[3], t)], F + ".neg({0} & " + F + ".masque())")
            nom = {"+": "add", "-": "sub", "*": "mul", "/": "div"}.get(op)
            if nom is None:
                raise VtxError(f"ligne {ligne_de(e)} : « {op} » ne s'applique pas à un flottant")
            return self.b([self.val(e[2], t), self.val(e[3], t)],
                          F + "." + nom + "({0} & " + F + ".masque(), {1} & " + F + ".masque())")
        if g == "appel":
            return self.appel(e)
        return self.val_e(e)

    def val_w(self, e):
        g = e[0]
        if g == "wnombre":
            return lit(e[1])
        if g == "non":
            return f"(!{self.val(e[1], 'w')})"
        if g == "bin":
            op = e[1]
            forme = {"+": "{0}.wrapping_add({1})", "-": "{0}.wrapping_sub({1})", "*": "{0}.wrapping_mul({1})",
                     "/": "divs128({0}, {1})", "%": "mods128({0}, {1})", "./": "divs128({0}, {1})",
                     ".%": "mods128({0}, {1})", "<<": "{0}.wrapping_shl(({1} & 127) as u32)",
                     ">>": "(({0} as i128) >> ({1} & 127)) as u128", ".>>": "(({0} as i128) >> ({1} & 127)) as u128",
                     "&": "{0} & {1}", "|": "{0} | {1}", "^": "{0} ^ {1}"}.get(op)
            if forme is None:
                raise VtxError(f"ligne {ligne_de(e)} : « {op} » ne s'applique pas à un entier_petuar")
            return self.b([self.val(e[2], "w"), self.val(e[3], "w")], forme)
        return self.val_e(e)

    # ------------------------------------------------------------ appels
    def logique_rs(self, nom, args, ligne):
        t = self.typ(("appel", nom, args, ligne))
        if nom in ("logique", "comme_logique"):
            ta = "q" if args[0][0] == "blit" else self.typ(args[0])
            if ta == "q":
                return self.val(args[0], "q")
            x = self.val(args[0])
            if nom == "comme_logique":
                return f"(({x} as u64) & 3) as u128"
            return f"(if ({x} as u64) == 0 {{ 1u128 }} else {{ 2u128 }})"
        parts = [self.val(args[0], t)] + ([self.val(args[1], t)] if OPS_LOGIQUES[nom] == 2 else [])
        if L() and t == "e":
            if nom in ("et4", "ou4"):
                return self.b(parts, f"{nom}_128({{0}}, {{1}})")
            if nom == "fusion":
                return self.b(parts, "({0} | {1})")
            if nom == "consensus":
                return self.b(parts, "({0} & {1})")
            if nom == "anti":
                return self.b(parts, "anti_128({0})")
            return self.b(parts, "non4_128({0})")
        if nom in ("et4", "ou4"):
            return self.b(parts, f"{nom}_64({{0}}, {{1}})")
        if nom == "fusion":
            return self.b(parts, "((({0} as u64) | ({1} as u64)) as u128)")
        if nom == "consensus":
            return self.b(parts, "((({0} as u64) & ({1} as u64)) as u128)")
        if nom == "anti" and t != "q":
            return self.b(parts, "anti_64({0})")
        if nom == "anti":
            return self.b(parts, "(non4_64({0}) ^ 3)")
        return self.b(parts, "non4_64({0})")

    def appel(self, e):
        nom, args, ligne = e[1], e[2], e[3]
        if nom == "__code_logique":
            return self.val(args[0], "q")
        if nom in OPS_LOGIQUES or nom in ("logique", "comme_logique"):
            return self.logique_rs(nom, args, ligne)
        if nom in INTEGRES:
            if len(args) != INTEGRES[nom]:
                raise VtxError(f"ligne {ligne} : « {nom} » attend {INTEGRES[nom]} argument(s)")
            return self.integre(nom, args, ligne)
        if nom in V.MATHS_128 and any(self.typ(a) == "x" for a in args) and nom not in self.fonctions_du_programme():
            nom = nom + "_128"
            e = ("appel", nom, args, ligne)
        if nom in SURCHARGES and self.typ(e) == "w":
            return self.appel(("appel", "__q" + nom, args, ligne))
        if nom in SURCHARGES and self.typ(e) == "x":
            return self.appel(("appel", "__pq_" + nom, [self.bits_x(a) for a in args], ligne))
        if nom in SURCHARGES and self.typ(e) in ("f", "s", "i"):
            return self.surcharge_rs(nom, args, self.typ(e), ligne)
        if nom in ("afficher", "ecrire", "texte") and len(args) == 1:
            pf = self.fonctions.get(nom) or self.reserve.get(nom)
            if pf is not None and getattr(pf, "origine", "") == "prélude":
                a0 = args[0]
                ta = "q" if a0[0] == "blit" else self.typ(a0)
                if ta in ("i", "f", "s", "q", "w", "x", "p"):
                    nom = "__" + nom + "_" + ta
        f = self.signature(nom, ligne)
        if len(args) != len(f.params):
            raise VtxError(f"ligne {ligne} : « {nom} » attend {len(f.params)} argument(s)")
        self.appelees.add(nom)
        parts = [self.val(a, t) for a, t in zip(args, f.ptypes)]
        ramasse = self.peut_ramasser(nom)
        avant = self.recopier_cadre() if ramasse else ""

        def fin(n):
            appel = f"f_{ident(nom)}(c{''.join(', ' + x for x in n)})"
            return f"{{ {avant}{appel} }}" if avant else appel
        code = self.bloc(parts, fin) if parts else f"({fin([])})"
        return code + MARQUE if ramasse and MARQUE not in code else code

    def integre(self, nom, args, ligne):
        a = args
        e1 = lambda: self.val(a[0], "e")  # noqa: E731
        if nom == "sortie":
            return self.b([self.val(a[0])], "{{ c.m.sortie.push({0}); 0u128 }}")
        if nom == "__rompre":
            # un contrat rompu : comme HALT, la machine s'arrête (ce qui est en mémoire, les sorties et le texte restent)
            return "{ (c.vider)(c); finir(c); std::process::exit(0) }"
        if nom == "entrée":
            return "c.m.entree.pop_front().unwrap_or(0)"
        if nom == "cmp3":
            if L():
                return self.b([e1()], "(!{0})")
            return self.b([e1()], "((!({0} as u64)) as u128)")
        if nom == "lire_car":
            return self.b([e1()], "(c.m.lire_canal({0})" + ("" if L() else " & M64") + ")")
        if nom == "ecrire_car":
            return self.b([self.val(a[1], "e"), e1()], "{{ c.m.ecrire_canal({1}, {0}); 0u128 }}")
        if nom in ("ouvrir_lecture", "ouvrir_ecriture", "fermer", "fin_de"):
            code = {"ouvrir_lecture": 1, "ouvrir_ecriture": 2, "fermer": 3, "fin_de": 4}[nom]
            return self.b([e1()], "(c.sys(" + str(code) + ", {0})" + ("" if L() else " & M64") + ")")
        if nom == "bruit":
            return "(c.sys(5, 0)" + ("" if L() else " & M64") + ")"
        if nom == "pile":
            self.appelees.add("<pile>")
            return "c.sp"
        if nom == "__service":
            return self.b([e1(), self.val(a[1], "e")], "(c.sys({0}, {1})" + ("" if L() else " & M64") + ")")
        if nom == "nb_bits":
            if L():
                return self.b([e1()], "({0}.count_ones() as u128)")
            return self.b([e1()], "(({0} as u64).count_ones() as u128)")
        if nom == "qegal":
            return self.b([e1(), self.val(a[1], "e")], ("qegal_128" if L() else "qegal_64") + "({0}, {1})")
        if nom in ("min4", "max4", "addm4"):
            return self.b([e1(), self.val(a[1], "e")], ("quits_128" if L() else "quits_64") + "({0}, {1}, " + str({"min4": 0, "max4": 1, "addm4": 2}[nom]) + ")")
        if nom == "gdot":
            return self.b([e1(), self.val(a[1], "e")], "gdot_64({0}, {1})")
        if nom == "mul_haut" and L():
            return self.b([e1(), self.val(a[1], "e")], "mulhu128({0}, {1})")
        if nom == "mul_haut_signe" and L():
            return self.b([e1(), self.val(a[1], "e")], "mulhs128l({0}, {1})")
        if nom == "mul_haut":
            return self.b([e1(), self.val(a[1], "e")], "((({0} as u64 as u128) * ({1} as u64 as u128)) >> 64)")
        if nom == "mul_haut_signe":
            return self.b([e1(), self.val(a[1], "e")], "(((({0} as u64 as i64 as i128) * ({1} as u64 as i64 as i128)) >> 64) as u64 as u128)")
        if nom == "brin":
            return self.b([e1()], "c.m.brin({0})")
        if nom in ("marquer_adn", "marquer_arn", "liberer_brin"):
            q = {"marquer_adn": 1, "marquer_arn": 2, "liberer_brin": 0}[nom]
            return self.b([e1(), self.val(a[1], "e")], "{{ c.marquer({0}, {1}, " + str(q) + "); 0u128 }}")
        if nom == "gemv":
            raise VtxError(f"ligne {ligne} : la forge de Lugus ne traduit pas encore gemv()")
        return self.conversion(nom, args, ligne)

    def fonction_point(self, nom, args, ligne):
        if nom in ("point", "point32", "matiere"):
            base = V.MATIERE_DEFAUT if nom == "point" else 2 << 30
            parts = [self.val(x, "e") for x in args]
            vs = []
            for k in range(3):
                if nom == "point":
                    vs.append(f"(((({{{k}}} as u64) & 255) * 16843009) as u128 & M32) << {32 * (3 - k)}")
                else:
                    vs.append(f"(({{{k}}} & M32) << {32 * (3 - k)})")
            forme = f"({base}u128 | " + " | ".join(vs) + ")"
            for k in range(3, len(args)):
                dec, nb = ((30, 2), (24, 6), (18, 6), (12, 6), (6, 6), (0, 6))[k - 2]
                forme = f"mate({forme}, {{{k}}}, {dec}, {nb})"
            return self.b(parts, forme)
        if nom == "comme_point":
            return self.val(args[0])
        if nom == "melanger":
            p = args[2]
            if p[0] != "nombre" or p[1] > 256:
                raise VtxError(f"ligne {ligne} : melanger(a, b, poids) : le poids est un nombre écrit, de 0 à 256")
            return self.b([self.val(args[0], "p"), self.val(args[1], "p")], "melange({0}, {1}, " + str(p[1]) + ")")
        if nom == "antipoint":
            return self.b([self.val(args[0], "p")], "({0} ^ (((1u128 << 96) - 1) << 32))")
        k = V.CODONS_AVEC[nom]
        dec, nb = ((30, 2), (24, 6), (18, 6), (12, 6), (6, 6), (0, 6))[k]
        return self.b([self.val(args[0], "p"), self.val(args[1], "q" if nom == "avec_etat" else "e")],
                      "mate({0}, {1}, " + f"{dec}, {nb})")

    def conversion(self, nom, args, ligne):
        if nom in V.RETOURS and V.RETOURS[nom] == "p":
            return self.fonction_point(nom, args, ligne)
        x = args[0]
        t = self.typ(x)

        def interdit():
            raise VtxError(f"ligne {ligne} : « {nom} » ne s'applique pas à un {NOM_TYPE[t]}")
        v = lambda voulu=None: self.val(x, voulu)  # noqa: E731
        if nom in ("flottant_petuar", "flottant_128"):
            if t not in V.X_DEPUIS:
                interdit()
            return {"x": v(), "e": f"Q128.de_entier({v()}, {128 if L() else 64}, false)", "i": f"Q128.de_entier({v()}, 32, false)",
                    "f": f"Q64.vers(&Q128, {v()} & M64)", "s": f"Q32.vers(&Q128, {v()} & M32)",
                    "w": f"Q128.de_entier({v()}, 128, true)"}[t]
        if nom == "comme_flottant_petuar":
            if t not in ("w", "e", "i", "x"):
                interdit()
            return v()
        if nom == "__mot128":
            return v()
        if nom == "flottant_petuar_signe":
            if t not in V.ENTIERS:
                interdit()
            return f"Q128.de_entier({v()}, {(128 if L() else 64) if t == 'e' else 32}, true)"
        if nom == "vers_ieee128":
            if t != "x":
                interdit()
            return f"Q128.vers_ieee({v()})"
        if nom == "de_ieee128":
            if t != "w":
                interdit()
            return f"Q128.de_ieee({v()})"
        if t == "x":
            c = v()
            if nom == "bits":
                return c
            return {"racine": f"Q128.racine({c})", "flottant": f"Q128.vers(&Q64, {c})",
                    "flottant_64": f"Q128.vers(&Q64, {c})", "flottant_32": f"Q128.vers(&Q32, {c})",
                    "entier_128": f"Q128.vers_entier({c}, false, 128)", "entier_petuar": f"Q128.vers_entier({c}, false, 128)",
                    "entier": f"Q128.vers_entier({c}, false, {128 if L() else 64})",
                    "arrondi": f"Q128.vers_entier({c}, true, {128 if L() else 64})",
                    "entier_32": f"(Q128.vers_entier({c}, false, 128) & M32)"}.get(nom) or interdit()
        if nom in ("flottant", "flottant_64"):
            if t == "w":
                return f"Q128.vers(&Q64, Q128.de_entier({v()}, 128, true))"
            if t not in ("e", "i", "f", "s"):
                interdit()
            if L() and t == "e":
                return f"Q64.de_entier({v()}, 128, false)"
            return {"e": f"Q64.de_entier({v()} & M64, 64, false)", "i": f"Q64.de_entier({v()} & M64, 64, false)",
                    "s": f"Q32.vers(&Q64, {v()} & M32)", "f": v()}[t]
        if nom == "flottant_32":
            if t not in ("e", "i", "f", "s"):
                interdit()
            if L() and t == "e":
                return f"Q64.vers(&Q32, Q64.de_entier({v()}, 128, false))"
            return {"e": f"Q64.vers(&Q32, Q64.de_entier({v()} & M64, 64, false))",
                    "i": f"Q64.vers(&Q32, Q64.de_entier({v()} & M64, 64, false))",
                    "f": f"Q64.vers(&Q32, {v()} & M64)", "s": v()}[t]
        if nom == "flottant_signe":
            if t not in V.ENTIERS:
                interdit()
            if t == "i":
                return f"Q64.de_entier(sext32({v()}), 64, true)"
            if L():
                return f"Q64.de_entier({v()}, 128, true)"
            return f"Q64.de_entier({v()} & M64, 64, true)"
        if nom in ("entier", "entier_32"):
            c = v()
            n = 128 if L() else 64
            if t == "w":
                c = c if L() else f"({c} & M64)"
            elif t == "s":
                c = f"Q64.vers_entier(Q32.vers(&Q64, {c} & M32), false, {n})"
            elif t == "f":
                c = f"Q64.vers_entier({c} & M64, false, {n})"
            return f"({c} & M32)" if nom == "entier_32" else c
        if nom == "arrondi":
            if t == "s":
                return f"Q64.vers_entier(Q32.vers(&Q64, {v()} & M32), true, {128 if L() else 64})"
            if t == "f":
                return f"Q64.vers_entier({v()} & M64, true, {128 if L() else 64})"
            interdit()
        if nom == "racine":
            if t == "s":
                return f"Q32.racine({v()} & M32)"
            return f"Q64.racine({v('f')} & M64)"
        if nom in ("comme_flottant", "comme_flottant_32", "bits"):
            if t in ("w", "q") or (nom != "bits" and t not in V.ENTIERS):
                interdit()
            return f"({v()} & M32)" if nom == "comme_flottant_32" else v()
        if nom == "vers_ieee64":
            if t != "f":
                interdit()
            return f"Q64.vers_ieee({v()} & M64)"
        if nom == "de_ieee64":
            if t not in V.ENTIERS:
                interdit()
            return f"Q64.de_ieee({v()} & M64)"
        if nom in ("entier_128", "entier_petuar"):
            if t == "f":
                return f"Q64.vers_entier({v()} & M64, false, 128)"
            if t == "s":
                return f"Q32.vers_entier({v()} & M32, false, 128)"
            if t not in ("e", "i", "w", "p"):
                interdit()
            return v()
        if nom in ("entier_128_signe", "entier_petuar_signe"):
            if t not in V.ENTIERS:
                interdit()
            return f"({v()} as u32 as i32 as i128 as u128)" if t == "i" else f"({v()} as u64 as i64 as i128 as u128)"
        if nom in ("entier_128_de", "entier_petuar_de"):
            return self.b([self.val(args[0], "e"), self.val(args[1], "e")], "(({0} << 64) | {1})")
        if nom in ("bas", "haut"):
            if t not in ("w", "x"):
                interdit()
            return f"({v()} & M64)" if nom == "bas" else f"({v()} >> 64)"
        raise VtxError(f"ligne {ligne} : « {nom} » : conversion inconnue de la forge")

    def surcharge_rs(self, nom, args, t, ligne):
        if nom == "abs":
            c = self.val(args[0], t)
            if t == "i":
                return self.b([c], "(if ({0} & 0x8000_0000) != 0 {{ ((0u64.wrapping_sub({0} as u64)) as u128) & M32 }} else {{ {0} }})")
            F = FMT[t]
            return self.b([c], "(if " + F + ".etat({0} & " + F + ".masque()) == 1 {{ " + F + ".neg({0} & " + F + ".masque()) }} else {{ {0} }})")
        parts = [self.val(args[0], t), self.val(args[1], t)]
        if t == "i":
            moins = "(({a} as u32 as i32) < ({b} as u32 as i32))"
        else:
            F = FMT[t]
            moins = F + ".cmp({a} & " + F + ".masque(), {b} & " + F + ".masque()) == 1"
        if nom == "min":
            return self.bloc(parts, lambda m: f"if {moins.format(a=m[1], b=m[0])} {{ {m[1]} }} else {{ {m[0]} }}")
        return self.bloc(parts, lambda m: f"if {moins.format(a=m[0], b=m[1])} {{ {m[1]} }} else {{ {m[0]} }}")

    # ------------------------------------------------------------ le programme
    def forger(self):
        self.forgees = list(self.fonctions.values())
        self.ramasse = None
        k = 0
        while k < len(self.forgees):          # premier passage : qui appelle qui ; qui lit la pile
            self.fonction_rs(self.forgees[k])
            k += 1
        ramasse = {n for n, a in self.graphe.items() if "<pile>" in a}
        change = True
        while change:
            change = False
            for n, a in self.graphe.items():
                if n not in ramasse and a & ramasse:
                    ramasse.add(n)
                    change = True
        self.ramasse = ramasse
        membrane(self.forgees)   # 0.837 : les cellules : ce qui passe la membrane de chaque molécule
        self.noyaux = []
        self.plan = planifier_zones(self.forgees, self.ecrits, bool(self.blobs and any(v for _, _, v in self.blobs)),
                                    self.blobs)
        return [self.fonction_rs(f) for f in self.forgees]


# ------------------------------------------------------------------------------------------------------------------
# L'adaptation automatique : un tableau que seul son nom touche (aucun accès par @, aucune référence, aucun service qui
# lit la mémoire, aucun brin posé) est rangé hors du cube, dans un tableau Rust serré, du plus petit type qui tient ce
# qu'on y écrit : des nombres écrits jusqu'à 255 dans des octets, des entiers de 64 bits dans des u64, le reste en u128.
# À la fin (ou à une erreur), son contenu est recopié dans le cube : la mémoire finale est celle de la machine.
SERVICES_MEMOIRE = {6, 7, 11, 12, 13, 22}          # ils lisent ou écrivent la mémoire du programme
TYPES_64 = {"e", "i", "s", "q"}


def gabarit(t):
    """Un morceau de Rust écrit avec @0, @1 pour les valeurs : la forme de bloc() (accolades doublées)."""
    return t.replace("{", "{{").replace("}", "}}").replace("@0", "{0}").replace("@1", "{1}")


def _parcourir(n, f):
    if isinstance(n, tuple):
        f(n)
        for x in n:
            _parcourir(x, f)
    elif isinstance(n, list):
        for x in n:
            _parcourir(x, f)


def planifier_zones(fonctions, ecrits, _blobs_presents, blobs):
    zones, bruts, refus = set(), [], [False]

    def voir(n):
        g = n[0] if n and isinstance(n[0], str) else None
        if g == "lire" and len(n) in (3, 4):
            if len(n) == 4 and isinstance(n[3], tuple):
                zones.add(n[3])
            else:
                bruts.append((n[1], n[2]))
        elif g == "ecrire" and len(n) >= 5:
            if len(n) > 5 and isinstance(n[5], tuple):
                zones.add(n[5])
            else:
                bruts.append((n[1], n[2]))
        elif g in ("champ_ref", "ecrire_champ"):
            bruts.append((None, None))
        elif g == "appel" and len(n) > 2 and isinstance(n[1], str):
            nom, args = n[1], n[2]
            if nom in ("marquer_adn", "marquer_arn", "liberer_brin", "pile", "gemv") or nom.startswith("ranger") \
                    or nom.startswith("jeter") or nom.startswith("sauver") or nom.startswith("charger"):
                refus[0] = True
            if nom == "__service":
                c = args[0] if args else None
                if not (isinstance(c, tuple) and c[0] == "nombre" and c[1] not in SERVICES_MEMOIRE):
                    refus[0] = True
    for f in fonctions:
        _parcourir(f.corps, voir)
    for et, adr, vals in blobs:
        if vals:
            bruts.append((et, ("intervalle", adr, adr + len(vals))))
    if refus[0] or any(et is None or not isinstance(et, int) for et, _ in bruts):
        return {}
    plan = {}
    for z in sorted(zones):
        et, debut, fin = z
        if et == 0 or fin - debut < 64:
            continue
        if any(z2 != z and z2[0] == et and z2[1] < fin and debut < z2[2] for z2 in zones):
            continue
        touche = False
        for e2, a2 in bruts:
            if e2 != et:
                continue
            if a2[0] == "nombre":
                touche = touche or debut <= (a2[1] & 0xFFFF_FFFF_FFFF) < fin
            elif a2[0] == "intervalle":
                touche = touche or (a2[1] < fin and debut < a2[2])
            else:
                touche = True
        if touche:
            continue
        vus = ecrits.get(z, [])
        if vus and all(isinstance(v, int) for v in vus):
            m = max(vus)
            ty = "u8" if m < 1 << 8 else "u16" if m < 1 << 16 else "u32" if m < 1 << 32 else "u64" if m < 1 << 64 else "u128"
        elif all(isinstance(v, int) and v < 1 << 64 or v in TYPES_64 and not (v == "e" and L()) for v in vus):
            # 0.833 : l'entier par défaut a 128 bits : un tableau d'entiers reste en u128 (u64 avec « dunon; »)
            ty = "u64"
        else:
            ty = "u128"
        plan[z] = (len(plan), ty)
    return plan


def code_zones(plan):
    """Les tableaux serrés : leur place, leur départ (vide, ou le cube s'il en existe sur disque pour leur étage : alors
    ils restent dans le cube) et leur recopie dans le cube."""
    s = []
    for (et, debut, fin), (k, ty) in sorted(plan.items(), key=lambda x: x[1][0]):
        s.append(f"static mut Z{k}: *mut {ty} = std::ptr::null_mut();\nstatic mut ZA{k}: bool = false;")
    s.append("fn debuter_zones(c: &mut Ctx) {")
    s.append("    let disque = |e: u32| c.m.dossier.as_ref().map(|d| std::fs::read_dir(d).map(|l| l.flatten().any(|f| "
             "f.file_name().to_string_lossy().starts_with(&format!(\"cube128-{}-\", e)))).unwrap_or(false)).unwrap_or(false);")
    for (et, debut, fin), (k, ty) in sorted(plan.items(), key=lambda x: x[1][0]):
        s.append(f"    if !disque({et}) {{ unsafe {{ Z{k} = Box::leak(vec![0{ty}; {fin - debut}].into_boxed_slice()).as_mut_ptr(); "
                 f"ZA{k} = true; }} }}")
    s.append("}")
    s.append("fn vider_zones(c: &mut Ctx) {")
    for (et, debut, fin), (k, ty) in sorted(plan.items(), key=lambda x: x[1][0]):
        s.append(f"    unsafe {{ if ZA{k} {{ ZA{k} = false; for i in 0..{fin - debut}usize {{ let v = *Z{k}.add(i) as u128; "
                 f"if v != 0 {{ let _ = c.m.ecrire_mem(etg({debut}u128 + i as u128, {et}), v); }} }} }} }}")
    s.append("}")
    return "\n".join(s)


ATTRIBUTS = ("#![allow(unused_mut, unused_variables, unused_assignments, unreachable_code, unused_parens, dead_code, "
             "clippy::all, non_snake_case, unused_imports, unused_labels, unused_braces)]")
MODULES = ["qflot128", "spu128", "hote", "miroir", "taranis_vk", "gif", "sortie"]     # recopiés de vtx-rs/src
# (0.78 : gif et sortie, la fenêtre : un programme forgé présente lui-même ses images)


def carte_directe(sortie=None):
    """0.830 : le gène « carte_directe » (Gutuater, à la forge) : VTX_CARTE_DIRECTE=1 ou 0 l'impose ; sinon l'ARN de
    Gutuater à côté du programme forgé (« carte_directe 0 vrai ») ; sinon faux (la carte mêlée, comme avant)"""
    v = os.environ.get("VTX_CARTE_DIRECTE")
    if v in ("0", "1"):
        return v == "1"
    if sortie and os.environ.get("VTX_GUTUATER") != "0":
        arn = os.path.join(os.path.dirname(os.path.abspath(sortie)), "gutuater.arn")
        if os.path.exists(arn):
            for l in open(arn, encoding="utf-8"):
                m = l.split()
                if len(m) >= 3 and m[0] == "carte_directe" and m[1] == "0":
                    print(f"gutuater : la carte directe : {m[2]} ({'65 536 places' if m[2] == 'vrai' else '1 024 places mêlées'})",
                          file=sys.stderr)
                    return m[2] == "vrai"
    return False


def noyau(sortie=None):
    src = os.path.join(racine, "vtx-rs", "src")
    mods = []
    for m in MODULES:
        texte = open(os.path.join(src, m + ".rs"), encoding="utf-8").read()
        mods.append(f"#[allow(dead_code, unused_imports, unused_variables)]\nmod {m} {{\n{texte}\n}}\n")
    n = open(os.path.join(ici, "noyau_forge128.rs"), encoding="utf-8").read()
    if carte_directe(sortie):
        n = n.replace("const CARTE_DIRECTE: bool = false;", "const CARTE_DIRECTE: bool = true;", 1)
    return ATTRIBUTS + "\n" + n.replace("// @MODULES@", "\n".join(mods), 1)


def programme_rust(src, dossier=None, nom="programme"):
    """Le programme forgé (sans le noyau) : ses mots, ses fonctions, et lancer() qui le joue avec des entrées."""
    g, mots, etiquettes = compiler_arbre(src, dossier)
    fo = Forge(g, etiquettes)
    fo.nom_programme = nom
    fonctions = fo.forger()
    s = [f"const NOM: &str = {nom!r};".replace("'", '"'),
         f"const FIN_CODE: u128 = {etiquettes['FIN_CODE']};",
         f"static MOTS: [u128; {len(mots)}] = [" + ",".join(str(w) for w in mots) + "];\n"]
    s += [x.replace(MARQUE, "") for x in fonctions]
    s.append(code_zones(fo.plan or {}))
    # 0.810 : le réglage de chaque boucle « en bandes » (le vergobret mesure)
    for r, h in sorted(set(getattr(fo, "reglages", []))):
        s.append(f"#[allow(dead_code)]\nstatic {r}: Reglage = Reglage::neuf({h}u64);")
    # 0.816 : le choix de la carte ou du processeur, pour chaque boucle qui sait aller à la carte
    for r in sorted(set(getattr(fo, "choix", []))):
        s.append(f"#[allow(dead_code)]\nstatic {r}: Choix = Choix::neuf();")
    for k, spv in enumerate(fo.noyaux):
        mots = [int.from_bytes(spv[i:i + 4], "little") for i in range(0, len(spv), 4)]
        s.append(f"#[allow(dead_code)]\nstatic SPV{k}: [u32; {len(mots)}] = [" + ",".join(map(str, mots)) + "];")
    # la machine d'un fil (les vagues sur plusieurs cœurs) : sa mémoire à elle, le programme chargé (textes et constantes)
    s.append("#[allow(dead_code)]\nfn ctx_fils() -> Ctx {\n    let mut m = Spu128::nouveau();\n    m.charger(&MOTS);\n"
             "    Ctx { m, sp: spu128::PILE, cl: [u128::MAX; 64], pl: [std::ptr::null_mut(); 64], ce: [u128::MAX; 64], carte: Carte::neuve(),\n"
             "          pe: [std::ptr::null_mut(); 64], pb: [std::ptr::null_mut(); 64], rb: [std::ptr::null_mut(); 64], wb: [std::ptr::null_mut(); 64], vider: |_c| {}, ombre: None }\n}")
    # la machine d'un cylindre : celle d'un fil, qui lit le cube commun et n'écrit que dans le sien
    # 0.74b : les machines des cylindres sont gardées d'un passage à l'autre (une machine neuve remettait à zéro deux
    # pages d'un mégaoctet, le code et la pile, à chaque passage et dans chaque fil)
    s.append("#[allow(dead_code)]\nfn ctx_cylindre(inst: &Instantane) -> Box<Ctx> {\n"
             "    let mut c = match CTX_RESERVE.lock().unwrap().pop() { Some(EnvoiCtx(c)) => c, None => Box::new(ctx_fils()) };\n"
             "    c.sp = spu128::PILE; c.cl = [u128::MAX; 64]; c.ce = [u128::MAX; 64]; c.pb = [std::ptr::null_mut(); 64]; c.rb = [std::ptr::null_mut(); 64]; c.wb = [std::ptr::null_mut(); 64]; c.carte.oublier();\n"
             "    c.ombre = Some(Box::new(Cylindre { commun: inst as *const Instantane, feuilles: Default::default(), "
             "lus: Default::default(), vues: Default::default(), partage: false, ecrits: Default::default(), danger: false }));\n    c\n}")
    # 0.77 : la machine d'un cœur « en bandes » : il écrit directement dans le cube commun
    s.append("#[allow(dead_code)]\nfn ctx_bande(inst: &Instantane) -> Box<Ctx> {\n    let mut c = ctx_cylindre(inst);\n"
             "    c.ombre.as_mut().unwrap().partage = true;\n    c\n}")
    s.append(code_druide())
    s.append("pub fn lancer(entrees: &[String]) {\n    lancer_programme(f_principal, debuter_zones, vider_zones, &MOTS, FIN_CODE, "
             "NOM, entrees, druide_fin);\n}\n")
    return "\n".join(s), mots


def code_druide():
    """0.835 : les compteurs des molécules (VTX_DRUIDE=poids) et druide_fin, que le noyau appelle à la fin : PROG.poids
    (« molécule travail ») et PROG.temps (le temps du programme, en microsecondes), à côté de l'exécutable"""
    mode = druide_mode()
    noms = DRUIDE_NOMS[0]
    out = []
    n = max(1, len(noms))
    out.append("#[allow(dead_code)]\nstatic POIDS: [std::sync::atomic::AtomicU64; %d] = { const Z: std::sync::atomic::AtomicU64 = "
               "std::sync::atomic::AtomicU64::new(0); [Z; %d] };" % (n, n))
    out.append("#[allow(dead_code)]\nconst NOMS_POIDS: [&str; %d] = [%s];" % (len(noms), ", ".join('"%s"' % x for x in noms)))
    obs = DRUIDE_OBS[0]
    no = max(1, len(obs))
    out.append("#[allow(dead_code)]\nstatic OBS: [std::sync::Mutex<(u128, u128, i128, i128, u64)>; %d] = { const Z: "
               "std::sync::Mutex<(u128, u128, i128, i128, u64)> = std::sync::Mutex::new((u128::MAX, 0, i128::MAX, i128::MIN, 0)); "
               "[Z; %d] };" % (no, no))
    out.append("#[allow(dead_code)]\nconst NOMS_OBS: [&str; %d] = [%s];" % (len(obs), ", ".join('"%s %s"' % x for x in obs)))
    out.append("#[allow(dead_code)]\n#[inline(never)]\nfn observer(k: usize, v: u128) {\n    if let Ok(mut g) = OBS[k].lock() {\n"
               "        let s = v as i128;\n        if v < g.0 { g.0 = v; }\n        if v > g.1 { g.1 = v; }\n"
               "        if s < g.2 { g.2 = s; }\n        if s > g.3 { g.3 = s; }\n        g.4 += 1;\n    }\n}")
    out.append("#[allow(unused_variables)]\nfn druide_fin(us: u128) {")
    if mode in ("poids", "1"):
        out.append("    use std::io::Write;")
        out.append("    let exe = match std::env::current_exe() { Ok(e) => e, Err(_) => return };")
    if mode == "1":
        # le temps seul : la passe des poids (ses compteurs pèsent) n'écrit pas de temps
        out.append("    if let Ok(mut f) = std::fs::File::create(exe.with_extension(\"temps\")) { let _ = writeln!(f, \"temps {}\", us); }")
    if mode == "poids":
        out.append("    if let Ok(mut f) = std::fs::File::create(exe.with_extension(\"poids\")) {")
        out.append("        for (k, n) in NOMS_POIDS.iter().enumerate() {")
        out.append("            let _ = writeln!(f, \"{} {}\", n, POIDS[k].load(std::sync::atomic::Ordering::Relaxed));")
        out.append("        }")
        out.append("    }")
        # 0.836 : ce que les variables ont vraiment pris (PROG.observe : molécule variable bas haut petit grand fois)
        out.append("    if let Ok(mut f) = std::fs::File::create(exe.with_extension(\"observe\")) {")
        out.append("        let sx = |v: i128| if v < 0 { format!(\"-{:x}\", v.unsigned_abs()) } else { format!(\"{:x}\", v) };")
        out.append("        for (k, n) in NOMS_OBS.iter().enumerate() {")
        out.append("            if let Ok(g) = OBS[k].lock() { if g.4 > 0 { let _ = writeln!(f, \"{} {:x} {:x} {} {} {}\", n, g.0, g.1, sx(g.2), sx(g.3), g.4); } }")
        out.append("        }")
        out.append("    }")
    out.append("}")
    return "\n".join(out)


def source_rust(src, dossier=None, nom="programme", sortie=None):
    """Le programme Rust complet d'un programme vtx."""
    ESUS_RELEVE[0] = []
    DRUIDE_NOMS[0] = []
    DRUIDE_OBS[0] = []
    ESUS_ETEINT[0] = lire_arn_druide(os.path.splitext(sortie)[0] + ".arn") if sortie else set()
    DEPLIER[0] = lire_deplier(os.path.splitext(sortie)[0] + ".arn") if sortie else {}
    prog, mots = programme_rust(src, dossier, nom)
    main = "\nfn main() {\n    let a: Vec<String> = std::env::args().collect();\n    lancer(&a[1..]);\n}\n"
    return noyau(sortie) + "\n" + prog + main, mots


def rustc_options(natif=False):
    o = ["--edition", "2021", "-C", "opt-level=3", "-C", "panic=abort", "-C", "codegen-units=1"]
    if natif:
        o += ["-C", "target-cpu=native"]
    return o


VERSION_RUSTC = [None]


def rustc_version():
    if VERSION_RUSTC[0] is None:
        try:
            VERSION_RUSTC[0] = subprocess.run(["rustc", "--version"], capture_output=True, text=True).stdout.strip()
        except OSError:
            VERSION_RUSTC[0] = "?"
    return VERSION_RUSTC[0]


def forger_fichier(chemin, sortie=None, rs=None, natif=False):
    src = open(chemin, encoding="utf-8").read()
    ext = ".exe" if os.name == "nt" else ""
    sortie = sortie or os.path.splitext(chemin)[0] + ".lugus" + ext
    code, _ = source_rust(src, os.path.dirname(os.path.abspath(chemin)), os.path.splitext(os.path.basename(chemin))[0],
                          sortie)
    garder = rs is not None
    rs = rs or os.path.join(tempfile.mkdtemp(prefix="forge128-"), "programme.rs")
    with open(rs, "w", encoding="utf-8") as f:
        f.write(code)
    rustc = shutil.which("rustc")
    if not rustc:
        raise VtxError("rustc introuvable : la forge passe par le compilateur Rust (rustup.rs)")
    # 0.838 : le grenier : un exécutable déjà forgé depuis exactement le même texte Rust (et les mêmes options) est
    # repris tel quel ; les générations du Druide (le parent et la variante, tour à tour) ne se recompilent plus
    grenier = os.path.join(os.path.dirname(os.path.abspath(sortie)), ".grenier")
    cle = hashlib.sha256((code + "\0" + " ".join(rustc_options(natif)) + "\0" + rustc_version()).encode("utf-8")).hexdigest()[:32]
    garde = os.path.join(grenier, cle + ext)
    if os.environ.get("VTX_GRENIER") != "0" and os.path.exists(garde):
        shutil.copy2(garde, sortie)
        os.utime(garde)
        print("forge : repris du grenier (le même texte Rust)", file=sys.stderr)
    else:
        r = subprocess.run([rustc] + rustc_options(natif) + ["-o", sortie, rs], capture_output=True, text=True)
        if r.returncode:
            raise VtxError("rustc a refusé le programme forgé :\n" + r.stderr[-3000:])
        if os.environ.get("VTX_GRENIER") != "0":
            try:
                os.makedirs(grenier, exist_ok=True)
                shutil.copy2(sortie, garde)
                gardes = sorted((os.path.join(grenier, x) for x in os.listdir(grenier)), key=os.path.getmtime)
                for x in gardes[:-16]:
                    os.remove(x)   # seize exécutables gardés au plus, les plus anciens partent
            except OSError:
                pass
    if not garder:
        shutil.rmtree(os.path.dirname(rs), ignore_errors=True)
    ecrire_releve_esus(os.path.splitext(sortie)[0] + ".esus", os.path.basename(chemin))
    ecrire_cellules(os.path.splitext(sortie)[0] + ".cellules")
    return sortie


CELLULES = [{}]   # 0.837 : molécule du programme -> (membrane ouverte ?, les molécules du programme qu'elle appelle)


def ecrire_cellules(chemin):
    """0.837 : les cellules du programme, pour le Druide : chaque molécule (hors prélude), sa membrane (ouverte : ses
    paramètres reçoivent ce que ses appelants y mettent ; fermée sinon), les molécules qu'elle appelle"""
    if not CELLULES[0]:
        return
    lignes = [f"# les cellules ({128 if L() else 64} bits) : molécule membrane (ouverte|fermee) empreinte appelle…"]
    for n, (ouv, app, emp) in CELLULES[0].items():
        lignes.append(f"{n} {'ouverte' if ouv else 'fermee'} {emp} " + " ".join(sorted(app)))
    with open(chemin, "w", encoding="utf-8") as f:
        f.write("\n".join(l.rstrip() for l in lignes) + "\n")


def ecrire_releve_esus(chemin, programme):
    """0.835 : le relevé d'Ésus à côté de l'exécutable : pour chaque variable entière de chaque molécule, ses quatre
    points (le plus bas, le plus haut, les bits sûrement à 0, sûrement à 1, en hex) ; le Druide les rangera dans le
    cube (les quatre étages d'une fréquence) et les apprendra d'une forge à l'autre."""
    if not ESUS_RELEVE[0] and L():
        return
    lignes = [f"# Ésus : les quatre points des variables de {programme} (molécule variable bas haut zéros uns, puis le plus petit et le plus grand avec le signe)"]
    vus = {}
    for r in ESUS_RELEVE[0]:
        vus[(r[0], r[1])] = r          # une molécule forgée deux fois : son dernier relevé
    def sx(v):
        return f"-{-v:x}" if v < 0 else f"{v:x}"
    for mol, var, bas, haut, z, o, sb, sh in vus.values():
        lignes.append(f"{mol} {var} {bas:x} {haut:x} {z:x} {o:x} {sx(sb)} {sx(sh)}")
    with open(chemin, "w", encoding="utf-8") as f:
        f.write("\n".join(lignes) + "\n")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--aide"):
        print(__doc__)
        sys.exit(0)
    sortie = rs = None
    natif = "--natif" in args
    args = [a for a in args if a != "--natif"]
    if "-o" in args:
        i = args.index("-o")
        sortie = args[i + 1]
        del args[i:i + 2]
    if "--rs" in args:
        i = args.index("--rs")
        rs = args[i + 1]
        del args[i:i + 2]
    try:
        exe = forger_fichier(args[0], sortie, rs, natif)
    except VtxError as e:
        print("erreur :", e, file=sys.stderr)
        sys.exit(1)
    print(f"{exe} : forgé")
