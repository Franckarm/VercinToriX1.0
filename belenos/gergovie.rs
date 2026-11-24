// Belenos : l'épreuve de Gergovie en Rust écrit à la main (0.819). Le même calcul que cubes_ref.c et cubes_scene.vtx,
// entier pour entier (la même empreinte) ; les rangées de l'image sur tous les cœurs (des fils de std, sans bibliothèque).
//     rustc -C opt-level=3 -C overflow-checks=off -C target-cpu=native belenos/gergovie.rs -o gergovie_rs
//     GERGOVIE_VOL=240 GERGOVIE_JOUR=120 ./gergovie_rs        (sans GERGOVIE : le film de 48 images, comme cubes_ref)
// Les opérations de vtx : / % < > sans signe ; les signées par sdiv, sar, slt ; tout sur 64 bits, en enveloppant (le
// dépassement enveloppe : overflow-checks=off). Les accès aux tableaux restent vérifiés : c'est du Rust ordinaire.
#![allow(clippy::all)]
#![allow(arithmetic_overflow, unused_assignments)]
use std::sync::atomic::{AtomicUsize, Ordering};
use std::time::Instant;

type U = u64;
const RN: U = 1;
const RD: U = 1;
const W: U = 1280;
const H: U = 720;
const TUILES: U = 2 * RN / RD;
const MONDE: U = 256 * TUILES;
const MASQ: U = MONDE - 1;
const NB: U = MONDE / 8;
const MER: U = 44 * RN / RD;
const VIDE: U = 1 << 63;
const LOIN: U = 8;
const MANQUE: U = 1 << 62;
const ROCHE: U = 1;
const HERBE: U = 2;
const NEIGE: U = 3;
const SABLE: U = 4;
const EAU: U = 5;
const TERRE: U = 6;
const LANDE: U = 7;
const ARCHE_X: U = 256 * RN / RD;
const ARCHE_Z: U = 300 * RN / RD;
const ARCHE_R: U = 30 * RN / RD;
const ARCHE_E: U = 7 * RN / RD;
const P3: U = 16 * RN / RD;
const UN: U = (RN + RD - 1) / RD;

#[inline(always)]
fn sdiv(a: U, b: U) -> U {
    ((a as i64).wrapping_div(b as i64)) as U
}
#[inline(always)]
fn sar(a: U, n: u32) -> U {
    ((a as i64) >> n) as U
}
#[inline(always)]
fn slt(a: U, b: U) -> bool {
    (a as i64) < (b as i64)
}
fn racine_entiere(x: U) -> U {
    let (mut r, mut v, mut b) = (0u64, x, 1u64 << 62);
    while b > v {
        b >>= 2;
    }
    while b != 0 {
        if v >= r + b {
            v -= r + b;
            r = (r >> 1) + b;
        } else {
            r >>= 1;
        }
        b >>= 2;
    }
    r
}
#[inline(always)]
fn hache(x: U, z: U) -> U {
    let mut h = (x & 4095) * 374761393 + (z & 4095) * 668265263 + 1013904223;
    h = (h ^ (h >> 13)) * 1274126177;
    (h ^ (h >> 16)) & 65535
}
#[inline(always)]
fn hache3(x: U, y: U, z: U) -> U {
    let mut h = (x & 1023) * 374761393 + (y & 1023) * 668265263 + (z & 1023) * 2246822519 + 1013904223;
    h = (h ^ (h >> 13)) * 1274126177;
    (h ^ (h >> 16)) & 65535
}
fn bruit_lisse(x: U, z: U, p: U) -> U {
    let (x0, z0, fx, fz) = (x / p, z / p, (x % p) * 256 / p, (z % p) * 256 / p);
    let sx = fx * fx * (768 - 2 * fx) / 65536;
    let sz = fz * fz * (768 - 2 * fz) / 65536;
    let n = MONDE / p;
    let a = hache(x0 % n, z0 % n);
    let b = hache((x0 + 1) % n, z0 % n);
    let c = hache(x0 % n, (z0 + 1) % n);
    let d = hache((x0 + 1) % n, (z0 + 1) % n);
    let h1 = (a * (256 - sx) + b * sx) / 256;
    let h2 = (c * (256 - sx) + d * sx) / 256;
    (h1 * (256 - sz) + h2 * sz) / 256
}
fn bruit3(x: U, y: U, z: U) -> U {
    let (x0, y0, z0) = (x / P3, y / P3, z / P3);
    let (fx, fy, fz) = ((x % P3) * 256 / P3, (y % P3) * 256 / P3, (z % P3) * 256 / P3);
    let sx = fx * fx * (768 - 2 * fx) / 65536;
    let sy = fy * fy * (768 - 2 * fy) / 65536;
    let sz = fz * fz * (768 - 2 * fz) / 65536;
    let a0 = (hache3(x0, y0, z0) * (256 - sx) + hache3(x0 + 1, y0, z0) * sx) / 256;
    let a1 = (hache3(x0, y0 + 1, z0) * (256 - sx) + hache3(x0 + 1, y0 + 1, z0) * sx) / 256;
    let a2 = (hache3(x0, y0, z0 + 1) * (256 - sx) + hache3(x0 + 1, y0, z0 + 1) * sx) / 256;
    let a3 = (hache3(x0, y0 + 1, z0 + 1) * (256 - sx) + hache3(x0 + 1, y0 + 1, z0 + 1) * sx) / 256;
    let b0 = (a0 * (256 - sy) + a1 * sy) / 256;
    let b1 = (a2 * (256 - sy) + a3 * sy) / 256;
    (b0 * (256 - sz) + b1 * sz) / 256
}
fn rgb24(mut r: U, mut g: U, mut b: U) -> U {
    if slt(r, 0) {
        r = 0;
    }
    if slt(g, 0) {
        g = 0;
    }
    if slt(b, 0) {
        b = 0;
    }
    r = r.min(255);
    g = g.min(255);
    b = b.min(255);
    (r << 16) | (g << 8) | b
}
#[inline(always)]
fn normale_mot(nx: U, ny: U, nz: U) -> U {
    ((nx + 128) & 255) | (((ny + 128) & 255) << 8) | (((nz + 128) & 255) << 16)
}

