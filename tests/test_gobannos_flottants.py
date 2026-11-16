#!/usr/bin/env python3
"""Les flottants dans Gobannos (0.6y) : la bibliothèque écrite en vtx avec des entiers seulement (gobannos/flottants.vtx)
donne, au bit près, ce que donne la machine pour chaque instruction flottante de Lugus, aux trois largeurs ; Gobannos
la traduit avec le programme et y envoie chaque instruction flottante : la même sortie et le même compte d'instructions
que Lugus."""
import os
import struct
import subprocess
import sys
import tempfile

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
WIN = os.name == "nt"
X = ".exe" if WIN else ""
LUGUS = os.path.join(racine, "vtx-rs", "target", "release", "lugus" + X)
GOB = os.path.join(racine, "gobannos", "gobannos.vtx")
d = tempfile.mkdtemp()
echecs = 0


def verifier(nom, ok, detail=""):
    global echecs
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok else f" : {detail}"), flush=True)
    echecs += 0 if ok else 1


def lancer(cmd, entree="", dossier=None, sans_clavier=False):
    env = dict(os.environ)
    if sans_clavier:
        env["VTX_SANS_CLAVIER"] = "1"
    return subprocess.run(cmd, input=entree.encode("utf-8"), capture_output=True, cwd=dossier, env=env, timeout=600)


BIB = os.path.join(d, "flottants.mots")
BIB_VTX = os.path.join(racine, "gobannos", "flottants.vtx")


def forger(prog, systeme):
    b = os.path.splitext(os.path.basename(prog))[0]
    mots = os.path.join(d, b + ".mots")
    r = lancer([LUGUS, "compiler", prog, mots])
    if r.returncode != 0:
        return None, "ne compile pas : " + r.stdout.decode("utf-8", "replace")[-300:]
    exe = os.path.join(d, b + (".exe" if systeme == "windows" else ".elf"))
    r = lancer([LUGUS, GOB], f"{mots}\n{exe}\n{systeme}\n{BIB}\n")
    if r.returncode != 0 or not os.path.exists(exe):
        return None, r.stdout.decode("utf-8", "replace")[-400:] + r.stderr.decode("utf-8", "replace")[-400:]
    if not WIN:
        os.chmod(exe, 0o755)
    return exe, r.stdout.decode("utf-8", "replace")


def comparer(prog, entree="", clavier=False):
    systeme = "windows" if WIN else "linux"
    exe, info = forger(prog, systeme)
    if exe is None:
        return False, info
    dossier = os.path.dirname(prog)
    rl = lancer([LUGUS, prog], entree, dossier, sans_clavier=not clavier)
    rg = lancer([exe], entree, dossier)
    lug = rl.stdout.decode("utf-8", "replace").replace("\r\n", "\n")
    out = rg.stdout.decode("utf-8", "replace").replace("\r\n", "\n")
    err = [l for l in rg.stderr.decode("utf-8", "replace").replace("\r\n", "\n").split("\n") if l]
    sorties = [l for l in err if not l.startswith("Gobannos")]
    attendu = (sorties[0] + "\n" if sorties else "") + out
    ok = rg.returncode == 0 and attendu == lug
    return ok, f"code {rg.returncode} ; {err[:2]} ; Lugus {lug[:200]!r} ; Gobannos {attendu[:200]!r}"



import random  # noqa: E402
sys.path.insert(0, os.path.join(racine, "spu128"))
sys.path.insert(0, os.path.join(racine, "spu64"))
sys.path.insert(0, racine)
import spu128  # noqa: E402
import vtx128  # noqa: E402

