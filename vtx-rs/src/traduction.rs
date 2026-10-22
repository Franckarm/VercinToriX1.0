// Traduction d'un programme du SPU en Rust, compilé ensuite par rustc en code natif (LLVM).
// Chaque bloc d'instructions (de la cible d'un saut au saut suivant) devient une branche d'un « match » sur le
// compteur ordinal ; les registres deviennent des variables locales, que le compilateur garde dans les registres de la
// machine. Le code est statique : on suit les sauts depuis l'adresse 0 pour ne traduire que les instructions (les
// données et les textes rangés après le code ne sont jamais décodés). Un RET saute à l'adresse lue sur la pile : le
// « match » la retrouve parmi les points de retour (l'instruction qui suit chaque CALL).
// Les accords de la partition sont joués comme par la machine interprétée : une adresse où commence un accord confie
// ses mesures à jouer_accord, qui lance les tâches d'une mesure sur plusieurs cylindres (fils) ; chaque tâche est la
// même fonction, lancée à l'adresse de la tâche et arrêtée à son adresse de fin.
use std::collections::BTreeMap;

use std::collections::BTreeSet;
use std::fmt::Write;

const ADR: u32 = 0x00FF_FFFF;

fn champs(w: u32) -> (u32, u32, u32, u32) {
    (w >> 24, (w >> 16) & 255, (w >> 8) & 255, (w & 255) >> 6)
}

/// L'adresse d'un saut : 20 bits (g, b, puis les 4 bits bas du dernier octet).
fn cible(w: u32) -> u32 {
    ((w & 15) << 16) | (((w >> 16) & 255) << 8) | ((w >> 8) & 255)
}

fn reg(n: u32) -> String {
    if n == 0 { "0u32".to_string() } else { format!("r{}", n) }
}

/// Les adresses de la table des accords : début de chaque accord (et son numéro + 1), et toutes les bornes.
fn adresses_accords(table: &[u32]) -> (BTreeMap<u32, u32>, BTreeSet<u32>) {
    let mut debuts = BTreeMap::new();
    let mut bornes = BTreeSet::new();
    let mut it = table.iter().copied();
    let n = it.next().unwrap_or(0);
    for k in 0..n {
        let debut = it.next().unwrap_or(0);
        let fin = it.next().unwrap_or(0);
        debuts.insert(debut, k + 1);
        bornes.insert(debut);
        bornes.insert(fin);
        let nm = it.next().unwrap_or(0);
        for _ in 0..nm {
            let nt = it.next().unwrap_or(0);
            for _ in 0..nt {
                bornes.insert(it.next().unwrap_or(0));
                bornes.insert(it.next().unwrap_or(0));
            }
        }
    }
    (debuts, bornes)
}

/// Adresses atteintes, cibles de sauts et points de retour.
fn analyser(mots: &[u32], bornes: &BTreeSet<u32>) -> Result<(BTreeSet<u32>, BTreeSet<u32>), String> {
    let mot = |a: u32| -> u32 { mots.get(a as usize).copied().unwrap_or(0) };
    let mut vues = BTreeSet::new();
    let mut tetes = BTreeSet::new();
    let mut pile = vec![0u32];
    tetes.insert(0);
    // les bornes des accords et des tâches commencent un bloc (on s'y arrête ou on y lance un accord)
    for &b in bornes {
        tetes.insert(b);
        pile.push(b);
    }
    while let Some(pc) = pile.pop() {
        if !vues.insert(pc) {
            continue;
        }
        let (op, _, _, _) = champs(mot(pc));
        let suivant = (pc + 1) & ADR;
        match op {
            0x0A => pile.push((pc + 2) & ADR),
            0x30 => {
                let t = cible(mot(pc));
                tetes.insert(t);
                pile.push(t);
            }
            0x31 | 0x32 | 0x35 | 0x36 | 0x33 => {
                let t = cible(mot(pc));
                tetes.insert(t);
                tetes.insert(suivant);
                pile.push(t);
                pile.push(suivant);
            }
            0x34 | 0x3F | 0x22 => {}
            _ => pile.push(suivant),
        }
    }
    // une instruction qui suit un saut, un RET ou un HALT commence un bloc
    for &pc in &vues {
        let (op, _, _, _) = champs(mot(pc));
        if matches!(op, 0x30 | 0x31 | 0x32 | 0x33 | 0x34 | 0x35 | 0x36 | 0x3F) {
            tetes.insert((pc + 1) & ADR);
        }
    }
    Ok((vues, tetes))
}

