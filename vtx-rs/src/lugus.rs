// lugus : Lugus, la machine SPU-128 (spécification : docs/specification-spu128.md).
//   lugus corpus FICHIER            une ligne « mots;entrées » par programme -> « pas|sorties|mémoire|B:brins|T:texte »
//   lugus lancer FICHIER.mots [ENTRÉES…]   lance un programme (mots de 128 bits en décimal, séparés par des virgules)
//   lugus PROG.vtx [ENTRÉES…]       compile avec vtxc128 (embarqué) puis exécute : ni Python ni étape .mots
//   lugus compiler PROG.vtx [SORTIE.mots]   écrit seulement les mots
//   lugus renouveler vtxc128.vtx    vtxc128 se recompile lui-même ; point fixe exigé avant d'écrire vtxc128.mots
//   lugus ranger PROG.vtx [PROG.adn]        compile et range l'ADN : les mots et leurs trois témoins
//   lugus transcrire PROG.adn [PROG.mots]   vérifie et répare l'ADN, retire les témoins : les mots (l'ARN)
//   lugus PROG.adn [ENTRÉES…]       vérifie et répare l'ADN ; l'épissage retire les témoins : l'ARN (les mots seuls) est lancé
//   lugus pourquoi PROG.vtx [LIAISON | RÉACTION.LIAISON] [ENTRÉES…]   la provenance : d'où vient chaque valeur
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
use machine128::{compiler128, compiler128_prov, dossier_de128, nombres128, COMPILATEUR128, COMPLET128, VTXC128};
use spu128::Spu128;

fn compiler_ou_sortir(compilateur: &[u128], fichier: &str, mode: machine128::Mode128) -> Vec<u128> {
    let source = match std::fs::read_to_string(fichier) {
        Ok(t) => t,
        Err(e) => {
            eprintln!("lecture de {} impossible : {}", fichier, e);
            std::process::exit(1);
        }
    };
    match compiler128(compilateur, &source, &dossier_de128(fichier), mode, false) {
        Ok((m, _, _)) => m,
        Err(e) => {
            eprint!("{}", e);
            std::process::exit(1);
        }
    }
}

fn ecrire_mots(chemin: &str, mots: &[u128]) {
    let t = mots.iter().map(|v| v.to_string()).collect::<Vec<_>>().join(",") + ";\n";
    if let Err(e) = std::fs::write(chemin, t) {
        eprintln!("écriture de {} impossible : {}", chemin, e);
        std::process::exit(1);
    }
}

fn jouer(mots: &[u128], entrees: &[String], dossier: Option<std::path::PathBuf>) {
    let mut spu = Spu128::nouveau();
    spu.dossier = dossier;
    spu.charger(mots);
    spu.entree.extend(entrees.iter().filter_map(|x| x.parse::<u128>().ok()));
    let debut = std::time::Instant::now();
    let r = spu.executer(u64::MAX);
    let duree = debut.elapsed();
    if !spu.sortie.is_empty() {
        println!("{}", spu.sortie.iter().map(|v| v.to_string()).collect::<Vec<_>>().join(","));
    }
    let t: String = spu.texte.iter().filter_map(|&v| char::from_u32((v & 0x1F_FFFF) as u32)).collect();
    print!("{}", t);
    if std::env::var("LUGUS_TEMPS").is_ok() {
        eprintln!("{} instructions en {:.3} s", spu.pas, duree.as_secs_f64());
    }
    if let Err(e) = r {
        eprintln!("erreur : {}", e);
        std::process::exit(1);
    }
}

fn lire_nombres(t: &str) -> Vec<u128> {
    t.split(|c: char| c == ',' || c.is_whitespace()).filter(|x| !x.is_empty()).map(|x| x.parse::<u128>().unwrap_or(0)).collect()
}

