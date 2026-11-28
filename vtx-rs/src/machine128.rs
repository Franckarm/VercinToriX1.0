// Lugus (le SPU-128) avec son compilateur embarqué : vtxc128 (vtxc/vtxc128.vtx) déjà compilé, dans vtxc128.mots. Ce que
// font « lugus PROG.vtx » (compiler et lancer un programme sans Python) et Ogmios quand il travaille sur Lugus.
use crate::spu128::Spu128;

/// vtxc128 compilé (optimisé, sans prélude) : ses mots de 128 bits, en décimal séparés par des virgules.
pub const VTXC128: &str = include_str!("../vtxc128.mots");
/// le lecteur d'ADN écrit en vtx (chimie/adn.vtx), compilé par vtxc128 : `lugus compiler ../chimie/adn.vtx lecteur_adn.mots`
pub const LECTEUR_ADN: &str = include_str!("../lecteur_adn.mots");
/// 0.846 : le Druide conseiller (druide/conseiller.vtx), compilé par vtxc128 :
/// `lugus compiler ../druide/conseiller.vtx druide_conseiller.mots` (outils/druide.sh)
pub const DRUIDE_CONSEILLER: &str = include_str!("../druide_conseiller.mots");

/// 0.845 : le nemeton d'un programme (la mémoire de ses agents) : VTX_NEMETON/NOM, sinon ~/.vercintorix/nemeton/NOM
pub fn nemeton_de(programme: &std::path::Path) -> std::path::PathBuf {
    let nom = programme.file_stem().map(|n| n.to_string_lossy().into_owned()).unwrap_or_else(|| "programme".into());
    let base = match std::env::var_os("VTX_NEMETON") {
        Some(b) => std::path::PathBuf::from(b),
        None => std::path::PathBuf::from(std::env::var_os("USERPROFILE").or_else(|| std::env::var_os("HOME")).unwrap_or_default())
            .join(".vercintorix").join("nemeton"),
    };
    base.join(nom)
}

/// 0.846 : les conseils du Druide pour un programme, tels qu'il les dit (« conseil|ÉTAT|LIGNE|TEXTE|POTION »,
/// « savoir|AGENT|TEXTE », « fin|N ») : le conseiller écrit en vtx, joué sur une machine fille
pub fn druide_brut(programme: &std::path::Path) -> String {
    let chemin = std::fs::canonicalize(programme).unwrap_or_else(|_| programme.to_path_buf());
    let chemin = chemin.to_string_lossy().into_owned();
    let chemin = chemin.strip_prefix(r"\\?\").unwrap_or(&chemin).to_string();
    let nem = nemeton_de(programme).to_string_lossy().into_owned();
    let mut spu = Spu128::nouveau();
    spu.dossier = programme.parent().map(|d| d.to_path_buf());
    spu.charger(&nombres128(DRUIDE_CONSEILLER));
    for e in [chemin, nem] {
        spu.texte_entree.extend(e.chars().map(|ch| ch as u128));
        spu.texte_entree.push_back(10);
    }
    let _ = spu.executer(2_000_000_000);
    spu.texte.iter().filter_map(|&v| char::from_u32((v & 0x1F_FFFF) as u32)).collect()
}

/// le dialogue du Druide, en clair (pour la fenêtre des explications d'Ogmios et « lugus druide ») ; les potions
/// sont proposées, jamais posées sans le programmeur
pub fn druide_texte(programme: &std::path::Path, fin_de_ligne: &str) -> String {
    let brut = druide_brut(programme);
    let mut conseils = Vec::new();
    let mut savoirs = Vec::new();
    let mut lus = String::new();
    for l in brut.lines() {
        let m: Vec<&str> = l.splitn(5, '|').collect();
        if m.len() >= 4 && m[0] == "conseil" {
            let etat = match m[1] { "vrai" => "sûr", "inconnu" => "à vérifier", "variable" => "selon le cas", "faux" => "à corriger", x => x };
            // 0.848 : « LIGNE@FICHIER » pour un fichier importé
            let (ligne, fichier) = match m[2].split_once('@') { Some((l, f)) => (l, f), None => (m[2], "") };
            let ou = if fichier.is_empty() { format!("ligne {}", ligne) } else { format!("ligne {} de {}", ligne, fichier) };
            let mut t = format!("· {} ({}) : {}", ou, etat, m[3]);
            if m.len() >= 5 && !m[4].trim().is_empty() {
                t.push_str(&format!("{}    la potion : {}", fin_de_ligne, m[4].trim()));
            }
            conseils.push(((fichier.to_string(), ligne.parse::<usize>().unwrap_or(0)), t));
        } else if m.len() >= 2 && m[0] == "lus" {
            lus = m[1].to_string();
        } else if m.len() >= 3 && m[0] == "savoir" {
            savoirs.push(format!("· {} : {}", m[1], m[2]));
        }
    }
    let mut r = String::from("Le Druide :");
    r.push_str(fin_de_ligne);
    if !lus.is_empty() {
        r.push_str(&format!("(il a lu aussi ce que le programme importe : {})", lus));
        r.push_str(fin_de_ligne);
    }
    if conseils.is_empty() {
        r.push_str("je ne vois rien à redire.");
        r.push_str(fin_de_ligne);
    } else {
        conseils.sort_by(|a, b| a.0.cmp(&b.0));
        r.push_str(&conseils.iter().map(|c| c.1.clone()).collect::<Vec<_>>().join(fin_de_ligne));
        r.push_str(fin_de_ligne);
    }
    if !savoirs.is_empty() {
        r.push_str(fin_de_ligne);
        r.push_str("Ce que savent les agents de ce programme :");
        r.push_str(fin_de_ligne);
        r.push_str(&savoirs.join(fin_de_ligne));
        r.push_str(fin_de_ligne);
    }
    r
}

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
/// Le pas à pas d'Ogmios : sans partition (l'exécution reste en séquence, ligne après ligne).
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
    let (code, prov, ex, _, _, carte) = passer_vtxc128(compilateur, source, base, mode, lignes, provenance, false)?;
    if !ex.trim().is_empty() {
        rejouer_exemples(compilateur, source, base, mode, &ex)?;
    }
    let mut morceaux = code.split(';');
    let mots = nombres128(morceaux.next().unwrap_or(""));
    // 0.6r : les promesses « touche … », jugées sur les mots ordinaires (la trace et le pas à pas en ajoutent)
    if !lignes && !provenance && mode.prelude && mode.optim && mode.partition {
        juger_promesses(&mots, &carte, source)?;
    }
    let table = nombres128(morceaux.next().unwrap_or(""));
    let dbg = nombres128(morceaux.next().unwrap_or(""));
    Ok((mots, table, dbg, prov))
}

