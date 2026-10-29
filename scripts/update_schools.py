#!/usr/bin/env python3
"""나이스(NEIS) 학사일정을 조회해 data/schools.json 의 졸업일 정보를 갱신합니다.

사용법
  export NEIS_KEY=발급받은키          # 키는 코드/채팅에 적지 말고 환경변수나 CI 비밀값으로만
  python3 scripts/update_schools.py --max 3000          # 오래된/미조회 학교부터 3000개 갱신
  python3 scripts/update_schools.py --max 50 --dry-run  # 파일을 쓰지 않고 결과만 확인
  python3 scripts/update_schools.py --csv-check school_summary.csv --max 1200 --dry-run
        # 기존 수집 결과(CSV)와 분류가 같은지 대조 (처음 한 번 꼭 해 보세요)

표준 라이브러리만 사용합니다. (pip 설치 필요 없음)
"""
import argparse, concurrent.futures as cf, csv, json, os, re, sys, tempfile, time, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta

API = "https://open.neis.go.kr/hub/SchoolSchedule"
KST = timezone(timedelta(hours=9))

# ── 졸업일 분류 규칙: 기존 PowerShell 수집기(collect_neis_nationwide.ps1 v0.4.0)와 똑같이 옮겼어요 ──
WINDOW_FROM, WINDOW_TO = "20261201", "20270228"
ART = re.compile(r"음악회|연주회|전시|공연|예술제|축제|졸업작품|발표회")
PREP = re.compile(r"사정회|졸업후미산입|졸업진급사정|졸업사정|졸업앨범|졸업사진|졸업여행|졸업생|졸업논문|졸업시험|졸업식연습|졸업식예행|졸업식리허설|졸업식안내|졸업식준비")
CEREMONY = re.compile(r"졸업식|졸업[/·•,\-]종업식|졸업및종업식|종업식[/·•,\-]졸업")
CONTEXT = re.compile(r"종업식")
HOLIDAY = re.compile(r"휴업|휴무|휴교")   # '졸업식 휴업'은 졸업식 날짜라고 단정하지 않고 확인 필요로 (2026-10-30 추가)

ST_OK, ST_MULTI = "Graduation found in NEIS", "Review: multiple graduation dates"
ST_AMBIG, ST_NONE = "Review: ambiguous event name", "Graduation not yet found"
ST_NOCAL, ST_NQ = "No calendar data", "not_queried"


def event_class(name):
    n = re.sub(r"\s+", "", name or "").replace("（", "(").replace("）", ")")
    art, prep, cer = ART.search(n), PREP.search(n), CEREMONY.search(n)
    if cer and art: return "review"
    if cer and HOLIDAY.search(n): return "review"
    if art: return "future_event"
    if prep: return "excluded"
    if cer: return "graduation"
    if "졸업" in n: return "review"
    return "other"


def classify(rows, no_data=False):
    """NEIS 학사일정 행 → (status, dates, review_dates, raw_events). 순수 함수라 테스트하기 쉬워요."""
    ev, grad, amb = {}, set(), set()
    for r in rows:
        d, n = str(r.get("AA_YMD", "")), (r.get("EVENT_NM") or "").strip()
        ev.setdefault(d, []).append(n)
        c = event_class(n)
        if c == "graduation": grad.add(d)
        elif c == "review": amb.add(d)
    dates, review = sorted(x for x in grad if x), sorted(x for x in amb if x)
    if len(dates) > 1: status = ST_MULTI
    elif len(dates) == 1: status = ST_OK
    elif review: status = ST_AMBIG
    elif no_data: status = ST_NOCAL
    else: status = ST_NONE
    raw = {}
    if status in (ST_MULTI, ST_AMBIG):
        keep = set(dates) | set(review) | {d for d, ns in ev.items() if any(CONTEXT.search(n) for n in ns)}
        raw = {d: ev[d] for d in sorted(keep)}
    return status, dates, review, raw


