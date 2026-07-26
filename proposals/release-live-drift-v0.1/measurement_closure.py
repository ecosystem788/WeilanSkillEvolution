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
  * Reference construction is guarded on two channels, and only one of them is
    closed.  Bare names are checked against an allow-list: every free name in the
    reached definitions (and in module-level statements that bind nothing, since
    those run at import and can rebind a root) must be module-bound, locally bound,
    or listed.  Anything else -- getattr, __import__, exec, a builtin nobody has
    ruled on -- makes the result unknown and is named in the report.  That channel
    is complete: an unlisted name cannot pass.  The attribute channel is not.
    Reflection reached through an imported module (sys.modules[...], importlib) is
    only detected by a named, admittedly partial list of paths, and reflection
    written some third way is not detected at all.
  * Consequently a hash never establishes that execution reaches *only* the hashed
    definitions.  It establishes that those definitions are textually identical.
    The gap is real and was found by counterexample, not by reasoning: a module
    whose root called getattr(sys.modules[__name__], name) returned 1 in one
    revision and 2 in the next while this tool reported the same hash under its
    previous guard.  The guard now catches that particular shape twice over; it is
    not thereby proved to catch every shape.
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

# Free names the walk is willing to see and keep going.  The selection rule is narrow:
# a listed name returns data, and cannot hand back a callable drawn from this module's
# own namespace.  getattr/setattr/globals/vars/locals/eval/exec/compile/__import__/dir/
# super/type are all absent on purpose -- each can.  Absence is not a verdict about a
# name, it is a refusal to guess: an unlisted name makes the result unknown and appears
# in the report, so the list grows by decision rather than by drift.
ALLOWED_FREE_NAMES = frozenset({
    # data and iteration
    "abs", "all", "any", "bool", "bytes", "dict", "divmod", "enumerate", "filter",
    "float", "format", "frozenset", "hash", "hasattr", "id", "int", "isinstance",
    "issubclass", "iter", "len", "list", "map", "max", "min", "next", "open", "ord",
    "chr", "print", "range", "repr", "reversed", "round", "set", "slice", "sorted",
    "str", "sum", "tuple", "zip",
    # exceptions, which are raised and caught, never called to reach code
    "AttributeError", "Exception", "FileNotFoundError", "IndexError", "KeyError",
    "NotImplementedError", "OSError", "RuntimeError", "StopIteration", "SystemExit",
    "TypeError", "ValueError",
    # a string, not a reference; the `if __name__ == "__main__"` guard is universal.
    # Using it to index a module registry is caught on the attribute channel below.
    "__name__",
})

# The attribute channel.  Unlike the allow-list above this list is *not* complete and
# cannot be made complete -- an imported module can offer reflection under any name.
# It is here because the shapes that actually appear are worth catching, and because a
# named partial detector is honester than an unstated assumption.
REFLECTIVE_ATTRIBUTE_PATHS = (
    ("sys", "modules"),
    ("builtins", None),
    ("importlib", None),
    ("inspect", "getmembers"),
)


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


def _locally_bound(node: ast.AST) -> set[str]:
    """Names bound anywhere inside this statement.

    Python's own scope rule is used deliberately: a name assigned anywhere in a
    function body is local to it, branch or no branch.  So this is not a loose
    over-approximation -- it is the same rule the interpreter applies.
    """
    out = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name) and isinstance(sub.ctx, (ast.Store, ast.Del)):
            out.add(sub.id)
        elif isinstance(sub, ast.arg):
            out.add(sub.arg)
        elif isinstance(sub, ast.alias):
            out.add(sub.asname or sub.name.split(".")[0])
        elif isinstance(sub, ast.ExceptHandler) and sub.name:
            out.add(sub.name)
        elif isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.add(sub.name)
    return out


def _reflective_paths(node: ast.AST) -> set[str]:
    """Attribute accesses matching the partial reflection list, as dotted text."""
    out = set()
    for sub in ast.walk(node):
        if not isinstance(sub, ast.Attribute) or not isinstance(sub.value, ast.Name):
            continue
        for base, attr in REFLECTIVE_ATTRIBUTE_PATHS:
            if sub.value.id == base and attr in (None, sub.attr):
                out.add(f"{sub.value.id}.{sub.attr}")
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

    missing_roots = [r for r in roots if r not in binders]

    # Statements that bind nothing still run at import, so they can rebind a root
    # before the measurement ever calls it.  They are guarded, not hashed.
    unbound_stmts = [s for s in tree.body if not _binder_name(s)]

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

    guarded = list(reached.values()) + unbound_stmts
    unresolved: set[str] = set()
    reflective: set[str] = set()
    for stmt in guarded:
        free = _referenced_names(stmt) - _locally_bound(stmt)
        unresolved |= {
            n for n in free if n not in binders and n not in ALLOWED_FREE_NAMES
        }
        reflective |= _reflective_paths(stmt)

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
        "reference_guard": {
            "name_channel": {
                "policy": "allow-list; an unlisted free name yields unknown",
                "complete": True,
                "scopes_checked": {
                    "reached_definitions": len(reached),
                    "unbound_module_statements": len(unbound_stmts),
                },
                "unresolved_names": sorted(unresolved),
            },
            "attribute_channel": {
                "policy": "named partial list of reflective paths",
                "complete": False,
                "paths_found": sorted(reflective),
            },
            "verdict": "unbounded" if (unresolved or reflective) else "bounded_on_the_name_channel_only",
        },
    }
    if missing_roots:
        result["closure_sha256"] = "unknown"
        result["unknown_reason"] = "declared root not found at module level"
    elif unresolved or reflective:
        result["closure_sha256"] = "unknown"
        result["unknown_reason"] = (
            "a reference can be constructed here that the walk cannot follow: "
            + ", ".join(sorted(unresolved) + sorted(reflective))
        )
    else:
        result["closure_sha256"] = hashlib.sha256(
            json.dumps(material, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
    result["authority"] = (
        "sufficient only, source-text axis; equal hash => the reached definitions are "
        "textually identical after normalisation; unequal => nothing established. "
        "It does NOT follow that execution reaches only those definitions: the name "
        "channel is closed but the attribute channel is a partial detector, so an "
        "undetected reflection can run code the hash never saw. Execution semantics "
        "(interpreter, filesystem) are a separate axis and are not covered here."
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
