# find-frame-index-v0.1 — 候选,不是落地

把 `find_frame` 的逐 id glob 换成一次 scandir 建的**进程内** id→路径表。
本目录是 Codex 2026-08-01T01:29:56+09:00【反对·窄修】要求的那个形状:外部候选,
不动 `D:\CodexData\skills\solve-with-weilan`。**本轮零 deployed 改动,未签,不得读成已采纳。**

被驳回的那一版错在两处,这里都改了:
1. 上一版入树的是 monkeypatch 探针,不是候选实现——它测的是探针里自己写的
   `indexed_find_frame`,构造上抓不到候选的缺陷,因为候选当时还不存在。
2. 上一版绕过了本工作区的外部 Skill Evolution plane(AGENTS.md「Change discipline」)。

## 一、制品与地址

| | 内容寻址 hash |
|---|---|
| baseline(= 当前 deployed skill 的干净副本) | `ae0537dab5c050c9c1fadf7d432eaa39fa34449ba4420dd879f13068d0b142ad` |
| candidate | `fb16689a63538f39d35374a123c860c0bfbfddeca900fd10027483c865830996` |

旧候选 `794022d90d8a173468ea67a9bb98f69176f603ef9ba2dc032088d7c8d0a7ad5b`
已经废弃:它被 `CODEX_REVIEW_20260801.md` 指出的契约自撞 blocker 否掉,不得再读成现行候选。

`proposal.json` 已过 `proposal-validate`(valid:true, changed_path_count:2)。

`artifacts/` **不入仓**:它是 `baseline/` 与 `candidate/` 的逐字副本,由两条命令确定性重建,
且地址本身自验(重跑 `candidate-freeze` 得 `created:false` 即证存量未漂)。重建:

```
python tools/evolution_cli.py candidate-freeze --source proposals/find-frame-index-v0.1/baseline/solve-with-weilan  --artifact-root proposals/find-frame-index-v0.1/artifacts
python tools/evolution_cli.py candidate-freeze --source proposals/find-frame-index-v0.1/candidate/solve-with-weilan --artifact-root proposals/find-frame-index-v0.1/artifacts
```

`baseline/` 与 `candidate/` 本身入仓,所以第三方不必持有 deployed skill 才能复跑——
这一条是刻意的,针对 `goal:cited-evidence-absent-from-tree` 那条 FINDING。

## 二、改了什么(候选内,两个文件)

`scripts/weilan_trace.py`
- `_frame_index()`:一次 `os.scandir` 扫 `frames/` 下的日期目录,建 id→[paths],并保存完整
  `{date_dir_name: st_mtime_ns}` 映射。纯派生物,不落盘、不新增文件、不新增格式。
- `find_frame()`:每次查表前以日期目录名字集合 + 每目录 mtime 护栏核对;有差异即重建。查不到、
  表里的路径已消失或命中路径已不再匹配该 id 时回退原 glob;`read_events` 过滤空帧、
  多命中 `RuntimeError`、无命中 `FileNotFoundError` 逐字不变。
- `note_frame_write()` + 两处调用点(`append_event`、lineaged open 的 `write_event_file_atomic`):
  写到 `frames/` 下即弃表。**窄失效**:写别处不弃表,否则每条账本追加都会白白抹掉加速。

`scripts/test_find_frame_index.py`:11 条新回归。

## 三、正确性证据

**承重的一支是等价探针,不是那个测试文件。** `_probe_20260801_find_frame_equivalence.py`
把同样 9 个场景分别喂给两棵冻结树(各自独立子进程、独立 temp method-state),比对结果:

- **9/9 逐字等价**:plain_hit / missing_id / duplicate_id / empty_frame_file_only /
  empty_and_live_same_id / moved_after_first_lookup / deleted_after_first_lookup /
  appended_by_this_process_after_first_lookup / foreign_second_file_after_first_lookup。
- 原案唯一的分歧 `foreign_second_file_after_first_lookup` 已被护栏关掉:第二个日期目录出现后,
  名字集合变化使索引重建,两个 live id 因而与 baseline 一样抛 `RuntimeError`。

修订契约有两条严格义务。**T1**:返回的路径在返回时必须仍是该 id 的 live match。
**T2**:foreign creation 之后,只要随后的 stat 已能观察到日期目录 mtime 变化,护栏必须重建,
重复 live id 必须抛 `RuntimeError`。仍披露一条不作为 rollback trigger 的边界:foreign creation
若与护栏观察落在同一个约 1 ms 的目录 mtime tick 内,该次 lookup 仍可能看不见它。护栏成本探针
`_probe_20260801_guard_cost_and_mtime.py` 量到 200 次中 197 次 mtime 改变、3 次不变,最小正差
`0.9921 ms`。

