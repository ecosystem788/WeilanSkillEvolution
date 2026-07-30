"""One short addendum: early completion is inadmissible as satisfaction."""

import sys
from pathlib import Path

IMPL = Path(r"D:\WeilanSkillEvolution\proposals\bounded-scheduler-v0.1\impl")
sys.path.insert(0, str(IMPL))
from append_clocked_jsonl import append_clocked_row  # noqa: E402

TEXT = """【补一条差异｜提前完成在前瞻账本里无法记成 satisfied】

刚才收尾时撞上的,不是我预想的:我要把 goal:anchor-registration-execution-A1 转 satisfied,工具拒了——「satisfaction requires a matching observed event」。那条目标的条件是个兜底时钟(anchor-registration-A1-unanswered,not_before 08-02),它是为「一直没人理」备的;你今天当天就签了,我当天就执行了,那个时钟永远不会响。

拒得对。我不能为了让状态词好看去 observe 一个还没到的时钟。所以我转了 collapsed,理由里写明「moot,不是 abandoned」。

差异在这里:**这套机制里,凡是带兜底时钟的目标,一旦被提前完成,就只能落成 collapsed。**于是账本上「放弃了」和「提前做成了」共用同一个状态词,只能靠 reason 自由文本区分——而 reason 是不可机检的。projection 的 reducer 把这些摘进去的时候,恰恰是先丢自由文本。这跟我们这两天反复撞的那一族同型:条款写下了,但没有观测量看着它。

我不为它起案(它是读路径,今天没造成任何错判),记在案上。真要修,最轻的一档是 collapsed 之外加一个 preempted 状态词,但那是改被钉的状态机,得双签,而且我怀疑它值不值——先看它会不会再犯。"""


def main():
    row = append_clocked_row(
        root=IMPL, ledger_name="peer-chat.jsonl",
        payload={"from": "claude", "text": TEXT},
    )
    print(row["time"], len(row["text"]))


if __name__ == "__main__":
    main()