/// Compile pour le débogueur : les mots, la table des lignes, et code.sym (les fonctions et leurs variables, que
/// symboles.rs lit) ; les exemples sont rejoués comme pour compiler128.
pub fn compiler128_dbg(compilateur: &[u128], source: &str, base: &str, mode: Mode128)
                       -> Result<(Vec<u128>, Vec<u128>, String), String> {
    let (code, _, ex, _, sym, _) = passer_vtxc128(compilateur, source, base, mode, true, false, false)?;
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
    compiler128_carte(compilateur, source, base, mode).map(|(m, i, _)| (m, i))
}

/// les mots, les isotopes, et code.carte (0.6p : « nom|mot » pour chaque fonction gardée)
pub fn compiler128_carte(compilateur: &[u128], source: &str, base: &str, mode: Mode128)
                         -> Result<(Vec<u128>, Vec<(String, usize)>, String), String> {
    let (code, _, ex, iso, _, carte) = passer_vtxc128(compilateur, source, base, mode, false, false, false)?;
    if !ex.trim().is_empty() {
        rejouer_exemples(compilateur, source, base, mode, &ex)?;
    }
    let mots = nombres128(code.split(';').next().unwrap_or(""));
    if mode.prelude && mode.optim && mode.partition {
        juger_promesses(&mots, &carte, source)?;
    }
    let isotopes = iso.lines().filter_map(|l| {
        let (n, a) = l.trim_end_matches('\r').split_once('|')?;
        Some((n.to_string(), a.parse::<usize>().ok()?))
    }).collect();
    Ok((mots, isotopes, carte.replace('\r', "")))
}

