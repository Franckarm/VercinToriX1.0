// Le cube dessiné : un étage de la mémoire à plat, ou en perspective isométrique (256 × 256 × 256 mots).
// Utilisé par la fenêtre de l'atelier, et par « vtx image » qui écrit l'image dans un fichier.
use super::Memoire;

/// La couleur d'un mot (0x00RRGGBB). Un petit nombre (285 vaut #0000011D, presque noir) serait invisible : il prend
/// une teinte d'une palette (violet, bleu, vert, jaune) selon sa grandeur, rapportée au plus grand petit nombre présent.
pub fn couleur(m: u32, max_petit: u32) -> u32 {
    if m == 0 {
        return 0x0010_1418;
    }
    if !petit(m) {
        return (m >> 24) << 16 | ((m >> 16) & 255) << 8 | ((m >> 8) & 255);
    }
    let t = ((m as f32 + 1.0).ln() / (max_petit.max(2) as f32 + 1.0).ln()).clamp(0.0, 1.0);
    const PALETTE: [(f32, f32, f32); 5] = [(72.0, 20.0, 110.0), (59.0, 82.0, 160.0), (33.0, 150.0, 140.0), (94.0, 201.0, 98.0), (253.0, 231.0, 37.0)];
    let x = t * 4.0;
    let i = (x as usize).min(3);
    let f = x - i as f32;
    let (a, b) = (PALETTE[i], PALETTE[i + 1]);
    let c = |u: f32, v: f32| (u + (v - u) * f) as u32;
    c(a.0, b.0) << 16 | c(a.1, b.1) << 8 | c(a.2, b.2)
}

/// Un mot dont les trois couleurs sont presque noires : un nombre plutôt qu'une couleur.
pub fn petit(m: u32) -> bool {
    m != 0 && (m >> 24) < 24 && ((m >> 16) & 255) < 24 && ((m >> 8) & 255) < 24
}

/// À plat : une ligne de l'image = `largeur` mots consécutifs ; chaque mot un carré de sa couleur.
pub fn rendre_plan(mem: &Memoire, etage: u32, largeur: u32, base: u32, l: usize, h: usize, px: &mut [u32]) {
    let cote = (l as u32 / largeur).max(1) as usize;
    let pas = ((largeur as usize + l - 1) / l).max(1) as u32;
    let lit = |x: usize, y: usize| -> Option<u32> {
        let (ligne, col) = ((y / cote) as u32 * pas, (x / cote) as u32 * pas);
        let adr = base as u64 + ligne as u64 * largeur as u64 + col as u64;
        if col < largeur && adr <= 0xFF_FFFF { Some(mem.lit(etage, adr as u32)) } else { None }
    };
    let mut max_petit = 0;
    for y in (0..h).step_by(cote) {
        for x in (0..l).step_by(cote) {
            if let Some(m) = lit(x, y) {
                if petit(m) {
                    max_petit = max_petit.max(m);
                }
            }
        }
    }
    for y in 0..h {
        let ligne = (y / cote) as u32 * pas;
        for x in 0..l {
            let col = (x / cote) as u32 * pas;
            px[y * l + x] = if col < largeur {
                let adr = base as u64 + ligne as u64 * largeur as u64 + col as u64;
                if adr <= 0xFF_FFFF { couleur(mem.lit(etage, adr as u32), max_petit) } else { 0x0008_0808 }
            } else {
                0x0008_0808
            };
        }
    }
}