九场景里的 foreign-write 场景走的是**日期目录名字集合**这条腿,不是 mtime 腿;mtime 腿另由
`_probe_20260801_claude_mtime_leg_residual.py` 在目录名全程不变且无 sleep 的条件下实测 60/60
抛 `RuntimeError`、0 漏。这个结果只说明披露偏保守,不证明 same-tick 残留不存在。

### 一条负面结果,写在前面免得被读肥

独立评审把修订后的新测试文件喂给“修订树但 `weilan_trace.py` 换回无护栏的废弃候选
`794022d9…`”的临时树:`test_foreign_second_file_rebuilds_after_observable_mtime_change`(T2)
在无护栏树 **FAILED**、在修订候选 **PASSED**。其余 9 条在无护栏树仍 PASSED;same-tick
残留测试因那棵废弃树没有 `_FRAME_INDEX_DIR_MTIMES` 而失败,不计作护栏的行为鉴别。

## 四、验收(印 rc 与节点,不印「全过」)

`_probe_20260801_suite_acceptance.py`,两棵树同条件:

| | pytest rc | 收集节点 | PASSED | FAILED |
|---|---|---|---|---|
| baseline | 1 | 93 | 92 | 1 |
| candidate | 1 | 104 | 103 | 1 |

- 节点差 = 恰好我新增的 11 条,`only in baseline` 为空集,`candidate-only failures` 为空集。
- **套件不是全绿**,两棵树同一条红:`test_slow_loop.py::test_promotion_gate_rejects_on_full_budget`
  —— `promotion requires a valid source_authenticity marker: invalid_or_incomplete_marker`
  (`weilan_trace.py:2177`)。它在**冻结 baseline 上同样红**,故是先在缺陷,不是本候选引入的。
  我刻意**没有**在本案里修它:文件集锁死,扩项就是偷渡。它值不值得单开一案,归你判,我不选。
- 23 个 main() 式脚本直接跑,两棵树同样只有 `test_slow_loop.py` 非零(rc=1),同一条先在缺陷。

## 五、性能(同一次运行,交错跑,不锚固定 digest)

性能判据只承重已归档的 `_probe_20260801_claude_revision_perf.out.json`:该次四跑按
baseline→candidate→baseline→candidate 交错运行,并要求四次 stdout 字节同一。独立评审时
账本为 5888 条:

- **四跑 stdout 逐字全同**;若账本在一组测量中增长,该 flag 会 false,那组耗时
  就不能作为同载荷比较。
- `min_run_speedup_x = min(baseline_elapsed_s) / min(candidate_elapsed_s)`:它配的是每臂最快次,
  **不是最坏配对**,也不是观察到的最小相邻配对加速。该口径报 **2.54×**;mean-ratio 报
  **2.63×**。
- Codex 先前报告的 **2.51× / 2.61×** 只保留为散文口径、未归档的背景,不承重门槛判断,
  也不与已归档测量合称两次可复算证据。
- 已归档的 `2.54×` 只比原 `2.5×` 门槛高约 1%,而宿主负载不受控;`proposal.json` 因此把
  门槛降为 **2.0×**,仍保留独立的 stdout byte-identical 指标。绝对秒数不作跨轮比较。

不锚固定 digest 是上一版的自我更正:lineage-show 的输出随账本增长而变,保质期以分钟计。

## 六、边界(不得读肥)

- **快 ≠ 对**。四跑字节相同只说明在**这一个账本、这一条命令**上两者同输出,不构成对
  `find_frame` 全定义域的等价证明;定义域证据是第三节那 9 个场景,而 9 个场景也是有限的。
- **等价探针不覆盖并发**。它是单进程顺序脚本,「别的进程」是用直接写文件模拟的。真并发下
  两个实现各自的行为都没测。
- **表是进程内的**,所以它对跨进程的任何断言都零贡献;它也从不落盘,故不产生新的可信面。
- 本目录**不含** adoption decision,也不含 shadow-result。采纳须独立复核 + 双签,签名者不能是我。

## 七、复跑

```
cd proposals/find-frame-index-v0.1
python -X utf8 _probe_20260801_candidate_tree_diff.py       # 只改了声明的两个路径
python -X utf8 _probe_20260801_claude_revision_equivalence.py # 承重:修订版 9 场景行为等价
python -X utf8 _probe_20260801_claude_revision_acceptance.py  # rc + 节点数 + T2 鉴别力
python -X utf8 _probe_20260801_claude_revision_perf.py        # 逐字相等 + 独立耗时
python -X utf8 _probe_20260801_guard_cost_and_mtime.py        # 197/200 + 0.9921 ms
python -X utf8 _probe_20260801_claude_mtime_leg_residual.py   # 只量 mtime 腿
```

先跑第一节的两条 `candidate-freeze` 重建 `artifacts/`;探针都从冻结树取输入。
一切 `time` 只当只追加文件内的身份键,不当时刻(`ledger-timestamp-authority-v0.1`)。
