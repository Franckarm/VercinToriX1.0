// L'atelier en fenêtre Windows (atelier.exe) : Win32 et GDI directement, sans bibliothèque.
// En haut, des boutons (Ouvrir, Enregistrer, Lancer, Pas à pas, les entrées, l'étage, la vue). À gauche, le texte du
// programme (le contrôle d'édition de Windows : souris, sélection, presse-papiers, annulation). À droite, le cube :
// un étage de la mémoire, à plat (chaque mot est un pixel de sa couleur) ou en perspective isométrique (l'étage
// vu comme un cube de 256 × 256 × 256 mots, les mots non nuls en voxels). En dessous, ce qu'a donné le programme.
#![allow(non_snake_case, clippy::upper_case_acronyms)]

use super::{compiler_avec, compiler_lignes, dossier_de, executer_dans, lire_partition, nombres, Etat, Memoire, ARRET,
            ATTENTE_NS, CANAL_ENTREE, CANAL_SORTIE, CLAVIER, COMPLET, DIRECT, PAS_A_PAS, PILE_HAUT, VTXC};
use super::arbre::{self, Noeud};
use super::machine64::{compiler64, nombres64, situer_erreur, COMPLET64, PAS_A_PAS64, VTXC64};
use super::spu64::Spu64;
use super::pas64::{panneau64, table_des_lignes, Moteur, Pas, Vue64};
use super::spu128::Spu128;
use super::pas128::{image128, panneau128, presenter128};
use super::machine128::{compiler128, nombres128, COMPLET128, PAS_A_PAS128, VTXC128};
use std::collections::{HashMap, HashSet};
use std::sync::atomic::Ordering;
use std::sync::mpsc;
use core::ffi::c_void;
use std::path::{Path, PathBuf};
use std::sync::Mutex;

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
struct Point {
    x: i32,
    y: i32,
}
#[repr(C)]
struct Msg {
    hwnd: H,
    message: u32,
    wParam: usize,
    lParam: isize,
    time: u32,
    pt: Point,
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
struct BitmapInfoHeader {
    biSize: u32,
    biWidth: i32,
    biHeight: i32,
    biPlanes: u16,
    biBitCount: u16,
    biCompression: u32,
    biSizeImage: u32,
    biXPelsPerMeter: i32,
    biYPelsPerMeter: i32,
    biClrUsed: u32,
    biClrImportant: u32,
}
#[repr(C)]
struct BitmapInfo {
    bmiHeader: BitmapInfoHeader,
    bmiColors: [u32; 1],
}
#[repr(C)]
struct Accel {
    fVirt: u8,
    key: u16,
    cmd: u16,
}
#[repr(C)]
struct OpenFileName {
    lStructSize: u32,
    hwndOwner: H,
    hInstance: H,
    lpstrFilter: *const u16,
    lpstrCustomFilter: *mut u16,
    nMaxCustFilter: u32,
    nFilterIndex: u32,
    lpstrFile: *mut u16,
    nMaxFile: u32,
    lpstrFileTitle: *mut u16,
    nMaxFileTitle: u32,
    lpstrInitialDir: *const u16,
    lpstrTitle: *const u16,
    Flags: u32,
    nFileOffset: u16,
    nFileExtension: u16,
    lpstrDefExt: *const u16,
    lCustData: isize,
    lpfnHook: *const c_void,
    lpTemplateName: *const u16,
    pvReserved: *mut c_void,
    dwReserved: u32,
    FlagsEx: u32,
}

#[link(name = "user32")]
extern "system" {
    fn RegisterClassExW(c: *const WndClassEx) -> u16;
    fn CreateWindowExW(ex: u32, classe: *const u16, titre: *const u16, style: u32, x: i32, y: i32, l: i32, h: i32,
                       parent: H, menu: H, inst: H, param: *mut c_void) -> H;
    fn DefWindowProcW(h: H, m: u32, w: usize, l: isize) -> isize;
    fn CallWindowProcW(p: isize, h: H, m: u32, w: usize, l: isize) -> isize;
    fn SetWindowLongPtrW(h: H, index: i32, v: isize) -> isize;
    fn GetMessageW(m: *mut Msg, h: H, a: u32, b: u32) -> i32;
    fn TranslateMessage(m: *const Msg) -> i32;
    fn DispatchMessageW(m: *const Msg) -> isize;
    fn TranslateAcceleratorW(h: H, t: H, m: *mut Msg) -> i32;
    fn CreateAcceleratorTableW(a: *const Accel, n: i32) -> H;
    fn PostQuitMessage(code: i32);
    fn PostMessageW(h: H, m: u32, w: usize, l: isize) -> i32;
    fn SendMessageW(h: H, m: u32, w: usize, l: isize) -> isize;
    fn ShowWindow(h: H, n: i32) -> i32;
    fn MoveWindow(h: H, x: i32, y: i32, l: i32, ht: i32, redessiner: i32) -> i32;
    fn SetWindowTextW(h: H, t: *const u16) -> i32;
    fn GetWindowTextW(h: H, t: *mut u16, n: i32) -> i32;
    fn GetWindowTextLengthW(h: H) -> i32;
    fn CreateMenu() -> H;
    fn CreatePopupMenu() -> H;
    fn AppendMenuW(m: H, drapeaux: u32, id: usize, t: *const u16) -> i32;
    fn SetMenu(h: H, m: H) -> i32;
    fn GetMenu(h: H) -> H;
    fn CheckMenuItem(m: H, id: u32, drapeaux: u32) -> u32;
    fn MessageBoxW(h: H, t: *const u16, titre: *const u16, genre: u32) -> i32;
    fn InvalidateRect(h: H, r: *const Rect, effacer: i32) -> i32;
    fn BeginPaint(h: H, p: *mut PaintStruct) -> H;
    fn EndPaint(h: H, p: *const PaintStruct) -> i32;
    fn GetClientRect(h: H, r: *mut Rect) -> i32;
    fn LoadCursorW(inst: H, nom: *const u16) -> H;
    fn SetFocus(h: H) -> H;
    fn SetCapture(h: H) -> H;
    fn ReleaseCapture() -> i32;
    fn GetCapture() -> H;
    fn GetKeyState(vk: i32) -> i16;
    fn GetFocus() -> H;
    fn SetProcessDPIAware() -> i32;
    fn GetDC(h: H) -> H;
    fn ReleaseDC(h: H, dc: H) -> i32;
    fn DestroyWindow(h: H) -> i32;
    fn SetTimer(h: H, id: usize, ms: u32, f: *const c_void) -> usize;
    fn KillTimer(h: H, id: usize) -> i32;
    fn LoadImageW(inst: H, nom: *const u16, genre: u32, l: i32, h: i32, drapeaux: u32) -> H;
    fn FillRect(dc: H, r: *const Rect, pinceau: H) -> i32;
}
#[link(name = "gdi32")]
extern "system" {
    fn CreateFontW(h: i32, l: i32, esc: i32, orient: i32, graisse: i32, italique: u32, souligne: u32, barre: u32,
                   jeu: u32, precision: u32, decoupe: u32, qualite: u32, famille: u32, nom: *const u16) -> H;
    fn StretchDIBits(dc: H, xd: i32, yd: i32, ld: i32, hd: i32, xs: i32, ys: i32, ls: i32, hs: i32, bits: *const c_void,
                     info: *const BitmapInfo, usage: u32, rop: u32) -> i32;
    fn CreateSolidBrush(c: u32) -> H;
    fn SetTextColor(dc: H, c: u32) -> u32;
    fn SetBkColor(dc: H, c: u32) -> u32;
    fn GetDeviceCaps(dc: H, index: i32) -> i32;
    fn TextOutW(dc: H, x: i32, y: i32, t: *const u16, n: i32) -> i32;
    fn SetBkMode(dc: H, mode: i32) -> i32;
    fn SelectObject(dc: H, o: H) -> H;
    fn DeleteObject(o: H) -> i32;
    fn CreateCompatibleDC(dc: H) -> H;
    fn CreateCompatibleBitmap(dc: H, l: i32, h: i32) -> H;
    fn BitBlt(dc: H, x: i32, y: i32, l: i32, h: i32, src: H, xs: i32, ys: i32, rop: u32) -> i32;
    fn DeleteDC(dc: H) -> i32;
}
#[link(name = "kernel32")]
extern "system" {
    fn GetModuleHandleW(nom: *const u16) -> H;
}
#[link(name = "comdlg32")]
extern "system" {
    fn GetOpenFileNameW(o: *mut OpenFileName) -> i32;
    fn GetSaveFileNameW(o: *mut OpenFileName) -> i32;
}

// messages et styles
const WM_CREATE: u32 = 0x0001;
const WM_DESTROY: u32 = 0x0002;
const WM_SIZE: u32 = 0x0005;
const WM_PAINT: u32 = 0x000F;
const WM_CLOSE: u32 = 0x0010;
const WM_ERASEBKGND: u32 = 0x0014;
const WM_SETFONT: u32 = 0x0030;
const WM_CHAR: u32 = 0x0102;
const WM_COMMAND: u32 = 0x0111;
const WM_CTLCOLOREDIT: u32 = 0x0133;
const WM_CTLCOLORSTATIC: u32 = 0x0138;
const WM_LBUTTONDOWN: u32 = 0x0201;
const WM_MOUSEMOVE: u32 = 0x0200;
const WM_LBUTTONUP: u32 = 0x0202;
const WM_LBUTTONDBLCLK: u32 = 0x0203;
const WM_RBUTTONDOWN: u32 = 0x0204;
const WM_RBUTTONUP: u32 = 0x0205;
const WM_MBUTTONDOWN: u32 = 0x0207;
const WM_MBUTTONUP: u32 = 0x0208;
const WM_KEYDOWN: u32 = 0x0100;
const WM_KEYUP: u32 = 0x0101;
const WM_SYSKEYDOWN: u32 = 0x0104;
const WM_SYSKEYUP: u32 = 0x0105;
const WM_KILLFOCUS: u32 = 0x0008;
const WM_MOUSEWHEEL: u32 = 0x020A;
const WM_CUT: u32 = 0x0300;
const WM_COPY: u32 = 0x0301;
const WM_PASTE: u32 = 0x0302;
const WM_UNDO: u32 = 0x0304;
const WM_APP_FINI: u32 = 0x8001;
// la première image d'un programme : la vue du cube prend le clavier (demandé par message, pas pendant la peinture)
const WM_APP_CLAVIER: u32 = 0x8003;
const WM_TIMER: u32 = 0x0113;
const EM_GETSEL: u32 = 0x00B0;
const EM_SETSEL: u32 = 0x00B1;
const EM_SCROLLCARET: u32 = 0x00B7;
const EM_GETMODIFY: u32 = 0x00B8;
const EM_SETMODIFY: u32 = 0x00B9;
const EM_LINEINDEX: u32 = 0x00BB;
const EM_REPLACESEL: u32 = 0x00C2;
const EM_GETLINE: u32 = 0x00C4;
const EM_SETLIMITTEXT: u32 = 0x00C5;
const EM_LINEFROMCHAR: u32 = 0x00C9;
const EM_SETTABSTOPS: u32 = 0x00CB;
const EM_GETLINECOUNT: u32 = 0x00BA;
const EM_GETFIRSTVISIBLELINE: u32 = 0x00CE;
const EM_POSFROMCHAR: u32 = 0x00D6;
const EN_CHANGE: usize = 0x0300;
const WS_OVERLAPPEDWINDOW: u32 = 0x00CF_0000;
const WS_VISIBLE: u32 = 0x1000_0000;
const WS_CHILD: u32 = 0x4000_0000;
const WS_VSCROLL: u32 = 0x0020_0000;
const WS_HSCROLL: u32 = 0x0010_0000;
const WS_CLIPCHILDREN: u32 = 0x0200_0000;
const WS_TABSTOP: u32 = 0x0001_0000;
const WS_EX_CLIENTEDGE: u32 = 0x0000_0200;
const ES_MULTILINE: u32 = 0x0004;
const ES_AUTOVSCROLL: u32 = 0x0040;
const ES_AUTOHSCROLL: u32 = 0x0080;
const ES_NOHIDESEL: u32 = 0x0100;
const ES_READONLY: u32 = 0x0800;
const ES_WANTRETURN: u32 = 0x1000;
const SS_CENTERIMAGE: u32 = 0x0200;
const CW_USEDEFAULT: i32 = 0x8000_0000u32 as i32;
const MF_POPUP: u32 = 0x0010;
const MF_SEPARATOR: u32 = 0x0800;
const IDC_ARROW: usize = 32512;
const GWLP_WNDPROC: i32 = -4;
const MB_YESNOCANCEL: u32 = 0x0003;
const MB_ICONQUESTION: u32 = 0x0020;
const MB_ICONINFORMATION: u32 = 0x0040;
const IDYES: i32 = 6;
const IDCANCEL: i32 = 2;
const FVIRTKEY: u8 = 1;
const FCONTROL: u8 = 8;
const SRCCOPY: u32 = 0x00CC_0020;

// commandes (menus, raccourcis, boutons)
const C_NOUVEAU: u16 = 1001;
const C_OUVRIR: u16 = 1002;
const C_ENREGISTRER: u16 = 1003;
const C_ENREGISTRER_SOUS: u16 = 1004;
const C_QUITTER: u16 = 1005;
const C_ANNULER: u16 = 1101;
const C_COUPER: u16 = 1102;
const C_COPIER: u16 = 1103;
const C_COLLER: u16 = 1104;
const C_TOUT: u16 = 1105;
const C_LANCER: u16 = 1201;
const C_PAS: u16 = 1202;
const C_ARRETER: u16 = 1203;
const C_PAS_DESSUS: u16 = 1206;
const C_POINT: u16 = 1207;
const C_FIN_PAS: u16 = 1208;
const C_MACHINE64: u16 = 1209; // la machine suivante (Ctrl+M, le bouton)
const C_LUGUS: u16 = 1210;
const C_M32: u16 = 1211;
const C_M64: u16 = 1212;
const C_ASSOCIER: u16 = 1402;
const C_PURGER: u16 = 1205;
const C_ETAGE: u16 = 1300; // + 0..3
const C_VUE: u16 = 1310;
const C_LARGEUR: u16 = 1311;
const C_EFFACER: u16 = 1312;
const C_ONGLET_SORTIE: u16 = 1313;
const C_ONGLET_TERMINAL: u16 = 1314;
const C_ONGLET_PAS: u16 = 1315;
const C_APROPOS: u16 = 1401;
const C_GIF: u16 = 1316;
const C_PNG: u16 = 1317;

const FOND: u32 = 0x001E1E1E; // COLORREF : 0x00BBGGRR
const TEXTE: u32 = 0x00D4D4D4;

fn w(s: &str) -> Vec<u16> {
    s.encode_utf16().chain(std::iter::once(0)).collect()
}

/// L'état de la fenêtre : un seul fil (celui des messages) le touche ; le programme lancé tourne à côté et rend son
/// résultat par FINI.
struct Atelier {
    inst: H,
    fen: H,
    source: H,
    sortie: H,
    entrees: H,
    cube: H,
    etat: H,
    boutons: Vec<(H, u16)>,
    etiquettes: Vec<H>,
    police: H,
    police_ui: H,
    pinceau: H,
    echelle: f32,
    fichier: Option<PathBuf>,
    mem: Option<Memoire>,
    etage: u32,
    iso: bool,
    // la vue en quits : chaque mot en 4 × 4 cases de couleur de Belnap
    vue_quits: bool,
    largeur: u32,
    base: u32,
    zoom: f32,
    en_cours: bool,
    ancien_proc_source: isize,
    // sous le cube : le terminal (sortie du programme et commandes) et l'arbre des liaisons
    term_entree: H,
    // comme VS Code : l'onglet « Sortie » (le compte rendu de chaque exécution) et l'onglet « Terminal » (interactif)
    journal: H,
    onglets: [H; 3],
    // le pas à pas, dans la fenêtre même : la machine arrêtée entre deux lignes, les points d'arrêt, le panneau
    pas: Option<Pas>,
    points: HashSet<usize>,
    pas_texte: H,
    onglet: usize,
    ancien_proc_term: isize,
    arbre: H,
    noeuds: Vec<Noeud>,
    ouverts: HashSet<Vec<usize>>,
    defile: i32,
    choisi: Option<(u32, u32)>,
    // les numéros de ligne à gauche du texte, et l'image d'un programme qui dessine
    lignes: H,
    vue_lignes: (isize, isize),
    ligne_erreur: Option<usize>,
    dessin: bool,
    rx_sortie: Option<mpsc::Receiver<u32>>,
    tx_entree: Option<mpsc::Sender<u32>>,
    icone: H,
    // la machine : 32 (SPU-32, vtxc), 64 (SPU-64, vtxc64, mots de 64 bits) ou 128 (Lugus, vtxc128, mots de 128 bits) ;
    // et, après un programme de 64 ou 128 bits, ses vraies valeurs (le cube montre leurs points de 32 bits)
    machine: u32,
    vue64: Option<Vue64>,
    // la vue en perspective tournée à la souris : quarts de tour, décalage en pixels, glissement en cours
    quart: u32,
    decal: (i32, i32),
    glisse: Option<(i32, i32)>,
}

#[derive(Clone, Copy, PartialEq)]
enum Avance {
    Pas,
    Dessus,
    Continuer,
}

const LIMITE_PAS: u64 = 200_000_000;

static mut ATELIER: *mut Atelier = std::ptr::null_mut();
fn a() -> &'static mut Atelier {
    unsafe { &mut *ATELIER }
}

