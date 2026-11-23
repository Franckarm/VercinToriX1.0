/* Belenos : le val des neiges, le même calcul en C (la référence de comparaison).
 * Copie fidèle de val_scene.vtx + val_banc.vtx : mots de 64 bits non signés, les opérations signées (./ .< .>) par
 * conversion en int64_t. Doit donner la même empreinte que `lugus belenos/val_banc.vtx`.
 *     cc -O2 -o val_ref belenos/val_ref.c && ./val_ref
 * Œuvre protégée de son créateur : ne pas diffuser hors du projet. */
#include <stdint.h>
#include <stdio.h>
#include <time.h>
#include <stdlib.h>

typedef uint64_t u;
typedef int64_t s;

#define W 1280
#define H 720
#define G 512
#define MASQUE 511
#define NPAS 400
#define BANDE 16
#define ECHELLE 587
#define DISQUE 24
#define IMAGES 12

static u HAUT[G * G], COUL[G * G], ALB[G * G];
static u SINUS[1024], INV[NPAS], DIST[NPAS], BRUME[NPAS];
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

static u NUNIT[G * G], INVW[1024], OMBRE[G * G], FEUR[G * G], TEINTES[7];
static u ETAT[G * G], COMPTE[4 * G], NXT[G * G], NZT[G * G], NLT[G * G];

/* 0.79 : la pente de chaque case, calculée une fois */
static void preparer_normales(void) {
    for (u z = 0; z < G; z++)
        for (u x = 0; x < G; x++) {
            u gx = hauteur_en(x + 1, z) - hauteur_en(x + G - 1, z);
            u gz = hauteur_en(x, z + 1) - hauteur_en(x, z + G - 1);
            NXT[z * G + x] = 0 - gx;
            NZT[z * G + x] = 0 - gz;
            u lg_ = racine_entiere(gx * gx + 262144 + gz * gz);
            NLT[z * G + x] = lg_;
            u ux_ = sdiv((0 - gx) * 4096, lg_), uy_ = 512 * 4096 / lg_, uz_ = sdiv((0 - gz) * 4096, lg_);
            NUNIT[z * G + x] = ((ux_ + 8192) << 28) | (uy_ << 14) | (uz_ + 8192);
        }
}

/* 0.80 : l'ombre et la lumière ensemble (comme val_scene.vtx) : l'ouverture au ciel, les feux, le balayage aller-retour */
#define NFEUX 8
#define RAYON 40
#define NOIR 24
static u OUV[G * G], FEU[G * G], PYR1[256 * 256], PYR2[128 * 128], PYR3[64 * 64], PYR4[32 * 32], FOYERS[6 * NFEUX];
static u RV1[256 * 256], RV2[128 * 128], RV3[64 * 64], RV4[32 * 32];
static u REGLES, DIRS[16], BRUMEC[3];

static void preparer_ouverture(void) {
    for (u oz = 0; oz < G; oz++)
        for (u ox = 0; ox < G; ox++) {
            u oh = HAUT[oz * G + ox], occ = 0;
            for (u dir = 0; dir < 8; dir++) {
                u ux = DIRS[2 * dir], uz = DIRS[2 * dir + 1];
                u pas = (dir & 1) == 1 ? 362 : 256;
                u m = 0;
                for (u d = 3; d < 40; d = d * 2) {
                    u e = hauteur_en(ox + ux * d, oz + uz * d) - oh;
                    if (slt(0, e)) {
                        u t = e * 256 / (d * pas);
                        if (t > m) m = t;
                    }
                }
                occ = occ + m * m * 256 / (m * m + 65536);
            }
            u ouv = 256 - occ / 8;
            if (ouv < 16) ouv = 16;
            OUV[oz * G + ox] = ouv;
        }
}

