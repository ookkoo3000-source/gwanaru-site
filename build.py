#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""사이트 빌드: templates/ + data/content.py + posts/*.md  →  정적 HTML, sitemap.xml, rss.xml, robots.txt, 404.html

    python build.py

- 블로그 글은 posts/ 폴더에 .md 파일을 넣기만 하면 됩니다 (형식은 posts/README.md 참고).
- sitemap의 lastmod는 .lastmod.json에 페이지 본문 해시를 저장해 두고, 본문이 실제로 바뀐 날만 갱신합니다.
"""
import html, os, re, sys, json, hashlib, datetime, pathlib, email.utils
import markdown, yaml

ROOT = pathlib.Path(__file__).parent
sys.path.insert(0, str(ROOT / "data"))
import content as D  # noqa: E402

OUT = ROOT
TODAY = datetime.date.today().isoformat()
esc = html.escape
pages = []   # (path, lastmod, priority)

LASTMOD_FILE = ROOT / ".lastmod.json"
try: LASTMOD = json.loads(LASTMOD_FILE.read_text(encoding="utf-8"))
except Exception: LASTMOD = {}

def read(p): return (ROOT / p).read_text(encoding="utf-8")
def write(p, s):
    p = OUT / p; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(s, encoding="utf-8")

def lastmod_for(path, body, fixed=None):
    """본문 해시가 바뀐 날을 lastmod로. fixed(블로그 글 날짜)가 있으면 그 날과 변경일 중 늦은 쪽."""
    h = hashlib.sha1(body.replace("\r\n", "\n").encode("utf-8")).hexdigest()   # OS별 줄바꿈 차이로 해시가 달라지지 않게
    rec = LASTMOD.get(path)
    if not rec or rec.get("hash") != h:
        rec = {"hash": h, "date": TODAY}
        LASTMOD[path] = rec
    d = rec["date"]
    if fixed and fixed > d: d = fixed
    return d

# ---------------------------------------------------------------- 공통 조각
FONTS = """<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
<link href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css" rel="stylesheet">"""

FAVICON = """<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='7' fill='%2310243a'/%3E%3Cpath d='M7 20c3-3 6-3 9 0s6 3 9 0' stroke='%2345c2b6' stroke-width='3' fill='none' stroke-linecap='round'/%3E%3Cpath d='M7 13c3-3 6-3 9 0s6 3 9 0' stroke='%23fff' stroke-width='3' fill='none' stroke-linecap='round'/%3E%3C/svg%3E">"""

LOGO_MARK = ('<svg class="logo__mark" viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" rx="7" fill="#10243a"/>'
             '<path d="M7 20c3-3 6-3 9 0s6 3 9 0" stroke="#45c2b6" stroke-width="3" fill="none" stroke-linecap="round"/>'
             '<path d="M7 13c3-3 6-3 9 0s6 3 9 0" stroke="#fff" stroke-width="3" fill="none" stroke-linecap="round"/></svg>')

def analytics():
    if not D.GA_ID: return ""
    return f"""<script async src="https://www.googletagmanager.com/gtag/js?id={D.GA_ID}"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}gtag('js',new Date());gtag('config','{D.GA_ID}',{{anonymize_ip:true}});</script>"""

def verify_tags():
    t = f'<meta name="naver-site-verification" content="{D.NAVER_VERIFY}">' if D.NAVER_VERIFY else ""
    if D.GOOGLE_VERIFY: t += f'\n<meta name="google-site-verification" content="{D.GOOGLE_VERIFY}">'
    return t

ORG_LD = {"@context": "https://schema.org", "@type": "Organization", "name": D.SITE_NAME, "url": D.SITE_URL + "/",
          "telephone": D.PHONE_INTL, "description": "초·중·고 1:1 방문·화상 과외 상담 및 선생님 연결",
          "contactPoint": [{"@type": "ContactPoint", "telephone": D.PHONE_INTL, "contactType": "customer service", "availableLanguage": "ko"}]}

