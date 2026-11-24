"""0.826 : le gène « fondre » (Gutuater) : un lot de la carte fondu en un seul noyau, et sa garde.

    python3 tests/test_fondre.py      (il faut une carte : sinon, rien n'est joué)

1. un lot fidèle (la seconde boucle ne lit que la case i de la première) : fondu, le même résultat que Lugus ;
2. un lot infidèle (elle lit la case i + 1) : la garde du noyau fondu le voit, la machine s'arrête et le note
   (« infidele fondre LIEU ») ; Gutuater le tait pour toujours ; relancé, le lot séparé donne le résultat de Lugus."""
import os
import subprocess
import sys
import tempfile

racine = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LUGUS = os.path.join(racine, "vtx-rs", "target", "release", "lugus" + (".exe" if os.name == "nt" else ""))
GUT = os.path.join(racine, "gutuater", "gutuater.vtx")
D = tempfile.mkdtemp(prefix="fondre-")
echecs = []
env = dict(os.environ, VTX_EPISSAGE="rapide", VTX_CARTE="1")


def verifier(nom, ok, detail=""):
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok or not detail else " : " + detail), flush=True)
    if not ok:
        echecs.append(nom)


def forger(nom):
    src = os.path.join(racine, "tests", "fondre", nom + ".vtx")
    dossier = os.path.join(D, nom)
    os.makedirs(dossier, exist_ok=True)
    exe = os.path.join(dossier, nom + (".exe" if os.name == "nt" else ""))
    r = subprocess.run([sys.executable, os.path.join(racine, "forge", "forge128.py"), src, "-o", exe],
                       capture_output=True, text=True, env=dict(env, VTX_TARANIS="1"))
    attendu = subprocess.run([LUGUS, src], capture_output=True, text=True).stdout.strip()
    return dossier, exe, r.stderr, attendu


def jouer(exe):
    r = subprocess.run([exe], capture_output=True, text=True, env=env, cwd=os.path.dirname(exe))
    return r.returncode, r.stdout.strip(), r.stderr


dossier, exe, dit, attendu = forger("fidele")
verifier("la forge fond le lot fidèle (la garde : 120 et 200)", "se fond aussi en un noyau" in dit and "[120, 200]" in dit, dit[-300:])
open(os.path.join(dossier, "gutuater.arn"), "w").write("fondre 12 vrai\n")
rc, sortie, err = jouer(exe)
if "pas de carte" in err:
    print("pas de carte : rien d'autre n'est joué")
    sys.exit(0)
verifier(f"fondu, le même résultat que Lugus ({attendu})", rc == 0 and sortie == attendu, f"{rc} {sortie} {err[-300:]}")
verifier("le vergobret a suivi l'ARN (fondu, sans essai)", "fondre vrai" in err or rc == 0, err[-200:])

dossier, exe, dit, attendu = forger("infidele")
open(os.path.join(dossier, "gutuater.arn"), "w").write("fondre 12 vrai\n")
rc, sortie, err = jouer(exe)
verifier("infidèle : la garde arrête la machine", rc == 3 and "pas fidèle" in err, f"{rc} {err[-300:]}")
mes = open(os.path.join(dossier, "gutuater.mesures")).read() if os.path.exists(os.path.join(dossier, "gutuater.mesures")) else ""
verifier("et le note pour Gutuater", "infidele fondre 12" in mes, mes)
r = subprocess.run([LUGUS, GUT], input=dossier + "\n", capture_output=True, text=True, encoding="utf-8")
arn = open(os.path.join(dossier, "gutuater.arn")).read()
verifier("Gutuater le tait pour toujours", "fondre 12 faux" in arn and "infidèle" in r.stdout, r.stdout + arn)
rc, sortie, err = jouer(exe)
verifier(f"relancé : le lot séparé, le résultat de Lugus ({attendu})", rc == 0 and sortie == attendu, f"{rc} {sortie} {err[-200:]}")

print("Tout est conforme" if not echecs else f"{len(echecs)} échec(s)")
sys.exit(1 if echecs else 0)
