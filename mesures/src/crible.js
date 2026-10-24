const N = 5000000; const p = new Uint32Array(N);
for (let q = 2; q < N; q++) p[q] = 1;
for (let i = 2; i * i < N; i++) if (p[i] === 1) for (let j = i * i; j < N; j += i) p[j] = 0;
let n = 0; for (let k = 2; k < N; k++) n += p[k];
console.log(n);