struct Fini {
    texte: String,
    resume: String,
    mem: Option<Memoire>,
    ligne_erreur: Option<usize>,
    vue64: Option<Vue64>,
    // l'image que le programme laisse (ecran(l, h)), en 0x00RRGGBB
    image: Option<(usize, usize, Vec<u32>)>,
}
static FINI: Mutex<Option<Fini>> = Mutex::new(None);

// ------------------------------------------------------------------------------------------------ texte des contrôles
fn lire_texte(h: H) -> String {
    unsafe {
        let n = GetWindowTextLengthW(h);
        let mut t = vec![0u16; n as usize + 1];
        let k = GetWindowTextW(h, t.as_mut_ptr(), n + 1);
        String::from_utf16_lossy(&t[..k.max(0) as usize])
    }
}
fn ecrire_texte(h: H, t: &str) {
    let t = t.replace("\r\n", "\n").replace('\n', "\r\n");
    unsafe {
        SetWindowTextW(h, w(&t).as_ptr());
    }
}
fn titre() {
    let at = a();
    let nom = at.fichier.as_ref().and_then(|f| f.file_name()).map(|n| n.to_string_lossy().into_owned()).unwrap_or("sans titre".into());
    let modifie = unsafe { SendMessageW(at.source, EM_GETMODIFY, 0, 0) } != 0;
    unsafe {
        SetWindowTextW(at.fen, w(&format!("{}{} — Atelier vtx · {}", nom, if modifie { " •" } else { "" },
                                          nom_machine(at.machine))).as_ptr());
    }
}
fn etat(t: &str) {
    unsafe {
        SetWindowTextW(a().etat, w(&format!("  {}", t)).as_ptr());
    }
}

fn nom_machine(m: u32) -> &'static str {
    match m {
        128 => "Lugus",
        64 => "SPU-64",
        _ => "SPU-32",
    }
}

fn compilateur_de(m: u32) -> &'static str {
    match m {
        128 => "vtxc128",
        64 => "vtxc64",
        _ => "vtxc",
    }
}

/// La machine : 128 bits (Lugus, compilée par vtxc128), 64 bits (SPU-64, compilée par vtxc64) ou 32 bits (SPU-32,
/// compilée par vtxc). Le menu la coche, le bouton et le titre la nomment ; le pas à pas en cours est arrêté (il tourne
/// sur l'autre machine).
fn choisir_machine(m: u32) {
    let at = a();
    if at.en_cours {
        etat("un programme tourne : la machine changera après lui");
        return;
    }
    if at.pas.is_some() {
        arreter_pas("pas à pas arrêté : changement de machine");
    }
    at.machine = m;
    unsafe {
        for (c, x) in [(C_M32, 32), (C_M64, 64), (C_LUGUS, 128)] {
            CheckMenuItem(GetMenu(at.fen), c as u32, if m == x { 8 } else { 0 }); // MF_CHECKED
        }
        if let Some(b) = at.boutons.iter().find(|b| b.1 == C_MACHINE64) {
            SetWindowTextW(b.0, w(&format!("Machine : {}", nom_machine(m))).as_ptr());
        }
    }
    titre();
}

// ------------------------------------------------------------------------------------------------ fichiers
fn dossier_de_depart() -> PathBuf {
    if let Ok(exe) = std::env::current_exe() {
        let mut p = exe.parent().map(|x| x.to_path_buf()).unwrap_or_default();
        for _ in 0..5 {
            if p.join("exemples").is_dir() {
                return p.join("exemples");
            }
            match p.parent() {
                Some(q) => p = q.to_path_buf(),
                None => break,
            }
        }
    }
    std::env::current_dir().unwrap_or_default()
}

fn dialogue_fichier(enregistrer: bool) -> Option<PathBuf> {
    let at = a();
    let mut tampon = vec![0u16; 2048];
    if let Some(f) = &at.fichier {
        let n: Vec<u16> = f.file_name().map(|n| n.to_string_lossy().encode_utf16().collect()).unwrap_or_default();
        tampon[..n.len().min(2000)].copy_from_slice(&n[..n.len().min(2000)]);
    }
    let filtre: Vec<u16> = "Programmes vtx (*.vtx)\0*.vtx\0Tous les fichiers\0*.*\0\0".encode_utf16().collect();
    let depart = at.fichier.as_ref().and_then(|f| f.parent().map(|p| p.to_path_buf())).unwrap_or_else(dossier_de_depart);
    let depart = w(&depart.to_string_lossy());
    let ext = w("vtx");
    let mut o = OpenFileName {
        lStructSize: std::mem::size_of::<OpenFileName>() as u32, hwndOwner: at.fen, hInstance: std::ptr::null_mut(),
        lpstrFilter: filtre.as_ptr(), lpstrCustomFilter: std::ptr::null_mut(), nMaxCustFilter: 0, nFilterIndex: 1,
        lpstrFile: tampon.as_mut_ptr(), nMaxFile: tampon.len() as u32, lpstrFileTitle: std::ptr::null_mut(), nMaxFileTitle: 0,
        lpstrInitialDir: depart.as_ptr(), lpstrTitle: std::ptr::null(),
        Flags: if enregistrer { 0x2 | 0x800 | 0x80000 } else { 0x1000 | 0x800 | 0x80000 },
        nFileOffset: 0, nFileExtension: 0, lpstrDefExt: ext.as_ptr(), lCustData: 0, lpfnHook: std::ptr::null(),
        lpTemplateName: std::ptr::null(), pvReserved: std::ptr::null_mut(), dwReserved: 0, FlagsEx: 0,
    };
    let ok = unsafe { if enregistrer { GetSaveFileNameW(&mut o) } else { GetOpenFileNameW(&mut o) } };
    if ok == 0 {
        return None;
    }
    let n = tampon.iter().position(|&c| c == 0).unwrap_or(0);
    Some(PathBuf::from(String::from_utf16_lossy(&tampon[..n])))
}

/// Un autre programme (Nouveau, Ouvrir) : les résultats du précédent disparaissent de toutes les vues.
fn effacer_resultats() {
    let at = a();
    if at.en_cours {
        return;
    }
    at.mem = None;
    at.vue64 = None;
    at.pas = None;
    at.noeuds.clear();
    at.ouverts.clear();
    at.choisi = None;
    at.dessin = false;
    *IMAGE.lock().unwrap() = None;
    at.ligne_erreur = None;
    at.vue_lignes = (-1, -1);
    ecrire_texte(at.journal, "");
    ecrire_texte(at.sortie, "");
    unsafe {
        for h in [at.cube, at.arbre, at.lignes] {
            InvalidateRect(h, std::ptr::null(), 0);
        }
    }
}

fn charger(chemin: &Path) {
    let at = a();
    let texte = std::fs::read_to_string(chemin).unwrap_or_else(|_| MODELE.to_string());
    ecrire_texte(at.source, &texte);
    unsafe {
        SendMessageW(at.source, EM_SETMODIFY, 0, 0);
    }
    at.fichier = Some(chemin.to_path_buf());
    effacer_resultats();
    // la machine : celle que le fichier nomme dans ses premières lignes (« // machine : spu-32 », « spu-64 » ou
    // « lugus ») ; sinon les exemples de la machine 32 bits (dossier « exemples ») s'ouvrent sur elle, ceux de Lugus
    // (dossier « exemples128 ») sur Lugus, tout le reste sur la SPU-64. Ctrl+M change toujours de machine.
    let dossier_nomme = |n: &str| chemin.components().any(|c| c.as_os_str().to_string_lossy().eq_ignore_ascii_case(n));
    let (m, pourquoi) = match machine_ecrite(&texte) {
        Some(m) => (m, " (écrite dans le fichier ; Ctrl+M pour changer)"),
        None if dossier_nomme("exemples") => (32, " (dossier exemples ; Ctrl+M pour changer)"),
        None if dossier_nomme("exemples128") => (128, " (dossier exemples128 ; Ctrl+M pour changer)"),
        None => (64, ""),
    };
    choisir_machine(m);
    etat(&format!("ouvert : {} · machine {}{}", chemin.display(), nom_machine(m), pourquoi));
}

/// La machine écrite en tête d'un programme, dans ses dix premières lignes : « // machine : spu-32 » (ou « 32 ») rend
/// Some(32), « spu-64 » (ou « 64 ») Some(64), « lugus » (ou « spu-128 », « 128 ») Some(128).
pub fn machine_ecrite(texte: &str) -> Option<u32> {
    for ligne in texte.lines().take(10) {
        let l = ligne.trim();
        if let Some(r) = l.strip_prefix("//") {
            let r = r.trim().to_lowercase();
            if let Some(m) = r.strip_prefix("machine") {
                let m = m.trim_start_matches([' ', ':', '\u{a0}']).trim();
                if m.starts_with("spu-32") || m.starts_with("spu32") || m.starts_with("32") {
                    return Some(32);
                }
                if m.starts_with("spu-64") || m.starts_with("spu64") || m.starts_with("64") {
                    return Some(64);
                }
                if m.starts_with("lugus") || m.starts_with("spu-128") || m.starts_with("spu128") || m.starts_with("128") {
                    return Some(128);
                }
            }
        }
    }
    None
}

/// Enregistre (en demandant un nom s'il n'y en a pas) ; false si l'utilisateur a renoncé ou si l'écriture échoue.
fn enregistrer(sous: bool) -> bool {
    let at = a();
    if sous || at.fichier.is_none() {
        match dialogue_fichier(true) {
            Some(f) => at.fichier = Some(f),
            None => return false,
        }
    }
    let f = at.fichier.clone().unwrap();
    let mut t = lire_texte(at.source).replace("\r\n", "\n").replace('\t', "    ");
    if !t.ends_with('\n') {
        t.push('\n');
    }
    match std::fs::write(&f, t) {
        Ok(_) => {
            unsafe {
                SendMessageW(at.source, EM_SETMODIFY, 0, 0);
            }
            titre();
            etat(&format!("enregistré : {}", f.display()));
            true
        }
        Err(e) => {
            message(&format!("Impossible d'enregistrer {} :\n{}", f.display(), e));
            false
        }
    }
}

fn message(t: &str) {
    unsafe {
        MessageBoxW(a().fen, w(t).as_ptr(), w("Atelier vtx").as_ptr(), MB_ICONINFORMATION);
    }
}

/// Les modifications non enregistrées : true si l'on peut continuer (enregistrées ou abandonnées).
fn peut_quitter() -> bool {
    let at = a();
    if unsafe { SendMessageW(at.source, EM_GETMODIFY, 0, 0) } == 0 {
        return true;
    }
    let r = unsafe {
        MessageBoxW(at.fen, w("Le programme a été modifié. Enregistrer les modifications ?").as_ptr(), w("Atelier vtx").as_ptr(),
                    MB_YESNOCANCEL | MB_ICONQUESTION)
    };
    match r {
        IDYES => enregistrer(false),
        IDCANCEL => false,
        _ => true,
    }
}

const MODELE: &str = "fonction principal() {\n    afficher(\"Bonjour, Vercintorix !\");\n}\n";

// ------------------------------------------------------------------------------------------------ lancer
fn lancer() {
    let at = a();
    if at.en_cours {
        etat("un programme tourne déjà");
        return;
    }
    at.pas = None;
    // sans nom : on lance quand même, depuis un fichier temporaire (rien n'est demandé)
    let fichier = if at.fichier.is_none() {
        let f = std::env::temp_dir().join("sans titre.vtx");
        if std::fs::write(&f, lire_texte(at.source).replace("\r\n", "\n")).is_err() {
            message("Impossible d'écrire le fichier temporaire.");
            return;
        }
        f
    } else {
        if !enregistrer(false) {
            return;
        }
        at.fichier.clone().unwrap()
    };
    let source = lire_texte(at.source).replace("\r\n", "\n");
    let entrees: Vec<u64> = lire_texte(at.entrees).split_whitespace().filter_map(|x| x.parse::<u64>().ok()).collect();
    let m = at.machine;
    at.en_cours = true;
    // la mémoire du programme précédent est rendue avant d'en prendre une autre
    at.mem = None;
    at.vue64 = None;
    at.noeuds.clear();
    at.ouverts.clear();
    unsafe {
        InvalidateRect(at.cube, std::ptr::null(), 0);
        InvalidateRect(at.arbre, std::ptr::null(), 0);
    }
    let nom = fichier.file_name().map(|n| n.to_string_lossy().into_owned()).unwrap_or_default();
    let machine = nom_machine(m);
    ajouter_texte(at.sortie, &format!("\n▶ {} · {}\n", nom, machine));
    ecrire_texte(at.journal, &format!("▶ {} : compilation et exécution sur la machine {}…\n", nom, machine));
    montrer_onglet(1);
    etat("compilation et exécution… (la ligne sous le terminal répond au programme ; Maj+F5 l'arrête)");
    // la console du programme passe par le terminal
    let (tx_s, rx_s) = mpsc::channel();
    let (tx_e, rx_e) = mpsc::channel();
    *CANAL_SORTIE.lock().unwrap() = Some(tx_s);
    *CANAL_ENTREE.lock().unwrap() = Some(rx_e);
    at.rx_sortie = Some(rx_s);
    at.tx_entree = Some(tx_e);
    ARRET.store(false, Ordering::Relaxed);
    // les images du programme (presenter()) viennent dans la vue du cube ; la souris et le clavier y vont au programme
    *IMAGE.lock().unwrap() = None;
    at.dessin = false;
    super::hote::remettre();
    super::hote::FENETRE.store(true, Ordering::Relaxed);
    super::gobatix::installer(Some(Box::new(VueAtelier { cube: at.cube as usize })));
    ANNONCEE.store(false, Ordering::Relaxed);
    PEINTURE.store(false, Ordering::Relaxed);
    unsafe {
        SetFocus(at.term_entree);
        SetTimer(at.fen, 1, 30, std::ptr::null());
    }
    let fen = at.fen as usize;
    std::thread::spawn(move || {
        let fini = if m == 128 {
            executer128(&fichier, &source, &entrees)
        } else if m == 64 {
            executer64(&fichier, &source, &entrees)
        } else {
            let e32: Vec<u32> = entrees.iter().map(|&x| x as u32).collect();
            executer(&fichier, &source, &e32)
        };
        DIRECT.store(false, Ordering::Relaxed);
        CLAVIER.store(0, Ordering::Relaxed);
        *CANAL_SORTIE.lock().unwrap() = None;
        *CANAL_ENTREE.lock().unwrap() = None;
        *FINI.lock().unwrap() = Some(fini);
        unsafe {
            PostMessageW(fen as H, WM_APP_FINI, 0, 0);
        }
    });
}

