// Ce que la machine hôte donne à un programme interactif, pareil sur le SPU-32 et le SPU-64 (services 16 à 21) :
// la souris dans l'image, les touches, l'horloge, la cadence des images. Une fenêtre (Gobatix ou l'atelier) écrit ici
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
// 16 ms : 60 images par seconde au plus, comme la fenêtre de Gobatix
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
            if vk >= 32 || matches!(vk, 8 | 9 | 13 | 27) {
                ajouter_touche(vk);
            }
        }
        _ => {}
    }
}

// ---- le scénario : des gestes écrits d'avance, rejoués image par image (vtx gobatix … --scenario FICHIER), pour montrer
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
