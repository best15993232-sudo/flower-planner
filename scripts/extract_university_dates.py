#!/usr/bin/env python3
"""대학 학사일정 페이지에서 '학위수여식' 날짜 후보를 뽑아 보고서로 만들어요. (사이트 데이터는 바꾸지 않아요)

- 주소 목록: data/university_sources.json
- robots.txt 가 막은 페이지는 가져오지 않아요.
- 날짜와 요일이 안 맞으면(오기 의심) 표시하고, 요일이 맞는 연도를 제안해요.
- PDF는 아직 자동으로 읽지 않고 '수동 확인'으로 남겨요.
- 결과: docs/reports/university-dates-YYYY-MM-DD.md

사용: python3 scripts/extract_university_dates.py [--academic-year 2026]
"""
import argparse, datetime as dt, html.parser, json, os, re, sys, urllib.request, urllib.robotparser, urllib.parse

UA = "flower-planner-bot/0.1 (+https://best15993232-sudo.github.io/flower-planner/)"
WD = "월화수목금토일"
KEYWORD = re.compile(r"학위\s*수여식|졸업식")
PREP = re.compile(r"연습|리허설|예행|준비|대여|안내")

# ── 날짜 표현 ─────────────────────────────────────────────
RE_FULL = re.compile(r"(20\d\d)\s*[.년/-]\s*(\d{1,2})\s*[.월/-]\s*(\d{1,2})\s*일?\.?\s*(?:\(\s*([월화수목금토일])\s*\))?")
RE_MD = re.compile(r"(?<![\d.])(\d{1,2})\.\s?(\d{1,2})\.?\s*(?:\(\s*([월화수목금토일])\s*\))?")
RE_DAY = re.compile(r"(?<![\d.])(\d{1,2})\s*일?\s*\(\s*([월화수목금토일])\s*\)")
RE_HEADER = re.compile(r"^\s*(?:(20\d\d)\s*[년.]\s*)?(\d{1,2})\s*(?:월|\.)\s*(?:[A-Za-z]+)?\s*$")
RE_YEAR_LINE = re.compile(r"^\W*(20\d\d)\s*(?:학년도|년)?\s*(?:\d\s*학기)?\s*(?:\W|학년도)*(?:전체일정)?$")   # '2026학년도 2학기', '◀ 2026 학년도 ▶' 같은 머리 줄


class _Text(html.parser.HTMLParser):
    BLOCK = {"br", "p", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "dt", "dd", "section", "article", "table", "ul", "ol"}

    def __init__(self):
        super().__init__(); self.out = []; self.skip = 0

    def handle_starttag(self, tag, a):
        if tag in ("script", "style", "noscript"): self.skip += 1
        elif tag in self.BLOCK: self.out.append("\n")
        elif tag in ("td", "th"): self.out.append("\t")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"): self.skip = max(0, self.skip - 1)
        elif tag in self.BLOCK: self.out.append("\n")

    def handle_data(self, d):
        if not self.skip: self.out.append(d)


def html_to_text(s):
    p = _Text(); p.feed(s); return "".join(p.out)


def _mk(y, m, d):
    try: return dt.date(y, m, d)
    except ValueError: return None


