// La traduction directe de Lugus en x86-64 (le premier pas : 0.5zv).
//
// Les mots du programme sont traduits une fois, au lancement, en instructions du processeur du PC, posées dans une
// mémoire exécutable. Chaque demi-instruction de Lugus devient un morceau de code x86-64 qui lit et écrit les registres
// de la machine (Spu128.r, z, c, pas) à leur place, en mémoire : la machine reste la même, seule la manière de
// l'avancer change. Les accès à la mémoire de Lugus passent par natif_lire et natif_ecrire (les pages, le cache, les
// cubes sur disque : le même chemin que Lugus).
//
// Ce qui est traduit : à la largeur 64, les opérations entières du chemin court de Lugus (ADD, ADDI, SUB, CMP, MUL,
// AND, OR, XOR, les décalages, MOVI, ETG), la division et le reste sans signe ; les mêmes (sauf ETG et la division)
// sur tout le mot de 128 bits (0.6j) ; les constantes LDI et LDIH ;
// les flottants quaternaires (addition, soustraction, produit, quotient, racine, comparaisons, conversions depuis les
// entiers), par un appel direct à natif_flot, le format en constante ; à la largeur 128 : MOV, les lectures et écritures de la mémoire et de la
// pile, les sauts, CALL et RET. Tout le reste (les flottants, les divisions, les services, l'arrêt…) est rejoué par
// Lugus lui-même, une instruction, puis le code traduit reprend. Les deux donnent donc toujours le même résultat : on le
// vérifie (tests/test_natif128.py) en comparant les sorties, le texte, les registres et le compte des instructions.
//
// Les registres de x86-64 : rbx porte l'adresse de la machine ; r12 le compte des instructions (0.6j) ; rax, rcx, rdx, rsi, rdi, r8, r9 servent de brouillon.
// Les appels suivent la convention System V (extern "sysv64"), la même sous Windows et sous Linux.
use super::spu128::{natif_ecrire, natif_flot_pour, natif_lire, natif_rejouer, places_natif, Spu128};

const M120_HAUT: u64 = (1u64 << 56) - 1;

struct Asm {
    o: Vec<u8>,
    // (place du rel32 à corriger, demi-instruction visée)
    sauts: Vec<(usize, usize)>,
    // (place du rel32, étiquette : 0 la sortie « rejouer », 1 la sortie « continuer »)
    sorties: Vec<(usize, u8)>,
    // la place du compte des instructions dans la machine (Spu128.pas)
    pas: usize,
    // la place des registres de Lugus dans la machine (Spu128.r)
    or: usize,
    // 0.6k : le registre du processeur qui porte la moitié basse de chaque registre de Lugus (NUL : en mémoire)
    carte: [u8; 16],
}

const NUL: u8 = 0xFF;
// Les registres de Lugus gardés dans ceux du processeur (0.6k) : les plus utilisés par les programmes compilés (r1 et
// r2 les calculs, r14 la pile, r13 le cadre, r9 et r10). Seule la moitié basse y vit ; la haute reste en mémoire.
// rbp, r13, r14, r15 survivent aux appels ; r10 et r11 non, mais chaque appel range et reprend tout de toute façon.
const CARTE: [(usize, u8); 6] = [(1, 13), (2, 14), (14, 15), (13, 5), (9, 10), (10, 11)];

const RAX: u8 = 0;
const RCX: u8 = 1;
const RDX: u8 = 2;
const RSI: u8 = 6;
const R8: u8 = 8;
const R9: u8 = 9;
const R12: u8 = 12;

