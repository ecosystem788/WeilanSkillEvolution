#!/usr/bin/env python3
"""Attack my own peer-chat claim (2026-07-29T02:46 item 7 / Codex 03:20 registry clause):
"the four grafting mechanisms are all cheaply enumerable -- for-each-ref refs/replace/,
rev-parse --git-path info/grafts + existence, remote.*.promisor, .git/shallow".

Those probes are keyed on FIXED namespaces/paths. Git documents two environment knobs that
relocate exactly those two sources:
  GIT_REPLACE_REF_BASE  -- where refs/replace/* actually live
  GIT_GRAFT_FILE        -- where the grafts file actually lives

If the walker honours the relocated source while the fixed-path probe reports "empty",
then the registry itself reproduces the fail-open one level up: a registry that looks clean
because it looked in the wrong place, and then authorises a definitive verdict.

Also tests the constructive alternative: whether asking git in the SAME environment
(`git replace -l`, namespace-agnostic `for-each-ref`) recovers the mechanism.

Read-only w.r.t. the workspace; all work in a temp directory. No network, no writes to the repo.
"""

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ENV = dict(os.environ)
ENV.update({
    "GIT_AUTHOR_NAME": "probe", "GIT_AUTHOR_EMAIL": "probe@local",
    "GIT_COMMITTER_NAME": "probe", "GIT_COMMITTER_EMAIL": "probe@local",
    "GIT_CONFIG_NOSYSTEM": "1", "HOME": tempfile.gettempdir(),
})
# make sure the host environment does not already carry the knobs under test
for _k in ("GIT_REPLACE_REF_BASE", "GIT_GRAFT_FILE"):
    ENV.pop(_k, None)


def git(cwd, *args, env=None, check=True):
    e = dict(ENV)
    if env:
        e.update(env)
    p = subprocess.run(["git", "-c", "commit.gpgsign=false", *args], cwd=str(cwd),
                       capture_output=True, text=True, env=e)
    if check and p.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} -> rc={p.returncode}\n{p.stderr}")
    return p


