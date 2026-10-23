# 블로그 글 스펙 검사(공백 포함 글자수, 이전 프로젝트 기준과 동일): 서론 300자+, h2 6개+, 각 h2 섹션 700자+, FAQ 3개, 전체 2000자+
import re, sys, pathlib
sys.stdout.reconfigure(encoding="utf-8")
def plain(h): return re.sub(r"<[^>]+>", "", h).strip()
ok_all = True
for f in sys.argv[1:]:
    t = pathlib.Path(f).read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", t, re.S); meta, body = m.group(1), m.group(2)
    title = re.search(r"^title:\s*(.+)$", meta, re.M).group(1)
    parts = re.split(r"(?=<h2[ >])", body)
    intro, secs = parts[0], parts[1:]
    faq_i = next((i for i, s in enumerate(secs) if "자주 묻는 질문" in s[:80]), None)
    faq = secs[faq_i] if faq_i is not None else ""
    body_secs = [s for i, s in enumerate(secs) if i != faq_i]
    probs = []
    if len(plain(intro)) < 300: probs.append(f"서론 {len(plain(intro))}자")
    if len(body_secs) < 6: probs.append(f"소제목 {len(body_secs)}개")
    for s in body_secs:
        h = re.search(r"<h2[^>]*>(.*?)</h2>", s).group(1); n = len(plain(s))
        if n < 700: probs.append(f"[{h}] {n}자")
    nfaq = len(re.findall(r"<h3", faq))
    if nfaq != 3: probs.append(f"FAQ {nfaq}개")
    if "<strong>" not in body: probs.append("강조 없음")
    total = len(plain(body))
    if total < 2000: probs.append(f"전체 {total}자")
    print(("OK  " if not probs else "FAIL") + f" {pathlib.Path(f).name} | {title} | 전체 {total}자, 소제목 {len(body_secs)}, FAQ {nfaq}" + ("" if not probs else " | " + "; ".join(probs)))
    ok_all &= not probs
sys.exit(0 if ok_all else 1)
