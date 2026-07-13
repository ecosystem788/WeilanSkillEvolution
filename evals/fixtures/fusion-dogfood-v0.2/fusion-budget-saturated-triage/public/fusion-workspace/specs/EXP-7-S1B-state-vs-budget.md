# EXP-7 / P3-S1-B — 态记忆 vs 文本预算:支线注册门的非平凡版

状态:**已冻结(2026-07-04;Claude 起草;Codex 机械评审 v0.2:流/Q 边界、上下文上限硬检查、态注入契约、
corpus-v2 硬依赖、δ 统计口径;Claude 复核修订 v0.3:退出格全划分(新增 invalid_instrument)、
地板牙池化校准(原按格判 8 格假失败率 81.4% → 池化后 0.6%)、同窗牙阈对齐计数粒度、选项集范畴契约;
项目方确认冻结;冻结前零官方实现零官方跑)。**
上位:`../ROADMAP.md` P3 新阶梯第 1 级;修正 `PROPOSAL-dual-line-redesign.md` §3-S1 的原注册
(原文"携带态 vs 重放全文"在确定性模型下 ill-posed:全文重放逐位重建同一状态,行为差恒为零,
或在真实核路径上只测得 prefill/decode 浮点噪声——两种都无意义;非平凡形式 = **预算版**)。
理论定调:受限生成——价值只在预算饱和时显形(《元寂》line 33-34;EXP-4 审计边界 (c) 同型;
与 P4-M1 构成**合流实验**,见两仓 ROADMAP)。

## 0. 一句话

同一条流单次流过后,冻结上下文窗 K:**携带窗边界处线性层循环态**(arm A)与**重置态**(arm B)
在完全相同的 K 窗文本上回答"事实在窗外"的问题。态若真是记忆器官,A 必须可测地更准,
且 A−B 随事实距离 D 的**保留曲线**是门控 delta 遗忘的第一张行为级生理图;
答不赢 = `state_redundant`,支线按原注册死刑线收缩。

## 1. 主张与退出结构

```text
H_state  线性态(recurrent+conv)在窗边界携带窗外的行为相关信息:
         ≥1 个 D>K 网格点上 acc_A − acc_B ≥ δ 且 acc_A ≥ 0.5
H_null   态是文本的冗余缓存 → state_redundant(支线收缩为效率声明,M1 降为可选)
副产     保留曲线 acc_A(D,K) − acc_B(D,K):态的自然遗忘率(状态代谢的基线生理参数,喂 S2)
边界诚实 本实验测"信息保持",不测"义项载体"(载体归属是 M0b/M1 的事);
         读出用受控 forced-choice,不做 margin-越线式载体声明(吸收 corpus-v2 caveat-a)
```

## 2. 被试、材料与机械化定义

