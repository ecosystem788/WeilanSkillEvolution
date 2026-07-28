from __future__ import annotations

import hashlib
from pathlib import Path


CRON_WAKE_BRIEF = Path(__file__).with_name("wake_brief.py")
LIVE_WAKE_BRIEF = Path("C:/Users/zy/.claude/skills/solve-with-weilan/scripts/wake_brief.py")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_cron_and_live_agent_wake_brief_are_byte_identical() -> None:
    cron_hash = sha256(CRON_WAKE_BRIEF)
    live_hash = sha256(LIVE_WAKE_BRIEF)
    assert cron_hash == live_hash, (
        f"cron wake_brief sha256={cron_hash}; "
        f"live agent wake_brief sha256={live_hash}"
    )
