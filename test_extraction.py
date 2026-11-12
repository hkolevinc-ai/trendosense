import json, unittest
from temu import Template
from scraper import choose_category, matches, row_for
class ExtractionTest(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.t=Template('template.xlsx');cls.cfg=json.load(open('config.json'))
 def test_soap_beats_oil_keyword(self):
  self.assertEqual(choose_category({'name':'Натурален сапун със зехтин и дафиново масло'})[0],'18937')
 def test_lotion_beats_fragrance_name(self):
  self.assertEqual(choose_category({'name':'Victoria Secret Fragrance Body Lotion 236ml'})[0],'18948')
 def test_translations_and_negation(self):
  self.assertTrue(matches('Dimethicone','Вода, глицерин, диметикон.'))
  self.assertFalse(matches('Retinol','Формула без ретинол.'))
  self.assertFalse(matches('Wood','Woody Fashion'))
 def test_mdf_dependencies_and_package(self):
  p={'id':1,'name':'Холна маса MDF','permalink':'https://trendosense.com/1','description':'100% MDF. Брой пакети: 1. 35 x 35 x 10 см / 3 кг (1 брой)','prices':{'price':'1000','regular_price':'1000','currency_code':'EUR','currency_minor_unit':2},'is_in_stock':True,'images':[]}
  r,e,n=row_for(p,self.t,self.cfg,{})
  self.assertEqual(r.get('FT'),'Artificial board');self.assertEqual(r.get('FU'),'Fiberboard')
  self.assertEqual((r['YL'],r['YM'],r['YN'],r['YK']),(35,35,10,3000))
  self.assertNotIn('FR',r) # MDF does not establish tree species.
  self.assertIn('Missing: 4099 - Fiberboard Density',e)
if __name__=='__main__':unittest.main()
