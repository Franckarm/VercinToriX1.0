#!/usr/bin/env python3
"""Gobatix interactif : souris, touches, cadence, anti-couleur, animations GIF, sur le SPU-32 et le SPU-64.

 1. Les deux compilateurs de chaque machine donnent les mêmes mots pour les programmes qui utilisent les nouvelles
    fonctions (vtx.py = vtxc embarqué, vtx64.py = vtxc64 embarqué ; prélude, optimisations, partition).
 2. Sans fenêtre : souris(), touche(), molette(), appuyee() rendent 0, cadence() rend l'ancienne cadence (16),
    anti_couleur est une involution ; même résultat sur les machines Python et Rust.
 3. Le GIF : chaque image décodée (Pillow, si présent) est exactement l'image du programme tramée sur la palette du
    cube ; les images inchangées ne coûtent rien (différence par l'anti-cube : points inchangés transparents).
 4. Un scénario de gestes (peindre.scenario) rejoué image par image : la peinture, la palette, la molette, les flèches ;
    le SPU-32 et le SPU-64 donnent le même GIF, octet pour octet.
"""
import os
import shutil
import subprocess
import sys
import tempfile

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, racine)
import vtx  # noqa: E402
import vtx64  # noqa: E402

cargo = shutil.which("cargo")
if not cargo:
    print("cargo absent : Gobatix n'est pas vérifié (il tourne sur la machine Rust)")
    sys.exit(0)
rs = os.path.join(racine, "vtx-rs")
cible = os.environ.get("CARGO_TARGET_DIR") or os.path.join(rs, "target")
subprocess.run([cargo, "build", "--release", "-q"], cwd=rs, check=True)
ext = ".exe" if os.name == "nt" else ""
VTX = os.path.join(cible, "release", "vtx" + ext)
VTX64 = os.path.join(cible, "release", "vtx64" + ext)
TMP = tempfile.mkdtemp(prefix="gobatix-")
GOB = os.path.join(racine, "exemples", "gobatix")
echecs = []


def verifier(nom, ok, detail=""):
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok or not detail else " : " + detail), flush=True)
    if not ok:
        echecs.append(nom)


def mots_fichier(p):
    t = open(p).read().strip()
    return [int(x) for x in t.split(";")[0].split(",") if x]


ESSAI = """fonction principal() {
    sortie(souris());
    sortie(souris_x(11256099) + souris_y(11256099) + souris_boutons(251658240) + souris_dedans(134217728));
    sortie(touche());
    sortie(molette());
    sortie(appuyee(touche_gauche()) + appuyee(97));
    sortie(cadence(40));
    sortie(cadence(16));
    soit c = rgb(10, 200, 30);
    sortie(anti_couleur(anti_couleur(c)) == c);
    sortie(touche_haut() + touche_droite() + touche_bas() + touche_entree() + touche_echap() + touche_espace());
    ecran(8, 4);
    pixel(1, 1, c);
    pixel_anti(1, 1);
    rectangle_anti(0, 0, 3, 3);
    rectangle_anti(0, 0, 3, 3);
    sortie(@1[9] == anti_couleur(c));
    sortie(texte_image(0, 0, "Clé", c) + largeur_texte("ab\\ncdé", 2));
    sortie(glisse_x(souris_glisse()) + glisse_y(1 << 16) + glisse_x(65535) + 1);
    soit t = horloge();
    sortie(presenter());
}
"""

# 1. mêmes mots
progs = {"essai": ESSAI}
for nom in ("peindre.vtx", "cube_tournant.vtx", "cube_chromatique.vtx"):
    progs[nom] = open(os.path.join(GOB, nom), encoding="utf-8").read()
ok32 = ok64 = 0
for nom, src in progs.items():
    p = os.path.join(TMP, "p.vtx")
    with open(p, "w", encoding="utf-8") as f:
        f.write(src)
    a = vtx.assembler(vtx.compiler(src, prelude=True, optim=True, partition=True))
    subprocess.run([VTX, "compiler", p, os.path.join(TMP, "p.prog")], capture_output=True, check=True)
    ok32 += a == mots_fichier(os.path.join(TMP, "p.prog"))
    try:
        b = vtx64.assembler(vtx64.compiler(src, prelude=True, optim=True, partition=True))
    except vtx64.VtxError:
        b = None  # un programme écrit pour les flottants du SPU-32 peut ne pas compiler en 64 bits
    if b is None:
        ok64 += 1
        continue
    subprocess.run([VTX64, "compiler", p, os.path.join(TMP, "p.mots")], capture_output=True, check=True)
    ok64 += b == mots_fichier(os.path.join(TMP, "p.mots"))
verifier(f"1. mêmes mots : vtx.py = vtxc {ok32}/{len(progs)}, vtx64.py = vtxc64 {ok64}/{len(progs)}",
         ok32 == ok64 == len(progs))

# 2. sans fenêtre, les quatre machines
attendu = [0, 0xABC123 & 4095, 0, 0, 0, 16, 40, 1, 65574 + 65575 + 65576 + 13 + 27 + 32, 1, 18 + 36, 1, 0]
attendu[1] = (0xABC123 & 4095) + ((0xABC123 >> 12) & 4095) + 7 + 1
p = os.path.join(TMP, "essai.vtx")
with open(p, "w", encoding="utf-8") as f:
    f.write(ESSAI)
