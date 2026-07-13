const scrollKey='weilan-page-scroll',chatKey='weilan-chat-scroll',receiptKey='weilan-receipt-scroll';
const el=id=>document.querySelector(`#${id}`);
function saveScroll(){sessionStorage.setItem(scrollKey,String(window.scrollY));for(const [id,key] of [['messages',chatKey],['receipt-list',receiptKey]]){const node=el(id);if(node)sessionStorage.setItem(key,String(node.scrollTop))}}
function restoreScroll(){const saved=Number(sessionStorage.getItem(scrollKey));if(Number.isFinite(saved))scrollTo(0,saved);for(const [id,key] of [['messages',chatKey],['receipt-list',receiptKey]]){const node=el(id),top=Number(sessionStorage.getItem(key));if(node&&Number.isFinite(top))node.scrollTop=top}}
addEventListener('pagehide',saveScroll);addEventListener('beforeunload',saveScroll);
function details(refs=[]){const d=document.createElement('details'),s=document.createElement('summary'),p=document.createElement('pre');s.textContent='source refs';p.textContent=refs.join('\n')||'无 source ref';d.append(s,p);return d}
function card(title,text,refs=[],className='card'){const node=document.createElement('article');node.className=className;const h=document.createElement('strong'),p=document.createElement('p');h.textContent=title;p.textContent=text;node.append(h,p,details(refs));return node}
function renderList(id,items,build,empty){const root=el(id),top=root.scrollTop;root.replaceChildren(...(items.length?items.map(build):[card(empty,'',[],'empty')]));root.scrollTop=top}
function render(vm){
 el('activation').textContent=vm.authority.state;el('as-of').textContent=vm.as_of?`截至此次 recall 裁断：${vm.as_of}（不表示磁盘当前仍如此）`:'无法核验：此次 recall 缺少裁断时点';el('projection').textContent=vm.verifiable?(vm.projection.valid?(vm.projection.focus||'有效投影'):'已失效/脏'):'整页无法核验';el('sources').textContent=(vm.projection.source_refs||[]).join('\n');
 renderList('agenda-list',vm.agenda||[],x=>card(x.goal_ref||'未命名目标',`${x.description||''}\nnot-before: ${((x.condition||{}).not_before_utc)||'未设置'}`,x.source_refs), '当前没有登记中的任务线。');
 renderList('receipt-list',vm.recent_receipts||[],x=>card(`${x.outcome} · ${x.frame_id}`,x.verdict,x.source_refs,'card receipt'),'尚无已关闭的 continuation 收据帧。');
 renderList('messages',vm.chat||[],x=>{const who=x.from==='owner'?'张云':x.from==='claude'?'Claude':'Codex';const delivered=x.from==='owner'?(x.woke===true?' · 已送达并触发 wake':x.woke===false?' · 已送达':' · 已送达'):'';return card(`${who} · ${x.time||''}${delivered}`,x.text||'',x.source_refs,`card message ${x.from||''}`)},'茶水间还空着。');
 renderList('discussion-list',vm.discussion||[],x=>card(`${x.state} · ${x.proposal_time||''}`,`${x.proposal}\n\n裁断：${x.decision}`,x.source_refs,'card decision'),'当前没有已双签的结构化提案/裁断。');
 renderList('governance-list',vm.governance||[],x=>card(`${x.valid?'valid':'历史'} · ${x.state||''}`,x.summary||x.description||'治理条目',x.source_refs),'当前没有治理账本条目。');
}
addEventListener('DOMContentLoaded',async()=>{try{const c=await fetch('/api/config').then(r=>r.json());el('network-banner').textContent=c.banner}catch(e){}if('serviceWorker'in navigator)navigator.serviceWorker.register('/sw.js').catch(()=>{});await poll(true)});
async function poll(first=false){try{const vm=await fetch('/api/view-model',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error();return r.json()});render(vm);if(first)requestAnimationFrame(restoreScroll)}catch(e){}finally{setTimeout(poll,15000)}}
