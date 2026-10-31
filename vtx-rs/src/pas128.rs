// Hors de Windows, seule la vérification (essai-pas128) s'en sert : une partie y reste inemployée.
#![cfg_attr(not(any(windows, feature = "verif_fenetre")), allow(dead_code))]
// Le pas à pas et les vues de Lugus (le SPU-128), sans fenêtre : l'atelier (fenetre.rs) s'en sert, et
// « vtx-spu essai-pas128 PROG.vtx » les vérifie partout (même sous Linux). Les vues du cube et le pas à pas eux-mêmes
// sont ceux de la machine 64 bits (pas64.rs : Vue64, Pas, Moteur::M128) ; ici, ce qui est propre aux mots de 128 bits.
use super::pas64::{table_des_lignes, Moteur, Pas, Vue64};
use super::spu128::Spu128;

/// Un point de matière de Lugus #RRRRRRRR_VVVVVVVV_BBBBBBBB_MMMMMMMM vu en point de 32 bits #RRGGBBAA : l'octet fort de
/// chaque couleur, et la transparence (le codon 3 de la matière, 6 bits) en alpha. Un mot dont les 64 bits hauts sont
/// nuls est un mot de la machine 64 bits (un point profond, ou un nombre) : il est vu comme elle le voit.
pub fn vers_point32_128(v: u128) -> u32 {
    if v >> 64 == 0 {
        return super::machine64::vers_point32(v as u64);
    }
    let t = ((v >> 12) & 63) as u32;
    (((v >> 120) & 0xFF) << 24 | ((v >> 88) & 0xFF) << 16 | ((v >> 56) & 0xFF) << 8) as u32 | (t * 255 / 63)
}

/// Le même point vu en 0x00RRGGBB, pour l'image d'un programme qui dessine.
pub fn point128(v: u128) -> u32 {
    if v >> 64 == 0 {
        return super::toile::point64(v as u64);
    }
    (((v >> 120) & 0xFF) << 16 | ((v >> 88) & 0xFF) << 8 | ((v >> 56) & 0xFF)) as u32
}

/// Un mot de 128 bits en logique de Belnap : un seul logique (0 à 3) par son nom ; sinon ses 64 quits.
pub fn belnap128(v: u128) -> String {
    if v <= 3 {
        return ["inconnu", "faux", "vrai", "variable"][v as usize].to_string();
    }
    let q: Vec<char> = (0..64).rev().map(|k| ['·', 'f', 'v', '±'][((v >> (2 * k)) & 3) as usize]).collect();
    q.chunks(8).map(|c| c.iter().collect::<String>()).collect::<Vec<_>>().join(" ")
}

/// Un registre ou un mot : décimal (signé pour un petit négatif), quatre voies de 32 bits en hex.
pub fn ligne128(nom: &str, v: u128) -> String {
    let d = if (v as i128) < 0 && (v as i128) >= -(1i128 << 40) { (v as i128).to_string() } else { v.to_string() };
    format!("{:<5}{:>40}  #{:08X} {:08X} {:08X} {:08X}\n", nom, d, v >> 96, (v >> 64) & 0xFFFF_FFFF, (v >> 32) & 0xFFFF_FFFF,
            v & 0xFFFF_FFFF)
}

const NOMS_CODONS: [&str; 6] = ["état", "reflet", "lumière", "transparence", "profondeur", "rugosité"];