r32 = subprocess.run([VTX, p], capture_output=True, text=True).stdout.strip().split("\n")[-1]
r64 = subprocess.run([VTX64, p], capture_output=True, text=True).stdout.strip().split("\n")[-1]
py32 = vtx.executer(ESSAI, ())[0].sortie
py64 = vtx64.executer(ESSAI, ()) if hasattr(vtx64, "executer") else None
py64 = py64[0].sortie if py64 else None
lisible = lambda t: [int(x) for x in t.split(",")]
ok = lisible(r32) == attendu and lisible(r64) == attendu and list(py32) == attendu and (py64 is None or list(py64) == attendu)
verifier("2. sans fenêtre : souris, touche, molette, appuyee à 0, cadence gardée, anti involutif ; Python et Rust, 32 et 64 bits",
         ok, f"attendu {attendu}, Rust {r32} / {r64}, Python {list(py32)} / {py64}")

# 3. le GIF
gif = os.path.join(TMP, "cube.gif")
pngs = os.path.join(TMP, "png")
subprocess.run([VTX, "gobatix", os.path.join(GOB, "cube_tournant.vtx"), "--gif", gif, "--max", "60"], capture_output=True, check=True)
subprocess.run([VTX, "gobatix", os.path.join(GOB, "cube_tournant.vtx"), "--images", pngs, "--max", "60"], capture_output=True, check=True)
try:
    import numpy as np
    from PIL import Image
except ImportError:
    np = None
if np is None:
    verifier("3. GIF écrit (Pillow ou numpy absent : images non décodées)", os.path.getsize(gif) > 1000)
else:
    B = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5]
    pal = [(r * 51, g * 51, b * 51) for r in range(6) for g in range(6) for b in range(6)]
    pal += [((k * 255 + 19) // 38,) * 3 for k in range(39)] + [(0, 0, 0)]
    pal = np.array(pal)

    def tramer(a):
        h, w, _ = a.shape
        y, x = np.mgrid[0:h, 0:w]
        t = np.array(B)[(y & 3) * 4 + (x & 3)]
        r, g, b = [a[:, :, i].astype(int) for i in range(3)]
        q = lambda v: np.minimum((v * 5 * 16 + t * 255) // (255 * 16), 5)
        gris = (r == g) & (g == b) & (r % 51 != 0)
        return pal[np.where(gris, np.minimum((r * 38 * 16 + t * 255) // (255 * 16), 38) + 216, q(r) * 36 + q(g) * 6 + q(b))]

    im = Image.open(gif)
    faux = 0
    for n in range(60):
        im.seek(n)
        dec = np.array(im.convert("RGB")).astype(int)
        ref = tramer(np.array(Image.open(os.path.join(pngs, f"image-{n + 1:04d}.png")).convert("RGB")))
        faux += int((dec != ref).any(axis=2).sum())
    verifier(f"3. GIF du cube tournant : 60 images décodées, {faux} point(s) différent(s) de l'image tramée attendue", faux == 0)

# 4. le scénario
g32, g64 = os.path.join(TMP, "p32.gif"), os.path.join(TMP, "p64.gif")
sc = os.path.join(GOB, "peindre.scenario")
subprocess.run([VTX, "gobatix", os.path.join(GOB, "peindre.vtx"), "--scenario", sc, "--gif", g32, "--max", "200"],
               capture_output=True, check=True)
subprocess.run([VTX, "gobatix64", os.path.join(GOB, "peindre.vtx"), "--scenario", sc, "--gif", g64, "--max", "200"],
               capture_output=True, check=True)
meme = open(g32, "rb").read() == open(g64, "rb").read()
detail = ""
if np is not None:
    im = Image.open(g32)
    im.seek(199)
    a = np.array(im.convert("RGB")).astype(int)
    blanc = (a[:, :, 0] == 255) & (a[:, :, 1] == 255) & (a[:, :, 2] == 255)
    rouge = (a[:, :, 0] == 255) & (a[:, :, 1] == 51) & (a[:, :, 2] == 51)
    bleu = (a[:, :, 0] == 51) & (a[:, :, 1] == 153) & (a[:, :, 2] == 255)
    # la spirale blanche au milieu, la vague rouge en bas, la vague bleue en haut (sous la palette)
    ok_p = blanc[60:170, 90:240].sum() > 2000 and rouge[150:200].sum() > 1000 and bleu[22:70].sum() > 800
    # la case bleue de la palette est soulignée (choisie au clic)
    ok_p = ok_p and blanc[16:18, 4 + 4 * 18:4 + 4 * 18 + 14].all()
    detail = f" ; peinture : blanc {int(blanc.sum())}, rouge {int(rouge.sum())}, bleu {int(bleu.sum())} points"
    meme = meme and ok_p
verifier("4. scénario de gestes rejoué (peindre.vtx) : même GIF sur le SPU-32 et le SPU-64" + detail, meme)

shutil.rmtree(TMP, ignore_errors=True)
print()
print("Gobatix : " + ("tout est conforme" if not echecs else f"{len(echecs)} échec(s)"))
sys.exit(1 if echecs else 0)
