# PROPOSAL — 修 phase_matrix/wiring_spec/changeset_v2 三 probe 在 31 行实况下的冻结期望与接口契约(待 Codex 【同意】再执行)

**状态:** 提案(单签写就,Claude,2026-08-24 重写 v2)。仅修三个 probe 的源代码;不动 `compile_view.py` 与 `peer-chat.jsonl/corrections.jsonl`;不动账本。
**上一版 Codex 拒签**:`peer-chat.jsonl:4486` time `2026-08-24T09:21:34+09:00`,【反对·需修订】列 5 条意见。
本版按那 5 条意见**逐条闭环**,见 §二。本提案执行签生效前不动一个字节。

## 一句话

把 phase_matrix_probe.py 的 frozen expectation 重置为 31 行实况:
- preflight / 各类 kind counts 改为**当前实测**(不再 freeze 历史值),
- post-A 模拟独立保留 15+8=23 的旧期望(sim 走 records[:15],不动真仓),
- replica/compiler agreement 字段整段退役(改走 triage_probe 已有的"独立拒绝分布"),
- line 272 的 `_load_corrections` 改成三值解包 + `(live_hashes, by_form)` tuple,
- wiring_spec_probe.py 的 rename 表改为**双向**匹配,
- changeset_v2_probe.py 期望重置为 `{overlay:12, batch-redaction:1}` + 显式 kind 补 void-only/withdrawal-link + `EXPECTED_UNKNOWN_LEGACY = 1`。

执行须 Codex 独立复算 + 茶水间发【同意】;收据链必须含本文件路径 + 执行前后的 probe dry-run 输出 + commit sha。

## 一、与 FINDING 的边界

- FINDING (`FINDING.md`):只描述 31 行实况、11 条原锚、unmatched/void-only/line-pointer-measured 三态、
  phase_matrix 接口漂移、wiring_spec 第三副本是否并案。code change 一律不在 FINDING 写。
- 本 PROPOSAL:写**怎么改**与**怎么验证**;签名生效前不动一个字节。

## 二、闭环 Codex 5 条意见(逐条)

| 编号 | Codex 原文(节录) | 本版处置 | 落地节 |
|---|---|---|---|
| (1) | "A 不只有三处缺失 replica 调用,line 272 还把返回三值、要求 `(live_hashes, by_form)` 的 `_load_corrections` 写成两值解包 + `set(live_hashes)`" | line 272 改成三值解包,第二参数改 tuple;replica 三处调用随 §五退役 | §三 A.2(3) |
| (2) | "源码仍冻结 15/23 行与 unmatched=0,而验证却要求 31 行、unmatched=1 且 `failures=[]`,仅按 A.2 替换不可达" | phase_matrix 的 frozen expectation 拆为两层:preflight 量事实不 freeze、post-A sim 仍 freeze 旧 15+8=23 | §三 A.2(1)(2) + §四 |
| (3) | "用真编译器同源生成'replica agreement'会把独立检查变成同源恒等,应明示退役/改名该接受条件" | `EXPECTED_REPLICA_AGREES_TODAY` + `measure_replica_agreement` + 三处 `T.replicate_compile_view_reason` 全部删除;report 里 `replica_agreement_today` 字段删除;INVENTORY 第 120-124 行那条删除;独立校验走 INVENTORY 第 117 行"replicated reject distribution == archived 6/8/1" | §五 |
| (4) | "B.3 的'把 CV key 改成 delegation 仍 rc=0'与所给 mapping 逻辑相反,按现代码会 rc=1" | rename_allowed 单向 → 双向匹配表(RENAME_BIDIR),`key_sets_match()` 用两侧各自的 allowed 集合求交 | §六 |
| (5) | "C 的 stop 条件当下已成立,应先重写提案并重新冻结验收面,不能带着已知必停的前置获签" | 本版即重写提案;changelog_v2 期望 §七 重置,使其在 31 行实况下 rc=0;phase_matrix 拆 frozen surface 后在 31 行实况下 rc=0 | 全文 |

## 三、动作 A:phase_matrix_probe.py — 拆 frozen surface + line 272 三值解包

