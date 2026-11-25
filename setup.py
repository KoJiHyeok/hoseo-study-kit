#!/usr/bin/env python3
"""config.json -> 과목 폴더 · 과목 CLAUDE.md · MOC · 전담 에이전트를 만든다. 여러 번 돌려도 안전하다(있는 파일은 건드리지 않음).

사용:
  python setup.py            # 만들기 (과목을 추가했을 때도 다시 실행)
  python setup.py --force    # 에이전트 정의만 템플릿으로 다시 쓰기 (과목 CLAUDE.md·MOC·필기는 절대 덮지 않음)
  python setup.py --check    # 환경 점검만 (git · gh · aside · claude · pywebview · PyMuPDF)
"""
import re, shutil, subprocess, sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TPL = ROOT / "templates"
SUBDIRS = ["materials", "필기", "할일", "시험지", "개념"]


def check():
    def has(cmd):
        return shutil.which(cmd) is not None

    def mod(name):
        try:
            __import__(name)
            return True
        except ImportError:
            return False

    rows = [
        ("python 3.9+", sys.version_info >= (3, 9), "python.org 에서 설치"),
        ("git", has("git"), "git-scm.com"),
        ("gh (GitHub CLI)", has("gh"), "cli.github.com → `gh auth login`"),
        ("claude (Claude Code)", has("claude"), "필수 — 요약·에이전트가 여기서 돈다"),
        ("aside", has("aside"), "LMS 자동 수집용. 없으면 자료를 직접 내려받아 materials/ 에 넣는다"),
        ("PyMuPDF", mod("pymupdf") or mod("fitz"), "`pip install pymupdf` — 한글 PDF 읽기"),
    ]
    if sys.platform == "win32":
        rows.append(("pywebview", mod("webview"), "`pip install pywebview` — 할일 앱 독립 창 (없으면 브라우저 앱 모드)"))
    if sys.platform == "darwin":
        rows.append(("swiftc", has("swiftc"), "`xcode-select --install` — 할일.app 빌드"))
    ok = True
    for name, good, hint in rows:
        print(f"  {'OK ' if good else '-- '} {name:22} {'' if good else hint}")
        ok &= good or name in ("aside", "pywebview", "swiftc", "gh (GitHub CLI)")
    return ok


def render(text, c, slug):
    exam = ("**매주 필수** — 요약을 손볼 때마다 그 주차 시험지도 같이 갱신한다 (이 과목은 시험이 과제·퀴즈에서 거의 그대로 나온다)"
            if c["exam_weekly"] else "사용자가 요청할 때만 만든다")
    vals = {**c, "slug": slug, "today": date.today().isoformat(), "exam_note": exam,
            "lms_id": c["lms_id"] if c.get("lms_id") else "(미설정)"}
    return re.sub(r"\{\{(\w+)\}\}", lambda m: str(vals.get(m.group(1), "")), text)


def write_new(path, text, force=False):
    if path.exists() and not force:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def main():
    if "--check" in sys.argv:
        sys.exit(0 if check() else 1)
    sys.path.insert(0, str(ROOT))
    from kit import COURSES  # config.json 이 없으면 여기서 안내 후 종료

    errors = []
    for slug, c in COURSES.items():
        if "_" in slug or " " in slug:
            errors.append(f"slug '{slug}' 에 '_' 나 공백을 쓸 수 없다 (요약 파일명 YYYY-MM-DD_<slug>_<주제>.md 를 깨뜨린다)")
        if not re.fullmatch(r"[a-z0-9-]+", c["agent"]):
            errors.append(f"agent '{c['agent']}' 는 영문 소문자·숫자·- 만 (예: ds, os, eng)")
    if len({c["agent"] for c in COURSES.values()}) != len(COURSES):
        errors.append("agent 값이 겹친다")
    if errors:
        sys.exit("config.json 오류:\n  " + "\n  ".join(errors))

    force = "--force" in sys.argv
    made = []
    for d in ["Record/summaries", "Record/transcripts", "auto"]:
        (ROOT / d).mkdir(parents=True, exist_ok=True)
        keep = ROOT / d / ".gitkeep"
        if not any((ROOT / d).iterdir()):
            keep.touch()
    if write_new(ROOT / "메모.md", ""):
        made.append("메모.md")

    for slug, c in COURSES.items():
        base = ROOT / c["dir"]
        for sub in SUBDIRS:
            (base / sub).mkdir(parents=True, exist_ok=True)
            if not any((base / sub).iterdir()):
                (base / sub / ".gitkeep").touch()
        pairs = [
            (base / "CLAUDE.md", "course-CLAUDE.md", False),
            (base / f"{c['dir']}.md", "course-MOC.md", False),
            (ROOT / ".claude" / "agents" / f"course-{c['agent']}.md", "course-agent.md", force),
        ]
        for path, tpl, f in pairs:
            if write_new(path, render((TPL / tpl).read_text(encoding="utf-8"), c, slug), f):
                made.append(path.relative_to(ROOT).as_posix())

    print(f"과목 {len(COURSES)}개: " + ", ".join(f"{s}({c['dir']}, course-{c['agent']})" for s, c in COURSES.items()))
    print("새로 만든 파일:" if made else "새로 만든 파일 없음 (이미 다 있음)")
    for m in made:
        print("  +", m)
    print("\n환경 점검:")
    check()


if __name__ == "__main__":
    main()
