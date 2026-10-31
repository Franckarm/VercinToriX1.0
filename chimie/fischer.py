#!/usr/bin/env python3
"""Fischer : le rangement des molécules dans le cube (docs/vtx-reactions.md, étape 3).

Le cube des molécules : l'étage 0 (avec le code : c'est l'ADN), le cube de fréquence 12 (la masse du carbone). Ses
256³ cases sont parcourues par le fil de Hilbert (une case ne mène qu'à sa voisine : la carte ne crée pas de fausses
ruptures). Le fil est coupé en 4096 colonnes de 4096 cases.

- **La formule choisit la colonne** : la masse de la molécule (sa taille en hex). Les molécules de même masse sont dans
  la même colonne, celles de masses voisines dans des colonnes voisines.
- **La signature choisit la place dans la colonne** : une empreinte de la molécule (ses atomes, leurs liaisons, sans les
  noms), qui ne dépend que de ce qu'elle est. On la retrouve en calculant sa signature, sans chercher.
- **La molécule occupe une suite de cases** : une tête (sa signature) puis un atome par case, la chaîne à la suite.
  Si la place est prise, on avance le long du fil (comme une brique qui cherche son trou dans un casse-brique) ; une
  colonne pleine déborde dans la suivante.

    python3 chimie/fischer.py essai [N]        remplit le cube de N molécules au hasard : saturation, recherches, image
"""
import hashlib
import os
import random
import sys

COTE = 8                      # bits par axe : 256 cases
COLONNE = 4096                # cases par colonne
N_COLONNES = (1 << (3 * COTE)) // COLONNE
ETAGE, FREQUENCE = 0, 12      # le cube des molécules


# ---------------------------------------------------------------- le fil de Hilbert en trois dimensions (Skilling, 2004)
def _transposer_vers_axes(x, b):
    n = len(x)
    N = 2 << (b - 1)
    t = x[n - 1] >> 1
    for i in range(n - 1, 0, -1):
        x[i] ^= x[i - 1]
    x[0] ^= t
    q = 2
    while q != N:
        p = q - 1
        for i in range(n - 1, -1, -1):
            if x[i] & q:
                x[0] ^= p
            else:
                t = (x[0] ^ x[i]) & p
                x[0] ^= t
                x[i] ^= t
        q <<= 1
    return x


def _axes_vers_transposer(x, b):
    n = len(x)
    M = 1 << (b - 1)
    q = M
    while q > 1:
        p = q - 1
        for i in range(n):
            if x[i] & q:
                x[0] ^= p
            else:
                t = (x[0] ^ x[i]) & p
                x[0] ^= t
                x[i] ^= t
        q >>= 1
    for i in range(1, n):
        x[i] ^= x[i - 1]
    t = 0
    q = M
    while q > 1:
        if x[n - 1] & q:
            t ^= q - 1
        q >>= 1
    for i in range(n):
        x[i] ^= t
    return x


