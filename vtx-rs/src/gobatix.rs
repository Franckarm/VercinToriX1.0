// Gobatix, premier pas : le service graphique de la machine.
//
// Un programme vtx dessine dans l'image de l'étage 1 (ecran, pixel, trait, rectangle, disque : le prélude) puis appelle
// presenter() : la machine copie l'image vers une sortie, la montre, et rend 0 pour continuer, 1 si l'utilisateur a
// fermé la fenêtre, 4294967295 si le programme n'a pas préparé d'image. Deux sorties :
//   - la fenêtre (Windows) : une fenêtre Win32 écrite directement, à 60 images par seconde au plus ;
//   - les fichiers (toutes les machines) : une image PNG par appel, pour vérifier une animation sans écran.
// vtx gobatix PROG.vtx                                 la fenêtre (Windows)
// vtx gobatix PROG.vtx --images DOSSIER [--max N] [--pas K]   les images image-0001.png… (une sur K, au plus N appels)
use super::cube::taille_dessin;
use super::Memoire;
use std::sync::Mutex;

pub trait Sortie: Send {
    /// Montre une image de l × h points (0x00RRGGBB, ligne par ligne). Rend faux quand il faut s'arrêter.
    fn montrer(&mut self, l: usize, h: usize, px: &[u32]) -> bool;
    /// Après la fin du programme : la fenêtre reste ouverte jusqu'à sa fermeture.
    fn attendre_fin(&mut self) {}
}

static SORTIE: Mutex<Option<Box<dyn Sortie>>> = Mutex::new(None);

/// Le service 12 : présenter l'image du programme.
pub fn presenter(mem: &Memoire) -> u32 {
    let (l, h) = match taille_dessin(mem) {
        Some((l, h)) => (l as usize, h as usize),
        None => return 0xFFFF_FFFF,
    };
    let mut garde = SORTIE.lock().unwrap();
    let sortie = match garde.as_mut() {
        Some(s) => s,
        None => return 0,
    };
    let mut px = vec![0u32; l * h];
    for (i, p) in px.iter_mut().enumerate() {
        *p = mem.lit(1, i as u32) >> 8;
    }
    if sortie.montrer(l, h, &px) { 0 } else { 1 }
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

/// vtx gobatix PROG.vtx [--images DOSSIER] [--max N] [--pas K]
pub fn lancer(args: &[String]) {
    use super::{compiler_avec, dossier_de, executer_dans, nombres, COMPLET, VTXC};
    if args.is_empty() {
        eprintln!("utilisation : vtx gobatix PROG.vtx [--images DOSSIER] [--max N] [--pas K]");
        std::process::exit(2);
    }
    let (mut images, mut max, mut pas) = (None, usize::MAX, 1usize);
    let mut i = 1;
    while i < args.len() {
        let v = args.get(i + 1);
        match args[i].as_str() {
            "--images" => images = v.cloned(),
            "--max" => max = v.and_then(|x| x.parse().ok()).unwrap_or(usize::MAX),
            "--pas" => pas = v.and_then(|x| x.parse().ok()).unwrap_or(1).max(1),
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
    let (mots, _) = compiler_avec(&nombres(VTXC), &source, &base, COMPLET).unwrap_or_else(|e| {
        eprint!("{}", e);
        std::process::exit(1)
    });
    let sortie: Box<dyn Sortie> = match images {
        Some(d) => {
            let _ = std::fs::create_dir_all(&d);
            Box::new(Fichiers { dossier: d.into(), appels: 0, ecrites: 0, pas, max })
        }
        None => match fenetre(&args[0]) {
            Some(s) => s,
            None => {
                eprintln!("pas de fenêtre sur cette machine : utilisez --images DOSSIER");
                std::process::exit(2)
            }
        },
    };
    *SORTIE.lock().unwrap() = Some(sortie);
    let mut mem = Memoire::new(false);
    super::charger(&mut mem, &mots);
    let r = executer_dans(&mem, &[], u64::MAX / 4, Some(std::path::Path::new(&base)), None);
    if let Some(s) = SORTIE.lock().unwrap().as_mut() {
        s.attendre_fin();
    }
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
    }
    static IMAGE: Mutex<Image> = Mutex::new(Image { px: Vec::new(), l: 0, h: 0, ferme: false });

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
                let im = IMAGE.lock().unwrap();
                if im.l > 0 && im.h > 0 && im.px.len() == im.l * im.h {
                    // l'image remplit la fenêtre sans être déformée (bandes noires sinon)
                    let e = (cl as f32 / im.l as f32).min(ch as f32 / im.h as f32);
                    let (dl, dh) = (((im.l as f32 * e) as i32).max(1), ((im.h as f32 * e) as i32).max(1));
                    let (x0, y0) = ((cl - dl) / 2, (ch - dh) / 2);
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
            // 60 images par seconde au plus
            let cadence = Duration::from_micros(16_667);
            let ecoule = self.dernier.elapsed();
            if ecoule < cadence {
                std::thread::sleep(cadence - ecoule);
            }
            self.dernier = Instant::now();
            true
        }
        fn attendre_fin(&mut self) {
            // le programme est fini : l'image reste affichée jusqu'à la fermeture de la fenêtre
            while self.hwnd.is_some() && !IMAGE.lock().unwrap().ferme {
                std::thread::sleep(Duration::from_millis(50));
            }
        }
    }
}

