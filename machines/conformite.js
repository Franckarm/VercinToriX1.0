// Rejoue le corpus de conformité sur les deux machines JavaScript et compare aux résultats attendus.
// Utilisation : node machines/conformite.js conformite/corpus_conformite.txt conformite/corpus_attendu.txt
const fs = require("fs"), path = require("path");
eval(fs.readFileSync(path.join(__dirname, "vm_rapide.js"), "utf8") + "\n" + fs.readFileSync(path.join(__dirname, "vm_traduite.js"), "utf8")
  + "\nglobalThis.SPU = SPU; globalThis.SPUTraduit = SPUTraduit;");
const L = fs.readFileSync(process.argv[2], "utf8").trim().split("\n"), A = fs.readFileSync(process.argv[3], "utf8").trim().split("\n");
let total = 0;
for (const [nom, fab] of [["JavaScript interprété", globalThis.SPU], ["JavaScript traduit", globalThis.SPUTraduit]]) {
  let ec = 0;
  L.forEach((l, i) => {
    const [m, e] = l.split(";"); const mots = m.split(",").map(Number), ent = e ? e.split(",").map(Number) : [];
    const spu = fab(mots); const r = spu.run(ent, 5e8); const mem = [];
    for (let et = 1; et < 4; et++) for (let a = 0; a < 65536; a++) if (spu.S[et][a]) mem.push([et * 16777216 + a, spu.S[et][a]]);
    for (const [k, v] of spu.haut) if (k >= 16777216 && v) mem.push([k, v]);
    const s = r.steps + "|" + r.out.join(",") + "|" + mem.sort((x, y) => x[0] - y[0]).map(x => x[0] + ":" + x[1]).join(",")
      + (r.texte && r.texte.length ? "|T:" + r.texte.join(",") : "");
    if (s !== A[i]) ec++;
  });
  console.log(`${nom} : ${L.length} programmes, ${ec} écart(s)`);
  total += ec;
}
process.exit(total ? 1 : 0);
