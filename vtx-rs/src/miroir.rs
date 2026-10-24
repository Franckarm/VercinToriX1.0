// Les cubes sur disque en miroir inversé (un RAID 1 dont la seconde copie est l'opposée de la première).
//
// À côté de chaque fichier de cube (cube-E-F.cub au SPU-32, cube64-E-F.cub au SPU-64) s'écrit son anti-cube
// (anticube-E-F.cub, anticube64-E-F.cub) : le même contenu, chaque octet après l'en-tête complémenté (« VTXCUB… »
// devient « VTXANT… »). Pourquoi l'opposé plutôt qu'une copie identique : une panne qui frappe les deux copies de la
// même façon (une page remise à zéro, un fichier tronqué au même endroit, une écriture folle) donnerait deux copies
// d'accord dans l'erreur ; avec l'opposé, l'accord parfait des deux est « tout à 1 », que de telles pannes cassent.
//
// Bit par bit, la paire (copie, anti-copie) est un quit de Belnap : (1, 0) et (0, 1) sont les deux valeurs sûres,
// (0, 0) l'absence (inconnu), (1, 1) la contradiction (variable). Pour un cube entier, la lecture rend :
//   vrai      les deux copies s'accordent ;
//   faux      une seule copie est lisible (l'autre manque, est abîmée ou tronquée) : le cube est réparé à partir
//             d'elle, et la copie abîmée réécrite ;
//   variable  les deux copies se contredisent : la première est gardée, la contradiction est signalée ;
//   inconnu   ni l'une ni l'autre.
// etat_disque() (service 22) rend le pire état vu depuis son dernier appel (inconnu < vrai < faux < variable).
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU8, Ordering};

pub const INCONNU: u8 = 0;
pub const FAUX: u8 = 1;
pub const VRAI: u8 = 2;
pub const VARIABLE: u8 = 3;

static ETAT: AtomicU8 = AtomicU8::new(INCONNU);

fn gravite(e: u8) -> u8 {
    match e {
        VRAI => 1,
        FAUX => 2,
        VARIABLE => 3,
        _ => 0,
    }
}

/// Retient un état de lecture (le plus grave l'emporte).
pub fn noter(e: u8) {
    let mut v = ETAT.load(Ordering::Relaxed);
    while gravite(e) > gravite(v) {
        match ETAT.compare_exchange(v, e, Ordering::Relaxed, Ordering::Relaxed) {
            Ok(_) => break,
            Err(x) => v = x,
        }
    }
}

/// Le service 22 : l'état depuis le dernier appel, puis inconnu.
pub fn prendre_etat() -> u8 {
    ETAT.swap(INCONNU, Ordering::Relaxed)
}

/// Le chemin de l'anti-cube : « anti » devant le nom du fichier.
pub fn chemin_anti(chemin: &Path) -> PathBuf {
    let nom = chemin.file_name().map(|n| n.to_string_lossy().into_owned()).unwrap_or_default();
    chemin.with_file_name(format!("anti{}", nom))
}

fn entete_anti(entete: &[u8]) -> Vec<u8> {
    let mut e = entete.to_vec();
    if e.len() >= 6 {
        e[3..6].copy_from_slice(b"ANT");
    }
    e
}

/// Écrit le cube (son en-tête de 8 octets, puis le corps) et son anti-cube.
pub fn ecrire_double(chemin: &Path, octets: &[u8]) -> std::io::Result<()> {
    std::fs::write(chemin, octets)?;
    let mut a = entete_anti(&octets[..8.min(octets.len())]);
    a.extend(octets.iter().skip(8).map(|b| !b));
    std::fs::write(chemin_anti(chemin), a)
}

/// Lit un cube et son anti-cube, les accorde (voir plus haut) et rend le contenu retenu (en-tête compris), ou None ; une
/// copie absente ou abîmée est réécrite à partir de l'autre.
pub fn lire_double(chemin: &Path, entete: &[u8]) -> Option<Vec<u8>> {
    let anti = chemin_anti(chemin);
    let p = std::fs::read(chemin).ok().filter(|b| b.len() >= 8 && &b[..8] == entete);
    let ea = entete_anti(entete);
    let a = std::fs::read(&anti).ok().filter(|b| b.len() >= 8 && b[..8] == ea[..]).map(|b| {
        let mut v = entete.to_vec();
        v.extend(b.iter().skip(8).map(|x| !x));
        v
    });
    let (garde, etat) = match (p, a) {
        (Some(p), Some(a)) => {
            if p == a {
                (p, VRAI)
            } else if a.len() > p.len() && a.starts_with(&p) {
                (a, FAUX) // la copie est tronquée : l'anti-copie la complète
            } else if p.len() > a.len() && p.starts_with(&a) {
                (p, FAUX)
            } else {
                (p, VARIABLE)
            }
        }
        (Some(p), None) => (p, FAUX),
        (None, Some(a)) => (a, FAUX),
        (None, None) => {
            noter(INCONNU);
            return None;
        }
    };
    if etat == FAUX {
        // la copie absente ou abîmée est refaite : les deux redeviennent l'une l'opposée de l'autre
        let _ = ecrire_double(chemin, &garde);
    }
    noter(etat);
    Some(garde)
}
