// La paillasse : la surface des réactions, au centre d'Ogmios (docs/vtx-chimie.md, docs/vtx-reactions.md).
//
// Une réaction y est dessinée comme une molécule : chaque atome est une case (son élément, déduit de la valence : H, O, N,
// C), chaque liaison un trait d'une sortie (à droite d'une case) vers une entrée (à gauche) ; les cases sont rangées par
// vagues, de gauche à droite. La paillasse et le texte sont le même programme, dans les deux sens :
//   - le texte change : la paillasse est relue (sans compiler : une lecture des lignes de la réaction, qui garde ce qui
//     n'est pas encore juste, comme une entrée libre « _ », une liaison inconnue) ;
//   - sur la paillasse, on déplace une case, on tire une liaison d'une sortie vers une case (elle remplit son entrée
//     libre « _ », ou remplace l'entrée visée), on tire une entrée vers le vide (elle redevient « _ »), on ajoute un
//     atome (double clic dans le vide : la ligne « = _ -> l1 » s'écrit dans la réaction), on en retire un (Suppr) :
//     chaque geste réécrit la ligne du texte.
// Après une exécution avec la provenance (Ctrl+P), chaque liaison porte sa valeur et son état de Belnap : vrai (arrivée),
// faux (sa branche n'a pas réagi), inconnu (jamais calculée).
//
// Ce module ne dépend pas de Windows : il dessine dans une image (les traits, les cases) et rend la liste des textes à
// écrire par-dessus. L'atelier écrit ces textes avec la police de Windows ; « vtx paillasse » les écrit avec la police
// 5 × 7 du prélude, dans un PNG, pour vérifier sans écran.
use std::collections::HashMap;

// ------------------------------------------------------------------------------------------------ la lecture du texte
#[derive(Clone, Debug, PartialEq)]
pub enum Genre {
    Calcul,
    Si,
    Pont,
    RendezVous,
    Chaque,
    Effet,
}

/// une entrée d'un atome : un nom de liaison (toutes ses places dans la ligne) ou une entrée libre « _ » (une place)
#[derive(Clone, Debug)]
pub struct Port {
    pub nom: String,
    pub places: Vec<(usize, usize)>, // octets dans la ligne
}

#[derive(Clone, Debug)]
pub struct Atome {
    pub ligne: usize, // à partir de 0
    pub nom: String,
    pub quoi: String,
    pub sorties: Vec<String>,
    pub entrees: Vec<Port>,
    pub apres: Vec<String>,
    pub genre: Genre,
    pub vague: usize,
    pub element: String,
}

impl Atome {
    pub fn cle(&self) -> String {
        match self.sorties.first() {
            Some(s) => s.clone(),
            None => format!("@{}", self.quoi.trim()),
        }
    }
    pub fn valence(&self) -> usize {
        self.entrees.iter().filter(|p| p.nom != "_").count() + self.sorties.len()
    }
}

#[derive(Clone, Debug)]
pub struct Reaction {
    pub nom: String,
    pub ligne: usize,
    pub fin: usize, // la ligne de l'accolade fermante
    pub params: Vec<String>,
    pub resultat: Option<String>,
    pub atomes: Vec<Atome>,
    pub contrats: Vec<(usize, String)>,
    pub erreurs: Vec<String>,
    pub nb_vagues: usize,
}

const MOTS: &[&str] = &["si", "alors", "sinon", "pour", "chaque", "dans", "somme", "min", "max", "rendez", "vous", "rendezvous",
                        "pont", "vers", "vrai", "faux", "inconnu", "variable", "et", "ou", "non", "apres", "reparer", "par", "garder"];
const UNITES: &[&str] = &["m", "kg", "s", "A", "K", "mol", "cd", "N", "J", "W", "Pa", "Hz", "C", "V", "Ω", "km", "cm", "mm", "g",
                          "ms", "min", "h"];

fn lettre(c: char) -> bool {
    c.is_alphanumeric() || c == '_'
}

/// la fin du code d'une ligne : avant « // » (hors d'un texte)
fn fin_code(l: &str) -> usize {
    let b = l.as_bytes();
    let mut dans = false;
    let mut i = 0;
    while i < b.len() {
        if b[i] == b'"' {
            dans = !dans;
        } else if !dans && b[i] == b'/' && i + 1 < b.len() && b[i + 1] == b'/' {
            return i;
        }
        i += 1;
    }
    b.len()
}

/// la première place de « motif » hors des textes, entre d et f
fn chercher(l: &str, motif: &str, d: usize, f: usize) -> Option<usize> {
    let b = l.as_bytes();
    let m = motif.as_bytes();
    let mut dans = false;
    let mut i = d;
    while i + m.len() <= f {
        if b[i] == b'"' {
            dans = !dans;
        } else if !dans && &b[i..i + m.len()] == m {
            return Some(i);
        }
        i += 1;
    }
    None
}

/// les mots d'un morceau de ligne : (mot, début, fin, ce qui précède, ce qui suit), sans les textes ni les nombres ;
/// les unités écrites après un nombre sont sautées
fn mots(l: &str, d: usize, f: usize) -> Vec<(String, usize, usize, char, char)> {
    let mut v = Vec::new();
    let cs: Vec<(usize, char)> = l[d..f].char_indices().map(|(i, c)| (i + d, c)).collect();
    let mut k = 0;
    let mut apres_nombre = false;
    let mut prec = ' ';
    while k < cs.len() {
        let (i, c) = cs[k];
        if c == '"' || c == '\'' {
            let q = c;
            k += 1;
            while k < cs.len() && cs[k].1 != q {
                k += 1;
            }
            k += 1;
            prec = q;
            apres_nombre = false;
            continue;
        }
        if c.is_ascii_digit() || c == '#' {
            k += 1;
            while k < cs.len() && (lettre(cs[k].1) || cs[k].1 == '.') {
                k += 1;
            }
            apres_nombre = true;
            prec = '0';
            continue;
        }
        if lettre(c) {
            let d0 = i;
            while k < cs.len() && lettre(cs[k].1) {
                k += 1;
            }
            let f0 = if k < cs.len() { cs[k].0 } else { f };
            let mot = l[d0..f0].to_string();
            if apres_nombre && UNITES.contains(&mot.as_str()) {
                // une unité : elle continue après « / », « · » ou un exposant
                prec = 'u';
                continue;
            }
            apres_nombre = false;
            let mut j = k;
            while j < cs.len() && cs[j].1 == ' ' {
                j += 1;
            }
            let suit = if j < cs.len() { cs[j].1 } else { ' ' };
            v.push((mot, d0, f0, prec, suit));
            prec = 'a';
            continue;
        }
        if c != ' ' {
            if !(apres_nombre && (c == '/' || c == '·' || c == '²' || c == '³' || c == '°')) {
                apres_nombre = false;
            }
            prec = c;
        }
        k += 1;
    }
    v
}

fn element_de(v: usize) -> String {
    match v.max(1) {
        1 => "H".into(),
        2 => "O".into(),
        3 => "N".into(),
        4 => "C".into(),
        n => format!("C{}", (n + 1) / 2),
    }
}

/// la lecture : les réactions du texte, leurs atomes, leurs liaisons et leurs vagues
pub fn analyser(source: &str) -> Vec<Reaction> {
    let lignes: Vec<&str> = source.split('\n').collect();
    let mut out = Vec::new();
    let mut i = 0;
    while i < lignes.len() {
        let l = lignes[i].trim_end_matches('\r');
        let t = l.trim_start();
        if !t.starts_with("reaction ") {
            i += 1;
            continue;
        }
        let fc = fin_code(l);
        let code = &l[..fc];
        // l'en-tête : reaction NOM(p1: type unité, p2) -> r: type unité {
        let apres_mot = code.find("reaction ").map(|p| p + 9).unwrap_or(0);
        let ouv = code[apres_mot..].find('(').map(|p| p + apres_mot);
        let nom = code[apres_mot..ouv.unwrap_or(code.len())].trim().trim_end_matches('{').trim().to_string();
        let mut params = Vec::new();
        let mut resultat = None;
        if let Some(o) = ouv {
            let fe = code[o..].find(')').map(|p| p + o).unwrap_or(code.len());
            for morceau in code[o + 1..fe].split(',') {
                let n = morceau.split(':').next().unwrap_or("").trim();
                if !n.is_empty() {
                    params.push(n.to_string());
                }
            }
            if let Some(fl) = code[fe..].find("->") {
                let r = code[fe + fl + 2..].split(|c| c == ':' || c == '{').next().unwrap_or("").trim();
                if !r.is_empty() {
                    resultat = Some(r.to_string());
                }
            }
        }
        // le corps : jusqu'à l'accolade qui ferme (les accolades comptées hors des textes et des commentaires)
        let mut prof = code.matches('{').count() as i64 - code.matches('}').count() as i64;
        let mut j = i + 1;
        let mut corps = Vec::new();
        while j < lignes.len() && prof > 0 {
            let lj = lignes[j].trim_end_matches('\r');
            let cj = &lj[..fin_code(lj)];
            let mut dans = false;
            let mut ferme = false;
            for c in cj.chars() {
                if c == '"' {
                    dans = !dans;
                } else if !dans && c == '{' {
                    prof += 1;
                } else if !dans && c == '}' {
                    prof -= 1;
                    if prof == 0 {
                        ferme = true;
                    }
                }
            }
            if ferme {
                break;
            }
            corps.push(j);
            j += 1;
        }
        let mut r = Reaction { nom, ligne: i, fin: j.min(lignes.len().saturating_sub(1)), params, resultat, atomes: vec![], contrats: vec![],
                               erreurs: vec![], nb_vagues: 0 };
        if prof > 0 {
            r.erreurs.push(format!("la réaction {} n'est pas fermée (une accolade manque)", r.nom));
        }
        for &k in &corps {
            let lk = lignes[k].trim_end_matches('\r');
            lire_atome(&mut r, lk, k);
        }
        relier_et_ranger(&mut r, &lignes);
        out.push(r);
        i = j + 1;
    }
    out
}

