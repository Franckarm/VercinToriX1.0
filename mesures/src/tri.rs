const N: usize = 500_000;
fn trier(a: &mut [u32], mut g: isize, mut d: isize) {
    while g < d {
        let p = a[((g + d) / 2) as usize];
        let (mut i, mut j) = (g, d);
        while i <= j {
            while a[i as usize] < p { i += 1; }
            while a[j as usize] > p { j -= 1; }
            if i <= j { a.swap(i as usize, j as usize); i += 1; j -= 1; }
        }
        if j - g < d - i { if g < j { trier(a, g, j); } g = i; } else { if i < d { trier(a, i, d); } d = j; }
    }
}
fn main() {
    let mut a = vec![0u32; N];
    let mut x: u32 = 2463534242;
    for v in a.iter_mut() { x ^= x << 13; x ^= x >> 17; x ^= x << 5; *v = x & 16777215; }
    trier(&mut a, 0, N as isize - 1);
    let mut s: u32 = 0;
    for &v in &a { s = s.wrapping_mul(31).wrapping_add(v); }
    println!("{}", s);
}
