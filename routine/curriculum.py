#!/usr/bin/env python3
"""기초 학습 커리큘럼 설계 (Claude Code 헤드리스, 구독).

연구 노트의 용어 104개는 전부 이 연구 고유의 것이라 그 아래 단계가 비어 있다.
딥러닝·LLM 기초를 단계별로 설계해 연구 용어로 이어 붙인다.

산출물 curriculum/foundations.json 은 **레포에 커밋되는 사람이 고치는 파일**이다.
한 번 만들고 나면 --force 없이는 다시 만들지 않는다.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common import load, read  # noqa: E402
from generate import call_claude, extract_json, log_usage  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.join(ROOT, "curriculum", "foundations.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-sonnet-5")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    if os.path.exists(DEST) and not args.force:
        d = json.load(open(DEST, encoding="utf-8"))
        n = sum(len(s["concepts"]) for s in d["stages"])
        print(f"이미 있음: {len(d['stages'])}단계 {n}개 (--force 로 재설계)")
        return 0

    notes = load("notes.json")
    repo_keys = [c["key"] for c in notes["concepts"]]
    prompt = read(os.path.join(ROOT, "prompts", "curriculum.md")).replace(
        "{REPO_KEYS}", ", ".join(repo_keys))

    for attempt in (1, 2):
        res, err = call_claude(prompt, args.model, timeout=600)
        log_usage("curriculum", res)
        if err:
            print(f"  시도 {attempt}: {err}")
            continue
        obj = extract_json(res.get("result", ""))
        if not obj or "stages" not in obj:
            print(f"  시도 {attempt}: JSON 실패")
            continue

        # 검증·정리: 연구 용어와 겹치면 버리고, 링크는 실재하는 키로만
        repo = set(repo_keys)
        seen = set()
        stages = []
        for st in sorted(obj["stages"], key=lambda x: x.get("stage", 0)):
            keep = []
            for c in st.get("concepts", []):
                k = (c.get("key") or "").strip().lower()
                if not k or k in seen or k in repo:
                    continue
                seen.add(k)
                c["key"] = k
                c["prerequisites"] = [p for p in c.get("prerequisites", [])
                                      if p in seen and p != k][:2]
                c["leads_to"] = [p for p in c.get("leads_to", []) if p in repo][:3]
                c["stage"] = st.get("stage", 0)
                keep.append(c)
            if keep:
                stages.append({"stage": st.get("stage", 0),
                               "title": st.get("title", ""),
                               "goal": st.get("goal", ""), "concepts": keep})
        total = sum(len(s["concepts"]) for s in stages)
        if total < 15:
            print(f"  시도 {attempt}: 개념이 너무 적음({total})")
            continue

        os.makedirs(os.path.dirname(DEST), exist_ok=True)
        with open(DEST, "w", encoding="utf-8") as f:
            json.dump({"stages": stages, "count": total}, f,
                      ensure_ascii=False, indent=1)
        print(f"커리큘럼 {len(stages)}단계 {total}개 -> {DEST}")
        for st in stages:
            names = ", ".join(c["name"] for c in st["concepts"])
            print(f"  {st['stage']}. {st['title']}  ({len(st['concepts'])})")
            print(f"     {names[:100]}")
        return 0
    print("커리큘럼 설계 실패")
    return 1


if __name__ == "__main__":
    sys.exit(main())
