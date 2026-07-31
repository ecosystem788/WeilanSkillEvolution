"""Read-only probe: independent review of Codex's 2026-07-31T13:23:44+09:00 proposal
(route load_lineage_records through the existing memoized_records).

Verifies the three points Codex asked me to check, against the LIVE deployed skill only.
Writes nothing. Run:
    python _probe_20260731_lineage_memo_safety.py
"""

import ast
import hashlib
import json
import re
from pathlib import Path

LIVE = Path(r"C:/Users/zy/.claude/skills/solve-with-weilan/scripts/weilan_trace.py")

src = LIVE.read_bytes()
tree = ast.parse(src.decode("utf-8"))
lines = src.decode("utf-8").split("\n")

out = {
    "live_path": str(LIVE),
    "live_sha256": hashlib.sha256(src).hexdigest(),
}

# ---- module-level call graph -------------------------------------------------
defs = {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def called_names(node):
    names = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            f = sub.func
            if isinstance(f, ast.Name):
                names.add(f.id)
            elif isinstance(f, ast.Attribute):
                names.add(f.attr)
        elif isinstance(sub, ast.Name):
            # function passed as a value (decorator tables, dispatch dicts, partials)
            names.add(sub.id)
    return names


graph = {name: called_names(node) & set(defs) for name, node in defs.items()}


def decorator_names(node):
    got = set()
    for d in node.decorator_list:
        if isinstance(d, ast.Name):
            got.add(d.id)
        elif isinstance(d, ast.Call) and isinstance(d.func, ast.Name):
            got.add(d.func.id)
        elif isinstance(d, ast.Attribute):
            got.add(d.attr)
    return got


memoized = sorted(n for n, node in defs.items() if "memoized_derivation" in decorator_names(node))
out["memoized_derivation_functions"] = memoized

# ---- point 2a: where can the memo scope be entered at all? -------------------
scope_uses = [
    (i + 1, L.strip())
    for i, L in enumerate(lines)
    if "derivation_memo_scope" in L and not L.lstrip().startswith(("def ", "@", '"""', "#"))
]
out["derivation_memo_scope_call_sites"] = scope_uses

# ---- point 2b: what actually mutates the lineage ledger on disk? -------------
# The ledger read by load_lineage_records is lineage_directory()/ *.jsonl only.
ledger_writers = set()
for name, node in defs.items():
    seg = "\n".join(lines[node.lineno - 1 : (node.end_lineno or node.lineno)])
    if re.search(r"append_event\(\s*lineage_path", seg) or re.search(
        r"write_json_atomic\(\s*lineage_paths", seg
    ):
        ledger_writers.add(name)
out["lineage_ledger_writers"] = sorted(ledger_writers)

# write_lineage_heads targets a DERIVED cache, not a load_lineage_records source.
heads_writers = sorted(n for n, c in graph.items() if "write_lineage_heads" in c)
out["lineage_heads_cache_writers"] = heads_writers
out["heads_cache_is_a_memoized_source"] = "lineage_heads_path" in called_names(
    defs["load_lineage_records"]
)

# ---- point 2c: can any memoized derivation reach a ledger writer? ------------
def reaches(start, targets):
    seen, stack, hits = set(), [start], []
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        for callee in graph.get(cur, ()):
            if callee in targets:
                hits.append((cur, callee))
            stack.append(callee)
    return hits


out["memoized_reaching_ledger_writer"] = {
    fn: reaches(fn, ledger_writers) for fn in memoized if reaches(fn, ledger_writers)
}
out["memoized_reaching_heads_cache_writer"] = {
    fn: reaches(fn, {"write_lineage_heads"})
    for fn in memoized
    if reaches(fn, {"write_lineage_heads"})
}

# ---- point 2d: does the sole ledger writer re-read after its write? ----------
writer_bodies = {}
for name in sorted(ledger_writers):
    node = defs[name]
    seg_lines = lines[node.lineno - 1 : (node.end_lineno or node.lineno)]
    write_at = next(
        (i for i, L in enumerate(seg_lines) if re.search(r"append_event\(\s*lineage_path", L)), None
    )
    reads_after = [
        (node.lineno + i, L.strip())
        for i, L in enumerate(seg_lines)
        if write_at is not None and i > write_at and "load_lineage_records(" in L
    ]
    writer_bodies[name] = {
        "decorated_with": sorted(decorator_names(node)),
        "write_line": node.lineno + write_at if write_at is not None else None,
        "load_lineage_records_calls_after_write": reads_after,
    }
out["sole_writer_read_after_write"] = writer_bodies

# ---- point 1: is load_lineage_records shape-identical to the memoized helper? -
ll = defs["load_lineage_records"]
ls = defs["load_scoped_ledger_records"]
ll_src = "\n".join(lines[ll.lineno - 1 : ll.end_lineno])
ls_src = "\n".join(lines[ls.lineno - 1 : ls.end_lineno])
out["warning_strings"] = {
    "load_lineage_records": re.findall(r'f"\{path\.name\}: ([^"]*)"', ll_src),
    "load_scoped_ledger_records_with_kind_lineage": [
        w.replace("{kind.replace('_', ' ')}", "lineage")
        for w in re.findall(r'f"\{path\.name\}: ([^"]*)"', ls_src)
    ],
}
out["warning_strings"]["identical"] = (
    out["warning_strings"]["load_lineage_records"]
    == out["warning_strings"]["load_scoped_ledger_records_with_kind_lineage"]
)

# memo key granularity vs the identity filter it must not conflate
out["memo_key_vs_filter"] = {
    "memo_key_line": next(
        (i + 1, L.strip()) for i, L in enumerate(lines) if "key = (kind, workspace_key" in L
    ),
    "note": "workspace_key = sha256(normalized_workspace(v))[:16]; scope_key = "
    "sha256(normalize_scope(v).casefold())[:12]. The filter in load_lineage_records "
    "compares exactly normalized_workspace and normalize_scope().casefold(). Same "
    "two values already select lineage_directory(), so a key collision would already "
    "have merged the two ledgers on disk: memoization adds no new conflation.",
}

# ---- point 3: does memoized_records replay warnings verbatim? ----------------
mr = defs["memoized_records"]
out["memoized_records_source"] = "\n".join(lines[mr.lineno - 1 : mr.end_lineno])

# ---- residual: memoized funcs that read lineage today ------------------------
out["memoized_reading_lineage"] = {
    fn: sorted(reaches(fn, {"load_lineage_records"})) for fn in memoized
    if reaches(fn, {"load_lineage_records"})
}

print(json.dumps(out, ensure_ascii=False, indent=2))
