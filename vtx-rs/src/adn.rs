// L'ADN d'un programme et sa fiabilité par les trois témoins (docs/vtx-reactions.md, étape 5) : la même chose que
// chimie/adn.py, en Rust, pour que Lugus (et l'atelier) vérifient et réparent un programme rangé avant de le lancer.
// Les deux font le même ADN (le même découpage, les mêmes témoins, le même fichier) et le lisent de même :
// tests/test_adn.py le vérifie.
//
//   la signature de chaque molécule (64 bits) ; l'ombre (quatre mots de Reed-Solomon par colonne entrelacée d'au plus
//   251 mots) ; les neutrons (8 bits par mot, aux frontières : les molécules qui écrivent ou sortent quelque chose).
use std::collections::BTreeMap;

pub const INCONNU: u8 = 0;
pub const FAUX: u8 = 1;
pub const VRAI: u8 = 2;
pub const VARIABLE: u8 = 3;
const COLONNE: usize = 251;
const OMBRE: usize = 4;
const M64: u128 = u64::MAX as u128;

pub fn nom_etat(e: u8) -> &'static str {
    match e {
        VRAI => "vrai",
        FAUX => "faux (réparé)",
        VARIABLE => "variable",
        _ => "inconnu",
    }
}

fn pire(a: u8, b: u8) -> u8 {
    let rang = |e: u8| match e {
        VRAI => 0,
        INCONNU => 1,
        FAUX => 2,
        _ => 3,
    };
    if rang(a) >= rang(b) { a } else { b }
}

// ------------------------------------------------------------------------------------------------ Reed-Solomon, GF(256)
struct Gf {
    exp: [u8; 512],
    log: [u8; 256],
}

fn gf() -> &'static Gf {
    static G: std::sync::OnceLock<Gf> = std::sync::OnceLock::new();
    G.get_or_init(|| {
        let mut g = Gf { exp: [0; 512], log: [0; 256] };
        let mut x: u32 = 1;
        for i in 0..255 {
            g.exp[i] = x as u8;
            g.log[x as usize] = i as u8;
            x <<= 1;
            if x & 0x100 != 0 {
                x ^= 0x11D;
            }
        }
        for i in 255..512 {
            g.exp[i] = g.exp[i - 255];
        }
        g
    })
}

fn mul(a: u8, b: u8) -> u8 {
    if a == 0 || b == 0 {
        return 0;
    }
    let g = gf();
    g.exp[g.log[a as usize] as usize + g.log[b as usize] as usize]
}

fn div(a: u8, b: u8) -> u8 {
    if a == 0 {
        return 0;
    }
    let g = gf();
    g.exp[(g.log[a as usize] as usize + 255 - g.log[b as usize] as usize) % 255]
}

fn pw(a: u8, n: usize) -> u8 {
    if a == 0 {
        return 0;
    }
    let g = gf();
    g.exp[(g.log[a as usize] as usize * n) % 255]
}

fn inv(a: u8) -> u8 {
    let g = gf();
    g.exp[255 - g.log[a as usize] as usize]
}

fn p_mul(p: &[u8], q: &[u8]) -> Vec<u8> {
    let mut r = vec![0u8; p.len() + q.len() - 1];
    for (j, &b) in q.iter().enumerate() {
        for (i, &a) in p.iter().enumerate() {
            r[i + j] ^= mul(a, b);
        }
    }
    r
}

fn p_add(p: &[u8], q: &[u8]) -> Vec<u8> {
    let n = p.len().max(q.len());
    let mut r = vec![0u8; n];
    r[n - p.len()..].copy_from_slice(p);
    for i in 0..q.len() {
        r[i + n - q.len()] ^= q[i];
    }
    r
}

fn p_scale(p: &[u8], x: u8) -> Vec<u8> {
    p.iter().map(|&a| mul(a, x)).collect()
}

fn p_eval(p: &[u8], x: u8) -> u8 {
    let mut y = p[0];
    for &c in &p[1..] {
        y = mul(y, x) ^ c;
    }
    y
}

fn generateur(r: usize) -> Vec<u8> {
    let mut g = vec![1u8];
    for i in 0..r {
        g = p_mul(&g, &[1, gf().exp[i]]);
    }
    g
}

/// msg (le plus fort d'abord) -> les r octets de contrôle
pub fn coder(msg: &[u8], r: usize) -> Vec<u8> {
    let g = generateur(r);
    let mut out = msg.to_vec();
    out.extend(std::iter::repeat(0).take(r));
    for i in 0..msg.len() {
        let c = out[i];
        if c != 0 {
            for j in 1..g.len() {
                out[i + j] ^= mul(g[j], c);
            }
        }
    }
    out[msg.len()..].to_vec()
}

fn syndromes(cw: &[u8], r: usize) -> Vec<u8> {
    let mut s = vec![0u8];
    for i in 0..r {
        s.push(p_eval(cw, gf().exp[i]));
    }
    s
}

fn localisateur_effacements(pos_coef: &[usize]) -> Vec<u8> {
    let mut e = vec![1u8];
    for &p in pos_coef {
        e = p_mul(&e, &p_add(&[1], &[gf().exp[p], 0]));
    }
    e
}

fn divmod_reste(dividende: &[u8], diviseur: &[u8]) -> Vec<u8> {
    let mut out = dividende.to_vec();
    let d = diviseur.len() - 1;
    if dividende.len() >= d {
        for i in 0..dividende.len() - d {
            let c = out[i];
            if c != 0 {
                for j in 1..diviseur.len() {
                    if diviseur[j] != 0 {
                        out[i + j] ^= mul(diviseur[j], c);
                    }
                }
            }
        }
    }
    out[out.len() - d..].to_vec()
}

