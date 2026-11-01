'use strict';
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),html=fs.readFileSync(path.join(root,'每日聚合站_融合版.html'),'utf8');
const handler=html.slice(html.indexOf('  if((b=e.target.closest(".more-btn")))'),html.indexOf('  if((b=e.target.closest("[data-fold]")))'));
function expand(id,all,visible){const body={innerHTML:''},card={querySelector:()=>body},button={dataset:{node:id},closest:s=>s==='.card'?card:{remove(){}}};const ctx={NODES:all,visibleNodes:()=>visible,matchItem:()=>true,ICONS:{},tt:r=>r[0],esc:String,e:{target:{closest:()=>button}}};vm.runInNewContext('(function(){var b;'+handler+'})()',ctx);return body.innerHTML;}
const rows=Array.from({length:6},(_,i)=>['saved '+i,'','','https://example.test/'+i]);
assert.equal((expand('saved-reader',[],[{id:'saved-reader',name:'Saved',items:rows}]).match(/class="row"/g)||[]).length,6);
const full=[{id:'feed',name:'Feed',items:[['ALREADY_READ','','','https://a.test/1'],['UNREAD','','','https://a.test/2']]}];
const unread=[{...full[0],items:[full[0].items[1]]}];assert.ok(!expand('feed',full,unread).includes('ALREADY_READ'));assert.ok(expand('feed',full,unread).includes('UNREAD'));
assert.equal(expand('removed',[],[]),'');
const render=html.slice(html.indexOf('function renderGrid(){'),html.indexOf('function renderTop10(){'));
const output={innerHTML:''};const esc=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
const ctx={state:{q:''},visibleNodes:()=>[{id:'private',name:'<img src=x>',board:'<fixture>',private:true,items:[]}],matchItem:()=>true,ICONS:{},esc,$:()=>output,tt:()=>''};vm.runInNewContext(render+';renderGrid()',ctx);
assert.ok(output.innerHTML.includes('translate="no" data-private="true"'));assert.ok(!output.innerHTML.includes('<img src=x>'));assert.ok(output.innerHTML.includes('&lt;fixture&gt;'));
// Check the actual translation collector against public/private text-node fixtures.
const source=fs.readFileSync(path.join(root,'server/translate.js'),'utf8');const collector=source.slice(source.indexOf('function collect(){'),source.indexOf('async function run(){'));
const fixtures=[{text:'Public English headline',rule:null},{text:'Private custom headline',rule:'[data-private="true"]'},{text:'Private keyword reason',rule:'.editor-reason'},{text:'Private saved headline',rule:'[data-node="saved-reader"]'},{text:'Private subscription name',rule:'.rss-source>summary'}];
const nodes=fixtures.map(x=>({nodeValue:x.text,isConnected:true,parentElement:{closest:s=>x.rule&&s.includes(x.rule)?{}:null}}));
const c={records:new Map(),cache:new Map(),attempted:new Set(),dictionary:{},target:'zh-CN',visible:()=>true,record:n=>({original:n.nodeValue,last:n.nodeValue}),apply(){},NodeFilter:{SHOW_TEXT:4},document:{querySelectorAll:()=>[{}],createTreeWalker:()=>{let i=0;return {nextNode:()=>nodes[i++]||null};}}};vm.runInNewContext(collector+';result=collect()',c);assert.equal(c.result.length,1);assert.equal(c.result[0].text,'Public English headline');
console.log('Frontend audit: saved expansion, unread filter, stale source, escaping/private markup, and translation privacy fixtures passed.');
