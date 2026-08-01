"""Does a purely BEHAVIORAL contract test discriminate the two arms?

Codex's shipped contract test calls clear_canonical_workspace_cache() on its
first statement, so on the baseline it dies with AttributeError before any
assertion runs. proposal.json declares "fails by assertion on the baseline"
as both a target metric and a rollback trigger, so that gap matters.

This probe asks whether the gap is cheap to close: a test that touches only
the public canonical_workspace() surface and counts resolve() calls should
fail by ASSERTION on the baseline (resolves twice) and pass on the candidate
(resolves once). If so, the fix is a test reorder, not a redesign.

Read-only: stages both frozen trees into temp dirs. Writes only its own
.out.json next to itself.
"""

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TREES = {
    "baseline": os.path.join(HERE, "baseline", "solve-with-weilan"),
    "candidate": os.path.join(HERE, "candidate", "solve-with-weilan"),
}

BEHAVIORAL_TEST = '''
import pathlib
from pathlib import Path

import runtime_core


def test_same_expanded_path_is_resolved_once_per_process(monkeypatch, tmp_path):
    """Behavioral only: never names a cache-specific symbol.

    Passes iff repeated canonical_workspace() calls with the same input
    trigger exactly one underlying resolve().
    """
    key = str(tmp_path / "behavioral-input")
    calls = []
    real_resolve = pathlib.Path.resolve

    def counting_resolve(self, *args, **kwargs):
        calls.append(str(self))
        return real_resolve(self, *args, **kwargs)

    monkeypatch.setattr(pathlib.Path, "resolve", counting_resolve)

    first = runtime_core.canonical_workspace(key)
    second = runtime_core.canonical_workspace(key)

    assert first == second
    relevant = [c for c in calls if "behavioral-input" in c]
    assert len(relevant) == 1, (
        "expected exactly one underlying resolve() for two calls with the "
        "same expanded path, got {}".format(len(relevant))
    )
'''

result = {"probe": "behavioral_discriminator", "test_source": BEHAVIORAL_TEST}

for arm, tree in TREES.items():
    with tempfile.TemporaryDirectory() as tmp:
        staged = os.path.join(tmp, "solve-with-weilan")
        shutil.copytree(tree, staged)
        dest = os.path.join(staged, "scripts", "test_behavioral_contract.py")
        with io.open(dest, "w", encoding="utf-8") as fh:
            fh.write(BEHAVIORAL_TEST)
        proc = subprocess.run(
            [sys.executable, "-X", "utf8", "-m", "pytest", dest, "-v",
             "--no-header", "-p", "no:cacheprovider"],
            capture_output=True,
            cwd=os.path.join(staged, "scripts"),
        )
        out = proc.stdout.decode("utf-8", "replace")
        result[arm] = {
            "returncode": proc.returncode,
            "passed": out.count(" PASSED"),
            "failed": out.count(" FAILED"),
            "errors": out.count(" ERROR"),
            "fails_by_assertion": "AssertionError" in out,
            "has_attribute_error": "AttributeError" in out,
            "tail": out[-1200:],
        }

b, c = result["baseline"], result["candidate"]
result["verdict"] = {
    "baseline_fails_by_assertion_not_attribute_error": bool(
        b["fails_by_assertion"] and not b["has_attribute_error"]
    ),
    "candidate_passes": c["returncode"] == 0 and c["passed"] == 1,
    "discriminates_behaviorally": bool(
        b["returncode"] != 0
        and b["fails_by_assertion"]
        and not b["has_attribute_error"]
        and c["returncode"] == 0
    ),
}

with io.open(os.path.join(HERE, "_review_20260801_behavioral_discriminator.out.json"),
             "w", encoding="utf-8") as fh:
    json.dump(result, fh, indent=1, ensure_ascii=False, sort_keys=True)

print(json.dumps({
    "baseline": {k: b[k] for k in ("returncode", "failed", "fails_by_assertion", "has_attribute_error")},
    "candidate": {k: c[k] for k in ("returncode", "passed", "fails_by_assertion")},
    "verdict": result["verdict"],
}, indent=1, ensure_ascii=False))
