#!/usr/bin/env python3
"""Vérifie l'assembleur x86-64 de natif/x86.py contre GNU as : mêmes octets pour chaque forme d'instruction.
Il faut GNU as et objcopy (binutils). Utilisation : python3 natif/test_x86.py [fichier.s produit par natif.py]"""
import os, shutil, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from x86 import *


def comparer(asm, nom="essai"):
    if not (shutil.which("as") and shutil.which("objcopy")):
        print("GNU as absent : vérification de l'encodage sautée")
        return True
    code = asm.resoudre()
    d = tempfile.mkdtemp(prefix="x86-")
    s = os.path.join(d, "a.s")
    with open(s, "w") as f:
        f.write(".intel_syntax noprefix\n.text\nDEBUT:\n" + "\n".join(asm.texte) + "\n")
    subprocess.run(["as", "-o", os.path.join(d, "a.o"), s], check=True)
    subprocess.run(["objcopy", "-O", "binary", "-j", ".text", os.path.join(d, "a.o"), os.path.join(d, "a.bin")], check=True)
    gnu = open(os.path.join(d, "a.bin"), "rb").read()
    if gnu == code:
        shutil.rmtree(d)
        return True
    for i, (x, y) in enumerate(zip(code, gnu)):
        if x != y:
            break
    else:
        i = min(len(code), len(gnu))
    # retrouver l'instruction fautive
    a2 = Asm(asm.base)
    print(f"{nom} : écart à l'octet {i} (nous {len(code)} octets, GNU {len(gnu)}) ; fichiers dans {d}")
    print("nous :", code[max(0, i - 8):i + 8].hex(" "))
    print("GNU  :", gnu[max(0, i - 8):i + 8].hex(" "))
    return False


def batterie():
    a = Asm(0x400000)
    regs = [R32[i] for i in (0, 1, 2, 3, 5, 6, 7, 8, 11, 12, 13, 14, 15)]
    mems = [dword(RBP, depl=8), dword(RBP, depl=0), dword(RBP, depl=400), dword(R13_), dword(R12_, depl=-4),
            dword(R15_, RAX, 4, 1 << 26), dword(R15_, R14_, 4), dword(RSP, depl=16), dword(R15_, RDX, 4, 3 << 26),
            dword(RCX, RDX, 4), dword(RBP, RDX, 1, 4096)]
    for nom in ALU:
        for r in regs:
            a.alu(nom, r, R32[1])
            a.alu(nom, R32[9], r)
            for v in (1, -1, 127, 128, 0xFFFFFF, 0x7FC00000, 0xAAAAAAAA):
                a.alu(nom, r, v)
        for m in mems:
            a.alu(nom, EAX, m)
            a.alu(nom, m, R32[10])
            a.alu(nom, m, 5)
        a.alu(nom, RAX, 1 << 30)
        a.alu(nom, RDX, RCX)
        a.alu(nom, R64[9], qword(RBP, depl=72))
    a.alu("cmp", byte(RBP, depl=64), 0)
    a.alu("cmp", AL, 47)
    a.alu("cmp", CL, 47)
    a.alu("cmp", AL, byte(RDI))
    a.alu("and", AL, CL)
    a.test(AL, AL)
    for r in regs:
        for s in regs:
            a.mov(r, s)
        a.mov(r, 0)
        a.mov(r, 0xFFFFFFFF)
        for m in mems:
            a.mov(r, m)
            a.mov(m, r)
    for m in mems:
        a.mov(m, 12345)
    a.mov(qword(RBP, depl=72), RAX)
    a.mov(RAX, qword(RBP, depl=72))
    a.mov(R64[12], R64[3])
    a.mov(RAX, 5)
    a.mov(byte(RBP, RDX, 1, 4096), AL)
    a.mov(AL, byte(RSI))
    a.mov(byte(RBP, depl=9), 7)
    a.mov(AL, 10)
    for r in regs:
        a.lea(r, dword(R13_, depl=-3))
        a.test(r, r)
        a.imul(r, R32[3])
        a.imul(r, dword(RBP, depl=20))
        a.popcnt(r, R32[8])
        for n in ("shl", "shr", "sar"):
            a.decaler(n, r, "cl")
            a.decaler(n, r, 1)
            a.decaler(n, r, 4)
        for n in UNAIRE:
            a.unaire(n, r)
    a.lea(RCX, qword(etiq="T1"))
    a.lea(RSI, qword(RAX, depl=1 << 30))
    a.lea(RDX, qword(RBP, RDX, 1, 4096))
    a.test(EAX, 1)
    a.test(ECX, 0x80000000)
    a.decaler("shr", RAX, 4)
    a.unaire("div", RCX)
    a.unaire("mul", dword(RBP, depl=20))
    for cc in CC:
        a.setcc(cc, byte(RBP, depl=64))
        a.setcc(cc, AL)
        a.jcc(cc, "T1")
        a.cmovcc(cc, EAX, ECX)
    a.bt(dword(RBP, depl=68), 0)
    a.movzx8(EAX, byte(RBP, depl=64))
    a.movzx8(EAX, R8[6])
    a.etiquette("T1")
    a.jmp("T1")
    a.call("T1")
    a.jmp_r(RAX)
    a.call_r(RCX)
    a.ret()
    a.syscall()
    for r in R64:
        if r.n != 4:
            a.push(r)
            a.pop(r)
    a.rep_movsd()
    a.rep_movsq()
    a.rep_movsb()
    a.rdtsc()
    a.call_r(qword(etiq='T1'))
    a.jmp_r(qword(etiq='T1'))
    a.call_r(qword(RAX, depl=8))
    a.rva32('T1')
    a.rva64('T1')
    a.cld()
    for x in (XMM[0], XMM[1], XMM[9]):
        a.movd(x, EAX)
        a.movd(x, R32[12])
        a.movd(x, dword(RBP, depl=24))
        a.movd(R32[13], x)
        a.movd(EAX, x)
        a.movd(x, RAX)
        a.movd(RAX, x)
        for n in SS:
            a.ss(n, x, XMM[1])
            a.ss(n, XMM[0], x)
        a.ucomiss(x, XMM[1])
        a.ucomiss(XMM[0], x)
        a.cvtsi2ss(x, RAX)
        a.cvtsi2ss(x, EAX)
        a.cvttss2si(RAX, x)
        a.cvtss2si(RAX, x)
        a.cvttss2si(R64[9], x)
    a.ucomiss(XMM[0], dword(RBP, depl=136))
    a.paddq(XMM[15], XMM[14])
    a.pxor(XMM[15], XMM[15])
    a.movd(RAX, XMM[15])
    a.movd(XMM[14], RAX)
    a.mots32([1, 2, 3])
    a.adresse32("T1")
    a.octets(b"\x01\x02")
    return a


if __name__ == "__main__":
    ok = comparer(batterie(), "batterie")
    print("encodage x86-64 identique à GNU as" if ok else "ÉCART d'encodage")
    sys.exit(0 if ok else 1)
