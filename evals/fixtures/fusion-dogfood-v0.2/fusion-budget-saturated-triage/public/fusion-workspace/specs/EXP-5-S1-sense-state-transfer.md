# EXP-5 / P3-S1-M0 — 义项能不能随状态搬家:跨义项态交换第一刀

状态:**冻结(2026-07-04 项目方授权;Claude 复核通过;RUN_ID=exp5-s1-m0-v1;冻结后允许 Codex 开始 GPU 官方 run 脚本与执行;本次冻结只改状态/簿记,不改实验判据)。**
上位:`../ROADMAP.md` P3 状态线;`../理论基石与工程方向.md` §四/§六;接 EXP-3/S0(exit=substrate_reachable)。
前身裁决:S0 审计 `exp3_s0_audit#2026-07-03`(弥散非基线伪影;q_undefinable 分不清 H_probe/H_substrate;状态携带行为因果义项信息但不在(层,头)坐标系局部化)。
理论定调:carrier 是构造非发现(元寂 line 16 量子化=构造行为);理论=trace 非 holder;牙可搬,q/MDL 等机制=未验证假设(2026-07-03 项目方定调)。
GPU 环境:`gpu-env-ready#2026-07-03`(RTX 5090 / torch 2.8.0+cu128 / transformers 5.12.1 / torch fallback 无 FLA;S0 smoke replay exact + 38 tok/s)。

## 0. 一句话

S0 证明了 24 层 linear 递归态**摸得到、读写干净、有行为因果的义项信息**,但那信息**不在(层,头)坐标系里局部化**——
天然 carrier 没白送。S1 的问题从"治理哪些头"改写为"**义项能不能被构造成可操纵的单元**"。
但在构造子空间(SVD/探针,那是 M1)之前,先问一个更便宜、更能证伪的问题:
**把"苹果=公司"语境的 linear 态整个搬进"苹果=水果"的语境,续写会不会倒向公司义?**
搬得动 → 义项信息在 linear 态里**可因果访问**(S0 的 q_undefinable 是 H_probe,探针太粗),M1 去精细隔离;
搬不动 → 要么义项真弥散不可及(H_substrate),要么它根本不在 linear 态里(在 full 层)——两种都是状态级融合的硬坏消息,诚实报。

## 1. 性质:最小化第一刀,测"可迁移"不测"可隔离"

S1-M0 **只测义项信息在 linear 态里的可因果迁移性**,不构造子空间、不隔离 carrier(那是 S1-M1)。
理由(项目一贯纪律 + 《分散但趋同》第五环):零件太多每个都是 confound;先用最粗、最强、最便宜的因果操作(整态交换)敲一个 go/no-go,
再决定要不要投入精细的子空间构造。**承认 confound**:整态 swap 若切换义项,可能是"移植了整段语境记忆"而非"移植了义项 carrier"——
S1-M0 **不主张**已隔离义项,只主张"义项信息在这个态里、可被因果操纵";隔离留 M1(§7)。
**允许输**:swap 不切换义项是关于基质的诚实事实,不是失败;它可能把 P3 状态线导向降级或改介入点,如实报。

## 2. 被试、介入点与语料(复用 S0 冻结件)

```text
被试      GPU 上的 Qwen3.5-4B(torch fallback,无 FLA;环境见 §6 钉死)。
介入点    主介入只换 linear 层递归态 past_key_values.layers[i].recurrent_states,S0 已验证可 hook。
          conv_states 保持宿语境原值,避免把短卷积局部 n-gram 记忆混进"递归态搬家"主张;
          recurrent+conv bundle 只作 selection 诊断观察量,不进入 pass/exit 判据。
          full 层 KV cache 只在 §4 诊断实验里作对照 swap,不是治理对象(状态级融合只治 linear 态)。
语料      复用 corpus/s0_probe_corpus.json 冻结件(sha256=bdd79a1d...,不重新出语料):
          selection 8(苹果/小米,定 swap 方案+最小充分层集)| holdout 4(长城,验迁移)
          | negative 2(香蕉,特异性对照)| physiology 1(恒等往返+tok/s+GPU 确定性基线)。
义项对    同 surface 跨义项对(如 苹果-公司 ctx ↔ 苹果-水果 ctx),target 首 token 判义项倒向(公司向/水果向)。
```

