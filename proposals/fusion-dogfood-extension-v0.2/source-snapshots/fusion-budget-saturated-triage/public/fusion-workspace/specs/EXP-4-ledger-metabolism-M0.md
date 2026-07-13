# EXP-4 / P4-M0 — 账本代谢微缩版:给活着的记忆装消化系统,第一刀

状态:**修订草案 v2.1(2026-07-03 Claude 起草;同日 Codex 评审 6 findings(2 P0 / 3 P1 / 1 P2),Claude 核验全数采纳修订;Codex 追加隔离环境与 hash 审计口径;待 Claude 提名清单 + 项目方冻结;冻结前零代谢事件)。**
上位:`../ROADMAP.md` P4 dogfood 线;`../理论基石与工程方向.md`;ai first 定调(账本=现役慢环身体)。
解剖真源:账本 decision `weilan-anatomy#2026-07-03`(四层解剖:FIFO 读出病因、双底座零使用、A/B 免复制设计)。
理论地位:牙(反复活/留出/先组后稳/允许输)=已验证纪律,搬用;**MDL 门=未验证假设第一次实弹检验,允许输**(理论=trace 非 holder,2026-07-03 项目方定调)。

## 0. 一句话

微澜的账本已经病了:35 条语义记忆纯 append、代谢器官(supersedes/disposition)长而未用、
读出是 `[-8:]` 纯时间截断——**冗余是 FIFO 读出的必然分泌物**(旧结论想留在 projection 里,
唯一策略是反复重写自己)。M0 问一个最小问题:**三个代谢算子(吸收/死亡/崩溃)作用于这本真实账本,
能不能在不丢任何活信息的前提下减负,且行为读出不降?**这是微澜机制第一次治理真实生产数据,
也是自指闭环第一段实装:方法治理方法自己的记忆。

## 1. 性质:单机制单裁决,最小化先行

M0 **只测代谢算子的安全性与有效性**,不测 q 竞争读出(那是 M1,见 §7 非目标)。
理由:《分散但趋同》第五环自己的教训——零件太多每个都是 confound;EXP-1.5 两负的教训——
一次押一个假设。M0 的代谢候选**提名是人工的**(Claude 从解剖出的冗余中提名),**门是机械的**
(MDL 字节 + 行为不变式),裁决是行为的(A/B)。提名偏差风险如实声明,由门与死刑线兜底。
**允许输**:若代谢丢信息或行为变差,那是关于算子设计的诚实坏消息,回炉,不粉饰。

## 2. 被试与双臂(承重;A/B 在派生层,不复制账本)

```text
被试      fusion-program scope 语义账本冻结快照(2026-07-03,35 条:15 decision/11 fact/
          5 lesson/2 constraint/2 open_question;jsonl 逐文件 sha256 冻结)。真实生产数据,非合成语料。
分层事实  semantic jsonl=观察层(append-only,永不改写——所有代谢事件都是新 append);
          projection=义项层(确定性 reducer 派生)。代谢不违反 append-only,两层各守其分。
双臂      FIFO 臂:沙箱副本 A(纯快照,零事件)→ 现状 reducer(decisions=[-8:]+16KB 顶)→ projection_F
          代谢臂:沙箱副本 B(同一快照 + 代谢事件 append)→ 同一 reducer → projection_M
          同一 reducer、同一预算——唯一自变量=代谢事件本身。
隔离执行  (P0)代谢事件**不写真实 method-state**:把 method-state 快照复制为两个沙箱副本
          A/B(复制后与真实账本逐文件 sha256 三方对账=同源起点)。运行时优先显式设置
          WEILAN_METHOD_HOME=<sandbox>/method-state;若改用 CODEX_HOME=<sandbox>,则必须先确认
          WEILAN_METHOD_HOME 未设置或已清空(weilan_trace.py 的 state_root 优先级为
          WEILAN_METHOD_HOME > CODEX_HOME/method-state)。receipt 必报两者环境值。代谢命令与
          两臂 projection 重建全部在各自沙箱内执行;真实 fusion-program 账本全程**只读**。
          run 结束沙箱整体留档为产物。
读出预算  16KB projection / 8 decision 槽位是**真实守恒预算**(非模拟):代谢的收益
          就用这个预算的字面字节数与槽位占用来度量,MDL 不是比喻。
```

## 3. 三个代谢算子(M0 版:人工提名 + 机械门 + append-only 落账)

