// neutrons, CRC-8 (0x07) : un million de mots de 128 bits (xorshift64), la somme de leurs neutrons ; la table de deux octets
const N: u64 = 1000000;
fn main() {
    let mut t = [0u64; 256];
    for k in 0..256 { let mut c = k as u64; for _ in 0..8 { c = if c & 128 != 0 { ((c << 1) ^ 7) & 255 } else { (c << 1) & 255 }; } t[k] = c; }
    let mut t2 = vec![0u64; 65536];
    for y in 0..256usize { for x in 0..256usize { t2[x | (y << 8)] = t[(t[x] as usize) ^ y]; } }
    let (mut x, mut s) = (88172645463325252u64, 0u64);
    for _ in 0..N {
        x ^= x << 13; x ^= x >> 7; x ^= x << 17; let h = x;
        x ^= x << 13; x ^= x >> 7; x ^= x << 17; let b = x;
        let mut c = t2[(b & 65535) as usize];
        c = t2[(c ^ ((b >> 16) & 65535)) as usize]; c = t2[(c ^ ((b >> 32) & 65535)) as usize]; c = t2[(c ^ (b >> 48)) as usize];
        c = t2[(c ^ (h & 65535)) as usize]; c = t2[(c ^ ((h >> 16) & 65535)) as usize]; c = t2[(c ^ ((h >> 32) & 65535)) as usize];
        c = t2[(c ^ (h >> 48)) as usize];
        s = s.wrapping_add(c);
    }
    println!("{}", s);
}
