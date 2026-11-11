#!/usr/bin/env python3
"""Trendosense -> the supplied Temu workbook. Python 3.11+, standard library only."""
import argparse, concurrent.futures, csv, html, json, math, re, sys, time, urllib.parse, urllib.request
from functools import lru_cache
from collections import Counter
from decimal import Decimal, ROUND_CEILING
from html.parser import HTMLParser
from pathlib import Path
from temu import Template, number

BASE='https://trendosense.com'
class Text(HTMLParser):
    def __init__(self): super().__init__();self.parts=[];self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ['script','style']:self.skip+=1
        if tag in ['p','li','br','h2','h3','tr']:self.parts.append('\n')
    def handle_endtag(self,tag):
        if tag in ['script','style']:self.skip=max(0,self.skip-1)
    def handle_data(self,data):
        if not self.skip:self.parts.append(data)
def clean(s):
    p=Text();p.feed(s or '')
    return '\n'.join(re.sub(r'\s+',' ',v).strip() for v in ''.join(p.parts).splitlines() if v.strip())
def short(s):return re.sub(r'\s+',' ',html.unescape(s)).strip()
def get(url):
    for n in range(4):
        try:
            req=urllib.request.Request(url,headers={'User-Agent':'TrendosenseCatalogExporter/1.0','Accept':'application/json,text/html'})
            with urllib.request.urlopen(req,timeout=60) as r:return r.read(),dict(r.headers)
        except Exception:
            if n==3:raise
            time.sleep(1+n)
def api(path):
    b,h=get(BASE+'/wp-json/wc/store/v1/'+path);return json.loads(b),h
def catalog(limit=0):
    first,h=api('products?per_page=100&page=1&orderby=id&order=asc')
    pages=int(h.get('X-WP-TotalPages',h.get('x-wp-totalpages','1')))
    total=int(h.get('X-WP-Total',h.get('x-wp-total','0')))
    wanted=pages if not limit else min(pages,math.ceil(limit/100))
    def page(n):return api(f'products?per_page=100&page={n}&orderby=id&order=asc')[0]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:allp=first+sum(list(ex.map(page,range(2,wanted+1))),[])
    unique={p['id']:p for p in allp}
    if len(unique)!=len(allp):raise RuntimeError('Duplicate IDs during pagination. Rerun against a stable catalog.')
    if not limit and total and len(unique)!=total:raise RuntimeError(f'Incomplete catalog: {len(unique)} / {total}')
    return list(unique.values())[:limit or None]

