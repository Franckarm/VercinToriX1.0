#!/usr/bin/env python3
"""Les tableaux dynamiques de logiques de Lugus, logique[] (0.6) : un tableau qui grandit et dont chaque case porte une
des quatre valeurs ; il se déclare (soit t: logique[] = [vrai, inconnu]), se reconnaît à ses valeurs écrites
([faux, variable]), se passe à une fonction et en revient, se lit (t[i], pour x dans t), s'écrit, s'allonge (ajouter,
inserer), se raccourcit (retirer, enlever), se cherche (indice, contient), se copie. Mêmes mots par vtx128.py et
vtxc128 ; chaque cas comme attendu ; exemples128/conseil.vtx traduit en x86-64 comme joué par Lugus seul."""
import os
import subprocess
import sys
import tempfile

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, racine)
import vtx128  # noqa: E402

X = ".exe" if os.name == "nt" else ""
BIN = os.path.join(racine, "vtx-rs", "target", "release")
d = tempfile.mkdtemp()
echecs = 0


def verifier(nom, ok, detail=""):
    global echecs
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok else f" : {detail}"), flush=True)
    echecs += 0 if ok else 1


def memes_mots(fic):
    src = open(fic, encoding="utf-8").read()
    ref = vtx128.assembler(vtx128.compiler(src, dossier=os.path.dirname(fic)))
    sortie = os.path.join(d, os.path.basename(fic) + ".mots")
    r = subprocess.run([os.path.join(BIN, "lugus" + X), "compiler", fic, sortie], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    m = [int(x) for x in open(sortie).read().split(";")[0].split(",") if x.strip()] if r.returncode == 0 else None
    return m == ref, f"{len(ref)} contre {None if m is None else len(m)} {r.stdout[-200:]} {r.stderr[-200:]}"


def exe(fic, interprete=False):
    e = os.path.join(d, os.path.splitext(os.path.basename(fic))[0] + X)
    if not os.path.exists(e):
        subprocess.run([os.path.join(BIN, "vtx" + X), "exe128", fic, e], capture_output=True)
    env = dict(os.environ, VTX_SANS_PAUSE="1", VTX_CONSOLE="1")
    env.pop("VTX_INTERPRETE", None)
    if interprete:
        env["VTX_INTERPRETE"] = "1"
    return subprocess.run([e], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=d, env=env,
                          timeout=120).stdout


cas = os.path.join(d, "cas.vtx")
open(cas, "w", encoding="utf-8").write("""// machine : lugus
fonction neuf(n): logique[] {
    soit t: logique[] = [inconnu];
    pour i dans 1..n { ajouter(t, comme_logique(i % 4)); }
    retour t;
}
fonction rassembler(t: logique[]): logique {
    soit a: logique = inconnu;
    pour x dans t { a = fusion(a, x); }
    retour a;
}
fonction renverser(t: logique[]) {
    pour i dans 0..longueur(t) { t[i] = non4(t[i]); }
}
fonction principal() {
    soit t: logique[] = [vrai, inconnu, faux];
    afficher(t[0], t[1], t[2], longueur(t));
    ajouter(t, variable);
    inserer(t, 0, faux);
    afficher(t[0], t[1], t[2], t[3], t[4], longueur(t));
    t[2] = fusion(t[2], vrai);
    t[1] = et4(t[1], t[0]);
    afficher(t[1], t[2], indice(t, variable), contient(t, inconnu), contient(t, vrai));
    afficher(retirer(t), enlever(t, 0), longueur(t), t[0], t[1], t[2]);
    soit u = [faux, variable];
    afficher(u[0], u[1], rassembler(u), rassembler([vrai, vrai]), rassembler([inconnu]));
    soit n = neuf(6);
    afficher(n[0], n[1], n[2], n[3], n[4], n[5], rassembler(n));
    soit c = copie(n);
    renverser(c);
    afficher(c[1], c[2], c[3], n[1], n[2], n[3]);
    soit vrais = 0;
    pour x dans n {
        selon x {
            vrai { vrais = vrais + 1; }
            faux { vrais = vrais + 10; }
            inconnu { vrais = vrais + 100; }
            variable { vrais = vrais + 1000; }
        }
    }
    afficher(vrais);
}
""")
ok, detail = memes_mots(cas)
verifier("vtx128.py et vtxc128 donnent les mêmes mots (les cas)", ok, detail)
o = exe(cas).splitlines()
attendu = ["vrai inconnu faux 3",
           "faux vrai inconnu faux variable 5",
           "faux vrai 4 0 1",
           "variable faux 3 faux vrai faux",
           "faux variable variable vrai inconnu",
           "inconnu faux vrai variable inconnu faux variable",
           "vrai faux variable faux vrai variable",
           "1221"]
noms = ["déclaré et lu : soit t: logique[] = [vrai, inconnu, faux]", "ajouter et inserer",
        "écrire une case (fusion, et4), indice et contient", "retirer et enlever",
        "reconnu à ses valeurs écrites ([faux, variable]) et passé à une fonction", "rendu par une fonction (: logique[])",
        "copie puis non4 sur chaque case : l'original ne change pas", "pour x dans t, avec selon sur les quatre valeurs"]
for i, (n, a) in enumerate(zip(noms, attendu)):
    verifier(n, i < len(o) and o[i] == a, f"{o[i] if i < len(o) else None!r} attendu {a!r}")
verifier("les cas : traduits en x86-64 comme joués par Lugus seul", exe(cas) == exe(cas, True), "")

demo = os.path.join(racine, "exemples128", "conseil.vtx")
ok, detail = memes_mots(demo)
verifier("conseil.vtx : mêmes mots par les deux compilateurs", ok, detail)
a, b = exe(demo), exe(demo, True)
verifier("conseil.vtx : le matin, le soir, les paroles rassemblées ; traduit = Lugus seul",
         a == b and "après le matin  : vrai faux inconnu variable inconnu" in a
         and "le soir         : vrai faux vrai variable inconnu vrai" in a
         and "question 3, les trois paroles rassemblées : variable" in a and "sans la dernière (faux) : vrai ; il en reste 2" in a
         and "la mémoire du conseil garde : variable" in a, a[-600:])
print("les tableaux de logiques : " + ("tout est conforme" if echecs == 0 else f"{echecs} échec(s)"))
sys.exit(1 if echecs else 0)