fn executer(fichier: &Path, source: &str, entrees: &[u32]) -> Fini {
    let f = fichier.to_string_lossy().into_owned();
    let base = dossier_de(&f);
    let nom = fichier.file_name().map(|n| n.to_string_lossy().into_owned()).unwrap_or_default();
    let t0 = std::time::Instant::now();
    let (mots, table) = match compiler_avec(&nombres(VTXC), source, &base, COMPLET) {
        Ok(r) => r,
        Err(e) => {
            let ligne = e.find("erreur ligne ").and_then(|p| e[p + 13..].chars().take_while(|c| c.is_ascii_digit()).collect::<String>().parse().ok());
            let t = e.replace("erreur ligne ", &format!("erreur {}, ligne ", nom));
            return Fini { texte: t.clone(), resume: t, mem: None, ligne_erreur: ligne, vue64: None, image: None };
        }
    };
    let tc = t0.elapsed().as_secs_f64();
    let mut mem = Memoire::new(false);
    super::charger(&mut mem, &mots);
    let cyl = super::cylindres_voulus(None);
    let part = if table.first().copied().unwrap_or(0) == 0 || cyl <= 1 { None } else { Some(lire_partition(&table, cyl)) };
    // la console du programme (et pas celle du compilateur) va dans la fenêtre d'exécution
    DIRECT.store(true, Ordering::Relaxed);
    CLAVIER.store(2, Ordering::Relaxed);
    ATTENTE_NS.store(0, Ordering::Relaxed);
    let t1 = std::time::Instant::now();
    // sans limite : un programme interactif tourne tant qu'on veut ; Maj+F5 l'arrête
    let r = executer_dans(&mem, entrees, u64::MAX / 4, Some(Path::new(&base)), part.as_ref());
    // le temps passé à attendre le clavier n'est pas du calcul
    let attente = ATTENTE_NS.load(Ordering::Relaxed) as f64 / 1e9;
    let te = (t1.elapsed().as_secs_f64() - attente).max(0.0);
    let duree = |t: f64| if t < 1.0 { format!("{:.0} ms", t * 1000.0) } else { format!("{:.2} s", t) };
    let mut texte = String::new();
    let mut resume = String::new();
    match r {
        Ok(r) => {
            resume.push_str(&format!("{} mots, compilé en {} ; {} instructions en {}{}\n", mots.len(), duree(tc), r.pas, duree(te),
                                     if attente > 0.0 { format!(" (et {} à attendre le clavier)", duree(attente)) } else { String::new() }));
            if !r.sorties.is_empty() {
                let s: Vec<String> = r.sorties.iter().map(|v| v.to_string()).collect();
                resume.push_str(&format!("sorties : {}\n", s.join(",")));
            }
            // la sortie : ce que le programme a écrit, puis le bilan
            texte.extend(r.texte.iter().filter_map(|&v| char::from_u32(v & 0x1F_FFFF)));
            if !texte.is_empty() && !texte.ends_with('\n') {
                texte.push('\n');
            }
            texte.push_str("──────────\n");
            texte.push_str(&resume);
        }
        Err(e) => {
            resume.push_str(&format!("{}\n", if e.contains("arrêté") { "programme arrêté".to_string() } else { format!("erreur à l'exécution : {}", e) }));
            texte.push_str(&resume);
        }
    }
    let image = image32(&mem);
    Fini { texte, resume, mem: Some(mem), ligne_erreur: None, vue64: None, image }
}

/// F5 sur la machine 64 bits : vtxc64 (embarqué) compile, la SPU-64 exécute ; sa console passe par le terminal.
fn executer64(fichier: &Path, source: &str, entrees: &[u64]) -> Fini {
    let f = fichier.to_string_lossy().into_owned();
    let base = dossier_de(&f);
    let t0 = std::time::Instant::now();
    let mots = match compiler64(&nombres64(VTXC64), source, &base, COMPLET64, false) {
        Ok((m, _, _)) => m,
        Err(e) => {
            let (t, ligne) = situer_erreur(&e, &f);
            return Fini { texte: t.clone(), resume: t, mem: None, ligne_erreur: ligne, vue64: None, image: None };
        }
    };
    let tc = t0.elapsed().as_secs_f64();
    let mut s = Spu64::nouveau();
    s.dossier = Some(PathBuf::from(&base));
    s.charger(&mots);
    s.entree.extend(entrees.iter().copied());
    // la console : chaque caractère part aussitôt vers le terminal, et il est gardé pour le compte rendu
    let ecrit = std::rc::Rc::new(std::cell::RefCell::new(String::new()));
    let garde = ecrit.clone();
    s.console_ecrire = Some(Box::new(move |v: u64| {
        if let Some(tx) = CANAL_SORTIE.lock().unwrap().as_ref() {
            let _ = tx.send((v & 0x1F_FFFF) as u32);
        }
        if let Some(c) = char::from_u32((v & 0x1F_FFFF) as u32) {
            garde.borrow_mut().push(c);
        }
    }));
    s.console_lire = Some(Box::new(|| {
        let t = std::time::Instant::now();
        let r = CANAL_ENTREE.lock().unwrap();
        let v = match r.as_ref().map(|c| c.recv()) {
            Some(Ok(v)) => v as u64,
            _ => u64::MAX,
        };
        ATTENTE_NS.fetch_add(t.elapsed().as_nanos() as u64, Ordering::Relaxed);
        v
    }));
    s.arret = Some(&ARRET);
    s.parler = Some(super::parler_hote);
    s.presenter = Some(Box::new(super::gobatix::presenter64));
    ATTENTE_NS.store(0, Ordering::Relaxed);
    let t1 = std::time::Instant::now();
    let r = s.executer(u64::MAX / 4);
    let attente = ATTENTE_NS.load(Ordering::Relaxed) as f64 / 1e9;
    let te = (t1.elapsed().as_secs_f64() - attente).max(0.0);
    let duree = |t: f64| if t < 1.0 { format!("{:.0} ms", t * 1000.0) } else { format!("{:.2} s", t) };
    s.console_ecrire = None;
    s.console_lire = None;
    let mut texte = ecrit.borrow().clone();
    let mut resume = String::new();
    match r {
        Ok(()) => {
            resume.push_str(&format!("SPU-64 · {} mots, compilé en {} ; {} instructions en {}{}\n", mots.len(), duree(tc), s.pas, duree(te),
                                     if attente > 0.0 { format!(" (et {} à attendre le clavier)", duree(attente)) } else { String::new() }));
            if !s.sortie.is_empty() {
                let v: Vec<String> = s.sortie.iter().map(|v| v.to_string()).collect();
                resume.push_str(&format!("sorties : {}\n", v.join(",")));
            }
            if !texte.is_empty() && !texte.ends_with('\n') {
                texte.push('\n');
            }
            texte.push_str("──────────\n");
            texte.push_str(&resume);
        }
        Err(e) => {
            resume.push_str(&format!("{}\n", if e.contains("arrêté") { "programme arrêté".to_string() } else { format!("erreur à l'exécution : {}", e) }));
            if !texte.is_empty() && !texte.ends_with('\n') {
                texte.push('\n');
            }
            texte.push_str(&resume);
        }
    }
    let image = super::gobatix::image64(&s);
    let mut vue = Vue64::depuis(&s);
    let mem = vue.memoire();
    Fini { texte, resume, mem: Some(mem), ligne_erreur: None, vue64: Some(vue), image }
}

/// F5 sur Lugus : vtxc128 (embarqué) compile, Lugus exécute ; sa console passe par le terminal.
fn executer128(fichier: &Path, source: &str, entrees: &[u64]) -> Fini {
    let f = fichier.to_string_lossy().into_owned();
    let base = dossier_de(&f);
    let t0 = std::time::Instant::now();
    let mots = match compiler128(&nombres128(VTXC128), source, &base, COMPLET128, false) {
        Ok((m, _, _)) => m,
        Err(e) => {
            let (t, ligne) = situer_erreur(&e, &f);
            return Fini { texte: t.clone(), resume: t, mem: None, ligne_erreur: ligne, vue64: None, image: None };
        }
    };
    let tc = t0.elapsed().as_secs_f64();
    let mut s = Spu128::nouveau();
    s.dossier = Some(PathBuf::from(&base));
    s.charger(&mots);
    s.entree.extend(entrees.iter().map(|&x| x as u128));
    let ecrit = std::rc::Rc::new(std::cell::RefCell::new(String::new()));
    let garde = ecrit.clone();
    s.console_ecrire = Some(Box::new(move |v: u128| {
        if let Some(tx) = CANAL_SORTIE.lock().unwrap().as_ref() {
            let _ = tx.send((v & 0x1F_FFFF) as u32);
        }
        if let Some(c) = char::from_u32((v & 0x1F_FFFF) as u32) {
            garde.borrow_mut().push(c);
        }
    }));
    s.console_lire = Some(Box::new(|| {
        let t = std::time::Instant::now();
        let r = CANAL_ENTREE.lock().unwrap();
        let v = match r.as_ref().map(|c| c.recv()) {
            Some(Ok(v)) => v as u128,
            _ => u128::MAX,
        };
        ATTENTE_NS.fetch_add(t.elapsed().as_nanos() as u64, Ordering::Relaxed);
        v
    }));
    s.arret = Some(&ARRET);
    s.parler = Some(super::parler_hote);
    s.presenter = Some(Box::new(presenter128));
    ATTENTE_NS.store(0, Ordering::Relaxed);
    let t1 = std::time::Instant::now();
    let r = s.executer(u64::MAX / 4);
    let attente = ATTENTE_NS.load(Ordering::Relaxed) as f64 / 1e9;
    let te = (t1.elapsed().as_secs_f64() - attente).max(0.0);
    let duree = |t: f64| if t < 1.0 { format!("{:.0} ms", t * 1000.0) } else { format!("{:.2} s", t) };
    s.console_ecrire = None;
    s.console_lire = None;
    let mut texte = ecrit.borrow().clone();
    let mut resume = String::new();
    match r {
        Ok(()) => {
            resume.push_str(&format!("Lugus · {} mots, compilé en {} ; {} instructions en {}{}\n", mots.len(), duree(tc), s.pas, duree(te),
                                     if attente > 0.0 { format!(" (et {} à attendre le clavier)", duree(attente)) } else { String::new() }));
            if !s.sortie.is_empty() {
                let v: Vec<String> = s.sortie.iter().map(|v| v.to_string()).collect();
                resume.push_str(&format!("sorties : {}\n", v.join(",")));
            }
            if !texte.is_empty() && !texte.ends_with('\n') {
                texte.push('\n');
            }
            texte.push_str("──────────\n");
            texte.push_str(&resume);
        }
        Err(e) => {
            resume.push_str(&format!("{}\n", if e.contains("arrêté") { "programme arrêté".to_string() } else { format!("erreur à l'exécution : {}", e) }));
            if !texte.is_empty() && !texte.ends_with('\n') {
                texte.push('\n');
            }
            texte.push_str(&resume);
        }
    }
    let image = image128(&s);
    let mut vue = Vue64::depuis128(&s);
    let mem = vue.memoire();
    Fini { texte, resume, mem: Some(mem), ligne_erreur: None, vue64: Some(vue), image }
}

fn fini() {
    let at = a();
    at.en_cours = false;
    let f = match FINI.lock().unwrap().take() {
        Some(f) => f,
        None => return,
    };
    super::gobatix::installer(None);
    super::hote::FENETRE.store(false, Ordering::Relaxed);
    super::hote::tout_relacher();
    unsafe {
        // la vue du cube rend la souris si elle la tenait (pas l'éditeur, qui sélectionne peut-être)
        if GetCapture() == at.cube {
            ReleaseCapture();
        }
    }
    // une animation en cours d'enregistrement est écrite à la fin du programme
    if super::gobatix::ENREGISTRER.load(Ordering::Relaxed) {
        basculer_enregistrement();
    }
    if let Some(img) = f.image.clone() {
        *IMAGE.lock().unwrap() = Some(img);
    }
    // le terminal : le reste de ce que le programme a écrit, puis le bilan
    vider_sortie_programme();
    at.rx_sortie = None;
    at.tx_entree = None;
    unsafe {
        KillTimer(at.fen, 1);
    }
    let _ = &f.texte;
    ajouter_texte(at.sortie, &format!("\n── {}", f.resume));
    // la sortie : le compte rendu complet ; on y passe après l'exécution, sauf si le programme a dialogué au clavier
    ajouter_texte(at.journal, &f.texte);
    let a_dialogue = ATTENTE_NS.load(Ordering::Relaxed) > 0;
    if f.ligne_erreur.is_some() || !a_dialogue {
        montrer_onglet(0);
    }
    at.ligne_erreur = f.ligne_erreur;
    at.vue_lignes = (-1, -1);
    if let Some(l) = f.ligne_erreur {
        // la ligne fautive est sélectionnée dans le texte (et son numéro passe en rouge)
        unsafe {
            let debut = SendMessageW(at.source, EM_LINEINDEX, l.saturating_sub(1), 0);
            let fin = SendMessageW(at.source, EM_LINEINDEX, l, 0);
            let fin = if fin < 0 { GetWindowTextLengthW(at.source) as isize } else { fin };
            SendMessageW(at.source, EM_SETSEL, debut.max(0) as usize, fin);
            SendMessageW(at.source, EM_SCROLLCARET, 0, 0);
            SetFocus(at.source);
        }
        etat(&format!("erreur de compilation, ligne {}", l));
        return;
    }
    if let Some(m) = f.mem {
        // si l'étage regardé est vide, on montre le premier étage (1 à 3) qui contient quelque chose (tout l'étage :
        // le tas commence à 8 388 608)
        let vide = |e: u32| (0..=0xFF_FFFFu32).all(|x| m.lit(e, x) == 0);
        if vide(at.etage) {
            if let Some(e) = (1..4u32).find(|&e| !vide(e)) {
                at.etage = e;
                at.base = 0;
            }
        }
        // un programme qui dessine (ecran(l, h)) : la vue montre son image (les deux machines)
        at.dessin = IMAGE.lock().unwrap().is_some();
        at.mem = Some(m);
        at.vue64 = f.vue64;
        at.choisi = None;
        rafraichir_arbre();
    }
    if let Some(v) = &at.vue64 {
        etat(&format!("programme terminé ({}) · cube : étage {}, cube 0, points vus en 32 bits · clic ou « mot » : la vraie valeur \
                       · « cube ÉTAGE FRÉQUENCE » change de cube", v.nom(), at.etage));
    } else {
        etat(&format!("programme terminé · cube : étage {} · l'arbre montre les objets du tas", at.etage));
    }
    unsafe {
        InvalidateRect(at.cube, std::ptr::null(), 0);
    }
}

// ------------------------------------------------------------------------------------------------ les numéros de ligne
fn suivre_lignes() {
    let at = a();
    let v = unsafe { (SendMessageW(at.source, EM_GETFIRSTVISIBLELINE, 0, 0), SendMessageW(at.source, EM_GETLINECOUNT, 0, 0)) };
    if v != at.vue_lignes {
        at.vue_lignes = v;
        unsafe {
            InvalidateRect(at.lignes, std::ptr::null(), 0);
        }
    }
}

unsafe extern "system" fn proc_lignes(h: H, m: u32, wp: usize, lp: isize) -> isize {
    match m {
        WM_ERASEBKGND => 1,
        WM_PAINT => {
            let at = a();
            let mut ps: PaintStruct = std::mem::zeroed();
            let dc = BeginPaint(h, &mut ps);
            let mut r = Rect::default();
            GetClientRect(h, &mut r);
            let mdc = CreateCompatibleDC(dc);
            let bmp = CreateCompatibleBitmap(dc, r.right.max(1), r.bottom.max(1));
            let ancien_bmp = SelectObject(mdc, bmp);
            let fond = CreateSolidBrush(0x0018_1818);
            FillRect(mdc, &r, fond);
            DeleteObject(fond);
            let ancienne_police = SelectObject(mdc, at.police);
            SetBkMode(mdc, 1);
            let premiere = SendMessageW(at.source, EM_GETFIRSTVISIBLELINE, 0, 0).max(0);
            let total = SendMessageW(at.source, EM_GETLINECOUNT, 0, 0);
            // la position de chaque ligne visible est demandée au texte lui-même (EM_POSFROMCHAR) : toujours alignée
            let decalage = (2.0 * at.echelle) as i32; // le bord du texte
            let mut n = premiere;
            while n < total {
                let debut = SendMessageW(at.source, EM_LINEINDEX, n as usize, 0);
                if debut < 0 {
                    break;
                }
                let pos = SendMessageW(at.source, EM_POSFROMCHAR, debut as usize, 0);
                let y = ((pos >> 16) & 0xFFFF) as i16 as i32 + decalage;
                if y > r.bottom {
                    break;
                }
                let erreur = at.ligne_erreur == Some(n as usize + 1);
                // le pas à pas : la ligne où la machine s'est arrêtée (▶, en jaune) et les points d'arrêt (●, en rouge)
                let courante = at.pas.as_ref().and_then(|p| p.ligne) == Some(n as usize);
                let point = at.points.contains(&(n as usize));
                SetTextColor(mdc, if erreur { 0x0060_60F0 } else if courante { 0x0040_D0F0 } else { 0x0070_7070 });
                let t = w(&format!("{:>4}", n + 1));
                TextOutW(mdc, (4.0 * at.echelle) as i32, y, t.as_ptr(), t.len() as i32 - 1);
                if point {
                    SetTextColor(mdc, 0x0040_40E0);
                    let p = w("●");
                    TextOutW(mdc, 0, y, p.as_ptr(), 1);
                }
                if courante {
                    SetTextColor(mdc, 0x0040_D0F0);
                    let p = w("▶");
                    TextOutW(mdc, (if point { 9.0 } else { 0.0 } * at.echelle) as i32, y, p.as_ptr(), 1);
                }
                n += 1;
            }
            BitBlt(dc, 0, 0, r.right, r.bottom, mdc, 0, 0, SRCCOPY);
            SelectObject(mdc, ancienne_police);
            SelectObject(mdc, ancien_bmp);
            DeleteObject(bmp);
            DeleteDC(mdc);
            EndPaint(h, &ps);
            0
        }
        _ => DefWindowProcW(h, m, wp, lp),
    }
}

