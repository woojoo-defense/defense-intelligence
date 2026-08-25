# -*- coding: utf-8 -*-
"""일일뉴스 생성기 — 2026-08-01부터 매일 1개 호.

새로 수집하지 않는다. 이미 확보된 주간 원자료(data/archive/raw/{월요일}.json,
각각 직전 월~일 7일치를 담고 있음)를 날짜별로 잘라 그날의 신호만 담는다.
2026-08-24·25는 자체 데일리 원자료(data/raw/)를 쓴다.

일간호의 성격: '데일리 시그널'. 그날 실제로 잡힌 신호를 선별·정리하고,
상위 신호가 주제 지식베이스(daily_topics)에 매칭되면 해설 카드 1~2건을 구성한다.
매칭이 없으면 해설 없이 신호만 싣는다 — 억지 해설보다 생략이 낫다.

산출:
  repo/public/issues/{date}-d.html / {date}-d_web.html
  색인(issues.json)에 type:"daily", slug:"{date}-d" 항목 병합

사용법:
  python system/build_daily.py                 # 1/1 ~ 어제까지 전체
  python system/build_daily.py --only 2026-03-14
"""

import argparse
import glob
import json
import os
import sys
from datetime import date as ddate, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render as R  # noqa: E402
from daily_topics import match_topic  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEEK_RAW = os.path.join(ROOT, "data", "archive", "raw")
DAY_RAW = os.path.join(ROOT, "data", "raw")
SLICE_DIR = os.path.join(ROOT, "data", "archive", "raw_daily")
OUT = os.path.join(ROOT, "repo", "public", "issues")
IDX = os.path.join(ROOT, "repo", "public", "data", "issues.json")

START = ddate(2026, 8, 1)
TITLES_PATH = os.path.join(ROOT, "data", "archive", "daily_titles.json")


def load_titles():
    """한글 제목 오버라이드(subject·해설 카드 제목). 없으면 빈 dict."""
    if os.path.exists(TITLES_PATH):
        try:
            return json.load(open(TITLES_PATH, encoding="utf-8"))
        except Exception:
            pass
    return {}


def weekly_file_for(day):
    """day(어제 뉴스 기준일)를 커버하는 주간 원자료의 발행일(월요일)을 찾는다.
    월요일 P의 파일은 P-7..P-1을 커버한다."""
    monday_after = day + timedelta(days=(7 - day.weekday()) % 7 or 7)
    return os.path.join(WEEK_RAW, f"{monday_after}.json")


def load_slice(pub):
    """발행일 pub의 일간호가 다루는 '전일(pub-1)' 신호를 원자료에서 잘라낸다."""
    target = pub - timedelta(days=1)
    own = os.path.join(DAY_RAW, f"{pub}.json")
    if os.path.exists(own):                      # 8/24·25처럼 자체 수집분이 있는 날
        items = json.load(open(own, encoding="utf-8"))["items"]
        return [i for i in items], str(target)
    wf = weekly_file_for(target)
    if not os.path.exists(wf):
        return None, str(target)
    items = json.load(open(wf, encoding="utf-8"))["items"]
    day_items = [i for i in items if i.get("date") == str(target)]
    # 날짜 없는 항목 중 논문·오피니언은 발행 주기가 느슨하므로 월·목요일에만 소량 배분
    if pub.weekday() in (0, 3):
        extras = [i for i in items if not i.get("date")
                  and i.get("kind") in ("paper", "opinion")][:6]
        day_items += extras
    return day_items, str(target)


def parse_country(it):
    t = it.get("title", "")
    if "–" in t:
        return t.split("–")[0].strip()[:14]
    return (it.get("country_hint") or "")[:14]


def build_lead(pub, items, tenders):
    y = pub - timedelta(days=1)
    parts = [f"{y.month}월 {y.day}일 하루 동안 잡힌 신호 <b>{len(items)}건</b>을 정리했습니다."]
    if tenders:
        soon = [t for t in tenders if t.get("deadline")]
        parts.append(f"조달공고는 <b>{len(tenders)}건</b>"
                     + (f", 이 중 마감일이 확인된 공고가 {len(soon)}건입니다." if soon else "입니다."))
    top = items[0] if items else None
    if top:
        tp = match_topic(f"{top.get('title', '')} {top.get('snippet', '')}")
        if tp:
            parts.append(f"오늘의 상위 신호는 <b>{tp['name']}</b> 관련 움직임입니다.")
    return " ".join(parts)


