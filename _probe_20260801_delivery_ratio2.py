#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only census, part 2: churn on LIVE machinery only + prospective-goal
lifecycle (registered / satisfied / collapsed / still-open).

Excludes candidate/ baseline/ rollback/ deployment/ copies, which are whole-file
snapshots and dominate raw numstat.
"""
import json
import os
import re
import subprocess
import collections

ROOT = r"D:\WeilanSkillEvolution"
SINCE = "2026-07-11"

def git(*args):
    return subprocess.run(["git", "-C", ROOT] + list(args),
                          capture_output=True).stdout.decode("utf-8", "replace")

COPY = re.compile(r"(^|/)(candidate|baseline|rollback|deployment|deployments|"
                  r"_bak|archive)/")
LIVE = re.compile(r"^(skill/solve-with-weilan/|"
                  r"proposals/bounded-scheduler-v0\.1/impl/|"
                  r"proposals/mutual-aid-v0\.1/)")
PROBE = re.compile(r"(_probe_|/test_|^test_)")

res = {}

stat = git("log", "--since=%s" % SINCE, "--numstat", "--date=short",
           "--pretty=format:@@@%h|%ad|%s")
cur = None
live_churn = collections.Counter()
live_days = collections.Counter()
live_commits = {}
for line in stat.splitlines():
    if line.startswith("@@@"):
        cur = line[3:].split("|", 2)
        continue
    parts = line.split("\t")
    if len(parts) != 3 or parts[0] == "-":
        continue
    a, d, f = parts
    f = f.replace("\\", "/")
    if COPY.search(f) or not LIVE.match(f):
        continue
    if PROBE.search(f) or not f.endswith(".py"):
        continue
    n = int(a) + int(d)
    live_churn[f] += n
    live_days[cur[1]] += n
    live_commits.setdefault(cur[0], {"date": cur[1], "subject": cur[2][:80],
                                     "lines": 0, "files": []})
    live_commits[cur[0]]["lines"] += n
    live_commits[cur[0]]["files"].append(f.split("/")[-1])

res["live_machinery_churn_by_file"] = dict(sorted(live_churn.items(),
                                                  key=lambda kv: -kv[1]))
res["live_machinery_churn_total"] = sum(live_churn.values())
res["live_machinery_churn_by_day"] = dict(sorted(live_days.items()))
res["live_machinery_commits"] = sorted(live_commits.values(),
                                       key=lambda c: c["date"])
res["live_machinery_commit_count"] = len(live_commits)

# --- prospective goals lifecycle -------------------------------------------
home = os.environ.get("CODEX_HOME") or os.path.join(
    os.path.expanduser("~"), ".codex")
ms = os.path.join(home, "method-state")
found = []
for dp, _, fn in os.walk(ms):
    for f in fn:
        if "prospect" in f.lower():
            found.append(os.path.join(dp, f))
res["prospective_files"] = found[:20]

states = collections.Counter()
goals = {}
for path in found:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            txt = fh.read()
    except Exception as e:
        continue
    for line in txt.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            o = json.loads(line)
        except Exception:
            continue
        ref = o.get("goal_ref") or o.get("ref")
        st = o.get("state") or o.get("new_state")
        if ref:
            goals.setdefault(ref, {"first": None, "states": []})
            if st:
                goals[ref]["states"].append(st)
for ref, g in goals.items():
    final = g["states"][-1] if g["states"] else "unknown"
    states[final] += 1
res["prospective_state_counts"] = dict(states)
res["prospective_goal_count"] = len(goals)
res["prospective_open_refs"] = sorted(
    r for r, g in goals.items()
    if (g["states"][-1] if g["states"] else "") in ("active", "registered", ""))

print(json.dumps(res, ensure_ascii=False, indent=2))
