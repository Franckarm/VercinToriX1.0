#!/usr/bin/env python3
"""0.852 : la forge écrite en vtx (forge_vtx.py : le Rust écrit par vtxc128) contre la machine émulée : chaque programme
que vtxc128 sait forger doit rendre les mêmes sorties, le même texte et le même état final que Lugus émulé (lugus
corpus) sur ses propres mots. Ceux qu'il ne sait pas encore forger sont comptés, par raison (l'ancienne forge les garde).

    python3 forge/test_forge_vtx.py [NOMBRE_DE_PROGRAMMES_AU_HASARD] [GRAINE]"""
import collections
import os
import random
import shutil
import subprocess
import sys
import tempfile

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, racine)
sys.path.insert(0, ici)
sys.path.insert(0, os.path.join(racine, "vtxc"))
import vtx128  # noqa: E402  (seulement pour ses programmes d'essai)
import forge128  # noqa: E402
import forge_vtx  # noqa: E402
from hasard64 import G  # noqa: E402

rustc = shutil.which("rustc")
if not rustc:
    print("rustc absent : la forge en vtx n'est pas essayée")
    sys.exit(0)
N = int(sys.argv[1]) if len(sys.argv) > 1 else 60
GRAINE = int(sys.argv[2]) if len(sys.argv) > 2 else 852
EXE = forge_vtx.LUGUS
TMP = tempfile.mkdtemp(prefix="forge-vtx-test-")

PROPRES = [
    ("carrés", "fonction carre(x) { retour x * x; } fonction principal() { soit s = 0; pour i dans 0..10 "
     "{ s = s + carre(i); } si s > 100 { sortie(s); } sinon { sortie(0); } }", []),
    ("fibonacci récursif", "fonction fib(n) { si n < 2 { retour n; } retour fib(n - 1) + fib(n - 2); } "
     "fonction principal() { sortie(fib(20)); }", []),
    ("tantque, arrêter, continuer", "fonction principal() { soit i = 0; soit s = 0; tantque i < 100 { i = i + 1; "
     "si i % 3 == 0 { continuer; } si i > 50 { arrêter; } s = s + i; } sortie(s); sortie(i); }", []),
    ("décalages et masques", "fonction principal() { soit x = 1; pour k dans 0..130 { x = (x << 1) | (k & 1); } "
     "sortie(x); sortie(x >> 100); sortie(x ^ 12345); sortie(x & 255); }", []),
    ("débordement de 128 bits", "fonction principal() { soit x = 1; pour k dans 0..200 { x = x * 3 + 1; } "
     "sortie(x); sortie(x / 7); sortie(x % 1000); soit z = 0; sortie(z - 1); }", []),
    ("entrées", "fonction principal() { sortie(entrée() + entrée()); }", [20, 22]),
    ("et, ou", "fonction principal() { soit n = 0; pour i dans 0..50 { si (i > 10 && i < 20) || i == 42 "
     "{ n = n + 1; } } sortie(n); }", []),
    ("ramasse-miettes : une liste gardée, des miettes", "structure N { v, s: N } fonction faire(n): N { soit l: N = nul; "
     "pour i dans 0..n { l = N { v: i, s: l }; soit m = N { v: 7, s: nul }; } retour l; } "
     "fonction somme(l: N) { soit s = 0; tantque l != nul { s = s + l.v; l = l.s; } retour s; } "
     "fonction principal() { soit a = faire(300); sortie(ramasser() > 0); soit b = faire(200); "
     "sortie(somme(a)); sortie(somme(b)); sortie(ramasser()); sortie(somme(a) + somme(b)); }", []),
    ("textes et logiques", "fonction principal() { soit t = \"bonjour\"; afficher(longueur(t)); soit l = vrai; "
     "selon l { vrai { sortie(1); } faux { sortie(2); } inconnu { sortie(3); } variable { sortie(4); } } "
     "afficher(t); }", []),
    ("pas de boucle", "fonction principal() { soit s = 0; pour i dans 0..100 pas 7 { s = s + i; } sortie(s); }", []),
]

