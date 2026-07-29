"""Read-only follow-up probe for the withdrawal-link sidecar entry.

  A. Path-scoped test of "has the chat line ever entered a commit" vs the
     unscoped -S test used in peer-chat 2026-07-30T03:30:33+09:00.
     Also: which files in d405684 actually carry those stamps.
  B. Checkout form of peer-chat.jsonl (git cat-file --filters): does a fresh
     clone land CRLF, i.e. would the "current physical line bytes" convention
     survive a clone for this particular file?
  C. Is peer-chat.corrections.jsonl line 16 in HEAD at all?
  D. Does peer_health_wake surface the withdrawal-link entry? (structural read:
     the entry's target line must be an invalid-JSON line to be consulted.)
No writes.
"""
import hashlib
import json
import subprocess
import sys

ROOT = r"D:\WeilanSkillEvolution"
CHAT = "proposals/bounded-scheduler-v0.1/impl/peer-chat.jsonl"
CORR = "proposals/bounded-scheduler-v0.1/impl/peer-chat.corrections.jsonl"
STAMPS = {
    "chat_3017": "2026-07-30T02:58:26+09:00",
    "chat_3019": "2026-07-30T03:17:03+09:00",
    "corrections_16": "2026-07-30T03:40:04+09:00",
}


def git(*args):
    p = subprocess.run(["git", "-C", ROOT] + list(args), capture_output=True)
    return p.returncode, p.stdout, p.stderr


def split_lines(blob: bytes):
    parts = blob.split(b"\n")
    if parts and parts[-1] == b"":
        parts.pop()
    return parts


def main():
    out = {}

    # A. path-scoped vs unscoped
    a = {}
    for label, stamp in STAMPS.items():
        rc, unscoped, _ = git("log", "--all", "--oneline", "-S", stamp)
        rc2, scoped, _ = git("log", "--all", "--oneline", "-S", stamp, "--",
                             CHAT if label.startswith("chat") else CORR)
        a[label] = {
            "unscoped": unscoped.decode("utf-8", "replace").split() or ["none"],
            "scoped_to_own_ledger": scoped.decode("utf-8", "replace").split() or ["none"],
        }
    # which files in d405684 carry the chat stamps
    rc, names, _ = git("show", "--name-only", "--format=", "d405684")
    carriers = {}
    for path in names.decode("utf-8", "replace").split():
        rc2, blob, _ = git("show", f"d405684:{path}")
        if rc2 != 0:
            continue
        carriers[path] = [k for k, s in STAMPS.items() if s.encode() in blob]
    a["d405684_files_carrying_stamps"] = carriers
    out["A_in_tree_test"] = a

    # B. checkout form
    rc, filtered, err = git("cat-file", "--filters", f"HEAD:{CHAT}")
    if rc == 0:
        flines = split_lines(filtered)
        out["B_checkout_form"] = {
            "lines": len(flines),
            "cr_terminated_lines": sum(1 for ln in flines if ln.endswith(b"\r")),
            "sha256_of_line_3016_if_present": (
                hashlib.sha256(flines[3015]).hexdigest() if len(flines) >= 3016 else None
            ),
        }
    else:
        out["B_checkout_form"] = f"error: {err.decode('utf-8', 'replace')}"

    # C. corrections file in HEAD
    rc, corr_head, err = git("show", f"HEAD:{CORR}")
    with open(rf"{ROOT}\{CORR}".replace("/", "\\"), "rb") as f:
        corr_wt = split_lines(f.read())
    out["C_corrections"] = {
        "working_tree_lines": len(corr_wt),
        "head_blob_lines": len(split_lines(corr_head)) if rc == 0 else f"error: {err!r}",
    }

    # D. would peer_health_wake consult it? target must fail json.loads
    target = corr_wt  # placeholder to keep names obvious
    with open(rf"{ROOT}\{CHAT}".replace("/", "\\"), "rb") as f:
        chat_wt = split_lines(f.read())
    line_3017 = chat_wt[3016]
    parses = True
    try:
        json.loads(line_3017.decode("utf-8"))
    except Exception:  # noqa: BLE001
        parses = False
    out["D_reader"] = {
        "target_line_3017_parses_as_json": parses,
        "note": ("peer_health_wake._known_correction is called only from the "
                 "json.JSONDecodeError branch of _rows; a parsing target line "
                 "is never matched against the corrections sidecar."),
        "corrections_entry_kinds_seen": sorted(
            {json.loads(ln.decode("utf-8")).get("kind", "<none>") for ln in target}
        ),
    }

    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
