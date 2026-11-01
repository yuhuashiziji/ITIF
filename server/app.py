"""Local RSS and market-data service. Python 3.10+, standard library only."""
import rss_engine
import editorial
import domestic
import market_adapters
import translation
import public_http
import concurrent.futures, datetime, ipaddress, json, os, socket, threading, time
import urllib.request, urllib.parse, xml.etree.ElementTree as ET
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE=Path(__file__).resolve().parent.parent
DATA=BASE/'server'/'data'; DATA.mkdir(exist_ok=True)
LOCK=threading.RLock()
EDITOR=editorial.Editorial(BASE)
SOURCE_LOCKS={}
SOURCE_LOCK_GUARD=threading.Lock()
def load(path,default):
    try:return json.loads(path.read_text(encoding='utf-8'))
    except (OSError,ValueError):return default
CONFIG=load(BASE/'server'/'config.json',load(BASE/'server'/'config.example.json',{}))
STATE=load(DATA/'cache.json',{'markets':{},'feeds':[]})
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save():
    with LOCK:
        tmp=DATA/'cache.tmp';tmp.write_text(json.dumps(STATE,ensure_ascii=False),encoding='utf-8');tmp.replace(DATA/'cache.json')
def public_url(url):
    p=urllib.parse.urlsplit(url)
    if p.scheme not in ('http','https') or not p.hostname or p.username or p.password:raise ValueError('需要公开 HTTP/HTTPS 地址')
    for addr in socket.getaddrinfo(p.hostname,p.port or (443 if p.scheme=='https' else 80),type=socket.SOCK_STREAM):
        if not ipaddress.ip_address(addr[4][0]).is_global:raise ValueError('不允许访问本地或内网地址')
    return url
class Redirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        public_url(newurl);return super().redirect_request(req,fp,code,msg,headers,newurl)
def request(url):
    public_url(url)
    req=urllib.request.Request(url,headers={'User-Agent':'DailyAggregator/1.0 (personal dashboard)','Accept':'application/json, application/xml, text/xml, */*'})
    with public_http.opener(Redirect).open(req,timeout=12) as r:
        data=r.read(4_000_001)
        if len(data)>4_000_000:raise ValueError('响应过大')
        return data
def getjson(url):return json.loads(request(url))
def market(kind):
    if kind in ('crypto','us'):
        result=market_adapters.crypto(CONFIG,getjson) if kind=='crypto' else market_adapters.us(CONFIG,request,getjson)
        with LOCK:STATE['markets'][kind]={**result,'fetched_at':now()}
        save()
        return

    rows=[];errors=[]
    source={'stock':'腾讯财经公开行情','us':'Yahoo Finance（个人使用）','crypto':'CoinGecko'}[kind]
    if kind=='stock':
        symbols=CONFIG.get('stocks',['sh600519','sz300750','sh688981'])
        text=request('https://qt.gtimg.cn/q='+','.join(symbols)).decode('gbk',errors='replace')
        for line in text.split(';'):
            if '="' not in line:continue
            a=line.split('="',1)[1].strip('"\r\n').split('~')
            if len(a)>32 and a[3]:rows.append({'name':a[1],'symbol':a[2],'price':market_adapters.number(a[3]),'change':market_adapters.number(a[32]),'time':a[30],'currency':'CNY'})
    if not rows:raise ValueError('; '.join(errors) or '来源没有返回有效行情')
    with LOCK:STATE['markets'][kind]={'rows':rows,'source':source,'fetched_at':now(),'error':'; '.join(errors),'stale':bool(errors)}
    save()
