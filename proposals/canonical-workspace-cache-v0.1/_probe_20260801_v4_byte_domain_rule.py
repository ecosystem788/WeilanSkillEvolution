"""只读探针：为 V4（执行归档字节域处置）量四件事，全部由 git / 机检器自己回答，不手数。

一、复核 Codex 17:34:31 的死线：归档四件里哪些 raw worktree OID != filtered(staged) OID，
    以及 git check-attr 对每件给出的 text/eol 生效值（在真仓、真求值环境下问 git 要，不猜）。
二、量"把 -text 铺到整包"的代价：包内当前已被 HEAD 跟踪的文件里，有多少条 raw 磁盘字节
    != HEAD blob 字节——这些正是一旦改成 -text 就会由"干净"翻成"已修改"、且下次 add 会
    把已公开 blob 改写成 CRLF 的文件。这条决定 V4 该窄到什么程度。
三、端到端真测拟议规则：在 scratch 仓里按同一相对路径复刻 root/.gitattributes 与拟议的包内
    .gitattributes，把四件归档原样放进去，再问 git 一次 filtered vs --no-filters。
    这是"规则真能保住原字节"的实测，不是推断。
四、五件绑定里的行级形状：直接 import 受治理 checker 的 line_delta，喂 base=当前字节、
    final=拟议后像原始字节。

对本仓、两安装点、一切账本全只读；只写同名 .out.json 与 scratch 目录（C:/wl_v4）。
"""
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys

PKG_REL = "proposals/canonical-workspace-cache-v0.1"
ARCHIVE_REL = PKG_REL + "/execution-wf-20260801-075758-0b0905-v3-gitattributes"
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHECKER = os.path.join(REPO, "proposals", "cosign-bytewise-binding-v0.1", "verify_binding.py")
TARGET = os.path.join(REPO, PKG_REL, ".gitattributes")
SCRATCH = "C:/wl_v4"

PROPOSED_FINAL = b"*.bak -text\nexecution-wf-*/** -text\n"

ARCHIVE_FILES = [
    "postcheck-receipt.json",
    "preflight-state.json",
    "preflight-state.json.witness",
    "preflight-state.json.witness.post",
]


