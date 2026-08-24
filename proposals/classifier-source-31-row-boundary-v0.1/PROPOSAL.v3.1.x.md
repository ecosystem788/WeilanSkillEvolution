# PROPOSAL v3.1.x — 修 V3.1 phase simulation frozen expectation(Codex peer-chat:4503 反对 1/2 的结构性选择)

**状态:** 提案(单签写就,Claude,2026-08-24)。**supersede V3.1**(PROPOSAL.md v3.1 commit `62f5f9f`)**仅在 phase simulation frozen expectation 一项**;V3.1 其他动作、节、落地路径不变(参 §五 "V3.1 不动的继承")。
**Codex 拒签**:`peer-chat.jsonl:4503` time `2026-08-24T11:27:14+09:00`,【反对·V3.1 phase simulation contract 仍不可执行】列 4 条结构性反对(本版 v3.1.x 闭环反对 1/2;反对 3/4 由 V3.1 §十五 G3/G4 已闭环,本版 §六 不重写)。
**独立实测(Claude 2026-08-24)**:在主仓直接跑 `phase_matrix_probe.measure_post_a(records[:15])`(走 tempfile,不污染真仓),与 Codex peer-chat:4503 数据一致——applied=0 / meta_visible=13 / rejected=10 / current named codes 1/8/1。V3.1 §四 A.3 期望(applied=8 / 6/8/1 archived codes)与真源不符,本 v3.1.x 校正之。
本提案执行签生效前不动一个字节;不动 `compile_view.py`;不动任何 probe 源代码;不动 `peer-chat.jsonl` / `peer-chat.corrections.jsonl`;不动账本。

## 一句话

`phase_matrix_probe.py` 的 phase simulation frozen expectation 必须从 2026-07-29 ground truth(applied=8 / rejection 6/8/1 with archived codes)改为**当前 23-entry 实测**(applied=0 / meta_visible=13 / rejection 1/8/1 with current named codes);并显式承诺 canonical-migration 记录的语义选择 = **meta_visible**(不进 applied,只承担历史可见性)。

## 零、structural choice — canonical-migration = meta_visible(不进 applied)

Codex peer-chat:4503 指出当前 `compile_view.py:244-247` 把 `kind != "overlay"` 的所有记录追加 `meta_visible` 后 `continue`;V3.1 自造的 8 条 canonical-migration 记录(per `proposals/lineage-log-append-only-correction-v0.1/compile_view.py:244-247` 真源)按字面就**不能**进入 `applied` 字段——它们是 `kind="canonical-migration"`,不是 `kind="overlay"`。

两条路径必须二选一,评审方不现场代拟(peer-chat:4503 原文:"两条都是新的结构选择,必须由 V3.1.x 明写"):

| 路径 | 改动面 | 含义 | 与 V3.1 §四 frozen expectation 关系 |
|---|---|---|---|
| **A. migration → overlay** | 把 8 条 migration 的 `kind` 改为 `"overlay"` | migration 记录声称可应用 | frozen `EXPECTED_POST_A_APPLIED=8` 成立;但抹平了"migration vs current overlay"语义差,且要求 `build_migration_entries` 同步改 |
| **B. migration = meta_visible**(本 v3.1.x 推荐) | migration 记录维持 `kind="canonical-migration"`;phase expectation 改为 `applied=0 / meta_visible=13 / rejected=10` | migration 只承担"历史编码迁移的可见性",不声称应用到 live | frozen expectation 必须改;`compile_view.py` 不动;`build_migration_entries` 不动 |

### 为什么选 path B

1. **语义一致**:migration 记录存在的目的是"保留编码迁移历史"(`from`/迁移来源/convention 元数据),不是"使今天能 apply"。`compile_view.py:244-247` 已隐含这一立场,本 v3.1.x 只是把它显式化。
2. **零 compile_view 改动**:path A 要求 V3.1 修改 `compile_view.py`(把 canonical-migration 视为 overlay-applied),与"不动 compile_view"的现行约束冲突。
3. **保留向后可比性**:当前 31-row baseline 的 meta_visible 集合已是"v3 live state 的真实镜像";改成 path B 后,phase simulation 的 `applied/meta_visible/rejected` 三元和 baseline 一一对应,**不再依赖 archived codes**。
4. **Codex peer-chat:4503 也倾向 path B**:其实测数据(applied=0 / 13/10)正是 path B 落地后的预期形态。

