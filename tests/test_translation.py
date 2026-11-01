import sys, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
import translation
class TranslationTests(unittest.TestCase):
 def test_multibyte_chunks_preserve_text(self):
  text='中文与English混排。'*100
  parts=translation.chunks(text)
  self.assertEqual(''.join(parts),text)
  self.assertTrue(all(len(x.encode('utf-8'))<=450 for x in parts))
 def test_invalid_language_and_payload(self):
  for obj in ({'target':'fr','texts':['a']},{'target':'en','texts':[]},{'target':'en','texts':['x'*1601]},[],{'target':'en','texts':[1]}):
   with self.assertRaises(ValueError):translation.validate(obj)
 def test_matching_language_never_uses_network(self):
  with patch('urllib.request.urlopen',side_effect=AssertionError('network')):
   self.assertEqual(translation.translate('中文标题','zh-CN'),'中文标题')
 def test_failure_keeps_original(self):
  with patch.object(translation,'translate',side_effect=TimeoutError()):
   row=translation.batch({'target':'en','texts':['中文']})['results'][0]
   self.assertEqual(row['text'],'中文');self.assertIn('error',row)
 def test_successful_cache_avoids_second_request(self):
  import io,os
  with patch.dict(os.environ,{'LIBRETRANSLATE_URL':''}),patch('public_http.opener') as opener,patch.object(opener.return_value,'open',return_value=io.BytesIO(b'{"responseStatus":200,"responseData":{"translatedText":"Hello world"}}')) as request:
   translation.CACHE.clear()
   self.assertEqual(translation.translate('你好世界','en'),'Hello world')
   self.assertEqual(translation.translate('你好世界','en'),'Hello world')
   self.assertEqual(request.call_count,1)
if __name__=='__main__':unittest.main()
