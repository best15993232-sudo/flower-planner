"""지역별 졸업식 페이지(검색용 글자 페이지)를 만들어요.

만드는 것
- area/index.html        전국 요약
- area/<시도코드>.html    시·도 (예: area/41.html 경기도)
- area/<시군구코드>.html  시·군·구 (예: area/41135.html 성남시 분당구)
- qna.html               자주 묻는 질문

원칙 (docs/seo-plan-20261120.md)
- 화면을 연 뒤 채우는 방식이 아니라, HTML 안에 학교명·날짜가 처음부터 글자로 들어 있어요.
- 같은 자료면 같은 파일이 나와요(정렬·숫자 표기 고정, 만든 시각을 본문에 넣지 않음).
- '마지막 변경일'은 그 페이지 내용이 실제로 바뀐 날만 바꿔요(area/pages.json 에 기록).
- 검사에 걸리면 아무 파일도 쓰지 않고 멈춰요(이전 정상 페이지 유지).
- 날짜 확인 학교가 MIN_DATED 곳 이상인 시·군·구만 따로 페이지를 만들어요.

쓰는 법
  python3 scripts/build_area_pages.py                 # 전부
  python3 scripts/build_area_pages.py --only 41,41135 # 시안: 전국 + 경기도 + 분당구 + Q&A
"""
import argparse, hashlib, html, json, os, sys, urllib.parse
from collections import Counter, defaultdict
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda *p: os.path.join(ROOT, *p)
BASE = "https://best15993232-sudo.github.io/flower-planner/"
MIN_DATED = 5          # 사용자 결정 (2026-11-20): 날짜 확인 학교 5곳 이상이면 시·군·구 페이지 발행
MAX_DROP = 0.2         # 지난번보다 학교 수가 20% 넘게 줄면 멈춤

SIDO = {  # 코드: (페이지에 쓰는 이름, 짧은 이름)
    "11": ("서울특별시", "서울"), "26": ("부산광역시", "부산"), "27": ("대구광역시", "대구"),
    "28": ("인천광역시", "인천"), "30": ("대전광역시", "대전"), "31": ("울산광역시", "울산"),
    "36": ("세종특별자치시", "세종"), "41": ("경기도", "경기"), "43": ("충청북도", "충북"),
    "44": ("충청남도", "충남"), "47": ("경상북도", "경북"), "48": ("경상남도", "경남"),
    "50": ("제주특별자치도", "제주"), "51": ("강원특별자치도", "강원"), "52": ("전북특별자치도", "전북"),
    "12": ("전남광주통합특별시", "전남광주"),
}
KINDS = [("초등학교", "초등학교"), ("중학교", "중학교"), ("고등학교", "고등학교"), ("대학", "대학교 학위수여식")]
DOW = "월화수목금토일"
esc = lambda s: html.escape(str(s), quote=True)


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def kind_of(p):
    return "대학" if p["type"] == "campus" else p["kind"]


def md(d):      # 20261230 → 12월 30일 (수)
    x = date(int(d[:4]), int(d[4:6]), int(d[6:]))
    return f"{x.month}월 {x.day}일 ({DOW[x.weekday()]})"


def mds(d):     # 표 안 짧은 날짜: 12/30(수)
    x = date(int(d[:4]), int(d[4:6]), int(d[6:]))
    return f"{x.month}/{x.day}({DOW[x.weekday()]})"


def num(n):
    return f"{n:,}"


# ---------------------------------------------------------------- 자료 모으기
def collect():
    places = load(D("data", "places.json"))["places"]
    evs = load(D("data", "events.json"))
    ev = {e["place"]: e for e in evs["events"] if e.get("type") == "graduation"}
    regions = load(D("data", "place_regions.json"))["regions"]
    names = {}      # 시군구 코드 → 이름 (주소 기준 이름 우선)
    schools = []
    for p in places:
        r = regions.get(p["id"])
        if not r: continue
        code = r[0]
        if r[3].startswith("a") or code not in names: names[code] = r[2]
        e = ev.get(p["id"], {})
        d = e.get("date")
        src = (e.get("source") or {}).get("kind")
        s = {"id": p["id"], "name": p["name"], "kind": kind_of(p), "code": code, "date": d,
             "notice": src == "school_notice", "univ_ok": src == "school_page" and bool(d),
             "grads": ((p.get("size") or {}).get("grads")), "status": e.get("status") or "not_queried",
             "suspect": False}
        if d and src == "neis":      # 사이트와 같은 기준의 '날짜 확인 필요' 표시
            w = e.get("winterStart")
            if d < "20261205": s["suspect"] = True
            elif w and (date(int(w[:4]), int(w[4:6]), int(w[6:])) - date(int(d[:4]), int(d[4:6]), int(d[6:]))).days >= 10:
                s["suspect"] = True
        schools.append(s)
    return schools, names, evs.get("updatedAt") or ""


