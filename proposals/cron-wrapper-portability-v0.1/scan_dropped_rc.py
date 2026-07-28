"""Scan for the class Codex named: a module-level bare `main()` whose main()
reports failure via a NON-ZERO RETURN, so the process exits rc 0 regardless.

A bare `main()` is only a dumb-green line if main() signals failure by return
value.  If main() raises / sys.exit()s on failure, rc still bears weight.  So
the predicate is a conjunction, checked on the AST:

  (a) module level (incl. `if __name__ == "__main__":`) calls `main()` or
      `<mod>.main()` NOT wrapped in sys.exit(...)/exit(...), AND
  (b) the resolved main() body contains `return <non-zero-literal>` or
      `return <expr>` that is not a bare `return`/`return None`/`return 0`.

(b) is deliberately loose: any non-constant return is reported as SUSPECT, not
CONFIRMED, because we cannot evaluate it statically.  Nothing here is a verdict;
it is a list of places to look.
"""
import ast
import json
import pathlib
import sys

ROOT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
SKIP_DIRS = {"__pycache__", ".git", "node_modules"}
SKIP_TOP = {"staging", "deployments"}


def is_exit_wrapped(node):
    """True if this Call is sys.exit(main()) / exit(main()) / raise SystemExit(main())."""
    f = node.func
    name = getattr(f, "id", None) or getattr(f, "attr", None)
    return name in {"exit", "_exit"}


def bare_main_calls(tree):
    """Module-level Expr statements that are a bare main()/x.main() call."""
    out = []
    stack = [(s, False) for s in tree.body]
    while stack:
        stmt, _ = stack.pop()
        if isinstance(stmt, ast.If):          # descend into if __name__ == ...
            stack += [(s, True) for s in stmt.body + stmt.orelse]
            continue
        if isinstance(stmt, ast.Try):
            stack += [(s, True) for s in stmt.body]
            continue
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            call = stmt.value
            fname = getattr(call.func, "id", None) or getattr(call.func, "attr", None)
            if fname == "main":
                out.append(stmt.lineno)
    return out


def main_returns_nonzero(tree):
    """Inspect a local `def main(...)`: does it return a value other than None/0?"""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "main":
            verdict = "no-local-main-return"
            for sub in ast.walk(node):
                if isinstance(sub, ast.Return) and sub.value is not None:
                    v = sub.value
                    if isinstance(v, ast.Constant):
                        if v.value not in (None, 0, False):
                            return "CONFIRMED"       # e.g. `return 1`
                        verdict = "returns-zero-only"
                    else:
                        verdict = "SUSPECT"          # e.g. `return 0 if ok else 1`
            return verdict
    return "no-local-main"        # main imported from elsewhere -> look by hand


def walk_py(root):
    """os.walk, not rglob: prunes skipped dirs before descending, and survives
    the deep/vanished paths this repo's fixture trees are full of."""
    import os
    for dirpath, dirnames, filenames in os.walk(root, onerror=lambda e: None):
        rel = pathlib.Path(dirpath).relative_to(root).parts
        dirnames[:] = [
            d for d in dirnames
            if d not in SKIP_DIRS and not (not rel and d in SKIP_TOP)
        ]
        for fn in filenames:
            if fn.endswith(".py"):
                yield pathlib.Path(dirpath) / fn


rows = []
skipped_unreadable = 0
for path in walk_py(ROOT):
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except (SyntaxError, OSError):
        skipped_unreadable += 1
        continue
    calls = bare_main_calls(tree)
    if not calls:
        continue
    # only flag if no sys.exit(main()) anywhere in the module
    if any(
        is_exit_wrapped(n)
        and n.args
        and isinstance(n.args[0], ast.Call)
        and (getattr(n.args[0].func, "id", None) or getattr(n.args[0].func, "attr", None)) == "main"
        for n in ast.walk(tree)
        if isinstance(n, ast.Call)
    ):
        continue
    rows.append({
        "file": str(path.relative_to(ROOT)).replace("\\", "/"),
        "bare_main_lines": calls,
        "main_return_verdict": main_returns_nonzero(tree),
    })

rows.sort(key=lambda r: (r["main_return_verdict"] != "CONFIRMED", r["file"]))
print(json.dumps({"root": str(ROOT), "hits": rows, "count": len(rows),
                  "skipped_unreadable": skipped_unreadable},
                 ensure_ascii=False, indent=1))
