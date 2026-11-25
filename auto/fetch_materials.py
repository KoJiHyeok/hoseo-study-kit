#!/usr/bin/env python3
"""LMS 강의자료 → <과목>/materials/ 자동 수집 (맥·Windows — Aside 필요, LMS 에 로그인돼 있어야 함).

- LMS 접근은 `aside repl` 로 한다: 로그인된 Aside 탭 안에서 fetch (Node 쪽 fetch 는 쿠키가 안 붙어 리다이렉트 루프).
- 대상: 과목 '자료 목록'(course/resources.php)의 ubfile·resource(단일 파일)와 folder(묶음). vod(영상)는 제외.
- 원장 auto/materials-ledger.json 에 받은 항목을 적어 다음부터 건너뛴다.
- 받은 파일과 **내용(md5)이 같은 파일이 materials/ 에 이미 있으면 저장하지 않는다** (예전에 손으로 이름 바꿔 넣은 것 포함).
- 새 파일은 `<NN>주차_<LMS 원본 파일명>` 으로 저장. 원본 바이트 그대로 — 변환·수정 없음.
- **세션이 만료돼 있으면 aside 로 다시 로그인하고 이어서 받는다** (저장된 아이디·비밀번호 자동완성만 — 입력·추측 안 함, 최대 3회).
- 출력 마지막 줄 = JSON 요약 {"login": bool, "relogin": n, "new": [...], "skipped": [...]}. 종료코드 0 정상 / 2 재로그인까지 실패 / 1 기타 실패.

사용: python auto/fetch_materials.py [--dry-run] [과목slug ...]   (맥은 python3)
"""
import base64, hashlib, json, re, subprocess, sys, tempfile
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent.parent            # repo 루트
sys.path.insert(0, str(ROOT))
from kit import COURSES as _C, LMS_BASE  # noqa: E402  과목·LMS id 는 config.json 이 정본

LEDGER = ROOT / "auto" / "materials-ledger.json"
COURSES = {slug: (c["lms_id"], c["dir"]) for slug, c in _C.items() if c.get("lms_id")}   # slug: (course id, 폴더)
EXTS = {".pdf", ".pptx", ".ppt", ".hwp", ".hwpx", ".docx", ".c", ".h", ".cpp", ".py", ".txt", ".key"}
MAX_MB = 60
BASE = LMS_BASE


def repl(js):
    """aside repl 1회 실행 → 'RESULT:' 로 시작하는 줄의 JSON 을 돌려준다."""
    p = subprocess.run(["aside", "repl", js], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=170)
    for line in (p.stdout + p.stderr).splitlines():
        if line.startswith("RESULT:"):
            return json.loads(line[7:])
    raise RuntimeError("aside repl 결과 없음: " + (p.stdout + p.stderr)[-400:])


RELOGIN_TRIES = 3
RELOGIN_PROMPT = (
    "{base}/login/index.php 를 열어라. 상단에 로그아웃 링크가 보이면 이미 로그인된 것이니 아무것도 누르지 말고 끝내라. "
    "로그인 페이지면 브라우저에 저장된 아이디·비밀번호 자동완성으로 채우고 로그인 버튼을 눌러라. "
    "자동완성이 안 되면 추측하거나 직접 입력하지 말고 '저장된 비밀번호 없음' 이라고 보고하고 멈춰라. "
    "로그인 버튼을 눌렀는데 여전히 로그인 페이지면 5초 뒤 한 번 더 눌러라. 로그인 외에는 아무것도 누르지 마라."
)


def relogin():
    """LMS 세션 만료 → aside 로 재로그인. 성공 여부는 호출한 쪽이 목록을 다시 읽어 판정한다."""
    try:
        subprocess.run(["aside", "--timeout", "4m", RELOGIN_PROMPT.format(base=BASE)], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=300)
    except Exception as e:                                   # aside 미설치·타임아웃 — 재시도 루프가 실패로 끝낸다
        print(f"  ! 재로그인 호출 실패: {e}", file=sys.stderr)


