// La machine SPU-64 avec son compilateur embarqué : vtxc64 (vtxc/vtxc64.vtx) déjà compilé, dans vtxc64.mots. Ce que
// font vtx64.exe (compiler et lancer un programme sans Python) et l'atelier quand il travaille en 64 bits.
use crate::spu64::Spu64;

/// vtxc64 compilé (optimisé, sans prélude) : ses mots, en décimal séparés par des virgules.
pub const VTXC64: &str = include_str!("../vtxc64.mots");

pub fn nombres64(s: &str) -> Vec<u64> {
    s.split(|c: char| c == ',' || c.is_whitespace()).filter(|x| !x.is_empty()).map(|x| x.parse::<u64>().unwrap_or(0)).collect()
}

/// Ce que vtxc64 fait : ajouter le prélude, optimiser, partitionner les tâches en accords.
#[derive(Clone, Copy)]
pub struct Mode64 {
    pub prelude: bool,
    pub optim: bool,
    pub partition: bool,
}

/// Un programme : prélude, optimisations, partition (comme vtx64.py par défaut).
pub const COMPLET64: Mode64 = Mode64 { prelude: true, optim: true, partition: true };
/// Le pas à pas de l'atelier : sans partition (l'exécution reste en séquence, ligne après ligne).
pub const PAS_A_PAS64: Mode64 = Mode64 { prelude: true, optim: true, partition: false };
/// vtxc64 lui-même : sans prélude (il a ses propres outils), optimisé, sans partition.
pub const COMPILATEUR64: Mode64 = Mode64 { prelude: false, optim: true, partition: false };

/// Fait tourner un compilateur (ses mots) sur un texte vtx ; rend les mots produits, la table des accords et, avec
/// lignes, la table du pas à pas (adresse, ligne, adresse, ligne…), ou les messages d'erreur. vtxc64 lit « source.vtx »
/// et écrit « code.mots » dans un dossier de travail temporaire ; ses entrées : le dossier du programme (un caractère
/// par entrée, puis 0), où il cherche les fichiers importés, puis les drapeaux.
pub fn compiler64(compilateur: &[u64], source: &str, base: &str, mode: Mode64, lignes: bool)
                  -> Result<(Vec<u64>, Vec<u64>, Vec<u64>), String> {
    let dossier = std::env::temp_dir().join(format!("vtxc64-{}-{}", std::process::id(),
                                                     std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH)
                                                         .map(|d| d.as_nanos()).unwrap_or(0)));
    std::fs::create_dir_all(&dossier).map_err(|e| e.to_string())?;
    std::fs::write(dossier.join("source.vtx"), source).map_err(|e| e.to_string())?;
    let mut s = Spu64::nouveau();
    s.dossier = Some(dossier.clone());
    s.charger(compilateur);
    s.entree.extend(base.chars().map(|c| c as u64));
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
            let mots = nombres64(morceaux.next().unwrap_or(""));
            let table = nombres64(morceaux.next().unwrap_or(""));
            let dbg = nombres64(morceaux.next().unwrap_or(""));
            Ok((mots, table, dbg))
        }
        Err(_) => Err(messages),
    }
}

/// Le dossier absolu d'un fichier (les fichiers importés sont cherchés à partir de lui).
pub fn dossier_de64(fichier: &str) -> String {
    let chemin = std::env::current_dir().unwrap_or_default().join(fichier);
    chemin.parent().map(|p| p.to_string_lossy().into_owned()).unwrap_or_default()
}

/// « erreur ligne N » devient « erreur FICHIER, ligne N » (l'éditeur retrouve l'endroit), et rend N.
pub fn situer_erreur(e: &str, fichier: &str) -> (String, Option<usize>) {
    let nom = std::path::Path::new(fichier).file_name().map(|n| n.to_string_lossy().into_owned()).unwrap_or_default();
    let ligne = e.find("erreur ligne ").and_then(|p| e[p + 13..].chars().take_while(|c| c.is_ascii_digit()).collect::<String>().parse().ok());
    (e.replace("erreur ligne ", &format!("erreur {}, ligne ", nom)), ligne)
}

/// Un caractère du clavier (UTF-8), ou 2^64 - 1 à la fin de l'entrée.
pub fn lire_car_clavier64() -> u64 {
    use std::io::Read;
    let mut entree = std::io::stdin().lock();
    let mut o = [0u8; 4];
    if entree.read(&mut o[..1]).unwrap_or(0) == 0 {
        return u64::MAX;
    }
    let n = match o[0] {
        0x00..=0x7F => 1,
        0xC0..=0xDF => 2,
        0xE0..=0xEF => 3,
        _ => 4,
    };
    for k in 1..n {
        if entree.read(&mut o[k..k + 1]).unwrap_or(0) == 0 {
            return u64::MAX;
        }
    }
    std::str::from_utf8(&o[..n]).ok().and_then(|s| s.chars().next()).map(|c| c as u64).unwrap_or(0xFFFD)
}

/// La console d'un programme lancé dans un terminal : ce qu'il écrit paraît aussitôt, ce qu'il lit vient du clavier.
pub fn brancher_terminal(s: &mut Spu64) {
    s.console_ecrire = Some(Box::new(|v: u64| {
        use std::io::Write;
        let mut o = std::io::stdout();
        if let Some(c) = char::from_u32((v & 0x1F_FFFF) as u32) {
            let _ = write!(o, "{}", c);
        }
        if v == 10 {
            let _ = o.flush();
        }
    }));
    s.console_lire = Some(Box::new(|| {
        use std::io::Write;
        let _ = std::io::stdout().flush();
        lire_car_clavier64()
    }));
}

/// Dire un texte à voix haute : la voix de Windows (System.Speech, en français si une voix française est installée) ;
/// ailleurs espeak-ng ou espeak s'il est là ; sinon rien. L'appel attend la fin de la phrase.
pub fn parler64(t: &str) {
    if t.trim().is_empty() {
        return;
    }
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        let script = "Add-Type -AssemblyName System.Speech; $v = New-Object System.Speech.Synthesis.SpeechSynthesizer; \
            try { $v.SelectVoiceByHints('NotSet', 'NotSet', 0, [Globalization.CultureInfo]'fr-FR') } catch {}; $v.Speak($env:VTX_VOIX)";
        let _ = std::process::Command::new("powershell").args(["-NoProfile", "-NonInteractive", "-Command", script])
            .env("VTX_VOIX", t).creation_flags(0x0800_0000).status();
    }
    #[cfg(not(windows))]
    {
        for prog in ["espeak-ng", "espeak"] {
            if std::process::Command::new(prog).args(["-v", "fr", t]).stdout(std::process::Stdio::null())
                .stderr(std::process::Stdio::null()).status().is_ok() {
                return;
            }
        }
    }
}

/// Un point profond #RRRRGGGGBBBBAAAA vu en point de 32 bits #RRGGBBAA (l'octet fort de chaque voie), pour les vues
/// du cube de l'atelier ; un petit nombre (moins de 2^32) reste tel quel, pour garder sa couleur de petit nombre.
pub fn vers_point32(v: u64) -> u32 {
    if v < 1 << 32 {
        return v as u32;
    }
    (((v >> 56) & 0xFF) << 24 | ((v >> 40) & 0xFF) << 16 | ((v >> 24) & 0xFF) << 8 | ((v >> 8) & 0xFF)) as u32
}
