#!/usr/bin/env python3
"""Les cubes sur disque en miroir inversé : chaque cube rangé s'écrit avec son anti-cube (« anticube-… »), et la
relecture rend un état de Belnap (etat_disque()) : vrai (les deux s'accordent), faux (une seule copie lisible : réparée),
variable (les deux se contredisent), inconnu (rien).

Pour chaque machine (SPU-32 et SPU-64 ; Python et Rust) : un programme range un cube, un autre le relit, après
chaque sorte d'avarie : rien, la copie effacée, l'anti-copie effacée, la copie tronquée, un octet changé, les deux
effacées. On vérifie l'état rendu, les valeurs relues, et que la copie abîmée a été refaite.
"""
import os
import shutil
import subprocess
import sys
import tempfile

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, racine)
sys.path.insert(0, os.path.join(racine, "spu64"))
import vtx  # noqa: E402
import vtx64  # noqa: E402

ECRIRE32 = """fonction principal() {
    accorder(1, 42);
    pour i dans 0..1000 { @1[i * 97] = i * 3 + 1; }
    sortie(ranger_cube(1, 42));
}"""
LIRE32 = """fonction principal() {
    accorder(1, 42);
    soit s = 0;
    pour i dans 0..1000 { s = s + @1[i * 97]; }
    sortie(entier(etat_disque()));
    sortie(s);
}"""
ECRIRE64 = """fonction principal() {
    soit d = cube_adresse(1, 42, 0);
    pour i dans 0..1000 { @[d + i * 97] = i * 3 + 1; }
    sortie(ranger_cube(1, 42));
}"""
LIRE64 = """fonction principal() {
    soit d = cube_adresse(1, 42, 0);
    soit s = 0;
    pour i dans 0..1000 { s = s + @[d + i * 97]; }
    sortie(entier(etat_disque()));
    sortie(s);
}"""
SOMME = sum(i * 3 + 1 for i in range(1000))

cargo = shutil.which("cargo")
VTX = VTX64 = None
if cargo:
    rs = os.path.join(racine, "vtx-rs")
    cible = os.environ.get("CARGO_TARGET_DIR") or os.path.join(rs, "target")
    subprocess.run([cargo, "build", "--release", "-q"], cwd=rs, check=True)
    ext = ".exe" if os.name == "nt" else ""
    VTX, VTX64 = os.path.join(cible, "release", "vtx" + ext), os.path.join(cible, "release", "vtx64" + ext)


def lancer(machine, src, d):
    """Exécute src dans le dossier d sur la machine (py32, rs32, py64, rs64) ; rend les sorties."""
    if machine == "py32":
        cpu = vtx.CPU()
        cpu.dossier_fichiers = d
        cpu.charger(vtx.assembler(vtx.compiler(src)))
        cpu.executer(50_000_000)
        return list(cpu.sortie)
    if machine == "py64":
        return list(vtx64.executer(src, (), max_pas=50_000_000, dossier=d)[0].sortie)
    p = os.path.join(d, "p.vtx")
    with open(p, "w", encoding="utf-8") as f:
        f.write(src)
    r = subprocess.run([VTX if machine == "rs32" else VTX64, "p.vtx"], cwd=d, capture_output=True, text=True)
    lignes = [x for x in r.stdout.strip().split("\n") if x]
    return [int(x) for x in lignes[-1].split(",")] if lignes else []


def avarie(d, nom, genre):
    p, a = os.path.join(d, nom), os.path.join(d, "anti" + nom)
    if genre == "copie effacée":
        os.remove(p)
    elif genre == "anti-copie effacée":
        os.remove(a)
    elif genre == "copie tronquée":
        b = open(p, "rb").read()
        open(p, "wb").write(b[:len(b) // 2])
    elif genre == "un octet changé":
        b = bytearray(open(p, "rb").read())
        b[8 + 4 + 97 * 4 * 5] ^= 0x10
        open(p, "wb").write(bytes(b))
    elif genre == "les deux effacées":
        os.remove(p)
        os.remove(a)


CAS = [("intact", 2, True), ("copie effacée", 1, True), ("anti-copie effacée", 1, True), ("copie tronquée", 1, True),
       ("un octet changé", 3, False), ("les deux effacées", 0, None)]
machines = ["py32", "py64"] + (["rs32", "rs64"] if cargo else [])
ok = total = 0
for m in machines:
    m64 = m.endswith("64")
    nom = "cube64-1-42.cub" if m64 else "cube-1-42.cub"
    bilan = []
    for genre, etat_attendu, valeurs_justes in CAS:
        d = tempfile.mkdtemp(prefix="miroir-")
        lancer(m, ECRIRE64 if m64 else ECRIRE32, d)
        present = os.path.exists(os.path.join(d, nom)) and os.path.exists(os.path.join(d, "anti" + nom))
        avarie(d, nom, genre)
        s = lancer(m, LIRE64 if m64 else LIRE32, d)
        etat, somme = (s + [None, None])[:2]
        bon = present and etat == etat_attendu
        if valeurs_justes is True:
            bon = bon and somme == SOMME
        elif valeurs_justes is None:
            bon = bon and somme == 0
        if etat_attendu == 1:
            # réparé : les deux copies sont refaites, et une seconde lecture les trouve d'accord
            s2 = lancer(m, LIRE64 if m64 else LIRE32, d)
            bon = bon and s2[:1] == [2] and s2[1:2] == [SOMME]
        bilan.append(f"{genre} → {['inconnu', 'faux', 'vrai', 'variable'][etat] if etat is not None else '?'}"
                     + ("" if bon else " (ÉCHEC)"))
        ok += bon
        total += 1
        shutil.rmtree(d, ignore_errors=True)
    print(f"{m} : " + " ; ".join(bilan))
print(f"Miroir inversé : {ok}/{total} " + ("conforme" if ok == total else "ÉCHEC"))
sys.exit(0 if ok == total else 1)
