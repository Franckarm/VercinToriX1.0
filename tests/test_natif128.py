#!/usr/bin/env python3
"""La traduction de Lugus en x86-64 (0.5zv, vtx-rs/src/natif128.rs) : chaque programme fait en .exe (vtx exe128) est
joué deux fois, traduit (le défaut) et par Lugus seul (VTX_INTERPRETE). Les deux doivent écrire le même texte, rendre
les mêmes sorties, finir de la même façon (erreur comprise) et compter le même nombre d'instructions. Puis le gain,
mesuré sur exemples128/banc_traduction.vtx (un crible, une récursion, un brassage d'entiers)."""
import glob
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
X = ".exe" if os.name == "nt" else ""
VTX = os.path.join(racine, "vtx-rs", "target", "release", "vtx" + X)
d = tempfile.mkdtemp()
echecs = 0
_journal = os.environ.get("VTXJOURNAL")


def print(*a, **k):  # noqa: A001 : à l'écran et, depuis le .bat, dans son journal (on voit où l'on en est)
    import builtins
    builtins.print(*a, **k)
    if _journal:
        with open(_journal, "a", encoding="utf-8") as f:
            f.write(" ".join(str(x) for x in a) + "\n")



def verifier(nom, ok, detail=""):
    global echecs
    print(("OK   " if ok else "ÉCHEC ") + nom + ("" if ok else f" : {detail}"), flush=True)
    echecs += 0 if ok else 1


if platform.machine().lower() not in ("x86_64", "amd64"):
    print(f"processeur {platform.machine()} : pas de traduction en x86-64 ici, test sauté")
    sys.exit(0)


def jouer(exe, interprete, entree=""):
    env = dict(os.environ, VTX_SANS_PAUSE="1", VTX_CONSOLE="1", VTX_COMPTE="1")
    env.pop("VTX_INTERPRETE", None)
    if interprete:
        env["VTX_INTERPRETE"] = "1"
    print(f"   … {os.path.basename(exe)} {'par Lugus seul' if interprete else 'traduit'}", flush=True)
    try:
        r = subprocess.run([exe], input=entree, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           cwd=d, env=env, timeout=120)
    except subprocess.TimeoutExpired:
        return -9, "", -1, 0.0, ["figé : plus de deux minutes"], "figé"
    m = re.search(r"instructions (\d+) ; (.*?) ; ([\d.]+) s", r.stderr)
    erreur = [l for l in r.stderr.splitlines() if l.startswith("erreur")]
    return r.returncode, r.stdout, int(m.group(1)) if m else -1, float(m.group(3)) if m else 0.0, erreur, (m.group(2) if m else r.stderr)


