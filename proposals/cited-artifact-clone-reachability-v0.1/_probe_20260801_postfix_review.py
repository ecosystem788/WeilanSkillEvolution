#!/usr/bin/env python3
"""Read-only review probe for the 2026-08-01 five-item cited-artifact fix.

Two questions the signed acceptance did not pin down:

Q1  Is `unresolvable_component` the only Win32-strippable component shape?
    The fix special-cases exactly "..."; any other component that Win32 strips
    (trailing dots, longer dot runs) would still fall through to the
    resolve()/relative_to() branch and get reason "path escapes root", which is
    the exact misdiagnosis item 2 was signed to remove.

Q2  What does the headline `warning_count` say when a citation ends as
    `check_error:*`?  Before the fix a CheckError aborted the whole bucket
    (rc=2, ok=false).  After the fix it is demoted to a per-citation status
    that is not in `warning_statuses`.

Writes nothing outside its own temp dirs; emits JSON on stdout.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile


IMPL = Path(r"D:\WeilanSkillEvolution\proposals\bounded-scheduler-v0.1\impl")
CHECKER = IMPL / "cited_artifact_receipt_check.py"

spec = importlib.util.spec_from_file_location("cited_artifact_receipt_check", CHECKER)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

AUTHOR = "codex"
TIMESTAMP = "2026-08-01T00:00:00+09:00"


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def _repo(base: Path) -> tuple[Path, Path]:
    root = base / "repo"
    ledger_root = root / "proposals" / "bounded-scheduler-v0.1" / "impl"
    ledger_root.mkdir(parents=True)
    (root / "proposals" / "tracked.md").write_text("tracked\n", encoding="utf-8")
    _git(root, "init")
    ident = ("-c", "user.name=WeiLan Probe", "-c", "user.email=probe@example.invalid")
    _git(root, *ident, "add", "proposals/tracked.md")
    _git(root, *ident, "commit", "-m", "seed")
    return root, ledger_root


def _bucket(ledger_root: Path, text: str) -> dict:
    record = {"from": AUTHOR, "time": TIMESTAMP, "text": text}
    (ledger_root / gate.LEDGER_NAME).write_text(
        json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return gate.check_bucket(root=ledger_root, author=AUTHOR, timestamp=TIMESTAMP)


def q1_component_shapes() -> dict:
    """Which dot-shaped components resolve() mangles, and how the fix labels them."""
    shapes = [
        "...",       # the one the fix special-cases
        "....",      # longer dot run
        ".....",
        "trail.",    # trailing single dot
        "trail...",  # trailing dot run
        "mid.dle",   # control: ordinary dotted name
    ]
    out = []
    with tempfile.TemporaryDirectory() as tmp:
        root, ledger_root = _repo(Path(tmp))
        for shape in shapes:
            path = f"proposals/{shape}/ghost.md"
            extracted = gate.cited_paths(f"see {path} for details")
            resolved = (root / "proposals" / shape / "ghost.md").resolve()
            payload = _bucket(ledger_root, f"see {path} and proposals/tracked.md")
            citations = {c["path"]: c for c in payload["records"][0]["citations"]}
            entry = citations.get(path, {})
            out.append(
                {
                    "component": shape,
                    "path": path,
                    "extracted_by_regex": extracted == [path],
                    "resolve_str": str(resolved),
                    "resolve_uses_extended_prefix": str(resolved).startswith("\\\\?\\"),
                    "component_survived_resolve": shape in resolved.parts,
                    "status": entry.get("status"),
                    "classification_error": entry.get("classification_error"),
                    "bucket_warning_count": payload["warning_count"],
                    "sibling_still_classified": citations.get(
                        "proposals/tracked.md", {}
                    ).get("status"),
                }
            )
    return {"question": "which components does the fix actually cover", "cases": out}


def q2_check_error_warning() -> dict:
    """Headline numbers a bucket reports when one citation cannot be classified."""
    with tempfile.TemporaryDirectory() as tmp:
        root, ledger_root = _repo(Path(tmp))
        original = gate._classify

        def failing(**kwargs):
            if kwargs["path"] == "proposals/escaping.md":
                raise gate.CheckError("invalid_path", "path escapes root: proposals/escaping.md")
            return original(**kwargs)

        gate._classify = failing
        try:
            payload = _bucket(
                ledger_root, "proposals/escaping.md and proposals/tracked.md"
            )
        finally:
            gate._classify = original

    citations = {c["path"]: c for c in payload["records"][0]["citations"]}
    return {
        "question": "does a per-citation check_error reach the headline",
        "status_counts": payload["status_counts"],
        "warning_count": payload["warning_count"],
        "warning_statuses": payload["warning_statuses"],
        "errored_citation_status": citations["proposals/escaping.md"]["status"],
        "errored_citation_reason": citations["proposals/escaping.md"]
        .get("classification_error", {})
        .get("reason"),
        "sibling_status": citations["proposals/tracked.md"]["status"],
        "note": (
            "before the fix this same CheckError aborted the bucket: main() returned 2 "
            "with ok=false; after the fix the run is rc=0 / ok=true / warning_count as shown"
        ),
    }


def main() -> int:
    payload = {
        "probe": "cited_artifact_postfix_review",
        "authority": "report_only",
        "checker": str(CHECKER),
        "checker_sha256": __import__("hashlib")
        .sha256(CHECKER.read_bytes())
        .hexdigest(),
        "python": sys.version.split()[0],
        "q1_component_shapes": q1_component_shapes(),
        "q2_check_error_warning": q2_check_error_warning(),
        "boundary": (
            "measures only how the checker labels synthetic citations; says nothing "
            "about whether any cited bytes are the ones a signer read"
        ),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
