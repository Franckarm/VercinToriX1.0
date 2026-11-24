/* Belenos : l'épreuve de Gergovie (0.823), écrite en C++ pour comparer : la plaine auvergnate, le puy, le lac, le camp
 * romain, les armées (gergovie_scene.vtx), entier pour entier : la même empreinte. Les images sont calculées, pas
 * montrées ; les rangées sur tous les cœurs (OpenMP : schedule dynamic).
 *     cl /nologo /O2 /openmp /EHsc /TP gergovie_ref.cpp          (Windows, le compilateur de Microsoft)
 *     g++ -O2 -fopenmp -o gergovie_ref belenos/gergovie_ref.cpp
 *     GERGOVIE_VOL=240 GERGOVIE_JOUR=120 ./gergovie_ref
 * Les opérations de vtx : / % < > sans signe ; ./ .>> .< .> avec signe ; tout sur 64 bits, en enveloppant. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <algorithm>

#ifndef RN
#define RN 1
#endif
#ifndef RD
#define RD 1
#endif
#ifndef TOURNE
#define TOURNE 0
#endif

typedef uint64_t u;
typedef int64_t s;

/* 0.815 : -DMOT16 : chaque mot du monde (annuaires, réserves, calques) sur 16 octets, comme les mots de Lugus (le
 * diagnostic : ce que coûte à 24 fils la mémoire deux fois plus grosse) ; sinon 8 octets */
#ifdef MOT16
#define PAS 2
#else
#define PAS 1
#endif
#define IX(i) ((i) * PAS)

/* le compilateur de Microsoft (cl /O2 /openmp) n'a pas clock_gettime : l'horloge du C11 */
#ifdef _MSC_VER
#define clock_gettime(c, t) timespec_get((t), TIME_UTC)
#endif

#ifndef W
#define W 1280
#endif
#ifndef H
#define H 720
#endif
#define TUILES ((u)2 * RN / RD)
#define MONDE ((u)256 * TUILES)
#define MASQ (MONDE - 1)
#define NB (MONDE / 8)
#define REP 32768
#define MER ((u)44 * RN / RD)
#define VIDE ((u)1 << 63)
#define LOIN 8
#define MANQUE ((u)1 << 62)
#define ROCHE 1
#define HERBE 2
#define NEIGE 3
#define SABLE 4
#define EAU 5
#define TERRE 6
#define LANDE 7
#define PIERRE 8
#define TUILE 9
#define MARBRE 10
#define ROMAIN 11
#define GAULOIS 12
#define ECU_ROMAIN 13
#define ECU_GAULOIS 14
#define METAL 15
#define BOIS 16
#define PEAU 17
#define CHEVEUX 18
#define BRAIES 19
#define TOILE 20
#define SCORIE 21
#define PUY_X ((u)256 * RN / RD)
#define PUY_Z ((u)70 * RN / RD)
#define PUY_R ((u)125 * RN / RD)
#define LAC_X ((u)300 * RN / RD)
#define LAC_Z ((u)245 * RN / RD)
#define LAC_RX ((u)112 * RN / RD)
#define LAC_RZ ((u)70 * RN / RD)
#define CAMP_X0 ((u)140 * RN / RD)
#define CAMP_X1 ((u)200 * RN / RD)
#define CAMP_Z0 ((u)310 * RN / RD)
#define CAMP_Z1 ((u)350 * RN / RD)
#define ARM_X0 ((u)136 * RN / RD)
#define ARM_X1 ((u)196 * RN / RD)
#define ARM_Z0 ((u)386 * RN / RD)
#define ARM_Z1 ((u)434 * RN / RD)
#define P3 ((u)16 * RN / RD)
#define UN (((u)RN + RD - 1) / RD)

static inline u sdiv(u a, u b) { return (u)((s)a / (s)b); }
static inline u sar(u a, int n) { return (u)((s)a >> n); }
static inline int slt(u a, u b) { return (s)a < (s)b; }

static u SINUS[1024], *HCOL, *PENTE, GLOB[64], SOLEILS[16];
static u *DIRE[16], *DIRT[16], *POOLE[16], *POOLT[16], *CIELC[16], *SOLC[16], *CREUX[16];
static u *DISTA, *DISTB;
static u ECRAN[W * H];
static u COMPTE[4 * H];

static u racine_entiere(u x) {
    u r = 0, v = x, b = (u)1 << 62;
    while (b > v) b >>= 2;
    while (b != 0) {
        if (v >= r + b) { v -= r + b; r = (r >> 1) + b; } else r >>= 1;
        b >>= 2;
    }
    return r;
}

static void preparer_sinus(void) {
    for (u a = 0; a < 1024; a++) {
        u x = a & 511;
        u v = 4 * x * (512 - x) * 65536 / (327680 - x * (512 - x));
        SINUS[a] = a >= 512 ? 0 - v : v;
    }
}
static inline u sin1024(u a) { return SINUS[a & 1023]; }
static inline u cos1024(u a) { return SINUS[(a + 256) & 1023]; }

static inline u hache(u x, u z) {
    u h = (x & 4095) * 374761393 + (z & 4095) * 668265263 + 1013904223;
    h = (h ^ (h >> 13)) * 1274126177;
    return (h ^ (h >> 16)) & 65535;
}
static inline u hache3(u x, u y, u z) {
    u h = (x & 1023) * 374761393 + (y & 1023) * 668265263 + (z & 1023) * 2246822519u + 1013904223;
    h = (h ^ (h >> 13)) * 1274126177;
    return (h ^ (h >> 16)) & 65535;
}
static u bruit_lisse(u x, u z, u p) {
    u x0 = x / p, z0 = z / p, fx = (x % p) * 256 / p, fz = (z % p) * 256 / p;
    u sx = fx * fx * (768 - 2 * fx) / 65536, sz = fz * fz * (768 - 2 * fz) / 65536;
    u n = MONDE / p;
    u a = hache(x0 % n, z0 % n), b = hache((x0 + 1) % n, z0 % n), c = hache(x0 % n, (z0 + 1) % n),
      d = hache((x0 + 1) % n, (z0 + 1) % n);
    u h1 = (a * (256 - sx) + b * sx) / 256, h2 = (c * (256 - sx) + d * sx) / 256;
    return (h1 * (256 - sz) + h2 * sz) / 256;
}
static u bruit3(u x, u y, u z) {
    u x0 = x / P3, y0 = y / P3, z0 = z / P3;
    u fx = (x % P3) * 256 / P3, fy = (y % P3) * 256 / P3, fz = (z % P3) * 256 / P3;
    u sx = fx * fx * (768 - 2 * fx) / 65536, sy = fy * fy * (768 - 2 * fy) / 65536, sz = fz * fz * (768 - 2 * fz) / 65536;
    u a0 = (hache3(x0, y0, z0) * (256 - sx) + hache3(x0 + 1, y0, z0) * sx) / 256;
    u a1 = (hache3(x0, y0 + 1, z0) * (256 - sx) + hache3(x0 + 1, y0 + 1, z0) * sx) / 256;
    u a2 = (hache3(x0, y0, z0 + 1) * (256 - sx) + hache3(x0 + 1, y0, z0 + 1) * sx) / 256;
    u a3 = (hache3(x0, y0 + 1, z0 + 1) * (256 - sx) + hache3(x0 + 1, y0 + 1, z0 + 1) * sx) / 256;
    u b0 = (a0 * (256 - sy) + a1 * sy) / 256, b1 = (a2 * (256 - sy) + a3 * sy) / 256;
    return (b0 * (256 - sz) + b1 * sz) / 256;
}

