# FINDING·不开案｜push 前脱敏门判的不是 push 会发布的那棵树

- 作者：Claude，2026-07-30 wake episode
- 器械：`proposals/scaffold-opensource-export-v0.1/scan_only_gate.py`(2026-07-14 立,peer-chat)
- 只读探针：`proposals/redaction-gate-tree-subject-v0.1/_probe_20260730_gate_tree_subject.py`
- 探针输出：`proposals/redaction-gate-tree-subject-v0.1/_probe_20260730_gate_tree_subject.out.json`
- 状态：不开案。四条候选处置我刻意不选,留给 Codex 独立判。

## 一、一句话

门的裁决不是"会发布什么"的函数。它 `os.walk()` 一个**文件系统目录**,而 push 发布的是一棵
**git 树**;今天这两个主体在同一份 pattern 表下给出 163 对 2 个命中,而多出来的 161 个
**一个都不会被发布**。

## 二、只读复跑口径

测于 `HEAD=225a0d09206836e1c53ca75639a00d36beadf4d1`;被判的 commit 取
`310e57546dd51742fc8f38c403c3df3fcdeb375f`(2026-07-30 日推实际推上去的 authorized head,
见 peer-chat `2026-07-30T06:57:05+09:00` 的 PUSH_RECEIPT)。

```
python proposals/redaction-gate-tree-subject-v0.1/_probe_20260730_gate_tree_subject.py \
    --commit 310e57546dd51742fc8f38c403c3df3fcdeb375f
```

探针与门共用同一份 pattern 表(`redaction-private-strings.local.txt`,3 条,untracked)、同一条
decode 规则(utf-8 → utf-16 → 放弃)、同一套 `SKIP_DIRS`。差别只有一处,就是被测主体:
门走文件系统,探针走 `git ls-tree -r` + `git cat-file --batch` 的**原始 blob 字节**。
探针不碰远端、不写任何账本、从不打印 pattern(只打 `pattern_index`),与门的披露纪律一致。

## 三、坐实的事实

| 主体 | 计数 | 命中 | 裁决 |
| --- | --- | --- | --- |
| git 树 @ `310e5754` | 3921 路径 | **2** | FAIL |
| 文件系统 @ `D:\WeilanSkillEvolution` | 36759 文件 | **163** | FAIL |

· git 树的 2 个命中,逐字就是 2026-07-30 06:38:05 我报给 @云 的那两处
  (`impl/codex-inbox.jsonl`、`impl/peer-chat.jsonl`,均 `pattern_index=0`、`where=content`)。
  **那份报告对已发布树是准确的**——本条不推翻它,是给它补一个它没说的边界。
· `filesystem_only = 161`,`git_tree_only = 0`。
· 161 个文件系统独有命中里,**在被判 commit 上被跟踪的有 0 个**(探针逐条 `git cat-file -e`
  实测,不靠推断)。它们全住在 `impl/wake-codex-runs/` 与 `impl/wake-agent-runs/` 的本地唤醒日志里。

结论的两半都要说清:**今天没有第三处泄露**(这是好消息,也是我原本怀疑的方向,查完是空的);
**同时**门的 FAIL 里 161/163 = 98.8% 与"会不会被发布"无关。

## 四、为什么这不是"多报一点无害"

**(1) 信噪比反转,不是噪声偏多。** 真·新增暴露到来时,它是 163 行 FAIL 清单里新增的 1 行。
把"每次 push 前门必须 PASS"当纪律,这条纪律今天**不可满足**,而且不可满足的原因与暴露无关;
人一旦习惯"FAIL 是常态,看一眼就过",门就退化成仪式。

**(2) 门读的是脏字节,不是会被推上去的字节。** 门 `open()` 工作区文件;push 发布的是
authorized oid 上的 blob。此刻 `git status` 有 **15 个** dirty 的被跟踪文件,`impl/peer-chat.jsonl`
就在其中。今天两个主体在这 3 条 pattern 上恰好同答,那是**偶合,不是结构保证**:
一条刚写进工作区、还没 commit 的私串会被门抓到(好),而一条已在 blob 里、却在工作区被改掉的
私串会被门**漏掉**(坏),后者正是"已提交但未推送"窗口里的真实形状。

**(3) 主体本身不稳定。** 本回合内文件系统计数从 36762 变成 36759,差额恰是我自己建了又删的
3 个临时文件。被判对象随本地草稿漂移;git 树由一个 oid 钉死。

**(4) 显而易见的便宜修法是错的:不能教门去读 `.gitignore`。** 两个亲兄弟目录,同样被 ignore,
发布状态相反——

```
.gitignore:11  proposals/bounded-scheduler-v0.1/impl/wake-codex-runs/   → 该 commit 上跟踪 0 个
.gitignore:18  proposals/bounded-scheduler-v0.1/impl/wake-agent-runs/   → 该 commit 上跟踪 1035 个
```

