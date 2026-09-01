#!/usr/bin/env python3
"""research/*.md 를 결정론적으로 파싱한다 (LLM 미사용).

prefill-opt 노트의 실제 관습에서 뽑아낸 규칙:
  개념 헤딩      '## 1-3. Attention', '## TTFT (Time To First Token)'
  개념 링크      '← 이어짐: [양자화](#4-1-양자화가-하는-일), [PP](#5-3-pp)'
  코드 근거      01-code-map.md 의 표: | 개념 | `dllama.cpp:414~530` | 메모 |
  논문 시드      refs.md 의 arXiv/DOI 링크
  학습 경로      04-reading-path.md 의 'Stage N' + ★/○/△
  가설           00-RESEARCH-PLAN.md 의 H1~H5
출력: out/notes.json
"""
import re
import sys
from collections import defaultdict

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common import NOTE_DIR, dump, head_sha, norm, read, strip_md, walk  # noqa: E402

# 개념 사전 역할의 문서 — 여기의 헤딩만 '정의된 개념'으로 신뢰한다.
# 그 외 문서의 헤딩은 섹션 제목일 확률이 높아 개념으로 채택하지 않는다.
CONCEPT_DOCS = ("08-glossary.md", "02-glossary-extra.md",
                "03-glossary-full.md", "04-concepts.md")

# ---- 헤딩에서 개념을 골라내는 규칙 -------------------------------------------
NUM_PREFIX = re.compile(r"^\d+(?:[-.]\w+)*\.\s*")          # '1-3. ', '4-1. '
SECTION_WORDS = ("part", "목차", "부록", "요약", "참고", "정리", "짝이 되는")
# 한국어 서술형 어미로 끝나면 개념명이 아니라 문장 제목이다
SENTENCE_END = re.compile(r"(다|까|나|가|요|자|음|함|짓|봄|것|점)$")
VERBISH = re.compile(r"(하는|되는|이란|인가|왜 |어떻게|무엇|어디|언제|그리고|라면)")
# 섹션 제목의 표식: 부제 대시, 콜론, 번호 목록, '~부.'
SECTIONISH = re.compile(r"[—–:：#]|^\d+부\.|^\d+\s|발견\s*#|Stage\s")
# 개념이 아니라 '용어 묶음'의 제목인 것들
#   '알고리즘 용어', '시스템·측정 용어', '통신·배리어', 'E. 방법론·기반'
CATEGORY = re.compile(r"·|^[A-Z]\.\s|(용어|가이드|기호표|목록|정리|기반|조건)$")
# 너무 일반적이라 학습 대상이 될 수 없는 낱말
GENERIC = {"모델", "성능", "알고리즘", "체제", "문제 설정", "미해결", "선행 조건",
           "세 가지 결론", "예외", "요약", "개요", "배경", "정의", "결론",
           "리스크", "하드웨어", "에너지", "일반화", "진행 순서", "운영 규칙",
           "워크로드", "실측", "관찰", "가정", "제약", "목표", "범위"}


def heading_to_concept(text):
    """헤딩 문자열 -> [(개념명, 별칭들), ...] 또는 None

    노트의 헤딩은 개념명이기도 하고 섹션 제목이기도 하다.
    걸러내는 순서가 중요하다 — 괄호를 벗기고 병렬을 분해한 *뒤에도*
    같은 필터를 다시 적용해야 '모델 (Llama-3)' 의 '모델' 이 새지 않는다.
    """
    t = strip_md(text)
    t = NUM_PREFIX.sub("", t).strip()
    if not t or len(t) > 40:
        return None

    # 괄호는 별칭으로 뗀다: 'GQA (Grouped-Query Attention)'
    aliases = []
    m = re.match(r"^([^(]+)\(([^)]+)\)\s*$", t)
    if m:
        head, alias = m.group(1).strip(), m.group(2).strip()
        if head:
            t = head
            if len(alias) < 40:
                aliases.append(alias)

    def acceptable(x):
        if not x or len(x) > 40:
            return False
        low = x.lower()
        if any(w in low for w in SECTION_WORDS):
            return False
        if VERBISH.search(x) or SECTIONISH.search(x) or CATEGORY.search(x):
            return False
        if x in GENERIC or low in GENERIC:
            return False
        if len(x.split()) >= 4:
            return False
        # 한글만으로 된 서술형 제목 ('깊이는 순차다', '버블은 정량화된다')
        if SENTENCE_END.search(x) and not re.search(r"[A-Za-z]", x) \
                and len(x.split()) >= 2:
            return False
        return True

    # 병렬 헤딩을 조각낸다: 'all-reduce / ring / P2P', 'FFN 와 SwiGLU'
    parts = [p.strip() for p in t.split("/") if p.strip()]
    if len(parts) == 1:
        m = re.match(r"^(.{2,20}?)\s*(?:와|과)\s+(.{2,20})$", t)
        if m:
            parts = [m.group(1).strip(), m.group(2).strip()]
    if len(parts) > 1:
        keep = [p for p in parts if len(p) <= 24 and acceptable(p)]
        return [(p, []) for p in keep] if keep else None

    return [(t, aliases)] if acceptable(t) else None


