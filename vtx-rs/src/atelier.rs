// L'atelier vtx en mode console : « vtx atelier programme.vtx ».
// À gauche, l'éditeur (couleurs du langage, numéros de ligne). À droite, le cube : un étage de la mémoire du SPU
// dessiné en couleurs, chaque mot #RRGGBBAA étant un pixel de sa couleur (deux pixels par caractère, avec un
// demi-carré). En bas à droite, ce qu'a donné le programme : instructions, sorties, console, erreurs.
// Aucune bibliothèque : le terminal est piloté par les séquences ANSI (Windows 10 et plus, macOS, Linux).

use std::io::Write;

use super::{boucle, charger, compiler_avec, compiler_lignes, dossier_de, executer_dans, lire_partition, nombres, Etat, Fichiers,
            Memoire, COMPLET, PAS_A_PAS, PILE_HAUT, VTXC};
use std::collections::{HashMap, HashSet};
use std::path::{Path, PathBuf};

// ------------------------------------------------------------------------------------------------ terminal
#[cfg(windows)]
pub(crate) mod console {
    type Handle = *mut core::ffi::c_void;
    #[repr(C)]
    struct Coord {
        x: i16,
        y: i16,
    }
    #[repr(C)]
    struct Rect {
        g: i16,
        h: i16,
        d: i16,
        b: i16,
    }
    #[repr(C)]
    struct Info {
        taille: Coord,
        curseur: Coord,
        attributs: u16,
        fenetre: Rect,
        max: Coord,
    }
    #[link(name = "kernel32")]
    extern "system" {
        fn GetStdHandle(n: u32) -> Handle;
        fn GetConsoleMode(h: Handle, m: *mut u32) -> i32;
        fn SetConsoleMode(h: Handle, m: u32) -> i32;
        fn GetConsoleScreenBufferInfo(h: Handle, i: *mut Info) -> i32;
        fn SetConsoleOutputCP(cp: u32) -> i32;
        fn SetConsoleCP(cp: u32) -> i32;
        fn ReadConsoleW(h: Handle, tampon: *mut u16, n: u32, lus: *mut u32, controle: *mut core::ffi::c_void) -> i32;
        fn GlobalAlloc(drapeaux: u32, n: usize) -> Handle;
        fn GlobalLock(h: Handle) -> *mut core::ffi::c_void;
        fn GlobalUnlock(h: Handle) -> i32;
    }
    #[link(name = "user32")]
    extern "system" {
        fn OpenClipboard(h: Handle) -> i32;
        fn CloseClipboard() -> i32;
        fn EmptyClipboard() -> i32;
        fn GetClipboardData(format: u32) -> Handle;
        fn SetClipboardData(format: u32, h: Handle) -> Handle;
    }
    const TEXTE_UNICODE: u32 = 13;

    /// Le presse-papiers de Windows : le texte copié ici se colle ailleurs, et inversement.
    pub fn ecrire_presse(t: &str) {
        let mut u: Vec<u16> = t.replace('\n', "\r\n").encode_utf16().collect();
        u.push(0);
        unsafe {
            if OpenClipboard(std::ptr::null_mut()) == 0 {
                return;
            }
            EmptyClipboard();
            let h = GlobalAlloc(2, u.len() * 2);
            if !h.is_null() {
                let p = GlobalLock(h) as *mut u16;
                if !p.is_null() {
                    std::ptr::copy_nonoverlapping(u.as_ptr(), p, u.len());
                    GlobalUnlock(h);
                    SetClipboardData(TEXTE_UNICODE, h);
                }
            }
            CloseClipboard();
        }
    }
    pub fn lire_presse() -> Option<String> {
        unsafe {
            if OpenClipboard(std::ptr::null_mut()) == 0 {
                return None;
            }
            let h = GetClipboardData(TEXTE_UNICODE);
            let mut r = None;
            if !h.is_null() {
                let p = GlobalLock(h) as *const u16;
                if !p.is_null() {
                    let mut n = 0;
                    while *p.add(n) != 0 && n < 50_000_000 {
                        n += 1;
                    }
                    r = Some(String::from_utf16_lossy(std::slice::from_raw_parts(p, n)).replace("\r\n", "\n"));
                    GlobalUnlock(h);
                }
            }
            CloseClipboard();
            r
        }
    }
    const ENTREE: u32 = 0xFFFF_FFF6;
    const SORTIE: u32 = 0xFFFF_FFF5;
    static mut ANCIENS: (u32, u32) = (0, 0);

    pub fn brut() {
        unsafe {
            SetConsoleOutputCP(65001);
            SetConsoleCP(65001);
            let (e, s) = (GetStdHandle(ENTREE), GetStdHandle(SORTIE));
            let (mut me, mut ms) = (0u32, 0u32);
            GetConsoleMode(e, &mut me);
            GetConsoleMode(s, &mut ms);
            ANCIENS = (me, ms);
            // entrée : sans écho ni ligne, touches en séquences VT ; sortie : séquences VT
            SetConsoleMode(e, (me & !(0x1 | 0x2 | 0x4 | 0x40)) | 0x200 | 0x80);
            SetConsoleMode(s, ms | 0x4 | 0x1);
        }
    }
    pub fn retablir() {
        unsafe {
            SetConsoleMode(GetStdHandle(ENTREE), ANCIENS.0);
            SetConsoleMode(GetStdHandle(SORTIE), ANCIENS.1);
        }
    }
    /// Les touches tapées, en UTF-8 (séquences VT comprises).
    pub fn lire() -> Option<Vec<u8>> {
        let mut t = [0u16; 512];
        let mut n = 0u32;
        let ok = unsafe { ReadConsoleW(GetStdHandle(ENTREE), t.as_mut_ptr(), 512, &mut n, std::ptr::null_mut()) };
        if ok == 0 {
            return None;
        }
        Some(String::from_utf16_lossy(&t[..n as usize]).into_bytes())
    }
    pub fn taille() -> (usize, usize) {
        unsafe {
            let mut i: Info = std::mem::zeroed();
            if GetConsoleScreenBufferInfo(GetStdHandle(SORTIE), &mut i) != 0 {
                let l = (i.fenetre.d - i.fenetre.g + 1) as usize;
                let h = (i.fenetre.b - i.fenetre.h + 1) as usize;
                return (l.max(40), h.max(12));
            }
            (100, 30)
        }
    }
}

#[cfg(not(windows))]
pub(crate) mod console {
    use std::process::{Command, Stdio};
    static mut ANCIEN: Option<String> = None;

    fn stty(args: &[&str]) -> Option<String> {
        let o = Command::new("stty").args(args).stdin(Stdio::inherit()).output().ok()?;
        Some(String::from_utf8_lossy(&o.stdout).trim().to_string())
    }
    pub fn brut() {
        unsafe {
            ANCIEN = stty(&["-g"]);
        }
        stty(&["raw", "-echo"]);
    }
    pub fn retablir() {
        #[allow(static_mut_refs)]
        let a = unsafe { ANCIEN.clone() };
        match a {
            Some(a) if !a.is_empty() => {
                stty(&[a.as_str()]);
            }
            _ => {
                stty(&["sane"]);
            }
        }
    }
    pub fn lire() -> Option<Vec<u8>> {
        use std::io::Read;
        let mut t = [0u8; 4096];
        match std::io::stdin().read(&mut t) {
            Ok(0) | Err(_) => None,
            Ok(n) => Some(t[..n].to_vec()),
        }
    }
    /// Copie : la séquence OSC 52, que comprennent la plupart des terminaux ; le collage arrive par le terminal.
    pub fn ecrire_presse(t: &str) {
        use std::io::Write;
        const B64: &[u8] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
        let o = t.as_bytes();
        let mut e = String::new();
        for c in o.chunks(3) {
            let n = (c[0] as u32) << 16 | (*c.get(1).unwrap_or(&0) as u32) << 8 | *c.get(2).unwrap_or(&0) as u32;
            for k in 0..4 {
                if k <= c.len() {
                    e.push(B64[((n >> (18 - 6 * k)) & 63) as usize] as char);
                } else {
                    e.push('=');
                }
            }
        }
        let mut s = std::io::stdout();
        let _ = write!(s, "\x1b]52;c;{}\x07", e);
        let _ = s.flush();
    }
    pub fn lire_presse() -> Option<String> {
        None
    }
    pub fn taille() -> (usize, usize) {
        if let Some(t) = stty(&["size"]) {
            let v: Vec<usize> = t.split_whitespace().filter_map(|x| x.parse().ok()).collect();
            if v.len() == 2 && v[0] > 0 && v[1] > 0 {
                return (v[1].max(40), v[0].max(12));
            }
        }
        (100, 30)
    }
}

// ------------------------------------------------------------------------------------------------ touches
#[derive(Debug, Clone, PartialEq)]
enum Touche {
    Car(char),
    Entree,
    Retour,
    Suppr,
    Tab,
    Haut,
    Bas,
    Gauche,
    Droite,
    Debut,
    Fin,
    PageHaut,
    PageBas,
    F(u8),
    Ctrl(char),
    Echap,
    Maj(Box<Touche>),
    Alt(char),
    Souris { b: u32, x: usize, y: usize, appui: bool },
    Colle(String),
}

