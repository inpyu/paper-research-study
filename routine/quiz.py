#!/usr/bin/env python3
"""진단 문제 출제 (Claude Code 헤드리스, 구독).

과목별로 난이도 1~5 에 걸친 문항을 만든다. 적응형 진단이 난이도로 문제를 고른다.
출력: out/quiz/<course_id>.json
"""
import argparse
import json
import os
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common import OUT, load, read  # noqa: E402
from generate import call_claude, extract_json, log_usage  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAT = os.path.join(ROOT, "curriculum", "catalog.json")
DEST = os.path.join(OUT, "quiz")


def keys():
    out = [c["key"] for c in load("notes.json")["concepts"]]
    fp = os.path.join(ROOT, "curriculum", "foundations.json")
    if os.path.exists(fp):
        for st in json.load(open(fp, encoding="utf-8"))["stages"]:
            out += [c["key"] for c in st["concepts"]]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-sonnet-5")
    ap.add_argument("--n", type=int, default=14, help="과목당 문항 수")
    ap.add_argument("--limit", type=int, default=4)
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(CAT):
        print("카탈로그가 없다 — 먼저 catalog.py")
        return 1
    cat = json.load(open(CAT, encoding="utf-8"))
    os.makedirs(DEST, exist_ok=True)
    tpl = read(os.path.join(ROOT, "prompts", "quiz.md"))
    ck = keys()

    todo = []
    for t in cat["tracks"]:
        for c in t["courses"]:
            if not c.get("lessons"):
                continue
            if os.path.exists(os.path.join(DEST, c["id"] + ".json")):
                continue
            todo.append((t, c))
    if not args.all:
        todo = todo[:args.limit]
    if not todo:
        print("출제할 과목 없음 — 전부 최신")
        return 0

    made = 0
    for t, c in todo:
        lessons = "\n".join(
            f"- {l['title']} — {l['one_liner']}"
            + (f" (주제: {', '.join(l['quiz_topics'])})" if l.get("quiz_topics") else "")
            for l in c["lessons"])
        prompt = (tpl.replace("{COURSE}", f"{c['title']}\n영역: {t['title']}")
                     .replace("{LESSONS}", lessons)
                     .replace("{CONCEPTS}", ", ".join(ck))
                     .replace("{N}", str(args.n)))
        for attempt in (1, 2):
            res, err = call_claude(prompt, args.model, timeout=600)
            log_usage("quiz", res)
            if err:
                print(f"  {c['id']} 시도 {attempt}: {err}")
                continue
            obj = extract_json(res.get("result", ""))
            if not obj or not obj.get("items"):
                print(f"  {c['id']} 시도 {attempt}: JSON 실패")
                continue
            items, biased_n = [], 0
            for i, it in enumerate(obj["items"], 1):
                ch = it.get("choices") or []
                a = it.get("answer")
                if len(ch) != 4 or not isinstance(a, int) or not 0 <= a <= 3:
                    continue
                if len({x.strip() for x in ch}) != 4:
                    continue          # 보기 중복이면 정답이 하나가 아니다
                L = [len(x) for x in ch]
                if L[a] == max(L) and max(L) >= 20 and max(L) > sorted(L)[-2] * 1.45:
                    biased_n += 1     # 길이로 찍히는 문항. quiz_fix.py 가 교정한다
                items.append({
                    "id": it.get("id") or f"{c['id']}-q{i:02d}",
                    "course": c["id"], "course_title": c["title"],
                    "track": t["id"],
                    "topic": it.get("topic", ""),
                    "difficulty": max(1, min(5, int(it.get("difficulty", 3)))),
                    "question": it.get("question", ""),
                    "choices": ch, "answer": a,
                    "explanation": it.get("explanation", ""),
                    "concepts": [k for k in it.get("concepts", []) if k in ck][:2],
                })
            if len(items) < 6:
                print(f"  {c['id']} 시도 {attempt}: 유효 문항 부족({len(items)})")
                continue
            with open(os.path.join(DEST, c["id"] + ".json"), "w",
                      encoding="utf-8") as f:
                json.dump({"course": c["id"], "title": c["title"],
                           "count": len(items), "items": items},
                          f, ensure_ascii=False, indent=1)
            made += 1
            dist = {}
            for it in items:
                dist[it["difficulty"]] = dist.get(it["difficulty"], 0) + 1
            print(f"  {c['id']:<20} {len(items):>2}문항 · 난이도 분포 "
                  + " ".join(f"{k}:{v}" for k, v in sorted(dist.items()))
                  + (f" · 길이편향 {biased_n}" if biased_n else ""))
            break
    done = len([f for f in os.listdir(DEST) if f.endswith(".json")])
    print(f"출제 {made}과목 · 누적 {done}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
