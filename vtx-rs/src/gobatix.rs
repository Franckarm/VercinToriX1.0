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
use super::gif::Gif;
use super::spu64::Spu64;
use super::Memoire;
use super::hote;
use std::sync::Mutex;

pub trait Sortie: Send {
    /// Montre une image de l × h points (0x00RRGGBB, ligne par ligne). Rend faux quand il faut s'arrêter.
    fn montrer(&mut self, l: usize, h: usize, px: &[u32]) -> bool;
    /// Après la fin du programme : la fenêtre reste ouverte jusqu'à sa fermeture ; un fichier est écrit.
    fn attendre_fin(&mut self) {}
}

static SORTIE: Mutex<Option<Box<dyn Sortie>>> = Mutex::new(None);
/// L'enregistrement (l'atelier : bouton « Enregistrer ») : tant qu'il est demandé, chaque image montrée s'ajoute à
/// l'animation, commencée à la première image.
pub static ENREGISTRER: std::sync::atomic::AtomicBool = std::sync::atomic::AtomicBool::new(false);
pub static ENREGISTREMENT: Mutex<Option<Gif>> = Mutex::new(None);
/// Au plus tant d'images dans un enregistrement (une minute à 30 images par seconde).
pub const MAX_IMAGES: usize = 1800;

/// Choisit la sortie des images (None : aucune, presenter() rend 0 sans rien montrer).
pub fn installer(s: Option<Box<dyn Sortie>>) {
    *SORTIE.lock().unwrap() = s;
}

/// Le délai d'une image dans une animation : la cadence du programme (20 ms au moins, 1/50 de seconde).
fn delai_ms() -> u32 {
    hote::CADENCE_MS.load(std::sync::atomic::Ordering::Relaxed).max(20)
}

/// Commun aux deux machines : l'image part vers la sortie et l'enregistrement, puis la cadence est respectée.
fn montrer(l: usize, h: usize, px: &[u32]) -> bool {
    {
        if ENREGISTRER.load(std::sync::atomic::Ordering::Relaxed) {
            let mut e = ENREGISTREMENT.lock().unwrap();
            let g = e.get_or_insert_with(|| Gif::new(l, h));
            if g.images < MAX_IMAGES {
                g.ajouter(l, h, px, delai_ms());
            }
        }
    }
    let continuer = match SORTIE.lock().unwrap().as_mut() {
        Some(s) => s.montrer(l, h, px),
        None => true,
    };
    hote::attendre_cadence();
    hote::image_presentee();
    continuer
}

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

struct Fichiers {
    dossier: std::path::PathBuf,
    appels: usize,
    ecrites: usize,
    pas: usize,
    max: usize,
}

impl Sortie for Fichiers {
    fn montrer(&mut self, l: usize, h: usize, px: &[u32]) -> bool {
        self.appels += 1;
        if (self.appels - 1) % self.pas == 0 {
            self.ecrites += 1;
            let png = super::cube::png_de(&px.iter().map(|&v| v | 0xFF00_0000).collect::<Vec<u32>>(), l, h);
            let _ = std::fs::write(self.dossier.join(format!("image-{:04}.png", self.ecrites)), png);
        }
        self.appels < self.max
    }
}

/// Une animation GIF : une image sur `pas`, au plus `max` appels ; le fichier est écrit à la fin.
struct Animation {
    chemin: std::path::PathBuf,
    gif: Option<Gif>,
    appels: usize,
    pas: usize,
    max: usize,
}