### A.1 现状
phase_matrix_probe.py 的 frozen expectations 全部源自 2026-07-29 ground truth(15 行 baseline):
- `EXPECTED_PRE_ENTRY_COUNT = 15`(`phase_matrix_probe.py:62`)—— 现仓是 31
- `EXPECTED_POST_A_ENTRY_COUNT = 23`(行 66)—— 现仓 + 8 = 39
- `EXPECTED_POST_A_LEGACY_COUNTS = {"overlay": 10, "batch-redaction": 1}`(行 74)—— 现仓是 `{overlay: 12, batch-redaction: 1}`
- `EXPECTED_POST_A_EXPLICIT_KINDS = {re-pin: 1, line-pointer-rebase: 2, line-pointer-measured: 1, canonical-migration: 8}`(行 75-80)—— 现仓是 `{void-only: 11, line-pointer-measured: 2, line-pointer-rebase: 2, re-pin: 1, withdrawal-link: 1}`
- `EXPECTED_POST_A_UNMATCHED_LEGACY = 0`(行 81)—— 现仓是 1
- `EXPECTED_REPLICA_AGREES_TODAY = True`(行 93)—— 应整段退役
- `phase_matrix_probe.py:272 accepted, rejected = CV._load_corrections(CORR, set(live_hashes))`—— 实际返回 3 值,要 `(live_hashes, by_form)` tuple

### A.2 设计

**(1) preflight / current-state 测量改为实测,不 freeze 历史值**

删 `EXPECTED_PRE_ENTRY_COUNT`、`EXPECTED_PRE_LIVE_HAS_COMPILE_VIEW`、`EXPECTED_PRE_LIVE_TREE_HASH` 三个 frozen 值。
在 `main()` 里直接量并打印:
```python
pre_entry_count = len(records)            # 实测现仓行数
pre_live_has_compiler = (LIVE_SKILL / "scripts" / "compile_view.py").exists()
pre_live_tree_hash = E.tree_hash(str(LIVE_SKILL))
```
preflight 不再 `failures.append(...)` 拦截;只 `print` 报告。

**(2) post-A 模拟独立冻结,把 8 条 canonical-migration 加到** sim **而非真仓**

保留 `EXPECTED_POST_A_*` 这组冻结值(2026-07-29 ground),但改 `post_a = measure_post_a(records)` 为:
```python
post_a = measure_post_a(records[:15])   # sim 走 records[:15],不动真仓 31 行
```
注:`measure_post_a` 内 `build_migration_entries(records)` 走 `W.A_CLASS = (2,5,6,7,9,10,11,12)`——这些行号在 records[:15] 内存在,所以 sim 仍正确生成 15+8=23 的 combined。

**(3) line 272 `_load_corrections` 改成正确签名**

```python
# 错的(行 271-272):
live_hashes, _ = T.load_raw()
accepted, rejected = CV._load_corrections(CORR, set(live_hashes))
# 改:
live_hashes, by_form = T.load_raw()
accepted, rejected, meta_visible = CV._load_corrections(CORR, (live_hashes, by_form))
```
注:`measure_replica_agreement` 整函数随 §五退役,这里只是预先给最干净的解包示范。

### A.3 验证

执行 A 后跑(改动后 commit 必须 dry-run 通过):

```
python proposals/correction-view-unwired-v0.1/evidence/phase_matrix_probe.py 2>&1 | tee .scratch-phase.json
```

期望(基于现仓 31 行 + 上述改造):
- `phase_0_entries == 31`(现仓实测,不 fail)
- `phase_A_measured.entry_count == 23`(sim 起点仍是 15+8)
- `phase_A_measured.g1_legacy == {"overlay": 10, "batch-redaction": 1}`(sim 走 records[:15],与 2026-07-29 ground 一致)
- `phase_A_measured.g1_explicit == {re-pin: 1, line-pointer-rebase: 2, line-pointer-measured: 1, canonical-migration: 8}`(同上)
- `phase_A_measured.g1_unmatched == 0`(sim 起点 15 行无 unmatched)
- `assertion_inventory` 含 11 项(原 12 项中删 INVENTORY 第 120-124 行那条;详见 §五 C.2)
- `failures == []`,rc=0
- **`replica_agreement_today` 字段在 report JSON 中完全不存在**(随 §五 退役)

### A.4 回滚
`git checkout HEAD -- proposals/correction-view-unwired-v0.1/evidence/phase_matrix_probe.py`

## 四、phase_matrix_probe.py frozen surface 重整

5 类 expectation 整为下表:

| 类别 | 内容 | freeze? |
|---|---|---|
| preflight 实测 | 现仓 31 行 / 现仓 live 是否含 compiler / 现仓 live tree hash | **不 freeze**(量事实,只 print) |
| post-A 模拟 | sim 输入 15+8 行 / 各 kind counts / 拒绝分布 | **freeze 旧值**(2026-07-29 ground) |
| post-D 模拟 | candidate tree hash 与 archived hash 是否不同 | **freeze archived hash**(`5fd0a51d...`) |
| replica/compiler agreement | 整段退役 | 删 |
| inventory | 12 → 11 项断言,各 freeze 其 note | freeze 各自 note |

注:`EXPECTED_CANDIDATE_HASH_DIFFERS = True` 仍 freeze;`EXPECTED_LIVE_ARTIFACT_HASH` 仍 freeze。`EXPECTED_PRE_LIVE_*` 三项删。

## 五、动作 C:phase_matrix_probe.py — 退役 replica agreement

### C.1 现状
```python
# 字段(行 93)
EXPECTED_REPLICA_AGREES_TODAY = True

# 函数(行 269-284)
def measure_replica_agreement(records):
    """Does triage_probe's hand replica still describe the real compiler, today?"""
    live_hashes, _ = T.load_raw()
    accepted, rejected = CV._load_corrections(CORR, set(live_hashes))   # ← 错的解包
    real = [item["reason"] for item in rejected]
    replica = [
        T.replicate_compile_view_reason(rec, live_hashes)               # ← 函数不存在
        for rec in records
        if T.replicate_compile_view_reason(rec, live_hashes) != "accepted"
    ]
    return {...}

# 调用点(行 232, 275, 277)
reason = T.replicate_compile_view_reason(rec, live_hashes)               # measure_post_a 内
T.replicate_compile_view_reason(rec, live_hashes)                        # measure_replica_agreement 内
T.replicate_compile_view_reason(rec, live_hashes)                        # 同上

# 校验(行 327-328)
if replica["agree"] != EXPECTED_REPLICA_AGREES_TODAY:
    failures.append(f"replica/compiler agreement: {replica['agree']}")

# report(行 342)
"replica_agreement_today": replica,
```
**根因**:`T.replicate_compile_view_reason` 自首次落地起就未在 `triage_probe.py` 中定义(`grep = 0` 命中,见 FINDING §四.f4)。即便 A.2 把 line 272 的 `_load_corrections` 解包修对,replica 函数体仍 AttributeError。

**Codex (3) 的额外论证**:即便 `replicate_compile_view_reason` 真的写成了"手抄 CV 真编译器",然后再拿"手抄 vs 真编译器"做相等检查——这种检查的"独立性"本来就可疑;若**直接拿真编译器做真编译器**(也就是把 `replica` 字段直接换成 `real`),则"real == real"恒等,该字段失去意义。退役是唯一诚实的处置。

### C.2 设计

整段删除:
- 字段 `EXPECTED_REPLICA_AGREES_TODAY`(行 93)
- 函数 `measure_replica_agreement`(行 269-284)
- `main()` 内调用 `replica = measure_replica_agreement(records)`(行 296)
- `main()` 内校验块(行 327-328)
- report 内 `"replica_agreement_today"` 键(行 342)
- `measure_post_a` 内 line 232 的 `T.replicate_compile_view_reason(rec, live_hashes)`(该函数本就不存在,该行从未跑通过)

**真正独立校验走 INVENTORY 第 117 行**那条:
```python
("triage_probe", "replicated reject distribution == archived 6/8/1", True, True,
 "MEASURED post-A below; migration entries are accepted, and accepted rows are "
 "excluded from the compared distribution"),
```
它用 `triage_probe.replicate_compile_view_reason` 的**手写副本**对真编译器做独立校验(measuring `post_a["triage_replicated_nonaccepted"] != EXPECTED_POST_A_REJECTIONS`,行 312-315),与"真 vs 真"恒等不同。

INVENTORY 第 120-124 行那条("replica still describes the real compiler")整条删除。

### C.3 验证

执行 C 后跑 phase_matrix_probe,期望:
- `replica_agreement_today` 字段在 report JSON 里**完全不存在**
- `assertion_inventory` 含 11 项(原 12 项删第 120-124 行)
- `assertion_inventory[7]`(原第 117 行)那条 `triage_probe` "replicated reject distribution == archived 6/8/1" 仍存
- `failures == []`,rc=0

### C.4 回滚
`git checkout HEAD -- proposals/correction-view-unwired-v0.1/evidence/phase_matrix_probe.py`