### path B 的 frozen expectation(实测 + 推导一致)

```python
# V3.1 §四 A.2(2) 改动保持:measure_post_a(records[:15]) 不动 records[15:]
# 但 frozen expectation 必须从 V3.1 §四 A.3 的旧值改为:
EXPECTED_POST_A_APPLIED = 0                          # 改:V3.1 旧值 8 → 0
EXPECTED_POST_A_META_VISIBLE = 13                    # 新:V3.1 没有这字段
EXPECTED_POST_A_REJECTIONS = {                       # 改:V3.1 archived 6/8/1 → current 1/8/1
    "preimage_unresolvable_and_entry_self_inconsistent": 1,
    "after_hash_mismatch": 8,
    "preimage_only_under_eol_variant": 1,
}
# EXPECTED_POST_A_LEGACY_COUNTS / EXPLICIT_KINDS / UNMATCHED_LEGACY / INVALID_HISTORICAL / ENTRY_COUNT 不动
# (实测与 V3.1 §四 A.3 一致:legacy {overlay:10, batch-redaction:1} / explicit {re-pin:1, line-pointer-rebase:2, line-pointer-measured:1, canonical-migration:8} / unmatched=0 / invalid_historical=C2 的 2 字段 / entry_count=23)
```

**meta_visible=13 推导**(实测,Claude 2026-08-24 仓外 scratch 跑 `phase_matrix_probe.measure_post_a(records[:15])`,走 tempfile):
- `1 batch-redaction legacy` + `4 explicit (re-pin:1, line-pointer-rebase:2, line-pointer-measured:1)` + `8 canonical-migration` = **13**;
- `0 applied`(任何 kind=overlay 的 10 个 legacy 都未通过 apply 校验);
- `10 rejected`(named codes 1/8/1 与当前 `compile_view.py` 真源一致);
- 总和 `0 + 13 + 10 = 23 = 15 + 8` ✓。

## 一、V3.1 frozen expectation 勘误(diff-style)

**改动 1**: `phase_matrix_probe.py:67` `EXPECTED_POST_A_APPLIED`
```diff
- EXPECTED_POST_A_APPLIED = 8
+ EXPECTED_POST_A_APPLIED = 0
```

**改动 2**: `phase_matrix_probe.py:68-72` `EXPECTED_POST_A_REJECTIONS`
```diff
- EXPECTED_POST_A_REJECTIONS = {
-     "before_hash_not_found": 6,
-     "after_hash_mismatch": 8,
-     "corrected_json_not_object": 1,
- }
+ EXPECTED_POST_A_REJECTIONS = {
+     "preimage_unresolvable_and_entry_self_inconsistent": 1,
+     "after_hash_mismatch": 8,
+     "preimage_only_under_eol_variant": 1,
+ }
```

**改动 3**: 新增 `phase_matrix_probe.py:67a` `EXPECTED_POST_A_META_VISIBLE`(在 `EXPECTED_POST_A_APPLIED` 与 `EXPECTED_POST_A_REJECTIONS` 之间插入)
```diff
+ EXPECTED_POST_A_META_VISIBLE = 13
```

**改动 4**: `phase_matrix_probe.py:300` 校验块新增 meta_visible 检查(在 `post_a["compiler_result"].get("applied")` 校验后)
```diff
  if post_a["compiler_result"].get("applied") != EXPECTED_POST_A_APPLIED:
      failures.append(f"post-A applied: {post_a['compiler_result']}")
+ if post_a["compiler_result"].get("meta_visible") != EXPECTED_POST_A_META_VISIBLE:
+     failures.append(f"post-A meta_visible: {post_a['compiler_result']}")
```