impl Sortie for Animation {
    fn montrer(&mut self, l: usize, h: usize, px: &[u32]) -> bool {
        self.appels += 1;
        if (self.appels - 1) % self.pas == 0 {
            let g = self.gif.get_or_insert_with(|| Gif::new(l, h));
            g.ajouter(l, h, px, delai_ms() * self.pas as u32);
        }
        self.appels < self.max
    }
    fn attendre_fin(&mut self) {
        if let Some(g) = self.gif.take() {
            let n = g.images;
            let o = g.finir();
            match std::fs::write(&self.chemin, &o) {
                Ok(()) => eprintln!("{} : {} images, {} octets", self.chemin.display(), n, o.len()),
                Err(e) => eprintln!("{} : écriture impossible ({})", self.chemin.display(), e),
            }
        }
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
    let sortie: Box<dyn Sortie> = match (images, gif) {
        (Some(d), _) => {
            let _ = std::fs::create_dir_all(&d);
            Box::new(Fichiers { dossier: d.into(), appels: 0, ecrites: 0, pas, max })
        }
        (None, Some(f)) => Box::new(Animation { chemin: f.into(), gif: None, appels: 0, pas, max }),
        (None, None) => match fenetre(&args[0]) {
            Some(s) => s,
            None => {
                eprintln!("pas de fenêtre sur cette machine : utilisez --images DOSSIER ou --gif FICHIER.gif");
                std::process::exit(2)
            }
        },
    };
    hote::remettre();
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
    if let Some(s) = SORTIE.lock().unwrap().as_mut() {
        s.attendre_fin();
    }
    installer(None);
    if let Err(e) = r {
        eprintln!("erreur : {}", e);
        std::process::exit(1);
    }
}

#[cfg(windows)]
fn fenetre(prog: &str) -> Option<Box<dyn Sortie>> {
    Some(Box::new(fen::Fenetre::new(prog)))
}
#[cfg(not(windows))]
fn fenetre(_prog: &str) -> Option<Box<dyn Sortie>> {
    None
}

// La fenêtre Win32 : un fil à elle (boucle de messages), l'image partagée sous un verrou, StretchDIBits pour peindre.
#[cfg(any(windows, feature = "verif_fenetre"))]
#[allow(non_snake_case, dead_code)]
mod fen {
    use core::ffi::c_void;
    use std::sync::Mutex;
    use std::time::{Duration, Instant};

    type H = *mut c_void;
    type Proc = unsafe extern "system" fn(H, u32, usize, isize) -> isize;

    #[repr(C)]
    struct WndClassEx {
        cbSize: u32, style: u32, lpfnWndProc: Proc, cbClsExtra: i32, cbWndExtra: i32, hInstance: H, hIcon: H, hCursor: H,
        hbrBackground: H, lpszMenuName: *const u16, lpszClassName: *const u16, hIconSm: H,
    }
    #[repr(C)]
    struct Point { x: i32, y: i32 }
    #[repr(C)]
    struct Msg { hwnd: H, message: u32, wParam: usize, lParam: isize, time: u32, pt: Point }
    #[repr(C)]
    #[derive(Default)]
    struct Rect { left: i32, top: i32, right: i32, bottom: i32 }
    #[repr(C)]
    struct PaintStruct { hdc: H, fErase: i32, rcPaint: Rect, fRestore: i32, fIncUpdate: i32, rgbReserved: [u8; 32] }
    #[repr(C)]
    struct BitmapInfoHeader {
        biSize: u32, biWidth: i32, biHeight: i32, biPlanes: u16, biBitCount: u16, biCompression: u32, biSizeImage: u32,
        biXPelsPerMeter: i32, biYPelsPerMeter: i32, biClrUsed: u32, biClrImportant: u32,
    }
    #[repr(C)]
    struct BitmapInfo { bmiHeader: BitmapInfoHeader, bmiColors: [u32; 1] }

