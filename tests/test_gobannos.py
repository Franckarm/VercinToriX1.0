#!/usr/bin/env python3
"""Gobannos, premier temps (0.6v) : les mots de Lugus traduits en x86-64 par un programme écrit en vtx
(gobannos/gobannos.vtx, joué par Lugus), qui écrit lui-même l'exécutable (ELF sous Linux, PE sous Windows).

Pour chaque programme : la même sortie que Lugus (le texte, puis sortie() dans la même ligne « a,b,c »), et le même
compte d'instructions là où le programme l'écrit. Ce qui n'est pas encore traduit (les flottants…) arrête l'exécutable
en le disant (code 3), jamais en silence. Sous Linux, on vérifie aussi l'exécutable Windows (PE32+, KERNEL32)."""
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


def forger(prog, systeme):
    b = os.path.splitext(os.path.basename(prog))[0]
    mots = os.path.join(d, b + ".mots")
    r = lancer([LUGUS, "compiler", prog, mots])
    if r.returncode != 0:
        return None, "ne compile pas : " + r.stdout.decode("utf-8", "replace")[-300:]
    exe = os.path.join(d, b + (".exe" if systeme == "windows" else ".elf"))
    r = lancer([LUGUS, GOB], f"{mots}\n{exe}\n{systeme}\n")
    if r.returncode != 0 or not os.path.exists(exe):
        return None, r.stdout.decode("utf-8", "replace")[-400:] + r.stderr.decode("utf-8", "replace")[-400:]
    if not WIN:
        os.chmod(exe, 0o755)
    return exe, r.stdout.decode("utf-8", "replace")


def en_dunon(prog):
    """0.833 : Gobannos traduit les mots d'un programme en Dunon (l'entier de 64 bits) ; la division de 128 bits n'est
    pas encore traduite. Une copie du programme, « dunon; » en tête (après ses commentaires), à côté de lui."""
    s = open(prog, encoding="utf-8").read()
    l = s.split("\n")
    i = 0
    while i < len(l) and l[i].startswith("//"):
        i += 1
    if "dunon;" not in l:
        l.insert(i, "dunon;")
    c = os.path.join(os.path.dirname(prog), "dunon_" + os.path.basename(prog))
    open(c, "w", encoding="utf-8").write("\n".join(l))
    COPIES.append(c)
    return c


COPIES = []


def comparer(prog, entree="", clavier=False):
    systeme = "windows" if WIN else "linux"
    prog = en_dunon(prog)
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


E = os.path.join(racine, "exemples128")
PAREILS = ["alternance", "banc_traduction", "codon", "combat", "conseil", "cylindres", "duel", "gene", "panel",
           "quatre_verites", "releves", "supposons"]

# 1. les exemples de Lugus qui ne demandent que des entiers : la même sortie, au caractère près
for nom in PAREILS:
    ok, detail = comparer(os.path.join(E, nom + ".vtx"))
    verifier(f"exemples128/{nom}.vtx : la même sortie que Lugus (le compte des instructions compris s'il l'écrit)",
             ok, detail)

# 2. les bords : la division par zéro, la division signée par -1, les décalages, les entiers de 128 bits, les tableaux
#    de quits et de logiques, le quaternaire, la récursion, les textes
ok, detail = comparer(os.path.join(ici, "gobannos", "bords.vtx"))
verifier("les bords des entiers, la pile, les tableaux rangés, le quaternaire : comme Lugus", ok, detail)

# 3. le clavier : des lignes tapées (accents en UTF-8), une réponse à quatre valeurs, un nombre, la fin de l'entrée
LIRE = """fonction principal() {
    afficher("Ton nom ?");
    soit n = lire_ligne();
    afficher("Bonjour,", n, "!");
    soit l = lire_logique();
    afficher(l);
    soit x = nombre(lire_ligne());
    afficher(x * 2);
    afficher(lire_ligne(), "fin");
}
"""
p = os.path.join(d, "lire.vtx")
open(p, "w", encoding="utf-8").write(LIRE)
ok, detail = comparer(p, "Éloïse\noui\n21\n", clavier=True)
verifier("le clavier : les lignes, les accents, une réponse à quatre valeurs, la fin de l'entrée", ok, detail)

# 4. ce qui n'est pas encore traduit : l'exécutable s'arrête en le disant
FLOT = "fonction principal() {\n    afficher(\"avant\");\n    soit x = 1.5;\n    afficher(x * 2.0);\n}\n"
p = os.path.join(d, "flot.vtx")
open(p, "w", encoding="utf-8").write(FLOT)
exe, info = forger(en_dunon(p), "windows" if WIN else "linux")
r = lancer([exe]) if exe else None
verifier("un flottant (pas encore traduit) : « avant » écrit, puis l'arrêt dit (code 3), rien de faux",
         r is not None and r.returncode == 3 and r.stdout.decode("utf-8").replace("\r\n", "\n") == "avant\n"
         and "pas encore traduite par Gobannos" in r.stderr.decode("utf-8"),
         info if r is None else f"{r.returncode} {r.stdout!r} {r.stderr!r}")

# 4 bis. 0.833 : un programme à 128 bits (sans « dunon; ») : sa division de 128 bits n'est pas encore traduite ;
# l'exécutable s'arrête en le disant (code 3), sans rien écrire de faux
p = os.path.join(d, "large.vtx")
open(p, "w", encoding="utf-8").write("fonction principal() {\n    afficher(1 << 100);\n}\n")
exe, info = forger(p, "windows" if WIN else "linux")
r = lancer([exe]) if exe else None
verifier("l'entier de 128 bits (la division pas encore traduite) : l'arrêt dit (code 3), rien de faux",
         r is not None and r.returncode == 3 and r.stdout == b"" and "pas encore traduite par Gobannos" in r.stderr.decode("utf-8"),
         info if r is None else f"{r.returncode} {r.stdout!r} {r.stderr!r}")

# 5. l'exécutable Windows (vérifié sous Linux) : PE32+, une section, KERNEL32 et ses sept fonctions
if not WIN:
    exe, info = forger(en_dunon(os.path.join(E, "supposons.vtx")), "windows")
    ok = exe is not None
    if ok:
        b = open(exe, "rb").read()
        pe = struct.unpack_from("<I", b, 60)[0]
        ok = b[:2] == b"MZ" and b[pe:pe + 4] == b"PE\0\0" and struct.unpack_from("<H", b, pe + 24)[0] == 0x20B
        ok = ok and b"KERNEL32.dll" in b and all(f.encode() in b for f in (
            "GetStdHandle", "WriteFile", "ReadFile", "VirtualAlloc", "ExitProcess", "SetConsoleOutputCP"))
        r = subprocess.run(["objdump", "-p", exe], capture_output=True, text=True)
        ok = ok and (r.returncode != 0 or "pei-x86-64" in r.stdout)
    verifier("l'exécutable Windows : PE32+, KERNEL32 seul (GetStdHandle, WriteFile, ReadFile, VirtualAlloc…)", ok,
             info)

import shutil  # noqa: E402
shutil.rmtree(d, ignore_errors=True)
print("Gobannos : " + ("tout est conforme" if echecs == 0 else f"{echecs} écart(s)"))
for c in COPIES:
    if os.path.exists(c):
        os.remove(c)
sys.exit(1 if echecs else 0)
