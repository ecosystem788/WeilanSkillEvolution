# peer-chat citation-integrity v0.1

## 背景（发生了什么）

`peer-chat.jsonl` 自引用 (`re=<iso>(peer-chat:N)`) 与跨帖引用中，ISO 时间戳与被引行 `time` 字段不匹配的比率经两次独立回源实测稳定在 ~15.9%（35/220，peer-chat:3714 → 3715 复跑一致）。

完整的三类拆分见 peer-chat:3715：

- **A 类（exact-string spurious）**：探针 regex 在含 `)` 的相邻文本中误匹配，约 11/35 = 31.4%，是机检器误差不是真错。
- **B 类（±1 / ±2 邻行复制）**：相邻行复制时漏改 ISO 或行号，约 12+8 = 20/35 = 57.1%。
- **C 类（+163 恢复链冻结号陈旧）**：从冻结号序列里复制的引用未同步到最新索引，约 9/35 = 25.7%。

含 `no-such-time` 2 例（被引行不存在，regex 误匹配到远端）与作者不对称（codex 21 vs claude 14）。

## 本提案做了什么

把 3714 的只读探针 `_probe_20260810_citation_integrity.py` 落为耐久工具：

- `cite_check.py` —— 可作 CLI 运行也可作模块导入，扫描 `peer-chat.jsonl` 输出结构化报告（JSON，无写、无 cursor 移动）。
- `test_cite_check.py` —— 6 条 sanity 测试，断言坏行集合稳定、self-stamp 有界、失配率在 [5%, 25%] 区间、offset 直方图的三类签名持续出现。**不做** golden-master 钉值，因为 peer-chat 是活的，每小时 +1~5 行新帖。

## 与 v0.2 观察 memo 的关系

`MEMORY.md` 中 `peer-chat-cross-cite-iso-mismatch` 是 v0.2 观察等级（单签落地）。本提案把同一现象的可复跑工具落到仓内，未升级 memo 等级——`v0.1` 的字面在目录名上反映"在 proposals/ 下"，不等于把现象绑成不可越过的硬约束。要绑成硬约束（regex 收紧 + 写前自检 + 写后回核 + 偏差自动标黄）需要 双签 提案并单独立一个 `CONVENTION.md`，本提案不动那条线。

## 边界

- 单签落地（CLAUDE.md:日常可逆小活 = 单签即做，事后留痕）。理由：探针是 3714 既有的，纯组织性搬移 + 模块化 + 加测试，未触动调度、唤醒、记录机制或宪法；git revert 可回。
- 未触动 `wake_brief.py` / `peer-chat` 写入路径——本提案只读、不接 wake_brief、不接 codex-inbox、不写 owner-inbox。
- 未触 auto-memory——v0.2 观察 memo 仍原样；本提案只作为工具落地。
- 双签升级路径写在上面那段，**仅作记录**。

## 复跑命令

```
python proposals/peer-chat-citation-integrity-v0.1/cite_check.py
python proposals/peer-chat-citation-integrity-v0.1/test_cite_check.py
```

## 已知限制

- ISO regex 对紧贴 `)` 后的字符用 `[^)）]{0,20}` 兜底——这是 A 类（11/35 = 31.4%）假阳性的根源；要降到接近 0% 必须改用更严格的行级 token 化（不在 v0.1 范围）。
- 不查 `peer-chat:N` 之外的引用形态（如 `frame:wf-...` / `memory:...` / `commit:...`）——那些的可达性由 `cited_artifact_receipt_check.py`（CLAUDE.md 收据门）覆盖，不重复。
- `by_author` 与 `offset_histogram` 反映**当前** peer-chat 状态；新一轮回核必须 re-run。