fn corriger_valeurs(cw: &[u8], synd: &[u8], pos_err: &[usize]) -> Option<Vec<u8>> {
    let n = cw.len();
    let coef_pos: Vec<usize> = pos_err.iter().map(|&p| n - 1 - p).collect();
    let loc = localisateur_effacements(&coef_pos);
    let synd_inv: Vec<u8> = synd.iter().rev().cloned().collect();
    let mut div_ = vec![1u8];
    div_.extend(std::iter::repeat(0).take(loc.len()));     // [1] + [0] * (r + 1), r = len(loc) - 1
    let omega: Vec<u8> = divmod_reste(&p_mul(&synd_inv, &loc), &div_).into_iter().rev().collect();
    let x: Vec<u8> = coef_pos.iter().map(|&p| gf().exp[p]).collect();
    let mut e = vec![0u8; n];
    for (i, &xi) in x.iter().enumerate() {
        let xi_inv = inv(xi);
        let mut prime = 1u8;
        for (j, &xj) in x.iter().enumerate() {
            if j != i {
                prime = mul(prime, 1 ^ mul(xi_inv, xj));
            }
        }
        if prime == 0 {
            return None;
        }
        let om: Vec<u8> = omega.iter().rev().cloned().collect();
        let y = mul(pw(xi, 1), p_eval(&om, xi_inv));
        e[pos_err[i]] = div(y, prime);
    }
    Some(cw.iter().zip(e.iter()).map(|(c, e)| c ^ e).collect())
}

fn trouver_localisateur(synd: &[u8], r: usize, nb_eff: usize) -> Option<Vec<u8>> {
    let mut err_loc = vec![1u8];
    let mut old_loc = vec![1u8];
    let decal = synd.len() - r;
    for i in 0..r.saturating_sub(nb_eff) {
        let k = i + decal;
        let mut delta = synd[k];
        for j in 1..err_loc.len() {
            delta ^= mul(err_loc[err_loc.len() - 1 - j], synd[k - j]);
        }
        old_loc.push(0);
        if delta != 0 {
            if old_loc.len() > err_loc.len() {
                let new_loc = p_scale(&old_loc, delta);
                old_loc = p_scale(&err_loc, inv(delta));
                err_loc = new_loc;
            }
            err_loc = p_add(&err_loc, &p_scale(&old_loc, delta));
        }
    }
    while !err_loc.is_empty() && err_loc[0] == 0 {
        err_loc.remove(0);
    }
    if err_loc.is_empty() {
        return None;
    }
    let errs = err_loc.len() - 1;
    if (errs as isize - nb_eff as isize) * 2 + nb_eff as isize > r as isize {
        return None;
    }
    Some(err_loc)
}

fn trouver_erreurs(err_loc: &[u8], n: usize) -> Option<Vec<usize>> {
    let errs = err_loc.len() - 1;
    let pos: Vec<usize> = (0..n).filter(|&i| p_eval(err_loc, pw(2, i)) == 0).map(|i| n - 1 - i).collect();
    if pos.len() != errs { None } else { Some(pos) }
}

fn forney_syndromes(synd: &[u8], pos: &[usize], n: usize) -> Vec<u8> {
    let mut fs: Vec<u8> = synd[1..].to_vec();
    for &q in pos {
        let x = gf().exp[n - 1 - q];
        for j in 0..fs.len() - 1 {
            fs[j] = mul(fs[j], x) ^ fs[j + 1];
        }
    }
    fs
}

/// le mot de code corrigé (2 erreurs + effacements <= r), ou None
pub fn decoder(cw0: &[u8], r: usize, effaces: &[usize]) -> Option<Vec<u8>> {
    let mut cw = cw0.to_vec();
    let n = cw.len();
    if effaces.len() > r {
        return None;
    }
    for &p in effaces {
        cw[p] = 0;
    }
    let synd = syndromes(&cw, r);
    if synd.iter().all(|&s| s == 0) {
        return Some(cw);
    }
    let fsynd = forney_syndromes(&synd, effaces, n);
    let err_loc = trouver_localisateur(&fsynd, r, effaces.len())?;
    let rev: Vec<u8> = err_loc.iter().rev().cloned().collect();
    let pos = trouver_erreurs(&rev, n)?;
    let mut toutes: Vec<usize> = effaces.to_vec();
    for p in pos {
        if !effaces.contains(&p) {
            toutes.push(p);
        }
    }
    let out = corriger_valeurs(&cw, &synd, &toutes)?;
    if syndromes(&out, r).iter().any(|&s| s != 0) {
        return None;
    }
    Some(out)
}

// ------------------------------------------------------------------------------------------------ les témoins
fn melanger(z: u64) -> u64 {
    let mut z = z.wrapping_add(0x9E3779B97F4A7C15);
    z = (z ^ (z >> 30)).wrapping_mul(0xBF58476D1CE4E5B9);
    z = (z ^ (z >> 27)).wrapping_mul(0x94D049BB133111EB);
    z ^ (z >> 31)
}

pub fn signature(mots: &[u128]) -> u64 {
    let mut h = melanger(0x5643_5458_4144_4E00 ^ mots.len() as u64);
    for &w in mots {
        h = melanger(h ^ (w & M64) as u64);
        h = melanger(h ^ (w >> 64) as u64);
    }
    h
}

pub fn crc8(w: u128) -> u8 {
    let mut c: u8 = 0;
    for octet in w.to_le_bytes() {
        c ^= octet;
        for _ in 0..8 {
            c = if c & 0x80 != 0 { (c << 1) ^ 0x07 } else { c << 1 };
        }
    }
    c
}

