"""0.845 : les cubes nommés (« cube nom @2; », « cube f[N] @2 frequence F; », « cube x @2 arn; », « @nom[i] »,
« @f(t)[i] ») : vtxc128 seul pour Lugus (0.851), les deux compilateurs de Dunon (vtx64.py, vtxc64) donnent les mêmes
mots, la même sortie, et les mêmes refus."""
import os, subprocess, sys, tempfile
ICI = os.path.dirname(os.path.abspath(__file__))
R = os.path.dirname(ICI)
sys.path[:0] = [R, os.path.join(R, "spu64")]
import vtx64  # noqa: E402
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
    for nom, mod, binaire in (("Lugus", None, LUGUS), ("Dunon", vtx64, VTX64)):
        src = open(EX, encoding="utf-8").read()
        f = os.path.join(d, "x.mots")
        subprocess.run([binaire, "compiler", EX, f], capture_output=True, text=True)
        ml = [int(x) for x in open(f).read().split(";")[0].split(",") if x.strip()]
        # 0.851 : sur Lugus, un seul compilateur (mod = None : vtxc128 répond seul)
        m = mod.assembler(mod.compiler(src, dossier=os.path.dirname(EX))) if mod is not None else ml
        if isinstance(m, tuple):
            m = m[0]
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
        # 0.851 : Dunon par ses deux compilateurs ; Lugus par vtxc128 seul, qui doit dire le même refus
        try:
            vtx64.compiler(r)
            py = "accepté"
        except vtx64.VtxError as e:
            py = str(e)
        for nom, binaire in (("Lugus", LUGUS), ("Dunon", VTX64)):
            rs = subprocess.run([binaire, p], capture_output=True, text=True)
            vx = (rs.stdout + rs.stderr).strip().splitlines()[0] if (rs.stdout + rs.stderr).strip() else ""
            dire(f"{nom} : refusé de même : {py}", vx.endswith(py) and py != "accepté", (py, vx))
print("Les cubes nommés : tout est conforme" if ok else "Les cubes nommés : des écarts")
sys.exit(0 if ok else 1)
