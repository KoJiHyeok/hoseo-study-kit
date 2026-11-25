#!/usr/bin/env python3
"""할 일 대시보드 — <과목>/할일/*.md 를 읽어 '달력 + 이번 주 할 일·마감 + 자유 메모' 를 앱 창으로 보여준다.

맥 · Windows 공용 (표준 라이브러리만). 동기화 = git:
- 화면 열 때 / 2분마다: git pull
- 체크하면: 그 md 줄의 [ ] <-> [x] 를 고치고 그 파일만 commit + push
- 메모: <repo>/메모.md 에 자동 저장, 마지막 입력 20초 뒤 commit + push (창 닫을 때도)

창:
- 맥: ~/Applications/할일.app (dash/mac/ 의 Swift WKWebView 껍데기)가 `app.py --no-open` 을 띄우고 붙는다
- Windows: `pip install pywebview` 돼 있으면 독립 창(Edge WebView2), 없으면 브라우저 앱 모드로 대체
"""
import json, re, subprocess, sys, threading, time, webbrowser
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent.parent          # repo 루트
sys.path.insert(0, str(ROOT / "Record" / "site"))
from build import COURSES, SEMESTER, SEMESTER_START, SUMMARIES, TODO_ITEM, parse, parse_due  # noqa: E402  파서 규칙은 사이트와 하나로

PORT = 8765
URL = f"http://127.0.0.1:{PORT}/"
PULL_EVERY = 120
HTML = (Path(__file__).parent / "index.html")
MEMO = ROOT / "메모.md"
MEMO_PUSH_DELAY = 20

git_lock = threading.Lock()
state = {"last_pull": 0.0, "sync": "아직 동기화 전", "ok": True}
memo_timer = None


# Windows: pythonw(콘솔 없음)에서 git.exe 를 띄우면 매번 cmd 창이 깜빡인다 → 창 없이 실행
NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


def git(*args):
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=60,
                       creationflags=NO_WINDOW)
    return r.returncode, (r.stdout + r.stderr).strip()


def set_sync(ok, msg):
    state.update(ok=ok, sync=f"{datetime.now():%H:%M} {msg}")


def pull(force=False):
    if not force and time.time() - state["last_pull"] < PULL_EVERY:
        return
    with git_lock:
        state["last_pull"] = time.time()
        code, out = safe_pull()
        set_sync(code == 0, "받아옴" if code == 0 else "pull 실패: " + last_line(out))


def last_line(out):
    return (out.splitlines() or ["?"])[-1][:80]


def safe_pull():
    """충돌로 rebase 가 멈추면 즉시 되돌린다 — repo 를 rebase 중 상태로 남기지 않는다."""
    code, out = git("pull", "--rebase", "--autostash", "-q")
    if code != 0:
        git("rebase", "--abort")
    return code, out


def push_file(rel, label):
    with git_lock:
        git("add", "--", rel)
        if git("status", "--porcelain", "--", rel)[1]:
            code, out = git("commit", "-q", "-m", f"todo({SEMESTER}): {label}", "--", rel)
            if code != 0:
                return set_sync(False, "commit 실패: " + out[-80:])
        for _ in range(2):
            safe_pull()
            code, out = git("push", "-q")
            if code == 0:
                state["last_pull"] = time.time()
                return set_sync(True, "올림")
        set_sync(False, "push 실패 (로컬엔 저장됨): " + last_line(out))


def save_memo(text):
    global memo_timer
    MEMO.write_text(text, encoding="utf-8")
    if memo_timer:
        memo_timer.cancel()
    memo_timer = threading.Timer(MEMO_PUSH_DELAY, flush_memo)
    memo_timer.daemon = True
    memo_timer.start()


def flush_memo():
    global memo_timer
    if memo_timer:
        memo_timer.cancel()
        memo_timer = None
        push_file(MEMO.name, "메모")


def week_of(d):
    return (d - SEMESTER_START).days // 7 + 1


