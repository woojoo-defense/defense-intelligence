# -*- coding: utf-8 -*-
"""제목 한글화 계층.

원칙:
  - 이미 한글이 포함된 제목은 건드리지 않는다.
  - 번역 결과는 data/translations.json 에 캐시되어 재빌드 시 안정적이다.
  - 기계번역 후 방산 용어 교정표(GLOSSARY)를 적용한다.
  - 원제는 항상 title_orig 로 보존되어 화면에 병기된다.

TED 공고 제목("Country – CPV영문 – 현지어원문")은 국가·품목을 사전으로 옮기고
현지어 원문 부분만 기계번역해 정확도를 높인다.
"""

import json
import os
import re
import ssl
import threading
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_PATH = os.path.join(ROOT, "data", "translations.json")

_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE
_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0 Safari/537.36"}
_LOCK = threading.Lock()

_cache = None


def _load():
    global _cache
    if _cache is None:
        if os.path.exists(CACHE_PATH):
            try:
                _cache = json.load(open(CACHE_PATH, encoding="utf-8"))
            except Exception:
                _cache = {}
        else:
            _cache = {}
    return _cache


def save_cache():
    with _LOCK:
        if _cache is not None:
            json.dump(_cache, open(CACHE_PATH, "w", encoding="utf-8"),
                      ensure_ascii=False, indent=0)


COUNTRY = {
    "poland": "폴란드", "norway": "노르웨이", "finland": "핀란드", "sweden": "스웨덴",
    "denmark": "덴마크", "germany": "독일", "france": "프랑스", "italy": "이탈리아",
    "spain": "스페인", "portugal": "포르투갈", "belgium": "벨기에",
    "netherlands": "네덜란드", "austria": "오스트리아", "switzerland": "스위스",
    "romania": "루마니아", "bulgaria": "불가리아", "czechia": "체코",
    "czech republic": "체코", "slovakia": "슬로바키아", "slovenia": "슬로베니아",
    "hungary": "헝가리", "croatia": "크로아티아", "greece": "그리스",
    "estonia": "에스토니아", "latvia": "라트비아", "lithuania": "리투아니아",
    "ireland": "아일랜드", "luxembourg": "룩셈부르크", "malta": "몰타",
    "cyprus": "키프로스", "iceland": "아이슬란드", "ukraine": "우크라이나",
    "united kingdom": "영국", "uk": "영국", "united states": "미국", "usa": "미국",
    "canada": "캐나다", "australia": "호주", "india": "인도",
    "indonesia": "인도네시아", "malaysia": "말레이시아", "philippines": "필리핀",
    "vietnam": "베트남", "thailand": "태국", "singapore": "싱가포르",
    "japan": "일본", "taiwan": "대만", "south korea": "한국",
    "saudi arabia": "사우디", "uae": "UAE", "qatar": "카타르", "oman": "오만",
    "kuwait": "쿠웨이트", "egypt": "이집트", "israel": "이스라엘",
    "turkey": "튀르키예", "türkiye": "튀르키예", "brazil": "브라질", "peru": "페루",
    "미 육군": "미 육군", "미 공군": "미 공군", "미 해군": "미 해군",
}