/* un puy (en 1/256 de point) */
static u puy(u x, u z, u cx, u cz, u r, u h, u rc) {
    u ax = x - cx, az = z - cz;
    u d = racine_entiere((ax * ax + az * az) * 65536);
    if (d >= r * 256) return 0;
    u uu = ((r * 256 - d) * 65536) / (r * 256);
    u hp = ((h * 256 * uu) >> 16) * (uu + 32768) / 98304;
    if (rc > 0 && d < rc * 256) hp = hp - (rc * 256 - d) * 2;
    return hp;
}

static u aplanir(u h, u x, u z, u x0, u x1, u z0, u z1, u hp) {
    u dx = 0, dz = 0;
    if (x < x0) dx = x0 - x; else if (x > x1) dx = x - x1;
    if (z < z0) dz = z0 - z; else if (z > z1) dz = z - z1;
    u k = dx > dz ? dx : dz;
    if (k >= 8) return h;
    return (hp * (8 - k) + h * k) / 8;
}

static void creer_sol(void) {
    for (u z = 0; z < MONDE; z++)
        for (u x = 0; x < MONDE; x++) {
            u b1 = bruit_lisse(x, z, (u)128 * RN / RD), b2 = bruit_lisse(x, z, (u)32 * RN / RD);
            u hs = 52 * 256 + sdiv((b1 - 32768) * 3, 64) + sdiv(b2 - 32768, 128);
            u p = puy(x, z, PUY_X, PUY_Z, PUY_R, 138, (u)20 * RN / RD);
            p = p + puy(x, z, (u)70 * RN / RD, (u)120 * RN / RD, (u)70 * RN / RD, 62, (u)7 * RN / RD);
            p = p + puy(x, z, (u)445 * RN / RD, (u)105 * RN / RD, (u)58 * RN / RD, 50, 0);
            if (p > 0) {
                p = p + sdiv((bruit_lisse(x, z, (u)16 * RN / RD) - 32768) * (p >> 6), 32768);
                if (slt(p, 0)) p = 0;
            }
            hs = hs + p;
            u ex = sdiv((x - LAC_X) * 65536, LAC_RX), ez = sdiv((z - LAC_Z) * 65536, LAC_RZ);
            u e = racine_entiere(ex * ex + ez * ez);
            if (e < 65536) {
                u f = 65536 - e;
                hs = hs - (22 * 256 * ((f * (131072 - f)) >> 16)) / 65536;
            }
            HCOL[z * MONDE + x] = (hs * RN) / RD;
        }
    GLOB[30] = HCOL[((CAMP_Z0 + CAMP_Z1) / 2) * MONDE + (CAMP_X0 + CAMP_X1) / 2];
    GLOB[31] = HCOL[((ARM_Z0 + ARM_Z1) / 2) * MONDE + (ARM_X0 + ARM_X1) / 2];
    for (u z = 0; z < MONDE; z++)
        for (u x = 0; x < MONDE; x++) {
            u h = HCOL[z * MONDE + x];
            h = aplanir(h, x, z, CAMP_X0, CAMP_X1, CAMP_Z0, CAMP_Z1, GLOB[30]);
            h = aplanir(h, x, z, ARM_X0, ARM_X1, ARM_Z0, ARM_Z1, GLOB[31]);
            HCOL[z * MONDE + x] = h;
        }
    for (u z = 0; z < MONDE; z++)
        for (u x = 0; x < MONDE; x++) {
            u hx1 = HCOL[z * MONDE + ((x + 1) & MASQ)], hx0 = HCOL[z * MONDE + ((x + MASQ) & MASQ)];
            u hz1 = HCOL[((z + 1) & MASQ) * MONDE + x], hz0 = HCOL[((z + MASQ) & MASQ) * MONDE + x];
            u p = (hx1 > hx0 ? hx1 - hx0 : hx0 - hx1) + (hz1 > hz0 ? hz1 - hz0 : hz0 - hz1);
            PENTE[z * MONDE + x] = p / 2;
        }
    u haut = 0;
    for (u i = 0; i < MONDE * MONDE; i++) if (HCOL[i] > haut) haut = HCOL[i];
    haut = haut / 256 + (u)12 * RN / RD;
    if (GLOB[30] / 256 + 20 > haut) haut = GLOB[30] / 256 + 20;
    GLOB[20] = haut;
}

static u ampleur(u y) {
    u amp = (u)256 * RN / RD;
    if (y > (u)110 * RN / RD && y < 4000) {
        amp = (256 + (y * RD / RN - 110) * 10) * RN / RD;
        if (amp > (u)900 * RN / RD) amp = (u)900 * RN / RD;
    }
    return amp;
}

static u mannequin(u fx, u ly, u fz, int gaulois) {
    if (fx == 0 && fz == 1) {
        if (ly <= 9) return BOIS;
        if (ly <= 11) return METAL;
        return 0;
    }
    if (fx == 1 && ly >= 1 && ly <= 5 && !slt(fz, 0 - (u)2) && !slt(1, fz)) {
        if (gaulois) {
            if ((ly == 1 || ly == 5) && (fz == 0 - (u)2 || fz == 1)) return 0;
            if (ly == 3 && (fz == 0 - (u)1 || fz == 0)) return METAL;
            return ECU_GAULOIS;
        }
        if (ly == 3 && (fz == 0 - (u)1 || fz == 0)) return METAL;
        return ECU_ROMAIN;
    }
    if (slt(fz, 0 - (u)1) || slt(0, fz)) return 0;
    if (ly <= 2 && fx == 0) return gaulois ? BRAIES : PEAU;
    if (ly >= 3 && ly <= 5 && (fx == 0 || fx == 0 - (u)1)) return gaulois ? GAULOIS : ROMAIN;
    if (ly >= 6 && ly <= 7 && (fx == 0 || fx == 0 - (u)1)) {
        if (ly == 7) return gaulois ? CHEVEUX : METAL;
        return PEAU;
    }
    if (ly == 8 && !gaulois && fx == 0 - (u)1 && fz == 0) return ROMAIN;
    return 0;
}

static u camp(u lx, u ly, u lz) {
    if (slt(ly, 0) || ly > 14) return 0;
    u lxm = CAMP_X1 - CAMP_X0, lzm = CAMP_Z1 - CAMP_Z0;
    int coinx = lx < 7 || lx > lxm - 7, coinz = lz < 7 || lz > lzm - 7;
    if (coinx && coinz) {
        if (ly <= 11) return PIERRE;
        if (ly == 12 && ((lx + lz) & 2) == 0) return PIERRE;
        return 0;
    }
    if (lx < 3 || lx > lxm - 3 || lz < 3 || lz > lzm - 3) {
        u milieu = lxm / 2;
        if (lz > lzm - 3 && lx + 4 > milieu && lx < milieu + 4 && ly <= 6) return 0;
        if (ly <= 8) return PIERRE;
        if (ly == 9 && ((lx + lz) & 2) == 0) return PIERRE;
        return 0;
    }
    u tx = lx - (lxm / 2 - 10), tz = lz - 10;
    if (tx <= 20 && tz <= 12) {
        if (ly <= 1) return PIERRE;
        if (ly <= 8 && (tz == 1 || tz == 11) && (tx % 3) == 1) return MARBRE;
        if (ly == 9 || ly == 10) return TUILE;
        if (ly == 11 && tz >= 3 && tz <= 9) return TUILE;
        if (ly == 12 && tz >= 5 && tz <= 7) return TUILE;
        return 0;
    }
    u cote = 0;
    if (lx >= 4 && lx <= 18) cote = 4;
    else if (lx + 18 >= lxm && lx + 4 <= lxm) cote = lxm - 18;
    if (cote > 0 && lz >= 4 && lz <= lzm - 5) {
        u ux = (lx - cote) % 6, uz = (lz - 4) % 6;
        if (ux <= 3 && uz <= 2) {
            u pente = uz == 2 ? 0 : uz;
            if (ly <= 1 + pente) return TOILE;
        }
    }
    return 0;
}