def area_name(code, names):
    """시·군·구 화면 이름. 같은 이름(중구·동구…)이 여러 곳이라 시·도를 붙여요."""
    sd = code[:2]
    n = names[code]
    if sd == "36": return "세종특별자치시"
    if sd == "12": return ("광주 " if n.endswith("구") else "전남 ") + n
    return f"{SIDO[sd][1]} {n}"


def stats(rows):
    dated = [r for r in rows if r["date"]]
    days = Counter(r["date"] for r in dated)
    top = sorted(days.items(), key=lambda x: (-x[1], x[0]))[:3]
    months = Counter(r["date"][:6] for r in dated)
    return {"total": len(rows), "dated": len(dated), "undated": len(rows) - len(dated),
            "top": top, "days": sorted(days.items()), "months": sorted(months.items())}


# ---------------------------------------------------------------- 화면 조각
CSS = """
:root{--bg:#F6F1E7;--card:#fff;--line:#E2D7C5;--ink:#3A3128;--ink2:#8C7B66;--ink3:#9A8B78;--brand:#7A5A34;--brand-soft:#F1E6D3;
--kraft:#C9A77C;--kraft-ink:#3A2A1A;--yellow:#F6DE9B;--yellow-ink:#7A5410;--beige:#EFE7DA;--muted:#F3ECE0}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font-family:Pretendard,"Apple SD Gothic Neo","Malgun Gothic",system-ui,sans-serif;font-size:15px;line-height:1.6;letter-spacing:-.2px}
main{max-width:680px;margin:0 auto;padding:16px 16px 56px}
a{color:var(--brand)}
.logo{display:inline-block;background:var(--kraft);color:var(--kraft-ink);padding:4px 12px 6px;border-radius:12px 12px 12px 4px;font-family:Gaegu,cursive;font-weight:700;font-size:20px;text-decoration:none;transform:rotate(-2deg)}
.crumb{font-size:13px;color:var(--ink2);margin:14px 0 4px}
.crumb a{color:var(--ink2)}
h1{font-size:22px;line-height:1.35;margin:4px 0 6px;letter-spacing:-.6px}
h2{font-size:17px;margin:30px 0 8px}
.lead{margin:0;color:var(--ink2);font-size:14px}
.box{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px;margin:14px 0}
.nums{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;text-align:center}
.nums b{display:block;font-size:20px}
.nums span{font-size:12px;color:var(--ink2)}
.top{margin:12px 0 0;font-size:14px}
.small{font-size:12.5px;color:var(--ink2)}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden;font-size:14px}
th,td{padding:9px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{background:var(--beige);font-size:12.5px;color:var(--ink2);font-weight:700}
tr:last-child td{border-bottom:0}
td.n,th.n{text-align:right;white-space:nowrap}
td.d{white-space:nowrap}
td.k{white-space:nowrap}
table.sum{font-size:13.5px}
table.sum th,table.sum td{padding:9px 7px}
.tag{display:inline-block;font-size:11px;font-weight:700;padding:1px 6px;border-radius:5px;background:var(--yellow);color:var(--yellow-ink);margin-left:4px;white-space:nowrap}
.tag.g{background:var(--muted);color:var(--ink2)}
.undec{color:var(--ink2)}
.cta{display:block;margin:22px 0 0;padding:14px;border-radius:14px;background:var(--brand);color:#fff;text-align:center;font-weight:700;text-decoration:none}
.links{display:flex;flex-wrap:wrap;gap:6px 12px;font-size:14px;margin:6px 0 0}
.foot{font-size:12px;color:var(--ink3);line-height:1.7;margin:30px 0 0}
dl.qa dt{font-weight:700;margin:22px 0 4px}
dl.qa dd{margin:0;color:var(--ink)}
"""


