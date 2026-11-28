fn debuter_zones(c: &mut Ctx) {
    let disque = |e: u32| c.m.dossier.as_ref().map(|d| std::fs::read_dir(d).map(|l| l.flatten().any(|f| f.file_name().to_string_lossy().starts_with(&format!("cube128-{}-", e)))).unwrap_or(false)).unwrap_or(false);
}
fn vider_zones(c: &mut Ctx) {
}
#[allow(dead_code)]
fn ctx_fils() -> Ctx {
    let mut m = Spu128::nouveau();
    m.charger(&MOTS);
    Ctx { m, sp: spu128::PILE, cl: [u128::MAX; 64], pl: [std::ptr::null_mut(); 64], ce: [u128::MAX; 64], carte: Carte::neuve(),
          pe: [std::ptr::null_mut(); 64], pb: [std::ptr::null_mut(); 64], rb: [std::ptr::null_mut(); 64], wb: [std::ptr::null_mut(); 64], vider: |_c| {}, ombre: None }
}
#[allow(dead_code)]
fn ctx_cylindre(inst: &Instantane) -> Box<Ctx> {
    let mut c = match CTX_RESERVE.lock().unwrap().pop() { Some(EnvoiCtx(c)) => c, None => Box::new(ctx_fils()) };
    c.sp = spu128::PILE; c.cl = [u128::MAX; 64]; c.ce = [u128::MAX; 64]; c.pb = [std::ptr::null_mut(); 64]; c.rb = [std::ptr::null_mut(); 64]; c.wb = [std::ptr::null_mut(); 64]; c.carte.oublier();
    c.ombre = Some(Box::new(Cylindre { commun: inst as *const Instantane, feuilles: Default::default(), lus: Default::default(), vues: Default::default(), partage: false, ecrits: Default::default(), danger: false }));
    c
}
#[allow(dead_code)]
fn ctx_bande(inst: &Instantane) -> Box<Ctx> {
    let mut c = ctx_cylindre(inst);
    c.ombre.as_mut().unwrap().partage = true;
    c
}
#[allow(dead_code)]
static POIDS: [std::sync::atomic::AtomicU64; 1] = { const Z: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0); [Z; 1] };
#[allow(dead_code)]
const NOMS_POIDS: [&str; 0] = [];
#[allow(dead_code)]
static OBS: [std::sync::Mutex<(u128, u128, i128, i128, u64)>; 1] = { const Z: std::sync::Mutex<(u128, u128, i128, i128, u64)> = std::sync::Mutex::new((u128::MAX, 0, i128::MAX, i128::MIN, 0)); [Z; 1] };
#[allow(dead_code)]
const NOMS_OBS: [&str; 0] = [];
#[allow(dead_code)]
#[inline(never)]
fn observer(k: usize, v: u128) {
    if let Ok(mut g) = OBS[k].lock() {
        let s = v as i128;
        if v < g.0 { g.0 = v; }
        if v > g.1 { g.1 = v; }
        if s < g.2 { g.2 = s; }
        if s > g.3 { g.3 = s; }
        g.4 += 1;
    }
}
#[allow(unused_variables)]
fn druide_fin(us: u128) {
}
#[allow(dead_code)]
#[inline(always)]
fn garde_cube(a: u128) {
    let e = if a >> 64 == 0 { (a >> 62) & 3 } else { a >> 126 };
    if e == 1 || e == 2 { arret_membrane_cube(e, a); }
}
#[allow(dead_code)]
#[cold]
#[inline(never)]
fn arret_membrane_cube(e: u128, a: u128) {
    eprintln!("membrane du cube : un texte écrit à l'étage {} (adresse {:#x}) : la preuve d'Ésus ne tient plus ; reforger avec VTX_MEMBRANE_CUBE=0", e, a);
    std::process::exit(4);
}
pub fn lancer(entrees: &[String]) {
    nommer_programme(NOM);
    lancer_programme(f_principal, debuter_zones, vider_zones, &MOTS, FIN_CODE, NOM, entrees, druide_fin);
}

