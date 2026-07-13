# EXP-6 / P3-S1-M0b — 义项载体是不是完整循环态:bundle 升主介入 + 坐实 reframe

状态:**冻结(2026-07-04 项目方授权冻结;RUN_ID=exp6-s1-m0b-v1;Claude 起草 → Codex 补机械判据 → Claude 复核发现阈值锚点算术错误(10/16 实为小米 6/8+苹果 4/8 非"各 6/8")且苹果 surface 在收紧判据下边缘 → 项目方采纳 per-surface 裁决 → Claude 据此修订;冻结前零加载零实现,冻结后允许 Codex 开始 GPU 官方 run 脚本与执行)。**
上位:`../ROADMAP.md` P3 状态线;接 EXP-5/S1-M0(exit=substrate_diffuse,Claude 审计 reframe 为介入点错误)。
前身裁决:`exp5_s1_m0_audit#2026-07-04`——recurrent-only swap 0/16(低于香蕉噪声地板 2/16),但 recurrent+conv bundle 12/16(gain 12-22 nat)。
审计更正(2026-07-04):S1-M0 的 bundle flip **已采单次 fluency 且 passes**(swap 续写流畅、source target 现于续写),`deterministic.enabled=true`;仅 **determinism R=3 显式重跑** skip。故 reframe 证据比 M0 审计初述更扎实,但 R=3 复现仍必补。
理论定调:carrier 是构造非发现(元寂 line16);义项载体=完整 gated-delta 循环态而非我们预设的一半,是"构造非发现"的又一应验。

## 0. 一句话

S1-M0 证伪了一个我们从 S0 起就默认的假设:**状态级融合的介入点 = linear 层 recurrent state(那 24MB)**。
数据说:只换 recurrent 态义项纹丝不动(0/16),把 conv 态一起换才翻转(12/16)。M0b 做三件事:
**(1) 把 recurrent+conv bundle 从诊断升为主介入,补齐 M0 skip 的 R=3 复现,坐实"义项态可迁移";
(2) 加 conv-only 对照,把载体归属定位到 recurrent / conv / 联合;
(3) 用能杀死自己的退出码——若 bundle flip 在 R=3 下不复现、或不迁移到 holdout,reframe 被打回,substrate_diffuse 字面读法(P3 降级)重新上桌。**
这不是 M0 的重跑(M0 机械判决无误),是换被测介入点后的新一刀。

## 1. 性质:坐实一个 reframe,且让它能被证伪

M0b 检验 S1-M0 审计提出的假设 **H_bundle**:义项信息可通过完整 gated-delta 循环态(recurrent+conv)因果迁移。
这是**我(Claude)提的假设,M0b 必须能杀死它**——所以退出码含 `transfer_not_reproducible` 与 `bundle_diffuse`(reframe 失败,回到 P3 降级)。
仍是**最小化**:只加一个对照(conv-only)分离载体,不一次引入线索词位置控制(那留 M0c/M1)。
**承认 confound**:bundle flip 可能是 conv 搬运末 4 token 义项线索的近因痕迹(conv kernel=4),非义项抽象载体——
M0b 用 conv-only 对照给出第一层分离,但**不主张**完全排除近因(H_conv_recency vs H_conv_carrier 的完全判别留 M0c)。
**允许输**:bundle 不复现或不迁移 holdout 是诚实坏消息,那样 substrate_diffuse 的字面降级读法成立,如实报。

## 2. 被试、介入点与语料(复用 S0/M0 冻结件)

