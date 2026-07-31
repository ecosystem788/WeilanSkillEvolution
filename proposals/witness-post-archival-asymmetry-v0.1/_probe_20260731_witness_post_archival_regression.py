#!/usr/bin/env python3
"""Read-only: is the post-side witness detail archived, landing by landing?

CONVENTION §5.3.d names three artifacts to archive; `witness-archival-gap-v0.1`
found the .witness snapshot was 0/6. That gap was then closed -- twice. This probe
asks the next question: the conservation verdict `non_target_conserved` is
`witness_digest_post == witness_digest_pre`, so a third party who wants to recheck
it needs BOTH detail files. Which landings archived which?

Census over every commit that ever added a postcheck-receipt.json (= a landing),
plus a recompute of each archived detail file against the digest its receipt claims.
"""
import hashlib
import json
import subprocess
import sys

REPO = r"D:\WeilanSkillEvolution"


def git(*a, check=True):
    p = subprocess.run(["git", "-C", REPO] + list(a), capture_output=True)
    if check and p.returncode != 0:
        return None
    return p.stdout


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def main():
    log = git("log", "--all", "--diff-filter=A", "--name-only",
              "--format=@%H %ad", "--date=short", "--", "*postcheck-receipt.json")
    landings = []
    cur = None
    for line in log.decode("utf-8", "replace").splitlines():
        if line.startswith("@"):
            cur = {"commit": line[1:41], "date": line[42:], "receipts": []}
            landings.append(cur)
        elif line.strip() and cur is not None:
            cur["receipts"].append(line.strip())

    rows = []
    for L in landings:
        for rpath in L["receipts"]:
            d = rpath.rsplit("/", 1)[0]
            raw = git("cat-file", "blob", f"{L['commit']}:{rpath}")
            rec = json.loads(raw.decode("utf-8-sig"))
            row = {
                "commit": L["commit"][:7],
                "date": L["date"],
                "dir": d,
                "ok": rec.get("ok"),
                "non_target_conserved": rec.get("non_target_conserved"),
                "digest_pre": rec.get("witness_digest_pre"),
                "digest_post": rec.get("witness_digest_post"),
            }
            # is each detail file present in that landing tree, and does it recompute?
            for side, suffix in (("pre", ".witness"), ("post", ".witness.post")):
                # find any file in that dir ending with the suffix
                tree = git("ls-tree", "-r", "--name-only", L["commit"], d + "/")
                names = tree.decode("utf-8", "replace").split("\n") if tree else []
                hit = [n for n in names if n.endswith(suffix)]
                if suffix == ".witness":
                    hit = [n for n in hit if not n.endswith(".witness.post")]
                if not hit:
                    row[f"{side}_detail"] = "ABSENT"
                    continue
                blob = git("cat-file", "blob", f"{L['commit']}:{hit[0]}")
                got = sha256(blob)
                row[f"{side}_detail"] = (
                    "recomputes" if got == row[f"digest_{side}"] else f"MISMATCH:{got[:12]}"
                )
            rows.append(row)

    rows.sort(key=lambda r: r["date"])
    out = {
        "landings": len(rows),
        "rows": rows,
        "summary": {
            "pre_archived_and_recomputes": sum(1 for r in rows if r.get("pre_detail") == "recomputes"),
            "post_archived_and_recomputes": sum(1 for r in rows if r.get("post_detail") == "recomputes"),
            "pre_absent": sum(1 for r in rows if r.get("pre_detail") == "ABSENT"),
            "post_absent": sum(1 for r in rows if r.get("post_detail") == "ABSENT"),
        },
    }
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
