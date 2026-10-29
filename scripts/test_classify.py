import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from update_schools import classify, winter_start
R = lambda d, n: {"AA_YMD": d, "EVENT_NM": n}
d = json.load(open(os.path.join(os.path.dirname(__file__), "..", "data", "schools.json"), encoding="utf-8"))
B = {s["id"]: s for s in d["schools"]}
fails = 0
# 1) 예전에는 저장된 결과를 그대로 되돌려 넣어 비교했지만, 규칙을 고치면서(졸업식 휴업·사정회) 기대값이 바뀌어
#    헷갈리는 행사명 사례는 test_event_rules.py 로 옮겼어요.
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
w = winter_start([R("20261216", "겨울방학"), R("20261217", "겨울 방학"), R("20270105", "개학")])
ok = w == "20261216"; fails += not ok
print("OK " if ok else "FAIL", "winter_start", w)
sys.exit(1 if fails else 0)
