"""
발행 전 링크 검증
------------------
편집본(data/edition/YYYY-MM-DD.json)의 모든 URL이 실제로 살아 있는지 확인한다.

확인 순서
  1) 그날 수집 원자료(data/raw/YYYY-MM-DD.json)에 있는 URL인가  → 즉시 통과 (수집기가 가져온 실제 링크)
  2) 아니면 실제로 접속해 응답 코드를 확인
  3) 어느 쪽도 아니면 '출처 불명'으로 표시 — 손으로 옮겨 적다 틀렸거나 지어낸 주소일 수 있다

발행 전에 반드시 통과시킬 것. 링크 하나가 죽어 있으면 뉴스레터 전체의 신뢰가 깎인다.

사용법:
  python system/verify.py
  python system/verify.py --date 2026-08-24
"""

import argparse
import concurrent.futures as cf
import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0 Safari/537.36"}
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

# 일부 사이트(국내 전시회 사이트 등)는 낡은 암호설정을 써서 파이썬이 연결을 거부한다.
# 브라우저는 접속되는데 검증기만 실패하는 상황을 막기 위한 완화 컨텍스트.
# 링크 생존 확인 용도이며 민감정보를 주고받지 않으므로 안전하다.
CTX_LEGACY = ssl.create_default_context()
CTX_LEGACY.check_hostname = False
CTX_LEGACY.verify_mode = ssl.CERT_NONE
try:
    CTX_LEGACY.set_ciphers("DEFAULT@SECLEVEL=0")
except ssl.SSLError:
    pass


def collect_urls(ed):
    """편집본에서 (위치, 제목, URL) 목록을 뽑는다.
    전시회 캘린더는 별도 파일(data/exhibitions.json)에서 오므로 함께 검사한다."""
    out = []
    exh_path = os.path.join(ROOT, "data", "exhibitions.json")
    if any(sec.get("kind") == "calendar"
           for t in (ed.get("tabs") or []) for sec in t.get("sections", []))             and os.path.exists(exh_path):
        for x in json.load(open(exh_path, encoding="utf-8"))["exhibitions"]:
            if x.get("url") and not x.get("skip_verify"):
                out.append(("전시회 캘린더", x.get("name_ko", "")[:60], x["url"]))
            elif x.get("skip_verify"):
                print(f"  (검증 생략) {x.get('name_ko', '')} — {x['skip_verify']}")
    tabs = ed.get("tabs") or [{"label": "본문", "sections": ed.get("sections", [])}]
    for t in tabs:
        for sec in t.get("sections", []):
            for it in sec.get("items", []):
                where = f"{t['label']} / {sec.get('title', '')}"
                if it.get("url"):
                    out.append((where, it.get("title", "")[:60], it["url"]))
                for o in it.get("others", []) or []:
                    if o.get("url"):
                        out.append((where, "(관련기사) " + (o.get("outlet") or ""), o["url"]))
    return out


def check(url):
    """접속 확인. HEAD 거부 시 GET, 구형 TLS 서버는 완화 설정으로 재시도."""
    last = ""
    for ctx in (CTX, CTX_LEGACY):
        for method in ("HEAD", "GET"):
            try:
                req = urllib.request.Request(url, headers=UA, method=method)
                return urllib.request.urlopen(req, timeout=25, context=ctx).status, ""
            except urllib.error.HTTPError as ex:
                if ex.code in (403, 405, 429) and method == "HEAD":
                    continue                   # HEAD 거부 → GET 재시도
                return ex.code, ""
            except Exception as ex:
                last = type(ex).__name__
                continue
    return 0, last or "실패"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    ap.add_argument("--all", action="store_true",
                    help="수집 원자료에 있는 URL도 실제 접속해 확인 (느림)")
    args = ap.parse_args()

    ed_path = os.path.join(ROOT, "data", "edition", f"{args.date}.json")
    ed = json.load(open(ed_path, encoding="utf-8"))

    raw_path = os.path.join(ROOT, "data", "raw", f"{args.date}.json")
    known = set()
    if os.path.exists(raw_path):
        for it in json.load(open(raw_path, encoding="utf-8"))["items"]:
            known.add(it["url"])
            for o in it.get("others", []) or []:
                known.add(o["url"])

    urls = collect_urls(ed)
    print(f"편집본 {args.date} — 검증 대상 {len(urls)}건 "
          f"(수집 원자료 보유 링크 {len(known)}건)\n")

    todo, ok_known = [], []
    for where, title, url in urls:
        if url in known and not args.all:
            ok_known.append((where, title, url))
        else:
            todo.append((where, title, url))

    print(f"[1] 수집 원자료와 일치 — {len(ok_known)}건 통과 (접속 확인 생략)")
    print(f"[2] 원자료에 없는 링크 {len(todo)}건 → 실제 접속 확인 중…\n")

    bad, suspicious = [], []
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(check, u): (w, t, u) for w, t, u in todo}
        for f in cf.as_completed(futs):
            w, t, u = futs[f]
            code, err = f.result()
            if code and 200 <= code < 400:
                mark = "OK  "
            elif code in (403, 429):
                mark = "주의"                    # 봇 차단 — 사람이 열면 대개 정상
                suspicious.append((w, t, u, code))
            else:
                mark = "실패"
                bad.append((w, t, u, code or err))
            print(f"  {mark} {code or err:>4} | {t[:52]:52s} | {u[:60]}")

    print("\n" + "=" * 72)
    if bad:
        print(f"[X] 접속 실패 {len(bad)}건 — 발행 전에 반드시 확인하세요")
        for w, t, u, c in bad:
            print(f"    · [{w}] {t}")
            print(f"      {u}  ({c})")
    if suspicious:
        print(f"[!] 봇 차단 추정 {len(suspicious)}건 — 브라우저로 직접 열어 확인 권장")
        for w, t, u, c in suspicious:
            print(f"    · {t} ({c})")
    if not bad and not suspicious:
        print("[OK] 모든 링크 정상. 발행 가능합니다.")
    print("=" * 72)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