def feed(source):
    url=source['url']
    if source.get('kind')=='hot':
        if source.get('snapshot'):raise ValueError('暂无稳定公开榜单，保留明确标注的历史快照')
        return {**source,'source_id':source['id'],'items':domestic.fetch(source,request),'fetched_at':now(),'checked_at':now(),'error':'','failures':0}
    with LOCK:old=next((x for x in STATE['feeds'] if x['url']==url),{})
    headers={}
    if old.get('etag'):headers['If-None-Match']=old['etag']
    if old.get('last_modified'):headers['If-Modified-Since']=old['last_modified']
    raw,response_headers,final,status=rss_engine.fetch(url,public_url,Redirect,headers)
    if status==304:return {**old,'name':source['name'],'category':source.get('category','news'),'language':source.get('language','en'),'weight':source.get('weight',80),'checked_at':now(),'error':'','failures':0}
    items=rss_engine.parse(raw,final)
    return {'name':source['name'],'source_id':source.get('id'),'kind':source.get('kind','rss'),'category':source.get('category','news'),'language':source.get('language','en'),'weight':source.get('weight',80),'url':url,'items':items,'fetched_at':now(),'checked_at':now(),'error':'','failures':0,'etag':response_headers.get('ETag',''),'last_modified':response_headers.get('Last-Modified','')}

def refresh_feed(source):
    with SOURCE_LOCK_GUARD:guard=SOURCE_LOCKS.setdefault(source['url'],threading.Lock())
    if not guard.acquire(blocking=False):return
    try:
        try:result=feed(source)
        except Exception as e:
            with LOCK:old=next((x for x in STATE['feeds'] if x['url']==source['url']),{})
            result={**old,'name':source['name'],'category':source.get('category','news'),'language':source.get('language','en'),'weight':source.get('weight',80),'url':source['url'],'items':old.get('items',[]),'error':str(e),'checked_at':now(),'failures':old.get('failures',0)+1}
        interval=max(300,int(source.get('interval',900)))*min(16,2**min(4,result.get('failures',0)))
        result['next_check_at']=(datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(seconds=interval)).isoformat()
        with LOCK:STATE['feeds']=[x for x in STATE['feeds'] if x['url']!=source['url']]+[result]
        save()
    finally:guard.release()

def refresh_market(kind):
    try:market(kind)
    except Exception as e:
        with LOCK:STATE['markets'][kind]={**STATE['markets'].get(kind,{}),'error':str(e),'stale':True}
def scheduler():
    pending={};market_due={};edition_due=0;pool=concurrent.futures.ThreadPoolExecutor(max_workers=8)
    while True:
        with LOCK:sources=EDITOR.sources(CONFIG);feeds={f['url']:f for f in STATE['feeds']}
        for source in sources:
            key=source['url']
            if not source.get('enabled',True) or (key in pending and not pending[key].done()):continue
            due=editorial.timestamp(feeds.get(key,{}).get('next_check_at','')) or 0
            if time.time()>=due:pending[key]=pool.submit(refresh_feed,source)
        for kind in ('stock','us','crypto'):
            key='market:'+kind
            if time.time()>=market_due.get(kind,0) and (key not in pending or pending[key].done()):
                pending[key]=pool.submit(refresh_market,kind);market_due[kind]=time.time()+max(300,int(CONFIG.get('market_interval',300)))
        if time.time()>=edition_due:
            with LOCK:snapshot=json.loads(json.dumps(STATE['feeds']));config=json.loads(json.dumps(CONFIG))
            EDITOR.build(snapshot,config);edition_due=time.time()+300
        time.sleep(3)
REFRESH_LOCK=threading.Lock()
def manual_refresh():
    try:
        with LOCK:sources=[x for x in EDITOR.sources(CONFIG) if x.get('enabled',True)]
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(refresh_feed,sources))
        save()
    finally:REFRESH_LOCK.release()

def client_state():
    with LOCK:
        data=json.loads(json.dumps(STATE));cached={f['url']:f for f in data['feeds']}
        data['feeds']=[{**cached.get(s['url'],{'items':[]}),**{k:s.get(k) for k in ('name','url','category','language','weight','kind','snapshot','private','id')},'source_id':s['id']} for s in EDITOR.sources(CONFIG) if s.get('enabled',True)]
        return data

