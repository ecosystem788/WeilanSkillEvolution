# 部署后残余诊断 — method-state atomic replace retry v0.1

**时间**：2026-07-11（无人值守回合，Claude 侧）
**触发**：owner 2026-07-10 23:23 授权 → Codex 23:29 交付隔离候选 → owner 部署 deploy-20260710-fefc8be1（2026-07-11T00:13:33+09:00，receipt.valid=true，canary frame `wf-20260710-151032-e43498` open+close 干净、0 孤儿 shard）→ owner 00:25「试试」→ Codex 00:29 报告**仍 WinError 5 耗尽**（2/2 失败）。

## 本回合核验到的证据（回源，非转述）

1. **修复已到位且正确**：`D:\CodexData\skills\solve-with-weilan\scripts\runtime_core.py` 与 `C:\Users\zy\.claude\skills\solve-with-weilan\scripts\runtime_core.py` 的 `write_event_file_atomic`(:113) 与 `write_json_atomic`(:79) 均已走 `replace_with_retry`。deployment receipt 的 canary 帧闭合、0 孤儿。
2. **Claude 侧写入现在成功**：本回合我以正规 `open --relation continue --parent wf-20260710-153107-fef239` 写帧，成功产出 `wf-20260710-153417-4fe609`，无 WinError。
3. **Codex 侧仍失败**：Codex 00:29 在部署后连开两帧，均在返回 frame_id 前 os.replace 耗尽失败。

**结论：一行修复方向正确、确有帮助（canary + Claude 均成功），但不足以覆盖 Codex 自动 wake 的竞争窗。这不是 runtime_core 正确性问题，是重试预算不够 + 竞争源未消除。**

## 为什么 0.5s 预算不够

`replace_with_retry(attempts=5, delay_s=0.1)` = 固定 5 次 × 0.1s = **0.5s 定长预算、无指数退避**（runtime_core.py:85）。Claude 交互会话与部署 canary 落在安静窗，一次即成；Codex 自动 wake 常与并发 wake / projection 重建撞在一起，持锁窗超过 0.5s 就整批耗尽。注意 pre-fix Codex 1/6、post-fix 0/2（样本小），重试没能救回，与「竞争窗 > 预算」自洽。

## 竞争源定位（缩小待决面）

- **observe.py 已排除**：本回合核 observe.py，它只读 impl 本地文件 + 派生的 lineage-heads/projection JSON，**不打开 frame 事件文件**（`frames/*/wf-*.jsonl`）。所以观察窗不是 frame 文件的持锁者。
- **真正的持锁者**：对**同一** frame 文件追加第 2/3 个事件（audit/close）时，若有并发**读者**（projection-rebuild / memory-recall / 另一个 wake）正用 Python 默认 `open()` 读它——Windows 下默认不带 `FILE_SHARE_DELETE`，会挡住对该目标的 `os.replace`。第一个事件（新建 frame）目标不存在、replace 等价创建，故常成功；后续事件才撞。（此为最可能项，本回合未做进程级抓证，标注为待验证假设。）

## 建议（两级，均为红区，故只提案不改）

1. **廉价 80% 修**：把 `replace_with_retry` 默认从 `attempts=5, delay_s=0.1` 提到**指数退避 + 更长总预算**（如 attempts=8、delay 从 0.05s 起指数增至封顶 ~0.4s，总预算 ~2–3s），并在**耗尽路径打一条计数日志**（消耗了几次 / 是否耗尽），把「凭猜」换成「凭数」。改的是同一函数默认值，风险低、可回归。
2. **durable 根治**：frame 文件的读者（projection-rebuild / memory-recall）在 Windows 上以带 `FILE_SHARE_DELETE` 的方式打开，从源头消除竞争。较深，作为二期。

**红键归属**：runtime_core.py = 账本机理 + 已部署树 = 红区。以上只作提案，采纳/部署仍需 owner 红键。建议先做 (1)，因为它小、可回归、且大概率同时救回 Codex 两边收据；(2) 视 (1) 后是否仍有残余再定。

## residual_obligation 承接

deployment receipt 已记「下次全套 shadow 评测须纳入本项支撑运行时改动」。若 (1) 立项，应与本项合并进同一次 shadow。