def comparer(src, nom, entree=""):
    exe = os.path.join(d, nom + X)
    c = subprocess.run([VTX, "exe128", src, exe], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if c.returncode != 0:
        verifier(f"{nom} : l'exécutable se fait", False, c.stderr[-300:])
        return None
    a = jouer(exe, False, entree)
    b = jouer(exe, True, entree)
    ok = a[0] == b[0] and a[1] == b[1] and a[2] == b[2] and a[4] == b[4] and a[2] > 0 and "traduit en x86-64" in a[5]
    verifier(f"{nom} : traduit et joué par Lugus, mêmes texte, sorties, fin et instructions ({a[2]:,})", ok,
             f"code {a[0]}/{b[0]} pas {a[2]}/{b[2]} {a[5]} | {a[1][-200:]!r} / {b[1][-200:]!r} {a[4]} {b[4]}")
    return a, b


# 1. les exemples de Lugus et le vocabulaire
for f in sorted(glob.glob(os.path.join(racine, "exemples128", "*.vtx"))):
    nom = os.path.splitext(os.path.basename(f))[0]
    if nom == "banc_traduction":
        continue
    comparer(f, nom)
comparer(os.path.join(racine, "exemples", "premiers", "vocabulaire.vtx"), "vocabulaire")

# 2. des programmes faits pour la traduction : les bords des entiers, la pile, les erreurs
cas = {
    "bords": """// machine : lugus
fonction f(a, b) { retour a * b - (a ^ b) + (a >> 3) + (b << 5); }
fonction principal() {
    soit x = 18446744073709551615;
    soit y = x + 1;
    afficher(y, x - 1, x * x, f(x, 3), f(0, 0), x >> 63, x << 63);
    soit t = [1, 2, 3, 4, 5];
    soit s = 0;
    pour v dans t { s = s + v * v; }
    afficher(s, combien(t, 4), maximum(t));
    soit k = 0;
    tantque k < 100 { k = k + 7; si k > 50 { k = k + 100; } }
    afficher(k);
    sortie(s);
    sortie(k);
}
""",
    "recursion": """// machine : lugus
fonction ack(m, n) {
    si m == 0 { retour n + 1; }
    si n == 0 { retour ack(m - 1, 1); }
    retour ack(m - 1, ack(m, n - 1));
}
fonction principal() { afficher("ack(2, 3) =", ack(2, 3), "ack(3, 4) =", ack(3, 4)); }
""",
    "erreur": """// machine : lugus
fonction principal() {
    soit t = [1, 2, 3];
    soit s = 0;
    pour i dans 0..10 { s = s + t[i]; }
    afficher(s);
}
""",
    "textes": """// machine : lugus
fonction principal() {
    soit m = "Vercingétorix";
    soit r = "";
    pour i dans 0..5 { r = r + inverser_texte(m) + "|"; }
    afficher(r, combien_texte(r, "x"));
    soit a = 2.5;
    soit b = a * 3.0 + racine(2.0);
    afficher(b);
}
""",
    # 0.6j : les opérations sur tout le mot de 128 bits, traduites (retenue du bas au haut, zéro sur 128 bits,
    # décalages de 0 à 127, produit, comparaisons suivies d'un saut)
    "large": """// machine : lugus
// les opérations sur tout le mot de 128 bits : chaque résultat écrit, pour comparer la traduction à Lugus seul
fonction montrer(x: entier_128) {
    ecrire(haut(x));
    ecrire(" ");
    ecrire(bas(x));
    ecrire(" ; ");
}
fonction principal() {
    soit a: entier_128 = 1;
    soit b: entier_128 = 3;
    soit somme: entier_128 = 0;
    soit petits = 0;
    soit egaux = 0;
    pour tour dans 0..400 {
        // des valeurs qui débordent des 64 bits, dans les deux sens
        a = a * 6364136223846793005 + 1442695040888963407;
        b = (b * a) ^ (a >> 17) ^ (b << 29);
        soit n = tour % 131;
        soit g: entier_128 = a << n;
        soit d: entier_128 = b >> n;
        soit e: entier_128 = (a - b) + (a & b) - (a | b) + (g ^ d);
        somme = somme + e - 7;
        si a < b { petits = petits + 1; }
        si a - a == 0 { egaux = egaux + 1; }
        si g == d { egaux = egaux + 1000; }
        si tour % 40 == 0 {
            montrer(a); montrer(b); montrer(g); montrer(d); montrer(e); montrer(somme);
            afficher(n, petits, egaux);
        }
    }
    // les bords : la retenue qui passe du bas au haut, le zéro sur 128 bits, les décalages de 0, 63, 64, 65, 127
    soit un: entier_128 = 1;
    soit plein: entier_128 = 18446744073709551615;
    soit haut_seul: entier_128 = un << 64;
    montrer(plein + un); montrer(haut_seul - un); montrer(haut_seul * haut_seul); montrer(plein * plein);
    afficher("");
    soit moins: entier_128 = 0 - un;
    pour k dans [0, 1, 63, 64, 65, 127] {
        montrer(un << k); montrer(moins >> k); montrer(haut_seul >> k); montrer(plein << k);
        afficher(k);
    }
    soit z: entier_128 = haut_seul;
    soit tours = 0;
    tantque z != 0 { z = z - haut_seul; tours = tours + 1; }
    si haut_seul < un { afficher("faux : 2^64 < 1"); } sinon { afficher("2^64 n'est pas plus petit que 1 ;", tours); }
    si moins < un { afficher("-1 < 1"); } sinon { afficher("-1 n'est pas plus petit que 1"); }
    montrer(somme);
    afficher(petits, egaux);
}
""",
}
for nom, src in cas.items():
    f = os.path.join(d, nom + ".vtx")
    open(f, "w", encoding="utf-8").write(src)
    comparer(f, nom)

# 3. le clavier : le loto, sans hasard qui change d'une fois à l'autre (le choix 3 : les chances, puis quitter)
comparer(os.path.join(racine, "exemples", "premiers", "loto.vtx"), "loto", "3\n0\n")

# 4. le gain
r = comparer(os.path.join(racine, "exemples128", "banc_traduction.vtx"), "banc")
if r:
    a, b = r
    gain = b[3] / max(a[3], 1e-6)
    print(f"   banc : {a[2]:,} instructions ; traduit {a[3]:.3f} s, Lugus seul {b[3]:.3f} s : gain {gain:.2f} ; {a[5]}")
    verifier("la traduction va au moins deux fois plus vite que Lugus seul sur le banc", gain >= 2.0, f"gain {gain:.2f}")

shutil.rmtree(d, ignore_errors=True)
print("traduction de Lugus en x86-64 : " + ("tout est conforme" if echecs == 0 else f"{echecs} échec(s)"))
sys.exit(1 if echecs else 0)
