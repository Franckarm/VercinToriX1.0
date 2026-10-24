const M: usize = 524288;
fn main() {
    let (mut u, mut v) = (vec![0u8; M * 16], vec![0u8; M * 16]);
    let mut x: u32 = 2463534242;
    for i in 0..M {
        x ^= x << 13; x ^= x >> 17; x ^= x << 5;
        for q in 0..16 { u[i * 16 + q] = ((x >> (2 * q)) & 3) as u8; }
        x ^= x << 13; x ^= x >> 17; x ^= x << 5;
        for q in 0..16 { v[i * 16 + q] = ((x >> (2 * q)) & 3) as u8; }
    }
    let mut n: u32 = 0;
    for _ in 0..4 { for i in 0..M * 16 { n += (u[i] == v[i]) as u32; } }
    println!("{}", n);
}