`wake-agent-runs/` 被 ignore **且** 有 1035 个文件被跟踪、已随日推公开(ignore 规则对既已
跟踪的路径不追溯)。所以"是否会被发布"这件事,**文件系统给不出、`.gitignore` 给不出**,
唯一权威是 authorized oid 上的那棵 git 树。这条否掉的是最容易被顺手采纳的那个补丁。

## 五、边界(别把本条读高)

· 本条**不**报告任何新的已发布泄露:git 树上就是那两处,与 07-30 的报告一致。
· 本条**不**是说门无用。门今天抓到的两处是真的,`--tree` 对"导出快照"这个原始用途是对的主体
  ——它 2026-07-14 立的时候面对的是 export 树,不是日推。病在**复用到 push 前**这一步。
· 探针扫原始 blob 字节。第三方 clone 落盘时会过 eol filter,字节可能与 blob 不同
  (见 `proposals/line-hash-eol-convention-v0.1/FINDING.md`)。对"发布出去的对象里有什么"
  这个问题,原始 blob 是对的主体;对"clone 出来的文件里有什么"则需另一次测量。本条不做那次。
· 3 条 pattern 是一份人工维护的私串表。门与探针都只证明"这 3 条不在/在",不证明"没有隐私泄露"。

## 六、四条候选处置(我刻意不选)

1. **换主体**:给门加 `--commit`,判 authorized oid 的 git 树;`--tree` 保留给 export 用途。
   最贴合病灶,但改的是 2026-07-14 立的共有器械,须双签。
2. **加锚集**:把今天已公开的 2 行冻成锚集,门此后区分"零新增暴露"与"干净"两态
   (与 `goal:classifier-source-duplication-and-closed-set-observability` 的 frozen-anchor 同形)。
   不动主体,只让裁决可用;但锚集本身需要一条"谁能往锚集里加"的规矩,否则它是消音器。
3. **两者都要**:主体换成 git 树 + 锚集,纪律才既可满足又有牙。代价是范围最大。
4. **什么都不改,只写下不得引用**:明确"门的 FAIL 不构成 push 阻断依据",把纪律留在人手上。
   诚实,但等于放弃 07-14 立门的意图。

我倾向 3,但**这是判断不是授权**——`goal:redaction-gate-discipline` 里那条"每次 push 前必须
在整棵可发布树上跑 scan_only_gate"的双签**尚未提出**,而本条恰好证明:那句话里的
"整棵可发布树"在今天的器械上**没有对应的主体**。所以那条提案不该照原话提。

## 七、与云那条待裁的关系

`goal:redaction-gate-discipline` 的第 (1) 项(两行已公开命中:留着不动 vs 重写公开历史)
仍在等云裁断,本条**不催、不代判**,也不依赖它:上面四条候选在两种裁断下都成立。
只补一条云可能用得上的事实——那两处就是全部,git 树上没有第三处。

## 八、2026-08-02 追加:门的输入契约没闭合(Codex 退回重提的四条,实测)

- 触发:Codex 于 peer-chat `2026-08-02T13:10:52+09:00` 【反对·退回重提】我 `13:01:03` 的
  「把推送前跑私串门写进 CHARTER 六.1」提案,承重理由是**输入契约未闭合**。本节不辩,只量。
- 只读探针:`_probe_20260802_gate_input_binding.py` / 输出 `.out.json`
- 口径:`commit=4384a5cf2069366c7f89e8b03ee6fb5bcf0d59d7`;fixture ruleset 用两个**必然命中路径的
  无害 token**(不是私串),写在临时目录,工作区一个字节不动;从不打印 pattern。

### 8.1 Codex 要的两条,给了,结论对门有利

| 问 | 实测 |
| --- | --- |
| (3) 真实 NEW_MATCHES(rc 2) 夹具 | **有**:`state=NEW_MATCHES`、`rc=2`、4652 blob 扫出 3120 处、全部 unanchored |
| (4) 跨工作区同输入同结果 | **是**:`--no-checkout` 新克隆里重跑,9 个可比字段**逐个相同** |

顺带一条好消息:ruleset 摘要只是**文件内容**的函数——同字节换个路径,摘要不变
(`path_changes_digest: false`)。所以"私档放哪儿"不是分歧源。

### 8.2 但 (4) 那个"是"要打折,而折扣正好坐实 Codex

第二个工作区读的 registry **就是第一个工作区那一份**——`DEFAULT_REGISTRY` 是写死的
`D:\...` 绝对路径(`scan_only_gate.py:27-29`),两次跑的 `stale_anchor_count=2` 相同是因为
**它们读的是同一个文件**,不是因为裁决可复现。故 8.1 那行只证明**扫描**与工作区无关,
**不证明裁决**与工作区无关。

### 8.3 新差异一:同一套私串,只是行序不同,就把整个 registry 打成陈旧

摘要取自 `"\n".join(patterns)`(`scan_only_gate.py:63-64`),是**有序**的:

```
ruleset_a          (set {A,B}, 序 A→B)  digest a76934...  occurrence_count 3120
ruleset_b_reordered(set {A,B}, 序 B→A)  digest 58890f...  occurrence_count 3120
```

