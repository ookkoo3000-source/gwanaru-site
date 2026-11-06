# -*- coding: utf-8 -*-
"""나이스 학사일정에서 지역별 학교의 시험(고사·지필평가) 일정을 모아 data/exam_schedule.json 에 저장.
    python -I tools_exam_schedule.py 20261101 20261231 서울-강남구 경기-성남시-분당구 ...   [--level 중학교|고등학교|all]
- data/schools.json(--neis로 만든 것, 학교 코드 포함)을 읽는다.
- 이벤트명에 '고사', '지필', '평가'가 들어간 날만 남기고, 연속된 날짜는 기간으로 묶는다.
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
dst = ROOT / "data" / "exam_schedule.json"
out = json.loads(dst.read_text(encoding="utf-8")) if dst.exists() else {"fetched": {}, "regions": {}}
KEEP = re.compile(r"고사|지필|평가")
DROP = re.compile(r"수행|동아리|평가회|평가원|자기평가|학교평가|교원평가|만족도|진단평가|성취도평가|기초학력|수능|수학능력|원안|통지표|성적|자습|교육활동|연수|발송|채점|이의|검토|모의|영어듣기|듣기평가|학력평가|고사장|감독|봉사|자율|시간표|학력신장|교육과정평가|자체평가|형성평가")

def fetch(school):
    q = urllib.parse.urlencode({"KEY": KEY, "Type": "json", "pIndex": 1, "pSize": 300, "ATPT_OFCDC_SC_CODE": school["office_code"], "SD_SCHUL_CODE": school["code"], "AA_FROM_YMD": frm, "AA_TO_YMD": to})
    d = json.load(urllib.request.urlopen("https://open.neis.go.kr/hub/SchoolSchedule?" + q, timeout=60))
    if "SchoolSchedule" not in d: return None   # 미등록
    ev = [(e["AA_YMD"], (e["EVENT_NM"] or "").strip()) for e in d["SchoolSchedule"][1]["row"]]
    ev = [(y, n) for y, n in ev if KEEP.search(n) and not DROP.search(n)]
    # 같은 이벤트명의 연속 날짜 묶기
    by_name = {}
    for y, n in sorted(ev):
        d0 = datetime.date(int(y[:4]), int(y[4:6]), int(y[6:]))
        g = by_name.setdefault(n, [])
        if g and (d0 - g[-1]["end"]).days <= 3: g[-1]["end"] = d0
        else: g.append({"name": n, "start": d0, "end": d0})
    groups = sorted((x for g in by_name.values() for x in g), key=lambda x: (x["start"], x["name"]))
    return [{"name": g["name"], "start": g["start"].isoformat(), "end": g["end"].isoformat()} for g in groups]

for slug in slugs:
    if slug not in regs: print("  [건너뜀] 없는 지역 slug:", slug); continue
    r = regs[slug]
    schools = [s for s in r["schools"] if (level == "all" or s["level"] == level) and s["code"]]
    res = []
    for s in schools:
        try: ev = fetch(s)
        except Exception as e: ev = None; print("  오류", s["name"], e)
        res.append({"name": s["name"], "level": s["level"], "type": s["type"], "coedu": s["coedu"], "hs_type": s["hs_type"], "dong": s["dong"], "events": ev})
        time.sleep(0.15)
    out["regions"][slug] = {"slug": slug, "sido": r["sido"], "sgg": r["sgg"], "level": level, "range": [frm, to], "schools": res}
    out["fetched"][slug] = datetime.date.today().isoformat()
    n_reg = sum(1 for x in res if x["events"]); n_exam = sum(1 for x in res if x["events"] and any("기말" in e["name"] or "고사" in e["name"] for e in x["events"]))
    print(f"{slug}: {level} {len(res)}곳 중 일정 등록 {n_reg}곳, 시험 일정 있음 {n_exam}곳")
    dst.write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")   # 지역마다 저장
dst.write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")
print("→", dst)