def page(path, title, desc, crumbs, body, changed):
    """crumbs: [(이름, 상대주소 또는 None)] 마지막이 현재 페이지."""
    depth = path.count("/")
    up = "../" * depth
    url = BASE + (path[:-len("index.html")] if path.endswith("index.html") else path)
    crumb_html = " › ".join(f'<a href="{esc(h)}">{esc(n)}</a>' if h else f"<span>{esc(n)}</span>" for n, h in crumbs)
    ld = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n,
         "item": urllib.parse.urljoin(url, h) if h else url} for i, (n, h) in enumerate(crumbs)]}
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{esc(url)}">
<meta property="og:type" content="website">
<meta property="og:url" content="{esc(url)}">
<meta property="og:site_name" content="꽃집을 위한 사이트">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:image" content="{BASE}og-image.jpg">
<meta name="theme-color" content="#F6F1E7">
<link rel="icon" type="image/png" sizes="32x32" href="{up}favicon.png">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Gaegu:wght@700&display=swap">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
<style>{CSS}</style>
</head>
<body>
<main>
<a class="logo" href="{up}">언제 졸업해?</a>
<nav class="crumb" aria-label="위치">{crumb_html}</nav>
{body}
<a class="cta" href="{up}">우리 가게 주변 학교로 보기 →</a>
<p class="foot">출처: 나이스 학사일정(교육부), 대학 학위수여식은 각 학교 공식 학사일정 페이지, 졸업생 수는 교육부 학교알리미 2026년 공시. 졸업식 날짜는 학교 사정으로 바뀔 수 있어요. 꼭 학교 공지로 확인하세요. <a href="{up}qna.html">자주 묻는 질문</a> · <a href="{up}privacy.html">개인정보처리방침·이용약관</a><br>마지막 변경일 {esc(changed)}</p>
</main>
<script defer src="https://static.cloudflareinsights.com/beacon.min.js" data-cf-beacon='{{"token": "8be9a26d6f3f4182aff85b28dbce6b00"}}'></script>
</body>
</html>
"""


def summary_box(st, what="학교"):
    top = ", ".join(f"<b>{md(d)}</b> {num(n)}곳" for d, n in st["top"]) or "아직 없음"
    return f"""<div class="box"><div class="nums">
<div><b>{num(st['total'])}</b><span>전체 {what}</span></div>
<div><b>{num(st['dated'])}</b><span>날짜 확인</span></div>
<div><b>{num(st['undated'])}</b><span>아직 미정</span></div></div>
<p class="top">가장 많은 날: {top}</p>
<p class="small" style="margin:4px 0 0">가장 많은 날은 날짜가 확인된 학교만 센 값이에요.</p></div>"""


def month_line(st):
    return " · ".join(f"{int(m[4:])}월 {num(n)}곳" for m, n in st["months"])


def school_rows(rows, up):
    out = []
    for r in sorted(rows, key=lambda r: (r["date"] or "99999999", r["name"], r["id"])):
        link = f'{up}?s={urllib.parse.quote(r["id"], safe="")}'
        if r["date"]:
            tags = ""
            if r["notice"]: tags += '<span class="tag">학교 공지 확인</span>'
            if r["univ_ok"]: tags += '<span class="tag g">학교 일정 확인</span>'
            if r["suspect"]: tags += '<span class="tag g">날짜 확인 필요</span>'
            d = f"{md(r['date'])}{tags}"
        else:
            d = '<span class="undec">아직 미정</span>'
        g = num(r["grads"]) if r["grads"] else "-"
        out.append(f'<tr><td><a href="{esc(link)}">{esc(r["name"])}</a></td><td class="d">{d}</td><td class="n">{g}</td></tr>')
    return "\n".join(out)


def kind_tables(rows, up):
    parts = []
    by = defaultdict(list)
    for r in rows: by[r["kind"]].append(r)
    for k, label in KINDS:
        rs = by.get(k)
        if not rs: continue
        st = stats(rs)
        head = "학위수여식" if k == "대학" else "졸업식"
        note = ('<p class="small">대학은 학교 공식 학사일정 페이지에서 확인한 날짜만 넣어요. 캠퍼스·단과대별로 다를 수 있어요.</p>'
                if k == "대학" else "")
        parts.append(f"""<h2>{label} {num(st['total'])}곳 <span class="small">(날짜 확인 {num(st['dated'])}곳)</span></h2>{note}
