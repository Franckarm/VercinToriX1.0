// La paillasse : la surface des réactions, au centre d'Ogmios (docs/vtx-chimie.md, docs/vtx-reactions.md).
//
// Une réaction y est dessinée comme une molécule : chaque atome est une case (son élément, déduit de la valence : H, O, N,
// C), chaque liaison un trait d'une sortie (à droite d'une case) vers une entrée (à gauche) ; les cases sont rangées par
// vagues, de gauche à droite. La paillasse et le texte sont le même programme, dans les deux sens :
//   - le texte change : la paillasse est relue (sans compiler : une lecture des lignes de la réaction, qui garde ce qui
//     n'est pas encore juste, comme une entrée libre « _ », une liaison inconnue) ;
//   - sur la paillasse, on déplace une case, on tire une liaison d'une sortie vers une case (elle remplit son entrée
//     libre « _ », ou remplace l'entrée visée), on tire une entrée vers le vide (elle redevient « _ »), on ajoute un
//     atome (double clic dans le vide : la ligne « = _ -> l1 » s'écrit dans la réaction), on en retire un (Suppr),
//     on pose ou on édite une case au clic droit (une petite boîte sur la case : Entrée récrit sa ligne) :
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
    /// l'isotope lourd (« -> a lourd ») : la liaison est critique, la réaction garde ses neutrons dans l'ADN
    pub lourd: bool,
    /// 0.69 : la famille de la case (S, Si, Fe, Mg…), lue dans ce qu'elle fait ; vide : une case de structure seule.
    /// L'élément (H, O, N, C, par la valence) reste celui de la molécule de registre
    pub famille: String,
    /// 0.70 : la page (une autre réaction du texte) vers laquelle cette case renvoie sa valeur, s'il y en a une
    pub vers: Option<String>,
    /// 0.70b : la page (la réaction qui appelle celle-ci) vers laquelle cette case renvoie le résultat : le retour
    pub retour: Option<String>,
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
    /// la carte du programme (pas une réaction) : une case par fonction, une liaison par appel ; on la regarde, on y
    /// choisit une fonction, on n'y réécrit pas le texte
    pub carte: bool,
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

// ------------------------------------------------------------------------------------------------ la palette des cases
/// 0.69 : une case de la palette. Les quatre éléments de structure (H, O, N, C) viennent de la valence et composent la
/// molécule de registre ; les autres éléments nomment la famille de ce que fait la case. Le modèle s'écrit dans la
/// réaction : « _ » est une entrée libre (on y tire une liaison), « @ » la liaison qu'elle donne, « # » une seconde.
pub struct CasePalette {
    pub symbole: &'static str,
    pub element: &'static str,
    pub famille: &'static str,
    pub nom: &'static str,
    pub modele: &'static str,
    pub aide: &'static str,
}

pub const PALETTE: &[CasePalette] = &[
    CasePalette { symbole: "C", element: "carbone", famille: "calcul", nom: "addition", modele: "= _ + _ -> @",
                  aide: "additionne deux liaisons (aussi -, *, /, %) ; la case la plus simple" },
    CasePalette { symbole: "C", element: "carbone", famille: "calcul", nom: "comparaison", modele: "= _ < _ -> @",
                  aide: "compare deux valeurs : une logique de Belnap, vraie, fausse, inconnue ou variable" },
    CasePalette { symbole: "S", element: "soufre", famille: "logique", nom: "fusion", modele: "= fusion(_, _) -> @",
                  aide: "rassemble deux témoignages : deux contraires donnent variable, la contradiction est gardée" },
    CasePalette { symbole: "S", element: "soufre", famille: "logique", nom: "et4", modele: "= et4(_, _) -> @",
                  aide: "le et des quatre valeurs : un faux l'emporte, un inconnu reste inconnu" },
    CasePalette { symbole: "S", element: "soufre", famille: "logique", nom: "anti", modele: "= anti(_) -> @",
                  aide: "l'antiparticule : vrai et faux s'échangent, inconnu et variable restent" },
    CasePalette { symbole: "Si", element: "silicium", famille: "condition", nom: "garder", modele: "= si _ alors _ -> @",
                  aide: "garde la valeur si le test est vrai ; sinon la liaison porte faux et sa branche ne réagit pas" },
    CasePalette { symbole: "Si", element: "silicium", famille: "condition", nom: "choisir", modele: "= si _ alors _ sinon _ -> @",
                  aide: "choisit entre deux valeurs selon le test" },
    CasePalette { symbole: "Fe", element: "fer", famille: "mémoire du cube", nom: "lire_cube", modele: "= @3[_] -> @",
                  aide: "lit une case du cube (étage 3, l'adresse en entrée) : un pont, l'ordre des lignes y compte" },
    CasePalette { symbole: "Fe", element: "fer", famille: "mémoire du cube", nom: "ecrire_cube", modele: "@3[_] = _",
                  aide: "écrit une valeur dans une case du cube : un pont et un bout de chaîne" },
    CasePalette { symbole: "Mg", element: "magnésium", famille: "vague", nom: "chaque", modele: "= pour chaque v dans _ : v * 2 -> @",
                  aide: "applique un calcul à chaque élément d'un tableau, tous ensemble, sur plusieurs cœurs" },
    CasePalette { symbole: "Mg", element: "magnésium", famille: "vague", nom: "somme", modele: "= somme pour chaque v dans _ : v -> @",
                  aide: "réduit une vague en une valeur (aussi min, max) : un arbre de rendez-vous" },
    CasePalette { symbole: "Mg", element: "magnésium", famille: "vague", nom: "garder_dans", modele: "= garder v dans _ si v > 0 -> @",
                  aide: "filtre un tableau : ne garde que les éléments qui passent le test" },
    CasePalette { symbole: "K", element: "potassium", famille: "rendez-vous", nom: "rendez_vous", modele: "= rendez-vous(_, _) -> @, #",
                  aide: "attend que toutes ses liaisons soient arrivées, puis les laisse partir ensemble" },
    CasePalette { symbole: "F", element: "fluor", famille: "conversion", nom: "en_flottant", modele: "= flottant(_) -> @",
                  aide: "un entier devient flottant (aussi entier(), entier_32(), flottant_32())" },
    CasePalette { symbole: "F", element: "fluor", famille: "conversion", nom: "en_entier", modele: "= entier(_) -> @",
                  aide: "un flottant devient entier (la partie entière)" },
    CasePalette { symbole: "P", element: "phosphore", famille: "mesure", nom: "racine", modele: "= racine(_) -> @",
                  aide: "la racine carrée d'un flottant (aussi sinus, cosinus, logarithme, puissance)" },
    CasePalette { symbole: "Au", element: "or", famille: "calcul exact", nom: "fma", modele: "= multiplier_ajouter(_, _, _) -> @",
                  aide: "a × b + c avec un seul arrondi : le calcul exact, celui des sommes qui ne dérivent pas" },
    CasePalette { symbole: "Zn", element: "zinc", famille: "réparation", nom: "reparer", modele: "= reparer _ / _ par 0 -> @",
                  aide: "le zinc protège le fer : une division par zéro (variable) est réparée par la valeur de secours" },
    CasePalette { symbole: "Ar", element: "argon", famille: "hasard", nom: "hasard", modele: "= hasard(_) -> @",
                  aide: "un nombre au hasard de 0 à n - 1 (graine(n) le rend reproductible)" },
    CasePalette { symbole: "Ca", element: "calcium", famille: "temps", nom: "horloge", modele: "= horloge() -> @",
                  aide: "l'heure de la machine : mesurer la durée d'une vague" },
    CasePalette { symbole: "Na", element: "sodium", famille: "données", nom: "tableau", modele: "= [1, 2, 3] -> @",
                  aide: "un tableau écrit, la source d'une vague" },
    CasePalette { symbole: "Na", element: "sodium", famille: "données", nom: "element", modele: "= _[_] -> @",
                  aide: "lit un élément d'un tableau" },
    CasePalette { symbole: "Cl", element: "chlore", famille: "écran", nom: "afficher", modele: "= afficher(_)",
                  aide: "montre une valeur à l'écran : un bout de chaîne, il ne donne pas de liaison" },
    CasePalette { symbole: "Ne", element: "néon", famille: "fin", nom: "fin", modele: "= _ -> !",
                  aide: "la fin de la réaction : la liaison qu'elle rend (son « -> r »), ou la sortie du programme \
                         (sortie(_)) si elle ne rend rien ; le néon, l'enseigne qui dit que c'est fini" },
    CasePalette { symbole: "Ne", element: "néon", famille: "fin", nom: "appeler", modele: "= >(_) -> @",
                  aide: "appelle la page suivante comme un sous-programme (créée s'il n'y en a pas) : sa valeur y part, \
                         et le résultat de la page revient dans une liaison neuve ; la réaction continue" },
    CasePalette { symbole: "Ne", element: "néon", famille: "fin", nom: "suite", modele: "= >(_) -> !",
                  aide: "la fin qui renvoie à la page suivante : sa valeur part dans l'onglet d'après (créé s'il n'existe \
                         pas), qui la reçoit en entrée ; la case dit le nom de la page, un double clic l'ouvre" },
];

/// la famille d'une case, lue dans ce qu'elle fait (le symbole de son élément), vide pour une case de structure seule
pub fn famille_de(quoi: &str) -> &'static str {
    let q = quoi.trim().trim_start_matches('=').trim();
    let debut = |m: &[&str]| m.iter().any(|x| q.starts_with(x));
    if debut(&["fusion(", "et4(", "ou4(", "anti(", "comme_logique("]) {
        "S"
    } else if debut(&["si ", "selon "]) {
        "Si"
    } else if q.contains("@3[") || q.contains("@2[") || q.contains("@1[") {
        "Fe"
    } else if debut(&["pour chaque", "somme pour", "min pour", "max pour", "garder "]) {
        "Mg"
    } else if debut(&["rendez-vous", "rendezvous"]) {
        "K"
    } else if debut(&["flottant(", "entier(", "entier_32(", "flottant_32(", "flottant_64(", "entier_petuar(", "flottant_petuar("]) {
        "F"
    } else if debut(&["racine(", "sinus(", "cosinus(", "tangente(", "logarithme(", "exponentielle(", "puissance(", "absolu("]) {
        "P"
    } else if debut(&["multiplier_ajouter("]) {
        "Au"
    } else if debut(&["reparer "]) {
        "Zn"
    } else if debut(&["hasard(", "bruit(", "graine("]) {
        "Ar"
    } else if debut(&["horloge("]) {
        "Ca"
    } else if q.starts_with('[') {
        "Na"
    } else if debut(&["sortie("]) {
        "Ne"
    } else if debut(&["afficher(", "ecrire("]) {
        "Cl"
    } else {
        ""
    }
}

fn nom_element(e: &str) -> &'static str {
    match e {
        "H" => "hydrogène",
        "O" => "oxygène",
        "N" => "azote",
        s if s.starts_with('C') && s.len() <= 3 && s[1..].chars().all(|c| c.is_ascii_digit()) => "carbone",
        s => PALETTE.iter().find(|c| c.symbole == s).map(|c| c.element).unwrap_or("carbone"),
    }
}

/// la palette expliquée : les éléments de structure, puis chaque case, famille par famille
pub fn texte_palette() -> String {
    let mut t = String::from("Les cases de la paillasse (menu Cases d'Ogmios, ou « poser NOM »).\r\n\
        Structure, par la valence (le nombre de liaisons) : H hydrogène 1, O oxygène 2, N azote 3, C carbone 4 ; ce sont \
        eux qui composent la molécule de registre rangée dans le cube.\r\n\
        Les familles, par ce que fait la case : « _ » est une entrée libre, on y tire une liaison.\r\n");
    let mut famille = "";
    for c in PALETTE {
        if c.famille != famille {
            famille = c.famille;
            t.push_str(&format!("{} {} — {}\r\n", c.symbole, c.element, c.famille));
        }
        t.push_str(&format!("    {:<12} {:<38} {}\r\n", c.nom, c.modele, c.aide));
    }
    t
}

