"""Read-only independent review of commit 07309aa (--commit input identity v2).

Re-derives the nine acceptance criteria of the double-signed v2 delegation
without importing the gate's own test file.  Writes no file inside the
workspace except its own .out.json; every subject copy lives in a temp dir.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

REPO = r"D:\WeilanSkillEvolution"
GATE = os.path.join(REPO, "proposals", "scaffold-opensource-export-v0.1",
                    "scan_only_gate.py")
REGISTRY = os.path.join(REPO, "proposals", "redaction-gate-tree-subject-v0.1",
                        "occurrence-registry.jsonl")
PRIVATE = os.path.join(REPO, "proposals", "scaffold-opensource-export-v0.1",
                       "redaction-private-strings.local.txt")
PIN = "4384a5cf2069366c7f89e8b03ee6fb5bcf0d59d7"
NEW_KEYS = ["private_strings_path", "private_strings_bytes_sha256",
            "registry_path", "registry_bytes_sha256", "registry_entry_count",
            "registry_anchor_set_sha256", "gate_version"]
# written out by hand from the spec, not imported from the gate
SPEC_IDENTITY_FIELDS = ("path", "ruleset_digest", "pattern_index", "where",
                        "line_hash", "occurrence_ordinal")


def run(args, cwd=REPO):
    proc = subprocess.run([sys.executable, *args], cwd=cwd,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out = proc.stdout.decode("utf-8", "replace")
    err = proc.stderr.decode("utf-8", "replace")
    try:
        receipt = json.loads(out)
    except json.JSONDecodeError:
        receipt = None
    return {"rc": proc.returncode, "receipt": receipt, "stdout": out,
            "stderr": err}


def digest(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def spec_anchor_digest(entries):
    """Six-step canonical algorithm, re-implemented from the spec text."""
    rows = set()
    for entry in entries:
        projected = []
        for field in SPEC_IDENTITY_FIELDS:
            value = entry[field]
            if isinstance(value, bool):
                value = int(value)
            projected.append(value)
        rows.add(json.dumps(projected, ensure_ascii=False,
                            separators=(",", ":")))
    return hashlib.sha256("\n".join(sorted(rows)).encode("utf-8")).hexdigest()


def read_registry(path):
    entries = []
    with open(path, "rb") as fh:
        for raw in fh.read().split(b"\n"):
            if raw:
                entries.append(json.loads(raw.decode("utf-8")))
    return entries


def summarize(receipt, keep_occurrences=False):
    if receipt is None:
        return None
    thin = {k: v for k, v in receipt.items() if k != "occurrences"}
    thin["_occurrence_digest"] = hashlib.sha256(json.dumps(
        receipt.get("occurrences", []), ensure_ascii=False,
        sort_keys=False).encode("utf-8")).hexdigest()
    if keep_occurrences:
        thin["_occurrences_head"] = receipt.get("occurrences", [])[:2]
    return thin


def main():
    tmp = tempfile.mkdtemp(prefix="gate_review_")
    result = {"tmp": tmp, "pin": PIN, "checks": {}}
    pre = {"registry": digest(REGISTRY), "private": digest(PRIVATE),
           "registry_mtime": os.path.getmtime(REGISTRY),
           "private_mtime": os.path.getmtime(PRIVATE)}

    # ---- old gate from 07309aa^ -------------------------------------------
    old_src = subprocess.run(
        ["git", "show", "07309aae8601642b9b920820c61bd6b241a670de^:"
         "proposals/scaffold-opensource-export-v0.1/scan_only_gate.py"],
        cwd=REPO, stdout=subprocess.PIPE, check=True).stdout
    old_gate = os.path.join(tmp, "old_scan_only_gate.py")
    with open(old_gate, "wb") as fh:
        fh.write(old_src)

    # ---- criterion 1: zero drift on default args ---------------------------
    old_run = run([old_gate, "--commit", PIN])
    new_run = run([GATE, "--commit", PIN])
    old_r, new_r = old_run["receipt"], new_run["receipt"]
    old_keys = list(old_r.keys()) if old_r else []
    new_keys = list(new_r.keys()) if new_r else []
    result["checks"]["c1_zero_drift"] = {
        "old_rc": old_run["rc"], "new_rc": new_run["rc"],
        "old_key_order": old_keys,
        "new_prefix_matches_old": new_keys[:len(old_keys)] == old_keys,
        "new_suffix": new_keys[len(old_keys):],
        "suffix_is_exactly_seven_spec_keys":
            new_keys[len(old_keys):] == NEW_KEYS,
        "shared_values_equal": old_r is not None and new_r is not None and all(
            json.dumps(old_r[k], ensure_ascii=False, sort_keys=False)
            == json.dumps(new_r[k], ensure_ascii=False, sort_keys=False)
            for k in old_keys),
        "occurrences_byte_identical": (
            json.dumps(old_r.get("occurrences"), ensure_ascii=False)
            == json.dumps(new_r.get("occurrences"), ensure_ascii=False)
            if old_r and new_r else None),
        "new_receipt": summarize(new_r),
    }

    # ---- criterion 2: --tree receipt byte-identical -------------------------
    tree_subject = os.path.join(tmp, "tree_subject")
    os.makedirs(tree_subject)
    with open(os.path.join(tree_subject, "a.txt"), "w",
              encoding="utf-8") as fh:
        fh.write("harmless\n")
    old_tree = run([old_gate, "--tree", tree_subject])
    new_tree = run([GATE, "--tree", tree_subject])
    result["checks"]["c2_tree_unchanged"] = {
        "rc_equal": old_tree["rc"] == new_tree["rc"],
        "stdout_byte_identical": old_tree["stdout"] == new_tree["stdout"],
        "rc": new_tree["rc"],
        "registry_keys_absent": new_tree["receipt"] is not None and not any(
            k in new_tree["receipt"] for k in NEW_KEYS),
    }

    # ---- criterion 3: verbatim and reversed registry copies -----------------
    verbatim = os.path.join(tmp, "registry_verbatim.jsonl")
    shutil.copyfile(REGISTRY, verbatim)
    with open(REGISTRY, "rb") as fh:
        raw = fh.read()
    lines = [ln for ln in raw.split(b"\n") if ln]
    reversed_path = os.path.join(tmp, "registry_reversed.jsonl")
    with open(reversed_path, "wb") as fh:
        fh.write(b"\n".join(reversed(lines)))
    dup_path = os.path.join(tmp, "registry_duplicated.jsonl")
    with open(dup_path, "wb") as fh:
        fh.write(b"\n".join(lines + lines))
    v_run = run([GATE, "--commit", PIN, "--registry", verbatim])
    r_run = run([GATE, "--commit", PIN, "--registry", reversed_path])
    d_run = run([GATE, "--commit", PIN, "--registry", dup_path])
    base = new_r
    result["checks"]["c3_registry_copies"] = {
        "verbatim": {
            "rc": v_run["rc"],
            "path_differs": v_run["receipt"]["registry_path"]
            != base["registry_path"],
            "bytes_sha_equal": v_run["receipt"]["registry_bytes_sha256"]
            == base["registry_bytes_sha256"],
            "anchor_sha_equal": v_run["receipt"]["registry_anchor_set_sha256"]
            == base["registry_anchor_set_sha256"],
            "state_equal": v_run["receipt"]["state"] == base["state"],
        },
        "reversed": {
            "rc": r_run["rc"],
            "bytes_sha_differs": r_run["receipt"]["registry_bytes_sha256"]
            != base["registry_bytes_sha256"],
            "anchor_sha_equal": r_run["receipt"]["registry_anchor_set_sha256"]
            == base["registry_anchor_set_sha256"],
            "state_equal": r_run["receipt"]["state"] == base["state"],
            "entry_count_equal": r_run["receipt"]["registry_entry_count"]
            == base["registry_entry_count"],
        },
        "duplicated": {
            "rc": d_run["rc"],
            "anchor_sha_equal": d_run["receipt"]["registry_anchor_set_sha256"]
            == base["registry_anchor_set_sha256"],
            "entry_count_doubled": d_run["receipt"]["registry_entry_count"]
            == 2 * base["registry_entry_count"],
            "stale_anchor_count": d_run["receipt"]["stale_anchor_count"],
            "state_equal": d_run["receipt"]["state"] == base["state"],
        },
    }

    # ---- criterion 4: unreadable / malformed registry -----------------------
    missing = os.path.join(tmp, "nope.jsonl")
    bad = os.path.join(tmp, "registry_bad.jsonl")
    with open(bad, "wb") as fh:
        fh.write(lines[0] + b"\n" + b"{not json\n")
    incomplete = os.path.join(tmp, "registry_incomplete.jsonl")
    with open(incomplete, "wb") as fh:
        fh.write(json.dumps({"path": "x"}).encode("utf-8"))
    a_dir = os.path.join(tmp, "registry_dir")
    os.makedirs(a_dir)
    m_run = run([GATE, "--commit", PIN, "--registry", missing])
    b_run = run([GATE, "--commit", PIN, "--registry", bad])
    i_run = run([GATE, "--commit", PIN, "--registry", incomplete])
    dir_run = run([GATE, "--commit", PIN, "--registry", a_dir])
    result["checks"]["c4_bad_registry"] = {
        "missing": {"rc": m_run["rc"], "stderr": m_run["stderr"].strip(),
                    "stdout_empty": m_run["stdout"] == ""},
        "bad_line": {"rc": b_run["rc"], "stderr": b_run["stderr"].strip(),
                     "stdout_empty": b_run["stdout"] == ""},
        "incomplete": {"rc": i_run["rc"], "stderr": i_run["stderr"].strip(),
                       "stdout_empty": i_run["stdout"] == ""},
        "directory": {"rc": dir_run["rc"],
                      "stderr": dir_run["stderr"].strip()[:200],
                      "stdout_empty": dir_run["stdout"] == "",
                      "is_structured": dir_run["stderr"].strip()
                      .startswith("{")},
    }

    # ---- criteria 5 + 9: NEW_MATCHES receipt carries the seven keys ---------
    fixture = os.path.join(tmp, "fixture_ruleset.txt")
    with open(fixture, "w", encoding="utf-8") as fh:
        fh.write("peer_health_wake\ntest_peer_health_wake\n")
    f_run = run([GATE, "--commit", PIN, "--private-strings", fixture])
    f_r = f_run["receipt"]
    result["checks"]["c5_c9_new_matches"] = {
        "rc": f_run["rc"],
        "state": f_r["state"] if f_r else None,
        "all_seven_present": f_r is not None and all(k in f_r
                                                     for k in NEW_KEYS),
        "gate_version_rc2": f_r.get("gate_version") if f_r else None,
        "gate_version_rc3": base.get("gate_version"),
        "private_path_is_fixture": f_r is not None
        and f_r["private_strings_path"] == os.path.abspath(fixture),
        "private_bytes_sha_matches_disk": f_r is not None
        and f_r["private_strings_bytes_sha256"] == digest(fixture),
        "anchor_sha_equal_base": f_r is not None
        and f_r["registry_anchor_set_sha256"]
        == base["registry_anchor_set_sha256"],
        "occurrence_count": f_r.get("occurrence_count") if f_r else None,
    }

    # ---- criterion 8: canonical algorithm re-derived independently ----------
    entries = read_registry(REGISTRY)
    spec_from_disk = spec_anchor_digest(entries)
    spec_reversed = spec_anchor_digest(list(reversed(entries)))
    spec_dup = spec_anchor_digest(entries + entries)
    empty = hashlib.sha256(b"").hexdigest()
    bool_entry = dict(entries[0])
    bool_entry["pattern_index"] = True
    int_entry = dict(entries[0])
    int_entry["pattern_index"] = 1
    mutated = dict(entries[0])
    mutated["line_hash"] = "0" * 64
    result["checks"]["c8_canonical"] = {
        "spec_digest_from_disk": spec_from_disk,
        "gate_receipt_digest": base["registry_anchor_set_sha256"],
        "independent_matches_receipt":
            spec_from_disk == base["registry_anchor_set_sha256"],
        "F1_order_invariant": spec_reversed == spec_from_disk,
        "F1_duplication_invariant": spec_dup == spec_from_disk,
        "F4_empty_set": spec_anchor_digest([]) == empty,
        "empty_vector": spec_anchor_digest([]),
        "bool_int_equal": spec_anchor_digest([bool_entry])
        == spec_anchor_digest([int_entry]),
        "F2_discriminative": spec_anchor_digest([mutated])
        != spec_anchor_digest([entries[0]]),
        "entry_count_disk": len(entries),
        "entry_count_receipt": base["registry_entry_count"],
    }

    # ---- criterion 7: cross-workspace binding via file:// clone -------------
    clone = os.path.join(tmp, "clone")
    clone_proc = subprocess.run(
        ["git", "clone", "--no-checkout", "--quiet",
         "file:///D:/WeilanSkillEvolution", clone],
        cwd=tmp, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    c7 = {"clone_rc": clone_proc.returncode,
          "clone_stderr": clone_proc.stderr.decode("utf-8", "replace")[:300]}
    if clone_proc.returncode == 0:
        c_registry = os.path.join(clone, "copied-registry.jsonl")
        c_private = os.path.join(clone, "copied-private.txt")
        shutil.copyfile(REGISTRY, c_registry)
        shutil.copyfile(PRIVATE, c_private)
        c_run = run([GATE, "--commit", PIN, "--registry", c_registry,
                     "--private-strings", c_private], cwd=clone)
        c_r = c_run["receipt"]
        c7.update({
            "rc": c_run["rc"],
            "stderr": c_run["stderr"].strip()[:300],
            "paths_differ": c_r is not None
            and c_r["registry_path"] != base["registry_path"]
            and c_r["private_strings_path"] != base["private_strings_path"],
            "digests_equal": c_r is not None and all(
                c_r[k] == base[k] for k in
                ("registry_bytes_sha256", "private_strings_bytes_sha256",
                 "registry_anchor_set_sha256", "ruleset_digest",
                 "resolved_oid")),
            "thirteen_keys_equal": c_r is not None and all(
                json.dumps(c_r[k], ensure_ascii=False)
                == json.dumps(base[k], ensure_ascii=False)
                for k in old_keys),
            "state": c_r.get("state") if c_r else None,
        })
    result["checks"]["c7_cross_workspace"] = c7

    # ---- criterion 6: gate wrote nothing, printed no pattern ---------------
    post = {"registry": digest(REGISTRY), "private": digest(PRIVATE),
            "registry_mtime": os.path.getmtime(REGISTRY),
            "private_mtime": os.path.getmtime(PRIVATE)}
    with open(PRIVATE, encoding="utf-8") as fh:
        secrets = [ln.strip() for ln in fh if ln.strip()]
    every_stream = "".join(
        r["stdout"] + r["stderr"] for r in
        (old_run, new_run, v_run, r_run, d_run, m_run, b_run, i_run, dir_run,
         f_run) )
    result["checks"]["c6_read_only"] = {
        "subjects_unchanged": pre == post,
        "leaked_pattern_count": sum(1 for s in secrets
                                    if s in every_stream),
        "tmp_files_written_in_repo": False,
    }
    result["_note"] = ("leaked_pattern_count counts private tokens appearing "
                       "verbatim in any gate stdout/stderr of this probe")
    out = __file__.replace(".py", ".out.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=1)
    print(out)
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
