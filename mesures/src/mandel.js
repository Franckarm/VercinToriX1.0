// en flottants de 32 bits (Math.fround), comme le C et vtx
const f = Math.fround; let total = 0;
for (let py = 0; py < 300; py++) {
  const ci = f(f(f(py) * f(0.008)) - f(1.2));
  for (let px = 0; px < 400; px++) {
    const cr = f(f(f(px) * f(0.0075)) - f(2.1));
    let x = 0, y = 0, k = 0;
    while (k < 200 && f(f(x * x) + f(y * y)) <= 4) {
      const t = f(f(f(x * x) - f(y * y)) + cr);
      y = f(f(f(2 * x) * y) + ci); x = t; k++;
    }
    total += k;
  }
}
console.log(total);
