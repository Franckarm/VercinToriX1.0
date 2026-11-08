// Le débogueur de Lugus, par les noms : vtxc128 écrit code.sym en pas à pas (une ligne par fonction : son nom, la place
// de son premier mot, sa ligne ; une par variable : son nom, sa place dans le cadre, sa sorte). D'ici, l'atelier remonte
// la pile des appels (le cadre R13 garde l'ancien cadre en +0 et l'adresse de retour en +1) et écrit chaque variable
// comme le programme l'entend : un texte entre guillemets, un tableau entre crochets, un flottant en décimal, un
// logique par son nom de Belnap.
use super::spu128::Spu128;

#[derive(Clone, Debug)]
pub struct Variable {
    pub nom: String,
    pub place: i128,  // dans le cadre : -1, -2… les locales ; +2, +3… les paramètres
    pub sorte: String, // e i f s w x q p t tt tf r<n>
}

#[derive(Clone, Debug)]
pub struct Fonction {
    pub nom: String,
    pub debut: u128, // la place de son premier mot, en demi-mots (le pc de Lugus)
    #[allow(dead_code)]
    pub ligne: u32,
    pub prelude: bool,
    pub variables: Vec<Variable>,
}

#[derive(Clone, Debug, Default)]
pub struct Symboles {
    pub fonctions: Vec<Fonction>, // rangées par place
}

/// Une étape de la pile des appels : la fonction, son cadre, et où l'on en est (le pc, ou l'adresse de retour).
#[derive(Clone, Debug)]
pub struct Etape {
    pub fonction: usize,
    pub cadre: u128,
    pub pc: u128,
}

const PLAFOND: usize = 12; // cases montrées d'un tableau, caractères d'un texte (x 5)

impl Symboles {
    pub fn lire(t: &str) -> Symboles {
        let mut f: Vec<Fonction> = Vec::new();
        for l in t.lines() {
            let p: Vec<&str> = l.trim_end_matches('\r').split('|').collect();
            match p.first() {
                Some(&"F") if p.len() >= 5 => f.push(Fonction {
                    nom: p[1].to_string(),
                    debut: p[2].parse().unwrap_or(0),
                    ligne: p[3].parse().unwrap_or(0),
                    prelude: p[4] == "p",
                    variables: vec![],
                }),
                Some(&"V") if p.len() >= 4 => {
                    if let Some(der) = f.last_mut() {
                        der.variables.push(Variable { nom: p[1].to_string(), place: p[2].parse().unwrap_or(0), sorte: p[3].to_string() });
                    }
                }
                _ => {}
            }
        }
        for x in f.iter_mut() {
            // les paramètres d'abord (le premier est le plus loin du cadre), puis les locales dans l'ordre du texte
            x.variables.sort_by_key(|v| if v.place > 0 { (0, -v.place) } else { (1, -v.place) });
        }
        f.sort_by_key(|x| x.debut);
        Symboles { fonctions: f }
    }

    /// la fonction dont le code contient le pc : la dernière qui commence avant lui
    pub fn fonction_de(&self, pc: u128) -> Option<usize> {
        let k = self.fonctions.partition_point(|f| f.debut <= pc);
        if k == 0 { None } else { Some(k - 1) }
    }

    /// la pile des appels, de la fonction en cours jusqu'au principal
    pub fn pile(&self, s: &Spu128) -> Vec<Etape> {
        let mut e = Vec::new();
        let (mut cadre, mut pc) = (s.r[13], s.pc as u128);
        while e.len() < 64 {
            let f = match self.fonction_de(pc) {
                Some(f) => f,
                None => break,
            };
            // au tout début d'une fonction (avant « pousser R13 »), le cadre est encore celui de l'appelant
            e.push(Etape { fonction: f, cadre, pc });
            if cadre == 0 || cadre > super::spu128::PILE {
                break;
            }
            let ancien = s.regarder(cadre);
            let retour = s.regarder(cadre + 1);
            if ancien <= cadre || retour == 0 {
                break;
            }
            cadre = ancien;
            pc = retour;
        }
        e
    }

