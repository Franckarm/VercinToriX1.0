// La vitrine d'un .exe de Lugus : lancé d'un double clic sous Windows, le programme a sa fenêtre à lui au lieu d'une
// console grise. À gauche son texte (ce qu'il écrit, ce qu'on lui tape) ; à droite le cube chromatique de sa mémoire,
// en perspective, qui se remplit pendant qu'il tourne ; en bas l'état de la machine. La fenêtre de dessin (toile)
// s'ouvre à part, à la première image, comme avant.
//
// La machine tourne sur son fil, par tranches de quelques millions d'instructions ; entre deux tranches, et chaque fois
// que le programme attend le clavier, elle laisse une vue de sa mémoire (pas64::Vue64, celle d'Ogmios) que la fenêtre
// dessine avec cube::rendre_iso. Clic : l'étage suivant ; clic droit : tourner d'un quart ; molette : zoom.

#[cfg(windows)]
pub use w::jouer;

#[cfg(windows)]
mod w {
    use std::collections::VecDeque;
    use std::ffi::c_void;
    use std::sync::atomic::{AtomicBool, AtomicIsize, AtomicU64, Ordering};
    use std::sync::{Condvar, Mutex};
    use std::time::{Duration, Instant};

    use super::super::cube::rendre_iso;
    use super::super::memoire::Memoire;
    use super::super::pas64::Vue64;
    use super::super::spu128::Spu128;

    type H = *mut c_void;

    #[repr(C)]
    struct WndClassEx {
        cb_size: u32, style: u32, proc_: unsafe extern "system" fn(H, u32, usize, isize) -> isize, cls: i32, wnd: i32,
        inst: H, icone: H, curseur: H, fond: H, menu: *const u16, nom: *const u16, icone_p: H,
    }
    #[repr(C)]
    #[derive(Default, Clone, Copy)]
    struct Rect { left: i32, top: i32, right: i32, bottom: i32 }
    #[repr(C)]
    struct Msg { h: H, m: u32, wp: usize, lp: isize, t: u32, x: i32, y: i32 }
    #[repr(C)]
    struct PaintStruct { dc: H, efface: i32, r: Rect, restore: i32, maj: i32, res: [u8; 32] }
    #[repr(C)]
    struct BitmapInfoHeader {
        size: u32, l: i32, h: i32, plans: u16, bits: u16, compr: u32, taille: u32, xm: i32, ym: i32, used: u32, imp: u32,
    }
    #[repr(C)]
    struct BitmapInfo { tete: BitmapInfoHeader, couleurs: [u32; 1] }
    #[repr(C)]
    #[derive(Default)]
    struct Taille { cx: i32, cy: i32 }

