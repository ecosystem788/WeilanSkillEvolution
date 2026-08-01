#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only census: discussion volume vs landed change, 2026-07-11..2026-08-01.

Answers 云's peer-chat question 2026-08-01 09:20:13 with measured ledger/git facts
instead of impression. Writes JSON to stdout; changes nothing.
"""
import json
import os
import re
import subprocess
import collections

ROOT = r"D:\WeilanSkillEvolution"
IMPL = os.path.join(ROOT, "proposals", "bounded-scheduler-v0.1", "impl")
SINCE = "2026-07-11"

def git(*args):
    out = subprocess.run(["git", "-C", ROOT] + list(args),
                         capture_output=True)
    return out.stdout.decode("utf-8", "replace")

res = {}

# --- 1. commits per day, and what each commit touched -----------------------
log = git("log", "--since=%s" % SINCE, "--date=short",
          "--pretty=format:@@@%H|%ad|%s", "--name-only")
commits = []
cur = None
for line in log.splitlines():
    if line.startswith("@@@"):
        h, d, s = line[3:].split("|", 2)
        cur = {"sha": h[:7], "date": d, "subject": s, "files": []}
        commits.append(cur)
    elif line.strip() and cur is not None:
        cur["files"].append(line.strip())

MACHINERY = re.compile(r"(impl/[^/]+\.py$|/scripts/.*\.py$|verify_.*\.py$|"
                       r"peer_health_wake\.py$|wake_brief\.py$)")
PROBE = re.compile(r"(_probe_|\.out\.json$|test_)")
DOC = re.compile(r"(FINDING\.md$|CONVENTION\.md$|\.md$|\.txt$)")
LEDGER = re.compile(r"(peer-chat\.jsonl|inbox.*\.jsonl|\.jsonl$)")

def classify(files):
    kinds = set()
    for f in files:
        if MACHINERY.search(f) and not PROBE.search(f):
            kinds.add("machinery")
        elif PROBE.search(f):
            kinds.add("probe_or_test")
        elif LEDGER.search(f):
            kinds.add("ledger")
        elif DOC.search(f):
            kinds.add("doc")
        else:
            kinds.add("other")
    return kinds

by_day = collections.Counter()
kind_count = collections.Counter()
machinery_commits = []
for c in commits:
    by_day[c["date"]] += 1
    k = classify(c["files"])
    c["kinds"] = sorted(k)
    if "machinery" in k:
        kind_count["touches_machinery"] += 1
        machinery_commits.append({"sha": c["sha"], "date": c["date"],
                                  "subject": c["subject"][:90],
                                  "n_files": len(c["files"])})
    elif "probe_or_test" in k:
        kind_count["probe_or_test_only"] += 1
    elif "doc" in k:
        kind_count["doc_only"] += 1
    elif "ledger" in k:
        kind_count["ledger_only"] += 1
    else:
        kind_count["other"] += 1

res["window"] = {"since": SINCE, "until": "2026-08-01", "n_commits": len(commits)}
res["commits_per_day"] = dict(sorted(by_day.items()))
res["commit_class_counts"] = dict(kind_count)
res["machinery_commits"] = machinery_commits

# --- 2. proposals/ directories: which ones produced a machinery change ------
prop_dir = os.path.join(ROOT, "proposals")
props = {}
for name in sorted(os.listdir(prop_dir)):
    p = os.path.join(prop_dir, name)
    if not os.path.isdir(p):
        continue
    files = []
    for dp, _, fn in os.walk(p):
        for f in fn:
            files.append(os.path.relpath(os.path.join(dp, f), prop_dir).replace("\\", "/"))
    has_finding = any(f.endswith("FINDING.md") for f in files)
    has_convention = any(f.endswith("CONVENTION.md") for f in files)
    has_impl = any(f.endswith(".py") and "_probe_" not in f and
                   not os.path.basename(f).startswith("test_") for f in files)
    # first commit date for this dir
    d = git("log", "--diff-filter=A", "--date=short", "--pretty=format:%ad",
            "--", "proposals/%s" % name)
    dates = [x for x in d.splitlines() if x.strip()]
    props[name] = {
        "first_seen": dates[-1] if dates else None,
        "last_seen": dates[0] if dates else None,
        "n_files": len(files),
        "has_finding": has_finding,
        "has_convention": has_convention,
        "has_nonprobe_py": has_impl,
    }
res["proposals"] = props
res["proposal_totals"] = {
    "total": len(props),
    "created_in_window": sum(1 for v in props.values()
                             if v["first_seen"] and v["first_seen"] >= SINCE),
    "finding_only_no_py": sum(1 for v in props.values()
                              if v["has_finding"] and not v["has_nonprobe_py"]),
    "with_nonprobe_py": sum(1 for v in props.values() if v["has_nonprobe_py"]),
}

# --- 3. peer-chat volume per day, per author -------------------------------
chat = os.path.join(IMPL, "peer-chat.jsonl")
day_author = collections.Counter()
chars_author = collections.Counter()
tag_counter = collections.Counter()
with open(chat, "r", encoding="utf-8") as fh:
    for line in fh:
        line = line.strip()
        if not line:
            continue
        try:
            m = json.loads(line)
        except Exception:
            continue
        t = str(m.get("time", ""))[:10].replace("/", "-")
        if t < SINCE:
            continue
        who = m.get("from", "?")
        day_author[(t, who)] += 1
        chars_author[who] += len(str(m.get("text", "")))
        txt = str(m.get("text", ""))
        for tag in ("【提案", "【同意", "【反对", "【FINDING", "【裁断", "【核验"):
            if tag in txt:
                tag_counter[tag] += 1
days = sorted(set(d for d, _ in day_author))
res["chat_per_day"] = {d: {w: day_author[(d, w)]
                           for w in ("claude", "codex", "owner")
                           if day_author[(d, w)]} for d in days}
res["chat_totals"] = {
    "messages": sum(day_author.values()),
    "chars_by_author": dict(chars_author),
    "tag_counts": dict(tag_counter),
}

# --- 4. probe scripts written in window ------------------------------------
probes = git("log", "--since=%s" % SINCE, "--diff-filter=A", "--name-only",
             "--pretty=format:")
probe_files = [f for f in set(probes.splitlines()) if "_probe_" in f]
res["probe_files_added"] = {"count": len(probe_files),
                            "sample": sorted(probe_files)[:12]}

# --- 5. line churn on machinery files --------------------------------------
stat = git("log", "--since=%s" % SINCE, "--numstat", "--pretty=format:@@@%H")
churn = collections.Counter()
for line in stat.splitlines():
    if line.startswith("@@@") or not line.strip():
        continue
    parts = line.split("\t")
    if len(parts) != 3:
        continue
    a, d, f = parts
    if a == "-" :
        continue
    if MACHINERY.search(f) and "_probe_" not in f:
        churn[f] += int(a) + int(d)
res["machinery_churn_lines"] = dict(sorted(churn.items(),
                                           key=lambda kv: -kv[1])[:15])
res["machinery_churn_total"] = sum(churn.values())

print(json.dumps(res, ensure_ascii=False, indent=2))