/// En perspective isométrique : l'étage est un cube de 256 × 256 × 256 mots (adresse = x + 256 y + 65536 z, z vers
/// le haut) ; chaque mot non nul est un petit cube de sa couleur, les plus proches devant. Le cadrage suit les mots
/// présents ; la molette zoome.
pub fn rendre_iso(mem: &Memoire, etage: u32, zoom: f32, l: usize, h: usize, px: &mut [u32]) -> usize {
    for p in px.iter_mut() {
        *p = 0x0010_1418;
    }
    let mut voxels: Vec<(u32, u32)> = Vec::new();
    let mut max_petit = 0u32;
    let (mut x0, mut y0, mut z0, mut x1, mut y1, mut z1) = (255u32, 255u32, 255u32, 0u32, 0u32, 0u32);
    for adr in 0..(1u32 << 24) {
        let m = mem.lit(etage, adr);
        if m != 0 {
            let (x, y, z) = (adr & 255, (adr >> 8) & 255, adr >> 16);
            x0 = x0.min(x);
            y0 = y0.min(y);
            z0 = z0.min(z);
            x1 = x1.max(x);
            y1 = y1.max(y);
            z1 = z1.max(z);
            if voxels.len() < 8_000_000 {
                voxels.push((adr, m));
            }
            if petit(m) {
                max_petit = max_petit.max(m);
            }
        }
    }
    if voxels.is_empty() {
        x0 = 0;
        y0 = 0;
        z0 = 0;
        x1 = 255;
        y1 = 255;
        z1 = 255;
    }
    // la boîte, au moins 8 de côté
    let elargir = |a: &mut u32, b: &mut u32| {
        if *b - *a < 7 {
            *b = (*a + 7).min(255);
            *a = b.saturating_sub(7);
        }
    };
    elargir(&mut x0, &mut x1);
    elargir(&mut y0, &mut y1);
    elargir(&mut z0, &mut z1);
    let (dx, dy, dz) = ((x1 - x0 + 1) as f32, (y1 - y0 + 1) as f32, (z1 - z0 + 1) as f32);
    let c30 = 0.866_025_4f32;
    let largeur_p = (dx + dy) * c30;
    let hauteur_p = (dx + dy) * 0.5 + dz;
    let u = ((l as f32 * 0.9) / largeur_p).min((h as f32 * 0.9) / hauteur_p) * zoom;
    let ox = l as f32 / 2.0 - (dx - dy) * c30 * u / 2.0;
    let oy = h as f32 / 2.0 - ((dx + dy) * 0.5 - dz) * u / 2.0;
    let proj = |x: f32, y: f32, z: f32| -> (f32, f32) { (ox + (x - y) * c30 * u, oy + (x + y) * 0.5 * u - z * u) };
    // les arêtes de la boîte
    let trait_ = |a: (f32, f32), b: (f32, f32), c: u32, px: &mut [u32]| {
        let n = ((b.0 - a.0).abs().max((b.1 - a.1).abs()) as usize).max(1);
        for i in 0..=n {
            let t = i as f32 / n as f32;
            let (x, y) = ((a.0 + (b.0 - a.0) * t) as i32, (a.1 + (b.1 - a.1) * t) as i32);
            if x >= 0 && y >= 0 && (x as usize) < l && (y as usize) < h {
                px[y as usize * l + x as usize] = c;
            }
        }
    };
    let coins = [(0.0, 0.0, 0.0), (dx, 0.0, 0.0), (0.0, dy, 0.0), (dx, dy, 0.0), (0.0, 0.0, dz), (dx, 0.0, dz), (0.0, dy, dz), (dx, dy, dz)];
    for &(i, j) in &[(0, 1), (0, 2), (1, 3), (2, 3), (4, 5), (4, 6), (5, 7), (6, 7), (0, 4), (1, 5), (2, 6), (3, 7)] {
        let (a, b) = (coins[i], coins[j]);
        trait_(proj(a.0, a.1, a.2), proj(b.0, b.1, b.2), 0x0040_4858, px);
    }
    // les voxels : trois faces visibles (dessus clair, côtés plus sombres), les plus proches devant
    let mut z = vec![i32::MIN; l * h];
    for &(adr, m) in &voxels {
        let (x, y, zz) = ((adr & 255) - x0, ((adr >> 8) & 255) - y0, (adr >> 16) - z0);
        if x as f32 >= dx || y as f32 >= dy || zz as f32 >= dz {
            continue;
        }
        let profondeur = (x + y + zz) as i32;
        let c = couleur(m, max_petit);
        let (xf, yf, zf) = (x as f32, y as f32, zz as f32);
        if u < 2.5 {
            // petit : un point
            let (sx, sy) = proj(xf + 0.5, yf + 0.5, zf + 0.5);
            let (xx, yy) = (sx as i32, sy as i32);
            for (di, dj) in [(0, 0), (1, 0), (0, 1), (1, 1)].iter().take(if u < 1.5 { 1 } else { 4 }) {
                let (a_, b_) = (xx + di, yy + dj);
                if a_ >= 0 && b_ >= 0 && (a_ as usize) < l && (b_ as usize) < h {
                    let k = b_ as usize * l + a_ as usize;
                    if profondeur >= z[k] {
                        z[k] = profondeur;
                        px[k] = c;
                    }
                }
            }
            continue;
        }
        // un vrai petit cube : le dessus et les deux faces tournées vers nous, ombrées
        let assombrir = |c: u32, k: u32| (((c >> 16) & 255) * k / 10) << 16 | (((c >> 8) & 255) * k / 10) << 8 | (c & 255) * k / 10;
        let faces = [
            ([(0.0, 0.0, 1.0), (1.0, 0.0, 1.0), (1.0, 1.0, 1.0), (0.0, 1.0, 1.0)], 10),
            ([(1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (1.0, 1.0, 1.0), (1.0, 0.0, 1.0)], 6),
            ([(0.0, 1.0, 0.0), (1.0, 1.0, 0.0), (1.0, 1.0, 1.0), (0.0, 1.0, 1.0)], 8),
        ];
        for (coins, k) in faces.iter() {
            let q: Vec<(f32, f32)> = coins.iter().map(|&(a_, b_, c_)| proj(xf + a_, yf + b_, zf + c_)).collect();
            let teinte = assombrir(c, *k);
            let (mx0, mx1) = (q.iter().map(|p| p.0).fold(f32::MAX, f32::min), q.iter().map(|p| p.0).fold(f32::MIN, f32::max));
            let (my0, my1) = (q.iter().map(|p| p.1).fold(f32::MAX, f32::min), q.iter().map(|p| p.1).fold(f32::MIN, f32::max));
            for yy in (my0.floor() as i32).max(0)..=(my1.ceil() as i32).min(h as i32 - 1) {
                for xx in (mx0.floor() as i32).max(0)..=(mx1.ceil() as i32).min(l as i32 - 1) {
                    let (fx, fy) = (xx as f32 + 0.5, yy as f32 + 0.5);
                    // dedans si du même côté des quatre arêtes
                    let mut pos = false;
                    let mut neg = false;
                    for e in 0..4 {
                        let (a_, b_) = (q[e], q[(e + 1) % 4]);
                        let v = (b_.0 - a_.0) * (fy - a_.1) - (b_.1 - a_.1) * (fx - a_.0);
                        if v > 0.0 {
                            pos = true;
                        } else if v < 0.0 {
                            neg = true;
                        }
                    }
                    if pos && neg {
                        continue;
                    }
                    let kk = yy as usize * l + xx as usize;
                    if profondeur >= z[kk] {
                        z[kk] = profondeur;
                        px[kk] = teinte;
                    }
                }
            }
        }
    }
    voxels.len()
}


/// vtx image PROG.vtx SORTIE.ppm [étage] [plan|iso] [entrées…] : lance le programme et écrit le cube en image (PPM).
pub fn image(args: &[String]) {
    use super::{compiler_avec, dossier_de, executer_dans, nombres, COMPLET, VTXC};
    if args.len() < 2 {
        eprintln!("utilisation : vtx image PROG.vtx SORTIE.ppm [étage] [plan|iso] [entrées…]");
        std::process::exit(2);
    }
    let source = std::fs::read_to_string(&args[0]).expect("lecture impossible");
    let base = dossier_de(&args[0]);
    let (mots, _) = compiler_avec(&nombres(VTXC), &source, &base, COMPLET).unwrap_or_else(|e| {
        eprint!("{}", e);
        std::process::exit(1)
    });
    let mut mem = Memoire::new(false);
    super::charger(&mut mem, &mots);
    let entrees: Vec<u32> = args.iter().skip(4).filter_map(|x| x.parse::<u64>().ok()).map(|x| x as u32).collect();
    executer_dans(&mem, &entrees, 5_000_000_000, Some(std::path::Path::new(&base)), None).unwrap_or_else(|e| {
        eprintln!("erreur : {}", e);
        std::process::exit(1)
    });
    let etage = args.get(2).and_then(|e| e.parse().ok()).unwrap_or(1);
    let (l, h) = (800usize, 600usize);
    let mut px = vec![0u32; l * h];
    if args.get(3).map(|s| s.as_str()) == Some("plan") {
        rendre_plan(&mem, etage, 128, 0, l, h, &mut px);
    } else {
        let n = rendre_iso(&mem, etage, 1.0, l, h, &mut px);
        println!("{} mots non nuls dans l'étage {}", n, etage);
    }
    let mut o = format!("P6\n{} {}\n255\n", l, h).into_bytes();
    for p in px {
        o.extend_from_slice(&[(p >> 16) as u8, (p >> 8) as u8, p as u8]);
    }
    std::fs::write(&args[1], o).expect("écriture impossible");
}

// ------------------------------------------------------------------------------------------------ l'icône
/// L'icône de Vercintorix : le cube chromatique vu de son coin blanc (1, 1, 1), ses trois faces visibles colorées par
/// leur position (rouge, vert, bleu = x, y, z). Pixels 0xAARRGGBB, de haut en bas.
pub fn icone(taille: usize) -> Vec<u32> {
    let mut px = vec![0u32; taille * taille];
    let s = taille as f32 / 2.1;
    let c30 = 0.866_025_4f32;
    let (cx, cy) = (taille as f32 / 2.0, taille as f32 / 2.0 + s * 0.5);
    let proj = |x: f32, y: f32, z: f32| (cx + (x - y) * c30 * s * 0.98, cy + ((x + y) * 0.5 - z) * s * 0.98 - s * 0.5);
    // une face : origine, deux arêtes, et la couleur d'un point (a, b) de la face ; ombre
    let faces: [((f32, f32, f32), (f32, f32, f32), (f32, f32, f32), u8, f32); 3] = [
        ((0.0, 0.0, 1.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), 0, 1.0),   // dessus : z = 1
        ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0), 1, 0.88),  // x = 1
        ((0.0, 1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0), 2, 0.74),  // y = 1
    ];
    for y in 0..taille {
        for x in 0..taille {
            let (fx, fy) = (x as f32 + 0.5, y as f32 + 0.5);
            for &(o, u, v, genre, ombre) in faces.iter() {
                let po = proj(o.0, o.1, o.2);
                let pu = proj(o.0 + u.0, o.1 + u.1, o.2 + u.2);
                let pv = proj(o.0 + v.0, o.1 + v.1, o.2 + v.2);
                let (ux, uy, vx, vy) = (pu.0 - po.0, pu.1 - po.1, pv.0 - po.0, pv.1 - po.1);
                let det = ux * vy - uy * vx;
                if det.abs() < 1e-6 {
                    continue;
                }
                let (dx, dy) = (fx - po.0, fy - po.1);
                let a = (dx * vy - dy * vx) / det;
                let b = (ux * dy - uy * dx) / det;
                if (-0.01..=1.01).contains(&a) && (-0.01..=1.01).contains(&b) {
                    let (a, b) = (a.clamp(0.0, 1.0), b.clamp(0.0, 1.0));
                    let (r, g, bl) = match genre {
                        0 => (a, b, 1.0),
                        1 => (1.0, a, b),
                        _ => (a, 1.0, b),
                    };
                    let k = |v: f32| ((v * 0.85 + 0.15) * ombre * 255.0) as u32;
                    px[y * taille + x] = 0xFF00_0000 | k(r) << 16 | k(g) << 8 | k(bl);
                    break;
                }
            }
        }
    }
    px
}

