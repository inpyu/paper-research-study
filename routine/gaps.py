#!/usr/bin/env python3
"""갭 산출 (LLM 미사용).

개념 갭
  G1 코드에 있는데 노트에 아예 없음        -> 지금 막히는 지점
  G2 노트에 있는데 코드 근거가 없음        -> 미구현 / 순수 배경지식
  G3 노트에서 언급만 되고 정의된 적 없음   -> "안다고 착각하고 넘어간" 것 ★
문서화 갭
  G4 어떤 노트도 언급하지 않는 소스 파일
  G5 노트에 설명이 없는 CLI 플래그
출력: out/gaps.json  +  사람이 읽는 요약(stdout)
"""
import argparse
import re
import sys
from collections import Counter

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common import NOTE_DIR, REPO, dump, load, norm, read, walk  # noqa: E402

# 개념일 리 없는 흔한 토큰 + 이미 아는 게 당연한 일반 용어
STOP = {w.lower() for w in """
the and for with this that from not are was were has have had you your
one two all any out per via off top end new old use used using
및 그리고 하지만 그러나 것 수 등 때 더 각 이 그 저 안 밖 위 아래 전 후 중 간
TODO FIXME XXX NOTE OK YES NO ID URL API HTTP JSON YAML CSV TSV
CPU GPU RAM DRAM SRAM ROM SSD NVMe MB GB KB TB MS NS US
FLOP FLOPS GFLOPS TFLOPS GFLOP MFLOPS SBC PC OS RTT
SPDX NOLINT FileCopyrightText License Copyright
distributed llama llama.cpp github arxiv
""".split()}
# 'pp4', 'tp2', 'b16' 같은 실험 설정 라벨은 개념이 아니다
CONFIG_LABEL = re.compile(r"^(pp|tp|sp|cp|dp|b|s|n|q)\d+$")
# 측정값('16.3 ms')·수식 조각('M < N')은 용어가 아니다
NOT_A_TERM = re.compile(r"^[\d.]|[<>=≤≥×·]|^\W")
# 노트가 아니라 upstream 에서 온 파일 — 문서화 갭으로 세지 않는다
VENDORED = ("src/json.hpp", "src/nn/pthread.h")


def load_note_text():
    blobs = {}
    for rel, full in walk(NOTE_DIR, (".md",)):
        blobs[rel] = read(full)
    return blobs


