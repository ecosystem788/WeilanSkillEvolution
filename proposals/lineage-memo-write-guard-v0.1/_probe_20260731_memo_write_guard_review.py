"""Read-only review probe for Codex's 2026-07-31T14:32:30+09:00 proposal
(fail-closed write guard: refuse persistent write while a derivation memo is active).

Only reads and AST-parses the live deployed Skill scripts. Writes nothing but its own
.out.json next to itself. Verifies three claims Codex asked me to check independently,
plus the false-positive risk Codex did not ask about (does any memoized derivation
transitively reach a guarded writer?).
"""
import ast
import hashlib
import json
import os
import sys

SCRIPTS = r"C:\Users\zy\.claude\skills\solve-with-weilan\scripts"
TARGETS = ["weilan_trace.py", "transaction.py", "runtime_core.py"]

GUARD = "assert_transaction_write_allowed"
SIX = [
    "command_metabolic_prepare",
    "command_metabolic_commit",
    "command_metabolic_abort",
    "command_metabolic_recover",
    "materialize_transition_args",
    "command_metabolic_run",
]
# names that mean "this touches durable state"
WRITE_HINTS = (
    "append_event",
    "append_governance_event",
    "write_json",
    "atomic_write",
    "write_text",
    "os.replace",
    "commit",
    "stage",
    "materialize",
)


def sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def load(path):
    with open(path, "r", encoding="utf-8") as fh:
        src = fh.read()
    return src, ast.parse(src)


def called_names(node):
    """All dotted call targets syntactically inside node."""
    out = []
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Name):
                out.append(f.id)
            elif isinstance(f, ast.Attribute):
                base = f.value
                if isinstance(base, ast.Name):
                    out.append(base.id + "." + f.attr)
                else:
                    out.append("." + f.attr)
    return out


def funcs_of(tree):
    d = {}
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            d.setdefault(n.name, []).append(n)
    return d


def first_stmt_guard_position(fn, guard):
    """Index of the top-level statement containing the guard call, and what
    statements precede it (as source-kind labels)."""
    for i, stmt in enumerate(fn.body):
        if guard in called_names(stmt):
            preceding = []
            for s in fn.body[:i]:
                if isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant):
                    preceding.append("docstring")
                else:
                    preceding.append(type(s).__name__ + "@L" + str(s.lineno))
            return {"stmt_index": i, "lineno": stmt.lineno, "preceding": preceding}
    return None