// ------------------------------------------------------------------------------------------------ le terminal
/// Ajoute du texte à la fin d'un contrôle d'édition (le terminal).
fn ajouter_texte(h: H, t: &str) {
    if h.is_null() || t.is_empty() {
        return;
    }
    let t = t.replace("\r\n", "\n").replace('\n', "\r\n");
    unsafe {
        let n = GetWindowTextLengthW(h) as usize;
        SendMessageW(h, EM_SETSEL, n, n as isize);
        SendMessageW(h, EM_REPLACESEL, 0, w(&t).as_ptr() as isize);
        SendMessageW(h, EM_SCROLLCARET, 0, 0);
    }
}

/// Ce que le programme a écrit depuis la dernière fois, vers le terminal.
fn vider_sortie_programme() {
    let at = a();
    let mut t = String::new();
    if let Some(rx) = &at.rx_sortie {
        while let Ok(v) = rx.try_recv() {
            if let Some(c) = char::from_u32(v & 0x1F_FFFF) {
                t.push(c);
            }
        }
    }
    ajouter_texte(at.sortie, &t);
}

/// Montre l'onglet « Sortie » (0), « Terminal » (1) ou « Pas à pas » (2).
fn montrer_onglet(i: usize) {
    let at = a();
    at.onglet = i;
    unsafe {
        ShowWindow(at.journal, if i == 0 { 5 } else { 0 });
        ShowWindow(at.sortie, if i == 1 { 5 } else { 0 });
        ShowWindow(at.term_entree, if i == 1 { 5 } else { 0 });
        ShowWindow(at.pas_texte, if i == 2 { 5 } else { 0 });
        // l'onglet actif est écrit entre crochets
        SetWindowTextW(at.onglets[0], w(if i == 0 { "[ Sortie ]" } else { "Sortie" }).as_ptr());
        SetWindowTextW(at.onglets[1], w(if i == 1 { "[ Terminal ]" } else { "Terminal" }).as_ptr());
        SetWindowTextW(at.onglets[2], w(if i == 2 { "[ Pas à pas ]" } else { "Pas à pas" }).as_ptr());
        if i == 1 {
            SetFocus(at.term_entree);
        }
    }
}

/// Entrée dans la ligne du terminal : pendant l'exécution, la ligne part vers le programme (lire_car(1), lire_ligne()) ;
/// sinon c'est une commande de l'atelier.
fn ligne_terminal() {
    let at = a();
    let t = lire_texte(at.term_entree);
    unsafe {
        SetWindowTextW(at.term_entree, w("").as_ptr());
    }
    if at.en_cours {
        if let Some(tx) = &at.tx_entree {
            for c in t.chars() {
                let _ = tx.send(c as u32);
            }
            let _ = tx.send(10);
            ajouter_texte(at.sortie, &format!("{}\n", t));
        }
        return;
    }
    ajouter_texte(at.sortie, &format!("› {}\n", t));
    let mots: Vec<&str> = t.split_whitespace().collect();
    let nombre = |s: &str| -> Option<u32> {
        let s = s.trim_start_matches('@');
        if let Some(h) = s.strip_prefix('#').or_else(|| s.strip_prefix("0x")) { u32::from_str_radix(h, 16).ok() } else { s.parse().ok() }
    };
    match mots.first().copied() {
        None => {}
        Some("aide") => ajouter_texte(at.sortie, "commandes : lancer · arreter · machine 32|64|128 · cubes · cube ÉTAGE FRÉQUENCE · mot ADRESSE · mot ÉTAGE ADRESSE · etage N · arbre · effacer · purger\n\
            ADRESSE : décimale, #hex ou 0xhex. L'arbre montre le mot choisi et les objets du tas (tableaux, dicos, textes)\n\
            avec leurs liaisons ; un clic sur une ligne l'ouvre ou la ferme. À plat (F6), un clic dans le cube choisit un mot.\n"),
        Some("lancer") => lancer(),
        Some("cubes") if at.vue64.is_some() => {
            let v = at.vue64.as_ref().unwrap();
            let mut t = format!("{} · les cubes écrits par le programme :\n", v.nom());
            for e in 0..4u32 {
                let c = v.cubes(e);
                if !c.is_empty() {
                    let l: Vec<String> = c.iter().map(|x| x.to_string()).collect();
                    t.push_str(&format!("   étage {} : {} (regardé : {})\n", e, l.join(", "), v.frequences[e as usize]));
                }
            }
            ajouter_texte(at.sortie, &t);
        }
        Some("cubes") => {
            let d = at.fichier.as_ref().and_then(|f| f.parent().map(|p| p.to_path_buf())).unwrap_or_else(dossier_de_depart);
            ajouter_texte(at.sortie, &super::texte_cubes(at.mem.as_ref(), &d));
        }
        Some("cube") if at.vue64.is_some() => match (mots.get(1).and_then(|x| nombre(x)), mots.get(2).and_then(|x| nombre(x))) {
            (Some(e), Some(f)) if e < 4 && f < 1 << 24 => {
                let mut nom = "";
                if let (Some(v), Some(m)) = (at.vue64.as_mut(), at.mem.as_ref()) {
                    v.accorder(m, e, f);
                    nom = v.nom();
                }
                ajouter_texte(at.sortie, &format!("l'étage {} regarde maintenant le cube {} ({})\n", e, f, nom));
                commande(C_ETAGE + e as u16);
                rafraichir_arbre();
            }
            _ => ajouter_texte(at.sortie, "cube ÉTAGE FRÉQUENCE (étage 0 à 3) : montre ce cube de la machine 64 ou 128 bits ; l'arbre liste les cubes écrits\n"),
        },
        Some("machine") => {
            match mots.get(1).copied() {
                Some("32") => choisir_machine(32),
                Some("64") => choisir_machine(64),
                Some("128") | Some("lugus") => choisir_machine(128),
                _ => {}
            }
            ajouter_texte(at.sortie, &format!("machine : {} (machine 32, 64 ou 128 pour changer)\n", nom_machine(a().machine)));
        }
        Some("cube") => match (mots.get(1).and_then(|x| nombre(x)), mots.get(2).and_then(|x| nombre(x))) {
            (Some(e), Some(f)) if (1..4).contains(&e) && at.mem.is_some() => {
                let d = at.fichier.as_ref().and_then(|f| f.parent().map(|p| p.to_path_buf())).unwrap_or_else(dossier_de_depart);
                if let Some(m) = &at.mem {
                    m.accorder(e, f, Some(&d));
                }
                ajouter_texte(at.sortie, &format!("l'étage {} regarde maintenant le cube {}\n", e, f));
                commande(C_ETAGE + e as u16);
            }
            _ => ajouter_texte(at.sortie, "cube ÉTAGE FRÉQUENCE (étage 1 à 3, après une exécution) : montre ce cube, en mémoire ou sur disque\n"),
        },
        Some("arreter") | Some("arrêter") => commande(C_ARRETER),
        Some("effacer") => ecrire_texte(at.sortie, ""),
        Some("purger") => {
            effacer_resultats();
            ajouter_texte(at.sortie, "mémoire du programme rendue à Windows (cube et arbre vidés)\n");
        }
        Some("arbre") => {
            rafraichir_arbre();
            ajouter_texte(at.sortie, "arbre recalculé\n");
        }
        Some("etage") | Some("étage") => match mots.get(1).and_then(|x| nombre(x)) {
            Some(e) if e < 4 => commande(C_ETAGE + e as u16),
            _ => ajouter_texte(at.sortie, "etage 0, 1, 2 ou 3\n"),
        },
        Some("mot") => {
            let (e, adr) = match (mots.get(1).and_then(|x| nombre(x)), mots.get(2).and_then(|x| nombre(x))) {
                (Some(e), Some(adr)) if e < 4 => (e, adr),
                (Some(adr), None) => (at.etage, adr),
                _ => {
                    ajouter_texte(at.sortie, "mot ADRESSE, ou mot ÉTAGE ADRESSE\n");
                    return;
                }
            };
            choisir_mot(e, adr & 0xFF_FFFF);
        }
        Some(x) => ajouter_texte(at.sortie, &format!("« {} » : commande inconnue (tapez aide)\n", x)),
    }
}

unsafe extern "system" fn proc_term(h: H, m: u32, wp: usize, lp: isize) -> isize {
    if m == WM_CHAR && wp == 13 {
        ligne_terminal();
        return 0;
    }
    CallWindowProcW(a().ancien_proc_term, h, m, wp, lp)
}

// ------------------------------------------------------------------------------------------------ l'arbre des liaisons
/// Le mot choisi (clic dans le cube, ou « mot ») : son décodage dans le terminal, et en tête de l'arbre.
fn choisir_mot(e: u32, adr: u32) {
    let at = a();
    let mem = match &at.mem {
        Some(m) => m,
        None => {
            ajouter_texte(at.sortie, "rien à lire : lancez d'abord le programme\n");
            return;
        }
    };
    let mut t = format!("@{}[{}]\n", e, adr);
    let lignes = match &at.vue64 {
        Some(v) => v.decoder(e, v.lit(e, (v.frequences[e as usize & 3] as u128) << 24 | adr as u128)),
        None => arbre::decoder(mem.lit(e, adr)),
    };
    for l in lignes {
        t.push_str(&format!("   {}\n", l));
    }
    ajouter_texte(at.sortie, &t);
    at.choisi = Some((e, adr));
    rafraichir_arbre();
}

fn rafraichir_arbre() {
    let at = a();
    at.noeuds.clear();
    at.ouverts.clear();
    at.defile = 0;
    if let Some(v) = &at.vue64 {
        // machine 64 ou 128 bits : le mot choisi (sa vraie valeur) et les cubes écrits de chaque étage
        if let Some((e, adr)) = at.choisi {
            let f = v.frequences[e as usize & 3];
            let val = v.lit(e, (f as u128) << 24 | adr as u128);
            let enfants = v.decoder(e, val).into_iter().map(|l| Noeud::feuille(l, None)).collect();
            at.noeuds.push(Noeud { texte: format!("@{}[{}] (cube {})", e, adr, f), mot: Some(v.point32(val)), logique: None, enfants });
        }
        let mut cubes = Noeud::feuille(format!("{} : les cubes écrits (étage : fréquences)", v.nom()), None);
        for e in 0..4u32 {
            let c = v.cubes(e);
            if !c.is_empty() {
                let l: Vec<String> = c.iter().take(24).map(|x| x.to_string()).collect();
                cubes.enfants.push(Noeud::feuille(format!("étage {} : {}{}", e, l.join(", "), if c.len() > 24 { " …" } else { "" }), None));
            }
        }
        at.noeuds.push(cubes);
        for i in 0..at.noeuds.len() {
            at.ouverts.insert(vec![i]);
        }
    } else if let Some(mem) = &at.mem {
        let lit = |e: u32, x: u32| mem.lit(e, x);
        if let Some((e, adr)) = at.choisi {
            at.noeuds.push(arbre::noeud_mot(&lit, e, adr));
        }
        at.noeuds.extend(arbre::arbre(&lit));
        for i in 0..at.noeuds.len() {
            at.ouverts.insert(vec![i]);
        }
    }
    unsafe {
        InvalidateRect(at.arbre, std::ptr::null(), 0);
    }
}

/// Les lignes visibles : (profondeur, chemin, noeud).
fn lignes_arbre() -> Vec<(usize, Vec<usize>, &'static Noeud)> {
    fn rec(n: &'static Noeud, chemin: Vec<usize>, prof: usize, ouverts: &HashSet<Vec<usize>>, r: &mut Vec<(usize, Vec<usize>, &'static Noeud)>) {
        let ouvert = ouverts.contains(&chemin);
        r.push((prof, chemin.clone(), n));
        if ouvert {
            for (i, e) in n.enfants.iter().enumerate() {
                let mut c = chemin.clone();
                c.push(i);
                rec(e, c, prof + 1, ouverts, r);
            }
        }
    }
    let at = a();
    let mut r = Vec::new();
    for (i, n) in at.noeuds.iter().enumerate() {
        rec(n, vec![i], 0, &at.ouverts, &mut r);
    }
    r
}

fn couleur_logique(q: u8) -> u32 {
    // COLORREF 0x00BBGGRR : inconnu gris, faux rouge, vrai vert, variable orange
    [0x0090_9090, 0x0060_60E0, 0x0070_C870, 0x0040_A8E8][q as usize & 3]
}

unsafe extern "system" fn proc_arbre(h: H, m: u32, wp: usize, lp: isize) -> isize {
    let at = a();
    let hl = (18.0 * at.echelle) as i32;
    let ind = (16.0 * at.echelle) as i32;
    match m {
        WM_ERASEBKGND => 1,
        WM_PAINT => {
            let mut ps: PaintStruct = std::mem::zeroed();
            let dc = BeginPaint(h, &mut ps);
            let mut r = Rect::default();
            GetClientRect(h, &mut r);
            // dessin hors écran puis copie : pas de scintillement
            let mdc = CreateCompatibleDC(dc);
            let bmp = CreateCompatibleBitmap(dc, r.right.max(1), r.bottom.max(1));
            let ancien_bmp = SelectObject(mdc, bmp);
            let fond = CreateSolidBrush(FOND);
            FillRect(mdc, &r, fond);
            DeleteObject(fond);
            let ancienne_police = SelectObject(mdc, at.police);
            SetBkMode(mdc, 1);
            let lignes = lignes_arbre();
            if lignes.is_empty() {
                SetTextColor(mdc, 0x0080_8080);
                let t = w("l'arbre des liaisons apparaît après l'exécution (F5)");
                TextOutW(mdc, ind / 2, hl / 4, t.as_ptr(), t.len() as i32 - 1);
            }
            let guide = CreateSolidBrush(0x0040_4040);
            for (k, (prof, chemin, n)) in lignes.iter().enumerate().skip(at.defile.max(0) as usize) {
                let y = (k as i32 - at.defile) * hl + hl / 6;
                if y > r.bottom {
                    break;
                }
                let x0 = ind / 2 + *prof as i32 * ind;
                for d in 0..*prof {
                    let gx = ind / 2 + d as i32 * ind + ind / 3;
                    FillRect(mdc, &Rect { left: gx, top: y, right: gx + 1, bottom: y + hl }, guide);
                }
                // ouvrir / fermer
                if !n.enfants.is_empty() {
                    SetTextColor(mdc, 0x00B0_B0B0);
                    let s = w(if at.ouverts.contains(chemin) { "▾" } else { "▸" });
                    TextOutW(mdc, x0, y, s.as_ptr(), 1);
                }
                let mut x = x0 + ind;
                // la couleur du mot dans le cube
                if let Some(v) = n.mot {
                    let c = super::cube::couleur(v, 1000);
                    let pinceau = CreateSolidBrush(((c & 0xFF) << 16) | (c & 0xFF00) | ((c >> 16) & 0xFF));
                    let cote = hl * 2 / 3;
                    let carre = Rect { left: x, top: y + (hl - cote) / 2, right: x + cote, bottom: y + (hl + cote) / 2 };
                    FillRect(mdc, &carre, guide);
                    let interieur = Rect { left: carre.left + 1, top: carre.top + 1, right: carre.right - 1, bottom: carre.bottom - 1 };
                    FillRect(mdc, &interieur, pinceau);
                    DeleteObject(pinceau);
                    x += cote + ind / 3;
                }
                SetTextColor(mdc, n.logique.map(couleur_logique).unwrap_or(TEXTE));
                let t = w(&n.texte);
                TextOutW(mdc, x, y, t.as_ptr(), t.len() as i32 - 1);
            }
            DeleteObject(guide);
            BitBlt(dc, 0, 0, r.right, r.bottom, mdc, 0, 0, SRCCOPY);
            SelectObject(mdc, ancienne_police);
            SelectObject(mdc, ancien_bmp);
            DeleteObject(bmp);
            DeleteDC(mdc);
            EndPaint(h, &ps);
            0
        }
        WM_LBUTTONDOWN => {
            let y = ((lp >> 16) & 0xFFFF) as i16 as i32;
            let k = (y - hl / 6).max(0) / hl + at.defile;
            let lignes = lignes_arbre();
            if let Some((_, chemin, n)) = lignes.get(k as usize) {
                if !n.enfants.is_empty() {
                    if !at.ouverts.remove(chemin) {
                        at.ouverts.insert(chemin.clone());
                    }
                }
                if let Some(v) = n.mot {
                    etat(&format!("{}  ·  {}", n.texte, arbre::decoder(v)[0]));
                }
                InvalidateRect(h, std::ptr::null(), 0);
            }
            SetFocus(h);
            0
        }
        WM_MOUSEWHEEL => {
            let cran = ((wp >> 16) & 0xFFFF) as i16 as i32 / 120;
            let n = lignes_arbre().len() as i32;
            at.defile = (at.defile - 3 * cran).clamp(0, (n - 1).max(0));
            InvalidateRect(h, std::ptr::null(), 0);
            0
        }
        _ => DefWindowProcW(h, m, wp, lp),
    }
}