/// Un fichier .ico (Windows) : plusieurs tailles, en 32 bits.
pub fn ico(tailles: &[usize]) -> Vec<u8> {
    let mut o = vec![0, 0, 1, 0, tailles.len() as u8, 0];
    let mut images = Vec::new();
    for &t in tailles {
        let px = icone(t);
        let mut im = Vec::new();
        for v in [40u32, t as u32, 2 * t as u32] {
            im.extend_from_slice(&v.to_le_bytes());
        }
        im.extend_from_slice(&1u16.to_le_bytes());
        im.extend_from_slice(&32u16.to_le_bytes());
        for _ in 0..6 {
            im.extend_from_slice(&0u32.to_le_bytes());
        }
        for y in (0..t).rev() {
            for x in 0..t {
                im.extend_from_slice(&px[y * t + x].to_le_bytes()); // BGRA en petit-boutiste
            }
        }
        let ligne_masque = (t + 31) / 32 * 4;
        im.extend(std::iter::repeat(0u8).take(ligne_masque * t));
        images.push(im);
    }
    let mut decalage = 6 + 16 * tailles.len();
    for (i, &t) in tailles.iter().enumerate() {
        o.extend_from_slice(&[if t >= 256 { 0 } else { t as u8 }, if t >= 256 { 0 } else { t as u8 }, 0, 0]);
        o.extend_from_slice(&1u16.to_le_bytes());
        o.extend_from_slice(&32u16.to_le_bytes());
        o.extend_from_slice(&(images[i].len() as u32).to_le_bytes());
        o.extend_from_slice(&(decalage as u32).to_le_bytes());
        decalage += images[i].len();
    }
    for im in images {
        o.extend(im);
    }
    o
}

