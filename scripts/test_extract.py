"""학사일정 원문(fixtures, 2026-10-29 각 대학 페이지에서 저장)으로 추출기를 시험해요. 인터넷 불필요."""
import os, sys, datetime as dt
sys.path.insert(0, os.path.dirname(__file__))
from extract_university_dates import extract, in_season, html_to_text
F = os.path.join(os.path.dirname(__file__), "fixtures")
cases = {"snu.txt": ["20270224"], "yonsei.txt": ["20270222"], "korea.txt": ["20270225"],
         "skku.txt": ["20270225"], "inhatc.txt": ["20270212"]}
bad = 0
for fn, want in cases.items():
    res = [r for r in extract(open(os.path.join(F, fn), encoding="utf-8").read()) if in_season(r[0], 2026)]
    got = sorted({d.strftime("%Y%m%d") for d, l, n in res})
    ok = got == want and not any(n for d, l, n in res); bad += not ok   # 날짜가 맞고, 괜한 요일 경고도 없어야 함
    print("OK " if ok else "FAIL", fn, got)
# 경북대 PDF처럼 줄 안에 (2.19.)만 있는 경우
got = extract("2026학년도 학사력\n설연휴 (2.6.~2.9.)\n2026학년도\n전기학위수여식 (2.19.)\n")
ok = [d.strftime("%Y%m%d") for d, *_ in got if in_season(d, 2026)] == ["20270219"]; bad += not ok
print("OK " if ok else "FAIL", "knu-like", [(d, n) for d, l, n in got])
# 아주대처럼 연도를 잘못 적은 경우 → 요일로 바로잡고 메모
got = extract("2026학년도 2학기\n2026학년도 전기 학위수여식\t2026. 02. 13.(토)\n")
ok = len(got) == 1 and got[0][0] == dt.date(2027, 2, 13) and "요일 불일치" in got[0][2]; bad += not ok
print("OK " if ok else "FAIL", "ajou-like", got)
# HTML → 글자 변환
t = html_to_text("<table><tr><td>2월</td><td>25(목)</td><td>2026학년도 전기 학위수여식</td></tr></table><script>var x='1월';</script>")
got = [d.strftime("%Y%m%d") for d, *_ in extract(t)]
ok = got == ["20270225"]; bad += not ok
print("OK " if ok else "FAIL", "html-table", got, repr(t))
# 준비성 공지는 제외
ok = extract("2월\n24(수)\n학위수여식 예행연습\n") == []; bad += not ok
print("OK " if ok else "FAIL", "prep-excluded")
sys.exit(1 if bad else 0)
