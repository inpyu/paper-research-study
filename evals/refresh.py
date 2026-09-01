#!/usr/bin/env python3
"""현재 파서 결과로 정답셋 템플릿을 갱신한다.

이미 표시한 체크는 보존한다 — 다시 채점하지 않아도 되게.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLDEN = os.path.join(ROOT, "evals", "concepts.golden.md")
ITEM = re.compile(r"^- \[([ x~])\]\s*(?:\d+\.\s*)?(.+?)(?:\s*\(.*\))?\s*$")

prev = {}
free = []
if os.path.exists(GOLDEN):
    sec = 0
    for line in open(GOLDEN, encoding="utf-8"):
        m = re.match(r"^## (\d)\.", line)
        if m:
            sec = int(m.group(1)); continue
        m = ITEM.match(line)
        if m:
            prev[m.group(2)] = m.group(1)
            if sec == 2 and not m.group(2).startswith("("):
                free.append((m.group(1), m.group(2)))

notes = json.load(open(os.path.join(ROOT, "out", "notes.json"), encoding="utf-8"))
gaps = json.load(open(os.path.join(ROOT, "out", "gaps.json"), encoding="utf-8"))
L = ["""# evals/concepts.golden.md — 개념 정답셋

파서 품질의 기준선. **손으로 채운다.** 파서나 점수식을 고칠 때마다 `python3 evals/run.py` 로 대조한다.

## 1. 파서가 뽑은 개념 (자동 갱신)
`[x]` 맞음 · `[~]` 이름이 어색함 · `[ ]` 개념이 아님(오탐)
"""]
for c in notes["concepts"]:
    L.append(f"- [{prev.get(c['name'], ' ')}] {c['name']}")
L.append("""
## 2. 빠진 개념 (손으로 추가)
내가 아는데 위 목록에 없는 개념을 적는다. 재현율의 기준.
""")
L += [f"- [{f}] {n}" for f, n in free] or ["- [ ] (예: chunked prefill)"]
L.append("""
## 3. G3 상위 10개 판정
`[x]` 실제로 내가 설명 못 함(진짜 갭) · `[ ]` 사실 알고 있음(오탐)
""")
for i, x in enumerate(gaps["G3"][:10], 1):
    L.append(f"- [{prev.get(x['term'], ' ')}] {i}. {x['term']}  "
             f"(문서 {x['doc_count']}개, 강조 {x['emph']}회)")
L.append("""
> **완료 기준**: 3절에서 `[x]`가 7개 이상이면 M1 통과.
""")
open(GOLDEN, "w", encoding="utf-8").write("\n".join(L))
print(f"갱신: 개념 {len(notes['concepts'])}개 · G3 상위 10개 · 기존 체크 {len(prev)}개 보존")
