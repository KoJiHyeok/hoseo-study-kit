# SETUP.md — Claude Code 가 따라 하는 설치 절차

> 이 파일은 **Claude Code(에이전트)에게 주는 지시서**다. 학생이 이 repo 링크를 주며 "설치해줘"라고 하면, 아래를 위에서부터 순서대로 실행한다.
> 학생에게는 **꼭 필요한 것만** 묻는다(과목 확인, 개강일). 나머지는 직접 확인하고 처리한다.

## 0. 원칙

- 결과물은 **학생 본인의 private repo** 다. 이 템플릿 repo 에 push 하지 않는다.
- 강의자료·요약·전사·메모는 학생 private repo 에만 쌓인다. **public 으로 만들지 않는다.**
- 학생의 학번·비밀번호를 묻거나 파일에 쓰지 않는다. LMS 로그인은 Aside 브라우저에 저장된 것만 쓴다.
- 맥이면 `python3`, Windows 면 `python` (Windows `python3` 은 조용히 실패하는 스텁).

## 1. 환경 점검

```
git --version
gh auth status            # 안 돼 있으면 학생에게: ! gh auth login
aside --version           # 없으면 https://aside.com 설치 안내 — 없어도 수동 모드로 진행 가능
python --version          # 3.9+
```

빠진 게 있으면 한 번에 모아서 설치 방법을 안내하고, 학생이 설치를 마치면 이어서 진행한다.
PyMuPDF 는 바로 설치한다: `python -m pip install pymupdf` (Windows 는 `pywebview` 도: `python -m pip install pywebview`).

## 2. 학생 private repo 만들기

repo 이름은 기본 `study-<학기>` (예: `study-2026-2`). 위치는 `~/dev/` 아래.

```
cd ~/dev
gh repo create study-2026-2 --private --template <이 템플릿 repo의 owner/name> --clone
cd study-2026-2
```

`--template` 이 거절되면: `git clone <템플릿 URL> study-2026-2` → `cd` → `git remote remove origin` → `gh repo create study-2026-2 --private --source . --push`.

**이후 모든 작업은 이 새 repo 안에서 한다.** 이 시점부터 새 repo 의 `CLAUDE.md` 가 운영 규칙이다.

## 3. 과목 찾기 — aside 로 LMS 를 본다

학생에게 먼저 "Aside 브라우저에서 LMS(https://learn.hoseo.ac.kr)에 로그인해 두세요"라고 하고 확인을 받는다. 그다음:

```
aside "https://learn.hoseo.ac.kr 를 열어 (로그인 페이지면 저장된 아이디·비밀번호 자동완성으로 로그인, 자동완성 안 되면 멈추고 보고). '나의 강좌'(대시보드 강좌 목록)에서 이번 학기 강좌를 전부 찾아 각각 강좌명 · 교수명 · course id(주소 course/view.php?id= 의 숫자) · 강의 시간(보이면)을 표로 알려줘. 아무것도 누르거나 제출하지 마."
```

aside 결과로 표를 만들어 학생에게 **한 번에** 확인받는다:

- 관리할 과목 고르기 (교양·관리 안 할 과목은 뺀다)
- 요일·시간이 비어 있으면 채워 달라고
- 개강일 (`semester_start` = 개강 주 **월요일**)
- 시험이 매주 퀴즈·과제에서 거의 그대로 나오는 과목 → `exam_weekly: true`

aside 가 없거나 실패하면 학생에게 과목명·교수·요일시간을 직접 받는다. course id 는 LMS 강좌 주소의 `id=` 숫자라고 알려 준다.

## 4. config.json → setup

`config.example.json` 을 `config.json` 으로 복사해 채운다.

- `slug`: 짧은 한글/영문, **`_`·공백 금지** (요약 파일명에 들어간다). 예: `자료구조`, `운영체제`, `영어`
- `dir`: 과목 폴더 이름 (보통 정식 과목명)
- `agent`: 영문 소문자 id (예: `ds`, `os`, `eng`) → 에이전트 `course-ds`
- `short`: 달력에 뜰 2~4글자
- `hue`: 생략하면 자동

```
python setup.py
```

출력의 "새로 만든 파일"과 "환경 점검"을 확인한다. 오류가 나면 config.json 을 고쳐 다시 돌린다.

## 5. 첫 자료 수집 (aside 있을 때)

```
python auto/fetch_materials.py --dry-run     # 받을 목록만
python auto/fetch_materials.py               # 실제로 받기
```

종료코드 2 = 로그인 만료 → 3번의 aside 로그인 호출을 다시 하고 한 번 더. 받은 파일은 `<과목폴더>/materials/` 에 들어간다.

## 6. 할일 앱 설치

**Windows**
```
python -m pip install pywebview
```
바탕화면 바로가기를 만든다 (대상: `dash\launch-windows.bat`):
```powershell
$s = (New-Object -ComObject WScript.Shell).CreateShortcut("$([Environment]::GetFolderPath('Desktop'))\할일.lnk")
$s.TargetPath = (Resolve-Path dash\launch-windows.bat).Path; $s.WorkingDirectory = (Resolve-Path dash).Path; $s.WindowStyle = 7; $s.Save()
```

**맥**
```
bash dash/make-mac-app.sh       # ~/Applications/할일.app + 로그인 시 자동 실행
```
swiftc 가 없으면 `xcode-select --install` 후 다시.

실행해 보고 `http://127.0.0.1:8765/api/ping` 이 `{"app": "hoseo-dash"}` 를 돌려주는지 확인한다.

## 7. 강의노트 사이트 첫 배포

```
python Record/site/build.py
```
→ `Record/site/study-notes.html` 을 Artifact 로 publish (비공개 기본값 유지). 받은 URL 을 `config.json` 의 `site_url` 에 적는다. 이후 재배포는 항상 이 URL 로.

## 8. 매일 자동 점검 (선택 — 학생에게 물어본다)

매일 07:40 에 LMS 마감·제출 상태와 새 자료를 확인해 할일을 갱신하고 push 한다. 그 시간에 컴퓨터가 켜져 있어야 한다.

- 맥: `bash auto/install-daily-mac.sh`
- Windows: `pwsh -File auto\install-daily-windows.ps1`
- Discord 알림을 원하면 `auto/.env` 에 `DISCORD_WEBHOOK=<웹훅 URL>` (커밋 안 됨). 없으면 `auto/notify.log` 에만 남는다.

## 9. LMS 영상 전사 (맥, 애플 실리콘만 — 선택)

```
brew install ffmpeg
python3 -m venv ~/.venvs/stt && ~/.venvs/stt/bin/pip install mlx-whisper pymupdf
```
이후 `/lms-recap` 으로 새 강의 영상을 전사·요약한다. Windows 는 건너뛴다 (자료 기반 요약만).

## 10. 마무리

```
git add -A
git commit -m "setup: <학기> 과목 N개"
git push
```

학생에게 보고할 것:
- 만든 private repo URL, 관리 과목 표
- 할일 앱 여는 법, 강의노트 사이트 URL
- 자동 점검 설치 여부
- **매일 쓰는 법**: 수업 중 `<과목>/필기/NN주차.md` 에 필기 → 수업 후 Claude Code 에서 `/today`
- 다른 기기에서 쓰려면: `gh repo clone <repo>` 후 6번만 하면 된다
