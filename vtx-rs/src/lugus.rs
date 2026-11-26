// lugus : Lugus, la machine SPU-128 (spécification : docs/specification-spu128.md).
//   lugus corpus FICHIER            une ligne « mots;entrées » par programme -> « pas|sorties|mémoire|B:brins|T:texte »
//   lugus lancer FICHIER.mots [ENTRÉES…]   lance un programme (mots de 128 bits en décimal, séparés par des virgules)
//   lugus PROG.vtx [ENTRÉES…]       compile avec vtxc128 (embarqué) puis exécute : ni Python ni étape .mots
//   lugus compiler PROG.vtx [SORTIE.mots]   écrit seulement les mots
//   lugus renouveler vtxc128.vtx    vtxc128 se recompile lui-même ; point fixe exigé avant d'écrire vtxc128.mots
//   lugus ranger PROG.vtx [PROG.adn]        compile et range l'ADN : les mots et leurs trois témoins
//   lugus transcrire PROG.adn [PROG.mots]   vérifie et répare l'ADN, retire les témoins : les mots (l'ARN)
//   lugus PROG.adn [ENTRÉES…] [--veille]   vérifie et répare l'ADN ; l'épissage retire les témoins : l'ARN (les mots
//                                   seuls) est lancé ; la patrouille veille avec --veille, ou si le programme a des isotopes
//                                   lourds (LUGUS_PATROUILLE=0 l'éteint, =1 l'arme)
//   lugus transcrire PROG.adn PROG.arn   l'ARN : l'ARNc (0.66 : il porte tout ; les isoformes épissées ne s'écrivent
//                                   plus, les anciens ARN se lisent toujours)
//   lugus PROG.arn [ENTRÉES…] [--veille | --rapide]   vérifie la coiffe, lance ; --rapide : les mots seuls (ni témoins,
//                                   ni patrouille, ni souvenirs), ce que faisait l'ARN rapide
//   lugus relire PROG.adn [RELU.adn]      la même lecture, faite par le lecteur d'ADN écrit en vtx (chimie/adn.vtx,
//                                   embarqué) : le compte rendu, puis l'ADN relu (réparé) s'il est demandé
//   lugus apprendre PROG.adn [ENTRÉES…]   lance, puis garde les souvenirs dans l'ADN (l'épigénome) : relancé, il les reprend
//   lugus oublier PROG.adn          retire l'épigénome
//   lugus eprouver PROG.adn [ENTRÉES…]  l'épreuve : lancé avec ses vérifications ; passée, elle est notée dans l'ADN
//   lugus PROG.adn --rapide         (0.70 : les vérifications de t[i] sont faites par la machine : rien à retirer)
//   lugus pourquoi PROG.adn …       la même chose, depuis le texte gardé dans l'ADN (s'il redonne ses mots)
//   lugus pourquoi PROG.vtx [LIAISON | RÉACTION.LIAISON] [ENTRÉES…]   la provenance : d'où vient chaque valeur
//   lugus cataloguer DOSSIER        le catalogue des modules du dossier (catalogue.vtxcat : nom, empreinte, molécules et
//                                   leur vibration), écrit par le lecteur en vtx (0.62) ; « importer empreinte "…"; » y cherche
//   lugus morceaux PROG.vtx         les morceaux du programme et leur vibration (comme python3 chimie/adn.py morceaux)
#[allow(dead_code)]
mod qflot128;
#[allow(dead_code)]
mod spu128;
#[allow(dead_code)]
mod hote;
#[allow(dead_code)]
mod miroir;
#[allow(dead_code)]
mod machine128;
#[allow(dead_code)]
mod adn;
#[allow(dead_code)]
mod provenance;
#[allow(dead_code)]
mod gif;
#[allow(dead_code)]
mod sortie;
/// 0.67 : un message de Lugus (sur la sortie des erreurs), gardé pour le glossaire de la fin
macro_rules! dire {
    ($($a:tt)*) => {{
        let __s = format!($($a)*);
        eprintln!("{}", __s);
        crate::hote::glossaire_noter(&__s);
    }};
}

/// 0.67 : finir, après le glossaire des mots parus dans les messages
fn sortir(code: i32) -> ! {
    crate::hote::glossaire_dire();
    std::process::exit(code)
}

use machine128::{compiler128, compiler128_prov, dossier_de128, nombres128, COMPILATEUR128, COMPLET128, VTXC128};
use spu128::Spu128;

fn compiler_ou_sortir(compilateur: &[u128], fichier: &str, mode: machine128::Mode128) -> Vec<u128> {
    let source = match std::fs::read_to_string(fichier) {
        Ok(t) => t,
        Err(e) => {
            dire!("lecture de {} impossible : {}", fichier, e);
            sortir(1);
        }
    };
    match compiler128(compilateur, &source, &dossier_de128(fichier), mode, false) {
        Ok((m, _, _)) => m,
        Err(e) => {
            eprint!("{}", e);
            sortir(1);
        }
    }
}

fn ecrire_mots(chemin: &str, mots: &[u128]) {
    let t = mots.iter().map(|v| v.to_string()).collect::<Vec<_>>().join(",") + ";\n";
    if let Err(e) = std::fs::write(chemin, t) {
        dire!("écriture de {} impossible : {}", chemin, e);
        sortir(1);
    }
}

// ------------------------------------------------------------------------------------------------ l'épigénome
// Les souvenirs des atomes lourds (des fonctions pures : pour les mêmes entrées, toujours le même résultat) sont rangés
// dans @3[#1000000..#1FFFFFF]. Après une exécution, « lugus apprendre » les garde dans l'ADN (l'intron « epigenome ») :
// le programme relancé repart avec ce qu'il a appris. Ils sont liés à la signature des mots (un autre programme, même
// d'une lettre, ne les reprend pas) et ont la leur : un épigénome abîmé est oublié, jamais lu de travers.
const SOUV_DEBUT: u128 = 0x100_0000;
const SOUV_FIN: u128 = 0x200_0000;

