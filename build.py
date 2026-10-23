#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""사이트 빌드: templates/ + data/content.py + posts/*.md  →  정적 HTML, sitemap.xml, rss.xml, robots.txt

    python3 build.py

블로그 글은 posts/ 폴더에 .md 파일을 넣기만 하면 됩니다 (형식은 posts/README.md 참고).
"""
import html, os, re, sys, datetime, pathlib, shutil, email.utils
import markdown, yaml

ROOT = pathlib.Path(__file__).parent
sys.path.insert(0, str(ROOT / "data"))
import content as D  # noqa: E402

OUT = ROOT  # 결과를 저장소 루트에 바로 씁니다 (GitHub Pages가 루트를 서빙)
TODAY = datetime.date.today().isoformat()
esc = html.escape

def read(p): return (ROOT / p).read_text(encoding="utf-8")
def write(p, s):
    p = OUT / p; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(s, encoding="utf-8")

# ---------------------------------------------------------------- 공통 조각
def head(title, desc, path, extra="", depth=1, jsonld=None, og_type="website"):
    rel = "../" * depth
    url = f"{D.SITE_URL}/{path}"
    ld = ""
    if jsonld:
        import json
        ld = f'<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>'
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{url}">
<meta name="robots" content="index, follow">
<meta name="naver-site-verification" content="{D.NAVER_VERIFY}">
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="{D.SITE_NAME}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{D.SITE_URL}/img/og.png">
<meta property="og:locale" content="ko_KR">
{extra}
<link rel="alternate" type="application/rss+xml" title="{D.SITE_NAME} 블로그" href="{D.SITE_URL}/rss.xml">
{FAVICON}
{FONTS}
<link rel="stylesheet" href="{rel}css/site.css">
<script>document.documentElement.classList.add('js')</script>
{ld}
</head>
<body>
{header(rel)}
<main>
"""

def aside(depth=1, links=()):
    rel = "../" * depth
    li = "".join(f'<li><a href="{rel}{h}">{esc(t)}</a></li>' for t, h in links)
    return f"""<aside class="page__aside">
  <div class="aside-card">
    <h2>무료 상담 신청</h2>
    <p>학년, 과목, 지역, 원하는 요일만 알려주세요. 2~3일 안에 선생님 후보를 안내하고 첫 수업은 무료 체험입니다.</p>
    <a class="btn btn--yellow" href="sms:{D.PHONE_RAW}">💬 문자로 무료 체험 신청</a>
    <a class="btn btn--brand" href="tel:{D.PHONE_RAW}">📞 {D.PHONE}</a>
  </div>
  <div class="aside-links">
    <h3>함께 보기</h3>
    <ul>{li}</ul>
  </div>
</aside>"""

def foot(depth=1):
    return f"""</main>
{footer("../" * depth)}
</body>
</html>
"""

def faq_html(items):
    return "\n".join(f'<details class="qa"><summary>{esc(q)}</summary><p>{esc(a)}</p></details>' for q, a in items)

