import re, json
def parse(path):
    indi, fam = {}, {}
    cur = None; kind = None; ev = None
    for raw in open(path, encoding='utf-8-sig'):
        line = raw.rstrip('\r\n')
        m = re.match(r'^(\d+)\s+(?:(@[^@]+@)\s+)?(\S+)\s?(.*)$', line)
        if not m: continue
        lvl, xref, tag, val = int(m[1]), m[2], m[3], m[4]
        if lvl == 0:
            ev = None
            if tag == 'INDI':
                cur = indi.setdefault(xref.strip('@'), {'id': xref.strip('@'), 'name':'', 'sex':'', 'birt':{}, 'deat':{}, 'famc':[], 'fams':[]}); kind='I'
            elif tag == 'FAM':
                cur = fam.setdefault(xref.strip('@'), {'id': xref.strip('@'), 'husb':None, 'wife':None, 'chil':[], 'marr':{}}); kind='F'
            else:
                cur = None; kind=None
            continue
        if cur is None: continue
        if lvl == 1:
            ev = tag
            if kind == 'I':
                if tag == 'NAME' and not cur['name']: cur['name'] = val
                elif tag == 'SEX': cur['sex'] = val
                elif tag == 'FAMC': cur['famc'].append(val.strip('@'))
                elif tag == 'FAMS': cur['fams'].append(val.strip('@'))
            else:
                if tag == 'HUSB': cur['husb'] = val.strip('@')
                elif tag == 'WIFE': cur['wife'] = val.strip('@')
                elif tag == 'CHIL': cur['chil'].append(val.strip('@'))
        elif lvl == 2 and tag in ('DATE','PLAC'):
            key = {'BIRT':'birt','DEAT':'deat','MARR':'marr'}.get(ev)
            if key and key in cur and tag.lower() not in cur[key]:
                cur[key][tag.lower()] = val
    return indi, fam
