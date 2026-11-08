// La visionneuse d'Ogmios : ce qu'un programme a créé s'ouvre dans sa propre fenêtre, à côté de l'atelier.
//   - une image (PNG, GIF, BMP, JPEG) : montrée par GDI+ (la bibliothèque d'images de Windows), à la taille de la
//     fenêtre, les petites images agrandies sans flou (chaque point reste un carré) ;
//   - un son (WAV) : joué (PlaySound) ; un clic dans sa fenêtre le rejoue, Échap l'arrête ;
//   - un exécutable : lancé dans sa propre console.
// Avant chaque exécution, l'atelier photographie le dossier du programme (photo) ; à la fin, ce qui est nouveau ou a
// changé (nouveautes) s'ouvre (ouvrir). Une fenêtre par fichier ; la rouvrir la remet devant.
#![allow(non_snake_case, clippy::upper_case_acronyms)]
use core::ffi::c_void;
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::time::SystemTime;

type H = *mut c_void;
type Proc = unsafe extern "system" fn(H, u32, usize, isize) -> isize;

#[repr(C)]
struct WndClassEx {
    cbSize: u32,
    style: u32,
    lpfnWndProc: Proc,
    cbClsExtra: i32,
    cbWndExtra: i32,
    hInstance: H,
    hIcon: H,
    hCursor: H,
    hbrBackground: H,
    lpszMenuName: *const u16,
    lpszClassName: *const u16,
    hIconSm: H,
}
#[repr(C)]
#[derive(Default)]
struct Rect {
    left: i32,
    top: i32,
    right: i32,
    bottom: i32,
}
#[repr(C)]
struct PaintStruct {
    hdc: H,
    fErase: i32,
    rcPaint: Rect,
    fRestore: i32,
    fIncUpdate: i32,
    rgbReserved: [u8; 32],
}
#[repr(C)]
struct StartupInput {
    version: u32,
    rappel: usize,
    sans_fil: i32,
    sans_codecs: i32,
}
#[repr(C)]
struct StartupInfoW {
    cb: u32,
    lpReserved: *mut u16,
    lpDesktop: *mut u16,
    lpTitle: *mut u16,
    dwX: u32,
    dwY: u32,
    dwXSize: u32,
    dwYSize: u32,
    dwXCountChars: u32,
    dwYCountChars: u32,
    dwFillAttribute: u32,
    dwFlags: u32,
    wShowWindow: u16,
    cbReserved2: u16,
    lpReserved2: *mut u8,
    hStdInput: H,
    hStdOutput: H,
    hStdError: H,
}
#[repr(C)]
struct ProcessInformation {
    hProcess: H,
    hThread: H,
    dwProcessId: u32,
    dwThreadId: u32,
}

