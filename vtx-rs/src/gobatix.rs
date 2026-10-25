// Gobatix : le service graphique de la machine, sur le SPU-32 et le SPU-64.
//
// Un programme vtx dessine dans l'image de l'étage 1 (ecran, pixel, trait, rectangle, disque : le prélude) puis appelle
// presenter() : la machine copie l'image vers une sortie, la montre, et rend 0 pour continuer, 1 si l'utilisateur a
// fermé la fenêtre, le plus grand nombre si le programme n'a pas préparé d'image. L'image montrée est une image finie :
// le programme dessine déjà la suivante sans que l'écran le voie (le double tampon : l'anti-cube de l'image).
// Les sorties :
//   - la fenêtre (Windows) : une fenêtre Win32 écrite directement, à la cadence choisie par cadence(ms) (60 images par
//     seconde par défaut) ; la souris et le clavier y sont transmis au programme (souris(), touche(), appuyee()) ;
//   - les images PNG (toutes les machines), une par appel, pour vérifier une animation sans écran ;
//   - une animation GIF (toutes les machines), écrite par différence d'une image à l'autre (gif.rs) ;
//   - l'atelier, qui montre les images dans sa vue du cube et peut les enregistrer en GIF.
// vtx gobatix PROG.vtx                                    la fenêtre (Windows), SPU-32
// vtx gobatix64 PROG.vtx                                  la même chose sur le SPU-64
// … --images DOSSIER [--max N] [--pas K]                  les images image-0001.png… (une sur K, au plus N appels)
// … --gif FICHIER.gif [--max N] [--pas K]                 une animation GIF
// … --scenario FICHIER                                   des gestes (souris, touches) rejoués image par image (hote.rs)
use super::cube::taille_dessin;
use super::spu64::Spu64;
use super::Memoire;
use super::hote;
#[allow(unused_imports)]
pub use super::sortie::{installer, montrer, Sortie, ENREGISTREMENT, ENREGISTRER, MAX_IMAGES};
use super::sortie;


/// Le service 12 du SPU-32 : présenter l'image du programme.
pub fn presenter(mem: &Memoire) -> u32 {
    let (l, h) = match taille_dessin(mem) {
        Some((l, h)) => (l as usize, h as usize),
        None => return 0xFFFF_FFFF,
    };
    let mut px = vec![0u32; l * h];
    for (i, p) in px.iter_mut().enumerate() {
        *p = mem.lit(1, i as u32) >> 8;
    }
    if montrer(l, h, &px) { 0 } else { 1 }
}

/// La taille de l'image d'un programme du SPU-64 (@3[14680058], @3[14680059]), si elle est raisonnable.
pub fn taille_dessin64(s: &Spu64) -> Option<(usize, usize)> {
    let (l, h) = (s.regarder((3u64 << 62) | 14_680_058), s.regarder((3u64 << 62) | 14_680_059));
    if (1..=4096).contains(&l) && (1..=4096).contains(&h) && l * h <= 1 << 24 { Some((l as usize, h as usize)) } else { None }
}

/// L'image d'un programme du SPU-64 : chaque point profond #RRRRGGGGBBBBAAAA vu en 0x00RRGGBB (l'octet fort de chaque voie).
pub fn image64(s: &Spu64) -> Option<(usize, usize, Vec<u32>)> {
    let (l, h) = taille_dessin64(s)?;
    let px = (0..l * h).map(|i| point64(s.regarder((1u64 << 62) | i as u64))).collect();
    Some((l, h, px))
}

/// Un point profond vu en 0x00RRGGBB (toujours l'octet fort de chaque voie : rgb(0, 0, 0) = #000000000000FFFF est noir).
pub fn point64(v: u64) -> u32 {
    (((v >> 56) & 0xFF) << 16 | ((v >> 40) & 0xFF) << 8 | ((v >> 24) & 0xFF)) as u32
}

/// Le service 12 du SPU-64.
pub fn presenter64(s: &Spu64) -> u64 {
    match image64(s) {
        Some((l, h, px)) => if montrer(l, h, &px) { 0 } else { 1 },
        None => u64::MAX,
    }
}