    // les mêmes fonctions que sortie.rs, avec des structures de même forme (Msg : 48 octets)
    #[allow(clashing_extern_declarations)]
    #[link(name = "user32")]
    extern "system" {
        fn RegisterClassExW(c: *const WndClassEx) -> u16;
        fn CreateWindowExW(ex: u32, cls: *const u16, titre: *const u16, style: u32, x: i32, y: i32, l: i32, h: i32,
                           parent: H, menu: H, inst: H, p: *mut c_void) -> H;
        fn DefWindowProcW(h: H, m: u32, wp: usize, lp: isize) -> isize;
        fn GetMessageW(m: *mut Msg, h: H, a: u32, b: u32) -> i32;
        fn TranslateMessage(m: *const Msg) -> i32;
        fn DispatchMessageW(m: *const Msg) -> isize;
        fn PostQuitMessage(c: i32);
        fn BeginPaint(h: H, p: *mut PaintStruct) -> H;
        fn EndPaint(h: H, p: *const PaintStruct) -> i32;
        fn GetClientRect(h: H, r: *mut Rect) -> i32;
        fn InvalidateRect(h: H, r: *const Rect, e: i32) -> i32;
        fn SetTimer(h: H, id: usize, ms: u32, f: *const c_void) -> usize;
        fn LoadCursorW(i: H, n: *const u16) -> H;
        fn LoadIconW(i: H, n: *const u16) -> H;
        fn ShowWindow(h: H, c: i32) -> i32;
        fn FillRect(dc: H, r: *const Rect, b: H) -> i32;
        fn SetProcessDPIAware() -> i32;
    }
    #[link(name = "gdi32")]
    extern "system" {
        fn StretchDIBits(dc: H, x: i32, y: i32, l: i32, h: i32, sx: i32, sy: i32, sl: i32, sh: i32, bits: *const c_void,
                         info: *const BitmapInfo, usage: u32, rop: u32) -> i32;
        fn CreateFontW(h: i32, l: i32, e: i32, o: i32, poids: i32, it: u32, so: u32, ba: u32, cs: u32, op: u32, cp: u32,
                       q: u32, pf: u32, nom: *const u16) -> H;
        fn SelectObject(dc: H, o: H) -> H;
        fn DeleteObject(o: H) -> i32;
        fn SetTextColor(dc: H, c: u32) -> u32;
        fn SetBkMode(dc: H, m: i32) -> i32;
        fn TextOutW(dc: H, x: i32, y: i32, t: *const u16, n: i32) -> i32;
        fn GetTextExtentPoint32W(dc: H, t: *const u16, n: i32, s: *mut Taille) -> i32;
        fn CreateSolidBrush(c: u32) -> H;
        fn CreateCompatibleDC(dc: H) -> H;
        fn CreateCompatibleBitmap(dc: H, l: i32, h: i32) -> H;
        fn BitBlt(d: H, x: i32, y: i32, l: i32, h: i32, s: H, sx: i32, sy: i32, rop: u32) -> i32;
        fn DeleteDC(dc: H) -> i32;
    }
    #[link(name = "kernel32")]
    extern "system" {
        fn GetModuleHandleW(n: *const u16) -> H;
        fn FreeConsole() -> i32;
    }

    fn w(s: &str) -> Vec<u16> {
        s.encode_utf16().chain(std::iter::once(0)).collect()
    }
    /// une couleur Windows (0x00BBGGRR) depuis #RRGGBB
    fn bgr(c: u32) -> u32 {
        ((c & 0xFF) << 16) | (c & 0xFF00) | ((c >> 16) & 0xFF)
    }

    const FOND: u32 = 0x10_1418;
    const ENCRE: u32 = 0xE6_E1D3;
    const SAISIE: u32 = 0xF2_C14E;
    const DISCRET: u32 = 0x8A_93A6;

    /// la mémoire montrée : une Memoire de 32 bits par étage (le cube de l'atelier), prise par la machine
    struct Vue(Memoire);
    unsafe impl Send for Vue {}

    struct Etat {
        lignes: Vec<String>,
        saisie: String,
        fini: Option<String>,
        vue: Option<Vue>,
        etages_pleins: [bool; 4],
        // la vue dessinée (refaite quand la mémoire ou le regard change)
        rendu: Option<(usize, usize, Vec<u32>, usize)>,
        neuf: bool,
        etage: u32,
        quart: u32,
        zoom: f32,
    }

    static ETAT: Mutex<Option<Etat>> = Mutex::new(None);
    static CLAVIER: Mutex<VecDeque<u128>> = Mutex::new(VecDeque::new());
    static SIGNAL: Condvar = Condvar::new();
    static FERMEE: AtomicBool = AtomicBool::new(false);
    static PAS: AtomicU64 = AtomicU64::new(0);
    static DERNIERE_VUE: AtomicU64 = AtomicU64::new(u64::MAX);
    static FENETRE: AtomicIsize = AtomicIsize::new(0);
    static ATTEND: AtomicBool = AtomicBool::new(false);
    static FINI: AtomicBool = AtomicBool::new(false);
    static TITRE: Mutex<String> = Mutex::new(String::new());

    fn avec<R>(f: impl FnOnce(&mut Etat) -> R) -> R {
        let mut g = ETAT.lock().unwrap();
        f(g.as_mut().unwrap())
    }

    fn rafraichir() {
        let f = FENETRE.load(Ordering::Relaxed);
        if f != 0 {
            unsafe { InvalidateRect(f as H, std::ptr::null(), 0) };
        }
    }

