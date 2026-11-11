import subprocess, time, os
env = dict(os.environ, VTX_CONSOLE="1", VTX_SANS_PAUSE="1"); env.pop("JAVA_TOOL_OPTIONS", None)
envi = dict(env, VTX_INTERPRETE="1")
cas = [("C (gcc -O2)", ["./c64"], ["./c128"], env), ("Rust (-O)", ["./r64"], ["./r128"], env),
       ("Java", ["java", "Banc64"], ["java", "Banc128"], env),
       ("Lugus traduit", ["./l64"], ["./l128"], env), ("Lugus seul", ["./l64"], ["./l128"], envi),
       ("Python 3", ["python3", "banc.py", "64"], ["python3", "banc.py", "128"], env)]
def t(cmd, e, n):
    m = 1e9
    for _ in range(n):
        d = time.perf_counter(); subprocess.run(cmd, capture_output=True, env=e); m = min(m, time.perf_counter() - d)
    return m
for nom, a, b, e in cas:
    n = 2 if "Python" in nom or "128" in nom else 5
    print(f"{nom:15} 64 bits : {t(a, e, 5 if 'Python' not in nom else 2):7.3f} s   128 bits : {t(b, e, 3 if 'Python' not in nom else 2):7.3f} s", flush=True)
