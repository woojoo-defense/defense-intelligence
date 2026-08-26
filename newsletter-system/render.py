"""
방산MICE 글로벌 뉴스 - 렌더러
------------------------------
data/edition/YYYY-MM-DD.json (편집 완료본) → 두 가지 산출물

  1) 05_콘텐츠/발행/YYYY-MM-DD.html       발송용 메일 (탭 없이 순차 배치, 인라인 스타일)
  2) 05_콘텐츠/발행/YYYY-MM-DD_web.html   웹 게시용 (CSS 전용 탭, JS 없음)

메일 클라이언트는 <style>/JS를 제거하므로 탭이 동작하지 않는다.
따라서 메일에는 상단 목차(앵커 링크)를 넣고 두 탭을 이어서 배치하고,
탭 전환이 필요한 웹 게시용은 별도 파일로 만든다.

원칙: 모든 항목은 원문으로 바로 이동할 수 있어야 한다.
      제목 자체가 링크이고, 우측에 원문 버튼을 별도로 둔다.

사용법:
  python system/render.py                    # 오늘자 (메일 + 웹 동시 생성)
  python system/render.py --date 2026-08-24
"""

import argparse
import html
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from translate import ko_title, has_hangul
import json
import os
import re
import sys
from datetime import datetime, timedelta

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EDITION_DIR = os.path.join(ROOT, "data", "edition")
RAW_DIR = os.path.join(ROOT, "data", "raw")
OUT_DIR = os.path.join(ROOT, "05_콘텐츠", "발행")

C = {
    "bg": "#eef1f5", "card": "#ffffff", "navy": "#0e2a47", "navy2": "#16406b",
    "text": "#1c2b3a", "muted": "#5f7183", "line": "#dde4ec",
    "red": "#b3261e", "redbg": "#fdeceb", "blue": "#1b5e9e", "bluebg": "#eaf2fa",
    "green": "#1e6b46", "greenbg": "#e9f4ee", "amber": "#8a6100", "amberbg": "#fdf3e0",
}
FONT = ("-apple-system,BlinkMacSystemFont,'Segoe UI','Malgun Gothic','맑은 고딕',"
        "AppleSGothicNeo,'Apple SD Gothic Neo',Roboto,sans-serif")
PALETTE = {"red": (C["red"], C["redbg"]), "blue": (C["blue"], C["bluebg"]),
           "green": (C["green"], C["greenbg"]), "amber": (C["amber"], C["amberbg"]),
           "navy": (C["navy"], "#e8edf3")}


def e(s):
    return html.escape(str(s or ""))


def A(url, text, style=""):
    """모든 외부 링크는 새 창으로."""
    return (f'<a href="{e(url)}" target="_blank" rel="noopener" '
            f'style="{style}">{text}</a>')


def badge(text, tone="navy"):
    fg, bg = PALETTE.get(tone, PALETTE["navy"])
    return (f'<span style="display:inline-block;background:{bg};color:{fg};'
            f'font-size:11px;font-weight:700;padding:3px 7px;border-radius:3px;'
            f'margin:0 4px 4px 0;white-space:nowrap;">{e(text)}</span>')


def grade_tone(g):
    return {"A": "green", "B": "blue", "C": "amber", "D": "red"}.get(str(g).upper(), "navy")


def src_link(url, label="원문 보기"):
    """항목마다 반드시 붙는 원문 이동 버튼."""
    return A(url, f"{e(label)} &rsaquo;",
             f'color:{C["blue"]};font-weight:700;text-decoration:none;white-space:nowrap;')


# ------------------------------------------------------------------ 블록

