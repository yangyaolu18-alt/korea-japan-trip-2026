#!/usr/bin/env python3
"""Build a private, portable guide and Google My Maps imports from one data file."""
import csv, io, json, html, zipfile, math
from pathlib import Path
from collections import defaultdict
from urllib.parse import quote
import xml.etree.ElementTree as ET
from currency import annotate, annotate_html

ROOT = Path(__file__).resolve().parent
D = json.loads((ROOT/'trip-data.json').read_text())
E = html.escape
places = {p[0]:p for p in D['places']}
sources = {s[0]:s for s in D['sources']}
def link(url,label): return f'<a href="{E(url,quote=True)}" target="_blank" rel="noopener noreferrer">{E(label)} ↗</a>'
def cite(ids): return ' · '.join(link(sources[k][2],sources[k][1]) for k in ids)
def google(p): return 'https://www.google.com/maps/search/?api=1&query='+quote(p[2])
def naver(p): return 'https://map.naver.com/p/search/'+quote(p[2])
def navlinks(p): return link(google(p),'Google Maps')+(' · '+link(naver(p),'NAVER Map') if p[3]=='KR' else '')
def money(cur,n): return {'KRW':'₩','JPY':'JP¥','CNY':'CN¥'}[cur]+f'{n:,.0f}'
def money_range(cur,a,b): return money(cur,a) if a==b else money(cur,a)+'–'+money(cur,b)
def totals(day):
    t=defaultdict(lambda:[0,0])
    for _,cur,a,b in day['costs']:t[cur][0]+=a;t[cur][1]+=b
    return ' ＋ '.join(money_range(c,a,b) for c,(a,b) in t.items())

def straight_km(leg):
    a,b = places[leg['start']],places[leg['end']]
    lat1,lat2 = math.radians(a[4]),math.radians(b[4])
    dx,dy = lat2-lat1,math.radians(b[5]-a[5])
    v = math.sin(dx/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dy/2)**2
    return round(6371 * 2 * math.atan2(math.sqrt(v), math.sqrt(1-v)), 1)
def leg_time(leg):
    a,b=leg['minutes']
    return (str(a) if a==b else f'{a}–{b}')+' 分钟'
def leg_text(leg):
    return f"{places[leg['start']][1]} → {places[leg['end']][1]}：直线约 {leg['km']:g} km · {leg['mode']}约 {leg_time(leg)}。{leg['note']}"
for day in D['days']:
    for leg in day['legs']:leg['km']=straight_km(leg)
for leg in D.get('alternative_legs',[]):leg['km']=straight_km(leg)
for day in D.get('japan_alternatives',[]):
    for leg in day['legs']:leg['km']=straight_km(leg)

base_cost=[sum(c[i]*{'JPY':.048,'KRW':.005,'CNY':1}[c[1]] for d in D['days'] for c in d['costs']) for i in (2,3)]
base_range=f'{base_cost[0]:,.0f}–{base_cost[1]:,.0f}'

def data_table(headings,rows):
    return '<div class="table-scroll"><table><thead><tr>'+''.join('<th>'+E(h)+'</th>' for h in headings)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+E(c)+'</td>' for c in row)+'</tr>' for row in rows)+'</tbody></table></div>'

plan=D['japan_plan']
review=D['itinerary_review']
audit_html='<div class="japan-decisions panel itinerary-review" id="itinerary-review"><span class="eyebrow">ITINERARY CHECK / '+E(review['checked'])+'</span><h3>'+E(review['verdict'])+'</h3><p>'+E(review['summary'])+'</p><div class="review-recommendation"><b>已确认主线：两次远途，中间休息</b><p>'+E(review['recommendation'])+'</p><small>'+E(review['alternative_note'])+'</small></div><p>'+E(review['date_flex'])+'</p><details><summary>展开逐日复核 · 10 天哪里顺、哪里紧</summary>'+data_table(['日期／地区','判断','原因与修正'],review['rows'])+'</details><details><summary>能执行之前，还要落实哪些预约？</summary><ul>'+''.join('<li>'+E(s)+'</li>' for s in review['conditions'])+'</ul></details><div class="day-note"><b>JR Pass 随路线选</b><p>'+E(review['rail'])+'</p></div><p class="muted">'+E(review['boundary'])+'</p><small>'+cite(review['sources'])+'</small></div>'
japan_decisions='<div class="japan-decisions panel" id="japan-choices"><span class="eyebrow">FUKUOKA AS A BASE</span><h3>最终路线：保留喜欢的体验，减少赶路</h3><p>'+E(plan['intro'])+'</p>'+data_table(['日期','原来的安排','这版主线','取舍'],plan['changes'])+'<details><summary>展开 7 条路线比较 · 含酒店往返时间</summary>'+data_table(['目的地','建议','时间代价','为什么'],plan['choices'])+'<p class="muted">'+E(plan['time_note'])+'</p></details><p>替换项地图：'+''.join(f'<a class="button small" href="exports/alternative-japan-{key}.kml" download>↓ {name}</a> ' for key,name in [(a['key'],a['label']) for a in D['japan_alternatives']])+'</p></div>'
japan_decisions+='<div class="japan-decisions panel" id="jr-pass"><span class="eyebrow">RAIL PASS / 09.29 — 10.01</span><h3>值得买：北部九州 3 日券，9/29–10/1</h3>'+data_table(['票种','单人','两人','适用判断'],plan['rail_rows'])+'<h4>相同四段铁路：散买 vs 通票</h4>'+data_table(['比较项目','单人','两人','计算口径'],plan['rail_comparison'])+'<div class="pass-reasons">'+''.join('<p>'+E(n)+'</p>' for n in plan['rail_notes'][:3])+'</div><details><summary>覆盖范围、6 次指定席怎么分、买票顺序</summary>'+''.join('<p>'+E(n)+'</p>' for n in plan['rail_notes'][3:])+'</details><p class="muted">本版预算只在 9/29 计一次两人 3 日券；餐厅单餐额度属于当天餐饮，不重复相加。天草巴士、船票、温泉与太宰府交通已计入；博物馆及由布院之森提前网约费用只计入上限。志贺岛、小仓／门司港、别府仍为替换项。</p><small>'+cite(plan['sources'])+'</small></div>'

