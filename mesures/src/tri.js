const N = 500000; const a = new Uint32Array(N); let x = 2463534242 >>> 0;
for (let i = 0; i < N; i++) { x ^= x << 13; x >>>= 0; x ^= x >>> 17; x ^= x << 5; x >>>= 0; a[i] = x & 16777215; }
function trier(g, d) {
  while (g < d) {
    const p = a[(g + d) >> 1]; let i = g, j = d;
    while (i <= j) { while (a[i] < p) i++; while (a[j] > p) j--; if (i <= j) { const t = a[i]; a[i] = a[j]; a[j] = t; i++; j--; } }
    if (j - g < d - i) { if (g < j) trier(g, j); g = i; } else { if (i < d) trier(i, d); d = j; }
  }
}
trier(0, N - 1);
let s = 0; for (let i = 0; i < N; i++) s = (Math.imul(s, 31) + a[i]) >>> 0;
console.log(s);
