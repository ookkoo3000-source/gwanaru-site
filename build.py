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
{FONTS}
<link rel="stylesheet" href="{rel}css/base.css">
<link rel="stylesheet" href="{rel}css/site.css">
<script>document.documentElement.classList.add('js')</script>
{ld}
</head>
<body>
<header class="top page-top">
  <a class="top__mark" href="{rel}">{D.SITE_NAME}</a>
  <nav><a class="top__link" href="{rel}blog/">블로그</a><span aria-hidden="true"> · </span><a class="top__link tel" href="tel:{D.PHONE_RAW}">{D.PHONE}</a></nav>
</header>
<main>
"""

def aside(depth=1, links=()):
    rel = "../" * depth
    li = "".join(f'<li><a href="{rel}{h}">{esc(t)}</a></li>' for t, h in links)
    return f"""<aside class="page__aside">
  <div class="aside-card">
    <h2>무료 상담 신청</h2>
    <p>학년, 과목, 지역, 원하는 요일만 알려주세요. 2~3일 안에 선생님 후보를 안내하고 첫 수업은 무료 체험입니다.</p>
    <a class="button" href="tel:{D.PHONE_RAW}">전화 {D.PHONE}</a>
    <a class="button button--ink" href="sms:{D.PHONE_RAW}">문자로 신청</a>
    <ul>{li}</ul>
  </div>
</aside>"""

def foot(depth=1):
    rel = "../" * depth
    return f"""</main>
<footer class="pagefoot">
  <span>© 2026 {D.SITE_NAME} · <a href="tel:{D.PHONE_RAW}">{D.PHONE}</a></span>
  <span><a href="{rel}">홈</a> · <a href="{rel}blog/">블로그</a> · <a href="{rel}sitemap.xml">사이트맵</a> · <a href="{rel}rss.xml">RSS</a></span>
</footer>
<script src="{rel}js/base.js" defer></script>
<script src="{rel}js/site.js" defer></script>
</body>
</html>
"""

def faq_html(items):
    return "\n".join(f'<p><dfn>{esc(q)}</dfn> {esc(a)}</p>' for q, a in items)

def faq_ld(items):
    return {"@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in items]}

def crumbs(depth, *parts):
    rel = "../" * depth
    out = [f'<a href="{rel}">홈</a>']
    for t, h in parts:
        out.append(f'<a href="{rel}{h}">{esc(t)}</a>' if h else esc(t))
    return '<p class="crumbs">' + " › ".join(out) + "</p>"

FONTS = """<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="preconnect" href="https://api.fontshare.com">
<link rel="preconnect" href="https://cdn.fontshare.com" crossorigin>
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
<link href="https://api.fontshare.com/v2/css?f[]=gambarino@400&f[]=general-sans@400,500&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;500;600&display=swap" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css" rel="stylesheet">"""

FS = "Noto Serif KR, Noto Serif CJK KR, serif"          # display face in drawings
FT = "Pretendard, Noto Sans KR, Noto Sans CJK KR, sans-serif"  # text face in drawings
INK, MUTED, SURF, SURF2, SURF3, PAPER = "#06525c", "#2f737d", "#ebf0ee", "#dde6e3", "#cbd9d5", "#ffffff"

def pic(src, w, h, alt, draw, lazy=True):
    """A photograph slot with a drawn fallback: the drawing shows only when the file is missing."""
    lz = ' loading="lazy"' if lazy else ' fetchpriority="high"'
    return (f'<div class="pic"><img src="{src}" width="{w}" height="{h}" alt="{esc(alt)}"{lz} '
            f'onerror="this.parentNode.classList.add(\'is-missing\')"><div class="pic__draw">{draw}</div></div>')

