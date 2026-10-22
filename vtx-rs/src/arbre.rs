#![cfg_attr(not(windows), allow(dead_code))]
//! L'arbre des liaisons : ce que la mémoire contient après l'exécution, vu comme des objets reliés.
//!
//! Le tas (étage 3, de 8 388 608 au pointeur rangé en 14 680 056) contient les objets du programme ; une poignée
//! `#03xxxxxx` les désigne. On reconnaît chaque objet par sa forme :
//!   tableau : [n, capacité, adresse des données]          dico : [n, capacité, clés, valeurs, états, ouvert]
//!   texte   : [longueur, caractères…]
//! Les racines sont les objets que rien dans le tas ne désigne (ils ne sont tenus que par les variables du programme).
//! Le journal des hypothèses (l'ARN en attente de validation) est à partir de 15 728 640.
//! Indépendant de Windows : la fenêtre le dessine, `vtx arbre` l'écrit.

pub const TAS_DEBUT: u32 = 8_388_608;
pub const TAS_HAUT: u32 = 14_680_056;
pub const TAS_FIN: u32 = 14_680_048;
pub const HYP_DEBUT: u32 = 15_728_640;
pub const HYP_PTR: u32 = 16_777_200;
pub const HYP_N: u32 = 16_777_201;
const MASQUE: u32 = 0x00FF_FFFF;
const MAX_ENFANTS: usize = 256;
const MAX_PROFONDEUR: usize = 8;

#[derive(Clone, Debug)]
pub struct Noeud {
    /// le texte de la ligne
    pub texte: String,
    /// le mot dont la couleur est montrée (sa couleur dans le cube)
    pub mot: Option<u32>,
    /// un état logique à quatre valeurs (0 inconnu, 1 faux, 2 vrai, 3 variable)
    pub logique: Option<u8>,
    pub enfants: Vec<Noeud>,
}

impl Noeud {
    pub fn feuille(texte: String, mot: Option<u32>) -> Noeud {
        Noeud { texte, mot, logique: None, enfants: Vec::new() }
    }
}

pub const NOMS_LOGIQUES: [&str; 4] = ["inconnu", "faux", "vrai", "variable"];

/// Ce que dit un mot, lu comme un point du cube et comme un mot biologique.
pub fn decoder(v: u32) -> Vec<String> {
    let (r, g, b, a) = (v >> 24, (v >> 16) & 255, (v >> 8) & 255, v & 255);
    let quits: String = (0..16).rev().map(|k| char::from(b'0' + ((v >> (2 * k)) & 3) as u8)).collect();
    let mut l = vec![
        format!("{} (signé {})  ·  #{:08X}", v, v as i32, v),
        format!("couleur : rouge {}, vert {}, bleu {}, alpha {}", r, g, b, a),
        format!("quits : {} {} {} {}", &quits[0..4], &quits[4..8], &quits[8..12], &quits[12..16]),
    ];
    // les mêmes quits en logique de Belnap : · inconnu, f faux, v vrai, ± variable
    let lg: String = (0..16).rev().map(|k| ['·', 'f', 'v', '±'][((v >> (2 * k)) & 3) as usize]).collect();
    let lg: Vec<char> = lg.chars().collect();
    let g = |i: usize| lg[i..i + 4].iter().collect::<String>();
    l.push(if v <= 3 {
        format!("logique : {}", ["inconnu", "faux", "vrai", "variable"][v as usize])
    } else {
        format!("logique (16 quits) : {} {} {} {}", g(0), g(4), g(8), g(12))
    });
    let f = f32::from_bits(v);
    if f.is_finite() && f != 0.0 && f.abs() > 1e-6 && f.abs() < 1e9 {
        l.push(format!("lu comme flottant : {}", f));
    }
    // la convention biologique : alpha = quit étage, quit type, lettre de la voie (A, G, C), bit d'état T/U
    let voie = (a >> 2) & 3;
    let lettre = ["aucune", "A (rouge)", "G (vert)", "C (bleu)"][voie as usize];
    let brin = if a & 1 == 1 { "T : ADN (mémoire validée)" } else { "U : ARN (copie de travail, hypothèse)" };
    l.push(format!("biologique : voie {} · {} · étage {} · type {}", lettre, brin, a >> 6, (a >> 4) & 3));
    if v >> 24 <= 3 && v & MASQUE != 0 {
        l.push(format!("adresse : @{}[{}]", v >> 24, v & MASQUE));
    }
    l
}

