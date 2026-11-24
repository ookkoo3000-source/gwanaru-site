# -*- coding: utf-8 -*-
"""나이스 학사일정에서 지역별 학교의 겨울방학 관련 일정(방학식·겨울방학·종업식·졸업식·개학·봄방학)을 모아 data/vacation_schedule.json 에 저장.
    python -I tools_vacation_schedule.py 20261201 20270301 서울-강남구 경기-성남시-분당구 ...   [--level 중학교|고등학교|all]
- data/schools.json(--neis로 만든 것, 학교 코드 포함)을 읽는다.
- 이벤트명에 '방학', '개학', '종업', '졸업'이 들어간 날만 남기고(행사 준비·캠프 등은 제외), 연속된 날짜는 기간으로 묶는다.
- 학교가 나이스에 일정을 올리지 않았으면 그 학교는 '미등록'으로 표시(추측하지 않음)."""
import sys, json, pathlib, urllib.request, urllib.parse, time, datetime, re
sys.stdout.reconfigure(encoding="utf-8")
ROOT = pathlib.Path(__file__).parent
KEY = (ROOT / ".neis_key").read_text(encoding="utf-8").strip()
args = [a for a in sys.argv[1:] if not a.startswith("--")]
level = "중학교"
if "--level" in sys.argv: level = sys.argv[sys.argv.index("--level") + 1]
frm, to, slugs = args[0], args[1], args[2:]
S = json.loads((ROOT / "data" / "schools.json").read_text(encoding="utf-8"))
regs = {r["slug"]: r for r in S["regions"]}
dst = ROOT / "data" / "vacation_schedule.json"
out = json.loads(dst.read_text(encoding="utf-8")) if dst.exists() else {"fetched": {}, "regions": {}}
KEEP = re.compile(r"방학|개학|종업|졸업")
DROP = re.compile(r"예행|연습|평가회|준비|사진|앨범|설명회|여행|캠프|프로그램|교실|특강|돌봄|과제|선정|심사|대상자|안내|통신|계획|협의|회의|워크숍|연수|도서관|개방|급식|자치|상담|독서|캠페인|봉사|수업|학습|영어|수학|체험|대회|운영|기간 중|방학 중|방학중|투표|선거|배부|제출|공고|모집|신청|사정회|사정|영상|토의|제작|진급|리허설|점검|환경|청소|소독|공사|방과후|방과 후|교실|강좌|안전|교육|^졸업$|^종업$")
GAP_DAYS = 6   # 설 연휴 등으로 '겨울방학' 등록이 며칠 끊겨도 하나의 기간으로 묶음

def fetch(school):
    q = urllib.parse.urlencode({"KEY": KEY, "Type": "json", "pIndex": 1, "pSize": 300, "ATPT_OFCDC_SC_CODE": school["office_code"], "SD_SCHUL_CODE": school["code"], "AA_FROM_YMD": frm, "AA_TO_YMD": to})
    d = json.load(urllib.request.urlopen("https://open.neis.go.kr/hub/SchoolSchedule?" + q, timeout=60))
    if "SchoolSchedule" not in d: return None   # 미등록
    ev = [(e["AA_YMD"], (e["EVENT_NM"] or "").strip()) for e in d["SchoolSchedule"][1]["row"]]
    ev = [(y, n) for y, n in ev if KEEP.search(n) and not DROP.search(n)]
    # 같은 이벤트명의 연속 날짜 묶기 (주말을 건너뛴 연속도 하나로)
    by_name = {}
    for y, n in sorted(ev):
        d0 = datetime.date(int(y[:4]), int(y[4:6]), int(y[6:]))
        g = by_name.setdefault(n, [])
        if g and (d0 - g[-1]["end"]).days <= GAP_DAYS: g[-1]["end"] = d0
        else: g.append({"name": n, "start": d0, "end": d0})
    groups = sorted((x for g in by_name.values() for x in g), key=lambda x: (x["start"], x["name"]))
    return [{"name": g["name"], "start": g["start"].isoformat(), "end": g["end"].isoformat()} for g in groups]

for slug in slugs:
    if slug not in regs: print("  [건너뜀] 없는 지역 slug:", slug); continue
    r = regs[slug]
    schools = [s for s in r["schools"] if (level == "all" or s["level"] == level) and s["code"]]
    res = []
    for s in schools:
        ev = None
        for attempt in range(3):   # 연결 끊김 등 일시 오류는 재시도 (오류를 '미등록'으로 기록하지 않기 위해)
            try: ev = fetch(s); break
            except Exception as e:
                print(f"  오류({attempt + 1}/3)", s["name"], e); time.sleep(2 * (attempt + 1))
        else: print("  [확인 필요] 3회 실패 → 미등록으로 기록됨:", s["name"])
        res.append({"name": s["name"], "level": s["level"], "type": s["type"], "coedu": s["coedu"], "hs_type": s["hs_type"], "dong": s["dong"], "events": ev})
        time.sleep(0.15)
    out["regions"][slug] = {"slug": slug, "sido": r["sido"], "sgg": r["sgg"], "level": level, "range": [frm, to], "schools": res}
    out["fetched"][slug] = datetime.date.today().isoformat()
    n_reg = sum(1 for x in res if x["events"]); n_vac = sum(1 for x in res if x["events"] and any("방학" in e["name"] for e in x["events"]))
    print(f"{slug}: {level} {len(res)}곳 중 방학 관련 일정 등록 {n_reg}곳, 겨울방학 일정 있음 {n_vac}곳")
    dst.write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")   # 지역마다 저장
dst.write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")
print("→", dst)
