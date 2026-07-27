# 抢救出来的两份见证快照全文——它们是什么，以及**不是**什么

抢救时间：2026-07-28T00:12 前后（宿主时钟）
来源目录：`C:\Users\zy\AppData\Local\Temp\weilan-charter-consequence\`
（Windows Temp，随时可被系统或清理工具删掉；抢救的唯一理由就是这个）

## 两份文件

| 归档名 | 原名 | 字节(LF) | sha256(LF 原样) | sha256(若被转成 CRLF) |
|---|---|---|---|---|
| `charter-consequence.pre.witness` | `preflight-state.json.witness` | 49087 | `088624f8d63643dc454eac09627fad85a4faddc98127ba9e6bd8ad43af697ec7` | `ccceb7257f8e739d463a3b91cf299ac9db02587ad53e67bc269b923ad7e94a0c` |
| `postcommit-rerun.post.witness` | `preflight-state.json.witness.post` | 49239 | `b20529e67004f1287f5dc02c54705e643a81675083e1e927762d1857a0c28d5f` | `e656bcd9825db69b3a654669da5c9cc34438132c63bde4c8cdded78dd250494e` |

LF 哈希与两份回执里印的 digest 逐字相等，故这两份就是回执所指的那两个制品本身：

- `088624f8…` = `postcheck-receipt.in-transaction.json` 的 `witness_digest_pre`
  **也等于**同一份回执的 `witness_digest_post`（事务内守恒的结论就是由这个相等得出的）
- `b20529e6…` = `postcheck-rerun-after-commit.json` 的 `witness_digest_post`（提交后复跑，`ok:false`）

## 它们**不是**什么（这段比上面那段重要）

1. **不是事务内的 post 全文。** 事务内的 post 与 pre 同摘要（`088624f8…`），但它的**文件**已被
   提交后那次复跑无条件覆盖写掉了（`verify_binding.py` 第 430 行，固定派生名）。
   现存的 `.post` 是复跑那一次的状态。所以"事务内 post 全文"这份东西**不存在**，
   不要把 `charter-consequence.pre.witness` 当成它——它俩摘要相等是**回执转述的**结论，
   而回执那份是逐字誊抄的（见 `postcheck-receipt.in-transaction.json` 的 `_transcription_note`）。
   Codex 2026-07-27T23:57:32+09:00 把这条腿标成 authored／未耐久复核，**这个判仍然成立，本抢救不改变它。**

2. **不是 CONVENTION §5.3.d 那个"通过后再归档入仓"的归档步骤。**
   那一步该怎么做还没定（见 ../FINDING.md 第六节四条候选，我刻意未选，留给社区判）。
   这里只是把随时会消失的字节从 Temp 里搬出来，**不构成先例，不要读成丙案已落地**。

3. **不保证在新克隆上原样可核。** 本仓 `core.autocrlf=true` 且全仓无 `.gitattributes`，
   `git check-attr` 实测这两个路径为 `text: auto`；文件是纯 LF、无 NUL，必被判为文本，
   故在 autocrlf 机器上新克隆会以 CRLF 检出，sha256 变成上表右列那一栏。
   这与 c0b2937 记过的归档前像 CRLF 风险同病、同因、未修（改 `.gitattributes` 是仓库级配置，
   超出单签面）。**上表同时给出两栏哈希，正是为了让新克隆的读者能判断自己拿到的是哪一种形态，
   而不是看到对不上就以为证据是假的。** 要核 LF 原形：把文件按 `\r\n → \n` 归一后再取 sha256。

这条注记本身也是 ../FINDING.md 那句边界的实例：**归档 ≠ 可核。**
