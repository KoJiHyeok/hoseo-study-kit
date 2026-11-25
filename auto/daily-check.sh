#!/bin/zsh
# 매일 마감·제출 상태 점검 (맥) — 설치: auto/install-daily-mac.sh  (매일 07:40)
# 수동 실행: auto/daily-check.sh

export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG="$ROOT/auto/last-run.log"
cd "$ROOT" || exit 1

stamp() { date "+%Y-%m-%d %H:%M"; }

# Aside 가 떠 있어야 LMS 에 접근할 수 있다 (사용자 로그인 보유)
if ! pgrep -x Aside >/dev/null 2>&1; then
  open -a Aside
  for i in $(seq 1 24); do
    sleep 5
    pgrep -x Aside >/dev/null 2>&1 && break
  done
  sleep 15   # 데몬이 뜰 시간
fi

if ! pgrep -x Aside >/dev/null 2>&1; then
  echo "$(stamp) 실패: Aside 가 실행되지 않음 (LMS 접근 불가)" >> "$LOG"
  python3 auto/notify.py "⚠️ 자동점검 실패: Aside 미실행. 수동 확인 필요" >/dev/null 2>&1
  exit 1
fi

claude -p "$(cat "$ROOT/auto/PROMPT.md")" \
  --permission-mode bypassPermissions \
  >> "$ROOT/auto/last-run.out" 2>&1

rc=$?
[ $rc -ne 0 ] && echo "$(stamp) 실패: claude 종료코드 $rc" >> "$LOG"
exit $rc
