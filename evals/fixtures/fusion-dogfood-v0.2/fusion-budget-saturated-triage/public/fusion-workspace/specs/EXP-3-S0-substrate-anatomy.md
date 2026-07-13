# EXP-3 / S0 — 基质解剖与冒烟：那 50MB 递归态摸不摸得到

状态：**已冻结（2026-07-03 v2.1：Codex 评审 6 findings 全采纳 + 探针语料冻结件 corpus/s0_probe_corpus.json + Q3/q 机械判据补齐；项目方同日授权"补语料即冻结开跑"；冻结参数与 sha256 见 PROJECT_CONTROL `exp3_s0_freeze`）。**
上位：`../ROADMAP.md` P3 基质线（主攻）；`../理论基石与工程方向.md` §四（火/炉分工）、§六（三环）。
前身：`PROPOSAL-dual-line-redesign.md` §3 S0 草图（基于 9B 侦察）——本件据 4B 实测重写并精确化。
架构事实真源：账本 `memory:778f…`（`778b369f`，读 config.json + safetensors index 核实，2026-07-03）。
帧：`wf-20260703-020016-96784d`（fusion-program / main）。

## 0. 一句话（理论出处：元寂 守恒/帧流/自我=读出；《分散但趋同》§一 快慢分离；感知层讨论=多模态归属）

微澜前四个实验都在**模型外面**治理文本记忆（LLM 的笔记本）；P3 第一次问：治理能不能介入**模型内部的连续状态**（LLM 的身体）。
Qwen3.5-4B 的 24 个 linear attention 层各携一块**固定大小递归态**（合计 12.58M 元素；bf16 实测 25.2MB / fp32 50.3MB，见 §2），不随流长增长、被新 token 覆写——
这物理地实现了理论的守恒（硬预算非模拟）、帧流（持续演化的基质非文本重建）、自我=读出（行为是状态投影）。
**S0 不测任何治理机制**（那是 S1/S2）。S0 只回答一组 go/no-go 事实：这块态**摸得到吗、读得出吗、写回去模型还活吗、里面的义项结构够不够"个体化"**。
摸不到，整条 P3 状态线当场停；摸得到，微澜第一次从"管笔记本"够到"摸身体"。

## 1. S0 的性质：这是一道门，不是一个主张

S0 **没有**可证伪的机制主张（不主张竞争/崩溃/吸收有效）。它预注册的是**一组互斥的工程事实裁决** + **一组必须如实入账的观察量**。
理由（元寂总原则 #3/#4）：先证明基质"可被真实接管并独立验证"，再谈机制。跳过这道门直接上 S1/S2 =在没确认能读写状态的地基上盖楼。
**允许输**：S0 就可能死（linear attention 的 CPU kernel 可能不存在或态无法干净物化）——那是关于硬件/实现的诚实事实，不是理论失败，如实记 blocked。

## 2. 基质精确定义（承重；linear 与 full 必须分开对待）

```text
模型        D:/models/Qwen3.5-4B（model_type=qwen3_5,混合注意力,instruct 版带 chat_template）
32 层构成   24 linear_attention（SSM/gated-delta:A_log/conv1d/dt_bias/in_proj_{qkv,a,b,z}/out_proj）
            + 8 full_attention（每 4 层一个,full_attention_interval=4;标准 q/k/v/o + q_norm/k_norm,GQA kv=4）
介入点      **仅 linear 层递归态**——每层 [1, 32 value头, 128 key_dim, 128 value_dim] = 524288 元素(batch=1 每流;批量随 batch 线性放大);
            × 24 层 = **12.58M 元素**(承重数:守恒论证系于元素数与覆写语义,与 dtype 无关)。字节量随加载 dtype 变:
            config mamba_ssm_dtype=float32 推导 50.3MB;dtype=auto 实载实测 cache 为 **bfloat16=25.2MB**(2026-07-03 env probe,
            该配置项未落到运行时 cache——expected/actual 必须分开,见 §3①③)。另有小 conv1d 短卷积态(kernel=4,实测每层 [1,8192,4]),一并抓。
不属基质    full 层是 KV cache（随上下文增长,不守恒,append-only 完美参照）——**S0 只登记其存在,不介入**。
理论映射    linear=快守恒代谢态、full=慢 append-only 参照 → 架构自带《分散但趋同》§一 的快慢分离,
            不是我们强加的。微澜的竞争/崩溃/吸收若成立,舞台是这 50MB,不是笼统的"模型状态"。
读取语义    "递归态"指**逐 token 更新、生成时被 use_cache 携带的那个状态对象**（类 Mamba/SSM cache),
            不是训练态 chunked scan 里只瞬时存在的中间量。S0 头等风险=确认它作为持久张量真实可取。
```