```text
被试      GPU 上的 Qwen3.5-4B(torch fallback,无 FLA;环境钉死同 M0,见 §6)。
介入面    每 linear 层完整循环态 = recurrent_states [1,32,128,128] + conv_states [1,8192,4](bf16,S0 实测)。
          M0 只换前者(0/16);M0b 主介入换二者 bundle,并加 conv-only 对照单换后者。
三路 swap  ·recurrent-only:M0 已证 0/16,作已知基线复算(锚定对比,不重新论证)
          ·conv-only(新):只换 conv_states,recurrent 保持宿值 → 测 conv 单独作用
          ·recurrent+conv bundle(主判据):M0 旧松阈值 12/16;收紧阈值(§3)Claude 复算=10/16=**小米 6/8 达标 + 苹果 4/8 不达标**
           (Codex 锚点"各 6/8"算术有误已订正;苹果义项对边缘:2 对栽在 fruit-2 强宿 target、2 对 swap_margin 贴阈值)。
           per-surface 裁决(§5)吸收此 surface 异质,不让苹果一票否决,升为 pass 判据
语料      复用 corpus/s0_probe_corpus.json 冻结件(sha256=bdd79a1d85a912b0ffc4500b7c5e55c0215b13ee94938f67ef66827eeb864f5a):selection 8(苹果/小米)
          | holdout 4(长城)| negative 2(香蕉)| physiology 1。不重新出语料。
对齐/公式  完全继承 M0 §2.1:prefix_ids+last_id 对齐、target 倒向公式、义项对枚举(每 surface 8 ordered pair)。
```

## 3. 判据(继承 M0 机械定义,两处收紧)

```text
flip 收紧    M0 的 flip=(swap_margin>=0 and gain>=1nat)在香蕉阴性上假阳性 2/16(base 强抑制对,swap 追平即过 gain 门,
             = Claude 复核预挂点 B)。M0b 冻结阈值为:flip=(swap_margin>=1.0nat and gain>=2.0nat)。
             正裕度要求源 target 实质超过宿 target,不只是追平;不得跑后调参。
per-probe    M0 苹果 company→fruit 2/4 差一票源于单个强宿 target(fruit-2/tid100827)拖累,非方向失败。
             M0b 主判据改 per-direction flip 率的同时,必报 per-probe 明细,并把 selection 判据放宽到
             "每 surface 跨义项 8 对中 ≥6 flip"(surface 级)而非"每方向 3/4",减少单 probe 异质的门噪声;冻结阈值=≥6/8。
selection 聚合 **per-surface 裁决**(项目方 2026-07-04 采纳):每 selection surface(苹果/小米)独立按 ≥6/8 裁决;
             **不要求两 surface 全达标**——≥1 个 selection surface 达标即允许进入 holdout(承认 surface 异质:
             M0 数据苹果 4/8 边缘、小米 6/8 强,苹果不阻断小米坐实)。每 surface 坐实/边缘为必报明细。
holdout      长城 holdout:bundle 主 swap 按 surface 级 ≥6/8 双方向成立,才可判泛化(留出牙,防 selection 特异;
             长城是独立第三 surface,是 per-surface 裁决的跨 surface 泛化仲裁者,见 §5)。
negative     香蕉 source swap 进 apple/millet host:任何会进入退出码判读的 arm(bundle 或 conv-only)中,任一 ordered probe
             满足收紧后的 flip 即特异性牙失败;不得用 surface 聚合稀释阴性假阳性。
determinism  必跑,不 skip(补 M0 缺口):对每个被计入 selection/holdout 判据的 bundle 或 conv-only flip,R=3 重跑
             8-token greedy token ids 全等。deterministic 模式不支持或全局 CuBLAS/torch 复现失败 → blocked_gpu_determinism;
             单个 flip R=3 不全等 → 该 flip 作废并报告。作废致 bundle holdout 不达标 → transfer_not_reproducible;
             作废致 conv-only 不达标 → 不得判 carrier_is_conv_dominant。
fluency      每个 flip 的 8-token 续写按 M0 判据(合法+avg logprob >= 宿基线-5nat);M0b 额外必报:
             R=3 token ids、avg logprob、source target 是否现于 swap 续写及首次出现位置(义项相关性证据,非纯 margin 数字)。
```

## 4. 载体归属(M0b 的核心新增:三路 swap 对比)

