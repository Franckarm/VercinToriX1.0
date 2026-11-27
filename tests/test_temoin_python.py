#!/usr/bin/env python3
"""0.851 : le témoin (la décision du créateur : la machine Python de vtx128.py garde un rôle, petit, à la main). Pour
voir si une modification de Vercintorix change ce que fait un programme : une poignée de programmes de Lugus, joués par
lugus (vtxc128 et la machine Rust) et par vtx128.py (son compilateur et sa machine Python) ; la même sortie attendue.

Ne se joue pas par défaut : « python3 verifier.py --temoin », ou directement :
    python3 tests/test_temoin_python.py [PROG.vtx …]      (sans argument : la poignée d'exemples ci-dessous)

Si un programme diffère, ce n'est pas forcément une erreur de lugus : la machine Python peut être en retard (un mot du
langage ajouté seulement à vtxc128). Le témoin dit qu'il y a un écart ; à regarder à la main."""
import os
import subprocess
import sys

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
X = ".exe" if os.name == "nt" else ""
LUGUS = os.path.join(racine, "vtx-rs", "target", "release", "lugus" + X)
POIGNEE = ["bonjour128.vtx", "quatre_verites.vtx", "codon.vtx", "supposons.vtx", "valeurs.vtx", "nombres.vtx",
           "entier128.vtx", "reste.vtx"]
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1", VTX_SANS_CLAVIER="1")


def jouer(cmd, dossier):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=dossier, env=ENV,
                       stdin=subprocess.DEVNULL, timeout=900)
    # la machine Python dit à la fin combien d'instructions elle a jouées : ce n'est pas la sortie du programme
    return "".join(l + "\n" for l in r.stdout.split("\n") if l and "instructions exécutées" not in l)


def normal_python(t):
    """la machine Python écrit « sortie : V  (#…) » par valeur ; lugus les écrit en tête, sur une ligne, séparées par des
    virgules"""
    sorties, reste = [], []
    for l in t.split("\n"):
        if l.startswith("sortie : "):
            sorties.append(l[9:].split()[0])
        elif l:
            reste.append(l)
    return "".join(x + "\n" for x in ([",".join(sorties)] if sorties else []) + reste)


progs = sys.argv[1:] or [os.path.join(racine, "exemples128", f) for f in POIGNEE]
ecarts = 0
for p in [os.path.abspath(x) for x in progs]:
    d = os.path.dirname(os.path.abspath(p))
    a = jouer([LUGUS, p], d)
    b = jouer([sys.executable, os.path.join(racine, "vtx128.py"), "run", p], d)
    ok = a != "" and (a == b or a == normal_python(b))
    ecarts += 0 if ok else 1
    print(("OK   " if ok else "ÉCART ") + f"{os.path.basename(p)} : lugus et le témoin Python"
          + ("" if ok else f" : {a[-200:]!r} / {b[-200:]!r}"), flush=True)
print("le témoin : " + ("les mêmes sorties" if not ecarts else f"{ecarts} écart(s), à regarder"))
sys.exit(1 if ecarts else 0)
