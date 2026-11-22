/* Belenos : le val des neiges, le même calcul en C (la référence de comparaison).
 * Copie fidèle de val_scene.vtx + val_banc.vtx : mots de 64 bits non signés, les opérations signées (./ .< .>) par
 * conversion en int64_t. Doit donner la même empreinte que `lugus belenos/val_banc.vtx`.
 *     cc -O2 -o val_ref belenos/val_ref.c && ./val_ref
 * Œuvre protégée de son créateur : ne pas diffuser hors du projet. */
#include <stdint.h>
#include <stdio.h>
#include <time.h>

typedef uint64_t u;
typedef int64_t s;

#define W 480
#define H 270
#define G 512
#define MASQUE 511
#define NPAS 400
#define BANDE 16
#define ECHELLE 220
#define NOMBRE 17
#define IMAGES 12

static u HAUT[G * G], COUL[G * G], ALB[G * G];
static u SINUS[1024], INV[NPAS], DIST[NPAS], BRUME[NPAS], YBUF[W], OMB[NOMBRE];
static u ECRAN[W * H];            /* 0xRRGGBB */

static u sdiv(u a, u b) { return (u)((s)a / (s)b); }
static int slt(u a, u b) { return (s)a < (s)b; }
static u rgb(u r, u g, u b) { return ((r & 255) << 16) | ((g & 255) << 8) | (b & 255); }

static u hache(u x, u z) {
    u h = (x & MASQUE) * 374761393u + (z & MASQUE) * 668265263u + 1013904223u;
    h = (h ^ (h >> 13)) * 1274126177u;
    return (h ^ (h >> 16)) & 65535;
}

static u bruit_lisse(u x, u z, u p) {
    u x0 = x / p, z0 = z / p;
    u fx = (x % p) * 256 / p, fz = (z % p) * 256 / p;
    u sx = fx * fx * (768 - 2 * fx) / 65536;
    u sz = fz * fz * (768 - 2 * fz) / 65536;
    u pg = G / p;
    u a = hache(x0 % pg, z0 % pg), b = hache((x0 + 1) % pg, z0 % pg);
    u c = hache(x0 % pg, (z0 + 1) % pg), d = hache((x0 + 1) % pg, (z0 + 1) % pg);
    u h1 = (a * (256 - sx) + b * sx) / 256;
    u h2 = (c * (256 - sx) + d * sx) / 256;
    return (h1 * (256 - sz) + h2 * sz) / 256;
}

static void creer_relief(void) {
    for (u z = 0; z < G; z++)
        for (u x = 0; x < G; x++) {
            u h = bruit_lisse(x, z, 256) * 16 + bruit_lisse(x, z, 128) * 8 + bruit_lisse(x, z, 64) * 4 +
                  bruit_lisse(x, z, 32) * 2 + bruit_lisse(x, z, 16);
            u n = h / 31, m = 0;
            if (n > 20000) m = (n - 20000) * 2;
            if (m > 65535) m = 65535;
            HAUT[z * G + x] = m * m / 65536 * 5 / 2 + n / 6;
        }
}

static void peindre_relief(void) {
    for (u z = 0; z < G; z++)
        for (u x = 0; x < G; x++) {
            u h = HAUT[z * G + x], hx = HAUT[z * G + ((x + 1) & MASQUE)], hz = HAUT[((z + 1) & MASQUE) * G + x];
            u pente = 0;
            pente += hx > h ? hx - h : h - hx;
            pente += hz > h ? hz - h : h - hz;
            u r = 70, g = 110, b = 60;
            if (pente > 700) { r = 110; g = 105; b = 100; }
            else if (h > 30000 || (h > 20000 && pente < 260)) { r = 235; g = 238; b = 245; }
            else if (h > 12000) { r = 120; g = 115; b = 80; }
            u grain = hache(x * 7, z * 13) & 15;
            r += grain; g += grain; b += grain;
            if (r > 255) r = 255;
            if (g > 255) g = 255;
            if (b > 255) b = 255;
            ALB[z * G + x] = r * 65536 + g * 256 + b;
        }
}

static u sin1024(u a) { return SINUS[a & 1023]; }
static u cos1024(u a) { return SINUS[(a + 256) & 1023]; }
static u hauteur_en(u x, u z) { return HAUT[(z & MASQUE) * G + (x & MASQUE)]; }

