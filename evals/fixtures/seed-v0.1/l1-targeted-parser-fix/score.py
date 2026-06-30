import argparse
import hashlib
import json
from pathlib import Path
from hidden.check import evaluate


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--trial-root", type=Path, required=True)
    args = p.parse_args()
    initial = json.loads((Path(__file__).parent / "fixture-manifest.json").read_text(encoding="utf-8"))["public_files"]
    result = evaluate(args.trial_root / "public", initial, (args.trial_root / "final.txt").read_text(encoding="utf-8"), json.loads((args.trial_root / "telemetry.json").read_text(encoding="utf-8")))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