def with_login(summary, fn, *args):
    """fn 결과가 login:false 면 재로그인 후 다시 부른다 (최대 RELOGIN_TRIES 회)."""
    r = fn(*args)
    while not r.get("login") and summary["relogin"] < RELOGIN_TRIES:
        summary["relogin"] += 1
        print(f"  · LMS 세션 만료 → aside 재로그인 ({summary['relogin']}/{RELOGIN_TRIES})", file=sys.stderr)
        relogin()
        r = fn(*args)
    return r


def list_course(cid):
    """자료 목록: [{kind, id, title, week, files?}] — folder 는 안의 pluginfile 링크까지 펼친다."""
    js = r"""
const pgL = await openTab("%s/course/resources.php?id=%d");
const outL = await pgL.evaluate(async () => {
  if (/login\/index\.php/.test(location.href)) return { login: false };
  let week = 0; const items = [];
  for (const tr of document.querySelectorAll("table.generaltable tbody tr")) {
    const sec = tr.cells[0]?.innerText.trim(); const m = sec && sec.match(/(\d+)\s*주차|week\s*(\d+)/i);
    if (m) week = +(m[1] || m[2]);
    const a = tr.querySelector("a[href*='/mod/']"); if (!a) continue;
    const km = a.href.match(/\/mod\/(\w+)\/view\.php\?id=(\d+)/); if (!km) continue;
    const it = { kind: km[1], id: km[2], title: a.innerText.trim(), week };
    if (it.kind === "folder") {
      const h = await (await fetch(a.href, { credentials: "include" })).text();
      it.files = [...new Set([...h.matchAll(/href="([^"]*pluginfile\.php[^"]*)"/g)].map(x => x[1].replace(/&amp;/g, "&")))];
    }
    items.push(it);
  }
  return { login: true, items };
});
console.log("RESULT:" + JSON.stringify(outL)); await closeTab(pgL);
""" % (BASE, cid)
    return repl(js)


def download(cid, url):
    """탭 안 fetch 로 받아 base64 로 넘긴다 → (최종 URL, bytes).
    본문을 받기 **전에** 응답 헤더로 확장자·크기를 거른다 — 100MB 넘는 pptx·영상을 다 받다가 CDP 30초 제한에 걸린 적 있다."""
    js = r"""
const pgD = await openTab("%s/course/resources.php?id=%d");
const outD = await pgD.evaluate(async ({ u, exts, max }) => {
  if (/login\/index\.php/.test(location.href)) return { login: false };
  const ac = new AbortController();
  const r = await fetch(u, { credentials: "include", signal: ac.signal });
  if (/login\/index\.php/.test(r.url)) { ac.abort(); return { login: false }; }
  if (!r.ok) { ac.abort(); return { login: true, error: "HTTP " + r.status }; }
  const name = decodeURIComponent(new URL(r.url).pathname.split("/").pop());
  const ext = ((name.match(/\.[^.]+$/) || [""])[0]).toLowerCase();
  if (!exts.includes(ext)) { ac.abort(); return { login: true, url: r.url, skip: "ext" }; }
  const len = +r.headers.get("content-length") || 0;
  if (len > max) { ac.abort(); return { login: true, url: r.url, error: "too big " + len }; }
  const blob = await r.blob();
  if (blob.size > max) return { login: true, url: r.url, error: "too big " + blob.size };
  const b64 = await new Promise((ok, no) => { const f = new FileReader(); f.onload = () => ok(f.result.slice(f.result.indexOf(",") + 1)); f.onerror = no; f.readAsDataURL(blob); });
  return { login: true, url: r.url, ctype: r.headers.get("content-type"), b64 };
}, { u: %s, exts: %s, max: %d });
console.log("RESULT:" + JSON.stringify(outD)); await closeTab(pgD);
""" % (BASE, cid, json.dumps(url), json.dumps(sorted(EXTS)), MAX_MB * 1048576)
    return repl(js)


