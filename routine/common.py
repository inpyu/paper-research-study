"""공용 유틸 — 표준 라이브러리만 사용한다.

이 서버에는 pip 도, node 도 없다. cron 루틴이 의존성 설치 없이 돌아야 하므로
파서는 전부 stdlib + 정규식으로 구현한다. (tree-sitter 도입은 선택 사항이며,
index_code.py 의 심볼 추출기만 교체하면 된다.)
"""
import json
import os
import re
import subprocess
import unicodedata

REPO = os.environ.get("TARGET_REPO", os.path.expanduser("~/work/prefill-opt"))
OUT = os.environ.get("OUT_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out"))

NOTE_DIR = "research"
CODE_DIRS = ("src", "prefill_bench", "scripts")
CODE_EXT = (".cpp", ".hpp", ".h", ".c", ".py", ".sh")


def repo_path(*parts):
    return os.path.join(REPO, *parts)


def walk(rel_dir, exts=None):
    """레포 상대경로로 파일을 순회한다."""
    root = repo_path(rel_dir)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__")]
        for fn in sorted(filenames):
            if exts and not fn.endswith(exts):
                continue
            full = os.path.join(dirpath, fn)
            yield os.path.relpath(full, REPO), full


def read(full):
    with open(full, encoding="utf-8", errors="replace") as f:
        return f.read()


def git(*args):
    try:
        return subprocess.run(("git", "-C", REPO) + args, capture_output=True,
                              text=True, timeout=60).stdout
    except Exception:
        return ""


def head_sha():
    return git("rev-parse", "HEAD").strip()


# ---------- 용어 정규화 ----------
_WS = re.compile(r"\s+")
_MD = re.compile(r"[*_`\[\]]")


def strip_md(s):
    s = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", s)   # [텍스트](링크) -> 텍스트
    s = _MD.sub("", s)
    return _WS.sub(" ", s).strip()


def norm(term):
    """표기 흔들림 통합: KV-cache / kv cache / KV 캐시 -> kv cache"""
    t = unicodedata.normalize("NFKC", term).lower().strip()
    t = t.replace("캐시", "cache")
    t = re.sub(r"[_\-/]+", " ", t)
    t = re.sub(r"[^0-9a-z가-힣 .+]", " ", t)
    return _WS.sub(" ", t).strip()


def dump(name, obj):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    return p


def load(name):
    with open(os.path.join(OUT, name), encoding="utf-8") as f:
        return json.load(f)
