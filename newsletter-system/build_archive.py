"""
아카이브 주간호 생성기
-----------------------
data/archive/edition/YYYY-MM-DD.json (편집본)  +  data/archive/raw/YYYY-MM-DD.json (원자료)
      → repo/public/issues/YYYY-MM-DD.html   (메일 형태 HTML)
      → repo/public/data/issues.json         (사이트 목록용 색인)

핵심 설계: 편집본은 기사 URL을 직접 적지 않고 **원자료의 인덱스(ref)만 참조**한다.
사람이 주소를 옮겨 적다 틀리는 사고를 구조적으로 없애기 위해서다.
제목·매체·마감일도 원자료에서 그대로 가져오고, 편집자는 한국어 해설만 쓴다.

편집본 형식:
{
  "date": "2026-01-12", "no": 2,
  "subject": "메일 제목",
  "lead": "리드 2~3문장",
  "features": [{"ref": 3, "ko": "한국어 제목", "why": "왜 중요한가", "action": "지금 할 일"}],
  "tenders": [{"ref": 45, "ko": "한국어 품목명", "note": "한 줄 해설"}],
  "briefs":  [{"ref": 7,  "ko": "한국어 제목", "note": "한 줄 해설"}]
}

사용법:
  python system/build_archive.py            # 전체
  python system/build_archive.py --only 2026-01-12
"""

import argparse
import glob
import json
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render as R  # noqa: E402
from translate import ko_title, ko_country  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "archive", "raw")
ED = os.path.join(ROOT, "data", "archive", "edition")
OUT = os.path.join(ROOT, "repo", "public", "issues")
IDX = os.path.join(ROOT, "repo", "public", "data", "issues.json")


def resolve(ref, items, date):
    """원자료 인덱스를 실제 항목으로 바꾼다. 범위를 벗어나면 즉시 알린다."""
    if not isinstance(ref, int) or not (0 <= ref < len(items)):
        raise IndexError(f"{date}: ref {ref} 범위 초과 (원자료 {len(items)}건)")
    return items[ref]


