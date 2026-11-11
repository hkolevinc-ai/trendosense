"""Focused regression checks for Temu routing and preservation."""
import json, re, unittest, zipfile, tempfile
from pathlib import Path
from temu import Template
from scraper import expand, choose_category, row_for

class RulesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.t=Template('template.xlsx')
    def test_dependent_voltage_and_wood(self):
        t=self.t;r={'E':'12507','FJ':'Use Without Electricity','FQ':'No'}
        self.assertFalse(t.active('FK',r));self.assertFalse(t.active('FR',r))
        r.update(FJ='Plug Powered',FQ='Yes')
        self.assertTrue(t.active('FK',r));self.assertTrue(t.active('FR',r))
    def test_repeat_columns_and_na(self):
        r={'E':'18981','EJ':'Hyaluronic Acid','XG':'Capacity','XN':'30 ml','YJ':'N/A','YG':9.99,'YK':100,'YL':15,'YM':8,'YN':8,'L':'Test','M':'TS-1','N':'TS-1','XU':'https://example.org/image.jpg','YF':20,'YP':'Yes','YQ':1,'YR':'piece','YX':'Сандански','ABB':'TS-1','ABC':'FMS TRADE'}
        e=self.t.validate(r)
        self.assertNotIn('Missing: 3707 - Main Ingredients',e)
        self.assertNotIn('Missing: List Price - EUR',e)
        self.assertIn('Missing: EU Responsible person',e)
    def test_variation_own_price_sku_image(self):
        p={'id':1,'name':'Serum','type':'variable','prices':{'currency_minor_unit':2},'images':[], '_extra':{'html_variations':[{'variation_id':2,'sku':'sku-2','display_price':5.2,'display_regular_price':7.8,'attributes':{'attribute_volume':'30ml'},'is_in_stock':True,'image':{'full_src':'https://example.org/original.png'}}]}}
        v=expand(p)[0]
        self.assertEqual((v['id'],v['sku'],v['prices']['price']),(2,'sku-2','520'))
        self.assertEqual(v['images'][0]['src'],'https://example.org/original.png')
    def test_categories_do_not_force_unisex_or_lamps(self):
        for title in ['Унисекс парфюм Eau de Parfum 100 ml','Подова лампа 150cm']:
            self.assertEqual(choose_category({'name':title})[0],'')
        self.assertEqual(choose_category({'name':'Холна масичка 70x40 см'})[0],'12507')
    def test_native_template_preservation(self):
        with tempfile.TemporaryDirectory() as d:
            dst=Path(d)/'out.xlsx';self.t.write([{'E':'18981','L':'Example','N':'TS-1'}],dst)
            with zipfile.ZipFile(self.t.path) as a,zipfile.ZipFile(dst) as b:
                self.assertEqual(a.namelist(),b.namelist())
                path=self.t.paths['Template']
                for f in a.namelist():
                    if f!=path:self.assertEqual(a.read(f),b.read(f),f)
                x=a.read(path).decode();y=b.read(path).decode()
                for n in range(1,5):
                    pat=rf'<row\b[^>]*\br="{n}"[^>]*>.*?</row>'
                    self.assertEqual(re.search(pat,x,re.S).group(),re.search(pat,y,re.S).group())
                for tag in ['dataValidations','conditionalFormatting','cols']:
                    pat=rf'<{tag}\b.*?</{tag}>'
                    self.assertEqual(re.findall(pat,x,re.S),re.findall(pat,y,re.S))

if __name__=='__main__':unittest.main()