```text
recurrent-only  0/16(M0 已证,复算锚定)
conv-only       新测。机械定义:若 conv-only 在同一阈值、同一 surface 级 selection/holdout、同一 negative/R=3/fluency 门下
                独立通过,即视为"≈bundle";若 selection 或 holdout 任一不达标,即视为 conv-only 单独不足。
bundle          主判据

归属判读(必报观察量,喂 M1 介入点定义):
  bundle 高 + recurrent-only 低 + conv-only 低   → 载体=联合态(H_conv_carrier 倾向:需二者协同,非任一单独)
  bundle 高 + conv-only 独立通过同一完整门       → 载体=conv 主导(可能近因痕迹 H_conv_recency,须 M0c 控线索词位置排除)
  bundle 低(不复现/不迁移 holdout)             → reframe 失败,substrate_diffuse 字面成立
近因诚实     conv kernel=4 只覆盖末 4 token。conv-only 高 flip 无法区分"conv 携带短程义项态"与"conv 搬运末4线索词"——
             M0b 如实标注该 confound 未排除,H_conv_recency 完全判别(控制线索词到末尾距离)留 M0c。
```

## 5. 退出码(预注册,互斥)与效度门

```text
前置:per-surface 裁决——义项态可迁移按 surface 独立判定,苹果 4/8 边缘不一票否决;
     每 surface(苹果/小米/长城)bundle per-direction flip、坐实/边缘、R=3、fluency 均必报。
carrier_is_bundle          (pass)**≥1 个 selection surface(苹果或小米)** bundle 达 surface 门(≥6/8)
                           + **holdout 长城也达 surface 门**(≥6/8 双方向)+ 达门 flip R=3 全复现 + fluency 通过
                           + 香蕉任一 probe 不 flip + recurrent-only 与 conv-only 单独均不足
                           → 义项态可迁移跨 selection+holdout 泛化,载体=完整 gated-delta 循环态,
                           放行 S1-M1。附坐实/边缘 surface 明细(承认异质,如苹果边缘小米坐实)
carrier_is_conv_dominant   conv-only 独立通过与 bundle 相同的 per-surface 完整门(≥1 selection + holdout + R=3 + negative + fluency)
                           → 载体 conv 主导;近因 confound 未排除 → 升 M0c(控线索词位置)前不放行 M1
bundle_surface_dependent   ≥1 selection surface 坐实但 **holdout 长城不达标** → 义项态可迁移但**不跨 surface 泛化**
                           (疑 selection 特异/过拟合)→ 不放行 M1;附坐实 surface 清单,升项目方定是否 M0c 扩语料
transfer_not_reproducible  达门 bundle flip 在 R=3 下不复现 → M0 的 12/16 疑为 GPU 抖动;reframe 被打回,
                           substrate_diffuse 字面读法(P3 降级)重新上桌 → 升项目方
bundle_diffuse             **无任何 surface(selection 与 holdout 皆无)** 达 surface 门 → 义项态不可迁移,
                           reframe 不成立,P3 降级(诚实坏消息)
blocked_gpu_determinism    deterministic 模式报不支持或环境级复现失败(区别于 flip 级不复现)→ 修环境重跑
blocked_no_hook            bundle swap 不改前向(logits 不变)→ 假 hook,修 hook 重跑
效度门 invalid_incomplete_report:必报观察量缺一(尤其 determinism R=3 token ids、conv-only selection/holdout/negative、
                           per-surface+per-probe 明细、fluency avg_logprob/source-target-position、swap 前后 logit delta、环境指纹)
                           → run 无效。
```

## 6. 杀死测试(每颗牙演示会失败)

