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

# 5. l'ADN version 3 : des introns signalés (GU nom N … AG), les isotopes lourds, le texte et sa rétrotranscription
ISO = """// machine : lugus
reaction freinage(v: flottant, d: flottant) -> a: flottant {
    = v * v / (2.0 * d)   -> a lourd
}
reaction somme(n) -> s {
    = n * (n + 1) / 2 -> s
}
fonction principal() {
    afficher(freinage(30.0, 45.0));
    sortie(somme(10));
}
"""
f_iso = os.path.join(d, "iso.vtx")
open(f_iso, "w", encoding="utf-8", newline="\n").write(ISO)
mots_i, mols_i, t_i = adn.ranger_texte(ISO, d)
lourdes = [m for m in mols_i if m.isotope]
sans = adn.temoins(mots_i, adn.decouper(mots_i))
verifier("« -> a lourd » : la molécule de freinage est un isotope lourd, ses mots gardent leurs neutrons (hors frontière)",
         len(lourdes) == 1 and not lourdes[0].frontiere and all(i in t_i["neutrons"] for i in range(lourdes[0].debut, lourdes[0].fin))
         and not any(i in sans["neutrons"] for i in range(lourdes[0].debut, lourdes[0].fin)), str(mols_i[:4]))
import vtx128  # noqa: E402
vtx128.COMPAT_64 = False
m_sans = vtx128.assembler(vtx128.compiler(ISO.replace(" lourd", "")), True)[0]
verifier("l'isotope ne change pas le code : les mêmes mots avec ou sans « lourd »", m_sans == mots_i)
f_iso_adn = os.path.join(d, "iso.adn")
adn.ecrire_adn(f_iso_adn, mots_i, mols_i, t_i)
texte = open(f_iso_adn, encoding="utf-8").read()
noms_sec = [n for n, _ in adn.sections_adn(texte)]
verifier("le fichier : VTXADN03, chaque section entre GU et AG (mots, molecules, ombres, neutrons, isotopes, source)",
         texte.startswith("VTXADN03\n") and noms_sec == ["mots", "molecules", "ombres", "neutrons", "isotopes", "source"], str(noms_sec))
# une section inconnue (d'une version future) est sautée sans être analysée, et gardée telle quelle
t_x = adn.copie_temoins(t_i)
t_x["introns"].insert(0, ("avenir", ["GU faux 3", "AG", "n'importe quoi"]))
adn.ecrire_adn(f_iso_adn, mots_i, mols_i, t_x)
m2, mol2, t2 = adn.lire_adn(f_iso_adn)
verifier("un intron inconnu (même s'il contient « GU » et « AG ») est sauté et gardé tel quel",
         m2 == mots_i and t2["introns"][0] == ("avenir", ["GU faux 3", "AG", "n'importe quoi"]))
e_r, quoi_r = adn.retrotranscrire(mots_i, t_i, d)
t_f = adn.copie_temoins(t_i)
t_f["introns"] = [(n, [x.replace("2.0 * d", "2.5 * d") for x in l]) for n, l in t_f["introns"]]
e_f, quoi_f = adn.retrotranscrire(mots_i, t_f, d)
verifier("la rétrotranscription : le texte gardé redonne les mots (vrai) ; un texte retouché ne les redonne pas (faux)",
         e_r == adn.VRAI and e_f == adn.FAUX, quoi_r + " / " + quoi_f)
# l'ADN version 2 se lit toujours
f_v2 = os.path.join(d, "v2.adn")
with open(f_v2, "w", encoding="utf-8", newline="\n") as f:
    f.write("VTXADN02\n" + ",".join(map(str, mots_i)) + "\n"
            + "\t".join(f"m{m.debut}|{m.debut}|{m.fin}|{int(m.frontiere)}|{sg}" for m, sg in zip(mols_i, t_i["signatures"])) + "\n"
            + ";".join(",".join(map(str, o)) for o in t_i["ombres"]) + "\n"
            + ",".join(f"{i}:{v}" for i, v in sorted(sans["neutrons"].items())) + "\n")
m3, mol3, t3 = adn.lire_adn(f_v2)
e3, _ = adn.lire(m3, mol3, t3)
verifier("un ADN de la version 2 se lit encore (vrai)", m3 == mots_i and e3 == adn.VRAI)
if os.path.exists(lugus):
    f_rs = os.path.join(d, "iso-rs.adn")
    f_py = os.path.join(d, "iso-py.adn")
    subprocess.run([lugus, "ranger", f_iso, f_rs], capture_output=True, text=True, encoding="utf-8")
    subprocess.run(py + ["ranger", f_iso, f_py], capture_output=True, text=True, encoding="utf-8", env=ENV)
    verifier("Lugus range le même ADN version 3 que Python (isotopes et texte compris), octet pour octet",
             os.path.exists(f_rs) and open(f_rs, "rb").read() == open(f_py, "rb").read())
    r = subprocess.run([lugus, "transcrire", f_rs, os.path.join(d, "iso.mots")], capture_output=True, text=True, encoding="utf-8")
    verifier("lugus transcrire : « le texte : vrai » (rétrotranscription par vtxc128)",
             "le texte : vrai" in r.stderr, r.stderr)
    adn.ecrire_adn(f_rs, mots_i, mols_i, t_f)
    r = subprocess.run([lugus, "transcrire", f_rs, os.path.join(d, "iso.mots")], capture_output=True, text=True, encoding="utf-8")
    verifier("un texte retouché dans l'ADN : « le texte : faux », les mots restent ceux de l'ADN",
             "le texte : faux" in r.stderr and "l'ADN : vrai" in r.stderr, r.stderr)
    r = subprocess.run([lugus, "pourquoi", f_py, "s"], capture_output=True, text=True, encoding="utf-8")
    r2 = subprocess.run([lugus, "pourquoi", f_iso, "s"], capture_output=True, text=True, encoding="utf-8")
    verifier("lugus pourquoi PROG.adn : depuis le texte gardé, le même arbre que depuis PROG.vtx",
             r.returncode == 0 and r.stdout == r2.stdout and "s = 55" in r.stdout, r.stdout + r.stderr)
    r = subprocess.run([lugus, "pourquoi", f_rs, "s"], capture_output=True, text=True, encoding="utf-8")
    verifier("lugus pourquoi refuse un ADN dont le texte ne redonne pas les mots", r.returncode != 0 and "faux" in r.stderr,
             r.stderr)

