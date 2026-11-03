#!/usr/bin/env python3
"""La patrouille, l'apoptose et l'épissage alternatif (docs/vtx-reactions.md, « L'ADN vivant ») : pendant que Lugus
fait tourner un ADN, la patrouille relit le code contre ses témoins et le répare ; un isotope lourd (« -> a lourd »)
est relu à chaque entrée et à chaque sortie : abîmé entre deux appels, il est réparé avant de servir ; abîmé pendant
qu'il sert, la machine s'arrête (l'apoptose) plutôt que de rendre un résultat qui n'est pas sûr. Un ARN porte une
coiffe (vérifiée). La patrouille est éteinte par défaut : elle veille avec --veille, ou quand le programme a des
isotopes lourds. Les avaries sont posées pendant l'exécution (LUGUS_AVARIE=PAS:MOT:BIT).

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

def faussent(f_prog, places, bits, pas, n=3):
    """des avaries qui faussent vraiment le résultat de f_prog (l'ARN rapide : sans témoins, sans patrouille) ; le
    critère ne dit rien de la patrouille, et ne dépend pas de la place exacte du code (qui change avec le compilateur)"""
    out = []
    for place in places:
        for bit in bits:
            av = f"{pas}:{place}:{bit}"
            if lancer(f_prog, av)[1] != JUSTE:
                out.append(av)
                break
        if len(out) >= n:
            break
    return out


# 2-3. l'isotope lourd abîmé, à chaque pas d'une fenêtre (entre deux appels ou pendant qu'il sert) : la machine ne rend
#      jamais un résultat faux ; réparé à son entrée (il n'a pas servi abîmé), ou l'apoptose (rien n'est rendu)
mots_lourds = faussent(f_rapide, range(lourde.debut + 2, lourde.fin), (100, 70, 9), 1000000, n=2)
issues = {"entree": 0, "apoptose": 0, "travers": []}
for av in mots_lourds:
    _, place, bit = av.split(":")
    for pas in range(1000000, 1000060):
        c, s, e = lancer(f_adn, f"{pas}:{place}:{bit}")
        if c == 0 and s == JUSTE and "isotope lourd, relu à son entrée : il n'a pas servi abîmé" in e:
            issues["entree"] += 1
        elif c != 0 and s == "" and "apoptose" in e and "s'est abîmée pendant qu'elle servait" in e:
            issues["apoptose"] += 1
        elif s != JUSTE:
            issues["travers"].append(f"{pas}:{place}:{bit} -> {s!r} {e[-120:]!r}")
verifier(f"l'isotope abîmé à chaque pas d'une fenêtre ({len(mots_lourds)} avaries qui faussent l'ARN rapide, 60 pas) : "
         f"jamais de résultat faux ; réparé à son entrée {issues['entree']} fois, l'apoptose {issues['apoptose']} fois",
         len(mots_lourds) == 2 and not issues["travers"] and issues["entree"] > 0 and issues["apoptose"] > 0,
         str(issues["travers"][:3]))

# 4. une molécule froide (bilan, appelée à la fin) abîmée : la patrouille la répare en passant, et dit depuis quand
#    elle a pu servir abîmée
froides = faussent(f_rapide, range(froide.debut + 1, froide.fin), (70, 40, 100, 6), 100000, n=3)
for av in froides:
    c, s, e = lancer(f_adn, av)
    verifier(f"une molécule froide abîmée ({av}) : réparée par la patrouille, le résultat juste",
             c == 0 and s == JUSTE and f"m{froide.debut} faux (réparé)" in e and "a pu servir abîmée" in e, s + " / " + e)
av_froide = froides[0] if froides else f"100000:{froide.debut + 4}:70"
c2, s2, _ = lancer(f_adn, av_froide, LUGUS_PATROUILLE="0")
verifier(f"trois avaries de la molécule froide qui faussent l'ARN rapide ; la même avarie sans patrouille "
         f"(LUGUS_PATROUILLE=0) : le résultat est faux", len(froides) == 3 and s2 != JUSTE, f"{froides} {s2}")

# 5. au-delà des témoins : l'apoptose
avaries = ",".join(f"100000:{i}:{b}" for i in range(froide.debut, froide.debut + 9) for b in (3, 70))
c, s, e = lancer(f_adn, avaries)
verifier("neuf mots voisins abîmés (au-delà de l'ombre) : l'apoptose, aucun résultat rendu",
         c != 0 and "apoptose" in e and s == "", s + " / " + e)

# 6. l'ARN sûr (les témoins gardés) : la patrouille veille aussi
f_sur = os.path.join(d, "pat.arn")
subprocess.run([lugus, "transcrire", f_adn, f_sur, "--isoforme", "sur"], capture_output=True, text=True,
               encoding="utf-8")
c, s, e = lancer(f_sur, av_froide)
verifier("l'ARN sûr : la patrouille répare comme depuis l'ADN", c == 0 and s == JUSTE and "réparé" in e, s + " / " + e)

# 7. un ARN ancien qui porte encore une queue (la section est sautée) : il est lancé comme les autres
texte = open(f_sur, encoding="utf-8").read()
ancien = texte.replace("AG\nGU mots", "AG\nGU queue 1\n7\nAG\nGU mots", 1)
f_ancien = os.path.join(d, "ancien.arn")
open(f_ancien, "w", encoding="utf-8", newline="\n").write(ancien)
c, s, e = lancer(f_ancien)
verifier("un ARN ancien avec sa queue : la section est sautée, il est lancé, le fichier n'est pas réécrit",
         c == 0 and s == JUSTE and "GU queue" in ancien and open(f_ancien, encoding="utf-8").read() == ancien, s + " / " + e)

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

# 10. sans isotope lourd, la patrouille est éteinte par défaut : --veille (ou LUGUS_PATROUILLE=1) l'arme
SANS = PROG.replace("-> a lourd", "-> a")
f_v = os.path.join(d, "sans.vtx")
open(f_v, "w", encoding="utf-8", newline="\n").write(SANS)
f_sans = os.path.join(d, "sans.adn")
subprocess.run([lugus, "ranger", f_v, f_sans], capture_output=True)
_, mols2, _ = adn.lire_adn(f_sans)
froide2 = next(m for m in mols2 if m.debut == froide.debut)
# une avarie qui fausse vraiment le résultat sans patrouille (cherchée dans la molécule : le code change avec le
# compilateur, une place fixe peut tomber sur un bit sans effet)
av, c, s, e = None, 0, JUSTE, ""
for place in range(froide2.debut + 1, froide2.fin):
    for bit in (70, 40, 100, 6):
        av_k = f"100000:{place}:{bit}"
        c, s, e = lancer(f_sans, av_k)
        if s != JUSTE:
            av = av_k
            break
    if av:
        break
av = av or f"100000:{froide2.debut + 4}:70"

r = subprocess.run([lugus, f_sans, "--veille"], capture_output=True, text=True, encoding="utf-8",
                   env=dict(os.environ, LUGUS_AVARIE=av))
c3, s3, e3 = lancer(f_sans, av, LUGUS_PATROUILLE="1")
c4, s4, e4 = lancer(f_adn, av_froide, LUGUS_PATROUILLE="0")
verifier("sans isotope lourd : pas de patrouille par défaut (le résultat est faux), --veille ou LUGUS_PATROUILLE=1 "
         "la rendent (réparé, juste) ; LUGUS_PATROUILLE=0 l'éteint même avec un isotope",
         s != JUSTE and "patrouille" not in e and r.stdout.strip() == JUSTE and "réparé" in r.stderr
         and s3 == JUSTE and s4 != JUSTE, f"{s} / {r.stdout} {r.stderr} / {s3} / {s4}")
c, s, e = lancer(f_sans, LUGUS_TEMPS="1")
verifier("sans avarie ni isotope : le résultat juste, la patrouille absente du rapport",
         c == 0 and s == JUSTE and "patrouille" not in e, s + " / " + e)

print("patrouille : " + ("tout est conforme" if not echecs else f"{len(echecs)} échec(s)"))
sys.exit(1 if echecs else 0)