def head(title, desc, path, extra="", depth=1, jsonld=None, og_type="website"):
    rel = "../" * depth
    url = f"{D.SITE_URL}/{path}"
    lds = [ORG_LD] if path == "" else []
    if jsonld: lds += jsonld if isinstance(jsonld, list) else [jsonld]
    ld = "".join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in lds)
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{url}">
<meta name="robots" content="index, follow">
{verify_tags()}
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="{D.SITE_NAME}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{D.SITE_URL}/img/og.png">
<meta property="og:locale" content="ko_KR">
<meta name="theme-color" content="#10243a">
{extra}
<link rel="alternate" type="application/rss+xml" title="{D.SITE_NAME} 블로그" href="{D.SITE_URL}/rss.xml">
{FAVICON}
{FONTS}
<link rel="stylesheet" href="{rel}css/site.css">
{ld}
{analytics()}
</head>
<body>
<a class="skip" href="#main">본문으로 바로가기</a>
{header(rel)}
<main id="main">
"""

NAV = [("초등", "elementary/"), ("중등", "middle/"), ("고등", "high/"), ("화상과외", "online/"), ("방문과외", "visit/"), ("수업료 안내", "cost/"), ("블로그", "blog/")]

def header(rel=""):
    home = rel or "./"
    links = "".join(f'<a href="{rel}{h}">{esc(t)}</a>' for t, h in NAV)
    return f"""<header class="site-head">
  <div class="container site-head__in">
    <a class="logo" href="{home}">{LOGO_MARK}<span>{D.SITE_NAME}</span></a>
    <nav class="gnb" id="gnb" aria-label="주요 메뉴">{links}</nav>
    <div class="site-head__cta">
      <a class="btn btn--line btn--sm" href="tel:{D.PHONE_RAW}" data-track="tel_click">전화 {D.PHONE}</a>
      <a class="btn btn--primary btn--sm" href="{rel}contact/">상담 신청</a>
    </div>
    <button class="menu-btn" type="button" aria-controls="gnb" aria-expanded="false" aria-label="메뉴 열기"><span></span><span></span><span></span></button>
  </div>
</header>"""

def footer(rel=""):
    home = rel or "./"
    grades = "".join(f'<li><a href="{rel}{gk}/">{g["name"]} 과외</a></li>' for gk, g in D.GRADES.items())
    return f"""</main>
<footer class="site-foot">
  <div class="container site-foot__in">
    <div class="site-foot__brand">
      <a class="logo logo--light" href="{home}">{LOGO_MARK}<span>{D.SITE_NAME}</span></a>
      <p>초·중·고 1:1 방문·화상 과외 상담과 선생님 연결을 안내합니다.</p>
      <p class="site-foot__tel"><a href="tel:{D.PHONE_RAW}" data-track="tel_click">{D.PHONE}</a><br><small>전화 연결이 어려우면 문자나 <a href="{rel}contact/">상담 신청서</a>를 남겨 주세요. 확인 후 연락드립니다.</small></p>
    </div>
    <div class="site-foot__cols">
      <div><h2>학년별</h2><ul>{grades}</ul></div>
      <div><h2>안내</h2><ul><li><a href="{rel}online/">화상과외</a></li><li><a href="{rel}visit/">방문과외</a></li><li><a href="{rel}cost/">수업료 상담 안내</a></li><li><a href="{rel}contact/">상담 신청</a></li></ul></div>
      <div><h2>읽을거리</h2><ul><li><a href="{rel}blog/">블로그</a></li><li><a href="{rel}rss.xml">RSS</a></li><li><a href="{rel}sitemap.xml">사이트맵</a></li></ul></div>
    </div>
  </div>
  <div class="container site-foot__bottom">© 2026 {D.SITE_NAME}</div>
</footer>
<div class="quickbar" id="quickbar">
  <a href="tel:{D.PHONE_RAW}" data-track="tel_click">전화 상담</a>
  <a class="quickbar__main" href="{rel}contact/">무료 체험 상담 신청</a>