tickets=D['japan_tickets']
japan_decisions+='<div class="japan-decisions panel" id="japan-tickets"><span class="eyebrow">TICKETS / CHECKED 2026.09.23</span><h3>海豚、温泉与太宰府：多少钱，怎么订</h3><p>以下都是成人价格；每天另有完整费用拆分。金额后附人民币参考，换算率可在预算区调整。</p>'+data_table(['地区／项目','每人','两人','预约方式'],tickets['rows'])+'<div class="closure-note"><b>10/1 梦想园：先泡汤，再逛街</b><p>周四小男汤「弘法の湯」清扫，大男露天汤「御夢想の湯」按常规开放。日归 14:00 截止接待、14:30 结束；临时营业出发前再确认。</p></div><p>天草属于熊本县上天草市；由布院属于大分县由布市。别府也在大分县，目前仅作由布院替换项；小仓／门司港在福冈县北九州市，不是福冈市。</p><small>'+cite(tickets['sources'])+'</small></div>'
japan_decisions=audit_html+japan_decisions

# Export only itinerary places, preserving visit order. Optional museum is explicit.
def export_set(days,stem):
    used={}
    for day in days:
        for pid in dict.fromkeys(day['points']):used.setdefault(pid,[]).append(day)
    rows=[]
    for pid,ds in used.items():
        p=places[pid]
        arrivals='\n'.join(f"D{d['id']} {leg_text(l)}" for d in ds for l in d.get('legs',[]) if l['end']==pid)
        rows.append({'Name':p[1]+('（可选）' if p[6]=='可选' and '可选' not in p[1] else ''),'Latitude':p[4],'Longitude':p[5],
          'Day':', '.join('D'+str(d['id']) for d in ds),'Dates':', '.join(d['iso'] for d in ds),'Regions':' / '.join(dict.fromkeys(d.get('region','') for d in ds)),
          'Category':p[6],'Description':annotate(p[7])+'；地图坐标为区域/地标参考，请以导航入口为准。\n'+arrivals+'\n距离为参考点间直线距离，非道路或轨道里程；地面耗时为规划估计，非实时导航。人民币按 ₩1,000＝5 元、JP¥100＝4.8 元估算。','GoogleMaps':google(p)})
    out=ROOT/'exports';out.mkdir(exist_ok=True)
    with (out/(stem+'.csv')).open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    ns='http://www.opengis.net/kml/2.2';ET.register_namespace('',ns)
    kml=ET.Element('{'+ns+'}kml');doc=ET.SubElement(kml,'Document');ET.SubElement(doc,'name').text='首尔与北九州 · '+stem
    ET.SubElement(doc,'description').text='2026 私人旅行最终路线；预约待落实，点位参考，不含实时路线、订单与医疗信息。'
    for r in rows:
        pm=ET.SubElement(doc,'Placemark');ET.SubElement(pm,'name').text=r['Name']
        ET.SubElement(pm,'description').text=r['Day']+' | '+r['Dates']+' | '+r['Regions']+'\n'+r['Description']+'\n'+r['GoogleMaps']
        ext=ET.SubElement(pm,'ExtendedData')
        for key in ('Day','Dates','Regions','Category'):
            v=ET.SubElement(ext,'Data',name=key);ET.SubElement(v,'value').text=r[key]
        pt=ET.SubElement(pm,'Point');ET.SubElement(pt,'coordinates').text=f"{r['Longitude']},{r['Latitude']},0"
    ET.ElementTree(kml).write(out/(stem+'.kml'),encoding='utf-8',xml_declaration=True)
    return len(rows)
pointcount=export_set(D['days'],'all-places')
for day in D['days']:export_set([day],f"day-{day['id']:02d}")
segments=[
 ('korea-first','韩国前程','09.26 — 09.28',[1,2],'入住 Recenz，景福宫与两人美发。9/28 的机场出发写在九州段 D3。'),
 ('japan','日本九州','09.28 — 10.03',list(range(3,9)),'福冈连住 5 晚：9/29 天草、9/30 市内恢复、10/1 由布院、10/2 太宰府。先看最终路线与 3 日 JR Pass 比较，再按日期展开。D3 / D8 包含日韩两端接驳。'),
 ('korea-last','韩国后程','10.03 — 10.05',[9,10],'入住 Signature，皮肤咨询或圣水散步。10/3 深夜抵达接驳见九州段 D8。')
]
for key,_,_,ids,_ in segments:
    export_set([d for d in D['days'] if d['id'] in ids],'segment-'+key)

alternative=dict(D['days'][8],points=['signature','seongsu','forest'],legs=D['alternative_legs'])
export_set([alternative],'alternative-seongsu')
for day in D['japan_alternatives']:
    export_set([day],'alternative-japan-'+day['key'])

