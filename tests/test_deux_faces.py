"""0.844 : la clepsydre à deux faces (PROGRESSIF = 3 et 4, la méthode du créateur) : le C++ de référence et vtx au
processeur donnent le même film du jour, image par image (à demi-échelle, 320 × 180, huit images du jour) ; sur la
carte aussi quand une carte (ou lavapipe) répond. Les noyaux de la carte du mode sont tous acceptés."""
import os, re, subprocess, sys, tempfile
ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(ICI)
SCENE = os.path.join(RACINE, "belenos", "gergovie_scene.vtx")
CPP = os.path.join(RACINE, "belenos", "gergovie_ref.cpp")
ok = True


def film(sortie):
    m = re.findall(r"le jour[^\n]*le film entier, empreinte (-?\d+)", sortie)
    return m[-1] if m else None


with tempfile.TemporaryDirectory() as d:
    scene = open(SCENE, encoding="utf-8").read()
    scene = scene.replace("constante W = 1280;", "constante W = 320;").replace("constante H = 720;", "constante H = 180;")
    open(os.path.join(d, "gergovie_scene.vtx"), "w", encoding="utf-8").write(scene)
    for p in (3, 4):
        exe_c = os.path.join(d, f"ref{p}")
        subprocess.run(["g++", "-O2", "-fopenmp", "-DRD=2", "-DW=320", "-DH=180", f"-DPROGRESSIF={p}", "-o", exe_c, CPP],
                       check=True)
        attendu = film(subprocess.run([exe_c], capture_output=True, text=True,
                                      env=dict(os.environ, GERGOVIE_VOL="2", GERGOVIE_JOUR="8")).stdout)
        for carte in (0, 1):
            prog = os.path.join(d, f"g{p}{carte}.vtx")
            open(prog, "w", encoding="utf-8").write(
                f"dunon;\nconstante RN = 1;\nconstante RD = 2;\nconstante BLOCS = 0;\nconstante PROGRESSIF = {p};\n"
                f"importer \"gergovie_scene.vtx\";\n\nfonction principal() {{\n    epreuve(2, 8, {carte});\n}}\n")
            exe = os.path.join(d, f"g{p}{carte}")
            env = dict(os.environ, VTX_EPISSAGE="rapide", VTX_TARANIS="1")
            f = subprocess.run([sys.executable, os.path.join(RACINE, "forge", "forge128.py"), prog, "-o", exe],
                               capture_output=True, text=True, env=env)
            refus = [l for l in f.stderr.splitlines() if "reste au processeur" in l]
            sortie = subprocess.run([exe], capture_output=True, text=True, env=dict(os.environ, VTX_CARTE=str(carte)))
            vu = film(sortie.stdout)
            lieu = "sur la carte" if carte else "au processeur"
            if carte and "sur la carte" not in sortie.stdout:
                print("    ", f"PROGRESSIF = {p}, {lieu} : pas de carte ici, passé")
                continue
            bon = vu == attendu and vu is not None and not (carte and refus)
            ok &= bon
            print("OK  " if bon else "ÉCHEC", f"PROGRESSIF = {p}, {lieu} : le film du jour {vu}, le C++ {attendu}",
                  "" if bon else (refus[:3], sortie.stderr[-300:]))
print("La clepsydre à deux faces : tout est conforme" if ok else "La clepsydre à deux faces : des écarts")
sys.exit(0 if ok else 1)