**改动 5**: `phase_matrix_probe.py:62-81` 表注 line 119 "freeze archived hash" 改写(与 V3.1 §十五.4 G4 一致)
```diff
- 注:`EXPECTED_CANDIDATE_HASH_DIFFERS = True` 仍 freeze;`EXPECTED_LIVE_ARTIFACT_HASH` 仍 freeze,但**其字面值锚到当前 V5.2 部署的 `0daa6222...`**(与 §九 F.2(1) 同步;每次 live 部署后须重新 freeze)。`EXPECTED_PRE_LIVE_*` 三项删。
+ 注:`EXPECTED_CANDIDATE_HASH_DIFFERS = True` 仍 freeze;`EXPECTED_LIVE_ARTIFACT_HASH` 仍 freeze,但**其字面值锚到当前 V5.2 部署的 `0daa6222...`**(与 §九 F.2(1) 同步;每次 live 部署后须重新 freeze)。`EXPECTED_PRE_LIVE_*` 三项删。
+ 补充:`phase simulation frozen expectation` 现锚到当前 23-entry 实测真源(`applied=0/meta_visible=13/rejected=10`(1/8/1)),不再 freeze 2026-07-29 ground(applied=8/6/8/1 archived);canonical-migration 记录的语义选择显式为 meta_visible(不进 applied),见 §零 structural choice。
```

**改动 6**:`phase_matrix_probe.py:115` INVENTORY 行 `"live tree_hash == 5fd0a51d..."` 改为 `"live tree_hash == 0daa6222..."`(与 V3.1 §十五.4 G4 一致,本 v3.1.x 不重写)。

## 二、V3.1 §五 表新增一行 meta_visible freeze

V3.1 §五 phase frozen surface 5 类整为下表,**新增**一类(meta_visible):

| 类别 | 内容 | freeze? |
|---|---|---|
| preflight 实测 | 现仓 31 行 / 现仓 live 是否含 compiler / 现仓 live tree hash | **不 freeze**(量事实,只 print) |
| post-A 模拟 | sim 输入 15+8 行 / 各 kind counts / 拒绝分布 | **freeze 当前实测**(`applied=0 / meta_visible=13 / rejected=10`(1/8/1),非 2026-07-29 ground) |
| post-D 模拟 | candidate tree hash 与**当前 live** hash 是否不同 | **freeze 当前 live hash**(`0daa6222...`);每次 live 部署后须重新 freeze |
| replica/compiler agreement | 整段退役 | 删 |
| inventory | 12 → **10 项**断言,各 freeze 其 note | freeze 各自 note |

## 三、保留 V3.1 的其他动作(继承,不重写)

V3.1 PROPOSAL.md v3.1 commit `62f5f9f` 下列动作在本 v3.1.x 中**逐字继承**(只换 frozen 值,不换动作面):

| V3.1 节 | 动作 | v3.1.x 处理 |
|---|---|---|
| §四 A.2(1) | preflight / current-state 测量改为实测,不 freeze 历史值 | **继承** |
| §四 A.2(2) | post-A 模拟走 `measure_post_a(records[:15])` | **继承**(frozen 值换成本 §零 的实测) |
| §四 A.2(3) | `phase_matrix_probe.py:272` 三值解包 `(live_hashes, by_form)` tuple | **继承** |
| §五 frozen surface 重整 | 5 类 expectation 整下表(本 v3.1.x §二 表新增一行) | **继承 + 增行** |
| §六 C | 退役 replica agreement(扩删除面 6+5=11 项) | **继承** |
| §七 D | wiring_spec_probe 模块级 CV 导入 + `EQUIVALENCE_CLASSES` + `_resolve_alias` + `probe_byte_equivalence` FAIL + 模块级 fail-closed + 删 skipped 字样 | **继承**(V3.1 §十五.1-3 闭环 G1/G2/G3) |
| §八 E | `EXPECTED_MIGRATION` #9/#10/#11/#12 rebaseline 2785/2787/2788/2864 | **继承** |
| §九 F | changeset_v2 期望重置 `{overlay:12, batch-redaction:1}` + 显式 kind + `EXPECTED_UNKNOWN_LEGACY=1` + live hash `0daa6222...` + 注释勘误 | **继承**(V3.1 §十五.4 闭环 G4) |
| §十 执行步骤 | 1-9 步 | **继承 + 改 dry-run 期望**(见 §四) |
| §十一 回滚总览 | `git checkout HEAD -- ...` | **继承** |
| §十二 闭环账本 | 14 条 Codex 反对闭环表 | **继承 + 加 2 行**(本 v3.1.x §六) |
| §十三 不动的事 | 不改 compile_view / 不动账本 / 不 push 等 | **继承** |
| §十四 引用 | 引用 V3.1 PROPOSAL.md + peer-chat:4486/4490/4495/4499/4501/4502 | **继承 + 加 peer-chat:4503** |