#[link(name = "user32")]
extern "system" {
    fn RegisterClassExW(c: *const WndClassEx) -> u16;
    fn CreateWindowExW(ex: u32, classe: *const u16, titre: *const u16, style: u32, x: i32, y: i32, l: i32, h: i32, parent: H,
                       menu: H, inst: H, p: *mut c_void) -> H;
    fn DefWindowProcW(h: H, m: u32, wp: usize, lp: isize) -> isize;
    fn BeginPaint(h: H, p: *mut PaintStruct) -> H;
    fn EndPaint(h: H, p: *const PaintStruct) -> i32;
    fn GetClientRect(h: H, r: *mut Rect) -> i32;
    fn FillRect(dc: H, r: *const Rect, b: H) -> i32;
    fn InvalidateRect(h: H, r: *const Rect, e: i32) -> i32;
    fn ShowWindow(h: H, n: i32) -> i32;
    fn SetForegroundWindow(h: H) -> i32;
    fn LoadCursorW(i: H, n: *const u16) -> H;
    fn DrawTextW(dc: H, t: *const u16, n: i32, r: *mut Rect, f: u32) -> i32;
    fn GetModuleHandleW(n: *const u16) -> H;
}
#[link(name = "gdi32")]
extern "system" {
    fn CreateSolidBrush(c: u32) -> H;
    fn DeleteObject(o: H) -> i32;
    fn SetTextColor(dc: H, c: u32) -> u32;
    fn SetBkMode(dc: H, m: i32) -> i32;
}
#[link(name = "gdiplus")]
extern "system" {
    fn GdiplusStartup(jeton: *mut usize, entree: *const StartupInput, sortie: *mut c_void) -> i32;
    fn GdipCreateBitmapFromFile(nom: *const u16, image: *mut H) -> i32;
    fn GdipGetImageWidth(image: H, l: *mut u32) -> i32;
    fn GdipGetImageHeight(image: H, h: *mut u32) -> i32;
    fn GdipCreateFromHDC(dc: H, g: *mut H) -> i32;
    fn GdipDeleteGraphics(g: H) -> i32;
    fn GdipSetInterpolationMode(g: H, mode: i32) -> i32;
    fn GdipSetPixelOffsetMode(g: H, mode: i32) -> i32;
    fn GdipDrawImageRectI(g: H, image: H, x: i32, y: i32, l: i32, h: i32) -> i32;
    fn GdipDisposeImage(image: H) -> i32;
}
#[link(name = "winmm")]
extern "system" {
    fn PlaySoundW(son: *const u16, module: H, drapeaux: u32) -> i32;
}
#[link(name = "kernel32")]
extern "system" {
    fn CreateProcessW(app: *const u16, ligne: *mut u16, pa: *const c_void, ta: *const c_void, herite: i32, drapeaux: u32,
                      env: *const c_void, dossier: *const u16, si: *const StartupInfoW, pi: *mut ProcessInformation) -> i32;
    fn CloseHandle(h: H) -> i32;
}

const WS_OVERLAPPEDWINDOW: u32 = 0x00CF_0000;
const WS_VISIBLE: u32 = 0x1000_0000;
const CW_USEDEFAULT: i32 = 0x8000_0000u32 as i32;
const WM_PAINT: u32 = 0x000F;
const WM_SIZE: u32 = 0x0005;
const WM_DESTROY: u32 = 0x0002;
const WM_LBUTTONDOWN: u32 = 0x0201;
const WM_KEYDOWN: u32 = 0x0100;
const WM_ERASEBKGND: u32 = 0x0014;
const SND_ASYNC: u32 = 0x1;
const SND_FILENAME: u32 = 0x2_0000;
const CREATE_NEW_CONSOLE: u32 = 0x10;

fn w(s: &str) -> Vec<u16> {
    s.encode_utf16().chain(std::iter::once(0)).collect()
}

/// ce qu'un fichier est pour la visionneuse
#[derive(Clone, Copy, PartialEq)]
pub enum Genre {
    Image,
    Son,
    Programme,
}

pub fn genre(p: &Path) -> Option<Genre> {
    match p.extension()?.to_str()?.to_ascii_lowercase().as_str() {
        "png" | "gif" | "bmp" | "jpg" | "jpeg" => Some(Genre::Image),
        "wav" => Some(Genre::Son),
        "exe" => Some(Genre::Programme),
        _ => None,
    }
}

/// la photo d'un dossier : ses fichiers (sans les sous-dossiers) et leur date
pub fn photo(dossier: &Path) -> HashMap<PathBuf, SystemTime> {
    let mut m = HashMap::new();
    if let Ok(l) = std::fs::read_dir(dossier) {
        for e in l.flatten() {
            if let Ok(md) = e.metadata() {
                if md.is_file() {
                    m.insert(e.path(), md.modified().unwrap_or(SystemTime::UNIX_EPOCH));
                }
            }
        }
    }
    m
}