TEXT_EXTS = {".c", ".h", ".cpp", ".py", ".txt"}


def md5(b, name=""):
    """내용 비교용. 코드·텍스트는 줄바꿈 차이(LMS CRLF vs repo LF — .gitattributes eol=lf)를 무시한다."""
    if Path(name).suffix.lower() in TEXT_EXTS:
        b = b.replace(b"\r\n", b"\n")
    return hashlib.md5(b).hexdigest()


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry-run" in sys.argv
    ledger = json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.exists() else {}
    summary = {"login": True, "relogin": 0, "new": [], "skipped": [], "errors": []}
    for slug, (cid, folder) in COURSES.items():
        if args and slug not in args:
            continue
        mat = ROOT / folder / "materials"
        have = {md5(f.read_bytes(), f.name): f.name for f in mat.glob("*") if f.is_file()} if mat.exists() else {}
        done = ledger.setdefault(slug, {})
        lst = with_login(summary, list_course, cid)
        if not lst.get("login"):
            summary["login"] = False
            break
        # 받을 후보: (원장 키, 다운로드 URL, 주차)
        todo = []
        for it in lst["items"]:
            if it["kind"] in ("ubfile", "resource"):
                todo.append((f"{it['kind']}:{it['id']}", f"{BASE}/mod/{it['kind']}/view.php?id={it['id']}", it["week"]))
            elif it["kind"] == "folder":
                for u in it.get("files", []):
                    todo.append(("pf:" + urlparse(u).path, u, it["week"]))
        for key, url, week in todo:
            if key in done:
                continue
            if dry:
                summary["new"].append(f"{slug} {week}주차 (dry) {unquote(url.rsplit('/', 1)[-1])}")
                continue
            try:
                r = with_login(summary, download, cid, url)
            except Exception as e:                          # 한 파일 실패가 나머지를 막지 않게
                summary["errors"].append(f"{slug} {url}: {str(e)[-160:]}")
                continue
            if not r.get("login"):
                summary["login"] = False
                break
            if r.get("skip") == "ext":                      # 영상 등 — 본문을 받지 않고 원장에만 남긴다
                name = unquote(urlparse(r["url"]).path.rsplit("/", 1)[-1])
                done[key] = {"skip": name}
                summary["skipped"].append(f"{slug} {name} (확장자)")
                continue
            if r.get("error") or "b64" not in r:
                summary["errors"].append(f"{slug} {url}: {r.get('error')}")
                if str(r.get("error", "")).startswith("too big"):    # 매일 다시 받지 않게 원장에 남긴다
                    done[key] = {"skip": r["error"], "url": r.get("url", url)}
                continue
            name = unquote(urlparse(r["url"]).path.rsplit("/", 1)[-1]).replace("/", "_").strip()
            ext = Path(name).suffix.lower()
            if ext not in EXTS:
                done[key] = {"skip": name}
                summary["skipped"].append(f"{slug} {name} (확장자)")
                continue
            data = base64.b64decode(r["b64"])
            h = md5(data, name)
            if h in have:                                   # 이미 있음(이름만 다를 수 있음)
                done[key] = {"file": have[h], "md5": h}
                continue
            mat.mkdir(parents=True, exist_ok=True)
            out = mat / f"{week:02d}주차_{name}"
            n = 2
            while out.exists():
                out = mat / f"{week:02d}주차_{Path(name).stem} ({n}){ext}"; n += 1
            out.write_bytes(data)
            have[h] = out.name
            done[key] = {"file": out.name, "md5": h}
            summary["new"].append(f"{folder}/materials/{out.name}")
        if not summary["login"]:
            break
    if not dry:
        LEDGER.write_text(json.dumps(ledger, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    sys.exit(0 if summary["login"] else 2)


if __name__ == "__main__":
    main()