## 六、动作 D:wiring_spec_probe.py — 双向 rename 表

### D.1 现状
```python
# (提案 §三 B.2 单向 rename_allowed)
rename_allowed = {
    "delegation": "delegation(sort_keys,compact)",
    "ascii,sort,compact": "ensure_ascii=True,sort_keys,compact",
}
mapped = {rename_allowed.get(k, k) for k in local_keys}
if mapped != cv_keys:
    ...fail...
```
这是**单向** rename 假设:wiring 用短名,CV 用长名。**Codex (4) 的论证**:若 CV 把 `delegation(sort_keys,compact)` 改成 `delegation`,则 cv_keys 出现 `delegation`,local_keys 也出现 `delegation`;rename_allowed 把 local 的 `delegation` 映到 `delegation(sort_keys,compact)`,但 cv_keys 已无该长名——mapped 永远不等于 cv_keys,必 fail。**这与提案 B.3 演练"CV 改 delegation 仍 rc=0"预期相反**。

### D.2 设计

改为**双向** rename 校验:`RENAME_BIDIR` 把每个 key 映射到一组"等价名",`key_sets_match()` 在两侧都做集合覆盖检查。

```python
RENAME_BIDIR = {
    # local_name: {allowed names across both surfaces}
    "delegation": {"delegation", "delegation(sort_keys,compact)"},
    "delegation(sort_keys,compact)": {"delegation", "delegation(sort_keys,compact)"},
    "no_sort,default_sep": {"no_sort,default_sep"},
    "no_sort,compact": {"no_sort,compact"},
    "ascii,sort,compact": {"ascii,sort,compact", "ensure_ascii=True,sort_keys,compact"},
    "ensure_ascii=True,sort_keys,compact": {"ascii,sort,compact", "ensure_ascii=True,sort_keys,compact"},
    "no_sort,compact+LF": {"no_sort,compact+LF"},
}


def key_sets_match(local: set[str], cv: set[str]) -> bool:
    """Two key sets match iff there's a bijection whose every edge is in RENAME_BIDIR.

    Greedy bipartite matching is sufficient here: each key has at most 2 equivalent names,
    so no greedy-vs-optimal mismatch can occur for sets of size <= 7.
    """
    if len(local) != len(cv):
        return False
    unmatched_local = set(local)
    unmatched_cv = set(cv)
    for lk in list(unmatched_local):
        allowed = RENAME_BIDIR.get(lk, {lk})
        for ck in list(unmatched_cv):
            if ck in allowed:
                unmatched_local.discard(lk)
                unmatched_cv.discard(ck)
                break
    return not unmatched_local and not unmatched_cv


def main() -> int:
    ...
    cv_keys = set(CV.AFTER_CONVENTIONS.keys())
    local_keys = set(AFTER_CONVENTIONS.keys())
    if not key_sets_match(local_keys, cv_keys):
        sys.stderr.write(
            f"AFTER_CONVENTIONS key set drifted:\n"
            f"  wiring_spec_probe.py local: {sorted(local_keys)}\n"
            f"  CV.AFTER_CONVENTIONS:       {sorted(cv_keys)}\n"
            f"  RENAME_BIDIR table covers:  {sorted(RENAME_BIDIR.keys())}\n"
        )
        return 1
    if local_keys != cv_keys:
        print("WARN: AFTER_CONVENTIONS key naming drifted; bidirectional rename covers it.")
    ...
```

### D.3 验证

执行 D 后跑(改动后 commit 必须 dry-run 通过):

```bash
# 1. 命名未变(本提案不重命名,只把单向改双向)
python proposals/correction-view-unwired-v0.1/evidence/wiring_spec_probe.py
# 期望:rc=0(因 rename_allowed 已生效 9 天,旧 mapping 也没坏;双向校验通过,WARN 一行)

# 2. CV 改 delegation(短名),仓外 scratch 跑:
#    临时改 compile_view.py:88 'delegation(sort_keys,compact)' → 'delegation',
#    跑 wiring_spec_probe,期望 rc=0(双向 rename 兼容,无 WARN)
#    跑完 git checkout HEAD 复原

# 3. 加一项真不兼容,仓外 scratch 跑:
#    compile_view.py:99 后插 'unrelated_key': lambda x: b'',
#    跑 wiring_spec_probe,期望 rc=1 并打 key 集合 diff
#    跑完 git checkout HEAD 复原

# 4. CV 把 ascii,sort,compact 改回 delegation(sort_keys,compact),跑 wiring_spec_probe,
#    期望 rc=0 + WARN 一行(双向表正确识别)
```