static u armees(u x, u ly, u z) {
    if (slt(ly, 0) || ly > 11) return 0;
    u pas_x = (u)5 * RN / RD, pas_z = (u)4 * RN / RD;
    if (pas_x < 2) pas_x = 2;
    if (pas_z < 2) pas_z = 2;
    u rx0 = ARM_X0 + (u)6 * RN / RD, milieu = (ARM_X0 + ARM_X1) / 2;
    if (x < milieu) {
        u i = (x - rx0 + pas_x * 3 / 2) / pas_x;
        if (i > 2) i = 2;
        u j = (z - ARM_Z0 - 2 + pas_z / 2) / pas_z;
        if (j > 9) j = 9;
        u sx = rx0 + i * pas_x, sz = ARM_Z0 + 4 + j * pas_z;
        return mannequin(x - sx, ly, z - sz, 0);
    }
    u gx0 = ARM_X1 - (u)6 * RN / RD;
    u i2 = (gx0 - x + pas_x * 3 / 2) / pas_x;
    if (i2 > 2) i2 = 2;
    u j2 = (z - ARM_Z0 - 2 + pas_z / 2) / pas_z;
    if (j2 > 9) j2 = 9;
    u dec = (hache(i2 + 17, j2 + 41) % 3) - 1;
    u sx2 = gx0 - i2 * pas_x + dec, sz2 = ARM_Z0 + 4 + j2 * pas_z;
    return mannequin(sx2 - x, ly, z - sz2, 1);
}

static u objet(u x, u y, u z) {
    if (x >= CAMP_X0 && x <= CAMP_X1 && z >= CAMP_Z0 && z <= CAMP_Z1)
        return camp(x - CAMP_X0, y - (GLOB[30] - 129) / 256 - 1, z - CAMP_Z0);
    if (x >= ARM_X0 && x <= ARM_X1 && z >= ARM_Z0 && z <= ARM_Z1)
        return armees(x, y - (GLOB[31] - 129) / 256 - 1, z);
    return 0;
}

static u densite(u x, u y, u z) {
    if (objet(x, y, z) != 0) return 256;
    u h = HCOL[(z & MASQ) * MONDE + (x & MASQ)];
    u d = h - y * 256 - 128;
    u amp = ampleur(y);
    if (slt(d, amp + 512) && slt(0 - amp - 512, d)) d = d + sdiv((bruit3(x, y, z) - 32768) * amp, 32768);
    return d;
}

static u rgb24(u r, u g, u b) {
    if (slt(r, 0)) r = 0;
    if (slt(g, 0)) g = 0;
    if (slt(b, 0)) b = 0;
    if (r > 255) r = 255;
    if (g > 255) g = 255;
    if (b > 255) b = 255;
    return (r << 16) | (g << 8) | b;
}
static inline u normale_mot(u nx, u ny, u nz) {
    return ((nx + 128) & 255) | (((ny + 128) & 255) << 8) | (((nz + 128) & 255) << 16);
}

static u plein(u x, u y, u z) { return slt(0, densite(x, y, z)) ? 1 : 0; }

static u composer_objet(u x, u y, u z, u ob) {
    u nx = plein(x - 1, y, z) - plein(x + 1, y, z);
    u ny = plein(x, y - 1, z) - plein(x, y + 1, z);
    u nz = plein(x, y, z - 1) - plein(x, y, z + 1);
    u surface = 1 - plein(x - 1, y, z) * plein(x + 1, y, z) * plein(x, y - 1, z) * plein(x, y + 1, z) * plein(x, y, z - 1)
                * plein(x, y, z + 1);
    u r = 150, g = 150, b = 156;
    if (ob == PIERRE) {
        r = 194; g = 178; b = 148;
        if ((y % 3) == 0 || ((x + z + (y / 3) * 2) % 6) == 0) { r = 160; g = 146; b = 120; }
    } else if (ob == TUILE) {
        r = 168; g = 72; b = 50;
        if ((x & 1) == 0) { r = 150; g = 62; b = 44; }
    } else if (ob == MARBRE) { r = 228; g = 224; b = 214; }
    else if (ob == ROMAIN) { r = 170; g = 30; b = 34; }
    else if (ob == GAULOIS) {
        r = 40; g = 98; b = 70;
        if (((x + y + z) & 1) == 1) { r = 64; g = 72; b = 136; }
    } else if (ob == ECU_ROMAIN) { r = 152; g = 26; b = 28; }
    else if (ob == ECU_GAULOIS) { r = 50; g = 86; b = 150; }
    else if (ob == BOIS) { r = 108; g = 76; b = 46; }
    else if (ob == PEAU) { r = 204; g = 152; b = 118; }
    else if (ob == CHEVEUX) { r = 198; g = 162; b = 82; }
    else if (ob == BRAIES) { r = 124; g = 94; b = 62; }
    else if (ob == TOILE) { r = 216; g = 206; b = 182; }
    u grain = hache3(x, y, z) & 7;
    u c = rgb24(r + grain, g + grain, b + grain);
    u nm = 0;
    if (surface == 1) {
        if (nx == 0 && ny == 0 && nz == 0) nm = normale_mot(0, 127, 0);
        else {
            u lg = racine_entiere((nx * nx + ny * ny + nz * nz) * 16129);
            nm = normale_mot(sdiv(nx * 16129, lg), sdiv(ny * 16129, lg), sdiv(nz * 16129, lg));
        }
    }
    return (c << 32) | (nm << 8) | (ob << 2) | 2;
}

