// vtx64 : la machine SPU-64 (spécification : docs/specification-spu64.md).
//   vtx64 corpus FICHIER            une ligne « mots;entrées » par programme -> « pas|sorties|mémoire|B:brins|T:texte »
//   vtx64 lancer FICHIER.mots [ENTRÉES…]   lance un programme (mots en décimal, séparés par des virgules)
//   vtx64 PROG.vtx [ENTRÉES…]       compile avec vtxc64 (embarqué) puis exécute : ni Python ni étape .mots
//   vtx64 compiler PROG.vtx [SORTIE.mots]   écrit seulement les mots
//   vtx64 renouveler vtxc64.vtx     vtxc64 se recompile lui-même ; point fixe exigé avant d'écrire vtxc64.mots
//   vtx64 profil FICHIER.mots [ENTRÉES…]   comme lancer, et compte les instructions par adresse (profil.txt)
mod qflot;
// une partie sert seulement à l'atelier (vues du cube, pas à pas)
#[allow(dead_code)]
mod spu64;
#[allow(dead_code)]
mod machine64;
use machine64::{compiler64, dossier_de64, nombres64, situer_erreur, COMPILATEUR64, COMPLET64, VTXC64};
use spu64::Spu64;

fn lire_source(fichier: &str) -> String {
    match std::fs::read_to_string(fichier) {
        Ok(t) => t,
        Err(e) => {
            eprintln!("lecture de {} impossible : {}", fichier, e);
            std::process::exit(1);
        }
    }
}

/// Compile un fichier avec vtxc64 ; une erreur est écrite avec le nom du fichier et la ligne, puis on s'arrête.
fn compiler_ou_sortir(compilateur: &[u64], fichier: &str, mode: machine64::Mode64) -> (Vec<u64>, Vec<u64>) {
    match compiler64(compilateur, &lire_source(fichier), &dossier_de64(fichier), mode, false) {
        Ok((m, t, _)) => (m, t),
        Err(e) => {
            eprint!("{}", situer_erreur(&e, fichier).0);
            std::process::exit(1);
        }
    }
}

