"""Assembleur x86-64 minimal (le sous-ensemble dont a besoin la traduction du SPU en code natif).

Chaque instruction est écrite deux fois : en octets (le code qui sera exécuté) et en texte (syntaxe Intel de GNU as),
pour que l'on puisse vérifier l'encodage contre l'assembleur GNU (natif/test_x86.py). Les sauts vers une étiquette
sont toujours longs (rel32) : pas de relaxation, le code est le même à chaque passe, ce qui le rend facile à reproduire
plus tard en vtx (le traducteur écrit en Vercintorix devra produire exactement les mêmes octets).
"""
import struct

NOMS64 = ["rax", "rcx", "rdx", "rbx", "rsp", "rbp", "rsi", "rdi"] + [f"r{i}" for i in range(8, 16)]
NOMS32 = ["eax", "ecx", "edx", "ebx", "esp", "ebp", "esi", "edi"] + [f"r{i}d" for i in range(8, 16)]
NOMS8 = ["al", "cl", "dl", "bl", "spl", "bpl", "sil", "dil"] + [f"r{i}b" for i in range(8, 16)]
TAILLES = {8: "byte", 32: "dword", 64: "qword", 128: "xmmword"}
CC = ["o", "no", "b", "ae", "e", "ne", "be", "a", "s", "ns", "p", "np", "l", "ge", "le", "g"]
CCN = {n: i for i, n in enumerate(CC)}
CCN.update({"z": 4, "nz": 5, "c": 2, "nc": 3})


class Reg:
    __slots__ = ("n", "t")

    def __init__(self, n, t):
        self.n, self.t = n, t

    def __repr__(self):
        return {64: NOMS64, 32: NOMS32, 8: NOMS8}[self.t][self.n]

    def __eq__(self, o):
        return isinstance(o, Reg) and o.n == self.n and o.t == self.t

    def __hash__(self):
        return hash((self.n, self.t))


class Xmm:
    __slots__ = ("n",)

    def __init__(self, n):
        self.n = n

    def __repr__(self):
        return f"xmm{self.n}"


class Mem:
    """[base + index*echelle + depl] ; base « rip » : relatif au compteur ordinal, vers une étiquette."""
    __slots__ = ("t", "base", "index", "ech", "depl", "etiq")

    def __init__(self, t, base=None, index=None, ech=1, depl=0, etiq=None):
        self.t, self.base, self.index, self.ech, self.depl, self.etiq = t, base, index, ech, depl, etiq

    def __repr__(self):
        if self.etiq is not None:
            return f"{TAILLES[self.t]} ptr [rip+{self.etiq}]"
        s = []
        if self.base is not None:
            s.append(NOMS64[self.base])
        if self.index is not None:
            s.append(f"{NOMS64[self.index]}*{self.ech}")
        t = "+".join(s)
        if self.depl or not s:
            t += f"{self.depl:+d}" if s else f"{self.depl}"
        return f"{TAILLES[self.t]} ptr [{t}]"


R64 = [Reg(i, 64) for i in range(16)]
R32 = [Reg(i, 32) for i in range(16)]
R8 = [Reg(i, 8) for i in range(16)]
RAX, RCX, RDX, RBX, RSP, RBP, RSI, RDI, R8_, R9_, R10_, R11_, R12_, R13_, R14_, R15_ = R64
EAX, ECX, EDX, EBX, ESP, EBP, ESI, EDI = R32[:8]
AL, CL, DL, BL = R8[:4]
XMM = [Xmm(i) for i in range(16)]


def dword(base=None, index=None, ech=1, depl=0, etiq=None):
    return Mem(32, base.n if isinstance(base, Reg) else base, index.n if isinstance(index, Reg) else index, ech, depl, etiq)


def qword(base=None, index=None, ech=1, depl=0, etiq=None):
    return Mem(64, base.n if isinstance(base, Reg) else base, index.n if isinstance(index, Reg) else index, ech, depl, etiq)


