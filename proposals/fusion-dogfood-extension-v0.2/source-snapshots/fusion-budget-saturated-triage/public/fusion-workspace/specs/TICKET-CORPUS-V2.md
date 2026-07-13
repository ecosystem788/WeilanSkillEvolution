# 工单 — CORPUS-V2:强度配平探针语料(给 Codex)

状态:**已冻结(2026-07-04;Claude 起草;同日冻结前评审 4 项发现(P1×2/P2×2)全采纳修订:强控硬门、
main/legacy 消费分层、宿主约束机械修复路径、hash 固定清单;项目方确认冻结;待上传云端配置后执行)。**
依据:`PROJECT_CONTROL.json#exp6_s1_m0b_offline_analysis`(R1–R5 规则的证据与出处),
分析工件 `artifacts/exp6-s1-m0b-v1_source_strength_analysis.md`。
上位:M0b 裁决 `bundle_surface_dependent` 照立;本工单不重判,只为 S1 下一刀(M1 或 S1 行为版)重建语料地基。
纪律:**语料冻结先于下一个实验 spec 冻结**;下一个 spec 引用本语料 sha256。

## 0. 一句话

v1 语料(15 探针)已被证明粒度低于仪器:单探针杠杆三次翻转裁决(fruit-2 拖苹果、banana-nc-2 造假阳、
wall-wall-2 拖 holdout)。v2 = **测量并配平两条噪声轴(源自迫近度 / 宿主开放度)+ 消灭单探针杠杆**。
本工单允许直接使用已租用的 RTX 5090 GPU 执行测量；CPU 仅作为 GPU 不可用时的 fallback,不得混跑生成同一份冻结结果。

## 1. 输入(已备好)

- 候选探针:`corpus/candidates_v2_claude.json`(Claude 已署名交付,含 intended_imminence 标注,超供)。
- 遗留探针:`corpus/s0_probe_corpus.json`(sha256=bdd79a1d…,15 探针)全部自动并入候选池,标 `legacy_v1`。
- 模型:`D:/models/Qwen3.5-4B` 或云端同 sha256 模型目录(同 exp3-s0/exp6 官方 run;`raw_text_no_chat_template`)。
- 执行环境:优先云端 RTX 5090 GPU,沿用 exp6-s1-m0b 官方栈(Python 3.11.15 / torch 2.8.0+cu128 / transformers 5.12.1 / safetensors 0.8.0 / `CUBLAS_WORKSPACE_CONFIG=:4096:8`)；如退回本地 CPU,须单独入册并不得与 GPU 测量混合。

## 2. 测量(每探针两个数,一次前向)

对候选池每个探针 p,在其**自身语境、自身末位**(对齐方式同 M0 §2.1:prefix_ids + last_id,无任何 swap):

```text
I(p) = base logprob(target 首 token)     # 自迫近度(source 侧强度 / host 侧目标自信,同一个量)
H(p) = 末位 next-token 分布的熵(nat)     # 开放度(注册用协变量)
```

- 目标 token 化:`target_continuation` 必须恰为 **1 个 token**,否则该候选淘汰(V1 门,同 run 的 target id 惯例)。
- 确定性:R=2 重测,同一设备/同一 dtype/同一环境下 logprob 与 H 逐位一致；GPU 必须启用 deterministic algorithms 并记录 CUDA/CuBLAS/TF32/dtype 指纹。不一致 → `blocked_env`,报环境指纹。
- 预估成本:~40 候选 × 2 遍单次前向；5090 GPU 应为分钟级到十几分钟级,主要耗时在模型加载与 tokenizer/IO；CPU fallback 仍按数小时级预估。

## 3. 配平规则(冻结于本工单;测量后只许机械执行,不许看数字后改规则)

