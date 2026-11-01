"""Build a minimal shared-host webroot, excluding all local state and Python sources."""
import argparse,hashlib,json,re,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
GUARD='<?php exit; ?>\n'
def asset(text):
    for route in ('status','editorial','translate','feeds','source','settings','refresh'):
        text=text.replace('/api/'+route,'api.php?action='+route)
    return text.replace('/api/edition?date=','api.php?action=edition&date=').replace('/rss.xml','api.php?action=rss')
def build(output):
    snapshot=json.loads((ROOT/'public-data/snapshot.json').read_text(encoding='utf-8'))
    if any(f.get('private') for f in snapshot['status']['feeds']):raise ValueError('Private source in public seed')
    files={p.name:p.read_text(encoding='utf-8') for p in (ROOT/'hosting/php').glob('*.php') if p.name!='config.php'}
    files['seed.php']=GUARD+json.dumps(snapshot,ensure_ascii=False,separators=(',',':'))
    html=(ROOT/'每日聚合站_融合版.html').read_text(encoding='utf-8')
    html=asset(html)
    html=re.sub(r'(src|href)="/(?!/)',r'\1="',html)
    html=html.replace('<script src="live.js">','<script src="public.js"></script>\n<script src="live.js">')
    files['template.php']=GUARD+asset(html)
    for p in (ROOT/'server').glob('*.js'):
        text=p.read_text(encoding='utf-8')
        if p.name=='live.js':
            text=text.replace("fetch('/api/refresh',{method:'POST'})","fetch('/api/status')").replace("toast('后台正在刷新订阅')","toast('已读取最新公开快照；来源抓取由定时任务执行')").replace("立即刷新 RSS","读取最新快照")
        if p.name=='editorial.js':
            text=text.replace("h+='<details class=\"editor-settings\"", "if(!window.ITIF_PUBLIC)h+='<details class=\"editor-settings\"")
            begin=text.index("    h='<h2>来源管理")
            end=text.index('\n  }',begin)
            old=text[begin:end]
            text=text[:begin]+"    if(window.ITIF_PUBLIC){h='<h2>来源状态</h2><p>公开来源由仓库维护者管理。刷新间隔受定时任务运行时间约束。</p>'+data.sources.map(function(s){return '<article class=\"editor-item\"><h3>'+esc(s.name)+'</h3><p>'+esc(s.error||('已收录 '+s.items+' 篇'))+'</p><p class=\"code\">最近检查 '+esc(stamp(s.checked_at))+'</p><p class=\"code\">'+esc(s.attribution||'')+'</p></article>';}).join('');}else{\n"+old+'\n    }'+text[end:]
            text=text.replace('来源管理','来源状态').replace('可在下方调整规则','等待下次来源更新')
        files[p.name]=asset(text)
    for p in (ROOT/'server').glob('*.css'):files[p.name]=p.read_text(encoding='utf-8')
    files['public.js']=(ROOT/'hosting/php/public.js').read_text(encoding='utf-8')
    files['LICENSE']=(ROOT/'LICENSE').read_text(encoding='utf-8')
    output.mkdir(parents=True,exist_ok=True)
    archive=output/'itif-php85.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for name,text in sorted(files.items()):z.writestr(name,text)
    (output/'itif-php85.sha256').write_text(hashlib.sha256(archive.read_bytes()).hexdigest()+'  '+archive.name+'\n',encoding='utf-8')
    print('PHP webroot:',len(files),'files,',archive.stat().st_size,'bytes')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=ROOT/'dist');a=p.parse_args();build(a.output)
