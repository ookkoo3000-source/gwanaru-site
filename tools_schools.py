# -*- coding: utf-8 -*-
"""전국 중·고등학교 목록 → data/schools.json (지역 페이지 생성용).

  공식 API(권장):  python -I tools_schools.py --neis          # .neis_key 파일의 나이스 인증키 사용
  CSV 파일:        python -I tools_schools.py <전국초중등학교위치표준데이터.csv>

출처
- --neis: 나이스 교육정보 개방포털 '학교기본정보'(open.neis.go.kr/hub/schoolInfo). 조회일을 기준일로 기록.
- CSV:   공공데이터포털 '전국초중등학교위치표준데이터'(한국교육시설안전원). CSV의 '데이터기준일자' 사용.
규칙
- 중학교·고등학교만. 지역 단위 = 시도 + 시군구(구가 있는 시는 구 단위). 세종은 시 전체 하나.
- 동/읍/면은 주소에서 뽑아 '주요 지역'으로 쓴다."""
import csv, sys, re, json, pathlib, collections, datetime, urllib.request, urllib.parse, time
sys.stdout.reconfigure(encoding="utf-8")
ROOT = pathlib.Path(__file__).parent

SIDO_SHORT = {"서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구", "인천광역시": "인천", "광주광역시": "광주", "대전광역시": "대전", "울산광역시": "울산",
              "세종특별자치시": "세종", "경기도": "경기", "강원특별자치도": "강원", "충청북도": "충북", "충청남도": "충남", "전북특별자치도": "전북", "전라남도": "전남",
              "경상북도": "경북", "경상남도": "경남", "제주특별자치도": "제주",
              "전남광주통합특별시": "광주전남", "대전충남통합특별시": "대전충남", "대구경북통합특별시": "대구경북"}   # 2026 통합시 주소 표기 대비
OFFICES = {"B10": "서울특별시", "C10": "부산광역시", "D10": "대구광역시", "E10": "인천광역시", "F10": "광주광역시", "G10": "대전광역시", "H10": "울산광역시", "I10": "세종특별자치시",
           "J10": "경기도", "K10": "강원특별자치도", "M10": "충청북도", "N10": "충청남도", "P10": "전북특별자치도", "Q10": "전라남도", "R10": "경상북도", "S10": "경상남도", "T10": "제주특별자치도"}
ADDR = re.compile(r"(\S+?(?:통합특별시|특별시|광역시|특별자치시|특별자치도|도))\s+(\S+?(?:시|군|구))(?:\s+(\S+?구)(?=\s|$))?(?:\s+(\S+?(?:동|읍|면|가|리)))?")

SIDO_NORMALIZE = [("서울특별시", ["서울시 ", "서울 "]), ("부산광역시", ["부산시 ", "부산 "]), ("대구광역시", ["대구시 ", "대구 "]), ("인천광역시", ["인천시 ", "인천 "]),
                  ("광주광역시", ["광주시 ", "광주 "]), ("대전광역시", ["대전시 ", "대전 "]), ("울산광역시", ["울산시 ", "울산 "]), ("세종특별자치시", ["세종시 ", "세종 "]),
                  ("경기도", ["경기 "]), ("강원특별자치도", ["강원도 ", "강원 "]), ("충청북도", ["충북 "]), ("충청남도", ["충남 "]), ("전북특별자치도", ["전라북도 ", "전북 "]),
                  ("전라남도", ["전남 "]), ("경상북도", ["경북 "]), ("경상남도", ["경남 "]), ("제주특별자치도", ["제주도 ", "제주 "])]
def normalize(addr):
    for full, shorts in SIDO_NORMALIZE:
        for sh in shorts:
            if addr.startswith(sh): return full + " " + addr[len(sh):]
    return addr

def parse(addr):
    addr = normalize((addr or "").strip())
    if addr.startswith("세종특별자치시"):
        m2 = re.match(r"세종특별자치시\s+(\S+?(?:동|읍|면))", addr)
        return "세종특별자치시", "세종특별자치시", "", (m2.group(1) if m2 else "")
    m = ADDR.match(addr)
    if not m: return None
    sido, a, b, dong = m.groups()
    if not a.endswith("시"):          # 구는 '시' 아래에만 있음
        b = ""
        m3 = re.match(re.escape(sido) + r"\s+" + re.escape(a) + r"\s+(\S+?(?:동|읍|면|가|리))", addr)
        dong = m3.group(1) if m3 else dong
    return sido, a, b or "", dong or ""

def rows_from_csv(path):
    raw = pathlib.Path(path).read_bytes()
    for enc in ("utf-8-sig", "cp949"):
        try: txt = raw.decode(enc); break
        except UnicodeDecodeError: pass
    out = []
    for r in csv.DictReader(txt.splitlines()):
        if r["학교급구분"] not in ("중학교", "고등학교") or r["운영상태"] != "운영": continue
        out.append({"name": r["학교명"], "level": r["학교급구분"], "type": r["설립형태"], "branch": r["본교분교구분"] == "분교",
                    "addr": r["소재지지번주소"], "addr2": r["소재지도로명주소"], "office": r["교육지원청명"], "code": "", "office_code": "",
                    "coedu": "", "hs_type": "", "homepage": ""})
    src = {"name": "전국초중등학교위치표준데이터(한국교육시설안전원, 공공데이터포털)", "date": next(csv.DictReader(txt.splitlines()))["데이터기준일자"]}
    return out, src

