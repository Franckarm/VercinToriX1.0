// Ce que la machine hôte donne à un programme interactif, pareil sur le SPU-32 et le SPU-64 (services 16 à 21) :
// la souris dans l'image, les touches, l'horloge, la cadence des images. Une fenêtre (la toile ou l'atelier) écrit ici
// ce qu'elle voit ; sans fenêtre, tout vaut 0 (pas de souris, pas de touche), sauf l'horloge.
//
//   16 souris()      x (bits 0-11) | y (12-23) | boutons (24-26 : gauche 1, droit 2, milieu 4) | dans l'image (27)
//   17 touche()      la prochaine touche appuyée (un caractère, ou 65536 + code de touche Windows), 0 s'il n'y en a pas
//   18 horloge()     millisecondes depuis le lancement
//   19 cadence(ms)   intervalle minimal entre deux presenter() (0 : le plus vite possible) ; rend l'ancien
//   20 molette()     crans de molette depuis le dernier appel (signé)
//   21 appuyee(t)    1 si la touche t est enfoncée en ce moment, sinon 0
//   23 souris_glisse()  le déplacement de la souris depuis le dernier appel : dx (bits 0-15), dy (16-31), signés
use std::collections::VecDeque;
use std::sync::atomic::{AtomicBool, AtomicI32, AtomicU32, AtomicU64, Ordering};
use std::sync::Mutex;
use std::time::{Duration, Instant};

pub static SOURIS: AtomicU32 = AtomicU32::new(0);
// le glissement de la souris (pixels de l'écran) depuis le dernier souris_glisse(), et sa dernière position vue
static GLISSE_X: AtomicI32 = AtomicI32::new(0);
static GLISSE_Y: AtomicI32 = AtomicI32::new(0);
static DERNIERE_POS: Mutex<Option<(i32, i32)>> = Mutex::new(None);
pub static MOLETTE: AtomicI32 = AtomicI32::new(0);
pub static TOUCHES: Mutex<VecDeque<u32>> = Mutex::new(VecDeque::new());
// les touches enfoncées : un bit par code de touche Windows (0 à 255)
static ENFONCEES: [AtomicU32; 8] = [const { AtomicU32::new(0) }; 8];
// 16 ms : 60 images par seconde au plus, comme la fenêtre de la toile
pub static CADENCE_MS: AtomicU32 = AtomicU32::new(16);
static DEBUT: Mutex<Option<Instant>> = Mutex::new(None);
static DERNIERE: Mutex<Option<Instant>> = Mutex::new(None);
/// L'horloge des images : une animation (GIF, images PNG) ou un scénario n'a pas de temps réel à suivre ; horloge()
/// y compte le temps des images déjà présentées (la cadence de chacune), et le programme se rejoue à l'identique,
/// sur toutes les machines et à toutes les vitesses.
pub static HORLOGE_IMAGES: AtomicBool = AtomicBool::new(false);
static TEMPS_IMAGES: AtomicU64 = AtomicU64::new(0);
/// Vrai quand une fenêtre écoute (sinon presenter() n'attend pas : les fichiers et les tests vont à pleine vitesse).
pub static FENETRE: AtomicBool = AtomicBool::new(false);

/// Un nouveau programme commence : l'horloge repart de zéro, les touches en attente sont oubliées.
pub fn remettre() {
    *DEBUT.lock().unwrap() = Some(Instant::now());
    *DERNIERE.lock().unwrap() = None;
    TEMPS_IMAGES.store(0, Ordering::Relaxed);
    TOUCHES.lock().unwrap().clear();
    MOLETTE.store(0, Ordering::Relaxed);
    CADENCE_MS.store(16, Ordering::Relaxed);
    SOURIS.store(0, Ordering::Relaxed);
    GLISSE_X.store(0, Ordering::Relaxed);
    GLISSE_Y.store(0, Ordering::Relaxed);
    *DERNIERE_POS.lock().unwrap() = None;
    tout_relacher();
    *SCENARIO.lock().unwrap() = (Vec::new(), 0, 0);
}

fn depuis_debut() -> u64 {
    if HORLOGE_IMAGES.load(Ordering::Relaxed) {
        return TEMPS_IMAGES.load(Ordering::Relaxed);
    }
    let mut d = DEBUT.lock().unwrap();
    d.get_or_insert_with(Instant::now).elapsed().as_millis() as u64
}

