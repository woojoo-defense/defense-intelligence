"""
SAM.gov (미국 연방조달) 수집 모듈
----------------------------------
Get Opportunities Public API 로 최근 공고를 가져와 국방 관련 건만 걸러낸다.

준비:
  1) SAM.gov 개인계정 생성 → Account Details → Public API Key 발급
  2) system/secrets.example.json 을 secrets.json 으로 복사하고 키를 붙여넣기
     (또는 환경변수 SAM_API_KEY 설정)

단독 점검:
  python system/sam.py            # 키 확인 + 실제 호출 + 결과 요약
"""

import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYS_DIR = os.path.join(ROOT, "system")
ENDPOINT = "https://api.sam.gov/opportunities/v2/search"

UA = {"User-Agent": "Mozilla/5.0 (compatible; DefenseMICE-NewsBot/1.0)",
      "Accept": "application/json"}
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

PTYPE_KO = {
    "r": "사전수요조사(Sources Sought)",
    "p": "사전공고(Presolicitation)",
    "o": "입찰공고(Solicitation)",
    "k": "통합공고(Combined Synopsis)",
    "a": "낙찰공고(Award)",
    "s": "특별공고(Special Notice)",
    "i": "묶음조달 의향(DoD)",
    "u": "수의계약 사유서(J&A)",
}

# 제품·용역 분류코드(PSC) 상위 2자리 → 한글 분야명
PSC_KO = {
    "10": "무기", "11": "핵병기", "12": "사격통제", "13": "탄약·폭발물",
    "14": "유도탄", "15": "항공기·기체구조", "16": "항공기 부품",
    "17": "항공기 지상지원", "19": "함정·소형선박", "20": "함정 장비",
    "23": "차량·트레일러", "24": "트랙터", "25": "차량 부품",
    "28": "엔진·터빈", "58": "통신·탐지·전자광학", "59": "전기·전자부품",
    "J0": "정비·수리 용역",
}


def get_api_key():
    """환경변수 → secrets.json 순으로 키를 찾는다."""
    key = os.environ.get("SAM_API_KEY", "").strip()
    if key:
        return key, "환경변수 SAM_API_KEY"
    path = os.path.join(SYS_DIR, "secrets.json")
    if os.path.exists(path):
        try:
            key = (json.load(open(path, encoding="utf-8")).get("sam_api_key") or "").strip()
            if key and not key.startswith("여기에"):
                return key, "system/secrets.json"
        except Exception as ex:
            return "", f"secrets.json 읽기 실패: {ex}"
    return "", "미설정"


CALLS_PATH = os.path.join(ROOT, "data", "sam_calls.json")
CACHE_DIR = os.path.join(ROOT, "data", "sam_cache")


def _cache_path(day=None):
    day = day or datetime.now().strftime("%Y-%m-%d")
    return os.path.join(CACHE_DIR, f"{day}.json")


