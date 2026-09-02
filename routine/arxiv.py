#!/usr/bin/env python3
"""arXiv 신규 논문 수집 + 시드 유사도 필터 (LLM 미사용, stdlib 전용).

1) 시드 정규화: refs.md 에서 뽑은 arXiv ID -> arXiv API 로 메타데이터 확정
                (제목·초록을 지어내지 않는다. API 응답만 쓴다)
2) 신규 수집  : 관심 카테고리의 최근 논문
3) 랭킹       : 시드 말뭉치에 대한 BM25 로 상위 N편
출력: out/papers_meta.json(시드 캐시), out/candidates.json
"""
import argparse
import json
import math
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common import OUT, dump, load  # noqa: E402

API = "http://export.arxiv.org/api/query?"
NS = {"a": "http://www.w3.org/2005/Atom"}
UA = {"User-Agent": "RepoScholar/0.1 (personal research tool; "
                    "mailto:caudcslab@gmail.com)"}
GAP = 5          # arXiv 권고는 3초 이상. 여유를 둔다
BUDGET = 180     # 전체 수집에 쓸 시간 상한(초). 넘으면 가진 것으로 진행한다
CATS = ("cs.DC", "cs.LG", "cs.AR", "cs.PF")

# refs.md 의 논문에서 자동 도출한 도메인 어휘 (질의 확장용)
QUERIES = [
    "prefill", "time to first token", "context parallelism", "chunked prefill",
    "edge inference", "CPU inference", "pipeline parallelism", "KV cache",
    "distributed inference", "LLM serving latency",
]

WORD = re.compile(r"[a-z][a-z0-9+-]{2,}")
STOP = set("""the and for with this that from are was were has have not but you our
we they our their its his her can may will would should could been being
using use used based new novel propose proposed method methods approach results
show shows paper work study which while when where what how why into than then
also more most such very much many both each other another same different""".split())


def tok(text):
    return [w for w in WORD.findall(text.lower()) if w not in STOP and len(w) > 2]


