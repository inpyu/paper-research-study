#!/usr/bin/env python3
"""로그 사전 (위키 W5) — LLM 미사용.

로그를 읽을 줄 아는 것이 이 연구의 실전 능력이다. 그런데 어느 문서도
로그 라인의 의미를 설명하지 않는다. 반복 패턴을 뽑아 사전을 만든다.

  1) 로그 라인을 템플릿으로 정규화 (숫자·경로·주소를 자리표시자로)
  2) 빈도 순으로 묶고
  3) 그 문자열을 출력하는 코드 위치를 찾아 붙인다
출력: out/logs.json
"""
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common import CODE_DIRS, NOTE_DIR, REPO, dump, read, walk  # noqa: E402

NUM = re.compile(r"\d+(?:\.\d+)?")
IP = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}(?::\d+)?\b")
PATH = re.compile(r"(?:/[\w.-]+){2,}")
HEX = re.compile(r"\b0x[0-9a-fA-F]+\b")
WS = re.compile(r"[ \t]+")
ERRORISH = re.compile(r"(🚨|critical|error|fail|abort|timeout|closed|retry)", re.I)
# printf/fprintf/cout 등에 박힌 문자열 리터럴
LITERAL = re.compile(r'"((?:[^"\\]|\\.){6,120})"')


def templatize(line):
    t = IP.sub("<ADDR>", line)
    t = PATH.sub("<PATH>", t)
    t = HEX.sub("<HEX>", t)
    t = NUM.sub("<N>", t)
    return WS.sub(" ", t).strip()


def anchor(template):
    """템플릿에서 코드 검색에 쓸 가장 긴 고정 문자열 조각."""
    parts = re.split(r"<[A-Z]+>", template)
    parts = [re.sub(r"[^\w가-힣 :/.\-]", "", p).strip() for p in parts]
    parts = [p for p in parts if len(p) >= 6]
    return max(parts, key=len) if parts else None


def main():
    art = os.path.join(REPO, "artifacts")
    templates = defaultdict(lambda: {"count": 0, "runs": set(),
                                     "examples": [], "files": set()})
    total = 0
    if os.path.isdir(art):
        for rid in sorted(os.listdir(art)):
            rawd = os.path.join(art, rid, "raw")
            if not os.path.isdir(rawd):
                continue
            for fn in sorted(os.listdir(rawd)):
                if not fn.endswith((".log", ".txt")):
                    continue
                try:
                    text = read(os.path.join(rawd, fn))
                except OSError:
                    continue
                for line in text.split("\n"):
                    line = line.rstrip()
                    if not line.strip() or len(line) > 400:
                        continue
                    total += 1
                    t = templatize(line)
                    if len(t) < 8:
                        continue
                    e = templates[t]
                    e["count"] += 1
                    e["runs"].add(rid)
                    e["files"].add(fn)
                    if len(e["examples"]) < 3 and line not in e["examples"]:
                        e["examples"].append(line)

    # 코드에서 출력 지점 찾기
    code_lines = []
    for d in CODE_DIRS:
        for rel, full in walk(d, (".cpp", ".hpp", ".c", ".h", ".py", ".sh")):
            try:
                for i, line in enumerate(read(full).split("\n"), 1):
                    if '"' in line and len(line) < 400:
                        code_lines.append((rel, i, line))
            except OSError:
                pass

    notes_text = {rel: read(full) for rel, full in walk(NOTE_DIR, (".md",))}

    items = []
    for t, e in templates.items():
        if e["count"] < 2 and len(e["runs"]) < 2:
            continue
        a = anchor(t)
        origin = None
        if a:
            key = a[:40]
            for rel, i, line in code_lines:
                if key in line:
                    origin = {"file": rel, "line": i}
                    break
        docs = []
        if a:
            probe = a[:24]
            docs = sorted(rel.replace("research/", "")
                          for rel, txt in notes_text.items() if probe in txt)
        items.append({
            "template": t[:200], "count": e["count"],
            "runs": sorted(e["runs"])[:6], "run_count": len(e["runs"]),
            "example": e["examples"][0][:200] if e["examples"] else "",
            "origin": origin, "notes": docs[:3],
            "is_error": bool(ERRORISH.search(t)),
        })
    items.sort(key=lambda x: (-x["run_count"], -x["count"]))

    documented = sum(1 for x in items if x["notes"])
    located = sum(1 for x in items if x["origin"])
    dump("logs.json", {"total_lines": total, "count": len(items),
                       "documented": documented, "located": located,
                       "items": items[:300]})
    print(f"로그 라인 {total:,}개 -> 템플릿 {len(items)}종")
    print(f"  코드 출력 지점을 찾은 것 {located}/{len(items)}")
    print(f"  노트가 설명하는 것       {documented}/{len(items)}  ← W5 갭")
    for x in items[:10]:
        mark = "⚠" if x["is_error"] else " "
        loc = f"{x['origin']['file'].replace('src/','')}:{x['origin']['line']}" \
            if x["origin"] else "출처 미상"
        print(f"  {mark} run {x['run_count']:>2} · {x['count']:>4}회  "
              f"{x['template'][:52]:<52} {loc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
