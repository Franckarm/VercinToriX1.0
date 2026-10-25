#!/usr/bin/env python3
"""La forge : un programme vtx devient un programme Rust, que rustc (LLVM) change en exécutable natif.

Ce n'est pas la traduction des mots du SPU (vtx traduire, dossier natif/) : la forge part de l'arbre du programme, tel
que vtx.py le lit et le type. Chaque fonction vtx devient une fonction Rust, chaque variable une variable Rust ; rustc
range les variables dans les registres de la machine hôte, déroule et vectorise les boucles. Autour du programme, la
machine elle-même (forge/noyau_forge.rs, qui reprend memoire.rs, miroir.rs, gif.rs, hote.rs et sortie.rs de vtx-rs) :
la mémoire du SPU (les quatre étages, les cubes et leurs fichiers miroirs ; l'image du programme compilé par vtx.py
est chargée telle quelle, les textes et les données sont aux mêmes adresses), les entrées, les sorties, les fichiers,
les services, et Gobatix (la fenêtre sous Windows, les animations GIF, les images, la souris, le clavier, les
scénarios). Chaque opération garde le sens qu'elle a sur le SPU (entiers de 32 bits sans signe, division par zéro,
flottants au NaN unique, longs signés…) : le programme forgé rend les mêmes sorties que la machine émulée.

Le ramasse-miettes du prélude cherche les références vivantes dans la pile du SPU (de pile() au haut de la pile).
Une fonction forgée qui appelle, de près ou de loin, le ramasse-miettes a donc un cadre dans la pile du SPU : avant
chaque appel qui peut ramasser, ses variables y sont recopiées (et les valeurs déjà calculées d'une expression
en cours, comme les arguments empilés par le SPU). Les autres fonctions n'ont aucun cadre.

Une variable flottante dont les bits ne sont jamais regardés (elle ne sert qu'au calcul) vit comme un flottant de la
machine : le NaN unique du SPU n'est imposé que là où les bits se voient.

Utilisation : python3 forge/forge.py PROG.vtx [-o EXE] [--rs FICHIER.rs] [--natif]
  --natif : optimise pour le processeur de cette machine (l'exécutable ne tourne alors pas forcément ailleurs)
L'exécutable prend les entrées du programme sur sa ligne de commande, et les options de Gobatix : --gif FICHIER,
--images DOSSIER, --max N, --pas K, --scenario FICHIER.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, racine)
import vtx  # noqa: E402
from vtx import VtxError, est_ref, ligne_de, LARGES2, INTEGRES, OPS_LOGIQUES, SURCHARGES, NOM_TYPE, CHAMPS, MASK  # noqa: E402

RT = {"l": "u64", "d": "u64", "w": "u128", "x": "u128", "#f": "f32", "#d": "f64"}
MOTS_TYPE = {"l": 2, "d": 2, "w": 4, "x": 4}
MARQUE = "/*R*/"          # dans le code d'une expression : un appel qui peut ramasser les miettes
SIMPLE = re.compile(r"^(v_\w+|t\d+|\d+u(32|64|128))$")
ZEROS = (("nombre", 0), ("fnombre", 0), ("dnombre", 0))
FL = {"f": ("f32", "f", "fb"), "d": ("f64", "dd", "db")}     # flottant de la machine, depuis les bits, vers les bits
OP_RS = {"==": "==", "!=": "!=", "<": "<", "<=": "<=", ">": ">", ">=": ">="}


def rt(t):
    return RT.get(t, "u32")


def mots_de(t):
    return MOTS_TYPE.get(t, 1)


def ident(nom):
    return "".join(ch if (ch.isascii() and (ch.isalnum() or ch == "_")) else f"_u{ord(ch):x}_" for ch in nom)


def lit(v, t="e"):
    return f"{v & ((1 << (32 * mots_de(t))) - 1)}{rt(t)}"


# ------------------------------------------------------------------------------------------------------------------
# La compilation de vtx.py, pas à pas, pour garder l'arbre des fonctions (le même que celui du Generateur).

def compiler_arbre(src, dossier=None, partition=True):
    if "importer" in src:
        lignes, _ = vtx.resoudre_carte(src, dossier, "programme")
        src = "\n".join(lignes)
    a = vtx.Analyseur(vtx.lexer(src))
    fs = a.programme()
    if a.donnees:
        fs = vtx.injecter_donnees(fs, a.donnees)
    noms = {f.nom for f in fs}
    ap = vtx.Analyseur(vtx.lexer(vtx.PRELUDE))
    ap.textes = a.textes
    pre = [f for f in ap.programme() if f.nom not in noms]
    for f in pre:
        f.origine = "prélude"
    fs = fs + pre
    vtx.typer_textes(fs, a.types_champs)
    gardees = vtx.elaguer(fs)
    reserve = {f.nom: f for f in fs if f not in gardees}
    vtx.DERNIERE_PARTITION["accords"], vtx.DERNIERE_PARTITION["notes"] = [], {}
    if partition:
        vtx.DERNIERE_PARTITION["accords"], vtx.DERNIERE_PARTITION["notes"] = vtx.partitionner(gardees, None)
    g = vtx.Generateur(gardees, True, a.donnees, reserve)
    g.structs, g.types_champs, g.textes = a.structs, a.types_champs, a.textes
    asm = g.generer()
    mots, _infos, etiquettes = vtx._assembler(asm)
    return g, mots, etiquettes


# ------------------------------------------------------------------------------------------------------------------

class Forge(vtx.Generateur):
    """Le Generateur de vtx.py pour les types et les règles ; chaque expression devient une expression Rust."""

    def __init__(self, g, etiquettes):
        super().__init__(list(g.fonctions.values()), True, g.blobs, {})
        self.structs, self.types_champs, self.textes = g.structs, g.types_champs, g.textes
        self.etiq = etiquettes
        self.ramasse = None          # premier passage : le graphe des appels ; second : les fonctions qui ramassent
        self.graphe = {}
        self.pile_directe = set()

    # ------------------------------------------------------------ outils
    def tmp(self):
        self.ntmp += 1
        return f"t{self.ntmp}"

    def peut_ramasser(self, nom):
        return self.ramasse is not None and nom in self.ramasse

    def bloc(self, parts, fin):
        """Évalue les parties (code, type) dans l'ordre, chacune dans une variable ; fin(noms) donne le résultat. Une
        valeur gardée pendant un appel qui peut ramasser les miettes est posée dans la pile du SPU, comme le SPU
        l'empile : le ramasse-miettes la voit."""
        noms, lets, pousses = [], [], 0
        for i, (code, t) in enumerate(parts):
            if SIMPLE.match(code):
                noms.append(code)
                continue
            n = self.tmp()
            lets.append(f"let {n}: {rt(t)} = {code};")
            noms.append(n)
            if not t.startswith("#") and any(MARQUE in c for c, _ in parts[i + 1:]):
                for k in range(mots_de(t)):
                    lets.append(f"c.sp = c.sp.wrapping_sub(1); c.mem.ecrit0(c.sp, ({n} >> {32 * k}) as u32);"
                                if k else f"c.sp = c.sp.wrapping_sub(1); c.mem.ecrit0(c.sp, {n} as u32);")
                pousses += mots_de(t)
        res = fin(noms)
        if not lets:
            return f"({res})"
        marque = MARQUE if any(MARQUE in c for c, _ in parts) or MARQUE in res else ""
        if pousses:
            return f"{{ {' '.join(lets)} let r_ = {res}; c.sp = c.sp.wrapping_add({pousses}); r_ }}{marque}"
        return f"{{ {' '.join(lets)} {res} }}{marque}"

    def ecrire_ligne(self, t):
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
        kinds, locales = {}, []
        for nom, l, kind, st in loc:
            chaque = st[0] == "soit"
            if nom in self.vars:
                if kinds.get(nom) == "pour" and kind == "pour":
                    t2 = (st[4] or self.typ(st[2])) if chaque else "e"
                    if t2 != self.vtypes.get(nom, "e"):
                        raise VtxError(f"ligne {l} : la variable de boucle « {nom} » change de type : donnez-lui un autre nom")
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
        # le cadre dans la pile du SPU, si la fonction appelle une fonction qui ramasse
        self.toutes = params + locales
        self.places, n = {}, 0
        for v in self.toutes:
            self.places[v] = n
            n += mots_de(self.vtypes[v])
        self.taille_cadre = n
        self.purs = self.analyser_purs(f)
        self.cadre_actif = (self.ramasse is not None and n > 0
                            and any(x in self.ramasse for x in self.graphe.get(f.nom, ())))
        self.lignes, self.niveau = [], 1
        for s in f.corps:
            self.instr(s)
        corps = self.lignes
        self.graphe[f.nom] = self.appelees
        cadre = self.cadre_actif
        tr = rt(f.rtype)
        nom = ident(f.nom)
        sig = ", ".join((f"a_{ident(p)}: u32" if p in self.purs and self.vtypes[p] == "f" else
                         f"a_{ident(p)}: u64" if p in self.purs else f"mut v_{ident(p)}: {rt(self.vtypes[p])}") for p in params)
        sig = ("c: &mut Ctx" + (", " + sig if sig else ""))
        out = []
        if cadre:
            noms = ", ".join(f"v_{ident(p)}" for p in params)
            sig0 = ", ".join(["c: &mut Ctx"] + [f"v_{ident(p)}: {rt(self.vtypes[p])}" for p in params])
            out.append(f"fn f_{nom}({sig0}) -> {tr} {{")
            out.append(f"    let sp0 = c.sp; c.sp = sp0.wrapping_sub({n});")
            out.append(f"    let r = fc_{nom}(c{', ' + noms if noms else ''}); c.sp = sp0; r")
            out.append("}")
            out.append("#[inline(always)]")
            out.append(f"fn fc_{nom}({sig}) -> {tr} {{")
            out.append("    let fp = c.sp;")
        else:
            out.append(f"fn f_{nom}({sig}) -> {tr} {{")
        for p in params:
            if p in self.purs:
                out.append(f"    let mut v_{ident(p)}: {FL[self.vtypes[p]][0]} = {FL[self.vtypes[p]][1]}(a_{ident(p)});")
        for v in locales:
            if v in self.purs:
                out.append(f"    let mut v_{ident(v)}: {FL[self.vtypes[v]][0]} = 0.0;")
            else:
                out.append(f"    let mut v_{ident(v)}: {rt(self.vtypes[v])} = 0;")
        out += corps
        out.append("    0")
        out.append("}")
        return "\n".join(out)

    def analyser_purs(self, f):
        """Les variables flottantes dont les bits ne sont jamais regardés : elles ne servent qu'au calcul (opérande
        d'une opération ou d'une comparaison flottante, conversion en entier, racine…) ou à en remplir une autre de
        même sorte. Elles vivent comme flottants de la machine, sans passer par les bits à chaque opération."""
        cand = {v for v in self.toutes if self.vtypes[v] in ("f", "d")}
        if not cand or getattr(self, "sans_purs", False):
            return set()
        mauvais, copies = set(), []
        CONV = ("entier", "arrondi", "racine", "flottant_64", "flottant", "arrondi_long")
        CONV_SURES = {("entier", "f"), ("entier", "d"), ("arrondi", "f"), ("arrondi", "d"), ("racine", "f"),
                      ("racine", "d"), ("arrondi_long", "d"), ("flottant", "d"), ("flottant_64", "f")}

        def ex(e, bon=False):
            if isinstance(e, list):
                for x in e:
                    ex(x)
                return
            if not isinstance(e, tuple) or not e:
                return
            g = e[0]
            if not isinstance(g, str):
                # un n-uplet qui n'est pas un noeud (les tâches d'un accord : instruction, note, nom)
                for x in e:
                    ex(x)
                return
            if g == "var" and len(e) == 3 and isinstance(e[1], str):
                if not bon:
                    mauvais.add(e[1])
                return
            if g == "bin" and isinstance(e[1], str) and len(e) >= 4:
                op = e[1]
                if op in ("+", "-", "*", "/") and self.typ(e) in ("f", "d"):
                    sous = not (op == "-" and e[2] in ZEROS)
                    ex(e[2], sous)
                    ex(e[3], sous)
                    return
                if op in vtx.COMPARAISONS:
                    ta, tb = self.typ(e[2]), self.typ(e[3])
                    if {ta, tb} <= {"e", "f", "d"} and {ta, tb} & {"f", "d"}:
                        ex(e[2], True)
                        ex(e[3], True)
                        return
            if g == "appel" and len(e) > 2 and isinstance(e[2], list) and len(e[2]) == 1:
                # conversions dont le résultat ne montre pas les bits de l'argument (flottant() d'un flottant ou
                # flottant_64() d'un flottant_64 ne changent rien : les bits passent, la variable n'est pas « pure »)
                ta = self.typ(e[2][0]) if e[1] in CONV else None
                if (e[1], ta) in CONV_SURES:
                    ex(e[2][0], True)
                    return
            if g in ("soit", "affecter") and isinstance(e[1], str):
                if e[1] in cand and len(e) > 2 and isinstance(e[2], tuple) and e[2][0] == "var":
                    copies.append((e[1], e[2][1]))
                else:
                    ex(e[2], e[1] in cand)
                return
            for x in e[1:]:
                ex(x)
        try:
            ex(f.corps)
        except VtxError:
            return set()
        purs = cand - mauvais
        change = True
        while change:
            change = False
            for d, src in copies:
                if src in purs and d not in purs:
                    purs.discard(src)
                    change = True
        return purs

    def recopier_cadre(self):
        """Les variables de la fonction dans son cadre de la pile du SPU (avant un appel qui peut ramasser)."""
        if not getattr(self, "cadre_actif", False):
            return ""
        s = []
        for v in self.toutes:
            p, t = self.places[v], self.vtypes[v]
            nv = f"v_{ident(v)}.to_bits()" if v in self.purs else f"v_{ident(v)}"
            for k in range(mots_de(t)):
                val = f"({nv} >> {32 * k}) as u32" if k else f"{nv} as u32"
                s.append(f"c.mem.ecrit0(fp.wrapping_add({p + k}), {val});")
        return " ".join(s) + " "

    # ------------------------------------------------------------ instructions
    def affecter_rs(self, nom, code):
        self.ecrire_ligne(f"v_{ident(nom)} = {code};")

    def instr(self, s):
        g = s[0]
        if g in ("soit", "affecter") and s[1] in self.purs:
            self.variable(s[1], s[3])
            self.affecter_rs(s[1], self.valfl(s[2], self.vtypes[s[1]]))
        elif g == "soit":
            t = self.vtypes[s[1]]
            if est_ref(t) and len(s) > 4 and s[4] == t and s[2][0] in ("var", "appel") and self.typ(s[2]) == "e":
                code = self.val(s[2])
            else:
                code = self.val(s[2], t)
            self.affecter_rs(s[1], code)
        elif g == "affecter":
            self.variable(s[1], s[3])
            t = self.vtypes[s[1]]
            self.affecter_rs(s[1], self.val(s[2], t))
        elif g == "ecrire_champ":
            _st, pos, t = self.champ_de(("champ_ref", s[1], s[2], s[4]))
            if t in LARGES2:
                raise VtxError(f"ligne {s[4]} : un champ ne peut pas contenir un {NOM_TYPE[t]}")
            v = self.val(s[3], t)
            b = self.val(s[1])
            self.ecrire_ligne(self.bloc([(v, t), (b, "e")],
                                        lambda n: f"c.mem.ecrit({n[1]} >> 24, {n[1]}.wrapping_add({pos}), {n[0]})") + ";")
        elif g == "ecrire":
            if self.typ(s[3]) in LARGES2:
                raise VtxError(f"ligne {s[4]} : un {NOM_TYPE[self.typ(s[3])]} occupe deux mots : écrivez bas(x) et haut(x) séparément")
            et = s[1]
            if isinstance(et, int):
                a = self.val(s[2], "e")
                v = self.val(s[3])
                if et == 0:
                    self.ecrire_ligne(self.bloc([(a, "e"), (v, "e")], lambda n: f"c.mem.ecrit0({n[0]}, {n[1]})") + ";")
                else:
                    self.ecrire_ligne(self.bloc([(a, "e"), (v, "e")], lambda n: f"c.mem.ecrit({et}, {n[0]}, {n[1]})") + ";")
            else:
                a = self.val(s[2], "e")
                e_ = self.val(et, "e")
                v = self.val(s[3])
                self.ecrire_ligne(self.bloc([(a, "e"), (e_, "e"), (v, "e")],
                                            lambda n: f"c.mem.ecrit({n[1]}, {n[0]}, {n[2]})") + ";")
        elif g == "si":
            self.ecrire_ligne(f"if {self.cond(s[1])} {{")
            self.niveau += 1
            for x in s[2]:
                self.instr(x)
            self.niveau -= 1
            if s[3] is not None:
                self.ecrire_ligne("} else {")
                self.niveau += 1
                for x in s[3]:
                    self.instr(x)
                self.niveau -= 1
            self.ecrire_ligne("}")
        elif g == "tantque":
            self.nboucle += 1
            lb = f"'b{self.nboucle}"
            self.ecrire_ligne(f"{lb}: loop {{")
            self.niveau += 1
            self.ecrire_ligne(f"if !{self.cond(s[1])} {{ break; }}")
            self.boucles.append((f"continue {lb}", f"break {lb}"))
            for x in s[2]:
                self.instr(x)
            self.boucles.pop()
            self.niveau -= 1
            self.ecrire_ligne("}")
        elif g == "pour":
            self.variable(s[1], s[5])
            self.nboucle += 1
            lb, lc = f"'b{self.nboucle}", f"'c{self.nboucle}"
            v = f"v_{ident(s[1])}"
            self.ecrire_ligne(f"{v} = {self.val(s[2], 'e')};")
            self.ecrire_ligne(f"{lb}: loop {{")
            self.niveau += 1
            self.ecrire_ligne(f"if !{self.cond(('bin', '<', ('var', s[1], s[5]), s[3]))} {{ break; }}")
            self.ecrire_ligne(f"{lc}: {{")
            self.niveau += 1
            self.boucles.append((f"break {lc}", f"break {lb}"))
            for x in s[4]:
                self.instr(x)
            self.boucles.pop()
            self.niveau -= 1
            self.ecrire_ligne("}")
            pas = s[6] if len(s) > 6 else 1
            self.ecrire_ligne(f"{v} = {v}.wrapping_add({pas & MASK});")
            self.niveau -= 1
            self.ecrire_ligne("}")
        elif g == "asm":
            if self.f.nom != "__init":
                raise VtxError("la forge ne traduit pas l'assembleur écrit dans le programme")
            # la copie des données (injecter_donnees) : de l'image du programme vers leur étage
            for i, (et, adr, vals) in enumerate(self.blobs):
                if vals:
                    src = self.etiq[f"DONNEES{i}"]
                    self.ecrire_ligne(f"for k in 0..{len(vals)}u32 {{ let v = c.mem.lit0({src}u32.wrapping_add(k)); "
                                      f"c.mem.ecrit({et}, {adr}u32.wrapping_add(k), v); }}")
        elif g == "bloc":
            for x in s[1]:
                self.instr(x)
        elif g == "segments":
            pre, _ = vtx.deplier_segments(s)
            for x in pre:
                self.instr(x)
            self.instr(("pour", s[1], ("var", f"__sa{s[7]}", s[5]), ("var", f"__sb{s[7]}", s[5]), s[4], s[5], 1))
        elif g == "accord":
            for mesure in s[2]:
                for st, _note, _nom in mesure:
                    self.instr(st)
        elif g in ("arreter", "continuer"):
            if not self.boucles:
                raise VtxError(f"ligne {s[1]} : « {'arrêter' if g == 'arreter' else 'continuer'} » hors d'une boucle")
            self.ecrire_ligne(self.boucles[-1][1 if g == "arreter" else 0] + ";")
        elif g == "retour":
            if s[1] is None:
                self.ecrire_ligne("return 0;")
            else:
                self.ecrire_ligne(f"return {self.val(s[1], self.f.rtype)};")
        else:
            self.ecrire_ligne(f"let _ = {self.val(s[1])};")

    # ------------------------------------------------------------ conditions
    def cond(self, e):
        """Une condition : une expression Rust booléenne."""
        self.refuser_logique(e)
        if e[0] == "bin" and e[1] in ("&&", "||"):
            return f"({self.cond(e[2])} {e[1]} {self.cond(e[3])})"
        if e[0] == "non_log":
            return f"!{self.cond(e[1])}"
        if e[0] == "bin" and e[1] in vtx.COMPARAISONS:
            code, nature = self.comparaison(e)
            return code if nature == "b" else f"({code} != 0)"
        if self.typ(e) == "x":
            raise VtxError(f"ligne {ligne_de(e)} : un flottant_petuar a un état à quatre valeurs et ne sert pas de condition : "
                           f"comparez-le, ou utilisez « selon etat(x) »")
        t = self.typ(e)
        v = self.val(e)
        if t == "f":
            return f"({v} & 0x7FFF_FFFF != 0)"
        if t == "d":
            return f"({v} & 0x7FFF_FFFF_FFFF_FFFF != 0)"
        return f"({v} != 0)"

    def comparaison(self, e):
        """(code, nature) : nature « b » pour un booléen Rust, « u » pour un entier dont seul le zéro est faux."""
        self.typ(e)
        op, a, b = e[1], e[2], e[3]
        ta, tb = self.typ(a), self.typ(b)
        if "q" in (ta, tb) or est_ref(ta) or est_ref(tb):
            t = "q" if "q" in (ta, tb) else (ta if est_ref(ta) else tb)
            return self.bloc([(self.val(a, t), "e"), (self.val(b, t), "e")], lambda n: f"{n[0]} {OP_RS[op]} {n[1]}"), "b"
        t = self.joindre(ta, tb, ligne_de(e), op)
        if t == "x":
            nom = {"==": "__pq_eq", "!=": "__pq_ne", "<": "__pq_lt", "<=": "__pq_le", ">": "__pq_gt", ">=": "__pq_ge"}[op]
            return self.appel(("appel", nom, [self.bits_x(a), self.bits_x(b)], ligne_de(e))), "u"
        if t == "w" and op not in ("==", "!="):
            a_, b_ = (a, b) if op in ("<", ">=") else (b, a)
            r = self.appel(("appel", "__qlt", [a_, b_], ligne_de(e)))
            return (f"({r} ^ 1)" if op in ("<=", ">=") else r), "u"
        if t in ("f", "d"):
            pa, pb = self.valfl(a, t), self.valfl(b, t)
            return self.bloc([(pa, "#" + t), (pb, "#" + t)], lambda n: f"{n[0]} {OP_RS[op]} {n[1]}"), "b"
        pa, pb = self.val(a, t), self.val(b, t)
        if t == "l":
            return self.bloc([(pa, t), (pb, t)], lambda n: f"({n[0]} as i64) {OP_RS[op]} ({n[1]} as i64)"), "b"
        return self.bloc([(pa, t), (pb, t)], lambda n: f"{n[0]} {OP_RS[op]} {n[1]}"), "b"

    # ------------------------------------------------------------ expressions
    def conv_rs(self, code, t, voulu, ligne):
        if t == voulu:
            return code
        if (t, voulu) == ("e", "f"):
            return f"fb({code} as f32)"
        if (t, voulu) == ("e", "l"):
            return f"({code} as u64)"
        if (t, voulu) == ("e", "w"):
            return f"({code} as u128)"
        if (t, voulu) == ("e", "d"):
            return f"db({code} as f64)"
        if (t, voulu) == ("f", "d"):
            return f"db(f({code}) as f64)"
        raise VtxError(f"ligne {ligne} : conversion implicite impossible de {NOM_TYPE[t]} vers {NOM_TYPE[voulu]} : "
                       f"utilisez entier(), flottant(), long() ou logique()")

    def val(self, e, voulu=None):
        """L'expression e en Rust, convertie au type voulu s'il est donné."""
        if e[0] == "blit":
            e = ("qnombre", e[1]) if voulu == "q" else ("nombre", e[2])
        if est_ref(voulu) and e == ("nombre", 0):
            return "0u32"
        t = self.typ(e)
        if est_ref(t):
            if e[0] == "nouveau_de":
                code = self.val_e(e[2])
            elif e[0] == "construire":
                parts = [(self.val_e(e[3]), "e")]
                champs = []
                for champ, v in e[2]:
                    pos = self.structs[e[1]].index(champ)
                    tc = self.types_champs.get(e[1], {}).get(champ, "e")
                    if tc in LARGES2:
                        raise VtxError(f"ligne {e[4]} : un champ ne peut pas contenir un {NOM_TYPE[tc]}")
                    parts.append((self.val(v, tc), "e"))
                    champs.append(pos)
                # chaque champ est écrit dès qu'il est calculé, dans l'ordre (comme le SPU)
                code = self.construire_rs(parts, champs)
            elif e[0] in ("champ_ref", "champ"):
                _st, pos, _t = self.champ_de(e)
                code = self.bloc([(self.val(e[1]), "e")], lambda n: f"c.mem.lit({n[0]} >> 24, {n[0]}.wrapping_add({pos}))")
            else:
                code = self.val_e(e)
            if voulu is not None and voulu != t:
                return self.conv_rs(code, t, voulu, ligne_de(e))
            return code
        if voulu == "x" and t in ("e", "f", "d"):
            return self.conversion("flottant_petuar", [e], ligne_de(e))
        if t == "e":
            code = self.val_e(e)
        elif t == "f":
            code = self.val_f(e)
        elif t == "q":
            code = lit(e[1]) if e[0] == "qnombre" else self.val_e(e)
        elif t == "d":
            code = self.val_d(e)
        elif t == "w":
            code = self.val_w(e)
        elif t == "x":
            code = self.val_x(e)
        else:
            code = self.val_l(e)
        if voulu is not None and voulu != t:
            return self.conv_rs(code, t, voulu, ligne_de(e))
        return code

    def construire_rs(self, parts, champs):
        """Structure { … } : l'adresse du bloc neuf, puis chaque champ calculé et écrit tour à tour."""
        n0 = self.tmp()
        s = [f"let {n0}: u32 = {parts[0][0]};"]
        reste = parts[1:]
        garde = any(MARQUE in c for c, _ in reste)
        if garde:
            s.append(f"c.sp = c.sp.wrapping_sub(1); c.mem.ecrit0(c.sp, {n0});")
        for (code, _t), p in zip(reste, champs):
            n = self.tmp()
            s.append(f"let {n}: u32 = {code}; c.mem.ecrit({n0} >> 24, {n0}.wrapping_add({p}), {n});")
        if garde:
            s.append("c.sp = c.sp.wrapping_add(1);")
        marque = MARQUE if any(MARQUE in c for c, _ in parts) else ""
        return f"{{ {' '.join(s)} {n0} }}{marque}"

    def var_rs(self, e):
        self.variable(e[1], e[2])
        if e[1] in self.purs:
            raise VtxError(f"forge : la variable flottante « {e[1]} » est lue comme des bits (erreur de la forge)")
        return f"v_{ident(e[1])}"

    def valfl(self, e, t):
        """e comme flottant de la machine (f32 pour t = « f », f64 pour « d ») : pas de NaN unique au milieu d'un calcul
        (il ne change rien tant que les bits ne sont pas regardés) ; e est converti au type t comme sur le SPU."""
        ty, de, _vers = FL[t]
        te = "q" if e[0] == "blit" else self.typ(e)
        if e[0] == "var" and e[1] in self.purs and te == t:
            self.variable(e[1], e[2])
            return f"v_{ident(e[1])}"
        if te == t and e[0] == "bin" and e[1] in ("+", "-", "*", "/") and not (e[1] == "-" and e[2] in ZEROS):
            a, b = self.valfl(e[2], t), self.valfl(e[3], t)
            return self.bloc([(a, "#" + t), (b, "#" + t)], lambda n: f"{n[0]} {e[1]} {n[1]}")
        if te == "e" and e[0] != "blit":
            return f"({self.val(e)} as {ty})"
        if te == "f" and t == "d":
            return f"({self.valfl(e, 'f')} as f64)"
        return f"{de}({self.val(e, t)})"

    def val_e(self, e):
        g = e[0]
        if g == "nombre":
            return lit(e[1])
        if g == "var":
            return self.var_rs(e)
        if g == "etiq":
            return lit(self.etiq[e[1].upper()])
        if g == "non":
            return f"(!{self.val(e[1])})"
        if g == "non_log":
            return f"(!{self.cond(e[1])} as u32)"
        if g == "bin":
            op = e[1]
            if op in ("&&", "||"):
                return f"({self.cond(e)} as u32)"
            if op in vtx.COMPARAISONS:
                code, nature = self.comparaison(e)
                return f"(({code}) as u32)" if nature == "b" else code
            a, b = self.val(e[2], "e"), self.val(e[3], "e")
            if op in ("<<q", ">>q"):
                sh = "wrapping_shl" if op == "<<q" else "wrapping_shr"
                return self.bloc([(a, "e"), (b, "e")], lambda n: f"{n[0]}.{sh}({n[1]}.wrapping_add({n[1]}))")
            forme = {"+": "{0}.wrapping_add({1})", "-": "{0}.wrapping_sub({1})", "*": "{0}.wrapping_mul({1})",
                     "/": "divu({0}, {1})", "%": "modu({0}, {1})", "&": "{0} & {1}", "|": "{0} | {1}", "^": "{0} ^ {1}",
                     "<<": "{0}.wrapping_shl({1})", ">>": "{0}.wrapping_shr({1})"}[op]
            return self.bloc([(a, "e"), (b, "e")], lambda n: forme.format(*n))
        if g == "champ_ref" or (g == "champ" and est_ref(self.typ(e[1]))):
            _st, pos, _t = self.champ_de(e)
            return self.bloc([(self.val(e[1]), "e")], lambda n: f"c.mem.lit({n[0]} >> 24, {n[0]}.wrapping_add({pos}))")
        if g == "champ":
            x = self.val(e[1])
            return f"(({x} >> {CHAMPS[e[2]]}) & 255)"
        if g == "quit":
            return self.bloc([(self.val(e[1]), "e"), (self.val(e[2], "e"), "e")],
                             lambda n: f"({n[0]} >> (({n[1]} & 15) * 2)) & 3")
        if g == "lire":
            if isinstance(e[1], int):
                a = self.val(e[2], "e")
                if e[1] == 0:
                    return self.bloc([(a, "e")], lambda n: f"c.mem.lit0({n[0]})")
                return self.bloc([(a, "e")], lambda n: f"c.mem.lit({e[1]}, {n[0]})")
            return self.bloc([(self.val(e[2], "e"), "e"), (self.val(e[1], "e"), "e")],
                             lambda n: f"c.mem.lit({n[1]}, {n[0]})")
        if g == "appel":
            return self.appel(e)
        raise VtxError(f"ligne {ligne_de(e)} : expression inattendue ({g})")

    def val_f(self, e):
        g = e[0]
        if g == "fnombre":
            return lit(e[1])
        if g == "var":
            return self.var_rs(e)
        if g == "bin":
            op = e[1]
            if op == "-" and e[2] in (("nombre", 0), ("fnombre", 0)):
                return f"({self.val(e[3], 'f')} ^ 0x8000_0000)"
            return f"fb({self.valfl(e, 'f')})"
        if g == "appel":
            return self.appel(e)
        if g in ("champ_ref", "champ"):
            return self.val_e(e)
        raise VtxError(f"ligne {ligne_de(e)} : expression flottante inattendue")

    def val_d(self, e):
        g = e[0]
        if g == "dnombre":
            return lit(e[1], "d")
        if g == "var":
            return self.var_rs(e)
        if g == "bin":
            op = e[1]
            if op == "-" and e[2] in (("nombre", 0), ("fnombre", 0), ("dnombre", 0)):
                return f"({self.val(e[3], 'd')} ^ 0x8000_0000_0000_0000)"
            return f"db({self.valfl(e, 'd')})"
        if g == "appel":
            return self.appel(e)
        raise VtxError(f"ligne {ligne_de(e)} : expression flottante_64 inattendue")

    def val_w(self, e):
        g = e[0]
        if g == "wnombre":
            return lit(e[1], "w")
        if g == "var":
            return self.var_rs(e)
        if g == "non":
            return f"(!{self.val(e[1], 'w')})"
        if g == "bin":
            op, l = e[1], ligne_de(e)
            if op in ("*", "/", "%"):
                if op == "*":
                    return self.appel(("appel", "__qmul", [e[2], e[3]], l))
                return self.appel(("appel", "__qdiv", [e[2], e[3], ("nombre", 1 if op == "%" else 0)], l))
            if op in ("<<", ">>"):
                return self.appel(("appel", "__qshl" if op == "<<" else "__qsar", [e[2], e[3]], l))
            a, b = self.val(e[2], "w"), self.val(e[3], "w")
            if op in ("+", "-"):
                m = "wrapping_add" if op == "+" else "wrapping_sub"
                return self.bloc([(a, "w"), (b, "w")], lambda n: f"{n[0]}.{m}({n[1]})")
            if op in vtx.BITS_OPS:
                return self.bloc([(a, "w"), (b, "w")], lambda n: f"{n[0]} {op} {n[1]}")
            raise VtxError(f"ligne {l} : « {op} » ne s'applique pas à un entier_128")
        if g == "appel":
            return self.appel(e)
        raise VtxError(f"ligne {ligne_de(e)} : expression entier_128 inattendue")

    def val_x(self, e):
        g = e[0]
        if g == "xnombre":
            return lit(e[1], "x")
        if g == "var":
            return self.var_rs(e)
        if g == "bin":
            op, l = e[1], ligne_de(e)
            if op == "-" and e[2] in (("nombre", 0), ("fnombre", 0), ("dnombre", 0)):
                return self.appel(("appel", "__pq_neg", [self.bits_x(e[3])], l))
            if op not in ("+", "-", "*", "/"):
                raise VtxError(f"ligne {l} : « {op} » ne s'applique pas à un flottant_petuar")
            nom = {"+": "__pq_add", "-": "__pq_sub", "*": "__pq_mul", "/": "__pq_div"}[op]
            return self.appel(("appel", nom, [self.bits_x(e[2]), self.bits_x(e[3])], l))
        if g == "appel":
            return self.appel(e)
        raise VtxError(f"ligne {ligne_de(e)} : expression flottant_petuar inattendue")

    def val_l(self, e):
        g = e[0]
        if g == "lnombre":
            return lit(e[1], "l")
        if g == "var":
            return self.var_rs(e)
        if g == "non":
            return f"(!{self.val(e[1], 'l')})"
        if g == "bin":
            op, l = e[1], ligne_de(e)
            if op in ("/", "%"):
                return self.appel(("appel", "__ldiv", [e[2], e[3], ("nombre", 1 if op == "%" else 0)], l))
            if op in ("<<", ">>"):
                return self.appel(("appel", "__lshl" if op == "<<" else "__lsar", [e[2], e[3]], l))
            a, b = self.val(e[2], "l"), self.val(e[3], "l")
            forme = {"+": "{0}.wrapping_add({1})", "-": "{0}.wrapping_sub({1})", "*": "{0}.wrapping_mul({1})",
                     "&": "{0} & {1}", "|": "{0} | {1}", "^": "{0} ^ {1}"}.get(op)
            if forme is None:
                raise VtxError(f"ligne {l} : « {op} » ne s'applique pas à un long")
            return self.bloc([(a, "l"), (b, "l")], lambda n: forme.format(*n))
        if g == "appel":
            return self.appel(e)
        raise VtxError(f"ligne {ligne_de(e)} : expression longue inattendue")

    # ------------------------------------------------------------ appels
    def logique_rs(self, nom, args, ligne):
        t = self.typ(("appel", nom, args, ligne))
        if nom in ("logique", "comme_logique"):
            if len(args) != 1:
                raise VtxError(f"ligne {ligne} : « {nom} » attend 1 argument")
            ta = "q" if args[0][0] == "blit" else self.typ(args[0])
            if ta == "q":
                return self.val(args[0], "q")
            if ta != "e":
                raise VtxError(f"ligne {ligne} : « {nom} » prend un entier")
            x = self.val(args[0])
            if nom == "comme_logique":
                return f"({x} & 3)"
            return f"(if {x} == 0 {{ 1u32 }} else {{ 2u32 }})"
        if OPS_LOGIQUES[nom] == 2:
            parts = [(self.val(args[0], t), "e"), (self.val(args[1], t), "e")]
        else:
            parts = [(self.val(args[0], t), "e")]
        forme = {"et4": "(({0} & {1}) & 0xAAAA_AAAA) | (({0} | {1}) & 0x5555_5555)",
                 "ou4": "(({0} | {1}) & 0xAAAA_AAAA) | (({0} & {1}) & 0x5555_5555)",
                 "fusion": "{0} | {1}", "consensus": "{0} & {1}"}.get(nom)
        if forme is None:
            if nom == "anti" and t != "q":
                forme = "!((({0} & 0xAAAA_AAAA) >> 1) | (({0} & 0x5555_5555) << 1))"
            elif nom == "anti":
                forme = "(((({0} & 0xAAAA_AAAA) >> 1) | (({0} & 0x5555_5555) << 1)) ^ 3)"
            else:
                forme = "((({0} & 0xAAAA_AAAA) >> 1) | (({0} & 0x5555_5555) << 1))"
        return self.bloc(parts, lambda n: forme.format(*n))

    def appel(self, e):
        nom, args, ligne = e[1], e[2], e[3]
        if nom == "__code_logique":
            ta = "q" if args[0][0] == "blit" else self.typ(args[0])
            if ta != "q":
                raise VtxError(f"ligne {ligne} : un tableau de logique reçoit des logiques (vrai, faux, inconnu, variable), "
                               f"pas un {NOM_TYPE[ta]} : utilisez logique() ou comme_logique()")
            return self.val(args[0], "q")
        if nom in OPS_LOGIQUES or nom in ("logique", "comme_logique"):
            return self.logique_rs(nom, args, ligne)
        if nom in INTEGRES:
            if len(args) != INTEGRES[nom]:
                raise VtxError(f"ligne {ligne} : « {nom} » attend {INTEGRES[nom]} argument(s)")
            return self.integre(nom, args, ligne)
        if nom in SURCHARGES and self.typ(e) == "w":
            return self.appel(("appel", "__q" + nom, args, ligne))
        if nom in SURCHARGES and self.typ(e) == "x":
            return self.appel(("appel", "__pq_" + nom, [self.bits_x(a) for a in args], ligne))
        if nom in SURCHARGES and self.typ(e) in ("f", "l", "d"):
            return self.surcharge_rs(nom, args, self.typ(e), ligne)
        if nom in ("afficher", "ecrire", "texte") and len(args) == 1:
            pf = self.fonctions.get(nom) or self.reserve.get(nom)
            if pf is not None and getattr(pf, "origine", "") == "prélude":
                a0 = args[0]
                ta = "q" if a0[0] == "blit" else self.typ(a0)
                if ta in ("f", "l", "q", "d", "w", "x"):
                    nom = "__" + nom + "_" + ta
        f = self.signature(nom, ligne)
        if len(args) != len(f.params):
            raise VtxError(f"ligne {ligne} : « {nom} » attend {len(f.params)} argument(s)")
        self.appelees.add(nom)
        parts = [(self.val(a, t), t) for a, t in zip(args, f.ptypes)]
        ramasse = self.peut_ramasser(nom)
        avant = self.recopier_cadre() if ramasse else ""

        def fin(n):
            appel = f"f_{ident(nom)}(c{''.join(', ' + x for x in n)})"
            return f"{{ {avant}{appel} }}" if avant else appel
        code = self.bloc(parts, fin) if parts else f"({fin([])})"
        return code + MARQUE if ramasse and MARQUE not in code else code

    def integre(self, nom, args, ligne):
        a = args
        if nom == "sortie":
            t = self.typ(a[0])
            x = self.val(a[0])
            n = mots_de(t)
            pousse = " ".join(f"c.es.sorties.push(({{0}} >> {32 * k}) as u32);" for k in range(n))
            return self.bloc([(x, t)], lambda m: f"{{ {pousse.format(m[0])} {m[0]} as u32 }}")
        if nom == "entrée":
            return "c.es.entree()"
        if nom == "cmp3":
            return f"(!{self.val(a[0], 'e')})"
        if nom == "lire_car":
            return self.bloc([(self.val(a[0], "e"), "e")], lambda m: f"c.es.entc({m[0]})")
        if nom == "ecrire_car":
            return self.bloc([(self.val(a[1], "e"), "e"), (self.val(a[0], "e"), "e")],
                             lambda m: f"{{ c.es.sorc({m[0]}, {m[1]}); 0u32 }}")
        if nom in ("ouvrir_lecture", "ouvrir_ecriture", "fermer", "fin_de"):
            code = {"ouvrir_lecture": 1, "ouvrir_ecriture": 2, "fermer": 3, "fin_de": 4}[nom]
            return self.bloc([(self.val(a[0], "e"), "e")], lambda m: f"c.es.sys(&c.mem, {code}, {m[0]})")
        if nom == "bruit":
            return "c.es.sys(&c.mem, 5, 0)"
        if nom == "pile":
            self.appelees.add("<pile>")
            return "c.sp"
        if nom == "__service":
            return self.bloc([(self.val(a[0], "e"), "e"), (self.val(a[1], "e"), "e")],
                             lambda m: f"c.es.sys(&c.mem, {m[0]}, {m[1]})")
        if nom == "nb_bits":
            return f"{self.val(a[0], 'e')}.count_ones()"
        if nom == "qegal":
            return self.bloc([(self.val(a[0], "e"), "e"), (self.val(a[1], "e"), "e")],
                             lambda m: f"{{ let x = {m[0]} ^ {m[1]}; !(x | (x >> 1)) & 0x5555_5555 }}")
        if nom == "gemv":
            parts = [(self.val(x, "e"), "e") for x in a]
            return self.bloc(parts, lambda m: "{ " + " ".join(f"c.sp = c.sp.wrapping_sub(1); c.mem.ecrit0(c.sp, {x});" for x in m)
                             + " gemv(&c.mem, c.sp); c.sp = c.sp.wrapping_add(5); 0u32 }")
        if nom in ("min4", "max4", "addm4", "gdot"):
            parts = [(self.val(a[0], "e"), "e"), (self.val(a[1], "e"), "e")]
            if nom == "gdot":
                return self.bloc(parts, lambda m: f"(dot({m[0]}, {m[1]}) as u32)")
            code = {"min4": 0x10, "max4": 0x11, "addm4": 0x13}[nom]
            return self.bloc(parts, lambda m: f"quits({m[0]}, {m[1]}, {code})")
        return self.conversion(nom, args, ligne)

    def conversion(self, nom, args, ligne):
        x = args[0]
        t = self.typ(x)

        def interdit():
            raise VtxError(f"ligne {ligne} : « {nom} » ne s'applique pas à un {NOM_TYPE[t]}")
        if nom in ("flottant_petuar", "flottant_128"):
            if t == "x":
                return self.val(x)
            if t in vtx.PQ_DEPUIS:
                if t == "f":
                    x = ("appel", "flottant_64", [x], ligne)
                return self.appel(("appel", vtx.PQ_DEPUIS[t], [x], ligne))
            interdit()
        if nom == "comme_flottant_petuar":
            if t != "w":
                interdit()
            return self.val(x)
        if nom == "vers_ieee128":
            if t != "x":
                interdit()
            return self.appel(("appel", "__pq_vers_ieee", [self.bits_x(x)], ligne))
        if nom == "de_ieee128":
            if t != "w":
                interdit()
            return self.appel(("appel", "__pq_de_ieee", [x], ligne))
        if t == "x":
            if nom == "bits":
                return self.val(x)
            if nom == "racine":
                return self.appel(("appel", "__pq_racine", [self.bits_x(x)], ligne))
            if nom == "flottant_64":
                return self.appel(("appel", "__pq_vers_d", [self.bits_x(x)], ligne))
            if nom == "flottant":
                return self.appel(("appel", "__pq_vers_f", [self.bits_x(x)], ligne))
            if nom in ("entier_128", "long", "entier"):
                w = self.appel(("appel", "__pq_vers_w", [self.bits_x(x)], ligne))
                return {"entier_128": w, "long": f"({w} as u64)", "entier": f"({w} as u32)"}[nom]
            interdit()
        v = None
        if nom == "flottant":
            if t == "l":
                interdit()
            if t == "d":
                return f"fb({self.valfl(x, 'd')} as f32)"
            v = self.val(x)
            return {"e": f"fb({v} as f32)"}.get(t, v)
        if nom == "flottant_signe":
            if t != "e":
                interdit()
            return f"fb({self.val(x)} as i32 as f32)"
        if nom == "entier":
            if t in ("f", "d"):
                return f"({self.valfl(x, t)} as i32 as u32)"
            v = self.val(x)
            return f"({v} as u32)" if t in LARGES2 else v
        if nom == "arrondi":
            if t not in ("f", "d"):
                interdit()
            return f"({self.valfl(x, t)}.round_ties_even() as i32 as u32)"
        if nom == "arrondi_long":
            if t != "d":
                interdit()
            return f"({self.valfl(x, 'd')}.round_ties_even() as i64 as u64)"
        if nom == "racine":
            if t == "d":
                return f"db({self.valfl(x, 'd')}.sqrt())"
            return f"fb({self.valfl(x, 'f')}.sqrt())"
        if nom in ("comme_flottant", "bits"):
            if t == "l" or (t == "d" and nom == "comme_flottant"):
                interdit()
            return self.val(x)
        if nom == "entier_128":
            if t not in ("e", "l", "w", "d"):
                interdit()
            if t == "d":
                return self.appel(("appel", "__dtoq", [x], ligne))
            v = self.val(x)
            return {"e": f"({v} as u128)", "l": f"({v} as i64 as i128 as u128)"}.get(t, v)
        if nom == "entier_128_signe":
            if t != "e":
                interdit()
            return f"({self.val(x)} as i32 as i128 as u128)"
        if nom == "entier_128_de":
            if t != "l" or self.typ(args[1]) != "l":
                raise VtxError(f"ligne {ligne} : entier_128_de(haut, bas) prend deux longs")
            return self.bloc([(self.val(args[0], "l"), "l"), (self.val(args[1], "l"), "l")],
                             lambda m: f"(({m[0]} as u128) << 64) | ({m[1]} as u128)")
        if nom == "flottant_64" and t == "w":
            return self.appel(("appel", "__qtod", [x], ligne))
        if nom == "flottant_64":
            if t not in ("e", "f", "d", "l"):
                interdit()
            if t == "f":
                return f"db({self.valfl(x, 'f')} as f64)"
            v = self.val(x)
            return {"e": f"db({v} as f64)", "l": f"db({v} as i64 as f64)"}.get(t, v)
        if nom == "flottant_64_signe":
            if t != "e":
                interdit()
            return f"db({self.val(x)} as i32 as f64)"
        if nom == "flottant_64_de":
            if t != "e" or self.typ(args[1]) != "e":
                raise VtxError(f"ligne {ligne} : flottant_64_de(haut, bas) prend deux entiers")
            return self.bloc([(self.val(args[0], "e"), "e"), (self.val(args[1], "e"), "e")],
                             lambda m: f"(({m[0]} as u64) << 32) | ({m[1]} as u64)")
        if nom == "comme_flottant_64":
            if t != "l":
                interdit()
            return self.val(x)
        if nom == "long":
            if t == "f":
                interdit()
            if t == "d":
                return f"({self.valfl(x, 'd')} as i64 as u64)"
            if t == "w":
                return f"({self.val(x)} as u64)"
            return self.val(x, "l")
        if nom == "long_signe":
            if t != "e":
                interdit()
            return f"({self.val(x)} as i32 as i64 as u64)"
        if nom == "long_de":
            if t != "e" or self.typ(args[1]) != "e":
                raise VtxError(f"ligne {ligne} : long_de(haut, bas) prend deux entiers")
            return self.bloc([(self.val(args[0], "e"), "e"), (self.val(args[1], "e"), "e")],
                             lambda m: f"(({m[0]} as u64) << 32) | ({m[1]} as u64)")
        if nom in ("bas", "haut") and t == "w":
            v = self.val(x)
            return f"({v} as u64)" if nom == "bas" else f"(({v} >> 64) as u64)"
        if nom in ("bas", "haut"):
            if t not in LARGES2:
                interdit()
            v = self.val(x)
            return f"({v} as u32)" if nom == "bas" else f"(({v} >> 32) as u32)"
        raise VtxError(f"ligne {ligne} : « {nom} » : conversion inconnue de la forge")

    def surcharge_rs(self, nom, args, t, ligne):
        if nom == "abs":
            if len(args) != 1:
                raise VtxError(f"ligne {ligne} : « abs » attend 1 argument")
            v = self.val(args[0], t)
            if t == "f":
                return f"({v} & 0x7FFF_FFFF)"
            if t == "d":
                return f"({v} & 0x7FFF_FFFF_FFFF_FFFF)"
            return self.bloc([(v, "l")], lambda m: f"if ({m[0]} as i64) < 0 {{ {m[0]}.wrapping_neg() }} else {{ {m[0]} }}")
        if len(args) != 2:
            raise VtxError(f"ligne {ligne} : « {nom} » attend 2 arguments")
        parts = [(self.val(args[0], t), t), (self.val(args[1], t), t)]
        if t == "f":
            moins = (lambda a, b: f"f({a}) < f({b})")
        elif t == "d":
            moins = (lambda a, b: f"dd({a}) < dd({b})")
        else:
            moins = (lambda a, b: f"({a} as i64) < ({b} as i64)")
        if nom == "min":
            return self.bloc(parts, lambda m: f"if {moins(m[1], m[0])} {{ {m[1]} }} else {{ {m[0]} }}")
        return self.bloc(parts, lambda m: f"if {moins(m[0], m[1])} {{ {m[1]} }} else {{ {m[0]} }}")

    # ------------------------------------------------------------ le programme
    def forger(self):
        fonctions = list(self.fonctions.values())
        # premier passage : qui appelle qui ; qui lit la pile (le ramasse-miettes)
        self.ramasse = None
        for f in fonctions:
            self.fonction_rs(f)
        ramasse = {n for n, a in self.graphe.items() if "<pile>" in a}
        change = True
        while change:
            change = False
            for n, a in self.graphe.items():
                if n not in ramasse and a & ramasse:
                    ramasse.add(n)
                    change = True
        self.ramasse = ramasse
        return [self.fonction_rs(f) for f in fonctions]