```text
M        = 全部通过 V1 的 selection 源候选的 I 中位数
源带     selection/holdout 源:|I(p) − M| ≤ 2.0 nat
negative **in-band 负控 ≥ 6**(|I−M| ≤ 2.0;strong control 不计入此数)
强控     **硬门:1–2 个,0 个 = insufficient_candidates。** 判定纯凭实测,与作者标注无关:
         I ≥ (入选 selection 源的 I 最大值) − 1.0 **且** I > M + 2.0(超带向上);
         达标者 >2 个按 I 降序取 2(平票按 id 字典序)
角色归一 候选文件的 role/intended_imminence 只是作者注记,一律不进判定;最终 band_role 由实测 I 归类:
         in-band → negative;达强控线 → negative_strong_control;两皆不达 → rejected(只入报告)
宿主     绝对地板 I(host) ≥ −6.0 nat;各 surface 宿主 I 均值 距跨 surface 总均值 ≤ 1.5 nat;
         H 全员入册;H 最高的两个宿主不得同 surface
宿主修复 约束检查定序:I 地板 → 各格裁选 → surface 均值 → H top-2。任一宿主约束失败:在**违约 surface
         的格内**做确定性单探针替换(取使违约量最小的备选,平票按 id 字典序),每约束至多 4 次替换,
         然后整体重验一轮;仍失败 → insufficient_candidates 并点名约束。**不许临场发明其他修复规则**
格数     配平后每 surface × sense ≥ 4 探针(selection: 苹果/小米;holdout: 长城)
超供裁选 某格超过 4:按 |I − 该格中位数| 升序取 4,平票按 id 字典序 —— 机械规则,零人工挑选
遗留     legacy_v1 探针同测同判,不因 M0b 用过而豁免;达带者以 legacy_flag=true 进 main_probes,
         不达带者进 legacy_anchors 层(跨版本锚,禁入任何 v2 主门);physiology 探针 gate-exempt
         (band_role=physiology,直接进 main_probes)
```

## 4. 交付物

```text
tools/measure_probe_covariates.py    # 测量:候选池 → corpus/probe_covariates_v2.json(I/H/token id/R=2 校验)
tools/build_corpus_v2.py             # 组装:按 §3 规则 → corpus/s1_probe_corpus_v2.json + 淘汰名单及理由
corpus/s1_probe_corpus_v2.json       # schema_version=s1_probe_corpus_v2,**三层显式分离,消费边界不可混**:
                                     #   main_probes{selection, holdout, negative, negative_strong_control,
                                     #               physiology}          ← 下游实验唯一许可消费面
                                     #   legacy_anchors[]                 ← out_of_band_legacy,禁入 v2 判据
                                     #   (rejected 候选不入语料文件,只入 build report 并逐条给理由)
                                     # 每探针字段:v1 基础上增 {imminence_nat, openness_nat, band_role,
                                     #   legacy_flag, included_in_main_gate: bool,
                                     #   exclusion_reason: string|null(included=true 时必须为 null)}
artifacts/corpus_v2_build_report.md  # 测量表 + 带检查 + 宿主修复记录 + 每条淘汰理由 + 环境/设备/dtype 指纹
                                     # + **固定 hash 清单(八项,缺一即 invalid)**:
                                     #   ①specs/TICKET-CORPUS-V2.md ②corpus/candidates_v2_claude.json
                                     #   ③corpus/s0_probe_corpus.json ④corpus/probe_covariates_v2.json
                                     #   ⑤corpus/s1_probe_corpus_v2.json ⑥tools/measure_probe_covariates.py
                                     #   ⑦tools/build_corpus_v2.py ⑧模型 config.json + tokenizer 文件 sha256
                                     # (report 自身 sha256 由冻结时 PROJECT_CONTROL 字段记录,形成链)
```

## 5. 退出码(互斥)

```text
corpus_v2_frozen_ready     全部硬门过(格数 + in-band 负控 ≥6 + 强控 1–2 + 宿主约束),八项 hash 齐,
                           待 Claude 复核带检查 → 项目方冻结(report 自身 sha256 一并入 PROJECT_CONTROL)
insufficient_candidates    任一硬门失败:某 sense 格 <4 / in-band 负控 <6 / **强控 =0** /
                           宿主均值或 H 规则修复 4 次仍败 —— 点名缺哪格哪门,回 Claude 补候选,只补测新增
blocked_env                模型/栈/确定性不可用,报指纹
```

## 6. 牙(每颗演示会失败)

```text
机械裁选牙   测量后改带宽/改规则/人工挑探针 = 违规;规则以本工单为准,改动须项目方点头并留痕
消费边界牙   下游实验 spec 只许引用 main_probes;legacy_anchors 出现在任何 v2 判据/pair plan 里 = 违规
单 token 牙  target 多 token 一律淘汰,不许改 target 迁就(改文本=新候选,重测)
遗留诚实牙   legacy 探针不因"M0b 用过"豁免带检查;banana-nc-2 预期为 out_of_band 或 strong control,如实标
角色牙       Codex 只测量与机械组装;文本作者=Claude;冻结=项目方。管线不得改写 prompt 文本
安全牙       全部候选为良性消歧文本;不碰安全对齐话题
```

## 7. 角色与顺序

```text
Claude  候选文本(已交)→ build report 复核(带检查+文本审计)→ 复核意见入 PROJECT_CONTROL
Codex   measure → build → report(§4)→ 报 exit code
项目方  冻结授权;insufficient 时裁定是否放宽格数(留痕)
顺序    本工单完成并冻结 → 才起草下一个实验 spec(M1 隔离 或 S1 预算行为版,届时另定)
```
