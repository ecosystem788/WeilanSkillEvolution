"""Compute the cosign five-binding figures for this proposal.

Byte semantics: raw bytes of the workspace file, open(path,'rb').read().
No encoding conversion, no EOL normalization, no BOM edits, trailing newline counted.
Line shape: canonical LCS per CONVENTION §5.5.b -- both sides split by
splitlines(keepends=True), LCS length by dynamic programming, then
added = len(final) - LCS, deleted = len(base) - LCS.  Those two counts depend
only on the LCS length, which is unique, so they are recomputable independently
of any implementation.

The DP is not reimplemented here: this module imports lcs_tables() from the
governed checker proposals/cosign-bytewise-binding-v0.1/verify_binding.py, so
the figures below are produced by the same authority that will machine-check
them.  difflib.SequenceMatcher is deliberately NOT used -- CONVENTION §5.5.b
forbids it with a counterexample (a,b,a -> b,c,a: it reports 2/2, true LCS
gives 1/1).  It happened to agree with the true LCS on all three rows of this
proposal; agreeing by luck is still the wrong method, which is what Codex
blocked on 2026-07-31T20:45:46+09:00.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

REPO = Path(r"D:\WeilanSkillEvolution")
IMPL = REPO / "proposals" / "bounded-scheduler-v0.1" / "impl"
PROP = REPO / "proposals" / "wake-entrypoint-ergonomics-v0.1"
LIVE = Path(r"C:\Users\zy\.claude\skills\solve-with-weilan\scripts\wake_brief.py")
CHECKER = REPO / "proposals" / "cosign-bytewise-binding-v0.1" / "verify_binding.py"


def _load_checker(path: Path):
    spec = importlib.util.spec_from_file_location("weilan_verify_binding", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


CHECK = _load_checker(CHECKER)
CHECKER_SHA256 = hashlib.sha256(CHECKER.read_bytes()).hexdigest()

TARGETS = [
    ("proposals/bounded-scheduler-v0.1/impl/wake_brief.py",
     IMPL / "wake_brief.py", PROP / "wake_brief.proposed-final.py"),
    ("proposals/bounded-scheduler-v0.1/impl/test_wake_brief.py",
     IMPL / "test_wake_brief.py", PROP / "test_wake_brief.proposed-final.py"),
    # base_path IS the target path, exactly like every other row: absence is
    # OBSERVED here, never asserted.  The post-image lives beside the other two
    # as *.proposed-final.py, so the real target is genuinely absent at signing
    # time under the one byte convention (raw workspace bytes) used throughout.
    ("proposals/wake-entrypoint-ergonomics-v0.1/"
     "_probe_20260731_wake_peek_prelanding_harness.py",
     PROP / "_probe_20260731_wake_peek_prelanding_harness.py",
     PROP / "_probe_20260731_wake_peek_prelanding_harness.proposed-final.py"),
    ("(deployed) C:/Users/zy/.claude/skills/solve-with-weilan/scripts/wake_brief.py",
     LIVE, PROP / "wake_brief.proposed-final.py"),
]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def shape(base: bytes, final: bytes) -> tuple[int, int, int]:
    a = base.splitlines(keepends=True)
    b = final.splitlines(keepends=True)
    n, m = len(a), len(b)
    if (n + 1) * (m + 1) > CHECK.MAX_DELTA_CELLS:
        # Same fail-closed rule as the checker: never fall back to a heuristic.
        raise SystemExit("delta cells %d exceed MAX_DELTA_CELLS=%d"
                         % ((n + 1) * (m + 1), CHECK.MAX_DELTA_CELLS))
    pre, w, _suf, _w2 = CHECK.lcs_tables(a, b)
    lcs = pre[n * w + m]
    return m - lcs, n - lcs, lcs


rows = []
for path, base_path, final_path in TARGETS:
    final = final_path.read_bytes()
    # Every row observes its own base path.  ABSENT is a reading, not a constant:
    # drop any byte into base_path and this row stops saying ABSENT.
    observed = {"base_path": str(base_path), "exists": base_path.exists()}
    if not observed["exists"]:
        # LCS(<empty>, final) == 0, so the canonical counts degenerate to
        # added = len(final), deleted = 0.  Same formula, not a special case.
        added, deleted, lcs = shape(b"", final)
        rows.append({"target": path, "base_observed": observed,
                     "base_sha256": "ABSENT", "base_bytes": None,
                     "final_sha256": sha256(final), "final_bytes": len(final),
                     "added": added, "deleted": deleted, "lcs_length": lcs})
        continue
    base = base_path.read_bytes()
    added, deleted, lcs = shape(base, final)
    rows.append({"target": path, "base_observed": observed,
                 "base_sha256": sha256(base), "base_bytes": len(base),
                 "final_sha256": sha256(final), "final_bytes": len(final),
                 "added": added, "deleted": deleted, "lcs_length": lcs})

# Deterministic so the reviewer can recompute it instead of trusting a nonce.
wake_final = sha256((PROP / "wake_brief.proposed-final.py").read_bytes())
deployment_id = sha256(
    ("wake-entrypoint-ergonomics-v0.1|" + wake_final).encode("ascii"))[:24]

print(json.dumps({"byte_semantics": "raw workspace bytes; no conversion; trailing newline counted",
                  "line_shape_semantics":
                      "canonical LCS DP per CONVENTION 5.5.b; added=len(final)-LCS, "
                      "deleted=len(base)-LCS; difflib.SequenceMatcher not used",
                  "lcs_source": {"path": "proposals/cosign-bytewise-binding-v0.1/verify_binding.py",
                                 "symbol": "lcs_tables", "sha256": CHECKER_SHA256},
                  "targets": rows,
                  "deployment_id": deployment_id,
                  "deployment_id_recipe":
                      "sha256('wake-entrypoint-ergonomics-v0.1|' + <target-1 final sha256>)[:24]",
                  "deployment_aux_paths": [
                      f"deployments/{deployment_id}/DEPLOYMENT_INTENT.json",
                      f"deployments/{deployment_id}/DEPLOYMENT_RECEIPT.json",
                      f"deployments/{deployment_id}/rollback/solve-with-weilan/scripts/wake_brief.py",
                  ]},
                 ensure_ascii=False, indent=2))
