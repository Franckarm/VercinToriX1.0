// L'exécutable de Lugus : un programme vtx et les cubes dont il a besoin, emportés dans un seul .exe.
//
// Le .exe est la machine elle-même (vtx.exe, déjà construite : ni Rust ni Python pour le faire), suivie d'un paquet :
// les mots du programme compilé par vtxc128, et les fichiers de son dossier qu'il lira (ses cubes sur disque, avec leurs
// anti-cubes et leurs ombres ; les fichiers que ses textes nomment). Au lancement, la machine trouve le paquet à sa
// propre fin, pose à côté d'elle les fichiers qui n'y sont pas encore (jamais par-dessus : le programme peut les avoir
// changés), puis joue le programme : la console au clavier, la fenêtre de dessin à la première image présentée.
//
// La fin du fichier : [le paquet][sa longueur, u64][« VTXLUGUS »]. Le paquet : des entrées [longueur du nom, u32][nom]
// [longueur des données, u64][données] ; « @mots » (les mots, u128 petit-boutiste), « @nom » (le nom du programme).
//
// C'est la première étape : les mots tournent sur Lugus embarqué, à la vitesse d'Ogmios. La suivante traduira les mots
// en x86-64 (comme natif.py pour Senos), dans le même paquet, et le socle gardera les services, les flottants et le cube.
use std::io::{Read, Seek, SeekFrom};
use std::path::{Path, PathBuf};

const MARQUE: &[u8; 8] = b"VTXLUGUS";
/// au plus tant d'octets de fichiers emportés (les cubes y compris)
const PLAFOND: u64 = 512 << 20;

pub struct Paquet {
    pub nom: String,
    pub mots: Vec<u128>,
    pub fichiers: Vec<(String, Vec<u8>)>,
}

/// La longueur du paquet à la fin de ce fichier, s'il en a un (16 octets lus : un vtx.exe ordinaire n'en a pas).
fn longueur_paquet(chemin: &Path) -> Option<(u64, u64)> {
    let mut f = std::fs::File::open(chemin).ok()?;
    let taille = f.metadata().ok()?.len();
    if taille < 16 {
        return None;
    }
    f.seek(SeekFrom::Start(taille - 16)).ok()?;
    let mut fin = [0u8; 16];
    f.read_exact(&mut fin).ok()?;
    if &fin[8..] != MARQUE {
        return None;
    }
    let n = u64::from_le_bytes(fin[..8].try_into().unwrap());
    if n + 16 > taille {
        return None;
    }
    Some((taille, n))
}

/// Le paquet que porte l'exécutable en cours, s'il en porte un.
pub fn paquet_embarque() -> Option<Paquet> {
    let exe = std::env::current_exe().ok()?;
    let (taille, n) = longueur_paquet(&exe)?;
    let mut f = std::fs::File::open(&exe).ok()?;
    f.seek(SeekFrom::Start(taille - 16 - n)).ok()?;
    let mut o = vec![0u8; n as usize];
    f.read_exact(&mut o).ok()?;
    lire_paquet(&o)
}

fn lire_paquet(o: &[u8]) -> Option<Paquet> {
    let mut p = Paquet { nom: String::new(), mots: Vec::new(), fichiers: Vec::new() };
    let mut k = 0usize;
    let prendre = |k: &mut usize, n: usize| -> Option<&[u8]> {
        let r = o.get(*k..*k + n)?;
        *k += n;
        Some(r)
    };
    while k < o.len() {
        let ln = u32::from_le_bytes(prendre(&mut k, 4)?.try_into().ok()?) as usize;
        let nom = String::from_utf8(prendre(&mut k, ln)?.to_vec()).ok()?;
        let ld = u64::from_le_bytes(prendre(&mut k, 8)?.try_into().ok()?) as usize;
        let d = prendre(&mut k, ld)?;
        match nom.as_str() {
            "@mots" => p.mots = d.chunks_exact(16).map(|c| u128::from_le_bytes(c.try_into().unwrap())).collect(),
            "@nom" => p.nom = String::from_utf8_lossy(d).into_owned(),
            _ => p.fichiers.push((nom, d.to_vec())),
        }
    }
    Some(p)
}

fn ecrire_entree(o: &mut Vec<u8>, nom: &str, d: &[u8]) {
    o.extend_from_slice(&(nom.len() as u32).to_le_bytes());
    o.extend_from_slice(nom.as_bytes());
    o.extend_from_slice(&(d.len() as u64).to_le_bytes());
    o.extend_from_slice(d);
}