impl Asm {
    fn b(&mut self, x: &[u8]) {
        self.o.extend_from_slice(x);
    }
    fn d32(&mut self, v: u32) {
        self.o.extend_from_slice(&v.to_le_bytes());
    }
    /// mov reg, [rbx + d]
    fn charger(&mut self, reg: u8, d: usize) {
        if let Some(m) = self.garde(d) {
            if m != reg {
                self.mov(reg, m);
            }
            return;
        }
        self.charger_mem(reg, d);
    }
    /// mov [rbx + d], reg
    fn ranger(&mut self, d: usize, reg: u8) {
        if let Some(m) = self.garde(d) {
            if m != reg {
                self.mov(m, reg);
            }
            return;
        }
        self.ranger_mem(d, reg);
    }
    /// mov qword [rbx + d], 0 (ou mov r32, 0 si la place est gardée : ni l'un ni l'autre ne touche aux drapeaux)
    fn zero(&mut self, d: usize) {
        if let Some(m) = self.garde(d) {
            if m >= 8 {
                self.b(&[0x41]);
            }
            self.b(&[0xB8 + (m & 7)]);
            self.d32(0);
            return;
        }
        self.b(&[0x48, 0xC7, 0x83]);
        self.d32(d as u32);
        self.d32(0);
    }
    /// add qword [rbx + d], 1, ou add m, 1 si la place est gardée (pose la retenue pour un adc qui suit)
    fn plus_un(&mut self, d: usize) {
        if let Some(m) = self.garde(d) {
            self.b(&[0x48 | (m >> 3), 0x83, 0xC0 | (m & 7), 1]);
            return;
        }
        self.b(&[0x48, 0x83, 0x83]);
        self.d32(d as u32);
        self.b(&[1]);
    }
    /// le registre du processeur qui garde la place d (la moitié basse d'un registre de Lugus), s'il y en a un
    fn garde(&self, d: usize) -> Option<u8> {
        if d >= self.or && d < self.or + 256 && (d - self.or) % 16 == 0 {
            let m = self.carte[(d - self.or) / 16];
            if m != NUL {
                return Some(m);
            }
        }
        None
    }
    /// mov dst, src (64 bits)
    fn mov(&mut self, dst: u8, src: u8) {
        self.b(&[0x48 | ((src >> 3) << 2) | (dst >> 3), 0x89, 0xC0 | ((src & 7) << 3) | (dst & 7)]);
    }
    fn charger_mem(&mut self, reg: u8, d: usize) {
        self.b(&[0x48 | ((reg >> 3) << 2), 0x8B, 0x80 | ((reg & 7) << 3) | 3]);
        self.d32(d as u32);
    }
    fn ranger_mem(&mut self, d: usize, reg: u8) {
        self.b(&[0x48 | ((reg >> 3) << 2), 0x89, 0x80 | ((reg & 7) << 3) | 3]);
        self.d32(d as u32);
    }
    /// les registres gardés retournent dans la machine (avant un appel à Lugus ou une sortie)
    fn deposer(&mut self) {
        for &(k, m) in CARTE.iter() {
            let d = self.or + 16 * k;
            self.ranger_mem(d, m);
        }
    }
    /// et reviennent de la machine (à l'entrée, après un appel : Lugus a pu les changer)
    fn reprendre(&mut self) {
        for &(k, m) in CARTE.iter() {
            let d = self.or + 16 * k;
            self.charger_mem(m, d);
        }
    }
    /// mov byte [rbx + d], v
    fn octet(&mut self, d: usize, v: u8) {
        self.b(&[0xC6, 0x83]);
        self.d32(d as u32);
        self.b(&[v]);
    }
    /// setcc byte [rbx + d] (cc : 0x92 setc, 0x94 setz)
    fn poser_drapeau(&mut self, cc: u8, d: usize) {
        self.b(&[0x0F, cc, 0x83]);
        self.d32(d as u32);
    }
    /// le compte des instructions vit dans r12 tant qu'on est dans le code traduit (0.6j) : lea r12, [r12 + 1], qui ne
    /// touche pas aux drapeaux du processeur. En mémoire, chaque instruction attendait l'écriture de la précédente.
    fn compter(&mut self, _d: usize) {
        self.b(&[0x4D, 0x8D, 0x64, 0x24, 0x01]);
    }
    /// mov reg, imm64
    fn imm64(&mut self, reg: u8, v: u64) {
        self.b(&[0x48 | (reg >> 3), 0xB8 + (reg & 7)]);
        self.o.extend_from_slice(&v.to_le_bytes());
    }
    /// jmp vers la demi-instruction p (corrigé à la fin)
    fn jmp_pc(&mut self, p: usize) {
        self.b(&[0xE9]);
        self.sauts.push((self.o.len(), p));
        self.d32(0);
    }
    /// jcc vers la demi-instruction p (cc : 0x84 je, 0x85 jne)
    fn jcc_pc(&mut self, cc: u8, p: usize) {
        self.b(&[0x0F, cc]);
        self.sauts.push((self.o.len(), p));
        self.d32(0);
    }
    fn jcc_sortie(&mut self, cc: u8, k: u8) {
        self.b(&[0x0F, cc]);
        self.sorties.push((self.o.len(), k));
        self.d32(0);
    }
    fn jmp_sortie(&mut self, k: u8) {
        self.b(&[0xE9]);
        self.sorties.push((self.o.len(), k));
        self.d32(0);
    }
    /// Le début commun d'un accès rapide (0.6j) : l'adresse est en rsi:rdx. Si elle est courte et que sa page est
    /// gardée (natif_cache, la case (adresse >> 16) & 63), rax reçoit l'adresse du mot ; sinon on saute au chemin de
    /// Lugus. rdi sert de brouillon. Rend les deux places de saut à corriger.
    fn mot_rapide(&mut self, cache: usize) -> [usize; 2] {
        self.b(&[0x48, 0x85, 0xD2]); // test rdx, rdx
        self.b(&[0x0F, 0x85]); // jnz : adresse longue
        let s1 = self.o.len();
        self.d32(0);
        self.b(&[0x48, 0x89, 0xF0, 0x48, 0xC1, 0xE8, 0x10]); // mov rax, rsi ; shr rax, 16
        self.b(&[0x89, 0xC7, 0x83, 0xE7, 0x3F, 0xC1, 0xE7, 0x04]); // mov edi, eax ; and edi, 63 ; shl edi, 4
        self.b(&[0x48, 0x3B, 0x84, 0x3B]); // cmp rax, [rbx + rdi + clé]
        self.d32(cache as u32);
        self.b(&[0x0F, 0x85]); // jne : une autre page
        let s2 = self.o.len();
        self.d32(0);
        self.b(&[0x0F, 0xB7, 0xC6, 0xC1, 0xE0, 0x04]); // movzx eax, si ; shl eax, 4
        self.b(&[0x48, 0x03, 0x84, 0x3B]); // add rax, [rbx + rdi + premier mot]
        self.d32((cache + 8) as u32);
        [s1, s2]
    }
    /// corrige un saut court posé par mot_rapide (ou un jmp) pour qu'il arrive ici
    fn ici(&mut self, place: usize) {
        let rel = (self.o.len() - (place + 4)) as u32;
        self.o[place..place + 4].copy_from_slice(&rel.to_le_bytes());
    }
    /// lire le mot d'adresse rsi:rdx dans r8:r9 : dans la page gardée s'il y est, sinon par natif_lire (qui la retient)
    fn lire_rapide(&mut self, cache: usize, lire: u64, tampon: usize) {
        let [s1, s2] = self.mot_rapide(cache);
        self.b(&[0x4C, 0x8B, 0x00, 0x4C, 0x8B, 0x48, 0x08]); // mov r8, [rax] ; mov r9, [rax + 8]
        self.b(&[0xE9]);
        let fin = self.o.len();
        self.d32(0);
        self.ici(s1);
        self.ici(s2);
        self.b(&[0x48, 0x89, 0xDF]); // mov rdi, rbx
        self.appeler(lire);
        self.charger(R8, tampon);
        self.charger(R9, tampon + 8);
        self.ici(fin);
    }
    /// écrire rcx:r8 à l'adresse rsi:rdx (gardées) : dans la page gardée, sinon par natif_ecrire ; refusée (un mot
    /// d'ADN) : rien n'a changé, on sort pour que Lugus rejoue l'instruction p et dise l'erreur
    fn ecrire_rapide(&mut self, cache: usize, ecrire: u64, p: usize) {
        let [s1, s2] = self.mot_rapide(cache);
        self.b(&[0x48, 0x89, 0x08, 0x4C, 0x89, 0x40, 0x08]); // mov [rax], rcx ; mov [rax + 8], r8
        self.b(&[0xE9]);
        let fin = self.o.len();
        self.d32(0);
        self.ici(s1);
        self.ici(s2);
        // garder l'adresse dans la pile : push rsi ; push rdx (l'alignement revient à 16)
        self.b(&[0x56, 0x52]);
        self.b(&[0x48, 0x89, 0xDF]); // mov rdi, rbx
        self.appeler(ecrire);
        self.b(&[0x5A, 0x5E]); // pop rdx ; pop rsi
        self.b(&[0x48, 0x85, 0xC0]); // test rax, rax
        self.b(&[0x0F, 0x84, 0x0A, 0x00, 0x00, 0x00]); // je +10 (écrite)
        self.b(&[0xB8]); // mov eax, p
        self.d32(p as u32);
        self.jmp_sortie(0);
        self.ici(fin);
    }
    /// appeler une fonction de Lugus (son adresse dans rax : mov rax, imm64 ; call rax) : le compte des instructions
    /// est rendu à la machine avant l'appel et repris après (la fonction peut le lire ou l'avancer)
    fn appeler(&mut self, f: u64) {
        let d = self.pas;
        self.ranger(d, R12);
        self.deposer();
        self.imm64(RAX, f);
        self.b(&[0xFF, 0xD0]);
        self.reprendre();
        self.charger(R12, d);
    }
}

