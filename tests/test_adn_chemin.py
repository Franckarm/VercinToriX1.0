#!/usr/bin/env python3
"""Le chemin de l'ADN en vtx (0.6n) : ranger, relire, transcrire et écrire l'ARN sont faits par le lecteur d'ADN écrit
en vtx (chimie/adn.vtx, embarqué dans lugus) ; Lugus ne fait que compiler (par vtxc128, en vtx lui aussi) et passer
les fichiers. Vérifié contre la référence chimie/adn.py, octet pour octet : l'ADN rangé (un programme avec un isotope
lourd, un texte en \\r\\n et accentué), l'ADN réparé après des avaries, les mots transcrits ; les quatre isoformes de
l'ARN (leur coiffe reconnue, l'ARN lancé par Lugus donne la sortie du programme) ; l'épigénome gardé dans l'ARN
« memoire » ; l'intron « compilateur » : un texte retouché est faux, un compilateur changé rend la rétrotranscription
inconnue."""
import os
import random
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
PY = [sys.executable, os.path.join(racine, "chimie", "adn.py")]
ENV = dict(os.environ, PYTHONIOENCODING="utf-8")
d = tempfile.mkdtemp()
echecs = 0


def verifier(nom, ok, detail=""):
    global echecs
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok else f" : {detail}"), flush=True)
    echecs += 0 if ok else 1


def lugus(*args, entree=None):
    return subprocess.run([LUGUS, *args], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=d,
                          input=entree, timeout=600)


def py(*args):
    return subprocess.run(PY + list(args), capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=d,
                          env=ENV, timeout=600)


def octets(f):
    return open(f, "rb").read()


ISO = """// machine : lugus
// l'isotope lourd et les accents : « é », « œ » ; ce texte est en \\r\\n
reaction freinage(v: flottant, d: flottant) -> a: flottant {
    = v * v / (2.0 * d)   -> a lourd
}
fonction principal() {
    afficher(freinage(30.0, 45.0));
    sortie(7);
}
"""
progs = {}
for nom in ("panel.vtx", "chute.vtx", "bonjour128.vtx"):
    shutil.copy(os.path.join(racine, "exemples128", nom), os.path.join(d, nom))
    progs[nom] = os.path.join(d, nom)
with open(os.path.join(d, "iso.vtx"), "w", encoding="utf-8", newline="\r\n") as f:
    f.write(ISO)
progs["iso.vtx"] = os.path.join(d, "iso.vtx")

# 1. ranger : l'ADN de vtx est celui de Python, octet pour octet
for nom, f in progs.items():
    a_v, a_p = f[:-4] + "_vtx.adn", f[:-4] + "_py.adn"
    r = lugus("ranger", f, a_v)
    py("ranger", f, a_p)
    ok = os.path.exists(a_v) and os.path.exists(a_p) and octets(a_v) == octets(a_p)
    verifier(f"ranger {nom} en vtx : le même ADN que Python, octet pour octet", ok, r.stdout + r.stderr)
texte_iso = octets(progs["iso.vtx"][:-4] + "_vtx.adn").decode("utf-8")
verifier("l'ADN d'iso.vtx : l'intron des isotopes, le texte (accents, \\r\\n rendus en \\n), la signature du compilateur",
         "GU isotopes 1\nfreinage|" in texte_iso and "« é », « œ »" in texte_iso and "\r" not in texte_iso
         and f"GU compilateur 1\n{adn.signature_compilateur()}\nAG\n" in texte_iso)

# 2. abîmer, puis transcrire en vtx : les mots d'origine, l'ADN réparé réécrit comme Python le réécrit
for nom in ("chute.vtx", "bonjour128.vtx"):
    base = progs[nom][:-4]
    mots0, _, _ = adn.lire_adn(base + "_py.adn")
    shutil.copy(base + "_py.adn", base + "_a.adn")
    py("abimer", base + "_a.adn", "3", "7")
    shutil.copy(base + "_a.adn", base + "_b.adn")
    r = lugus("transcrire", base + "_a.adn", base + "_a.mots")
    py("transcrire", base + "_b.adn", base + "_b.mots")
    mots_v = [int(x) for x in open(base + "_a.mots").read().split(";")[0].split(",") if x]
    verifier(f"{nom} : trois mots abîmés, transcrit en vtx : les mots d'origine, l'ADN réparé comme celui de Python",
             mots_v == mots0 and octets(base + "_a.adn") == octets(base + "_b.adn")
             and octets(base + "_a.mots") == octets(base + "_b.mots") and "le texte : vrai" in r.stderr,
             r.stderr[-400:])

# 3. l'ARN et ses quatre isoformes : écrit en vtx, sa coiffe reconnue par Lugus, lancé il donne la sortie du programme
base = progs["chute.vtx"][:-4]
attendu = lugus(progs["chute.vtx"]).stdout
mots, mols, t = adn.lire_adn(base + "_py.adn")


