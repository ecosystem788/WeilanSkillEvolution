#!/usr/bin/env python3
"""Read-only: measure the false-positive boundary of the widened PATH_RE lookbehind.

Answers, with the live ledger and hand-built adversarial strings:
  1. which character precedes the ':' in each citation the current gate drops;
  2. whether the widened pattern (colon removed from the char class, drive-letter
     guard added) survives drive-letter / URL / mixed-prefix adversarial cases;
  3. how much additional recall an *unguarded* colon widening would buy, and how
     many false positives it would admit.

Writes a JSON report; changes nothing.
"""

from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path
import re

IMPL = Path(r"D:\WeilanSkillEvolution\proposals\bounded-scheduler-v0.1\impl")
SPEC = importlib.util.spec_from_file_location(
    "gate", IMPL / "cited_artifact_receipt_check.py"
)
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)

BODY = (
    r"(?:"
    r"(?:" + "|".join(re.escape(item) for item in gate.DIRECTORIES) + r")/"
    r"[A-Za-z0-9_./+\-]+|"
    + "|".join(re.escape(item) for item in gate.ROOT_FILES)
    + r")"
)
# Guarded widening: colon dropped from the class, drive letters re-blocked.
GUARDED = re.compile(r"(?<![A-Za-z0-9_./\\-])(?<![A-Za-z0-9]:)" + BODY)
# Unguarded widening: colon simply dropped from the class.
UNGUARDED = re.compile(r"(?<![A-Za-z0-9_./\\-])" + BODY)

ADVERSARIAL = [
    ("drive_letter_backslash", r"C:\Users\zy\proposals\x.md"),
    ("drive_letter_forward", "D:proposals/bounded-scheduler-v0.1/impl/x.py"),
    ("drive_letter_spaced_forward", "D:/WeilanSkillEvolution/proposals/x.md"),
    ("http_url", "http://example.com/proposals/fake-v0.1/x.md"),
    ("https_url", "https://example.com/docs/fake.md"),
    ("git_scp_like", "git@host:proposals/x.md"),
    ("cjk_label", "全文路径:proposals/real-v0.1/FINDING.md"),
    ("ascii_label", "spec:proposals/real-v0.1/FINDING.md"),
    ("bracket_label", "【证据】:proposals/real-v0.1/FINDING.md"),
    ("bare", "proposals/real-v0.1/FINDING.md"),
    ("source_ref_suffix", "peer-chat.jsonl:126@2026-07-10 22:08:26"),
]


def extract(pattern: re.Pattern[str], text: str) -> list[str]:
    """Mirror gate.cited_paths() but with a caller-supplied pattern."""
    found: list[str] = []
    for match in pattern.finditer(text):
        candidate = gate._strip_tail(match.group(0))
        if not candidate.lower().endswith(gate.EXTENSIONS):
            continue
        from pathlib import PurePosixPath

        path = PurePosixPath(candidate)
        if path.is_absolute() or any(p in ("", ".", "..") for p in path.parts):
            continue
        normalized = path.as_posix()
        if normalized not in found:
            found.append(normalized)
    return found


def main() -> int:
    rows, _errors = gate._ledger_rows(IMPL / "peer-chat.jsonl")

    pre_colon: dict[str, int] = {}
    guarded_gain = 0
    unguarded_extra: list[dict[str, object]] = []
    unguarded_extra_total = 0
    for line_number, _raw, record in rows:
        text = record.get("text")
        if not isinstance(text, str):
            continue
        base = set(gate.cited_paths(text))
        g = extract(GUARDED, text)
        u = extract(UNGUARDED, text)
        for p in g:
            if p in base:
                continue
            guarded_gain += 1
            idx = text.find(p)
            # character immediately before the ':' that precedes the path
            key = text[max(0, idx - 2): idx - 1] if idx >= 2 else ""
            klass = (
                "ascii_alnum" if key.isascii() and key.isalnum()
                else "non_ascii" if key and not key.isascii()
                else "other_ascii" if key
                else "line_start"
            )
            pre_colon[klass] = pre_colon.get(klass, 0) + 1
        extra = [p for p in u if p not in g and p not in base]
        if extra:
            unguarded_extra_total += len(extra)
            if len(unguarded_extra) < 12:
                idx0 = text.find(extra[0])
                unguarded_extra.append(
                    {
                        "physical_line": line_number,
                        "from": record.get("from"),
                        "time": record.get("time"),
                        "paths": extra[:4],
                        "context": text[max(0, idx0 - 24): idx0 + 40],
                    }
                )

    adversarial = {
        name: {
            "gate": gate.cited_paths(text),
            "guarded": extract(GUARDED, text),
            "unguarded": extract(UNGUARDED, text),
        }
        for name, text in ADVERSARIAL
    }

    payload = {
        "probe": "lookbehind_boundary",
        "authority": "read_only_report",
        "ledger_rows": len(rows),
        "guarded_pattern": GUARDED.pattern,
        "unguarded_pattern": UNGUARDED.pattern,
        "guarded_recovered_citations": guarded_gain,
        "guarded_recovered_prefix_classes": pre_colon,
        "unguarded_extra_citations": unguarded_extra_total,
        "unguarded_extra_examples": unguarded_extra,
        "adversarial": adversarial,
        "boundary": (
            "measures extraction only; says nothing about whether an extracted "
            "path is reachable, nor about non-ASCII path names, which stay "
            "invisible to every pattern here"
        ),
    }
    out = Path(
        r"D:\WeilanSkillEvolution\proposals\cited-artifact-clone-reachability-v0.1"
        r"\_probe_20260801_lookbehind_boundary.out.json"
    )
    io.open(out, "w", encoding="utf-8").write(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    )
    print(
        json.dumps(
            {
                "guarded_recovered_citations": guarded_gain,
                "guarded_recovered_prefix_classes": pre_colon,
                "unguarded_extra_citations": unguarded_extra_total,
            },
            ensure_ascii=False,
        )
    )
    for name, res in adversarial.items():
        print(name, "| gate", res["gate"], "| guarded", res["guarded"], "| unguarded", res["unguarded"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