命中集合逐字段相同,摘要不同。而门的裁决不变式(文件头 6-10 行)要求 anchor 的
`ruleset_digest` **精确相等**才算已锚定——于是两个签名者哪怕持有**完全相同的私串集合**,
只要文件行序不同,对方的全部 anchor 一律 stale、全部命中 unanchored、结果必然 NEW_MATCHES,
**永远到不了 KNOWN_PUBLIC_ONLY**。这就是 Codex 说的"两个签名者得到不同 ruleset_digest",
现在有数了,且成因比"字节不同"更细:**集合相同也不够,得字节相同**。

### 8.4 新差异二:被退回的提案要求的绑定,今天在 CLI 上根本写不出来

`--registry` **不是参数**——传了直接 argparse 报错退出:

```
scan_only_gate.py: error: unrecognized arguments: --registry ...   (rc 2)
```

所以"明确两位签名者使用的 registry 输入与摘要绑定"不是补一段 CHARTER 文本能做到的,
它得**先改机件**。

### 8.5 新差异三:收据里没有能定位分歧的字段

收据的全部顶层键只有 13 个,下面这些**一个都没有**:

```
private_strings_path  registry_path  registry_digest
registry_entry_count  repository     gate_version
```

被退回的提案要两位签名者"报六项"再比对——可一旦两人 `ruleset_digest` 不一致,收据里
**没有任何字段能告诉他们为什么**(行序?私档不同?registry 不同?)。比对因此只能产出
"不一致"三个字,不能产出可裁决的差异。这是比 Codex 原话更强的一条:不只是输入没锁定,
**输出也不足以事后归因**。

### 8.6 对重提顺序的结论(判断,不是授权)

我**接受退回**。并且实测把顺序也定了:**CHARTER 文本不能先行**。可核的最小前置是改机件——
(a) 加 `--registry` 并把 registry 摘要与条目数写进收据;(b) 把私档路径与其摘要写进收据;
(c) ruleset 身份要么改为**有序集合的规范化**摘要、要么在 CHARTER 里明写"行序即身份、
签名者必须共享同一份字节"。三条都是机件改动 ⇒ **须与 Codex 双签、实现委派 Codex**。
本回合不提这个提案,先把测量交出去让 Codex 独立复核。

### 8.7 同日晚追加:registry 与 ruleset 的身份语义**不对称**——所以"同输入"不能按字节算

Codex 于 `2026-08-02T13:28:52+09:00` 独立复跑 8.1–8.5,逐字复现。起草 (a)(b) 的最小机件提案时
冒出一个 8.3 没答的问题:**registry 是不是也像 ruleset 那样对行序敏感?** 若是,将来 CHARTER
可以把"同输入"键在 registry 原始字节上;若否,那样键就会造出假停机。去测了。

- 只读探针:`_probe_20260802_registry_order_sensitivity.py` / 输出 `.out.json`
  (import 门本体、喂**真** registry,不经 CLI——因为 8.4 已证 `--registry` today 传不进去)

| 排列 | arrangement 摘要 | anchor 集合摘要 | verdict |
| --- | --- | --- | --- |
| 原序 | `7c2ffc27…` | `86151a01…` | `KNOWN_PUBLIC_ONLY` / rc 3 |
| 逆序 | `0a7c3223…` | `86151a01…` | 同上,`classified` **逐字节相同** |
| 每条复制一份 | `ab0e68b3…` | `86151a01…` | 同上,`classified` **逐字节相同** |

三个字节摘要各不相同,anchor 集合摘要**只有一个**,三者 `classified_sha256` 同为 `5626d8db…`。
机制在 `scan_only_gate.py:325-334`:registry 被消费成两个按 identity 元组建的 **set**,
与顺序无关、与重复无关;而 ruleset 是有序 `join`(`:63-64`)。**同一个工具,两种输入,两种身份语义。**

⇒ 结论(判断):将来 CHARTER 的停机判据应当键在 **anchor 集合摘要**,不是 registry 原始字节摘要。
键在字节,会把两个持有完全相同 anchor 集合、只是行序不同的签名者判成"输入不一致"而停——
一个**可证明不可能改变任何裁决**的假停。字节摘要仍应写进收据,但它答的是"我读的是哪份文件"。

**两个折扣,自己先打:**

1. 真 registry 只有 **2 条**,逆序=两元素对调,样本小到不足以单独承重;承重的是 `:325-334`
   的 set 语义,实测只是与它一致、**没撞翻**它。
2. 这支探针**测不出** `stale_anchor_count` 的重复敏感性:它是 `:380-382` 对 entries 直接求和
   (带重复),而当前 `stale=0`,复制一份仍是 0。按构造 `stale_anchor_count` **是**重复敏感的、
   anchor 集合摘要不是 ⇒ 两人若 registry 有重复行会得到**相同 state 但不同 stale_anchor_count**。
   此条**按构造主张、未实测**。

据此起草的最小机件提案(只做 (a)(b),(c) 仍不动)发于 peer-chat `2026-08-02T13:38:31+09:00`,
待 Codex 独立评审;**签之前不改机件一个字节**。
