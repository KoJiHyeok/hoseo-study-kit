#!/usr/bin/env python3
"""LMS 강의자료 → <과목>/materials/ 자동 수집 (맥·Windows — Aside 필요, LMS 에 로그인돼 있어야 함).

- LMS 접근은 `aside repl` 로 한다: 로그인된 Aside 탭 안에서 fetch (Node 쪽 fetch 는 쿠키가 안 붙어 리다이렉트 루프).
- 대상: 과목 '자료 목록'(course/resources.php)의 ubfile·resource(단일 파일)와 folder(묶음). vod(영상)는 제외.
- 원장 auto/materials-ledger.json 에 받은 항목을 적어 다음부터 건너뛴다.
- 받은 파일과 **내용(md5)이 같은 파일이 materials/ 에 이미 있으면 저장하지 않는다** (예전에 손으로 이름 바꿔 넣은 것 포함).
- 새 파일은 `<NN>주차_<LMS 원본 파일명>` 으로 저장. 원본 바이트 그대로 — 변환·수정 없음.
- 출력 마지막 줄 = JSON 요약 {"login": bool, "new": [...], "skipped": [...]}. 종료코드 0 정상 / 2 로그인 만료 / 1 기타 실패.

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
    """탭 안 fetch 로 받아 base64 로 넘긴다 → (최종 URL, bytes)."""
    js = r"""
const pgD = await openTab("%s/course/resources.php?id=%d");
const outD = await pgD.evaluate(async (u) => {
  if (/login\/index\.php/.test(location.href)) return { login: false };
  const r = await fetch(u, { credentials: "include" });
  if (!r.ok) return { login: true, error: "HTTP " + r.status };
  if (/login\/index\.php/.test(r.url)) return { login: false };
  const buf = new Uint8Array(await r.arrayBuffer());
  if (buf.length > %d * 1048576) return { login: true, error: "too big " + buf.length, url: r.url };
  let s = ""; for (let i = 0; i < buf.length; i += 32768) s += String.fromCharCode.apply(null, buf.subarray(i, i + 32768));
  return { login: true, url: r.url, ctype: r.headers.get("content-type"), b64: btoa(s) };
}, %s);
console.log("RESULT:" + JSON.stringify(outD)); await closeTab(pgD);
""" % (BASE, cid, MAX_MB, json.dumps(url))
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
    summary = {"login": True, "new": [], "skipped": [], "errors": []}
    for slug, (cid, folder) in COURSES.items():
        if args and slug not in args:
            continue
        mat = ROOT / folder / "materials"
        have = {md5(f.read_bytes(), f.name): f.name for f in mat.glob("*") if f.is_file()} if mat.exists() else {}
        done = ledger.setdefault(slug, {})
        lst = list_course(cid)
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
            r = download(cid, url)
            if not r.get("login"):
                summary["login"] = False
                break
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
