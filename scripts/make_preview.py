import re
s=open('index.html',encoding='utf-8').read()
def R(a,b,n=1):
    global s
    c=s.count(a); assert c==n,(c,a[:90]); s=s.replace(a,b)
# ---- head ----
R('<meta name="theme-color" content="#f6f5f0">','''<meta name="theme-color" content="#F6F1E7">
<meta name="robots" content="noindex">
<meta name="description" content="꽃집 사장님을 위한 졸업식 꽃 판매 플래너. 우리 가게 주변 초·중·고·대학 졸업식 날짜를 한눈에 보고 준비 수량까지 적어두세요.">
<link rel="icon" type="image/png" sizes="32x32" href="favicon.png">
<link rel="apple-touch-icon" sizes="180x180" href="apple-touch-icon.png">
<meta property="og:type" content="website">
<meta property="og:url" content="https://best15993232-sudo.github.io/flower-planner/">
<meta property="og:title" content="언제 졸업해? · 꽃 판매 플래너">
<meta property="og:description" content="우리 가게 주변 졸업식 날짜를 한눈에. 전국 초·중·고·대학.">
<meta property="og:image" content="https://best15993232-sudo.github.io/flower-planner/og-image.png">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="언제 졸업해? · 꽃 판매 플래너">
<meta name="twitter:description" content="우리 가게 주변 졸업식 날짜를 한눈에. 전국 초·중·고·대학.">
<meta name="twitter:image" content="https://best15993232-sudo.github.io/flower-planner/og-image.png">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Gaegu:wght@700&display=swap">''')
R('<title>언제 졸업해? · 우리 동네 졸업식 날짜</title>','<title>[미리보기] 언제 졸업해? · 꽃 판매 플래너</title>')
# remove analytics in preview
s=re.sub(r'<!-- 방문 통계:.*?</script>\n','',s,flags=re.S)
# ---- header ----
R('''  <div class="top">
    <div class="brand">🌸 언제 졸업해?</div>
  </div>''','''  <header class="hero">
    <div class="hero-l">
      <div class="bubble"><span class="tape"></span><h1>언제 졸업해?</h1></div>
      <p class="hero-sub">꽃 판매 플래너</p>
      <p class="hero-sub2">우리 가게 주변 졸업식 날짜</p>
    </div>
    <div class="hero-r" aria-hidden="true"><div class="lace"><img src="images/freesia-header.png" alt="" onerror="this.remove()"></div></div>
  </header>''')
# ---- locbar text format ----
R("  t.textContent=name;   // 위치 줄은 '어디'만. 거리는 목록 위 '반경' 알약과 필터에서 바꿔요\n  const where=LOC.kind==='shop'?(LOC.name||LOC.addr):LOC.kind==='place'?(LOC.addr||''):LOC.addr;",
  "  const where=LOC.kind==='shop'?(LOC.name||LOC.addr):LOC.kind==='place'?(LOC.label||LOC.addr||''):LOC.addr;\n  const kinds=ALL_KINDS.every(k=>st.kinds.has(k))?'':' · '+ALL_KINDS.filter(k=>st.kinds.has(k)).join('·');\n  t.textContent=`${where||name} 주변 ${RADIUS}km${kinds}`;   // 미리보기: '태전동 주변 2km · 고등학교' 한 줄")
R("  sub.textContent=where?`${where} 주변 · 반경 ${RADIUS}km`:st.list.length?`반경 ${RADIUS}km 안 ${st.list.length.toLocaleString('ko-KR')}곳`:`반경 ${RADIUS}km`;",
  "  sub.textContent=where?name:'';")
