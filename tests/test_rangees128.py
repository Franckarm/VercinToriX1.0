#!/usr/bin/env python3
"""Les tableaux de quits et de logiques de Lugus (0.5zz) : 64 éléments par mot (le mot de Lugus entier), les boucles
réécrites un mot à la fois, et les boucles voisines fondues en une seule passe. Des programmes tirés au hasard (des
tailles qui ne remplissent pas les mots, des bornes au milieu des mots, des boucles voisines de mêmes bornes ou non) :
ce que Lugus écrit doit être ce que calcule Python, élément par élément ; vtx128.py et vtxc128 donnent les mêmes mots.

    python3 tests/test_rangees128.py [nombre de programmes] [graine]"""
import os
import random
import subprocess
import sys
import tempfile

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, racine)
import vtx128  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 40
GRAINE = int(sys.argv[2]) if len(sys.argv) > 2 else 2026
X = ".exe" if os.name == "nt" else ""
LUGUS = os.path.join(racine, "vtx-rs", "target", "release", "lugus" + X)
d = tempfile.mkdtemp()
echecs = 0
_journal = os.environ.get("VTXJOURNAL")


def print(*a, **k):  # noqa: A001 : à l'écran et, depuis le .bat, dans son journal (on voit où l'on en est)
    import builtins
    builtins.print(*a, **k)
    if _journal:
        with open(_journal, "a", encoding="utf-8") as f:
            f.write(" ".join(str(x) for x in a) + "\n")



def verifier(nom, ok, detail=""):
    global echecs
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok else f" : {detail}"), flush=True)
    echecs += 0 if ok else 1


def v(q):
    return (q >> 1) & 1


def f(q):
    return q & 1


def lq(vv, ff):
    return (vv << 1) | ff


OPS_Q = {"&": lambda a, b: a & b, "|": lambda a, b: a | b, "^": lambda a, b: a ^ b, "min4": min, "max4": max}
OPS_L = {"et4": lambda a, b: lq(v(a) & v(b), f(a) | f(b)), "ou4": lambda a, b: lq(v(a) | v(b), f(a) & f(b)),
         "fusion": lambda a, b: a | b, "consensus": lambda a, b: a & b}
UN_L = {"non4": lambda a: lq(f(a), v(a)), "anti": lambda a: lq(1 - f(a), 1 - v(a))}
NOMS_L = ["inconnu", "faux", "vrai", "variable"]


