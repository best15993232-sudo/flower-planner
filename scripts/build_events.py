#!/usr/bin/env python3
"""수집 파일(schools.json · universities.json · university_sources.json)을
사이트가 읽는 두 파일로 바꿔요.

  data/places.json  장소: 학교·대학 캠퍼스·(나중에) 공연장·전시장. 규모(학생 수·좌석 수·면적) 포함
  data/events.json  행사: 장소마다 여러 개 가능. 졸업식·학위수여식, 나중에 공연·전시·입학식 등

구조 설명은 docs/data-structure.md 에 있어요. 수집 스크립트는 지금처럼
schools.json 을 고치고, 이 스크립트가 마지막에 두 파일을 다시 만들어요.
"""
import json, os, re, sys
from datetime import date

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
D = lambda *p: os.path.join(ROOT, "data", *p)
TERM = "2026"   # 2026학년도 (2026-12 ~ 2027-02 졸업)

SIDO_SHORT = {'서울특별시':'서울','부산광역시':'부산','대구광역시':'대구','인천광역시':'인천','대전광역시':'대전',
  '울산광역시':'울산','세종특별자치시':'세종','경기도':'경기','강원특별자치도':'강원','강원도':'강원','충청북도':'충북',
  '충청남도':'충남','전북특별자치도':'전북','전라북도':'전북','전라남도':'전남','경상북도':'경북','경상남도':'경남',
  '제주특별자치도':'제주','광주광역시':'광주'}

# 수집기 상태 → 행사 상태
STATUS = {
    "Graduation found in NEIS": "registered",          # 나이스에 졸업식 하루 등록
    "Review: multiple graduation dates": "review_multiple",
    "Review: ambiguous event name": "review_name",
    "Graduation not yet found": "missing",
    "No calendar data": "no_data",
    "not_queried": "not_queried",
}


def load(p, default=None):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def size_of(sizes, pid):
    """사이트에 필요한 규모 값만: 학교 students·grads, 공연장·전시장 seats·area"""
    z = sizes.get(pid) or {}
    return {k: z[k] for k in ("students", "grads", "seats", "area") if z.get(k) not in (None, "")} or None


def school_gender(c):
    return "m" if c == "남" else "f" if c == "여" else "co"


def build(schools_doc, univ_doc, sources_doc, sizes):
    places, events = [], []
    raw, rev = schools_doc.get("rawEvents", {}), schools_doc.get("reviewDates", {})

    for s in schools_doc["schools"]:
        p = {"id": s["id"], "type": "school", "name": s["name"], "kind": s["kind"], "region": s["region"],
             "address": s["address"], "gender": school_gender(s.get("coedu")), "website": s.get("website") or "",
             "lat": s.get("lat"), "lon": s.get("lon")}
        z = size_of(sizes, s["id"])
        if z: p["size"] = z
        places.append(p)

        status = STATUS.get(s["status"], "not_queried")
        dates = s.get("dates") or []
        e = {"id": f"grad:{s['id']}:{TERM}", "place": s["id"], "type": "graduation", "term": TERM,
             "label": "졸업식", "status": status,
             "date": dates[0] if status == "registered" and len(dates) == 1 else None,
             "source": {"kind": "neis", "checked": s.get("checked")}}
        if status != "registered":
            cands = dates if dates else rev.get(s["id"], [])
            if cands: e["candidates"] = cands
            if s["id"] in raw: e["rawNames"] = raw[s["id"]]
        if s.get("winter"): e["winterStart"] = s["winter"]
        if s.get("prevDates"):
            e["history"] = [{"from": s["prevDates"], "at": s.get("changedAt")}]
        events.append(e)

    by_name = {}
    for src in (sources_doc or {}).get("sources", []):
        by_name[(src["name"], src.get("campus", "본교"))] = src

    for u in univ_doc.get("universities", []):
        region = SIDO_SHORT.get(u["region"], u["region"])
        if u["region"] == "전남광주통합특별시":
            g = (u["address"].split(" ") + ["", ""])[1]
            region = "광주" if g.endswith("구") else "전남"
        camp = u.get("campus") or "본교"
        name = u["name"] + ("" if camp == "본교" else f" ({re.sub('캠퍼$', '캠퍼스', camp)})")
        p = {"id": u["id"], "type": "campus", "name": name, "kind": u["kind"], "region": region,
             "address": u["address"], "gender": "f" if "여자대학" in u["name"] else "co",
             "website": u.get("website") or "", "lat": u.get("lat"), "lon": u.get("lon")}
        z = size_of(sizes, u["id"])
        if z: p["size"] = z
        places.append(p)

        dates = u.get("dates") or []
        ok = len(dates) == 1
        src = by_name.get((u["name"], camp), {})
        e = {"id": f"grad:{u['id']}:{TERM}", "place": u["id"], "type": "graduation", "term": TERM,
             "label": u.get("dateLabel") or "학위수여식", "unit": "학부", "status": "confirmed" if ok else "missing",
             "date": dates[0] if ok else None,
             "source": {"kind": "school_page" if ok else "none",
                        "url": u.get("dateUrl") or src.get("url") or "", "checked": u.get("dateChecked")}}
        events.append(e)
    return places, events


def validate(places, events):
    ids = {p["id"] for p in places}
    assert len(ids) == len(places), "장소 id 중복"
    eids = set()
    for e in events:
        assert e["place"] in ids, f"없는 장소를 가리키는 행사: {e['id']}"
        assert e["id"] not in eids, f"행사 id 중복: {e['id']}"
        eids.add(e["id"])
        if e["status"] in ("registered", "confirmed"):
            assert re.fullmatch(r"\d{8}", e["date"] or ""), f"확인 상태인데 날짜가 없음: {e['id']}"
        else:
            assert e["date"] is None, f"미확인 상태인데 날짜가 있음: {e['id']}"


def main():
    schools_doc = load(D("schools.json"))
    univ_doc = load(D("universities.json"), {"universities": []})
    sources = load(D("university_sources.json"), {})
    sz = load(D("place_sizes.json"), {}) or {}
    sizes = sz.get("sizes", {})
    places, events = build(schools_doc, univ_doc, sources, sizes)
    validate(places, events)
    upd = schools_doc.get("updatedAt") or date.today().isoformat()
    out = [("places.json", {"version": 1, "updatedAt": upd, "sizeYear": sz.get("year"), "sizeSource": sz.get("source"), "places": places}),
           ("events.json", {"version": 1, "updatedAt": upd, "term": TERM, "events": events})]
    for name, doc in out:
        with open(D(name), "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
    print(f"장소 {len(places):,}곳 · 행사 {len(events):,}건 "
          f"(날짜 있음 {sum(1 for e in events if e['date']):,}건)")


if __name__ == "__main__":
    sys.exit(main())
