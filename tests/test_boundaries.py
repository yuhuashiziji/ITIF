import sys,unittest,json,tempfile,threading,urllib.request,urllib.error
from pathlib import Path
from unittest.mock import patch,Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
import app,editorial,domestic,rss_engine,public_http
class BoundaryTests(unittest.TestCase):
 def test_private_peer_rejected_after_resolution(self):
  sock=Mock();sock.getpeername.return_value=('127.0.0.1',80)
  with patch('socket.create_connection',return_value=sock):
   with self.assertRaises(ValueError):public_http.checked_connection(('example.test',80))
  sock.close.assert_called_once()
 def test_public_peer_allowed(self):
  sock=Mock();sock.getpeername.return_value=('1.1.1.1',443)
  with patch('socket.create_connection',return_value=sock):self.assertIs(public_http.checked_connection(('example.test',443)),sock)
  sock.close.assert_not_called()
 def test_both_protocols_check_connected_peer(self):
  self.assertIs(public_http.PublicHTTPConnection('example.test')._create_connection,public_http.checked_connection)
  self.assertIs(public_http.PublicHTTPSConnection('example.test')._create_connection,public_http.checked_connection)
 def test_utf16_dtd_rejected(self):
  raw='<?xml version="1.0" encoding="UTF-16"?><!DOCTYPE rss [<!ENTITY title "fixture">]><rss/>'.encode('utf-16')
  with self.assertRaisesRegex(ValueError,'实体'):rss_engine.root_of(raw)
 def test_custom_privacy_survives_projections(self):
  with tempfile.TemporaryDirectory() as temp:
   engine=editorial.Editorial(temp);config={'feeds':[{'name':'Private fixture','url':'https://example.test/feed'}]}
   source=engine.sources(config)[0];self.assertTrue(source['private'])
   with patch.object(app,'EDITOR',engine),patch.object(app,'CONFIG',config),patch.object(app,'STATE',{'markets':{},'feeds':[]}):
    data=app.client_state();self.assertTrue(data['feeds'][0]['private']);self.assertTrue(domestic.board_nodes(data['feeds'])[0]['private'])
   stamp='2026-11-01T10:00:00Z';items=engine.articles([{'url':source['url'],'fetched_at':stamp,'items':[{'title':'fixture','url':'https://example.test/a'}]}],[source],editorial.DEFAULT,clock=editorial.timestamp(stamp))
   self.assertTrue(items[0]['private'])
 def test_stock_is_persisted(self):
  fields=['']*33;fields[1]='Fixture';fields[2]='600519';fields[3]='1';fields[30]='20261101100000';fields[32]='0';response=('v="'+'~'.join(fields)+'";').encode('gbk')
  with patch.object(app,'STATE',{'markets':{},'feeds':[]}),patch.object(app,'request',return_value=response),patch.object(app,'save') as save:
   app.market('stock');save.assert_called_once()
 def test_non_finite_stock_quote_rejected(self):
  fields=['']*33;fields[1]='Fixture';fields[2]='600519';fields[3]='nan';fields[32]='0';response=('v="'+'~'.join(fields)+'";').encode('gbk')
  with patch.object(app,'STATE',{'markets':{},'feeds':[]}),patch.object(app,'request',return_value=response),patch.object(app,'save') as save:
   with self.assertRaises(ValueError):app.market('stock')
   save.assert_not_called()
class HttpBoundaryTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.server=app.ThreadingHTTPServer(('127.0.0.1',0),app.Handler);cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
 @classmethod
 def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.thread.join()
 def request(self,path,payload=None,host='127.0.0.1:8765',origin='http://127.0.0.1:8765'):
  req=urllib.request.Request('http://127.0.0.1:'+str(self.server.server_port)+path,data=None if payload is None else json.dumps(payload).encode(),headers={'Host':host,'Origin':origin,'Content-Type':'application/json'})
  try:
   with urllib.request.urlopen(req,timeout=4) as r:return r.status,r.read()
  except urllib.error.HTTPError as e:return e.code,e.read()
 def test_private_files_not_served(self):
  for url in ['/server/config.json','/server/data/cache.json','/.env','/../server/config.json','/spider/data/trans_cache.json','/tools/package_release.py']:self.assertEqual(self.request(url)[0],404,url)
 def test_host_and_origin_rejected(self):
  self.assertEqual(self.request('/api/status',host='evil.test')[0],403)
  self.assertEqual(self.request('/api/translate',{'texts':['fixture'],'target':'en'},origin='https://evil.test')[0],403)
 def test_invalid_json_type_returns_400(self):
  for url in ['/api/settings','/api/source','/api/feeds','/api/translate']:self.assertEqual(self.request(url,[])[0],400,url)
 def test_snapshot_export_uses_catalog(self):
  source={'id':'snap','name':'fixture','url':'https://example.test/feed','snapshot':True,'enabled':True};state={'markets':{},'feeds':[{'name':'fixture','url':source['url'],'items':[{'title':'OLD_FIXTURE','url':'https://example.test/old'}]}]}
  with patch.object(app.EDITOR,'sources',return_value=[source]),patch.object(app,'STATE',state):
   code,raw=self.request('/rss.xml');self.assertEqual(code,200);self.assertNotIn(b'OLD_FIXTURE',raw)
 def test_old_unknown_archive_sources_are_private(self):
  with tempfile.TemporaryDirectory() as temp:
   folder=Path(temp);(folder/'editions').mkdir();(folder/'editions/2026-11-01.json').write_text(json.dumps({'items':[{'source_id':'not-in-public-catalog','title':'fixture'}]}),encoding='utf-8')
   with patch.object(app,'DATA',folder):
    code,raw=self.request('/api/edition?date=2026-11-01');self.assertEqual(code,200);self.assertTrue(json.loads(raw)['items'][0]['private'])
if __name__=='__main__':unittest.main()