/// La fonction traduite : elle part de et.pc avec les registres de et, et s'arrête au HALT ou à l'adresse arret
/// (fin d'une tâche) ; elle rend le nombre d'instructions jouées.
pub fn traduire(mots: &[u32], nom: &str, table: &[u32]) -> Result<String, String> {
    let mot = |a: u32| -> u32 { mots.get(a as usize).copied().unwrap_or(0) };
    let (debuts, bornes) = adresses_accords(table);
    let (vues, tetes) = analyser(mots, &bornes)?;
    let mut s = String::new();
    writeln!(s, "fn {}(mem: &Memoire, es: &mut Es, max_pas: u64, et: &mut Regs, arret: u32, part: Option<&Partition>, actif: u32) -> Result<u64, String> {{", nom).unwrap();
    for i in 1..16 {
        writeln!(s, "    let mut r{}: u32 = et.r[{}];", i, i).unwrap();
    }
    s.push_str("    let (mut z, mut c) = (et.z, et.c);\n    let mut pas: u64 = 0;\n    let mut pc: u32 = et.pc;\n    loop {\n");
    // l'arrêt d'une tâche ne peut tomber que sur une borne de la table : le test n'est fait qu'à ces adresses
    s.push_str("        match pc {\n");
    for &debut in tetes.iter().filter(|t| vues.contains(t)) {
        // les instructions du bloc
        let mut corps = String::new();
        let mut n: u64 = 0;
        let mut pc = debut;
        let mut fin = String::new();
        loop {
            let w = mot(pc);
            let (op, g, b, etage) = champs(w);
            let rd = g >> 4;
            let ra = reg(g & 15);
            let rb = reg(b >> 4);
            let decal = if b > 127 { b as i64 - 256 } else { b as i64 };
            let mut suivant = (pc + 1) & ADR;
            n += 1;
            let ecrire = |v: &str| -> String {
                if rd == 0 { format!("{{ let _v: u32 = {}; }}", v) } else { format!("r{} = {};", rd, v) }
            };
            let res = |v: &str| -> String {
                if rd == 0 {
                    format!("{{ let v: u32 = {}; z = v == 0; c = false; }}", v)
                } else {
                    format!("{{ let v: u32 = {}; r{} = v; z = v == 0; c = false; }}", v, rd)
                }
            };
            let ligne = match op {
                0x00 => String::new(),
                0x01 | 0x06 => {
                    let y = if op == 0x01 { format!("{} as u64", rb) } else { format!("{}u64", b) };
                    format!("{{ let s = {} as u64 + {}; {} z = (s & MASK) == 0; c = s > MASK; }}", ra, y, ecrire("s as u32"))
                }
                0x02 | 0x07 | 0x0E => {
                    let y = if op == 0x07 { format!("{}u32", b) } else { rb.clone() };
                    let w_ = if op == 0x0E { String::new() } else { ecrire("v") };
                    format!("{{ let a = {}; let y = {}; let v = a.wrapping_sub(y); {} z = v == 0; c = a < y; }}", ra, y, w_)
                }
                0x03 => res(&format!("{}.wrapping_mul({})", ra, rb)),
                0x04 => res(&format!("{} << 2", ra)),
                0x05 => res(&format!("{} >> 2", ra)),
                0x08 => res(&format!("{} << ({} & 31)", ra, rb)),
                0x09 => res(&format!("{} >> ({} & 31)", ra, rb)),
                0x0A => {
                    let v = mot(suivant);
                    suivant = (suivant + 1) & ADR;
                    res(&format!("{}u32", v))
                }
                0x0B => ecrire(&ra),
                0x0C => res(&format!("{{ let (a, y) = ({}, {}); if y == 0 {{ u32::MAX }} else {{ a / y }} }}", ra, rb)),
                0x0D => res(&format!("{{ let (a, y) = ({}, {}); if y == 0 {{ a }} else {{ a % y }} }}", ra, rb)),
                0x10 | 0x11 | 0x13 => res(&format!("quits({}, {}, {})", ra, rb, op)),
                0x12 => res(&format!("!{}", ra)),
                0x14 => res(&format!("{} & {}", ra, rb)),
                0x15 => res(&format!("{} | {}", ra, rb)),
                0x16 => res(&format!("{} ^ {}", ra, rb)),
                0x20 => res(&format!("mem.lit({}, {})", etage, ra)),
                0x21 => format!("mem.ecrit({}, {}, {});", etage, reg(rd), ra),
                0x22 => "return Err(\"DMA non implémentée\".into());".to_string(),
                0x23 => ecrire("es.entree()"),
                0x24 => format!("es.sorties.push({});", ra),
                0x51 => res(&format!("es.entc({})", ra)),
                0x52 => format!("es.sorc({}, {});", ra, rb),
                0x53 => res(&format!("es.sys(mem, {}, {})", ra, rb)),
                0x25 => ecrire(&format!("mem.lit(0, (r13 as i64 + {}) as u32)", decal)),
                0x26 => format!("mem.ecrit(0, (r13 as i64 + {}) as u32, {});", decal, reg(rd)),
                0x27 => format!("{{ let v = {}; r14 = r14.wrapping_sub(1) & ADR; mem.ecrit(0, r14, v); }}", ra),
                0x28 => format!("{{ let v = mem.lit(0, r14); r14 = (r14 + 1) & ADR; {} }}", ecrire("v")),
                0x29 => res(&format!("mem.lit({} & 3, {})", rb, ra)),
                0x2A => format!("mem.ecrit({} & 3, {}, {});", rb, reg(rd), ra),
                0x56 => res(&format!("(({a} & {b}) & 0xAAAA_AAAA) | (({a} | {b}) & 0x5555_5555)", a = ra, b = rb)),
                0x57 => res(&format!("(({a} | {b}) & 0xAAAA_AAAA) | (({a} & {b}) & 0x5555_5555)", a = ra, b = rb)),
                0x58 => res(&format!("(({a} & 0xAAAA_AAAA) >> 1) | (({a} & 0x5555_5555) << 1)", a = ra)),
                0x59 => res(&format!("!((({a} & 0xAAAA_AAAA) >> 1) | (({a} & 0x5555_5555) << 1))", a = ra)),
                0x5A => res(&format!("({} >> (({} & 15) * 2)) & 3", ra, rb)),
                0x54 => res(&format!("(mem.lit({}, {}.wrapping_add({} >> 4) & ADR) >> (({} & 15) * 2)) & 3", etage, ra, rb, rb)),
                0x55 => format!("{{ let a = {}.wrapping_add({} >> 4) & ADR; let d = ({} & 15) * 2; \
                                 let v = (mem.lit({}, a) & !(3u32 << d)) | (({} & 3) << d); mem.ecrit({}, a, v); }}",
                                ra, rb, rb, etage, reg(rd), etage),
                0x38 => res(&format!("dot({}, {}) as u32", ra, rb)),
                0x39 => "gemv(mem, r14);".to_string(),
                0x40 => res(&format!("fb(f({}) + f({}))", ra, rb)),
                0x41 => res(&format!("fb(f({}) - f({}))", ra, rb)),
                0x42 => res(&format!("fb(f({}) * f({}))", ra, rb)),
                0x43 => res(&format!("fb(f({}) / f({}))", ra, rb)),
                0x44 => res(&format!("(f({}) == f({})) as u32", ra, rb)),
                0x45 => res(&format!("(f({}) < f({})) as u32", ra, rb)),
                0x46 => res(&format!("(f({}) <= f({})) as u32", ra, rb)),
                0x47 => res(&format!("fb(f({}).sqrt())", ra)),
                0x48 => res(&format!("fb({} as f32)", ra)),
                0x49 => res(&format!("fb({} as i32 as f32)", ra)),
                0x4A => res(&format!("f({}) as i32 as u32", ra)),
                0x4B => res(&format!("f({}).round_ties_even() as i32 as u32", ra)),
                0x4C => format!("{{ let s = {} as u64 + {} as u64 + c as u64; {} z = (s & MASK) == 0; c = s > MASK; }}", ra, rb, ecrire("s as u32")),
                0x4D => format!("{{ let a = {} as u64; let y = {} as u64 + c as u64; let v = a.wrapping_sub(y) as u32; {} z = v == 0; c = a < y; }}",
                                ra, rb, ecrire("v")),
                0x4E => res(&format!("(({} as u64 * {} as u64) >> 32) as u32", ra, rb)),
                0x4F => res(&format!("{{ let x = {} ^ {}; !(x | (x >> 1)) & 0x5555_5555 }}", ra, rb)),
                0x50 => res(&format!("{}.count_ones()", ra)),
                // sauts : fin du bloc
                0x30 => { fin = format!("pc = {};", cible(w)); String::new() }
                0x31 | 0x32 | 0x35 | 0x36 => {
                    let cond = match op { 0x31 => "z", 0x32 => "!z", 0x35 => "c", _ => "!c" };
                    fin = format!("pc = if {} {{ {} }} else {{ {} }};", cond, cible(w), suivant);
                    String::new()
                }
                0x33 => {
                    fin = format!("r14 = r14.wrapping_sub(1) & ADR; mem.ecrit(0, r14, {}); pc = {};", suivant, cible(w));
                    String::new()
                }
                0x34 => { fin = "pc = mem.lit(0, r14); r14 = (r14 + 1) & ADR;".to_string(); String::new() }
                0x3F => { fin = "return Ok(pas);".to_string(); String::new() }
                _ => format!("return Err(format!(\"code d'opération inconnu {:#04x} à l'adresse {}\"));", op, pc),
            };
            if !ligne.is_empty() {
                writeln!(corps, "                {}", ligne).unwrap();
            }
            if !fin.is_empty() || op == 0x22 {
                break;
            }
            pc = suivant;
            if tetes.contains(&pc) || !vues.contains(&pc) {
                fin = format!("pc = {};", pc);
                break;
            }
        }
        writeln!(s, "            {} => {{", debut).unwrap();
        if bornes.contains(&debut) {
            writeln!(s, "                if pc == arret {{ et.r = [0, r1, r2, r3, r4, r5, r6, r7, r8, r9, r10, r11, r12, r13, r14, r15]; et.pc = pc; et.z = z; et.c = c; return Ok(pas); }}").unwrap();
        }
        if let Some(&numero) = debuts.get(&debut) {
            // un accord commence ici : ses tâches sont jouées par jouer_accord (sauf si c'est lui qu'on joue déjà)
            writeln!(s, "                if let Some(p) = part {{ if actif != {} {{", numero).unwrap();
            writeln!(s, "                    *et = Regs {{ r: [0, r1, r2, r3, r4, r5, r6, r7, r8, r9, r10, r11, r12, r13, r14, r15], pc, z, c }};").unwrap();
            writeln!(s, "                    pas += jouer_accord({}, mem, es, et, {}, max_pas, p)?;", nom, numero).unwrap();
            writeln!(s, "                    r13 = et.r[13]; r14 = et.r[14]; pc = et.pc; continue;").unwrap();
            writeln!(s, "                }} }}").unwrap();
        }
        writeln!(s, "                if pas + {} > max_pas {{ return Err(format!(\"limite de {{}} instructions atteinte\", max_pas)); }}", n).unwrap();
        writeln!(s, "                pas += {};", n).unwrap();
        s.push_str(&corps);
        writeln!(s, "                {}", fin).unwrap();
        writeln!(s, "            }}").unwrap();
    }
    s.push_str("            _ => return Err(format!(\"saut vers l'adresse {}, qui n'est pas du code traduit\", pc)),\n        }\n    }\n}\n");
    Ok(s)
}

