"""학교·캠퍼스마다 옛 주소(지번 주소)의 동 이름을 모아 data/place_dongs.json 에 저장해요.
사이트 검색에서 '정자동'처럼 옛 주소 동 이름으로 쳐도 학교가 나오게 하려는 용도예요.
- 카카오 주소 검색(도로명 주소 → 지번 주소의 법정동·리)과 좌표 → 행정동 변환을 써요.
- 이미 있는 곳은 건너뛰어요(새로 생긴 학교만 채움). 키는 환경변수 KAKAO_REST_KEY 로만 넣어요."""
import json, os, sys, time, urllib.error, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
key = os.environ.get("KAKAO_REST_KEY") or sys.exit("KAKAO_REST_KEY 환경변수가 없어요.")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "place_dongs.json")
places = json.load(open(os.path.join(ROOT, "data", "places.json"), encoding="utf-8"))["places"]
old = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
dongs = old.get("dongs", {})

def get(path, params):
    url = "https://dapi.kakao.com" + path + "?" + urllib.parse.urlencode(params)
    for i in range(3):
        try:
            req = urllib.request.Request(url, headers={"Authorization": "KakaoAK " + key})
            return json.load(urllib.request.urlopen(req, timeout=15)).get("documents", [])
        except urllib.error.HTTPError as e:
            if e.code in (400, 404): return []
            time.sleep(1.5 * (i + 1))
        except Exception:
            time.sleep(1.5 * (i + 1))
    return None

def one(p):
    names = []
    docs = get("/v2/local/search/address.json", {"query": p["address"]}) if p.get("address") else []
    if docs:
        a = docs[0].get("address") or {}
        names += [a.get("region_3depth_name"), a.get("region_3depth_h_name")]
        # 리 단위 (예: 봉담읍 상리) 는 3depth 에 '읍 리'가 같이 들어와요
    if p.get("lat") is not None and p.get("lon") is not None:
        r = get("/v2/local/geo/coord2regioncode.json", {"x": p["lon"], "y": p["lat"]}) or []
        for d in r:
            names += [d.get("region_3depth_name"), d.get("region_4depth_name")]
    out = []
    for n in names:
        for w in (n or "").split():
            if w and w not in out and w not in (p.get("address") or "").split():
                out.append(w)
    return p["id"], " ".join(out)

todo = [p for p in places if p["id"] not in dongs]
print(f"전체 {len(places)}곳, 새로 찾을 곳 {len(todo)}곳")
t0 = time.time()
with ThreadPoolExecutor(8) as ex:
    for i, (pid, d) in enumerate(ex.map(one, todo), 1):
        if d: dongs[pid] = d
        if i % 1000 == 0: print(i, f"{time.time()-t0:.0f}초")
keep = {p["id"] for p in places}
dongs = {k: v for k, v in sorted(dongs.items()) if k in keep}
json.dump({"about": "옛 주소(지번)·행정동 동 이름. 사이트 검색용. scripts/fetch_dongs.py 로 만들어요.", "dongs": dongs},
          open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(f"동 이름 있는 곳 {len(dongs)}/{len(places)}")
