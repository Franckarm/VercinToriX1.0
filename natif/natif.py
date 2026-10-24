#!/usr/bin/env python3
"""Traduction directe d'un programme du SPU en code machine x86-64 : un exécutable autonome, sans Rust, sans LLVM.

Chaque instruction du SPU devient quelques instructions x86-64 (assembleur maison : natif/x86.py, vérifié contre
GNU as). Ce traducteur en Python est la référence : le traducteur écrit en Vercintorix devra produire exactement les
mêmes octets.

Machine traduite :
  - mémoire du SPU : 4 étages de 16 M mots, réservés d'un coup (256 Mo de mémoire virtuelle, remplie à la demande) ;
    r15 en est la base, le mot (e, a) est en [r15 + a*4 + e*64 Mo] ;
  - registres du SPU : R1-R4 et R9-R14 dans des registres de la machine, R5-R8 et R15 en mémoire ([rbp + 4r]) ;
  - drapeaux z et c : ceux de la machine tant que c'est possible ; une analyse de vie des drapeaux ne les range en
    mémoire que lorsqu'ils serviront plus loin et qu'une instruction les écraserait ;
  - sauts : directs ; CALL empile l'adresse de retour du SPU sur la pile du SPU (comme la machine) ; RET la relit et
    saute par une table (une entrée par mot du programme) ;
  - entrées : les nombres de la ligne de commande ; sorties et texte écrits à la fin, comme « vtx PROG.vtx ».

Utilisation :
  python3 natif/natif.py PROG.vtx [SORTIE]         compile (vtx.py) puis traduit : un exécutable Linux (ELF)
  python3 natif/natif.py --mots PROG.mots [SORTIE]  traduit des mots déjà compilés (séparés par des virgules)
"""
import os
import struct
import sys

ici = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ici)
from x86 import *  # noqa

ADR = 0xFFFFFF
MASQUE = 0xFFFFFFFF
BASE = 0x400000
ENTETE = 64 + 56          # en-tête ELF et un en-tête de programme
PILE_HAUT = 0x7FFFFF

from socle import Socle, CARTE, Z, C, F2_31, TAILLE_ETAT  # noqa

# drapeaux : écrits par ces instructions (z et c)
ECRIT_DRAPEAUX = {0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0C, 0x0D, 0x0E, 0x10, 0x11, 0x12, 0x13,
                  0x14, 0x15, 0x16, 0x20, 0x29, 0x38, 0x4C, 0x4D, 0x4E, 0x4F, 0x50, 0x51, 0x53, 0x54, 0x56, 0x57, 0x58,
                  0x59, 0x5A} | set(range(0x40, 0x4C))
LIT_DRAPEAUX = {0x31, 0x32, 0x35, 0x36, 0x4C, 0x4D}
CONNUS = {0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x10, 0x11, 0x12, 0x13,
          0x14, 0x15, 0x16, 0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x29, 0x2A, 0x30, 0x31, 0x32, 0x33,
          0x34, 0x35, 0x36, 0x38, 0x39, 0x3F} | set(range(0x40, 0x5B))
# instructions dont la traduction n'écrase pas les drapeaux de la machine (et qui ne les écrivent pas)
SANS_EFFET = {0x00, 0x0B}


def cible(w):
    return ((w & 15) << 16) | (((w >> 16) & 255) << 8) | ((w >> 8) & 255)


def analyser(mots):
    """Instructions atteintes, cibles de sauts, points de retour, successeurs."""
    n = len(mots)
    mot = lambda p: mots[p] if p < n else 0
    vues, cibles, retours = set(), {0}, set()
    pile = [0]
    while pile:
        pc = pile.pop()
        if pc in vues:
            continue
        vues.add(pc)
        if pc >= n:
            continue                       # hors du programme : erreur à l'exécution
        w = mot(pc)
        op = w >> 24
        suiv = (pc + 1) & ADR
        if op == 0x0A:
            pile.append((pc + 2) & ADR)
        elif op == 0x30:
            cibles.add(cible(w))
            pile.append(cible(w))
        elif op in (0x31, 0x32, 0x35, 0x36):
            cibles.add(cible(w))
            pile += [cible(w), suiv]
        elif op == 0x33:
            cibles.add(cible(w))
            retours.add(suiv)
            pile += [cible(w), suiv]
        elif op in (0x34, 0x3F, 0x22) or op not in CONNUS:
            pass
        else:
            pile.append(suiv)
    return vues, cibles, retours


