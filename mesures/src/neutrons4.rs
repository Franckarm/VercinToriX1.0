// neutrons quaternaires (CRC sur GF(4)) : un million de mots de 128 bits (xorshift64), la somme de leurs neutrons ; la table de deux octets
const N: u64 = 1000000;
fn m4(a: u64, b: u64) -> u64 { if a == 0 || b == 0 { return 0; } let mut l = (a - 1) + (b - 1); if l >= 3 { l -= 3; } l + 1 }
fn main() {
    let mut t = [0u64; 256];
    for k in 0..256u64 { let mut r = 0u64; for q in (0..4).rev() { let tq = ((k >> (2 * q)) & 3) ^ (r >> 6);
        r = (((r >> 4) & 3) << 6) | ((((r >> 2) & 3) ^ m4(tq, 1)) << 4) | (((r & 3) ^ m4(tq, 2)) << 2) | m4(tq, 1); } t[k as usize] = r; }
    let mut t2 = vec![0u64; 65536];
    for x in 0..256usize { for y in 0..256usize { t2[(x << 8) | y] = t[(t[x] as usize) ^ y] << 8; } }
    let (mut x, mut s) = (88172645463325252u64, 0u64);
    for _ in 0..N {
        x ^= x << 13; x ^= x >> 7; x ^= x << 17; let h = x;
        x ^= x << 13; x ^= x >> 7; x ^= x << 17; let b = x;
        let mut c = t2[(h >> 48) as usize];
        c = t2[(c ^ ((h >> 32) & 65535)) as usize]; c = t2[(c ^ ((h >> 16) & 65535)) as usize];
        c = t2[(c ^ (h & 65535)) as usize]; c = t2[(c ^ (b >> 48)) as usize];
        c = t2[(c ^ ((b >> 32) & 65535)) as usize]; c = t2[(c ^ ((b >> 16) & 65535)) as usize];
        c = t2[(c ^ (b & 65535)) as usize];
        s = s.wrapping_add(c >> 8);
    }
    println!("{}", s);
}