</div>
<script src="{rel}js/site.js" defer></script>
</body>
</html>
"""

def foot(depth=1):
    return footer("../" * depth)

def faq_html(items):
    return '<div class="faq">' + "\n".join(f'<details class="qa"><summary>{esc(q)}</summary><div class="qa__a"><p>{esc(a)}</p></div></details>' for q, a in items) + "</div>"

def basic_faq(name):
    """핵심 페이지가 아닌 안내 페이지용 짧은 FAQ. 수업료는 여기 한 번만."""
    return [(f"{name}는 어떻게 시작하나요?", f"전화·문자·신청서로 학년, 과목, 지금 어려운 부분을 알려주시면 조건에 맞는 선생님을 안내하고, {D.TRIAL} 뒤에 계속할지 정하시면 됩니다."),
            (f"{name} 수업료는 얼마인가요?", D.PRICE_NOTE + " 수업료를 정하는 조건은 수업료 상담 안내 페이지에 있습니다.")]

def faq_ld(items):
    return {"@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in items]}

def crumbs(depth, *parts):
    rel = "../" * depth
    out = [f'<a href="{rel}">홈</a>']
    for t, h in parts:
        out.append(f'<a href="{rel}{h}">{esc(t)}</a>' if h else f"<span>{esc(t)}</span>")
    return '<nav class="crumbs" aria-label="현재 위치">' + " › ".join(out) + "</nav>"

def picture(src_base, w, h, alt, lazy=True, cls=""):
    """img/foo.jpg + img/foo.webp 가 있으면 <picture>. 첫 화면 이미지는 lazy=False."""
    lz = ' loading="lazy" decoding="async"' if lazy else ' fetchpriority="high" decoding="async"'
    c = f' class="{cls}"' if cls else ""
    webp = f'<source type="image/webp" srcset="{src_base}.webp">' if (ROOT / (src_base.split("/", 1)[-1] if src_base.startswith("../") else src_base)).with_suffix(".webp").exists() else ""
    return f'<picture{c}>{webp}<img src="{src_base}.jpg" width="{w}" height="{h}" alt="{esc(alt)}"{lz}></picture>'

def form_html(rel="", page_url=None):
    subj = "".join(f'<label class="chk"><input type="checkbox" name="과목" value="{s["name"]}"> {s["name"]}</label>' for s in D.SUBJECTS.values())
    grades = "".join(f'<option>{o}</option>' for o in ["초등 1~3학년", "초등 4~6학년", "중학교 1학년", "중학교 2학년", "중학교 3학년", "고등학교 1학년", "고등학교 2학년", "고등학교 3학년", "기타"])
    return f"""<form class="apply" id="apply-form" method="post" action="{D.FORM_ENDPOINT}" novalidate>
  <input type="hidden" name="_subject" value="{D.FORM_SUBJECT}">
  <input type="hidden" name="_template" value="table">
  <input type="hidden" name="_captcha" value="false">
  <input type="hidden" name="신청 페이지" value="{page_url or D.SITE_URL + "/"}">
  <input type="hidden" name="처음 들어온 페이지" value="">
  <input type="hidden" name="유입 경로" value="">
  <p class="hp" aria-hidden="true"><label>이 칸은 비워 두세요<input type="text" name="_honey" tabindex="-1" autocomplete="off"></label></p>
  <div class="apply__grid">
    <div class="field-wrap">
      <label for="f-phone">연락처 <b>*</b></label>
      <input class="field" id="f-phone" name="연락처" type="tel" inputmode="tel" autocomplete="tel" placeholder="010-0000-0000" required>
    </div>
    <div class="field-wrap">
      <label for="f-grade">학년 <b>*</b></label>
      <select class="field" id="f-grade" name="학년" required><option value="">선택</option>{grades}</select>
    </div>
  </div>
  <fieldset class="field-wrap">
    <legend>희망 과목 <b>*</b> <small>(여러 개 선택 가능)</small></legend>
    <div class="chks">{subj}</div>
  </fieldset>
  <fieldset class="field-wrap">
    <legend>수업 방식 <b>*</b></legend>
    <div class="chks">
      <label class="chk"><input type="radio" name="방식" value="방문" required> 방문</label>
      <label class="chk"><input type="radio" name="방식" value="화상"> 화상</label>
      <label class="chk"><input type="radio" name="방식" value="상담 후 결정"> 상담 후 결정</label>
    </div>
  </fieldset>
  <div class="field-wrap" id="f-region-wrap">
    <label for="f-region">지역 <small>(방문 희망 시 시·구·동까지)</small></label>
    <input class="field" id="f-region" name="지역" type="text" autocomplete="address-level2" placeholder="예: 서울 양천구 목동">
  </div>
  <div class="field-wrap">
    <label for="f-note">학생의 고민 또는 연락 가능한 시간 <small>(선택)</small></label>
    <textarea class="field" id="f-note" name="내용" rows="3" placeholder="예: 중2 수학 함수 단원부터 막혀요 / 평일 저녁 7시 이후 통화 가능"></textarea>
  </div>
  <label class="chk chk--agree"><input type="checkbox" name="개인정보동의" value="동의" required> <span>개인정보 수집·이용에 동의합니다. <b>*</b></span></label>
  <p class="apply__privacy">수집 항목: 연락처, 학년, 희망 과목, 수업 방식, 지역, 남기신 내용 · 목적: 과외 상담 연락 · 상담 목적 외에는 사용하지 않으며, 삭제를 원하시면 {D.PHONE}로 알려주세요.</p>
  <p class="apply__error" id="apply-error" role="alert" hidden></p>
  <button class="btn btn--primary btn--lg apply__submit" type="submit" id="apply-submit">상담 신청 보내기</button>
  <p class="apply__alt">문자로 남기시려면 <a href="sms:{D.PHONE_RAW}?body={html.escape('과외 상담 신청합니다. 학년/과목/지역: ')}" data-track="sms_click">문자 보내기</a> (문자 앱이 열리고 직접 전송하셔야 접수됩니다) · 전화 <a href="tel:{D.PHONE_RAW}" data-track="tel_click">{D.PHONE}</a></p>
