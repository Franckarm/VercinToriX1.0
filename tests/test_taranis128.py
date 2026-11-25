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
print("Taranis et le 128 : tout est conforme" if ok else "Taranis et le 128 : des écarts")
sys.exit(0 if ok else 1)