fn main() {
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
    } else if args.len() >= 3 && args[1] == "lancer" {
        let texte = std::fs::read_to_string(&args[2]).expect("programme illisible");
        let mots = lire_nombres(texte.split(';').next().unwrap_or(""));
        let mut spu = Spu128::nouveau();
        spu.dossier = std::path::Path::new(&args[2]).parent().map(|p| p.to_path_buf());
        spu.charger(&mots);
        spu.entree.extend(args[3..].iter().filter_map(|x| x.parse::<u128>().ok()));
        let r = spu.executer(u64::MAX);
        if !spu.sortie.is_empty() {
            println!("{}", spu.sortie.iter().map(|v| v.to_string()).collect::<Vec<_>>().join(","));
        }
        let t: String = spu.texte.iter().filter_map(|&v| char::from_u32((v & 0x1F_FFFF) as u32)).collect();
        print!("{}", t);
        if let Err(e) = r {
            eprintln!("erreur : {}", e);
            std::process::exit(1);
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
            eprintln!("pas de point fixe : vtxc128.mots n'est pas renouvelé");
            std::process::exit(1);
        }
        let chemin = std::path::Path::new(&args[2]).with_extension("mots");
        ecrire_mots(&chemin.to_string_lossy(), &m1);
        println!("point fixe : {} mots -> {}", m1.len(), chemin.display());
    } else if args.len() >= 3 && args[1] == "ranger" {
        let mots = compiler_ou_sortir(&nombres128(VTXC128), &args[2], COMPLET128);
        let sortie = if args.len() > 3 { args[3].clone() } else { std::path::Path::new(&args[2]).with_extension("adn").to_string_lossy().into_owned() };
        let (mols, t) = adn::ranger(&mots);
        if let Err(e) = adn::ecrire_adn(&sortie, &mots, &mols, &t) {
            eprintln!("écriture de {} impossible : {}", sortie, e);
            std::process::exit(1);
        }
        let p = adn::place_des_temoins(&mots, &mols);
        println!("{} mots, {} molécules, témoins {} mots ({:.1} %) -> {}", mots.len(), mols.len(), p,
                 100.0 * p as f64 / mots.len() as f64, sortie);
    } else if args.len() >= 3 && args[1] == "pourquoi" {
        let source = std::fs::read_to_string(&args[2]).unwrap_or_else(|e| {
            eprintln!("lecture de {} impossible : {}", args[2], e);
            std::process::exit(1)
        });
        let (mots, _, _, prov) = match compiler128_prov(&nombres128(VTXC128), &source, &dossier_de128(&args[2]), COMPLET128, false, true) {
            Ok(r) => r,
            Err(e) => {
                eprint!("{}", e);
                std::process::exit(1);
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
            eprintln!("erreur : {}", e);
        }
        let reactions = provenance::lire(&prov);
        let memoire = provenance::cases(&reactions, |a| spu.lire((3u128 << 62) | a as u128));
        let lire = |a: u64| *memoire.get(&a).unwrap_or(&0);
        println!("{}", provenance::pourquoi(&reactions, quoi.as_deref(), &lire));
    } else if args.len() >= 3 && args[1] == "transcrire" {
        match adn::transcrire(&args[2], true) {
            Ok((mots, _)) => {
                let sortie = if args.len() > 3 { args[3].clone() } else { std::path::Path::new(&args[2]).with_extension("mots").to_string_lossy().into_owned() };
                ecrire_mots(&sortie, &mots);
                println!("l'ARN (les mots seuls, les témoins retirés) -> {}", sortie);
            }
            Err(e) => {
                eprintln!("{}", e);
                std::process::exit(1);
            }
        }
    } else if args.len() >= 2 && args[1].ends_with(".adn") {
        // l'ADN est vérifié et réparé avant de tourner : seul un ADN vrai ou réparé est lancé
        match adn::transcrire(&args[1], false) {
            Ok((mots, _)) => {
                let dossier = std::path::Path::new(&args[1]).parent().map(|p| p.to_path_buf());
                jouer(&mots, &args[2..], dossier);
            }
            Err(e) => {
                eprintln!("{}", e);
                std::process::exit(1);
            }
        }
    } else if args.len() >= 2 && args[1].ends_with(".vtx") {
        let mots = compiler_ou_sortir(&nombres128(VTXC128), &args[1], COMPLET128);
        let dossier = std::path::Path::new(&args[1]).parent().map(|p| p.to_path_buf());
        jouer(&mots, &args[2..], dossier);
    } else {
        eprintln!("utilisation : lugus PROG.vtx [ENTRÉES…] | lugus PROG.adn [ENTRÉES…] | lugus ranger PROG.vtx [PROG.adn] | lugus transcrire PROG.adn [PROG.mots] | lugus compiler PROG.vtx [SORTIE.mots] | lugus renouveler vtxc128.vtx | lugus corpus FICHIER | lugus lancer FICHIER.mots [ENTRÉES…]");
        std::process::exit(2);
    }
}
