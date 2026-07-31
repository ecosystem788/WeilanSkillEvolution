"""Read-only independent check of Codex's quiet-contract-equality claim.

Claim under review (peer-chat 2026-07-31T13:54:05+09:00): on the same one-off
ledger, the rollback base and the deployed live weilan_trace.py derive a
byte-identical quiet metabolic contract (contract_hash / branches / issues),
and each derivation leaves method-state byte-unchanged.

This probe never touches the live artifact or the real method-state: both
versions are copied into a temp tree and pointed at a temp WEILAN_METHOD_HOME.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

LIVE = Path(r"C:\Users\zy\.claude\skills\solve-with-weilan\scripts\weilan_trace.py")
BASE = Path(
    r"D:\WeilanSkillEvolution\proposals\frame-abandon-validation-gap-v0.1\evidence"
    r"\weilan_trace.py.live-"
    r"dc5eb30b05a85da3574ab5887c17f5aa1b10b3cd6d6cf0cdb48779079e8f143f.copy"
)
SCOPE = "probe-scope"


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def state_digest(root):
    """Digest every byte under the method state, path-sorted."""
    entries = []
    for path in sorted(Path(root).rglob("*")):
        if path.is_file():
            rel = path.relative_to(root).as_posix()
            entries.append((rel, hashlib.sha256(path.read_bytes()).hexdigest()))
    blob = json.dumps(entries, sort_keys=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest(), len(entries)


def run(script, args, env):
    proc = subprocess.run(
        [sys.executable, str(script)] + args,
        capture_output=True,
        env=env,
    )
    out = proc.stdout.decode("utf-8", errors="replace")
    err = proc.stderr.decode("utf-8", errors="replace")
    return proc.returncode, out, err


def main():
    tmp = Path(tempfile.mkdtemp(prefix="wl-quiet-"))
    result = {"tmp": str(tmp)}
    try:
        # weilan_trace imports sibling modules (runtime_core, ...), so each
        # version needs a full copy of the scripts tree around it.
        base_script = tmp / "base" / "weilan_trace.py"
        live_script = tmp / "live" / "weilan_trace.py"
        shutil.copytree(LIVE.parent, tmp / "base")
        shutil.copytree(LIVE.parent, tmp / "live")
        shutil.copyfile(BASE, base_script)
        shutil.copyfile(LIVE, live_script)
        result["base_sha256"] = sha256_file(base_script)
        result["live_sha256"] = sha256_file(live_script)

        method_home = tmp / "method-state"
        method_home.mkdir()
        workspace = tmp / "ws"
        workspace.mkdir()

        env = dict(os.environ)
        env["WEILAN_METHOD_HOME"] = str(method_home)
        env.pop("PYTHONWARNINGS", None)

        # Build a small real lineage with the BASE version: root then continue.
        rc, out, err = run(
            base_script,
            ["open", "--level", "L2", "--workspace", str(workspace), "--scope", SCOPE,
             "--branch", "main", "--relation", "root",
             "--problem", "quiet contract equality probe",
             "--success", "two versions derive the same contract"],
            env,
        )
        result["seed_open_rc"] = rc
        if rc != 0:
            result["seed_open_err"] = err[-2000:]
            return result
        frame_id = json.loads(out)["frame_id"]
        result["seed_frame_id"] = frame_id

        # Quiet state: nothing else written. Snapshot bytes.
        before_digest, before_count = state_digest(method_home)
        result["state_before"] = {"digest": before_digest, "files": before_count}

        contracts = {}
        per_version_state = {}
        for name, script in (("base", base_script), ("live", live_script)):
            rc, out, err = run(
                script,
                ["metabolic-contract", "--workspace", str(workspace), "--scope", SCOPE],
                env,
            )
            if rc != 0:
                result[f"{name}_contract_rc"] = rc
                result[f"{name}_contract_err"] = err[-2000:]
                return result
            contracts[name] = json.loads(out)
            digest, count = state_digest(method_home)
            per_version_state[name] = {"digest": digest, "files": count}

        result["state_after_each"] = per_version_state
        result["method_state_unchanged_by_base"] = (
            per_version_state["base"]["digest"] == before_digest
        )
        result["method_state_unchanged_by_live"] = (
            per_version_state["live"]["digest"] == before_digest
        )

        base_c, live_c = contracts["base"], contracts["live"]
        result["contract_hash_base"] = base_c.get("contract_hash")
        result["contract_hash_live"] = live_c.get("contract_hash")
        result["contract_hash_equal"] = base_c.get("contract_hash") == live_c.get("contract_hash")
        result["branches_equal"] = base_c.get("branches") == live_c.get("branches")
        result["issues_equal"] = base_c.get("issues") == live_c.get("issues")
        result["issues"] = base_c.get("issues")

        canon_base = json.dumps(base_c, ensure_ascii=False, sort_keys=True)
        canon_live = json.dumps(live_c, ensure_ascii=False, sort_keys=True)
        result["whole_object_bytewise_equal"] = canon_base == canon_live
        if canon_base != canon_live:
            differing = sorted(
                key for key in set(base_c) | set(live_c)
                if base_c.get(key) != live_c.get(key)
            )
            result["differing_keys"] = differing
        return result
    finally:
        result["cleanup"] = "kept" if os.environ.get("WL_KEEP_TMP") else "removed"
        if not os.environ.get("WL_KEEP_TMP"):
            shutil.rmtree(tmp, ignore_errors=True)
        Path(
            r"D:\WeilanSkillEvolution\proposals\frame-abandon-validation-gap-v0.1"
            r"\_probe_20260731_claude_quiet_contract_equality.out.json"
        ).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    print(json.dumps(main(), ensure_ascii=False, indent=2))