def collect():
    items = []
    for slug, c in COURSES.items():
        d = ROOT / c["dir"] / "할일"
        for f in sorted(d.glob("*.md")) if d.is_dir() else []:
            text = f.read_text(encoding="utf-8")
            wk = re.search(r"^week:\s*(\d+)", text, flags=re.M)
            wk = int(wk.group(1)) if wk else int(re.sub(r"\D", "", f.stem) or 0)
            for n, line in enumerate(text.splitlines()):
                m = TODO_ITEM.match(line)
                if m:
                    t = m.group(2)
                    items.append({"slug": slug, "hue": c["hue"], "week": wk,
                                  "file": f.relative_to(ROOT).as_posix(), "line": n,
                                  "text": t, "done": m.group(1).lower() == "x", "due": parse_due(t)})
    today = date.today()
    return {"today": today.isoformat(), "week": week_of(today), "items": items,
            "semesterStart": SEMESTER_START.isoformat(), "short": {k: c["short"] for k, c in COURSES.items()},
            "memo": MEMO.read_text(encoding="utf-8") if MEMO.exists() else "",
            "sync": state["sync"], "ok": state["ok"]}


def collect_study():
    """중간고사 모음: <과목>/중간고사/*.md + <과목>/시험지/00-*.md (통합 시험지)"""
    out = []
    for slug, c in COURSES.items():
        base = ROOT / c["dir"]
        files = sorted((base / "중간고사").glob("*.md")) + sorted((base / "시험지").glob("00-*.md"))
        docs = []
        for f in files:
            text = f.read_text(encoding="utf-8")
            fm = re.match(r"^---\n(.*?)\n---\n", text, flags=re.S)
            meta = fm.group(1) if fm else ""
            title = re.search(r"^title:\s*(.+)$", meta, flags=re.M)
            order = re.search(r"^order:\s*(\d+)", meta, flags=re.M)
            docs.append({"path": f.relative_to(ROOT).as_posix(),
                         "title": title.group(1).strip() if title else f.stem,
                         "order": int(order.group(1)) if order else (1 if "시험지" in f.parts else 9),
                         "q": len(re.findall(r"^## Q\d+", text, flags=re.M)),
                         "updated": datetime.fromtimestamp(f.stat().st_mtime).strftime("%m-%d")})
        out.append({"slug": slug, "hue": c["hue"], "name": c["name"],
                    "docs": sorted(docs, key=lambda d: (d["order"], d["title"]))})
    return out


def read_doc(rel):
    path = (ROOT / rel).resolve()
    if ROOT not in path.parents or path.suffix != ".md" or not ({"중간고사", "시험지"} & set(path.parts)):
        raise ValueError("허용되지 않은 경로")
    return path.read_text(encoding="utf-8")


def collect_notes():
    """강의노트 탭: Record/summaries/*.md — 사이트(build.py)와 같은 파서. 목록엔 본문을 빼고 보낸다."""
    notes = [n for n in map(parse, sorted(SUMMARIES.glob("*.md"))) if n]
    return [{"slug": slug, "hue": c["hue"], "name": c["name"], "prof": c["prof"], "when": c["when"],
             "notes": sorted(({k: v for k, v in n.items() if k != "md"} for n in notes if n["slug"] == slug),
                             key=lambda n: (n["date"], n["id"]), reverse=True)}
            for slug, c in COURSES.items()]


def read_note(note_id):
    path = (SUMMARIES / f"{note_id}.md").resolve()
    if path.parent != SUMMARIES.resolve() or not path.exists():
        raise ValueError("노트를 찾지 못함")
    return parse(path)


WIKILINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")


def fm_list(meta, key):
    m = re.search(rf"^{key}:\s*\[(.*?)\]\s*$", meta, flags=re.M)
    return [s.strip().strip("'\"") for s in m.group(1).split(",") if s.strip()] if m else []