flights=''.join('<tr>'+''.join(f'<td>{E(x)}</td>' for x in row)+'</tr>' for row in D['flights'])
overview=''.join(f'''<a class="route-day" href="#day-{d['id']}"><span class="micro">{d['date']} · {d['week']}</span><strong><i>{d['id']:02}</i>{E(d['tag'])}</strong><span class="region-label">{E(d['region'])}</span><p>{E(d['mission'])}</p><small>{E(d['sleep'])}</small></a>''' for d in D['days'])
dayhtml=''
daycards={}
for d in D['days']:
    dayreview='<div class="daily-review"><b>复核：'+E(d['review']['verdict'])+'</b><p>'+E(d['review']['note'])+'</p></div>'
    fees=''
    if d.get('fees'):
        fees='<div class="daily-fees"><h4>门票与项目费用 · 成人</h4>'+data_table(['项目','每人','两人','预约／说明'],d['fees'])+'<p>'+E(d['fee_note'])+'</p><small>'+cite(d['fee_sources'])+'</small></div>'
    meals=''
    if d.get('meals'):
        meals='<div class="meal-plan"><h4>今天吃哪家 · 已计入当天餐饮</h4>'+''.join(f'<article class="meal"><span class="micro">{E(t)}</span><h4>{E(places[p][1])}</h4><b>{E(b)}</b><p>{E(order)}。{E(note)}</p><small>{navlinks(places[p])} · {cite([src])}</small></article>' for t,p,order,b,note,src in d['meals'])+'</div>'
    timelines=''.join(f'<li><time>{E(t)}</time><div><h4>{E(ti)}</h4><p>{E(desc)}</p></div></li>' for t,ti,desc in d['timeline'])
    stops=''.join(f'<div class="place"><span>{E(places[p][1])}{" · 可选" if p=="kyuhaku" else ""}</span><small>{navlinks(places[p])}</small></div>' for p in dict.fromkeys(d['points']))
    costrows=''.join(f'<tr><td>{E(cat)}</td><td>{money_range(cur,a,b)}</td></tr>' for cat,cur,a,b in d['costs'])
    legs=''.join(f'<li><span>{E(places[l["start"]][1])} → {E(places[l["end"]][1])}{"（可选）" if l.get("optional") else ""}</span><strong>直线约 {l["km"]:g} km · {E(l["mode"])}约 {leg_time(l)}</strong><small>{E(l["note"])}{(" "+cite([l["source"]])) if l.get("source") else ""}</small></li>' for l in d['legs'])
    daycards[d['id']]=f'''<article class="day panel" id="day-{d['id']}">
      <header class="day-head"><div class="day-no">{d['id']:02}</div><div><div class="micro">{d['date']} · {d['week']} / {E(d['tag'])}</div><p class="day-region"><b>主要地区：{E(d['region'])}</b><span>{E(d['region_detail'])}</span></p><h3>{E(d['title'])}</h3><p class="mission">{E(d['mission'])}</p></div><span class="pill">{E(d['pace'])}</span></header>
      {dayreview}<div class="day-columns"><div><ol class="timeline">{timelines}</ol>{fees}<div class="day-note"><b>怎么走</b><p>{E(d['transport'])}</p><details class="daily-legs"><summary>逐段距离与交通时间 · {len(d['legs'])} 段</summary><ol>{legs}</ol><small>公里数为参考点间直线距离，实际道路／轨道通常更长；耗时按交通方式独立估计，不由直线距离推算。</small></details></div><div class="day-note"><b>怎么吃</b><p>{E(d['food'])}</p></div>{meals}</div>
      <aside><div class="sleep"><span class="micro">TONIGHT</span><p>{E(d['sleep'])}</p></div><div class="day-cost"><span class="micro">两人当天 · 首尔房费与项目另计</span><strong>{totals(d)}</strong><details><summary>费用拆分</summary><table>{costrows}</table></details></div><div class="day-note accent"><b>需要提前确认</b><p>{E(d['booking'])}</p></div><div class="day-note"><b>雨天 / 太累时</b><p>{E(d['fallback'])}</p></div><details class="stop-details"><summary>地图与导航 · {len(set(d['points']))} 个地点</summary>{stops}<a class="button small" href="exports/day-{d['id']:02}.kml" download>下载 D{d['id']} 地图 KML</a></details><button class="button small map-jump" data-day="{d['id']}">在概览地图看这一天 ↗</button></aside></div><div class="citations">参考：{cite(d['sources'])}。航班来自你的截图；地面时间为规划估计。</div></article>'''
tabs=''.join(f'<button role="tab" id="tab-{key}" aria-controls="segment-{key}" aria-selected="{str(i==0).lower()}" tabindex="{0 if i==0 else -1}" data-segment="{key}"><small>0{i+1} / {dates}</small><strong>{name}</strong></button>' for i,(key,name,dates,_,_) in enumerate(segments))
dayhtml='<div class="trip-tabs" role="tablist" aria-label="选择行程段">'+tabs+'</div>'
for key,name,dates,ids,note in segments:
    jump=('<a href="#day-3">查看 9/28 出发安排 ↗</a>' if key=='korea-first' else '<a href="#day-8">查看 10/3 抵达安排 ↗</a>' if key=='korea-last' else '')
    index=''.join(f'<a href="#day-{d["id"]}"><b>{d["id"]:02}</b><span>{d["date"]}</span></a>' for d in D['days'] if d['id'] in ids)
    dayhtml+=f'<div class="trip-panel" role="tabpanel" id="segment-{key}" aria-labelledby="tab-{key}" tabindex="0"><div class="segment-intro"><div><h3>{name}<span>{dates}</span></h3><p>{note} {jump}</p></div><a class="button small" href="exports/segment-{key}.kml" download>↓ 这段地图</a></div><div class="day-index">{index}</div>'+(japan_decisions if key=='japan' else '')+''.join(daycards[i] for i in ids)+'</div>'
hotels=''.join(f'''<article class="panel hotel"><div class="micro">{E(h['nights'])}</div><h3>{E(h['place'])}</h3><p>{E(h['reason'])}</p><strong>{E(h['budget'])}</strong><p class="muted">{E(h['names'])}</p><small>{cite([h['source']])}</small></article>''' for h in D['hotels'])
foods=''.join(f'''<article class="food-item"><span class="micro">{E(f[0])}</span><h3>{E(f[1])}</h3><strong>{E(f[2])}</strong><p>{E(f[3])}</p><small>{navlinks(places[f[4]])}{(' · '+cite([f[5]])) if f[5] else ''}</small></article>''' for f in D['food'])
checks=''.join(f'<label class="check"><input type="checkbox" data-check="{E(i)}"><span>{annotate(E(v),rich=True)}</span></label>' for i,v in D['checklist'])
sourcehtml=''.join(f'<li id="source-{s[0]}">{link(s[2],s[1])}<p>{E(s[3])}</p></li>' for s in D['sources'])
allpoints=''.join(f'<div class="place"><span>{E(p[1])}</span><small>{navlinks(p)}</small></div>' for p in D['places'] if any(p[0] in d['points'] for d in D['days']))

