"""
연구·오피니언 수집 모듈
------------------------
  papers   OpenAlex API — 방산·국방경제 분야 학술논문 (키 불필요)
  opinion  주요 싱크탱크·전문매체의 기고·논평 RSS

논문은 제목·초록·저널·DOI·오픈액세스 링크만 수집한다. 본문은 저장하지 않는다.
한국어 요약은 편집자가 직접 작성한다(자동 번역문을 그대로 싣지 않는다).

단독 점검:
  python system/research.py
"""

import json
import os
import ssl
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import concurrent.futures as cf
from datetime import datetime, timedelta

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
      "Accept": "application/json, application/rss+xml, application/xml;q=0.9, */*;q=0.8"}
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
ATOM = "{http://www.w3.org/2005/Atom}"


def _get(url, timeout=45):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                  timeout=timeout, context=CTX).read()


def _abstract(inv):
    """OpenAlex는 초록을 역색인(단어→위치)으로 준다. 원래 문장으로 복원한다."""
    if not inv:
        return ""
    try:
        length = max(p for ps in inv.values() for p in ps) + 1
        words = [""] * length
        for w, ps in inv.items():
            for p in ps:
                if 0 <= p < length:
                    words[p] = w
        return " ".join(x for x in words if x)
    except Exception:
        return ""


# ------------------------------------------------------------------ 논문

def collect_papers(cfg, days=None):
    """OpenAlex에서 방산·국방경제 논문을 수집한다.

    검색어는 반드시 따옴표로 묶은 구(phrase)여야 한다.
    'defense'만 넣으면 식물의 방어기작·독성학 논문이 대량으로 섞인다."""
    if not cfg.get("enabled"):
        return [], "SKIP 논문"
    since = cfg.get("from_date") or (datetime.now() - timedelta(days=cfg.get("days_back", 180))
                                     ).strftime("%Y-%m-%d")
    mail = cfg.get("mailto", "newsletter@example.org")
    seen, out, errs = set(), [], []

    # 해외 쿼리 + 국내 연구기관 소속 저자 필터를 함께 돌린다
    plans = [(q, "") for q in cfg.get("queries", [])]
    plans += [(q, ",authorships.institutions.country_code:kr")
              for q in cfg.get("kr_queries", [])]

    for q, extra in plans:
        url = ("https://api.openalex.org/works?filter=from_publication_date:" + since
               + extra
               + ",title_and_abstract.search:" + urllib.parse.quote(q)
               + f"&per-page={cfg.get('per_query', 10)}"
               + f"&sort={cfg.get('sort', 'cited_by_count:desc')}&mailto=" + mail)
        try:
            res = json.loads(_get(url))
        except Exception as ex:
            errs.append(f"{q[:18]}:{type(ex).__name__}")
            continue
        for w in res.get("results", []):
            wid = w.get("id")
            if not wid or wid in seen:
                continue
            seen.add(wid)
            src = (w.get("primary_location") or {}).get("source") or {}
            oa = w.get("open_access") or {}
            authors = [a.get("author", {}).get("display_name", "")
                       for a in (w.get("authorships") or [])][:4]
            link = oa.get("oa_url") or w.get("doi") or wid
            out.append({
                "region": "국내" if extra else "해외",
                "title": (w.get("title") or "")[:300],
                "url": link,
                "snippet": _abstract(w.get("abstract_inverted_index"))[:600],
                "published": w.get("publication_date", ""),
                "date": w.get("publication_date", ""),
                "source": "OpenAlex (학술논문)", "tier": 2,
                "country_hint": "", "kind": "paper",
                "outlet": src.get("display_name") or "학술지 미상",
                "outlet_url": "https://openalex.org",
                "journal": src.get("display_name") or "",
                "authors": ", ".join(a for a in authors if a),
                "citations": w.get("cited_by_count", 0),
                "kr_authored": bool(extra),
                "is_oa": bool(oa.get("oa_url")),
                "doi": w.get("doi") or "",
                "query": q,
            })
    out.sort(key=lambda x: (-x["citations"], x["date"]), reverse=False)
    log = f"OK   {len(out):3d}  OpenAlex 논문 (쿼리 {len(cfg.get('queries', []))}종)"
    if errs and not out:
        log = f"FAIL 논문: {' '.join(errs)[:80]}"
    return out, log


# ------------------------------------------------------------------ 오피니언

def collect_opinion(cfg, days=3):
    """싱크탱크·전문매체 기고/논평 RSS."""
    if not cfg.get("enabled"):
        return [], "SKIP 오피니언"
    cut = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    kws = [k.lower() for k in cfg.get("filter_kw", [])]

    def one(src):
        rows = []
        try:
            root = ET.fromstring(_get(src["url"], 30))
        except Exception:
            return rows
        nodes = root.findall(".//item") or root.findall(f".//{ATOM}entry")
        for n in nodes[:cfg.get("per_feed", 25)]:
            def g(tag):
                el = n.find(tag)
                return el if el is not None else n.find(ATOM + tag)

            t = g("title")
            title = (t.text or "").strip() if t is not None else ""
            le = g("link")
            link = ""
            if le is not None:
                link = (le.text or "").strip() or le.attrib.get("href", "")
            desc = ""
            for tag in ("description", "summary", "content"):
                d = g(tag)
                if d is not None and d.text:
                    import re as _re
                    desc = _re.sub(r"<[^>]+>", " ", d.text)
                    desc = " ".join(desc.split())[:500]
                    break
            au = g("creator") or g("author")
            author = ""
            if au is not None:
                author = (au.text or "").strip()
                if not author:
                    nm = au.find(ATOM + "name")
                    author = (nm.text or "").strip() if nm is not None else ""
            if not title or not link:
                continue
            if kws and not any(k in f"{title} {desc}".lower() for k in kws):
                continue
            pub = ""
            for tag in ("pubDate", "published", "updated"):
                d = g(tag)
                if d is not None and d.text:
                    pub = d.text.strip()
                    break
            rows.append({
                "title": title[:300], "url": link, "snippet": desc,
                "published": pub, "date": "",
                "source": src["name"], "tier": 2,
                "country_hint": "", "kind": "opinion", "region": "해외",
                "outlet": src["name"], "outlet_url": src["url"],
                "author": author[:80],
            })
        return rows

    out = []
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        for rows in ex.map(one, cfg.get("feeds", [])):
            out.extend(rows)
    return out, f"OK   {len(out):3d}  오피니언·기고 ({len(cfg.get('feeds', []))}개 매체)"


# ------------------------------------------------------------------ 점검

def main():
    cfg = json.load(open(os.path.join(ROOT, "system", "sources.json"), encoding="utf-8"))
    papers, log1 = collect_papers(cfg.get("papers", {}))
    print("=" * 72)
    print(log1)
    for p in papers[:12]:
        print(f"  · [{p['date']}] {p['title'][:72]}")
        print(f"    {p['journal'][:46]} | 인용 {p['citations']} | "
              f"{'오픈액세스' if p['is_oa'] else '유료'} | {p['url'][:56]}")

    ops, log2 = collect_opinion(cfg.get("opinion", {}), 5)
    print("\n" + "=" * 72)
    print(log2)
    for o in ops[:12]:
        print(f"  · [{o['outlet'][:20]}] {o['title'][:66]}")
        if o.get("author"):
            print(f"    필자: {o['author']}")


if __name__ == "__main__":
    main()
