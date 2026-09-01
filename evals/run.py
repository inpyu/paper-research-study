#!/usr/bin/env python3
"""정답셋 대조 — 파서를 고칠 때마다 돌린다.

concepts.golden.md 의 체크박스를 읽어 점수를 낸다.
  1절 [x]/[~] = 맞는 개념, [ ] = 오탐        -> 정밀도
  2절 손으로 적은 빠진 개념                   -> 재현율
  3절 G3 상위 [x] = 진짜 갭                   -> G3 유용성 (목표 7/10)
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "routine"))
from common import norm  # noqa: E402

GOLDEN = os.path.join(ROOT, "evals", "concepts.golden.md")
ITEM = re.compile(r"^- \[([ x~])\]\s*(.+?)\s*$")
SEC = re.compile(r"^## (\d)\.")


def parse_golden():
    secs = {1: [], 2: [], 3: []}
    cur = None
    for line in open(GOLDEN, encoding="utf-8"):
        m = SEC.match(line)
        if m:
            cur = int(m.group(1))
            continue
        m = ITEM.match(line)
        if m and cur:
            secs[cur].append((m.group(1), m.group(2)))
    return secs


def main():
    if not os.path.exists(GOLDEN):
        print("정답셋 없음"); return 1
    secs = parse_golden()
    notes = json.load(open(os.path.join(ROOT, "out", "notes.json"), encoding="utf-8"))
    gaps = json.load(open(os.path.join(ROOT, "out", "gaps.json"), encoding="utf-8"))
    extracted = {c["key"] for c in notes["concepts"]}

    s1 = secs[1]
    marked = [x for x in s1 if x[0] in "x~"]
    unmarked_all = all(x[0] == " " for x in s1)
    print(f"1절 개념 {len(s1)}개")
    if unmarked_all:
        print("   → 아직 채점 전 (전부 미표시). 표시하면 정밀도가 계산된다.")
        prec = None
    else:
        prec = len(marked) / len(s1) if s1 else 0
        print(f"   정밀도 {prec:.2f}  (맞음 {len(marked)} / 전체 {len(s1)})")
        for f, n in s1:
            if f == " ":
                print(f"     오탐: {n}")

    s2 = [n for _, n in secs[2] if n and not n.startswith("(")]
    if s2:
        hit = sum(1 for n in s2 if norm(n) in extracted)
        print(f"2절 빠진 개념 {len(s2)}개 중 {hit}개는 사실 추출되어 있음")
        rec = (len(marked) / (len(marked) + len(s2) - hit)) if marked else None
        if rec is not None:
            print(f"   재현율 {rec:.2f}")
        for n in s2:
            if norm(n) not in extracted:
                print(f"     미추출: {n}")
    else:
        print("2절 비어 있음 — 재현율 미측정")

    s3 = secs[3]
    real = [n for f, n in s3 if f == "x"]
    print(f"3절 G3 상위 {len(s3)}개 중 진짜 갭 {len(real)}개")
    if s3 and all(f == " " for f, _ in s3):
        print("   → 아직 채점 전")
    else:
        verdict = "통과" if len(real) >= 7 else "미달 — G3 점수식 보정 필요"
        print(f"   M1 완료 기준(7개 이상): {verdict}")

    print(f"\n현재 파서 상태: 개념 {len(extracted)} · "
          f"G3 {gaps['summary']['G3']} · G4 {gaps['summary']['G4']}"
          f"/{gaps['summary']['src_files']} · G5 {gaps['summary']['G5']}"
          f"/{gaps['summary']['flags']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