TEMPLATE='''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#08090a"><title>首尔与北九州 · 2026 秋日旅行</title><meta name="description" content="两个人的十日日韩旅行：首尔、福冈、天草、由布院与太宰府。每日主线、交通预算与可导出地图。"><link rel="stylesheet" href="assets/leaflet.css"><link rel="stylesheet" href="style.css"></head><body>
<a class="skip" href="#overview">跳到行程内容</a>
<header class="hero"><div class="hero-image"></div><div class="topline"><a href="#" class="brand">TWO OF US <span>/ ON THE ROAD</span></a><span class="edition">PRIVATE TRIP · 2026 / 09</span></div><div class="hero-content"><div class="eyebrow">SEOUL → FUKUOKA / AMAKUSA / YUFUIN / DAZAIFU → SEOUL</div><h1>跨过海，<br>慢慢玩。</h1><p class="hero-sub">首尔与北九州 · 两个人的秋日旅行</p><p class="hero-desc">换一个发型，吃一碗博多拉面，<br class="mobile-only">把一天留给山里的温泉。</p><div class="hero-stats"><div><strong>10</strong><span>个日历日</span></div><div><strong>09</strong><span>晚住宿</span></div><div><strong>02</strong><span>个人 · 公共交通</span></div><div class="stat-date"><strong>09.26 — 10.05</strong><span>2026 · 10/06 凌晨抵达南京</span></div></div><a href="#overview" class="button primary">展开这次旅行 ↓</a></div><small class="photo-credit">福冈夜景 · 图片来自福冈市官方旅游网站</small></header>
<nav class="nav" aria-label="攻略目录"><a class="nav-logo" href="#">KR / JP <em>2026</em></a><div><a href="#overview">总览</a><a href="#map-section">地图</a><a href="#itinerary">每日攻略</a><a href="#experiences">头发与皮肤</a><a href="#stay">住宿</a><a href="#food">美食</a><a href="#budget">预算</a><a href="#ready">出发准备</a></div><button class="print-button" id="print">打印 / PDF</button></nav>
<main><section id="overview"><div class="section-title"><div><span class="eyebrow">01 / THE PLAN</span><h2>有主线，也留白。</h2></div><span class="pill pending">酒店已适配 · 9/23 核验</span></div><p class="lead">日本最终主线：福冈连住 + 天草海豚 + 福冈恢复 + 由布院温泉 + 太宰府半日；两次远途中间完整休息一天。首尔围绕第一次来值得看的老城，以及想做的美发和皮肤项目展开。</p>
<div class="notice"><b>先读这条</b><p>截图对应 9/26–10/5 共 10 个日历日、9 晚。日本有 4 个完整白天 + 10/3 大半天；首尔完整白天是 9/27、10/4。三家酒店共 9 晚已订；保留福冈 5 晚，10/1 由布院日归。两段首尔酒店都在城市东部，已按实际位置留出交通时间。</p></div>
<div class="brief-grid"><div class="panel brief"><span class="micro">01 · 城市与项目</span><h3>首尔 / 两段，各两晚</h3><p>前程：景福宫、仁寺洞与两人美发。后程：一人皮肤咨询；没有预约就去圣水与首尔林。</p></div><div class="panel brief"><span class="micro">02 · 两次远途，中间休息</span><h3>福冈连住 5 晚，近郊与休息穿插</h3><p>New Gaea Domemae 位于唐人町。9/29 天草海豚，9/30 市内休息，10/1 由布院，10/2 太宰府半日。酒店到博多留 35–50 分钟；太宰府经天神转西铁。</p></div><div class="panel brief"><span class="micro">03 · 预算与预订</span><h3>房费已知，项目按需加</h3><p>福冈 5 晚 JP¥58,693 已计入预算。两段首尔房费待填；美发先看发型报价，皮肤针对暗沉先面诊。</p></div></div>
<div class="notice review-overview"><b>9/23 确认：最终路线与费用已同步</b><p>取消阿苏，9/30 福冈休息、10/1 由布院、10/2 太宰府；每日地图、导出、餐厅日期和预算已更新。<a href="#itinerary-review">看最终安排 →</a> · <a href="#jr-pass">为什么买北部九州 3 日券 →</a></p></div><div class="route-strip">@@OVERVIEW@@</div>
<div class="alerts"><article><span>节假日</span><h3>两段首尔都碰上假日周末</h3><p>秋夕为 9/24–26；10/3 开天节、10/5 补休。9/27 与 10/4 都是周日，美发和诊所必须逐家确认，不能按平日营业推算。</p><small>@@HOLIDAY@@</small></article><article><span>机场</span><h3>T1 / T2 分清，晚到留后手</h3><p>东方航空在截图中使用仁川 T1，大韩航空使用 T2。10/3 21:35 落地，不押注末班铁路；保留出租车预算，并确认酒店午夜后入住。</p><small>航站楼取自截图，出发前以航司通知复核。</small></article></div>
<details class="panel flight-panel"><summary>已提供航班 · 5 段 / 全部为当地时间</summary><div class="table-scroll"><table><thead><tr><th>日期</th><th>航班</th><th>出发</th><th>抵达</th><th>安排</th></tr></thead><tbody>@@FLIGHTS@@</tbody></table></div><p class="muted">日韩均为 UTC+9，中国为 UTC+8；截图下方 10/28 行程不属于本次旅行。未做航司实时状态核验。</p></details></section>

<section id="map-section"><div class="section-title"><div><span class="eyebrow">02 / A MAP TO TAKE WITH YOU</span><h2>把地点放在一起。</h2></div><a class="text-link" href="#map-export">带去 Google 地图 ↗</a></div><p class="lead">每段都能看到公里数、交通方式和预计时间。公里数是两点间的<b>直线距离</b>，帮助判断远近；实际路程更长，耗时按交通方式单独估计。蓝色为韩国，紫色为日本，橙色为航班。</p><div class="map-controls" role="group" aria-label="地图筛选"><button class="active" data-map="all" aria-pressed="true">全部</button><button data-map="KR" aria-pressed="false">首尔</button><button data-map="JP" aria-pressed="false">日本九州</button><label>单日 <select id="map-day"><option value="">选择一天</option>@@DAYOPTIONS@@</select></label></div><div class="map-layout panel"><div id="map" role="region" aria-label="旅行概览地图"><div class="map-loading">正在加载地图。离线时仍可使用下方地点清单与导出文件。</div></div><aside id="map-detail" aria-live="polite"></aside></div><div class="route-plan panel" id="route-plan" aria-live="polite"></div><small class="muted">底图需要联网；虚线不是道路或航线导航。坐标为区域 / 地标参考点，实际入口请用导航确认。三家已订酒店已标出；弘大美发和明洞咨询使用区域参考点，尚无确认预约。</small><details class="panel all-places"><summary>全部地点与导航链接（离线也能查看名称）</summary><div class="places-grid">@@ALLPOINTS@@</div></details>
<div class="export panel" id="map-export"><div><span class="micro">GOOGLE MY MAPS</span><h3>地图，随身带走。</h3><p>在电脑打开 <a href="https://www.google.com/mymaps" target="_blank" rel="noopener">Google 我的地图</a> → 创建地图 → 图层「导入」。KML 可直接导入；CSV 选择 Latitude / Longitude 定位、Name 作标题，可按 Day 着色。手机 Google Maps 在「已保存 / 你」→「地图」查看（界面名称可能不同）。</p><p class="muted">这会创建自定义地图，不会自动变成普通收藏列表，也不会生成逐向导航。导出包含 @@POINTCOUNT@@ 个参考点，地点说明附到达段的直线公里数与交通耗时；分段 KML 位于各 Tab，每日 KML 位于每日卡片内。圣水替代线可<a href="exports/alternative-seongsu.kml" download>单独下载</a>。@@MYMAPS@@</p></div><div class="export-actions"><a class="button primary" href="exports/all-places.kml" download>↓ 全程地图 KML</a><a class="button" href="exports/all-places.csv" download>↓ 全程地点 CSV</a></div></div></section>

<section id="itinerary"><div class="section-title"><div><span class="eyebrow">03 / DAY BY DAY</span><h2>每天有主线，分段慢慢看。</h2></div></div><p class="lead">时间是参考节奏，航班是固定边界。每天费用按两人计算，含已知福冈房费；首尔房费、美发、皮肤、购物和机票另计。跨国移动日 D3、D8 归在九州段，完整写明两端接驳。</p>@@DAYS@@</section>

<section id="experiences"><div class="section-title"><div><span class="eyebrow">04 / YOUR APPOINTMENTS</span><h2>把想做的项目，安排得从容。</h2></div><span class="pill pending">诉求已明确 · 档期待确认</span></div><div class="experience-grid"><article class="panel experience"><span class="micro">HAIR / 美发</span><h3>优先第一段，先换好发型。</h3><p>首选 <b>9/27 14:00 左右</b>，上午先看景福宫，中午再转去弘大；两人都做烫染时，先问能否同时服务。剪发暂留 1–1.5 小时，烫染暂留 3–4 小时，以店家答复为准。预约超过半天就删减宫殿或老城，不压缩美发时间。</p><div class="mini-card"><b>可联系的两家候选</b><p><b>SOONSIKI 弘大</b>：有面向国际客人的介绍与预约入口。<br><b>CCA Hair 弘大</b>：可先询问男士剪发、烫发和语言支持。</p><small>@@HAIR@@</small></div><p><b>预算先留：</b>剪发每人 ₩30,000–80,000；剪发加烫发每人 ₩120,000–250,000。均为规划额度，设计师、发长、漂染和护理会改变总价，需获得含税完整报价。</p><p class="muted">准备 2–3 张目标与避雷发型照片，说明能否接受每天吹整。不要只说“韩式”。没有确认档期时，D2 自动切换成景福宫＋仁寺洞路线，另询 10/4。</p><details><summary>复制给美发店的韩文询问</summary><p class="message" id="hair-message">안녕하세요. 남성 2명입니다. 2026년 9월 27일 오후 2시 예약이 가능한가요? 두 명이 동시에 시술받을 수 있나요? 원하는 스타일 사진을 보내드리겠습니다. 컷/펌/염색별 총 소요 시간과 부가세를 포함한 총금액, 추가 비용을 알려 주세요. 추석 연휴 영업 여부와 취소 규정도 확인 부탁드립니다.</p><button class="button small copy" data-copy="hair-message">复制询问</button><small>我替你写好询问文本，尚未发送或预约。</small></details></article>
<article class="panel experience"><span class="micro">SKIN / 皮肤</span><h3>想改善暗沉，先判断原因。</h3><p>你一人考虑“光子”，男朋友暂不安排皮肤项目。<b>值得先咨询，是否做光子不能只凭“暗沉”决定。</b>肤色不均、色素、干燥或刺激需要区别评估；一次治疗也不保证提亮。由皮肤科医生判断适应证、预期改善和替代方案。</p><div class="mini-card"><b>安排在 10/4，留出半天</b><p>预约 11:30 或更晚的面诊，再决定是否治疗。日本温泉已在此前完成；但翌日离境，仍需问清恢复、日晒、飞行与回国后的联系和随访。如果需要更长观察期，这次就保留咨询。</p></div><p><b>心理预算：</b>先留 ₩100,000–300,000 给你一人的咨询／基础项目。这是规划额度，不是光子报价；税费、设备、部位、疗程需书面报价，不预设购买套餐。</p><div class="mini-card"><b>可先询问：Beauty Lounge 明洞</b><p>官网列有周日门诊，可问 10/4 是否正常接诊。假期档期、接诊医生、语言和外国患者登记尚待核实；候选不代表医疗推荐。JFeel 弘大官网周日休诊，不排入这一天。</p><small>@@CLINIC@@</small></div><p><b>面诊带着问：</b>“我的暗沉原因是什么，光子适合吗？”“是否有更温和的处理？”“预计改善多少、要几次？”“恢复多久，10/5 飞行是否合适？”“费用含税吗，回国后如何随访？”</p><small>@@MEDICAL@@</small><p class="muted">没有确认预约时，整段改为圣水＋首尔林散步；若治疗，下午按医生建议休息，不叠加长时间户外暴晒和汗蒸。</p></article></div></section>

<section id="stay"><div class="section-title"><div><span class="eyebrow">05 / A GOOD PLACE TO STAY</span><h2>住得顺，玩得松。</h2></div></div><p class="lead">按你提供的三家酒店和入住日期编排，保留全部 9 晚。福冈房费采用你提供的订单总额；两段首尔房费尚未提供。</p><div class="hotel-grid">@@HOTELS@@</div><div class="photo-band"><img src="assets/kinrin.jpg" alt="由布院金鳞湖的雾气与山景参考照片" loading="lazy"><div><span class="micro">YUFUIN / DAY TRIP</span><h3>先泡温泉，<br>再逛小镇。</h3><p>梦想园日归接待为 10:00–14:00，14:30 结束，所以到站后先去泡汤，再吃午餐、逛汤之坪与金鳞湖。成人 ¥1,000；家庭汤只能现场等空位，不保证私汤。毛巾自带，营业及刺青规则出发前问清。</p><small>照片来自 JR 九州，为景观参考；不保证本次能见到晨雾。@@ONSEN@@</small></div></div><details class="panel flight-panel"><summary>为什么这次保留福冈 5 晚？温泉过夜的费用对比</summary><p>已订五晚总额 JP¥58,693，平均每晚约 ¥11,739。由布院两人一泊二食暂按 ¥45,000–70,000 规划，未查实时余房。</p><p>若可退一晚约 ¥11,739，住宿差额约 <b>人民币 1,600–2,800 元</b>；若福冈不能退，需另加 <b>2,160–3,360 元</b>。这是按初始汇率计算的住宿差额示例，实际按可退款额计算；旅馆含的晚餐和早餐可抵部分原餐费，交通差价另核。</p><p class="muted">已按你的选择保留福冈 5 晚，不计入上述升级。日归梦想园两人入浴约 ¥2,000，另有往返交通，均已放入 D6（10/1）。上面的住宿差额示例按每百日元＝人民币 4.8 元计算。</p></details></section>

<section id="food"><div class="section-title"><div><span class="eyebrow">06 / EAT YOUR WAY AROUND</span><h2>把好吃的放在顺路的地方。</h2></div></div><p class="lead">日本段已安排具体餐厅与分店，并放进每日卡片、导航和导出地图。以下为两人单餐规划额度，已计入每日餐饮，不再另加；营业信息需在到店前复核，均未预约。</p><div class="food-grid">@@FOOD@@</div><div class="notice"><b>关于屋台与预订</b><p>屋台适合体验气氛，先看明码菜单、确认席费和每人点单要求；排队过长或下雨就换店。由布院为日归，午晚餐均按自费计入；当天不另订温泉旅馆。生食、内脏、过敏与酒精偏好待你补充。</p></div></section>

<section id="budget"><div class="section-title"><div><span class="eyebrow">07 / MONEY, CLEARLY</span><h2>预算有范围，花钱有重点。</h2></div><div class="segmented" aria-label="预算人数"><button class="active" data-person="2" aria-pressed="true">两人合计</button><button data-person="1" aria-pressed="false">人均分摊</button></div></div><p class="lead">不含已买机票、购物、美发／皮肤默认费用，以及尚未报价的保险、通信。已含福冈 5 晚 JP¥58,693、两人北部九州 3 日券 JP¥28,000（仅计一次）、非 JR 交通、餐饮、门票、威海转机休息与南京深夜接送。<b>首尔 4 晚房费尚未计入</b>，可在下方填写；福冈若另收住宿税，两人五晚再留 ¥2,000 日元。</p><div class="notice"><b>先看心理预期</b><p>按初始汇率，两人基础约人民币 <b>@@BASE_RANGE@@ 元＋首尔 4 晚实际房费</b>（含已付福冈住宿）。两人剪＋烫与一人基础皮肤项目再预留约 <b>1,700–4,000 元</b>；若仅两人剪发加一人皮肤项目，约加 <b>800–2,300 元</b>。均不含购物、机票、保险通信；项目以面诊和店家报价为准。</p></div><div class="notice"><b>这版费用怎么变了</b><p>通票从 5 日改为 3 日，两人少 JP¥4,000；取消阿苏的登山巴士、博物馆／骑马预留及清晨出租车，加入太宰府地铁＋西铁。由布院之森提前网约两人往返 JP¥6,000 与可选博物馆 JP¥1,400 只放入上限，现场免费划位／不进馆便不花这部分。<a href="#jr-pass">查看散买与通票逐项比较 →</a></p></div><div class="budget-inputs panel"><label>₩1,000 ≈ 人民币<input id="krw-rate" type="number" min="0.01" step="0.1" value="5"></label><label>JP¥100 ≈ 人民币<input id="jpy-rate" type="number" min="0.01" step="0.1" value="4.8"></label><label>美发额外预算 · 两人/韩元<input id="hair-budget" type="number" min="0" step="10000" value="0"></label><label>皮肤额外预算 · 一人项目/韩元<input id="skin-budget" type="number" min="0" step="10000" value="0"></label><label>首尔 4 晚房费 · 两人/人民币<input id="kr-hotel-budget" type="number" min="0" step="100" value="0"></label><p class="muted">汇率为方便比较的<b>可编辑假设</b>，不是实时汇率或刷卡结算价。首尔房费和项目填 0 代表尚未计入，不代表免费。修改汇率会同步更新全页金额括号和预算表；保留到本次刷新前。下载文件按初始假设换算，人民币四舍五入到元。</p></div><div class="budget-results" aria-live="polite"><div class="panel"><span class="micro" id="budget-label">两人 / 基础规划</span><strong id="budget-total">—</strong><small>人民币折算范围（含上方填写项目）</small></div><div class="panel"><span class="micro">再加 15% 机动金</span><strong id="budget-buffer">—</strong><small>节日涨价、出租车与临时调整余量</small></div></div><div class="table-scroll panel"><table id="budget-table"><thead><tr><th>支出类别</th><th>原币合计 · 两人</th><th id="budget-column">人民币 / 两人</th></tr></thead><tbody></tbody></table></div><p class="muted">美发填写两人总额；皮肤填写你一人的项目金额。“人均”将旅行总额除以二，仅用于分摊。首尔实际房费填入后立即重算。</p></section>

<section id="ready"><div class="section-title"><div><span class="eyebrow">08 / BEFORE YOU GO</span><h2>临出发，只看这一页。</h2></div><span id="check-progress" class="pill">0 项完成</span></div><div class="ready-grid"><div class="panel checklist">@@CHECKS@@<small>勾选仅保存在本设备的浏览器中；隐私模式或 file:// 限制时可能不保存。</small></div><aside class="panel practical"><h3>几条会真的用上的信息</h3><p><b>入境：</b>你们已说明护照北京签发、日韩多年签；请自查两次入韩日期均在签证有效期内、签注为多次，以及各次停留条件。日本 <a href="https://www.digital.go.jp/en/policies/visit_japan_web" target="_blank" rel="noopener">Visit Japan Web</a> 是入境／海关手续工具，不代替签证。</p><p><b>导航：</b>韩国优先 NAVER Map，配 Papago 和韩文地址；日本可用 Google Maps。重要订单离线截图。</p><p><b>机场：</b>福冈地铁在国内线，往国际线要留接驳时间；本攻略跨国航班按起飞前约 3 小时抵达目标航站楼规划。@@AIRPORT@@</p><p><b>天气：</b>不把季节均值当预报。每日出门查降雨；9/26–10/5 的详细天气临行再看。遇强降雨或交通停运，取消远郊，保住航班与住宿。</p><p><b>紧急：</b>韩国、日本报警 110/112 各不相同：韩国报警 112，日本报警 110；两地急救与消防均 119。出发前保存保险援助电话与酒店地址。</p><p><b>返程：</b>威海间隔 8 小时 40 分，不默认行李直挂；10/6 01:10 才到南京，把接送安排到正确日期。</p></aside></div></section>
<section id="sources"><details class="sources panel"><summary>核验记录、来源与使用边界</summary><p>核验日期：2026-09-23。航班来自你提供的截图；价格范围、步行量、交通门到门时间是规划估计，非实时可售报价。没有替你订票、订房、联系商家、预约项目或导入 Google 账户。地图点位不含个人医疗诉求。</p><ol>@@SOURCES@@</ol><p>视觉沿用你提供的 <a href="https://yangyaolu18-alt.github.io/nz-south-island-road-trip-2026/" target="_blank" rel="noopener">新西兰攻略</a> 的暗色、蓝紫重点色、逐日卡片与地图结构；本次仅制作个人目的地攻略。照片出处见相邻署名。底图 © OpenStreetMap contributors，Leaflet BSD-2-Clause。</p></details></section></main>
<footer><span>TWO OF US / SEOUL & NORTH KYUSHU</span><p>2026.09.26 — 10.05 · 行程可变，一起出发就好。</p><a href="content.md" download>下载文字攻略</a> · <a href="README.md" download>使用说明</a></footer><div id="toast" role="status" aria-live="polite"></div><script id="trip-data" type="application/json">@@DATA@@</script><script src="assets/leaflet.js"></script><script src="app.js"></script></body></html>'''
replacements={'BASE_RANGE':base_range,'OVERVIEW':overview,'FLIGHTS':flights,'DAYS':dayhtml,'HOTELS':hotels,'FOOD':foods,'CHECKS':checks,'SOURCES':sourcehtml,'ALLPOINTS':allpoints,'POINTCOUNT':str(pointcount),'DATA':json.dumps(D,ensure_ascii=False).replace('</','<\\/'),
 'HOLIDAY':cite(['holidays']),'MYMAPS':cite(['mymaps']),'HAIR':cite(['hair','cca']),'MEDICAL':cite(['medical','aad','darkspots','melasma']),'CLINIC':cite(['beautylounge','jfeel']),'ONSEN':cite(['musouen']),'AIRPORT':cite(['airport']),
 'DAYOPTIONS':''.join(f'<option value="{d["id"]}">D{d["id"]} · {d["date"]} {E(d["region"])} · {E(d["tag"])}</option>' for d in D['days']),
 'DAYINDEX':''.join(f'<a href="#day-{d["id"]}"><b>{d["id"]:02}</b><span>{d["date"]}</span></a>' for d in D['days'])}
