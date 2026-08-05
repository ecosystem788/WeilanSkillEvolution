#!/usr/bin/env python3
"""Read-only review probe: spec clauses of --field-file not covered by test_append_field_file.py.

Signed spec = peer-chat proposal 2026-08-02T10:48:39+09:00 + Codex agreement 11:01:16.
Writes only into a throwaway temp directory; the live ledgers are never touched.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile


HELPER_PATH = (
    Path(__file__).parents[1]
    / "bounded-scheduler-v0.1"
    / "impl"
    / "append_clocked_jsonl.py"
)
SPEC = importlib.util.spec_from_file_location("append_clocked_jsonl", HELPER_PATH)
assert SPEC and SPEC.loader
HELPER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPER)


def run(root: Path, argv: list[str]) -> int:
    """Call the helper with its stdout echo swallowed, so this probe's own report stays valid JSON."""
    with contextlib.redirect_stdout(io.StringIO()):
        return HELPER.main(["--root", str(root), "--file", "ledger.jsonl", *argv])


def rows(root: Path) -> list[dict]:
    ledger = root / "ledger.jsonl"
    if not ledger.exists():
        return []
    return [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]


def case(name: str, clause: str, fn) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        try:
            observed = fn(root)
        except BaseException as exc:  # a raised exception is itself a finding
            observed = {"raised": f"{type(exc).__name__}: {exc}"}
        observed["ledger_rows"] = len(rows(root))
        return {"case": name, "clause": clause, "observed": observed}


def write(root: Path, name: str, data: bytes) -> Path:
    path = root / name
    path.write_bytes(data)
    return path


def c_reserved_time(root: Path) -> dict:
    src = write(root, "v.txt", b"2020-01-01T00:00:00+09:00")
    return {"rc": run(root, ["--field-file", f"time={src}"])}


def c_reserved_authority(root: Path) -> dict:
    src = write(root, "v.txt", b"authored")
    return {"rc": run(root, ["--field-file", f"time_authority={src}"])}


def c_data_json_conflict(root: Path) -> dict:
    src = write(root, "v.txt", b"x")
    return {"rc": run(root, ["--data-json", '{"a":"b"}', "--field-file", f"text={src}"])}


def c_empty_key(root: Path) -> dict:
    src = write(root, "v.txt", b"x")
    return {"rc": run(root, ["--field-file", f"={src}"])}


def c_consume_without_field_file(root: Path) -> dict:
    return {"rc": run(root, ["--field", "a=b", "--consume-field-file"])}


def c_duplicate_field_file_keys(root: Path) -> dict:
    a = write(root, "a.txt", b"first")
    b = write(root, "b.txt", b"second")
    rc = run(root, ["--field-file", f"text={a}", "--field-file", f"text={b}"])
    return {"rc": rc, "a_still_exists": a.exists(), "b_still_exists": b.exists()}


def c_no_strip_trailing_newline(root: Path) -> dict:
    intended = "line one\nline two\n\n"
    src = write(root, "v.txt", intended.encode("utf-8"))
    rc = run(root, ["--field-file", f"text={src}"])
    stored = rows(root)[0]["text"] if rows(root) else None
    return {"rc": rc, "byte_exact": stored == intended, "stored_repr": repr(stored)}


def c_no_crlf_normalisation(root: Path) -> dict:
    intended = "a\r\nb\r\n"
    src = write(root, "v.txt", intended.encode("utf-8"))
    rc = run(root, ["--field-file", f"text={src}"])
    stored = rows(root)[0]["text"] if rows(root) else None
    return {"rc": rc, "byte_exact": stored == intended, "stored_repr": repr(stored)}


def c_single_physical_line(root: Path) -> dict:
    """A multi-line value must still occupy exactly one JSONL physical line."""
    src = write(root, "v.txt", b"one\ntwo\nthree")
    rc = run(root, ["--field-file", f"text={src}"])
    raw = (root / "ledger.jsonl").read_bytes()
    return {
        "rc": rc,
        "newline_count": raw.count(b"\n"),
        "ends_with_newline": raw.endswith(b"\n"),
    }


def c_empty_file_value(root: Path) -> dict:
    src = write(root, "v.txt", b"")
    rc = run(root, ["--field-file", f"text={src}"])
    stored = rows(root)[0]["text"] if rows(root) else None
    return {"rc": rc, "stored_repr": repr(stored)}