static u racine_entiere(u x) {
    u r = 0, v = x, b = 4611686018427387904ull;
    while (b > v) b >>= 2;
    while (b != 0) {
        if (v >= r + b) { v -= r + b; r = (r >> 1) + b; } else r >>= 1;
        b >>= 2;
    }
    return r;
}

static void eclairer_ligne(u z, u az, u el) {
    u se = sin1024(el), ce = cos1024(el);
    u lx = sdiv(ce * sin1024(az), 65536), lz = sdiv(ce * cos1024(az), 65536), ly = se;
    u chaud = 256;
    if (slt(se, 30000)) { chaud = 96 + se * 160 / 30000; if (slt(se, 0)) chaud = 96; }
    u sr = 255, sg = 150 + chaud * 100 / 256, sb = 90 + chaud * 160 / 256;
    u montee = 0;
    if (slt(0, se) && slt(0, ce)) montee = se * 256 / ce;
    for (u x = 0; x < G; x++) {
        u h = HAUT[z * G + x];
        u gx = hauteur_en(x + 1, z) - hauteur_en(x + G - 1, z);
        u gz = hauteur_en(x, z + 1) - hauteur_en(x, z + G - 1);
        u n2 = gx * gx + 262144 + gz * gz;
        u nl = racine_entiere(n2);
        u pd = (0 - gx) * lx + 512 * ly + (0 - gz) * lz;
        u diffus = 0;
        if (slt(0, pd)) diffus = sdiv(pd, nl) / 256;
        if (diffus > 256) diffus = 256;
        u lumiere = 256;
        if (!slt(0, se)) lumiere = 0;
        else if (diffus > 0) {
            for (u k = 0; k < NOMBRE && lumiere > 0; k++) {
                u d = OMB[k];
                u px = x + sdiv(sin1024(az) * d, 65536);
                u pz = z + sdiv(cos1024(az) * d, 65536);
                u ht = hauteur_en(px, pz);
                u rayon = h + montee * d;
                if (ht > rayon - d * 6) {
                    u cache = (ht - rayon + d * 6) * 256 / (d * 12);
                    if (cache > 256) cache = 256;
                    if (256 - cache < lumiere) lumiere = 256 - cache;
                }
            }
        }
        u direct = diffus * lumiere / 256;
        u c = ALB[z * G + x];
        u r = (c >> 16) & 255, g = (c >> 8) & 255, b = c & 255;
        u rr = r * (60 + direct * sr / 256) / 256;
        u gg = g * (68 + direct * sg / 256) / 256;
        u bb = b * (84 + direct * sb / 256) / 256;
        if (rr > 255) rr = 255;
        if (gg > 255) gg = 255;
        if (bb > 255) bb = 255;
        COUL[z * G + x] = rr * 65536 + gg * 256 + bb;
    }
}

static void preparer_tables(void) {
    static const u d_ombre[NOMBRE] = {1, 2, 3, 4, 6, 8, 11, 15, 20, 27, 36, 48, 64, 85, 113, 150, 200};
    for (int k = 0; k < NOMBRE; k++) OMB[k] = d_ombre[k];
    for (u a = 0; a < 1024; a++) {
        u uu = a & 511;
        u v = 4 * uu * (512 - uu) * 65536 / (327680 - uu * (512 - uu));
        SINUS[a] = a >= 512 ? 0 - v : v;
    }
    u dist = 256;
    for (u k = 0; k < NPAS; k++) {
        DIST[k] = dist;
        INV[k] = (u)65536 * ECHELLE * 256 / dist;
        BRUME[k] = k * k * 256 / (NPAS * NPAS);
        dist = dist + 64 + dist / 60;
    }
}

static u embrume(u c, u part) {
    u r = ((c >> 16) & 255) * (256 - part) + 200 * part;
    u g = ((c >> 8) & 255) * (256 - part) + 214 * part;
    u b = (c & 255) * (256 - part) + 230 * part;
    return rgb(r / 256, g / 256, b / 256);
}