/// tout le monde : les colonnes, les annuaires (DIRE, DIRT), les réserves (POOLE, POOLT), les calques, les creux
struct Monde {
    sinus: [U; 1024],
    hcol: Vec<U>,
    pente: Vec<U>,
    glob: [U; 64],
    soleils: [U; 16],
    dire: Vec<Vec<U>>,
    dirt: Vec<Vec<U>>,
    poole: Vec<Vec<U>>,
    poolt: Vec<Vec<U>>,
    cielc: Vec<Vec<U>>,
    solc: Vec<Vec<U>>,
    creux: Vec<Vec<U>>,
}

fn fils() -> usize {
    std::env::var("GERGOVIE_FILS").ok().and_then(|s| s.parse().ok()).unwrap_or_else(|| {
        std::thread::available_parallelism().map(|n| n.get()).unwrap_or(1)
    })
}

/// les tours 0..n sur tous les cœurs, pris un par un (comme schedule(dynamic)) ; chaque fil rend ses résultats
fn partager<T: Send, F: Fn(usize) -> T + Sync>(n: usize, f: F) -> Vec<(usize, T)> {
    let suivant = AtomicUsize::new(0);
    let nf = fils().max(1);
    let mut tout: Vec<(usize, T)> = Vec::with_capacity(n);
    std::thread::scope(|sc| {
        let mains: Vec<_> = (0..nf)
            .map(|_| {
                sc.spawn(|| {
                    let mut a = Vec::new();
                    loop {
                        let i = suivant.fetch_add(1, Ordering::Relaxed);
                        if i >= n {
                            break;
                        }
                        a.push((i, f(i)));
                    }
                    a
                })
            })
            .collect();
        for m in mains {
            tout.extend(m.join().unwrap());
        }
    });
    tout
}