def successeurs(mots, pc, retours):
    if pc >= len(mots):
        return []
    w = mots[pc]
    op = w >> 24
    suiv = (pc + 1) & ADR
    if op == 0x0A:
        return [(pc + 2) & ADR]
    if op == 0x30:
        return [cible(w)]
    if op in (0x31, 0x32, 0x35, 0x36):
        return [cible(w), suiv]
    if op == 0x33:
        return [cible(w)]
    if op == 0x34:
        return list(retours)
    if op in (0x3F, 0x22) or op not in CONNUS:
        return []
    return [suiv]


def vie_drapeaux(mots, vues, retours):
    """vivant[pc] : les drapeaux à l'entrée de pc serviront avant d'être réécrits."""
    preds = {pc: [] for pc in vues}
    succ = {}
    for pc in vues:
        succ[pc] = [s for s in successeurs(mots, pc, retours) if s in vues]
        for s in succ[pc]:
            preds[s].append(pc)
    vivant = {pc: False for pc in vues}
    travail = list(vues)
    while travail:
        pc = travail.pop()
        op = mots[pc] >> 24 if pc < len(mots) else 0
        sortie = any(vivant[s] for s in succ[pc])
        v = op in LIT_DRAPEAUX or (sortie and op not in ECRIT_DRAPEAUX)
        if v != vivant[pc]:
            vivant[pc] = v
            travail += preds[pc]
    return vivant, succ


