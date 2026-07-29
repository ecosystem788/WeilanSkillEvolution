"""Read-only census: every producer/consumer of before_hash, and what framing each uses.

Codex named this enumeration as the precondition for opening the 乙 case
(peer-chat 2026-07-30T00:45:20+09:00). Nothing here writes; run it from anywhere.

Two conventions are actually implemented in live code today:
  A = compile_view.line_without_lf   -> strip a trailing b"\\n" only; a stored CR stays in the payload
  B = wake_brief._record_payload     -> strip exactly one complete separator (b"\\r\\n" or b"\\n"); a
                                        bare trailing CR on an unterminated record is NOT stripped
This probe measures where they disagree on the real bytes on disk.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
IMPL = REPO / "proposals" / "bounded-scheduler-v0.1" / "impl"

GOVERNED = [
    IMPL / "peer-chat.jsonl",
    IMPL / "owner-inbox.jsonl",
    IMPL / "owner-inbox-replies.jsonl",
    IMPL / "owner-inbox-processed.jsonl",
    IMPL / "codex-inbox.jsonl",
]

CORRECTIONS = IMPL / "peer-chat.corrections.jsonl"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def physical_records(data: bytes):
    """Same framing as wake_brief._physical_records: split after each b'\\n'."""
    start = 0
    index = 0
    while start < len(data):
        newline = data.find(b"\n", start)
        end = len(data) if newline < 0 else newline + 1
        yield index, data[start:end]
        index += 1
        start = end


def payload_a(record: bytes) -> bytes:
    """compile_view.line_without_lf"""
    return record[:-1] if record.endswith(b"\n") else record


def payload_b(record: bytes) -> bytes:
    """wake_brief._record_payload"""
    if record.endswith(b"\r\n"):
        return record[:-2]
    if record.endswith(b"\n"):
        return record[:-1]
    return record


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout


def census_entrypoints() -> dict:
    """Every .py on disk mentioning before_hash, tracked or not.

    Denominator note: `git grep` sees only tracked files, and the two real
    producers (_void_20260728_empty_line.py, _append_witness_preimage_correction.py)
    are untracked. Searching tracked-only silently reports zero producers, so this
    walks the filesystem and reports both denominators.
    """
    tracked = {
        f for f in git("grep", "-l", "before_hash", "--", "*.py").splitlines() if f
    }
    # Enumerate via git, not Path.rglob: this repo has paths past MAX_PATH and
    # rglob dies with WinError 3 partway through (see push-third-party-reachability-v0.1).
    candidates = [
        f
        for f in (
            git("ls-files", "--", "*.py")
            + git("ls-files", "--others", "--exclude-standard", "--", "*.py")
        ).splitlines()
        if f
    ]
    on_disk = []
    for rel in candidates:
        try:
            if b"before_hash" in (REPO / rel).read_bytes():
                on_disk.append(rel)
        except OSError:
            continue

    # A producer writes a before_hash into the LIVE sidecar. A filename prefix is
    # not evidence either way, and "mentions corrections.jsonl" is too loose (it
    # catches probes that only build tmp fixtures). Require both: it constructs a
    # before_hash value, and it appends to the live corrections ledger by name.
    self_rel = Path(__file__).resolve().relative_to(REPO).as_posix()
    producers = []
    for rel in on_disk:
        if rel == self_rel:  # this probe quotes the marker strings it searches for
            continue
        text = (REPO / rel).read_text(encoding="utf-8", errors="replace")
        writes_live = (
            'ledger_name="peer-chat.corrections.jsonl"' in text
            or "ledger_name='peer-chat.corrections.jsonl'" in text
        )
        if writes_live and '"before_hash":' in text:
            producers.append(rel)
    return {
        "on_disk_count": len(on_disk),
        "tracked_count": len(tracked),
        "untracked_missed_by_git_grep": sorted(set(on_disk) - tracked),
        "producers_writing_corrections_rows": sorted(producers),
        "tracked_files": sorted(tracked),
    }


def divergence() -> dict:
    rows = []
    for path in GOVERNED:
        if not path.exists():
            continue
        data = path.read_bytes()
        for index, record in physical_records(data):
            a, b = payload_a(record), payload_b(record)
            if a == b:
                continue
            rows.append(
                {
                    "file": path.name,
                    "line": index + 1,
                    "terminator": "CRLF" if record.endswith(b"\r\n") else "other",
                    "hash_A_cr_retained": sha(a),
                    "hash_B_cr_stripped": sha(b),
                }
            )
    return {"divergent_lines": rows, "count": len(rows)}


def unterminated_tail() -> dict:
    """B deliberately does not strip a bare CR from an unterminated last record."""
    out = []
    for path in GOVERNED:
        if not path.exists():
            continue
        data = path.read_bytes()
        if not data:
            continue
        out.append(
            {
                "file": path.name,
                "ends_with_lf": data.endswith(b"\n"),
                "last_byte": repr(data[-1:]),
            }
        )
    return {"files": out}


def corrections_resolution() -> dict:
    """For each stored before_hash: which convention's index resolves it, if any."""
    if not CORRECTIONS.exists():
        return {"error": "corrections file absent"}
    raw = (IMPL / "peer-chat.jsonl").read_bytes()
    idx_a, idx_b = {}, {}
    for index, record in physical_records(raw):
        idx_a.setdefault(sha(payload_a(record)), index + 1)
        idx_b.setdefault(sha(payload_b(record)), index + 1)

    out = []
    for index, record in physical_records(CORRECTIONS.read_bytes()):
        payload = payload_b(record)
        if not payload.strip():
            continue
        try:
            entry = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            out.append({"correction_line": index + 1, "parse_error": str(exc)})
            continue
        bh = entry.get("before_hash")
        if not isinstance(bh, str):
            out.append({"correction_line": index + 1, "before_hash": None, "kind": "no before_hash"})
            continue
        out.append(
            {
                "correction_line": index + 1,
                "corrects": entry.get("corrects"),
                "resolves_under_A": idx_a.get(bh),
                "resolves_under_B": idx_b.get(bh),
                "same_line_both": idx_a.get(bh) == idx_b.get(bh) and idx_a.get(bh) is not None,
            }
        )
    return {"entries": out, "count": len(out)}


def main() -> int:
    report = {
        "head": git("rev-parse", "HEAD").strip(),
        "entrypoints": census_entrypoints(),
        "convention_definitions": {
            "A": "proposals/lineage-log-append-only-correction-v0.1/compile_view.py:line_without_lf",
            "B": "skill/solve-with-weilan/scripts/wake_brief.py:_record_payload (3 more copies)",
        },
        "divergence_on_disk": divergence(),
        "unterminated_tail": unterminated_tail(),
        "corrections_resolution": corrections_resolution(),
    }
    json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
