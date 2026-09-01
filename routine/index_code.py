#!/usr/bin/env python3
"""코드 인덱싱 (LLM 미사용).

stdlib 정규식으로 심볼·CLI 플래그·주석 용어를 뽑는다.
tree-sitter 를 쓸 수 있게 되면 symbols() 만 교체하면 된다 (인터페이스 고정).
출력: out/code.json
"""
import re
import sys
from collections import Counter

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common import CODE_DIRS, CODE_EXT, dump, git, head_sha, norm, read, walk  # noqa: E402

# C/C++ 함수·메서드 정의: 'Type Class::name(args) {' 형태의 시작 줄
CPP_FUNC = re.compile(
    r"^[A-Za-z_][\w:<>,\s\*&]*?\b([A-Za-z_]\w*(?:::[A-Za-z_]\w*)?)\s*\([^;]*\)\s*(?:const\s*)?\{\s*$")
PY_FUNC = re.compile(r"^\s*(?:def|class)\s+([A-Za-z_]\w*)")
SH_FUNC = re.compile(r"^\s*([A-Za-z_]\w*)\s*\(\)\s*\{")
CPP_TYPE = re.compile(r"^\s*(?:class|struct|enum(?:\s+class)?)\s+([A-Za-z_]\w*)")
FLAG = re.compile(r'"(--[a-z][a-z0-9-]+)"')
COMMENT = re.compile(r"//\s*(.+)$|#\s+(.+)$")
TECH = re.compile(r"\b(?:[A-Z][A-Za-z]*[A-Z][A-Za-z0-9]*|[A-Z]{2,6}|[a-z]+(?:-[a-z]+)+)\b")
CAMEL_SPLIT = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")

SKIP_NAMES = {"if", "for", "while", "switch", "catch", "return", "sizeof", "else"}


def split_symbol(name):
    """sliceKvCache -> ['slice','Kv','Cache'] 를 다시 붙여 검색 가능한 용어로."""
    base = name.split("::")[-1]
    parts = [p for p in CAMEL_SPLIT.split(base) if p]
    return " ".join(parts)


def main():
    files, symbols, flags, comment_terms = [], [], {}, Counter()

    # 파일별 변경 빈도 (중요도 신호)
    churn = Counter()
    for line in git("log", "--format=", "--name-only").split("\n"):
        line = line.strip()
        if line:
            churn[line] += 1

    for d in CODE_DIRS:
        for rel, full in walk(d, CODE_EXT):
            text = read(full)
            lines = text.split("\n")
            files.append({"path": rel, "loc": len(lines), "churn": churn.get(rel, 0)})
            for i, line in enumerate(lines, 1):
                m = CPP_FUNC.match(line) or SH_FUNC.match(line)
                if m and m.group(1) not in SKIP_NAMES:
                    symbols.append({"name": m.group(1), "kind": "func",
                                    "file": rel, "line": i})
                elif PY_FUNC.match(line):
                    symbols.append({"name": PY_FUNC.match(line).group(1),
                                    "kind": "func", "file": rel, "line": i})
                elif CPP_TYPE.match(line):
                    symbols.append({"name": CPP_TYPE.match(line).group(1),
                                    "kind": "type", "file": rel, "line": i})
                for f in FLAG.findall(line):
                    e = flags.setdefault(f, {"flag": f, "sites": []})
                    e["sites"].append({"file": rel, "line": i})
                cm = COMMENT.search(line)
                if cm:
                    body = cm.group(1) or cm.group(2) or ""
                    for t in TECH.findall(body):
                        if 2 <= len(t) <= 40:
                            comment_terms[t] += 1

    # 코드에서 유래한 용어를 두 갈래로 나눈다.
    #   symbol_terms  : 함수·타입 이름 (신뢰도 높음, G1 의 근거)
    #   comment_terms : 주석 속 기술 용어 (린트 지시어 등 잡음이 많음)
    symbol_terms = {}
    for s in symbols:
        term = split_symbol(s["name"])
        if len(term) <= 3:
            continue
        e = symbol_terms.setdefault(norm(term), {"term": s["name"], "split": term,
                                                 "count": 0, "file": s["file"],
                                                 "line": s["line"]})
        e["count"] += 1
    code_terms = Counter({t: n for t, n in comment_terms.items()})
    for k, e in symbol_terms.items():
        code_terms[e["term"]] += e["count"]

    out = {
        "head_sha": head_sha(),
        "files": sorted(files, key=lambda f: -f["churn"]),
        "symbols": symbols,
        "flags": sorted(flags.values(), key=lambda f: f["flag"]),
        "symbol_terms": symbol_terms,
        "code_terms": {norm(t): {"term": t, "count": n}
                       for t, n in code_terms.most_common() if norm(t)},
    }
    path = dump("code.json", out)
    print(f"코드 파일     {len(files):5d}개  ({sum(f['loc'] for f in files):,}줄)")
    print(f"심볼          {len(symbols):5d}개")
    print(f"CLI 플래그    {len(flags):5d}개")
    print(f"심볼 용어     {len(symbol_terms):5d}개")
    print(f"코드 용어     {len(out['code_terms']):5d}개  (주석 포함)")
    top = [f"{f['path']}({f['churn']})" for f in out["files"][:5]]
    print("변경 잦은 파일 " + ", ".join(top))
    print(f"-> {path}")


if __name__ == "__main__":
    main()
