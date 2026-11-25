# 할일 앱 (맥 · Windows 공용)

펼친 노트 3쪽: **왼쪽 플래너 달력**(학기 주차·마감일 형광펜·날짜 클릭 시 그날 마감) · **가운데 줄 노트**(마감 임박 + 이번 주 그 외, 체크) · **오른쪽 떡메모지**(자유 메모).

- 구조: `app.py`(파이썬 표준 라이브러리 서버, 127.0.0.1:8765) + `index.html`. 창은 브라우저와 분리된 네이티브 웹뷰.
  - 맥: `~/Applications/할일.app` = `mac/main.swift`(WKWebView 껍데기)가 `app.py --no-open` 을 자식으로 띄움. Dock 아이콘(LMS)·Cmd+Q·창 위치 기억.
  - Windows: `pywebview` 가 있으면 독립 창(Edge WebView2), 없으면 Chrome/Edge 앱 모드로 대체.
- **`강의노트` 탭**: `Record/summaries/*.md` 요약을 과목별·최신 주차 위로 보여주고 앱 안에서 읽는다 — 강의노트 사이트(아티팩트)와 같은 파서(`build.parse`)라 요약 파일만 커밋되면 반영(사이트 재배포 불필요). 직접 열기: `#note=<요약 stem>`.
- **`자료` 탭**: `<과목>/materials/*` 원본을 다운로드·외부 앱 없이 앱 안에서 본다. 원본은 **읽기만** 한다(`/file` 은 materials/ 안·허용 확장자만 서빙).
  PDF = `vendor/pdfjs/`(pdf.js 3.11 — 웹뷰 내장 뷰어는 배율 제어가 안 돼서 직접 그림, `cmaps/` 가 한글 CID 폰트 담당) · PPTX = `vendor/pptx-preview.umd.js`(브라우저에서 직접 렌더, 일부 서식 근사) · HWP = `tools/hwp2txt.py` 로 본문 텍스트(표 칸·그림 없음) · .c = 코드 그대로 · .key = 못 엶(같은 이름 pptx 있으면 숨김).
  **배율 막대**: `−` `%`(클릭=100%) `+` · `↔ 가로 맞춤` · `↕ 세로 맞춤`(한 쪽이 창 높이에) — 맞춤 모드는 창 크기를 바꾸면 따라 다시 맞추고, 마지막 맞춤 모드를 기억한다. 단축키 ⌘+ / ⌘− / ⌘0(가로 맞춤), 트랙패드 핀치. HWP·코드는 글자 크기만 ±.
  자료를 열면 달력·메모를 접고 넓게 쓴다. 직접 열기: `#mat=<경로>`. **다른 기기에서는 materials/ 가 커밋·pull 돼야 보인다.**
- **`개념` 탭**: Obsidian 식 연결 노트. `<과목>/개념/<개념명>.md` (파일명 = 개념명, frontmatter `aliases`·`sources`, 첫 `>` 블록 = 정의, 본문 `[[개념]]` 링크)를 검색·이동한다.
  왼쪽 검색(이름·별칭·본문 + 강의노트 전문 `/api/search`) · 가운데 개념 페이지(정의 → 본문 → 나온 곳: `sources` 근거 + 이름이 등장하는 요약 자동 '언급') · 오른쪽 연결 지도 + 역링크.
  페이지 없는 `[[링크]]` = 주황 '빈 페이지'(근거 약하면 지어내지 않고 비워 둔다). 나온 곳을 누르면 강의노트로 열리고 `← 개념` 으로 돌아온다. 직접 열기: `#concept=<개념명>`. 개념 md 는 과목 전담 에이전트가 쓴다.
- 파서는 `Record/site/build.py` 것을 import → 사이트 `할 일` 탭과 규칙 동일. **정본은 md 파일.**
- **동기화 = git**: 열 때·2분마다 pull, 체크하면 그 파일만 commit + push. 메모는 `<repo>/메모.md` 에 0.4초 뒤 저장, 20초 모아 push(창 닫을 때도).
  pull 이 충돌하면 즉시 `rebase --abort` — repo 를 rebase 중 상태로 남기지 않는다. 실패는 상단에 빨간 글씨.
  양쪽 기기에서 **메모를 동시에** 고치면 충돌 → 한쪽 push 가 실패로 표시된다(로컬 파일엔 남음).

## 설치·실행
| 기기 | 처음 한 번 | 이후 |
|---|---|---|
| 맥 | `bash dash/make-mac-app.sh` (swiftc + 아이콘 + 로그인 자동 실행 등록) | 로그인하면 자동으로 뜸 · Spotlight `할일` |
| Windows | `python -m pip install pywebview` → `dash\launch-windows.bat` 바탕화면 바로가기 | 바로가기 더블클릭 |

- `mac/main.swift`·아이콘을 고쳤으면 `make-mac-app.sh` 다시. `app.py`·`index.html` 은 앱 재실행만.
- 끄기(맥 자동 실행): `launchctl bootout gui/$(id -u)/com.hoseostudykit.dash`
- 손글씨 폰트(Gaegu·Gowun Batang)는 Google Fonts — 오프라인이면 기본 글꼴.

## 개념 노트 형식 — `<과목>/개념/<개념명>.md`

```markdown
---
aliases: [별칭1, 별칭2]
sources: [2026-09-08_slug_주제]     # 근거가 된 요약 stem
---

> 한두 줄 정의 (첫 `>` 블록 = 정의)

본문. 다른 개념은 [[개념명]] 으로 잇는다. 근거가 약하면 페이지를 만들지 말고 링크만 둔다(앱에서 '빈 페이지'로 보임).
```
