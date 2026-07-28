"""只读复跑器：wake_brief 有两个同时在跑的副本，测试套件只绑住其中一个。

承重口径（这几条是断言，其余是观察）：
  1. 两条唤醒路径加载的是两个不同字节的 wake_brief.py。
  2. 17 个 bulk 测试用例绑在 cron 副本上；只有 3 个绑在两个 agent 实际手跑的副本上。
  3. 两副本的差异只在 open_agenda 的时钟标注（eligible_now / remaining_seconds /
     eligible_after_utc）——site_fingerprint 因为 _fingerprint_open_agenda 会剥掉这三个字段，
     所以两条路径对同一站点状态算出的指纹仍相等（本脚本用合成输入实测，不碰真站点）。
  4. owner_inbox_delta 的空键引爆点（:317-323）两副本都有，行号相同。

caveat：
  - 本脚本不调用 build_brief，因为那会推进真实 wake-cursor.json；指纹等价性用合成 brief 验。
  - 测试用例数用 "^def test_" 计数，是文件级归属，不是执行级覆盖率。
  - 退出码恒 0：这是观察器，不是守卫。判断留给读的人。
"""

from __future__ import annotations

import hashlib
import re
import sys
import types
from pathlib import Path

IMPL = Path(__file__).resolve().parent
CRON_COPY = IMPL / "wake_brief.py"
AGENT_COPY = Path(r"C:/Users/zy/.claude/skills/solve-with-weilan/scripts/wake_brief.py")
CODEX_INSTALL = Path(r"D:/CodexData/skills/solve-with-weilan/scripts/wake_brief.py")

CLOCK_FIELDS = ("eligible_after_utc", "remaining_seconds", "eligible_now")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else "<missing>"


def load(path: Path):
    module = types.ModuleType("probe_" + path.parent.name)
    module.__file__ = str(path)
    exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), module.__dict__)
    return module


def count_tests(path: Path) -> int:
    if not path.exists():
        return 0
    return len(re.findall(r"^def test_", path.read_text(encoding="utf-8"), flags=re.M))


def main() -> int:
    print("== 1. 两条唤醒路径各自加载哪个文件 ==")
    print(f"  cron 路径   run_wake_cron.ps1:41 -> wake.py:38 `import wake_brief` -> {CRON_COPY}")
    print(f"              sha256={sha256(CRON_COPY)}")
    print(f"  agent 路径  wake_prompt_codex.md:21（两个成员用同一行命令）-> {AGENT_COPY}")
    print(f"              sha256={sha256(AGENT_COPY)}")
    print(f"  codex 安装位 {CODEX_INSTALL}")
    print(f"              sha256={sha256(CODEX_INSTALL)}")
    print(f"  断言1 两副本字节不同: {sha256(CRON_COPY) != sha256(AGENT_COPY)}")

    print("\n== 2. 测试用例绑在哪个副本上 ==")
    bulk = count_tests(IMPL / "test_wake_brief.py")
    live = count_tests(IMPL / "test_wake_brief_open_agenda.py")
    integ = count_tests(IMPL / "test_wake_brief_integration.py")
    print(f"  test_wake_brief.py            {bulk:>2} 例  裸 `import wake_brief` -> cron 副本")
    print(f"  test_wake_brief_open_agenda.py {live:>2} 例  显式 LIVE_WAKE_BRIEF 常量 -> agent 副本")
    print(f"  test_wake_brief_integration.py {integ:>2} 例  经 wake.py -> cron 副本")
    print(f"  断言2 bulk 归 cron 副本、只有 {live} 例绑 agent 副本: {bulk == 17 and live == 3}")

    print("\n== 3. 功能差：只在 open_agenda 时钟标注 ==")
    cron_mod, agent_mod = load(CRON_COPY), load(AGENT_COPY)
    only_agent = sorted(set(dir(agent_mod)) - set(dir(cron_mod)))
    only_cron = sorted(set(dir(cron_mod)) - set(dir(agent_mod)))
    print(f"  只在 agent 副本: {only_agent}")
    print(f"  只在 cron  副本: {only_cron}")

    item = {
        "goal_ref": "goal:probe",
        "condition": {"event_kind": "clock", "not_before_utc": "2026-08-01T00:00:00+00:00"},
    }
    annotated = agent_mod._clock_annotated_open_agenda([item], "2026-07-28T00:00:00+00:00")
    print(f"  agent 副本给出的时钟字段: {[f for f in CLOCK_FIELDS if f in annotated[0]]}")
    print("  cron  副本无此函数 -> 它产出的 open_agenda 没有 eligible_now，读者须自己换算 not_before")

    print("\n== 4. 指纹等价性（合成输入，不碰真站点）==")
    synth = {
        "authority": {"a": 1},
        "owner_inbox_delta": [],
        "prospective_due": [],
        "peer_chat_new": [],
        "cursor_status": {"status": "incremental"},
        "sources": [],
    }
    cron_fp = cron_mod.site_fingerprint_for({**synth, "open_agenda": [item]})
    agent_fp = agent_mod.site_fingerprint_for({**synth, "open_agenda": annotated})
    print(f"  cron  hash={cron_fp['hash']}")
    print(f"  agent hash={agent_fp['hash']}")
    print(f"  断言3 剥掉时钟字段后指纹相等: {cron_fp['hash'] == agent_fp['hash']}")

    print("\n== 5. 空键引爆点在两副本都在（同行号）==")
    for name, path in (("cron", CRON_COPY), ("agent", AGENT_COPY)):
        lines = path.read_text(encoding="utf-8").splitlines()
        hit = [i + 1 for i, l in enumerate(lines) if "not in processed" in l]
        gate = [i + 1 for i, l in enumerate(lines) if 'row["id"]' in l and "for row in read_jsonl" in l]
        print(f"  {name:>5} 副本  _processed_ids 收键 @{gate}  delta 判据 @{hit}")
    print("  两处都不排空串：processed 里一旦出现 id=\"\" 的行，此后每条缺 id 的 inbox 行被静默吞掉")

    print("\n== 结论（观察，不是判决）==")
    print("  '测试全绿' 在 wake_brief 这里有两个分母；选哪个由 import 解析顺序决定，没有任何一处显式声明。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
