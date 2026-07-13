# EXP-1.5 — 寡头环的另半程:竞争吸收算子(亮的吸收暗的)

状态:**已冻结(2026-07-02 起草,同日按理论校对重写框架,Codex 终核后由项目方冻结)。** 实现与运行(Codex + API oracle)按本冻结件执行。
上位:`../ROADMAP.md` P2 副产待办;双线并行之 API 线;与 P3 基质线(本地)互不阻塞。

## 0. 一句话(理论出处:元寂计划 line 6;《分散但趋同》坑二与"粗化↔细化振荡")

元寂的循环两个方向都合法:**竞争=亮的吸收暗的(粗化/集中),崩溃=裂而更散(细化/分散)**,
活着的签名是两者间的有界振荡。EXP-1 只实现了崩溃半程——只会散不会聚,碎片化是棘轮。
本实验补上**吸收半程**(oracle 把关的合并),主张:同预算下它能回收**同义冗余副本**
(彼此差异趋零的碎片,《分散但趋同》坑二判定的过碎病理,非真差异),recall 升、precision 不降,
且**绝不吸收真差异**(跨义合并=死刑)。**目标不是"结构越少越好"——是粒度回到真差异处,环恢复双向。**
本实验的"第三把手"(坑二要求的过碎/健康分散判别器)= 审卷标签,只审不进信号。

## 1. 可证伪主张(能输)

**主张**:同语料、同 oracle(API)、同总预算 B 下,`full+merge` 相对 `full(仅裂)`:
碎片化指数 FI 严格下降,pairwise recall 严格上升,precision 下降不超过 ε=0.02,且**零跨义合并**。
**死刑线(继承 kernel 死刑线,永不豁免)**:任何一次把不同义项并到一起(苹果-水果×苹果-公司、
或碰香蕉的干净 carrier)→ `overmerge_regression`,机制判负——防治回"糊"是本实验的存在前提。

## 2. 两臂(唯一差别 = merge 算子;oracle 强度混淆已隔离)

```text
full        流式:贪心沉积 + 槽位驱逐 + 怀疑触发 split(EXP-1 机制原样,但 oracle 换 API——见下)
full+merge  同上 + 合并侧:同 surface 的 carrier 对,centroid 余弦 > **θ_m = 0.35** 触发合并怀疑 →
            oracle 判 carrier_same_sense → same 则并(血统记录两源),diff 则记录并冷却(同对不复问)

**θ_m 定值依据(冻结,2026-07-02 实测;初版误用多数标签判纯度,经 Codex 复算纠正为严格纯度口径)**:
对 EXP-1 full 终态全部 16 个同 surface carrier 对,用同一嵌入(paraphrase-multilingual-MiniLM-L12-v2,
成员向量非归一均值为质心,质心间余弦——与 run_exp1 口径逐字一致)实测:
**纯审卷同义对仅 3 个**(长城城墙碎片对,0.392 / 0.406 / 0.487——恰是本实验要治的碎片);
其余 13 对含跨义或混杂 carrier,其中多对显著高于门槛(0.500–0.773),**最高 0.773 为跨义对**(苹果水果×公司)。
结论:嵌入相似度完全不能区分同义/跨义(表示债再现),**θ_m=0.35 只是高召回怀疑门**——
取值低于全部纯同义对(0.392 留余量)、必然故意放进大量危险候选;正确性百分之百由
oracle 拒绝 + 冷却止损 + 审卷死刑承担,一分不押嵌入。
```

