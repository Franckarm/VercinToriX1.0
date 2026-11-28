// 0.852 : la forge écrite en vtx, sans Python (lugus forger) : vtxc128 écrit le Rust des fonctions du programme
// (code.rs) ; lugus l'assemble avec le noyau de la forge (forge/noyau_forge128.rs et les modules qu'il recopie), les mots
// et la fin commune (forge/queue_vtx.rs, la copie de forge128.queue_programme sans zones ni noyaux), puis rustc.
// Tout est embarqué dans lugus : un programme vtx devient un exécutable natif sans rien d'autre que rustc.

use crate::machine128::{nombres128, passer_vtxc128_rust, VTXC128};

const NOYAU: &str = include_str!("../../forge/noyau_forge128.rs");
const QUEUE: &str = include_str!("../../forge/queue_vtx.rs");
const MODULES: [(&str, &str); 7] = [
    ("qflot128", include_str!("qflot128.rs")),
    ("spu128", include_str!("spu128.rs")),
    ("hote", include_str!("hote.rs")),
    ("miroir", include_str!("miroir.rs")),
    ("taranis_vk", include_str!("taranis_vk.rs")),
    ("gif", include_str!("gif.rs")),
    ("sortie", include_str!("sortie.rs")),
];
const ATTRIBUTS: &str = "#![allow(unused_mut, unused_variables, unused_assignments, unreachable_code, unused_parens, dead_code, \
                         clippy::all, non_snake_case, unused_imports, unused_labels, unused_braces)]";

/// le noyau (comme noyau() de forge128.py) : les modules recopiés, les deux gènes que l'environnement impose
pub fn noyau() -> String {
    let mods: Vec<String> = MODULES.iter()
        .map(|(m, texte)| format!("#[allow(dead_code, unused_imports, unused_variables)]\nmod {} {{\n{}\n}}\n", m, texte)).collect();
    let mut n = NOYAU.to_string();
    if std::env::var("VTX_EPISSAGE").map_or(false, |v| v == "rapide") {
        n = n.replacen("const EPISSAGE_RAPIDE_FORGE: bool = false;", "const EPISSAGE_RAPIDE_FORGE: bool = true;", 1);
    }
    if std::env::var("VTX_CARTE_DIRECTE").map_or(false, |v| v == "1") {
        n = n.replacen("const CARTE_DIRECTE: bool = false;", "const CARTE_DIRECTE: bool = true;", 1);
    }
    format!("{}\n{}", ATTRIBUTS, n.replacen("// @MODULES@", &mods.join("\n"), 1))
}

/// le programme Rust complet, ou ce que vtxc128 ne sait pas encore écrire
pub fn source_rust(source: &str, base: &str, nom: &str) -> Result<String, String> {
    let (mots_t, rs) = passer_vtxc128_rust(&nombres128(VTXC128), source, base)?;
    if rs.starts_with("// pas encore") {
        return Err(rs);
    }
    let mots = nombres128(mots_t.split(';').next().unwrap_or(""));
    let liste: Vec<String> = mots.iter().map(|w| w.to_string()).collect();
    Ok(format!("{}\nconst NOM: &str = \"{}\";\n{}\nstatic MOTS: [u128; {}] = [{}];\n\n{}fn main() {{\n    let a: Vec<String> = std::env::args().collect();\n    lancer(&a[1..]);\n}}\n",
               noyau(), nom.replace('"', "_"), rs, mots.len(), liste.join(","), QUEUE))
}

/// forge le programme : le Rust (écrit à côté si rs est donné), puis rustc ; rend le chemin de l'exécutable
pub fn forger(fichier: &str, sortie: Option<String>, rs: Option<String>, natif: bool) -> Result<String, String> {
    let source = std::fs::read_to_string(fichier).map_err(|e| format!("lecture de {} impossible : {}", fichier, e))?;
    let p = std::path::Path::new(fichier);
    let nom = p.file_stem().map(|x| x.to_string_lossy().into_owned()).unwrap_or_else(|| "programme".into());
    let ext = if cfg!(windows) { ".exe" } else { "" };
    let sortie = sortie.unwrap_or_else(|| p.with_file_name(format!("{}.lugus{}", nom, ext)).to_string_lossy().into_owned());
    let code = source_rust(&source, &crate::machine128::dossier_de128(fichier), &nom)?;
    let chemin_rs = match rs {
        Some(r) => r,
        None => std::env::temp_dir().join(format!("forge-lugus-{}.rs", std::process::id())).to_string_lossy().into_owned(),
    };
    std::fs::write(&chemin_rs, &code).map_err(|e| e.to_string())?;
    let mut o = vec!["--edition", "2021", "-C", "opt-level=3", "-C", "panic=abort", "-C", "codegen-units=1"];
    if natif {
        o.extend(["-C", "target-cpu=native"]);
    }
    let r = std::process::Command::new("rustc").args(&o).arg("-o").arg(&sortie).arg(&chemin_rs).output()
        .map_err(|e| format!("rustc introuvable ({}) : la forge passe par le compilateur Rust (rustup.rs)", e))?;
    if !r.status.success() {
        let e = String::from_utf8_lossy(&r.stderr);
        return Err(format!("rustc a refusé le programme forgé ({}) :\n{}", chemin_rs, &e[e.len().saturating_sub(3000)..]));
    }
    Ok(sortie)
}