fn lire_atome(r: &mut Reaction, l: &str, numero: usize) {
    let fc = fin_code(l);
    let code = &l[..fc];
    let t = code.trim();
    if t.is_empty() || t == "{" || t == "}" {
        return;
    }
    let debut = code.len() - code.trim_start().len();
    for c in ["exige", "garantit"] {
        if t.starts_with(c) && t[c.len()..].starts_with(' ') && !t[c.len()..].trim_start().starts_with('=') {
            r.contrats.push((numero, t.trim_end_matches(';').to_string()));
            return;
        }
    }
    let fin = code.trim_end().trim_end_matches(';').len();
    let fleche = chercher(code, "->", debut, fin);
    let gauche_fin = fleche.unwrap_or(fin);
    // [nom =] ce que fait l'atome
    let mut q0 = debut;
    let mut nom = String::new();
    let ws = mots(code, debut, gauche_fin);
    if let Some((m, _, f0, _, suit)) = ws.first() {
        if *suit == '=' && code[*f0..].trim_start().starts_with('=') && !code[*f0..].trim_start().starts_with("==")
            && code[debut..].starts_with(m.as_str()) {
            nom = m.clone();
            q0 = f0 + code[*f0..].find('=').unwrap() + 1;
        }
    }
    if nom.is_empty() && code[debut..].starts_with('=') && !code[debut..].starts_with("==") {
        q0 = debut + 1;
    }
    // « apres » termine ce que fait l'atome (sans liaison) ou suit les liaisons
    let mut q1 = gauche_fin;
    let mut apres = Vec::new();
    let lire_apres = |d: usize, f: usize, apres: &mut Vec<String>| -> Option<usize> {
        let ws = mots(code, d, f);
        let p = ws.iter().position(|w| w.0 == "apres")?;
        for w in &ws[p + 1..] {
            apres.push(w.0.clone());
        }
        Some(ws[p].1)
    };
    let mut sorties = Vec::new();
    match fleche {
        None => {
            if let Some(p) = lire_apres(q0, gauche_fin, &mut apres) {
                q1 = p;
            }
        }
        Some(fl) => {
            let mut fin_s = fin;
            if let Some(p) = lire_apres(fl + 2, fin, &mut apres) {
                fin_s = p;
            }
            for morceau in code[fl + 2..fin_s].split(',') {
                let n = morceau.split(':').next().unwrap_or("").trim();
                if !n.is_empty() {
                    sorties.push(n.to_string());
                }
            }
        }
    }
    let quoi = code[q0..q1].trim().to_string();
    let tq = quoi.as_str();
    let genre = if tq.starts_with("si ") {
        Genre::Si
    } else if tq.starts_with("pont ") {
        Genre::Pont
    } else if tq.starts_with("rendez") {
        Genre::RendezVous
    } else if tq.starts_with("pour ") || ((tq.starts_with("somme ") || tq.starts_with("min ") || tq.starts_with("max "))
                                            && tq.contains(" pour ")) {
        Genre::Chaque
    } else if sorties.is_empty() {
        Genre::Effet
    } else {
        Genre::Calcul
    };
    // les entrées sont trouvées une fois toutes les liaisons connues (relier_et_ranger) : on garde la place de quoi
    r.atomes.push(Atome { ligne: numero, nom, quoi, sorties, entrees: vec![Port { nom: String::new(), places: vec![(q0, q1)] }],
                          apres, genre, vague: 0, element: String::new() });
}

/// ce que touche un atome hors de ses liaisons (comme Atome.cibles de vtx128.py) : (genre, étage, adresse)
#[derive(Clone, PartialEq)]
struct Cible(u8, Option<u32>, Option<u64>); // genre : 0 cube, 1 écran, 2 sortie, 3 le monde

fn heurte(a: &Cible, b: &Cible) -> bool {
    if a.0 == 3 || b.0 == 3 {
        return true;
    }
    if a.0 != b.0 {
        return false;
    }
    if a.0 != 0 {
        return true;
    }
    match (a.1, b.1) {
        (Some(x), Some(y)) => x == y && (a.2.is_none() || b.2.is_none() || a.2 == b.2),
        _ => true,
    }
}

/// les cases du cube nommées dans un morceau de texte : « @2[5] » (étage 2, case 5), « @2[i] » (étage 2, une case
/// calculée), « @(e)[…] » ou « @[…] » (n'importe où)
fn cases_du_cube(t: &str) -> Vec<Cible> {
    let mut v = Vec::new();
    let b: Vec<char> = t.chars().collect();
    let mut k = 0;
    while k < b.len() {
        if b[k] == '@' {
            let mut j = k + 1;
            let mut etage = String::new();
            while j < b.len() && b[j].is_ascii_digit() {
                etage.push(b[j]);
                j += 1;
            }
            let et = if etage.is_empty() { None } else { etage.parse::<u32>().ok() };
            // l'adresse : entre les crochets qui suivent (en sautant « (…) » d'un étage calculé)
            let mut p = 0i32;
            while j < b.len() && (b[j] != '[' || p > 0) {
                if b[j] == '(' { p += 1; }
                if b[j] == ')' { p -= 1; }
                j += 1;
            }
            let mut adr = String::new();
            let mut q = 0i32;
            j += 1;
            while j < b.len() && (b[j] != ']' || q > 0) {
                if b[j] == '[' { q += 1; }
                if b[j] == ']' { q -= 1; }
                adr.push(b[j]);
                j += 1;
            }
            let a = adr.trim().parse::<u64>().ok();
            v.push(Cible(0, et, if et.is_some() { a } else { None }));
            k = j;
        }
        k += 1;
    }
    v
}

fn cibles(a: &Atome, lignes: &[&str]) -> Vec<Cible> {
    let q = a.quoi.as_str();
    let mut c = Vec::new();
    match a.genre {
        Genre::Pont => {
            let (x, vers) = match q.rfind(" vers ") {
                Some(p) => (&q[5..p], &q[p + 6..]),
                None => (q, ""),
            };
            c.extend(cases_du_cube(x));
            c.extend(cases_du_cube(vers).into_iter().take(1));
        }
        _ => {
            c.extend(cases_du_cube(q));
            if a.sorties.is_empty() && a.genre == Genre::Effet {
                // un appel seul : afficher, ecrire… touchent l'écran ; sortie, la sortie ; une autre fonction, le monde
                let nom: String = q.chars().take_while(|ch| lettre(*ch)).collect();
                let reste = q[nom.len()..].trim_start();
                if !nom.is_empty() && reste.starts_with('(') && reste.ends_with(')') && appel_entier(reste) {
                    c.push(match nom.as_str() {
                        "afficher" | "ecrire" | "texte" | "ecrire_car" => Cible(1, None, None),
                        "sortie" => Cible(2, None, None),
                        _ => Cible(3, None, None),
                    });
                }
            }
        }
    }
    let _ = lignes;
    c
}

/// « (…) » est-il un seul groupe de parenthèses (l'appel est toute l'expression) ?
fn appel_entier(t: &str) -> bool {
    let mut p = 0i32;
    let mut dans = false;
    for (i, ch) in t.char_indices() {
        if ch == '"' {
            dans = !dans;
        }
        if dans {
            continue;
        }
        if ch == '(' {
            p += 1;
        } else if ch == ')' {
            p -= 1;
            if p == 0 && i + 1 < t.len() {
                return false;
            }
        }
    }
    p == 0
}