def save_cache(rows):
    """API 응답 원본을 저장해 두면 필터를 고칠 때 재호출이 필요 없다."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    json.dump(rows, open(_cache_path(), "w", encoding="utf-8"), ensure_ascii=False)


def load_cache(day=None):
    p = _cache_path(day)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else []


def _budget(cfg, add=0):
    """개인 계정은 하루 10회 제한이므로 호출 수를 기록해 초과를 막는다.
    add=0이면 조회만, add=1이면 1회 사용 기록."""
    today = datetime.now().strftime("%Y-%m-%d")
    data = {}
    if os.path.exists(CALLS_PATH):
        try:
            data = json.load(open(CALLS_PATH, encoding="utf-8"))
        except Exception:
            data = {}
    used = int(data.get(today, 0))
    if add:
        data = {today: used + add}          # 당일치만 보관
        os.makedirs(os.path.dirname(CALLS_PATH), exist_ok=True)
        json.dump(data, open(CALLS_PATH, "w", encoding="utf-8"))
        used += add
    return used, cfg.get("daily_call_budget", 8)


def _call(params, timeout=60):
    url = ENDPOINT + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=UA)
    try:
        return json.loads(urllib.request.urlopen(req, timeout=timeout, context=CTX).read()), ""
    except urllib.error.HTTPError as ex:
        body = ""
        try:
            body = ex.read().decode("utf-8", "ignore")[:300]
        except Exception:
            pass
        return None, f"HTTP {ex.code} {body}"
    except Exception as ex:
        return None, f"{type(ex).__name__}: {str(ex)[:150]}"


def _rows(res):
    """응답에서 공고 배열을 찾는다(키 이름이 버전에 따라 다를 수 있어 방어적으로 처리)."""
    if not isinstance(res, dict):
        return []
    for k in ("opportunitiesData", "opportunities", "data", "results"):
        if isinstance(res.get(k), list):
            return res[k]
    for v in res.values():                       # 마지막 수단: 첫 번째 리스트
        if isinstance(v, list) and v and isinstance(v[0], dict):
            return v
    return []


# 국방 관련 연방보급분류(FSC) 그룹 — 이 두 자리에 해당해야 국방 조달로 본다
DEFENSE_FSC = {"10", "11", "12", "13", "14", "15", "16", "17", "19", "20", "22",
               "23", "24", "25", "26", "28", "29", "49", "58", "59", "60", "63",
               "66", "69", "84"}
# 무기·탄약·유도탄은 발주기관과 무관하게 국방으로 본다
HARD_FSC = {"10", "11", "12", "13", "14"}
# 장비 관련 용역코드만 허용 (J 정비, K 개조, L 기술지원, N 설치, W 임대)
SERVICE_OK = {"J", "K", "L", "N", "W"}
# PSC가 비어 있을 때 제목으로 건지기 위한 키워드
TITLE_KW = ["aircraft", "missile", "ammunition", "weapon", "armor", "vehicle",
            "radar", "artillery", "howitzer", "munition", "combat", "tank",
            "helicopter", "naval", "ship", "submarine", "night vision", "optic",
            "uav", "drone", "counter-uas", "launcher", "turret", "gun",
            # 플랫폼 이름은 품목코드가 비어 있어도 국방으로 본다
            "b-52", "b52", "f-16", "f-15", "f-35", "c-130", "kc-135", "kc-46",
            "apache", "black hawk", "blackhawk", "chinook", "abrams", "bradley",
            "stryker", "patriot", "himars", "javelin", "aegis", "ah-64", "uh-60"]
# 품목코드는 국방으로 잡히지만 실제로는 급식·행정 물자인 건을 걸러낸다
TITLE_EXCLUDE = ["food", "bakery", "milk", "beverage", "catering", "marketing",
                 "picnic", "lawn", "janitorial", "debris boom", "furniture",
                 "office supply", "in ear monitor", "musical"]


def fsc_of(psc):
    """PSC에서 연방보급분류(FSC) 두 자리를 뽑는다.
    숫자 코드(2530)는 앞 2자리, 용역 코드(J019)는 문자 뒤 2자리."""
    psc = (psc or "").strip().upper()
    if not psc:
        return "", ""
    if psc[0].isdigit():
        return psc[:2], ""
    # 용역코드는 '문자 + 0 + FSC 2자리' 구조다 (J019=함정 정비, J059=전자장비 정비)
    return psc[2:4], psc[0]


def is_defense(row, cfg):
    """국방 조달인지 판정. (판정결과, 사유) 반환.

    기관명만으로 거르면 국방부가 발주한 피크닉장 콘크리트·냉난방기까지 들어온다.
    그래서 품목분류(FSC)를 1차 기준으로 삼고, 기관은 보조 조건으로만 쓴다."""
    psc = str(row.get("classificationCode") or "").strip().upper()
    fsc, letter = fsc_of(psc)
    org = str(row.get("fullParentPathName") or "").upper()
    is_dod = any(k in org for k in cfg["agency_keywords"])
    title = (row.get("title") or "").lower()

    if any(k in title for k in TITLE_EXCLUDE):
        return False, "급식·행정 물자"
    if letter and letter not in SERVICE_OK:
        return False, "장비 외 용역"                      # R 용역, Y 공사, Q 의료 등
    if fsc in HARD_FSC:
        return True, f"무기·탄약류(FSC {fsc})"            # 기관 불문
    if fsc in DEFENSE_FSC:
        if is_dod:
            return True, f"국방품목(FSC {fsc})"
        return False, f"비국방 기관(FSC {fsc})"
    if not psc:
        if is_dod and any(k in title for k in TITLE_KW):
            return True, "품목코드 없음·제목 판정"
        return False, "품목코드 없음"
    return False, f"비국방 품목(FSC {fsc})"


def collect_sam(cfg, days=None):
    """수집기 본체. (항목 리스트, 로그문자열) 반환."""
    if not cfg.get("enabled"):
        return [], "SKIP SAM.gov (설정 비활성)"
    key, where = get_api_key()
    if not key:
        return [], "SKIP SAM.gov (API 키 미설정 — system/secrets.json 확인)"

    days = days or cfg.get("days_back", 3)
    today = datetime.now()
    frm = (today - timedelta(days=days)).strftime("%m/%d/%Y")
    to = today.strftime("%m/%d/%Y")

    used, budget = _budget(cfg)
    if used >= budget:
        return [], (f"SKIP SAM.gov (오늘 호출 {used}/{budget} 소진 — "
                    f"개인계정 일 10회 제한. 내일 자동 초기화)")

    out, errs, calls, cached = [], [], 0, []
    for pt in cfg.get("ptypes", ["r", "p"]):
        offset = 0
        for _ in range(cfg.get("max_pages", 2)):
            if used + calls >= budget:
                errs.append("일일 호출 예산 도달")
                break
            params = {"api_key": key, "postedFrom": frm, "postedTo": to,
                      "ptype": pt, "limit": cfg.get("limit", 1000), "offset": offset}
            res, err = _call(params)
            calls += 1
            _budget(cfg, add=1)
            if err:
                errs.append(f"{pt}:{err}")
                break
            rows = _rows(res)
            if not rows:
                break
            cached.extend(rows)
            for r in rows:
                ok, why = is_defense(r, cfg)
                if not ok:
                    continue
                psc = str(r.get("classificationCode") or "")
                nid = r.get("noticeId", "")
                deadline = (r.get("responseDeadLine") or "")[:16].replace("T", " ")
                poc = (r.get("pointOfContact") or [{}])[0]
                office = str(r.get("fullParentPathName") or "").split(".")[-1]
                out.append({
                    "title": (r.get("title") or "").strip()[:300],
                    "url": r.get("uiLink") or f"https://sam.gov/opp/{nid}/view",
                    "snippet": f"{office} · PSC {psc} {PSC_KO.get(psc[:2], '')}"
                               f" · NAICS {r.get('naicsCode', '')}",
                    "published": str(r.get("postedDate", "")),
                    "date": str(r.get("postedDate", ""))[:10],
                    "source": "SAM.gov (미국 연방조달)", "tier": 1,
                    "country_hint": "미국", "kind": "tender", "region": "해외",
                    "outlet": "SAM.gov", "outlet_url": "https://sam.gov",
                    "buyer": str(r.get("fullParentPathName") or "")[:160],
                    "deadline": deadline,
                    "notice_type": PTYPE_KO.get(pt, r.get("type", "")),
                    "cpv": f"PSC {psc}",
                    "set_aside": r.get("setAside") or "",
                    "poc": f"{poc.get('fullName', '')} {poc.get('email', '')}".strip(),
                    "filter_tag": why,
                })
            if len(rows) < cfg.get("limit", 1000):
                break
            offset += cfg.get("limit", 1000)

    if cached:
        save_cache(cached)
    log = (f"OK   {len(out):3d}  SAM.gov (미국 연방조달 · 원시 {len(cached)}건 → "
           f"국방 {len(out)}건 · 요청 {calls}회 · 누적 {used + calls}/{budget})")
    if errs:
        log = f"FAIL SAM.gov: {' | '.join(errs)[:120]}"
    return out, log


# ------------------------------------------------------------------ 단독 점검

def offline_test():
    """저장된 원자료로 필터만 재검증한다. API 호출 없음."""
    cfg = json.load(open(os.path.join(SYS_DIR, "sources.json"), encoding="utf-8"))["sam"]
    rows = load_cache()
    if not rows:
        print("캐시가 없습니다. 먼저 python system/sam.py 를 1회 실행하세요.")
        return
    keep, drop = [], []
    for r in rows:
        ok, why = is_defense(r, cfg)
        (keep if ok else drop).append((why, r))
    print(f"원시 {len(rows)}건 → 채택 {len(keep)}건 / 제외 {len(drop)}건" + chr(10))
    print("[채택]")
    for why, r in keep[:25]:
        print(f"  {str(r.get('classificationCode') or '-'):5s} {why[:22]:22s} "
              f"| {(r.get('title') or '')[:62]}")
    print(chr(10) + "[제외 표본]")
    seen = set()
    for why, r in drop:
        if why[:12] in seen:
            continue
        seen.add(why[:12])
        print(f"  {str(r.get('classificationCode') or '-'):5s} {why[:22]:22s} "
              f"| {(r.get('title') or '')[:62]}")


def main():
    if "--offline" in sys.argv:
        return offline_test()
    print("=" * 60)
    print(" SAM.gov 연동 점검")
    print("=" * 60)
    key, where = get_api_key()
    if not key:
        print("\n[X] API 키를 찾지 못했습니다.")
        print("    1) https://sam.gov 개인계정 생성 후 Account Details에서 Public API Key 발급")
        print("    2) system/secrets.example.json 을 secrets.json 으로 복사")
        print("    3) sam_api_key 값에 발급받은 키를 붙여넣기")
        return
    print(f"\n[OK] API 키 확인 ({where}) — {key[:6]}…{key[-4:]} (길이 {len(key)})")

    cfg = json.load(open(os.path.join(SYS_DIR, "sources.json"), encoding="utf-8"))["sam"]
    print(f"\n조회 조건: 최근 {cfg['days_back']}일 · 공고유형 "
          f"{[PTYPE_KO.get(p, p) for p in cfg['ptypes']]}")
    print("호출 중… (수 초 소요)\n")

    items, log = collect_sam(cfg)
    print(log)
    if not items:
        print("\n결과 0건. 키가 유효하지 않거나 요청 한도를 초과했을 수 있습니다.")
        print("위 오류 메시지를 그대로 알려주시면 원인을 잡겠습니다.")
        return

    print(f"\n국방 관련 공고 {len(items)}건 — 상위 15건\n")
    for it in items[:15]:
        print(f"  [{it['notice_type']}] {it['title'][:72]}")
        print(f"     발주 {it['buyer'][:60]}")
        print(f"     마감 {it['deadline'] or '-'} · {it['cpv']} · {it['url']}")
    print("\n정상 동작합니다. 이제 1_수집.bat 을 돌리면 자동으로 함께 수집됩니다.")


if __name__ == "__main__":
    main()