    /// la machine laisse une vue de sa mémoire (au plus une par pas : la lecture d'une ligne en appelle une par lettre)
    fn prendre_vue(s: &Spu128) {
        if DERNIERE_VUE.swap(s.pas, Ordering::Relaxed) == s.pas {
            return;
        }
        PAS.store(s.pas, Ordering::Relaxed);
        let mut v = Vue64::depuis128(s);
        let mut pleins = [false; 4];
        for e in 0..4usize {
            pleins[e] = !s.pages_etage(e).is_empty();
        }
        let m = v.memoire();
        avec(|e| {
            e.vue = Some(Vue(m));
            e.etages_pleins = pleins;
            // le premier regard : l'étage des données (3, le tas) s'il a quelque chose, sinon celui du code
            if !e.etages_pleins[e.etage as usize] {
                e.etage = [3u32, 2, 1, 0].into_iter().find(|&k| pleins[k as usize]).unwrap_or(0);
            }
            e.neuf = true;
        });
        rafraichir();
    }

    fn ecrire_car(v: u128) {
        let c = match char::from_u32((v & 0x1F_FFFF) as u32) {
            Some(c) => c,
            None => return,
        };
        avec(|e| {
            if c == '\n' {
                e.lignes.push(String::new());
                if e.lignes.len() > 5000 {
                    e.lignes.drain(..1000);
                }
            } else if c != '\r' {
                e.lignes.last_mut().unwrap().push(c);
            }
        });
        if c == '\n' {
            rafraichir();
        }
    }

    fn lire_car() -> u128 {
        rafraichir();
        let mut q = CLAVIER.lock().unwrap();
        loop {
            if let Some(c) = q.pop_front() {
                if q.is_empty() {
                    ATTEND.store(false, Ordering::Relaxed);
                }
                return c;
            }
            if FERMEE.load(Ordering::Relaxed) {
                return u128::MAX;
            }
            if !ATTEND.swap(true, Ordering::Relaxed) {
                rafraichir();
            }
            q = SIGNAL.wait_timeout(q, Duration::from_millis(200)).unwrap().0;
        }
    }

    unsafe extern "system" fn proc_vitrine(h: H, m: u32, wp: usize, lp: isize) -> isize {
        match m {
            0x0014 => 1, // WM_ERASEBKGND
            0x000F => {
                peindre(h);
                0
            }
            0x0102 => {
                // WM_CHAR : la ligne tapée, rendue au programme à Entrée
                let c = char::from_u32(wp as u32).unwrap_or('\0');
                let mut fini = false;
                avec(|e| {
                    if e.fini.is_some() {
                        fini = true;
                        return;
                    }
                    match c {
                        '\r' | '\n' => {
                            let t = std::mem::take(&mut e.saisie);
                            e.lignes.last_mut().unwrap().push_str(&t);
                            let mut q = CLAVIER.lock().unwrap();
                            q.extend(t.chars().map(|c| c as u128));
                            q.push_back(10);
                        }
                        '\u{8}' => {
                            e.saisie.pop();
                        }
                        c if !c.is_control() => e.saisie.push(c),
                        _ => {}
                    }
                });
                if fini && (c == '\r' || c == '\u{1b}') {
                    PostQuitMessage(0);
                }
                SIGNAL.notify_all();
                InvalidateRect(h, std::ptr::null(), 0);
                0
            }
            0x0201 | 0x0204 => {
                // clic : l'étage suivant qui a quelque chose ; clic droit : un quart de tour
                avec(|e| {
                    if m == 0x0201 {
                        for k in 1..=4u32 {
                            let n = (e.etage + k) % 4;
                            if e.etages_pleins[n as usize] {
                                e.etage = n;
                                break;
                            }
                        }
                    } else {
                        e.quart = (e.quart + 1) % 4;
                    }
                    e.neuf = true;
                });
                InvalidateRect(h, std::ptr::null(), 0);
                0
            }
            0x020A => {
                let d = ((wp >> 16) & 0xFFFF) as i16 as i32;
                avec(|e| {
                    e.zoom = (e.zoom * if d > 0 { 1.25 } else { 0.8 }).clamp(0.25, 16.0);
                    e.neuf = true;
                });
                InvalidateRect(h, std::ptr::null(), 0);
                0
            }
            0x0113 => {
                // WM_TIMER : le compteur d'instructions et le curseur
                InvalidateRect(h, std::ptr::null(), 0);
                0
            }
            0x0010 | 0x0002 => {
                // WM_CLOSE, WM_DESTROY
                FERMEE.store(true, Ordering::Relaxed);
                SIGNAL.notify_all();
                PostQuitMessage(0);
                0
            }
            _ => DefWindowProcW(h, m, wp, lp),
        }
    }

