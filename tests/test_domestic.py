import sys,unittest,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
import domestic,editorial
class DomesticTests(unittest.TestCase):
 def test_domain_validation(self):
  rows=domestic.normalize([{'title':'ok','url':'https://www.zhihu.com/question/1'},{'title':'bad','url':'https://zhihu.com.evil.test/1'},{'title':'bad2','url':'javascript:alert(1)'}],['zhihu.com']);self.assertEqual(len(rows),1)
 def test_priority_metadata(self):
  nodes=domestic.board_nodes([{'name':name,'kind':'hot','items':[],'source_id':str(i)} for i,name in enumerate(domestic.PRIORITY)]);self.assertEqual([n['priority'] for n in nodes],list(range(6)));self.assertTrue(all(n['all'] for n in nodes))
 def test_toutiao_real_links(self):
  source={'adapter':'toutiao','url':'https://example.test','domains':['toutiao.com']};rows=domestic.fetch(source,lambda u:json.dumps({'data':[{'Title':'标题','ClusterIdStr':'123','HotValue':'100'}]}).encode());self.assertEqual(rows[0]['url'],'https://www.toutiao.com/trending/123/')
 def test_history_schema(self):
  source={'adapter':'sixty','url':'https://example.test','domains':['baidu.com']};rows=domestic.fetch(source,lambda u:json.dumps({'code':200,'data':{'items':[{'title':'event','link':'https://baike.baidu.com/item/1'}]}}).encode());self.assertEqual(len(rows),1)
 def test_snapshot_excluded(self):
  import tempfile
  with tempfile.TemporaryDirectory() as temp:
   engine=editorial.Editorial(temp);rows=engine.articles([{'url':'https://a.test','fetched_at':'2026-11-01T10:00:00Z','items':[{'title':'old','url':'https://a.test/post'}]}],[{'url':'https://a.test','snapshot':True}],editorial.DEFAULT);self.assertEqual(rows,[])
if __name__=='__main__':unittest.main()
