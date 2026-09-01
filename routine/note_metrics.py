#!/usr/bin/env python3
"""수치 대사전 (W6) + 출처 없는 수치(G7) + 문서 간 불일치(G8) — LLM 미사용.

artifacts/README.md 는 "논문의 모든 수치는 run-id 를 인용해야 한다"고 규정한다.
그 규칙을 기계가 검사한다. 논문 쓸 때 바로 쓸모 있는 갭이다.
출력: out/numbers.json  (모듈명은 note_metrics — 표준 라이브러리 numbers 를 가리면
       jsonschema 가 깨진다. 실제로 브리핑 생성이 이 이유로 실패했다.)
"""
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common import NOTE_DIR, REPO, dump, read, walk  # noqa: E402

# 측정값처럼 보이는 것: 1,234.5 ms / 20.5% / 1.85배 / 447토큰 / 11–14 FLOP/byte
UNIT = (r"(?:ms|s|초|us|µs|ns|GB|MB|KB|GiB|MiB|%|배|×|x|"
        r"토큰|tokens?|FLOP/byte|GFLOPS|GFLOP|TFLOPS|MB/s|GB/s|Gbps|Mbps|"
        r"코어|cores?|노드|nodes?|레이어|layers?|℃|°C)")
NUM = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*(" + UNIT + r")\b")
RUNID = re.compile(r"(?<![\w-])((?:[a-z]\w*_)+\w+|official_baseline\w*|"
                   r"b_axis\w*|diag\d+|model13b\w*)(?![\w-])")
CODEFENCE = re.compile(r"```.*?```", re.S)
STOPCTX = re.compile(r"^\s*[|>#-]")


def norm_num(v):
    return float(v.replace(",", ""))


def signature(ctx):
    """숫자를 뺀 주변 문맥 -> 같은 양을 가리키는지 판별하는 열쇠."""
    s = re.sub(r"[\d.,]+", "", ctx.lower())
    s = re.sub(r"[^0-9a-z가-힣 ]", " ", s)
    words = [w for w in s.split() if len(w) > 1]
    return " ".join(sorted(set(words))[:6])


