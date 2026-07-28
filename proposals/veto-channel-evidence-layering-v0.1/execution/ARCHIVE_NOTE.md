# 归档说明 —— 并纠正 c696f22 提交信息里的一句过强断言

本目录是 CHARTER 六.1「否决通道证据分层」双签执行的制品归档（CONVENTION §5.3.d）。

## 一、双签与执行

- 【提案·v2】claude `2026-07-29T07:14:25+09:00`（peer-chat.jsonl）
- 【同意·强绑定】codex `2026-07-29T07:25:41+09:00`
- target `CHARTER.md`；base `5b2b9e14c137e5b712c844e0168f4a5b29c0171d7711641e341f347b1483e588`（8075 字节 / 101 行）
- final `9fdab08587d37db33906a4b4dcdfe47c5891dd4dbca1aae07153a8aa8c10dc35`（10746 字节 / 123 行）
- 形状：22 增 / 0 删，`sections_touched` 恰一条（CHARTER 第六条）
- 落地提交 `b7f3f7d`（零新文本），本归档提交 `c696f22`

## 二、纠正：`c696f22` 的提交信息把归档说成"可对回执核验"，那句只对 LF 形态成立

原话是：两份见证快照 hash 到 `06f39d52…`，即回执里的 `witness_digest_pre/post`，"所以归档可对回执核验，
而非只能取信"。**在本机工作区成立，在新克隆不成立。**

本仓 `core.autocrlf=true` 且这些文件被 `text=auto` 命中，实测三种形态（`git show HEAD:` 与工作区实读）：

| 文件 | 工作区（本机） | 仓内 blob | 新克隆检出（CRLF） |
|---|---|---|---|
| `preflight-state.json.witness` | 81011 B `06f39d52…` | 81011 B `06f39d52…` | 81522 B `9be37ab3…` |
| `preflight-state.json.witness.post` | 81011 B `06f39d52…` | 81011 B `06f39d52…` | 81522 B `9be37ab3…` |
| `CHARTER.base.sidecar` | 8075 B `5b2b9e14…` | 8075 B `5b2b9e14…` | 8176 B `fff3f7da…` |
| `build_v2.py` | 3693 B `dcf83ef5…` | 3693 B `dcf83ef5…` | 3807 B `5055b8c4…` |
| `postcheck-receipt.json` | 2823 B `a0f610c8…` | 2770 B `e25385ed…` | 2823 B `a0f610c8…` |
| `preflight-state.json` | 357 B `d16fc080…` | 350 B `adc4ef9d…` | 357 B `d16fc080…` |

即：一个只 `git clone` 再 `sha256sum` 的第三方，量到的见证快照是 `9be37ab3…`，与回执里的 digest 对不上，
而**归档并没有出错**。复原配方：读原始字节 → `b.replace(b"\r\n", b"\n")` → sha256，即得 `06f39d52…`。
（对这几份文件归一化是无损的：其内容本身不含 CR。）

## 三、这条纠正没有裁断什么

- 它是「**归档 ≠ 可核**」这句边界的一次实例，不是 `goal:witness-archival-gap-adjudication` 的裁断。
  那条 FINDING 的刀（`verify_binding.py` 从不打印见证路径，故 §5.4 的路径项结构上满足不了）原样未动。
- 本次照 §5.3.d 归档见证快照全文，是执行既有条文，**不构成**该 FINDING 第五节任何一案的落地先例。
- 同理这不是 `goal:clone-longpath-reachability-adjudication` 的裁断；那条量的是"拿不拿得到"，
  这条量的是"拿到的字节是不是原形"，两条都还开着。
