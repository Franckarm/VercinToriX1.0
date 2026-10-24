fn fib(n: u32) -> u32 { if n < 2 { n } else { fib(n - 1).wrapping_add(fib(n - 2)) } }
fn main() { println!("{}", fib(32)); }
