#!/usr/bin/env python3
"""Read-only: how many ledger citations does PATH_RE's lookbehind silently drop?

Observed on claude 2026-08-01T07:21:03+09:00: a message naming three repo paths
reported cited_path_count=1. PATH_RE's negative lookbehind excludes ':' (there to
avoid matching inside 'C:/...' and 'http://...'), so the common receipt habit of
writing 'label:proposals/x/y.py' makes the citation invisible to the gate.

This probe measures the loss with a lookbehind that keeps the drive/scheme guard
but stops treating a bare ASCII colon as a path character.
"""
from __future__ import annotations

import io
import json
import re
from collections import Counter
from pathlib import Path
import sys

IMPL = Path(r"D:\WeilanSkillEvolution\proposals\bounded-scheduler-v0.1\impl")
sys.path.insert(0, str(IMPL))

import cited_artifact_receipt_check as gate  # noqa: E402

# same alternation body as gate.PATH_RE, rebuilt from the same constants; only the
# lookbehind differs -- a colon blocks the match only when itself preceded by an
# alnum (drive letter 'C:' / scheme 'http:'), which is what the guard was for.
BODY = (
    r"(?:" + "|".join(re.escape(item) for item in gate.DIRECTORIES) + r")/"
    r"[A-Za-z0-9_./+\-]+|"
    + "|".join(re.escape(item) for item in gate.ROOT_FILES)
)
WIDE = re.compile(r"(?<![A-Za-z0-9_./\\-])(?<![A-Za-z0-9]:)(?:" + BODY + r")")
assert re.compile(r"(?<![A-Za-z0-9_./:\\-])(?:" + BODY + r")").pattern == gate.PATH_RE.pattern, \
    "rebuilt body no longer equals the gate's own pattern -- probe is measuring something else"


def wide_paths(text: object) -> list[str]:
    if not isinstance(text, str):
        return []
    found: list[str] = []
    for match in WIDE.finditer(text):
        candidate = gate._strip_tail(match.group(0))
        if not candidate.lower().endswith(gate.EXTENSIONS):
            continue
        if candidate not in found:
            found.append(candidate)
    return found


def main() -> int:
    rows, _errors = gate._ledger_rows(IMPL / "peer-chat.jsonl")
    lost_total = 0
    messages_with_loss = 0
    prefix_counter: Counter[str] = Counter()
    examples: list[dict[str, object]] = []
    for line_number, _raw, record in rows:
        text = record.get("text")
        seen = set(gate.cited_paths(text))
        wide = wide_paths(text)
        lost = [p for p in wide if p not in seen]
        if not lost:
            continue
        messages_with_loss += 1
        lost_total += len(lost)
        if isinstance(text, str):
            for p in lost:
                idx = text.find(p)
                prefix_counter[text[max(0, idx - 1):idx]] += 1
        if len(examples) < 8:
            examples.append(
                {
                    "physical_line": line_number,
                    "from": record.get("from"),
                    "time": record.get("time"),
                    "seen_count": len(seen),
                    "lost": lost[:6],
                }
            )

    payload = {
        "probe": "colon_lookbehind_loss",
        "authority": "read_only_report",
        "gate_pattern": gate.PATH_RE.pattern,
        "widened_pattern": WIDE.pattern,
        "ledger_rows": len(rows),
        "messages_with_dropped_citations": messages_with_loss,
        "dropped_citation_total": lost_total,
        "dropping_prefix_char_counts": dict(prefix_counter.most_common()),
        "examples": examples,
        "boundary": "measures only the colon class of loss; non-ASCII path names stay invisible to both patterns and are not counted",
    }
    io.open(
        r"D:\WeilanSkillEvolution\proposals\cited-artifact-clone-reachability-v0.1\_probe_20260801_colon_lookbehind_loss.out.json",
        "w",
        encoding="utf-8",
    ).write(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    print(json.dumps({k: payload[k] for k in (
        "messages_with_dropped_citations", "dropped_citation_total",
        "dropping_prefix_char_counts")}, ensure_ascii=False))
    for e in examples[:4]:
        print(e["from"], e["time"], "seen", e["seen_count"], "lost", e["lost"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