fn voies(mots: &[u128]) -> Vec<Vec<u8>> {
    (0..16).map(|k| mots.iter().map(|&w| ((w >> (8 * (15 - k))) & 0xFF) as u8).collect()).collect()
}

fn mots_de(v: &[Vec<u8>]) -> Vec<u128> {
    (0..v[0].len()).map(|i| (0..16).fold(0u128, |acc, k| acc | ((v[k][i] as u128) << (8 * (15 - k))))).collect()
}

fn ombre_colonne(mots: &[u128]) -> Vec<u128> {
    let v: Vec<Vec<u8>> = voies(mots).iter().map(|l| coder(l, OMBRE)).collect();
    mots_de(&v)
}

fn nb_colonnes(n: usize) -> usize {
    ((n + COLONNE - 1) / COLONNE).max(1)
}

fn places_colonne(n: usize, k: usize) -> Vec<usize> {
    (k..n).step_by(nb_colonnes(n)).collect()
}

#[derive(Clone, Debug)]
pub struct Molecule {
    pub debut: usize,
    pub fin: usize,
    pub frontiere: bool,
    /// l'isotope lourd : une réaction qui porte un atome lourd (« -> a lourd ») ; ses mots gardent leurs neutrons
    pub isotope: bool,
}

impl Molecule {
    /// une molécule qui porte des neutrons : une frontière (O), ou un isotope lourd
    pub fn neutronee(&self) -> bool {
        self.frontiere || self.isotope
    }
}

#[derive(Clone, Debug, PartialEq)]
pub struct Temoins {
    pub signatures: Vec<u64>,
    pub ombres: Vec<Vec<u128>>,
    pub neutrons: BTreeMap<usize, u8>,
    /// les autres sections de l'ADN (les introns : les isotopes, le texte…), dans l'ordre, gardées telles quelles
    pub introns: Vec<(String, Vec<String>)>,
}

impl Temoins {
    pub fn intron(&self, nom: &str) -> Option<&Vec<String>> {
        self.introns.iter().find(|(n, _)| n == nom).map(|(_, l)| l)
    }
}

const OP_CALL: u128 = 0x33;
const OP_LDI: u128 = 0x0A;
const OP_LDIH: u128 = 0x2B;
const OPS_FRONTIERE: [u128; 9] = [0x21, 0x24, 0x2A, 0x39, 0x52, 0x53, 0x55, 0x5E, 0x5F];

fn demis(mots: &[u128]) -> Vec<(u128, bool)> {
    let mut v = Vec::with_capacity(mots.len() * 2);
    let mut lit = false;
    for &w in mots {
        for h in [w >> 64, w & M64] {
            v.push((h, lit));
            lit = !lit && ((h >> 48) == OP_LDI || (h >> 48) == OP_LDIH);
        }
    }
    v
}

/// la tête, puis une molécule par fonction (de la cible d'un CALL à la suivante) ; frontière : son code écrit ou sort
pub fn decouper(mots: &[u128]) -> Vec<Molecule> {
    let n = mots.len();
    let mut debuts: Vec<usize> = vec![0];
    for (h, lit) in demis(mots) {
        if !lit && (h >> 48) == OP_CALL {
            let d = ((h & 0xFFFF_FFFF) / 2) as usize;
            if d < n {
                debuts.push(d);
            }
        }
    }
    debuts.sort();
    debuts.dedup();
    let mut mols = Vec::new();
    for (i, &a) in debuts.iter().enumerate() {
        let b = if i + 1 < debuts.len() { debuts[i + 1] } else { n };
        let frontiere = demis(&mots[a..b]).iter().any(|&(h, lit)| !lit && OPS_FRONTIERE.contains(&(h >> 48)));
        mols.push(Molecule { debut: a, fin: b, frontiere, isotope: false });
    }
    mols
}

pub fn temoins(mots: &[u128], mols: &[Molecule]) -> Temoins {
    let mut neutrons = BTreeMap::new();
    for m in mols {
        if m.neutronee() {
            for i in m.debut..m.fin {
                neutrons.insert(i, crc8(mots[i]));
            }
        }
    }
    let n = mots.len();
    Temoins {
        signatures: mols.iter().map(|m| signature(&mots[m.debut..m.fin])).collect(),
        ombres: (0..nb_colonnes(n)).map(|k| {
            let col: Vec<u128> = places_colonne(n, k).iter().map(|&i| mots[i]).collect();
            ombre_colonne(&col)
        }).collect(),
        neutrons,
        introns: vec![],
    }
}

pub fn place_des_temoins(mots: &[u128], mols: &[Molecule]) -> usize {
    let o: usize = mols.iter().filter(|m| m.neutronee()).map(|m| m.fin - m.debut).sum();
    (mols.len() + 1) / 2 + OMBRE * nb_colonnes(mots.len()) + (o + 15) / 16
}

// ------------------------------------------------------------------------------------------------ la lecture
fn lire_colonne(mots: &mut [u128], k: usize, t: &mut Temoins) -> (u8, Vec<usize>, Vec<usize>) {
    let n = mots.len();
    let places = places_colonne(n, k);
    let data: Vec<u128> = places.iter().map(|&i| mots[i]).collect();
    let effaces: Vec<usize> = (0..places.len())
        .filter(|&j| t.neutrons.get(&places[j]).map_or(false, |&c| crc8(data[j]) != c)).collect();
    let eff_places: Vec<usize> = effaces.iter().map(|&j| places[j]).collect();
    if ombre_colonne(&data) == t.ombres[k] {
        return (if effaces.is_empty() { VRAI } else { FAUX }, vec![], eff_places);
    }
    if effaces.len() > OMBRE {
        return (VARIABLE, vec![], eff_places);
    }
    let mut tout = data.clone();
    tout.extend(t.ombres[k].iter().cloned());
    let mut cw = voies(&tout);
    for v in 0..16 {
        match decoder(&cw[v], OMBRE, &effaces) {
            Some(out) => cw[v] = out,
            None => return (VARIABLE, vec![], eff_places),
        }
    }
    let neuf = mots_de(&cw);
    let reparees: Vec<usize> = (0..data.len()).filter(|&j| neuf[j] != data[j]).map(|j| places[j]).collect();
    for (j, &i) in places.iter().enumerate() {
        mots[i] = neuf[j];
    }
    t.ombres[k] = neuf[data.len()..].to_vec();
    (FAUX, reparees, eff_places)
}

