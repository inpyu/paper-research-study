#!/usr/bin/env python3
"""개념 설명 생성 (Claude Code 헤드리스, 구독).

사이트의 본체는 갭 수치가 아니라 **설명**이다. 이 스크립트가 그걸 만든다.
이미 만든 개념은 건너뛴다(입력 해시가 같으면 재생성하지 않는다).
출력: out/explain/<key>.json
"""
import argparse
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common import NOTE_DIR, OUT, dump, load, read, walk  # noqa: E402
from generate import call_claude, extract_json, log_usage  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.join(OUT, "explain")
HEAD = re.compile(r"^(#{1,6})\s")


def excerpt(lines, start, level, limit=2200):
    """정의 헤딩부터 같은/상위 레벨 헤딩 직전까지."""
    out = []
    for i in range(start, len(lines)):
        m = HEAD.match(lines[i])
        if m and i > start - 1 and len(m.group(1)) <= level and i != start - 1:
            break
        out.append(lines[i])
        if sum(len(x) for x in out) > limit:
            break
    return "\n".join(out)[:limit]


def build_items(notes, keys):
    docs = {}
    for rel, full in walk(NOTE_DIR, (".md",)):
        docs[rel] = read(full).split("\n")
    by_key = {c["key"]: c for c in notes["concepts"]}
    links = {}
    for l in notes["links"]:
        links.setdefault(l["from"], []).append(l["to_text"])
    items = []
    for k in keys:
        c = by_key.get(k)
        if not c:
            continue
        exs = []
        for d in c["defs"][:2]:
            lines = docs.get(d["doc"])
            if lines:
                exs.append(f"[{d['doc']}:{d['line']}]\n"
                           + excerpt(lines, d["line"], d["level"]))
        items.append({"key": k, "name": c["name"], "aliases": c["aliases"],
                      "linked": links.get(k, [])[:4],
                      "excerpt": "\n\n".join(exs)})
    return items


def render(items, vocab):
    tpl = read(os.path.join(ROOT, "prompts", "concept.md"))
    blocks = []
    for it in items:
        b = [f"### key: {it['key']}", f"이름: {it['name']}"]
        if it["aliases"]:
            b.append(f"별칭: {', '.join(it['aliases'])}")
        if it["linked"]:
            b.append(f"노트가 연결한 개념: {', '.join(it['linked'])}")
        b.append("노트 발췌:\n" + (it["excerpt"] or "(없음 — 노트에 본문이 없다)"))
        blocks.append("\n".join(b))
    return (tpl.replace("{VOCAB}", ", ".join(vocab))
               .replace("{ITEMS}", "\n\n".join(blocks)))


def sig(it):
    return hashlib.sha256(
        (it["key"] + it["excerpt"]).encode("utf-8")).hexdigest()[:12]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-sonnet-5")
    ap.add_argument("--batch", type=int, default=6)
    ap.add_argument("--limit", type=int, default=12, help="이번 실행에서 만들 개수")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    notes = load("notes.json")
    os.makedirs(DEST, exist_ok=True)
    vocab = [c["key"] for c in notes["concepts"]]

    todo = []
    for c in notes["concepts"]:
        p = os.path.join(DEST, c["key"].replace(" ", "_") + ".json")
        if os.path.exists(p):
            try:
                if json.load(open(p, encoding="utf-8")).get("_sig"):
                    continue
            except Exception:
                pass
        todo.append(c["key"])
    if not args.all:
        todo = todo[:args.limit]
    if not todo:
        print("생성할 개념 없음 — 전부 최신")
        return 0

    items = build_items(notes, todo)
    made = 0
    for i in range(0, len(items), args.batch):
        chunk = items[i:i + args.batch]
        prompt = render(chunk, vocab)
        ok = False
        for attempt in (1, 2):
            res, err = call_claude(prompt, args.model, timeout=420)
            log_usage("concept", res)
            if err:
                print(f"  배치 {i//args.batch+1} 시도 {attempt}: {err}")
                continue
            obj = extract_json(res.get("result", ""))
            if not obj or "concepts" not in obj:
                print(f"  배치 {i//args.batch+1} 시도 {attempt}: JSON 실패")
                continue
            known = {it["key"] for it in chunk}
            wrote = 0
            for c in obj["concepts"]:
                if c.get("key") not in known:
                    continue
                src = next(x for x in chunk if x["key"] == c["key"])
                c["prerequisites"] = [k for k in c.get("prerequisites", [])
                                      if k in vocab and k != c["key"]][:3]
                c["related"] = [k for k in c.get("related", [])
                                if k in vocab and k != c["key"]][:3]
                c["_sig"] = sig(src)
                c["name"] = src["name"]
                with open(os.path.join(DEST, c["key"].replace(" ", "_") + ".json"),
                          "w", encoding="utf-8") as f:
                    json.dump(c, f, ensure_ascii=False, indent=1)
                wrote += 1
            if wrote:
                ok = True
                made += wrote
                print(f"  배치 {i//args.batch+1}: {wrote}개 생성 "
                      f"({', '.join(c['key'] for c in obj['concepts'][:3])}…)")
                break
        if not ok:
            print(f"  배치 {i//args.batch+1}: 실패 — 건너뜀(다음 실행에서 재시도)")
    done = len([f for f in os.listdir(DEST) if f.endswith(".json")])
    print(f"개념 설명 {made}개 생성 · 누적 {done}/{len(notes['concepts'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
