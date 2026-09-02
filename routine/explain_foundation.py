#!/usr/bin/env python3
"""기초 개념 설명 생성 (Claude Code 헤드리스, 구독).

curriculum/foundations.json 의 개념들에 본문을 채운다.
연구 노트가 없는 개념이므로 일반 지식으로 쓰되, 이 연구의 규모와 전제에 맞춘다.
출력: out/explain_found/<key>.json
"""
import argparse
import json
import os
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common import OUT, load, read  # noqa: E402
from generate import call_claude, extract_json, log_usage  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "curriculum", "foundations.json")
DEST = os.path.join(OUT, "explain_found")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-sonnet-5")
    ap.add_argument("--batch", type=int, default=6)
    ap.add_argument("--limit", type=int, default=12)
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(SRC):
        print("커리큘럼이 없다 — 먼저 curriculum.py 를 돌린다")
        return 1
    cur = json.load(open(SRC, encoding="utf-8"))
    repo_keys = [c["key"] for c in load("notes.json")["concepts"]]
    os.makedirs(DEST, exist_ok=True)
    tpl = read(os.path.join(ROOT, "prompts", "foundation.md"))

    todo = []
    for st in cur["stages"]:
        for c in st["concepts"]:
            p = os.path.join(DEST, c["key"].replace(" ", "_") + ".json")
            if not os.path.exists(p):
                todo.append(c)
    if not args.all:
        todo = todo[:args.limit]
    if not todo:
        print("생성할 기초 개념 없음 — 전부 최신")
        return 0

    made = 0
    for i in range(0, len(todo), args.batch):
        chunk = todo[i:i + args.batch]
        items = "\n\n".join(
            f"### key: {c['key']}\n이름: {c['name']}\n한 줄: {c.get('one_liner','')}\n"
            f"단계: {c.get('stage')}\n"
            f"선행: {', '.join(c.get('prerequisites', [])) or '없음'}\n"
            f"이어지는 연구 용어: {', '.join(c.get('leads_to', [])) or '없음'}"
            for c in chunk)
        prompt = (tpl.replace("{REPO_KEYS}", ", ".join(repo_keys))
                     .replace("{ITEMS}", items))
        for attempt in (1, 2):
            res, err = call_claude(prompt, args.model, timeout=600)
            log_usage("foundation", res)
            if err:
                print(f"  배치 {i//args.batch+1} 시도 {attempt}: {err}")
                continue
            obj = extract_json(res.get("result", ""))
            if not obj or "concepts" not in obj:
                print(f"  배치 {i//args.batch+1} 시도 {attempt}: JSON 실패")
                continue
            known = {c["key"]: c for c in chunk}
            wrote = 0
            for e in obj["concepts"]:
                src = known.get(e.get("key"))
                if not src:
                    continue
                e["leads_to"] = [k for k in e.get("leads_to", [])
                                 if k in repo_keys][:3] or src.get("leads_to", [])
                e["name"] = src["name"]
                e["stage"] = src.get("stage", 0)
                e["prerequisites"] = src.get("prerequisites", [])
                e["source"] = "foundation"
                with open(os.path.join(DEST, e["key"].replace(" ", "_") + ".json"),
                          "w", encoding="utf-8") as f:
                    json.dump(e, f, ensure_ascii=False, indent=1)
                wrote += 1
            if wrote:
                made += wrote
                print(f"  배치 {i//args.batch+1}: {wrote}개 "
                      f"({', '.join(c['key'] for c in chunk[:3])}…)")
                break
    total = sum(len(s["concepts"]) for s in cur["stages"])
    done = len([f for f in os.listdir(DEST) if f.endswith(".json")])
    print(f"기초 설명 {made}개 생성 · 누적 {done}/{total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