def c_utf16_le_bom_rejected(root: Path) -> dict:
    """UTF-16 payload must be refused, never silently reinterpreted.

    Honest note: an ASCII string in UTF-16-LE is full of NUL bytes, so the refusal here comes
    from the NUL guard, not the UTF-8 decode. Both are loud, but do not read this cell as
    evidence that the decode guard fired.
    """
    src = write(root, "v.txt", "hello".encode("utf-16-le"))
    rc = run(root, ["--field-file", f"text={src}"])
    return {"rc": rc, "refused_by": "nul_guard_not_decode_guard"}


def c_no_append_when_second_file_bad(root: Path) -> dict:
    """First field-file valid, second invalid: the whole append must be refused."""
    good = write(root, "a.txt", b"good")
    bad = write(root, "b.bin", b"\xff\xfe\xfa")
    rc = run(root, ["--field-file", f"a={good}", "--field-file", f"b={bad}"])
    return {"rc": rc}


def c_consume_not_run_on_failure(root: Path) -> dict:
    """--consume-field-file must not unlink anything when the append is refused."""
    good = write(root, "a.txt", b"good")
    bad = write(root, "b.bin", b"\xff")
    rc = run(root, ["--field-file", f"a={good}", "--field-file", f"b={bad}", "--consume-field-file"])
    return {"rc": rc, "good_survived": good.exists(), "bad_survived": bad.exists()}


def c_reserved_via_field_file_and_field_mix(root: Path) -> dict:
    src = write(root, "v.txt", b"x")
    return {"rc": run(root, ["--field", "from=claude", "--field-file", f"time={src}"])}


def c_consume_unlink_failure_stays_rc0(root: Path) -> dict:
    """Spec 3: a failed unlink must warn on stderr and still exit 0 — the append already happened.

    On Windows CPython opens without FILE_SHARE_DELETE, so an open handle makes unlink fail.
    """
    src = write(root, "held.txt", b"held open")
    captured = io.StringIO()
    with src.open("rb"):  # hold a handle open across the whole call
        with contextlib.redirect_stderr(captured):
            rc = run(root, ["--field-file", f"text={src}", "--consume-field-file"])
    return {
        "rc": rc,
        "unlink_failed_as_designed": src.exists(),
        "stderr_has_warning": "Warning" in captured.getvalue(),
        "stderr": captured.getvalue().strip(),
    }


def c_same_file_two_keys_consumed_once(root: Path) -> dict:
    """One file bound to two keys: dedup must not raise a spurious second-unlink failure."""
    src = write(root, "shared.txt", b"shared")
    captured = io.StringIO()
    with contextlib.redirect_stderr(captured):
        rc = run(root, ["--field-file", f"a={src}", "--field-file", f"b={src}", "--consume-field-file"])
    return {
        "rc": rc,
        "file_gone": not src.exists(),
        "stderr": captured.getvalue().strip(),
    }


CASES = [
    ("reserved_time_via_field_file", "spec 1: time/time_authority still refused", c_reserved_time),
    ("reserved_time_authority_via_field_file", "spec 1: no back door", c_reserved_authority),
    ("reserved_time_mixed_with_field", "spec 1: no back door under mixing", c_reserved_via_field_file_and_field_mix),
    ("data_json_conflict", "spec 1: mutually exclusive with --data-json", c_data_json_conflict),
    ("empty_key", "spec 1: empty key refused", c_empty_key),
    ("consume_without_field_file", "spec 3: flag requires --field-file", c_consume_without_field_file),
    ("duplicate_field_file_keys", "spec 1: duplicate keys refused", c_duplicate_field_file_keys),
    ("no_strip_trailing_newline", "spec 1: no strip", c_no_strip_trailing_newline),
    ("no_crlf_normalisation", "spec 1: no newline normalisation", c_no_crlf_normalisation),
    ("single_physical_line", "JSONL invariant: one row = one line", c_single_physical_line),
    ("empty_file_value", "spec 1: empty file is a value, not an error", c_empty_file_value),
    ("utf16_payload", "spec 1: strict UTF-8 only", c_utf16_le_bom_rejected),
    ("no_append_when_second_file_bad", "spec 1: failure means no append", c_no_append_when_second_file_bad),
    ("consume_not_run_on_failure", "spec 3: consume only after success", c_consume_not_run_on_failure),
    ("consume_unlink_failure_stays_rc0", "spec 3: unlink failure warns, rc stays 0", c_consume_unlink_failure_stays_rc0),
    ("same_file_two_keys_consumed_once", "spec 3: consume dedup", c_same_file_two_keys_consumed_once),
]


def main() -> int:
    report = {
        "probe": "_probe_20260802_field_file_review",
        "helper": str(HELPER_PATH),
        "signed_spec": "peer-chat 2026-08-02T10:48:39+09:00 (proposal) + 11:01:16 (agreement)",
        "cases": [case(name, clause, fn) for name, clause, fn in CASES],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