impl Monde {
    fn sin1024(&self, a: U) -> U {
        self.sinus[(a & 1023) as usize]
    }
    fn cos1024(&self, a: U) -> U {
        self.sinus[((a + 256) & 1023) as usize]
    }
    fn creer_sol(&mut self) {
        for z in 0..MONDE {
            for x in 0..MONDE {
                let h = bruit_lisse(x, z, 256 * RN / RD) * 16 + bruit_lisse(x, z, 128 * RN / RD) * 8
                    + bruit_lisse(x, z, 64 * RN / RD) * 4 + bruit_lisse(x, z, 32 * RN / RD) * 2
                    + bruit_lisse(x, z, 16 * RN / RD);
                let n = h / 31;
                let e = sdiv((n - 32768) * 11, 4);
                let mut n2 = 32768 + e;
                if slt(n2, 0) {
                    n2 = 0;
                }
                if n2 > 65535 {
                    n2 = 65535;
                }
                let mut m = 0;
                if n2 > 34000 {
                    m = (n2 - 34000) * 65536 / 31535;
                }
                if m > 65535 {
                    m = 65535;
                }
                let mut hs = 34 * 256 + n2 * 48 / 256 + m * m / 65536 * 160 / 256;
                if hs > 100 * 256 {
                    hs = 100 * 256 + (hs - 100 * 256) / 6;
                }
                self.hcol[(z * MONDE + x) as usize] = hs * RN / RD;
            }
        }
        for z in 0..MONDE {
            for x in 0..MONDE {
                let hc = |zz: U, xx: U| self.hcol[(zz * MONDE + xx) as usize];
                let (hx1, hx0) = (hc(z, (x + 1) & MASQ), hc(z, (x + MASQ) & MASQ));
                let (hz1, hz0) = (hc((z + 1) & MASQ, x), hc((z + MASQ) & MASQ, x));
                let p = hx1.abs_diff(hx0) + hz1.abs_diff(hz0);
                self.pente[(z * MONDE + x) as usize] = p / 2;
            }
        }
        self.glob[0] = (self.hcol[(ARCHE_Z * MONDE + ARCHE_X - ARCHE_R) as usize]
            + self.hcol[(ARCHE_Z * MONDE + ARCHE_X + ARCHE_R) as usize])
            / 512;
        let mut haut = *self.hcol.iter().max().unwrap();
        haut = haut / 256 + 12 * RN / RD;
        if self.glob[0] + ARCHE_R + ARCHE_E + 4 > haut {
            haut = self.glob[0] + ARCHE_R + ARCHE_E + 4;
        }
        self.glob[20] = haut;
    }
    fn ampleur(y: U) -> U {
        let mut amp = 384 * RN / RD;
        if y > 70 * RN / RD && y < 4000 {
            amp = (384 + (y * RD / RN - 70) * 40) * RN / RD;
            if amp > 1800 * RN / RD {
                amp = 1800 * RN / RD;
            }
        }
        amp
    }
    fn densite(&self, x: U, y: U, z: U) -> U {
        let h = self.hcol[((z & MASQ) * MONDE + (x & MASQ)) as usize];
        let mut d = h - y * 256 - 128;
        let amp = Monde::ampleur(y);
        if slt(d, amp + 512) && slt(0 - amp - 512, d) {
            d = d + sdiv((bruit3(x, y, z) - 32768) * amp, 32768);
        }
        let ay = self.glob[0];
        let (ax, az, ah) = (x - ARCHE_X, z - ARCHE_Z, y - ay);
        if slt(0 - 48 * RN / RD, ax) && slt(ax, 48 * RN / RD) && slt(0 - 12 * RN / RD, az) && slt(az, 12 * RN / RD)
            && slt(0 - 8 * RN / RD, ah) && slt(ah, 48 * RN / RD)
        {
            let q = racine_entiere((ax * ax + ah * ah) * 65536);
            let e = q - ARCHE_R * 256;
            let dist = racine_entiere(e * e + az * az * 65536);
            let da = ARCHE_E * 256 - dist + sdiv((bruit3(x * 2, y * 2, z * 2) - 32768) * (300 * RN / RD), 32768);
            if slt(d, da) {
                d = da;
            }
        }
        d
    }
    fn composer_point(&self, x: U, y: U, z: U) -> U {
        let d0 = self.densite(x, y, z);
        if !slt(0, d0) {
            if y < MER {
                let mut fond = sdiv(MER * 256 - self.hcol[((z & MASQ) * MONDE + (x & MASQ)) as usize], 64 * RN / RD);
                if slt(fond, 0) {
                    fond = 0;
                }
                if fond > 120 {
                    fond = 120;
                }
                let ce = rgb24(40 - fond / 6, 96 - fond / 3, 104 - fond / 5);
                return (ce << 32) | (normale_mot(0, 127, 0) << 8) | (EAU << 2) | 2;
            }
            return 0;
        }
        let (dxm, dxp) = (self.densite(x - 1, y, z), self.densite(x + 1, y, z));
        let (dym, dyp) = (self.densite(x, y - 1, z), self.densite(x, y + 1, z));
        let (dzm, dzp) = (self.densite(x, y, z - 1), self.densite(x, y, z + 1));
        let surface = !slt(0, dxm) || !slt(0, dxp) || !slt(0, dym) || !slt(0, dyp) || !slt(0, dzm) || !slt(0, dzp);
        let col = ((z & MASQ) * MONDE + (x & MASQ)) as usize;
        let (hs, pente) = (self.hcol[col] / 256, self.pente[col]);
        let mut mat = HERBE;
        if y + 3 * RN / RD < hs {
            mat = TERRE;
        }
        if slt(0, dyp) && surface {
            mat = ROCHE;
        } else if y <= MER + UN && y + UN >= MER {
            mat = SABLE;
        } else if y > 108 * RN / RD {
            mat = if pente < 300 { NEIGE } else { ROCHE };
        } else if pente > 420 || y > hs + UN {
            mat = ROCHE;
        } else if y > 80 * RN / RD {
            mat = LANDE;
        }
        let (mut r, mut g, mut b): (U, U, U) = match mat {
            ROCHE => (120, 114, 106),
            NEIGE => (236, 240, 246),
            SABLE => (196, 182, 140),
            TERRE => (100, 80, 60),
            LANDE => (128, 118, 80),
            _ => (78, 120, 58),
        };
        let tache = (bruit_lisse(x & MASQ, z & MASQ, 32 * RN / RD) / 2048) + ((y * RD / RN) & 3);
        let grain = hache3(x, y, z) & 15;
        r = r + tache + grain;
        g = g + tache + grain;
        b = b + tache / 2 + grain;
        let c = rgb24(r, g, b);
        let mut nm = 0;
        if surface {
            let (nx, ny, nz) = (dxm - dxp, dym - dyp, dzm - dzp);
            let lg = racine_entiere(nx * nx + ny * ny + nz * nz);
            nm = if lg == 0 {
                normale_mot(0, 127, 0)
            } else {
                normale_mot(sdiv(nx * 127, lg), sdiv(ny * 127, lg), sdiv(nz * 127, lg))
            };
        }
        (c << 32) | (nm << 8) | (mat << 2) | 2
    }
    fn classer_blocs(&mut self) {
        for q in 0..TUILES * TUILES * 1024 {
            let (t, bx, bz) = (q >> 10, q & 31, (q >> 5) & 31);
            let (x0, z0) = ((t % TUILES) * 256 + bx * 8, (t / TUILES) * 256 + bz * 8);
            let (mut hmin, mut hmax) = (1000000u64, 0u64);
            for dz in 0..10 {
                for dx in 0..10 {
                    let h = self.hcol[(((z0 + dz + MASQ) & MASQ) * MONDE + ((x0 + dx + MASQ) & MASQ)) as usize];
                    hmin = hmin.min(h);
                    hmax = hmax.max(h);
                }
            }
            let ay = self.glob[0];
            let arche_x = x0 + 8 + 48 * RN / RD > ARCHE_X && x0 < ARCHE_X + 48 * RN / RD
                && z0 + 8 + 12 * RN / RD > ARCHE_Z && z0 < ARCHE_Z + 12 * RN / RD;
            for by in 0..32 {
                let (y0, b) = (by * 8, ((bx << 10) | (by << 5) | bz) as usize);
                let amp = Monde::ampleur(y0 + 9);
                let mut e = 1;
                if arche_x && y0 + 9 + 8 * RN / RD > ay && y0 < ay + 48 * RN / RD + 1 {
                    e = 1;
                } else if y0 * 256 > hmax + amp + 640 {
                    if y0 >= MER {
                        e = 0;
                    } else if y0 + 8 <= MER {
                        e = 3;
                    }
                } else if (y0 + 9) * 256 + 640 + amp < hmin {
                    e = 2;
                }
                let t = t as usize;
                if e == 0 {
                    self.dire[t][b] = VIDE;
                } else if e == 2 {
                    self.dire[t][b] = (1 << 62) | (TERRE << 2) | 2;
                    self.dirt[t][b] = rgb24(100, 80, 60);
                } else if e == 3 {
                    let c = self.composer_point(x0 + 4, y0 + 4, z0 + 4);
                    self.dire[t][b] = (1 << 62) | (c & 4294967295);
                    self.dirt[t][b] = c >> 32;
                } else {
                    self.dire[t][b] = 1;
                }
            }
        }
    }
    fn placer_et_remplir(&mut self) {
        let nt = (TUILES * TUILES) as usize;
        for t in 0..nt {
            let mut n = 0u64;
            for b in 0..32768 {
                if self.dire[t][b] == 1 {
                    self.dire[t][b] = 16 + n;
                    n += 1;
                }
            }
            self.glob[1 + t] = n;
            let n = n as usize;
            self.poole.push(vec![0; n * 512 + 1]);
            self.poolt.push(vec![0; n * 512 + 1]);
            self.cielc.push(vec![0; n * 64 + 1]);
            self.solc.push(vec![0; n * 64 + 1]);
            self.creux.push(vec![0; n + 1]);
        }
        let colonnes = partager(nt * 1024, |q| {
            let q = q as U;
            let (t, bx, bz) = (q >> 10, q & 31, (q >> 5) & 31);
            let (x0, z0) = ((t % TUILES) * 256 + bx * 8, (t / TUILES) * 256 + bz * 8);
            let mut a: Vec<(usize, Vec<U>)> = Vec::new();
            for by in 0..32 {
                let e = self.dire[t as usize][((bx << 10) | (by << 5) | bz) as usize];
                if e >= 16 && e < (1 << 62) {
                    let pts = (0..512u64)
                        .map(|v| self.composer_point(x0 + (v >> 6), by * 8 + ((v >> 3) & 7), z0 + (v & 7)))
                        .collect();
                    a.push(((e - 16) as usize, pts));
                }
            }
            a
        });
        for (q, briques) in colonnes {
            let t = q >> 10;
            for (n, pts) in briques {
                for (v, c) in pts.into_iter().enumerate() {
                    self.poole[t][n * 512 + v] = c & 4294967295;
                    self.poolt[t][n * 512 + v] = c >> 32;
                }
            }
        }
        for t in 0..nt {
            for b in 0..self.glob[1 + t] as usize {
                let mut m = 0u64;
                for v in 0..512u64 {
                    if self.poole[t][b * 512 + v as usize] != 0 {
                        let (x, y, z) = (v >> 6, (v >> 3) & 7, v & 7);
                        let s4 = ((x >> 2) << 2) | ((y >> 2) << 1) | (z >> 2);
                        let s2 = (((x >> 1) & 1) << 2) | (((y >> 1) & 1) << 1) | ((z >> 1) & 1);
                        m |= 1 << (s4 * 8 + s2);
                    }
                }
                self.creux[t][b] = m;
            }
        }
    }
    fn mot_bloc(gx: U, gy: U, gz: U) -> (usize, usize) {
        let t = (gz >> 5) * TUILES + (gx >> 5);
        (t as usize, (((gx & 31) << 10) + (gy << 5) + (gz & 31)) as usize)
    }
    fn distancer_blocs(&mut self) {
        let cb = |gx: U, gy: U, gz: U| ((gy * NB + gz) * NB + gx) as usize;
        let taille = (NB * NB * 32) as usize;
        let mut de = vec![0u64; taille];
        let mut vers = vec![0u64; taille];
        for gy in 0..32 {
            for gz in 0..NB {
                for gx in 0..NB {
                    let (t, i) = Monde::mot_bloc(gx, gy, gz);
                    de[cb(gx, gy, gz)] = if (self.dire[t][i] >> 62) == 2 { LOIN } else { 0 };
                }
            }
        }
        for _ in 0..LOIN - 1 {
            for gy in 0..32 {
                for gz in 0..NB {
                    for gx in 0..NB {
                        let mut d = de[cb(gx, gy, gz)];
                        if d > 1 {
                            for k in 0..27u64 {
                                let (nx, ny, nz) = (gx + (k % 3) - 1, gy + ((k / 3) % 3) - 1, gz + (k / 9) - 1);
                                if nx < NB && ny < 32 && nz < NB {
                                    let v = de[cb(nx, ny, nz)] + 1;
                                    if v < d {
                                        d = v;
                                    }
                                }
                            }
                        }
                        vers[cb(gx, gy, gz)] = d;
                    }
                }
            }
            std::mem::swap(&mut de, &mut vers);
        }
        for gy in 0..32 {
            for gz in 0..NB {
                for gx in 0..NB {
                    let (t, i) = Monde::mot_bloc(gx, gy, gz);
                    if (self.dire[t][i] >> 62) == 2 {
                        self.dire[t][i] = VIDE | de[cb(gx, gy, gz)];
                    }
                }
            }
        }
    }
    #[inline(always)]
    fn element(&self, x: U, y: U, z: U) -> U {
        if x >= MONDE || z >= MONDE || y >= 256 {
            return 0;
        }
        let t = ((z >> 8) * TUILES + (x >> 8)) as usize;
        let e = self.dire[t][((((x >> 3) & 31) << 10) + (((y >> 3) & 31) << 5) + ((z >> 3) & 31)) as usize];
        if (e >> 62) == 2 {
            return 0;
        }
        if (e >> 62) == 1 {
            return e & 4294967295;
        }
        self.poole[t][((e - 16) * 512 + ((x & 7) << 6) + ((y & 7) << 3) + (z & 7)) as usize]
    }
    #[inline(always)]
    fn couleur(&self, x: U, y: U, z: U) -> U {
        let t = ((z >> 8) * TUILES + (x >> 8)) as usize;
        let b = ((((x >> 3) & 31) << 10) + (((y >> 3) & 31) << 5) + ((z >> 3) & 31)) as usize;
        let e = self.dire[t][b];
        if (e >> 62) == 1 {
            return self.dirt[t][b];
        }
        self.poolt[t][((e - 16) * 512 + ((x & 7) << 6) + ((y & 7) << 3) + (z & 7)) as usize]
    }
    fn tracer(&self, ox: U, oy: U, oz: U, dx: U, dy: U, dz: U, tmax: U, eau: bool) -> U {
        let mut t: U = 0;
        let plafond = self.glob[20] << 16;
        let p40: U = 1 << 40;
        let pen = |d: U| if slt(0, d) { p40 / d } else if slt(d, 0) { p40 / (0 - d) } else { 0 };
        let (ix, iy, iz) = (pen(dx), pen(dy), pen(dz));
        while t < tmax {
            let (px, py, pz) = (ox + sar(dx * t, 16), oy + sar(dy * t, 16), oz + sar(dz * t, 16));
            if !slt(py, plafond) && !slt(dy, 0) {
                return MANQUE;
            }
            if slt(py, 0) || slt(px, 0) || slt(pz, 0) || !slt(px, MONDE * 65536) || !slt(pz, MONDE * 65536)
                || !slt(py, 256 * 65536)
            {
                return MANQUE;
            }
            let (x, y, z) = (px >> 16, py >> 16, pz >> 16);
            let tl = ((z >> 8) * TUILES + (x >> 8)) as usize;
            let e = self.dire[tl][((((x >> 3) & 31) << 10) + (((y >> 3) & 31) << 5) + ((z >> 3) & 31)) as usize];
            let (mut sz_, mut av): (U, U) = (8, 1);
            if (e >> 62) == 2 {
                av = e & 255;
            } else if (e >> 62) == 1 {
                if eau || ((e >> 2) & 63) != EAU {
                    return t;
                }
            } else {
                let v = self.poole[tl][((e - 16) * 512 + ((x & 7) << 6) + ((y & 7) << 3) + (z & 7)) as usize];
                if v != 0 && (eau || ((v >> 2) & 63) != EAU) {
                    return t;
                }
                sz_ = 1;
                if v == 0 {
                    let m = self.creux[tl][(e - 16) as usize];
                    let s4 = (((x >> 2) & 1) << 2) | (((y >> 2) & 1) << 1) | ((z >> 2) & 1);
                    if ((m >> (s4 * 8)) & 255) == 0 {
                        sz_ = 4;
                    } else {
                        let s2 = (((x >> 1) & 1) << 2) | (((y >> 1) & 1) << 1) | ((z >> 1) & 1);
                        if ((m >> (s4 * 8 + s2)) & 1) == 0 {
                            sz_ = 2;
                        }
                    }
                }
            }
            let arr = if sz_ == 8 { (av - 1) * 8 } else { 0 };
            let mut pas = MANQUE;
            if slt(0, dx) {
                pas = pas.min(((((x | (sz_ - 1)) + 1 + arr) << 16) - px) * ix >> 24);
            } else if slt(dx, 0) {
                pas = pas.min(((px - (((x & (0 - sz_)) - arr) << 16)) + 1) * ix >> 24);
            }
            if slt(0, dy) {
                pas = pas.min(((((y | (sz_ - 1)) + 1 + arr) << 16) - py) * iy >> 24);
            } else if slt(dy, 0) {
                pas = pas.min(((py - (((y & (0 - sz_)) - arr) << 16)) + 1) * iy >> 24);
            }
            if slt(0, dz) {
                pas = pas.min(((((z | (sz_ - 1)) + 1 + arr) << 16) - pz) * iz >> 24);
            } else if slt(dz, 0) {
                pas = pas.min(((pz - (((z & (0 - sz_)) - arr) << 16)) + 1) * iz >> 24);
            }
            t = t + pas + 1;
        }
        MANQUE
    }
    fn preparer_soleil(&mut self, az: U, el: U) {
        let lx = sdiv(self.cos1024(el) * self.sin1024(az), 65536);
        let ly = self.sin1024(el);
        let lz = sdiv(self.cos1024(el) * self.cos1024(az), 65536);
        self.soleils[12] = lx;
        self.soleils[13] = ly;
        self.soleils[14] = lz;
        let ul = racine_entiere(lx * lx + lz * lz);
        let (ux, uz) = (sdiv(lz * 65536, ul), sdiv((0 - lx) * 65536, ul));
        let (vx, vy, vz) = (sdiv(0 - uz * ly, 65536), sdiv(uz * lx - ux * lz, 65536), sdiv(ux * ly, 65536));
        for k in 0..4usize {
            let (ex, ey, ez) = match k {
                0 => (ux, 0, uz),
                1 => (0 - ux, 0, 0 - uz),
                2 => (vx, vy, vz),
                _ => (0 - vx, 0 - vy, 0 - vz),
            };
            let (sx, sy, sz) = (lx + sdiv(ex * 2300, 65536), ly + sdiv(ey * 2300, 65536), lz + sdiv(ez * 2300, 65536));
            let lg = racine_entiere(sx * sx + sy * sy + sz * sz);
            self.soleils[3 * k] = sdiv(sx * 65536, lg);
            self.soleils[3 * k + 1] = sdiv(sy * 65536, lg);
            self.soleils[3 * k + 2] = sdiv(sz * 65536, lg);
        }
    }
    fn ciel(&self, dx: U, dy: U, dz: U) -> U {
        let hy = if slt(dy, 0) { 0 } else { dy };
        let t = hy * 256 / 65536;
        let (mut r, mut g, mut b) = ((200 * (256 - t) + 92 * t) / 256, (214 * (256 - t) + 128 * t) / 256, (230 * (256 - t) + 184 * t) / 256);
        let cs = sdiv(dx * self.soleils[12] + dy * self.soleils[13] + dz * self.soleils[14], 65536);
        if slt(65500, cs) {
            return rgb24(255, 248, 228);
        }
        if slt(60000, cs) {
            let lueur = (cs - 60000) * 90 / 5500;
            r += lueur;
            g += lueur * 3 / 4;
            b += lueur / 3;
        }
        rgb24(r, g, b)
    }
    fn depart(&self, x: U, y: U, z: U, nx: U, ny: U, nz: U) -> U {
        let (sx, sy, sz) = ((x << 16) + 32768 + nx * 858, (y << 16) + 32768 + ny * 858, (z << 16) + 32768 + nz * 858);
        if self.element(sx >> 16, sy >> 16, sz >> 16) != 0 {
            let (mut meilleur, mut note) = (6u64, 0u64.wrapping_sub(1000));
            for k in 0..6u64 {
                let (mut vx, mut vy, mut vz, mut nk) = (x, y, z, nx);
                match k {
                    0 => vx = x + 1,
                    1 => {
                        vx = x - 1;
                        nk = 0 - nx
                    }
                    2 => {
                        vy = y + 1;
                        nk = ny
                    }
                    3 => {
                        vy = y - 1;
                        nk = 0 - ny
                    }
                    4 => {
                        vz = z + 1;
                        nk = nz
                    }
                    _ => {
                        vz = z - 1;
                        nk = 0 - nz
                    }
                }
                if self.element(vx, vy, vz) == 0 && slt(note, nk) {
                    note = nk;
                    meilleur = k;
                }
            }
            return meilleur;
        }
        6
    }
    fn partir(&self, x: U, y: U, z: U, nx: U, ny: U, nz: U) -> (U, U, U) {
        let (mut sx, mut sy, mut sz) = ((x << 16) + 32768 + nx * 858, (y << 16) + 32768 + ny * 858, (z << 16) + 32768 + nz * 858);
        let dp = self.depart(x, y, z, nx, ny, nz);
        if dp < 6 {
            sx = (x << 16) + 32768;
            sy = (y << 16) + 32768;
            sz = (z << 16) + 32768;
            match dp {
                0 => sx += 65536,
                1 => sx -= 65536,
                2 => sy += 65536,
                3 => sy -= 65536,
                4 => sz += 65536,
                _ => sz -= 65536,
            }
        }
        (sx, sy, sz)
    }
    fn soleil_depuis(&self, sx: U, sy: U, sz: U, nx: U, ny: U, nz: U) -> U {
        let nl = sdiv(nx * self.soleils[12] + ny * self.soleils[13] + nz * self.soleils[14], 127);
        if !slt(0, nl) {
            return 0;
        }
        let mut vus = 0;
        for k in 0..4 {
            if self.tracer(sx, sy, sz, self.soleils[3 * k], self.soleils[3 * k + 1], self.soleils[3 * k + 2], 700 * 65536 * RN / RD, false)
                == MANQUE
            {
                vus += 1;
            }
        }
        vus
    }
    fn ciel_depuis(&self, sx: U, sy: U, sz: U, nx: U, ny: U, nz: U) -> U {
        let (n16x, n16y, n16z) = (nx * 516, ny * 516, nz * 516);
        let (mut t1x, mut t1y, mut t1z) = (0u64, 0u64, 0u64);
        let ay_ = if slt(ny, 0) { 0 - ny } else { ny };
        if slt(ay_, 90) {
            t1x = 0 - n16z;
            t1z = n16x;
        } else {
            t1y = n16z;
            t1z = 0 - n16y;
        }
        let mut l1 = racine_entiere(t1x * t1x + t1y * t1y + t1z * t1z);
        if l1 == 0 {
            l1 = 1;
        }
        t1x = sdiv(t1x * 65536, l1);
        t1y = sdiv(t1y * 65536, l1);
        t1z = sdiv(t1z * 65536, l1);
        let t2x = sdiv(n16y * t1z - n16z * t1y, 65536);
        let t2y = sdiv(n16z * t1x - n16x * t1z, 65536);
        let t2z = sdiv(n16x * t1y - n16y * t1x, 65536);
        let mut ouverts = 0;
        for k in 0..4 {
            let (ex, ey, ez) = match k {
                0 => (t1x, t1y, t1z),
                1 => (0 - t1x, 0 - t1y, 0 - t1z),
                2 => (t2x, t2y, t2z),
                _ => (0 - t2x, 0 - t2y, 0 - t2z),
            };
            let (cx, cy, cz) = (sdiv(n16x * 3 + ex * 4, 5), sdiv(n16y * 3 + ey * 4, 5), sdiv(n16z * 3 + ez * 4, 5));
            if self.tracer(sx, sy, sz, cx, cy, cz, 14 * 65536 * RN / RD, false) == MANQUE {
                ouverts += 1;
            }
        }
        ouverts
    }
    fn expose(&self, x: U, y: U, z: U) -> bool {
        self.element(x + 1, y, z) == 0 || self.element(x - 1, y, z) == 0 || self.element(x, y + 1, z) == 0
            || self.element(x, y - 1, z) == 0 || self.element(x, y, z + 1) == 0 || self.element(x, y, z - 1) == 0
    }
    fn ranger_lumiere(&mut self, avec_ciel: bool) {
        let nt = (TUILES * TUILES) as usize;
        let res = partager(nt * 1024, |q| {
            let q = q as U;
            let (t, bx, bz) = (q >> 10, q & 31, (q >> 5) & 31);
            let (x0, z0) = ((t % TUILES) * 256 + bx * 8, (t / TUILES) * 256 + bz * 8);
            let t = t as usize;
            let mut a: Vec<(usize, U, U)> = Vec::new();
            for by in 0..32u64 {
                let e = self.dire[t][((bx << 10) | (by << 5) | bz) as usize];
                if e >= 16 && e < (1 << 62) {
                    let n = (e - 16) as usize;
                    for w in 0..64usize {
                        let (mut ms_, mut mc) = (0u64, 0u64);
                        for j in 0..8u64 {
                            let v = w as U * 8 + j;
                            let (x, y, z) = (x0 + (v >> 6), by * 8 + ((v >> 3) & 7), z0 + (v & 7));
                            let el = self.poole[t][n * 512 + v as usize];
                            if el != 0 && ((el >> 2) & 63) != EAU && self.expose(x, y, z) {
                                let (mut nx, mut ny, mut nz) = (((el >> 8) & 255) - 128, ((el >> 16) & 255) - 128, ((el >> 24) & 255) - 128);
                                if nx == 0 - 128u64 {
                                    nx = 0;
                                    ny = 127;
                                    nz = 0;
                                }
                                let (sx, sy, sz) = self.partir(x, y, z, nx, ny, nz);
                                ms_ |= (128 | self.soleil_depuis(sx, sy, sz, nx, ny, nz)) << (j * 8);
                                if avec_ciel {
                                    mc |= (128 | self.ciel_depuis(sx, sy, sz, nx, ny, nz)) << (j * 8);
                                }
                            }
                        }
                        a.push((n * 64 + w, ms_, mc));
                    }
                }
            }
            a
        });
        for (q, l) in res {
            let t = q >> 10;
            for (i, ms_, mc) in l {
                self.solc[t][i] = ms_;
                if avec_ciel {
                    self.cielc[t][i] = mc;
                }
            }
        }
    }
    fn regarder(&self, ox: U, oy: U, oz: U, dx: U, dy: U, dz: U, profondeur: U, temps: U) -> U {
        let t = self.tracer(ox, oy, oz, dx, dy, dz, 1100 * 65536 * RN / RD, true);
        if t == MANQUE {
            return self.ciel(dx, dy, dz);
        }
        let (px, py, pz) = (ox + sar(dx * t, 16), oy + sar(dy * t, 16), oz + sar(dz * t, 16));
        let (x, y, z) = (px >> 16, py >> 16, pz >> 16);
        let (e, alb) = (self.element(x, y, z), self.couleur(x, y, z));
        let mat = (e >> 2) & 63;
        let (mut nx, mut ny, mut nz) = (((e >> 8) & 255) - 128, ((e >> 16) & 255) - 128, ((e >> 24) & 255) - 128);
        if nx == 0 - 128u64 {
            nx = 0;
            ny = 127;
            nz = 0;
        }
        let (lx, ly, lz) = (self.soleils[12], self.soleils[13], self.soleils[14]);
        let (mut etat, mut r, mut g, mut b): (U, U, U, U) = (1, 0, 0, 0);
        if mat == EAU {
            let mut rx = dx + sdiv(bruit_lisse((x + temps) & MASQ, z & MASQ, 16) - 32768, 24);
            let mut rz = dz + sdiv(bruit_lisse(x & MASQ, (z + temps * 2) & MASQ, 16) - 32768, 24);
            let mut ry = 0 - dy;
            let lg = racine_entiere(rx * rx + ry * ry + rz * rz);
            rx = sdiv(rx * 65536, lg);
            ry = sdiv(ry * 65536, lg);
            rz = sdiv(rz * 65536, lg);
            let renvoi = if profondeur > 0 {
                self.regarder(px, (MER << 16) + 32768, pz, rx, ry, rz, profondeur - 1, temps) & 16777215
            } else {
                self.ciel(rx, ry, rz)
            };
            let mut rasant = 65536 - (0 - dy);
            if slt(0, dy) {
                rasant = 65536;
            }
            let part = 64 + rasant * rasant / 65536 * 154 / 65536;
            let (fr, fg, fb) = ((alb >> 16) & 255, (alb >> 8) & 255, alb & 255);
            r = (fr * (256 - part) + ((renvoi >> 16) & 255) * part) / 256;
            g = (fg * (256 - part) + ((renvoi >> 8) & 255) * part) / 256;
            b = (fb * (256 - part) + (renvoi & 255) * part) / 256;
            etat = 2;
        } else {
            let mut nl = sdiv(nx * lx + ny * ly + nz * lz, 127);
            if !slt(0, nl) {
                nl = 0;
            }
            let (mut vus, mut ouverts) = (0u64, 0u64);
            let mut connu = false;
            let tt = ((z >> 8) * TUILES + (x >> 8)) as usize;
            let e0 = self.dire[tt][((((x >> 3) & 31) << 10) + (((y >> 3) & 31) << 5) + ((z >> 3) & 31)) as usize];
            if e0 >= 16 && e0 < (1 << 62) {
                let iv = ((x & 7) << 6) | ((y & 7) << 3) | (z & 7);
                let dec = (iv & 7) * 8;
                let k = ((e0 - 16) * 64 + (iv >> 3)) as usize;
                let sb = (self.solc[tt][k] >> dec) & 255;
                if sb >= 128 {
                    connu = true;
                    vus = sb & 15;
                    ouverts = (self.cielc[tt][k] >> dec) & 15;
                }
            }
            if !connu {
                vus = self.soleil_depuis(px + nx * 600, py + ny * 600, pz + nz * 600, nx, ny, nz);
                ouverts = self.ciel_depuis(px + nx * 600, py + ny * 600, pz + nz * 600, nx, ny, nz);
            }
            if slt(0, nl) {
                if vus == 4 {
                    etat = 2;
                } else if vus > 0 {
                    etat = 3;
                }
            }
            let ciel_part = 40 + ouverts * 30;
            let soleil = nl * vus / 4 * 256 / 65536;
            let lr = 76 * ciel_part / 160 + soleil * 255 / 256 + 20;
            let lg2 = 88 * ciel_part / 160 + soleil * 238 / 256 + 18;
            let lb = 112 * ciel_part / 160 + soleil * 210 / 256 + 14;
            r = ((alb >> 16) & 255) * lr / 200;
            g = ((alb >> 8) & 255) * lg2 / 200;
            b = (alb & 255) * lb / 200;
        }
        let d = (t >> 16) * RD / RN;
        let brume = (d * d / 1600).min(220);
        r = (r * (256 - brume) + 200 * brume) / 256;
        g = (g * (256 - brume) + 214 * brume) / 256;
        b = (b * (256 - brume) + 230 * brume) / 256;
        (etat << 24) | rgb24(r, g, b)
    }
    fn rendre(&self, ecran: &mut [U], cx: U, cy: U, cz: U, lacet: U, tangage: U, temps: U) {
        let (sl, cl, st, ct) = (self.sin1024(lacet), self.cos1024(lacet), self.sin1024(tangage), self.cos1024(tangage));
        let (fx, fy, fz) = (sdiv(sl * ct, 65536), st, sdiv(cl * ct, 65536));
        let (rx, rz) = (cl, 0 - sl);
        let (ux, uy, uz) = (sdiv(0 - sl * st, 65536), ct, sdiv(0 - cl * st, 65536));
        let rangs = partager(H as usize, |yy| {
            let y = yy as U;
            let sy = sdiv((H - 2 * y - 1) * 45889, W);
            (0..W)
                .map(|x| {
                    let sx = sdiv((2 * x + 1 - W) * 45889, W);
                    let mut dx = fx + sdiv(rx * sx + ux * sy, 65536);
                    let mut dy = fy + sdiv(uy * sy, 65536);
                    let mut dz = fz + sdiv(rz * sx + uz * sy, 65536);
                    let lg = racine_entiere(dx * dx + dy * dy + dz * dz);
                    dx = sdiv(dx * 65536, lg);
                    dy = sdiv(dy * 65536, lg);
                    dz = sdiv(dz * 65536, lg);
                    self.regarder(cx, cy, cz, dx, dy, dz, 1, temps) & 16777215
                })
                .collect::<Vec<U>>()
        });
        for (y, rang) in rangs {
            ecran[y * W as usize..(y + 1) * W as usize].copy_from_slice(&rang);
        }
    }
    fn camera(&self, i: U, n: U) -> (U, U, U, U) {
        let (ay, avant) = (self.glob[0], n * 7 / 12);
        let cx = ARCHE_X * 65536;
        let (cy, cz);
        if i < avant {
            cy = 110 * 65536 * RN / RD - (((110 * RN / RD - ay - 12 * RN / RD) * 65536 / avant) * i);
            cz = 470 * 65536 * RN / RD - ((170 * 65536 * RN / RD / avant) * i);
        } else {
            let (j, reste) = (i - avant, n - avant);
            cy = (ay + 12 * RN / RD) * 65536 + sdiv((64 * RN / RD - ay - 12 * RN / RD) * 65536, reste) * j;
            cz = ARCHE_Z * 65536 - ((110 * 65536 * RN / RD / reste) * j);
        }
        let vy = (ay + 14 * RN / RD) * 65536 - cy;
        let (mut tangage, mut vu) = (0u64, 0u64.wrapping_sub(1 << 62));
        for k in 0..129u64 {
            let a = (k + 1024 - 64) & 1023;
            let p = sdiv(vy, 256) * self.sin1024(a) + (80 * 256 * RN / RD) * self.cos1024(a);
            if slt(vu, p) {
                vu = p;
                tangage = a;
            }
        }
        (cx, cy, cz, tangage)
    }
}

