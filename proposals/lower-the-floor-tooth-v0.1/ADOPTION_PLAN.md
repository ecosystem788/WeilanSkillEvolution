# memory-note(降地板第一颗牙)—— 采纳 / 部署契约

**授权状态(2026-07-08):**
- **采纳:已授权**(项目方本轮明示"采纳")。
- **部署:未授权**(独立闸,需项目方另说"部署";CLAUDE.md "采纳与部署仍需独立明确授权")。

**标的:** 冻结候选 `proposals/lower-the-floor-tooth-v0.1/candidate/solve-with-weilan`,artifact hash `9b2130988817076de547dffe3627d31501d4f62e584a2d00daf979c8db36a3c9`,SPEC `FROZEN v0.1a`。

**角色:** Codex = 采纳的机械执行(走 evolution 平面);Claude = 事后审计;项目方 = 部署授权。

## 采纳阶段(现授权,Codex 执行)

```text
1. 走项目 evolution 平面做内容寻址采纳(tools/evolution_cli.py 一类),不手改 evals/manifest / ROADMAP 之外的授权文件路径。
2. 采纳 bundle 必须**同时含**:memory-note 命令 + 其 drift-guard 测试 test_memory_note.py。
   —— 命令与守卫捆绑采纳;只采命令不采测试 = 复制漂移无人看守,禁。
3. 采纳记录落在授权平面(内容寻址,可回滚)。
4. **不触碰部署件** D:\CodexData\skills\solve-with-weilan —— 那是"部署",不是"采纳"。
```

## 部署阶段(未授权,占位;需项目方另说"部署")

```text
D1. 把 memory-note 命令 + test_memory_note.py **一并**写入部署件 D:\CodexData\skills\solve-with-weilan。
D2. test_memory_note.py 进部署件的测试套件并在部署基座上跑绿(drift-guard 对部署件的 capture/promote 生效)。
D3. 部署基座若与 D:\CodexData 当前态有别,§2 门矩阵对部署基座再逐条核一遍(SPEC §8 ④)。
D4. 记录部署 + 回滚点。
```

## Claude 审计清单(采纳后我核)

```text
[ ] 采纳 artifact hash == 冻结候选 hash(9b2130…)
[ ] drift-guard 测试在采纳 bundle 内
[ ] 部署件 D:\CodexData 未被改动(部署闸仍关)
[ ] 采纳记录在授权平面、可回滚
```
