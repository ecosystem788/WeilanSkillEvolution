"""Read-only probe: do the file paths cited in peer-chat survive a clone?

For every repo-relative path mentioned in peer-chat.jsonl, classify:
  tracked_head   - in `git ls-files` at HEAD  -> a clone gets the file
  history_only   - never in HEAD but added at some point in --all history
  disk_only      - exists on disk, never in any commit  -> clone gets a dangling citation
  missing        - not on disk and not in history       -> dead citation everywhere

Writes JSON to stdout. Touches nothing.
"""
import io, json, os, re, subprocess, sys, collections

ROOT = r"D:\WeilanSkillEvolution"
CHAT = os.path.join(ROOT, "proposals", "bounded-scheduler-v0.1", "impl", "peer-chat.jsonl")

# ASCII-only path charset on purpose: \w matches CJK in Python str regexes,
# which would swallow the surrounding Chinese prose into the "path".
DIRS = "proposals|deployments|scripts|theory|evals|docs|tests"
PATH_RE = re.compile(r"(?:(?:%s)/)[A-Za-z0-9_./+-]+" % DIRS)
EXTS = (".py", ".md", ".json", ".jsonl", ".tsv", ".txt", ".ps1", ".yml", ".yaml")


def strip_tail(p):
    # citations sit inside prose/backticks; trim trailing punctuation that is
    # certainly not part of a filename, but keep a real extension intact.
    while p and p[-1] in ".,;:)(`'\"-/":
        if p.endswith(EXTS):
            break
        p = p[:-1]
    return p


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

    rows = []
    parse_errors = 0
    with io.open(CHAT, encoding="utf-8") as f:
        for lineno, raw in enumerate(f, 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                rec = json.loads(raw)
            except Exception:
                parse_errors += 1
                continue
            rows.append((lineno, rec))

    # path -> list of (chat_line, author, time)
    cites = collections.OrderedDict()
    for lineno, rec in rows:
        text = rec.get("text") or ""
        for m in PATH_RE.finditer(text):
            p = strip_tail(m.group(0))
            if not p or not p.endswith(EXTS):
                continue  # directory-only mentions are not file citations
            cites.setdefault(p, []).append(
                {"chat_line": lineno, "from": rec.get("from"), "time": rec.get("time")}
            )

    verdict = collections.Counter()
    detail = []
    for p, where in cites.items():
        on_disk = os.path.exists(os.path.join(ROOT, p.replace("/", os.sep)))
        if p in tracked:
            v = "tracked_head"
        elif p in ever:
            v = "history_only"
        elif on_disk:
            v = "disk_only"
        else:
            v = "missing"
        verdict[v] += 1
        detail.append({
            "path": p, "verdict": v, "on_disk": on_disk,
            "cite_count": len(where),
            "first_cite": where[0], "last_cite": where[-1],
        })

    # which proposal dirs are wholly unreachable from a clone
    dir_stat = collections.defaultdict(lambda: collections.Counter())
    for d in detail:
        parts = d["path"].split("/")
        key = "/".join(parts[:2]) if len(parts) > 1 else parts[0]
        dir_stat[key][d["verdict"]] += 1

    fully_lost = sorted(
        k for k, c in dir_stat.items()
        if c["tracked_head"] == 0 and (c["disk_only"] + c["missing"]) > 0
    )

    payload = json.dumps({
        "probe": "citation_reachability",
        "chat_rows": len(rows),
        "chat_parse_errors_skipped": parse_errors,
        "distinct_cited_paths": len(cites),
        "verdict_counts": dict(verdict),
        "fully_unreachable_dirs": fully_lost,
        "dir_breakdown": {k: dict(v) for k, v in sorted(dir_stat.items())},
        "detail": sorted(detail, key=lambda d: (d["verdict"], d["path"])),
    }, ensure_ascii=False, indent=2)
    # write the artifact ourselves: a PowerShell redirect would prepend a BOM
    # and the archived .out.json must stay byte-clean for re-runs.
    if len(sys.argv) > 1:
        with io.open(sys.argv[1], "w", encoding="utf-8", newline="\n") as fh:
            fh.write(payload + "\n")
    else:
        print(payload)


if __name__ == "__main__":
    main()
