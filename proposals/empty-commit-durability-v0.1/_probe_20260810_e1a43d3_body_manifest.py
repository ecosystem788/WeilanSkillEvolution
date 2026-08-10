"""Read-only probe: does e1a43d3's commit body actually carry the 28-filename
manifest that peer-chat:3743 item 3 claims is its only 留痕?

The commit is tree-identical to its parent (verified separately), so the body is
the sole verifiable artifact. Prints JSON to argv[1].
"""
import json
import re
import subprocess
import sys

REPO = r"D:\WeilanSkillEvolution"
COMMIT = "e1a43d3"


def git_bytes(*args):
    out = subprocess.run(["git", "-C", REPO, *args], capture_output=True)
    if out.returncode != 0:
        raise SystemExit(f"git {args} rc={out.returncode}: {out.stderr[:400]!r}")
    return out.stdout


def main() -> int:
    body = git_bytes("log", "-1", "--format=%B", COMMIT).decode("utf-8", errors="strict")
    # .patch-<something>.txt tokens named anywhere in the body
    names = re.findall(r"\.patch-[A-Za-z0-9._-]*\.txt", body)
    uniq = sorted(set(names))
    result = {
        "commit": COMMIT,
        "body_chars": len(body),
        "body_lines": len(body.splitlines()),
        "patch_name_mentions": len(names),
        "patch_name_unique": len(uniq),
        "claimed_in_peer_chat_3743": 28,
        "manifest_matches_claim": len(uniq) == 28,
        "unique_names": uniq,
        "body": body,
    }
    with open(sys.argv[1], "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