# Ordered by specific product type before broader site categories.
MAP=[
 (r'поставки? за цветя|стойка за растения|цветарник', '25088'),
 (r'холна масич|масички за кафе|комплект.*(?:средни маси|маси от)|маса woody', '12507'),
 (r'холна секция', '12606'),
 (r'екcфолиант|ексфолиант|ексфолиращ', '18963'),
 (r'фиксираща пудра|fixing powder', '19390'),
 (r'олио за устни|fat oil|lip glow oil', '55115'),
 (r'тинт за устни', '19404'),
 (r'гел за лице|многофункционален балсам', '18972'),
 (r'лифтинг пластир', '18979'),
 (r'околооч.*(?:пач|маск)|eye.*(?:patch|mask)', '18988'),
 (r'околооч.*серум|eye serum','18991'),(r'околооч|eye cream','18992'),
 (r'устни.*(?:нощ|маска)|lip.*(?:sleep|mask)','55118'),
 (r'устни.*(?:масло|олио)|lip oil','55115'),(r'пламп|lip plump','18774'),
 (r'балсам.*устни|lip balm','18772'),(r'гланц|lip gloss','19401'),(r'червило|lipstick','19404'),
 (r'bb\s*(?:cream|крем)','18966'),(r'cc\s*(?:cream|крем)','18967'),
 (r'коректор|concealer','19388'),(r'фон дьо тен|foundation(?! primer)','19389'),
 (r'основа за грим|primer','19391'),(r'хайлайт|highlighter','19397'),(r'руж|blush','19387'),(r'спирала|mascara','19380'),
 (r'комплект.*(?:шампоан|коса)|shampoo.*set','19327'),
 (r'шампоан|shampoo','19328'),(r'балсам.*коса|hair conditioner','19326'),
 (r'маска.*коса|hair mask','19332'),(r'серум.*(?:коса|скалп)|scalp serum','19264'),
 (r'масло.*коса|hair oil','19269'),(r'(?:спрей|балсам).*коса','19272'),
 (r'тоник.*коса|hair tonic','19275'),
 (r'комплект.*(?:лице|кожа)|skin.*(?:set|kit)','18984'),
 (r'хидрофил|почистващ.*(?:олио|масло)|cleansing oil','18953'),
 (r'почистващ.*балсам|cleansing balm','18960'),
 (r'почистващ.*крем|cleansing cream','18955'),
 (r'почистващ.*(?:гел|пяна|мус)|cleans(?:ing|er).*(?:gel|foam)|пенка','18956'),
 (r'почистващ|cleans(?:er|ing)','18958'),
 (r'скраб.*лице|face scrub','18963'),(r'пилинг|peel','18982'),
 (r'тонер|тоник.*лице|toner','18975'),
 (r'нощен.*крем|night cream','18970'),
 (r'спрей.*лице|face mist','18971'),
 (r'ампула|серум|есенция|бустер|ampoule|serum|essence|booster|reedle shot','18981'),
 (r'маска|mask','18977'),
 (r'крем.*лице|facial cream|face cream|moisturi[sz]er|\bcream\b','18972'),
 (r'сапун.*(?:ръце|hand)|hand wash','18938'),(r'сапун|soap','18937'),
 (r'душ гел|shower gel|body wash','18936'),(r'скраб.*тяло|body scrub','18940'),
 (r'лосион|body lotion','18948'),(r'масло.*тяло|body oil','18947'),
 (r'крем.*тяло|body cream','18946'),
 (r'цветарник|plant rack','25088'),(r'холна маса|coffee table','12507'),
 (r'поставка.*телевизор|tv stand','12606'),(r'етажерк|standing shelf','12797'),
 (r'рафт|floating shel','12796')]

def choose_category(p):
    title=short(p['name']).lower(); cats=' '.join(c['name'].lower() for c in p.get('categories',[]));d=clean(p.get('description','')).lower()
    if re.search(r'ламп|floor lamp|sun.?screen|слънцезащит|крем за (?:ръце|крака)|hand cream|foot cream',title):return '', 'Няма подходяща категория в прикачения шаблон'
    if re.search(r'augue|adipiscing|eames|wooden single|classic wooden|henectus|lorem|ipsum',title):return '', 'Вероятен демонстрационен продукт'
    if re.search(r'парфюм|eau de |perfume|cologne|body mist|спрей.*тяло',title):
        gender=title+' '+d
        male=bool(re.search(r'\bмъж(?:ки|е)\b|\b(?:for men|pour homme|male)\b',gender))
        female=bool(re.search(r'\bдамск|\b(?:for women|pour femme|female)\b',gender))
        if re.search(r'unisex|унисекс',gender) or male==female:return '', 'Необходима унисекс категория или потвърден пол за парфюма'
        if re.search('mist|спрей',title):return ('19221','') if female else ('','Няма мъжка категория за body spray')
        if re.search('комплект|set',title):return ('19218' if female else '19212'),' '
        if re.search('toilette|\bedt\b',title):return ('19225' if female else '19214'),''
        return ('19224' if female else '19213'),''
    # Body and hair categories before generic cream/serum rules.
    if 'козметика за тяло' in cats:
        for pattern,c in [(r'лосион','18948'),(r'масло|олио','18947'),(r'крем','18946'),(r'душ|гел','18936'),(r'сапун','18937')]:
            if re.search(pattern,title):return c,''
    if 'козметика за коса' in cats:
        for pattern,c in [(r'комплект','19327'),(r'шампоан','19328'),(r'спрей-балсам|балсам','19326'),(r'масло|олио','19269'),(r'серум|скалп','19264'),(r'терап|treatment','19277'),(r'спрей','19263')]:
            if re.search(pattern,title):return c,''
    if re.search(r'комплект.*(?:some by mi|skin|facial)',title):return '18984',''
    for pattern,c in MAP:
        if re.search(pattern,title):return c,''
    for keyword,c in [('Крем за лице','18972'),('Маска за лице','18977'),('Серум за лице','18981'),('Ампула за лице','18981'),('Есенция за лице','18981'),('Тонер за лице','18975')]:
        if any(x['name']==keyword for x in p.get('categories',[])):return c,''
    return '', 'Типът продукт изисква преглед на категорията'

