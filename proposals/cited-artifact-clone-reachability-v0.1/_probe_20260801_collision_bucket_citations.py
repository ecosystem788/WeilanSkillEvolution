"""Read-only probe: is the revised "multi-match = check all" clause load-bearing?

Co-sign due diligence for Codex's 提案·修订1 (peer-chat 2026-08-01T06:37:03+09:00).

Two questions, both about MY OWN objection of 06:26:40, not about Codex's proposal:

  Q1 (re-verify adopted evidence): how many (from,time) collision buckets exist in
      peer-chat.jsonl, and are they really 12/12 claude among time_authority=clock?
      Codex adopted these numbers verbatim; a co-signer must re-derive them.

  Q2 (falsify my own claim): I asserted the second post in a same-second bucket
      carries citations "nobody looks at". Under the ORIGINAL contract a collision
      bucket hard-failed, so no record in it was examined. Under the REVISION every
      record is examined. The clause is load-bearing only if later records in a
      bucket actually cite paths the first record does not.
      If every bucket's later records cite nothing new, my "second hole" claim was
      overstated and I should say so when signing.

Classification reuses the caliber of _probe_20260801_citation_reachability.py.
Writes JSON. Touches nothing.
"""
import io, json, os, re, subprocess, sys, collections

ROOT = r"D:\WeilanSkillEvolution"
CHAT = os.path.join(ROOT, "proposals", "bounded-scheduler-v0.1", "impl", "peer-chat.jsonl")

DIRS = "proposals|deployments|scripts|theory|evals|docs|tests"
PATH_RE = re.compile(r"(?:(?:%s)/)[A-Za-z0-9_./+-]+" % DIRS)
EXTS = (".py", ".md", ".json", ".jsonl", ".tsv", ".txt", ".ps1", ".yml", ".yaml")


def strip_tail(p):
    while p and p[-1] in ".,;:)(`'\"-/":
        if p.endswith(EXTS):
            break
        p = p[:-1]
    return p


def cited_paths(text):
    out = []
    for m in PATH_RE.finditer(text or ""):
        p = strip_tail(m.group(0))
        if p and p.endswith(EXTS) and p not in out:
            out.append(p)
    return out


def git(*args):
    r = subprocess.run(["git"] + list(args), cwd=ROOT, capture_output=True)
    return r.stdout.decode("utf-8", "replace")


def main():
    tracked = set(git("ls-files").splitlines())
    ever = set()
    for line in git("log", "--all", "--pretty=format:", "--name-only").splitlines():
        line = line.strip()
        if line:
            ever.add(line)

    def verdict(p):
        if p in tracked:
            return "tracked_head"
        if p in ever:
            return "history_only"
        if os.path.exists(os.path.join(ROOT, p.replace("/", os.sep))):
            return "disk_only"
        return "missing"

    rows = []
    parse_errors = []
    with io.open(CHAT, encoding="utf-8") as f:
        for lineno, raw in enumerate(f, 1):
            s = raw.strip()
            if not s:
                continue
            try:
                rows.append((lineno, json.loads(s)))
            except Exception as exc:
                parse_errors.append({"line": lineno, "error": str(exc)})

    # ---- Q1: collision buckets -------------------------------------------
    buckets_all = collections.OrderedDict()
    buckets_clock = collections.OrderedDict()
    author_msgs = collections.Counter()
    author_clock_msgs = collections.Counter()
    for lineno, rec in rows:
        key = (rec.get("from"), rec.get("time"))
        buckets_all.setdefault(key, []).append((lineno, rec))
        author_msgs[rec.get("from")] += 1
        if rec.get("time_authority") == "clock":
            buckets_clock.setdefault(key, []).append((lineno, rec))
            author_clock_msgs[rec.get("from")] += 1

    dup_all = [(k, v) for k, v in buckets_all.items() if len(v) > 1]
    dup_clock = [(k, v) for k, v in buckets_clock.items() if len(v) > 1]

    dup_clock_by_author = collections.Counter(k[0] for k, _ in dup_clock)
    rows_in_dup_clock = collections.Counter()
    for k, v in dup_clock:
        rows_in_dup_clock[k[0]] += len(v)

    # ---- Q2: do later records in a bucket cite anything new? --------------
    bucket_detail = []
    load_bearing = 0
    inert = 0
    new_path_verdicts = collections.Counter()
    for (author, t), members in dup_clock:
        seen = set()
        members_out = []
        bucket_adds_new = False
        for idx, (lineno, rec) in enumerate(members):
            paths = cited_paths(rec.get("text"))
            fresh = [p for p in paths if p not in seen]
            if idx > 0 and fresh:
                bucket_adds_new = True
                for p in fresh:
                    new_path_verdicts[verdict(p)] += 1
            seen.update(paths)
            members_out.append({
                "position_in_bucket": idx,
                "chat_line": lineno,
                "cited_path_count": len(paths),
                "paths_not_cited_by_earlier_member": fresh,
                "verdicts": {p: verdict(p) for p in paths},
                "text_head": (rec.get("text") or "")[:70],
            })
        if bucket_adds_new:
            load_bearing += 1
        else:
            inert += 1
        bucket_detail.append({
            "from": author,
            "time": t,
            "member_count": len(members),
            "later_members_cite_new_paths": bucket_adds_new,
            "members": members_out,
        })

    payload = {
        "probe": "collision_bucket_citations",
        "question": "is 'multi-match = check all' load-bearing, or cosmetic?",
        "chat_rows_parsed": len(rows),
        "chat_parse_errors_skipped": parse_errors,
        "q1_identity_key": {
            "duplicate_from_time_pairs_all_records": len(dup_all),
            "rows_involved_all_records": sum(len(v) for _, v in dup_all),
            "clock_authority_rows": sum(author_clock_msgs.values()),
            "duplicate_pairs_clock_only": len(dup_clock),
            "duplicate_pairs_clock_by_author": dict(dup_clock_by_author),
            "rows_inside_clock_collisions_by_author": dict(rows_in_dup_clock),
            "clock_rows_by_author": dict(author_clock_msgs),
            "all_rows_by_author": dict(author_msgs),
        },
        "q2_load_bearing": {
            "buckets_where_later_members_cite_new_paths": load_bearing,
            "buckets_where_they_do_not": inert,
            "verdicts_of_paths_only_visible_via_later_members": dict(new_path_verdicts),
        },
        "bucket_detail": bucket_detail,
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if len(sys.argv) > 1:
        with io.open(sys.argv[1], "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text + "\n")
    else:
        print(text)


if __name__ == "__main__":
    main()