def render_feature(it):
    tags = "".join(badge(t) for t in it.get("tags", []))
    if it.get("grade"):
        tags = badge(f"신뢰등급 {it['grade']}", grade_tone(it["grade"])) + tags
    if it.get("score") is not None:
        tags = badge(f"{it['score']}점", "red" if it["score"] >= 80 else "blue") + tags

    facts = "".join(
        f'<tr><td style="padding:5px 10px 5px 0;color:{C["muted"]};font-size:13px;'
        f'white-space:nowrap;vertical-align:top;width:82px;">{e(k)}</td>'
        f'<td style="padding:5px 0;color:{C["text"]};font-size:13px;font-weight:600;'
        f'vertical-align:top;">{v}</td></tr>'
        for k, v in it.get("facts", []))

    def bullets(key, label, color):
        vals = it.get(key) or []
        if not vals:
            return ""
        lis = "".join(f'<li style="margin:0 0 5px;color:{C["text"]};font-size:13.5px;'
                      f'line-height:1.62;">{v}</li>' for v in vals)
        return (f'<div style="margin:12px 0 0;"><div style="font-size:11.5px;font-weight:800;'
                f'color:{color};letter-spacing:.5px;margin-bottom:5px;">{label}</div>'
                f'<ul style="margin:0;padding-left:17px;">{lis}</ul></div>')

    why = ""
    if it.get("why"):
        why = (f'<div style="margin:12px 0 0;padding:11px 13px;background:{C["bluebg"]};'
               f'border-left:3px solid {C["blue"]};">'
               f'<div style="font-size:11.5px;font-weight:800;color:{C["blue"]};'
               f'margin-bottom:4px;">한국 기업에 주는 의미</div>'
               f'<div style="font-size:13.5px;line-height:1.65;color:{C["text"]};">'
               f'{it["why"]}</div></div>')

    title_html = A(it.get("url", "#"), e(it.get("title")),
                   f'color:{C["navy"]};text-decoration:none;')

    return f"""
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
           style="border:1px solid {C['line']};border-radius:6px;margin:0 0 14px;">
      <tr><td style="padding:16px 18px;">
        <div style="margin-bottom:8px;">{tags}</div>
        <div style="font-size:16.5px;font-weight:800;line-height:1.45;margin-bottom:10px;">
          {title_html}</div>
        <table role="presentation" cellpadding="0" cellspacing="0" width="100%"
               style="background:#f7f9fb;padding:8px 12px;border-radius:4px;">{facts}</table>
        {why}
        {bullets('targets', '유망 국내 기업·품목', C['green'])}
        {bullets('action', '지금 해야 할 일', C['red'])}
        <div style="margin-top:13px;padding-top:10px;border-top:1px solid {C['line']};
                    font-size:11.5px;color:{C['muted']};">
          출처: {e(it.get('source'))} &nbsp;·&nbsp; {src_link(it.get('url'), '원문 공고 확인')}
        </div>
      </td></tr>
    </table>"""


def render_table(items):
    head = (f'<tr style="background:{C["navy"]};">'
            + "".join(f'<th style="padding:8px 9px;color:#fff;font-size:11.5px;'
                      f'font-weight:700;text-align:left;white-space:nowrap;">{h}</th>'
                      for h in ["국가", "사업 / 품목", "단계", "마감", "원문"]) + "</tr>")
    rows = []
    for i, it in enumerate(items):
        bg = "#ffffff" if i % 2 == 0 else "#f7f9fb"
        dl_style = (f'color:{C["red"]};font-weight:800;' if it.get("urgent")
                    else f'color:{C["text"]};')
        note = (f'<div style="font-size:11.5px;color:{C["muted"]};margin-top:3px;'
                f'line-height:1.5;">{it["note"]}</div>') if it.get("note") else ""
        td = f'padding:9px;vertical-align:top;border-top:1px solid {C["line"]};'
        rows.append(
            f'<tr style="background:{bg};">'
            f'<td style="{td}font-size:12px;font-weight:700;color:{C["navy"]};'
            f'white-space:nowrap;">{e(it.get("country"))}</td>'
            f'<td style="{td}font-size:12.5px;line-height:1.5;">'
            + A(it.get("url", "#"), e(it.get("title")),
                f'color:{C["text"]};font-weight:600;text-decoration:none;')
            + f'{note}</td>'
            f'<td style="{td}font-size:11.5px;color:{C["muted"]};white-space:nowrap;">'
            f'{e(it.get("stage"))}</td>'
            f'<td style="{td}font-size:11.5px;white-space:nowrap;{dl_style}">'
            f'{e(it.get("deadline")) or "&ndash;"}</td>'
            f'<td style="{td}font-size:11.5px;">{src_link(it.get("url"), "공고")}</td></tr>')
    return (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'style="border:1px solid {C["line"]};border-radius:6px;border-collapse:separate;'
            f'overflow:hidden;margin:0 0 14px;">{head}{"".join(rows)}</table>')