/// vtx gobatix PROG.vtx [--images DOSSIER | --gif FICHIER] [--max N] [--pas K] ; m64 : sur le SPU-64.
pub fn lancer(args: &[String], m64: bool) {
    use super::{compiler_avec, dossier_de, executer_dans, nombres, COMPLET, VTXC};
    let usage = if m64 { "vtx gobatix64" } else { "vtx gobatix" };
    if args.is_empty() {
        eprintln!("utilisation : {} PROG.vtx [--images DOSSIER | --gif FICHIER.gif] [--max N] [--pas K] [--scenario FICHIER]", usage);
        std::process::exit(2);
    }
    let (mut images, mut gif, mut max, mut pas, mut scenario) = (None, None, usize::MAX, 1usize, None);
    let mut i = 1;
    while i < args.len() {
        let v = args.get(i + 1);
        match args[i].as_str() {
            "--images" => images = v.cloned(),
            "--gif" => gif = v.cloned(),
            "--max" => max = v.and_then(|x| x.parse().ok()).unwrap_or(usize::MAX),
            "--pas" => pas = v.and_then(|x| x.parse().ok()).unwrap_or(1).max(1),
            "--scenario" => scenario = v.cloned(),
            autre => {
                eprintln!("option inconnue : {}", autre);
                std::process::exit(2);
            }
        }
        i += 2;
    }
    let source = std::fs::read_to_string(&args[0]).unwrap_or_else(|e| {
        eprintln!("lecture impossible : {}", e);
        std::process::exit(1)
    });
    let base = dossier_de(&args[0]);
    // une animation ou un scénario : l'horloge des images (hote.rs), le programme se rejoue à l'identique
    let horloge_images = images.is_some() || gif.is_some() || scenario.is_some();
    let sortie: Box<dyn Sortie> = match (images, gif) {
        (Some(d), _) => sortie::fichiers(&d, pas, max),
        (None, Some(f)) => sortie::animation(&f, pas, max),
        (None, None) => match sortie::fenetre(&args[0]) {
            Some(s) => s,
            None => {
                eprintln!("pas de fenêtre sur cette machine : utilisez --images DOSSIER ou --gif FICHIER.gif");
                std::process::exit(2)
            }
        },
    };
    hote::remettre();
    hote::HORLOGE_IMAGES.store(horloge_images, std::sync::atomic::Ordering::Relaxed);
    if let Some(f) = scenario {
        let t = std::fs::read_to_string(&f).unwrap_or_else(|e| {
            eprintln!("scénario illisible : {}", e);
            std::process::exit(1)
        });
        if let Err(e) = hote::charger_scenario(&t) {
            eprintln!("{}", e);
            std::process::exit(1);
        }
    }
    installer(Some(sortie));
    let r: Result<(), String> = if m64 {
        use super::machine64::{compiler64, nombres64, COMPLET64, VTXC64};
        let mots = match compiler64(&nombres64(VTXC64), &source, &base, COMPLET64, false) {
            Ok((m, _, _)) => m,
            Err(e) => {
                eprint!("{}", e);
                std::process::exit(1)
            }
        };
        let mut s = Spu64::nouveau();
        s.dossier = Some(std::path::PathBuf::from(&base));
        s.charger(&mots);
        super::machine64::brancher_terminal(&mut s);
        s.presenter = Some(Box::new(presenter64));
        let r = s.executer(u64::MAX);
        if !s.sortie.is_empty() {
            println!("{}", s.sortie.iter().map(|v| v.to_string()).collect::<Vec<_>>().join(","));
        }
        r
    } else {
        let (mots, _) = compiler_avec(&nombres(VTXC), &source, &base, COMPLET).unwrap_or_else(|e| {
            eprint!("{}", e);
            std::process::exit(1)
        });
        let mut mem = Memoire::new(false);
        super::charger(&mut mem, &mots);
        executer_dans(&mem, &[], u64::MAX / 4, Some(std::path::Path::new(&base)), None).map(|_| ())
    };
    sortie::finir();
    if let Err(e) = r {
        eprintln!("erreur : {}", e);
        std::process::exit(1);
    }
}
