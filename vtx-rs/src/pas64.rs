// Hors de Windows, seule la vérification (essai) s'en sert : une partie y reste inemployée.
#![cfg_attr(not(any(windows, feature = "verif_fenetre")), allow(dead_code))]
// Le pas à pas et les vues de la machine 64 bits, sans fenêtre : l'atelier (fenetre.rs) s'en sert, et
// « vtx-spu essai-pas64 PROG.vtx » les vérifie partout (même sous Linux).
use super::machine64::vers_point32;
use super::spu64::Spu64;
use super::spu128::Spu128;
use super::pas128::{decoder128, vers_point32_128};
use super::{boucle, Etat, Fichiers, Memoire};
use std::collections::HashMap;
use std::path::PathBuf;

/// Le pas à pas : la machine arrêtée entre deux instructions, et la table adresse -> ligne donnée par vtxc.
pub struct Pas {
    pub moteur: Moteur,
    pub debuts: HashMap<u64, usize>,
    pub ligne: Option<usize>,
    pub fini: bool,
}

/// La machine du pas à pas : la SPU-32 (mémoire, registres, fichiers ouverts) ou la SPU-64.
pub enum Moteur {
    M32 { mem: Memoire, et: Etat, fichiers: Fichiers, entrees: Vec<u32>, dossier: PathBuf },
    M64(Box<Spu64>),
    M128(Box<Spu128>),
}

impl Pas {
    pub fn pc(&self) -> u64 {
        match &self.moteur {
            Moteur::M32 { et, .. } => et.pc as u64,
            Moteur::M64(s) => s.pc,
            Moteur::M128(s) => s.pc as u64,
        }
    }
    pub fn compte(&self) -> u64 {
        match &self.moteur {
            Moteur::M32 { et, .. } => et.pas,
            Moteur::M64(s) => s.pas,
            Moteur::M128(s) => s.pas,
        }
    }
    /// R13 : le cadre de la fonction en cours (il monte quand une fonction rend la main)
    pub fn cadre(&self) -> u64 {
        match &self.moteur {
            Moteur::M32 { et, .. } => et.r[13] as u64,
            Moteur::M64(s) => s.r[13],
            Moteur::M128(s) => s.r[13] as u64,
        }
    }
    /// Une instruction ; Ok(true) quand le programme est fini.
    pub fn une_instruction(&mut self) -> Result<bool, String> {
        match &mut self.moteur {
            Moteur::M32 { mem, et, fichiers, entrees, dossier } => {
                let limite = et.pas + 1;
                match boucle(mem, et, entrees, limite, Some(dossier), fichiers, u32::MAX, None, 0) {
                    Ok(()) => Ok(true),
                    Err(e) if e.starts_with("limite") => Ok(false),
                    Err(e) => Err(e),
                }
            }
            Moteur::M64(s) => {
                s.pas_unique()?;
                Ok(s.arrete)
            }
            Moteur::M128(s) => {
                s.pas_unique()?;
                Ok(s.arrete)
            }
        }
    }
    /// Jusqu'au bout, d'un coup.
    pub fn jusqu_au_bout(&mut self) -> Result<(), String> {
        match &mut self.moteur {
            Moteur::M32 { mem, et, fichiers, entrees, dossier } => {
                boucle(mem, et, entrees, 5_000_000_000, Some(dossier), fichiers, u32::MAX, None, 0)
            }
            Moteur::M64(s) => s.executer(20_000_000_000),
            Moteur::M128(s) => s.executer(20_000_000_000),
        }
    }
}

/// Ce qu'a laissé un programme de la machine 64 bits ou de Lugus : ses pages (les vraies valeurs, sur 64 ou 128 bits)
/// et la fréquence que regarde chaque étage du cube. Le cube de l'atelier dessine des points de 32 bits : un point
/// profond #RRRRGGGGBBBBAAAA y paraît par l'octet fort de chaque voie (vers_point32), un point de matière de Lugus par
/// l'octet fort de ses trois couleurs et sa transparence (vers_point32_128) ; le clic et « mot » rendent la vraie
/// valeur.
pub struct Vue64 {
    // (étage, indice >> 16) -> les 65 536 mots de la page ; la fréquence (le cube) est l'indice >> 24
    pub pages: HashMap<(u32, u128), Box<[u128]>>,
    pub frequences: [u32; 4],
    // 64 : la SPU-64 ; 128 : Lugus
    pub largeur: u32,
}