static void preparer_feux(void) {
    u n = 0, k = 0;
    while (n < NFEUX && k < 4096) {
        u fx = hache(k * 31 + 5, k * 17 + 3) & MASQUE;
        u fz = hache(k * 13 + 11, k * 29 + 7) & MASQUE;
        u fh = hauteur_en(fx, fz);
        u gx = NXT[fz * G + fx], gz = NZT[fz * G + fx];
        if (slt(gx, 0)) gx = 0 - gx;
        if (slt(gz, 0)) gz = 0 - gz;
        u bon = 0;
        if (fh < 14000 && gx + gz < 500) bon = 1;
        for (u q = 0; q < n; q++) {
            u ax = (fx + G - FOYERS[6 * q]) & MASQUE, az2 = (fz + G - FOYERS[6 * q + 1]) & MASQUE;
            if (ax > G / 2) ax = G - ax;
            if (az2 > G / 2) az2 = G - az2;
            if (ax < 60 && az2 < 60) bon = 0;
        }
        if (bon == 1) {
            u *f = FOYERS + 6 * n;
            f[0] = fx; f[1] = fz; f[2] = fh + 768;
            u sorte = n % 3;
            if (sorte == 0) { f[3] = 1115; f[4] = 612; f[5] = 262; }
            else if (sorte == 1) { f[3] = 955; f[4] = 337; f[5] = 150; }
            else { f[3] = 638; f[4] = 538; f[5] = 375; }
            n++;
        }
        k++;
    }
    REGLES = 1;
}

static void eclairer_feux(void) {
    for (u vz = 0; vz < G; vz++)
        for (u vx = 0; vx < G; vx++) {
            u cell = vz * G + vx, hc = HAUT[cell], lr = 0, lg = 0, lb = 0, foyer = 0;
            for (u f = 0; f < NFEUX; f++) {
                u *fb = FOYERS + 6 * f;
                u fx = fb[0], fz = fb[1], hs = fb[2];
                u ddx = ((vx + G + G / 2 - fx) & MASQUE) - G / 2;
                u ddz = ((vz + G + G / 2 - fz) & MASQUE) - G / 2;
                if (slt(ddx, RAYON) && slt(0 - RAYON, ddx) && slt(ddz, RAYON) && slt(0 - RAYON, ddz)) {
                    u d2 = ddx * ddx + ddz * ddz;
                    if (d2 < RAYON * RAYON) {
                        if (d2 <= 2) foyer = 1;
                        u dd = racine_entiere(d2 * 65536);
                        u reste_d = RAYON * 256 - dd;
                        u att = reste_d * reste_d / (RAYON * RAYON * 256);
                        u adx = slt(ddx, 0) ? 0 - ddx : ddx, adz = slt(ddz, 0) ? 0 - ddz : ddz;
                        u nmax = adz > adx ? adz : adx;
                        u vis = 256, face = 256;
                        if (nmax > 1) {
                            u cible = hc + 128, pire = 0 - (u)1000000000;
                            for (u t = 1; t < nmax; t++) {
                                u sx = fx + sdiv(ddx * t, nmax), sz = fz + sdiv(ddz * t, nmax);
                                u hy = hs + sdiv((cible - hs) * t, nmax);
                                u m = hauteur_en(sx, sz) - hy;
                                if (slt(pire, m)) pire = m;
                            }
                            if (!slt(pire, 160)) vis = 0;
                            else if (slt(0 - 160, pire)) vis = 256 - sdiv((pire + 160) * 128, 160);
                            u wx = (0 - ddx) * 256, wz = (0 - ddz) * 256, wy = hs - hc;
                            u pd = NXT[cell] * wx + 512 * wy + NZT[cell] * wz;
                            face = 0;
                            if (slt(0, pd)) {
                                u lv = racine_entiere(wx * wx + wy * wy + wz * wz);
                                face = sdiv(sdiv(pd, NLT[cell]) * 256, lv);
                                if (face > 256) face = 256;
                            }
                        }
                        u part = att * vis / 256 * face / 256;
                        lr += fb[3] * part / 256;
                        lg += fb[4] * part / 256;
                        lb += fb[5] * part / 256;
                    }
                }
            }
            if (lr > 4095) lr = 4095;
            if (lg > 4095) lg = 4095;
            if (lb > 4095) lb = 4095;
            FEU[cell] = (foyer << 60) | (lr << 32) | (lg << 16) | lb;
            u alb = ALB[cell], fr = ((alb >> 16) & 255) * lr / 256, fg = ((alb >> 8) & 255) * lg / 256, fb2 = (alb & 255) * lb / 256;
            if (fr > 255) fr = 255;
            if (fg > 255) fg = 255;
            if (fb2 > 255) fb2 = 255;
            FEUR[cell] = (fr << 32) | (fg << 16) | fb2;
        }
}

