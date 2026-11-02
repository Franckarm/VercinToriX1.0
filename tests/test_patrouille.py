#!/usr/bin/env python3
"""La patrouille, l'apoptose et l'épissage alternatif (docs/vtx-reactions.md, « L'ADN vivant ») : pendant que Lugus
fait tourner un ADN, la patrouille relit le code contre ses témoins et le répare ; un isotope lourd (« -> a lourd »)
est relu à chaque entrée et à chaque sortie : abîmé entre deux appels, il est réparé avant de servir ; abîmé pendant
qu'il sert, la machine s'arrête (l'apoptose) plutôt que de rendre un résultat qui n'est pas sûr. Un ARN porte une
coiffe (vérifiée) et une queue (usée, il est refait depuis l'ADN). Les avaries sont posées pendant l'exécution
(LUGUS_AVARIE=PAS:MOT:BIT).

    python3 tests/test_patrouille.py"""
import os
import subprocess
import sys
import tempfile

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, os.path.join(racine, "chimie"))
import adn  # noqa: E402

echecs = []
lugus = os.path.join(racine, "vtx-rs", "target", "release", "lugus" + (".exe" if os.name == "nt" else ""))


def verifier(nom, ok, detail=""):
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok or not detail else " : " + detail), flush=True)
    if not ok:
        echecs.append(nom)


def lancer(chemin, avarie=None, **env):
    e = dict(os.environ, **env)
    e.pop("LUGUS_AVARIE", None)
    if avarie:
        e["LUGUS_AVARIE"] = avarie
    r = subprocess.run([lugus, chemin], capture_output=True, text=True, encoding="utf-8", env=e)
    return r.returncode, r.stdout.strip(), r.stderr


if not os.path.exists(lugus):
    print("lugus n'est pas construit (cargo build --release dans vtx-rs) : rien n'est vérifié")
    sys.exit(1)

PROG = """// machine : lugus
reaction freinage(v: flottant, d: flottant) -> a: flottant {
    = v * v / (2.0 * d)   -> a lourd
}
fonction bilan(s: flottant): flottant {
    retour s / 1000.0 + 0.5;
}
fonction principal() {
    soit s = 0.0;
    pour k dans 0..40000 { s = s + freinage(flottant(k % 50), 45.0); }
    afficher(bilan(s));
}
"""
d = tempfile.mkdtemp(prefix="patrouille-")
f_vtx = os.path.join(d, "pat.vtx")
open(f_vtx, "w", encoding="utf-8", newline="\n").write(PROG)
f_adn = os.path.join(d, "pat.adn")
subprocess.run([lugus, "ranger", f_vtx, f_adn], capture_output=True, text=True, encoding="utf-8")
mots, mols, t = adn.lire_adn(f_adn)
lourde = next(m for m in mols if m.isotope)
froide = next(m for m in mols if m.debut == lourde.fin)          # la molécule qui suit (bilan, appelée à la fin)
JUSTE = "359.833333333333333333333333333401"
f_rapide = os.path.join(d, "pat.arn")
subprocess.run([lugus, "transcrire", f_adn, f_rapide, "--isoforme", "rapide"], capture_output=True, text=True, encoding="utf-8")

# 1. sans avarie : la patrouille ne change rien (ni le résultat, ni le nombre d'instructions)
c0, s0, e0 = lancer(f_adn, LUGUS_TEMPS="1")
c1, s1, e1 = lancer(f_adn, LUGUS_TEMPS="1", LUGUS_PATROUILLE="0")
n0 = next((l.split()[0] for l in e0.splitlines() if "instructions en" in l), "?")
n1 = next((l.split()[0] for l in e1.splitlines() if "instructions en" in l), "?")
verifier(f"sans avarie : le même résultat et les mêmes instructions ({n0}), avec ou sans patrouille, aucune réparation",
         c0 == c1 == 0 and s0 == s1 == JUSTE and n0 == n1 and "0 réparation(s)" in e0, e0 + e1)

# 2. l'isotope lourd abîmé entre deux appels (au pas d'un CALL) : réparé à son entrée, avant de servir
mot = lourde.debut + 12
c, s, e = lancer(f_adn, f"1000050:{mot}:100")
cr, sr, _ = lancer(f_rapide, f"1000050:{mot}:100")
verifier("l'isotope abîmé entre deux appels : réparé à son entrée, le résultat juste (l'ARN rapide, sans témoins, se trompe)",
         c == 0 and s == JUSTE and "isotope lourd, relu à son entrée : il n'a pas servi abîmé" in e and sr != JUSTE,
         f"{s} / {sr} / {e}")

# 3. l'isotope abîmé pendant qu'il sert : l'apoptose (rien n'est rendu de travers)
for pas, bit in ((1000001, 70), (1000001, 100), (1000020, 9)):
    c, s, e = lancer(f_adn, f"{pas}:{lourde.debut + 17}:{bit}")
    verifier(f"l'isotope abîmé pendant qu'il sert (pas {pas}, bit {bit}) : l'apoptose, aucun résultat rendu",
             c != 0 and "apoptose" in e and "s'est abîmée pendant qu'elle servait" in e and s == "", s + " / " + e)