ALIASES={
 'moisturizing':r'хидрат|moisturi', 'clean':r'почист|измив|cleans',
 'repair':r'възстанов|repair|кожна бариера',
 'anti-wrinkle by moisturizing':r'бръчк|wrinkle',
 'anti-aging by moisturizing':r'анти.?ейдж|anti.?aging|подмлад',
 'chemical exfoliation':r'пилинг|киселин|\baha\b|\bbha\b|\bpha\b',
 'physical exfoliation through beads or granules':r'скраб|scrub',
 'Engineered Wood':r'мдф|\bmdf\b|пдч|chipboard|engineered wood',
 'Manufactured wood':r'мдф|\bmdf\b|пдч|chipboard|engineered wood',
 'Wooden':r'дървен|дърво|wood',
 'Hyaluronic Acid':r'хиалурон|hyaluron', 'Nicotinamide':r'ниацинамид|niacinamide',
 'Niacinamide':r'ниацинамид|niacinamide','glycerin':r'glycerin|глицерин','Glycerin':r'glycerin|глицерин',
 'Retinol':r'ретинол|retinol','Vitamin C':r'витамин\s*c|vitamin\s*c|ascorbic','Vitamin E':r'витамин\s*е|vitamin\s*e|tocopherol',
 'Collagen':r'колаген|collagen','Peptide':r'пептид|peptide','Ceramide':r'керамид|серамид|ceramide',
 'Snail Mucin':r'муцин|snail','Rice':r'ориз|rice|oryza','Aloe Vera':r'алое|aloe',
 'Green Tea':r'зелен чай|green tea','Tea Tree':r'чаено дърво|tea tree','Shea Butter':r'ший|shea|butyrospermum',
 'Shea butter':r'ший|shea|butyrospermum','Salicylic Acid':r'салицил|salicylic','Lactic Acid':r'млечна киселина|lactic acid',
 'Lactic acid':r'млечна киселина|lactic acid','Ginseng':r'женшен|ginseng','Glutathione':r'глутатион|glutathione',
 'Squalane':r'сквалан|squalane','Honey':r'мед\b|honey','Coconut oil':r'кокос|coconut',
 'Argan Oil':r'арган|argan','Jojoba Oil':r'жожоба|jojoba','Cocoa butter':r'какаов|cocoa',
 'Sunflower oil':r'слънчоглед|helianthus','Olive Oil':r'маслин|olive','Rosehip Seed Oil':r'шипк|rosehip',
 'Aromatic':r'ароматн','Floral':r'цветен|цветни|floral','Fruity':r'плодов|fruity','Woody':r'дървес|woody',
 'Gourmand':r'гурме|gourmand','Citrus':r'цитрус|citrus','Oriental':r'ориентал|oriental',
 'Cream':r'крем|cream','Gel':r'гел|gel','Liquid':r'течен|течна|liquid',
 'Combination':r'комбиниран|combination','Dry':r'суха кожа|dry skin','Oily':r'мазна кожа|oily skin',
 'Sensitive':r'чувствителна кожа|sensitive skin','All Skins':r'всеки тип кожа|всички типове кожа|all skin',
 'Moisturizing':r'хидрат|moisturi','Anti-Aging':r'против стареене|анти-ейдж|anti.?aging',
 'Wood':r'дърво|дървен|wood','Metal':r'метал|metal','Glass':r'стъкло|стъклен|glass',
 'Plastic':r'пластмас|plastic','MDF':r'\bмдф\b|\bmdf\b',
}
@lru_cache(maxsize=4096)
def option_pattern(option):
    return re.compile(ALIASES.get(option) or (r'(?<!\w)'+re.escape(option)+r'(?!\w)'),re.I)

def matches(option,text):
    return len(option)>2 and bool(option_pattern(option).search(text))

def content(p):
    # Strip store/service information, retain actual product properties and INCI.
    txt=clean(p.get('description',''))
    return '\n'.join(x for x in txt.splitlines() if not re.search(r'доставк|гаранци|безплатн|цени на едро|регистрац|връщан|поръчайте|wholesale',x,re.I))

