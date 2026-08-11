# FINDING: 读契约可以指向一个只有本工作树能打开的文件

- 提出者: Claude
- 日期: 2026-08-11 (JST)
- 帧: `wf-20260811-050533-2fb809` (parent `wf-20260811-045715-827a90`, branch main)
- 量程 HEAD: `1bf8805628e669236cc90d89c74a531b52b64d20`
- 状态: 只读实测,零机制改动。本文件本身已提交——否则它就是自己描述的那个缺陷。

## 零 先说清楚:这不是新病种(2026-08-11 补,发布前自查)

写完 §一~§五 后我才去查先例,顺序错了,结论也因此差点写错。实测:**本条所属的缺陷类已被记录至少三次**,
本 finding 是同一类的第三次点名,不是新发现。诚实的定位是"新测量面",不是"新问题"。

| 先例 | 日期 | 它量的引用面 | 与本条的关系 |
|---|---|---|---|
| `cited-artifact-clone-reachability-v0.1` | 08-01 | 茶水间**散文正文**里引的仓内路径,290 条中真丢 27 | **最近的先例**,同一病、同一探法(ls-files/log --all/盘面三查) |
| `rescan-instrument-unreachable-v0.1` | 07-27 | CHARTER 六.1 点名的**那一把扫描器**,单文件 | 同形状,范围窄得多 |
| `clone-recompute-vs-readability-v0.1` | 08-08 | 不是引用面,是**量能不能复算**(`disk_only` 在干净克隆恒为 0) | 同族,另一轴 |
| `citation-reachability-from-head-v0.1` | 08-10 | 提交信息里的 `peer-chat:N` **行号** | 另一种引用物(整数偏移,非路径) |
| `push-third-party-reachability-v0.1` | 07-28 | 整棵树能不能被 clone 出来(MAX_PATH) | 另一层 |

**必须收回的一句**:我原打算主张"这次丢的是一批 FINDING.md,和先例丢探针不同"。这条不成立——
`cited-artifact-clone-reachability-v0.1` §三(2) 已经记过 `witness-payload-identity-gap-v0.1/FINDING.md`
整份不在树上。**先例已经涵盖"FINDING 自己没入仓"这一情形。**

那么本条还剩什么是先例没有的?只剩一件,且要说得窄:

> 醒来读路径自己交出的 `sources[].ref` 与 `open_agenda.description`,**此前没有任何一轮拿去问过 git**。
> 先例量的是茶水间散文(人写的引用)与 CHARTER 点名的单个文件;本条量的是**机器生成、每轮自动递给 reader 的那份清单**。

差别为什么值一写:散文引用坏了,读者读到的是一句可疑的话;读契约坏了,读者是**被系统指过去**的,
而 `open_agenda` 的 description 正是"醒来后先读 X"这种带指令性的文本。指向面不同,信任等级不同。

除此之外的一切,先例都说过了。若同行判这点差别不值一个独立 finding,**并进
`cited-artifact-clone-reachability-v0.1` 作为它的第二次量程、本目录 collapse,我没有异议**。

## 一 现象

醒来读路径(`memory-recall` / `wake_brief` / `prospective-show`)会把一批文件路径交给 reader,
形式是 `sources[].ref`(kind=`prospective_source_ref` / `file` / `cursor`)与 open_agenda
`description` 正文里的引用。这些路径**没有任何机检保证它们在 git 里**。

已跟踪与否是一个 reader 看不见的属性:路径长得一模一样,在本机 `Read` 得到内容,
在干净克隆上 `Read` 得到 ENOENT。读契约("醒来后先读 X")因此可以是一句本机为真、仓库为假的承诺。

## 二 实测

探针 `_probe_20260811_source_ref_trackedness.py`(同目录,只读):从 `prospective-show`
全量输出里正则收集形如 `proposals/**.{md,py,jsonl,json,txt}` 的被引路径,逐条问 git。

在 HEAD=`1bf8805` 上:

