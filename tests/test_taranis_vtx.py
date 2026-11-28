#!/usr/bin/env python3
"""0.854 : les noyaux de Taranis écrits par vtxc128, joués sur la carte de papier (taranis/interprete.py) : chaque
boucle en segments ci-dessous va à la carte ; le noyau est joué tour par tour, et ce qu'il écrit doit être ce que
Lugus écrit pour la même boucle (le programme sort ensuite chaque mot écrit). Les entiers de 64 bits (Dunon), les
divisions (par une constante, par une variable, signées), les appels (et leurs retours au milieu), le minimum
atomique, et le quaternaire : les logiques et les mots de 32 quits (et4, ou4, non4, anti, fusion, consensus, qegal,
min4, max4, addm4, gdot, selon).

    python3 tests/test_taranis_vtx.py"""
import os
import re
import subprocess
import sys
import tempfile

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, os.path.join(racine, "forge"))
sys.path.insert(0, os.path.join(racine, "taranis"))
import forge_vtx  # noqa: E402
import interprete  # noqa: E402

N = 48
F = 202
ENTETE = f"dunon;\nconstante F = {F};\nconstante N = {N};\n"
SORTIR = "pour j dans 0..N { sortie(@2[(F << 24) + j]); }"

CAS = [
    ("les entiers de 64 bits", "", "@2[(F << 24) + i] = i * 1000003 + (i << 40) - (i ^ 77);"),
    ("les décalages et le signe", "", "soit x = 0 - (i + 1); @2[(F << 24) + i] = (x .>> (i % 7)) + (i << (i % 63)) + (x >> 3);"),
    ("diviser par une constante", "", "soit x = i * 7919 + 13; @2[(F << 24) + i] = x / 7 + x % 10 + x / 1024 + x % 64 + (0 - x) ./ 3 + (0 - x) .% 5;"),
    ("diviser par une variable", "", "soit d = i % 9; soit x = i * 100003; @2[(F << 24) + i] = x / d + x % (d + 3) + (0 - x) ./ (d + 1) + x .% (0 - d - 2);"),
    ("diviser en 64 bits", "", "soit x = (i + 1) << 45; @2[(F << 24) + i] = x / (i + 3) + x % (i * 1000000007 + 1);"),
    ("comparaisons et conditions", "", "soit s = 0; si i < 10 || i > 40 { s = 1; } sinon si (0 - i) .< 0 && i != 20 { s = 2; } "
     "@2[(F << 24) + i] = s + (i >= 30) * 10 + (i == 7) * 100;"),
    ("une boucle dans la boucle", "", "soit s = 0; pour k dans 0..i { s = s + k * k; } soit t = 0; tantque t < 5 { t = t + 1; } "
     "@2[(F << 24) + i] = s + t;"),
    ("un appel, un retour au milieu", "fonction f(x) { si x % 3 == 0 { retour x * 2; } soit y = x; pour k dans 0..4 { "
     "si y > 100 { retour y; } y = y * 3; } retour y + 1; }", "@2[(F << 24) + i] = f(i);"),
    ("lire ce qu'on a écrit avant", "", "@2[(F << 24) + i] = i; @2[(F << 24) + i] = @2[(F << 24) + i] * 3 + 1;"),
    # le quaternaire sur la carte
    ("logiques : et4, ou4, non4, anti, fusion, consensus", "", "soit a = comme_logique(i % 4); soit b = comme_logique((i / 4) % 4); "
     "@2[(F << 24) + i] = entier(et4(a, b)) + 4 * entier(ou4(a, b)) + 16 * entier(non4(a)) + 64 * entier(anti(b)) "
     "+ 256 * entier(fusion(a, b)) + 1024 * entier(consensus(a, b)) + 4096 * entier(logique(i % 3));"),
    ("selon sur la carte", "", "soit l = comme_logique(i % 4); soit r = 0; selon l { vrai { r = 1; } faux { r = 2; } "
     "inconnu { r = 3; } variable { r = 4; } } si l == vrai { r = r + 10; } @2[(F << 24) + i] = r;"),
    ("selon sur un entier (la valeur sue)", "", "soit v = (i % 5) - 3; soit r = 0; selon v { vrai { r = 1; } faux { r = 2; } "
     "inconnu { r = 3; } variable { r = 4; } } @2[(F << 24) + i] = r;"),
    ("les mots de 32 quits", "", "soit x = i * 11400714819323198485; soit y = (i + 7) * 14029467366897019727; "
     "@2[(F << 24) + i] = min4(x, y) ^ (max4(x, y) * 3) ^ (addm4(x, y) * 5) ^ (qegal(x, y) * 7) ^ gdot(x, y) "
     "^ (et4(x, y) * 9) ^ (ou4(x, y) * 11) ^ (non4(x) * 13) ^ (anti(y) * 15) ^ nb_bits(x) ^ (nb_bits(0 - 1) << 50);"),
    ("garder le minimum (atomique)", "", "soit x = (i * 37) % 11; si x < @2[(F << 24) + (i % 4)] { @2[(F << 24) + (i % 4)] = x; }",
     "pour j dans 0..N { @2[(F << 24) + j] = 1000; }"),
]