/// La rétrotranscription : le texte gardé dans l'ADN (son intron « source »), recompilé par vtxc128, redonne-t-il les
/// mots ? (état de Belnap : vrai, faux pour un autre texte, inconnu sans texte ; et le message, comme chimie/adn.py)
pub fn retrotranscrire(t: &crate::adn::Temoins, mots: &[u128], base: &str) -> (u8, String) {
    let src = match t.intron("source") {
        Some(l) => l.join("\n"),
        None => return (crate::adn::INCONNU, "l'ADN ne garde pas de texte".into()),
    };
    // l'intron « compilateur » (0.6n) : si le compilateur a changé depuis le rangement, des mots qui ne reviennent pas
    // ne disent pas que le texte a été retouché : on ne sait pas (inconnu)
    let comp = t.intron("compilateur").and_then(|l| l.first().cloned());
    let change = comp.as_ref().map(|c| *c != signature_compilateur().to_string()).unwrap_or(false);
    let inconnu = || (crate::adn::INCONNU, "le compilateur a changé depuis le rangement : le texte ne peut pas être vérifié".to_string());
    match compiler128_iso(&nombres128(VTXC128), &src, base, COMPLET128) {
        Err(_) if change => inconnu(),
        Err(e) => (crate::adn::FAUX, format!("le texte gardé ne compile plus : {}", e.trim_end())),
        Ok((m2, _)) if m2 == mots => (crate::adn::VRAI, "le texte gardé redonne les mots, un pour un".into()),
        Ok(_) if change => inconnu(),
        Ok((m2, _)) => {
            let ecarts = m2.iter().zip(mots.iter()).filter(|(a, b)| a != b).count() + m2.len().abs_diff(mots.len());
            if comp.is_none() {
                (crate::adn::FAUX, format!("le texte gardé ne redonne pas ces mots ({} écart(s)) ; cet ADN ne note pas \
                                            son compilateur : il a pu changer depuis", ecarts))
            } else {
                (crate::adn::FAUX, format!("le texte gardé ne redonne pas ces mots ({} écart(s))", ecarts))
            }
        }
    }
}

/// la signature des mots du compilateur embarqué (vtxc128) : l'intron « compilateur » de l'ADN
pub fn signature_compilateur() -> u64 {
    // les mots jusqu'au « ; » (comme chimie/adn.py) : nombres128 lit « 10; » comme un 0
    crate::adn::signature(&nombres128(VTXC128.split(';').next().unwrap_or("")))
}

/// Le lecteur d'ADN écrit en vtx (chimie/adn.vtx) : ses entrées sont des textes (un caractère par entrée, chacun terminé
/// par 0). Rend l'état qu'il a sorti (2 vrai, 1 faux : réparé, 3 variable, 0 illisible) ; ce qu'il écrit va sur la
/// sortie d'erreur, comme le compte rendu de Lugus.
pub fn adn_en_vtx(entrees: &[String]) -> Result<u8, String> {
    adn_en_vtx_dans(entrees, None)
}

/// Le lecteur d'ADN dans un dossier : celui où il écrit et relit les cubes, et où le compilateur cherche les
/// importations du texte gardé (0.6n bis) ; « . » sinon.
pub fn adn_en_vtx_dans(entrees: &[String], dossier: Option<&std::path::Path>) -> Result<u8, String> {
    let (e, t) = adn_en_vtx_texte(entrees, dossier)?;
    eprint!("{}", t);
    crate::hote::glossaire_noter(&t);
    Ok(e)
}

/// un texte porte-t-il une promesse « touche … » (un en-tête de fonction ou de réaction, après sa dernière parenthèse) ?
pub fn a_des_promesses(source: &str) -> bool {
    // 0.6w : l'en-tête s'arrête à la première accolade (une fonction écrite sur une ligne garde son corps à côté)
    source.lines().any(|l| (l.starts_with("fonction ") || l.starts_with("reaction ")) && {
        let t = &l[..l.find('{').unwrap_or(l.len())];
        t.rfind(')').map(|i| t[i..].contains(" touche ")).unwrap_or(false)
    })
}

/// Les promesses jugées par le lecteur en vtx (0.6r) : Ok(les notes) si toutes sont tenues, Err(les messages) sinon.
/// Rien n'est lancé pour un texte sans promesse.
pub fn juger_promesses(mots: &[u128], carte: &str, source: &str) -> Result<String, String> {
    if !a_des_promesses(source) {
        return Ok(String::new());
    }
    let travail = std::env::temp_dir().join(format!("vtx-promesses-{}-{}", std::process::id(),
                                                     std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH)
                                                         .map(|d| d.as_nanos()).unwrap_or(0)));
    std::fs::create_dir_all(&travail).map_err(|e| e.to_string())?;
    let f_mots = travail.join("code.mots");
    let txt: Vec<String> = mots.iter().map(|w| w.to_string()).collect();
    let _ = std::fs::write(&f_mots, format!("{};\n", txt.join(",")));
    let f_carte = travail.join("code.carte");
    let _ = std::fs::write(&f_carte, carte);
    let f_src = travail.join("source.vtx");
    let _ = std::fs::write(&f_src, source);
    let entrees = vec![f_mots.to_string_lossy().into_owned(), f_carte.to_string_lossy().into_owned(), "promesses".into(),
                       f_src.to_string_lossy().into_owned()];
    let r = adn_en_vtx_texte(&entrees, None);
    let _ = std::fs::remove_dir_all(&travail);
    let (e, t) = r?;
    if e == crate::adn::VRAI {
        if !t.is_empty() {
            eprint!("{}", t);
    crate::hote::glossaire_noter(&t);
        }
        Ok(t)
    } else {
        Err(t)
    }
}