def main():
    root = Path(tempfile.mkdtemp(prefix="wl_reg_reloc_"))
    out = {"git_version": None, "legs": {}}
    try:
        repo = root / "repo"
        repo.mkdir()
        git(repo, "init", "-q", "-b", "main")
        out["git_version"] = git(repo, "--version").stdout.strip()
        oids = []
        for i in range(1, 11):
            (repo / "f.txt").write_text(f"line {i}\n", encoding="utf-8")
            git(repo, "add", "f.txt")
            git(repo, "commit", "-q", "-m", f"c{i}")
            oids.append(git(repo, "rev-parse", "HEAD").stdout.strip())
        c1, c5 = oids[0], oids[4]
        gd = Path(git(repo, "rev-parse", "--absolute-git-dir").stdout.strip())

        def domain(env=None):
            return int(git(repo, "rev-list", "--count", "HEAD", env=env).stdout.strip())

        def is_ancestor(env=None):
            return git(repo, "merge-base", "--is-ancestor", c1, "HEAD",
                       env=env, check=False).returncode

        def fixed_replace_probe(env=None):
            r = git(repo, "for-each-ref", "--format=%(refname)", "refs/replace/", env=env)
            return [x for x in r.stdout.splitlines() if x.strip()]

        def all_refs(env=None):
            r = git(repo, "for-each-ref", "--format=%(refname)", env=env)
            return [x for x in r.stdout.splitlines() if x.strip()]

        def fixed_graft_probe(env=None):
            p = git(repo, "rev-parse", "--git-path", "info/grafts", env=env).stdout.strip()
            fp = Path(p) if Path(p).is_absolute() else (repo / p)
            return {"path": str(fp), "exists": fp.exists()}

        def replace_list(env=None):
            r = git(repo, "replace", "-l", env=env, check=False)
            return {"rc": r.returncode,
                    "lines": [x for x in r.stdout.splitlines() if x.strip()]}

        out["legs"]["0_baseline"] = {
            "true_domain": domain(),
            "true_is_ancestor_rc": is_ancestor(),
            "fixed_replace_probe": fixed_replace_probe(),
            "fixed_graft_probe": fixed_graft_probe(),
            "note": "ground truth: c1 IS an ancestor of HEAD; domain 10",
        }

        # ---- Leg A: control. Default replace namespace; registry probe should see it. ----
        git(repo, "replace", "--graft", c5)
        out["legs"]["A_default_replace_namespace"] = {
            "fixed_replace_probe": fixed_replace_probe(),
            "replace_list": replace_list(),
            "walker_domain": domain(),
            "is_ancestor_rc": is_ancestor(),
            "registry_probe_sees_mechanism": bool(fixed_replace_probe()),
        }
        for ref in fixed_replace_probe():
            git(repo, "update-ref", "-d", ref)
        assert domain() == 10, "cleanup of default replace ref failed"

        # ---- Leg B: relocated replace ref base. ----
        base = "refs/hidden/replace/"
        benv = {"GIT_REPLACE_REF_BASE": base}
        git(repo, "replace", "--graft", c5, env=benv)
        legB = {
            "relocated_base": base,
            "with_env": {
                "fixed_replace_probe": fixed_replace_probe(env=benv),
                "replace_list": replace_list(env=benv),
                "all_refs_containing_replace": [r for r in all_refs(env=benv) if "replace" in r],
                "walker_domain": domain(env=benv),
                "is_ancestor_rc": is_ancestor(env=benv),
            },
            "without_env": {
                "fixed_replace_probe": fixed_replace_probe(),
                "replace_list": replace_list(),
                "all_refs_containing_replace": [r for r in all_refs() if "replace" in r],
                "walker_domain": domain(),
                "is_ancestor_rc": is_ancestor(),
            },
        }
        wenv = legB["with_env"]
        legB["fail_open"] = {
            "fixed_probe_reports_clean": wenv["fixed_replace_probe"] == [],
            "walker_is_grafted": wenv["walker_domain"] != 10,
            # contract per Codex 03:20: clean registry -> definitive verdict allowed
            "contract_verdict": "FALSE" if wenv["is_ancestor_rc"] != 0 else "TRUE",
            "ground_truth": "TRUE",
        }
        legB["fail_open"]["registry_authorises_wrong_answer"] = (
            legB["fail_open"]["fixed_probe_reports_clean"]
            and legB["fail_open"]["contract_verdict"] != legB["fail_open"]["ground_truth"]
        )
        legB["recovered_by_same_env_git_query"] = bool(wenv["replace_list"]["lines"])
        legB["recovered_by_namespace_agnostic_ref_scan"] = bool(
            wenv["all_refs_containing_replace"])
        out["legs"]["B_relocated_replace_base"] = legB
        for ref in [r for r in all_refs() if r.startswith("refs/hidden/")]:
            git(repo, "update-ref", "-d", ref)
        assert domain() == 10, "cleanup of relocated replace ref failed"

        # ---- Leg C: relocated grafts file. ----
        alt = root / "elsewhere" / "mygrafts"
        alt.parent.mkdir(parents=True, exist_ok=True)
        alt.write_text(f"{c5}\n", encoding="utf-8")
        cenv = {"GIT_GRAFT_FILE": str(alt)}
        legC = {
            "relocated_graft_file": str(alt),
            "with_env": {
                "fixed_graft_probe": fixed_graft_probe(env=cenv),
                "walker_domain": domain(env=cenv),
                "is_ancestor_rc": is_ancestor(env=cenv),
            },
            "without_env": {
                "fixed_graft_probe": fixed_graft_probe(),
                "walker_domain": domain(),
                "is_ancestor_rc": is_ancestor(),
            },
            "default_graft_path_exists": (gd / "info" / "grafts").exists(),
        }
        cw = legC["with_env"]
        legC["fail_open"] = {
            "fixed_probe_reports_clean": not cw["fixed_graft_probe"]["exists"],
            "walker_is_grafted": cw["walker_domain"] != 10,
            "contract_verdict": "FALSE" if cw["is_ancestor_rc"] != 0 else "TRUE",
            "ground_truth": "TRUE",
        }
        legC["fail_open"]["registry_authorises_wrong_answer"] = (
            legC["fail_open"]["fixed_probe_reports_clean"]
            and legC["fail_open"]["contract_verdict"] != legC["fail_open"]["ground_truth"]
        )
        out["legs"]["C_relocated_graft_file"] = legC

        # ---- Leg D: is the effective knob discoverable from git itself, or only from env? ----
        cfg = git(repo, "config", "--list", "--show-origin", env=cenv, check=False).stdout
        legD = {
            "config_list_mentions_graft_file": "graft" in cfg.lower(),
            "config_list_mentions_replace_base": "replace" in cfg.lower(),
            "git_var_l_mentions_knobs": None,
            "env_readable_by_evaluator": sorted(
                k for k in dict(ENV, **cenv) if k in ("GIT_GRAFT_FILE", "GIT_REPLACE_REF_BASE")),
        }
        v = git(repo, "var", "-l", env=cenv, check=False).stdout.lower()
        legD["git_var_l_mentions_knobs"] = ("graft" in v) or ("replace_ref_base" in v)
        out["legs"]["D_knob_discoverability"] = legD

        out["summary"] = {
            "replace_relocation_defeats_fixed_namespace_probe":
                out["legs"]["B_relocated_replace_base"]["fail_open"][
                    "registry_authorises_wrong_answer"],
            "grafts_relocation_defeats_fixed_path_probe":
                out["legs"]["C_relocated_graft_file"]["fail_open"][
                    "registry_authorises_wrong_answer"],
            "same_environment_query_recovers_replace":
                out["legs"]["B_relocated_replace_base"]["recovered_by_same_env_git_query"],
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    main()
