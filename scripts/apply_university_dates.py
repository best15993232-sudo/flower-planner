#!/usr/bin/env python3
"""data/university_sources.json 의 '사람이 확인한' 학위수여식 날짜를 data/universities.json 에 반영해요."""
import json, os, sys
R = os.path.join(os.path.dirname(__file__), "..", "data")
src = json.load(open(os.path.join(R, "university_sources.json"), encoding="utf-8"))["sources"]
p = os.path.join(R, "universities.json")
d = json.load(open(p, encoding="utf-8"))
by = {(u["name"], u["campus"]): u for u in d["universities"]}
n = 0
for s in src:
    u = by.get((s["name"], s.get("campus", "본교")))
    if not u:
        print("목록에 없는 대학:", s["name"], s.get("campus")); continue
    c = s.get("confirmed")
    if c and c.get("date"):
        u["dates"] = [c["date"]]
        u["dateLabel"], u["dateChecked"], u["dateUrl"] = c.get("label", ""), c.get("checked", ""), s["url"]
        n += 1
json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(f"확인된 날짜 {n}곳 반영")