/// ce qui est nouveau ou a changé depuis la photo, et que la visionneuse sait ouvrir (images et sons ; les .exe ne
/// s'ouvrent pas d'eux-mêmes)
pub fn nouveautes(dossier: &Path, avant: &HashMap<PathBuf, SystemTime>) -> Vec<PathBuf> {
    let mut v: Vec<PathBuf> = photo(dossier).into_iter()
        .filter(|(p, t)| matches!(genre(p), Some(Genre::Image) | Some(Genre::Son)) && avant.get(p).map_or(true, |a| a != t))
        .map(|(p, _)| p)
        .collect();
    v.sort();
    v
}

static PHOTO: std::sync::Mutex<Vec<(PathBuf, HashMap<PathBuf, SystemTime>)>> = std::sync::Mutex::new(Vec::new());

/// avant une exécution : la photo des dossiers où le programme peut écrire (le sien, et le dossier courant)
pub fn retenir(dossiers: &[PathBuf]) {
    let mut v: Vec<(PathBuf, HashMap<PathBuf, SystemTime>)> = Vec::new();
    for d in dossiers {
        if !v.iter().any(|(x, _)| x == d) {
            v.push((d.clone(), photo(d)));
        }
    }
    *PHOTO.lock().unwrap() = v;
}

/// après : ce qui est nouveau ou a changé dans ces dossiers
pub fn apres() -> Vec<PathBuf> {
    let photos = std::mem::take(&mut *PHOTO.lock().unwrap());
    let mut v: Vec<PathBuf> = Vec::new();
    for (d, avant) in &photos {
        for p in nouveautes(d, avant) {
            if !v.contains(&p) {
                v.push(p);
            }
        }
    }
    v
}

struct Vue {
    fen: H,
    chemin: PathBuf,
    genre: Genre,
    image: H,
    taille: (u32, u32),
}

static mut VUES: Vec<Vue> = Vec::new();
static mut PRETE: bool = false;

fn vues() -> &'static mut Vec<Vue> {
    unsafe { &mut *std::ptr::addr_of_mut!(VUES) }
}

unsafe fn preparer() {
    if PRETE {
        return;
    }
    PRETE = true;
    let mut jeton = 0usize;
    let entree = StartupInput { version: 1, rappel: 0, sans_fil: 0, sans_codecs: 0 };
    GdiplusStartup(&mut jeton, &entree, std::ptr::null_mut());
    let nom = w("VtxVisionneuse");
    let classe = WndClassEx {
        cbSize: std::mem::size_of::<WndClassEx>() as u32, style: 0x3, lpfnWndProc: proc_vue, cbClsExtra: 0, cbWndExtra: 0,
        hInstance: GetModuleHandleW(std::ptr::null()), hIcon: std::ptr::null_mut(),
        hCursor: LoadCursorW(std::ptr::null_mut(), 32512 as *const u16), hbrBackground: std::ptr::null_mut(),
        lpszMenuName: std::ptr::null(), lpszClassName: nom.as_ptr(), hIconSm: std::ptr::null_mut(),
    };
    RegisterClassExW(&classe);
}

/// une image chargée par GDI+ depuis une copie (le programme peut réécrire le fichier sans qu'il soit tenu)
unsafe fn charger_image(p: &Path) -> (H, (u32, u32)) {
    let copie = std::env::temp_dir().join(format!("vtx-vue-{}-{}", std::process::id(),
                                                  p.file_name().map(|n| n.to_string_lossy().into_owned()).unwrap_or_default()));
    let source = if std::fs::copy(p, &copie).is_ok() { copie } else { p.to_path_buf() };
    let mut im: H = std::ptr::null_mut();
    if GdipCreateBitmapFromFile(w(&source.to_string_lossy()).as_ptr(), &mut im) != 0 {
        return (std::ptr::null_mut(), (0, 0));
    }
    let (mut l, mut h) = (0u32, 0u32);
    GdipGetImageWidth(im, &mut l);
    GdipGetImageHeight(im, &mut h);
    (im, (l, h))
}