/// La souris, vue par la fenêtre, en points de l'image du programme.
pub fn poser_souris(x: i32, y: i32, boutons: u32, dedans: bool) {
    let v = (x.clamp(0, 4095) as u32) | ((y.clamp(0, 4095) as u32) << 12) | ((boutons & 7) << 24) | ((dedans as u32) << 27);
    SOURIS.store(v, Ordering::Relaxed);
}

/// La souris a bougé jusqu'en (mx, my), en pixels de la fenêtre : le glissement s'accumule.
pub fn glisser(mx: i32, my: i32) {
    let mut d = DERNIERE_POS.lock().unwrap();
    if let Some((x, y)) = *d {
        GLISSE_X.fetch_add(mx - x, Ordering::Relaxed);
        GLISSE_Y.fetch_add(my - y, Ordering::Relaxed);
    }
    *d = Some((mx, my));
}

/// Un glissement donné tel quel (les scénarios).
pub fn ajouter_glisse(dx: i32, dy: i32) {
    GLISSE_X.fetch_add(dx, Ordering::Relaxed);
    GLISSE_Y.fetch_add(dy, Ordering::Relaxed);
}

pub fn ajouter_molette(crans: i32) {
    MOLETTE.fetch_add(crans, Ordering::Relaxed);
}

/// Une touche appuyée : un caractère (code Unicode) ou une touche sans caractère (65536 + code Windows).
pub fn ajouter_touche(code: u32) {
    let mut t = TOUCHES.lock().unwrap();
    if t.len() < 256 {
        t.push_back(code);
    }
}

/// Une touche (code Windows, 0 à 255) enfoncée ou relâchée.
pub fn poser_enfoncee(vk: u32, bas: bool) {
    if vk < 256 {
        let (i, b) = ((vk >> 5) as usize, 1u32 << (vk & 31));
        if bas {
            ENFONCEES[i].fetch_or(b, Ordering::Relaxed);
        } else {
            ENFONCEES[i].fetch_and(!b, Ordering::Relaxed);
        }
    }
}

pub fn tout_relacher() {
    for e in ENFONCEES.iter() {
        e.store(0, Ordering::Relaxed);
    }
    SOURIS.fetch_and(!(7 << 24), Ordering::Relaxed);
}

/// Le code Windows d'une touche donnée comme dans touche() : une lettre ou un chiffre (majuscule ou minuscule), l'espace,
/// Entrée, Échap, Tab, Retour arrière, ou 65536 + code.
fn code_windows(t: u64) -> Option<u32> {
    if t >= 65536 {
        return if t - 65536 < 256 { Some((t - 65536) as u32) } else { None };
    }
    let c = char::from_u32(t as u32)?;
    match c {
        'a'..='z' => Some(c as u32 - 32),
        'A'..='Z' | '0'..='9' | ' ' => Some(c as u32),
        '\r' | '\n' => Some(13),
        '\u{1b}' => Some(27),
        '\t' => Some(9),
        '\u{8}' => Some(8),
        _ => None,
    }
}

/// presenter() vient de montrer une image : attendre la cadence, si une fenêtre la regarde.
pub fn attendre_cadence() {
    if !FENETRE.load(Ordering::Relaxed) {
        return;
    }
    let c = Duration::from_millis(CADENCE_MS.load(Ordering::Relaxed) as u64);
    let mut d = DERNIERE.lock().unwrap();
    if let Some(t) = *d {
        let e = t.elapsed();
        if e < c {
            std::thread::sleep(c - e);
        }
    }
    *d = Some(Instant::now());
}