/// le lecteur d'ADN, ce qu'il écrit rendu au lieu d'être écrit
pub fn adn_en_vtx_texte(entrees: &[String], dossier: Option<&std::path::Path>) -> Result<(u8, String), String> {
    let mut spu = Spu128::nouveau();
    spu.dossier = Some(dossier.map(|d| d.to_path_buf()).unwrap_or_else(|| std::path::PathBuf::from(".")));
    spu.compilateur = Some(compiler_pour_lecteur);
    spu.charger(&nombres128(LECTEUR_ADN));
    for e in entrees {
        spu.entree.extend(e.chars().map(|ch| ch as u128));
        spu.entree.push_back(0);
    }
    let r = spu.executer(u64::MAX);
    let t: String = spu.texte.iter().filter_map(|&v| char::from_u32((v & 0x1F_FFFF) as u32)).collect();
    if let Err(e) = r {
        eprint!("{}", t);
    crate::hote::glossaire_noter(&t);
        return Err(format!("erreur : {}", e));
    }
    Ok((spu.sortie.last().copied().unwrap_or(0) as u8, t))
}

/// Ranger un programme compilé par le lecteur d'ADN écrit en vtx (0.6p) : les mots, les isotopes et les noms des
/// fonctions (code.carte) posés dans un dossier de travail, puis « ranger » (l'ADN) ou « arnc » (l'ARNc) ; le texte
/// est lu dans `source` (le fichier du programme). Rend l'état du lecteur.
pub fn ranger_par_le_lecteur(verbe: &str, mots: &[u128], isotopes: &[(String, usize)], carte: &str, source: &str,
                             sortie: &str) -> Result<u8, String> {
    let travail = std::env::temp_dir().join(format!("vtx-ranger-{}-{}", std::process::id(),
                                                     std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH)
                                                         .map(|d| d.as_nanos()).unwrap_or(0)));
    std::fs::create_dir_all(&travail).map_err(|e| e.to_string())?;
    let f_mots = travail.join("code.mots");
    let txt: Vec<String> = mots.iter().map(|w| w.to_string()).collect();
    std::fs::write(&f_mots, format!("{};\n", txt.join(","))).map_err(|e| e.to_string())?;
    let mut iso = isotopes.to_vec();
    iso.sort_by_key(|x| x.1);
    let f_iso = travail.join("code.iso");
    let _ = std::fs::write(&f_iso, iso.iter().map(|(n, a)| format!("{}|{}\n", n, a)).collect::<String>());
    let f_carte = travail.join("code.carte");
    let _ = std::fs::write(&f_carte, carte);
    let entrees = vec![f_mots.to_string_lossy().into_owned(), chemin_absolu(sortie), verbe.to_string(),
                       chemin_absolu(source),
                       if iso.is_empty() { String::new() } else { f_iso.to_string_lossy().into_owned() },
                       signature_compilateur().to_string(), f_carte.to_string_lossy().into_owned(),
                       // 0.6q : le brin rangé avant, pour la face de la mémoire (recopié : la sortie va être réécrite)
                       {
                           let f_avant = travail.join("avant");
                           if std::fs::copy(sortie, &f_avant).is_ok() { f_avant.to_string_lossy().into_owned() } else { String::new() }
                       }];
    let r = adn_en_vtx(&entrees);
    let _ = std::fs::remove_dir_all(&travail);
    r
}

