#!/usr/bin/env python3
"""host-substrate-awareness — 零权威探针 (demonstrator, NOT wired into any mechanism)

播种于 peer-chat 2026-07-23 16:58:12(claude)的具体化:把"感知帧扩到宿主衬底"
从散文变成一枚可检视的构造。要害不是"能读多少宿主信号",而是证明:一枚宿主事实
只要用同一套证据纪律读(带 source_ref、authority=none、除非被裁断不承重),它就只是
另一枚感知帧,不比 owner-inbox 那枚更内或更外——而风险对称地被"有界具名"锁住:
这里就三枚,不是接监控放洪水。

纪律:
  - 只读。不改任何文件、不改唤醒机制、不写账本。
  - 恰好三枚具名事实,每枚带取值命令当 source_ref。
  - authority=none:承重判断仍须回源核验,本探针的输出不自动授权任何行动。
  - 与 peer_health_wake 同规格的零权威旁路;若要真折进 wake_brief,那是改机制→须双签。

用法: python probe.py [--workspace D:\\WeilanSkillEvolution]
"""
import argparse
import json
import os
import shutil
import stat
import subprocess
import sys


def _git_porcelain(workspace):
    cmd = ["git", "-C", workspace, "status", "--porcelain"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        # fail-closed:git 非零退出(非仓库/路径不存在)时,空 stdout 不是"干净",
        # 是"没读到"。绝不把未读伪装成 clean。(Codex 2026-07-23 19:53 承重裁断)
        if out.returncode != 0:
            return {
                "name": "working_tree_clean",
                "value": None,
                "detail": {
                    "error": "git status returned non-zero; tree state unread",
                    "returncode": out.returncode,
                    "stderr": out.stderr.strip(),
                },
                "source_ref": " ".join(cmd),
                "authority": "none",
            }
        dirty_lines = [ln for ln in out.stdout.splitlines() if ln.strip()]
        return {
            "name": "working_tree_clean",
            "value": len(dirty_lines) == 0,
            "detail": {"dirty_entry_count": len(dirty_lines)},
            "source_ref": " ".join(cmd),
            "authority": "none",
        }
    except Exception as exc:  # noqa: BLE001 — 探针宁可如实报失败也不假装读到
        return {
            "name": "working_tree_clean",
            "value": None,
            "detail": {"error": repr(exc)},
            "source_ref": " ".join(cmd),
            "authority": "none",
        }


def _disk_free(workspace):
    drive = os.path.splitdrive(os.path.abspath(workspace))[0] + os.sep
    try:
        usage = shutil.disk_usage(drive)
        return {
            "name": "workspace_disk_free_gb",
            "value": round(usage.free / (1024 ** 3), 2),
            "detail": {"drive": drive, "total_gb": round(usage.total / (1024 ** 3), 2)},
            "source_ref": f"shutil.disk_usage({drive!r}).free",
            "authority": "none",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "name": "workspace_disk_free_gb",
            "value": None,
            "detail": {"error": repr(exc), "drive": drive},
            "source_ref": f"shutil.disk_usage({drive!r}).free",
            "authority": "none",
        }


def _shared_ledger_reachable():
    codex_home = os.environ.get("CODEX_HOME", "")
    ledger = os.path.join(codex_home, "method-state") if codex_home else ""
    if not ledger:
        # CODEX_HOME 未配置:无从判定的地址,不是"确认不可达"。诚实记 None。
        return {
            "name": "shared_ledger_reachable",
            "value": None,
            "detail": {"path": ledger, "codex_home_set": False,
                       "error": "CODEX_HOME unset; no ledger path to check"},
            "source_ref": "os.stat($CODEX_HOME/method-state)",
            "authority": "none",
        }
    # 同 Codex 2026-07-23 19:53 承重裁断的推广:os.path.isdir 会吞掉 permission/
    # transient/网络不可达的 OSError 折成 False,把"没读到"伪装成"不可达"。用 os.stat
    # 显式区分:确认不存在=诚实的 False;读取本身失败=fail-closed 的 None。
    try:
        st = os.stat(ledger)
    except FileNotFoundError:
        return {
            "name": "shared_ledger_reachable",
            "value": False,
            "detail": {"path": ledger, "codex_home_set": True, "exists": False},
            "source_ref": "os.stat($CODEX_HOME/method-state)",
            "authority": "none",
        }
    except OSError as exc:  # noqa: BLE001 — permission/网络/瞬时:没读到,绝不折成不可达
        return {
            "name": "shared_ledger_reachable",
            "value": None,
            "detail": {"path": ledger, "codex_home_set": True, "error": repr(exc)},
            "source_ref": "os.stat($CODEX_HOME/method-state)",
            "authority": "none",
        }
    is_dir = stat.S_ISDIR(st.st_mode)
    return {
        "name": "shared_ledger_reachable",
        "value": is_dir,
        "detail": {"path": ledger, "codex_home_set": True, "exists": True,
                   "is_dir": is_dir},
        "source_ref": "os.stat($CODEX_HOME/method-state)",
        "authority": "none",
    }


# 可取值的具名宿主事实登记表。登记 ≠ 采集:一枚事实只在被当回合某个具名判断问题
# 显式声明时才取值(Codex 2026-07-23 19:45 承重差异:固定面板会把"可感知"悄悄变成
# "应持续感知";更小的契约是"一问一集、问结集退")。扩衬底=往登记表加具名帧,而不是
# 让谁常驻被读。
_FACT_REGISTRY = {
    "working_tree_clean": lambda workspace: _git_porcelain(workspace),
    "workspace_disk_free_gb": lambda workspace: _disk_free(workspace),
    "shared_ledger_reachable": lambda workspace: _shared_ledger_reachable(),
}


def collect(workspace, demand=None):
    """按需采集:demand 是当回合一个具名判断问题对有界事实集的声明。

    demand = {"question": <具名判断问题>, "facts": [<事实名>...], "retires_when": <失效条件>}
    无 demand(或 facts 为空)= 无消费问题 = 不采(facts:[]);这是"没有当前判断
    消费者就不采"的字面兑现,防旁路日后长成无界监控。
    未登记的事实名 fail-closed 记为 unavailable,绝不静默丢弃。
    """
    question = (demand or {}).get("question") if demand else None
    requested = list((demand or {}).get("facts") or []) if demand else []
    retires_when = (demand or {}).get("retires_when") if demand else None

    facts = []
    for name in requested:
        collector = _FACT_REGISTRY.get(name)
        if collector is None:
            facts.append({
                "name": name,
                "value": None,
                "detail": {"error": "fact not in registry; unread (fail-closed)"},
                "source_ref": "(unregistered)",
                "authority": "none",
            })
        else:
            facts.append(collector(workspace))

    return {
        "probe": "host-substrate-awareness-v0.1",
        "bounded": True,
        "demand_scoped": True,
        "declared_by": question,
        "demanded_facts": requested,
        "retires_when": retires_when,
        "count": len(facts),
        "authority": "none",
        "wired_into_any_mechanism": False,
        "registry": sorted(_FACT_REGISTRY.keys()),
        "note": (
            "零权威 demonstrator;一问一集、问结集退:无具名消费问题则不采。"
            "承重判断回源核验;真接线须双签(改机制)。"
        ),
        "facts": facts,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", default=r"D:\WeilanSkillEvolution")
    ap.add_argument(
        "--question",
        default=None,
        help="当回合声明此事实集的具名判断问题;缺省=无消费问题=不采",
    )
    ap.add_argument(
        "--facts",
        default="",
        help="逗号分隔的事实名(须在登记表内);缺省=空=不采",
    )
    ap.add_argument(
        "--retires-when",
        default=None,
        help="该事实集的失效条件(问结即退),写给未来核验者",
    )
    args = ap.parse_args()
    demand = None
    requested = [f.strip() for f in args.facts.split(",") if f.strip()]
    if args.question or requested:
        demand = {
            "question": args.question,
            "facts": requested,
            "retires_when": args.retires_when,
        }
    print(json.dumps(collect(args.workspace, demand), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sys.exit(main())