# ---- 본문에서 '언급된 용어' 후보를 뽑는 규칙 --------------------------------
INLINE_CODE = re.compile(r"`([^`\n]{2,40})`")
BOLD = re.compile(r"\*\*([^*\n]{2,40})\*\*")
TECH = re.compile(r"\b(?:[A-Z][A-Za-z]*[A-Z][A-Za-z0-9]*|[A-Z]{2,6}|[a-z]+(?:-[a-z]+)+)\b")
CODEISH = re.compile(r"[(){};=/\\]|\.(cpp|hpp|py|sh|tsv|log|md)\b|^--|^-[a-z]$")


def mention_candidates(body):
    """(용어, 강조여부) 집합. 강조 = 노트가 인라인코드/굵게로 표시한 것.

    노트가 강조한 용어는 '저자가 용어로 취급한 것'이라는 뜻이므로,
    단순 대문자 토큰(CPU, GPU)보다 개념일 확률이 훨씬 높다.
    """
    emph, plain = set(), set()
    for pat in (INLINE_CODE, BOLD):
        for m in pat.finditer(body):
            s = strip_md(m.group(1)).strip()
            if 2 <= len(s) <= 40 and not CODEISH.search(s):
                emph.add(s)
    for m in TECH.finditer(body):
        s = m.group(0)
        if 2 <= len(s) <= 40 and s not in emph:
            plain.add(s)
    return emph, plain


LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
NEXT_LINE = re.compile(r"^←\s*(?:이어짐|이어지는 개념)\s*[:：]?\s*(.*)$")
CODEREF = re.compile(r"`([A-Za-z0-9_./-]+\.(?:cpp|hpp|h|c|py|sh))(?::(\d+)(?:[~\-](\d+))?)?`")
ARXIV = re.compile(r"arxiv\.org/(?:abs|pdf|html)/(\d{4}\.\d{4,5})")
ARXIV_ID = re.compile(r"arXiv[:\s]+(\d{4}\.\d{4,5})")
DOI = re.compile(r"doi\.org/(10\.[^\s)\]]+)")
STAGE = re.compile(r"^#{2,3}\s*Stage\s+(\d+)\s*[—\-–]?\s*(.*)$")
HYP = re.compile(r"\b(H[1-9])\b")