fn souvenirs_de(spu: &Spu128) -> Vec<(u128, u128)> {
    let mut v = Vec::new();
    for (base, mots) in spu.pages_etage(3) {
        if base + mots.len() as u128 <= SOUV_DEBUT || base >= SOUV_FIN {
            continue;
        }
        for (k, &w) in mots.iter().enumerate() {
            let a = base + k as u128;
            if w != 0 && (SOUV_DEBUT..SOUV_FIN).contains(&a) {
                v.push((a, w));
            }
        }
    }
    v
}

fn signature_souvenirs(v: &[(u128, u128)]) -> u64 {
    let plat: Vec<u128> = v.iter().flat_map(|&(a, w)| [a, w]).collect();
    adn::signature(&plat)
}

fn intron_epigenome(mots: &[u128], v: &[(u128, u128)]) -> Vec<String> {
    let mut l = vec![format!("cle|{}|{}", adn::signature(mots), signature_souvenirs(v))];
    l.extend(v.iter().map(|(a, w)| format!("{}:{}", a, w)));
    l
}

/// les souvenirs de l'épigénome, s'il est de ce programme et intact ; sinon None, avec la raison
fn lire_epigenome(t: &adn::Temoins, mots: &[u128]) -> Result<Option<Vec<(u128, u128)>>, String> {
    let l = match t.intron("epigenome") {
        Some(l) => l,
        None => return Ok(None),
    };
    let tete: Vec<&str> = l.first().map(|x| x.split('|').collect()).unwrap_or_default();
    if tete.len() != 3 || tete[0] != "cle" {
        return Err("l'épigénome est illisible : oublié".into());
    }
    if tete[1] != adn::signature(mots).to_string() {
        return Err("l'épigénome est celui d'un autre programme : oublié".into());
    }
    let mut v = Vec::new();
    for x in &l[1..] {
        let p = x.split_once(':').and_then(|(a, w)| Some((a.parse::<u128>().ok()?, w.parse::<u128>().ok()?)));
        match p {
            Some((a, w)) if (SOUV_DEBUT..SOUV_FIN).contains(&a) => v.push((a, w)),
            _ => return Err("l'épigénome est abîmé : oublié".into()),
        }
    }
    if tete[2] != signature_souvenirs(&v).to_string() {
        return Err("l'épigénome est abîmé : oublié".into());
    }
    Ok(Some(v))
}

fn reprendre_epigenome(spu: &mut Spu128, t: &adn::Temoins, mots: &[u128]) -> usize {
    match lire_epigenome(t, mots) {
        Ok(Some(v)) => {
            for &(a, w) in &v {
                let _ = spu.ecrire_mem((3u128 << 126) | a, w);
            }
            dire!("l'épigénome : {} mots de souvenirs repris", v.len());
            v.len()
        }
        Ok(None) => 0,
        Err(e) => {
            dire!("{}", e);
            0
        }
    }
}

/// 0.68 : le titre de la fenêtre d'un programme : le nom du fichier lancé
fn titre_fenetre() -> String {
    std::env::args().nth(1).unwrap_or_default()
}

/// 0.68 : le service 12 (presenter) de Lugus lancé seul : l'image de l'étage 1 (ecran(l, h)) vers la fenêtre
fn presenter_lugus(s: &Spu128) -> u128 {
    let (l, h) = (s.regarder((3u128 << 62) | 14_680_058), s.regarder((3u128 << 62) | 14_680_059));
    if !((1..=4096).contains(&l) && (1..=4096).contains(&h) && l * h <= 1 << 24) {
        return u64::MAX as u128;
    }
    let (l, h) = (l as usize, h as usize);
    let px: Vec<u32> = (0..l * h).map(|i| {
        let v = s.regarder((1u128 << 62) | i as u128);
        if v >> 64 == 0 {
            (((v >> 56) & 0xFF) << 16 | ((v >> 40) & 0xFF) << 8 | ((v >> 24) & 0xFF)) as u32
        } else {
            (((v >> 120) & 0xFF) << 16 | ((v >> 88) & 0xFF) << 8 | ((v >> 56) & 0xFF)) as u32
        }
    }).collect();
    if sortie::montrer(l, h, &px) { 0 } else { 1 }
}

/// 0.64 : le cube du programme lancé depuis son cube (ses faces), donné à la machine qui le joue
static CUBE_LANCE: std::sync::Mutex<Option<crate::hote::CubeProgramme>> = std::sync::Mutex::new(None);

fn jouer(mots: &[u128], entrees: &[String], dossier: Option<std::path::PathBuf>) {
    jouer_avec(mots, entrees, dossier, None, None);
}

// ------------------------------------------------------------------------------------------------ la patrouille
/// LUGUS_AVARIE=PAS:MOT:BIT[,…] : des avaries posées pendant l'exécution (un bit du code retourné au pas donné), pour
/// essayer la patrouille
fn poser_avaries(spu: &mut Spu128) {
    if let Ok(v) = std::env::var("LUGUS_AVARIE") {
        let mut a: Vec<(u64, u128, u32)> = v.split(',').filter_map(|x| {
            let c: Vec<&str> = x.split(':').collect();
            if c.len() == 3 { Some((c[0].parse().ok()?, c[1].parse().ok()?, c[2].parse().ok()?)) } else { None }
        }).collect();
        a.sort();
        spu.avaries = a.into();
    }
}

