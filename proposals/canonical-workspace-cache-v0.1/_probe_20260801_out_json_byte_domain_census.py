"""Read-only census, bounded to tracked *.out.json paths: how many archived probe
outputs have on-disk bytes that differ from their HEAD blob bytes purely by CRLF?

Motivation: a digest recorded from an on-disk .out.json is clone-unstable whenever the
worktree copy is CRLF and the blob is LF. This counts how wide that condition is, so a
remedy can be scoped as "re-record N digests" vs "adopt a writing convention".

Classification per tracked *.out.json:
  lf_on_disk            - worktree bytes already LF; digest recorded from disk is stable
  crlf_only_difference  - worktree_lf == blob, worktree != blob (clone-unstable digest)
  content_differs       - differs beyond eol (uncommitted content)
  missing_from_worktree - tracked but absent on disk

Mutates nothing. Compares against HEAD blobs only; does not clone.
"""

import hashlib
import json
import os
import subprocess
import sys

REPO = r"D:\WeilanSkillEvolution"
OUT = os.path.splitext(os.path.abspath(__file__))[0] + ".out.json"


def run(args, binary=False):
    p = subprocess.run(args, cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out = p.stdout if binary else p.stdout.decode("utf-8", "replace")
    return out, p.returncode


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    head, rc = run(["git", "rev-parse", "HEAD"])
    if rc != 0:
        raise SystemExit("git rev-parse HEAD failed")
    head = head.strip()

    listing, rc = run(["git", "ls-tree", "-r", "--name-only", head])
    if rc != 0:
        raise SystemExit("git ls-tree failed")
    refs = sorted(p for p in listing.splitlines() if p.endswith(".out.json"))

    tally = {
        "lf_on_disk": 0,
        "crlf_only_difference": 0,
        "content_differs": 0,
        "missing_from_worktree": 0,
    }
    crlf_examples = []
    differs_examples = []

    for ref in refs:
        blob, rc_b = run(["git", "cat-file", "blob", "%s:%s" % (head, ref)], binary=True)
        if rc_b != 0:
            continue
        disk_path = os.path.join(REPO, ref.replace("/", os.sep))
        if not os.path.isfile(disk_path):
            tally["missing_from_worktree"] += 1
            continue
        with open(disk_path, "rb") as fh:
            wt = fh.read()
        if wt == blob:
            tally["lf_on_disk"] += 1
        elif wt.replace(b"\r\n", b"\n") == blob:
            tally["crlf_only_difference"] += 1
            if len(crlf_examples) < 8:
                crlf_examples.append(
                    {"ref": ref, "disk_sha256": sha(wt), "blob_sha256": sha(blob)}
                )
        else:
            tally["content_differs"] += 1
            if len(differs_examples) < 8:
                differs_examples.append(
                    {"ref": ref, "disk_sha256": sha(wt), "blob_sha256": sha(blob)}
                )

    out = {
        "probe": os.path.basename(__file__),
        "authority": "read_only_observation; no adoption or deployment authority",
        "head": head,
        "population": "tracked paths ending in .out.json at HEAD",
        "population_size": len(refs),
        "tally": tally,
        "crlf_only_examples_truncated_to_8": crlf_examples,
        "content_differs_examples_truncated_to_8": differs_examples,
        "boundary": (
            "Counts only tracked *.out.json. Untracked probe outputs are invisible here by "
            "construction, and 'content_differs' is not judged - it may be a legitimate "
            "uncommitted re-run. No claim is made about any proposal's adoption."
        ),
    }
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    json.dump({"population_size": len(refs), "tally": tally}, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