</form>
<div class="apply__done" id="apply-done" hidden tabindex="-1">
  <h3>상담 신청이 접수되었습니다</h3>
  <p>남겨 주신 연락처로 확인 후 연락드리겠습니다. 급하시면 <a href="tel:{D.PHONE_RAW}" data-track="tel_click">{D.PHONE}</a>로 전화 주세요.</p>
</div>"""

def cta_box(rel="", title="상담 신청", lead=None):
    lead = lead or "학년, 과목, 지금 어려운 부분을 알려주시면 조건에 맞는 선생님을 안내해 드립니다. 상담과 " + D.TRIAL + "은 무료입니다."
    return f"""<section class="cta-box" aria-labelledby="cta-h">
  <div>
    <h2 id="cta-h">{esc(title)}</h2>
    <p>{esc(lead)}</p>
  </div>
  <div class="cta-box__actions">
    <a class="btn btn--primary btn--lg" href="{rel}contact/">무료 체험 상담하기</a>
    <a class="btn btn--line btn--lg" href="tel:{D.PHONE_RAW}" data-track="tel_click">전화 상담하기</a>
  </div>
</section>"""

def aside(depth=1, links=()):
    rel = "../" * depth
    li = "".join(f'<li><a href="{rel}{h}">{esc(t)}</a></li>' for t, h in links)
    return f"""<aside class="page__aside">
  <div class="aside-card">
    <h2>무료 체험 상담</h2>
    <p>학년, 과목, 지금 어려운 부분을 알려주시면 조건에 맞는 선생님을 안내해 드립니다.</p>
    <a class="btn btn--primary" href="{rel}contact/">상담 신청하기</a>
    <a class="btn btn--ghost" href="tel:{D.PHONE_RAW}" data-track="tel_click">전화 {D.PHONE}</a>
  </div>
  <nav class="aside-links" aria-label="함께 보기">
    <h2>함께 보기</h2>
    <ul>{li}</ul>
  </nav>