// ------------------------------------------------------------------------------------------------ le pas à pas
// Dans la fenêtre même : F7 avance d'une ligne (en entrant dans les fonctions), F8 d'une ligne sans y entrer, F5
// continue jusqu'au prochain point d'arrêt (F9 en pose un sur la ligne du curseur), Échap ou Maj+F5 arrête. La ligne
// où la machine s'est arrêtée est choisie dans le texte et marquée ▶ ; l'onglet « Pas à pas » montre les registres et
// le cadre de la fonction, en décimal, en quaternaire (les 16 quits du mot) et en logique de Belnap.

/// Les 16 quits d'un mot, du quit 15 au quit 0 (le mot lu en base 4), par groupes de 4.
fn quits(v: u32) -> String {
    let q: Vec<char> = (0..16).rev().map(|k| char::from(b'0' + ((v >> (2 * k)) & 3) as u8)).collect();
    q.chunks(4).map(|c| c.iter().collect::<String>()).collect::<Vec<_>>().join(" ")
}

/// Le mot en logique de Belnap : un seul logique (0 à 3) par son nom ; sinon les 16 quits, · inconnu, f faux, v vrai,
/// ± variable (preuve du vrai et du faux à la fois).
fn belnap(v: u32) -> String {
    if v <= 3 {
        return ["inconnu", "faux", "vrai", "variable"][v as usize].to_string();
    }
    let q: Vec<char> = (0..16).rev().map(|k| ['·', 'f', 'v', '±'][((v >> (2 * k)) & 3) as usize]).collect();
    q.chunks(4).map(|c| c.iter().collect::<String>()).collect::<Vec<_>>().join(" ")
}

fn ligne_quaternaire(nom: &str, v: u32) -> String {
    format!("{:<5}{:>12}  {}  {}\n", nom, v as i32, quits(v), belnap(v))
}

/// Le panneau du pas à pas : registres, cadre de la fonction, sorties et console.
fn panneau_pas() -> String {
    let at = a();
    let d = match &at.pas {
        Some(d) => d,
        None => return String::new(),
    };
    let mut t = String::new();
    let ou = match d.ligne {
        Some(x) => format!("ligne {}", x + 1),
        None => if d.fini { "fini".into() } else { "début".into() },
    };
    t.push_str(&format!("pas à pas · {} · {} instructions · {}\n", ou, d.compte(),
                        match d.moteur { Moteur::M128(_) => "Lugus", Moteur::M64(_) => "SPU-64", _ => "SPU-32" }));
    t.push_str("F7 ligne suivante · F8 sans entrer dans les fonctions · F5 continuer · F9 point d'arrêt · Échap arrêter\n\n");
    let (mem, et) = match &d.moteur {
        Moteur::M32 { mem, et, .. } => (mem, et),
        Moteur::M64(s) => {
            panneau64(s, &mut t);
            return t;
        }
        Moteur::M128(s) => {
            panneau128(s, &mut t);
            return t;
        }
    };
    let r = &et.r;
    t.push_str(&format!("{:<5}{:>12}  {:<19}  {}\n", "", "décimal", "quaternaire (15→0)", "Belnap (· f v ±)"));
    for k in 1..13 {
        t.push_str(&ligne_quaternaire(&format!("R{}", k), r[k]));
    }
    t.push_str(&format!("R13 cadre {} · R14 pile {} · Z {} · C {} · pc {}\n", r[13], r[14], et.z as u8, et.c as u8, et.pc));
    if r[13] != 0 && r[13] < PILE_HAUT {
        t.push_str("\ncadre de la fonction : variables locales (-1, -2…), paramètres (+2, +3…)\n");
        let lit = |k: i64| mem.lit(0, (r[13] as i64 + k) as u32);
        for k in 1..9i64 {
            t.push_str(&ligne_quaternaire(&format!("{}", -k), lit(-k)));
        }
        for k in 2..6i64 {
            t.push_str(&ligne_quaternaire(&format!("+{}", k), lit(k)));
        }
    }
    if !et.sorties.is_empty() {
        let v: Vec<String> = et.sorties.iter().map(|v| v.to_string()).collect();
        t.push_str(&format!("\nsorties : {}\n", v.join(",")));
    }
    let c: String = et.texte.iter().filter_map(|&v| char::from_u32(v & 0x1F_FFFF)).collect();
    if !c.is_empty() {
        t.push_str("\nce que le programme a écrit :\n");
        for x in c.lines() {
            t.push_str(&format!("» {}\n", x));
        }
    }
    t
}

/// Compile pour le pas à pas (avec la table des lignes) et prépare la machine au début du programme.
fn debuter_pas() -> bool {
    let at = a();
    if at.en_cours {
        etat("un programme tourne déjà");
        return false;
    }
    let fichier = if at.fichier.is_none() {
        let f = std::env::temp_dir().join("sans titre.vtx");
        if std::fs::write(&f, lire_texte(at.source).replace("\r\n", "\n")).is_err() {
            message("Impossible d'écrire le fichier temporaire.");
            return false;
        }
        f
    } else {
        if !enregistrer(false) {
            return false;
        }
        at.fichier.clone().unwrap()
    };
    let source = lire_texte(at.source).replace("\r\n", "\n");
    let base = dossier_de(&fichier.to_string_lossy());
    let entrees: Vec<u64> = lire_texte(at.entrees).split_whitespace().filter_map(|x| x.parse::<u64>().ok()).collect();
    if at.machine == 128 {
        return debuter_pas128(&fichier, &source, &base, entrees);
    }
    if at.machine == 64 {
        return debuter_pas64(&fichier, &source, &base, entrees);
    }
    let (mots, _, dbg) = match compiler_lignes(&nombres(VTXC), &source, &base, PAS_A_PAS, true) {
        Ok(r) => r,
        Err(e) => {
            let nom = fichier.file_name().map(|n| n.to_string_lossy().into_owned()).unwrap_or_default();
            ecrire_texte(at.journal, &e.replace("erreur ligne ", &format!("erreur {}, ligne ", nom)));
            montrer_onglet(0);
            at.ligne_erreur = e.find("erreur ligne ").and_then(|p| e[p + 13..].chars().take_while(|c| c.is_ascii_digit()).collect::<String>().parse().ok());
            at.vue_lignes = (-1, -1);
            etat("erreur de compilation : le pas à pas ne peut pas commencer");
            return false;
        }
    };
    let mut mem = Memoire::new(false);
    super::charger(&mut mem, &mots);
    let debuts = table_des_lignes(dbg.iter().map(|&x| x as u64));
    let mut et = Etat { r: [0u32; 16], pc: 0, z: false, c: false, pas: 0, ie: 0, sorties: Vec::new(), texte: Vec::new() };
    et.r[14] = PILE_HAUT;
    let entrees = entrees.iter().map(|&x| x as u32).collect();
    at.ligne_erreur = None;
    at.pas = Some(Pas { moteur: Moteur::M32 { mem, et, fichiers: std::sync::Mutex::new(HashMap::new()), entrees, dossier: PathBuf::from(&base) },
                        debuts, ligne: None, fini: false });
    DIRECT.store(false, Ordering::Relaxed);
    CLAVIER.store(0, Ordering::Relaxed);
    true
}

/// Le pas à pas sur la machine 64 bits : vtxc64 compile avec la table des lignes, la SPU-64 attend au début.
fn debuter_pas64(fichier: &Path, source: &str, base: &str, entrees: Vec<u64>) -> bool {
    let at = a();
    let (mots, _, dbg) = match compiler64(&nombres64(VTXC64), source, base, PAS_A_PAS64, true) {
        Ok(r) => r,
        Err(e) => {
            let (t, ligne) = situer_erreur(&e, &fichier.to_string_lossy());
            ecrire_texte(at.journal, &t);
            montrer_onglet(0);
            at.ligne_erreur = ligne;
            at.vue_lignes = (-1, -1);
            etat("erreur de compilation : le pas à pas ne peut pas commencer");
            return false;
        }
    };
    let mut s = Box::new(Spu64::nouveau());
    s.dossier = Some(PathBuf::from(base));
    s.charger(&mots);
    s.entree.extend(entrees);
    s.parler = Some(super::parler_hote);
    at.ligne_erreur = None;
    at.pas = Some(Pas { moteur: Moteur::M64(s), debuts: table_des_lignes(dbg.into_iter()), ligne: None, fini: false });
    true
}

/// Le pas à pas sur Lugus : vtxc128 compile avec la table des lignes (en demi-mots : le pc de Lugus), Lugus attend au
/// début.
fn debuter_pas128(fichier: &Path, source: &str, base: &str, entrees: Vec<u64>) -> bool {
    let at = a();
    let (mots, _, dbg) = match compiler128(&nombres128(VTXC128), source, base, PAS_A_PAS128, true) {
        Ok(r) => r,
        Err(e) => {
            let (t, ligne) = situer_erreur(&e, &fichier.to_string_lossy());
            ecrire_texte(at.journal, &t);
            montrer_onglet(0);
            at.ligne_erreur = ligne;
            at.vue_lignes = (-1, -1);
            etat("erreur de compilation : le pas à pas ne peut pas commencer");
            return false;
        }
    };
    let mut s = Box::new(Spu128::nouveau());
    s.dossier = Some(PathBuf::from(base));
    s.charger(&mots);
    s.entree.extend(entrees.into_iter().map(|x| x as u128));
    s.parler = Some(super::parler_hote);
    at.ligne_erreur = None;
    at.pas = Some(Pas { moteur: Moteur::M128(s), debuts: table_des_lignes(dbg.into_iter().map(|x| x as u64)), ligne: None, fini: false });
    true
}

/// La ligne l amenée à l'écran, le curseur à son début (sans rien choisir : une touche ne l'effacerait pas) ; la
/// gouttière la marque ▶.
fn montrer_ligne(l: usize) {
    let at = a();
    unsafe {
        let debut = SendMessageW(at.source, EM_LINEINDEX, l, 0);
        if debut < 0 {
            return;
        }
        SendMessageW(at.source, EM_SETSEL, debut as usize, debut);
        SendMessageW(at.source, EM_SCROLLCARET, 0, 0);
    }
}

fn avancer(mode: Avance) {
    let at = a();
    if at.pas.is_none() && !debuter_pas() {
        return;
    }
    let points = at.points.clone();
    let d = at.pas.as_mut().unwrap();
    if d.fini {
        return;
    }
    let cadre = d.cadre();
    let depart = d.compte();
    let mut erreur = None;
    if mode == Avance::Continuer && points.is_empty() {
        // rien pour l'arrêter : on va jusqu'au bout d'un coup
        match d.jusqu_au_bout() {
            Ok(()) => d.fini = true,
            Err(e) => erreur = Some(e),
        }
    } else {
        loop {
            match d.une_instruction() {
                Ok(true) => {
                    d.fini = true;
                    break;
                }
                Ok(false) => {}
                Err(e) => {
                    erreur = Some(e);
                    break;
                }
            }
            if let Some(&l) = d.debuts.get(&d.pc()) {
                d.ligne = Some(l);
                let arreter = match mode {
                    Avance::Pas => true,
                    Avance::Dessus => d.cadre() >= cadre,
                    Avance::Continuer => points.contains(&l),
                };
                if arreter {
                    break;
                }
            }
            if d.compte() - depart >= LIMITE_PAS {
                erreur = Some(format!("{} instructions sans atteindre une ligne : arrêt (boucle sans fin ?)", LIMITE_PAS));
                break;
            }
        }
    }
    if let Some(e) = erreur {
        d.fini = true;
        d.ligne = None;
        etat(&format!("erreur à l'exécution : {}", e));
    } else if d.fini {
        d.ligne = None;
        etat(&format!("programme fini en {} instructions · le cube et l'arbre montrent sa mémoire · F7 recommence", d.compte()));
    } else {
        etat(&format!("pas à pas · ligne {} · F7 ligne · F8 par-dessus · F5 continuer · F9 point d'arrêt · Échap arrêter",
                      d.ligne.map(|l| l + 1).unwrap_or(0)));
    }
    let (ligne, fini) = (d.ligne, d.fini);
    ecrire_texte(at.pas_texte, &panneau_pas());
    if fini {
        // le programme est fini : sa mémoire passe au cube et à l'arbre, et l'on revient à l'édition
        if let Some(p) = at.pas.take() {
            match p.moteur {
                Moteur::M32 { mem, .. } => {
                    *IMAGE.lock().unwrap() = image32(&mem);
                    at.dessin = IMAGE.lock().unwrap().is_some();
                    at.mem = Some(mem);
                    at.vue64 = None;
                }
                Moteur::M64(s) => {
                    *IMAGE.lock().unwrap() = super::gobatix::image64(&s);
                    at.dessin = IMAGE.lock().unwrap().is_some();
                    let mut vue = Vue64::depuis(&s);
                    at.mem = Some(vue.memoire());
                    at.vue64 = Some(vue);
                }
                Moteur::M128(s) => {
                    *IMAGE.lock().unwrap() = image128(&s);
                    at.dessin = IMAGE.lock().unwrap().is_some();
                    let mut vue = Vue64::depuis128(&s);
                    at.mem = Some(vue.memoire());
                    at.vue64 = Some(vue);
                }
            }
            at.choisi = None;
            rafraichir_arbre();
            unsafe {
                InvalidateRect(at.cube, std::ptr::null(), 0);
            }
        }
    }
    if let Some(l) = ligne {
        montrer_ligne(l);
    }
    montrer_onglet(2);
    unsafe {
        SetFocus(at.source);
    }
    at.vue_lignes = (-1, -1);
    suivre_lignes();
}

/// Fin du pas à pas : retour à l'édition.
fn arreter_pas(raison: &str) {
    let at = a();
    if at.pas.take().is_some() {
        at.vue_lignes = (-1, -1);
        suivre_lignes();
        etat(raison);
    }
}

/// Un point d'arrêt sur la ligne du curseur (ou retiré s'il y en avait un).
fn basculer_point() {
    let at = a();
    let l = unsafe { SendMessageW(at.source, EM_LINEFROMCHAR, usize::MAX, 0) }.max(0) as usize;
    if !at.points.remove(&l) {
        at.points.insert(l);
        etat(&format!("point d'arrêt posé ligne {} · F5 pendant le pas à pas continue jusqu'à lui", l + 1));
    } else {
        etat(&format!("point d'arrêt retiré ligne {}", l + 1));
    }
    at.vue_lignes = (-1, -1);
    suivre_lignes();
}

// ------------------------------------------------------------------------------------------------ l'image du programme
/// L'image du programme : la dernière que presenter() a montrée pendant l'exécution, ou celle qu'il laisse en finissant
/// (0x00RRGGBB). C'est l'image finie ; le programme dessine déjà la suivante dans l'étage 1 sans qu'on la voie.
static IMAGE: Mutex<Option<(usize, usize, Vec<u32>)>> = Mutex::new(None);
/// Où l'image est peinte dans la vue du cube (x0, y0, largeur, hauteur), pour situer la souris dans l'image.
static PLACE: Mutex<(i32, i32, i32, i32)> = Mutex::new((0, 0, 0, 0));
static ANNONCEE: std::sync::atomic::AtomicBool = std::sync::atomic::AtomicBool::new(false);
static PEINTURE: std::sync::atomic::AtomicBool = std::sync::atomic::AtomicBool::new(false);

