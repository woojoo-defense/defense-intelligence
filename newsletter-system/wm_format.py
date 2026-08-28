# -*- coding: utf-8 -*-
"""주간·월간 '결산' 포맷 변환 (2026-08-29 개편).

resolve된 탭(모든 섹션에 items가 채워진 상태)과 원자료를 받아
결산형 탭 구조로 재조립한다. build_archive / build_monthly 가 발행 시 호출하고,
소급 적용 스크립트(_retrofit_wm.py)도 같은 함수를 쓴다.

주간: 주간 결산(핵심+동향) / 마감 임박 입찰(2주) / 주간 베스트 아티클 / 다음 주 일정
월간: 월간 결산(하이라이트) / 타임라인 / 마감 파이프라인(1달) / 이 달의 리서치 / 다음 달 일정
"""
import json
import os
from datetime import date, timedelta

from translate import COUNTRY, flag_for, ko_country, ko_title

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(p):
    return json.load(open(p, encoding="utf-8"))


def _find(tabs, kind, title_part=None):
    for t in tabs:
        for s in t.get("sections", []):
            if s.get("kind") != kind:
                continue
            if title_part and title_part not in (s.get("title") or ""):
                continue
            return s
    return None


def _scrap_rows(raw_items, region, limit):
    rows, seen = [], set()
    ordered = sorted(raw_items, key=lambda x: (-x.get("dupe_count", 1),
                                               -(x.get("score") or 0)))
    for it in ordered:
        if it.get("kind") != "news" or it.get("region") != region:
            continue
        if it["url"] in seen:
            continue
        seen.add(it["url"])
        _t = it["title"]
        _ko = ko_title(_t)
        orig = _t if _ko != _t else ""
        if orig:
            fl = flag_for(f"{_t} {_ko}")
            orig = f"{fl} {orig}".strip()
        rows.append({"title": _ko, "title_orig": orig, "url": it["url"],
                     "outlet": it.get("outlet") or it.get("source"),
                     "date": it.get("date", ""), "others": it.get("others", []),
                     "note": ""})
        if len(rows) >= limit:
            break
    return rows


def _tender_rows(raw_items, start, end):
    rows = []
    for it in raw_items:
        if it.get("kind") != "tender" or (it.get("score") or 0) < 30:
            continue
        dl = (it.get("deadline") or "")[:10]
        if not dl or not (str(start) <= dl <= str(end)):
            continue
        t = it["title"]
        country = ""
        if "–" in t:
            head = t.split("–")[0].strip()
            if head.lower() in COUNTRY:
                country = ko_country(head)
        if not country:
            src = it.get("source") or ""
            country = ("미국" if "SAM" in src else "캐나다" if "Canada" in src
                       else "영국" if "Tender" in src else "EU")
        rows.append({"country": country, "title": ko_title(t)[:150],
                     "note": (it.get("buyer") or "")[:70],
                     "stage": it.get("notice_type", ""), "deadline": dl,
                     "urgent": dl <= str(start + timedelta(days=7)),
                     "url": it["url"]})
    rows.sort(key=lambda r: r["deadline"])
    return rows


def _events_ahead(pub, days):
    out = []
    p = os.path.join(ROOT, "data", "seminars.json")
    if os.path.exists(p):
        for ev in _load(p).get("dated", []):
            end = ev.get("end") or ev["start"]
            if end < str(pub) or ev["start"] > str(pub + timedelta(days=days)):
                continue
            it = dict(ev)
            it["dday"] = (date.fromisoformat(ev["start"]) - pub).days
            out.append(it)
    for e in _load(os.path.join(ROOT, "data", "exhibitions.json"))["exhibitions"]:
        end = e.get("end") or e["start"]
        if end < str(pub) or e["start"] > str(pub + timedelta(days=days)):
            continue
        it = dict(e)
        it["dday"] = ((date.fromisoformat(e["start"]) - pub).days
                      if e.get("verified") else None)
        out.append(it)
    out.sort(key=lambda e: e["start"])
    return out