fn lire_touches(tampon: &[u8]) -> Vec<Touche> {
    let mut t = Vec::new();
    let s = String::from_utf8_lossy(tampon);
    let c: Vec<char> = s.chars().collect();
    let mut i = 0;
    while i < c.len() {
        let x = c[i];
        if x == '\u{1b}' {
            let reste: String = c[i + 1..].iter().take(40).collect();
            // texte collé (mode « bracketed paste ») : tel quel, sans retrait automatique
            if reste.starts_with("[200~") {
                let tout: String = c[i + 6..].iter().collect();
                let (colle, saut) = match tout.find("\u{1b}[201~") {
                    Some(p) => (tout[..p].to_string(), tout[..p].chars().count() + 6),
                    None => (tout.clone(), tout.chars().count()),
                };
                t.push(Touche::Colle(colle));
                i += 6 + saut;
                continue;
            }
            // souris (SGR) : ESC [ < b ; x ; y M (appui) ou m (relâché)
            if reste.starts_with("[<") {
                if let Some(fin) = reste.find(|ch| ch == 'M' || ch == 'm') {
                    let v: Vec<usize> = reste[2..fin].split(';').filter_map(|n| n.parse().ok()).collect();
                    if v.len() == 3 {
                        t.push(Touche::Souris { b: v[0] as u32, x: v[1], y: v[2], appui: reste[fin..].starts_with('M') });
                    }
                    i += 1 + reste[..fin + 1].chars().count();
                    continue;
                }
            }
            // Maj + flèche, Début, Fin : ESC [ 1 ; 2 A ; (Ctrl : ; 5, pris comme la flèche seule)
            if reste.starts_with("[1;") && reste.chars().count() >= 5 {
                let m: Vec<char> = reste.chars().collect();
                let base = match m[4] {
                    'A' => Some(Touche::Haut), 'B' => Some(Touche::Bas), 'C' => Some(Touche::Droite), 'D' => Some(Touche::Gauche),
                    'H' => Some(Touche::Debut), 'F' => Some(Touche::Fin), _ => None,
                };
                if let Some(b) = base {
                    t.push(if m[3] == '2' { Touche::Maj(Box::new(b)) } else { b });
                    i += 6;
                    continue;
                }
            }
            let seq = [
                ("[A", Touche::Haut), ("[B", Touche::Bas), ("[C", Touche::Droite), ("[D", Touche::Gauche),
                ("OA", Touche::Haut), ("OB", Touche::Bas), ("OC", Touche::Droite), ("OD", Touche::Gauche),
                ("[H", Touche::Debut), ("[F", Touche::Fin), ("OH", Touche::Debut), ("OF", Touche::Fin),
                ("[1~", Touche::Debut), ("[4~", Touche::Fin), ("[7~", Touche::Debut), ("[8~", Touche::Fin),
                ("[3~", Touche::Suppr), ("[5~", Touche::PageHaut), ("[6~", Touche::PageBas),
                ("OP", Touche::F(1)), ("OQ", Touche::F(2)), ("OR", Touche::F(3)), ("OS", Touche::F(4)),
                ("[11~", Touche::F(1)), ("[12~", Touche::F(2)), ("[13~", Touche::F(3)), ("[14~", Touche::F(4)),
                ("[15~", Touche::F(5)), ("[17~", Touche::F(6)), ("[18~", Touche::F(7)), ("[19~", Touche::F(8)),
                ("[20~", Touche::F(9)), ("[21~", Touche::F(10)),
            ];
            let mut trouve = false;
            for (p, k) in seq.iter() {
                if reste.starts_with(p) {
                    t.push(k.clone());
                    i += 1 + p.chars().count();
                    trouve = true;
                    break;
                }
            }
            if !trouve {
                // séquence inconnue (ou Échap seul) : on saute jusqu'à la lettre finale
                if reste.starts_with('[') || reste.starts_with('O') {
                    let mut j = i + 2;
                    while j < c.len() && !(c[j].is_ascii_alphabetic() || c[j] == '~') {
                        j += 1;
                    }
                    i = j + 1;
                } else if let Some(&l) = c.get(i + 1).filter(|l| l.is_alphanumeric()) {
                    t.push(Touche::Alt(l.to_ascii_lowercase()));
                    i += 2;
                } else {
                    t.push(Touche::Echap);
                    i += 1;
                }
            }
            continue;
        }
        t.push(match x {
            '\r' | '\n' => Touche::Entree,
            '\u{7f}' | '\u{8}' => Touche::Retour,
            '\t' => Touche::Tab,
            c @ '\u{1}'..='\u{1a}' => Touche::Ctrl((b'a' + (c as u8) - 1) as char),
            c => Touche::Car(c),
        });
        i += 1;
    }
    t
}

// ------------------------------------------------------------------------------------------------ couleurs du langage
const MOTS: &[&str] = &["fonction", "soit", "si", "sinon", "tantque", "pour", "dans", "par", "en", "segments", "cumulant", "retour",
    "constante", "structure", "tableau", "de", "donnees", "données", "arrêter", "arreter", "continuer", "hypothèse", "hypothese",
    "annuler", "valider", "selon", "autre", "importer", "et", "ou", "non"];
const TYPES: &[&str] = &["entier", "flottant", "long", "logique", "quits", "texte"];
const LOGIQUES: &[&str] = &["vrai", "faux", "inconnu", "variable", "nul"];

/// Couleur de chaque caractère d'une ligne (code ANSI de premier plan).
fn colorer(ligne: &[char]) -> Vec<&'static str> {
    let n = ligne.len();
    let mut col = vec!["\x1b[38;5;252m"; n];
    let mut i = 0;
    while i < n {
        let x = ligne[i];
        if x == '/' && i + 1 < n && ligne[i + 1] == '/' {
            for k in i..n {
                col[k] = "\x1b[38;5;244m";
            }
            break;
        }
        if x == '"' || x == '\'' {
            let mut j = i + 1;
            while j < n && ligne[j] != x {
                if ligne[j] == '\\' {
                    j += 1;
                }
                j += 1;
            }
            for k in i..(j + 1).min(n) {
                col[k] = "\x1b[38;5;180m";
            }
            i = j + 1;
            continue;
        }
        if x == '#' || x.is_ascii_digit() {
            let mut j = i + 1;
            while j < n && (ligne[j].is_ascii_alphanumeric() || ligne[j] == '_' || ligne[j] == '.') {
                j += 1;
            }
            for k in i..j {
                col[k] = "\x1b[38;5;151m";
            }
            i = j;
            continue;
        }
        if x.is_alphabetic() || x == '_' {
            let mut j = i;
            while j < n && (ligne[j].is_alphanumeric() || ligne[j] == '_') {
                j += 1;
            }
            let mot: String = ligne[i..j].iter().collect();
            let c = if MOTS.contains(&mot.as_str()) {
                "\x1b[38;5;75m"
            } else if TYPES.contains(&mot.as_str()) {
                "\x1b[38;5;79m"
            } else if LOGIQUES.contains(&mot.as_str()) {
                "\x1b[38;5;213m"
            } else if j < n && ligne[j] == '(' {
                "\x1b[38;5;222m"
            } else {
                "\x1b[38;5;252m"
            };
            for k in i..j {
                col[k] = c;
            }
            i = j;
            continue;
        }
        if x == '@' {
            col[i] = "\x1b[38;5;209m";
        }
        i += 1;
    }
    col
}

// ------------------------------------------------------------------------------------------------ l'atelier
#[derive(PartialEq, Clone, Copy)]
enum Focus {
    Editeur,
    Cube,
}

struct Atelier {
    fichier: String,
    lignes: Vec<Vec<char>>,
    cl: usize,
    cc: usize,
    haut: usize,
    gauche: usize,
    modifie: bool,
    annuler: Vec<(Vec<Vec<char>>, usize, usize)>,
    frappe: bool,
    focus: Focus,
    entrees: String,
    saisie: Option<String>,
    // le cube
    mem: Option<Memoire>,
    etage: u32,
    largeur: u32,
    base: u32,
    zoom: u32,
    sel: u32,
    mode_valeur: bool,
    // résultats
    message: String,
    rapport: Vec<String>,
    ligne_erreur: Option<usize>,
    quitter: bool,
    confirmer_sortie: bool,
    deb: Option<Debogage>,
    points: HashSet<usize>,
    ouvrir: Option<Ouvrir>,
    but_saisie: Saisie,
    ancre: Option<(usize, usize)>,
    retablir: Vec<(Vec<Vec<char>>, usize, usize)>,
    presse: String,
    menu: Option<(usize, usize)>,
    recherche: String,
    glisser: bool,
}

/// Le pas à pas : la machine arrêtée entre deux instructions, et la table adresse -> ligne donnée par vtxc.
struct Debogage {
    mem: Memoire,
    et: Etat,
    fichiers: Fichiers,
    entrees: Vec<u32>,
    dossier: PathBuf,
    debuts: HashMap<u32, usize>,
    ligne: Option<usize>,
    fini: bool,
}

#[derive(Clone, Copy, PartialEq)]
enum Avance {
    Pas,
    Dessus,
    Continuer,
}

/// La fenêtre « ouvrir » : les dossiers et les fichiers .vtx d'un dossier.
struct Ouvrir {
    dossier: PathBuf,
    entrees: Vec<(String, bool)>,
    sel: usize,
}

#[derive(PartialEq, Clone, Copy)]
enum Saisie {
    Entrees,
    NouveauFichier,
    EnregistrerSous,
    Rechercher,
}

const LIMITE_PAS: u64 = 200_000_000;

#[derive(Clone, Copy, PartialEq, Debug)]
enum Action {
    Nouveau, Ouvrir, Enregistrer, EnregistrerSous, Quitter,
    Annuler, Retablir, Couper, Copier, Coller, ToutSelectionner, Rechercher, Suivant, SupprimerLigne, Dupliquer,
    Lancer, Entrees, Pas, Dessus, Continuer, Point, Arreter,
    Cube, Etage(u32), Valeurs, Ajuster,
    Touches, Apropos,
}

type Entree = (&'static str, &'static str, Action);
const MENUS: &[(&str, &[Entree])] = &[
    ("Fichier", &[("Nouveau…", "Ctrl+N", Action::Nouveau), ("Ouvrir…", "Ctrl+O", Action::Ouvrir),
                  ("Enregistrer", "Ctrl+S", Action::Enregistrer), ("Enregistrer sous…", "", Action::EnregistrerSous),
                  ("Quitter", "Ctrl+Q", Action::Quitter)]),
    ("Édition", &[("Annuler", "Ctrl+Z", Action::Annuler), ("Rétablir", "Ctrl+Y", Action::Retablir),
                  ("Couper", "Ctrl+X", Action::Couper), ("Copier", "Ctrl+C", Action::Copier), ("Coller", "Ctrl+V", Action::Coller),
                  ("Tout sélectionner", "Ctrl+A", Action::ToutSelectionner), ("Rechercher…", "Ctrl+F", Action::Rechercher),
                  ("Rechercher le suivant", "F3", Action::Suivant), ("Supprimer la ligne", "Ctrl+K", Action::SupprimerLigne),
                  ("Dupliquer la ligne", "Ctrl+D", Action::Dupliquer)]),
    ("Exécuter", &[("Lancer", "F5", Action::Lancer), ("Entrées du programme…", "F4", Action::Entrees),
                   ("Pas à pas", "F7", Action::Pas), ("Pas par-dessus", "F8", Action::Dessus),
                   ("Continuer jusqu'au point d'arrêt", "F5", Action::Continuer), ("Point d'arrêt", "F9", Action::Point),
                   ("Arrêter le pas à pas", "Échap", Action::Arreter)]),
    ("Cube", &[("Éditeur / cube", "F6", Action::Cube), ("Étage 0 (code)", "0", Action::Etage(0)), ("Étage 1", "1", Action::Etage(1)),
               ("Étage 2", "2", Action::Etage(2)), ("Étage 3", "3", Action::Etage(3)), ("Couleurs / valeurs", "m", Action::Valeurs),
               ("Ajuster le zoom", "a", Action::Ajuster)]),
    ("Aide", &[("Touches", "F1", Action::Touches), ("À propos", "", Action::Apropos)]),
];

