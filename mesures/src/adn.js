const M = 524288; const u = new Uint8Array(M * 16), v = new Uint8Array(M * 16); let x = 2463534242 >>> 0;
const pas = () => { x ^= x << 13; x >>>= 0; x ^= x >>> 17; x ^= x << 5; x >>>= 0; };
for (let i = 0; i < M; i++) {
  pas(); for (let q = 0; q < 16; q++) u[i * 16 + q] = (x >>> (2 * q)) & 3;
  pas(); for (let q = 0; q < 16; q++) v[i * 16 + q] = (x >>> (2 * q)) & 3;
}
let n = 0; for (let r = 0; r < 4; r++) for (let i = 0; i < M * 16; i++) n += u[i] === v[i] ? 1 : 0;
console.log(n);