def enrich(p,cache):
    path=cache/f"{p['id']}.html"
    try:
        if not path.exists():path.write_bytes(get(p['permalink'])[0])
        raw=path.read_text();extra={}
        # Only product attribute table; never use related-product data.
        table=re.search(r'<table[^>]*class="[^"]*woocommerce-product-attributes.*?</table>',raw,re.S)
        if table:extra['attribute_text']=clean(table.group())
        v=re.search(r'data-product_variations=[\'"](.*?)[\'"]\s',raw,re.S)
        if v and v.group(1)!='false':extra['html_variations']=json.loads(html.unescape(v.group(1)))
        p['_extra']=extra
    except Exception as e:p['_enrichment_error']=str(e)
    return p

def expand(p):
    if p.get('type')=='grouped':return []
    if p.get('type')!='variable':return [p]
    vv=p.get('_extra',{}).get('html_variations',[])
    if not vv:
        # Public Store API exposes variation products using the parent filter.
        vv,_=api(f'products?type=variation&parent={p["id"]}&per_page=100')
        if len(vv)==100:raise ValueError('Variation pagination requires review for parent '+str(p['id']))
    if not vv:raise ValueError('Cannot retrieve all variations for '+str(p['id']))
    out=[]
    for v in vv:
        if 'display_price' not in v:
            q=dict(p);q.update(v);q['_parent_id']=p['id'];out.append(q);continue
        q=dict(p);q['_parent_id']=p['id'];q['id']=v['variation_id'];q['sku']=v.get('sku','')
        attrs=v.get('attributes',{});q['_variation_attrs']=attrs
        if any(not x for x in attrs.values()):raise ValueError('Wildcard variation must be resolved for '+str(v['variation_id']))
        q['name']=p['name']+' — '+', '.join(urllib.parse.unquote(str(x)) for x in attrs.values())
        q['prices']=dict(p['prices']);minor=q['prices'].get('currency_minor_unit',2)
        for k,vk in [('price','display_price'),('regular_price','display_regular_price')]:q['prices'][k]=str(round(Decimal(str(v[vk]))*(10**minor)))
        q['is_in_stock']=v.get('is_in_stock',False);q['weight']=v.get('weight',p.get('weight'));q['dimensions']=v.get('dimensions',p.get('dimensions',{}))
        if v.get('image',{}).get('full_src'):q['images']=[{'src':v['image']['full_src']}] + p.get('images',[])
        q['low_stock_remaining']=v.get('max_qty') if isinstance(v.get('max_qty'),int) else None
        out.append(q)
    return out

