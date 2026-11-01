# -*- coding: utf-8 -*-
"""사이트 상태 기록: sitemap의 모든 URL + 발견된 내부 링크에 대해 응답 코드, title, description, canonical, H1, robots 메타, 내부 링크를 수집.
    python -I tools_audit.py https://edumegong.co.kr audit/baseline-YYYY-MM-DD.json
결과 JSON은 변경 전후 비교용. 로컬 빌드 결과를 검사하려면 tools_seo_check.py를 쓴다."""
import sys, json, re, urllib.request, urllib.parse, html, datetime
sys.stdout.reconfigure(encoding="utf-8")
base, out = sys.argv[1].rstrip("/"), sys.argv[2]
UA = {"User-Agent": "Mozilla/5.0 (gwanaru-audit)"}

def get(url):
    url = urllib.parse.quote(url, safe=":/?&=%#")   # 한글 경로
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.geturl(), r.read().decode("utf-8", "replace"), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, url, "", dict(e.headers)
    except Exception as e:
        return None, url, str(e), {}

st, _, sm, _ = get(base + "/sitemap.xml")
urls = [urllib.parse.unquote(x) for x in re.findall(r"<loc>(.*?)</loc>", sm)]   # 키는 디코딩된 형태로 통일
seen, queue, pages = set(), list(urls), {}
while queue:
    u = queue.pop(0)
    if u in seen: continue
    seen.add(u)
    status, final, body, hdr = get(u)
    rec = {"status": status, "final": final, "x_robots": hdr.get("X-Robots-Tag")}
    if body and status == 200:
        m = lambda p: (re.search(p, body, re.S | re.I) or [None, None])[1]
        rec.update({
            "title": html.unescape(m(r"<title>(.*?)</title>") or "").strip(),
            "description": html.unescape(m(r'<meta name="description" content="(.*?)"') or ""),
            "canonical": m(r'<link rel="canonical" href="(.*?)"'),
            "robots_meta": m(r'<meta name="robots" content="(.*?)"'),
            "h1": [re.sub(r"<[^>]+>", "", h).strip() for h in re.findall(r"<h1[^>]*>(.*?)</h1>", body, re.S)],
            "naver_verify": bool(re.search(r'naver-site-verification" content="[0-9a-f]{20,}"', body)),
        })
        links = set()
        for href in re.findall(r'href="([^"#]+)"', body):
            if href.startswith(("tel:", "sms:", "mailto:", "data:", "javascript:")): continue
            absu = urllib.parse.urljoin(u, href)
            if absu.startswith(base):
                absu = urllib.parse.unquote(absu.split("?")[0])
                links.add(absu)
                if absu not in seen and absu.endswith(("/", ".html", ".xml", ".txt")): queue.append(absu)
        rec["internal_links"] = sorted(links)
    pages[u] = rec
res = {"base": base, "crawled_at": datetime.datetime.now().isoformat(timespec="seconds"), "sitemap_status": st, "sitemap_urls": urls, "pages": pages}
for p in ("/robots.txt", "/rss.xml"):
    s, _, b, _ = get(base + p); res[p] = {"status": s, "head": b[:300]}
json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
bad = {u: r["status"] for u, r in pages.items() if r["status"] != 200}
print(f"페이지 {len(pages)}개 기록 → {out}; 200 아님: {bad or '없음'}")
dup = {}
for u, r in pages.items():
    if r.get("title"): dup.setdefault(r["title"], []).append(u)
print("중복 title:", {t: v for t, v in dup.items() if len(v) > 1} or "없음")
print("canonical 불일치:", [u for u, r in pages.items() if r.get("canonical") and urllib.parse.unquote(r["canonical"]) != u] or "없음")
