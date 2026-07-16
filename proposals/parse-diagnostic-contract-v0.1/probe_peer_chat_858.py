"""Read-only host-fact probe for the malformed physical record at peer-chat line 858."""

from __future__ import annotations

import json
import sys
from pathlib import Path


EXPECTED_LINE = 858
EXPECTED_REASON = "invalid_json"
EXPECTED_SHA256 = "bfb3ec4dcc57876d630c07ed5e74ab42547d01e270bcbf6961038779046fd1be"


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    workspace = Path(args[0]) if args else Path(__file__).resolve().parents[2]
    wake_impl = workspace / "proposals" / "bounded-scheduler-v0.1" / "impl"
    sys.path.insert(0, str(wake_impl))
    import wake_brief

    source = wake_impl / "peer-chat.jsonl"
    matches = [row for row in wake_brief.read_jsonl(source) if row.get("line") == EXPECTED_LINE]
    observed = matches[0] if len(matches) == 1 else None
    passed = bool(
        observed
        and observed.get("reason_code") == EXPECTED_REASON
        and observed.get("raw_bytes_sha256") == EXPECTED_SHA256
    )
    report = {
        "probe": "peer-chat.jsonl:858",
        "passed": passed,
        "expected": {
            "line": EXPECTED_LINE,
            "reason_code": EXPECTED_REASON,
            "raw_bytes_sha256": EXPECTED_SHA256,
        },
        "observed": observed,
    }
    if not passed:
        report["response"] = "宿主事实漂移：重钉已知答案；不要修改读者代码或账本来制造绿灯。"
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
