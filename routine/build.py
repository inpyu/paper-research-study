#!/usr/bin/env python3
"""out/*.json -> site/public/data/*.json (정적 사이트가 먹는 형태)

파일을 잘게 나눈다. 개념 하나를 열 때 전체를 받지 않게 하기 위해서다.
manifest.json 의 해시로 클라이언트 캐시를 무효화한다.
"""
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common import OUT as OUTDIR, REPO, git, load  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "site", "public", "data")


def write(rel, obj):
    p = os.path.join(DATA, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    body = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    with open(p, "w", encoding="utf-8") as f:
        f.write(body)
    return rel, hashlib.sha256(body.encode()).hexdigest()[:12], len(body)


def gh(path, line=None, sha="main"):
    u = f"https://github.com/inpyu/prefill-opt/blob/{sha}/{path}"
    return u + (f"#L{line}" if line else "")


def main():
    notes, code, gaps = load("notes.json"), load("code.json"), load("gaps.json")
    sha = notes["head_sha"]
    files = []

    # ---- 개념: 목록(가벼움) + 개별 상세 ----
    ev_by_key = {}
    for e in notes["evidence"]:
        ev_by_key.setdefault(e["concept_key"], []).append(e)
    links_out = {}
    for l in notes["links"]:
        links_out.setdefault(l["from"], []).append(l)

    # 생성된 설명을 읽어 붙인다
    exp_dir = os.path.join(OUTDIR, "explain")
    explains = {}
    if os.path.isdir(exp_dir):
        for fn in os.listdir(exp_dir):
            if fn.endswith(".json"):
                try:
                    e = json.load(open(os.path.join(exp_dir, fn), encoding="utf-8"))
                    explains[e["key"]] = e
                except Exception:
                    pass

    index = []
    for c in notes["concepts"]:
        ev = ev_by_key.get(c["key"], []) + [
            e for e in c.get("evidence", []) if "via" in e]
        e = explains.get(c["key"], {})
        index.append({"key": c["key"], "name": c["name"],
                      "aliases": c["aliases"], "docs": len(c["defs"]),
                      "ev": len(ev), "one_liner": e.get("one_liner", ""),
                      "difficulty": e.get("difficulty", 0),
                      "tags": e.get("tags", []),
                      "explained": bool(e)})
        files.append(write(f"concept/{c['key'].replace(' ', '_')}.json", {
            "key": c["key"], "name": c["name"], "aliases": c["aliases"],
            **{k: e.get(k) for k in ("one_liner", "what", "why", "how",
                                     "in_this_repo", "difficulty", "tags")},
            "prerequisites": e.get("prerequisites", []),
            "related_keys": e.get("related", []),
            "defs": [{**d, "url": gh(d["doc"], d["line"], sha)} for d in c["defs"]],
            "evidence": [{**e, "url": gh(e["file"], e.get("line_start"), sha)}
                         for e in ev],
            "links": links_out.get(c["key"], []),
        }))
    # 학습 순서: 선행 개념 그래프의 깊이 -> 난이도 -> 이름
    prereq = {c["key"]: explains.get(c["key"], {}).get("prerequisites", [])
              for c in notes["concepts"]}
    keys = set(prereq)
    depth = {}

    def d_of(k, stack=()):
        if k in depth:
            return depth[k]
        if k in stack or k not in keys:          # 순환은 깊이 0 으로 끊는다
            return 0
        ds = [d_of(p, stack + (k,)) for p in prereq.get(k, []) if p in keys]
        depth[k] = (max(ds) + 1) if ds else 0
        return depth[k]

    for k in keys:
        d_of(k)
    by_key = {c["key"]: c for c in index}
    order = sorted(keys, key=lambda k: (depth.get(k, 0),
                                        by_key[k]["difficulty"] or 9,
                                        by_key[k]["name"].lower()))
    steps = {}
    for k in order:
        steps.setdefault(depth.get(k, 0), []).append(k)
    files.append(write("concepts.json", {
        "count": len(index), "items": index,
        "explained": sum(1 for x in index if x["explained"]),
        "order": order,
        "steps": [{"level": lv, "keys": ks} for lv, ks in sorted(steps.items())],
    }))

    # ---- 갭 ----
    for k in ("G1", "G2", "G3", "G4", "G5"):
        items = gaps[k]
        for x in items:
            if "file" in x and x["file"]:
                x["url"] = gh(x["file"], x.get("line"), sha)
            elif "path" in x:
                x["url"] = gh(x["path"], None, sha)
        files.append(write(f"gap/{k}.json", {"count": len(items), "items": items}))
    # 문서화 갭 G6~G8 을 요약에 합류시킨다
    try:
        art = load("artifacts.json")
        gaps["summary"]["G6"] = len(art["G6"])
        gaps["summary"]["runs"] = art["count"]
    except FileNotFoundError:
        pass
    try:
        lg = load("logs.json")
        gaps["summary"]["log_templates"] = lg["count"]
        gaps["summary"]["log_documented"] = lg["documented"]
    except FileNotFoundError:
        pass
    try:
        q = load("questions.json")
        gaps["summary"]["open_questions"] = q["count"]
    except FileNotFoundError:
        pass
    try:
        num = load("numbers.json")
        gaps["summary"]["G7"] = num["G7_count"]
        gaps["summary"]["G8"] = num["G8_count"]
        gaps["summary"]["numbers"] = num["count"]
    except FileNotFoundError:
        pass
    files.append(write("gaps.json", gaps["summary"]))

    # ---- 논문 시드 ----
    papers = []
    for pid, p in notes["papers"].items():
        papers.append({"id": pid, "source": p["source"],
                       "external_id": p["external_id"],
                       "title": p.get("note_title", ""),
                       "gap": p.get("note_gap", ""),
                       "url": (f"https://arxiv.org/abs/{p['external_id']}"
                               if p["source"] == "arxiv"
                               else f"https://doi.org/{p['external_id']}"),
                       "cited_in": sorted({s["doc"] for s in p["seen"]})})
    papers.sort(key=lambda x: -len(x["cited_in"]))
    files.append(write("papers.json", {"count": len(papers), "items": papers}))

    # ---- 브리핑: 최신 + 날짜별 + 목록 ----
    bdir = os.path.join(os.path.dirname(DATA), "..", "..", "out", "briefings")
    bdir = os.path.normpath(bdir)
    days = sorted(os.listdir(bdir)) if os.path.isdir(bdir) else []
    bindex = []
    for fn in days:
        if not fn.endswith(".json"):
            continue
        b = json.load(open(os.path.join(bdir, fn), encoding="utf-8"))
        files.append(write(f"briefing/{b['date']}.json", b))
        must = sum(1 for x in b["items"] if x["verdict"] == "must-read")
        bindex.append({"date": b["date"], "count": len(b["items"]),
                       "must": must,
                       "titles": [x["title"] for x in b["items"][:3]]})
    bindex.sort(key=lambda x: x["date"], reverse=True)
    files.append(write("briefings.json", {"count": len(bindex), "items": bindex,
                                          "latest": bindex[0]["date"] if bindex else None}))

    # ---- 코드 문서 (파일·함수 설명) ----
    doc_dir = os.path.join(OUTDIR, "codedoc")
    cdocs = {}
    if os.path.isdir(doc_dir):
        for fn in sorted(os.listdir(doc_dir)):
            if not fn.endswith(".json"):
                continue
            try:
                cd = json.load(open(os.path.join(doc_dir, fn), encoding="utf-8"))
            except Exception:
                continue
            cd["url"] = gh(cd["file"], None, sha)
            for f_ in cd.get("functions", []):
                f_["url"] = gh(cd["file"], f_.get("line"), sha)
            cdocs[cd["file"]] = cd
            files.append(write(f"code/{cd['file'].replace('/', '_')}.json", cd))

    # ---- 위키 뼈대: 파일 · 플래그 · 학습경로 · 가설 · 연대기 ----
    doc_of_file = {}
    for e in notes["evidence"]:
        doc_of_file.setdefault(e["file"], set()).add(e["doc"])
    src = [{"path": f["path"], "loc": f["loc"], "churn": f["churn"],
            "in_refs": f.get("in_refs", 0), "url": gh(f["path"], None, sha),
            "notes": sorted(doc_of_file.get(f["path"], []))}
           for f in code["files"] if f["path"].startswith("src/")]
    for f_ in src:
        cd = cdocs.get(f_["path"])
        if cd:
            f_["role"] = cd.get("role", "")[:160]
            f_["tags"] = cd.get("tags", [])
            f_["functions"] = len(cd.get("functions", []))
            f_["doc"] = True
    files.append(write("wiki/files.json", {
        "count": len(src), "documented": sum(1 for f_ in src if f_.get("doc")),
        "items": src}))
    files.append(write("wiki/flags.json", {
        "count": len(code["flags"]),
        "items": [{"flag": f["flag"], "sites": f["sites"],
                   "url": gh(f["sites"][0]["file"], f["sites"][0]["line"], sha)}
                  for f in code["flags"]]}))
    try:
        tr = load("trace.json")
        for t in tr["traces"]:
            t["covered"] = sum(1 for n in t["nodes"].values() if n["notes"])
            for n in t["nodes"].values():
                n["url"] = gh(n["file"], n["line"], sha)
        files.append(write("wiki/trace.json", tr))
    except FileNotFoundError:
        tr = None

    for name in ("artifacts", "numbers", "logs", "questions", "xref"):
        try:
            files.append(write(f"wiki/{name}.json", load(f"{name}.json")))
        except FileNotFoundError:
            pass

    log = [l for l in git("log", "--format=%h\t%ad\t%s", "--date=short").split("\n") if l]
    files.append(write("wiki/history.json", {
        "count": len(log),
        "items": [dict(zip(("sha", "date", "subject"), l.split("\t", 2)))
                  for l in log]}))
    files.append(write("wiki/plan.json", {
        "stages": notes["stages"], "hypotheses": notes["hypotheses"],
        "docs": [{**d, "url": gh(d["path"], None, sha)} for d in notes["docs"]]}))

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "repo": "inpyu/prefill-opt", "head_sha": sha,
        "summary": gaps["summary"],
        "latest_briefing": bindex[0]["date"] if bindex else None,
        "files": {rel: {"hash": h, "bytes": n} for rel, h, n in files},
    }
    write("manifest.json", manifest)
    total = sum(n for _, _, n in files)
    print(f"데이터 파일 {len(files)+1}개, {total/1024:.0f} KB -> site/public/data/")
    print(f"  개념 {len(index)} · 논문 {len(papers)} · 소스파일 {len(src)} · "
          f"플래그 {len(code['flags'])} · 커밋 {len(log)} · 브리핑 {len(bindex)}일치 · "
          f"실행경로 {len(tr['traces']) if tr else 0}개")
    print(f"  설명: 개념 {len(explains)}/{len(index)} · 코드 파일 {len(cdocs)}")


if __name__ == "__main__":
    main()
