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
    for pid in A.get('drop_person', []):   # duplicate records to leave out
        DROP.add(pid)
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

# Four views: Sarah (Sura) Sokolov, Pinchas (Pincus) Palat, Asher Zelig Veshnack, and the wider family.
SARAH, PINCUS, ASHER, HYMEN = 'I262525311332', 'I262525311317', 'I262525318130', 'I262525317573'
# Hymen is Asher's son; Ancestry also lists him in Pincus + Sarah's family.
f = find_fam(PINCUS, SARAH)
if f and HYMEN in F[f]['chil']:
    F[f]['chil'].remove(HYMEN); I[HYMEN]['famc'] = [x for x in I[HYMEN]['famc'] if x != f]
def oldest(p):   # climb to the earliest recorded ancestor through the father's line
    seen = set()
    while I[p]['famc'] and p not in seen:
        seen.add(p); fm = F.get(I[p]['famc'][0])
        nxt = fm and (fm['husb'] or fm['wife'])
        if not nxt or nxt not in I: break
        p = nxt
    return p
WIDER = [('S', oldest('I262525318119')), ('P', oldest('I262539792216')), ('V', oldest('I262798668669'))]

def clean(n): return re.sub(r'\s+', ' ', n.replace('/', ' ')).strip()
def bad(s): return (not s) or set(s) <= set('?-– ')
def info(p):
    x = I[p]; g = lambda d, k: '' if bad(d.get(k, '')) else d.get(k, '')
    out = {'id': p, 'name': x.get('literal') or clean(x['name']) or 'Unknown', 'sex': x['sex'], 'b': g(x['birt'], 'date'), 'bp': g(x['birt'], 'plac'),
           'd': g(x['deat'], 'date'), 'dp': g(x['deat'], 'plac')}
    if x['deat'].get('_y') and not out['d'] and not out['dp']: out['deceased'] = True
    out.update(x.get('extra', {}))
    return out
def yr(s):
    m = re.search(r'(\d{4})', s or ''); return int(m[1]) if m else 9999

spouse_of = collections.defaultdict(set)
def make_walker(home_map):
    def walk(p, line):
        node = info(p); node['line'] = line
        shared = collections.Counter(c for f in I[p]['fams'] if f in F for c in F[f]['chil'])
        def fam_order(fm):   # order marriages by their earliest child found only in that marriage
            first = 'first' in (I.get(fm['wife'] or '', {}).get('name', '') + I.get(fm['husb'] or '', {}).get('name', ''))
            return (0 if first else 1, min([yr(I[c]['birt'].get('date')) for c in fm['chil'] if c in I and shared[c] == 1] + [9999]))
        fams = sorted([F[f] for f in I[p]['fams'] if f in F], key=fam_order)
        with_sp = [fm for fm in fams if (fm['wife'] if fm['husb'] == p else fm['husb']) in I]
        node['sp'] = []; node['kids'] = []; listed = set()
        if p == SARAH: node['lead'] = True
        for i, fm in enumerate(fams):
            sp = fm['wife'] if fm['husb'] == p else fm['husb']
            if sp and sp in I:
                s = info(sp); s['marr'] = fm['marr'].get('date', ''); s['mp'] = fm['marr'].get('plac', ''); s['fi'] = i + 1; node['sp'].append(s); spouse_of[sp].add(p)
            home = home_map.get(fm['id'])
            if home and home != p:
                node['kidsAt'] = home
                continue
            kids = sorted([c for c in fm['chil'] if c in I and c not in DROP], key=lambda c: yr(I[c]['birt'].get('date')))
            for c in kids:
                if c in listed: continue          # same child recorded in two of this person's families
                listed.add(c)
                k = walk(c, line)
                k['fi'] = i + 1
                if len(with_sp) > 1 and sp in I: k['mi'] = i + 1
                node['kids'].append(k)
        return node
    return walk

views = {
    'sarah':   [make_walker({})(SARAH, 'S')],
    'pinchas': [make_walker({})(PINCUS, 'P')],
    'asher':   [make_walker({})(ASHER, 'V')],
}
w = make_walker({})   # children appear in full under every parent, even when that repeats them
views['wider'] = [w(r, l) for l, r in WIDER]
ALL = [t for ts in views.values() for t in ts]
def nodes(n):
    yield n
    for k in n.get('kids', []): yield from nodes(k)

# "also married" notes for spouses who married two descendants (Sarah)
for sp, ps in spouse_of.items():
    if len(ps) > 1:
        names = [I[p].get('literal') or clean(I[p]['name']) for p in ps]
        for t in ALL:
            for n in nodes(t):
                for s in n.get('sp', []):
                    if s['id'] == sp: s['also'] = [x for x in names if x != n['name']]

# cross-overs: spouses who are themselves descendants (Yankl and Chaya, Sarah's husbands)
blood = {n['id'] for t in views['wider'] for n in nodes(t) if not n.get('ref')}
for t in ALL:
    for n in nodes(t):
        for s in n.get('sp', []):
            if s['id'] in blood: s['cross'] = True

# in-law links: spouses who are siblings of other spouses (Pearl Goodman and Sanya Gutman)
spouse_ids = {s['id'] for t in ALL for n in nodes(t) for s in n.get('sp', [])}
def siblings(p):
    return {c for f in I[p]['famc'] if f in F for c in F[f]['chil'] if c != p}
