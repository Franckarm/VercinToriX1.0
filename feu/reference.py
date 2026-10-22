"""Référence Python indépendante de la scène du feu de camp (scene.vtx) et de l'analyse des voxels (analyse.vtx)."""
import numpy as np

M32 = 0xFFFFFFFF
N = 128
PIERRES = [(90, 10, 69, 6, 4, 5), (84, 10, 84, 7, 6, 5), (71, 10, 92, 8, 5, 5), (55, 10, 89, 6, 4, 5),
           (42, 10, 81, 7, 6, 5), (35, 10, 66, 8, 5, 5), (40, 10, 51, 6, 4, 5), (50, 10, 40, 7, 6, 5),
           (66, 10, 35, 8, 5, 5), (80, 10, 42, 6, 4, 5), (90, 10, 54, 7, 6, 5)]
BUCHES = [(81, 10, 73, 62, 44, 65), (60, 10, 83, 62, 44, 63), (45, 10, 66, 65, 44, 62), (56, 10, 47, 66, 44, 64),
          (78, 10, 51, 65, 44, 66)]


def hache(x, y, z):
    h = ((x * 73856093) ^ (y * 19349663) ^ (z * 83492791)) & M32
    h ^= h >> 13
    h = (h * 1274126177) & M32
    return h ^ (h >> 16)


def voxel(m, v, c, a):
    return ((m << 24) | ((v & 255) << 16) | ((c & 255) << 8) | (a & 255)) & M32


DEFAUT = [46, 13, 128, 0, 141, 128, 4, 3]