# 1. la bibliothèque : les mêmes mots par les deux compilateurs
vtx128.COMPAT_64 = False
texte = open(BIB_VTX, encoding="utf-8").read()
m_py, _ = vtx128.assembler(vtx128.compiler(texte, dossier=os.path.dirname(BIB_VTX)), True)
r = lancer([LUGUS, "compiler", BIB_VTX, BIB])
m_l = [int(x) for x in open(BIB).read().split(";")[0].split(",") if x] if r.returncode == 0 else None
verifier(f"gobannos/flottants.vtx : vtxc128 et vtx128.py donnent les mêmes mots ({len(m_py)})", m_l == m_py,
         r.stdout.decode("utf-8", "replace")[-300:])

# 2. la bibliothèque, jouée par Lugus, contre la machine (sa référence en Python, la même que qflot128.rs)
FMT = {0: (112, 14, 128), 1: (52, 10, 64), 2: (22, 8, 32)}


def brut(w, rnd):
    p, eb, t = FMT[w]
    emax = (1 << eb) - 1
    e = rnd.choice([1, 2, 2, 2, 2, 2, 2, 2, 0, 3])
    c = rnd.random()
    ex = emax if c < 0.05 else 0 if c < 0.12 else rnd.choice([1, 2, emax - 1, emax - 2]) if c < 0.2 else rnd.randrange(emax + 1)
    c = rnd.random()
    m = (0 if c < 0.05 else rnd.randrange(1 << rnd.randrange(1, p + 1)) if c < 0.15 else (1 << (p - 2)) if c < 0.25
         else (1 << p) - 1 if c < 0.3 else rnd.randrange(1 << (p - 2), 1 << p))
    return (e << (t - 2)) | (ex << p) | m


def piege(w, e0, rnd):
    p, eb, t = FMT[w]
    m = (1 << (p - 2 + rnd.randrange(0, 2))) | rnd.choice([0, 1, 3, 1 << rnd.randrange(1, p - 2), (1 << (p - 3)) | 1,
                                                            (1 << (p - 2)) - 1])
    m &= (1 << p) - 1
    if m < (1 << (p - 2)):
        m |= 1 << (p - 2)
    return (rnd.choice([1, 2]) << (t - 2)) | (e0 << p) | m


