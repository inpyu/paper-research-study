"""tree-sitter 기반 심볼·호출 추출.

정규식 인덱서가 못 하던 두 가지를 얻는다.
  1) 함수의 정확한 범위 (line_start~line_end)  -> 코드 근거 스니펫을 정확히 자른다
  2) 호출 관계 (누가 누구를 부르는가)          -> 실행 경로 페이지(W2)와 참조 중심성

tree_sitter 가 없으면 None 을 돌려주고, index_code.py 가 정규식으로 되돌아간다.
"""
import os

try:
    from tree_sitter import Language, Parser
    import tree_sitter_cpp
    import tree_sitter_python
    OK = True
except ImportError:                                    # pragma: no cover
    OK = False

if OK:
    CPP = Language(tree_sitter_cpp.language())
    PY = Language(tree_sitter_python.language())

NAME_NODES = ("identifier", "qualified_identifier", "field_identifier",
              "destructor_name", "operator_name", "type_identifier")


def _name(node, src):
    """선언자 사슬을 내려가 함수 이름 노드를 찾는다."""
    seen = set()
    stack = [node]
    while stack:
        n = stack.pop()
        if id(n) in seen:
            continue
        seen.add(id(n))
        if n.type in NAME_NODES:
            return src[n.start_byte:n.end_byte].decode("utf-8", "replace")
        for f in ("declarator", "name"):
            c = n.child_by_field_name(f)
            if c is not None:
                stack.append(c)
    return None


def _callee(node, src):
    f = node.child_by_field_name("function")
    if f is None:
        return None
    if f.type in NAME_NODES:
        return src[f.start_byte:f.end_byte].decode("utf-8", "replace")
    if f.type in ("field_expression", "attribute"):
        c = f.child_by_field_name("field") or f.child_by_field_name("attribute")
        if c is not None:
            return src[c.start_byte:c.end_byte].decode("utf-8", "replace")
    return None


def _collect_calls(fn_node, src, out):
    stack = [fn_node]
    while stack:
        n = stack.pop()
        if n.type in ("call_expression", "call"):
            c = _callee(n, src)
            if c:
                out.append((c, n.start_point[0] + 1))
        stack.extend(n.children)


def parse_file(path, rel):
    """-> (symbols, calls) 또는 None"""
    if not OK:
        return None
    ext = os.path.splitext(path)[1]
    if ext in (".cpp", ".hpp", ".h", ".c", ".cc"):
        lang, fn_types, ty_types = CPP, ("function_definition",), \
            ("class_specifier", "struct_specifier", "enum_specifier")
    elif ext == ".py":
        lang, fn_types, ty_types = PY, ("function_definition",), ("class_definition",)
    else:
        return None
    try:
        with open(path, "rb") as f:
            src = f.read()
        tree = Parser(lang).parse(src)
    except Exception:
        return None

    symbols, calls = [], []
    stack = [tree.root_node]
    while stack:
        n = stack.pop()
        if n.type in fn_types:
            nm = _name(n, src)
            if nm:
                sym = {"name": nm, "kind": "func", "file": rel,
                       "line": n.start_point[0] + 1,
                       "line_end": n.end_point[0] + 1}
                symbols.append(sym)
                got = []
                _collect_calls(n, src, got)
                for callee, line in got:
                    calls.append({"from": nm, "from_file": rel,
                                  "to": callee, "line": line})
        elif n.type in ty_types:
            nm = _name(n, src)
            if nm:
                symbols.append({"name": nm, "kind": "type", "file": rel,
                                "line": n.start_point[0] + 1,
                                "line_end": n.end_point[0] + 1})
        stack.extend(n.children)
    return symbols, calls
