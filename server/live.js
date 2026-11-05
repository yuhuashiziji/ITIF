(function(){
if(location.protocol==='file:')return;
var latest=window.__BOOTSTRAP__||{markets:{},feeds:[]};
function timeLabel(t){if(typeof t==='string'&&/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}/.test(t))return t;if(!t)return '暂无数据';return typeof t==='number'?new Date(t*1000).toLocaleString():(/^\d{14}$/.test(t)?t:new Date(t).toLocaleString());}
function marketHtml(id){var m=latest.markets[id];if(!m)return '<div class="empty">正在获取行情…</div>';var h='<div class="code">'+esc(m.source||'免费行情来源')+' · 获取时间 '+esc(timeLabel(m.fetched_at))+'</div>';
if(m.rows&&m.rows[0]&&m.rows[0].basis)h+='<div class="code">'+esc(m.rows[0].basis)+'</div>';
if(m.error)h+='<details class="code"><summary>部分行情更新失败 · 点击查看</summary>'+esc(m.error)+'</details>';
(m.rows||[]).forEach(function(r){h+='<div class="stock"><div><div class="nm">'+esc(({bitcoin:'比特币',ethereum:'以太坊',solana:'Solana',binancecoin:'BNB'})[r.name]||r.name)+'</div><div class="code">'+esc(r.symbol)+' · '+esc(r.currency)+' · '+esc(timeLabel(r.time))+'</div></div><div class="px">'+Number(r.price).toLocaleString(undefined,{maximumFractionDigits:4})+'</div><div class="chg '+(r.change==null||r.change===0?'':r.change>0?'up':'down')+'">'+(r.change==null?'—':(r.change>=0?'+':'')+Number(r.change).toFixed(2)+'%')+'</div></div>';});return h;}
function chineseFeed(f){return f.language==='zh'||(!f.language&&/[\u3400-\u9fff]/.test(f.name));}
function sortedFeeds(){return latest.feeds.slice().sort(function(a,b){return Number(chineseFeed(b))-Number(chineseFeed(a))||(b.weight||0)-(a.weight||0)||a.name.localeCompare(b.name);});}
function feedHtml(){return sortedFeeds().map(function(f){return '<details class="rss-source"'+(f.private?' translate="no" data-private="true"':'')+'><summary translate="no">'+esc(f.name)+' <span class="code">'+(f.items||[]).length+' 篇'+(f.error?' · 更新失败':'')+'</span></summary><p class="code">'+esc(f.error?'更新失败：'+f.error:'检查于 '+timeLabel(f.checked_at||f.fetched_at))+'</p>'+(f.items||[]).map(function(i){return '<div class="row">'+tt([i.title,'','',i.url])+'</div>';}).join('')+'</details>';}).join('')||'<div class="empty">首次订阅正在抓取</div>';}
function feedSummary(){var articles=latest.feeds.reduce(function(n,f){return n+(f.items||[]).length;},0),failed=latest.feeds.filter(function(f){return f.error;}).length;var h='<p class="code">'+latest.feeds.length+' 个来源 · '+articles+' 篇文章'+(failed?' · '+failed+' 个来源更新失败':'')+'</p>';var preview=[];sortedFeeds().forEach(function(f){if(f.items&&f.items[0]&&preview.length<3)preview.push(f.items[0]);});h+=preview.map(function(i){return '<div class="row">'+tt([i.title,'','',i.url])+'</div>';}).join('');return h+'<button class="tag" data-open-rss style="margin-top:12px">展开我的订阅 →</button>';}
var drawer=document.createElement('dialog');drawer.className='rss-drawer';drawer.setAttribute('aria-labelledby','rssDrawerTitle');drawer.innerHTML='<div class="rss-drawer-head"><div><h2 id="rssDrawerTitle">我的 RSS 订阅</h2><p class="code">中文优先 · 点击来源展开文章</p></div><button class="tag" data-close-rss aria-label="关闭订阅抽屉">关闭 ×</button></div><div class="rss-drawer-body"></div>';document.body.appendChild(drawer);
document.addEventListener('click',function(e){if(e.target.closest('[data-open-rss]')){drawer.querySelector('.rss-drawer-body').innerHTML=feedHtml();if(!drawer.open)drawer.showModal();}if(e.target.closest('[data-close-rss]'))drawer.close();});drawer.addEventListener('click',function(e){if(e.target===drawer){var r=drawer.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)drawer.close();}});

