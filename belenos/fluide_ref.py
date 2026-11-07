#!/usr/bin/env python3
"""La référence du fluide (Boltzmann sur réseau, D2Q9) : la même arithmétique entière que belenos/fluide_*.vtx (entiers
de 64 bits, divisions signées tronquées vers zéro, décalages arithmétiques), pour vérifier Lugus et, plus tard, la carte
graphique ; et une image du tourbillonnement (la vorticité) après un temps long.

    python3 belenos/fluide_ref.py [PAS] [image.png]"""
import sys

E = [(0, 0), (1, 0), (0, 1), (-1, 0), (0, -1), (1, 1), (-1, 1), (-1, -1), (1, -1)]
W = [16, 4, 4, 4, 4, 1, 1, 1, 1]
NX, NY = 128, 64
N = NX * NY
M64 = (1 << 64) - 1


def s64(x):
    x &= M64
    return x - (1 << 64) if x >> 63 else x


def divs(a, b):
    a, b = s64(a), s64(b)
    q = abs(a) // abs(b)
    return s64(q if (a >= 0) == (b >= 0) else -q)


def sar(a, k):
    return s64(a) >> k


def equilibre(rho, ux, uy, f=None):
    usq = sar(ux * ux + uy * uy, 24)
    r36 = divs(rho, 36)
    g = [0] * 9
    for i in range(1, 9):
        eu = E[i][0] * ux + E[i][1] * uy
        t = 16777216 + 3 * eu + sar(9 * eu * eu, 25) - sar(3 * usq, 1)
        q = sar(W[i] * r36 * t, 24)
        g[i] = q if f is None else s64(f[i] + sar((q - f[i]) * 31, 4))
    g[0] = s64(rho - sum(g[1:]))
    return g


def collision(f):
    rho = s64(sum(f))
    jx = f[1] - f[3] + f[5] - f[6] - f[7] + f[8]
    jy = f[2] - f[4] + f[5] + f[6] - f[7] - f[8]
    ux, uy = divs(jx << 24, rho), divs(jy << 24, rho)
    return equilibre(rho, ux, uy, f)


def depart():
    pops = []
    for c in range(N):
        x, y = c % NX, c // NX
        ux = -1342177 if (y < 16 or y >= 48) else 1342177
        tri = x % 64
        if tri >= 32:
            tri = 64 - tri
        uy = (tri - 16) * 5120
        pops.append(equilibre(16777216, ux, uy))
    return pops


def pas(pops):
    neuf = [[0] * 9 for _ in range(N)]
    for c in range(N):
        g = collision(pops[c])
        for i in range(9):
            neuf[(c + E[i][0] + E[i][1] * NX) % N][i] = g[i]
    return neuf


def empreinte(pops):
    masse, h = 0, 0
    for c, f in enumerate(pops):
        masse += sum(f)
        h = ((h ^ ((f[0] + 3 * f[1] + 5 * f[2] + 7 * f[3] + 11 * f[4] + 13 * f[5] + 17 * f[6] + 19 * f[7] + 23 * f[8] + c) & M64))
             * 1099511628211) & M64
    return masse & M64, h


def vitesses(pops):
    u = []
    for f in pops:
        rho = sum(f)
        u.append(((f[1] - f[3] + f[5] - f[6] - f[7] + f[8]) / rho, (f[2] - f[4] + f[5] + f[6] - f[7] - f[8]) / rho))
    return u


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    p = depart()
    for _ in range(n):
        p = pas(p)
    print(*empreinte(p), sep=",")
    if len(sys.argv) > 2:
        from PIL import Image
        u = vitesses(p)
        w = [0.0] * N        # la vorticité : dv/dx - du/dy
        for c in range(N):
            x, y = c % NX, c // NX
            w[c] = (u[y * NX + (x + 1) % NX][1] - u[y * NX + (x - 1) % NX][1]) - (u[((y + 1) % NY) * NX + x][0] - u[((y - 1) % NY) * NX + x][0])
        m = max(abs(v) for v in w) or 1
        img = Image.new("RGB", (NX, NY))
        for c in range(N):
            v = w[c] / m
            img.putpixel((c % NX, c // NX), (int(255 * max(v, 0)), int(255 * (1 - abs(v)) * 0.25), int(255 * max(-v, 0))))
        img.resize((NX * 6, NY * 6), Image.NEAREST).save(sys.argv[2])
        print("vorticité max", m)
