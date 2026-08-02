#!/usr/bin/env python3
"""Read-only: can the citation visibility gate notice a path the shell erased?

Takes one realistic community-style citation (a repo-relative path inside a markdown
code span), pushes it through the same shell arms as the fidelity matrix, and asks the
gate's own path extractor what it sees in the intended text vs the stored text.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

IMPL = Path(r"D:\WeilanSkillEvolution\proposals\bounded-scheduler-v0.1\impl")
HELPER = IMPL / "append_clocked_jsonl.py"
GATE = IMPL / "cited_artifact_receipt_check.py"
BASH = r"C:\Program Files\Git\bin\bash.exe"

INTENDED = (
    "evidence in `proposals/bounded-scheduler-v0.1/impl/peer-chat.jsonl` "
    "and proposals/mutual-aid-v0.1/peer_health_wake.py end"
)


def load_gate():
    spec = importlib.util.spec_from_file_location("gate", GATE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(cmd):
    p = subprocess.run(cmd, capture_output=True)
    return p.returncode, p.stderr.decode("utf-8", "replace")


def main() -> int:
    gate = load_gate()
    fixture = Path(tempfile.mkdtemp(prefix="wl_gate_erasure_"))
    py = sys.executable
    arms = {
        "bash_double": lambda led: [
            BASH, "-lc",
            f'"{py}" "{HELPER}" --root "{fixture}" --file "{led}" '
            f'--field "from=probe" --field "text={INTENDED}"',
        ],
        "bash_single": lambda led: [
            BASH, "-lc",
            f'"{py}" "{HELPER}" --root "{fixture}" --file "{led}" '
            f"--field 'from=probe' --field 'text={INTENDED}'",
        ],
        "ps_double": lambda led: [
            "powershell", "-NoProfile", "-NonInteractive", "-Command",
            f'& "{py}" "{HELPER}" --root "{fixture}" --file "{led}" '
            f'--field "from=probe" --field "text={INTENDED}"',
        ],
        "ps_single": lambda led: [
            "powershell", "-NoProfile", "-NonInteractive", "-Command",
            f'& "{py}" "{HELPER}" --root "{fixture}" --file "{led}" '
            f"--field 'from=probe' --field 'text={INTENDED}'",
        ],
        "argv_control": lambda led: [
            py, str(HELPER), "--root", str(fixture), "--file", led,
            "--field", "from=probe", "--field", f"text={INTENDED}",
        ],
    }
    try:
        intended_cited = gate.cited_paths(INTENDED)
        rows = []
        for arm, build in arms.items():
            led = f"{arm}.jsonl"
            (fixture / led).write_bytes(b"")
            rc, err = run(build(led))
            data = (fixture / led).read_bytes().strip()
            stored_text = None
            parses = False
            if data:
                try:
                    stored_text = json.loads(data.decode("utf-8")).get("text")
                    parses = True
                except Exception:  # noqa: BLE001
                    parses = False
            stored_cited = gate.cited_paths(stored_text) if stored_text else []
            erased = [p for p in intended_cited if p not in stored_cited]
            rows.append({
                "arm": arm,
                "rc": rc,
                "row_parses_as_json": parses,
                "text_identical": stored_text == INTENDED,
                "stored_text": stored_text,
                "gate_sees_paths": stored_cited,
                "paths_erased_from_the_gate": erased,
                "gate_would_report": (
                    "clean (nothing to notice)" if parses and not stored_cited
                    else "clean" if parses and not erased
                    else "n/a (loud failure upstream)" if not parses
                    else "partial"
                ),
                "stderr_head": err.strip().splitlines()[0][:160] if err.strip() else "",
            })
        print(json.dumps({
            "probe": "citation gate vs shell erasure",
            "intended_text": INTENDED,
            "gate_sees_in_intended": intended_cited,
            "arms": rows,
        }, ensure_ascii=False, indent=2))
        return 0
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
