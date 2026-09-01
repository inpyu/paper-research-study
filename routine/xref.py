#!/usr/bin/env python3
"""용어 역인덱스 (위키 W8) — LLM 미사용.

용어 하나에 대해 노트 · 코드 심볼 · 로그 템플릿 · 실험 run-id · 논문을
한 번에 보여준다. 개념 페이지와 위키를 잇는 접착제.
출력: out/xref.json
"""
import re
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common import NOTE_DIR, dump, load, norm, read, walk  # noqa: E402


def main():
    notes = load("notes.json")
    code = load("code.json")
    gaps = load("gaps.json")
    try:
        logs = load("logs.json")["items"]
    except FileNotFoundError:
        logs = []
    try:
        arts = load("artifacts.json")["runs"]
    except FileNotFoundError:
        arts = []

    blobs = {rel.replace("research/", ""): read(full)
             for rel, full in walk(NOTE_DIR, (".md",))}
    sym_by_norm = {}
    for s in code["symbols"]:
        sym_by_norm.setdefault(norm(s["name"]), []).append(s)

    # 대상: 정의된 개념 + G3 상위 60개 (내가 모르는 것도 역인덱스가 필요하다)
    targets = [{"term": c["name"], "key": c["key"], "defined": True}
               for c in notes["concepts"]]
    seen = {t["key"] for t in targets}
    for g in gaps["G3"][:60]:
        if g["key"] not in seen:
            targets.append({"term": g["term"], "key": g["key"], "defined": False})
            seen.add(g["key"])

    out = []
    for t in targets:
        term = t["term"]
        pat = re.compile(r"(?<![\w-])" + re.escape(term) + r"(?![\w-])", re.I)
        docs = [{"doc": d, "hits": len(pat.findall(txt))}
                for d, txt in blobs.items() if pat.search(txt)]
        docs.sort(key=lambda x: -x["hits"])
        syms = [{"name": s["name"], "file": s["file"], "line": s["line"]}
                for s in sym_by_norm.get(t["key"], [])][:6]
        lg = [{"template": x["template"][:90], "count": x["count"]}
              for x in logs if pat.search(x["template"])][:4]
        runs = [r["run_id"] for r in arts
                if any(pat.search(f) for f in r.get("flags", []))
                or pat.search(r["run_id"])][:5]
        papers = [{"id": pid, "title": p.get("note_title", "")[:70]}
                  for pid, p in notes["papers"].items()
                  if pat.search(p.get("note_title", ""))][:4]
        total = len(docs) + len(syms) + len(lg) + len(runs) + len(papers)
        if total == 0:
            continue
        out.append({"term": term, "key": t["key"], "defined": t["defined"],
                    "doc_count": len(docs), "docs": docs[:8], "symbols": syms, "logs": lg,
                    "runs": runs, "papers": papers, "reach": total})
    out.sort(key=lambda x: -x["reach"])

    spans = sum(1 for x in out if x["docs"] and x["symbols"])
    dump("xref.json", {"count": len(out), "both_note_and_code": spans, "items": out})
    print(f"역인덱스 {len(out)}개 용어")
    print(f"  노트와 코드 양쪽에 나타나는 용어 {spans}개")
    for x in out[:8]:
        print(f"  {x['term']:<26} 노트 {x['doc_count']:>2} · 심볼 {len(x['symbols'])} · "
              f"로그 {len(x['logs'])} · 실험 {len(x['runs'])} · 논문 {len(x['papers'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
