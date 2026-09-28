'use strict';
const trip=JSON.parse(document.getElementById('trip-data').textContent);
const points=Object.fromEntries(trip.places.map(p=>[p[0],p]));
const escapeHtml=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const google=p=>'https://www.google.com/maps/search/?api=1&query='+encodeURIComponent(p[2]);
const naver=p=>'https://map.naver.com/p/search/'+encodeURIComponent(p[2]);
const nav=p=>`<a href="${google(p)}" target="_blank" rel="noopener noreferrer">Google ↗</a>${p[3]==='KR'?` · <a href="${naver(p)}" target="_blank" rel="noopener noreferrer">NAVER ↗</a>`:''}`;
function toast(message){const el=document.getElementById('toast');el.textContent=message;el.classList.add('show');clearTimeout(toast.timer);toast.timer=setTimeout(()=>el.classList.remove('show'),3500)}
const format=n=>Math.round(n).toLocaleString('zh-CN');
const symbols={KRW:'₩',JPY:'JP¥',CNY:'CN¥'};
const readNumber=(id,fallback=0)=>{const input=document.getElementById(id),n=Number(input.value);return Number.isFinite(n)&&n>=Number(input.min||0)&&input.value!==''?n:fallback};
const getRates=()=>({KRW:readNumber('krw-rate',5)/1000,JPY:readNumber('jpy-rate',4.8)/100,CNY:1});
function cnyText(cur,lo,hi){const rate=getRates()[cur],a=format(lo*rate),b=format(hi*rate);return `（约人民币 ${a===b?a:a+'–'+b} 元）`}
function foreignMoney(cur,lo,hi=lo,raw){
  raw=raw||symbols[cur]+format(lo)+(lo===hi?'':'–'+format(hi));
  if(cur==='CNY')return escapeHtml(raw);
  return `<span class="foreign-money" data-currency="${cur}" data-low="${lo}" data-high="${hi}">${escapeHtml(raw)}<span class="cny-equivalent">${cnyText(cur,lo,hi)}</span></span>`;
}
function annotateMoneyText(text){
  return escapeHtml(text).replace(/(?<![\w¥₩])(JP¥|₩|¥)\s*(\d[\d,]*(?:\.\d+)?)(?:\s*[–—~～-]\s*(?:JP¥|₩|¥)?\s*(\d[\d,]*(?:\.\d+)?))?/g,(_,symbol,lo,hi)=>foreignMoney(symbol==='₩'?'KRW':'JPY',Number(lo.replaceAll(',','')),Number((hi||lo).replaceAll(',','')),symbol+lo+(hi?'–'+hi:'')));
}
function updateConversions(){document.querySelectorAll('.foreign-money').forEach(el=>{el.querySelector('.cny-equivalent').textContent=cnyText(el.dataset.currency,Number(el.dataset.low),Number(el.dataset.high))})}
const duration=leg=>leg.minutes[0]===leg.minutes[1]?`${leg.minutes[0]} 分钟`:`${leg.minutes[0]}–${leg.minutes[1]} 分钟`;
const distance=leg=>`直线约 ${leg.km} km`;
const legName=leg=>`${points[leg.start][1]} → ${points[leg.end][1]}`;
const legMeta=leg=>`${distance(leg)} · ${leg.mode}约 ${duration(leg)}`;
const legSource=leg=>{const s=trip.sources.find(s=>s[0]===leg.source);return s?` <a href="${escapeHtml(s[2])}" target="_blank" rel="noopener noreferrer">${escapeHtml(s[1])} ↗</a>`:''};
const legPopup=leg=>`<b>${escapeHtml(legName(leg))}</b><strong>${escapeHtml(legMeta(leg))}</strong><p>${escapeHtml(leg.note)}</p><small>公里数为两点直线距离，非道路／轨道里程。${legSource(leg)}</small>`;
let map,markers,lineLayer,shownLegs=[],routeLines=[],activeLeg=-1;
if(window.L){
  map=L.map('map',{scrollWheelZoom:false}).setView([35.55,128.45],6);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'}).addTo(map);
  L.control.scale({imperial:false,maxWidth:120}).addTo(map);
  markers=L.layerGroup().addTo(map);lineLayer=L.layerGroup().addTo(map);
  map.getContainer().querySelector('.map-loading')?.remove();
  map.on('zoomend moveend',updateRouteLabels);
}
function updateRouteLabels(){
  if(!map)return;
  const occupied=[];
  routeLines.forEach(({line,start,end})=>{
    const a=map.latLngToContainerPoint(start),b=map.latLngToContainerPoint(end),mid=a.add(b).divideBy(2);
    const overlaps=occupied.some(p=>Math.abs(p.x-mid.x)<155&&Math.abs(p.y-mid.y)<58);
    // At a country-wide zoom, keep short city hops in the complete route list.
    const size=map.getSize(),visible=a.distanceTo(b)>100&&!overlaps&&mid.x>25&&mid.x<size.x-25&&mid.y>25&&mid.y<size.y-25;
    if(visible){line.openTooltip();occupied.push(mid)}else line.closeTooltip();
  });
}
function focusLeg(index){
  const leg=shownLegs[index];if(!leg)return;activeLeg=index;
  document.querySelectorAll('[data-leg]').forEach(b=>b.setAttribute('aria-pressed',String(Number(b.dataset.leg)===index)));
  document.getElementById('route-status').textContent=`正在看：${legName(leg)} · ${legMeta(leg)}`;
  if(!map)return;
  const a=points[leg.start],b=points[leg.end];
  map.fitBounds([[a[4],a[5]],[b[4],b[5]]],{padding:[62,62],maxZoom:16,animate:false});
  L.popup({maxWidth:300}).setLatLng([(a[4]+b[4])/2,(a[5]+b[5])/2]).setContent(legPopup(leg)).openOn(map);
}
function showMap(mode='all'){
  const day=trip.days.find(d=>String(d.id)===String(mode));
  const ids=day?[...new Set(day.points)]:[...new Set(trip.days.flatMap(d=>d.points))].filter(id=>mode==='all'||points[id][3]===mode);
  const chosen=ids.map(id=>points[id]);activeLeg=-1;
  shownLegs=day?day.legs:trip.days.flatMap(d=>d.legs.filter(l=>l.overview&&(mode==='all'||points[l.start][3]===mode&&points[l.end][3]===mode)).map(l=>({...l,day:d.id})));
  markers?.clearLayers();lineLayer?.clearLayers();routeLines=[];map?.closePopup();
  if(map){
    chosen.forEach((p,i)=>{
      const icon=L.divIcon({className:'',html:`<div class="map-point ${p[3]==='JP'?'jp':''}">${i+1}</div>`,iconSize:[24,24],iconAnchor:[12,12]});
      L.marker([p[4],p[5]],{icon,title:p[1]}).bindPopup(()=>`<b>${escapeHtml(p[1])}${p[0]==='kyuhaku'?' · 可选':''}</b>${annotateMoneyText(p[7])}<br>${nav(p)}`).addTo(markers);
    });
    const edges=new Set();
    shownLegs.forEach(leg=>{
      const key=[leg.start,leg.end].sort().join('|');if(edges.has(key))return;edges.add(key);
      const a=points[leg.start],b=points[leg.end],start=[a[4],a[5]],end=[b[4],b[5]],flight=a[3]!==b[3];
      const line=L.polyline([start,end],{color:flight?'#f5ba77':a[3]==='KR'?'#60a5fa':'#a78bfa',weight:3,dashArray:flight?'9 10':'5 7',opacity:.8}).addTo(lineLayer);
      const related=shownLegs.filter(l=>[l.start,l.end].sort().join('|')===key);
      line.bindPopup(related.map(legPopup).join('<hr>'));
      line.bindTooltip(`<b>${distance(leg)}</b><span>${escapeHtml(leg.mode)} · ${duration(leg)}${related.length>1?' / 单程':''}</span>`,{permanent:true,direction:'center',className:'route-map-label',opacity:1});
      routeLines.push({line,start,end});
    });
    if(chosen.length)map.fitBounds(chosen.map(p=>[p[4],p[5]]),{padding:[48,48],maxZoom:14,animate:false});
    updateRouteLabels();
  }
  const title=day?`D${day.id} · ${day.tag}`:mode==='KR'?'首尔 · 两段停留':mode==='JP'?'九州 · 天草、由布院与太宰府':'两国，一趟秋日旅行';
  const desc=day?`主要地区：${day.region_detail}。${day.mission}`:mode==='KR'?'两段住长汉坪／长安洞。先看下方跨城与市内距离，再选单日查看每一段。':mode==='JP'?'唐人町连住五晚；9/29 天草、9/30 休息、10/1 由布院、10/2 太宰府。下方可查看每段距离、方式与时间。':'下方先列关键移动；选择单日，就能看到从出门到回酒店的每一段。';
  document.getElementById('map-detail').innerHTML=`<span class="micro">${chosen.length} PLACES / ${day?day.date:'OVERVIEW'}</span><h3>${escapeHtml(title)}</h3><p class="map-summary">${escapeHtml(desc)}</p><ol class="map-list">${chosen.map((p,i)=>`<li><span>${i+1}. ${escapeHtml(p[1])}${p[0]==='kyuhaku'?'（可选）':''}</span><span>${nav(p)}</span></li>`).join('')}</ol>${day?`<a class="button small" href="#day-${day.id}">回到 D${day.id} 攻略</a>`:''}`;
  document.getElementById('route-plan').innerHTML=`<div class="route-plan-head"><div><span class="micro">DISTANCE & TIME</span><h3>${day?'D'+day.id+' · 逐段怎么走':'关键移动 · 先建立距离感'}</h3></div><span class="pill">${shownLegs.length} 段</span></div><p class="route-help">公里数为直线参考；地面时间为规划估计，详见各段的起止和候车说明。缩小时较短的线段标签会收起，点「放大这段」即可聚焦。</p><ol class="route-legs">${shownLegs.map((l,i)=>`<li><div class="leg-heading"><span class="leg-index">${String(i+1).padStart(2,'0')}</span><h4>${escapeHtml(legName(l))}${l.optional?'（可选）':''}${l.day?`<small>D${l.day}</small>`:''}</h4><button data-leg="${i}" aria-pressed="false" aria-label="放大这段：${escapeHtml(legName(l))}">放大这段 ↗</button></div><div class="leg-metrics"><strong>${distance(l)}</strong><span>${escapeHtml(l.mode)}</span><b>约 ${duration(l)}</b></div><p>${escapeHtml(l.note)}${legSource(l)}</p></li>`).join('')}</ol><p class="route-status" id="route-status" role="status">选择一天可看完整行程；选择某一段可在地图中放大。</p>`;
  document.querySelectorAll('[data-leg]').forEach(b=>b.addEventListener('click',()=>{focusLeg(Number(b.dataset.leg));document.getElementById('map').scrollIntoView({block:'start',behavior:'auto'})}));
  document.querySelectorAll('[data-map]').forEach(b=>{const active=b.dataset.map===mode;b.classList.toggle('active',active);b.setAttribute('aria-pressed',String(active))});
  document.getElementById('map-day').value=day?String(day.id):'';
}
showMap();
document.querySelectorAll('[data-map]').forEach(b=>b.addEventListener('click',()=>showMap(b.dataset.map)));
document.getElementById('map-day').addEventListener('change',e=>showMap(e.target.value||'all'));
document.querySelectorAll('.map-jump').forEach(b=>b.addEventListener('click',()=>{showMap(b.dataset.day);document.getElementById('map-section').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'})}));

let people=2;
function calcBudget(){
  const rates=getRates();
  const groups={};
  for(const day of trip.days)for(const [category,currency,lo,hi]of day.costs){
    // Keep mixed bundled costs visible, rather than pretending exact allocation.
    const key=category;
    groups[key]??={};groups[key][currency]??=[0,0];groups[key][currency][0]+=lo;groups[key][currency][1]+=hi;
  }
  for(const [label,id]of [['美发 · 自填','hair-budget'],['皮肤 · 自填','skin-budget']]){const n=readNumber(id);if(n)groups[label]={KRW:[n,n]}}
  const hotel=readNumber('kr-hotel-budget');if(hotel)groups['首尔已订住宿 · 自填']={CNY:[hotel,hotel]};
  let total=[0,0];const divide=people===1?2:1;
  document.querySelector('#budget-table tbody').innerHTML=Object.entries(groups).map(([cat,currencies])=>{
    const cny=[0,0];for(const [cur,values]of Object.entries(currencies)){cny[0]+=values[0]*rates[cur];cny[1]+=values[1]*rates[cur]}
    total[0]+=cny[0];total[1]+=cny[1];
    const raw=Object.entries(currencies).map(([cur,v])=>foreignMoney(cur,v[0],v[1])).join('<br>');
    return `<tr><td>${escapeHtml(cat)}</td><td>${raw}</td><td>${cny[0]===cny[1]?'¥'+format(cny[0]/divide):'¥'+format(cny[0]/divide)+'–'+format(cny[1]/divide)}</td></tr>`;
  }).join('');
  document.getElementById('budget-total').textContent=`¥${format(total[0]/divide)}–${format(total[1]/divide)}`;
  document.getElementById('budget-buffer').textContent=`¥${format(total[0]*1.15/divide)}–${format(total[1]*1.15/divide)}`;
  document.getElementById('budget-label').textContent=people===2?'两人 / 基础规划':'每人 / 共同费用均摊';
  document.getElementById('budget-column').textContent=people===2?'人民币 / 两人':'人民币 / 人均';
  updateConversions();
}
document.querySelectorAll('.budget-inputs input').forEach(el=>el.addEventListener('input',calcBudget));
document.querySelectorAll('[data-person]').forEach(b=>b.addEventListener('click',()=>{people=Number(b.dataset.person);document.querySelectorAll('[data-person]').forEach(el=>{const active=Number(el.dataset.person)===people;el.classList.toggle('active',active);el.setAttribute('aria-pressed',String(active))});calcBudget()}));calcBudget();

const checkboxes=[...document.querySelectorAll('[data-check]')];
let saved={};try{saved=JSON.parse(localStorage.getItem('kr-jp-2026-checks')||'{}')||{}}catch{}
function progress(){document.getElementById('check-progress').textContent=`${checkboxes.filter(x=>x.checked).length} / ${checkboxes.length} 项完成`}
checkboxes.forEach(c=>{c.checked=saved[c.dataset.check]===true;c.addEventListener('change',()=>{saved[c.dataset.check]=c.checked;try{localStorage.setItem('kr-jp-2026-checks',JSON.stringify(saved))}catch{}progress()})});progress();
document.querySelectorAll('.copy').forEach(button=>button.addEventListener('click',async()=>{const text=document.getElementById(button.dataset.copy).textContent;try{await navigator.clipboard.writeText(text);toast('询问文本已复制；尚未发送')}catch{const selection=getSelection();const range=document.createRange();range.selectNodeContents(document.getElementById(button.dataset.copy));selection.removeAllRanges();selection.addRange(range);toast('已选中文字，请手动复制')}}));
let originalDetails=[];
window.addEventListener('beforeprint',()=>{originalDetails=[...document.querySelectorAll('details')].map(d=>[d,d.open]);originalDetails.forEach(([d])=>d.open=true)});
window.addEventListener('afterprint',()=>originalDetails.forEach(([d,open])=>d.open=open));
document.getElementById('print').addEventListener('click',()=>window.print());

// One itinerary, three accessible tabs; date links reveal their containing segment.
const segmentTabs=[...document.querySelectorAll('[data-segment]')];
const segmentPanels=[...document.querySelectorAll('.trip-panel')];
function selectSegment(key){
  segmentTabs.forEach(t=>{const on=t.dataset.segment===key;t.setAttribute('aria-selected',String(on));t.tabIndex=on?0:-1});
  segmentPanels.forEach(p=>p.hidden=p.id!=='segment-'+key);
}
function revealHash(scroll=false){
  const target=document.getElementById(location.hash.slice(1));
  const panel=target?.closest('.trip-panel');
  if(panel){selectSegment(panel.id.replace('segment-',''));if(scroll)target.scrollIntoView({block:'start'})}
}
segmentTabs.forEach((t,i)=>{
  t.addEventListener('click',()=>{selectSegment(t.dataset.segment);history.replaceState(null,'','#segment-'+t.dataset.segment);document.querySelector('.trip-tabs').scrollIntoView({block:'start'})});
  t.addEventListener('keydown',e=>{let next;if(e.key==='ArrowRight')next=(i+1)%3;if(e.key==='ArrowLeft')next=(i+2)%3;if(e.key==='Home')next=0;if(e.key==='End')next=2;if(next!==undefined){e.preventDefault();segmentTabs[next].focus();segmentTabs[next].click()}});
});
selectSegment('korea-first');revealHash(true);
window.addEventListener('hashchange',()=>revealHash(true));
document.addEventListener('click',e=>{const a=e.target.closest('a[href^="#day-"]');if(!a)return;const target=document.getElementById(a.getAttribute('href').slice(1));const panel=target?.closest('.trip-panel');if(panel)selectSegment(panel.id.replace('segment-',''))});
