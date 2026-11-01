"""Explainable source catalog, digest, event grouping, Markdown editions."""
import datetime as dt, hashlib, json, re, threading
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from email.utils import parsedate_to_datetime
ZONE=dt.timezone(dt.timedelta(hours=8))
DEFAULT={'include':[],'exclude':[],'max_items':20,'per_source':2,'hours':48,'quotas':{'tech':5,'finance':5,'dev':5,'ai':3,'news':2}}
def read(p,default):
    try:return json.loads(p.read_text(encoding='utf-8'))
    except (OSError,ValueError):return default
def atomic(p,data):
    p.parent.mkdir(parents=True,exist_ok=True);temp=p.with_suffix('.tmp');temp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(p)
def canonical(url):
    p=urlsplit(url);q=[(k,v) for k,v in parse_qsl(p.query,keep_blank_values=True) if not k.lower().startswith('utm_') and k.lower() not in ('fbclid','gclid')]
    return urlunsplit((p.scheme.lower(),p.netloc.lower(),p.path or '/',urlencode(q),''))
def timestamp(value):
    try:
        try:d=dt.datetime.fromisoformat(value.replace('Z','+00:00'))
        except ValueError:d=parsedate_to_datetime(value)
        return (d.replace(tzinfo=dt.timezone.utc) if d.tzinfo is None else d).timestamp()
    except (ValueError,TypeError,AttributeError,OverflowError):return None
def tokens(title):
    title=title.lower();words=set(re.findall(r'[a-z0-9]{2,}',title))
    for part in re.findall(r'[\u3400-\u9fff]+',title):words.update(part[i:i+2] for i in range(len(part)-1))
    return words-{'the','and','for','with','from','this','that','your','how','what'}
def events(articles):
    groups=[]
    for a in articles[:600]:
        t=tokens(a['title']);target=None
        for g in groups:
            first=g['articles'][0]
            if a['category']!=first['category'] or abs(a['time']-first['time'])>172800:continue
            same=a['canonical']==first['canonical']
            nums=re.findall(r'\d+(?:\.\d+)?',a['title']);other=re.findall(r'\d+(?:\.\d+)?',first['title'])
            similarity=len(t&g['_tokens'])/max(1,len(t|g['_tokens']))
            if same or (len(t)>=4 and len(g['_tokens'])>=4 and similarity>=.72 and set(nums)==set(other)):
                target=g;break
        if target is None:
            target={'id':a['id'],'title':a['title'],'category':a['category'],'articles':[],'_tokens':t};groups.append(target)
        if not any(x['canonical']==a['canonical'] and x['source_id']==a['source_id'] for x in target['articles']):target['articles'].append(a)
    for g in groups:
        del g['_tokens'];g['source_count']=len({urlsplit(a['url']).hostname for a in g['articles']});g['last_updated']=max(a['time'] for a in g['articles'])
    return sorted(groups,key=lambda g:(g['source_count'],g['last_updated']),reverse=True)
