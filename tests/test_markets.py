import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
import market_adapters as m
class MarketTests(unittest.TestCase):
 def test_binance_units(self):
  q=m.binance_quotes({'coins':['bitcoin']},lambda url:[{'symbol':'BTCUSDT','lastPrice':'100','priceChangePercent':'2','closeTime':1000000}]);self.assertEqual(q['rows'][0]['currency'],'USDT');self.assertEqual(q['rows'][0]['time'],1000)
 def test_crypto_fallback(self):
  def fetch(url):
   if 'binance' in url:raise ValueError('offline')
   return {'bitcoin':{'usd':101,'usd_24h_change':3,'last_updated_at':10}}
  self.assertEqual(m.crypto({'coins':['bitcoin']},fetch)['source'],'CoinGecko')
 def test_us_success_avoids_foreign_requests(self):
  fields=['']*36;fields[1]='Apple';fields[2]='AAPL.OQ';fields[3]='100';fields[30]='2026-10-30 16:00:00';fields[32]='-1';fields[35]='USD'
  def unexpected(url):raise AssertionError('unnecessary fallback')
  q=m.us({'us_stocks':['AAPL']},lambda url:('v_usAAPL="'+'~'.join(fields)+'";').encode(),unexpected);self.assertEqual(q['rows'][0]['price'],100)
 def test_yahoo_host_fallback(self):
  def fetch(url):
   if 'query1' in url:raise ValueError('offline')
   return {'chart':{'result':[{'meta':{'regularMarketPrice':110,'regularMarketTime':10},'indicators':{'quote':[{'close':[100,110]}]}}]}}
  self.assertAlmostEqual(m.yahoo('AAPL',fetch)['change'],10)
if __name__=='__main__':unittest.main()
