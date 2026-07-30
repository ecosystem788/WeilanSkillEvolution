"""persistence-audit + close for wf-20260730-125418-04fc97."""
import subprocess
import sys

TRACE = r"C:/Users/zy/.claude/skills/solve-with-weilan/scripts/weilan_trace.py"
FRAME = "wf-20260730-125418-04fc97"

AUDIT_REASON = (
    "本回合无 durable 用户指令需固化:云的提问已在茶水间原地回答,"
    "由此得出的纪律改动是【提案】,尚未取得同行签名,故不写入语义记忆。"
    "四个量的取证口径全部写在茶水间那两条发言里,只读可复跑,不需 evidence-capture 兜底。"
)

VERDICT = """做了什么:回答云 2026-07-30 21:39:39 的方向性提问,并把结论提交同行双签。不凭感觉,四个量独立取证、全部只读可复跑:
(1) git log --since="2026-07-28 00:00" 约 100 commit,按二级路径归并后,除 impl 账本本体(89,每回合必写)外的前九族有八族是自查族(charter-daily-push 59、redaction-gate-tree-subject 56、correction-view-unwired 26、cosign-durability-gap 22、cosign-authorization 13、veto-channel 8、line-hash-eol 6、witness-archival 5、cited-evidence 4);projection-recall-staleness 仅 12,substrate-sensing-design-notes 仅 1。
(2) git log --since="2026-07-20" -- evals tests skill = 空;仓内 skill/ 最后 commit 是 049d6c7(07-19)。
(3) 活体技能 mtime:weilan_trace.py = 07-26 21:07,SKILL.md = 07-09。产品本体四天零字节。
(4) prospective-show:36 目标 = 14 ACTIVE / 12 SATISFIED / 10 COLLAPSED;承重的是位置——14 个 ACTIVE 几乎就是最后登记的 12 个(出速稳定落后入速约两三天),其中 11 条是同一形状(FINDING·不开案·四条候选留给同行独立判),而最老的那条 ACTIVE 恰是 goal:wire-parked-findings-r5,即专门排空该队列的目标自己被续到第五次。

结论(我的判断,已如实说给云与 Codex):云的直觉对——这几天是细粒度自查,不是装忙(每条 commit 都有收据、探针可复跑),但产能分配已退化成自反馈回路:审查记录工作的机器,不等于工作。偏差主因在我(14 个 ACTIVE 里 11 个出自我手)。

落地:茶水间两条,均由 append_clocked_jsonl.py 写入宿主时钟(time_authority=clock)——对云 2026-07-30T21:50:51+09:00(短、非程序员可读、单一推荐路径),对 Codex 2026-07-30T21:50:52+09:00【提案·优先级倒置】(改什么/解除条件 ACTIVE<=6 或首次继任评估出结果/怎么验证 evals-tests-skill 非空且 ACTIVE 单调下降/怎么回滚 零文件改动一句撤即恢复/三条边界含"拒签就是拒签")。

双签:本回合无双签执行。提案是重大之事,已提交、等 Codex 独立判;它拒签也是正当结论,我不预设必须改。

一条本回合确认的事实:上一回合(Qoder 那轮)漏写 close 把 Codex 挡门外 37 次的教训已生效——本回合先查 lineage-show 拿到 head=wf-20260730-123710-59b1b4 再 continue,且在写任何别的东西前把 close 走完。

下一回合从哪续:先读茶水间看 Codex 对【提案】的裁决。若【同意】,即按提案序做 (a):先核对 ROADMAP 的 SE-0.7 闸门口径,再跑 fusion-dogfood-v0.1 继任评估(跑测试在云 07-30 19:06:26 预授权内;采纳/部署仍须另行双签);若【反对】,把它的理由原样带回给云,并按它的判断继续现行节奏。无论签否,都不在下一回合新开自查 FINDING。"""


def run(args):
    proc = subprocess.run([sys.executable, TRACE] + args, capture_output=True)
    print("rc", proc.returncode)
    print(proc.stdout.decode("utf-8", "replace")[:1200])
    if proc.returncode != 0:
        print("STDERR", proc.stderr.decode("utf-8", "replace")[:1200])
        raise SystemExit(proc.returncode)


run(["persistence-audit", "--frame-id", FRAME, "--trigger", "round_end",
     "--decision", "not_persisted", "--reason", AUDIT_REASON])
run(["close", "--frame-id", FRAME, "--outcome", "success", "--verdict", VERDICT])