```text
被试     Qwen3.5-4B;GPU RTX 5090;exp6 官方栈钉死(Python 3.11.15 / torch 2.8.0+cu128 /
         transformers 5.12.1 / CUBLAS_WORKSPACE_CONFIG=:4096:8 / deterministic / TF32 off);
         raw_text_no_chat_template(同 S0/M0b 惯例)
语料输入 corpus-v2 主语料为硬依赖:corpus/s1_probe_corpus_v2.json
         sha256=aa2232d0ecd845d30e5da212ea47310d9bf4a4a56b2e4e08413176966af73c20;
         只许读取 main_probes,legacy_anchors 禁入题库/判据/pair plan。corpus-v2 用于抽取
         surface/sense/target token 与良性中文义项词表;本实验的虚构绑定文本由冻结生成器另行生成。
选项集   每道题的 4 选项必须是**同一范畴的单 token 集**(如 4 色/4 器物/4 方位),范畴模板由生成器
         冻结;corpus-v2 只作词表来源,不决定选项集结构 —— 防选项范畴不齐使正确项可被语义合理性
         猜出(该风险由地板牙兜底,但兜底代价是整跑作废,故在生成器层先行阻断)。
流构造   每条 trial 分成 stream_body 与 Q,二者不得混名:
         · stream_body = 事实句 F + 漂移填充(顺序固定,无重复提及)
         · trial_text = stream_body + Q
         · F:虚构绑定陈述("〈虚构地名〉的〈实体〉〈属性〉是〈目标〉"),目标 ∈ 冻结 4 选项集,
           每选项恰 1 token(V1 门,同 corpus-v2 惯例);绑定由冻结种子随机指派 → 模型先验不可知
         · 填充:多主题良性中文,由冻结种子模板池生成;生成器强制字符串级不包含 F 的实体/目标
         · Q:"〈地名〉的〈实体〉〈属性〉是"(止于答案槽)
距离 D   = F 末 token 到 Q 首 token 的 token 数;窗口 K = 允许重放的 stream_body 尾部文本 token 数;
         T = Q 首 token 在 trial_text 中的位置;所有切片均以 T 为边界,Q 只拼接一次
网格     K ∈ {256, 1024} × D/K ∈ {0.25, 2, 8, 32}(D/K=0.25 为同窗牙用,事实在窗内);
         最长流 ≈ 34k token;每格 n = 16 条独立流(独立实体/独立绑定)
上限牙   冻结前必须读取模型 config 的 max_position_embeddings/model_max_length 等上下文上限,并 dry-run
         1 条最长 trial_text。若最长 trial_text 超限或 full prefill 不可执行,冻结前必须下调最大网格;
         不许在官方 run 中让 C 臂因上下文上限失败。
四臂     A 携带:prefill(trial_text[0:T−K]) 得到前缀 cache;从前缀 cache **只提取全部 linear 层
                recurrent_states + conv_states**,丢弃/不传递任何 full-attention KV;随后以该 linear
                state 为初值、原 position_ids 续 prefill(trial_text[T−K:T]+Q) → 读答案槽
         B 重置:同 token ids、同 position_ids prefill(trial_text[T−K:T]+Q),但 recurrent_states 与
                conv_states 必须使用模型真实 fresh-cache 初始态(不是复用 A,也不是未验证的手写零态)
         (A/B 的 full-attention KV 都只由 K 窗 prefill 现场产生;唯一差异 = 窗边界 linear state 初值)
         C 天花板:prefill(trial_text),无预算 —— 验题可答性
         D 地板:prefill(仅 Q)—— 验先验不可知
读出     答案槽处对冻结 4 选项 token 做 logprob argmax(forced-choice,机会率 0.25);
         次要观察(必报不判):8-token 贪心是否吐出目标及首现位
判据     cell(D,K) 通过 = acc_A − acc_B ≥ δ=0.25 且 acc_A ≥ 0.5(n=16;δ 是预注册 effect-size gate,
         不是显著性声明)。报告必须同时给 paired stream 级 A/B 胜负表(A正B错、A错B正、同错、同对)
         与 Wilson 区间;如需统计语言,只作为描述性辅助,不改预注册退出码
确定性   R=2:全部四臂 logprob 与贪心 token ids 逐位重现;不一致 → blocked_gpu_determinism
```

## 3. 退出码(预注册,互斥)

```text
state_carries_signal   ≥1 个 D>K cell 通过 + 全部牙过 → 支线注册门兑付,放行 M1/S2;附保留曲线
state_partial_horizon  仅 D=2K cell 通过(8K/32K 全败)→ 有限视界:态是短程记忆器官,如实记,
                       升项目方定 S2 值不值得(短视界仍可支撑窗边界治理,但主张要收窄)
state_redundant        无 D>K cell 通过 → 原注册死刑线兑现:支线收缩为效率声明,M1 降为可选,
                       结论回写 ROADMAP(诚实坏消息,不洗绿)
invalid_instrument     任一仪器牙失败(同窗等价牙 / 地板牙 / 天花板牙)→ **不判 H_state**(既不
                       carries_signal 也不 redundant——仪器坏了不等于态不存在);点名失败的牙与数值,
                       修语料/生成器后经项目方授权重跑。此码保证退出格对结果空间全划分(M0b 教训)
blocked_gpu_determinism / blocked_no_hook(A 臂态初值不改前向 = 假钩,钩子诚实牙失败归此)/ blocked_env
invalid_incomplete_report:必报观察量缺一(per-cell per-stream 四臂 logprob、R=2 token ids、
                       同窗牙/地板牙/天花板牙数值、生成器种子与语料 sha、环境指纹)→ run 无效
```