/// Les titres de la barre des menus : (colonne de départ, largeur), colonnes comptées à partir de 0.
fn titres_menus() -> Vec<(usize, usize)> {
    let mut x = 1;
    MENUS.iter().map(|(t, _)| {
        let l = t.chars().count() + 2;
        let r = (x, l);
        x += l + 1;
        r
    }).collect()
}

const LARGEURS: [u32; 8] = [16, 32, 64, 128, 256, 512, 1024, 4096];

impl Atelier {
    fn texte(&self) -> String {
        self.lignes.iter().map(|l| l.iter().collect::<String>()).collect::<Vec<_>>().join("\n")
    }

    fn memoriser(&mut self) {
        if self.annuler.len() > 300 {
            self.annuler.remove(0);
        }
        self.annuler.push((self.lignes.clone(), self.cl, self.cc));
        self.retablir.clear();
    }

    fn enregistrer(&mut self) {
        let mut t = self.texte();
        if !t.ends_with('\n') {
            t.push('\n');
        }
        match std::fs::write(&self.fichier, t) {
            Ok(_) => {
                self.modifie = false;
                self.message = format!("enregistré : {}", self.fichier);
            }
            Err(e) => self.message = format!("impossible d'enregistrer : {}", e),
        }
    }

    /// Ouvre un fichier dans l'éditeur (un fichier qui n'existe pas encore est créé à l'enregistrement).
    fn charger_fichier(&mut self, chemin: &Path) {
        let texte = std::fs::read_to_string(chemin).unwrap_or_else(|_| "fonction principal() {\n    \n}\n".to_string());
        self.lignes = decouper(&texte);
        self.fichier = chemin.to_string_lossy().into_owned();
        self.cl = 0;
        self.cc = 0;
        self.haut = 0;
        self.gauche = 0;
        self.modifie = false;
        self.annuler.clear();
        self.deb = None;
        self.mem = None;
        self.points.clear();
        self.ligne_erreur = None;
        self.rapport = vec![format!("ouvert : {}", self.fichier)];
        self.message = "F5 lancer · F7 pas à pas".into();
    }

    fn ouvrir_dossier(&mut self, dossier: PathBuf) {
        let mut entrees: Vec<(String, bool)> = Vec::new();
        if dossier.parent().is_some() {
            entrees.push(("..".into(), true));
        }
        let mut dossiers = Vec::new();
        let mut fichiers = Vec::new();
        if let Ok(lu) = std::fs::read_dir(&dossier) {
            for e in lu.flatten() {
                let nom = e.file_name().to_string_lossy().into_owned();
                if nom.starts_with('.') || nom == "target" {
                    continue;
                }
                let p = e.path();
                if p.is_dir() {
                    dossiers.push(nom);
                } else if nom.ends_with(".vtx") {
                    fichiers.push(nom);
                }
            }
        }
        dossiers.sort();
        fichiers.sort();
        entrees.extend(dossiers.into_iter().map(|n| (n, true)));
        entrees.extend(fichiers.into_iter().map(|n| (n, false)));
        self.ouvrir = Some(Ouvrir { dossier, entrees, sel: 0 });
        self.message = "Ouvrir : flèches, Entrée ; Ctrl+N nouveau fichier ici ; Échap pour revenir".into();
    }

    fn touche_ouvrir(&mut self, k: Touche, hauteur: usize) {
        let o = match self.ouvrir.as_mut() {
            Some(o) => o,
            None => return,
        };
        let n = o.entrees.len();
        match k {
            Touche::Haut => o.sel = o.sel.saturating_sub(1),
            Touche::Bas => o.sel = (o.sel + 1).min(n.saturating_sub(1)),
            Touche::PageHaut => o.sel = o.sel.saturating_sub(hauteur),
            Touche::PageBas => o.sel = (o.sel + hauteur).min(n.saturating_sub(1)),
            Touche::Echap => {
                self.ouvrir = None;
                self.message.clear();
            }
            Touche::Ctrl('n') => {
                self.but_saisie = Saisie::NouveauFichier;
                self.saisie = Some("nouveau.vtx".into());
            }
            Touche::Entree if n > 0 => {
                let (nom, dossier) = o.entrees[o.sel].clone();
                let chemin = if nom == ".." { o.dossier.parent().map(|p| p.to_path_buf()).unwrap_or(o.dossier.clone()) } else { o.dossier.join(&nom) };
                if dossier {
                    self.ouvrir_dossier(chemin);
                } else {
                    self.ouvrir = None;
                    self.charger_fichier(&chemin);
                }
            }
            _ => {}
        }
    }

    // ------------------------------------------------------------------ pas à pas
    fn debuter(&mut self) -> bool {
        self.enregistrer();
        self.ligne_erreur = None;
        let base = dossier_de(&self.fichier);
        let (mots, _, dbg) = match compiler_lignes(&nombres(VTXC), &self.texte(), &base, PAS_A_PAS, true) {
            Ok(r) => r,
            Err(e) => {
                self.erreur_compilation(&e);
                return false;
            }
        };
        let mut mem = Memoire::new(false);
        charger(&mut mem, &mots);
        let mut debuts = HashMap::new();
        for p in dbg.chunks(2) {
            if p.len() == 2 && p[1] >= 1 {
                debuts.entry(p[0]).or_insert(p[1] as usize - 1);
            }
        }
        let mut et = Etat { r: [0u32; 16], pc: 0, z: false, c: false, pas: 0, ie: 0, sorties: Vec::new(), texte: Vec::new() };
        et.r[14] = PILE_HAUT;
        let entrees = self.entrees.split_whitespace().filter_map(|x| x.parse::<u64>().ok()).map(|x| x as u32).collect();
        self.deb = Some(Debogage { mem, et, fichiers: std::sync::Mutex::new(HashMap::new()), entrees, dossier: PathBuf::from(&base),
                                   debuts, ligne: None, fini: false });
        self.rapport.clear();
        true
    }

    /// Une instruction de la machine ; Ok(true) quand le programme est fini.
    fn une_instruction(d: &mut Debogage) -> Result<bool, String> {
        let limite = d.et.pas + 1;
        match boucle(&d.mem, &mut d.et, &d.entrees, limite, Some(&d.dossier), &d.fichiers, u32::MAX, None, 0) {
            Ok(()) => Ok(true),
            Err(e) if e.starts_with("limite") => Ok(false),
            Err(e) => Err(e),
        }
    }

    fn avancer(&mut self, mode: Avance) {
        if self.deb.is_none() && !self.debuter() {
            return;
        }
        let points = self.points.clone();
        let d = self.deb.as_mut().unwrap();
        if d.fini {
            self.message = "le programme est fini : Échap pour revenir à l'édition".into();
            return;
        }
        let cadre = d.et.r[13];
        let depart = d.et.pas;
        let mut erreur = None;
        if mode == Avance::Continuer && points.is_empty() {
            // rien pour l'arrêter : on va jusqu'au bout d'un coup
            match boucle(&d.mem, &mut d.et, &d.entrees, 5_000_000_000, Some(&d.dossier), &d.fichiers, u32::MAX, None, 0) {
                Ok(()) => d.fini = true,
                Err(e) => erreur = Some(e),
            }
        } else {
            loop {
                match Self::une_instruction(d) {
                    Ok(true) => {
                        d.fini = true;
                        break;
                    }
                    Ok(false) => {}
                    Err(e) => {
                        erreur = Some(e);
                        break;
                    }
                }
                if let Some(&l) = d.debuts.get(&d.et.pc) {
                    d.ligne = Some(l);
                    let arreter = match mode {
                        Avance::Pas => true,
                        Avance::Dessus => d.et.r[13] >= cadre,
                        Avance::Continuer => points.contains(&l),
                    };
                    if arreter {
                        break;
                    }
                }
                if d.et.pas - depart >= LIMITE_PAS {
                    erreur = Some(format!("{} instructions sans atteindre une ligne : arrêt (boucle sans fin ?)", LIMITE_PAS));
                    break;
                }
            }
        }
        if let Some(l) = d.ligne {
            self.cl = l.min(self.lignes.len() - 1);
            self.cc = 0;
        }
        if let Some(e) = erreur {
            self.message = format!("erreur à l'exécution : {}", e);
            d.fini = true;
        } else if d.fini {
            d.ligne = None;
            self.message = format!("programme fini en {} instructions : Échap pour revenir à l'édition", d.et.pas);
        } else {
            self.message = format!("ligne {} · F7 pas · F8 pas par-dessus · F5 continuer · F9 point d'arrêt · Échap arrêter", d.ligne.map(|l| l + 1).unwrap_or(0));
        }
    }

    fn erreur_compilation(&mut self, e: &str) {
        let nom = Path::new(&self.fichier).file_name().map(|n| n.to_string_lossy().into_owned()).unwrap_or_default();
        self.rapport.clear();
        for l in e.lines().filter(|l| !l.trim().is_empty()) {
            self.rapport.push(l.replace("erreur ligne ", &format!("erreur {}, ligne ", nom)));
        }
        if let Some(p) = e.find("erreur ligne ") {
            let n: String = e[p + 13..].chars().take_while(|c| c.is_ascii_digit()).collect();
            if let Ok(n) = n.parse::<usize>() {
                if n >= 1 && n <= self.lignes.len() {
                    self.ligne_erreur = Some(n - 1);
                    self.cl = n - 1;
                    self.cc = 0;
                    self.focus = Focus::Editeur;
                }
            }
        }
        self.message = "erreur de compilation".into();
    }