/// Un fichier .png (Linux) : compression « stockée » (sans bibliothèque), CRC et Adler-32 calculés ici.
pub fn png(t: usize) -> Vec<u8> {
    png_de(&icone(t), t, t)
}

// ------------------------------------------------------------------------------------------------ le dessin
/// La taille de l'image préparée par ecran(l, h) (rangée en @3[14680058] et @3[14680059]), si le programme en a une.
pub fn taille_dessin(mem: &Memoire) -> Option<(u32, u32)> {
    let (l, h) = (mem.lit(3, 14_680_058), mem.lit(3, 14_680_059));
    if l >= 1 && h >= 1 && l <= 4096 && h <= 4096 && l * h <= 1 << 24 { Some((l, h)) } else { None }
}

/// L'image du programme (étage 1, ligne par ligne, mots #RRGGBBAA) agrandie pour remplir la vue sans la déformer.
pub fn rendre_dessin(mem: &Memoire, l: usize, h: usize, px: &mut [u32]) -> bool {
    let (dl, dh) = match taille_dessin(mem) {
        Some(t) => (t.0 as usize, t.1 as usize),
        None => return false,
    };
    let e = (l as f32 / dl as f32).min(h as f32 / dh as f32).max(0.01);
    let (ll, hh) = ((dl as f32 * e) as usize, (dh as f32 * e) as usize);
    let (x0, y0) = ((l - ll.min(l)) / 2, (h - hh.min(h)) / 2);
    for y in 0..hh.min(h) {
        let sy = ((y as f32 / e) as usize).min(dh - 1);
        for x in 0..ll.min(l) {
            let sx = ((x as f32 / e) as usize).min(dl - 1);
            px[(y0 + y) * l + x0 + x] = mem.lit(1, (sy * dl + sx) as u32) >> 8;
        }
    }
    true
}