```text
吸收(并冗余)   提名:两条在读出中可互换的冗余条目(解剖已见活标本:S0 系列 5 条互相重叠)。
                机械门(全过才许并):①合并条目 append + supersedes=[a,b](血统纯记账);
                ②合并后 projection 字节数下降(MDL 字面化);③m2 重推导过:仅凭合并条目,
                答题手能答出 a、b 各自的关键事实(冻结时按条目定题)。
死亡(杀被否证) 提名:被后续证据否证的条目。机械门:①否证证据必须引用账本内既有条目/收据
                (不许凭感觉杀);②(P0)必须存在承载否证结论的 **active successor 条目**,
                且重建 projection_M 后核验其**可见**(在 decision 槽内)——只剔除、不让答题手
                看到"现在信什么"的死亡非法(否则 m1 陷阱题无可见证据,测的是运气不是算子);
                ③disposition state 事件 append(历史保留,死=退出读出竞争,非删除)。
崩溃(拆过泛化) 提名:管辖过宽、被新证据打脸的条目。机械门:①拆出条目 append + supersedes=父;
                ②m2 反向过:拆出各条合起来覆盖父条目全部关键事实;③反复活不变式(见 §5)。
落账纪律        所有代谢事件走 memory-consolidate / memory-disposition 现有命令(解剖:双底座
                实现完整零使用——M0 就是它们的首次实战,但只打在沙箱副本 B 上,见 §2),
                不新建写路径。run_id 审计落位(P2,现有结构无 run_id 字段,M0 零代码改动):
                consolidate 用 --tag "run:exp4-m0-v1";disposition 把 "run:exp4-m0-v1" 写入
                --source 首位;审计按此前缀机械提取事件清单。
```

## 4. 行为读出(铁律 b/c:治理必须在行为上兑现,不看内部指标自嗨)

```text
任务集   N=20 道 forced-choice(EXP-2f 基建复用):关于项目真实历史/决策/事实的选择题,
         从账本 35 条内容出题,题目+锁定答案冻结时 sha256 定值。
m1 探针  死结论陷阱:题库内含 ≥3 道陷阱题,**死结论做成固定选项**(canonical id,选项文本
         取死条目 summary 原文),正确答案=successor 新结论(死亡门②保证其在 projection_M
         可见)。判据纯机械(P1):**answer.choice 命中死结论选项即违例**,不检测自由文本"引用"。
m2 探针  重推导:题库内含 ≥3 道只能靠被合并/被拆条目的原始信息作答的题;
         代谢臂答错 → 丢活信息,直接触发死刑线。
同手牙   出题手=Claude(锁答案先于任何答题);答题手=隔离会话(Codex 或独立 agent 实例),
         **只见 projection,不见完整账本、不见本 spec、不见对方臂答案**;评分=机械比对锁定答案。
输出契约 (P1)答题手输出固定 schema:每题仅 {"qid": ..., "choice": "<option_id>"},**不收自由
         文本 basis**(保持 EXP-2f 纯机械精确匹配);缺字段/非法 option_id → 该题记 invalid_answer
         入账(不计对错,invalid_answer>10% 触发 blocked_engineering)。
双臂同题 两臂各答同一套 20 题;主指标=答对率差(M−F);辅指标=projection 字节数、decision 槽位占用。
```

## 5. 杀死测试(每颗牙演示会失败)

```text
先组后稳牙  FIFO 臂 churn=0 是**尸体的稳定**(《分散但趋同》第六环),不算赢。pass 前置:
            代谢臂完成 ≥K 次真实代谢事件(K 冻结定,建议 吸收≥3 + 死亡≥1 + 崩溃≥1),
            事件不足 → 不产出 pass(没做手术就没有手术结论)。
反复活牙    合并产物在本 run 内不得再被合并(supersedes 链深 ≤1);死条目内容不得被新条目
            原文复述超过引用限度(那是借尸还魂)——违者该事件非法,run 记 invalid。
留出牙      两层冻结(P1):**spec 冻结(运行前)锁定题目生成规则**——seed、覆盖配额
            (每个吸收/崩溃事件 ≥1 道 m2 题、每个死亡事件 ≥1 道 m1 题的配额算法)、选项构造
            规则、输出 schema;**题库+锁答案=事件后派生件**,按冻结规则生成后立即 sha256
            记入 receipt(与运行前预注册件分层,防事后裁剪指控)。答案锁定先于答题手接触,
            题目不泄露臂别。
预算牙      两臂 reducer 与预算完全一致;不许给代谢臂放宽 16KB/8 槽(那改变了被测对象)。
边界牙      M0 零 q、零读出改造:reducer 一行不改(改读出是 M1);代谢事件之外不动账本。
真实性牙    被试=真实账本快照,不许为凑 K 值注入合成冗余条目;提名清单冻结时定死。
```