def render_brief(items):
    rows = []
    for it in items:
        rows.append(
            f'<tr><td style="padding:9px 0;border-bottom:1px solid {C["line"]};">'
            f'<div style="font-size:13.5px;font-weight:700;line-height:1.5;">'
            + A(it.get("url", "#"), e(it.get("title")),
                f'color:{C["navy"]};text-decoration:none;')
            + f'</div>'
            + ((f'<div style="font-size:11px;color:{C["muted"]};margin-top:2px;">'
                f'{e(it["title_orig"])}</div>') if it.get("title_orig") else '')
            + f'<div style="font-size:12.5px;color:{C["text"]};line-height:1.6;margin-top:3px;">'
            f'{it.get("note","")}</div>'
            f'<div style="font-size:11px;color:{C["muted"]};margin-top:4px;">'
            f'{e(it.get("source"))} &nbsp;·&nbsp; {src_link(it.get("url"))}</div>'
            f'</td></tr>')
    return (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'style="margin:0 0 14px;">{"".join(rows)}</table>')


def render_scrap(items):
    """아티클 스크랩 - 제목 링크 + 매체명 + 동일 사안 타 매체 링크."""
    rows = []
    for it in items:
        others = it.get("others") or []
        others_html = ""
        if others:
            links = " · ".join(
                A(o["url"], e(o["outlet"] or "관련기사"),
                  f'color:{C["muted"]};text-decoration:none;') for o in others[:4])
            others_html = (f'<div style="font-size:11px;color:{C["muted"]};margin-top:4px;">'
                           f'같은 사안 보도: {links}</div>')
        orig = ""
        if it.get("title_orig"):
            orig = (f'<div style="font-size:11.5px;color:{C["muted"]};margin-top:2px;'
                    f'line-height:1.45;">{e(it["title_orig"])}</div>')
        note = (f'<div style="font-size:12px;color:{C["text"]};line-height:1.6;'
                f'margin-top:4px;">{it["note"]}</div>') if it.get("note") else ""
        outlet = it.get("outlet") or it.get("source") or ""
        rows.append(
            f'<tr><td style="padding:10px 0;border-bottom:1px solid {C["line"]};">'
            f'<table role="presentation" width="100%"><tr>'
            f'<td style="vertical-align:top;">'
            f'<div style="font-size:13.5px;font-weight:700;line-height:1.5;">'
            + A(it.get("url", "#"), e(it.get("title")),
                f'color:{C["navy"]};text-decoration:none;')
            + f'</div>{orig}{note}'
            f'<div style="font-size:11px;color:{C["muted"]};margin-top:4px;">'
            f'{e(outlet)}{" · " + e(it.get("date")) if it.get("date") else ""}</div>'
            f'{others_html}</td>'
            f'<td width="70" align="right" style="vertical-align:top;padding-left:8px;'
            f'font-size:11.5px;">{src_link(it.get("url"), "원문")}</td>'
            f'</tr></table></td></tr>')
    return (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'style="margin:0 0 14px;">{"".join(rows)}</table>')


def render_calendar(items):
    """전시회 캘린더 - D-day와 준비 리드타임을 함께 보여준다."""
    rows = []
    for it in items:
        dday = it.get("dday")
        if dday is None:
            tone, dtxt = "navy", "일정 미확정"
        elif dday <= 30:
            tone, dtxt = "red", f"D-{dday}"
        elif dday <= 90:
            tone, dtxt = "amber", f"D-{dday}"
        else:
            tone, dtxt = "blue", f"D-{dday}"
        fg, bg = PALETTE[tone]

        period = it.get("start", "")
        if it.get("end"):
            period = f"{it['start']} ~ {it['end'][5:]}"
        note = ""
        if it.get("note"):
            note = (f'<div style="margin-top:6px;padding:7px 9px;background:{C["amberbg"]};'
                    f'border-left:3px solid {C["amber"]};font-size:11.5px;color:{C["text"]};'
                    f'line-height:1.55;">{it["note"]}</div>')
        rows.append(
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'style="border:1px solid {C["line"]};border-radius:6px;margin:0 0 10px;">'
            f'<tr><td width="76" align="center" style="background:{bg};padding:12px 6px;'
            f'vertical-align:top;border-radius:6px 0 0 6px;">'
            f'<div style="font-size:15px;font-weight:800;color:{fg};">{e(dtxt)}</div>'
            f'<div style="font-size:10.5px;color:{fg};margin-top:3px;">{e(it.get("country"))}</div>'
            f'</td>'
            f'<td style="padding:12px 14px;">'
            f'<div style="font-size:14.5px;font-weight:800;line-height:1.45;">'
            + A(it.get("url", "#"), e(it.get("name_ko") or it.get("name")),
                f'color:{C["navy"]};text-decoration:none;')
            + f'</div>'
            f'<div style="font-size:11.5px;color:{C["muted"]};margin-top:4px;">'
            f'{e(period)} · {e(it.get("city"))} · {e(it.get("focus"))}</div>'
            f'<div style="font-size:12.5px;color:{C["text"]};line-height:1.6;margin-top:7px;">'
            f'{it.get("why", "")}</div>{note}'
            f'<div style="font-size:11px;margin-top:8px;">{src_link(it.get("url"), "공식 사이트")}'
            f'</div></td></tr></table>')
    return "".join(rows)


