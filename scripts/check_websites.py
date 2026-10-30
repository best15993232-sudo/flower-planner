#!/usr/bin/env python3
"""학교·대학 홈페이지 주소가 실제로 열리는지 확인해요 (한 달에 한 번 + 수동).

결과: data/website_status.json
  { "checkedAt": "YYYY-MM-DD",
    "sites": { 장소id: {"url": 실제로 열린 주소, "ok": true/false, "how": "https|http|redirect",
                        "err": 실패 이유, "fails": 연속 실패 횟수, "dns": 도메인 자체가 없음} } }

build_events.py 가 이 파일을 보고
  - http 로만 열리면 http 주소로 바꿔 쓰고
  - 도메인이 아예 없거나 2번 연속(다른 날) 안 열리면 주소를 비워요 → 사이트에는 '학교 검색' 버튼이 나와요.
한 번 실패로는 지우지 않아요(학교 서버가 잠깐 멈췄을 수 있어서).

주의: 해외 서버(GitHub Actions)에서 보면 해외 접속을 막는 학교가 있어 실패로 보일 수 있어요.
실패가 너무 많으면(전체의 30% 이상) 결과를 저장하지 않고 멈춰요.
"""
import concurrent.futures as cf, json, os, re, socket, ssl, sys, time
import urllib.request, urllib.error
from datetime import date
from urllib.parse import urlsplit

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
D = lambda *p: os.path.join(ROOT, "data", *p)
UA = "Mozilla/5.0 (compatible; flower-planner-linkcheck/1.0; +https://best15993232-sudo.github.io/flower-planner/)"
CTX = ssl.create_default_context()
LAX = ssl._create_unverified_context()   # 인증서가 낡은 학교가 많아요. 열리는지만 보니까 인증서 오류는 '열림'으로 봐요


def load(p, d=None):
    try:
        return json.load(open(p, encoding="utf-8"))
    except FileNotFoundError:
        return d


def clean(u):
    u = (u or "").strip()
    if not u:
        return ""
    u = re.sub(r"\s+", "", u)
    u = re.sub(r"^https?://", "", u, flags=re.I)
    return u.rstrip("/")


def try_open(url, timeout):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
    for ctx in (CTX, LAX):
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
                r.read(512)
                return True, r.geturl(), r.status, ""
        except urllib.error.HTTPError as e:
            # 403·405 등은 서버가 살아 있다는 뜻. 사람이 브라우저로 열면 대개 열려요
            if e.code < 500 and e.code not in (404, 410):
                return True, url, e.code, ""
            return False, url, e.code, f"HTTP {e.code}"
        except urllib.error.URLError as e:
            r = e.reason
            if isinstance(r, ssl.SSLError) and ctx is CTX:
                continue
            return False, url, 0, type(r).__name__ + ":" + str(r)[:80]
        except (socket.timeout, TimeoutError):
            return False, url, 0, "timeout"
        except Exception as e:  # noqa
            return False, url, 0, type(e).__name__ + ":" + str(e)[:80]
    return False, url, 0, "ssl"


def check(raw, timeout):
    host_path = clean(raw)
    if not host_path:
        return None
    host = urlsplit("http://" + host_path).hostname or ""
    try:
        socket.getaddrinfo(host, None)
    except socket.gaierror:
        return {"ok": False, "url": "", "err": "dns", "dns": True}
    ok, final, code, err = try_open("https://" + host_path, timeout)
    if ok:
        return {"ok": True, "url": final if final.startswith("https://") else "https://" + host_path, "how": "https"}
    ok2, final2, code2, err2 = try_open("http://" + host_path, timeout)
    if ok2:
        return {"ok": True, "url": final2, "how": "http" if final2.startswith("http://") else "redirect"}
    return {"ok": False, "url": "", "err": err2 or err}


def main():
    schools = load(D("schools.json"))["schools"]
    univs = (load(D("universities.json"), {}) or {}).get("universities", [])
    items = [(s["id"], s.get("website", "")) for s in schools + univs if (s.get("website") or "").strip()]
    prev = (load(D("website_status.json"), {}) or {}).get("sites", {})
    only = os.environ.get("ONLY")   # 시험용: 앞에서 N곳만
    if only:
        items = items[: int(only)]

    t0 = time.time()
    res = {}
    with cf.ThreadPoolExecutor(48) as ex:
        futs = {ex.submit(check, w, 12): pid for pid, w in items}
        for i, f in enumerate(cf.as_completed(futs), 1):
            res[futs[f]] = f.result()
            if i % 1000 == 0:
                print(f"  {i:,}/{len(items):,} ({time.time()-t0:.0f}초)", flush=True)
    # 실패한 곳은 한 번 더, 천천히
    retry = [pid for pid, r in res.items() if r and not r["ok"] and not r.get("dns")]
    web = dict(items)
    with cf.ThreadPoolExecutor(16) as ex:
        for pid, r in zip(retry, ex.map(lambda p: check(web[p], 25), retry)):
            if r:
                res[pid] = r

    fail = [p for p, r in res.items() if r and not r["ok"]]
    rate = len(fail) / max(1, len(res))
    print(f"확인 {len(res):,}곳 · 열림 {len(res)-len(fail):,} · 안 열림 {len(fail):,} ({rate:.1%}) · "
          f"http로만 {sum(1 for r in res.values() if r and r.get('how')=='http'):,} · {time.time()-t0:.0f}초")
    if rate > 0.30 and not only:
        print("실패가 30%를 넘어요. 해외 접속 차단일 가능성이 커서 결과를 저장하지 않아요.")
        return 2

    sites = {}
    for pid, r in res.items():
        if r is None:
            continue
        r["fails"] = 0 if r["ok"] else (prev.get(pid, {}).get("fails", 0) + 1)
        sites[pid] = r
    with open(D("website_status.json"), "w", encoding="utf-8") as f:
        json.dump({"version": 1, "checkedAt": date.today().isoformat(), "sites": sites},
                  f, ensure_ascii=False, separators=(",", ":"))
    os.makedirs(os.path.join(ROOT, "docs", "reports"), exist_ok=True)
    names = {s["id"]: s["name"] for s in schools + univs}
    with open(os.path.join(ROOT, "docs", "reports", "websites_failed.txt"), "w", encoding="utf-8") as f:
        f.write(f"# 홈페이지가 안 열린 곳 ({date.today()}) {len(fail)}곳. fails=연속 실패 횟수\n")
        for p in sorted(fail, key=lambda p: names.get(p, "")):
            r = sites[p]
            f.write(f"{names.get(p,'')}\t{web.get(p,'')}\t{r.get('err','')}\tfails={r['fails']}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