impl Vue64 {
    pub fn depuis(s: &Spu64) -> Vue64 {
        let mut pages = HashMap::new();
        for e in 0..4usize {
            for (adr, mots) in s.pages_etage(e) {
                let v: Vec<u128> = mots.iter().map(|&x| x as u128).collect();
                pages.insert((e as u32, ((adr & 0xFFFF_FFFF_FFFF) >> 16) as u128), v.into_boxed_slice());
            }
        }
        Vue64 { pages, frequences: [0; 4], largeur: 64 }
    }
    pub fn depuis128(s: &Spu128) -> Vue64 {
        let mut pages = HashMap::new();
        for e in 0..4usize {
            for (i, mots) in s.pages_etage(e) {
                // les cubes au-delà de 2^32 restent hors de la vue (le cube de l'atelier les numérote sur 32 bits)
                if (i >> 24) >> 32 == 0 {
                    pages.insert((e as u32, i >> 16), mots.to_vec().into_boxed_slice());
                }
            }
        }
        Vue64 { pages, frequences: [0; 4], largeur: 128 }
    }
    pub fn nom(&self) -> &'static str {
        if self.largeur == 128 { "Lugus" } else { "SPU-64" }
    }
    /// Le mot de l'étage e à l'indice a (la fréquence au-dessus du bit 24).
    pub fn lit(&self, e: u32, a: u128) -> u128 {
        self.pages.get(&(e & 3, a >> 16)).map(|p| p[(a & 0xFFFF) as usize]).unwrap_or(0)
    }
    /// Un mot vu en point de 32 bits #RRGGBBAA.
    pub fn point32(&self, v: u128) -> u32 {
        if self.largeur == 128 { vers_point32_128(v) } else { vers_point32(v as u64) }
    }
    /// Ce que dit un mot de la machine.
    pub fn decoder(&self, e: u32, v: u128) -> Vec<String> {
        if self.largeur == 128 { decoder128(e, v) } else { decoder64(e, v as u64) }
    }
    /// Les fréquences (cubes) écrites de l'étage e.
    pub fn cubes(&self, e: u32) -> Vec<u32> {
        let mut v: Vec<u32> = self.pages.keys().filter(|k| k.0 == e).map(|k| (k.1 >> 8) as u32).collect();
        v.sort_unstable();
        v.dedup();
        v
    }
    /// L'étage e de la vue (mots de 32 bits) passe de son cube actuel au cube f.
    pub fn accorder(&mut self, mem: &Memoire, e: u32, f: u32) {
        let e = e & 3;
        let ancien = self.frequences[e as usize] as u128;
        for (k, _) in self.pages.iter().filter(|(k, _)| k.0 == e && k.1 >> 8 == ancien) {
            let base = ((k.1 & 0xFF) << 16) as u32;
            for i in 0..65536u32 {
                mem.ecrit(e, base | i, 0);
            }
        }
        self.frequences[e as usize] = f;
        for (k, p) in self.pages.iter().filter(|(k, _)| k.0 == e && k.1 >> 8 == f as u128) {
            let base = ((k.1 & 0xFF) << 16) as u32;
            for (i, &v) in p.iter().enumerate() {
                if v != 0 {
                    mem.ecrit(e, base | i as u32, self.point32(v));
                }
            }
        }
    }
    /// La mémoire que dessine le cube : chaque étage regarde son cube 0 ou, s'il est vide, le premier cube écrit
    /// (l'étage 0 garde le cube 0 : le code).
    pub fn memoire(&mut self) -> Memoire {
        let m = Memoire::new(false);
        for e in 0..4 {
            let c = self.cubes(e);
            let f = if e == 0 || c.is_empty() || c.contains(&0) { 0 } else { c[0] };
            self.frequences[e as usize] = u32::MAX;
            self.accorder(&m, e, f);
        }
        m
    }
}