    /// Le panneau du pas à pas : registres, cadre de la fonction, sorties et console.
    fn panneau(&self) -> Vec<String> {
        let d = match &self.deb {
            Some(d) => d,
            None => return Vec::new(),
        };
        let r = &d.et.r;
        let s = |v: u32| (v as i32).to_string();
        let mut l = Vec::new();
        l.push(format!("pas à pas · {} · {} instructions", match d.ligne { Some(x) => format!("ligne {}", x + 1), None => if d.fini { "fini".into() } else { "début".into() } }, d.et.pas));
        l.push(format!("R1 {}  R2 {}  R3 {}  R4 {}", s(r[1]), s(r[2]), s(r[3]), s(r[4])));
        l.push(format!("R5 {}  R6 {}  R7 {}  R8 {}", s(r[5]), s(r[6]), s(r[7]), s(r[8])));
        l.push(format!("R13 cadre {}  R14 pile {}  Z {}  C {}  pc {}", r[13], r[14], d.et.z as u8, d.et.c as u8, d.et.pc));
        if r[13] != 0 && r[13] < PILE_HAUT {
            let lit = |k: i64| s(d.mem.lit(0, (r[13] as i64 + k) as u32));
            l.push(format!("variables locales  -1: {}  -2: {}  -3: {}  -4: {}", lit(-1), lit(-2), lit(-3), lit(-4)));
            l.push(format!("paramètres         +2: {}  +3: {}  +4: {}", lit(2), lit(3), lit(4)));
        }
        if !d.et.sorties.is_empty() {
            let v: Vec<String> = d.et.sorties.iter().map(|v| v.to_string()).collect();
            l.push(format!("sorties : {}", v.join(",")));
        }
        let t: String = d.et.texte.iter().filter_map(|&v| char::from_u32(v & 0x1F_FFFF)).collect();
        for x in t.lines() {
            l.push(format!("» {}", x));
        }
        l
    }

    fn lancer(&mut self) {
        self.enregistrer();
        self.ligne_erreur = None;
        self.deb = None;
        self.rapport.clear();
        let base = dossier_de(&self.fichier);
        let t0 = std::time::Instant::now();
        let (mots, table) = match compiler_avec(&nombres(VTXC), &self.texte(), &base, COMPLET) {
            Ok(r) => r,
            Err(e) => {
                self.erreur_compilation(&e);
                return;
            }
        };
        let tc = t0.elapsed().as_secs_f64();
        let mut mem = Memoire::new(false);
        super::charger(&mut mem, &mots);
        let entrees: Vec<u32> = self.entrees.split_whitespace().filter_map(|x| x.parse::<u64>().ok()).map(|x| x as u32).collect();
        let cyl = super::cylindres_voulus(None);
        let part = if table.first().copied().unwrap_or(0) == 0 || cyl <= 1 { None } else { Some(lire_partition(&table, cyl)) };
        let dossier = std::path::PathBuf::from(&base);
        let t1 = std::time::Instant::now();
        let r = executer_dans(&mem, &entrees, 5_000_000_000, Some(&dossier), part.as_ref());
        let te = t1.elapsed().as_secs_f64();
        match r {
            Ok(r) => {
                let duree = |t: f64| if t < 1.0 { format!("{:.0} ms", t * 1000.0) } else { format!("{:.2} s", t) };
                self.rapport.push(format!("{} mots, compilé en {} ; {} instructions en {}", mots.len(), duree(tc), r.pas, duree(te)));
                if !r.sorties.is_empty() {
                    let s: Vec<String> = r.sorties.iter().map(|v| v.to_string()).collect();
                    self.rapport.push(format!("sorties : {}", s.join(",")));
                }
                let t: String = r.texte.iter().filter_map(|&v| char::from_u32(v & 0x1F_FFFF)).collect();
                for l in t.lines() {
                    self.rapport.push(format!("» {}", l));
                }
                self.message = "programme terminé".into();
            }
            Err(e) => {
                self.rapport.push(format!("erreur à l'exécution : {}", e));
                self.message = "erreur à l'exécution".into();
            }
        }
        // si l'étage regardé est vide au début, on montre le premier étage (1 à 3) qui contient quelque chose
        let vide = |e: u32| (0..65536u32).all(|a| mem.lit(e, a) == 0);
        if vide(self.etage) {
            if let Some(e) = (1..4u32).find(|&e| !vide(e)) {
                self.etage = e;
                self.base = 0;
            }
        }
        self.mem = Some(mem);
    }

    // ------------------------------------------------------------------ édition
    fn ligne(&self) -> &Vec<char> {
        &self.lignes[self.cl]
    }

    // ------------------------------------------------------------------ sélection, presse-papiers
    fn curseur(&self) -> (usize, usize) {
        (self.cl, self.cc.min(self.lignes[self.cl].len()))
    }

    fn bornes(&self) -> Option<((usize, usize), (usize, usize))> {
        let a = self.ancre?;
        let a = (a.0.min(self.lignes.len() - 1), a.1);
        let a = (a.0, a.1.min(self.lignes[a.0].len()));
        let b = self.curseur();
        if a == b {
            return None;
        }
        Some(if a < b { (a, b) } else { (b, a) })
    }

    fn texte_choisi(&self) -> Option<String> {
        let ((l1, c1), (l2, c2)) = self.bornes()?;
        if l1 == l2 {
            return Some(self.lignes[l1][c1..c2].iter().collect());
        }
        let mut t: String = self.lignes[l1][c1..].iter().collect();
        for l in l1 + 1..l2 {
            t.push('\n');
            t.extend(self.lignes[l].iter());
        }
        t.push('\n');
        t.extend(self.lignes[l2][..c2].iter());
        Some(t)
    }

    /// Efface la sélection (sans mémoriser : l'appelant l'a fait).
    fn effacer_choix(&mut self) -> bool {
        let ((l1, c1), (l2, c2)) = match self.bornes() {
            Some(b) => b,
            None => {
                self.ancre = None;
                return false;
            }
        };
        let fin: Vec<char> = self.lignes[l2][c2..].to_vec();
        self.lignes[l1].truncate(c1);
        self.lignes[l1].extend(fin);
        self.lignes.drain(l1 + 1..=l2);
        self.cl = l1;
        self.cc = c1;
        self.ancre = None;
        self.modifie = true;
        true
    }

    /// Insère un texte tel quel (collage) : plusieurs lignes, sans retrait automatique.
    fn inserer(&mut self, t: &str) {
        let t = t.replace("\r\n", "\n").replace('\r', "\n").replace('\t', "    ");
        let (l, c) = self.curseur();
        let fin: Vec<char> = self.lignes[l][c..].to_vec();
        self.lignes[l].truncate(c);
        let mut morceaux = t.split('\n');
        self.lignes[l].extend(morceaux.next().unwrap_or("").chars());
        let mut cl = l;
        for m in morceaux {
            cl += 1;
            self.lignes.insert(cl, m.chars().collect());
        }
        self.cc = self.lignes[cl].len();
        self.lignes[cl].extend(fin);
        self.cl = cl;
        self.modifie = true;
    }

    fn chercher(&mut self) {
        if self.recherche.is_empty() {
            return;
        }
        let motif: Vec<char> = self.recherche.chars().collect();
        let n = self.lignes.len();
        let (l0, c0) = self.curseur();
        for k in 0..=n {
            let l = (l0 + k) % n;
            let depart = if k == 0 { c0 + if self.bornes().is_some() { 0 } else { 1 } } else { 0 };
            let ligne = &self.lignes[l];
            if ligne.len() >= motif.len() {
                for c in depart.min(ligne.len())..=ligne.len() - motif.len() {
                    if ligne[c..c + motif.len()] == motif[..] && !(k == 0 && c == c0 && self.bornes().is_some() && n > 0 && false) {
                        if k == 0 && c < c0 + 1 && self.bornes().is_some() {
                            continue;
                        }
                        self.ancre = Some((l, c));
                        self.cl = l;
                        self.cc = c + motif.len();
                        self.message = format!("« {} » : ligne {}", self.recherche, l + 1);
                        return;
                    }
                }
            }
        }
        self.message = format!("« {} » introuvable", self.recherche);
    }

