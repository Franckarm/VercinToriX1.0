// La provenance (docs/vtx-reactions.md, étape 5) : « pourquoi cette valeur vaut 42 ? », sans Python. vtxc128, compilé avec
// la provenance, range la trace de chaque réaction dans le cube 2 de l'étage 3 et écrit code.prov (les réactions, la place
// de chaque nom dans la trace, ses atomes). Après l'exécution, on remonte les atomes de liaison en liaison jusqu'aux
// constantes et aux entrées, exactement comme « vtx128.py pourquoi » (sans les unités, que vtxc128 ne suit pas encore).
use std::collections::HashSet;

pub struct AtomeP {
    pub nom: String,
    pub ligne: u64,
    pub souvenir: bool,
    pub sorties: Vec<String>,
    pub entrees: Vec<String>,
    pub texte: String,
}

pub struct ReactionP {
    pub nom: String,
    pub ligne: u64,
    pub appels: u64,
    pub resultat: String,
    pub noms: Vec<(String, u64, char)>,
    pub unites: Vec<String>,          // l'unité de chaque nom (vide : aucune), dans l'ordre de noms
    pub atomes: Vec<AtomeP>,
}

fn liste(x: &str) -> Vec<String> {
    x.split(',').filter(|s| !s.is_empty()).map(|s| s.to_string()).collect()
}

/// lit code.prov
pub fn lire(texte: &str) -> Vec<ReactionP> {
    let mut r: Vec<ReactionP> = Vec::new();
    for l in texte.lines() {
        let c: Vec<&str> = l.splitn(7, '|').collect();
        match c[0] {
            "R" if c.len() >= 5 => r.push(ReactionP { nom: c[1].into(), ligne: c[2].parse().unwrap_or(0), appels: c[3].parse().unwrap_or(0),
                                                      resultat: c[4].into(), noms: vec![], unites: vec![], atomes: vec![] }),
            "N" if c.len() >= 4 && !r.is_empty() => {
                let t = c[3].chars().next().unwrap_or('e');
                let der = r.last_mut().unwrap();
                der.noms.push((c[1].into(), c[2].parse().unwrap_or(0), t));
                der.unites.push(c.get(4).map(|u| u.to_string()).unwrap_or_default());
            }
            "A" if c.len() >= 7 && !r.is_empty() => r.last_mut().unwrap().atomes.push(AtomeP {
                nom: c[1].into(), ligne: c[2].parse().unwrap_or(0), souvenir: c[3] == "1", sorties: liste(c[4]),
                entrees: liste(c[5]), texte: c[6].into() }),
            _ => {}
        }
    }
    r
}

/// les cases de la trace, lues une fois dans la mémoire de la machine
pub fn cases(reactions: &[ReactionP], mut lire: impl FnMut(u64) -> u128) -> std::collections::HashMap<u64, u128> {
    let mut m = std::collections::HashMap::new();
    for r in reactions {
        m.insert(r.appels, lire(r.appels));
        for (_, b, _) in &r.noms {
            for k in 0..3 {
                m.insert(b + k, lire(b + k));
            }
        }
    }
    m
}

/// %.15g de Python
fn g15(x: f64) -> String {
    if x.is_nan() {
        return "nan".into();
    }
    if x.is_infinite() {
        return if x < 0.0 { "-inf".into() } else { "inf".into() };
    }
    if x == 0.0 {
        return if x.is_sign_negative() { "-0".into() } else { "0".into() };
    }
    let e = format!("{:.14e}", x);
    let (mant, exp) = e.split_once('e').unwrap();
    let exp: i32 = exp.parse().unwrap();
    let sans_zeros = |s: &str| -> String {
        if s.contains('.') { s.trim_end_matches('0').trim_end_matches('.').to_string() } else { s.to_string() }
    };
    if (-4..15).contains(&exp) {
        sans_zeros(&format!("{:.*}", (14 - exp) as usize, x))
    } else {
        format!("{}e{}{:02}", sans_zeros(mant), if exp < 0 { '-' } else { '+' }, exp.abs())
    }
}

/// une valeur rangée écrite selon son type (comme valeur_affichee de vtx128.py)
pub fn valeur(v: u128, t: char) -> String {
    match t {
        'x' => {
            let (et, e, m) = (v >> 126, ((v >> 112) & 16383) as i32, v & ((1u128 << 112) - 1));
            if et == 0 {
                return "inconnu".into();
            }
            if et == 3 {
                return "variable".into();
            }
            if e == 16383 {
                return "?".into();
            }
            let x = (m as f64) * 2f64.powi(2 * (e.max(1) - 8247));
            g15(if et == 1 { -x } else { x })
        }
        'f' => {
            let a = v as u64;
            let (et, e, m) = (a >> 62, ((a >> 52) & 1023) as i32, a & ((1u64 << 52) - 1));
            let x = (m as f64) * 2f64.powi(2 * (e.max(1) - 537));
            g15(if et == 1 { -x } else { x })
        }
        'q' => ["inconnu", "faux", "vrai", "variable"][(v & 3) as usize].into(),
        'p' => format!("#{:032X}", v),
        'e' | 'i' => {
            let v64 = v as u64;
            if t == 'e' && v64 >> 63 == 1 {
                format!("{} ({})", v64, v64 as i64)
            } else {
                v64.to_string()
            }
        }
        _ => v.to_string(),
    }
}

