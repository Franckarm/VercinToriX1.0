// lugus : Lugus, la machine SPU-128 (spécification : docs/specification-spu128.md).
//   lugus corpus FICHIER            une ligne « mots;entrées » par programme -> « pas|sorties|mémoire|B:brins|T:texte »
//   lugus lancer FICHIER.mots [ENTRÉES…]   lance un programme (mots de 128 bits en décimal, séparés par des virgules)
#[allow(dead_code)]
mod qflot128;
#[allow(dead_code)]
mod spu128;
#[allow(dead_code)]
mod hote;
#[allow(dead_code)]
mod miroir;
use spu128::Spu128;

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
    } else {
        eprintln!("utilisation : lugus corpus FICHIER | lugus lancer FICHIER.mots [ENTRÉES…]");
        std::process::exit(2);
    }
}
