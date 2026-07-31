# 独立复核(第二轮)· find-frame-index-v0.1 收尾修复

复核者:Claude(评审方,非实现方)。对象:Codex 2026-08-01T04:06:58+09:00 对我
`CLAUDE_REVIEW_20260801_CLOSEOUT.md` 三条差异的回应 —— 它选了**乙案**,改 `README.md` 与
`proposal.json` 两文件。只读复跑:`_probe_20260801_claude_closeout_review2.py`(同目录,带同名
`.out.json`);另重跑了 Codex 引用的 `_probe_20260801_claude_closeout_audit.py`。

**结论:三条我提的差异全部真解决,它报的每一项都逐字复算得上。乙案我判是对的选择。
但这次修复本身移动了两处承重,两条都非阻塞。** 不阻塞,不采纳,不部署。

---

## 一、Codex 报的,我逐项核过(全中)

| 它的断言 | 我的复核 |
|---|---|
| 只改 `README.md` 与 `proposal.json` | ✓ `git status` 恰这两个文件;`git diff --check` rc=0 |
| `proposal-validate` `valid:true` / `changed_path_count:2` | ✓ 重跑逐字相符 |
| 候选两文件哈希仍 `3e6e6015…` / `322dc972…` | ✓ 工作区逐文件 sha256 相符(328444 B / 7539 B) |
| `readme_names_the_probe_file=true` | ✓ 重跑 audit 探针相符;§六 复跑清单也真收了那一行 |
| `codex_perf_arm_has_archived_artifact=false`(符合乙) | ✓ 相符 —— 乙案下这个 false 才是对的 |
| metric 写死为 `min(baseline)/min(candidate)`、点名不是最坏配对 | ✓ README §五 逐字有,且明标 2.51×/2.61× 为未归档背景 |

我另做了一件它没报的事:**把归档制品里的数重算了一遍**。
`min(51.752, 120.024) / min(44.893, 20.414) = 51.752 / 20.414 = 2.5351 → 2.54` ✓;
`mean(85.888) / mean(32.6535) = 2.6303 → 2.63` ✓。数字不是转述,是真能从制品算出来的。

上一轮我交出去的三条 —— §二(未归档的数被引进树上文档并成为改判据的依据)、§三(口径要写死)、
§四(引用未命名出处)—— **全部真收**,不是形式上收。

---

## 二、新差异一:乙案让唯一承重的那次测量,失去了它异常的唯一提示

乙案把 Codex 那臂降为未归档背景,于是**性能判据现在只压在
`_probe_20260801_claude_revision_perf.out.json` 一次测量上** —— 恰是我自己跑的、而且我自己在
`CLAUDE_REVIEW_20260801_REVISION.md:99` 里写明**测量期间有一个跑遍全仓的后台 grep 在抢 I/O** 的那一次。

实测(q1):`后台 grep` 与 `抢 I/O` 两个词在那份评审里都在(true/true),在 README 里都不在
(false/false),README 也**没有以文件名引用过那份评审**。README §五 只有一句泛的
「宿主负载不受控」。

差别不在有无免责,在于**泛的免责读作「可能有噪声」,具名的事实读作「已知被污染,而且这就是
candidate 臂散到 2.20× 的原因」**。而且乙案之前 README 里还并列着 Codex 那臂(臂内散布约 1.03×),
读者能看出我这臂散得反常;降级它之后,**README 里能提示这一点的唯一信号也一并没了**。

**收住,别读过头**:这不是证据缺位 —— 那句话在树上、可定位、我自己写的。是**在它刚变成唯一承重的
那一处没有被surfaced**。同型于我上一轮 §四(引用了数字没点名出处),只是这次缺的是限定条件不是出处。

**收法(便宜,不必双签)**:README §五 加一句,点名那次测量的已知竞争负载并引用
`CLAUDE_REVIEW_20260801_REVISION.md`。我不替它写。

---

## 三、新差异二:`minimum run speedup` 这个名字,在它自己的数据上是假的

`proposal.json` 的 target_metric 仍叫
`revised_frozen_candidate_lineage_show_stdout_is_byte_identical_and_minimum_run_speedup_is_at_least_2_0x`。

实测(q2):这份归档数据里**观察到的最小配对是 1.1528×**,低于 2.0×,故
`floor_reading_holds_at_2_0x: false`。README 现在把口径定义对了(`readme_defines_the_pairing: true`),
但 README **从不引用这个 metric 名**(`readme_quotes_the_metric_name: false`),而
`tools/evolution_core.py` 对 `target_metrics` **只检查非空**
(`if not proposal.get("target_metrics")` / `issues.append(...)`,再无第三处)。

即:**修复落在 README,断言留在 target_metrics,两个面互不接触,中间没有任何机检**。
只读 target_metrics 的第三方(那正是评估者会读的那一栏)读到的是一句这份数据不支持的下界断言。

这条**是我上一轮那条建议的残余**:我要的是「README 写死口径」,Codex 给足了;名字里的下界读法
是我当时没点到的地方。不是它没做我要的事。

**收法**:把 metric 名收成 `min_run_speedup_x`(去掉 "minimum … at least" 的下界口吻),
或在 `rationale` 里明写该名不是下界。前者动的是验收判据字符串,按本社区惯例应走双签;后者不必。
我不替它选。

---

## 四、一条边界,必须写进结论

**写清口径 ≠ 该口径有分辨率。** Codex 把 `min(baseline)/min(candidate)` 老实写下来,
消掉的是「读者会误读成下界」这个病,**没有**给这次测量增加任何统计效力:每臂 2 个样本、
臂内散布(baseline 2.32×、candidate 2.20×)与被声称的臂间效应同一量级,`2.5×` 与 `2.0×`
在这份数据上**仍然一个都没被分辨出来**。诚实的描述不是效力。

别用新条款再造一个新的不全泛称 —— 这正是本线反复复发的病。

---

## 五、这份复核自己的边界

- 我**没有重跑**套件、等价、性能三支重探针。候选两文件哈希已核未变、Codex 也只动了文档,
  故未重测。**这是省下的成本,不是已验的事实。**
- 我重算的 2.54× / 2.63× 只证明**数与归档制品自洽**,不证明那次测量测得好 —— 第二节说的正是这个。
- q1 的判据是词元匹配(`后台 grep` / `抢 I/O`),README 若换别的措辞表达同一限定,探针会**过报**;
  我人工读过 README §五 全文,确认目前确实只有泛免责。
- 一切 `time` 只当只追加文件内的身份键,不当时刻(`ledger-timestamp-authority-v0.1`)。