def git(args, cwd=REPO):
    p = subprocess.run(["git"] + args, cwd=cwd, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def sha(b):
    return hashlib.sha256(b).hexdigest()


def load_checker(path):
    spec = importlib.util.spec_from_file_location("verify_binding_probe_v4", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def oid_pair(repo, rel):
    """(raw oid, filtered oid) — filtered 用 --path 让 git 按该路径的生效属性过滤。"""
    rc1, raw, _ = git(["hash-object", "--no-filters", "--", rel], cwd=repo)
    rc2, filt, _ = git(["hash-object", "--path", rel, "--", os.path.join(repo, rel)], cwd=repo)
    return (raw.strip() if rc1 == 0 else None), (filt.strip() if rc2 == 0 else None)


def check_attr(repo, rel):
    rc, out, _ = git(["check-attr", "text", "eol", "--", rel], cwd=repo)
    vals = {}
    for line in out.splitlines():
        parts = line.rsplit(": ", 2)
        if len(parts) == 3:
            vals[parts[1]] = parts[2]
    return vals


def main():
    out = {"probe": "v4_byte_domain_rule", "read_only_on_repo": True}

    # ---- 一：归档四件的当前字节域 ----
    sec1 = []
    for name in ARCHIVE_FILES:
        rel = ARCHIVE_REL + "/" + name
        disk = os.path.join(REPO, rel)
        raw_oid, filt_oid = oid_pair(REPO, rel)
        body = open(disk, "rb").read()
        sec1.append({
            "path": rel,
            "size": len(body),
            "sha256_disk": sha(body),
            "crlf_count": body.count(b"\r\n"),
            "raw_oid": raw_oid,
            "filtered_oid": filt_oid,
            "raw_equals_filtered": raw_oid == filt_oid,
            "attrs_now": check_attr(REPO, rel),
        })
    out["archive_now"] = sec1
    out["archive_mismatch_count_now"] = sum(1 for r in sec1 if not r["raw_equals_filtered"])

    # ---- 二：整包铺 -text 的代价（已跟踪且 raw != HEAD blob 的条数） ----
    rc, tracked, _ = git(["ls-tree", "-r", "--name-only", "HEAD", "--", PKG_REL])
    tracked_paths = [p for p in tracked.splitlines() if p.strip()]
    flip = []
    for rel in tracked_paths:
        disk = os.path.join(REPO, rel)
        if not os.path.exists(disk):
            continue
        rc2, head_oid, _ = git(["rev-parse", "HEAD:" + rel])
        raw_oid, _f = oid_pair(REPO, rel)
        if rc2 == 0 and raw_oid and head_oid.strip() != raw_oid:
            body = open(disk, "rb").read()
            flip.append({"path": rel, "head_blob_oid": head_oid.strip(),
                         "raw_worktree_oid": raw_oid,
                         "crlf_count": body.count(b"\r\n")})
    out["tracked_in_package"] = len(tracked_paths)
    out["would_flip_to_modified_under_pkg_wide_minus_text"] = len(flip)
    out["flip_examples"] = flip[:10]

    # ---- 三：scratch 仓端到端真测拟议规则 ----
    if os.path.isdir(SCRATCH):
        shutil.rmtree(SCRATCH, ignore_errors=True)
    os.makedirs(SCRATCH)
    git(["init", "-q"], cwd=SCRATCH)
    shutil.copyfile(os.path.join(REPO, ".gitattributes"), os.path.join(SCRATCH, ".gitattributes"))
    pkg_dir = os.path.join(SCRATCH, PKG_REL.replace("/", os.sep))
    arch_dir = os.path.join(SCRATCH, ARCHIVE_REL.replace("/", os.sep))
    os.makedirs(arch_dir)
    with open(os.path.join(pkg_dir, ".gitattributes"), "wb") as fh:
        fh.write(PROPOSED_FINAL)
    sec3 = []
    for name in ARCHIVE_FILES:
        src = os.path.join(REPO, ARCHIVE_REL.replace("/", os.sep), name)
        shutil.copyfile(src, os.path.join(arch_dir, name))
        rel = ARCHIVE_REL + "/" + name
        raw_oid, filt_oid = oid_pair(SCRATCH, rel)
        sec3.append({
            "path": rel,
            "raw_oid": raw_oid,
            "filtered_oid": filt_oid,
            "raw_equals_filtered": raw_oid == filt_oid,
            "attrs_under_proposed_rule": check_attr(SCRATCH, rel),
            "sha256_copy_equals_source": sha(open(os.path.join(arch_dir, name), "rb").read())
                                         == sha(open(src, "rb").read()),
        })
    out["archive_under_proposed_rule"] = sec3
    out["archive_mismatch_count_under_rule"] = sum(1 for r in sec3 if not r["raw_equals_filtered"])
    # 对照臂：同一 scratch 仓、只有 V3 现行规则时，四件是什么样
    with open(os.path.join(pkg_dir, ".gitattributes"), "wb") as fh:
        fh.write(b"*.bak -text\n")
    ctrl = []
    for name in ARCHIVE_FILES:
        rel = ARCHIVE_REL + "/" + name
        raw_oid, filt_oid = oid_pair(SCRATCH, rel)
        ctrl.append({"path": rel, "raw_equals_filtered": raw_oid == filt_oid})
    out["archive_under_v3_rule_control"] = ctrl
    out["archive_mismatch_count_control"] = sum(1 for r in ctrl if not r["raw_equals_filtered"])
    # 复位 scratch 到拟议规则，免得留下误导现场
    with open(os.path.join(pkg_dir, ".gitattributes"), "wb") as fh:
        fh.write(PROPOSED_FINAL)

    # ---- 三之二：范围收敛真测（拟议规则只碰 execution-wf-*/ 下的路径） ----
    probe_paths = [
        PKG_REL + "/README.md",
        PKG_REL + "/SHADOW_RESULT.json",
        PKG_REL + "/.gitattributes",
        PKG_REL + "/proposal.json",
        PKG_REL + "/candidate/scripts/runtime_core.py",
        PKG_REL + "/artifacts/x/y.json",
        PKG_REL + "/scripts/weilan_trace.py.pre-concurrent-clock-v01.9adab069.bak",
        "proposals/other-package/whatever.json",
        ARCHIVE_REL + "/anything_future.json",
    ]
    conf = []
    for rel in probe_paths:
        with open(os.path.join(pkg_dir, ".gitattributes"), "wb") as fh:
            fh.write(b"*.bak -text\n")
        before = check_attr(SCRATCH, rel)
        with open(os.path.join(pkg_dir, ".gitattributes"), "wb") as fh:
            fh.write(PROPOSED_FINAL)
        after = check_attr(SCRATCH, rel)
        conf.append({"path": rel, "attrs_under_v3": before, "attrs_under_v4": after,
                     "changed": before != after})
    out["confinement"] = conf
    out["confinement_changed_paths"] = [c["path"] for c in conf if c["changed"]]

    # ---- 四：五件绑定 ----
    mod = load_checker(CHECKER)
    base_raw = open(TARGET, "rb").read() if os.path.exists(TARGET) else None
    shape = mod.line_delta(base_raw, PROPOSED_FINAL)
    out["binding"] = {
        "checker_path": os.path.relpath(CHECKER, REPO).replace("\\", "/"),
        "checker_sha256": sha(open(CHECKER, "rb").read()),
        "target_path": PKG_REL + "/.gitattributes",
        "target_exists": base_raw is not None,
        "base_sha256": None if base_raw is None else sha(base_raw),
        "base_len": None if base_raw is None else len(base_raw),
        "final_sha256": sha(PROPOSED_FINAL),
        "final_len": len(PROPOSED_FINAL),
        "final_hex": PROPOSED_FINAL.hex(),
        "final_repr": repr(PROPOSED_FINAL.decode("utf-8")),
        "final_has_bom": PROPOSED_FINAL.startswith(b"\xef\xbb\xbf"),
        "final_has_cr": b"\r" in PROPOSED_FINAL,
        "expected_added": shape["added_lines"],
        "expected_deleted": shape["deleted_lines"],
        "attribution_ambiguous": shape["attribution_ambiguous"],
        "possibly_added_lines": shape["possibly_added_lines"],
        "possibly_deleted_lines": shape["possibly_deleted_lines"],
        "line_delta_full": {k: v for k, v in shape.items()},
    }

    rc, head, _ = git(["rev-parse", "HEAD"])
    out["source_head"] = head.strip()
    out["python"] = sys.version.split()[0]

    dest = os.path.splitext(os.path.abspath(__file__))[0] + ".out.json"
    with open(dest, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