def programme(r):
    n = r.randrange(1, 300)
    sorte = r.choice(["quits", "logique"])
    noms = ["ta", "tb", "tc", "td"]
    src = ["// machine : lugus"]
    for k, nm in enumerate(noms):
        src.append(f"tableau {nm}[{n}] de {sorte} @2[{k * 1000}];")
    src.append("fonction principal() {")
    val = {nm: [0] * n for nm in noms}
    # le remplissage (pas réécrit : l'indice y est calculé)
    for k, nm in enumerate(noms):
        a_, b_ = r.randrange(1, 9), r.randrange(4)
        expr = f"(i * {a_} + {b_}) % 4"
        src.append(f"    pour i dans 0..{n} {{ {nm}[i] = {'comme_logique(' + expr + ')' if sorte == 'logique' else expr}; }}")
        for i in range(n):
            val[nm][i] = (i * a_ + b_) % 4
    compteurs = []
    bornes_communes = (r.randrange(0, n + 1), None)
    for g in range(r.randrange(2, 7)):
        if r.random() < 0.6:
            a0 = bornes_communes[0]
            b0 = r.randrange(a0, n + 1) if bornes_communes[1] is None else bornes_communes[1]
            bornes_communes = (a0, b0)
        else:
            a0 = r.randrange(0, n + 1)
            b0 = r.randrange(a0, n + 1)
        cible, x, y = r.sample(noms, 3)
        genre = r.random()
        if genre < 0.55:
            if sorte == "quits":
                op = r.choice(list(OPS_Q))
                e = f"{op}({x}[i], {y}[i])" if op in ("min4", "max4") else f"{x}[i] {op} {y}[i]"
                fn = OPS_Q[op]
            else:
                if r.random() < 0.3:
                    op = r.choice(list(UN_L))
                    e = f"{op}({x}[i])"
                    fn = lambda a, b, op=op: UN_L[op](a)  # noqa: E731
                else:
                    op = r.choice(list(OPS_L))
                    e = f"{op}({x}[i], {y}[i])"
                    fn = OPS_L[op]
            src.append(f"    pour i dans {a0}..{b0} {{ {cible}[i] = {e}; }}")
            for i in range(a0, b0):
                val[cible][i] = fn(val[x][i], val[y][i])
        elif genre < 0.8:
            c = f"n{g}"
            k = r.randrange(4)
            const = NOMS_L[k] if sorte == "logique" else str(k)
            op = r.choice(["==", "!="])
            src.append(f"    soit {c} = 0;")
            src.append(f"    pour i dans {a0}..{b0} {{ si {x}[i] {op} {const} {{ {c} = {c} + 1; }} }}")
            compteurs.append((c, sum(1 for i in range(a0, b0) if (val[x][i] == k) == (op == "=="))))
        else:
            if sorte != "quits":
                continue
            c = f"s{g}"
            src.append(f"    soit {c} = 0;")
            src.append(f"    pour i dans {a0}..{b0} {{ {c} = {c} + {x}[i]; }}")
            compteurs.append((c, sum(val[x][i] for i in range(a0, b0))))
    attendu = []
    for nm in noms:
        src.append(f"    soit h_{nm} = 7;")
        lu = f"entier({nm}[i])" if sorte == "logique" else f"{nm}[i]"
        src.append(f"    pour i dans 0..{n} {{ h_{nm} = (h_{nm} * 5 + {lu} + i) % 1000003; }}")
        h = 7
        for i in range(n):
            h = (h * 5 + val[nm][i] + i) % 1000003
        attendu.append(str(h))
    for c, x in compteurs:
        attendu.append(str(x))
    src.append("    afficher(" + ", ".join([f"h_{nm}" for nm in noms] + [c for c, _ in compteurs]) + ");")
    src.append("}")
    return "\n".join(src) + "\n", " ".join(attendu)


r = random.Random(GRAINE)
mots_ok = sorties_ok = 0
for k in range(N):
    src, attendu = programme(r)
    fic = os.path.join(d, f"r{k}.vtx")
    open(fic, "w", encoding="utf-8").write(src)
    ref = vtx128.assembler(vtx128.compiler(src, dossier=d))
    sortie_mots = os.path.join(d, f"r{k}.mots")
    m, dit = None, ""
    for essai in range(2):
        # (un second essai : sous Windows, un antivirus peut tenir un instant un fichier tout juste écrit)
        rr = subprocess.run([LUGUS, "compiler", fic, sortie_mots], capture_output=True, text=True, encoding="utf-8",
                            errors="replace", timeout=120)
        dit = f"code {rr.returncode} ; sortie {rr.stdout[-200:]!r} ; erreur {rr.stderr[-300:]!r}"
        if rr.returncode == 0 and os.path.isfile(sortie_mots):
            m = [int(x) for x in open(sortie_mots).read().split(";")[0].split(",") if x.strip()]
            break
        print(f"   programme {k}, essai {essai + 1} : la compilation n'a pas abouti ({dit})", flush=True)
    if m == ref:
        mots_ok += 1
    else:
        verifier(f"programme {k} : mêmes mots", False, f"{len(ref)} contre {None if m is None else len(m)} ; {dit}")
        print(src)
        continue
    if k % 20 == 19:
        print(f"   … {k + 1} programmes sur {N}", flush=True)
    o = subprocess.run([LUGUS, fic], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120).stdout.strip()
    if o == attendu:
        sorties_ok += 1
    else:
        verifier(f"programme {k} : ce que Lugus écrit", False, f"{o!r} attendu {attendu!r}")
        print(src)
verifier(f"{N} programmes : vtx128.py et vtxc128 donnent les mêmes mots", mots_ok == N, f"{mots_ok}/{N}")
verifier(f"{N} programmes : Lugus écrit ce que calcule Python, élément par élément", sorties_ok == N, f"{sorties_ok}/{N}")
print("tableaux rangés de Lugus : " + ("tout est conforme" if echecs == 0 else f"{echecs} échec(s)"))
sys.exit(1 if echecs else 0)
