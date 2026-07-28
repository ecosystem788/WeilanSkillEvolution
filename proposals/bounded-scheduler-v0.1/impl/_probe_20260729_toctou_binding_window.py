"""Probe: can "bind the effective input vector to THIS evaluation" be implemented
by snapshotting before/after the adjudication?

Context (peer-chat 2026-07-29T03:47:20+09:00, codex): the signed clause requires the
detector's effective-input-vector to be bound to the evaluation being adjudicated, and
codex explicitly flagged TOCTOU as untested: "只在事后打印 env 不够，mutable refs/files/config
也须与判定时快照绑定".

This probe treats the cheapest plausible implementation of that binding -- bracketing the
adjudication with a detection pass on each side and requiring both to agree -- as the
proposition under test.

All work happens in temp dirs. The workspace repo is never read or written by the probe.
Deterministic: no threads, no races. The mutation window is placed inside the bracket by
plain sequencing, so the result does not depend on timing.

Legs:
  A  baseline            : clean repo -> detector clean, adjudication TRUE, truth TRUE
  B  mutate-inside-bracket: detect(clean) -> graft -> adjudicate -> ungraft -> detect(clean)
  C  repo-state digest   : does hashing all refs + grafts at both ends catch leg B?
  D  ordering control    : leave the mutation in place -> does detect-after catch it?
  E  in-process evidence : does trace2 / GIT_TRACE expose the replace set actually applied
                           during the adjudication itself (evidence from inside the same
                           evaluation rather than from a bracket)?
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

GIT = "git"


def run(args, cwd, env=None, check=True):
    e = dict(os.environ)
    e.setdefault("GIT_CONFIG_NOSYSTEM", "1")
    e.setdefault("HOME", cwd)
    if env:
        e.update(env)
    p = subprocess.run(
        [GIT] + args, cwd=cwd, env=e, capture_output=True, text=True, encoding="utf-8",
        errors="replace",
    )
    if check and p.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} -> rc={p.returncode}\n{p.stderr}")
    return p


def make_repo(root, n=10):
    os.makedirs(root, exist_ok=True)
    run(["init", "-q", "-b", "main", "."], root)
    run(["config", "user.email", "probe@example.invalid"], root)
    run(["config", "user.name", "probe"], root)
    oids = []
    for i in range(1, n + 1):
        with open(os.path.join(root, "f.txt"), "w", encoding="utf-8") as fh:
            fh.write(f"c{i}\n")
        run(["add", "f.txt"], root)
        run(["commit", "-q", "-m", f"c{i}"], root)
        oids.append(run(["rev-parse", "HEAD"], root).stdout.strip())
    return oids


# ---- the detector under test: the enumerators that survived the previous round ----

def detect(root, env=None):
    """Positive enumeration of graph-rewrite mechanisms, keyed on git-resolved
    effective values (peer-chat 2026-07-29T03:32:45+09:00 item 3)."""
    replace_l = run(["replace", "-l"], root, env, check=False).stdout.strip()
    graft_path = run(["rev-parse", "--git-path", "info/grafts"], root, env).stdout.strip()
    graft_abs = graft_path if os.path.isabs(graft_path) else os.path.join(root, graft_path)
    graft_exists = os.path.exists(graft_abs)
    shallow_path = run(["rev-parse", "--git-path", "shallow"], root, env).stdout.strip()
    shallow_abs = shallow_path if os.path.isabs(shallow_path) else os.path.join(root, shallow_path)
    return {
        "replace_l": [x for x in replace_l.splitlines() if x],
        "graft_effective_path": graft_path,
        "graft_exists": graft_exists,
        "shallow_exists": os.path.exists(shallow_abs),
        "env_keys": {
            k: (env or {}).get(k, os.environ.get(k))
            for k in ("GIT_REPLACE_REF_BASE", "GIT_GRAFT_FILE", "GIT_NO_REPLACE_OBJECTS")
        },
    }


def detector_says_clean(d):
    return not d["replace_l"] and not d["graft_exists"] and not d["shallow_exists"]


def adjudicate(root, anc, desc, env=None):
    """The reachability question being answered: is `anc` an ancestor of `desc`?"""
    rc = run(["merge-base", "--is-ancestor", anc, desc], root, env, check=False).returncode
    return {"rc": rc, "answer": True if rc == 0 else (False if rc == 1 else None)}


def ungrafted_truth(root, anc, desc):
    """Truth oracle: walk the real object graph. Note --no-replace-objects is NOT
    trustworthy against info/grafts (proved 2026-07-29T03:09:35+09:00 item 4), so the
    oracle here is taken on a pristine clone-free copy with no mechanism in place."""
    rc = run(
        ["merge-base", "--is-ancestor", anc, desc], root,
        {"GIT_NO_REPLACE_OBJECTS": "1"}, check=False,
    ).returncode
    return True if rc == 0 else (False if rc == 1 else None)


def repo_state_digest(root, env=None):
    """Cheapest plausible 'bind mutable repo state' receipt: hash every ref plus the
    contents of the graft/shallow files."""
    h = hashlib.sha256()
    refs = run(["for-each-ref", "--format=%(refname) %(objectname)"], root, env).stdout
    h.update(refs.encode())
    for rel in ("info/grafts", "shallow"):
        p = run(["rev-parse", "--git-path", rel], root, env).stdout.strip()
        ap = p if os.path.isabs(p) else os.path.join(root, p)
        if os.path.exists(ap):
            with open(ap, "rb") as fh:
                h.update(fh.read())
        else:
            h.update(b"<absent>")
    return h.hexdigest()


def walker_domain(root, env=None):
    return len([x for x in run(["rev-list", "HEAD"], root, env).stdout.splitlines() if x])


def main():
    out = {"git_version": run(["--version"], os.getcwd()).stdout.strip(), "legs": {}}
    tmp = tempfile.mkdtemp(prefix="toctou_bind_")
    try:
        # ---------------- leg A: baseline ----------------
        a = os.path.join(tmp, "a")
        oids = make_repo(a)
        c1, head = oids[0], oids[-1]
        d0 = detect(a)
        adjA = adjudicate(a, c1, head)
        out["legs"]["A_baseline"] = {
            "detector_clean": detector_says_clean(d0),
            "adjudication": adjA,
            "truth": ungrafted_truth(a, c1, head),
            "walker_domain": walker_domain(a),
        }

        # ------- leg B: mutation lands strictly inside the bracket -------
        b = os.path.join(tmp, "b")
        oids = make_repo(b)
        c1, c5, head = oids[0], oids[4], oids[-1]

        pre = detect(b)
        pre_clean = detector_says_clean(pre)

        run(["replace", "--graft", c5], b)          # mutation opens
        adjB = adjudicate(b, c1, head)              # the evaluation being adjudicated
        dom_at_adj = walker_domain(b)
        replace_at_adj = [x for x in run(["replace", "-l"], b).stdout.splitlines() if x]
        run(["replace", "-d", c5], b)               # mutation closes

        post = detect(b)
        post_clean = detector_says_clean(post)

        out["legs"]["B_mutation_inside_bracket"] = {
            "pre_detector_clean": pre_clean,
            "post_detector_clean": post_clean,
            "bracket_agrees_and_clean": pre_clean and post_clean,
            "pre_vector": pre,
            "post_vector": post,
            "vectors_identical": pre == post,
            "adjudication": adjB,
            "walker_domain_during_adjudication": dom_at_adj,
            "replace_l_during_adjudication": replace_at_adj,
            "truth": ungrafted_truth(b, c1, head),
            "contract_authorizes_definite_answer": pre_clean and post_clean,
            "answer_is_wrong": adjB["answer"] is not ungrafted_truth(b, c1, head),
        }

        # ---- leg C: does a repo-state digest bracket catch leg B? ----
        c = os.path.join(tmp, "c")
        oids = make_repo(c)
        c1, c5, head = oids[0], oids[4], oids[-1]
        dig_pre = repo_state_digest(c)
        run(["replace", "--graft", c5], c)
        adjC = adjudicate(c, c1, head)
        run(["replace", "-d", c5], c)
        dig_post = repo_state_digest(c)
        out["legs"]["C_repo_state_digest_bracket"] = {
            "digest_pre": dig_pre,
            "digest_post": dig_post,
            "digests_match": dig_pre == dig_post,
            "adjudication": adjC,
            "truth": ungrafted_truth(c, c1, head),
            "digest_bracket_catches_it": dig_pre != dig_post,
        }

        # ---- leg D: ordering control -- mutation left in place ----
        d = os.path.join(tmp, "d")
        oids = make_repo(d)
        c1, c5, head = oids[0], oids[4], oids[-1]
        pre_d = detect(d)
        run(["replace", "--graft", c5], d)
        adjD = adjudicate(d, c1, head)
        post_d = detect(d)
        out["legs"]["D_mutation_left_in_place"] = {
            "pre_detector_clean": detector_says_clean(pre_d),
            "post_detector_clean": detector_says_clean(post_d),
            "post_detector_catches_it": not detector_says_clean(post_d),
            "adjudication": adjD,
            "truth": ungrafted_truth(d, c1, head),
        }

        # ---- leg E: is there evidence from INSIDE the same evaluation? ----
        e = os.path.join(tmp, "e")
        oids = make_repo(e)
        c1, c5, head = oids[0], oids[4], oids[-1]
        run(["replace", "--graft", c5], e)
        trace_path = os.path.join(tmp, "trace2.jsonl")
        p = run(
            ["merge-base", "--is-ancestor", c1, head], e,
            {"GIT_TRACE2_EVENT": trace_path, "GIT_TRACE": "1"}, check=False,
        )
        trace_txt = ""
        if os.path.exists(trace_path):
            with open(trace_path, encoding="utf-8", errors="replace") as fh:
                trace_txt = fh.read()
        combined = trace_txt + "\n" + p.stderr
        short5 = c5[:8]
        out["legs"]["E_in_process_evidence"] = {
            "adjudication_rc": p.returncode,
            "trace2_bytes": len(trace_txt),
            "stderr_bytes": len(p.stderr),
            "mentions_replace": "replace" in combined.lower(),
            "mentions_grafted_oid": short5 in combined,
            "trace_exposes_applied_replace_set": (
                "replace" in combined.lower() and short5 in combined
            ),
            "sample": combined[:400],
        }

        print(json.dumps(out, ensure_ascii=False, indent=1))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