def fetch(params, retries=3, deadline=None):
    """arXiv 는 과요청에 429 를 준다. 백오프하되 전체 시간 예산을 지킨다."""
    url = API + urllib.parse.urlencode(params)
    for i in range(retries):
        if deadline and time.time() > deadline:
            print("  시간 예산 초과 — 수집 중단")
            return None
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                return ET.fromstring(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 20 * (i + 1)
                print(f"  429 (요청 과다) — {wait}초 대기")
                if deadline and time.time() + wait > deadline:
                    return None
                time.sleep(wait)
                continue
            print(f"  arXiv HTTP {e.code}")
            return None
        except Exception as e:
            if i == retries - 1:
                print(f"  arXiv 요청 실패: {e}")
                return None
            time.sleep(5 * (i + 1))
    return None


def parse_entries(root):
    out = []
    if root is None:
        return out
    for e in root.findall("a:entry", NS):
        def txt(tag):
            n = e.find("a:" + tag, NS)
            return re.sub(r"\s+", " ", n.text).strip() if n is not None and n.text else ""
        aid = txt("id").rsplit("/", 1)[-1]
        out.append({
            "id": re.sub(r"v\d+$", "", aid),
            "title": txt("title"),
            "abstract": txt("summary"),
            "published": txt("published")[:10],
            "updated": txt("updated")[:10],
            "url": txt("id"),
            "authors": [a.find("a:name", NS).text
                        for a in e.findall("a:author", NS)][:8],
            "categories": [c.get("term") for c in e.findall("a:category", NS)],
        })
    return out


def seed_meta(ids, cache):
    """시드 논문 메타데이터. 한 번 받으면 캐시한다."""
    missing = [i for i in ids if i not in cache]
    for i in range(0, len(missing), 20):
        chunk = missing[i:i + 20]
        root = fetch({"id_list": ",".join(chunk), "max_results": len(chunk)})
        for e in parse_entries(root):
            cache[e["id"]] = e
        if root is not None:
            time.sleep(GAP)        # arXiv 권고 간격
    return cache


class BM25:
    def __init__(self, docs, k1=1.5, b=0.75):
        self.k1, self.b = k1, b
        self.docs = [Counter(d) for d in docs]
        self.len = [sum(c.values()) for c in self.docs]
        self.avg = (sum(self.len) / len(self.len)) if self.len else 0
        self.df = Counter()
        for c in self.docs:
            self.df.update(c.keys())
        self.N = len(self.docs)

    def idf(self, w):
        n = self.df.get(w, 0)
        return math.log(1 + (self.N - n + 0.5) / (n + 0.5))

    def score(self, query):
        """질의(후보 논문)가 시드 말뭉치와 얼마나 겹치는가.

        길이 편향을 없애려고 질의 고유어 수로 정규화한다.
        정규화가 없으면 초록이 긴 논문이 무조건 이긴다.
        """
        q = set(query)
        if not q:
            return 0.0
        s = 0.0
        for w in q:
            if w not in self.df:
                continue
            tf = sum(c.get(w, 0) for c in self.docs)
            s += self.idf(w) * (tf * (self.k1 + 1)) / (tf + self.k1)
        return s / math.sqrt(len(q))


def briefed_ids():
    """이미 브리핑한 논문 id. 같은 논문을 매일 다시 올리지 않기 위해서다.

    신선도 창(--days)만으로는 부족하다. 창이 3일이면 같은 논문이 사흘 내내
    올라온다. 실제로 09-02 브리핑이 09-01 과 같은 3편이었다.
    """
    d = os.path.join(OUT, "briefings")
    out = set()
    if os.path.isdir(d):
        for fn in os.listdir(d):
            if not fn.endswith(".json"):
                continue
            try:
                b = json.load(open(os.path.join(d, fn), encoding="utf-8"))
            except Exception:
                continue
            for x in b.get("all", b.get("items", [])):
                if x.get("id"):
                    out.add(x["id"])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=3, help="최근 며칠치 신규를 볼지")
    ap.add_argument("--top", type=int, default=8)
    ap.add_argument("--queries", type=int, default=4,
                    help="이번 실행에서 던질 질의 수 (arXiv 429 회피)")
    ap.add_argument("--repeat", action="store_true",
                    help="이미 브리핑한 논문도 다시 후보에 넣는다")
    ap.add_argument("--reuse", action="store_true",
                    help="직전 수집 결과를 재사용해 랭킹만 다시 한다")
    args = ap.parse_args()

    notes = load("notes.json")
    seed_ids = [p["external_id"] for p in notes["papers"].values()
                if p["source"] == "arxiv"]
    cache_path = os.path.join(OUT, "papers_meta.json")
    cache = json.load(open(cache_path, encoding="utf-8")) if os.path.exists(cache_path) else {}
    before = len(cache)
    cache = seed_meta(seed_ids, cache)
    dump("papers_meta.json", cache)
    seeds = [cache[i] for i in seed_ids if i in cache]
    print(f"시드 논문 {len(seeds)}/{len(seed_ids)}편 (신규 {len(cache)-before}편 수신)")

    # 시드 말뭉치 -> BM25 인덱스
    corpus = [tok(s["title"] + " " + s["abstract"]) for s in seeds]
    bm = BM25(corpus)

    # 신규 후보 수집 (--reuse 면 캐시 사용)
    raw_path = os.path.join(OUT, "candidates_raw.json")
    if args.reuse and os.path.exists(raw_path):
        cands = [c for c in json.load(open(raw_path, encoding="utf-8"))["items"]
                 if args.repeat or c["id"] not in briefed_ids()]
        print(f"캐시 재사용: 후보 {len(cands)}편")
        seen = set(seed_ids) | {c["id"] for c in cands}
        return rank_and_dump(cands, bm, args)
    already = set() if args.repeat else briefed_ids()
    if already:
        print(f"이미 브리핑한 논문 {len(already)}편 제외")
    # 매일 전체 질의를 다 던지면 요청이 많아 429 를 맞는다.
    # 날짜로 회전시켜 하루 4개만 쓴다. 열흘이면 한 바퀴 돈다.
    k = args.queries
    start = (int(time.time() // 86400) * k) % len(QUERIES)
    todays = [QUERIES[(start + i) % len(QUERIES)] for i in range(k)]
    print(f"오늘의 질의 {k}개: {', '.join(todays)}")
    deadline = time.time() + BUDGET
    seen, cands = set(seed_ids) | already, []
    for q in todays:
        cat = " OR ".join(f"cat:{c}" for c in CATS)
        root = fetch({"search_query": f"({cat}) AND all:\"{q}\"",
                      "sortBy": "submittedDate", "sortOrder": "descending",
                      "max_results": 40}, deadline=deadline)
        for e in parse_entries(root):
            if e["id"] in seen:
                continue
            seen.add(e["id"])
            e["matched_query"] = q
            cands.append(e)
        time.sleep(GAP)
    # 이전 수집분과 합친다(회전 질의라 하루치만으로는 얇다)
    if os.path.exists(raw_path):
        try:
            old = json.load(open(raw_path, encoding="utf-8"))["items"]
            have = {c["id"] for c in cands}
            cands += [c for c in old if c["id"] not in have][:400]
        except Exception:
            pass
    dump("candidates_raw.json", {"items": cands})
    return rank_and_dump(cands, bm, args)


def rank_and_dump(cands, bm, args):
    cutoff = time.strftime("%Y-%m-%d", time.gmtime(time.time() - args.days * 86400))
    fresh = [c for c in cands if max(c["published"], c["updated"]) >= cutoff]
    pool = fresh or cands            # 신규가 없으면 전체에서 고른다
    for c in pool:
        c["score"] = round(bm.score(tok(c["title"] + " " + c["abstract"])), 2)
    pool.sort(key=lambda c: -c["score"])
    top = pool[:args.top]

    dump("candidates.json", {"cutoff": cutoff, "fetched": len(cands),
                             "fresh": len(fresh), "items": top})
    print(f"후보 {len(cands)}편 수집 · {cutoff} 이후 신규 {len(fresh)}편 · 상위 {len(top)}편 선별")
    for c in top:
        print(f"  {c['score']:6.2f}  {c['published']}  {c['title'][:64]}")


if __name__ == "__main__":
    main()
