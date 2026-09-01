#!/usr/bin/env python3
"""실험 카드 (위키 W4) + 고아 실험 갭(G6) — LLM 미사용.

artifacts/README.md 의 규칙: "논문의 모든 수치는 여기의 run-id 를 인용해야 한다."
그 인용 관계를 양방향으로 만들고, 규칙 위반을 기계가 검사한다.

각 run-id 에서 읽는 것
  manifest.json  run_id · git_sha · dirty · binary_md5 · created_utc
  hosts.tsv      노드별 코어·governor·주파수·온도
  environment.txt 컴파일러·커널·아키텍처
  results.tsv    측정 결과 (수치 요약)
  raw/*.log      모델 설정 · 사용된 플래그 · 오류
출력: out/artifacts.json
"""
import json
import os
import re
import statistics
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common import NOTE_DIR, REPO, dump, git, read, walk  # noqa: E402

ART = "artifacts"
FLAG = re.compile(r"(--[a-z][a-z0-9-]+)")
KV = re.compile(r"^[^\w]*([A-Za-z][\w ]*?)\s*:\s*(.+?)\s*$")
ERROR = re.compile(r"(🚨|Critical error|Traceback|Segmentation fault|error:)", re.I)
MODEL_KEYS = ("Arch", "Dim", "HeadDim", "KvDim", "HiddenDim", "nLayers",
              "nHeads", "nKvHeads", "SeqLen", "RequiredMemory")


def tsv(path):
    try:
        rows = [l.split("\t") for l in read(path).strip().split("\n") if l.strip()]
    except OSError:
        return None, []
    if not rows:
        return None, []
    return rows[0], rows[1:]


def num_summary(head, rows):
    """숫자 열만 골라 최소/중앙/최대를 낸다."""
    out = {}
    for i, col in enumerate(head):
        vals = []
        for r in rows:
            if i < len(r):
                try:
                    vals.append(float(r[i].replace(",", "")))
                except ValueError:
                    pass
        if len(vals) >= 2 and len(vals) >= len(rows) * 0.6:
            out[col] = {"n": len(vals), "min": round(min(vals), 2),
                        "median": round(statistics.median(vals), 2),
                        "max": round(max(vals), 2)}
    return out


def main():
    root = os.path.join(REPO, ART)
    if not os.path.isdir(root):
        print("artifacts/ 없음"); return 0
    notes = {rel: read(full) for rel, full in walk(NOTE_DIR, (".md",))}
    known_sha = set()
    for line in git("log", "--format=%H").split():
        known_sha.add(line.strip())

    runs = []
    for rid in sorted(os.listdir(root)):
        d = os.path.join(root, rid)
        if not os.path.isdir(d):
            continue
        r = {"run_id": rid, "warnings": []}

        mp = os.path.join(d, "manifest.json")
        if os.path.exists(mp):
            try:
                m = json.loads(read(mp))
                r.update({k: m.get(k) for k in
                          ("git_sha", "dirty", "binary_md5", "created_utc")})
                if m.get("git_sha"):
                    r["sha_known"] = m["git_sha"] in known_sha
                    if not r["sha_known"]:
                        r["warnings"].append("manifest 의 git_sha 가 이 히스토리에 없음")
                if m.get("dirty"):
                    r["warnings"].append("dirty=true — 커밋 안 된 변경이 섞임")
            except Exception as e:
                r["warnings"].append(f"manifest 파싱 실패: {e}")
        else:
            r["warnings"].append("manifest.json 없음 — 재현 조건 불명")

        head, rows = tsv(os.path.join(d, "hosts.tsv"))
        if head:
            hosts = [dict(zip(head, row)) for row in rows]
            r["hosts"] = hosts
            r["node_count"] = len(hosts)
            temps = [float(h["temp_c"]) for h in hosts
                     if h.get("temp_c", "").replace(".", "").isdigit()]
            if temps:
                r["temp_range"] = [min(temps), max(temps)]
            govs = {h.get("governor") for h in hosts if h.get("governor")}
            r["governor"] = sorted(govs)
            if len(govs) > 1:
                r["warnings"].append(f"노드마다 governor 가 다름: {sorted(govs)}")

        ep = os.path.join(d, "environment.txt")
        if os.path.exists(ep):
            env = {}
            for line in read(ep).split("\n"):
                m = KV.match(line)
                if m:
                    env[m.group(1).strip()] = m.group(2)[:120]
            r["environment"] = env

        head, rows = tsv(os.path.join(d, "results.tsv"))
        if head:
            r["results"] = {"columns": head, "rows": len(rows),
                            "summary": num_summary(head, rows)}

        rawd = os.path.join(d, "raw")
        logs, flags, model, errors = [], set(), {}, []
        if os.path.isdir(rawd):
            for fn in sorted(os.listdir(rawd)):
                p = os.path.join(rawd, fn)
                logs.append(fn)
                if not fn.endswith((".log", ".txt")):
                    continue
                try:
                    text = read(p)
                except OSError:
                    continue
                flags |= set(FLAG.findall(text))
                for line in text.split("\n"):
                    if ERROR.search(line):
                        errors.append({"file": fn, "line": line.strip()[:120]})
                    m = KV.match(line)
                    if m and m.group(1).strip() in MODEL_KEYS:
                        model.setdefault(m.group(1).strip(), m.group(2)[:40])
        r["raw_files"] = len(logs)
        r["flags"] = sorted(flags)
        r["model"] = model
        r["errors"] = errors[:6]
        if errors:
            r["warnings"].append(f"로그에 오류 {len(errors)}건")
        if "inconclusive" in rid:
            r["warnings"].append("run-id 에 inconclusive — 결론 보류된 실험")

        # 단순 부분문자열이면 'official_baseline_v2' 가
        # 'official_baseline_v2_final' 언급에도 걸린다. 경계를 준다.
        pat = re.compile(r"(?<![\w-])" + re.escape(rid) + r"(?![\w-])")
        cited = sorted(rel.replace("research/", "") for rel, t in notes.items()
                       if pat.search(t))
        r["cited_in"] = cited
        if not cited:
            r["warnings"].append("어떤 노트도 이 실험을 인용하지 않음 (G6)")
        runs.append(r)

    g6 = [r["run_id"] for r in runs if not r["cited_in"]]
    dump("artifacts.json", {"count": len(runs), "runs": runs, "G6": g6})
    print(f"실험 카드 {len(runs)}개")
    for r in runs:
        w = f"  ⚠ {len(r['warnings'])}" if r["warnings"] else ""
        print(f"  {r['run_id']:<28} 노드 {r.get('node_count','-'):>2} · "
              f"로그 {r['raw_files']:>2} · 플래그 {len(r['flags']):>2} · "
              f"인용 {len(r['cited_in'])}{w}")
    print(f"\nG6 고아 실험 {len(g6)}/{len(runs)}: {', '.join(g6) or '없음'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