/// La sortie de Gobatix dans l'atelier : chaque image présentée remplace la précédente dans la vue du cube.
struct VueAtelier {
    cube: usize,
}
impl super::gobatix::Sortie for VueAtelier {
    fn montrer(&mut self, l: usize, h: usize, px: &[u32]) -> bool {
        {
            let mut im = IMAGE.lock().unwrap();
            match im.as_mut() {
                Some((il, ih, v)) if *il == l && *ih == h => v.copy_from_slice(px),
                _ => *im = Some((l, h, px.to_vec())),
            }
        }
        // une seule peinture demandée à la fois : si la précédente n'est pas faite, l'image est seulement remplacée
        if !PEINTURE.swap(true, Ordering::Relaxed) {
            unsafe {
                InvalidateRect(self.cube as H, std::ptr::null(), 0);
            }
        }
        !ARRET.load(Ordering::Relaxed)
    }
}

/// L'image d'un programme du SPU-32 (ecran(l, h) : @3[14680058], @3[14680059], points #RRGGBBAA dans l'étage 1).
fn image32(mem: &Memoire) -> Option<(usize, usize, Vec<u32>)> {
    let (l, h) = taille_dessin(mem)?;
    let px = (0..l * h).map(|i| mem.lit(1, i) >> 8).collect();
    Some((l as usize, h as usize, px))
}

/// Peint l'image (il × ih) dans la vue (l × h) : agrandie d'un nombre entier de fois quand elle tient (des pixels nets),
/// sinon réduite ; centrée. Rend sa place.
fn peindre_image(il: usize, ih: usize, ipx: &[u32], l: usize, h: usize, px: &mut [u32]) -> (i32, i32, i32, i32) {
    if il == 0 || ih == 0 || ipx.len() < il * ih {
        return (0, 0, 0, 0);
    }
    let e = (l as f32 / il as f32).min(h as f32 / ih as f32);
    let e = if e >= 1.0 { e.floor() } else { e.max(0.01) };
    let (dl, dh) = (((il as f32 * e) as usize).clamp(1, l), ((ih as f32 * e) as usize).clamp(1, h));
    let (x0, y0) = ((l - dl) / 2, (h - dh) / 2);
    for y in 0..dh {
        let sy = (y * ih / dh).min(ih - 1);
        let ligne = &ipx[sy * il..sy * il + il];
        let dest = &mut px[(y0 + y) * l + x0..(y0 + y) * l + x0 + dl];
        for (x, d) in dest.iter_mut().enumerate() {
            *d = ligne[(x * il / dl).min(il - 1)];
        }
    }
    (x0 as i32, y0 as i32, dl as i32, dh as i32)
}

/// La souris dans la vue du cube. Pendant l'exécution, sur l'image : elle va au programme (souris()). Le programme
/// fini, en perspective : glisser à gauche tourne le cube d'un quart de tour, glisser à droite le déplace, un double
/// clic le remet. Rend vrai si le message est traité.
unsafe fn souris_vue(h: H, m: u32, wp: usize, lp: isize) -> bool {
    let at = a();
    let (mx, my) = ((lp & 0xFFFF) as i16 as i32, ((lp >> 16) & 0xFFFF) as i16 as i32);
    let b = (wp as u32 & 1) | (wp as u32 & 2) | if wp & 16 != 0 { 4 } else { 0 };
    let presse = matches!(m, WM_LBUTTONDOWN | WM_RBUTTONDOWN | WM_MBUTTONDOWN | WM_LBUTTONDBLCLK);
    let lache = matches!(m, WM_LBUTTONUP | WM_RBUTTONUP | WM_MBUTTONUP);
    // la souris est rendue au reste de l'atelier dès que plus aucun bouton n'est enfoncé, quel que soit l'état (sinon,
    // un bouton relâché après la fin du programme laissait la vue du cube garder la souris : l'éditeur ne pouvait plus
    // arrêter de sélectionner)
    if lache && b == 0 {
        ReleaseCapture();
        at.glisse = None;
    }
    if at.en_cours {
        let taille = IMAGE.lock().unwrap().as_ref().map(|(l, h, _)| (*l, *h));
        let (il, ih) = match taille {
            Some(t) => t,
            None => return false,
        };
        if presse {
            SetFocus(h);
            SetCapture(h);
        }
        let (x0, y0, dl, dh) = *PLACE.lock().unwrap();
        super::hote::souris_dans_vue(mx, my, x0, y0, dl, dh, il, ih, b);
        return true;
    }
    if !at.iso || at.dessin || at.mem.is_none() {
        return false;
    }
    match m {
        WM_LBUTTONDBLCLK => {
            at.quart = 0;
            at.decal = (0, 0);
            at.zoom = 1.0;
            at.glisse = None;
            InvalidateRect(h, std::ptr::null(), 0);
        }
        WM_LBUTTONDOWN | WM_RBUTTONDOWN => {
            at.glisse = Some((mx, my));
            SetCapture(h);
        }
        WM_LBUTTONUP | WM_RBUTTONUP => {}
        WM_MOUSEMOVE => {
            if let Some((x, y)) = at.glisse {
                let seuil = (60.0 * at.echelle) as i32;
                if b & 1 != 0 && (mx - x).abs() >= seuil {
                    at.quart = (at.quart + if mx > x { 1 } else { 3 }) % 4;
                    at.glisse = Some((mx, my));
                    InvalidateRect(h, std::ptr::null(), 0);
                } else if b & 2 != 0 {
                    at.decal = (at.decal.0 + mx - x, at.decal.1 + my - y);
                    at.glisse = Some((mx, my));
                    InvalidateRect(h, std::ptr::null(), 0);
                }
            }
        }
        _ => return false,
    }
    true
}

/// Un nom libre à côté du programme : « programme-1.gif », « programme-2.gif »…
fn chemin_libre(ext: &str) -> PathBuf {
    let at = a();
    let (dossier, nom) = match &at.fichier {
        Some(f) => (f.parent().map(|p| p.to_path_buf()).unwrap_or_default(),
                    f.file_stem().map(|n| n.to_string_lossy().into_owned()).unwrap_or_else(|| "image".into())),
        None => (std::env::temp_dir(), "sans titre".to_string()),
    };
    let mut k = 1;
    loop {
        let p = dossier.join(format!("{}-{}.{}", nom, k, ext));
        if !p.exists() {
            return p;
        }
        k += 1;
    }
}

/// Ctrl+G : commencer l'enregistrement de l'animation (chaque image que présente le programme), ou le finir et
/// écrire le GIF à côté du programme.
fn basculer_enregistrement() {
    let at = a();
    let marche = !super::gobatix::ENREGISTRER.load(Ordering::Relaxed);
    if marche {
        *super::gobatix::ENREGISTREMENT.lock().unwrap() = None;
        super::gobatix::ENREGISTRER.store(true, Ordering::Relaxed);
        etat("enregistrement : chaque image que montre presenter() s'ajoute à l'animation · F5 pour lancer · Ctrl+G pour finir");
    } else {
        super::gobatix::ENREGISTRER.store(false, Ordering::Relaxed);
        let g = super::gobatix::ENREGISTREMENT.lock().unwrap().take();
        match g {
            None => etat("aucune image enregistrée : le programme doit dessiner (ecran) et appeler presenter()"),
            Some(g) => {
                let n = g.images;
                let o = g.finir();
                let p = chemin_libre("gif");
                match std::fs::write(&p, &o) {
                    Ok(()) => {
                        let t = format!("animation écrite : {} ({} images, {} Ko)", p.display(), n, (o.len() + 1023) / 1024);
                        ajouter_texte(at.journal, &format!("{}\n", t));
                        etat(&t);
                    }
                    Err(e) => message(&format!("Impossible d'écrire {} : {}", p.display(), e)),
                }
            }
        }
    }
    if let Some(b) = at.boutons.iter().find(|b| b.1 == C_GIF) {
        ecrire_texte(b.0, if marche { "■  Finir l'enregistrement" } else { "●  Enregistrer (GIF)" });
    }
}

/// L'image du programme en PNG, à côté du programme.
fn image_png() {
    let img = IMAGE.lock().unwrap().clone();
    match img {
        None => etat("pas d'image : le programme doit dessiner (ecran(l, h), pixel, trait…)"),
        Some((l, h, px)) => {
            let png = super::cube::png_de(&px.iter().map(|&v| v | 0xFF00_0000).collect::<Vec<u32>>(), l, h);
            let p = chemin_libre("png");
            match std::fs::write(&p, png) {
                Ok(()) => etat(&format!("image écrite : {}", p.display())),
                Err(e) => message(&format!("Impossible d'écrire {} : {}", p.display(), e)),
            }
        }
    }
}

// ------------------------------------------------------------------------------------------------ le cube
use super::cube::{rendre_iso, rendre_plan, rendre_quits, taille_dessin};

unsafe extern "system" fn proc_cube(h: H, m: u32, wp: usize, lp: isize) -> isize {
    match m {
        WM_ERASEBKGND => 1,
        WM_PAINT => {
            let mut ps: PaintStruct = std::mem::zeroed();
            let dc = BeginPaint(h, &mut ps);
            let mut r = Rect::default();
            GetClientRect(h, &mut r);
            let (l, ht) = ((r.right - r.left).max(1) as usize, (r.bottom - r.top).max(1) as usize);
            let mut px = vec![0x0010_1418u32; l * ht];
            let at = a();
            PEINTURE.store(false, Ordering::Relaxed);
            let image = if at.en_cours || at.dessin { IMAGE.lock().unwrap().clone() } else { None };
            if let Some((il, ih, ipx)) = &image {
                *PLACE.lock().unwrap() = peindre_image(*il, *ih, ipx, l, ht, &mut px);
                if !at.en_cours {
                    etat(&format!("image du programme : {} × {} points · F6 : image, cube en perspective, à plat, quits · Cube › Image en PNG",
                                  il, ih));
                } else if !ANNONCEE.swap(true, Ordering::Relaxed) {
                    // la première image : le clavier va au programme sans qu'il faille cliquer
                    PostMessageW(at.fen, WM_APP_CLAVIER, 0, 0);
                    etat(&format!("image du programme : {} × {} · la souris et le clavier vont au programme (un clic dans le texte \
                                   le reprend) · Ctrl+G : enregistrer en GIF · Maj+F5 : arrêter", il, ih));
                }
            } else if let Some(mem) = &at.mem {
                if at.iso {
                    let n = rendre_iso(mem, at.etage, at.zoom, at.quart, at.decal, l, ht, &mut px);
                    etat(&format!("cube en perspective · étage {} · {} mots non nuls · molette : zoom · glisser : tourner (gauche), \
                                   déplacer (droit) · double clic : revenir", at.etage, n));
                } else if at.vue_quits {
                    rendre_quits(mem, at.etage, at.largeur, at.base, l, ht, &mut px);
                } else {
                    rendre_plan(mem, at.etage, at.largeur, at.base, l, ht, &mut px);
                }
            }
            let info = BitmapInfo {
                bmiHeader: BitmapInfoHeader { biSize: std::mem::size_of::<BitmapInfoHeader>() as u32, biWidth: l as i32,
                    biHeight: -(ht as i32), biPlanes: 1, biBitCount: 32, biCompression: 0, biSizeImage: 0,
                    biXPelsPerMeter: 0, biYPelsPerMeter: 0, biClrUsed: 0, biClrImportant: 0 },
                bmiColors: [0],
            };
            StretchDIBits(dc, 0, 0, l as i32, ht as i32, 0, 0, l as i32, ht as i32, px.as_ptr() as *const c_void, &info, 0, SRCCOPY);
            EndPaint(h, &ps);
            0
        }
        WM_MOUSEMOVE | WM_LBUTTONDOWN | WM_LBUTTONUP | WM_RBUTTONDOWN | WM_RBUTTONUP | WM_MBUTTONDOWN | WM_MBUTTONUP
        | WM_LBUTTONDBLCLK if souris_vue(h, m, wp, lp) => 0,
        WM_KEYDOWN | WM_KEYUP | WM_CHAR | WM_SYSKEYDOWN | WM_SYSKEYUP if a().en_cours => {
            // le programme qui tourne reçoit le clavier (touche(), appuyee())
            super::hote::clavier_windows(m, wp);
            if m == WM_SYSKEYDOWN || m == WM_SYSKEYUP { DefWindowProcW(h, m, wp, lp) } else { 0 }
        }
        WM_KILLFOCUS => {
            super::hote::tout_relacher();
            0
        }
        // la souris reprise par Windows (Alt+Tab, une autre fenêtre) : plus de glissement en cours
        0x0215 => {
            a().glisse = None;
            0
        }
        WM_LBUTTONDOWN => {
            let at = a();
            let mut choix = None;
            if let (Some(mem), false, false) = (&at.mem, at.iso, at.dessin) {
                let (x, y) = ((lp & 0xFFFF) as i16 as i32, ((lp >> 16) & 0xFFFF) as i16 as i32);
                let mut r = Rect::default();
                GetClientRect(h, &mut r);
                let l = (r.right - r.left).max(1) as u32;
                let cote = (l / at.largeur).max(1);
                let pas = ((at.largeur + l - 1) / l).max(1);
                let adr = at.base + (y.max(0) as u32 / cote) * pas * at.largeur + (x.max(0) as u32 / cote) * pas;
                if adr <= 0xFF_FFFF && (x.max(0) as u32 / cote) * pas < at.largeur {
                    let v = mem.lit(at.etage, adr);
                    etat(&format!("@{}[{}] = #{:08X} = {} (signé {}) · quits {} · {}", at.etage, adr, v, v, v as i32, quits(v), belnap(v)));
                    choix = Some((at.etage, adr));
                }
            }
            if let Some((e, adr)) = choix {
                choisir_mot(e, adr);
            }
            0
        }
        WM_MOUSEWHEEL => {
            let at = a();
            let cran = ((wp >> 16) & 0xFFFF) as i16 as i32 / 120;
            if at.en_cours && IMAGE.lock().unwrap().is_some() {
                super::hote::ajouter_molette(cran);
                return 0;
            }
            if at.iso {
                at.zoom = (at.zoom * if cran > 0 { 1.25 } else { 0.8 }).clamp(0.2, 64.0);
            } else {
                let lignes = 16 * at.largeur;
                at.base = if cran > 0 { at.base.saturating_sub(lignes) } else { (at.base + lignes).min(0xFF_0000) };
                etat(&format!("à plat · étage {} · à partir de @{}[{}] · {} mots par ligne", at.etage, at.etage, at.base, at.largeur));
            }
            InvalidateRect(h, std::ptr::null(), 0);
            0
        }
        _ => DefWindowProcW(h, m, wp, lp),
    }
}

// ------------------------------------------------------------------------------------------------ l'éditeur
/// Le texte du programme : Entrée garde le retrait de la ligne (un niveau de plus après « { »), Tab met 4 espaces.
unsafe extern "system" fn proc_source(h: H, m: u32, wp: usize, lp: isize) -> isize {
    let ancien = a().ancien_proc_source;
    if m == WM_PASTE {
        // le presse-papiers peut venir d'ailleurs avec des fins de ligne « \n » seules : l'éditeur de Windows veut « \r\n »
        if let Some(t) = super::atelier::console::lire_presse() {
            let t = t.replace("\r\n", "\n").replace('\r', "\n").replace('\n', "\r\n").replace('\t', "    ");
            SendMessageW(h, EM_REPLACESEL, 1, w(&t).as_ptr() as isize);
            return 0;
        }
    }
    if m == WM_CHAR && wp == 9 {
        SendMessageW(h, EM_REPLACESEL, 1, w("    ").as_ptr() as isize);
        return 0;
    }
    if m == WM_CHAR && wp == 13 {
        let n = SendMessageW(h, EM_LINEFROMCHAR, usize::MAX, 0) as usize;
        let mut t = vec![0u16; 4096];
        t[0] = 4090;
        let k = SendMessageW(h, EM_GETLINE, n, t.as_mut_ptr() as isize) as usize;
        let ligne = String::from_utf16_lossy(&t[..k.min(4090)]);
        // seulement le texte avant le curseur compte pour « { »
        let mut debut = 0u32;
        SendMessageW(h, EM_GETSEL, &mut debut as *mut u32 as usize, 0);
        let col = (debut as isize - SendMessageW(h, EM_LINEINDEX, n, 0)).max(0) as usize;
        let avant: String = ligne.chars().take(col).collect();
        let mut retrait = ligne.chars().take_while(|c| *c == ' ').count().min(col);
        if avant.trim_end().ends_with('{') {
            retrait += 4;
        }
        let ins = format!("\r\n{}", " ".repeat(retrait));
        SendMessageW(h, EM_REPLACESEL, 1, w(&ins).as_ptr() as isize);
        return 0;
    }
    if m == WM_CHAR && wp == '}' as usize {
        // « } » sur une ligne vide : la fermante revient d'un niveau
        let n = SendMessageW(h, EM_LINEFROMCHAR, usize::MAX, 0) as usize;
        let mut t = vec![0u16; 4096];
        t[0] = 4090;
        let k = SendMessageW(h, EM_GETLINE, n, t.as_mut_ptr() as isize) as usize;
        let ligne = String::from_utf16_lossy(&t[..k.min(4090)]);
        let mut debut = 0u32;
        SendMessageW(h, EM_GETSEL, &mut debut as *mut u32 as usize, 0);
        let i = SendMessageW(h, EM_LINEINDEX, n, 0) as usize;
        if ligne.len() >= 4 && ligne.chars().all(|c| c == ' ') && debut as usize == i + ligne.chars().count() {
            SendMessageW(h, EM_SETSEL, debut as usize - 4, debut as isize);
            SendMessageW(h, EM_REPLACESEL, 1, w("}").as_ptr() as isize);
            return 0;
        }
    }
    CallWindowProcW(ancien, h, m, wp, lp)
}