cas = list(PROPRES)
cas += [(nom, src, list(e)) for nom, src, e, _ in vtx128.TESTS + vtx128.TESTS_128]
for k in range(N):
    cas.append((f"hasard {k}", G(random.Random(GRAINE * 7919 + k)).programme(), []))

modules, gardes, mots_de = [], [], []
laisses = collections.Counter()
for nom, src, e in cas:
    prog, mots = forge_vtx.programme_rust_vtx(src, None, nom)
    if prog is None:
        laisses[mots.split(" (ligne")[0]] += 1
        continue
    modules.append(f"mod p{len(gardes)} {{\nuse super::*;\n{prog}\n}}\n")
    gardes.append((nom, e))
    mots_de.append(mots)
print(f"{len(gardes)} programmes forgés par vtxc128, {sum(laisses.values())} laissés à l'ancienne forge :")
for r, n in laisses.most_common(30):
    print(f"  {n:4d}  {r}")
if not gardes:
    print("aucun programme forgé")
    sys.exit(1)
appels = "\n".join(f"        {k} => p{k}::lancer(&a[2..])," for k in range(len(gardes)))
main = f"fn main() {{\n    let a: Vec<String> = std::env::args().collect();\n    match a[1].parse::<usize>().unwrap() {{\n{appels}\n        _ => {{}}\n    }}\n}}\n"
rs = os.path.join(TMP, "tous.rs")
open(rs, "w", encoding="utf-8").write(forge128.noyau() + "\n" + "\n".join(modules) + main)
exe = os.path.join(TMP, "tous" + (".exe" if os.name == "nt" else ""))
r = subprocess.run([rustc] + forge128.rustc_options() + ["-o", exe, rs], capture_output=True, text=True)
if r.returncode:
    print("rustc a refusé les programmes forgés :\n" + r.stderr[-4000:])
    sys.exit(1)

with open(os.path.join(TMP, "corpus.txt"), "w") as f:
    for (nom, e), m in zip(gardes, mots_de):
        f.write(",".join(map(str, m)) + ";" + ",".join(map(str, e)) + "\n")
emul = subprocess.run([EXE, "corpus", os.path.join(TMP, "corpus.txt")], capture_output=True, text=True).stdout.split("\n")

ecarts, memoire, sans_fin = [], [], 0
env = dict(os.environ, FORGE_LIGNE="1")
for k, (nom, e) in enumerate(gardes):
    em = emul[k].strip()
    if em.startswith("ERREUR limite"):
        sans_fin += 1
        continue
    fo = subprocess.run([exe, str(k)] + [str(x) for x in e], capture_output=True, text=True, env=env, cwd=TMP,
                        timeout=120).stdout.strip()
    if em.startswith("ERREUR") or fo.startswith("ERREUR"):
        if not (em.startswith("ERREUR") and fo.startswith("ERREUR")):
            ecarts.append((nom, em[:200], fo[:200]))
        continue
    em = em[em.index("|"):]
    a, b = em.split("|"), fo.split("|")
    if a[1] != b[1] or [x for x in a if x.startswith("T:")] != [x for x in b if x.startswith("T:")]:
        ecarts.append((nom, em[:200], fo[:200]))
    elif em != fo:
        memoire.append(nom)
# le ramasse-miettes lit la pile de Lugus, que la forge ne tient pas mot pour mot (comme la forge Python) : ce qu'il
# garde peut différer, pas les sorties
memoire_pile = [n for n in memoire if n.startswith("ramasse-miettes")]
memoire = [n for n in memoire if n not in memoire_pile]
if memoire_pile:
    print(f"  la mémoire après le ramasse-miettes diffère (permis, comme pour la forge Python) : {memoire_pile}")