/* 0.802 : la pyramide de cubes des renvois (comme val_scene.vtx) */
static void reduire(u *dessous, u *dessus, u n) {
    for (u rz = 0; rz < n; rz++)
        for (u rx = 0; rx < n; rx++) {
            u *s0 = dessous + 4 * rz * n + 2 * rx;
            dessus[rz * n + rx] = s0[0] + s0[1] + s0[2 * n] + s0[2 * n + 1];
        }
}

static u lire_niveau(const u *base, u nn, u l, u x, u z) {
    u mk = nn - 1;
    u uu = ((x * 256 + 128) >> l) + nn * 256 - 128, v = ((z * 256 + 128) >> l) + nn * 256 - 128;
    u ix = (uu >> 8) & mk, iz = (v >> 8) & mk, ix1 = (ix + 1) & mk, iz1 = (iz + 1) & mk, tx = uu & 255, tz = v & 255;
    u pa = base[iz * nn + ix], pb = base[iz * nn + ix1], pc = base[iz1 * nn + ix], pd = base[iz1 * nn + ix1];
    u wa = (256 - tx) * (256 - tz), wb = tx * (256 - tz), wc = (256 - tx) * tz, wd = tx * tz;
    u vr = (((pa >> 32) & 65535) * wa + ((pb >> 32) & 65535) * wb + ((pc >> 32) & 65535) * wc + ((pd >> 32) & 65535) * wd) >> 16;
    u vg = (((pa >> 16) & 65535) * wa + ((pb >> 16) & 65535) * wb + ((pc >> 16) & 65535) * wc + ((pd >> 16) & 65535) * wd) >> 16;
    u vb = ((pa & 65535) * wa + (pb & 65535) * wb + (pc & 65535) * wc + (pd & 65535) * wd) >> 16;
    return (vr << 32) | (vg << 16) | vb;
}

static void descendre(const u *dessus, const u *somme, u *dessous, u n, u num, u den) {
    for (u dz = 0; dz < n; dz++)
        for (u dx = 0; dx < n; dx++) {
            u up = lire_niveau(dessus, n / 2, 1, dx, dz), sm = somme[dz * n + dx];
            u vr = ((up >> 32) & 65535) + ((sm >> 32) & 65535) * num / den;
            u vg = ((up >> 16) & 65535) + ((sm >> 16) & 65535) * num / den;
            u vb = (up & 65535) + (sm & 65535) * num / den;
            dessous[dz * n + dx] = (vr << 32) | (vg << 16) | vb;
        }
}

static void construire_pyramide(void) {
    u sr = TEINTES[3], sg = TEINTES[4], sb = TEINTES[5], feux = TEINTES[6];
    for (u qz = 0; qz < 256; qz++)
        for (u qx = 0; qx < 256; qx++) {
            u c0 = 2 * qz * G + 2 * qx, somme = 0;
            for (u k = 0; k < 4; k++) {
                u c = c0 + (k & 1) + (k >> 1) * G;
                u d = OMBRE[c] >> 2, alb = ALB[c], fr = FEUR[c] * feux;
                u or_ = ((alb >> 16) & 255) * (d * sr / 256) / 256 + ((fr >> 32) & 65535);
                u og = ((alb >> 8) & 255) * (d * sg / 256) / 256 + ((fr >> 16) & 65535);
                u ob = (alb & 255) * (d * sb / 256) / 256 + (fr & 65535);
                if (or_ > 255) or_ = 255;
                if (og > 255) og = 255;
                if (ob > 255) ob = 255;
                somme += (or_ << 32) | (og << 16) | ob;
            }
            PYR1[qz * 256 + qx] = somme;
        }
    reduire(PYR1, PYR2, 128);
    reduire(PYR2, PYR3, 64);
    reduire(PYR3, PYR4, 32);
    for (u hz = 0; hz < 32; hz++)
        for (u hx = 0; hx < 32; hx++) {
            u q4 = PYR4[hz * 32 + hx];
            RV4[hz * 32 + hx] = (((q4 >> 32) & 65535) / 64 << 32) | (((q4 >> 16) & 65535) / 64 << 16) | ((q4 & 65535) / 64);
        }
    descendre(RV4, PYR3, RV3, 64, 1, 16);
    descendre(RV3, PYR2, RV2, 128, 5, 16);
    descendre(RV2, PYR1, RV1, 256, 3, 2);
}

