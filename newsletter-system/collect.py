"""
방산MICE 글로벌 뉴스 - 수집기
--------------------------------
공개 RSS / 구글뉴스 타깃쿼리 / TED(EU 공공조달 API)에서 항목을 모아
중복 제거 → 자동 사전채점 → data/raw/YYYY-MM-DD.json 으로 저장한다.

원칙 (저작권 준수):
  - 기사 본문을 저장하지 않는다. 제목 / 요약 스니펫(피드가 공개한 범위) / URL / 발행일 / 출처만 저장.
  - 유료·로그인 콘텐츠는 수집하지 않는다.
  - 최종 기사는 이 원자료를 보고 사람이 자체 문장으로 작성한다.

사용법:
  python system/collect.py                 # 오늘자 수집
  python system/collect.py --days 2        # 최근 2일치 대상
  python system/collect.py --no-dedupe-history   # 과거 발행분 중복제거 끄기
"""

import argparse
import concurrent.futures as cf
import html
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sam import collect_sam                      # 미국 연방조달(SAM.gov) — API 키 있을 때만 동작
from portals import collect_canada, collect_poland, collect_uk   # 주요국 조달포털(키 불필요)
from research import collect_papers, collect_opinion             # 학술논문·오피니언

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYS_DIR = os.path.join(ROOT, "system")
DATA_DIR = os.path.join(ROOT, "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
SEEN_PATH = os.path.join(DATA_DIR, "seen.json")

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
      "Accept": "application/rss+xml, application/atom+xml, application/xml;q=0.9, */*;q=0.8",
      "Accept-Language": "en-US,en;q=0.9"}
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
ATOM = "{http://www.w3.org/2005/Atom}"


# ---------------------------------------------------------------- 공통 유틸

def fetch(url, data=None, headers=None, timeout=30):
    req = urllib.request.Request(url, data=data, headers={**UA, **(headers or {})})
    return urllib.request.urlopen(req, timeout=timeout, context=CTX).read()