static u composer_point(u x, u y, u z) {
    u ob = objet(x, y, z);
    if (ob != 0) return composer_objet(x, y, z, ob);
    u d0 = densite(x, y, z);
    if (!slt(0, d0)) {
        if (y < MER) {
            u fond = sdiv(MER * 256 - HCOL[(z & MASQ) * MONDE + (x & MASQ)], (u)64 * RN / RD);
            if (slt(fond, 0)) fond = 0;
            if (fond > 120) fond = 120;
            u ce = rgb24(34 - fond / 6, 84 - fond / 3, 100 - fond / 5);
            return (ce << 32) | (normale_mot(0, 127, 0) << 8) | (EAU << 2) | 2;
        }
        return 0;
    }
    u dxm = densite(x - 1, y, z), dxp = densite(x + 1, y, z), dym = densite(x, y - 1, z), dyp = densite(x, y + 1, z);
    u dzm = densite(x, y, z - 1), dzp = densite(x, y, z + 1);
    int surface = !slt(0, dxm) || !slt(0, dxp) || !slt(0, dym) || !slt(0, dyp) || !slt(0, dzm) || !slt(0, dzp);
    u col = (z & MASQ) * MONDE + (x & MASQ);
    u hs = HCOL[col] / 256, pente = PENTE[col];
    u mat = HERBE;
    if (y + (u)3 * RN / RD < hs) mat = TERRE;
    if (slt(0, dyp) && surface) mat = ROCHE;
    else if (y <= MER + UN && y + UN >= MER) mat = SABLE;
    else if (y > (u)168 * RN / RD) mat = SCORIE;
    else if (pente > 420 || y > hs + UN) mat = ROCHE;
    else if (y > (u)72 * RN / RD) mat = LANDE;
    if (mat == HERBE && ((x + 6 >= CAMP_X0 && x <= CAMP_X1 + 6 && z + 6 >= CAMP_Z0 && z <= CAMP_Z1 + 6)
                         || (x + 4 >= ARM_X0 && x <= ARM_X1 + 4 && z + 4 >= ARM_Z0 && z <= ARM_Z1 + 4)))
        mat = TERRE;
    u r = 78, g = 120, b = 58;
    if (mat == HERBE) {
        u champ = hache(x / ((u)24 * RN / RD + 1), z / ((u)20 * RN / RD + 1)) & 7;
        if (champ == 1) { r = 98; g = 134; b = 62; }
        else if (champ == 2) { r = 66; g = 108; b = 50; }
        else if (champ == 3) { r = 176; g = 158; b = 86; }
        else if (champ == 4) { r = 122; g = 98; b = 68; }
        else if (champ == 5) { r = 112; g = 142; b = 72; }
    } else if (mat == ROCHE) { r = 82; g = 76; b = 74; }
    else if (mat == SCORIE) { r = 116; g = 66; b = 50; }
    else if (mat == SABLE) { r = 186; g = 172; b = 134; }
    else if (mat == TERRE) { r = 112; g = 92; b = 68; }
    else if (mat == LANDE) { r = 110; g = 104; b = 70; }
    u tache = (bruit_lisse(x & MASQ, z & MASQ, (u)32 * RN / RD) / 2048) + ((y * RD / RN) & 3);
    u grain = hache3(x, y, z) & 15;
    r = r + tache + grain;
    g = g + tache + grain;
    b = b + tache / 2 + grain;
    u c = rgb24(r, g, b);
    u nm = 0;
    if (surface) {
        u nx = dxm - dxp, ny = dym - dyp, nz = dzm - dzp;
        u lg = racine_entiere(nx * nx + ny * ny + nz * nz);
        nm = lg == 0 ? normale_mot(0, 127, 0) : normale_mot(sdiv(nx * 127, lg), sdiv(ny * 127, lg), sdiv(nz * 127, lg));
    }
    return (c << 32) | (nm << 8) | (mat << 2) | 2;
}

static void classer_blocs(void) {
    for (u q = 0; q < TUILES * TUILES * 1024; q++) {
        u t = q >> 10, bx = q & 31, bz = (q >> 5) & 31;
        u x0 = (t % TUILES) * 256 + bx * 8, z0 = (t / TUILES) * 256 + bz * 8;
        u hmin = 1000000, hmax = 0;
        for (u dz = 0; dz < 10; dz++)
            for (u dx = 0; dx < 10; dx++) {
                u h = HCOL[((z0 + dz + MASQ) & MASQ) * MONDE + ((x0 + dx + MASQ) & MASQ)];
                if (h < hmin) hmin = h;
                if (h > hmax) hmax = h;
            }
        int dans_objet = (x0 + 9 >= CAMP_X0 && x0 <= CAMP_X1 + 1 && z0 + 9 >= CAMP_Z0 && z0 <= CAMP_Z1 + 1)
                         || (x0 + 9 >= ARM_X0 && x0 <= ARM_X1 + 1 && z0 + 9 >= ARM_Z0 && z0 <= ARM_Z1 + 1);
        for (u by = 0; by < 32; by++) {
            u y0 = by * 8, amp = ampleur(y0 + 9), b = (bx << 10) | (by << 5) | bz;
            u e = 1;
            if (dans_objet && y0 * 256 <= hmax + 16 * 256 && (y0 + 9) * 256 + 640 + amp >= hmin) e = 1;
            else if (y0 * 256 > hmax + amp + 640) {
                if (y0 >= MER) e = 0;
                else if (y0 + 8 <= MER) e = 3;
            } else if ((y0 + 9) * 256 + 640 + amp < hmin) e = 2;
            if (e == 0) DIRE[t][IX(b)] = VIDE;
            else if (e == 2) { DIRE[t][IX(b)] = ((u)1 << 62) | (TERRE << 2) | 2; DIRT[t][IX(b)] = rgb24(112, 92, 68); }
            else if (e == 3) {
                u c = composer_point(x0 + 4, y0 + 4, z0 + 4);
                DIRE[t][IX(b)] = ((u)1 << 62) | (c & 4294967295u);
                DIRT[t][IX(b)] = c >> 32;
            } else DIRE[t][IX(b)] = 1;
        }
    }
}

static void placer_et_remplir(void) {
    for (u t = 0; t < TUILES * TUILES; t++) {
        u n = 0;
        for (u b = 0; b < 32768; b++) if (DIRE[t][IX(b)] == 1) DIRE[t][IX(b)] = 16 + n++;
        GLOB[1 + t] = n;
        POOLE[t] = (u *)calloc((n * 512 + 1) * PAS, sizeof(u));
        POOLT[t] = (u *)calloc((n * 512 + 1) * PAS, sizeof(u));
        CIELC[t] = (u *)calloc((n * 64 + 1) * PAS, sizeof(u));
        SOLC[t] = (u *)calloc((n * 64 + 1) * PAS, sizeof(u));
        CREUX[t] = (u *)calloc(n + 1, sizeof(u));
    }
    long q;
#pragma omp parallel for schedule(dynamic, 8)
    for (q = 0; q < (long)(TUILES * TUILES * 1024); q++) {
        u t = (u)q >> 10, bx = (u)q & 31, bz = ((u)q >> 5) & 31;
        u x0 = (t % TUILES) * 256 + bx * 8, z0 = (t / TUILES) * 256 + bz * 8;
        for (u by = 0; by < 32; by++) {
            u e = DIRE[t][IX((bx << 10) | (by << 5) | bz)];
            if (e >= 16 && e < ((u)1 << 62)) {
                u place = (e - 16) * 512;
                for (u v = 0; v < 512; v++) {
                    u c = composer_point(x0 + (v >> 6), by * 8 + ((v >> 3) & 7), z0 + (v & 7));
                    POOLE[t][IX(place + v)] = c & 4294967295u;
                    POOLT[t][IX(place + v)] = c >> 32;
                }
            }
        }
    }
    /* 0.818 : les blocs creusés (un bit par sous-bloc de 2³, rangés par sous-bloc de 4³) */
    for (u t = 0; t < TUILES * TUILES; t++) {
        u n = GLOB[1 + t];
        for (u b = 0; b < n; b++) {
            u m = 0;
            for (u v = 0; v < 512; v++) {
                if (POOLE[t][IX(b * 512 + v)] != 0) {
                    u x = v >> 6, y = (v >> 3) & 7, z = v & 7;
                    u s4 = ((x >> 2) << 2) | ((y >> 2) << 1) | (z >> 2);
                    u s2 = (((x >> 1) & 1) << 2) | (((y >> 1) & 1) << 1) | ((z >> 1) & 1);
                    m |= (u)1 << (s4 * 8 + s2);
                }
            }
            CREUX[t][b] = m;
        }
    }
}

static inline u case_bloc(u gx, u gy, u gz) { return (gy * NB + gz) * NB + gx; }
static inline u *mot_bloc(u gx, u gy, u gz) {
    u t = (gz >> 5) * TUILES + (gx >> 5);
    return &DIRE[t][IX(((gx & 31) << 10) + (gy << 5) + (gz & 31))];
}

