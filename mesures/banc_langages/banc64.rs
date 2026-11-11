fn fib(n: u64) -> u64 { if n < 2 { n } else { fib(n - 1) + fib(n - 2) } }
fn main() {
    let n: u64 = 2_000_000; let mut compte = 0u64;
    let mut crible = vec![0u64; n as usize];
    for i in 2..n { if crible[i as usize] == 0 { compte += 1; let mut j = i * i; while j < n { crible[j as usize] = 1; j += i; } } }
    println!("premiers : {}", compte);
    println!("fib(27) : {}", fib(std::hint::black_box(27)));
    let mut h: u64 = 7;
    for k in 0..3_000_000u64 { h = h.wrapping_mul(31).wrapping_add(k) ^ (h >> 3); }
    println!("brassage : {}", h as i64);
}