/// La mémoire exécutable où vit le code traduit.
struct Executable {
    p: *mut u8,
    taille: usize,
}

#[cfg(unix)]
extern "C" {
    fn mmap(a: *mut u8, l: usize, prot: i32, flags: i32, fd: i32, off: i64) -> *mut u8;
    fn mprotect(a: *mut u8, l: usize, prot: i32) -> i32;
    fn munmap(a: *mut u8, l: usize) -> i32;
}
#[cfg(windows)]
#[link(name = "kernel32")]
extern "system" {
    fn VirtualAlloc(a: *mut u8, l: usize, t: u32, p: u32) -> *mut u8;
    fn VirtualProtect(a: *mut u8, l: usize, p: u32, ancien: *mut u32) -> i32;
    fn VirtualFree(a: *mut u8, l: usize, t: u32) -> i32;
}

impl Executable {
    fn nouveau(code: &[u8]) -> Option<Executable> {
        let taille = (code.len() + 4095) & !4095;
        unsafe {
            #[cfg(unix)]
            let p = {
                let p = mmap(std::ptr::null_mut(), taille, 3, 0x22, -1, 0); // lire + écrire, privé et anonyme
                if p as isize == -1 {
                    return None;
                }
                std::ptr::copy_nonoverlapping(code.as_ptr(), p, code.len());
                if mprotect(p, taille, 5) != 0 {
                    // lire + exécuter
                    return None;
                }
                p
            };
            #[cfg(windows)]
            let p = {
                let p = VirtualAlloc(std::ptr::null_mut(), taille, 0x3000, 0x04); // réservé et engagé, lire + écrire
                if p.is_null() {
                    return None;
                }
                std::ptr::copy_nonoverlapping(code.as_ptr(), p, code.len());
                let mut ancien = 0u32;
                if VirtualProtect(p, taille, 0x20, &mut ancien) == 0 {
                    // lire + exécuter
                    return None;
                }
                p
            };
            Some(Executable { p, taille })
        }
    }
}

impl Drop for Executable {
    fn drop(&mut self) {
        unsafe {
            #[cfg(unix)]
            munmap(self.p, self.taille);
            #[cfg(windows)]
            {
                let _ = self.taille;
                VirtualFree(self.p, 0, 0x8000);
            }
        }
    }
}

/// Le programme traduit : le code, et pour chaque demi-instruction l'adresse de son morceau (ou 0 : rejouée par Lugus).
pub struct Traduction {
    _code: Executable,
    _table: Vec<u64>,
    table_p: *const u64,
    entree: extern "sysv64" fn(*mut Spu128, u64) -> u64,
    pub n: usize,
    /// combien de demi-instructions sont traduites (le reste est rejoué)
    pub traduites: usize,
}

/// une demi-instruction du programme (les mots de Lugus portent deux demi-instructions : la haute d'abord)
fn demi(mots: &[u128], p: usize) -> u64 {
    let w = mots[p >> 1];
    if p & 1 == 0 { (w >> 64) as u64 } else { w as u64 }
}

