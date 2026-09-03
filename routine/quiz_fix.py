#!/usr/bin/env python3
"""문항 품질 교정 — 길이로 정답을 찍을 수 있는 문항을 고친다.

출제 프롬프트에 "보기 길이를 맞춰라"라고 써도 지켜지지 않았다(280문항 중 123개).
규칙은 프롬프트가 아니라 검사로 강제해야 한다.
고친 결과가 여전히 편향이면 원본을 유지한다 — 절대 나빠지지 않게.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common import OUT, read  # noqa: E402
from generate import call_claude, extract_json, log_usage  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.join(OUT, "quiz")


def biased(item):
    """정답 보기만 유독 긴가. 짧은 보기끼리는 문제 삼지 않는다."""
    L = [len(c) for c in item["choices"]]
    m, second = max(L), sorted(L)[-2]
    return L[item["answer"]] == m and m >= 20 and m > second * 1.45


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-sonnet-5")
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--limit", type=int, default=200)
    args = ap.parse_args()

    tpl = read(os.path.join(ROOT, "prompts", "quiz_fix.md"))
    files = sorted(f for f in os.listdir(DEST) if f.endswith(".json"))
    banks = {f: json.load(open(os.path.join(DEST, f), encoding="utf-8"))
             for f in files}
    todo = [(f, it) for f, b in banks.items() for it in b["items"] if biased(it)]
    todo = todo[:args.limit]
    if not todo:
        print("길이 편향 문항 없음")
        return 0
    print(f"교정 대상 {len(todo)}문항")

    fixed = 0
    for i in range(0, len(todo), args.batch):
        chunk = todo[i:i + args.batch]
        blocks = []
        for _, it in chunk:
            ch = "\n".join(f'  [{j}] {c}' for j, c in enumerate(it["choices"]))
            blocks.append(f"### id: {it['id']}\n문제: {it['question']}\n"
                          f"보기:\n{ch}\n정답 인덱스: {it['answer']}\n"
                          f"해설: {it['explanation']}")
        prompt = tpl.replace("{ITEMS}", "\n\n".join(blocks))
        obj = None
        for attempt in (1, 2):
            res, err = call_claude(prompt, args.model, timeout=600)
            log_usage("quiz_fix", res)
            if err:
                print(f"  배치 {i//args.batch+1} 시도 {attempt}: {err}")
                continue
            obj = extract_json(res.get("result", ""))
            if obj and "items" in obj:
                break
            print(f"  배치 {i//args.batch+1} 시도 {attempt}: JSON 실패")
            obj = None
        if obj is None:
            continue
        got = {x.get("id"): x for x in obj["items"]}
        for fname, it in chunk:
            g = got.get(it["id"])
            if not g:
                continue
            ch, a = g.get("choices"), g.get("answer")
            if not ch or len(ch) != 4 or a != it["answer"]:
                continue                       # 정답 위치가 바뀌면 버린다
            if len({c.strip() for c in ch}) != 4:
                continue
            cand = {**it, "choices": ch,
                    "explanation": g.get("explanation") or it["explanation"]}
            if biased(cand):
                continue                       # 나아지지 않았으면 원본 유지
            for k, x in enumerate(banks[fname]["items"]):
                if x["id"] == it["id"]:
                    banks[fname]["items"][k] = cand
                    fixed += 1
                    break
        print(f"  배치 {i//args.batch+1}: 누적 {fixed}개 교정")

    for f, b in banks.items():
        with open(os.path.join(DEST, f), "w", encoding="utf-8") as fh:
            json.dump(b, fh, ensure_ascii=False, indent=1)
    left = sum(1 for b in banks.values() for it in b["items"] if biased(it))
    total = sum(len(b["items"]) for b in banks.values())
    print(f"교정 {fixed}개 · 남은 편향 {left}/{total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