def main():
    concepts = {}          # key(norm) -> dict
    links = []             # (from_key, to_text, doc)
    mentions = defaultdict(lambda: {"docs": set(), "emph": 0, "term": ""})
    evidence = []          # 코드맵 표에서 나온 개념->파일:줄
    papers = {}            # arxiv_id/doi -> dict
    stages = []            # 학습 경로
    hypotheses = {}
    docs = []

    for rel, full in walk(NOTE_DIR, (".md",)):
        text = read(full)
        docs.append({"path": rel, "lines": text.count("\n") + 1,
                     "title": next((strip_md(l[2:]) for l in text.split("\n")
                                    if l.startswith("# ")), rel)})
        is_concept_doc = rel.endswith(CONCEPT_DOCS)
        cur_key = None
        pending_link_from = None       # '← 이어짐:' 이 여러 줄에 걸칠 때
        for i, line in enumerate(text.split("\n"), 1):
            hm = re.match(r"^(#{1,4})\s+(.*)$", line)
            if hm:
                sm = STAGE.match(line)
                if sm and "reading-path" in rel:
                    stages.append({"stage": int(sm.group(1)),
                                   "title": strip_md(sm.group(2)),
                                   "doc": rel, "line": i})
                got = heading_to_concept(hm.group(2)) if is_concept_doc else None
                cur_key = None
                if got:
                    for name, aliases in got:
                        k = norm(name)
                        if not k:
                            continue
                        cur_key = k
                        c = concepts.setdefault(k, {
                            "key": k, "name": name, "aliases": [],
                            "defs": [], "evidence": []})
                        for a in aliases:
                            if a not in c["aliases"]:
                                c["aliases"].append(a)
                        c["defs"].append({"doc": rel, "line": i,
                                          "level": len(hm.group(1))})
                continue

            nm = NEXT_LINE.match(line.strip())
            if nm and cur_key:
                pending_link_from = cur_key
                rest = nm.group(1)
            elif pending_link_from and line.strip().startswith("["):
                rest = line.strip()          # 앞 줄에서 이어진 링크 목록
            else:
                pending_link_from = None
                rest = None
            if rest is not None:
                for text_, href in LINK.findall(rest):
                    links.append({"from": pending_link_from,
                                  "to_text": strip_md(text_),
                                  "to_key": norm(strip_md(text_)),
                                  "doc": rel, "line": i, "kind": "next"})
                if not rest.rstrip().endswith(","):
                    pending_link_from = None

            # 코드맵 표: | 개념 | `file:line~line` | 메모 |
            if rel.endswith("01-code-map.md") and line.startswith("|"):
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if len(cells) >= 2:
                    cm = CODEREF.search(cells[1])
                    if cm:
                        name = strip_md(cells[0])
                        if name and len(name) <= 40:
                            evidence.append({
                                "concept_key": norm(name), "concept": name,
                                "file": cm.group(1),
                                "line_start": int(cm.group(2)) if cm.group(2) else None,
                                "line_end": int(cm.group(3)) if cm.group(3) else None,
                                "doc": rel, "doc_line": i,
                                "note": strip_md(cells[2]) if len(cells) > 2 else ""})

            for aid in set(ARXIV.findall(line)) | set(ARXIV_ID.findall(line)):
                p = papers.setdefault("arXiv:" + aid, {
                    "source": "arxiv", "external_id": aid, "seen": []})
                p["seen"].append({"doc": rel, "line": i})
                if line.strip().startswith("|"):
                    cells = [c.strip() for c in line.strip().strip("|").split("|")]
                    if cells:
                        p.setdefault("note_title", strip_md(cells[0]))
                        if len(cells) > 2:
                            p.setdefault("note_gap", strip_md(cells[2]))
            for d in DOI.findall(line):
                papers.setdefault("doi:" + d, {"source": "doi", "external_id": d,
                                               "seen": []})["seen"].append(
                    {"doc": rel, "line": i})

            if "RESEARCH-PLAN" in rel:
                # 표의 첫 칸이 'H3' 인 줄이 그 가설의 정의다.
                # 단순 첫 등장을 쓰면 H1 설명 안에 언급된 'H3' 가 잡힌다.
                cells = [c.strip() for c in line.strip().strip("|").split("|")] \
                    if line.strip().startswith("|") else []
                own = strip_md(cells[0]) if cells else ""
                for h in HYP.findall(line):
                    prev = hypotheses.get(h)
                    is_def = own == h
                    if prev is None or (is_def and not prev.get("is_def")):
                        hypotheses[h] = {"id": h, "doc": rel, "line": i,
                                         "is_def": is_def,
                                         "context": strip_md(line)[:220]}

        emph, plain = mention_candidates(text)
        for term in emph | plain:
            k = norm(term)
            if not k:
                continue
            e = mentions[k]
            e["docs"].add(rel)
            e["term"] = e["term"] or term
            if term in emph:
                e["emph"] += 1

    # 정의된 개념에 코드 근거 붙이기
    for e in evidence:
        c = concepts.get(e["concept_key"])
        if c:
            c["evidence"].append(e)

    out = {
        "head_sha": head_sha(),
        "docs": sorted(docs, key=lambda d: -d["lines"]),
        "concepts": sorted(concepts.values(), key=lambda c: c["key"]),
        "links": links,
        "mentions": {k: {"term": v["term"], "docs": sorted(v["docs"]),
                         "emph": v["emph"]}
                     for k, v in sorted(mentions.items())},
        "evidence": evidence,
        "papers": papers,
        "stages": stages,
        "hypotheses": hypotheses,
    }
    path = dump("notes.json", out)
    print(f"노트 문서      {len(docs):5d}개  ({sum(d['lines'] for d in docs):,}줄)")
    print(f"정의된 개념    {len(concepts):5d}개")
    print(f"개념 링크      {len(links):5d}개")
    print(f"코드 근거      {len(evidence):5d}개  (01-code-map.md)")
    print(f"언급 용어 후보 {len(mentions):5d}개")
    print(f"논문 시드      {len(papers):5d}편")
    print(f"학습 경로      {len(stages):5d} Stage")
    print(f"가설           {len(hypotheses):5d}개  {', '.join(sorted(hypotheses))}")
    print(f"-> {path}")


if __name__ == "__main__":
    main()