/// Traduit les mots du programme (le code, au début de l'étage 0). None si la mémoire exécutable est refusée.
pub fn traduire(mots: &[u128]) -> Option<Traduction> {
    // VTX_PROFIL : chaque instruction non traduite ressort du code traduit, pour être comptée
    let profil = std::env::var("VTX_PROFIL").is_ok();
    let rejouer = natif_rejouer as *const () as usize as u64;
    let [or, opc, oz, oc, opas, otampon, ocache] = places_natif();
    let reg = |i: usize| or + 16 * i;
    let n = mots.len() * 2;
    let mut carte = [NUL; 16];
    for &(k, m) in CARTE.iter() {
        carte[k] = m;
    }
    let mut a = Asm { o: Vec::with_capacity(n * 40), sauts: Vec::new(), sorties: Vec::new(), pas: opas, or, carte };
    // l'entrée : push rbx, rbp, r12, r13, r14, r15, et rax pour que la pile reste alignée sur 16 pour les appels ;
    // mov rbx, rdi ; les registres gardés ; r12 = le compte des instructions ; jmp rsi
    a.b(&[0x53, 0x55, 0x41, 0x54, 0x41, 0x55, 0x41, 0x56, 0x41, 0x57, 0x50, 0x48, 0x89, 0xFB]);
    a.reprendre();
    a.charger(R12, opas);
    a.b(&[0xFF, 0xE6]);
    let mut debuts = vec![0usize; n + 1];
    let mut traduit = vec![false; n];
    let lire = natif_lire as *const () as usize as u64;
    let ecrire = natif_ecrire as *const () as usize as u64;
    for p in 0..n {
        debuts[p] = a.o.len();
        let h = demi(mots, p);
        let op = (h >> 48) as u16;
        let d = ((h >> 44) & 15) as usize;
        let s = ((h >> 40) & 15) as usize;
        let t = ((h >> 36) & 15) as usize;
        let wl = ((h >> 32) & 15) as u32;
        let imm = (h & 0xFFFF_FFFF) as u32;
        let cible = imm as usize;
        let mut ok = true;
        // les drapeaux que pose celle-ci sont morts (0.6k) : en suivant le seul chemin qui part d'elle, on trouve une
        // instruction qui pose z et c sans les lire avant toute instruction qui les lit, qui peut sortir du code
        // traduit ou appeler Lugus. On traverse MOV et ETG (ils ne touchent ni aux drapeaux, ni à la mémoire) et les
        // sauts sans condition. Elle n'a pas à les écrire (des écritures en mémoire de moins ; un saut qui arrive
        // ailleurs sur ce chemin n'y change rien : les drapeaux y sont morts aussi).
        let suivante_pose = {
            let pose = |q: usize, op2: u16, wl2: u32| -> bool {
                (wl2 == 1 && matches!(op2, 0x01 | 0x06 | 0x02 | 0x07 | 0x0E | 0x0F | 0x03 | 0x14 | 0x15 | 0x16 | 0x08 | 0x09
                    | 0x17 | 0x18 | 0x19 | 0x0C | 0x0D))
                    || (wl2 == 0 && matches!(op2, 0x20 | 0x25 | 0x01 | 0x06 | 0x02 | 0x07 | 0x0E | 0x0F | 0x03 | 0x14 | 0x15
                        | 0x16 | 0x08 | 0x09 | 0x17 | 0x18 | 0x19))
                    || (wl2 <= 2 && matches!(op2, 0x0A | 0x2B) && q + 2 <= n)
            };
            let mut q = p + 1;
            let mut vus = 0;
            loop {
                if q >= n || vus > 16 {
                    break false;
                }
                let h2 = demi(mots, q);
                let (op2, wl2, c2) = ((h2 >> 48) as u16, ((h2 >> 32) & 15) as u32, (h2 & 0xFFFF_FFFF) as usize);
                if pose(q, op2, wl2) {
                    break true;
                }
                if (wl2 == 0 && op2 == 0x0B) || (wl2 == 1 && op2 == 0x1F) {
                    q += 1;
                } else if op2 == 0x30 && wl2 <= 2 && c2 < n {
                    q = c2;
                } else {
                    break false;
                }
                vus += 1;
            }
        };
        // l'adresse rsi:rdx = r[base] + imm (signé), masquée à 120 bits si masque
        let adresse = |a: &mut Asm, base: usize, masque: bool| {
            a.charger(RSI, reg(base));
            a.charger(RDX, reg(base) + 8);
            a.b(&[0x48, 0x81, 0xC6]); // add rsi, imm32
            a.d32(imm);
            a.b(&[0x48, 0x83, 0xD2, if (imm as i32) < 0 { 0xFF } else { 0x00 }]); // adc rdx, 0 ou -1
            if masque {
                a.imm64(RCX, M120_HAUT);
                a.b(&[0x48, 0x21, 0xCA]); // and rdx, rcx
            }
        };
        match (wl, op) {
            (1, 0x01 | 0x06 | 0x02 | 0x07 | 0x0E | 0x0F | 0x03 | 0x14 | 0x15 | 0x16 | 0x08 | 0x09 | 0x17 | 0x18 | 0x19) => {
                a.charger(RAX, reg(s));
                if matches!(op, 0x01 | 0x02 | 0x0E | 0x03 | 0x14 | 0x15 | 0x16 | 0x08 | 0x09 | 0x17) {
                    a.charger(RCX, reg(t));
                }
                let mut retenue = false;
                match op {
                    0x01 => { a.b(&[0x48, 0x01, 0xC8]); retenue = true; }
                    0x06 => { a.b(&[0x48, 0x05]); a.d32(imm); retenue = true; }
                    0x02 | 0x0E => { a.b(&[0x48, 0x29, 0xC8]); retenue = true; }
                    0x07 | 0x0F => { a.b(&[0x48, 0x2D]); a.d32(imm); retenue = true; }
                    0x03 => a.b(&[0x48, 0x0F, 0xAF, 0xC1]),
                    0x14 => a.b(&[0x48, 0x21, 0xC8]),
                    0x15 => a.b(&[0x48, 0x09, 0xC8]),
                    0x16 => a.b(&[0x48, 0x31, 0xC8]),
                    0x08 => a.b(&[0x48, 0xD3, 0xE0]),
                    0x09 => a.b(&[0x48, 0xD3, 0xE8]),
                    0x17 => a.b(&[0x48, 0xD3, 0xF8]),
                    0x18 => { a.b(&[0x48, 0xC7, 0xC0]); a.d32(imm); }
                    _ => { a.b(&[0xB8]); a.d32(imm); } // 0x19 : mov eax, imm32 (les 32 bits hauts à zéro)
                }
                if !suivante_pose {
                    if retenue {
                        // l'addition ou la soustraction a posé la retenue et le zéro du processeur : on les copie
                        a.poser_drapeau(0x92, oc);
                    } else {
                        a.octet(oc, 0);
                        a.b(&[0x48, 0x85, 0xC0]); // test rax, rax (z ; la retenue du processeur à zéro, comme c)
                    }
                    a.poser_drapeau(0x94, oz);
                }
                let ecrit = !matches!(op, 0x0E | 0x0F);
                if ecrit && d != 0 {
                    a.ranger(reg(d), RAX);
                    a.zero(reg(d) + 8);
                }
                a.compter(opas);
                // la suivante est un saut selon z ou c (0.6j) : les drapeaux du processeur disent encore z et c (ni mov,
                // ni lea, ni setcc ne les changent) ; on saute tout de suite, sans relire la mémoire. Le saut garde son
                // propre morceau, à sa place, pour qui arrive sur lui d'ailleurs.
                if !suivante_pose && p + 1 < n {
                    let h2 = demi(mots, p + 1);
                    let (op2, wl2, cible2) = ((h2 >> 48) as u16, ((h2 >> 32) & 15) as u32, (h2 & 0xFFFF_FFFF) as usize);
                    if wl2 <= 2 && matches!(op2, 0x31 | 0x32 | 0x35 | 0x36) && cible2 < n {
                        a.compter(opas);
                        a.jcc_pc(match op2 { 0x31 => 0x84, 0x32 => 0x85, 0x35 => 0x82, _ => 0x83 }, cible2);
                        a.jmp_pc(p + 2);
                    }
                }
            }
            (0, 0x01 | 0x06 | 0x02 | 0x07 | 0x0E | 0x0F | 0x03 | 0x14 | 0x15 | 0x16 | 0x08 | 0x09 | 0x17 | 0x18 | 0x19) => {
                // les mêmes opérations sur tout le mot de Lugus, 128 bits (0.6j) : S dans rax:rdx, T dans rcx:r8
                let immediat = matches!(op, 0x06 | 0x07 | 0x0F);
                let decalage = matches!(op, 0x08 | 0x09 | 0x17);
                if !matches!(op, 0x18 | 0x19) {
                    a.charger(RAX, reg(s));
                    a.charger(RDX, reg(s) + 8);
                }
                if immediat {
                    // l'immédiat, avec son signe étendu à 128 bits
                    a.b(&[0x48, 0xC7, 0xC1]); // mov rcx, imm32 (signé)
                    a.d32(imm);
                    if (imm as i32) < 0 {
                        a.b(&[0x49, 0xC7, 0xC0, 0xFF, 0xFF, 0xFF, 0xFF]); // mov r8, -1
                    } else {
                        a.b(&[0x45, 0x31, 0xC0]); // xor r8d, r8d
                    }
                } else if decalage {
                    a.charger(RCX, reg(t));
                    a.b(&[0x83, 0xE1, 0x7F]); // and ecx, 127
                } else if !matches!(op, 0x18 | 0x19) {
                    a.charger(RCX, reg(t));
                    a.charger(R8, reg(t) + 8);
                }
                let mut retenue = false;
                match op {
                    0x01 | 0x06 => { a.b(&[0x48, 0x01, 0xC8, 0x4C, 0x11, 0xC2]); retenue = true; } // add rax, rcx ; adc rdx, r8
                    0x02 | 0x07 | 0x0E | 0x0F => { a.b(&[0x48, 0x29, 0xC8, 0x4C, 0x19, 0xC2]); retenue = true; } // sub ; sbb
                    0x14 => a.b(&[0x48, 0x21, 0xC8, 0x4C, 0x21, 0xC2]),
                    0x15 => a.b(&[0x48, 0x09, 0xC8, 0x4C, 0x09, 0xC2]),
                    0x16 => a.b(&[0x48, 0x31, 0xC8, 0x4C, 0x31, 0xC2]),
                    0x03 => {
                        // le bas du produit : bas × bas sur 128 bits, plus les deux produits croisés dans le haut
                        a.b(&[0x48, 0x89, 0xD6]); // mov rsi, rdx
                        a.b(&[0x48, 0x0F, 0xAF, 0xF1]); // imul rsi, rcx
                        a.b(&[0x4C, 0x0F, 0xAF, 0xC0]); // imul r8, rax
                        a.b(&[0x4C, 0x01, 0xC6]); // add rsi, r8
                        a.b(&[0x48, 0xF7, 0xE1]); // mul rcx
                        a.b(&[0x48, 0x01, 0xF2]); // add rdx, rsi
                    }
                    0x08 => {
                        // à gauche de 0 à 127 : 64 ou plus, le bas passe en haut d'abord
                        a.b(&[0xF6, 0xC1, 0x40, 0x74, 0x05]); // test cl, 64 ; jz +5
                        a.b(&[0x48, 0x89, 0xC2, 0x31, 0xC0]); // mov rdx, rax ; xor eax, eax
                        a.b(&[0x48, 0x0F, 0xA5, 0xC2]); // shld rdx, rax, cl
                        a.b(&[0x48, 0xD3, 0xE0]); // shl rax, cl
                    }
                    0x09 => {
                        a.b(&[0xF6, 0xC1, 0x40, 0x74, 0x05]); // test cl, 64 ; jz +5
                        a.b(&[0x48, 0x89, 0xD0, 0x31, 0xD2]); // mov rax, rdx ; xor edx, edx
                        a.b(&[0x48, 0x0F, 0xAD, 0xD0]); // shrd rax, rdx, cl
                        a.b(&[0x48, 0xD3, 0xEA]); // shr rdx, cl
                    }
                    0x17 => {
                        a.b(&[0xF6, 0xC1, 0x40, 0x74, 0x07]); // test cl, 64 ; jz +7
                        a.b(&[0x48, 0x89, 0xD0, 0x48, 0xC1, 0xFA, 0x3F]); // mov rax, rdx ; sar rdx, 63
                        a.b(&[0x48, 0x0F, 0xAD, 0xD0]); // shrd rax, rdx, cl
                        a.b(&[0x48, 0xD3, 0xFA]); // sar rdx, cl
                    }
                    0x18 => {
                        a.b(&[0x48, 0xC7, 0xC0]); // mov rax, imm32 (signé)
                        a.d32(imm);
                        if (imm as i32) < 0 {
                            a.b(&[0x48, 0xC7, 0xC2, 0xFF, 0xFF, 0xFF, 0xFF]); // mov rdx, -1
                        } else {
                            a.b(&[0x31, 0xD2]); // xor edx, edx
                        }
                    }
                    _ => { a.b(&[0xB8]); a.d32(imm); a.b(&[0x31, 0xD2]); } // 0x19 : mov eax, imm32 ; xor edx, edx
                }
                if !suivante_pose {
                    if retenue {
                        // la retenue du processeur, gardée dans dil (le calcul de z va l'effacer)
                        a.b(&[0x40, 0x0F, 0x92, 0xC7]); // setc dil
                        a.b(&[0x40, 0x88, 0xBB]); // mov [rbx + c], dil
                        a.d32(oc as u32);
                    } else {
                        a.octet(oc, 0);
                    }
                    a.b(&[0x48, 0x89, 0xC6, 0x48, 0x09, 0xD6]); // mov rsi, rax ; or rsi, rdx (z ; la retenue à zéro)
                    a.poser_drapeau(0x94, oz);
                }
                if !matches!(op, 0x0E | 0x0F) && d != 0 {
                    a.ranger(reg(d), RAX);
                    a.ranger(reg(d) + 8, RDX);
                }
                a.compter(opas);
                // la suivante est un saut selon z ou c : comme à 64 bits, on saute tout de suite
                if !suivante_pose && p + 1 < n {
                    let h2 = demi(mots, p + 1);
                    let (op2, wl2, cible2) = ((h2 >> 48) as u16, ((h2 >> 32) & 15) as u32, (h2 & 0xFFFF_FFFF) as usize);
                    if wl2 <= 2 && matches!(op2, 0x31 | 0x32 | 0x35 | 0x36) && cible2 < n {
                        a.compter(opas);
                        if retenue && matches!(op2, 0x35 | 0x36) {
                            a.b(&[0x40, 0xD0, 0xEF]); // shr dil, 1 : la retenue gardée revient dans celle du processeur
                        }
                        a.jcc_pc(match op2 { 0x31 => 0x84, 0x32 => 0x85, 0x35 => 0x82, _ => 0x83 }, cible2);
                        a.jmp_pc(p + 2);
                    }
                }
            }
            (1, 0x1F) => {
                // ETG : l'étage dans les deux bits hauts ; z et c ne changent pas
                if d != 0 {
                    a.charger(RAX, reg(s));
                    a.imm64(RCX, !(3u64 << 62));
                    a.b(&[0x48, 0x21, 0xC8]); // and rax, rcx
                    a.imm64(RCX, ((imm as u64) & 3) << 62);
                    a.b(&[0x48, 0x09, 0xC8]); // or rax, rcx
                    a.ranger(reg(d), RAX);
                    a.zero(reg(d) + 8);
                }
                a.compter(opas);
            }
            (1, 0x0C | 0x0D) => {
                // la division et le reste, sans signe ; par zéro : tout à un pour la division, le dividende pour le reste
                a.charger(RAX, reg(s));
                a.charger(RCX, reg(t));
                a.b(&[0x48, 0x85, 0xC9]); // test rcx, rcx
                if op == 0x0C {
                    a.b(&[0x74, 0x07]); // jz : diviseur nul
                    a.b(&[0x31, 0xD2, 0x48, 0xF7, 0xF1]); // xor edx, edx ; div rcx
                    a.b(&[0xEB, 0x07]); // jmp : fin
                    a.b(&[0x48, 0xC7, 0xC0, 0xFF, 0xFF, 0xFF, 0xFF]); // mov rax, -1
                } else {
                    a.b(&[0x74, 0x08]); // jz : diviseur nul, rax garde le dividende
                    a.b(&[0x31, 0xD2, 0x48, 0xF7, 0xF1]); // xor edx, edx ; div rcx
                    a.b(&[0x48, 0x89, 0xD0]); // mov rax, rdx
                }
                a.octet(oc, 0);
                a.b(&[0x48, 0x85, 0xC0]); // test rax, rax
                a.poser_drapeau(0x94, oz);
                if d != 0 {
                    a.ranger(reg(d), RAX);
                    a.zero(reg(d) + 8);
                }
                a.compter(opas);
            }
            (0 | 1 | 2, 0x0A | 0x2B) if p + 2 <= n => {
                // LDI et LDIH : la constante est la demi-instruction suivante (64 bits), qu'on saute
                let k = demi(mots, p + 1);
                if op == 0x0A {
                    if d != 0 {
                        a.imm64(RAX, k);
                        a.ranger(reg(d), RAX);
                        a.zero(reg(d) + 8);
                    }
                    a.octet(oz, (k == 0) as u8);
                } else {
                    // le haut du mot ; le bas reste (z : tout le mot est nul)
                    if d != 0 {
                        a.imm64(RAX, k);
                        a.ranger(reg(d) + 8, RAX);
                    }
                    if k != 0 {
                        a.octet(oz, 0);
                    } else {
                        a.charger(RAX, reg(d));
                        a.b(&[0x48, 0x85, 0xC0]); // test rax, rax
                        a.poser_drapeau(0x94, oz);
                    }
                }
                a.octet(oc, 0);
                a.compter(opas);
                a.jmp_pc(p + 2);
            }
            (0 | 1 | 2, 0x40..=0x49 | 0x5B | 0x5C | 0x5D) if natif_flot_pour(op, wl).is_some() => {
                // les flottants quaternaires : un appel direct à natif_flot (le format en constante)
                a.b(&[0x48, 0x89, 0xDF]); // mov rdi, rbx
                a.b(&[0xBE]); // mov esi, regs
                a.d32((d | s << 4 | t << 8 | ((imm & 3) as usize) << 12) as u32);
                a.appeler(natif_flot_pour(op, wl).unwrap());
                a.compter(opas);
            }
            (0, 0x0B) => {
                if d != 0 {
                    a.charger(RAX, reg(s));
                    a.charger(RCX, reg(s) + 8);
                    a.ranger(reg(d), RAX);
                    a.ranger(reg(d) + 8, RCX);
                }
                a.compter(opas);
            }
            (0 | 1 | 2, 0x30 | 0x31 | 0x32 | 0x35 | 0x36) if cible < n => {
                a.compter(opas);
                match op {
                    0x30 => a.jmp_pc(cible),
                    _ => {
                        let champ = if op == 0x31 || op == 0x32 { oz } else { oc };
                        a.b(&[0x80, 0xBB]); // cmp byte [rbx + champ], 0
                        a.d32(champ as u32);
                        a.b(&[0]);
                        // 0x31 saute si z, 0x32 si non z, 0x35 si c, 0x36 si non c
                        a.jcc_pc(if op == 0x31 || op == 0x35 { 0x85 } else { 0x84 }, cible);
                    }
                }
            }
            (0, 0x20 | 0x25 | 0x28) => {
                match op {
                    0x20 => adresse(&mut a, s, false),
                    0x25 => adresse(&mut a, 13, true),
                    _ => {
                        a.charger(RSI, reg(14));
                        a.charger(RDX, reg(14) + 8);
                    }
                }
                // la valeur dans r8:r9
                a.lire_rapide(ocache, lire, otampon);
                if op == 0x28 {
                    // r14 = (r14 + 1) & M120
                    a.plus_un(reg(14));
                    a.b(&[0x48, 0x83, 0x93]);
                    a.d32((reg(14) + 8) as u32);
                    a.b(&[0]);
                    a.imm64(RCX, M120_HAUT);
                    a.b(&[0x48, 0x21, 0x8B]); // and [rbx + d], rcx
                    a.d32((reg(14) + 8) as u32);
                } else if !suivante_pose {
                    a.octet(oc, 0);
                    a.b(&[0x4C, 0x89, 0xC0, 0x4C, 0x09, 0xC8]); // mov rax, r8 ; or rax, r9
                    a.poser_drapeau(0x94, oz);
                }
                if d != 0 {
                    a.ranger(reg(d), R8);
                    a.ranger(reg(d) + 8, R9);
                }
                a.compter(opas);
            }
            (0, 0x21 | 0x26 | 0x27) | (0 | 1 | 2, 0x33) if op != 0x33 || cible < n => {
                // la valeur en rcx:r8, l'adresse en rsi:rdx ; pour la pile, r14 - 1 calculé ici, posé après l'écriture
                match op {
                    0x21 => {
                        adresse(&mut a, d, false);
                        a.charger(RCX, reg(s));
                        a.charger(R8, reg(s) + 8);
                    }
                    0x26 => {
                        adresse(&mut a, 13, true);
                        a.charger(RCX, reg(d));
                        a.charger(R8, reg(d) + 8);
                    }
                    _ => {
                        a.charger(RSI, reg(14));
                        a.charger(RDX, reg(14) + 8);
                        a.b(&[0x48, 0x83, 0xEE, 0x01]); // sub rsi, 1
                        a.b(&[0x48, 0x83, 0xDA, 0x00]); // sbb rdx, 0
                        a.imm64(RCX, M120_HAUT);
                        a.b(&[0x48, 0x21, 0xCA]); // and rdx, rcx
                        if op == 0x27 {
                            a.charger(RCX, reg(s));
                            a.charger(R8, reg(s) + 8);
                        } else {
                            // CALL : on empile l'adresse de retour
                            a.b(&[0x48, 0xC7, 0xC1]);
                            a.d32((p + 1) as u32);
                            a.b(&[0x45, 0x31, 0xC0]); // xor r8d, r8d
                        }
                    }
                }
                a.ecrire_rapide(ocache, ecrire, p);
                if op == 0x27 || op == 0x33 {
                    a.ranger(reg(14), RSI);
                    a.ranger(reg(14) + 8, RDX);
                }
                a.compter(opas);
                if op == 0x33 {
                    a.jmp_pc(cible);
                }
            }
            (0 | 1 | 2, 0x34) => {
                a.charger(RSI, reg(14));
                a.charger(RDX, reg(14) + 8);
                a.lire_rapide(ocache, lire, otampon);
                a.b(&[0x4C, 0x89, 0xC0, 0x4C, 0x89, 0xCA]); // mov rax, r8 ; mov rdx, r9
                // r14 = (r14 + 1) & M120
                a.plus_un(reg(14));
                a.b(&[0x48, 0x83, 0x93]);
                a.d32((reg(14) + 8) as u32);
                a.b(&[0]);
                a.imm64(RCX, M120_HAUT);
                a.b(&[0x48, 0x21, 0x8B]);
                a.d32((reg(14) + 8) as u32);
                a.compter(opas);
                // le retour : masqué à 120 bits ; dans le programme traduit, on y saute par la table
                a.b(&[0x48, 0x21, 0xCA]); // and rdx, rcx (rcx porte encore le masque)
                a.b(&[0x48, 0x85, 0xD2]); // test rdx, rdx
                a.jcc_sortie(0x85, 1);
                a.b(&[0x48, 0x3D]); // cmp rax, n
                a.d32(n as u32);
                a.jcc_sortie(0x83, 1); // jae : hors du programme traduit
                a.imm64(RCX, 0); // l'adresse de la table, posée à la fin
                let place_table = a.o.len() - 8;
                a.b(&[0xFF, 0x24, 0xC1]); // jmp [rcx + rax*8]
                a.sauts.push((place_table, usize::MAX));
            }
            _ => ok = false,
        }
        if !ok && profil {
            a.o.truncate(debuts[p]);
            a.b(&[0xB8]);
            a.d32(p as u32);
            a.jmp_sortie(0);
        } else if !ok {
            // rejouée par Lugus, appelé d'ici (natif_rejouer) : on ne quitte le code traduit que si la machine est
            // allée ailleurs (1) ou sur une erreur (2)
            a.o.truncate(debuts[p]);
            a.b(&[0x48, 0x89, 0xDF]); // mov rdi, rbx
            a.b(&[0xBE]); // mov esi, p
            a.d32(p as u32);
            a.appeler(rejouer);
            a.b(&[0x85, 0xC0]); // test eax, eax
            a.b(&[0x74, 0x0E]); // jz : à la suite
            a.b(&[0x83, 0xF8, 0x01]); // cmp eax, 1
            a.jcc_sortie(0x84, 2);
            a.jmp_sortie(3);
        } else {
            traduit[p] = true;
        }
    }
    debuts[n] = a.o.len();
    // après la dernière : rejouer (Lugus dira ce qu'il y a là)
    a.b(&[0xB8]);
    a.d32(n as u32);
    a.jmp_sortie(0);
    // la sortie « rejouer » : eax = p ; pc = p ; rendre 1
    let sortie0 = a.o.len();
    a.ranger(opas, R12);
    a.deposer();
    a.ranger(opc, RAX);
    a.zero(opc + 8);
    a.b(&[0xB8, 1, 0, 0, 0]);
    a.b(&[0x59, 0x41, 0x5F, 0x41, 0x5E, 0x41, 0x5D, 0x41, 0x5C, 0x5D, 0x5B, 0xC3]); // pop rcx (l'alignement), r15 … rbx ; ret
    // la sortie « continuer » : rax:rdx = pc ; rendre 0
    let sortie1 = a.o.len();
    a.ranger(opas, R12);
    a.deposer();
    a.ranger(opc, RAX);
    a.ranger(opc + 8, RDX);
    a.b(&[0x31, 0xC0]);
    a.b(&[0x59, 0x41, 0x5F, 0x41, 0x5E, 0x41, 0x5D, 0x41, 0x5C, 0x5D, 0x5B, 0xC3]); // pop rcx (l'alignement), r15 … rbx ; ret
    // la sortie « ailleurs » : pc est déjà posé ; rendre 0
    let sortie2 = a.o.len();
    a.ranger(opas, R12);
    a.deposer();
    a.b(&[0x31, 0xC0]);
    a.b(&[0x59, 0x41, 0x5F, 0x41, 0x5E, 0x41, 0x5D, 0x41, 0x5C, 0x5D, 0x5B, 0xC3]); // pop rcx (l'alignement), r15 … rbx ; ret
    // la sortie « erreur » : rendre 2
    let sortie3 = a.o.len();
    a.ranger(opas, R12);
    a.deposer();
    a.b(&[0xB8, 2, 0, 0, 0]);
    a.b(&[0x59, 0x41, 0x5F, 0x41, 0x5E, 0x41, 0x5D, 0x41, 0x5C, 0x5D, 0x5B, 0xC3]); // pop rcx (l'alignement), r15 … rbx ; ret
    for &(place, k) in &a.sorties {
        let but = [sortie0, sortie1, sortie2, sortie3][k as usize];
        let rel = but as i64 - (place as i64 + 4);
        a.o[place..place + 4].copy_from_slice(&(rel as i32).to_le_bytes());
    }
    let sauts: Vec<(usize, usize)> = a.sauts.iter().filter(|x| x.1 != usize::MAX).copied().collect();
    for (place, p) in sauts {
        let rel = debuts[p] as i64 - (place as i64 + 4);
        a.o[place..place + 4].copy_from_slice(&(rel as i32).to_le_bytes());
    }
    let places_table: Vec<usize> = a.sauts.iter().filter(|x| x.1 == usize::MAX).map(|x| x.0).collect();
    // la table vit dans le tas de Rust : on la fait d'abord, puis on pose son adresse dans le code, puis on copie le code
    let mut table = vec![0u64; n];
    let tp = table.as_ptr() as u64;
    for pl in places_table {
        a.o[pl..pl + 8].copy_from_slice(&tp.to_le_bytes());
    }
    // VTX_VIDAGE=fichier : le code traduit écrit tel quel, et la place de chaque demi-instruction dans fichier.places
    if let Ok(f) = std::env::var("VTX_VIDAGE") {
        let _ = std::fs::write(&f, &a.o);
        let places: Vec<String> = debuts.iter().map(|x| x.to_string()).collect();
        let _ = std::fs::write(format!("{}.places", f), places.join("\n"));
    }
    let code = Executable::nouveau(&a.o)?;
    for p in 0..n {
        table[p] = code.p as u64 + debuts[p] as u64;
    }
    let entree: extern "sysv64" fn(*mut Spu128, u64) -> u64 = unsafe { std::mem::transmute(code.p) };
    let traduites = traduit.iter().filter(|&&x| x).count();
    let table_p = table.as_ptr();
    Some(Traduction { _code: code, _table: table, table_p, entree, n, traduites })
}