/// Le service 27 du lecteur d'ADN : le texte compilé par vtxc128 (le compilateur de vtx, écrit en vtx, lancé sur une
/// machine fille), comme « lugus compiler » ; ses mots « a,b,c;\n », ou « ! » suivi de l'erreur.
pub fn compiler_pour_lecteur(source: &str, dossier: &std::path::Path) -> String {
    // le préfixe « \\?\ » des chemins canoniques de Windows est retiré : les importations se cherchent depuis ce dossier
    let base = dossier.to_string_lossy().into_owned();
    let base = base.strip_prefix(r"\\?\").unwrap_or(&base).to_string();
    // 0.6p : après les mots, les noms des fonctions (« nom|mot » par ligne) : la carte se refait et se compare
    match compiler128_carte(&nombres128(VTXC128), source, &base, COMPLET128) {
        Ok((m, _, carte)) => format!("{};\n{}", m.iter().map(|w| w.to_string()).collect::<Vec<_>>().join(","), carte),
        Err(e) => format!("!{}", e.trim_end()),
    }
}

/// le dossier d'un fichier, absolu (pour le lecteur d'ADN)
pub fn dossier_absolu(x: &str) -> std::path::PathBuf {
    std::path::Path::new(&chemin_absolu(x)).parent().map(|p| p.to_path_buf()).unwrap_or_else(|| std::path::PathBuf::from("."))
}

/// un chemin absolu (le lecteur en vtx ouvre les fichiers depuis son propre dossier)
pub fn chemin_absolu(x: &str) -> String {
    std::fs::canonicalize(std::path::Path::new(x).parent().filter(|p| !p.as_os_str().is_empty())
        .unwrap_or(std::path::Path::new(".")))
        .map(|d| d.join(std::path::Path::new(x).file_name().unwrap_or_default()))
        .unwrap_or_else(|_| std::path::PathBuf::from(x)).to_string_lossy().into_owned()
        .trim_start_matches(r"\\?\").to_string()
}

/// une passe de vtxc128 dans un dossier de travail : (code.mots, code.prov, code.ex, code.iso), ou les messages d'erreur
fn passer_vtxc128(compilateur: &[u128], source: &str, base: &str, mode: Mode128, lignes: bool, provenance: bool,
                  exemples: bool) -> Result<(String, String, String, String, String, String), String> {
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
    let carte = std::fs::read_to_string(dossier.join("code.carte")).unwrap_or_default();
    let _ = std::fs::remove_dir_all(&dossier);
    let messages: String = s.texte.iter().filter_map(|&v| char::from_u32((v & 0x1F_FFFF) as u32)).collect();
    if let Err(e) = r {
        return Err(format!("{}{}\n", messages, e));
    }
    match code {
        Ok(t) => Ok((t, prov, ex, iso, sym, carte)),
        Err(_) => Err(messages),
    }
}

/// 0.852 : la forge écrite en vtx : vtxc128 écrit aussi code.rs (l'entrée « rust », après les six drapeaux) ; rend les
/// mots (code.mots, la table des accords comprise) et le Rust des fonctions (ou ce qui manque : « // pas encore : … »)
pub fn passer_vtxc128_rust(compilateur: &[u128], source: &str, base: &str) -> Result<(String, String), String> {
    let dossier = std::env::temp_dir().join(format!("vtxc128-rs-{}-{}", std::process::id(),
                                                     std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH)
                                                         .map(|d| d.as_nanos()).unwrap_or(0)));
    std::fs::create_dir_all(&dossier).map_err(|e| e.to_string())?;
    std::fs::write(dossier.join("source.vtx"), source).map_err(|e| e.to_string())?;
    let mut s = Spu128::nouveau();
    s.dossier = Some(dossier.clone());
    s.charger(compilateur);
    s.entree.extend(base.chars().map(|c| c as u128));
    s.entree.push_back(0);
    for drapeau in [1u128, 1, 1, 0, 0, 0, 1] {
        s.entree.push_back(drapeau);
    }
    let r = s.executer(200_000_000_000);
    let code = std::fs::read_to_string(dossier.join("code.mots"));
    let rs = std::fs::read_to_string(dossier.join("code.rs"));
    let _ = std::fs::remove_dir_all(&dossier);
    let messages: String = s.texte.iter().filter_map(|&v| char::from_u32((v & 0x1F_FFFF) as u32)).collect();
    if let Err(e) = r {
        return Err(format!("{}{}\n", messages, e));
    }
    match (code, rs) {
        (Ok(m), Ok(r)) => Ok((m, r)),
        _ => Err(messages),
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
    let (code, _, _, _, _, _) = passer_vtxc128(compilateur, source, base, mode_ex, false, false, true)?;
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