## 3. 四层解剖（按成本从低到高；便宜且零风险的先跑，贵的看证据再决定）

```text
① 骨架层（纯静态,safetensors 流式扫描,不加载不推理,~分钟级,零风险）
   枚举全部张量:每层 linear/full 归类核对(对齐 config layer_types);从 config 推导 **expected_state_spec**
   (shape+dtype 假设——静态扫描证明不了运行时 cache 的真实 shape/dtype,真值只由③生理层捕获落盘);
   核对 language_model(426 张量) / visual(297 张量) 的干净边界;顶层 mtp.*(15 张量,multi-token-prediction
   辅助头)登记为第三类:非基质非视觉塔,标准文本前向不经过,S0 只登记不介入。产物:骨架清单 JSON。
② 组织层（纯静态,逐层权重统计,~分钟级,零风险）
   每层权重的范数/稀疏度/异常值分布,找冗余候选(为将来更深手术备证,S0 只出证据不动刀)。产物:组织统计 JSON。
③ 生理层（前向,贵,吃 CPU;S0 的真风险都在这）
   执行环境**钉死**(2026-07-03 实测跑通 stack;换版本=环境变更,须重探测+修订记录):Python 3.11.9 / torch 2.5.1+cpu /
   transformers 5.12.1 / safetensors 0.8.0;加载类 AutoModelForCausalLM→Qwen3_5ForCausalLM;torch_dtype="auto"
   (实测 cache 为 bf16;若数值问题定位到 dtype,允许 fp32 复跑,如实记录,不改判据);态对象=
   past_key_values.layers[i].recurrent_states / conv_states(config `linear_attention` ↔ 模块名 `linear_attn`,映射见骨架 naming_map);
   **文本塔加载(跳过 visual 权重)**;固定探针 prompt 前向跑通;cache 抓全 24 层 linear 态(逐层 **actual** shape/dtype 落盘,
   与①expected 并列报告:shape 不符=疑抓错对象,按钩子诚实牙查;dtype 不符=如实记录,以 actual 为准,不算 fail);
   测 decode tok/s;状态存盘→恢复→逐 token 复现后续生成(恒等往返)。产物:生理报告 + 状态快照样本 + tok/s。
④ 手术层（第一刀=切视觉塔,纯减法,低风险;更深的刀 S0 不做,留 ② 证据授权）
   视觉塔(model.visual,独立 24 层 ViT,经 image/video token 汇入文本嵌入)与文本塔干净分离;
   仅载文本塔即等效"切除"(M-RoPE 退化为标准 RoPE,文本路径不依赖视觉);验证纯文本前向与①边界一致。
   产物:手术第一刀确认(管道走通+减负)。**视觉塔权重留盘不删**(感知帧阶段请回,见 §7 非目标)。
```

## 4. 三个硬问题（S0 必须回答；②③产物喂给它们）

```text
Q1 摸得到吗   env 起得来 + 文本塔载得进 + 前向跑得动(kernel 在 CPU 上存在) + tok/s 可测。→ 决定 blocked_env / blocked_no_cpu_path
Q2 读写得干净吗 24 层 linear 态作为持久张量取得到 + 恒等往返逐 token 复现生成。→ 决定 blocked_no_hook / substrate_reachable
Q3 里面有个体吗 喂最小义项对(苹果=水果 ctx vs 苹果=公司 ctx,语料=corpus/s0_probe_corpus.json 冻结件),看状态差异是
              **局部**(集中在少数头/层)还是**弥散**(摊满全部子空间)。**机械定义**:义项对 prefill 终态之差 Δ
              逐(层,头)取 Frobenius 范数得能量分布,报 HHI(份额平方和)+ top-8 头能量占比;判读基线=香蕉阴性对
              (同义项异表述)的同指标——义项对浓度不显著高于阴性基线 → 测的是噪声,不许报"局部"。
              → 不进退出码,是**必报观察量**(局部=头即天然 carrier,量子化白送;
              弥散=S1/S2 需先做子空间分解才有"个体")。理论第一原则(界限清晰差异才成立)能否在本基质落地,看此条。
```

