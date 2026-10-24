# -*- coding: utf-8 -*-
"""빌드 결과(로컬 HTML) 기술 점검. 배포 전에 실행.
    python -I tools_seo_check.py
확인: title/description 유무·중복, H1 정확히 1개, canonical = 대표 URL, robots 메타, 내부 링크가 실제 파일로 연결되는지,
      sitemap의 URL이 모두 존재하고 색인 대상인지, 치환 안 된 {{ }}, alt 없는 이미지, lastmod 형식."""
import re, sys, pathlib, html, urllib.parse
sys.stdout.reconfigure(encoding="utf-8")
ROOT = pathlib.Path(__file__).parent
sys.path.insert(0, str(ROOT / "data")); import content as D  # noqa

SKIP_DIRS = {".git", "audit", "data", "posts", "templates", "tools", "__pycache__", ".github"}
files = [p for p in ROOT.rglob("*.html") if not (set(p.relative_to(ROOT).parts) & SKIP_DIRS)]
problems, titles, descs = [], {}, {}
def rel_url(p):
    r = p.relative_to(ROOT).as_posix()
    return "" if r == "index.html" else (r[:-len("index.html")] if r.endswith("/index.html") else r)

for p in files:
    s = p.read_text(encoding="utf-8"); u = rel_url(p); tag = f"/{u}"
    m = lambda rx: (re.search(rx, s, re.S | re.I) or [None, None])[1]
    t = html.unescape(m(r"<title>(.*?)</title>") or "").strip(); d = m(r'<meta name="description" content="(.*?)"') or ""
    if not t: problems.append(f"{tag}: title 없음")
    if not d: problems.append(f"{tag}: description 없음")
    if len(t) > 70: problems.append(f"{tag}: title {len(t)}자(70 초과)")
    if len(d) > 170: problems.append(f"{tag}: description {len(d)}자(170 초과)")
    titles.setdefault(t, []).append(tag); descs.setdefault(d, []).append(tag)
    h1 = re.findall(r"<h1[^>]*>", s)
    if len(h1) != 1: problems.append(f"{tag}: h1 {len(h1)}개")
    can = m(r'<link rel="canonical" href="(.*?)"')
    noindex = "noindex" in (m(r'<meta name="robots" content="(.*?)"') or "")
    if p.name == "404.html":
        if not noindex: problems.append("404.html: noindex 없음")
    else:
        if can != f"{D.SITE_URL}/{u}": problems.append(f"{tag}: canonical 불일치 → {can}")
        if noindex: problems.append(f"{tag}: noindex 설정됨")
    if "{{" in s: problems.append(f"{tag}: 치환 안 된 플레이스홀더")
    for img in re.findall(r"<img [^>]*>", s):
        if 'alt="' not in img: problems.append(f"{tag}: alt 없는 이미지 {img[:60]}")
    for href in re.findall(r'(?:href|src|srcset)="([^"]+)"', s):
        if href.startswith(("http", "#", "tel:", "sms:", "mailto:", "data:", "//")): continue
        href = href.split("#")[0].split("?")[0]
        if not href: continue
        target = (ROOT / href.lstrip("/")) if href.startswith("/") else (p.parent / href)
        target = target.resolve()
        if target.is_dir(): target = target / "index.html"
        if not target.exists(): problems.append(f"{tag}: 깨진 링크 {href}")

for t, v in titles.items():
    if len(v) > 1: problems.append(f"중복 title {t!r}: {v}")
for d, v in descs.items():
    if len(v) > 1: problems.append(f"중복 description: {v}")

sm = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
locs = re.findall(r"<loc>(.*?)</loc>", sm); mods = re.findall(r"<lastmod>(.*?)</lastmod>", sm)
for loc in locs:
    path = loc.replace(D.SITE_URL + "/", "")
    f = ROOT / path / "index.html" if path == "" or path.endswith("/") else ROOT / path
    if path == "": f = ROOT / "index.html"
    if not f.exists(): problems.append(f"sitemap: 파일 없음 {loc}")
for mo in mods:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", mo): problems.append(f"sitemap: lastmod 형식 {mo}")
if len(set(locs)) != len(locs): problems.append("sitemap: 중복 URL")
indexable = {("/" + rel_url(p)) for p in files if p.name != "404.html"}
smset = {"/" + l.replace(D.SITE_URL + "/", "") for l in locs}
missing = indexable - smset
if missing: problems.append(f"sitemap에 없는 페이지: {sorted(missing)}")

print(f"검사 페이지 {len(files)}개, sitemap URL {len(locs)}개")
print("\n".join(problems) if problems else "문제 없음")
sys.exit(1 if problems else 0)
