#!/usr/bin/env python3
"""Read-only independent review of commit 1bc5727 (fail() push_attempted required).

Checks, all against git objects and source AST -- no remote, no writes:
  A. blob oids of the two implementation files at the landed commit
  B. authorization locatability: peer-chat blob + the two cited line sha256
  C. AST recount of fail() call sites and their explicit push_attempted values
  D. which fail() sites sit before / after the single git push call expression
  E. which fail() reasons are named anywhere in the test file (call-time reach)
"""

import ast
import hashlib
import json
import subprocess
from pathlib import Path

COMMIT = "1bc57277813442f3648461eebe754b3bbcf3546e"
TOOL = "proposals/charter-daily-push-v0.1/push_authorized_oid.py"
TEST = "proposals/charter-daily-push-v0.1/test_push_authorized_oid.py"
LEDGER = "proposals/bounded-scheduler-v0.1/impl/peer-chat.jsonl"
CLAIMED = {
    TOOL: "3f229552c1724f17cf1a6da1315f9cf879291490",
    TEST: "8153298ece7bc99efb843d020e6036dc0ac77d2b",
    LEDGER: "c0c8374a32d4e1f60d3963c0bb28923bd6d2d898",
}
CLAIMED_LINES = {
    3051: "14bb05a5eebbb2530f1fb041901b2294ff648d3932e12e6f203063c80b792050",
    3052: "8557ba8172c3d7158bab64caf5e6bb4612f553f574868443347c933c0211cd14",
}
ROOT = Path(__file__).resolve().parents[2]


def git(*args, binary=False):
    proc = subprocess.run(
        ["git", *args], cwd=str(ROOT), capture_output=True
    )
    if proc.returncode != 0:
        raise SystemExit(f"git {args} failed: {proc.stderr!r}")
    return proc.stdout if binary else proc.stdout.decode("utf-8").strip()


report = {"commit": COMMIT}

# A + B(blob part): claimed blob oids at the landed commit.
report["blob_oids"] = {
    path: {
        "claimed": claimed,
        "observed": git("rev-parse", f"{COMMIT}:{path}"),
    }
    for path, claimed in CLAIMED.items()
}
for path, entry in report["blob_oids"].items():
    entry["match"] = entry["claimed"] == entry["observed"]

# B: line-level authorization locatability, current-record-minus-LF-v1.
ledger_bytes = git("cat-file", "blob", CLAIMED[LEDGER], binary=True)
records = ledger_bytes.split(b"\n")
report["ledger_frame_count"] = len(records) - (1 if records[-1] == b"" else 0)
lines = {}
for number, claimed_hash in CLAIMED_LINES.items():
    raw = records[number - 1]
    observed = hashlib.sha256(raw).hexdigest()
    parsed = json.loads(raw.decode("utf-8"))
    lines[number] = {
        "claimed": claimed_hash,
        "observed": observed,
        "match": observed == claimed_hash,
        "trailing_cr": raw.endswith(b"\r"),
        "from": parsed.get("from"),
        "time": parsed.get("time"),
        "text_head": parsed.get("text", "")[:40],
    }
report["cited_lines"] = lines

# C + D: AST recount over the landed blob, not the working tree.
source = git("cat-file", "blob", CLAIMED[TOOL], binary=True).decode("utf-8")
tree = ast.parse(source)
push_call_lines = [
    node.lineno
    for node in ast.walk(tree)
    if isinstance(node, ast.Call)
    and isinstance(node.func, ast.Name)
    and node.func.id == "git"
    and any(
        isinstance(a, ast.Starred)
        and isinstance(a.value, ast.Call)
        and getattr(a.value.func, "id", None) == "push_argv"
        for a in node.args
    )
]
report["push_subprocess_call_lines"] = push_call_lines
pivot = push_call_lines[0] if len(push_call_lines) == 1 else None

fail_calls = []
remote_read_calls = []
for node in ast.walk(tree):
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
        continue
    if node.func.id not in {"fail", "live_remote_oid"}:
        continue
    keywords = {k.arg: k.value for k in node.keywords if k.arg}
    has_kwargs_splat = any(k.arg is None for k in node.keywords)
    value = keywords.get("push_attempted")
    entry = {
        "line": node.lineno,
        "explicit": "push_attempted" in keywords,
        "value": (
            value.value
            if isinstance(value, ast.Constant)
            else (None if value is None else ast.dump(value))
        ),
        "is_literal": isinstance(value, ast.Constant),
        "kwargs_splat": has_kwargs_splat,
        "reason": (
            node.args[0].value
            if node.args and isinstance(node.args[0], ast.Constant)
            else (
                ast.unparse(node.args[0]) if node.args else None
            )
        ),
        "before_push": None if pivot is None else node.lineno < pivot,
    }
    (fail_calls if node.func.id == "fail" else remote_read_calls).append(entry)

fail_calls.sort(key=lambda e: e["line"])
remote_read_calls.sort(key=lambda e: e["line"])
report["fail_call_count"] = len(fail_calls)
report["fail_calls_missing_push_attempted"] = [
    e["line"] for e in fail_calls if not e["explicit"]
]
report["fail_calls_non_literal_push_attempted"] = [
    e["line"] for e in fail_calls if e["explicit"] and not e["is_literal"]
]
report["fail_calls"] = fail_calls
report["live_remote_oid_calls"] = remote_read_calls

# fail() sites reachable only through live_remote_oid keep the caller's value;
# record whether every such caller passes a literal.
report["live_remote_oid_all_literal"] = all(
    e["is_literal"] for e in remote_read_calls
)

# E: call-time reach -- is each fail() reason string named in the test file?
test_source = git("cat-file", "blob", CLAIMED[TEST], binary=True).decode("utf-8")
report["reason_named_in_tests"] = {
    e["reason"]: (e["reason"] in test_source)
    for e in fail_calls
    if isinstance(e["reason"], str)
}
report["reasons_not_named_in_tests"] = sorted(
    reason
    for reason, present in report["reason_named_in_tests"].items()
    if not present
)

# ok-path receipts: literal dicts, not routed through fail().
report["emit_literal_dict_lines"] = [
    node.lineno
    for node in ast.walk(tree)
    if isinstance(node, ast.Call)
    and isinstance(node.func, ast.Name)
    and node.func.id == "emit"
    and node.args
    and isinstance(node.args[0], ast.Dict)
]

# Working-tree drift for the two implementation files.
report["worktree_drift"] = {
    path: git("hash-object", path) != CLAIMED[path]
    for path in (TOOL, TEST)
}

print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