GLOSSARY = [
    ("자주식 곡사포", "자주포"), ("자체 추진 곡사포", "자주포"), ("자주 곡사포", "자주포"),
    ("견인 곡사포", "견인포"), ("곡사포", "자주포"),
    ("잠수함", "잠수함"), ("호위함", "호위함"),
    ("입찰", "입찰"), ("조달", "조달"),
    ("탄약", "탄약"), ("군용", "군용"),
    ("공군", "공군"), ("육군", "육군"), ("해군", "해군"),
    ("방위군", "방위군"), ("무인 항공기", "무인기"), ("드론", "드론"),
    ("로켓 발사기", "로켓 발사대"), ("유탄 발사기", "유탄발사기"),
    ("소총", "소총"), ("기관총", "기관총"),
    ("防衛", "방위"),
    ("한화 에어로스페이스", "한화에어로스페이스"),
    ("현대 로템", "현대로템"), ("현대로 템", "현대로템"),
    ("케이 방위", "K-방산"), ("K 방위", "K-방산"),
    ("천무 로켓", "천무"), ("천궁 II", "천궁-II"), ("청궁", "천궁"),
    ("검색된 출처:", "사전수요조사:"), ("검색된 소스:", "사전수요조사:"),
    ("소스 소트", "사전수요조사"), ("억 건의", "억 달러 규모의"),
    ("조 건의", "조 규모의"), ("백만 건의", "백만 달러 규모의"),
    ("입찰 요청", "입찰공고"), ("제안 요청", "제안요청(RFP)"),
    ("정보 요청", "정보요청(RFI)"), ("프레임워크 계약", "기본협약"),
    ("프레임 워크", "기본협약"), ("록히드 마틴", "록히드마틴"),
    ("보 잉", "보잉"), ("라인 메탈", "라인메탈"), ("라인메탈", "라인메탈"),
]

_HANGUL = re.compile(r"[가-힣]")


def has_hangul(text):
    return bool(_HANGUL.search(text or ""))


_THROTTLE = threading.Semaphore(3)


def _mt(text, sl="auto"):
    """구글 번역(dict-chrome-ex). 429 백오프 포함. 실패 시 원문 반환."""
    import time
    if not text or not text.strip():
        return text
    url = ("https://clients5.google.com/translate_a/t?client=dict-chrome-ex"
           f"&sl={sl}&tl=ko&q=" + urllib.parse.quote(text[:400]))
    for attempt in range(4):
        with _THROTTLE:
            try:
                raw = urllib.request.urlopen(
                    urllib.request.Request(url, headers=_UA),
                    timeout=20, context=_CTX).read()
                data = json.loads(raw)
                # 형식: ["번역"] 또는 [["번역","감지언어"]]
                out = data[0]
                if isinstance(out, list):
                    out = out[0]
                time.sleep(0.25)
                return (out or "").strip() or text
            except urllib.error.HTTPError as ex:
                if ex.code == 429:
                    time.sleep(4 + attempt * 4)
                    continue
                return text
            except Exception:
                time.sleep(1.0)
    return text


def _postfix(text):
    for a, b in GLOSSARY:
        text = text.replace(a, b)
    # 흔한 어색함 정리
    text = re.sub(r"\s+", " ", text).strip()
    text = text.replace(" - ", " — ")
    return text


def ko_country(name):
    n = (name or "").strip()
    return COUNTRY.get(n.lower(), n)


def ko_title(text):
    """제목 한글화(캐시 우선). 한글 포함 제목은 그대로 둔다."""
    if not text or has_hangul(text):
        return text
    cache = _load()
    key = text.strip()
    with _LOCK:
        if key in cache:
            return cache[key]
    # TED형: "Country – CPV – native"
    parts = [p.strip() for p in key.split("–")]
    if len(parts) >= 2 and parts[0].lower() in COUNTRY:
        country = COUNTRY[parts[0].lower()]
        mid = _postfix(_mt(parts[1]))
        tail = ""
        if len(parts) >= 3 and parts[2]:
            tail = _postfix(_mt(" – ".join(parts[2:])))
            if tail and tail != mid:
                tail = " — " + tail[:90]
            else:
                tail = ""
        out = f"{country}: {mid}{tail}"
    else:
        out = _postfix(_mt(key))
    with _LOCK:
        cache[key] = out
    return out


def warm(titles, workers=6):
    """제목 목록을 병렬로 미리 번역해 캐시를 채운다."""
    import concurrent.futures as cf
    todo = [t for t in dict.fromkeys(titles) if t and not has_hangul(t)
            and t.strip() not in _load()]
    if not todo:
        return 0
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(ko_title, todo))
    save_cache()
    return len(todo)
