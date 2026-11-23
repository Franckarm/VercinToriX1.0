/* Belenos : le paysage fait dans le cube, écrit en C pour comparer (0.809 ; 0.810 : les calques de lumière ; 0.811 : la pente apprise ; 0.818 : les blocs creusés). Le même calcul que cubes_scene.vtx et
 * cubes_film.vtx, entier pour entier : la même empreinte. Sans GIF (les images sont calculées, pas écrites).
 *     cc -O2 -o cubes_ref belenos/cubes_ref.c                      (l'échelle 1, un cœur)
 *     cc -O2 -fopenmp -o cubes_ref belenos/cubes_ref.c             (les rangées de l'image sur tous les cœurs)
 *     cc -O2 -DRN=2 -DRD=1 ...                                      (une autre échelle)
 *     CUBES_IMAGES=6 ./cubes_ref                                     (moins d'images)
 *     cl /O2 /openmp /TC cubes_ref.c                                (Windows, le compilateur de Microsoft)
 * Les opérations de vtx : / % < > sans signe ; ./ .>> .< .> avec signe ; tout sur 64 bits, en enveloppant. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

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

#define W 1280
#define H 720
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
#define ARCHE_X ((u)256 * RN / RD)
#define ARCHE_Z ((u)300 * RN / RD)
#define ARCHE_R ((u)30 * RN / RD)
#define ARCHE_E ((u)7 * RN / RD)
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

static void creer_sol(void) {
    for (u z = 0; z < MONDE; z++)
        for (u x = 0; x < MONDE; x++) {
            u h = bruit_lisse(x, z, (u)256 * RN / RD) * 16 + bruit_lisse(x, z, (u)128 * RN / RD) * 8
                  + bruit_lisse(x, z, (u)64 * RN / RD) * 4 + bruit_lisse(x, z, (u)32 * RN / RD) * 2 + bruit_lisse(x, z, (u)16 * RN / RD);
            u n = h / 31;
            u e = sdiv((n - 32768) * 11, 4);
            u n2 = 32768 + e;
            if (slt(n2, 0)) n2 = 0;
            if (n2 > 65535) n2 = 65535;
            u m = 0;
            if (n2 > 34000) m = (n2 - 34000) * 65536 / 31535;
            if (m > 65535) m = 65535;
            u hs = 34 * 256 + n2 * 48 / 256 + m * m / 65536 * 160 / 256;
            if (hs > 100 * 256) hs = 100 * 256 + (hs - 100 * 256) / 6;
            HCOL[z * MONDE + x] = hs * RN / RD;
        }
    for (u z = 0; z < MONDE; z++)
        for (u x = 0; x < MONDE; x++) {
            u hx1 = HCOL[z * MONDE + ((x + 1) & MASQ)], hx0 = HCOL[z * MONDE + ((x + MASQ) & MASQ)];
            u hz1 = HCOL[((z + 1) & MASQ) * MONDE + x], hz0 = HCOL[((z + MASQ) & MASQ) * MONDE + x];
            u p = 0;
            p += hx1 > hx0 ? hx1 - hx0 : hx0 - hx1;
            p += hz1 > hz0 ? hz1 - hz0 : hz0 - hz1;
            PENTE[z * MONDE + x] = p / 2;
        }
    GLOB[0] = (HCOL[ARCHE_Z * MONDE + ARCHE_X - ARCHE_R] + HCOL[ARCHE_Z * MONDE + ARCHE_X + ARCHE_R]) / 512;
    u haut = 0;
    for (u i = 0; i < MONDE * MONDE; i++) if (HCOL[i] > haut) haut = HCOL[i];
    haut = haut / 256 + (u)12 * RN / RD;
    if (GLOB[0] + ARCHE_R + ARCHE_E + 4 > haut) haut = GLOB[0] + ARCHE_R + ARCHE_E + 4;
    GLOB[20] = haut;
}

static u ampleur(u y) {
    u amp = (u)384 * RN / RD;
    if (y > (u)70 * RN / RD && y < 4000) {
        amp = (384 + (y * RD / RN - 70) * 40) * RN / RD;
        if (amp > (u)1800 * RN / RD) amp = (u)1800 * RN / RD;
    }
    return amp;
}

static u densite(u x, u y, u z) {
    u h = HCOL[(z & MASQ) * MONDE + (x & MASQ)];
    u d = h - y * 256 - 128;
    u amp = ampleur(y);
    if (slt(d, amp + 512) && slt(0 - amp - 512, d)) d = d + sdiv((bruit3(x, y, z) - 32768) * amp, 32768);
    u ay = GLOB[0];
    u ax = x - ARCHE_X, az = z - ARCHE_Z, ah = y - ay;
    if (slt(0 - (u)48 * RN / RD, ax) && slt(ax, (u)48 * RN / RD) && slt(0 - (u)12 * RN / RD, az) && slt(az, (u)12 * RN / RD)
        && slt(0 - (u)8 * RN / RD, ah) && slt(ah, (u)48 * RN / RD)) {
        u q = racine_entiere((ax * ax + ah * ah) * 65536);
        u e = q - ARCHE_R * 256;
        u dist = racine_entiere(e * e + az * az * 65536);
        u da = ARCHE_E * 256 - dist + sdiv((bruit3(x * 2, y * 2, z * 2) - 32768) * ((u)300 * RN / RD), 32768);
        if (slt(d, da)) d = da;
    }
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

static u composer_point(u x, u y, u z) {
    u d0 = densite(x, y, z);
    if (!slt(0, d0)) {
        if (y < MER) {
            u fond = sdiv(MER * 256 - HCOL[(z & MASQ) * MONDE + (x & MASQ)], (u)64 * RN / RD);
            if (slt(fond, 0)) fond = 0;
            if (fond > 120) fond = 120;
            u ce = rgb24(40 - fond / 6, 96 - fond / 3, 104 - fond / 5);
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
    else if (y > (u)108 * RN / RD) mat = pente < 300 ? NEIGE : ROCHE;
    else if (pente > 420 || y > hs + UN) mat = ROCHE;
    else if (y > (u)80 * RN / RD) mat = LANDE;
    u r = 78, g = 120, b = 58;
    if (mat == ROCHE) { r = 120; g = 114; b = 106; }
    else if (mat == NEIGE) { r = 236; g = 240; b = 246; }
    else if (mat == SABLE) { r = 196; g = 182; b = 140; }
    else if (mat == TERRE) { r = 100; g = 80; b = 60; }
    else if (mat == LANDE) { r = 128; g = 118; b = 80; }
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
        u ay = GLOB[0];
        int arche_x = x0 + 8 + (u)48 * RN / RD > ARCHE_X && x0 < ARCHE_X + (u)48 * RN / RD && z0 + 8 + (u)12 * RN / RD > ARCHE_Z
                      && z0 < ARCHE_Z + (u)12 * RN / RD;
        for (u by = 0; by < 32; by++) {
            u y0 = by * 8, amp = ampleur(y0 + 9), b = (bx << 10) | (by << 5) | bz;
            u e = 1;
            if (arche_x && y0 + 9 + (u)8 * RN / RD > ay && y0 < ay + (u)48 * RN / RD + 1) e = 1;
            else if (y0 * 256 > hmax + amp + 640) {
                if (y0 >= MER) e = 0;
                else if (y0 + 8 <= MER) e = 3;
            } else if ((y0 + 9) * 256 + 640 + amp < hmin) e = 2;
            if (e == 0) DIRE[t][IX(b)] = VIDE;
            else if (e == 2) { DIRE[t][IX(b)] = ((u)1 << 62) | (TERRE << 2) | 2; DIRT[t][IX(b)] = rgb24(100, 80, 60); }
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
        POOLE[t] = calloc((n * 512 + 1) * PAS, sizeof(u));
        POOLT[t] = calloc((n * 512 + 1) * PAS, sizeof(u));
        CIELC[t] = calloc((n * 64 + 1) * PAS, sizeof(u));
        SOLC[t] = calloc((n * 64 + 1) * PAS, sizeof(u));
        CREUX[t] = calloc(n + 1, sizeof(u));
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
    DISTA = calloc(NB * NB * 32, sizeof(u));
    DISTB = calloc(NB * NB * 32, sizeof(u));
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

static u regarder(u ox, u oy, u oz, u dx, u dy, u dz, u profondeur, u temps) {
    u t = tracer(ox, oy, oz, dx, dy, dz, (u)1100 * 65536 * RN / RD, 1);
    if (t == MANQUE) return ciel(dx, dy, dz);
    u px = ox + sar(dx * t, 16), py = oy + sar(dy * t, 16), pz = oz + sar(dz * t, 16);
    u x = px >> 16, y = py >> 16, z = pz >> 16;
    u e = element(x, y, z), alb = couleur(x, y, z);
    u mat = (e >> 2) & 63;
    u nx = ((e >> 8) & 255) - 128, ny = ((e >> 16) & 255) - 128, nz = ((e >> 24) & 255) - 128;
    if (nx == 0 - (u)128) { nx = 0; ny = 127; nz = 0; }
    u lx = SOLEILS[12], ly = SOLEILS[13], lz = SOLEILS[14];
    u etat = 1, r = 0, g = 0, b = 0;
    if (mat == EAU) {
        u rx = dx + sdiv(bruit_lisse((x + temps) & MASQ, z & MASQ, 16) - 32768, 24);
        u rz = dz + sdiv(bruit_lisse(x & MASQ, (z + temps * 2) & MASQ, 16) - 32768, 24);
        u ry = 0 - dy;
        u lg = racine_entiere(rx * rx + ry * ry + rz * rz);
        rx = sdiv(rx * 65536, lg); ry = sdiv(ry * 65536, lg); rz = sdiv(rz * 65536, lg);
        u renvoi = profondeur > 0 ? regarder(px, (MER << 16) + 32768, pz, rx, ry, rz, profondeur - 1, temps) & 16777215
                                  : ciel(rx, ry, rz);
        u rasant = 65536 - (0 - dy);
        if (slt(0, dy)) rasant = 65536;
        u part = 64 + rasant * rasant / 65536 * 154 / 65536;
        u fr = (alb >> 16) & 255, fg = (alb >> 8) & 255, fb = alb & 255;
        r = (fr * (256 - part) + ((renvoi >> 16) & 255) * part) / 256;
        g = (fg * (256 - part) + ((renvoi >> 8) & 255) * part) / 256;
        b = (fb * (256 - part) + (renvoi & 255) * part) / 256;
        etat = 2;
    } else {
        u nl = sdiv(nx * lx + ny * ly + nz * lz, 127);
        if (!slt(0, nl)) nl = 0;
        u vus = 0, ouverts = 0;
        int connu = 0;
        u tt = (z >> 8) * TUILES + (x >> 8);
        u e0 = DIRE[tt][IX((((x >> 3) & 31) << 10) + (((y >> 3) & 31) << 5) + ((z >> 3) & 31))];
        if (e0 >= 16 && e0 < ((u)1 << 62)) {
            u iv = ((x & 7) << 6) | ((y & 7) << 3) | (z & 7), dec = (iv & 7) * 8;
            u sb = (SOLC[tt][IX((e0 - 16) * 64 + (iv >> 3))] >> dec) & 255;
            if (sb >= 128) { connu = 1; vus = sb & 15; ouverts = (CIELC[tt][IX((e0 - 16) * 64 + (iv >> 3))] >> dec) & 15; }
        }
        if (!connu) { vus = soleil_depuis(px + nx * 600, py + ny * 600, pz + nz * 600, nx, ny, nz); ouverts = ciel_depuis(px + nx * 600, py + ny * 600, pz + nz * 600, nx, ny, nz); }
        if (slt(0, nl)) { if (vus == 4) etat = 2; else if (vus > 0) etat = 3; }
        u ciel_part = 40 + ouverts * 30;
        u soleil = nl * vus / 4 * 256 / 65536;
        u lr = 76 * ciel_part / 160 + soleil * 255 / 256 + 20, lg2 = 88 * ciel_part / 160 + soleil * 238 / 256 + 18,
          lb = 112 * ciel_part / 160 + soleil * 210 / 256 + 14;
        r = ((alb >> 16) & 255) * lr / 200; g = ((alb >> 8) & 255) * lg2 / 200; b = (alb & 255) * lb / 200;
    }
    u d = (t >> 16) * RD / RN;
    u brume = d * d / 1600;
    if (brume > 220) brume = 220;
    r = (r * (256 - brume) + 200 * brume) / 256;
    g = (g * (256 - brume) + 214 * brume) / 256;
    b = (b * (256 - brume) + 230 * brume) / 256;
    return (etat << 24) | rgb24(r, g, b);
}

static void rendre_cubes(u cx, u cy, u cz, u lacet, u tangage, u temps) {
    u sl = sin1024(lacet), cl = cos1024(lacet), st = sin1024(tangage), ct = cos1024(tangage);
    u fx = sdiv(sl * ct, 65536), fy = st, fz = sdiv(cl * ct, 65536);
    u rx = cl, rz = 0 - sl;
    u ux = sdiv(0 - sl * st, 65536), uy = ct, uz = sdiv(0 - cl * st, 65536);
    long yy;
#pragma omp parallel for schedule(dynamic, 4)
    for (yy = 0; yy < H; yy++) {
        u y = (u)yy, n0 = 0, n1 = 0, n2 = 0, n3 = 0;
        u sy = sdiv((H - 2 * y - 1) * 45889, W);
        for (u x = 0; x < W; x++) {
            u sx = sdiv((2 * x + 1 - W) * 45889, W);
            u dx = fx + sdiv(rx * sx + ux * sy, 65536), dy = fy + sdiv(uy * sy, 65536), dz = fz + sdiv(rz * sx + uz * sy, 65536);
            u lg = racine_entiere(dx * dx + dy * dy + dz * dz);
            dx = sdiv(dx * 65536, lg); dy = sdiv(dy * 65536, lg); dz = sdiv(dz * 65536, lg);
            u v = regarder(cx, cy, cz, dx, dy, dz, 1, temps);
            u etat = v >> 24;
            if (etat == 0) n0++; else if (etat == 1) n1++; else if (etat == 2) n2++; else n3++;
            ECRAN[y * W + x] = v & 16777215;
        }
        COMPTE[4 * y] = n0; COMPTE[4 * y + 1] = n1; COMPTE[4 * y + 2] = n2; COMPTE[4 * y + 3] = n3;
    }
}

static double ms(struct timespec a, struct timespec b) { return (b.tv_sec - a.tv_sec) * 1e3 + (b.tv_nsec - a.tv_nsec) / 1e6; }

int main(void) {
    u IMAGES = getenv("CUBES_IMAGES") ? (u)atoll(getenv("CUBES_IMAGES")) : 48;
    HCOL = calloc(MONDE * MONDE, sizeof(u));
    PENTE = calloc(MONDE * MONDE, sizeof(u));
    for (u t = 0; t < TUILES * TUILES; t++) { DIRE[t] = calloc(32768 * PAS, sizeof(u)); DIRT[t] = calloc(32768 * PAS, sizeof(u)); }
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
    preparer_soleil(360, 70);
    clock_gettime(CLOCK_MONOTONIC, &t0);
    ranger_lumiere(1);
    clock_gettime(CLOCK_MONOTONIC, &t1);
    printf("les calques de lumiere : %.0f ms\n", ms(t0, t1));
    u ay = GLOB[0];
    double total = 0;
    u avant = IMAGES * 7 / 12;
    for (u i = 0; i < IMAGES; i++) {
        clock_gettime(CLOCK_MONOTONIC, &ti);
        if (TOURNE == 1) { preparer_soleil(300 + i * 3, 50 + i); ranger_lumiere(0); }
        u cx = ARCHE_X * 65536, cy, cz;
        if (i < avant) {
            cy = (u)110 * 65536 * RN / RD - (((u)110 * RN / RD - ay - (u)12 * RN / RD) * 65536 / avant) * i;
            cz = (u)470 * 65536 * RN / RD - ((u)170 * 65536 * RN / RD / avant) * i;
        } else {
            u j = i - avant, reste = IMAGES - avant;
            cy = (ay + (u)12 * RN / RD) * 65536 + sdiv(((u)64 * RN / RD - ay - (u)12 * RN / RD) * 65536, reste) * j;
            cz = ARCHE_Z * 65536 - ((u)110 * 65536 * RN / RD / reste) * j;
        }
        u lacet = 512;
        u vy = (ay + (u)14 * RN / RD) * 65536 - cy;
        u tangage = 0, vu = 0 - ((u)1 << 62);
        for (u k = 0; k < 129; k++) {
            u a = (k + 1024 - 64) & 1023;
            u p = sdiv(vy, 256) * sin1024(a) + ((u)80 * 256 * RN / RD) * cos1024(a);
            if (slt(vu, p)) { vu = p; tangage = a; }
        }
        rendre_cubes(cx, cy, cz, lacet, tangage, i * 3);
        clock_gettime(CLOCK_MONOTONIC, &tf);
        total += ms(ti, tf);
        if (getenv("CUBES_DETAIL")) printf("image %llu : %.0f ms\n", (unsigned long long)i + 1, ms(ti, tf));
    }
    if (getenv("CUBES_PPM")) {
        FILE *f = fopen(getenv("CUBES_PPM"), "wb");
        fprintf(f, "P6 %d %d 255\n", W, H);
        for (u i = 0; i < W * H; i++) { unsigned char p[3] = {ECRAN[i] >> 16, ECRAN[i] >> 8, ECRAN[i]}; fwrite(p, 1, 3, f); }
        fclose(f);
    }
    u h = 14695981039346656037u;
    for (u i = 0; i < W * H; i++) h = (h ^ ECRAN[i]) * 1099511628211u;
    printf("%llu images en %.0f ms (%.0f ms par image)\n", (unsigned long long)IMAGES, total, total / IMAGES);
    printf("empreinte : %lld\n", (long long)h);
    return 0;
}
