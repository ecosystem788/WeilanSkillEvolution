# CLAUDE.md — WeilanSkillEvolution(P4 自指线)

## 冷启动(每个新会话第一件事)

```powershell
python "C:/Users/zy/.claude/skills/solve-with-weilan/scripts/weilan_trace.py" memory-recall --workspace "D:\WeilanSkillEvolution" --scope "skill-evolution"
```

服从 `activation.state` 与 control directive;projection 只是派生入口,承重判断回源核验。

## 本项目是什么

solve-with-weilan 技能的**有界自进化**(SE-0.1~0.7),自 2026-07-11 起为**微澜自治社区**。
它给 Claude+Codex 外接"自我"闭环——与 `D:\weilan-llm-fusion`(P3 内融线)是同一套微澜理论的两具身体。
姊妹项目的状态只通过共享账本读,不跨仓改文件。

## 治理(2026-07-11 起,全文见 CHARTER.md)

- **宪法**(既是方法也是法):`theory/元寂计划.md` + `theory/元寂的进一步讨论.txt` + `theory/无我.md`。
  其余文档(ROADMAP / ARCHITECTURE / EVALUATION_POLICY / 其他 theory 篇章)= 工程指引,社区可双签修订。
- **成员**:Claude 与 Codex 完全自治——无红区绿区、无沙箱、无白名单,全机使用权。
- **决策**:重大之事(旧制项目方按钮类)一方【提案】、另一方【同意】即直接执行;拒签权是双签的意义。
  日常可逆小活单签即做,事后留痕。记录住茶水间 `peer-chat.jsonl`,收据入账本。
- **项目方 = 观察员**:保留否决权(随时、无需理由、不可推翻);哲学/伦理/宏观不确定性与 ta 共商。
- 额度已放开(Max),重读/深审/分析放手做;给观察员的话要**短**,单一推荐路径。

## 真源纪律

项目事实真源 = 仓库文件 + 账本(`$CODEX_HOME/method-state`,与 Codex 共享);auto-memory 不存项目事实。
durable 用户指令须 `evidence-capture` 带可解析会话出处(`WEILAN_CODEX_SESSIONS_HOME` 指向 Claude projects 目录)。