fn relier_et_ranger(r: &mut Reaction, lignes: &[&str]) {
    let mut donne: HashMap<String, usize> = HashMap::new();
    for (k, a) in r.atomes.iter().enumerate() {
        for s in &a.sorties {
            if donne.insert(s.clone(), k).is_some() || r.params.contains(s) {
                r.erreurs.push(format!("ligne {} : la liaison {} est donnée deux fois", a.ligne + 1, s));
            }
        }
    }
    let params = r.params.clone();
    for a in r.atomes.iter_mut() {
        let (q0, q1) = a.entrees[0].places[0];
        let l = lignes[a.ligne].trim_end_matches('\r');
        let mut ports: Vec<Port> = Vec::new();
        for (m, d, f, prec, suit) in mots(l, q0, q1) {
            if prec == '.' || suit == '(' || MOTS.contains(&m.as_str()) {
                continue;
            }
            if m == "_" {
                ports.push(Port { nom: m, places: vec![(d, f)] });
            } else if donne.contains_key(&m) || params.contains(&m) {
                match ports.iter_mut().find(|p| p.nom == m) {
                    Some(p) => p.places.push((d, f)),
                    None => ports.push(Port { nom: m, places: vec![(d, f)] }),
                }
            }
        }
        a.entrees = ports;
        a.element = element_de(a.valence());
    }
    // l'ordre : ce que l'atome nomme dans « apres », puis, comme le compilateur, deux atomes qui touchent la même chose
    // (la même case du cube, l'écran, la sortie) : le second attend le premier, dans l'ordre des lignes, sauf si les
    // liaisons ou l'ordre écrit disent déjà le contraire
    let n = r.atomes.len();
    let par_nom: HashMap<String, usize> = r.atomes.iter().enumerate().filter(|(_, a)| !a.nom.is_empty()).map(|(k, a)| (a.nom.clone(), k)).collect();
    let mut avant: Vec<Vec<usize>> = vec![vec![]; n];
    for (k, a) in r.atomes.iter().enumerate() {
        for x in &a.apres {
            match par_nom.get(x) {
                Some(&d) => avant[k].push(d),
                None => r.erreurs.push(format!("ligne {} : « apres {} » : aucun atome ne porte ce nom", a.ligne + 1, x)),
            }
        }
    }
    let entrees_de = |k: usize| -> Vec<usize> { r.atomes[k].entrees.iter().filter_map(|p| donne.get(&p.nom).copied()).collect() };
    let lues: Vec<Vec<usize>> = (0..n).map(entrees_de).collect();
    let cibles: Vec<Vec<Cible>> = r.atomes.iter().map(|a| cibles(a, lignes)).collect();
    fn attend(a: usize, b: usize, avant: &[Vec<usize>], lues: &[Vec<usize>], vus: &mut Vec<bool>) -> bool {
        if vus[a] {
            return false;
        }
        vus[a] = true;
        avant[a].iter().chain(lues[a].iter()).any(|&p| p == b || attend(p, b, avant, lues, vus))
    }
    let mut effets: Vec<usize> = (0..n).filter(|&k| !cibles[k].is_empty()).collect();
    effets.sort_by_key(|&k| r.atomes[k].ligne);
    for (i, &a) in effets.iter().enumerate() {
        for &b in &effets[..i] {
            let conflit = cibles[a].iter().any(|x| cibles[b].iter().any(|y| heurte(x, y)));
            if conflit && !avant[a].contains(&b) && !attend(b, a, &avant, &lues, &mut vec![false; n]) {
                avant[a].push(b);
            }
        }
    }
    let mut deps: Vec<Vec<usize>> = vec![vec![]; n];
    for k in 0..n {
        deps[k] = lues[k].iter().chain(avant[k].iter()).copied().collect();
    }
    let mut vague = vec![0usize; n];
    let mut etat = vec![0u8; n]; // 0 pas vu, 1 en cours, 2 fait
    fn visiter(k: usize, deps: &[Vec<usize>], vague: &mut [usize], etat: &mut [u8], cycle: &mut bool) -> usize {
        if etat[k] == 2 {
            return vague[k];
        }
        if etat[k] == 1 {
            *cycle = true;
            return 0;
        }
        etat[k] = 1;
        let mut v = 1;
        for &d in &deps[k] {
            v = v.max(visiter(d, deps, vague, etat, cycle) + 1);
        }
        etat[k] = 2;
        vague[k] = v;
        v
    }
    let mut cycle = false;
    for k in 0..n {
        visiter(k, &deps, &mut vague, &mut etat, &mut cycle);
    }
    if cycle {
        r.erreurs.push("des liaisons forment un cycle : une liaison qui revient sur elle-même".into());
    }
    for (k, a) in r.atomes.iter_mut().enumerate() {
        a.vague = vague[k];
    }
    r.nb_vagues = vague.iter().copied().max().unwrap_or(0);
}

// ------------------------------------------------------------------------------------------------ les gestes sur le texte
fn remplacer_places(l: &str, places: &[(usize, usize)], par: &str) -> String {
    let mut p: Vec<(usize, usize)> = places.to_vec();
    p.sort();
    let mut out = String::new();
    let mut i = 0;
    for (d, f) in p {
        out.push_str(&l[i..d]);
        out.push_str(par);
        i = f;
    }
    out.push_str(&l[i..]);
    out
}

fn remplacer_ligne(source: &str, ligne: usize, nouvelle: &str) -> String {
    let mut v: Vec<String> = source.split('\n').map(|s| s.to_string()).collect();
    if ligne < v.len() {
        let cr = v[ligne].ends_with('\r');
        v[ligne] = nouvelle.to_string() + if cr { "\r" } else { "" };
    }
    v.join("\n")
}

/// relier : l'entrée « port » de l'atome reçoit la liaison « nom » (port = None : la première entrée libre « _ »)
pub fn relier(source: &str, a: &Atome, port: Option<usize>, nom: &str) -> Result<String, String> {
    let l = source.split('\n').nth(a.ligne).unwrap_or("").trim_end_matches('\r');
    let p = match port {
        Some(k) => a.entrees.get(k).ok_or("cette entrée n'existe pas")?,
        None => a.entrees.iter().find(|p| p.nom == "_").ok_or_else(|| {
            format!("l'atome « {} » n'a pas d'entrée libre : tirez la liaison sur une de ses entrées pour la remplacer, ou écrivez _ \
                     dans son texte", a.quoi)
        })?,
    };
    if a.sorties.iter().any(|s| s == nom) {
        return Err(format!("{} sort de cet atome : une liaison ne revient pas sur l'atome qui la donne", nom));
    }
    Ok(remplacer_ligne(source, a.ligne, &remplacer_places(l, &p.places, nom)))
}

/// délier : l'entrée redevient libre (« _ »)
pub fn delier(source: &str, a: &Atome, port: usize) -> Result<String, String> {
    let l = source.split('\n').nth(a.ligne).unwrap_or("").trim_end_matches('\r');
    let p = a.entrees.get(port).ok_or("cette entrée n'existe pas")?;
    Ok(remplacer_ligne(source, a.ligne, &remplacer_places(l, &p.places, "_")))
}

/// un atome neuf à la fin de la réaction : « = _ -> lK » ; rend le texte et la ligne écrite
pub fn ajouter_atome(source: &str, r: &Reaction) -> (String, usize) {
    let mut k = 1;
    let pris = |n: &str| r.params.iter().any(|p| p == n) || r.atomes.iter().any(|a| a.sorties.iter().any(|s| s == n));
    while pris(&format!("l{}", k)) {
        k += 1;
    }
    let lignes: Vec<&str> = source.split('\n').collect();
    let retrait = r.atomes.last().map(|a| {
        let l = lignes[a.ligne];
        l[..l.len() - l.trim_start().len()].to_string()
    }).unwrap_or_else(|| "    ".into());
    let cr = if source.contains("\r\n") { "\r" } else { "" };
    let mut v: Vec<String> = lignes.iter().map(|s| s.to_string()).collect();
    let place = r.fin.min(v.len());
    v.insert(place, format!("{}= _ -> l{}{}", retrait, k, cr));
    (v.join("\n"), place)
}

/// retirer un atome : sa ligne s'en va
pub fn retirer_atome(source: &str, a: &Atome) -> String {
    let mut v: Vec<&str> = source.split('\n').collect();
    if a.ligne < v.len() {
        v.remove(a.ligne);
    }
    v.join("\n")
}

/// une réaction neuve, à la fin du texte
pub fn ajouter_reaction(source: &str) -> (String, usize) {
    let noms: Vec<String> = analyser(source).into_iter().map(|r| r.nom).collect();
    let mut nom = "principal".to_string();
    let mut k = 1;
    while noms.contains(&nom) || source.contains(&format!("fonction {}(", nom)) {
        nom = format!("r{}", k);
        k += 1;
    }
    let cr = if source.contains("\r\n") { "\r\n" } else { "\n" };
    let mut t = source.trim_end().to_string();
    if !t.is_empty() {
        t.push_str(cr);
        t.push_str(cr);
    }
    let ligne = t.split('\n').count() - 1;
    t.push_str(&format!("reaction {}() {{{}    = _ -> l1{}}}{}", nom, cr, cr, cr));
    (t, ligne + 1)
}

