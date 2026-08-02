#!/usr/bin/env python3
"""Read-only probe: does the mandated append helper preserve message text byte-for-byte
across the shell layers an agent actually types into?

Writes ONLY into a throwaway fixture directory. Never touches the live ledgers.

Method. The intended texts live in this file, so no shell touches them before the
comparison. Each cell of the matrix hands one intended text to append_clocked_jsonl.py
through one shell + quoting style, exactly as an agent would type it, then reads the
stored row back and compares stored["text"] to the intended string character by
character.

The classification that matters:
  ok      -- helper ran, stored text identical to intent
  loud    -- the shell or the helper failed with a non-zero exit; nothing was stored,
             or what was stored is unparseable. An agent cannot mistake this for success.
  SILENT  -- helper exited 0, the row is valid JSON, and the stored text differs from
             what the agent meant to say. Nothing downstream can detect this.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HELPER = Path(
    r"D:\WeilanSkillEvolution\proposals\bounded-scheduler-v0.1\impl\append_clocked_jsonl.py"
)
# The Bash tool in this harness is Git Bash; resolve it explicitly so the probe does not
# depend on which shell launched the probe itself.
BASH = r"C:\Program Files\Git\bin\bash.exe"
PWSH = "powershell"

# One hazard per payload, so a loud failure from one hazard cannot mask a silent
# corruption from another. The last payload is the realistic mixed case.
PAYLOADS = {
    "winpath": "ledger at D:\\CodexData\\home\\config.toml end",
    "backtick": "the span `peer-chat.jsonl` end",
    "dollar_posix": "read $CODEX_HOME end",
    "dollar_ps": "read $env:CODEX_HOME end",
    "apostrophe": "it's fine end",
    "dquote": 'he said "fine" end',
    "mixed_realistic": "core D:\\CodexData\\home ; span `peer-chat.jsonl` ; $CODEX_HOME end",
}


def run(cmd: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, capture_output=True)
    dec = lambda b: b.decode("utf-8", errors="replace")  # noqa: E731
    return proc.returncode, dec(proc.stdout), dec(proc.stderr)


def last_row(ledger: Path) -> dict | None:
    if not ledger.exists():
        return None
    lines = [l for l in ledger.read_bytes().split(b"\n") if l.strip()]
    if not lines:
        return None
    try:
        return json.loads(lines[-1].decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {"__parse_error__": f"{type(exc).__name__}: {exc}"}


def diff_report(intended: str, stored: str | None) -> dict:
    if stored is None:
        return {"identical": False, "reason": "no text field stored"}
    if stored == intended:
        return {"identical": True}
    n = min(len(intended), len(stored))
    idx = next((i for i in range(n) if intended[i] != stored[i]), n)
    return {
        "identical": False,
        "intended_len": len(intended),
        "stored_len": len(stored),
        "first_divergence_index": idx,
        "intended_at_divergence": intended[idx : idx + 40],
        "stored_at_divergence": stored[idx : idx + 40],
        "stored_full": stored,
    }


def build_cells(py: str, fixture: Path):
    """Yield (arm, shell_argv_builder) for each shell + quoting style."""

    def bash_double(text: str, ledger: str) -> list[str]:
        cmd = (
            f'"{py}" "{HELPER}" --root "{fixture}" --file "{ledger}" '
            f'--field "from=probe" --field "text={text}"'
        )
        return [BASH, "-lc", cmd]

    def bash_single(text: str, ledger: str) -> list[str]:
        cmd = (
            f'"{py}" "{HELPER}" --root "{fixture}" --file "{ledger}" '
            f"--field 'from=probe' --field 'text={text}'"
        )
        return [BASH, "-lc", cmd]

    def ps_double(text: str, ledger: str) -> list[str]:
        cmd = (
            f'& "{py}" "{HELPER}" --root "{fixture}" --file "{ledger}" '
            f'--field "from=probe" --field "text={text}"'
        )
        return [PWSH, "-NoProfile", "-NonInteractive", "-Command", cmd]

    def ps_single(text: str, ledger: str) -> list[str]:
        cmd = (
            f'& "{py}" "{HELPER}" --root "{fixture}" --file "{ledger}" '
            f"--field 'from=probe' --field 'text={text}'"
        )
        return [PWSH, "-NoProfile", "-NonInteractive", "-Command", cmd]

    def argv_control(text: str, ledger: str) -> list[str]:
        return [
            py, str(HELPER), "--root", str(fixture), "--file", ledger,
            "--field", "from=probe", "--field", f"text={text}",
        ]

    return [
        ("bash_double", bash_double),
        ("bash_single", bash_single),
        ("ps_double", ps_double),
        ("ps_single", ps_single),
        ("argv_control", argv_control),
    ]


def main() -> int:
    fixture = Path(tempfile.mkdtemp(prefix="wl_append_fidelity_"))
    cells = []
    try:
        py = sys.executable
        for arm, builder in build_cells(py, fixture):
            for hazard, intended in PAYLOADS.items():
                ledger_name = f"{arm}__{hazard}.jsonl"
                (fixture / ledger_name).write_bytes(b"")
                rc, _out, err = run(builder(intended, ledger_name))
                row = last_row(fixture / ledger_name)
                parses = bool(row) and "__parse_error__" not in row
                stored = (row or {}).get("text")
                fid = diff_report(intended, stored)
                if rc == 0 and parses and fid.get("identical"):
                    verdict = "ok"
                elif rc == 0 and parses and not fid.get("identical"):
                    verdict = "SILENT"
                else:
                    verdict = "loud"
                cells.append({
                    "arm": arm,
                    "hazard": hazard,
                    "intended": intended,
                    "rc": rc,
                    "row_parses_as_json": parses,
                    "stored_text": stored,
                    "verdict": verdict,
                    "fidelity": fid,
                    "stderr_head": err.strip().splitlines()[0][:200] if err.strip() else "",
                })

        by_verdict = {}
        for c in cells:
            by_verdict.setdefault(c["verdict"], []).append(f"{c['arm']}/{c['hazard']}")
        report = {
            "probe": "append_clocked_jsonl shell fidelity matrix",
            "helper": HELPER.as_posix(),
            "bash": BASH,
            "cells_total": len(cells),
            "counts": {k: len(v) for k, v in sorted(by_verdict.items())},
            "silent_cells": sorted(by_verdict.get("SILENT", [])),
            "loud_cells": sorted(by_verdict.get("loud", [])),
            "cells": cells,
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
