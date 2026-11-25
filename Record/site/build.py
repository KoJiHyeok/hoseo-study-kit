#!/usr/bin/env python3
"""Record/summaries/*.md -> site/study-notes.html (Artifact 배포용 단일 HTML).

사용법: python3 build.py
- summaries 파일명 규칙: YYYY-MM-DD_<과목slug>_<주제>.md
- 주차 = (날짜 - config.json 의 semester_start) // 7 + 1
- 시험지: <과목>/시험지/NN주차.md · 할 일: <과목>/할일/NN주차.md (둘 다 자동 수집)
"""
import json, re, sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).parent
SUMMARIES = HERE.parent / "summaries"
TEMPLATE = HERE / "template.html"
OUT = HERE / "study-notes.html"

sys.path.insert(0, str(HERE.parent.parent))          # repo 루트의 kit.py
from kit import COURSES, SEMESTER, SEMESTER_START, SCHOOL  # noqa: E402  과목·학기는 config.json 이 정본

FNAME = re.compile(r"^(\d{4}-\d{2}-\d{2})_([^_]+)_(.+)\.md$")


def parse(path: Path):
    m = FNAME.match(path.name)
    if not m:
        print(f"  ! 파일명 규칙 불일치, 건너뜀: {path.name}", file=sys.stderr)
        return None
    d, slug, topic = m.group(1), m.group(2), m.group(3)
    if slug not in COURSES:
        print(f"  ! 미등록 slug '{slug}', 건너뜀: {path.name}", file=sys.stderr)
        return None
    text = path.read_text(encoding="utf-8")
    body = re.sub(r"^---\n.*?\n---\n", "", text, count=1, flags=re.S)
    # 본문 첫 H1을 제목으로 (없으면 파일명 topic)
    h1 = re.search(r"^# (.+)$", body, flags=re.M)
    title = h1.group(1).strip() if h1 else topic.replace("-", " ")
    title = re.sub(r"\s*—\s*\d{4}-\d{2}-\d{2}\s*$", "", title)  # 제목 끝 날짜 중복 제거
    one = re.search(r"^> \*\*한 줄 요약\*\*:\s*(.+)$", body, flags=re.M)
    y, mo, dy = map(int, d.split("-"))
    week = (date(y, mo, dy) - SEMESTER_START).days // 7 + 1
    return {
        "id": path.stem, "date": d, "slug": slug, "week": week,
        "title": title, "oneLiner": (one.group(1).strip() if one else ""),
        "md": body.strip(),
    }


QHEAD = re.compile(r"^##\s*Q(\d+)\s*·\s*([^·\n]+?)\s*·\s*([^\n]+?)\s*$", re.M)
CHOICE = re.compile(r"^- ([①②③④⑤⑥⑦⑧])\s*(.+)$\n?", re.M)
KEYS = re.compile(r"^([①-⑧](?:\s*[·,]\s*[①-⑧])*)\s*(?:\n|$)")


def parse_exam(path, slug):
    """<과목>/시험지/<NN>주차.md -> {week, questions:[{n,type,points,prompt,answer,source}]}"""
    text = path.read_text(encoding="utf-8")
    fm = re.match(r"^---\n(.*?)\n---\n", text, flags=re.S)
    meta, body = (fm.group(1) if fm else ""), (text[fm.end():] if fm else text)
    week = re.search(r"^week:\s*(\d+)", meta, flags=re.M)
    week = int(week.group(1)) if week else int(re.sub(r"\D", "", path.stem) or 0)

    heads = list(QHEAD.finditer(body))
    qs = []
    for i, h in enumerate(heads):
        chunk = body[h.end(): heads[i + 1].start() if i + 1 < len(heads) else len(body)].strip()
        # 정답 / 출처 분리
        m_ans = re.search(r"^\*\*정답\*\*\s*$", chunk, flags=re.M)
        prompt = chunk[:m_ans.start()].strip() if m_ans else chunk
        rest = chunk[m_ans.end():].strip() if m_ans else ""
        m_src = re.search(r"^\*\*출처\*\*\s*(.+)$", rest, flags=re.M)
        answer = (rest[:m_src.start()].strip() if m_src else rest)
        source = (m_src.group(1).strip() if m_src else "")
        if not prompt:
            continue
        q = {"n": int(h.group(1)), "type": h.group(2).strip(),
             "points": h.group(3).strip(), "prompt": prompt,
             "answer": answer, "source": source}
        # 객관식: 정답 첫 줄이 번호 하나(①~④)이고 보기가 `- ① …` 줄이면 풀이 가능 문항
        # 복수선택: 정답 첫 줄이 `④ · ⑤` 처럼 번호만 나열 -> key = "④⑤" (정렬된 문자열)
        key = KEYS.match(answer)
        opts = CHOICE.findall(prompt)
        ks = sorted(re.findall(r"[①-⑧]", key.group(1))) if key else []
        if ks and len(opts) >= 2 and all(k in [o for o, _ in opts] for k in ks):
            q["stem"] = CHOICE.sub("", prompt).strip()
            q["choices"] = [{"k": k, "text": t.strip()} for k, t in opts]
            q["key"] = "".join(ks)
            q["multi"] = len(ks) > 1 or bool(re.search(r"모두\s*고르", prompt))
            q["explain"] = answer[key.end():].strip()
        qs.append(q)
    if not qs:
        print(f"  ! 문항 0개, 건너뜀: {path}", file=sys.stderr)
        return None
    title = re.search(r"^title:\s*(.+)$", meta, flags=re.M)
    return {"id": f"{slug}-{path.stem}" if title else f"{slug}-{week:02d}", "slug": slug, "week": week,
            "title": title.group(1).strip() if title else "",
            "count": len(qs), "questions": qs}