// ------------------------------------------------------------------------------------------------ le dessin
pub const FOND: u32 = 0x1B1E24;
const GRILLE: u32 = 0x262A33;
const BANDE: u32 = 0x20242C;
const ENCRE: u32 = 0xD8D4C8;
const PALE: u32 = 0x8A93A6;
const OR: u32 = 0xFFD060;
const VRAI: u32 = 0x78C878;
const FAUX: u32 = 0xE06050;
const INCONNU: u32 = 0x5A6272;
const VARIABLE: u32 = 0xC890E8;
const BRAISE: u32 = 0xFF7040;

fn couleur_element(e: &str) -> u32 {
    match e.chars().next() {
        Some('H') => 0xE8E8E8,
        Some('O') => 0xE05050,
        Some('N') => 0x5080F0,
        _ => 0x9AA0A8,
    }
}

pub struct TexteP {
    pub x: i32,
    pub y: i32,
    pub texte: String,
    pub couleur: u32,
}

/// une case placée : l'atome, son rectangle, ses entrées et ses sorties (les points)
#[derive(Clone)]
struct Case {
    atome: usize,
    x: i32,
    y: i32,
    l: i32,
    h: i32,
    entrees: Vec<(i32, i32)>,
    sorties: Vec<(i32, i32)>,
}

#[derive(Clone)]
enum Geste {
    Deplacer { atome: usize, dx: i32, dy: i32, x0: i32, y0: i32, bouge: bool },
    Lier { nom: String, de: (i32, i32), a: (i32, i32) },
    Delier { atome: usize, port: usize, de: (i32, i32), a: (i32, i32) },
    Panoramique { x0: i32, y0: i32, d0: (i32, i32) },
}

pub enum Reponse {
    Rien,
    Redessiner,
    /// le texte réécrit par un geste ; la ligne à montrer dans l'éditeur
    Texte { source: String, ligne: usize },
    /// aller à cette ligne dans l'éditeur
    Aller(usize),
    Message(String),
}

pub enum Souris {
    Bas,
    Bouge,
    Haut,
    Double,
}

pub struct Paillasse {
    pub reactions: Vec<Reaction>,
    pub courante: usize,
    pub choisi: Option<usize>,
    /// les places choisies à la main : (réaction, clé de l'atome) -> (x, y) en points de la paillasse
    pub positions: HashMap<(String, String), (i32, i32)>,
    /// après une exécution avec la provenance : (réaction, liaison) -> (valeur écrite, état de Belnap 0..3)
    pub valeurs: HashMap<(String, String), (String, u8)>,
    pub decal: (i32, i32),
    /// la taille d'un caractère de la police (en pixels de l'écran) et l'échelle
    pub car_l: i32,
    pub car_h: i32,
    pub echelle: f32,
    pub message: Option<String>,
    cases: Vec<Case>,
    colonnes: Vec<(usize, i32, i32)>, // (vague, x, largeur) ; la vague 0 : les entrées de la réaction
    onglets: Vec<(i32, i32, i32, i32, usize)>,
    entrees_r: Vec<(String, (i32, i32))>,
    geste: Option<Geste>,
}

impl Default for Paillasse {
    fn default() -> Self {
        Self::nouvelle()
    }
}

/// une image : des points 0x00RRGGBB
pub struct Image {
    pub l: usize,
    pub h: usize,
    pub px: Vec<u32>,
}

impl Image {
    fn point(&mut self, x: i32, y: i32, c: u32) {
        if x >= 0 && y >= 0 && (x as usize) < self.l && (y as usize) < self.h {
            self.px[y as usize * self.l + x as usize] = c;
        }
    }
    fn plein(&mut self, x: i32, y: i32, l: i32, h: i32, c: u32) {
        for j in y.max(0)..(y + h).min(self.h as i32) {
            for i in x.max(0)..(x + l).min(self.l as i32) {
                self.px[j as usize * self.l + i as usize] = c;
            }
        }
    }
    fn cadre(&mut self, x: i32, y: i32, l: i32, h: i32, e: i32, c: u32) {
        self.plein(x, y, l, e, c);
        self.plein(x, y + h - e, l, e, c);
        self.plein(x, y, e, h, c);
        self.plein(x + l - e, y, e, h, c);
    }
    fn disque(&mut self, cx: i32, cy: i32, r: i32, c: u32) {
        for j in -r..=r {
            for i in -r..=r {
                if i * i + j * j <= r * r {
                    self.point(cx + i, cy + j, c);
                }
            }
        }
    }
    fn anneau(&mut self, cx: i32, cy: i32, r: i32, c: u32) {
        for j in -r..=r {
            for i in -r..=r {
                let d = i * i + j * j;
                if d <= r * r && d >= (r - 2) * (r - 2) {
                    self.point(cx + i, cy + j, c);
                }
            }
        }
    }
    fn trait_(&mut self, a: (i32, i32), b: (i32, i32), e: i32, c: u32, pointille: bool) {
        let n = ((b.0 - a.0).abs().max((b.1 - a.1).abs())).max(1);
        for k in 0..=n {
            if pointille && (k / 6) % 2 == 1 {
                continue;
            }
            let x = a.0 + (b.0 - a.0) * k / n;
            let y = a.1 + (b.1 - a.1) * k / n;
            self.plein(x - e / 2, y - e / 2, e, e, c);
        }
    }
    /// une liaison : une courbe de Bézier qui sort à l'horizontale et arrive à l'horizontale
    fn courbe(&mut self, a: (i32, i32), b: (i32, i32), e: i32, c: u32, pointille: bool) {
        let dx = ((b.0 - a.0).abs() / 2).max(30) as f32;
        let p = [(a.0 as f32, a.1 as f32), (a.0 as f32 + dx, a.1 as f32), (b.0 as f32 - dx, b.1 as f32), (b.0 as f32, b.1 as f32)];
        let n = 40;
        let mut prec = a;
        for k in 1..=n {
            let t = k as f32 / n as f32;
            let u = 1.0 - t;
            let x = u * u * u * p[0].0 + 3.0 * u * u * t * p[1].0 + 3.0 * u * t * t * p[2].0 + t * t * t * p[3].0;
            let y = u * u * u * p[0].1 + 3.0 * u * u * t * p[1].1 + 3.0 * u * t * t * p[2].1 + t * t * t * p[3].1;
            let q = (x.round() as i32, y.round() as i32);
            if !pointille || k % 4 < 2 {
                self.trait_(prec, q, e, c, false);
            }
            prec = q;
        }
    }
}

/// les textes écrits avec la police 5 × 7 (pour les PNG de « vtx paillasse »)
pub fn ecrire_textes(im: &mut Image, textes: &[TexteP], car_l: i32, car_h: i32) {
    let s = ((car_h - 2) / 8).max(1);
    for t in textes {
        let mut x = t.x;
        for ch in t.texte.chars() {
            let c = ch as u32;
            let k = if (32..=126).contains(&c) {
                Some((c - 32) as usize)
            } else {
                [233, 232, 234, 235, 224, 226, 231, 249, 251, 244, 238, 239, 201, 200, 192, 199, 215, 183, 171, 187, 176]
                    .iter().position(|&v| v == c).map(|p| 95 + p)
            };
            let (ga, gb) = POLICE[k.unwrap_or(31)];
            for col in 0..5 {
                let v = if col < 4 { (ga >> (7 * col)) & 127 } else { gb };
                for lig in 0..7 {
                    if (v >> lig) & 1 == 1 {
                        im.plein(x + col as i32 * s, t.y + (car_h - 7 * s) / 2 + lig as i32 * s, s, s, t.couleur);
                    }
                }
            }
            x += car_l;
        }
    }
}

impl Paillasse {
    pub fn nouvelle() -> Paillasse {
        Paillasse { reactions: vec![], courante: 0, choisi: None, positions: HashMap::new(), valeurs: HashMap::new(), decal: (0, 0),
                    car_l: 6, car_h: 12, echelle: 1.0, message: None, cases: vec![], colonnes: vec![], onglets: vec![], entrees_r: vec![], geste: None }
    }

    /// relire le texte (la réaction montrée et l'atome choisi restent, si on les retrouve)
    pub fn lire(&mut self, source: &str) {
        let nom = self.reactions.get(self.courante).map(|r| r.nom.clone());
        let cle = self.choisi.and_then(|k| self.reaction().and_then(|r| r.atomes.get(k)).map(|a| a.cle()));
        self.reactions = analyser(source);
        self.courante = nom.and_then(|n| self.reactions.iter().position(|r| r.nom == n)).unwrap_or(0).min(self.reactions.len().saturating_sub(1));
        self.choisi = cle.and_then(|c| self.reaction().and_then(|r| r.atomes.iter().position(|a| a.cle() == c)));
        self.geste = None;
    }

