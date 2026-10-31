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
from vtx128 import VtxError, est_ref, ligne_de, INTEGRES, OPS_LOGIQUES, SURCHARGES, NOM_TYPE, CHAMPS  # noqa: E402

MARQUE = "/*R*/"          # dans le code d'une expression : un appel qui peut ramasser les miettes
SIMPLE = re.compile(r"^(v_\w+|t\d+|\d+u128)$")
M64 = (1 << 64) - 1
M32 = (1 << 32) - 1
# les formats des flottants (qflot128.rs) et leur masque
FMT = {"f": "Q64", "s": "Q32", "x": "Q128"}
OP_RS = {"==": "==", "!=": "!=", "<": "<", "<=": "<=", ">": ">", ">=": ">="}


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
        for s in f.corps:
            self.instr(s)
        corps = self.lignes
        self.graphe[f.nom] = self.appelees
        nom = ident(f.nom)
        sig = ", ".join(f"mut v_{ident(p)}: u128" for p in params)
        sig = "c: &mut Ctx" + (", " + sig if sig else "")
        out = []
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
    def instr(self, s):
        g = s[0]
        if g == "soit":
            t = self.vtypes[s[1]]
            if est_ref(t) and len(s) > 4 and s[4] == t and s[2][0] in ("var", "appel") and self.typ(s[2]) == "e":
                code = self.val(s[2])
            else:
                code = self.val(s[2], t)
            self.ligne(f"v_{ident(s[1])} = {code};")
        elif g == "affecter":
            self.variable(s[1], s[3])
            self.ligne(f"v_{ident(s[1])} = {self.val(s[2], self.vtypes[s[1]])};")
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
            else:
                for x in s[1]:
                    self.instr(x)
        elif g == "segments":
            pre, _ = V.deplier_segments(s)
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
    EFFETS = {"sortie", "afficher", "entrée", "lire_car", "ecrire_car", "__service", "ouvrir_lecture", "ouvrir_ecriture",
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
        if t == "w":
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
        if signe:
            return self.b([pa, pb], "({0} as u64 as i64) " + OP_RS[o] + " ({1} as u64 as i64)")
        return self.b([pa, pb], "({0} as u64) " + OP_RS[o] + " ({1} as u64)")

    # ------------------------------------------------------------ expressions
    def conv_rs(self, code, t, voulu, ligne):
        if t == voulu or (voulu == "e" and t == "i") or (voulu == "w" and t in V.ENTIERS):
            return code
        if voulu == "f" and t in V.ENTIERS:
            return f"Q64.de_entier(({code}) & M64, 64, false)"
        if voulu == "f" and t == "s":
            return f"Q32.vers(&Q64, ({code}) & M32)"
        if voulu == "s" and t in V.ENTIERS:
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
        if nom == "entrée":
            return "c.m.entree.pop_front().unwrap_or(0)"
        if nom == "cmp3":
            return self.b([e1()], "((!({0} as u64)) as u128)")
        if nom == "lire_car":
            return self.b([e1()], "(c.m.lire_canal({0}) & M64)")
        if nom == "ecrire_car":
            return self.b([self.val(a[1], "e"), e1()], "{{ c.m.ecrire_canal({1}, {0}); 0u128 }}")
        if nom in ("ouvrir_lecture", "ouvrir_ecriture", "fermer", "fin_de"):
            code = {"ouvrir_lecture": 1, "ouvrir_ecriture": 2, "fermer": 3, "fin_de": 4}[nom]
            return self.b([e1()], "c.sys(" + str(code) + ", {0})")
        if nom == "bruit":
            return "c.sys(5, 0)"
        if nom == "pile":
            self.appelees.add("<pile>")
            return "c.sp"
        if nom == "__service":
            return self.b([e1(), self.val(a[1], "e")], "c.sys({0}, {1})")
        if nom == "nb_bits":
            return self.b([e1()], "(({0} as u64).count_ones() as u128)")
        if nom == "qegal":
            return self.b([e1(), self.val(a[1], "e")], "qegal_64({0}, {1})")
        if nom in ("min4", "max4", "addm4"):
            return self.b([e1(), self.val(a[1], "e")], "quits_64({0}, {1}, " + str({"min4": 0, "max4": 1, "addm4": 2}[nom]) + ")")
        if nom == "gdot":
            return self.b([e1(), self.val(a[1], "e")], "gdot_64({0}, {1})")
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
            return {"x": v(), "e": f"Q128.de_entier({v()}, 64, false)", "i": f"Q128.de_entier({v()}, 32, false)",
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
            return f"Q128.de_entier({v()}, {64 if t == 'e' else 32}, true)"
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
                    "entier": f"Q128.vers_entier({c}, false, 64)", "arrondi": f"Q128.vers_entier({c}, true, 64)",
                    "entier_32": f"(Q128.vers_entier({c}, false, 128) & M32)"}.get(nom) or interdit()
        if nom in ("flottant", "flottant_64"):
            if t == "w":
                return f"Q128.vers(&Q64, Q128.de_entier({v()}, 128, true))"
            if t not in ("e", "i", "f", "s"):
                interdit()
            return {"e": f"Q64.de_entier({v()} & M64, 64, false)", "i": f"Q64.de_entier({v()} & M64, 64, false)",
                    "s": f"Q32.vers(&Q64, {v()} & M32)", "f": v()}[t]
        if nom == "flottant_32":
            if t not in ("e", "i", "f", "s"):
                interdit()
            return {"e": f"Q64.vers(&Q32, Q64.de_entier({v()} & M64, 64, false))",
                    "i": f"Q64.vers(&Q32, Q64.de_entier({v()} & M64, 64, false))",
                    "f": f"Q64.vers(&Q32, {v()} & M64)", "s": v()}[t]
        if nom == "flottant_signe":
            if t not in V.ENTIERS:
                interdit()
            if t == "i":
                return f"Q64.de_entier(sext32({v()}), 64, true)"
            return f"Q64.de_entier({v()} & M64, 64, true)"
        if nom in ("entier", "entier_32"):
            c = v()
            if t == "w":
                c = f"({c} & M64)"
            elif t == "s":
                c = f"Q64.vers_entier(Q32.vers(&Q64, {c} & M32), false, 64)"
            elif t == "f":
                c = f"Q64.vers_entier({c} & M64, false, 64)"
            return f"({c} & M32)" if nom == "entier_32" else c
        if nom == "arrondi":
            if t == "s":
                return f"Q64.vers_entier(Q32.vers(&Q64, {v()} & M32), true, 64)"
            if t == "f":
                return f"Q64.vers_entier({v()} & M64, true, 64)"
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
        elif all(isinstance(v, int) and v < 1 << 64 or v in TYPES_64 for v in vus):
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
MODULES = ["qflot128", "spu128", "hote", "miroir"]     # recopiés de vtx-rs/src


def noyau():
    src = os.path.join(racine, "vtx-rs", "src")
    mods = []
    for m in MODULES:
        texte = open(os.path.join(src, m + ".rs"), encoding="utf-8").read()
        mods.append(f"#[allow(dead_code, unused_imports, unused_variables)]\nmod {m} {{\n{texte}\n}}\n")
    n = open(os.path.join(ici, "noyau_forge128.rs"), encoding="utf-8").read()
    return ATTRIBUTS + "\n" + n.replace("// @MODULES@", "\n".join(mods), 1)


def programme_rust(src, dossier=None, nom="programme"):
    """Le programme forgé (sans le noyau) : ses mots, ses fonctions, et lancer() qui le joue avec des entrées."""
    g, mots, etiquettes = compiler_arbre(src, dossier)
    fo = Forge(g, etiquettes)
    fonctions = fo.forger()
    s = [f"const NOM: &str = {nom!r};".replace("'", '"'),
         f"const FIN_CODE: u128 = {etiquettes['FIN_CODE']};",
         f"static MOTS: [u128; {len(mots)}] = [" + ",".join(str(w) for w in mots) + "];\n"]
    s += [x.replace(MARQUE, "") for x in fonctions]
    s.append(code_zones(fo.plan or {}))
    # la machine d'un fil (les vagues sur plusieurs cœurs) : sa mémoire à elle, le programme chargé (textes et constantes)
    s.append("#[allow(dead_code)]\nfn ctx_fils() -> Ctx {\n    let mut m = Spu128::nouveau();\n    m.charger(&MOTS);\n"
             "    Ctx { m, sp: spu128::PILE, cl: [u128::MAX; 16], pl: [std::ptr::null_mut(); 16], ce: [u128::MAX; 16],\n"
             "          pe: [std::ptr::null_mut(); 16], vider: |_c| {} }\n}")
    s.append("pub fn lancer(entrees: &[String]) {\n    lancer_programme(f_principal, debuter_zones, vider_zones, &MOTS, FIN_CODE, "
             "NOM, entrees);\n}\n")
    return "\n".join(s), mots


def source_rust(src, dossier=None, nom="programme"):
    """Le programme Rust complet d'un programme vtx."""
    prog, mots = programme_rust(src, dossier, nom)
    main = "\nfn main() {\n    let a: Vec<String> = std::env::args().collect();\n    lancer(&a[1..]);\n}\n"
    return noyau() + "\n" + prog + main, mots


def rustc_options(natif=False):
    o = ["--edition", "2021", "-C", "opt-level=3", "-C", "panic=abort", "-C", "codegen-units=1"]
    if natif:
        o += ["-C", "target-cpu=native"]
    return o


def forger_fichier(chemin, sortie=None, rs=None, natif=False):
    src = open(chemin, encoding="utf-8").read()
    code, _ = source_rust(src, os.path.dirname(os.path.abspath(chemin)), os.path.splitext(os.path.basename(chemin))[0])
    ext = ".exe" if os.name == "nt" else ""
    sortie = sortie or os.path.splitext(chemin)[0] + ".lugus" + ext
    garder = rs is not None
    rs = rs or os.path.join(tempfile.mkdtemp(prefix="forge128-"), "programme.rs")
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