def collect_exams(root):
    out = []
    for slug, c in COURSES.items():
        d = root / c["dir"] / "시험지"
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.md")):
            e = parse_exam(f, slug)
            if e:
                out.append(e)
    return sorted(out, key=lambda e: (e["week"], list(COURSES).index(e["slug"])))


TODO_ITEM = re.compile(r"^- \[( |x|X)\]\s*(.+?)\s*$")
TODO_SUB = re.compile(r"^\s{2,}- (.+?)\s*$")
DUE = re.compile(r"(?:마감\s*|(?<!\d)(?<!\d\s)~\s*)(?:(\d{4})-)?(\d{2})-(\d{2})(?:\s*\(.\))?(?:\s*(\d{1,2}:\d{2}))?")


def parse_due(text):
    """'마감 09-13 23:59' / '~09-13' -> 'YYYY-MM-DD HH:MM' (연도 생략 시 학기 연도)"""
    m = DUE.search(text)
    if not m:
        return ""
    y = int(m.group(1)) if m.group(1) else SEMESTER_START.year
    mo, d = int(m.group(2)), int(m.group(3))
    if not m.group(1) and mo < SEMESTER_START.month:   # 1~2월은 다음 해
        y += 1
    try:
        date(y, mo, d)
    except ValueError:
        return ""
    return f"{y:04d}-{mo:02d}-{d:02d}" + (f" {int(m.group(4).split(':')[0]):02d}:{m.group(4).split(':')[1]}" if m.group(4) else "")


def parse_todo(path, slug):
    """<과목>/할일/<NN>주차.md -> {week, items:[{text, done, due, notes:[...]}]}"""
    text = path.read_text(encoding="utf-8")
    fm = re.match(r"^---\n(.*?)\n---\n", text, flags=re.S)
    meta, body = (fm.group(1) if fm else ""), (text[fm.end():] if fm else text)
    week = re.search(r"^week:\s*(\d+)", meta, flags=re.M)
    week = int(week.group(1)) if week else int(re.sub(r"\D", "", path.stem) or 0)

    items = []
    for line in body.splitlines():
        m = TODO_ITEM.match(line)
        if m:
            items.append({"text": m.group(2), "done": m.group(1).lower() == "x",
                          "due": parse_due(m.group(2)), "notes": []})
            continue
        m = TODO_SUB.match(line)
        if m and items:
            items[-1]["notes"].append(m.group(1))
    if not items:
        print(f"  ! 항목 0개, 건너뜀: {path}", file=sys.stderr)
        return None
    return {"id": f"{slug}-{week:02d}", "slug": slug, "week": week, "items": items}


def collect_todos(root):
    out = []
    for slug, c in COURSES.items():
        d = root / c["dir"] / "할일"
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.md")):
            t = parse_todo(f, slug)
            if t:
                out.append(t)
    return sorted(out, key=lambda t: (t["week"], list(COURSES).index(t["slug"])))


def main():
    notes = sorted(
        filter(None, (parse(p) for p in sorted(SUMMARIES.glob("*.md")))),
        key=lambda n: (n["date"], n["id"]),
    )
    exams = collect_exams(HERE.parent.parent)
    todos = collect_todos(HERE.parent.parent)
    data = {
        "built": date.today().isoformat(),
        "semesterStart": SEMESTER_START.isoformat(),
        "courses": COURSES,
        "order": list(COURSES.keys()),
        "notes": notes,
        "exams": exams,
        "todos": todos,
    }
    label = " · ".join(x for x in (SCHOOL, SEMESTER) if x)
    html = (TEMPLATE.read_text(encoding="utf-8")
            .replace("__LABEL__", label).replace("__SEMESTER__", SEMESTER)
            .replace("/*__DATA__*/", "window.DATA = " + json.dumps(data, ensure_ascii=False)))
    OUT.write_text(html, encoding="utf-8")
    n_items = sum(len(t["items"]) for t in todos)
    n_open = sum(1 for t in todos for i in t["items"] if not i["done"])
    print(f"OK: {len(notes)}개 노트 · 시험지 {len(exams)}회분({sum(e['count'] for e in exams)}문항) · 할 일 {n_items}건(미완료 {n_open}) -> {OUT}")


if __name__ == "__main__":
    main()
