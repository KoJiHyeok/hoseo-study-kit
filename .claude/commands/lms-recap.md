# /lms-recap — LMS 새 강의 영상 → 전사 → 요약 → 강의노트 배포 (맥 · 애플 실리콘 전용)

LMS(Moodle/Coursemos)에 새로 열린 강의 영상을 찾아 음성 추출 → 로컬 Whisper 전사 → 과목 에이전트 배합 요약 → 사이트 재배포까지 한 번에.

## 준비 (처음 한 번 — SETUP.md 9번)

- `brew install ffmpeg`
- `python3 -m venv ~/.venvs/stt && ~/.venvs/stt/bin/pip install mlx-whisper pymupdf`
- 모델 `mlx-community/whisper-large-v3-turbo` 는 첫 실행 때 받는다.
- Windows 에서는 실행하지 않는다 (mlx 는 애플 실리콘 전용, ffmpeg 없음).

## 원장

`Record/lms-ledger.json` — `{"processed": {vid: stem}, "skipped": {vid: 사유}}`. 없으면 만든다.

## 절차

1. `git pull --rebase`
2. **새 영상 탐지** — `aside repl` 로 로그인된 탭 안에서 fetch (패턴은 `auto/fetch_materials.py` 의 `repl()`). `config.json` 각 과목 `lms_id` 의 `<lms_base>/course/view.php?id=<id>` 에서 `mod/vod/view.php?id=` 링크의 vid·제목·학습기간·길이를 뽑는다.
   - 오늘이 학습기간 안인 영상만. 원장에 있는 vid 는 제외. 설치 가이드류(~5분 화면 따라하기)는 skipped.
3. **m3u8 추출** — `<lms_base>/mod/vod/viewer.php?id=<vid>` HTML 에서 `https://…\.m3u8` 정규식.
4. **음성 추출** — `ffmpeg -nostdin -y -loglevel error -i "<m3u8>" -vn -ac 1 -ar 16000 <임시>/<stem>.mp3 < /dev/null`
   - 끝의 "Error during demuxing" 는 무시하고 `ffprobe` 길이(표기 ±10초)로 성공 판정.
5. **전사** — 한 번에 하나씩:
   ```
   ~/.venvs/stt/bin/python -c "import mlx_whisper; r=mlx_whisper.transcribe('<mp3>', path_or_hf_repo='mlx-community/whisper-large-v3-turbo', language='ko', condition_on_previous_text=False); open('Record/transcripts/<stem>.txt','w').write(r['text'].strip())" < /dev/null
   ```
   파일명 `YYYY-MM-DD_<slug>_<주제-kebab>.txt`.
6. **요약** — 과목 전담 에이전트 `course-<agent>` 에 전사 경로 + 같은 주차 자료 + 필기를 넘겨 배합 요약 (여러 과목이면 병렬).
7. **사이트** — `python3 Record/site/build.py` → `site_url` 로 재배포.
8. **원장 · 보고** — 원장 갱신. 과목별 결과 + 영상 속 과제·마감 언급 + **학습기간 마감일**(출석은 학생이 직접 재생해야 인정된다).
9. commit + push.

## 함정 (실측)

- **ffmpeg 는 stdin 을 먹는다** — `while read` 루프 안에서 돌리면 다음 줄을 삼켜 영상이 조용히 빠진다. 항상 `-nostdin … < /dev/null`. 끝나면 전사본 개수 = 목록 개수 대조.
- **CDN DNS 실패** (`nodename nor servname`) — `dig +short <host>` 로 IP 를 얻어 `curl --resolve "<host>:443:<ip>"` 로 `index.m3u8` 과 세그먼트를 직접 받아 이어붙인 뒤 ffmpeg 변환.
- **Metal 미가용** (백그라운드에서 `Unable to reach MTLCompilerService`) — `import mlx.core as mx; mx.set_default_device(mx.cpu)` 로 CPU 전사 (28분 영상 ≈ 11분). 긴 전사는 `subprocess.Popen(start_new_session=True)` 로 떼어 낸다.
- 전사본·요약은 수업 콘텐츠 — private repo 와 비공개 Artifact 밖으로 내보내지 않는다.
