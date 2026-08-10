"""Read-only census: do commit-message `peer-chat:N` citations resolve?

Two axes, deliberately separated (see FINDING.md §三):
  AXIS A  per-commit-tree : at commit C, does C's own tree hold line N?
                            -> immutable history; a catch-up commit CANNOT fix this.
  AXIS B  from-HEAD       : cloning at HEAD, is line N readable?
                            -> this is the load-bearing one, and it IS fixable.

EXTRACTOR VERSION MATTERS (lesson from peer-chat:3719 -- a mismatch rate is a property
of the extractor, not of the ledger). Patterns and blind spots are declared below and
printed in the output, so any quoted number carries its own caveats.

Patterns caught:
  P1  peer-chat:N   plus a run of N+M / N/M/K immediately following
  P2  peer-chat <=24 chars> N-M   (range form), only when 0 < M-N < 200
Declared blind spots / noise:
  - bare numbers with no nearby "peer-chat" token           (miss)
  - citations in commit trailers or git notes               (miss)
  - citations to other ledgers (codex-inbox, ...)           (out of scope)
  - year-like tokens such as "2026" can be picked up by P1  (false positive)
  - `--all` includes this machine's stash refs, so the commit denominator is
    machine-local; stash index commits are listed separately.

No writes anywhere. Only git plumbing: log / rev-parse / cat-file.
"""
import re
import subprocess
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

REPO = r"D:\WeilanSkillEvolution"
LEDGER = "proposals/bounded-scheduler-v0.1/impl/peer-chat.jsonl"


def git(*args):
    """Run git, return raw bytes. Never text=True -- GBK decode hazard on this box."""
    p = subprocess.run(["git", "-C", REPO] + list(args),
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return p.returncode, p.stdout, p.stderr


P1 = re.compile(r"peer-chat[:：]\s*(\d{3,5})((?:\s*[+/,、]\s*\d{3,5})*)")
P1_MORE = re.compile(r"\d{3,5}")
P2 = re.compile(r"peer-chat[^\n]{0,24}?(\d{3,5})\s*[-–]\s*(\d{3,5})")


def cites(msg):
    out = set()
    for m in P1.finditer(msg):
        out.add(int(m.group(1)))
        for extra in P1_MORE.findall(m.group(2) or ""):
            out.add(int(extra))
    for m in P2.finditer(msg):
        a, b = int(m.group(1)), int(m.group(2))
        if 0 < b - a < 200:
            out.update(range(a, b + 1))
        else:
            out.update((a, b))
    return sorted(out)


_cache = {}


def ledger_height(rev):
    """Line count of LEDGER as of `rev`; None if the path is absent there."""
    rc, oid_raw, _ = git("rev-parse", f"{rev}:{LEDGER}")
    if rc != 0:
        return None
    oid = oid_raw.decode("ascii").strip()
    if oid not in _cache:
        rc, blob, _ = git("cat-file", "blob", oid)
        if rc != 0:
            return None
        _cache[oid] = len(blob.decode("utf-8", errors="replace").splitlines())
    return _cache[oid]


def stash_shas():
    """Synthetic stash commits only.

    A stash commit's parents are [base, index, (untracked)].  `base` is a REAL
    commit on a real branch -- excluding it would silently drop genuine history
    from the census (this bit the first draft of this probe: it excluded 5bde85c).
    So: take the stash commit itself and parents[1:], never parents[0].
    """
    rc, out, _ = git("stash", "list", "--format=%H")
    if rc != 0:
        return set()
    shas = set()
    for line in out.decode("utf-8", "replace").split():
        stash = line.strip()
        shas.add(stash)
        rc2, parents, _ = git("rev-list", "--parents", "-n", "1", stash)
        if rc2 == 0:
            # fields: <stash> <base> <index> [<untracked>] -- skip stash and base
            shas.update(parents.decode().split()[2:])
    return shas


SEP, REC = "\x1e", "\x1d"
rc, out, err = git("log", "--all", f"--format=%H{SEP}%ad{SEP}%B{REC}",
                   "--date=format:%Y-%m-%d %H:%M")
assert rc == 0, err.decode("utf-8", "replace")

commits = []
for chunk in out.decode("utf-8", errors="replace").split(REC):
    if not chunk.strip():
        continue
    sha, date, msg = chunk.strip("\n").split(SEP, 2)
    commits.append((sha.strip(), date, msg))

stashes = stash_shas()
head_h = ledger_height("HEAD")

rows = []
for sha, date, msg in commits:
    c = cites(msg)
    if not c:
        continue
    own = ledger_height(sha)
    bad_a = c if own is None else [n for n in c if n > own]
    bad_b = [n for n in c if head_h is None or n > head_h]
    rows.append((sha, date, msg.splitlines()[0][:70], c, own, bad_a, bad_b, sha in stashes))

real = [r for r in rows if not r[7]]


def report(rows, label):
    ptr = sum(len(r[3]) for r in rows)
    da = sum(len(r[5]) for r in rows)
    db = sum(len(r[6]) for r in rows)
    ca = sum(1 for r in rows if r[5])
    cb = sum(1 for r in rows if r[6])
    print(f"[{label}] citing commits={len(rows)}  pointers={ptr}")
    print(f"    AXIS A per-commit-tree : dangling {da}/{ptr}"
          + (f" ({da/ptr:.1%})" if ptr else "") + f"  across {ca} commits")
    print(f"    AXIS B from-HEAD       : dangling {db}/{ptr}"
          + (f" ({db/ptr:.1%})" if ptr else "") + f"  across {cb} commits")


print("=" * 78)
print("CENSUS: peer-chat:N citations in commit messages -- two reachability axes")
print("=" * 78)
print(f"commits walked (--all, machine-local incl. stash) : {len(commits)}")
print(f"HEAD ledger height                                : {head_h}")
try:
    disk = len(open(REPO + "\\" + LEDGER.replace("/", "\\"),
                    encoding="utf-8").read().splitlines())
    print(f"working-tree ledger height                        : {disk}"
          + ("   <-- AHEAD OF HEAD" if head_h is not None and disk > head_h else ""))
except OSError as e:
    print("working-tree ledger unreadable:", e)
print()
report(rows, "all refs")
report(real, "excl. stash")
print()

max_cited = max((n for r in rows for n in r[3]), default=None)
print(f"highest cited pointer = {max_cited}")
verdict = (head_h is not None and max_cited is not None and max_cited <= head_h)
print(f"AXIS B ASSERTION  all cited pointers <= HEAD height : "
      f"{'PASS' if verdict else 'FAIL'}")
print()

print("--- commits with AXIS A dangling pointers (newest first) ---")
for sha, date, subj, c, own, bad_a, bad_b, is_stash in rows:
    if not bad_a:
        continue
    tag = " [stash-index]" if is_stash else ""
    hh = "PATH-ABSENT" if own is None else f"own-height={own}"
    print(f"{sha[:8]} {date}  {hh}{tag}")
    print(f"   subj : {subj}")
    print(f"   cited: {c}")
    print(f"   A-dangling: {bad_a}")
    print(f"   B-dangling: {bad_b if bad_b else '(none -- readable from HEAD)'}")
