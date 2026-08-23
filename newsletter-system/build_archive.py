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
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render as R  # noqa: E402

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

    secs = []

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
    if feats:
        secs.append({"kind": "feature", "title": "이번 주 핵심",
                     "subtitle": "국내 기업의 사업기회 관점에서 본 주요 움직임", "items": feats})

    tds = []
    for t in ed.get("tenders", []):
        it = resolve(t["ref"], items, date)
        country = (it["title"].split("–")[0].strip() if "–" in it["title"] else
                   it.get("country_hint") or "")
        tds.append({"country": t.get("country") or country,
                    "title": t.get("ko") or it["title"],
                    "note": t.get("note", ""), "stage": it.get("notice_type", ""),
                    "deadline": (it.get("deadline") or "")[:10], "url": it["url"]})
    if tds:
        secs.append({"kind": "table", "title": "이번 주 해외 조달공고",
                     "subtitle": "EU 공공조달(TED) 국방 분야 공고 중 국내 기업 대응 가능성이 있는 건",
                     "items": tds})

    brs = []
    for b in ed.get("briefs", []):
        it = resolve(b["ref"], items, date)
        brs.append({"title": b.get("ko") or it["title"],
                    "note": b.get("note", ""),
                    "source": f"{it.get('outlet') or it.get('source')}"
                              f"{' · ' + it['date'] if it.get('date') else ''}",
                    "url": it["url"]})
    if brs:
        secs.append({"kind": "brief", "title": "주요 동향",
                     "subtitle": "제목을 누르면 원문으로 이동합니다", "items": brs})

    doc = {
        "date": date, "issue": ed.get("no", 1),
        "subject": ed.get("subject", ""), "preheader": ed.get("preheader", ""),
        "lead": ed.get("lead", ""),
        "stats": {"수집": f"{raw['counts']['unique']}건",
                  "조달공고": f"{raw['counts']['tender']}건",
                  "본 호 수록": f"{len(feats) + len(tds) + len(brs)}건",
                  "대상기간": raw["covers"]},
        "tabs": [{"id": "main", "label": "주간 브리핑", "desc": "", "sections": secs}],
    }
    d = datetime.strptime(date, "%Y-%m-%d")
    datestr = f"{d.year}년 {d.month}월 {d.day}일 ({'월화수목금토일'[d.weekday()]})"
    body, _ = R.render_tab_body(doc["tabs"][0], date, set())
    bodies = [{"id": "main", "label": "주간 브리핑", "desc": "",
               "html": body, "count": len(feats) + len(tds) + len(brs)}]
    html = R.render_email(doc, datestr, bodies)
    return html, doc, raw


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
            html, doc, raw = build_one(ed)
        except Exception as ex:
            errs.append(f"{ed.get('date')}: {type(ex).__name__} {ex}")
            continue
        open(os.path.join(OUT, f"{ed['date']}.html"), "w", encoding="utf-8").write(html)
        index.append({
            "date": ed["date"], "no": ed.get("no"),
            "subject": ed.get("subject", ""),
            "summary": ed.get("summary") or ed.get("preheader", ""),
            "covers": raw["covers"],
            "counts": {"collected": raw["counts"]["unique"],
                       "tender": raw["counts"]["tender"],
                       "published": doc["stats"]["본 호 수록"]},
            "tags": ed.get("tags", []),
        })
        print(f"  OK  {ed['date']}  제{ed.get('no')}호  {ed.get('subject', '')[:52]}")

    index.sort(key=lambda x: x["date"], reverse=True)
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