    unsafe fn texte(dc: H, x: i32, y: i32, t: &str, c: u32) {
        let u: Vec<u16> = t.encode_utf16().collect();
        SetTextColor(dc, bgr(c));
        TextOutW(dc, x, y, u.as_ptr(), u.len() as i32);
    }

    unsafe fn peindre(h: H) {
        let mut ps: PaintStruct = std::mem::zeroed();
        let dc0 = BeginPaint(h, &mut ps);
        let mut r = Rect::default();
        GetClientRect(h, &mut r);
        let (l, ht) = ((r.right - r.left).max(1), (r.bottom - r.top).max(1));
        // double tampon : rien ne clignote
        let dc = CreateCompatibleDC(dc0);
        let bm = CreateCompatibleBitmap(dc0, l, ht);
        let ancien_bm = SelectObject(dc, bm);
        let fond = CreateSolidBrush(bgr(FOND));
        FillRect(dc, &r, fond);
        DeleteObject(fond);
        let police = CreateFontW(-17, 0, 0, 0, 400, 0, 0, 0, 1, 0, 0, 5, 49, w("Consolas").as_ptr());
        let ancienne = SelectObject(dc, police);
        SetBkMode(dc, 1);
        let mut t = Taille::default();
        let m = w("M");
        GetTextExtentPoint32W(dc, m.as_ptr(), 1, &mut t);
        let (cw, ch) = (t.cx.max(6), t.cy.max(12) + 2);

        let marge = 14;
        let cube_l = (l * 2 / 5).clamp(200, 900);
        let texte_l = l - cube_l - marge * 3;
        let colonnes = (texte_l / cw).max(10) as usize;
        let bas = ht - ch - marge;

        let mut g = ETAT.lock().unwrap();
        let e = g.as_mut().unwrap();
        // les lignes, coupées à la largeur, les dernières en bas
        let ms = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map(|d| d.as_millis()).unwrap_or(0);
        let curseur = if (ms / 500) % 2 == 0 { "▌" } else { " " };
        let mut vues: Vec<(String, u32)> = Vec::new();
        let n = e.lignes.len();
        for (i, li) in e.lignes.iter().enumerate() {
            let (corps, saisie) = if i + 1 == n && e.fini.is_none() { (li.clone(), Some(format!("{}{}", e.saisie, curseur))) } else { (li.clone(), None) };
            let tout: Vec<char> = corps.chars().chain(saisie.clone().unwrap_or_default().chars()).collect();
            let nc = corps.chars().count();
            if tout.is_empty() {
                vues.push((String::new(), ENCRE));
                continue;
            }
            for (k, morceau) in tout.chunks(colonnes).enumerate() {
                let debut = k * colonnes;
                if saisie.is_some() && debut + morceau.len() > nc {
                    // la part tapée, d'une autre couleur
                    let coupe = nc.saturating_sub(debut).min(morceau.len());
                    vues.push((morceau[..coupe].iter().collect(), ENCRE));
                    vues.push((format!("\u{0}{}", morceau[coupe..].iter().collect::<String>()), SAISIE));
                } else {
                    vues.push((morceau.iter().collect(), ENCRE));
                }
            }
        }
        // (une entrée qui commence par \0 continue la ligne précédente)
        let mut rangs: Vec<Vec<(String, u32)>> = Vec::new();
        for (s, c) in vues {
            if let Some(rest) = s.strip_prefix('\u{0}') {
                if let Some(d) = rangs.last_mut() {
                    d.push((rest.to_string(), c));
                    continue;
                }
            }
            rangs.push(vec![(s, c)]);
        }
        let visibles = ((bas - marge) / ch).max(1) as usize;
        let debut = rangs.len().saturating_sub(visibles);
        for (k, rang) in rangs[debut..].iter().enumerate() {
            let y = marge + k as i32 * ch;
            let mut x = marge;
            for (s, c) in rang {
                texte(dc, x, y, s, *c);
                x += s.chars().count() as i32 * cw;
            }
        }

        // le cube
        let (cx, cy, cl, chh) = (l - cube_l - marge, marge, cube_l, bas - marge * 2);
        let (pl, ph) = (cl.max(1) as usize, chh.max(1) as usize);
        let refaire = e.neuf || e.rendu.as_ref().map(|r| r.0 != pl || r.1 != ph).unwrap_or(true);
        if refaire {
            if let Some(v) = &e.vue {
                let mut px = vec![FOND; pl * ph];
                let n = rendre_iso(&v.0, e.etage, e.zoom, e.quart, (0, 0), pl, ph, &mut px);
                e.rendu = Some((pl, ph, px, n));
                e.neuf = false;
            }
        }
        if let Some((rl, rh, px, _)) = &e.rendu {
            let info = BitmapInfo {
                tete: BitmapInfoHeader { size: std::mem::size_of::<BitmapInfoHeader>() as u32, l: *rl as i32, h: -(*rh as i32),
                    plans: 1, bits: 32, compr: 0, taille: 0, xm: 0, ym: 0, used: 0, imp: 0 },
                couleurs: [0],
            };
            StretchDIBits(dc, cx, cy, *rl as i32, *rh as i32, 0, 0, *rl as i32, *rh as i32, px.as_ptr() as *const c_void, &info,
                          0, 0x00CC_0020);
        } else {
            texte(dc, cx + 10, cy + 10, "le cube se remplit quand la machine tourne…", DISCRET);
        }

        // l'état
        let pas = PAS.load(Ordering::Relaxed);
        let mots = e.rendu.as_ref().map(|r| r.3).unwrap_or(0);
        let ou = match &e.fini {
            Some(f) => format!("{} · Entrée ou Échap : fermer", f),
            None if ATTEND.load(Ordering::Relaxed) => "le programme attend votre réponse (Entrée pour l'envoyer)".to_string(),
            None => "la machine tourne".to_string(),
        };
        let etat = format!("{} · Lugus · {} instructions · cube : étage {}, {} mots · clic : étage · clic droit : tourner · molette : zoom",
                           ou, grouper(pas), e.etage, mots);
        texte(dc, marge, ht - ch - 6, &etat, DISCRET);
        drop(g);

        SelectObject(dc, ancienne);
        DeleteObject(police);
        BitBlt(dc0, 0, 0, l, ht, dc, 0, 0, 0x00CC_0020);
        SelectObject(dc, ancien_bm);
        DeleteObject(bm);
        DeleteDC(dc);
        EndPaint(h, &ps);
    }

