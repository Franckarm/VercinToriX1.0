#!/usr/bin/env python3
"""La fiabilité de l'ADN (chimie/adn.py ; docs/vtx-reactions.md, étape 5) : les trois témoins (la signature de chaque
molécule, l'ombre des colonnes entrelacées, les neutrons des frontières) réparent les avaries d'un programme rangé ; ce
qu'ils ne réparent pas est vu (variable), et rien n'est jamais réparé de travers.

    python3 tests/test_adn.py"""
import os
import random
import subprocess
import sys
import tempfile

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, os.path.join(racine, "chimie"))
import adn  # noqa: E402
import rs  # noqa: E402

echecs = []
ENV = dict(os.environ, PYTHONIOENCODING="utf-8")     # sous Windows aussi, les accents passent entre les programmes


def verifier(nom, ok, detail=""):
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok or not detail else " : " + detail), flush=True)
    if not ok:
        echecs.append(nom)


# 1. le code de Reed-Solomon : dans sa capacité (2 erreurs + effacements <= 4), toujours juste
g = random.Random(5)
faux = 0
for _ in range(1500):
    msg = [g.randrange(256) for _ in range(g.randrange(5, 251))]
    cw = msg + rs.coder(msg, 4)
    nf = g.randrange(0, 5)
    ne = g.randrange(0, (4 - nf) // 2 + 1)
    pos = g.sample(range(len(cw)), nf + ne)
    ab = list(cw)
    for p in pos:
        ab[p] ^= g.randrange(1, 256)
    faux += rs.decoder(ab, 4, pos[:nf]) != cw
verifier("Reed-Solomon : 1 500 mots de code abîmés dans sa capacité, tous rendus", faux == 0, str(faux))

# 2. les avaries, sur un programme d'environ 2 000 mots et sur un petit
dex = os.path.join(racine, "exemples128")
lignes = []
r = adn.essai([os.path.join(dex, "chute.vtx"), os.path.join(dex, "panel.vtx")], n=40, graine=11, ecrire=lignes.append)
print("\n".join(lignes))
muettes = sum(c["muet"] for c in r.values())
verifier("aucune erreur muette (rien n'est réparé de travers, rien ne passe sans être vu)", muettes == 0, str(muettes))
toutes = ["un bit", "un mot", "un mot effacé", "deux mots échangés", "deux mots d'une molécule", "une rafale de quatre mots",
          "une rafale de huit mots", "un témoin", "un mot et sa signature"]
verifier("chute.vtx (1 929 mots, 6 % de témoins) : tout réparé, jusqu'aux rafales de huit mots",
         all(r[("chute.vtx", gnr)]["réparé"] == 40 for gnr in toutes), str({gnr: r[("chute.vtx", gnr)] for gnr in toutes}))
verifier("panel.vtx (89 mots, une seule colonne) : un ou deux mots abîmés, un témoin : réparés",
         all(r[("panel.vtx", gnr)]["réparé"] == 40 for gnr in toutes[:5] + toutes[7:]))
verifier("au-delà de l'ombre (trois mots d'une colonne, seize au hasard) : vu ou réparé, jamais muet",
         all(r[(f, gnr)]["vu"] + r[(f, gnr)]["réparé"] == 40 for f in ("chute.vtx", "panel.vtx")
             for gnr in ("trois mots d'une colonne", "seize mots au hasard")))

# 3. le fichier : ranger, abîmer, transcrire (l'ARN = les mots seuls, comme vtx128.py mots)
d = tempfile.mkdtemp(prefix="adn-")
f_adn = os.path.join(d, "chute.adn")
py = [sys.executable, os.path.join(racine, "chimie", "adn.py")]
subprocess.run(py + ["ranger", os.path.join(dex, "chute.vtx"), f_adn], capture_output=True, text=True, encoding="utf-8",
               check=True, env=ENV)
mots, molecules, t = adn.lire_adn(f_adn)
abime = list(mots)
for i in (100, 101, 102, 900):
    abime[i] ^= 0xDEADBEEF << (i % 60)
adn.ecrire_adn(f_adn, abime, molecules, t)
s = subprocess.run(py + ["transcrire", f_adn, os.path.join(d, "chute.mots")], capture_output=True, text=True,
                   encoding="utf-8", env=ENV)
arn = [int(x) for x in open(os.path.join(d, "chute.mots")).read().split(";")[0].split(",")] if s.returncode == 0 else []
s2 = subprocess.run(py + ["transcrire", f_adn, os.path.join(d, "chute2.mots")], capture_output=True, text=True,
                    encoding="utf-8", env=ENV)
verifier("ranger, abîmer quatre mots, transcrire : l'ARN est le programme d'origine, l'ADN réparé réécrit",
         arn == mots and "faux (réparé)" in s.stdout and "l'ADN : vrai" in s2.stdout, s.stdout + s.stderr)
# 4. Lugus en Rust : le même ADN que Python, et la même lecture de chaque avarie (l'état, les mots, l'ADN réécrit)
lugus = os.path.join(racine, "vtx-rs", "target", "release", "lugus" + (".exe" if os.name == "nt" else ""))
if os.path.exists(lugus):
    f_rs = os.path.join(d, "chute-rs.adn")
    f_py = os.path.join(d, "chute-py.adn")
    subprocess.run([lugus, "ranger", os.path.join(dex, "chute.vtx"), f_rs], capture_output=True, text=True, encoding="utf-8")
    subprocess.run(py + ["ranger", os.path.join(dex, "chute.vtx"), f_py], capture_output=True, text=True, encoding="utf-8",
                   env=ENV)
    verifier("Lugus range le même ADN que Python, octet pour octet", open(f_rs, "rb").read() == open(f_py, "rb").read())
    mots0, molecules, t0 = adn.lire_adn(f_py)
    g = random.Random(23)
    ecarts, n = [], 0
    for genre in adn.GENRES:
        for k in range(12):
            abime, t = list(mots0), adn.copie_temoins(t0)
            adn.avarie(genre, abime, t, molecules, g)
            f_a = os.path.join(d, "abime.adn")
            adn.ecrire_adn(f_a, abime, molecules, t)
            # Python
            m_py, t_py = list(abime), adn.copie_temoins(t)
            etat_py, _ = adn.lire(m_py, molecules, t_py)
            # Rust
            r = subprocess.run([lugus, "transcrire", f_a, os.path.join(d, "abime.mots")], capture_output=True, text=True,
                               encoding="utf-8")
            etat_rs = next((l.split(" : ", 1)[1] for l in r.stderr.splitlines() if l.startswith("l'ADN : ")), "?")
            n += 1
            if etat_rs != adn.NOM_ETAT[etat_py]:
                ecarts.append((genre, "état", etat_py, etat_rs))
                continue
            if etat_py != adn.VARIABLE:
                m_rs = [int(x) for x in open(os.path.join(d, "abime.mots")).read().split(";")[0].split(",")]
                if m_rs != m_py:
                    ecarts.append((genre, "mots"))
                elif etat_py == adn.FAUX:
                    adn.ecrire_adn(os.path.join(d, "attendu.adn"), m_py, molecules, t_py)
                    if open(f_a).read() != open(os.path.join(d, "attendu.adn")).read():
                        ecarts.append((genre, "ADN réécrit"))
    verifier(f"Lugus lit l'ADN comme Python : {n - len(ecarts)}/{n} avaries, même état, mêmes mots, même ADN réparé",
             not ecarts, str(ecarts[:4]))
    r = subprocess.run([lugus, f_rs], capture_output=True, text=True, encoding="utf-8")
    verifier("lugus PROG.adn : vérifié, puis lancé (la chute : 2500)", r.stdout.startswith("2500"), r.stdout + r.stderr)
print("ADN : " + ("tout est conforme" if not echecs else f"{len(echecs)} échec(s)"))
sys.exit(1 if echecs else 0)