def collect_concepts():
    """개념 탭: <과목>/개념/*.md — 파일명 = 개념명. 정의 = 첫 '>' 블록, [[링크]]로 서로 잇는다.
    역링크는 화면에서 links 를 뒤집어 만든다. mentions = 이름·별칭이 본문에 나오는 강의노트(근거 sources 와 별개)."""
    notes = {n["id"]: n for n in map(parse, sorted(SUMMARIES.glob("*.md"))) if n}
    out = []
    for slug, c in COURSES.items():
        d = ROOT / c["dir"] / "개념"
        for f in sorted(d.glob("*.md")) if d.is_dir() else []:
            text = f.read_text(encoding="utf-8")
            fm = re.match(r"^---\n(.*?)\n---\n?", text, flags=re.S)
            meta, body = (fm.group(1), text[fm.end():]) if fm else ("", text)
            body = re.sub(r"^# .+\n", "", body.lstrip())                  # 제목은 파일명으로
            dm = re.match(r"((?:>.*(?:\n|$))+)", body)
            definition = re.sub(r"^> ?", "", dm.group(1), flags=re.M).strip() if dm else ""
            body = body[dm.end():].strip() if dm else body.strip()
            aliases = fm_list(meta, "aliases")
            terms = {t.lower() for t in [f.stem, *aliases] if len(t) >= 2}
            sources = [s for s in fm_list(meta, "sources") if s in notes]
            mentions = [nid for nid, n in notes.items() if n["slug"] == slug and nid not in sources
                        and any(t in n["md"].lower() for t in terms)]
            out.append({"name": f.stem, "slug": slug, "hue": c["hue"], "aliases": aliases,
                        "def": definition, "md": body, "path": f.relative_to(ROOT).as_posix(),
                        "links": list(dict.fromkeys(WIKILINK.findall(definition + "\n" + body))),
                        "sources": sources, "mentions": mentions})
    titles = {nid: {"title": n["title"], "date": n["date"], "week": n["week"], "slug": n["slug"]} for nid, n in notes.items()}
    return {"concepts": out, "notes": titles}


def search_notes(q, limit=12):
    """개념 검색에 안 걸릴 때를 위한 강의노트 전문 검색 — 걸린 줄 앞뒤를 조금 잘라 보낸다."""
    q = q.strip().lower()
    if len(q) < 2:
        return []
    hits = []
    for n in filter(None, map(parse, sorted(SUMMARIES.glob("*.md"), reverse=True))):
        low = n["md"].lower()
        at = low.find(q)
        if at < 0:
            continue
        snip = re.sub(r"[=*`#>|]", "", n["md"][max(0, at - 40): at + len(q) + 60]).replace("\n", " ")
        hits.append({"id": n["id"], "slug": n["slug"], "title": n["title"], "date": n["date"],
                     "count": low.count(q), "snip": snip})
    return sorted(hits, key=lambda h: -h["count"])[:limit]


MAT_TYPES = {".pdf": "application/pdf", ".pptx": "application/octet-stream", ".c": "text/plain; charset=utf-8",
             ".h": "text/plain; charset=utf-8", ".txt": "text/plain; charset=utf-8", ".hwp": None, ".hwpx": None, ".key": None}