    /// Les actions des menus et des raccourcis.
    fn agir(&mut self, act: Action, hauteur: usize, lc: u32, hc: u32) {
        let edition = matches!(act, Action::Annuler | Action::Retablir | Action::Couper | Action::Coller | Action::SupprimerLigne
            | Action::Dupliquer);
        if edition && self.deb.is_some() {
            self.message = "pas à pas en cours : Échap pour l'arrêter, puis modifiez".into();
            return;
        }
        if act != Action::Quitter && act != Action::Ouvrir {
            self.confirmer_sortie = false;
        }
        match act {
            Action::Nouveau => {
                self.but_saisie = Saisie::NouveauFichier;
                self.saisie = Some("nouveau.vtx".into());
            }
            Action::Ouvrir => {
                if self.modifie && !self.confirmer_sortie {
                    self.confirmer_sortie = true;
                    self.message = "modifications non enregistrées : Ctrl+S pour enregistrer, Ctrl+O encore pour ouvrir sans".into();
                } else {
                    self.confirmer_sortie = false;
                    let d = Path::new(&self.fichier).parent().map(|p| p.to_path_buf()).filter(|p| p.is_dir()).unwrap_or_else(dossier_de_depart);
                    let d = std::fs::canonicalize(&d).unwrap_or(d);
                    self.ouvrir_dossier(d);
                }
            }
            Action::Enregistrer => self.enregistrer(),
            Action::EnregistrerSous => {
                self.but_saisie = Saisie::EnregistrerSous;
                self.saisie = Some(Path::new(&self.fichier).file_name().map(|n| n.to_string_lossy().into_owned()).unwrap_or_default());
            }
            Action::Quitter => {
                if self.modifie && !self.confirmer_sortie {
                    self.confirmer_sortie = true;
                    self.message = "modifications non enregistrées : Ctrl+S pour enregistrer, Ctrl+Q encore pour quitter sans".into();
                } else {
                    self.quitter = true;
                }
            }
            Action::Annuler => {
                if let Some((l, a, b)) = self.annuler.pop() {
                    self.retablir.push((std::mem::replace(&mut self.lignes, l), self.cl, self.cc));
                    self.cl = a.min(self.lignes.len() - 1);
                    self.cc = b;
                    self.ancre = None;
                    self.modifie = true;
                    self.message = "annulé".into();
                }
            }
            Action::Retablir => {
                if let Some((l, a, b)) = self.retablir.pop() {
                    self.annuler.push((std::mem::replace(&mut self.lignes, l), self.cl, self.cc));
                    self.cl = a.min(self.lignes.len() - 1);
                    self.cc = b;
                    self.ancre = None;
                    self.modifie = true;
                    self.message = "rétabli".into();
                }
            }
            Action::Copier | Action::Couper => {
                // sans sélection : la ligne entière
                let t = match self.texte_choisi() {
                    Some(t) => t,
                    None => {
                        let l: String = self.lignes[self.cl].iter().collect();
                        l + "\n"
                    }
                };
                self.presse = t.clone();
                console::ecrire_presse(&t);
                if act == Action::Couper {
                    self.memoriser();
                    if self.bornes().is_some() {
                        self.effacer_choix();
                    } else if self.lignes.len() > 1 {
                        self.lignes.remove(self.cl);
                        self.cl = self.cl.min(self.lignes.len() - 1);
                        self.cc = 0;
                        self.modifie = true;
                    } else {
                        self.lignes[0].clear();
                        self.cc = 0;
                        self.modifie = true;
                    }
                    self.message = "coupé".into();
                } else {
                    self.message = format!("copié : {} caractère(s)", t.chars().count());
                }
            }
            Action::Coller => {
                let t = console::lire_presse().unwrap_or_else(|| self.presse.clone());
                if !t.is_empty() {
                    self.memoriser();
                    self.effacer_choix();
                    self.inserer(&t);
                }
            }
            Action::ToutSelectionner => {
                self.ancre = Some((0, 0));
                self.cl = self.lignes.len() - 1;
                self.cc = self.lignes[self.cl].len();
                self.focus = Focus::Editeur;
            }
            Action::Rechercher => {
                self.but_saisie = Saisie::Rechercher;
                self.saisie = Some(self.recherche.clone());
            }
            Action::Suivant => self.chercher(),
            Action::SupprimerLigne => self.touche_editeur(Touche::Ctrl('k'), hauteur),
            Action::Dupliquer => self.touche_editeur(Touche::Ctrl('d'), hauteur),
            Action::Lancer => self.lancer(),
            Action::Entrees => {
                self.but_saisie = Saisie::Entrees;
                self.saisie = Some(self.entrees.clone());
            }
            Action::Pas => self.avancer(Avance::Pas),
            Action::Dessus => self.avancer(Avance::Dessus),
            Action::Continuer => {
                if self.deb.is_some() {
                    self.avancer(Avance::Continuer)
                } else {
                    self.lancer()
                }
            }
            Action::Point => {
                let l = self.cl;
                if !self.points.remove(&l) {
                    self.points.insert(l);
                }
                self.message = format!("points d'arrêt : {}", if self.points.is_empty() { "aucun".to_string() } else {
                    let mut v: Vec<usize> = self.points.iter().map(|x| x + 1).collect();
                    v.sort();
                    v.iter().map(|x| x.to_string()).collect::<Vec<_>>().join(", ") });
            }
            Action::Arreter => {
                if let Some(d) = self.deb.take() {
                    self.rapport = vec![format!("pas à pas arrêté après {} instructions", d.et.pas)];
                    self.mem = Some(d.mem);
                    self.message = "retour à l'édition".into();
                }
            }
            Action::Cube => self.focus = if self.focus == Focus::Editeur { Focus::Cube } else { Focus::Editeur },
            Action::Etage(e) => {
                self.etage = e;
                self.message = format!("étage {}", e);
            }
            Action::Valeurs => self.touche_cube(Touche::Car('m'), lc, hc),
            Action::Ajuster => self.touche_cube(Touche::Car('a'), lc, hc),
            Action::Touches => {
                self.deb = None;
                self.rapport = vec![
                    "F10 ou Alt+F, E, X, C, A : les menus (la souris marche aussi).".into(),
                    "F5 lancer · F7 pas à pas · F8 pas par-dessus · F9 point d'arrêt · F4 entrées".into(),
                    "Ctrl+S enregistrer · Ctrl+O ouvrir · Ctrl+N nouveau · Ctrl+Q quitter".into(),
                    "Maj+flèches sélectionner · Ctrl+C/X/V copier, couper, coller · Ctrl+A tout".into(),
                    "Ctrl+Z annuler · Ctrl+Y rétablir · Ctrl+F rechercher · F3 suivant".into(),
                    "F6 passer au cube : 0-3 étage, l largeur, +/- zoom, m couleurs/valeurs".into(),
                ];
            }
            Action::Apropos => {
                self.message = "Atelier vtx : Vercintorix, le langage du cube chromatique et de la logique à quatre valeurs".into();
            }
        }
    }

    fn touche_editeur(&mut self, k: Touche, hauteur: usize) {
        // Maj + déplacement : la sélection s'étend ; un déplacement seul l'abandonne
        if let Touche::Maj(b) = k {
            if self.ancre.is_none() {
                self.ancre = Some(self.curseur());
            }
            let a = self.ancre;
            self.touche_editeur(*b, hauteur);
            self.ancre = a;
            return;
        }
        let deplacement = matches!(k, Touche::Haut | Touche::Bas | Touche::Gauche | Touche::Droite | Touche::Debut | Touche::Fin
            | Touche::PageHaut | Touche::PageBas);
        if deplacement {
            self.ancre = None;
        } else if matches!(k, Touche::Car(_) | Touche::Entree | Touche::Tab | Touche::Retour | Touche::Suppr) && self.bornes().is_some() {
            self.memoriser();
            self.effacer_choix();
            self.frappe = false;
            if matches!(k, Touche::Retour | Touche::Suppr) {
                return;
            }
        } else {
            self.ancre = None;
        }
        if let Touche::Colle(t) = &k {
            self.memoriser();
            self.inserer(t);
            return;
        }
        let n = self.lignes.len();
        let frappe = std::mem::replace(&mut self.frappe, false);
        self.frappe = frappe;
        match k {
            Touche::Car(x) => {
                // l'annulation reprend un mot entier, pas une lettre
                if !self.frappe || x == ' ' {
                    self.memoriser();
                }
                let mut cc = self.cc.min(self.ligne().len());
                // « } » sur une ligne vide : la fermante revient d'un niveau
                if x == '}' && cc >= 4 && self.lignes[self.cl].iter().all(|c| *c == ' ') {
                    self.lignes[self.cl].truncate(cc - 4);
                    cc -= 4;
                }
                self.lignes[self.cl].insert(cc, x);
                self.cc = cc + 1;
                self.modifie = true;
                self.frappe = true;
                return;
            }
            Touche::Tab => {
                self.memoriser();
                let cc = self.cc.min(self.ligne().len());
                for _ in 0..4 {
                    self.lignes[self.cl].insert(cc, ' ');
                }
                self.cc = cc + 4;
                self.modifie = true;
            }
            Touche::Entree => {
                self.memoriser();
                let cc = self.cc.min(self.ligne().len());
                let reste: Vec<char> = self.lignes[self.cl].split_off(cc);
                // indentation de la ligne courante, plus un niveau après « { »
                let mut retrait = self.lignes[self.cl].iter().take_while(|c| **c == ' ').count();
                if self.lignes[self.cl].iter().rev().find(|c| **c != ' ') == Some(&'{') {
                    retrait += 4;
                }
                let mut neuve: Vec<char> = vec![' '; retrait];
                let reste_t: Vec<char> = reste.into_iter().skip_while(|c| *c == ' ').collect();
                if reste_t.first() == Some(&'}') && retrait >= 4 {
                    // « {|} » : la fermante descend d'une ligne, au retrait d'origine
                    let mut fermee: Vec<char> = vec![' '; retrait - 4];
                    fermee.extend(reste_t);
                    self.lignes.insert(self.cl + 1, neuve.clone());
                    self.lignes.insert(self.cl + 2, fermee);
                } else {
                    neuve.extend(reste_t);
                    self.lignes.insert(self.cl + 1, neuve);
                }
                self.cl += 1;
                self.cc = retrait;
                self.modifie = true;
            }
            Touche::Retour => {
                let cc = self.cc.min(self.ligne().len());
                if cc > 0 {
                    self.memoriser();
                    // dans le retrait : on recule d'un niveau
                    let tout_blanc = self.lignes[self.cl][..cc].iter().all(|c| *c == ' ');
                    let k = if tout_blanc && cc % 4 == 0 { 4 } else { 1 };
                    self.lignes[self.cl].drain(cc - k..cc);
                    self.cc = cc - k;
                    self.modifie = true;
                } else if self.cl > 0 {
                    self.memoriser();
                    let l = self.lignes.remove(self.cl);
                    self.cl -= 1;
                    self.cc = self.lignes[self.cl].len();
                    self.lignes[self.cl].extend(l);
                    self.modifie = true;
                }
            }
            Touche::Suppr => {
                let cc = self.cc.min(self.ligne().len());
                if cc < self.ligne().len() {
                    self.memoriser();
                    self.lignes[self.cl].remove(cc);
                    self.modifie = true;
                } else if self.cl + 1 < n {
                    self.memoriser();
                    let l = self.lignes.remove(self.cl + 1);
                    self.lignes[self.cl].extend(l);
                    self.modifie = true;
                }
            }
            Touche::Haut => self.cl = self.cl.saturating_sub(1),
            Touche::Bas => self.cl = (self.cl + 1).min(n - 1),
            Touche::Gauche => {
                if self.cc.min(self.ligne().len()) > 0 {
                    self.cc = self.cc.min(self.ligne().len()) - 1;
                } else if self.cl > 0 {
                    self.cl -= 1;
                    self.cc = self.ligne().len();
                }
            }
            Touche::Droite => {
                if self.cc < self.ligne().len() {
                    self.cc += 1;
                } else if self.cl + 1 < n {
                    self.cl += 1;
                    self.cc = 0;
                }
            }
            Touche::Debut => {
                let r = self.ligne().iter().take_while(|c| **c == ' ').count();
                self.cc = if self.cc == r { 0 } else { r };
            }
            Touche::Fin => self.cc = self.ligne().len(),
            Touche::PageHaut => self.cl = self.cl.saturating_sub(hauteur),
            Touche::PageBas => self.cl = (self.cl + hauteur).min(n - 1),
            Touche::Ctrl('k') => {
                // supprime la ligne
                self.memoriser();
                if self.lignes.len() > 1 {
                    self.lignes.remove(self.cl);
                    self.cl = self.cl.min(self.lignes.len() - 1);
                } else {
                    self.lignes[0].clear();
                }
                self.modifie = true;
            }
            Touche::Ctrl('d') => {
                // duplique la ligne
                self.memoriser();
                let l = self.lignes[self.cl].clone();
                self.lignes.insert(self.cl + 1, l);
                self.cl += 1;
                self.modifie = true;
            }
            _ => {}
        }
        self.frappe = false;
    }