/// Les services 16 à 21 ; None pour un autre numéro. `m` : le masque du mot (32 ou 64 bits), pour les nombres signés.
pub fn service(code: u64, arg: u64, m: u64) -> Option<u64> {
    Some(match code {
        16 => SOURIS.load(Ordering::Relaxed) as u64,
        17 => TOUCHES.lock().unwrap().pop_front().unwrap_or(0) as u64,
        18 => depuis_debut() & m,
        19 => CADENCE_MS.swap(arg.min(60_000) as u32, Ordering::Relaxed) as u64,
        20 => (MOLETTE.swap(0, Ordering::Relaxed) as i64 as u64) & m,
        // 23 : le glissement depuis le dernier appel, dx (bits 0-15) et dy (16-31), signés sur 16 bits
        23 => {
            let dx = GLISSE_X.swap(0, Ordering::Relaxed).clamp(-32768, 32767);
            let dy = GLISSE_Y.swap(0, Ordering::Relaxed).clamp(-32768, 32767);
            ((dx as u16 as u64) | ((dy as u16 as u64) << 16)) & m
        }
        21 => match code_windows(arg) {
            Some(vk) => ((ENFONCEES[(vk >> 5) as usize].load(Ordering::Relaxed) >> (vk & 31)) & 1) as u64,
            None => 0,
        },
        _ => return None,
    })
}

/// La souris vue dans une fenêtre où l'image (il × ih points) est dessinée en (x0, y0), sur dl × dh pixels.
#[allow(clippy::too_many_arguments)]
pub fn souris_dans_vue(mx: i32, my: i32, x0: i32, y0: i32, dl: i32, dh: i32, il: usize, ih: usize, boutons: u32) {
    glisser(mx, my);
    if dl <= 0 || dh <= 0 || il == 0 || ih == 0 {
        return;
    }
    let x = ((mx - x0) as i64 * il as i64).div_euclid(dl as i64) as i32;
    let y = ((my - y0) as i64 * ih as i64).div_euclid(dh as i64) as i32;
    let dedans = x >= 0 && y >= 0 && (x as usize) < il && (y as usize) < ih;
    poser_souris(x.clamp(0, il as i32 - 1), y.clamp(0, ih as i32 - 1), boutons, dedans);
}

/// Les messages de clavier d'une fenêtre Windows (WM_KEYDOWN 0x100, WM_KEYUP 0x101, WM_CHAR 0x102) : les touches sans
/// caractère (flèches, F1…, début, fin, pages, insertion, suppression) arrivent en 65536 + code, les autres en caractère.
pub fn clavier_windows(message: u32, wp: usize) {
    let vk = (wp & 0xFFFF) as u32;
    match message {
        0x100 | 0x104 => {
            poser_enfoncee(vk, true);
            if matches!(vk, 33..=40 | 45 | 46 | 112..=123) {
                ajouter_touche(65536 + vk);
            }
        }
        0x101 | 0x105 => poser_enfoncee(vk, false),
        0x102 => {
            // les caractères, et les touches Ctrl+lettre (1 à 26 : Ctrl+S donne 19), Échap
            if vk >= 32 || (1..=27).contains(&vk) {
                ajouter_touche(vk);
            }
        }
        _ => {}
    }
}

// ---- le scénario : des gestes écrits d'avance, rejoués image par image (vtx toile … --scenario FICHIER), pour montrer
// ou vérifier un programme interactif sans écran. Une ligne par geste, « IMAGE geste valeurs », appliqué après la
// présentation de l'image IMAGE (0 : avant la première) :
//   12 souris X Y BOUTONS        la souris (dans l'image ; boutons : gauche 1, droit 2, milieu 4)
//   12 touche CODE               une touche appuyée (un caractère, ou 65536 + code), lue par touche()
//   12 appui CODE / relache CODE une touche enfoncée ou relâchée, vue par appuyee()
//   12 molette CRANS             des crans de molette
//   12 glisse DX DY              un glissement de la souris (pixels de l'écran), lu par souris_glisse()
// « # » commence un commentaire.
struct Geste {
    image: usize,
    quoi: u8,
    v: [i64; 3],
}
static SCENARIO: Mutex<(Vec<Geste>, usize, usize)> = Mutex::new((Vec::new(), 0, 0));

