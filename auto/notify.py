#!/usr/bin/env python3
"""자동 점검 알림 — auto/.env 에 DISCORD_WEBHOOK=... 이 있으면 Discord 로 보내고, 없으면 auto/notify.log 에만 남긴다.

사용: python auto/notify.py "<메시지>"
auto/.env 는 .gitignore 돼 있다. 웹훅 주소를 커밋하지 마라.
"""
import json, sys
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen

HERE = Path(__file__).resolve().parent


def webhook():
    env = HERE / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("DISCORD_WEBHOOK="):
                return line.split("=", 1)[1].strip()
    return ""


def main():
    msg = " ".join(sys.argv[1:]).strip()
    if not msg:
        sys.exit("메시지가 비었습니다")
    with open(HERE / "notify.log", "a", encoding="utf-8") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M} {msg}\n")
    url = webhook()
    if url:
        req = Request(url, data=json.dumps({"content": msg[:1900]}).encode(),
                      headers={"Content-Type": "application/json", "User-Agent": "study-kit-notify"})
        urlopen(req, timeout=15).read()
    print("알림:", msg, "(Discord)" if url else "(로그만)")


if __name__ == "__main__":
    main()
