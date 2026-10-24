const N: usize = 5_000_000;
fn main() {
    let mut p = vec![0u32; N];
    for q in 2..N { p[q] = 1; }
    let mut i = 2;
    while i * i < N {
        if p[i] == 1 { let mut j = i * i; while j < N { p[j] = 0; j += i; } }
        i += 1;
    }
    let n: u32 = p[2..].iter().sum();
    println!("{}", n);
}
