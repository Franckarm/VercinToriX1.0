"""Fait tourner un même programme (mots + entrées) sur les quatre machines de référence et rend, pour chacune, la ligne
« instructions|sorties|mémoire » du corpus de conformité. Sert aux tests qui ajoutent des instructions ou des types.

    lignes = lancer_toutes([(mots, entrees), ...])   ->  {"Python": [...], "Rust": [...], "JS interprété": [...], "JS traduit": [...]}
    ajouter_au_corpus(programmes)                     ->  ajoute des programmes au corpus de conformité (avec leur résultat)"""
import importlib.util
import os
import shutil
import subprocess
import tempfile

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
spec = importlib.util.spec_from_file_location("vtx", os.path.join(racine, "vtx.py"))
vtx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vtx)

EXE = os.path.join(racine, "vtx-rs", "target", "release", "vtx-spu" + (".exe" if os.name == "nt" else ""))


def ligne_python(mots, entrees, max_pas=500_000_000):
    cpu = vtx.CPU()
    cpu.charger(mots)
    cpu.entree.extend(entrees)
    cpu.executer(max_pas)
    mem = sorted((e * 16777216 + a, v) for (e, a), v in cpu.mem.items() if e >= 1 and v)
    s = f"{cpu.pas}|{','.join(map(str, cpu.sortie))}|{','.join(f'{k}:{v}' for k, v in mem)}"
    if cpu.texte:
        s += "|T:" + ",".join(map(str, cpu.texte))
    return s


def texte_corpus(programmes):
    return "\n".join(",".join(map(str, m)) + ";" + ",".join(map(str, e)) for m, e in programmes) + "\n"


def lignes_rust(programmes):
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(texte_corpus(programmes))
        nom = f.name
    try:
        r = subprocess.run([EXE, "corpus", nom], capture_output=True, text=True, encoding="utf-8")
    finally:
        os.unlink(nom)
    return r.stdout.strip().split("\n")


JS = r"""
const fs = require("fs"), path = require("path");
const racine = process.argv[2];
eval(fs.readFileSync(path.join(racine, "machines", "vm_rapide.js"), "utf8") + "\n" + fs.readFileSync(path.join(racine, "machines", "vm_traduite.js"), "utf8")
  + "\nglobalThis.SPU = SPU; globalThis.SPUTraduit = SPUTraduit;");
const L = fs.readFileSync(process.argv[3], "utf8").trim().split("\n");
const res = {};
for (const [nom, fab] of [["JS interprété", globalThis.SPU], ["JS traduit", globalThis.SPUTraduit]]) {
  res[nom] = L.map(l => {
    const [m, e] = l.split(";"); const mots = m.split(",").map(Number), ent = e ? e.split(",").map(Number) : [];
    const spu = fab(mots); let r;
    try { r = spu.run(ent, 5e8); } catch (x) { return "ERREUR " + x.message; }
    const mem = [];
    for (let et = 1; et < 4; et++) for (let a = 0; a < 65536; a++) if (spu.S[et][a]) mem.push([et * 16777216 + a, spu.S[et][a]]);
    for (const [k, v] of spu.haut) if (k >= 16777216 && v) mem.push([k, v]);
    return r.steps + "|" + r.out.join(",") + "|" + mem.sort((x, y) => x[0] - y[0]).map(x => x[0] + ":" + x[1]).join(",")
      + (r.texte && r.texte.length ? "|T:" + r.texte.join(",") : "");
  });
}
console.log(JSON.stringify(res));
"""


def lignes_js(programmes):
    if not shutil.which("node"):
        return {}
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(texte_corpus(programmes))
        nom = f.name
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(JS)
        js = f.name
    try:
        r = subprocess.run(["node", js, racine, nom], capture_output=True, text=True, encoding="utf-8")
    finally:
        os.unlink(nom)
        os.unlink(js)
    import json
    return json.loads(r.stdout)


def lancer_toutes(programmes):
    res = {"Python": [ligne_python(m, e) for m, e in programmes]}
    if os.path.exists(EXE):
        res["Rust"] = lignes_rust(programmes)
    res.update(lignes_js(programmes))
    return res


def comparer(res, ref="Python"):
    """Nombre d'écarts de chaque machine avec la référence."""
    return {nom: sum(a != b for a, b in zip(res[ref], v)) + abs(len(res[ref]) - len(v)) for nom, v in res.items() if nom != ref}


def ajouter_au_corpus(programmes, ecrire=True):
    """Ajoute des programmes (mots, entrées) au corpus de conformité, avec le résultat de la machine de référence."""
    cp = os.path.join(racine, "conformite", "corpus_conformite.txt")
    ca = os.path.join(racine, "conformite", "corpus_attendu.txt")
    res = lancer_toutes(programmes)
    ec = comparer(res)
    if any(ec.values()):
        raise RuntimeError(f"les machines ne s'accordent pas : {ec}")
    if ecrire:
        with open(cp, "a", encoding="utf-8") as f:
            f.write(texte_corpus(programmes))
        with open(ca, "a", encoding="utf-8") as f:
            f.write("\n".join(res["Python"]) + "\n")
    return res["Python"]
