#!/usr/bin/env python3
"""La forge contre la machine émulée : chaque programme forgé doit rendre les mêmes sorties, le même texte et le même
état final de la mémoire (étages 1 à 3) que le SPU émulé (vtx corpus).

Programmes : les exemples du paquet qui se terminent seuls (sans entrée, sans fenêtre), et des programmes tirés au
hasard (le générateur du test différentiel : opérations, mémoire, quits, appels, boucles, sorties).
Tous les programmes forgés vont dans un seul programme Rust (un module chacun), compilé une fois.

Utilisation : python3 forge/test_forge.py [NOMBRE_DE_PROGRAMMES_AU_HASARD] [--recolte FICHIER.json]
  (FICHIER.json : python3 forge/recolte.py FICHIER.json test_types.py test_flottant64.py …)
"""
import importlib.util
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, racine)
sys.path.insert(0, ici)
import vtx  # noqa: E402
import forge  # noqa: E402

cargo, rustc = shutil.which("cargo"), shutil.which("rustc")
if not (cargo and rustc):
    print("cargo ou rustc absent : la forge n'est pas essayée")
    sys.exit(0)
rs = os.path.join(racine, "vtx-rs")
cible = os.environ.get("CARGO_TARGET_DIR") or os.path.join(rs, "target")
subprocess.run([cargo, "build", "--release", "-q"], cwd=rs, check=True)
ext = ".exe" if os.name == "nt" else ""
VTX = os.path.join(cible, "release", "vtx" + ext)
TMP = tempfile.mkdtemp(prefix="forge-test-")
args = sys.argv[1:]
RECOLTE = None
if "--recolte" in args:
    i = args.index("--recolte")
    RECOLTE = args[i + 1]
    del args[i:i + 2]
NHASARD = int(args[0]) if args else 300

src_diff = open(os.path.join(racine, "tests", "test_differentiel.py"), encoding="utf-8").read()
# seulement le générateur (le fichier lance ses essais à la fin)
espace = {}
exec(compile("import random\n" + src_diff[src_diff.index("MASK = "):src_diff.index("\nclass Ret")], "diff", "exec"), espace)
Gen = espace["Gen"]

# ------------------------------------------------------------------ les programmes
cas = []          # (nom, source, entrées, dossier)
EXCLUS = {"vtxc", "debogueur", "jeu2", "jeu3", "toile", "scor", "exemples64", "mesures"}
for d, _, fichiers in os.walk(racine):
    rel = os.path.relpath(d, racine)
    if rel.startswith("vtx-rs") or any(p in EXCLUS for p in rel.split(os.sep)):
        continue
    for f in sorted(fichiers):
        if f.endswith(".vtx"):
            p = os.path.join(d, f)
            cas.append((os.path.relpath(p, racine), open(p, encoding="utf-8").read(), [], d))
rnd = random.Random(2026)
for k in range(NHASARD):
    cas.append((f"hasard-{k}", Gen(random.Random(rnd.random())).programme(), [], None))

# les programmes des tests de types (flottants, longs, flottant_64, entier_128, petuar) avec leurs entrées, récoltés
# par forge/recolte.py
if RECOLTE:
    import json
    for k, (src, entrees, dossier, test) in enumerate(json.load(open(RECOLTE))):
        cas.append((f"{test}#{k}", src, entrees, dossier))

# les mots du SPU (référence) et le Rust forgé
lignes, modules, gardes, refus = [], [], [], []
for nom, src, entrees, dossier in cas:
    try:
        g, mots, etiq = forge.compiler_arbre(src, dossier)
    except vtx.VtxError:
        continue          # ne compile pas sur le SPU : rien à comparer
    if "bruit()" in src or "hasard" in src:
        continue          # le bruit de la machine hôte : deux exécutions ne se ressemblent pas
    try:
        fo = forge.Forge(g, etiq)
        fonctions = fo.forger()
    except vtx.VtxError as e:
        refus.append((nom, str(e)))
        continue
    k = len(gardes)
    modules.append(f"mod p{k} {{\n#![allow(unused)]\nuse super::*;\nstatic MOTS: [u32; {len(mots)}] = ["
                   + ",".join(map(str, mots)) + "];\n" + "\n".join(fonctions)
                   + "\npub fn lancer(c: &mut Ctx) { charger_mots(&c.mem, &MOTS); f_principal(c); }\n}\n")
    lignes.append(",".join(map(str, mots)) + ";" + ",".join(map(str, entrees)))
    gardes.append(nom)

# la référence : le SPU émulé
cp = os.path.join(TMP, "corpus.txt")
with open(cp, "w") as f:
    f.write("\n".join(lignes) + "\n")
t0 = time.time()
ref = subprocess.run([VTX, "corpus", cp], capture_output=True, text=True).stdout.strip().split("\n")
temu = time.time() - t0