def row_for(p,t,config,override):
    row={};notes=[];cat,reason=choose_category(p);cat=str(override.get('E') or cat)
    title=short(p['name']);txt=content(p);evidence=title+'\n'+txt+'\n'+p.get('_extra',{}).get('attribute_text','')+'\n'+clean(p.get('short_description',''))
    for a in p.get('attributes',[]):evidence+='\n'+a.get('name','')+': '+', '.join(str(x) for x in a.get('terms',[]))
    def put(c,v):
        if v is not None and v!='' and t.allowed(c,dict(row,E=cat)):row[c]=v
    row.update(E=cat,G='Normal product',L=title[:500],M='TS-'+str(p.get('_parent_id',p['id'])),N=p.get('sku') or 'TS-'+str(p['id']),O='Add',T=txt[:2000],YH=p['permalink'])
    if not p.get('sku'):notes.append('Contribution SKU генериран от WooCommerce ID: '+row['N'])
    row['ABB']=row['N']
    if cat not in t.categories:return row,['Category: '+reason],notes
    # Pick only registered dropdown identities. Do not write setup instructions as names.
    opts=t.options('ABC',row)
    if config['manufacturer'] in opts:put('ABC',config['manufacturer'])
    elif len(opts)==1 and not opts[0].startswith('Must first'):put('ABC',opts[0])
    ep=config.get('eu_responsible_person','')
    if ep and ep in t.options('ABD',row):put('ABD',ep)
    put('YX',config.get('shipping_template') or (t.options('YX',row) or [''])[0]);put('YY','1 Day');put('YZ','I will ship this item myself')
    brands=[short(b['name']) for b in p.get('brands',[])]
    for b in brands:
        if b in t.options('R',row):put('R',b);break
    if row.get('R'):
        opts=t.options('S',row)
        if row['R'] in opts:put('S',row['R'])
        elif len(opts)==1 and not opts[0].startswith('Must first'):put('S',opts[0])
    pr=p.get('prices',{});currency=pr.get('currency_code');minor=int(pr.get('currency_minor_unit',2))
    if currency!='EUR':raise ValueError('Expected EUR, received '+str(currency))
    price=Decimal(pr.get('price') or '0')/(10**minor);regular=Decimal(pr.get('regular_price') or '0')/(10**minor)
    put('YG',float(price.quantize(Decimal('.01'),rounding=ROUND_CEILING)))
    if regular>price:put('YI',float(regular))
    else:put('YJ','N/A')
    qty=p.get('low_stock_remaining')
    if not p.get('is_in_stock'):qty=0
    elif qty is None:
        qty=config['default_stock'];notes.append('Количество '+str(qty)+': настройка, сайтът показва само наличност')
    put('YF',int(qty))
    images=list(dict.fromkeys(i['src'] for i in p.get('images',[]) if i.get('src') and 'placeholder' not in i['src']))
    for image in p.get('images',[]):
        source=image.get('src','')
        sizes=[int(x) for x in re.findall(r'\s(\d+)w',image.get('srcset',''))]
        if sizes and max(sizes)<800:notes.append('Оригинална снимка под 800px: '+source)
        if source and not re.search(r'\.(?:jpe?g|png)(?:\?|$)',source,re.I):notes.append('Форматът на оригиналната снимка изисква проверка в Temu: '+source)
    for c,url in zip(t.by_label['SKU Images URL'],images):put(c,url)
    for c,url in zip(t.by_label['Detail Images URL'],images[1:]):put(c,url)
    measures=re.findall(r'(\d+(?:[.,]\d+)?)\s*(ml|мл|литра|l|g|гр|грама|kg|кг)\b',title,re.I)
    amount=None;unit=None
    if len(measures)==1:
        amount=float(measures[0][0].replace(',','.'));unit={'мл':'ml','гр':'g','грама':'g','кг':'kg','литра':'l'}.get(measures[0][1].lower(),measures[0][1].lower())
    is_set=bool(re.search(r'комплект|\bset\b',title,re.I))
    # Packaging counts describe packs, not an invented stock amount.
    count=re.search(r'(\d+)\s*(?:бр(?:оя)?\.?|pcs|pieces)\b',title,re.I)
    multipack=re.search(r'(\d+)\s*[x×]\s*\d+(?:[.,]\d+)?\s*(?:ml|мл|g|гр)\b',title,re.I)
    pieces=int(count.group(1)) if count else int(multipack.group(1)) if multipack else 1
    put('YO','Mixed set of different products' if is_set else ('Multi-piece set' if pieces>1 else 'Single set'))
    put('YP','Yes');put('YQ',pieces);put('YR','piece')
    if amount and not is_set:
        put('YS',amount);put('YT',round(amount*pieces,4));put('YU',unit)
    variation=p.get('_variation_attrs',{})
    themes=[]
    for k,v in variation.items():
        key=urllib.parse.unquote(k).lower();value=urllib.parse.unquote(v)
        label='Color' if re.search(r'color|цвят',key) else 'Capacity' if re.search(r'volume|обем|capacity',key) else 'Size' if re.search(r'size|размер',key) else 'Model'
        cs=[c for c in t.by_label.get(label,[]) if t.keys[c].startswith('t_4_')]
        if cs:row[cs[0]]=value;themes.append(label)
    if not themes:
        if amount and not is_set:themes=['Capacity'];row['XN']=f'{amount:g} {unit}'
        else:themes=['Model'];row['XS']=row['N']
    if len(themes)>2:notes.append('Повече от 2 вариационни свойства');themes=themes[:2]
    theme=' × '.join(themes)
    options=t.options('XG',row)
    if theme not in options and ' × '.join(reversed(themes)) in options:theme=' × '.join(reversed(themes))
    put('XG',theme)
    weight=p.get('weight')
    if weight:put('YK',math.ceil(float(str(weight).replace(',','.'))*10000)/10)
    elif amount and unit in ['g','kg','ml','l']:
        put('YK',math.ceil(amount*(1000 if unit in ['l','kg'] else 1)*1.15));notes.append('Тегло оценено от нетното съдържание +15%')
    dims=p.get('dimensions') or {}
    if all(dims.get(k) for k in ['length','width','height']):
        for c,k in zip(['YL','YM','YN'],['length','width','height']):put(c,math.ceil(float(str(dims[k]).replace(',','.'))*10)/10)
    elif config.get('estimate_package_dimensions'):
        default=[20,20,20]
        if 'Beauty' in t.categories[cat] or 'Health' in t.categories[cat]:default=[15,8,8] if not amount or amount<=150 else [22,12,10]
        for c,v in zip(['YL','YM','YN'],default):put(c,v)
        notes.append('Опаковъчните размери са ориентировъчни: '+' × '.join(map(str,default))+' cm')
    # Country is extracted only from an explicit origin phrase, never brand nationality.
    origins={'Bulgaria':r'българия|bulgaria','South Korea':r'южна корея|south korea|republic of korea','Korea':r'южна корея|south korea','China':r'китай|china','Italy':r'италия|italy','France':r'франция|france','Turkey':r'турция|turkey|türkiye','United Arab Emirates':r'обединени арабски емирства|united arab emirates|\buae\b','Poland':r'полша|poland','Germany':r'германия|germany'}
    for country,pat in origins.items():
        if re.search(r'(?:произход|произведен[оаи]? в|made in|country of origin)\s*[:\-]?\s*(?:'+pat+')',evidence,re.I) and country in t.options('ZB',row):put('ZB',country);break
    ean=re.search(r'(?:EAN|GTIN|баркод)\s*[:\-]?\s*(\d{8,14})\b',evidence,re.I)
    if ean:
        digits=ean.group(1);valid=len(digits) in [8,12,13,14] and sum(int(v)*(3 if i%2==0 else 1) for i,v in enumerate(digits[-2::-1]))%10==(10-int(digits[-1]))%10
        if valid:put('YV','EAN' if len(digits) in [8,13] else 'UPC' if len(digits)==12 else 'GTIN-14');put('YW',digits)
        else:notes.append('Невалиден контролен знак на баркода: '+digits)
    # Repeat passes support multi-level dependencies, e.g. material -> wood type -> species.
    groups={}
    for c,key in t.keys.items():
        if key.startswith('t_3_'):groups.setdefault(key,[]).append(c)
    matched={}
    for _ in range(3):
        for key,cs in groups.items():
            cs=sorted(cs,key=number);c=cs[0]
            if not t.allowed(c,row) or any(row.get(x) is not None for x in cs):continue
            opts=t.options(c,row)
            h=t.headers[c]
            if h=='1561 - Power Supply' and cat in ['12507','12508','12796','12797','25088','12606']:
                if 'Use Without Electricity' in opts:put(c,'Use Without Electricity');continue
            if h=='4102 - Contain Wooden Materials' and re.search(r'дърв|\bwood|\bmdf|пдч|мдф',evidence,re.I):
                if 'Yes' in opts:put(c,'Yes');continue
            if h=='7972 - Application Scenarios' and 'For Human Use' in opts and re.search(r'козметика|кожа|коса|лице|устни',evidence,re.I):
                put(c,'For Human Use');continue
            for v in dict.fromkeys(opts):
                if v not in matched:matched[v]=matches(v,evidence)
            selected=[v for v in dict.fromkeys(opts) if matched[v]]
            for c,v in zip(cs,selected):put(c,v)
    # Product-specific merchant overrides use exact column letters and dropdown values.
    for c,v in override.items():
        if c in t.headers and v!='':row[c]=v
    # Numeric overrides remain numbers in Excel.
    for c in ['YG','YI','YK','YL','YM','YN','YS','YT']:
        if c in row:row[c]=float(row[c])
    for c in ['YF','YQ']:
        if c in row:row[c]=int(row[c])
    return row,t.validate(row),notes