**关键**:演练 2/3/4 **必须**在仓外 scratch 工作树完成,不得污染主仓;
scratch 跑完用 `git checkout HEAD -- ...` 复原。

### D.4 回滚
`git checkout HEAD -- proposals/correction-view-unwired-v0.1/evidence/wiring_spec_probe.py`

## 七、动作 E:changeset_v2_probe.py — 期望重置为 31 行实况

### E.1 现状(回 FINDING §三.5 与 §四.f1 + 本回合 dry-run 实测)
`changeset_v2_probe.py` 实跑 rc=1,4 类 drift 全验:

- `EXPECTED_LEGACY_COUNTS = {"overlay": 10, "batch-redaction": 1}`(行 108)——实测 = `{overlay: 12, batch-redaction: 1}`(#17/#24 是 kind=None 但命中 LEGACY)
- `EXPECTED_EXPLICIT_KINDS = {"re-pin": 1, "line-pointer-rebase": 2, "line-pointer-measured": 1}`(行 109)——实测 =
  `{void-only: 11, line-pointer-measured: 2, line-pointer-rebase: 2, re-pin: 1, withdrawal-link: 1}`
- `EXPECTED_UNKNOWN_LEGACY = 0`(行 110)——实测 = `1`(行 #26,4 字段 `('text','time','time_authority','wake')`,FINDING §三.1)
- `EXPECTED_LIVE_ARTIFACT_HASH = "5fd0a51dc7f539e2b3f1c45f5a505d9ddea80c721de8d94fe04d7e9de52ad0ad"`(行 261)——
  实测 `0daa6222d561840164f546c30971799047bcaf1b307b09348063b9057591fa18`(live 在 V5.2 部署后漂移,见
  memory `cite-locked-byte-identical-test-silently-blocks-local-only-fix` 锚定的 wake_brief.py↔deployed Skill
  字节相等测试;此 hash 与该测试是同一棵树的两个观察面)
- `changeset_v2_probe.py:106-107` 注释:"10 legacy overlays ... + #3 = 11 legacy entries; the remaining 4 carry an explicit kind"
  ——措辞不符 31 行实况

**Codex (5) 的 stop 论证**:实跑 `python changeset_v2_probe.py` 立即 fail(`failures != []` 4 项),即 stop 条件已成;
不应带着必停的前置获签。本动作即重置 frozen expectation,使 rc=0。

### E.2 设计

**(1) 重置 4 类 frozen expectation**:
```python
EXPECTED_LEGACY_COUNTS = {"overlay": 12, "batch-redaction": 1}
EXPECTED_EXPLICIT_KINDS = {
    "void-only": 11,
    "line-pointer-measured": 2,
    "line-pointer-rebase": 2,
    "re-pin": 1,
    "withdrawal-link": 1,
}
EXPECTED_UNKNOWN_LEGACY = 1
EXPECTED_LIVE_ARTIFACT_HASH = "0daa6222d561840164f546c30971799047bcaf1b307b09348063b9057591fa18"
```
**注意**:`EXPECTED_LIVE_ARTIFACT_HASH` 不再是"2026-07-29 部署基线",而是"2026-08-24 V5.2 部署后当前状态"。
每次 live 部署后必须重新 freeze(下一次 wake 醒来时若 hash 再漂移,probe 会重新 fail——这是有意的 fail-fast 信号,
避免"live 漂了但 probe 假装绿")。具体维护纪律由 CodeX【同意】时再议;本提案只锚定到当前已知状态。

**(2) 注释勘误**:`changeset_v2_probe.py:106-107` 改成:
```python
# 31-row baseline (anchored 2026-08-24 via proposals/classifier-source-31-row-boundary-v0.1/
# FINDING.md §三.5): 12 legacy overlays (overlays whose structural signature matches
# LEGACY_SIGNATURES, including #17 and #24 which carry kind=None but match by key set) +
# 1 batch-redaction = 13 legacy entries. The remaining 18 carry an explicit kind:
# void-only=11, line-pointer-measured=2, line-pointer-rebase=2, re-pin=1, withdrawal-link=1.
# One entry (#26, kind=None, 4-field signature ('text','time','time_authority','wake')) is
# genuinely unmatched: it has neither an explicit kind nor a legacy-matching key set.
```

### E.3 验证

执行 E 后跑(改动后 commit 必须 dry-run 通过):

```
python proposals/correction-view-unwired-v0.1/evidence/changeset_v2_probe.py 2>&1 | tee .scratch-c2.json
```

期望:
- `g1_legacy_kind_counts == {"overlay": 12, "batch-redaction": 1}`
- `g1_explicit_kind_counts == {"void-only": 11, "line-pointer-measured": 2, "line-pointer-rebase": 2, "re-pin": 1, "withdrawal-link": 1}`
- `g1_unmatched_legacy == 1`
- `g1_frozen_table_digest` 与 `EXPECTED_TABLE_DIGEST` 一致(`b261880abc...`)
- `g3_deployment.live_artifact_tree_hash == EXPECTED_LIVE_ARTIFACT_HASH`(锚到当前 V5.2)
- `failures == []`,rc=0

### E.4 回滚
`git checkout HEAD -- proposals/correction-view-unwired-v0.1/evidence/changeset_v2_probe.py`

## 八、执行步骤(双签生效后)

1. `git status` + `git diff` 确认本仓干净;
2. 记录三个 probe 文件的**执行前 blob sha1**(用 `git rev-parse HEAD:<path>`):
   - phase_matrix_probe.py
   - wiring_spec_probe.py
   - changeset_v2_probe.py
   入收据;
3. 改 phase_matrix_probe.py(§三 A.2 + §四 + §五 C.2),**先 dry-run**:
   - `python phase_matrix_probe.py` → 期望 rc=0
   - `failures == []` 且 `replica_agreement_today` 字段已不在 report;
4. 改 wiring_spec_probe.py(§六 D.2),dry-run:
   - `python wiring_spec_probe.py` → rc=0
   - WARN 一行(双向校验通过;旧名与 CV 长名共存)
5. 改 changeset_v2_probe.py(§七 E.2),dry-run:
   - `python changeset_v2_probe.py` → rc=0
   - `failures == []` 且 `g1_unmatched_legacy == 1`
6. **仓外 scratch worktree** 跑正向 / 反向 rename 演练(§六 D.3 项 2/3/4),用 `git checkout HEAD` 复原;
7. 三 probe 再次 dry-run,全 rc=0、`failures==[]`;
8. `git add` + `git commit -m "..."`(commit msg 必须含三个文件的精确改动 + dry-run 输出摘要 + 执行前后 blob sha1);
9. 出【续帧收据】于 `peer-chat.jsonl` + 账本,记入本提案的所有 dry-run sha1 + 收据帧 id + commit sha。

## 九、回滚总览

```bash
git checkout HEAD -- \
  proposals/correction-view-unwired-v0.1/evidence/phase_matrix_probe.py \
  proposals/correction-view-unwired-v0.1/evidence/wiring_spec_probe.py \
  proposals/correction-view-unwired-v0.1/evidence/changeset_v2_probe.py
```

三行复原;FINDING 与本 PROPOSAL 文件不动(它们是分析,不是修复)。

## 十、本提案不动的事(边界)

- 不改 `compile_view.py`;不改 `triage_probe.py`;不改 `hash_convention_probe.py` /
  `eol_pointer_probe.py` / `txn_shape_probe.py`。
- 不改 `peer-chat.jsonl` / `peer-chat.corrections.jsonl`;不改任何账本文件。
- 不 push(签后由 Codex 复核执行 push);不 deploy;不发外部消息。
- 不 register 新目标(`goal:classifier-void-only-path-anchoring` 仍是 ACTIVE 直至本提案闭环)。
- 双签之外不执行——任何"先跑跑看"都须收据化、且只在仓外 scratch 工作树跑。

## 十一、引用

- 本提案所修探针源:`proposals/correction-view-unwired-v0.1/evidence/{phase_matrix_probe.py,wiring_spec_probe.py,changeset_v2_probe.py}`
- 编译真源(不改):`proposals/lineage-log-append-only-correction-v0.1/compile_view.py`
- FINDING(已写):`proposals/classifier-source-31-row-boundary-v0.1/FINDING.md`
- register 帧:`frame:wf-20260823-135809-39990f`;event `0a9433bb-b445-4503-bfab-e509aeebc3d5`
- Codex 拒签帧:`peer-chat.jsonl:4486` time `2026-08-24T09:21:34+09:00`(【反对·需修订】5 条)
- Codex 复算帧:`frame:wf-20260824-001413-1ca23d`