#!/usr/bin/env python3
"""Fabrique les deux versions du fluide (Boltzmann sur réseau, D2Q9, entiers à virgule fixe 24 bits), qui ne diffèrent
que par la propagation : fluide_copie.vtx (A : les populations sont poussées dans la cellule voisine, deux tampons) et
fluide_tapis.vtx (B : le tapis roulant, un seul tampon ; chaque direction a son origine, qui recule d'un cran à chaque
pas : aucune donnée ne bouge). La collision est la même, écrite une fois ici.

    python3 belenos/fabriquer_fluide.py"""
import os

ici = os.path.dirname(os.path.abspath(__file__))
E = [(0, 0), (1, 0), (0, 1), (-1, 0), (0, -1), (1, 1), (-1, 1), (-1, -1), (1, -1)]
W = [16, 4, 4, 4, 4, 1, 1, 1, 1]          # les poids, sur 36
NX, NY, PAS = 128, 64, 50
N = NX * NY


def produit(k, a):
    """k * a pour un petit entier k (-1, 0, 1), écrit sans multiplication"""
    return {1: f"{a}", -1: f"(0 - {a})", 0: "0"}[k]


def collision(indent):
    """f0..f8 -> g0..g8 : BGK, ω = 31/16 (peu visqueux : un nombre de Reynolds d'environ 240) ; la masse est gardée
    exactement (g0 la complète)"""
    p = " " * indent
    l = [f"{p}soit rho = f0 + f1 + f2 + f3 + f4 + f5 + f6 + f7 + f8;",
         f"{p}soit jx = f1 - f3 + f5 - f6 - f7 + f8;",
         f"{p}soit jy = f2 - f4 + f5 + f6 - f7 - f8;",
         f"{p}soit ux = (jx << 24) ./ rho;",
         f"{p}soit uy = (jy << 24) ./ rho;",
         f"{p}soit usq = (ux * ux + uy * uy) .>> 24;",
         f"{p}soit r36 = rho ./ 36;"]
    for i in range(1, 9):
        ex, ey = E[i]
        eu = " + ".join(x for x in (produit(ex, "ux") if ex else "", produit(ey, "uy") if ey else "") if x)
        l += [f"{p}soit eu{i} = {eu};",
              f"{p}soit t{i} = 16777216 + 3 * eu{i} + ((9 * eu{i} * eu{i}) .>> 25) - ((3 * usq) .>> 1);",
              f"{p}soit q{i} = ({W[i]} * r36 * t{i}) .>> 24;",
              f"{p}soit g{i} = f{i} + (((q{i} - f{i}) * 31) .>> 4);"]
    l.append(f"{p}soit g0 = rho - (g1 + g2 + g3 + g4 + g5 + g6 + g7 + g8);")
    return "\n".join(l)


def equilibre(indent):
    """rho, ux, uy (déjà posés) -> g0..g8 à l'équilibre (le départ)"""
    p = " " * indent
    l = [f"{p}soit usq = (ux * ux + uy * uy) .>> 24;", f"{p}soit r36 = rho ./ 36;"]
    for i in range(1, 9):
        ex, ey = E[i]
        eu = " + ".join(x for x in (produit(ex, "ux") if ex else "", produit(ey, "uy") if ey else "") if x)
        l += [f"{p}soit eu{i} = {eu};",
              f"{p}soit t{i} = 16777216 + 3 * eu{i} + ((9 * eu{i} * eu{i}) .>> 25) - ((3 * usq) .>> 1);",
              f"{p}soit g{i} = ({W[i]} * r36 * t{i}) .>> 24;"]
    l.append(f"{p}soit g0 = rho - (g1 + g2 + g3 + g4 + g5 + g6 + g7 + g8);")
    return "\n".join(l)


def decalage(i):
    ex, ey = E[i]
    return (ex + ey * NX) % N


def entete():
    return f"""// Le fluide (Boltzmann sur réseau, D2Q9) : {NX} × {NY} cellules, bouclé, en entiers à virgule fixe (24 bits) ;
// une couche de cisaillement (deux courants opposés, une petite perturbation) : des tourbillons doivent naître.
// Fabriqué par belenos/fabriquer_fluide.py (la collision est la même dans les deux versions).
constante NX = {NX};
constante N = {N};
constante Y1 = {NY // 4};
constante Y3 = {3 * NY // 4};
constante MASQUE = {N - 1};
constante PAS = {PAS};
"""