def scene(params=None, image=0):
    """Scène du feu ; params : les 8 paramètres du feu (hauteur, rayon, penchant, montée, puissance, teinte, seuil,
    balancement), image : numéro de l'image (montée des langues et de la fumée)."""
    p = params or DEFAUT
    vol = np.zeros(N ** 3, dtype=np.uint32)
    blocs = np.zeros(4096, dtype=np.uint32)

    def poser(x, y, z, m):
        vol[(z * N + y) * N + x] = m
        blocs[((z >> 3) * 16 + (y >> 3)) * 16 + (x >> 3)] = 1

    def plein(x, y, z):
        return (int(vol[(z * N + y) * N + x]) & 255) >= 128

    for z in range(N):
        for x in range(N):
            h = 10
            d2 = (x - 64) ** 2 + (z - 64) ** 2
            m = 2 if d2 < 576 else 1
            v = hache(x, 1, z) & 31
            for y in range(h):
                poser(x, y, z, voxel(m, v, 0, 255))
    for cx, cy, cz, rx, ry, rz in PIERRES:
        r2 = rx * rx * ry * ry * rz * rz
        for z in range(cz - rz, cz + rz + 1):
            for y in range(cy - ry, cy + ry + 1):
                for x in range(cx - rx, cx + rx + 1):
                    dx, dy, dz = abs(x - cx), abs(y - cy), abs(z - cz)
                    val = dx * dx * ry * ry * rz * rz + dy * dy * rx * rx * rz * rz + dz * dz * rx * rx * ry * ry
                    h = hache(x, y, z)
                    if val <= (r2 * (28 + (h & 7))) // 32:
                        poser(x, y, z, voxel(3, h >> 8, 0, 255))
    for bx, by, bz, ax, ay, az in BUCHES:
        ux, uy, uz = ax - bx, ay - by, az - bz
        l2 = ux * ux + uy * uy + uz * uz
        for z in range(min(bz, az) - 4, max(bz, az) + 5):
            for y in range(by - 4, ay + 5):
                for x in range(min(bx, ax) - 4, max(bx, ax) + 5):
                    px, py, pz = x - bx, y - by, z - bz
                    tn = px * ux + py * uy + pz * uz
                    if 0 <= tn <= l2:
                        perp = (px * px + py * py + pz * pz) * l2 - tn * tn
                        if perp <= 9 * l2:
                            h = hache(x, y, z)
                            frac = tn * 100 // l2
                            m, c = 4, 0
                            if frac < 30:
                                m = 5
                                if (h & 7) == 0 and perp >= 4 * l2:
                                    m, c = 6, 160 + ((h >> 8) & 63)
                            poser(x, y, z, voxel(m, h >> 16, c, 255))
    for z in range(53, 76):
        for y in range(9, 13):
            for x in range(53, 76):
                d2 = (x - 64) ** 2 + (z - 64) ** 2
                h = hache(x, y, z)
                if d2 < 121 and (y < 11 or (h & 3) != 0):
                    m, c = 5, 0
                    if h & 1:
                        m, c = 6, 200 + ((h >> 8) & 55) - y * 4
                    poser(x, y, z, voxel(m, h >> 16, c, 255))
    for z in range(43, 58):
        for y in range(10, 20):
            for x in range(97, 112):
                d2 = (x - 104) ** 2 + (z - 50) ** 2
                if d2 <= 49 and not (y >= 12 and d2 <= 25):
                    poser(x, y, z, voxel(7, hache(x, y, z) >> 20, 0, 255))
    glisse = image * p[3]
    for y in range(12, 12 + p[0]):
        hh = y - 12
        r = p[1] - hh * 2 // 7
        penche = int((hh * hh * (p[2] - 128)) / 8192)          # division signée vers zéro, comme ./
        yy = (y - glisse) & M32
        cx = 63 + (((hache(1, yy >> 2, 7) >> 5) & 3) * p[7]) // 3 + penche
        cz = 63 + ((hache(2, yy >> 2, 9) >> 5) & 3)
        if r > 0:
            r2 = r * r
            for z in range(cz - r, cz + r + 1):
                for x in range(cx - r, cx + r + 1):
                    d2 = (x - cx) ** 2 + (z - cz) ** 2
                    n = hache(x >> 1, yy >> 2, z >> 1) & 255
                    if d2 < r2 and n > hh * p[6] and not plein(x, y, z):
                        dens = 20 + (r2 - d2) * 90 // r2
                        chaud = min(max(255 - hh * 3 - d2 * 60 // r2 + p[5] - 128, 0), 255)
                        poser(x, y, z, voxel(8, n, chaud, dens))
    for y in range(60, 127):
        hh = y - 60
        r = 5 + hh // 5
        cx, cz = 64 + hh // 4 + int((hh * (p[2] - 128)) / 256), 64 + hh // 10
        r2 = r * r
        for z in range(cz - r, cz + r + 1):
            for x in range(cx - r, cx + r + 1):
                d2 = (x - cx) ** 2 + (z - cz) ** 2
                n = hache(x >> 2, ((y - image * 2) & M32) >> 2, z >> 2) & 255
                if d2 < r2 and n < 140 and (int(vol[(z * N + y) * N + x]) & 255) == 0:
                    dens = 8 + (n & 15)
                    dens = dens - hh // 8 if dens > hh // 8 + 2 else 2
                    poser(x, y, z, voxel(9, n, 0, dens))
    return vol, blocs


def somme_scene(vol):
    s, compte = 0, 0
    for v in np.nonzero(vol)[0]:
        s = (s * 31 + int(vol[v]) + int(v)) & M32
        compte += 1
    return compte, s


# --- la mémoire du cube qui anime le feu (anime.vtx)
CLES = [0x78806428, 0xC880AA78, 0xAA288CC8, 0xAADC8CC8, 0x50803214, 0xFA80E6A0]
VALEURS1 = [0x280C8002, 0x320D8003, 0x2C0D4C03, 0x2C0DB403, 0x1A0B8001, 0x3C0E8004]
VALEURS2 = [0x6E760503, 0x9C8A0403, 0x85800403, 0x85800403, 0x4E620601, 0xCB940303]


def voies(m):
    return [(m >> 24) & 255, (m >> 16) & 255, (m >> 8) & 255, m & 255]


def triangle(f, p):
    m = f % (2 * p)
    return abs(m - p) * 255 // p


def requete(f):
    r = 110 + triangle(f + 5, 13) * 130 // 255
    v = 40 + triangle(f, 29) * 176 // 255
    b = 90 + (hache(f >> 1, 3, 5) & 127)
    a = 40 + (hache(f, 7, 1) & 191)
    return (r << 24) | (v << 16) | (b << 8) | a


def rappeler(q):
    poids = []
    for c in CLES:
        d = sum((x - y) ** 2 for x, y in zip(voies(q), voies(c))) >> 11
        poids.append(65536 >> d if d < 16 else 0)
    total = sum(poids) or 1
    vals = [voies(a) + voies(b) for a, b in zip(VALEURS1, VALEURS2)]
    return [sum(w * v[p] for w, v in zip(poids, vals)) // total for p in range(8)]