## 5. q 候选的预注册探针（只测"可定义否",不主张守恒成立）

```text
候选定义   某 linear 单元(层/头)对当前义项的**解释份额** = 消融归因:把该单元的递归态清零(或替换为均值),
           测 target 首 token(义项已定续写,target 语义见语料文件)的对数概率跌幅;跌幅 = 该单元的压缩份额。
预算纪律   全头扫不可行(24 层×32 头=768 次消融,每次一整回前向,CPU 地板 ~20s → 数日)。**粗到细两阶段**:
           pass1=24 个 linear 层整层消融 × selection;取层级份额 top-3 层;pass2=仅 top-3 层内 32 头逐头消融
           (96 次)× selection;holdout 只复算已选单元,不再全扫。
为何是它   这是《分散但趋同》§二"压缩份额 q=受限生成的影子价"的**状态版本**,不是从聚类嫁接的外部量。
S0 只验    (a) **稳定**=同义项异表述变体间,单元份额排序一致(selection 内 Spearman ρ≥0.5,且 holdout 上不反号;
           确定性 CPU 前向下"同输入重复一致"是平凡判据,不采)、(b) **非退化**=份额分布既非均摊(top-8 头合计
           份额 ≥50%)也非单头独吞到平凡(无单头 >90%);
           退化/不稳 → 报 q_undefinable_on_substrate(不是 blocked,是给 S2 的诚实坏消息,S2 设计据此调整或降级)。
纪律       消融归因的头选择必须在**留出义项对**上验证,不得在选头那批上自证(防循环选择,见 §6 局部性诚实牙)。
```

## 6. 退出码（预注册，互斥）与杀死测试（每颗牙演示会失败）

```text
退出码（S0 = 门,只有一个 pass 出口,其余皆 blocked 类不消耗裁决）:
  substrate_reachable       env 起 + 文本塔载 + 前向跑动 + 24 层 linear 态全抓 + 恒等往返复现生成 → 放行 S1
  blocked_env               Python/transformers 载不动 qwen3_5(实测 KeyError 类) → 修环境重跑
  blocked_no_cpu_path       linear attention 无可用 CPU kernel / 前向报错或不产出 → 修实现或换路径重跑
  blocked_no_hook           递归态取不到持久张量,或恒等往返无法逐 token 复现 → 态不可干净读写,修 hook 重跑
必报观察量（不进退出码;缺一 → **invalid_incomplete_report**:效度门,run 无效**不产出裁决**,补齐重跑——
同 EXP 系列 oracle 日志校验的语义,区别于 blocked 类工程事实裁决）:
  tok/s 实测 + S1/S2 算力可行性旗标(低于地板 → 标 compute_tight,警示但不阻断 S0)
  24 层 linear 态逐层 shape/dtype;局部性浓度指数(Q3);q 可定义性(§5);手术第一刀确认;骨架+组织统计

杀死测试:
  钩子诚实牙  抓到的态必须是前向**真正在用**的那个:扰动它→生成改变;清零它→生成退化。
              若"抓到的"是不影响前向的死副本 → 假钩子,blocked_no_hook(不许拿死副本冒充可读)。
  复现牙      恒等往返(存→恢复→续跑)必须逐 token 复现:判据=续跑 N=32 token 的 token id 序列**全等**
              (机械可判;logit 差异只记录不判);不复现 → blocked_no_hook,不硬编不假装。
  地板牙      固定 prompt 测 decode tok/s;linear kernel 若退化成朴素循环慢到不可用,如实记 compute_tight,
              **不许换更小模型或删层来伪造达标**(那改变了被测对象)。
  局部性诚实牙 Q3 浓度指数在**留出**最小义项对上算,不得在选头那批上自证(防循环)。
  边界牙      S0 跑**零治理**:除恒等往返与单头消融探针外,不衰减/不重置/不重组任何态;
              实现若为"效果"去改态 → 越界(那是 S1/S2),不算 S0。
  安全牙      语料仅良性义项消歧(苹果/小米/长城);管道**不含**任何 abliteration/去审查/权重改写;
              不碰安全对齐(不在因果链、动了只添混淆变量,见 §7)。
```