/// la patrouille branchée sur la machine : elle relit le code contre ses témoins pendant l'exécution
fn armer_patrouille(spu: &mut Spu128, mots: &[u128], mols: Vec<adn::Molecule>, t: adn::Temoins)
                    -> std::rc::Rc<std::cell::RefCell<adn::Patrouille>> {
    let p = std::rc::Rc::new(std::cell::RefCell::new(adn::Patrouille::nouvelle(mots, mols, t)));
    spu.controles = p.borrow().controles().iter().map(|&(d, f)| (d as u128, f as u128)).collect();
    let q = p.clone();
    spu.patrouille = Some(Box::new(move |spu: &mut Spu128, ronde: spu128::Ronde| {
        let mut pat = q.borrow_mut();
        let pas = spu.pas;
        let change = {
            let lire = |i: usize| spu.regarder(i as u128);
            match ronde {
                spu128::Ronde::Tic => pat.tic(&lire, pas),
                spu128::Ronde::Image => pat.ronde(&lire, pas),
                spu128::Ronde::Effet => {
                    pat.effet(&lire, pas)?;
                    false
                }
                spu128::Ronde::Entree(d) => pat.entree(d as usize, &lire),
                spu128::Ronde::Sortie(d) => {
                    pat.sortie(d as usize, &lire, pas)?;
                    false
                }
            }
        };
        if change {
            let ecrire = {
                let lire = |i: usize| spu.regarder(i as u128);
                pat.reparer(&lire, pas)?
            };
            for (i, w) in ecrire {
                spu.poser_code(i as u128, w);
            }
        }
        if let spu128::Ronde::Entree(d) = ronde {
            pat.entrer(d as usize);
        }
        Ok(())
    }));
    p
}

/// Un caractère lu au clavier (UTF-8) ; u128::MAX à la fin de l'entrée.
fn lire_car_clavier() -> u128 {
    use std::io::Read;
    let mut entree = std::io::stdin().lock();
    let mut o = [0u8; 4];
    if entree.read(&mut o[..1]).unwrap_or(0) == 0 {
        return u128::MAX;
    }
    let n = match o[0] {
        0x00..=0x7F => 1,
        0xC0..=0xDF => 2,
        0xE0..=0xEF => 3,
        _ => 4,
    };
    for k in 1..n {
        if entree.read(&mut o[k..k + 1]).unwrap_or(0) == 0 {
            return u128::MAX;
        }
    }
    std::str::from_utf8(&o[..n]).ok().and_then(|t| t.chars().next()).map(|c| c as u128).unwrap_or(0xFFFD)
}

/// Le clavier (0.6i) : ce que le programme lit vient de l'entrée, comme dans l'exécutable de Lugus et sur Dunon.
/// Devant quelqu'un (l'entrée et la sortie sont un terminal), ce qu'il écrit paraît aussitôt, pour que la question
/// se lise avant la réponse ; sinon la sortie reste rendue à la fin, comme avant. VTX_SANS_CLAVIER=1 : pas de
/// clavier du tout (toute lecture est la fin de l'entrée), pour les vérifications lancées depuis une console.
fn brancher_clavier(spu: &mut Spu128) {
    use std::io::IsTerminal;
    if std::env::var("VTX_SANS_CLAVIER").is_ok() {
        return;
    }
    spu.console_lire = Some(Box::new(|| {
        use std::io::Write;
        let _ = std::io::stdout().flush();
        lire_car_clavier()
    }));
    if std::io::stdin().is_terminal() && std::io::stdout().is_terminal() {
        spu.console_ecrire = Some(Box::new(|v: u128| {
            use std::io::Write;
            let mut o = std::io::stdout();
            if let Some(c) = char::from_u32((v & 0x1F_FFFF) as u32) {
                let _ = write!(o, "{}", c);
            }
            if v == 10 {
                let _ = o.flush();
            }
        }));
    }
}

/// lance ; avec un ADN, l'épigénome est d'abord repris, et la patrouille veille si elle est armée ; rend la
/// machine (pour apprendre)
fn jouer_avec(mots: &[u128], entrees: &[String], dossier: Option<std::path::PathBuf>, t: Option<&adn::Temoins>,
              veille: Option<(Vec<adn::Molecule>, adn::Temoins)>) -> Spu128 {
    let mut spu = Spu128::nouveau();
    spu.dossier = dossier;
    spu.cube_programme = CUBE_LANCE.lock().unwrap().take();
    // 0.68 : un programme qui dessine (ecran, pixel, presenter) ouvre sa fenêtre, comme un programme fini (Windows) ;
    // ailleurs, presenter() rend 0 sans rien montrer, comme avant
    // (la fenêtre s'ouvre pour quelqu'un : la console, ou VTX_FENETRE=1 ; lu par un tube, comme dans les tests, le
    // programme ne l'ouvre pas, VTX_FENETRE=0 non plus)
    let fenetre_voulue = {
        use std::io::IsTerminal;
        match std::env::var("VTX_FENETRE").ok().as_deref() {
            Some("0") => false,
            Some("1") => true,
            _ => std::io::stdout().is_terminal(),
        }
    };
    if fenetre_voulue {
        if let Some(f) = sortie::fenetre(&titre_fenetre()) {
            sortie::installer(Some(f));
            spu.presenter = Some(Box::new(presenter_lugus));
        }
    }
    spu.charger(mots);
    if let Some(t) = t {
        reprendre_epigenome(&mut spu, t, mots);
    }
    poser_avaries(&mut spu);
    // la patrouille est éteinte par défaut : elle veille si on le demande (--veille, LUGUS_PATROUILLE=1) ou si le
    // programme a des isotopes lourds (« -> a lourd » : c'est ainsi qu'on écrit « cette fonction doit être sûre ») ;
    // LUGUS_PATROUILLE=0 l'éteint toujours
    let demandee = entrees.iter().any(|a| a == "--veille");
    let patrouille = match veille {
        Some((mols, tv)) => {
            let reglage = std::env::var("LUGUS_PATROUILLE").ok();
            let armee = match reglage.as_deref() {
                Some("0") => false,
                Some("1") => true,
                _ => demandee || mols.iter().any(|m| m.isotope),
            };
            if armee { Some(armer_patrouille(&mut spu, mots, mols, tv)) } else { None }
        }
        None => {
            if demandee {
                dire!("--veille : sans témoins (un .vtx, ou un ARN rapide ou mémoire), la patrouille ne peut pas veiller");
            }
            None
        }
    };
    spu.entree.extend(entrees.iter().filter(|a| *a != "--veille").filter_map(|x| x.parse::<u128>().ok()));
    brancher_clavier(&mut spu);
    let debut = std::time::Instant::now();
    let r = spu.executer(u64::MAX);
    let duree = debut.elapsed();
    if !spu.sortie.is_empty() {
        println!("{}", spu.sortie.iter().map(|v| v.to_string()).collect::<Vec<_>>().join(","));
    }
    let t: String = spu.texte.iter().filter_map(|&v| char::from_u32((v & 0x1F_FFFF) as u32)).collect();
    print!("{}", t);
    if std::env::var("LUGUS_TEMPS").is_ok() {
        dire!("{} instructions en {:.3} s", spu.pas, duree.as_secs_f64());
    }
    if let Some(p) = &patrouille {
        let p = p.borrow();
        for x in &p.reparations {
            dire!("la patrouille, {}", x);
        }
        if std::env::var("LUGUS_TEMPS").is_ok() || !p.reparations.is_empty() {
            dire!("la patrouille : {} relecture(s), {} réparation(s)", p.relues, p.reparations.len());
        }
    }
    if let Err(e) = r {
        dire!("erreur : {}", e);
        sortie::finir();
        sortir(1);
    }
    // 0.68 : la fenêtre du programme reste ouverte jusqu'à ce qu'on la ferme (s'il en a ouvert une)
    sortie::finir();
    spu
}