/// vtx dessin PROG.vtx SORTIE.png [ÉCHELLE] : le programme, puis son image en PNG.
pub fn dessin(args: &[String]) {
    use super::{compiler_avec, dossier_de, executer_dans, nombres, COMPLET, VTXC};
    if args.len() < 2 {
        eprintln!("utilisation : vtx dessin PROG.vtx SORTIE.png [ÉCHELLE]");
        std::process::exit(2);
    }
    let source = std::fs::read_to_string(&args[0]).expect("lecture impossible");
    let base = dossier_de(&args[0]);
    let (mots, _) = compiler_avec(&nombres(VTXC), &source, &base, COMPLET).unwrap_or_else(|e| {
        eprint!("{}", e);
        std::process::exit(1)
    });
    let mut mem = Memoire::new(false);
    super::charger(&mut mem, &mots);
    executer_dans(&mem, &[], 5_000_000_000, Some(std::path::Path::new(&base)), None).unwrap_or_else(|e| {
        eprintln!("erreur : {}", e);
        std::process::exit(1)
    });
    let (dl, dh) = match taille_dessin(&mem) {
        Some(t) => t,
        None => {
            eprintln!("ce programme ne dessine pas (pas d'appel à ecran(l, h))");
            std::process::exit(1)
        }
    };
    let e: usize = args.get(2).and_then(|x| x.parse().ok()).unwrap_or(4).clamp(1, 16);
    let (l, h) = (dl as usize * e, dh as usize * e);
    let mut px = vec![0u32; l * h];
    rendre_dessin(&mem, l, h, &mut px);
    std::fs::write(&args[1], png_de(&px.iter().map(|&v| v | 0xFF00_0000).collect::<Vec<u32>>(), l, h)).expect("écriture impossible");
    println!("{} : {} × {} points (× {})", args[1], dl, dh, e);
}

