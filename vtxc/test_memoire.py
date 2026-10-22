"""Mémoire qui se libère (en-têtes de blocs, liberer, ramasser) et mémoire qui dure (sauver_tas, charger_tas) :
mêmes mots par vtx.py et vtxc, blocs réutilisés, données gardées intactes, souvenirs d'un lancement à l'autre."""
import os, shutil, subprocess, sys, tempfile
ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, racine)
import vtx  # noqa: E402

rs = os.path.join(racine, "vtx-rs")
cible = os.environ.get("CARGO_TARGET_DIR") or os.path.join(rs, "target")
subprocess.run([shutil.which("cargo") or "cargo", "build", "--release", "-q"], cwd=rs, check=True)
VTX = os.path.join(cible, "release", "vtx" + (".exe" if os.name == "nt" else ""))
tmp = tempfile.mkdtemp()
ok = True
try:
    for nom in ("ramasser.vtx", "memoire.vtx", "cubes.vtx", "purge.vtx"):
        shutil.copy(os.path.join(racine, "exemples", "premiers", nom), tmp)
        src = open(os.path.join(tmp, nom), encoding="utf-8").read()
        py = vtx.assembler(vtx.compiler(src, dossier=tmp))
        p = os.path.join(tmp, "x.prog")
        subprocess.run([VTX, "compiler", os.path.join(tmp, nom), p], check=True, capture_output=True)
        vc = [int(x) for x in open(p).read().split(";")[0].split(",")]
        if py != vc:
            print(nom, ": MOTS DIFFÉRENTS")
            ok = False
    r = subprocess.run([VTX, "ramasser.vtx"], cwd=tmp, capture_output=True, text=True, encoding="utf-8").stdout
    lignes = dict(l.split(" :", 1) for l in r.strip().split("\n"))
    avant = int(lignes["tas utilisé avant"])
    libres = int(lignes["mots libérés"])
    apres = int(lignes["tas après 900 nouveaux tableaux"])
    garde = lignes["gardés intacts"].strip() == "10 4500 chromatique" and lignes["dico"].strip() == "500 1 34 300"
    ok1 = libres > avant * 0.9 and apres == avant and garde
    print(f"Ramasse-miettes : {libres} mots libérés sur {avant} ; 900 nouveaux tableaux sans grandir le tas : "
          f"{'oui' if apres == avant else 'NON'} ; données gardées intactes : {'oui' if garde else 'NON'}")
    sorties = [subprocess.run([VTX, "memoire.vtx"], cwd=tmp, capture_output=True, text=True, encoding="utf-8").stdout
               for _ in range(3)]
    ok2 = (sorties[0].startswith("première fois") and "lancé 2 fois ; premier ami : Ambiorix ; amis : 2" in sorties[1]
           and "lancé 3 fois" in sorties[2] and "amis : 3" in sorties[2])
    print(f"Mémoire qui dure (sauver_tas, charger_tas) : souvenirs sur trois lancements : {'oui' if ok2 else 'NON'}")
    # le programme change entre deux lancements (le code bouge) : les textes rangés restent justes
    autre = 'fonction inutile(x) { afficher("du texte pour tout décaler", x); retour x * 3; }\n' + open(
        os.path.join(tmp, "memoire.vtx"), encoding="utf-8").read()
    with open(os.path.join(tmp, "memoire2.vtx"), "w", encoding="utf-8") as f:
        f.write(autre)
    s4 = subprocess.run([VTX, "memoire2.vtx"], cwd=tmp, capture_output=True, text=True, encoding="utf-8").stdout
    ok2b = "je suis ScoR lancé 4 fois ; premier ami : Ambiorix ; amis : 4" in s4
    print(f"Mémoire qui dure quand le programme change : textes gardés : {'oui' if ok2b else 'NON ' + s4}")
    ok2 = ok2 and ok2b
    attendu = ("cube 262 : 262000 262999\ncube 330 : 330000 330999\ncube 392 : 392000 392999\n"
               "cube 0 : 0 ; l'étage 0 refuse : 1\nfin de deux cubes : 7 puis 1 9\n")
    rc = subprocess.run([VTX, "cubes.vtx"], cwd=tmp, capture_output=True, text=True, encoding="utf-8").stdout
    cpu, _, _ = vtx.executer(open(os.path.join(tmp, "cubes.vtx"), encoding="utf-8").read(), dossier=tmp)
    rp = "".join(chr(c) for c in cpu.texte)
    ok3 = rc == attendu and rp == attendu
    print(f"Cubes additionnés par fréquence (accorder, frequence) : machine Rust {'juste' if rc == attendu else 'ÉCART'}, "
          f"machine Python {'juste' if rp == attendu else 'ÉCART'}")
    rp2 = subprocess.run([VTX, "purge.vtx"], cwd=tmp, capture_output=True, text=True, encoding="utf-8").stdout
    ok4 = rp2.startswith("gardés : 120 somme : 7140000")
    print(f"Purge automatique (tas plein deux fois : nouveau ramasse puis réessaie, blocs voisins fondus) : "
          f"{'données justes' if ok4 else 'ÉCART ' + rp2}")
    ok = ok and ok1 and ok2 and ok3 and ok4
finally:
    shutil.rmtree(tmp, ignore_errors=True)
sys.exit(0 if ok else 1)
