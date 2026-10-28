#!/usr/bin/env python3
"""data/universities.json 의 주소를 카카오 로컬 API(주소→좌표)로 변환해 좌표를 채웁니다. 한 번만 돌리면 돼요(좌표가 없는 곳만 조회).
키는 환경변수 KAKAO_REST_KEY 로만 넣어 주세요(카카오 개발자 콘솔의 'REST API 키')."""
import json, os, sys, time, urllib.parse, urllib.request
key = os.environ.get("KAKAO_REST_KEY") or sys.exit("KAKAO_REST_KEY 환경변수가 없어요.")
p = os.path.join(os.path.dirname(__file__), "..", "data", "universities.json")
d = json.load(open(p, encoding="utf-8"))
done = fail = 0
for u in d["universities"]:
    if u.get("lat") is not None: continue
    q = urllib.parse.urlencode({"query": u["address"]})
    req = urllib.request.Request("https://dapi.kakao.com/v2/local/search/address.json?" + q,
                                 headers={"Authorization": "KakaoAK " + key})
    try:
        docs = json.load(urllib.request.urlopen(req, timeout=15)).get("documents", [])
    except Exception as e:
        print("실패:", u["name"], type(e).__name__); fail += 1; continue
    if docs:
        u["lat"], u["lon"] = round(float(docs[0]["y"]), 6), round(float(docs[0]["x"]), 6); done += 1
    else:
        print("주소를 못 찾음:", u["name"], u["address"]); fail += 1
    time.sleep(0.05)
json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(f"좌표 {done}곳 채움, 확인 필요 {fail}곳")