def winter_start(rows):
    """학교가 나이스에 등록한 '겨울방학' 중 가장 이른 날짜. 졸업식 날짜가 이상한지 판단할 때 참고해요."""
    ds = [str(r.get("AA_YMD", "")) for r in rows or []
          if "겨울방학" in re.sub(r"\s+", "", r.get("EVENT_NM") or "")]
    return min(ds) if ds else None


class ApiError(Exception):
    pass


def fetch_rows(key, office, code, retries=4):
    q = urllib.parse.urlencode({"KEY": key, "Type": "json", "pIndex": 1, "pSize": 1000,
                                "ATPT_OFCDC_SC_CODE": office, "SD_SCHUL_CODE": code,
                                "AA_FROM_YMD": WINDOW_FROM, "AA_TO_YMD": WINDOW_TO})
    last = None
    for i in range(retries):
        try:
            with urllib.request.urlopen(f"{API}?{q}", timeout=20) as r:
                data = json.load(r)
            if "SchoolSchedule" in data:
                head, body = data["SchoolSchedule"][0]["head"], data["SchoolSchedule"][1:]
                code_ = head[1]["RESULT"]["CODE"]
                if code_ == "INFO-000":
                    return body[0]["row"] if body else []
                raise ApiError(code_)
            code_ = data.get("RESULT", {}).get("CODE", "?")
            if code_ == "INFO-200":          # 해당 기간 데이터 없음 → '학사일정 자료 없음'
                return None
            if code_ in ("ERROR-290", "ERROR-300", "ERROR-337"):   # 키 오류/호출 한도: 재시도 무의미
                raise SystemExit(f"NEIS 오류 {code_}: {data['RESULT'].get('MESSAGE')}")
            raise ApiError(code_)
        except SystemExit:
            raise
        except Exception as e:                 # 네트워크/일시 오류 → 잠깐 쉬고 재시도
            last = e
            time.sleep(1.5 * (i + 1))
    raise ApiError(str(last))


PAST_GRACE = 3     # 졸업식이 지난 지 3일이 넘은 학교는 더 이상 조회하지 않아요


def pick_priority(schools, today):
    """우선 조회 대상 선택. 졸업식이 가까울수록 자주 확인해요.
      · 아직 조회 안 한 학교 / 날짜 미등록·후보 여러 개·행사명 확인 필요 → 실행할 때마다
      · 졸업식이 14일 안 → 실행할 때마다 (날짜 변경이 가장 치명적인 시기)
      · 졸업식이 15~42일 뒤 → 3일에 한 번
      · 그보다 먼 일정, 학사일정 자료 없음 → 7일에 한 번"""
    t = datetime.strptime(today, "%Y-%m-%d").date()
    ymd = lambda n: (t + timedelta(days=n)).strftime("%Y%m%d")
    iso = lambda n: (t - timedelta(days=n)).strftime("%Y-%m-%d")
    lo, d14, d42 = ymd(-PAST_GRACE), ymd(14), ymd(42)
    picked = []
    for s in schools:
        chk = s.get("checked") or ""
        if s["status"] == ST_NQ:
            picked.append((0, chk, s)); continue
        if chk == today:
            continue
        d = s["dates"][0] if s["dates"] else None
        if s["status"] == ST_OK and d:
            if d < lo: continue                                    # 이미 지난 졸업식
            gap = 0 if d <= d14 else 3 if d <= d42 else 7
            tier = 1 if d <= d42 else 2
        elif s["status"] in (ST_NONE, ST_MULTI, ST_AMBIG):
            gap, tier = 0, 1
        else:
            gap, tier = 7, 2
        if chk <= iso(gap) if gap else True:
            picked.append((tier, chk, s))
    picked.sort(key=lambda x: (x[0], x[1]))
    return [x[2] for x in picked], sum(1 for x in picked if x[0] < 2), sum(1 for x in picked if x[0] == 2)