# 6. l'épigénome : les souvenirs d'une exécution gardés dans l'ADN ; relancé, le programme repart avec ce qu'il a appris
if os.path.exists(lugus):
    f_alt = os.path.join(d, "alternance.adn")
    subprocess.run([lugus, "ranger", os.path.join(dex, "alternance.vtx"), f_alt], capture_output=True, text=True, encoding="utf-8")
    env_t = dict(os.environ, LUGUS_TEMPS="1")

    def lancer_adn(chemin):
        r = subprocess.run([lugus, chemin], capture_output=True, text=True, encoding="utf-8", env=env_t)
        n = next((int(l.split()[0]) for l in r.stderr.splitlines() if l.endswith(" s") and "instructions" in l), -1)
        return r.stdout.strip(), n, r.stderr

    s0, n0, _ = lancer_adn(f_alt)
    r = subprocess.run([lugus, "apprendre", f_alt], capture_output=True, text=True, encoding="utf-8")
    s1, n1, e1 = lancer_adn(f_alt)
    verifier(f"apprendre puis relancer : le même résultat, {n0} -> {n1} instructions (les souvenirs repris)",
             s0 == s1 == "2640024" and 0 < n1 * 20 < n0 and "souvenirs repris" in e1, f"{s0} {s1} {n0} {n1} {e1}")
    m_a, mol_a, t_a = adn.lire_adn(f_alt)
    epi = adn.intron(t_a, "epigenome")
    # un souvenir abîmé : l'épigénome est oublié, jamais lu de travers
    t_b = adn.copie_temoins(t_a)
    t_b["introns"] = [(n, ([x for x in l[:2]] + [l[2].split(":")[0] + ":" + str(int(l[2].split(":")[1]) + 1)] + l[3:])
                       if n == "epigenome" else l) for n, l in t_b["introns"]]
    f_b = os.path.join(d, "alternance-b.adn")
    adn.ecrire_adn(f_b, m_a, mol_a, t_b)
    s2, n2, e2 = lancer_adn(f_b)
    verifier("un souvenir abîmé dans l'épigénome : il est oublié (le même résultat, sans le raccourci)",
             s2 == s0 and n2 == n0 and "abîmé : oublié" in e2, f"{s2} {n2} {e2}")
    # l'épigénome d'un autre programme n'est pas repris
    f_c = os.path.join(d, "chute-epi.adn")
    subprocess.run([lugus, "ranger", os.path.join(dex, "chute.vtx"), f_c], capture_output=True, text=True, encoding="utf-8")
    m_c, mol_c, t_c = adn.lire_adn(f_c)
    t_c["introns"].append(("epigenome", epi))
    adn.ecrire_adn(f_c, m_c, mol_c, t_c)
    r = subprocess.run([lugus, f_c], capture_output=True, text=True, encoding="utf-8")
    verifier("l'épigénome d'un autre programme n'est pas repris", r.stdout.startswith("2500") and "autre programme" in r.stderr,
             r.stdout + r.stderr)
    # l'ADN abîmé, réparé : l'épigénome reste
    ab = list(m_a)
    ab[5] ^= 1 << 77
    adn.ecrire_adn(f_alt, ab, mol_a, t_a)
    s3, n3, e3 = lancer_adn(f_alt)
    verifier("un mot abîmé, réparé à la lecture : l'épigénome est gardé et repris", s3 == s0 and n3 == n1
             and adn.intron(adn.lire_adn(f_alt)[2], "epigenome") == epi, f"{s3} {n3} {e3}")
    subprocess.run([lugus, "oublier", f_alt], capture_output=True, text=True, encoding="utf-8")
    s4, n4, _ = lancer_adn(f_alt)
    verifier("oublier : l'épigénome retiré, le programme repart de rien", s4 == s0 and n4 == n0
             and adn.intron(adn.lire_adn(f_alt)[2], "epigenome") is None, f"{s4} {n4}")
print("ADN : " + ("tout est conforme" if not echecs else f"{len(echecs)} échec(s)"))
sys.exit(1 if echecs else 0)