    fn touche_cube(&mut self, k: Touche, lc: u32, hc: u32) {
        let l = self.largeur;
        let pas_page = l * (hc * 2) * self.zoom;
        match k {
            Touche::Gauche => self.sel = self.sel.saturating_sub(self.zoom),
            Touche::Droite => self.sel = (self.sel + self.zoom).min(0xFF_FFFF),
            Touche::Haut => self.sel = self.sel.saturating_sub(l * self.zoom),
            Touche::Bas => self.sel = (self.sel + l * self.zoom).min(0xFF_FFFF),
            Touche::PageHaut => self.sel = self.sel.saturating_sub(pas_page),
            Touche::PageBas => self.sel = (self.sel + pas_page).min(0xFF_FFFF),
            Touche::Debut => self.sel = 0,
            Touche::Car('l') => {
                let i = LARGEURS.iter().position(|&x| x == self.largeur).unwrap_or(0);
                self.largeur = LARGEURS[(i + 1) % LARGEURS.len()];
                self.ajuster(lc);
                self.message = format!("largeur de l'image : {} mots par ligne (zoom 1/{})", self.largeur, self.zoom);
            }
            Touche::Car('m') => {
                self.mode_valeur = !self.mode_valeur;
                self.message = if self.mode_valeur { "mode valeurs : tous les mots en dégradé selon leur grandeur".into() } else { "mode couleurs : chaque mot est sa couleur #RRGGBBAA (les petits nombres en dégradé)".into() };
            }
            Touche::Car(c @ '0'..='3') => {
                self.etage = c as u32 - '0' as u32;
                self.message = format!("étage {}", self.etage);
            }
            Touche::Car('L') => {
                let i = LARGEURS.iter().position(|&x| x == self.largeur).unwrap_or(0);
                self.largeur = LARGEURS[(i + LARGEURS.len() - 1) % LARGEURS.len()];
                self.ajuster(lc);
                self.message = format!("largeur de l'image : {} mots par ligne (zoom 1/{})", self.largeur, self.zoom);
            }
            Touche::Car('a') => {
                self.ajuster(lc);
                self.message = format!("zoom ajusté : 1/{}", self.zoom);
            }
            Touche::Car('+') => self.zoom = (self.zoom / 2).max(1),
            Touche::Car('-') => self.zoom = (self.zoom * 2).min(256),
            _ => {}
        }
        // la sélection reste visible
        let ligne_sel = self.sel / l;
        let ligne_base = self.base / l;
        let lignes_visibles = hc * 2 * self.zoom;
        if ligne_sel < ligne_base {
            self.base = ligne_sel * l;
        } else if ligne_sel >= ligne_base + lignes_visibles {
            self.base = (ligne_sel + 1).saturating_sub(lignes_visibles) * l;
        }
    }

    /// Le plus petit zoom (puissance de deux) qui fait tenir une ligne de l'image dans la largeur du cube.
    fn ajuster(&mut self, lc: u32) {
        let mut z = 1;
        while self.largeur / z > lc.max(1) && z < 256 {
            z *= 2;
        }
        self.zoom = z;
        self.sel = self.sel / self.largeur * self.largeur;
    }

    // ------------------------------------------------------------------ dessin
    fn memoire(&self) -> Option<&Memoire> {
        match &self.deb {
            Some(d) => Some(&d.mem),
            None => self.mem.as_ref(),
        }
    }

    fn pixel(&self, adr: u32) -> (u8, u8, u8) {
        let w = match self.memoire() {
            Some(m) if adr <= 0xFF_FFFF => m.lit(self.etage, adr),
            _ => 0,
        };
        // un mot non nul mais presque noir (un petit nombre : 285 vaut #0000011D) serait invisible : on le montre
        // en dégradé selon sa grandeur ; les vraies couleurs restent des couleurs
        let sombre = w != 0 && (w >> 24) < 24 && ((w >> 16) & 255) < 24 && ((w >> 8) & 255) < 24;
        if self.mode_valeur || sombre {
            if w == 0 {
                return (0, 0, 0);
            }
            let k = (32 - w.leading_zeros()) as f32 / 32.0;
            let r = (255.0 * (k * 1.6).min(1.0)) as u8;
            let g = (255.0 * ((k - 0.3) * 1.6).clamp(0.0, 1.0)) as u8;
            let b = (255.0 * ((k - 0.6) * 2.5).clamp(0.0, 1.0)) as u8;
            return (r.max(40), g, b);
        }
        ((w >> 24) as u8, (w >> 16) as u8, (w >> 8) as u8)
    }

    fn dessiner(&mut self, out: &mut String, l_ecran: usize, h_ecran: usize) {
        use std::fmt::Write as _;
        out.clear();
        out.push_str("\x1b[?25l\x1b[H");
        let le = (l_ecran * 11 / 20).max(30);           // largeur de l'éditeur
        let lc = l_ecran.saturating_sub(le + 1);        // largeur du cube
        let h = h_ecran.saturating_sub(3);              // hauteur utile (barre des menus, message, aide)
        let hc = (h * 3 / 5).max(4);                    // hauteur du cube (en caractères)
        let hr = h.saturating_sub(hc + 1);              // hauteur du rapport
        // défilement de l'éditeur
        if self.cl < self.haut {
            self.haut = self.cl;
        }
        if self.cl >= self.haut + h {
            self.haut = self.cl + 1 - h;
        }
        let gout = 5;
        let lt = le.saturating_sub(gout + 1);
        let cc = self.cc.min(self.lignes[self.cl].len());
        if cc < self.gauche {
            self.gauche = cc;
        }
        if cc >= self.gauche + lt {
            self.gauche = cc + 1 - lt;
        }
        let selb = self.sel;
        let lcube = self.largeur;
        // ----- barre des menus
        {
            let mut barre = String::from("\x1b[1;1H\x1b[48;5;237m\x1b[38;5;252m ");
            let mut largeur = 1;
            for (i, (t, _)) in MENUS.iter().enumerate() {
                let ouvert = self.menu.map(|m| m.0) == Some(i);
                if ouvert {
                    write!(barre, "\x1b[48;5;24m\x1b[38;5;231m {} \x1b[48;5;237m\x1b[38;5;252m ", t).unwrap();
                } else {
                    write!(barre, " {}  ", t).unwrap();
                }
                largeur += t.chars().count() + 3;
            }
            let droite = format!("{}{} ", Path::new(&self.fichier).file_name().map(|n| n.to_string_lossy().into_owned()).unwrap_or_default(),
                                 if self.modifie { " •" } else { "" });
            let reste = l_ecran.saturating_sub(largeur + droite.chars().count());
            write!(barre, "{}\x1b[38;5;180m{}\x1b[0m", " ".repeat(reste), droite).unwrap();
            out.push_str(&barre);
        }
        let choix = self.bornes();
        for y in 0..h {
            write!(out, "\x1b[{};1H", y + 2).unwrap();
            // ----- éditeur
            let nl = self.haut + y;
            if let Some(o) = &self.ouvrir {
                // la fenêtre « ouvrir » prend la place de l'éditeur
                let debut = o.sel.saturating_sub(h.saturating_sub(3));
                let t = if y == 0 {
                    format!(" Ouvrir dans {}", o.dossier.display())
                } else if y == 1 {
                    String::new()
                } else {
                    match o.entrees.get(debut + y - 2) {
                        Some((nom, dossier)) => format!("{} {}{}", if debut + y - 2 == o.sel { "▶" } else { " " }, nom, if *dossier { "/" } else { "" }),
                        None => String::new(),
                    }
                };
                let choisi = y >= 2 && debut + y - 2 == o.sel;
                let t: String = t.chars().take(le).collect();
                let fond = if y == 0 { "\x1b[48;5;24m\x1b[38;5;231m" } else if choisi { "\x1b[48;5;238m\x1b[38;5;231m" } else { "\x1b[48;5;234m\x1b[38;5;252m" };
                write!(out, "{}{}{}", fond, t, " ".repeat(le.saturating_sub(t.chars().count()))).unwrap();
            } else if nl < self.lignes.len() {
                let erreur = self.ligne_erreur == Some(nl);
                let execution = self.deb.as_ref().and_then(|d| d.ligne) == Some(nl);
                let fond = if execution { "\x1b[48;5;22m" } else if erreur { "\x1b[48;5;52m" } else if nl == self.cl && self.focus == Focus::Editeur { "\x1b[48;5;236m" } else { "\x1b[48;5;234m" };
                let marque = if execution { "\x1b[38;5;120m▶" } else if self.points.contains(&nl) { "\x1b[38;5;196m●" } else { " " };
                write!(out, "{}{}\x1b[38;5;240m{:>3} ", fond, marque, nl + 1).unwrap();
                let ligne = &self.lignes[nl];
                let cols = colorer(ligne);
                let mut ecrit = 0;
                for (k, ch) in ligne.iter().enumerate().skip(self.gauche).take(lt) {
                    let curseur = nl == self.cl && k == cc && self.focus == Focus::Editeur;
                    let choisi = choix.map(|(a, b)| (nl, k) >= a && (nl, k) < b).unwrap_or(false);
                    if curseur {
                        write!(out, "\x1b[7m{}{}\x1b[27m{}", cols[k], ch, fond).unwrap();
                    } else if choisi {
                        write!(out, "\x1b[48;5;25m{}{}{}", cols[k], ch, fond).unwrap();
                    } else {
                        write!(out, "{}{}", cols[k], ch).unwrap();
                    }
                    ecrit += 1;
                }
                if nl == self.cl && cc >= ligne.len() && self.focus == Focus::Editeur && ecrit < lt {
                    out.push_str("\x1b[7m \x1b[27m");
                    ecrit += 1;
                }
                write!(out, "{}{}", fond, " ".repeat(lt.saturating_sub(ecrit))).unwrap();
            } else {
                write!(out, "\x1b[48;5;234m\x1b[38;5;238m{:>4} {}", "~", " ".repeat(lt)).unwrap();
            }
            // ----- séparation
            out.push_str("\x1b[48;5;238m \x1b[0m");
            // ----- cube (en haut) puis rapport (en bas)
            if y < hc {
                for x in 0..lc as u32 {
                    let mut px = [(0u8, 0u8, 0u8); 2];
                    let mut sel = false;
                    for d in 0..2u32 {
                        let ligne_img = (self.base / lcube) + (2 * y as u32 + d) * self.zoom;
                        let col = x * self.zoom;
                        if col < lcube {
                            let adr = ligne_img * lcube + col;
                            px[d as usize] = self.pixel(adr);
                            if self.focus == Focus::Cube && adr <= selb && selb < adr + self.zoom && ligne_img <= selb / lcube && selb / lcube < ligne_img + self.zoom {
                                sel = true;
                            }
                        } else {
                            px[d as usize] = (20, 20, 24);
                        }
                    }
                    if sel {
                        out.push_str("\x1b[48;5;15m\x1b[38;5;196m▣");
                    } else {
                        write!(out, "\x1b[38;2;{};{};{}m\x1b[48;2;{};{};{}m▀", px[0].0, px[0].1, px[0].2, px[1].0, px[1].1, px[1].2).unwrap();
                    }
                }
                out.push_str("\x1b[0m");
            } else if y == hc {
                // ligne d'information du cube
                let w = self.memoire().map(|m| m.lit(self.etage, self.sel)).unwrap_or(0);
                let info = format!(" étage {} · @{}[{}] = #{:08X} ({}) · {} mots/ligne · zoom 1/{} ", self.etage, self.etage, self.sel, w, w,
                                   self.largeur, self.zoom);
                let info: String = info.chars().take(lc).collect();
                write!(out, "\x1b[48;5;24m\x1b[38;5;231m{}{}\x1b[0m", info, " ".repeat(lc.saturating_sub(info.chars().count()))).unwrap();
            } else {
                let k = y - hc - 1;
                let lignes_r = if self.deb.is_some() { self.panneau() } else { self.rapport.clone() };
                // les quatre premières lignes du panneau restent ; la console défile en dessous
                let t = if self.deb.is_some() && lignes_r.len() > hr {
                    let fixe = 6.min(hr);
                    if k < fixe { lignes_r[k].clone() } else { lignes_r.get(lignes_r.len() - (hr - fixe) + (k - fixe)).cloned().unwrap_or_default() }
                } else {
                    let debut = lignes_r.len().saturating_sub(hr);
                    lignes_r.get(debut + k).cloned().unwrap_or_default()
                };
                let couleur = if t.starts_with("erreur") { "\x1b[38;5;203m" } else if t.starts_with('»') { "\x1b[38;5;229m" } else if t.starts_with("pas à pas") { "\x1b[38;5;120m" } else { "\x1b[38;5;250m" };
                let t: String = t.chars().take(lc).collect();
                write!(out, "\x1b[48;5;233m{}{}{}\x1b[0m", couleur, t, " ".repeat(lc.saturating_sub(t.chars().count()))).unwrap();
            }
        }
        // ----- message et touches
        let titre = format!(" {}{} ", self.fichier, if self.modifie { " •" } else { "" });
        let msg = match &self.saisie {
            Some(s) if self.but_saisie == Saisie::NouveauFichier => format!(" Nom du nouveau fichier, Entrée pour valider : {}▌", s),
            Some(s) if self.but_saisie == Saisie::EnregistrerSous => format!(" Enregistrer sous (nom ou chemin), Entrée pour valider : {}▌", s),
            Some(s) if self.but_saisie == Saisie::Rechercher => format!(" Rechercher, Entrée pour valider : {}▌", s),
            Some(s) => format!(" Entrées du programme (nombres séparés par des espaces), Entrée pour valider : {}▌", s),
            None => format!("{} {}", titre, self.message),
        };
        let msg: String = msg.chars().take(l_ecran).collect();
        write!(out, "\x1b[{};1H\x1b[48;5;236m\x1b[38;5;231m{}{}\x1b[0m", h + 2, msg, " ".repeat(l_ecran.saturating_sub(msg.chars().count()))).unwrap();
        let aide = if self.ouvrir.is_some() {
            " ↑↓ choisir · Entrée ouvrir · Ctrl+N nouveau fichier · Échap revenir · Ctrl+Q quitter"
        } else if self.deb.is_some() && self.focus == Focus::Editeur {
            " F7 pas · F8 pas par-dessus · F5 continuer · F9 point d'arrêt · F6 cube · Échap arrêter le pas à pas · Ctrl+Q quitter"
        } else if self.focus == Focus::Editeur {
            " F10 menus · F5 lancer · F7 pas à pas · F9 point d'arrêt · F4 entrées · Ctrl+S enregistrer · Ctrl+O ouvrir · F6 cube · Ctrl+Q quitter"
        } else {
            " flèches · Pg↑↓ · 0-3 étage · l/L largeur · a ajuster · +/- zoom · m couleurs/valeurs · Début @0 · F6/Échap éditeur · F5 lancer · Ctrl+Q quitter"
        };
        let aide: String = aide.chars().take(l_ecran).collect();
        write!(out, "\x1b[{};1H\x1b[48;5;24m\x1b[38;5;231m{}{}\x1b[0m", h + 3, aide, " ".repeat(l_ecran.saturating_sub(aide.chars().count()))).unwrap();
        // ----- le menu ouvert, par-dessus le reste
        if let Some((m, sel)) = self.menu {
            let (x0, _) = titres_menus()[m];
            let entrees = MENUS[m].1;
            let lg = entrees.iter().map(|(t, r, _)| t.chars().count() + r.chars().count() + 4).max().unwrap_or(10).max(20);
            for (i, (t, r, _)) in entrees.iter().enumerate() {
                let fond = if i == sel { "\x1b[48;5;24m\x1b[38;5;231m" } else { "\x1b[48;5;238m\x1b[38;5;252m" };
                let espace = lg.saturating_sub(t.chars().count() + r.chars().count() + 2);
                write!(out, "\x1b[{};{}H{} {}{}\x1b[38;5;248m{} \x1b[0m", i + 2, x0 + 1, fond, t, " ".repeat(espace), r).unwrap();
            }
        }
    }
}