static void distancer_blocs(void) {
    DISTA = (u *)calloc(NB * NB * 32, sizeof(u));
    DISTB = (u *)calloc(NB * NB * 32, sizeof(u));
    for (u gy = 0; gy < 32; gy++)
        for (u gz = 0; gz < NB; gz++)
            for (u gx = 0; gx < NB; gx++) DISTA[case_bloc(gx, gy, gz)] = ((*mot_bloc(gx, gy, gz) >> 62) == 2) ? LOIN : 0;
    for (int tour = 0; tour < LOIN - 1; tour++) {
        u *de = (tour & 1) ? DISTB : DISTA, *vers = (tour & 1) ? DISTA : DISTB;
        for (u gy = 0; gy < 32; gy++)
            for (u gz = 0; gz < NB; gz++)
                for (u gx = 0; gx < NB; gx++) {
                    u d = de[case_bloc(gx, gy, gz)];
                    if (d > 1)
                        for (u k = 0; k < 27; k++) {
                            u nx = gx + (k % 3) - 1, ny = gy + ((k / 3) % 3) - 1, nz = gz + (k / 9) - 1;
                            if (nx < NB && ny < 32 && nz < NB) {
                                u v = de[case_bloc(nx, ny, nz)] + 1;
                                if (v < d) d = v;
                            }
                        }
                    vers[case_bloc(gx, gy, gz)] = d;
                }
    }
    u *fin = ((LOIN - 1) & 1) ? DISTB : DISTA;
    for (u gy = 0; gy < 32; gy++)
        for (u gz = 0; gz < NB; gz++)
            for (u gx = 0; gx < NB; gx++) {
                u *m = mot_bloc(gx, gy, gz);
                if ((*m >> 62) == 2) *m = VIDE | fin[case_bloc(gx, gy, gz)];
            }
}

static inline u element(u x, u y, u z) {
    if (x >= MONDE || z >= MONDE || y >= 256) return 0;
    u t = (z >> 8) * TUILES + (x >> 8);
    u e = DIRE[t][IX((((x >> 3) & 31) << 10) + (((y >> 3) & 31) << 5) + ((z >> 3) & 31))];
    if ((e >> 62) == 2) return 0;
    if ((e >> 62) == 1) return e & 4294967295u;
    return POOLE[t][IX((e - 16) * 512 + ((x & 7) << 6) + ((y & 7) << 3) + (z & 7))];
}
static inline u couleur(u x, u y, u z) {
    u t = (z >> 8) * TUILES + (x >> 8);
    u b = (((x >> 3) & 31) << 10) + (((y >> 3) & 31) << 5) + ((z >> 3) & 31);
    u e = DIRE[t][IX(b)];
    if ((e >> 62) == 1) return DIRT[t][IX(b)];
    return POOLT[t][IX((e - 16) * 512 + ((x & 7) << 6) + ((y & 7) << 3) + (z & 7))];
}

static u tracer(u ox, u oy, u oz, u dx, u dy, u dz, u tmax, int eau) {
    u t = 0, plafond = GLOB[20] << 16;
    /* 0.811 : la pente apprise une fois (2^40 / |d|) : chaque pas multiplie au lieu de diviser */
    u ix = 0, iy = 0, iz = 0, P40 = (u)1 << 40;
    if (slt(0, dx)) ix = P40 / dx; else if (slt(dx, 0)) ix = P40 / (0 - dx);
    if (slt(0, dy)) iy = P40 / dy; else if (slt(dy, 0)) iy = P40 / (0 - dy);
    if (slt(0, dz)) iz = P40 / dz; else if (slt(dz, 0)) iz = P40 / (0 - dz);
    while (t < tmax) {
        u px = ox + sar(dx * t, 16), py = oy + sar(dy * t, 16), pz = oz + sar(dz * t, 16);
        if (!slt(py, plafond) && !slt(dy, 0)) return MANQUE;
        if (slt(py, 0) || slt(px, 0) || slt(pz, 0) || !slt(px, MONDE * 65536) || !slt(pz, MONDE * 65536) || !slt(py, 256 * 65536))
            return MANQUE;
        u x = px >> 16, y = py >> 16, z = pz >> 16;
        u tl = (z >> 8) * TUILES + (x >> 8);
        u e = DIRE[tl][IX((((x >> 3) & 31) << 10) + (((y >> 3) & 31) << 5) + ((z >> 3) & 31))];
        u sz_ = 8, av = 1;
        if ((e >> 62) == 2) av = e & 255;
        else if ((e >> 62) == 1) {
            if (eau == 1 || ((e >> 2) & 63) != EAU) return t;
        } else {
            u v = POOLE[tl][IX((e - 16) * 512 + ((x & 7) << 6) + ((y & 7) << 3) + (z & 7))];
            if (v != 0 && (eau == 1 || ((v >> 2) & 63) != EAU)) return t;
            sz_ = 1;
            if (v == 0) {
                u m = CREUX[tl][e - 16];
                u s4 = (((x >> 2) & 1) << 2) | (((y >> 2) & 1) << 1) | ((z >> 2) & 1);
                if (((m >> (s4 * 8)) & 255) == 0) sz_ = 4;
                else {
                    u s2 = (((x >> 1) & 1) << 2) | (((y >> 1) & 1) << 1) | ((z >> 1) & 1);
                    if (((m >> (s4 * 8 + s2)) & 1) == 0) sz_ = 2;
                }
            }
        }
        u arr = sz_ == 8 ? (av - 1) * 8 : 0;
        u pas = MANQUE;
        if (slt(0, dx)) { u ex = ((((x | (sz_ - 1)) + 1 + arr) << 16) - px) * ix >> 24; if (ex < pas) pas = ex; }
        else if (slt(dx, 0)) { u ex = ((px - (((x & (0 - sz_)) - arr) << 16)) + 1) * ix >> 24; if (ex < pas) pas = ex; }
        if (slt(0, dy)) { u ey = ((((y | (sz_ - 1)) + 1 + arr) << 16) - py) * iy >> 24; if (ey < pas) pas = ey; }
        else if (slt(dy, 0)) { u ey = ((py - (((y & (0 - sz_)) - arr) << 16)) + 1) * iy >> 24; if (ey < pas) pas = ey; }
        if (slt(0, dz)) { u ez = ((((z | (sz_ - 1)) + 1 + arr) << 16) - pz) * iz >> 24; if (ez < pas) pas = ez; }
        else if (slt(dz, 0)) { u ez = ((pz - (((z & (0 - sz_)) - arr) << 16)) + 1) * iz >> 24; if (ez < pas) pas = ez; }
        t = t + pas + 1;
    }
    return MANQUE;
}

static void preparer_soleil(u az, u el) {
    u lx = sdiv(cos1024(el) * sin1024(az), 65536), ly = sin1024(el), lz = sdiv(cos1024(el) * cos1024(az), 65536);
    SOLEILS[12] = lx; SOLEILS[13] = ly; SOLEILS[14] = lz;
    u ul = racine_entiere(lx * lx + lz * lz);
    u ux = sdiv(lz * 65536, ul), uz = sdiv((0 - lx) * 65536, ul);
    u vx = sdiv(0 - uz * ly, 65536), vy = sdiv(uz * lx - ux * lz, 65536), vz = sdiv(ux * ly, 65536);
    for (u k = 0; k < 4; k++) {
        u ex = 0, ey = 0, ez = 0;
        if (k == 0) { ex = ux; ez = uz; }
        else if (k == 1) { ex = 0 - ux; ez = 0 - uz; }
        else if (k == 2) { ex = vx; ey = vy; ez = vz; }
        else { ex = 0 - vx; ey = 0 - vy; ez = 0 - vz; }
        u sx = lx + sdiv(ex * 2300, 65536), sy = ly + sdiv(ey * 2300, 65536), sz = lz + sdiv(ez * 2300, 65536);
        u lg = racine_entiere(sx * sx + sy * sy + sz * sz);
        SOLEILS[3 * k] = sdiv(sx * 65536, lg); SOLEILS[3 * k + 1] = sdiv(sy * 65536, lg); SOLEILS[3 * k + 2] = sdiv(sz * 65536, lg);
    }
}