pub fn charger_scenario(texte: &str) -> Result<usize, String> {
    let mut g = Vec::new();
    for (n, ligne) in texte.lines().enumerate() {
        let l = ligne.split('#').next().unwrap_or("").trim();
        if l.is_empty() {
            continue;
        }
        let m: Vec<&str> = l.split_whitespace().collect();
        let nb = |i: usize| -> Result<i64, String> {
            m.get(i).and_then(|t| t.parse::<i64>().ok()).ok_or(format!("scénario, ligne {} : nombre attendu", n + 1))
        };
        let image = nb(0)? as usize;
        let (quoi, k) = match m.get(1).copied() {
            Some("souris") => (0, 3),
            Some("touche") => (1, 1),
            Some("appui") => (2, 1),
            Some("relache") => (3, 1),
            Some("molette") => (4, 1),
            Some("glisse") => (5, 2),
            _ => return Err(format!("scénario, ligne {} : souris, touche, appui, relache, molette ou glisse attendu", n + 1)),
        };
        let mut v = [0i64; 3];
        for (j, x) in v.iter_mut().enumerate().take(k) {
            *x = nb(2 + j)?;
        }
        g.push(Geste { image, quoi, v });
    }
    g.sort_by_key(|x| x.image);
    let n = g.len();
    *SCENARIO.lock().unwrap() = (g, 0, 0);
    appliquer_scenario(0);
    Ok(n)
}

fn appliquer_scenario(image: usize) {
    let mut s = SCENARIO.lock().unwrap();
    while s.1 < s.0.len() && s.0[s.1].image <= image {
        let g = &s.0[s.1];
        match g.quoi {
            0 => poser_souris(g.v[0] as i32, g.v[1] as i32, g.v[2] as u32, true),
            1 => ajouter_touche(g.v[0] as u32),
            2 | 3 => {
                if let Some(vk) = code_windows(g.v[0] as u64) {
                    poser_enfoncee(vk, g.quoi == 2);
                }
            }
            4 => ajouter_molette(g.v[0] as i32),
            _ => ajouter_glisse(g.v[0] as i32, g.v[1] as i32),
        }
        s.1 += 1;
    }
}

/// Une image vient d'être présentée : les gestes prévus après elle.
pub fn image_presentee() {
    TEMPS_IMAGES.fetch_add(CADENCE_MS.load(Ordering::Relaxed) as u64, Ordering::Relaxed);
    let image = {
        let mut s = SCENARIO.lock().unwrap();
        if s.0.is_empty() {
            return;
        }
        s.2 += 1;
        s.2
    };
    appliquer_scenario(image);
}

/// 0.62 : les noms d'un dossier, triés (l'ordre des caractères), un par ligne, un sous-dossier terminé par « / » ; le
/// service 28 de Lugus et de Dunon. Err(true) : le nom existe mais n'est pas un dossier ; Err(false) : il est absent.
pub fn lister_dossier(chemin: &std::path::Path) -> Result<String, bool> {
    // le dossier d'un programme lancé depuis son propre dossier est le chemin vide : c'est « . »
    let chemin = if chemin.as_os_str().is_empty() { std::path::Path::new(".") } else { chemin };
    let lecture = match std::fs::read_dir(chemin) {
        Ok(l) => l,
        Err(_) => return Err(chemin.exists()),
    };
    let mut noms: Vec<String> = lecture
        .filter_map(|e| e.ok())
        .map(|e| {
            let n = e.file_name().to_string_lossy().into_owned();
            if e.path().is_dir() { n + "/" } else { n }
        })
        .collect();
    noms.sort();
    Ok(noms.iter().map(|n| n.clone() + "\n").collect())
}

/// 0.63 : un nom de cube mère : de 1 à 64 caractères (lettres, chiffres, « _ », « - », les lettres accentuées du
/// latin), sans « - » au bord, et dont le dernier morceau après un « - » n'est pas un nombre (sinon le nom d'un sous-cube,
/// NOM-ÉTAGE-FRÉQUENCE, serait ambigu)
pub fn car_de_mere_valide(x: char) -> bool {
    x.is_ascii_alphanumeric() || x == '_' || x == '-' || (('\u{C0}'..='\u{FF}').contains(&x) && x != '\u{D7}' && x != '\u{F7}')
}

pub fn nom_de_mere_valide(n: &str) -> bool {
    let c: Vec<char> = n.chars().collect();
    if c.is_empty() || c.len() > 64 || c[0] == '-' || c[c.len() - 1] == '-' {
        return false;
    }
    if !c.iter().all(|&x| car_de_mere_valide(x)) {
        return false;
    }
    !n.rsplit('-').next().unwrap().chars().all(|x| x.is_ascii_digit())
}

