# EXP-8 / P3-S2-M0 — 钝器态治理:僵/糊诊断与治理净空

状态:**已冻结(2026-07-04;Claude v0.3 复审通过;项目方授权冻结;冻结前零官方实现零官方跑)。**
上位:`../ROADMAP.md` P3 阶梯第 3 级(S2)首刀;前置 = EXP-7 `state_carries_signal`(注册门已兑付,
审计 `exp7_s1b_audit`)。设计输入(全部来自 EXP-7 审计):保留视界 1–8k token、B 被无关填充误导跌破
地板(干扰是真的)、检索在读出级、同窗牙空转教训(本 spec 修复:控制格带非空前缀)。
理论定调:治理算子第一次上身——不僵(旧绑定不垄断)、不糊(更新不毁库)、**不伤健康流**
(`intervention_destructive` = oversplit_healthy 类注册死刑线,永不豁免)。

## 0. 一句话

在"事实中途被更新"的流上,携带态自然回答**新值还是旧值**?(僵/糊/原生代谢三个世界,先诊断)
再问:**一个旋钮的钝器算子**(窗边界态衰减 λ∈{1, 0.5, 0.25, 0})的按需应用,能不能同时赢过
"永远保留"和"永远重置",且不伤"答案在窗内文本里"的健康处理?——治理有没有净空,一跑见分晓。

## 1. 主张与世界判定

```text
组织     每条流恰有一个被探绑定,流分两型:
         UPDATE 型:F1(entity→旧标签)…填充…F2(同 entity 换成新标签)…填充…Q(问"现在")
         STABLE 型:G(entity→标签,从不更新)…填充…Q
         所有事实都在窗外(检索纯靠态);距离取 EXP-7 实测保留区:
         D(F2)=D(G)≈2048(峰区),D(F1)≈4096(仍在视界内 —— F1 必须可被记住,
         否则"没有僵"只是"忘光了",原生代谢主张不成立)
世界判定 (必报观察,基于 λ=1 臂在 UPDATE 型上的选项分布 {current, stale, other}):
         W1 原生代谢  current ≥ 0.5 且 stale ≤ 0.15   —— delta 规则天然完成了取代,僵不是病
         W2 僵        stale ≥ 0.35(高于机会率 0.25)  —— 旧绑定垄断,正是理论要治的病
         W3 糊        其余                            —— 更新碰撞毁库
         (世界判定用**全部 24 条 UPDATE** 的 λ=1 分布——它是纯观察,不涉 λ 选择,无需受 split 约束)
治理主张 H_gov:存在按流型选 λ 的条件策略 π_gov,在预冻结 deterministic split 的 eval 半样本上,
         其综合成绩比最优的单一固定 λ 策略高 ≥ δ_gov,且不触伤健康牙 —— "治理有利可图"
         (检测器怎么造是 S2-M1 的事,本刀只测净空上限:条件按 oracle 流型给,诚实声明这是天花板不是产品;
         但 λ 选择不得用同一批 eval 样本反向挑最优)
```

## 2. 被试、材料与机械化定义

