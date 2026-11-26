"""0.846 : le Druide conseiller (druide/conseiller.vtx) : les mêmes mots par vtx128.py et vtxc128 ; les mots embarqués
dans Lugus (vtx-rs/druide_conseiller.mots) sont ceux du texte ; « lugus druide » dit les six conseils attendus de
tests/druide/conseils.vtx, dans l'ordre des lignes, et ce que Gutuater a appris (le nemeton)."""
import os, subprocess, sys, tempfile
ICI = os.path.dirname(os.path.abspath(__file__))
R = os.path.dirname(ICI)
sys.path.insert(0, R)
import vtx128  # noqa: E402
LUGUS = os.path.join(R, "vtx-rs", "target", "release", "lugus")
ok = True


def dire(nom, bon, detail=""):
    global ok
    ok &= bon
    print(("OK   " if bon else "ÉCHEC ") + nom + ("" if bon else " : " + str(detail)[:400]))


src = os.path.join(R, "druide", "conseiller.vtx")
m, _ = vtx128.assembler(vtx128.compiler(open(src, encoding="utf-8").read(), dossier=os.path.dirname(src)), True)
with tempfile.TemporaryDirectory() as d:
    f = os.path.join(d, "c.mots")
    subprocess.run([LUGUS, "compiler", src, f], capture_output=True, text=True)
    ml = [int(x) for x in open(f).read().split(";")[0].split(",") if x.strip()]
    dire(f"les mêmes mots par les deux compilateurs ({len(ml)} mots)", m == ml)
    emb = [int(x) for x in open(os.path.join(R, "vtx-rs", "druide_conseiller.mots")).read().split(";")[0].split(",") if x.strip()]
    dire("les mots embarqués sont ceux du texte (outils/druide.sh)", emb == ml)
    nem = os.path.join(d, "nemeton", "conseils")
    os.makedirs(nem)
    open(os.path.join(nem, "gutuater.arn"), "w").write("carte_directe 0 vrai\n")
    r = subprocess.run([LUGUS, "druide", os.path.join(ICI, "druide", "conseils.vtx")], capture_output=True, text=True,
                       env=dict(os.environ, VTX_NEMETON=os.path.join(d, "nemeton")))
    t = r.stdout
    attendus = ["ligne 3 (sûr) : la constante « VIDE » est déjà définie à la ligne 2",
                "ligne 6 (à vérifier) : ce « selon » ne dit rien pour inconnu",
                "la potion : inconnu { } variable { }",
                "ligne 13 (sûr) : sur Lugus, « entier_64 » compte en 128 bits",
                "ligne 14 (sûr) : une adresse du cube écrite à la main",
                "la potion : cube cube_49 @2 frequence 49;",
                "ligne 15 (sûr) : une famille de cubes écrite à la main",
                "ligne 17 (selon le cas) : « si … == vrai »",
                "Gutuater : la carte directe (le monde d'un seul tenant au processeur) : vrai"]
    for a in attendus:
        dire("le Druide dit : " + a, a in t, t)
    places = [t.find("ligne " + str(n) + " (") for n in (3, 6, 13, 14, 15, 17)]
    dire("dans l'ordre des lignes", all(p >= 0 for p in places) and places == sorted(places), places)
print("Le Druide conseiller : tout est conforme" if ok else "Le Druide conseiller : des écarts")
sys.exit(0 if ok else 1)
