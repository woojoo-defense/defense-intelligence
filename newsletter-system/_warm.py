# -*- coding: utf-8 -*-
"""전체 호 제목 번역 캐시 워밍 — 진행 출력 + 40건마다 저장."""
import json, glob, sys, time
sys.path.insert(0, "system")
sys.stdout.reconfigure(encoding="utf-8")
from translate import ko_title, save_cache, has_hangul, _load

titles = []
for f in glob.glob("repo/public/issues/*.json"):
    d = json.load(open(f, encoding="utf-8"))
    for t in d.get("tabs", []):
        for sec in t.get("sections", []):
            if sec.get("kind") in ("table", "brief", "scrap"):
                for it in sec.get("items", []):
                    ti = it.get("title", "")
                    if ti and not has_hangul(ti):
                        titles.append(ti.strip())

uniq = [t for t in dict.fromkeys(titles) if t not in _load()]
print(f"번역 대상: {len(uniq)}건", flush=True)

start = time.time()
for i, t in enumerate(uniq, 1):
    ko_title(t)
    if i % 40 == 0:
        save_cache()
        el = time.time() - start
        eta = el / i * (len(uniq) - i)
        print(f"  {i}/{len(uniq)}  경과 {el/60:.1f}분  남은 예상 {eta/60:.1f}분", flush=True)
save_cache()
print(f"완료: {len(uniq)}건 (총 {(time.time()-start)/60:.1f}분)", flush=True)
