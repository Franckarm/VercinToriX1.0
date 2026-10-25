// Noyau des programmes forgés (forge/forge.py) : la machine autour du programme vtx. La mémoire est celle de la
// machine émulée (memoire.rs, avec les cubes et leurs fichiers miroirs : miroir.rs), Gobatix aussi (la fenêtre, les
// images, l'animation GIF, la souris et le clavier : sortie.rs, gif.rs, hote.rs) ; ces fichiers de vtx-rs sont
// recopiés ici tels quels, à la place de la ligne @MODULES@. Suivent les entrées, les sorties, les fichiers et les
// services du SPU (SYS), puis le programme lui-même : une fonction Rust par fonction vtx.
use std::fs;
use std::io::Write;

// @MODULES@

use memoire::*;

const MASK: u64 = 0xFFFF_FFFF;
const PILE_HAUT: u32 = 0x7F_FFFF;

#[inline(always)]
fn f(w: u32) -> f32 {
    f32::from_bits(w)
}

#[inline(always)]
fn fb(v: f32) -> u32 {
    if v.is_nan() { 0x7FC0_0000 } else { v.to_bits() }
}

#[inline(always)]
fn dd(x: u64) -> f64 {
    f64::from_bits(x)
}

#[inline(always)]
fn db(v: f64) -> u64 {
    if v.is_nan() { 0x7FF8_0000_0000_0000 } else { v.to_bits() }
}

#[inline(always)]
fn divu(a: u32, b: u32) -> u32 {
    if b == 0 { u32::MAX } else { a / b }
}

#[inline(always)]
fn modu(a: u32, b: u32) -> u32 {
    if b == 0 { a } else { a % b }
}

#[inline(always)]
fn dot(x: u32, y: u32) -> u64 {
    ((x >> 24) as u64) * ((y >> 24) as u64)
        + (((x >> 16) & 255) as u64) * (((y >> 16) & 255) as u64)
        + (((x >> 8) & 255) as u64) * (((y >> 8) & 255) as u64)
        + ((x & 255) as u64) * ((y & 255) as u64)
}

fn quits(a: u32, b: u32, op: u32) -> u32 {
    let mut r = 0u32;
    for k in 0..16 {
        let x = (a >> (2 * k)) & 3;
        let y = (b >> (2 * k)) & 3;
        let v = match op {
            0x10 => x.min(y),
            0x11 => x.max(y),
            _ => (x + y) & 3,
        };
        r |= v << (2 * k);
    }
    r
}

struct Fichier {
    lecture: bool,
    car: Vec<u32>,
    pos: usize,
    chemin: std::path::PathBuf,
}

/// Entrées, sorties, console et fichiers du programme.
struct Es {
    entrees: Vec<u32>,
    ie: usize,
    sorties: Vec<u32>,
    texte: Vec<u32>,
    fichiers: std::collections::HashMap<u32, Fichier>,
    dossier: Option<std::path::PathBuf>,
    /// le clavier se lit (programme lancé seul) ; faux pour la vérification : rien à lire, comme l'interprète
    clavier: bool,
}

