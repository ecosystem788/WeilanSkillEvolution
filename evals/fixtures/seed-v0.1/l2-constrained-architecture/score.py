import argparse
import json
from pathlib import Path
from hidden.check import evaluate


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--trial-root", type=Path, required=True)
    args = p.parse_args()
    result = evaluate(args.trial_root / "public", args.trial_root / "method-state")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
