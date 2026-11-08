// Lugus (le SPU-128) avec son compilateur embarqué : vtxc128 (vtxc/vtxc128.vtx) déjà compilé, dans vtxc128.mots. Ce que
// font « lugus PROG.vtx » (compiler et lancer un programme sans Python) et l'atelier quand il travaille sur Lugus.
use crate::spu128::Spu128;

/// vtxc128 compilé (optimisé, sans prélude) : ses mots de 128 bits, en décimal séparés par des virgules.
pub const VTXC128: &str = include_str!("../vtxc128.mots");
/// le lecteur d'ADN écrit en vtx (chimie/adn.vtx), compilé par vtxc128 : `lugus compiler ../chimie/adn.vtx lecteur_adn.mots`
pub const LECTEUR_ADN: &str = include_str!("../lecteur_adn.mots");

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
    compiler128_prov(compilateur, source, base, mode, lignes, false).map(|(m, t, d, _)| (m, t, d))
}

/// la même chose, avec la provenance au choix : chaque réaction range la trace de ses liaisons ; rend aussi code.prov.
/// Les exemples du programme (« exemple f(2) == 4 ») sont rejoués à chaque compilation, comme vtx128.py : vtxc128 écrit
/// code.ex, compile le programme des exemples (le même principal que vtx128.py), Lugus le fait tourner ; un exemple faux
/// arrête la compilation.
pub fn compiler128_prov(compilateur: &[u128], source: &str, base: &str, mode: Mode128, lignes: bool, provenance: bool)
                        -> Result<(Vec<u128>, Vec<u128>, Vec<u128>, String), String> {
    let (code, prov, ex, _, _) = passer_vtxc128(compilateur, source, base, mode, lignes, provenance, false)?;
    if !ex.trim().is_empty() {
        rejouer_exemples(compilateur, source, base, mode, &ex)?;
    }
    let mut morceaux = code.split(';');
    let mots = nombres128(morceaux.next().unwrap_or(""));
    let table = nombres128(morceaux.next().unwrap_or(""));
    let dbg = nombres128(morceaux.next().unwrap_or(""));
    Ok((mots, table, dbg, prov))
}

/// Compile pour le débogueur : les mots, la table des lignes, et code.sym (les fonctions et leurs variables, que
/// symboles.rs lit) ; les exemples sont rejoués comme pour compiler128.
pub fn compiler128_dbg(compilateur: &[u128], source: &str, base: &str, mode: Mode128)
                       -> Result<(Vec<u128>, Vec<u128>, String), String> {
    let (code, _, ex, _, sym) = passer_vtxc128(compilateur, source, base, mode, true, false, false)?;
    if !ex.trim().is_empty() {
        rejouer_exemples(compilateur, source, base, mode, &ex)?;
    }
    let mut morceaux = code.split(';');
    let mots = nombres128(morceaux.next().unwrap_or(""));
    let _table = morceaux.next();
    let dbg = nombres128(morceaux.next().unwrap_or(""));
    Ok((mots, dbg, sym))
}

/// Compile pour l'ADN : les mots (exemples rejoués) et les isotopes lourds, (réaction, place de son premier mot), que
/// vtxc128 écrit dans code.iso pour les réactions qui portent un atome lourd (« -> a lourd »).
pub fn compiler128_iso(compilateur: &[u128], source: &str, base: &str, mode: Mode128)
                       -> Result<(Vec<u128>, Vec<(String, usize)>), String> {
    let (code, _, ex, iso, _) = passer_vtxc128(compilateur, source, base, mode, false, false, false)?;
    if !ex.trim().is_empty() {
        rejouer_exemples(compilateur, source, base, mode, &ex)?;
    }
    let mots = nombres128(code.split(';').next().unwrap_or(""));
    let isotopes = iso.lines().filter_map(|l| {
        let (n, a) = l.trim_end_matches('\r').split_once('|')?;
        Some((n.to_string(), a.parse::<usize>().ok()?))
    }).collect();
    Ok((mots, isotopes))
}

