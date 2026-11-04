// 공유 미리보기(og.png)와 홈 화면 아이콘(icons/*.png)을 그려 PNG로 저장해요.
// 실행: 저장소 폴더에서  node scripts/make_share_images.js   (Playwright 필요)
// 그림은 모두 이 파일 안의 도형으로 직접 그려요(사진·다른 회사 로고 없음).
const { chromium } = require('playwright');
const path = require('path');
const ROOT = path.join(__dirname, '..');

const C = { bg:'#f6f5f0', card:'#fff', ink:'#1d2b24', ink2:'#5d6d63', ink3:'#8a978e', line:'#e6e9e2',
  brand:'#1f5a43', brandSoft:'#e8f2ec', rose:'#c4486b', roseSoft:'#fbeaf0', amber:'#e7b13a' };

// 다섯 장 꽃잎 꽃(🌸 느낌). size = 지름 비율용 viewBox 100
function flower(petal = C.rose, inner = '#e98aa6', center = C.amber) {
  const p = [0, 72, 144, 216, 288].map(a =>
    `<g transform="rotate(${a} 50 50)"><path d="M50 50 C36 38 34 14 50 8 C66 14 64 38 50 50Z" fill="${petal}"/>` +
    `<path d="M50 44 C44 36 44 22 50 17 C56 22 56 36 50 44Z" fill="${inner}" opacity=".55"/></g>`).join('');
  return `<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">${p}<circle cx="50" cy="50" r="9" fill="${center}"/>` +
    `<circle cx="50" cy="50" r="4" fill="#fff" opacity=".5"/></svg>`;
}

// 글꼴: 인터넷에서 Pretendard 를 받아 와요. 막혀 있으면 PRETENDARD_DIR(woff2 폴더)을 지정하세요
//   예) npm pack pretendard@1.3.9 && tar xzf pretendard-1.3.9.tgz
//       PRETENDARD_DIR=package/dist/web/static/woff2 node scripts/make_share_images.js
const fs = require('fs');
function fontCss() {
  const dir = process.env.PRETENDARD_DIR;
  if (!dir) return '<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css">';
  return '<style>' + [['Regular', 400], ['Medium', 500], ['Bold', 700]].map(([n, w]) =>
    `@font-face{font-family:Pretendard;font-weight:${w};src:url(data:font/woff2;base64,${fs.readFileSync(path.join(dir, `Pretendard-${n}.woff2`)).toString('base64')}) format("woff2")}`).join('') + '</style>';
}
const FONT = `${fontCss()}
<style>*{box-sizing:border-box;margin:0}body{font-family:Pretendard,"WenQuanYi Zen Hei",sans-serif;letter-spacing:-.5px;word-break:keep-all}</style>`;

const OG = `<!doctype html><html><head><meta charset="utf-8">${FONT}<style>
body{width:1200px;height:630px;background:${C.bg};color:${C.ink};position:relative;overflow:hidden}
.blob{position:absolute;right:-120px;top:-140px;width:620px;height:620px;border-radius:50%;background:${C.roseSoft}}
.l{position:absolute;left:84px;top:96px;width:620px}
.logo{width:104px;height:104px}
h1{font-size:76px;font-weight:700;margin-top:34px;letter-spacing:-2.5px}
p{font-size:34px;line-height:1.45;color:${C.ink2};margin-top:20px;font-weight:500}
.pills{display:flex;gap:12px;margin-top:40px}
.pill{height:52px;padding:0 24px;border-radius:999px;background:#fff;border:2px solid ${C.line};font-size:24px;color:${C.ink2};display:flex;align-items:center;font-weight:500}
.cards{position:absolute;right:72px;top:118px;width:410px}
.c{background:#fff;border:2px solid ${C.line};border-radius:24px;padding:24px 26px;margin-bottom:18px;box-shadow:0 8px 24px #1d2b240d;display:flex;align-items:center;gap:18px}
.d{width:78px;height:78px;border-radius:18px;background:${C.bg};display:flex;flex-direction:column;align-items:center;justify-content:center;flex:none}
.d b{font-size:32px;line-height:1;font-weight:700}.d span{font-size:17px;color:${C.ink3};margin-top:4px}
.t{white-space:nowrap}.t b{display:block;font-size:24px;font-weight:700}.t span{font-size:19px;color:${C.ink3}}
.add{margin-left:auto;width:44px;height:44px;border-radius:12px;background:${C.brand};color:#fff;font-size:30px;display:flex;align-items:center;justify-content:center;flex:none;font-weight:500}
.c.off{opacity:.55}
</style></head><body><div class="blob"></div>
<div class="l"><div class="logo">${flower()}</div><h1>꽃 판매 플래너</h1>
<p>우리 동네 학교 졸업식 날짜를 한눈에.<br>담아 두고 꽃다발 수량까지 준비하세요.</p>
<div class="pills"><div class="pill">초·중·고</div><div class="pill">대학교</div><div class="pill">내 주변 순</div></div></div>
<div class="cards">
<div class="c"><div class="d"><b>2.12</b><span>목</span></div><div class="t"><b>초등학교 졸업식</b><span>1.2km · 6학년 180명</span></div><div class="add">+</div></div>
<div class="c"><div class="d"><b>2.13</b><span>금</span></div><div class="t"><b>중학교 졸업식</b><span>2.4km · 3학년 240명</span></div><div class="add">+</div></div>
<div class="c off"><div class="d"><b>2.20</b><span>금</span></div><div class="t"><b>대학 학위수여식</b><span>5.8km</span></div><div class="add">+</div></div>
</div></body></html>`;

// 아이콘: 초록 바탕(maskable 여백 고려해 꽃은 가운데 60%)
const ICON = (size, round) => `<!doctype html><html><head><meta charset="utf-8"><style>*{margin:0}
body{width:${size}px;height:${size}px;background:${round ? 'transparent' : C.brand}}
.b{width:100%;height:100%;background:${C.brand};display:flex;align-items:center;justify-content:center}
.f{width:62%;height:62%}</style></head><body><div class="b"><div class="f">${flower('#fbeaf0', '#f3b6c8', C.amber)}</div></div></body></html>`;

(async () => {
  const b = await chromium.launch();
  const shot = async (html, w, h, file) => {
    const pg = await b.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: 1 });
    await pg.setContent(html, { waitUntil: 'networkidle' }).catch(() => {});
    await pg.evaluate(() => document.fonts.ready);
    await pg.screenshot({ path: path.join(ROOT, file), omitBackground: false });
    await pg.close(); console.log('저장:', file);
  };
  await shot(OG, 1200, 630, 'og.png');
  for (const s of [192, 512]) await shot(ICON(s), s, s, `icons/icon-${s}.png`);
  await shot(ICON(180), 180, 180, 'icons/apple-touch-icon.png');
  await shot(ICON(32), 32, 32, 'icons/favicon-32.png');
  await b.close();
})();