/// Ce que dit un mot de Lugus : nombre, point de matière (couleurs et codons), adresse, demi-instructions, flottant,
/// logique.
pub fn decoder128(e: u32, v: u128) -> Vec<String> {
    let mut l = vec![format!("{} (signé : {})", v, v as i128)];
    if e != 0 && v >> 64 != 0 {
        let m = v as u32;
        let codons: Vec<String> = [(30u32, 2u32), (24, 6), (18, 6), (12, 6), (6, 6), (0, 6)].iter().enumerate()
            .map(|(k, &(d, n))| format!("{} {}", NOMS_CODONS[k], (m >> d) & ((1 << n) - 1))).collect();
        l.push(format!("point de matière : r #{:08X} v #{:08X} b #{:08X} · {} · vu en 32 bits #{:08X}", v >> 96,
                       (v >> 64) & 0xFFFF_FFFF, (v >> 32) & 0xFFFF_FFFF, codons.join(", "), vers_point32_128(v)));
        if v >> 126 != 0 && (v >> 120) & 0x3F == 0 {
            l.push(format!("adresse longue : étage {}, indice {}", v >> 126, v & ((1u128 << 120) - 1)));
        }
    } else if v >> 64 == 0 {
        let w = v as u64;
        l.push(format!("point profond #{:016X} · vu en 32 bits #{:08X}", w, super::machine64::vers_point32(w)));
        if w >> 62 != 0 && (w >> 48) & 0x3FFF == 0 {
            l.push(format!("adresse courte : étage {}, indice {}", w >> 62, w & 0xFFFF_FFFF_FFFF));
        }
    }
    if e == 0 {
        for (k, h) in [(v >> 64) as u64, v as u64].iter().enumerate() {
            if h >> 48 != 0 && h >> 56 == 0 {
                let largeur = match (h >> 32) & 15 { 0 => "", 1 => ".64", 2 => ".32", _ => ".?" };
                l.push(format!("demi-instruction {} : op {:#04X}{}, d R{}, s R{}, t R{}, imm {}", if k == 0 { "haute" } else { "basse" },
                               h >> 48, largeur, (h >> 44) & 15, (h >> 40) & 15, (h >> 36) & 15, *h as u32 as i32));
            }
        }
    }
    let q = crate::qflot128::Q128;
    if q.etat(v) == 1 || q.etat(v) == 2 {
        let d = f64::from_bits(q.vers_ieee(v) as u64);
        if d.is_finite() && d != 0.0 && d.abs() > 1e-12 && d.abs() < 1e15 {
            l.push(format!("flottant (128 bits, quaternaire) : ≈ {}", d));
        }
    }
    l.push(format!("Belnap : {}", belnap128(v)));
    l
}

