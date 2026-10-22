import json
cands=[]
for line in open('/root/.claude/projects/-home-claude/b21cb473-61f1-580d-ba79-699e83f87bd3.jsonl'):
    try: d=json.loads(line)
    except: continue
    m=d.get('message',{})
    if m.get('role')!='assistant' or not isinstance(m.get('content'),list): continue
    for c in m['content']:
        if c.get('type')=='tool_use' and c.get('name')=='Bash':
            t=c['input'].get('command','')
            if 'fonction accord_segments' in t:
                cands.append(t)
print(len(cands), [len(c) for c in cands])
cmd=cands[-1]
i=cmd.index("python3 - <<'EOF'\n")+len("python3 - <<'EOF'\n"); j=cmd.index("\nEOF\n", i)
script=cmd[i:j]
a='''R("""    } sinon si g == N_DONNEES {""","""    } sinon si g == N_ACCORD {'''
assert a in script
script=script.replace(a,'''R("""    } sinon si g == N_DONNEES {
        soit dn = c.blocs;""","""    } sinon si g == N_ACCORD {''')
b='''    } sinon si g == N_BLOC {
        instrs(c, s.premier);
    } sinon si g == N_DONNEES {""")'''
assert b in script
script=script.replace(b,'''    } sinon si g == N_BLOC {
        instrs(c, s.premier);
    } sinon si g == N_DONNEES {
        soit dn = c.blocs;""")''')
open('patch_partition.py','w').write(script)