class Traducteur:
    def __init__(self, mots, corpus=False, texte=True):
        self.mots = list(mots)
        self.corpus = corpus
        self.a = Asm(BASE + ENTETE)
        self.a.avec_texte = texte
        self.locales = 0

    # --- registres du SPU
    def op(self, r):
        """Opérande source pour le registre r du SPU (None pour R0)."""
        if r == 0:
            return None
        return R32[CARTE[r]] if r in CARTE else dword(RBP, depl=4 * r)

    def charger(self, dst, r):
        a = self.a
        if r == 0:
            a.mov(dst, 0)
        elif r in CARTE:
            if CARTE[r] != dst.n:
                a.mov(dst, R32[CARTE[r]])
        else:
            a.mov(dst, dword(RBP, depl=4 * r))

    def source(self, r):
        """Opérande pour une opération à deux opérandes : registre, mémoire ou 0 immédiat."""
        return 0 if r == 0 else self.op(r)

    def ranger(self, r, src):
        if r == 0:
            return
        self.a.mov(R32[CARTE[r]] if r in CARTE else dword(RBP, depl=4 * r), src)

    def locale(self):
        self.locales += 1
        return f"L{self.locales}"

    def traduire(self):
        mots = self.mots
        n = len(mots)
        a = self.a
        vues, cibles, retours = analyser(mots)
        vivant, succ = vie_drapeaux(mots, vues, retours)
        ordre = sorted(vues)
        suivante = {p: (ordre[i + 1] if i + 1 < len(ordre) else None) for i, p in enumerate(ordre)}
        # les points de jonction : on y arrive avec les drapeaux en mémoire
        jonctions = set(cibles) | set(retours) | {0}
        for pc in ordre:
            if pc < n:
                op = mots[pc] >> 24
                if op not in (0x30, 0x33, 0x34, 0x3F, 0x22) and op in CONNUS:
                    s = (pc + 2) & ADR if op == 0x0A else (pc + 1) & ADR
                    if suivante[pc] != s:
                        jonctions.add(s)

        Socle(a).construire(n, self.corpus)
        etat = "M"

        def vivant_a(p):
            return vivant.get(p, False)

        def garder():
            nonlocal etat
            if etat == "N":
                a.setcc("e", byte(RBP, depl=Z))
                a.setcc("b", byte(RBP, depl=C))
                etat = "B"

        def ecrase(pc):
            """La traduction de pc va écraser les drapeaux de la machine."""
            nonlocal etat
            if vivant_a(pc):
                garder()
            etat = "M"

        def sauter(cc, t):
            """Saut (cc None : toujours) vers l'adresse t du SPU."""
            if vivant_a(t):
                garder()
            if cc is None:
                a.jmp(f"P{t}")
            else:
                a.jcc(cc, f"P{t}")

        for pc in ordre:
            a.etiquette(f"P{pc}")
            if pc in jonctions:
                etat = "M"
            if self.corpus:
                a.paddq(XMM[15], XMM[14])
            if pc >= n:
                a.jmp("E_HORS")
                continue
            w = mots[pc]
            op, g, b, e = w >> 24, (w >> 16) & 255, (w >> 8) & 255, (w & 255) >> 6
            rd, rs, rt = g >> 4, g & 15, b >> 4
            decal = b - 256 if b > 127 else b
            suiv = (pc + 1) & ADR
            continue_seq = True

            if op == 0x00:
                pass
            elif op in (0x01, 0x02, 0x14, 0x15, 0x16):
                self.charger(EAX, rs)
                a.alu({1: "add", 2: "sub", 0x14: "and", 0x15: "or", 0x16: "xor"}[op], EAX, self.source(rt))
                self.ranger(rd, EAX)
                etat = "N"
            elif op in (0x06, 0x07):
                self.charger(EAX, rs)
                a.alu("add" if op == 0x06 else "sub", EAX, b)
                self.ranger(rd, EAX)
                etat = "N"
            elif op == 0x0E:
                self.charger(EAX, rs)
                a.alu("cmp", EAX, self.source(rt))
                etat = "N"
            elif op in (0x4C, 0x4D):
                self.charger(EAX, rs)
                src = self.source(rt)
                if etat == "M":
                    a.bt(dword(RBP, depl=C), 0)
                a.alu("adc" if op == 0x4C else "sbb", EAX, src)
                self.ranger(rd, EAX)
                etat = "N"
            elif op == 0x03:
                self.charger(EAX, rs)
                src = self.source(rt)
                if src == 0:
                    a.mov(EAX, 0)
                else:
                    a.imul(EAX, src)
                a.test(EAX, EAX)
                self.ranger(rd, EAX)
                etat = "N"
            elif op in (0x04, 0x05):
                self.charger(EAX, rs)
                a.decaler("shl" if op == 0x04 else "shr", EAX, 2)
                a.test(EAX, EAX)
                self.ranger(rd, EAX)
                etat = "N"
            elif op in (0x08, 0x09):
                self.charger(EAX, rs)
                self.charger(ECX, rt)
                a.decaler("shl" if op == 0x08 else "shr", EAX, "cl")
                a.test(EAX, EAX)
                self.ranger(rd, EAX)
                etat = "N"
            elif op == 0x0A:
                v = mots[pc + 1] if pc + 1 < n else 0
                a.mov(EAX, v)
                a.test(EAX, EAX)
                self.ranger(rd, EAX)
                etat = "N"
            elif op == 0x0B:
                if rd != rs:
                    if rd != 0:
                        if rs in CARTE or rd in CARTE or rs == 0:
                            dst = self.op(rd)
                            if rs == 0:
                                a.mov(dst, 0)
                            elif isinstance(dst, Reg):
                                a.mov(dst, self.op(rs))
                            else:
                                a.mov(dst, R32[CARTE[rs]])
                        else:
                            a.mov(EAX, self.op(rs))
                            self.ranger(rd, EAX)
            elif op in (0x0C, 0x0D):
                zero, fin = self.locale(), self.locale()
                self.charger(EAX, rs)
                self.charger(ECX, rt)
                a.test(ECX, ECX)
                a.jcc("e", zero)
                a.alu("xor", EDX, EDX)
                a.unaire("div", ECX)
                if op == 0x0D:
                    a.mov(EAX, EDX)
                a.jmp(fin)
                a.etiquette(zero)
                if op == 0x0C:
                    a.mov(EAX, MASQUE)
                a.etiquette(fin)
                a.test(EAX, EAX)
                self.ranger(rd, EAX)
                etat = "N"
            elif op in (0x10, 0x11):
                self.charger(EAX, rs)
                self.charger(ECX, rt)
                a.mov(EDX, 0 if op == 0x10 else 1)
                a.call("QUITS")
                a.test(EAX, EAX)
                self.ranger(rd, EAX)
                etat = "N"
            elif op == 0x13:
                # (x + y) & 3 quit par quit : bits bas additionnés sans débordement, puis bits hauts
                self.charger(EAX, rs)
                self.charger(ECX, rt)
                a.mov(EDX, EAX)
                a.alu("xor", EDX, ECX)
                a.alu("and", EDX, 0xAAAAAAAA)
                a.alu("and", EAX, 0x55555555)
                a.alu("and", ECX, 0x55555555)
                a.alu("add", EAX, ECX)
                a.alu("xor", EAX, EDX)
                self.ranger(rd, EAX)
                etat = "N"
            elif op == 0x12:
                self.charger(EAX, rs)
                a.unaire("not", EAX)
                a.test(EAX, EAX)
                self.ranger(rd, EAX)
                etat = "N"
            elif op == 0x20:
                self.charger(EAX, rs)
                a.alu("and", EAX, ADR)
                a.mov(EAX, dword(R15_, RAX, 4, e << 26))
                a.test(EAX, EAX)
                self.ranger(rd, EAX)
                etat = "N"
            elif op == 0x21:
                ecrase(pc)
                self.charger(EDX, rd)
                a.alu("and", EDX, ADR)
                self.charger(EAX, rs)
                a.mov(dword(R15_, RDX, 4, e << 26), EAX)
            elif op == 0x29:
                self.charger(EAX, rs)
                a.alu("and", EAX, ADR)
                self.charger(ECX, rt)
                a.alu("and", ECX, 3)
                a.decaler("shl", ECX, 24)
                a.alu("or", EAX, ECX)
                a.mov(EAX, dword(R15_, RAX, 4))
                a.test(EAX, EAX)
                self.ranger(rd, EAX)
                etat = "N"
            elif op == 0x2A:
                ecrase(pc)
                self.charger(EDX, rd)
                a.alu("and", EDX, ADR)
                self.charger(ECX, rt)
                a.alu("and", ECX, 3)
                a.decaler("shl", ECX, 24)
                a.alu("or", EDX, ECX)
                self.charger(EAX, rs)
                a.mov(dword(R15_, RDX, 4), EAX)
            elif op in (0x54, 0x55):
                if op == 0x55:
                    ecrase(pc)
                self.charger(EAX, rs)
                self.charger(ECX, rt)
                a.mov(EDX, ECX)
                a.decaler("shr", EDX, 4)
                a.alu("add", EAX, EDX)
                a.alu("and", EAX, ADR)
                a.alu("and", ECX, 15)
                a.alu("add", ECX, ECX)
                m = dword(R15_, RAX, 4, e << 26)
                if op == 0x54:
                    a.mov(EAX, m)
                    a.decaler("shr", EAX, "cl")
                    a.alu("and", EAX, 3)
                    self.ranger(rd, EAX)
                    etat = "N"
                else:
                    a.mov(EDX, 3)
                    a.decaler("shl", EDX, "cl")
                    a.unaire("not", EDX)
                    a.alu("and", m, EDX)
                    self.charger(EDX, rd)
                    a.alu("and", EDX, 3)
                    a.decaler("shl", EDX, "cl")
                    a.alu("or", m, EDX)
            elif op in (0x56, 0x57):
                self.charger(EAX, rs)
                self.charger(EDX, rs)
                src = self.source(rt)
                a.alu("and" if op == 0x56 else "or", EDX, src)
                a.alu("and", EDX, 0xAAAAAAAA)
                a.alu("or" if op == 0x56 else "and", EAX, src)
                a.alu("and", EAX, 0x55555555)
                a.alu("or", EAX, EDX)
                self.ranger(rd, EAX)
                etat = "N"
            elif op in (0x58, 0x59):
                self.charger(EAX, rs)
                a.mov(EDX, EAX)
                a.alu("and", EDX, 0xAAAAAAAA)
                a.decaler("shr", EDX, 1)
                a.alu("and", EAX, 0x55555555)
                a.alu("add", EAX, EAX)
                a.alu("or", EAX, EDX)
                if op == 0x59:
                    a.unaire("not", EAX)
                    a.test(EAX, EAX)
                self.ranger(rd, EAX)
                etat = "N"
            elif op == 0x5A:
                self.charger(EAX, rs)
                self.charger(ECX, rt)
                a.alu("and", ECX, 15)
                a.alu("add", ECX, ECX)
                a.decaler("shr", EAX, "cl")
                a.alu("and", EAX, 3)
                self.ranger(rd, EAX)
                etat = "N"
            elif op == 0x22:
                a.jmp("E_DMA")
                continue_seq = False
            elif op == 0x23:
                ecrase(pc)
                a.call("ENTREE")
                self.ranger(rd, EAX)
            elif op == 0x24:
                ecrase(pc)
                self.charger(EAX, rs)
                a.call("SORTIE")
            elif op in (0x25, 0x26):
                ecrase(pc)
                if 13 in CARTE:
                    a.lea(EDX, dword(R64[CARTE[13]], depl=decal))
                else:
                    a.mov(EDX, dword(RBP, depl=52))
                    a.alu("add", EDX, decal)
                a.alu("and", EDX, ADR)
                if op == 0x25:
                    a.mov(EAX, dword(R15_, RDX, 4))
                    self.ranger(rd, EAX)
                else:
                    self.charger(EAX, rd)
                    a.mov(dword(R15_, RDX, 4), EAX)
            elif op == 0x27:
                ecrase(pc)
                self.charger(EAX, rs)
                self.pile_moins()
                a.mov(dword(R15_, RDX, 4), EAX)
            elif op == 0x28:
                ecrase(pc)
                self.charger(EDX, 14)
                a.alu("and", EDX, ADR)
                a.mov(EAX, dword(R15_, RDX, 4))
                a.alu("add", EDX, 1)
                a.alu("and", EDX, ADR)
                self.ranger(14, EDX)
                self.ranger(rd, EAX)
            elif op in (0x30, 0x31, 0x32, 0x35, 0x36):
                t = cible(w)
                if op == 0x30:
                    sauter(None, t)
                    continue_seq = False
                else:
                    cc = {0x31: "e", 0x32: "ne", 0x35: "b", 0x36: "ae"}[op]
                    if etat == "M":
                        a.alu("cmp", byte(RBP, depl=Z if op in (0x31, 0x32) else C), 0)
                        cc = "ne" if op in (0x31, 0x35) else "e"
                    sauter(cc, t)
            elif op == 0x33:
                ecrase(pc)
                self.pile_moins()
                a.mov(dword(R15_, RDX, 4), suiv)
                sauter(None, cible(w))
                continue_seq = False
            elif op == 0x34:
                ecrase(pc)
                self.charger(EDX, 14)
                a.alu("and", EDX, ADR)
                a.mov(EAX, dword(R15_, RDX, 4))
                a.alu("add", EDX, 1)
                a.alu("and", EDX, ADR)
                self.ranger(14, EDX)
                a.alu("cmp", EAX, n)
                a.jcc("ae", "E_RETOUR")
                a.lea(RCX, qword(etiq="TABLE"))
                a.mov(EAX, dword(RCX, RAX, 4))
                a.jmp_r(RAX)
                continue_seq = False
            elif op == 0x38:
                self.charger(EAX, rs)
                self.charger(ECX, rt)
                a.call("GDOT")
                a.test(EAX, EAX)
                self.ranger(rd, EAX)
                etat = "N"
            elif op == 0x39:
                ecrase(pc)
                self.charger(EDX, 14)
                a.call("GEMV")
            elif op == 0x3F:
                a.jmp("FIN")
                continue_seq = False
            elif op in (0x40, 0x41, 0x42, 0x43):
                self.flottants(rs, rt)
                a.ss({0x40: "addss", 0x41: "subss", 0x42: "mulss", 0x43: "divss"}[op], XMM[0], XMM[1])
                self.nan_unique()
                self.ranger(rd, EAX)
                etat = "N"
            elif op in (0x44, 0x45, 0x46):
                self.flottants(rs, rt)
                if op == 0x44:
                    a.ucomiss(XMM[0], XMM[1])
                    a.setcc("e", AL)
                    a.setcc("np", CL)
                    a.alu("and", AL, CL)
                else:
                    a.ucomiss(XMM[1], XMM[0])
                    a.setcc("a" if op == 0x45 else "ae", AL)
                a.movzx8(EAX, AL)
                a.test(EAX, EAX)
                self.ranger(rd, EAX)
                etat = "N"
            elif op == 0x47:
                self.flottants(rs, 0)
                a.ss("sqrtss", XMM[0], XMM[0])
                self.nan_unique()
                self.ranger(rd, EAX)
                etat = "N"
            elif op in (0x48, 0x49):
                self.charger(EAX, rs)
                a.cvtsi2ss(XMM[0], RAX if op == 0x48 else EAX)
                a.movd(EAX, XMM[0])
                a.test(EAX, EAX)
                self.ranger(rd, EAX)
                etat = "N"
            elif op in (0x4A, 0x4B):
                nan, haut, bas, fin = (self.locale() for _ in range(4))
                self.charger(EAX, rs)
                a.movd(XMM[0], EAX)
                a.ucomiss(XMM[0], XMM[0])
                a.jcc("p", nan)
                a.ucomiss(XMM[0], dword(RBP, depl=F2_31))
                a.jcc("ae", haut)
                (a.cvttss2si if op == 0x4A else a.cvtss2si)(RAX, XMM[0])
                a.alu("cmp", RAX, -(1 << 31))
                a.jcc("l", bas)
                a.jmp(fin)
                a.etiquette(nan)
                a.alu("xor", EAX, EAX)
                a.jmp(fin)
                a.etiquette(haut)
                a.mov(EAX, 0x7FFFFFFF)
                a.jmp(fin)
                a.etiquette(bas)
                a.mov(EAX, 0x80000000)
                a.etiquette(fin)
                a.test(EAX, EAX)
                self.ranger(rd, EAX)
                etat = "N"
            elif op == 0x4E:
                self.charger(EAX, rs)
                src = self.source(rt)
                if src == 0 or isinstance(src, Reg) and src.n in (0, 2):
                    self.charger(ECX, rt)
                    src = ECX
                a.unaire("mul", src)
                a.mov(EAX, EDX)
                a.test(EAX, EAX)
                self.ranger(rd, EAX)
                etat = "N"
            elif op == 0x4F:
                self.charger(EAX, rs)
                a.alu("xor", EAX, self.source(rt))
                a.mov(EDX, EAX)
                a.decaler("shr", EDX, 1)
                a.alu("or", EAX, EDX)
                a.unaire("not", EAX)
                a.alu("and", EAX, 0x55555555)
                self.ranger(rd, EAX)
                etat = "N"
            elif op == 0x50:
                self.charger(EAX, rs)
                a.popcnt(EAX, EAX)
                a.test(EAX, EAX)
                self.ranger(rd, EAX)
                etat = "N"
            elif op in (0x51, 0x52, 0x53):
                if op == 0x52:
                    ecrase(pc)
                self.charger(EAX, rs)
                self.charger(ECX, rt)
                a.call({0x51: "ENTC", 0x52: "SORC", 0x53: "SYS"}[op])
                if op != 0x52:
                    a.test(EAX, EAX)
                    self.ranger(rd, EAX)
                    etat = "N"
            else:
                a.mov(EAX, pc)
                a.mov(ECX, op)
                a.jmp("E_INCONNU")
                continue_seq = False

            if continue_seq:
                s = (pc + 2) & ADR if op == 0x0A else suiv
                if suivante[pc] == s:
                    if s in jonctions and vivant_a(s):
                        garder()
                else:
                    sauter(None, s)

        # table des retours : une adresse par mot du programme
        a.aligner(4)
        a.etiquette("TABLE")
        for p in range(n):
            a.adresse32(f"P{p}" if p in vues else "E_RETOUR")
        a.etiquette("PROGRAMME")
        a.mots32(mots)
        a.aligner(64)
        a.etiquette("ETAT")

    def pile_moins(self):
        """R14 = (R14 - 1) & ADR ; edx = R14."""
        a = self.a
        if 14 in CARTE:
            r = R32[CARTE[14]]
            a.alu("sub", r, 1)
            a.alu("and", r, ADR)
            a.mov(EDX, r)
        else:
            a.mov(EDX, dword(RBP, depl=56))
            a.alu("sub", EDX, 1)
            a.alu("and", EDX, ADR)
            a.mov(dword(RBP, depl=56), EDX)

    def flottants(self, rs, rt):
        a = self.a
        for x, r in ((XMM[0], rs), (XMM[1], rt)):
            if r == 0:
                a.mov(EAX, 0)
                a.movd(x, EAX)
            else:
                a.movd(x, self.op(r))

    def nan_unique(self):
        """eax = xmm0, NaN rendu 0x7FC00000 ; drapeaux du résultat."""
        a = self.a
        ok = self.locale()
        a.movd(EAX, XMM[0])
        a.ucomiss(XMM[0], XMM[0])
        a.jcc("np", ok)
        a.mov(EAX, 0x7FC00000)
        a.etiquette(ok)
        a.test(EAX, EAX)

    def elf(self):
        code = self.a.resoudre()
        taille = ENTETE + len(code)
        memoire = taille + TAILLE_ETAT + 64
        entree = self.a.adresse("DEMARRER")
        eh = struct.pack("<16sHHIQQQIHHHHHH", b"\x7fELF\x02\x01\x01" + b"\0" * 9, 2, 0x3E, 1, entree, 64, 0, 0, 64, 56, 1,
                         64, 0, 0)
        ph = struct.pack("<IIQQQQQQ", 1, 7, 0, BASE, BASE, taille, memoire, 0x1000)
        return eh + ph + code


def traduire(mots, corpus=False, texte=False):
    t = Traducteur(mots, corpus, texte)
    t.traduire()
    return t


def ecrire_executable(chemin, mots, corpus=False):
    t = traduire(mots, corpus)
    with open(chemin, "wb") as f:
        f.write(t.elf())
    os.chmod(chemin, 0o755)
    return t


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(2)
    if args[0] == "--mots":
        mots = [int(x) for x in open(args[1]).read().replace(";", ",").split(",")[0:] if x.strip()]
        sortie = args[2] if len(args) > 2 else os.path.splitext(args[1])[0]
    else:
        sys.path.insert(0, os.path.dirname(ici))
        import vtx
        src = open(args[0], encoding="utf-8").read()
        mots = vtx.assembler(vtx.compiler(src, dossier=os.path.dirname(os.path.abspath(args[0]))))
        sortie = args[1] if len(args) > 1 else os.path.splitext(args[0])[0]
    t = ecrire_executable(sortie, mots)
    print(f"{sortie} : {len(mots)} mots du SPU -> {len(t.a.code)} octets x86-64")
