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
| candidate | `794022d90d8a173468ea67a9bb98f69176f603ef9ba2dc032088d7c8d0a7ad5b` |

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
- `_frame_index()`:一次 `os.scandir` 扫 `frames/` 下的日期目录,建 id→[paths]。纯派生物,
  不落盘、不新增文件、不新增格式。
- `find_frame()`:先查表,查不到或表里的路径已消失则回退原 glob;`read_events` 过滤空帧、
  多命中 `RuntimeError`、无命中 `FileNotFoundError` 逐字不变。
- `note_frame_write()` + 两处调用点(`append_event`、lineaged open 的 `write_event_file_atomic`):
  写到 `frames/` 下即弃表。**窄失效**:写别处不弃表,否则每条账本追加都会白白抹掉加速。

`scripts/test_find_frame_index.py`:10 条新回归。

## 三、正确性证据

**承重的一支是等价探针,不是那个测试文件。** `_probe_20260801_find_frame_equivalence.py`
把同样 9 个场景分别喂给两棵冻结树(各自独立子进程、独立 temp method-state),比对结果:

- 8/9 逐字等价:plain_hit / missing_id / duplicate_id / empty_frame_file_only /
  empty_and_live_same_id / moved_after_first_lookup / deleted_after_first_lookup /
  appended_by_this_process_after_first_lookup。
- 1/9 分歧,且**恰是提案自己披露的那条竞态**:`foreign_second_file_after_first_lookup`
  —— 建表后由别的进程新造同 id 第二文件,baseline 抛 `RuntimeError`,candidate 仍返回它已知的
  那一个。探针的 `divergence_is_exactly_the_disclosed_race` 为 true。

这条竞态 v1 接受并披露,理由:glob 版自身也不保证(它只是恰好每次重扫),且义务 (a) 关不掉它
——索引里的路径确实还在。测试文件里 `test_disclosed_residual_race_is_pinned_not_hidden`
**断言这条分歧本身**而不是断言它被修好了:将来谁真把它关上,那条测试会红,于是必须重新裁断,
而不是悄悄改掉。

### 一条负面结果,写在前面免得被读肥

`_probe_20260801_test_discriminates.py` 把新测试文件嫁接到 baseline 上跑,结果是
10 个节点**全 ERROR**。这**不**是「10 条行为差异」——它们全部错在 fixture setup,因为
baseline 上没有 `invalidate_frame_index` 这个函数。全 ERROR 只证明 API 不存在,不证明任何行为不同。
把它读成行为鉴别,就是这条线反复犯的「零命中读成零输入」。行为鉴别只在等价探针里,别引错。

## 四、验收(印 rc 与节点,不印「全过」)

`_probe_20260801_suite_acceptance.py`,两棵树同条件:

| | pytest rc | 收集节点 | PASSED | FAILED |
|---|---|---|---|---|
| baseline | 1 | 93 | 92 | 1 |
| candidate | 1 | 103 | 102 | 1 |

- 节点差 = 恰好我新增的 10 条,`only in baseline` 为空集。
- **套件不是全绿**,两棵树同一条红:`test_slow_loop.py::test_promotion_gate_rejects_on_full_budget`
  —— `promotion requires a valid source_authenticity marker: invalid_or_incomplete_marker`
  (`weilan_trace.py:2177`)。它在**冻结 baseline 上同样红**,故是先在缺陷,不是本候选引入的。
  我刻意**没有**在本案里修它:文件集锁死,扩项就是偷渡。它值不值得单开一案,归你判,我不选。
- 23 个 main() 式脚本直接跑,两棵树同样只有 `test_slow_loop.py` 非零(rc=1),同一条先在缺陷。

## 五、性能(同一次运行,交错跑,不锚固定 digest)

`_probe_20260801_frozen_tree_perf.py`,顺序 baseline→candidate→baseline→candidate,
真实账本 5881 帧:

- **四跑 stdout 逐字全同**(1,348,418 B,record_count 5881,valid true,单一 digest)。
  这同时证明探针期间账本没长——若长了,这个 flag 会 false,那时的耗时对比就是在比不同载荷。
- baseline 92.024 s(冷)/ 32.386 s(热);candidate 11.401 s / 11.753 s。热对热 ≈ **2.84×**。

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
python -X utf8 _probe_20260801_find_frame_equivalence.py    # 承重:9 场景行为等价
python -X utf8 _probe_20260801_suite_acceptance.py          # rc + 节点数(约 2 分钟)
python -X utf8 _probe_20260801_frozen_tree_perf.py          # 逐字相等 + 耗时(约 2.5 分钟)
python -X utf8 _probe_20260801_test_discriminates.py        # 负面结果,见第三节
```

先跑第一节的两条 `candidate-freeze` 重建 `artifacts/`,五支探针都从那里取树。
一切 `time` 只当只追加文件内的身份键,不当时刻(`ledger-timestamp-authority-v0.1`)。
