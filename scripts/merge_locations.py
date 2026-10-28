#!/usr/bin/env python3
"""전국초중등학교위치표준데이터(CSV)의 위도·경도를 data/schools.json 에 합칩니다.
인터넷·키 불필요. 모호한 학교는 임의 좌표를 넣지 않고 목록으로 남겨요.

사용: python3 scripts/merge_locations.py school_locations.csv [--base data/schools.json] [--review review_locations.csv]
CSV 인코딩은 CP949/UTF-8 모두 자동 인식해요."""
import argparse, collections, csv, json, os, re, sys, tempfile


def read_csv(path):
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "cp949"):
        try:
            return list(csv.DictReader(raw.decode(enc).splitlines()))
        except UnicodeDecodeError:
            pass
    sys.exit("CSV 인코딩을 읽지 못했어요.")


nn = lambda s: re.sub(r"\s+", "", s or "")
SIDO = {"서울": "서울", "부산": "부산", "대구": "대구", "인천": "인천", "광주": "광주", "대전": "대전", "울산": "울산",
        "세종": "세종", "경기": "경기", "강원": "강원", "충북": "충북", "충남": "충남", "전북": "전북", "전남": "전남",
        "경북": "경북", "경남": "경남", "제주": "제주", "충청북": "충북", "충청남": "충남", "전라북": "전북",
        "전라남": "전남", "경상북": "경북", "경상남": "경남", "전남광": "광주"}


def rest(addr):
    """시·도 이름이 달라도 비교되도록 첫 단어(시도)를 뺀 나머지 주소"""
    p = (addr or "").split(None, 1)
    return nn(p[1]) if len(p) > 1 else ""


def roads(addr):
    return set(re.findall(r"[가-힣0-9]+(?:대로|로|길)\d*(?:번길)?\s*\d*(?:-\d+)?", addr or ""))


def match(s, cands):
    if not cands:
        return None, "no_candidate"
    a = nn(s["address"])
    m = [r for r in cands if nn(r["소재지도로명주소"]) == a]
    if len(m) == 1: return m[0], "address"
    m = [r for r in cands if rest(r["소재지도로명주소"]) == rest(s["address"])]
    if len(m) == 1: return m[0], "address_no_sido"
    if len(cands) == 1:
        c = cands[0]
        # 이름·학교급이 유일해도 시군구가 완전히 다르면 건너뜀
        t1 = (s["address"].split() + ["", ""])[1]
        t2 = (c["소재지도로명주소"].split() + ["", ""])[1]
        if t1 == t2 or t1[:2] == t2[:2]: return c, "name_unique"
        return None, "name_unique_but_district_differs"
    ra = roads(s["address"])
    m = [r for r in cands if ra and ra == roads(r["소재지도로명주소"])]
    if len(m) == 1: return m[0], "road"
    return None, "ambiguous"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--base", default="data/schools.json")
    ap.add_argument("--review", default="review_locations.csv")
    a = ap.parse_args()
    base = json.load(open(a.base, encoding="utf-8"))
    idx = collections.defaultdict(list)
    for r in read_csv(a.csv):
        if r.get("운영상태", "운영") != "운영" or not r.get("위도") or not r.get("경도"):
            continue
        idx[(nn(r["학교명"]), r["학교급구분"])].append(r)
    how, review = collections.Counter(), []
    for s in base["schools"]:
        r, why = match(s, idx.get((nn(s["name"]), s["kind"]), []))
        how[why if r is None else why] += 1
        if r is None:
            review.append((s["id"], s["name"], s["kind"], s["address"], why)); continue
        lat, lon = float(r["위도"]), float(r["경도"])
        if not (33 <= lat <= 39 and 124 <= lon <= 132):       # 한국 밖 좌표는 오류로 보고 건너뜀
            review.append((s["id"], s["name"], s["kind"], s["address"], "out_of_range")); how["out_of_range"] += 1; continue
        s["lat"], s["lon"] = round(lat, 6), round(lon, 6)
    total = len(base["schools"])
    ok = sum(1 for s in base["schools"] if s.get("lat") is not None)
    print(f"좌표 결합 {ok:,}/{total:,}개교 ({100*ok/total:.1f}%)")
    for k, v in how.most_common(): print(f"  {k}: {v:,}")
    with open(a.review, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f); w.writerow(["id", "name", "kind", "address", "reason"]); w.writerows(review)
    print(f"확인 필요 {len(review):,}개교 → {a.review}")
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(a.base)), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(base, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, a.base)


if __name__ == "__main__":
    main()