</aside>"""

def related_posts_html(posts, rel, grade=None, subject=None, slugs=None, n=3):
    if slugs:
        sel = [p for s in slugs for p in posts if p["slug"] == s]
    else:
        sel = [p for p in posts if (grade and p["grade"] == grade) or (subject and p["subject"] == subject)]
        sel = sorted(sel, key=lambda p: ((p["grade"] == grade) + (p["subject"] == subject), p["date"]), reverse=True)
    sel = sel[:n]
    if not sel: return ""
    li = "".join(f'<li><a href="{rel}blog/{p["slug"]}/">{esc(p["title"])}</a><span>{p["date"].isoformat()}</span></li>' for p in sel)
    return f'<h2>관련 글</h2><ul class="post-list">{li}</ul>'

# ---------------------------------------------------------------- 메인
def build_index(posts):
    # ② 학년×과목 찾기: 행=과목, 열=학년. 버튼 이름 = 도착 페이지 이름
    rows = []
    for sk, s in D.SUBJECTS.items():
        cells = "".join(f'<td><a href="{gk}-{sk}/">{g["name"]} {s["name"]}</a></td>' for gk, g in D.GRADES.items())
        rows.append(f'<tr><th scope="row">{esc(s["name"])}<small>{esc(s["desc"])}</small></th>{cells}</tr>')
    heads = "".join(f'<th scope="col"><a href="{gk}/">{g["name"]} 과외<small>{g["range"]}</small></a></th>' for gk, g in D.GRADES.items())
    find = f'<div class="find-wrap"><table class="find"><thead><tr><th scope="col">과목</th>{heads}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
    concerns = "".join(f'<li><h3>{esc(q)}</h3><p>{esc(a)}</p><a href="{h}">관련 수업 안내 →</a></li>' for q, a, h in D.CONCERNS)
    proc = {t: p for t, p in D.PROCESS}
    how_keys = ["상담에서 확인하는 것", "체험 수업에서 확인할 수 있는 것", "진도와 교재", "숙제와 오답", "학부모님께 전달"]
    how = "".join(f'<div class="dl__row"><dt>{esc(k)}</dt><dd>{esc(proc[k])}</dd></div>' for k in how_keys)
    teacher = "".join(f'<div class="dl__row"><dt>{esc(k)}</dt><dd>{esc(proc[k])}</dd></div>' for k in ["선생님을 연결하는 기준", "선생님과 맞지 않을 때"])
    steps = "".join(f'<li><span class="step__no">{i}</span><h3>{esc(t)}</h3><p>{esc(d)}</p></li>' for i, (t, d) in enumerate(D.STEPS, 1))
    latest = "".join(f'<li><a href="blog/{p["slug"]}/">{esc(p["title"])}</a><span>{p["date"].isoformat()}</span></li>' for p in posts[:4])
    page = read("templates/index.html")
    rep = {"{{HEADER}}": header(""), "{{FOOTER}}": footer(""), "{{SITE_URL}}": D.SITE_URL, "{{SITE_NAME}}": D.SITE_NAME,
           "{{TAGLINE}}": esc(D.TAGLINE).replace("\n", "<br>"), "{{TAGLINE_SUB}}": esc(D.TAGLINE_SUB).replace("\n", "<br>"), "{{PHONE}}": D.PHONE, "{{PHONE_RAW}}": D.PHONE_RAW,
           "{{TRIAL}}": D.TRIAL, "{{PRICE_NOTE}}": esc(D.PRICE_NOTE), "{{VERIFY}}": verify_tags(), "{{FONTS}}": FONTS, "{{FAVICON}}": FAVICON, "{{ANALYTICS}}": analytics(),
           "{{HERO_PIC}}": picture("img/hero", 1500, 1000, "책상에서 선생님과 학생이 수학 문제집을 함께 보며 풀이하는 1:1 수업 장면", lazy=False),
           "{{FIND}}": find, "{{CONCERNS}}": concerns, "{{HOW}}": how, "{{TEACHER}}": teacher, "{{STEPS}}": steps,
           "{{LATEST_POSTS}}": latest, "{{FAQ}}": faq_html(D.FAQ), "{{FORM}}": form_html("", D.SITE_URL + "/#apply"),
           "{{LD}}": "".join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in [ORG_LD, faq_ld(D.FAQ)])}
    for k, v in rep.items(): page = page.replace(k, v)
    write("index.html", page)
    body = page.split("<main", 1)[1].split("</main>", 1)[0]
    pages.append(("", lastmod_for("", body), "1.0"))

# ---------------------------------------------------------------- 학년×과목 · 학년 · 안내 페이지
def service_page(slug, title, desc, body, links, depth=1, jsonld=None, extra=""):
    full = f'<div class="page container"><div class="page__grid"><article class="page__main">{body}</article>{aside(depth, links)}</div></div>'
    write(slug + "index.html", head(title, desc, slug, extra, depth, jsonld) + full + foot(depth))
    return body

def build_keyword_pages(posts):
    for gk, g in D.GRADES.items():
        for sk, s in D.SUBJECTS.items():
            slug = f"{gk}-{sk}/"
            name = f'{g["name"]} {s["name"]} 과외'
            f = D.FOCUS[(gk, sk)]
            core = D.CORE_PAGES.get(f"{gk}-{sk}")
            title = f'{name} | 1:1 방문·화상, {D.TRIAL} | {D.SITE_NAME}'
            desc = f'{g["full"]} {s["name"]} 1:1 과외 상담. {f["p"][0][:70]}… 방문·화상 선택, 상담과 체험 수업은 무료.'
            b = [crumbs(1, (g["name"] + " 과외", gk + "/"), (name, None)),
                 f"<h1>{esc(name)}</h1>",
                 f'<p class="lead">{esc(g["full"])} {esc(s["name"])} 1:1 과외를 방문 또는 화상으로 상담하고, 조건에 맞는 선생님을 안내합니다. 상담과 {D.TRIAL}은 무료입니다.</p>',
                 f'<h2>{esc(f["h"])}</h2>' + "".join(f"<p>{esc(x)}</p>" for x in f["p"]),
                 "<h2>이런 학생에게 맞습니다</h2><ul class=\"plain\">" + "".join(f"<li>{esc(x)}</li>" for x in g["fit"]) + "</ul>",
                 "<h2>상담과 체험 수업에서 확인하는 것</h2><p>상담에서는 아래를 여쭤보고, 체험 수업에서는 선생님이 직접 점검합니다.</p><ul class=\"plain\">" + "".join(f"<li>{esc(x)}</li>" for x in f["check"]) + "</ul>",
                 f'<h2>{esc(s["name"])} 수업은 이렇게 진행합니다</h2><p>{esc(s["intro"])}</p><ul class="plain">' + "".join(f"<li>{esc(x)}</li>" for x in s["points"]) + "</ul>"]
            if core:
                b += [f'<h2>{esc(core["example"]["h"])}</h2><p class="example">{esc(core["example"]["p"])}</p>',
                      f'<h2>학습 계획과 교재, 숙제 관리</h2><p>{esc(core["plan"])}</p>',
                      f'<h2>방문과 화상, 어느 쪽이 맞을까</h2><p>{esc(core["mode"])}</p>',
                      f'<h2>{esc(name)} 자주 묻는 질문</h2>' + faq_html(core["faq"]),
                      related_posts_html(posts, "../", slugs=core["related"])]
            else:
                b += [f'<h2>진행 순서</h2><p>상담 → 선생님 안내 → {D.TRIAL} → 수업 결정 순서로 진행됩니다. 자세한 과정은 <a href="../#steps">진행 순서 안내</a>에 있습니다.</p>',
                      f'<h2>{esc(name)} 자주 묻는 질문</h2>' + faq_html(basic_faq(name)),
                      related_posts_html(posts, "../", grade=gk, subject=sk)]
            links = [(f'{g["name"]} {o["name"]} 과외', f"{gk}-{ok}/") for ok, o in D.SUBJECTS.items() if ok != sk] + \
                    [(f'{o["name"]} {s["name"]} 과외', f"{ok}-{sk}/") for ok, o in D.GRADES.items() if ok != gk] + \
                    [("화상과외", "online/"), ("방문과외", "visit/"), ("수업료 상담 안내", "cost/")]
            body = service_page(slug, title, desc, "\n".join(b), links, 1, faq_ld(core["faq"]) if core else None)
            pages.append((slug, lastmod_for(slug, body), "0.9" if core else "0.8"))

        # 학년 허브
        slug = f"{gk}/"
        title = f'{g["name"]} 과외 | 국어·영어·수학·과학·사회 1:1 방문·화상 | {D.SITE_NAME}'
        desc = f'{g["full"]} 1:1 과외 상담. {g["intro"][:60]}… 과목별 수업 안내와 방문·화상 선택, 상담과 체험 수업은 무료.'
        subj = "".join(f'<li><a href="../{gk}-{sk}/">{esc(g["name"])} {esc(s["name"])} 과외</a><p>{esc(D.FOCUS[(gk, sk)]["p"][0][:90])}…</p></li>' for sk, s in D.SUBJECTS.items())
        b = [crumbs(1, (g["name"] + " 과외", None)),
             f'<h1>{esc(g["name"])} 과외 <span class="muted">{esc(g["range"])}</span></h1>',
             f'<p class="lead">{esc(g["intro"])}</p>',
             f'<h2>과목별 안내</h2><ul class="subject-list">{subj}</ul>',
             "<h2>이런 학생에게 맞습니다</h2><ul class=\"plain\">" + "".join(f"<li>{esc(p)}</li>" for p in g["fit"]) + "</ul>",
             f'<h2>진행 순서</h2><p>상담 → 선생님 안내 → {D.TRIAL} → 수업 결정 순서로 진행됩니다. 자세한 과정은 <a href="../#steps">진행 순서 안내</a>에 있습니다.</p>',
             f'<h2>{esc(g["name"])} 과외 자주 묻는 질문</h2>' + faq_html(basic_faq(g["name"] + " 과외")),
             related_posts_html(posts, "../", grade=gk, n=4)]
        body = service_page(slug, title, desc, "\n".join(b), [(f'{o["name"]} 과외', f"{ok}/") for ok, o in D.GRADES.items() if ok != gk] + [("화상과외", "online/"), ("방문과외", "visit/")], 1)
        pages.append((slug, lastmod_for(slug, body), "0.9"))

    for key, p in D.EXTRA_PAGES.items():
        slug = f"{key}/"
        title = f'{p["title"]} | {D.SITE_NAME}' if key == "cost" else f'{p["title"]} | 초중고 1:1, {D.TRIAL} | {D.SITE_NAME}'
        secs = "".join(f"<h2>{esc(h)}</h2><p>{esc(t)}</p>" for h, t in p["sections"])
        b = [crumbs(1, (p["title"], None)), f'<h1>{esc(p["h1"])}</h1>', f'<p class="lead">{esc(p["intro"])}</p>', secs,
             "<h2>이런 경우에 맞습니다</h2><ul class=\"plain\">" + "".join(f"<li>{esc(x)}</li>" for x in p["fit"]) + "</ul>",
             "<h2>자주 묻는 질문</h2>" + faq_html(p["faq"]),
             related_posts_html(posts, "../", slugs={"online": ["2026-10-19-online-vs-visit-tutoring", "2026-10-21-pre-high-english-prep"], "visit": ["2026-10-19-online-vs-visit-tutoring", "2026-10-24-elementary-math-tutoring-cost"], "cost": ["2026-10-23-middle-math-tutoring-cost", "2026-10-24-high-math-tutoring-cost", "2026-10-24-elementary-math-tutoring-cost"]}[key])]
        body = service_page(slug, title, p["desc"], "\n".join(b), [(f'{o["name"]} 과외', f"{ok}/") for ok, o in D.GRADES.items()] + [(q["title"], f"{qk}/") for qk, q in D.EXTRA_PAGES.items() if qk != key], 1, faq_ld(p["faq"]))
        pages.append((slug, lastmod_for(slug, body), "0.9"))

    # 상담 신청 페이지
    slug = "contact/"
    ask = "".join(f"<li>{esc(x)}</li>" for x in ["학년과 학교, 과목", "최근 시험 결과나 지금 막히는 단원", "학원·학습지 병행 여부", "희망 요일과 시간대", "방문·화상 선호(방문이면 지역)", "아이 성향"])
    b = [crumbs(1, ("상담 신청", None)), "<h1>무료 체험 상담 신청</h1>",
         f'<p class="lead">아래 신청서를 남기시면 확인 후 연락드립니다. 전화 <a href="tel:{D.PHONE_RAW}" data-track="tel_click">{D.PHONE}</a>로 바로 상담하셔도 됩니다. 상담과 {D.TRIAL}은 무료입니다.</p>',
         form_html("../", D.SITE_URL + "/contact/"),
         f'<h2>상담에서 여쭤보는 것</h2><p>미리 생각해 두시면 상담이 빨라집니다.</p><ul class="plain">{ask}</ul>']
    body = service_page(slug, f"상담 신청 | 초중고 1:1 과외 {D.TRIAL} | {D.SITE_NAME}", f"초·중·고 1:1 과외 무료 체험 상담 신청. 연락처, 학년, 희망 과목, 방문·화상만 남기시면 확인 후 연락드립니다. 전화 {D.PHONE}", "\n".join(b),
                        [(f'{o["name"]} 과외', f"{ok}/") for ok, o in D.GRADES.items()] + [("화상과외", "online/"), ("방문과외", "visit/"), ("수업료 상담 안내", "cost/")], 1)
    pages.append((slug, lastmod_for(slug, body), "0.8"))

    # 404 (GitHub Pages가 자동 사용). 과거 도메인 주소로 들어온 방문자 안내용 — 색인 제외
    nf = f"""<div class="page container"><div class="page__grid"><article class="page__main">