def build_one(pub, no, titles=None):
    ov = (titles or {}).get(str(pub), {})
    items, covers = load_slice(pub)
    if items is None:
        return None, f"원자료 없음 ({covers})"
    items = sorted(items, key=lambda x: (-x.get("score", 0), x.get("tier", 9)))
    news = [i for i in items if i.get("kind") == "news"]
    tenders = [i for i in items if i.get("kind") == "tender"]

    # ---- 해설 카드: 상위 신호 중 주제 매칭되는 것 1~2건 (뉴스·조달 각 1건까지)
    feats, used_urls = [], set()
    for pool in (news[:6], tenders[:4]):
        for it in pool:
            tp = match_topic(f"{it.get('title', '')} {it.get('snippet', '')} {it.get('buyer', '')}")
            if not tp or it.get("score", 0) < 30:
                continue
            facts = [["출처", f"{it.get('outlet') or it.get('source')} · {it.get('date') or covers}"]]
            if it.get("buyer"):
                facts.insert(0, ["발주기관", it["buyer"][:90]])
            if it.get("notice_type"):
                facts.insert(0, ["사업단계", it["notice_type"]])
            if it.get("deadline"):
                facts.append(["마감", it["deadline"]])
            facts.append(["원제", it["title"]])
            ko_list = ov.get("feats", [])
            ko_title = ko_list[len(feats)] if len(feats) < len(ko_list) else None
            feats.append({
                "score": it.get("score"), "grade": "A" if it.get("tier") == 1 else "C",
                "tags": tp["tags"],
                "title": (f"[{tp['name']}] {ko_title}" if ko_title
                          else f"[{tp['name']}] " + it["title"][:120]),
                "facts": facts, "why": tp["why"],
                "targets": tp["targets"], "action": tp["action"],
                "source": it.get("outlet") or it.get("source"), "url": it["url"],
            })
            used_urls.add(it["url"])
            break                                    # 풀당 1건
    feats = feats[:2]

    brief_secs = []
    if feats:
        brief_secs.append({"kind": "feature", "title": "오늘의 신호 해설",
                           "subtitle": "상위 신호를 주제 관점에서 해설합니다 — 세부 조건은 반드시 원문으로 확인하십시오",
                           "items": feats})

    # ---- 입찰정보
    tds = []
    for it in tenders[:9]:
        tds.append({"country": parse_country(it), "title": it["title"][:150],
                    "note": (it.get("buyer") or "")[:70],
                    "stage": it.get("notice_type", ""),
                    "deadline": (it.get("deadline") or "")[:10],
                    "urgent": bool(it.get("deadline")
                                   and (it["deadline"][:10] <= str(pub + timedelta(days=10)))),
                    "url": it["url"]})
    global_secs = []
    if tds:
        global_secs.append({"kind": "table", "title": "입찰정보",
                            "subtitle": "전일 게시된 국방 조달공고 — 제목 또는 우측 '공고'를 누르면 원문으로 이동합니다",
                            "items": tds})

    # ---- 방산정보 (상위 뉴스, 해설 카드에 쓴 건 제외)
    brs = []
    for it in news:
        if it["url"] in used_urls or len(brs) >= 6:
            continue
        brs.append({"title": it["title"][:160], "note": "",
                    "source": f"{it.get('outlet') or it.get('source')}"
                              f"{' · ' + it['date'] if it.get('date') else ''}",
                    "url": it["url"]})
        used_urls.add(it["url"])
    if brs:
        global_secs.append({"kind": "brief", "title": "방산정보",
                            "subtitle": "전일의 주요 보도 — 제목을 누르면 원문으로 이동합니다",
                            "items": brs})

    # ---- 슬라이스를 임시 raw로 저장 (스크랩 auto가 읽는다)
    os.makedirs(SLICE_DIR, exist_ok=True)
    key = str(pub)
    json.dump({"issue_date": key, "covers": covers,
               "counts": {"unique": len(items),
                          "tender": len(tenders)},
               "items": items},
              open(os.path.join(SLICE_DIR, f"{key}.json"), "w", encoding="utf-8"),
              ensure_ascii=False)

    tabs = [
        {"id": "brief", "label": "데일리 뉴스",
         "desc": "전일 수집된 신호 중 가장 중요한 것을 골라 주제 관점의 해설과 함께 정리했습니다.",
         "sections": brief_secs},
        {"id": "global", "label": "글로벌 방산 정보",
         "desc": "전일의 조달공고와 시장 동향입니다. 마감일과 자격요건은 반드시 원문 공고로 확인하십시오.",
         "sections": global_secs},
        {"id": "scrap", "label": "방산 아티클 스크랩",
         "desc": "전일 수집된 국내·해외 방산 기사입니다. 본문은 복제하지 않으며 모든 항목이 원문으로 연결됩니다.",
         "sections": [
             {"kind": "scrap", "title": "국내 방산 아티클",
              "subtitle": "국내 매체 보도 — 제목을 누르면 원문으로 이동합니다",
              "auto": {"region": "국내", "limit": 12, "show_snippet": False}},
             {"kind": "scrap", "title": "해외 방산 아티클",
              "subtitle": "해외 매체 보도 — 매체명과 함께 원문으로 연결됩니다",
              "auto": {"region": "해외", "limit": 12, "show_snippet": False}},
             {"kind": "scrap", "title": "연구·오피니언",
              "subtitle": "학술논문과 싱크탱크 기고",
              "auto": {"kinds": ["paper", "opinion"], "limit": 6, "show_snippet": False}},
         ]},
        {"id": "mice", "label": "전시회·MICE 캘린더",
         "desc": "발행 시점 기준으로 다가오는 방산전시회입니다.",
         "sections": [
             {"kind": "calendar", "title": "다가오는 방산전시회",
              "subtitle": "발행일 기준 D-day · 지난 행사는 자동 제외",
              "auto": {"months": 20, "limit": 6}},
         ]},
    ]

    subject = f"[방산MICE 데일리] {pub.month}/{pub.day} — "
    if ov.get("subject"):
        subject += ov["subject"]
    elif feats:
        subject += feats[0]["title"][:52]
    elif tds:
        subject += f"신규 조달공고 {len(tds)}건"
    else:
        subject += f"신호 {len(items)}건 정리"

    doc = {"date": key, "issue": no,
           "cadence": "일일뉴스", "lead_title": "오늘의 핵심",
           "subject": subject, "preheader": "",
           "lead": build_lead(pub, items, tenders),
           "stats": {"수집": f"{len(items)}건", "조달공고": f"{len(tenders)}건",
                     "대상일": covers},
           "tabs": tabs}

    d = datetime.combine(pub, datetime.min.time())
    datestr = f"{d.year}년 {d.month}월 {d.day}일 ({'월화수목금토일'[d.weekday()]})"
    used, bodies, total = set(), [], 0
    for t in tabs:
        body, _ = R.render_tab_body(t, key, used)
        cnt = 0
        for sec in t["sections"]:
            if sec.get("kind") == "calendar":
                cnt += len(R.load_exhibitions(sec.get("auto", {}), pub))
            elif sec.get("kind") == "scrap":
                cnt += len(R.fill_auto(sec, key, set(used)))
            else:
                cnt += len(sec.get("items", []))
        total += cnt
        bodies.append({"id": t["id"], "label": t["label"], "desc": t["desc"],
                       "html": body, "count": cnt})
    doc["stats"]["본 호 수록"] = f"{total}건"
    mail = R.render_email(doc, datestr, bodies)
    web = R.render_web(doc, datestr, bodies)

    entry = {"slug": f"{key}-d", "type": "daily", "date": key, "no": no,
             "subject": doc["subject"].replace("[방산MICE 데일리] ", ""),
             "summary": (f"{covers} 신호 {len(items)}건 · 조달공고 {len(tenders)}건"
                         + (f" · 해설 {len(feats)}건" if feats else "")),
             "covers": f"{covers} (일간)",
             "counts": {"collected": len(items), "tender": len(tenders),
                        "published": f"{total}건"},
             "tags": (feats[0]["tags"][:3] if feats else [])}
    return (mail, web, entry), None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None)
    ap.add_argument("--to", default=None, help="이 날짜까지 (기본: 데이터가 있는 마지막 날)")
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    R.RAW_DIR = SLICE_DIR                       # 스크랩 auto가 슬라이스를 읽도록

    end = (datetime.strptime(args.to, "%Y-%m-%d").date() if args.to
           else datetime.now().date())
    days = ([datetime.strptime(args.only, "%Y-%m-%d").date()] if args.only
            else [START + timedelta(days=i) for i in range((end - START).days + 1)])

    titles = load_titles()
    entries, skipped = [], []
    for pub in days:
        no = (pub - START).days + 1
        res, err = build_one(pub, no, titles)
        if err:
            skipped.append((str(pub), err))
            continue
        mail, web, entry = res
        open(os.path.join(OUT, f"{pub}-d.html"), "w", encoding="utf-8").write(mail)
        open(os.path.join(OUT, f"{pub}-d_web.html"), "w", encoding="utf-8").write(web)
        entries.append(entry)
        if no % 30 == 0 or args.only:
            print(f"  … {pub} (제{no}호) 까지 생성")

    # ---- 색인 병합 (slug 기준)
    idx = []
    if os.path.exists(IDX):
        try:
            idx = json.load(open(IDX, encoding="utf-8"))
        except Exception:
            idx = []
    for e in idx:                                # 구버전 항목에 slug/type 보정
        e.setdefault("slug", e["date"])
        e.setdefault("type", "weekly")
    have = {e["slug"] for e in entries}
    idx = [e for e in idx if e["slug"] not in have] + entries
    order = {"monthly": 0, "weekly": 1, "daily": 2}
    idx.sort(key=lambda x: (x["date"], -order.get(x.get("type", "weekly"), 9)), reverse=True)
    json.dump(idx, open(IDX, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print(f"\n일간호 {len(entries)}건 생성 (색인 총 {len(idx)}건)")
    if skipped:
        print(f"건너뜀 {len(skipped)}건: {skipped[:5]}")


if __name__ == "__main__":
    main()