/// Une ligne courte pour un mot ordinaire.
pub fn court(v: u32) -> String {
    if v < 65536 {
        format!("{}  ·  #{:08X}", v, v)
    } else if v >= 0xFFFF_0000 {
        format!("{}  ·  #{:08X}", v as i32, v)
    } else {
        format!("#{:08X}", v)
    }
}

pub struct Lecteur<'a> {
    pub lit: &'a dyn Fn(u32, u32) -> u32,
    haut: u32,
}

impl<'a> Lecteur<'a> {
    pub fn new(lit: &'a dyn Fn(u32, u32) -> u32) -> Lecteur<'a> {
        let h = lit(3, TAS_HAUT);
        let haut = if h < TAS_DEBUT || h > TAS_FIN { TAS_DEBUT } else { h };
        Lecteur { lit, haut }
    }
    fn l(&self, p: u32) -> u32 {
        (self.lit)(3, p & MASQUE)
    }
    fn dans_tas(&self, p: u32) -> bool {
        p >= TAS_DEBUT && p < self.haut
    }
    pub fn mots_utilises(&self) -> u32 {
        self.haut - TAS_DEBUT
    }
    /// Un texte : la longueur (1 à 65 536) puis des caractères valides.
    pub fn texte(&self, h: u32) -> Option<String> {
        let (e, a) = (h >> 24, h & MASQUE);
        if e > 3 || (e == 3 && !self.dans_tas(a)) {
            return None;
        }
        let n = (self.lit)(e, a);
        if n == 0 || n > 65536 || a as u64 + n as u64 >= 1 << 24 {
            return None;
        }
        let mut s = String::new();
        for k in 0..n {
            let c = (self.lit)(e, a + 1 + k);
            match char::from_u32(c) {
                Some(ch) if c == 9 || c == 10 || c == 13 || c >= 32 => s.push(ch),
                _ => return None,
            }
        }
        Some(s)
    }
    fn est_dico(&self, p: u32) -> bool {
        let (n, cap) = (self.l(p), self.l(p + 1));
        cap >= 16 && cap.is_power_of_two() && cap <= 1 << 22 && n <= cap && self.l(p + 5) <= 1
            && [2, 3, 4].iter().all(|&k| { let x = self.l(p + k); self.dans_tas(x) && x + cap <= self.haut })
    }
    fn est_tableau(&self, p: u32) -> bool {
        let (n, cap, d) = (self.l(p), self.l(p + 1), self.l(p + 2));
        cap >= 4 && cap <= 1 << 22 && n <= cap && self.dans_tas(d) && d + cap <= self.haut
    }
    /// La sorte de l'objet désigné par une poignée du tas.
    pub fn sorte(&self, h: u32) -> Option<&'static str> {
        if h >> 24 != 3 || !self.dans_tas(h & MASQUE) {
            return None;
        }
        let p = h & MASQUE;
        if self.est_dico(p) {
            Some("dico")
        } else if self.est_tableau(p) {
            Some("tableau")
        } else if self.texte(h).is_some() {
            Some("texte")
        } else {
            None
        }
    }
    /// Les poignées contenues dans un objet (ses liaisons).
    fn liaisons(&self, h: u32) -> Vec<u32> {
        let p = h & MASQUE;
        let mut r = Vec::new();
        match self.sorte(h) {
            Some("tableau") => {
                let (n, d) = (self.l(p), self.l(p + 2));
                r.extend((0..n.min(1 << 16)).map(|k| self.l(d + k)));
            }
            Some("dico") => {
                let (cap, ks, vs) = (self.l(p + 1), self.l(p + 2), self.l(p + 3));
                for k in 0..cap {
                    if self.l(ks + k) != 0 {
                        r.push(self.l(ks + k));
                        r.push(self.l(vs + k));
                    }
                }
            }
            _ => {}
        }
        r.retain(|&v| self.sorte(v).is_some());
        r
    }