# ---- dday: no English ----
R("return n<0?['지남',true]:n===0?['오늘',false]:['D-'+n,n>14]}","return n<0?['지남',true]:n===0?['오늘',false]:[n+'일 남음',n>14]}")
# ---- school row ----
a=s.index('function cardHtml(s){');b=s.index('function render(reset=true){')
s=s[:a]+r'''const WD=['일요일','월요일','화요일','수요일','목요일','금요일','토요일'];
function cardHtml(s){
  const ok=isOk(s),[label,tone]=stText(s);
  let dateCol,badge,btn;
  if(ok){
    const d=s.dates[0],dt=new Date(+d.slice(0,4),+d.slice(4,6)-1,+d.slice(6,8)),[dd,far]=dday(d),on=!!find(s.id,d);
    dateCol=`<div class="dcol"><span class="dm">${+d.slice(4,6)}월</span><b class="dd2">${+d.slice(6,8)}</b><span class="dw">${WD[dt.getDay()]}</span></div>`;
    badge=`<span class="bdg ${far?'':'soon'}">${dd}</span>${suspect(s)?'<span class="bdg dash">날짜 확인 필요</span>':''}`;
    btn=`<button class="add ${on?'done':''}" data-add="${esc(s.id)}" aria-pressed="${on}">${on?'✓ 담음':'+ 담기'}</button>`;
  }else{
    const n=anySaved(s.id).length;
    dateCol=`<div class="dcol none"><span class="dm">&nbsp;</span><b class="dd2">?</b><span class="dw">미정</span></div>`;
    badge=`<span class="bdg dash">날짜 확인 필요</span>`;
    btn=`<button class="add ${n?'done':''}" data-open="${esc(s.id)}">${n?'✓ 담음':'날짜 입력'}</button>`;
  }
  const km=LOC?dist.get(s.id):null;
  const meta=[km!=null?kmText(km):'',s.size&&s.size.grads?`졸업생 ${s.size.grads.toLocaleString('ko-KR')}명`:''].filter(Boolean).join(' · ');
  return `<article class="card row" data-card="${esc(s.id)}">${dateCol}
  <div class="rmid"><div class="name">${esc(s.name)}</div><div class="rmeta">${esc(s.kind)}${meta?' · '+meta:''}</div><div class="rbdg">${badge}</div></div>${btn}</article>`;
}

'''+s[b:]
# ---- plan empty ----
R('<div class="empty"><span class="big">🌷</span>아직 담은 일정이 없어요.','<div class="empty"><img class="emptyimg" src="images/freesia-empty.png" alt="" onerror="this.remove()">아직 담은 일정이 없어요.')
# ---- css ----
css=r"""
/* ===== 미리보기: 빈티지 압화 다꾸 (꽃시세 사이트와 같은 계열) ===== */
:root{--bg:#F6F1E7;--card:#FFFFFF;--paper:#FFFDF8;--line:#E2D7C5;--dot:#D9CEBD;--ink:#3A3128;--ink2:#8C7B66;--ink3:#9A8B78;
 --kraft:#C9A77C;--kraft-ink:#3A2A1A;--tape:rgba(232,214,170,.75);--yellow:#F6DE9B;--yellow-ink:#7A5410;--beige:#EFE7DA;
 --brand:#3A3128;--brand-d:#2a231c;--brand-soft:#EFE7DA;--rose:#3A3128;--rose-soft:#EFE7DA;--amber:#7A5410;--amber-soft:#F6DE9B;--muted:#F3ECE0}
body{background:var(--bg);color:var(--ink)}
/* 제목 영역 */
.hero{display:flex;align-items:flex-start;justify-content:space-between;gap:10px;padding:18px 0 12px;min-height:150px;max-height:170px}
.hero-l{padding-top:6px}
.bubble{position:relative;display:inline-block;background:var(--kraft);color:var(--kraft-ink);padding:8px 18px 10px;border-radius:14px 14px 14px 4px;transform:rotate(-2.5deg);box-shadow:0 1px 0 #00000014}
.bubble::after{content:"";position:absolute;left:14px;bottom:-9px;border:9px solid transparent;border-top-color:var(--kraft);border-bottom:0;border-left:0}
.bubble h1{margin:0;font-family:Gaegu,cursive;font-weight:700;font-size:30px;line-height:1.15;letter-spacing:0}
.tape{position:absolute;top:-9px;right:-14px;width:52px;height:18px;background:var(--tape);transform:rotate(18deg);box-shadow:0 1px 1px #0000000d}
.hero-sub{margin:16px 0 0;font-size:15px;font-weight:700;color:var(--ink)}
.hero-sub2{margin:2px 0 0;font-size:12.5px;color:var(--ink2)}
.hero-r{flex:none;width:120px;height:140px}
.lace{width:100%;height:100%;border-radius:8px;background:radial-gradient(circle at 8px 8px,#fff 3px,transparent 3.5px) 0 0/16px 16px,var(--paper);border:1px dashed var(--line);display:flex;align-items:center;justify-content:center;overflow:hidden}
.lace img{width:100%;height:100%;object-fit:contain;filter:drop-shadow(0 2px 3px #3a312822)}
.lace:has(img){background:none;border:0;overflow:visible}
.hero-r{width:128px;height:146px;margin-right:-6px}
/* 위치 줄 */
.locbar{background:#fff;border:1px solid var(--line);border-radius:10px;min-height:52px;padding:10px 12px}
.locbar b{font-size:15px}
.locbar .loc-ch{background:none;color:var(--ink);text-decoration:underline;text-underline-offset:3px;padding:4px 2px;font-weight:600}
#locIc{color:var(--ink2)}
.btn,.btn.loc-cta,#locate,#fapply{background:var(--ink);color:#fff;border-radius:10px}
.btn.line{background:#fff;color:var(--ink);border:1.5px solid var(--ink)}
.search input,.placebox input,.dinput,.memo{background:#fff;border-color:var(--line);border-radius:10px}
.sticky{background:var(--bg)}
/* 칩·알약: 둥글기 8px */
.chip,.chip-select select,.fbtn,.pillrow button,.range-pills button,.achip,.viewseg,.viewseg button,.seg,.seg button,.need .pills button,.badge,.tag,.pill,.sus,.evl,.same,.rchip,.pricelink{border-radius:8px}
.fbtn,.pillrow button,.range-pills button,.chip-select select{background:#fff;border-color:var(--line)}
.viewseg,.seg{background:var(--beige)}
.achip,.pill,.tag,.badge,.loc-ch{background:var(--beige);color:var(--ink)}
/* 학교 목록: 카드 대신 점선 줄 */
.list{background:var(--paper);border:1px solid var(--line);border-radius:10px;padding:0 14px}
.list:has(.sk){background:none;border:0;padding:0}
.card.row{display:grid;grid-template-columns:52px minmax(0,1fr) auto;gap:12px;align-items:center;background:none;border:0;border-bottom:1px dashed var(--dot);border-radius:0;padding:14px 0;box-shadow:none}
.card.row:last-child{border-bottom:0}
.card.row:hover{box-shadow:none}
.dcol{display:flex;flex-direction:column;align-items:center;line-height:1.1;color:var(--ink)}
.dcol .dm,.dcol .dw{font-size:11.5px;color:var(--ink2)}
.dcol .dd2{font-size:26px;font-weight:700;margin:2px 0}
.dcol.none .dd2{color:var(--ink3)}
.rmid{min-width:0}
.rmid .name{font-size:16px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.rmeta{font-size:12.5px;color:var(--ink2);margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.rbdg{display:flex;gap:5px;flex-wrap:wrap;margin-top:6px}
.bdg{font-size:11.5px;font-weight:700;padding:2px 8px;border-radius:6px;background:var(--beige);color:var(--ink)}
.bdg.soon{background:var(--yellow);color:var(--yellow-ink)}
.bdg.dash{background:none;border:1px dashed var(--ink3);color:var(--ink2);font-weight:600}
.card.row .add{height:40px;min-width:76px;padding:0 12px;border-radius:8px;background:#fff;color:var(--ink);border:1.5px solid var(--ink);font-size:14px}
.card.row .add.done{background:var(--ink);color:#fff;border-color:var(--ink)}
.card.row .add.alt{border-style:dashed}
#mapcard .card.row{background:#fff;border:1px solid var(--line);border-radius:10px;padding:12px}
.promo{background:#fff;border:1px dashed var(--line);border-radius:10px;margin:8px 0}
/* 내 일정 */
.scard,.plansum,.backup{background:#fff;border-color:var(--line);border-radius:10px}
.need{background:var(--ink);border-radius:10px}
.need .pills button[aria-pressed=true]{background:var(--yellow);color:var(--yellow-ink)}
.group h3 small,.group h3 small.far,.c-date .dd{color:var(--ink2)}
.emptyimg{display:block;height:130px;width:auto;margin:0 auto 12px;filter:drop-shadow(0 2px 3px #3a312822)}
/* 시트 */
.sheet{background:var(--paper)}
.links a,.links button{background:#fff;border:1px solid var(--line);border-radius:10px}
.links button[aria-pressed=true]{background:var(--ink);color:#fff}
/* 하단 탭 */
.tabbar{background:#FFFDF8;backdrop-filter:none;-webkit-backdrop-filter:none;border-top:1px solid var(--line)}
.tabbar button,.tabbar .tab-shop{color:var(--ink3);font-weight:500}
.tabbar button[aria-selected=true]{color:var(--ink);font-weight:700}
#dot{background:var(--yellow);color:var(--yellow-ink)}
.toast{background:var(--ink)}
.toast button{color:var(--yellow)}
.card.row .dcol{grid-column:1;grid-row:1}
.card.row .rmid{grid-column:2;grid-row:1}
.card.row > .add{grid-column:3;grid-row:1;align-self:center;width:auto;margin:0}
"""
R("</style>",css+"</style>")
open('preview.html','w',encoding='utf-8').write(s)
print('ok')
