"""
아카이브 백필 — 과거 주간호 원자료 수집
----------------------------------------
2026-01-05(월)부터 매주 월요일 발행분을 만들기 위해,
각 호가 다루는 '직전 한 주'의 실제 기사·조달공고를 수집한다.

수집원 (둘 다 과거 기간 조회가 가능한 것만 사용)
  - 구글뉴스 RSS  : after:/before: 연산자로 특정 주간의 기사만 조회
  - TED (EU 조달) : publication-date 범위 지정으로 해당 주 공고 조회

지어낸 내용이 아니라 실제 그 주에 보도·공고된 것만 담는다.
결과: data/archive/raw/YYYY-MM-DD.json  (YYYY-MM-DD = 발행일=월요일)

사용법:
  python system/backfill.py                    # 전체 34주
  python system/backfill.py --from 2026-06-01  # 특정 시점 이후만
  python system/backfill.py --only 2026-01-05  # 한 주만
"""

import argparse
import json
import os
import ssl
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import concurrent.futures as cf
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect import clean, norm_title, parse_date, score_item, cluster, is_blocked  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "data", "archive", "raw")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
      "Accept": "application/rss+xml, application/json, application/xml;q=0.9, */*;q=0.8"}
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

# 주간호용 축약 쿼리 세트. 매주 돌리므로 개수를 줄여 요청량을 관리한다.
QUERIES = [
    ("K-방산", "en", '(Hanwha OR "Korea Aerospace" OR "Hyundai Rotem" OR "LIG Nex1" OR "South Korea") '
                     'defense export OR contract OR deal'),
    ("유럽조달", "en", '(Poland OR Romania OR Norway OR Finland OR Sweden OR Netherlands OR Germany) '
                      'defence procurement OR contract OR order'),
    ("중동", "en", '(Saudi OR UAE OR Qatar OR Egypt OR Kuwait) defence contract OR procurement OR deal'),
    ("아시아·태평양", "en", '(India OR Indonesia OR Malaysia OR Philippines OR Vietnam OR Australia) '
                          'defence procurement OR contract OR acquisition'),
    ("미국·NATO", "en", '(Pentagon OR "US Army" OR "US Navy" OR NATO OR NSPA) contract award OR supplier '
                        'OR "supply chain" defense'),
    ("OEM공급망", "en", '(Rheinmetall OR "BAE Systems" OR Lockheed OR RTX OR Leonardo OR Saab OR Thales) '
                       'supplier OR "supply chain" OR partnership OR order'),
    ("국내", "ko", '방산 수출 OR 방위산업 OR 방위사업청'),
]


def get(url, timeout=45, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers={**UA, **(headers or {})})
    return urllib.request.urlopen(req, timeout=timeout, context=CTX).read()


def mondays(start="2026-01-05", end=None):
    """발행일(월요일) 목록."""
    d = datetime.strptime(start, "%Y-%m-%d").date()
    last = datetime.strptime(end, "%Y-%m-%d").date() if end else datetime.now().date()
    out = []
    while d <= last:
        out.append(d)
        d += timedelta(days=7)
    return out


def fetch_news(label, lang, query, d_from, d_to, retry=2):
    """구글뉴스 기간 검색. after/before는 해당 주에 실제 보도된 기사만 돌려준다."""
    loc = "hl=ko&gl=KR&ceid=KR:ko" if lang == "ko" else "hl=en-US&gl=US&ceid=US:en"
    q = f"{query} after:{d_from} before:{d_to}"
    url = "https://news.google.com/rss/search?q=" + urllib.parse.quote(q) + "&" + loc
    for attempt in range(retry + 1):
        try:
            root = ET.fromstring(get(url, 40))
            break
        except Exception:
            if attempt == retry:
                return []
            time.sleep(2 + attempt * 2)
    rows = []
    for n in root.findall(".//item"):
        t = n.find("title")
        link = n.find("link")
        if t is None or link is None:
            continue
        title = clean(t.text, 300)
        so = n.find("source")
        outlet = (so.text or "").strip() if so is not None else ""
        if " - " in title:
            head, _, tail = title.rpartition(" - ")
            if 2 < len(tail) < 40:
                title, outlet = head, outlet or tail
        pub = n.find("pubDate")
        d = n.find("description")
        rows.append({
            "title": title, "url": (link.text or "").strip(),
            "snippet": clean(d.text if d is not None else "", 300),
            "published": (pub.text or "").strip() if pub is not None else "",
            "date": str(parse_date(pub.text if pub is not None else "") or ""),
            "source": ("구글뉴스KR/" if lang == "ko" else "구글뉴스/") + label,
            "tier": 3, "kind": "news",
            "region": "국내" if lang == "ko" else "해외",
            "outlet": outlet, "outlet_url": "", "query": label,
        })
    return rows


