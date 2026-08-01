#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only census, part 3.

(a) Split live-path .py churn into REAL machinery vs one-shot ceremony scripts
    (_append_/_open_/_close_/_receipt_/_register_/_scan_/_msg_/_read_/_tail_),
    which exist only to write one chat message or one ledger row.
(b) Prospective-goal lifecycle straight from the jsonl store.
"""
import json
import os
import re
import subprocess
import collections

ROOT = r"D:\WeilanSkillEvolution"
SINCE = "2026-07-11"
STORE = (r"D:\CodexData\home\method-state\memory\prospective\workspaces"
         r"\d431c38105a9a791\c36aecb1ff20")

def git(*args):
    return subprocess.run(["git", "-C", ROOT] + list(args),
                          capture_output=True).stdout.decode("utf-8", "replace")

COPY = re.compile(r"(^|/)(candidate|baseline|rollback|deployment|deployments)/")
LIVE = re.compile(r"^(skill/solve-with-weilan/|"
                  r"proposals/bounded-scheduler-v0\.1/impl/|"
                  r"proposals/mutual-aid-v0\.1/)")
CEREMONY = re.compile(r"/_(append|open|close|receipt|register|scan|msg|read|"
                      r"tail|concurrent_receipt|verify|blocker|probe)_")
PROBE = re.compile(r"(_probe_|/test_)")

res = {}
stat = git("log", "--since=%s" % SINCE, "--numstat", "--date=short",
           "--pretty=format:@@@%h|%ad")
cur = None
buckets = collections.defaultdict(collections.Counter)   # week -> kind -> lines
kind_files = collections.defaultdict(set)

def week_of(d):
    return {"2026-07-11": "w1", "2026-07-12": "w1", "2026-07-13": "w1",
            "2026-07-14": "w1", "2026-07-15": "w1", "2026-07-16": "w1",
            "2026-07-17": "w1"}.get(d, "w2" if d <= "2026-07-24" else "w3")

for line in stat.splitlines():
    if line.startswith("@@@"):
        cur = line[3:].split("|", 1)
        continue
    p = line.split("\t")
    if len(p) != 3 or p[0] == "-":
        continue
    a, d, f = p
    f = f.replace("\\", "/")
    if COPY.search(f) or not LIVE.match(f) or not f.endswith(".py"):
        continue
    n = int(a) + int(d)
    if PROBE.search(f):
        kind = "probe_or_test"
    elif CEREMONY.search(f):
        kind = "ceremony_oneshot"
    else:
        kind = "real_machinery"
    buckets[week_of(cur[1])][kind] += n
    kind_files[kind].add(f)

res["churn_by_week_kind"] = {w: dict(c) for w, c in sorted(buckets.items())}
res["distinct_files_by_kind"] = {k: len(v) for k, v in kind_files.items()}
tot = collections.Counter()
for w, c in buckets.items():
    tot.update(c)
res["churn_total_by_kind"] = dict(tot)

# ceremony scripts currently on disk (committed or not)
impl = os.path.join(ROOT, "proposals", "bounded-scheduler-v0.1", "impl")
on_disk = [f for f in os.listdir(impl)
           if f.endswith(".py") and CEREMONY.search("/" + f)]
res["ceremony_scripts_on_disk_now"] = len(on_disk)

# --- prospective lifecycle --------------------------------------------------
recs = []
for fn in sorted(os.listdir(STORE)):
    if not fn.endswith(".jsonl"):
        continue
    with open(os.path.join(STORE, fn), "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                recs.append((fn[:10], json.loads(line)))
            except Exception:
                pass
res["prospective_record_count"] = len(recs)
res["prospective_record_kinds"] = dict(collections.Counter(
    r.get("kind") or r.get("record_kind") or r.get("type") or "?"
    for _, r in recs))

hist = collections.defaultdict(list)
for day, r in recs:
    ref = r.get("goal_ref") or (r.get("goal") or {}).get("goal_ref")
    if not ref:
        continue
    st = (r.get("state") or r.get("to_state") or r.get("new_state")
          or r.get("kind") or "?")
    hist[ref].append((day, st))
final = collections.Counter()
open_goals = []
for ref, h in hist.items():
    last = h[-1][1]
    final[last] += 1
    if last in ("active", "registered", "register"):
        open_goals.append({"ref": ref, "registered": h[0][0],
                           "n_events": len(h), "age_days": None})
res["prospective_goal_count"] = len(hist)
res["prospective_final_states"] = dict(final)
res["prospective_open"] = sorted(open_goals, key=lambda g: g["registered"])

print(json.dumps(res, ensure_ascii=False, indent=2))
