# hoseo-study-kit

호서대 학생용 **학기 공부 시스템**입니다. Claude Code 가 LMS 자료를 모아 주차별 강의노트, 시험지, 할 일을 만들어 주고, 데스크톱 할일 앱과 강의노트 사이트로 보여 줍니다.

```
LMS ──aside──▶ materials/ ──과목 전담 에이전트──▶ 요약 · 시험지 · 할일 · 개념
                    ▲                                     │
            내 필기 · 영상 전사(맥)                         ▼
                                     할일 앱(데스크톱) · 강의노트 사이트(Claude Artifact)
                                                   │
                                          git 으로 노트북 ↔ 데스크톱 동기화
```

## 설치 — Claude Code 에 이렇게 말하세요

```
https://github.com/KoJiHyeok/hoseo-study-kit 받아서 SETUP.md 대로 내 버전 설치해줘
```

Claude 가 아래를 순서대로 진행합니다.

1. 내 GitHub 에 **private repo** 를 만듭니다.
2. Aside 로 LMS 의 내 강좌 목록을 읽습니다.
3. 관리할 과목을 내게 확인받습니다.
4. 과목별 폴더와 전담 에이전트를 만듭니다.
5. 첫 강의자료를 받습니다.
6. 할일 앱을 설치하고 강의노트 사이트를 배포합니다.

자세한 절차는 [`SETUP.md`](SETUP.md)에 있습니다.

### 미리 있어야 하는 것

| | 필수 | 용도 |
|---|:-:|---|
| [Claude Code](https://claude.com/claude-code) (유료 플랜) | ✅ | 요약, 에이전트, 사이트 배포 전부 |
| git · GitHub 계정 · [`gh`](https://cli.github.com) | ✅ | 내 private repo, 기기 간 동기화 |
| Python 3.9+ | ✅ | 앱, 사이트 빌드, 자료 수집 |
| [Aside](https://aside.com) | 권장 | LMS 자동 접속 (없으면 자료를 직접 내려받아 넣는 수동 모드) |
| 맥 애플 실리콘 + ffmpeg | 선택 | LMS 강의 영상 전사 |

## 매일 쓰는 법

1. **수업 중**: `<과목>/필기/NN주차.md` 에 필기합니다. 맨 위 `##### Keyword` 블록에 그날 키워드 2~3개를 적습니다.
2. **수업 후**: Claude Code 에서 `/today` 를 실행합니다. 자료 수집, 요약, 할일, 시험지, 사이트, push 까지 이어서 하고, 소화용 질문을 남깁니다.
3. **시험 전**: `/quiz <자료>` 로 객관식 문제를 만든 뒤 사이트 `시험지` 탭에서 풀고 채점합니다.
4. **(선택) 매일 07:40 자동 점검**: LMS 마감·제출 상태와 새 자료를 확인해 할일에 반영합니다.

## 구성

| 경로 | 무엇 |
|---|---|
| `config.json` | 내 과목, 학기, LMS course id. **바꿀 곳은 여기 하나** |
| `setup.py` | config 로 과목 폴더와 에이전트를 생성 (`--check` 는 환경 점검) |
| `dash/` | 할일 앱: 달력, 마감, 메모, 강의노트, 시험지, 개념, 자료 뷰어 (맥 `.app`, Windows pywebview) |
| `Record/site/` | 강의노트 사이트 빌드 |
| `auto/` | LMS 자료·마감 수집, 매일 자동 점검 (맥 LaunchAgent, Windows 작업 스케줄러) |
| `.claude/` | `/today`, `/quiz`, `/lms-recap`, 과목 에이전트 템플릿 |
| `tools/` | HWP·PPTX 텍스트 추출 (표준 라이브러리만 사용) |

## 주의

- **내 repo 는 private 으로 두세요.** 강의자료와 영상 전사는 교수님 저작물입니다. 강의노트 사이트도 비공개 Artifact 그대로 둡니다.
- LMS 퀴즈와 과제는 **열어 보기만** 하고, 제출은 학생이 확인한 뒤에만 합니다. 자동 점검은 응시·제출 버튼을 절대 누르지 않습니다.
- 학번과 비밀번호는 어디에도 저장하지 않습니다. LMS 로그인은 Aside 브라우저에 저장된 것만 씁니다.
- AI 요약은 공부 보조 도구입니다. 과제를 AI 로 대신 쓰는 용도가 아닙니다. 교수님의 AI 사용 방침을 따르세요.

## 라이선스

MIT. `dash/vendor/` 의 pdf.js(Apache-2.0), marked(MIT), pptx-preview(ISC)는 각자의 라이선스를 따릅니다.
