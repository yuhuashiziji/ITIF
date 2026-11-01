(function(){
document.addEventListener('click',function(e){if(e.target.closest('[data-addsub]')){e.preventDefault();e.stopImmediatePropagation();toast('公开来源由仓库维护者管理；收藏和已读记录保存在当前浏览器。');}},true);
var original=renderSubs;renderSubs=function(){original();document.querySelectorAll('[data-addsub]').forEach(function(b){b.remove();});};
function delivery(data){var d=data.delivery;if(!d)return;var status=document.getElementById('publicDataStatus');if(!status){status=document.createElement('p');status.id='publicDataStatus';status.className='code';status.setAttribute('role','status');var heading=document.querySelector('#view-home .wrap');heading.insertBefore(status,heading.firstChild);}
status.textContent='公开浏览版 · 数据快照 '+new Date(d.generated_at).toLocaleString()+(d.stale?' · 数据已超过两小时，等待更新':'')+(d.error?' · '+d.error:'')+' · 收藏仅保存在本机';}
document.addEventListener('desk:data',function(e){delivery(e.detail);});delivery(window.__BOOTSTRAP__||{});
})();
