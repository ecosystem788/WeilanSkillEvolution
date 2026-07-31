# -*- coding: utf-8 -*-
"""Read-only probe B: are any never-committed ledger rows load-bearing?

Two questions, both answered from sources, not from prose:
  Q1  peer-chat.corrections.jsonl — peer_health_wake.py cites rows by 1-based
      line number ("<path>:4"). Which of the cited line numbers live in rows that
      no commit contains? A third-party clone resolves those refs to a DIFFERENT
      row (or to nothing), because the committed file is shorter.
  Q2  concurrent-receipts.jsonl / blocker-quarantine.jsonl / peer-health-alerts.jsonl
      — dump the never-committed rows' identifying fields so the loss is nameable.
Output: _probe_20260801_uncommitted_row_weight.out.json
"""
import json
import os
import subprocess
import sys

REPO = r"D:\WeilanSkillEvolution"
IMPL = "proposals/bounded-scheduler-v0.1/impl"
OUT = os.path.join(REPO, "proposals", "ledger-rows-never-committed-v0.1",
                   "_probe_20260801_uncommitted_row_weight.out.json")
LEDGERS = ["peer-chat.corrections.jsonl", "concurrent-receipts.jsonl",
           "blocker-quarantine.jsonl", "peer-health-alerts.jsonl"]


def git(*args):
    r = subprocess.run(["git", "-C", REPO] + list(args), capture_output=True)
    return None if r.returncode != 0 else r.stdout


def rows(b):
    if b is None:
        return []
    return [ln for ln in b.decode("utf-8", "replace").replace("\r\n", "\n").split("\n") if ln.strip()]


def summarise(raw):
    try:
        d = json.loads(raw)
    except Exception:
        return {"unparsed": raw[:120]}
    keep = ("time", "id", "from", "kind", "event", "reason", "corrects", "line",
            "peer", "state", "frame_id", "receipt_id", "source")
    return {k: d[k] for k in keep if k in d}


def main():
    head = git("rev-parse", "HEAD").decode().strip()
    result = {"probe": "uncommitted_row_weight", "read_only": True, "head": head,
              "ledgers": {}, "q1_citation_resolution": None}

    for name in LEDGERS:
        path = "%s/%s" % (IMPL, name)
        disk = rows(open(os.path.join(REPO, path.replace("/", os.sep)), "rb").read())
        committed = set()
        for c in (git("rev-list", "--all", "--", path) or b"").decode().split():
            committed.update(rows(git("show", "%s:%s" % (c, path))))
        never = [(i + 1, ln) for i, ln in enumerate(disk) if ln not in committed]
        result["ledgers"][name] = {
            "disk_rows": len(disk),
            "never_committed_line_numbers": [i for i, _ in never],
            "never_committed_rows": [summarise(ln) for _, ln in never],
        }

    # Q1: peer_health_wake emits "<corrections path>:<1-based row>" refs, so the whole
    # 1..N row space is citable. We do NOT invoke peer_health_wake here: it is a
    # producer (it appends to peer-health-alerts.jsonl) and this probe must stay
    # read-only. Refs actually observed in this turn's sentinel run were 4, 6, 7.
    head_rows = rows(git("show", "%s:%s/peer-chat.corrections.jsonl" % (head, IMPL)))
    disk_rows = rows(open(os.path.join(REPO, IMPL.replace("/", os.sep),
                                       "peer-chat.corrections.jsonl"), "rb").read())
    cited = list(range(1, len(disk_rows) + 1))
    resolution = []
    for n in cited:
        d_row = summarise(disk_rows[n - 1]) if 0 < n <= len(disk_rows) else None
        h_row = summarise(head_rows[n - 1]) if 0 < n <= len(head_rows) else None
        resolution.append({
            "cited_line": n,
            "resolves_in_worktree_to": d_row,
            "resolves_in_HEAD_to": h_row,
            "same_row": d_row == h_row,
        })
    result["q1_citation_resolution"] = {
        "citable_lines": cited,
        "refs_observed_in_this_turn_sentinel_run": [4, 6, 7],
        "worktree_rows": len(disk_rows),
        "head_rows": len(head_rows),
        "resolution": resolution,
        "all_cited_lines_resolve_identically": all(x["same_row"] for x in resolution) if resolution else None,
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=1, sort_keys=True)
        fh.write("\n")
    print(json.dumps(result["q1_citation_resolution"], ensure_ascii=False, indent=1))
    for k, v in result["ledgers"].items():
        print(k, "never-committed lines:", v["never_committed_line_numbers"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