def cas(rnd):
    w = rnd.choice([0, 0, 1, 2])
    op = rnd.choice([0x40, 0x41, 0x42, 0x43, 0x47, 0x44, 0x45, 0x46, 0x5D, 0x5B, 0x5C, 0x48, 0x49, 0x4A, 0x4B, 0x6E, 0x6C, 0x6D, 0x6C, 0x6D,
                     0x40, 0x42, 0x43, 0x40, 0x41])
    x = rnd.randrange(3)
    p, eb, t = FMT[w]
    a, b = brut(w, rnd), brut(w, rnd)
    if op in (0x40, 0x41) and rnd.random() < 0.4:
        b = (a & ~((1 << p) - 1)) | rnd.randrange(1 << p) if rnd.random() < 0.5 else a ^ rnd.randrange(1 << min(8, p))
        if rnd.random() < 0.5:
            b ^= 3 << (t - 2)
    if rnd.random() < 0.35 and op in (0x40, 0x41, 0x42, 0x43, 0x47, 0x5D, 0x45):
        emax = (1 << eb) - 1
        e0 = rnd.choice([rnd.randrange(1, emax), 1, 2, emax - 1, rnd.randrange(1, 40), emax - rnd.randrange(1, 40)])
        e1 = max(0, min(emax - 1, e0 + rnd.randrange(-p // 2 - 2, p // 2 + 3)))
        a, b = piege(w, e0, rnd), piege(w, e1, rnd)
        if rnd.random() < 0.2:
            b &= ~(((1 << eb) - 1) << p)
    if op in (0x48, 0x49):
        a = rnd.choice([rnd.randrange(1 << 128), rnd.randrange(1 << rnd.randrange(1, 129)), 1 << 127, (1 << 128) - 1, 0, 1,
                        1 << 63, (1 << 64) - 1])
    if op == 0x6E:
        g = x if x in (1, 2) else 0
        a = brut(g, rnd) | (rnd.randrange(1 << 128) & ~((1 << FMT[g][2]) - 1) if rnd.random() < 0.3 else 0)
    elif op == 0x6D and rnd.random() < 0.6:
        a = rnd.choice([rnd.randrange(1 << t), rnd.randrange(1 << t) | (((1 << {128: 15, 64: 11, 32: 8}[t]) - 1) << (t - 1 - {128: 15, 64: 11, 32: 8}[t])), 0, 1 << (t - 1), 1])
    elif op not in (0x48, 0x49) and rnd.random() < 0.2:
        a |= rnd.randrange(1 << 128) & ~((1 << t) - 1)
    return op, w, x, a, b


def machine(op, w, x, a, b):
    m = spu128.CPU.__new__(spu128.CPU)
    res = {}
    m.poser = lambda d_, v, *k: res.setdefault("v", v)
    spu128.CPU.flottant(m, op, 1, a, b, w, x)
    return res["v"]


N = 0
ECARTS = []
for graine in (1, 2):
    rnd = random.Random(graine)
    L = [cas(rnd) for _ in range(3000)]
    entree = "essai\n" + "".join(f"{op} {w} {x} {a} {b}\n" for op, w, x, a, b in L) + "\n"
    r = lancer([LUGUS, BIB_VTX], entree, sans_clavier=False)
    lignes = [l for l in r.stdout.decode("utf-8", "replace").split("\n") if l.startswith("#")]
    if len(lignes) != len(L):
        ECARTS.append(f"la bibliothèque a rendu {len(lignes)} résultats sur {len(L)}")
        continue
    for (op, w, x, a, b), l in zip(L, lignes):
        _, h, lo = l.split("#")
        v = (int(h, 16) << 64) | int(lo, 16)
        N += 1
        if v != machine(op, w, x, a, b):
            ECARTS.append(f"op={op:#x} w={w} x={x} a={a:#x} b={b:#x}")
verifier(f"la bibliothèque contre la machine : {N} calculs tirés au hasard (les cas limites, les milieux, les "
         f"sous-normaux, les trois largeurs), au bit près", not ECARTS and N == 6000, repr(ECARTS[:4]))

# 3. Gobannos : les flottants traduits, la même sortie et le même compte d'instructions que Lugus
E = os.path.join(racine, "exemples128")
TOUS = os.path.join(ici, "gobannos", "flottants_tous.vtx")
ok, detail = comparer(TOUS)
verifier("chaque instruction flottante, aux trois largeurs, les mathématiques du prélude : la sortie de Lugus et "
         "le même compte d'instructions", ok, detail)
for nom in ("types_fonction", "freinage", "scene_incrementale", "chute"):
    ok, detail = comparer(os.path.join(E, nom + ".vtx"))
    verifier(f"exemples128/{nom}.vtx (des flottants) : la sortie de Lugus", ok, detail)

# 4. sans la bibliothèque (trois lignes d'entrée, comme en 0.6v) : le flottant arrête l'exécutable en le disant
systeme = "windows" if WIN else "linux"
mots = os.path.join(d, "sans.mots")
lancer([LUGUS, "compiler", TOUS, mots])
exe = os.path.join(d, "sans" + (".exe" if WIN else ".elf"))
lancer([LUGUS, GOB], f"{mots}\n{exe}\n{systeme}\n")
if os.path.exists(exe) and not WIN:
    os.chmod(exe, 0o755)
rg = lancer([exe]) if os.path.exists(exe) else None
verifier("sans la bibliothèque : l'instruction flottante arrête l'exécutable en le disant (code 3)",
         rg is not None and rg.returncode == 3 and "pas encore traduite" in rg.stderr.decode("utf-8", "replace"),
         "" if rg is None else rg.stderr.decode("utf-8", "replace")[-300:])

import shutil  # noqa: E402
shutil.rmtree(d, ignore_errors=True)
print("les flottants de Gobannos : " + ("tout est conforme" if echecs == 0 else f"{echecs} écart(s)"))
sys.exit(1 if echecs else 0)