<h1>찾으시는 페이지가 없습니다</h1>
<p class="lead">주소가 바뀌었거나 삭제된 페이지입니다. 이 주소(edumegong.co.kr)는 현재 초·중·고 1:1 과외 상담 사이트 <strong>{D.SITE_NAME}</strong>로 운영되고 있으며, 이전에 운영되던 사이트의 페이지는 제공하지 않습니다.</p>
<h2>이런 내용을 찾고 계셨다면</h2>
<ul class="plain"><li><a href="/">과외나루 홈</a> — 초·중·고 1:1 과외 상담 안내</li><li><a href="/online/">화상과외</a> · <a href="/visit/">방문과외</a></li><li><a href="/blog/">블로그</a> — 학년별·과목별 공부와 과외 선택에 관한 글</li><li><a href="/contact/">상담 신청</a></li></ul>
</article>{aside(1, [(f'{o["name"]} 과외', f"{ok}/") for ok, o in D.GRADES.items()])}</div></div>"""
    h = head(f"페이지를 찾을 수 없습니다 | {D.SITE_NAME}", "요청하신 페이지가 없습니다.", "404.html", "", 0).replace('<meta name="robots" content="index, follow">', '<meta name="robots" content="noindex, follow">').replace(f'<link rel="canonical" href="{D.SITE_URL}/404.html">', "")
    page404 = h + nf + foot(0)
    page404 = re.sub(r'(href|src)="(?!https?:|//|/|#|tel:|sms:|mailto:|data:)(\./)?', r'="/', page404)
    write("404.html", page404)

# ---------------------------------------------------------------- 블로그
def slugify(s):
    s = re.sub(r"[^\w\-가-힣]+", "-", s.strip().lower()).strip("-")
    return s[:80] or "post"

def load_posts():
    posts = []
    for f in sorted((ROOT / "posts").glob("*.md")):
        if f.name.lower() in ("readme.md", "keywords.md"): continue
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
                      "keywords": meta.get("keywords", ""), "grade": meta.get("grade", ""), "subject": meta.get("subject", ""), "updated": str(meta.get("updated", "") or "")})
    posts.sort(key=lambda p: (p["date"], p["slug"]), reverse=True)
    return posts

def build_blog(posts):
    for p in posts:
        slug = f"blog/{p['slug']}/"
        title = f'{p["title"]} | {D.SITE_NAME} 블로그'
        related = [q for q in posts if q is not p and (q["grade"] == p["grade"] or q["subject"] == p["subject"])][:4] or [q for q in posts if q is not p][:4]
        rel_html = "".join(f'<li><a href="../{q["slug"]}/">{esc(q["title"])}</a><span>{q["date"].isoformat()}</span></li>' for q in related)
        mod = p["updated"] or p["date"].isoformat()
        ld = {"@context": "https://schema.org", "@type": "Article", "headline": p["title"], "description": p["desc"],
              "datePublished": p["date"].isoformat(), "dateModified": mod,
              "author": {"@type": "Organization", "name": D.SITE_NAME}, "publisher": {"@type": "Organization", "name": D.SITE_NAME},
              "mainEntityOfPage": f"{D.SITE_URL}/{slug}"}
        extra = f'<meta property="article:published_time" content="{p["date"].isoformat()}">'
        hubs = []
        if p["grade"] in D.GRADES and p["subject"] in D.SUBJECTS:
            hubs.append((f'{D.GRADES[p["grade"]]["name"]} {D.SUBJECTS[p["subject"]]["name"]} 과외', f'{p["grade"]}-{p["subject"]}/'))
        if p["grade"] in D.GRADES: hubs.append((f'{D.GRADES[p["grade"]]["name"]} 과외', f'{p["grade"]}/'))
        body = f"""{crumbs(2, ("블로그", "blog/"), (p["title"], None))}