**oracle 一致性纪律**:两臂全部判断(same_sense / coherent / split / carrier_same_sense)均由
**同一 API oracle**(qwen3-max 日期快照,temperature=0,同步调用、全量落盘)作出——EXP-1 的 Claude 批答
终态仅作历史参照,不与本实验直接对比(oracle 强度不同,直接比即混淆)。
**守恒纪律与调度(冻结)**:merge 与 split **共花同一预算 B**(与 EXP-1 同值)——代谢两半在稀缺下竞争,
是理论要的形状。但"竞争"不等于"放任饿死",调度规则冻结如下:
  每 turn:先 split 侧(至多 1 次怀疑审计,消耗 ≤2 调用:coherent+split),后 merge 侧(至多 1 次,1 调用);
  无预算保留额(守恒纯粹);每次"merge 该查但预算已尽"记一次 merge_starved 事件入账。
  若 merges_executed = 0 且 merge_starved > 0 → 判 `budget_policy_starved`(blocked 类:是调度问题不是算子失败,
  修调度重跑,不消耗裁决)——与 merge_vacuous(有预算查了但没触发/没改善)严格区分。
  预算分配轨迹(split 花费/merge 花费/starved/弃权)入 receipt。

## 3. Oracle 协议(v1.2:同步 API + 内容寻址日志)

```text
继承 v1.1 的内容寻址 qid、硬配额、重试一次即弃权;文件批答轮次退役(oracle 为 API,同步应答),
但每次调用的 prompt/应答/qid 仍逐条落盘可审。
**新 validator(冻结)**:carrier_same_sense 合法答案 ∈ {same, diff},oracle_api.py 的校验器必须支持全部四类
(same_sense / coherent / split / carrier_same_sense);沿用 oracle_file.py 旧 validator 而未扩 → blocked。
**leak-check 升级(冻结)**:禁入 token 表不再手列——运行时从语料**机械生成**(全部 true_sense 取值 +
"true_sense"/"sense" 字段名 + 任何仅存在于标签而不存在于句子文本的词,含 banana 等全部英文标签值);
手列漏项(v1.1 漏 banana)即此修的动因。**API 参数(冻结)**:model="qwen3-max-2026-01-23",
base_url=https://dashscope.aliyuncs.com/compatible-mode/v1,temperature=0,max_tokens=64,timeout=120s,
传输错误重试 1 次(2s 退避,attempt=2);key 仅从 DASHSCOPE_API_KEY 环境变量读取,不落盘、不入日志/receipt。
新增判断类型 carrier_same_sense,模板入 specs/oracle-prompt-v2.md(v1 三类原样继承 + 新增一类):
  「下面两组句子,各自围绕同一个多义词。只根据内容判断:两组中该词是否指同一个意思?
   只答 same 或 diff。无法判断答 diff。组1:{...} 组2:{...}」
每组给成员代表句(≤5 句,时间序采样);"无法判断答 diff"= 合并侧的保守默认,方向与死刑线一致。
```

## 4. 度量(标签只审卷)

```text
FI 碎片化指数   Σ_surface (carrier 数 − 真义项数),true_sense 仅审卷。EXP-1 终态参照:FI=5
                (苹果 3/2、小米 3/2、长城 5/2、香蕉 1/1)。
pairwise P/R/F1 同 EXP-1 度量,分母含全部 turn。
merge 事件账    每次合并:触发信号值、oracle 判断、两源 carrier 血统、事后审卷(是否同义)——
                跨义合并数必须为 0(审卷),否则死刑。
预算账          split 花费 vs merge 花费 vs 弃权,两臂对照。
```

## 5. 退出码(预注册,互斥)

```text
labels_leaked / oracle_unlogged / budget_exceeded / api_unavailable / budget_policy_starved → blocked_engineering(不消耗裁决)
任何跨义合并(审卷)或香蕉/干净分离被并                                    → overmerge_regression(死刑,机制判负)
零次合并触发,或 FI 无下降                                                → merge_vacuous(算子白设,如实记)
FI 降但 recall 未升或 precision 降幅 > ε                                  → merge_lossy(合并在毁信息,判负)
FI 严格降 + recall 严格升 + precision 降幅 ≤ ε + 零跨义合并               → absorption_earns_its_keep(通过)
辅助观察(不进门,均如实入 receipt):
  (i) API oracle 下 full 是否复现 EXP-1 方向性结论(oracle 鲁棒性,白送的复现);
  (ii) **有界振荡签名**:全流上 split 与 merge 事件是否都发生、carrier 数轨迹是振荡还是单调——
       理论预言活的系统两向都动;只降不升或只升不降都要如实记录(《分散但趋同》:单调曲线是坏消息)。
```

