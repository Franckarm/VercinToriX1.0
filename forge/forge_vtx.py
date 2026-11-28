"""0.852 : la forge écrite en vtx (docs/vtx-un-compilateur.md, étape 2). vtxc128 écrit lui-même le Rust des fonctions
du programme (« code.rs », l'entrée « rust » de son protocole) pendant qu'il en écrit les mots ; ce module n'est plus
qu'un assembleur : le noyau, les mots, le Rust de vtxc128, la fin commune (forge128.queue_programme), puis rustc.

Ce que vtxc128 ne sait pas encore écrire, il le dit (« // pas encore : … ») : programme_rust_vtx rend alors None et la
raison, et forge128 garde la main (son propre Rust, depuis l'arbre de vtx128.py).

  forge128.forger_fichier essaie d'abord cette forge (0.856 : par défaut ; VTX_FORGE_VTX=0 : la forge Python seule)
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
X = ".exe" if os.name == "nt" else ""
LUGUS = os.path.join(racine, "vtx-rs", "target", "release", "lugus" + X)
VTXC128 = os.path.join(racine, "vtx-rs", "vtxc128.mots")


def lire_mots(t):
    return [int(x) for x in t.split(";")[0].replace("\n", "").split(",") if x.strip()]


def passer_vtxc128(src, dossier=None, compilateur=None, lots_python=False):
    """vtxc128 sur src, avec l'entrée « rust » : (le texte de code.rs, les mots) ; (None, le message) s'il refuse"""
    d = tempfile.mkdtemp(prefix="forge-vtx-")
    try:
        with open(os.path.join(d, "source.vtx"), "w", encoding="utf-8") as f:
            f.write(src)
        base = os.path.abspath(dossier) + os.sep if dossier else ""
        # le protocole de passer_vtxc128 (machine128.rs) : le dossier des importer, 0, prélude, optim, partition,
        # lignes, provenance, exemples ; puis rust
        entrees = [str(ord(ch)) for ch in base] + ["0", "1", "1", "1", "0", "0", "0", "2" if lots_python else "1"]
        # lugus lancer prend pour dossier celui des mots : le compilateur y est recopié, à côté de source.vtx
        shutil.copyfile(compilateur or VTXC128, os.path.join(d, "c.mots"))
        r = subprocess.run([LUGUS, "lancer", os.path.join(d, "c.mots")] + entrees, cwd=d, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL)
        cm, cr = os.path.join(d, "code.mots"), os.path.join(d, "code.rs")
        if not os.path.exists(cm) or not os.path.exists(cr):
            return None, (r.stdout + r.stderr).strip()
        return open(cr, encoding="utf-8", errors="replace").read(), lire_mots(open(cm).read())
    finally:
        shutil.rmtree(d, ignore_errors=True)


def programme_rust_vtx(src, dossier=None, nom="programme"):
    """(le programme forgé sans le noyau, ses mots) ; (None, la raison) si vtxc128 ne sait pas encore tout écrire"""
    import forge128
    rs, mots = passer_vtxc128(src, dossier)
    if rs is None:
        return None, "vtxc128 a refusé le programme : " + mots[-300:]
    if rs.startswith("// pas encore"):
        return None, rs.strip().splitlines()[0][3:]
    s = [f"const NOM: &str = {nom!r};".replace("'", '"'), rs,
         f"static MOTS: [u128; {len(mots)}] = [" + ",".join(str(w) for w in mots) + "];\n", queue_fixe()]
    return "\n".join(s), mots


def queue_fixe():
    """la fin commune d'un programme forgé par vtxc128 (sans zones, réglages ni noyaux) ; forge/queue_vtx.rs en est la
    copie que lugus embarque (lugus forger) : test_forge_vtx.py vérifie qu'elles restent les mêmes"""
    import forge128
    forge128.DRUIDE_NOMS[0], forge128.DRUIDE_OBS[0], forge128.CUBE_SUPPOSE[0] = [], [], []
    return "\n".join(forge128.queue_programme({}, [], [], []))


QUEUE = os.path.join(ici, "queue_vtx.rs")


def source_rust_vtx(src, dossier=None, nom="programme", sortie=None):
    """le programme Rust complet (noyau compris), ou (None, la raison)"""
    import forge128
    prog, mots = programme_rust_vtx(src, dossier, nom)
    if prog is None:
        return None, mots
    main = "\nfn main() {\n    let a: Vec<String> = std::env::args().collect();\n    lancer(&a[1..]);\n}\n"
    return forge128.noyau(sortie, nom) + "\n" + prog + main, mots


if __name__ == "__main__":
    # forge_vtx.py PROG.vtx : écrit PROG.vtx.rs (ou dit pourquoi l'ancienne forge garderait la main)
    # forge_vtx.py --queue : récrit forge/queue_vtx.rs (après un changement de forge128.queue_programme)
    sys.path.insert(0, ici)
    if sys.argv[1] == "--queue":
        open(QUEUE, "w", encoding="utf-8").write(queue_fixe() + "\n")
        print("forge/queue_vtx.rs récrit (puis : cargo build --release, lugus l'embarque)")
        sys.exit(0)
    p = sys.argv[1]
    code, m = source_rust_vtx(open(p, encoding="utf-8").read(), os.path.dirname(os.path.abspath(p)),
                              os.path.splitext(os.path.basename(p))[0])
    if code is None:
        print("forge en vtx : " + m)
        sys.exit(2)
    open(p + ".rs", "w", encoding="utf-8").write(code)
    print(f"forge en vtx : {p}.rs ({len(m)} mots)")