<h1>{esc(p["title"])}</h1>
<p class="post-meta"><time datetime="{p["date"].isoformat()}">{p["date"].strftime("%Y년 %m월 %d일")}</time>{(' · 수정 ' + p["updated"]) if p["updated"] else ''}</p>
<div class="post">{p["html"]}</div>
<h2>함께 읽기</h2>
<ul class="post-list">{rel_html}</ul>"""
        full = f'<div class="page container"><div class="page__grid"><article class="page__main">{body}</article>{aside(2, hubs + [("화상과외", "online/"), ("방문과외", "visit/"), ("수업료 상담 안내", "cost/")])}</div></div>'
        write(slug + "index.html", head(title, p["desc"], slug, extra, 2, ld, "article") + full + foot(2))
        pages.append((slug, lastmod_for(slug, p["html"], fixed=mod), "0.7"))

    per = 30
    chunks = [posts[i:i + per] for i in range(0, max(len(posts), 1), per)] or [[]]
    for n, chunk in enumerate(chunks, 1):
        slug = "blog/" if n == 1 else f"blog/page/{n}/"
        depth = 1 if n == 1 else 3
        rel = "../" * depth
        items = "".join(f'<li><a href="{rel}blog/{q["slug"]}/">{esc(q["title"])}</a><span>{q["date"].isoformat()}</span><p>{esc(q["desc"][:110])}</p></li>' for q in chunk) or "<li>첫 글을 준비하고 있습니다.</li>"
        nav = ""
        if n > 1: nav += f'<a href="{rel}blog/{"" if n == 2 else f"page/{n-1}/"}">← 이전</a> '
        if n < len(chunks): nav += f'<a href="{rel}blog/page/{n+1}/">다음 →</a>'
        body = f"""{crumbs(depth, ("블로그", None))}