    #[link(name = "user32")]
    extern "system" {
        fn RegisterClassExW(c: *const WndClassEx) -> u16;
        fn CreateWindowExW(ex: u32, classe: *const u16, titre: *const u16, style: u32, x: i32, y: i32, l: i32, h: i32,
                           parent: H, menu: H, inst: H, param: *mut c_void) -> H;
        fn DefWindowProcW(h: H, m: u32, w: usize, l: isize) -> isize;
        fn GetMessageW(m: *mut Msg, h: H, a: u32, b: u32) -> i32;
        fn TranslateMessage(m: *const Msg) -> i32;
        fn DispatchMessageW(m: *const Msg) -> isize;
        fn PostQuitMessage(code: i32);
        fn PostMessageW(h: H, m: u32, w: usize, l: isize) -> i32;
        fn ShowWindow(h: H, n: i32) -> i32;
        fn InvalidateRect(h: H, r: *const Rect, effacer: i32) -> i32;
        fn BeginPaint(h: H, p: *mut PaintStruct) -> H;
        fn EndPaint(h: H, p: *const PaintStruct) -> i32;
        fn GetClientRect(h: H, r: *mut Rect) -> i32;
        fn AdjustWindowRect(r: *mut Rect, style: u32, menu: i32) -> i32;
        fn LoadCursorW(inst: H, nom: *const u16) -> H;
        fn DestroyWindow(h: H) -> i32;
        fn SetProcessDPIAware() -> i32;
        fn SetCapture(h: H) -> H;
        fn ReleaseCapture() -> i32;
        fn ScreenToClient(h: H, p: *mut Point) -> i32;
    }
    #[link(name = "gdi32")]
    extern "system" {
        fn StretchDIBits(dc: H, xd: i32, yd: i32, ld: i32, hd: i32, xs: i32, ys: i32, ls: i32, hs: i32, bits: *const c_void,
                         info: *const BitmapInfo, usage: u32, rop: u32) -> i32;
        fn GetStockObject(i: i32) -> H;
    }
    #[link(name = "kernel32")]
    extern "system" {
        fn GetModuleHandleW(nom: *const u16) -> H;
    }

    const WM_DESTROY: u32 = 0x0002;
    const WM_PAINT: u32 = 0x000F;
    const WM_CLOSE: u32 = 0x0010;
    const WM_ERASEBKGND: u32 = 0x0014;
    const WM_KILLFOCUS: u32 = 0x0008;
    const WM_MOUSEMOVE: u32 = 0x0200;
    const WM_LBUTTONDOWN: u32 = 0x0201;
    const WM_LBUTTONUP: u32 = 0x0202;
    const WM_RBUTTONDOWN: u32 = 0x0204;
    const WM_RBUTTONUP: u32 = 0x0205;
    const WM_MBUTTONDOWN: u32 = 0x0207;
    const WM_MBUTTONUP: u32 = 0x0208;
    const WM_MOUSEWHEEL: u32 = 0x020A;
    const WS_OVERLAPPEDWINDOW: u32 = 0x00CF_0000;
    const WS_VISIBLE: u32 = 0x1000_0000;
    const CW_USEDEFAULT: i32 = 0x8000_0000u32 as i32;
    const SRCCOPY: u32 = 0x00CC_0020;
    const BLACK_BRUSH: i32 = 4;
    const IDC_ARROW: usize = 32512;

    struct Image {
        px: Vec<u32>,
        l: usize,
        h: usize,
        ferme: bool,
        // où l'image est peinte dans la fenêtre (pour situer la souris dans l'image)
        place: (i32, i32, i32, i32),
    }
    static IMAGE: Mutex<Image> = Mutex::new(Image { px: Vec::new(), l: 0, h: 0, ferme: false, place: (0, 0, 0, 0) });
    static BOUTONS: std::sync::atomic::AtomicU32 = std::sync::atomic::AtomicU32::new(0);

    fn w(s: &str) -> Vec<u16> {
        s.encode_utf16().chain(std::iter::once(0)).collect()
    }