class Handler(BaseHTTPRequestHandler):
    def reply(self,body,status=200,ctype='application/json; charset=utf-8'):
        raw=json.dumps(body,ensure_ascii=False).encode() if isinstance(body,dict) else body
        self.send_response(status);self.send_header('Content-Type',ctype);self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('X-Frame-Options','DENY');self.send_header('Referrer-Policy','no-referrer');self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        if self.headers.get('Host','') not in ('127.0.0.1:8765','localhost:8765'):return self.reply({'error':'Invalid Host'},403)
        path=urllib.parse.urlsplit(self.path).path
        if path=='/api/editorial':
            with LOCK:feeds=json.loads(json.dumps(STATE['feeds']));config=json.loads(json.dumps(CONFIG))
            return self.reply(EDITOR.build(feeds,config))
        if path=='/api/edition':
            date=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query).get('date',[''])[0]
            import re
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',date):return self.reply({'error':'Invalid date'},400)
            edition=editorial.read(DATA/'editions'/f'{date}.json',None)
            if edition:
                public_ids={s['id'] for s in editorial.read(BASE/'server/sources.json',[]) if not s.get('private')}
                for article in edition.get('items',[]):
                    article['private']=bool(article.get('private')) or article.get('source_id') not in public_ids
            return self.reply(edition or {'error':'Not found'},200 if edition else 404)
        if path=='/editorial.js':return self.reply((BASE/'server/editorial.js').read_bytes(),ctype='application/javascript; charset=utf-8')
        if path=='/rss.xml':
            with LOCK:
                active={s['url'] for s in EDITOR.sources(CONFIG) if s.get('enabled',True) and not s.get('snapshot')};return self.reply(rss_engine.export([f for f in STATE['feeds'] if f['url'] in active and not f.get('snapshot')]),ctype='application/rss+xml; charset=utf-8')
        if path=='/api/status':return self.reply(client_state())
        if path in ('/','/index.html'):
            bootstrap=client_state();feeds=bootstrap['feeds']
            payload=json.dumps(bootstrap,ensure_ascii=False).replace('<','\\u003c').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
            nodes=json.dumps(domestic.board_nodes(feeds),ensure_ascii=False).replace('<','\\u003c')
            html=(BASE/'每日聚合站_融合版.html').read_text(encoding='utf-8')
            html=html.replace('/* ============ 初始渲染 ============ */','window.__BOOTSTRAP__='+payload+'; NODES='+nodes+';\n/* ============ 初始渲染 ============ */')
            return self.reply(html.encode('utf-8'),ctype='text/html; charset=utf-8')
        if path=='/design.css':return self.reply((BASE/'server/design.css').read_bytes(),ctype='text/css; charset=utf-8')
        if path=='/design.js':return self.reply((BASE/'server/design.js').read_bytes(),ctype='application/javascript; charset=utf-8')
        if path=='/translate.js':return self.reply((BASE/'server/translate.js').read_bytes(),ctype='application/javascript; charset=utf-8')
        if path=='/reader.js':return self.reply((BASE/'server/reader.js').read_bytes(),ctype='application/javascript; charset=utf-8')
        if path=='/live.js':return self.reply((BASE/'server/live.js').read_bytes(),ctype='application/javascript; charset=utf-8')
        self.reply({'error':'Not found'},404)
    def do_POST(self):
        if self.headers.get('Host','') not in ('127.0.0.1:8765','localhost:8765') or self.headers.get('Origin') not in ('http://127.0.0.1:8765','http://localhost:8765'):return self.reply({'error':'Invalid origin'},403)
        if self.path=='/api/translate':
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=24000:raise ValueError('翻译请求过大或为空')
                return self.reply(translation.batch(json.loads(self.rfile.read(length))))
            except (ValueError,TypeError) as e:return self.reply({'error':str(e)},400)
        if self.path in ('/api/settings','/api/source'):
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=16000:raise ValueError('Invalid request size')
                obj=json.loads(self.rfile.read(length))
                if not isinstance(obj,dict):raise ValueError('请求必须是 JSON 对象')
                if self.path=='/api/settings':
                    settings=EDITOR.settings()
                    for key in ('include','exclude'):
                        values=obj.get(key,settings[key])
                        if not isinstance(values,list) or len(values)>30 or any(not isinstance(x,str) or not 1<=len(x)<=80 for x in values):raise ValueError('关键词格式错误')
                        settings[key]=values
                    for key,lo,hi in [('max_items',1,100),('per_source',1,10),('hours',1,168)]:
                        value=obj.get(key,settings[key])
                        if type(value) is not int or not lo<=value<=hi:raise ValueError('数量或时间范围错误')
                        settings[key]=value
                    quotas=obj.get('quotas',settings['quotas'])
                    if not isinstance(quotas,dict) or any(k not in ('tech','finance','dev','ai','news','ent','shopping') or type(v) is not int or not 0<=v<=100 for k,v in quotas.items()):raise ValueError('分类配额错误')
                    settings['quotas']=quotas
                    with EDITOR.lock:editorial.atomic(DATA/'editorial-settings.json',settings)
                else:
                    source=next((s for s in EDITOR.sources(CONFIG) if s['id']==obj.get('id')),None)
                    if not source:raise ValueError('来源不存在')
                    values={k:obj.get(k,source.get(k)) for k in ('enabled','weight','interval','language','category')}
                    if type(values['enabled']) is not bool or type(values['weight']) is not int or not 0<=values['weight']<=200 or type(values['interval']) is not int or not 300<=values['interval']<=604800 or values['language'] not in ('zh','en','other') or values['category'] not in ('tech','finance','dev','ai','news','ent','shopping'):raise ValueError('来源配置错误')
                    with LOCK:
                        CONFIG.setdefault('source_overrides',{})[source['id']]=values;editorial.atomic(BASE/'server/config.json',CONFIG)
                return self.reply({'ok':True})
            except (ValueError,TypeError,KeyError) as e:return self.reply({'error':str(e)},400)
        if self.path=='/api/refresh':
            if not REFRESH_LOCK.acquire(blocking=False):return self.reply({'ok':True,'running':True},202)
            threading.Thread(target=manual_refresh,daemon=True).start()
            return self.reply({'ok':True,'running':True},202)
        if self.path!='/api/feeds':return self.reply({'error':'Not found'},404)
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=4096:raise ValueError('请求过大或为空')
            obj=json.loads(self.rfile.read(length))
            if not isinstance(obj,dict):raise ValueError('请求必须是 JSON 对象')
            name=str(obj.get('name','')).strip()[:100];url=rss_engine.resolve(str(obj.get('url','')).strip(),public_url,Redirect,CONFIG.get('rsshub_base','https://rsshub.app'))
            if not name:raise ValueError('请输入名称')
            with LOCK:
                feeds=CONFIG.setdefault('feeds',[])
                if len(feeds)>=50:raise ValueError('最多 50 个订阅源')
                if not any(x['url']==url for x in feeds):feeds.append({'name':name,'url':url})
                tmp=BASE/'server/config.tmp';tmp.write_text(json.dumps(CONFIG,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(BASE/'server/config.json')
            threading.Thread(target=lambda: (refresh_feed({'name':name,'url':url}),save()),daemon=True).start()
            self.reply({'ok':True,'url':url})
        except Exception as e:self.reply({'error':str(e)},400)
if __name__=='__main__':
    threading.Thread(target=scheduler,daemon=True).start()
    print('Daily Aggregator: http://127.0.0.1:8765',flush=True)
    ThreadingHTTPServer(('127.0.0.1',8765),Handler).serve_forever()
