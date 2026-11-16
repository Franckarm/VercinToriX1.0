#!/usr/bin/env python3
"""La fiabilité de l'ADN par son code chimique (docs/vtx-reactions.md, étape 5, deuxième temps).

L'ADN d'un programme, ce sont ses mots compilés, rangés pour durer. Il est découpé en molécules, d'après les mots seuls
(Python et Lugus en Rust font le même découpage, le même ADN) : la tête du programme, puis une molécule par fonction (ou
réaction), de son début (la cible d'un CALL) au début de la suivante ; la dernière garde les textes et les données. Trois témoins indépendants se recoupent (la triangulation) :

  1. la signature de chaque molécule : l'empreinte de ses mots (64 bits). Elle voit tout changement, sans dire où, et
     confirme chaque réparation : un mot réparé de travers ne passe pas ;
  2. l'ombre : l'ADN est lu en colonnes d'au plus 251 mots, entrelacées (la colonne k prend un mot sur C, à partir du
     k-ième : une rafale de mots voisins se répartit entre les colonnes), chacune avec quatre mots d'ombre (un code de
     Reed-Solomon sur les seize octets de chaque mot). Elle répare deux mots abîmés n'importe où dans la colonne, ou
     quatre si l'on sait lesquels ;
  3. les neutrons : le contrôle de chaque mot (8 bits), là où les erreurs entrent : les molécules qui touchent le monde
     (O : leur code écrit en mémoire ou sort quelque chose). Ils disent quels mots sont abîmés ; l'ombre en répare alors
     deux fois plus.

Le contrôle est donc là où il compte : rien en plus sur les constantes (les textes, les données), le plus aux
frontières. À la lecture, chaque molécule a un état de Belnap : vrai (intacte), faux (réparée, ou un témoin abîmé
refait), variable (abîmée au-delà de ses témoins : gardée telle quelle, pour la preuve).

À la transcription (ADN -> ARN), l'épissage retire les témoins : l'ARN, ce sont les mots seuls, vérifiés.

    python3 chimie/adn.py ranger PROG.vtx [PROG.adn]      l'ADN : les mots et les témoins
    python3 chimie/adn.py transcrire PROG.adn [PROG.mots]  vérifie, répare, épisse : les mots
    python3 chimie/adn.py hex PROG.adn [PROG.hex]         les mots en hex, chacun à sa place du cube (0.6n bis)
    python3 chimie/adn.py retrotranscrire PROG.arn [PROG-c.adn]  l'ARN rendu à l'ADN : l'ADNc (0.6n bis)
    python3 chimie/adn.py abimer PROG.adn [N] [GRAINE]     abîme N mots au hasard (pour essayer la réparation)
    python3 chimie/adn.py essai [PROG.vtx…]                les avaries mesurées (détection, réparation, place)"""
import os
import random
import sys

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, racine)
sys.path.insert(0, ici)
import rs  # noqa: E402

INCONNU, FAUX, VRAI, VARIABLE = 0, 1, 2, 3
NOM_ETAT = {INCONNU: "inconnu", FAUX: "faux (réparé)", VRAI: "vrai", VARIABLE: "variable"}
COLONNE = 251               # les mots d'une colonne ; avec ses quatre mots d'ombre, 255 : la longueur d'un code sur GF(256)
OMBRE = 4


def pire(a, b):
    rang = {VRAI: 0, INCONNU: 1, FAUX: 2, VARIABLE: 3}
    return a if rang[a] >= rang[b] else b


# ---------------------------------------------------------------------------------------------------- les témoins
M64 = (1 << 64) - 1


def melanger(z):
    """le mélange de splitmix64"""
    z = (z + 0x9E3779B97F4A7C15) & M64
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & M64
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & M64
    return z ^ (z >> 31)


def signature(mots):
    """l'empreinte d'une molécule : 64 bits, chaque moitié de mot mêlée à son tour (la même en Rust : vtx-rs/src/adn.rs)"""
    h = melanger(0x5643_5458_4144_4E00 ^ len(mots))      # « VCTXADN »
    for w in mots:
        h = melanger(h ^ (w & M64))
        h = melanger(h ^ (w >> 64))
    return h


def crc8(w):
    """les neutrons d'un mot : un CRC de 8 bits (polynôme 0x07) sur ses seize octets"""
    c = 0
    for octet in w.to_bytes(16, "little"):
        c ^= octet
        for _ in range(8):
            c = ((c << 1) ^ 0x07) & 0xFF if c & 0x80 else (c << 1) & 0xFF
    return c


# les neutrons quaternaires (ADN version 4) : le mot lu comme 64 quits, le plus fort d'abord, divisé par
# g(x) = x^4 + x^2 + ωx + 1 sur GF(4) (0, 1, ω = 2, ω² = 3 ; l'addition est le OU exclusif) ; le reste, 4 quits, est le
# neutron (le coefficient de x^3 dans les deux bits forts). Il voit toute erreur d'un ou deux quits, de deux bits, et
# toute rafale de 8 bits au plus (chimie/essai_neutrons.py). Linéaire sur GF(2) : une table par octet, l'octet fort d'abord.
def _gf4_mul(a, b):
    if a == 0 or b == 0:
        return 0
    lg = (None, 0, 1, 2)
    return (1, 2, 3)[(lg[a] + lg[b]) % 3]


GF4_GEN = (0, 1, 2, 1)       # g3, g2, g1, g0


def _gf4_pas(r, q):
    """un quit q entre dans le reste r (4 quits, le coefficient de x^3 en haut)"""
    t = q ^ (r >> 6)
    r0, r1, r2 = (r >> 4) & 3, (r >> 2) & 3, r & 3
    return ((r0 ^ _gf4_mul(t, GF4_GEN[0])) << 6 | (r1 ^ _gf4_mul(t, GF4_GEN[1])) << 4
            | (r2 ^ _gf4_mul(t, GF4_GEN[2])) << 2 | _gf4_mul(t, GF4_GEN[3]))


GF4_TABLE = []
for _x in range(256):
    _r = 0
    for _k in (3, 2, 1, 0):
        _r = _gf4_pas(_r, (_x >> (2 * _k)) & 3)
    GF4_TABLE.append(_r)