impl Es {
    fn new(entrees: Vec<u32>, dossier: Option<std::path::PathBuf>) -> Self {
        Es { entrees, ie: 0, sorties: Vec::new(), texte: Vec::new(), fichiers: Default::default(), dossier, clavier: true }
    }
    #[inline(always)]
    fn entree(&mut self) -> u32 {
        if self.ie < self.entrees.len() {
            self.ie += 1;
            self.entrees[self.ie - 1]
        } else {
            0
        }
    }
    fn entc(&mut self, canal: u32) -> u32 {
        match canal {
            0 => self.entree(),
            1 if !self.clavier => 0xFFFF_FFFF,
            1 => {
                // le clavier : le texte en attente est montré d'abord (la question avant la réponse)
                use std::io::Read;
                let mut o = std::io::stdout();
                if !self.texte.is_empty() {
                    let t: String = self.texte.iter().filter_map(|&v| char::from_u32(v & 0x1F_FFFF)).collect();
                    let _ = write!(o, "{}", t);
                    self.texte.clear();
                }
                let _ = o.flush();
                let mut entree = std::io::stdin().lock();
                let mut b = [0u8; 4];
                if entree.read(&mut b[..1]).unwrap_or(0) == 0 {
                    return 0xFFFF_FFFF;
                }
                let n = match b[0] { 0x00..=0x7F => 1, 0xC0..=0xDF => 2, 0xE0..=0xEF => 3, _ => 4 };
                for k in 1..n {
                    if entree.read(&mut b[k..k + 1]).unwrap_or(0) == 0 {
                        return 0xFFFF_FFFF;
                    }
                }
                std::str::from_utf8(&b[..n]).ok().and_then(|s| s.chars().next()).map(|c| c as u32).unwrap_or(0xFFFD)
            }
            k => match self.fichiers.get_mut(&k) {
                Some(fi) if fi.lecture && fi.pos < fi.car.len() => {
                    fi.pos += 1;
                    fi.car[fi.pos - 1]
                }
                _ => 0xFFFF_FFFF,
            },
        }
    }
    fn sorc(&mut self, v: u32, canal: u32) {
        match canal {
            0 => self.sorties.push(v),
            1 => self.texte.push(v),
            k => {
                if let Some(fi) = self.fichiers.get_mut(&k) {
                    if !fi.lecture {
                        fi.car.push(v);
                    }
                }
            }
        }
    }
    /// SYS : les services de la machine hôte, comme sur la machine émulée (main.rs).
    fn sys(&mut self, mem: &Memoire, service: u32, arg: u32) -> u32 {
        let dossier = self.dossier.clone();
        match service {
            1 | 2 => match &dossier {
                None => 0xFFFF_FFFF,
                Some(d) => {
                    let chemin = d.join(texte_memoire(mem, arg));
                    let canal = self.fichiers.keys().copied().max().unwrap_or(1).max(1) + 1;
                    if service == 1 {
                        match fs::read_to_string(&chemin) {
                            Ok(t) => {
                                self.fichiers.insert(canal, Fichier { lecture: true, car: t.chars().map(|c| c as u32).collect(), pos: 0, chemin });
                                canal
                            }
                            Err(_) => 0xFFFF_FFFF,
                        }
                    } else {
                        self.fichiers.insert(canal, Fichier { lecture: false, car: Vec::new(), pos: 0, chemin });
                        canal
                    }
                }
            },
            3 => match self.fichiers.remove(&arg) {
                None => 0xFFFF_FFFF,
                Some(fi) => {
                    if !fi.lecture {
                        let t: String = fi.car.iter().filter_map(|&v| char::from_u32(v & 0x1F_FFFF)).collect();
                        if fi.chemin.file_name().map(|n| n == "voix:").unwrap_or(false) {
                            parler_hote(&t);
                        } else {
                            let _ = fs::write(&fi.chemin, t);
                        }
                    }
                    0
                }
            },
            4 => match self.fichiers.get(&arg) {
                Some(fi) if fi.lecture && fi.pos < fi.car.len() => 0,
                _ => 1,
            },
            5 => bruit_hote(),
            6 | 7 => match &dossier {
                None => 0xFFFF_FFFF,
                Some(d) => {
                    let chemin = d.join(texte_memoire(mem, mem.lit(3, 14_680_060)));
                    let (a, n) = (mem.lit(3, 14_680_061), mem.lit(3, 14_680_062));
                    let (e, o) = ((a >> 24) & 3, a & ADR);
                    if service == 6 {
                        let mut b = Vec::with_capacity(n as usize * 4);
                        for i in 0..n {
                            b.extend_from_slice(&mem.lit(e, o.wrapping_add(i)).to_le_bytes());
                        }
                        fs::write(&chemin, b).map(|_| n).unwrap_or(0xFFFF_FFFF)
                    } else {
                        match fs::read(&chemin) {
                            Ok(b) => {
                                let k = (b.len() / 4).min(n as usize);
                                for i in 0..k {
                                    mem.ecrit(e, o.wrapping_add(i as u32), u32::from_le_bytes([b[4 * i], b[4 * i + 1], b[4 * i + 2], b[4 * i + 3]]));
                                }
                                k as u32
                            }
                            Err(_) => 0xFFFF_FFFF,
                        }
                    }
                }
            },
            8 => mem.accorder(arg & 3, arg >> 2, dossier.as_deref()),
            9 => mem.frequence(arg & 3),
            10 => {
                eprintln!("erreur : mémoire pleine : le tas ne peut plus grandir, même après avoir ramassé les miettes");
                std::process::exit(1);
            }
            11 => mem.ranger_cube(arg & 3, arg >> 2, dossier.as_deref()),
            12 => presenter(mem),
            16..=21 | 23 => hote::service(service as u64, arg as u64, 0xFFFF_FFFF).unwrap_or(0) as u32,
            22 => miroir::prendre_etat() as u32,
            _ => 0xFFFF_FFFF,
        }
    }
}