## 6. 杀死测试(每颗牙演示会失败)

```text
- 死刑牙(修:θ_m=0 只放宽触发,oracle 保守默认 diff 仍会拦住合并——那只证明 oracle 有效,证不了审卷有效):
          演示模式用 **mock oracle 对一个已知跨义对强制返回 same**(或直接注入一条合成 merge_event),
          审卷必须判死并触发 overmerge_regression → 抓不到=审卷失灵,blocked。演示环境,绝不入正式跑。
- 冷却牙:同一 carrier 对被 oracle 判 diff 后不得复问(防预算被同一对烧穿);复问 → budget 纪律红牌。
- 守恒牙:两臂总调用数 ≤ B,runner 硬计数;merge 侧无独立预算外配额。
- 不回弹牙(双向,《分散但趋同》§7 动力学不变式的移植):合法的裂,后续自由竞争下不得被本机制并回;
          合法的并,后续不得被本机制再裂。同一对结构的裂-并循环 ≥ 2 次 = thrashing 红牌——
          注意区分:**跨越多个 turn、由新证据触发的再重组是合法振荡(事件有据);同对短程往返是空转**。
          顺序牙:merge 在每 turn 的 split 检查之后运行;两类事件全部带戳入账,空转/合法振荡分列。
- 静态对照(修:单义流上同义重复 carrier 被触发、被合并是**健康行为**,不许当病判):
          纯 fruit-only 流上,full+merge 的合并**允许发生**,但审卷跨义合并数必须为 0(单义流上恒真,作审卷冒烟)、
          且终态 carrier 数 ≤ 初态(合并只减不增);真正的死刑对照 = 主流上苹果-水果/苹果-公司的干净分离必须存活。
```

## 7. 角色与实现边界(冻结后 Codex 建)

```text
角色    Codex=实现+运行+机械度量;API(qwen3-max 快照)=全部 oracle 判断;Claude=spec 起草+锁账后审计
        (审 merge 事件账 vs 审卷标签、预算账、oracle 日志完整性;不参与判断)
src/oracle_api.py        同步 API oracle:v1 模板 + carrier_same_sense;内容寻址日志;硬配额;温度 0
src/memory_merge.py      full+merge 臂(memory_budget.py 演进:合并算子 + 冷却表 + 血统)
src/run_exp15.py         两臂 + 度量 + 退出码 + receipt(FI/PRF/merge 账/预算账/震荡计数)
specs/oracle-prompt-v2.md 判断模板冻结件(v1 继承 + carrier_same_sense)
artifacts/exp15_*        oracle 日志 / merge 事件账 / report / receipt
参数:θ_m=0.35(定值依据见 §2)、代表句数 ≤5、B=48(与 EXP-1 同)、ε=0.02。
版本分叉:**v1(RUN_ID=exp15-v1)已冻结已裁决(负,§8.1),归档不再跑**;
**现行执行版 = v1.5b(RUN_ID=exp15b-v1)= v1 全部参数 + §8.2 资格门与调度修订**,以 §8.2 为准。
```

## 8. v1 交付记录(2026-07-02)与 EXP-1.5b 修订(预注册,待冻结)

### 8.1 v1 裁决:overmerge_regression(死刑线)+ 精度护栏爆(双重负,如实入账)

```text
官方跑(exp15-v1,API oracle):4 次合并,审卷抓到 1 次跨义(turn 77 长城);precision 0.933→0.803(降幅 0.13 ≫ ε)。
败因解剖:oracle 按内容判断无错(两组均公司为主);毒源=沉积期污染(桥接句[68]早被贪心嵌入塞进公司 carrier),
合并继承并平方放大存量污染。三次干净合并全部中靶(小米谷物合一、长城城墙碎片两连合=EXP-1 遗留 M07/M08),
FI 7→3、recall +0.151。死刑演示(mock oracle)被审卷正确判死,审卷牙验证有效;冒烟跑合规;预算 45/48 零饿死。
```