/// vérifie et répare l'ADN en place : (l'état le pire, [(numéro de la molécule, état, ce qui a été fait)])
pub fn lire(mots: &mut [u128], mols: &[Molecule], t: &mut Temoins) -> (u8, Vec<(usize, u8, String)>) {
    let avant = mots.to_vec();
    let nc = nb_colonnes(mots.len());
    let mut col_etat = vec![VRAI; nc];
    let mut col_reparees: Vec<Vec<usize>> = vec![vec![]; nc];
    let mut par_neutrons = std::collections::BTreeSet::new();
    for k in 0..nc {
        let (e, rep, eff) = lire_colonne(mots, k, t);
        col_etat[k] = e;
        col_reparees[k] = rep;
        par_neutrons.extend(eff);
    }
    let mut etat = if col_etat.iter().any(|&e| e == FAUX) { FAUX } else { VRAI };
    let mut rapport = Vec::new();
    for (j, m) in mols.iter().enumerate() {
        let cols: std::collections::BTreeSet<usize> = (m.debut..m.fin).map(|i| i % nc).collect();
        let changes: Vec<usize> = (m.debut..m.fin).filter(|&i| mots[i] != avant[i]).collect();
        let sig_ok = signature(&mots[m.debut..m.fin]) == t.signatures[j];
        let abimee = cols.iter().any(|&c| col_etat[c] == VARIABLE);
        let (e, quoi) = if sig_ok && changes.is_empty() && !abimee {
            (VRAI, String::new())
        } else if sig_ok {
            (FAUX, if changes.is_empty() { "ombre ou neutrons refaits".into() } else { format!("{} mot(s) réparé(s)", changes.len()) })
        } else if abimee {
            (VARIABLE, "abîmée au-delà de son ombre".into())
        } else if changes.is_empty() {
            t.signatures[j] = signature(&mots[m.debut..m.fin]);
            (FAUX, "signature refaite".into())
        } else if (m.neutronee() && changes.iter().all(|i| par_neutrons.contains(i) && t.neutrons.get(i) == Some(&crc8(mots[*i]))))
            || changes.iter().all(|&i| col_reparees[i % nc].len() == 1) {
            t.signatures[j] = signature(&mots[m.debut..m.fin]);
            (FAUX, format!("{} mot(s) réparé(s), signature refaite", changes.len()))
        } else {
            for &i in &changes {
                mots[i] = avant[i];
            }
            (VARIABLE, "réparation non confirmée par la signature".into())
        };
        etat = pire(etat, e);
        rapport.push((j, e, quoi));
    }
    if etat != VARIABLE {
        let cles: Vec<usize> = t.neutrons.keys().cloned().collect();
        for i in cles {
            t.neutrons.insert(i, crc8(mots[i]));
        }
    }
    (etat, rapport)
}

// ------------------------------------------------------------------------------------------------ le fichier
/// L'ADN de vtx, version 3 : des sections signalées comme des introns, « GU nom N », N lignes, puis « AG ». La lecture
/// saute une section qu'elle ne connaît pas sans rien analyser (comme chimie/adn.py, octet pour octet).
pub fn ecrire_adn(chemin: &str, mots: &[u128], mols: &[Molecule], t: &Temoins) -> std::io::Result<()> {
    let mut sections: Vec<(String, Vec<String>)> = vec![
        ("mots".into(), vec![mots.iter().map(|w| w.to_string()).collect::<Vec<_>>().join(",")]),
        ("molecules".into(), mols.iter().zip(t.signatures.iter())
            .map(|(m, sg)| format!("m{}|{}|{}|{}|{}|{}", m.debut, m.debut, m.fin, m.frontiere as u8, sg, m.isotope as u8)).collect()),
        ("ombres".into(), t.ombres.iter().map(|o| o.iter().map(|w| w.to_string()).collect::<Vec<_>>().join(",")).collect()),
        ("neutrons".into(), vec![t.neutrons.iter().map(|(i, v)| format!("{}:{}", i, v)).collect::<Vec<_>>().join(",")]),
    ];
    sections.extend(t.introns.iter().cloned());
    let mut s = String::from("VTXADN03\n");
    for (nom, lignes) in &sections {
        s += &format!("GU {} {}\n", nom, lignes.len());
        for x in lignes {
            s += x;
            s += "\n";
        }
        s += "AG\n";
    }
    std::fs::write(chemin, s)
}

/// [(nom, lignes)] d'un ADN version 3
fn sections_adn(l: &[&str], chemin: &str) -> Result<Vec<(String, Vec<String>)>, String> {
    let mut out = Vec::new();
    let mut i = 1;
    while i < l.len() && !l[i].is_empty() {
        let tete: Vec<&str> = l[i].split(' ').collect();
        if tete.len() != 3 || tete[0] != "GU" {
            return Err(format!("{} : borne d'intron attendue (GU), ligne {}", chemin, i + 1));
        }
        let n: usize = tete[2].parse().map_err(|_| format!("{} : longueur d'intron illisible, ligne {}", chemin, i + 1))?;
        if i + 1 + n >= l.len() || l[i + 1 + n] != "AG" {
            return Err(format!("{} : la section « {} » ne finit pas par AG", chemin, tete[1]));
        }
        out.push((tete[1].to_string(), l[i + 1..i + 1 + n].iter().map(|x| x.to_string()).collect()));
        i += n + 2;
    }
    Ok(out)
}

