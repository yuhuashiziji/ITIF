"""Public HTML extraction with Scrapling; networking stays on the validated transport.

No browser, login state, proxy pool or external article bodies are required.
"""
import datetime as dt, re, threading, time
from urllib.parse import urljoin,urlsplit,urlunsplit
from urllib.robotparser import RobotFileParser
from rss_engine import plain
_guard=threading.Lock();_locks={};_last={};_robots={}
def lock_for(host):
    with _guard:return _locks.setdefault(host,threading.Lock())
def allowed(url,request):
    p=urlsplit(url);base=p.scheme+'://'+p.netloc
    with _guard:cached=_robots.get(base)
    if cached is None:
        try:
            raw=request(base+'/robots.txt').decode('utf-8',errors='replace')
            # An HTML error page is not a robots policy; fail closed.
            if '<html' in raw[:300].lower():raise ValueError('Invalid robots')
            robot=RobotFileParser();robot.parse(raw.splitlines());cached=robot
        except Exception:cached=False
        with _guard:_robots[base]=cached
    return cached is not False and cached.can_fetch('ITIF',url)
def normalize_link(url,base,source):
    try:
        p=urlsplit(urljoin(base,url));host=(p.hostname or '').lower()
        if p.scheme not in ('http','https') or p.username or p.password:return None
        if not any(host==d or host.endswith('.'+d) for d in source['domains']):return None
        if not re.search(source['article_pattern'],p.path):return None
        return urlunsplit((p.scheme,p.netloc,p.path,p.query,''))
    except ValueError:return None
def extract(raw,source,clock=None):
    from scrapling import Selector
    page=Selector(content=raw,url=source['url']);rows=[];seen=set()
    clock=clock or dt.datetime.now(dt.timezone.utc)
    for a in page.css(source.get('selector','a[href]')):
        link=normalize_link(a.attrib.get('href',''),source['url'],source)
        title=plain(' '.join(a.xpath('.//text()').getall())).strip()
        if not link or link in seen or not 8<=len(title)<=180:continue
        # Date in the URL is only used to reject clearly old stories, never presented as a precise publication time.
        m=re.search(r'/(20\d{2})[/-](\d{2})[/-](\d{2})/',urlsplit(link).path)
        if m:
            try:
                age=(clock.date()-dt.date(*map(int,m.groups()))).days
                if age>7 or age< -1:continue
            except ValueError:continue
        seen.add(link);rows.append({'title':title,'url':link,'published':'','heat':'','summary':'','time_basis':'observed','rank_basis':'homepage_order'})
        if len(rows)>=30:break
    if len(rows)<source.get('min_items',3):raise ValueError('Page layout or content validation failed')
    return rows
def fetch(source,request):
    host=urlsplit(source['url']).hostname
    with lock_for(host):
        pause=max(0,2-(time.monotonic()-_last.get(host,0)))
        if pause:time.sleep(pause)
        try:
            if not allowed(source['url'],request):raise ValueError('Robots unavailable or disallowed')
            return extract(request(source['url']),source)
        finally:_last[host]=time.monotonic()