```text
复现牙(补M0缺口) 每个 bundle flip 必过 R=3 8-token 全等;determinism 不许 skip(M0 skip 是本轮头号要补项)。
自证伪牙        reframe 是 Claude 假设,M0b 必须能杀死:transfer_not_reproducible / bundle_diffuse 是真出口,
                不许为保 reframe 放宽 holdout/determinism。
载体诚实牙      conv-only 高 flip 时,不许声称"义项载体已定位"——近因 confound(末4线索词)未排除,如实标 H_conv_recency 待 M0c。
留出牙         载体归属与 flip 方案在 selection 定,holdout 验(继承 S0/M0)。
特异牙         香蕉 bundle swap 不得按收紧判据 flip;引发=无差别扰乱,transferable 主张作废。
钩子诚实牙      bundle swap 改前向(logits 变);M0 已见 max_abs_logit_delta>13,预期真 hook,但仍必验。
边界牙         M0b 零治理算子:只做 swap + 三路对比 + 载体归属,不加竞争/崩溃/吸收。
安全牙         语料仅良性义项消歧(复用 S0 冻结件);不碰安全对齐。
```

## 7. 角色、边界与预注册摘要

```text
角色    Claude=本 spec + 三路 swap 设计 + 载体归属判读 + 锁账审计;Codex=评审 + GPU harness(复用 M0 runner)
        + conv-only 对照实现 + R=3 determinism + 机械度量;项目方=冻结 + 死刑线 + P3 降级/介入点裁定。
非目标  不控制线索词位置(近因完全判别=M0c);不构造/隔离 carrier(=M1,前置=carrier_is_bundle);不加治理算子(=S2);
        不改权重;不碰安全对齐;不装 FLA;不重出语料。

gate    = M0b 坐实"义项载体=完整 gated-delta 循环态(recurrent+conv)"且 R=3 可复现,才放行 M1 在此介入面构造 carrier
decides = carrier_is_bundle(pass,per-surface:≥1 selection+holdout 泛化)| carrier_is_conv_dominant(升 M0c)
          | bundle_surface_dependent(selection 坐实但 holdout 不泛化,升项目方)| transfer_not_reproducible(reframe 打回,升项目方)
          | bundle_diffuse(无 surface 坐实,P3 降级)| blocked_gpu_determinism | blocked_no_hook
validity= 必报观察量缺一(determinism R=3 token ids / conv-only selection+holdout+negative+fluency / per-probe
          / fluency avg_logprob+source-target-position / logit delta / 环境指纹)→ invalid_incomplete_report
probe   = 三路 swap(recurrent-only 基线 / conv-only 分离 / bundle 主判据),坐实 reframe 并定位载体;近因 confound 诚实留 M0c
teeth   = 复现(R=3 不 skip)/ 自证伪(reframe 可被打回)/ 载体诚实(不冒充排除近因)/ 留出 / 特异 / 钩子诚实 / 边界 / 安全
env     = 钉死同 M0:RTX 5090 / Python 3.11.15 / torch 2.8.0+cu128 / transformers 5.12.1 / cuda:0 / torch fallback 无 FLA
          / CUBLAS_WORKSPACE_CONFIG=:4096:8(M0 runner 已证 deterministic CuBLAS 需此)
order   = ①三路 swap 全跑 selection → ②所有可能影响退出码的 arm 跑完整 holdout+negative+R=3+fluency:
          bundle selection 达标必须完整跑;conv-only selection 达标也必须完整跑,否则 invalid_incomplete_report
          → ③载体归属判读 → 裁决
版本    = RUN_ID=exp6-s1-m0b-v1(冻结时定);语料复用 corpus/s0_probe_corpus.json
          sha256=bdd79a1d85a912b0ffc4500b7c5e55c0215b13ee94938f67ef66827eeb864f5a
待冻结  = spec sha256 + GPU 环境指纹 + 收紧 flip 冻结阈(swap_margin>=1.0 / gain>=2.0)+ surface 级冻结判据(≥6/8)
          + per-surface 裁决规则(≥1 selection surface + holdout 泛化仲裁)+ R=3 determinism + 三路 swap 定义
          —— 定值于 PROJECT_CONTROL exp6_s1_m0b_freeze
```
