#!/usr/bin/env python3
"""전국대학및전문대학정보표준데이터(CSV)에서 대학·전문대학 본교/캠퍼스만 골라 data/universities.json 을 만듭니다.
(대학원 단위 기관은 제외) 좌표는 geocode_universities.py 로 따로 채워요.
사용: python3 scripts/build_universities.py university.csv"""
import csv, json, sys, os

def read(path):
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "cp949"):
        try: return list(csv.DictReader(raw.decode(enc).splitlines()))
        except UnicodeDecodeError: pass
    sys.exit("CSV 인코딩을 읽지 못했어요.")

out, old = [], {}
dst = os.path.join(os.path.dirname(__file__), "..", "data", "universities.json")
if os.path.exists(dst):   # 이미 채운 좌표·졸업일은 유지
    old = {u["id"]: u for u in json.load(open(dst, encoding="utf-8"))["universities"]}
for r in read(sys.argv[1]):
    if r["대학구분명"] not in ("대학", "전문대학"): continue
    uid = "U:" + r["학교명"] + "|" + r["소재지도로명주소"]
    u = {"id": uid, "name": r["학교명"], "kind": "전문대학" if r["대학구분명"] == "전문대학" else "대학교",
         "type": r["학교구분명"], "campus": r["본분교구분명"], "region": r["시도명"], "address": r["소재지도로명주소"],
         "website": r["홈페이지주소"], "phone": r["대표전화번호"], "founded": r["설립형태구분명"],
         "dates": [], "lat": None, "lon": None}
    if uid in old:
        for k in ("lat", "lon", "dates"): u[k] = old[uid].get(k, u[k])
    out.append(u)
json.dump({"version": 1, "source": "한국대학교육협의회 전국대학및전문대학정보표준데이터", "universities": out},
          open(dst, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(f"대학·전문대학 {len(out)}곳 저장 → data/universities.json")
