"""0.845 : les cubes nommés (« cube nom @2; », « cube f[N] @2 frequence F; », « cube x @2 arn; », « @nom[i] »,
« @f(t)[i] ») : les deux compilateurs de Lugus (vtx128.py, vtxc128) et de Dunon (vtx64.py, vtxc64) donnent les mêmes
mots, la même sortie, et les mêmes refus."""
import os, subprocess, sys, tempfile
ICI = os.path.dirname(os.path.abspath(__file__))
R = os.path.dirname(ICI)
sys.path[:0] = [R, os.path.join(R, "spu64")]
import vtx128, vtx64  # noqa: E402
LUGUS = os.path.join(R, "vtx-rs", "target", "release", "lugus")
VTX64 = os.path.join(R, "vtx-rs", "target", "release", "vtx64")
ok = True


def dire(nom, bon, detail=""):
    global ok
    ok &= bon
    print(("OK   " if bon else "ÉCHEC ") + nom + ("" if bon else " : " + str(detail)[:300]))


EX = os.path.join(R, "exemples128", "cubes_nommes.vtx")
ATTENDU = "relief : 9 49\ntuile 2 : 102\npassage : 151\nà la main : 49 102 151"
with tempfile.TemporaryDirectory() as d:
    for nom, mod, binaire in (("Lugus", vtx128, LUGUS), ("Dunon", vtx64, VTX64)):
        src = open(EX, encoding="utf-8").read()
        m = mod.assembler(mod.compiler(src, dossier=os.path.dirname(EX)))
        if isinstance(m, tuple):
            m = m[0]
        f = os.path.join(d, "x.mots")
        subprocess.run([binaire, "compiler", EX, f], capture_output=True, text=True)
        ml = [int(x) for x in open(f).read().split(";")[0].split(",") if x.strip()]
        dire(f"{nom} : les mêmes mots par les deux compilateurs ({len(ml)} mots)", m == ml)
        sortie = subprocess.run([binaire, EX], capture_output=True, text=True).stdout.strip()
        dire(f"{nom} : la sortie", sortie == ATTENDU, sortie)
    refus = ["cube a @2; cube a @2; fonction principal() {}",
             "cube a @2 frequence 10; cube b[3] @2 frequence 8; fonction principal() {}",
             "cube a @0; fonction principal() {}",
             "cube f[2] @2; fonction principal() { @f[1] = 2; }",
             "cube a @2; fonction principal() { @a(1)[1] = 2; }",
             "cube a @2 frequence; fonction principal() {}",
             "cube a @2 x; fonction principal() {}",
             "cube f[0] @2; fonction principal() {}"]
    for k, r in enumerate(refus):
        p = os.path.join(d, f"r{k}.vtx")
        open(p, "w", encoding="utf-8").write(r + "\n")
        for nom, mod, binaire in (("Lugus", vtx128, LUGUS), ("Dunon", vtx64, VTX64)):
            try:
                mod.compiler(r)
                py = "accepté"
            except mod.VtxError as e:
                py = str(e)
            rs = subprocess.run([binaire, p], capture_output=True, text=True)
            vx = (rs.stdout + rs.stderr).strip().splitlines()[0] if (rs.stdout + rs.stderr).strip() else ""
            dire(f"{nom} : refusé de même : {py}", vx.endswith(py) and py != "accepté", (py, vx))
print("Les cubes nommés : tout est conforme" if ok else "Les cubes nommés : des écarts")
sys.exit(0 if ok else 1)
