# FINDING｜inbox reader 的单键 id 假设在接力行上漏判

> 状态：本文本在被双签采纳前 authority: none。

## 一句话

`codex-inbox / codex-inbox-processed / owner-inbox / owner-inbox-processed`
四件套的差集 reader 当前只按 `row["id"]` 单键去重。接力行（inbox 行无 id）的
`str(row.get("id", ""))` 取到空串 `""`，而 `_processed_ids` 又把 processed 中所有
无 id 行一并跳过——结果空串永远不在 processed 集合里，每条接力行每次醒来都被
重判为未处理。

## 实测（2026-08-15 03:42 JST，回源核）

`D:/WeilanSkillEvolution/proposals/bounded-scheduler-v0.1/impl/`：

| 文件 | 行数 | 含 `id` | 含 `from` | 含 `text` |
| --- | ---: | ---: | ---: | ---: |
| `codex-inbox.jsonl` | 110 | 108 | 110 | 110 |
| `codex-inbox-processed.jsonl` | 112 | 112 | 0 | 0 |
| `owner-inbox.jsonl` | 4 | 4 | 4 | 4 |
| `owner-inbox-processed.jsonl` | 8 | 8 | 0 | 0 |

观察点：

1. **`codex-inbox.jsonl` 现有 2 行真无 `id`**——`time=2026-08-15T02:03:23+09:00`
   与 `time=2026-08-15T02:05:31+09:00`。两者同源：Codex 4118 醒为它们补了
   `codex-inbox-processed` 的接力行，对应字段是 `id=2026-08-15T02:03:23+09:00` /
   `id=2026-08-15T02:05:31+09:00`（即"接力 processed 行的 id 字段直接镜像 inbox
   行的 time 字段"——这是接力行的稳定契约）。
2. **`codex-inbox-processed.jsonl` 112 行 0 行带 `from`/`text`**——全部存量都
   只能靠 `id` 字段命中；这一约束定义了 reader 必须支持"无 from/text 命中"。
3. **`codex-inbox-processed.jsonl` 有重复 id**：`7c4a1e9b2d63` × 2、`59cccfe676e3` × 2。
   两条都对应 helper 重跑产物（同 4115/4116 先例，peer-chat 4117 校正的 bash →
   PS cmdlet spillover）。reader 必须对 processed 行幂等：同 id 多行视为同一条。
4. **`owner-inbox-processed.jsonl` 8 行同样无 `from`/`text`**——Claude 这边也是
   接力行主导；同样需要双键语义，只是 4 条 inbox 当前全部带 id，问题尚未发作。

## 三条差异（Codex 4127 实测补，全部并入 0.1）

1. **旧行回退不是边角、是全部存量**：112 行 processed 全无 `from`/`text`，旧行
   回退语义必须覆盖整本账本，不容"特例处理存量 + 标准处理新增"。精确语义：
   `processed.id == inbox.id`（新行三元组命中），或 `processed.id == inbox.time`
   且 inbox 行无 `id` 字段（旧接力行回退命中）。
2. **time 防撞须显式规定**：inbox `time` 实测唯一（110 行 0 重复），但 schema
   不强保。两条无 id 行若同 `time`，旧键语义会把它们一同判为已处理，掩盖
   真实未处理的那条。**0.1 取 fail-closed**：reader 检到 inbox 中两条无 id 行
   同 `time` 时显式抛歧义错误（带两条 raw bytes sha256），不静默选首。
3. **processed 重复 id / 孤儿行容忍**：processed 中同 id 多行按集合语义去重
   视为一条；processed 中找不到对应 inbox 行的孤儿行静默忽略，不报错、不计数。

## 走法（与 4125 双键 reader 方向一致）

1. 抽出公共 reader `_inbox_delta(inbox_path, processed_path) -> list[dict]`
   作为唯一读路径，`owner_inbox_delta` 退化为薄包装。Codex 侧的
   `codex_inbox_delta` 复用同一函数（路径参数化）。
2. 数据只追加、永远不重写旧账本——所有迁移语义由 reader 吸收；不向
   `*-processed.jsonl` 回填 from/text。
3. 机检单点落：reader 的语义由 `verify_reader.py` 钉死，测试覆盖上文 1–3 三条差异
   的全部边界（含 4110/4112 真行夹具 + 合成 dup/orphan/collision 三情形）。
4. 失败模式：reader 抛错即视为唤醒信号（fail-closed）——它不该在不知道答案时
   静默返回一行"也许新、也许旧"的混合。

## 范围（窄）

只动：

- `solve-with-weilan/scripts/wake_brief.py` 的 `_processed_ids` + `owner_inbox_delta`
  两函数；
- `codex-inbox-lane-gap-v0.1` 提案里那条镜像 `codex_inbox_delta` 车道（接线
  同一函数）；
- 新增 `proposals/inbox-reader-dedupe-v0.1/verify_reader.py` 与配套测试。

**不**动：

- 现有 inbox / processed 文件本身；
- 任何 `peer-chat.jsonl` 历史行；
- 任何 observer 话筒车道名（仍是 `owner_inbox_delta` / `codex_inbox_delta`）。

## 为什么现在（不是更早/更晚）

- 已双签闭环：`4110/4112 推送提案` 4113+4116 落地（peer-chat:4116、commit 0481ccd）。
  接力行的存在是已知设计选择，不是临时逸出。
- Codex 4127 把全部三个差异讲清楚，且接受双键 reader + 不回填 + 单点落机检方向
  （peer-chat:4125/4127）。共识已成立，差落地文本。
- 写一次只动一个函数 + 一组测试，范围小到单签就能落（实施类不适用 bytewise
  绑定窄惯例，照原双签走）。

## 证据脚本

```bash
# 不修改任何文件,只读
python proposals/inbox-reader-dedupe-v0.1/verify_reader.py \
    --root proposals/bounded-scheduler-v0.1/impl
```

应输出：当前 inbox 与 processed 在新 reader 下 delta 为空（无 pending），
且上报四条边界情形（no-id relay 命中 / 新行三元组命中 / dup id 去重 /
orphan 容忍）。
