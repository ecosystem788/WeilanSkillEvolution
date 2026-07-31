"""Independent review probe for frame_abandoned v2 (Claude, 2026-07-31).

Read-only w.r.t. the real ledger: everything runs under a throwaway state_root.
Attacks the three points Codex named plus the deadlock-unlock claim.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

TRACE = r"C:\Users\zy\.claude\skills\solve-with-weilan\scripts\weilan_trace.py"
WS = r"D:\ReviewProbeWS"
SCOPE = "probe-scope"

root = Path(tempfile.mkdtemp(prefix="abandon-review-"))
env = dict(os.environ)
env["WEILAN_METHOD_HOME"] = str(root)
env.pop("CODEX_HOME", None)
env.pop("PYTHONIOENCODING", None)

results = []


def run(*args, expect=None):
    proc = subprocess.run(
        [sys.executable, TRACE, *args],
        capture_output=True, env=env, cwd=str(root),
    )
    out = proc.stdout.decode("utf-8", "replace").strip()
    err = proc.stderr.decode("utf-8", "replace").strip()
    return proc.returncode, out, err


def check(name, ok, detail=""):
    results.append((name, "PASS" if ok else "FAIL", detail))
    print(("PASS " if ok else "FAIL ") + name + ("  | " + detail if detail else ""))


def open_frame(problem, parent=None, relation=None):
    args = ["open", "--workspace", WS, "--scope", SCOPE, "--level", "L2",
            "--problem", problem, "--success", "sc", "--budget", "1"]
    if parent:
        args += ["--parent", parent, "--relation", relation or "continue"]
    else:
        args += ["--relation", "root"]
    rc, out, err = run(*args)
    if rc != 0:
        return None, err
    return json.loads(out)["frame_id"], ""


def backdate(frame_id, seconds):
    """Rewrite the last event's timestamp to N seconds ago (test fixture only)."""
    import datetime
    p = None
    for cand in root.rglob("*.jsonl"):
        if frame_id in cand.name:
            p = cand
            break
    if p is None:
        for cand in root.rglob("*.jsonl"):
            txt = cand.read_text(encoding="utf-8")
            if frame_id in txt and "frame_opened" in txt:
                p = cand
                break
    lines = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
    ts = (datetime.datetime.now(datetime.timezone.utc)
          - datetime.timedelta(seconds=seconds)).isoformat()
    for ev in lines:
        if ev.get("frame_id") == frame_id:
            ev["timestamp_utc"] = ts
    p.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in lines) + "\n",
                 encoding="utf-8")
    return p


print("state_root =", root)

# --- setup: root frame + a second frame that becomes the head ---
f1, e = open_frame("probe root frame")
check("setup: root frame opened", f1 is not None, e)
rc, out, err = run("persistence-audit", "--frame-id", f1, "--trigger",
                   "round_end", "--decision", "not_persisted",
                   "--reason", "probe setup")
check("setup: root frame audited", rc == 0, err[:200])
rc, out, err = run("close", "--frame-id", f1, "--outcome", "success",
                   "--verdict", "probe close")
check("setup: root frame closed", rc == 0, err[:200])

f2, e = open_frame("probe stuck head", parent=f1, relation="continue")
check("setup: head frame opened", f2 is not None, e)

# --- BASELINE: the deadlock actually exists ---
f3, e = open_frame("would-be next", parent=f2, relation="continue")
check("A. deadlock reproduces: open on unclosed head is refused",
      f3 is None and "terminal" in e.lower(), e[:160])

# --- ATTACK 1: abandon before the silence threshold must fail ---
rc, out, err = run("frame-abandon", "--frame-id", f2, "--evidence", "{}",
                   "--reason", "too soon")
check("B. fresh frame cannot be abandoned (silence gate)", rc != 0, err[:160])

# --- ATTACK 2: threshold below hard floor must fail ---
path2 = backdate(f2, 100000)
rc, out, err = run("frame-abandon", "--frame-id", f2,
                   "--silence-threshold-seconds", "60",
                   "--evidence", "{}", "--reason", "lower the bar")
check("C. sub-3600s threshold rejected (hard floor)", rc != 0, err[:160])

# --- ATTACK 3: abandon a NON-head frame (f1, already closed) ---
rc, out, err = run("frame-abandon", "--frame-id", f1, "--evidence", "{}",
                   "--reason", "not the head")
check("D. non-head/closed frame cannot be abandoned", rc != 0, err[:160])

# --- ATTACK 4: reason/evidence hygiene ---
rc, out, err = run("frame-abandon", "--frame-id", f2, "--evidence", "not-json",
                   "--reason", "bad evidence")