fn lire_nombres(t: &str) -> Vec<u64> {
    t.split(|c: char| c == ',' || c.is_whitespace()).filter(|x| !x.is_empty()).map(|x| x.parse::<u64>().unwrap_or(0)).collect()
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
            let mut spu = Spu64::nouveau();
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
        let mut spu = Spu64::nouveau();
        spu.dossier = std::path::Path::new(&args[2]).parent().map(|p| p.to_path_buf());
        spu.charger(&mots);
        spu.entree.extend(args[3..].iter().map(|x| x.parse::<u64>().unwrap_or(0)));
        let debut = std::time::Instant::now();
        // VTX64_LIMITE : un nombre maximal d'instructions (pour trouver une boucle sans fin ; avec VTX64_OU, l'erreur dit où)
        let limite = std::env::var("VTX64_LIMITE").ok().and_then(|v| v.parse().ok()).unwrap_or(u64::MAX);
        let r = spu.executer(limite);
        let texte: String = spu.texte.iter().map(|&c| char::from_u32((c & 0x1F_FFFF) as u32).unwrap_or('?')).collect();
        print!("{}", texte);
        if !spu.sortie.is_empty() {
            println!("{}", spu.sortie.iter().map(|v| v.to_string()).collect::<Vec<_>>().join(","));
        }
        if let Err(x) = r {
            // VTX64_OU : dire aussi où (l'adresse dans le code) et quand ; sans elle, le message reste celui des tests
            if std::env::var("VTX64_OU").is_ok() {
                eprintln!("erreur : {} (à l'adresse {} du code, après {} instructions)", x, spu.pc, spu.pas);
            } else {
                eprintln!("erreur : {}", x);
            }
            std::process::exit(1);
        }
        eprintln!("{} instructions en {:.3} s", spu.pas, debut.elapsed().as_secs_f64());
    } else if args.len() >= 3 && args[1] == "profil" {
        // comme lancer, et compte les instructions par adresse : « profil.txt » à côté du programme (adresse nombre)
        let texte = std::fs::read_to_string(&args[2]).expect("programme illisible");
        let mots = lire_nombres(texte.split(';').next().unwrap_or(""));
        let mut spu = Spu64::nouveau();
        spu.dossier = std::path::Path::new(&args[2]).parent().map(|p| p.to_path_buf());
        spu.charger(&mots);
        spu.entree.extend(args[3..].iter().map(|x| x.parse::<u64>().unwrap_or(0)));
        let mut compte = vec![0u64; mots.len() + 1];
        let mut r = Ok(());
        while !spu.arrete {
            let pc = spu.pc as usize;
            if pc < compte.len() {
                compte[pc] += 1;
            }
            if let Err(x) = spu.pas_unique() {
                r = Err(x);
                break;
            }
        }
        let lignes: String = compte.iter().enumerate().filter(|(_, &n)| n > 0).map(|(a, n)| format!("{} {}\n", a, n)).collect();
        let chemin = spu.dossier.clone().unwrap_or_default().join("profil.txt");
        let _ = std::fs::write(chemin, lignes);
        let texte: String = spu.texte.iter().map(|&c| char::from_u32((c & 0x1F_FFFF) as u32).unwrap_or('?')).collect();
        print!("{}", texte);
        if let Err(x) = r {
            eprintln!("erreur : {}", x);
            std::process::exit(1);
        }
        eprintln!("{} instructions", spu.pas);
    } else if args.len() >= 2 && args[1].ends_with(".vtx") {
        // compiler avec vtxc64, puis exécuter ; la console du programme est le terminal
        let (mots, _) = compiler_ou_sortir(&nombres64(VTXC64), &args[1], COMPLET64);
        let mut spu = Spu64::nouveau();
        spu.dossier = Some(std::env::current_dir().unwrap_or_default());
        spu.charger(&mots);
        let e: Vec<u64> = args[2..].iter().flat_map(|t| t.split_whitespace())
            .map(|t| t.parse::<u64>().unwrap_or_else(|_| { eprintln!("entrée : un nombre attendu, pas « {} »", t); std::process::exit(2) }))
            .collect();
        spu.entree.extend(e);
        machine64::brancher_terminal(&mut spu);
        spu.parler = Some(machine64::parler64);
        let r = spu.executer(u64::MAX);
        {
            use std::io::Write;
            let _ = std::io::stdout().flush();
        }
        if !spu.sortie.is_empty() {
            println!("{}", spu.sortie.iter().map(|v| v.to_string()).collect::<Vec<_>>().join(","));
        }
        if let Err(x) = r {
            eprintln!("erreur : {}", x);
            std::process::exit(1);
        }
    } else if args.len() >= 3 && args[1] == "compiler" {
        let (mots, table) = compiler_ou_sortir(&nombres64(VTXC64), &args[2], COMPLET64);
        let sortie = args.get(3).cloned().unwrap_or_else(|| args[2].trim_end_matches(".vtx").to_string() + ".mots");
        let s: Vec<String> = mots.iter().map(|v| v.to_string()).collect();
        let t: Vec<String> = table.iter().map(|v| v.to_string()).collect();
        std::fs::write(&sortie, s.join(",") + ";" + &t.join(",") + "\n").expect("écriture impossible");
        println!("{} : {} mots", sortie, mots.len());
    } else if args.len() >= 3 && args[1] == "renouveler" {
        // l'ancien compilateur compile le nouveau (m1) ; m1 le recompile (m2) ; m2 se recompile (m3) : m2 = m3 exigé
        let fichier = &args[2];
        let source = lire_source(fichier);
        let (m1, _) = compiler_ou_sortir(&nombres64(VTXC64), fichier, COMPILATEUR64);
        let etape = |m: &[u64]| match compiler64(m, &source, &dossier_de64(fichier), COMPILATEUR64, false) {
            Ok((x, _, _)) => x,
            Err(e) => {
                eprint!("le nouveau compilateur échoue sur lui-même : {}", e);
                std::process::exit(1);
            }
        };
        let m2 = etape(&m1);
        let m3 = etape(&m2);
        if m2 != m3 {
            eprintln!("pas de point fixe : le nouveau compilateur ne se reproduit pas à l'identique ; rien n'est remplacé");
            std::process::exit(1);
        }
        let s: Vec<String> = m3.iter().map(|v| v.to_string()).collect();
        std::fs::write("vtxc64.mots", s.join(",")).expect("écriture de vtxc64.mots impossible");
        println!("point fixe atteint ({} mots) : vtxc64.mots écrit ; recompilez la machine (cargo build --release) pour l'embarquer", m3.len());
    } else {
        eprintln!("utilisation : vtx64 PROG.vtx [ENTRÉES…] | vtx64 compiler PROG.vtx [SORTIE] | vtx64 renouveler vtxc64.vtx | vtx64 corpus FICHIER | vtx64 lancer FICHIER.mots [ENTRÉES…] | vtx64 profil FICHIER.mots [ENTRÉES…]");
        std::process::exit(2);
    }
}
