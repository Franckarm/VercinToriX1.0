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
}

#[derive(Clone, Debug, PartialEq)]
pub struct Temoins {
    pub signatures: Vec<u64>,
    pub ombres: Vec<Vec<u128>>,
    pub neutrons: BTreeMap<usize, u8>,
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
        mols.push(Molecule { debut: a, fin: b, frontiere });
    }
    mols
}

pub fn temoins(mots: &[u128], mols: &[Molecule]) -> Temoins {
    let mut neutrons = BTreeMap::new();
    for m in mols {
        if m.frontiere {
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
    }
}

pub fn place_des_temoins(mots: &[u128], mols: &[Molecule]) -> usize {
    let o: usize = mols.iter().filter(|m| m.frontiere).map(|m| m.fin - m.debut).sum();
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
        } else if (m.frontiere && changes.iter().all(|i| par_neutrons.contains(i) && t.neutrons.get(i) == Some(&crc8(mots[*i]))))
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
pub fn ecrire_adn(chemin: &str, mots: &[u128], mols: &[Molecule], t: &Temoins) -> std::io::Result<()> {
    let mut s = String::from("VTXADN02\n");
    s += &mots.iter().map(|w| w.to_string()).collect::<Vec<_>>().join(",");
    s += "\n";
    s += &mols.iter().zip(t.signatures.iter())
        .map(|(m, sg)| format!("m{}|{}|{}|{}|{}", m.debut, m.debut, m.fin, m.frontiere as u8, sg)).collect::<Vec<_>>().join("\t");
    s += "\n";
    s += &t.ombres.iter().map(|o| o.iter().map(|w| w.to_string()).collect::<Vec<_>>().join(",")).collect::<Vec<_>>().join(";");
    s += "\n";
    s += &t.neutrons.iter().map(|(i, v)| format!("{}:{}", i, v)).collect::<Vec<_>>().join(",");
    s += "\n";
    std::fs::write(chemin, s)
}

pub fn lire_adn(chemin: &str) -> Result<(Vec<u128>, Vec<Molecule>, Temoins), String> {
    let texte = std::fs::read_to_string(chemin).map_err(|e| format!("{} : {}", chemin, e))?;
    // les fins de ligne de Windows (\r\n) sont acceptées : un ADN recopié ou écrit sous Windows reste lisible
    let l: Vec<&str> = texte.split('\n').map(|x| x.trim_end_matches('\r')).collect();
    if l.len() < 5 || l[0] != "VTXADN02" {
        return Err(format!("{} : ce n'est pas un ADN de vtx", chemin));
    }
    let nb = |x: &str| x.parse::<u128>().map_err(|_| format!("{} : nombre illisible « {} »", chemin, x));
    let mots: Vec<u128> = l[1].split(',').filter(|x| !x.is_empty()).map(nb).collect::<Result<_, _>>()?;
    let mut mols = Vec::new();
    let mut sigs = Vec::new();
    for x in l[2].split('\t').filter(|x| !x.is_empty()) {
        let c: Vec<&str> = x.split('|').collect();
        if c.len() != 5 {
            return Err(format!("{} : molécule illisible", chemin));
        }
        mols.push(Molecule { debut: nb(c[1])? as usize, fin: nb(c[2])? as usize, frontiere: c[3] == "1" });
        sigs.push(nb(c[4])? as u64);
    }
    let ombres: Vec<Vec<u128>> = l[3].split(';').filter(|x| !x.is_empty())
        .map(|o| o.split(',').map(nb).collect::<Result<_, _>>()).collect::<Result<_, _>>()?;
    let mut neutrons = BTreeMap::new();
    for x in l[4].split(',').filter(|x| !x.is_empty()) {
        let (a, b) = x.split_once(':').ok_or(format!("{} : neutron illisible", chemin))?;
        neutrons.insert(nb(a)? as usize, nb(b)? as u8);
    }
    // un ADN dont les tables ne collent pas aux mots (tronqué, mal recopié) n'est pas lu
    if mols.iter().any(|m| m.fin > mots.len() || m.debut >= m.fin) || ombres.len() != nb_colonnes(mots.len())
        || ombres.iter().any(|o| o.len() != OMBRE) {
        return Err(format!("{} : les témoins ne correspondent pas aux mots", chemin));
    }
    Ok((mots, mols, Temoins { signatures: sigs, ombres, neutrons }))
}

/// ranger : les mots d'un programme -> son ADN (les molécules et les témoins)
pub fn ranger(mots: &[u128]) -> (Vec<Molecule>, Temoins) {
    let mols = decouper(mots);
    let t = temoins(mots, &mols);
    (mols, t)
}

/// transcrire : lit l'ADN, le vérifie et le répare ; rend les mots (l'ARN) et l'état. Un ADN réparé est réécrit ; un ADN
/// variable n'est pas transcrit (Err), il est gardé tel qu'il a été lu.
pub fn transcrire(chemin: &str, bavard: bool) -> Result<(Vec<u128>, u8), String> {
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
    Ok((mots, etat))
}