const CONNUES: [&str; 4] = ["mots", "molecules", "ombres", "neutrons"];

pub fn lire_adn(chemin: &str) -> Result<(Vec<u128>, Vec<Molecule>, Temoins), String> {
    let texte = std::fs::read_to_string(chemin).map_err(|e| format!("{} : {}", chemin, e))?;
    adn_depuis_texte(&texte, chemin)
}

pub fn adn_depuis_texte(texte: &str, chemin: &str) -> Result<(Vec<u128>, Vec<Molecule>, Temoins), String> {
    // les fins de ligne de Windows (\r\n) sont acceptées : un ADN recopié ou écrit sous Windows reste lisible
    let texte = texte.replace("\r\n", "\n");
    let l: Vec<&str> = texte.split('\n').collect();
    let (mots_l, mols_l, ombres_l, neutrons_l, introns): (String, Vec<String>, Vec<String>, String, Vec<(String, Vec<String>)>) =
        if l.len() >= 5 && l[0] == "VTXADN02" {
            (l[1].into(), l[2].split('\t').filter(|x| !x.is_empty()).map(|x| format!("{}|0", x)).collect(),
             l[3].split(';').filter(|x| !x.is_empty()).map(|x| x.to_string()).collect(), l[4].into(), vec![])
        } else if !l.is_empty() && l[0] == "VTXADN03" {
            let tout = sections_adn(&l, chemin)?;
            let sec = |n: &str| tout.iter().find(|(k, _)| k == n).map(|(_, v)| v.clone());
            let manque = || format!("{} : une section manque", chemin);
            (sec("mots").ok_or_else(manque)?.first().cloned().unwrap_or_default(), sec("molecules").ok_or_else(manque)?,
             sec("ombres").ok_or_else(manque)?, sec("neutrons").ok_or_else(manque)?.first().cloned().unwrap_or_default(),
             tout.iter().filter(|(k, _)| !CONNUES.contains(&k.as_str())).cloned().collect())
        } else {
            return Err(format!("{} : ce n'est pas un ADN de vtx", chemin));
        };
    let nb = |x: &str| x.parse::<u128>().map_err(|_| format!("{} : nombre illisible « {} »", chemin, x));
    let mots: Vec<u128> = mots_l.split(',').filter(|x| !x.is_empty()).map(nb).collect::<Result<_, _>>()?;
    let mut mols = Vec::new();
    let mut sigs = Vec::new();
    for x in &mols_l {
        let c: Vec<&str> = x.split('|').collect();
        if c.len() != 6 {
            return Err(format!("{} : molécule illisible", chemin));
        }
        mols.push(Molecule { debut: nb(c[1])? as usize, fin: nb(c[2])? as usize, frontiere: c[3] == "1", isotope: c[5] == "1" });
        sigs.push(nb(c[4])? as u64);
    }
    let ombres: Vec<Vec<u128>> = ombres_l.iter()
        .map(|o| o.split(',').map(nb).collect::<Result<_, _>>()).collect::<Result<_, _>>()?;
    let mut neutrons = BTreeMap::new();
    for x in neutrons_l.split(',').filter(|x| !x.is_empty()) {
        let (a, b) = x.split_once(':').ok_or(format!("{} : neutron illisible", chemin))?;
        neutrons.insert(nb(a)? as usize, nb(b)? as u8);
    }
    // un ADN dont les tables ne collent pas aux mots (tronqué, mal recopié) n'est pas lu
    if mols.iter().any(|m| m.fin > mots.len() || m.debut >= m.fin) || ombres.len() != nb_colonnes(mots.len())
        || ombres.iter().any(|o| o.len() != OMBRE) {
        return Err(format!("{} : les témoins ne correspondent pas aux mots", chemin));
    }
    Ok((mots, mols, Temoins { signatures: sigs, ombres, neutrons, introns }))
}

/// ranger : les mots d'un programme -> son ADN (les molécules et les témoins)
pub fn ranger(mots: &[u128]) -> (Vec<Molecule>, Temoins) {
    let mols = decouper(mots);
    let t = temoins(mots, &mols);
    (mols, t)
}

/// ranger avec les introns : les isotopes lourds (réaction, place de son premier mot) donnent des neutrons à leur
/// molécule ; le texte du programme est gardé, pour la rétrotranscription (recompilé, il doit redonner les mots)
pub fn ranger_texte(mots: &[u128], isotopes: &[(String, usize)], source: &str) -> (Vec<Molecule>, Temoins) {
    let mut mols = decouper(mots);
    let mut iso: Vec<(String, usize)> = isotopes.to_vec();
    iso.sort_by_key(|x| x.1);
    for (_, a) in &iso {
        for m in mols.iter_mut() {
            if m.debut <= *a && *a < m.fin {
                m.isotope = true;
            }
        }
    }
    let mut t = temoins(mots, &mols);
    if !iso.is_empty() {
        t.introns.push(("isotopes".into(), iso.iter().map(|(n, a)| format!("{}|{}", n, a)).collect()));
    }
    t.introns.push(("source".into(), source.replace("\r\n", "\n").split('\n').map(|x| x.to_string()).collect()));
    (mols, t)
}