def byte(base=None, index=None, ech=1, depl=0, etiq=None):
    return Mem(8, base.n if isinstance(base, Reg) else base, index.n if isinstance(index, Reg) else index, ech, depl, etiq)


def signe32(v):
    v &= 0xFFFFFFFF
    return v - (1 << 32) if v >= 1 << 31 else v


ALU = {"add": 0, "or": 1, "adc": 2, "sbb": 3, "and": 4, "sub": 5, "xor": 6, "cmp": 7}
DECAL = {"shl": 4, "shr": 5, "sar": 7}
UNAIRE = {"not": 2, "neg": 3, "mul": 4, "div": 6}
SS = {"addss": 0x58, "mulss": 0x59, "subss": 0x5C, "divss": 0x5E, "sqrtss": 0x51}


class Asm:
    def __init__(self, base_virtuelle):
        self.code = bytearray()
        self.texte = []                 # lignes pour GNU as
        self.etiquettes = {}
        self.renvois = []               # (position, étiquette, sorte, fin) : 'rel' (rel32 depuis fin) ou 'abs' (adresse 32 bits)
        self.base = base_virtuelle      # adresse virtuelle de l'octet 0 de self.code
        self.image = 0x400000           # adresse de l'image (pour les adresses relatives du format PE)
        self.avec_texte = True

    # --- étiquettes et données
    def etiquette(self, nom):
        if nom in self.etiquettes:
            raise ValueError(f"étiquette en double : {nom}")
        self.etiquettes[nom] = len(self.code)
        if self.avec_texte:
            self.texte.append(f"{nom}:")

    def octets(self, b):
        self.code += b
        if self.avec_texte and b:
            self.texte.append(".byte " + ",".join(str(x) for x in b))

    def mots32(self, valeurs):
        self.code += struct.pack(f"<{len(valeurs)}I", *valeurs)
        if self.avec_texte and valeurs:
            for i in range(0, len(valeurs), 32):
                self.texte.append(".long " + ",".join(str(x) for x in valeurs[i:i + 32]))

    def adresse32(self, etiq):
        """Un mot de 32 bits : l'adresse virtuelle de l'étiquette."""
        self.renvois.append((len(self.code), etiq, "abs", 0))
        self.code += b"\0\0\0\0"
        if self.avec_texte:
            self.texte.append(f".long {etiq} - DEBUT + {self.base}")

    def adresse64(self, etiq):
        """Un mot de 64 bits : l'adresse virtuelle de l'étiquette."""
        self.renvois.append((len(self.code), etiq, "abs64", 0))
        self.code += b"\0" * 8
        if self.avec_texte:
            self.texte.append(f".quad {etiq} - DEBUT + {self.base}")

    def rva32(self, etiq):
        """Un mot de 32 bits : l'adresse relative à l'image (PE) de l'étiquette."""
        self.renvois.append((len(self.code), etiq, "rva", 0))
        self.code += b"\0\0\0\0"
        if self.avec_texte:
            self.texte.append(f".long {etiq} - DEBUT + {self.base - self.image}")

    def rva64(self, etiq):
        self.renvois.append((len(self.code), etiq, "rva64", 0))
        self.code += b"\0" * 8
        if self.avec_texte:
            self.texte.append(f".quad {etiq} - DEBUT + {self.base - self.image}")

    def quad(self, v):
        self.code += struct.pack("<Q", v)
        if self.avec_texte:
            self.texte.append(f".quad {v}")

    def aligner(self, n):
        while len(self.code) % n:
            self.code.append(0x90 if False else 0)
            if self.avec_texte:
                self.texte.append(".byte 0")

    def adresse(self, nom):
        return self.base + self.etiquettes[nom]

    def resoudre(self):
        for pos, etiq, sorte, fin in self.renvois:
            if etiq not in self.etiquettes:
                raise ValueError(f"étiquette inconnue : {etiq}")
            cible = self.etiquettes[etiq]
            if sorte == "rel":
                self.code[pos:pos + 4] = struct.pack("<i", cible - fin)
            elif sorte == "abs":
                self.code[pos:pos + 4] = struct.pack("<I", self.base + cible)
            elif sorte == "rva":
                self.code[pos:pos + 4] = struct.pack("<I", self.base + cible - self.image)
            elif sorte == "rva64":
                self.code[pos:pos + 8] = struct.pack("<Q", self.base + cible - self.image)
            else:
                self.code[pos:pos + 8] = struct.pack("<Q", self.base + cible)
        return bytes(self.code)

    # --- encodage
    def _modrm(self, reg, rm):
        """(bits REX R/X/B, octets ModRM [SIB] [déplacement], étiquette rip ou None)."""
        rex = 4 if reg & 8 else 0
        if isinstance(rm, (Reg, Xmm)):
            if rm.n & 8:
                rex |= 1
            return rex, bytes([0xC0 | (reg & 7) << 3 | (rm.n & 7)]), None
        m = rm
        if m.etiq is not None:
            return rex, bytes([(reg & 7) << 3 | 5]) + b"\0\0\0\0", m.etiq
        b, i, d = m.base, m.index, m.depl
        if b is None:
            if i is None:
                return rex, bytes([(reg & 7) << 3 | 4, 0x25]) + struct.pack("<i", d), None
            if i & 8:
                rex |= 2
            ss = {1: 0, 2: 1, 4: 2, 8: 3}[m.ech]
            return rex, bytes([(reg & 7) << 3 | 4, ss << 6 | (i & 7) << 3 | 5]) + struct.pack("<i", d), None
        if b & 8:
            rex |= 1
        mod = 0 if d == 0 and (b & 7) != 5 else (1 if -128 <= d <= 127 else 2)
        dp = b"" if mod == 0 else (struct.pack("<b", d) if mod == 1 else struct.pack("<i", d))
        if i is not None:
            if i & 8:
                rex |= 2
            ss = {1: 0, 2: 1, 4: 2, 8: 3}[m.ech]
            return rex, bytes([mod << 6 | (reg & 7) << 3 | 4, ss << 6 | (i & 7) << 3 | (b & 7)]) + dp, None
        if (b & 7) == 4:
            return rex, bytes([mod << 6 | (reg & 7) << 3 | 4, 0x24]) + dp, None
        return rex, bytes([mod << 6 | (reg & 7) << 3 | (b & 7)]) + dp, None

    def _ins(self, texte, op, reg=None, rm=None, w=False, pre=b"", imm=b"", rex8=False):
        """pre : préfixes (66, F3) ; op : octets du code d'opération ; reg : champ reg (nombre) ; rm : opérande."""
        out = bytearray(pre)
        rex = 8 if w else 0
        corps = b""
        etiq = None
        if rm is not None:
            bits, corps, etiq = self._modrm(reg, rm)
            rex |= bits
        if rex or rex8:
            out.append(0x40 | rex)
        out += op
        debut = len(self.code) + len(out)
        out += corps
        out += imm
        if etiq is not None:
            pos = debut + 1
            self.renvois.append((pos, etiq, "rel", len(self.code) + len(out)))
        self.code += out
        if self.avec_texte:
            self.texte.append(texte)

    @staticmethod
    def _t(o):
        return o.t if isinstance(o, (Reg, Mem)) else None

    @staticmethod
    def _rex8(*ops):
        return any(isinstance(o, Reg) and o.t == 8 and 4 <= o.n < 8 for o in ops)

    # --- instructions
    def alu(self, nom, dst, src):
        k = ALU[nom]
        t = self._t(dst)
        w = t == 64
        txt = f"{nom} {dst}, {src}"
        if isinstance(src, int):
            v = src if t == 8 else signe32(src)
            if t == 8 and isinstance(dst, Reg) and dst.n == 0:
                self._ins(txt, bytes([k * 8 + 4]), imm=struct.pack("<B", src & 255))
            elif t == 8:
                self._ins(txt, b"\x80", k, dst, imm=struct.pack("<B", src & 255), rex8=self._rex8(dst))
            elif -128 <= v <= 127:
                self._ins(txt, b"\x83", k, dst, w, imm=struct.pack("<b", v))
            elif isinstance(dst, Reg) and dst.n == 0:
                self._ins(txt, bytes([k * 8 + 5]), w=w, imm=struct.pack("<i", v))
            else:
                self._ins(txt, b"\x81", k, dst, w, imm=struct.pack("<i", v))
        elif isinstance(src, Reg):
            self._ins(txt, bytes([k * 8 + (0 if t == 8 else 1)]), src.n, dst, w, rex8=self._rex8(dst, src))
        else:
            self._ins(txt, bytes([k * 8 + (2 if t == 8 else 3)]), dst.n, src, w, rex8=self._rex8(dst))

    def mov(self, dst, src):
        t = self._t(dst)
        w = t == 64
        txt = f"mov {dst}, {src}"
        if isinstance(src, int):
            if isinstance(dst, Reg) and t == 32:
                self._ins(txt, bytes([0xB8 + (dst.n & 7)]), w=False, imm=struct.pack("<I", src & 0xFFFFFFFF),
                          pre=b"\x41" if dst.n & 8 else b"")
            elif t == 8:
                if isinstance(dst, Reg):
                    self._ins(txt, bytes([0xB0 + (dst.n & 7)]), imm=struct.pack("<B", src & 255),
                              pre=b"\x41" if dst.n & 8 else b"")
                else:
                    self._ins(txt, b"\xC6", 0, dst, imm=struct.pack("<B", src & 255))
            else:
                self._ins(txt, b"\xC7", 0, dst, w, imm=struct.pack("<i", signe32(src)))
        elif isinstance(src, Reg):
            self._ins(txt, b"\x88" if t == 8 else b"\x89", src.n, dst, w, rex8=self._rex8(dst, src))
        else:
            self._ins(txt, b"\x8A" if t == 8 else b"\x8B", dst.n, src, w, rex8=self._rex8(dst))

    def lea(self, dst, m):
        m = Mem(64, m.base, m.index, m.ech, m.depl, m.etiq)
        txt = f"lea {dst}, " + repr(m).split(" ptr ")[1]
        self._ins(txt, b"\x8D", dst.n, m, dst.t == 64)

    def test(self, a, b):
        t = self._t(a)
        txt = f"test {a}, {b}"
        if isinstance(b, int):
            if isinstance(a, Reg) and a.n == 0:
                self._ins(txt, b"\xA9", w=t == 64, imm=struct.pack("<I", b & 0xFFFFFFFF))
            else:
                self._ins(txt, b"\xF7", 0, a, t == 64, imm=struct.pack("<I", b & 0xFFFFFFFF))
        else:
            self._ins(txt, b"\x84" if t == 8 else b"\x85", b.n, a, t == 64, rex8=self._rex8(a, b))

    def decaler(self, nom, dst, n):
        k = DECAL[nom]
        w = self._t(dst) == 64
        if n == "cl":
            self._ins(f"{nom} {dst}, cl", b"\xD3", k, dst, w)
        elif n == 1:
            self._ins(f"{nom} {dst}, 1", b"\xD1", k, dst, w)
        else:
            self._ins(f"{nom} {dst}, {n}", b"\xC1", k, dst, w, imm=bytes([n & 255]))

    def unaire(self, nom, op):
        self._ins(f"{nom} {op}", b"\xF7", UNAIRE[nom], op, self._t(op) == 64)

    def imul(self, dst, src):
        self._ins(f"imul {dst}, {src}", b"\x0F\xAF", dst.n, src, dst.t == 64)

    def popcnt(self, dst, src):
        self._ins(f"popcnt {dst}, {src}", b"\x0F\xB8", dst.n, src, dst.t == 64, pre=b"\xF3")

    def movzx8(self, dst, src):
        self._ins(f"movzx {dst}, {src}", b"\x0F\xB6", dst.n, src, dst.t == 64, rex8=self._rex8(src))

    def setcc(self, cc, dst):
        self._ins(f"set{cc} {dst}", bytes([0x0F, 0x90 + CCN[cc]]), 0, dst, rex8=self._rex8(dst))

    def bt(self, op, bit):
        self._ins(f"bt {op}, {bit}", b"\x0F\xBA", 4, op, self._t(op) == 64, imm=bytes([bit]))

    def cmovcc(self, cc, dst, src):
        self._ins(f"cmov{cc} {dst}, {src}", bytes([0x0F, 0x40 + CCN[cc]]), dst.n, src, dst.t == 64)

    # sauts
    def _rel(self, txt, op, etiq):
        self.code += op
        self.renvois.append((len(self.code), etiq, "rel", len(self.code) + 4))
        self.code += b"\0\0\0\0"
        if self.avec_texte:
            self.texte.append(txt)

    def jmp(self, etiq):
        self._rel(f"{{disp32}} jmp {etiq}", b"\xE9", etiq)

    def jcc(self, cc, etiq):
        self._rel(f"{{disp32}} j{cc} {etiq}", bytes([0x0F, 0x80 + CCN[cc]]), etiq)

    def call(self, etiq):
        self._rel(f"call {etiq}", b"\xE8", etiq)

    def jmp_r(self, r):
        self._ins(f"jmp {r}", b"\xFF", 4, r)

    def call_r(self, r):
        self._ins(f"call {r}", b"\xFF", 2, r)

    def ret(self):
        self._ins("ret", b"\xC3")

    def syscall(self):
        self._ins("syscall", b"\x0F\x05")

    def push(self, r):
        self._ins(f"push {r}", bytes([0x50 + (r.n & 7)]), pre=b"\x41" if r.n & 8 else b"")

    def pop(self, r):
        self._ins(f"pop {r}", bytes([0x58 + (r.n & 7)]), pre=b"\x41" if r.n & 8 else b"")

    def rep_movsd(self):
        self._ins("rep movsd", b"\xA5", pre=b"\xF3")

    def rep_movsb(self):
        self._ins("rep movsb", b"\xA4", pre=b"\xF3")

    def rep_stosd(self):
        self._ins("rep stosd", b"\xAB", pre=b"\xF3")

    def rep_movsq(self):
        self._ins("rep movsq", b"\x48\xA5", pre=b"\xF3")

    def rdtsc(self):
        self._ins("rdtsc", b"\x0F\x31")

    def cld(self):
        self._ins("cld", b"\xFC")

    def ud2(self):
        self._ins("ud2", b"\x0F\x0B")

    # SSE
    def movd(self, dst, src):
        if isinstance(dst, Xmm):
            w = self._t(src) == 64
            self._ins(f"{'movq' if w else 'movd'} {dst}, {src}", b"\x0F\x6E", dst.n, src, w, pre=b"\x66")
        else:
            w = self._t(dst) == 64
            self._ins(f"{'movq' if w else 'movd'} {dst}, {src}", b"\x0F\x7E", src.n, dst, w, pre=b"\x66")

    def ss(self, nom, dst, src):
        self._ins(f"{nom} {dst}, {src}", bytes([0x0F, SS[nom]]), dst.n, src, pre=b"\xF3")

    def ucomiss(self, a, b):
        self._ins(f"ucomiss {a}, {b}", b"\x0F\x2E", a.n, b)

    def cvtsi2ss(self, dst, src):
        self._ins(f"cvtsi2ss {dst}, {src}", b"\x0F\x2A", dst.n, src, self._t(src) == 64, pre=b"\xF3")

    def cvttss2si(self, dst, src):
        self._ins(f"cvttss2si {dst}, {src}", b"\x0F\x2C", dst.n, src, dst.t == 64, pre=b"\xF3")

    def cvtss2si(self, dst, src):
        self._ins(f"cvtss2si {dst}, {src}", b"\x0F\x2D", dst.n, src, dst.t == 64, pre=b"\xF3")

    def paddq(self, dst, src):
        self._ins(f"paddq {dst}, {src}", b"\x0F\xD4", dst.n, src, pre=b"\x66")

    def pxor(self, dst, src):
        self._ins(f"pxor {dst}, {src}", b"\x0F\xEF", dst.n, src, pre=b"\x66")
