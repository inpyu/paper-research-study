#!/usr/bin/env python3
"""Claude Code 헤드리스로 브리핑을 생성한다 (구독 사용, API 키 없음).

원칙
  - 한 번의 호출, 하나의 JSON 산출물. 대화형 상태에 의존하지 않는다.
  - 스키마 검증에 실패하면 1회 재시도, 그래도 실패면 직전 산출물을 유지한다.
  - 매 호출의 usage 를 logs/usage.jsonl 에 적재한다.
출력: out/briefings/YYYY-MM-DD.json
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common import OUT, load  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLAUDE = next((p for p in (
    os.path.expanduser("~/.local/bin/claude"),
    "/home/cau/.vscode-server/extensions/anthropic.claude-code-2.1.252-linux-x64/"
    "resources/native-binary/claude") if os.path.exists(p)), "claude")

SCHEMA = {
    "type": "object",
    "required": ["briefings"],
    "properties": {"briefings": {"type": "array", "items": {
        "type": "object",
        "required": ["id", "what", "relation", "verdict"],
        "properties": {
            "id": {"type": "string"},
            "what": {"type": "string", "minLength": 5},
            "relation": {"type": "string", "minLength": 5},
            "verdict": {"enum": ["must-read", "skim", "skip"]},
            "gap": {"type": "string"},
            "topics": {"type": "array", "items": {"type": "string"}},
            "hypotheses": {"type": "array", "items":
                           {"type": "string", "pattern": "^H[1-9]$"}},
        }}}},
}


def log_usage(kind, res):
    os.makedirs(os.path.join(ROOT, "logs"), exist_ok=True)
    u = (res or {}).get("usage", {})
    rec = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "kind": kind,
           "input": u.get("input_tokens"), "output": u.get("output_tokens"),
           "cache_read": u.get("cache_read_input_tokens"),
           "cache_create": u.get("cache_creation_input_tokens"),
           "cost_usd_list": (res or {}).get("total_cost_usd"),
           "duration_ms": (res or {}).get("duration_api_ms")}
    with open(os.path.join(ROOT, "logs", "usage.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def call_claude(prompt, model, timeout=240):
    env = {k: v for k, v in os.environ.items()
           if k not in ("CLAUDECODE", "CLAUDE_CODE_SSE_PORT")}
    r = subprocess.run(
        [CLAUDE, "-p", prompt, "--model", model, "--output-format", "json",
         "--permission-mode", "acceptEdits", "--allowedTools", ""],
        capture_output=True, text=True, timeout=timeout, env=env, cwd=ROOT)
    if r.returncode != 0:
        return None, f"claude 실패({r.returncode}): {r.stderr.strip()[:200]}"
    try:
        res = json.loads(r.stdout)
    except json.JSONDecodeError:
        return None, "claude 출력이 JSON 이 아님"
    return res, None


def extract_json(text):
    """모델이 앞뒤에 말을 붙였을 때를 대비해 첫 JSON 객체를 꺼낸다."""
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    i, depth = text.find("{"), 0
    if i < 0:
        return None
    for j in range(i, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[i:j + 1])
                except json.JSONDecodeError:
                    return None
    return None


def build_prompt(cands, notes):
    hyp = "\n".join(f"- {h['id']}: {h['context'].strip('| ')}"
                    for h in sorted(notes["hypotheses"].values(),
                                    key=lambda x: x["id"]))
    meta = json.load(open(os.path.join(OUT, "papers_meta.json"), encoding="utf-8"))
    seeds = [m["title"] for m in list(meta.values())[:12]]
    papers = "\n\n".join(
        f"### id: {c['id']}\n제목: {c['title']}\n분류: {', '.join(c['categories'][:4])}\n"
        f"공개: {c['published']}\n초록: {c['abstract'][:1400]}"
        for c in cands)
    tpl = open(os.path.join(ROOT, "prompts", "briefing.md"), encoding="utf-8").read()
    return (tpl.replace("{HYPOTHESES}", hyp)
               .replace("{SEED_TITLES}", "; ".join(seeds))
               .replace("{PAPERS}", papers))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-haiku-4-5-20251001")
    ap.add_argument("--top", type=int, default=6, help="브리핑에 넣을 후보 수")
    ap.add_argument("--keep", type=int, default=3, help="최종 저장할 편수")
    args = ap.parse_args()

    notes = load("notes.json")
    cands = load("candidates.json")["items"][:args.top]
    if not cands:
        print("후보 없음 — 건너뜀")
        return 0
    by_id = {c["id"]: c for c in cands}
    prompt = build_prompt(cands, notes)

    parsed = None
    for attempt in (1, 2):
        res, err = call_claude(prompt, args.model)
        log_usage("briefing", res)
        if err:
            print(f"  시도 {attempt}: {err}")
            continue
        obj = extract_json(res.get("result", ""))
        if obj is None:
            print(f"  시도 {attempt}: JSON 추출 실패")
            continue
        try:
            import jsonschema
            jsonschema.validate(obj, SCHEMA)
        except ImportError:
            pass
        except Exception as e:
            print(f"  시도 {attempt}: 스키마 위반 {str(e)[:120]}")
            continue
        unknown = [b["id"] for b in obj["briefings"] if b["id"] not in by_id]
        if unknown:
            print(f"  시도 {attempt}: 모르는 id {unknown[:3]}")
            continue
        parsed = obj
        break

    if parsed is None:
        print("생성 실패 — 직전 산출물을 유지한다 (배포는 계속 진행)")
        return 1

    order = {"must-read": 0, "skim": 1, "skip": 2}
    # 모델이 같은 논문을 두 번 낼 수 있다. 먼저 중복을 제거한다.
    dedup = {}
    for b in parsed["briefings"]:
        if b["id"] not in dedup or order[b["verdict"]] < order[dedup[b["id"]]["verdict"]]:
            dedup[b["id"]] = b
    items = sorted(dedup.values(), key=lambda b: (order[b["verdict"]],
                                                  -by_id[b["id"]]["score"]))
    # 가설 번호(H2)만 보여주면 무슨 말인지 알 수 없다. 본문을 함께 넣는다.
    hyp_text = {h["id"]: h["context"].strip("| ").split("|")[1].strip()
                if "|" in h["context"] else h["context"]
                for h in notes["hypotheses"].values()}

    def enrich(b):
        c = by_id[b["id"]]
        notes_ = [f"{h}: {hyp_text.get(h, '')}"[:120]
                  for h in (b.get("hypotheses") or []) if h in hyp_text]
        return {**b, "hypothesis_notes": notes_,
                "topics": b.get("topics", [])[:4],
                "title": c["title"], "url": c["url"],
                "published": c["published"], "authors": c["authors"][:5],
                "categories": c["categories"][:4], "score": c["score"],
                "abstract": c["abstract"][:600]}

    allb = [enrich(b) for b in items]
    # 판정 우선순위 -> 유사도 순으로 정확히 keep 편만 남긴다(전체는 all 에 보존).
    out = allb[:args.keep]
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    os.makedirs(os.path.join(OUT, "briefings"), exist_ok=True)
    p = os.path.join(OUT, "briefings", f"{day}.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"date": day, "model": args.model,
                   "items": out, "all": allb}, f, ensure_ascii=False, indent=1)
    print(f"브리핑 {len(out)}편 -> {p}")
    for b in out:
        print(f"  [{b['verdict']:9}] {b['title'][:58]}")
        print(f"              {b['relation'][:88]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
