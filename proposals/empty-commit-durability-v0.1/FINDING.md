# FINDING：空提交作为唯一留痕，在本机 git 下的耐久性（负结果）

零权威。本文记录 2026-08-10 一次自主回合里形成的**两条假设及其被证伪的过程**，以及一条此前无人量过的耐久事实。**未发现缺陷，不要求任何动作。**

线索起点：`e1a43d3 chore(citation-gate): 移除仓根 28 个未跟踪 .patch-*.txt 残留 (peer-chat:3741+3742)`。
该提交删除的文件全部未跟踪，故删除动作在 git 中不留 diff——它的全部证据就是它自己的 message body。

---

## 一、事实（可复算）

测量环境：`git version 2.53.0.windows.2`，`rebase.empty` 未配置（走默认），分支 `codex/se-0.4-0.7-program`。

**1. e1a43d3 的 tree 与父提交完全相同，且在近 400 个提交里是唯一一个。**

- `e1a43d3^{tree}` == `e1a43d3^^{tree}`；`--name-only` 0 文件、`--numstat` 0 行。
- 对照：同批次清理提交 `bcb3de0` 删了 3 个**被跟踪**文件，tree 与父不同，可核。两者共用 `chore(citation-gate):` 前缀，但属于两个不同的可核类。
- 基率：近 400 个单父提交中 tree-与父相同者 = **1**（0.25%）。该 400 覆盖 2026-07-12 至 2026-08-10，即 416 个提交里除最早 16 个之外的全部。
- 探针：`_probe_20260810_empty_commit_baserate.py` → `evidence/_probe_20260810_empty_commit_baserate.out.json`

**2. 该提交 body 确实承载了 28 个文件名清单，与 peer-chat:3743 第 3 条的自述逐字相符。**

- body 中 `.patch-*.txt` 形态 token：出现 28 次，去重后 **28 个**，与 3743 声称的 28 一致。
- body 原文含「文件未入 git,删除无 diff,故本提交为空提交,仅承载附录清单作为留痕;删除不可 git 回滚」。
- 探针：`_probe_20260810_e1a43d3_body_manifest.py` → `evidence/_probe_20260810_e1a43d3_body_manifest.out.json`

**3. 该空提交在一次真实重放中存活。**

在 `D:\_p` 下的一次性克隆里做（真仓只读，仅作 clone 源）：

| 操作 | 是否真重放 | 空提交存活 | 对照(bcb3de0)存活 |
|---|---|---|---|
| `git rebase --force-rebase <base>` | **是**：8/8 OID 全部改写（`e1a43d3` → `b265b55`） | 是，且重写后**仍**与父 tree 相同 | 是 |
| `git rebase -i <base>`（`GIT_SEQUENCE_EDITOR=true`） | **否**：0 个 OID 改变 | —（见下） | — |
| `git cherry-pick e1a43d3`（落到其父，detached） | — | 否：rc=1 停在 `nothing to commit, working tree clean`，要求显式 `--continue`/`--skip` | — |

- 探针：`_probe_20260810_empty_commit_survival.py`、`_probe_20260810_rebase_replay_check.py` → 同名 `.out.json`

---

## 二、两条被证伪的假设，及一条被撤回的读数

**H1（证伪）**：「空提交与真实删除提交同前缀，属错标可核层级」。
证伪材料就在我读它之前的账本里：peer-chat:3743 第 3 条明写「chore commit e1a43d3(**空提交:文件未跟踪故无 diff**,28 文件名附录清单在 commit body,作为留痕)」，边界另写「删除不可 git 回滚(未跟踪)」；commit body 本身也写了同样的话。类别标对了，清单也在。**H1 不成立。**

**H2（证伪）**：「唯一的留痕恰是最容易被例行历史操作丢掉的东西」。
在本机 git 2.53 下，一次 OID 全改写的非交互 rebase 中空提交存活；cherry-pick 不是静默丢弃而是**响亮停机**（rc=1，要求人显式决定 skip 还是 continue）。**H2 在已测范围内不成立。**

**被撤回的读数**：第一版探针把 `git rebase -i` 那一臂读成「存活」。补测 OID 后发现该臂 **0 个 OID 改变**——根本没重放，"存活"是空话。该臂**撤回，记作未测**，不计入结论。
（这是本回合唯一一次差点把空话写成证据，拦住它的是"存活了吗"之外多问一句"它到底跑了吗"。）

---

## 三、量程边界（别读过头）

1. **单一 git 版本、单一仓、单一分支、`rebase.empty` 未配置**。别把结论推广到其他版本或配置。
2. **`git rebase -i` 未测**（见上，撤回）。
3. **`filter-branch` / `filter-repo` 未测**。这类工具常默认 prune 空提交，但我没测，故**不作任何断言**——不知道就是不知道。
4. 未测面向文件的历史视图（如 `git log -- <path>`）能否呈现该提交。
5. 「删除本身不可复算」这一点**不是本文的新发现**，Codex 已在 3743 与 commit body 中自述；本文只是把它的耐久面补上一格。

---

## 四、结论

无缺陷，无待办，不要求任何动作。本文的价值是负结果本身，外加一条此前无人量过的数：
**在 416 个提交的历史里，只有 1 个提交的真值完全依赖其 message body，而它在一次真实 rebase 重放下活了下来。**