<table><thead><tr><th>학교</th><th>{head}</th><th class="n">졸업생</th></tr></thead><tbody>
{school_rows(rs, up)}
</tbody></table>""")
    return "\n".join(parts)


# ---------------------------------------------------------------- 페이지 3종 + Q&A
def build(schools, names, only):
    pages = {}
    by_code = defaultdict(list)
    for s in schools: by_code[s["code"]].append(s)
    sidos = defaultdict(list)
    for c in by_code: sidos[c[:2]].append(c)
    published = {c for c, rs in by_code.items() if stats(rs)["dated"] >= MIN_DATED}
    sido_page = {sd: ("area/36110.html" if sd == "36" else f"area/{sd}.html") for sd in sidos}   # 세종은 시·군·구가 하나라 바로 연결
    want = lambda p: only is None or p in only
    if only is not None:   # 시안: 만드는 페이지에만 링크를 걸어요(없는 페이지로 가는 링크 금지)
        published = {c for c in published if f"area/{c}.html" in only}
        sido_page = {sd: p for sd, p in sido_page.items() if p in only}
    def rel(frm, to):     # 상대 주소. index.html 은 폴더 주소로 (canonical 과 같게)
        r = os.path.relpath(D(to), os.path.dirname(D(frm))).replace(os.sep, "/")
        if r == "index.html": return "./"
        return r[:-len("index.html")] if r.endswith("/index.html") else r
    ord_sido = sorted(sidos, key=lambda sd: list(SIDO).index(sd))

    # 전국
    st = stats(schools)
    p = "area/index.html"
    rows = []
    for sd in ord_sido:
        rs = [s for c in sidos[sd] for s in by_code[c]]
        t = stats(rs)
        nm = esc(SIDO[sd][0])
        link = f'<a href="{rel(p, sido_page[sd])}">{nm}</a>' if sd in sido_page else nm
        top = f"{mds(t['top'][0][0])} {num(t['top'][0][1])}곳" if t["top"] else "-"
        rows.append(f'<tr><td class="k">{link}</td><td class="n">{num(t["total"])}</td><td class="n">{num(t["dated"])}</td><td>{top}</td></tr>')
    kinds = []
    for k, label in KINDS:
        t = stats([s for s in schools if s["kind"] == k])
        top = f"{mds(t['top'][0][0])} {num(t['top'][0][1])}곳" if t["top"] else "-"
        kinds.append(f'<tr><td class="k">{label}</td><td class="n">{num(t["total"])}</td><td class="n">{num(t["dated"])}</td><td>{top}</td></tr>')
    body = f"""<h1>2027 졸업식 날짜, 전국 학교 한눈에</h1>