def collect_materials():
    """자료 탭: <과목>/materials/* 원본 목록. 같은 이름 pptx 가 있는 .key 는 숨긴다(앱에서 못 여는 중복)."""
    out = []
    for slug, c in COURSES.items():
        d = ROOT / c["dir"] / "materials"
        files = sorted(f for f in d.glob("*") if f.is_file() and f.suffix.lower() in MAT_TYPES) if d.exists() else []
        stems = {f.stem for f in files if f.suffix.lower() == ".pptx"}
        items = []
        for f in files:
            ext = f.suffix.lower()
            if ext == ".key" and f.stem in stems:
                continue
            m = re.match(r"^(\d+)주차_(.+)$", f.stem)
            items.append({"path": f.relative_to(ROOT).as_posix(), "ext": ext[1:],
                          "week": int(m.group(1)) if m else 0, "name": m.group(2) if m else f.stem,
                          "kb": f.stat().st_size // 1024})
        out.append({"slug": slug, "hue": c["hue"], "name": c["name"], "items": items})
    return out


def material_path(rel):
    """읽기 전용 — materials/ 안의 허용 확장자만. 원본은 절대 쓰지 않는다."""
    path = (ROOT / rel).resolve()
    if ROOT not in path.parents or "materials" not in path.parts or path.suffix.lower() not in MAT_TYPES:
        raise ValueError("허용되지 않은 경로")
    return path


def hwp_text(rel):
    path = material_path(rel)
    if path.suffix.lower() == ".hwpx":                # zip + XML: 문단(<hp:p>)마다 글(<hp:t>)을 잇는다
        import zipfile
        with zipfile.ZipFile(path) as z:
            secs = sorted((n for n in z.namelist() if re.match(r"Contents/section\d+\.xml$", n)),
                          key=lambda n: int(re.search(r"\d+", n).group()))
            paras = []
            for n in secs:
                xml = z.read(n).decode("utf-8")
                for p in re.findall(r"<hp:p\b.*?</hp:p>", xml, flags=re.S):
                    t = "".join(re.findall(r"<hp:t\b[^>]*>(.*?)</hp:t>", p, flags=re.S))
                    t = re.sub(r"<[^>]+>", "", t)
                    paras.append(t.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&amp;", "&"))
        return "\n".join(paras)
    sys.path.insert(0, str(ROOT / "tools"))
    from hwp2txt import extract
    return extract(str(path))


def toggle(rel, line_no, text, done):
    path = (ROOT / rel).resolve()
    if ROOT not in path.parents or "할일" not in path.parts:
        raise ValueError("허용되지 않은 경로")
    lines = path.read_text(encoding="utf-8").split("\n")
    m = TODO_ITEM.match(lines[line_no]) if line_no < len(lines) else None
    if not m or m.group(2) != text:          # 그새 pull 로 파일이 바뀌었으면 텍스트로 다시 찾는다
        line_no = next((i for i, l in enumerate(lines)
                        if (mm := TODO_ITEM.match(l)) and mm.group(2) == text), None)
        if line_no is None:
            raise ValueError("항목을 찾지 못함 — 새로고침")
    lines[line_no] = re.sub(r"^- \[[ xX]\]", "- [x]" if done else "- [ ]", lines[line_no], count=1)
    path.write_text("\n".join(lines), encoding="utf-8")
    label = ("✓ " if done else "↺ ") + re.sub(r"\s+—.*", "", text).replace("⭐", "").replace("**", "").strip()[:50]
    threading.Thread(target=push_file, args=(rel, label), daemon=True).start()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/":
            return self.send(200, HTML.read_bytes(), "text/html; charset=utf-8")
        if self.path.startswith("/api/todos"):
            pull(force="force" in self.path)
            return self.send(200, collect())
        if self.path == "/api/study":
            return self.send(200, collect_study())
        if self.path.startswith("/api/doc?"):
            from urllib.parse import parse_qs, urlparse
            try:
                return self.send(200, {"md": read_doc(parse_qs(urlparse(self.path).query)["path"][0])})
            except Exception as e:
                return self.send(400, {"error": str(e)})
        if self.path == "/api/notes":
            return self.send(200, collect_notes())
        if self.path.startswith("/api/note?"):
            from urllib.parse import parse_qs, urlparse
            try:
                return self.send(200, read_note(parse_qs(urlparse(self.path).query)["id"][0]))
            except Exception as e:
                return self.send(400, {"error": str(e)})
        if self.path == "/api/concepts":
            return self.send(200, collect_concepts())
        if self.path.startswith("/api/search?"):
            from urllib.parse import parse_qs, urlparse
            return self.send(200, search_notes(parse_qs(urlparse(self.path).query).get("q", [""])[0]))
        if self.path == "/api/materials":
            return self.send(200, collect_materials())
        if self.path.startswith(("/file?", "/api/hwp?")):
            from urllib.parse import parse_qs, urlparse
            try:
                rel = parse_qs(urlparse(self.path).query)["path"][0]
                if self.path.startswith("/api/hwp?"):
                    return self.send(200, {"text": hwp_text(rel)})
                f = material_path(rel)
                return self.send(200, f.read_bytes(), MAT_TYPES[f.suffix.lower()] or "application/octet-stream")
            except Exception as e:
                return self.send(400, {"error": str(e)})
        if self.path in ("/vendor/marked.min.js", "/vendor/pptx-preview.umd.js"):
            return self.send(200, (Path(__file__).parent / self.path.lstrip("/")).read_bytes(),
                             "text/javascript; charset=utf-8")
        if self.path.startswith("/vendor/pdfjs/"):   # pdf.js 빌드 + cmaps(한글 CID 폰트) + standard_fonts
            base = (Path(__file__).parent / "vendor" / "pdfjs").resolve()
            f = (Path(__file__).parent / self.path.split("?")[0].lstrip("/")).resolve()
            if base in f.parents and f.is_file():
                ctype = "text/javascript; charset=utf-8" if f.suffix == ".js" else "application/octet-stream"
                return self.send(200, f.read_bytes(), ctype)
        if self.path == "/api/ping":
            return self.send(200, {"app": "hoseo-dash"})
        self.send(404, {"error": "not found"})

    def do_POST(self):
        if self.path not in ("/api/toggle", "/api/memo"):
            return self.send(404, {"error": "not found"})
        try:
            b = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            if self.path == "/api/memo":
                save_memo(str(b["text"]))
            else:
                toggle(b["file"], int(b["line"]), b["text"], bool(b["done"]))
            self.send(200, {"ok": True})
        except Exception as e:
            self.send(400, {"error": str(e)})


def open_window():
    """브라우저 '앱 모드'(주소창 없는 창). 없으면 일반 탭."""
    if sys.platform == "darwin":
        for app in ("Google Chrome", "Microsoft Edge", "Brave Browser"):
            if Path(f"/Applications/{app}.app").exists():
                subprocess.Popen(["open", "-na", app, "--args", f"--app={URL}", "--window-size=1180,800"])
                return
    elif sys.platform == "win32":
        import os
        for exe in (r"%ProgramFiles%\Google\Chrome\Application\chrome.exe",
                    r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe",
                    r"%LocalAppData%\Google\Chrome\Application\chrome.exe",
                    r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe",
                    r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"):
            p = os.path.expandvars(exe)
            if os.path.exists(p):
                subprocess.Popen([p, f"--app={URL}", "--window-size=1180,800"])
                return
    webbrowser.open(URL)


def already_running():
    try:
        return json.load(urlopen(URL + "api/ping", timeout=1)).get("app") == "hoseo-dash"
    except Exception:
        return False


def on_term(*_):
    flush_memo()
    sys.exit(0)


if __name__ == "__main__":
    import signal
    signal.signal(signal.SIGTERM, on_term)
    headless = "--no-open" in sys.argv          # 맥 Swift 껍데기가 이 모드로 띄운다
    if already_running():
        if not headless:
            open_window()
        sys.exit(0)
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    try:
        import webview                           # Windows: pywebview = 브라우저와 분리된 독립 창
    except ImportError:
        webview = None
    try:
        if headless or not webview:
            if not headless:
                threading.Timer(0.5, open_window).start()
            print(f"할 일 대시보드: {URL}  (Ctrl+C 로 종료)")
            server.serve_forever()
        else:
            threading.Thread(target=server.serve_forever, daemon=True).start()
            webview.create_window("할일", URL, width=1180, height=800, min_size=(380, 500),
                                  background_color="#FDFBF3")
            webview.start()                      # 창을 닫으면 여기서 돌아온다
    except KeyboardInterrupt:
        pass
    finally:
        flush_memo()