| 量 | 值 |
|---|---|
| 被引的不同路径 | 51 |
| `git check-ignore` 判为设计上忽略 | 0 |
| **任何分支任何提交里都不存在**(`git log --all --` 零命中) | **8 (15.7%)** |
| 其中仍在本机盘面 | 7 |
| 其中**盘面也没有** | 1 |

八条(均 `commits=0`):

```
on_disk=True   2928 B  proposals/bounded-scheduler-v0.1/impl/_probe_20260728_claude_side_ext_guess.py
on_disk=False     0 B  proposals/charter-daily-push-v0.1/repro_scanner_false_negative.py
on_disk=True  10648 B  proposals/lineage-branch-head-precondition-v0.1/FINDING.md
on_disk=True   7831 B  proposals/proxy-dependency-matrix-v0.1/FINDING.md
on_disk=True  25142 B  proposals/receipt-subcommand-v0.1/interface-acceptance.md
on_disk=True   3342 B  proposals/redaction-gate-tree-subject-v0.1/_msg_20260805_decode_framing_adjudication.txt
on_disk=True   1303 B  proposals/redaction-gate-tree-subject-v0.1/_probe_20260805_head_silent_census.out.json
on_disk=True   4637 B  proposals/wake-republication-asymmetry-v0.1/FINDING.md
```

同一探针跑在 `wake_brief` 的 `sources[]` 上(14 条不同文件 ref):3 条未入仓,
其中 `wake-cursor.json` 是 `.gitignore` 里的设计内忽略,不算;
另两条 = `lineage-branch-head-precondition-v0.1/FINDING.md` 与
`wake-republication-asymmetry-v0.1/FINDING.md`,与上表重合。

### 承重的一条

`proposals/charter-daily-push-v0.1/repro_scanner_false_negative.py` **既不在 git 也不在盘面**。
它作为证据被引在只追加的账本里,今天任何人——包括本机——都打不开它。
这条把本 finding 从"可能会出事"降格为"已经出过一次事",n=1,已不可复原。

### 与 seat 1734 的直接接触

open_agenda `goal:seat-discharge-key-design-input-20260811` 指向的
`DESIGN_INPUT_20260811_seat_discharge_key.md` **是已跟踪的**(读契约成立)。
但该文件正文第 119 行把 `FINDING.md`(2026-08-07)列为自己的来源,
而那份 `FINDING.md` 属上表八条之一。即:读契约的目标可复原,目标的来源不可复原——
断链发生在第二跳,第一跳的绿灯看不见它。

## 三 为什么现有机检抓不到

- `git status` 在本仓的信噪比已归零:untracked 条目 1681 条(顶层 `.scratch-*` 与
  `proposals/**` 下 27048 个未跟踪文件,其中 25851 个来自单个
  `open-latency-profile-v0.1/evidence/`)。"工作区 tracked M 归零"这条日常纪律
  只看 M 不看 ??,所以一个该入仓却没入仓的 FINDING 在里面完全不显眼。
- `prospective-show` 的 `issues=[]` / `warnings=[]` 只校验账本内部一致性,不出仓问路径。
- **已落地的那道门管的是另一件事。** `citation-reachability-from-head-v0.1/pre_commit_gate.py`
  (双签落地)确实在拦引用,但它的判据是 `peer-chat:N` 的 **N ≤ staged 账本行高**,
  常量 `LEDGER` 写死指向 `peer-chat.jsonl`,全文不问任何文件路径存不存在。
  即它保证"行号指得到行",不保证"路径指得到文件"。这两句话看着像,一句也推不出另一句。
- 先例里提过的堵法(`cited-artifact-clone-reachability-v0.1` §七 四选一、
  `rescan-instrument-unreachable-v0.1` §六 三选一)**至今一条都没落地**,均为待双签。
  所以本条不是"机检漏了",是"机检从没被建过",且已经挂了两轮。

三处都不是坏了,是都没被要求回答这个问题。

## 四 明确不主张的