/// Le service 12 : présenter l'image du programme (étage 1, mots #RRGGBBAA ; sa taille en @3[14680058..14680059]).
/// La première image ouvre la fenêtre (Windows), si aucune autre sortie n'a été choisie (--gif, --images).
fn presenter(mem: &Memoire) -> u32 {
    let (l, h) = (mem.lit(3, 14_680_058), mem.lit(3, 14_680_059));
    if !(l >= 1 && h >= 1 && l <= 4096 && h <= 4096 && l * h <= 1 << 24) {
        return 0xFFFF_FFFF;
    }
    if !sortie::installee() && !SANS_FENETRE.load(std::sync::atomic::Ordering::Relaxed) {
        SANS_FENETRE.store(true, std::sync::atomic::Ordering::Relaxed);
        if let Some(s) = sortie::fenetre(NOM) {
            sortie::installer(Some(s));
        }
    }
    let (l, h) = (l as usize, h as usize);
    let mut px = vec![0u32; l * h];
    for (i, p) in px.iter_mut().enumerate() {
        *p = mem.lit(1, i as u32) >> 8;
    }
    if sortie::montrer(l, h, &px) { 0 } else { 1 }
}

static SANS_FENETRE: std::sync::atomic::AtomicBool = std::sync::atomic::AtomicBool::new(false);