/// poser une case de la palette dans une réaction : sa ligne à la fin, ses liaisons nommées lK (et lK+1)
pub fn poser_modele(source: &str, r: &Reaction, c: &CasePalette) -> (String, usize) {
    let pris = |n: &str| r.params.iter().any(|p| p == n) || r.atomes.iter().any(|a| a.sorties.iter().any(|s| s == n));
    let mut k = 1;
    while pris(&format!("l{}", k)) || pris(&format!("l{}", k + 1)) {
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
    v.insert(place, format!("{}{}{}", retrait, ligne_du_modele(c, Some(r), k), cr));
    (v.join("\n"), place)
}

/// la ligne d'une case : « @ » la liaison lK, « # » lK+1, « ! » le résultat de la réaction (sans résultat : la sortie)
pub fn ligne_du_modele(c: &CasePalette, r: Option<&Reaction>, k: usize) -> String {
    if c.modele.contains('!') {
        return match r.and_then(|r| r.resultat.clone()) {
            Some(res) => c.modele.replace('!', &res),
            None => "= sortie(_)".into(),
        };
    }
    let ligne = c.modele.replace('#', &format!("l{}", k + 1)).replace('@', &format!("l{}", k));
    // « @3[ » n'est pas une liaison : le modèle l'écrit tel quel
    ligne.replace(&format!("l{}3[", k), "@3[")
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

/// 0.70 : une case qui appelle une autre réaction du texte renvoie vers cette page (le néon, la fin qui continue)
fn noter_renvois(rs: &mut [Reaction]) {
    let noms: Vec<String> = rs.iter().filter(|r| !r.carte).map(|r| r.nom.clone()).collect();
    for r in rs.iter_mut().filter(|r| !r.carte) {
        let ici = r.nom.clone();
        for a in r.atomes.iter_mut() {
            let q = a.quoi.trim().trim_start_matches('=').trim();
            let q = q.strip_prefix("sortie(").unwrap_or(q);
            if let Some(n) = noms.iter().find(|n| **n != ici && q.starts_with(&format!("{}(", n))) {
                a.vers = Some(n.clone());
                a.famille = "Ne".into();
            }
        }
    }
    // 0.70b : la page appelée : la case qui donne son résultat retourne vers la (première) page qui l'appelle
    let appels: Vec<(String, String)> = rs.iter().filter(|r| !r.carte)
        .flat_map(|r| r.atomes.iter().filter_map(|a| a.vers.clone()).map(move |v| (v, r.nom.clone()))).collect();
    for r in rs.iter_mut().filter(|r| !r.carte) {
        let appelant = appels.iter().find(|(v, _)| *v == r.nom).map(|(_, a)| a.clone());
        if let (Some(res), Some(ap)) = (r.resultat.clone(), appelant) {
            for a in r.atomes.iter_mut().filter(|a| a.sorties.contains(&res)) {
                a.retour = Some(ap.clone());
                a.famille = "Ne".into();
            }
        }
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
                               erreurs: vec![], nb_vagues: 0, carte: false };
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
    noter_renvois(&mut out);
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
    let mut lourd = false;
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
                let mut mots_s = morceau.split_whitespace();
                let n = morceau.split(':').next().unwrap_or("").split_whitespace().next().unwrap_or("");
                if !n.is_empty() {
                    sorties.push(n.to_string());
                }
                if mots_s.any(|w| w == "lourd") {
                    lourd = true;
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
                          apres, genre, vague: 0, element: String::new(), lourd, famille: String::new(),
                          vers: None, retour: None });
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
    let resultat = r.resultat.clone();
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
        a.famille = famille_de(&a.quoi).to_string();
        if resultat.as_ref().map_or(false, |res| a.sorties.contains(res)) {
            a.famille = "Ne".into();     // 0.69b : la case qui donne le résultat de la réaction : la fin
        }
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

// ------------------------------------------------------------------------------------------------ la carte du programme
/// La carte d'un programme : chaque fonction est une case (son élément : sa valence, comme un atome), chaque appel une
/// liaison de la fonction appelée (à gauche) vers celle qui l'appelle (à droite) : le programme se lit comme une molécule,
/// des feuilles (qui n'appellent rien) jusqu'à principal. Les vagues : la profondeur des appels (un appel récursif ne
/// compte pas). None : le texte n'a pas de fonction.
pub fn carte(source: &str) -> Option<Reaction> {
    let lignes: Vec<&str> = source.split('\n').collect();
    // les fonctions : leur nom, leurs paramètres, leurs lignes (de l'en-tête à l'accolade fermante)
    let mut fonctions: Vec<(String, String, usize, usize)> = Vec::new();
    let mut i = 0;
    while i < lignes.len() {
        let l = lignes[i].trim_end_matches('\r');
        let t = l.trim_start();
        if let Some(reste) = t.strip_prefix("fonction ") {
            let nom: String = reste.trim_start().chars().take_while(|&c| lettre(c)).collect();
            if !nom.is_empty() {
                let sig = reste.split('{').next().unwrap_or("").trim().to_string();
                let mut prof = 0i32;
                let mut vu = false;
                let mut j = i;
                'tout: while j < lignes.len() {
                    let lj = lignes[j];
                    let code = &lj[..fin_code(lj)];
                    let mut dans = false;
                    for c in code.chars() {
                        match c {
                            '"' => dans = !dans,
                            '{' if !dans => {
                                prof += 1;
                                vu = true;
                            }
                            '}' if !dans => {
                                prof -= 1;
                                if vu && prof == 0 {
                                    break 'tout;
                                }
                            }
                            _ => {}
                        }
                    }
                    j += 1;
                }
                let fin = j.min(lignes.len().saturating_sub(1));
                fonctions.push((nom, sig, i, fin));
                i = fin + 1;
                continue;
            }
        }
        i += 1;
    }
    if fonctions.is_empty() {
        return None;
    }
    let noms: HashMap<String, usize> = fonctions.iter().enumerate().map(|(k, f)| (f.0.clone(), k)).collect();
    // les appels : un nom de fonction du programme suivi de « ( », hors des textes et des commentaires
    let mut appels: Vec<Vec<usize>> = vec![vec![]; fonctions.len()];
    for (k, f) in fonctions.iter().enumerate() {
        for lj in &lignes[f.2..=f.3] {
            let code = &lj[..fin_code(lj)];
            let b: Vec<char> = code.chars().collect();
            let mut dans = false;
            let mut x = 0;
            while x < b.len() {
                if b[x] == '"' {
                    dans = !dans;
                    x += 1;
                    continue;
                }
                if !dans && lettre(b[x]) && (x == 0 || !lettre(b[x - 1])) {
                    let d = x;
                    while x < b.len() && lettre(b[x]) {
                        x += 1;
                    }
                    let mot: String = b[d..x].iter().collect();
                    let mut y = x;
                    while y < b.len() && b[y] == ' ' {
                        y += 1;
                    }
                    let entete = d >= 9 && b[..d].iter().collect::<String>().trim_end().ends_with("fonction");
                    if y < b.len() && b[y] == '(' && !entete {
                        if let Some(&c) = noms.get(&mot) {
                            if !appels[k].contains(&c) {
                                appels[k].push(c);
                            }
                        }
                    }
                    continue;
                }
                x += 1;
            }
        }
    }
    let mut atomes: Vec<Atome> = fonctions.iter().enumerate().map(|(k, f)| {
        let entrees: Vec<Port> = appels[k].iter().filter(|&&c| c != k).map(|&c| Port { nom: fonctions[c].0.clone(), places: vec![] }).collect();
        let mut a = Atome { ligne: f.2, nom: f.0.clone(), quoi: format!("fonction {}", f.1), sorties: vec![f.0.clone()], entrees,
                            apres: vec![], genre: Genre::Calcul, vague: 0, element: String::new(), lourd: false,
                            famille: String::new(), vers: None, retour: None };
        a.element = element_de(a.valence());
        a
    }).collect();
    // les vagues : 1 pour une fonction qui n'appelle rien, sinon une de plus que la plus profonde qu'elle appelle
    let n = atomes.len();
    let mut vague = vec![0usize; n];
    let mut etat = vec![0u8; n];
    fn visiter(k: usize, appels: &[Vec<usize>], vague: &mut [usize], etat: &mut [u8]) -> usize {
        if etat[k] == 2 {
            return vague[k];
        }
        if etat[k] == 1 {
            return 0;
        }
        etat[k] = 1;
        let mut v = 1;
        for &d in &appels[k] {
            if d != k {
                v = v.max(visiter(d, appels, vague, etat) + 1);
            }
        }
        etat[k] = 2;
        vague[k] = v;
        v
    }
    for k in 0..n {
        visiter(k, &appels, &mut vague, &mut etat);
    }
    for (k, a) in atomes.iter_mut().enumerate() {
        a.vague = vague[k];
    }
    Some(Reaction { nom: "le programme".into(), ligne: 0, fin: lignes.len().saturating_sub(1), params: vec![], resultat: None,
                    atomes, contrats: vec![], erreurs: vec![], nb_vagues: vague.iter().copied().max().unwrap_or(0), carte: true })
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

/// éditer une case : sa ligne devient « texte », au même retrait (le texte tapé dans la boîte du clic droit)
pub fn editer_ligne(source: &str, ligne: usize, texte: &str) -> String {
    let l = source.split('\n').nth(ligne).unwrap_or("").trim_end_matches('\r');
    let retrait = &l[..l.len() - l.trim_start().len()];
    let t = texte.trim().replace(['\r', '\n'], " ");
    remplacer_ligne(source, ligne, &format!("{}{}", retrait, t))
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
/// 0.70 : la ligne où écrire une case de la vague v : avant la première case (dans l'ordre des lignes) d'une vague plus
/// tardive, sinon à la fin de la réaction ; « sauf » : la case qu'on déplace
pub fn ligne_pour_vague(r: &Reaction, v: usize, sauf: Option<usize>) -> usize {
    let mut ordre: Vec<usize> = (0..r.atomes.len()).filter(|&k| Some(k) != sauf).collect();
    ordre.sort_by_key(|&k| r.atomes[k].ligne);
    ordre.iter().find(|&&k| r.atomes[k].vague > v).map(|&k| r.atomes[k].ligne).unwrap_or(r.fin)
}

/// 0.70b : les lignes des cases de la réaction réécrites dans l'ordre donné (les places des lignes de cases ne
/// changent pas, seulement ce qui y est écrit) ; rend le texte et la nouvelle ligne de la case « suivie »
pub fn ordonner_lignes(source: &str, r: &Reaction, ordre: &[usize], suivie: usize) -> (String, usize) {
    let mut v: Vec<String> = source.split('\n').map(|x| x.to_string()).collect();
    let mut places: Vec<usize> = r.atomes.iter().map(|a| a.ligne).collect();
    places.sort();
    places.dedup();
    if places.len() != r.atomes.len() || ordre.len() != r.atomes.len() || places.iter().any(|&p| p >= v.len()) {
        return (source.to_string(), r.atomes[suivie].ligne);
    }
    let textes: Vec<String> = ordre.iter().map(|&k| v[r.atomes[k].ligne].clone()).collect();
    let mut ligne = r.atomes[suivie].ligne;
    for (i, &p) in places.iter().enumerate() {
        v[p] = textes[i].clone();
        if ordre[i] == suivie {
            ligne = p;
        }
    }
    (v.join("\n"), ligne)
}

/// 0.70 : déplacer la ligne « de » pour qu'elle vienne juste avant la ligne « avant » (des places du texte d'origine) ;
/// rend le texte et la nouvelle place de la ligne
pub fn deplacer_ligne(source: &str, de: usize, avant: usize) -> (String, usize) {
    let mut v: Vec<String> = source.split('\n').map(|x| x.to_string()).collect();
    if de >= v.len() || avant == de || avant == de + 1 {
        return (source.to_string(), de);
    }
    let l = v.remove(de);
    let place = if avant > de { avant - 1 } else { avant };
    v.insert(place.min(v.len()), l);
    (v.join("\n"), place)
}

/// 0.70 : une page neuve (une réaction qui reçoit une valeur et la rend) : « reaction page_N(entree) -> fin » ; rend le
/// texte, la ligne de sa première case et son nom
pub fn ajouter_page(source: &str) -> (String, usize, String) {
    let noms: Vec<String> = analyser(source).into_iter().map(|r| r.nom).collect();
    let mut k = noms.len() + 1;
    let mut nom = format!("page_{}", k);
    while noms.contains(&nom) || source.contains(&format!("fonction {}(", nom)) {
        k += 1;
        nom = format!("page_{}", k);
    }
    let cr = if source.contains("\r\n") { "\r\n" } else { "\n" };
    let mut t = source.trim_end().to_string();
    if !t.is_empty() {
        t.push_str(cr);
        t.push_str(cr);
    }
    let ligne = t.split('\n').count() - 1;
    t.push_str(&format!("// la page {} : elle reçoit « entree » de la page d'avant{}reaction {}(entree) -> fin {{{}    \
                         = entree -> fin{}}}{}", nom, cr, nom, cr, cr, cr));
    (t, ligne + 2, nom)
}

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
    // 0.69 : les familles de la palette, chacune sa couleur
    match e {
        "S" => return 0xE8D040,
        "Si" => return 0x40B8B0,
        "Fe" => return 0xC07040,
        "Mg" => return 0x90D060,
        "K" => return 0xB070E0,
        "F" => return 0x70D8E8,
        "P" => return 0xF09040,
        "Au" => return OR,
        "Zn" => return 0x8890A0,
        "Ar" => return 0x6890E0,
        "Ca" => return 0xF0E8D0,
        "Na" => return 0xA8A0F0,
        "Ne" => return 0xFF5A8C,
        "Cl" => return 0x60D060,
        _ => {}
    }
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
    /// 0.72 : la colonne (la vague) où la case est rangée
    col: usize,
    x: i32,
    y: i32,
    l: i32,
    h: i32,
    entrees: Vec<(i32, i32)>,
    sorties: Vec<(i32, i32)>,
}

#[derive(Clone)]
enum Geste {
    /// 0.72 : (mx, my) la souris ; cible : la colonne et le rang où la case tomberait si on la lâchait
    Deplacer { atome: usize, dx: i32, dy: i32, x0: i32, y0: i32, bouge: bool, mx: i32, my: i32, cible: Option<(usize, usize)> },
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
    /// le clic droit : écrire le texte d'une case dans une petite boîte posée sur elle (en x, y de la paillasse) ;
    /// source : le texte réécrit d'abord (une case neuve posée là), ligne : la ligne qu'Entrée remplacera
    Editer { source: Option<String>, ligne: usize, texte: String, x: i32, y: i32 },
    /// 0.69b : le clic droit dans le vide d'une réaction : montrer le menu des cases en (x, y) ; le choix va à poser_ici
    Palette { x: i32, y: i32 },
}

pub enum Souris {
    Bas,
    Bouge,
    Haut,
    Double,
    /// le clic droit : sur une case, l'éditer ; dans le vide, le menu des cases (Reponse::Palette), puis poser_ici
    Droit,
}

/// Les six faces de chaque fonction (0.6q), lues dans l'ADN rangé à côté du programme (la section « faces » écrite par
/// le lecteur en vtx), et le centre de chacune : son état à la lecture de cet ADN.
#[derive(Clone, Debug, Default)]
pub struct Faces {
    /// le nom -> les dix-sept champs de sa ligne
    pub lignes: HashMap<String, Vec<String>>,
    /// le début de chaque molécule -> son nom (ou « la tête », « mN »)
    pub noms: HashMap<usize, String>,
    /// le début de chaque molécule -> son état à la lecture (2 vrai, 1 réparée, 3 variable)
    pub centres: HashMap<usize, u8>,
    /// le texte gardé dans l'ADN (pour savoir si la carte date d'avant la dernière retouche)
    pub source: String,
}

impl Faces {
    /// lire les faces d'un ADN (et le vérifier, pour le centre) ; None s'il n'a pas de faces
    pub fn depuis_adn(chemin: &str) -> Option<Faces> {
        let texte = std::fs::read_to_string(chemin).ok()?.replace("\r\n", "\n");
        let l: Vec<&str> = texte.split('\n').collect();
        let section = |nom: &str| -> Option<Vec<String>> {
            let tete = format!("GU {} ", nom);
            let i = l.iter().position(|x| x.starts_with(&tete))?;
            let n: usize = l[i][tete.len()..].trim().parse().ok()?;
            Some(l.get(i + 1..i + 1 + n)?.iter().map(|x| x.to_string()).collect())
        };
        let lignes = section("faces")?;
        let mut f = Faces { source: section("source").map(|v| v.join("\n")).unwrap_or_default(), ..Default::default() };
        for x in &lignes {
            let c: Vec<String> = x.splitn(17, '|').map(|y| y.to_string()).collect();
            if c.len() < 17 {
                continue;
            }
            let deb: usize = c[0].trim_start_matches('m').parse().unwrap_or(0);
            let nom = if !c[1].is_empty() { c[1].clone() } else if c[2] == "tete" { "la tête".into() } else { c[0].clone() };
            f.noms.insert(deb, nom.clone());
            if !c[1].is_empty() {
                f.lignes.insert(nom, c);
            }
        }
        if let Ok((mut mots, mols, mut t)) = crate::adn::lire_adn(chemin) {
            let (_, rapport) = crate::adn::lire(&mut mots, &mols, &mut t);
            for m in &mols {
                f.centres.insert(m.debut, crate::adn::VRAI);
            }
            for (j, e, _) in rapport {
                if let Some(m) = mols.get(j) {
                    f.centres.insert(m.debut, e);
                }
            }
        }
        Some(f)
    }

    fn liste(&self, champ: &str) -> String {
        let v: Vec<String> = champ.split(',').filter(|x| !x.is_empty())
            .map(|x| x.parse::<usize>().ok().and_then(|d| self.noms.get(&d).cloned()).unwrap_or_else(|| format!("m{}", x)))
            .filter(|n| !n.starts_with("__hyp_"))
            .collect();
        if v.len() > 8 {
            format!("{} et {} autres", v[..8].join(", "), v.len() - 8)
        } else {
            v.join(", ")
        }
    }

    /// les six faces et le centre d'une fonction, en clair (comme « lugus carte »)
    pub fn texte(&self, nom: &str) -> Option<String> {
        let c = self.lignes.get(nom)?;
        let n = |k: usize| c[k].trim_start_matches('i').parse::<usize>().ok();
        let mot = |v: Option<usize>| match v {
            Some(0) => "rien",
            Some(1) => "lit la mémoire",
            Some(2) => "écrit la mémoire",
            _ => "le monde",
        };
        let mut t = String::new();
        let (a, b) = c[3].split_once('-').unwrap_or(("?", "?"));
        let genre = match c[2].as_str() {
            "fonction" => format!("une fonction, lignes {} à {}", a, b),
            "reaction" => format!("une réaction, lignes {} à {}", a, b),
            _ => "empruntée (au prélude ou à une bibliothèque)".into(),
        };
        t.push_str(&format!("{} : {}, {} mots\r\n", nom, genre, c[4]));
        if !c[16].is_empty() {
            t.push_str(&format!("    {}\r\n", c[16]));
        }
        let deb: usize = c[0].trim_start_matches('m').parse().unwrap_or(0);
        t.push_str(&format!("Au centre : {}.\r\n", match self.centres.get(&deb) {
            Some(&e) if e == crate::adn::FAUX => "faux (réparée à cette lecture de l'ADN)",
            Some(&e) if e == crate::adn::VARIABLE => "variable (abîmée, non réparée)",
            Some(_) => "vrai (intacte à cette lecture de l'ADN)",
            None => "inconnu (l'ADN ne se lit pas)",
        }));
        t.push_str(&format!("Ce qu'elle touche : {}.\r\n", if c[5] == c[6] {
            format!("{} ({})", mot(n(5)), if c[8].is_empty() { "elle-même" } else { "elle-même et ses appels" })
        } else {
            format!("{} elle-même ; {} par ses appels", mot(n(5)), mot(n(6)))
        }));
        let pr = match c[7].as_str() {
            "-" => " ; hors d'atteinte depuis la tête".to_string(),
            "0" => String::new(),
            x => format!(" ; à {} pas de la tête", x),
        };
        t.push_str(&format!("Ses racines : {}{}.\r\n",
                            if c[9].is_empty() { "appelée par personne (sinon par elle-même)".to_string() } else { format!("appelée par {}", self.liste(&c[9])) },
                            pr));
        // les rouages du journal des hypothèses (supposons, hypothèse) sont dits à part, comme le texte les écrit
        let rouages = c[8].split(',').filter_map(|x| x.parse::<usize>().ok())
            .filter(|d| self.noms.get(d).map_or(false, |n| n.starts_with("__hyp_"))).count();
        let appels = self.liste(&c[8]);
        let branches = match (appels.is_empty(), rouages > 0) {
            (true, false) => "n'appelle rien (une feuille)".to_string(),
            (true, true) => "suppose (supposons ou hypothèse : le journal qui défait les écritures)".to_string(),
            (false, false) => format!("appelle {}", appels),
            (false, true) => format!("appelle {} ; suppose (supposons ou hypothèse : le journal qui défait les écritures)", appels),
        };
        t.push_str(&format!("Ses branches : {}.\r\n", branches));
        let mut pm = vec![];
        if n(10).unwrap_or(0) > 0 {
            pm.push(format!("exige {}", c[10]));
        }
        if n(11).unwrap_or(0) > 0 {
            pm.push(format!("garantit {}", c[11]));
        }
        match n(12).unwrap_or(0) {
            0 => {}
            1 => pm.push("1 exemple vérifié".into()),
            k => pm.push(format!("{} exemples vérifiés", k)),
        }
        if c[13] == "1" {
            pm.push("isotope lourd (relue à l'entrée et à la sortie)".into());
        }
        // 0.6r : la promesse « touche … » de l'en-tête, et si la carte la tient
        let tete = &c[16];
        let apres = tete.rfind(')').map(|i| &tete[i..]).unwrap_or("");
        if let Some(j) = apres.find(" touche ") {
            let mot: String = apres[j + 8..].chars().take_while(|&ch| ch != ' ' && ch != '{').collect();
            let niveau = match mot.as_str() {
                "rien" => Some((0, "ne rien toucher")),
                "lecture" => Some((1, "lire la mémoire au plus")),
                "memoire" | "mémoire" => Some((2, "ne pas toucher le monde")),
                "monde" => Some((3, "dit qu'elle touche le monde")),
                _ => None,
            };
            if let Some((p, quoi)) = niveau {
                if p == 3 {
                    pm.push(quoi.to_string());
                } else {
                    pm.push(format!("{} ({})", quoi, if n(6).unwrap_or(3) <= p { "tenue" } else { "rompue" }));
                }
            }
        }
        t.push_str(&format!("Ses promesses : {}.\r\n", if pm.is_empty() { "aucune écrite".to_string() } else { pm.join(", ") }));
        t.push_str(&format!("Sa mémoire : {}.\r\n", match c[15].chars().next() {
            Some('?') => "son histoire est inconnue (rien n'était rangé avant)".to_string(),
            Some('n') => "nouvelle à ce rangement".to_string(),
            Some('c') => "changée depuis le rangement d'avant".to_string(),
            Some('i') => {
                let k = n(15).unwrap_or(1);
                format!("inchangée depuis {} rangement{}", k, if k > 1 { "s" } else { "" })
            }
            _ => "inconnue".to_string(),
        }));
        Some(t)
    }
}

pub struct Paillasse {
    /// les six faces des fonctions (0.6q), de l'ADN rangé au dernier F5 ; perimee : le texte a changé depuis
    pub faces: Option<Faces>,
    pub perimee: bool,
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
    /// 0.69 : la palette montrée dans les explications ; la dernière case posée depuis la palette
    pub palette_ouverte: bool,
    pub derniere_case: Option<usize>,
    /// 0.69b : où le clic droit a ouvert le menu des cases
    pub clic_droit: Option<(i32, i32)>,
    /// 0.72 : la place réservée à la case qu'on glisse (x, y, largeur, hauteur)
    fantome: Option<(i32, i32, i32, i32)>,
    /// 0.72 : la fenêtre d'édition d'une case, si elle est ouverte
    pub edition: Option<Edition>,
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
        Paillasse { faces: None, perimee: false, reactions: vec![], courante: 0, choisi: None, positions: HashMap::new(), valeurs: HashMap::new(), decal: (0, 0),
                    car_l: 6, car_h: 12, echelle: 1.0, message: None, cases: vec![], colonnes: vec![], onglets: vec![], entrees_r: vec![], geste: None,
                    palette_ouverte: false, derniere_case: None, clic_droit: None, fantome: None, edition: None }
    }

    /// relire le texte (la réaction montrée et l'atome choisi restent, si on les retrouve)
    pub fn lire(&mut self, source: &str) {
        self.perimee = self.faces.as_ref().map_or(false, |f| f.source.trim_end() != source.replace("\r\n", "\n").trim_end());
        let nom = self.reactions.get(self.courante).map(|r| r.nom.clone());
        let cle = self.choisi.and_then(|k| self.reaction().and_then(|r| r.atomes.get(k)).map(|a| a.cle()));
        self.reactions = analyser(source);
        // la carte du programme : toujours là, après les réactions (la seule paillasse d'un programme sans réaction)
        if let Some(c) = carte(source) {
            self.reactions.push(c);
        }
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
                if r.carte && self.courante < self.reactions.len() && !self.reactions[self.courante].carte {
                    return false;
                }
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
        // 0.70b : le titre dit aussi l'élément de structure et la page vers laquelle la case renvoie (ou retourne)
        let titre = titre + if a.famille.is_empty() { 0 } else { 3 + a.element.chars().count() as i32 }
            + a.vers.as_ref().map_or(0, |n| 6 + n.chars().count() as i32)
            + a.retour.as_ref().map_or(0, |n| 14 + n.chars().count() as i32);
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

    /// 0.72 : la colonne (la vague) d'une case : celle choisie à la main (gardée dans PROG.paillasse), sinon sa vague
    fn colonne_atome(&self, r: &Reaction, k: usize) -> usize {
        let a = &r.atomes[k];
        match self.positions.get(&(r.nom.clone(), a.cle())) {
            Some(&(c, -1)) if c >= 1 => c as usize,
            _ => a.vague.max(1),
        }
    }

    /// 0.72 : les cases de chaque colonne, dans l'ordre de leurs lignes (l'indice 0, les entrées, reste vide) ; apercu :
    /// la case qu'on glisse, rangée à la colonne et au rang où elle tomberait
    fn par_colonnes(&self, r: &Reaction, apercu: Option<(usize, usize, usize)>) -> Vec<Vec<usize>> {
        let mut ks: Vec<usize> = (0..r.atomes.len()).collect();
        ks.sort_by_key(|&k| r.atomes[k].ligne);
        let mut n = r.nb_vagues.max(1);
        for &k in &ks {
            n = n.max(self.colonne_atome(r, k));
        }
        if let Some((_, c, _)) = apercu {
            n = n.max(c);
        }
        let mut cols: Vec<Vec<usize>> = vec![vec![]; n + 1];
        for &k in &ks {
            if apercu.map_or(false, |p| p.0 == k) {
                continue;
            }
            cols[self.colonne_atome(r, k)].push(k);
        }
        if let Some((k, c, rang)) = apercu {
            let v = &mut cols[c];
            v.insert(rang.min(v.len()), k);
        }
        cols
    }

    /// 0.72 : où tomberait la case « atome » lâchée en (x, y) : la colonne sous la souris (la dernière, libre, si l'on
    /// va plus loin), et le rang : le nombre de cases de cette colonne dont le milieu est au-dessus de la souris
    fn cible_sous(&self, atome: usize, x: i32, y: i32) -> (usize, usize) {
        let dernier = self.colonnes.iter().map(|c| c.0).max().unwrap_or(1).max(1);
        let col = match self.colonne_de(x) {
            Some(v) => v.max(1),
            None if self.colonnes.first().map_or(false, |c| x < c.1) => 1,
            None => dernier,
        };
        let rang = self.cases.iter().filter(|c| c.col == col && c.atome != atome && c.y + c.h / 2 < y).count();
        (col, rang)
    }

    /// 0.72 : la ligne où écrire une case neuve de la colonne v : avant la première case d'une colonne plus tardive
    fn ligne_pour_colonne(&self, r: &Reaction, v: usize) -> usize {
        let cols = self.par_colonnes(r, None);
        cols.iter().skip(v + 1).flatten().map(|&k| r.atomes[k].ligne).min().unwrap_or(r.fin)
    }

    /// les cases de la réaction montrée, rangées dans leurs colonnes (0.72 : la grille aimantée : une colonne par
    /// vague, les cases empilées dans l'ordre de leurs lignes ; pendant un glissement, les autres s'écartent pour
    /// montrer la place où la case tombera, et une colonne libre attend au bout)
    fn placer(&mut self) {
        self.cases.clear();
        self.entrees_r.clear();
        self.colonnes.clear();
        self.fantome = None;
        let r = match self.reactions.get(self.courante) {
            Some(r) => r.clone(),
            None => return,
        };
        let (cl, ch) = (self.car_l, self.car_h);
        let (x0, y0) = self.origine();
        let glisse = match &self.geste {
            Some(Geste::Deplacer { atome, bouge: true, cible: Some((c, rang)), dx, dy, mx, my, .. }) if !r.carte =>
                Some((*atome, *c, *rang, *mx - *dx, *my - *dy)),
            _ => None,
        };
        let mut cols = self.par_colonnes(&r, glisse.map(|g| (g.0, g.1, g.2)));
        if glisse.is_some() && cols.last().map_or(false, |c| !c.is_empty()) {
            cols.push(vec![]);
        }
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
        let mut place_col: Vec<i32> = vec![0; cols.len()];
        for v in 1..cols.len() {
            let dans: Vec<&Atome> = cols[v].iter().map(|&k| &r.atomes[k]).collect();
            let lmax = dans.iter().map(|a| self.mesure_case(a).0).max().unwrap_or(self.px(120));
            let lab = dans.iter().flat_map(|a| a.sorties.iter()).map(|s| self.etiquette_sortie(s).chars().count() as i32).max().unwrap_or(0);
            let large = lmax + (lab * cl + self.px(40)).max(self.px(70));
            self.colonnes.push((v, x - self.px(12), large));
            place_col[v] = x;
            x += large;
        }
        let mut glissee: Option<Case> = None;
        for v in 1..cols.len() {
            let mut y = y0;
            for &k in &cols[v] {
                let a = &r.atomes[k];
                let (l, h, rangs) = self.mesure_case(a);
                let (cx, cy) = match glisse {
                    Some(g) if g.0 == k => {
                        // la place réservée (le fantôme), et la case qui suit la souris
                        self.fantome = Some((place_col[v], y, l, h));
                        (g.3, g.4)
                    }
                    _ => (place_col[v], y),
                };
                y += h + self.px(26);
                let entrees = (0..a.entrees.len()).map(|i| (cx, cy + rangs[i])).collect();
                let sorties = (0..a.sorties.len()).map(|i| (cx + l, cy + rangs[i])).collect();
                let c = Case { atome: k, col: v, x: cx, y: cy, l, h, entrees, sorties };
                if glisse.map_or(false, |g| g.0 == k) {
                    glissee = Some(c);
                } else {
                    self.cases.push(c);
                }
            }
        }
        // la case qu'on glisse est dessinée par-dessus les autres
        if let Some(c) = glissee {
            self.cases.push(c);
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
        // 0.72 : la place où la case glissée tombera : un cadre en pointillés, et la ligne qu'elle prendra
        if let (Some((fx, fy, fl, fh)), Some(Geste::Deplacer { atome, cible: Some((v, _)), .. })) = (self.fantome, &self.geste) {
            let pas_p = self.px(6).max(3);
            for i in (0..fl).step_by(pas_p as usize * 2) {
                im.plein(fx + i, fy, pas_p.min(fl - i), e2, OR);
                im.plein(fx + i, fy + fh - e2, pas_p.min(fl - i), e2, OR);
            }
            for j in (0..fh).step_by(pas_p as usize * 2) {
                im.plein(fx, fy + j, e2, pas_p.min(fh - j), OR);
                im.plein(fx + fl - e2, fy + j, e2, pas_p.min(fh - j), OR);
            }
            let cols = self.par_colonnes(&r, self.cases.iter().find(|c| c.atome == *atome).map(|_| {
                let (c, rang) = match &self.geste { Some(Geste::Deplacer { cible: Some(p), .. }) => *p, _ => (1, 0) };
                (*atome, c, rang)
            }));
            let mut lignes: Vec<usize> = r.atomes.iter().map(|a| a.ligne).collect();
            lignes.sort();
            let pos = cols.iter().flatten().position(|k| k == atome).unwrap_or(0);
            let ligne = lignes.get(pos).copied().unwrap_or(0) + 1;
            // l'étiquette, au-dessus de la case qu'on tient (elle couvre souvent sa place)
            let t = format!("ici : vague {}, ligne {}", v, ligne);
            let (gx, gy) = self.cases.last().map(|c| (c.x, c.y)).unwrap_or((fx, fy));
            let lt = (t.chars().count() as i32 + 2) * cl;
            im.plein(gx, gy - ch - self.px(10), lt, ch + self.px(6), 0x3A3020);
            tx.push(TexteP { x: gx + cl, y: gy - ch - self.px(7), texte: t, couleur: OR });
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
            // 0.69 : une case d'une famille porte son symbole et sa couleur ; la structure (H, O, N, C) suit le titre
            let symbole = if a.famille.is_empty() { a.element.clone() } else { a.famille.clone() };
            let coul = couleur_element(&symbole);
            let choisi = self.choisi == Some(c.atome);
            im.plein(c.x, c.y, c.l, c.h, 0x262B35);
            im.plein(c.x, c.y, c.l, ch + self.px(10), 0x303644);
            im.cadre(c.x, c.y, c.l, c.h, if choisi { e2 + e1 } else { e1 }, if choisi { OR } else { coul });
            // l'élément, dans un rond de sa couleur
            // un symbole de deux lettres (Fe, Mg…) : un rond un peu plus large
            let rayon = (ch / 2).max(cl * symbole.chars().count() as i32 / 2 + self.px(2));
            let rx = c.x + self.px(4) + rayon;
            let ry = c.y + (ch + self.px(10)) / 2;
            im.disque(rx, ry, rayon, coul);
            tx.push(TexteP { x: rx - cl * symbole.chars().count() as i32 / 2, y: ry - ch / 2, texte: symbole.clone(), couleur: 0x1B1E24 });
            let titre = if a.nom.is_empty() { format!("ligne {}", a.ligne + 1) } else { a.nom.clone() };
            let titre = if a.famille.is_empty() { titre } else { format!("{} · {}", titre, a.element) };
            let titre = match (&a.vers, &a.retour) {
                (Some(n), _) => format!("{} vers {}", titre, n),
                (None, Some(n)) => format!("{} retour vers {}", titre, n),
                _ => titre,
            };
            tx.push(TexteP { x: rx + rayon + self.px(6), y: c.y + self.px(5), texte: titre, couleur: ENCRE });
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
        self.dessiner_edition(&mut im, &mut tx, l as i32, h as i32);
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
        // 0.72 : la fenêtre d'édition ouverte prend les clics (un double clic compte comme un clic)
        if self.edition.is_some() {
            return match genre {
                Souris::Bas | Souris::Double => self.clic_edition(x, y, source),
                _ => Reponse::Rien,
            };
        }
        if matches!(genre, Souris::Bas | Souris::Droit | Souris::Double) {
            self.palette_ouverte = false;
        }
        if self.cases.is_empty() && self.onglets.is_empty() {
            self.dessiner(800, 600);
        }
        if self.reaction().map_or(false, |r| r.carte) {
            // la carte : choisir une fonction (le texte y va), glisser le vide ; rien ne réécrit le texte
            match genre {
                Souris::Bas => {
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
                    if let Some(k) = self.case_sous(x, y).map(|c| c.atome) {
                        self.choisi = Some(k);
                        let l = self.reaction().unwrap().atomes[k].ligne;
                        return Reponse::Aller(l);
                    }
                    // le vide : on fait glisser la carte (de gauche à droite, de haut en bas)
                    self.choisi = None;
                    self.geste = Some(Geste::Panoramique { x0: x, y0: y, d0: self.decal });
                    return Reponse::Redessiner;
                }
                Souris::Bouge => {
                    if let Some(Geste::Panoramique { x0, y0, d0 }) = self.geste.clone() {
                        self.decal = (d0.0 + x - x0, d0.1 + y - y0);
                        return Reponse::Redessiner;
                    }
                    return Reponse::Rien;
                }
                Souris::Haut => {
                    self.geste = None;
                    return Reponse::Rien;
                }
                Souris::Droit => {
                    if let Some(k) = self.case_sous(x, y).map(|c| c.atome) {
                        self.choisi = Some(k);
                        return Reponse::Message("la carte se lit : une fonction s'écrit dans le texte ; dans une réaction \
                                                 (onglet du haut), le clic droit édite ses cases".into());
                    }
                    return Reponse::Rien;
                }
                Souris::Double => {
                    // un double clic dans le vide d'un programme sans réaction : une réaction neuve, comme avant
                    if self.case_sous(x, y).is_none() && self.reactions.iter().all(|r| r.carte) {
                        let (s, l) = ajouter_reaction(source);
                        return Reponse::Texte { source: s, ligne: l };
                    }
                    return Reponse::Rien;
                }
            }
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
                    self.geste = Some(Geste::Deplacer { atome: c.atome, dx: x - c.x, dy: y - c.y, x0: x, y0: y, bouge: false,
                                                        mx: x, my: y, cible: None });
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
                    Some(Geste::Deplacer { atome, dx, dy, x0, y0, bouge, cible, .. }) => {
                        let _ = (echelle, ox, oy, &nom_r, cle);
                        let bouge = bouge || (x - x0).abs() > 3 || (y - y0).abs() > 3;
                        // 0.72 : la grille aimantée : la colonne sous la souris, et le rang parmi ses cases (au-dessus du
                        // milieu d'une case : avant elle) ; les autres cases s'écartent pour montrer la place
                        let cible = if bouge { Some(self.cible_sous(atome, x, y)) } else { cible };
                        self.geste = Some(Geste::Deplacer { atome, dx, dy, x0, y0, bouge, mx: x, my: y, cible });
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
                    // 0.70b : la paillasse fait l'ordre du texte : les lignes des cases suivent leurs places, colonne par
                    // colonne (de gauche à droite), puis de haut en bas ; la case reste où on l'a posée
                    Some(Geste::Deplacer { atome, bouge: true, cible, .. }) if !r.carte => {
                        // 0.72 : la case tombe à la place montrée ; le texte prend l'ordre des colonnes, puis des rangs
                        let (v, rang) = cible.unwrap_or_else(|| self.cible_sous(atome, x, y));
                        let cols = self.par_colonnes(&r, Some((atome, v, rang)));
                        let ordre: Vec<usize> = cols.iter().flatten().copied().collect();
                        let (s, l) = ordonner_lignes(source, &r, &ordre, atome);
                        let a = &r.atomes[atome];
                        let cle_a = (r.nom.clone(), a.cle());
                        if v == a.vague.max(1) {
                            self.positions.remove(&cle_a);
                        } else {
                            self.positions.insert(cle_a, (v as i32, -1));
                        }
                        let _ = x;
                        // une valeur reçue d'une vague plus tardive : la case est posée là, elle calculera à son arrivée
                        let entrees: Vec<&str> = a.entrees.iter().map(|e| e.nom.as_str()).collect();
                        let attend = r.atomes.iter().filter(|b| b.vague >= v && b.sorties.iter().any(|o| entrees.contains(&o.as_str())))
                            .flat_map(|b| b.sorties.iter().filter(|o| entrees.contains(&o.as_str())).cloned()).collect::<Vec<_>>();
                        let mut avant: Vec<usize> = (0..r.atomes.len()).collect();
                        avant.sort_by_key(|&k| r.atomes[k].ligne);
                        self.message = Some(if s == source && ordre != avant {
                            "le texte n'a pas pu suivre : une case de cette réaction n'est pas sur une seule ligne".to_string()
                        } else if attend.is_empty() && v > a.vague.max(1) {
                            format!("la case est à la vague {}, ligne {} (elle pourrait réagir dès la vague {})", v, l + 1, a.vague)
                        } else if attend.is_empty() {
                            format!("la case est à la vague {}, ligne {}", v, l + 1)
                        } else {
                            format!("la case est à la vague {}, ligne {} ; elle reçoit {} d'une vague plus tardive : \
                                     elle calculera quand la valeur arrivera", v, l + 1, attend.join(", "))
                        });
                        if s == source {
                            Reponse::Redessiner
                        } else {
                            Reponse::Texte { source: s, ligne: l }
                        }
                    }
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
            Souris::Droit => {
                self.geste = None;
                if self.reactions.is_empty() {
                    let (s, l) = ajouter_reaction(source);
                    let t = s.split('\n').nth(l).unwrap_or("").trim().to_string();
                    return Reponse::Editer { source: Some(s), ligne: l, texte: t, x, y };
                }
                if let Some(c) = self.case_sous(x, y).cloned() {
                    // 0.72 : la fenêtre d'édition de la case
                    self.choisi = Some(c.atome);
                    let l = self.reaction().unwrap().atomes[c.atome].ligne;
                    self.ouvrir_edition(source, l);
                    return Reponse::Aller(l);
                }
                // 0.69b : dans le vide, le menu des cases là où l'on a cliqué
                self.clic_droit = Some((x, y));
                Reponse::Palette { x, y }
            }
            Souris::Double => {
                self.geste = None;
                if self.reactions.is_empty() {
                    let (s, l) = ajouter_reaction(source);
                    return Reponse::Texte { source: s, ligne: l };
                }
                if let Some(c) = self.case_sous(x, y).cloned() {
                    // 0.72 : le double clic sur l'en-tête d'une case : la fenêtre d'édition
                    if y < c.y + self.car_h + self.px(10) {
                        self.choisi = Some(c.atome);
                        let l = self.reaction().unwrap().atomes[c.atome].ligne;
                        self.ouvrir_edition(source, l);
                        return Reponse::Aller(l);
                    }
                    let r = self.reaction().unwrap();
                    // 0.70 : une case qui renvoie vers une page : le double clic ouvre la page
                    if let Some(n) = r.atomes[c.atome].vers.clone().or_else(|| r.atomes[c.atome].retour.clone()) {
                        if let Some(i) = self.reactions.iter().position(|q| q.nom == n) {
                            self.courante = i;
                            self.choisi = None;
                            return Reponse::Redessiner;
                        }
                    }
                    return Reponse::Aller(r.atomes[c.atome].ligne);
                }
                let (s, l) = self.poser_atome(x, y, source);
                self.ouvrir_edition(&s, l);
                Reponse::Texte { source: s, ligne: l }
            }
        }
    }

    /// 0.69b : la case choisie au menu du clic droit (None : la case vide « = _ -> lK »), posée où l'on a cliqué,
    /// puis ouverte à l'édition
    pub fn poser_ici(&mut self, k: Option<usize>, source: &str) -> Reponse {
        let (x, y) = match self.clic_droit.take() {
            Some(p) => p,
            None => return Reponse::Rien,
        };
        // 0.70 : la colonne où l'on a cliqué décide de la place de la ligne (avant la vague suivante)
        let vague = self.colonne_de(x);
        if let Some((k, c)) = k.and_then(|k| PALETTE.get(k).map(|c| (k, c))) {
            if c.nom == "suite" || c.nom == "appeler" {
                self.derniere_case = Some(k);
                return self.poser_suite(source, Some((x, y)), c.nom == "appeler");
            }
        }
        let r0 = self.reaction().filter(|r| !r.carte).cloned();
        let (s, l) = match k.and_then(|k| PALETTE.get(k).map(|c| (k, c))) {
            None => self.poser_atome(x, y, source),
            Some((k, c)) => {
                let r = match self.reaction().filter(|r| !r.carte) {
                    Some(r) => r.clone(),
                    None => return Reponse::Rien,
                };
                let (s, l) = poser_modele(source, &r, c);
                self.derniere_case = Some(k);
                (s, l)
            }
        };
        let _ = (vague, r0, y);
        // 0.72 : la case neuve va dans la colonne où l'on a cliqué (au bout), et la fenêtre d'édition s'ouvre
        let (s, l) = self.ranger_neuve(&s, l, x);
        self.ouvrir_edition(&s, l);
        Reponse::Texte { source: s, ligne: l }
    }

    /// 0.72 : une case neuve (sa ligne l dans le texte s) rangée dans la colonne sous x : sa ligne va avant les colonnes
    /// plus tardives, et sa colonne est retenue ; rend le texte et la ligne
    fn ranger_neuve(&mut self, s: &str, l: usize, x: i32) -> (String, usize) {
        let col = match self.colonne_de(x) {
            Some(v) => v.max(1),
            None if self.colonnes.first().map_or(false, |c| x < c.1) => 1,
            None => self.colonnes.iter().map(|c| c.0).max().unwrap_or(1).max(1),
        };
        let nom = match self.reaction().filter(|r| !r.carte) {
            Some(r) => r.nom.clone(),
            None => return (s.to_string(), l),
        };
        let r = match analyser(s).into_iter().find(|q| q.nom == nom) {
            Some(r) => r,
            None => return (s.to_string(), l),
        };
        let k = match r.atomes.iter().position(|a| a.ligne == l) {
            Some(k) => k,
            None => return (s.to_string(), l),
        };
        let cle = (nom.clone(), r.atomes[k].cle());
        if col == r.atomes[k].vague.max(1) {
            self.positions.remove(&cle);
        } else {
            self.positions.insert(cle, (col as i32, -1));
        }
        // la ligne : avant la première case d'une colonne plus tardive (sans compter la case neuve)
        let mut autres = r.clone();
        autres.atomes.remove(k);
        let avant = self.ligne_pour_colonne(&autres, col);
        deplacer_ligne(s, l, avant.min(r.fin))
    }

    /// 0.70 : la vague de la colonne sous x (0 : les entrées), s'il y en a une
    pub fn colonne_de(&self, x: i32) -> Option<usize> {
        self.colonnes.iter().find(|c| x >= c.1 && x < c.1 + c.2).map(|c| c.0)
    }

    /// 0.70 : une page neuve, montrée tout de suite
    pub fn nouvelle_page(&mut self, source: &str) -> Reponse {
        let (s, l, nom) = ajouter_page(source);
        self.lire(&s);
        if let Some(i) = self.reactions.iter().position(|r| r.nom == nom) {
            self.courante = i;
        }
        self.message = Some(format!("la page « {} » : elle reçoit « entree » ; une case « suite » (Ne) de la page d'avant \
                                     lui envoie sa valeur", nom));
        Reponse::Texte { source: s, ligne: l }
    }

    /// 0.70 : la case « suite » : la fin qui renvoie à la page suivante (l'onglet d'après, créé s'il n'existe pas)
    fn poser_suite(&mut self, source: &str, ou: Option<(i32, i32)>, appeler: bool) -> Reponse {
        let r = match self.reaction().filter(|r| !r.carte) {
            Some(r) => r.clone(),
            None => return Reponse::Message("la suite se pose dans une page (une réaction)".into()),
        };
        let pages: Vec<String> = self.reactions.iter().filter(|q| !q.carte).map(|q| q.nom.clone()).collect();
        let ici = pages.iter().position(|n| *n == r.nom).unwrap_or(0);
        let (mut src, suivante) = match pages.get(ici + 1) {
            Some(n) => (source.to_string(), n.clone()),
            None => {
                let (s, _, n) = ajouter_page(source);
                (s, n)
            }
        };
        let nb = analyser(&src).into_iter().find(|q| q.nom == suivante).map_or(1, |q| q.params.len().max(1));
        let appel = format!("{}({})", suivante, vec!["_"; nb].join(", "));
        // le résultat de la réaction s'il n'est pas encore donné ; sinon une liaison neuve (la réaction le donne déjà)
        let ligne = match &r.resultat {
            Some(res) if !appeler && !r.atomes.iter().any(|a| a.sorties.contains(res)) => format!("= {} -> {}", appel, res),
            Some(_) => {
                let mut k = 1;
                while r.params.contains(&format!("l{}", k)) || r.atomes.iter().any(|a| a.sorties.contains(&format!("l{}", k))) {
                    k += 1;
                }
                format!("= {} -> l{}", appel, k)
            }
            None if !appeler => format!("= sortie({})", appel),
            None => {
                let mut k = 1;
                while r.params.contains(&format!("l{}", k)) || r.atomes.iter().any(|a| a.sorties.contains(&format!("l{}", k))) {
                    k += 1;
                }
                format!("= {} -> l{}", appel, k)
            }
        };
        let lignes: Vec<&str> = src.split('\n').collect();
        let retrait = r.atomes.last().map(|a| {
            let l = lignes[a.ligne];
            l[..l.len() - l.trim_start().len()].to_string()
        }).unwrap_or_else(|| "    ".into());
        let cr = if src.contains("\r\n") { "\r" } else { "" };
        let mut v: Vec<String> = lignes.iter().map(|x| x.to_string()).collect();
        let place = r.fin.min(v.len());
        v.insert(place, format!("{}{}{}", retrait, ligne, cr));
        src = v.join("\n");
        let mut place = place;
        if let Some((x, _)) = ou {
            let (s2, l2) = self.ranger_neuve(&src, place, x);
            src = s2;
            place = l2;
        }
        self.message = Some(if appeler {
            format!("l'appel : la valeur part dans la page « {} », son résultat revient ici (double clic : ouvrir la page)",
                    suivante)
        } else {
            format!("la suite : la valeur part dans la page « {} » (double clic sur la case pour l'ouvrir)", suivante)
        });
        if ou.is_some() {
            self.ouvrir_edition(&src, place);
        }
        Reponse::Texte { source: src, ligne: place }
    }

    /// un atome neuf « = _ -> lK » à la fin de la réaction, placé où l'on a cliqué ; rend le texte et sa ligne
    fn poser_atome(&mut self, x: i32, y: i32, source: &str) -> (String, usize) {
        let r = self.reaction().unwrap().clone();
        let (s, l) = ajouter_atome(source, &r);
        let nom = format!("l{}", {
            let mut k = 1;
            while r.params.contains(&format!("l{}", k)) || r.atomes.iter().any(|a| a.sorties.contains(&format!("l{}", k))) {
                k += 1;
            }
            k
        });
        let _ = (nom, y);
        self.ranger_neuve(&s, l, x)
    }

    /// une touche quand la paillasse a le clavier : Suppr retire l'atome choisi, Échap oublie le choix
    pub fn touche(&mut self, vk: u32, source: &str) -> Reponse {
        if self.edition.is_some() {
            return self.touche_edition(vk, source);
        }
        if self.reaction().map_or(false, |r| r.carte) && vk == 0x2E {
            return Reponse::Message("la carte du programme se lit, elle ne se réécrit pas : retirez la fonction dans le texte".into());
        }
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
    /// 0.69 : poser la case k de la palette dans la réaction montrée (une réaction neuve s'il n'y en a pas)
    pub fn poser_case(&mut self, k: usize, source: &str) -> Reponse {
        let c = match PALETTE.get(k) {
            Some(c) => c,
            None => return Reponse::Message(format!("pas de case {} dans la palette", k)),
        };
        self.palette_ouverte = false;
        self.derniere_case = Some(k);
        self.choisi = None;
        if c.nom == "suite" || c.nom == "appeler" {
            return self.poser_suite(source, None, c.nom == "appeler");
        }
        let r = self.reaction().filter(|r| !r.carte).cloned();
        let (s, l) = match r {
            Some(r) => poser_modele(source, &r, c),
            None => {
                // une réaction neuve : sa première case est celle-ci
                let (s, l) = ajouter_reaction(source);
                let modele = ligne_du_modele(c, None, 1);
                let s = editer_ligne(&s, l, &modele);
                self.lire(&s);
                if let Some(i) = self.reactions.iter().position(|r| !r.carte && r.ligne + 1 == l) {
                    self.courante = i;
                }
                (s, l)
            }
        };
        Reponse::Texte { source: s, ligne: l }
    }

    /// les explications : la palette si elle est ouverte, la case posée, puis la case ou la réaction choisie
    pub fn explication(&self) -> String {
        if self.palette_ouverte {
            return texte_palette();
        }
        let mut t = String::new();
        if let (None, Some(c)) = (self.choisi, self.derniere_case.and_then(|k| PALETTE.get(k))) {
            t.push_str(&format!("Case posée : {} {} ({}) — {}\r\nSes « _ » sont des entrées libres : tirez-y une liaison, \
                                 ou clic droit pour écrire la case.\r\n\r\n", c.symbole, c.nom, c.famille, c.aide));
        }
        t + &self.explication_case()
    }

    fn explication_case(&self) -> String {
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
        if r.carte {
            match self.choisi.and_then(|k| r.atomes.get(k)) {
                Some(a) if self.faces.as_ref().and_then(|f| f.texte(&a.nom)).is_some() => {
                    // 0.6q : les six faces, de l'ADN rangé au dernier F5
                    t.push_str(&self.faces.as_ref().and_then(|f| f.texte(&a.nom)).unwrap_or_default());
                    if self.perimee {
                        t.push_str("(Ces faces viennent de l'ADN rangé au dernier F5 : le texte a changé depuis ; F5 les refait.)\r\n");
                    }
                }
                Some(a) => {
                    let appelle: Vec<&str> = a.entrees.iter().map(|p| p.nom.as_str()).collect();
                    let appelee: Vec<&str> = r.atomes.iter().filter(|b| b.entrees.iter().any(|p| p.nom == a.nom)).map(|b| b.nom.as_str()).collect();
                    t.push_str(&format!("{} — ligne {}\r\n{}\r\n", a.nom, a.ligne + 1, a.quoi));
                    t.push_str(&format!("Elle appelle : {}.\r\nElle est appelée par : {}.\r\n",
                                        if appelle.is_empty() { "rien (une feuille)".to_string() } else { appelle.join(", ") },
                                        if appelee.is_empty() { "personne".to_string() } else { appelee.join(", ") }));
                    t.push_str(&format!("Vague {} : la profondeur de ses appels.\r\n", a.vague));
                    t.push_str("F5 sur Lugus range l'ADN avec la carte : les six faces de la fonction (ce qu'elle est, ce qu'elle \
                                touche, ses racines, ses branches, ses promesses, sa mémoire) et son état viendront ici.\r\n");
                }
                None => {
                    t.push_str(&format!("La carte du programme : {} fonction{}, {} vague{} d'appels. Chaque case est une fonction ; \
                                         une liaison va de la fonction appelée (à gauche) vers celle qui l'appelle (à droite).\r\n\
                                         Un clic sur une case : le texte va à la fonction. Pour voyager sur la carte : glisser le vide à la souris, \
                                         la molette (haut, bas), Maj + molette (gauche, droite). La carte se lit ; le texte se change dans \
                                         l'éditeur, et la carte suit.\r\n", r.atomes.len(), if r.atomes.len() > 1 { "s" } else { "" },
                                        r.nb_vagues, if r.nb_vagues > 1 { "s" } else { "" }));
                }
            }
            return t;
        }
        match self.choisi.and_then(|k| r.atomes.get(k)) {
            Some(a) => {
                let nom_el = nom_element(&a.element);
                let lues: Vec<&str> = a.entrees.iter().filter(|p| p.nom != "_").map(|p| p.nom.as_str()).collect();
                let libres = a.entrees.iter().filter(|p| p.nom == "_").count();
                t.push_str(&format!("{} — ligne {}\r\n", if a.nom.is_empty() { "un atome" } else { &a.nom }, a.ligne + 1));
                t.push_str(&format!("{} ({}), valence {} : il lit {} et donne {}.\r\n", a.element, nom_el, a.valence(),
                                    if lues.is_empty() { "rien".to_string() } else { lues.join(", ") },
                                    if a.sorties.is_empty() { "rien (un bout de chaîne)".to_string() } else { a.sorties.join(", ") }));
                if let Some(c) = PALETTE.iter().find(|c| c.symbole == a.famille) {
                    t.push_str(&format!("Famille {} ({}, {}) : {}\r\n", c.symbole, c.element, c.famille,
                                        PALETTE.iter().filter(|x| x.symbole == c.symbole)
                                               .find(|x| a.quoi.trim().starts_with(x.modele.trim_start_matches('=').trim()
                                                                                 .split(['(', ' ', '_']).next().unwrap_or("")))
                                               .unwrap_or(c).aide));
                }
                if let Some(n) = &a.retour {
                    t.push_str(&format!("Le retour : le résultat de cette page revient à la page « {} », qui l'appelle \
                                         (double clic : y revenir).\r\n", n));
                }
                if let Some(n) = &a.vers {
                    t.push_str(&format!("Elle renvoie à la page « {} » : sa valeur y part en entrée (double clic : ouvrir la \
                                         page).\r\n", n));
                }
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
                t.push_str("Glisser une case : chaque vague est une colonne, les cases s'y empilent dans l'ordre de leurs lignes ; \
                            pendant le glissement, les autres s'écartent et un cadre montre la place (la vague et la ligne qu'elle \
                            prendra) ; lâchée, la ligne du texte suit. Tirer d'une sortie (à droite d'une case) vers une case : lier \
                            (la liaison remplit son entrée libre « _ », ou l'entrée visée). Tirer une entrée vers le vide : délier.\r\n\
                            Clic droit sur une case, ou double clic sur son en-tête : la fenêtre d'édition (son nom, ce qu'elle fait, \
                            le nombre et le nom de ses entrées et de ses sorties ; Tab : le champ suivant, Entrée écrit, Échap \
                            renonce). Clic droit dans le vide : le menu des cases, la case choisie se pose dans cette colonne et \
                            s'édite. Double clic dans le vide : une case vide (« = _ -> l1 »). Suppr : retirer la case choisie. \
                            Glisser le vide : déplacer la paillasse.\r\n\
                            Ctrl+P : faire réagir avec la provenance ; chaque liaison montre alors sa valeur (vert : arrivée, rouge : \
                            sa branche n'a pas réagi, gris : jamais calculée).\r\n");
                // 0.6q : la réaction est une molécule : ses six faces, de l'ADN rangé au dernier F5
                if let Some(f) = self.faces.as_ref().and_then(|f| f.texte(&r.nom)) {
                    t.push_str("\r\nLes six faces de la réaction, et son état :\r\n");
                    t.push_str(&f);
                    if self.perimee {
                        t.push_str("(Ces faces viennent de l'ADN rangé au dernier F5 : le texte a changé depuis ; F5 les refait.)\r\n");
                    }
                }
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
                        // 0.72 : seules les colonnes choisies (« |N|-1 ») ; les anciennes places au point près sont oubliées
                        if y == -1 {
                            self.positions.insert((r.to_string(), k.to_string()), (x, y));
                        }
                    }
                }
            }
        }
    }
}

// ------------------------------------------------------------------------------------------------ 0.72 : éditer une case
/// Un morceau de « ce que fait » une case : du texte, ou une de ses entrées (son numéro dans la liste des entrées)
#[derive(Clone, Debug)]
enum Morceau {
    Texte(String),
    Entree(usize),
}

/// Ce qu'on peut viser dans la fenêtre d'édition
#[derive(Clone, Copy, Debug, PartialEq)]
enum Zone {
    Champ(usize),
    Moins(bool),
    Plus(bool),
    Ecrire,
    Annuler,
}

/// 0.72 : la fenêtre d'édition d'une case (le clic droit sur une case, ou le double clic sur son en-tête). On y écrit
/// son nom, ce qu'elle fait, ses entrées et ses sorties (leur nombre et leurs noms) ; la ligne de code qui en sortira
/// est montrée en bas ; Entrée l'écrit dans le texte, Échap renonce.
#[derive(Clone, Debug)]
pub struct Edition {
    pub reaction: String,
    pub ligne: usize,
    retrait: String,
    /// le début de la ligne quand la case n'a pas de nom (« = », ou rien pour « @3[_] = _ »)
    sans_nom: String,
    pub nom: String,
    morceaux: Vec<Morceau>,
    /// les noms des entrées (« _ » : une entrée libre ; vide pendant qu'on l'écrit : libre aussi)
    pub entrees: Vec<String>,
    /// les sorties, telles qu'écrites (« a lourd », « r: flottant ») ; leurs noms d'origine, pour les renommer partout
    pub sorties: Vec<String>,
    anciennes: Vec<String>,
    apres: String,
    commentaire: String,
    /// les liaisons connues de la réaction (ses entrées et les sorties des autres cases)
    connues: Vec<String>,
    pub champ: usize,
    zones: Vec<(i32, i32, i32, i32, Zone)>,
}

fn nom_valide(n: &str) -> bool {
    !n.is_empty() && n.chars().next().map_or(false, |c| c.is_alphabetic() || c == '_') && n.chars().all(lettre)
}

impl Edition {
    /// la case de la ligne « ligne » du texte, dans la réaction r
    fn depuis(source: &str, r: &Reaction, ligne: usize) -> Option<Edition> {
        let k = r.atomes.iter().position(|a| a.ligne == ligne)?;
        let l = source.split('\n').nth(ligne)?.trim_end_matches('\r');
        let fc = fin_code(l);
        let code = &l[..fc];
        let debut = code.len() - code.trim_start().len();
        let fin = code.trim_end().trim_end_matches(';').len().max(debut);
        let fleche = chercher(code, "->", debut, fin);
        // « apres » : après les sorties, ou au bout de ce que fait la case
        let ws = mots(code, debut, fin);
        let p_apres = ws.iter().filter(|w| w.0 == "apres").map(|w| w.1).last();
        let gauche_fin = fleche.or(p_apres).unwrap_or(fin);
        let a = &r.atomes[k];
        let (q0, nom) = if !a.nom.is_empty() {
            let e = code[debut..].find('=').map(|p| p + debut + 1).unwrap_or(debut);
            (e, a.nom.clone())
        } else if code[debut..].starts_with('=') && !code[debut..].starts_with("==") {
            (debut + 1, String::new())
        } else {
            (debut, String::new())
        };
        let sans_nom = if code[debut..].starts_with('=') || !a.nom.is_empty() { "= ".to_string() } else { String::new() };
        let quoi = code[q0..gauche_fin].trim().to_string();
        let sorties: Vec<String> = match fleche {
            Some(fl) => {
                let fs = p_apres.filter(|&p| p > fl).unwrap_or(fin);
                code[fl + 2..fs].split(',').map(|m| m.trim().to_string()).filter(|m| !m.is_empty()).collect()
            }
            None => vec![],
        };
        let apres = p_apres.map(|p| code[p + 5..fin].trim().to_string()).unwrap_or_default();
        let mut connues: Vec<String> = r.params.clone();
        for (j, b) in r.atomes.iter().enumerate() {
            if j != k {
                connues.extend(b.sorties.iter().cloned());
            }
        }
        let mut e = Edition {
            reaction: r.nom.clone(),
            ligne,
            retrait: code[..debut].to_string(),
            sans_nom,
            nom,
            morceaux: vec![],
            entrees: vec![],
            anciennes: sorties.iter().map(|m| premier_mot(m)).collect(),
            sorties,
            apres,
            commentaire: l[fc..].trim().to_string(),
            connues,
            champ: 1,
            zones: vec![],
        };
        e.decouper(&quoi);
        Some(e)
    }

    /// « ce que fait » la case, en texte
    pub fn quoi(&self) -> String {
        let mut t = String::new();
        for m in &self.morceaux {
            match m {
                Morceau::Texte(x) => t.push_str(x),
                Morceau::Entree(i) => {
                    let n = &self.entrees[*i];
                    t.push_str(if n.is_empty() { "_" } else { n });
                }
            }
        }
        t
    }

    /// coupe « ce que fait » en texte et en entrées (« _ », ou une liaison connue), comme la paillasse les voit
    fn decouper(&mut self, quoi: &str) {
        self.morceaux.clear();
        self.entrees.clear();
        let mut i = 0;
        for (m, d, f, prec, suit) in mots(quoi, 0, quoi.len()) {
            if prec == '.' || suit == '(' || MOTS.contains(&m.as_str()) {
                continue;
            }
            if m != "_" && !self.connues.contains(&m) {
                continue;
            }
            if d > i {
                self.morceaux.push(Morceau::Texte(quoi[i..d].to_string()));
            }
            // une liaison nommée deux fois est une seule entrée ; chaque « _ » en est une
            let k = if m == "_" { None } else { self.entrees.iter().position(|e| *e == m) };
            let k = match k {
                Some(k) => k,
                None => {
                    self.entrees.push(m.clone());
                    self.entrees.len() - 1
                }
            };
            self.morceaux.push(Morceau::Entree(k));
            i = f;
        }
        if i < quoi.len() {
            self.morceaux.push(Morceau::Texte(quoi[i..].to_string()));
        }
    }

    /// une entrée de plus : un argument « _ » de plus à l'appel qui finit la case, sinon « op _ » avec la dernière
    /// opération écrite (« + _ » s'il n'y en a pas)
    fn ajouter_entree(&mut self) {
        let q = self.quoi();
        let t = q.trim_end();
        let neuf = if t.ends_with(')') && t.contains('(') {
            let p = t.len() - 1;
            let avant = t[..p].trim_end();
            if avant.ends_with('(') { format!("{}_)", &t[..p]) } else { format!("{}, _)", &t[..p]) }
        } else if t.ends_with(']') && t.contains('[') {
            format!("{} + _", t)
        } else {
            let op = t.char_indices().rev().find(|(_, c)| "+-*/%<>".contains(*c)).map(|(i, c)| {
                // « <= », « >= », « == » : l'opération entière
                let deux = &t[i.saturating_sub(1)..i + c.len_utf8()];
                if deux == "<=" || deux == ">=" || deux == "==" || deux == "!=" { deux.to_string() } else { c.to_string() }
            });
            let op = match op.as_deref() {
                Some("-") if t.trim_start().starts_with('-') && t.matches('-').count() == 1 => "+".to_string(),
                Some(o) => o.to_string(),
                None => "+".to_string(),
            };
            if t.is_empty() { "_".to_string() } else { format!("{} {} _", t, op) }
        };
        self.decouper(&neuf);
        self.champ = 2 + self.entrees.len().saturating_sub(1);
    }

    /// une entrée de moins : la dernière place de la dernière entrée s'en va, avec ce qui la sépare de la précédente
    /// (« , » ou l'opération)
    fn retirer_entree(&mut self) {
        let n = match self.entrees.len() {
            0 => return,
            n => n - 1,
        };
        let p = match self.morceaux.iter().rposition(|m| matches!(m, Morceau::Entree(i) if *i == n)) {
            Some(p) => p,
            None => return,
        };
        let sep = |c: char| ",+-*/%<>=!&|".contains(c);
        let mut fait = false;
        if p > 0 {
            if let Morceau::Texte(t) = &mut self.morceaux[p - 1] {
                let tt = t.trim_end();
                let coupe = tt.trim_end_matches(sep);
                if coupe.len() < tt.len() {
                    *t = coupe.trim_end().to_string();
                    fait = true;
                }
            }
        }
        if !fait && p + 1 < self.morceaux.len() {
            if let Morceau::Texte(t) = &mut self.morceaux[p + 1] {
                let tt = t.trim_start();
                let coupe = tt.trim_start_matches(sep);
                if coupe.len() < tt.len() {
                    *t = coupe.trim_start().to_string();
                    if !t.is_empty() && !t.starts_with(')') && !t.starts_with(']') {
                        t.insert(0, ' ');
                    }
                }
            }
        }
        self.morceaux.remove(p);
        let q = self.quoi();
        self.decouper(&q);
        self.champ = self.champ.min(self.nb_champs() - 1);
    }

    fn ajouter_sortie(&mut self) {
        let mut k = 1;
        while self.connues.contains(&format!("l{}", k)) || self.sorties.iter().any(|s| premier_mot(s) == format!("l{}", k)) {
            k += 1;
        }
        self.sorties.push(format!("l{}", k));
        self.anciennes.push(String::new());
        self.champ = 2 + self.entrees.len() + self.sorties.len() - 1;
    }

    fn retirer_sortie(&mut self) {
        self.sorties.pop();
        self.anciennes.pop();
        self.champ = self.champ.min(self.nb_champs() - 1);
    }

    fn nb_champs(&self) -> usize {
        2 + self.entrees.len() + self.sorties.len()
    }

    /// le texte du champ n
    fn valeur(&self, n: usize) -> String {
        let ne = self.entrees.len();
        match n {
            0 => self.nom.clone(),
            1 => self.quoi(),
            k if k < 2 + ne => self.entrees[k - 2].clone(),
            k => self.sorties.get(k - 2 - ne).map(|s| premier_mot(s)).unwrap_or_default(),
        }
    }

    /// le champ n reçoit le texte v
    fn poser(&mut self, n: usize, v: String) {
        let ne = self.entrees.len();
        match n {
            0 => self.nom = v,
            1 => self.decouper(&v),
            k if k < 2 + ne => self.entrees[k - 2] = v,
            k => {
                if let Some(s) = self.sorties.get_mut(k - 2 - ne) {
                    let reste = s[premier_mot(s).len()..].to_string();
                    *s = v + &reste;
                }
            }
        }
    }

    fn taper(&mut self, c: char) {
        let n = self.champ;
        let mut v = self.valeur(n);
        // dans un nom (de case, d'entrée, de sortie) : seulement des lettres, des chiffres et « _ »
        if n != 1 && !lettre(c) {
            return;
        }
        if n >= 2 && n < 2 + self.entrees.len() && v == "_" {
            v.clear();
        }
        v.push(c);
        self.poser(n, v);
    }

    fn effacer(&mut self) {
        let n = self.champ;
        let mut v = self.valeur(n);
        v.pop();
        self.poser(n, v);
    }

    /// la ligne de code que la case deviendra
    pub fn ligne_code(&self) -> String {
        let mut t = self.retrait.clone();
        if !self.nom.trim().is_empty() {
            t.push_str(self.nom.trim());
            t.push_str(" = ");
        } else {
            t.push_str(&self.sans_nom);
        }
        t.push_str(self.quoi().trim());
        let sorties: Vec<&String> = self.sorties.iter().filter(|s| !premier_mot(s).is_empty()).collect();
        if !sorties.is_empty() {
            t.push_str(" -> ");
            t.push_str(&sorties.iter().map(|s| s.as_str()).collect::<Vec<_>>().join(", "));
        }
        if !self.apres.is_empty() {
            t.push_str(" apres ");
            t.push_str(&self.apres);
        }
        if !self.commentaire.is_empty() {
            t.push_str("  ");
            t.push_str(&self.commentaire);
        }
        t
    }

    /// ce qui ne va pas encore (un nom qui n'en est pas un, une sortie donnée deux fois…), ou None
    fn probleme(&self) -> Option<String> {
        if !self.nom.is_empty() && (!nom_valide(&self.nom) || MOTS.contains(&self.nom.as_str())) {
            return Some(format!("« {} » ne peut pas être un nom de case", self.nom));
        }
        if self.quoi().trim().is_empty() {
            return Some("la case ne fait rien : écrivez ce qu'elle fait".into());
        }
        let mut vus: Vec<String> = vec![];
        for s in &self.sorties {
            let n = premier_mot(s);
            if n.is_empty() {
                continue;
            }
            if !nom_valide(&n) {
                return Some(format!("« {} » n'est pas un nom de liaison", n));
            }
            if vus.contains(&n) || (self.connues.contains(&n) && !self.anciennes.contains(&n)) {
                return Some(format!("la liaison {} est déjà donnée ailleurs", n));
            }
            vus.push(n);
        }
        None
    }

    /// écrire la case dans le texte : sa ligne, et les sorties renommées partout dans la réaction
    fn ecrire(&self, source: &str, r: &Reaction) -> String {
        let mut v: Vec<String> = source.split('\n').map(|x| x.to_string()).collect();
        if self.ligne < v.len() {
            let cr = v[self.ligne].ends_with('\r');
            v[self.ligne] = self.ligne_code() + if cr { "\r" } else { "" };
        }
        // une sortie renommée : les cases qui la lisaient lisent le nouveau nom
        for (i, s) in self.sorties.iter().enumerate() {
            let (ancien, neuf) = (self.anciennes.get(i).cloned().unwrap_or_default(), premier_mot(s));
            if ancien.is_empty() || neuf.is_empty() || ancien == neuf {
                continue;
            }
            for k in r.ligne..=r.fin.min(v.len().saturating_sub(1)) {
                if k == self.ligne {
                    continue;
                }
                let l = v[k].clone();
                let fc = fin_code(l.trim_end_matches('\r'));
                let mut places: Vec<(usize, usize)> = mots(&l, 0, fc).into_iter().filter(|w| w.0 == ancien && w.3 != '.')
                    .map(|w| (w.1, w.2)).collect();
                if k == r.ligne {
                    // l'en-tête : seulement le résultat (« -> r »)
                    let fl = l.find("->").unwrap_or(l.len());
                    places.retain(|p| p.0 > fl);
                }
                if !places.is_empty() {
                    v[k] = remplacer_places(&l, &places, &neuf);
                }
            }
        }
        v.join("\n")
    }
}

/// le premier mot (le nom) d'une sortie écrite « a lourd » ou « r: flottant »
fn premier_mot(s: &str) -> String {
    s.trim().chars().take_while(|&c| lettre(c)).collect()
}

impl Paillasse {
    /// 0.72 : la fenêtre d'édition est-elle ouverte (le clavier va alors à elle) ?
    pub fn en_edition(&self) -> bool {
        self.edition.is_some()
    }

    /// 0.72 : ouvrir la fenêtre d'édition de la case de la ligne « ligne » (dans le texte « source »)
    pub fn ouvrir_edition(&mut self, source: &str, ligne: usize) -> bool {
        let nom = match self.reaction().filter(|r| !r.carte) {
            Some(r) => r.nom.clone(),
            None => return false,
        };
        let r = match analyser(source).into_iter().find(|q| q.nom == nom) {
            Some(r) => r,
            None => return false,
        };
        self.edition = Edition::depuis(source, &r, ligne);
        if self.edition.is_some() {
            self.message = Some("la case s'édite : Tab passe au champ suivant, Entrée l'écrit dans le texte, Échap renonce".into());
        }
        self.edition.is_some()
    }

    /// 0.72 : un caractère tapé, pour la fenêtre d'édition
    pub fn caractere(&mut self, c: char) -> Reponse {
        match self.edition.as_mut() {
            Some(e) if !c.is_control() => {
                e.taper(c);
                Reponse::Redessiner
            }
            _ => Reponse::Rien,
        }
    }

    /// 0.72 : une touche pour la fenêtre d'édition (Tab, flèches, Retour, Entrée, Échap)
    fn touche_edition(&mut self, vk: u32, source: &str) -> Reponse {
        let e = match self.edition.as_mut() {
            Some(e) => e,
            None => return Reponse::Rien,
        };
        match vk {
            0x09 | 0x28 => e.champ = (e.champ + 1) % e.nb_champs(),
            0x26 => e.champ = (e.champ + e.nb_champs() - 1) % e.nb_champs(),
            0x08 => e.effacer(),
            0x0D => return self.ecrire_edition(source),
            0x1B => {
                self.edition = None;
                self.message = Some("rien n'est écrit".into());
            }
            _ => return Reponse::Rien,
        }
        Reponse::Redessiner
    }

    fn ecrire_edition(&mut self, source: &str) -> Reponse {
        let e = match self.edition.clone() {
            Some(e) => e,
            None => return Reponse::Rien,
        };
        if let Some(p) = e.probleme() {
            self.message = Some(p.clone());
            return Reponse::Message(p);
        }
        let r = match analyser(source).into_iter().find(|q| q.nom == e.reaction) {
            Some(r) => r,
            None => {
                self.edition = None;
                return Reponse::Message("la réaction de cette case n'est plus dans le texte".into());
            }
        };
        self.edition = None;
        let s = e.ecrire(source, &r);
        self.message = Some(format!("la case est écrite, ligne {}", e.ligne + 1));
        if s == source {
            Reponse::Redessiner
        } else {
            Reponse::Texte { source: s, ligne: e.ligne }
        }
    }

    /// 0.72 : un clic quand la fenêtre d'édition est ouverte : un champ, − ou +, Écrire, Annuler ; ailleurs, rien
    fn clic_edition(&mut self, x: i32, y: i32, source: &str) -> Reponse {
        let z = match self.edition.as_ref() {
            Some(e) => e.zones.iter().find(|z| x >= z.0 && x < z.0 + z.2 && y >= z.1 && y < z.1 + z.3).map(|z| z.4),
            None => return Reponse::Rien,
        };
        let e = self.edition.as_mut().unwrap();
        match z {
            Some(Zone::Champ(n)) => e.champ = n,
            Some(Zone::Moins(false)) => e.retirer_entree(),
            Some(Zone::Plus(false)) => e.ajouter_entree(),
            Some(Zone::Moins(true)) => e.retirer_sortie(),
            Some(Zone::Plus(true)) => e.ajouter_sortie(),
            Some(Zone::Ecrire) => return self.ecrire_edition(source),
            Some(Zone::Annuler) => {
                self.edition = None;
                self.message = Some("rien n'est écrit".into());
            }
            None => {}
        }
        Reponse::Redessiner
    }

    /// 0.72 : dessiner la fenêtre d'édition par-dessus la paillasse (les textes qu'elle couvre sont retirés)
    fn dessiner_edition(&mut self, im: &mut Image, tx: &mut Vec<TexteP>, l: i32, h: i32) {
        let (cl, ch) = (self.car_l, self.car_h);
        let e1 = self.px(1).max(1);
        let e2 = self.px(2).max(2);
        let e = match self.edition.as_mut() {
            Some(e) => e,
            None => return,
        };
        let marge = cl;
        let lf = (58 * cl).min(l - 2 * marge).max(30 * cl);
        let rang = ch + ch / 2 + 4;
        let n_lignes = 9 + e.entrees.len() + e.sorties.len();
        let hf = (n_lignes as i32 * rang + rang).min(h - 2 * marge);
        let xf = (l - lf - marge).max(marge);
        let yf = (ch * 3).min(h - hf - marge).max(marge);
        // ce qui est dessous ne se lit plus
        tx.retain(|t| !(t.x >= xf - 4 * cl && t.x < xf + lf && t.y >= yf - ch && t.y < yf + hf));
        im.plein(xf + e2 * 2, yf + e2 * 2, lf, hf, 0x101216);
        im.plein(xf, yf, lf, hf, 0x2A303C);
        im.cadre(xf, yf, lf, hf, e2, OR);
        im.plein(xf, yf, lf, rang, 0x353C4A);
        e.zones.clear();
        let mut y = yf + 3;
        tx.push(TexteP { x: xf + cl, y, texte: format!("Éditer la case, ligne {}", e.ligne + 1), couleur: OR });
        y += rang + 2;
        let xc = xf + 18 * cl;
        let lc = lf - 19 * cl;
        let champ = |e: &mut Edition, im: &mut Image, tx: &mut Vec<TexteP>, y: i32, etiquette: &str, n: usize, x_et: i32| {
            tx.push(TexteP { x: x_et, y: y + 2, texte: etiquette.to_string(), couleur: PALE });
            let actif = e.champ == n;
            im.plein(xc, y, lc, ch + 6, if actif { 0x1C2028 } else { 0x23272F });
            im.cadre(xc, y, lc, ch + 6, e1, if actif { OR } else { 0x4A5262 });
            let mut v = e.valeur(n);
            if n >= 2 && n < 2 + e.entrees.len() && (v.is_empty() || v == "_") && !actif {
                v = "_ (libre)".into();
            }
            let place = (lc / cl - 2).max(4) as usize;
            let nb = v.chars().count();
            let mut montre: String = if nb > place { v.chars().skip(nb - place).collect() } else { v };
            if actif {
                montre.push('|');
            }
            tx.push(TexteP { x: xc + cl / 2, y: y + 3, texte: montre, couleur: ENCRE });
            e.zones.push((xc, y, lc, ch + 6, Zone::Champ(n)));
        };
        champ(e, im, tx, y, "nom (facultatif)", 0, xf + cl);
        y += rang;
        champ(e, im, tx, y, "ce qu'elle fait", 1, xf + cl);
        y += rang + 4;
        // les entrées et les sorties : leur nombre (− et +), puis un champ par nom
        let bouton = |e: &mut Edition, im: &mut Image, tx: &mut Vec<TexteP>, x: i32, y: i32, t: &str, z: Zone| {
            let lb = 3 * cl;
            im.plein(x, y, lb, ch + 6, 0x3A4252);
            im.cadre(x, y, lb, ch + 6, e1, 0x5A6478);
            tx.push(TexteP { x: x + cl, y: y + 3, texte: t.to_string(), couleur: ENCRE });
            e.zones.push((x, y, lb, ch + 6, z));
        };
        for sortie in [false, true] {
            let n = if sortie { e.sorties.len() } else { e.entrees.len() };
            let titre = if sortie { format!("sorties : {}", n) } else { format!("entrées : {}", n) };
            tx.push(TexteP { x: xf + cl, y: y + 3, texte: titre, couleur: if sortie { 0xE0A040 } else { 0x70B0A0 } });
            bouton(e, im, tx, xc, y, "-", Zone::Moins(sortie));
            bouton(e, im, tx, xc + 4 * cl, y, "+", Zone::Plus(sortie));
            y += rang;
            for i in 0..n {
                let k = if sortie { 2 + e.entrees.len() + i } else { 2 + i };
                champ(e, im, tx, y, &format!("  {} {}", if sortie { "sortie" } else { "entrée" }, i + 1), k, xf + cl);
                y += rang;
            }
            y += 4;
        }
        // la ligne de code qui sortira, et ce qui ne va pas
        tx.push(TexteP { x: xf + cl, y, texte: "le code :".into(), couleur: PALE });
        y += ch + 4;
        let code = e.ligne_code().trim().to_string();
        let place = (lf / cl - 2).max(10) as usize;
        let code: String = if code.chars().count() > place { code.chars().take(place - 1).collect::<String>() + "…" } else { code };
        tx.push(TexteP { x: xf + cl, y, texte: code, couleur: 0xC8C4B8 });
        y += rang;
        if let Some(p) = e.probleme() {
            tx.push(TexteP { x: xf + cl, y, texte: p, couleur: FAUX });
        }
        y += rang;
        let lb = 16 * cl;
        for (k, (t, z)) in [("Écrire (Entrée)", Zone::Ecrire), ("Annuler (Échap)", Zone::Annuler)].iter().enumerate() {
            let x = xf + cl + k as i32 * (lb + 2 * cl);
            im.plein(x, y, lb, ch + 8, if k == 0 { 0x4A6A3A } else { 0x3A4252 });
            im.cadre(x, y, lb, ch + 8, e1, if k == 0 { VRAI } else { 0x5A6478 });
            tx.push(TexteP { x: x + cl, y: y + 4, texte: t.to_string(), couleur: ENCRE });
            e.zones.push((x, y, lb, ch + 8, *z));
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
    let mut faces: Option<String> = None;
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
            "--faces" => faces = args.get(i + 1).cloned(),
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
    if let Some(f) = &faces {
        p.faces = Faces::depuis_adn(f);
        if p.faces.is_none() {
            println!("message : {} n'a pas de faces (rangez-le de nouveau)", f);
        }
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
        let mut en_edition: Option<usize> = None;
        for l in t.lines() {
            let m: Vec<&str> = l.split('#').next().unwrap_or("").split_whitespace().collect();
            if m.is_empty() {
                continue;
            }
            let n = |k: usize| m.get(k).and_then(|v| v.parse::<i32>().ok()).unwrap_or(0);
            let ouverte = p.edition.is_some();
            let rep = match m[0] {
                "bas" => p.souris(Souris::Bas, n(1), n(2), &source),
                "bouge" => p.souris(Souris::Bouge, n(1), n(2), &source),
                "haut" => p.souris(Souris::Haut, n(1), n(2), &source),
                "double" => p.souris(Souris::Double, n(1), n(2), &source),
                "droit" => p.souris(Souris::Droit, n(1), n(2), &source),
                // ecrire TEXTE : ce qu'on tape dans la boîte du clic droit, puis Entrée
                // 0.72 : la fenêtre d'édition ouverte : la ligne entière de la case devient TEXTE, et la fenêtre se ferme
                "ecrire" if p.edition.is_some() => {
                    let ligne = p.edition.take().map(|e| e.ligne).unwrap_or(0);
                    let t = l.splitn(2, char::is_whitespace).nth(1).unwrap_or("").trim();
                    Reponse::Texte { source: editer_ligne(&source, ligne, t), ligne }
                }
                "ecrire" => match en_edition.take() {
                    Some(ligne) => {
                        let t = l.splitn(2, char::is_whitespace).nth(1).unwrap_or("").trim();
                        Reponse::Texte { source: editer_ligne(&source, ligne, t), ligne }
                    }
                    None => Reponse::Message("rien à écrire : pas de case en édition (clic droit d'abord)".into()),
                },
                "touche" => p.touche(n(1) as u32, &source),
                // 0.72 : car TEXTE : des caractères tapés (pour la fenêtre d'édition)
                "car" => {
                    let t = l.splitn(2, char::is_whitespace).nth(1).unwrap_or("").trim_end();
                    for c in t.chars() {
                        p.caractere(c);
                    }
                    Reponse::Redessiner
                }
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
                // choisir NOM : la case de la fonction NOM sur la carte du programme ; explique : la fenêtre des explications
                "choisir" => {
                    // une réaction : son onglet ; sinon la case de la fonction sur la carte
                    if let Some(k) = p.reactions.iter().position(|r| !r.carte && Some(r.nom.as_str()) == m.get(1).copied()) {
                        p.courante = k;
                        p.choisi = None;
                    } else if let Some(k) = p.reactions.iter().position(|r| r.carte) {
                        p.courante = k;
                        p.choisi = p.reactions[k].atomes.iter().position(|a| Some(a.nom.as_str()) == m.get(1).copied());
                    }
                    Reponse::Redessiner
                }
                "explique" => {
                    println!("--- explications\n{}", p.explication().replace("\r\n", "\n").trim_end());
                    Reponse::Rien
                }
                // 0.69 : palette : la montrer ; poser NOM : poser la case NOM de la palette dans la réaction montrée
                "palette" => {
                    p.palette_ouverte = true;
                    Reponse::Redessiner
                }
                // 0.69b : après « droit X Y » dans le vide : case NOM (ou case vide) : la case choisie au menu
                "case" => {
                    let nom = m.get(1).copied().unwrap_or("vide");
                    let k = PALETTE.iter().position(|c| c.nom == nom);
                    if k.is_none() && nom != "vide" {
                        Reponse::Message(format!("pas de case « {} » dans la palette", nom))
                    } else {
                        p.poser_ici(k, &source)
                    }
                }
                // 0.70 : page : une page neuve
                "page" => p.nouvelle_page(&source),
                "poser" => match PALETTE.iter().position(|c| Some(c.nom) == m.get(1).copied()) {
                    Some(k) => p.poser_case(k, &source),
                    None => Reponse::Message(format!("pas de case « {} » dans la palette", m.get(1).copied().unwrap_or(""))),
                },
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
                Reponse::Palette { x, y } => println!("le menu des cases, en ({}, {})", x, y),
                Reponse::Message(m) => println!("message : {}", m),
                Reponse::Editer { source: s, ligne, texte, .. } => {
                    if let Some(s) = s {
                        source = s;
                        p.lire(&source);
                    }
                    en_edition = Some(ligne);
                    println!("édition de la ligne {} : {}", ligne + 1, texte);
                }
                _ => {}
            }
            // 0.72 : la fenêtre d'édition vient de s'ouvrir : ce qu'elle édite
            if !ouverte {
                if let Some(e) = &p.edition {
                    println!("édition de la ligne {} : {}", e.ligne + 1, e.ligne_code().trim());
                }
            }
            if let Some(m) = &p.message {
                if m.starts_with("la case est à la vague") {
                    println!("message : {}", m);
                }
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
        for r in p.reactions.iter().filter(|r| !r.carte) {
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