static void eclairer_lignes(u n0, u n1, u az, u el) {
    u se_vrai = sin1024(el), l_az = az, l_el = el, lune = 0;
    if (slt(se_vrai, 0)) { lune = 1; l_az = (az + 512) & 1023; l_el = 0 - el; }
    u se = sin1024(l_el), ce = cos1024(l_el), sa = sin1024(l_az), ca = cos1024(l_az);
    u lx = sdiv(ce * sa, 65536), lz = sdiv(ce * ca, 65536), ly = se;
    u chaud = 256;
    if (slt(se, 30000)) { chaud = 96 + se * 160 / 30000; if (slt(se, 0)) chaud = 96; }
    u sr = 255, sg = 150 + chaud * 100 / 256, sb = 90 + chaud * 160 / 256;
    if (lune == 1) { sr = 60; sg = 72; sb = 104; }
    TEINTES[3] = sr; TEINTES[4] = sg; TEINTES[5] = sb;
    u montee = 0;
    if (slt(0, se) && slt(0, ce)) montee = se * 256 / ce;
    u asa = slt(sa, 0) ? 0 - sa : sa, aca = slt(ca, 0) ? 0 - ca : ca;
    u axe_x = asa >= aca, dmaj = 1, dmin;
    if (axe_x) { if (slt(0, sa)) dmaj = 0 - 1; dmin = sdiv((0 - ca) * 65536, asa); }
    else { if (slt(0, ca)) dmaj = 0 - 1; dmin = sdiv((0 - sa) * 65536, aca); }
    u longueur = racine_entiere((u)65536 * 65536 + dmin * dmin);
    u chute = montee * longueur / 65536;
    for (u n = n0; n < n1; n++) {
        u ligne = n & MASQUE;
        u horizon = 0 - (u)1000000000, docc = 0, nv = 0, nf = 0, nvar = 0;
        for (u i = 0; i < 2 * G; i++) {
            u maj = (i * dmaj) & MASQUE;
            u mino = ((u)((s)((ligne << 16) + i * dmin) >> 16)) & MASQUE;
            u x = maj, z = mino;
            if (!axe_x) { x = mino; z = maj; }
            u cell = z * G + x;
            u h = HAUT[cell];
            horizon = horizon - chute;
            docc = docc + 1;
            if (i >= G) {
                u nu = NUNIT[cell];
                u dot = (((nu >> 28) & 16383) - 8192) * lx + ((nu >> 14) & 16383) * ly + ((nu & 16383) - 8192) * lz;
                u diffus = 0;
                if (slt(0, dot)) diffus = dot >> 20;
                if (diffus > 256) diffus = 256;
                u marge = horizon - h, dc = docc > 1023 ? 1023 : docc, w = 12 + dc * 6, lumiere = 256;
                if (!slt(0, se) || diffus == 0) lumiere = 0;
                else if (!slt(marge, w)) lumiere = 0;
                else if (slt(0 - w, marge)) lumiere = 256 - (((marge + w) * INVW[dc]) >> 16);
                u direct = diffus * lumiere / 256;
                u etat = 1;
                if (direct > 0) etat = lumiere == 256 ? 2 : 3;
                OMBRE[cell] = (direct << 2) | etat;
                if (etat == 2) nv++; else if (etat == 1) nf++; else nvar++;
            }
            if (slt(horizon, h)) { horizon = h; docc = 0; }
        }
        COMPTE[4 * ligne] = 0; COMPTE[4 * ligne + 1] = nf; COMPTE[4 * ligne + 2] = nv; COMPTE[4 * ligne + 3] = nvar;
    }
}

