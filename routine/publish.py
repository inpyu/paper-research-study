#!/usr/bin/env python3
"""변경이 있을 때만 commit & push. 검증에 걸리면 push 하지 않는다."""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "site", "public", "data")


def sh(*a, **kw):
    return subprocess.run(a, cwd=ROOT, capture_output=True, text=True, **kw)


def verify():
    """깨진 데이터가 배포되는 경로를 만들지 않는다."""
    man = os.path.join(DATA, "manifest.json")
    if not os.path.exists(man):
        return "manifest.json 없음"
    m = json.load(open(man, encoding="utf-8"))
    for rel in m["files"]:
        p = os.path.join(DATA, rel)
        if not os.path.exists(p):
            return f"누락: {rel}"
        try:
            json.load(open(p, encoding="utf-8"))
        except Exception as e:
            return f"JSON 깨짐 {rel}: {e}"
    s = m["summary"]
    if s["concepts_defined"] < 50:
        return f"개념이 비정상적으로 적음({s['concepts_defined']}) — 파서 회귀 의심"
    return None


def main():
    err = verify()
    if err:
        print(f"검증 실패 — push 하지 않음: {err}")
        return 1
    if not sh("git", "status", "--porcelain", "site/public/data").stdout.strip():
        print("변경 없음 — push 생략")
        return 0
    m = json.load(open(os.path.join(DATA, "manifest.json"), encoding="utf-8"))
    s = m["summary"]
    msg = (f"data: {m['generated_at'][:10]} "
           f"(개념 {s['concepts_defined']}, G3 {s['G3']}, G5 {s['G5']}/{s['flags']})")
    sh("git", "add", "site/public/data")
    r = sh("git", "commit", "-m", msg)
    if r.returncode:
        print("commit 실패:", r.stderr.strip()[:200])
        return 1
    r = sh("git", "push", "origin", "HEAD")
    if r.returncode:
        print("push 실패:", r.stderr.strip()[:200])
        return 1
    print("배포:", msg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