main = r'''
const NOM: &str = "vérification";
static MOTS: [u32; 0] = [];

fn main() {
    let fichier = std::env::args().nth(1).expect("fichier du corpus");
    let texte = fs::read_to_string(fichier).expect("lecture du corpus impossible");
    let lignes: Vec<String> = texte.lines().filter(|l| !l.trim().is_empty()).map(|l| l.to_string()).collect();
    let fil = std::thread::Builder::new().stack_size(1 << 30).spawn(move || {
        let sortie = std::io::stdout();
        let mut out = std::io::BufWriter::new(sortie.lock());
        let mut mem = Memoire::new(true);
        for (k, ligne) in lignes.iter().enumerate() {
            let (_m, e) = ligne.split_once(';').unwrap_or((ligne, ""));
            mem.effacer();
            let mut es = Es::new(nombres(e), None);
            es.clavier = false;
            let mut c = Ctx { mem, es, sp: PILE_HAUT };
            lancer(k, &mut c);
            let s: Vec<String> = c.es.sorties.iter().map(|v| v.to_string()).collect();
            let etat: Vec<String> = c.mem.etat().iter().map(|(k, v)| format!("{}:{}", k, v)).collect();
            let t: Vec<String> = c.es.texte.iter().map(|v| v.to_string()).collect();
            if t.is_empty() {
                writeln!(out, "{}|{}", s.join(","), etat.join(",")).unwrap();
            } else {
                writeln!(out, "{}|{}|T:{}", s.join(","), etat.join(","), t.join(",")).unwrap();
            }
            mem = c.mem;
            // l'étage 0 (code, pile) n'est pas suivi : on le remet à zéro
            unsafe { std::ptr::write_bytes(mem.base0, 0, ETAGE) };
        }
    }).unwrap();
    fil.join().unwrap();
}
'''
disp = "fn lancer(k: usize, c: &mut Ctx) {\n    match k {\n" + "".join(f"        {k} => p{k}::lancer(c),\n" for k in range(len(gardes))) + "        _ => {}\n    }\n}\n"
code = forge.noyau() + "\n".join(modules) + disp + main
rsf = os.path.join(TMP, "forge_corpus.rs")
with open(rsf, "w", encoding="utf-8") as f:
    f.write(code)
t0 = time.time()
r = subprocess.run([rustc, "--edition", "2021", "-C", "opt-level=1", "-C", "panic=abort", "-o", os.path.join(TMP, "fc" + ext), rsf],
                   capture_output=True, text=True)
tc = time.time() - t0
if r.returncode:
    print(r.stderr[-4000:])
    print("ÉCHEC : rustc refuse le corpus forgé (gardé dans", rsf, ")")
    sys.exit(1)
t0 = time.time()
obt = subprocess.run([os.path.join(TMP, "fc" + ext), cp], capture_output=True, text=True).stdout.strip().split("\n")
tf = time.time() - t0
# Le ramasse-miettes est conservateur : il garde tout bloc qu'un mot de la pile semble désigner. La pile du SPU porte
# d'autres mots que celle d'un programme forgé (registres sauvés, valeurs périmées) : après une purge, le tas peut
# garder quelques blocs de plus ou de moins. Ces programmes mesurent le tas ; on compare tout sauf ces mesures.
TAS = {"exemples/premiers/purge.vtx", "exemples/premiers/ramasser.vtx"}
ecarts, tas = [], 0
for k, nom in enumerate(gardes):
    a = ref[k].split("|", 1)[1] if k < len(ref) and "|" in ref[k] else (ref[k] if k < len(ref) else "?")
    b = obt[k] if k < len(obt) else "?"
    if a != b and nom in TAS:
        # les mêmes sorties ; le texte et la mémoire du tas peuvent différer par les seules mesures du tas
        ta, tb = (x.split("|T:")[-1] if "|T:" in x else "" for x in (a, b))
        texte = lambda t: "".join(chr(int(v)) for v in t.split(",") if v)
        sans_tas = lambda t: texte(t).rsplit("tas", 1)[0]
        if a.split("|")[0] == b.split("|")[0] and sans_tas(ta) == sans_tas(tb):
            tas += 1
            continue
    if a != b:
        ecarts.append((nom, a[:200], b[:200]))
for nom, a, b in ecarts[:10]:
    print("ÉCART", nom, "\n   SPU   :", a, "\n   forge :", b)
for nom, e in refus[:10]:
    print("REFUS", nom, ":", e)
print(f"Forge : {len(gardes)} programmes ({len(cas) - NHASARD} du paquet et des tests essayés, {NHASARD} au hasard), "
      f"{len(ecarts)} écart(s), {len(refus)} refus, {tas} mesure(s) du tas différente(s) ; rustc {tc:.0f} s ; SPU émulé {temu:.1f} s, forgés {tf:.2f} s")
if not ecarts and not refus:
    shutil.rmtree(TMP, ignore_errors=True)
sys.exit(1 if ecarts or refus else 0)