def faq_ld(items):
    return {"@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in items]}

def crumbs(depth, *parts):
    rel = "../" * depth
    out = [f'<a href="{rel}">홈</a>']
    for t, h in parts:
        out.append(f'<a href="{rel}{h}">{esc(t)}</a>' if h else esc(t))
    return '<p class="crumbs">' + " › ".join(out) + "</p>"

FONTS = """<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
<link href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css" rel="stylesheet">"""

FAVICON = """<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='9' fill='%230e8f86'/%3E%3Cpath d='M6 19c3-3 6-3 10 0s7 3 10 0' stroke='%23fff' stroke-width='3' fill='none' stroke-linecap='round'/%3E%3Cpath d='M6 13c3-3 6-3 10 0s7 3 10 0' stroke='%23ffd43b' stroke-width='3' fill='none' stroke-linecap='round'/%3E%3C/svg%3E">"""

LOGO_MARK = ('<svg class="logo__mark" viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" rx="9" fill="#0e8f86"/>'
             '<path d="M6 19c3-3 6-3 10 0s7 3 10 0" stroke="#fff" stroke-width="3" fill="none" stroke-linecap="round"/>'
             '<path d="M6 13c3-3 6-3 10 0s7 3 10 0" stroke="#ffd43b" stroke-width="3" fill="none" stroke-linecap="round"/></svg>')

def header(rel=""):
    nav = [("초등 과외", "elementary/"), ("중등 과외", "middle/"), ("고등 과외", "high/"), ("화상과외", "online/"),
           ("방문과외", "visit/"), ("과외 비용", "cost/"), ("블로그", "blog/")]
    links = "".join(f'<a href="{rel}{h}">{esc(t)}</a>' for t, h in nav)
    home = rel or "./"
    return f"""<header class="site-head">
  <div class="container site-head__in">
    <a class="logo" href="{home}">{LOGO_MARK}<span>{D.SITE_NAME}</span></a>
    <nav class="gnb" id="gnb" aria-label="주요 메뉴">{links}</nav>
    <a class="btn btn--brand btn--sm head-tel" href="tel:{D.PHONE_RAW}">📞 {D.PHONE}</a>
    <button class="menu-btn" type="button" aria-controls="gnb" aria-expanded="false" aria-label="메뉴 열기"><span></span><span></span><span></span></button>
  </div>
</header>"""

def footer(rel=""):
    home = rel or "./"
    grades = "".join(f'<li><a href="{rel}{gk}/">{g["name"]} 과외</a></li>' for gk, g in D.GRADES.items())
    subj = "".join(f'<li><a href="{rel}middle-{sk}/">{s["name"]} 과외</a></li>' for sk, s in D.SUBJECTS.items())
    return f"""<footer class="site-foot">
  <div class="container site-foot__in">
    <div class="site-foot__brand">
      <a class="logo logo--light" href="{home}">{LOGO_MARK}<span>{D.SITE_NAME}</span></a>
      <p>아이와 꼭 맞는 선생님을 잇는 곳.<br>초중고 방문·화상 1:1 과외 상담</p>
      <p class="site-foot__tel"><a href="tel:{D.PHONE_RAW}">{D.PHONE}</a><br><small>평일 09–21시 · 주말 10–18시 · 문자 언제든</small></p>
    </div>
    <div class="site-foot__cols">
      <div><h4>학년별</h4><ul>{grades}</ul></div>
      <div><h4>과목별</h4><ul>{subj}</ul></div>
      <div><h4>안내</h4><ul><li><a href="{rel}online/">화상과외</a></li><li><a href="{rel}visit/">방문과외</a></li><li><a href="{rel}cost/">과외 비용</a></li><li><a href="{rel}blog/">블로그</a></li></ul></div>
    </div>
  </div>
  <div class="container site-foot__bottom">© 2026 {D.SITE_NAME} · <a href="{rel}sitemap.xml">사이트맵</a> · <a href="{rel}rss.xml">RSS</a></div>
</footer>
<div class="quickbar">
  <a href="tel:{D.PHONE_RAW}">📞 전화 상담</a>
  <a class="quickbar__main" href="sms:{D.PHONE_RAW}">💬 문자로 무료 체험 신청</a>
</div>
<script src="{rel}js/base.js" defer></script>
<script src="{rel}js/site.js" defer></script>"""

SUBJECT_ICON = {"math": "➗", "english": "🔤", "korean": "📖", "science": "🔬", "social": "🌏"}
GRADE_ICON = {"elementary": "🌱", "middle": "📘", "high": "🎓"}

def build_index(posts):
    import json
    grade_cards = []
    for i, (gk, g) in enumerate(D.GRADES.items()):
        li = "".join(f'<a href="{gk}-{sk}/">{esc(s["name"])}</a>' for sk, s in D.SUBJECTS.items())
        grade_cards.append(f'''<article class="grade" data-reveal style="--i:{i}">
  <a class="grade__head" href="{gk}/"><span class="grade__ic">{GRADE_ICON[gk]}</span><span><b>{g["name"]} 과외</b><small>{g["range"]}</small></span><span class="grade__go">→</span></a>
  <p>{esc(g["intro"])}</p>
  <div class="chips">{li}</div>
</article>''')
    subject_cards = []
    for i, (sk, s) in enumerate(D.SUBJECTS.items()):
        subject_cards.append(f'''<a class="subj" href="middle-{sk}/" data-reveal style="--i:{i}">
  <div class="subj__img"><img src="img/subject-{sk}.jpg" width="1200" height="900" alt="{esc(s["name"])} 수업 자료" loading="lazy"></div>
  <div class="subj__body"><b>{SUBJECT_ICON[sk]} {esc(s["name"])}</b><p>{esc(s["desc"])}</p></div>
</a>''')
    latest = "".join(f'''<a class="post-card" href="blog/{p["slug"]}/"><time datetime="{p["date"].isoformat()}">{p["date"].strftime("%Y.%m.%d")}</time><b>{esc(p["title"])}</b><p>{esc(p["desc"][:80])}</p><span class="more">읽어 보기 →</span></a>''' for p in posts[:3]) or '<p class="muted">첫 글을 준비하고 있습니다.</p>'
    page = read("templates/index.html")
    page = (page.replace("{{HEADER}}", header("")).replace("{{FOOTER}}", footer(""))
                .replace("{{SITE_URL}}", D.SITE_URL).replace("{{SITE_NAME}}", D.SITE_NAME).replace("{{NAVER_VERIFY}}", D.NAVER_VERIFY)
                .replace("{{FONTS}}", FONTS).replace("{{FAVICON}}", FAVICON)
                .replace("{{GRADE_CARDS}}", "\n".join(grade_cards)).replace("{{SUBJECT_CARDS}}", "\n".join(subject_cards))
                .replace("{{LATEST_POSTS}}", latest)
                .replace("{{FAQ}}", faq_html(D.FAQ)).replace("{{FAQ_LD}}", json.dumps(faq_ld(D.FAQ), ensure_ascii=False)))
    write("index.html", page)
    pages.append(("", TODAY, "1.0"))

pages = []   # (path, lastmod, priority)

# ---------------------------------------------------------------- 키워드 페이지 (학년×과목, 학년 허브, 기타)
def build_keyword_pages():
    for gk, g in D.GRADES.items():
        for sk, s in D.SUBJECTS.items():
            slug = f"{gk}-{sk}/"
            kw = f'{g["name"]}{s["name"]}과외'
            title = f'{g["name"]} {s["name"]} 과외 | 방문·화상 1:1, 무료 체험 | {D.SITE_NAME}'
            desc = f'{g["full"]} {s["name"]} 1:1 과외 상담. {s["desc"]} 방문·화상 모두 가능, 첫 수업 무료 체험. 전화 {D.PHONE}'
            faq = [(f'{g["name"]} {s["name"]} 과외는 주 몇 회가 적당한가요?', "주 1회로 시작해 시험 전후에 주 2회로 늘리는 가정이 많습니다. 아이의 현재 상태를 듣고 상담에서 같이 정합니다."),
                   (f'{g["name"]} {s["name"]} 과외 비용은 얼마인가요?', f'월 기준 {", ".join(f"{n} {p}" for n, p in g["price"])} 범위이며 정확한 금액은 상담에서 확정합니다. 상담과 체험은 무료입니다.'),
                   ("방문과 화상 중 어느 쪽이 좋나요?", "집중이 어려우면 방문, 일정이 빡빡하면 화상이 맞는 편입니다. 체험 수업을 한 번 해 보고 정해도 됩니다.")]
            body = f"""<section class="page wrap"><div class="page__grid"><article class="page__main">
{crumbs(1, (g["name"] + " 과외", gk + "/"), (kw, None))}
<h1>{esc(g["name"])} {esc(s["name"])} 과외</h1>
<p class="lead">{esc(g["full"])} {esc(s["name"])} 1:1 과외를 방문 또는 화상으로 상담하고 선생님을 연결합니다. 첫 수업은 무료 체험입니다.</p>
<h2>{esc(g["name"])} {esc(s["name"])}, 이렇게 수업합니다</h2>
<p>{esc(s["intro"])}</p>
<p>{esc(g["intro"])}</p>
<ul class="plain">{"".join(f"<li>{esc(p)}</li>" for p in s["points"])}</ul>
<h2>이런 학생에게 맞습니다</h2>
<ul class="plain">{"".join(f"<li>{esc(p)}</li>" for p in g["fit"])}</ul>
<h2>{esc(g["name"])} {esc(s["name"])} 과외 비용</h2>
<p>월 기준 안내 범위입니다. {esc(", ".join(f"{n} {p}" for n, p in g["price"]))}. 과목 수, 횟수, 선생님에 따라 달라지며 정확한 금액은 상담에서 확정합니다. 상담과 체험 수업은 무료입니다.</p>
<h2>진행 순서</h2>
<p>오늘 전화나 문자로 학년, 과목, 지역, 원하는 요일을 알려주시면 2~3일 안에 선생님 후보 1~2명을 안내합니다. 그 주에 무료 체험 수업을 하고, 계속할지는 가족이 정합니다. 첫 수업까지 보통 일주일입니다.</p>
<h2>자주 묻는 질문</h2>
<div class="faq">{faq_html(faq)}</div>
</article>
{aside(1, [(f'{g["name"]} {o["name"]} 과외', f"{gk}-{ok}/") for ok, o in D.SUBJECTS.items() if ok != sk] + [(f'{o["name"]} {s["name"]} 과외', f"{ok}-{sk}/") for ok, o in D.GRADES.items() if ok != gk] + [("화상과외", "online/"), ("방문과외", "visit/"), ("과외 비용", "cost/")])}
</div></section>"""
            extra = f'<meta name="keywords" content="{kw}, {g["name"]} {s["name"]} 과외, {s["name"]}과외, {g["name"]}과외, 화상과외, 방문과외">'
            write(slug + "index.html", head(title, desc, slug, extra, 1, faq_ld(faq)) + body + foot(1))
            pages.append((slug, TODAY, "0.8"))

        # 학년 허브
        slug = f"{gk}/"
        title = f'{g["name"]} 과외 | 국어·영어·수학·과학·사회 1:1 | {D.SITE_NAME}'
        desc = f'{g["full"]} 1:1 과외 상담. 과목별 수업 방식과 월 비용 범위, 방문·화상 선택. 첫 수업 무료 체험. 전화 {D.PHONE}'
        subj = "".join(f'<li><a href="../{gk}-{sk}/">{esc(g["name"])} {esc(s["name"])} 과외</a> — {esc(s["desc"])}</li>' for sk, s in D.SUBJECTS.items())
        body = f"""<section class="page wrap"><div class="page__grid"><article class="page__main">
{crumbs(1, (g["name"] + " 과외", None))}
<h1>{esc(g["name"])} 과외 <span class="muted">{esc(g["range"])}</span></h1>
<p class="lead">{esc(g["intro"])}</p>
<h2>과목별 안내</h2>
<ul class="plain">{subj}</ul>
<h2>이런 학생에게 맞습니다</h2>
<ul class="plain">{"".join(f"<li>{esc(p)}</li>" for p in g["fit"])}</ul>
<h2>{esc(g["name"])} 과외 비용</h2>
<p>월 기준 안내 범위: {esc(", ".join(f"{n} {p}" for n, p in g["price"]))}. 정확한 금액은 상담에서 확정하며 상담과 체험은 무료입니다. 자세한 설명은 <a href="../cost/">과외 비용</a> 페이지에 있습니다.</p>
<h2>자주 묻는 질문</h2>
<div class="faq">{faq_html(D.FAQ[:6])}</div>
</article>
{aside(1, [(f'{o["name"]} 과외', f"{ok}/") for ok, o in D.GRADES.items() if ok != gk] + [("화상과외", "online/"), ("방문과외", "visit/")])}
</div></section>"""
        write(slug + "index.html", head(title, desc, slug, f'<meta name="keywords" content="{g["name"]}과외, {g["name"]} 과외, {g["full"]} 과외, 1:1 과외">', 1, faq_ld(D.FAQ[:6])) + body + foot(1))
        pages.append((slug, TODAY, "0.9"))

    for key, p in D.EXTRA_PAGES.items():
        slug = f"{key}/"
        title = f'{p["title"]} | 초중고 1:1, 무료 체험 | {D.SITE_NAME}'
        body = f"""<section class="page wrap"><div class="page__grid"><article class="page__main">
{crumbs(1, (p["title"], None))}
<h1>{esc(p["h1"])}</h1>
<p class="lead">{esc(p["intro"])}</p>
<h2>특징</h2>
<ul class="plain">{"".join(f"<li>{esc(x)}</li>" for x in p["points"])}</ul>
<h2>이런 학생에게 맞습니다</h2>
<ul class="plain">{"".join(f"<li>{esc(x)}</li>" for x in p["fit"])}</ul>
<h2>진행 순서</h2>
<p>전화나 문자로 학년, 과목, 지역, 원하는 요일을 알려주시면 2~3일 안에 선생님 후보를 안내하고, 그 주에 무료 체험 수업을 합니다. 체험 뒤에 계속할지는 가족이 정합니다.</p>
<h2>자주 묻는 질문</h2>
<div class="faq">{faq_html(p["faq"])}</div>
</article>
{aside(1, [(f'{o["name"]} 과외', f"{ok}/") for ok, o in D.GRADES.items()] + [(q["title"], f"{qk}/") for qk, q in D.EXTRA_PAGES.items() if qk != key])}
</div></section>"""
        write(slug + "index.html", head(title, p["desc"], slug, f'<meta name="keywords" content="{p["title"]}, 1:1 과외, 과외 상담">', 1, faq_ld(p["faq"])) + body + foot(1))
        pages.append((slug, TODAY, "0.9"))

# ---------------------------------------------------------------- 블로그
def slugify(s):
    s = re.sub(r"[^\w\-가-힣]+", "-", s.strip().lower()).strip("-")
    return s[:80] or "post"

def load_posts():
    posts = []
    for f in sorted((ROOT / "posts").glob("*.md")):
        if f.name.lower() == "readme.md": continue
        text = f.read_text(encoding="utf-8")
        m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.S)
        if not m:
            print(f"[건너뜀] {f.name}: 맨 위에 --- 로 감싼 정보(title, date 등)가 없습니다"); continue
        meta = yaml.safe_load(m.group(1)) or {}
        body_md = m.group(2)
        if "title" not in meta: print(f"[건너뜀] {f.name}: title이 없습니다"); continue
        date = meta.get("date") or datetime.date.fromtimestamp(f.stat().st_mtime)
        if isinstance(date, datetime.datetime): date = date.date()
        if isinstance(date, str): date = datetime.date.fromisoformat(date[:10])
        slug = meta.get("slug") or slugify(f.stem)
        body_html = markdown.markdown(body_md, extensions=["extra", "sane_lists"])
        plain = re.sub(r"<[^>]+>", "", body_html)
        desc = meta.get("description") or re.sub(r"\s+", " ", plain).strip()[:150]
        posts.append({"title": str(meta["title"]), "date": date, "slug": slug, "html": body_html, "desc": desc,
                      "keywords": meta.get("keywords", ""), "grade": meta.get("grade", ""), "subject": meta.get("subject", "")})
    posts.sort(key=lambda p: (p["date"], p["slug"]), reverse=True)
    return posts