def extract(text, ay=2026):
    """글자에서 학위수여식 후보 [(date, 원문 줄, 요일 메모)]를 뽑아요."""
    lines = [l.strip() for l in text.replace("\r", "").split("\n")]
    lines = [l for l in lines if l]
    # 페이지 머리의 짧은 줄(예: '2026학년도', '2026년 2학기')에서 기준 연도를 잡아요
    ys = [int(m.group(1)) for l in lines[:60] for m in [RE_YEAR_LINE.match(l)] if m]
    base = max(ys) if ys else ay
    year = month = last_m = None
    out, recent = [], []

    def resolve(m, d, wd, explicit_y=None):
        y = explicit_y or year or (base if m >= 3 else base + 1)
        date, note = _mk(y, m, d), ""
        if date and wd and WD[date.weekday()] != wd:
            alt = [yy for yy in (y - 1, y + 1) if _mk(yy, m, d) and WD[_mk(yy, m, d).weekday()] == wd]
            note = f"요일 불일치: {y}.{m}.{d}은 {WD[date.weekday()]}요일인데 원문은 {wd}요일" + (f", {alt[0]}년이면 맞음" if alt else "")
            if alt: date = _mk(alt[0], m, d)
        return date, note

    def dates_in(line):
        res = [resolve(int(g.group(2)), int(g.group(3)), g.group(4), int(g.group(1))) for g in RE_FULL.finditer(line)]
        if res: return res
        res = [resolve(int(g.group(1)), int(g.group(2)), g.group(3)) for g in RE_MD.finditer(line)
               if 1 <= int(g.group(1)) <= 12]
        if res: return res
        return [resolve(month, int(g.group(1)), g.group(2)) for g in RE_DAY.finditer(line)] if month else []

    for raw in lines:
        head, _, rest = raw.partition("\t")
        h = RE_HEADER.match(head)
        if h and 1 <= int(h.group(2)) <= 12:          # '2027년 2월', '2월', '2027.02.' 같은 달 머리
            m = int(h.group(2))
            if h.group(1): year = int(h.group(1))
            elif year is None: year = base if m >= 3 else base + 1
            elif last_m is not None and m < last_m: year += 1    # 12월 → 1월 넘어가면 다음 해
            month, last_m = m, m
            raw = rest.strip()
            if not raw: continue
        found = dates_in(raw)
        if KEYWORD.search(raw) and not PREP.search(raw):
            for date, note in (found or recent[-1:]):    # 날짜가 같은 줄에 없으면 바로 앞 날짜 줄
                if date: out.append((date, raw, note))
        if found: recent = found
    return out


def in_season(d, ay):
    return dt.date(ay, 11, 1) <= d <= dt.date(ay + 1, 3, 31)


def allowed(url):
    try:
        rp = urllib.robotparser.RobotFileParser()
        u = urllib.parse.urlsplit(url)
        rp.set_url(f"{u.scheme}://{u.netloc}/robots.txt"); rp.read()
        return rp.can_fetch(UA, url)
    except Exception:
        return True


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    raw = urllib.request.urlopen(req, timeout=25).read()
    for enc in ("utf-8", "cp949", "euc-kr"):
        try: return raw.decode(enc)
        except UnicodeDecodeError: pass
    return raw.decode("utf-8", "replace")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--academic-year", type=int, default=2026)
    a = ap.parse_args(); ay = a.academic_year
    root = os.path.join(os.path.dirname(__file__), "..")
    src = json.load(open(os.path.join(root, "data", "university_sources.json"), encoding="utf-8"))["sources"]
    rows = []
    for s in src:
        conf = (s.get("confirmed") or {}).get("date")
        if s.get("format") == "pdf":
            rows.append((s, "수동 확인", "PDF는 아직 자동으로 읽지 않아요", [])); continue
        if not allowed(s["url"]):
            rows.append((s, "수집 금지", "robots.txt가 막고 있어요", [])); continue
        try:
            text = html_to_text(fetch(s["url"]))
        except Exception as e:
            rows.append((s, "접속 실패", type(e).__name__, [])); continue
        cands = [c for c in extract(text, ay) if in_season(c[0], ay)]
        ds = sorted({c[0].strftime("%Y%m%d") for c in cands})
        if not ds: state = "후보 없음"
        elif conf and ds == [conf]: state = "일치"
        elif conf and conf in ds: state = "후보 여러 개"
        elif conf: state = "⚠ 변경 의심"
        else: state = "새 후보"
        if any(c[2] for c in cands): state += " · 요일 확인"
        rows.append((s, state, "", cands))
    today = dt.date.today().isoformat()
    os.makedirs(os.path.join(root, "docs", "reports"), exist_ok=True)
    rp = os.path.join(root, "docs", "reports", f"university-dates-{today}.md")
    with open(rp, "w", encoding="utf-8") as f:
        f.write(f"# 대학 학위수여식 자동 점검 ({today})\n\n자동으로 뽑은 후보예요. 사이트에는 사람이 확인한 값(university_sources.json의 confirmed)만 반영돼요.\n\n")
        f.write("| 대학 | 상태 | 확인된 날짜 | 이번에 찾은 후보 (원문) |\n|---|---|---|---|\n")
        for s, state, why, cands in rows:
            conf = (s.get("confirmed") or {}).get("date", "")
            c = "<br>".join(f'{d:%Y.%m.%d} ({WD[d.weekday()]}) “{l[:40]}”' + (f" ⚠ {n}" if n else "") for d, l, n in cands) or why
            f.write(f'| [{s["name"]}]({s["url"]}) | {state} | {conf} | {c} |\n')
    print(open(rp, encoding="utf-8").read())


if __name__ == "__main__":
    main()
