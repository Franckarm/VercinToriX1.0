// Traducteur du code machine du SPU vers JavaScript : chaque bloc de base devient une fonction JavaScript compilée
// une fois, les registres deviennent des variables, les opérandes et les adresses fixes sont résolus à la traduction.
// Même interface et même sémantique que SPU() de vm_rapide.js (sorties, nombre d'instructions, mémoire).
// Hypothèse : le code ne se modifie pas lui-même (les écritures dans l'étage 0 ne touchent que la pile et les données).
function SPUTraduit(words) {
  const ADR = 0xFFFFFF, LIM = 65536;
  const code = new Uint32Array(65536), pile = new Uint32Array(65536);
  const S = [null, new Uint32Array(LIM), new Uint32Array(LIM), new Uint32Array(LIM)], haut = new Map();
  code.set(words);
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
  const dot = (x, y) => (((x >>> 24) * (y >>> 24)) + (((x >>> 16) & 255) * ((y >>> 16) & 255)) + (((x >>> 8) & 255) * ((y >>> 8) & 255)) + ((x & 255) * (y & 255)));
  const FB = new Float32Array(1), IB = new Uint32Array(FB.buffer);
  const vf = w => { IB[0] = w; return FB[0]; };
  const fb = v => { if (v !== v) return 0x7FC00000; FB[0] = v; return IB[0]; };
  const sat = t => t >= 2147483648 ? 0x7FFFFFFF : t < -2147483648 ? 0x80000000 : t >>> 0;
  const pair = x => { const f = Math.floor(x), d = x - f; return d < 0.5 ? f : d > 0.5 ? f + 1 : (f % 2 === 0 ? f : f + 1); };
  const ftoi = w => { const x = vf(w); return x !== x ? 0 : sat(Math.trunc(x)); };
  const fround = w => { const x = vf(w); return x !== x ? 0 : !isFinite(x) ? sat(x) : sat(pair(x)); };
  const popc = (x) => { x = x - ((x >>> 1) & 0x55555555); x = (x & 0x33333333) + ((x >>> 2) & 0x33333333);
    return Math.imul((x + (x >>> 4)) & 0x0F0F0F0F, 0x01010101) >>> 24; };
  const mulhu = (a, b) => { const al = a & 0xFFFF, ah = a >>> 16, bl = b & 0xFFFF, bh = b >>> 16;
    const ll = al * bl, lh = al * bh, hl = ah * bl, hh = ah * bh; const mid = (ll >>> 16) + (lh & 0xFFFF) + (hl & 0xFFFF);
    return (hh + (lh >>> 16) + (hl >>> 16) + Math.floor(mid / 65536)) >>> 0; };
  const quit = (A, B, f) => { let r = 0; for (let q = 0; q < 16; q++) { const x = (A >>> (2 * q)) & 3, y = (B >>> (2 * q)) & 3; r |= (f === 0 ? Math.min(x, y) : f === 1 ? Math.max(x, y) : (x + y) & 3) << (2 * q); } return r >>> 0; };
  const gemv = (sp) => { const n = rd(0, sp + 4), ww = rd(0, sp + 3), qb = rd(0, sp + 2), kb = rd(0, sp + 1), ob = rd(0, sp);
    for (let i = 0; i < n; i++) { let s = 0; for (let j = 0; j < ww; j++) s += dot(rd(2, qb + j), rd(2, kb + i * ww + j)); wr(2, ob + i, s); } };
  const ctx = { R: new Uint32Array(16), z: false, c: false, steps: 0, max: 0, inp: [], ii: 0, out: [], texte: [] };

  // 1. Code atteignable et débuts de blocs, en suivant le flot de contrôle depuis l'adresse 0.
  const SAUTS = new Set([48, 49, 50, 51, 53, 54]);
  const instr = new Map(), debuts = new Set([0]), pile_a = [0];
  while (pile_a.length) {
    const pc = pile_a.pop();
    if (instr.has(pc) || pc >= words.length) continue;
    const w = code[pc], op = w >>> 24, g = (w >>> 16) & 255, b = (w >>> 8) & 255;
    const lg = op === 10 ? 2 : 1, suite = pc + lg;
    instr.set(pc, w);
    if (SAUTS.has(op)) { const t = (g << 8) | b; debuts.add(t); pile_a.push(t); }
    if (op === 48 || op === 52 || op === 63) { if (op === 63) debuts.add(suite); continue; }
    if (SAUTS.has(op)) debuts.add(suite);
    pile_a.push(suite);
  }

  // 2. Traduction d'une instruction en instructions JavaScript.
  const Rg = i => i === 0 ? "0" : "R[" + i + "]";
  const ecr = (d, v) => d === 0 ? "" : "R[" + d + "]=" + v + ";";
  function traduire(pc, w) {
    const op = w >>> 24, g = (w >>> 16) & 255, b = (w >>> 8) & 255, et = (w & 255) >>> 6;
    const d = g >> 4, s = g & 15, t = b >> 4, dc = b > 127 ? b - 256 : b, cible = (g << 8) | b, nx = (pc + (op === 10 ? 2 : 1)) & ADR;
    const A = Rg(s), B = Rg(t), F = "C.z=r===0;C.c=false;";
    switch (op) {
      case 0: return "";
      case 1: return `{const u=${A}+${B};r=u>>>0;${ecr(d, "r")}C.z=r===0;C.c=u>4294967295;}`;
      case 6: return `{const u=${A}+${b};r=u>>>0;${ecr(d, "r")}C.z=r===0;C.c=u>4294967295;}`;
      case 2: case 14: return `{const a=${A},y=${B};r=(a-y)>>>0;${op === 2 ? ecr(d, "r") : ""}C.z=r===0;C.c=a<y;}`;
      case 7: return `{const a=${A};r=(a-${b})>>>0;${ecr(d, "r")}C.z=r===0;C.c=a<${b};}`;
      case 3: return `r=Math.imul(${A},${B})>>>0;${ecr(d, "r")}${F}`;
      case 4: return `r=(${A}<<2)>>>0;${ecr(d, "r")}${F}`;
      case 5: return `r=${A}>>>2;${ecr(d, "r")}${F}`;
      case 8: return `r=(${A}<<(${B}&31))>>>0;${ecr(d, "r")}${F}`;
      case 9: return `r=${A}>>>(${B}&31);${ecr(d, "r")}${F}`;
      case 10: { const k = code[pc + 1] >>> 0; return `${ecr(d, k)}C.z=${k === 0};C.c=false;`; }
      case 11: return ecr(d, A);
      case 12: return `{const a=${A},y=${B};r=y===0?4294967295:(a-(a%y))/y;${ecr(d, "r")}${F}}`;
      case 13: return `{const a=${A},y=${B};r=y===0?a:a%y;${ecr(d, "r")}${F}}`;
      case 16: return `r=quit(${A},${B},0);${ecr(d, "r")}${F}`;
      case 17: return `r=quit(${A},${B},1);${ecr(d, "r")}${F}`;
      case 19: return `r=quit(${A},${B},2);${ecr(d, "r")}${F}`;
      case 18: return `r=(~${A})>>>0;${ecr(d, "r")}${F}`;
      case 20: return `r=(${A}&${B})>>>0;${ecr(d, "r")}${F}`;
      case 21: return `r=(${A}|${B})>>>0;${ecr(d, "r")}${F}`;
      case 22: return `r=(${A}^${B})>>>0;${ecr(d, "r")}${F}`;
      case 32: return et === 0 ? `r=rd(0,${A});${ecr(d, "r")}${F}`
        : `{const a=${A}&16777215;r=a<65536?S${et}[a]:rd(${et},a);}${ecr(d, "r")}${F}`;
      case 33: return et === 0 ? `wr(0,${Rg(d)},${A});`
        : `{const a=${Rg(d)}&16777215;if(a<65536)S${et}[a]=${A};else wr(${et},a,${A});}`;
      case 35: return ecr(d, "(C.ii<C.inp.length?C.inp[C.ii++]>>>0:0)") || "if(C.ii<C.inp.length)C.ii++;";
      case 36: return `C.out.push(${A});`;
      case 37: return ecr(d, `rd(0,(R[13]+${dc})&16777215)`);
      case 38: return `wr(0,(R[13]+${dc})&16777215,${Rg(d)});`;
      case 39: return `R[14]=(R[14]-1)&16777215;pile[R[14]-8323072]=${A};`;
      case 40: return `r=rd(0,R[14]);R[14]=(R[14]+1)&16777215;${ecr(d, "r")}`;
      case 41: return `r=rd(${B}&3,${A});${ecr(d, "r")}${F}`;
      case 42: return `wr(${B}&3,${Rg(d)},${A});`;
      case 48: return `return ${cible};`;
      case 49: return `if(C.z)return ${cible};`;
      case 50: return `if(!C.z)return ${cible};`;
      case 53: return `if(C.c)return ${cible};`;
      case 54: return `if(!C.c)return ${cible};`;
      case 51: return `R[14]=(R[14]-1)&16777215;wr(0,R[14],${nx});return ${cible};`;
      case 52: return `r=rd(0,R[14]);R[14]=(R[14]+1)&16777215;return r;`;
      case 56: return `r=dot(${A},${B})>>>0;${ecr(d, "r")}${F}`;
      case 57: return `gemv(R[14]);`;
      case 64: return `r=fb(vf(${A})+vf(${B}));${ecr(d, "r")}${F}`;
      case 65: return `r=fb(vf(${A})-vf(${B}));${ecr(d, "r")}${F}`;
      case 66: return `r=fb(vf(${A})*vf(${B}));${ecr(d, "r")}${F}`;
      case 67: return `r=fb(vf(${A})/vf(${B}));${ecr(d, "r")}${F}`;
      case 68: return `r=vf(${A})===vf(${B})?1:0;${ecr(d, "r")}${F}`;
      case 69: return `r=vf(${A})<vf(${B})?1:0;${ecr(d, "r")}${F}`;
      case 70: return `r=vf(${A})<=vf(${B})?1:0;${ecr(d, "r")}${F}`;
      case 71: return `r=fb(Math.sqrt(vf(${A})));${ecr(d, "r")}${F}`;
      case 72: return `r=fb(${A});${ecr(d, "r")}${F}`;
      case 73: return `r=fb(${A}|0);${ecr(d, "r")}${F}`;
      case 74: return `r=ftoi(${A});${ecr(d, "r")}${F}`;
      case 75: return `r=fround(${A});${ecr(d, "r")}${F}`;
      case 76: return `{const u=${A}+${B}+(C.c?1:0);r=u>>>0;${ecr(d, "r")}C.z=r===0;C.c=u>4294967295;}`;
      case 77: return `{const a=${A},y=${B}+(C.c?1:0);r=(a-y)>>>0;${ecr(d, "r")}C.z=r===0;C.c=a<y;}`;
      case 78: return `r=mulhu(${A},${B});${ecr(d, "r")}${F}`;
      case 79: return `{const x=(${A}^${B})>>>0;r=(~(x|(x>>>1))&1431655765)>>>0;${ecr(d, "r")}${F}}`;
      case 80: return `r=popc(${A});${ecr(d, "r")}${F}`;
      case 81: return `r=(${A})===0?(C.ii<C.inp.length?C.inp[C.ii++]>>>0:0):4294967295;${ecr(d, "r")}${F}`;
      case 82: return `{const k=${B};if(k===0)C.out.push(${A});else if(k===1)C.texte.push(${A});}`;
      case 83: return `r=(${A})===4?1:(${A})===5?(Math.random()*4294967296)>>>0:4294967295;${ecr(d, "r")}C.z=false;C.c=false;`;
      case 63: return `return -1;`;
      default: return `throw new Error("code d’opération ${op} à l’adresse ${pc}");`;
    }
  }

  // 3. Un bloc = une fonction : nombre d'instructions compté à l'entrée, puis les instructions à la suite.
  const S1 = S[1], S2 = S[2], S3 = S[3];
  const fabrique = (src) => new Function("C", "R", "S1", "S2", "S3", "rd", "wr", "dot", "quit", "gemv", "pile",
    "vf", "fb", "ftoi", "fround", "mulhu", "popc", src)(ctx, ctx.R, S1, S2, S3, rd, wr, dot, quit, gemv, pile, vf, fb, ftoi, fround,
    mulhu, popc);
  const adresses = [...instr.keys()].sort((a, b) => a - b);
  const blocs = new Array(words.length + 1);
  let nblocs = 0, i = 0;
  while (i < adresses.length) {
    const debut = adresses[i];
    let corps = "", n = 0, pc = debut, fin = false;
    while (i < adresses.length && adresses[i] === pc && (pc === debut || !debuts.has(pc))) {
      const w = instr.get(pc), op = w >>> 24;
      corps += traduire(pc, w) + "\n";
      n++; i++;
      pc += op === 10 ? 2 : 1;
      if (op === 48 || op === 52 || op === 63) { fin = true; break; }
    }
    const src = `return function(){let r=0;C.steps+=${n};if(C.steps>C.max)throw new Error("limite de pas");\n${corps}${fin ? "" : "return " + pc + ";"}};`;
    blocs[debut] = fabrique(src);
    nblocs++;
  }

  function run(inputs, maxSteps) {
    const R = ctx.R; R.fill(0); R[14] = 0x7FFFFF;
    ctx.z = false; ctx.c = false; ctx.steps = 0; ctx.max = maxSteps; ctx.inp = inputs; ctx.ii = 0; ctx.out = []; ctx.texte = [];
    let pc = 0;
    while (pc !== -1) {
      const f = blocs[pc];
      if (f === undefined) throw new Error("saut vers une adresse non traduite : " + pc);
      pc = f();
    }
    return { out: ctx.out, steps: ctx.steps, texte: ctx.texte };
  }
  return { run, rd, wr, S, haut, nblocs, ninstr: instr.size };
}
if (typeof module !== "undefined") module.exports = { SPUTraduit };
