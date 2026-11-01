# -*- coding: utf-8 -*-
"""전국 중·고등학교 목록 → data/schools.json (지역 페이지 생성용).
    python -I tools_schools.py <전국초중등학교위치표준데이터.csv>
출처: 공공데이터포털 '전국초중등학교위치표준데이터'(한국교육시설안전원). CSV의 '데이터기준일자'를 그대로 기록한다.
- 중학교·고등학교, 운영 중인 본교·분교만.
- 지역 단위 = 시도 + 시군구(구가 있는 시는 구 단위). 세종은 시 전체 하나.
- 동/읍/면은 지번주소에서 뽑아 '주요 지역'으로 쓴다."""
import csv, sys, re, json, pathlib, collections
sys.stdout.reconfigure(encoding="utf-8")
src = pathlib.Path(sys.argv[1])
raw = src.read_bytes()
for enc in ("utf-8-sig", "cp949"):
    try: txt = raw.decode(enc); break
    except UnicodeDecodeError: pass
rows = list(csv.DictReader(txt.splitlines()))

SIDO_SHORT = {"서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구", "인천광역시": "인천", "광주광역시": "광주", "대전광역시": "대전", "울산광역시": "울산",
              "세종특별자치시": "세종", "경기도": "경기", "강원특별자치도": "강원", "충청북도": "충북", "충청남도": "충남", "전북특별자치도": "전북", "전라남도": "전남",
              "경상북도": "경북", "경상남도": "경남", "제주특별자치도": "제주"}
ADDR = re.compile(r"(\S+?(?:특별시|광역시|특별자치시|특별자치도|도))\s+(\S+?(?:시|군|구))(?:\s+(\S+?구)(?=\s|$))?(?:\s+(\S+?(?:동|읍|면|가|리)))?")

def parse(addr):
    if (addr or "").startswith("세종특별자치시"):
        m2 = re.match(r"세종특별자치시\s+(\S+?(?:동|읍|면))", addr)
        return "세종특별자치시", "세종특별자치시", "", (m2.group(1) if m2 else "")
    m = ADDR.match(addr or "")
    if not m: return None
    sido, a, b, dong = m.groups()
    if not a.endswith("시"):          # 구는 '시' 아래에만 있음 (강남구 압구정동 → 압구 오인 방지)
        if b: dong = dong or ""; b = ""
        m3 = re.match(re.escape(sido) + r"\s+" + re.escape(a) + r"\s+(\S+?(?:동|읍|면|가|리))", addr)
        dong = m3.group(1) if m3 else dong
    if sido == "세종특별자치시":  # '세종특별자치시 조치원읍 …' 처럼 시군구가 없음
        m2 = re.match(r"세종특별자치시\s+(\S+?(?:동|읍|면))", addr)
        return sido, "세종특별자치시", "", (m2.group(1) if m2 else "")
    return sido, a, b or "", dong or ""

regions = collections.OrderedDict()
skipped = 0
for r in rows:
    if r["학교급구분"] not in ("중학교", "고등학교") or r["운영상태"] != "운영": continue
    p = parse(r["소재지지번주소"]) or parse(r["소재지도로명주소"])
    if not p: skipped += 1; print("  파싱 실패:", r["학교명"], r["소재지지번주소"], "|", r["소재지도로명주소"]) if skipped <= 5 else None; continue
    sido, a, b, dong = p
    sgg = (a + " " + b).strip() if b else a
    key = (sido, sgg)
    reg = regions.setdefault(key, {"sido": sido, "sido_short": SIDO_SHORT.get(sido, sido), "sgg": sgg, "city": a, "gu": b,
                                   "slug": f'{SIDO_SHORT.get(sido, sido)}-{sgg.replace(" ", "-")}' if sido != "세종특별자치시" else "세종-세종시",   # 시도 허브(area/세종/)와 겹치지 않게
                                   "offices": collections.Counter(), "schools": [], "dongs": collections.Counter()})
    reg["offices"][r["교육지원청명"]] += 1
    if dong and not re.fullmatch(r"\d+.*", dong): reg["dongs"][dong] += 1
    reg["schools"].append({"name": r["학교명"], "level": r["학교급구분"], "type": r["설립형태"], "branch": r["본교분교구분"] == "분교", "dong": dong})

out = []
for (sido, sgg), reg in sorted(regions.items(), key=lambda kv: (list(SIDO_SHORT).index(kv[0][0]) if kv[0][0] in SIDO_SHORT else 99, kv[0][1])):
    reg["schools"].sort(key=lambda s: (s["level"] != "중학교", s["name"]))
    reg["offices"] = [o for o, _ in reg["offices"].most_common()]
    reg["dongs"] = [d for d, _ in reg["dongs"].most_common(12)]
    reg["mid"] = sum(1 for s in reg["schools"] if s["level"] == "중학교")
    reg["high"] = sum(1 for s in reg["schools"] if s["level"] == "고등학교")
    out.append(reg)

data = {"source": {"name": "전국초중등학교위치표준데이터(한국교육시설안전원, 공공데이터포털)", "date": rows[0]["데이터기준일자"], "note": "중·고등학교, 운영 중인 학교만. 학교명·소재지는 공공데이터 기준이며 과외나루와 학교는 관계가 없습니다."},
        "regions": out}
dst = pathlib.Path(__file__).parent / "data" / "schools.json"
dst.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
slugs = [r["slug"] for r in out]
assert len(slugs) == len(set(slugs)), "slug 중복"
print(f"지역 {len(out)}개, 학교 {sum(len(r['schools']) for r in out)}곳(중 {sum(r['mid'] for r in out)}, 고 {sum(r['high'] for r in out)}), 주소 파싱 실패 {skipped}, 기준일 {data['source']['date']} → {dst} ({dst.stat().st_size//1024}KB)")
print("예:", [(r["slug"], r["mid"], r["high"], r["dongs"][:3]) for r in out[:3]])