    /// la vue du débogueur : la pile des appels, puis les variables de chaque étape (la plus récente d'abord)
    pub fn vue(&self, s: &Spu128, ligne_de: &dyn Fn(u128) -> Option<usize>) -> String {
        let mut t = String::new();
        let pile = self.pile(s);
        let siennes: Vec<&Etape> = pile.iter().filter(|e| !self.fonctions[e.fonction].prelude).collect();
        if siennes.is_empty() {
            return t;
        }
        t.push_str("la pile des appels (la fonction en cours d'abord) :\n");
        for (k, e) in pile.iter().enumerate() {
            let f = &self.fonctions[e.fonction];
            let ou = match ligne_de(e.pc) {
                Some(l) => format!(", ligne {}", l + 1),
                None => String::new(),
            };
            t.push_str(&format!("  {} {}{}{}\n", if k == 0 { "▶" } else { "·" }, f.nom, if f.prelude { " (prélude)" } else { "" }, ou));
        }
        for (k, e) in siennes.iter().enumerate() {
            let f = &self.fonctions[e.fonction];
            if f.variables.is_empty() {
                continue;
            }
            t.push_str(&format!("\n{} {} :\n", if k == 0 { "les variables de" } else { "et dans" }, f.nom));
            let large = f.variables.iter().map(|v| v.nom.chars().count()).max().unwrap_or(0).min(18);
            for v in &f.variables {
                let brut = s.regarder((e.cadre as i128 + v.place) as u128);
                t.push_str(&format!("  {:<large$} = {}\n", v.nom, valeur(s, &v.sorte, brut), large = large));
            }
        }
        t
    }
}

fn signe(v: u128) -> String {
    let w = v as u64 as i64;
    if v >> 64 == 0 && w < 0 && w > -(1i64 << 40) {
        w.to_string()
    } else if (v as i128) < 0 && (v as i128) > -(1i128 << 40) {
        (v as i128).to_string()
    } else {
        v.to_string()
    }
}

fn flottant(bits: u128, taille: u32) -> String {
    use super::qflot128::{Q128, Q32, Q64};
    let q = match taille { 32 => Q32, 64 => Q64, _ => Q128 };
    let v = bits & q.masque();
    match q.etat(v) {
        0 => return "inconnu (flottant)".into(),
        3 => return "variable (flottant)".into(),
        _ => {}
    }
    let i = q.vers_ieee(v);
    let d = match taille {
        32 => f32::from_bits(i as u32) as f64,
        64 => f64::from_bits(i as u64),
        _ => {
            // binary128 vers f64 : le signe, l'exposant de 15 bits, les 52 premiers bits de la mantisse
            let s = (i >> 127) as u64;
            let e = ((i >> 112) & 0x7FFF) as i64;
            let m = ((i >> 60) & ((1u128 << 52) - 1)) as u64;
            if e == 0 {
                0.0
            } else if e == 0x7FFF {
                if m == 0 { if s == 1 { f64::NEG_INFINITY } else { f64::INFINITY } } else { f64::NAN }
            } else {
                let e2 = e - 16383 + 1023;
                if e2 >= 2047 { if s == 1 { f64::NEG_INFINITY } else { f64::INFINITY } } else if e2 <= 0 { 0.0 } else {
                    f64::from_bits((s << 63) | ((e2 as u64) << 52) | m)
                }
            }
        }
    };
    let mut t = format!("{}", d);
    if !t.contains('.') && !t.contains('e') && !t.contains("inf") && !t.contains("NaN") {
        t.push_str(".0");
    }
    t
}

fn belnap(v: u128) -> String {
    if v <= 3 { ["inconnu", "faux", "vrai", "variable"][v as usize].into() } else { format!("{} (pas un logique)", v) }
}

