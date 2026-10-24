fn main() {
    let mut total: u32 = 0;
    for py in 0..300 {
        let ci = py as f32 * 0.008 - 1.2;
        for px in 0..400 {
            let cr = px as f32 * 0.0075 - 2.1;
            let (mut x, mut y, mut k) = (0.0f32, 0.0f32, 0u32);
            while k < 200 && x * x + y * y <= 4.0 {
                let t = x * x - y * y + cr;
                y = 2.0 * x * y + ci;
                x = t;
                k += 1;
            }
            total += k;
        }
    }
    println!("{}", total);
}
