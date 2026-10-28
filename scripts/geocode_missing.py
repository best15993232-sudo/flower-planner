#!/usr/bin/env python3
"""좌표가 없는 학교·대학을 카카오 로컬 API로 보충합니다. (좌표가 있는 곳은 건드리지 않아요)
1) 주소 검색 → 2) 실패하면 학교 이름 키워드 검색(학교 카테고리, 같은 시·군·구일 때만 인정)
키는 환경변수 KAKAO_REST_KEY. 결과는 학교마다 geo 필드에 출처를 남겨요(kakao_address / kakao_keyword)."""
import json, os, re, sys, time, urllib.error, urllib.parse, urllib.request

KEY = os.environ.get("KAKAO_REST_KEY") or sys.exit("KAKAO_REST_KEY 환경변수가 없어요.")
ROOT = os.path.join(os.path.dirname(__file__), "..", "data")


def call(path, **q):
    req = urllib.request.Request(f"https://dapi.kakao.com{path}?" + urllib.parse.urlencode(q),
                                 headers={"Authorization": "KakaoAK " + KEY})
    try:
        return json.load(urllib.request.urlopen(req, timeout=15)).get("documents", [])
    except urllib.error.HTTPError as e:
        if e.code in (401, 403): sys.exit(f"카카오 인증 오류({e.code}): 키와 '제품 설정 > 카카오맵' 사용 설정을 확인해 주세요.")
        if e.code == 429: sys.exit("카카오 호출 한도(429). 내일 다시 실행해 주세요.")
        return []
    finally:
        time.sleep(0.06)


def district(addr):
    """주소에서 시·군·구 단어들 (시도 이름이 바뀌어도 비교되도록 시도는 제외)"""
    toks = (addr or "").split()[1:4]
    return {t for t in toks if re.search(r"(시|군|구)$", t)}


def clean_name(n):
    return re.sub(r"\s+|\(.*?\)", "", n or "")


def find(s):
    addr = (s.get("address") or "").strip()
    if addr:
        d = call("/v2/local/search/address.json", query=addr)
        if d:
            return float(d[0]["y"]), float(d[0]["x"]), "kakao_address"
    # 학교 이름으로 검색: 학교 카테고리(SC4)이고, 이름이 같고, 시·군·구가 겹칠 때만
    name = clean_name(s["name"])
    want = district(addr)
    for doc in call("/v2/local/search/keyword.json", query=f'{s.get("region","")} {s["name"]}'.strip(), category_group_code="SC4", size=15):
        if clean_name(doc.get("place_name")) != name:
            continue
        got = district(doc.get("road_address_name") or doc.get("address_name"))
        if want and not (want & got):
            continue
        return float(doc["y"]), float(doc["x"]), "kakao_keyword"
    return None


def run(fname, listkey, label):
    p = os.path.join(ROOT, fname)
    d = json.load(open(p, encoding="utf-8"))
    items = [s for s in d[listkey] if s.get("lat") is None]
    ok, miss = 0, []
    for s in items:
        r = find(s)
        if r and 33 <= r[0] <= 39 and 124 <= r[1] <= 132:
            s["lat"], s["lon"], s["geo"] = round(r[0], 6), round(r[1], 6), r[2]; ok += 1
        else:
            miss.append(f'{s["name"]} | {s.get("address","")}')
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"[{label}] 좌표 없던 {len(items)}곳 중 {ok}곳 보충, 남은 {len(miss)}곳")
    for m in miss: print("   남음:", m)


run("schools.json", "schools", "초중고")
run("universities.json", "universities", "대학")
