// lugus : Lugus, la machine SPU-128 (spécification : docs/specification-spu128.md).
//   lugus corpus FICHIER            une ligne « mots;entrées » par programme -> « pas|sorties|mémoire|B:brins|T:texte »
//   lugus lancer FICHIER.mots [ENTRÉES…]   lance un programme (mots de 128 bits en décimal, séparés par des virgules)
//   lugus PROG.vtx [ENTRÉES…]       compile avec vtxc128 (embarqué) puis exécute : ni Python ni étape .mots
//   lugus compiler PROG.vtx [SORTIE.mots]   écrit seulement les mots
//   lugus renouveler vtxc128.vtx    vtxc128 se recompile lui-même ; point fixe exigé avant d'écrire vtxc128.mots
//   lugus ranger PROG.vtx [PROG.adn]        compile et range l'ADN : les mots et leurs trois témoins
//   lugus transcrire PROG.adn [PROG.mots]   vérifie et répare l'ADN, retire les témoins : les mots (l'ARN)
//   lugus PROG.adn [ENTRÉES…]       vérifie et répare l'ADN ; l'épissage retire les témoins : l'ARN (les mots seuls) est lancé
//   lugus transcrire PROG.adn PROG.arn [--isoforme rapide|sur|memoire|complet] [--queue N]   l'épissage alternatif : un ARN
//                                   avec sa coiffe et sa queue ; sur garde les témoins (la patrouille), memoire l'épigénome
//   lugus PROG.arn [ENTRÉES…]       vérifie la coiffe, raccourcit la queue (usée : refait depuis PROG.adn), lance
//   lugus apprendre PROG.adn [ENTRÉES…]   lance, puis garde les souvenirs dans l'ADN (l'épigénome) : relancé, il les reprend
//   lugus oublier PROG.adn          retire l'épigénome
//   lugus pourquoi PROG.adn …       la même chose, depuis le texte gardé dans l'ADN (s'il redonne ses mots)
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
use machine128::{compiler128, compiler128_iso, compiler128_prov, dossier_de128, nombres128, COMPILATEUR128, COMPLET128, VTXC128};
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
            eprintln!("l'épigénome : {} mots de souvenirs repris", v.len());
            v.len()
        }
        Ok(None) => 0,
        Err(e) => {
            eprintln!("{}", e);
            0
        }
    }
}

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
        Ok(())
    }));
    p
}

