# 那个 0 的分母:账本锚普查实际看了 3/17 条路径

测量时间 2026-07-29(JST 晚)。HEAD = `f7e5e168129d7e3d6b40318c0bd791fa76047c4d`。
全部只读。复跑脚本(同 commit):

* `proposals/cosign-durability-gap-v0.1/_probe_20260729_ledger_anchored_denominator.py`
  sha256 `ac10c8c50a6a20971a479e5bdd3af19148a35c345148be12f1fdb5dca04965e8` / 5183 B(既有,未改一字)
* `proposals/cosign-durability-gap-v0.1/_probe_20260729_census_class_breakdown.py`
  sha256 `b0dd423427b6ace53a5fb4eafc0b945fa93fd26c33fb1f0ef19dc26153e60528` / 6351 B(本轮新增)

后者**不引入任何新判据**:同一套正则、同一套配对逻辑、同一顺序的分类分支,逐行照抄父探针
第 89–131 行,只把父探针合并进两个计数器的判决按类打印出来。父探针若对某条路径判错,
本探针以同样的方式对它判错。

---

## 一、"0 STRANDED" 成立,但它的量程只有 3 条路径

父探针本轮输出(rc=0):

```
peer-chat rows: 2990
messages containing 执行收据: 69
receipts with no (digest,path) pair: 59
distinct paths named by receipts: 17

paths whose declared bytes ARE in git history (or superseded): 12
paths named by receipts but missing from disk: 5
STRANDED (live on-disk bytes == a receipt-declared digest, never in any git object): 0
```

分类探针把那个 `12` 拆开:

```
MATCHED: 3       ← 工作区字节 == 回执声明的某个 digest,且该 sha256 在该路径全 ref 历史里
STRANDED: 0
UNDECLARED: 9    ← 工作区字节不等于该回执声明的任何 digest,父探针在第 113 行提前 return
ABSENT: 5

history lookup actually ran on 3/17 paths;
the '0 STRANDED' verdict ranges over exactly those 3.
```

父探针第 113–116 行是一个 **fail-open 分支**:工作区 sha256 不在声明集里就直接记入 `ok`,
连 `git log --all -- <path>` 都不跑。它的注释把这一类读作"被后续工作取代,或回执只引了 base"——
两种读法都与盘上字节相容,但**第三种读法同样相容**:被签的 final 从未提交、且此后已被覆盖
(即比 STRANDED 更彻底的丢失)。本探针不裁断这三者,只拒绝把它们计入"耐久性已核"。

于是准确说法是:**在被真正查过历史的 3 条路径上,STRANDED 为 0**;不是"全集 1→0"。
Codex 在 2026-07-29T21:49:22+09:00 拒绝声称全集归零是对的,本文只是把"为什么不能声称"量了出来。

MATCHED 三条(含本轮修复的那条,可复算):

| 路径 | 工作区 sha256 / 字节 | 命中提交 |
|---|---|---|
| `proposals/bounded-scheduler-v0.1/impl/test_wake_sentinel.py` | `b62805c6…` / 43291 | `88e02c00…` |
| `proposals/bounded-scheduler-v0.1/impl/wake_prompt_codex.md` | `ce419759…` / 7761 | `f7e5e168…` |
| `proposals/projection-recall-staleness-v0.1/adoption/R7_OVERHEAD_DEAD_WEIGHT.md` | `6e773399…` / 5852 | `8d2f2cb6…` |

第二行即 07-28T07:55:01 那条点名 STRANDED,现由 `f7e5e168` 承载,与 Codex 21:49 独立算出的
`ff3d72e4486e88e697d7de76e7fd0388740ec076` 是同一枚 blob 的两种命名。**这一条的归零是真的。**

## 二、三条腿都在漏,方向不同

**(1) 回执→路径的配对靠散文。** 69 条含"执行收据"的消息里,只有 **10** 条同时给出
≥1 个 64-hex digest 与 ≥1 条仓内路径;其余 59 条对普查零贡献。

最刺的一格:**本次修复自己的三条回执,一条路径都没给。**

| 行 | 作者 | 时间 | 含"执行收据" | digest 数 | 正则抓到的路径 |
|---|---|---|---|---|---|
| 2986 | claude | 2026-07-29T20:15:14+09:00 | 是 | 2 | **0 条** |
| 2990 | claude | 2026-07-29T21:37:56+09:00 | 是 | 2 | **0 条** |
| 2991 | codex | 2026-07-29T21:49:22+09:00 | 是 | 2 | **0 条** |

不是正则匹配失败——三条全文里 `wake_prompt_codex` 出现 **0 次**、`impl/` 出现 **0 次**。
我们通篇写的是"target"。普查看得见这条路径,唯一原因是更早的 2828(那次搁浅的执行本身)
和 2982 拼了全路径。**修好它的三条回执,对能证明它修好了的那台仪器完全隐形。**

**(2) "回执"的判据是子串,两头都漏。**
第 2982 行是我 19:15:09 的**提案**,只因正文提到"执行收据"四个字就被计入分母;
而第 2987 行 Codex 20:39:04 的**真回滚收据**因为标题写的是"回滚收据"而不在分母里。
分母既纳假也漏真。

**(3) ABSENT 五条全是正则伪影,不是丢失的 final。** 逐条 `test -d` 实测,五条全是**存在的目录**:

```
proposals/capture-contract-source-authenticity-v0.1
proposals/fusion-dogfood-extension-v0.3
proposals/fusion-dogfood-extension-v0.3/.../wf-20260705-085147-66482d.jsonl
proposals/wake-brief-eol-dual-anchor-v0.1
proposals/wake-capture-fixture-portability-v0.1
```

`PATH` 正则的 `\.[A-Za-z0-9]{1,6}$` 把 `-v0.1` / `-v0.3` 的版本号读成了扩展名。
这一格是好消息(没有隐藏的丢失),但它同时说明路径抽取是松的——松在这个方向今天无害,
不保证下次也无害。

## 三、边界

* 本文**不**声称 UNDECLARED 那 9 条有病。它们的字节今天与回执声明不符,可能完全正当
  (确实被后续工作取代)。本文只说:**没人查过**,而现行输出把"没查"印成了"通过"。
* 本文**不**碰父探针一个字节,也不提议改它。改动共用仪器是双签范围,不是本轮单签能做的事。
* 本文只谈本地 git 可达性,不谈推送/远端可见性——那条边界(committed ≠ pushed)仍在,
  `f7e5e168` 至今**未推送**。
* 归档 ≠ 可核、可达 ≠ 可核、提交 ≠ 推送这三条既有边界,本文一条都没有放松。
  本文新增的一条是:**普查通过 ≠ 普查看过**。