def restructure_weekly(resolved_tabs, pub, raw_items):
    """pub: 발행일(date). raw_items: 해당 주 원자료 items."""
    feat = _find(resolved_tabs, "feature")
    watch = _find(resolved_tabs, "table", "주목")
    trends = _find(resolved_tabs, "brief", "방산정보") or _find(resolved_tabs, "brief", "동향")
    closing = _tender_rows(raw_items, pub, pub + timedelta(days=14))

    wrap_secs = []
    if feat and feat.get("items"):
        wrap_secs.append({"kind": "feature", "title": "이번 주 핵심",
                          "subtitle": "한 주를 규정한 사안 — 세부 조건은 반드시 원문으로 확인하십시오",
                          "items": feat["items"]})
    if trends and trends.get("items"):
        wrap_secs.append({"kind": "brief", "title": "그 밖의 주요 동향",
                          "subtitle": "핵심에 담지 않은 굵직한 보도",
                          "items": trends["items"]})

    tabs = [
        {"id": "wrap", "label": "주간 결산",
         "desc": "지난 한 주를 핵심 사안 중심으로 정리했습니다.",
         "sections": wrap_secs},
        {"id": "closing", "label": "마감 임박 입찰",
         "desc": "발행일로부터 2주 안에 마감되는 조달공고입니다. 자격요건은 반드시 원문으로 확인하십시오.",
         "sections": ([{"kind": "table", "title": "마감 임박 입찰",
                        "subtitle": f"2주 내 마감 {len(closing)}건 — 마감일 순, 7일 내 마감은 강조",
                        "items": closing}] if closing else [])},
        {"id": "best", "label": "주간 베스트 아티클",
         "desc": "한 주 동안 여러 매체가 함께 다룬 사안을 우선으로 골랐습니다.",
         "sections": [
             {"kind": "scrap", "title": "국내", "subtitle": "국내 매체 보도",
              "items": _scrap_rows(raw_items, "국내", 8)},
             {"kind": "scrap", "title": "해외", "subtitle": "해외 매체 보도",
              "items": _scrap_rows(raw_items, "해외", 8)}]},
        {"id": "ahead", "label": "다음 주 일정",
         "desc": "다가오는 3주의 전시회·세미나와 주목 일정입니다.",
         "sections": [
             {"kind": "calendar", "title": "다가오는 전시회·세미나",
              "subtitle": "발행일 기준 D-day", "items": _events_ahead(pub, 21)},
         ] + ([{"kind": "table", "title": watch["title"],
                "subtitle": watch.get("subtitle", ""), "items": watch["items"]}]
              if watch and watch.get("items") else [])},
    ]
    return tabs


def restructure_monthly(resolved_tabs, pub, raw_items):
    feats = []
    for t in resolved_tabs:
        for s in t.get("sections", []):
            if s.get("kind") == "feature":
                feats.extend(s.get("items", []))
    watch = _find(resolved_tabs, "table", "주목")

    # 타임라인: 일자별 최상위 신호 1건
    by_day = {}
    for it in raw_items:
        if it.get("kind") != "news" or not it.get("date"):
            continue
        d0 = it["date"]
        if d0 not in by_day or (it.get("score") or 0) > (by_day[d0].get("score") or 0):
            by_day[d0] = it
    tl = []
    for d0 in sorted(by_day):
        it = by_day[d0]
        if (it.get("score") or 0) < 20:
            continue
        _ko = ko_title(it["title"])
        fl = flag_for(f"{it['title']} {_ko}")
        tl.append({"date": f"{int(d0[5:7])}/{int(d0[8:10])}",
                   "title": _ko[:120], "url": it["url"], "note": "",
                   "source": f"{fl} {it.get('outlet') or it.get('source')}".strip()})
    tl = tl[:16]

    papers = []
    for it in sorted(raw_items, key=lambda x: -(x.get("score") or 0)):
        if it.get("kind") not in ("paper", "opinion") or len(papers) >= 10:
            continue
        _ko = ko_title(it["title"])
        orig = it["title"] if _ko != it["title"] else ""
        if orig:
            fl = flag_for(it["title"])
            orig = f"{fl} {orig}".strip()
        papers.append({"title": _ko, "title_orig": orig, "url": it["url"],
                       "note": "", "source": it.get("outlet") or it.get("source")})

    pipeline = _tender_rows(raw_items, pub, pub + timedelta(days=31))
    mname = f"{pub.month - 1 if pub.month > 1 else 12}월"
    nname = f"{pub.month}월"

    tabs = [
        {"id": "wrap", "label": "월간 결산",
         "desc": f"{mname} 한 달을 핵심 사안 중심으로 정리했습니다.",
         "sections": ([{"kind": "feature", "title": "이 달의 하이라이트",
                        "subtitle": "한 달을 규정한 사안 — 세부 조건은 반드시 원문으로 확인하십시오",
                        "items": feats}] if feats else [])},
        {"id": "timeline", "label": "타임라인",
         "desc": f"{mname} 한 달의 흐름을 날짜순으로 되짚습니다. 일자별 최상위 신호 1건씩입니다.",
         "sections": ([{"kind": "timeline", "title": f"{mname}의 타임라인",
                        "subtitle": "날짜를 따라 읽는 한 달", "items": tl}] if tl else [])},
        {"id": "pipeline", "label": "마감 파이프라인",
         "desc": "발행일로부터 한 달 안에 마감되는 조달공고입니다.",
         "sections": ([{"kind": "table", "title": f"{nname} 마감 파이프라인",
                        "subtitle": f"1개월 내 마감 {len(pipeline)}건 — 마감일 순",
                        "items": pipeline}] if pipeline else [])},
        {"id": "research", "label": "이 달의 리서치",
         "desc": f"{mname}에 나온 논문·싱크탱크 리포트 가운데 주목할 것들입니다.",
         "sections": ([{"kind": "brief", "title": "논문·리포트",
                        "subtitle": "제목을 누르면 원문으로 이동합니다",
                        "items": papers}] if papers else [])},
        {"id": "ahead", "label": "다음 달 일정",
         "desc": "다가오는 45일의 전시회·세미나 일정입니다.",
         "sections": [
             {"kind": "calendar", "title": "다가오는 전시회·세미나",
              "subtitle": "발행일 기준 D-day", "items": _events_ahead(pub, 45)},
         ] + ([{"kind": "table", "title": watch["title"],
                "subtitle": watch.get("subtitle", ""), "items": watch["items"]}]
              if watch and watch.get("items") else [])},
    ]
    return tabs