/// ouvre le fichier dans la visionneuse (ou, pour un exécutable, le lance dans sa propre console) ; rend un mot pour
/// la barre d'état de l'atelier
pub fn ouvrir(p: &Path) -> String {
    let g = match genre(p) {
        Some(g) => g,
        None => return format!("{} : la visionneuse ne sait pas l'ouvrir", p.display()),
    };
    let nom = p.file_name().map(|n| n.to_string_lossy().into_owned()).unwrap_or_default();
    unsafe {
        if g == Genre::Programme {
            let si = StartupInfoW { cb: std::mem::size_of::<StartupInfoW>() as u32, lpReserved: std::ptr::null_mut(),
                                    lpDesktop: std::ptr::null_mut(), lpTitle: std::ptr::null_mut(), dwX: 0, dwY: 0, dwXSize: 0,
                                    dwYSize: 0, dwXCountChars: 0, dwYCountChars: 0, dwFillAttribute: 0, dwFlags: 0,
                                    wShowWindow: 0, cbReserved2: 0, lpReserved2: std::ptr::null_mut(),
                                    hStdInput: std::ptr::null_mut(), hStdOutput: std::ptr::null_mut(),
                                    hStdError: std::ptr::null_mut() };
            let mut pi = ProcessInformation { hProcess: std::ptr::null_mut(), hThread: std::ptr::null_mut(), dwProcessId: 0,
                                              dwThreadId: 0 };
            let mut ligne = w(&format!("\"{}\"", p.display()));
            let dossier = p.parent().map(|d| w(&d.to_string_lossy()));
            let ok = CreateProcessW(std::ptr::null(), ligne.as_mut_ptr(), std::ptr::null(), std::ptr::null(), 0,
                                    CREATE_NEW_CONSOLE, std::ptr::null(),
                                    dossier.as_ref().map_or(std::ptr::null(), |d| d.as_ptr()), &si, &mut pi);
            if ok == 0 {
                return format!("{} : Windows refuse de le lancer", nom);
            }
            CloseHandle(pi.hThread);
            CloseHandle(pi.hProcess);
            return format!("{} : lancé dans sa propre fenêtre", nom);
        }
        preparer();
        // déjà ouvert : on le recharge et on le remet devant
        if let Some(v) = vues().iter_mut().find(|v| v.chemin == p) {
            if v.genre == Genre::Image {
                if !v.image.is_null() {
                    GdipDisposeImage(v.image);
                }
                let (im, t) = charger_image(p);
                v.image = im;
                v.taille = t;
            } else {
                PlaySoundW(w(&p.to_string_lossy()).as_ptr(), std::ptr::null_mut(), SND_FILENAME | SND_ASYNC);
            }
            InvalidateRect(v.fen, std::ptr::null(), 0);
            ShowWindow(v.fen, 9);
            SetForegroundWindow(v.fen);
            return format!("{} : remis à jour", nom);
        }
        let (image, taille) = if g == Genre::Image { charger_image(p) } else { (std::ptr::null_mut(), (0, 0)) };
        let titre = match g {
            Genre::Image if !image.is_null() => format!("{} — {} × {}", nom, taille.0, taille.1),
            Genre::Image => format!("{} — illisible", nom),
            _ => format!("{} — son", nom),
        };
        let (l, h) = match g {
            Genre::Image if taille.0 > 0 => {
                let k = (900.0 / taille.0 as f32).min(700.0 / taille.1 as f32).clamp(0.1, 8.0);
                ((taille.0 as f32 * k) as i32 + 16, (taille.1 as f32 * k) as i32 + 40)
            }
            _ => (460, 160),
        };
        let fen = CreateWindowExW(0, w("VtxVisionneuse").as_ptr(), w(&titre).as_ptr(), WS_OVERLAPPEDWINDOW | WS_VISIBLE,
                                  CW_USEDEFAULT, CW_USEDEFAULT, l.max(240), h.max(120), std::ptr::null_mut(), std::ptr::null_mut(),
                                  GetModuleHandleW(std::ptr::null()), std::ptr::null_mut());
        vues().push(Vue { fen, chemin: p.to_path_buf(), genre: g, image, taille });
        if g == Genre::Son {
            PlaySoundW(w(&p.to_string_lossy()).as_ptr(), std::ptr::null_mut(), SND_FILENAME | SND_ASYNC);
        }
        format!("{} : ouvert dans sa fenêtre", nom)
    }
}

