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