/// La rétrotranscription : le texte gardé dans l'ADN (son intron « source »), recompilé par vtxc128, redonne-t-il les
/// mots ? (état de Belnap : vrai, faux pour un autre texte, inconnu sans texte ; et le message, comme chimie/adn.py)
pub fn retrotranscrire(t: &crate::adn::Temoins, mots: &[u128], base: &str) -> (u8, String) {
    let src = match t.intron("source") {
        Some(l) => l.join("\n"),
        None => return (crate::adn::INCONNU, "l'ADN ne garde pas de texte".into()),
    };
    match compiler128_iso(&nombres128(VTXC128), &src, base, COMPLET128) {
        Err(e) => (crate::adn::FAUX, format!("le texte gardé ne compile plus : {}", e.trim_end())),
        Ok((m2, _)) if m2 == mots => (crate::adn::VRAI, "le texte gardé redonne les mots, un pour un".into()),
        Ok((m2, _)) => {
            let ecarts = m2.iter().zip(mots.iter()).filter(|(a, b)| a != b).count() + m2.len().abs_diff(mots.len());
            (crate::adn::FAUX, format!("le texte gardé ne redonne pas ces mots ({} écart(s))", ecarts))
        }
    }
}

/// une passe de vtxc128 dans un dossier de travail : (code.mots, code.prov, code.ex, code.iso), ou les messages d'erreur
fn passer_vtxc128(compilateur: &[u128], source: &str, base: &str, mode: Mode128, lignes: bool, provenance: bool,
                  exemples: bool) -> Result<(String, String, String, String, String), String> {
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
    for drapeau in [mode.prelude, mode.optim, mode.partition, lignes, provenance, exemples] {
        s.entree.push_back(if drapeau { 1 } else { 0 });
    }
    let r = s.executer(200_000_000_000);
    let code = std::fs::read_to_string(dossier.join("code.mots"));
    let prov = std::fs::read_to_string(dossier.join("code.prov")).unwrap_or_default();
    let ex = std::fs::read_to_string(dossier.join("code.ex")).unwrap_or_default();
    let iso = std::fs::read_to_string(dossier.join("code.iso")).unwrap_or_default();
    let sym = std::fs::read_to_string(dossier.join("code.sym")).unwrap_or_default();
    let _ = std::fs::remove_dir_all(&dossier);
    let messages: String = s.texte.iter().filter_map(|&v| char::from_u32((v & 0x1F_FFFF) as u32)).collect();
    if let Err(e) = r {
        return Err(format!("{}{}\n", messages, e));
    }
    match code {
        Ok(t) => Ok((t, prov, ex, iso, sym)),
        Err(_) => Err(messages),
    }
}

/// les exemples rejoués (comme verifier_exemples de vtx128.py) : chaque exemple sort 1 (vrai) ou 0, puis le programme
/// affiche ce que vaut le côté gauche d'une égalité
fn rejouer_exemples(compilateur: &[u128], source: &str, base: &str, mode: Mode128, ex: &str) -> Result<(), String> {
    let lus: Vec<(&str, bool, &str)> = ex.lines().filter_map(|l| {
        let c: Vec<&str> = l.trim_end_matches('\r').splitn(3, '|').collect();
        if c.len() == 3 { Some((c[0], c[1] == "1", c[2])) } else { None }
    }).collect();
    if lus.is_empty() {
        return Ok(());
    }
    let mode_ex = Mode128 { prelude: mode.prelude, optim: mode.optim, partition: false };
    let (code, _, _, _, _) = passer_vtxc128(compilateur, source, base, mode_ex, false, false, true)?;
    let mut m = Spu128::nouveau();
    m.charger(&nombres128(code.split(';').next().unwrap_or("")));
    if let Err(e) = m.executer(50_000_000) {
        return Err(format!("erreur ligne {} : les exemples n'ont pas pu être rejoués : {}\nvtxc : compilation arrêtée\n", lus[0].0, e));
    }
    let obtenus: String = m.texte.iter().filter_map(|&v| char::from_u32((v & 0x1F_FFFF) as u32)).collect();
    let obtenus: Vec<&str> = obtenus.split('\n').collect();
    for (k, (ligne, egalite, texte)) in lus.iter().enumerate() {
        if m.sortie.get(k) != Some(&1) {
            let detail = if *egalite { format!(" : le côté gauche vaut {}", obtenus.get(k).unwrap_or(&"?")) } else { String::new() };
            return Err(format!("erreur ligne {} : l'exemple « {} » est faux{}\nvtxc : compilation arrêtée\n", ligne, texte, detail));
        }
    }
    Ok(())
}