static u teinte(u cell, u px, u pz) {
    u fe = 0;
    if (TEINTES[6] == 1) { fe = FEU[cell]; if ((fe >> 60) == 1) return 0xFFFFC0; }
    u alb = ALB[cell], d = OMBRE[cell] >> 2, ouv = OUV[cell];
    u rv = lire_niveau(RV1, 256, 1, px, pz), recu = 128 + (256 - ouv) * 2;
    u tr = TEINTES[0] * ouv / 256 + d * TEINTES[3] / 256 + ((fe >> 32) & 65535) + ((rv >> 32) & 65535) * recu / 4096;
    u tg = TEINTES[1] * ouv / 256 + d * TEINTES[4] / 256 + ((fe >> 16) & 65535) + ((rv >> 16) & 65535) * recu / 4096;
    u tb = TEINTES[2] * ouv / 256 + d * TEINTES[5] / 256 + (fe & 65535) + (rv & 65535) * recu / 4096;
    u qr = ((alb >> 16) & 255) * tr / 256, qg = ((alb >> 8) & 255) * tg / 256, qb = (alb & 255) * tb / 256;
    if (qr > 255) qr = 255;
    if (qg > 255) qg = 255;
    if (qb > 255) qb = 255;
    return qr * 65536 + qg * 256 + qb;
}

static void eclairer_tout(u az, u el) {
    u se_vrai = sin1024(el), jour = 256;
    if (slt(se_vrai, 16000)) { jour = 0; if (slt(0 - 6000, se_vrai)) jour = (se_vrai + 6000) * 256 / 22000; }
    TEINTES[0] = 8 + 52 * jour / 256; TEINTES[1] = 11 + 57 * jour / 256; TEINTES[2] = 24 + 60 * jour / 256;
    TEINTES[6] = REGLES;
    eclairer_lignes(0, G, az, el);
    construire_pyramide();
}

static void preparer_tables(void) {
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
    for (u d = 0; d < 1024; d++) INVW[d] = 128 * 65536 / (12 + 6 * d);
    static const int dd[16] = {1, 0, 1, 1, 0, 1, -1, 1, -1, 0, -1, -1, 0, -1, 1, -1};
    for (int i = 0; i < 16; i++) DIRS[i] = (u)(s)dd[i];
}

static u embrume(u c, u part) {
    u r = ((c >> 16) & 255) * (256 - part) + BRUMEC[0] * part;
    u g = ((c >> 8) & 255) * (256 - part) + BRUMEC[1] * part;
    u b = (c & 255) * (256 - part) + BRUMEC[2] * part;
    return rgb(r / 256, g / 256, b / 256);
}

static u CIEL[H];

