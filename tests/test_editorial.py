import sys,unittest,tempfile,json,datetime,threading,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
import editorial as e
class EditorialTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name);(self.base/'content/weekly').mkdir(parents=True);self.editor=e.Editorial(self.base)
        self.sources=[{'id':'cn','name':'中文','url':'https://cn.test/feed','category':'dev','language':'zh','weight':120,'enabled':True},{'id':'en','name':'EN','url':'https://en.test/feed','category':'finance','language':'en','weight':80,'enabled':True}]
        e.atomic(self.base/'server/sources.json',self.sources)
    def tearDown(self):self.temp.cleanup()
    def article(self,title='Rust compiler release 1.80 improves performance',url='https://a.test/post',source='cn',cat='dev',stamp=100):
        return {'id':url,'canonical':e.canonical(url),'title':title,'url':url,'source_id':source,'category':cat,'time':stamp,'score':100,'age_hours':1}
    def test_tracking(self):self.assertEqual(e.canonical('https://a.test/p?utm_source=x&id=2#top'),'https://a.test/p?id=2')
    def test_events_preserve_sources(self):
        a=self.article();b=self.article(url='https://b.test/post',source='en');g=e.events([a,b]);self.assertEqual(len(g),1);self.assertEqual(g[0]['source_count'],2);self.assertEqual(len(g[0]['articles']),2)
    def test_numbers_categories_time_separate(self):
        a=self.article();variants=[self.article(title=a['title'].replace('1.80','1.81'),url='https://b.test/other'),self.article(cat='finance'),self.article(stamp=200000)]
        for b in variants:self.assertEqual(len(e.events([a,b])),2)
    def test_chinese_group(self):
        a=self.article(title='开源数据库发布全新查询引擎优化方案');b=self.article(title='开源数据库发布全新查询引擎优化方案',url='https://b.test');self.assertEqual(len(e.events([a,b])),1)
    def test_quotas_and_dedup(self):
        rows=[self.article(url='https://a.test/'+str(i)) for i in range(10)];settings={**e.DEFAULT,'per_source':2};self.assertEqual(len(self.editor.select(rows,settings)),2)
        self.assertEqual(len(self.editor.select([rows[0],rows[0]],settings)),1)
    def test_old_articles_excluded(self):
        a=self.article();a['age_hours']=100;self.assertEqual(self.editor.select([a],e.DEFAULT),[])
    def test_keyword_and_fallback_timestamp(self):
        feed={'url':self.sources[0]['url'],'fetched_at':'2026-11-01T10:00:00+08:00','items':[{'title':'Rust tutorial','url':'https://a.test/a'},{'title':'advert','url':'https://a.test/b'}]}
        settings={**e.DEFAULT,'include':['Rust'],'exclude':['advert']};rows=self.editor.articles([feed],self.sources,settings,clock=e.timestamp('2026-11-01T11:00:00+08:00'))
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['time_basis'],'fetched');self.assertIn('Rust',rows[0]['reason'])
    def test_disabled_source(self):
        self.sources[0]['enabled']=False;feed={'url':self.sources[0]['url'],'fetched_at':'2026-11-01T10:00:00+08:00','items':[{'title':'x','url':'https://a.test'}]};self.assertEqual(self.editor.articles([feed],self.sources,e.DEFAULT),[])
    def test_source_override(self):self.assertFalse(self.editor.sources({'source_overrides':{'cn':{'enabled':False}}})[0]['enabled'])
    def test_weekly_drafts_hidden(self):
        p=self.base/'content/weekly/test.md';p.write_text('# Week\n\n## Draft\nurl: https://example.com\nreason: text\nstatus: draft\n\n## Approved\nurl: https://example.com/post\nreason: useful\nstatus: published\n',encoding='utf-8');self.assertEqual(len(self.editor.weekly()[0]['items']),1)
    def test_archive_and_empty_day(self):
        old=self.base/'server/data/editions/2025-01-01.json';e.atomic(old,{'date':'2025-01-01','items':[]});result=self.editor.build([],{});self.assertIn('2025-01-01',result['archives']);self.assertEqual(e.read(old,{})['date'],'2025-01-01')

class RefreshTests(unittest.TestCase):
    def test_failure_retains_cache_and_backs_off(self):
        from unittest.mock import patch
        import app
        old=app.STATE
        app.STATE={'markets':{},'feeds':[{'url':'https://test.invalid/rss','items':[{'title':'cached'}],'failures':0}]}
        try:
            with patch.object(app,'feed',side_effect=ValueError('offline')),patch.object(app,'save'):
                app.refresh_feed({'url':'https://test.invalid/rss','name':'Test','interval':300})
            result=app.STATE['feeds'][0]
            self.assertEqual(result['items'][0]['title'],'cached');self.assertEqual(result['failures'],1)
            self.assertGreater(e.timestamp(result['next_check_at'])-time.time(),590)
        finally:app.STATE=old
    def test_same_source_not_overlapped(self):
        from unittest.mock import patch
        import app
        entered=threading.Event();release=threading.Event();calls=[];old=app.STATE
        app.STATE={'markets':{},'feeds':[]};source={'url':'https://overlap.invalid/rss','name':'Test','interval':300}
        def fake(source):
            calls.append(1);entered.set();release.wait(3);return {'url':source['url'],'items':[],'failures':0}
        try:
            with patch.object(app,'feed',side_effect=fake),patch.object(app,'save'):
                worker=threading.Thread(target=app.refresh_feed,args=(source,));worker.start();self.assertTrue(entered.wait(2));app.refresh_feed(source);release.set();worker.join(3);self.assertEqual(len(calls),1)
        finally:release.set();app.STATE=old

if __name__=='__main__':unittest.main()

