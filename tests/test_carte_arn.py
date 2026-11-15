#!/usr/bin/env python3
"""La carte du programme (0.6p, 0.6q) : dans l'ADN et l'ARNc, pour chaque molécule, les six faces d'un dé (ce qu'elle
est et ce qu'elle touche, ses racines et ses branches, ses promesses et sa mémoire), et au centre son état à la lecture. Écrite par le lecteur en vtx (chimie/adn.vtx), vérifiée contre la référence
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
VTX = os.path.join(racine, "vtx-rs", "target", "release", "vtx" + X)
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
    return {l.split("|")[1] or l.split("|")[0]: l.split("|", 16) for l in sec.get("faces", [])}


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
             and "GU faces" in open(os.path.join(d, "ex", p + ".adn"), encoding="utf-8").read(), r.stderr[-300:])
    lugus("arnc", src, os.path.join("ex", p + "_c.arn"))
    lugus("retrotranscrire", os.path.join("ex", p + "_c.arn"), os.path.join("ex", p + "_c.adn"))
    verifier(f"{p} : l'ARNc porte la carte ; rétrotranscrit, l'ADN entier (la carte comprise)",
             octets(os.path.join("ex", p + "_c.adn")) == octets(os.path.join("ex", p + ".adn")))

# 2. les faces, sur le programme fait pour elles
c = carte_de(os.path.join("ex", "faces.adn"))
moy, fr, som, rem, pri = c.get("moyenne"), c.get("freinage"), c.get("somme_jusqu_a"), c.get("remplir"), c.get("principal")
verifier("ce qu'elle est : le genre, les lignes, l'en-tête",
         moy and moy[2] == "reaction" and moy[3] == "29-33" and moy[16] == "reaction moyenne(a, b) -> m"
         and pri and pri[2] == "fonction" and pri[16] == "fonction principal()", repr((moy, pri)))
verifier("ce qu'elle touche : la somme ne touche rien, remplir écrit la mémoire, principal touche le monde",
         som and som[5] == "0" and som[6] == "0" and rem and rem[5] == "2" and pri and pri[6] == "3",
         repr((som, rem, pri)))
debut = {v[0]: k for k, v in c.items()}
verifier("ses racines et ses branches : principal est à un pas de la tête, appelée par elle, et appelle remplir et "
         "la somme ; la somme, à deux pas, appelée par principal",
         pri and pri[7] == "1" and pri[9] == "0" and rem[0][1:] in pri[8].split(",") and som[0][1:] in pri[8].split(",")
         and som[7] == "2" and som[9] == pri[0][1:], repr((pri, som)))
verifier("ses promesses : exige, garantit, un exemple vérifié ; l'isotope lourd",
         moy[10:14] == ["1", "1", "1", "0"] and fr and fr[13] == "1", repr((moy, fr)))
verifier("sa mémoire : l'empreinte de son texte ; rien n'était rangé avant (« ? »)",
         moy[14] == str(adn.fnv("".join(x + "\n" for x in open(os.path.join(d, "ex", "faces.vtx"), encoding="utf-8")
                                    .read().split("\n")[28:33]))) and moy[15] == "?", repr(moy))
r = lugus("carte", os.path.join("ex", "faces.adn"))
verifier("lugus carte : les quatre faces écrites, et les fonctions recopiées en ligne nommées",
         r.returncode == 0 and "moyenne : une réaction, lignes 29 à 33" in r.stderr
         and "ses promesses     : exige 1, garantit 1, 1 exemple vérifié" in r.stderr
         and "remplir : une fonction" in r.stderr and "ce qu'elle touche : écrit la mémoire" in r.stderr
         and "ses racines       : appelée par principal ; à 2 pas de la tête" in r.stderr
         and "ses branches      : n'appelle rien (une feuille)" in r.stderr
         and "au centre         : vrai (intacte à cette lecture)" in r.stderr
         and "sa mémoire        : son histoire est inconnue" in r.stderr
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
i = l.index(next(x for x in l if x.startswith("GU faces ")))
n = int(l[i].split()[2])
sans = "\n".join(l[:i] + l[i + n + 2:])
open(os.path.join(d, "sans.adn"), "w", encoding="utf-8").write(sans)
r = lugus("transcrire", "sans.adn", "z.mots")
verifier("un ADN rangé avant la carte : le texte vrai, la carte inconnue",
         "le texte : vrai" in r.stderr and "la carte : inconnu" in r.stderr, r.stderr[-400:])

# 5. l'histoire, d'un rangement à l'autre : la même que la référence ; inchangée, changée, nouvelle
avant = open(os.path.join(d, "ex", "faces.adn"), encoding="utf-8").read()
texte = open(os.path.join(d, "ex", "faces.vtx"), encoding="utf-8").read()
texte2 = texte.replace("        s = s + i;", "        s = s + i * 1;").replace("fonction principal() {", """fonction carre(x) {
    soit r = 0;
    pour i dans 0..x {
        r = r + x;
    }
    retour r;
}

