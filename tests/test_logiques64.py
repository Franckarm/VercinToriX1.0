#!/usr/bin/env python3
"""Dunon, le SPU-64, fait le travail de Lugus (0.6h) : les tableaux dynamiques de logiques, logique[] (déclarés,
reconnus à leurs valeurs écrites, passés aux fonctions, allongés, raccourcis, cherchés, copiés) ; un tableau de textes
écrit dans une variable ; et les programmes de Lugus conseil.vtx et combat.vtx, qui écrivent sur Dunon exactement ce
qu'ils écrivent sur Lugus. Mêmes mots par vtx64.py et vtxc64."""
import os
import subprocess
import sys
import tempfile

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, racine)
import vtx64  # noqa: E402

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
    ref = vtx64.assembler(vtx64.compiler(src, dossier=os.path.dirname(fic)))
    sortie = os.path.join(d, os.path.basename(fic) + ".mots")
    r = subprocess.run([os.path.join(BIN, "vtx64" + X), "compiler", fic, sortie], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    m = [int(x) for x in open(sortie).read().split(";")[0].split(",") if x.strip()] if r.returncode == 0 else None
    return m == ref, f"{len(ref)} contre {None if m is None else len(m)} {r.stdout[-200:]} {r.stderr[-200:]}"


def exe(fic):
    return subprocess.run([os.path.join(BIN, "vtx64" + X), fic], capture_output=True, text=True, encoding="utf-8",
                          errors="replace", cwd=d, timeout=300).stdout


def sur_lugus(fic):
    return subprocess.run([os.path.join(BIN, "lugus" + X), fic], capture_output=True, text=True, encoding="utf-8",
                          errors="replace", cwd=d, timeout=300).stdout


cas = os.path.join(d, "cas.vtx")
open(cas, "w", encoding="utf-8").write("""// machine : dunon
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
verifier("vtx64.py et vtxc64 donnent les mêmes mots (les cas)", ok, detail)
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
verifier("les cas : Dunon écrit comme Lugus", exe(cas) == sur_lugus(cas) and len(exe(cas)) > 50, "")

textes = os.path.join(d, "textes.vtx")
open(textes, "w", encoding="utf-8").write("""fonction principal() {
    soit actions = ["attendre", "agir", "fuir"];
    soit p = [1, 0];
    afficher(actions[1], actions[p[1]]);
    soit i = 2;
    afficher(actions[i] + " !", actions[i] == "fuir", longueur(actions));
}
""")
ok, detail = memes_mots(textes)
verifier("un tableau de textes écrit dans une variable : mêmes mots par les deux compilateurs", ok, detail)
verifier("ses cases s'affichent, s'ajoutent et se comparent comme des textes",
         exe(textes) == "agir attendre\nfuir ! 1 3\n", repr(exe(textes)))
for nom, repere in (("conseil.vtx", "le soir         : vrai faux vrai variable inconnu vrai"),
                    ("combat.vtx", "Brennos : le codon et le hasard : gagnés 494 ; perdus 6")):
    prog = os.path.join(racine, "exemples128", nom)
    ok, detail = memes_mots(prog)
    verifier(f"{nom} (écrit pour Lugus) : mêmes mots par vtx64.py et vtxc64", ok, detail)
    a = exe(prog)
    verifier(f"{nom} : Dunon écrit exactement ce que Lugus écrit", a == sur_lugus(prog) and repere in a, a[-300:])
# instructions() sur Dunon (0.6i) : codon.vtx, qui mesure son coût, y compile ; tout est pareil sauf le compte lui-même
prog = os.path.join(racine, "exemples128", "codon.vtx")
ok, detail = memes_mots(prog)
verifier("codon.vtx (il mesure son coût par instructions()) : mêmes mots par vtx64.py et vtxc64", ok, detail)
a, b = exe(prog).splitlines(), sur_lugus(prog).splitlines()
verifier("codon.vtx : Dunon écrit ce que Lugus écrit, sauf la ligne du coût (71 instructions de Dunon, 63 de Lugus)",
         len(a) > 40 and a[:-1] == b[:-1] and a[-1].startswith("un tri de dossier : 71 instructions")
         and b[-1].startswith("un tri de dossier : 63 instructions") and a[-1].endswith("sommes 13152000 168000"), a[-1] if a else "")
print("Dunon fait le travail de Lugus : " + ("tout est conforme" if echecs == 0 else f"{echecs} échec(s)"))
sys.exit(1 if echecs else 0)