    /// Le noeud d'une valeur : un objet du tas avec ses liaisons, ou un mot.
    pub fn noeud(&self, v: u32, prefixe: &str, prof: usize, chemin: &mut Vec<u32>) -> Noeud {
        let p = v & MASQUE;
        let sorte = self.sorte(v);
        if sorte.is_some() && chemin.contains(&v) {
            return Noeud::feuille(format!("{}↺ déjà vu plus haut (@3[{}])", prefixe, p), Some(v));
        }
        match sorte {
            Some("texte") => {
                let t = self.texte(v).unwrap_or_default();
                let t = if t.chars().count() > 60 { format!("{}…", t.chars().take(60).collect::<String>()) } else { t };
                Noeud::feuille(format!("{}texte \"{}\"  ·  @3[{}]", prefixe, t, p), Some(v))
            }
            Some("tableau") if prof < MAX_PROFONDEUR => {
                let (n, cap, d) = (self.l(p), self.l(p + 1), self.l(p + 2));
                chemin.push(v);
                // un tableau dont toutes les cases se lisent comme des textes (les textes écrits dans le programme sont
                // à l'étage 0, sans poignée du tas) : on les montre comme textes
                let textes = n > 0 && (0..n.min(MAX_ENFANTS as u32)).all(|k| self.texte(self.l(d + k)).is_some());
                // un tableau dont toutes les cases ont la forme d'un flottant ordinaire (et pas d'un petit entier) :
                // on montre les valeurs flottantes
                let flottant = |v: u32| v == 0 || v == 0x8000_0000 || { let e = (v >> 23) & 255; (100..=160).contains(&e) };
                let flottants = !textes && n > 0 && (0..n.min(MAX_ENFANTS as u32)).all(|k| flottant(self.l(d + k)))
                    && (0..n.min(MAX_ENFANTS as u32)).any(|k| self.l(d + k) & 0x7FFF_FFFF != 0);
                let mut enfants: Vec<Noeud> = (0..n.min(MAX_ENFANTS as u32)).map(|k| {
                    let x = self.l(d + k);
                    if flottants {
                        return Noeud::feuille(format!("[{}] {}  ·  #{:08X}", k, f32::from_bits(x), x), Some(x));
                    }
                    match (textes, self.texte(x)) {
                        (true, Some(t)) if self.sorte(x).is_none() => Noeud::feuille(format!("[{}] texte \"{}\"", k, t), Some(x)),
                        _ => self.noeud(x, &format!("[{}] ", k), prof + 1, chemin),
                    }
                }).collect();
                if n as usize > MAX_ENFANTS {
                    enfants.push(Noeud::feuille(format!("… et {} de plus", n as usize - MAX_ENFANTS), None));
                }
                chemin.pop();
                Noeud { texte: format!("{}tableau{} de {} (capacité {})  ·  @3[{}] → données @3[{}]", prefixe,
                                       if flottants { " de flottants" } else { "" }, n, cap, p, d),
                        mot: Some(v), logique: None, enfants }
            }
            Some("dico") if prof < MAX_PROFONDEUR => {
                let (n, cap, ks, vs, qs, ouvert) = (self.l(p), self.l(p + 1), self.l(p + 2), self.l(p + 3), self.l(p + 4), self.l(p + 5));
                chemin.push(v);
                let mut enfants = Vec::new();
                for k in 0..cap {
                    let cle = self.l(ks + k);
                    if cle == 0 {
                        continue;
                    }
                    if enfants.len() == MAX_ENFANTS {
                        enfants.push(Noeud::feuille(format!("… et {} de plus", n as usize - MAX_ENFANTS), None));
                        break;
                    }
                    let nom = self.texte(cle).unwrap_or_else(|| court(cle));
                    let q = (self.l(qs + k) & 3) as u8;
                    let mut e = self.noeud(self.l(vs + k), &format!("\"{}\" = ", nom), prof + 1, chemin);
                    e.texte = format!("{}   [{}]", e.texte, NOMS_LOGIQUES[q as usize]);
                    e.logique = Some(q);
                    enfants.push(e);
                }
                chemin.pop();
                let sorte = if ouvert == 1 { "ouvert : absent = inconnu" } else { "fermé : absent = faux" };
                Noeud { texte: format!("{}dico de {} clés ({})  ·  @3[{}]", prefixe, n, sorte, p), mot: Some(v), logique: None, enfants }
            }
            Some(s) => Noeud::feuille(format!("{}{} @3[{}] (trop profond)", prefixe, s, p), Some(v)),
            None => Noeud::feuille(format!("{}{}", prefixe, court(v)), Some(v)),
        }
    }

    /// Les objets du tas que désigne une poignée trouvée dans les étages (variables, données, autres objets).
    pub fn objets(&self) -> Vec<u32> {
        let mut vus = std::collections::BTreeSet::new();
        for e in 0..4u32 {
            for a in 0..=MASQUE {
                let v = (self.lit)(e, a);
                if v >> 24 == 3 && self.dans_tas(v & MASQUE) && (e != 3 || a < HYP_DEBUT) {
                    vus.insert(v);
                }
            }
        }
        vus.into_iter().filter(|&v| self.sorte(v).is_some()).collect()
    }

