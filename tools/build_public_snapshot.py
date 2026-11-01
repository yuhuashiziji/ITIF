"""Fetch only the checked-in public catalog; never import the local application state."""
import argparse, concurrent.futures, datetime as dt, ipaddress, json, socket, sys, tempfile, shutil
from pathlib import Path
from urllib.parse import urlsplit
import urllib.request
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'server'))
import domestic, editorial, market_adapters, public_http, rss_engine
def now():return dt.datetime.now(dt.timezone.utc).isoformat()
def public_url(url):
    p=urlsplit(url)
    if p.scheme not in ('http','https') or not p.hostname or p.username or p.password:raise ValueError('Invalid public URL')
    for a in socket.getaddrinfo(p.hostname,p.port or (443 if p.scheme=='https' else 80),type=socket.SOCK_STREAM):
        if not ipaddress.ip_address(a[4][0]).is_global:raise ValueError('Non-public address')
class Redirect(public_http.Redirect):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        public_url(newurl);return super().redirect_request(req,fp,code,msg,headers,newurl)
def request(url):
    public_url(url)
    req=urllib.request.Request(url,headers={'User-Agent':'ITIF/0.2 public-feed-reader','Accept':'application/json,application/xml,*/*'})
    with public_http.opener(Redirect).open(req,timeout=12) as r:
        b=r.read(4_000_001)
        if len(b)>4_000_000:raise ValueError('Too large')
        return b
def getjson(url):return json.loads(request(url))
def valid_link(url):
    try:
        p=urlsplit(url)
        return p.scheme in ('http','https') and bool(p.hostname) and not p.username and not p.password
    except ValueError:return False
def public_items(items):
    return [{k:str(a.get(k,''))[:(2000 if k=='url' else 300)] for k in ('title','url','heat','published')} for a in items[:40] if valid_link(a.get('url','')) and a.get('title')]
def fetch_feed(s,old):
    result={k:s[k] for k in ('id','name','url','category','language','weight','kind','snapshot') if k in s}
    result.update(source_id=s['id'],private=False,checked_at=now(),next_check_at=(dt.datetime.now(dt.timezone.utc)+dt.timedelta(seconds=max(1800,s.get('interval',1800)))).isoformat())
    if s.get('snapshot'):
        return {**result,'items':[],'error':'暂无稳定免费公开榜单','fetched_at':None}
    # Respect source intervals and previous failure backoff; a scheduled run is not a forced refresh.
    due=editorial.timestamp(old.get('next_check_at','')) or 0
    if due>dt.datetime.now().timestamp():
        return {**result,**{k:old[k] for k in ('items','fetched_at','checked_at','next_check_at','error','failures') if k in old},'items':public_items(old.get('items',[]))}
    try:
        items=domestic.fetch(s,request) if s.get('kind')=='hot' else rss_engine.parse(request(s['url']),s['url'])
        if not items:raise ValueError('No articles')
        result.update(items=public_items(items),fetched_at=now(),error='',failures=0)
    except Exception:
        fails=min(4,int(old.get('failures',0))+1)
        result.update(items=public_items(old.get('items',[])),fetched_at=old.get('fetched_at'),error='来源暂不可用，保留上次成功数据',failures=fails,next_check_at=(dt.datetime.now(dt.timezone.utc)+dt.timedelta(seconds=max(1800,s.get('interval',1800))*2**fails)).isoformat())
    return result
def stock(config):
    raw=request('https://qt.gtimg.cn/q='+','.join(config['stocks'])).decode('gbk',errors='replace');rows=[]
    for line in raw.split(';'):
        if '="' not in line:continue
        a=line.split('="',1)[1].strip('"\r\n').split('~')
        if len(a)>32 and a[3]:rows.append({'name':a[1],'symbol':a[2],'price':market_adapters.number(a[3]),'change':market_adapters.number(a[32]),'time':a[30],'currency':'CNY','basis':'较前收盘涨跌 · 来源时间'})
    if not rows:raise ValueError('No quotes')
    return {'rows':rows,'source':'腾讯公开行情','error':'','stale':False}
def quote(kind,config,old):
    try:
        result=stock(config) if kind=='stock' else market_adapters.crypto(config,getjson) if kind=='crypto' else market_adapters.us(config,request,getjson)
        if result.get('error'):result['error']='部分行情暂不可用'
        return {**result,'fetched_at':now(),'checked_at':now()}
    except Exception:return {**old,'rows':old.get('rows',[]),'error':'来源暂不可用，行情可能过期','stale':True,'checked_at':now()}
def build(output,offline=False):
    sources=[s for s in json.loads((ROOT/'server/sources.json').read_text(encoding='utf-8')) if s.get('enabled',True) and not s.get('private')]
    config=json.loads((ROOT/'server/config.example.json').read_text(encoding='utf-8'));config['feeds']=[]
    # Only this public artifact is eligible for retry fallback. Local runtime caches are never read.
    old=editorial.read(output,{}) if not offline else {};previous={f['source_id']:f for f in old.get('status',{}).get('feeds',[]) if f.get('source_id') in {s['id'] for s in sources} and not f.get('private')}
    if offline:
        feeds=[{**s,'source_id':s['id'],'items':[],'error':'等待首次公开抓取','private':False} for s in sources];markets={}
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            feeds=list(pool.map(lambda s:fetch_feed(s,previous.get(s['id'],{})),sources))
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            markets=dict(zip(('stock','us','crypto'),pool.map(lambda k:quote(k,config,old.get('status',{}).get('markets',{}).get(k,{})),('stock','us','crypto'))))
    with tempfile.TemporaryDirectory() as folder:
        base=Path(folder);(base/'server').mkdir();(base/'server/sources.json').write_text(json.dumps(sources),encoding='utf-8')
        shutil.copytree(ROOT/'content',base/'content');ed=editorial.Editorial(base).build(feeds,config)
    ed['read_only']=True
    editions={k:v for k,v in old.get('editions',{}).items() if k in old.get('editorial',{}).get('archives',[]) and all(not a.get('private') and a.get('source_id') in previous for a in v.get('items',[]))}
    editions[ed['daily']['date']]=ed['daily'];editions={k:editions[k] for k in sorted(editions,reverse=True)[:7]};ed['archives']=list(editions)
    data={'schema':1,'generated_at':now(),'status':{'feeds':feeds,'markets':markets,'read_only':True},'editorial':ed,'editions':editions}
    output.parent.mkdir(parents=True,exist_ok=True);temp=output.with_suffix('.tmp');temp.write_text(json.dumps(data,ensure_ascii=False,allow_nan=False,separators=(',',':')),encoding='utf-8');temp.replace(output)
    print('Public snapshot:',len(feeds),'sources,',sum(len(f['items']) for f in feeds),'articles,',len(markets),'market groups')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=ROOT/'public-data/snapshot.json');p.add_argument('--offline',action='store_true');a=p.parse_args();build(a.output,a.offline)
