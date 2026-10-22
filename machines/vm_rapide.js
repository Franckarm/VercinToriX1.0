// Émulateur du SPU en JavaScript, mémoire en tableaux typés (même sémantique que vtx.py et Vtx.java).
function SPU(words) {
  const ADR = 0xFFFFFF, LIM = 65536;
  const code = new Uint32Array(65536), pile = new Uint32Array(65536);
  const S = [null, new Uint32Array(LIM), new Uint32Array(LIM), new Uint32Array(LIM)], haut = new Map();
  code.set(words);
  const R = new Uint32Array(16);
  const rd = (e, a) => {
    a &= ADR;
    if (e === 0) return a >= 0x7F0000 ? pile[a - 0x7F0000] : (a < 65536 ? code[a] : 0);
    if (a < LIM) return S[e][a];
    const v = haut.get(e * 0x1000000 + a);
    return v === undefined ? 0 : v;
  };
  const wr = (e, a, v) => {
    a &= ADR; v >>>= 0;
    if (e === 0) { if (a >= 0x7F0000) pile[a - 0x7F0000] = v; else if (a < 65536) code[a] = v; return; }
    if (a < LIM) S[e][a] = v; else haut.set(e * 0x1000000 + a, v);
  };
  const FB = new Float32Array(1), IB = new Uint32Array(FB.buffer);
  const vf = w => { IB[0] = w; return FB[0]; };
  const fb = v => { if (v !== v) return 0x7FC00000; FB[0] = v; return IB[0]; };
  const sat = t => t >= 2147483648 ? 0x7FFFFFFF : t < -2147483648 ? 0x80000000 : t >>> 0;
  const pair = x => { const f = Math.floor(x), d = x - f; return d < 0.5 ? f : d > 0.5 ? f + 1 : (f % 2 === 0 ? f : f + 1); };
  const popc = (x) => { x = x - ((x >>> 1) & 0x55555555); x = (x & 0x33333333) + ((x >>> 2) & 0x33333333);
    return Math.imul((x + (x >>> 4)) & 0x0F0F0F0F, 0x01010101) >>> 24; };
  const mulhu = (a, b) => { const al = a & 0xFFFF, ah = a >>> 16, bl = b & 0xFFFF, bh = b >>> 16;
    const ll = al * bl, lh = al * bh, hl = ah * bl, hh = ah * bh; const mid = (ll >>> 16) + (lh & 0xFFFF) + (hl & 0xFFFF);
    return (hh + (lh >>> 16) + (hl >>> 16) + Math.floor(mid / 65536)) >>> 0; };
  const dot = (x, y) => (((x >>> 24) * (y >>> 24)) + (((x >>> 16) & 255) * ((y >>> 16) & 255)) + (((x >>> 8) & 255) * ((y >>> 8) & 255)) + ((x & 255) * (y & 255)));
  function run(inputs, maxSteps) {
    R.fill(0); R[14] = 0x7FFFFF;
    const out = [], texte = [], inp = inputs; let ii = 0, pc = 0, z = false, c = false, halt = false, steps = 0;
    const set = (i, v) => { if (i) R[i] = v >>> 0; };
    while (!halt) {
      if (steps++ > maxSteps) throw new Error("limite de pas");
      const w = code[pc], op = w >>> 24, g = (w >>> 16) & 255, b = (w >>> 8) & 255, et = (w & 255) >>> 6;
      const d = g >> 4, A = R[g & 15], B = R[b >> 4], dc = b > 127 ? b - 256 : b;
      let nx = (pc + 1) & ADR, r;
      switch (op) {
        case 0: break;
        case 1: case 6: { const s = A + (op === 1 ? B : b); r = s >>> 0; set(d, r); z = r === 0; c = s > 0xFFFFFFFF; break; }
        case 2: case 7: case 14: { const y = op === 7 ? b : B; r = (A - y) >>> 0; if (op !== 14) set(d, r); z = r === 0; c = A < y; break; }
        case 3: r = Math.imul(A, B) >>> 0; set(d, r); z = r === 0; c = false; break;
        case 4: r = (A << 2) >>> 0; set(d, r); z = r === 0; c = false; break;
        case 5: r = A >>> 2; set(d, r); z = r === 0; c = false; break;
        case 8: r = (A << (B & 31)) >>> 0; set(d, r); z = r === 0; c = false; break;
        case 9: r = A >>> (B & 31); set(d, r); z = r === 0; c = false; break;
        case 10: r = code[nx]; set(d, r); z = r === 0; c = false; nx = (nx + 1) & ADR; break;
        case 11: set(d, A); break;
        case 12: case 13: r = B === 0 ? (op === 12 ? 0xFFFFFFFF : A) : (op === 12 ? (A - (A % B)) / B : A % B); set(d, r); z = r === 0; c = false; break;
        case 16: case 17: case 19: { r = 0; for (let q = 0; q < 16; q++) { const x = (A >>> (2 * q)) & 3, y = (B >>> (2 * q)) & 3; r |= (op === 16 ? Math.min(x, y) : op === 17 ? Math.max(x, y) : (x + y) & 3) << (2 * q); } r >>>= 0; set(d, r); z = r === 0; c = false; break; }
        case 18: r = (~A) >>> 0; set(d, r); z = r === 0; c = false; break;
        case 20: r = (A & B) >>> 0; set(d, r); z = r === 0; c = false; break;
        case 21: r = (A | B) >>> 0; set(d, r); z = r === 0; c = false; break;
        case 22: r = (A ^ B) >>> 0; set(d, r); z = r === 0; c = false; break;
        case 32: r = rd(et, A); set(d, r); z = r === 0; c = false; break;
        case 33: wr(et, R[d], A); break;
        case 35: set(d, ii < inp.length ? inp[ii++] : 0); break;
        case 36: out.push(A); break;
        case 37: set(d, rd(0, (R[13] + dc) & ADR)); break;
        case 38: wr(0, (R[13] + dc) & ADR, R[d]); break;
        case 39: R[14] = (R[14] - 1) & ADR; wr(0, R[14], A); break;
        case 40: r = rd(0, R[14]); R[14] = (R[14] + 1) & ADR; set(d, r); break;
        case 41: { const e = B & 3; r = rd(e, A); set(d, r); z = r === 0; c = false; break; }
        case 42: wr(B & 3, R[d], A); break;
        case 84: r = (rd(et, (A + (B >>> 4)) & ADR) >>> ((B & 15) * 2)) & 3; set(d, r); z = r === 0; c = false; break;
        case 85: { const a = (A + (B >>> 4)) & ADR, sh = (B & 15) * 2;
          wr(et, a, ((rd(et, a) & ~(3 << sh)) | ((R[d] & 3) << sh)) >>> 0); break; }
        case 48: case 49: case 50: case 51: case 53: case 54: {
          const j = op === 48 || op === 51 || (op === 49 && z) || (op === 50 && !z) || (op === 53 && c) || (op === 54 && !c);
          if (op === 51) { R[14] = (R[14] - 1) & ADR; wr(0, R[14], nx); }
          if (j) nx = ((w & 15) << 16) | (g << 8) | b; break; }
        case 52: nx = rd(0, R[14]); R[14] = (R[14] + 1) & ADR; break;
        case 56: r = dot(A, B) >>> 0; set(d, r); z = r === 0; c = false; break;
        case 57: { const sp = R[14], n = rd(0, sp + 4), ww = rd(0, sp + 3), qb = rd(0, sp + 2), kb = rd(0, sp + 1), ob = rd(0, sp);
          for (let i = 0; i < n; i++) { let s = 0; for (let j = 0; j < ww; j++) s += dot(rd(2, qb + j), rd(2, kb + i * ww + j)); wr(2, ob + i, s); } break; }
        case 64: r = fb(vf(A) + vf(B)); set(d, r); z = r === 0; c = false; break;
        case 65: r = fb(vf(A) - vf(B)); set(d, r); z = r === 0; c = false; break;
        case 66: r = fb(vf(A) * vf(B)); set(d, r); z = r === 0; c = false; break;
        case 67: r = fb(vf(A) / vf(B)); set(d, r); z = r === 0; c = false; break;
        case 68: r = vf(A) === vf(B) ? 1 : 0; set(d, r); z = r === 0; c = false; break;
        case 69: r = vf(A) < vf(B) ? 1 : 0; set(d, r); z = r === 0; c = false; break;
        case 70: r = vf(A) <= vf(B) ? 1 : 0; set(d, r); z = r === 0; c = false; break;
        case 71: r = fb(Math.sqrt(vf(A))); set(d, r); z = r === 0; c = false; break;
        case 72: r = fb(A); set(d, r); z = r === 0; c = false; break;
        case 73: r = fb(A | 0); set(d, r); z = r === 0; c = false; break;
        case 74: { const x = vf(A); r = x !== x ? 0 : sat(Math.trunc(x)); set(d, r); z = r === 0; c = false; break; }
        case 75: { const x = vf(A); r = x !== x ? 0 : !isFinite(x) ? sat(x) : sat(pair(x)); set(d, r); z = r === 0; c = false; break; }
        case 76: { const s = A + B + (c ? 1 : 0); r = s >>> 0; set(d, r); z = r === 0; c = s > 0xFFFFFFFF; break; }
        case 77: { const y = B + (c ? 1 : 0); r = (A - y) >>> 0; set(d, r); z = r === 0; c = A < y; break; }
        case 78: r = mulhu(A, B); set(d, r); z = r === 0; c = false; break;
        case 79: { const x = (A ^ B) >>> 0; r = (~(x | (x >>> 1)) & 0x55555555) >>> 0; set(d, r); z = r === 0; c = false; break; }
        case 80: r = popc(A); set(d, r); z = r === 0; c = false; break;
        case 81: r = A === 0 ? (ii < inp.length ? inp[ii++] >>> 0 : 0) : 0xFFFFFFFF; set(d, r); z = r === 0; c = false; break;
        case 82: if (B === 0) out.push(A); else if (B === 1) texte.push(A); break;
        case 83: r = A === 4 ? 1 : A === 5 ? (Math.random() * 4294967296) >>> 0 : 0xFFFFFFFF; set(d, r); z = false; c = false; break;
        case 63: halt = true; break;
        default: throw new Error("code d’opération " + op);
      }
      pc = nx;
    }
    return { out, steps, texte };
  }
  return { run, rd, wr, S, haut };
}