## 4. 牙(每颗演示会失败)

```text
同窗等价牙   D/K=0.25(事实在窗内)时 |acc_A − acc_B| ≤ 0.125(= 2/16,对齐 n=16 的计数粒度;
             原 0.1 在粒度 1/16 下实际含义是 ≤1/16,过紧)—— A 的优势若在同窗仍存在,
             说明测的是初值扰动混淆,不是窗外记忆;触发 → invalid_instrument,不落 state_redundant
地板牙       D 臂(仅问句)**跨全部 trial 池化**(n=128)acc ≤ 0.35 —— 防绑定可被先验猜出。
             校准依据:按格判(n=16,≥6/16 即超)单格假失败率 0.190,8 格至少一格假失败 0.814,
             必然误咬;池化后(≥45/128)假失败率 0.006。per-cell 地板 acc 必报不判。
             触发 → invalid_instrument
天花板牙     C 臂每格 ≥ 15/16(显式计数,等价 0.9375;quality gate 故意按格判——某格 2 题不可答
             就该拦下那格的题)—— 否则题太难,测的是能力不是记忆;触发 → invalid_instrument
钩子诚实牙   A/B 两臂在答案槽的 logits 必须可测地不同(否则态初值没被真正注入);
             另做 single-stream probe:同一 K 窗下替换为随机其他前缀 linear state 时 logits 也应变化,
             用来证明 runner 确实消费初值,但该 probe 不参与退出码
无调参牙     δ/网格/n/选项集冻结后不动;跑后只许按预注册判据判读
语料牙       流语料由冻结种子生成器产出,语料+生成器+种子三 sha 入冻结;corpus-v2 只许 main_probes
             (消费边界,继承 corpus_v2_final_freeze 下游契约),legacy_anchors 出现在题库即 invalid
上下文牙     最长 trial_text 的 token_len、模型上下文上限、dry-run 结果必须入 freeze record;
             若官方 run 中发现超限,exit=blocked_env,不得静默删格
预算牙       GPU 时数入册;粗估 128 流 × (1 全 prefill + 3 短 prefill) × R2 ≈ 单晚级,超 2 倍升项目方
安全牙       填充与事实全为良性虚构内容;不碰安全对齐
```

## 5. 角色、顺序与冻结件

```text
角色    Claude = 本 spec + 生成器模板设计 + 锁账审计;Codex = 机械评审(重点:臂对齐/position_ids/
        态初值注入的实现可行性、判据自洽、成本核)+ 生成器与 runner 实现 + GPU 官方 run;
        项目方 = 冻结 + 死刑线裁定
顺序    ①Codex 机械评审本 spec → ②修订定稿 → ③项目方冻结(spec sha + 生成器 sha + 种子 + 语料 sha
        + 环境指纹入 PROJECT_CONTROL#exp7_s1b_freeze)→ ④runner 实现与 dry-run → ⑤官方 GPU run
        → ⑥Claude 锁账审计 → ⑦裁决回写 ROADMAP;若 state_carries_signal 且 P4-M1 亦出裁决,
        触发合流联合评审(两仓 ROADMAP 已注册)
非目标  不做义项载体声明(M0b/M1 的事);不做态干预/治理算子(S2);不改权重;不装 FLA;
        不用聊天模板;不在本实验里调 corpus-v2 的任何东西
RUN_ID  exp7-s1b-v1(冻结时定)
```