WIDGETS.forEach(function(w){if(['stock','us','crypto'].indexOf(w.id)>=0){w.hint='免费数据 · 定时更新';w.render=function(){return marketHtml(w.id);};}if(w.id==='sub'){w.hint='真实 RSS';w.render=feedSummary;}});
var refreshOld=$('refreshBtn'),refreshNew=refreshOld.cloneNode(true);refreshOld.replaceWith(refreshNew);
refreshNew.title='立即刷新 RSS';refreshNew.setAttribute('aria-label','立即刷新 RSS');refreshNew.addEventListener('click',async function(){if(refreshNew.disabled)return;refreshNew.disabled=true;refreshNew.setAttribute('aria-busy','true');refreshNew.setAttribute('aria-label','正在请求刷新');try{var r=await fetch('/api/refresh',{method:'POST'});if(!r.ok)throw Error('刷新请求失败');toast('后台正在刷新订阅');setTimeout(poll,3000);}catch(e){toast(e.message);}finally{refreshNew.disabled=false;refreshNew.removeAttribute('aria-busy');refreshNew.setAttribute('aria-label','立即刷新 RSS');}});
$('subUrl').placeholder='网站首页、RSS/Atom 或 rsshub://路由';
var originalSubs=renderSubs;renderSubs=function(){originalSubs();var h='<section class="card" translate="no"><div class="card-body"><h3>RSS 自动订阅与刷新</h3><p><a href="/rss.xml" target="_blank" rel="noopener">订阅本站聚合 RSS</a> · 按来源设置自动检查</p>'+feedSummary()+'</div></section>';$("subsGrid").insertAdjacentHTML('afterbegin',h);};
var oldButton=$('subOk'),button=oldButton.cloneNode(true);oldButton.replaceWith(button);button.addEventListener('click',async function(){var name=$('subName').value.trim(),url=$('subUrl').value.trim();button.disabled=true;try{var r=await fetch('/api/feeds',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:name,url:url})});var a=await r.json();if(!r.ok)throw Error(a.error);$('subDialog').classList.remove('show');$('subName').value='';$('subUrl').value='';toast('订阅已识别并保存，正在立即抓取');}catch(e){toast('添加失败：'+e.message);}finally{button.disabled=false;}});

var archivedNodes=window.__BOOTSTRAP__?[]:NODES.slice();
function applyFeeds(){
  var priority=['微信','微博','今日头条','搜狗','历史上的今天','知乎'];
  var live=latest.feeds.map(function(f,i){var hot=f.kind==='hot',label=f.snapshot?'历史快照 · 时间未知':f.error?'缓存 · 更新失败':hot?'平台热榜':f.kind==='web'?'网页精选 · 发现时间':'RSS';return {id:(hot?'hot-':'rss-')+(f.source_id||f.id||i),name:f.name,language:f.language,weight:f.weight,priority:priority.indexOf(f.name)<0?99:priority.indexOf(f.name),private:!!f.private,snapshot:!!f.snapshot,error:f.error||'',board:label+(f.snapshot?'':' · '+timeLabel(f.fetched_at)),cat:f.category||'news',all:true,color:hot?'#dc2626':'#1e40af',items:(f.items||[]).map(function(r){return [r.title,r.heat||'','',r.url];})};});
  NODES=live.concat(archivedNodes.map(function(n){var c=Object.assign({},n);c.board=n.board+' · 历史数据';c.items=n.items.filter(function(r){return /^https?:\/\//i.test(r[3]||'');}).map(function(r){return [r[2]||r[0],r[1],'',r[3]];});return c;}).filter(function(n){return n.items.length;}));
  TOP10=[];latest.feeds.forEach(function(f){if(f.items && f.items[0])TOP10.push([f.items[0].title,f.name,f.items[0].url]);});TOP10=TOP10.slice(0,10);
  if(state.route==='home')renderHome();
}

async function poll(){try{var r=await fetch('/api/status');if(!r.ok)throw Error('后台不可用');latest=await r.json();document.dispatchEvent(new CustomEvent('desk:data',{detail:latest}));
var badge=document.querySelector('.nav-item[data-view="subs"] .mini');if(badge)badge.textContent=latest.feeds.length;
var status=$('liveSourceStatus');if(status)status.innerHTML=sortedFeeds().map(function(f){return '<div class="src-item"><span class="dot '+(f.error?'warn':'ok')+'"></span><span class="sn">'+esc(f.name)+'</span><span class="st">'+(f.snapshot?'历史快照':f.error?'更新失败':f.items&&f.items.length?'已连接':'等待抓取')+'</span></div>';}).join('');
applyFeeds();if(state.route==='workbench')renderBoard();if(state.route==='subs')renderSubs();}catch(e){toast('后台连接失败，当前数据可能过期');}}
applyFeeds();
window.addEventListener('hashchange',function(){if(state.route==='home')renderHome();});
poll();setInterval(poll,30000);
})();
