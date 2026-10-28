"""기존 수집 결과(school_summary.csv + event_audit.csv)와 이 스크립트의 분류가 같은지 대조해요. (인터넷·키 불필요)
사용: python3 scripts/verify_against_audit.py school_summary.csv event_audit.csv"""
import csv, sys, os, collections
sys.path.insert(0, os.path.dirname(__file__))
from update_schools import classify, event_class, ST_NOCAL
summ = list(csv.DictReader(open(sys.argv[1], encoding="utf-8-sig")))
aud = collections.defaultdict(list)
cls_bad = 0
for r in csv.DictReader(open(sys.argv[2], encoding="utf-8-sig")):
    aud[f'{r["OfficeCode"]}:{r["SchoolCode"]}'].append({"AA_YMD": r["EventDate"], "EVENT_NM": r["EventName"]})
    if event_class(r["EventName"]) != r["Classification"]:
        cls_bad += 1
        if cls_bad <= 5: print("행사 분류 불일치:", r["EventName"], r["Classification"], event_class(r["EventName"]))
bad = 0
for r in summ:
    sid = f'{r["OfficeCode"]}:{r["SchoolCode"]}'
    st, dates, _, _ = classify(aud.get(sid, []), no_data=(r["Result"] == ST_NOCAL))
    exp = r["GraduationDates"].split(";") if r["GraduationDates"] else []
    if (st, dates) != (r["Result"], exp):
        bad += 1
        if bad <= 10: print("학교 불일치:", r["School"], r["Result"], exp, "→", st, dates)
print(f"행사 분류 불일치 {cls_bad}건 / 학교 {len(summ)}곳 중 불일치 {bad}곳")
sys.exit(1 if (bad or cls_bad) else 0)