/// FNV-1a de 64 bits sur des caractères (l'indicatif d'un cube mère, l'empreinte d'un module)
pub fn fnv64_texte(t: &str) -> u64 {
    let mut h: u64 = 0xCBF29CE484222325;
    for c in t.chars() {
        h = (h ^ c as u64).wrapping_mul(0x100000001B3);
    }
    h
}

pub fn fnv64_octets(b: &[u8]) -> u64 {
    let mut h: u64 = 0xCBF29CE484222325;
    for &c in b {
        h = (h ^ c as u64).wrapping_mul(0x100000001B3);
    }
    h
}

/// le brassage des coiffes de cube (splitmix64, comme brasser() du lecteur d'ADN)
pub fn brasser64(z0: u64) -> u64 {
    let mut z = z0.wrapping_add(0x9E3779B97F4A7C15);
    z = (z ^ (z >> 30)).wrapping_mul(0xBF58476D1CE4E5B9);
    z = (z ^ (z >> 27)).wrapping_mul(0x94D049BB133111EB);
    z ^ (z >> 31)
}

/// 0.62c, 0.63 : ce qu'un nom de fichier de cube désigne (TETE : « cube128 » ou « cube64 ») : un cube simple
/// (TETE-ÉTAGE-FRÉQUENCE.cub), un sous-cube d'un cube mère (TETE-NOM-ÉTAGE-FRÉQUENCE.cub) ou un cube mère (TETE-NOM.cub)
#[derive(Debug, Clone, PartialEq)]
pub enum NomCube {
    Simple(usize, u64),
    Sous(String, usize, u64),
    Mere(String),
}

/// 0.64 : l'étage dans le nom d'un cube : Đ (le tau gallicum) pour l'étage 0, le code ; le chiffre pour les autres
pub fn lettre_etage(e: usize) -> String {
    if e == 0 { "Đ".to_string() } else { e.to_string() }
}

pub fn nom_de_cube(chemin: &std::path::Path, tete: &str) -> Option<NomCube> {
    let n = chemin.file_name()?.to_str()?;
    let r = n.strip_prefix(tete)?.strip_prefix('-')?.strip_suffix(".cub")?;
    let ef = |e: &str, f: &str| -> Option<(usize, u64)> {
        if f.is_empty() || f.len() > 8 || !f.bytes().all(|c| c.is_ascii_digit()) {
            return None;
        }
        // 0.64 : l'étage 0 (le code) se nomme par le tau gallicum, Đ ; les étages 1 à 3 par leur chiffre
        let e: usize = match e {
            "Đ" => 0,
            "1" => 1,
            "2" => 2,
            "3" => 3,
            _ => return None,
        };
        let f: u64 = f.parse().ok()?;
        if f > 0xFF_FFFF {
            return None;
        }
        Some((e, f))
    };
    let morceaux: Vec<&str> = r.rsplitn(3, '-').collect();
    if morceaux.len() == 2 {
        if let Some((e, f)) = ef(morceaux[1], morceaux[0]) {
            return Some(NomCube::Simple(e, f));
        }
    }
    if morceaux.len() == 3 {
        if let Some((e, f)) = ef(morceaux[1], morceaux[0]) {
            if nom_de_mere_valide(morceaux[2]) {
                return Some(NomCube::Sous(morceaux[2].to_string(), e, f));
            }
            return None;
        }
    }
    if nom_de_mere_valide(r) {
        return Some(NomCube::Mere(r.to_string()));
    }
    None
}

/// 0.64b : la marque du format des cubes mères à quatre étages, à l'étage Đ, au point #FFFFFD (« VTXMERE2 »)
pub const MARQUE_MERE: u64 = 0x5654_584D_4552_4532;