OFFICES = [("B10","서울"),("C10","부산"),("D10","대구"),("E10","인천"),("F10","광주"),("G10","대전"),("H10","울산"),
           ("I10","세종"),("J10","경기"),("K10","강원"),("M10","충북"),("N10","충남"),("P10","전북"),("Q10","전남"),
           ("R10","경북"),("S10","경남"),("T10","제주")]


def fetch_info_page(key, office, page, retries=4):
    q = urllib.parse.urlencode({"KEY": key, "Type": "json", "pIndex": page, "pSize": 1000, "ATPT_OFCDC_SC_CODE": office})
    last = None
    for i in range(retries):
        try:
            with urllib.request.urlopen(f"https://open.neis.go.kr/hub/schoolInfo?{q}", timeout=30) as r:
                data = json.load(r)
            if "schoolInfo" in data:
                if data["schoolInfo"][0]["head"][1]["RESULT"]["CODE"] != "INFO-000":
                    raise ApiError("head")
                return data["schoolInfo"][0]["head"][0]["list_total_count"], data["schoolInfo"][1]["row"]
            if data.get("RESULT", {}).get("CODE") == "INFO-200":
                return 0, []
            raise ApiError(data.get("RESULT", {}).get("CODE", "?"))
        except Exception as e:
            last = e
            time.sleep(1.5 * (i + 1))
    raise ApiError(str(last))


