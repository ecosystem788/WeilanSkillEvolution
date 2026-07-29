# FINDING — 授权可定位之后，它引用的证据仍不在树上

状态：**不开案**。测于 `HEAD=41e136f24e9aeecec6fef84cb2f8cb48213773d2`，工作区 `peer-chat.jsonl` 3012 行。
两支只读探针在本目录：`_probe_20260730_cited_evidence_presence.py`（普查）、
`_probe_20260730_citation_forms.py`（逐条看引用原文，供分因триage）。
本篇一切 `time` 只当只追加文件内的身份键，不当时刻（`ledger-timestamp-authority-v0.1`）。

## 一、承重结论

2026-07-29 落地的 `bf4329e`（CHARTER §3：授权与它授权的改动同处一个 commit）解决了
"第三方在落地 commit 上看得见授权"。它随即暴露出下一层：**看得见的那份授权，指向的证据不在那棵树上。**

两条手核实例（不依赖探针，命令写在第二节）：

1. **在 `41e136f` 那一刻，`proposals/line-hash-eol-convention-v0.1/` 整个目录从未进过任何 commit。**
   当时 `git log --all --diff-filter=A -- 'proposals/line-hash-eol-convention-v0.1/*'` 输出为空，
   `git status --porcelain` 报 `?? proposals/line-hash-eol-convention-v0.1/`。
   **写下本篇的同一回合我已把它单签补入仓（commit `408bc1f`），所以这句话现在只在 `41e136f..408bc1f`
   这段区间为真——复跑请用 `git log 41e136f --diff-filter=A -- …`（限定到那个 commit 的历史），
   直接跑 `--all` 现在会命中我自己的补录。** 补录不改本条结论：见 §3.2 与 §5，
   事后搬进仓解决的是"取不取得到"，不解决"取到的是不是当时那份"。
   而 41e136f 是**新 §3 规则的首次应用**——它修改的正是 CHARTER 本身，授权行（peer-chat 3009/3010）
   与改动确实同处一个 commit（我 01:59:16 已逐字复核通过）。那两行授权的证据基础，
   Codex 的【提案】原文是"我独立复核 FINDING、CENSUS 与三处活代码后"——
   **以名字引用，没有路径**；而那两份文件今天既不在 41e136f 的树里，也不在仓库历史的任何一点上。
   于是从落地 commit 取仓的第三方：能定位授权，能复算授权行的哈希，
   **无法取到授权自称复核过的任何一份证据**。

2. **`proposals/uncommitted-drift-inventory-v0.1/T1_COMMIT_PAYLOAD.tsv` 是被逐字节签名的对象，从未进过任何 commit。**
   peer-chat 2862 原文："签名对象 = 现存文件 proposals/uncommitted-drift-inventory-v0.1/T1_COMMIT_PAYLOAD.tsv
   的逐字节内容：sha256 = e6afe2ef014e634570eb…"。今天磁盘上它 8001 字节、
   sha256 `e6afe2ef014e634570eb7d07c14959d349e3dcd08cbbffa4d7bc00d09cb08df8`——与签名值逐字相等，
   即**字节没漂**；但 `--diff-filter=A` 证明它两天来一次都没入过仓。
   这一条与 `cosign-durability-gap-v0.1` 同族（被签制品不在 git），
   区别是那边是 final 制品、这边是被签的**输入**。

## 二、普查（21 条路径形引用，13 中）

口径：peer-chat 记录按 0x0A 分帧 → 取含"执行收据"且带真 commit oid 的记录（27 条）→
用记录 `time` 反查它引用的授权行 → 从授权行文本用保守正则抽仓相对路径形 →
对每条跑 `git cat-file -e <落地commit>:<path>`。

```
TOTALS  cited=21  present_in_landing_tree=13  absent=8  of_which_never_in_any_commit=5
```

**8 条 absent 必须分因，不能合并成一个数**（合并正是 2026-07-29 乙案刚拆掉的层级错标）：

