#!/usr/bin/env python3
"""Le chemin dans les deux sens (0.6n bis) : Cube → Hex → ADN → ARN, et retour, ARN → ADN (la rétrotranscription :
l'ADNc), ADN → Hex → Cube ; chaque station rend les mêmes mots, et tout est fait par le lecteur d'ADN écrit en vtx
(chimie/adn.vtx, embarqué dans lugus). Vérifié contre la référence chimie/adn.py, octet pour octet : le hex, l'ADN rangé
depuis un hex ou un cube, l'ADNc de chaque isoforme ; un hex et un cube se lancent ; les avaries : un hex retouché (pris
tel qu'il est, et dit), des places qui ne se suivent pas (refusé), un cube abîmé ou effacé (réparé par son anti-cube et
son ombre), un ARN sûr abîmé ou à la coiffe abîmée (réparé par ses témoins), un ARN rapide abîmé (variable : rien
n'est écrit)."""
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


def mots_adn(f):
    return adn.lire_adn(os.path.join(d, f))[0]


def adn_des_mots(f, mots):
    """la référence : l'ADN de mots seuls (le découpage, les témoins, sans introns)"""
    m = adn.decouper(mots)
    adn.ecrire_adn(os.path.join(d, f), mots, m, adn.temoins(mots, m))


if not os.path.exists(LUGUS):
    print("lugus n'est pas construit (cargo build --release dans vtx-rs) : rien n'est vérifié")
    sys.exit(1)

ISO = """// machine : lugus
// un isotope lourd, des accents : « é », « œ »
reaction freinage(v: flottant, d: flottant) -> a: flottant {
    = v * v / (2.0 * d)   -> a lourd
}
fonction principal() {
    afficher(freinage(30.0, 45.0));
    afficher("é œ");
    sortie(7);
}
"""
open(os.path.join(d, "iso.vtx"), "w", encoding="utf-8").write(ISO)
progs = ["iso"]
for nom in ("chute", "panel"):
    shutil.copy(os.path.join(racine, "exemples128", nom + ".vtx"), d)
    progs.append(nom)

for p in progs:
    lance = lugus(p + ".vtx").stdout
    r = lugus("ranger", p + ".vtx")
    verifier(f"{p} : rangé", r.returncode == 0, r.stderr)
    m0 = mots_adn(p + ".adn")

    # ADN → Hex
    r = lugus("hex", p + ".adn")
    adn.ecrire_hex(os.path.join(d, p + "_ref.hex"), m0)
    verifier(f"{p} : ADN → hex, le même que la référence, octet pour octet ({len(m0)} mots)",
             r.returncode == 0 and octets(p + ".hex") == octets(p + "_ref.hex"), r.stderr)
    verifier(f"{p} : le hex relu par la référence redonne les mots",
             adn.lire_hex(os.path.join(d, p + ".hex")) == (m0, False))

    # Hex → ADN
    r = lugus("ranger", p + ".hex", p + "_h.adn")
    adn_des_mots(p + "_hr.adn", m0)
    verifier(f"{p} : hex → ADN, le même que la référence (les mots seuls, leurs témoins refaits)",
             r.returncode == 0 and octets(p + "_h.adn") == octets(p + "_hr.adn"), r.stderr)

    # ADN → Cube → ADN
    r = lugus("cube", p + ".adn", "262")
    cube = "cube128-1-262.cub"
    verifier(f"{p} : ADN → cube (cube, anti-cube, ombre)",
             r.returncode == 0 and all(os.path.exists(os.path.join(d, x + "128-1-262.cub")) for x in ("cube", "anticube", "ombre")),
             r.stderr)
    r = lugus("ranger", cube, p + "_c.adn")
    verifier(f"{p} : cube → ADN, les mêmes mots, le même ADN que depuis le hex",
             r.returncode == 0 and "le cube : vrai" in r.stderr and octets(p + "_c.adn") == octets(p + "_hr.adn"), r.stderr)

    # lancer un hex, un cube
    rh = lugus(p + ".hex")
    rc = lugus(cube)
    verifier(f"{p} : le hex et le cube se lancent, la sortie du programme",
             rh.stdout == lance and rc.stdout == lance and lance != "", repr((rh.stdout, rc.stdout, lance, rh.stderr)))

    # ADN → ARN → ADNc, chaque isoforme
    for iso in ("rapide", "sur", "memoire", "complet"):
        a = f"{p}_{iso}.arn"
        lugus("transcrire", p + ".adn", a, "--isoforme", iso)
        r = lugus("retrotranscrire", a, f"{p}_{iso}_c.adn")
        e, mots, mols, t = adn.adnc(os.path.join(d, a))
        adn.ecrire_adn(os.path.join(d, f"{p}_{iso}_cr.adn"), mots, mols, t)
        verifier(f"{p} : ARN {iso} → ADNc, le même que la référence, les mots de l'ADN",
                 r.returncode == 0 and octets(f"{p}_{iso}_c.adn") == octets(f"{p}_{iso}_cr.adn") and mots == m0
                 and mots_adn(f"{p}_{iso}_c.adn") == m0, r.stderr)