def refresh_directory(key, schools):
    """학교기본정보로 신설 학교 추가, 주소·홈페이지·남녀공학 갱신. 사라진 학교는 지우지 않고 알려만 줘요."""
    by = {s["id"]: s for s in schools}
    seen, added, updated = set(), 0, 0
    for off, region in OFFICES:
        page = 1
        while True:
            total, rows = fetch_info_page(key, off, page)
            for r in rows:
                kind, code, name = r.get("SCHUL_KND_SC_NM", ""), r.get("SD_SCHUL_CODE", ""), r.get("SCHUL_NM", "")
                if kind not in ("초등학교", "중학교", "고등학교") or not code or name.startswith("(가칭)"):
                    continue
                sid = f"{off}:{code}"; seen.add(sid)
                info = {"address": r.get("ORG_RDNMA", ""), "website": r.get("HMPG_ADRES", ""), "coedu": r.get("COEDU_SC_NM", "")}
                if sid in by:
                    for k, v in info.items():
                        if v and by[sid].get(k) != v:
                            by[sid][k] = v; updated += 1
                else:
                    by[sid] = {"id": sid, "name": name, "kind": kind, "region": region, **info, "status": ST_NQ,
                               "dates": [], "checked": None, "lat": None, "lon": None}
                    schools.append(by[sid]); added += 1
            if page * 1000 >= total: break
            page += 1; time.sleep(0.12)
    missing = [i for i in by if i not in seen]
    print(f"학교 목록 갱신: 신설 {added}개교 추가 · 정보 수정 {updated}건 · 목록에서 사라진 학교 {len(missing)}개교(삭제하지 않음)")
    return schools


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="data/schools.json")
    ap.add_argument("--out", default=None, help="기본값: --base 와 같은 파일")
    ap.add_argument("--max", type=int, default=3000, help="이번 실행에서 조회할 학교 수 (오래된/미조회 우선)")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--priority", action="store_true", help="졸업식 임박·미등록 학교 위주로만 조회 (평일 자동 실행용)")
    ap.add_argument("--refresh-directory", action="store_true", help="학교기본정보로 신설 학교 추가·주소 갱신 (한 달에 한 번 정도)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--csv-check", help="기존 수집 CSV와 분류 결과를 대조 (대조 대상 학교만 조회)")
    a = ap.parse_args()
    key = os.environ.get("NEIS_KEY")
    if not key:
        sys.exit("NEIS_KEY 환경변수가 없어요.")

    base = json.load(open(a.base, encoding="utf-8"))
    schools = base["schools"]
    if a.refresh_directory:
        schools = refresh_directory(key, schools)
    by = {s["id"]: s for s in schools}

    expected = {}
    if a.csv_check:
        for r in csv.DictReader(open(a.csv_check, encoding="utf-8-sig")):
            expected[f'{r["OfficeCode"]}:{r["SchoolCode"]}'] = (r["Result"], r["GraduationDates"].split(";") if r["GraduationDates"] else [])
        targets = [by[i] for i in expected if i in by]
    elif a.priority:
        targets, na, nb = pick_priority(schools, datetime.now(KST).strftime("%Y-%m-%d"))
        print(f"우선 조회: 임박·미등록 {na}개교 + 오래된 일반 {nb}개교")
    else:
        # 전체 조회: 미조회 먼저, 그다음 마지막 조회가 오래된 순
        targets = sorted(schools, key=lambda s: (s["status"] != ST_NQ, s.get("checked") or ""))
    targets = targets[: a.max]
    print(f"조회 대상 {len(targets)}개교", flush=True)

    now = datetime.now(KST)
    today = now.strftime("%Y-%m-%d")
    results, fails = {}, []

    def work(s):
        off, code = s["id"].split(":")
        time.sleep(0.05)
        return s["id"], fetch_rows(key, off, code)

    with cf.ThreadPoolExecutor(a.workers) as ex:
        futs = {ex.submit(work, s): s for s in targets}
        for n, f in enumerate(cf.as_completed(futs), 1):
            s = futs[f]
            try:
                results[s["id"]] = f.result()[1]
            except ApiError as e:
                fails.append((s["id"], str(e)))
            if n % 200 == 0:
                print(f"  {n}/{len(targets)} (실패 {len(fails)})", flush=True)

    if targets and len(fails) / len(targets) > 0.05:
        sys.exit(f"실패율이 높아요({len(fails)}/{len(targets)}). 기존 파일은 건드리지 않았어요.")

    changed = 0
    mism = []
    raw, rev = dict(base.get("rawEvents", {})), dict(base.get("reviewDates", {}))
    for sid, rows in results.items():
        s = by[sid]
        status, dates, review, rawev = classify(rows or [], no_data=rows is None)
        if expected:
            es, ed = expected.get(sid, (None, None))
            if (es, ed) != (status, dates):
                mism.append((s["name"], sid, (es, ed), (status, dates)))
        if s["status"] != ST_NQ and s["dates"] != dates:      # 날짜가 바뀐 학교 기록 (사이트 알림용)
            s["prevDates"], s["changedAt"] = s["dates"], today
            changed += 1
        s["status"], s["dates"], s["checked"] = status, dates, today
        w = winter_start(rows)
        if w: s["winter"] = w
        else: s.pop("winter", None)
        raw.pop(sid, None); rev.pop(sid, None)
        if rawev: raw[sid] = rawev
        if review and status == ST_AMBIG: rev[sid] = review   # 날짜가 비어 있는 '행사명 확인 필요' 학교만

    print(f"갱신 {len(results)}개교 · 날짜 변경 {changed}개교 · 실패 {len(fails)}개교")
    for sid, why in fails[:10]:
        print("  실패:", sid, why)
    if expected:
        print(f"CSV 대조: 불일치 {len(mism)} / {len(results)}")
        for m in mism[:15]:
            print("  ", m)
    if a.dry_run or a.csv_check:
        print("(파일은 쓰지 않았어요)")
        return

    base.update(schools=schools, rawEvents=raw, reviewDates=rev, version=1,
                updatedAt=today)
    out = a.out or a.base
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(out)), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(base, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, out)       # 쓰는 도중 끊겨도 기존 파일이 깨지지 않게 교체
    print("저장:", out)


if __name__ == "__main__":
    main()
