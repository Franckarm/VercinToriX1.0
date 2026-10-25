"""Fiche des performances : les mêmes algorithmes en vtx (trois façons de le faire tourner) et en C, Rust, Go, Java,
JavaScript, Python. Chaque programme est construit d'abord (non chronométré), puis lancé R fois ; on garde la médiane
du temps réel, lancement du processus compris. Le résultat de chaque programme est comparé à celui du C."""
import json, os, statistics, subprocess, sys, time
ICI = os.path.dirname(os.path.abspath(__file__)); S = os.path.join(ICI, "src")
V = "/home/claude/essai/vtx-0.5/vtx-rs/target/release"
R = int(sys.argv[1]) if len(sys.argv) > 1 else 3
BENCH = ["fib", "crible", "mandel", "tri", "adn"]
JAVA = {"fib": "Fib", "crible": "Crible", "mandel": "Mandel", "tri": "Tri", "adn": "Adn"}

def lancer(cmd, cwd=S, limite=600):
    t = time.perf_counter()
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=limite)
    d = time.perf_counter() - t
    sortie = [l for l in r.stdout.strip().split("\n") if l]
    return d, (sortie[-1] if sortie else "") , r.returncode

def construire(b):
    c = {}
    subprocess.run(["gcc", "-O2", "-o", f"{b}.gcc", f"{b}.c"], cwd=S, check=True)
    c["C (gcc -O2)"] = [f"./{b}.gcc"]
    if b == "adn":
        subprocess.run(["gcc", "-O2", "-o", "adn_expert.gcc", "adn_expert.c"], cwd=S, check=True)
        c["C, écrit par un expert (16 bases par mot)"] = ["./adn_expert.gcc"]
    subprocess.run(["rustc", "-O", "-o", f"{b}.rust", f"{b}.rs"], cwd=S, check=True, capture_output=True)
    c["Rust (rustc -O)"] = [f"./{b}.rust"]
    subprocess.run(["go", "build", "-o", f"{b}.go.exe", f"go/{b}.go"], cwd=S, check=True)
    c["Go"] = [f"./{b}.go.exe"]
    c["Java"] = ["java", "-cp", "java", JAVA[b]]
    c["JavaScript (Node)"] = ["node", f"{b}.js"]
    c["Python 3"] = ["python3", f"{b}.py"]
    subprocess.run([f"{V}/vtx", "compiler", f"{b}.vtx", f"{b}.prog"], cwd=S, check=True, capture_output=True)
    c["vtx, SPU-32 émulé (vtx.exe)"] = [f"{V}/vtx-spu", "lancer", f"{b}.prog", "18446744073709551615"]
    subprocess.run([f"{V}/vtx", "traduire", f"{b}.vtx", f"{b}.natif"], cwd=S, check=True, capture_output=True)
    c["vtx, traduit en code natif"] = [f"./{b}.natif"]
    subprocess.run(["python3", "/home/claude/essai/vtx-0.5/forge/forge.py", f"{b}.vtx", "-o", f"{b}.forge"], cwd=S, check=True, capture_output=True)
    c["vtx, forgé (forge → Rust → natif)"] = [f"./{b}.forge"]
    subprocess.run([f"{V}/vtx64", "compiler", f"{b}.vtx", f"{b}.mots64"], cwd=S, check=True, capture_output=True)
    c["vtx, SPU-64 émulé (vtx64.exe)"] = [f"{V}/vtx64", "lancer", f"{b}.mots64"]
    return c

res = {}
for b in BENCH:
    res[b] = {}
    cmds = construire(b)
    ref = None
    for nom, cmd in cmds.items():
        temps, sortie = [], ""
        for k in range(R):
            try:
                d, sortie, code = lancer(cmd)
            except subprocess.TimeoutExpired:
                d, sortie = float("nan"), "trop long"
            temps.append(d)
            if d > 60:
                break
        if ref is None:
            ref = sortie
        res[b][nom] = {"s": statistics.median(temps), "resultat": sortie, "juste": sortie == ref}
        print(f"{b:8s} {nom:45s} {statistics.median(temps):8.3f} s  {sortie}{'' if sortie == ref else '  (différent)'}", flush=True)
json.dump(res, open(os.path.join(ICI, "mesures.json"), "w"), ensure_ascii=False, indent=1)
