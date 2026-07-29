# 证据：durability closure 的四态可以全真，而下一次普通提交把 target 还原成签名前字节

**作者**：Claude，2026-07-29（本机时区 UTC+9），为评审
`PROPOSAL-POSTCHECK-DURABILITY-CLOSURE.md`（sha256 `bc4daf15a590e567d5334a405fd4a1d42316caf58a3bf7ef0e9cc6d2884a1970`）而做。
**权威**：零。这是一次实测，不是条款。复跑脚本 `_probe_20260729_closure_index_state.py`，
对本仓只读（全部动作发生在 `tempfile.mkdtemp()` 建的临时仓，跑完删除）。

## 一、探针问的问题

提案第三节第 4 条明确允许两种实现（"porcelain 或临时 index/plumbing"），并写"命令偏好不写进法"。
第四节夹具 1 只钉住"**其他** index/worktree 状态逐项不变"。于是有一个空位没人管：
**target 自己在真实 index 里的条目**，在 closure 之后是什么。

## 二、实测（2026-07-29 复跑输出，逐字）

按临时 index/plumbing 实现走一次 closure：`read-tree HEAD` → `hash-object -w target` →
`update-index --cacheinfo` → `write-tree` → `commit-tree -p HEAD` → `update-ref` CAS。同时按夹具 1
的要求制造 unrelated staged / unstaged / untracked 漂移。

```json
{
  "four_states_all_pass": {
    "signed_raw_present": true,
    "local_ref_reachable": true,
    "git_blob_equals_signed_raw": true,
    "remote_visibility": "not_in_scope"
  },
  "closure_commit_path_delta": ["target.txt"],
  "real_index_after_closure": {
    "status_porcelain": ["MM target.txt", "M  unrelated.txt", "?? untracked.txt"],
    "diff_cached_name_status": ["M\ttarget.txt", "M\tunrelated.txt"]
  },
  "hazard": {
    "next_plain_commit_target_bytes": "base bytes\n",
    "equals_signed_final": false,
    "equals_pre_signature_base": true
  }
}
```

## 三、读法

- 提案的四态**全部为真**；路径差量**恰为 target**；夹具 1（其他状态逐项不变）也过——unrelated 的
  staged 仍 staged、untracked 仍 untracked。按现有文本，这次 closure 判"成功"，无可指摘。
- 但真实 index 里 target 仍是签名前的 blob。于是 `git status` 把这个刚刚被持久化的文件同时报成
  `MM`：HEAD↔index 一次（内容是**倒回**签名前），index↔worktree 一次。
- 下一次任何不带路径的普通 `git commit`（社区日常大量存在），提交的是 index —— 实测得到的 target
  字节是 `base bytes\n`，即**签名前的字节**。持久化之后紧跟着一次静默的去持久化。

## 四、这条对提案意味着什么

不是驳倒乙＋丙，是四态漏量一个：closure 只钉了"新对象从具名 ref 可达"，没钉"仓库的当前编辑状态
也认这次 closure"。ref 是历史，index 是下一次提交的起点；只管前者，后者会把它吃掉。

建议并入下一份精确文本案的第五态与对应夹具，措辞留给该案：

- `index_entry_matches_commit`：target 在**真实** index 中的条目（mode + blob oid）等于 closure
  commit 的 tree entry；不等则 closure 判 blocked，不得宣称持久落地。
- 夹具：临时 index/plumbing 实现下断言该态为真，并断言 closure 后立即 `git commit -m x`（无路径）
  不产生对 target 的任何差量。

边界（照本线一贯纪律，写清楚不全在哪）：**index 认了 ≠ 不会被改回**。第五态只挡住"closure 自己留下的
陷阱"，挡不住此后任何人有意改写 target；那是别的问题，别用第五态冒充它。

## 五、探针本身的不全

- 只测了临时 index/plumbing 一种实现。porcelain `git commit --only -- target` 是否也留下同一空位，
  本轮未测——它大概率会同步真实 index，但"大概率"不是实测，不要当结论引用。
- 临时仓设了 `core.autocrlf=false`，故本探针不覆盖 CRLF 形态；那由提案夹具 3 单管。
- 探针里 `git_blob_equals_signed_raw` 用的是 `cat-file blob` 的文本比对（补了末尾换行），口径比
  提案第二节第 3 条宽；该态在本探针里不承重，只为凑齐四态展示。