def build_blog(posts):
    for i, p in enumerate(posts):
        slug = f"blog/{p['slug']}/"
        title = f'{p["title"]} | {D.SITE_NAME} 블로그'
        related = [q for q in posts if q is not p and (q["grade"] == p["grade"] or q["subject"] == p["subject"])][:5] or [q for q in posts if q is not p][:5]
        rel_html = "".join(f'<li><a href="../{q["slug"]}/">{esc(q["title"])}</a></li>' for q in related)
        ld = {"@context": "https://schema.org", "@type": "Article", "headline": p["title"], "description": p["desc"],
              "datePublished": p["date"].isoformat(), "dateModified": p["date"].isoformat(),
              "author": {"@type": "Organization", "name": D.SITE_NAME}, "publisher": {"@type": "Organization", "name": D.SITE_NAME},
              "mainEntityOfPage": f"{D.SITE_URL}/{slug}"}
        extra = f'<meta name="keywords" content="{esc(p["keywords"])}"><meta property="article:published_time" content="{p["date"].isoformat()}">'
        body = f"""<section class="page wrap"><div class="page__grid"><article class="page__main">
{crumbs(2, ("블로그", "blog/"), (p["title"], None))}
<h1>{esc(p["title"])}</h1>
<p class="crumbs"><time datetime="{p["date"].isoformat()}">{p["date"].strftime("%Y년 %m월 %d일")}</time></p>
<div class="post">{p["html"]}</div>
<h2>함께 읽기</h2>
<ul class="plain">{rel_html}</ul>
</article>
{aside(2, [(f'{g["name"]} 과외', f"{gk}/") for gk, g in D.GRADES.items()] + [("화상과외", "online/"), ("과외 비용", "cost/")])}
</div></section>"""
        write(slug + "index.html", head(title, p["desc"], slug, extra, 2, ld, "article") + body + foot(2))
        pages.append((slug, p["date"].isoformat(), "0.7"))

    # 블로그 목록 (페이지당 30개)
    per = 30
    chunks = [posts[i:i + per] for i in range(0, max(len(posts), 1), per)] or [[]]
    for n, chunk in enumerate(chunks, 1):
        slug = "blog/" if n == 1 else f"blog/page/{n}/"
        depth = 1 if n == 1 else 3
        rel = "../" * depth
        items = "".join(f'<li><a href="{rel}blog/{q["slug"]}/">{esc(q["title"])}</a> <span class="muted">{q["date"].isoformat()}</span><br><span class="muted">{esc(q["desc"][:90])}</span></li>' for q in chunk) or "<li>첫 글을 준비하고 있습니다.</li>"
        nav = ""
        if n > 1: nav += f'<a href="{rel}blog/{"" if n == 2 else f"page/{n-1}/"}">← 이전</a> '
        if n < len(chunks): nav += f'<a href="{rel}blog/page/{n+1}/">다음 →</a>'
        body = f"""<section class="page wrap"><div class="page__grid"><article class="page__main">
{crumbs(depth, ("블로그", None))}
<h1>과외 블로그</h1>
<p class="lead">학년별·과목별 과외 이야기와 학부모가 자주 묻는 질문을 매일 올립니다. 글 {len(posts)}개.</p>
<ul class="plain">{items}</ul>
<p class="crumbs">{nav}</p>
</article>
{aside(depth, [(f'{g["name"]} 과외', f"{gk}/") for gk, g in D.GRADES.items()] + [("화상과외", "online/"), ("방문과외", "visit/"), ("과외 비용", "cost/")])}
</div></section>"""
        write(slug + "index.html", head(f"과외 블로그 | 학년별·과목별 과외 안내 | {D.SITE_NAME}", "초중고 과외, 화상과외, 방문과외에 대한 글을 매일 올립니다. 학년별 공부법과 과외 비용, 선생님 고르는 법.", slug, "", depth) + body + foot(depth))
        pages.append((slug, TODAY, "0.6"))

