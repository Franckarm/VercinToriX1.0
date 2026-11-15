#!/usr/bin/env python3
"""La carte du programme (0.6p) : dans l'ADN et l'ARNc, pour chaque molécule, ses quatre faces : ce qu'elle est, ce
qu'elle touche, ses racines, ses promesses. Écrite par le lecteur en vtx (chimie/adn.vtx), vérifiée contre la référence
chimie/adn.py, octet pour octet ; montrée par « lugus carte » ; refaite et comparée à la rétrotranscription."""
import os
import shutil
import subprocess
import sys
import tempfile

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, os.path.join(racine, "chimie"))
import adn  # noqa: E402

X = ".exe" if os.name == "nt" else ""
LUGUS = os.path.join(racine, "vtx-rs", "target", "release", "lugus" + X)
d = tempfile.mkdtemp()
echecs = 0


def verifier(nom, ok, detail=""):
    global echecs
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok else f" : {detail}"), flush=True)
    echecs += 0 if ok else 1


def lugus(*args):
    return subprocess.run([LUGUS, *args], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=d,
                          timeout=900)


def octets(f):
    return open(os.path.join(d, f), "rb").read()


def carte_de(f):
    texte = open(os.path.join(d, f), encoding="utf-8").read()
    sec = dict(adn.sections_adn(texte))
    return {l.split("|")[1] or l.split("|")[0]: l.split("|") for l in sec.get("carte", [])}


if not os.path.exists(LUGUS):
    print("lugus n'est pas construit (cargo build --release dans vtx-rs) : rien n'est vérifié")
    sys.exit(1)

os.makedirs(os.path.join(d, "ex"))
shutil.copytree(os.path.join(racine, "bibliotheque"), os.path.join(d, "bibliotheque"))
for nom in ("chute", "panel", "codon", "combat", "freinage"):
    shutil.copy(os.path.join(racine, "exemples128", nom + ".vtx"), os.path.join(d, "ex"))
open(os.path.join(d, "ex", "faces.vtx"), "w", encoding="utf-8").write("""// les quatre faces
fonction Réfléchir_Bien(a) {
    retour a + 1;
}

exemple Réfléchir_Bien(2) == 3
exemple double(4) == 8
exemple moyenne(4, 6) == 5

fonction double(x) {
    retour 2 * x;
}

// une fonction pure, lourde (une boucle), jamais recopiée en ligne
fonction somme_jusqu_a(n) {
    soit s = 0;
    pour i dans 0..n {
        s = s + i;
    }
    retour s;
}

fonction remplir(t, n) {
    pour i dans 0..n {
        t[i] = i * i;
    }
}

reaction moyenne(a, b) -> m {
    exige b != 0
    garantit m >= 0
    = (a + b) / 2 -> m
}

reaction freinage(v: flottant, d: flottant) -> a: flottant {
    = v * v / (2.0 * d)   -> a lourd
}

fonction principal() {
    soit t = [0, 0, 0, 0];
    remplir(t, 4);
    afficher(Réfléchir_Bien(2), double(3), moyenne(4, 6), somme_jusqu_a(10), t[3], freinage(30.0, 45.0));
}
""")
progs = ["faces", "chute", "panel", "codon", "combat", "freinage"]

# 1. la même carte que la référence, octet pour octet, dans l'ADN ; l'ARNc la porte, et sa rétrotranscription aussi
for p in progs:
    src = os.path.join("ex", p + ".vtx")
    r = lugus("ranger", src)
    texte = open(os.path.join(d, src), encoding="utf-8").read()
    mots, mols, t = adn.ranger_texte(texte, os.path.join(d, "ex"))
    adn.ecrire_adn(os.path.join(d, "ex", p + "_py.adn"), mots, mols, t)
    verifier(f"{p} : l'ADN rangé en vtx, avec sa carte, est celui de la référence, octet pour octet",
             r.returncode == 0 and octets(os.path.join("ex", p + ".adn")) == octets(os.path.join("ex", p + "_py.adn"))
             and "GU carte" in open(os.path.join(d, "ex", p + ".adn"), encoding="utf-8").read(), r.stderr[-300:])
    lugus("arnc", src, os.path.join("ex", p + "_c.arn"))
    lugus("retrotranscrire", os.path.join("ex", p + "_c.arn"), os.path.join("ex", p + "_c.adn"))
    verifier(f"{p} : l'ARNc porte la carte ; rétrotranscrit, l'ADN entier (la carte comprise)",
             octets(os.path.join("ex", p + "_c.adn")) == octets(os.path.join("ex", p + ".adn")))

# 2. les faces, sur le programme fait pour elles
c = carte_de(os.path.join("ex", "faces.adn"))
moy, fr, som, rem, pri = c.get("moyenne"), c.get("freinage"), c.get("somme_jusqu_a"), c.get("remplir"), c.get("principal")
verifier("ce qu'elle est : le genre, les lignes, l'en-tête",
         moy and moy[2] == "reaction" and moy[3] == "29-33" and moy[13] == "reaction moyenne(a, b) -> m"
         and pri and pri[2] == "fonction" and pri[13] == "fonction principal()", repr((moy, pri)))
