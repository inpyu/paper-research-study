#!/usr/bin/env python3
"""열린 질문 (위키 W7) — LLM 미사용.

코드의 TODO/FIXME, 노트의 미결 표현, 결론 보류된 실험을 한 목록으로 모은다.
출력: out/questions.json
"""
import re
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common import CODE_DIRS, CODE_EXT, NOTE_DIR, dump, load, read, walk  # noqa: E402

CODE_MARK = re.compile(r"\b(TODO|FIXME|XXX|HACK|WIP)\b[: ]?\s*(.*)", re.I)
NOTE_MARK = re.compile(
    r"(확인\s*필요|검증\s*필요|미해결|아직\s*모른다|불명|보류|재측정\s*필요|"
    r"TBD|의문|숙제|추후|남은\s*과제|왜\s*그런지)")
NOISE = re.compile(r"^\s*[-*]?\s*$")


def main():
    items = []

    for d in CODE_DIRS:
        for rel, full in walk(d, CODE_EXT):
            try:
                lines = read(full).split("\n")
            except OSError:
                continue
            for i, line in enumerate(lines, 1):
                if "//" not in line and "#" not in line:
                    continue
                m = CODE_MARK.search(line)
                if m:
                    body = m.group(2).strip() or line.strip()
                    items.append({"kind": "code", "mark": m.group(1).upper(),
                                  "where": rel, "line": i, "text": body[:180]})

    for rel, full in walk(NOTE_DIR, (".md",)):
        try:
            lines = read(full).split("\n")
        except OSError:
            continue
        for i, line in enumerate(lines, 1):
            if NOISE.match(line) or line.startswith("|"):
                continue
            m = NOTE_MARK.search(line)
            if m:
                items.append({"kind": "note", "mark": m.group(1),
                              "where": rel.replace("research/", ""), "line": i,
                              "text": re.sub(r"\s+", " ", line).strip()[:200]})

    try:
        art = load("artifacts.json")
        for r in art["runs"]:
            if "inconclusive" in r["run_id"]:
                items.append({"kind": "run", "mark": "inconclusive",
                              "where": f"artifacts/{r['run_id']}", "line": None,
                              "text": "결론 보류된 실험 — 재측정 대상"})
            for e in r.get("errors", [])[:2]:
                items.append({"kind": "run", "mark": "error",
                              "where": f"artifacts/{r['run_id']}/raw/{e['file']}",
                              "line": None, "text": e["line"][:180]})
    except FileNotFoundError:
        pass

    by_kind = {}
    for x in items:
        by_kind[x["kind"]] = by_kind.get(x["kind"], 0) + 1
    dump("questions.json", {"count": len(items), "by_kind": by_kind,
                            "items": items[:500]})
    print(f"열린 질문 {len(items)}건  {by_kind}")
    for x in items[:8]:
        loc = f"{x['where']}:{x['line']}" if x["line"] else x["where"]
        print(f"  [{x['mark']:<12}] {loc:<42} {x['text'][:60]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