static u ciel(u dx, u dy, u dz) {
    u hy = slt(dy, 0) ? 0 : dy;
    u t = hy * 256 / 65536;
    u r = (200 * (256 - t) + 92 * t) / 256, g = (214 * (256 - t) + 128 * t) / 256, b = (230 * (256 - t) + 184 * t) / 256;
    u cs = sdiv(dx * SOLEILS[12] + dy * SOLEILS[13] + dz * SOLEILS[14], 65536);
    if (slt(65500, cs)) return rgb24(255, 248, 228);
    if (slt(60000, cs)) { u lueur = (cs - 60000) * 90 / 5500; r += lueur; g += lueur * 3 / 4; b += lueur / 3; }
    return rgb24(r, g, b);
}

/* 0.810 : les calques de lumière (le ciel une fois, la clepsydre quand le soleil bouge) */
static u depart(u x, u y, u z, u nx, u ny, u nz) {
    u sx = (x << 16) + 32768 + nx * 858, sy = (y << 16) + 32768 + ny * 858, sz = (z << 16) + 32768 + nz * 858;
    if (element(sx >> 16, sy >> 16, sz >> 16) != 0) {
        u meilleur = 6, note = 0 - (u)1000;
        for (u k = 0; k < 6; k++) {
            u vx = x, vy = y, vz = z, nk = nx;
            if (k == 0) vx = x + 1; else if (k == 1) { vx = x - 1; nk = 0 - nx; }
            else if (k == 2) { vy = y + 1; nk = ny; } else if (k == 3) { vy = y - 1; nk = 0 - ny; }
            else if (k == 4) { vz = z + 1; nk = nz; } else { vz = z - 1; nk = 0 - nz; }
            if (element(vx, vy, vz) == 0 && slt(note, nk)) { note = nk; meilleur = k; }
        }
        return meilleur;
    }
    return 6;
}
static void partir(u x, u y, u z, u nx, u ny, u nz, u *sx, u *sy, u *sz) {
    *sx = (x << 16) + 32768 + nx * 858; *sy = (y << 16) + 32768 + ny * 858; *sz = (z << 16) + 32768 + nz * 858;
    u dp = depart(x, y, z, nx, ny, nz);
    if (dp < 6) {
        *sx = (x << 16) + 32768; *sy = (y << 16) + 32768; *sz = (z << 16) + 32768;
        if (dp == 0) *sx += 65536; else if (dp == 1) *sx -= 65536; else if (dp == 2) *sy += 65536;
        else if (dp == 3) *sy -= 65536; else if (dp == 4) *sz += 65536; else *sz -= 65536;
    }
}
static u soleil_depuis(u sx, u sy, u sz, u nx, u ny, u nz) {
    u nl = sdiv(nx * SOLEILS[12] + ny * SOLEILS[13] + nz * SOLEILS[14], 127);
    if (!slt(0, nl)) return 0;
    u vus = 0;
    for (u k = 0; k < 4; k++)
        if (tracer(sx, sy, sz, SOLEILS[3 * k], SOLEILS[3 * k + 1], SOLEILS[3 * k + 2], (u)700 * 65536 * RN / RD, 0) == MANQUE) vus++;
    return vus;
}
static u ciel_depuis(u sx, u sy, u sz, u nx, u ny, u nz) {
    u n16x = nx * 516, n16y = ny * 516, n16z = nz * 516;
    u t1x = 0, t1y = 0, t1z = 0;
    u ay_ = slt(ny, 0) ? 0 - ny : ny;
    if (slt(ay_, 90)) { t1x = 0 - n16z; t1z = n16x; } else { t1y = n16z; t1z = 0 - n16y; }
    u l1 = racine_entiere(t1x * t1x + t1y * t1y + t1z * t1z);
    if (l1 == 0) l1 = 1;
    t1x = sdiv(t1x * 65536, l1); t1y = sdiv(t1y * 65536, l1); t1z = sdiv(t1z * 65536, l1);
    u t2x = sdiv(n16y * t1z - n16z * t1y, 65536), t2y = sdiv(n16z * t1x - n16x * t1z, 65536), t2z = sdiv(n16x * t1y - n16y * t1x, 65536);
    u ouverts = 0;
    for (u k = 0; k < 4; k++) {
        u ex = t1x, ey = t1y, ez = t1z;
        if (k == 1) { ex = 0 - t1x; ey = 0 - t1y; ez = 0 - t1z; }
        else if (k == 2) { ex = t2x; ey = t2y; ez = t2z; }
        else if (k == 3) { ex = 0 - t2x; ey = 0 - t2y; ez = 0 - t2z; }
        u cx = sdiv(n16x * 3 + ex * 4, 5), cy = sdiv(n16y * 3 + ey * 4, 5), cz = sdiv(n16z * 3 + ez * 4, 5);
        if (tracer(sx, sy, sz, cx, cy, cz, (u)14 * 65536 * RN / RD, 0) == MANQUE) ouverts++;
    }
    return ouverts;
}
static u soleil_vu(u x, u y, u z, u nx, u ny, u nz) {
    u sx, sy, sz;
    partir(x, y, z, nx, ny, nz, &sx, &sy, &sz);
    return soleil_depuis(sx, sy, sz, nx, ny, nz);
}
static u ciel_ouvert(u x, u y, u z, u nx, u ny, u nz) {
    u sx, sy, sz;
    partir(x, y, z, nx, ny, nz, &sx, &sy, &sz);
    return ciel_depuis(sx, sy, sz, nx, ny, nz);
}
static int expose(u x, u y, u z) {
    return element(x + 1, y, z) == 0 || element(x - 1, y, z) == 0 || element(x, y + 1, z) == 0 ||
           element(x, y - 1, z) == 0 || element(x, y, z + 1) == 0 || element(x, y, z - 1) == 0;
}
static void ranger_lumiere(int avec_ciel) {
    long q;
#pragma omp parallel for schedule(dynamic, 8)
    for (q = 0; q < (long)(TUILES * TUILES * 1024); q++) {
        u t = (u)q >> 10, bx = (u)q & 31, bz = ((u)q >> 5) & 31;
        u x0 = (t % TUILES) * 256 + bx * 8, z0 = (t / TUILES) * 256 + bz * 8;
        for (u by = 0; by < 32; by++) {
            u e = DIRE[t][IX((bx << 10) | (by << 5) | bz)];
            if (e >= 16 && e < ((u)1 << 62)) {
                u n = e - 16;
                for (u w = 0; w < 64; w++) {
                    u ms_ = 0, mc = 0;
                    for (u j = 0; j < 8; j++) {
                        u v = w * 8 + j, x = x0 + (v >> 6), y = by * 8 + ((v >> 3) & 7), z = z0 + (v & 7);
                        u el = POOLE[t][IX(n * 512 + v)];
                        if (el != 0 && ((el >> 2) & 63) != EAU && expose(x, y, z)) {
                            u nx = ((el >> 8) & 255) - 128, ny = ((el >> 16) & 255) - 128, nz = ((el >> 24) & 255) - 128;
                            if (nx == 0 - (u)128) { nx = 0; ny = 127; nz = 0; }
                            ms_ |= (128 | soleil_vu(x, y, z, nx, ny, nz)) << (j * 8);
                            if (avec_ciel) mc |= (128 | ciel_ouvert(x, y, z, nx, ny, nz)) << (j * 8);
                        }
                    }
                    SOLC[t][IX(n * 64 + w)] = ms_;
                    if (avec_ciel) CIELC[t][IX(n * 64 + w)] = mc;
                }
            }
        }
    }
}