DEPART = """// le départ : la densité 1 partout, ±0,08 selon la rangée, une petite onde en triangle en y
fonction depart(base) {
    pour c0 dans 0..N {
        soit x = c0 % NX;
        soit y = c0 / NX;
        soit rho = 16777216;
        soit ux = 1342177;
        si y < Y1 || y >= Y3 {
            ux = 0 - 1342177;
        }
        soit tri = x % 64;
        si tri >= 32 {
            tri = 64 - tri;
        }
        soit uy = (tri - 16) * 5120;
EQUILIBRE
        POSER
    }
}

"""

FIN = """// le compte : la masse, et une empreinte de toutes les populations (chaque cellule logique, chaque direction)
fonction compte(src) {
    soit masse = 0;
    soit empreinte = 0;
    pour c2 dans 0..N {
LIRE_FIN
        masse = masse + f0 + f1 + f2 + f3 + f4 + f5 + f6 + f7 + f8;
        empreinte = (empreinte ^ (f0 + 3 * f1 + 5 * f2 + 7 * f3 + 11 * f4 + 13 * f5 + 17 * f6 + 19 * f7 + 23 * f8 + c2)) * 1099511628211;
    }
    sortie(masse);
    sortie(empreinte);
}
"""


def copie():
    s = entete() + f"""// A, la copie : chaque cellule pousse ses populations dans la voisine (deux tampons, F0 et F1, qui alternent).
constante F0 = 0;
constante F1 = {9 * N};

""" + DEPART.replace("EQUILIBRE", equilibre(8)).replace("POSER", "\n        ".join(
        f"@2[base + {i * N} + c0] = g{i};" for i in range(9))) + FIN.replace("LIRE_FIN", "\n".join(
        f"        soit f{i} = @2[src + {i * N} + c2];" for i in range(9))) + """
fonction principal() {
    depart(F0);
    soit src = F0;
    soit dst = F1;
    pour t dans 0..PAS {
        pour c dans 0..N {
""" + "\n".join(f"            soit f{i} = @2[src + {i * N} + c];" for i in range(9)) + "\n" + collision(12) + "\n" + "\n".join(
        f"            @2[dst + {i * N} + ((c + {decalage(i)}) & MASQUE)] = g{i};" for i in range(9)) + """
        }
        soit e = src;
        src = dst;
        dst = e;
    }
    compte(src);
}
"""
    return s


def tapis():
    s = entete() + f"""// B, le tapis roulant : un seul tampon ; la direction i de la cellule logique c est rangée en (c + o_i) mod N, et
// o_i recule de son décalage à chaque pas : la propagation ne déplace aucune donnée.
constante F = 0;
constante ORIGINES = {9 * N};

""" + DEPART.replace("EQUILIBRE", equilibre(8)).replace("POSER", "\n        ".join(
        f"@2[base + {i * N} + c0] = g{i};" for i in range(9))) + FIN.replace("LIRE_FIN", "\n".join(
        f"        soit f{i} = @2[src + {i * N} + ((c2 + @2[ORIGINES + {i}]) & MASQUE)];" for i in range(9))) + """
fonction principal() {
    depart(F);
""" + "\n".join(f"    soit o{i} = 0;" for i in range(9)) + """
    pour t dans 0..PAS {
        pour c dans 0..N {
""" + "\n".join(f"            soit a{i} = F + {i * N} + ((c + o{i}) & MASQUE);" for i in range(9)) + "\n" + "\n".join(
        f"            soit f{i} = @2[a{i}];" for i in range(9)) + "\n" + collision(12) + "\n" + "\n".join(
        f"            @2[a{i}] = g{i};" for i in range(9)) + "\n        }\n" + "\n".join(
        f"        o{i} = (o{i} + {(N - decalage(i)) % N}) & MASQUE;" for i in range(9)) + """
    }
""" + "\n".join(f"    @2[ORIGINES + {i}] = o{i};" for i in range(9)) + """
    compte(F);
}
"""
    return s