/// lance ; avec un ADN, l'épigénome est d'abord repris, et la patrouille veille (sauf LUGUS_PATROUILLE=0) ; rend la
/// machine (pour apprendre)
fn jouer_avec(mots: &[u128], entrees: &[String], dossier: Option<std::path::PathBuf>, t: Option<&adn::Temoins>,
              veille: Option<(Vec<adn::Molecule>, adn::Temoins)>) -> Spu128 {
    let mut spu = Spu128::nouveau();
    spu.dossier = dossier;
    spu.charger(mots);
    if let Some(t) = t {
        reprendre_epigenome(&mut spu, t, mots);
    }
    poser_avaries(&mut spu);
    let patrouille = match veille {
        Some((mols, tv)) if std::env::var("LUGUS_PATROUILLE").map_or(true, |v| v != "0") =>
            Some(armer_patrouille(&mut spu, mots, mols, tv)),
        _ => None,
    };
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
    if let Some(p) = &patrouille {
        let p = p.borrow();
        for x in &p.reparations {
            eprintln!("la patrouille, {}", x);
        }
        if std::env::var("LUGUS_TEMPS").is_ok() || !p.reparations.is_empty() {
            eprintln!("la patrouille : {} relecture(s), {} réparation(s)", p.relues, p.reparations.len());
        }
    }
    if let Err(e) = r {
        eprintln!("erreur : {}", e);
        std::process::exit(1);
    }
    spu
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
        let source = std::fs::read_to_string(&args[2]).unwrap_or_else(|e| {
            eprintln!("lecture de {} impossible : {}", args[2], e);
            std::process::exit(1)
        });
        let (mots, isotopes) = compiler128_iso(&nombres128(VTXC128), &source, &dossier_de128(&args[2]), COMPLET128)
            .unwrap_or_else(|e| {
                eprint!("{}", e);
                std::process::exit(1)
            });
        let sortie = if args.len() > 3 { args[3].clone() } else { std::path::Path::new(&args[2]).with_extension("adn").to_string_lossy().into_owned() };
        let (mols, t) = adn::ranger_texte(&mots, &isotopes, &source);
        if let Err(e) = adn::ecrire_adn(&sortie, &mots, &mols, &t) {
            eprintln!("écriture de {} impossible : {}", sortie, e);
            std::process::exit(1);
        }
        let p = adn::place_des_temoins(&mots, &mols);
        let mut noms: Vec<String> = Vec::new();
        for (n, a) in &isotopes {
            if mols.iter().any(|m| m.isotope && m.debut == *a) {
                noms.push(n.clone());
            }
        }
        println!("{} mots, {} molécules, témoins {} mots ({:.1} %){} -> {}", mots.len(), mols.len(), p,
                 100.0 * p as f64 / mots.len() as f64,
                 if noms.is_empty() { String::new() } else { format!(", isotopes lourds : {}", noms.join(", ")) }, sortie);
    } else if args.len() >= 3 && args[1] == "pourquoi" {
        // d'un .adn : le texte qu'il garde, s'il redonne bien ses mots (la rétrotranscription)
        let source = if args[2].ends_with(".adn") {
            let (mots_adn, _, t) = adn::transcrire(&args[2], false).unwrap_or_else(|e| {
                eprintln!("{}", e);
                std::process::exit(1)
            });
            let (e, quoi) = machine128::retrotranscrire(&t, &mots_adn, &dossier_de128(&args[2]));
            if e != adn::VRAI {
                eprintln!("le texte : {}, {}", adn::nom_etat(e).split(' ').next().unwrap_or(""), quoi);
                std::process::exit(1);
            }
            t.intron("source").map(|l| l.join("\n")).unwrap_or_default()
        } else {
            std::fs::read_to_string(&args[2]).unwrap_or_else(|e| {
                eprintln!("lecture de {} impossible : {}", args[2], e);
                std::process::exit(1)
            })
        };
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
    } else if args.len() >= 3 && (args[1] == "apprendre" || args[1] == "oublier") {
        // apprendre : lancer, puis garder les souvenirs dans l'ADN (l'épigénome) ; oublier : les retirer
        // l'ADN est d'abord vérifié (et réparé, réécrit) ; l'épigénome d'avant est repris pour apprendre encore
        let (mots, _, t0) = adn::transcrire(&args[2], false).unwrap_or_else(|e| {
            eprintln!("{}", e);
            std::process::exit(1)
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
            eprintln!("écriture de {} impossible : {}", args[2], e);
            std::process::exit(1);
        }
        if args[1] == "apprendre" {
            eprintln!("l'épigénome : {} mots de souvenirs rangés dans {}", n, args[2]);
        } else {
            eprintln!("l'épigénome est oublié");
        }
    } else if args.len() >= 3 && args[1] == "transcrire" {
        match adn::transcrire(&args[2], true) {
            Ok((mots, _, t)) => {
                if t.intron("source").is_some() {
                    let (e, quoi) = machine128::retrotranscrire(&t, &mots, &dossier_de128(&args[2]));
                    eprintln!("le texte : {}, {}", adn::nom_etat(e).split(' ').next().unwrap_or(""), quoi);
                }
                let sortie = if args.len() > 3 && !args[3].starts_with("--") { args[3].clone() } else { std::path::Path::new(&args[2]).with_extension("mots").to_string_lossy().into_owned() };
                let isoforme = args.iter().position(|a| a == "--isoforme").and_then(|i| args.get(i + 1)).cloned();
                if sortie.ends_with(".arn") || isoforme.is_some() {
                    // l'épissage alternatif : l'isoforme choisie (rapide par défaut)
                    let iso = isoforme.unwrap_or_else(|| "rapide".into());
                    let sortie = if sortie.ends_with(".arn") { sortie } else { std::path::Path::new(&args[2]).with_extension("arn").to_string_lossy().into_owned() };
                    let mols = adn::lire_adn(&args[2]).map(|x| x.1).unwrap_or_default();
                    let queue = args.iter().position(|a| a == "--queue").and_then(|i| args.get(i + 1))
                        .and_then(|x| x.parse::<u32>().ok()).unwrap_or(adn::QUEUE);
                    if let Err(e) = adn::ecrire_arn(&sortie, &mots, &mols, &t, &iso, queue) {
                        eprintln!("{}", e);
                        std::process::exit(1);
                    }
                    println!("l'ARN, isoforme {} (coiffe, queue de {} lancements) -> {}", iso, queue, sortie);
                } else {
                    ecrire_mots(&sortie, &mots);
                    println!("l'ARN (les mots seuls, les témoins retirés) -> {}", sortie);
                }
            }
            Err(e) => {
                eprintln!("{}", e);
                std::process::exit(1);
            }
        }
    } else if args.len() >= 2 && args[1].ends_with(".adn") {
        // l'ADN est vérifié et réparé avant de tourner : seul un ADN vrai ou réparé est lancé
        match adn::transcrire(&args[1], false) {
            Ok((mots, _, t)) => {
                let dossier = std::path::Path::new(&args[1]).parent().map(|p| p.to_path_buf());
                let mols = adn::lire_adn(&args[1]).map(|x| x.1).unwrap_or_default();
                let veille = Some((mols, t.clone()));
                jouer_avec(&mots, &args[2..], dossier, Some(&t), veille);
            }
            Err(e) => {
                eprintln!("{}", e);
                std::process::exit(1);
            }
        }
    } else if args.len() >= 2 && args[1].ends_with(".arn") {
        // l'ARN : sa coiffe vérifiée, sa queue raccourcie ; usée, il est refait depuis l'ADN (relu et réparé)
        let mut arn = adn::lire_arn(&args[1]).unwrap_or_else(|e| {
            eprintln!("{}", e);
            std::process::exit(1)
        });
        if arn.queue == 0 {
            let f_adn = std::path::Path::new(&args[1]).with_extension("adn").to_string_lossy().into_owned();
            if !std::path::Path::new(&f_adn).exists() {
                eprintln!("{} : l'ARN est usé (sa queue est épuisée) et son ADN ({}) est absent : retranscrivez-le", args[1], f_adn);
                std::process::exit(1);
            }
            let (mots, _, t) = adn::transcrire(&f_adn, false).unwrap_or_else(|e| {
                eprintln!("{}", e);
                std::process::exit(1)
            });
            let mols = adn::lire_adn(&f_adn).map(|x| x.1).unwrap_or_default();
            if let Err(e) = adn::ecrire_arn(&args[1], &mots, &mols, &t, &arn.isoforme, adn::QUEUE) {
                eprintln!("{}", e);
                std::process::exit(1);
            }
            eprintln!("l'ARN était usé : refait depuis {} (relu), une queue neuve de {} lancements", f_adn, adn::QUEUE);
            arn = adn::lire_arn(&args[1]).unwrap_or_else(|e| {
                eprintln!("{}", e);
                std::process::exit(1)
            });
        }
        let _ = adn::raccourcir_queue(&args[1]);
        let dossier = std::path::Path::new(&args[1]).parent().map(|p| p.to_path_buf());
        let epi = arn.epigenome.clone().map(|e| adn::Temoins { signatures: vec![], ombres: vec![], neutrons: Default::default(),
                                                                  introns: vec![("epigenome".into(), e)] });
        jouer_avec(&arn.mots, &args[2..], dossier, epi.as_ref(), arn.temoins.take());
    } else if args.len() >= 2 && args[1].ends_with(".vtx") {
        let mots = compiler_ou_sortir(&nombres128(VTXC128), &args[1], COMPLET128);
        let dossier = std::path::Path::new(&args[1]).parent().map(|p| p.to_path_buf());
        jouer(&mots, &args[2..], dossier);
    } else {
        eprintln!("utilisation : lugus PROG.vtx [ENTRÉES…] | lugus PROG.adn [ENTRÉES…] | lugus PROG.arn [ENTRÉES…] | lugus ranger PROG.vtx [PROG.adn] | lugus transcrire PROG.adn [PROG.mots] | lugus apprendre PROG.adn [ENTRÉES…] | lugus oublier PROG.adn | lugus compiler PROG.vtx [SORTIE.mots] | lugus renouveler vtxc128.vtx | lugus corpus FICHIER | lugus lancer FICHIER.mots [ENTRÉES…]");
        std::process::exit(2);
    }
}
