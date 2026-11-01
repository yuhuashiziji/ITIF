"""Opt-in page translation. No credentials or text are stored on disk."""
import concurrent.futures, html, json, os, threading, urllib.parse, urllib.request
from collections import OrderedDict
import public_http
CACHE=OrderedDict()
LOCK=threading.Lock()
SLOTS=threading.BoundedSemaphore(3)

def chunks(text, limit=450):
    result=[];part=''
    for ch in text:
        if len((part+ch).encode('utf-8'))>limit:
            result.append(part);part=''
        part+=ch
    if part:result.append(part)
    return result

def validate(obj):
    if not isinstance(obj,dict) or obj.get('target') not in ('zh-CN','en'):raise ValueError('只支持中文或英文')
    texts=obj.get('texts')
    if not isinstance(texts,list) or not 1<=len(texts)<=12 or any(not isinstance(t,str) or not 1<=len(t)<=1600 for t in texts) or sum(len(t) for t in texts)>5000:raise ValueError('翻译请求过大或格式错误')
    return texts,obj['target']

def translate(text,target):
    endpoint=os.environ.get('LIBRETRANSLATE_URL','').strip()
    key=(endpoint,target,text)
    with LOCK:
        if key in CACHE:
            CACHE.move_to_end(key);return CACHE[key]
    source='zh-CN' if any('\u3400'<=c<='\u9fff' for c in text) else 'en'
    if source==target:return text
    results=[]
    with SLOTS:
        for part in chunks(text):
            if endpoint:
                url=endpoint.rstrip('/')+'/translate'
                if urllib.parse.urlsplit(url).scheme not in ('http','https'):raise ValueError('翻译服务配置错误')
                req=urllib.request.Request(url,data=json.dumps({'q':part,'source':'zh' if source=='zh-CN' else 'en','target':'zh' if target=='zh-CN' else 'en','format':'text'}).encode(),headers={'Content-Type':'application/json'})
            else:
                url='https://api.mymemory.translated.net/get?'+urllib.parse.urlencode({'q':part,'langpair':source+'|'+target})
                req=urllib.request.Request(url,headers={'User-Agent':'DailyAggregator/1.0'})
            with (urllib.request.urlopen(req,timeout=12) if endpoint else public_http.opener().open(req,timeout=12)) as r:
                raw=r.read(262145)
                if len(raw)>262144:raise ValueError('翻译响应过大')
                data=json.loads(raw)
            if endpoint:value=data.get('translatedText')
            else:
                if data.get('quotaFinished') or str(data.get('responseStatus'))!='200':raise ValueError('免费翻译额度用尽或来源暂不可用')
                value=(data.get('responseData') or {}).get('translatedText')
            if not isinstance(value,str) or not value.strip():raise ValueError('翻译来源没有返回文本')
            results.append(html.unescape(value))
    value=''.join(results)
    with LOCK:
        CACHE[key]=value
        while len(CACHE)>1500:CACHE.popitem(last=False)
    return value

def batch(obj):
    texts,target=validate(obj)
    def one(t):
        try:return {'text':translate(t,target)}
        except Exception:return {'text':t,'error':'翻译暂不可用或免费额度已用尽，保留原文'}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:rows=list(pool.map(one,texts))
    return {'results':rows,'provider':'LibreTranslate' if os.environ.get('LIBRETRANSLATE_URL') else 'MyMemory'}