def build_one(ed):
    """편집본 → 뉴스레터 HTML 문자열."""
    date = ed["date"]
    raw = json.load(open(os.path.join(RAW, f"{date}.json"), encoding="utf-8"))
    items = raw["items"]

    brief_secs, global_secs = [], []

    feats = []
    for f in ed.get("features", []):
        it = resolve(f["ref"], items, date)
        facts = [["출처", f"{it.get('outlet') or it.get('source')} · {it.get('date') or ''}"]]
        if it.get("buyer"):
            facts.insert(0, ["발주기관", it["buyer"]])
        if it.get("notice_type"):
            facts.insert(0, ["사업단계", it["notice_type"]])
        if it.get("deadline"):
            facts.append(["마감", it["deadline"]])
        facts.append(["원제", it["title"]])
        feats.append({
            "score": it.get("score"), "grade": f.get("grade", "B"),
            "tags": f.get("tags", []),
            "title": f.get("ko") or it["title"],
            "facts": facts, "why": f.get("why", ""),
            "targets": f.get("targets", []), "action": f.get("action", []),
            "source": it.get("outlet") or it.get("source"), "url": it["url"],
        })
    # ---- 이번 주 주목 일정: 발행일 이후 2주 내 마감되는 공고 (원자료에서 자동)
    watch = []
    pub_d = datetime.strptime(date, "%Y-%m-%d").date()
    for it in sorted(items, key=lambda x: x.get("deadline") or "9999"):
        dl = (it.get("deadline") or "")[:10]
        if not dl or it.get("kind") != "tender":
            continue
        try:
            dd = datetime.strptime(dl, "%Y-%m-%d").date()
        except ValueError:
            continue
        if pub_d <= dd <= pub_d + timedelta(days=14):
            c = (it["title"].split("–")[0].strip()[:14] if "–" in it["title"] else "")
            watch.append({"country": ko_country(c),
                          "title": ko_title(it["title"])[:150],
                          "note": (it.get("buyer") or "")[:70],
                          "stage": it.get("notice_type", ""), "deadline": dl,
                          "urgent": dd <= pub_d + timedelta(days=7), "url": it["url"]})
        if len(watch) >= 6:
            break

    if feats:
        brief_secs.append({"kind": "feature", "title": "이번 주 핵심",
                           "subtitle": "국내 기업의 사업기회 관점에서 본 주요 움직임 — "
                                       "왜 중요한가 · 누구에게 기회인가 · 지금 할 일",
                           "items": feats})

    if watch:
        brief_secs.append({"kind": "table", "title": "이번 주 주목 일정",
                           "subtitle": "발행일 기준 2주 내 마감되는 공고 — 지금 검토해야 대응이 가능합니다",
                           "items": watch})

    tds = []
    for t in ed.get("tenders", []):
        it = resolve(t["ref"], items, date)
        country = (it["title"].split("–")[0].strip() if "–" in it["title"] else
                   it.get("country_hint") or "")
        tds.append({"country": ko_country(t.get("country") or country),
                    "title": t.get("ko") or ko_title(it["title"]),
                    "note": t.get("note", ""), "stage": it.get("notice_type", ""),
                    "deadline": (it.get("deadline") or "")[:10], "url": it["url"]})
    if tds:
        global_secs.append({"kind": "table", "title": "입찰정보",
                            "subtitle": "EU 공공조달(TED) 국방 분야 공고 중 국내 기업 대응 가능성이 있는 건 — "
                                        "제목 또는 우측 '공고'를 누르면 원문으로 이동합니다",
                            "items": tds})

    brs = []
    for b in ed.get("briefs", []):
        it = resolve(b["ref"], items, date)
        _ko = b.get("ko") or ko_title(it["title"])
        brs.append({"title": _ko,
                    "title_orig": (it["title"] if _ko != it["title"] else ""),
                    "note": b.get("note", ""),
                    "source": f"{it.get('outlet') or it.get('source')}"
                              f"{' · ' + it['date'] if it.get('date') else ''}",
                    "url": it["url"]})
    if brs:
        global_secs.append({"kind": "brief", "title": "방산정보",
                            "subtitle": "향후 사업으로 전환될 가능성이 있는 신호 — 제목을 누르면 원문으로 이동합니다",
                            "items": brs})

    # ---- 탭 구성: 주간 브리핑 / 글로벌 방산 정보 / 아티클 스크랩 / 전시회·MICE 캘린더
    tabs = [
        {"id": "brief", "label": "주간 뉴스",
         "desc": "이번 주 가장 중요한 움직임을 골라 '왜 중요한가 → 누구에게 기회인가 → 지금 무엇을 할 것인가' "
                 "순으로 정리했습니다.",
         "sections": brief_secs},
        {"id": "global", "label": "글로벌 방산 정보",
         "desc": "이번 주 해외 조달공고와 글로벌 시장·공급망 동향입니다. "
                 "마감일과 자격요건은 반드시 원문 공고로 확인하십시오.",
         "sections": global_secs},
        {"id": "scrap", "label": "방산 아티클 스크랩",
         "desc": "이번 주 수집된 국내·해외 방산 기사를 제목과 원문 링크 중심으로 모았습니다. "
                 "본문은 복제하지 않으며, 같은 사안을 여러 매체가 보도한 경우 대표기사 아래에 "
                 "타 매체 링크를 함께 제공합니다.",
         "sections": [
             {"kind": "scrap", "title": "국내 방산 아티클",
              "subtitle": "국내 매체 보도 — 제목을 누르면 원문으로 이동합니다",
              "auto": {"region": "국내", "limit": 16, "show_snippet": False}},
             {"kind": "scrap", "title": "해외 방산 아티클",
              "subtitle": "해외 매체 보도 — 원제 그대로 표기하며 매체명과 함께 원문으로 연결됩니다",
              "auto": {"region": "해외", "limit": 16, "show_snippet": False}},
             {"kind": "scrap", "title": "연구·오피니언",
              "subtitle": "학술논문과 싱크탱크 기고 — 저널명·필자와 함께 원문(DOI)으로 연결됩니다",
              "auto": {"kinds": ["paper", "opinion"], "limit": 10, "show_snippet": False}},
         ]},
        {"id": "mice", "label": "전시회·MICE 캘린더",
         "desc": "발행 시점 기준으로 다가오는 해외 방산전시회입니다. "
                 "국가관·공동관 신청은 통상 개최 4~6개월 전에 마감되므로 D-180 시점부터 검토가 필요합니다.",
         "sections": [
             {"kind": "calendar", "title": "다가오는 해외 방산전시회",
              "subtitle": "발행일 기준 D-day · 이미 끝난 행사는 자동 제외",
              "auto": {"months": 20, "limit": 8}},
             {"kind": "scrap", "title": "이번 주 전시회·상담회 소식",
              "subtitle": "수집된 기사 중 전시회·사절단·상담회 관련 건",
              "auto": {"limit": 6, "show_snippet": False,
                       "keywords": ["exhibition", "expo", "air show", "trade fair", "전시회",
                                    "상담회", "사절단", "DSEI", "IDEX", "Eurosatory", "ADEX",
                                    "MSPO", "Indo Defence", "AUSA", "Euronaval", "EDEX",
                                    "Aero India", "DSA ", "defence show", "pavilion", "국가관"]}},
         ]},
    ]

    doc = {
        "date": date, "issue": ed.get("no", 1),
        "cadence": "주간뉴스", "lead_title": "이번 주 핵심",
        "subject": ed.get("subject", ""), "preheader": ed.get("preheader", ""),
        "lead": ed.get("lead", ""),
        "stats": {"수집": f"{raw['counts']['unique']}건",
                  "조달공고": f"{raw['counts']['tender']}건",
                  "대상기간": raw["covers"]},
        "tabs": tabs,
    }
    d = datetime.strptime(date, "%Y-%m-%d")
    datestr = f"{d.year}년 {d.month}월 {d.day}일 ({'월화수목금토일'[d.weekday()]})"

    used, bodies, total = set(), [], 0
    today = d.date()
    for t in tabs:
        body, _ = R.render_tab_body(t, date, used)
        cnt = 0
        for sec in t["sections"]:
            if sec.get("kind") == "calendar":
                cnt += len(R.load_exhibitions(sec.get("auto", {}), today))
            elif sec.get("kind") == "scrap":
                cnt += len(R.fill_auto(sec, date, set(used)))
            else:
                cnt += len(sec.get("items", []))
        total += cnt
        bodies.append({"id": t["id"], "label": t["label"], "desc": t["desc"],
                       "html": body, "count": cnt})
    doc["stats"]["본 호 수록"] = f"{total}건"
    mail = R.render_email(doc, datestr, bodies)     # 발송용: 탭 없이 순차 배치
    web = R.render_web(doc, datestr, bodies)        # 웹 게시용: CSS 전용 탭
    R.export_doc(doc, tabs, date, today,
                 os.path.join(OUT, f"{date}.json"))
    R.og_shell(doc, ed["date"], os.path.join(os.path.dirname(OUT), "archive"))
    return mail, web, doc, raw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None)
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(os.path.dirname(IDX), exist_ok=True)

    # 아카이브 렌더링 시에는 원자료 경로가 다르므로 잠시 바꿔 끼운다
    R.RAW_DIR = RAW

    files = ([os.path.join(ED, f"{args.only}.json")] if args.only
             else sorted(glob.glob(os.path.join(ED, "*.json"))))
    index, errs = [], []
    for f in files:
        ed = json.load(open(f, encoding="utf-8"))
        try:
            mail, web, doc, raw = build_one(ed)
        except Exception as ex:
            errs.append(f"{ed.get('date')}: {type(ex).__name__} {ex}")
            continue
        open(os.path.join(OUT, f"{ed['date']}.html"), "w", encoding="utf-8").write(mail)
        open(os.path.join(OUT, f"{ed['date']}_web.html"), "w", encoding="utf-8").write(web)
        index.append({
            "slug": ed["date"], "type": "weekly",
            "date": ed["date"], "no": ed.get("no"),
            "subject": ed.get("subject", ""),
            "summary": ed.get("summary") or ed.get("preheader", ""),
            "covers": raw["covers"],
            "counts": {"collected": raw["counts"]["unique"],
                       "tender": raw["counts"]["tender"],
                       "published": doc["stats"].get("본 호 수록", "")},
            "tags": ed.get("tags", []),
        })
        print(f"  OK  {ed['date']}  제{ed.get('no')}호  {ed.get('subject', '')[:52]}")

    # 기존 색인의 아카이브 외 항목(데일리 등)은 보존한다
    if os.path.exists(IDX):
        try:
            built = {e["slug"] for e in index}
            for e in json.load(open(IDX, encoding="utf-8")):
                e.setdefault("slug", e["date"])
                e.setdefault("type", "weekly")
                if e["slug"] not in built:
                    index.append(e)
        except Exception:
            pass
    order = {"monthly": 0, "weekly": 1, "daily": 2}
    index.sort(key=lambda x: (x["date"], -order.get(x.get("type", "weekly"), 9)), reverse=True)
    json.dump(index, open(IDX, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\n{len(index)}개 호 생성 → {OUT}")
    print(f"색인 → {IDX}")
    if errs:
        print("\n[오류]")
        for e in errs:
            print("  !", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
