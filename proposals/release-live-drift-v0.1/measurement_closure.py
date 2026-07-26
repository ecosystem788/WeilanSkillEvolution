"""Read-only: hash the code a measurement actually reaches, not the file it lives in.

Why this exists.  measure_drift.py's comparison_key includes measurer.sha256, which
pins the whole file.  Editing a docstring therefore mints a new dimension even when
the code that produces the numbers is untouched -- and that has already happened
three times in this file's own history.  The alternative usually proposed is a
hand-declared method_id, but that is an author's claim ("the algorithm did not
change") which a reader cannot check.

This computes the claim instead.  Given a source file and one or more declared root
names, it walks module-level references from those roots, drops docstrings, and
hashes the normalised text of exactly the definitions reached.  What remains an
author's claim shrinks from "the method is unchanged" to "these are the roots" --
which a reader can check by reading the call site.  Nothing is written.

Honest limits, all of them load-bearing:
  * Sufficient only, and only on the source-text axis.  Equal closure hash means the
    reached definitions are textually identical after normalisation.  It says nothing
    about execution semantics (interpreter, filesystem) -- that is a separate axis
    and stays in measure_drift.py's runtime_semantics.
  * The hash is normalised by ast.unparse, whose output is not guaranteed stable
    across Python versions.  Two closure hashes are comparable only under the same
    unparser; the boundary is reported so a reader can refuse the comparison.
  * Dynamic name resolution (exec/eval/globals/vars/locals, or getattr on the module)
    can reach code the walk cannot see.  Any of these anywhere in the module makes
    the result unknown rather than a hash.  Fail closed.
  * Whatever a root does not reach is out of scope by construction, and is listed in
    unreached_module_names so an over-narrow root list is visible, not hidden.

Usage:
  python measurement_closure.py --source measure_drift.py --root collect --root sha256
  python measurement_closure.py --git-rev 8e93653 --git-path proposals/.../measure_drift.py \
      --root collect --root sha256
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Names whose presence anywhere in the module means a reference can be constructed at
# runtime, so a static walk cannot bound what the measurement reaches.
DYNAMIC_NAMES = frozenset({"exec", "eval", "globals", "vars", "locals", "compile"})


def _binder_name(node: ast.stmt) -> list[str]:
    """Module-level names this statement binds, or [] if it binds none."""
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return [node.name]
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        return [alias.asname or alias.name.split(".")[0] for alias in node.names]
    if isinstance(node, ast.Assign):
        names = []
        for target in node.targets:
            if isinstance(target, ast.Name):
                names.append(target.id)
            elif isinstance(target, (ast.Tuple, ast.List)):
                names.extend(e.id for e in target.elts if isinstance(e, ast.Name))
        return names
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return [node.target.id]
    return []


def _strip_docstrings(node: ast.AST) -> ast.AST:
    """Remove docstrings everywhere, so prose edits do not move the hash.

    Comments are already absent -- ast.parse discards them -- which is the point:
    the hash tracks code, and this makes docstrings behave the same way.
    """
    for sub in ast.walk(node):
        if isinstance(sub, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = sub.body
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                sub.body = body[1:] or [ast.Pass()]
    return node


def _referenced_names(node: ast.AST) -> set[str]:
    """Every bare name read inside this statement, including attribute bases."""
    out = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name):
            out.add(sub.id)
    return out


def closure(source: str, roots: list[str]) -> dict:
    tree = ast.parse(source)

    binders: dict[str, ast.stmt] = {}
    order: dict[str, int] = {}
    for index, stmt in enumerate(tree.body):
        for name in _binder_name(stmt):
            # A rebound name keeps its first slot but its latest statement, which is
            # what the module would actually resolve to at import time.
            binders[name] = stmt
            order.setdefault(name, index)

    dynamic_hits = sorted(
        name for name in _referenced_names(tree) if name in DYNAMIC_NAMES
    )
    missing_roots = [r for r in roots if r not in binders]

    reached: dict[str, ast.stmt] = {}
    frontier = [r for r in roots if r in binders]
    while frontier:
        name = frontier.pop()
        if name in reached:
            continue
        stmt = binders[name]
        reached[name] = stmt
        for ref in sorted(_referenced_names(stmt)):
            if ref in binders and ref not in reached:
                frontier.append(ref)

    # One statement can bind several reached names (a shared import line); hash each
    # statement once, labelled by every reached name it binds, so the label set is
    # itself part of what is hashed.
    units = []
    seen_stmts: list[ast.stmt] = []
    for name in sorted(reached, key=lambda n: (order[n], n)):
        stmt = reached[name]
        if any(stmt is s for s in seen_stmts):
            continue
        seen_stmts.append(stmt)
        labels = sorted(n for n in reached if reached[n] is stmt)
        text = ast.unparse(_strip_docstrings(ast.parse(ast.unparse(stmt))))
        units.append({"binds": labels, "normalised": text})

    material = {
        "roots": sorted(roots),
        "units": units,
        "unparser": f"{sys.version_info.major}.{sys.version_info.minor}",
    }
    unreached = sorted(n for n in binders if n not in reached)

    result = {
        "roots_declared": sorted(roots),
        "roots_missing": sorted(missing_roots),
        "reached_names": sorted(reached, key=lambda n: (order[n], n)),
        "unreached_module_names": unreached,
        "unparser_boundary": material["unparser"],
        "dynamic_reference_guard": {
            "names_found": dynamic_hits,
            "verdict": "unbounded" if dynamic_hits else "static",
        },
    }
    if missing_roots:
        result["closure_sha256"] = "unknown"
        result["unknown_reason"] = "declared root not found at module level"
    elif dynamic_hits:
        result["closure_sha256"] = "unknown"
        result["unknown_reason"] = (
            "module can construct references dynamically; a static walk cannot bound "
            "what the measurement reaches"
        )
    else:
        result["closure_sha256"] = hashlib.sha256(
            json.dumps(material, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
    result["authority"] = (
        "sufficient only, source-text axis; equal hash => reached definitions are "
        "textually identical after normalisation; unequal => nothing established. "
        "Execution semantics are a separate axis and are not covered here."
    )
    return result


def _git_show(rev: str, path: str) -> str | None:
    try:
        return subprocess.run(
            ["git", "-C", str(REPO_ROOT), "show", f"{rev}:{path}"],
            capture_output=True, text=True, check=True,
        ).stdout
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", help="path to a source file on disk")
    ap.add_argument("--git-rev", action="append", default=[],
                    help="read the source at this revision instead (repeatable)")
    ap.add_argument("--git-path", help="repo-relative path, required with --git-rev")
    ap.add_argument("--root", action="append", default=[], required=True,
                    help="module-level name the measurement enters through (repeatable)")
    args = ap.parse_args()

    reports = []
    if args.git_rev:
        if not args.git_path:
            print("--git-rev requires --git-path", file=sys.stderr)
            return 2
        for rev in args.git_rev:
            src = _git_show(rev, args.git_path)
            if src is None:
                reports.append({"rev": rev, "path": args.git_path,
                                "closure_sha256": "unknown",
                                "unknown_reason": "git show failed"})
                continue
            report = closure(src, args.root)
            report["rev"] = rev
            report["path"] = args.git_path
            report["file_sha256"] = hashlib.sha256(src.encode("utf-8")).hexdigest()
            reports.append(report)
    else:
        if not args.source:
            print("give --source or --git-rev/--git-path", file=sys.stderr)
            return 2
        raw = Path(args.source).read_bytes()
        report = closure(raw.decode("utf-8"), args.root)
        report["path"] = str(Path(args.source))
        report["file_sha256"] = hashlib.sha256(raw).hexdigest()
        reports.append(report)

    print(json.dumps(reports if len(reports) > 1 else reports[0],
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