def main():
    result = {"scripts_dir": SCRIPTS, "hashes": {}, "checks": {}}
    trees = {}
    for name in TARGETS:
        p = os.path.join(SCRIPTS, name)
        if not os.path.exists(p):
            result["hashes"][name] = None
            continue
        result["hashes"][name] = sha(p)
        src, tree = load(p)
        trees[name] = (src, tree)

    wt_src, wt = trees["weilan_trace.py"]
    wt_funcs = funcs_of(wt)

    # ---- claim 1: are the six the complete guarded set, and is the guard first? ----
    guarded = {}
    for fname, defs in wt_funcs.items():
        for fn in defs:
            pos = first_stmt_guard_position(fn, GUARD)
            if pos:
                guarded.setdefault(fname, []).append(dict(pos, def_lineno=fn.lineno))
    result["checks"]["guard_call_sites"] = guarded
    result["checks"]["guarded_set_equals_six"] = sorted(guarded) == sorted(SIX)
    result["checks"]["six_missing_guard"] = [n for n in SIX if n not in guarded]
    result["checks"]["guard_extra_beyond_six"] = [n for n in guarded if n not in SIX]

    # is the guard the first non-docstring statement in each?
    not_first = {}
    for fname, hits in guarded.items():
        for h in hits:
            pre = [p for p in h["preceding"] if p != "docstring"]
            if pre:
                not_first[fname] = pre
    result["checks"]["guard_not_first_statement"] = not_first

    # ---- claim 1b: transaction.py writers reachable from weilan_trace w/o guard ----
    tx_src, tx = trees["transaction.py"]
    tx_funcs = funcs_of(tx)
    tx_public = [n for n in tx_funcs if not n.startswith("_")]
    # which weilan_trace functions call transaction.<something> / imported tx names
    tx_callers = {}
    for fname, defs in wt_funcs.items():
        for fn in defs:
            calls = called_names(fn)
            hits = sorted({c for c in calls
                           if c.startswith("transaction.")
                           or c.split(".")[-1] in tx_public and c.startswith("transaction")})
            if hits:
                tx_callers.setdefault(fname, sorted(set(hits)))
    result["checks"]["weilan_trace_funcs_calling_transaction_module"] = tx_callers
    result["checks"]["transaction_callers_not_guarded"] = {
        k: v for k, v in tx_callers.items() if k not in guarded
    }

    # ---- claim 2: does command_open_lineaged_fenced actually append? ----
    fenced = wt_funcs.get("command_open_lineaged_fenced", [])
    fenced_info = []
    for fn in fenced:
        calls = called_names(fn)
        fenced_info.append({
            "def_lineno": fn.lineno,
            "end_lineno": getattr(fn, "end_lineno", None),
            "calls_append_event": "append_event" in calls,
            "write_ish_calls": sorted({c for c in calls
                                       if any(h in c for h in WRITE_HINTS)}),
            "first_stmts": [type(s).__name__ + "@L" + str(s.lineno) for s in fn.body[:6]],
        })
    result["checks"]["command_open_lineaged_fenced"] = fenced_info

    # every weilan_trace function that calls append_event directly
    append_callers = sorted({fname for fname, defs in wt_funcs.items()
                             for fn in defs if "append_event" in called_names(fn)})
    result["checks"]["direct_append_event_callers"] = append_callers

    gov_callers = sorted({fname for fname, defs in wt_funcs.items()
                          for fn in defs
                          if "append_governance_event" in called_names(fn)})
    result["checks"]["append_governance_event_callers"] = gov_callers

    # ---- claim 3: governance append memo exception ----
    gov = wt_funcs.get("append_governance_event", [])
    gov_info = []
    for fn in gov:
        seg = ast.get_source_segment(wt_src, fn) or ""
        gov_info.append({
            "def_lineno": fn.lineno,
            "mentions_DERIVATION_MEMO": "_DERIVATION_MEMO" in seg,
            "memo_lines": [l.strip() for l in seg.splitlines()
                           if "_DERIVATION_MEMO" in l or "memo" in l.lower()][:20],
        })
    result["checks"]["append_governance_event"] = gov_info

    # ---- FALSE-POSITIVE RISK: can a memoized derivation reach a guarded writer? ----
    memoized = []
    for fname, defs in wt_funcs.items():
        for fn in defs:
            for dec in fn.decorator_list:
                nm = dec.id if isinstance(dec, ast.Name) else getattr(dec, "attr", None)
                if nm == "memoized_derivation":
                    memoized.append({"name": fname, "lineno": fn.lineno})
    result["checks"]["memoized_functions"] = memoized

    # build a static call graph over weilan_trace only
    graph = {}
    for fname, defs in wt_funcs.items():
        s = set()
        for fn in defs:
            s.update(called_names(fn))
        graph[fname] = s

    danger = set(SIX) | {"command_open_lineaged_fenced", "append_event"}
    danger |= set(tx_public)

    def reach(start, limit=4000):
        seen, stack, paths = set(), [(start, [start])], []
        while stack:
            cur, path = stack.pop()
            if cur in seen or len(seen) > limit:
                continue
            seen.add(cur)
            for callee in graph.get(cur, ()):
                base = callee.split(".")[-1]
                if base in danger:
                    paths.append(path + [callee])
                if base in graph and base not in seen:
                    stack.append((base, path + [base]))
        return paths

    fp = {}
    for m in memoized:
        p = reach(m["name"])
        if p:
            fp[m["name"]] = [" -> ".join(x) for x in p][:12]
    result["checks"]["memoized_reaching_write_paths"] = fp

    # who calls derivation_memo_scope (Codex claims memoized_derivation is the only one)
    scope_callers = sorted({fname for fname, defs in wt_funcs.items()
                            for fn in defs
                            if "derivation_memo_scope" in called_names(fn)})
    result["checks"]["derivation_memo_scope_callers"] = scope_callers
    # module-level (non-function) uses too
    result["checks"]["derivation_memo_scope_textual_hits"] = [
        i + 1 for i, l in enumerate(wt_src.splitlines())
        if "derivation_memo_scope" in l
    ]

    out = os.path.splitext(os.path.abspath(__file__))[0] + ".out.json"
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2, sort_keys=True)
    print(out)
    json.dump(result["checks"], sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()
