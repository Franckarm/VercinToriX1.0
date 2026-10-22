"""Le type texte et afficher à plusieurs valeurs : vtx.py et vtxc donnent les mêmes mots, et le texte attendu."""
import glob, os, re, shutil, subprocess, sys, tempfile
ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, racine)
import vtx  # noqa: E402

rs = os.path.join(racine, "vtx-rs")
cible = os.environ.get("CARGO_TARGET_DIR") or os.path.join(rs, "target")
subprocess.run([shutil.which("cargo") or "cargo", "build", "--release", "-q"], cwd=rs, check=True)
VTX = os.path.join(cible, "release", "vtx" + (".exe" if os.name == "nt" else ""))
RAPIDE = os.environ.get("VTX_RAPIDE") == "1"


def mots_vtxc(f):
    p = f + ".prog"
    r = subprocess.run([VTX, "compiler", f, p], capture_output=True, text=True)
    if r.returncode:
        return "ERREUR " + (r.stdout + r.stderr)[-300:]
    m = [int(x) for x in open(p).read().split(";")[0].split(",")]
    os.remove(p)
    return m


def sans_points_virgules(t):
    # le « ; » en fin de ligne (suivi ou non d'un commentaire) disparaît
    return "\n".join(re.sub(r";([ \t]*(//.*)?)$", r"\1", l) for l in t.split("\n"))


tmp = tempfile.mkdtemp()
d = tmp
try:
    # 4. le type texte et afficher à plusieurs valeurs : même code par vtx.py et vtxc, et le texte attendu
    TEXTES = open(os.path.join(racine, "exemples", "premiers", "textes.vtx"), encoding="utf-8").read()
    ATTENDU = ("Bonjour, Vercintorix !\nn = -2\npi vaut 3.141593, et 2^40 vaut 1099511627776\nlogique : variable\négal\n"
               "différent\ntotal : 42 1.5 vrai fin\nAmbiorix a 40 ans\n11 6 cint\n-122\nsans retour 7\n01234\n1\n")
    f = os.path.join(d, "textes.vtx")
    open(f, "w", encoding="utf-8").write(TEXTES)
    py = vtx.assembler(vtx.compiler(TEXTES, dossier=d))
    vc = mots_vtxc(f)
    r = subprocess.run([VTX, f], capture_output=True, text=True, encoding="utf-8")
    cpu, _, _ = vtx.executer(TEXTES, dossier=d)
    t_py = "".join(chr(c) for c in cpu.texte)
    ok4 = py == vc and r.stdout == ATTENDU and t_py == ATTENDU
    print(f"Type texte (+, ==, !=, champs, texte(), sous_texte, position, nombre) et afficher(a, b, c) : "
          f"{'mêmes mots et texte attendu' if ok4 else 'ÉCART'}")
    if not ok4:
        print(repr(r.stdout), repr(t_py), py == vc)
finally:
    shutil.rmtree(tmp, ignore_errors=True)
sys.exit(0 if ok4 else 1)