# l'ARNc (0.6o) : le programme naît en ARN, sans fichier d'ADN ; rétrotranscrit, il rend l'ADN entier
for p in progs:
    os.makedirs(os.path.join(d, "ne"), exist_ok=True)
    shutil.copy(os.path.join(d, p + ".vtx"), os.path.join(d, "ne"))
    src = os.path.join("ne", p + ".vtx")
    r = lugus("arnc", src)
    verifier(f"{p} : vtx → ARNc, aucun ADN écrit ; lancé, la sortie du programme",
             r.returncode == 0 and sorted(os.listdir(os.path.join(d, "ne"))) == [p + ".arn", p + ".vtx"]
             and lugus(os.path.join("ne", p + ".arn")).stdout == lugus(p + ".vtx").stdout, r.stderr)
    r = lugus("retrotranscrire", os.path.join("ne", p + ".arn"))
    lugus("ranger", src, os.path.join("ne", "ref.adn"))
    e, mots, mols, t = adn.adnc(os.path.join(d, "ne", p + ".arn"))
    adn.ecrire_adn(os.path.join(d, "ne", "py.adn"), mots, mols, t)
    c = octets(os.path.join("ne", p + "-c.adn"))
    verifier(f"{p} : ARNc → ADNc : l'ADN entier (texte, isotopes, compilateur), celui de ranger et de la référence, octet pour octet",
             r.returncode == 0 and c == octets(os.path.join("ne", "ref.adn")) and c == octets(os.path.join("ne", "py.adn")),
             r.stderr)
    r = lugus("transcrire", os.path.join("ne", p + "-c.adn"), os.path.join("ne", "retour.arn"), "--isoforme", "arnc")
    verifier(f"{p} : ADNc → ARNc : l'ARNc de départ, octet pour octet ; le texte vérifié : vrai",
             octets(os.path.join("ne", "retour.arn")) == octets(os.path.join("ne", p + ".arn")) and "le texte : vrai" in r.stderr,
             r.stderr)
    shutil.rmtree(os.path.join(d, "ne"))

# le tour entier, dans l'ordre du créateur : la chaîne descendue jusqu'au cube, puis remontée station par station
#   vtx → ARNc → ADNc → hex → cube → hex → ADN → ARN, lancé
os.makedirs(os.path.join(d, "tour"), exist_ok=True)
shutil.copy(os.path.join(d, "chute.vtx"), os.path.join(d, "tour"))
T = lambda x: os.path.join("tour", x)
etapes = [("arnc", T("chute.vtx"), T("t1.arn")), ("retrotranscrire", T("t1.arn"), T("t2.adn")),
          ("hex", T("t2.adn"), T("t3.hex")), ("cube", T("t3.hex"), "330"),
          ("hex", T("cube128-1-330.cub"), T("t5.hex")), ("ranger", T("t5.hex"), T("t6.adn")),
          ("transcrire", T("t6.adn"), T("t7.arn"), "--isoforme", "rapide")]
ok = True
for e in etapes:
    r = lugus(*e)
    ok = ok and r.returncode == 0
fin = lugus(T("t7.arn")).stdout
verifier("le tour entier : vtx → ARNc → ADNc → hex → cube → hex → ADN → ARN, lancé : la sortie du programme ; "
         "le hex du retour est celui de l'aller",
         ok and fin == lugus("chute.vtx").stdout and fin != "" and mots_adn(T("t6.adn")) == mots_adn("chute.adn")
         and octets(T("t3.hex")) == octets(T("t5.hex")))

# les avaries du hex
m0 = mots_adn("chute.adn")
l = open(os.path.join(d, "chute.hex"), encoding="utf-8").read().split("\n")
l[5] = l[5][:-1] + ("0" if l[5][-1] != "0" else "1")
open(os.path.join(d, "retouche.hex"), "w", encoding="utf-8").write("\n".join(l))
r = lugus("ranger", "retouche.hex", "retouche.adn")
mr, retouche = adn.lire_hex(os.path.join(d, "retouche.hex"))
verifier("un hex retouché à la main : dit, et pris tel qu'il est écrit (les mots retouchés rangés)",
         r.returncode == 0 and "retouché" in r.stderr and retouche and mots_adn("retouche.adn") == mr and mr != m0, r.stderr)
l = open(os.path.join(d, "chute.hex"), encoding="utf-8").read().split("\n")
l[3], l[4] = l[4], l[3]
open(os.path.join(d, "desordre.hex"), "w", encoding="utf-8").write("\n".join(l))
r = lugus("ranger", "desordre.hex", "desordre.adn")
verifier("un hex dont les places ne se suivent pas : refusé, rien n'est écrit",
         r.returncode != 0 and "ne se suivent pas" in r.stderr and not os.path.exists(os.path.join(d, "desordre.adn")), r.stderr)

