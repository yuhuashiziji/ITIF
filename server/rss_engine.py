"""Independent RSS/Atom discovery and refresh engine (no third-party source code)."""
import urllib.parse, urllib.request, urllib.error
import xml.etree.ElementTree as ET
import public_http
from html.parser import HTMLParser

class Discovery(HTMLParser):
    def __init__(self,base):super().__init__();self.base=base;self.urls=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='link' and 'alternate' in a.get('rel','').lower().split() and a.get('type','').lower() in ('application/rss+xml','application/atom+xml','application/feed+json'):
            url=urllib.parse.urljoin(self.base,a.get('href',''))
            if urllib.parse.urlsplit(url).scheme in ('http','https') and url not in self.urls:self.urls.append(url)
def root_of(raw):
    declarations=raw.replace(b'\x00',b'').upper()
    if b'<!DOCTYPE' in declarations or b'<!ENTITY' in declarations:raise ValueError('XML 实体声明不受支持')
    root=ET.fromstring(raw)
    if root.tag.split('}')[-1] not in ('rss','feed','RDF'):raise ValueError('不是 RSS/Atom 文档')
    return root
def fetch(url,public_url,redirect,headers=None):
    public_url(url)
    req=urllib.request.Request(url,headers={'User-Agent':'DailyAggregator/1.0','Accept':'application/rss+xml, application/atom+xml, application/xml, text/html;q=0.8',**(headers or {})})
    try:
        with public_http.opener(redirect).open(req,timeout=12) as r:
            raw=r.read(4_000_001)
            if len(raw)>4_000_000:raise ValueError('订阅响应超过 4 MB')
            return raw,dict(r.headers),r.url,200
    except urllib.error.HTTPError as e:
        if e.code==304:return b'',{},url,304
        raise
def resolve(url,public_url,redirect,base='https://rsshub.app'):
    if url.startswith('rsshub://'):
        return base.rstrip('/')+'/'+url[len('rsshub://'):].lstrip('/')
    raw,headers,final,status=fetch(url,public_url,redirect)
    try:root_of(raw);return final
    except (ET.ParseError,ValueError):pass
    parser=Discovery(final);parser.feed(raw.decode('utf-8',errors='replace'))
    if not parser.urls:raise ValueError('网页未声明 RSS/Atom，请提供订阅地址或 RSSHub 地址')
    errors=[]
    for candidate in parser.urls[:5]:
        try:
            raw,_,final,_=fetch(candidate,public_url,redirect);root_of(raw);return final
        except Exception as e:errors.append(str(e))
    raise ValueError('发现的订阅均不可用：'+'; '.join(errors))
class PlainText(HTMLParser):
    def __init__(self):super().__init__();self.parts=[]
    def handle_data(self,data):self.parts.append(data)
def plain(value):
    p=PlainText();p.feed(value);return ' '.join(' '.join(p.parts).split())[:500]

def parse(raw,url):
    root=root_of(raw);items=[];seen=set()
    def text(el,name):
        return next((''.join(c.itertext()).strip() for c in el if c.tag.split('}')[-1]==name),'')
    for node in root.iter():
        if node.tag.split('}')[-1] not in ('item','entry'):continue
        title=text(node,'title');link=text(node,'link')
        if not link:link=next((c.get('href','') for c in node if c.tag.split('}')[-1]=='link' and c.get('rel','alternate')=='alternate'),'')
        if not link:continue
        link=urllib.parse.urljoin(url,link)
        if not title or urllib.parse.urlsplit(link).scheme not in ('http','https') or link in seen:continue
        seen.add(link);items.append({'title':title,'url':link,'published':text(node,'pubDate') or text(node,'published') or text(node,'updated'),'summary':plain(text(node,'description') or text(node,'summary'))})
    return items[:100]
def export(feeds):
    root=ET.Element('rss',version='2.0');channel=ET.SubElement(root,'channel')
    for key,val in [('title','ITIF 信息台订阅'),('link','http://127.0.0.1:8765/'),('description','个人订阅聚合')]:ET.SubElement(channel,key).text=val
    seen=set()
    for feed in feeds:
        for row in feed.get('items',[]):
            if row['url'] in seen:continue
            seen.add(row['url']);item=ET.SubElement(channel,'item')
            for key,val in [('title',row['title']),('link',row['url']),('guid',row['url']),('description',feed['name'])]:ET.SubElement(item,key).text=val
    return ET.tostring(root,encoding='utf-8',xml_declaration=True)