for t in ALL:
    for n in nodes(t):
        for s in n.get('sp', []):
            sibs = [x for x in siblings(s['id']) if x in spouse_ids]
            if sibs:
                rel = {'F': 'Sister', 'M': 'Brother'}.get(I[s['id']]['sex'], 'Sibling')
                s['sib'] = rel + ' of ' + ', '.join(I[x].get('literal') or clean(I[x]['name']) for x in sibs)
                s['sibNames'] = [I[x].get('literal') or clean(I[x]['name']) for x in sibs]

for name, ts in views.items():
    ids = {n['id'] for t in ts for n in nodes(t)}
    print(f"{name:8s} people {len(ids):4d}")

out = {'views': views, 'sarah_parents': [info(x) for x in (F[I[SARAH]['famc'][0]]['husb'], F[I[SARAH]['famc'][0]]['wife']) if x],
       'sarah_siblings': [info(c) for c in F[I[SARAH]['famc'][0]]['chil'] if c != SARAH]}
if full_out:
    json.dump(out, open(full_out, 'w', encoding='utf-8'), ensure_ascii=False)
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
LIVING = set()
def decide(n, est):   # pass 1: anyone judged possibly living in any view is hidden in every view
    y = byear(n) or est
    if maybe_living(n, est): LIVING.add(n['id'])
    for s in n.get('sp', []):
        if maybe_living(s, y): LIVING.add(s['id'])
    kids = n.get('kids', [])
    known = [byear(k) for k in kids if byear(k)]
    kid_est = round(sum(known) / len(known)) if known else ((y + 25) if y else None)
    for k in kids: decide(k, kid_est)
for t in ALL: decide(t, byear(t) or 1790)
LIVING_NAMES = set()
def scrub(p):
    LIVING_NAMES.add(p['name'])
    for k in ('b', 'bp', 'd', 'dp', 'marr', 'mp', 'note'): p[k] = ''
    p['name'] = 'Living relative'
    p['living'] = True
for t in ALL:
    for n in nodes(t):
        if n['id'] in LIVING: scrub(n)
        for s in n.get('sp', []):
            if s['id'] in LIVING: scrub(s)
            elif n.get('living'): s['marr'] = ''; s['mp'] = ''
for t in ALL:
    for n in nodes(t):
        for s in n.get('sp', []):
            if s.get('also'): s['also'] = ['Living relative' if a in LIVING_NAMES else a for a in s['also']]
            if s.get('sib') and (s.get('living') or any(x in LIVING_NAMES for x in s.get('sibNames', []))): s.pop('sib')
            s.pop('sibNames', None)
for x in out['sarah_siblings']:
    if x['id'] in LIVING: scrub(x)
print('hidden details for', len(LIVING), 'possibly living people')
data = json.dumps(out, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
tpl = open(os.path.join(HERE, 'template.html'), encoding='utf-8').read()
open(os.path.join(ROOT, 'index.html'), 'w', encoding='utf-8').write(tpl.replace('__DATA__', data))
print('wrote index.html')

# --- towns page: family members born in Teplyk and Zhabokrych (built from the privacy-safe data) ---
import html as _html
def year_txt(s):
    m = re.search(r'\d{4}', s or '')
    if not m: return ''
    return ('c. ' if re.search(r'abt|about|circa|est', s, re.I) else 'bef. ' if re.search(r'bef', s, re.I) else '') + m[0]
people = {}
def gather(n, parent):
    if not n.get('living'):
        if n['id'] not in people or people[n['id']][1] == 'spouse':
            if parent:
                other = next((s for s in parent.get('sp', []) if s.get('fi') == n.get('fi')), None)
                rel = 'Child of ' + parent['name'] + (' and ' + other['name'] if other and not other.get('living') else '')
            else:
                rel = ''
            people[n['id']] = (n, 'desc', rel)
    for s in n.get('sp', []):
        if not s.get('living') and s['id'] not in people:
            people[s['id']] = (s, 'spouse', 'Married ' + n['name'])
    for k in n.get('kids', []): gather(k, n)
for t in out['views']['wider']: gather(t, None)
def born_in(pat):
    rows = [v for v in people.values() if re.search(pat, v[0].get('bp') or '', re.I)]
    rows.sort(key=lambda v: (yr(v[0].get('b')), v[0]['name']))
    li = []
    for n, kind, rel in rows:
        yrs = year_txt(n.get('b'))
        d = year_txt(n.get('d'))
        span = (yrs + ('–' + d if d else '')) if yrs else ('d. ' + d if d else '')
        cls = 'nm lead' if n.get('lead') else 'nm'
        li.append(f'<li><span class="yr">{_html.escape(span)}</span><span><span class="{cls}">{_html.escape(n["name"])}</span>'
                  + (f'<span class="rel">{_html.escape(rel)}</span>' if rel else '') + '</span></li>')
    return len(rows), ''.join(li)
tc, tl = born_in(r'tepl[iy]k'); zc, zl = born_in(r'zhabokry?i?ch')
tt = open(os.path.join(HERE, 'towns_template.html'), encoding='utf-8').read()
tt = tt.replace('__TEPLYK_COUNT__', str(tc)).replace('__TEPLYK_LIST__', tl).replace('__ZHAB_COUNT__', str(zc)).replace('__ZHAB_LIST__', zl)
open(os.path.join(ROOT, 'towns.html'), 'w', encoding='utf-8').write(tt)
print('wrote towns.html', tc, 'born in Teplyk,', zc, 'in Zhabokrych')
