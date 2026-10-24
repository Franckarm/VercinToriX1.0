// Une animation GIF, écrite à la main (sans bibliothèque), à partir des images que montre presenter().
//
// La palette est le cube chromatique lui-même, réduit à 6 niveaux par voie (216 couleurs, index r × 36 + g × 6 + b),
// plus 39 gris ; une trame ordonnée (Bayer 4 × 4) garde exactes les couleurs posées sur la grille (0, 51, 102… 255).
//
// L'anti-cube : chaque image n'est écrite que par sa différence avec la précédente. Un point qui n'a pas changé n'apporte
// aucune preuve nouvelle : il est *inconnu* (au sens de Belnap) et devient l'index transparent 255, que le GIF laisse
// voir à travers ; seul le rectangle qui contient des changements est écrit. Une image identique à la précédente
// n'ajoute rien : elle allonge seulement la durée de la précédente.

const TRANSPARENT: u8 = 255;
const BAYER: [u8; 16] = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5];

pub struct Gif {
    l: usize,
    h: usize,
    octets: Vec<u8>,
    prec: Option<Vec<u8>>,
    // la place du délai de la dernière image écrite (pour l'allonger), et ce délai
    place_delai: usize,
    delai: u32,
    pub images: usize,
}

fn palette() -> Vec<u8> {
    let mut p = Vec::with_capacity(768);
    for r in 0..6u32 {
        for g in 0..6u32 {
            for b in 0..6u32 {
                p.extend_from_slice(&[(r * 51) as u8, (g * 51) as u8, (b * 51) as u8]);
            }
        }
    }
    for k in 0..39u32 {
        let v = ((k * 255 + 19) / 38) as u8;
        p.extend_from_slice(&[v, v, v]);
    }
    p.extend_from_slice(&[0, 0, 0]);
    p
}

/// L'index de la palette d'un point 0x00RRGGBB, tramé selon sa place.
pub fn index(c: u32, x: usize, y: usize) -> u8 {
    let (r, g, b) = ((c >> 16) & 255, (c >> 8) & 255, c & 255);
    let t = BAYER[(y & 3) * 4 + (x & 3)] as u32; // seuil t / 16
    if r == g && g == b && r % 51 != 0 {
        // un gris hors de la grille : la rampe de 39 gris
        let q = ((r * 38 * 16 + t * 255) / (255 * 16)).min(38);
        return 216 + q as u8;
    }
    let q = |v: u32| ((v * 5 * 16 + t * 255) / (255 * 16)).min(5);
    (q(r) * 36 + q(g) * 6 + q(b)) as u8
}

impl Gif {
    pub fn new(l: usize, h: usize) -> Gif {
        let (l, h) = (l.clamp(1, 65535), h.clamp(1, 65535));
        let mut o = Vec::new();
        o.extend_from_slice(b"GIF89a");
        o.extend_from_slice(&(l as u16).to_le_bytes());
        o.extend_from_slice(&(h as u16).to_le_bytes());
        o.extend_from_slice(&[0xF7, 0, 0]);
        o.extend_from_slice(&palette());
        // NETSCAPE2.0 : l'animation tourne en boucle
        o.extend_from_slice(&[0x21, 0xFF, 11]);
        o.extend_from_slice(b"NETSCAPE2.0");
        o.extend_from_slice(&[3, 1, 0, 0, 0]);
        Gif { l, h, octets: o, prec: None, place_delai: 0, delai: 0, images: 0 }
    }

    pub fn largeur(&self) -> usize {
        self.l
    }
    pub fn hauteur(&self) -> usize {
        self.h
    }