/// 0.63 : le cube mère NOM (TETE-NOM.cub, avec son anti-cube et son ombre) mis à jour après le rangement du sous-cube
/// (e, f). 0.64b : le cube mère porte ses quatre étages, comme ses sous-cubes : le descripteur de l'étage e du sous-cube
/// de fréquence f est à son étage e, à l'adresse #f, sur 64 bits (présent, 512, plus ses pages ; puis 54 bits de
/// coiffe, l'empreinte FNV-1a de son fichier) ; sur Lugus, la moitié haute du point porte l'indicatif (FNV-1a du nom).
/// À l'étage Đ : la marque du format en #FFFFFD, la coiffe en #FFFFFE (le brassage de tous les points), la queue en
/// #FFFFFF (l'indicatif en haut sur Lugus, le nombre de descripteurs). Une page du fichier dit son étage (bits 8 et 9
/// de son numéro). Un cube mère d'avant (sans la marque) est refait. Aucune ancienne version n'est gardée.
/// large : Lugus (points de 128 bits), sinon Dunon (64)
pub fn mere_mettre_a_jour(dossier: &std::path::Path, tete: &str, nom: &str, e: usize, f: u64, pages: u64,
                          fichier: &[u8], large: bool) -> std::io::Result<()> {
    let entete: &[u8; 8] = if large { b"VTXCU128" } else { b"VTXCUB64" };
    let ws = if large { 16 } else { 8 };
    let taille = 4 + 65536 * ws + 16384;
    let chemin = dossier.join(format!("{}-{}.cub", tete, nom));
    // les points, par (étage << 24) | adresse
    let mut points: std::collections::BTreeMap<u64, u128> = std::collections::BTreeMap::new();
    if let Some(b) = crate::miroir::lire_double(&chemin, entete) {
        if b.len() >= 8 && &b[..8] == entete {
            let mut k = 8;
            while k + taille <= b.len() {
                let hp = u32::from_le_bytes(b[k..k + 4].try_into().unwrap()) as u64;
                let base = (((hp >> 8) & 3) << 24) | ((hp & 255) << 16);
                for j in 0..65536usize {
                    let o = k + 4 + ws * j;
                    let v = if large {
                        u128::from_le_bytes(b[o..o + 16].try_into().unwrap())
                    } else {
                        u64::from_le_bytes(b[o..o + 8].try_into().unwrap()) as u128
                    };
                    if v != 0 {
                        points.insert(base | j as u64, v);
                    }
                }
                k += taille;
            }
        }
    }
    if points.get(&0xFF_FFFD).map(|v| *v as u64) != Some(MARQUE_MERE) {
        points.clear();
    }
    points.remove(&0xFF_FFFE);
    points.remove(&0xFF_FFFF);
    let indicatif = fnv64_texte(nom) as u128;
    let lo = (0x200 | (pages & 0x1FF)) | ((fnv64_octets(fichier) & ((1u64 << 54) - 1)) << 10);
    points.insert(((e as u64) << 24) | f, if large { (indicatif << 64) | lo as u128 } else { lo as u128 });
    points.insert(0xFF_FFFD, MARQUE_MERE as u128);
    let (mut somme, mut ou) = (0u64, 0u64);
    for (p, w) in &points {
        let g = brasser64(brasser64(brasser64(*p) ^ (*w >> 64) as u64) ^ *w as u64);
        somme = somme.wrapping_add(g);
        ou ^= g;
    }
    // le nombre de descripteurs (la marque n'en est pas un)
    let n = points.len() as u64 - 1;
    let coiffe = brasser64(brasser64(brasser64(n) ^ somme) ^ ou);
    points.insert(0xFF_FFFE, coiffe as u128);
    points.insert(0xFF_FFFF, if large { (indicatif << 64) | n as u128 } else { n as u128 });
    let mut sortie: Vec<u8> = entete.to_vec();
    let mut pages_de: Vec<u64> = points.keys().map(|p| p >> 16).collect();
    pages_de.dedup();
    for pg in pages_de {
        // le numéro de la page : son étage en bits 8 et 9, sa page dans l'étage en bits 0 à 7
        sortie.extend_from_slice(&((((pg >> 8) & 3) << 8 | (pg & 255)) as u32).to_le_bytes());
        for j in 0..65536u64 {
            let v = points.get(&((pg << 16) | j)).copied().unwrap_or(0);
            if large {
                sortie.extend_from_slice(&v.to_le_bytes());
            } else {
                sortie.extend_from_slice(&(v as u64).to_le_bytes());
            }
        }
        sortie.extend(std::iter::repeat(0u8).take(16384));
    }
    crate::miroir::ecrire_double(&chemin, &sortie)
}

