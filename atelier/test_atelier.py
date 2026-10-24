"""L'atelier (« vtx atelier programme.vtx ») piloté dans un pseudo-terminal : on tape, on lance, on lit l'écran.
Un petit émulateur de terminal reconstitue l'écran à partir des séquences ANSI. Sous Windows, il n'y a pas de
pseudo-terminal en Python : le test est sauté (l'atelier s'essaie alors à la main).
Option : --image FICHIER.html enregistre le dernier écran, en couleurs."""
import os, re, shutil, subprocess, sys, tempfile, time, html

if os.name == "nt":
    print("Windows : pas de pseudo-terminal en Python, test sauté (essayez « vtx atelier exemples\\rayons.vtx »)")
    sys.exit(0)
import pty, fcntl, termios, struct, select

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
rs = os.path.join(racine, "vtx-rs")
cible = os.environ.get("CARGO_TARGET_DIR") or os.path.join(rs, "target")
subprocess.run([shutil.which("cargo") or "cargo", "build", "--release", "-q"], cwd=rs, check=True)
VTX = os.path.join(cible, "release", "vtx")
L, H = 140, 40
F2, F4, F5, F6 = "\x1b[12~", "\x1b[14~", "\x1b[15~", "\x1b[17~"
BAS, FIN = "\x1b[B", "\x1b[F"


F7, F8, F9, F10 = "\x1b[18~", "\x1b[19~", "\x1b[20~", "\x1b[21~"


def piloter(fichier, touches, dossier=None):
    pid, fd = pty.fork()
    if pid == 0:
        os.environ["TERM"] = "xterm-256color"
        if dossier:
            os.chdir(dossier)
        os.execv(VTX, [VTX, "atelier"] + ([fichier] if fichier else []))
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", H, L, 0, 0))
    flux = bytearray()

    def lire(duree, jusqua=None, debut=0):
        fin = time.time() + duree
        if jusqua and jusqua in flux[debut:]:
            return True
        while time.time() < fin:
            r, _, _ = select.select([fd], [], [], 0.05)
            if r:
                try:
                    d = os.read(fd, 65536)
                except OSError:
                    return False
                if not d:
                    return False
                flux.extend(d)
                if jusqua and jusqua in flux[debut:]:
                    lire(0.2)
                    return True
        return True

    lire(1.0)
    marque = 0
    for k in touches:
        if isinstance(k, tuple):        # (motif attendu depuis la touche précédente, délai maximal)
            lire(k[1], k[0].encode(), marque)
            continue
        marque = len(flux)
        os.write(fd, k.encode())
        lire(0.25)
    os.write(fd, b"\x11")              # Ctrl+Q
    lire(0.3)
    os.write(fd, b"\x11")
    fini = not lire(1.0)
    try:
        _, statut = os.waitpid(pid, os.WNOHANG)
    except ChildProcessError:
        statut = 0
    if not fini:
        os.kill(pid, 9)
        os.waitpid(pid, 0)
    return bytes(flux), fini