## 2.1 机械定义(冻结前必须随 spec 一起锁定)

```text
prompt 切分       对每条 probe: ids=tokenizer(prompt, add_special_tokens=False);
                 prefix_ids=ids[:-1], last_id=ids[-1], target_id=tokenizer(target_continuation)[0]。
状态对齐          源态=source prefix_ids 前向后的 cache;宿态=host prefix_ids 前向后的 cache;
                 swap 后只用宿的 last_id、cache_position/position_ids/attention_mask 继续一步,
                 读取 next-token logits。源/宿 prompt token 长度不要求相等;位置语义继承宿语境。
linear 主 swap    对选中 linear layer,仅把宿 cache.layers[i].recurrent_states 替换为源 recurrent_states;
                 conv_states、full KV、embedding/weights 均保持宿语境原值。
bundle 诊断       selection 上额外跑 recurrent_states+conv_states 同换,只报告是否与主 swap 符号不同;
                 若 bundle 成而 recurrent-only 不成,记为 conv_confounded_transfer 设计输入,不算 pass。
full-KV 诊断      只在 linear 主 swap 不成时执行。为避免源/宿长度不齐,不整段搬 KV;
                 对每个 full_attention layer,取源 prefix 最后一个 cache 位置的 key/value 向量,
                 写入宿 prefix 最后一个 cache 位置,宿序列长度和 cache_position 不变,再喂宿 last_id。
                 这称为 full-KV terminal swap。若 cache schema 使该替换无法物化或替换后 logits 不变,
                 记 blocked_no_hook(诊断 hook 不完整),不产出 sense_in_full_not_linear/substrate_diffuse 裁决。
target 倒向公式   对有 host target h、source target s 的一次 ordered swap:
                 base_margin = logp_base(h) - logp_base(s)
                 swap_margin = logp_swap(s) - logp_swap(h)
                 gain = (logp_swap(s)-logp_swap(h)) - (logp_base(s)-logp_base(h))
                 flip = (swap_margin >= 0.0) and (gain >= 1.0 nat)。
                 即:swap 后 source target 至少追平 host target,且相对基线推进不少于 1 nat。
义项对枚举        同 surface 两个 sense 各 2 条 probe 时,跑全部 ordered cross-sense pair:
                 A1/A2 -> B1/B2 共 4 次,B1/B2 -> A1/A2 共 4 次,每 surface 8 次。
selection 判据    苹果、 小米 两个 surface 各自两方向都至少 3/4 flip,才允许进入层定位。
holdout 判据      长城 holdout 两方向都至少 3/4 flip,才可判 sense_state_transferable。
negative 判据     香蕉 source -> 苹果/小米 selection host:不得满足上述 flip;若任一满足,特异性牙失败。
流畅性判据        对每个被计为 flip 的 swap,继续 greedy decode 8 token:
                 无 NaN/Inf、token id 合法,且 8 token 平均 logprob >= 宿基线平均 logprob - 5.0 nat。
                 不满足则该 flip 作废;若作废导致 holdout/selection 不达标,不得判 transferable。
钩子诚实          每类 swap 至少一个 selection 正例必须 max_abs(logits_swap-logits_base)>1e-6;
                 若全部 swap logits 不变,blocked_no_hook。
GPU 复现          torch.use_deterministic_algorithms(True),固定 seed=exp5-s1-m0-v1:determinism:v1,
                 同一 ordered swap 重跑 R=3 次,greedy 8-token 序列必须全等;若 deterministic 模式报不支持
                 或 token 序列不全等,blocked_gpu_determinism。
```

## 3. 态交换实验(三段,从强到细)