    fn grouper(n: u64) -> String {
        let s = n.to_string();
        let mut o = String::new();
        for (i, c) in s.chars().enumerate() {
            if i > 0 && (s.len() - i) % 3 == 0 {
                o.push(' ');
            }
            o.push(c);
        }
        o
    }

    /// Joue le programme dans la vitrine ; rend le code de sortie quand la fenêtre est fermée.
    pub fn jouer(mut s: Spu128, nom: &str) -> i32 {
        unsafe {
            FreeConsole();
            SetProcessDPIAware();
        }
        *ETAT.lock().unwrap() = Some(Etat {
            lignes: vec![String::new()], saisie: String::new(), fini: None, vue: None,
            etages_pleins: [false; 4], rendu: None, neuf: false, etage: 3, quart: 0, zoom: 1.0,
        });
        s.console_ecrire = Some(Box::new(ecrire_car));
        s.console_lire = Some(Box::new(lire_car));
        s.avant_lire = Some(prendre_vue);
        *TITRE.lock().unwrap() = format!("{} — Vercintorix, machine Lugus", nom);
        // la fenêtre sur son fil (elle ne tient que des statiques) ; la machine sur celui-ci
        let (tx, rx) = std::sync::mpsc::channel::<bool>();
        std::thread::spawn(move || unsafe {
            let inst = GetModuleHandleW(std::ptr::null());
            let nom_cls = w("VtxVitrine");
            let classe = WndClassEx {
                cb_size: std::mem::size_of::<WndClassEx>() as u32, style: 3, proc_: proc_vitrine, cls: 0, wnd: 0, inst,
                icone: LoadIconW(inst, 1 as *const u16), curseur: LoadCursorW(std::ptr::null_mut(), 32512 as *const u16),
                fond: std::ptr::null_mut(), menu: std::ptr::null(), nom: nom_cls.as_ptr(),
                icone_p: std::ptr::null_mut(),
            };
            RegisterClassExW(&classe);
            let titre = w(&TITRE.lock().unwrap().clone());
            let h = CreateWindowExW(0, nom_cls.as_ptr(), titre.as_ptr(), 0x00CF_0000 | 0x1000_0000, 0x8000_0000u32 as i32,
                                    0x8000_0000u32 as i32, 1200, 760, std::ptr::null_mut(), std::ptr::null_mut(), inst,
                                    std::ptr::null_mut());
            if h.is_null() {
                let _ = tx.send(false);
                return;
            }
            FENETRE.store(h as isize, Ordering::Relaxed);
            ShowWindow(h, 5);
            SetTimer(h, 1, 250, std::ptr::null());
            let _ = tx.send(true);
            let mut msg: Msg = std::mem::zeroed();
            while GetMessageW(&mut msg, std::ptr::null_mut(), 0, 0) > 0 {
                TranslateMessage(&msg);
                DispatchMessageW(&msg);
            }
            FENETRE.store(0, Ordering::Relaxed);
            FERMEE.store(true, Ordering::Relaxed);
            SIGNAL.notify_all();
            // fermée avant la fin du programme : on ne le laisse pas tourner sans fenêtre
            if !FINI.load(Ordering::Relaxed) {
                std::process::exit(0);
            }
        });
        if rx.recv() != Ok(true) {
            return 2;
        }
        let mut derniere = Instant::now();
        let r = loop {
            let borne = s.pas.saturating_add(3_000_000);
            match s.executer(borne) {
                Ok(()) => break Ok(()),
                Err(e) if e.starts_with("limite de") && !s.arrete => {
                    PAS.store(s.pas, Ordering::Relaxed);
                    if derniere.elapsed() > Duration::from_millis(400) {
                        prendre_vue(&s);
                        derniere = Instant::now();
                    }
                }
                Err(e) => break Err(e),
            }
        };
        DERNIERE_VUE.store(u64::MAX, Ordering::Relaxed);
        prendre_vue(&s);
        if !s.sortie.is_empty() {
            let t = s.sortie.iter().map(|v| v.to_string()).collect::<Vec<_>>().join(",");
            for c in format!("\nsorties : {}\n", t).chars() {
                ecrire_car(c as u128);
            }
        }
        let mut code = 0;
        let f = match r {
            Ok(()) => "le programme est fini".to_string(),
            Err(e) => {
                for c in format!("\nerreur : {}\n", e).chars() {
                    ecrire_car(c as u128);
                }
                code = 1;
                "le programme s'est arrêté sur une erreur".to_string()
            }
        };
        ATTEND.store(false, Ordering::Relaxed);
        avec(|e| e.fini = Some(f));
        FINI.store(true, Ordering::Relaxed);
        rafraichir();
        // la vitrine (et la toile, s'il y en a une) restent jusqu'à leur fermeture
        while !FERMEE.load(Ordering::Relaxed) {
            std::thread::sleep(Duration::from_millis(50));
        }
        code
    }
}
