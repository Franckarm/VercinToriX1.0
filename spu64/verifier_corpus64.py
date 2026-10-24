#!/usr/bin/env python3
"""Le corpus de conformité du SPU-64 : la machine Rust (vtx64) doit redonner chaque ligne attendue."""
import os
import subprocess
import sys

ici = os.path.dirname(os.path.abspath(__file__))
exe = os.path.join(os.path.dirname(ici), "vtx-rs", "target", "release", "vtx64" + (".exe" if os.name == "nt" else ""))
r = subprocess.run([exe, "corpus", os.path.join(ici, "corpus64.txt")], capture_output=True, text=True)
obtenu = r.stdout.strip("\n").split("\n")
attendu = open(os.path.join(ici, "corpus64_attendu.txt")).read().strip("\n").split("\n")
ec = [i for i, (a, b) in enumerate(zip(attendu, obtenu)) if a != b]
print(f"SPU-64 Rust : {len(attendu)} programmes, {len(ec) + abs(len(attendu) - len(obtenu))} écart(s)")
sys.exit(1 if ec or len(attendu) != len(obtenu) else 0)