/// Dire un texte à voix haute : la voix de Windows ; ailleurs espeak-ng ou espeak s'il est là ; sinon rien.
fn parler_hote(t: &str) {
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

fn bruit_hote() -> u32 {
    use std::hash::{BuildHasher, Hasher};
    static COMPTEUR: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
    let mut h = std::collections::hash_map::RandomState::new().build_hasher();
    h.write_u128(std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map(|d| d.as_nanos()).unwrap_or(0));
    h.write_u64(COMPTEUR.fetch_add(1, std::sync::atomic::Ordering::Relaxed));
    let x = h.finish();
    (x ^ (x >> 32)) as u32
}

fn texte_memoire(mem: &Memoire, adr: u32) -> String {
    let (e, a) = ((adr >> 24) & 3, adr & ADR);
    let n = mem.lit(e, a).min(4096);
    (0..n).filter_map(|i| char::from_u32(mem.lit(e, a.wrapping_add(1 + i)) & 0x1F_FFFF)).collect()
}

fn gemv(mem: &Memoire, sp: u32) {
    let lit0 = |t: u32| mem.lit(0, sp.wrapping_add(4 - t));
    let (n, w_, qb, kb, ob) = (lit0(0), lit0(1), lit0(2), lit0(3), lit0(4));
    let q: Vec<u32> = (0..w_).map(|j| mem.lit(2, qb.wrapping_add(j))).collect();
    for i in 0..n {
        let mut s: u64 = 0;
        for j in 0..w_ {
            let adr = (kb as u64 + i as u64 * w_ as u64 + j as u64) as u32;
            s += dot(q[j as usize], mem.lit(2, adr));
        }
        mem.ecrit(2, ob.wrapping_add(i), s as u32);
    }
}

fn nombres(s: &str) -> Vec<u32> {
    s.split(',').filter(|t| !t.trim().is_empty()).map(|t| t.trim().parse::<u64>().expect("nombre attendu") as u32).collect()
}

fn charger_mots(mem: &Memoire, mots: &[u32]) {
    for (i, &w) in mots.iter().enumerate() {
        mem.ecrit(0, i as u32, w);
    }
}

/// La machine d'un programme forgé : sa mémoire, ses entrées et sorties, et le sommet de la pile du SPU (le cadre des
/// fonctions qui peuvent ramasser les miettes, que le ramasse-miettes parcourt).
struct Ctx {
    mem: Memoire,
    es: Es,
    sp: u32,
}

/// Lance le programme comme « vtx PROG.vtx » (ou « vtx gobatix PROG.vtx » s'il présente des images) : les nombres de
/// la ligne de commande sont ses entrées ; --gif FICHIER, --images DOSSIER, --max N, --pas K, --scenario FICHIER
/// comme pour Gobatix.
fn lancer_programme(principal: fn(&mut Ctx) -> u32) {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let (mut images, mut gif, mut max, mut pas, mut scenario) = (None, None, usize::MAX, 1usize, None);
    let mut entrees = Vec::new();
    let mut i = 0;
    while i < args.len() {
        let v = args.get(i + 1).cloned();
        match args[i].as_str() {
            "--images" => images = v,
            "--gif" => gif = v,
            "--max" => max = v.and_then(|x| x.parse().ok()).unwrap_or(usize::MAX),
            "--pas" => pas = v.and_then(|x| x.parse().ok()).unwrap_or(1).max(1),
            "--scenario" => scenario = v,
            n => {
                entrees.push(n.parse::<u64>().unwrap_or_else(|_| {
                    eprintln!("entrée : un nombre, ou --gif FICHIER, --images DOSSIER, --max N, --pas K, --scenario FICHIER");
                    std::process::exit(2)
                }) as u32);
                i += 1;
                continue;
            }
        }
        i += 2;
    }
    hote::remettre();
    // une animation ou un scénario : l'horloge des images (hote.rs), le programme se rejoue à l'identique
    hote::HORLOGE_IMAGES.store(images.is_some() || gif.is_some() || scenario.is_some(), std::sync::atomic::Ordering::Relaxed);
    if let Some(f) = scenario {
        let t = fs::read_to_string(&f).unwrap_or_else(|e| {
            eprintln!("scénario illisible : {}", e);
            std::process::exit(1)
        });
        if let Err(e) = hote::charger_scenario(&t) {
            eprintln!("{}", e);
            std::process::exit(1);
        }
    }
    match (images, gif) {
        (Some(d), _) => sortie::installer(Some(sortie::fichiers(&d, pas, max))),
        (None, Some(g)) => sortie::installer(Some(sortie::animation(&g, pas, max))),
        _ => {}
    }
    // une grande pile : les fonctions récursives du programme vtx sont des fonctions récursives de la machine
    let fil = std::thread::Builder::new().stack_size(1 << 30).spawn(move || {
        let mem = Memoire::new(false);
        charger_mots(&mem, &MOTS);
        let es = Es::new(entrees, std::env::current_dir().ok());
        let mut c = Ctx { mem, es, sp: PILE_HAUT };
        principal(&mut c);
        if !c.es.sorties.is_empty() {
            let s: Vec<String> = c.es.sorties.iter().map(|v| v.to_string()).collect();
            println!("{}", s.join(","));
        }
        let t: String = c.es.texte.iter().filter_map(|&v| char::from_u32(v & 0x1F_FFFF)).collect();
        print!("{}", t);
        let _ = std::io::stdout().flush();
    }).expect("fil d'exécution");
    let ok = fil.join().is_ok();
    sortie::finir();
    if !ok {
        std::process::exit(1);
    }
}