def tuiles(tx=32, ty=16, par_vague=4):
    """C, les tuiles : la grille découpée en tuiles de tx × ty cellules ; chaque tuile a son ombre (ses cellules et une
    marge d'une cellule prise chez les voisines, bouclée comme les autres versions : la voisine de droite de la
    dernière cellule d'une rangée est la première de la rangée suivante), où la collision est faite ; la propagation lit l'ombre (chaque
    cellule tire ses populations des voisines de l'ombre) et écrit le tampon d'arrivée. Les ombres sont rangées côte à
    côte ; les tuiles sont calculées par vagues de par_vague, dans un ordre qui n'est pas celui de la grille : les
    nombres sont les mêmes quel que soit l'ordre (chaque tuile ne lit que le tampon de départ)."""
    lx, ly = tx + 2, ty + 2
    lxy = lx * ly
    nt = (NX // tx) * (NY // ty)
    saut = next(k for k in range(nt // 2 + 1, nt) if __import__("math").gcd(k, nt) == 1)
    s = entete() + f"""// C, les tuiles : {NX // tx} × {NY // ty} tuiles de {tx} × {ty} cellules, chacune avec son ombre (la tuile et une
// marge d'une cellule) ; les ombres côte à côte, calculées par vagues de {par_vague} tuiles, dans le désordre.
constante F0 = 0;
constante F1 = {9 * N};
constante OMBRES = {18 * N};
constante TX = {tx};
constante TY = {ty};
constante LX = {lx};
constante LY = {ly};
constante TUX = {NX // tx};
constante NT = {nt};
constante VAGUE = {par_vague};

""" + DEPART.replace("EQUILIBRE", equilibre(8)).replace("POSER", "\n        ".join(
        f"@2[base + {i * N} + c0] = g{i};" for i in range(9))) + FIN.replace("LIRE_FIN", "\n".join(
        f"        soit f{i} = @2[src + {i * N} + c2];" for i in range(9))) + f"""
// une tuile : la collision dans son ombre (la tuile et sa marge), puis la propagation de l'ombre vers le tampon dst
fonction tuile(t, src, dst) {{
    soit bx = (t % TUX) * TX;
    soit by = (t / TUX) * TY;
    soit om = OMBRES + t * {9 * lxy};
    pour oy dans 0..LY {{
        pour ox dans 0..LX {{
            soit c = ((by + oy - 1) * NX + bx + ox - 1 + N) & MASQUE;
""" + "\n".join(f"            soit f{i} = @2[src + {i * N} + c];" for i in range(9)) + "\n" + collision(12) + "\n" + \
        "            soit l = oy * LX + ox;\n" + "\n".join(
        f"            @2[om + {i * lxy} + l] = g{i};" for i in range(9)) + """
        }
    }
    pour py dans 1..LY - 1 {
        pour px dans 1..LX - 1 {
            soit d = (by + py - 1) * NX + bx + px - 1;
            soit m = om + py * LX + px;
""" + "\n".join(
        f"            @2[dst + {i * N} + d] = @2[m + {i * lxy - (E[i][0] + E[i][1] * lx)}];" for i in range(9)) + f"""
        }}
    }}
}}

fonction principal() {{
    depart(F0);
    soit src = F0;
    soit dst = F1;
    pour t dans 0..PAS {{
        // les vagues : VAGUE tuiles à la fois ; la tuile n° (k · {saut}) mod NT, un ordre qui n'est pas celui de la grille
        pour v dans 0..NT / VAGUE {{
            pour k dans 0..VAGUE {{
                tuile(((v * VAGUE + k) * {saut}) % NT, src, dst);
            }}
        }}
        soit e = src;
        src = dst;
        dst = e;
    }}
    compte(src);
}}
"""
    return s


def regler(nx, ny, pas):
    """la taille de la grille (nx · ny une puissance de 2) et le nombre de pas"""
    global NX, NY, PAS, N
    NX, NY, PAS, N = nx, ny, pas, nx * ny


if __name__ == "__main__":
    for nom, texte in (("fluide_copie.vtx", copie()), ("fluide_tapis.vtx", tapis()), ("fluide_tuiles.vtx", tuiles())):
        open(os.path.join(ici, nom), "w", encoding="utf-8").write(texte)
        print(nom, len(texte.splitlines()), "lignes")