/* 0.78 : chaque point de l'écran écrit une fois (comme val_scene.vtx) : chaque colonne son relief, puis son ciel */
static void rendre(u cx, u cz, u ch, u a, u hor, u az, u el) {
    u se = sin1024(el), soir = 0;
    if (slt(se, 24000)) { soir = 160 - se * 160 / 24000; if (slt(se, 0)) soir = 160; }
    u nuit = 0;
    if (slt(se, 4000)) { nuit = 220; if (slt(0 - 6000, se)) nuit = (4000 - se) * 220 / 10000; }
    BRUMEC[0] = 200 * (256 - nuit) / 256 + nuit / 22;
    BRUMEC[1] = 214 * (256 - nuit) / 256 + nuit / 16;
    BRUMEC[2] = 230 * (256 - nuit) / 256 + nuit / 7;
    for (u y = 0; y < H; y++) {
        u t = y * 256 / H;
        u r = (0x5A * (256 - t) + (0xC8 + soir * 55 / 160) * t) / 256;
        u g = (0x7C * (256 - t) + (0xD6 - soir * 40 / 160) * t) / 256;
        u b = (0xB4 * (256 - t) + (0xE6 - soir * 110 / 160) * t) / 256;
        r = r * (256 - nuit) / 256 + nuit / 40;
        g = g * (256 - nuit) / 256 + nuit / 30;
        b = b * (256 - nuit) / 256 + nuit / 12;
        CIEL[y] = rgb(r, g, b);
    }
    u sx = 0, sy = 0, soleil_vu = 0;
    u astre_az = az, astre_el = el, astre_c = rgb(255, 245, 220), rayon2 = 455;
    if (slt(se, 0)) { astre_az = (az + 512) & 1023; astre_el = 0 - el; astre_c = rgb(225, 230, 245); rayon2 = 213; }
    u ase = sin1024(astre_el);
    u ecart_s = (astre_az - a + 512) & 1023;
    if (ecart_s > 512 - 85 && ecart_s < 512 + 85 && slt(0, ase)) {
        sx = W / 2 + sdiv((ecart_s - 512) * (W / 2), 85);
        u sy_haut = sdiv(ase * ECHELLE, cos1024(astre_el));
        if (sy_haut < hor + 53) { sy = hor - sy_haut; soleil_vu = 1; }
    }
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
                u cc = embrume(teinte(cell, px & MASQUE, pz & MASQUE), BRUME[k]);
                for (u yy = ys; yy < haut; yy++) ECRAN[yy * W + x] = cc;
                haut = ys;
            }
        }
        u ex = x - sx;
        for (u yc = 0; yc < haut; yc++) {
            u pc = CIEL[yc];
            if (soleil_vu == 1 && slt(ex, DISQUE) && slt(0 - DISQUE, ex)) {
                u ey = yc - sy;
                if (slt(ey, DISQUE) && slt(0 - DISQUE, ey) && ex * ex + ey * ey < rayon2) pc = astre_c;
            }
            ECRAN[yc * W + x] = pc;
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
    preparer_normales();
    preparer_ouverture();
    preparer_feux();
    eclairer_feux();
    u az = 640, el = 71;
    eclairer_tout(az, el);
    clock_gettime(CLOCK_MONOTONIC, &t1);
    u cx = ((u)1 << 40) + (G / 2) * 65536, cz = ((u)1 << 40) + (G / 2) * 65536, a = 0;
    for (int n = 0; n < IMAGES; n++) {
        u sa = SINUS[a & 1023], ca = SINUS[(a + 256) & 1023];
        cx += sdiv(sa, 2);
        cz += sdiv(ca, 2);
        a = (a + 6) & 1023;
        az = (az + 4) & 1023;
        eclairer_tout(az, el);
        u sol = HAUT[((cz >> 16) & MASQUE) * G + ((cx >> 16) & MASQUE)];
        rendre(cx, cz, sol + 4000, a, H / 3, az, el);
    }
    clock_gettime(CLOCK_MONOTONIC, &t2);
    u h = 14695981039346656037ull;
    for (int i = 0; i < W * H; i++) h = (h ^ ECRAN[i]) * 1099511628211ull;
    printf("empreinte : %lld\n", (long long)h);
    /* VAL_DESSUS=fichier.ppm [el] : la carte éclairée vue de dessus (pour régler la lumière) */
    if (getenv("VAL_DESSUS")) {
        u e2 = getenv("VAL_EL") ? (u)(s)atoll(getenv("VAL_EL")) : el;
        if (getenv("VAL_SANS_FEUX")) REGLES = 0;
        if (getenv("VAL_EL") || getenv("VAL_SANS_FEUX")) eclairer_tout(az, e2);
        FILE *f = fopen(getenv("VAL_DESSUS"), "wb");
        fprintf(f, "P6 %d %d 255\n", G, G);
        for (int i = 0; i < G * G; i++) { u cc = teinte(i, i % G, i / G); unsigned char p[3] = {cc >> 16, cc >> 8, cc}; fwrite(p, 1, 3, f); }
        fclose(f);
    }
    fprintf(stderr, "préparation %.1f ms, %d images en %.1f ms (%.2f ms par image)\n", ms(t0, t1), IMAGES, ms(t1, t2),
            ms(t1, t2) / IMAGES);
    return 0;
}