def load_exhibitions(cfg, today):
    """전시회 캘린더를 읽어 다가오는 순으로 정렬하고 D-day를 계산한다."""
    path = os.path.join(ROOT, "data", "exhibitions.json")
    if not os.path.exists(path):
        print("  ! data/exhibitions.json 없음")
        return []
    rows = json.load(open(path, encoding="utf-8"))["exhibitions"]
    out = []
    horizon = today + timedelta(days=30 * cfg.get("months", 18))
    for r in rows:
        try:
            start = datetime.strptime(r["start"], "%Y-%m-%d").date()
        except (KeyError, ValueError):
            continue
        end = start
        if r.get("end"):
            try:
                end = datetime.strptime(r["end"], "%Y-%m-%d").date()
            except ValueError:
                pass
        if end < today or start > horizon:      # 이미 끝났거나 너무 먼 건 제외
            continue
        r = dict(r)
        r["dday"] = (start - today).days if r.get("verified") else None
        out.append(r)
    out.sort(key=lambda x: x["start"])
    return out[:cfg.get("limit", 12)]


def resolve_tabs(tabs, date, pub_date):
    """auto 섹션(scrap·calendar)을 실제 항목으로 채운 탭 사본을 만든다.
    사이트가 React로 직접 그릴 수 있도록 JSON 직렬화 가능한 구조를 반환한다.
    중복 배제(used) 누적 순서는 render_tab_body와 동일하다."""
    used = set()
    out = []
    for t in tabs:
        secs = []
        for sec in t.get("sections", []):
            sec2 = {k: v for k, v in sec.items() if k not in ("auto",)}
            kind = sec.get("kind", "feature")
            if kind == "calendar":
                sec2["items"] = load_exhibitions(sec.get("auto", {}), pub_date)
            elif kind == "scrap":
                sec2["items"] = fill_auto(sec, date, used)
            else:
                sec2["items"] = sec.get("items", [])
                for it in sec2["items"]:
                    if it.get("url"):
                        used.add(it["url"])
            secs.append(sec2)
        t2 = {k: v for k, v in t.items() if k != "sections"}
        t2["sections"] = secs
        out.append(t2)
    return out


def export_doc(doc, tabs, date, pub_date, out_path):
    """React 뷰어용 JSON 문서를 저장한다."""
    payload = dict(doc)
    payload["tabs"] = resolve_tabs(tabs, date, pub_date)
    json.dump(payload, open(out_path, "w", encoding="utf-8"), ensure_ascii=False)


OG_SHELL = """<!doctype html>
<html lang="ko">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{title}</title>
    <meta property="og:type" content="article" />
    <meta property="og:site_name" content="방산MICE 글로벌 마켓 인텔리전스" />
    <meta property="og:title" content="{ogtitle}" />
    <meta property="og:description" content="{desc}" />
    <meta property="og:url" content="https://defense-intelligence.vercel.app/archive/{slug}" />
    <meta property="og:image" content="https://defense-intelligence.vercel.app/og/{slug}.png" />
    <meta property="og:image:width" content="1200" />
    <meta property="og:image:height" content="630" />
    <meta name="description" content="{desc}" />
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:image" content="https://defense-intelligence.vercel.app/og/{slug}.png" />
    <link rel="stylesheet" as="style" crossorigin
          href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css" />
    <link rel="stylesheet" href="/assets/app.css" />
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🛡️</text></svg>" />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/assets/app.js"></script>
  </body>
</html>
"""


