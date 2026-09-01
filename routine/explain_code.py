#!/usr/bin/env python3
"""파일·함수 설명 생성 (Claude Code 헤드리스, 구독).

"코드 구조를 파일 하나하나, 함수 하나하나 설명" 이 목표.
파일 내용이 바뀌면(해시가 달라지면) 다시 만든다.
출력: out/codedoc/<경로를 _ 로 바꾼 이름>.json
"""
import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common import OUT, REPO, load, read  # noqa: E402
from generate import call_claude, extract_json, log_usage  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.join(OUT, "codedoc")
MAX_SRC = 14000            # 프롬프트에 넣을 소스 상한


def slug(path):
    return path.replace("/", "_").replace(".", "-")


def build(path, syms, churn, refs):
    full = os.path.join(REPO, path)
    src = read(full)
    lines = src.split("\n")
    body = src if len(src) <= MAX_SRC else (
        "\n".join(lines[:250]) + "\n\n… (중략) …\n\n" + "\n".join(lines[-120:]))
    fl = "\n".join(f"- {s['name']}  ({s['line']}~{s.get('line_end', '?')})"
                   for s in syms[:40])
    return (f"경로: {path}\n줄수: {len(lines)}\n"
            f"git 변경 {churn}회 · 다른 코드에서 참조 {refs}회\n\n"
            f"### 함수·타입 목록\n{fl or '(없음)'}\n\n"
            f"### 소스\n```cpp\n{body}\n```")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-sonnet-5")
    ap.add_argument("--limit", type=int, default=6)
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    code = load("code.json")
    os.makedirs(DEST, exist_ok=True)
    tpl = read(os.path.join(ROOT, "prompts", "codefile.md"))

    by_file = {}
    for s in code["symbols"]:
        by_file.setdefault(s["file"], []).append(s)

    # upstream 덩어리와 테스트는 뒤로 민다. 참조·변경 많은 것부터.
    cand = [f for f in code["files"]
            if f["path"].startswith("src/")
            and f["path"] not in ("src/json.hpp",)
            and "/llamafile/" not in f["path"]]
    cand.sort(key=lambda f: -(f["churn"] * 3 + f.get("in_refs", 0)))

    todo = []
    for f in cand:
        p = os.path.join(DEST, slug(f["path"]) + ".json")
        h = hashlib.sha256(
            read(os.path.join(REPO, f["path"])).encode()).hexdigest()[:12]
        if os.path.exists(p):
            try:
                if json.load(open(p, encoding="utf-8")).get("_sig") == h:
                    continue
            except Exception:
                pass
        todo.append((f, h))
    if not args.all:
        todo = todo[:args.limit]
    if not todo:
        print("생성할 파일 없음 — 전부 최신")
        return 0

    made = 0
    for f, h in todo:
        syms = sorted(by_file.get(f["path"], []), key=lambda s: s["line"])
        prompt = tpl.replace("{FILE}", build(f["path"], syms, f["churn"],
                                             f.get("in_refs", 0)))
        for attempt in (1, 2):
            res, err = call_claude(prompt, args.model, timeout=420)
            log_usage("codefile", res)
            if err:
                print(f"  {f['path']} 시도 {attempt}: {err}")
                continue
            obj = extract_json(res.get("result", ""))
            if not obj or "role" not in obj:
                print(f"  {f['path']} 시도 {attempt}: JSON 실패")
                continue
            known = {s["name"] for s in syms}
            byname = {s["name"]: s for s in syms}
            fns = []
            for fn in obj.get("functions", []):
                if fn.get("name") in known:
                    s = byname[fn["name"]]
                    fns.append({**fn, "line": s["line"],
                                "line_end": s.get("line_end")})
            obj["functions"] = fns
            obj["file"] = f["path"]
            obj["_sig"] = h
            obj["loc"] = f["loc"]
            obj["churn"] = f["churn"]
            obj["in_refs"] = f.get("in_refs", 0)
            obj["symbol_count"] = len(syms)
            with open(os.path.join(DEST, slug(f["path"]) + ".json"), "w",
                      encoding="utf-8") as fh:
                json.dump(obj, fh, ensure_ascii=False, indent=1)
            made += 1
            print(f"  {f['path']:<34} 함수 {len(fns):>2}개  {obj['role'][:44]}")
            break
    done = len([x for x in os.listdir(DEST) if x.endswith(".json")])
    print(f"파일 설명 {made}개 생성 · 누적 {done}/{len(cand)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
