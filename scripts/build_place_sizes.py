#!/usr/bin/env python3
"""학교알리미 공개용데이터로 학교별 학생 수(전체·졸업 학년)를 만들어요. 1년에 한 번 돌려요.

준비물 (학교알리미 > 공개용데이터, 시도교육청 '전체'로 받기)
  1) 학교기본정보 CSV: 학교급별로 (정보공시 학교코드 · 이름 · 주소 · 위도/경도)
  2) 학년별·학급별 학생수 CSV: 공시년도 올해, 학교급별로

사용법
  python3 scripts/build_place_sizes.py --year 2026 --info 기본정보폴더 --students 학생수폴더
  → data/place_sizes.json 을 만들고, build_events.py 가 장소(places.json)에 붙여요.

학교알리미 학교코드(S0…)와 나이스 학교코드는 달라서, 기본정보의 이름·좌표로 우리 학교와 이어요.
"""
import argparse, csv, glob, json, math, os, re, sys
from collections import defaultdict

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

SIDO_SHORT = {'서울특별시':'서울','부산광역시':'부산','대구광역시':'대구','인천광역시':'인천','대전광역시':'대전',
  '울산광역시':'울산','세종특별자치시':'세종','경기도':'경기','강원특별자치도':'강원','강원도':'강원','충청북도':'충북',
  '충청남도':'충남','전북특별자치도':'전북','전라북도':'전북','전라남도':'전남','경상북도':'경북','경상남도':'경남',
  '제주특별자치도':'제주','광주광역시':'광주'}


def rows(path):
    for enc in ("utf-8-sig", "cp949"):
        try:
            with open(path, encoding=enc, newline="") as f:
                return list(csv.DictReader(f))
        except UnicodeDecodeError:
            continue
    raise SystemExit(f"읽을 수 없는 파일: {path}")


def num(v):
    try:
        return int(float(str(v).replace(",", "") or 0))
    except ValueError:
        return 0


def nname(s):
    s = re.sub(r"\s+|\(.*?\)", "", s or "")
    return s


def km(a, b, c, d):
    if None in (a, b, c, d):
        return None
    r = math.pi / 180
    x = (d - b) * r * math.cos((a + c) / 2 * r)
    y = (c - a) * r
    return 6371 * math.hypot(x, y)


def fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def grads_of(r):
    """졸업 학년 학생 수: 부(초등부·중등부 등)가 없는 일반 열에서 학생이 있는 가장 높은 학년."""
    best = None
    for k, v in r.items():
        m = re.fullmatch(r"(\d)학년 학생수", k or "")
        if m and num(v) > 0 and (best is None or int(m.group(1)) > best[0]):
            best = (int(m.group(1)), num(v))
    return best[1] if best else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", required=True)
    ap.add_argument("--info", required=True, help="학교기본정보 CSV 폴더")
    ap.add_argument("--students", required=True, help="학년별·학급별 학생수 CSV 폴더")
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "place_sizes.json"))
    a = ap.parse_args()

    info = {}
    for p in glob.glob(os.path.join(a.info, "*.csv")):
        for r in rows(p):
            info[r["정보공시 학교코드"]] = r

    ours = json.load(open(os.path.join(ROOT, "data", "schools.json"), encoding="utf-8"))["schools"]
    by_name = defaultdict(list)
    for s in ours:
        by_name[nname(s["name"])].append(s)

    sizes, unmatched, used = {}, [], {}
    for p in sorted(glob.glob(os.path.join(a.students, "*.csv"))):
        for r in rows(p):
            if r.get("제외여부") == "Y":
                continue
            code = r["정보공시 학교코드"]
            total = num(r.get("학생수(계)")) or sum(num(v) for k, v in r.items() if k and k.endswith("학생수(계)"))
            if not total:
                continue
            i = info.get(code, {})
            lat, lon = fnum(i.get("위도")), fnum(i.get("경도"))
            sido = SIDO_SHORT.get(r["시도교육청"].replace("교육청", ""), "")
            cands = by_name.get(nname(r["학교명"]), [])
            pick = None
            if len(cands) == 1:
                c = cands[0]
                d = km(lat, lon, c.get("lat"), c.get("lon"))
                if (d is not None and d < 3) or (d is None and (not sido or c["region"] == sido or sido in ("광주", "전남"))):
                    pick = c
            elif cands:
                ds = [(km(lat, lon, c.get("lat"), c.get("lon")), c) for c in cands]
                ds = [x for x in ds if x[0] is not None and x[0] < 3]
                if ds:
                    pick = min(ds, key=lambda x: x[0])[1]
            if not pick:
                unmatched.append(f"{r['학교명']} ({r['지역']}, {code})")
                continue
            if pick["id"] in used:   # 같은 우리 학교에 두 줄이 붙으면 둘 다 버려요 (잘못 이을 바엔 비워 둬요)
                sizes.pop(pick["id"], None)
                unmatched.append(f"{r['학교명']} (중복 연결, {code})")
                continue
            used[pick["id"]] = code
            z = {"students": total, "classes": num(r.get("학급수(계)")) or None, "year": int(a.year), "code": code}
            g = grads_of(r)
            if g:
                z["grads"] = g
            sizes[pick["id"]] = {k: v for k, v in z.items() if v is not None}

    doc = {"version": 1, "year": int(a.year),
           "source": f"학교알리미 공개용데이터 · 학년별·학급별 학생수 ({a.year}년 공시)",
           "note": "1년에 한 번 갱신. students=전체 학생 수, grads=졸업 학년 학생 수, code=학교알리미 학교코드",
           "sizes": sizes}
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
    n_ours = len(ours)
    print(f"연결 {len(sizes):,}곳 / 우리 학교 {n_ours:,}곳 ({len(sizes)/n_ours:.1%}) · 못 이은 줄 {len(unmatched):,}")
    rep = os.path.join(ROOT, "docs", "reports", f"place_sizes_unmatched_{a.year}.txt")
    os.makedirs(os.path.dirname(rep), exist_ok=True)
    with open(rep, "w", encoding="utf-8") as f:
        f.write("\n".join(unmatched))


if __name__ == "__main__":
    sys.exit(main())