    unsafe extern "system" fn proc_fenetre(h: H, m: u32, wp: usize, lp: isize) -> isize {
        match m {
            WM_ERASEBKGND => 1,
            WM_PAINT => {
                let mut ps: PaintStruct = std::mem::zeroed();
                let dc = BeginPaint(h, &mut ps);
                let mut r = Rect::default();
                GetClientRect(h, &mut r);
                let (cl, ch) = ((r.right - r.left).max(1), (r.bottom - r.top).max(1));
                let mut im = IMAGE.lock().unwrap();
                if im.l > 0 && im.h > 0 && im.px.len() == im.l * im.h {
                    // l'image remplit la fenêtre sans être déformée (bandes noires sinon)
                    let e = (cl as f32 / im.l as f32).min(ch as f32 / im.h as f32);
                    let (dl, dh) = (((im.l as f32 * e) as i32).max(1), ((im.h as f32 * e) as i32).max(1));
                    let (x0, y0) = ((cl - dl) / 2, (ch - dh) / 2);
                    im.place = (x0, y0, dl, dh);
                    let info = BitmapInfo {
                        bmiHeader: BitmapInfoHeader { biSize: std::mem::size_of::<BitmapInfoHeader>() as u32, biWidth: im.l as i32,
                            biHeight: -(im.h as i32), biPlanes: 1, biBitCount: 32, biCompression: 0, biSizeImage: 0,
                            biXPelsPerMeter: 0, biYPelsPerMeter: 0, biClrUsed: 0, biClrImportant: 0 },
                        bmiColors: [0],
                    };
                    StretchDIBits(dc, x0, y0, dl, dh, 0, 0, im.l as i32, im.h as i32, im.px.as_ptr() as *const c_void, &info, 0, SRCCOPY);
                }
                drop(im);
                EndPaint(h, &ps);
                0
            }
            WM_MOUSEMOVE | WM_LBUTTONDOWN | WM_LBUTTONUP | WM_RBUTTONDOWN | WM_RBUTTONUP | WM_MBUTTONDOWN | WM_MBUTTONUP => {
                // la souris, en points de l'image ; boutons : gauche 1, droit 2, milieu 4 (MK_LBUTTON 1, MK_RBUTTON 2,
                // MK_MBUTTON 16 dans wParam)
                let b = (wp as u32 & 1) | (wp as u32 & 2) | if wp & 16 != 0 { 4 } else { 0 };
                BOUTONS.store(b, std::sync::atomic::Ordering::Relaxed);
                match m {
                    WM_LBUTTONDOWN | WM_RBUTTONDOWN | WM_MBUTTONDOWN => { SetCapture(h); }
                    WM_LBUTTONUP | WM_RBUTTONUP | WM_MBUTTONUP if b == 0 => { ReleaseCapture(); }
                    _ => {}
                }
                let (mx, my) = ((lp & 0xFFFF) as i16 as i32, ((lp >> 16) & 0xFFFF) as i16 as i32);
                let im = IMAGE.lock().unwrap();
                // (souris_dans_vue compte aussi le glissement)
                let (x0, y0, dl, dh) = im.place;
                super::hote::souris_dans_vue(mx, my, x0, y0, dl, dh, im.l, im.h, b);
                0
            }
            WM_MOUSEWHEEL => {
                super::hote::ajouter_molette(((wp >> 16) & 0xFFFF) as i16 as i32 / 120);
                0
            }
            0x100 | 0x101 | 0x102 | 0x104 | 0x105 => {
                super::hote::clavier_windows(m, wp);
                DefWindowProcW(h, m, wp, lp)
            }
            WM_KILLFOCUS => {
                super::hote::tout_relacher();
                0
            }
            WM_CLOSE => {
                IMAGE.lock().unwrap().ferme = true;
                DestroyWindow(h);
                0
            }
            WM_DESTROY => {
                IMAGE.lock().unwrap().ferme = true;
                PostQuitMessage(0);
                0
            }
            _ => DefWindowProcW(h, m, wp, lp),
        }
    }

    pub struct Fenetre {
        titre: String,
        hwnd: Option<isize>,
        dernier: Instant,
    }