for k,v in replacements.items():TEMPLATE=TEMPLATE.replace('@@'+k+'@@',v)
(ROOT/'index.html').write_text(annotate_html(TEMPLATE))

md=['# '+D['title'],D['dates']+'；2026-09-23 用户确认最终路线；具体预约待落实。','## 已确认偏好与待补充信息']+['- '+x for x in D['assumptions']]+['','## 航班（截图，当地时间）']+[' | '.join(x) for x in D['flights']]
md += ['\n## 行程复核 · '+review['checked'],review['verdict'],review['summary'],review['recommendation'],review['alternative_note'],review['date_flex'],review['rail'],review['boundary']]+['- '+s for s in review['conditions']]
md += ['\n## 日本路线取舍与 JR Pass',plan['intro'],'\n### 新旧安排比较']+[' | '.join(row) for row in plan['changes']]
md += ['\n### 目的地比较',plan['time_note']]+[' | '.join(row) for row in plan['choices']]
md += ['\n### 票价与预约（成人）']+[' | '.join(row) for row in tickets['rows']]
md += ['\n### JR Pass']+[' | '.join(row) for row in plan['rail_rows']]+[' | '.join(row) for row in plan['rail_comparison']]+plan['rail_notes']
for d in D['days']:
    md += [f"\n## D{d['id']} · {d['date']} {d['week']} · {d['title']}",'主要地区：'+d['region_detail'],d['mission'],'住宿：'+d['sleep']]
    md += ['复核：'+d['review']['verdict']+'。'+d['review']['note']]
    md += [f'- {t}｜{n}：{desc}' for t,n,desc in d['timeline']]
    md += [f'- {t}｜{places[p][1]}：{order}；{b}。{note} [导航]({google(places[p])})' for t,p,order,b,note,src in d.get('meals',[])]
    if d.get('fees'): md += ['门票与项目（每人 / 两人 / 说明）：']+[' | '.join(row) for row in d['fees']]+[d['fee_note']]
    md += ['交通：'+d['transport'],'餐食：'+d['food'],'提前确认：'+d['booking'],'备选：'+d['fallback'],'两人费用（含福冈房费，首尔房费/项目另计）：'+totals(d)]
    md += ['逐段距离与耗时（公里为直线参考，非实际路程）：']+['- '+leg_text(l) for l in d['legs']]
    md += ['地图：'+', '.join(f'[{places[p][1]}]({google(places[p])})' for p in dict.fromkeys(d['points']))]
    md += ['来源：'+'、'.join(f'[{sources[s][1]}]({sources[s][2]})' for s in d['sources'])]