def lugus(src, d):
    p = os.path.join(d, "p.vtx")
    open(p, "w", encoding="utf-8").write(src)
    r = subprocess.run([forge_vtx.LUGUS, p], capture_output=True, text=True)
    lignes = [x for x in r.stdout.splitlines() if "," in x or x.strip().isdigit()]
    return [int(x) for x in lignes[0].split(",")] if lignes else None, r.stderr


def noyau(rs):
    m = re.search(r"static SPV: \[u32; \d+\] = \[([0-9,]+)\];", rs)
    ext = re.search(r"taranis_boucle_pages\(c, &\[\], &\[\], &SPV, ta, tb, &\[([^\]]*)\]", rs)
    refus = re.findall(r"// taranis : la boucle de la ligne \d+ reste aux cœurs : (.*)", rs)
    if not m:
        return None, None, refus
    return [int(x) for x in m.group(1).split(",")], [x.strip() for x in ext.group(1).split(",") if x.strip()], refus


ok = True
d = tempfile.mkdtemp(prefix="taranis-vtx-")
for cas in CAS:
    nom, fonctions, corps = cas[0], cas[1], cas[2]
    avant = cas[3] if len(cas) > 3 else ""
    src = (ENTETE + fonctions + "\nfonction principal() { " + avant + " pour i dans 0..N en segments { " + corps + " } "
           + SORTIR + " }\n")
    attendu, err = lugus(src, d)
    rs, _ = forge_vtx.passer_vtxc128(src, d)
    mots, ext, refus = noyau(rs or "")
    if mots is None:
        ok = False
        print(f"ÉCHEC {nom} : pas de noyau ({refus[:1] or (rs or '')[:200]})")
        continue
    if ext:
        ok = False
        print(f"ÉCHEC {nom} : des variables d'avant la boucle ({ext}) : le test ne sait pas les donner")
        continue
    # le monde : la fréquence F d'un seul tenant (sa place, sa taille) ; ce que la boucle trouve en entrant
    fenetre = {}
    if avant:
        for j in range(N):
            fenetre[(F << 24) + j] = 1000
    table = [0] * 512
    table[F] = (F << 24) & 0xFFFFFFFF
    table[256 + F] = 1 << 24
    params = [0] * 64
    params[1], params[2], params[5] = 0, N, N
    try:
        interprete.jouer(mots, fenetre, params, table, N)
    except Exception as x:
        ok = False
        print(f"ÉCHEC {nom} : la carte de papier : {type(x).__name__} {x}")
        continue
    obtenu = [fenetre.get((F << 24) + j, 0) for j in range(N)]
    bon = attendu is not None and obtenu == attendu and params[0] == 0
    ok &= bon
    print(("OK   " if bon else "ÉCHEC ") + f"{nom} : {len(mots)} mots de SPIR-V" + ("" if bon else
          f" ; Lugus {attendu[:6] if attendu else err[-200:]} ; la carte {obtenu[:6]} ; drapeau {params[0]}"))
print("Taranis écrit par vtxc128, joué sur la carte de papier : tout est conforme" if ok else "des écarts")
sys.exit(0 if ok else 1)