def og_shell(doc, slug, out_dir):
    """카카오톡·페이스북 등 크롤러용 경로별 정적 쉘.
    크롤러는 JS를 실행하지 않으므로 OG 메타를 정적으로 박아 두고,
    실제 방문자는 같은 파일이 로드하는 SPA 번들(고정 파일명)로 앱을 본다."""
    d = datetime.strptime(doc["date"], "%Y-%m-%d")
    wd = "월화수목금토일"[d.weekday()]
    # 브라우저 탭에는 날짜를, OG 제목은 브랜드만 (날짜는 이미지가 보여준다)
    title = f"{d.year % 100:02d}.{d.month:02d}.{d.day:02d}({wd}) 방산MICE 글로벌 마켓 인텔리전스"
    og_title = "방산MICE 글로벌 마켓 인텔리전스"
    # 설명: 고정 브랜드 메시지. 카톡 카드 2줄 안에 들어가게 아주 짧게 유지
    desc = "뉴스에서 수출기회까지 — 매일 아침 발행"
    os.makedirs(out_dir, exist_ok=True)
    html_out = (OG_SHELL
                .replace("{title}", e(title))
                .replace("{ogtitle}", e(og_title))
                .replace("{desc}", e(desc))
                .replace("{slug}", slug)
                .replace("\U0001F6E1\uFE0F", "🛡️"))
    open(os.path.join(out_dir, f"{slug}.html"), "w", encoding="utf-8").write(html_out)
    # OG 이미지 (1200×630) — PIL이 없으면 조용히 건너뛴다
    try:
        from og_image import og_image as _ogimg
        tkey = ("daily" if slug.endswith("-d")
                else "monthly" if slug.endswith("-m") else "weekly")
        _ogimg(doc["date"], wd, tkey, doc.get("issue", ""),
               os.path.join(os.path.dirname(out_dir), "og", f"{slug}.png"))
    except Exception as ex:
        print(f"  [og-image 생략] {slug}: {ex}")


def section_header(sec, first=False):
    sub = (f'<div style="font-size:12px;color:{C["muted"]};margin-top:3px;">'
           f'{e(sec.get("subtitle"))}</div>') if sec.get("subtitle") else ""
    return (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'style="margin:{"0" if first else "26px"} 0 12px;">'
            f'<tr><td style="border-left:4px solid {C["navy"]};padding-left:11px;">'
            f'<div style="font-size:15px;font-weight:800;color:{C["navy"]};">'
            f'{e(sec.get("title"))}</div>{sub}</td></tr></table>')


# ------------------------------------------------------------------ 자동 채움

def fill_auto(sec, date, used_urls):
    """kind=scrap 섹션의 auto 설정에 따라 수집 원자료에서 자동으로 채운다."""
    cfg = sec.get("auto")
    if not cfg:
        return sec.get("items", [])
    raw_path = os.path.join(RAW_DIR, f"{date}.json")
    if not os.path.exists(raw_path):
        print(f"  ! 원자료 없음: {raw_path} (수집을 먼저 실행하세요)")
        return sec.get("items", [])

    raw = json.load(open(raw_path, encoding="utf-8"))["items"]
    # 스크랩은 '여러 매체가 함께 다룬 사안'이 먼저 오는 것이 자연스럽다
    raw = sorted(raw, key=lambda x: (-x.get("dupe_count", 1), -x.get("score", 0),
                                     x.get("tier", 9)))
    picked = list(sec.get("items", []))          # 수동 작성분이 항상 먼저
    for u in picked:
        used_urls.add(u.get("url"))

    for it in raw:
        if len(picked) >= cfg.get("limit", 20):
            break
        kinds = cfg.get("kinds", ["news"])
        if it.get("kind", "news") not in kinds:
            continue
        if cfg.get("region") and it.get("region") != cfg["region"]:
            continue
        if it["url"] in used_urls:
            continue
        if it.get("score", 0) < cfg.get("min_score", 0):
            continue
        kws = cfg.get("keywords")
        if kws:
            blob = f"{it.get('title','')} {it.get('snippet','')}".lower()
            if not any(k.lower() in blob for k in kws):
                continue
        used_urls.add(it["url"])
        _t = it["title"]
        _ko = ko_title(_t)
        row = {
            "title": _ko, "url": it["url"],
            "title_orig": (_t if _ko != _t else it.get("title_orig", "")) or "",
            "outlet": it.get("outlet") or it.get("source"),
            "date": it.get("date", ""), "others": it.get("others", []),
            "note": (it.get("snippet", "")[:110] + "…") if cfg.get("show_snippet")
                    and it.get("snippet") else "",
        }
        # 논문·오피니언은 부가정보를 함께 표기한다
        if it.get("kind") == "paper":
            row["outlet"] = it.get("journal") or row["outlet"]
            meta = []
            if it.get("citations"):
                meta.append(f"인용 {it['citations']}")
            meta.append("오픈액세스" if it.get("is_oa") else "유료 저널")
            if it.get("authors"):
                meta.insert(0, it["authors"][:60])
            row["note"] = " · ".join(meta)
        elif it.get("kind") == "opinion" and it.get("author"):
            row["note"] = f"필자: {it['author']}"
        picked.append(row)
    return picked


