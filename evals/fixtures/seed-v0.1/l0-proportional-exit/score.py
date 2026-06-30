import argparse
import json
from pathlib import Path
from hidden.check import evaluate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trial-root", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        result = evaluate("仅在启用严格模式时，解析器才会拒绝尾随逗号。", {"tool_calls": 0}, 0)
        assert all(value == 1 for value in result["metrics"].values())
    else:
        root = args.trial_root
        telemetry = json.loads((root / "telemetry.json").read_text(encoding="utf-8"))
        method_dir = root / "method-state"
        events = sum(1 for path in method_dir.rglob("*.jsonl") for line in path.read_text(encoding="utf-8").splitlines() if line.strip()) if method_dir.exists() else 0
        result = evaluate((root / "final.txt").read_text(encoding="utf-8"), telemetry, events)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
