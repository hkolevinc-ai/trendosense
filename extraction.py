"""Source-driven synonyms. Unknown INCI, wood species and origin are not guessed."""
import re
ALIASES = {
'Wood':r'дърво|дървен|\bwood(?:en)?\b',
'Activated Charcoal':r'актив(?:ен|ния|ният) въглен|charcoal',
'Caffeine':r'кофеин|caffeine|с кафе\b', 'Olives':r'зехтин|маслинов|olea europaea',
'Olive Oil':r'зехтин|маслинов|olea europaea', 'Castor':r'рицинов|ricinus',
'Castor Oil':r'рицинов|ricinus', 'Glycerin':r'глицерин|glycerin', 'glycerin':r'глицерин|glycerin',
'Dimethicone':r'диметикон|(?<!\w)dimethicone(?!\w)',
'Glycolic Acid':r'гликолова киселина|glycolic acid', 'Menthol':r'ментол|menthol',
'Vitamin E':r'витамин\s*[eе]|vitamin\s*e|tocopher(?:ol|yl)',
'Vitamin C':r'витамин\s*[cс]|vitamin\s*c|ascorb(?:ic|yl)',
'Hyaluronic Acid':r'хиалурон|hyaluron', 'Ceramide':r'керамид|серамид|ceramide',
'Salicylic Acid':r'салицил|salicylic', 'Niacinamide':r'ниацинамид|niacinamide',
'Nicotinamide':r'ниацинамид|niacinamide', 'Retinol':r'ретинол|retinol',
'Rose':r'роза\b|розов екстракт|rose extract', 'Rosemary':r'розмарин|rosmarinus',
'Shea butter':r'ший|шеа|shea|butyrospermum', 'Shea Butter':r'ший|шеа|shea|butyrospermum',
'Sunflower oil':r'слънчогледово|helianthus annuus', 'Coconut':r'кокос|cocos nucifera',
'Coconut oil':r'кокосово масло|cocos nucifera', 'Almond Oil':r'бадемово|prunus amygdalus',
'Grape Seed Oil':r'гроздови семки|vitis vinifera', 'Jojoba Oil':r'жожоба|simmondsia',
'Argan Oil':r'арганово|argania spinosa','Argan':r'арган|argania spinosa',
'Citric Acid':r'лимонена киселина|citric acid', 'NaOH':r'натриев хидроксид|sodium hydroxide',
'Hamamelis Water':r'хамамелис|hamamelis', 'Licorice':r'женско биле|glycyrrhiza',
'Chamomile':r'лайка|chamomilla|chamomile', 'Green Tea':r'зелен чай|camellia sinensis',
'Tea Tree':r'чаено дърво|melaleuca', 'Aloe Vera':r'алое|aloe barbadensis',
'Petrolatum':r'вазелин|petrolatum', 'Silicon':r'силиций|silica\b',
'Alpha hydroxy acids':r'\baha\b|алфа.?хидрокси', 'Peptide':r'пептид|peptide',
'moisturizing':r'хидрат|овлажн|moisturi', 'clean':r'почист|измив|cleans',
'repair':r'възстанов|регенер|repair',
}

def apply_fields(p,t,row,evidence,notes):
    cat=row['E'];body=re.sub('<[^>]+>',' ',p.get('description',''))
    # Suppress colour/veneer mentions before determining actual timber.
    timber=re.sub(r'(?:орехов|дъбов|дървесен|орех|дъб)[^.,;\n]{0,18}(?:цвят|декор|финиш|тон)', '',body,flags=re.I)
    timber=re.sub(r'(?:цвят|декор|финиш)[^.,;\n]{0,30}', '',timber,flags=re.I)
    panel=bool(re.search(r'\bmdf\b|мдф|пдч|particle\s*board|chipboard',body,re.I))
    explicitwood=bool(re.search(r'дървен|дърво|wooden|solid wood',body,re.I))
    def put(c,v):
        if t.allowed(c,row) and v in t.options(c,row):row[c]=v;notes.append(f'{c}={v}: разпознато в продуктовия текст')
    furniture=cat in ['12507','12508','12796','12797','25088','12606']
    if furniture:
        if panel or explicitwood:put('FQ','Yes')
        if panel:
            put('FT','Artificial board');put('HN','Engineered Wood')
            if not row.get('EP'):put('EP','Other material')
            put('FU','Fiberboard' if re.search(r'\bmdf\b|мдф',body,re.I) else 'Particle board')
        if explicitwood and not row.get('EP'):put('EP','Wood')
        if re.search(r'(?:изработен|материал|масив)[^.;\n]{0,70}(?:дъб|орех|бук|oak|walnut|beech)',timber,re.I):
            put('FR','Hardwood')
        if not re.search(r'електр|батери|осветл|led|електрон|electri',body,re.I):put('FY','Without Battery')
    # Other is used only for an explicitly named ingredient outside the enum.
    if not any(row.get(c) for c in ['EJ','EK','EL','EM','EN','EO']):
        named=re.search(r'центела|centella|пантенол|panthenol|\bpdrn\b|бифида|bifida|прополис|propolis|beta.?glucan|бета.?глюкан',evidence,re.I)
        if named:put('EJ','Other');notes.append('Основна съставка извън менюто: '+named.group())
    # Extract transport package dimensions/weight only when the description labels it as a package.
    package=re.search(r'(?:брой пакети|опаковка|размери на опаковката)[\s\S]{0,130}?(\d+(?:[.,]\d+)?)\s*[x×]\s*(\d+(?:[.,]\d+)?)\s*[x×]\s*(\d+(?:[.,]\d+)?)\s*(?:см|cm)\s*/\s*(\d+(?:[.,]\d+)?)\s*(?:кг|kg)',body,re.I)
    if package:
        for c,v in zip(['YL','YM','YN'],package.groups()[:3]):row[c]=float(v.replace(',','.'))
        row['YK']=round(float(package.group(4).replace(',','.'))*1000,1)
        notes.append('Транспортна опаковка: размери и тегло от описанието')