/// Un PNG (sans compression) à partir de pixels 0xAARRGGBB, de haut en bas.
pub fn png_de(px: &[u32], l: usize, t_h: usize) -> Vec<u8> {
    let t = l;
    let mut brut = Vec::new();
    for y in 0..t_h {
        brut.push(0u8);
        for x in 0..t {
            let v = px[y * t + x];
            brut.extend_from_slice(&[(v >> 16) as u8, (v >> 8) as u8, v as u8, (v >> 24) as u8]);
        }
    }
    let mut z = vec![0x78, 0x01];
    let blocs: Vec<&[u8]> = brut.chunks(65535).collect();
    for (i, b) in blocs.iter().enumerate() {
        z.push(if i + 1 == blocs.len() { 1 } else { 0 });
        z.extend_from_slice(&(b.len() as u16).to_le_bytes());
        z.extend_from_slice(&(!(b.len() as u16)).to_le_bytes());
        z.extend_from_slice(b);
    }
    let (mut a, mut b) = (1u32, 0u32);
    for &x in &brut {
        a = (a + x as u32) % 65521;
        b = (b + a) % 65521;
    }
    z.extend_from_slice(&((b << 16) | a).to_be_bytes());
    fn crc(d: &[u8]) -> u32 {
        let mut c = 0xFFFF_FFFFu32;
        for &x in d {
            c ^= x as u32;
            for _ in 0..8 {
                c = if c & 1 != 0 { 0xEDB8_8320 ^ (c >> 1) } else { c >> 1 };
            }
        }
        !c
    }
    let mut o = vec![0x89, b'P', b'N', b'G', 13, 10, 26, 10];
    let morceau = |genre: &[u8], d: &[u8], o: &mut Vec<u8>| {
        o.extend_from_slice(&(d.len() as u32).to_be_bytes());
        let mut c = genre.to_vec();
        c.extend_from_slice(d);
        o.extend_from_slice(&c);
        o.extend_from_slice(&crc(&c).to_be_bytes());
    };
    let mut ihdr = Vec::new();
    ihdr.extend_from_slice(&(t as u32).to_be_bytes());
    ihdr.extend_from_slice(&(t_h as u32).to_be_bytes());
    ihdr.extend_from_slice(&[8, 6, 0, 0, 0]);
    morceau(b"IHDR", &ihdr, &mut o);
    morceau(b"IDAT", &z, &mut o);
    morceau(b"IEND", &[], &mut o);
    o
}
