"""Read-only census: do 执行收据 quote their authorizations' file references faithfully?

Motivating instance (2026-07-30): receipt at 02:58:26+09:00 rendered the 同意's
verbatim citation `proposals/bounded-scheduler-v0.1/impl/_probe_20260730_citation_forms_review.py`
as bare name `_probe_20260730_citation_forms_review.py` plus a *different* directory
`proposals/cited-evidence-absent-from-tree-v0.1/...`. The classification (not_in_tree)
happened to survive because both paths are absent from the tree — so the mis-quote was
invisible to any check that re-parses the receipt's own copy of the string.

This probe never re-parses the receipt's copy alone. For each receipt it goes back to
the authorization lines the receipt itself names, extracts their path-like tokens, and
sorts basename-matched pairs into three buckets. Only the first two are defects:

  dir_dropped     : authorization cited DIR/N, receipt cites bare N. Information the
                    authorization had is gone from the receipt; a third party re-parsing
                    the receipt cannot recover which DIR was meant.
  dir_contradicted: authorization cited DIR_A/N, receipt cites DIR_R/N, DIR_A != DIR_R.
  dir_asserted    : authorization cited bare N, receipt supplies DIR/N. NOT a defect by
                    itself -- disambiguation is the direction we want -- but the receipt
                    is asserting something the authorization never said, so each one is
                    reported with a tree check: does DIR/N exist at HEAD, and is N a
                    unique basename in HEAD's tree? A non-unique or absent basename means
                    the resolution rests on the executor's inference alone.

Tokens in the receipt that share no basename with any authorization token are NOT
flagged: a receipt legitimately names files it touched. Receipts whose cited
authorization stamps cannot be resolved are reported separately as `unresolved`
and are counted in no other bucket -- zero hits here is not zero input.

Known tokenizer limit, stated rather than hidden: the path regex accepts any
slash-joined run of name characters ending in a known extension, so prose that runs two
filenames together without whitespace yields one glued token (observed:
`wake_agent.ps1/test_wake_sentinel.py`). Glued tokens are reported verbatim; judge them
by reading the cited line, not by trusting this bucket.

Everything is read-only. Nothing is written, staged, or committed.
"""
import io
import json
import re
import subprocess
import sys
from collections import OrderedDict

LEDGER = ("D:/WeilanSkillEvolution/proposals/bounded-scheduler-v0.1/impl/"
          "peer-chat.jsonl")

STAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+\d{2}:\d{2}")
# repo-relative-ish path or bare filename with a known code/doc extension
EXTS = r"(?:py|md|json|jsonl|tsv|txt|toml|yaml|yml|cfg|ps1|sh)"
TOKEN_RE = re.compile(r"[0-9A-Za-z_.\-]+(?:/[0-9A-Za-z_.\-]+)*\." + EXTS + r"\b")


def load(path):
    rows, unparsed = [], []
    for n, raw in enumerate(io.open(path, encoding="utf-8"), 1):
        if not raw.strip():
            continue
        try:
            rows.append((n, json.loads(raw)))
        except Exception as exc:
            unparsed.append((n, str(exc)))
    return rows, unparsed


def basename(tok):
    return tok.rsplit("/", 1)[-1]


_HEAD_TREE = None


def head_tree():
    """Every tracked path at HEAD. Read-only; HEAD, not each landing commit --
    stated so nobody reads these checks as being about the receipt's own tree."""
    global _HEAD_TREE
    if _HEAD_TREE is None:
        p = subprocess.run(["git", "-C", "D:/WeilanSkillEvolution",
                            "ls-tree", "-r", "--name-only", "HEAD"],
                           capture_output=True)
        if p.returncode != 0:
            sys.exit("ls-tree failed: %s" % p.stderr.decode("utf-8", "replace"))
        _HEAD_TREE = p.stdout.decode("utf-8").splitlines()
    return _HEAD_TREE


def head_check(tok):
    tree = head_tree()
    same_base = [t for t in tree if basename(t) == basename(tok)]
    return {"asserted_path_at_head": "present" if tok in tree else "absent",
            "basename_matches_at_head": len(same_base),
            "matches": sorted(same_base)[:5]}


def main():
    rows, unparsed = load(LEDGER)
    by_time = OrderedDict()
    for n, obj in rows:
        t = obj.get("time")
        if t is not None:
            by_time.setdefault(t, (n, obj))

    receipts = [(n, o) for n, o in rows if "执行收据" in (o.get("text") or "")]

    report = {
        "ledger": LEDGER,
        "ledger_lines_parsed": len(rows),
        "ledger_lines_unparsed": [{"line": n, "error": e} for n, e in unparsed],
        "receipts_total": len(receipts),
        "receipts_unresolved_authorization": [],
        "receipts_checked": 0,
        "findings": [],
        "assertions_only": [],
        "clean_receipts": [],
    }

    for n, obj in receipts:
        text = obj.get("text") or ""
        own = obj.get("time")
        cited = [s for s in dict.fromkeys(STAMP_RE.findall(text))
                 if s != own and s in by_time]
        if not cited:
            report["receipts_unresolved_authorization"].append(
                {"line": n, "time": own,
                 "reason": "no cited stamp resolves to a ledger line"})
            continue
        report["receipts_checked"] += 1

        auth_tokens = set()
        for s in cited:
            auth_tokens.update(TOKEN_RE.findall(by_time[s][1].get("text") or ""))
        recv_tokens = set(TOKEN_RE.findall(text))

        auth_by_base = {}
        for t in auth_tokens:
            auth_by_base.setdefault(basename(t), set()).add(t)

        hits, asserted = [], []
        for r in sorted(recv_tokens):
            if r in auth_tokens:
                continue
            peers = auth_by_base.get(basename(r))
            if not peers:
                continue  # different file entirely; not a quotation of this auth
            with_dir = sorted(p for p in peers if "/" in p)
            if "/" not in r:
                if with_dir:
                    hits.append({"kind": "dir_dropped", "receipt_token": r,
                                 "authorization_tokens": with_dir})
            elif with_dir and r not in with_dir:
                hits.append({"kind": "dir_contradicted", "receipt_token": r,
                             "authorization_tokens": with_dir})
            elif not with_dir:
                asserted.append({"kind": "dir_asserted", "receipt_token": r,
                                 "authorization_tokens": sorted(peers),
                                 "head_check": head_check(r)})
        entry = {"line": n, "time": own, "cited_authorizations": cited}
        if hits:
            entry["mutations"] = hits
            if asserted:
                entry["assertions"] = asserted
            report["findings"].append(entry)
        elif asserted:
            entry["assertions"] = asserted
            report["assertions_only"].append(entry)
        else:
            report["clean_receipts"].append({"line": n, "time": own})

    report["summary"] = {
        "receipts_total": len(receipts),
        "checked": report["receipts_checked"],
        "unresolved": len(report["receipts_unresolved_authorization"]),
        "with_mutations": len(report["findings"]),
        "assertions_only": len(report["assertions_only"]),
        "clean": len(report["clean_receipts"]),
    }
    json.dump(report, sys.stdout, ensure_ascii=False, indent=1)
    print()


if __name__ == "__main__":
    main()