    impl Fenetre {
        pub fn new(prog: &str) -> Self {
            let nom = std::path::Path::new(prog).file_name().map(|n| n.to_string_lossy().to_string()).unwrap_or_default();
            Fenetre { titre: format!("Gobatix — {}", nom), hwnd: None, dernier: Instant::now() }
        }
        /// Crée la fenêtre (et son fil) à la première image : sa taille suit celle de l'image, agrandie jusqu'à 4 fois.
        fn ouvrir(&mut self, l: usize, h: usize) {
            let titre = self.titre.clone();
            let (tx, rx) = std::sync::mpsc::channel::<isize>();
            std::thread::spawn(move || unsafe {
                SetProcessDPIAware();
                let inst = GetModuleHandleW(std::ptr::null());
                let nom = w("VtxGobatix");
                let classe = WndClassEx {
                    cbSize: std::mem::size_of::<WndClassEx>() as u32, style: 0x3, lpfnWndProc: proc_fenetre, cbClsExtra: 0,
                    cbWndExtra: 0, hInstance: inst, hIcon: std::ptr::null_mut(),
                    hCursor: LoadCursorW(std::ptr::null_mut(), IDC_ARROW as *const u16), hbrBackground: GetStockObject(BLACK_BRUSH),
                    lpszMenuName: std::ptr::null(), lpszClassName: nom.as_ptr(), hIconSm: std::ptr::null_mut(),
                };
                RegisterClassExW(&classe);
                let e = (1280 / l.max(1)).clamp(1, 4).min((720 / h.max(1)).max(1)) as i32;
                let mut r = Rect { left: 0, top: 0, right: l as i32 * e, bottom: h as i32 * e };
                AdjustWindowRect(&mut r, WS_OVERLAPPEDWINDOW, 0);
                let fen = CreateWindowExW(0, nom.as_ptr(), w(&titre).as_ptr(), WS_OVERLAPPEDWINDOW | WS_VISIBLE, CW_USEDEFAULT,
                                          CW_USEDEFAULT, r.right - r.left, r.bottom - r.top, std::ptr::null_mut(),
                                          std::ptr::null_mut(), inst, std::ptr::null_mut());
                if fen.is_null() {
                    IMAGE.lock().unwrap().ferme = true;
                    let _ = tx.send(0);
                    return;
                }
                ShowWindow(fen, 5);
                let _ = tx.send(fen as isize);
                let mut msg: Msg = std::mem::zeroed();
                while GetMessageW(&mut msg, std::ptr::null_mut(), 0, 0) > 0 {
                    TranslateMessage(&msg);
                    DispatchMessageW(&msg);
                }
                IMAGE.lock().unwrap().ferme = true;
            });
            self.hwnd = rx.recv().ok();
        }
    }

    impl super::Sortie for Fenetre {
        fn montrer(&mut self, l: usize, h: usize, px: &[u32]) -> bool {
            if self.hwnd.is_none() {
                self.ouvrir(l, h);
            }
            {
                let mut im = IMAGE.lock().unwrap();
                if im.ferme {
                    return false;
                }
                im.l = l;
                im.h = h;
                im.px.clear();
                im.px.extend_from_slice(px);
            }
            if let Some(hw) = self.hwnd {
                unsafe { InvalidateRect(hw as H, std::ptr::null(), 0) };
            }
            // la cadence (60 images par seconde par défaut, cadence(ms) la change) : hote::attendre_cadence
            super::hote::FENETRE.store(true, std::sync::atomic::Ordering::Relaxed);
            self.dernier = Instant::now();
            true
        }
        fn attendre_fin(&mut self) {
            super::hote::FENETRE.store(false, std::sync::atomic::Ordering::Relaxed);
            // le programme est fini : l'image reste affichée jusqu'à la fermeture de la fenêtre
            while self.hwnd.is_some() && !IMAGE.lock().unwrap().ferme {
                std::thread::sleep(Duration::from_millis(50));
            }
        }
    }
}