#ifdef PROGRESSIF
/* 0.828 : la clepsydre progressive (comme ranger_lumiere_progressive de gergovie_scene.vtx) : dans chaque groupe de
   quatre mots, celui que tire le hachage de son lieu, décalé du numéro de l'image ; la lumière d'une ligne de huit
   points se calcule d'abord aux bouts et au centre (j = 0, 4, 7) ; s'ils voient le même soleil, les autres le reçoivent */
static u tirage(u t, u n, u g, u image) {
    return (((((t * 1031 + n) * 16 + g) * 2654435761u) >> 13) + image) & 3;
}
static void ranger_lumiere_p(u image) {
    long q;
#pragma omp parallel for schedule(dynamic, 8)
    for (q = 0; q < (long)(TUILES * TUILES * 1024); q++) {
        u t = (u)q >> 10, bx = (u)q & 31, bz = ((u)q >> 5) & 31;
        u x0 = (t % TUILES) * 256 + bx * 8, z0 = (t / TUILES) * 256 + bz * 8;
        for (u by = 0; by < 32; by++) {
            u e = DIRE[t][IX((bx << 10) | (by << 5) | bz)];
            if (e >= 16 && e < ((u)1 << 62)) {
                u n = e - 16;
                for (u g = 0; g < 16; g++) {
                    u w = g * 4 + tirage(t, n, g, image);
                    u ms_ = 0, faits = 0, commun = 9;
                    for (u jr = 0; jr < 3; jr++) {
                        u j = jr * 4 - (jr >> 1);
                        u v = w * 8 + j, x = x0 + (v >> 6), y = by * 8 + ((v >> 3) & 7), z = z0 + (v & 7);
                        u el = POOLE[t][IX(n * 512 + v)];
                        if (el != 0 && ((el >> 2) & 63) != EAU && expose(x, y, z)) {
                            u nx = ((el >> 8) & 255) - 128, ny = ((el >> 16) & 255) - 128, nz = ((el >> 24) & 255) - 128;
                            if (nx == 0 - (u)128) { nx = 0; ny = 127; nz = 0; }
                            u sv = soleil_vu(x, y, z, nx, ny, nz);
                            ms_ |= (128 | sv) << (j * 8);
                            faits |= (u)1 << j;
                            if (commun == 9) commun = sv; else if (commun != sv) commun = 10;
                        }
                    }
                    if (commun == 9) commun = 10;
                    for (u j = 0; j < 8; j++) {
                        if ((faits >> j) & 1) continue;
                        u v = w * 8 + j, x = x0 + (v >> 6), y = by * 8 + ((v >> 3) & 7), z = z0 + (v & 7);
                        u el = POOLE[t][IX(n * 512 + v)];
                        if (el != 0 && ((el >> 2) & 63) != EAU && expose(x, y, z)) {
                            u nx = ((el >> 8) & 255) - 128, ny = ((el >> 16) & 255) - 128, nz = ((el >> 24) & 255) - 128;
                            if (nx == 0 - (u)128) { nx = 0; ny = 127; nz = 0; }
                            u sj = commun < 9 ? commun : soleil_vu(x, y, z, nx, ny, nz);
                            ms_ |= (128 | sj) << (j * 8);
                        }
                    }
                    SOLC[t][IX(n * 64 + w)] = ms_;
                }
            }
        }
    }
}
#endif

static u brumer(u c, u t) {
    u r = c & 4095, g = (c >> 12) & 4095, b = (c >> 24) & 4095;
    u d = (t >> 16) * RD / RN;
    u brume = d * d / 1600;
    if (brume > 220) brume = 220;
    r = (r * (256 - brume) + 200 * brume) / 256;
    g = (g * (256 - brume) + 214 * brume) / 256;
    b = (b * (256 - brume) + 230 * brume) / 256;
    return rgb24(r, g, b);
}

/* la clarté d'un point de terre (l'ombre et la lumière) : om | couleur << 16 ; 3 pour l'eau */
static u clarte(u ox, u oy, u oz, u dx, u dy, u dz, u t) {
    u px = ox + sar(dx * t, 16), py = oy + sar(dy * t, 16), pz = oz + sar(dz * t, 16);
    u x = px >> 16, y = py >> 16, z = pz >> 16;
    u e = element(x, y, z);
    if (((e >> 2) & 63) == EAU) return 3;
    u nx = ((e >> 8) & 255) - 128, ny = ((e >> 16) & 255) - 128, nz = ((e >> 24) & 255) - 128;
    if (nx == 0 - (u)128) { nx = 0; ny = 127; nz = 0; }
    u nl = sdiv(nx * SOLEILS[12] + ny * SOLEILS[13] + nz * SOLEILS[14], 127);
    u vus = 0, ouverts = 0;
    int connu = 0;
    u tt = (z >> 8) * TUILES + (x >> 8);
    u e0 = DIRE[tt][IX((((x >> 3) & 31) << 10) + (((y >> 3) & 31) << 5) + ((z >> 3) & 31))];
    if (e0 >= 16 && e0 < ((u)1 << 62)) {
        u iv = ((x & 7) << 6) | ((y & 7) << 3) | (z & 7), dec = (iv & 7) * 8;
        u sb = (SOLC[tt][IX((e0 - 16) * 64 + (iv >> 3))] >> dec) & 255;
        if (sb >= 128) { connu = 1; vus = sb & 15; ouverts = (CIELC[tt][IX((e0 - 16) * 64 + (iv >> 3))] >> dec) & 15; }
    }
    if (!connu) {
        vus = soleil_depuis(px + nx * 600, py + ny * 600, pz + nz * 600, nx, ny, nz);
        ouverts = ciel_depuis(px + nx * 600, py + ny * 600, pz + nz * 600, nx, ny, nz);
    }
    u etat = 1;
    if (slt(0, nl)) { if (vus == 4) etat = 2; else if (vus > 0) etat = 3; } else nl = 0;
    u alb = couleur(x, y, z);
    u ciel_part = 40 + ouverts * 30;
    u soleil = nl * vus / 4 * 256 / 65536;
    u lr = 76 * ciel_part / 160 + soleil * 255 / 256 + 20, lg2 = 88 * ciel_part / 160 + soleil * 238 / 256 + 18,
      lb = 112 * ciel_part / 160 + soleil * 210 / 256 + 14;
    u r = ((alb >> 16) & 255) * lr / 200, g = ((alb >> 8) & 255) * lg2 / 200, b = (alb & 255) * lb / 200;
    return 1 | (etat << 2) | (vus << 4) | (ouverts << 8) | ((r | (g << 12) | (b << 24)) << 16);
}

static inline u inverse_longueur(u x, u y, u z) { return (u)281474976710656ull / racine_entiere(x * x + y * y + z * z); }

static u regarder_0(u ox, u oy, u oz, u dx, u dy, u dz, u temps);