/// Un mot de 64 bits en logique de Belnap : un seul logique (0 à 3) par son nom ; sinon ses 32 quits.
pub fn belnap64(v: u64) -> String {
    if v <= 3 {
        return ["inconnu", "faux", "vrai", "variable"][v as usize].to_string();
    }
    let q: Vec<char> = (0..32).rev().map(|k| ['·', 'f', 'v', '±'][((v >> (2 * k)) & 3) as usize]).collect();
    q.chunks(4).map(|c| c.iter().collect::<String>()).collect::<Vec<_>>().join(" ")
}

pub fn ligne64(nom: &str, v: u64) -> String {
    // en décimal : signé pour un petit négatif ; une adresse longue ou un grand mot reste sans signe
    let d = if (v as i64) < 0 && (v as i64) >= -(1i64 << 40) { (v as i64).to_string() } else { v.to_string() };
    format!("{:<5}{:>21}  #{:04X} {:04X} {:04X} {:04X}  {}\n", nom, d, v >> 48, (v >> 32) & 0xFFFF, (v >> 16) & 0xFFFF, v & 0xFFFF,
            belnap64(v))
}

/// Ce que dit un mot de 64 bits : nombre, point profond, adresse longue, instruction, logique.
pub fn decoder64(e: u32, v: u64) -> Vec<String> {
    let mut l = vec![format!("{} (signé : {})", v, v as i64), format!("point profond #{:016X} · vu en 32 bits #{:08X}", v, vers_point32(v))];
    if v >> 48 != 0 && v >> 62 != 0 && (v >> 48) & 0x3FFF == 0 {
        l.push(format!("adresse longue : étage {}, cube {}, #{:06X}", v >> 62, (v >> 24) & 0xFF_FFFF, v & 0xFF_FFFF));
    }
    if e == 0 && v >> 48 != 0 && v >> 56 == 0 {
        l.push(format!("instruction : op {:#04X}, d R{}, s R{}, t R{}, imm {}", v >> 48, (v >> 44) & 15, (v >> 40) & 15, (v >> 36) & 15,
                       v as u32 as i32));
    }
    let f = f64::from_bits(v);
    if v >> 52 != 0 && f.is_finite() && f.abs() > 1e-12 && f.abs() < 1e15 {
        l.push(format!("flottant_64 : {}", f));
    }
    l.push(format!("Belnap : {}", belnap64(v)));
    l
}

/// Le panneau de la machine 64 bits : registres sur 64 bits (décimal signé, quatre voies en hex, 32 quits de Belnap),
/// cadre de la fonction, sorties et console.
pub fn panneau64(s: &Spu64, t: &mut String) {
    let r = &s.r;
    t.push_str(&format!("{:<5}{:>21}  {:<20}  {}\n", "", "décimal", "#RRRR GGGG BBBB AAAA", "Belnap (32 quits : · f v ±)"));
    for k in 1..13 {
        t.push_str(&ligne64(&format!("R{}", k), r[k]));
    }
    let (z, c) = s.drapeaux();
    t.push_str(&format!("R13 cadre {:#X} · R14 pile {:#X} · Z {} · C {} · pc {}\n", r[13], r[14], z as u8, c as u8, s.pc));
    if r[13] != 0 && r[13] <= super::spu64::PILE {
        t.push_str("\ncadre de la fonction : variables locales (-1, -2…), paramètres (+2, +3…)\n");
        let lit = |k: i64| s.regarder((r[13] as i64 + k) as u64);
        for k in 1..9i64 {
            t.push_str(&ligne64(&format!("{}", -k), lit(-k)));
        }
        for k in 2..6i64 {
            t.push_str(&ligne64(&format!("+{}", k), lit(k)));
        }
    }
    if !s.sortie.is_empty() {
        let v: Vec<String> = s.sortie.iter().map(|v| v.to_string()).collect();
        t.push_str(&format!("\nsorties : {}\n", v.join(",")));
    }
    let c: String = s.texte.iter().filter_map(|&v| char::from_u32((v & 0x1F_FFFF) as u32)).collect();
    if !c.is_empty() {
        t.push_str("\nce que le programme a écrit :\n");
        for x in c.lines() {
            t.push_str(&format!("» {}\n", x));
        }
    }
}