```text
被试     Qwen3.5-4B;RTX 5090;exp7 官方栈钉死(含 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
         进指纹);raw_text_no_chat_template
生成器   扩展 tools/exp7_s1b_generate.py:同虚构实体池、同标签字母表(甲乙丙丁,单 token V1 门)、
         同填充池;新增更新句模板("…换成了/改为〈新标签〉",与 F1 句式不同);冻结种子。
         泄漏规则:entity 恰出现在 F1/F2/Q(UPDATE)或 G/Q(STABLE);旧标签仅 F1、新标签仅 F2;
         填充池字符级不含四个标签字符与任何 entity
窗口     K=256 固定(EXP-7 过门的 K);D 定义同 EXP-7(事实末 token → Q 首 token)
算子     窗边界(T−K)处只治理 linear recurrent_states,λ ∈ {1, 0.5, 0.25, 0}:
         · λ=1:继承 EXP-7 的 A,传入同一份保存态(只含 linear recurrent+conv,full-attention KV 丢弃)
         · λ∈{0.5,0.25}:从同一份保存态深拷贝派生,recurrent_states ×= λ;conv_states 原样复制但不治理,
           因窗 prefill 4 token 内即覆写,报告中必须注明 conv 未参与 λ 轴解释
         · λ=0:继承 EXP-7 的 B,不传任何保存态,使用模型真实 fresh-cache 初始态;不得用手写零态模拟
         四个 λ 臂共享同一份保存态来源 hash(paired,确定性友好);λ=0 记录 fresh-cache endpoint hash/指纹
主试次   UPDATE 24 条 + STABLE 24 条;每条跑 4 个 λ 臂 + C(全文天花板)+ D(仅问句地板)
控制格   健康牙格(修复 EXP-7 同窗牙空转):STABLE 型 12 条,G 放在**窗内文本**,且窗前有
         ≥1024 token 无关填充前缀(保证 λ 臂的前缀态非空、确有东西可衰减)——
         答案在文本里时,任何 λ 都不得损害回答。
         **兼职干扰探针**(必报不判):若控制格上 λ<1 显著优于 λ=1(健康牙是单边门,不咬这个方向),
         即"携带无关态损害窗内阅读"的直接证据——EXP-7 B 抑制现象的对照面,喂 S2 干扰轴设计
读出     同 EXP-7:答案槽对冻结 4 选项 logprob argmax;UPDATE 型选项集必含 {旧标签, 新标签,
         两个未用标签},分布 {current, stale, other} 全量入册;次要观察:8-token 贪心
判据     主试次在冻结种子下按流型与目标标签分层后,用 trial_id 哈希稳定切成 select/eval 两半:
         UPDATE select/eval 各 12,STABLE select/eval 各 12,每半样本内四标签尽量均衡;split 入冻结记录,跑后不得改
         综合成绩 S(π) = mean( UPDATE 型 current-acc, STABLE 型 acc )
         π_gov 只在 select 半样本上按 oracle 流型选 λ_UPDATE 与 λ_STABLE;官方裁决只看 eval 半样本:
         S_eval(π_gov) − max_λ S_eval(π_λ) ≥ δ_gov = 0.15(等价 eval 24 题净胜至少 4 题);
         π_λ = 单一 λ 用于所有 eval 流;max_λ 可在 eval 上取最大,作为保守强基线;
         π_gov 所选各 λ 均须通过健康牙。全样本表只作描述性报告,不改裁决
         世界判定阈:见 §1(基于 λ=1 的 UPDATE 分布)
确定性   R=2:全部臂 logprob 与贪心 token ids 逐位重现
```

## 3. 退出码(预注册,互斥,按序判定,对结果格全划分)

```text
① blocked_gpu_determinism / blocked_no_hook(λ 缩放不改 logits = 假钩)/ blocked_env
② invalid_instrument      仪器牙失败(见 §4:天花板牙 / 地板牙 / 泄漏牙)→ 不判任何 H;点名牙与数值,
                          修语料/生成器后经项目方授权重跑
③ invalid_incomplete_report 必报观察量缺一 → run 无效
④ intervention_destructive **注册死刑线**:每一个 λ<1 都触伤健康牙(答案在窗内文本时损害回答)
                          → 钝器治理在此基质上是破坏性的;S2 钝器线关停,M1 手术刀成为必经;
                          如实回写 ROADMAP,不洗绿
⑤ state_ops_profitable    治理门通过(≥1 个 λ<1 过健康牙,且 split 后条件策略在 eval 赢固定策略 ≥ δ_gov)
                          → 治理有净空;放行 S2-M1(检测器:把 oracle 条件换成自读出信号)
⑥ native_supersession     W1 且治理门不过(λ=1 已近全局最优)→ 器官在此尺度自带代谢
                          (delta 规则天然取代旧绑定)——诚实好消息;S2 轴心转向干扰/糊
                          (EXP-7 B 抑制指向的方向),M0 的僵病假设在此尺度证伪
⑦ blunt_ops_insufficient  其余(W2/W3 且无 λ 策略过门,但算子未全灭健康牙)→ 钝器无效但无害;
                          M1 出袋(手术刀的价值此刻从推测变为已证需求)
```