unsafe extern "system" fn proc_vue(h: H, m: u32, wp: usize, lp: isize) -> isize {
    let k = match vues().iter().position(|v| v.fen == h) {
        Some(k) => k,
        None => return DefWindowProcW(h, m, wp, lp),
    };
    match m {
        WM_ERASEBKGND => 1,
        WM_SIZE => {
            InvalidateRect(h, std::ptr::null(), 0);
            0
        }
        WM_PAINT => {
            let mut ps: PaintStruct = std::mem::zeroed();
            let dc = BeginPaint(h, &mut ps);
            let mut r = Rect::default();
            GetClientRect(h, &mut r);
            let fond = CreateSolidBrush(0x00201C1A);
            FillRect(dc, &r, fond);
            DeleteObject(fond);
            let v = &vues()[k];
            let (l, hh) = (r.right - r.left, r.bottom - r.top);
            if v.genre == Genre::Image && !v.image.is_null() && v.taille.0 > 0 {
                // à la taille de la fenêtre, sans déformer ; agrandie par un nombre entier si elle est petite
                let mut kk = (l as f32 / v.taille.0 as f32).min(hh as f32 / v.taille.1 as f32);
                if kk >= 1.0 {
                    kk = kk.floor();
                }
                let (il, ih) = ((v.taille.0 as f32 * kk) as i32, (v.taille.1 as f32 * kk) as i32);
                let mut g: H = std::ptr::null_mut();
                if GdipCreateFromHDC(dc, &mut g) == 0 {
                    GdipSetInterpolationMode(g, if kk >= 1.0 { 5 } else { 7 });
                    GdipSetPixelOffsetMode(g, 4);
                    GdipDrawImageRectI(g, v.image, (l - il) / 2, (hh - ih) / 2, il, ih);
                    GdipDeleteGraphics(g);
                }
            } else {
                let t = match v.genre {
                    Genre::Son => format!("♪ {}\r\n\r\nUn clic : rejouer.  Échap : arrêter.",
                                          v.chemin.file_name().map(|n| n.to_string_lossy().into_owned()).unwrap_or_default()),
                    _ => format!("{}\r\n\r\nGDI+ ne sait pas lire cette image.", v.chemin.display()),
                };
                SetBkMode(dc, 1);
                SetTextColor(dc, 0x00E8E0D8);
                let mut rr = Rect { left: 16, top: 16, right: l - 16, bottom: hh - 16 };
                let tw = w(&t);
                DrawTextW(dc, tw.as_ptr(), -1, &mut rr, 0x10);
            }
            EndPaint(h, &ps);
            0
        }
        WM_LBUTTONDOWN => {
            let v = &vues()[k];
            if v.genre == Genre::Son {
                PlaySoundW(w(&v.chemin.to_string_lossy()).as_ptr(), std::ptr::null_mut(), SND_FILENAME | SND_ASYNC);
            }
            0
        }
        WM_KEYDOWN => {
            if wp == 0x1B && vues()[k].genre == Genre::Son {
                PlaySoundW(std::ptr::null(), std::ptr::null_mut(), 0);
            }
            0
        }
        WM_DESTROY => {
            let v = vues().remove(k);
            if v.genre == Genre::Son {
                PlaySoundW(std::ptr::null(), std::ptr::null_mut(), 0);
            }
            if !v.image.is_null() {
                GdipDisposeImage(v.image);
            }
            0
        }
        _ => DefWindowProcW(h, m, wp, lp),
    }
}
