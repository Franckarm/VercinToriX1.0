// Lugus (le SPU-128) avec son compilateur embarqué : vtxc128 (vtxc/vtxc128.vtx) déjà compilé, dans vtxc128.mots. Ce que
// font « lugus PROG.vtx » (compiler et lancer un programme sans Python) et l'atelier quand il travaille sur Lugus.
use crate::spu128::Spu128;

/// vtxc128 compilé (optimisé, sans prélude) : ses mots de 128 bits, en décimal séparés par des virgules.
pub const VTXC128: &str = include_str!("../vtxc128.mots");

pub fn nombres128(s: &str) -> Vec<u128> {
    s.split(|c: char| c == ',' || c.is_whitespace()).filter(|x| !x.is_empty()).map(|x| x.parse::<u128>().unwrap_or(0)).collect()
}

/// Ce que vtxc128 fait : ajouter le prélude, optimiser, partitionner les tâches en accords.
#[derive(Clone, Copy)]
pub struct Mode128 {
    pub prelude: bool,
    pub optim: bool,
    pub partition: bool,
}

/// Un programme : prélude, optimisations, partition (comme vtx128.py par défaut).
pub const COMPLET128: Mode128 = Mode128 { prelude: true, optim: true, partition: true };
/// Le pas à pas de l'atelier : sans partition (l'exécution reste en séquence, ligne après ligne).
pub const PAS_A_PAS128: Mode128 = Mode128 { prelude: true, optim: true, partition: false };
/// vtxc128 lui-même : sans prélude (il a ses propres outils), optimisé, sans partition.
pub const COMPILATEUR128: Mode128 = Mode128 { prelude: false, optim: true, partition: false };

/// Fait tourner un compilateur (ses mots) sur un texte vtx ; rend les mots produits, la table des accords et, avec
/// lignes, la table du pas à pas, ou les messages d'erreur. vtxc128 lit « source.vtx » et écrit « code.mots » dans un
/// dossier de travail temporaire ; ses entrées : le dossier du programme (un caractère par entrée, puis 0), puis les
/// drapeaux.
pub fn compiler128(compilateur: &[u128], source: &str, base: &str, mode: Mode128, lignes: bool)
                   -> Result<(Vec<u128>, Vec<u128>, Vec<u128>), String> {
    let dossier = std::env::temp_dir().join(format!("vtxc128-{}-{}", std::process::id(),
                                                     std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH)
                                                         .map(|d| d.as_nanos()).unwrap_or(0)));
    std::fs::create_dir_all(&dossier).map_err(|e| e.to_string())?;
    std::fs::write(dossier.join("source.vtx"), source).map_err(|e| e.to_string())?;
    let mut s = Spu128::nouveau();
    s.dossier = Some(dossier.clone());
    s.charger(compilateur);
    s.entree.extend(base.chars().map(|c| c as u128));
    s.entree.push_back(0);
    for drapeau in [mode.prelude, mode.optim, mode.partition, lignes] {
        s.entree.push_back(if drapeau { 1 } else { 0 });
    }
    let r = s.executer(200_000_000_000);
    let code = std::fs::read_to_string(dossier.join("code.mots"));
    let _ = std::fs::remove_dir_all(&dossier);
    let messages: String = s.texte.iter().filter_map(|&v| char::from_u32((v & 0x1F_FFFF) as u32)).collect();
    if let Err(e) = r {
        return Err(format!("{}{}\n", messages, e));
    }
    match code {
        Ok(t) => {
            let mut morceaux = t.split(';');
            let mots = nombres128(morceaux.next().unwrap_or(""));
            let table = nombres128(morceaux.next().unwrap_or(""));
            let dbg = nombres128(morceaux.next().unwrap_or(""));
            Ok((mots, table, dbg))
        }
        Err(_) => Err(messages),
    }
}

/// Le dossier absolu d'un fichier (les fichiers importés sont cherchés à partir de lui).
pub fn dossier_de128(fichier: &str) -> String {
    let chemin = std::env::current_dir().unwrap_or_default().join(fichier);
    chemin.parent().map(|p| p.to_string_lossy().into_owned()).unwrap_or_default()
}