# ------------------------------------------------------------------ 조립

def render_tab_body(tab, date, used_urls):
    out = []
    today = datetime.strptime(date, "%Y-%m-%d").date()
    for i, sec in enumerate(tab.get("sections", [])):
        if sec.get("kind") == "calendar":
            items = load_exhibitions(sec.get("auto", {}), today)
        elif sec.get("kind") == "scrap":
            items = fill_auto(sec, date, used_urls)
        else:
            items = sec.get("items", [])
        if not items:
            continue
        out.append(section_header(sec, first=(i == 0)))
        kind = sec.get("kind", "feature")
        if kind == "feature":
            out.extend(render_feature(it) for it in items)
            for it in items:
                used_urls.add(it.get("url"))
        elif kind == "table":
            out.append(render_table(items))
            for it in items:
                used_urls.add(it.get("url"))
        elif kind == "calendar":
            out.append(render_calendar(items))
        elif kind == "scrap":
            out.append(render_scrap(items))
        else:
            out.append(render_brief(items))
            for it in items:
                used_urls.add(it.get("url"))
    return "".join(out), sum(1 for _ in out)


def header_block(ed, datestr):
    return f"""
  <tr><td style="background:{C['navy']};padding:20px 22px;">
    <table role="presentation" width="100%"><tr>
      <td><div style="font-size:10.5px;font-weight:700;color:#7fa8d4;letter-spacing:2.2px;">
            K-DEFENSE GLOBAL MARKET INTELLIGENCE</div>
          <div style="font-size:20px;font-weight:800;color:#fff;margin-top:5px;">
            방산MICE 글로벌 방산뉴스</div></td>
      <td align="right" style="vertical-align:bottom;">
          <div style="font-size:12px;color:#a9c6e3;font-weight:600;">{datestr}</div>
          <div style="font-size:11px;color:#7fa8d4;margin-top:3px;">
            제{e(ed.get('issue', 1))}호 · {e(ed.get('cadence', '데일리 시그널'))}</div></td>
    </tr></table>
    <div style="margin-top:12px;padding-top:10px;border-top:1px solid #2a4d73;
                font-size:11px;color:#8fb4d9;">
      디펜스엑스포 · 한국방위산업MICE협회 &nbsp;|&nbsp; 뉴스에서 수출기회까지</div>
  </td></tr>"""


def footer_block(ed):
    stats = ed.get("stats", {})
    statline = " · ".join(f"{k} {v}" for k, v in stats.items()) if stats else ""
    return f"""
  <tr><td style="background:#f7f9fb;border-top:1px solid {C['line']};padding:16px 22px;">
    <div style="font-size:11.5px;font-weight:700;color:{C['navy']};margin-bottom:6px;">
      후속지원 안내</div>
    <div style="font-size:11.5px;color:{C['muted']};line-height:1.75;">
      본 뉴스에 소개된 사업에 관심이 있으신 기업은 회신 주시면 해당 국가 KOTRA 무역관 연결,
      현지 파트너 후보 확인, 전시회·상담회 참가, 수출금융 상담을 지원해 드립니다.<br>
      관심 국가·품목을 등록하시면 해당 분야 공고를 우선 발송해 드립니다.</div>
  </td></tr>
  <tr><td style="background:{C['navy']};padding:14px 22px;">
    <div style="font-size:10.5px;color:#8fb4d9;line-height:1.8;">
      {('본 호 수집 ' + statline + '<br>') if statline else ''}
      정보 신뢰등급 &nbsp;A 해외 정부·군·조달기관 공식자료 &nbsp;|&nbsp; B 기업 공식발표·KOTRA·무관 확인
      &nbsp;|&nbsp; C 복수 전문매체 &nbsp;|&nbsp; D 단일 매체<br>
      본 뉴스는 공개된 조달공고·정부 발표·기업 보도자료를 확인해 자체 작성했으며 모든 항목에
      원문 링크를 제공합니다. 스크랩 섹션은 각 매체의 제목과 링크만 제공하며 본문을 복제하지 않습니다.
      계약 조건·자격요건은 반드시 원문 공고로 확인하시기 바랍니다.<br>
      발행 디펜스엑스포 · 한국방위산업MICE협회 &nbsp;|&nbsp; 수신거부 및 문의는 본 메일 회신</div>
  </td></tr>"""