md += ['\n## 项目安排','美发优先询问 9/27 14:00，两人同时服务；剪发每人 ₩30,000–80,000，剪加烫每人 ₩120,000–250,000，为规划额度。','用户一人考虑改善暗沉，10/4 留半天面诊，光子不是默认决定。先留 ₩100,000–300,000，是否适合、恢复及翌日飞行由医生评估。Beauty Lounge 明洞官网有周日门诊信息，假期实际档期未核验；JFeel 弘大周日休诊。无预约改圣水/首尔林。','\n## 住宿']
for h in D['hotels']:md += [h['nights']+'｜'+h['place']+'｜'+h['budget'],h['reason'],h['names']]
md += ['\n## 预算',f'两人基础约人民币 {base_range} 元，已含福冈5晚实际房费 ¥58,693；首尔4晚房费、美发/皮肤、机票、购物、保险通信另计。网站可填实际首尔房费和项目额度。假设 ₩1,000≈人民币5元、JP¥100≈人民币4.8元，非实时汇率。','\n## 出发清单']+['- [ ] '+v for _,v in D['checklist']]
md += ['\n## 核验来源']+[f'- [{s[1]}]({s[2]})：{s[3]}' for s in D['sources']]
(ROOT/'content.md').write_text(annotate('\n\n'.join(md)))
(ROOT/'README.md').write_text(annotate("""# 首尔与北九州 · 两个人的秋日旅行

打开 `index.html`，按「韩国前程」「日本九州」「韩国后程」切换。
最终路线已确认：保留全部9晚酒店，福冈5晚连住；9/29天草海豚、9/30福冈恢复与美食、10/1由布院温泉、10/2太宰府半日、10/3福冈收尾飞首尔。阿苏已从每日地图和预算移除。D3和D8展示两端跨国接驳。

## 通票与预算

推荐北部九州3日券，9/29–10/1，官网线上成人JP¥14,000，两人JP¥28,000，仅在9/29计一次。每人四次铁路指定席，免费六次额度足够，余位须另确认。
官网网络票参考：博多—熊本往返每人JP¥10,620，加博多—由布院往返JP¥11,200，共JP¥21,820。3日券每人省JP¥7,820；若另付由布院之森提前网约两程每人JP¥3,000，仍省JP¥4,820。实际早特、余位或渠道可能改变报价。
网约由布院之森两人往返JP¥6,000只计入上限；若连新干线两程也提前网约，两人再加JP¥4,000未计入主预算。现场在免费次数内划位不收网约费，但不保证有位。
西铁、地铁、天草巴士、海豚船、温泉与景点均另付。10/2西铁和10/3机场地铁不在JR范围内，无需升级5日券。

福冈房费JP¥58,693已计入；首尔4晚房费未知，可在网页预算填写。机票、购物、美发/皮肤、保险通信另计；若福冈住宿税未含，两人五晚再留JP¥2,000。餐厅额度属于每日餐饮，不重复计入。
韩元和日元后均附人民币参考，默认每千韩元＝人民币5元、每百日元＝人民币4.8元，非实时汇率。网页可改；导出使用默认汇率。

## 仍需本人落实

- 9/28博多先领取通票，9/29起用；窗口07:00–22:00。两人护照、兑换凭证及购买渠道要求的付款实体卡随身携带。
- 9/29海豚船13:00、12:40前取票。网购成人JP¥5,400，巴士成人往返JP¥3,740；巴士非预约制，留排队余量。
- 9/30 18:00濵田屋くうてん鸡锅建议预约。
- 10/1由布院往返指定席及梦想园营业：入浴每人JP¥1,000，14:00截止接待。周四小男汤清扫，大男露天汤按常规开放，临时安排再问店方。
- 10/2蕎麦安武查看临时营业、带现金；九州国立博物馆可选成人JP¥700。
- 首尔9/27两人美发、10/3午夜后入住、10/4 11:30或更晚的面诊均需确认。皮肤治疗由本人面诊决定。

## 地图与导入

网页地图有分段公里、交通方式与耗时。公里是参考点间直线距离，非道路/轨道里程；耗时另按公共交通规划，非实时导航。
电脑打开 https://www.google.com/mymaps ，创建地图并导入 `exports/all-places.kml`；或按三段导入 `segment-*.kml`。CSV用Latitude/Longitude定位、Name作标题。每日 `day-01`至`day-10`也可独立导入。
手机Google Maps在“已保存/你”的“地图”查看，自定义地图不会自动变成普通收藏或逐向导航。未登录你的账户执行导入。
志贺岛、小仓/门司港、别府的 `alternative-japan-*` 仅为替换地图，不混入主路线和预算；太宰府已成为10/2主线。

## 文件

- `trip-data.json` 为数据源，运行 `python3 build.py` 重建网页、文字版、地图和下载包。
- `index.html`、`style.css`、`app.js` 为网页；`content.md` 为文字攻略。
- `exports/` 包含全程、三段、每日和替换地图的KML/UTF-8 CSV。
- 地图底图需联网；离线仍可看正文、预算和地点列表。
- 图片用于私人攻略，公开发布前核对授权。

核验日期2026-09-23。价格为官方公布参考或明确标注的规划额度；未查询实时余位、预约或付款。
"""))
# Keep the portable download in sync with generated content.
files=['index.html','style.css','app.js','trip-data.json','build.py','currency.py','content.md','README.md']
files += ['assets/'+name for name in ['fukuoka-night.jpg','kinrin.jpg','leaflet.js','leaflet.css','LEAFLET-LICENSE.txt']]
files += [str(p.relative_to(ROOT)) for p in sorted((ROOT/'exports').glob('*')) if p.suffix in ('.kml','.csv')]
with zipfile.ZipFile(ROOT/'korea-japan-trip-2026.zip','w',zipfile.ZIP_DEFLATED) as archive:
    for file in files:archive.write(ROOT/file,file)

print(f'Built guide and {len(list((ROOT/"exports").glob("*.*")))} exports; {pointcount} places; base CNY {base_range}.')