def clean(text, limit=400):
    """HTML 태그 제거 + 공백 정리."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def norm_title(t):
    """중복 판정용 제목 정규화."""
    t = re.sub(r"[^a-z0-9가-힣]+", "", (t or "").lower())
    return t[:90]


def parse_date(s):
    """RSS/Atom의 다양한 날짜 포맷 → date 객체 (실패 시 None)."""
    if not s:
        return None
    s = s.strip()
    fmts = ["%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z",
            "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"]
    for f in fmts:
        try:
            return datetime.strptime(s.replace("GMT", "+0000"), f).date()
        except ValueError:
            continue
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))).date()
    return None


# ---------------------------------------------------------------- 수집기

def collect_rss(src):
    """일반 RSS/Atom 피드 수집."""
    out = []
    try:
        root = ET.fromstring(fetch(src["url"]))
    except Exception as e:
        return out, f"FAIL {src['name']}: {type(e).__name__} {str(e)[:60]}"

    nodes = root.findall(".//item") or root.findall(f".//{ATOM}entry")
    for n in nodes:
        def g(tag):
            el = n.find(tag)
            if el is None:
                el = n.find(ATOM + tag)
            return el

        t = g("title")
        title = clean(t.text if t is not None else "", 300)
        link_el = g("link")
        link = ""
        if link_el is not None:
            link = (link_el.text or "").strip() or link_el.attrib.get("href", "")
        desc = ""
        for tag in ("description", "summary", "content"):
            d = g(tag)
            if d is not None and d.text:
                desc = clean(d.text)
                break
        pub = ""
        for tag in ("pubDate", "published", "updated", "date"):
            d = g(tag)
            if d is not None and d.text:
                pub = d.text.strip()
                break
        if not title or not link:
            continue
        # 종합지 피드는 방산 기사만 골라낸다 (filter_kw가 있을 때만)
        fkw = src.get("filter_kw")
        if fkw and not any(k.lower() in f"{title} {desc}".lower() for k in fkw):
            continue
        # 구글뉴스는 <source> 태그로 실제 매체명·도메인을 제공한다
        so = n.find("source")
        outlet = (so.text or "").strip() if so is not None else ""
        outlet_url = so.attrib.get("url", "") if so is not None else ""
        out.append({
            "title": title, "url": link, "snippet": desc,
            "published": pub, "date": str(parse_date(pub) or ""),
            "source": src["name"], "tier": src["tier"],
            "country_hint": src.get("country", ""), "kind": "news",
            "region": src.get("region", "해외"),
            "outlet": outlet, "outlet_url": outlet_url,
        })
    return out, f"OK   {len(out):3d}  {src['name']}"


def collect_google_news(item, days=3):
    """구글뉴스 RSS 타깃 쿼리. region이 '국내'면 한국어 로케일로 조회."""
    kr = item.get("region") == "국내"
    loc = "hl=ko&gl=KR&ceid=KR:ko" if kr else "hl=en-US&gl=US&ceid=US:en"
    url = ("https://news.google.com/rss/search?q="
           + urllib.parse.quote(f"{item['q']} when:{days}d") + "&" + loc)
    src = {"name": ("구글뉴스KR/" if kr else "구글뉴스/") + item["label"],
           "tier": 3, "url": url, "country": "한국" if kr else "",
           "region": item.get("region", "해외")}
    rows, log = collect_rss(src)
    for r in rows:
        # 구글뉴스 제목은 "제목 - 매체명" 형태 → 매체명을 제목에서 분리
        if " - " in r["title"]:
            head, _, tail = r["title"].rpartition(" - ")
            if 2 < len(tail) < 40:
                r["title"] = head
                r["outlet"] = r.get("outlet") or tail
        r["query"] = item["label"]
    return rows, log


def collect_ted(cfg):
    """TED(EU 공공조달) API. 무료·키 불필요. 국방 CPV만 필터링."""
    out = []
    if not cfg.get("enabled"):
        return out, "SKIP TED"
    payload = {
        "query": f"classification-cpv IN (35000000) AND publication-date >= today(-{cfg['days_back']})",
        "fields": ["publication-number", "notice-title", "buyer-country", "buyer-name",
                   "publication-date", "deadline-receipt-request", "notice-type",
                   "classification-cpv", "description-lot"],
        "limit": cfg.get("limit", 100), "page": 1,
    }
    try:
        res = json.loads(fetch("https://api.ted.europa.eu/v3/notices/search",
                               data=json.dumps(payload).encode(),
                               headers={"Content-Type": "application/json"}, timeout=45))
    except Exception as e:
        return out, f"FAIL TED: {type(e).__name__} {str(e)[:80]}"

    prefixes = tuple(cfg["cpv_prefixes"])
    for n in res.get("notices", []):
        cpvs = n.get("classification-cpv") or []
        if not any(str(c).startswith(prefixes) for c in cpvs):
            continue  # 방산 아닌 일반 보안·감시 장비 제외

        def pick(field):
            v = n.get(field)
            if isinstance(v, dict):
                for lang in ("eng", "ENG"):
                    if v.get(lang):
                        x = v[lang]
                        return x[0] if isinstance(x, list) else x
                for x in v.values():
                    return x[0] if isinstance(x, list) else x
            if isinstance(v, list):
                return v[0]
            return v or ""

        title = clean(pick("notice-title"), 300)
        deadlines = n.get("deadline-receipt-request") or []
        ntype = n.get("notice-type", "")
        pubno = n.get("publication-number", "")
        out.append({
            "title": title,
            "url": f"https://ted.europa.eu/en/notice/{pubno}",
            "snippet": clean(pick("description-lot"), 400),
            "published": str(n.get("publication-date", "")),
            "date": str(n.get("publication-date", ""))[:10],
            "source": "TED (EU 공공조달)", "tier": 1,
            "country_hint": "", "kind": "tender", "region": "해외",
            "outlet": "TED (EU 공공조달)", "outlet_url": "https://ted.europa.eu",
            "buyer": clean(pick("buyer-name"), 120),
            "deadline": (deadlines[0][:16].replace("T", " ") if deadlines else ""),
            "notice_type": {"cn-standard": "입찰공고", "can-standard": "낙찰공고",
                            "cn-social": "입찰공고", "can-social": "낙찰공고",
                            "cn-desg": "설계공모", "pin-only": "사전정보(PIN)",
                            "pin-tran": "사전정보(PIN)", "pin-buyer": "사전정보(PIN)",
                            "pmc": "사전시장조사(PMC)",
                            "corr": "정정공고", "veat": "수의계약 사전공고"}.get(ntype, ntype),
            "cpv": ",".join(sorted(set(str(c) for c in cpvs))[:6]),
        })
    return out, f"OK   {len(out):3d}  TED (EU 공공조달, 국방 CPV 필터 후)"


# ---------------------------------------------------------------- 필터·군집

def is_blocked(item, cfg):
    """기계번역·수집형 매체, 방산과 무관한 사건사고·주가 기사 제외."""
    outlet = (item.get("outlet") or "").lower()
    for b in cfg.get("blocklist_outlets", []):
        if b.lower() and b.lower() in outlet:
            return True
    title = item.get("title", "")
    return any(k in title for k in cfg.get("blocklist_title_kw", []))


def tokens(title):
    """제목에서 2글자 이상 토큰 추출(한글 조사 일부 제거)."""
    raw = re.sub(r"[^0-9A-Za-z가-힣]+", " ", (title or "")).split()
    out = set()
    for w in raw:
        w = w.lower()
        if re.match(r"^[가-힣]+$", w) and len(w) > 2:
            w = re.sub(r"(은|는|이|가|을|를|에|의|와|과|으로|로|에서|에게|까지|부터)$", "", w)
        if len(w) >= 2:
            out.add(w)
    return out


def cluster(items, cfg, threshold=0.38):
    """같은 사건을 다룬 기사를 하나로 묶는다.
    비교 기준은 '대표기사의 토큰'으로 고정한다(누적하면 연쇄 병합이 일어나 과다 통합됨).
    결과: 대표기사 1건 + others(다른 매체 원문 링크)."""
    pref = {o.lower(): i for i, o in enumerate(cfg.get("preferred_outlets", []))}

    def rank(x):
        """대표기사 선정 순위: 주요매체 → 점수 → 공식출처 → 제목 길이."""
        o = (x.get("outlet") or x.get("source") or "").lower()
        p = min([i for k, i in pref.items() if k in o], default=99)
        return (p, -x.get("score", 0), x.get("tier", 9), len(x["title"]))

    groups = []
    for it in items:
        tk = tokens(it["title"])
        if not tk:
            groups.append({"tokens": tk, "members": [it]})
            continue
        placed = False
        for g in groups:
            inter = len(tk & g["tokens"])
            if inter < 2:
                continue
            union = len(tk | g["tokens"]) or 1
            contain = inter / (min(len(tk), len(g["tokens"])) or 1)
            if inter / union >= threshold or (inter >= 3 and contain >= 0.62):
                g["members"].append(it)
                placed = True
                break
        if not placed:
            groups.append({"tokens": tk, "members": [it]})   # 토큰 누적하지 않음

    out = []
    for g in groups:
        rep = dict(sorted(g["members"], key=rank)[0])
        rep["others"] = [{"outlet": m.get("outlet") or m.get("source"), "url": m["url"]}
                         for m in sorted(g["members"], key=rank) if m["url"] != rep["url"]][:5]
        rep["dupe_count"] = len(g["members"])
        out.append(rep)
    return out


# ---------------------------------------------------------------- 채점

_KW_RE = {}


def kw_match(kw, text):
    """키워드가 낱말 단위로 들어있는지 확인한다.

    단순 포함 검사는 오탐이 난다. 예를 들어 'oman'은 R-oman-ia에,
    'india'는 Indiana에 걸린다. 앞뒤에 영문자가 붙지 않는 경우만 인정한다."""
    kw = kw.strip()
    if not kw:
        return False
    if not kw.isascii():                       # 한글 키워드는 그대로 포함 검사
        return kw in text
    rx = _KW_RE.get(kw)
    if rx is None:
        rx = _KW_RE[kw] = re.compile(
            "(?<![a-z0-9])" + re.escape(kw) + "(?![a-z])", re.I)
    return bool(rx.search(text))


def score_item(item, scoring):
    """자동 사전채점(0~100). 발행 여부의 '후보 정렬'용이지 발행 결정이 아니다."""
    text = (f"{item.get('title','')} {item.get('snippet','')} "
            f"{item.get('buyer','')} {item.get('notice_type','')}").lower()
    total, hits = 0, []
    for key, rule in scoring.items():
        matched = [k for k in rule["kw"] if kw_match(k, text)]
        if matched:
            total += rule["weight"]
            hits.append(f"{key}({len(matched)})")
    if item.get("tier") == 1:
        total += 10
        hits.append("공식출처(+10)")
    if item.get("kind") == "tender" and item.get("deadline"):
        total += 10
        hits.append("마감일확인(+10)")
    item["score"] = max(0, min(100, total))
    item["score_tags"] = hits
    return item


# ---------------------------------------------------------------- 메인

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=3, help="최근 N일 이내 항목만 채택")
    ap.add_argument("--no-dedupe-history", action="store_true")
    args = ap.parse_args()

    os.makedirs(RAW_DIR, exist_ok=True)
    cfg = json.load(open(os.path.join(SYS_DIR, "sources.json"), encoding="utf-8"))

    tasks = []
    with cf.ThreadPoolExecutor(max_workers=12) as ex:
        for s in cfg["rss"]:
            tasks.append(ex.submit(collect_rss, s))
        for g in cfg["google_news"]:
            tasks.append(ex.submit(collect_google_news, g, args.days))
        for g in cfg.get("google_news_kr", []):
            tasks.append(ex.submit(collect_google_news, g, args.days))
        tasks.append(ex.submit(collect_ted, cfg["ted"]))
        if cfg.get("sam"):
            tasks.append(ex.submit(collect_sam, cfg["sam"], args.days))
        pt = cfg.get("portals", {})
        for key, fn in (("canada", collect_canada), ("poland", collect_poland),
                        ("uk", collect_uk)):
            if pt.get(key):
                tasks.append(ex.submit(fn, pt[key], args.days))
        if cfg.get("papers"):
            tasks.append(ex.submit(collect_papers, cfg["papers"], args.days))
        if cfg.get("opinion"):
            tasks.append(ex.submit(collect_opinion, cfg["opinion"], max(args.days, 7)))

        items, logs = [], []
        for f in cf.as_completed(tasks):
            rows, log = f.result()
            items.extend(rows)
            logs.append(log)

    print("[수집 결과]")
    for l in sorted(logs):
        print("  " + l)

    # --- 기간 필터
    cutoff = (datetime.now(timezone.utc) - timedelta(days=args.days)).date()
    fresh = []
    for it in items:
        if it.get("kind") in ("paper", "opinion"):
            fresh.append(it)              # 논문·논평은 발행 주기가 길어 기간 필터를 적용하지 않는다
            continue
        d = parse_date(it.get("date") or it.get("published"))
        if d is None or d >= cutoff:      # 날짜 파싱 실패분은 살려둔다
            fresh.append(it)

    # --- 중복 제거 (같은 회차 내 + 과거 발행분)
    seen_hist = {}
    if os.path.exists(SEEN_PATH):
        seen_hist = json.load(open(SEEN_PATH, encoding="utf-8"))
    seen_keys = set() if args.no_dedupe_history else set(seen_hist.keys())

    uniq, batch_keys = [], set()
    for it in sorted(fresh, key=lambda x: x.get("tier", 9)):   # 공식출처 우선 보존
        k = norm_title(it["title"])
        if not k or k in batch_keys or k in seen_keys:
            continue
        batch_keys.add(k)
        uniq.append(it)

    # --- 블록리스트 제외
    blocked = [it for it in uniq if is_blocked(it, cfg)]
    uniq = [it for it in uniq if not is_blocked(it, cfg)]

    # --- 채점
    for it in uniq:
        score_item(it, cfg["scoring"])

    # --- 유사기사 군집화 (국내/해외 각각) → 스크랩 목록의 중복 제거
    special = [i for i in uniq if i.get("kind") in ("paper", "opinion")]
    rest = [i for i in uniq if i.get("kind") not in ("paper", "opinion")]
    kr = cluster([i for i in rest if i.get("region") == "국내"], cfg)
    ov = cluster([i for i in rest if i.get("region") != "국내"], cfg)
    uniq = kr + ov + special
    uniq.sort(key=lambda x: (-x["score"], x.get("tier", 9)))

    today = datetime.now().strftime("%Y-%m-%d")
    out_path = os.path.join(RAW_DIR, f"{today}.json")
    json.dump({"collected_at": datetime.now().isoformat(timespec="seconds"),
               "counts": {"raw": len(items), "fresh": len(fresh), "unique": len(uniq)},
               "items": uniq},
              open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # --- seen 갱신 (30일 보관)
    for it in uniq:
        seen_hist[norm_title(it["title"])] = today
    keep_after = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    seen_hist = {k: v for k, v in seen_hist.items() if v >= keep_after}
    json.dump(seen_hist, open(SEEN_PATH, "w", encoding="utf-8"), ensure_ascii=False)

    # --- 편집자용 다이제스트(마크다운) 동시 생성
    dg = [f"# 수집 다이제스트 {today}",
          f"원시 {len(items)} / 기간내 {len(fresh)} / 중복제거 {len(uniq)}" + chr(10)]
    for i, it in enumerate(uniq[:80]):
        head = (f"### [{i}] {it['score']}점 · {it.get('region','해외')} · {it['source']}"
                + (f" · {it['outlet']}" if it.get("outlet") else ""))
        if it["kind"] == "tender":
            head += (f" · 발주 {it.get('buyer','')[:50]}"
                     f" · {it.get('notice_type','')} · 마감 {it.get('deadline','') or '-'}")
        dg.append(head)
        dg.append(f"**{it['title']}**"
                  + (f"  _(외 {it['dupe_count']-1}개 매체)_" if it.get("dupe_count", 1) > 1 else ""))
        if it.get("snippet"):
            dg.append(f"> {it['snippet']}")
        dg.append(f"{it['url']}" + chr(10))
    open(os.path.join(RAW_DIR, f"{today}_digest.md"), "w",
         encoding="utf-8").write(chr(10).join(dg))

    tenders = sum(1 for i in uniq if i["kind"] == "tender")
    print(f"\n[요약] 원시 {len(items)}건 → 기간내 {len(fresh)}건 → 중복제거 {len(uniq)}건 "
          f"(조달공고 {tenders}건)")
    print(f"[저장] {out_path}")
    print(f"[저장] {os.path.join(RAW_DIR, today + '_digest.md')}  ← 편집용 다이제스트")
    print("\n[상위 12건 미리보기]")
    for it in uniq[:12]:
        print(f"  {it['score']:3d} | {it['source'][:22]:22s} | {it['title'][:70]}")


if __name__ == "__main__":
    main()