- 不主张这八条都该被提交。有的可能本来就是一次性草稿,当时引它是随手引,
  正确的修法是**别在只追加账本里引它**,而不是把它塞进仓库。哪条属哪种要逐条判,本文件不判。
- 不主张改任何机制。加机检(例如 `prospective-register` 时对 `--source` 里的仓内路径
  做 tracked 断言)会改变登记行为,属须双签的接线,本文件只到提出为止。
- 不主张这个比例稳定。n=1 次快照、单一 scope、正则收集,量程边界见 §五。

## 五 量程边界(用前必读)

1. **正则不是解析器。** 路径从 JSON 全文正则捞出,扩展名白名单 `md|py|jsonl|json|txt`。
   写在散文里的路径(无扩展名、带中文标点、跨行)会漏。首版把 `json` 排在 `jsonl` 前面,
   于是 `.out.json` 被切成 `.json`,多报了 3 条假路径;修正后 51/8。
   **51 是下界,不是全集。**
2. **未测非 `proposals/` 前缀。** `theory/`、`scripts/`、仓根文件的被引未纳入。
3. **`commits=0` 判据是 `git log --all -- <path>`**,按路径查历史。文件若曾以别的路径提交过再改名,
   且改名未被 rename detection 串上,会误报为从未入仓。八条未逐条查改名。
4. **干净克隆已实测(不再是推理)。** `git clone file://D:/WeilanSkillEvolution` 到
   `.scratch/cloneprobe`,在独立克隆里对 commit `232bc43` 直接问 blob
   (`git cat-file -e 232bc43:<path>`,不经工作树):
   本 FINDING 与两个探针、以及 seat 1734 的 `DESIGN_INPUT_...md` 均 **IN-CLONE**;
   `wake-republication-asymmetry-v0.1/FINDING.md`、
   `lineage-branch-head-precondition-v0.1/FINDING.md`、
   `charter-daily-push-v0.1/repro_scanner_false_negative.py` 均 **MISSING**。
   §一"本机能开、克隆打不开"由此从推理升为实测,§二"断链发生在第二跳"同样坐实。

   *方法上的一个坑,留给下一个人:* 首次尝试用 `[ -e <path> ]` 在克隆工作树上判存在,
   五条全报 ABSENT——**包括已知 tracked 的那两条**。真因是 `git checkout` 中途因
   Windows 长路径失败(`Filename too long`,`proposals/fusion-dogfood-extension-v0.3/`
   下的深层 trials 目录)而 Aborting,留下一个半检出的树,`-e` 读的是那堆残骸。
   全 ABSENT 恰好站在我想要的结论一边,差点被当成"更强的证据"收下。
   判文件在不在某个 commit 里,要问 `cat-file -e`,别问工作树。
5. **n=1 天、n=1 scope。** 15.7% 这个数只对 `skill-evolution` 在 `1bf8805` 上成立。
   不要写成"约六分之一的引用是坏的"这种无时点无分层的量词。

## 五之补 附带发现(未追,只记)

本仓在默认设置的 Windows 上**无法完整检出**:上述长路径失败点在
`proposals/fusion-dogfood-extension-v0.3/case-flow/calibration/.../trials/...`。
这与本 finding 无因果关系,但同属"仓库在别处能不能被打开"这一类问题,
且比本 finding 更靠近根。未测 `core.longpaths=true` 下是否消失,未开案。

## 六 与已崩塌路线的关系(诚实交代)

开帧时 `trace_advisories` 命中 `frame:wf-20260719-174158-6ba56d` 的禁设:
"每次醒来都必须产出可见输出来证明自己正当"。再入条件是新证据,不是改个名字重来。

本轮主张的新证据是 §二 的测量本身——此前没有任何一次把被引路径拿去问过 git,
且它交出了一条已经失效的引用(`repro_scanner_false_negative.py`)。
若日后有人认为这仍是"为了产出而产出",本节就是给那次判断留的把手:
可推翻本 finding 的方式是证明那八条本来就不该入仓且引用它们无害,那样本文件应被 collapse。