verifier("ce qu'elle touche : la somme ne touche rien, remplir écrit la mémoire, principal touche le monde",
         som and som[5] == "0" and som[6] == "0" and rem and rem[5] == "2" and pri and pri[6] == "3",
         repr((som, rem, pri)))
debut = {v[0]: k for k, v in c.items()}
verifier("ses racines : principal est à un pas de la tête et appelle remplir et la somme ; la somme, à deux pas",
         pri and pri[7] == "1" and rem[0][1:] in pri[8].split(",") and som[0][1:] in pri[8].split(",") and som[7] == "2",
         repr((pri, som)))
verifier("ses promesses : exige, garantit, un exemple vérifié ; l'isotope lourd",
         moy[9:13] == ["1", "1", "1", "0"] and fr and fr[12] == "1", repr((moy, fr)))
r = lugus("carte", os.path.join("ex", "faces.adn"))
verifier("lugus carte : les quatre faces écrites, et les fonctions recopiées en ligne nommées",
         r.returncode == 0 and "moyenne : une réaction, lignes 29 à 33" in r.stderr
         and "ses promesses     : exige 1, garantit 1, 1 exemple vérifié" in r.stderr
         and "remplir : une fonction" in r.stderr and "ce qu'elle touche : écrit la mémoire" in r.stderr
         and "sans molécule à elles" in r.stderr and "Réfléchir_Bien" in r.stderr
         and "isotope lourd" in r.stderr, r.stderr[-1500:])
r2 = lugus("carte", os.path.join("ex", "faces.adn"), "--tout")
verifier("lugus carte --tout : les molécules empruntées aussi",
         "empruntée (au prélude ou à une bibliothèque)" in r2.stderr and len(r2.stderr) > len(r.stderr))
avant = sorted(os.listdir(os.path.join(d, "ex")))
r = lugus("carte", os.path.join("ex", "chute.vtx"))
verifier("lugus carte PROG.vtx : la carte, sans rien écrire à côté du programme",
         r.returncode == 0 and "chute : une réaction, lignes 5 à 12" in r.stderr
         and sorted(os.listdir(os.path.join(d, "ex"))) == avant, r.stderr[-500:])

# 3. ce que dit un brin sans carte : ses mots seuls (Belnap : les noms et les promesses inconnus)
lugus("transcrire", os.path.join("ex", "faces.adn"), "rapide.arn", "--isoforme", "rapide")
r = lugus("carte", "rapide.arn")
verifier("un ARN rapide : ce qu'il touche et ses racines viennent des mots ; ses noms et ses promesses sont inconnus",
         r.returncode == 0 and "ce brin n'a pas de carte rangée" in r.stderr and "son nom est inconnu" in r.stderr
         and "ses promesses     : inconnues" in r.stderr, r.stderr[:600])

# 4. la carte vérifiée à la rétrotranscription : vraie ; abîmée (faux, et où) ; absente (inconnu)
r = lugus("transcrire", os.path.join("ex", "faces.adn"), "x.mots")
verifier("transcrire : le texte vrai, la carte vraie",
         "le texte : vrai" in r.stderr and "la carte : vrai" in r.stderr, r.stderr[-400:])
texte = open(os.path.join(d, "ex", "faces.adn"), encoding="utf-8").read()
ligne = "|".join(som)
abime = texte.replace(ligne, ligne.replace(f"|{som[4]}|0|0|", f"|{som[4]}|3|3|", 1))
open(os.path.join(d, "abime.adn"), "w", encoding="utf-8").write(abime)
r = lugus("transcrire", "abime.adn", "y.mots")
verifier("une carte retouchée (la somme dite toucher le monde) : la carte est fausse, et dit dès quelle molécule",
         abime != texte and "la carte : faux" in r.stderr and f"dès la molécule {som[0]}" in r.stderr, r.stderr[-400:])
l = texte.split("\n")
i = l.index(next(x for x in l if x.startswith("GU carte ")))
n = int(l[i].split()[2])
sans = "\n".join(l[:i] + l[i + n + 2:])
open(os.path.join(d, "sans.adn"), "w", encoding="utf-8").write(sans)
r = lugus("transcrire", "sans.adn", "z.mots")
verifier("un ADN rangé avant la carte : le texte vrai, la carte inconnue",
         "le texte : vrai" in r.stderr and "la carte : inconnu" in r.stderr, r.stderr[-400:])

shutil.rmtree(d, ignore_errors=True)
print("la carte du programme : " + ("tout est conforme" if echecs == 0 else f"{echecs} écart(s)"))
sys.exit(1 if echecs else 0)
