# -*- coding: utf-8 -*-
"""월간뉴스용 원자료 수집 — 발행일(매월 1일) 기준 직전 한 달치.

주간 백필과 같은 소스(구글뉴스 기간검색 + TED)를 월 단위 창으로 조회한다.
월간은 '그 달의 큰 흐름'이 목적이므로 쿼리를 넓히고 TED 한도를 키운다.

결과: data/archive/raw_monthly/{YYYY-MM-01}.json
사용법:
  python system/backfill_month.py                  # 2026-01-01 ~ 2026-08-01 전체
  python system/backfill_month.py --only 2026-03-01
"""

import argparse
import json
import os
import sys
import time
import concurrent.futures as cf
from datetime import date as ddate, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect import norm_title, score_item, cluster, is_blocked  # noqa: E402
from backfill import fetch_news, fetch_ted  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "data", "archive", "raw_monthly")

QUERIES = [
    ("K-방산", "en", '(Hanwha OR "Korea Aerospace" OR "Hyundai Rotem" OR "LIG Nex1" OR '
                     '"South Korea") defense export OR contract OR deal'),
    ("유럽", "en", '(Poland OR Romania OR Norway OR Finland OR Germany OR NATO) defence '
                   'procurement OR contract OR order'),
    ("중동·인도", "en", '(Saudi OR UAE OR Egypt OR India OR Indonesia) defence contract OR '
                       'procurement OR deal'),
    ("미국·OEM", "en", '(Pentagon OR "US Army" OR "US Navy" OR Rheinmetall OR Lockheed OR '
                       '"BAE Systems") contract OR supplier OR "supply chain" defense'),
    ("국내", "ko", '방산 수출 OR 방위산업 OR 방위사업청'),
    ("정책·전망", "en", 'defence budget OR "defense spending" OR "military procurement" '
                        'policy OR reform'),
]


def month_window(pub):
    """발행일(1일) 기준 직전 달의 [시작, 끝] 날짜."""
    end = pub - timedelta(days=1)                 # 직전 달 말일
    start = end.replace(day=1)
    return start, end


def firsts(start="2026-01-01", end="2026-08-01"):
    d = ddate.fromisoformat(start)
    last = ddate.fromisoformat(end)
    out = []
    while d <= last:
        out.append(d)
        d = (d.replace(day=28) + timedelta(days=7)).replace(day=1)
    return out


def build_month(pub, cfg):
    start, end = month_window(pub)
    fs, ts = str(start), str(end + timedelta(days=1))
    items = []
    with cf.ThreadPoolExecutor(max_workers=3) as ex:
        futs = [ex.submit(fetch_news, lb, lg, q, fs, ts) for lb, lg, q in QUERIES]
        futs.append(ex.submit(fetch_ted, fs, str(end), cfg["ted"]["cpv_prefixes"], 250))
        for f in futs:
            items.extend(f.result())

    items = [i for i in items if not is_blocked(i, cfg)]
    seen, uniq = set(), []
    for it in sorted(items, key=lambda x: x.get("tier", 9)):
        k = norm_title(it["title"])
        if not k or k in seen:
            continue
        seen.add(k)
        uniq.append(it)
    for it in uniq:
        score_item(it, cfg["scoring"])
    kr = cluster([i for i in uniq if i.get("region") == "국내"], cfg)
    ov = cluster([i for i in uniq if i.get("region") != "국내"], cfg)
    uniq = sorted(kr + ov, key=lambda x: (-x["score"], x.get("tier", 9)))
    return {"issue_date": str(pub), "covers": f"{fs} ~ {end}",
            "counts": {"raw": len(items), "unique": len(uniq),
                       "tender": sum(1 for i in uniq if i["kind"] == "tender")},
            "items": uniq}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    os.makedirs(OUT_DIR, exist_ok=True)
    cfg = json.load(open(os.path.join(ROOT, "system", "sources.json"), encoding="utf-8"))
    months = [ddate.fromisoformat(args.only)] if args.only else firsts()

    for i, pub in enumerate(months, 1):
        path = os.path.join(OUT_DIR, f"{pub}.json")
        if os.path.exists(path) and not args.force:
            print(f"  [{i}/{len(months)}] {pub} — 이미 있음")
            continue
        m = build_month(pub, cfg)
        json.dump(m, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        top = m["items"][0]["title"][:56] if m["items"] else "(없음)"
        print(f"  [{i}/{len(months)}] {pub} — {m['counts']['unique']:3d}건 "
              f"(공고 {m['counts']['tender']:2d}) | {top}")
        time.sleep(2)
    print("완료")


if __name__ == "__main__":
    main()