    pub fn reaction(&self) -> Option<&Reaction> {
        self.reactions.get(self.courante)
    }

    /// le curseur du texte est sur cette ligne : la réaction et l'atome qui y sont deviennent ceux de la paillasse ;
    /// vrai si quelque chose a changé
    pub fn choisir_ligne(&mut self, ligne: usize) -> bool {
        for (k, r) in self.reactions.iter().enumerate() {
            if ligne >= r.ligne && ligne <= r.fin {
                let a = r.atomes.iter().position(|a| a.ligne == ligne);
                let change = self.courante != k || self.choisi != a;
                self.courante = k;
                self.choisi = a;
                return change;
            }
        }
        false
    }

    fn px(&self, v: i32) -> i32 {
        (v as f32 * self.echelle) as i32
    }

    /// la taille d'une case et la place de ses rangées d'entrées et de sorties (relatives à la case)
    fn mesure_case(&self, a: &Atome) -> (i32, i32, Vec<i32>) {
        let (cl, ch) = (self.car_l, self.car_h);
        let n = a.entrees.len().max(a.sorties.len()) as i32;
        let lab = a.entrees.iter().map(|p| if p.nom == "_" { 1 } else { p.nom.chars().count() }).max().unwrap_or(0) as i32;
        let titre = if a.nom.is_empty() { 8 } else { a.nom.chars().count() as i32 };
        let l = (a.quoi.chars().count().min(40) as i32 + 4).max(titre + 7).max(lab + 6).max(14) * cl;
        let ht = ch + self.px(10);
        let ry0 = ht + ch + self.px(10);
        let rangs: Vec<i32> = (0..n).map(|i| ry0 + i * (ch + self.px(6)) + ch / 2).collect();
        let h = ry0 + n * (ch + self.px(6)) + self.px(2);
        (l, h, rangs)
    }

    fn etiquette_sortie(&self, s: &str) -> String {
        match self.etat_liaison(s) {
            Some((v, 1)) => format!("{} porte faux ({})", s, v),
            Some((_, 3)) => format!("{} : variable (erreur)", s),
            Some((_, 0)) => format!("{} : jamais calculée", s),
            Some((v, _)) => format!("{} = {}", s, v),
            None => s.to_string(),
        }
    }

    /// les cases de la réaction montrée : rangées par vagues (ou à la place choisie à la main)
    fn placer(&mut self) {
        self.cases.clear();
        self.entrees_r.clear();
        self.colonnes.clear();
        let r = match self.reactions.get(self.courante) {
            Some(r) => r.clone(),
            None => return,
        };
        let (cl, ch) = (self.car_l, self.car_h);
        let (x0, y0) = self.origine();
        // les colonnes : les entrées de la réaction (s'il y en a), puis une par vague, assez large pour ses cases et
        // les noms de leurs sorties
        let mut x = x0;
        if !r.params.is_empty() {
            let lp = r.params.iter().map(|p| {
                let t = match self.etat_liaison(p) { Some((v, _)) => format!("{} = {}", p, v), None => p.clone() };
                t.chars().count() as i32
            }).max().unwrap_or(1) * cl + self.px(40);
            for (k, p) in r.params.iter().enumerate() {
                self.entrees_r.push((p.clone(), (x + lp, y0 + self.px(10) + k as i32 * (ch + self.px(14)) + ch / 2)));
            }
            self.colonnes.push((0, x - self.px(12), lp + self.px(40)));
            x += lp + self.px(40);
        }
        for v in 1..=r.nb_vagues.max(1) {
            let dans: Vec<&Atome> = r.atomes.iter().filter(|a| a.vague == v).collect();
            let lmax = dans.iter().map(|a| self.mesure_case(a).0).max().unwrap_or(self.px(120));
            let lab = dans.iter().flat_map(|a| a.sorties.iter()).map(|s| self.etiquette_sortie(s).chars().count() as i32).max().unwrap_or(0);
            let large = lmax + (lab * cl + self.px(40)).max(self.px(70));
            self.colonnes.push((v, x - self.px(12), large));
            x += large;
        }
        let mut hauteur_vague: HashMap<usize, i32> = HashMap::new();
        let mut ordre: Vec<usize> = (0..r.atomes.len()).collect();
        ordre.sort_by_key(|&k| (r.atomes[k].vague, r.atomes[k].ligne));
        for k in ordre {
            let a = &r.atomes[k];
            let (l, h, rangs) = self.mesure_case(a);
            let (x, y) = match self.positions.get(&(r.nom.clone(), a.cle())) {
                Some(&(px, py)) => (x0 + self.px(px), y0 + self.px(py)),
                None => {
                    let cx = self.colonnes.iter().find(|c| c.0 == a.vague).map(|c| c.1 + self.px(12)).unwrap_or(x0);
                    let hy = hauteur_vague.entry(a.vague).or_insert(0);
                    let p = (cx, y0 + *hy);
                    *hy += h + self.px(26);
                    p
                }
            };
            let entrees = (0..a.entrees.len()).map(|i| (x, y + rangs[i])).collect();
            let sorties = (0..a.sorties.len()).map(|i| (x + l, y + rangs[i])).collect();
            self.cases.push(Case { atome: k, x, y, l, h, entrees, sorties });
        }
    }

    /// le coin des cases (les places choisies à la main y sont relatives), sous les onglets et le titre des vagues
    fn origine(&self) -> (i32, i32) {
        (self.px(24) + self.decal.0, self.car_h * 2 + self.px(44) + self.decal.1)
    }

    /// la sortie qui donne une liaison : le point d'une case, ou celui d'une entrée de la réaction
    fn source_de(&self, nom: &str) -> Option<(i32, i32)> {
        let r = self.reaction()?;
        for c in &self.cases {
            if let Some(i) = r.atomes[c.atome].sorties.iter().position(|s| s == nom) {
                return Some(c.sorties[i]);
            }
        }
        self.entrees_r.iter().find(|e| e.0 == nom).map(|e| e.1)
    }

    fn etat_liaison(&self, nom: &str) -> Option<&(String, u8)> {
        let r = self.reaction()?;
        self.valeurs.get(&(r.nom.clone(), nom.to_string()))
    }