/// le texte à l'adresse a : sa longueur, puis un caractère par mot
fn texte(s: &Spu128, a: u128) -> String {
    if a == 0 {
        return "(pas encore de texte)".into();
    }
    let n = s.regarder(a);
    if n > 1_000_000 {
        return format!("? (adresse {:#X} : pas un texte)", a);
    }
    let mut t = String::from("\"");
    for i in 0..(n as usize).min(PLAFOND * 5) {
        let c = s.regarder(a + 1 + i as u128);
        t.push(char::from_u32((c & 0x1F_FFFF) as u32).unwrap_or('?'));
    }
    t.push('"');
    if n as usize > PLAFOND * 5 {
        t.push_str(&format!("… ({} caractères)", n));
    }
    t
}

/// un tableau dynamique : la poignée h (étage 3) garde la longueur, la capacité, l'indice des données (étage 3)
fn cases(s: &Spu128, h: u128) -> Option<(usize, Vec<u128>)> {
    if h >> 64 != 0 || h >> 62 != 3 {
        return None;
    }
    let e3 = 3u128 << 62;
    let p = h & 0xFF_FFFF;
    let (n, cap, d) = (s.regarder(e3 | p), s.regarder(e3 | (p + 1)), s.regarder(e3 | (p + 2)));
    if n > cap || cap > 1 << 24 || d > 0xFF_FFFF {
        return None;
    }
    let v = (0..(n as usize).min(PLAFOND)).map(|i| s.regarder(e3 | (d + i as u128))).collect();
    Some((n as usize, v))
}

/// une adresse de texte plausible : dans le tas ou avec le code, une longueur raisonnable, des caractères
fn est_texte(s: &Spu128, a: u128) -> bool {
    if a >> 64 != 0 || (a >> 62 != 3 && a >> 62 != 0) || a == 0 {
        return false;
    }
    let n = s.regarder(a);
    n < 100_000 && (0..(n as usize).min(8)).all(|i| {
        let c = s.regarder(a + 1 + i as u128);
        c > 0 && c < 0x11_0000
    })
}

fn liste(n: usize, v: Vec<String>) -> String {
    let mut t = format!("[{}", v.join(", "));
    if n > v.len() {
        t.push_str(&format!(", … ({} cases)", n));
    }
    t.push(']');
    t
}

/// la valeur d'une variable, écrite selon sa sorte
pub fn valeur(s: &Spu128, sorte: &str, v: u128) -> String {
    match sorte {
        "t" => texte(s, v),
        "tt" => match cases(s, v) {
            Some((n, c)) => liste(n, c.into_iter().map(|a| texte(s, a)).collect()),
            None => format!("{} (pas encore un tableau)", signe(v)),
        },
        "tf" => match cases(s, v) {
            Some((n, c)) => liste(n, c.into_iter().map(|b| flottant(b, 64)).collect()),
            None => format!("{} (pas encore un tableau)", signe(v)),
        },
        "f" => flottant(v, 64),
        "s" => flottant(v, 32),
        "x" => flottant(v, 128),
        "q" => belnap(v),
        "p" => format!("point #{:08X}_{:08X}_{:08X}_{:08X}", v >> 96, (v >> 64) & 0xFFFF_FFFF, (v >> 32) & 0xFFFF_FFFF, v & 0xFFFF_FFFF),
        r if r.starts_with('r') => if v == 0 { "nul".into() } else { format!("structure à l'adresse {:#X}", v) },
        _ => {
            // un entier, ou la poignée d'un tableau (le texte ne le dit pas : on regarde ; un entier de l'étage 3, plus
            // grand que 2^63, serait rare) ; un tableau dont chaque case est un texte du tas est un tableau de textes
            match cases(s, v) {
                Some((n, c)) if !c.is_empty() && c.iter().all(|&a| est_texte(s, a)) => liste(n, c.into_iter().map(|a| texte(s, a)).collect()),
                Some((n, c)) => liste(n, c.into_iter().map(signe).collect()),
                None => signe(v),
            }
        }
    }
}