def mentioned_in(blobs, needle, lowered=None):
    """노트 원문에 그대로 등장하는가 (문서 목록 반환)"""
    n = needle.lower()
    return [rel for rel, txt in (lowered or blobs).items() if n in txt]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=10)
    args = ap.parse_args()

    notes = load("notes.json")
    code = load("code.json")
    blobs = load_note_text()
    lowered = {rel: txt.lower() for rel, txt in blobs.items()}

    defined = {c["key"]: c for c in notes["concepts"]}
    mentions = notes["mentions"]
    stage_terms = " ".join(s["title"] for s in notes["stages"]).lower()
    churn = {f["path"]: f["churn"] for f in code["files"]}
    sym_by_term = Counter()
    file_of_term = {}
    for s in code["symbols"]:
        sym_by_term[norm(s["name"])] += 1
        file_of_term.setdefault(norm(s["name"]), s["file"])

    # ---------- G1: 코드에 있는데 노트에 전혀 없음 ----------
    g1 = []
    for key, info in code["symbol_terms"].items():
        if key in defined or key in mentions or key in STOP:
            continue
        term = info["term"]
        if len(term) < 4 or term.lower() in STOP or CONFIG_LABEL.match(key):
            continue
        if mentioned_in(blobs, term, lowered):
            continue
        f = info.get("file", "")
        if f in VENDORED or f.endswith("-test.cpp") or "/llamafile/" in f:
            continue
        g1.append({"key": key, "term": term, "count": info["count"],
                   "file": f, "churn": churn.get(f, 0),
                   "score": round(info["count"] * 0.5 + churn.get(f, 0) * 0.8, 2)})
    g1.sort(key=lambda x: -x["score"])

    # ---------- G2: 노트에 있는데 코드 근거 없음 ----------
    # 01-code-map.md 의 표만으로는 34개뿐이라, 코드 본문 검색으로 근거를 넓힌다.
    code_blobs = {}
    for f in code["files"]:
        if f["path"] in VENDORED:
            continue
        try:
            code_blobs[f["path"]] = read(
                __import__("os").path.join(REPO, f["path"])).lower()
        except OSError:
            pass
    g2 = []
    for c in notes["concepts"]:
        if c["evidence"]:
            continue
        needles = [c["name"]] + c.get("aliases", [])
        hit = None
        for nd in needles:
            nl = nd.lower()
            if len(nl) < 3:
                continue
            for path, blob in code_blobs.items():
                if nl in blob:
                    hit = path
                    break
            if hit:
                break
        if hit:
            c["evidence"].append({"file": hit, "via": "text-match"})
            continue
        g2.append({"key": c["key"], "name": c["name"], "docs": len(c["defs"])})

    # ---------- G3: 언급만 되고 정의된 적 없음 ★ ----------
    g3 = []
    for key, info in mentions.items():
        docs, emph = info["docs"], info["emph"]
        term = info["term"] or key
        if key in defined or key in STOP or term.lower() in STOP:
            continue
        if len(key) < 4 or CONFIG_LABEL.match(key) or NOT_A_TERM.search(term):
            continue
        in_code = sym_by_term.get(key, 0) + (1 if key in code["code_terms"] else 0)
        # 노트가 용어로 취급했거나(강조) 코드에 실체가 있는 것만 후보로 삼는다.
        if not emph and not in_code:
            continue
        if len(docs) < 2 and not in_code:
            continue
        f = file_of_term.get(key, "")
        score = (0.35 * len(docs)              # 여러 문서가 전제할수록
                 + 0.30 * min(emph, 6)         # 노트가 용어로 강조했을수록
                 + 0.25 * min(in_code, 4)      # 코드에 실체가 있을수록
                 + 0.20 * (2 if term.lower() in stage_terms else 0)
                 + 0.10 * min(churn.get(f, 0), 10))
        g3.append({"key": key, "term": term, "docs": docs, "emph": emph,
                   "doc_count": len(docs), "in_code": in_code,
                   "file": f, "score": round(score, 2)})
    g3.sort(key=lambda x: -x["score"])

    # ---------- G4: 노트가 언급하지 않는 소스 파일 ----------
    g4 = []
    for f in code["files"]:
        if not f["path"].startswith("src/") or f["path"] in VENDORED:
            continue
        base = f["path"].split("/")[-1]
        if mentioned_in(blobs, base, lowered):
            continue
        g4.append({"path": f["path"], "loc": f["loc"], "churn": f["churn"]})
    g4.sort(key=lambda x: (-x["churn"], -x["loc"]))

    # ---------- G5: 노트에 없는 CLI 플래그 ----------
    g5 = []
    for fl in code["flags"]:
        if mentioned_in(blobs, fl["flag"], lowered):
            continue
        g5.append({"flag": fl["flag"], "sites": len(fl["sites"]),
                   "file": fl["sites"][0]["file"], "line": fl["sites"][0]["line"]})

    src_files = [f for f in code["files"] if f["path"].startswith("src/")]
    out = {"head_sha": notes["head_sha"],
           "summary": {
               "concepts_defined": len(defined),
               "mentions": len(mentions),
               "src_files": len(src_files),
               "flags": len(code["flags"]),
               "G1": len(g1), "G2": len(g2), "G3": len(g3),
               "G4": len(g4), "G5": len(g5)},
           "G1": g1, "G2": g2, "G3": g3, "G4": g4, "G5": g5}
    path = dump("gaps.json", out)

    n = args.top
    print(f"\n{'='*66}\n갭 리포트  ({notes['head_sha'][:8]})\n{'='*66}")
    s = out["summary"]
    print(f"정의된 개념 {s['concepts_defined']}  ·  언급 용어 {s['mentions']}  ·  "
          f"소스 파일 {s['src_files']}  ·  CLI 플래그 {s['flags']}")

    print(f"\n★ G3 — 노트에서 언급만 되고 정의된 적 없는 용어  ({len(g3)}개 중 상위 {n})")
    print("   " + "-" * 62)
    for i, x in enumerate(g3[:n], 1):
        where = f"코드 {x['in_code']}곳" if x["in_code"] else "노트만"
        print(f"  {i:2d}. {x['term']:<28} 문서 {x['doc_count']}개 · 강조 {x['emph']}회"
              f" · {where}  (점수 {x['score']})")
        print(f"      → {', '.join(d.replace('research/','') for d in x['docs'][:4])}")

    by_file = {}
    for x in g1:
        by_file.setdefault(x["file"] or "(파일 미상)", []).append(x)
    ranked = sorted(by_file.items(), key=lambda kv: -sum(y["score"] for y in kv[1]))
    print(f"\n  G1 — 코드에만 있고 노트에 없는 용어  ({len(g1)}개, 파일별 상위 {n})")
    print("   " + "-" * 62)
    for fpath, items in ranked[:n]:
        names = ", ".join(y["term"] for y in items[:4])
        more = f" 외 {len(items)-4}개" if len(items) > 4 else ""
        print(f"      {fpath:<30} {len(items):>3}개  {names}{more}")

    print(f"\n  G4 — 노트가 한 번도 언급하지 않는 소스 파일  ({len(g4)}/{len(src_files)})")
    print("   " + "-" * 62)
    for x in g4[:n]:
        print(f"      {x['path']:<34} {x['loc']:>5}줄  변경 {x['churn']}회")

    print(f"\n  G5 — 노트에 설명이 없는 CLI 플래그  ({len(g5)}/{len(code['flags'])})")
    print("   " + "-" * 62)
    for i in range(0, min(len(g5), 24), 3):
        print("      " + "  ".join(f"{x['flag']:<24}" for x in g5[i:i+3]))

    print(f"\n  G2 — 노트에 있으나 코드 근거가 없는 개념  ({len(g2)}/{s['concepts_defined']})")
    print(f"\n-> {path}\n")


if __name__ == "__main__":
    main()
