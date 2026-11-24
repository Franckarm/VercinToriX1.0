"""0.831 : garder le minimum (« si x < @2[a] { @2[a] = x; } ») : Lugus le joue point après point ; la carte, tous à la
fois, d'un seul geste (OpAtomicUMin de 64 bits) ; une carte qui ne le sait pas laisse la boucle au processeur.

    python3 tests/test_minimum.py"""
import os
import subprocess
import sys
import tempfile

racine = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LUGUS = os.path.join(racine, "vtx-rs", "target", "release", "lugus" + (".exe" if os.name == "nt" else ""))
PROG = os.path.join(racine, "tests", "minimum", "minimum.vtx")
D = tempfile.mkdtemp(prefix="minimum-")
echecs = []


def verifier(nom, ok, detail=""):
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok or not detail else " : " + detail), flush=True)
    if not ok:
        echecs.append(nom)


exe = os.path.join(D, "minimum" + (".exe" if os.name == "nt" else ""))
f = subprocess.run([sys.executable, os.path.join(racine, "forge", "forge128.py"), PROG, "-o", exe], capture_output=True, text=True)
verifier("forgé", f.returncode == 0, f.stderr[-400:])
attendu = subprocess.run([LUGUS, PROG], capture_output=True, text=True).stdout.strip()
env = dict(os.environ, VTX_EPISSAGE="rapide", VTX_CARTE="1", VTX_TARANIS="1")
r = subprocess.run([exe], capture_output=True, text=True, env=env)
if "pas de carte" in r.stderr:
    print("pas de carte : rien d'autre n'est joué")
    sys.exit(0)
sur_carte = "200000 tours" in r.stderr
verifier(f"200 000 points, 1 000 cases : le même minimum que Lugus ({attendu}) "
         + ("sur la carte" if sur_carte else "(la carte ne garde pas le minimum : au processeur)"),
         r.stdout.strip() == attendu, r.stdout + r.stderr[-300:])
r = subprocess.run([exe], capture_output=True, text=True, env=dict(env, VTX_ATOMIQUE64="0"))
verifier("sans le minimum atomique : la boucle reste au processeur, le même résultat",
         r.stdout.strip() == attendu and "ne garde pas le minimum" in r.stderr, r.stdout + r.stderr[-300:])
r = subprocess.run([exe], capture_output=True, text=True, env=dict(os.environ, VTX_CARTE="0"))
verifier("au processeur (les cylindres) : le même résultat", r.stdout.strip() == attendu, r.stdout + r.stderr[-300:])
print("Tout est conforme" if not echecs else f"{len(echecs)} échec(s)")
sys.exit(1 if echecs else 0)