```text
① 全态 swap（最强因果操作,先敲 go/no-go）
   源:义项 A 语境 prefix 终态;宿:义项 B 语境 prefix 终态。
   操作:用源 recurrent_states 整体替换宿 24 个 linear 层 recurrent_states,从宿 last_id 继续一步;
        按 §2.1 的 target 倒向公式测续写 target 是否从 B 义倒向 A 义。
   判读:倒向 = 义项随态迁移(可因果访问);不倒 = 不可访问(进 §4 诊断)。
② 层定位（若①倒向:义项载体紧凑度）
   按 full_attention_interval 划 8 个 interval block,每组=3 个 linear 层(夹在相邻 full 层之间)。
   先逐 block 单独 swap,按 selection flip 率和 gain 排序;再贪心加入 block,直到 selection 判据成立;
   最后逐个尝试移除已选 block,移除后仍成立则删去。报告 greedy-minimal sufficient block set。
   对入选 block 内逐层复算,报告 layer-level 紧凑度,但不声称全局最小。层集越小 = 义项态载体越紧凑;
   需全 24 层才切换 = 载体弥散(M1 子空间构造更难,但仍可做)。这是必报观察量,不是退出码。
③ 特异性（swap 的因果是义项特异,不是无差别扰乱）
   香蕉阴性:按 §2.1 把香蕉 source 态进苹果/小米 selection host,不得满足 flip。
   流畅性:按 §2.1 的 8-token 平均 logprob 与合法 token 判据;崩=把模型打坏,切换无意义。
```

## 4. 诊断:义项若不随 linear 态迁移,它在哪(服务状态级融合可行性)

```text
若 §3① linear 全态 swap 不切换义项 → 做一次对照:改做 full-KV terminal swap(其余不动,定义见 §2.1)。
  full-KV terminal swap 切换、linear swap 不切换 → 义项信息主要可由 full 层末端参照态因果操纵,不在 linear 递归态。
    含义:状态级融合的介入点(linear 50MB 递归态)选错了——这是对双环架构内环的**重大坏消息**,必须诚实上报。
  两者都不切换 → 义项信息不可通过态交换因果访问(H_substrate 强信号,或信息在嵌入/权重不在 cache)。
这一诊断让 S1-M0 不只回答"义项在不在态里",而是"在不在**我们要治理的那个 linear 态**里"——直接定价状态级融合。
```

## 5. 硬问题(S1-M0 必答)

```text
Q1 搬得动吗   recurrent-only linear 全态 swap 按 §2.1 在 selection+holdout 上特异切换义项
              (holdout 两方向各 ≥3/4 + 香蕉不动 + 流畅 + 复现)?→ sense_state_transferable
Q2 在哪       若搬不动:full-KV terminal swap 切换吗?→ sense_in_full_not_linear（介入点坏消息）| 都不动→substrate_diffuse
Q3 多紧凑     若搬得动:greedy-minimal sufficient block/layer set 多大?→ 必报观察量(喂 M1 子空间构造)
```

## 6. 退出码(预注册,互斥)与效度门

```text
sense_state_transferable   (唯一 pass)recurrent-only linear 态 swap 在 holdout 上按 §2.1 特异切换义项(长城两方向各 ≥3/4
                           + 香蕉不切换 + 流畅性保持 + GPU 复现)→ 义项信息在 linear 递归态可因果操纵,放行 S1-M1
sense_in_full_not_linear   linear swap 不切换、full-KV terminal swap 切换 → 义项在 full 层末端参照态可操纵,不在 linear 递归态;
                           状态级融合介入点需重审(不消耗 M1 授权,升项目方决策:改介入点 or 改架构)
substrate_diffuse          linear 与 full-KV terminal swap 都不特异切换义项 → 义项不可通过本轮态交换因果访问;
                           P3 状态线降级(诚实坏消息,非工程失败)
blocked_gpu_determinism    固定 seed+deterministic 下 swap 结果不可复现(GPU 非确定性未控)→ 修环境重跑
blocked_no_hook            required swap 不改变前向或 full-KV terminal 诊断无法物化(假 hook/诊断 hook 不完整)→ 修 hook 重跑
效度门 invalid_incomplete_report:必报观察量缺一 → run 无效不产出裁决(同 S0/M0 语义)。
必报观察量:ordered pair 逐项 base/swap logprob 与 flip/gain、greedy-minimal block/layer set(Q3)、
            recurrent+conv bundle 诊断、full-KV terminal 诊断对照、香蕉特异性、流畅性度量、
            GPU R=3 复跑一致性、swap 前后 logit 变化(钩子诚实证据)、环境指纹。
```

## 7. 杀死测试(每颗牙演示会失败)