ATTRIBUTS = ("#![allow(unused_mut, unused_variables, unused_assignments, unreachable_code, unused_parens, dead_code, "
             "clippy::all, non_snake_case, unused_imports, unused_labels)]")
MODULES = ["miroir", "memoire", "gif", "hote", "sortie"]     # recopiés de vtx-rs/src


def noyau():
    """Le noyau des programmes forgés : noyau_forge.rs, avec les fichiers de la machine qu'il reprend."""
    src = os.path.join(racine, "vtx-rs", "src")
    mods = []
    for m in MODULES:
        texte = open(os.path.join(src, m + ".rs"), encoding="utf-8").read()
        mods.append(f"#[allow(dead_code, unused_imports, unused_variables)]\nmod {m} {{\n{texte}\n}}\n")
    n = open(os.path.join(ici, "noyau_forge.rs"), encoding="utf-8").read()
    return ATTRIBUTS + "\n" + n.replace("// @MODULES@", "\n".join(mods), 1)


def source_rust(src, dossier=None, nom="programme"):
    """Le programme Rust complet d'un programme vtx."""
    g, mots, etiquettes = compiler_arbre(src, dossier)
    fo = Forge(g, etiquettes)
    fonctions = fo.forger()
    s = [noyau()]
    s.append(f"const NOM: &str = {nom!r};".replace("'", '"'))
    s.append(f"static MOTS: [u32; {len(mots)}] = [" + ",".join(str(w) for w in mots) + "];\n")
    s += fonctions
    s.append("\nfn main() {\n    lancer_programme(f_principal);\n}\n")
    return "\n".join(s), mots


