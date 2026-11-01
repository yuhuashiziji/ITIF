(function(){
'use strict';
var data=null,view='boards',busy=false,archive=null;
var names={tech:'科技',finance:'财经',dev:'开发',ai:'AI',news:'新闻',ent:'娱乐',shopping:'购物'};
var nav=document.createElement('nav');nav.className='editor-nav';nav.setAttribute('aria-label','阅读视图');
nav.innerHTML=[['boards','来源榜单'],['daily','每日精选'],['events','事件聚合'],['weekly','每周精选'],['sources','来源管理']].map(function(x){return '<button class="tag" data-ed-view="'+x[0]+'">'+x[1]+'</button>';}).join('');
var panel=document.createElement('section');panel.id='editorPanel';panel.className='editor-panel';panel.hidden=true;
var wrap=document.querySelector('#view-home .wrap');wrap.insertBefore(nav,wrap.firstChild);nav.insertAdjacentElement('afterend',panel);
function stamp(t){return t?new Date(t).toLocaleString():'尚未检查';}
function article(a){return '<article class="editor-item"'+(a.private?' translate="no" data-private="true"':'')+'><div class="code">'+esc(names[a.category]||a.category||'')+' · '+esc(a.source||a.language||'')+'</div><h3>'+tt([a.title,'','',a.url])+'</h3>'+(a.reason?'<p class="editor-reason">'+esc(a.reason)+'</p>':'')+(a.summary?'<p>'+esc(a.summary)+'</p>':'')+'</article>';}
function selected(v,x){return v===x?' selected':'';}
function options(values,value){return values.map(function(v){return '<option value="'+esc(v)+'"'+selected(v,value)+'>'+esc(names[v]||v)+'</option>';}).join('');}
function draw(){
  nav.querySelectorAll('[data-ed-view]').forEach(function(b){b.classList.toggle('on',b.dataset.edView===view);});
  var home=document.querySelector('#view-home .home-main');home.hidden=view!=='boards';$('quickRow').hidden=view!=='boards';panel.hidden=view==='boards';if(view==='boards')return;
  if(!data){panel.innerHTML='<p>正在加载…</p>';return;}
  var h='';
  if(view==='daily'){
    var daily=archive||data.daily;
    h='<h2>'+esc(daily.date)+' 每日精选</h2><p>规则筛选 · 关注词加权 · 分类配额 · 每源限额。候选不足时不会使用旧新闻凑数。</p><label>历史归档 <select id="editionDate"><option value="">今天</option>'+data.archives.map(function(d){return '<option'+selected(d,archive&&archive.date)+'>'+esc(d)+'</option>';}).join('')+'</select></label>';
    h+=(daily.items||[]).map(article).join('')||'<p>所选时间范围内没有符合条件的文章，可在下方调整规则。</p>';
    var s=data.settings;
    h+='<details class="editor-settings"><summary>精选规则与关键词</summary><form id="editorSettings"><label>关注词（逗号分隔，提高排序）<input name="include" value="'+esc(s.include.join(', '))+'"></label><label>屏蔽词（不进入精选和事件）<input name="exclude" value="'+esc(s.exclude.join(', '))+'"></label><label>每日上限<input name="max_items" type="number" min="1" max="100" value="'+s.max_items+'"></label><label>每来源上限<input name="per_source" type="number" min="1" max="10" value="'+s.per_source+'"></label><label>候选时间范围（小时）<input name="hours" type="number" min="1" max="168" value="'+s.hours+'"></label><fieldset><legend>类别最多条数</legend>'+Object.keys(names).map(function(c){return '<label>'+names[c]+'<input name="quota-'+c+'" type="number" min="0" max="100" value="'+(s.quotas[c]||0)+'"></label>';}).join('')+'</fieldset><button class="tag" type="submit">保存规则</button></form></details>';
  }
  if(view==='events'){
    h='<h2>事件聚合</h2><p>按标题相似度、类别与时间窗口分组。不是事实核查，不合并中英文语义；保留所有原文入口。</p>';
    h+=data.events.slice(0,100).map(function(e){return '<details class="editor-item"'+(e.articles.some(function(a){return a.private;})?' translate="no" data-private="true"':'')+(e.source_count>1?' open':'')+'><summary>'+esc(e.title)+' <span class="code">'+e.source_count+' 个来源 · '+esc(names[e.category]||e.category)+'</span></summary>'+e.articles.map(article).join('')+'</details>';}).join('')||'<p>暂无符合时间范围的事件。</p>';
  }
  if(view==='weekly'){
    h='<h2>每周精选</h2><p>编辑精选的推荐内容，保留原文语言与推荐理由。</p>';
    h+=data.weekly.length?data.weekly.map(function(w){return '<section><h3>'+esc(w.title)+'</h3>'+w.items.map(article).join('')+'</section>';}).join(''):'<p>尚未发布编辑精选。维护者可按项目中的 content/weekly/TEMPLATE.md 编写推荐并审核发布。</p>';
    h+='<details class="editor-item"><summary>如何投稿</summary><p>在项目 GitHub 仓库选择“New issue → 推荐文章或工具”，提交标题、原文地址、语言与推荐理由。维护者审核后通过 Markdown 文件发布。当前尚未配置公开仓库地址，请通过仓库页面投稿。</p></details>';
  }
  if(view==='sources'){
    h='<h2>来源管理</h2><p>配置仅保存到本机。更改刷新间隔后，下一次任务完成时应用；禁用来源将停止后续调度。</p>';
    h+=data.sources.map(function(s){return '<form class="editor-item source-form" data-source-id="'+esc(s.id)+'"><h3>'+esc(s.name)+'</h3><p class="code">'+esc(s.url)+'</p><p>'+esc(s.error?'更新失败：'+s.error:s.items?'正常 · '+s.items+' 篇':'等待抓取')+'<br>检查：'+esc(stamp(s.checked_at))+' · 下次：'+esc(stamp(s.next_check_at))+'</p><div class="source-fields"><label>启用<input name="enabled" type="checkbox"'+(s.enabled?' checked':'')+'></label><label>语言<select name="language">'+options(['zh','en','other'],s.language)+'</select></label><label>分类<select name="category">'+options(Object.keys(names),s.category)+'</select></label><label>权重<input name="weight" type="number" min="0" max="200" value="'+s.weight+'"></label><label>刷新秒数<input name="interval" type="number" min="300" max="604800" value="'+s.interval+'"></label></div><p class="code">'+esc(s.attribution)+'</p><button type="submit" class="tag">保存来源</button></form>';}).join('');
  }
  panel.innerHTML=h;
}
async function refresh(){if(busy)return;busy=true;try{var r=await fetch('/api/editorial');if(!r.ok)throw Error('无法读取精选数据');data=await r.json();if(!panel.querySelector('input:focus,select:focus'))draw();}catch(e){toast(e.message);}finally{busy=false;}}
nav.addEventListener('click',function(e){var b=e.target.closest('[data-ed-view]');if(!b)return;view=b.dataset.edView;draw();refresh();});
panel.addEventListener('change',async function(e){if(e.target.id!=='editionDate')return;if(!e.target.value){archive=null;draw();return;}try{var r=await fetch('/api/edition?date='+encodeURIComponent(e.target.value));if(!r.ok)throw Error('归档不可用');archive=await r.json();draw();}catch(e){toast(e.message);}});
panel.addEventListener('submit',async function(e){e.preventDefault();var f=e.target,obj={},url;if(f.id==='editorSettings'){var split=function(v){return v.split(/[,，\n]/).map(function(v){return v.trim();}).filter(Boolean);};obj={include:split(f.elements.include.value),exclude:split(f.elements.exclude.value),max_items:Number(f.elements.max_items.value),per_source:Number(f.elements.per_source.value),hours:Number(f.elements.hours.value),quotas:{}};Object.keys(names).forEach(function(c){obj.quotas[c]=Number(f.elements['quota-'+c].value);});url='/api/settings';}else if(f.classList.contains('source-form')){obj={id:f.dataset.sourceId,enabled:f.elements.enabled.checked,language:f.elements.language.value,category:f.elements.category.value,weight:Number(f.elements.weight.value),interval:Number(f.elements.interval.value)};url='/api/source';}else return;var button=f.querySelector('button[type="submit"]');button.disabled=true;try{var r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(obj)});var result=await r.json();if(!r.ok)throw Error(result.error);archive=null;toast('配置已保存');await refresh();}catch(e){toast(e.message);}finally{button.disabled=false;}});
draw();refresh();setInterval(function(){if(view!=='boards')refresh();},60000);
})();