for x in ecarts[:6]:
    print("  ÉCART", x)
if memoire:
    print(f"  mémoire finale différente (sorties identiques) : {len(memoire)} : {memoire[:5]}")
print(f"{len(gardes) - sans_fin} programmes forgés en vtx : {len(gardes) - sans_fin - len(ecarts)} rendent les mêmes sorties "
      f"et le même texte que Lugus émulé ; {len(gardes) - sans_fin - len(ecarts) - len(memoire)} aussi la même mémoire"
      + (f" ({sans_fin} sans fin, écartés)" if sans_fin else ""))

# la fin commune embarquée par lugus (forge/queue_vtx.rs) : la même que forge128.queue_programme
queue_ok = open(forge_vtx.QUEUE, encoding="utf-8").read() == forge_vtx.queue_fixe() + "\n"
print(("OK  " if queue_ok else "ÉCART ") + "forge/queue_vtx.rs = forge128.queue_programme (sinon : forge_vtx.py --queue)")

# lugus forger (sans Python) : Gergovie (l'orage, demi-échelle, peu d'images) donne le même Rust que forge_vtx.py, et
# l'exécutable les mêmes empreintes et les mêmes images que celui de la forge Python
G_OK = True
gd = os.path.join(TMP, "gergovie")
os.makedirs(gd)
for f in ("gergovie_scene.vtx",):
    shutil.copy(os.path.join(racine, "belenos", f), gd)
src = open(os.path.join(racine, "belenos", "gergovie_orage.vtx"), encoding="utf-8").read()
src = src.replace("constante RD = 1;", "constante RD = 2;").replace("epreuve_orage(240, 120, 120, 240, 1)",
                                                                  "epreuve_orage(6, 3, 3, 6, 1)")
go = os.path.join(gd, "go.vtx")
open(go, "w", encoding="utf-8").write(src)
r = subprocess.run([EXE, "forger", go, "-o", os.path.join(gd, "gl"), "--rs", os.path.join(gd, "gl.rs")],
                   capture_output=True, text=True)
code_py, _ = forge_vtx.source_rust_vtx(src, gd, "go", None)
meme_rust = r.returncode == 0 and open(os.path.join(gd, "gl.rs"), encoding="utf-8").read() == code_py
print(("OK  " if meme_rust else "ÉCART ") + "lugus forger (sans Python) : le même Rust que forge_vtx.py, pour Gergovie"
      + ("" if r.returncode == 0 else " : " + r.stderr[-300:]))
env = dict(os.environ, VTX_GRENIER="0")
f = subprocess.run([sys.executable, os.path.join(ici, "forge128.py"), go, "-o", os.path.join(gd, "gp")],
                   capture_output=True, text=True, env=env)
sorties = []
for exe_g in ("gl", "gp"):
    im = os.path.join(gd, "im_" + exe_g)
    os.makedirs(im)
    o = subprocess.run([os.path.join(gd, exe_g)], capture_output=True, text=True, cwd=gd, timeout=900,
                       env=dict(os.environ, VTX_IMAGES=im)).stdout
    imgs = [open(os.path.join(im, x), "rb").read() for x in sorted(os.listdir(im))]
    sorties.append((o, imgs))
meme_g = meme_rust and f.returncode == 0 and sorties[0] == sorties[1] and "empreinte" in sorties[0][0]
G_OK = meme_rust and meme_g
print(("OK  " if meme_g else "ÉCART ") + f"Gergovie forgé par vtxc128 : les mêmes empreintes et les mêmes images "
      f"({len(sorties[0][1])}) que la forge Python")
shutil.rmtree(TMP, ignore_errors=True)
ok = not ecarts and not memoire and queue_ok and G_OK
print("La forge en vtx : conforme." if ok else f"{len(ecarts)} écart(s), {len(memoire)} mémoire(s)")
sys.exit(0 if ok else 1)