def lead_block(ed):
    if not ed.get("lead"):
        return ""
    return (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'style="background:{C["navy2"]};border-radius:6px;margin:0 0 22px;">'
            f'<tr><td style="padding:15px 18px;">'
            f'<div style="font-size:11px;font-weight:800;color:#8fb4d9;letter-spacing:1px;'
            f'margin-bottom:6px;">{e(ed.get("lead_title", "오늘의 핵심"))}</div>'
            f'<div style="font-size:14px;line-height:1.7;color:#fff;">{ed["lead"]}</div>'
            f'</td></tr></table>')


def render_email(ed, datestr, bodies):
    """메일용: 탭 대신 목차 + 순차 배치."""
    nav = "".join(
        f'<a href="#tab-{e(t["id"])}" style="display:inline-block;background:#e8edf3;'
        f'color:{C["navy"]};font-size:12px;font-weight:700;padding:8px 14px;'
        f'border-radius:4px;margin:0 6px 6px 0;text-decoration:none;">'
        f'{i+1}. {e(t["label"])} <span style="color:{C["muted"]};font-weight:600;">'
        f'({t["count"]}건)</span></a>'
        for i, t in enumerate(bodies))

    parts = []
    for i, t in enumerate(bodies):
        parts.append(
            f'<a name="tab-{e(t["id"])}"></a><a id="tab-{e(t["id"])}"></a>'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'style="margin:{"0" if i == 0 else "34px"} 0 16px;">'
            f'<tr><td style="background:{C["navy"]};padding:11px 14px;border-radius:5px;">'
            f'<div style="font-size:14px;font-weight:800;color:#fff;">'
            f'{i+1}. {e(t["label"])}</div>'
            f'<div style="font-size:11.5px;color:#8fb4d9;margin-top:3px;">'
            f'{e(t["desc"])}</div></td></tr></table>')
        parts.append(t["html"])

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(ed.get('subject'))}</title></head>
<body style="margin:0;padding:0;background:{C['bg']};">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;">{e(ed.get('preheader',''))}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"
       style="background:{C['bg']};padding:18px 10px;">
<tr><td align="center">
<table role="presentation" width="680" cellpadding="0" cellspacing="0"
       style="width:100%;max-width:680px;background:{C['card']};border-radius:8px;
              overflow:hidden;font-family:{FONT};">
  {header_block(ed, datestr)}
  <tr><td style="padding:18px 22px 0;">
    <div style="font-size:11px;font-weight:800;color:{C['muted']};margin-bottom:7px;">
      목차</div>{nav}</td></tr>
  <tr><td style="padding:18px 22px 22px;">{lead_block(ed)}{''.join(parts)}</td></tr>
  {footer_block(ed)}