check("E. non-JSON --evidence rejected", rc != 0, err[:120])
rc, out, err = run("frame-abandon", "--frame-id", f2, "--evidence", "[1,2]",
                   "--reason", "array evidence")
check("F. non-object --evidence rejected", rc != 0, err[:120])
rc, out, err = run("frame-abandon", "--frame-id", f2, "--evidence", "{}",
                   "--reason", "   ")
check("G. blank --reason rejected", rc != 0, err[:120])

# --- ATTACK 5: forge frame_abandoned through the generic event door ---
rc, out, err = run("event", "--frame-id", f2, "--type", "frame_abandoned",
                   "--field", "reason=forged")
check("H. generic `event` door refuses frame_abandoned", rc != 0, err[:160])

# --- audit ledger state BEFORE abandonment ---
def audit_rows():
    rows = []
    for p in root.rglob("*.jsonl"):
        if "persistence" in str(p):
            for line in p.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    rows.append(json.loads(line))
    return rows

before = audit_rows()

# --- THE REAL RUN ---
rc, out, err = run("frame-abandon", "--frame-id", f2, "--evidence",
                   '{"probe":"claude-review-20260731"}',
                   "--reason", "peer never returned; independent review probe")
check("I. legitimate abandonment succeeds", rc == 0, (err or out)[:200])
abandon_out = json.loads(out) if rc == 0 else {}
print("   ->", json.dumps(abandon_out, ensure_ascii=False))

after = audit_rows()
auto = [r for r in after if r not in before]
check("J. auto NOT_PERSISTED written for missing triggers",
      all(r.get("decision") == "NOT_PERSISTED" for r in auto),
      f"{len(auto)} rows: {[r.get('trigger') for r in auto]}")

# --- ATTACK 6: idempotence / half-retry --- rerun must not double-write ---
rc2, out2, err2 = run("frame-abandon", "--frame-id", f2, "--evidence", "{}",
                      "--reason", "second attempt")
after2 = audit_rows()
check("K. re-abandon refused", rc2 != 0, err2[:140])
check("L. refused re-abandon wrote no extra audit rows",
      len(after2) == len(after), f"{len(after)} -> {len(after2)}")

# --- ATTACK 7: post-terminal writes must all be refused ---
rc, out, err = run("close", "--frame-id", f2, "--outcome", "success",
                   "--verdict", "sneak a verdict in")
check("M. cannot close an abandoned frame", rc != 0, err[:140])
rc, out, err = run("event", "--frame-id", f2, "--type", "evidence_recorded",
                   "--field", "claim=x", "--field", "source=y")
check("N. cannot append events to an abandoned frame", rc != 0, err[:140])
rc, out, err = run("persistence-audit", "--frame-id", f2, "--trigger",
                   "round_end", "--decision", "not_persisted",
                   "--reason", "late audit")
check("O. cannot audit an abandoned frame", rc != 0, err[:140])

# --- THE POINT: deadlock is actually unlocked ---
f4, e = open_frame("continuation after abandonment", parent=f2, relation="continue")
check("P. deadlock UNLOCKED: can continue from an abandoned head",
      f4 is not None, e[:200])

# --- terminal != closed, on the read side ---
rc, out, err = run("self-project", "--workspace", WS, "--scope", SCOPE)
proj = json.loads(out) if rc == 0 else {}
bh = proj.get("branch_heads", {}) if isinstance(proj, dict) else {}
print("   branch_heads =", json.dumps(bh, ensure_ascii=False)[:600])

rc, out, err = run("show", "--frame-id", f2)
evs = json.loads(out)
term = evs[-1]
check("Q. terminal event is frame_abandoned, not frame_closed",
      term["event_type"] == "frame_abandoned", term["event_type"])
check("R. frame_abandoned carries no outcome and no verdict",
      "outcome" not in term.get("data", {}) and "verdict" not in term.get("data", {}),
      json.dumps(term.get("data", {}), ensure_ascii=False)[:200])

rc, out, err = run("episode-index", "--workspace", WS, "--scope", SCOPE)
rc, out, err = run("episode-search", "--workspace", WS, "--scope", SCOPE,
                   "--query", "probe stuck head")
try:
    hits = json.loads(out)
except Exception:
    hits = out
print("   episode-search ->", json.dumps(hits, ensure_ascii=False)[:700])

print("\n=== SUMMARY ===")
fails = [r for r in results if r[1] == "FAIL"]
for n, s, d in results:
    print(f"{s}  {n}")
print(f"\n{len(results) - len(fails)}/{len(results)} passed")
print("state_root kept for inspection:", root)