// ------------------------------------------------------------------------------------------------ la fenêtre
fn creer_controles(fen: H) {
    let at = a();
    unsafe {
        let edit = w("EDIT");
        let bouton = w("BUTTON");
        let statique = w("STATIC");
        at.lignes = CreateWindowExW(0, w("VtxLignes").as_ptr(), w("").as_ptr(), WS_CHILD | WS_VISIBLE,
            0, 0, 10, 10, fen, 17 as H, at.inst, std::ptr::null_mut());
        at.source = CreateWindowExW(WS_EX_CLIENTEDGE, edit.as_ptr(), w("").as_ptr(),
            WS_CHILD | WS_VISIBLE | WS_VSCROLL | WS_HSCROLL | ES_MULTILINE | ES_AUTOVSCROLL | ES_AUTOHSCROLL | ES_NOHIDESEL | ES_WANTRETURN | WS_TABSTOP,
            0, 0, 10, 10, fen, 10 as H, at.inst, std::ptr::null_mut());
        at.sortie = CreateWindowExW(WS_EX_CLIENTEDGE, edit.as_ptr(), w("").as_ptr(),
            WS_CHILD | WS_VISIBLE | WS_VSCROLL | WS_HSCROLL | ES_MULTILINE | ES_AUTOVSCROLL | ES_AUTOHSCROLL | ES_READONLY,
            0, 0, 10, 10, fen, 11 as H, at.inst, std::ptr::null_mut());
        at.entrees = CreateWindowExW(WS_EX_CLIENTEDGE, edit.as_ptr(), w("").as_ptr(), WS_CHILD | WS_VISIBLE | ES_AUTOHSCROLL | WS_TABSTOP,
            0, 0, 10, 10, fen, 12 as H, at.inst, std::ptr::null_mut());
        at.journal = CreateWindowExW(WS_EX_CLIENTEDGE, edit.as_ptr(), w("").as_ptr(),
            WS_CHILD | WS_VSCROLL | WS_HSCROLL | ES_MULTILINE | ES_AUTOVSCROLL | ES_AUTOHSCROLL | ES_READONLY,
            0, 0, 10, 10, fen, 18 as H, at.inst, std::ptr::null_mut());
        at.pas_texte = CreateWindowExW(WS_EX_CLIENTEDGE, edit.as_ptr(), w("").as_ptr(),
            WS_CHILD | WS_VSCROLL | WS_HSCROLL | ES_MULTILINE | ES_AUTOVSCROLL | ES_AUTOHSCROLL | ES_READONLY,
            0, 0, 10, 10, fen, 19 as H, at.inst, std::ptr::null_mut());
        for (i, (t, c)) in [("Sortie", C_ONGLET_SORTIE), ("Terminal", C_ONGLET_TERMINAL), ("Pas à pas", C_ONGLET_PAS)].iter().enumerate() {
            at.onglets[i] = CreateWindowExW(0, bouton.as_ptr(), w(t).as_ptr(), WS_CHILD | WS_VISIBLE | WS_TABSTOP, 0, 0, 10, 10, fen,
                                            *c as usize as H, at.inst, std::ptr::null_mut());
        }
        at.term_entree = CreateWindowExW(WS_EX_CLIENTEDGE, edit.as_ptr(), w("").as_ptr(), WS_CHILD | WS_VISIBLE | ES_AUTOHSCROLL | WS_TABSTOP,
            0, 0, 10, 10, fen, 15 as H, at.inst, std::ptr::null_mut());
        at.arbre = CreateWindowExW(WS_EX_CLIENTEDGE, w("VtxArbre").as_ptr(), w("").as_ptr(), WS_CHILD | WS_VISIBLE,
            0, 0, 10, 10, fen, 16 as H, at.inst, std::ptr::null_mut());
        at.cube = CreateWindowExW(WS_EX_CLIENTEDGE, w("VtxCube").as_ptr(), w("").as_ptr(), WS_CHILD | WS_VISIBLE,
            0, 0, 10, 10, fen, 13 as H, at.inst, std::ptr::null_mut());
        at.etat = CreateWindowExW(0, statique.as_ptr(), w("").as_ptr(), WS_CHILD | WS_VISIBLE | SS_CENTERIMAGE,
            0, 0, 10, 10, fen, 14 as H, at.inst, std::ptr::null_mut());
        for (t, c) in [("Ouvrir", C_OUVRIR), ("Enregistrer", C_ENREGISTRER), ("▶  Lancer  (F5)", C_LANCER), ("Pas à pas  (F7)", C_PAS),
                       ("0", C_ETAGE), ("1", C_ETAGE + 1), ("2", C_ETAGE + 2), ("3", C_ETAGE + 3), ("Vue : perspective / à plat / quits  (F6)", C_VUE),
                       ("Largeur", C_LARGEUR), ("Machine : SPU-64", C_MACHINE64), ("●  Enregistrer (GIF)", C_GIF)] {
            let b = CreateWindowExW(0, bouton.as_ptr(), w(t).as_ptr(), WS_CHILD | WS_VISIBLE | WS_TABSTOP, 0, 0, 10, 10, fen,
                                    c as usize as H, at.inst, std::ptr::null_mut());
            at.boutons.push((b, c));
        }
        for t in ["Entrées :", "Étage :"] {
            let e = CreateWindowExW(0, statique.as_ptr(), w(t).as_ptr(), WS_CHILD | WS_VISIBLE | SS_CENTERIMAGE, 0, 0, 10, 10, fen,
                                    std::ptr::null_mut(), at.inst, std::ptr::null_mut());
            at.etiquettes.push(e);
        }
        // polices : à chasse fixe pour le code, celle de l'interface pour le reste
        let dc = GetDC(fen);
        at.echelle = GetDeviceCaps(dc, 90) as f32 / 96.0;
        ReleaseDC(fen, dc);
        let px = |p: f32| -(p * at.echelle) as i32;
        at.police = CreateFontW(px(15.0), 0, 0, 0, 400, 0, 0, 0, 1, 0, 0, 5, 0x31, w("Consolas").as_ptr());
        at.police_ui = CreateFontW(px(14.0), 0, 0, 0, 400, 0, 0, 0, 1, 0, 0, 5, 0, w("Segoe UI").as_ptr());
        for h in [at.source, at.sortie, at.entrees, at.term_entree, at.journal, at.pas_texte] {
            SendMessageW(h, WM_SETFONT, at.police as usize, 1);
        }
        ecrire_texte(at.pas_texte, "pas à pas : F7 avance d'une ligne (la machine s'arrête au début de chaque ligne du programme),
            F8 aussi mais sans entrer dans les fonctions, F5 continue jusqu'au prochain point d'arrêt (F9 en pose un
            sur la ligne du curseur), Échap arrête. Ici : les registres et le cadre de la fonction, en décimal,
            en quaternaire (les 16 quits du mot, du quit 15 au quit 0) et en logique de Belnap
            (· inconnu, f faux, v vrai, ± variable).
");
        for h in at.onglets {
            SendMessageW(h, WM_SETFONT, at.police_ui as usize, 1);
        }
        SendMessageW(at.journal, EM_SETLIMITTEXT, 64 << 20, 0);
        ecrire_texte(at.journal, "sortie : le compte rendu de chaque exécution (compilation, ce que le programme a écrit, bilan).\n");
        ecrire_texte(at.sortie, "terminal vtx : la sortie du programme s'écrit ici ; la ligne du dessous lui répond pendant l'exécution,\n\
            et prend des commandes le reste du temps (tapez aide).\n");
        for h in at.boutons.iter().map(|b| b.0).chain(at.etiquettes.iter().copied()).chain(std::iter::once(at.etat)) {
            SendMessageW(h, WM_SETFONT, at.police_ui as usize, 1);
        }
        SendMessageW(at.source, EM_SETLIMITTEXT, 64 << 20, 0);
        SendMessageW(at.sortie, EM_SETLIMITTEXT, 64 << 20, 0);
        let tab: i32 = 16;
        SendMessageW(at.source, EM_SETTABSTOPS, 1, &tab as *const i32 as isize);
        at.pinceau = CreateSolidBrush(FOND);
        at.ancien_proc_source = SetWindowLongPtrW(at.source, GWLP_WNDPROC, proc_source as *const () as usize as isize);
        at.ancien_proc_term = SetWindowLongPtrW(at.term_entree, GWLP_WNDPROC, proc_term as *const () as usize as isize);
    }
}

fn disposer(fen: H) {
    let at = a();
    let mut r = Rect::default();
    unsafe {
        GetClientRect(fen, &mut r);
    }
    let e = at.echelle;
    let px = |v: f32| (v * e) as i32;
    let (l, h) = (r.right, r.bottom);
    let barre = px(36.0);
    let bas = px(24.0);
    let marge = px(4.0);
    // la barre des boutons
    let mut x = marge;
    let largeurs = [70.0, 90.0, 120.0, 120.0];
    unsafe {
        for (i, lb) in largeurs.iter().enumerate() {
            MoveWindow(at.boutons[i].0, x, marge, px(*lb), barre - 2 * marge, 1);
            x += px(*lb) + marge;
        }
        x += marge * 2;
        MoveWindow(at.etiquettes[0], x, marge, px(62.0), barre - 2 * marge, 1);
        x += px(62.0);
        MoveWindow(at.entrees, x, marge + px(3.0), px(130.0), barre - 2 * marge - px(6.0), 1);
        x += px(130.0) + marge * 3;
        MoveWindow(at.etiquettes[1], x, marge, px(46.0), barre - 2 * marge, 1);
        x += px(46.0);
        for i in 4..8 {
            MoveWindow(at.boutons[i].0, x, marge, px(28.0), barre - 2 * marge, 1);
            x += px(28.0) + px(2.0);
        }
        x += marge * 2;
        MoveWindow(at.boutons[8].0, x, marge, px(270.0), barre - 2 * marge, 1);
        x += px(270.0) + marge;
        MoveWindow(at.boutons[9].0, x, marge, px(70.0), barre - 2 * marge, 1);
        x += px(70.0) + marge * 3;
        MoveWindow(at.boutons[10].0, x, marge, px(140.0), barre - 2 * marge, 1);
        x += px(140.0) + marge;
        MoveWindow(at.boutons[11].0, x, marge, px(200.0), barre - 2 * marge, 1);
        // l'éditeur à gauche, le cube et la sortie à droite
        let gauche = (l as f32 * 0.5) as i32;
        let haut_util = h - barre - bas;
        let gouttiere = px(44.0);
        MoveWindow(at.lignes, 0, barre, gouttiere, haut_util, 1);
        MoveWindow(at.source, gouttiere, barre, gauche - gouttiere, haut_util, 1);
        let hc = (haut_util as f32 * 0.6) as i32;
        MoveWindow(at.cube, gauche + marge, barre, l - gauche - marge, hc, 1);
        // sous le cube : le terminal (et sa ligne) à gauche, l'arbre des liaisons à droite
        let yb = barre + hc + marge;
        let hb = haut_util - hc - marge;
        let lt = (l - gauche - marge) * 5 / 11;
        let hligne = px(26.0);
        let honglet = px(26.0);
        MoveWindow(at.onglets[0], gauche + marge, yb, px(90.0), honglet, 1);
        MoveWindow(at.onglets[1], gauche + marge + px(92.0), yb, px(90.0), honglet, 1);
        MoveWindow(at.onglets[2], gauche + marge + px(184.0), yb, px(100.0), honglet, 1);
        let yt = yb + honglet + px(2.0);
        let ht = hb - honglet - px(2.0);
        MoveWindow(at.journal, gauche + marge, yt, lt, ht, 1);
        MoveWindow(at.pas_texte, gauche + marge, yt, lt, ht, 1);
        MoveWindow(at.sortie, gauche + marge, yt, lt, ht - hligne, 1);
        MoveWindow(at.term_entree, gauche + marge, yt + ht - hligne, lt, hligne, 1);
        MoveWindow(at.arbre, gauche + marge + lt + marge, yb, l - gauche - marge - lt - marge, hb, 1);
        MoveWindow(at.etat, 0, h - bas, l, bas, 1);
    }
}

fn menus(fen: H) {
    unsafe {
        let barre = CreateMenu();
        let ajouter = |m: H, t: &str, id: u16| {
            if t.is_empty() {
                AppendMenuW(m, MF_SEPARATOR, 0, std::ptr::null());
            } else {
                AppendMenuW(m, 0, id as usize, w(t).as_ptr());
            }
        };
        let fichier = CreatePopupMenu();
        ajouter(fichier, "&Nouveau\tCtrl+N", C_NOUVEAU);
        ajouter(fichier, "&Ouvrir…\tCtrl+O", C_OUVRIR);
        ajouter(fichier, "&Enregistrer\tCtrl+S", C_ENREGISTRER);
        ajouter(fichier, "Enregistrer &sous…", C_ENREGISTRER_SOUS);
        ajouter(fichier, "", 0);
        ajouter(fichier, "&Quitter", C_QUITTER);
        let edition = CreatePopupMenu();
        ajouter(edition, "&Annuler\tCtrl+Z", C_ANNULER);
        ajouter(edition, "", 0);
        ajouter(edition, "&Couper\tCtrl+X", C_COUPER);
        ajouter(edition, "C&opier\tCtrl+C", C_COPIER);
        ajouter(edition, "Co&ller\tCtrl+V", C_COLLER);
        ajouter(edition, "&Tout sélectionner\tCtrl+A", C_TOUT);
        let executer = CreatePopupMenu();
        ajouter(executer, "&Lancer\tF5", C_LANCER);
        ajouter(executer, "&Arrêter\tMaj+F5", C_ARRETER);
        ajouter(executer, "P&urger la mémoire du programme", C_PURGER);
        ajouter(executer, "", 0);
        ajouter(executer, "Machine &suivante (SPU-64 → Lugus → SPU-32)\tCtrl+M", C_MACHINE64);
        ajouter(executer, "Machine &64 bits (SPU-64, vtxc64)", C_M64);
        ajouter(executer, "Machine L&ugus (SPU-128, vtxc128)", C_LUGUS);
        ajouter(executer, "Machine 3&2 bits (SPU-32, vtxc)", C_M32);
        ajouter(executer, "", 0);
        ajouter(executer, "&Pas à pas : ligne suivante\tF7", C_PAS);
        ajouter(executer, "Pas à pas &sans entrer dans les fonctions\tF8", C_PAS_DESSUS);
        ajouter(executer, "Point d'arrêt sur la &ligne\tF9", C_POINT);
        ajouter(executer, "&Continuer jusqu'au point d'arrêt\tF5", C_LANCER);
        ajouter(executer, "Arrêter le pas à pas\tÉchap", C_FIN_PAS);
        let cube = CreatePopupMenu();
        ajouter(cube, "Étage &0 (le code)", C_ETAGE);
        ajouter(cube, "Étage &1", C_ETAGE + 1);
        ajouter(cube, "Étage &2", C_ETAGE + 2);
        ajouter(cube, "Étage &3", C_ETAGE + 3);
        ajouter(cube, "", 0);
        ajouter(cube, "&Vue : perspective, à plat, en quits\tF6", C_VUE);
        ajouter(cube, "&Largeur de l'image (à plat)", C_LARGEUR);
        ajouter(cube, "&Effacer la mémoire affichée", C_EFFACER);
        ajouter(cube, "", 0);
        ajouter(cube, "Enregistrer l'&animation (GIF) : commencer, finir\tCtrl+G", C_GIF);
        ajouter(cube, "&Image du programme en PNG", C_PNG);
        let aide = CreatePopupMenu();
        ajouter(aide, "&Associer les fichiers .vtx à l'atelier", C_ASSOCIER);
        ajouter(aide, "À &propos", C_APROPOS);
        for (m, t) in [(fichier, "&Fichier"), (edition, "&Édition"), (executer, "E&xécuter"), (cube, "&Cube"), (aide, "&Aide")] {
            AppendMenuW(barre, MF_POPUP, m as usize, w(t).as_ptr());
        }
        SetMenu(fen, barre);
        for (c, x) in [(C_M32, 32), (C_M64, 64), (C_LUGUS, 128)] {
            CheckMenuItem(barre, c as u32, if a().machine == x { 8 } else { 0 });
        }
    }
}

fn commande(c: u16) {
    let at = a();
    let cible = || {
        let f = unsafe { GetFocus() };
        let b = a();
        if f == b.sortie || f == b.entrees { f } else { b.source }
    };
    unsafe {
        match c {
            C_NOUVEAU => {
                if peut_quitter() {
                    at.fichier = None;
                    ecrire_texte(at.source, MODELE);
                    SendMessageW(at.source, EM_SETMODIFY, 0, 0);
                    effacer_resultats();
                    titre();
                }
            }
            C_OUVRIR => {
                if peut_quitter() {
                    if let Some(f) = dialogue_fichier(false) {
                        charger(&f);
                    }
                }
            }
            C_ENREGISTRER => {
                enregistrer(false);
            }
            C_ENREGISTRER_SOUS => {
                enregistrer(true);
            }
            C_QUITTER => {
                if peut_quitter() {
                    DestroyWindow(at.fen);
                }
            }
            C_ANNULER => {
                SendMessageW(cible(), WM_UNDO, 0, 0);
            }
            C_COUPER => {
                SendMessageW(cible(), WM_CUT, 0, 0);
            }
            C_COPIER => {
                SendMessageW(cible(), WM_COPY, 0, 0);
            }
            C_COLLER => {
                SendMessageW(cible(), WM_PASTE, 0, 0);
            }
            C_TOUT => {
                SendMessageW(cible(), EM_SETSEL, 0, -1);
            }
            C_LANCER => {
                if at.pas.is_some() {
                    avancer(Avance::Continuer);
                } else {
                    lancer();
                }
            }
            C_MACHINE64 | C_M32 | C_M64 | C_LUGUS => {
                let m = match c {
                    C_M32 => 32,
                    C_M64 => 64,
                    C_LUGUS => 128,
                    _ => match at.machine { 64 => 128, 128 => 32, _ => 64 },
                };
                choisir_machine(m);
                let m = a().machine;
                etat(&format!("machine {} : F5 et le pas à pas compilent avec {}", nom_machine(m), compilateur_de(m)));
            }
            C_PURGER => {
                effacer_resultats();
                etat("mémoire du programme rendue (cube et arbre vidés)");
            }
            C_ONGLET_SORTIE => montrer_onglet(0),
            C_ONGLET_TERMINAL => montrer_onglet(1),
            C_ONGLET_PAS => montrer_onglet(2),
            C_ARRETER if at.pas.is_some() => arreter_pas("pas à pas arrêté : retour à l'édition"),
            C_ARRETER => {
                if at.en_cours {
                    ARRET.store(true, Ordering::Relaxed);
                    at.tx_entree = None; // un programme qui attend une ligne la reçoit vide : il peut finir
                    etat("arrêt demandé…");
                }
            }
            C_ASSOCIER => match super::installer(true) {
                Ok(m) => message(&m),
                Err(e) => message(&e),
            },
            C_GIF => basculer_enregistrement(),
            C_PNG => image_png(),
            C_PAS => avancer(Avance::Pas),
            C_PAS_DESSUS => avancer(Avance::Dessus),
            C_POINT => basculer_point(),
            C_FIN_PAS => arreter_pas("pas à pas arrêté : retour à l'édition"),
            x if (C_ETAGE..C_ETAGE + 4).contains(&x) => {
                at.etage = (x - C_ETAGE) as u32;
                at.base = 0;
                etat(&format!("cube : étage {}", at.etage));
                InvalidateRect(at.cube, std::ptr::null(), 0);
            }
            C_VUE => {
                // image du programme (s'il dessine) → cube en perspective → à plat → en quits → image…
                let a_dessin = IMAGE.lock().unwrap().is_some();
                if at.dessin {
                    at.dessin = false;
                    at.iso = true;
                } else if at.iso {
                    at.iso = false;
                    at.vue_quits = false;
                } else if !at.vue_quits {
                    at.vue_quits = true;
                } else {
                    at.vue_quits = false;
                    at.iso = true;
                    at.dessin = a_dessin;
                }
                if !at.iso && !at.dessin {
                    if at.vue_quits {
                        etat(&format!("en quits · étage {} · {} mots par ligne · chaque mot : 16 quits en 4 × 4 (quit 15 en haut à gauche) · \
                                       gris inconnu, rouge faux, vert vrai, orange variable · clic : un mot", at.etage, at.largeur));
                    } else {
                        etat(&format!("à plat · étage {} · {} mots par ligne · clic : la valeur d'un mot · molette : défiler", at.etage, at.largeur));
                    }
                }
                InvalidateRect(at.cube, std::ptr::null(), 0);
            }
            C_LARGEUR => {
                let l = [16, 32, 64, 128, 256, 512, 1024];
                let i = l.iter().position(|&x| x == at.largeur).unwrap_or(0);
                at.largeur = l[(i + 1) % l.len()];
                etat(&format!("à plat · {} mots par ligne", at.largeur));
                InvalidateRect(at.cube, std::ptr::null(), 0);
            }
            C_EFFACER => {
                at.mem = None;
                at.vue64 = None;
                InvalidateRect(at.cube, std::ptr::null(), 0);
            }
            C_APROPOS => message("Atelier vtx\n\nVercintorix : le langage du cube chromatique et de la logique à quatre valeurs.\n\nMachine SPU-64 (par défaut) : mots de 64 bits, points profonds #RRRRGGGGBBBBAAAA, compilés par vtxc64 ; le cube les montre en points de 32 bits. Machine Lugus (SPU-128) : mots de 128 bits, points de matière (trois couleurs de 32 bits et la matière), flottants de 128 bits, compilés par vtxc128 ; le cube les montre aussi en points de 32 bits (la transparence en alpha). Machine SPU-32 : mots #RRGGBBAA, compilés par vtxc. Exécuter › Machine suivante (Ctrl+M) passe de l'une à l'autre ; « // machine : lugus » en tête d'un programme la choisit.\n\nF5 lance le programme, F6 change la vue du cube.\nPas à pas : F7 ligne suivante, F8 sans entrer dans les fonctions, F9 point d'arrêt, F5 continuer, Échap arrêter."),
            _ => {}
        }
    }
}

unsafe extern "system" fn proc_fenetre(h: H, m: u32, wp: usize, lp: isize) -> isize {
    match m {
        WM_CREATE => {
            a().fen = h;
            creer_controles(h);
            menus(h);
            0
        }
        WM_SIZE => {
            if !a().source.is_null() {
                disposer(h);
            }
            0
        }
        WM_COMMAND => {
            let id = (wp & 0xFFFF) as u16;
            let notif = (wp >> 16) & 0xFFFF;
            if lp as H == a().source {
                if notif == EN_CHANGE {
                    titre();
                    arreter_pas("le texte a changé : pas à pas arrêté");
                }
                return 0;
            }
            if lp as H == a().entrees || lp as H == a().sortie || lp as H == a().term_entree || lp as H == a().journal
                || lp as H == a().pas_texte {
                return 0;
            }
            commande(id);
            0
        }
        WM_CTLCOLOREDIT | WM_CTLCOLORSTATIC => {
            // l'éditeur et la sortie en sombre ; le reste garde les couleurs de Windows
            let at = a();
            if lp as H == at.source || lp as H == at.sortie || lp as H == at.term_entree || lp as H == at.journal || lp as H == at.pas_texte {
                SetTextColor(wp as H, TEXTE);
                SetBkColor(wp as H, FOND);
                return at.pinceau as isize;
            }
            DefWindowProcW(h, m, wp, lp)
        }
        WM_APP_FINI => {
            fini();
            0
        }
        WM_APP_CLAVIER => {
            if a().en_cours {
                SetFocus(a().cube);
            }
            0
        }
        WM_TIMER => {
            if wp == 2 {
                suivre_lignes();
            } else {
                vider_sortie_programme();
            }
            0
        }
        WM_CLOSE => {
            if peut_quitter() {
                DestroyWindow(h);
            }
            0
        }
        WM_DESTROY => {
            PostQuitMessage(0);
            0
        }
        _ => DefWindowProcW(h, m, wp, lp),
    }
}

/// atelier.exe : la fenêtre, sur le fichier donné (ou un nouveau programme).
pub fn lancer_fenetre(fichier: Option<&str>) {
    unsafe {
        SetProcessDPIAware();
        let inst = GetModuleHandleW(std::ptr::null());
        let boite = Box::new(Atelier {
            inst, fen: std::ptr::null_mut(), source: std::ptr::null_mut(), sortie: std::ptr::null_mut(), entrees: std::ptr::null_mut(),
            cube: std::ptr::null_mut(), etat: std::ptr::null_mut(), boutons: Vec::new(), etiquettes: Vec::new(),
            police: std::ptr::null_mut(), police_ui: std::ptr::null_mut(), pinceau: std::ptr::null_mut(), echelle: 1.0,
            fichier: None, mem: None, etage: 1, iso: true, vue_quits: false, largeur: 64, base: 0, zoom: 1.0, en_cours: false, ancien_proc_source: 0,
            term_entree: std::ptr::null_mut(), journal: std::ptr::null_mut(), onglets: [std::ptr::null_mut(); 3], onglet: 1,
            pas: None, points: HashSet::new(), pas_texte: std::ptr::null_mut(),
            ancien_proc_term: 0, arbre: std::ptr::null_mut(), noeuds: Vec::new(),
            ouverts: HashSet::new(), defile: 0, choisi: None, lignes: std::ptr::null_mut(), vue_lignes: (-1, -1), ligne_erreur: None,
            dessin: false, rx_sortie: None, tx_entree: None, icone: std::ptr::null_mut(), machine: 64, vue64: None,
            quart: 0, decal: (0, 0), glisse: None,
        });
        ATELIER = Box::into_raw(boite);
        let curseur = LoadCursorW(std::ptr::null_mut(), IDC_ARROW as *const u16);
        // l'icône du cube, à côté de l'exécutable (écrite la première fois)
        if let Some(d) = std::env::current_exe().ok().and_then(|e| e.parent().map(|p| p.to_path_buf())) {
            let f = d.join("vtx.ico");
            if !f.exists() {
                let _ = std::fs::write(&f, super::cube::ico(&[16, 32, 48, 256]));
            }
            a().icone = LoadImageW(std::ptr::null_mut(), w(&f.to_string_lossy()).as_ptr(), 1, 0, 0, 0x10 | 0x40);
        }
        let nom_fen = w("VtxAtelier");
        let nom_cube = w("VtxCube");
        let classe = WndClassEx {
            cbSize: std::mem::size_of::<WndClassEx>() as u32, style: 0, lpfnWndProc: proc_fenetre, cbClsExtra: 0, cbWndExtra: 0,
            hInstance: inst, hIcon: a().icone, hCursor: curseur, hbrBackground: 16 as H, // COLOR_BTNFACE + 1
            lpszMenuName: std::ptr::null(), lpszClassName: nom_fen.as_ptr(), hIconSm: a().icone,
        };
        RegisterClassExW(&classe);
        let nom_arbre = w("VtxArbre");
        let classe_arbre = WndClassEx {
            cbSize: std::mem::size_of::<WndClassEx>() as u32, style: 0x3, lpfnWndProc: proc_arbre, cbClsExtra: 0, cbWndExtra: 0,
            hInstance: inst, hIcon: std::ptr::null_mut(), hCursor: curseur, hbrBackground: std::ptr::null_mut(),
            lpszMenuName: std::ptr::null(), lpszClassName: nom_arbre.as_ptr(), hIconSm: std::ptr::null_mut(),
        };
        RegisterClassExW(&classe_arbre);
        let nom_lignes = w("VtxLignes");
        let classe_lignes = WndClassEx {
            cbSize: std::mem::size_of::<WndClassEx>() as u32, style: 0x3, lpfnWndProc: proc_lignes, cbClsExtra: 0, cbWndExtra: 0,
            hInstance: inst, hIcon: std::ptr::null_mut(), hCursor: curseur, hbrBackground: std::ptr::null_mut(),
            lpszMenuName: std::ptr::null(), lpszClassName: nom_lignes.as_ptr(), hIconSm: std::ptr::null_mut(),
        };
        RegisterClassExW(&classe_lignes);
        let classe_cube = WndClassEx {
            cbSize: std::mem::size_of::<WndClassEx>() as u32, style: 0xB, lpfnWndProc: proc_cube, cbClsExtra: 0, cbWndExtra: 0,
            hInstance: inst, hIcon: std::ptr::null_mut(), hCursor: curseur, hbrBackground: std::ptr::null_mut(),
            lpszMenuName: std::ptr::null(), lpszClassName: nom_cube.as_ptr(), hIconSm: std::ptr::null_mut(),
        };
        RegisterClassExW(&classe_cube);
        let fen = CreateWindowExW(0, nom_fen.as_ptr(), w("Atelier vtx").as_ptr(), WS_OVERLAPPEDWINDOW | WS_CLIPCHILDREN,
                                  CW_USEDEFAULT, CW_USEDEFAULT, 1400, 860, std::ptr::null_mut(), std::ptr::null_mut(), inst,
                                  std::ptr::null_mut());
        if fen.is_null() {
            return;
        }
        match fichier {
            Some(f) => charger(Path::new(f)),
            None => {
                ecrire_texte(a().source, MODELE);
                SendMessageW(a().source, EM_SETMODIFY, 0, 0);
                titre();
                etat("F5 lance le programme · Fichier › Ouvrir pour un exemple · le cube montre la mémoire après l'exécution");
            }
        }
        ShowWindow(fen, 3); // agrandie
        SetTimer(fen, 2, 100, std::ptr::null()); // les numéros de ligne suivent le défilement du texte
        disposer(fen);
        montrer_onglet(0);
        SetFocus(a().source);
        let raccourcis = [
            Accel { fVirt: FVIRTKEY | FCONTROL, key: b'N' as u16, cmd: C_NOUVEAU },
            Accel { fVirt: FVIRTKEY | FCONTROL, key: b'O' as u16, cmd: C_OUVRIR },
            Accel { fVirt: FVIRTKEY | FCONTROL, key: b'S' as u16, cmd: C_ENREGISTRER },
            Accel { fVirt: FVIRTKEY | FCONTROL, key: b'A' as u16, cmd: C_TOUT },
            Accel { fVirt: FVIRTKEY | FCONTROL, key: b'M' as u16, cmd: C_MACHINE64 },
            Accel { fVirt: FVIRTKEY | FCONTROL, key: b'G' as u16, cmd: C_GIF },
            Accel { fVirt: FVIRTKEY, key: 0x74, cmd: C_LANCER }, // F5
            Accel { fVirt: FVIRTKEY | 4, key: 0x74, cmd: C_ARRETER }, // Maj+F5
            Accel { fVirt: FVIRTKEY, key: 0x75, cmd: C_VUE },    // F6
            Accel { fVirt: FVIRTKEY, key: 0x76, cmd: C_PAS },    // F7
            Accel { fVirt: FVIRTKEY, key: 0x77, cmd: C_PAS_DESSUS }, // F8
            Accel { fVirt: FVIRTKEY, key: 0x78, cmd: C_POINT },  // F9
            Accel { fVirt: FVIRTKEY, key: 0x1B, cmd: C_FIN_PAS }, // Échap
        ];
        let table = CreateAcceleratorTableW(raccourcis.as_ptr(), raccourcis.len() as i32);
        let mut msg: Msg = std::mem::zeroed();
        while GetMessageW(&mut msg, std::ptr::null_mut(), 0, 0) > 0 {
            // pendant l'exécution, les touches tapées dans l'image vont au programme (Échap compris)
            let at = a();
            // les raccourcis de l'atelier restent à l'atelier : Ctrl+…, Alt+… et les touches F1 à F12
            let direct = at.en_cours && msg.hwnd == at.cube && matches!(msg.message, WM_KEYDOWN | WM_KEYUP)
                && !(0x70..=0x7B).contains(&msg.wParam) && GetKeyState(0x11) >= 0 && GetKeyState(0x12) >= 0;
            if direct || TranslateAcceleratorW(fen, table, &mut msg) == 0 {
                TranslateMessage(&msg);
                DispatchMessageW(&msg);
            }
        }
    }
}