/// Le panneau de Lugus : registres sur 128 bits (décimal, quatre voies), cadre de la fonction, sorties et console.
pub fn panneau128(s: &Spu128, t: &mut String) {
    let r = &s.r;
    t.push_str(&format!("{:<5}{:>40}  {}\n", "", "décimal", "les quatre voies de 32 bits (r v b matière)"));
    for k in 1..13 {
        t.push_str(&ligne128(&format!("R{}", k), r[k]));
    }
    let (z, c) = s.drapeaux();
    t.push_str(&format!("R13 cadre {:#X} · R14 pile {:#X} · Z {} · C {} · pc {} (demi-mots)\n", r[13], r[14], z as u8, c as u8, s.pc));
    if r[13] != 0 && r[13] <= super::spu128::PILE {
        t.push_str("\ncadre de la fonction : variables locales (-1, -2…), paramètres (+2, +3…)\n");
        let lit = |k: i128| s.regarder((r[13] as i128 + k) as u128);
        for k in 1..9i128 {
            t.push_str(&ligne128(&format!("{}", -k), lit(-k)));
        }
        for k in 2..6i128 {
            t.push_str(&ligne128(&format!("+{}", k), lit(k)));
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

/// L'image d'un programme de Lugus (ecran(l, h) : @3[14680058], @3[14680059] ; les points dans l'étage 1).
pub fn image128(s: &Spu128) -> Option<(usize, usize, Vec<u32>)> {
    let (l, h) = (s.regarder((3u128 << 62) | 14_680_058), s.regarder((3u128 << 62) | 14_680_059));
    if !((1..=4096).contains(&l) && (1..=4096).contains(&h) && l * h <= 1 << 24) {
        return None;
    }
    let (l, h) = (l as usize, h as usize);
    let px = (0..l * h).map(|i| point128(s.regarder((1u128 << 62) | i as u128))).collect();
    Some((l, h, px))
}

/// Le service 12 de Lugus (presenter) : l'image vers la sortie de la toile.
pub fn presenter128(s: &Spu128) -> u128 {
    match image128(s) {
        Some((l, h, px)) => if super::toile::montrer(l, h, &px) { 0 } else { 1 },
        None => u64::MAX as u128,
    }
}

/// vtx-spu essai-pas128 PROG.vtx [ENTRÉES…] : ce que fait l'atelier sur Lugus, sans fenêtre. Pas à pas ligne par ligne
/// (F7), puis par-dessus les fonctions (F8), puis d'un coup (F5) : les trois doivent finir avec la même console et les
/// mêmes sorties que l'exécution complète ; puis la vue du cube (points de 32 bits) et le panneau.
pub fn essai(args: &[String]) {
    use super::machine128::{compiler128, dossier_de128, nombres128, COMPLET128, PAS_A_PAS128, VTXC128};
    let fichier = match args.first() {
        Some(f) => f.clone(),
        None => {
            eprintln!("vtx-spu essai-pas128 PROG.vtx [ENTRÉES…]");
            std::process::exit(2);
        }
    };
    let source = std::fs::read_to_string(&fichier).expect("lecture impossible");
    let base = dossier_de128(&fichier);
    let entrees: Vec<u128> = args[1..].iter().filter_map(|x| x.parse().ok()).collect();
    let console = |s: &Spu128| -> String { s.texte.iter().filter_map(|&v| char::from_u32((v & 0x1F_FFFF) as u32)).collect() };
    let mut n_dossier = 0;
    let mut dossier_neuf = || {
        n_dossier += 1;
        let d = std::env::temp_dir().join(format!("essai-pas128-{}-{}", std::process::id(), n_dossier));
        let _ = std::fs::remove_dir_all(&d);
        std::fs::create_dir_all(&d).expect("dossier temporaire");
        d
    };
    let compilateur = nombres128(VTXC128);
    let (m, _, _) = compiler128(&compilateur, &source, &base, COMPLET128, false).unwrap_or_else(|e| {
        eprint!("{}", e);
        std::process::exit(1)
    });
    let mut r = Spu128::nouveau();
    r.dossier = Some(dossier_neuf());
    r.charger(&m);
    r.entree.extend(entrees.iter().copied());
    let ref_fin = r.executer(20_000_000_000);
    println!("référence (F5 de l'atelier) : {} instructions{}", r.pas, match &ref_fin { Ok(()) => String::new(), Err(e) => format!(", arrêt : {}", e) });
    let (ref_texte, ref_sortie) = (console(&r), r.sortie.clone());
    let (mots, _, dbg) = compiler128(&compilateur, &source, &base, PAS_A_PAS128, true).expect("compilation pas à pas");
    let debuts = table_des_lignes(dbg.into_iter().map(|x| x as u64));
    println!("{} : {} mots (pas à pas), {} lignes repérées", fichier, mots.len(), debuts.len());
    let mut neuf = || {
        let mut s = Box::new(Spu128::nouveau());
        s.dossier = Some(dossier_neuf());
        s.charger(&mots);
        s.entree.extend(entrees.iter().copied());
        Pas { moteur: Moteur::M128(s), debuts: debuts.clone(), ligne: None, fini: false }
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
            Moteur::M128(s) => s,
            _ => unreachable!(),
        };
        let ok = console(s) == ref_texte && s.sortie == ref_sortie && fin == ref_fin;
        println!("{} : {} arrêts{} · {} instructions · console et sorties {}", mode, arrets,
                 if premieres.is_empty() { String::new() } else { format!(" (lignes {:?}…)", premieres) }, s.pas,
                 if ok { "identiques à la référence" } else { "DIFFÉRENTES" });
        bilan.push(ok);
        // le pas à pas s'arrête au moins une fois par ligne exécutée
        if mode == "F7" {
            bilan.push(arrets > 0);
            let mut t = String::new();
            panneau128(s, &mut t);
            println!("--- panneau à la fin\n{}---", t.lines().take(16).collect::<Vec<_>>().join("\n"));
            let mut vue = Vue64::depuis128(s);
            let mem = vue.memoire();
            for e in 0..4u32 {
                let c = vue.cubes(e);
                if c.is_empty() {
                    continue;
                }
                let mut n = 0u64;
                let mut faux = 0u64;
                let f0 = vue.frequences[e as usize] as u128;
                for (k, p) in vue.pages.iter().filter(|(k, _)| k.0 == e && k.1 >> 8 == f0) {
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
            }
            if let Some((l, h, px)) = image128(s) {
                let couleurs: std::collections::HashSet<u32> = px.iter().copied().collect();
                println!("image : {} × {}, {} couleurs (la première : #{:06X})", l, h, couleurs.len(), px[0]);
            }
            for l in decoder128(0, s.regarder(0)) {
                println!("@0[0] : {}", l);
            }
        }
    }
    if bilan.iter().all(|&x| x) {
        println!("conforme");
        for k in 1..=n_dossier {
            let _ = std::fs::remove_dir_all(std::env::temp_dir().join(format!("essai-pas128-{}-{}", std::process::id(), k)));
        }
    } else {
        println!("NON CONFORME");
        std::process::exit(1);
    }
}