/// Un programme complet, prêt pour rustc : le noyau, les mots du programme (code, données, textes), la fonction
/// traduite, et un « main » qui prend les entrées sur la ligne de commande, comme « vtx programme.vtx ».
pub fn programme_complet(mots: &[u32], table: &[u32]) -> Result<String, String> {
    let mut s = String::from(include_str!("noyau_natif.rs"));
    s.push_str("\nstatic MOTS: [u32; ");
    write!(s, "{}] = [", mots.len()).unwrap();
    for (i, w) in mots.iter().enumerate() {
        if i % 16 == 0 {
            s.push_str("\n    ");
        }
        write!(s, "{}, ", w).unwrap();
    }
    s.push_str("\n];\n\n");
    write!(s, "static TABLE: [u32; {}] = {:?};\n\n", table.len(), table).unwrap();
    s.push_str(&traduire(mots, "programme", table)?);
    s.push_str(r#"
fn main() {
    let entrees: Vec<u32> = std::env::args().skip(1).map(|t| t.parse::<u64>().expect("entrée : un nombre") as u32).collect();
    let mut mem = Memoire::new(false);
    charger(&mut mem, &MOTS);
    let mut es = Es::new(entrees, std::env::current_dir().ok());
    let mut et = Regs { r: [0; 16], pc: 0, z: false, c: false };
    et.r[14] = PILE_HAUT;
    let cylindres = cylindres_machine();
    let part = if TABLE.first().copied().unwrap_or(0) == 0 || cylindres <= 1 { None } else { Some(lire_partition(&TABLE, cylindres)) };
    match programme(&mem, &mut es, u64::MAX, &mut et, u32::MAX, part.as_ref(), 0) {
        Ok(_) => {
            if !es.sorties.is_empty() {
                let s: Vec<String> = es.sorties.iter().map(|v| v.to_string()).collect();
                println!("{}", s.join(","));
            }
            let t: String = es.texte.iter().filter_map(|&v| char::from_u32(v & 0x1F_FFFF)).collect();
            print!("{}", t);
            let _ = std::io::stdout().flush();
        }
        Err(e) => {
            eprintln!("erreur : {}", e);
            std::process::exit(1);
        }
    }
}
"#);
    Ok(s)
}

/// Tout un corpus dans un seul programme (pour la vérification) : une fonction par programme, et un « main » qui relit
/// le fichier du corpus et écrit « instructions|sorties|mémoire » comme « vtx-spu corpus ».
pub fn corpus_complet(lignes: &[(Vec<u32>, Vec<u32>)]) -> Result<String, String> {
    let mut s = String::from(include_str!("noyau_natif.rs"));
    for (k, (mots, _)) in lignes.iter().enumerate() {
        s.push_str(&traduire(mots, &format!("programme_{}", k), &[])?);
    }
    s.push_str("\nfn lancer(k: usize, mem: &Memoire, es: &mut Es) -> Result<u64, String> {\n    match k {\n");
    for k in 0..lignes.len() {
        writeln!(s, "        {} => {{ let mut et = Regs {{ r: [0; 16], pc: 0, z: false, c: false }}; et.r[14] = PILE_HAUT; programme_{}(mem, es, 500_000_000, &mut et, u32::MAX, None, 0) }}", k, k).unwrap();
    }
    s.push_str("        _ => Err(\"programme inconnu\".into()),\n    }\n}\n");
    s.push_str(r#"
fn main() {
    let fichier = std::env::args().nth(1).expect("fichier du corpus");
    let texte = fs::read_to_string(fichier).expect("lecture du corpus impossible");
    let sortie = std::io::stdout();
    let mut out = std::io::BufWriter::new(sortie.lock());
    let mut mem = Memoire::new(true);
    for (k, ligne) in texte.lines().filter(|l| !l.trim().is_empty()).enumerate() {
        let (m, e) = ligne.split_once(';').unwrap_or((ligne, ""));
        mem.effacer();
        charger(&mut mem, &nombres(m));
        let mut es = Es::new(nombres(e), None);
        es.clavier = false;
        match lancer(k, &mem, &mut es) {
            Ok(pas) => {
                let s: Vec<String> = es.sorties.iter().map(|v| v.to_string()).collect();
                let etat: Vec<String> = mem.etat().iter().map(|(k, v)| format!("{}:{}", k, v)).collect();
                let t: Vec<String> = es.texte.iter().map(|v| v.to_string()).collect();
                if t.is_empty() {
                    writeln!(out, "{}|{}|{}", pas, s.join(","), etat.join(",")).unwrap();
                } else {
                    writeln!(out, "{}|{}|{}|T:{}", pas, s.join(","), etat.join(","), t.join(",")).unwrap();
                }
            }
            Err(e) => writeln!(out, "ERREUR {}", e).unwrap(),
        }
    }
}
"#);
    Ok(s)
}
