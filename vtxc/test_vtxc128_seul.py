#!/usr/bin/env python3
"""0.851 : vtxc128, le seul compilateur de Lugus (la décision du créateur, docs/vtx-un-compilateur.md). Rien de Python
ne compile ici : tout passe par le compilateur embarqué dans lugus (vtx-rs/vtxc128.mots). La règle « les mêmes mots que
vtx128.py » devient « les mêmes résultats » :

 1. Point fixe sans Python : le vtxc128 embarqué compile vtxc128.vtx et retombe sur ses propres mots (optimisé), et la
    forme non optimisée se recompile elle-même à l'identique.
 2. Chaque programme (la suite de Lugus, des programmes tirés au hasard à graines fixes, les réactions, les erreurs) est
    compilé sous trois réglages (prélude ; optimisé ; partition) : les trois doivent donner la même sortie, et cette
    sortie doit être celle qui est gardée dans tests/attendus/vtxc128_seul.json (le témoin : rangé en 0.851, quand
    vtx128.py et vtxc128 donnaient encore les mêmes mots ; « --refaire » le réécrit, à ne faire qu'après avoir regardé
    pourquoi une sortie change). Les programmes tirés au hasard (à graines fixes) ne sont pas faits pour être joués :
    l'empreinte de leurs mots est gardée ; elle change quand le compilateur change sa façon d'écrire (« --refaire »,
    après avoir vu que les sorties de la suite n'ont pas bougé).
 3. Ogmios sur Lugus : le pas à pas des exemples (comme avant).

    python3 vtxc/test_vtxc128_seul.py [--refaire] [--seul MOT]"""
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, ici)
from hasard64 import G  # noqa: E402
from hasard_reactions import R  # noqa: E402

EXE = os.path.join(racine, "vtx-rs", "target", "release", "lugus" + (".exe" if os.name == "nt" else ""))
SPU = os.path.join(racine, "vtx-rs", "target", "release", "vtx-spu" + (".exe" if os.name == "nt" else ""))
TEMOIN = os.path.join(racine, "tests", "attendus", "vtxc128_seul.json")
REFAIRE = "--refaire" in sys.argv
SEUL = sys.argv[sys.argv.index("--seul") + 1] if "--seul" in sys.argv else None
D = tempfile.mkdtemp(prefix="vtxc128-seul-")
COMBOS = ((1, 0, 0), (1, 1, 0), (1, 1, 1))
# les programmes qui écrivent à l'étage 0 (le code) : leur sortie dépend de la taille du code, donc du réglage (la
# machine refuse d'écrire dans un mot de l'ADN) ; leurs trois sorties sont gardées telles quelles
SELON_REGLAGE = {"suite : mémoire étagée"}
echecs = []


def verifier(nom, ok, detail=""):
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok or not detail else " : " + detail), flush=True)
    if not ok:
        echecs.append(nom)


def lire_mots(f):
    return [int(x) for x in open(f).read().split(";")[0].replace("\n", "").split(",") if x.strip()]


EMB = lire_mots(os.path.join(racine, "vtx-rs", "vtxc128.mots"))


