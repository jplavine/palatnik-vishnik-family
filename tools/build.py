"""Build the family tree.

  python3 tools/build.py TREE.ged                    writes index.html (living relatives hidden)
  python3 tools/build.py TREE.ged --full OUT.json    also writes every name and date to OUT.json

Additions that are not in the Ancestry export live in private/additions.json (not committed).
"""
import re, json, collections, sys, os, datetime
from ged import parse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
args = sys.argv[1:]
if not args: sys.exit(__doc__)
full_out = None
if '--full' in args:
    i = args.index('--full'); full_out = args[i + 1]; del args[i:i + 2]
I, F = parse(args[0])

# --- merge duplicate records found in the Ancestry export ---
# Ancestry renumbers family records on every export, so families are found by the people in them.
def find_fam(a, b=None):
    for f in I[a]['fams']:
        fm = F[f]; other = fm['wife'] if fm['husb'] == a else fm['husb']
        if other == b: return f
    return None
BEN, IDA2 = 'I262525321262', 'I262545607073'          # Benjamin + second Ida record duplicate Schaje Ben + Ida
dup = find_fam(BEN, IDA2)
I[BEN]['fams'] = [f for f in I[BEN]['fams'] if f != dup]
ISA, MEY, CHANA = 'I262539792217', 'I262525318449', 'I262525318450'   # Isaac: move into Meyer + Chana
solo = find_fam(MEY, None); main = find_fam(MEY, CHANA)
F[main]['chil'].append(ISA); I[ISA]['famc'] = [main]
I[MEY]['fams'] = [f for f in I[MEY]['fams'] if f != solo]
DROP = {'I262580014910', 'I262586324092', 'I262546144019'}

# --- private additions (family corrections not yet in Ancestry) ---
for i in I.values(): i['extra'] = {}
FAM_HOME = {}
add_path = os.path.join(ROOT, 'private', 'additions.json')
if os.path.exists(add_path):
    A = json.load(open(add_path, encoding='utf-8'))
    for old, new in A.get('merge_person', {}).items():
        for f in I[old]['fams']:
            fm = F[f]
            if fm['husb'] == old: fm['husb'] = new
            if fm['wife'] == old: fm['wife'] = new
            if f not in I[new]['fams']: I[new]['fams'].append(f)
        del I[old]
    for pid, name in A.get('rename', {}).items(): I[pid]['literal'] = name
    for a, b2 in A.get('drop_family', []):
        f = find_fam(a, b2)
        if f:
            for q in (F[f]['husb'], F[f]['wife']):
                if q: I[q]['fams'] = [x for x in I[q]['fams'] if x != f]
            for c in F[f]['chil']: DROP.add(c)
            if a in I and b2 not in (a,): DROP.add(b2)
            del F[f]
    for h in A.get('family_home', []):
        f = find_fam(*h['couple'])
        if f: FAM_HOME[f] = h['home']
    resolve = lambda f: find_fam(*f) if isinstance(f, list) else f
    for fam in A.get('families', []):
        F[fam['id']] = {'id': fam['id'], 'husb': fam.get('husb'), 'wife': fam.get('wife'), 'chil': [], 'marr': {}}
        for k in ('husb', 'wife'):
            if fam.get(k) and fam[k] in I: I[fam[k]]['fams'].append(fam['id'])
    for p in A.get('people', []):
        pid = p['id']
        I[pid] = {'id': pid, 'name': p['name'], 'sex': p.get('sex', ''), 'famc': [], 'fams': [],
                  'birt': {k: v for k, v in (('date', p.get('b')), ('plac', p.get('bp'))) if v},
                  'deat': {k: v for k, v in (('date', p.get('d')), ('plac', p.get('dp'))) if v},
                  'extra': {k: p[k] for k in ('note', 'fate', 'deceased', 'step', 'assume_living') if k in p}}
        I[pid]['extra'].setdefault('assume_living', True)
        for fam in A.get('families', []):
            if pid in (fam.get('husb'), fam.get('wife')) and fam['id'] not in I[pid]['fams']: I[pid]['fams'].append(fam['id'])
        if 'spouse_of' in p:
            other = p['spouse_of']
            fam = resolve(p.get('family')) or next((f for f in I[other]['fams'] if not (F[f]['husb'] and F[f]['wife'])), None)
            if not fam:
                fam = 'AF_' + pid; F[fam] = {'id': fam, 'husb': None, 'wife': None, 'chil': [], 'marr': {}}
                I[other]['fams'].append(fam)
            slot = 'wife' if F[fam]['husb'] == other else 'husb'
            F[fam][slot] = pid; I[pid]['fams'].append(fam)
        if 'parent' in p:
            par = p['parent']
            fam = resolve(p.get('family')) or (I[par]['fams'][0] if I[par]['fams'] else None)
            if not fam:
                fam = 'AF_' + par; F[fam] = {'id': fam, 'husb': par if I[par]['sex'] != 'F' else None,
                                           'wife': par if I[par]['sex'] == 'F' else None, 'chil': [], 'marr': {}}
                I[par]['fams'].append(fam)
            F[fam]['chil'].append(pid); I[pid]['famc'] = [fam]
    for pid, extra in A.get('set', {}).items():
        for k in ('b', 'bp', 'd', 'dp'):
            if k in extra: I[pid]['birt' if k[0] == 'b' else 'deat']['date' if len(k) == 1 else 'plac'] = extra[k]
        I[pid]['extra'].update({k: v for k, v in extra.items() if k in ('note', 'fate', 'deceased')})

