"""One-shot, observable scheduler entry for an installed WeiLan runtime."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True

from bounded_scheduler import Action, run_episode


def _canonical(data: object) -> bytes:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _append(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")
        stream.flush()


def tick(install_root: Path, *, tick_only: bool = False) -> tuple[int, dict]:
    root = install_root.resolve()
    runtime_dir = root / "data" / "runtime"
    config_path = runtime_dir / "runtime.json"
    config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.is_file() else {}
    config_hash = hashlib.sha256(_canonical(config)).hexdigest()
    queue = [
        Action(
            id=str(item.get("id", f"item-{index}")),
            kind=str(item.get("kind", "analyze")),
            summary=str(item.get("summary", "")),
        )
        for index, item in enumerate(config.get("work_queue", []))
        if isinstance(item, dict)
    ]
    episode = run_episode(queue)
    outcome = "nothing_due"
    detail: dict[str, object] = {"episode_stop_reason": episode.stop_reason}
    code = 0
    command = config.get("agent_command")
    if not tick_only and command:
        if not isinstance(command, list) or not command or not all(isinstance(x, str) and x for x in command):
            outcome, code = "agent_failed", 2
            detail.update(exit=2, stderr_hash=hashlib.sha256(b"invalid agent_command").hexdigest())
        else:
            completed = subprocess.run(command, cwd=root, text=True, encoding="utf-8", capture_output=True)
            if completed.returncode == 0:
                outcome = "agent_invoked"
            else:
                outcome, code = "agent_failed", completed.returncode or 1
                detail.update(
                    exit=completed.returncode,
                    stderr_hash=hashlib.sha256(completed.stderr.encode("utf-8")).hexdigest(),
                )
    elif tick_only or not command:
        outcome = "no_agent_configured" if not queue else "nothing_due"
    receipt = {
        "schema": "weilan_portable_scheduler_tick_v0.1",
        "time_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "config_sha256": config_hash,
        "outcome": outcome,
        "tick_only": bool(tick_only),
        **detail,
    }
    _append(runtime_dir / "scheduler-ticks.jsonl", receipt)
    return code, receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    child = sub.add_parser("tick")
    child.add_argument("--install-root", type=Path, required=True)
    child.add_argument("--tick-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        code, result = tick(args.install_root, tick_only=args.tick_only)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        code, result = 1, {"schema": "weilan_portable_scheduler_error_v0.1", "status": "error", "error": str(exc)}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