    /// le dessin : l'image, et les textes à écrire par-dessus
    pub fn dessiner(&mut self, l: usize, h: usize) -> (Image, Vec<TexteP>) {
        self.placer();
        let mut im = Image { l: l.max(1), h: h.max(1), px: vec![FOND; l.max(1) * h.max(1)] };
        let mut tx: Vec<TexteP> = Vec::new();
        let (cl, ch) = (self.car_l, self.car_h);
        let e1 = self.px(1).max(1);
        let e2 = self.px(2).max(2);
        // la grille de la paillasse
        let pas = self.px(24).max(8);
        let (ox, oy) = (self.decal.0.rem_euclid(pas), self.decal.1.rem_euclid(pas));
        for y in (oy..h as i32).step_by(pas as usize) {
            for x in (ox..l as i32).step_by(pas as usize) {
                im.point(x, y, GRILLE);
            }
        }
        // les onglets des réactions
        self.onglets.clear();
        let mut x = self.px(8);
        let ho = ch + self.px(10);
        if self.reactions.is_empty() {
            tx.push(TexteP { x: self.px(16), y: self.px(16), texte: "pas de réaction dans ce programme".into(), couleur: PALE });
            tx.push(TexteP { x: self.px(16), y: self.px(16) + ch + self.px(6),
                             texte: "double clic : une réaction neuve (reaction … { … }) s'écrit à la fin du texte".into(), couleur: PALE });
            return (im, tx);
        }
        for (k, r) in self.reactions.iter().enumerate() {
            let lo = (r.nom.chars().count() as i32 + 4) * cl;
            let actif = k == self.courante;
            im.plein(x, self.px(6), lo, ho, if actif { 0x2E3442 } else { BANDE });
            if actif {
                im.plein(x, self.px(6) + ho - e2, lo, e2, OR);
            }
            tx.push(TexteP { x: x + 2 * cl, y: self.px(6) + self.px(5), texte: r.nom.clone(), couleur: if actif { ENCRE } else { PALE } });
            self.onglets.push((x, self.px(6), lo, ho, k));
            x += lo + self.px(6);
        }
        let r = self.reactions[self.courante].clone();
        let y_haut = self.px(6) + ho + self.px(6);
        // les bandes des vagues
        for (k, &(v, xb, large)) in self.colonnes.clone().iter().enumerate() {
            if k % 2 == 1 {
                im.plein(xb, y_haut, large, h as i32 - y_haut, BANDE);
            }
            let titre = if v == 0 { "entrées".to_string() } else { format!("vague {}", v) };
            tx.push(TexteP { x: xb + self.px(12), y: y_haut + self.px(4), texte: titre, couleur: INCONNU });
        }
        // les contrats et les erreurs, en bas
        let mut yb = h as i32 - self.px(8) - ch;
        for e in r.erreurs.iter().rev() {
            tx.push(TexteP { x: self.px(12), y: yb, texte: e.clone(), couleur: FAUX });
            yb -= ch + self.px(4);
        }
        for (_, c) in r.contrats.iter().rev() {
            tx.push(TexteP { x: self.px(12), y: yb, texte: c.clone(), couleur: 0xE0A040 });
            yb -= ch + self.px(4);
        }
        // les liaisons : de la sortie qui les donne vers chaque entrée qui les lit
        for c in self.cases.clone() {
            let a = &r.atomes[c.atome];
            for (i, p) in a.entrees.iter().enumerate() {
                let b = c.entrees[i];
                if p.nom == "_" {
                    continue;
                }
                if let Some(s) = self.source_de(&p.nom) {
                    let (coul, pointille) = match self.etat_liaison(&p.nom).map(|v| v.1) {
                        Some(2) => (VRAI, false),
                        Some(1) => (FAUX, false),
                        Some(0) => (INCONNU, true),
                        Some(_) => (VARIABLE, false),
                        None => (PALE, false),
                    };
                    im.courbe(s, b, e2, coul, pointille);
                }
            }
        }
        // le résultat de la réaction : un trait vers la droite
        if let Some(res) = &r.resultat {
            if let Some(s) = self.source_de(res) {
                let fin = (s.0 + self.px(70), s.1);
                im.trait_(s, fin, e2, BRAISE, false);
                im.disque(fin.0, fin.1, self.px(5), BRAISE);
                tx.push(TexteP { x: fin.0 + self.px(10), y: fin.1 - ch / 2, texte: format!("rend {}", res), couleur: BRAISE });
            }
        }
        // les entrées de la réaction
        for (nom, (px, py)) in self.entrees_r.clone() {
            im.disque(px, py, self.px(6), 0x70B0A0);
            let mut t = nom.clone();
            if let Some((v, _)) = self.etat_liaison(&nom) {
                t = format!("{} = {}", nom, v);
            }
            tx.push(TexteP { x: px - self.px(12) - t.chars().count() as i32 * cl, y: py - ch / 2, texte: t, couleur: 0x70B0A0 });
        }
        // les cases
        for c in self.cases.clone() {
            let a = &r.atomes[c.atome];
            let coul = couleur_element(&a.element);
            let choisi = self.choisi == Some(c.atome);
            im.plein(c.x, c.y, c.l, c.h, 0x262B35);
            im.plein(c.x, c.y, c.l, ch + self.px(10), 0x303644);
            im.cadre(c.x, c.y, c.l, c.h, if choisi { e2 + e1 } else { e1 }, if choisi { OR } else { coul });
            // l'élément, dans un rond de sa couleur
            let rx = c.x + self.px(4) + ch / 2;
            let ry = c.y + (ch + self.px(10)) / 2;
            im.disque(rx, ry, ch / 2, coul);
            tx.push(TexteP { x: rx - cl * a.element.chars().count() as i32 / 2, y: ry - ch / 2, texte: a.element.clone(), couleur: 0x1B1E24 });
            let titre = if a.nom.is_empty() { format!("ligne {}", a.ligne + 1) } else { a.nom.clone() };
            tx.push(TexteP { x: rx + ch / 2 + self.px(6), y: c.y + self.px(5), texte: titre, couleur: ENCRE });
            let q: String = if a.quoi.chars().count() > 40 { a.quoi.chars().take(39).collect::<String>() + "…" } else { a.quoi.clone() };
            tx.push(TexteP { x: c.x + cl, y: c.y + ch + self.px(15), texte: q, couleur: 0xC8C4B8 });
            // les entrées (à gauche, leur nom dans la case) et les sorties (à droite, leur nom et leur valeur dehors)
            for (i, p) in a.entrees.iter().enumerate() {
                let (px_, py) = c.entrees[i];
                if p.nom == "_" {
                    im.anneau(px_, py, self.px(6), INCONNU);
                    tx.push(TexteP { x: px_ + self.px(10), y: py - ch / 2, texte: "_ libre".into(), couleur: INCONNU });
                } else {
                    im.disque(px_, py, self.px(5), PALE);
                    tx.push(TexteP { x: px_ + self.px(10), y: py - ch / 2, texte: p.nom.clone(), couleur: PALE });
                }
            }
            for (i, s) in a.sorties.iter().enumerate() {
                let (px_, py) = c.sorties[i];
                let coul_s = match self.etat_liaison(s).map(|v| v.1) {
                    Some(2) => VRAI,
                    Some(1) => FAUX,
                    Some(0) => INCONNU,
                    Some(_) => VARIABLE,
                    None => 0xE0A040,
                };
                im.disque(px_, py, self.px(6), coul_s);
                tx.push(TexteP { x: px_ + self.px(10), y: py - ch - self.px(2), texte: self.etiquette_sortie(s), couleur: coul_s });
            }
        }
        // le geste en cours
        match &self.geste {
            Some(Geste::Lier { de, a, .. }) | Some(Geste::Delier { de, a, .. }) => im.courbe(*de, *a, e2, OR, true),
            _ => {}
        }
        if let Some(m) = &self.message {
            tx.push(TexteP { x: self.px(12), y: h as i32 - self.px(8) - ch, texte: m.clone(), couleur: OR });
        }
        (im, tx)
    }

    fn case_sous(&self, x: i32, y: i32) -> Option<&Case> {
        self.cases.iter().rev().find(|c| x >= c.x && x < c.x + c.l && y >= c.y && y < c.y + c.h)
    }

    fn port_sous(&self, x: i32, y: i32, sortie: bool) -> Option<(usize, usize, (i32, i32))> {
        let r2 = (self.px(9)).pow(2);
        for c in &self.cases {
            let pts = if sortie { &c.sorties } else { &c.entrees };
            for (i, p) in pts.iter().enumerate() {
                if (p.0 - x).pow(2) + (p.1 - y).pow(2) <= r2 {
                    return Some((c.atome, i, *p));
                }
            }
        }
        None
    }

