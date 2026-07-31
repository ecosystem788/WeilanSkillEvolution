"""Adversarial follow-up probe: the case frame-abandon was built for but cannot handle.

Scenario: an instance collapsed a candidate and died before emitting the trace.
That is the *most likely* shape of a real deadlocked frame. Two claims under test:

  F1  frame-abandon refuses such a frame -> the deadlock is NOT cured for it.
  F2  the refusal happens AFTER append_abandonment_audits has already written
      a machine-authored NOT_PERSISTED row, which (a) permanently asserts
      something false about a still-live frame and (b) pre-satisfies the
      close-time persistence-audit gate.
"""
import datetime
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

TRACE = r"C:\Users\zy\.claude\skills\solve-with-weilan\scripts\weilan_trace.py"
WS = r"D:\ReviewProbeWS2"
SCOPE = "probe-scope-2"

root = Path(tempfile.mkdtemp(prefix="abandon-review2-"))
env = dict(os.environ)
env["WEILAN_METHOD_HOME"] = str(root)
env.pop("CODEX_HOME", None)


def run(*args):
    p = subprocess.run([sys.executable, TRACE, *args], capture_output=True,
                       env=env, cwd=str(root))
    return (p.returncode,
            p.stdout.decode("utf-8", "replace").strip(),
            p.stderr.decode("utf-8", "replace").strip())


def audit_rows():
    rows = []
    for p in root.rglob("*.jsonl"):
        if "persistence" in str(p):
            for line in p.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    rows.append(json.loads(line))
    return rows


def backdate(frame_id, seconds):
    for cand in root.rglob("*.jsonl"):
        txt = cand.read_text(encoding="utf-8")
        if frame_id in txt and "frame_opened" in txt:
            lines = [json.loads(x) for x in txt.splitlines() if x.strip()]
            ts = (datetime.datetime.now(datetime.timezone.utc)
                  - datetime.timedelta(seconds=seconds)).isoformat()
            for ev in lines:
                if ev.get("frame_id") == frame_id:
                    ev["timestamp_utc"] = ts
            cand.write_text(
                "\n".join(json.dumps(x, ensure_ascii=False) for x in lines) + "\n",
                encoding="utf-8")
            return cand
    raise RuntimeError("frame file not found")


print("state_root =", root)

# root frame -> head frame
rc, out, err = run("open", "--workspace", WS, "--scope", SCOPE, "--level", "L2",
                   "--problem", "root", "--success", "sc", "--budget", "1",
                   "--relation", "root")
f1 = json.loads(out)["frame_id"]
run("persistence-audit", "--frame-id", f1, "--trigger", "round_end",
    "--decision", "not_persisted", "--reason", "setup")
run("close", "--frame-id", f1, "--outcome", "success", "--verdict", "setup")

rc, out, err = run("open", "--workspace", WS, "--scope", SCOPE, "--level", "L2",
                   "--problem", "died right after collapsing a candidate",
                   "--success", "sc", "--budget", "1",
                   "--parent", f1, "--relation", "continue")
f2 = json.loads(out)["frame_id"]
print("head frame =", f2)

# the realistic deadlock shape: collapse recorded, instance dies before the trace
rc, out, err = run("event", "--frame-id", f2, "--type", "minimal_unit_collapsed",
                   "--field", "former_holder=candidate-A",
                   "--field", "invalidating_evidence=probe evidence",
                   "--field", "scope=" + SCOPE)
print("collapse appended:", rc == 0, err[:200])
assert rc == 0, err

backdate(f2, 100000)          # simulate ~28h of silence
before = audit_rows()

rc, out, err = run("frame-abandon", "--frame-id", f2, "--evidence",
                   '{"probe":"claude-review-f1f2"}',
                   "--reason", "holder never returned after the collapse")
after = audit_rows()
new_rows = [r for r in after if r not in before]

print("\n--- F1: can this frame be abandoned? ---")
print("exit code =", rc)
print("stderr    =", err[:300])
f1_hit = rc != 0
print("F1 CONFIRMED (deadlock NOT cured)" if f1_hit else "F1 refuted (abandon succeeded)")

print("\n--- F2: what did the failed attempt leave behind? ---")
print(f"new persistence-audit rows written by the FAILED command: {len(new_rows)}")
for r in new_rows:
    print("   ", json.dumps({k: r[k] for k in
                             ("frame_id", "trigger", "decision", "reason", "authority")},
                            ensure_ascii=False))
f2a_hit = len(new_rows) > 0

# is the frame still live and writable?
rc2, out2, err2 = run("event", "--frame-id", f2, "--type", "trace_emitted",
                      "--field", "forbidden_assumption=candidate-A is sound",
                      "--field", "invalidating_evidence=probe evidence",
                      "--field", "once_reasonable=it typechecked",
                      "--field", "reentry_condition=new evidence appears",
                      "--field", "reusable_results=the harness")
print("\nframe still writable after failed abandon:", rc2 == 0, err2[:160])

# and can it now be closed WITHOUT anyone performing a real persistence audit?
rc3, out3, err3 = run("close", "--frame-id", f2, "--outcome", "success",
                      "--verdict", "closed with a real verdict")
print("close succeeded with NO human/agent persistence-audit:", rc3 == 0,
      (out3 or err3)[:200])
f2b_hit = rc3 == 0 and len(new_rows) > 0

print("\n=== VERDICT ===")
print("F1 deadlock uncured for mid-collapse frames :", "CONFIRMED" if f1_hit else "no")
print("F2a failed command wrote audit rows anyway  :", "CONFIRMED" if f2a_hit else "no")
print("F2b close-time audit gate pre-satisfied     :", "CONFIRMED" if f2b_hit else "no")
print("state_root:", root)
