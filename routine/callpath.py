#!/usr/bin/env python3
"""실행 경로 추적 (위키 W2) — LLM 미사용.

"프롬프트 하나를 넣으면 무슨 일이 일어나는가"를 호출 그래프로 편다.
각 단계에 노트의 어느 문서가 그 함수를 언급하는지 붙인다.
출력: out/trace.json  (모듈명은 callpath — 표준 라이브러리 trace 와 충돌 방지)
"""
import sys
from collections import defaultdict, deque

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common import NOTE_DIR, dump, load, read, walk  # noqa: E402

# 진입점 — 이 레포에서 의미 있는 흐름의 출발점
ENTRIES = [
    ("src/dllama.cpp", "inference", "prefill/decode 본 루프"),
    ("src/dllama.cpp", "inferenceContinuousBatching", "연속 배칭 경로"),
    ("src/app.cpp", "runWorkerApp", "워커 노드 루프"),
]
# upstream/보일러플레이트 — 경로에서 제외한다
EXCLUDE = ("src/json.hpp", "src/nn/pthread.h")
EXCLUDE_DIR = ("src/nn/llamafile/",)
NOISE = {"size", "data", "get", "end", "begin", "push_back", "create", "at",
         "clear", "empty", "reset", "close", "open", "read", "write", "printf",
         "assert", "min", "max", "abs", "to_string", "c_str", "length"}
MAX_DEPTH = 4
MAX_FANOUT = 8


def keep(file):
    return (file not in EXCLUDE and not file.startswith(EXCLUDE_DIR)
            and file.startswith(("src/", "prefill_bench/")))


def main():
    code = load("code.json")
    notes_text = {rel: read(full) for rel, full in walk(NOTE_DIR, (".md",))}

    out_edges = defaultdict(list)
    for e in code["calls"]:
        if keep(e["from_file"]) and keep(e["to_file"]) and e["to"] not in NOISE:
            out_edges[(e["from_file"], e["from"])].append(e)

    span = {(s["file"], s["name"]): s for s in code["symbols"]}
    weight = defaultdict(int)
    for e in code["calls"]:
        weight[(e["to_file"], e["to"])] += 1

    traces = []
    for efile, ename, label in ENTRIES:
        if (efile, ename) not in span:
            continue
        nodes, edges, seen = {}, [], set()
        q = deque([((efile, ename), 0)])
        seen.add((efile, ename))
        while q:
            key, depth = q.popleft()
            s = span.get(key)
            if s is None:
                continue
            docs = sorted(d for d, t in notes_text.items() if s["name"] in t)
            nodes[f"{key[0]}#{key[1]}"] = {
                "file": key[0], "name": key[1], "depth": depth,
                "line": s["line"], "line_end": s.get("line_end"),
                "refs": weight.get(key, 0),
                "notes": [d.replace("research/", "") for d in docs][:4],
            }
            if depth >= MAX_DEPTH:
                continue
            # 같은 함수를 여러 번 부르면 한 번만, 참조 많은 순으로 상위 N개
            uniq = {}
            for e in out_edges.get(key, []):
                uniq.setdefault((e["to_file"], e["to"]), e)
            ranked = sorted(uniq.items(),
                            key=lambda kv: -weight.get(kv[0], 0))[:MAX_FANOUT]
            for tgt, e in ranked:
                edges.append({"from": f"{key[0]}#{key[1]}",
                              "to": f"{tgt[0]}#{tgt[1]}", "line": e["line"]})
                if tgt not in seen:
                    seen.add(tgt)
                    q.append((tgt, depth + 1))
        traces.append({"entry": f"{efile}#{ename}", "label": label,
                       "nodes": nodes, "edges": edges})
        covered = sum(1 for n in nodes.values() if n["notes"])
        print(f"{label:22} 노드 {len(nodes):3d} · 간선 {len(edges):3d} · "
              f"노트가 설명하는 노드 {covered}/{len(nodes)}")

    dump("trace.json", {"head_sha": code["head_sha"], "traces": traces})
    print("-> out/trace.json")


if __name__ == "__main__":
    main()