    /// la souris (x, y en pixels de la paillasse) ; source : le texte actuel
    pub fn souris(&mut self, genre: Souris, x: i32, y: i32, source: &str) -> Reponse {
        if self.cases.is_empty() && self.onglets.is_empty() {
            self.dessiner(800, 600);
        }
        match genre {
            Souris::Bas => {
                self.message = None;
                for &(ox, oy, ol, oh, k) in &self.onglets {
                    if x >= ox && x < ox + ol && y >= oy && y < oy + oh {
                        self.courante = k;
                        self.choisi = None;
                        return match self.reaction() {
                            Some(r) => Reponse::Aller(r.ligne),
                            None => Reponse::Redessiner,
                        };
                    }
                }
                if let Some((k, i, p)) = self.port_sous(x, y, true) {
                    let nom = self.reaction().unwrap().atomes[k].sorties[i].clone();
                    self.geste = Some(Geste::Lier { nom, de: p, a: (x, y) });
                    return Reponse::Redessiner;
                }
                for (nom, p) in self.entrees_r.clone() {
                    if (p.0 - x).pow(2) + (p.1 - y).pow(2) <= self.px(9).pow(2) {
                        self.geste = Some(Geste::Lier { nom, de: p, a: (x, y) });
                        return Reponse::Redessiner;
                    }
                }
                if let Some((k, i, p)) = self.port_sous(x, y, false) {
                    self.choisi = Some(k);
                    self.geste = Some(Geste::Delier { atome: k, port: i, de: p, a: (x, y) });
                    return Reponse::Redessiner;
                }
                if let Some(c) = self.case_sous(x, y).cloned() {
                    self.choisi = Some(c.atome);
                    self.geste = Some(Geste::Deplacer { atome: c.atome, dx: x - c.x, dy: y - c.y, x0: x, y0: y, bouge: false });
                    return Reponse::Redessiner;
                }
                self.choisi = None;
                self.geste = Some(Geste::Panoramique { x0: x, y0: y, d0: self.decal });
                Reponse::Redessiner
            }
            Souris::Bouge => {
                let echelle = self.echelle;
                let (ox, oy) = self.origine();
                let nom_r = self.reaction().map(|r| r.nom.clone());
                let cle = |p: &Paillasse, k: usize| p.reaction().map(|r| r.atomes[k].cle());
                match self.geste.clone() {
                    Some(Geste::Deplacer { atome, dx, dy, x0, y0, bouge }) => {
                        let bouge = bouge || (x - x0).abs() > 3 || (y - y0).abs() > 3;
                        if bouge {
                            let px = ((x - dx - ox) as f32 / echelle) as i32;
                            let py = ((y - dy - oy) as f32 / echelle) as i32;
                            if let (Some(n), Some(c)) = (nom_r, cle(self, atome)) {
                                self.positions.insert((n, c), (px, py));
                            }
                        }
                        self.geste = Some(Geste::Deplacer { atome, dx, dy, x0, y0, bouge });
                        Reponse::Redessiner
                    }
                    Some(Geste::Lier { nom, de, .. }) => {
                        self.geste = Some(Geste::Lier { nom, de, a: (x, y) });
                        Reponse::Redessiner
                    }
                    Some(Geste::Delier { atome, port, de, .. }) => {
                        self.geste = Some(Geste::Delier { atome, port, de, a: (x, y) });
                        Reponse::Redessiner
                    }
                    Some(Geste::Panoramique { x0, y0, d0 }) => {
                        self.decal = (d0.0 + x - x0, d0.1 + y - y0);
                        Reponse::Redessiner
                    }
                    None => Reponse::Rien,
                }
            }
            Souris::Haut => {
                let g = self.geste.take();
                let r = match self.reaction() {
                    Some(r) => r.clone(),
                    None => return Reponse::Redessiner,
                };
                match g {
                    Some(Geste::Deplacer { atome, bouge: false, .. }) => Reponse::Aller(r.atomes[atome].ligne),
                    Some(Geste::Lier { nom, .. }) => {
                        let cible = self.port_sous(x, y, false).map(|(k, i, _)| (k, Some(i)))
                            .or_else(|| self.case_sous(x, y).map(|c| (c.atome, None)));
                        match cible {
                            Some((k, port)) => match relier(source, &r.atomes[k], port, &nom) {
                                Ok(s) => {
                                    self.choisi = Some(k);
                                    Reponse::Texte { source: s, ligne: r.atomes[k].ligne }
                                }
                                Err(e) => {
                                    self.message = Some(e.clone());
                                    Reponse::Message(e)
                                }
                            },
                            None => Reponse::Redessiner,
                        }
                    }
                    Some(Geste::Delier { atome, port, de, .. }) => {
                        if (x - de.0).abs() <= self.px(9) && (y - de.1).abs() <= self.px(9) {
                            return Reponse::Aller(r.atomes[atome].ligne);
                        }
                        let nom = r.atomes[atome].entrees[port].nom.clone();
                        // posée sur l'entrée d'un autre atome : la liaison y va ; ailleurs : l'entrée redevient libre
                        let cible = self.port_sous(x, y, false).map(|(k, i, _)| (k, Some(i)))
                            .or_else(|| self.case_sous(x, y).map(|c| (c.atome, None)));
                        let mut s = match delier(source, &r.atomes[atome], port) {
                            Ok(s) => s,
                            Err(e) => return Reponse::Message(e),
                        };
                        if let (Some((k, p)), false) = (cible, nom == "_") {
                            if k != atome {
                                if let Ok(s2) = relier(&s, &r.atomes[k], p, &nom) {
                                    s = s2;
                                }
                            }
                        }
                        Reponse::Texte { source: s, ligne: r.atomes[atome].ligne }
                    }
                    _ => Reponse::Redessiner,
                }
            }
            Souris::Double => {
                self.geste = None;
                if self.reactions.is_empty() {
                    let (s, l) = ajouter_reaction(source);
                    return Reponse::Texte { source: s, ligne: l };
                }
                if let Some(c) = self.case_sous(x, y) {
                    let r = self.reaction().unwrap();
                    return Reponse::Aller(r.atomes[c.atome].ligne);
                }
                let r = self.reaction().unwrap().clone();
                let (s, l) = ajouter_atome(source, &r);
                // l'atome neuf vient où l'on a cliqué
                let nom = format!("l{}", {
                    let mut k = 1;
                    while r.params.contains(&format!("l{}", k)) || r.atomes.iter().any(|a| a.sorties.contains(&format!("l{}", k))) {
                        k += 1;
                    }
                    k
                });
                let (ox, oy) = self.origine();
                let px = ((x - ox) as f32 / self.echelle) as i32;
                let py = ((y - oy) as f32 / self.echelle) as i32;
                self.positions.insert((r.nom.clone(), nom), (px, py));
                Reponse::Texte { source: s, ligne: l }
            }
        }
    }

    /// une touche quand la paillasse a le clavier : Suppr retire l'atome choisi, Échap oublie le choix
    pub fn touche(&mut self, vk: u32, source: &str) -> Reponse {
        match vk {
            0x2E => {
                let (r, k) = match (self.reaction(), self.choisi) {
                    (Some(r), Some(k)) if k < r.atomes.len() => (r.clone(), k),
                    _ => return Reponse::Rien,
                };
                self.choisi = None;
                let l = r.atomes[k].ligne;
                Reponse::Texte { source: retirer_atome(source, &r.atomes[k]), ligne: l.saturating_sub(1) }
            }
            0x1B => {
                self.choisi = None;
                self.geste = None;
                Reponse::Redessiner
            }
            _ => Reponse::Rien,
        }
    }

    /// la fenêtre des explications : ce qu'est l'atome choisi, ou comment se servir de la paillasse
    pub fn explication(&self) -> String {
        let r = match self.reaction() {
            Some(r) => r,
            None => {
                return "La paillasse montre les réactions du programme : chaque atome est une case, chaque liaison un trait.\r\n\
                        Ce programme n'en a pas encore. Double-cliquez sur la paillasse : une réaction neuve s'écrit à la fin du \
                        texte."
                    .into()
            }
        };
        let mut t = String::new();
        match self.choisi.and_then(|k| r.atomes.get(k)) {
            Some(a) => {
                let nom_el = match a.element.chars().next() {
                    Some('H') => "hydrogène",
                    Some('O') => "oxygène",
                    Some('N') => "azote",
                    _ => "carbone",
                };
                let lues: Vec<&str> = a.entrees.iter().filter(|p| p.nom != "_").map(|p| p.nom.as_str()).collect();
                let libres = a.entrees.iter().filter(|p| p.nom == "_").count();
                t.push_str(&format!("{} — ligne {}\r\n", if a.nom.is_empty() { "un atome" } else { &a.nom }, a.ligne + 1));
                t.push_str(&format!("{} ({}), valence {} : il lit {} et donne {}.\r\n", a.element, nom_el, a.valence(),
                                    if lues.is_empty() { "rien".to_string() } else { lues.join(", ") },
                                    if a.sorties.is_empty() { "rien (un bout de chaîne)".to_string() } else { a.sorties.join(", ") }));
                t.push_str(&format!("Ce qu'il fait : {}\r\n", a.quoi));
                t.push_str(&format!("Vague {} : {}\r\n", a.vague, if lues.is_empty() && a.apres.is_empty() {
                    "il réagit tout de suite, avec les autres atomes sans entrée.".to_string()
                } else {
                    format!("il réagit dès que {} {} arrivée{}.", lues.join(" et "), if lues.len() > 1 { "sont" } else { "est" },
                            if lues.len() > 1 { "s" } else { "" })
                }));
                t.push_str(match a.genre {
                    Genre::Si => "Une condition : si le test est faux, sa liaison porte faux et la suite de la branche ne réagit pas.\r\n",
                    Genre::Pont => "Un pont vers le cube : c'est là que l'ordre compte ; deux ponts sur la même case gardent l'ordre des lignes.\r\n",
                    Genre::RendezVous => "Un rendez-vous : ses liaisons partent ensemble, quand toutes sont arrivées.\r\n",
                    Genre::Chaque => "Une vague d'atomes réduite en une liaison (somme, min, max) : partagée entre les cœurs une fois forgée.\r\n",
                    Genre::Effet => "Un bout de chaîne : il agit sur le monde (afficher, sortie) et ne donne pas de liaison.\r\n",
                    Genre::Calcul => "",
                });
                if libres > 0 {
                    t.push_str(&format!("{} entrée{} libre{} (« _ ») : tirez une liaison dessus depuis une sortie.\r\n", libres,
                                        if libres > 1 { "s" } else { "" }, if libres > 1 { "s" } else { "" }));
                }
                for s in &a.sorties {
                    if let Some((v, e)) = self.valeurs.get(&(r.nom.clone(), s.clone())) {
                        t.push_str(&match e {
                            2 => format!("{} = {} (vrai : arrivée, à la dernière réaction)\r\n", s, v),
                            1 => format!("{} porte faux : sa branche n'a pas réagi (la valeur calculée : {})\r\n", s, v),
                            0 => format!("{} : jamais calculée (inconnu)\r\n", s),
                            _ => format!("{} : variable : une erreur (une division par zéro) non réparée ; « reparer {} par … » la répare\r\n", s, s),
                        });
                    }
                }
            }
            None => {
                t.push_str(&format!("La réaction {} : {} atome{}, {} vague{}", r.nom, r.atomes.len(), if r.atomes.len() > 1 { "s" } else { "" },
                                    r.nb_vagues, if r.nb_vagues > 1 { "s" } else { "" }));
                if let Some(res) = &r.resultat {
                    t.push_str(&format!(", elle rend {}", res));
                }
                t.push_str(".\r\n");
                t.push_str("Glisser une case : la déplacer. Tirer d'une sortie (à droite d'une case) vers une case : lier (la \
                            liaison remplit son entrée libre « _ », ou l'entrée visée). Tirer une entrée vers le vide : délier.\r\n\
                            Double clic dans le vide : un atome neuf (« = _ -> l1 » s'écrit dans le texte). Suppr : retirer l'atome \
                            choisi. Glisser le vide : déplacer la paillasse.\r\n\
                            Ctrl+P : faire réagir avec la provenance ; chaque liaison montre alors sa valeur (vert : arrivée, rouge : \
                            sa branche n'a pas réagi, gris : jamais calculée).\r\n");
            }
        }
        for e in &r.erreurs {
            t.push_str(&format!("À corriger : {}\r\n", e));
        }
        t
    }