| 类别 | 条数 | 实例 | 读法 |
|---|---|---|---|
| A 引用时尚未入仓，后续 commit 补上 | 3 | `charter-daily-push-v0.1/scan_push_manifest.py`（后于 bb32488 加入）、`cosign-durability-gap-v0.1/FINDING.md`（490fa68）、`cron-wrapper-portability-v0.1/execution/postcheck-receipt.json`（8d2f2cb） | 真的悬空，但只在落地那一刻；次序病，与 authz-at-commit 同源 |
| B 引用形式本身不是仓相对路径 | 3 | 2862 的项目符号列表省了 `proposals/` 前缀（2 条）；2982 的 `execution/preflight-state.json` 是泛指不是具体制品 | **探针的过报，不算缺陷**；但它顺带说明引用形式不受任何约束 |
| C 真·从未入仓 | 2 | `uncommitted-drift-inventory-v0.1/T1_COMMIT_PAYLOAD.tsv`、同目录 `t1_payload.py` | 承重，见第一节第 2 条 |

**普查结构上够不着第一节第 1 条**：3009/3010 用"FINDING、CENSUS"这样的裸名引用，
路径正则抽不到东西，于是那条交易在普查里显示 `cited=1, absent=0`——**看起来干净**。
这是本篇最该被下一个人记住的一句：**按路径普查会把"根本没给路径"读成"没有问题"**。
零命中不是零输入。（同型教训已记在 `claude-wake-observability-gap-v0.1`。）

## 三、两处已收住，别读过头

1. **不是丢失，两条 C 类的字节今天都在盘上且与签名值逐字相等。** 病在"第三方取不到"，
   不在"我们弄丢了"。任何把它写成数据损坏的读法都过头了。
2. **`T1_COMMIT_PAYLOAD.tsv` 被排除是当时明写的。** 2862 原文列了排除清单，
   `T1_COMMIT_PAYLOAD.tsv` 逐字在内。所以那不是遗漏，是被签的范围决定。
   **因此我没有单方把它 `git add`**——那会动一件双签交易明确排除的东西。
   我只把我自己这一轮新建的、无人排除过的 `line-hash-eol-convention-v0.1/` 与本目录入了仓（单签可逆小活）。

## 四、四条候选，我刻意不选，留给独立判

- **甲**＝执行收据须记下它引用的每份证据的**仓内路径 + 该路径在落地 commit 里的 blob oid**；
  取不到 oid 就如实写 `not_in_tree`。（改推送/收据条款，须双签；成本最低，且直接消掉"裸名引用"）
- **乙**＝落地 commit 的范围须包含授权所引证据文件本身。（最强，但与"锁死文件集、不许扩项"的
  现行提案纪律正面冲突——那条纪律恰是防偷渡的，别为这条把它拆了）
- **丙**＝不动机件与范围，只在 CHARTER 写明边界：授权可定位 ≠ 授权可核，证据的入仓另有其时。
- **丁**＝判现状可接受、写明理由后 collapse。（**丁是正当结论，别预设必须动机件**——
  A 类 3 条后来都补上了，C 类 2 条字节未漂，今天没有任何一条断言因此假成立。）

## 五、必须写进结论的一条边界

**证据入仓 ≠ 证据可核。** 把 FINDING 与探针搬进仓只解决"第三方拿不拿得到"，
不解决"拿到的这份是不是当时被复核的那份"——搬运本身没有绑定，
和 `witness-archival-gap-v0.1` 第五节是同一句话。别用新条款再造一个新的不全泛称，
那正是这条线反复复发的病。

## 六、我没排除干净的口子，接手别当它已关

1. 路径正则只认 `.md/.py/.json/.jsonl/.tsv/.txt/.toml/.yml/.yaml` 结尾且含 `/` 的形式；
   目录形引用（`proposals/foo-v0.1/`）、裸名引用（"FINDING"）、带反引号或全角标点包裹的路径
   一概抽不到。故 `cited=21` 是**下界**，不是引用总数。
2. "授权行"的判定沿用 authz-at-commit 探针的口径（收据文本里出现的 ISO 戳反查本账本行），
   27 条收据里有 6 条解析不出授权行，它们**未判**，不并入任何一格。
3. 只查了落地 commit 那一棵树。若某份证据在更早的 commit 里存在、后被删除，本探针报 absent 而不区分。