    /// Les racines : les objets que rien dans le tas ne désigne.
    pub fn racines(&self) -> Vec<u32> {
        let objets = self.objets();
        let mut tenus = std::collections::HashSet::new();
        for &o in &objets {
            tenus.extend(self.liaisons(o));
        }
        objets.into_iter().filter(|o| !tenus.contains(o)).collect()
    }

    /// Le journal des hypothèses : (étage, adresse, ancienne valeur, valeur actuelle).
    pub fn hypotheses(&self) -> (u32, Vec<(u32, u32, u32, u32)>) {
        let fin = self.l(HYP_PTR);
        let ouvertes = self.l(HYP_N);
        let mut r = Vec::new();
        if fin >= HYP_DEBUT && fin < HYP_PTR {
            let mut p = HYP_DEBUT;
            while p + 2 < fin && r.len() < 4096 {
                let (e, a, ancien) = (self.l(p), self.l(p + 1), self.l(p + 2));
                r.push((e & 3, a & MASQUE, ancien, (self.lit)(e & 3, a & MASQUE)));
                p += 3;
            }
        }
        (ouvertes, r)
    }
}

/// L'arbre complet après une exécution.
pub fn arbre(lit: &dyn Fn(u32, u32) -> u32) -> Vec<Noeud> {
    let lec = Lecteur::new(lit);
    let mut r = Vec::new();
    let racines = lec.racines();
    let mut tas = Noeud {
        texte: format!("tas (étage 3) : {} mots utilisés, {} objet(s) tenu(s) par le programme", lec.mots_utilises(), racines.len()),
        mot: None,
        logique: None,
        enfants: Vec::new(),
    };
    for h in racines {
        tas.enfants.push(lec.noeud(h, "", 0, &mut Vec::new()));
    }
    r.push(tas);
    let (ouvertes, hyp) = lec.hypotheses();
    if !hyp.is_empty() {
        let mut n = Noeud {
            texte: format!("hypothèses : {} écriture(s) notée(s), {} hypothèse(s) ouverte(s) (ARN : pas encore validée)", hyp.len(), ouvertes),
            mot: None,
            logique: Some(if ouvertes > 0 { 0 } else { 2 }),
            enfants: Vec::new(),
        };
        for (e, a, ancien, actuel) in hyp.into_iter().take(MAX_ENFANTS) {
            n.enfants.push(Noeud::feuille(format!("@{}[{}] : avant {} → maintenant {}", e, a, court(ancien), court(actuel)), Some(actuel)));
        }
        r.push(n);
    }
    r
}

/// Le noeud d'un mot choisi (un clic dans le cube, ou la commande « mot ») : son décodage, puis ce qu'il désigne.
pub fn noeud_mot(lit: &dyn Fn(u32, u32) -> u32, etage: u32, adr: u32) -> Noeud {
    let lec = Lecteur::new(lit);
    let v = lit(etage & 3, adr & MASQUE);
    let mut n = Noeud { texte: format!("@{}[{}]", etage, adr), mot: Some(v), logique: None, enfants: Vec::new() };
    for l in decoder(v) {
        n.enfants.push(Noeud::feuille(l, None));
    }
    if lec.sorte(v).is_some() {
        n.enfants.push(lec.noeud(v, "désigne : ", 0, &mut Vec::new()));
    }
    n
}

/// L'arbre en texte (la commande `vtx arbre`, et les tests).
pub fn ecrire(noeuds: &[Noeud]) -> String {
    fn rec(n: &Noeud, retrait: &str, dernier: bool, racine: bool, s: &mut String) {
        if racine {
            s.push_str(&n.texte);
        } else {
            s.push_str(retrait);
            s.push_str(if dernier { "└─ " } else { "├─ " });
            s.push_str(&n.texte);
        }
        s.push('\n');
        let suite = if racine { String::new() } else { format!("{}{}", retrait, if dernier { "   " } else { "│  " }) };
        for (i, e) in n.enfants.iter().enumerate() {
            rec(e, &suite, i + 1 == n.enfants.len(), false, s);
        }
    }
    let mut s = String::new();
    for n in noeuds {
        rec(n, "", true, true, &mut s);
    }
    s
}