```text
钩子诚实牙    required swap 必须真改前向:swap 后 logits 变(对齐 S0 hook honesty)。全部无效果=假 hook,blocked_no_hook。
复现牙        fixed seed + torch.use_deterministic_algorithms;同一 swap 复跑 R=3 次,8-token greedy id 全等;
              不一致 → blocked_gpu_determinism,不硬编不假装(S0 CPU 确定,GPU 须显式控)。
留出牙        swap 方案 + 最小充分层集在 selection 上定,holdout 上验特异切换;holdout 不迁移=selection 过拟合,
              不算 transferable(S0 那颗咬死假 carrier 的牙原样搬)。
特异性牙      香蕉阴性态 swap 不得按 §2.1 引发 source target 倒向;引发 = swap 在无差别搞乱,transferable 主张作废。
confound 诚实牙 S1-M0 只主张"义项信息在 linear 态可因果迁移",**不主张已隔离 carrier**(整段移植 vs 义项移植的
              confound 明确留 M1);最小充分层集只报为"载体紧凑度"诚实指标,不包装成"找到了 carrier"。
边界牙        S1-M0 零治理算子:只做态 swap + 层定位 + 诊断对照,不加竞争/崩溃/吸收/衰减;
              为"效果"改态即越界(那是 S2)。
安全牙        语料仅良性义项消歧(复用 S0 冻结件);不含 abliteration/去审查/权重改写;不碰安全对齐。
```

## 8. 角色、边界与预注册摘要

```text
角色    Claude=本 spec + swap 实验设计 + 锁账后审计;Codex=评审 + GPU harness + swap/层定位/诊断脚本 + 机械度量;
        项目方=冻结 + 死刑线 + 介入点重审授权(若判 sense_in_full_not_linear)。
非目标  不构造子空间/不训探针/不隔离 carrier(=S1-M1,前置=本件 pass);不加任何治理算子(=S2);
        不装 FLA(用 S0 已验证 torch path);不改权重;不碰安全对齐;不重出语料(复用 S0 冻结件)。

gate    = S1-M0 证明义项信息在 recurrent-only linear 态可因果迁移(不测隔离),才放行 S1-M1(子空间构造/carrier 隔离)
decides = sense_state_transferable(唯一 pass)| sense_in_full_not_linear(介入点坏消息,升项目方)
          | substrate_diffuse(P3 降级)| blocked_gpu_determinism | blocked_no_hook
validity= 必报观察量缺一 → invalid_incomplete_report
probe   = 跨义项 recurrent state 交换(全 linear→层定位→特异性),H_probe/H_substrate 的最强最便宜判别;confound 诚实留 M1
teeth   = 钩子诚实(swap 改前向)/ 复现(GPU R=3 次 8-token 全等)/ 留出(selection 定 holdout 验)/ 特异(香蕉不动+流畅)
          / confound 诚实(不冒充 carrier)/ 边界(零治理)/ 安全(不拆对齐)
env     = 钉死 RTX 5090 / Python 3.11.15 / torch 2.8.0+cu128 / transformers 5.12.1 / cuda:0 / torch fallback 无 FLA
          (理由:S0 钩子诚实牙在 CPU torch implementation 上验证,GPU torch fallback 同代码路径;FLA 藏态+需重验)
order   = ①recurrent-only 全 linear swap(go/no-go)→ [倒向] ②greedy block/layer 定位 + ③特异性 → 裁决;
          [不倒] ④full-KV terminal 诊断 → 裁决
版本    = RUN_ID=exp5-s1-m0-v1(冻结时定);语料复用 corpus/s0_probe_corpus.json(sha256=bdd79a1d...)
冻结定值 = reviewed_content_sha256=05dd48f9274ba77a3bb9ae82d0099587f662c992e34941a01b7da5cb462c578e(Claude 复核内容)
          + frozen_spec_sha256(冻结状态行更新后写入 PROJECT_CONTROL exp5_s1_m0_freeze)
          + GPU 环境指纹 + seed=exp5-s1-m0-v1:determinism:v1 + target 倒向公式(1 nat)
          + R=3/8-token 复现牙 + greedy-minimal block/layer 算法 —— 定值于 PROJECT_CONTROL exp5_s1_m0_freeze
```
