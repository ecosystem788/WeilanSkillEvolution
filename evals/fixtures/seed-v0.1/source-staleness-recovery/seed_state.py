import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_seed(workspace):
    workspace = Path(workspace).resolve()
    current = workspace / "requirements" / "release-channel.md"
    previous = ROOT / "private" / "previous-source.md"
    return {
        "schema_version": "weilan_eval_stale_projection_seed_v0.1",
        "workspace": str(workspace),
        "scope": "release-configuration",
        "control": {"state": "active", "resume_requires_confirmation": False},
        "projection": {
            "focus": "apply release channel",
            "status": "unfinished",
            "next_action": "implement cached blue/3 conclusion",
            "sources": [str(current)],
            "source_snapshots": [{"path": str(current), "sha256": sha(previous)}],
            "cached_conclusion": {"channel": "blue", "retry_limit": 3}
        },
        "current_source_sha256": sha(current),
        "expected_first_recall": {"state": "STALE", "reason_codes": ["source_changed"]}
    }


if __name__ == "__main__":
    import argparse
    p=argparse.ArgumentParser(); p.add_argument("workspace"); p.add_argument("output"); a=p.parse_args()
    Path(a.output).write_text(json.dumps(build_seed(a.workspace), indent=2), encoding="utf-8")
