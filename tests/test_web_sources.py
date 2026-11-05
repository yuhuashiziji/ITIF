import sys,json,datetime,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'server'));import web_sources
class WebTests(unittest.TestCase):
    def source(self):return {'url':'https://news.example.org/','domains':['example.org'],'article_pattern':r'/20\d{2}/\d{2}/\d{2}/\w+\.html','min_items':1}
    def test_extract_filters_navigation_duplicate_and_old(self):
        raw=b'''<a href="/2026/11/05/story.html">A real article headline</a><a href="/2026/11/05/story.html">Repeated article headline</a><a href="/2020/01/01/old.html">An old article headline</a><a href="https://evil.example.net/2026/11/05/x.html">Offsite article headline</a><a href="/login">Navigation headline</a>'''
        rows=web_sources.extract(raw,self.source(),datetime.datetime(2026,11,5));self.assertEqual(len(rows),1);self.assertEqual(rows[0]['published'],'');self.assertEqual(rows[0]['heat'],'');self.assertEqual(rows[0]['url'],'https://news.example.org/2026/11/05/story.html')
    def test_layout_failure_does_not_publish_navigation(self):
        with self.assertRaises(ValueError):web_sources.extract(b'<a href="/">Navigation only</a>',self.source())
    def test_robots_disallow(self):
        web_sources._robots.clear();self.assertFalse(web_sources.allowed('https://example.org/private',lambda u:b'User-agent: *\nDisallow: /private'))
    def test_robots_failure_is_closed(self):
        web_sources._robots.clear()
        def fail(u):raise OSError()
        self.assertFalse(web_sources.allowed('https://example.org/',fail))
if __name__=='__main__':unittest.main()
