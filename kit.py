"""설정 로더 — 모든 스크립트(앱·사이트 빌드·자료 수집·setup)가 config.json 을 여기서 읽는다.

과목·학기·LMS 주소는 코드에 박지 않는다. 바꿀 곳은 config.json 하나다.
"""
import json, sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "config.json"

if not CONFIG.exists():
    sys.exit("config.json 이 없습니다. SETUP.md 대로 config.example.json 을 복사해 채운 뒤 `python setup.py` 를 실행하세요.")

CFG = json.loads(CONFIG.read_text(encoding="utf-8"))

SCHOOL = CFG.get("school", "")
SEMESTER = CFG["semester"]                                   # 예: "2026-2" — 커밋 메시지·사이트 제목
SEMESTER_START = date.fromisoformat(CFG["semester_start"])   # 개강 주 월요일 — 주차 계산 기준
LMS_BASE = CFG.get("lms_base", "https://learn.hoseo.ac.kr").rstrip("/")
SITE_URL = CFG.get("site_url", "")

HUES = [152, 210, 268, 24, 330, 90, 180, 300]

# slug -> {name, prof, when, room, dir, hue, short, lms_id, agent, exam_weekly}
COURSES = {}
for i, c in enumerate(CFG["courses"]):
    COURSES[c["slug"]] = {
        "name": c["name"],
        "prof": c.get("prof", ""),
        "when": c.get("when", ""),
        "room": c.get("room", ""),
        "dir": c.get("dir") or c["name"],
        "hue": c.get("hue", HUES[i % len(HUES)]),
        "short": c.get("short") or c["slug"],
        "lms_id": c.get("lms_id"),
        "agent": c.get("agent") or f"course{i + 1}",
        "exam_weekly": bool(c.get("exam_weekly", False)),
    }