# les avaries du cube : un mot abîmé dans le cube, puis le cube effacé (l'anti-cube et l'ombre le refont)
lugus("cube", "chute.adn", "392")
f = os.path.join(d, "cube128-1-392.cub")
b = bytearray(open(f, "rb").read())
b[8 + 4 + 16 * 3 + 5] ^= 0x5A
open(f, "wb").write(bytes(b))
r = lugus("ranger", "cube128-1-392.cub", "abime.adn")
verifier("un mot abîmé dans le cube : réparé par l'anti-cube et l'ombre, les mots d'origine",
         r.returncode == 0 and "réparé" in r.stderr and mots_adn("abime.adn") == m0, r.stderr)
os.remove(f)
r = lugus("ranger", "cube128-1-392.cub", "efface.adn")
verifier("le cube effacé : refait depuis son anti-cube, les mots d'origine",
         r.returncode == 0 and mots_adn("efface.adn") == m0 and os.path.exists(f), r.stderr)

# les avaries de l'ARN
def abimer_arn(source, cible, places, coiffe=False):
    l = open(os.path.join(d, source), encoding="utf-8").read().split("\n")
    i = l.index("GU mots 1") + 1
    w = l[i].split(",")
    for k in places:
        w[k] = str(int(w[k]) ^ (1 << 77) ^ 12345)
    l[i] = ",".join(w)
    if coiffe:
        j = l.index("GU coiffe 1") + 1
        s, iso = l[j].split("|")
        l[j] = str(int(s) ^ 1) + "|" + iso
    open(os.path.join(d, cible), "w", encoding="utf-8").write("\n".join(l))


abimer_arn("chute_sur.arn", "abime_sur.arn", [4, 40])
r = lugus("retrotranscrire", "abime_sur.arn", "abime_sur_c.adn")
e, mots, mols, t = adn.adnc(os.path.join(d, "abime_sur.arn"))
adn.ecrire_adn(os.path.join(d, "abime_sur_cr.adn"), mots, mols, t)
verifier("un ARN sûr abîmé (deux mots) : réparé par ses témoins, l'ADNc de l'ARN intact, celui de la référence",
         r.returncode == 0 and "faux (réparé)" in r.stderr and octets("abime_sur_c.adn") == octets("chute_sur_c.adn")
         and octets("abime_sur_c.adn") == octets("abime_sur_cr.adn") and e == adn.FAUX, r.stderr)
abimer_arn("chute_sur.arn", "coiffe_sur.arn", [], coiffe=True)
r = lugus("retrotranscrire", "coiffe_sur.arn", "coiffe_sur_c.adn")
verifier("un ARN sûr à la coiffe abîmée : les témoins reconnaissent les mots, la coiffe est refaite",
         r.returncode == 0 and "la coiffe : faux" in r.stderr and octets("coiffe_sur_c.adn") == octets("chute_sur_c.adn"),
         r.stderr)
abimer_arn("chute_rapide.arn", "abime_rapide.arn", [4])
r = lugus("retrotranscrire", "abime_rapide.arn", "abime_rapide_c.adn")
e, _, _, _ = adn.adnc(os.path.join(d, "abime_rapide.arn"))
verifier("un ARN rapide abîmé : sa coiffe ne reconnaît pas ses mots, sans témoins rien ne tranche (variable, rien n'est écrit)",
         r.returncode != 0 and "variable" not in r.stdout and e == adn.VARIABLE
         and not os.path.exists(os.path.join(d, "abime_rapide_c.adn")), r.stderr)

# le texte gardé vérifié en vtx sur un long texte qui importe une bibliothèque (plus de 4096 caractères : le service 27
# prend le texte entier, pas un nom de fichier)
os.makedirs(os.path.join(d, "ex"), exist_ok=True)
shutil.copy(os.path.join(racine, "exemples128", "codon.vtx"), os.path.join(d, "ex"))
shutil.copytree(os.path.join(racine, "bibliotheque"), os.path.join(d, "bibliotheque"))
lugus("ranger", os.path.join("ex", "codon.vtx"))
r = lugus("transcrire", os.path.join("ex", "codon.adn"), os.path.join("ex", "codon.arn"), "--isoforme", "sur")
verifier("le texte gardé d'un long programme qui importe une bibliothèque, vérifié en vtx : vrai",
         "le texte : vrai" in r.stderr, r.stderr)

shutil.rmtree(d, ignore_errors=True)
print("le chemin dans les deux sens : " + ("tout est conforme" if echecs == 0 else f"{echecs} écart(s)"))
sys.exit(1 if echecs else 0)