static void rendre(u cx, u cz, u ch, u a, u hor, u az, u el) {
    u se = sin1024(el), soir = 0;
    if (slt(se, 24000)) { soir = 160 - se * 160 / 24000; if (slt(se, 0)) soir = 160; }
    for (u y = 0; y < H; y++) {
        u t = y * 256 / H;
        u r = (0x5A * (256 - t) + (0xC8 + soir * 55 / 160) * t) / 256;
        u g = (0x7C * (256 - t) + (0xD6 - soir * 40 / 160) * t) / 256;
        u b = (0xB4 * (256 - t) + (0xE6 - soir * 110 / 160) * t) / 256;
        u c = rgb(r, g, b);
        for (u x = 0; x < W; x++) ECRAN[y * W + x] = c;
    }
    u ecart_s = (az - a + 512) & 1023;
    if (ecart_s > 512 - 85 && ecart_s < 512 + 85 && slt(0, se)) {
        u sx = W / 2 + sdiv((ecart_s - 512) * (W / 2), 85);
        u sy_haut = sdiv(se * ECHELLE, cos1024(el));
        if (sy_haut < hor + 20) {
            u sy = hor - sy_haut;
            for (u ddy = 0; ddy < 17; ddy++)
                for (u ddx = 0; ddx < 17; ddx++) {
                    u ex = ddx - 8, ey = ddy - 8;
                    if (ex * ex + ey * ey < 64) {
                        u qx = sx + ex, qy = sy + ey;
                        if (qx < W && qy < H) ECRAN[qy * W + qx] = rgb(255, 245, 220);
                    }
                }
        }
    }
    for (u x = 0; x < W; x++) YBUF[x] = H;
    u sa = SINUS[a & 1023], ca = SINUS[(a + 256) & 1023];
    for (u x = 0; x < W; x++) {
        u ecart = x * 2 * 37837 / W;
        u e = ecart - 37837;
        u dx = sa + sdiv(e * ca, 65536);
        u dz = ca - sdiv(e * sa, 65536);
        u haut = H;
        for (u k = 0; k < NPAS && haut > 0; k++) {
            u dist = DIST[k];
            u px = (cx + sdiv(dx * dist, 256)) >> 16;
            u pz = (cz + sdiv(dz * dist, 256)) >> 16;
            u cell = (pz & MASQUE) * G + (px & MASQUE);
            u h = HAUT[cell], inv = INV[k];
            u ys = 0;
            u dessus = ch * inv / 16777216, dessous = h * inv / 16777216;
            if (hor + dessus > dessous) ys = hor + dessus - dessous;
            if (ys < haut) {
                u cc = embrume(COUL[cell], BRUME[k]);
                for (u yy = ys; yy < haut; yy++) ECRAN[yy * W + x] = cc;
                haut = ys;
            }
        }
    }
}

static double ms(struct timespec a, struct timespec b) {
    return (b.tv_sec - a.tv_sec) * 1e3 + (b.tv_nsec - a.tv_nsec) / 1e6;
}

int main(void) {
    struct timespec t0, t1, t2;
    clock_gettime(CLOCK_MONOTONIC, &t0);
    preparer_tables();
    creer_relief();
    peindre_relief();
    u az = 640, el = 71;
    for (u z = 0; z < G; z++) eclairer_ligne(z, az, el);
    clock_gettime(CLOCK_MONOTONIC, &t1);
    u cx = ((u)1 << 40) + (G / 2) * 65536, cz = ((u)1 << 40) + (G / 2) * 65536, a = 0, bande = 0;
    for (int n = 0; n < IMAGES; n++) {
        u sa = SINUS[a & 1023], ca = SINUS[(a + 256) & 1023];
        cx += sdiv(sa, 2);
        cz += sdiv(ca, 2);
        a = (a + 6) & 1023;
        az = (az + 4) & 1023;
        for (u q = 0; q < BANDE; q++) eclairer_ligne((bande + q) & MASQUE, az, el);
        bande = (bande + BANDE) & MASQUE;
        u sol = HAUT[((cz >> 16) & MASQUE) * G + ((cx >> 16) & MASQUE)];
        rendre(cx, cz, sol + 4000, a, H / 3, az, el);
    }
    clock_gettime(CLOCK_MONOTONIC, &t2);
    u h = 14695981039346656037ull;
    for (int i = 0; i < W * H; i++) h = (h ^ ECRAN[i]) * 1099511628211ull;
    printf("empreinte : %lld\n", (long long)h);
    fprintf(stderr, "préparation %.1f ms, %d images en %.1f ms (%.2f ms par image)\n", ms(t0, t1), IMAGES, ms(t1, t2),
            ms(t1, t2) / IMAGES);
    return 0;
}