def compiler(compilateur, src, pr, op, pa):
    """les mots de src compilés par compilateur (des mots de vtxc128), ou (None, le message)"""
    open(os.path.join(D, "c.mots"), "w").write(",".join(map(str, compilateur)) + ";\n")
    open(os.path.join(D, "source.vtx"), "w", encoding="utf-8").write(src)
    cm = os.path.join(D, "code.mots")
    if os.path.exists(cm):
        os.remove(cm)
    r = subprocess.run([EXE, "lancer", os.path.join(D, "c.mots"), "0", str(pr), str(op), str(pa)], cwd=D,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if not os.path.exists(cm):
        return None, (r.stdout + r.stderr).strip()
    return lire_mots(cm), ""


def jouer(src, entrees, pr, op, pa, seulement_compiler=False):
    """la sortie du programme compilé (ou « ERREUR » et le message du compilateur) ; seulement_compiler : l'empreinte de
    ses mots (les programmes tirés au hasard ne sont pas faits pour être joués : certains tournent sans fin)"""
    mots, msg = compiler(EMB, src, pr, op, pa)
    if mots is None:
        # le message, sans le chemin du dossier de travail
        return "ERREUR " + " / ".join(l.strip() for l in msg.replace(D, "").splitlines() if l.strip())[:400]
    if seulement_compiler:
        h = 14695981039346656037
        for m in mots:
            h = ((h ^ (m & ((1 << 64) - 1)) ^ (m >> 64)) * 1099511628211) & ((1 << 64) - 1)
        return f"compilé : {len(mots)} mots, empreinte {h:016x} (réglages {pr}{op}{pa})"
    p = os.path.join(D, "prog.mots")
    open(p, "w").write(",".join(map(str, mots)) + ";\n")
    try:
        r = subprocess.run([EXE, "lancer", p] + [str(e) for e in entrees], cwd=D, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=60, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return "TROP LONG"
    return (r.stdout + r.stderr).replace(D, "").strip() + f"\n[code {r.returncode}]"


# 1. le point fixe, sans Python
src_c = open(os.path.join(ici, "vtxc128.vtx"), encoding="utf-8").read()
if not SEUL:
    t0 = time.time()
    m_opt, msg = compiler(EMB, src_c, 0, 1, 0)
    verifier(f"point fixe (optimisé) : le vtxc128 embarqué compile vtxc128.vtx et retombe sur ses mots ({len(EMB)} mots, "
             f"{time.time() - t0:.0f} s)", m_opt == EMB, msg[-300:] + " (refaire : lugus renouveler vtxc/vtxc128.vtx)")
    t0 = time.time()
    m1, msg1 = compiler(EMB, src_c, 0, 0, 0)
    m2, msg2 = (compiler(m1, src_c, 0, 0, 0) if m1 else (None, msg1))
    verifier(f"point fixe (sans optimisation) : M1 = M2 ({len(m1 or [])} mots, {time.time() - t0:.0f} s)",
             m1 is not None and m1 == m2, (msg1 + msg2)[-300:])
    arbre = lire_mots(os.path.join(ici, "vtxc128.mots"))
    verifier("vtxc/vtxc128.mots = vtx-rs/vtxc128.mots (le compilateur embarqué dans lugus)", arbre == EMB)

# 2. les programmes : la même sortie sous trois réglages, et celle du témoin
cas = {}
sys.path.insert(0, racine)
import vtx128  # noqa: E402  (seulement pour lire la liste de ses programmes de test : rien n'y est compilé)
for nom, src, entrees, *_ in vtx128.TESTS:
    cas["suite : " + nom] = (src, list(entrees))
for nom, src, entrees, *_ in vtx128.TESTS_128:
    cas["Lugus : " + nom] = (src, list(entrees))
for k in range(12):
    cas[f"au hasard {k}"] = (G(random.Random(1000 + k)).programme(), [])
dex = os.path.join(racine, "exemples128")
for f in sorted(os.listdir(dex)):
    if f.endswith(".vtx"):
        src = open(os.path.join(dex, f), encoding="utf-8").read()
        if "reaction " in src and "entrée()" not in src and "lire_ligne" not in src:
            cas["exemples128/" + f] = (src, [])
for k in range(16):
    cas[f"réaction au hasard {k}"] = (R(random.Random(2000 + k)).programme(), [])
ERREURS = {
    "un cycle": "reaction principal() { = b + 1 -> a\n = a + 1 -> b\n }",
    "une liaison donnée deux fois": "reaction principal() { = 1 -> a\n = 2 -> a\n }",
    "des m + des s": "reaction f() -> d { = 2 m -> a\n = 3 s -> b\n = a + b -> d }\nfonction principal() { sortie(f()); }",
    "une variable inconnue": "fonction principal() { sortie(zut); }",
    "un ; oublié": "fonction principal() { soit a = 1 sortie(a); }",
}
# un exemple faux : « lugus PROG.vtx » rejoue les exemples avant de lancer le programme, et s'arrête
EX_FAUX = ("reaction moyenne(a, b) -> m {\n    total = a + b -> t\n    moitie = t / 2 -> m\n}\n"
           "exemple moyenne(10, 20) == 16;\nfonction principal() { sortie(moyenne(1, 3)); }\n")
for nom, src in ERREURS.items():
    cas["erreur : " + nom] = (src, [])
if SEUL:
    cas = {k: v for k, v in cas.items() if SEUL in k}

temoin = {}
if os.path.exists(TEMOIN) and not REFAIRE:
    temoin = json.load(open(TEMOIN, encoding="utf-8"))
t0 = time.time()
nouveau = {}
diff_reglages, diff_temoin, absents = [], [], []
for k, (nom, (src, entrees)) in enumerate(cas.items()):
    tk = time.time()
    hasard = nom.startswith("au hasard") or nom.startswith("réaction au hasard")
    sorties = [jouer(src, entrees, *c, seulement_compiler=hasard) for c in COMBOS]
    if time.time() - tk > 20:
        print(f"    (lent : {nom} {time.time() - tk:.0f} s)", flush=True)
    if k % 20 == 19:
        print(f"    … {k + 1}/{len(cas)} ({time.time() - t0:.0f} s)", flush=True)
    if not hasard and nom not in SELON_REGLAGE and len(set(sorties)) != 1:
        diff_reglages.append((nom, [s[-120:] for s in sorties]))
    garde = sorties[0] if not (hasard or nom in SELON_REGLAGE) else " | ".join(sorties)
    nouveau[nom] = garde
    if not REFAIRE:
        if nom not in temoin:
            absents.append(nom)
        elif temoin[nom] != garde:
            diff_temoin.append((nom, temoin[nom][-160:], garde[-160:]))
for e in diff_reglages[:5]:
    print("   ", e)
verifier(f"{len(cas)} programmes : la même sortie sous les trois réglages ({time.time() - t0:.0f} s)", not diff_reglages)
if REFAIRE:
    os.makedirs(os.path.dirname(TEMOIN), exist_ok=True)
    json.dump(nouveau, open(TEMOIN, "w", encoding="utf-8"), ensure_ascii=False, indent=0, sort_keys=True)
    print(f"témoin réécrit : {TEMOIN} ({len(nouveau)} sorties)")
else:
    for e in diff_temoin[:5]:
        print("   ", e)
    verifier(f"les sorties du témoin : {len(cas) - len(diff_temoin) - len(absents)}/{len(cas)} identiques"
             + (f" ({len(absents)} absent(s) du témoin)" if absents else ""), not diff_temoin and not absents,
             str(absents[:3]))
    n_err = sum(1 for k in cas if k.startswith("erreur : ") and nouveau[k].startswith("ERREUR"))
    verifier(f"les erreurs : {n_err}/{sum(1 for k in cas if k.startswith('erreur : '))} refusées par le compilateur",
             n_err == sum(1 for k in cas if k.startswith("erreur : ")))

if not SEUL:
    f = os.path.join(D, "faux.vtx")
    open(f, "w", encoding="utf-8").write(EX_FAUX)
    r = subprocess.run([EXE, f], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=D,
                       stdin=subprocess.DEVNULL)
    verifier("lugus refuse un exemple faux (et ne lance pas le programme)", r.returncode != 0 and "2" not in r.stdout.split(),
             (r.stdout + r.stderr)[-300:])

# 3. Ogmios sur Lugus : le pas à pas des exemples
if not SEUL:
    exs = sorted(f for f in os.listdir(dex) if f.endswith(".vtx")
                 and "instructions()" not in open(os.path.join(dex, f), encoding="utf-8").read())
    ecarts = []
    for f in exs:
        r = subprocess.run([SPU, "essai-pas128", os.path.join(dex, f)], cwd=D, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if r.returncode != 0 or not r.stdout.rstrip().endswith("conforme") or "NON CONFORME" in r.stdout:
            ecarts.append(f)
    verifier(f"Ogmios sur Lugus : {len(exs) - len(ecarts)}/{len(exs)} exemples, pas à pas et vue conformes", not ecarts,
             str(ecarts))

shutil.rmtree(D, ignore_errors=True)
print("vtxc128 seul : " + ("tout est conforme" if not echecs else f"{len(echecs)} échec(s)"))
sys.exit(1 if echecs else 0)
