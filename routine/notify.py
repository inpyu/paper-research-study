#!/usr/bin/env python3
"""푸시 알림. 서버가 직접 보낸다 — 사이트에는 서버가 없다.

ntfy.sh 는 계정도 키도 필요 없다. 토픽 이름이 곧 주소이므로 추측 못 할 이름을 쓴다.
설정: ~/.config/reposcholar/notify.json  {"ntfy_topic": "..."}  또는 환경변수 NTFY_TOPIC
알림 실패는 루틴 전체를 실패시키지 않는다.
"""
import json
import os
import sys
import urllib.request
from datetime import datetime

CFG = os.path.expanduser("~/.config/reposcholar/notify.json")
SITE = "https://paper-research-study.vercel.app/"


def topic():
    if os.environ.get("NTFY_TOPIC"):
        return os.environ["NTFY_TOPIC"]
    if os.path.exists(CFG):
        return json.load(open(CFG, encoding="utf-8")).get("ntfy_topic")
    return None


def send(title, body, tags="books", click=SITE, priority="default"):
    t = topic()
    if not t:
        print("알림 설정 없음 — 건너뜀 (~/.config/reposcholar/notify.json)")
        return 0
    req = urllib.request.Request(
        f"https://ntfy.sh/{t}", data=body.encode("utf-8"), method="POST",
        headers={"Title": title.encode("utf-8").decode("latin-1", "ignore"),
                 "Tags": tags, "Click": click, "Priority": priority,
                 "Markdown": "yes"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            r.read()
        print(f"알림 발송: {title}")
        return 0
    except Exception as e:
        print(f"알림 실패(무시): {e}")
        return 0


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    d = os.path.join(root, "out", "briefings")
    files = sorted(os.listdir(d)) if os.path.isdir(d) else []
    if not files:
        return send("RepoScholar", "오늘 새 브리핑이 없습니다.", tags="zzz")
    b = json.load(open(os.path.join(d, files[-1]), encoding="utf-8"))
    today = datetime.now().astimezone().strftime("%Y-%m-%d")
    if b.get("date") != today:
        # 오늘 새 브리핑이 없으면 어제 것을 '오늘의 브리핑' 으로 보내지 않는다.
        return send("RepoScholar · 새 브리핑 없음",
                    f"오늘({today})은 새로 다룰 논문이 없었습니다. "
                    f"최신 브리핑은 {b.get('date')} 입니다.",
                    tags="zzz", priority="low")
    items = b["items"]
    must = [x for x in items if x["verdict"] == "must-read"]
    head = f"{b['date']} · 논문 {len(items)}편" + (
        f" · must-read {len(must)}편" if must else "")
    body = "\n".join(f"**[{x['verdict']}]** {x['title']}\n{x['relation']}"
                     for x in items)
    return send(f"오늘의 브리핑 — {head}", body,
                tags="books" if not must else "fire",
                priority="high" if must else "default")


if __name__ == "__main__":
    sys.exit(main())