def rows_from_neis():
    key = (ROOT / ".neis_key").read_text(encoding="utf-8").strip()
    out = []
    for code, sido in OFFICES.items():
        for kind in ("중학교", "고등학교"):
            p = 1
            while True:
                q = urllib.parse.urlencode({"KEY": key, "Type": "json", "pIndex": p, "pSize": 1000, "ATPT_OFCDC_SC_CODE": code, "SCHUL_KND_SC_NM": kind})
                d = json.load(urllib.request.urlopen("https://open.neis.go.kr/hub/schoolInfo?" + q, timeout=60))
                if "schoolInfo" not in d: break
                rows = d["schoolInfo"][1]["row"]
                for r in rows:
                    out.append({"name": r["SCHUL_NM"], "level": kind, "type": r["FOND_SC_NM"] or "", "branch": False,
                                "addr": r["ORG_RDNMA"] or "", "addr2": r["ORG_RDNMA"] or "", "office": r["JU_ORG_NM"] or "", "code": r["SD_SCHUL_CODE"], "office_code": code,
                                "coedu": r["COEDU_SC_NM"] or "", "hs_type": (r["HS_SC_NM"] or "").strip(), "homepage": (r["HMPG_ADRES"] or "").strip()})
                if len(rows) < 1000: break
                p += 1
            time.sleep(0.2)
        print(f"  {sido}: 누적 {len(out)}")
    return out, {"name": "나이스 교육정보 개방포털 학교기본정보", "date": datetime.date.today().isoformat()}

rows, src = rows_from_neis() if sys.argv[1] == "--neis" else rows_from_csv(sys.argv[1])
if sys.argv[1] == "--neis" and len(sys.argv) > 2 and pathlib.Path(sys.argv[2]).exists():   # --neis <csv>: 지번 동 보조
    csv_rows, _ = rows_from_csv(sys.argv[2])
    dong_by = {}
    for c in csv_rows:
        pc = parse(c["addr"])
        if pc and pc[3]: dong_by[(c["name"], pc[0])] = pc[3]
    for r in rows:
        pr = parse(r["addr"])
        if pr and not pr[3]:
            d = dong_by.get((r["name"], pr[0]))
            if d: r["dong_hint"] = d
    print(f"  지번 동 보조: {sum(1 for r in rows if r.get('dong_hint'))}곳")
parsed = []
for r in rows:
    p = parse(r["addr"]) or parse(r["addr2"])
    parsed.append((r, p))
mixed = collections.defaultdict(lambda: [0, 0])          # (시도, 시) → [구 있음, 구 없음]
for r, p in parsed:
    if p and p[1].endswith("시"): mixed[(p[0], p[1])][0 if p[2] else 1] += 1
COLLAPSE = {k for k, (g, ng) in mixed.items() if g and ng and ng / (g + ng) >= 0.2}
if COLLAPSE: print("  구 혼용 → 시 단위로 합침:", sorted(k[1] for k in COLLAPSE))
regions = collections.OrderedDict(); skipped = 0
for r, p in parsed:
    if not p: skipped += 1; print("  파싱 실패:", r["name"], r["addr"]) if skipped <= 5 else None; continue
    sido, a, b, dong = p
    if (sido, a) in COLLAPSE: b = ""
    dong = dong or r.get("dong_hint", "")
    sgg = (a + " " + b).strip() if b else a
    reg = regions.setdefault((sido, sgg), {"sido": sido, "sido_short": SIDO_SHORT.get(sido, sido), "sgg": sgg, "city": a, "gu": b,
                                           "slug": f'{SIDO_SHORT.get(sido, sido)}-{sgg.replace(" ", "-")}' if sido != "세종특별자치시" else "세종-세종시",
                                           "offices": collections.Counter(), "schools": [], "dongs": collections.Counter()})
    reg["offices"][r["office"]] += 1
    if dong and not re.fullmatch(r"\d+.*", dong): reg["dongs"][dong] += 1
    reg["schools"].append({"name": r["name"], "level": r["level"], "type": r["type"], "branch": r["branch"], "dong": dong,
                           "code": r["code"], "office_code": r["office_code"], "coedu": r["coedu"], "hs_type": r["hs_type"], "homepage": r["homepage"]})
out = []
for (sido, sgg), reg in sorted(regions.items(), key=lambda kv: (list(SIDO_SHORT).index(kv[0][0]) if kv[0][0] in SIDO_SHORT else 99, kv[0][1])):
    reg["schools"].sort(key=lambda s: (s["level"] != "중학교", s["name"]))
    reg["offices"] = [o for o, _ in reg["offices"].most_common()]
    reg["dongs"] = [d for d, _ in reg["dongs"].most_common(12)]
    reg["mid"] = sum(1 for s in reg["schools"] if s["level"] == "중학교")
    reg["high"] = sum(1 for s in reg["schools"] if s["level"] == "고등학교")
    out.append(reg)
data = {"source": {**src, "note": "중·고등학교만. 학교명·소재지는 공공 데이터 기준이며 과외나루와 학교는 관계가 없습니다."}, "regions": out}
dst = ROOT / "data" / "schools.json"
dst.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
slugs = [r["slug"] for r in out]; assert len(slugs) == len(set(slugs)), "slug 중복"
print(f"지역 {len(out)}개, 학교 {sum(len(r['schools']) for r in out)}곳(중 {sum(r['mid'] for r in out)}, 고 {sum(r['high'] for r in out)}), 파싱 실패 {skipped}, 출처 {src['name']} {src['date']} → {dst} ({dst.stat().st_size//1024}KB)")