<p class="lead">2026학년도 초·중·고 졸업식과 대학 학위수여식(2026년 12월~2027년 2월) 날짜를 시·도, 시·군·구별로 모았어요.</p>
{summary_box(st)}
<p class="small">달마다 졸업식 수: {month_line(st)}</p>
<h2>학교급별 졸업식</h2>
<table class="sum"><thead><tr><th>학교급</th><th class="n">전체</th><th class="n">날짜 확인</th><th>가장 많은 날</th></tr></thead><tbody>
{chr(10).join(kinds)}
</tbody></table>
<h2>시·도별 졸업식 날짜</h2>
<table class="sum"><thead><tr><th>시·도</th><th class="n">학교</th><th class="n">날짜 확인</th><th>가장 많은 날</th></tr></thead><tbody>
{chr(10).join(rows)}
</tbody></table>"""
    tops = ", ".join(f"{md(d)} {num(n)}곳" for d, n in st["top"][:2])
    pages[p] = ("2027 졸업식 날짜 · 전국 초·중·고·대학 졸업식 일정 | 언제 졸업해?",
                f"전국 {num(st['total'])}개 학교의 2027 졸업식 날짜. 날짜 확인 {num(st['dated'])}곳, 가장 많은 날 {tops}. 시·도와 시·군·구별로 찾아보세요.",
                [("전국", None)], body)

    # 시·도
    for sd in ord_sido:
        if sd == "36": continue
        p = f"area/{sd}.html"
        if not want(p): continue
        full = SIDO[sd][0]
        rs = [s for c in sidos[sd] for s in by_code[c]]
        t = stats(rs)
        rows = []
        for c in sorted(sidos[sd], key=lambda c: names[c]):
            u = stats(by_code[c])
            nm = esc(names[c])
            link = f'<a href="{rel(p, f"area/{c}.html")}">{nm}</a>' if c in published else nm
            top = f"{mds(u['top'][0][0])} {num(u['top'][0][1])}곳" if u["top"] else "-"
            rows.append(f'<tr><td class="k">{link}</td><td class="n">{num(u["total"])}</td><td class="n">{num(u["dated"])}</td><td>{top}</td></tr>')
        kinds = []
        for k, label in KINDS:
            u = stats([s for s in rs if s["kind"] == k])
            if not u["total"]: continue
            top = f"{mds(u['top'][0][0])} {num(u['top'][0][1])}곳" if u["top"] else "-"
            kinds.append(f'<tr><td class="k">{label}</td><td class="n">{num(u["total"])}</td><td class="n">{num(u["dated"])}</td><td>{top}</td></tr>')
        others = " ".join(f'<a href="{rel(p, sido_page[o])}">{esc(SIDO[o][1])}</a>' for o in ord_sido if o != sd and o in sido_page)
        body = f"""<h1>{esc(full)} 졸업식 날짜 2027</h1>
<p class="lead">{esc(full)} 초·중·고 졸업식과 대학 학위수여식 날짜를 시·군·구별로 모았어요.</p>
{summary_box(t)}
<p class="small">달마다 졸업식 수: {month_line(t)}</p>
<h2>학교급별</h2>
<table class="sum"><thead><tr><th>학교급</th><th class="n">전체</th><th class="n">날짜 확인</th><th>가장 많은 날</th></tr></thead><tbody>
{chr(10).join(kinds)}
</tbody></table>
<h2>시·군·구별 졸업식 날짜</h2>
<table class="sum"><thead><tr><th>시·군·구</th><th class="n">학교</th><th class="n">날짜 확인</th><th>가장 많은 날</th></tr></thead><tbody>
{chr(10).join(rows)}
</tbody></table>
{f'<h2>다른 시·도</h2><div class="links">{others}</div>' if others else ''}"""
        tops = ", ".join(f"{md(d)} {num(n)}곳" for d, n in t["top"][:2])
        pages[p] = (f"{full} 졸업식 날짜 2027 · 시·군·구별 초·중·고 졸업식 | 언제 졸업해?",
                    f"{full} {num(t['total'])}개 학교 2027 졸업식 날짜. 날짜 확인 {num(t['dated'])}곳, 가장 많은 날 {tops}.",
                    [("전국", rel(p, "area/index.html")), (full, None)], body)

    # 시·군·구
    for c in sorted(published):
        p = f"area/{c}.html"
        if not want(p): continue
        sd = c[:2]
        rs = by_code[c]
        t = stats(rs)
        an = area_name(c, names)
        h_name = an if sd != "36" else "세종특별자치시"
        crumbs = [("전국", rel(p, "area/index.html"))]
        if sd != "36": crumbs.append((SIDO[sd][0], rel(p, sido_page[sd]) if sd in sido_page else None))
        crumbs.append((names[c] if sd != "36" else "세종특별자치시", None))
        days = "".join(f'<tr><td class="d">{md(d)}</td><td class="n">{n}곳</td></tr>' for d, n in t["days"])
        sib = [o for o in sorted(sidos[sd], key=lambda o: names[o]) if o != c and o in published]
        sib_html = " ".join(f'<a href="{rel(p, f"area/{o}.html")}">{esc(names[o])}</a>' for o in sib)
        body = f"""<h1>{esc(h_name)} 졸업식 날짜 2027</h1>