def rustc_options(natif=False):
    o = ["--edition", "2021", "-C", "opt-level=3", "-C", "panic=abort", "-C", "codegen-units=1"]
    if natif:
        o += ["-C", "target-cpu=native"]
    return o


def forger_fichier(chemin, sortie=None, rs=None, natif=False):
    src = open(chemin, encoding="utf-8").read()
    code, _ = source_rust(src, os.path.dirname(os.path.abspath(chemin)), os.path.splitext(os.path.basename(chemin))[0])
    ext = ".exe" if os.name == "nt" else ""
    sortie = sortie or os.path.splitext(chemin)[0] + ext
    garder = rs is not None
    rs = rs or os.path.join(tempfile.mkdtemp(prefix="forge-"), "programme.rs")
    with open(rs, "w", encoding="utf-8") as f:
        f.write(code)
    rustc = shutil.which("rustc")
    if not rustc:
        raise VtxError("rustc introuvable : la forge passe par le compilateur Rust (rustup.rs)")
    r = subprocess.run([rustc] + rustc_options(natif) + ["-o", sortie, rs], capture_output=True, text=True)
    if r.returncode:
        raise VtxError("rustc a refusé le programme forgé :\n" + r.stderr[-3000:])
    if not garder:
        shutil.rmtree(os.path.dirname(rs), ignore_errors=True)
    return sortie


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