/// transcrire : lit l'ADN, le vérifie et le répare ; rend les mots (l'ARN) et l'état. Un ADN réparé est réécrit ; un ADN
/// variable n'est pas transcrit (Err), il est gardé tel qu'il a été lu.
pub fn transcrire(chemin: &str, bavard: bool) -> Result<(Vec<u128>, u8, Temoins), String> {
    let (mut mots, mols, mut t) = lire_adn(chemin)?;
    let (etat, rapport) = lire(&mut mots, &mols, &mut t);
    if bavard || etat != VRAI {
        for (j, e, quoi) in &rapport {
            if *e != VRAI {
                eprintln!("  m{} : {}, {}", mols[*j].debut, nom_etat(*e), quoi);
            }
        }
        eprintln!("l'ADN : {}", nom_etat(etat));
    }
    if etat == VARIABLE {
        return Err("l'ADN est abîmé au-delà de ses témoins : rien n'est transcrit, il est gardé tel qu'il a été lu".into());
    }
    if etat == FAUX {
        ecrire_adn(chemin, &mots, &mols, &t).map_err(|e| e.to_string())?;
        eprintln!("l'ADN réparé est réécrit");
    }
    Ok((mots, etat, t))
}

// ------------------------------------------------------------------------------------------------ la patrouille
/// La patrouille : pendant que le programme tourne, elle relit le code en mémoire contre ses témoins, comme les
/// enzymes qui parcourent l'ADN d'une cellule. Une empreinte de 64 bits par colonne (prise sur les mots vérifiés au
/// lancement) dit vite si une colonne a changé ; alors seulement la lecture complète (l'ombre, les neutrons, les
/// signatures) répare, et la triangulation confirme. Les isotopes lourds sont relus à chaque entrée (un point de
/// contrôle, comme avant la division d'une cellule) et une fois sur deux à chaque tic. Une molécule abîmée au-delà de
/// ses témoins arrête la machine : l'apoptose, plutôt que lancer du code abîmé.
pub struct Patrouille {
    pub mols: Vec<Molecule>,
    pub t: Temoins,
    n: usize,
    empreintes: Vec<u64>,
    cols_lourdes: Vec<usize>,
    prochaine: usize,
    prochaine_lourde: usize,
    tics: u64,
    /// le pas de la dernière relecture propre de chaque colonne : une avarie trouvée a pu servir depuis
    propre: Vec<u64>,
    /// les fonctions surveillées (isotopes lourds), en demi-instructions : (entrée, entrée de la suivante, l'empreinte
    /// de ses mots, prise au lancement sur les mots vérifiés ; une fonction peut finir dans le premier mot de la suivante)
    zones: Vec<(usize, usize, u64)>,
    pub relues: u64,
    pub reparations: Vec<String>,
}

impl Patrouille {
    pub fn nouvelle(mots: &[u128], mols: Vec<Molecule>, t: Temoins) -> Patrouille {
        let n = mots.len();
        let nc = nb_colonnes(n);
        let empreintes: Vec<u64> = (0..nc).map(|k| empreinte_colonne(&places_colonne(n, k), &|i| mots[i])).collect();
        let mut cols_lourdes: Vec<usize> = mols.iter().filter(|m| m.isotope).flat_map(|m| (m.debut..m.fin).map(move |i| i % nc)).collect();
        cols_lourdes.sort();
        cols_lourdes.dedup();
        let propre = vec![0; empreintes.len()];
        // les entrées des fonctions (les cibles des CALL), en demi-instructions
        let mut cibles: Vec<usize> = demis(mots).iter().filter(|&&(h, lit)| !lit && (h >> 48) == OP_CALL)
            .map(|&(h, _)| (h & 0xFFFF_FFFF) as usize).filter(|&d| d / 2 < n).collect();
        cibles.sort();
        cibles.dedup();
        let mut zones = Vec::new();
        for m in mols.iter().filter(|m| m.isotope) {
            if let Some(k) = cibles.iter().position(|&c| c / 2 == m.debut) {
                let (a, b) = (cibles[k], cibles.get(k + 1).cloned().unwrap_or(2 * n));
                zones.push((a, b, signature(&mots[a / 2..=(b - 1) / 2])));
            }
        }
        Patrouille { mols, t, n, empreintes, cols_lourdes, prochaine: 0, prochaine_lourde: 0, tics: 0, propre, zones, relues: 0,
                     reparations: vec![] }
    }

    /// les fonctions surveillées à l'entrée et à la sortie (les isotopes lourds), en demi-instructions
    pub fn controles(&self) -> Vec<(usize, usize)> {
        self.zones.iter().map(|z| (z.0, z.1)).collect()
    }

    fn colonne_changee(&mut self, k: usize, lire: &dyn Fn(usize) -> u128, pas: u64) -> bool {
        self.relues += 1;
        let change = empreinte_colonne(&places_colonne(self.n, k), lire) != self.empreintes[k];
        if !change {
            self.propre[k] = pas;
        }
        change
    }

    /// un tic : une colonne relue (une lourde, puis une de l'ensemble, tour à tour) ; rend vrai si elle a changé
    pub fn tic(&mut self, lire: &dyn Fn(usize) -> u128, pas: u64) -> bool {
        self.tics += 1;
        let k = if self.tics % 2 == 0 && !self.cols_lourdes.is_empty() {
            self.prochaine_lourde = (self.prochaine_lourde + 1) % self.cols_lourdes.len();
            self.cols_lourdes[self.prochaine_lourde]
        } else {
            self.prochaine = (self.prochaine + 1) % self.empreintes.len();
            self.prochaine
        };
        self.colonne_changee(k, lire, pas)
    }