fonction principal() {
    afficher(carre(7));""")
open(os.path.join(d, "ex", "faces.vtx"), "w", encoding="utf-8").write(texte2)
r = lugus("ranger", os.path.join("ex", "faces.vtx"))
mots, mols, t = adn.ranger_texte(texte2, os.path.join(d, "ex"), avant)
adn.ecrire_adn(os.path.join(d, "ex", "faces2_py.adn"), mots, mols, t)
c2 = carte_de(os.path.join("ex", "faces.adn"))
verifier("le second rangement : le même ADN que la référence (avec le rangement d'avant), octet pour octet",
         r.returncode == 0 and octets(os.path.join("ex", "faces.adn")) == octets(os.path.join("ex", "faces2_py.adn")),
         r.stderr[-300:])
verifier("sa mémoire : la somme retouchée est changée, la moyenne inchangée depuis 1 rangement, carre nouvelle",
         c2["somme_jusqu_a"][15] == "c" and c2["moyenne"][15] == "i1" and c2["carre"][15] == "n",
         repr((c2.get("somme_jusqu_a"), c2.get("moyenne"), c2.get("carre"))))
lugus("ranger", os.path.join("ex", "faces.vtx"))
c3 = carte_de(os.path.join("ex", "faces.adn"))
verifier("un troisième rangement sans retouche : la moyenne inchangée depuis 2 rangements, la somme depuis 1",
         c3["moyenne"][15] == "i2" and c3["somme_jusqu_a"][15] == "i1" and c3["carre"][15] == "i1",
         repr((c3["moyenne"][15], c3["somme_jusqu_a"][15], c3["carre"][15])))
r = lugus("transcrire", os.path.join("ex", "faces.adn"), "w.mots")
verifier("la carte d'un ADN qui a une histoire : vraie (l'histoire n'est pas dans le texte : elle est recopiée)",
         "la carte : vrai" in r.stderr, r.stderr[-300:])

# 6. le centre : l'état de chaque molécule à cette lecture
l = open(os.path.join(d, "ex", "faces.adn"), encoding="utf-8").read().split("\n")
i = l.index("GU mots 1") + 1
w = l[i].split(",")
k = int(c3["moyenne"][0][1:]) + 2
w[k] = str(int(w[k]) ^ 12345)
l[i] = ",".join(w)
open(os.path.join(d, "centre.adn"), "w", encoding="utf-8").write("\n".join(l))
r = lugus("carte", "centre.adn")
bloc = r.stderr[r.stderr.find("moyenne : une réaction"):]
verifier("au centre : la molécule abîmée est réparée à cette lecture, les autres intactes",
         "l'ADN : faux (réparé)" in r.stderr and "au centre         : faux (réparée à cette lecture)" in bloc.split("\n\n")[0]
         and "au centre         : vrai (intacte à cette lecture)" in r.stderr, r.stderr[:900])

# 7. Ogmios : la paillasse montre les six faces de la fonction choisie, et dit quand le texte a changé depuis
open(os.path.join(d, "g.txt"), "w").write("choisir principal\nexplique\nchoisir moyenne\nexplique\n")
r = subprocess.run([VTX, "paillasse", os.path.join(d, "ex", "faces.vtx"), "--faces", os.path.join(d, "centre.adn"),
                    "--gestes", os.path.join(d, "g.txt")], capture_output=True, text=True, encoding="utf-8", errors="replace")
verifier("la paillasse d'Ogmios : les six faces et le centre, d'une fonction (sur la carte) et d'une réaction (son onglet)",
         "principal : une fonction" in r.stdout and "Ses branches : appelle" in r.stdout and "Sa mémoire : inchangée" in r.stdout
         and "Les six faces de la réaction, et son état" in r.stdout and "Au centre : faux (réparée" in r.stdout
         and "le texte a changé depuis" not in r.stdout, r.stdout[-1500:] + r.stderr[-300:])
open(os.path.join(d, "ex", "faces.vtx"), "a", encoding="utf-8").write("// retouche\n")
r = subprocess.run([VTX, "paillasse", os.path.join(d, "ex", "faces.vtx"), "--faces", os.path.join(d, "centre.adn"),
                    "--gestes", os.path.join(d, "g.txt")], capture_output=True, text=True, encoding="utf-8", errors="replace")
verifier("le texte retouché depuis le dernier F5 : la paillasse le dit", "le texte a changé depuis" in r.stdout,
         r.stdout[-400:])

# 8. une carte à quatre faces (rangée en 0.6p) : inconnue
v4 = open(os.path.join(d, "ex", "faces.adn"), encoding="utf-8").read().replace("GU faces ", "GU carte ")
open(os.path.join(d, "v4.adn"), "w", encoding="utf-8").write(v4)
r = lugus("transcrire", "v4.adn", "v.mots")
verifier("une carte à quatre faces (0.6p) : inconnue, il faut ranger de nouveau",
         "la carte : inconnu, elle a quatre faces" in r.stderr, r.stderr[-300:])

shutil.rmtree(d, ignore_errors=True)
print("la carte du programme : " + ("tout est conforme" if echecs == 0 else f"{echecs} écart(s)"))
sys.exit(1 if echecs else 0)
