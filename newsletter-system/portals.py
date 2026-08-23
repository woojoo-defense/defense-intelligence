"""
주요국 조달포털 수집 모듈 (API 키 불필요)
------------------------------------------
TED(EU)·SAM.gov(미국)로 덮이지 않는 국가별 포털을 보완한다.

  canada  CanadaBuys 공개데이터 CSV   — 캐나다 국방부(DND) 등 전체 공개 입찰
  poland  e-Zamówienia Board API      — 폴란드 국내(EU 기준액 미만) 공고. TED에 안 올라오는 건
  uk      Find a Tender Service OCDS  — 영국 고액 공고(국방부·잠수함사업단·Dstl 포함)

단독 점검:
  python system/portals.py            # 세 곳 모두 호출해 결과 요약
"""

import csv
import io
import re
import json
import os
import ssl
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
      "Accept": "application/json, text/csv, application/xml, */*"}
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def _get(url, timeout=90):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                  timeout=timeout, context=CTX).read()


def _cutoff(days):
    return (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")


# ------------------------------------------------------------------ 캐나다

CA_ENTITY_KW = ["national defence", "defence construction", "canadian forces",
                "canadian coast guard", "royal canadian"]
CA_TITLE_KW = ["defence", "military", "weapon", "ammunition", "armour", "armor",
               "aircraft", "naval", "ship", "submarine", "radar", "vehicle",
               "spares", "sonar", "missile", "combat", "surveillance"]


def collect_canada(cfg, days=3):
    """CanadaBuys 공개 입찰공고 CSV. 캐나다 국방부(DND) 물량이 상시 150건 이상."""
    if not cfg.get("enabled"):
        return [], "SKIP 캐나다"
    try:
        raw = _get(cfg["url"], 150).decode("utf-8-sig", "ignore")
    except Exception as ex:
        return [], f"FAIL 캐나다: {type(ex).__name__} {str(ex)[:60]}"

    cut = _cutoff(days)
    out = []
    for r in csv.DictReader(io.StringIO(raw)):
        if (r.get("publicationDate-datePublication") or "")[:10] < cut:
            continue
        entity = r.get("contractingEntityName-nomEntitContractante-eng", "")
        if any(k in entity.lower() for k in ("mounted police", "parks canada",
                                             "correctional", "border services")):
            continue
        title = r.get("title-titre-eng", "")
        blob = f"{entity} {title} {r.get('unspscDescription-eng', '')}".lower()
        if not (any(k in entity.lower() for k in CA_ENTITY_KW)
                or any(k in blob for k in CA_TITLE_KW)):
            continue

        sol = r.get("solicitationNumber-numeroSollicitation", "")
        url = (r.get("noticeURL-URLavis-eng") or "").strip()
        if not url:
            # 국방부 공고는 CSV에 직접 링크가 없어 공고번호 검색 주소로 연결한다
            url = ("https://canadabuys.canada.ca/en/tender-opportunities?search_filter="
                   + urllib.parse.quote(sol))
        out.append({
            "title": title[:300],
            "url": url,
            "snippet": (r.get("unspscDescription-eng", "") or "").replace("*", " ").strip()[:300],
            "published": r.get("publicationDate-datePublication", ""),
            "date": (r.get("publicationDate-datePublication") or "")[:10],
            "source": "CanadaBuys (캐나다 조달)", "tier": 1,
            "country_hint": "캐나다", "kind": "tender", "region": "해외",
            "outlet": "CanadaBuys", "outlet_url": "https://canadabuys.canada.ca",
            "buyer": entity[:160],
            "deadline": (r.get("tenderClosingDate-appelOffresDateCloture") or "")[:16].replace("T", " "),
            "notice_type": r.get("noticeType-avisType-eng", ""),
            "cpv": f"공고번호 {sol}",
        })
    return out, f"OK   {len(out):3d}  CanadaBuys (캐나다 조달)"


# ------------------------------------------------------------------ 폴란드

def collect_poland(cfg, days=3):
    """폴란드 e-Zamówienia. 키워드 검색이 정확도가 높아 품목 키워드로 조회한다.
    (EU 기준액 미만 국내 공고라 TED에는 올라오지 않는다)"""
    if not cfg.get("enabled"):
        return [], "SKIP 폴란드"
    cut = _cutoff(days)
    base = ("https://ezamowienia.gov.pl/mo-board/api/v1/Board/Search"
            "?SortingColumnName=PublicationDate&SortingDirection=DESC"
            "&PageNumber=1&PageSize=10&OrderObject=")
    seen, out, errs = set(), [], []
    for kw in cfg.get("keywords", []):
        try:
            rows = json.loads(_get(base + urllib.parse.quote(kw), 45))
        except Exception as ex:
            errs.append(f"{kw}:{type(ex).__name__}")
            continue
        for r in rows if isinstance(rows, list) else []:
            no = r.get("noticeNumber") or r.get("bzpNumber") or r.get("moIdentifier")
            if not no or no in seen:
                continue
            if (r.get("publicationDate") or "")[:10] < cut:
                continue
            cpv = str(r.get("cpvCode") or "")
            if not cpv.startswith(tuple(cfg.get("cpv_prefixes", ["35"]))):
                continue          # 군 부대의 급식·시설·도로 발주 제외
            url_pdf = (r.get("pdfUrl") or "").strip()
            if "ted.europa.eu" in url_pdf:
                continue          # TED 게재분은 EU 수집기가 이미 가져온다
            seen.add(no)
            mo = r.get("moIdentifier") or ""
            url = (r.get("pdfUrl") or "").strip() or \
                  ("https://ezamowienia.gov.pl/mp-client/search/list/" + mo if mo
                   else "https://ezamowienia.gov.pl/mp-client/tenders/list")
            out.append({
                "title": (r.get("orderObject") or "")[:300],
                "url": url,
                "snippet": f"{r.get('noticeTypeDisplayName') or ''} · "
                           f"{'EU 기준액 미만' if r.get('isTenderAmountBelowEU') else 'EU 기준액 이상'}",
                "published": r.get("publicationDate", ""),
                "date": (r.get("publicationDate") or "")[:10],
                "source": "e-Zamówienia (폴란드 조달)", "tier": 1,
                "country_hint": "폴란드", "kind": "tender", "region": "해외",
                "outlet": "e-Zamówienia", "outlet_url": "https://ezamowienia.gov.pl",
                "buyer": (r.get("organizationName") or "")[:160],
                "deadline": (r.get("submittingOffersDate") or "")[:16].replace("T", " "),
                "notice_type": r.get("noticeTypeDisplayName") or "",
                "cpv": f"CPV {r.get('cpvCode') or '-'}",
                "search_kw": kw,
            })
    log = f"OK   {len(out):3d}  e-Zamówienia (폴란드, 키워드 {len(cfg.get('keywords', []))}종)"
    if errs and not out:
        log = f"FAIL 폴란드: {' '.join(errs)[:90]}"
    return out, log


# ------------------------------------------------------------------ 영국

# 짧은 약어(AWE, DIO, DE&S)는 단어 경계로 맞춰야 한다.
# "awe "를 단순 포함으로 검사하면 Wyth-enshawe 같은 지명에 오탐이 난다.
UK_BUYER_RE = re.compile(
    r"\b(defence|ministry of defence|dstl|submarine delivery|"
    r"royal navy|royal air force|british army|awe|dio|de&s)\b", re.I)


def collect_uk(cfg, days=3):
    """영국 Find a Tender Service(OCDS). 서버측 품목 필터가 없어
    발주기관명·CPV로 직접 걸러낸다. 국방 비중은 낮지만 국방부 공고가 여기로 나온다."""
    if not cfg.get("enabled"):
        return [], "SKIP 영국"
    url = ("https://www.find-tender.service.gov.uk/api/1.0/ocdsReleasePackages"
           f"?updatedFrom={_cutoff(days)}T00:00:00&limit=100")
    out, pages, total = [], 0, 0
    while url and pages < cfg.get("max_pages", 6):
        try:
            res = json.loads(_get(url, 60))
        except Exception as ex:
            return out, f"FAIL 영국: {type(ex).__name__} {str(ex)[:60]}"
        pages += 1
        rel = res.get("releases", [])
        total += len(rel)
        for x in rel:
            t = x.get("tender") or {}
            buyer = ((x.get("buyer") or {}).get("name") or "")
            cpvs = []
            for lot in (t.get("lots") or []):
                for it in (lot.get("items") or []):
                    if it.get("classification"):
                        cpvs.append(str(it["classification"].get("id", "")))
                    for a in (it.get("additionalClassifications") or []):
                        cpvs.append(str(a.get("id", "")))
            for it in (t.get("items") or []):
                if it.get("classification"):
                    cpvs.append(str(it["classification"].get("id", "")))
            hit_buyer = bool(UK_BUYER_RE.search(buyer))
            hit_cpv = any(c.startswith(tuple(cfg.get("cpv_prefixes",
                       ["353", "354", "355", "356", "357", "358", "359"])))
                          for c in cpvs)
            if not (hit_buyer or hit_cpv):
                continue
            out.append({
                "title": (t.get("title") or "")[:300],
                "url": f"https://www.find-tender.service.gov.uk/Notice/{x.get('id', '')}",
                "snippet": (t.get("description") or "")[:300],
                "published": x.get("date", ""),
                "date": str(x.get("date", ""))[:10],
                "source": "Find a Tender (영국 조달)", "tier": 1,
                "country_hint": "영국", "kind": "tender", "region": "해외",
                "outlet": "Find a Tender", "outlet_url": "https://www.find-tender.service.gov.uk",
                "buyer": buyer[:160],
                "deadline": ((t.get("tenderPeriod") or {}).get("endDate")
                             or "")[:16].replace("T", " "),
                "notice_type": t.get("procurementMethodDetails") or t.get("status") or "",
                "cpv": ("CPV " + cpvs[0]) if cpvs else "",
            })
        url = (res.get("links") or {}).get("next")
    return out, f"OK   {len(out):3d}  Find a Tender (영국, {pages}p/{total}건 중)"


# ------------------------------------------------------------------ 점검

def main():
    cfg = json.load(open(os.path.join(ROOT, "system", "sources.json"),
                         encoding="utf-8")).get("portals", {})
    for name, fn in (("canada", collect_canada), ("poland", collect_poland), ("uk", collect_uk)):
        items, log = fn(cfg.get(name, {}), 3)
        print("\n" + "=" * 70)
        print(log)
        for it in items[:8]:
            print(f"  · [{it.get('notice_type', '')[:18]}] {it['title'][:64]}")
            print(f"    {it['buyer'][:50]} | 마감 {it.get('deadline') or '-'} | {it['cpv'][:24]}")
            print(f"    {it['url'][:96]}")


if __name__ == "__main__":
    main()
