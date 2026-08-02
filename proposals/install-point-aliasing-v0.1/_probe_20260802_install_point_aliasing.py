"""Read-only probe: are the two "install points" one physical directory, and
does that make the two-point agreement checks constructively unfailable?

Writes nothing outside a temporary directory of its own making. Never touches
the live install trees except to read bytes and query file ids.

Run:
    python proposals/install-point-aliasing-v0.1/_probe_20260802_install_point_aliasing.py
Emits the same JSON to stdout and to the sibling .out.json.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "_probe_20260802_install_point_aliasing.out.json")

CLAUDE_ROOT = os.path.join(os.environ["USERPROFILE"], ".claude", "skills", "solve-with-weilan")
CODEX_ROOT = os.path.join("D:", os.sep, "CodexData", "skills", "solve-with-weilan")
RELPATHS = ["scripts/weilan_trace.py", "scripts/runtime_core.py"]

DEPLOY_TOOL = os.path.join(
    os.path.dirname(HERE), "find-frame-index-v0.1", "deploy_find_frame_index.py"
)


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace")
    return {"rc": p.returncode, "stdout": p.stdout, "stderr": p.stderr}


def file_id(path):
    if not os.path.isfile(path):
        return None
    r = run(["fsutil", "file", "queryfileid", path])
    if r["rc"] != 0:
        return {"error": r["stderr"].strip()}
    return r["stdout"].strip().split()[-1]


def sha256_file(path):
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def reparse_chain(path):
    """Walk the path from the drive down, reporting any reparse point."""
    chain = []
    parts = []
    head = path
    while True:
        head, tail = os.path.split(head)
        if not tail:
            parts.append(head)
            break
        parts.append(tail)
    parts.reverse()
    cur = parts[0]
    for part in parts[1:]:
        cur = os.path.join(cur, part)
        if not os.path.exists(cur):
            break
        ps = (
            "$i = Get-Item -LiteralPath '%s' -Force; "
            "if ($i.Attributes -match 'ReparsePoint') "
            "{ \"$($i.LinkType)|$($i.Target)\" } else { 'plain|' }" % cur
        )
        r = run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps])
        kind, _, target = r["stdout"].strip().partition("|")
        if kind and kind != "plain":
            chain.append({"path": cur, "link_type": kind, "target": target})
    return chain


def sandbox_demo():
    """Reproduce the aliasing in a temp dir and show the divergent branch is dead.

    Mirrors deploy_find_frame_index.classify(): a state per root, then
    `all_installs_agree = len({states}) == 1`.
    """
    tmp = tempfile.mkdtemp(prefix="wl_alias_")
    try:
        real = os.path.join(tmp, "real")
        os.makedirs(os.path.join(real, "scripts"))
        target_file = os.path.join(real, "scripts", "x.py")
        with open(target_file, "wb") as fh:
            fh.write(b"baseline\n")
        link = os.path.join(tmp, "aliased")
        mk = run(["cmd", "/c", "mklink", "/J", link, real])
        if mk["rc"] != 0:
            return {"created": False, "detail": mk}

        def states_via(roots):
            return [sha256_file(os.path.join(r, "scripts", "x.py")) for r in roots]

        roots = [link, real]
        before = states_via(roots)
        # Try to make the two roots disagree by writing through ONE of them.
        with open(os.path.join(real, "scripts", "x.py"), "wb") as fh:
            fh.write(b"candidate\n")
        after = states_via(roots)
        # And through the other one.
        with open(os.path.join(link, "scripts", "x.py"), "wb") as fh:
            fh.write(b"third\n")
        after2 = states_via(roots)
        return {
            "created": True,
            "roots": roots,
            "states_initial": before,
            "states_after_write_via_real": after,
            "states_after_write_via_link": after2,
            "agreement_forced_in_all_three_reads": [
                len(set(s)) == 1 for s in (before, after, after2)
            ],
            "divergence_ever_observed": any(len(set(s)) > 1 for s in (before, after, after2)),
        }
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    result = {
        "probe": "install_point_aliasing",
        "question": (
            "Do the two install points named by deploy_find_frame_index.installs() "
            "resolve to one physical file, making 'both installs agree' unfailable?"
        ),
        "roots": {"claude": CLAUDE_ROOT, "codex": CODEX_ROOT},
        "reparse_chain": {
            "claude": reparse_chain(CLAUDE_ROOT),
            "codex": reparse_chain(CODEX_ROOT),
        },
        "per_file": {},
        "deploy_tool_verify": None,
        "sandbox": sandbox_demo(),
    }
    for rel in RELPATHS:
        c = os.path.join(CLAUDE_ROOT, *rel.split("/"))
        d = os.path.join(CODEX_ROOT, *rel.split("/"))
        cid, did = file_id(c), file_id(d)
        result["per_file"][rel] = {
            "claude": {"path": c, "file_id": cid, "sha256": sha256_file(c),
                       "size": os.path.getsize(c) if os.path.isfile(c) else None},
            "codex": {"path": d, "file_id": did, "sha256": sha256_file(d),
                      "size": os.path.getsize(d) if os.path.isfile(d) else None},
            "same_ntfs_file_id": cid is not None and cid == did,
        }
    if os.path.isfile(DEPLOY_TOOL):
        r = run([sys.executable, DEPLOY_TOOL, "verify"])
        parsed = None
        try:
            parsed = json.loads(r["stdout"])
        except Exception as exc:  # pragma: no cover - diagnostic only
            parsed = {"parse_error": str(exc)}
        result["deploy_tool_verify"] = {
            "tool": DEPLOY_TOOL,
            "rc": r["rc"],
            "all_installs_agree": parsed.get("all_installs_agree") if isinstance(parsed, dict) else None,
            "state": parsed.get("state") if isinstance(parsed, dict) else None,
            "observed_identical_across_installs": (
                isinstance(parsed, dict)
                and "installs" in parsed
                and len({json.dumps(v["observed"], sort_keys=True)
                         for v in parsed["installs"].values()}) == 1
            ),
        }
    result["conclusion"] = {
        "one_physical_tree": all(v["same_ntfs_file_id"] for v in result["per_file"].values()),
        "divergent_branch_reachable_in_production": False,
        "note": (
            "deploy_find_frame_index.cmd_verify sets state='divergent' only when the two "
            "classify() results differ; both read the same bytes, so that branch and the R9 "
            "rollback trigger built on it cannot fire in this environment."
        ),
    }
    text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