fn decouper(texte: &str) -> Vec<Vec<char>> {
    let mut lignes: Vec<Vec<char>> = texte.split('\n').map(|l| l.trim_end_matches('\r').chars().collect()).collect();
    if lignes.len() > 1 && lignes.last().map(|l| l.is_empty()).unwrap_or(false) {
        lignes.pop();
    }
    if lignes.is_empty() {
        lignes.push(Vec::new());
    }
    lignes
}

/// Le dossier de départ sans fichier : le dossier courant s'il contient des programmes .vtx ; sinon (par exemple
/// …/vtx-rs/target/release, après un double-clic) on remonte au paquet, là où sont les exemples.
fn dossier_de_depart() -> PathBuf {
    let ici = std::env::current_dir().unwrap_or_default();
    // un dossier qui contient déjà des programmes : c'est là qu'on travaille
    let a_des_vtx = std::fs::read_dir(&ici).map(|l| l.flatten().any(|e| e.file_name().to_string_lossy().ends_with(".vtx"))).unwrap_or(false);
    if a_des_vtx {
        return ici;
    }
    let mut p = ici.clone();
    for _ in 0..4 {
        if p.join("exemples").is_dir() {
            return p;
        }
        match p.parent() {
            Some(q) => p = q.to_path_buf(),
            None => break,
        }
    }
    if let Ok(exe) = std::env::current_exe() {
        let mut p = exe.parent().map(|x| x.to_path_buf()).unwrap_or_default();
        for _ in 0..5 {
            if p.join("exemples").is_dir() {
                return p;
            }
            match p.parent() {
                Some(q) => p = q.to_path_buf(),
                None => break,
            }
        }
    }
    ici
}

/// La lettre qui ouvre un menu avec Alt : f, e, x, c, a.
fn menu_lettre(t: &str) -> char {
    match t {
        "Fichier" => 'f',
        "Édition" => 'e',
        "Exécuter" => 'x',
        "Cube" => 'c',
        _ => 'a',
    }
}

