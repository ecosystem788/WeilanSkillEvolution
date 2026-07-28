#!/usr/bin/env python3
"""Live canary for the Codex wake run-log UTF-8 fix (commit 286f3b9).

Read-only. Answers three questions about run logs produced AFTER the fix:
  (1) does every physical line json.loads, and is the CJK text real Chinese
      rather than cp936-misdecoded mojibake?
  (2) does the file decode as strict UTF-8 at the byte level?
  (3) is at least one CJK payload byte-identical to an independently written
      source (peer-chat.jsonl, appended by a different writer), so that
      "looks like Chinese" is corroborated rather than self-asserted?

The mojibake discriminator is not a tautology: a known-answer self-test runs
first and fails the whole script if the discriminator cannot separate real
Chinese from synthesised UTF-8-read-as-cp936 damage.

Bound on the discriminator, learned the hard way while writing it: most
Chinese UTF-8 byte streams are NOT valid cp936, so real console damage is
usually LOSSY - it comes back as mojibake plus U+FFFD, and cannot be caught by
a re-encode round trip. Hence three legs, not one:
  A. round trip (catches the lossless minority, e.g. "元寂计划" -> "鍏冨瘋璁″垝")
  B. U+FFFD count (the fingerprint of the lossy majority). Measured caveat:
     leg B cannot tell damage from DISCUSSION of damage - the 2026-07-27T14-51-49
     run trips it 4 times because Codex quotes the accident signature
     ("stop=闈欓?") inside a message about this very bug. Verdict therefore
     reports the count and requires a human to read the context, rather than
     failing closed on a substring.
  C. positive realness: common Chinese function characters (的 是 不 了 在 ...)
     are present. Mojibake alphabets essentially never contain them.
Leg C is the load-bearing one; A and B are negative evidence only.

Usage:
  python live_canary.py --root <impl dir> [--since 2026-07-27T10:44:34+09:00]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from datetime import datetime, timezone, timedelta

CJK = re.compile(r"[一-鿿]")
RUN_NAME = re.compile(r"^(\d{4}-\d{2}-\d{2})T(\d{2})-(\d{2})-(\d{2})\.jsonl$")


def looks_mojibake(text: str) -> bool:
    """True if text is plausibly UTF-8 bytes that were decoded as cp936.

    Round-trip test: re-encode as cp936 and try to read the bytes as UTF-8.
    Real Chinese almost never survives that (cp936 bytes are not valid UTF-8);
    mojibake does, because the bytes were UTF-8 to begin with.
    """
    cjk = "".join(CJK.findall(text))
    if len(cjk) < 4:
        return False
    try:
        raw = text.encode("cp936", errors="strict")
    except UnicodeEncodeError:
        return False
    try:
        recovered = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return False
    return bool(CJK.search(recovered))


COMMON = set("的是不了在有一我这那你他们和就也要说会为可以到就上下之与本回合据写签")
REPLACEMENT = "�"


def looks_real_chinese(text: str) -> bool:
    """Positive evidence: common Chinese characters are present (leg C)."""
    cjk = set(CJK.findall(text))
    return bool(cjk & COMMON)


def self_test() -> None:
    """Known-answer check: all three legs must separate real from damaged.

    Two damage models are exercised because both occur in practice:
    lossless (bytes happen to be valid cp936) and lossy (they are not, and the
    decoder substitutes U+FFFD).
    """
    real = "这一回合做了什么，下一回合从哪续，收据要如实写。"
    lossless = "元寂计划".encode("utf-8").decode("cp936")  # -> 鍏冨瘋璁″垝
    lossy = real.encode("utf-8").decode("cp936", errors="replace")

    assert not looks_mojibake(real), "self-test: real Chinese flagged by leg A"
    assert looks_mojibake(lossless), "self-test: leg A missed lossless mojibake"
    assert REPLACEMENT not in real, "self-test: real sample already damaged"
    assert REPLACEMENT in lossy, "self-test: leg B premise false"
    assert looks_real_chinese(real), "self-test: leg C rejected real Chinese"
    assert not looks_real_chinese(lossless), "self-test: leg C accepted mojibake"
    assert not looks_real_chinese(lossy), "self-test: leg C accepted lossy mojibake"


def run_started_at(path: pathlib.Path) -> datetime | None:
    m = RUN_NAME.match(path.name)
    if not m:
        return None
    day, hh, mm, ss = m.groups()
    # run file names are stamped in host local time (UTC+9 on this box)
    return datetime.fromisoformat(f"{day}T{hh}:{mm}:{ss}").replace(
        tzinfo=timezone(timedelta(hours=9))
    )


def detect_encoding(raw: bytes) -> str:
    """Encoding of the run log ON DISK, by BOM.

    Measured, not assumed: these files carry a .jsonl name but PowerShell 5.1
    redirection writes them as UTF-16LE with BOM. Reading them as UTF-8 -- the
    obvious thing to do with that extension -- yields zero parseable lines, so
    the disk encoding is a separate layer from the console decoding that commit
    286f3b9 fixed. Do not conflate the two.
    """
    if raw[:2] == b"\xff\xfe":
        return "utf-16-le"
    if raw[:2] == b"\xfe\xff":
        return "utf-16-be"
    if raw[:3] == b"\xef\xbb\xbf":
        return "utf-8-sig"
    return "utf-8"


def scan(path: pathlib.Path) -> dict:
    raw = path.read_bytes()
    encoding = detect_encoding(raw)
    result = {
        "file": path.name,
        "bytes": len(raw),
        "disk_encoding": encoding,
        "decodes_strict": True,
        "decode_error": None,
        "lines": 0,
        "json_ok": 0,
        "json_errors": [],
        "cjk_lines": 0,
        "mojibake_lines": [],
        "replacement_chars": 0,
        "real_chinese_lines": 0,
        "cjk_samples": [],
    }
    try:
        text = raw.decode(encoding, errors="strict")
        if encoding.startswith("utf-16"):
            text = text.lstrip("﻿")
    except UnicodeDecodeError as exc:
        result["decodes_strict"] = False
        result["decode_error"] = str(exc)
        text = raw.decode(encoding, errors="replace")

    for lineno, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        result["lines"] += 1
        try:
            json.loads(line)
            result["json_ok"] += 1
        except Exception as exc:  # noqa: BLE001 - report, do not classify
            if len(result["json_errors"]) < 5:
                result["json_errors"].append({"line": lineno, "error": str(exc)[:160]})
            continue
        if CJK.search(line):
            result["cjk_lines"] += 1
            if looks_mojibake(line) and len(result["mojibake_lines"]) < 5:
                result["mojibake_lines"].append(lineno)
            result["replacement_chars"] += line.count(REPLACEMENT)
            if looks_real_chinese(line):
                result["real_chinese_lines"] += 1
            if len(result["cjk_samples"]) < 3:
                snippet = "".join(CJK.findall(line))[:40]
                result["cjk_samples"].append({"line": lineno, "cjk": snippet})
    return result


def corroborate(run_paths: list[pathlib.Path], peer_chat: pathlib.Path) -> dict:
    """Find a Chinese payload present byte-identically in both writers.

    peer-chat.jsonl is appended by append_clocked_jsonl.py, a different writer
    than the PowerShell console pipe under test. A shared substring therefore
    corroborates the run log's decoding against an outside source.
    """
    out = {"checked_messages": 0, "matches": []}
    if not peer_chat.exists():
        out["error"] = "peer-chat.jsonl not found"
        return out
    needles = []
    for line in peer_chat.read_text(encoding="utf-8").splitlines()[-60:]:
        try:
            rec = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        text = rec.get("text") or ""
        # Needles must be CONTIGUOUS runs of the original text. An earlier
        # version concatenated CJK.findall(), which drops punctuation and can
        # therefore never match verbatim - it scored 0/59 and looked like a
        # finding about the logs when it was a defect in the probe.
        runs = CJK.pattern and re.findall(r"[一-鿿]{12,}", text)
        if runs:
            needles.append((rec.get("from"), rec.get("time"), runs[0][:24]))
    out["checked_messages"] = len(needles)
    blobs = {}
    for p in run_paths:
        raw = p.read_bytes()
        blobs[p.name] = raw.decode(detect_encoding(raw), errors="replace")
    for who, when, needle in needles:
        for name, blob in blobs.items():
            if needle in blob:
                out["matches"].append(
                    {"from": who, "time": when, "needle": needle, "found_in": name}
                )
                break
        if len(out["matches"]) >= 5:
            break
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="bounded-scheduler impl directory")
    ap.add_argument(
        "--since",
        default="2026-07-27T10:44:34+09:00",
        help="only inspect runs started at/after this instant (fix commit time)",
    )
    ap.add_argument(
        "--control",
        type=int,
        default=10,
        help="how many pre-fix runs to scan as a control group (0 to skip)",
    )
    args = ap.parse_args()

    self_test()

    root = pathlib.Path(args.root)
    runs_dir = root / "wake-codex-runs"
    since = datetime.fromisoformat(args.since)

    post_fix, pre_fix = [], []
    for path in sorted(runs_dir.glob("*.jsonl")):
        started = run_started_at(path)
        if started is None:
            continue
        (post_fix if started >= since else pre_fix).append(path)

    # Control group: without it, "post-fix runs are clean" cannot be told apart
    # from "these logs were never damaged". Take the runs immediately before the
    # cut, so the only material difference is the fix itself.
    control = pre_fix[-args.control :] if args.control and pre_fix else []

    report = {
        "fix_commit": "286f3b9",
        "since": args.since,
        "post_fix_runs": len(post_fix),
        "self_test": "passed",
        "runs": [scan(p) for p in post_fix],
        "pre_fix_control": [scan(p) for p in control],
    }
    report["corroboration"] = corroborate(post_fix, root / "peer-chat.jsonl")

    verdict = {
        "decodes_strict_all": all(r["decodes_strict"] for r in report["runs"]),
        "json_errors_total": sum(len(r["json_errors"]) for r in report["runs"]),
        "cjk_lines_total": sum(r["cjk_lines"] for r in report["runs"]),
        "mojibake_lines_total": sum(len(r["mojibake_lines"]) for r in report["runs"]),
        # reported, deliberately NOT a green/red gate - see leg B caveat above
        "replacement_chars_total": sum(r["replacement_chars"] for r in report["runs"]),
        "replacement_char_runs": [
            r["file"] for r in report["runs"] if r["replacement_chars"]
        ],
        "real_chinese_lines_total": sum(r["real_chinese_lines"] for r in report["runs"]),
        "corroborated_matches": len(report["corroboration"].get("matches", [])),
        "control_runs": len(report["pre_fix_control"]),
        "control_damaged_runs": sum(
            1
            for r in report["pre_fix_control"]
            if r["mojibake_lines"] or r["replacement_chars"]
        ),
        "control_real_chinese_lines": sum(
            r["real_chinese_lines"] for r in report["pre_fix_control"]
        ),
    }
    verdict["green"] = (
        report["post_fix_runs"] > 0
        and verdict["decodes_strict_all"]
        and verdict["json_errors_total"] == 0
        and verdict["cjk_lines_total"] > 0
        and verdict["mojibake_lines_total"] == 0
        and verdict["real_chinese_lines_total"] > 0
        and verdict["corroborated_matches"] > 0
    )
    report["verdict"] = verdict

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if verdict["green"] else 1


if __name__ == "__main__":
    sys.exit(main())