def svg_hero():
    return (f'<svg viewBox="0 0 1500 1000"><rect width="1500" height="1000" fill="{SURF}"/>'
            f'<rect x="150" y="180" width="900" height="640" fill="{PAPER}"/>'
            + "".join(f'<rect x="210" y="{260+i*64}" width="{w}" height="14" fill="{SURF2}"/>' for i, w in enumerate([700, 560, 640, 420, 600, 520, 300]))
            + f'<rect x="210" y="324" width="560" height="14" fill="{MUTED}"/>'
            f'<path d="M1010 420 l260 -60 l26 18 l-260 60 z" fill="{INK}"/><path d="M1270 360 l26 18 l30 -8 l-34 -24 z" fill="{MUTED}"/>'
            f'<circle cx="1180" cy="760" r="90" fill="{SURF3}"/><rect x="1120" y="640" width="120" height="60" fill="{SURF2}"/></svg>')

def svg_sheet():
    g = f'font-family="{FT}" font-size="15" fill="{INK}"'
    rows = "".join(f'<text x="110" y="{130+i*50}" {g}>{t}</text><line x1="170" y1="{134+i*50}" x2="530" y2="{134+i*50}" stroke="{INK}" stroke-width="1.5"/>'
                   for i, t in enumerate(["학생", "학년", "과목", "지역", "요일", "방식"]))
    hand = "".join(f'<text x="184" y="{176+i*50}" font-family="{FS}" font-size="17" fill="{MUTED}" font-style="italic">{t}</text>'
                   for i, t in enumerate(["중 2", "수학, 영어", "분당 · 화상 가능", "화 · 목 저녁"]))
    return (f'<svg viewBox="0 0 640 480" role="img" aria-label="상담지: 학생, 학년, 과목, 지역, 요일, 방식을 적는 종이">'
            f'<rect width="640" height="480" fill="{SURF}"/><rect x="80" y="30" width="480" height="420" fill="{PAPER}"/>'
            f'<text x="110" y="80" font-family="{FS}" font-size="26" font-weight="600" fill="{INK}">과외 상담지</text>'
            f'<text x="420" y="80" font-family="{FT}" font-size="14" fill="{MUTED}">No. 0001</text>{rows}{hand}'
            f'<g class="pen"><path d="M150 405 l120 -18 l10 6 l-120 18 z" fill="{INK}"/><path d="M270 387 l10 6 l12 -4 l-14 -8 z" fill="{MUTED}"/></g>'
            f'<rect x="430" y="410" width="110" height="26" fill="{INK}"/><text x="485" y="428" text-anchor="middle" font-family="{FT}" font-size="13" fill="{PAPER}">체험 1회 무료</text></svg>')

def svg_timetable():
    days = "".join(f'<text x="{300+i*200}" y="72" text-anchor="middle" font-family="{FT}" font-size="30" fill="{MUTED}">{d}</text>' for i, d in enumerate("월화수목금토일"))
    hours = "".join(f'<text x="100" y="{185+i*130}" text-anchor="middle" font-family="{FT}" font-size="26" fill="{MUTED}">{h}시</text>' for i, h in enumerate(range(16, 22)))
    grid = "".join(f'<line x1="{200+i*200}" y1="0" x2="{200+i*200}" y2="900"/>' for i in range(7)) + "".join(f'<line x1="0" y1="{110+i*130}" x2="1600" y2="{110+i*130}"/>' for i in range(6))
    def slot(x, y, t, u, fill, ink, delay=""):
        st = f' style="animation-delay:{delay}"' if delay else ""
        return (f'<g class="slot"{st}><rect x="{x}" y="{y}" width="176" height="236" fill="{fill}"/>'
                f'<text x="{x+88}" y="{y+108}" text-anchor="middle" font-family="{FS}" font-size="30" fill="{ink}">{t}</text>'
                f'<text x="{x+88}" y="{y+148}" text-anchor="middle" font-family="{FT}" font-size="22" fill="{ink}">{u}</text></g>')
    return (f'<svg viewBox="0 0 1600 900" preserveAspectRatio="xMidYMid slice"><rect width="1600" height="900" fill="{SURF}"/>'
            f'<g stroke="{SURF3}" stroke-width="2">{grid}</g>{days}{hours}'
            + slot(412, 382, "수학", "화상 · 90분", INK, PAPER) + slot(812, 382, "수학", "화상 · 90분", INK, PAPER, "1.4s")
            + slot(1212, 122, "영어", "방문 · 2시간", PAPER, INK, "0.7s") + "</svg>")