def c256(n):
    base = [(0, 0, 0), (205, 0, 0), (0, 205, 0), (205, 205, 0), (0, 0, 238), (205, 0, 205), (0, 205, 205), (229, 229, 229),
            (127, 127, 127), (255, 0, 0), (0, 255, 0), (255, 255, 0), (92, 92, 255), (255, 0, 255), (0, 255, 255), (255, 255, 255)]
    if n < 16:
        return base[n]
    if n < 232:
        n -= 16
        v = [0, 95, 135, 175, 215, 255]
        return (v[n // 36], v[n // 6 % 6], v[n % 6])
    g = 8 + 10 * (n - 232)
    return (g, g, g)


def ecran(flux, avant_sortie=True):
    """La grille des caractères (et leurs couleurs) du dernier écran dessiné avant la sortie de l'atelier."""
    t = flux.decode("utf-8", "replace")
    if avant_sortie and "\x1b[?1049l" in t:
        t = t[:t.rfind("\x1b[?1049l")]
    # l'atelier redessine tout l'écran à chaque fois : le dernier dessin suffit
    if "\x1b[?25l\x1b[H" in t:
        t = t[t.rfind("\x1b[?25l\x1b[H"):]
    g = [[(" ", (200, 200, 200), (0, 0, 0))] * L for _ in range(H)]
    y = x = 0
    fg, bg, inv = (200, 200, 200), (0, 0, 0), False
    for m in re.finditer(r"\x1b\[([?0-9;]*)([A-Za-z])|([^\x1b])", t):
        if m.group(3) is not None:
            ch = m.group(3)
            if ch in "\r\n":
                continue
            if 0 <= y < H and 0 <= x < L:
                g[y][x] = (ch, bg, fg) if inv else (ch, fg, bg)
            x += 1
            continue
        p, c = m.group(1), m.group(2)
        if c == "H":
            a = [int(v) if v else 1 for v in p.split(";")] if p else [1, 1]
            y, x = a[0] - 1, (a[1] - 1 if len(a) > 1 else 0)
        elif c == "m":
            a = [int(v) if v else 0 for v in p.split(";")] if p else [0]
            k = 0
            while k < len(a):
                v = a[k]
                if v == 0:
                    fg, bg, inv = (200, 200, 200), (0, 0, 0), False
                elif v == 7:
                    inv = True
                elif v == 27:
                    inv = False
                elif v in (38, 48) and k + 1 < len(a) and a[k + 1] == 5:
                    col = c256(a[k + 2]); k += 2
                    fg, bg = (col, bg) if v == 38 else (fg, col)
                elif v in (38, 48) and k + 1 < len(a) and a[k + 1] == 2:
                    col = tuple(a[k + 2:k + 5]); k += 4
                    fg, bg = (col, bg) if v == 38 else (fg, col)
                k += 1
    return g


def texte(g):
    return "\n".join("".join(c[0] for c in l) for l in g)


def en_html(g):
    morceaux = ['<!doctype html><meta charset="utf-8"><body style="background:#000;margin:0">'
                '<pre style="font:15px/17px monospace;margin:0">']
    for l in g:
        for ch, f, b in l:
            morceaux.append('<span style="color:rgb%s;background:rgb%s">%s</span>' % (f, b, html.escape(ch)))
        morceaux.append("\n")
    return "".join(morceaux) + "</pre>"


bons = total = 0
def verifier(nom, ok, detail=""):
    global bons, total
    total += 1
    bons += bool(ok)
    print(("ok    " if ok else "ÉCHEC ") + nom + ("" if ok else " : " + detail))


tmp = tempfile.mkdtemp()
try:
    # 1. un programme du paquet : F5 compile et lance ; les sorties s'affichent
    shutil.copy(os.path.join(racine, "exemples", "premiers", "carres.vtx"), tmp)
    flux, fini = piloter(os.path.join(tmp, "carres.vtx"), [F5, ("sorties", 30)])
    t = texte(ecran(flux))
    verifier("carres.vtx : F5 donne « sorties : 285 »", "sorties : 285" in t, t[-400:])
    verifier("Ctrl+Q quitte et rend le terminal", fini and flux.rstrip().endswith(b"\x1b[?1049l") or b"\x1b[?1049l" in flux[-200:])

    # 2. le cube : rayons.vtx dessine une image dans l'étage 2 ; F4 donne les entrées, F6 passe au cube
    shutil.copy(os.path.join(racine, "exemples", "rayons.vtx"), tmp)
    flux, _ = piloter(os.path.join(tmp, "rayons.vtx"), [F4, "600 900 100", "\r", F5, ("instructions", 60), F6, "2", "l"])
    g = ecran(flux)
    t = texte(g)
    verifier("rayons.vtx : programme lancé avec ses entrées", "instructions" in t and "erreur" not in t, t[-600:])
    # les couleurs du cube : des pixels de ciel (bleu nuit) et de murs, pas un écran noir
    couleurs = set()
    for l in g[1:H // 2]:
        for ch, f, b in l[L * 11 // 20 + 1:]:
            if ch == "▀":
                couleurs.add(f); couleurs.add(b)
    verifier("le cube montre l'image de l'étage 2 (%d couleurs)" % len(couleurs), len(couleurs) > 20, str(len(couleurs)))
    verifier("la ligne d'information donne l'étage et la largeur", "étage 2" in t and "128 mots/ligne" in t, t)
    if "--image" in sys.argv:
        open(sys.argv[sys.argv.index("--image") + 1], "w", encoding="utf-8").write(en_html(g))

    # 3. l'éditeur : on écrit un programme, on l'enregistre, on le lance
    neuf = os.path.join(tmp, "neuf.vtx")
    flux, _ = piloter(neuf, [BAS, FIN, "soit x = 6;\r", "si x > 2 {\r", "sortie(x * 7);\r", "}\r",
                             "ecrire_texte(1, \"salut\\n\");", F5, ("sorties", 30)])
    attendu = 'fonction principal() {\n    soit x = 6;\n    si x > 2 {\n        sortie(x * 7);\n    }\n    ecrire_texte(1, "salut\\n");\n}\n'
    obtenu = open(neuf, encoding="utf-8").read()
    verifier("éditeur : retrait automatique, « } » revient d'un niveau, F5 enregistre", obtenu == attendu, repr(obtenu))
    t = texte(ecran(flux))
    verifier("le programme écrit donne « sorties : 42 » et « » salut »", "sorties : 42" in t and "» salut" in t, t[-400:])

    # 4. une erreur : la ligne est marquée, le message nomme le fichier
    faute = os.path.join(tmp, "faute.vtx")
    open(faute, "w").write("fonction principal() {\n    soit a = 1\n    sortie(a) sortie(a)\n}\n")
    flux, _ = piloter(faute, [F5, ("erreur", 30)])
    g = ecran(flux)
    t = texte(g)
    rouge = [y for y in range(H) if g[y][0][2] == c256(52)]
    verifier("erreur : « erreur faute.vtx, ligne 3 » et la ligne 3 en rouge", "erreur faute.vtx, ligne 3" in t and rouge == [3],
             f"{rouge} {t[-300:]}")

    # 5. annuler (Ctrl+Z) et quitter sans enregistrer
    flux, _ = piloter(faute, [FIN, " // essai", "\x1a"])
    t = texte(ecran(flux))
    verifier("Ctrl+Z annule le dernier mot tapé", "essai" not in t.split("\n")[1] and "//" in t.split("\n")[1], t.split("\n")[1])
    verifier("quitter sans F2 laisse le fichier intact", open(faute).read().startswith("fonction principal() {\n    soit a = 1\n"))

    # 6. le pas à pas : F7 avance d'une ligne (en entrant dans les fonctions), F8 passe par-dessus, F9 + F5 va
    #    jusqu'au point d'arrêt ; la ligne en cours est en vert, le panneau montre registres et variables
    pas = os.path.join(tmp, "pas.vtx")
    open(pas, "w").write("fonction carre(x) {\n    retour x * x;\n}\n\nfonction principal() {\n    soit a = 3;\n"
                         "    soit b = carre(a);\n    afficher(b);\n    soit c = carre(b);\n    afficher(c - 100);\n}\n")
    VERT = (0, 95, 0)
    def ligne_verte(g):
        return [y for y in range(H) if g[y][1][2] == VERT]
    flux, _ = piloter(pas, [F7])
    g = ecran(flux)
    verifier("F7 : première ligne de principal (6) en vert", ligne_verte(g) == [6], str(ligne_verte(g)))
    flux, _ = piloter(pas, [F7, F7, F7])
    g = ecran(flux)
    verifier("F7 trois fois : entre dans carre (ligne 2)", ligne_verte(g) == [2], str(ligne_verte(g)))
    flux, _ = piloter(pas, [F7, F7, F8, F8])
    g = ecran(flux)
    t = texte(g)
    verifier("F8 : passe par-dessus carre et afficher (ligne 9), la console montre 9", ligne_verte(g) == [9] and "» 9" in t,
             f"{ligne_verte(g)} {t[-500:]}")
    verifier("le panneau montre les registres et les variables locales",
             "pas à pas · ligne 9" in t and "R1 " in t and "variables locales  -1: 3  -2: 9" in t, t[-900:])
    flux, _ = piloter(pas, [BAS * 9, F9, F7, ("ligne 6", 5), F5, ("ligne 10", 5)])
    g = ecran(flux)
    t = texte(g)
    verifier("F9 sur la ligne 10, F5 : arrêt sur le point d'arrêt", ligne_verte(g) == [10],
             f"{ligne_verte(g)}")
    flux, _ = piloter(pas, [F7, F5, ("fini", 10)])
    t = texte(ecran(flux))
    verifier("F5 sans point d'arrêt : jusqu'au bout, « » -19 »", "programme fini" in t and "» -19" in t, t[-500:])

    # 7. sans fichier : la fenêtre « ouvrir » ; Entrée sur un fichier l'ouvre
    flux, _ = piloter(None, [], dossier=tmp)
    t = texte(ecran(flux))
    verifier("sans fichier : la fenêtre « ouvrir » liste les .vtx du dossier", "Ouvrir dans" in t and "pas.vtx" in t and "carres.vtx" in t, t[:600])
    noms = sorted(f for f in os.listdir(tmp) if f.endswith(".vtx"))
    flux, _ = piloter(None, [BAS * (noms.index("pas.vtx") + 1), "\r"], dossier=tmp)
    t = texte(ecran(flux))
    verifier("Entrée ouvre le fichier choisi", "fonction carre(x)" in t, t[:400])

    # 8. les menus (F10, flèches, Entrée), la sélection, copier-coller, rétablir, le collage, la souris
    menus = os.path.join(tmp, "menus.vtx")
    open(menus, "w").write("fonction principal() {\n    afficher(1);\n}\n")
    flux, _ = piloter(menus, [F10])
    t = texte(ecran(flux))
    verifier("F10 ouvre le menu Fichier", "Fichier" in t.split("\n")[0] and "Enregistrer sous" in t and "Ouvrir…" in t, t[:500])
    flux, _ = piloter(menus, [F10, "\x1b[C", "\x1b[C"])
    t = texte(ecran(flux))
    verifier("flèche droite : le menu Exécuter", "Pas par-dessus" in t and "Point d'arrêt" in t, t[:600])
    # Maj+Fin sélectionne la ligne 2, Ctrl+C la copie, Fin, Entrée, Ctrl+V la colle en dessous, puis F2
    flux, _ = piloter(menus, [BAS, "\x1b[H", "\x1b[1;2F", "\x03", "\x1b[F", "\r", "\x16", F2])
    obtenu = open(menus).read()
    verifier("Maj+Fin, Ctrl+C, Ctrl+V : la ligne est dupliquée", obtenu.count("afficher(1);") == 2, repr(obtenu))
    # Ctrl+Z puis Ctrl+Y : annuler puis rétablir
    flux, _ = piloter(menus, [BAS, "\x1b[F", " // x", "\x1a", "\x19", F2])
    verifier("Ctrl+Z puis Ctrl+Y rétablit", "// x" in open(menus).read(), open(menus).read())
    # un collage encadré (« bracketed paste ») : inséré tel quel, sans retrait automatique en plus
    flux, _ = piloter(menus, [BAS, "\x1b[F", "\x1b[200~\n    soit a = 2;\n    soit b = 3;\x1b[201~", F2])
    obtenu = open(menus).read()
    verifier("collage de plusieurs lignes, retraits gardés", "\n    soit a = 2;\n    soit b = 3;" in obtenu, repr(obtenu))
    # la souris : un clic sur « Édition » ouvre le menu, un clic sur « Tout sélectionner », puis Ctrl+X vide le fichier
    x_ed = 1 + len(" Fichier ") + 1 + 1
    flux, _ = piloter(menus, [f"\x1b[<0;{x_ed + 2};1M", f"\x1b[<0;{x_ed + 3};7M", "\x18", F2])
    obtenu = open(menus).read()
    verifier("souris : menu Édition, « Tout sélectionner », puis Ctrl+X", obtenu.strip() == "", repr(obtenu))

    # atelier (le même exécutable sous un autre nom) ouvre directement l'atelier
    ATELIER = os.path.join(cible, "release", "atelier")
    verifier("l'exécutable « atelier » est construit", os.path.exists(ATELIER))
finally:
    shutil.rmtree(tmp, ignore_errors=True)
print(f"\nAtelier : {bons}/{total} vérifications")
sys.exit(0 if bons == total else 1)