/// Les fichiers du dossier que le programme emporte : ses cubes sur disque (cube128-, anticube128-, ombre128-), et
/// ceux que nomment les textes de sa source (« donnees.txt », « carte.cub »…), s'ils sont dans le dossier.
fn fichiers_utiles(source: &str, dossier: &Path) -> Vec<String> {
    let mut noms: Vec<String> = Vec::new();
    if let Ok(l) = std::fs::read_dir(dossier) {
        for f in l.flatten() {
            let n = f.file_name().to_string_lossy().into_owned();
            if ["cube128-", "anticube128-", "ombre128-"].iter().any(|p| n.starts_with(p)) && f.path().is_file() {
                noms.push(n);
            }
        }
    }
    // les textes de la source : ce qui est entre guillemets, sur une ligne
    for ligne in source.lines() {
        let l = ligne.split("//").next().unwrap_or("");
        let morceaux: Vec<&str> = l.split('"').collect();
        for (i, m) in morceaux.iter().enumerate() {
            if i % 2 == 0 || m.is_empty() || m.len() > 200 {
                continue;
            }
            let m = m.strip_prefix("octets:").unwrap_or(m);
            // un nom simple, dans le dossier (pas de chemin qui en sort)
            if m.contains("..") || m.starts_with('/') || m.starts_with('\\') || m.contains(':') {
                continue;
            }
            let p = dossier.join(m);
            if p.is_file() && !m.ends_with(".vtx") && !noms.iter().any(|n| n == m) {
                noms.push(m.to_string());
            }
        }
    }
    noms.sort();
    noms
}

/// Fait l'exécutable : compile PROG.vtx pour Lugus, puis écrit le socle suivi du paquet. Rend le compte rendu.
pub fn fabriquer(fichier: &Path, socle: &Path, sortie: &Path) -> Result<String, String> {
    use super::machine128::{compiler128, dossier_de128, nombres128, COMPLET128, VTXC128};
    let source = std::fs::read_to_string(fichier).map_err(|e| format!("lecture de {} impossible : {}", fichier.display(), e))?;
    let f = fichier.to_string_lossy().into_owned();
    let base = dossier_de128(&f);
    let (mots, _, _) = compiler128(&nombres128(VTXC128), &source, &base, COMPLET128, false)?;
    // le socle : la machine, sans le paquet qu'elle porterait déjà (un .exe de Lugus refait à partir d'un autre)
    let mut octets = std::fs::read(socle).map_err(|e| format!("la machine ({}) est illisible : {}", socle.display(), e))?;
    if let Some((taille, n)) = longueur_paquet(socle) {
        octets.truncate((taille - 16 - n) as usize);
    }
    let nom = fichier.file_stem().map(|n| n.to_string_lossy().into_owned()).unwrap_or_default();
    let mut paquet = Vec::new();
    ecrire_entree(&mut paquet, "@nom", nom.as_bytes());
    let m: Vec<u8> = mots.iter().flat_map(|w| w.to_le_bytes()).collect();
    ecrire_entree(&mut paquet, "@mots", &m);
    let dossier = PathBuf::from(&base);
    let mut emportes = Vec::new();
    let mut total = 0u64;
    for n in fichiers_utiles(&source, &dossier) {
        let d = match std::fs::read(dossier.join(&n)) {
            Ok(d) => d,
            Err(_) => continue,
        };
        total += d.len() as u64;
        if total > PLAFOND {
            return Err(format!("trop de fichiers à emporter (plus de {} Mo) : {} et les suivants", PLAFOND >> 20, n));
        }
        ecrire_entree(&mut paquet, &n, &d);
        emportes.push(n);
    }
    octets.extend_from_slice(&paquet);
    octets.extend_from_slice(&(paquet.len() as u64).to_le_bytes());
    octets.extend_from_slice(MARQUE);
    std::fs::write(sortie, &octets).map_err(|e| format!("écriture de {} impossible : {}", sortie.display(), e))?;
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let _ = std::fs::set_permissions(sortie, std::fs::Permissions::from_mode(0o755));
    }
    let cubes = emportes.iter().filter(|n| n.starts_with("cube128-")).count();
    let mut t = format!("{} : {} mots de Lugus, {} octets", sortie.display(), mots.len(), octets.len());
    if emportes.is_empty() {
        t.push_str(" ; aucun cube ni fichier à emporter");
    } else {
        t.push_str(&format!(" ; emportés : {} cube(s) sur disque, {} fichier(s) en tout ({})", cubes, emportes.len(), emportes.join(", ")));
    }
    Ok(t)
}

/// La console du programme : ce qu'il écrit paraît aussitôt, ce qu'il lit vient du clavier.
pub fn brancher_terminal128(s: &mut super::spu128::Spu128) {
    s.console_ecrire = Some(Box::new(|v: u128| {
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
        match super::machine64::lire_car_clavier64() {
            u64::MAX => u128::MAX,
            c => c as u128,
        }
    }));
}

#[cfg(windows)]
#[link(name = "kernel32")]
extern "system" {
    fn GetConsoleProcessList(liste: *mut u32, n: u32) -> u32;
}

/// la console n'est qu'à ce programme : il a été lancé d'un double clic, pas depuis un terminal
#[cfg(windows)]
fn console_a_lui() -> bool {
    let mut l = [0u32; 4];
    unsafe { GetConsoleProcessList(l.as_mut_ptr(), 4) == 1 }
}