## 7. 角色、边界与应急条款

```text
角色    Codex=环境搭建 + 扫描/前向/hook 脚本 + 机械度量;Claude=本 spec + 解剖解读 + 手术方案 + 锁账后审计;
        项目方=冻结 + 持死刑线 + 手术授权(更深的刀)。（分工继承:大代码 Codex,设计/评审 Claude。）
仪器    复用 EXP 系列:最小义项对语料、forced-choice 探针、审计流水线;状态健康不发明新度量,行为读出现成。
应急①   若生理层见状态动力学**贫瘠**(instruct 版 mode collapse 致态变化平淡、竞争无花样)→
        换 **base(对齐前预训练)检查点**重跑生理层(需另下载,报项目方)。**这是方法学选择,不是拆对齐**——
        base 分布更肥、更适合观察原始语义动力学(理论出处:要看竞争就别用被压平的分布)。
应急②   若 Q2 blocked_no_hook 但 HF 实现有 SSM cache 对象 → 优先走 cache API 而非 forward hook(实现细节,不改判据)。
非目标  不微调/不 LoRA/不改权重(硬件死刑+理论不需要);不碰安全对齐(宪法§5:安全=内部反垄断非对齐外部目标,炉不改火);
        不删视觉塔权重(留盘,感知帧阶段请回——多模态属感知层,义项竞争先定义在语义单元);
        S0 不做任何治理算子;不为支线推翻主线预注册;不把"摸身体"包装成 AGI 路径本身(它是守恒/帧流两基石的可证伪测试)。
```

## 8. 预注册摘要

```text
gate   = S0 是门:证明 linear 递归态(12.58M 元素)可达/可读写,才放行 S1;个体化(Q3)与 q 可定义性(§5)=必报设计输入,不作放行条件
decides= substrate_reachable(唯一 pass) | blocked_env | blocked_no_cpu_path | blocked_no_hook(皆不消耗裁决)
validity= 必报观察量缺一 → invalid_incomplete_report(run 无效,不产出裁决,补齐重跑)
reports= tok/s+算力旗标、24 层态 expected vs actual shape/dtype、局部性浓度(Q3)、q 可定义性(§5)、手术第一刀、骨架+组织统计
probe  = q 候选=消融归因(压缩份额的状态版),S0 只验稳定+非退化,不主张守恒成立;语料=corpus/s0_probe_corpus.json(冻结件:
         physiology 1 条 + selection 8 条(苹果/小米)+ holdout 4 条(长城)+ 阴性对照 2 条(香蕉))
teeth  = 钩子诚实(扰动即变)/复现(恒等往返逐token)/地板(不换小模型伪造)/局部性诚实(留出验证)/边界(零治理)/安全(不拆对齐)
order  = ①骨架 ②组织(纯扫描先跑,零风险)→ ③生理(前向,真风险)→ ④手术第一刀(切视觉塔=纯减法+多模态处理)
铁律   = (a)状态读取须证明是前向真用的量(钩子诚实牙),绝不信死副本;(d)这是机制跃迁(摸身体),不是参数堆积
版本   = 执行 RUN_ID=exp3-s0-v1(冻结时定);架构事实引 memory:778b369f
预跑   = 2026-07-03 冻结前探测(s0_env_probe/s0_skeleton/s0_tissue)=**回填输入,非官方 run**:env continue、
         态 [1,32,128,128]/层 dtype=auto→bf16 24MiB、tok/s 0.0505(torch fallback 无 fast path,compute_tight 预期)。
         官方 S0 裁决 run 于冻结后全四层重新执行,预跑产物只用于定参,不用于裁决。
冻结   = 冻结仪式先于官方 run(EXP-2f 教训);spec sha256 + 探针语料 sha256 定值于 PROJECT_CONTROL `exp3_s0_freeze` 字段
         (sha256 不写入本文件,避免自引用);tok/s 地板 0.5=**compute_tight 旗标阈,非阻断门**(S1 预算输入;
         由 S1 最小探针套件预算反推;实测 0.0505 → 官方 run 预期带 compute_tight)
```