    /// une ronde entière : vrai si une colonne a changé
    pub fn ronde(&mut self, lire: &dyn Fn(usize) -> u128, pas: u64) -> bool {
        let mut change = false;
        for k in 0..self.empreintes.len() {
            change |= self.colonne_changee(k, lire, pas);
        }
        change
    }

    /// la fonction qui commence à la demi-instruction `entree` : ses molécules relues ; vrai si l'une a changé
    fn molecule_changee(&mut self, entree: usize, lire: &dyn Fn(usize) -> u128) -> Option<bool> {
        let &(a, b, sig) = self.zones.iter().find(|z| z.0 == entree)?;
        self.relues += 1;
        let mots: Vec<u128> = (a / 2..=(b - 1) / 2).map(lire).collect();
        Some(signature(&mots) != sig)
    }

    /// l'entrée d'une molécule surveillée (sa première place) : sa signature relue ; vrai si elle a changé (elle est
    /// alors réparée avant de servir)
    pub fn entree(&mut self, debut: usize, lire: &dyn Fn(usize) -> u128) -> bool {
        self.molecule_changee(debut, lire).unwrap_or(false)
    }

    /// la sortie d'une molécule surveillée : relue à l'entrée, elle était saine ; abîmée maintenant, c'est pendant
    /// qu'elle servait : son résultat n'est pas sûr, la machine s'arrête (l'apoptose) plutôt que de le rendre
    pub fn sortie(&mut self, debut: usize, lire: &dyn Fn(usize) -> u128, pas: u64) -> Result<(), String> {
        if self.molecule_changee(debut, lire).unwrap_or(false) {
            return Err(format!("apoptose au pas {} : la molécule m{} (un isotope lourd) s'est abîmée pendant qu'elle servait ; \
                                son résultat n'est pas sûr, la machine s'arrête plutôt que de le rendre", pas, debut / 2));
        }
        Ok(())
    }

    /// la réparation : tout le code relu contre ses témoins ; rend les mots à réécrire, ou l'apoptose (Err)
    pub fn reparer(&mut self, lire: &dyn Fn(usize) -> u128, pas: u64) -> Result<Vec<(usize, u128)>, String> {
        let avant: Vec<u128> = (0..self.n).map(lire).collect();
        let mut mots = avant.clone();
        let mut t = self.t.clone();
        let (etat, rapport) = self::lire(&mut mots, &self.mols, &mut t);
        if etat == VARIABLE {
            let m = rapport.iter().find(|(_, e, _)| *e == VARIABLE).map(|(j, _, q)| format!("m{} ({})", self.mols[*j].debut, q))
                .unwrap_or_default();
            return Err(format!("apoptose au pas {} : la molécule {} est abîmée au-delà de ses témoins ; la machine s'arrête \
                                plutôt que de lancer du code abîmé", pas, m));
        }
        let changes: Vec<(usize, u128)> = (0..self.n).filter(|&i| mots[i] != avant[i]).map(|i| (i, mots[i])).collect();
        let nc = self.empreintes.len();
        for (j, e, quoi) in &rapport {
            if *e != VRAI {
                let m = &self.mols[*j];
                // depuis quand elle a pu servir abîmée : la plus ancienne dernière relecture propre de ses colonnes
                // (un isotope lourd, relu à chaque entrée, n'a pas servi abîmé)
                let depuis = (m.debut..m.fin).filter(|i| changes.iter().any(|c| c.0 == *i)).map(|i| self.propre[i % nc]).min();
                let note = match (m.isotope, depuis) {
                    (true, _) => " ; isotope lourd, relu à son entrée : il n'a pas servi abîmé".to_string(),
                    (false, Some(0)) => " ; elle a pu servir abîmée depuis le lancement (pas encore relue)".to_string(),
                    (false, Some(d)) => format!(" ; elle a pu servir abîmée depuis le pas {} (sa dernière relecture propre)", d),
                    _ => String::new(),
                };
                self.reparations.push(format!("pas {} : m{} {}, {}{}", pas, m.debut, nom_etat(*e), quoi, note));
            }
        }
        self.t = t;
        for z in self.zones.iter_mut() {
            z.2 = signature(&mots[z.0 / 2..=(z.1 - 1) / 2]);
        }
        for k in 0..nc {
            self.empreintes[k] = empreinte_colonne(&places_colonne(self.n, k), &|i| mots[i]);
        }
        Ok(changes)
    }
}

fn empreinte_colonne(places: &[usize], lire: &dyn Fn(usize) -> u128) -> u64 {
    let mut h = melanger(0x5041_5452_4F55_494C ^ places.len() as u64);      // « PATROUIL »
    for &i in places {
        let w = lire(i);
        h = melanger(h ^ (w as u64));
        h = melanger(h ^ ((w >> 64) as u64));
    }
    h
}

// ------------------------------------------------------------------------------------------------ l'ARN
/// L'épissage alternatif : un même ADN donne plusieurs ARN, selon ce qu'on garde des introns.
///   rapide  : les mots seuls ;
///   sur     : les mots et leurs témoins (molécules, ombre, neutrons) : la patrouille veille pendant l'exécution ;
///   memoire : les mots et l'épigénome (les souvenirs appris) ;
///   complet : les deux.
/// L'ARN porte une coiffe (la signature de ses mots, vérifiée avant de lancer : un ARN dont la coiffe ne reconnaît pas
/// les mots est dégradé, jamais lancé) et une queue (le nombre de lancements qui lui restent : à chaque lancement elle
/// raccourcit ; usée, l'ARN est refait depuis l'ADN, qui est relu et réparé au passage).
pub const ISOFORMES: [&str; 4] = ["rapide", "sur", "memoire", "complet"];
pub const QUEUE: u32 = 64;