def write_csv(path,rows,fields):
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--limit',type=int,default=0);ap.add_argument('--offline');ap.add_argument('--no-enrich',action='store_true');ap.add_argument('--no-xlsx',action='store_true');ap.add_argument('--output',default='outputs');args=ap.parse_args()
    cfg=json.loads(Path('config.json').read_text());t=Template(cfg['template']);out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    # Never leave a previous successful run masquerading as this run's ready file.
    for pattern in ['TEMU_READY_*.xlsx','DRAFT_REVIEW_*.xlsx']:
        for stale in out.glob(pattern):stale.unlink()
    products=json.loads(Path(args.offline).read_text()) if args.offline else catalog(args.limit)
    if args.limit:products=products[:args.limit]
    (out/'raw_products.json').write_text(json.dumps(products,ensure_ascii=False,indent=2))
    if not args.no_enrich:
        cache=Path('.cache/html');cache.mkdir(parents=True,exist_ok=True)
        with concurrent.futures.ThreadPoolExecutor(max_workers=cfg.get('workers',4)) as ex:products=list(ex.map(lambda p:enrich(p,cache),products))
        (out/'raw_products.json').write_text(json.dumps(products,ensure_ascii=False,indent=2))
    overrides={}
    if Path('overrides.csv').exists():
        with open('overrides.csv',encoding='utf-8-sig',newline='') as f:overrides={r['product_id']:r for r in csv.DictReader(f) if r.get('product_id')}
    drafts=[];ready=[];issues=[];audit=[];seen=set();categories=Counter();fields=Counter()
    for parent in products:
        try:
            if parent.get('type')=='grouped':
                issues.append({'product_id':parent['id'],'name':parent['name'],'url':parent['permalink'],'issues':'Grouped product: children exported separately'});continue
            for p in expand(parent):
                ov=overrides.get(str(parent['id']),{})|overrides.get(str(p['id']),{})
                row,errors,notes=row_for(p,t,cfg,ov)
                if row.get('N') in seen:errors.append('Duplicate Contribution SKU: '+row['N'])
                seen.add(row.get('N'));categories[row.get('E') or 'UNMAPPED']+=1
                if p.get('_enrichment_error'):notes.append('HTML enrichment failed: '+p['_enrichment_error'])
                for e in errors:fields[e]+=1
                record={'product_id':p['id'],'sku':row.get('N',''),'name':p['name'],'url':p['permalink'],'category':row.get('E',''),'issues':' | '.join(errors),'notes':' | '.join(notes)}
                audit.append(record)
                if errors:issues.append(record)
                else:ready.append(row)
                if row.get('E') in t.categories:drafts.append(row)
        except Exception as e:
            issues.append({'product_id':parent['id'],'name':parent['name'],'url':parent['permalink'],'issues':'Processing error: '+str(e)})
    (out/'draft_rows.json').write_text(json.dumps(drafts,ensure_ascii=False,indent=2));(out/'ready_rows.json').write_text(json.dumps(ready,ensure_ascii=False,indent=2))
    headers=['product_id','sku','name','url','category','issues','notes'];write_csv(out/'needs_data.csv',issues,headers);write_csv(out/'audit.csv',audit,headers)
    write_csv(out/'category_rules.csv',[{'category_id':cat,'category_path':path,'field':t.headers[cs[0]],'columns':','.join(cs),'conditional':str(cs[0] in t.rules.get(cat+'_condition_require',set()))} for cat,path in t.categories.items() for cs in t.groups(cat)],['category_id','category_path','field','columns','conditional'])
    write_csv(out/'dropdown_values.csv',[{'key':k,'values':' | '.join(v)} for k,v in t.dropdowns.items()],['key','values'])
    if not args.no_xlsx:
        for prefix,rows in [('DRAFT_REVIEW',drafts),('TEMU_READY',ready)]:
            for i in range(0,len(rows),2000):t.write(rows[i:i+2000],out/f'{prefix}_{i//2000+1:03}.xlsx')
    summary={'catalog_products':len(products),'mapped_sku_rows':len(drafts),'ready_sku_rows':len(ready),'records_with_issues':len(issues),'categories':dict(categories),'issues':dict(fields.most_common()),'manufacturer':cfg['manufacturer'],'template_categories':len(t.categories),'enriched_products':sum('_extra' in p for p in products)}
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(json.dumps(summary,ensure_ascii=False,indent=2))
    if not ready:print('No upload-ready file: see needs_data.csv. Drafts are for review only.')

if __name__=='__main__':main()