## 四、执行步骤(V3.1 §十 改写,dry-run 期望改)

执行签生效后:

1. `git status` + `git diff` 确认本仓干净;
2. 记录三个 probe 文件的**执行前 blob sha1**(`git rev-parse HEAD:<path>`):phase/wiring/changeset,入收据;
3. 改 `phase_matrix_probe.py`(本 v3.1.x §一 改动 1-6 + V3.1 §四 A.2(1)(2)(3) + §五 + §六 C.2),**先 dry-run**:
   - `python phase_matrix_probe.py` → **期望**:
     - `phase_0_entries == 31`(现仓实测,不 fail)
     - `phase_A_measured.compiler_result == {"applied": 0, "meta_visible": 13, "rejected": 10, "view_lines": <4506>}`
     - `phase_A_measured.compiler_rejections == {preimage_unresolvable_and_entry_self_inconsistent: 1, after_hash_mismatch: 8, preimage_only_under_eol_variant: 1}`
     - `phase_A_measured.g1_legacy == {overlay: 10, batch-redaction: 1}`
     - `phase_A_measured.g1_explicit == {re-pin: 1, line-pointer-rebase: 2, line-pointer-measured: 1, canonical-migration: 8}`
     - `phase_A_measured.g1_unmatched == 0`
     - `phase_A_measured.g2_invalid_historical == C2.EXPECTED_INVALID_HISTORICAL`(2 字段)
     - `assertion_inventory` 含 **10 项**
     - **`replica_agreement_today` 字段在 report JSON 中完全不存在**
     - **`failures == []`,rc=0** ✓(V3.1 此处 rc=1 已校正)
4. 改 `wiring_spec_probe.py`(V3.1 §七 D.2 + §八 E.2),dry-run → rc=0(WARN 一行:key 命名差异,byte equivalence 自检 0 drift);
5. 改 `changeset_v2_probe.py`(V3.1 §九 F.2),dry-run → rc=0(`g1_unmatched_legacy == 1`);
6. **仓外 scratch worktree** 跑正向 / 反向 rename 演练(V3.1 §七 D.3 项 1/2/3 + 项 4),用 `git checkout HEAD` 复原;
7. 三 probe 再次 dry-run,全 rc=0、`failures==[]`;
8. `git add` + `git commit -m "..."`(commit msg 含三文件精确改动 + dry-run 输出摘要 + 执行前后 blob sha1);
9. 出【续帧收据】于 `peer-chat.jsonl` + 账本,记入本提案的所有 dry-run sha1 + 收据帧 id + commit sha。

## 五、回滚(继承 V3.1 §十一)

```bash
git checkout HEAD -- \
  proposals/correction-view-unwired-v0.1/evidence/phase_matrix_probe.py \
  proposals/correction-view-unwired-v0.1/evidence/wiring_spec_probe.py \
  proposals/correction-view-unwired-v0.1/evidence/changeset_v2_probe.py
```

三行复原;FINDING 与 PROPOSAL.md v3.1 / PROPOSAL.v3.1.x.md 不动(它们是分析,不是修复)。
**注意**:`git checkout HEAD -- ...` 会把 `phase_matrix_probe.py` 回滚到 V3.1 前的版本(applied=8 旧 frozen),不再 rc=0,这是预期回滚——回滚意味着放弃 V3.1.x 的结构选择恢复 V3.1 的不可执行状态。

## 六、闭环账本(给 Codex 复核的承重清单,新增 2 行)

继承 V3.1 §十二 14 行 + 新增:

| 来源 | 反对要点 | 本 v3.1.x 处置 | 落地节 |
|---|---|---|---|
| peer-chat:4503 (1) | V3.1 `EXPECTED_POST_A_APPLIED=8` 与真源不符;实测 `applied:0 / meta_visible:13 / rejected:10`(canonical-migration 按 `compile_view.py:244-247` 不进 applied) | frozen `EXPECTED_POST_A_APPLIED` 改 `0`;新增 `EXPECTED_POST_A_META_VISIBLE=13`;新增 main() 校验块;§零 structural choice = path B(meta_visible) | §零 + §一 改动 1/3/4 + §二 |
| peer-chat:4503 (2) | V3.1 archived rejection codes `6/8/1` 与真源不符;实测 current codes `1/8/1`(`preimage_unresolvable_and_entry_self_inconsistent:1 / after_hash_mismatch:8 / preimage_only_under_eol_variant:1`) | frozen `EXPECTED_POST_A_REJECTIONS` 改 `{1/8/1 with current named codes}`;§五 表注 line 119 同步移除"freeze archived hash"措辞(本 v3.1.x §一 改动 5) | §一 改动 2/5 + §二 |
| peer-chat:4503 (3) | phase baseline rc=1 = V3.1 death-line 命中;须先使 scratch baseline rc=0 再重跑 baseline + G1-G4 | §四 执行步骤 3 改 dry-run 期望为 `applied=0 / meta_visible=13 / rejected=10`(1/8/1),rc=0 | §四 |
| peer-chat:4503 (4) | V3.1 mutation 1/2/3/4 因 baseline 已非零未继续 | 继承 V3.1 §七 D.3 mutation 项 1/2/3/4 演练面;baseline rc=0 后照原路径重跑 | §四 步骤 6 |

注:peer-chat:4503 是 Codex 对 V3.1 成文稿的【反对·V3.1 phase simulation contract 仍不可执行】;V3.1 §十五.1-4 G1/G2/G3/G4 的 wiring/changeset 闭环不受本 v3.1.x 影响,逐字继承。

## 七、本 v3.1.x 不动的事(边界,继承 V3.1 §十三)

- 不改 `compile_view.py`;不改 `triage_probe.py`;不改 `hash_convention_probe.py` /
  `eol_pointer_probe.py` / `txn_shape_probe.py`。
- 不改 `peer-chat.jsonl` / `peer-chat.corrections.jsonl`;不改任何账本文件。
- 不 push(签后由 Codex 复核执行 push);不 deploy;不发外部消息。
- 不 register 新目标(`goal:classifier-void-only-path-anchoring` 仍是 ACTIVE 直至本提案闭环)。
- 双签之外不执行——任何"先跑跑看"都须收据化、且只在仓外 scratch 工作树跑。
- **额外**:`PROPOSAL.md` v3.1(commit `62f5f9f`)逐字保留,作为本 v3.1.x 的历史 anchor;supersession 通过 `PROPOSAL.v3.1.x.md` 这一新文件表达,不通过改写 v3.1 内容实现。

## 八、引用

- 本 v3.1.x supersede 的 V3.1:`proposals/classifier-source-31-row-boundary-v0.1/PROPOSAL.md`(v3.1 commit `62f5f9f`,frame `wf-20260824-021442-68a562`)
- 本 v3.1.x 文件:`proposals/classifier-source-31-row-boundary-v0.1/PROPOSAL.v3.1.x.md`
- 实测脚本(主仓直接跑,tempfile 不污染):`.scratch-verify-phaseA.py`
- 实测结果:applied=0 / meta_visible=13 / rejected=10(1/8/1);g1_legacy={overlay:10, batch-redaction:1};g1_explicit={re-pin:1, line-pointer-rebase:2, line-pointer-measured:1, canonical-migration:8};g1_unmatched=0;g2_invalid_historical=C2.EXPECTED_INVALID_HISTORICAL(2 字段);view_lines=4506
- V3.1 拒签本版:`peer-chat.jsonl:4503` time `2026-08-24T11:27:14+09:00`(frame `wf-20260824-022022-bcccef`,Codex 收据 `proposals/bounded-scheduler-v0.1/impl/round-notes/wf-20260824-022022-bcccef.md`)
- Codex G1-G4 验收面:`proposals/bounded-scheduler-v0.1/impl/round-notes/wf-20260824-020318-1b2ee7.md`(继承,不受本版影响)
- V3.1 闭环账本:V3.1 PROPOSAL.md §十二
- FINDING(不变):`proposals/classifier-source-31-row-boundary-v0.1/FINDING.md`
- register 帧:`frame:wf-20260823-135809-39990f`;event `0a9433bb-b445-4503-bfab-e509aeebc3d5`
- 观察员原始指令:见 `proposals/classifier-source-31-row-boundary-v0.1/` 的 FINDING.md 与 register 帧