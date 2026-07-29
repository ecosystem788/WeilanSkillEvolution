"""Cross-reference: which enumeration anchor sees which co-signed execution.

Three anchors have been used or proposed for "the set of co-signed precise-text
executions":
  (1) the hand-written EXECUTIONS list inside _audit_cosign_durability.py  -> 5
  (2) execution dirs holding preflight-state.json on disk                  -> 7
  (3) strong-binding 【同意】 messages in the governance ledger            -> 12 (9 parsed)

This prints the coverage matrix so the disagreement is a table, not a claim.

Zero authority. Read-only. Exits 0 always.
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))

# (1) verbatim from _audit_cosign_durability.py's EXECUTIONS list
AUDIT5 = [
    "proposals/cosign-bytewise-binding-v0.1/execution-v0.6",
    "proposals/codex-cold-start-scope-ambiguity-v0.1/execution",
    "proposals/cron-wrapper-portability-v0.1/execution",
    "proposals/charter-daily-push-v0.1/execution",
    "proposals/cosign-bytewise-binding-v0.1/execution-v0.7",
]

# (3) admitted rows from _probe_20260729_extended_durability_audit.py
LEDGER = [
    ("L2601", "2026-07-26 08:21:00", "CHARTER.md"),
    ("L2734", "2026-07-27T13:18:41", ".github/workflows/scheduler-windows-regressions.yml"),
    ("L2740", "2026-07-27T14:00:55", "proposals/bounded-scheduler-v0.1/impl/test_wake_sentinel.py"),
    ("L2749", "2026-07-27T15:27:41", "proposals/bounded-scheduler-v0.1/impl/run_wake_cron.ps1"),
    ("L2755", "2026-07-27T16:37:54", "proposals/bounded-scheduler-v0.1/impl/wake_codex.ps1"),
    ("L2761", "2026-07-27T18:44:56", "proposals/cosign-bytewise-binding-v0.1/CONVENTION.md"),
    ("L2769", "2026-07-27T20:18:13", "CHARTER.md"),
    ("L2781", "2026-07-27T23:30:47", "CHARTER.md"),
    ("L2940", "2026-07-29T07:25:41", "CHARTER.md"),
]


def main():
    # (2) walk disk for preflight-state.json anchors
    anchors = {}
    for root, _dirs, files in os.walk(os.path.join(REPO, "proposals")):
        if "preflight-state.json" not in files:
            continue
        rel = os.path.relpath(root, REPO).replace(os.sep, "/")
        with io.open(os.path.join(root, "preflight-state.json"),
                     encoding="utf-8-sig") as fh:
            st = json.load(fh)
        anchors.setdefault(st.get("target"), []).append(rel)

    print("== anchor (2): execution dirs holding preflight-state.json : %d =="
          % sum(len(v) for v in anchors.values()))
    for target in sorted(anchors):
        for d in sorted(anchors[target]):
            mark = "  [in audit's 5]" if d in AUDIT5 else "  [NOT in audit's 5]"
            print("  %-56s %s%s" % (d, target, mark))

    print("\n== coverage matrix: ledger co-sign -> disk anchor -> audit's 5 ==")
    print("%-6s %-20s %-52s %-10s %s"
          % ("chatL", "co-signed", "target", "anchor?", "in audit's 5?"))
    no_anchor = []
    for ln, when, target in LEDGER:
        dirs = anchors.get(target, [])
        has_anchor = "yes" if dirs else "NO"
        in5 = "yes" if any(d in AUDIT5 for d in dirs) else "no"
        if not dirs:
            no_anchor.append((ln, when, target))
        print("%-6s %-20s %-52s %-10s %s" % (ln, when, target, has_anchor, in5))

    print("\n  ledger co-signs with NO preflight-state.json anchor at all: %d"
          % len(no_anchor))
    for ln, when, target in no_anchor:
        print("    %s  %s  %s" % (ln, when, target))
    # Per-target arithmetic, computed rather than asserted: an anchor keyed on
    # target path cannot distinguish successive revisions of the same file, so
    # "has an anchor" is not the same as per-execution coverage.
    print("\n== per-target: ledger co-signs vs anchors ==")
    print("   (RESIDUE rows are strong-binding co-signs whose final digest this")
    print("    probe could not parse; they are counted, not silently dropped.)")
    residue_targets = [("L2764", "2026-07-27T19:17:30", "CHARTER.md")]
    counts = {}
    for _ln, _when, target in LEDGER:
        counts.setdefault(target, [0, 0])[0] += 1
    for _ln, _when, target in residue_targets:
        counts.setdefault(target, [0, 0])[0] += 1
    for target in counts:
        counts[target][1] = len(anchors.get(target, []))
    short = 0
    for target in sorted(counts):
        n_cosign, n_anchor = counts[target]
        gap = n_cosign - n_anchor
        short += max(0, gap)
        flag = "  <-- %d co-sign(s) with no distinct anchor" % gap if gap > 0 else ""
        print("  %-52s co-signs=%d anchors=%d%s" % (target, n_cosign, n_anchor, flag))
    print("\n  total co-signed executions with no distinct anchor: %d" % short)
    return 0


if __name__ == "__main__":
    sys.exit(main())