impl Traduction {
    /// Avance la machine jusqu'à son arrêt : le code traduit tant qu'il peut, Lugus pour le reste. Ni la limite
    /// d'instructions, ni la patrouille, ni l'arrêt demandé de l'atelier ne sont regardés ici : c'est le mode d'un
    /// .exe. (Un programme qui écrirait dans son propre code serait suivi par Lugus, pas par la traduction.)
    pub fn executer(&self, s: &mut Spu128) -> Result<(), String> {
        let sp: *mut Spu128 = s;
        // VTX_PROFIL : le compte des instructions rejouées par Lugus, par code et largeur (ce qu'il reste à traduire)
        let mut profil = if std::env::var("VTX_PROFIL").is_ok() { Some(std::collections::HashMap::new()) } else { None };
        while !s.arrete {
            let p = s.pc;
            if p < self.n as u128 {
                // Lugus a pu jouer entre-temps : le code traduit ne garde aucune page d'une entrée à l'autre
                s.natif_oublier();
                let r = (self.entree)(sp, unsafe { *self.table_p.add(p as usize) });
                if r == 2 {
                    return Err(s.natif_erreur.take().unwrap_or_else(|| "erreur dans le code traduit".to_string()));
                }
                if r == 1 {
                    if let Some(pr) = profil.as_mut() {
                        let h = s.demi_pub(s.pc);
                        *pr.entry(((h >> 48) as u16, ((h >> 32) & 15) as u8)).or_insert(0u64) += 1;
                    }
                    s.pas_unique()?;
                }
            } else {
                s.pas_unique()?;
            }
        }
        if let Some(pr) = profil {
            let mut v: Vec<_> = pr.into_iter().collect();
            v.sort_by(|a, b| b.1.cmp(&a.1));
            let total: u64 = v.iter().map(|x| x.1).sum();
            eprintln!("rejouées par Lugus : {} sur {} instructions", total, s.pas);
            for ((op, wl), n) in v.iter().take(14) {
                eprintln!("  code #{:02X} largeur {} : {}", op, wl, n);
            }
        }
        Ok(())
    }
}