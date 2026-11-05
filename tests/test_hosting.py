import os,sys,tempfile,unittest,json,zipfile,subprocess,urllib.request,urllib.error,socket,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import build_public_snapshot as exporter
import package_php
import shutil
PHP=os.environ.get('ITIF_TEST_PHP') or shutil.which('php')
def http(url,data=None,headers=None):
    try:
        with urllib.request.urlopen(urllib.request.Request(url,data=data,headers=headers or {}),timeout=10) as r:return r.status,r.read(),r.headers
    except urllib.error.HTTPError as r:return r.code,r.read(),r.headers
class HostingTests(unittest.TestCase):
    def test_export_ignores_local_and_prior_private_state(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'snapshot.json';p.write_text(json.dumps({'status':{'feeds':[{'source_id':'secret','private':True,'items':[{'title':'PRIVATE_SENTINEL','url':'http://example.org'}]}]}}))
            exporter.build(p,offline=True);v=json.loads(p.read_text(encoding='utf-8'))
            self.assertNotIn('PRIVATE_SENTINEL',p.read_text(encoding='utf-8'));self.assertEqual(len(v['status']['feeds']),len([s for s in json.loads((ROOT/'server/sources.json').read_text(encoding='utf-8')) if s.get('enabled',True) and not s.get('private')]))
            self.assertTrue(all(not f.get('private') and not f['items'] for f in v['status']['feeds']))
            self.assertTrue(v['editorial']['read_only'])
    def test_failure_keeps_original_time_and_public_links(self):
        from unittest.mock import patch
        s={'id':'example','name':'example','url':'https://example.org/rss','kind':'rss','category':'news','language':'en','weight':80}
        with patch.object(exporter,'request',side_effect=RuntimeError('PRIVATE_EXCEPTION')):
            f=exporter.fetch_feed(s,{'fetched_at':'2026-10-01T00:00:00Z','items':[{'title':'valid','url':'https://example.org/a'},{'title':'bad','url':'javascript:alert(1)'}]})
        self.assertEqual(f['fetched_at'],'2026-10-01T00:00:00Z');self.assertEqual(len(f['items']),1);self.assertNotIn('PRIVATE_EXCEPTION',json.dumps(f))
    @unittest.skipUnless(PHP,"PHP CLI unavailable")
    def test_php_subfolder_and_boundaries(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);package_php.build(base);site=base/'itif';site.mkdir()
            with zipfile.ZipFile(base/'itif-php85.zip') as z:
                self.assertNotIn('config.php',z.namelist());self.assertFalse(any(n.endswith('.py') for n in z.namelist()));z.extractall(site)
            seed=json.loads((site/'seed.php').read_text(encoding='utf-8').split('\n',1)[1]);(site/'runtime').mkdir()
            (site/'runtime/snapshot.php').write_text('<?php exit; ?>\n'+json.dumps({'checked':int(time.time()),'value':seed,'error':''}),encoding='utf-8')
            with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
            process=subprocess.Popen([str(PHP),'-S',f'127.0.0.1:{port}','-t',str(base)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            url=f'http://127.0.0.1:{port}/itif/'
            try:
                for _ in range(50):
                    try:status,raw,h=http(url+'api.php?action=health');break
                    except OSError:time.sleep(.05)
                self.assertEqual(status,200);v=json.loads(raw);self.assertTrue(v['ok']);self.assertIn('delivery',v)
                status,raw,h=http(url);self.assertEqual(status,200);text=raw.decode();self.assertIn('window.ITIF_PUBLIC=true',text);self.assertIn('api.php?action=rss',text);self.assertNotIn('src="/',text);self.assertNotIn('href="/',text)
                self.assertEqual(h['X-Frame-Options'],'DENY')
                status,raw,h=http(url+'api.php?action=status');self.assertEqual(status,200);v=json.loads(raw);self.assertEqual(len(v['feeds']),len(seed['status']['feeds']));self.assertTrue(all(not f.get('private') for f in v['feeds']))
                for name in ['seed.php','template.php','config.example.php','runtime/snapshot.php']:
                    status,raw,h=http(url+name);self.assertEqual(raw,b'',name)
                self.assertEqual(http(url+'lib.php')[0],404)
                self.assertEqual(http(url+'api.php?action=source',b'{}')[0],404)
                self.assertEqual(http(url+'api.php?action=status',b'{}')[0],405)
                self.assertEqual(http(url+'api.php?action=translate',b'{}',{'Origin':'https://evil.example'})[0],403)
                self.assertEqual(http(url+'api.php?action=translate',b'{"texts":17}',{'Origin':url.split('/itif')[0]})[0],400)
                self.assertEqual(http(url+'api.php?action=edition&date=../../config.php')[0],400)
                status,raw,h=http(url+'api.php?action=rss');self.assertEqual(status,200);self.assertIn(b'<rss version="2.0">',raw);self.assertNotIn(b'127.0.0.1',raw)
                from xml.etree import ElementTree
                ElementTree.fromstring(raw)
                for p in site.glob('*.php'):subprocess.run([str(PHP),'-l',str(p)],check=True,capture_output=True)
                for p in site.glob('*.js'):subprocess.run(['node','--check',str(p)],check=True,capture_output=True)
            finally:process.terminate();process.wait(timeout=10)
if __name__=='__main__':unittest.main(verbosity=2)