## 4. 牙(每颗演示会失败)

```text
天花板牙   C 臂 UPDATE 型 current-acc ≥ 23/24 且 STABLE 型 ≥ 23/24(按型判)——
           文本层的取代语义必须成立("现在"问法有效),否则题坏 → invalid_instrument
地板牙     D 臂跨全部主试次池化(n=48):正确数 ≥ 20/48(acc≥0.4167)才失败 —— 机会率 0.25 下
           假失败率≈0.84%(19/48 约1.84%,17/48 约7.04%,已校准;池化不按格,EXP-7 教训)
           → invalid_instrument
健康牙     控制格(答案在窗内文本 + 非空无关前缀态,n=12)按 λ **以计数判**:
           correct(λ=1) − correct(λ) ≤ 2(单边损害门;λ 比 λ=1 更好不算伤健康;
           ≤2/12≈0.167,对齐计数粒度,EXP-7 审计教训——小数阈在 1/12 粒度下会名不副实)
           ——伤健康流的 λ 不得进入 π_gov;
           全部 λ<1 触伤 → 退出码④。此牙同时修复 EXP-7 同窗牙空转:前缀强制非空,有真实咬合面
钩子诚实牙 λ=0.5 与 λ=1 在答案槽 logits 必须可测地不同(缩放确实生效);λ 臂间共享保存态的
           hash 一致性入册
无调参牙   λ 集合/δ_gov/阈值/n/选项集冻结后不动;世界判定阈冻结后不动
泄漏牙     §2 泄漏规则由生成器机械执行并在 build 报告中给字符级校验数;违规 → invalid_instrument,
           点名 leakage_tooth 与违规字段
预算牙     60 条流(UPDATE 24 + STABLE 24 + 健康 12) × (1 边界 prefill ≈2–5k + 6 短臂) × R2,
           预估低于 EXP-7 单晚;超 2 倍升项目方
安全牙     全部虚构良性内容;不碰安全对齐
```

## 5. 必报观察量(缺一即 invalid_incomplete_report)

```text
per-trial per-λ {current, stale, other} 选择与 logprob;C/D 臂全量;健康牙格 per-λ 明细;
冻结 split 明细(select/eval trial_id);世界判定三率(λ=1 UPDATE 分布);
S_select(π_λ) 全表、π_gov 的 λ_UPDATE/λ_STABLE 选择、S_eval(π_λ) 全表 + S_eval(π_gov);
eval 净胜题数与 δ_gov 判定;paired 胜负表(λ 间两两,
描述性 Wilson 区间);R=2 token ids;共享保存态 hash;生成器种子/语料/spec/runner sha;环境指纹;
D(F1)/D(F2) 实测 token 距离(须落在 §2 设计区间 ±10%,超出入报)
```

## 6. 角色、顺序与冻结件

```text
角色    Claude = 本 spec + 世界判定阈与治理门设计 + 锁账审计;Codex = 机械评审(重点:λ 缩放实现、
        共享态 paired 结构、健康牙格几何、成本核)+ 生成器扩展与 runner + GPU 官方 run;
        项目方 = 冻结 + 死刑线裁定
顺序    ①Codex 机械评审 → ②修订定稿 → ③项目方冻结(spec+生成器+种子+语料 sha+环境指纹入
        PROJECT_CONTROL#exp8_s2_m0_freeze)→ ④runner + dry-run → ⑤官方 run → ⑥Claude 锁账审计
        → ⑦裁决回写 ROADMAP;若 ⑤/⑥ 与 P4-M1 均出裁决 → 合流联合评审照两仓 ROADMAP 执行
非目标  不造检测器(oracle 条件是诚实的天花板测量,产品化检测 = S2-M1);不做子空间手术(M1);
        不碰 full-attention KV;不改权重;不用聊天模板;corpus-v2 仅 main_probes(若引用)
RUN_ID  exp8-s2-m0-v1(冻结时定)
```
