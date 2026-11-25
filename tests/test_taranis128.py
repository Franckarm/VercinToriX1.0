"""0.836 : la frontière de Taranis. Taranis compte en 64 bits ; un programme Lugus (128 bits) reste au processeur,
même avec VTX_CARTE=1, et donne la sortie de Lugus (les bits au-delà de 64 gardés). Le même en « dunon; » peut aller
à la carte et donne la sortie de Lugus en Dunon."""
import os, subprocess, sys, tempfile
ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(ICI)
LUGUS = os.path.join(RACINE, "vtx-rs", "target", "release", "lugus")
ok = True
src = os.path.join(ICI, "taranis128.vtx")
with tempfile.TemporaryDirectory() as d:
    texte = open(src, encoding="utf-8").read()
    dun = os.path.join(d, "dunon.vtx")
    open(dun, "w", encoding="utf-8").write("dunon;\n" + texte.replace("(i << 70)", "(i << 40)"))
    for nom, p in (("Lugus (128)", src), ("Dunon (64)", dun)):
        attendu = subprocess.run([LUGUS, p], capture_output=True, text=True).stdout
        env = dict(os.environ, VTX_CARTE="1")
        exe = os.path.join(d, "prog")
        f = subprocess.run([sys.executable, os.path.join(RACINE, "forge", "forge128.py"), p, "-o", exe],
                           capture_output=True, text=True, env=env)
        sortie = subprocess.run([exe], capture_output=True, text=True, env=env).stdout
        alla = "taranis :" in f.stderr
        bon = sortie == attendu and (nom.startswith("Dunon") or not alla)
        ok &= bon
        print("OK  " if bon else "ÉCHEC", nom, ": la sortie de Lugus" + ("" if not alla else " (la carte)"),
              "" if bon else repr((sortie, attendu, f.stderr[-300:])))
# 0.840 : le noyau de la carte doit savoir les mots du prélude qui dépendent de la largeur (nb_bits : 64 sur la carte) :
# une boucle qui appelle racine_entiere va à la carte (la 0.840 l'avait refusée : Gergovie sur la carte à 5,8 images
# par seconde au lieu de 57)
sys.path.insert(0, os.path.join(RACINE, "forge"))
sys.path.insert(0, os.path.join(RACINE, "taranis"))
import forge128, noyau_vtx  # noqa: E402
os.environ["VTX_CARTE"] = "1"
os.environ["VTX_EPISSAGE"] = "rapide"
pris, refus = [0], []


def enrober(cls):
    orig = cls.compiler

    def compter(self):
        try:
            r = orig(self)
            pris[0] += 1
            return r
        except noyau_vtx.PasPourLaCarte as e:
            refus.append(str(e))
            raise
    cls.compiler = compter


for cls in (noyau_vtx.Noyau, noyau_vtx.NoyauI64, noyau_vtx.NoyauTaranis):
    enrober(cls)
with tempfile.TemporaryDirectory() as d:
    for nomg in ("gergovie_carte", "gergovie_carte_eventail"):
        g = os.path.join(RACINE, "belenos", nomg + ".vtx")
        forge128.source_rust(open(g, encoding="utf-8").read(), os.path.dirname(g), nomg, os.path.join(d, nomg))
bon = pris[0] > 0 and not any("nb_bits" in r for r in refus)
ok &= bon
print("OK  " if bon else "ÉCHEC", "Gergovie sur la carte (le témoin et l'éventail) : ses noyaux compilés, aucun refusé pour nb_bits", "" if bon else refus[:3])
print("Taranis et le 128 : tout est conforme" if ok else "Taranis et le 128 : des écarts")
sys.exit(0 if ok else 1)
