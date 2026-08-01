"""Read-only: does the landed V3 .gitattributes survive a real clone, and does its rule still evaluate there?

Writes only under C:/wl_v3c (scratch clone target). Never touches this repo, the two
install trees, or any ledger. Output written with newline="\n" so its own digest is
stable across a clone (the 75/85 CRLF lesson from CLAUDE_REVIEW3_20260801.md).

Three questions, each measured rather than inferred:
  Q1 blob domain    -- is the committed blob byte-identical to the cosigned 12-byte address?
  Q2 checkout domain-- what does a clean clone on this host put on disk for that file?
  Q3 effect         -- in that clone, does git still evaluate `-text` for the .bak path?
Q3 is the one that matters: if the checked-out .gitattributes is CRLF and git's attribute
parser chokes on it, V3 buys nothing for the third party it was written for.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys

REPO = r"D:\WeilanSkillEvolution"
CLONE = r"C:\wl_v3c"
TARGET = "proposals/canonical-workspace-cache-v0.1/.gitattributes"
BAK = ("proposals/canonical-workspace-cache-v0.1/baseline/solve-with-weilan/scripts/"
       "weilan_trace.py.pre-concurrent-clock-v01.9adab069.bak")
PY = "proposals/canonical-workspace-cache-v0.1/candidate/solve-with-weilan/scripts/runtime_core.py"
COSIGNED_SHA = "b3b1fb0f9049ff042f75c37f223baa403596480c67f29d549619cd54bd58f450"


def run(args, cwd=None, binary=False):
    p = subprocess.run(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return {
        "rc": p.returncode,
        "out": p.stdout if binary else p.stdout.decode("utf-8", "replace"),
        "err": p.stderr.decode("utf-8", "replace"),
    }


def describe(raw):
    return {
        "len": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "hex": raw.hex(),
        "contains_crlf": b"\r\n" in raw,
    }


def check_attr(cwd, path):
    r = run(["git", "check-attr", "-a", "--", path], cwd=cwd)
    attrs = {}
    for line in r["out"].splitlines():
        # "<path>: <attr>: <value>" -- path may contain ": " so split from the right
        head, _, value = line.rpartition(": ")
        _, _, attr = head.rpartition(": ")
        if attr:
            attrs[attr] = value
    return {"rc": r["rc"], "attrs": attrs, "raw": r["out"].strip()}


out = {"probe": os.path.basename(__file__), "repo": REPO, "clone": CLONE}

head = run(["git", "rev-parse", "HEAD"], cwd=REPO)["out"].strip()
out["source_head"] = head

# --- source worktree (what the cosign measured) ---
with open(os.path.join(REPO, TARGET.replace("/", os.sep)), "rb") as fh:
    out["q0_source_worktree"] = describe(fh.read())
out["q0_matches_cosigned"] = out["q0_source_worktree"]["sha256"] == COSIGNED_SHA

# --- Q1: blob domain ---
blob = run(["git", "cat-file", "blob", "HEAD:" + TARGET], cwd=REPO, binary=True)
out["q1_blob"] = describe(blob["out"]) if blob["rc"] == 0 else {"error": blob["err"]}
out["q1_blob_matches_cosigned"] = out["q1_blob"].get("sha256") == COSIGNED_SHA

# --- Q2: clean clone on this host ---
if os.path.isdir(CLONE):
    shutil.rmtree(CLONE, ignore_errors=True)
clone = run(["git", "-c", "core.longpaths=true", "clone", "--quiet",
             "file:///" + REPO.replace("\\", "/"), CLONE])
out["q2_clone_rc"] = clone["rc"]
out["q2_clone_err"] = clone["err"].strip()[:600]
if clone["rc"] != 0:
    out["verdict"] = "INVALID: clone failed"
    with open(__file__.replace(".py", ".out.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    sys.exit(1)

# a clone whose checkout silently half-failed would fake every answer below (longpath lesson)
status = run(["git", "status", "--porcelain"], cwd=CLONE)
out["q2_clone_status_empty"] = status["out"].strip() == ""
out["q2_clone_status_head"] = status["out"][:400]
out["q2_clone_index_count"] = len(run(["git", "ls-files"], cwd=CLONE)["out"].splitlines())

with open(os.path.join(CLONE, TARGET.replace("/", os.sep)), "rb") as fh:
    out["q2_clone_worktree"] = describe(fh.read())
out["q2_clone_matches_cosigned"] = out["q2_clone_worktree"]["sha256"] == COSIGNED_SHA

# --- Q3: does the rule still evaluate in that clone? ---
out["q3_clone_bak"] = check_attr(CLONE, BAK)
out["q3_clone_py"] = check_attr(CLONE, PY)
out["q3_clone_target_itself"] = check_attr(CLONE, TARGET)
out["q3_source_bak"] = check_attr(REPO, BAK)

out["q3_rule_effective_in_clone"] = out["q3_clone_bak"]["attrs"].get("text") == "unset"
out["q3_py_still_lf_in_clone"] = out["q3_clone_py"]["attrs"].get("eol") == "lf"

out["verdict"] = {
    "blob_reproduces_cosigned_address": out["q1_blob_matches_cosigned"],
    "clone_worktree_reproduces_cosigned_address": out["q2_clone_matches_cosigned"],
    "rule_effective_in_clean_clone": out["q3_rule_effective_in_clone"],
    "sibling_py_unaffected": out["q3_py_still_lf_in_clone"],
}

with open(__file__.replace(".py", ".out.json"), "w", encoding="utf-8", newline="\n") as fh:
    json.dump(out, fh, indent=2, ensure_ascii=False)
print(json.dumps(out["verdict"], ensure_ascii=False, indent=2))
print("q0_source", out["q0_source_worktree"]["len"], out["q0_source_worktree"]["sha256"][:16])
print("q1_blob  ", out["q1_blob"].get("len"), str(out["q1_blob"].get("sha256"))[:16])
print("q2_clone ", out["q2_clone_worktree"]["len"], out["q2_clone_worktree"]["sha256"][:16],
      "crlf=", out["q2_clone_worktree"]["contains_crlf"])
print("q2_status_empty", out["q2_clone_status_empty"], "index", out["q2_clone_index_count"])
print("q3_bak_in_clone ", out["q3_clone_bak"]["raw"])
print("q3_bak_in_source", out["q3_source_bak"]["raw"])
