#!/usr/bin/env python3
"""List every peer-chat record mentioning unresolvable_component, in order,
so the adjudication history of the un-landed checker change can be read."""
import json
import subprocess
from pathlib import Path
import pathlib

REPO = pathlib.Path(
    subprocess.run(["git", "rev-parse", "--show-toplevel"],
                   cwd=str(pathlib.Path(__file__).resolve().parent),
                   capture_output=True, check=True)
    .stdout.decode("utf-8").strip()
)
LEDGER = REPO / "proposals/bounded-scheduler-v0.1/impl/peer-chat.jsonl"
TERM = "unresolvable_component"

with LEDGER.open(encoding="utf-8") as fh:
    for lineno, raw in enumerate(fh, 1):
        raw = raw.strip()
        if not raw:
            continue
        try:
            rec = json.loads(raw)
        except Exception:  # noqa: BLE001
            continue
        text = rec.get("text") or ""
        if TERM not in text:
            continue
        idx = text.find(TERM)
        print("=" * 70)
        print(f"line={lineno} from={rec.get('from')} time={rec.get('time')}")
        print("HEADLINE:", text.split("\n", 1)[0][:160])
        print("CONTEXT:", text[max(0, idx - 400): idx + 400].replace("\n", " "))