    /// le plan de la paillasse (pour les essais sans écran) : une ligne par case, « ligne x y l h | entrées | sorties »,
    /// puis les entrées de la réaction et les onglets
    pub fn plan(&self) -> String {
        let mut t = String::new();
        if let Some(r) = self.reaction() {
            for c in &self.cases {
                let pts = |v: &Vec<(i32, i32)>| v.iter().map(|p| format!("{},{}", p.0, p.1)).collect::<Vec<_>>().join(" ");
                t.push_str(&format!("case {} {} {} {} {} | {} | {}\n", r.atomes[c.atome].ligne + 1, c.x, c.y, c.l, c.h, pts(&c.entrees), pts(&c.sorties)));
            }
        }
        for (n, p) in &self.entrees_r {
            t.push_str(&format!("entree {} {},{}\n", n, p.0, p.1));
        }
        for &(x, y, l, h, k) in &self.onglets {
            t.push_str(&format!("onglet {} {} {} {} {}\n", self.reactions[k].nom, x, y, l, h));
        }
        t
    }

    /// les places choisies à la main, en texte (PROG.paillasse) : « réaction|clé|x|y » par ligne
    pub fn positions_texte(&self) -> String {
        let mut v: Vec<String> = self.positions.iter().map(|((r, c), (x, y))| format!("{}|{}|{}|{}", r, c, x, y)).collect();
        v.sort();
        v.join("\n") + "\n"
    }

    pub fn lire_positions(&mut self, t: &str) {
        self.positions.clear();
        for l in t.lines() {
            let c: Vec<&str> = l.rsplitn(3, '|').collect();
            if c.len() == 3 {
                if let (Ok(y), Ok(x)) = (c[0].parse::<i32>(), c[1].parse::<i32>()) {
                    if let Some((r, k)) = c[2].split_once('|') {
                        self.positions.insert((r.to_string(), k.to_string()), (x, y));
                    }
                }
            }
        }
    }
}

include!("police5x7.rs");

// ------------------------------------------------------------------------------------------------ vtx paillasse (sans écran)
/// vtx paillasse PROG.vtx [--png F.png] [--taille LxH] [--gestes FICHIER] [--ecrire]
/// Les gestes, un par ligne : « bas X Y », « bouge X Y », « haut X Y », « double X Y », « touche CODE », « ligne N »
/// (le curseur du texte va à la ligne N, à partir de 1), « png F.png » (une image à ce moment). À la fin : l'image
/// (--png), les explications, et le texte s'il a changé (écrit dans le fichier avec --ecrire, sinon montré).
pub fn commande(args: &[String]) {
    let fichier = match args.first() {
        Some(f) => f.clone(),
        None => {
            eprintln!("utilisation : vtx paillasse PROG.vtx [--png F.png] [--taille LxH] [--gestes FICHIER] [--ecrire]");
            std::process::exit(2);
        }
    };
    let (mut png, mut taille, mut gestes, mut ecrire, mut plan, mut valeurs) = (None, (1000usize, 640usize), None, false, false, false);
    let mut analyse = false;
    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--png" => png = args.get(i + 1).cloned(),
            "--taille" => {
                if let Some((a, b)) = args.get(i + 1).and_then(|t| t.split_once('x')) {
                    taille = (a.parse().unwrap_or(1000), b.parse().unwrap_or(640));
                }
            }
            "--gestes" => gestes = args.get(i + 1).cloned(),
            "--ecrire" | "--plan" | "--valeurs" | "--analyse" => {
                match args[i].as_str() {
                    "--plan" => plan = true,
                    "--analyse" => analyse = true,
                    "--valeurs" => valeurs = true,
                    _ => ecrire = true,
                }
                i += 1;
                continue;
            }
            autre => {
                eprintln!("option inconnue : {}", autre);
                std::process::exit(2);
            }
        }
        i += 2;
    }
    let mut source = std::fs::read_to_string(&fichier).unwrap_or_else(|e| {
        eprintln!("lecture de {} impossible : {}", fichier, e);
        std::process::exit(1)
    });
    let original = source.clone();
    let mut p = Paillasse::nouvelle();
    p.car_l = 6;
    p.car_h = 12;
    let place = format!("{}.paillasse", fichier.trim_end_matches(".vtx"));
    if let Ok(t) = std::fs::read_to_string(&place) {
        p.lire_positions(&t);
    }
    p.lire(&source);
    if valeurs {
        // Ctrl+P de l'atelier : le programme compilé avec la provenance et lancé ; chaque liaison porte sa valeur
        let base = super::machine128::dossier_de128(&fichier);
        match super::machine128::valeurs_liaisons(&source, &base, &[]) {
            Ok(v) => p.valeurs = v,
            Err(e) => print!("{}", e),
        }
    }
    let image = |p: &mut Paillasse, f: &str| {
        let (mut im, tx) = p.dessiner(taille.0, taille.1);
        ecrire_textes(&mut im, &tx, p.car_l, p.car_h);
        if let Err(e) = std::fs::write(f, super::sortie::png_de(&im.px, im.l, im.h)) {
            eprintln!("{} : {}", f, e);
        }
    };
    p.dessiner(taille.0, taille.1);
    if let Some(g) = gestes {
        let t = std::fs::read_to_string(&g).unwrap_or_default();
        for l in t.lines() {
            let m: Vec<&str> = l.split('#').next().unwrap_or("").split_whitespace().collect();
            if m.is_empty() {
                continue;
            }
            let n = |k: usize| m.get(k).and_then(|v| v.parse::<i32>().ok()).unwrap_or(0);
            let rep = match m[0] {
                "bas" => p.souris(Souris::Bas, n(1), n(2), &source),
                "bouge" => p.souris(Souris::Bouge, n(1), n(2), &source),
                "haut" => p.souris(Souris::Haut, n(1), n(2), &source),
                "double" => p.souris(Souris::Double, n(1), n(2), &source),
                "touche" => p.touche(n(1) as u32, &source),
                "ligne" => {
                    p.choisir_ligne((n(1) - 1).max(0) as usize);
                    Reponse::Redessiner
                }
                "png" => {
                    image(&mut p, m.get(1).copied().unwrap_or("paillasse.png"));
                    Reponse::Rien
                }
                "plan" => {
                    print!("{}", p.plan());
                    Reponse::Rien
                }
                autre => {
                    eprintln!("geste inconnu : {}", autre);
                    Reponse::Rien
                }
            };
            match rep {
                Reponse::Texte { source: s, ligne } => {
                    source = s;
                    p.lire(&source);
                    println!("texte réécrit (ligne {})", ligne + 1);
                }
                Reponse::Aller(l) => println!("aller à la ligne {}", l + 1),
                Reponse::Message(m) => println!("message : {}", m),
                _ => {}
            }
            p.dessiner(taille.0, taille.1);
        }
    }
    if let Some(f) = png {
        image(&mut p, &f);
    }
    if plan {
        print!("{}", p.plan());
    }
    if analyse {
        // la lecture : « réaction|ligne|nom|élément|vague|entrées|sorties » par atome, puis les erreurs
        for r in &p.reactions {
            for a in &r.atomes {
                let e: Vec<&str> = a.entrees.iter().map(|x| x.nom.as_str()).collect();
                println!("atome {}|{}|{}|{}|{}|{}|{}", r.nom, a.ligne + 1, a.nom, a.element, a.vague, e.join(","), a.sorties.join(","));
            }
            for e in &r.erreurs {
                println!("erreur {}|{}", r.nom, e);
            }
        }
    }
    println!("--- explications\n{}", p.explication().replace("\r\n", "\n").trim_end());
    if !p.positions.is_empty() {
        let _ = std::fs::write(&place, p.positions_texte());
    }
    if source != original {
        if ecrire {
            std::fs::write(&fichier, &source).expect("écriture impossible");
            println!("--- {} réécrit", fichier);
        } else {
            println!("--- le texte\n{}", source);
        }
    }
}