# 4. une molécule froide (bilan, appelée à la fin) abîmée : la patrouille la répare en passant, et dit depuis quand
#    elle a pu servir abîmée
for k in (2, 4, 7):
    c, s, e = lancer(f_adn, f"100000:{froide.debut + k}:70")
    verifier(f"une molécule froide abîmée (mot {froide.debut + k}) : réparée par la patrouille, le résultat juste",
             c == 0 and s == JUSTE and f"m{froide.debut} faux (réparé)" in e and "a pu servir abîmée" in e, s + " / " + e)
c, s, _ = lancer(f_rapide, f"100000:{froide.debut + 4}:70")
c2, s2, _ = lancer(f_adn, f"100000:{froide.debut + 4}:70", LUGUS_PATROUILLE="0")
verifier("la même avarie sans patrouille (l'ARN rapide, ou LUGUS_PATROUILLE=0) : le résultat est faux",
         s != JUSTE and s2 != JUSTE, f"{s} {s2}")

# 5. au-delà des témoins : l'apoptose
avaries = ",".join(f"100000:{i}:{b}" for i in range(froide.debut, froide.debut + 9) for b in (3, 70))
c, s, e = lancer(f_adn, avaries)
verifier("neuf mots voisins abîmés (au-delà de l'ombre) : l'apoptose, aucun résultat rendu",
         c != 0 and "apoptose" in e and s == "", s + " / " + e)

# 6. l'ARN sûr (les témoins gardés) : la patrouille veille aussi
f_sur = os.path.join(d, "pat.arn")
subprocess.run([lugus, "transcrire", f_adn, f_sur, "--isoforme", "sur", "--queue", "2"], capture_output=True, text=True,
               encoding="utf-8")
c, s, e = lancer(f_sur, f"100000:{froide.debut + 4}:70")
verifier("l'ARN sûr : la patrouille répare comme depuis l'ADN", c == 0 and s == JUSTE and "réparé" in e, s + " / " + e)

# 7. la queue : deux lancements, puis l'ARN est refait depuis l'ADN (relu)
c, s, _ = lancer(f_sur)
c2, s2, e2 = lancer(f_sur)
q = adn.sections_adn(open(f_sur, encoding="utf-8").read())
queue = dict(q)["queue"][0]
verifier("la queue épuisée : l'ARN est refait depuis l'ADN (relu), avec une queue neuve",
         s == s2 == JUSTE and "l'ARN était usé : refait depuis" in e2 and queue == "63", f"{e2} queue {queue}")

# 8. la coiffe : un ARN dont les mots ne sont plus les siens n'est pas lancé
texte = open(f_sur, encoding="utf-8").read()
i = texte.index("GU mots 1\n") + len("GU mots 1\n")
j = texte.index(",", i)
abime = texte[:i] + str(int(texte[i:j]) ^ (1 << 40)) + texte[j:]
f_deg = os.path.join(d, "deg.arn")
open(f_deg, "w", encoding="utf-8", newline="\n").write(abime)
c, s, e = lancer(f_deg)
verifier("la coiffe ne reconnaît pas les mots : l'ARN dégradé n'est pas lancé", c != 0 and s == "" and "coiffe" in e, e)

# 9. l'ARN mémoire : l'épigénome voyage avec lui
f_alt = os.path.join(d, "alternance.adn")
subprocess.run([lugus, "ranger", os.path.join(racine, "exemples128", "alternance.vtx"), f_alt], capture_output=True)
subprocess.run([lugus, "apprendre", f_alt], capture_output=True)
f_mem = os.path.join(d, "alternance.arn")
subprocess.run([lugus, "transcrire", f_alt, f_mem, "--isoforme", "memoire"], capture_output=True)
c, s, e = lancer(f_mem, LUGUS_TEMPS="1")
f_rap2 = os.path.join(d, "alt-rapide.arn")
subprocess.run([lugus, "transcrire", f_alt, f_rap2], capture_output=True)
c2, s2, e2 = lancer(f_rap2, LUGUS_TEMPS="1")
n_mem = int(next((l.split()[0] for l in e.splitlines() if "instructions en" in l), "0"))
n_rap = int(next((l.split()[0] for l in e2.splitlines() if "instructions en" in l), "0"))
verifier(f"l'ARN mémoire reprend l'épigénome : {n_rap} -> {n_mem} instructions, le même résultat",
         s == s2 == "2640024" and 0 < n_mem * 20 < n_rap and "souvenirs repris" in e, f"{s} {s2} {e}")

print("patrouille : " + ("tout est conforme" if not echecs else f"{len(echecs)} échec(s)"))
sys.exit(1 if echecs else 0)