<h1>과외 블로그</h1>
<p class="lead">학년별·과목별 공부 고민과 과외 선택에 필요한 정보를 정리합니다. 글 {len(posts)}개.</p>
<ul class="post-list post-list--full">{items}</ul>
<p class="crumbs">{nav}</p>"""
        full = f'<div class="page container"><div class="page__grid"><article class="page__main">{body}</article>{aside(depth, [(f"{g["name"]} 과외", f"{gk}/") for gk, g in D.GRADES.items()] + [("화상과외", "online/"), ("방문과외", "visit/"), ("수업료 상담 안내", "cost/")])}</div></div>'
        write(slug + "index.html", head(f"과외 블로그 | 학년별·과목별 공부와 과외 선택 안내 | {D.SITE_NAME}", "초중고 과외, 화상과외, 방문과외에 대한 글. 학년별 공부법, 과외 선택 기준, 선생님 고르는 법.", slug, "", depth) + full + foot(depth))
        pages.append((slug, lastmod_for(slug, items), "0.6"))

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
    LASTMOD_FILE.write_text(json.dumps(LASTMOD, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")

if __name__ == "__main__":
    posts = load_posts()
    build_index(posts)
    build_keyword_pages(posts)
    build_blog(posts)
    build_feeds(posts)
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"완료: 페이지 {len(pages)}개 (블로그 글 {len(posts)}개) → {OUT}")