fn lire_nombres(t: &str) -> Vec<u128> {
    t.split(|c: char| c == ',' || c.is_whitespace()).filter(|x| !x.is_empty()).map(|x| x.parse::<u128>().unwrap_or(0)).collect()
}

fn main() {
    lugus();
    crate::hote::glossaire_dire();
}

fn lugus() {
    spu128::garde_plantage();
    let args: Vec<String> = std::env::args().collect();
    if args.len() >= 3 && args[1] == "corpus" {
        let texte = std::fs::read_to_string(&args[2]).expect("fichier du corpus illisible");
        let mut sortie = String::new();
        for ligne in texte.lines() {
            let ligne = ligne.trim();
            if ligne.is_empty() {
                continue;
            }
            let (m, e) = ligne.split_once(';').unwrap_or((ligne, ""));
            let mut spu = Spu128::nouveau();
            spu.charger(&lire_nombres(m));
            spu.entree.extend(lire_nombres(e));
            match spu.executer(50_000_000) {
                Ok(()) => sortie.push_str(&spu.ligne_corpus()),
                Err(x) => {
                    sortie.push_str("ERREUR ");
                    sortie.push_str(&x);
                }
            }
            sortie.push('\n');
        }
        print!("{}", sortie);
    } else if args.len() >= 3 && args[1] == "druide" {
        // 0.846 : les conseils du Druide (le même dialogue que dans Ogmios)
        print!("{}", crate::machine128::druide_texte(std::path::Path::new(&args[2]), "\n"));
    } else if args.len() >= 3 && args[1] == "lancer" {
        let texte = std::fs::read_to_string(&args[2]).expect("programme illisible");
        let mots = lire_nombres(texte.split(';').next().unwrap_or(""));
        let mut spu = Spu128::nouveau();
        spu.dossier = std::path::Path::new(&args[2]).parent().map(|p| p.to_path_buf());
        spu.charger(&mots);
        spu.entree.extend(args[3..].iter().filter_map(|x| x.parse::<u128>().ok()));
        let debut = std::time::Instant::now();
        let r = spu.executer(u64::MAX);
        let duree = debut.elapsed();
        if !spu.sortie.is_empty() {
            println!("{}", spu.sortie.iter().map(|v| v.to_string()).collect::<Vec<_>>().join(","));
        }
        let t: String = spu.texte.iter().filter_map(|&v| char::from_u32((v & 0x1F_FFFF) as u32)).collect();
        print!("{}", t);
        if std::env::var("LUGUS_TEMPS").is_ok() {
            dire!("{} instructions en {:.3} s", spu.pas, duree.as_secs_f64());
        }
        if let Err(e) = r {
            dire!("erreur : {}", e);
            sortir(1);
        }
    } else if args.len() >= 3 && args[1] == "compiler" {
        let mots = compiler_ou_sortir(&nombres128(VTXC128), &args[2], COMPLET128);
        let sortie = if args.len() > 3 { args[3].clone() } else { std::path::Path::new(&args[2]).with_extension("mots").to_string_lossy().into_owned() };
        ecrire_mots(&sortie, &mots);
        println!("{} mots de Lugus -> {}", mots.len(), sortie);
    } else if args.len() >= 3 && args[1] == "renouveler" {
        // vtxc128 se compile lui-même deux fois : les deux résultats doivent être les mêmes (point fixe)
        let m1 = compiler_ou_sortir(&nombres128(VTXC128), &args[2], COMPILATEUR128);
        let m2 = compiler_ou_sortir(&m1, &args[2], COMPILATEUR128);
        if m1 != m2 {
            dire!("pas de point fixe : vtxc128.mots n'est pas renouvelé");
            sortir(1);
        }
        let chemin = std::path::Path::new(&args[2]).with_extension("mots");
        ecrire_mots(&chemin.to_string_lossy(), &m1);
        println!("point fixe : {} mots -> {}", m1.len(), chemin.display());
    } else if args.len() >= 3 && (args[1] == "retrotranscrire" || (args[1] == "ranger" && !args[2].ends_with(".vtx"))) {
        // 0.6n bis : ranger un brin qui n'est pas un texte (des mots, un hex, un cube, un ARN : la rétrotranscription,
        // ARN → ADN) ; tout est fait par le lecteur d'ADN écrit en vtx. L'ADN d'un ARN (l'ADNc) ne prend pas le nom de
        // l'ADN d'origine : NOM-c.adn
        let p = std::path::Path::new(&args[2]);
        let sortie = if args.len() > 3 { args[3].clone() } else if args[2].ends_with(".arn") {
            p.with_file_name(format!("{}-c.adn", p.file_stem().map(|x| x.to_string_lossy().into_owned()).unwrap_or_default()))
                .to_string_lossy().into_owned()
        } else { p.with_extension("adn").to_string_lossy().into_owned() };
        let entrees = vec![machine128::chemin_absolu(&args[2]), machine128::chemin_absolu(&sortie), "ranger".into()];
        let etat = machine128::adn_en_vtx_dans(&entrees, Some(&machine128::dossier_absolu(&args[2]))).unwrap_or_else(|e| {
            dire!("{}", e);
            sortir(1)
        });
        sortir(if etat == adn::VRAI { 0 } else { 1 });
    } else if args.len() >= 3 && args[1] == "empreinte" {
        // 0.61 : l'empreinte d'un module, à écrire après « importer "x.vtx" empreinte "…"; » (FNV-1a de 64 bits sur les
        // caractères, les retours chariot sautés : le calcul de vtx128.py et vtxc128)
        for f in &args[2..] {
            match std::fs::read(f) {
                Ok(o) => {
                    let mut h: u64 = 0xCBF29CE484222325;
                    for ch in String::from_utf8_lossy(&o).chars() {
                        if ch != '\r' {
                            h = (h ^ ch as u64).wrapping_mul(0x100000001B3);
                        }
                    }
                    println!("{:016x}  {}", h, f);
                }
                Err(e) => {
                    dire!("{} : {}", f, e);
                    sortir(1);
                }
            }
        }
    } else if args.len() >= 3 && args[1] == "cataloguer" {
        // 0.62 : le catalogue des modules d'un dossier (DOSSIER/catalogue.vtxcat : leur nom, leur empreinte, leurs
        // molécules et leur vibration), écrit par le lecteur en vtx ; chaque module compilé par vtxc128 (service 27)
        let d = std::fs::canonicalize(&args[2]).unwrap_or_else(|e| {
            dire!("{} : {}", args[2], e);
            sortir(1)
        });
        let ds = d.to_string_lossy().trim_start_matches(r"\\?\").to_string();
        let entrees = vec![ds.clone(), String::new(), "cataloguer".into()];
        let etat = machine128::adn_en_vtx_dans(&entrees, Some(std::path::Path::new(&ds))).unwrap_or_else(|e| {
            dire!("{}", e);
            sortir(1)
        });
        sortir(if etat == adn::VRAI { 0 } else { 1 });
    } else if args.len() >= 3 && args[1] == "morceaux" {
        // 0.62 : les morceaux d'un programme et leur vibration (la même liste que « python3 chimie/adn.py morceaux »)
        let source = std::fs::read_to_string(&args[2]).unwrap_or_else(|e| {
            dire!("lecture de {} impossible : {}", args[2], e);
            sortir(1)
        });
        let (mots, _, _) = machine128::compiler128_carte(&nombres128(VTXC128), &source, &dossier_de128(&args[2]), COMPLET128)
            .unwrap_or_else(|e| {
                eprint!("{}", e);
                sortir(1)
            });
        let travail = std::env::temp_dir().join(format!("vtx-morceaux-{}", std::process::id()));
        let _ = std::fs::create_dir_all(&travail);
        let f = travail.join("code.mots");
        let _ = std::fs::write(&f, format!("{};\n", mots.iter().map(|w| w.to_string()).collect::<Vec<_>>().join(",")));
        let entrees = vec![f.to_string_lossy().into_owned(), String::new(), "morceaux".into()];
        let etat = machine128::adn_en_vtx_dans(&entrees, Some(&travail)).unwrap_or_else(|e| {
            dire!("{}", e);
            sortir(1)
        });
        let _ = std::fs::remove_dir_all(&travail);
        sortir(if etat == adn::VRAI { 0 } else { 1 });
    } else if args.len() >= 3 && args[1] == "carte" {
        // 0.6p : la carte du programme (ce qu'est chaque molécule, ce qu'elle touche, ses racines, ses promesses), lue
        // par le lecteur en vtx dans un ADN ou un ARN ; d'un .vtx, l'ARNc est fait d'abord, à part, puis lu
        let tout = args.iter().any(|a| a == "--tout");
        let mut brin = args[2].clone();
        let travail = std::env::temp_dir().join(format!("vtx-carte-{}", std::process::id()));
        if brin.ends_with(".vtx") {
            let _ = std::fs::create_dir_all(&travail);
            let a = travail.join(std::path::Path::new(&brin).with_extension("arn").file_name().unwrap_or_default());
            let moi = std::env::current_exe().unwrap_or_else(|_| "lugus".into());
            let r = std::process::Command::new(moi).args(["arnc", &brin, &a.to_string_lossy()]).output();
            match r {
                Ok(o) if o.status.success() => brin = a.to_string_lossy().into_owned(),
                Ok(o) => {
                    eprint!("{}", String::from_utf8_lossy(&o.stderr));
                    sortir(1)
                }
                Err(e) => {
                    dire!("{}", e);
                    sortir(1)
                }
            }
        }
        // 0.62 : les catalogues où la carte cherche d'où vient chaque molécule (ceux que « importer empreinte » lit)
        let mut entrees = vec![machine128::chemin_absolu(&brin), if tout { "--tout".into() } else { String::new() }, "carte".into()];
        entrees.extend(catalogues_de(&machine128::dossier_absolu(&args[2])));
        let etat = machine128::adn_en_vtx_dans(&entrees, Some(&machine128::dossier_absolu(&brin))).unwrap_or_else(|e| {
            dire!("{}", e);
            sortir(1)
        });
        let _ = std::fs::remove_dir_all(&travail);
        sortir(if etat == adn::VRAI || etat == adn::FAUX { 0 } else { 1 });
    } else if args.len() >= 3 && (args[1] == "hex" || args[1] == "cube") {
        // 0.6n bis : le chemin dans l'autre sens, ADN (ou ARN, mots, hex, cube) → Hex → Cube, par le lecteur en vtx
        let (sortie, freq) = if args[1] == "hex" {
            (if args.len() > 3 { args[3].clone() } else { std::path::Path::new(&args[2]).with_extension("hex").to_string_lossy().into_owned() },
             String::new())
        } else {
            (String::new(), args.get(3).cloned().unwrap_or_default())
        };
        // 0.63 : le cube d'un programme est un sous-cube de son cube mère, nommé comme le programme
        let mere = if args[1] == "cube" { mere_de(&args[2]) } else { String::new() };
        let entrees = vec![machine128::chemin_absolu(&args[2]),
                           if sortie.is_empty() { String::new() } else { machine128::chemin_absolu(&sortie) },
                           args[1].clone(), freq, mere];
        let etat = machine128::adn_en_vtx_dans(&entrees, Some(&machine128::dossier_absolu(&args[2]))).unwrap_or_else(|e| {
            dire!("{}", e);
            sortir(1)
        });
        sortir(if etat == adn::VRAI || etat == adn::FAUX { 0 } else { 1 });
    } else if args.len() >= 3 && (args[1] == "ranger" || args[1] == "arnc") {
        // 0.6o : « arnc » : le programme naît en ARN (l'ARNc : coiffe, témoins, texte), sans fichier d'ADN
        // 0.6n : le rangement est fait par le lecteur d'ADN écrit en vtx (chimie/adn.vtx) ; Lugus ne fait que compiler
        // (par vtxc128, lui aussi en vtx) et lui passer les fichiers
        let source = std::fs::read_to_string(&args[2]).unwrap_or_else(|e| {
            dire!("lecture de {} impossible : {}", args[2], e);
            sortir(1)
        });
        let (mots, isotopes, carte) = machine128::compiler128_carte(&nombres128(VTXC128), &source, &dossier_de128(&args[2]), COMPLET128)
            .unwrap_or_else(|e| {
                eprint!("{}", e);
                sortir(1)
            });
        let arnc = args[1] == "arnc";
        let sortie = if args.len() > 3 { args[3].clone() } else { std::path::Path::new(&args[2]).with_extension(if arnc { "arn" } else { "adn" }).to_string_lossy().into_owned() };
        let etat = machine128::ranger_par_le_lecteur(&args[1], &mots, &isotopes, &carte, &args[2], &sortie).unwrap_or_else(|e| {
            dire!("{}", e);
            sortir(1)
        });
        sortir(if etat == adn::VRAI { 0 } else { 1 });
    } else if args.len() >= 3 && args[1] == "pourquoi" {
        // d'un .adn : le texte qu'il garde, s'il redonne bien ses mots (la rétrotranscription)
        let source = if args[2].ends_with(".adn") {
            let (mots_adn, _, t) = adn::transcrire(&args[2], false).unwrap_or_else(|e| {
                dire!("{}", e);
                sortir(1)
            });
            let (e, quoi) = machine128::retrotranscrire(&t, &mots_adn, &dossier_de128(&args[2]));
            if e != adn::VRAI {
                dire!("le texte : {}, {}", adn::nom_etat(e).split(' ').next().unwrap_or(""), quoi);
                sortir(1);
            }
            t.intron("source").map(|l| l.join("\n")).unwrap_or_default()
        } else {
            std::fs::read_to_string(&args[2]).unwrap_or_else(|e| {
                dire!("lecture de {} impossible : {}", args[2], e);
                sortir(1)
            })
        };
        let (mots, _, _, prov) = match compiler128_prov(&nombres128(VTXC128), &source, &dossier_de128(&args[2]), COMPLET128, false, true) {
            Ok(r) => r,
            Err(e) => {
                eprint!("{}", e);
                sortir(1);
            }
        };
        let quoi = args.get(3).filter(|x| x.parse::<i128>().is_err()).cloned();
        let entrees = &args[if quoi.is_some() { 4 } else { 3 }.min(args.len())..];
        let mut spu = Spu128::nouveau();
        spu.dossier = std::path::Path::new(&args[2]).parent().map(|p| p.to_path_buf());
        spu.charger(&mots);
        spu.entree.extend(entrees.iter().filter_map(|x| x.parse::<u128>().ok()));
        let r = spu.executer(u64::MAX);
        if !spu.sortie.is_empty() {
            println!("sorties : {}", spu.sortie.iter().map(|v| v.to_string()).collect::<Vec<_>>().join(", "));
        }
        let t: String = spu.texte.iter().filter_map(|&v| char::from_u32((v & 0x1F_FFFF) as u32)).collect();
        if !t.is_empty() {
            println!("texte : {}", t.trim_end_matches('\n').replace('\n', " / "));
        }
        if let Err(e) = r {
            dire!("erreur : {}", e);
        }
        let reactions = provenance::lire(&prov);
        let memoire = provenance::cases(&reactions, |a| spu.lire((3u128 << 62) | a as u128));
        let lire = |a: u64| *memoire.get(&a).unwrap_or(&0);
        println!("{}", provenance::pourquoi(&reactions, quoi.as_deref(), &lire));
    } else if args.len() >= 3 && args[1] == "eprouver" {
        // 0.69c : l'épreuve : le programme tourne avec ses vérifications (t[i] dans ses bornes) ; s'il va au bout sans en
        // déclencher, l'ADN le note (l'intron « epreuve », la signature de ses mots) : l'épissage rapide est permis
        let (mots, _, t0) = adn::transcrire(&args[2], false).unwrap_or_else(|e| {
            dire!("{}", e);
            sortir(1)
        });
        if t0.intron("source").is_none() {
            dire!("{} ne garde pas son texte : l'épissage rapide le recompile sans vérifications, il en a besoin", args[2]);
            sortir(1);
        }
        let mols = adn::lire_adn(&args[2]).map(|x| x.1).unwrap_or_default();
        let dossier = std::path::Path::new(&args[2]).parent().map(|p| p.to_path_buf());
        // une erreur (un t[i] hors du tableau) arrête Lugus ici : rien n'est noté
        jouer_avec(&mots, &args[3..], dossier, Some(&t0), None);
        let mut t = t0.clone();
        t.introns.retain(|(n, _)| n != "epreuve");
        t.introns.push(("epreuve".into(), vec![adn::signature(&mots).to_string()]));
        if let Err(e) = adn::ecrire_adn(&args[2], &mots, &mols, &t) {
            dire!("écriture de {} impossible : {}", args[2], e);
            sortir(1);
        }
        dire!("l'épreuve est passée : aucun t[i] n'est sorti de son tableau (avec ces entrées-là) ; notée dans {}",
              args[2]);
    } else if args.len() >= 3 && (args[1] == "apprendre" || args[1] == "oublier") {
        // apprendre : lancer, puis garder les souvenirs dans l'ADN (l'épigénome) ; oublier : les retirer
        // l'ADN est d'abord vérifié (et réparé, réécrit) ; l'épigénome d'avant est repris pour apprendre encore
        let (mots, _, t0) = adn::transcrire(&args[2], false).unwrap_or_else(|e| {
            dire!("{}", e);
            sortir(1)
        });
        let mols = adn::lire_adn(&args[2]).map(|x| x.1).unwrap_or_default();
        let mut t = t0.clone();
        t.introns.retain(|(n, _)| n != "epigenome");
        let mut n = 0;
        if args[1] == "apprendre" {
            let dossier = std::path::Path::new(&args[2]).parent().map(|p| p.to_path_buf());
            let spu = jouer_avec(&mots, &args[3..], dossier, Some(&t0), None);
            let v = souvenirs_de(&spu);
            n = v.len();
            if !v.is_empty() {
                t.introns.push(("epigenome".into(), intron_epigenome(&mots, &v)));
            }
        }
        if let Err(e) = adn::ecrire_adn(&args[2], &mots, &mols, &t) {
            dire!("écriture de {} impossible : {}", args[2], e);
            sortir(1);
        }
        if args[1] == "apprendre" {
            dire!("l'épigénome : {} mots de souvenirs rangés dans {}", n, args[2]);
        } else {
            dire!("l'épigénome est oublié");
        }
    } else if args.len() >= 3 && args[1] == "relire" {
        // le lecteur d'ADN écrit en vtx : les chemins lui sont donnés en entrées (un caractère par entrée, terminés par 0)
        let mut entrees = vec![machine128::chemin_absolu(&args[2])];
        if let Some(x) = args.get(3) {
            entrees.push(machine128::chemin_absolu(x));
        }
        let etat = machine128::adn_en_vtx(&entrees).unwrap_or_else(|e| {
            dire!("{}", e);
            sortir(1)
        });
        sortir(if etat == adn::VRAI || etat == adn::FAUX { 0 } else { 1 });
    } else if args.len() >= 3 && args[1] == "transcrire" {
        // 0.6n : la transcription (vérifier, réparer, réécrire l'ADN réparé, écrire l'ARN) est faite par le lecteur d'ADN
        // écrit en vtx ; Lugus ne garde que la rétrotranscription, qui recompile le texte (par vtxc128) et compare
        let sortie = if args.len() > 3 && !args[3].starts_with("--") { args[3].clone() } else { std::path::Path::new(&args[2]).with_extension("mots").to_string_lossy().into_owned() };
        let isoforme = args.iter().position(|a| a == "--isoforme").and_then(|i| args.get(i + 1)).cloned();
        let sortie = if isoforme.is_some() && !sortie.ends_with(".arn") { std::path::Path::new(&args[2]).with_extension("arn").to_string_lossy().into_owned() } else { sortie };
        // 0.6n bis : la vérification du texte gardé aussi (le lecteur le donne au compilateur, vtxc128, sur une
        // machine fille, et compare les mots) ; la signature du compilateur d'aujourd'hui lui est passée
        let entrees = vec![machine128::chemin_absolu(&args[2]), machine128::chemin_absolu(&sortie), "transcrire".into(),
                           isoforme.unwrap_or_default(), machine128::signature_compilateur().to_string()];
        let etat = machine128::adn_en_vtx_dans(&entrees, Some(&machine128::dossier_absolu(&args[2]))).unwrap_or_else(|e| {
            dire!("{}", e);
            sortir(1)
        });
        if etat != adn::VRAI && etat != adn::FAUX {
            sortir(1);
        }
    } else if args.len() >= 2 && args[1].ends_with(".adn") {
        // l'ADN est vérifié et réparé avant de tourner : seul un ADN vrai ou réparé est lancé
        match adn::transcrire(&args[1], false) {
            Ok((mots, _, t)) => {
                let dossier = std::path::Path::new(&args[1]).parent().map(|p| p.to_path_buf());
                // 0.70 : les vérifications de t[i] sont faites par la machine (LDT, STT) en une instruction, plus vite
                // que l'ancienne lecture sans vérification : l'épissage rapide n'a plus rien à retirer
                if args[2..].iter().any(|a| a == "--rapide") {
                    dire!("--rapide : les vérifications de t[i] sont faites par la machine elle-même (LDT, STT), en une \
                           instruction, plus vite que sans elles : il n'y a plus rien à retirer");
                    let entrees: Vec<String> = args[2..].iter().filter(|a| *a != "--rapide").cloned().collect();
                    let mols = adn::lire_adn(&args[1]).map(|x| x.1).unwrap_or_default();
                    jouer_avec(&mots, &entrees, dossier, Some(&t), Some((mols, t.clone())));
                    return;
                }
                let mols = adn::lire_adn(&args[1]).map(|x| x.1).unwrap_or_default();
                let veille = Some((mols, t.clone()));
                jouer_avec(&mots, &args[2..], dossier, Some(&t), veille);
            }
            Err(e) => {
                dire!("{}", e);
                sortir(1);
            }
        }
    } else if args.len() >= 2 && (args[1].ends_with(".hex") || args[1].ends_with(".cub")) {
        // 0.6n bis : un hex ou un cube se lance aussi ; le lecteur en vtx le lit (le cube : relu par son miroir, sa coiffe
        // vérifiée), puis Lugus joue ses mots
        let travail = std::env::temp_dir().join(format!("vtx-brin-{}.mots", std::process::id()));
        let entrees = vec![machine128::chemin_absolu(&args[1]), travail.to_string_lossy().into_owned(), "mots".into()];
        let etat = machine128::adn_en_vtx_dans(&entrees, Some(&machine128::dossier_absolu(&args[1]))).unwrap_or_else(|e| {
            dire!("{}", e);
            sortir(1)
        });
        let mots = std::fs::read_to_string(&travail).map(|t| nombres128(t.split(';').next().unwrap_or(""))).unwrap_or_default();
        let _ = std::fs::remove_file(&travail);
        if (etat != adn::VRAI && etat != adn::FAUX) || mots.is_empty() {
            sortir(1);
        }
        let dossier = std::path::Path::new(&args[1]).parent().map(|p| p.to_path_buf());
        // 0.64 : lancé depuis son cube, le programme lit ses faces (le service 31) : le code à l'étage Đ, les faces aux
        // étages 1 à 3 de la même fréquence
        if args[1].ends_with(".cub") {
            let lieu = match crate::hote::nom_de_cube(std::path::Path::new(&args[1]), "cube128") {
                Some(crate::hote::NomCube::Sous(n, _, f)) => Some((Some(n), f)),
                Some(crate::hote::NomCube::Mere(n)) => Some((Some(n), 440)),
                Some(crate::hote::NomCube::Simple(_, f)) => Some((None, f)),
                None => None,
            };
            if let Some((nom, f)) = lieu {
                let d = dossier.clone().filter(|d| !d.as_os_str().is_empty()).unwrap_or_else(|| std::path::PathBuf::from("."));
                let e = if etat == adn::FAUX { 1 } else { 2 };
                *CUBE_LANCE.lock().unwrap() = crate::hote::CubeProgramme::ouvrir(&d, nom.as_deref(), f, e);
            }
        }
        jouer(&mots, &args[2..], dossier);
    } else if args.len() >= 2 && args[1].ends_with(".arn") {
        // l'ARN : sa coiffe vérifiée (un ARN qui ne reconnaît pas ses mots n'est pas lancé)
        let mut arn = adn::lire_arn(&args[1]).unwrap_or_else(|e| {
            dire!("{}", e);
            sortir(1)
        });
        let dossier = std::path::Path::new(&args[1]).parent().map(|p| p.to_path_buf());
        // 0.66 : --rapide lance les mots seuls (ni témoins, ni patrouille, ni souvenirs) : ce que faisait l'ARN rapide
        if args[2..].iter().any(|a| a == "--rapide") {
            let entrees: Vec<String> = args[2..].iter().filter(|a| *a != "--rapide").cloned().collect();
            jouer_avec(&arn.mots, &entrees, dossier, None, None);
        } else {
            let epi = arn.epigenome.clone().map(|e| adn::Temoins { signatures: vec![], ombres: vec![], neutrons: Default::default(),
                                                                      introns: vec![("epigenome".into(), e)], version: 4 });
            jouer_avec(&arn.mots, &args[2..], dossier, epi.as_ref(), arn.temoins.take());
        }
    } else if args.len() >= 2 && args[1].ends_with(".vtx") {
        let mots = compiler_ou_sortir(&nombres128(VTXC128), &args[1], COMPLET128);
        let dossier = std::path::Path::new(&args[1]).parent().map(|p| p.to_path_buf());
        jouer(&mots, &args[2..], dossier);
    } else {
        dire!("utilisation : lugus PROG.vtx [ENTRÉES…] | lugus PROG.adn [ENTRÉES…] | lugus PROG.arn [ENTRÉES…] [--veille|--rapide] | lugus ranger PROG.vtx [PROG.adn] | lugus arnc PROG.vtx [PROG.arn] | lugus carte PROG.(vtx|adn|arn) [--tout] | lugus cataloguer DOSSIER | lugus morceaux PROG.vtx | lugus transcrire PROG.adn [PROG.mots|PROG.arn] | lugus retrotranscrire PROG.arn [PROG-c.adn] | lugus ranger PROG.(mots|hex|cub|arn) [PROG.adn] | lugus hex PROG.(adn|arn|mots|cub) [PROG.hex] | lugus cube PROG.(adn|arn|mots|hex) [FRÉQUENCE] | lugus PROG.hex | lugus cube128-[NOM-]Đ-F.cub | lugus cube128-NOM.cub | lugus apprendre PROG.adn [ENTRÉES…] | lugus oublier PROG.adn | lugus eprouver PROG.adn [ENTRÉES…] | lugus PROG.adn --rapide | lugus compiler PROG.vtx [SORTIE.mots] | lugus renouveler vtxc128.vtx | lugus corpus FICHIER | lugus lancer FICHIER.mots [ENTRÉES…] | lugus druide PROG.vtx");
        sortir(2);
    }
}

/// 0.62c : les cubes des catalogues d'un dossier (cube128-1-392.cub), dans l'ordre où « importer empreinte » les lit
/// (le dossier, bibliotheque/, ../bibliotheque/), ceux qui existent, chacun une fois
fn catalogues_de(d: &std::path::Path) -> Vec<String> {
    let mut r: Vec<String> = Vec::new();
    for c in ["cube128-1-392.cub", "bibliotheque/cube128-1-392.cub", "../bibliotheque/cube128-1-392.cub"] {
        if let Ok(x) = std::fs::canonicalize(d.join(c)) {
            let x = x.to_string_lossy().trim_start_matches(r"\\?\").to_string();
            if !r.contains(&x) {
                r.push(x);
            }
        }
    }
    r
}

/// 0.63 : le nom du cube mère d'un programme : celui du cube donné (sous-cube ou cube mère), sinon le nom de son fichier
/// (sans extension), ses caractères refusés changés en « _ »
fn mere_de(chemin: &str) -> String {
    let p = std::path::Path::new(chemin);
    match vtx_rs_hote_nom(p) {
        Some(n) => return n,
        None => {}
    }
    let tige = p.file_stem().map(|s| s.to_string_lossy().into_owned()).unwrap_or_default();
    let mut n: String = tige
        .chars()
        .map(|c| if crate::hote::car_de_mere_valide(c) { c } else { '_' })
        .take(64)
        .collect();
    n = n.trim_matches('-').to_string();
    if !crate::hote::nom_de_mere_valide(&n) {
        n.push('_');
    }
    if !crate::hote::nom_de_mere_valide(&n) {
        n = "programme".to_string();
    }
    n
}

fn vtx_rs_hote_nom(p: &std::path::Path) -> Option<String> {
    match crate::hote::nom_de_cube(p, "cube128")? {
        crate::hote::NomCube::Sous(n, _, _) | crate::hote::NomCube::Mere(n) => Some(n),
        crate::hote::NomCube::Simple(_, _) => None,
    }
}