/// Le dossier absolu d'un fichier (les fichiers importés sont cherchés à partir de lui).
pub fn dossier_de128(fichier: &str) -> String {
    let chemin = std::env::current_dir().unwrap_or_default().join(fichier);
    chemin.parent().map(|p| p.to_string_lossy().into_owned()).unwrap_or_default()
}

/// La machine fille (le service 24 de Lugus) : un programme vtx compilé par vtxc128 (ses exemples rejoués) puis lancé
/// sur un Lugus neuf, à côté de celui qui le demande. Rend le compte rendu, en texte : ce que le programme a écrit, ses
/// sorties, puis le nombre de mots et d'instructions, ou l'erreur. C'est ainsi qu'Ogmios, écrit en vtx, lance F5.
pub fn machine_fille(chemin: &std::path::Path, max_pas: u64) -> String {
    let source = match std::fs::read_to_string(chemin) {
        Ok(t) => t,
        Err(e) => return format!("lecture de {} impossible : {}\n", chemin.display(), e),
    };
    let base = chemin.parent().map(|p| p.to_string_lossy().into_owned()).unwrap_or_default();
    let mots = match compiler128(&nombres128(VTXC128), &source, &base, COMPLET128, false) {
        Ok((m, _, _)) => m,
        Err(e) => return e,
    };
    let mut s = Spu128::nouveau();
    s.dossier = Some(std::path::PathBuf::from(&base));
    s.charger(&mots);
    let r = s.executer(max_pas);
    let mut t: String = s.texte.iter().filter_map(|&v| char::from_u32((v & 0x1F_FFFF) as u32)).collect();
    if !t.is_empty() && !t.ends_with('\n') {
        t.push('\n');
    }
    if !s.sortie.is_empty() {
        t += &format!("sorties : {}\n", s.sortie.iter().map(|v| v.to_string()).collect::<Vec<_>>().join(", "));
    }
    t += &format!("{} mots, {} instructions\n", mots.len(), s.pas);
    if let Err(e) = r {
        t += &format!("erreur : {}\n", e);
    }
    t
}

/// Les valeurs des liaisons, pour la paillasse : le programme compilé avec la provenance et lancé ; pour chaque
/// (réaction, liaison) sa dernière valeur écrite (avec son unité) et son état de Belnap : 2 vrai (arrivée), 1 faux (sa
/// branche n'a pas réagi), 0 inconnu (jamais calculée).
pub fn valeurs_liaisons(source: &str, base: &str, entrees: &[u128])
                        -> Result<std::collections::HashMap<(String, String), (String, u8)>, String> {
    use crate::provenance;
    let (mots, _, _, prov) = compiler128_prov(&nombres128(VTXC128), source, base, COMPLET128, false, true)?;
    let mut s = Spu128::nouveau();
    s.dossier = Some(std::path::PathBuf::from(base));
    s.charger(&mots);
    s.entree.extend(entrees.iter().copied());
    let fin = s.executer(2_000_000_000);
    let reactions = provenance::lire(&prov);
    let m = provenance::cases(&reactions, |a| s.lire((3u128 << 62) | a as u128));
    let lire = |a: u64| *m.get(&a).unwrap_or(&0);
    let mut vals = std::collections::HashMap::new();
    for r in &reactions {
        for (i, (nom, b, t)) in r.noms.iter().enumerate() {
            let (v, nb, la) = (lire(*b), lire(b + 1), lire(b + 2));
            let u = r.unites.get(i).cloned().unwrap_or_default();
            let texte = if u.is_empty() { provenance::valeur(v, *t) } else { format!("{} {}", provenance::valeur(v, *t), u) };
            let est_param = !r.atomes.iter().any(|a| a.sorties.iter().any(|s| s == nom));
            let etat = if est_param { if la != 0 { 2 } else { 0 } } else if nb == 0 { 0 } else if la == 0 { 1 } else if la == 3 { 3 } else { 2 };
            vals.insert((r.nom.clone(), nom.clone()), (texte, etat));
        }
    }
    if let Err(e) = fin {
        if vals.is_empty() {
            return Err(e);
        }
    }
    Ok(vals)
}
