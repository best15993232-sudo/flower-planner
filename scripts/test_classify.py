import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from update_schools import classify
R = lambda d, n: {"AA_YMD": d, "EVENT_NM": n}
d = json.load(open(os.path.join(os.path.dirname(__file__), "..", "data", "schools.json"), encoding="utf-8"))
B = {s["id"]: s for s in d["schools"]}
fails = 0
# 1) 기존 결과에 저장된 행사명 7곳을 되돌려 넣어 같은 분류가 나오는지
for sid, ev in d["rawEvents"].items():
    rows = [R(day, n) for day, ns in ev.items() for n in ns]
    st, dates, rev, _ = classify(rows)
    ok = st == B[sid]["status"] and dates == B[sid]["dates"] and rev == d["reviewDates"].get(sid, [])
    fails += not ok
    print("OK " if ok else "FAIL", B[sid]["name"], st, len(dates), len(rev))
# 2) 단순 사례
cases = [
    ([R("20270108", "졸업식"), R("20270108", "종업식")], "Graduation found in NEIS", ["20270108"]),
    ([R("20270105", "여름방학")], "Graduation not yet found", []),
    ([], "No calendar data", []),
    ([R("20270110", "졸업후 미산입일")], "Graduation not yet found", []),      # 준비/제외 행사
    ([R("20270110", "졸업식 연주회")], "Review: ambiguous event name", []),    # 공연과 섞이면 확인 필요
]
for rows, st_, dt_ in cases:
    st, dates, *_ = classify(rows, no_data=(not rows))
    ok = (st, dates) == (st_, dt_); fails += not ok
    print("OK " if ok else "FAIL", st, dates)
sys.exit(1 if fails else 0)