class Editorial:
    def __init__(self,base):self.base=Path(base);self.lock=threading.RLock()
    def sources(self,config):
        sources=read(self.base/'server/sources.json',[]);by={x['url']:dict(x) for x in sources};overrides=config.get('source_overrides',{})
        for x in config.get('feeds',[]):
            if x['url'] not in by:by[x['url']]={**x,'id':hashlib.sha256(x['url'].encode()).hexdigest()[:12],'language':'zh' if re.search(r'[\u3400-\u9fff]',x['name']) else 'en','category':x.get('category','news'),'weight':80,'interval':900,'enabled':True,'kind':'rss','private':True,'attribution':'用户添加，需核实使用条款'}
        return [{**x,**overrides.get(x['id'],{})} for x in by.values()]
    def settings(self):return {**DEFAULT,**read(self.base/'server/data/editorial-settings.json',{})}
    def articles(self,feeds,sources,settings,clock=None):
        clock=clock or dt.datetime.now().timestamp();by={s['url']:s for s in sources if s.get('enabled',True) and not s.get('snapshot')};out=[];seen=set()
        for f in feeds:
            s=by.get(f['url'])
            if not s:continue
            for row in f.get('items',[]):
                url=row.get('url','')
                if urlsplit(url).scheme not in ('http','https'):continue
                key=canonical(url)
                if (s['id'],key) in seen:continue
                seen.add((s['id'],key));published=timestamp(row.get('published',''));observed=timestamp(f.get('fetched_at',''));stamp=published if published is not None else observed
                if stamp is None or stamp>clock+3600:continue
                age=max(0,(clock-stamp)/3600);title=row.get('title','');lower=title.lower()
                if any(k.lower() in lower for k in settings['exclude']):continue
                match=[k for k in settings['include'] if k.lower() in lower];score=s.get('weight',80)+(200 if s['language']=='zh' else 0)+(20 if match else 0)+max(0,24-age)-(30 if f.get('error') else 0)
                out.append({'id':hashlib.sha256(key.encode()).hexdigest()[:20],'canonical':key,'title':title,'url':url,'source':s['name'],'source_id':s['id'],'private':bool(s.get('private')),'category':s['category'],'language':s['language'],'time':stamp,'published':row.get('published',''),'time_basis':'published' if published is not None else 'fetched','age_hours':round(age,1),'score':round(score,1),'summary':row.get('summary',''),'reason':('关注词：'+', '.join(match)+'；' if match else '')+('中文来源；' if s['language']=='zh' else '国际来源；')+('抓取时间，发布时间未知' if published is None else '按发布时间筛选')})
        return sorted(out,key=lambda a:(a['score'],a['time']),reverse=True)
    def select(self,articles,settings):
        selected=[];cats=Counter();sources=Counter();seen=set()
        for a in articles:
            if a['age_hours']>settings['hours'] or a['canonical'] in seen:continue
            if cats[a['category']]>=settings['quotas'].get(a['category'],0) or sources[a['source_id']]>=settings['per_source']:continue
            selected.append(a);seen.add(a['canonical']);cats[a['category']]+=1;sources[a['source_id']]+=1
            if len(selected)>=settings['max_items']:break
        return selected
    def build(self,feeds,config):
        with self.lock:
            settings=self.settings();sources=self.sources(config);articles=self.articles(feeds,sources,settings);today=dt.datetime.now(ZONE).date().isoformat()
            daily={'date':today,'generated_at':dt.datetime.now(ZONE).isoformat(),'items':self.select(articles,settings),'selection':'规则精选，非人工审核或 AI 摘要'}
            if daily['items']:atomic(self.base/'server/data/editions'/f'{today}.json',daily)
            health=[]
            for s in sources:
                f=next((f for f in feeds if f['url']==s['url']),{});health.append({**s,'error':f.get('error',''),'checked_at':f.get('checked_at'),'fetched_at':f.get('fetched_at'),'items':len(f.get('items',[])),'failures':f.get('failures',0),'next_check_at':f.get('next_check_at')})
            recent=[a for a in articles if a['age_hours']<=settings['hours']]
            return {'settings':settings,'sources':health,'daily':daily,'events':events(recent),'weekly':self.weekly(),'archives':[p.stem for p in sorted((self.base/'server/data/editions').glob('*.json'),reverse=True)]}
    def weekly(self):
        editions=[]
        for p in sorted((self.base/'content/weekly').glob('*.md'),reverse=True):
            text=p.read_text(encoding='utf-8');items=[]
            for block in text.split('\n## ')[1:]:
                lines=block.splitlines();fields={}
                for line in lines[1:]:
                    if ': ' in line:k,v=line.split(': ',1);fields[k.strip()]=v.strip()
                if fields.get('status')=='published' and urlsplit(fields.get('url','')).scheme in ('http','https') and fields.get('reason'):
                    items.append({'title':lines[0].strip(),'url':fields['url'],'reason':fields['reason'],'category':fields.get('category','dev'),'language':fields.get('language','en')})
            if items:editions.append({'id':p.stem,'title':text.splitlines()[0].lstrip('# '),'items':items})
        return editions
