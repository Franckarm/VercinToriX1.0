"""ScoR v1 (raisonnement) et v0 : mêmes mots par vtx.py et vtxc ; le rêve range les liaisons ; des réponses attendues ; inconnu honnête."""
import os, re, shutil, subprocess, sys, tempfile
ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
sys.path.insert(0, racine)
import vtx  # noqa: E402

rs = os.path.join(racine, "vtx-rs")
cible = os.environ.get("CARGO_TARGET_DIR") or os.path.join(rs, "target")
subprocess.run([shutil.which("cargo") or "cargo", "build", "--release", "-q"], cwd=rs, check=True)
VTX = os.path.join(cible, "release", "vtx" + (".exe" if os.name == "nt" else ""))

src = open(os.path.join(ici, "scor.vtx"), encoding="utf-8").read()
py = vtx.assembler(vtx.compiler(src, dossier=ici))
prog = os.path.join(ici, "_scor.prog")
subprocess.run([VTX, "compiler", os.path.join(ici, "scor.vtx"), prog], check=True, capture_output=True)
vc = [int(x) for x in open(prog).read().split(";")[0].split(",")]
os.remove(prog)
# le ScoR garde sa mémoire d'un lancement à l'autre : le test part d'une mémoire vide, dans un dossier à part
tmp = tempfile.mkdtemp()
# il lit un corpus figé (une copie des documents du 22 octobre 2026) : le test ne doit pas changer quand on écrit la
# documentation (une phrase neuve peut, à juste titre, rendre un mot « variable »)
shutil.copytree(ici, os.path.join(tmp, "scor"), ignore=shutil.ignore_patterns("scor.memoire*", "corpus_essai"))
shutil.copytree(os.path.join(ici, "corpus_essai", "docs"), os.path.join(tmp, "docs"))
shutil.copy(os.path.join(ici, "corpus_essai", "COMMENCER.md"), tmp)
dossier = os.path.join(tmp, "scor")
r = subprocess.run([VTX, "scor.vtx"], cwd=dossier, capture_output=True, text=True, encoding="utf-8",
                   input="le hérisson est piquant\n\n")
r2 = subprocess.run([VTX, "scor.vtx"], cwd=dossier, capture_output=True, text=True, encoding="utf-8",
                    input="le hérisson est-il piquant ?\n\n").stdout
shutil.rmtree(tmp, ignore_errors=True)
memoire = "mémoire rechargée" in r2 and "vrai : dit directement (1 fois)" in r2
print(f"ScoR : apprend en parlant et s'en souvient au lancement suivant : {'oui' if memoire else 'NON'}")
t = r.stdout
rapport = float(re.findall(r"rapport ([0-9.]+)", t)[-1])
prouves = sum(int(x) for x in re.findall(r"bilan : (\d+) réponses", t))
cases = [int(x) for x in re.findall(r"spirale : (\d+) cases", t)]
attendus = ["vrai : déduit : chat → mammifère (1) → animal (1) → vivant (1)",
            "faux : déduit : requin → poisson (1), et « poisson n'est pas mammifère » (1)",
            "faux : dit directement : « dauphin n'est pas poisson »",
            "exception, le fait le plus précis l'emporte",
            "vrai : déduit : moineau → oiseau (1) → volant (1)",
            "faux : déduit : arn → hypothèse (1), et « hypothèse n'est pas preuve » (1)",
            "variable : deux règles se contredisent : nixon → quaker",
            "« licorne » : jamais lu → inconnu"]
raisonne = all(a in t for a in attendus)
print(f"ScoR v1, raisonnement : {sum(a in t for a in attendus)}/{len(attendus)} conclusions attendues (déduction, négation, "
      f"exception, contradiction, inconnu)")
ok = (memoire and raisonne and py == vc and rapport < 0.3 and prouves >= 20 and "vrai  embarqué" in t and "« licorne » : jamais lu → inconnu" in t
      and t.count("→ anti-cube") >= 1 and max(cases) < 410)
print(f"ScoR v0 : mots {'identiques' if py == vc else 'DIFFÉRENTS'} ; rapport liés/hasard {rapport:.3f} ; {prouves}/56 réponses "
      f"appuyées par des phrases ; spirale : au plus {max(cases)} cases sur 4096 ; {'conforme' if ok else 'ÉCART'}")
sys.exit(0 if ok else 1)
