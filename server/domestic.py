"""Domestic public hot-list adapters. Independent implementation, no cookies."""
import datetime,json,urllib.parse
PRIORITY=['微信','微博','今日头条','搜狗','历史上的今天','知乎']
def normalize(rows,domains=()):
    out=[];seen=set()
    for row in rows:
        title=str(row.get('title','')).strip();url=row.get('url') or row.get('link') or '';host=urllib.parse.urlsplit(url).hostname or ''
        if not title or urllib.parse.urlsplit(url).scheme not in ('http','https') or url in seen:continue
        if domains and not any(host==d or host.endswith('.'+d) for d in domains):continue
        seen.add(url);out.append({'title':title,'url':url,'heat':str(row.get('heat') or row.get('hot_value_desc') or row.get('hot_value') or ''),'published':row.get('published',''),'summary':str(row.get('summary',''))[:500]})
    if not out:raise ValueError('来源未返回有效原文链接')
    return out[:40]
def fetch(source,request):
    kind=source['adapter'];body=json.loads(request(source['url']))
    if kind=='toutiao':rows=[{'title':a['Title'],'url':a.get('Url') or 'https://www.toutiao.com/trending/'+str(a.get('ClusterIdStr') or a['ClusterId'])+'/','heat':a.get('HotValue','')} for a in body.get('data',[])]
    elif kind=='zhihu':rows=[{'title':a['target']['title_area']['text'],'url':a['target']['link']['url'],'heat':a['target'].get('metrics_area',{}).get('text','')} for a in body.get('data',[])]
    elif kind=='sixty':
        if body.get('code')!=200:raise ValueError(str(body.get('message','接口暂不可用')))
        rows=body['data'];rows=rows.get('items',[]) if isinstance(rows,dict) else rows
    else:raise ValueError('未知热榜适配器')
    return normalize(rows,source.get('domains',[]))
def board_nodes(feeds):
    nodes=[]
    for f in feeds:
        hot=f.get('kind')=='hot';name=f['name'];status='历史快照' if f.get('snapshot') else '缓存 · 更新失败' if f.get('error') else '热榜' if hot else '网页精选' if f.get('kind')=='web' else 'RSS'
        nodes.append({'id':('hot-' if hot else 'rss-')+f.get('source_id',str(len(nodes))),'name':name,'cat':f.get('category','news'),'language':f.get('language','zh' if hot else 'en'),'weight':f.get('weight',80),'board':status+' · '+('时间未知' if f.get('snapshot') else f.get('fetched_at') or '等待抓取'),'all':True,'private':bool(f.get('private')),'snapshot':f.get('snapshot',False),'error':f.get('error',''),'priority':PRIORITY.index(name) if name in PRIORITY else 99,'color':'#dc2626' if hot else '#1e40af','items':[[r['title'],r.get('heat',''),'',r['url']] for r in f.get('items',[]) if r.get('url','').startswith(('http://','https://'))]})
    return nodes