pages = []   # (path, lastmod, priority)

# ---------------------------------------------------------------- 과목 미리보기 그림
def subject_svg(key):
    F = FS
    base = f'<svg viewBox="0 0 640 480"><rect width="640" height="480" fill="{SURF}"/><rect x="60" y="40" width="520" height="400" fill="{PAPER}"/>'
    if key == "math":
        body = (f'<path d="M120 360 Q 320 60 520 360" fill="none" stroke="#2f737d" stroke-width="6"/>'
                f'<line x1="100" y1="380" x2="540" y2="380" stroke="#06525c" stroke-width="2"/><line x1="320" y1="90" x2="320" y2="400" stroke="#06525c" stroke-width="2"/>'
                f'<text x="110" y="100" font-family="{F}" font-size="22" fill="#06525c">y = -(x-3)² + 9</text><circle cx="320" cy="135" r="8" fill="#06525c"/>'
                f'<text x="340" y="130" font-family="{F}" font-size="18" fill="#2f737d">꼭짓점</text>')
    elif key == "english":
        lines = ["The teacher asked the students to read", "the passage carefully before answering.", "Because the question was difficult,", "many of them read it twice."]
        body = "".join(f'<text x="110" y="{130+i*58}" font-family="{F}" font-size="24" fill="#06525c">{t}</text>' for i, t in enumerate(lines))
        body += '<rect x="110" y="190" width="150" height="4" fill="#2f737d"/><rect x="110" y="306" width="100" height="4" fill="#2f737d"/><text x="420" y="330" font-family="'+F+'" font-size="18" fill="#2f737d">접속사 → 이유</text>'
    elif key == "korean":
        lines = ["글쓴이는 도시의 밤을 ‘잠들지 않는 바다’에", "빗대어 말한다. 끊임없이 움직이는 불빛을", "파도로, 사람들을 물고기로 본 것이다.", "", "문제. 윗글의 표현 방식으로 알맞은 것은?"]
        body = "".join(f'<text x="110" y="{130+i*52}" font-family="{F}" font-size="22" fill="#06525c">{t}</text>' for i, t in enumerate(lines))
        body += '<rect x="110" y="138" width="230" height="5" fill="#2f737d"/><text x="120" y="420" font-family="'+F+'" font-size="20" fill="#2f737d">③ 비유</text>'
    elif key == "science":
        body = (f'<rect x="150" y="150" width="120" height="200" fill="none" stroke="#06525c" stroke-width="3"/><rect x="150" y="250" width="120" height="100" fill="#2f737d"/>'
                f'<rect x="370" y="150" width="120" height="200" fill="none" stroke="#06525c" stroke-width="3"/><rect x="370" y="200" width="120" height="150" fill="#2f737d"/>'
                f'<text x="210" y="390" text-anchor="middle" font-family="{F}" font-size="18" fill="#06525c">가열 전</text><text x="430" y="390" text-anchor="middle" font-family="{F}" font-size="18" fill="#06525c">가열 후</text>'
                f'<text x="110" y="100" font-family="{F}" font-size="22" fill="#06525c">실험 3. 온도와 부피</text>')
    elif key == "social":
        body = (f'<line x1="100" y1="240" x2="540" y2="240" stroke="#06525c" stroke-width="3"/>'
                + "".join(f'<circle cx="{140+i*100}" cy="240" r="9" fill="{"#2f737d" if i==2 else "#06525c"}"/><text x="{140+i*100}" y="{210 if i%2==0 else 285}" text-anchor="middle" font-family="{F}" font-size="18" fill="#06525c">{y}</text>' for i, y in enumerate(["1392", "1592", "1636", "1876", "1910"]))
                + f'<text x="110" y="100" font-family="{F}" font-size="22" fill="#06525c">조선 시대 연표</text><text x="340" y="400" text-anchor="middle" font-family="{F}" font-size="18" fill="#2f737d">병자호란</text>')
    else:  # international
        body = (f'<text x="110" y="100" font-family="{F}" font-size="22" fill="#06525c">IB Mathematics AA · Unit 4</text>'
                + "".join(f'<rect x="110" y="{140+i*48}" width="{w}" height="22" fill="{"#2f737d" if i==1 else "#dde6e3"}"/>' for i, w in enumerate([380, 300, 420, 260, 340]))
                + f'<text x="110" y="420" font-family="{F}" font-size="18" fill="#2f737d">Internal assessment due: Week 6</text>')
    return base + body + "</svg>"