ROOTS = [('V', 'I262798668669'), ('P', 'I262539792216')]   # walk Vishnik first so Hymen sits under his father
def clean(n): return re.sub(r'\s+', ' ', n.replace('/', ' ')).strip()
def bad(s): return (not s) or set(s) <= set('?-– ')
def info(p):
    x = I[p]; g = lambda d, k: '' if bad(d.get(k, '')) else d.get(k, '')
    out = {'id': p, 'name': x.get('literal') or clean(x['name']) or 'Unknown', 'sex': x['sex'], 'b': g(x['birt'], 'date'), 'bp': g(x['birt'], 'plac'),
           'd': g(x['deat'], 'date'), 'dp': g(x['deat'], 'plac')}
    out.update(x.get('extra', {}))
    return out
def yr(s):
    m = re.search(r'(\d{4})', s or ''); return int(m[1]) if m else 9999

seen = {}; spouse_of = collections.defaultdict(list)
def walk(p, line):
    node = info(p); node['line'] = line
    if p in seen:
        node['ref'] = seen[p]; return node
    seen[p] = line
    fams = sorted([F[f] for f in I[p]['fams'] if f in F],
                  key=lambda fm: 0 if 'first' in (I.get(fm['wife'] or '', {}).get('name', '') + I.get(fm['husb'] or '', {}).get('name', '')) else 1)
    with_sp = [fm for fm in fams if (fm['wife'] if fm['husb'] == p else fm['husb']) in I]
    node['sp'] = []; node['kids'] = []
    for i, fm in enumerate(fams):
        sp = fm['wife'] if fm['husb'] == p else fm['husb']
        if sp and sp in I:
            s = info(sp); s['marr'] = fm['marr'].get('date', ''); s['fi'] = i + 1; node['sp'].append(s); spouse_of[sp].append(p)
        home = FAM_HOME.get(fm['id'])
        if home and home != p:
            node['kidsAt'] = home
            continue
        kids = sorted([c for c in fm['chil'] if c in I and c not in DROP], key=lambda c: yr(I[c]['birt'].get('date')))
        for c in kids:
            k = walk(c, line)
            k['fi'] = i + 1
            if len(with_sp) > 1 and sp in I: k['mi'] = i + 1
            node['kids'].append(k)
    return node

trees = [walk(r, l) for l, r in ROOTS]
trees = [trees[1], trees[0]]   # display Palatnik first

# "also married" notes for spouses who married two descendants
for sp, ps in spouse_of.items():
    if len(ps) > 1:
        names = [I[p].get('literal') or clean(I[p]['name']) for p in ps]
        def ann(n):
            for s in n.get('sp', []):
                if s['id'] == sp: s['also'] = [x for x in names if x != n['name']]
            for k in n.get('kids', []): ann(k)
        for t in trees: ann(t)

cnt = collections.Counter()
def col(n):
    cnt[(n['name'], n['b'])] += 0 if (n.get('ref') or n.get('step')) else 1
    for k in n.get('kids', []): col(k)
for t in trees: col(t)
print('possible dup persons:', [k for k, v in cnt.items() if v > 1])
def depth(n): return 1 + max([depth(k) for k in n.get('kids', [])] + [0])
print('descendants', sum(cnt.values()), 'spouses', len(spouse_of), 'gens', max(depth(t) for t in trees))

if full_out:
    json.dump(trees, open(full_out, 'w', encoding='utf-8'), ensure_ascii=False)
    print('wrote', full_out)

# --- privacy: hide names, dates and places of people who may be living ---
CUTOFF = datetime.date.today().year - 100
def byear(p):
    m = re.search(r'\d{4}', p.get('b', '')); return int(m[0]) if m else None
def maybe_living(p, est):
    if p.get('d') or p.get('dp') or p.get('fate') or p.get('deceased'): return False
    if p.get('assume_living'): return True
    y = byear(p) or est
    return y is None or y > CUTOFF
LIVING_NAMES = set()
def scrub(p):
    LIVING_NAMES.add(p['name'])
    for k in ('b', 'bp', 'd', 'dp', 'marr', 'note'): p[k] = ''
    p['name'] = 'Living relative'
    p['living'] = True
hidden = 0
def priv(n, est):
    global hidden
    y = byear(n) or est
    if maybe_living(n, est): scrub(n); hidden += 1
    for s in n.get('sp', []):
        if maybe_living(s, y): scrub(s); hidden += 1
        elif n.get('living'): s['marr'] = ''
    kids = n.get('kids', [])
    known = [byear(k) for k in kids if byear(k)]
    kid_est = round(sum(known) / len(known)) if known else ((y + 25) if y else None)
    for k in kids: priv(k, kid_est)
for t in trees: priv(t, byear(t) or 1790)
def fix_also(n):
    for s in n.get('sp', []):
        if s.get('also'): s['also'] = ['Living relative' if a in LIVING_NAMES else a for a in s['also']]
    for k in n.get('kids', []): fix_also(k)
for t in trees: fix_also(t)
print('hidden details for', hidden, 'possibly living people')
data = json.dumps(trees, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
tpl = open(os.path.join(HERE, 'template.html'), encoding='utf-8').read()
open(os.path.join(ROOT, 'index.html'), 'w', encoding='utf-8').write(tpl.replace('__DATA__', data))
print('wrote index.html')