pub struct Arn {
    pub mots: Vec<u128>,
    pub isoforme: String,
    pub queue: u32,
    pub temoins: Option<(Vec<Molecule>, Temoins)>,
    pub epigenome: Option<Vec<String>>,
}

pub fn ecrire_arn(chemin: &str, mots: &[u128], mols: &[Molecule], t: &Temoins, isoforme: &str, queue: u32)
                  -> Result<(), String> {
    if !ISOFORMES.contains(&isoforme) {
        return Err(format!("isoforme inconnue « {} » (rapide, sur, memoire, complet)", isoforme));
    }
    let mut sections: Vec<(String, Vec<String>)> = vec![
        ("coiffe".into(), vec![format!("{}|{}", signature(mots), isoforme)]),
        ("queue".into(), vec![queue.to_string()]),
        ("mots".into(), vec![mots.iter().map(|w| w.to_string()).collect::<Vec<_>>().join(",")]),
    ];
    if isoforme == "sur" || isoforme == "complet" {
        sections.push(("molecules".into(), mols.iter().zip(t.signatures.iter())
            .map(|(m, sg)| format!("m{}|{}|{}|{}|{}|{}", m.debut, m.debut, m.fin, m.frontiere as u8, sg, m.isotope as u8)).collect()));
        sections.push(("ombres".into(), t.ombres.iter().map(|o| o.iter().map(|w| w.to_string()).collect::<Vec<_>>().join(",")).collect()));
        sections.push(("neutrons".into(), vec![t.neutrons.iter().map(|(i, v)| format!("{}:{}", i, v)).collect::<Vec<_>>().join(",")]));
    }
    if isoforme == "memoire" || isoforme == "complet" {
        if let Some(e) = t.intron("epigenome") {
            sections.push(("epigenome".into(), e.clone()));
        }
    }
    let mut s = String::from("VTXARN01\n");
    for (nom, lignes) in &sections {
        s += &format!("GU {} {}\n", nom, lignes.len());
        for x in lignes {
            s += x;
            s += "\n";
        }
        s += "AG\n";
    }
    std::fs::write(chemin, s).map_err(|e| format!("{} : {}", chemin, e))
}

pub fn lire_arn(chemin: &str) -> Result<Arn, String> {
    let texte = std::fs::read_to_string(chemin).map_err(|e| format!("{} : {}", chemin, e))?.replace("\r\n", "\n");
    let l: Vec<&str> = texte.split('\n').collect();
    if l.is_empty() || l[0] != "VTXARN01" {
        return Err(format!("{} : ce n'est pas un ARN de vtx", chemin));
    }
    let tout = sections_adn(&l, chemin)?;
    let sec = |n: &str| tout.iter().find(|(k, _)| k == n).map(|(_, v)| v.clone());
    let degrade = || format!("{} : l'ARN est dégradé (sans coiffe, sans queue ou sans mots) : retranscrivez-le depuis l'ADN", chemin);
    let coiffe = sec("coiffe").and_then(|v| v.first().cloned()).ok_or_else(degrade)?;
    let queue: u32 = sec("queue").and_then(|v| v.first().and_then(|x| x.parse().ok())).ok_or_else(degrade)?;
    let mots: Vec<u128> = sec("mots").and_then(|v| v.first().cloned()).ok_or_else(degrade)?
        .split(',').filter(|x| !x.is_empty()).map(|x| x.parse::<u128>().map_err(|_| degrade())).collect::<Result<_, _>>()?;
    let (sig, isoforme) = coiffe.split_once('|').ok_or_else(degrade)?;
    if sig != signature(&mots).to_string() {
        return Err(format!("{} : la coiffe ne reconnaît pas les mots : l'ARN est dégradé, il n'est pas lancé ; \
                            retranscrivez-le depuis l'ADN", chemin));
    }
    let temoins = match (sec("molecules"), sec("ombres"), sec("neutrons")) {
        (Some(ml), Some(ol), Some(nl)) => {
            // les témoins de l'ARN sûr : lus comme ceux de l'ADN
            let mut faux = String::from("VTXADN03\n");
            for (nom, lignes) in [("mots", vec![mots.iter().map(|w| w.to_string()).collect::<Vec<_>>().join(",")]),
                                  ("molecules", ml), ("ombres", ol), ("neutrons", nl)] {
                faux += &format!("GU {} {}\n{}\nAG\n", nom, lignes.len(), lignes.join("\n"));
            }
            let (_, mols, t) = adn_depuis_texte(&faux, chemin)?;
            Some((mols, t))
        }
        _ => None,
    };
    Ok(Arn { mots, isoforme: isoforme.to_string(), queue, temoins, epigenome: sec("epigenome") })
}

/// la queue raccourcie d'un lancement (l'ARN réécrit tel quel, sa queue moins un)
pub fn raccourcir_queue(chemin: &str) -> Result<u32, String> {
    let texte = std::fs::read_to_string(chemin).map_err(|e| format!("{} : {}", chemin, e))?;
    let i = texte.find("GU queue 1\n").ok_or_else(|| format!("{} : sans queue", chemin))? + "GU queue 1\n".len();
    let j = i + texte[i..].find('\n').ok_or_else(|| format!("{} : queue illisible", chemin))?;
    let q: u32 = texte[i..j].trim().parse().map_err(|_| format!("{} : queue illisible", chemin))?;
    let q2 = q.saturating_sub(1);
    let neuf = format!("{}{}{}", &texte[..i], q2, &texte[j..]);
    std::fs::write(chemin, neuf).map_err(|e| format!("{} : {}", chemin, e))?;
    Ok(q2)
}