/// L'atelier, sur un fichier, ou (None) en commençant par la fenêtre « ouvrir ».
pub fn atelier(fichier: Option<&str>) {
    let mut a = Atelier {
        fichier: String::new(), lignes: vec![Vec::new()], cl: 0, cc: 0, haut: 0, gauche: 0, modifie: false, annuler: Vec::new(), frappe: false,
        focus: Focus::Editeur, entrees: String::new(), saisie: None, mem: None, etage: 1, largeur: 64, base: 0, zoom: 1, sel: 0,
        mode_valeur: false, message: String::new(), rapport: Vec::new(),
        ligne_erreur: None, quitter: false, confirmer_sortie: false, deb: None, points: HashSet::new(), ouvrir: None,
        but_saisie: Saisie::Entrees, ancre: None, retablir: Vec::new(), presse: String::new(), menu: None, recherche: String::new(),
        glisser: false,
    };
    match fichier {
        Some(f) => a.charger_fichier(Path::new(f)),
        None => {
            let d = dossier_de_depart();
            a.charger_fichier(&d.join("nouveau.vtx"));
            a.ouvrir_dossier(d);
        }
    }
    a.rapport = vec!["Bienvenue dans l'atelier vtx.".into(),
        "F5 compile et lance ; F7 avance pas à pas, ligne par ligne ; F9 pose un point d'arrêt.".into(),
        "F6 passe au cube : 0-3 choisit l'étage, l la largeur de l'image, +/- le zoom.".into(),
        "Ctrl+O ouvre un autre fichier.".into()];
    console::brut();
    let mut sortie = std::io::stdout();
    // titre de la fenêtre, écran à part, souris (appuis et glissements, en SGR), collage encadré
    let _ = write!(sortie, "\x1b]0;Atelier vtx\x07\x1b[?1049h\x1b[?25l\x1b[?1002h\x1b[?1006h\x1b[?2004h");
    let ancien_crochet = std::panic::take_hook();
    std::panic::set_hook(Box::new(move |info| {
        console::retablir();
        print!("\x1b[?2004l\x1b[?1006l\x1b[?1002l\x1b[0m\x1b[?25h\x1b[?1049l");
        ancien_crochet(info);
    }));
    let mut ecran = String::new();
    while !a.quitter {
        let (le, he) = console::taille();
        a.dessiner(&mut ecran, le, he);
        let _ = sortie.write_all(ecran.as_bytes());
        let _ = sortie.flush();
        let tampon = match console::lire() {
            Some(t) => t,
            None => break,
        };
        let h = he.saturating_sub(3);
        let le_ed = (le * 11 / 20).max(30);
        let lc = le.saturating_sub(le_ed + 1) as u32;
        let hc = ((h * 3 / 5).max(4)) as u32;
        let mut tampon = tampon;
        // un collage trop long pour une seule lecture : on lit jusqu'à la fin du texte collé
        while String::from_utf8_lossy(&tampon).contains("\x1b[200~") && !String::from_utf8_lossy(&tampon).contains("\x1b[201~") {
            match console::lire() {
                Some(t) => tampon.extend(t),
                None => break,
            }
        }
        #[allow(unused_mut)]
        let mut touches = lire_touches(&tampon);
        // la console de Windows colle en « tapant » le texte : plusieurs lignes d'un coup, c'est un collage
        #[cfg(windows)]
        {
            let t = String::from_utf8_lossy(&tampon);
            if !t.contains('\x1b') && t.matches('\r').count() >= 2 && a.saisie.is_none() {
                touches = vec![Touche::Colle(t.into_owned())];
            }
        }
        for k in touches {
            // ----- une saisie en cours (entrées, nom de fichier, recherche)
            if let Some(s) = a.saisie.as_mut() {
                match k {
                    Touche::Entree => {
                        let v = a.saisie.take().unwrap();
                        match a.but_saisie {
                            Saisie::Entrees => {
                                a.entrees = v;
                                a.message = format!("entrées : {}", if a.entrees.trim().is_empty() { "aucune" } else { a.entrees.trim() });
                            }
                            Saisie::NouveauFichier | Saisie::EnregistrerSous => {
                                let mut nom = v.trim().to_string();
                                if !nom.is_empty() {
                                    if !nom.ends_with(".vtx") {
                                        nom.push_str(".vtx");
                                    }
                                    let dossier = a.ouvrir.as_ref().map(|o| o.dossier.clone())
                                        .or_else(|| Path::new(&a.fichier).parent().map(|p| p.to_path_buf())).unwrap_or_default();
                                    let chemin = dossier.join(nom);
                                    if a.but_saisie == Saisie::NouveauFichier {
                                        a.ouvrir = None;
                                        a.charger_fichier(&chemin);
                                    } else {
                                        a.fichier = chemin.to_string_lossy().into_owned();
                                    }
                                    a.enregistrer();
                                }
                            }
                            Saisie::Rechercher => {
                                a.recherche = v;
                                a.chercher();
                            }
                        }
                        a.but_saisie = Saisie::Entrees;
                    }
                    Touche::Echap | Touche::Ctrl('c') => {
                        a.saisie = None;
                        a.but_saisie = Saisie::Entrees;
                    }
                    Touche::Retour => {
                        s.pop();
                    }
                    Touche::Car(c) => s.push(c),
                    Touche::Colle(t) => s.push_str(t.lines().next().unwrap_or("")),
                    _ => {}
                }
                continue;
            }
            // ----- la souris
            if let Touche::Souris { b, x, y, appui } = k {
                let (x, y) = (x.saturating_sub(1), y.saturating_sub(1));
                if b == 0 && appui && y == 0 {
                    // un titre de la barre des menus
                    a.menu = titres_menus().iter().position(|&(x0, l)| x >= x0 && x < x0 + l).map(|m| (m, 0));
                    continue;
                }
                if let Some((m, _)) = a.menu {
                    if b == 0 && appui {
                        let (x0, _) = titres_menus()[m];
                        let entrees = MENUS[m].1;
                        a.menu = None;
                        if y >= 1 && y <= entrees.len() && x >= x0 {
                            let act = entrees[y - 1].2;
                            a.dessiner(&mut ecran, le, he);
                            let _ = sortie.write_all(ecran.as_bytes());
                            a.agir(act, h, lc, hc);
                        }
                    }
                    continue;
                }
                if a.ouvrir.is_some() {
                    if b == 0 && appui && y >= 3 {
                        if let Some(o) = a.ouvrir.as_mut() {
                            let debut = o.sel.saturating_sub(h.saturating_sub(3));
                            let i = debut + y - 3;
                            if i < o.entrees.len() {
                                if o.sel == i {
                                    a.touche_ouvrir(Touche::Entree, h);
                                } else {
                                    o.sel = i;
                                }
                            }
                        }
                    } else if b == 64 {
                        a.touche_ouvrir(Touche::Haut, h);
                    } else if b == 65 {
                        a.touche_ouvrir(Touche::Bas, h);
                    }
                    continue;
                }
                let dans_editeur = x < le_ed && y >= 1 && y <= h;
                match b {
                    0 | 32 if dans_editeur => {
                        let nl = (a.haut + y - 1).min(a.lignes.len() - 1);
                        let col = (a.gauche + x.saturating_sub(5)).min(a.lignes[nl].len());
                        if b == 0 && appui {
                            a.focus = Focus::Editeur;
                            a.cl = nl;
                            a.cc = col;
                            a.ancre = Some((nl, col));
                            a.glisser = true;
                        } else if b == 32 && a.glisser {
                            a.cl = nl;
                            a.cc = col;
                        }
                    }
                    0 if !appui => a.glisser = false,
                    0 if appui && x > le_ed && y >= 1 && (y - 1) < hc as usize => {
                        // un clic dans le cube : sélection du mot sous la souris
                        a.focus = Focus::Cube;
                        let col = ((x - le_ed - 1) as u32) * a.zoom;
                        let ligne_img = a.base / a.largeur + ((y - 1) as u32 * 2) * a.zoom;
                        if col < a.largeur {
                            a.sel = (ligne_img * a.largeur + col).min(0xFF_FFFF);
                        }
                    }
                    64 if dans_editeur => {
                        a.haut = a.haut.saturating_sub(3);
                        a.cl = a.cl.saturating_sub(3);
                    }
                    65 if dans_editeur => {
                        a.cl = (a.cl + 3).min(a.lignes.len() - 1);
                        a.haut = (a.haut + 3).min(a.lignes.len().saturating_sub(1));
                    }
                    _ => {}
                }
                if b == 0 && !appui {
                    a.glisser = false;
                }
                continue;
            }
            // ----- un menu ouvert : flèches, Entrée, Échap
            if let Some((m, sel)) = a.menu {
                let n = MENUS[m].1.len();
                match k {
                    Touche::Gauche => a.menu = Some(((m + MENUS.len() - 1) % MENUS.len(), 0)),
                    Touche::Droite => a.menu = Some(((m + 1) % MENUS.len(), 0)),
                    Touche::Haut => a.menu = Some((m, (sel + n - 1) % n)),
                    Touche::Bas => a.menu = Some((m, (sel + 1) % n)),
                    Touche::Entree => {
                        a.menu = None;
                        let act = MENUS[m].1[sel].2;
                        a.dessiner(&mut ecran, le, he);
                        let _ = sortie.write_all(ecran.as_bytes());
                        let _ = sortie.flush();
                        a.agir(act, h, lc, hc);
                    }
                    Touche::Alt(c) => a.menu = MENUS.iter().position(|(t, _)| menu_lettre(t) == c).map(|m| (m, 0)),
                    Touche::Ctrl('q') => a.agir(Action::Quitter, h, lc, hc),
                    _ => a.menu = None,
                }
                continue;
            }
            if a.ouvrir.is_some() && k != Touche::Ctrl('q') {
                if k == Touche::F(10) {
                    a.menu = Some((0, 0));
                } else {
                    a.touche_ouvrir(k, h);
                }
                continue;
            }
            if k != Touche::Ctrl('q') && k != Touche::Ctrl('o') {
                a.confirmer_sortie = false;
            }
            let ed = a.focus == Focus::Editeur;
            let act = match &k {
                Touche::F(10) => {
                    a.menu = Some((0, 0));
                    continue;
                }
                Touche::Alt(c) => {
                    a.menu = MENUS.iter().position(|(t, _)| menu_lettre(t) == *c).map(|m| (m, 0));
                    continue;
                }
                Touche::F(1) => Some(Action::Touches),
                Touche::Ctrl('q') => Some(Action::Quitter),
                Touche::F(2) | Touche::Ctrl('s') => Some(Action::Enregistrer),
                Touche::Ctrl('o') => Some(Action::Ouvrir),
                Touche::Ctrl('n') => Some(Action::Nouveau),
                Touche::F(4) | Touche::Ctrl('e') => Some(Action::Entrees),
                Touche::F(5) | Touche::Ctrl('r') => Some(if a.deb.is_some() { Action::Continuer } else { Action::Lancer }),
                Touche::F(7) => Some(Action::Pas),
                Touche::F(8) => Some(Action::Dessus),
                Touche::F(9) => Some(Action::Point),
                Touche::F(3) => Some(Action::Suivant),
                Touche::F(6) | Touche::Ctrl('t') => Some(Action::Cube),
                Touche::Ctrl('z') if ed => Some(Action::Annuler),
                Touche::Ctrl('y') if ed => Some(Action::Retablir),
                Touche::Ctrl('x') if ed => Some(Action::Couper),
                Touche::Ctrl('c') if ed => Some(Action::Copier),
                Touche::Ctrl('v') if ed => Some(Action::Coller),
                Touche::Ctrl('a') if ed => Some(Action::ToutSelectionner),
                Touche::Ctrl('f') => Some(Action::Rechercher),
                Touche::Ctrl('k') if ed => Some(Action::SupprimerLigne),
                Touche::Ctrl('d') if ed => Some(Action::Dupliquer),
                Touche::Echap if a.deb.is_some() && ed => Some(Action::Arreter),
                Touche::Echap if ed => {
                    a.ancre = None;
                    continue;
                }
                Touche::Echap | Touche::Tab if !ed => {
                    a.focus = Focus::Editeur;
                    continue;
                }
                _ => None,
            };
            if let Some(act) = act {
                if matches!(act, Action::Lancer | Action::Pas | Action::Dessus | Action::Continuer) {
                    a.message = if act == Action::Lancer { "compilation et exécution…".into() } else { "exécution…".into() };
                    a.dessiner(&mut ecran, le, he);
                    let _ = sortie.write_all(ecran.as_bytes());
                    let _ = sortie.flush();
                }
                a.agir(act, h, lc, hc);
                continue;
            }
            let edition = matches!(k, Touche::Car(_) | Touche::Entree | Touche::Retour | Touche::Suppr | Touche::Tab | Touche::Colle(_));
            if ed && edition && a.deb.is_some() {
                a.message = "pas à pas en cours : Échap pour l'arrêter, puis modifiez".into();
            } else if ed {
                a.touche_editeur(k, h);
            } else {
                a.touche_cube(k, lc, hc);
            }
            if a.ligne_erreur.is_some() && a.modifie {
                a.ligne_erreur = None;
            }
        }
    }
    console::retablir();
    let _ = write!(sortie, "\x1b[?2004l\x1b[?1006l\x1b[?1002l\x1b[0m\x1b[?25h\x1b[?1049l");
    let _ = sortie.flush();
}
