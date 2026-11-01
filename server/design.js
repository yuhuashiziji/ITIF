(function(){
'use strict';
var data=window.__BOOTSTRAP__||{feeds:[],markets:{}},statusExpanded=false;
var heading=document.createElement('header');heading.className='desk-heading';heading.innerHTML='<div><h1>今日信息总览</h1><p id="deskScope">中文优先，重要信息直达原文。</p></div><div class="desk-date"><strong>'+new Intl.DateTimeFormat('zh-CN',{timeZone:'Asia/Shanghai',month:'2-digit',day:'2-digit'}).format(new Date())+'</strong>'+new Intl.DateTimeFormat('zh-CN',{timeZone:'Asia/Shanghai',weekday:'long'}).format(new Date())+'</div>';
var wrap=document.querySelector('#view-home .wrap');wrap.insertBefore(heading,wrap.firstChild);
var logo=document.querySelector('.brand svg');if(logo)logo.outerHTML='<svg viewBox="0 0 32 32" fill="none" aria-hidden="true"><path d="M5 5h15v20H5zM12 9h15v20H12" stroke="currentColor" stroke-width="1.8"/><path d="M9 10h7M9 14h7M16 19h7M16 23h7" stroke="currentColor" stroke-width="1.8"/><path d="M5 5h15" stroke="var(--brand)" stroke-width="3"/></svg>';
var search=document.querySelector('.search'),top=document.querySelector('.topbar-in');
// One input, moved rather than cloned so search state and listeners survive.
function placeSearch(){if(matchMedia('(max-width:600px)').matches){top.appendChild(search);search.classList.add('mobile-search');}else{document.querySelector('.top-right').insertBefore(search,document.querySelector('.top-right').firstChild);search.classList.remove('mobile-search');}}
placeSearch();window.addEventListener('resize',placeSearch);
// Own this slot across polling and route redraws; the old tag cloud is demo content.
renderTags=function(){var tags=$('tags');if(!tags)return;var card=tags.closest('.side-card');card.querySelector('h3').textContent='阅读说明';tags.className='desk-reading-note';tags.innerHTML='<p>保留原文语言，点击标题阅读。<br>收藏与已读记录保存在本机。</p><p>标记为“历史快照”的内容不代表今日热榜，也不会进入每日精选。</p>';};renderTags();
var sideTitle=document.querySelector('.side-card h3');if(sideTitle)sideTitle.textContent='来源速览';
var side=document.querySelector('.side');if(side){var first=side.querySelector('.side-card');var button=document.createElement('button');button.className='source-status-toggle';button.textContent='展开全部推荐';button.addEventListener('click',function(){first.classList.toggle('is-expanded');button.textContent=first.classList.contains('is-expanded')?'收起推荐':'展开全部推荐';});first.appendChild(button);
var status=$('liveSourceStatus');if(status){var toggle=document.createElement('button');toggle.className='source-status-toggle';toggle.textContent='查看全部来源状态';toggle.addEventListener('click',function(){statusExpanded=!statusExpanded;status.classList.toggle('is-expanded',statusExpanded);toggle.textContent=statusExpanded?'收起来源状态':'查看全部来源状态';});status.parentElement.appendChild(toggle);}}
function scope(){var feeds=data.feeds||[],zh=feeds.filter(function(f){return f.language==='zh';}).length;var el=$('deskScope');if(el)el.textContent=feeds.length+' 个来源 · '+zh+' 个中文来源 · 保留原文，按需翻译';}
scope();document.addEventListener('desk:data',function(e){data=e.detail;scope();});
// Replace obsolete demo hot stories with the same real source records as the homepage.
WIDGETS.forEach(function(w){if(w.id==='hot'){w.hint='国内来源';w.render=function(){return ['微博','今日头条'].map(function(name){var f=(data.feeds||[]).find(function(f){return f.name===name;});return '<div class="hot-sec"><div class="lab">'+name+'</div>'+(f?(f.items||[]).slice(0,3).map(function(r){return '<div class="row">'+tt([r.title,'','',r.url])+'</div>';}).join(''):'<p class="code">等待来源更新</p>')+'</div>';}).join('');};}if(w.id==='cal')w.hint='演示日历';if(w.id==='gh')w.hint='演示项目';});
if(state.route==='workbench')renderBoard();
})();