<p class="lead">{esc(h_name)} 초·중·고 {num(sum(1 for r in rs if r['kind'] != '대학'))}곳의 졸업식 날짜{'와 대학 학위수여식' if any(r['kind'] == '대학' for r in rs) else ''}를 모았어요. 학교 이름을 누르면 지도·길찾기와 함께 볼 수 있고, 내 일정에 담을 수 있어요.</p>
{summary_box(t)}
<p class="small">‘졸업생’은 2026년 학교알리미 공시의 최종 학년 학생 수예요. <a href="{rel(p, 'qna.html')}#grads">무슨 뜻인가요?</a></p>
{kind_tables(rs, "../")}
<h2>날짜별 졸업식 수</h2>
<table><thead><tr><th>날짜</th><th class="n">학교 수</th></tr></thead><tbody>
{days}
</tbody></table>
{f'<h2>{esc(SIDO[sd][0])} 다른 시·군·구</h2><div class="links">{sib_html}</div>' if sib_html else ''}"""
        tops = ", ".join(f"{md(d)} {num(n)}곳" for d, n in t["top"][:2])
        pages[p] = (f"{h_name} 졸업식 날짜 2027 · 학교 {num(t['total'])}곳 | 언제 졸업해?",
                    f"{h_name} 초·중·고 졸업식·대학 학위수여식 날짜. 전체 {num(t['total'])}곳 중 날짜 확인 {num(t['dated'])}곳, 가장 많은 날 {tops}.",
                    crumbs, body)

    # Q&A
    p = "qna.html"
    body = QNA
    pages[p] = ("졸업식 날짜 자주 묻는 질문 · 언제 나오나요, 바뀌나요 | 언제 졸업해?",
                "졸업식 날짜는 어디서 가져오는지, 언제 나오는지, 바뀔 수 있는지, 졸업생 수는 무슨 뜻인지 정리했어요.",
                [("언제 졸업해?", "./"), ("자주 묻는 질문", None)], body)
    return pages


QNA = """<h1>졸업식 날짜, 자주 묻는 질문</h1>
<p class="lead">언제 졸업해?에 나오는 졸업식 날짜와 숫자가 어디서 왔는지, 어떻게 읽으면 되는지 정리했어요. 지역별 날짜는 <a href="area/">전국 졸업식 날짜</a>에서 볼 수 있어요.</p>
<dl class="qa">
<dt id="source">졸업식 날짜는 어디서 가져오나요?</dt>
<dd>초·중·고는 교육부 나이스(NEIS)에 학교가 등록한 학사일정에서 ‘졸업식’을 찾아 보여 줘요. 매일 새벽 다시 받아서 바뀐 날짜를 반영해요. 대학 학위수여식은 나이스에 없어서, 각 학교 공식 학사일정 페이지에서 직접 확인한 날짜만 넣어요.</dd>
<dt id="notice">‘학교 공지 확인’은 무엇인가요?</dt>
<dd>나이스 날짜와 다른 날짜가 학교 가정통신문·공지에 나온 경우, 운영자가 그 공지를 직접 확인하고 공지 날짜를 보여 주는 표시예요. 나이스 날짜가 공지와 같아지면 다시 나이스 표시로 돌아가요.</dd>
<dt id="undecided">‘아직 미정’인 학교는 언제 나오나요?</dt>
<dd>학교가 아직 나이스에 졸업식을 등록하지 않았거나, 날짜 후보가 여러 개라 하나로 정하지 못한 경우예요. 학교가 등록하면 다음 날 새벽 갱신 때 반영돼요. 급하면 학교 홈페이지나 가정통신문을 확인해 주세요.</dd>
<dt id="change">졸업식 날짜가 바뀌기도 하나요?</dt>
<dd>네, 학교 사정으로 바뀔 수 있어요. 나이스 날짜가 바뀌면 사이트도 바뀌고, 내 일정에 담아 둔 학교는 ‘날짜가 바뀌었어요’ 알림이 떠요. 판매 준비 전에는 학교 공지로 꼭 다시 확인해 주세요.</dd>
<dt id="suspect">‘날짜 확인 필요’는 무엇인가요?</dt>
<dd>나이스 날짜가 평소와 달라 보일 때 붙는 표시예요. 예를 들어 12월 5일보다 이른 졸업식이나, 겨울방학 시작보다 10일 넘게 앞선 졸업식이에요. 틀렸다는 뜻은 아니니 학교 공지로 확인해 주세요.</dd>
<dt id="grads">‘졸업생’ 수는 무슨 뜻인가요?</dt>
<dd>교육부 학교알리미 2026년 공시(4월 기준) ‘학년별 학생 수’의 최종 학년 학생 수예요. 초등학교는 6학년, 중·고등학교는 3학년이에요. 실제 졸업하는 인원과 조금 다를 수 있어요. 꽃다발 수량을 가늠하는 참고 숫자로 봐 주세요.</dd>
<dt id="top">‘가장 많은 날’은 어떻게 세나요?</dt>
<dd>날짜가 확인된 학교만 날짜별로 세어서 가장 많은 날을 보여 줘요. ‘아직 미정’인 학교는 세지 않아요.</dd>
<dt id="time">졸업식 시간도 알 수 있나요?</dt>
<dd>나이스 학사일정에는 시간이 없어요. 시간은 학교 공지로 확인해 주세요.</dd>
<dt id="sell">학교 앞에서 꽃을 팔아도 되나요?</dt>
<dd>목록에 있다고 해서 판매가 허용되는 장소는 아니에요. 학교 앞 도로·인도의 판매 가능 여부는 직접 확인해 주세요.</dd>
</dl>"""


# ---------------------------------------------------------------- 검사·저장
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="시안용: 만들 시·도/시·군·구 코드 (쉼표로)")
    a = ap.parse_args()
    only = None
    if a.only:
        only = {"area/index.html", "qna.html"} | {f"area/{c.strip()}.html" for c in a.only.split(",") if c.strip()}
    schools, names, data_day = collect()
    if not data_day: sys.exit("events.json 에 updatedAt 이 없어요. 멈춰요.")
    state_p = D("area", "pages.json")
    state = load(state_p) if os.path.exists(state_p) else {"total": 0, "pages": {}}
    # 검사 1: 학교 수가 갑자기 크게 줄면 멈춤
    if state.get("total") and len(schools) < state["total"] * (1 - MAX_DROP):
        sys.exit(f"학교 수가 {state['total']} → {len(schools)} 로 크게 줄었어요. 자료 받기 문제일 수 있어 멈춰요.")
    pages = build(schools, names, only)
    # 검사 2: 빈 페이지 금지
    for p, (title, desc, crumbs, body) in pages.items():
        if p.startswith("area/") and p != "area/index.html" and "<tbody>\n\n</tbody>" in body:
            sys.exit(f"{p} 에 빈 표가 있어요. 멈춰요.")
    # 쓰기: 내용(마지막 변경일 빼고)이 바뀐 페이지만 날짜를 바꾸고 다시 써요
    out, changed_n = {}, 0
    for p, (title, desc, crumbs, body) in sorted(pages.items()):
        h = hashlib.sha256((title + desc + json.dumps(crumbs, ensure_ascii=False) + body).encode()).hexdigest()[:16]
        old = state["pages"].get(p, {})
        day = old.get("changed") if old.get("hash") == h and os.path.exists(D(p)) else data_day
        out[p] = {"hash": h, "changed": day}
        txt = page(p, title, desc, crumbs, body, day)
        if not os.path.exists(D(p)) or open(D(p), encoding="utf-8").read() != txt:
            os.makedirs(os.path.dirname(D(p)) or ROOT, exist_ok=True)
            with open(D(p) + ".tmp", "w", encoding="utf-8") as f: f.write(txt)
            changed_n += 1
    for p in out:      # 모두 만든 뒤 한 번에 바꿔 끼워요
        if os.path.exists(D(p) + ".tmp"): os.replace(D(p) + ".tmp", D(p))
    keep = {k: v for k, v in state["pages"].items() if k not in out and only is not None}   # 시안 때는 다른 기록 유지
    new_state = {"about": "지역 페이지 기록(내용 지문과 마지막 변경일). scripts/build_area_pages.py 가 관리해요.",
                 "total": len(schools), "pages": dict(sorted({**keep, **out}.items()))}
    if new_state != state:
        with open(state_p, "w", encoding="utf-8") as f:
            json.dump(new_state, f, ensure_ascii=False, indent=1)
            f.write("\n")
    print(f"페이지 {len(out)}개 중 바뀐 파일 {changed_n}개")


if __name__ == "__main__":
    main()
