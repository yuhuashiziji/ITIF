/* Reading features independently implemented; references in README. */
(function(){
function load(key){try{var v=JSON.parse(localStorage.getItem(key)||'{}');return v&&typeof v==='object'&&!Array.isArray(v)?v:{};}catch(e){return {};}}
var stars=load('reader-stars'),reads=load('reader-reads'),pins=load('reader-pins'),mode='all';
function persist(key,obj){try{localStorage.setItem(key,JSON.stringify(obj));}catch(e){toast('浏览器存储不可用，修改仅在当前页面生效');}}
function chinese(n){return n.language==='zh'||(!n.language&&/[\u3400-\u9fff]/.test(n.name));}
var featured=['Cloudflare Blog','Rust Blog','MIT News AI','Federal Reserve','Stack Overflow Blog'];
function score(n){return (pins[n.name]?2000:0)+(n.priority<6?1000-n.priority*50:0)+(Number.isFinite(n.weight)?n.weight:chinese(n)?120:featured.indexOf(n.name)>=0?110:80)+(chinese(n)?200:0)+(n.id.indexOf('rss-')===0?20:-300);}
window.readerScore=score;
var originalVisible=visibleNodes;
visibleNodes=function(){var seen=new Set();return originalVisible().slice().sort(function(a,b){return score(b)-score(a)||a.name.localeCompare(b.name);}).map(function(n){var c=Object.assign({},n);c.items=n.items.filter(function(row){var url=row[3];if(!url||seen.has(url))return false;seen.add(url);return mode==='saved'?!!stars[url]:mode==='unread'?!reads[url]:true;});return c;}).filter(function(n){return n.items.length||(!state.q&&mode==='all'&&n.id.indexOf('hot-')===0);});};
var originalTT=tt;
tt=function(row){var url=row[3],h=originalTT(row);if(!/^https?:\/\//i.test(url||''))return h;
var saved=!!stars[url];return '<span class="reader-entry'+(reads[url]?' reader-read':'')+'">'+h+'<span class="reader-actions"><button class="reader-star" data-star="'+esc(url)+'" data-title="'+esc(row[2]||row[0])+'" aria-pressed="'+saved+'" aria-label="'+(saved?'取消收藏：':'收藏：')+esc(row[2]||row[0])+'" title="'+(saved?'取消收藏':'收藏文章')+'">'+(saved?'★':'☆')+'</button></span></span>';};
var toolbar=document.createElement('div');toolbar.className='reader-toolbar';toolbar.innerHTML='<div><button class="tag on" data-reader="all">全部</button> <button class="tag" data-reader="unread">未读</button> <button class="tag" data-reader="saved">收藏</button></div><span class="reader-hint">中文优先 · 精选国际来源 · 点击来源置顶</span>';
$('tabs').insertAdjacentElement('afterend',toolbar);
function redraw(){renderGrid();if(state.route==='subs')renderSubs();if(state.route==='workbench')renderBoard();}
var gridOriginal=renderGrid;renderGrid=function(){gridOriginal();document.querySelectorAll('#grid .card').forEach(function(card){var n=NODES.find(function(x){return x.id===card.dataset.node;});if(!n)return;var head=card.querySelector('.card-head');var button=document.createElement('button');button.className='tag reader-pin';button.dataset.pin=n.name;button.textContent=pins[n.name]?'取消置顶':'置顶';button.setAttribute('aria-pressed',String(!!pins[n.name]));head.appendChild(button);});};
document.addEventListener('click',function(e){var button=e.target.closest('[data-reader]');if(button){mode=button.dataset.reader;toolbar.querySelectorAll('[data-reader]').forEach(function(b){b.classList.toggle('on',b===button);});renderGrid();return;}
button=e.target.closest('[data-star]');if(button){var url=button.dataset.star;if(stars[url])delete stars[url];else stars[url]={title:button.dataset.title,url:url};persist('reader-stars',stars);redraw();return;}
button=e.target.closest('[data-pin]');if(button){var name=button.dataset.pin;if(pins[name])delete pins[name];else pins[name]=true;persist('reader-pins',pins);renderGrid();return;}
var link=e.target.closest('a.tt');if(link){reads[link.getAttribute('href')]=true;persist('reader-reads',reads);link.closest('.reader-entry')?.classList.add('reader-read');}
});
// Favorites remain accessible even after the source rotates an article out.
var baseVisible=visibleNodes;visibleNodes=function(){if(mode!=='saved')return baseVisible();var rows=Object.keys(stars).map(function(url){return [stars[url].title||url,'','',url];});return rows.length?[{id:'saved-reader',name:'我的收藏',board:'本浏览器保存',cat:state.cat,all:true,items:rows}]:[];};
var oldTop=renderTop10;renderTop10=function(){TOP10=visibleNodes().filter(function(n){return n.items.length;}).slice(0,10).map(function(n){return [n.items[0][0],n.name,n.items[0][3]];});oldTop();};
renderGrid();renderTop10();
})();