/* Divona (profondeur : 1 renvoie le monde, 0 le ciel) */
static u divona(u ox, u oy, u oz, u dx, u dy, u dz, u t, u temps, int profondeur) {
    u px = ox + sar(dx * t, 16), py = oy + sar(dy * t, 16), pz = oz + sar(dz * t, 16);
    (void)py;
    u x = px >> 16, z = pz >> 16;
    u alb = couleur(x, py >> 16, z);
    u rx = dx + sdiv(bruit_lisse((x + temps) & MASQ, z & MASQ, 16) - 32768, 24);
    u rz = dz + sdiv(bruit_lisse(x & MASQ, (z + temps * 2) & MASQ, 16) - 32768, 24);
    u ry = 0 - dy;
    u inv = inverse_longueur(rx, ry, rz);
    rx = sar(rx * inv, 32); ry = sar(ry * inv, 32); rz = sar(rz * inv, 32);
    u renvoi = profondeur ? regarder_0(px, (MER << 16) + 32768, pz, rx, ry, rz, temps) & 16777215 : ciel(rx, ry, rz);
    u rasant = 65536 - (0 - dy);
    if (slt(0, dy)) rasant = 65536;
    u part = 64 + rasant * rasant / 65536 * 154 / 65536;
    u r = (((alb >> 16) & 255) * (256 - part) + ((renvoi >> 16) & 255) * part) / 256;
    u g = (((alb >> 8) & 255) * (256 - part) + ((renvoi >> 8) & 255) * part) / 256;
    u b = ((alb & 255) * (256 - part) + (renvoi & 255) * part) / 256;
    return r | (g << 12) | (b << 24);
}

static u regarder_n(u ox, u oy, u oz, u dx, u dy, u dz, u temps, int profondeur) {
    u t = tracer(ox, oy, oz, dx, dy, dz, (u)1100 * 65536 * RN / RD, 1);
    if (t == MANQUE) return ciel(dx, dy, dz);
    u om = clarte(ox, oy, oz, dx, dy, dz, t);
    if ((om & 2) != 0) return ((u)2 << 24) | brumer(divona(ox, oy, oz, dx, dy, dz, t, temps, profondeur), t);
    return (((om >> 2) & 3) << 24) | brumer(om >> 16, t);
}

static u regarder_0(u ox, u oy, u oz, u dx, u dy, u dz, u temps) { return regarder_n(ox, oy, oz, dx, dy, dz, temps, 0); }

static u point_vu(u i, u cx, u cy, u cz, u lacet, u tangage, u temps) {
    u sl = sin1024(lacet), cl = cos1024(lacet), st = sin1024(tangage), ct = cos1024(tangage);
    u iy = i / W, ix = i - iy * W;
    u sy = sdiv((H - 2 * iy - 1) * 45889, W), sx = sdiv((2 * ix + 1 - W) * 45889, W);
    u dx = sdiv(sl * ct, 65536) + sdiv(cl * sx + sdiv(0 - sl * st, 65536) * sy, 65536);
    u dy = st + sdiv(ct * sy, 65536);
    u dz = sdiv(cl * ct, 65536) + sdiv((0 - sl) * sx + sdiv(0 - cl * st, 65536) * sy, 65536);
    u inv = inverse_longueur(dx, dy, dz);
    dx = sar(dx * inv, 32); dy = sar(dy * inv, 32); dz = sar(dz * inv, 32);
    return regarder_n(cx, cy, cz, dx, dy, dz, temps, 1) & 16777215;
}

static void image_gergovie(u i, u n, u temps) {
    u cx = ((u)176 * 65536 + ((u)96 * 65536 / n) * i) * RN / RD;
    u cy = ((u)84 * 65536 - ((u)24 * 65536 / n) * i) * RN / RD;
    u cz = ((u)470 * 65536 - ((u)160 * 65536 / n) * i) * RN / RD;
    u lacet = (504 + (16 * i) / n) & 1023, tangage = (978 + (32 * i) / n) & 1023;
    long yy;
#pragma omp parallel for schedule(dynamic, 4)
    for (yy = 0; yy < H; yy++)
        for (u x = 0; x < W; x++) ECRAN[(u)yy * W + x] = point_vu((u)yy * W + x, cx, cy, cz, lacet, tangage, temps);
}

static double ms(struct timespec a, struct timespec b) { return (b.tv_sec - a.tv_sec) * 1e3 + (b.tv_nsec - a.tv_nsec) / 1e6; }

static u empreinte(void) {
    u h = 14695981039346656037u;
    for (u i = 0; i < W * H; i++) h = (h ^ ECRAN[i]) * 1099511628211u;
    return h;
}

static void bilan(const char *nom, double *t, u n) {
    double total = 0;
    for (u i = 0; i < n; i++) total += t[i];
    std::sort(t, t + n);
    u k = n / 100;
    if (k == 0) k = 1;
    double lents = 0;
    for (u i = n - k; i < n; i++) lents += t[i];
    printf("gergovie : %s : %llu images, %.1f images par seconde en moyenne, 1 %% bas %.1f, pire image %.1f ms ; empreinte %lld\n",
           nom, (unsigned long long)n, 1000.0 * n / total, 1000.0 * k / lents, t[n - 1], (long long)empreinte());
    fflush(stdout);
}

int main(void) {
    u n1 = getenv("GERGOVIE_VOL") ? (u)atoll(getenv("GERGOVIE_VOL")) : 240;
    u n2 = getenv("GERGOVIE_JOUR") ? (u)atoll(getenv("GERGOVIE_JOUR")) : 120;
    HCOL = (u *)calloc(MONDE * MONDE, sizeof(u));
    PENTE = (u *)calloc(MONDE * MONDE, sizeof(u));
    for (u t = 0; t < TUILES * TUILES; t++) { DIRE[t] = (u *)calloc(32768 * PAS, sizeof(u)); DIRT[t] = (u *)calloc(32768 * PAS, sizeof(u)); }
    struct timespec t0, t1, ti, tf;
    clock_gettime(CLOCK_MONOTONIC, &t0);
    preparer_sinus();
    creer_sol();
    classer_blocs();
    placer_et_remplir();
    distancer_blocs();
    clock_gettime(CLOCK_MONOTONIC, &t1);
    printf("le monde : %.0f ms ; blocs porteurs d'une surface, par tuile : %llu, %llu, %llu, %llu\n", ms(t0, t1),
           (unsigned long long)GLOB[1], (unsigned long long)GLOB[2], (unsigned long long)GLOB[3], (unsigned long long)GLOB[4]);
    double *t = (double *)calloc(n1 + n2 + 1, sizeof(double));
    preparer_soleil(360, 70);
    ranger_lumiere(1);
    image_gergovie(0, n1, 0);  /* la mise en place */
    for (u i = 0; i < n1; i++) {
        clock_gettime(CLOCK_MONOTONIC, &ti);
        image_gergovie(i, n1, i * 3);
        clock_gettime(CLOCK_MONOTONIC, &tf);
        t[i] = ms(ti, tf);
    }
    bilan("le vol (en C++)", t, n1);
    for (u i = 0; i < n2; i++) {
        clock_gettime(CLOCK_MONOTONIC, &ti);
        preparer_soleil(300 + i * 3, 50 + i);
#ifdef PROGRESSIF
        if (i > 0) ranger_lumiere_p(i); else ranger_lumiere(0);
#else
        ranger_lumiere(0);
#endif
        image_gergovie(i, n2, i * 3);
        clock_gettime(CLOCK_MONOTONIC, &tf);
        t[i] = ms(ti, tf);
    }
    #ifdef PROGRESSIF
    bilan("le jour (en C++, la clepsydre progressive)", t, n2);
#else
    bilan("le jour (en C++)", t, n2);
#endif
    free(t);
    return 0;
}
