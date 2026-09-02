#!/usr/bin/env python3
"""학습 카탈로그 (영역 → 과목 → 레슨) 생성.

curriculum/skeleton.json 이 골격(영역·과목·레슨 수)이고,
이 스크립트가 과목별로 레슨을 채운다. 한 과목씩 독립 호출이라
중간에 실패해도 나머지는 살아남는다.
출력: curriculum/catalog.json  (레포에 커밋되는 사람이 고치는 파일)
"""
import argparse
import json
import os
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common import OUT, load, read  # noqa: E402
from generate import call_claude, extract_json, log_usage  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKEL = os.path.join(ROOT, "curriculum", "skeleton.json")
DEST = os.path.join(ROOT, "curriculum", "catalog.json")


def all_concept_keys():
    keys = [c["key"] for c in load("notes.json")["concepts"]]
    fp = os.path.join(ROOT, "curriculum", "foundations.json")
    if os.path.exists(fp):
        for st in json.load(open(fp, encoding="utf-8"))["stages"]:
            keys += [c["key"] for c in st["concepts"]]
    return keys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-sonnet-5")
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    skel = json.load(open(SKEL, encoding="utf-8"))
    cat = {"tracks": []}
    if os.path.exists(DEST) and not args.force:
        cat = json.load(open(DEST, encoding="utf-8"))
    have = {c["id"]: c for t in cat["tracks"] for c in t["courses"]
            if c.get("lessons")}

    keys = all_concept_keys()
    tpl = read(os.path.join(ROOT, "prompts", "catalog.md"))
    made = 0

    tracks = []
    for t in skel["tracks"]:
        courses = []
        for c in t["courses"]:
            if c["id"] in have:
                courses.append(have[c["id"]])
                continue
            if made >= args.limit:
                courses.append({**c, "lessons": []})
                continue
            prompt = tpl.replace("{CONCEPTS}", ", ".join(keys)).replace(
                "{COURSE}",
                f"id: {c['id']}\n제목: {c['title']}\n영역: {t['title']}\n"
                f"레슨 수: {c['lessons']}개")
            got = None
            for attempt in (1, 2):
                res, err = call_claude(prompt, args.model, timeout=600)
                log_usage("catalog", res)
                if err:
                    print(f"  {c['id']} 시도 {attempt}: {err}")
                    continue
                obj = extract_json(res.get("result", ""))
                if not obj or not obj.get("lessons"):
                    print(f"  {c['id']} 시도 {attempt}: JSON 실패")
                    continue
                got = obj
                break
            if not got:
                courses.append({**c, "lessons": []})
                continue
            lessons = []
            for i, l in enumerate(got["lessons"], 1):
                lessons.append({
                    "id": l.get("id") or f"{c['id']}-{i:02d}",
                    "title": l.get("title", ""),
                    "one_liner": l.get("one_liner", ""),
                    "minutes": max(15, min(120, int(l.get("minutes", 40) or 40))),
                    "concepts": [k for k in l.get("concepts", []) if k in keys][:4],
                    "quiz_topics": l.get("quiz_topics", [])[:3],
                })
            courses.append({"id": c["id"], "title": c["title"],
                            "summary": got.get("summary", ""),
                            "lessons": lessons,
                            "minutes": sum(x["minutes"] for x in lessons)})
            made += 1
            print(f"  {c['id']:<20} 레슨 {len(lessons):>2}개 · "
                  f"{sum(x['minutes'] for x in lessons)}분")
        tracks.append({"id": t["id"], "title": t["title"], "courses": courses})

    for t in tracks:
        t["minutes"] = sum(c.get("minutes", 0) for c in t["courses"])
        t["course_count"] = len(t["courses"])
    cat = {"tracks": tracks,
           "lesson_count": sum(len(c.get("lessons", []))
                               for t in tracks for c in t["courses"]),
           "minutes": sum(t["minutes"] for t in tracks)}
    with open(DEST, "w", encoding="utf-8") as f:
        json.dump(cat, f, ensure_ascii=False, indent=1)
    done = sum(1 for t in tracks for c in t["courses"] if c.get("lessons"))
    total = sum(len(t["courses"]) for t in tracks)
    print(f"카탈로그 {done}/{total} 과목 · 레슨 {cat['lesson_count']}개 · "
          f"{cat['minutes']//60}시간 {cat['minutes']%60}분 -> {DEST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
