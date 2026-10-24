#!/usr/bin/env python3
"""Les appels en série « f(a): x, y, z; » (= f(a, x); f(a, y); f(a, z);) : les quatre compilateurs.

 1. Chaque programme donne les mêmes mots que sa forme écrite à la main (vtx.py et vtx64.py).
 2. vtxc et vtxc64 (embarqués dans la machine Rust) donnent les mêmes mots que vtx.py et vtx64.py, ou refusent avec eux.
 3. L'exécution : mêmes sorties sur les machines Python et Rust.
"""
import os
import shutil
import subprocess
import sys
import tempfile

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, racine)
import vtx  # noqa: E402
import vtx64  # noqa: E402

CAS = [
    # (programme en série, le même écrit à la main)
    ("""fonction principal() {
    soit l = tableau(0);
    ajouter(l): 1, 2, (3 + 4) * 2, 9;
    pour v dans l { sortie(v); }
}""", """fonction principal() {
    soit l = tableau(0);
    ajouter(l, 1); ajouter(l, 2); ajouter(l, (3 + 4) * 2); ajouter(l, 9);
    pour v dans l { sortie(v); }
}"""),
    ("""fonction principal() {
    afficher(): "un, deux", 42, 1.5;
    ecrire(): "x = ",
              7,
              "\\n";
}""", """fonction principal() {
    afficher("un, deux"); afficher(42); afficher(1.5);
    ecrire("x = "); ecrire(7); ecrire("\\n");
}"""),
    ("""structure P { x, y }
fonction somme(a, b, p: P) { sortie(a + b + p.x + p.y); }
fonction principal() {
    soit k = 3;
    si k > 1 {
        somme(k, 1): P { x: 1, y: 2 }, P { x: k, y: [4, 5][1] };
    } sinon {
        sortie(0);
    }
}""", """structure P { x, y }
fonction somme(a, b, p: P) { sortie(a + b + p.x + p.y); }
fonction principal() {
    soit k = 3;
    si k > 1 {
        somme(k, 1, P { x: 1, y: 2 }); somme(k, 1, P { x: k, y: [4, 5][1] });
    } sinon {
        sortie(0);
    }
}"""),
    ("""fonction f(a, b) { sortie(a * 10 + b); }
fonction principal() {
    pour i dans 0..3 {
        f(i): i, i + 1;
    }
}""", """fonction f(a, b) { sortie(a * 10 + b); }
fonction principal() {
    pour i dans 0..3 {
        f(i, i); f(i, i + 1);
    }
}"""),
]
ERREURS = [
    "fonction principal() {\n    sortie(): 1, 2\n}",
    "fonction principal() {\n    sortie(): ;\n}",
    "fonction principal() {\n    sortie(): 1, , 2;\n}",
]

ok1 = 0
for a, b in CAS:
    m = [vtx.assembler(vtx.compiler(s, prelude=True, optim=True)) for s in (a, b)]
    n = [vtx64.assembler(vtx64.compiler(s, prelude=True, optim=True)) for s in (a, b)]
    ok1 += m[0] == m[1] and n[0] == n[1]
print(f"1. {ok1}/{len(CAS)} programmes en série : mêmes mots que la forme écrite à la main (vtx.py et vtx64.py)")
refus = 0
for e in ERREURS:
    for mod in (vtx, vtx64):
        try:
            mod.compiler(e)
        except mod.VtxError:
            refus += 1
print(f"   {refus}/{2 * len(ERREURS)} formes fautives refusées")
echec = ok1 != len(CAS) or refus != 2 * len(ERREURS)

cargo = shutil.which("cargo")
if not cargo:
    print("cargo absent : vtxc et vtxc64 ne sont pas vérifiés")
    sys.exit(1 if echec else 0)
rs = os.path.join(racine, "vtx-rs")
cible = os.environ.get("CARGO_TARGET_DIR") or os.path.join(rs, "target")
subprocess.run([cargo, "build", "--release", "-q"], cwd=rs, check=True)
ext = ".exe" if os.name == "nt" else ""
VTX, VTX64 = os.path.join(cible, "release", "vtx" + ext), os.path.join(cible, "release", "vtx64" + ext)
TMP = tempfile.mkdtemp(prefix="serie-")


def mots(exe, src, sortie):
    p = os.path.join(TMP, "p.vtx")
    with open(p, "w", encoding="utf-8") as f:
        f.write(src)
    q = os.path.join(TMP, sortie)
    if os.path.exists(q):
        os.remove(q)
    r = subprocess.run([exe, "compiler", p, q], capture_output=True)
    if r.returncode != 0 or not os.path.exists(q):
        return None
    return [int(x) for x in open(q).read().strip().split(";")[0].split(",") if x]


ok2 = ok3 = 0
for a, _ in CAS:
    m32 = vtx.assembler(vtx.compiler(a, prelude=True, optim=True, partition=True))
    m64 = vtx64.assembler(vtx64.compiler(a, prelude=True, optim=True, partition=True))
    ok2 += mots(VTX, a, "p.prog") == m32 and mots(VTX64, a, "p.mots") == m64
    p = os.path.join(TMP, "p.vtx")
    s32 = subprocess.run([VTX, p], capture_output=True, text=True).stdout
    s64 = subprocess.run([VTX64, p], capture_output=True, text=True).stdout
    r = vtx.executer(a, ())[0]
    attendu = "".join(chr(c) for c in r.texte) + (",".join(map(str, r.sortie)) + "\n" if r.sortie else "")
    ok3 += s32 == attendu and s64 == attendu
for e in ERREURS:
    ok2 += 0 if (mots(VTX, e, "p.prog") is None and mots(VTX64, e, "p.mots") is None) else -100
print(f"2. vtxc et vtxc64 : mêmes mots que vtx.py et vtx64.py ({ok2}/{len(CAS)}), et les mêmes refus")
print(f"3. exécution : mêmes sorties, machine Python et machines Rust 32 et 64 bits : {ok3}/{len(CAS)}")
shutil.rmtree(TMP, ignore_errors=True)
echec = echec or ok2 != len(CAS) or ok3 != len(CAS)
print("Appels en série : " + ("tout est conforme" if not echec else "ÉCHEC"))
sys.exit(1 if echec else 0)
