"""Read Temu's own rules and patch only populated data cells in the original ZIP.
No Excel reserialization: dropdowns, names, conditional formats, images and hidden
sheets remain byte-for-byte identical. All XML inputs are local trusted templates.
"""
import copy
import re
import zipfile
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
def col(ref): return re.sub(r'\d+$', '', ref)
def number(c):
    n = 0
    for x in c: n = n * 26 + ord(x) - 64
    return n

class Template:
    def __init__(self, path):
        self.path = path
        with zipfile.ZipFile(path) as z:
            ss = ET.fromstring(z.read('xl/sharedStrings.xml')) if 'xl/sharedStrings.xml' in z.namelist() else []
            strings = [''.join(n.itertext()) for n in ss]
            rels = {r.get('Id'): r.get('Target') for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
            sheets = {}
            self.paths = {}
            for sh in ET.fromstring(z.read('xl/workbook.xml')).find('s:sheets', NS):
                p = rels[sh.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')]
                p = p.lstrip('/') if p.startswith('/') else 'xl/' + p
                self.paths[sh.get('name')] = p
                if sh.get('name') not in ['Template','Dropdown Lists','GoodsLevelMode','Conditions List','Category Name']: continue
                root = ET.fromstring(z.read(p)); rows = []
                for row in root.findall('s:sheetData/s:row', NS):
                    d = {}
                    for c in row:
                        v = c.find('s:v', NS)
                        if c.get('t') == 's': value = strings[int(v.text)]
                        elif c.get('t') == 'inlineStr': value = ''.join(c.find('s:is', NS).itertext())
                        else: value = v.text if v is not None else None
                        if value is not None: d[col(c.get('r'))] = value
                    rows.append(d)
                sheets[sh.get('name')] = rows
                if sh.get('name') == 'Template': self.root = root
            self.headers = sheets['Template'][1]
            self.keys = sheets['Template'][3]
            self.rules = {r['A']: {c for c in r if c != 'A'} for r in sheets['GoodsLevelMode'][1:] if 'A' in r}
            self.dropdowns = {r['A']: [v for c,v in r.items() if c not in ['A','B']] for r in sheets['Dropdown Lists'] if 'A' in r}
            self.conditions = {r['A']: [v for c,v in r.items() if c not in ['A','B']] for r in sheets['Conditions List'] if 'A' in r}
            self.categories = {r['A']:r['B'] for r in sheets['Category Name'] if 'A' in r and 'B' in r}
            self.deps = {}
            for cf in self.root.findall('s:conditionalFormatting', NS):
                for f in cf.findall('s:cfRule/s:formula', NS):
                    if 'Conditions List' in (f.text or ''):
                        deps = re.findall(r'HLOOKUP\(\$?([A-Z]+)\$?5,', f.text)
                        if deps: self.deps[col(cf.get('sqref').split(':')[0])] = list(dict.fromkeys(deps))
            self.by_label = {}
            for c,h in self.headers.items(): self.by_label.setdefault(h, []).append(c)
            self.styles = {col(c.get('r')):c.get('s') for c in self.root.findall('s:sheetData/s:row', NS)[4]}

    def active(self, c, row):
        key = self.keys.get(c, '')
        if key not in self.conditions: return True
        deps = self.deps.get(c)
        if not deps: return False  # Unresolved dependency must never silently validate.
        return any(row.get(p) in self.conditions[key] for p in deps)

    def options(self, c, row):
        h = self.headers[c]; cat = str(row.get('E','')); section = self.keys[c].split('_')[1]
        if section == '3':
            parents = self.deps.get(c, [])
            parts = [str(row.get(p,'')) for p in parents]
            for key in ['t_3_'+cat+'_'+'_'.join(parts)+'_'+h, 't_3_'+cat+'_'+h]:
                if key in self.dropdowns: return self.dropdowns[key]
        if h == 'Trademark': return self.dropdowns.get('t_1_'+str(row.get('R',''))+'_Trademark', [])
        if h == 'Handling Time': return self.dropdowns.get('t_7_Normal product___Handling Time', [])
        return self.dropdowns.get(f't_{section}_{cat}_{h}', self.dropdowns.get(f't_{section}_{h}', []))

    def allowed(self, c, row):
        return c not in self.rules.get(str(row.get('E',''))+'_disabled', set()) and self.active(c,row)

    def groups(self, cat):
        out = {}
        for c in self.rules.get(str(cat)+'_require',set()): out.setdefault(self.keys[c], []).append(c)
        for c in self.rules.get(str(cat)+'_condition_require',set()): out.setdefault(self.keys[c], []).append(c)
        return [sorted(v,key=number) for v in out.values()]

    def validate(self, row):
        errors = []
        cat = str(row.get('E',''))
        if cat not in self.categories: return ['Category: no supported category selected']
        for group in self.groups(cat):
            live = [c for c in group if self.allowed(c,row)]
            if live and not any(row.get(c) not in [None,''] for c in live):
                if group[0]=='YI' and row.get('YJ')=='N/A': continue
                errors.append('Missing: '+self.headers[group[0]])
        # Selecting a variation theme activates at least one corresponding value.
        theme = str(row.get('XG',''))
        for part in theme.split(' × '):
            cs = [c for c in self.by_label.get(part,[]) if self.keys[c].startswith('t_4_')]
            if cs and not any(row.get(c) not in [None,''] for c in cs): errors.append('Missing variation: '+part)
        for c,v in row.items():
            if v in [None,''] or c not in self.headers: continue
            if not self.allowed(c,row): errors.append('Disabled field: '+self.headers[c]);continue
            opts = self.options(c,row)
            if opts and str(v) not in opts: errors.append('Invalid dropdown: '+self.headers[c]+' = '+str(v))
            if str(v).startswith('Must first finish'): errors.append('Account setup required: '+self.headers[c])
        for c in ['YG','YK','YL','YM','YN']:
            try:
                if float(row.get(c,0))<=0: errors.append('Positive number required: '+self.headers[c])
            except (TypeError,ValueError): errors.append('Invalid number: '+self.headers[c])
        if row.get('YI') and float(row['YI'])<=float(row['YG']):errors.append('List price must exceed base price')
        if row.get('YI') and row.get('YJ'):errors.append('List price and N/A are mutually exclusive')
        if not str(row.get('XU','')).startswith('https://'): errors.append('Missing original image URL')
        if len(str(row.get('L','')))>500: errors.append('Product Name exceeds 500 chars')
        if len(str(row.get('T','')))>2000: errors.append('Product Description exceeds 2000 chars')
        return sorted(set(errors))

    def write(self, rows, target):
        if len(rows)>2000: raise ValueError('Temu allows at most 2000 SKU rows per file')
        # Surgical replacement retains all surrounding XML and every other ZIP member.
        with zipfile.ZipFile(self.path) as zin:
            path=self.paths['Template']; xml=zin.read(path).decode('utf-8')
            match=re.search(r'<sheetData\b[^>]*>(.*?)</sheetData>',xml,re.S)
            original=match.group(1)
            oldrows=re.findall(r'<row\b[^>]*>.*?</row>',original,re.S)
            output=[]
            for old in oldrows:
                n=int(re.search(r'\br="(\d+)"',old).group(1))
                if n<5 or n>=5+len(rows):
                    if n>=5:
                        # Clear old user content, preserve template formulas and styles.
                        old=re.sub(r'<c\b[^>]*>.*?</c>', lambda m:m.group(0) if '<f' in m.group(0) else re.sub(r'\s+t="[^"]*"','',m.group(0).split('>')[0])+'/>',old,flags=re.S)
                    output.append(old);continue
                row=rows[n-5]; cells={col(m.group(1)):m.group(0) for m in re.finditer(r'<c\b[^>]*\br="([A-Z]+)\d+"[^>]*(?:/>|>.*?</c>)',old,re.S)}
                for c in list(cells):
                    if '<f' not in cells[c]: cells[c]=re.sub(r'\s+t="[^"]*"','',cells[c].split('>')[0]).rstrip('/')+'/>'
                for c,v in row.items():
                    if v is None or v=='':continue
                    style=self.styles.get(c);attrs=f' r="{c}{n}"'+(f' s="{style}"' if style else '')
                    if isinstance(v,(int,float)) and not isinstance(v,bool):cell=f'<c{attrs}><v>{v}</v></c>'
                    else:cell=f'<c{attrs} t="inlineStr"><is><t xml:space="preserve">{escape(str(v))}</t></is></c>'
                    cells[c]=cell
                # Keep the original Category Name formula and refresh its cached value.
                # This lets previews show the path before Excel recalculates the file.
                if 'F' in cells and '<f' in cells['F'] and str(row.get('E','')) in self.categories:
                    cached=cells['F'];cached=re.sub(r'\s+t="[^"]*"','',cached, count=1)
                    cached=cached.replace('>', ' t="str">',1)
                    cached=re.sub(r'<v>.*?</v>','<v>'+escape(self.categories[str(row['E'])])+'</v>',cached,flags=re.S)
                    cells['F']=cached
                start=old.split('>',1)[0]+'>';output.append(start+''.join(cells[c] for c in sorted(cells,key=number))+'</row>')
            xml=xml[:match.start(1)]+''.join(output)+xml[match.end(1):]
            with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as zout:
                for item in zin.infolist():zout.writestr(item,xml.encode() if item.filename==path else zin.read(item.filename))
