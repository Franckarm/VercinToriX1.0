import sys, subprocess, os
sys.path[:0]=[__import__('os').path.dirname(__import__('os').path.dirname(__import__('os').path.abspath(__file__))),__import__('os').path.dirname(__import__('os').path.dirname(__import__('os').path.abspath(__file__)))+'/spu64']
import vtx64
B=__import__('os').path.dirname(__import__('os').path.dirname(__import__('os').path.abspath(__file__)))+'/vtx-rs/target/release/vtx64'
for f in sys.argv[1:]:
    src=open(f,encoding='utf-8').read()
    try: m=vtx64.assembler(vtx64.compiler(src, dossier=os.path.dirname(f)))
    except Exception as e: m='ERR '+str(e)
    r=subprocess.run([B,'compiler',f,__import__('tempfile').gettempdir()+'/y.mots'],capture_output=True,text=True)
    if r.returncode==0 and os.path.exists(__import__('tempfile').gettempdir()+'/y.mots'):
        ml=[int(x) for x in open(__import__('tempfile').gettempdir()+'/y.mots').read().split(';')[0].split(',') if x.strip()]; os.remove(__import__('tempfile').gettempdir()+'/y.mots')
    else: ml='ERR '+(r.stdout+r.stderr).strip()[-200:]
    print(f,'MEMES' if m==ml else 'DIFF','' if m==ml else (str(m)[:150],str(ml)[:150]))
