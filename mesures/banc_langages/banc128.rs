fn fib(n: i128) -> i128 { if n < 2 { n } else { fib(n - 1) + fib(n - 2) } }
fn main() {
    let n: i128 = 2_000_000; let mut compte = 0i128;
    let mut crible = vec![0i128; n as usize];
    let mut i: i128 = 2;
    while i < n { if crible[i as usize] == 0 { compte += 1; let mut j = i * i; while j < n { crible[j as usize] = 1; j += i; } } i += 1; }
    println!("premiers : {}", compte);
    println!("fib(27) : {}", fib(std::hint::black_box(27)));
    let mut h: u128 = 7;
    let mut k: u128 = 0;
    while k < 3_000_000 { h = h.wrapping_mul(31).wrapping_add(k) ^ (((h as i128) >> 3) as u128); k += 1; }
    println!("brassage : {} {}", (h >> 64) as i64, h as i64);
}