## 6. 退出码(预注册,互斥)与效度门

```text
metabolism_safe_and_lean   (唯一 pass)≥K 事件 + projection 字节净降 + m1 零违例 + m2 全过
                           + forced-choice 答对率 M ≥ F − ε(ε 冻结定,建议 0.05=一题差)
metabolism_neutral         事件足额执行,行为无差异且字节无净降——诚实的"白忙",算子设计回炉
metabolism_lossy           (死刑)m1 任一违例(死结论复活)或 m2 任一失败(丢活信息)
                           或 M < F − ε——代谢毁了或没治住记忆,回炉(P1:m1 明确纳入负出口)
blocked_engineering        管道/隔离/锁答案任一故障,不产出裁决,修复重跑
效度门 invalid_incomplete_report:必报观察量缺一 → run 无效不产出裁决(同 S0 语义)。
必报观察量:两臂答对率+逐题对照、m1/m2 逐题结果、代谢事件清单(供审计逐件验门)、
            successor 可见性核验(死亡门②)、两臂 projection 字节/槽位、supersedes/disposition 链、
            沙箱 hash 审计(执行前:A/B/真实账本同源逐文件 hash;执行后:A 零变化,B 仅允许
            run_id=exp4-m0-v1 事件路径变化)、WEILAN_METHOD_HOME/CODEX_HOME 环境值、
            invalid_answer 计数。
停止规则:两负(lossy/neutral 各算一负)→ 不出第三版,算子设计升级为项目方决策(继承 EXP-1.5 教训)。
```

## 7. 角色、边界与非目标

```text
角色    Claude=本 spec + 代谢提名清单 + 出题锁答案 + 锁账后审计;Codex=spec 评审 + 管道实现
        + 隔离答题手运行 + 机械评分;项目方=冻结 + 死刑线 + 提名清单批准(防提名者既当医生又当法官)。
非目标  M0 不改 reducer(q 竞争读出=M1,前置条件:M0 pass);不做自动提名(触发器/冲突自动检测
        =M1+);不动 frame/评测/演化平面(那是 WeilanSkillEvolution 的辖区,若代谢算子需要
        进 weilan_trace.py 的改动,走演化仓提案流程,不直接改部署件);不碰其他 scope 的账本;
        16KB/8 槽预算不动。
应急    若 memory-consolidate/disposition 现有命令有实现缺陷(零使用=零实战检验),修复走
        演化仓提案,修复本身不算代谢事件;修复后重跑,不改判据。
```

## 8. 预注册摘要

```text
gate    = P4-M0 是第一刀:证明代谢算子在真实账本上安全(不丢活信息)且有效(减负不降行为),
          才放行 M1(q 竞争读出替代 FIFO)
decides = metabolism_safe_and_lean(唯一 pass)| metabolism_neutral | metabolism_lossy(死刑)
          | blocked_engineering(不产出裁决)
validity= 必报观察量缺一 → invalid_incomplete_report(run 无效,补齐重跑)
reports = 两臂逐题对照、m1/m2 结果、代谢事件清单+门核验、字节/槽位收支、血统链、快照 hash
probe   = MDL 门(字节降)=未验证假设第一次实弹检验,允许输;行为不变式(m2)为其兜底
teeth   = 先组后稳(K 事件前置)/ 反复活(链深≤1+禁借尸还魂)/ 留出(两层冻结:规则运行前冻,
          题库=事件后派生件即锁)/ 预算(两臂同 reducer 同预算)/ 边界(零读出改造+沙箱隔离,
          真实账本全程只读;显式审计 WEILAN_METHOD_HOME/CODEX_HOME 指向)/ 真实性(不注入合成冗余)
order   = 快照冻结+沙箱 A/B 复制三方对账 → 提名清单批准 → 代谢事件执行(仅沙箱 B)+逐门核验
          (含 successor 可见性)→ 按冻结规则出题+锁答案(派生件 hash 入 receipt)
          → 隔离双臂答题(choice-only)→ 机械评分 → 退出码 → Claude 锁账审计
版本    = RUN_ID=exp4-m0-v1(冻结时定);解剖真源引账本 weilan-anatomy#2026-07-03
待冻结  = 运行前定值(PROJECT_CONTROL exp4_m0_freeze):spec sha256 + 账本快照 sha256(逐 jsonl)
          + Claude 提名清单 sha256(缺失则不得冻结/不得执行)+ 题目生成规则(seed/配额/选项构造/
          输出 schema)+ K(建议 3+1+1)+ ε(建议 0.05)+ N(建议 20)。运行中派生件
          (sha256 入 receipt 非 freeze):题库+锁答案。
```
