"""Read-only probe: which scan_only_gate --commit inputs move the receipt, and
which of those are invisible in the receipt a co-signer would compare.

Answers the three empirical asks in Codex's 2026-08-02T13:10:52+09:00
[反对·退回重提] against the CHARTER 六.1 proposal:
  A. a real NEW_MATCHES (rc 2) run against a controlled fixture ruleset;
  B. same input, different workspace -> same result?
  C. is the ruleset identity a function of the pattern *set* or of the file's
     exact bytes (i.e. does pattern order alone re-key every registry anchor)?

Writes nothing into the repository working tree: the fixture ruleset files and
the second workspace both live under a temp dir. Never prints a pattern.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

GATE = os.path.join(
    r"D:\WeilanSkillEvolution", "proposals", "scaffold-opensource-export-v0.1",
    "scan_only_gate.py")
REPO = r"D:\WeilanSkillEvolution"
# Benign tokens that certainly occur in tracked paths of this repo. These are
# fixture patterns, not private strings; the probe still never prints them
# back out of the receipt.
FIXTURE_PATTERNS = ["peer-chat", "CHARTER"]

# Fields a co-signer would compare under the rejected proposal's "report six
# fields" rule, plus the ones that localise a disagreement.
COMPARE = ("state", "ruleset_digest", "pattern_count", "entries_scanned",
           "files_scanned", "occurrence_count", "unanchored_occurrence_count",
           "stale_anchor_count", "resolved_oid")


def write_ruleset(path, patterns):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(patterns) + "\n")
    return hashlib.sha256(
        "\n".join(patterns).encode("utf-8")).hexdigest()


def run_gate(commit, ruleset, cwd):
    proc = subprocess.run(
        [sys.executable, GATE, "--commit", commit, "--private-strings", ruleset],
        cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    out = proc.stdout.decode("utf-8", "replace")
    try:
        receipt = json.loads(out) if out.strip() else None
    except json.JSONDecodeError:
        receipt = None
    return {
        "rc": proc.returncode,
        "receipt": receipt,
        "stderr": proc.stderr.decode("utf-8", "replace").strip()[:400],
    }


def summary(run):
    if run["receipt"] is None:
        return {"rc": run["rc"], "receipt": None, "stderr": run["stderr"]}
    picked = {k: run["receipt"].get(k) for k in COMPARE}
    picked["rc"] = run["rc"]
    return picked


def main():
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO, stdout=subprocess.PIPE,
        check=True).stdout.decode("ascii").strip()

    tmp = tempfile.mkdtemp(prefix="gate_input_probe_")
    result = {"probe": "scan_only_gate_input_binding",
              "commit": commit, "tmp": tmp, "observations": {}}
    obs = result["observations"]
    try:
        # --- ruleset fixtures -------------------------------------------
        a = os.path.join(tmp, "ruleset_a.txt")
        b = os.path.join(tmp, "ruleset_b_reordered.txt")
        c = os.path.join(tmp, "sub", "ruleset_a_copy.txt")
        os.makedirs(os.path.dirname(c))
        digest_a = write_ruleset(a, FIXTURE_PATTERNS)
        digest_b = write_ruleset(b, list(reversed(FIXTURE_PATTERNS)))
        digest_c = write_ruleset(c, FIXTURE_PATTERNS)
        obs["fixture_digests"] = {
            "a": digest_a, "b_reordered": digest_b, "c_same_bytes_other_path": digest_c,
            "reorder_changes_digest": digest_a != digest_b,
            "path_changes_digest": digest_a != digest_c,
        }

        # --- A. real NEW_MATCHES in the home workspace -------------------
        home_a = run_gate(commit, a, REPO)
        obs["A_home_ruleset_a"] = summary(home_a)

        # --- C. same pattern SET, different file order -------------------
        home_b = run_gate(commit, b, REPO)
        obs["C_home_ruleset_b_reordered"] = summary(home_b)

        # --- B. second workspace, byte-identical ruleset ------------------
        clone = os.path.join(tmp, "workspace2")
        cp = subprocess.run(
            ["git", "clone", "--no-checkout", "file:///D:/WeilanSkillEvolution", clone],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        obs["clone_rc"] = cp.returncode
        if cp.returncode == 0:
            obs["B_workspace2_ruleset_a"] = summary(run_gate(commit, c, clone))
        else:
            obs["B_workspace2_ruleset_a"] = {
                "error": "clone_failed",
                "stderr": cp.stderr.decode("utf-8", "replace")[-400:]}

        # --- registry parameterisation -----------------------------------
        # There is no --registry flag; confirm the gate rejects one rather
        # than honouring it, i.e. the registry is not a bindable input.
        proc = subprocess.run(
            [sys.executable, GATE, "--commit", commit, "--private-strings", a,
             "--registry", os.path.join(tmp, "empty-registry.jsonl")],
            cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        obs["registry_flag"] = {
            "rc": proc.returncode,
            "stderr_tail": proc.stderr.decode("utf-8", "replace").strip()[-200:],
        }

        # --- what the receipt does NOT carry ------------------------------
        keys = sorted(home_a["receipt"].keys()) if home_a["receipt"] else []
        obs["receipt_top_level_keys"] = keys
        obs["receipt_omits"] = [
            name for name in ("private_strings_path", "registry_path",
                              "registry_digest", "registry_entry_count",
                              "repository", "gate_version")
            if name not in keys]
    finally:
        result["cleanup"] = "kept" if os.environ.get("KEEP_PROBE_TMP") else "removed"
        json.dump(result, sys.stdout, ensure_ascii=False, indent=1)
        print()
        if not os.environ.get("KEEP_PROBE_TMP"):
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