# ---------------------------------------------------------------- sitemap / rss / robots
def build_feeds(posts):
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path, mod, pri in pages:
        sm.append(f"  <url><loc>{D.SITE_URL}/{path}</loc><lastmod>{mod}</lastmod><priority>{pri}</priority></url>")
    sm.append("</urlset>")
    write("sitemap.xml", "\n".join(sm))
    now = email.utils.format_datetime(datetime.datetime.now(datetime.timezone.utc))
    rss = ['<?xml version="1.0" encoding="UTF-8"?>', '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>',
           f"<title>{esc(D.SITE_NAME)} 블로그</title><link>{D.SITE_URL}/blog/</link><description>초중고 과외, 화상과외, 방문과외 안내</description><language>ko</language><lastBuildDate>{now}</lastBuildDate>",
           f'<atom:link href="{D.SITE_URL}/rss.xml" rel="self" type="application/rss+xml"/>']
    for p in posts[:50]:
        d = email.utils.format_datetime(datetime.datetime.combine(p["date"], datetime.time(9, 0), tzinfo=datetime.timezone(datetime.timedelta(hours=9))))
        rss.append(f"<item><title>{esc(p['title'])}</title><link>{D.SITE_URL}/blog/{p['slug']}/</link><guid>{D.SITE_URL}/blog/{p['slug']}/</guid><pubDate>{d}</pubDate><description>{esc(p['desc'])}</description></item>")
    rss.append("</channel></rss>")
    write("rss.xml", "\n".join(rss))
    write("robots.txt", f"User-agent: *\nAllow: /\nUser-agent: Yeti\nAllow: /\n\nSitemap: {D.SITE_URL}/sitemap.xml\n")

if __name__ == "__main__":
    posts = load_posts()
    build_index(posts)
    build_keyword_pages()
    build_blog(posts)
    build_feeds(posts)
    print(f"완료: 페이지 {len(pages)}개 (블로그 글 {len(posts)}개) → {OUT}")