# ---------------------------------------------------------------- 메인 페이지
def build_index():
    bars, previews = [], []
    order = list(D.SUBJECTS.items())
    for i, (key, s) in enumerate(order):
        items = [(f'{g["name"]} {s["name"]} 과외', f'{gk}-{key}/', g["range"]) for gk, g in D.GRADES.items()]
        li = "".join(f'<li><a href="{h}">{esc(t)}</a><span>{esc(r)}</span></li>' for t, h, r in items)
        bars.append(f'''<details class="bar" data-preview="{key}" data-reveal style="--i:{i}"{" open" if i == 0 else ""}>
  <summary>{esc(s["name"])}<span class="plus" aria-hidden="true">+</span></summary>
  <div class="bar__panel"><div class="bar__thumb">{pic(f"img/subject-{key}.jpg", 1200, 900, s["name"] + " 수업 자료", subject_svg(key))}</div><ul>{li}</ul><p class="bar__desc">{esc(s["desc"])}</p></div>
</details>''')
        previews.append(f'<div class="preview__slide" data-id="{key}">{pic(f"img/subject-{key}.jpg", 1200, 900, "", subject_svg(key))}</div>')
    groups = []
    for i, (gk, g) in enumerate(D.GRADES.items()):
        items = "".join(f'<div class="menu__item"><div><span class="menu__name">{esc(n)}</span><small>월 4회 기준 · 과목 1개</small></div><span class="menu__price">{esc(p)}</span></div>' for n, p in g["price"])
        groups.append(f'<div class="menu__group" data-reveal style="--i:{i}"><h3>{g["name"]} <span class="muted">{g["range"]}</span></h3>{items}</div>')
    page = read("templates/index.html")
    page = (page.replace("{{SITE_URL}}", D.SITE_URL).replace("{{SITE_NAME}}", D.SITE_NAME).replace("{{NAVER_VERIFY}}", D.NAVER_VERIFY).replace("{{FONTS}}", FONTS)
                .replace("{{SVG_HERO}}", svg_hero()).replace("{{SVG_SHEET}}", svg_sheet()).replace("{{SVG_TIMETABLE}}", svg_timetable())
                .replace("{{SUBJECT_BARS}}", "\n".join(bars)).replace("{{SUBJECT_PREVIEWS}}", "\n".join(previews))
                .replace("{{PRICE_GROUPS}}", "\n".join(groups)).replace("{{FAQ}}", faq_html(D.FAQ)))
    write("index.html", page)
    pages.append(("", TODAY, "1.0"))

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
<div class="faq__text">{faq_html(faq)}</div>
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
<div class="faq__text">{faq_html(D.FAQ[:6])}</div>
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
<div class="faq__text">{faq_html(p["faq"])}</div>
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
    build_index()
    build_keyword_pages()
    posts = load_posts()
    build_blog(posts)
    build_feeds(posts)
    print(f"완료: 페이지 {len(pages)}개 (블로그 글 {len(posts)}개) → {OUT}")