def crc_gf4(w):
    """les neutrons quaternaires d'un mot (8 bits : 4 quits), par la table : seize octets, le plus fort d'abord"""
    c = 0
    for octet in w.to_bytes(16, "big"):
        c = GF4_TABLE[c ^ octet]
    return c


def neutron(w, version):
    """les neutrons d'un mot selon la version de l'ADN : CRC-8 jusqu'à la 3, quaternaires à partir de la 4"""
    return crc_gf4(w) if version >= 4 else crc8(w)


def voies(mots):
    """les seize voies d'octets d'une suite de mots (l'octet fort d'abord)"""
    return [[(w >> (8 * (15 - k))) & 0xFF for w in mots] for k in range(16)]


def mots_de(v):
    n = len(v[0])
    return [sum(v[k][i] << (8 * (15 - k)) for k in range(16)) for i in range(n)]


def ombre_colonne(mots):
    return mots_de([rs.coder(v, OMBRE) for v in voies(mots)])


def nb_colonnes(n):
    return max(1, (n + COLONNE - 1) // COLONNE)


def places_colonne(n, k):
    """les places des mots de la colonne k : un sur C, à partir de k"""
    return range(k, n, nb_colonnes(n))


class Molecule:
    def __init__(self, nom, debut, fin, frontiere, isotope=False):
        self.nom, self.debut, self.fin, self.frontiere, self.isotope = nom, debut, fin, frontiere, isotope

    @property
    def neutronee(self):
        """une molécule qui porte des neutrons : une frontière (O), ou un isotope lourd (« -> a lourd »)"""
        return self.frontiere or self.isotope

    def __repr__(self):
        return f"{self.nom}[{self.debut}:{self.fin}]{' O' if self.frontiere else ''}{' lourde' if self.isotope else ''}"


def temoins(mots, molecules):
    """{signatures, ombres (une liste de quatre mots par colonne), neutrons (place -> 8 bits, aux frontières)}"""
    neutrons = {}
    for m in molecules:
        if m.neutronee:
            for i in range(m.debut, m.fin):
                neutrons[i] = crc_gf4(mots[i])
    return {"signatures": [signature(mots[m.debut:m.fin]) for m in molecules],
            "ombres": [ombre_colonne([mots[i] for i in places_colonne(len(mots), k)]) for k in range(nb_colonnes(len(mots)))],
            "neutrons": neutrons, "introns": [], "version": 4}


def copie_temoins(t):
    return {"signatures": list(t["signatures"]), "ombres": [list(o) for o in t["ombres"]], "neutrons": dict(t["neutrons"]),
            "introns": [(n, list(l)) for n, l in t.get("introns", [])], "version": t.get("version", 4)}


def place_des_temoins(mots, molecules):
    """en mots : les signatures (deux par mot), l'ombre (quatre par colonne), les neutrons (seize par mot)"""
    colonnes = nb_colonnes(len(mots))
    o = sum(m.fin - m.debut for m in molecules if m.neutronee)
    return (len(molecules) + 1) // 2 + OMBRE * colonnes + (o + 15) // 16


# ---------------------------------------------------------------------------------------------------- la lecture
def lire_colonne(mots, k, t):
    """répare la colonne k en place ; rend (état, places réparées, places désignées par les neutrons)"""
    places = list(places_colonne(len(mots), k))
    data = [mots[i] for i in places]
    om = t["ombres"][k]
    effaces = [j for j, i in enumerate(places) if i in t["neutrons"] and neutron(data[j], t.get("version", 4)) != t["neutrons"][i]]
    if ombre_colonne(data) == om:
        return (FAUX if effaces else VRAI), [], [places[j] for j in effaces]
    if len(effaces) > OMBRE:
        return VARIABLE, [], [places[j] for j in effaces]
    cw = voies(data + om)
    reparees = []
    for v in range(16):
        out = rs.decoder(cw[v], OMBRE, effaces)
        if out is None:
            return VARIABLE, [], [places[j] for j in effaces]
        cw[v] = out
    neuf = mots_de(cw)
    reparees = [places[j] for j in range(len(data)) if neuf[j] != data[j]]
    for j, i in enumerate(places):
        mots[i] = neuf[j]
    t["ombres"][k] = neuf[len(data):]
    return FAUX, reparees, [places[j] for j in effaces]


def lire(mots, molecules, t):
    """vérifie et répare l'ADN en place ; rend (état le pire, [(molécule, état, quoi)])"""
    avant = list(mots)
    col_etat, par_neutrons, col_reparees = {}, set(), {}
    nc = nb_colonnes(len(mots))
    for k in range(nc):
        e, reparees, effaces = lire_colonne(mots, k, t)
        col_etat[k] = e
        col_reparees[k] = reparees
        par_neutrons |= set(effaces)
    etat = FAUX if any(e == FAUX for e in col_etat.values()) else VRAI      # au moins un témoin refait
    rapport = []
    for j, m in enumerate(molecules):
        cols = {i % nc for i in range(m.debut, m.fin)}
        changes = [i for i in range(m.debut, m.fin) if mots[i] != avant[i]]
        sig_ok = signature(mots[m.debut:m.fin]) == t["signatures"][j]
        abimee = any(col_etat[c] == VARIABLE for c in cols)
        if sig_ok and not changes and not abimee:
            e, quoi = VRAI, ""
        elif sig_ok:
            e, quoi = FAUX, f"{len(changes)} mot(s) réparé(s)" if changes else "ombre ou neutrons refaits"
        elif abimee:
            e, quoi = VARIABLE, "abîmée au-delà de son ombre"
        elif not changes:
            # l'ombre et les neutrons s'accordent avec les mots : c'est la signature qui est abîmée (deux contre un)
            e, quoi = FAUX, "signature refaite"
            t["signatures"][j] = signature(mots[m.debut:m.fin])
        elif (m.neutronee and all(i in par_neutrons and neutron(mots[i], t.get("version", 4)) == t["neutrons"].get(i) for i in changes)) or \
                all(len(col_reparees[i % nc]) == 1 for i in changes):
            # deux témoins contre un : les mots réparés sont ceux que les neutrons désignaient, et ils les reconnaissent ;
            # ou l'ombre n'a eu qu'un mot à réparer dans chaque colonne (la moitié de ce qu'elle peut : une fausse
            # réparation demanderait trois mots abîmés dans la colonne). La signature, seule contre eux, est refaite.
            e, quoi = FAUX, f"{len(changes)} mot(s) réparé(s), signature refaite"
            t["signatures"][j] = signature(mots[m.debut:m.fin])
        else:
            # la réparation n'est pas confirmée : la molécule est gardée telle qu'elle a été lue
            for i in changes:
                mots[i] = avant[i]
            e, quoi = VARIABLE, "réparation non confirmée par la signature"
        etat = pire(etat, e)
        rapport.append((m, e, quoi))
    if etat != VARIABLE:
        t["neutrons"] = {i: neutron(mots[i], t.get("version", 4)) for i in t["neutrons"]}
    return etat, rapport


# ---------------------------------------------------------------------------------------------------- le découpage



# les codes d'opération de Lugus (spu128.py) : CALL, LDI et LDIH (suivis d'une constante), ceux qui écrivent ou sortent
OP_CALL, OP_LDI, OP_LDIH = 0x33, 0x0A, 0x2B
OPS_FRONTIERE = {0x21, 0x24, 0x2A, 0x39, 0x52, 0x53, 0x55, 0x5E, 0x5F}   # ST OUT STX GEMV SORC SYS STQ MARQUE BRIN


def demis(mots):
    """les demi-instructions (la haute d'abord), chacune avec un drapeau : vraie instruction ou constante d'un LDI"""
    lit = False
    for w in mots:
        for h in (w >> 64, w & M64):
            yield h, lit
            lit = not lit and (h >> 48) in (OP_LDI, OP_LDIH)


def decouper(mots):
    """les molécules, d'après les mots seuls : la tête, puis une par fonction (de la cible d'un CALL à la suivante).
    Une molécule est une frontière (O) si son code écrit en mémoire ou sort quelque chose."""
    n = len(mots)
    debuts = {0} | {(h & 0xFFFFFFFF) // 2 for h, lit in demis(mots) if not lit and (h >> 48) == OP_CALL}
    debuts = sorted(d for d in debuts if d < n)
    molecules = []
    for a, b in zip(debuts, debuts[1:] + [n]):
        frontiere = any(not lit and (h >> 48) in OPS_FRONTIERE for h, lit in demis(mots[a:b]))
        molecules.append(Molecule(f"m{a}", a, b, frontiere))
    return molecules


def molecules_du_programme(src, dossier=None):
    """(les mots, les molécules), le programme compilé comme le fait Lugus (le prélude, les optimisations)"""
    mots, molecules, _ = molecules_et_isotopes(src, dossier)
    return mots, molecules


def molecules_et_isotopes(src, dossier=None):
    mots, molecules, isotopes, _ = molecules_isotopes_noms(src, dossier)
    return mots, molecules, isotopes


def molecules_isotopes_noms(src, dossier=None):
    """(les mots, les molécules, les isotopes [(nom, mot)]) : les réactions qui portent un atome lourd (« -> a lourd »)
    sont des isotopes lourds ; leur molécule (celle où tombe leur premier mot) garde ses neutrons"""
    import vtx128
    vtx128.COMPAT_64 = False
    vtx128.REACTIONS.clear()
    asm = vtx128.compiler(src, dossier=dossier)
    lourdes = {nom for nom, m in vtx128.REACTIONS.items() if any(getattr(a, "lourdes", None) for a in m.atomes)}
    mots, etiq = vtx128.assembler(asm, True)
    molecules = decouper(mots)
    noms = {v // 2: k[2:].lower() for k, v in etiq.items() if k.startswith("F_") and not k.endswith("_FIN")}
    for m in molecules:
        m.nom = "tête" if m.debut == 0 else noms.get(m.debut, m.nom)
    nom_ecrit = {x.lower(): x for x in lourdes}
    isotopes = sorted(((nom_ecrit[n], a) for a, n in noms.items() if n in nom_ecrit), key=lambda x: x[1])
    marquer_isotopes(molecules, isotopes)
    # « F_NOM_FIN » est la fin de la fonction NOM, sauf s'il n'y a pas de « F_NOM » (une fonction nommée « …_fin »)
    return mots, molecules, isotopes, {v // 2: bas(k[2:]) for k, v in etiq.items()
                                       if k.startswith("F_") and not (k.endswith("_FIN") and k[:-4] in etiq)}


def marquer_isotopes(molecules, isotopes):
    for _, adr in isotopes:
        for m in molecules:
            if m.debut <= adr < m.fin:
                m.isotope = True


# ---------------------------------------------------------------------------------------------------- les avaries
def avarie(genre, mots, t, molecules, g):
    n = len(mots)
    if genre == "un bit":
        mots[g.randrange(n)] ^= 1 << g.randrange(128)
    elif genre == "un mot":
        mots[g.randrange(n)] = g.getrandbits(128)
    elif genre == "un mot effacé":
        mots[g.randrange(n)] = 0
    elif genre == "deux mots échangés":
        i = g.randrange(n - 1)
        mots[i], mots[i + 1] = mots[i + 1], mots[i]
    elif genre == "deux mots d'une molécule":
        m = g.choice([m for m in molecules if m.fin - m.debut >= 2])
        for i in g.sample(range(m.debut, m.fin), 2):
            mots[i] ^= g.getrandbits(128) | 1
    elif genre == "une rafale de quatre mots":
        i = g.randrange(n - 4)
        for k in range(4):
            mots[i + k] = g.getrandbits(128)
    elif genre == "une rafale de huit mots":
        i = g.randrange(n - 8)
        for k in range(8):
            mots[i + k] = g.getrandbits(128)
    elif genre == "trois mots d'une colonne":
        nc = nb_colonnes(n)
        k = g.randrange(nc)
        for i in g.sample(list(places_colonne(n, k)), 3):
            mots[i] ^= g.getrandbits(128) | 1
    elif genre == "seize mots au hasard":
        for i in g.sample(range(n), 16):
            mots[i] ^= g.getrandbits(128) | 1
    elif genre == "un témoin":
        quoi = g.choice(["signature", "ombre", "neutrons"] if t["neutrons"] else ["signature", "ombre"])
        if quoi == "signature":
            t["signatures"][g.randrange(len(t["signatures"]))] ^= 1 << g.randrange(64)
        elif quoi == "ombre":
            o = t["ombres"][g.randrange(len(t["ombres"]))]
            o[g.randrange(OMBRE)] ^= 1 << g.randrange(128)
        else:
            i = g.choice(list(t["neutrons"]))
            t["neutrons"][i] ^= 1 << g.randrange(8)
    elif genre == "un mot et sa signature":
        j = g.randrange(len(molecules))
        m = molecules[j]
        mots[g.randrange(m.debut, m.fin)] ^= g.getrandbits(128) | 1
        t["signatures"][j] ^= 1 << g.randrange(64)
    else:
        raise ValueError(genre)


GENRES = ["un bit", "un mot", "un mot effacé", "deux mots échangés", "deux mots d'une molécule", "une rafale de quatre mots",
          "une rafale de huit mots", "trois mots d'une colonne", "seize mots au hasard", "un témoin", "un mot et sa signature"]


def essai(fichiers, n=200, graine=1, ecrire=print, genres=None):
    g = random.Random(graine)
    resultats = {}
    for f in fichiers:
        src = open(f, encoding="utf-8").read()
        mots, molecules = molecules_du_programme(src, os.path.dirname(os.path.abspath(f)))
        t0 = temoins(mots, molecules)
        place = place_des_temoins(mots, molecules)
        o = sum(m.fin - m.debut for m in molecules if m.frontiere)
        ecrire(f"\n{os.path.basename(f)} : {len(mots)} mots, {len(molecules)} molécules ({100 * o / len(mots):.0f} % des mots "
               f"dans des frontières O) ; témoins : {place} mots, {100 * place / len(mots):.1f} % de l'ADN")
        for genre in genres or GENRES:
            c = {"réparé": 0, "vu": 0, "intact": 0, "muet": 0}
            for _ in range(n):
                abime, t = list(mots), copie_temoins(t0)
                avarie(genre, abime, t, molecules, g)
                touche = abime != mots
                etat, _ = lire(abime, molecules, t)
                if etat in (VRAI, FAUX) and abime != mots:
                    c["muet"] += 1             # une erreur passée sans être vue : ne doit jamais arriver
                elif etat == VARIABLE:
                    c["vu"] += 1
                elif touche or etat == FAUX:
                    c["réparé"] += 1
                else:
                    c["intact"] += 1
            resultats[(os.path.basename(f), genre)] = c
            ecrire(f"  {genre:28s} réparé {100 * c['réparé'] / n:5.1f} %   vu, non réparé {100 * c['vu'] / n:5.1f} %"
                   f"   sans effet {100 * c['intact'] / n:5.1f} %   erreur muette {c['muet']}")
    return resultats


# ---------------------------------------------------------------------------------------------------- le fichier ADN
def ecrire_adn(chemin, mots, molecules, t):
    """L'ADN de vtx, versions 3 et 4 (les neutrons seuls changent) : des sections signalées comme des introns,
    « GU nom N » puis N lignes puis « AG ». La lecture saute une section qu'elle ne connaît pas sans rien analyser (la même chose en Rust : vtx-rs/src/adn.rs)."""
    sections = [("mots", [",".join(map(str, mots))]),
                ("molecules", [f"m{m.debut}|{m.debut}|{m.fin}|{int(m.frontiere)}|{s}|{int(m.isotope)}"
                               for m, s in zip(molecules, t["signatures"])]),
                ("ombres", [",".join(map(str, o)) for o in t["ombres"]]),
                ("neutrons", [",".join(f"{i}:{v}" for i, v in sorted(t["neutrons"].items()))])]
    sections += t.get("introns", [])
    with open(chemin, "w", encoding="utf-8", newline="\n") as f:     # \n partout : Lugus (Rust) lit le même fichier
        # la version garde ses neutrons : un ADN lu en version 3 (CRC-8) est réécrit en version 3, octet pour octet
        f.write("VTXADN04\n" if t.get("version", 4) >= 4 else "VTXADN03\n")
        for nom, lignes in sections:
            f.write(f"GU {nom} {len(lignes)}\n")
            for x in lignes:
                f.write(x + "\n")
            f.write("AG\n")


def sections_adn(texte):
    """[(nom, lignes)] d'un ADN version 3 ou 4"""
    l = texte.split("\n")
    out, i = [], 1
    while i < len(l) and l[i]:
        tete = l[i].split(" ")
        if len(tete) != 3 or tete[0] != "GU":
            raise ValueError(f"ADN : borne d'intron attendue (GU), ligne {i + 1}")
        n = int(tete[2])
        if i + 1 + n >= len(l) or l[i + 1 + n] != "AG":
            raise ValueError(f"ADN : la section « {tete[1]} » ne finit pas par AG")
        out.append((tete[1], l[i + 1:i + 1 + n]))
        i += n + 2
    return out


CONNUES = ("mots", "molecules", "ombres", "neutrons")


def lire_adn(chemin):
    texte = open(chemin, encoding="utf-8").read().replace("\r\n", "\n")
    l = texte.split("\n")
    if l[0] == "VTXADN02":            # l'ADN version 2 : cinq lignes, sans introns
        sec = {"mots": [l[1]], "molecules": [x + "|0" for x in l[2].split("\t") if x], "ombres": [o for o in l[3].split(";") if o],
               "neutrons": [l[4]]}
        introns = []
    elif l[0] in ("VTXADN03", "VTXADN04"):
        tout = sections_adn(texte)
        sec = dict(tout)
        introns = [(n, x) for n, x in tout if n not in CONNUES]
    else:
        raise ValueError("ce n'est pas un ADN de vtx")
    mots = [int(x) for x in sec["mots"][0].split(",") if x]
    molecules, sigs = [], []
    for x in sec["molecules"]:
        nom, a, b, fr, s, iso = x.split("|")
        molecules.append(Molecule(nom, int(a), int(b), fr == "1", iso == "1"))
        sigs.append(int(s))
    ombres = [[int(v) for v in o.split(",")] for o in sec["ombres"]]
    neutrons = {int(a): int(b) for a, b in (x.split(":") for x in sec["neutrons"][0].split(",") if x)}
    version = 4 if l[0] == "VTXADN04" else 3
    return mots, molecules, {"signatures": sigs, "ombres": ombres, "neutrons": neutrons, "introns": introns,
                             "version": version}


def intron(t, nom):
    return next((x for n, x in t.get("introns", []) if n == nom), None)


def signature_compilateur():
    """la signature des mots du compilateur de Lugus (vtxc/vtxc128.mots, celui qu'embarque lugus) : l'intron
    « compilateur » de l'ADN (0.6n)"""
    texte = open(os.path.join(racine, "vtxc", "vtxc128.mots")).read().split(";")[0]
    return signature([int(x) for x in texte.split(",") if x.strip()])


def retrotranscrire(mots, t, dossier):
    """le texte gardé dans l'ADN, recompilé, redonne-t-il ses mots ? (VRAI, FAUX : un autre texte, INCONNU : pas de
    texte, ou le compilateur a changé depuis le rangement), et le message"""
    src = intron(t, "source")
    if src is None:
        return INCONNU, "l'ADN ne garde pas de texte"
    comp = intron(t, "compilateur")
    change = comp is not None and comp[:1] != [str(signature_compilateur())]
    try:
        m2, _, _ = molecules_et_isotopes("\n".join(src), dossier)
    except Exception as e:      # noqa: BLE001
        if change:
            return INCONNU, "le compilateur a changé depuis le rangement : le texte ne peut pas être vérifié"
        return FAUX, f"le texte gardé ne compile plus : {e}"
    if m2 == mots:
        return VRAI, "le texte gardé redonne les mots, un pour un"
    if change:
        return INCONNU, "le compilateur a changé depuis le rangement : le texte ne peut pas être vérifié"
    ecarts = sum(a != b for a, b in zip(m2, mots)) + abs(len(m2) - len(mots))
    if comp is None:
        return FAUX, (f"le texte gardé ne redonne pas ces mots ({ecarts} écart(s)) ; cet ADN ne note pas son "
                      "compilateur : il a pu changer depuis")
    return FAUX, f"le texte gardé ne redonne pas ces mots ({ecarts} écart(s))"


def ranger_texte(src, dossier, ancien=None):
    """(les mots, les molécules, les témoins avec leurs introns : les isotopes, le texte, le compilateur, la carte) ;
    ancien : le brin rangé avant (son texte), pour la face de la mémoire"""
    mots, molecules, isotopes, noms = molecules_isotopes_noms(src, dossier)
    t = temoins(mots, molecules)
    if isotopes:
        t["introns"].append(("isotopes", [f"{n}|{a}" for n, a in isotopes]))
    lignes = src.replace("\r\n", "\n").split("\n")
    t["introns"].append(("source", lignes))
    t["introns"].append(("compilateur", [str(signature_compilateur())]))
    t["introns"].append(("faces", faire_carte(mots, molecules, noms, lignes, ancien)))
    return mots, molecules, t


# ---------------------------------------------------------------------------------------------------- les promesses (0.6r)
NIVEAUX = {"rien": 0, "lecture": 1, "memoire": 2, "mémoire": 2, "monde": 3}
PROMET = {0: "de ne rien toucher", 1: "de lire la mémoire au plus", 2: "de ne pas toucher le monde"}
FAIT = {1: "lit la mémoire", 2: "écrit la mémoire", 3: "touche le monde"}


def promesse_de(tete):
    """« touche X » après la dernière parenthèse de l'en-tête : 0 à 3, ou None"""
    # 0.6w : l'en-tête s'arrête à la première accolade (une fonction écrite sur une ligne garde son corps à côté)
    if "{" in tete:
        tete = tete[:tete.index("{")]
    i = tete.rfind(")")
    j = tete.find(" touche ", i + 1 if i >= 0 else 0)
    if j < 0:
        return None
    mot = tete[j + 8:]
    k = 0
    while k < len(mot) and mot[k] not in " {":
        k += 1
    return NIVEAUX.get(mot[:k])


def promesses(mots, molecules, noms, lignes):
    """les messages : chaque promesse rompue (avec le chemin qui la rompt), et celles qui ne se vérifient pas à part"""
    debuts, faces, appels, tout, prof = bases_carte(mots, molecules)
    ecrits = entetes(lignes)
    vues, r = set(), []
    nom_de = {}
    for m in molecules:
        if m.debut in noms:
            nom_de[m.debut] = next((e[0] for e in ecrits if bas(e[0]) == noms[m.debut]), noms[m.debut])
    for k, m in enumerate(molecules):
        if m.debut == 0 or m.debut not in noms:
            continue
        e = next((e for e in ecrits if bas(e[0]) == noms[m.debut]), None)
        if e is None:
            continue
        vues.add(e[0])
        p = promesse_de(e[7])
        if p is None or p >= 3 or tout[k] <= p:
            continue
        chemin, x, vu = [], k, {k}
        while faces[x][0] <= p:
            c = next((debuts[c] for c in appels[x] if tout[debuts[c]] > p and debuts[c] not in vu), None)
            if c is None:
                break
            vu.add(c)
            chemin.append(nom_de.get(molecules[c].debut, f"m{molecules[c].debut}"))
            x = c
        r.append(f"promesse rompue : {e[0]} (ligne {e[2]}) promet {PROMET[p]}, mais elle {FAIT[tout[k]]} : "
                 + ("elle-même" if not chemin else "par " + " → ".join(chemin)))
    for e in ecrits:
        if e[0] not in vues and promesse_de(e[7]) is not None:
            r.append(f"promesse inconnue : {e[0]} (ligne {e[2]}) est recopiée en ligne là où elle sert : sa promesse "
                     "se vérifie dans celles qui l'appellent, pas à part")
    return r


# ---------------------------------------------------------------------------------------------------- la carte (0.6p, 0.6q)
# Pour chaque molécule, une ligne, les six faces d'un dé, en trois paires opposées :
#   ce qu'elle est (nom, genre, lignes, taille, en-tête)  |  ce qu'elle touche (0 rien, 1 lit la mémoire, 2 écrit la
#   mémoire, 3 le monde ; elle-même, puis avec ses appels)
#   ses racines (sa profondeur depuis la tête, qui l'appelle)  |  ses branches (ce qu'elle appelle)
#   ses promesses (exige, garantit, les exemples, isotope lourd)  |  sa mémoire (son empreinte, son histoire d'un
#   rangement à l'autre : « ? » rien d'avant, « n » nouvelle, « c » changée, « iK » inchangée depuis K rangements)
# Le centre, son état de Belnap, n'est pas écrit : il se lit à chaque lecture du brin.
# m<début>|nom|genre|L-E|mots|touche|touche avec ses appels|profondeur|appelle|appelée par|exige|garantit|exemples|
#   lourd|empreinte|histoire|en-tête
# Tirée des mots, du texte et des noms donnés par le compilateur ; le lecteur en vtx (chimie/adn.vtx) l'écrit de même,
# octet pour octet.
OPS_LIT = {0x20, 0x29, 0x54, 0x38, 0x5F}          # LD LDX LDQ GDOT BRIN
OPS_ECRIT = {0x21, 0x2A, 0x55, 0x39, 0x5E}        # ST STX STQ GEMV MARQUE
OPS_MONDE = {0x24, 0x52, 0x23, 0x51}              # OUT SORC IN ENTC
SERVICES = {10: 2, 13: 2, 25: 1, 26: 2}           # les autres services touchent le monde (fichiers, cubes, voix…)
DEBUTS = ("fonction ", "reaction ", "structure ", "constante ", "exemple ", "importer ")


def bas(t):
    """les majuscules latines en minuscules (A-Z, À-Þ, Œ, Ÿ), comme le lecteur en vtx"""
    r = []
    for c in t:
        o = ord(c)
        if 65 <= o <= 90 or (0xC0 <= o <= 0xDE and o != 0xD7):
            o += 32
        elif o == 0x152:
            o = 0x153
        elif o == 0x178:
            o = 0xFF
        r.append(chr(o))
    return "".join(r)


def lettre_nom(c):
    o = ord(c)
    return 48 <= o <= 57 or 65 <= o <= 90 or 97 <= o <= 122 or o == 95 or o >= 128


def entetes(lignes):
    """[(nom, genre, ligne, dernière, exige, garantit, exemples, en-tête)] des fonctions et réactions écrites"""
    hauts = [i for i, l in enumerate(lignes) if l.startswith(DEBUTS)]
    r = []
    for i, l in enumerate(lignes):
        kw = "fonction " if l.startswith("fonction ") else "reaction " if l.startswith("reaction ") else None
        if kw is None or "(" not in l[len(kw):]:
            continue
        reste = l[len(kw):]
        nom = reste[:reste.index("(")].strip(" \t")
        suivant = next((j for j in hauts if j > i), len(lignes))
        fin = suivant - 1
        while fin > i and (lignes[fin].strip(" \t") == "" or lignes[fin].startswith("//")):
            fin -= 1
        ex = ga = 0
        # les contrats d'une réaction (dans une fonction, « exige » ne vit que dans une lecture de « supposons »)
        for x in (lignes[i:fin + 1] if kw == "reaction " else []):
            st = x.lstrip(" \t")
            for mot in ("exige", "garantit"):
                if st.startswith(mot) and (len(st) == len(mot) or st[len(mot)] in " ("):
                    if mot == "exige":
                        ex += 1
                    else:
                        ga += 1
        tete = l.rstrip(" \t")
        if tete.endswith("{"):
            tete = tete[:-1].rstrip(" \t")
        r.append([nom, kw.strip(), i + 1, fin + 1, ex, ga, 0, tete])
    for l in lignes:
        if not l.startswith("exemple "):
            continue
        for e in r:
            cle = e[0] + "("
            j = l.find(cle)
            while j >= 0:
                if j == 0 or not lettre_nom(l[j - 1]):
                    e[6] += 1
                    break
                j = l.find(cle, j + 1)
    return r


def touche_et_appels(mots, a, b, plat):
    """(ce que touche la molécule [a, b) elle-même, les débuts des molécules qu'elle appelle)"""
    niveau, appels = 0, set()
    connu, pile = [None] * 16, []
    avant = 0
    avant_h, marque = 0, 3
    for p in range(2 * a, 2 * b):
        h, lit = plat[p]
        if lit:
            continue
        op, d, s_ = h >> 48, (h >> 44) & 15, (h >> 40) & 15
        # 0.6w : PUSH puis RET, un saut calculé (le trampoline des appels par valeur) : le monde, par prudence
        # 0.6y : un trampoline promis porte sa promesse juste avant le PUSH (LDIS R15,#k, k < 3)
        if op == 0x27:
            marque = 3
            if avant_h >> 48 == 0x18 and (avant_h >> 44) & 15 == 15 and avant_h & 0xFFFFFFFF < 3:
                marque = avant_h & 0xFFFFFFFF
        if op == 0x34 and avant == 0x27:
            niveau = max(niveau, marque)
        avant = op
        avant_h = h
        imm = h & 0xFFFFFFFF
        if op in OPS_LIT:
            niveau = max(niveau, 1)
        elif op in OPS_ECRIT:
            niveau = max(niveau, 2)
        elif op in OPS_MONDE:
            niveau = 3
        if op == 0x18:
            connu[d] = imm - (1 << 32) if imm >> 31 else imm
        elif op == 0x19:
            connu[d] = imm
        elif op == OP_LDI:
            connu[d] = plat[p + 1][0] if p + 1 < len(plat) else None
        elif op == 0x0B:
            connu[d] = connu[s_]
        elif op == 0x27:
            pile.append(connu[s_])
        elif op == 0x28:
            connu[d] = pile.pop() if pile else None
        elif op == 0x53:
            niveau = max(niveau, SERVICES.get(connu[s_], 3) if connu[s_] is not None else 3)
            connu[d] = None
        elif op == OP_CALL:
            appels.add(imm // 2)
            connu = [None] * 16
        else:
            connu[d] = None
    return niveau, appels


def fnv(texte):
    h = 14695981039346656037
    for c in texte:
        h = ((h ^ ord(c)) * 1099511628211) & 0xFFFFFFFFFFFFFFFF
    return h


def cle_carte(champs):
    """la clé d'une ligne de la carte, d'un rangement à l'autre : son nom, « la tête », ou sa place"""
    if champs[1]:
        return champs[1]
    return "\ttete" if champs[2] == "tete" else champs[0]


def anciens_de(texte):
    """{clé : (empreinte, histoire)} des faces d'un brin rangé avant ; None s'il n'en a pas"""
    if texte is None:
        return None
    lignes = texte.replace("\r\n", "\n").split("\n")
    for i, l in enumerate(lignes):
        if l.startswith("GU faces "):
            r = {}
            for x in lignes[i + 1:i + 1 + int(l.split()[2])]:
                c = x.split("|")
                if len(c) >= 17:
                    r.setdefault(cle_carte(c), (c[14], c[15]))
            return r
    return None


def histoire(ancien, cle, empreinte):
    if ancien is None:
        return "?"
    if cle not in ancien:
        return "n"
    e, h = ancien[cle]
    if e != empreinte:
        return "c"
    return f"i{int(h[1:]) + 1}" if h.startswith("i") else "i1"


def bases_carte(mots, molecules):
    """(les débuts, ce que touche chaque molécule elle-même, avec ses appels, ses appels, sa profondeur)"""
    plat = list(demis(mots))
    debuts = {m.debut: k for k, m in enumerate(molecules)}
    faces = [touche_et_appels(mots, m.debut, m.fin, plat) for m in molecules]
    appels = [sorted(x for x in ap if x in debuts) for _, ap in faces]
    tout = [n for n, _ in faces]
    change = True
    while change:
        change = False
        for k in range(len(molecules)):
            for c in appels[k]:
                if tout[debuts[c]] > tout[k]:
                    tout[k], change = tout[debuts[c]], True
    prof = [None] * len(molecules)
    if molecules:
        prof[0] = 0
        file = [0]
        for k in file:
            for c in appels[k]:
                if prof[debuts[c]] is None:
                    prof[debuts[c]] = prof[k] + 1
                    file.append(debuts[c])
    return debuts, faces, appels, tout, prof


def faire_carte(mots, molecules, noms, lignes, ancien=None):
    ancien = anciens_de(ancien)
    debuts, faces, appels, tout, prof = bases_carte(mots, molecules)
    ecrits = entetes(lignes)
    appelants = [sorted(molecules[j].debut for j in range(len(molecules)) if j != k and m.debut in appels[j])
                 for k, m in enumerate(molecules)]
    r = []
    for k, m in enumerate(molecules):
        nom, genre, lg, ex, ga, exe, tete = "", "inconnue", "0-0", 0, 0, 0, ""
        empreinte = m.fin - m.debut
        if m.debut == 0:
            genre = "tete"
        elif m.debut in noms:
            nom, genre = noms[m.debut], "empruntee"
            for e in ecrits:
                if bas(e[0]) == nom:
                    nom, genre, lg, ex, ga, exe, tete = e[0], e[1], f"{e[2]}-{e[3]}", e[4], e[5], e[6], e[7]
                    empreinte = fnv("".join(x + "\n" for x in lignes[e[2] - 1:e[3]]))
                    break
        champs = [f"m{m.debut}", nom, genre]
        r.append(f"m{m.debut}|{nom}|{genre}|{lg}|{m.fin - m.debut}|{faces[k][0]}|{tout[k]}|"
                 f"{'-' if prof[k] is None else prof[k]}|{','.join(map(str, appels[k]))}|"
                 f"{','.join(map(str, appelants[k]))}|{ex}|{ga}|{exe}|{int(m.isotope)}|{empreinte}|"
                 f"{histoire(ancien, cle_carte(champs), str(empreinte))}|{tete}")
    return r


# ---------------------------------------------------------------------------------------------------- le chemin dans les deux sens (0.6n bis)
def ecrire_hex(chemin, mots):
    """le hex : « VTXHEX01 N SIGNATURE », puis une ligne par mot, sa place dans le cube (#RRGGBB) et ses quatre voies
    (#RRRRRRRR_VVVVVVVV_BBBBBBBB_MMMMMMMM) ; comme le lecteur en vtx (chimie/adn.vtx) l'écrit"""
    with open(chemin, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"VTXHEX01 {len(mots)} {signature(mots)}\n")
        for i, w in enumerate(mots):
            x = f"{w:032X}"
            f.write(f"#{i:06X} #{x[0:8]}_{x[8:16]}_{x[16:24]}_{x[24:32]}\n")


def lire_hex(chemin):
    """(les mots, retouché) d'un hex : les lignes vides et « // » sautées, les « _ » libres, les places qui se suivent"""
    l = open(chemin, encoding="utf-8").read().replace("\r\n", "\n").split("\n")
    tete = l[0].split(" ")
    if len(tete) != 3 or tete[0] != "VTXHEX01":
        raise ValueError("ce n'est pas un hex de vtx (VTXHEX01)")
    mots = []
    for x in l[1:]:
        x = x.strip()
        if not x or x.startswith("//"):
            continue
        place, mot = x.split()
        if int(place[1:], 16) != len(mots):
            raise ValueError("les places ne se suivent pas")
        mots.append(int(mot[1:].replace("_", ""), 16))
    if len(mots) != int(tete[1]):
        raise ValueError("le hex annonce un autre nombre de mots")
    return mots, signature(mots) != int(tete[2])


def adnc(chemin):
    """la rétrotranscription : l'ADN d'un ARN (l'ADNc), comme le lecteur en vtx le fait. Rend (état, mots, molécules,
    témoins) : un ARN sûr (avec ses témoins) est vérifié et réparé, et sa coiffe refaite si les témoins reconnaissent
    les mots ; un ARN sans témoins n'a que sa coiffe (variable si elle ne reconnaît pas les mots), ses témoins sont
    refaits. L'épigénome est gardé ; le texte et le nom des isotopes, retirés à l'épissage, n'y sont pas."""
    texte = open(chemin, encoding="utf-8").read().replace("\r\n", "\n")
    l0 = texte.split("\n")[0]
    if l0 not in ("VTXARN01", "VTXARN02"):
        raise ValueError("ce n'est pas un ARN de vtx")
    version = 4 if l0 == "VTXARN02" else 3
    tout = sections_adn(texte)
    sec = dict(tout)
    sig = int(sec["coiffe"][0].split("|")[0])
    mots = [int(x) for x in sec["mots"][0].split(",") if x]
    introns = [(n, x) for n, x in tout if n not in CONNUES + ("coiffe",)]
    if "molecules" in sec:
        molecules, sigs = [], []
        for x in sec["molecules"]:
            nom, a, b, fr, sg, iso = x.split("|")
            molecules.append(Molecule(nom, int(a), int(b), fr == "1", iso == "1"))
            sigs.append(int(sg))
        t = {"signatures": sigs, "ombres": [[int(v) for v in o.split(",")] for o in sec["ombres"]],
             "neutrons": {int(a): int(b) for a, b in (x.split(":") for x in sec["neutrons"][0].split(",") if x)},
             "introns": introns, "version": version}
        etat, _ = lire(mots, molecules, t)
        if etat != VARIABLE and signature(mots) != sig:
            etat = pire(etat, FAUX)
        return etat, mots, molecules, t
    if signature(mots) != sig:
        return VARIABLE, mots, [], {}
    molecules = decouper(mots)
    t = temoins(mots, molecules)
    t["neutrons"] = {i: neutron(mots[i], version) for i in t["neutrons"]}
    t["introns"], t["version"] = introns, version
    return VRAI, mots, molecules, t


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]
    if cmd == "ranger":
        src = sys.argv[2]
        mots, molecules, t = ranger_texte(open(src, encoding="utf-8").read(), os.path.dirname(os.path.abspath(src)))
        sortie = sys.argv[3] if len(sys.argv) > 3 else os.path.splitext(src)[0] + ".adn"
        ecrire_adn(sortie, mots, molecules, t)
        p = place_des_temoins(mots, molecules)
        lourdes = [m.nom for m in molecules if m.isotope]
        print(f"{len(mots)} mots, {len(molecules)} molécules, témoins {p} mots ({100 * p / len(mots):.1f} %)"
              + (f", isotopes lourds : {', '.join(lourdes)}" if lourdes else "") + f" -> {sortie}")
    elif cmd == "transcrire":
        mots, molecules, t = lire_adn(sys.argv[2])
        etat, rapport = lire(mots, molecules, t)
        for m, e, quoi in rapport:
            if e != VRAI:
                print(f"  {m.nom} : {NOM_ETAT[e]}, {quoi}")
        print(f"l'ADN : {NOM_ETAT[etat]}")
        if etat != VARIABLE and intron(t, "source") is not None:
            e_t, quoi = retrotranscrire(mots, t, os.path.dirname(os.path.abspath(sys.argv[2])))
            print(f"le texte : {NOM_ETAT[e_t].split(' ')[0]}, {quoi}")
        if etat == VARIABLE:
            print("rien n'est transcrit : l'ADN est gardé tel qu'il a été lu, pour la preuve")
            sys.exit(1)
        sortie = sys.argv[3] if len(sys.argv) > 3 else os.path.splitext(sys.argv[2])[0] + ".mots"
        with open(sortie, "w", newline="\n") as f:
            f.write(",".join(map(str, mots)) + ";\n")
        print(f"l'ARN (les mots seuls, les témoins retirés à l'épissage) -> {sortie}")
        if etat == FAUX:
            ecrire_adn(sys.argv[2], mots, molecules, t)          # l'ADN réparé est réécrit
            print("l'ADN réparé est réécrit")
    elif cmd == "hex":
        mots, molecules, t = lire_adn(sys.argv[2])
        etat, _ = lire(mots, molecules, t)
        if etat == VARIABLE:
            print("rien n'est écrit : l'ADN est gardé tel qu'il a été lu, pour la preuve")
            sys.exit(1)
        sortie = sys.argv[3] if len(sys.argv) > 3 else os.path.splitext(sys.argv[2])[0] + ".hex"
        ecrire_hex(sortie, mots)
        print(f"le hex : {len(mots)} mots, chacun à sa place du cube -> {sortie}")
    elif cmd == "retrotranscrire":
        etat, mots, molecules, t = adnc(sys.argv[2])
        print(f"l'ARN : {NOM_ETAT[etat]}")
        if etat == VARIABLE:
            sys.exit(1)
        sortie = sys.argv[3] if len(sys.argv) > 3 else os.path.splitext(sys.argv[2])[0] + "-c.adn"
        ecrire_adn(sortie, mots, molecules, t)
        print(f"l'ADNc -> {sortie}")
    elif cmd == "abimer":
        mots, molecules, t = lire_adn(sys.argv[2])
        n = int(sys.argv[3]) if len(sys.argv) > 3 else 3
        g = random.Random(int(sys.argv[4]) if len(sys.argv) > 4 else 1)
        places = g.sample(range(len(mots)), n)
        for i in places:
            mots[i] ^= g.getrandbits(128) | 1
        ecrire_adn(sys.argv[2], mots, molecules, t)
        print(f"{n} mot(s) abîmé(s) : {sorted(places)}")
    elif cmd == "essai":
        fichiers = sys.argv[2:] or [os.path.join(racine, "exemples128", f) for f in
                                    ("panel.vtx", "chute.vtx", "scene_incrementale.vtx", "bonjour128.vtx")]
        essai(fichiers)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