### 8.2 EXP-1.5b:唯一改动 = 合并资格前置内聚体检(吸收方必须先干净)

```text
改动(冻结)   merge 怀疑对触发后、问 carrier_same_sense 之前,双方 carrier 须先通过 coherent 判定
              (oracle,全成员文本,与 v1 协议同类同模板):
              - 双方 coherent → 继续 carrier_same_sense,后续同 v1;
              - 任一方 incoherent → 本次不合并;该 carrier 转为下一 turn split 侧的强制候选
                (复用已有 incoherent 答案直接进 split 调用,不重复问 coherent);
                该合并对记 deferred(挂起),不占冷却名额——源头裂干净后,新对经 θ_m 扫描自然重入。
体检缓存      内聚证书随成员变动(沉积/裂/并)即失效;内容寻址缓存天然去重,同一成员集不重复付费。
              **单例 carrier(1 成员)机械视为 coherent,零调用**(单句无从混义)。
调度(v1.5b 冻结,取代 v1 的"merge 侧 ≤1 调用")
              merge 侧每 turn 至多处理 **1 个候选对**,单对上限 **3 次调用**(coherent A + coherent B +
              carrier_same_sense;缓存/单例命中即免费)。**不开没钱收尾的工**:处理前先按缓存态结算
              本对所需调用数,剩余预算不足 → 记 merge_starved,本 turn merge 侧不动
              (starved 语义不变=钱不够;deferred 语义不变=体检不过,两者分账)。
强制 split 队列(v1.5b 冻结)
              体检 incoherent 的 carrier 进强制队列,**优先级高于**方差怀疑排序(oracle 实证 > 启发式);
              多个强制候选按入队 turn 先进先出;处理时复用缓存的 incoherent 答案,只花 1 次 split 调用。
              split 应答无效/弃权:协议内重试 1 次后仍失败 → 该 carrier 移出队列、记 forced_split_failed
              入 receipt(其 incoherent 证书仍在,保持合并无资格,不阻塞运行)。
预算          体检与强制 split 调用均计入共享 B(守恒不破);receipt 新增 eligibility / deferred /
              merge_starved / forced_split_failed 四笔账。
其余零改动    θ_m=0.35 / B=48 / ε=0.02 / 死刑线 / 全部牙 / API 参数 / oracle-prompt-v2 原封;RUN_ID=exp15b-v1。
理论出处      "先崩溃后重组"的次序从每 turn 调度升级为吸收算子的资格条件——带病的结构没有资格当吸收方。
诚实风险      若 oracle 把污染 carrier 误判为 coherent(如[68]旅游品牌句在公司组里可能被读成"都在说品牌"),
              致命合并仍会发生、死刑线会再次触发——那将证明体检的天花板是 oracle 的分辨力,如实判负,不再修补第三版
              (两负即回炉重审吸收算子的设计假设,升级为项目方决策)。
```

## 9. 预注册摘要

```text
claim  = 同预算下 merge 算子(带资格门)降 FI、升 recall、precision 损 ≤0.02,且零跨义合并
nulls  = {full(仅裂,同 API oracle)};allow-to-lose;overmerge_regression 为死刑出口
oracle = API qwen3-max 快照 temp=0,两臂同源同预算;merge/split/eligibility 共花 B(守恒竞争)
gate   = 合并资格前置内聚体检(§8.2:双方 coherent 才问同义;单例免检;病方转强制 split 队列)
teeth  = 死刑演示(mock oracle 验审卷)/ 冷却 / 守恒+新调度(单对≤3调用,不开没钱收尾的工)/ 双向不回弹 / 静态对照零跨义+只减不增
stop   = 两负回炉:v1 已负(§8.1);v1.5b 若再触死刑线或护栏 → 不修第三版,吸收算子设计假设升级为项目方决策
铁律   = (a) 判断全落盘;(d) 这是机制跃迁(补全代谢循环),不是参数堆积
版本   = 执行 RUN_ID=exp15b-v1;v1 归档(负)
```
