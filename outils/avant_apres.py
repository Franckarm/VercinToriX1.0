# usage : git show HEAD:vtx128.py > /tmp/vieux128.py ; python3 outils/avant_apres.py 128 /tmp/vieux128.py (ou 64 et vtx64.py)
import sys, glob, os, importlib.util
R=__import__('os').path.dirname(__import__('os').path.dirname(__import__('os').path.abspath(__file__)))
sys.path[:0]=[R, R+'/spu64', R+'/spu128']
def charger(nom, chemin):
    spec=importlib.util.spec_from_file_location(nom, chemin); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
machine=sys.argv[1]
if machine=='128':
    import vtx128 as neuf; vieux=charger('v128', sys.argv[2])
    for m in (neuf, vieux): m.COMPAT_64=False
    asm=lambda m,a: m.assembler(a, True)[0]
else:
    import vtx64 as neuf; vieux=charger('v64', sys.argv[2])
    asm=lambda m,a: m.assembler(a)
fics=[]
for d in ('exemples128','exemples64','tests','bibliotheque','exemples/premiers','exemples','chimie','gobannos','belenos','tests/gobannos','tests/nombres'):
    fics+=sorted(glob.glob(R+'/'+d+'/*.vtx'))
n=d_=e=0
for f in fics:
    src=open(f,encoding='utf-8').read(); res=[]
    for m in (vieux, neuf):
        try: res.append(asm(m, m.compiler(src, dossier=os.path.dirname(f))))
        except Exception as ex: res.append('ERR '+str(ex)[:80])
    if isinstance(res[0],str): e+=1; continue
    n+=1
    if res[0]!=res[1]: d_+=1; print('CHANGÉ', f.replace(R+'/',''), str(res[1])[:90])
print(machine, n,'programmes compilés par l ancien,', d_,'changés ;', e, 'refusés par l ancien')