    /// Ajoute une image de l × h points (0x00RRGGBB), montrée pendant `ms` millisecondes. Une image d'une autre taille
    /// que la première est recadrée (coin haut gauche) ou complétée en noir.
    pub fn ajouter(&mut self, l: usize, h: usize, px: &[u32], ms: u32) {
        let cs = ((ms + 5) / 10).max(2); // les navigateurs ralentissent les délais de moins de 2 centièmes
        let mut idx = vec![0u8; self.l * self.h];
        for y in 0..self.h {
            for x in 0..self.l {
                let c = if x < l && y < h { px[y * l + x] } else { 0 };
                idx[y * self.l + x] = index(c, x, y);
            }
        }
        // le rectangle des changements (toute l'image pour la première)
        let (mut x0, mut y0, mut x1, mut y1) = (self.l, self.h, 0usize, 0usize);
        match &self.prec {
            None => {
                x0 = 0;
                y0 = 0;
                x1 = self.l - 1;
                y1 = self.h - 1;
            }
            Some(p) => {
                for y in 0..self.h {
                    for x in 0..self.l {
                        if p[y * self.l + x] != idx[y * self.l + x] {
                            x0 = x0.min(x);
                            x1 = x1.max(x);
                            y0 = y0.min(y);
                            y1 = y1.max(y);
                        }
                    }
                }
                if x0 > x1 {
                    // rien de neuf : la précédente dure plus longtemps
                    self.delai = (self.delai + cs).min(65535);
                    let d = (self.delai as u16).to_le_bytes();
                    self.octets[self.place_delai] = d[0];
                    self.octets[self.place_delai + 1] = d[1];
                    return;
                }
            }
        }
        let (rl, rh) = (x1 - x0 + 1, y1 - y0 + 1);
        let mut donnees = Vec::with_capacity(rl * rh);
        for y in y0..=y1 {
            for x in x0..=x1 {
                let v = idx[y * self.l + x];
                let inchange = self.prec.as_ref().map(|p| p[y * self.l + x] == v).unwrap_or(false);
                donnees.push(if inchange { TRANSPARENT } else { v });
            }
        }
        // extension de contrôle : ne pas effacer (1 << 2), transparence (1), délai, index transparent
        let o = &mut self.octets;
        o.extend_from_slice(&[0x21, 0xF9, 4, 0x05]);
        self.place_delai = o.len();
        self.delai = cs;
        o.extend_from_slice(&(cs as u16).to_le_bytes());
        o.extend_from_slice(&[TRANSPARENT, 0]);
        o.push(0x2C);
        for v in [x0, y0, rl, rh] {
            o.extend_from_slice(&(v as u16).to_le_bytes());
        }
        o.push(0);
        o.push(8);
        let lzw = lzw(&donnees);
        for bloc in lzw.chunks(255) {
            o.push(bloc.len() as u8);
            o.extend_from_slice(bloc);
        }
        o.push(0);
        self.prec = Some(idx);
        self.images += 1;
    }

    /// Le fichier complet.
    pub fn finir(mut self) -> Vec<u8> {
        self.octets.push(0x3B);
        self.octets
    }
}

/// La compression LZW du GIF (taille minimale de code 8) : codes de 9 à 12 bits, rangés bit à bit, poids faible d'abord.
fn lzw(donnees: &[u8]) -> Vec<u8> {
    const EFFACER: u32 = 256;
    const FIN: u32 = 257;
    let mut sortie = Vec::new();
    let (mut acc, mut nb) = (0u32, 0u32);
    let mut ecrire = |code: u32, taille: u32, sortie: &mut Vec<u8>| {
        acc |= code << nb;
        nb += taille;
        while nb >= 8 {
            sortie.push((acc & 255) as u8);
            acc >>= 8;
            nb -= 8;
        }
    };
    // le dictionnaire : pour chaque (préfixe, octet), génération × 4096 + code ; une entrée d'une autre génération est
    // absente (repartir de zéro ne coûte alors qu'un compteur)
    let mut dico = vec![0u32; 4096 * 256];
    let mut generation = 1u32;
    let (mut suivant, mut taille) = (258u32, 9u32);
    ecrire(EFFACER, taille, &mut sortie);
    let mut iter = donnees.iter();
    let mut prefixe = match iter.next() {
        Some(&b) => b as u32,
        None => {
            ecrire(FIN, taille, &mut sortie);
            if nb > 0 {
                sortie.push((acc & 255) as u8);
            }
            return sortie;
        }
    };
    for &b in iter {
        let k = (prefixe as usize) * 256 + b as usize;
        if dico[k] >> 12 == generation {
            prefixe = dico[k] & 4095;
            continue;
        }
        ecrire(prefixe, taille, &mut sortie);
        if suivant < 4096 {
            dico[k] = (generation << 12) | suivant;
            suivant += 1;
            if suivant > (1 << taille) && taille < 12 {
                taille += 1;
            }
        }
        if suivant == 4096 {
            // le dictionnaire est plein : on repart de zéro
            ecrire(EFFACER, taille, &mut sortie);
            generation += 1;
            suivant = 258;
            taille = 9;
        }
        prefixe = b as u32;
    }
    ecrire(prefixe, taille, &mut sortie);
    ecrire(FIN, taille, &mut sortie);
    if nb > 0 {
        sortie.push((acc & 255) as u8);
    }
    sortie
}