</table></td></tr></table>
</body></html>"""


def render_web(ed, datestr, bodies):
    """웹 게시용: CSS 전용 탭(JS 없음)."""
    radios = "".join(
        f'<input type="radio" name="tabs" id="r-{e(t["id"])}" '
        f'{"checked" if i == 0 else ""}>' for i, t in enumerate(bodies))
    labels = "".join(
        f'<label for="r-{e(t["id"])}" class="tab">{e(t["label"])}'
        f'<span class="cnt">{t["count"]}</span></label>' for t in bodies)
    panes = "".join(
        f'<div class="pane"><div class="pane-desc">{e(t["desc"])}</div>{t["html"]}</div>'
        for t in bodies)

    css = f"""
    body{{margin:0;background:{C['bg']};font-family:{FONT};}}
    .wrap{{max-width:760px;margin:0 auto;padding:18px 10px;}}
    .card{{background:{C['card']};border-radius:8px;overflow:hidden;}}
    input[name=tabs]{{display:none;}}
    .tabbar{{display:flex;gap:0;background:#f0f3f7;border-bottom:1px solid {C['line']};
             padding:0 12px;flex-wrap:wrap;}}
    .tab{{padding:13px 18px;font-size:13.5px;font-weight:700;color:{C['muted']};
          cursor:pointer;border-bottom:3px solid transparent;user-select:none;
          display:flex;align-items:center;gap:7px;}}
    .tab:hover{{color:{C['navy']};}}
    .cnt{{background:#dde4ec;color:{C['muted']};font-size:11px;font-weight:700;
          padding:2px 7px;border-radius:9px;}}
    .pane{{display:none;padding:22px;}}
    .pane-desc{{font-size:12.5px;color:{C['muted']};background:#f7f9fb;padding:10px 13px;
                border-radius:5px;margin-bottom:18px;line-height:1.6;}}
    """ + "".join(
        f'#r-{t["id"]}:checked ~ .tabbar label[for="r-{t["id"]}"]'
        f'{{color:{C["navy"]};border-bottom-color:{C["navy"]};background:{C["card"]};}}'
        f'#r-{t["id"]}:checked ~ .tabbar label[for="r-{t["id"]}"] .cnt'
        f'{{background:{C["navy"]};color:#fff;}}'
        f'#r-{t["id"]}:checked ~ .panes > .pane:nth-child({i+1}){{display:block;}}'
        for i, t in enumerate(bodies))

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(ed.get('subject'))}</title><style>{css}</style></head>
<body><div class="wrap"><table class="card" width="100%" cellpadding="0" cellspacing="0"
  style="border-collapse:collapse;">{header_block(ed, datestr)}</table>
<div class="card" style="border-radius:0;padding:{'18px 22px 4px' if ed.get('lead') else '0'};">
  {lead_block(ed)}</div>
<div class="card" style="border-radius:0 0 8px 8px;">
  {radios}
  <div class="tabbar">{labels}</div>
  <div class="panes">{panes}</div>
  <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
    {footer_block(ed)}</table>
</div>
<div style="text-align:center;padding:14px;font-size:11.5px;color:{C['muted']};">
  {e(ed.get('date'))} · 제{e(ed.get('issue',1))}호</div>
</div></body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    args = ap.parse_args()

    ed = json.load(open(os.path.join(EDITION_DIR, f"{args.date}.json"), encoding="utf-8"))
    tabs = ed.get("tabs") or [{"id": "main", "label": "본문", "desc": "",
                               "sections": ed.get("sections", [])}]

    d = datetime.strptime(ed["date"], "%Y-%m-%d")
    datestr = f"{d.year}년 {d.month}월 {d.day}일 ({'월화수목금토일'[d.weekday()]})"

    used = set()
    bodies = []
    for t in tabs:
        html_body, _ = render_tab_body(t, args.date, used)
        cnt = 0
        today = datetime.strptime(ed["date"], "%Y-%m-%d").date()
        for sec in t.get("sections", []):
            if sec.get("kind") == "calendar":
                cnt += len(load_exhibitions(sec.get("auto", {}), today))
            elif sec.get("kind") == "scrap":
                cnt += len(fill_auto(sec, args.date, set(used)))
            else:
                cnt += len(sec.get("items", []))
        bodies.append({"id": t["id"], "label": t["label"], "desc": t.get("desc", ""),
                       "html": html_body, "count": cnt})

    os.makedirs(OUT_DIR, exist_ok=True)
    mail_path = os.path.join(OUT_DIR, f"{args.date}.html")
    web_path = os.path.join(OUT_DIR, f"{args.date}_web.html")
    open(mail_path, "w", encoding="utf-8").write(render_email(ed, datestr, bodies))
    open(web_path, "w", encoding="utf-8").write(render_web(ed, datestr, bodies))

    print(f"[생성] 메일용 {mail_path}")
    print(f"[생성] 웹용   {web_path}")
    print(f"[제목] {ed.get('subject')}")
    for b in bodies:
        print(f"[탭] {b['label']} — {b['count']}건")


if __name__ == "__main__":
    main()
