import re, json, collections, sys, os
from ged import parse
HERE=os.path.dirname(os.path.abspath(__file__))
if len(sys.argv)<2: sys.exit('usage: python3 tools/build.py path/to/tree.ged')
I,F=parse(sys.argv[1])
# --- merge duplicates ---
BEN='I262525321262'; I[BEN]['fams']=[f for f in I[BEN]['fams'] if f!='F117']   # F117 duplicates Schaje Ben + Ida (F215)
ISA='I262539792217'            # Isaac under Meyer-only family F572 -> move into Meyer+Chana F219
F['F219']['chil'].append(ISA); I[ISA]['famc']=['F219']
MEY=F['F219']['husb']; I[MEY]['fams']=[f for f in I[MEY]['fams'] if f!='F572']
DROP={'I262580014910','I262586324092','I262546144019'}          # Chana-only Isaac duplicate
ROOTS=[('V','I262798668669'),('P',F['F500']['husb'])]   # walk Vishnik first so Hymen sits under his father
def clean(n): return re.sub(r'\s+',' ',n.replace('/',' ')).strip()
def bad(s): return (not s) or set(s) <= set('?-– ')
def info(p):
    x=I[p]; g=lambda d,k: '' if bad(d.get(k,'')) else d.get(k,'')
    return {'id':p,'name':clean(x['name']) or 'Unknown','sex':x['sex'],'b':g(x['birt'],'date'),'bp':g(x['birt'],'plac'),'d':g(x['deat'],'date'),'dp':g(x['deat'],'plac')}
def yr(s):
    m=re.search(r'(\d{4})',s or ''); return int(m[1]) if m else 9999
seen={}; spouse_of=collections.defaultdict(list)
def walk(p,line):
    node=info(p); node['line']=line
    if p in seen:
        node['ref']=seen[p]; return node
    seen[p]=line
    fams=sorted([F[f] for f in I[p]['fams'] if f in F], key=lambda fm: 0 if 'first' in (I.get(fm['wife'] or '',{}).get('name','')+I.get(fm['husb'] or '',{}).get('name','')) else 1)
    node['sp']=[]; node['kids']=[]
    for i,fm in enumerate(fams):
        sp = fm['wife'] if fm['husb']==p else fm['husb']
        if sp and sp in I:
            s=info(sp); s['marr']=fm['marr'].get('date',''); s['fi']=i+1; node['sp'].append(s); spouse_of[sp].append(p)
        kids=sorted([c for c in fm['chil'] if c in I and c not in DROP], key=lambda c: yr(I[c]['birt'].get('date')))
        for c in kids:
            k=walk(c,line)
            if len(fams)>1: k['mi']=i+1
            node['kids'].append(k)
    return node
trees=[walk(r,l) for l,r in ROOTS]
trees=[trees[1],trees[0]]   # display Palatnik first
# "also married" notes for spouses who married two descendants
for sp,ps in spouse_of.items():
    if len(ps)>1:
        names=[clean(I[p]['name']) for p in ps]
        def ann(n):
            for s in n.get('sp',[]):
                if s['id']==sp: s['also']=[x for x in names if x!=n['name']]
            for k in n.get('kids',[]): ann(k)
        for t in trees: ann(t)
# duplicates check
cnt=collections.Counter()
def col(n):
    cnt[(n['name'],n['b'])]+=0 if n.get('ref') else 1
    for k in n.get('kids',[]): col(k)
for t in trees: col(t)
print('possible dup persons:',[k for k,v in cnt.items() if v>1])
nb=sum(cnt.values()); ns=len(spouse_of)
def depth(n): return 1+max([depth(k) for k in n.get('kids',[])]+[0])
print('descendants',nb,'spouses',ns,'gens',max(depth(t) for t in trees))
# --- privacy: hide dates and places of people who may be living ---
import datetime
CUTOFF=datetime.date.today().year-100
def byear(p):
    m=re.search(r'\d{4}',p.get('b','')); return int(m[0]) if m else None
def maybe_living(p,est):
    if p.get('d') or p.get('dp'): return False
    y=byear(p) or est
    return y is None or y>CUTOFF
LIVING_NAMES=set()
def scrub(p):
    LIVING_NAMES.add(p['name'])
    for k in ('b','bp','d','dp','marr'): p[k]=''
    p['name']='Living relative'
    p['living']=True
hidden=0
def priv(n,est):
    global hidden
    y=byear(n) or est
    if maybe_living(n,est): scrub(n); hidden+=1
    for s in n.get('sp',[]):
        if maybe_living(s,y): scrub(s); hidden+=1
        elif n.get('living'): s['marr']=''
    for k in n.get('kids',[]):
        priv(k,(y+25) if y else None)
for t in trees: priv(t,byear(t) or 1790)
def fix_also(n):
    for s in n.get('sp',[]):
        if s.get('also'): s['also']=['Living relative' if a in LIVING_NAMES else a for a in s['also']]
    for k in n.get('kids',[]): fix_also(k)
for t in trees: fix_also(t)
print('hidden details for',hidden,'possibly living people')
data=json.dumps(trees,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
tpl=open(os.path.join(HERE,'template.html'),encoding='utf-8').read()
open(os.path.join(HERE,'..','index.html'),'w',encoding='utf-8').write(tpl.replace('__DATA__',data))
print('wrote index.html')