def main():
    run_ids = set()
    ard = os.path.join(REPO, "artifacts")
    if os.path.isdir(ard):
        run_ids = {d for d in os.listdir(ard)
                   if os.path.isdir(os.path.join(ard, d))}

    facts = []
    doc_cites = {}          # 문서 -> 그 문서가 인용한 run-id (본문 전체 기준)
    for rel, full in walk(NOTE_DIR, (".md",)):
        text = CODEFENCE.sub(" ", read(full))
        doc_cites[rel.replace("research/", "")] = sorted(
            r for r in run_ids
            if re.search(r"(?<![\w-])" + re.escape(r) + r"(?![\w-])", text))
        lines = text.split("\n")
        # 섹션 단위로 run-id 인용 여부를 본다
        sec, sec_start = "", 0
        sec_runids = set()
        section_of = []
        for i, line in enumerate(lines):
            if line.startswith("#"):
                sec, sec_start, sec_runids = line.lstrip("# ").strip(), i, set()
            for m in RUNID.finditer(line):
                if m.group(1) in run_ids:
                    sec_runids.add(m.group(1))
            section_of.append((sec, sec_runids))
        # 섹션의 run-id 는 뒤에서 나올 수도 있으므로 두 번째 통과
        sec_map = defaultdict(set)
        cur = ""
        for i, line in enumerate(lines):
            if line.startswith("#"):
                cur = line.lstrip("# ").strip()
            for m in RUNID.finditer(line):
                if m.group(1) in run_ids:
                    sec_map[cur].add(m.group(1))

        cur = ""
        for i, line in enumerate(lines, 1):
            if line.startswith("#"):
                cur = line.lstrip("# ").strip()
                continue
            if not line.strip() or STOPCTX.match(line) and line.startswith(">"):
                continue
            for m in NUM.finditer(line):
                a, b = max(0, m.start() - 45), min(len(line), m.end() + 45)
                ctx = line[a:b].strip()
                facts.append({
                    "doc": rel.replace("research/", ""), "line": i,
                    "section": cur[:60],
                    "value": norm_num(m.group(1)), "unit": m.group(2),
                    "raw": m.group(0), "context": ctx,
                    "run_ids": sorted(sec_map.get(cur, [])),
                    "sig": signature(ctx),
                })

    # G7 — 출처 추적 불가한 수치
    #
    # 처음엔 '섹션에 run-id 인용이 없으면 G7' 로 했더니 1257개 중 1215개가 걸렸다.
    # 그건 갭이 아니라 잡음이다. 노트는 보통 문서 상단에서 한 번 run-id 를 밝힌다.
    # 그래서 판정을 문서 단위로 옮기고, 측정값을 주장하는 문서에만 적용한다.
    doc_runids = {d: set(v) for d, v in doc_cites.items()}
    doc_nums = defaultdict(int)
    for f in facts:
        doc_nums[f["doc"]] += 1
    # 측정 단위(시간·처리량·온도)를 쓰는 수치만 '측정 주장' 으로 본다.
    MEASURED = {"ms", "s", "초", "us", "µs", "ns", "GFLOPS", "GFLOP", "TFLOPS",
                "MB/s", "GB/s", "Gbps", "Mbps", "℃", "°C", "배", "×", "%"}
    g7 = [f for f in facts
          if f["unit"] in MEASURED and not doc_runids.get(f["doc"])]
    doc_report = sorted(
        ({"doc": d, "numbers": doc_nums[d], "run_ids": sorted(doc_runids.get(d, [])),
          "measured_unsourced": sum(1 for f in g7 if f["doc"] == d)}
         for d in doc_nums if True),
        key=lambda x: -x["measured_unsourced"])

    # G8 — 같은 문맥 서명인데 값이 다른 것
    groups = defaultdict(list)
    for f in facts:
        if len(f["sig"]) > 12:
            groups[(f["sig"], f["unit"])].append(f)
    g8 = []
    for (sig, unit), items in groups.items():
        vals = {f["value"] for f in items}
        if len(vals) > 1 and len({f["doc"] for f in items}) > 1:
            g8.append({"sig": sig, "unit": unit,
                       "values": sorted(vals)[:8],
                       "where": [{"doc": f["doc"], "line": f["line"],
                                  "raw": f["raw"], "context": f["context"][:90]}
                                 for f in items[:6]]})
    g8.sort(key=lambda x: -len(x["values"]))

    # 자주 인용되는 수치 = 이 연구의 핵심 숫자
    by_val = defaultdict(list)
    for f in facts:
        by_val[(f["value"], f["unit"])].append(f)
    top = sorted(by_val.items(), key=lambda kv: -len(kv[1]))[:60]
    dictionary = [{"value": v, "unit": u, "count": len(items),
                   "docs": sorted({f["doc"] for f in items})[:6],
                   "example": items[0]["context"][:110],
                   "run_ids": sorted({r for f in items for r in f["run_ids"]})[:4]}
                  for (v, u), items in top]

    dump("numbers.json", {"count": len(facts), "dictionary": dictionary,
                          "docs": doc_report,
                          "G7": g7[:400], "G7_count": len(g7),
                          "G8": g8[:60], "G8_count": len(g8)})
    print(f"수치 {len(facts)}개 추출")
    sourced = sum(1 for d in doc_report if d["run_ids"])
    print(f"run-id 를 인용하는 문서 {sourced}/{len(doc_report)}")
    print(f"G7 출처 없는 측정값       {len(g7)}개 "
          f"(측정 단위 수치만, 인용 없는 문서 기준)")
    for d in doc_report[:5]:
        if d["measured_unsourced"]:
            print(f"    {d['doc']:<34} 측정값 {d['measured_unsourced']:>3}개, run-id 인용 없음")
    print(f"G8 문서 간 불일치 후보     {len(g8)}건")
    for d in dictionary[:8]:
        print(f"  {d['value']:>10,.1f} {d['unit']:<10} {d['count']:>3}회  "
              f"{', '.join(d['docs'][:3])}")
    for x in g8[:4]:
        print(f"  불일치: {x['values']} {x['unit']}  ← {x['sig'][:50]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