def case_du_fil(h, b=COTE):
    """le rang h sur le fil -> la case (r, v, b)"""
    x = [0, 0, 0]
    for k in range(3 * b):
        bit = (h >> (3 * b - 1 - k)) & 1
        x[k % 3] |= bit << (b - 1 - k // 3)
    return tuple(_transposer_vers_axes(x, b))


def rang_sur_le_fil(r, v, bl, b=COTE):
    """la case -> son rang sur le fil"""
    x = _axes_vers_transposer([r, v, bl], b)
    h = 0
    for k in range(3 * b):
        h |= ((x[k % 3] >> (b - 1 - k // 3)) & 1) << (3 * b - 1 - k)
    return h


def adresse(rang):
    """l'adresse longue de Lugus d'un rang du fil dans le cube des molécules : étage 0, fréquence 12, #RRGGBB"""
    r, v, b = case_du_fil(rang)
    return (ETAGE << 126) | (FREQUENCE << 24) | (r << 16) | (v << 8) | b


# ---------------------------------------------------------------- la signature et la place
def signature(molecule):
    """L'empreinte de ce qu'est une molécule : ses atomes vague après vague (élément, genre, la forme de leur
    expression avec ses valeurs écrites) et, pour chacun, les atomes qui lui donnent ses liaisons d'entrée ; sans aucun
    nom, et sans l'ordre des lignes (dans une vague, les atomes sont rangés par leur propre description). Limite : deux
    atomes identiques dans une même vague (deux fois la constante 6) peuvent s'échanger selon l'ordre des lignes."""
    el = dict(molecule.elements())
    rang, forme = {}, []
    for vague in molecule.vagues:
        decrits = []
        for a in vague:
            def source(nom):
                if nom in molecule.donne:
                    p = molecule.donne[nom]
                    k = p.sorties.index(nom)
                    return f"s{rang[id(p)]}.{k}"
                if nom in molecule.params:
                    return f"p{molecule.params.index(nom)}"
                return "v"                         # une variable locale (celle de « pour chaque »)

            def forme_de(e):
                """la forme d'une expression : les liaisons remplacées par leur source, les nombres par k"""
                if isinstance(e, tuple) and e and isinstance(e[0], str):
                    if e[0] == "var":
                        return source(e[1])
                    if e[0] in ("nombre", "pqf", "flt", "str"):
                        return f"k{e[1]!r}"            # une valeur écrite fait partie de ce qu'est la molécule
                    return e[0] + "(" + ",".join(forme_de(x) for x in e[1:] if not isinstance(x, int) or e[0] == "mem") + ")"
                if isinstance(e, (tuple, list)):
                    return "[" + ",".join(forme_de(x) for x in e) + "]"
                return str(e) if isinstance(e, str) else ""
            decrits.append((f"{el[a.nom_affiche()]}:{a.genre}:{forme_de(a.quoi)}:{len(a.sorties)}", a))
        decrits.sort(key=lambda x: x[0])
        for d, a in decrits:
            rang[id(a)] = len(forme)
            forme.append(d)
    return int.from_bytes(hashlib.sha256("|".join(forme).encode()).digest()[:8], "big")


def colonne_brute(masse):
    return masse % N_COLONNES


class Repartition:
    """Les colonnes partagées selon la fréquence des masses (comme on égalise un histogramme) : une masse fréquente
    reçoit beaucoup de colonnes, une masse rare peu ; l'ordre est gardé (les masses voisines restent voisines), et la
    signature choisit la colonne dans la part de sa masse. Sans échantillon : une colonne par masse."""

    def __init__(self, masses=None):
        self.part = {}
        if masses:
            compte = {}
            for m in masses:
                compte[m] = compte.get(m, 0) + 1
            total, cumul = len(masses), 0
            for m in sorted(compte):
                debut = cumul * N_COLONNES // total
                cumul += compte[m]
                self.part[m] = (debut, max(1, cumul * N_COLONNES // total - debut))

    def colonne(self, masse, sig):
        if masse in self.part:
            debut, largeur = self.part[masse]
            return debut + (sig >> 20) % largeur
        # une masse jamais vue : la colonne de la masse la plus proche
        if self.part:
            proche = min(self.part, key=lambda m: abs(m - masse))
            debut, largeur = self.part[proche]
            return debut + (sig >> 20) % largeur
        return masse % N_COLONNES


REPARTITION = Repartition()


def colonne_de(masse, sig=0):
    return REPARTITION.colonne(masse, sig)


def colonnes_de(masse, deux=True, sig=0):
    """Les places possibles d'une molécule : la colonne de sa masse, et (le puzzle : une pièce qui ne rentre pas essaie
    l'autre sens) la colonne miroir, celle de l'anti-cube, à l'autre bout du fil."""
    c = colonne_de(masse, sig)
    return [c, N_COLONNES - 1 - c] if deux else [c]


class Cube:
    """Le cube des molécules : chaque case du fil est libre (0) ou occupée par la molécule n (n > 0)."""

    def __init__(self):
        self.occupe = {}           # rang du fil -> numéro de la molécule qui occupe la case
        self.tetes = {}            # rang de la tête -> (signature, longueur)
        self.debordements = 0
        # pour chaque colonne, le plus long chemin entre la place de départ d'une molécule et sa tête : une recherche ne
        # va jamais plus loin (une brique a pu sauter par-dessus un trou trop court pour elle)
        self.ecart_max = {}
        self.remplissage = {}      # colonne -> cases prises

    def libre(self, debut, longueur):
        return all((debut + k) not in self.occupe for k in range(longueur))

    def ranger(self, sig, masse, longueur, numero, deux=True):
        """La place d'une molécule : sa colonne (la masse, ou son miroir s'il est moins plein), son départ (la
        signature), puis le premier trou assez long le long du fil. Rend (rang de la tête, cases regardées)."""
        col = min(colonnes_de(masse, deux, sig), key=lambda c: self.remplissage.get(c, 0))
        depart = col * COLONNE + sig % COLONNE
        rang, vus = depart, 0
        total = 1 << (3 * COTE)
        while True:
            vus += 1
            # la première case prise de la place essayée : la brique saute juste après elle
            pris = next((k for k in range(longueur) if (rang + k) % total in self.occupe), None)
            if pris is None and rang + longueur <= total:
                break
            rang = (rang + (pris if pris is not None else 0) + 1) % total
            if vus > total:
                raise RuntimeError("le cube des molécules est plein")
        if rang // COLONNE != col:
            self.debordements += 1
        for k in range(longueur):
            self.occupe[rang + k] = numero
            cc = (rang + k) // COLONNE
            self.remplissage[cc] = self.remplissage.get(cc, 0) + 1
        self.tetes[rang] = (sig, longueur)
        ecart = (rang - depart) % total
        self.ecart_max[col] = max(self.ecart_max.get(col, 0), ecart)
        return rang, vus

    def retrouver(self, sig, masse, deux=True):
        """Une molécule par ce qu'elle est : de sa place de départ, le long du fil jusqu'à sa tête, dans sa colonne puis
        dans la colonne miroir. Rend (rang, cases regardées)."""
        total = 1 << (3 * COTE)
        vus = 0
        cols = colonnes_de(masse, deux, sig)
        # les deux colonnes ensemble, case après case : la plus proche des deux places est trouvée la première
        for ecart in range(max(self.ecart_max.get(c, 0) for c in cols) + 1):
            for col in cols:
                if ecart > self.ecart_max.get(col, 0):
                    continue
                vus += 1
                rang = (col * COLONNE + sig % COLONNE + ecart) % total
                t = self.tetes.get(rang)
                if t is not None and t[0] == sig:
                    return rang, vus
        return None, vus


# ---------------------------------------------------------------- l'essai : remplir jusqu'à saturation
def essai(n_molecules=20000, graine=12, image=None, deux=True, repartir=True):
    """Des molécules au hasard (masses et tailles comme celles des programmes : de 3 à 40 atomes) rangées dans le cube ;
    on mesure les cases regardées pour ranger et pour retrouver, le remplissage des colonnes et les débordements."""
    global REPARTITION
    r = random.Random(graine)

    def une_masse(rr):
        atomes = rr.randint(3, 40)
        # une masse vraisemblable : surtout des H et des N, quelques C et O
        return atomes, sum(rr.choice((1, 1, 14, 14, 12, 16)) for _ in range(atomes))
    # la répartition apprise sur 2000 molécules (un autre tirage) : la statistique des masses du langage
    echantillon = random.Random(graine + 1)
    REPARTITION = Repartition([une_masse(echantillon)[1] for _ in range(2000)]) if repartir else Repartition()
    cube = Cube()
    rangees = []
    for k in range(1, n_molecules + 1):
        atomes, masse = une_masse(r)
        sig = r.getrandbits(64)
        rang, vus = cube.ranger(sig, masse, atomes + 1, k, deux)
        rangees.append((sig, masse, rang, vus))
    trouves = [cube.retrouver(sig, masse, deux) for sig, masse, _, _ in rangees]
    if any(t[0] != rg for t, (_, _, rg, _) in zip(trouves, rangees)):
        raise RuntimeError("une molécule n'a pas été retrouvée à sa place")
    cherches = [t[1] for t in trouves]
    occupees = len(cube.occupe)
    par_col = {}
    for rang in cube.occupe:
        par_col[rang // COLONNE] = par_col.get(rang // COLONNE, 0) + 1
    pleine = max(par_col.values()) / COLONNE
    moy = lambda xs: sum(xs) / len(xs)  # noqa: E731
    res = {
        "molecules": n_molecules, "cases_occupees": occupees, "colonnes_touchees": len(par_col),
        "remplissage_max_colonne": round(pleine, 3), "debordements": cube.debordements,
        "ranger_moyen": round(moy([v for *_, v in rangees]), 2), "ranger_pire": max(v for *_, v in rangees),
        "retrouver_moyen": round(moy(cherches), 2), "retrouver_pire": max(cherches),
    }
    if image:
        dessiner(cube, sorted(par_col, key=lambda c: -par_col[c])[:4], image)
    return res


def dessiner(cube, colonnes, chemin):
    """Les colonnes les plus pleines en image : 64 × 64 cases chacune, une couleur par molécule (le puzzle)."""
    from PIL import Image
    t = 6
    img = Image.new("RGB", (len(colonnes) * (64 * t + 12), 64 * t), (24, 28, 32))
    for i, col in enumerate(colonnes):
        x0 = i * (64 * t + 12)
        for k in range(COLONNE):
            n = cube.occupe.get(col * COLONNE + k)
            if n is None:
                continue
            rr = random.Random(n)
            couleur = (rr.randint(60, 255), rr.randint(60, 255), rr.randint(60, 255))
            x, y = k % 64, k // 64
            for dx in range(t - 1):
                for dy in range(t - 1):
                    img.putpixel((x0 + x * t + dx, y * t + dy), couleur)
    img.save(chemin)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "essai":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 20000
        img = sys.argv[sys.argv.index("--image") + 1] if "--image" in sys.argv else \
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "casse-brique.png")
        for k, v in essai(n, image=img, deux="--une" not in sys.argv, repartir="--brut" not in sys.argv).items():
            print(f"{k:26s} {v}")
        print(f"-> {img}")
    else:
        print(__doc__)