def fetch_ted(d_from, d_to, cpv_prefixes, limit=100):
    """TED 과거 기간 조회."""
    body = json.dumps({
        "query": (f"classification-cpv IN (35000000) AND publication-date >= "
                  f"{d_from.replace('-', '')} AND publication-date <= {d_to.replace('-', '')}"),
        "fields": ["publication-number", "notice-title", "buyer-name", "publication-date",
                   "deadline-receipt-request", "notice-type", "classification-cpv",
                   "description-lot"],
        "limit": limit, "page": 1,
    }).encode()
    try:
        res = json.loads(get("https://api.ted.europa.eu/v3/notices/search", 60, body,
                             {"Content-Type": "application/json"}))
    except Exception:
        return []
    prefixes = tuple(cpv_prefixes)
    rows = []
    for n in res.get("notices", []):
        cpvs = n.get("classification-cpv") or []
        if not any(str(c).startswith(prefixes) for c in cpvs):
            continue

        def pick(f):
            v = n.get(f)
            if isinstance(v, dict):
                if v.get("eng"):
                    x = v["eng"]
                    return x[0] if isinstance(x, list) else x
                for x in v.values():
                    return x[0] if isinstance(x, list) else x
            if isinstance(v, list):
                return v[0]
            return v or ""

        dl = n.get("deadline-receipt-request") or []
        pubno = n.get("publication-number", "")
        rows.append({
            "title": clean(pick("notice-title"), 300),
            "url": f"https://ted.europa.eu/en/notice/-/detail/{pubno}",
            "snippet": clean(pick("description-lot"), 400),
            "published": str(n.get("publication-date", "")),
            "date": str(n.get("publication-date", ""))[:10],
            "source": "TED (EU 공공조달)", "tier": 1, "kind": "tender", "region": "해외",
            "outlet": "TED", "outlet_url": "https://ted.europa.eu",
            "buyer": clean(pick("buyer-name"), 120),
            "deadline": (dl[0][:16].replace("T", " ") if dl else ""),
            "notice_type": {"cn-standard": "입찰공고", "can-standard": "낙찰공고",
                            "pin-only": "사전정보(PIN)", "pmc": "사전시장조사(PMC)"}
                           .get(n.get("notice-type", ""), n.get("notice-type", "")),
            "cpv": ",".join(sorted(set(str(c) for c in cpvs))[:5]),
        })
    return rows


def build_week(pub_date, cfg):
    """발행일(월) 기준 직전 한 주(월~일)의 자료를 모은다."""
    d_to = pub_date - timedelta(days=1)          # 직전 일요일
    d_from = pub_date - timedelta(days=7)        # 직전 월요일
    fs, ts = d_from.strftime("%Y-%m-%d"), (d_to + timedelta(days=1)).strftime("%Y-%m-%d")

    items = []
    with cf.ThreadPoolExecutor(max_workers=4) as ex:
        futs = [ex.submit(fetch_news, lb, lg, q, fs, ts) for lb, lg, q in QUERIES]
        futs.append(ex.submit(fetch_ted, fs, d_to.strftime("%Y-%m-%d"),
                              cfg["ted"]["cpv_prefixes"]))
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
    return {
        "issue_date": pub_date.strftime("%Y-%m-%d"),
        "covers": f"{fs} ~ {d_to.strftime('%Y-%m-%d')}",
        "counts": {"raw": len(items), "unique": len(uniq),
                   "tender": sum(1 for i in uniq if i["kind"] == "tender")},
        "items": uniq,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="frm", default="2026-01-05")
    ap.add_argument("--to", dest="to", default=None)
    ap.add_argument("--only", default=None)
    ap.add_argument("--force", action="store_true", help="이미 받은 주도 다시 받기")
    args = ap.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    cfg = json.load(open(os.path.join(ROOT, "system", "sources.json"), encoding="utf-8"))
    days = ([datetime.strptime(args.only, "%Y-%m-%d").date()] if args.only
            else mondays(args.frm, args.to))

    print(f"백필 대상 {len(days)}주 ({days[0]} ~ {days[-1]})\n")
    for i, d in enumerate(days, 1):
        path = os.path.join(OUT_DIR, f"{d}.json")
        if os.path.exists(path) and not args.force:
            print(f"  [{i:2d}/{len(days)}] {d} — 이미 있음, 건너뜀")
            continue
        wk = build_week(d, cfg)
        json.dump(wk, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        top = wk["items"][0]["title"][:56] if wk["items"] else "(없음)"
        print(f"  [{i:2d}/{len(days)}] {d} — {wk['counts']['unique']:3d}건 "
              f"(공고 {wk['counts']['tender']:2d}) | {top}")
        time.sleep(1.5)                          # 구글뉴스 과부하 방지
    print(f"\n완료. {OUT_DIR}")


if __name__ == "__main__":
    main()
