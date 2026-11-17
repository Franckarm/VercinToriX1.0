import sys, subprocess
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.dirname(__import__('os').path.abspath(__file__))))
import vtx128
vtx128.COMPAT_64 = False
L = __import__('os').path.dirname(__import__('os').path.dirname(__import__('os').path.abspath(__file__)))+'/vtx-rs/target/release/lugus'
for f in sys.argv[1:]:
    src = open(f, encoding='utf-8').read()
    import os
    d = os.path.dirname(f)
    try:
        m, _ = vtx128.assembler(vtx128.compiler(src, dossier=d), True)
    except Exception as e:
        m = 'ERR ' + str(e)
    r = subprocess.run([L, 'compiler', f, __import__('tempfile').gettempdir()+'/x.mots'], capture_output=True, text=True)
    if r.returncode == 0 and os.path.exists(__import__('tempfile').gettempdir()+'/x.mots'):
        ml = [int(x) for x in open(__import__('tempfile').gettempdir()+'/x.mots').read().split(";")[0].split(",") if x]
        os.remove(__import__('tempfile').gettempdir()+'/x.mots')
    else:
        ml = 'ERR ' + (r.stdout + r.stderr).strip()[-200:]
    print(f, 'MEMES' if m == ml else 'DIFF', '' if m == ml else (str(m)[:150], str(ml)[:150]))