/// La table du compilateur (adresse, ligne, adresse, ligne…) : la première adresse de chaque ligne -> la ligne (dès 0).
pub fn table_des_lignes(dbg: impl Iterator<Item = u64>) -> HashMap<u64, usize> {
    let v: Vec<u64> = dbg.collect();
    let mut debuts = HashMap::new();
    for p in v.chunks(2) {
        if p.len() == 2 && p[1] >= 1 {
            debuts.entry(p[0]).or_insert(p[1] as usize - 1);
        }
    }
    debuts
}


/// vtx-spu essai-pas64 PROG.vtx [ENTRÉES…] : ce que fait l'atelier sur la machine 64 bits, sans fenêtre. Pas à pas
/// ligne par ligne (F7), puis par-dessus les fonctions (F8), puis d'un coup (F5) : les trois doivent finir avec la même
/// console et les mêmes sorties que l'exécution complète ; puis la vue du cube (points de 32 bits) et le panneau.
pub fn essai(args: &[String]) {
    use super::machine64::{compiler64, nombres64, COMPLET64, PAS_A_PAS64, VTXC64};
    let fichier = match args.first() {
        Some(f) => f.clone(),
        None => {
            eprintln!("vtx-spu essai-pas64 PROG.vtx [ENTRÉES…]");
            std::process::exit(2);
        }
    };
    let source = std::fs::read_to_string(&fichier).expect("lecture impossible");
    let base = super::machine64::dossier_de64(&fichier);
    let entrees: Vec<u64> = args[1..].iter().filter_map(|x| x.parse().ok()).collect();
    let console = |s: &Spu64| -> String { s.texte.iter().filter_map(|&v| char::from_u32((v & 0x1F_FFFF) as u32)).collect() };
    // chaque exécution a son propre dossier vide : les cubes qu'elle range sur disque ne touchent ni le dossier du
    // programme ni l'exécution suivante
    let mut n_dossier = 0;
    let mut dossier_neuf = || {
        n_dossier += 1;
        let d = std::env::temp_dir().join(format!("essai-pas64-{}-{}", std::process::id(), n_dossier));
        let _ = std::fs::remove_dir_all(&d);
        std::fs::create_dir_all(&d).expect("dossier temporaire");
        d
    };
    // la référence : compilé comme F5, exécuté d'un trait
    let (m, _, _) = compiler64(&nombres64(VTXC64), &source, &base, COMPLET64, false).unwrap_or_else(|e| {
        eprint!("{}", e);
        std::process::exit(1)
    });
    let mut r = Spu64::nouveau();
    r.dossier = Some(dossier_neuf());
    r.charger(&m);
    r.entree.extend(entrees.iter().copied());
    let ref_fin = r.executer(20_000_000_000);
    println!("référence (F5 de l'atelier) : {} instructions{}", r.pas, match &ref_fin { Ok(()) => String::new(), Err(e) => format!(", arrêt : {}", e) });
    let (ref_texte, ref_sortie) = (console(&r), r.sortie.clone());
    let (mots, _, dbg) = compiler64(&nombres64(VTXC64), &source, &base, PAS_A_PAS64, true).expect("compilation pas à pas");
    let debuts = table_des_lignes(dbg.into_iter());
    println!("{} : {} mots (pas à pas), {} lignes repérées", fichier, mots.len(), debuts.len());
    let mut neuf = || {
        let mut s = Box::new(Spu64::nouveau());
        s.dossier = Some(dossier_neuf());
        s.charger(&mots);
        s.entree.extend(entrees.iter().copied());
        Pas { moteur: Moteur::M64(s), debuts: debuts.clone(), ligne: None, fini: false }
    };
    let mut bilan = Vec::new();
    for mode in ["F7", "F8", "F5"] {
        let mut d = neuf();
        let mut arrets = 0u64;
        let mut premieres = Vec::new();
        let fin;
        if mode == "F5" {
            fin = d.jusqu_au_bout();
        } else {
            let mut cadre = d.cadre();
            loop {
                match d.une_instruction() {
                    Ok(false) => {}
                    Ok(true) => {
                        fin = Ok(());
                        break;
                    }
                    Err(e) => {
                        fin = Err(e);
                        break;
                    }
                }
                if let Some(&l) = d.debuts.get(&d.pc()) {
                    if mode == "F7" || d.cadre() >= cadre {
                        arrets += 1;
                        cadre = d.cadre();
                        if premieres.len() < 12 {
                            premieres.push(l + 1);
                        }
                    }
                }
            }
        }
        let s = match &d.moteur {
            Moteur::M64(s) => s,
            _ => unreachable!(),
        };
        let ok = console(s) == ref_texte && s.sortie == ref_sortie && fin == ref_fin;
        println!("{} : {} arrêts{} · {} instructions · console et sorties {}", mode, arrets,
                 if premieres.is_empty() { String::new() } else { format!(" (lignes {:?}…)", premieres) }, s.pas,
                 if ok { "identiques à la référence" } else { "DIFFÉRENTES" });
        bilan.push(ok);
        if mode == "F7" {
            let mut t = String::new();
            panneau64(s, &mut t);
            println!("--- panneau à la fin\n{}---", t.lines().take(16).collect::<Vec<_>>().join("\n"));
            let mut vue = Vue64::depuis(s);
            let mem = vue.memoire();
            for e in 0..4u32 {
                let c = vue.cubes(e);
                if c.is_empty() {
                    continue;
                }
                // la vue (cube 0) doit montrer chaque mot non nul de la machine, vu en 32 bits
                let mut n = 0u64;
                let mut faux = 0u64;
                let f0 = vue.frequences[e as usize] as u64;
                for (k, p) in vue.pages.iter().filter(|(k, _)| k.0 == e && k.1 >> 8 == f0 as u128) {
                    for (i, &v) in p.iter().enumerate() {
                        if v != 0 {
                            n += 1;
                            if mem.lit(e, (((k.1 & 0xFF) << 16) as u32) | i as u32) != vue.point32(v) {
                                faux += 1;
                            }
                        }
                    }
                }
                println!("étage {} : cubes {:?} · vue sur le cube {} : {} mots non nuls, {} mal vus", e, &c[..c.len().min(8)], f0, n, faux);
                bilan.push(faux == 0);
                if c.len() > 1 {
                    // changer de cube : l'ancien disparaît de la vue, le nouveau paraît
                    let f = *c.iter().find(|&&x| x as u64 != f0).unwrap();
                    vue.accorder(&mem, e, f);
                    let reste = vue.pages.iter().filter(|(k, _)| k.0 == e && k.1 >> 8 == f as u128)
                        .all(|(k, p)| p.iter().enumerate().all(|(i, &v)| mem.lit(e, (((k.1 & 0xFF) << 16) as u32) | i as u32) == vue.point32(v)));
                    println!("   cube {} : {}", f, if reste { "bien vu" } else { "MAL VU" });
                    bilan.push(reste);
                    vue.accorder(&mem, e, f0 as u32);
                }
            }
            for l in decoder64(0, s.regarder(0)) {
                println!("@0[0] : {}", l);
            }
        }
    }
    if bilan.iter().all(|&x| x) {
        println!("conforme");
        for k in 1..=n_dossier {
            let _ = std::fs::remove_dir_all(std::env::temp_dir().join(format!("essai-pas64-{}-{}", std::process::id(), k)));
        }
    } else {
        println!("NON CONFORME");
        std::process::exit(1);
    }
}