fn empreinte(ecran: &[U]) -> i64 {
    let mut h: U = 14695981039346656037;
    for &p in ecran {
        h = (h ^ p).wrapping_mul(1099511628211);
    }
    h as i64
}

fn bilan(nom: &str, t: &mut [f64], ecran: &[U]) {
    let n = t.len();
    let total: f64 = t.iter().sum();
    t.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let k = (n / 100).max(1);
    let lents: f64 = t[n - k..].iter().sum();
    println!(
        "gergovie : {} : {} images, {:.1} images par seconde en moyenne, 1 % bas {:.1}, pire image {:.1} ms ; empreinte {}",
        nom, n, 1000.0 * n as f64 / total, 1000.0 * k as f64 / lents, t[n - 1], empreinte(ecran)
    );
}

fn nombre(nom: &str, defaut: U) -> U {
    std::env::var(nom).ok().and_then(|s| s.parse().ok()).unwrap_or(defaut)
}

fn main() {
    let nt = (TUILES * TUILES) as usize;
    let mut m = Monde {
        sinus: [0; 1024],
        hcol: vec![0; (MONDE * MONDE) as usize],
        pente: vec![0; (MONDE * MONDE) as usize],
        glob: [0; 64],
        soleils: [0; 16],
        dire: vec![vec![0; 32768]; nt],
        dirt: vec![vec![0; 32768]; nt],
        poole: Vec::new(),
        poolt: Vec::new(),
        cielc: Vec::new(),
        solc: Vec::new(),
        creux: Vec::new(),
    };
    let t0 = Instant::now();
    for a in 0..1024u64 {
        let x = a & 511;
        let v = 4 * x * (512 - x) * 65536 / (327680 - x * (512 - x));
        m.sinus[a as usize] = if a >= 512 { 0 - v } else { v };
    }
    m.creer_sol();
    m.classer_blocs();
    m.placer_et_remplir();
    m.distancer_blocs();
    println!(
        "le monde : {:.0} ms ; blocs porteurs d'une surface, par tuile : {}, {}, {}, {} ; {} fils",
        t0.elapsed().as_secs_f64() * 1000.0, m.glob[1], m.glob[2], m.glob[3], m.glob[4], fils()
    );
    let mut ecran = vec![0u64; (W * H) as usize];
    if std::env::var("GERGOVIE").is_ok() {
        let (n1, n2) = (nombre("GERGOVIE_VOL", 240), nombre("GERGOVIE_JOUR", 120));
        m.preparer_soleil(360, 70);
        m.ranger_lumiere(true);
        let mut t = Vec::new();
        for i in 0..n1 {
            let ti = Instant::now();
            let (cx, cy, cz, tg) = m.camera(i, n1);
            m.rendre(&mut ecran, cx, cy, cz, 512, tg, i * 3);
            t.push(ti.elapsed().as_secs_f64() * 1000.0);
        }
        bilan("le vol (l'oeil bouge)", &mut t, &ecran);
        t.clear();
        for i in 0..n2 {
            let ti = Instant::now();
            m.preparer_soleil(300 + i * 3, 50 + i);
            m.ranger_lumiere(false);
            let (cx, cy, cz, tg) = m.camera(i, n2);
            m.rendre(&mut ecran, cx, cy, cz, 512, tg, i * 3);
            t.push(ti.elapsed().as_secs_f64() * 1000.0);
        }
        bilan("le jour (le soleil bouge aussi)", &mut t, &ecran);
        return;
    }
    let images = nombre("CUBES_IMAGES", 48);
    m.preparer_soleil(360, 70);
    m.ranger_lumiere(true);
    let mut total = 0.0;
    for i in 0..images {
        let ti = Instant::now();
        let (cx, cy, cz, tg) = m.camera(i, images);
        m.rendre(&mut ecran, cx, cy, cz, 512, tg, i * 3);
        total += ti.elapsed().as_secs_f64() * 1000.0;
    }
    println!("{} images en {:.0} ms ({:.0} ms par image)", images, total, total / images as f64);
    println!("empreinte : {}", empreinte(&ecran));
}
