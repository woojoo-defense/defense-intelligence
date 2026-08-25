# -*- coding: utf-8 -*-
"""내보낸 문서(repo/public/issues/*.json)의 링크를 검증한다.
사용: python system/_verify_doc.py 2026-08-26-d [raw날짜]"""
import json, os, sys
sys.path.insert(0, "system")
sys.stdout.reconfigure(encoding="utf-8")
from verify import check, BUILT_URL_HOSTS
import concurrent.futures as cf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
slug = sys.argv[1]
raw_date = sys.argv[2] if len(sys.argv) > 2 else slug.replace("-d", "").replace("-m", "")

doc = json.load(open(os.path.join(ROOT, "repo", "public", "issues", f"{slug}.json"),
                     encoding="utf-8"))

known = set()
for base in ("raw", os.path.join("archive", "raw"), os.path.join("archive", "raw_monthly")):
    p = os.path.join(ROOT, "data", base, f"{raw_date}.json")
    if os.path.exists(p):
        for it in json.load(open(p, encoding="utf-8"))["items"]:
            known.add(it["url"])
            for o in it.get("others", []) or []:
                known.add(o["url"])

urls = []
for t in doc.get("tabs", []):
    for s in t.get("sections", []):
        for it in s.get("items", []):
            for u in [it.get("url")] + [o.get("url") for o in it.get("others", []) or []]:
                if u:
                    urls.append((t["id"], (it.get("title") or "")[:40], u))

seen, todo, skipped = set(), [], 0
for w, ti, u in urls:
    if u in seen:
        continue
    seen.add(u)
    if u in known and not any(h in u for h in BUILT_URL_HOSTS):
        skipped += 1
    else:
        todo.append((w, ti, u))

print(f"{slug}: 링크 {len(seen)}건 — 원자료 일치 {skipped}건 통과, 접속 확인 {len(todo)}건")
bad = []
with cf.ThreadPoolExecutor(max_workers=3) as ex:
    futs = {ex.submit(check, u): (w, ti, u) for w, ti, u in todo}
    for f in cf.as_completed(futs):
        w, ti, u = futs[f]
        code, err = f.result()
        if not (code and 200 <= code < 400):
            bad.append((w, ti, u, code, err))
if bad:
    for w, ti, u, code, err in bad:
        print(f"  FAIL [{w}] {ti} → {code or err} {u}")
    sys.exit(1)
print("모든 링크 정상")