/// Lancé d'un double-clic en mode console, le .exe a sa console à lui : elle se fermerait avec lui. On attend une touche.
fn attendre_si_seul() {
    #[cfg(windows)]
    {
        if console_a_lui() && std::env::var("VTX_SANS_PAUSE").is_err() {
            use std::io::Write;
            print!("\n(Entrée pour fermer)");
            let _ = std::io::stdout().flush();
            let mut t = String::new();
            let _ = std::io::stdin().read_line(&mut t);
        }
    }
}

/// Joue le programme emporté : les fichiers posés à côté de l'exécutable s'ils manquent, puis Lugus.
pub fn jouer(p: Paquet) -> ! {
    let exe = std::env::current_exe().unwrap_or_default();
    let dossier = exe.parent().map(|d| d.to_path_buf()).unwrap_or_default();
    for (nom, d) in &p.fichiers {
        let c = dossier.join(nom);
        if !c.exists() {
            if let Err(e) = std::fs::write(&c, d) {
                eprintln!("{} : impossible de poser {} ({})", p.nom, nom, e);
            }
        }
    }
    let args: Vec<String> = std::env::args().skip(1).collect();
    let mut s = super::spu128::Spu128::nouveau();
    s.dossier = Some(dossier);
    s.charger(&p.mots);
    s.entree.extend(args.iter().filter_map(|x| x.parse::<u128>().ok()));
    s.presenter = Some(Box::new(super::pas128::presenter128));
    s.machine_fille = Some(super::machine128::machine_fille);
    s.parler = Some(super::parler_hote);
    // la fenêtre de dessin s'ouvre à la première image présentée (un programme sans image n'en a pas)
    if let Some(f) = super::sortie::fenetre(&p.nom) {
        super::sortie::installer(Some(f));
    }
    // lancé d'un double clic (sa console à lui), sous Windows : la vitrine, une fenêtre avec le texte et le cube
    #[cfg(windows)]
    {
        let force_console = args.iter().any(|a| a == "--console") || std::env::var("VTX_CONSOLE").is_ok();
        if !force_console && console_a_lui() {
            let code = super::vitrine::jouer(s, &p.nom, &p.mots);
            std::process::exit(code)
        }
    }
    brancher_terminal128(&mut s);
    let r = avancer(&mut s, &p.mots);
    {
        use std::io::Write;
        let _ = std::io::stdout().flush();
    }
    if !s.sortie.is_empty() {
        println!("{}", s.sortie.iter().map(|v| v.to_string()).collect::<Vec<_>>().join(","));
    }
    super::sortie::finir();
    let code = match r {
        Ok(()) => 0,
        Err(e) => {
            eprintln!("\nerreur : {}", e);
            1
        }
    };
    attendre_si_seul();
    std::process::exit(code)
}

/// Joue la machine jusqu'à son arrêt : traduite en x86-64 (natif128.rs), sauf avec VTX_INTERPRETE (Lugus seul, pour
/// comparer) ou si la mémoire exécutable est refusée. VTX_COMPTE écrit, sur la sortie d'erreur, le compte des
/// instructions et la part traduite.
pub fn avancer(s: &mut super::spu128::Spu128, mots: &[u128]) -> Result<(), String> {
    let t0 = std::time::Instant::now();
    let interprete = std::env::var("VTX_INTERPRETE").is_ok() || !cfg!(target_arch = "x86_64");
    let (r, quoi) = match if interprete { None } else { super::natif128::traduire(mots) } {
        Some(t) => {
            let q = format!("traduit en x86-64 : {} demi-instructions sur {}", t.traduites, t.n);
            (t.executer(s), q)
        }
        None => (s.executer(u64::MAX), "joué par Lugus (sans traduction)".to_string()),
    };
    if std::env::var("VTX_COMPTE").is_ok() {
        eprintln!("instructions {} ; {} ; {:.3} s ; accès par Lugus : {}", s.pas, quoi, t0.elapsed().as_secs_f64(),
                  super::spu128::LENTS.load(std::sync::atomic::Ordering::Relaxed));
    }
    r
}

/// vtx exe128 PROG.vtx [SORTIE] : l'exécutable de Lugus, fait à partir de cette machine-ci.
pub fn commande(args: &[String]) {
    let fichier = match args.first() {
        Some(f) => PathBuf::from(f),
        None => {
            eprintln!("utilisation : vtx exe128 PROG.vtx [SORTIE]");
            std::process::exit(2)
        }
    };
    let sortie = args.get(1).map(PathBuf::from).unwrap_or_else(|| {
        if cfg!(windows) { fichier.with_extension("exe") } else { fichier.with_extension("") }
    });
    let socle = std::env::current_exe().expect("chemin de la machine inconnu");
    match fabriquer(&fichier, &socle, &sortie) {
        Ok(t) => println!("{}", t),
        Err(e) => {
            eprint!("{}", e);
            if !e.ends_with('\n') {
                eprintln!();
            }
            std::process::exit(1)
        }
    }
}