/// 0.64 : les points d'un cube sur disque (relu par son miroir) : {place : point} des points non nuls ; None : absent
pub fn lire_points(chemin: &std::path::Path, large: bool) -> Option<std::collections::BTreeMap<u64, u128>> {
    let entete: &[u8; 8] = if large { b"VTXCU128" } else { b"VTXCUB64" };
    let ws = if large { 16 } else { 8 };
    let taille = 4 + 65536 * ws + 16384;
    let b = crate::miroir::lire_double(chemin, entete)?;
    if b.len() < 8 || &b[..8] != entete {
        return None;
    }
    let mut points = std::collections::BTreeMap::new();
    let mut k = 8;
    while k + taille <= b.len() {
        let p = (u32::from_le_bytes(b[k..k + 4].try_into().unwrap()) & 255) as u64;
        for j in 0..65536usize {
            let o = k + 4 + ws * j;
            let v = if large {
                u128::from_le_bytes(b[o..o + 16].try_into().unwrap())
            } else {
                u64::from_le_bytes(b[o..o + 8].try_into().unwrap()) as u128
            };
            if v != 0 {
                points.insert((p << 16) | j as u64, v);
            }
        }
        k += taille;
    }
    Some(points)
}

/// 0.64 : le cube d'un programme, lu pour ses faces : le code (l'étage Đ), les trois axes (étages 1, 2, 3 : la face
/// d'un côté dans la moitié basse du point, la face opposée dans la haute), l'état de la lecture (2 vrai, 1 faux : réparé)
pub struct CubeProgramme {
    pub code: std::collections::BTreeMap<u64, u128>,
    pub axes: [std::collections::BTreeMap<u64, u128>; 3],
    pub etat: u128,
}

impl CubeProgramme {
    /// le cube NOM (un sous-cube : « cube128-NOM-Đ-F.cub » et ses faces « cube128-NOM-1-F.cub »… ; sans nom, un cube
    /// simple « cube128-Đ-F.cub ») ; None s'il n'a pas de faces
    pub fn ouvrir(dossier: &std::path::Path, nom: Option<&str>, f: u64, etat: u128) -> Option<CubeProgramme> {
        let fichier = |e: usize| match nom {
            Some(m) => dossier.join(format!("cube128-{}-{}-{}.cub", m, lettre_etage(e), f)),
            None => dossier.join(format!("cube128-{}-{}.cub", lettre_etage(e), f)),
        };
        let avant = crate::miroir::prendre_etat();
        let code = lire_points(&fichier(0), true)?;
        let mut axes = [std::collections::BTreeMap::new(), std::collections::BTreeMap::new(), std::collections::BTreeMap::new()];
        for e in 1..=3 {
            axes[e - 1] = lire_points(&fichier(e), true)?;
        }
        // les faces réparées à cette lecture (faux), ou dont les copies se contredisent (variable), l'emportent
        let lu = crate::miroir::prendre_etat() as u128;
        crate::miroir::noter(avant);
        let etat = if lu == 3 { 3 } else if lu == 1 { 1 } else { etat };
        Some(CubeProgramme { code, axes, etat })
    }

    /// le nombre de mots de la molécule qui commence à la place p (sa face « ce qu'elle est »), 0 si elle n'est pas connue
    pub fn mots_de(&self, p: u64) -> u64 {
        ((self.axes[0].get(&p).copied().unwrap_or(0) as u64) >> 4) & 0xFF_FFFF
    }

    /// la face k (0 à 5 : ce qu'elle est, ce qu'elle touche, ses racines, ses branches, ses promesses, sa mémoire) de la
    /// molécule à la place p ; k = 6 : son centre (0 inconnu : pas de faces ; 3 variable : son code n'est plus celui du
    /// cube ; sinon l'état de la lecture du cube) ; lus : les mots qui tournent, à ses places
    pub fn face(&self, k: u64, p: u64, lus: &[u128]) -> u128 {
        if k < 6 {
            let w = self.axes[(k / 2) as usize].get(&p).copied().unwrap_or(0);
            return if k % 2 == 0 { w & 0xFFFF_FFFF_FFFF_FFFF } else { w >> 64 };
        }
        if k != 6 || p == 0xFF_FFFE || p == 0xFF_FFFF || !self.axes[0].contains_key(&p) {
            return 0;
        }
        let n = self.mots_de(p);
        for j in 0..n {
            if lus.get(j as usize).copied() != Some(self.code.get(&(p + j)).copied().unwrap_or(0)) {
                return 3;
            }
        }
        self.etat
    }
}