/// vtx-spu regarder128 PROG.vtx LIGNE [FOIS] : le pas à pas jusqu'à la ligne (la FOIS-ième fois), puis la vue du
/// débogueur ; de quoi vérifier sans l'atelier ce que le panneau montrera.
pub fn essai(args: &[String]) {
    use super::machine128::{compiler128_dbg, dossier_de128, nombres128, PAS_A_PAS128, VTXC128};
    use super::pas64::table_des_lignes;
    if args.len() < 2 {
        eprintln!("vtx-spu regarder128 PROG.vtx LIGNE [FOIS] [ENTRÉES…]");
        std::process::exit(2);
    }
    let sortir = args.iter().any(|a| a == "--sortir");
    let args: Vec<String> = args.iter().filter(|a| *a != "--sortir").cloned().collect();
    let fichier = &args[0];
    let cible: usize = args[1].parse().expect("LIGNE");
    let fois: usize = args.get(2).and_then(|x| x.parse().ok()).unwrap_or(1);
    let entrees: Vec<u128> = args.iter().skip(3).filter_map(|x| x.parse().ok()).collect();
    let source = std::fs::read_to_string(fichier).expect("lecture impossible");
    let (mots, dbg, sym) = compiler128_dbg(&nombres128(VTXC128), &source, &dossier_de128(fichier), PAS_A_PAS128)
        .unwrap_or_else(|e| {
            eprint!("{}", e);
            std::process::exit(1)
        });
    let symboles = Symboles::lire(&sym);
    let debuts = table_des_lignes(dbg.into_iter().map(|x| x as u64));
    let mut s = Spu128::nouveau();
    let d = std::env::temp_dir().join(format!("regarder128-{}", std::process::id()));
    let _ = std::fs::create_dir_all(&d);
    s.dossier = Some(d.clone());
    s.charger(&mots);
    s.entree.extend(entrees);
    let mut vu = 0;
    loop {
        if let Some(&l) = debuts.get(&(s.pc as u64)) {
            if l + 1 == cible {
                vu += 1;
                if vu == fois {
                    break;
                }
            }
        }
        match s.pas_unique().map(|_| !s.arrete) {
            Ok(true) => {}
            Ok(false) => {
                println!("le programme a fini sans passer {} fois par la ligne {}", fois, cible);
                let _ = std::fs::remove_dir_all(&d);
                std::process::exit(1);
            }
            Err(e) => {
                println!("arrêt : {}", e);
                let _ = std::fs::remove_dir_all(&d);
                std::process::exit(1);
            }
        }
    }
    if sortir {
        // Maj+F8 de l'atelier : jusqu'au retour dans l'appelante (son cadre revient), puis le retour lui-même
        let cadre = s.r[13];
        loop {
            if s.pas_unique().is_err() || s.arrete {
                println!("le programme a fini avant de sortir de la fonction");
                std::process::exit(1);
            }
            if s.r[13] > cadre {
                let _ = s.pas_unique();
                break;
            }
        }
    }
    let lignes: Vec<(u128, usize)> = {
        let mut v: Vec<(u128, usize)> = debuts.iter().map(|(&a, &l)| (a as u128, l)).collect();
        v.sort();
        v
    };
    let ligne_de = |pc: u128| -> Option<usize> {
        let k = lignes.partition_point(|x| x.0 <= pc);
        if k == 0 { None } else { Some(lignes[k - 1].1) }
    };
    println!("arrêt à la ligne {} ({} fois){}\n{}", cible, fois, if sortir { ", puis sorti de la fonction" } else { "" },
             symboles.vue(&s, &ligne_de));
    let _ = std::fs::remove_dir_all(&d);
}