fn element(a: &AtomeP) -> String {
    let v = (a.entrees.len() + a.sorties.len()).max(1);
    match v {
        1 => "H".into(),
        2 => "O".into(),
        3 => "N".into(),
        4 => "C".into(),
        _ => "C".repeat((v + 1) / 2),
    }
}

fn arbre(r: &ReactionP, liaison: &str, lire: &dyn Fn(u64) -> u128, prefixe: &str, vus: &mut HashSet<String>, out: &mut Vec<String>) {
    let place = |n: &str| r.noms.iter().find(|x| x.0 == n).map(|x| (x.1, x.2));
    // la valeur et son unité (comme vtx128.py : rien quand elle n'en a pas)
    let avec_unite = |v: String, n: &str| match r.noms.iter().position(|x| x.0 == n).map(|i| &r.unites[i]) {
        Some(u) if !u.is_empty() => format!("{} {}", v, u),
        _ => v,
    };
    let est_param = !r.atomes.iter().any(|a| a.sorties.iter().any(|s| s == liaison));
    if est_param {
        let vu = match place(liaison) {
            Some((b, t)) if lire(b + 2) != 0 => format!(" = {}", avec_unite(valeur(lire(b), t), liaison)),
            _ => String::new(),
        };
        out.push(format!("{}{}{}   ← une entrée de la réaction {}", prefixe, liaison, vu, r.nom));
        return;
    }
    let a = r.atomes.iter().find(|a| a.sorties.iter().any(|s| s == liaison)).unwrap();
    let (b, t) = place(liaison).unwrap_or((0, 'e'));
    let (val, nb, la) = (lire(b), lire(b + 1), lire(b + 2));
    let quoi = if nb == 0 {
        "jamais calculée".to_string()
    } else if la == 0 {
        format!("porte faux (sa branche n'a pas réagi ; la valeur calculée : {})", valeur(val, t))
    } else if la == 3 {
        format!("variable (une erreur, une division par zéro, non réparée ; la valeur calculée : {})", valeur(val, t))
    } else {
        format!("= {}", avec_unite(valeur(val, t), liaison))
    };
    let appels = lire(r.appels);
    let fois = if a.souvenir {
        format!(", souvenir : réagi {} fois sur {} appels", nb, appels)
    } else if nb <= 1 {
        String::new()
    } else {
        format!(", réagi {} fois", nb)
    };
    let nom = if a.nom.is_empty() { String::new() } else { format!("{} : ", a.nom) };
    let mut ligne = format!("{}{} {}   ← {}{}   (ligne {}, {}{})", prefixe, liaison, quoi, nom, a.texte, a.ligne, element(a), fois);
    if vus.contains(liaison) {
        ligne.push_str("   [vu plus haut]");
        out.push(ligne);
        return;
    }
    out.push(ligne);
    vus.insert(liaison.to_string());
    let p2 = format!("{}    ", prefixe);
    for e in &a.entrees {
        arbre(r, e, lire, &p2, vus, out);
    }
}

/// le texte de « pourquoi » : quoi = None (ce que rend chaque réaction, ou ce que lisent ses atomes de bout de chaîne),
/// « liaison » ou « réaction.liaison »
pub fn pourquoi(reactions: &[ReactionP], quoi: Option<&str>, lire: &dyn Fn(u64) -> u128) -> String {
    let mut out = Vec::new();
    for r in reactions {
        let connu = |n: &str| r.noms.iter().any(|x| x.0 == n);
        let cibles: Vec<String> = match quoi {
            None => {
                if !r.resultat.is_empty() && connu(&r.resultat) {
                    vec![r.resultat.clone()]
                } else {
                    let mut v: Vec<String> = Vec::new();
                    for a in r.atomes.iter().filter(|a| a.sorties.is_empty()) {
                        for e in &a.entrees {
                            if !v.contains(e) {
                                v.push(e.clone());
                            }
                        }
                    }
                    v
                }
            }
            Some(q) => match q.split_once('.') {
                Some((reac, l)) if reac == r.nom => vec![l.to_string()],
                Some(_) => vec![],
                None => vec![q.to_string()],
            },
        };
        let cibles: Vec<String> = cibles.into_iter().filter(|c| connu(c)).collect();
        if !cibles.is_empty() {
            out.push(String::new());
            out.push(format!("réaction {} :", r.nom));
            for c in &cibles {
                let mut vus = HashSet::new();
                arbre(r, c, lire, "  ", &mut vus, &mut out);
            }
        }
    }
    out.join("\n")
}
