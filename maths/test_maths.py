"""Les fonctions mathématiques, le hasard et l'affichage du prélude.
1. Précision : sinus, cosinus, tangente, exponentielle, logarithme, puissance, arctangente(2), arcsinus, arccosinus,
   plancher, plafond, sur des valeurs tirées au hasard, comparées à la bibliothèque mathématique de Python.
2. afficher() : le texte attendu pour des entiers négatifs, des flottants, des longs, des logiques et des textes.
3. vtxc (dans vtx.exe) produit les mêmes mots que vtx.py pour ces programmes, et le même texte à l'exécution."""
import math, os, random, re, shutil, struct, subprocess, sys

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, racine)
import vtx  # noqa: E402

f32 = lambda x: struct.unpack("f", struct.pack("f", x))[0]
b2f = lambda b: struct.unpack("f", struct.pack("I", b))[0]
RAPIDE = os.environ.get("VTX_RAPIDE") == "1"
N = 15 if RAPIDE else 60


def lit(v):
    if v < 0:
        return "(0.0 - %s)" % lit(-v)
    s = format(v, ".60f").rstrip("0")
    return s + "0" if s.endswith(".") else s


hasard = random.Random(5)
cas = []
def ajoute(fn, ref, tirages, absolu=False, tol=1e-6):
    for x in tirages:
        cas.append((fn, [f32(v) for v in x], ref, absolu, tol))
U = hasard.uniform
ajoute("sinus", math.sin, [[U(-30, 30)] for _ in range(N)] + [[0.0], [3.1415927], [1000.5]], True, 3e-7)
ajoute("cosinus", math.cos, [[U(-30, 30)] for _ in range(N)] + [[0.0], [1000.5]], True, 3e-7)
ajoute("tangente", math.tan, [[U(-1.4, 1.4)] for _ in range(N)], False, 2e-6)
ajoute("exponentielle", math.exp, [[U(-80, 88)] for _ in range(N)] + [[0.0], [1.0], [-1.0]], False, 1e-6)
ajoute("logarithme", math.log, [[10 ** U(-37, 38)] for _ in range(N)] + [[1.0], [2.0], [0.5]], True, 3e-6)
ajoute("puissance", math.pow, [[U(0.01, 10), U(-5, 5)] for _ in range(N)] + [[-2.0, 3.0], [2.0, 10.0]], False, 3e-6)
ajoute("arctangente", math.atan, [[U(-50, 50)] for _ in range(N)] + [[1.0], [-1.0]], True, 3e-7)
ajoute("arctangente2", math.atan2, [[U(-5, 5), U(-5, 5)] for _ in range(N)], True, 5e-7)
ajoute("arcsinus", math.asin, [[U(-1, 1)] for _ in range(N)] + [[1.0], [-1.0]], True, 5e-7)
ajoute("arccosinus", math.acos, [[U(-1, 1)] for _ in range(N)], True, 5e-7)
ajoute("plancher", math.floor, [[U(-1e4, 1e4)] for _ in range(N)] + [[-0.5], [2.0], [-3.0]], True, 0)
ajoute("plafond", math.ceil, [[U(-1e4, 1e4)] for _ in range(N)] + [[-0.5], [2.0]], True, 0)
src = "fonction principal() {\n" + "".join("    sortie(bits(%s(%s)));\n" % (fn, ", ".join(lit(a) for a in x))
                                           for fn, x, _, _, _ in cas) + "}\n"
cpu, _, _ = vtx.executer(src, max_pas=50_000_000)
pire, echecs = {}, 0
for (fn, x, ref, absolu, tol), b in zip(cas, cpu.sortie):
    v, e = b2f(b), ref(*x)
    err = abs(v - e) / max(1.0, abs(e)) if absolu else abs(v - e) / abs(e)
    pire[fn] = max(pire.get(fn, 0), err)
    if err > tol:
        echecs += 1
        print(f"  {fn}{tuple(x)} = {v!r}, attendu {e!r}")
print("1. Précision sur %d calculs : %s" % (len(cas), ", ".join(f"{k} {v:.1e}" for k, v in pire.items())))

AFFICHER = """fonction principal() {
    afficher(3 - 5);
    afficher(42);
    afficher(7.0 / 2);
    afficher(1.0 / 3.0);
    afficher(0.0 - 2.5);
    afficher(3.0);
    afficher(100000000000000000000.0);
    afficher(0.0000123);
    afficher(1.0 / 0.0);
    afficher(0L - 1234567890123L);
    afficher(fusion(vrai, faux));
    afficher(inconnu);
    afficher("Bonjour");
    afficher(sinus(pi() / 6.0));
    afficher(puissance(2.0, 10.0));
    ecrire_flottant(1, 2.0 / 3.0, 2);
    ecrire_car(1, 32);
    ecrire_hexa(1, #FF6020C0);
    ecrire_car(1, 10);
    graine(42);
    soit somme = 0;
    pour i dans 0..600 {
        soit d = hasard_entre(1, 6);
        si d < 1 || d > 6 { somme = 1000000; }
        somme = somme + d;
    }
    afficher(somme);
}
"""
ATTENDU = ("-2\n42\n3.5\n0.333333\n-2.5\n3.0\n1.0e20\n1.23e-5\ninf\n-1234567890123\nvariable\ninconnu\nBonjour\n0.5\n1024.0\n"
           "0.67 #FF6020C0\n")
cpu, _, _ = vtx.executer(AFFICHER, max_pas=50_000_000)
texte = "".join(chr(c) for c in cpu.texte)
debut, somme = texte[:len(ATTENDU)], texte[len(ATTENDU):].strip()
ok2 = debut == ATTENDU and somme.isdigit() and 1800 <= int(somme) <= 2400
print(f"2. afficher : {'texte attendu' if debut == ATTENDU else 'ÉCART'} ; 600 dés, somme {somme} (attendu vers 2100)")
if debut != ATTENDU:
    print(repr(debut))

ok3 = True
cargo = shutil.which("cargo")
if cargo:
    rs = os.path.join(racine, "vtx-rs")
    cible = os.environ.get("CARGO_TARGET_DIR") or os.path.join(rs, "target")
    subprocess.run([cargo, "build", "--release", "-q"], cwd=rs, check=True)
    exe = os.path.join(cible, "release", "vtx" + (".exe" if os.name == "nt" else ""))
    import tempfile
    d = tempfile.mkdtemp()
    try:
        for nom, s in (("maths", src), ("afficher", AFFICHER)):
            f = os.path.join(d, nom + ".vtx")
            open(f, "w", encoding="utf-8").write(s)
            subprocess.run([exe, "compiler", f, os.path.join(d, nom + ".prog")], check=True, capture_output=True)
            mots = [int(x) for x in open(os.path.join(d, nom + ".prog")).read().split(";")[0].split(",")]
            py = vtx.assembler(vtx.compiler(s, dossier=d))
            if mots != py:
                print(f"  {nom} : {len(mots)} mots par vtxc, {len(py)} par vtx.py")
            ok3 &= mots == py
        r = subprocess.run([exe, os.path.join(d, "afficher.vtx")], capture_output=True, text=True, encoding="utf-8")
        if r.stdout != texte:
            print("  texte de vtx.exe :", repr(r.stdout[:200]), r.stderr[-300:])
        ok3 &= r.stdout == texte
    finally:
        shutil.rmtree(d, ignore_errors=True)
    print(f"3. vtxc (vtx.exe) : mêmes mots que vtx.py et même texte affiché : {'oui' if ok3 else 'NON'}")
sys.exit(0 if echecs == 0 and ok2 and ok3 else 1)