def arn_attendu(iso):
    s = ["VTXARN02", "GU coiffe 1", f"{adn.signature(mots)}|{iso}", "AG", "GU mots 1", ",".join(map(str, mots)), "AG"]
    if iso in ("sur", "complet"):
        lm = [f"m{m.debut}|{m.debut}|{m.fin}|{int(m.frontiere)}|{sg}|{int(m.isotope)}" for m, sg in zip(mols, t["signatures"])]
        s += ["GU molecules %d" % len(lm)] + lm + ["AG"]
        s += ["GU ombres %d" % len(t["ombres"])] + [",".join(map(str, o)) for o in t["ombres"]] + ["AG"]
        s += ["GU neutrons 1", ",".join(f"{i}:{v}" for i, v in sorted(t["neutrons"].items())), "AG"]
    return "\n".join(s) + "\n"


for iso in ("rapide", "sur", "memoire", "complet"):
    f_arn = base + f"_{iso}.arn"
    r = lugus("transcrire", base + "_py.adn", f_arn, "--isoforme", iso)
    ecrit = open(f_arn, encoding="utf-8").read() if os.path.exists(f_arn) else ""
    joue = lugus(f_arn).stdout
    verifier(f"l'ARN « {iso} » écrit en vtx : le format de Lugus, sa coiffe reconnue, lancé il donne la sortie du "
             f"programme", ecrit == arn_attendu(iso) and joue == attendu, r.stderr[-300:] + joue[-200:])
r = lugus("transcrire", base + "_py.adn", base + "_x.arn", "--isoforme", "rien")
verifier("une isoforme inconnue est refusée", "isoforme inconnue" in r.stderr + r.stdout and not os.path.exists(base + "_x.arn"))

# 4. l'épigénome : appris par Lugus, gardé dans l'ARN « memoire » écrit en vtx, et l'ARN lancé reprend ses souvenirs
alt = os.path.join(d, "alternance.vtx")
shutil.copy(os.path.join(racine, "exemples128", "alternance.vtx"), alt)
lugus("ranger", alt)
lugus("apprendre", os.path.join(d, "alternance.adn"))
r = lugus("transcrire", os.path.join(d, "alternance.adn"), os.path.join(d, "alternance.arn"), "--isoforme", "memoire")
t_arn = open(os.path.join(d, "alternance.arn"), encoding="utf-8").read() if os.path.exists(os.path.join(d, "alternance.arn")) else ""
_, _, t_alt = adn.lire_adn(os.path.join(d, "alternance.adn"))
epi = adn.intron(t_alt, "epigenome")
verifier("l'épigénome (les souvenirs appris) est recopié dans l'ARN « memoire » écrit en vtx, ligne pour ligne",
         epi is not None and ("GU epigenome %d\n" % len(epi) + "\n".join(epi) + "\nAG\n") in t_arn, r.stderr[-300:])

# 5. la rétrotranscription et l'intron « compilateur »
f_iso_adn = progs["iso.vtx"][:-4] + "_vtx.adn"
texte = open(f_iso_adn, encoding="utf-8").read()
retouche = os.path.join(d, "retouche.adn")
open(retouche, "w", encoding="utf-8", newline="\n").write(texte.replace("2.0 * d", "2.5 * d"))
r1 = lugus("transcrire", f_iso_adn, os.path.join(d, "i1.mots"))
r2 = lugus("transcrire", retouche, os.path.join(d, "i2.mots"))
autre = os.path.join(d, "autre_compilateur.adn")
open(autre, "w", encoding="utf-8", newline="\n").write(
    texte.replace("2.0 * d", "2.5 * d").replace(f"GU compilateur 1\n{adn.signature_compilateur()}\n", "GU compilateur 1\n12345\n"))
r3 = lugus("transcrire", autre, os.path.join(d, "i3.mots"))
ancien = os.path.join(d, "ancien.adn")
open(ancien, "w", encoding="utf-8", newline="\n").write(
    texte.replace("2.0 * d", "2.5 * d").replace(f"GU compilateur 1\n{adn.signature_compilateur()}\nAG\n", ""))
r4 = lugus("transcrire", ancien, os.path.join(d, "i4.mots"))
verifier("rétrotranscription : le texte gardé redonne les mots (vrai) ; retouché (faux) ; retouché sous un autre "
         "compilateur (inconnu : on ne peut pas savoir) ; un ADN d'avant l'intron (faux, avec une réserve)",
         "le texte : vrai" in r1.stderr and "le texte : faux" in r2.stderr
         and "le texte : inconnu, le compilateur a changé" in r3.stderr
         and "le texte : faux" in r4.stderr and "ne note pas son compilateur" in r4.stderr,
         r1.stderr[-150:] + r2.stderr[-150:] + r3.stderr[-150:] + r4.stderr[-150:])
e_p, q_p = adn.retrotranscrire(*[adn.lire_adn(autre)[i] for i in (0, 2)], d)
verifier("la référence Python dit la même chose (inconnu)", e_p == adn.INCONNU, q_p)

# 6. relire (le lecteur en vtx, comme avant) : un ADN abîmé est relu et réparé
r = lugus("relire", base + "_a.adn", os.path.join(d, "relu.adn"))
verifier("lugus relire : l'ADN est relu en vtx", r.returncode == 0 and "l'ADN : " in r.stderr, r.stderr[-200:])
print("le chemin de l'ADN en vtx : " + ("tout est conforme" if echecs == 0 else f"{echecs} échec(s)"))
sys.exit(1 if echecs else 0)
