# EXP-2f — P2 终局:选择题重考,带停止规则(本设计族最后一跑)

状态:**已冻结(2026-07-02,项目方确认;Codex 评审六条已修,Claude 校准牙审计签字见 §7)。**
冻结件:本 spec + exp2f-questions-v1.md(4edb8040…)+ run_exp2f.py(65156a01…)。自此任何改动即 blocked。
上位:`../ROADMAP.md` P2;前序:EXP-2 v2(2/3)、v3b(2/5)均 `unstable_readout_not_frozen`。
失分对账结论(见账本 2026-07-02):主门失分 7/9 为仪器噪声(评分词表 5 + 格式 2),行为性问题仅 2。
**本版只换仪器,不动处理、不动门槛。**

## 0. 一句话

同样的记忆、同样的门槛、同样的盲测流程,把开放问答换成**四选一**,让词表噪声与格式噪声物理归零——
然后接受最终裁决:过即 P2 通过;不过即 P2 记负,**没有下一版**。

## 1. 不变项(三个版本攒下的资产,逐字继承)

```text
记忆臂     full-readout / rag-readout / no-memory;EXP-1 终态(artifacts/exp1_claude_terminal_carriers.json),
           同读出契约、**K=600**(Qwen3.5-4B tokenizer 计数,与 v3 冻结 spec 及 run_exp2.py K_MEMORY_TOKENS 一致)、
           同截断规则、记忆块与 v3b 逐字节一致(冻结时以 sha256 断言入 receipt)
盲测       回答者改为 **DashScope API(qwen-max 带日期快照版,冻结时写死具体型号;temperature=0)**——
           API 逐条无状态调用 = 会话隔离由物理保证(v2/v3b 的人工新窗协议就此退役);Qoder 人工粘贴仅作
           API 不可用时的回退,回退时执行原 360 条人工协议。key 由 runner 从本地读取,绝不入 spec/receipt/账本;
           每轮独立随机臂映射与选项乱序不变。回答者变更(Qoder 聊天→API 快照)属冻结前正当修订,型号入 receipt。
协议       echo nonce 强制回显;collected_at_utc 每行必填;无效行允许换新会话重投一次(attempt=2),再废;
           采集层错误单独产 artifacts/exp2f_collection_audit.json(v3b 实践转正为必交件)
角色       Codex=出题/实现/机械评分(可见钥匙,不答题);Claude=冻结前选项审计+锁答后 receipt 终审(不答题不评分);
           回答者不得见题集文件/钥匙/臂映射/任何 EXP 历史
每轮四检   full 严格最高;full−no-memory ≥ 0.20;full−rag ≥ 0.08;T2 与 T4 分别不输(平局=不输,须标注)
总门       5 轮中至少 4 轮通过
```

## 2. 唯一改动:答题形式(仪器修正,与记忆处理正交)

### 2.1 题制

每题 **4 个选项,恰好 1 个正确**,四类选项各就各位:

```text
A类 正确项      流内可证(答案锚定语料原句,冻结审计时逐条给出行号)
B类 错义陷阱    把另一义项的事实安到本义头上(直接替代 v3 的 forbidden 关键词机制——选它=真混淆,零误杀)
C类 似真缺席    现实中合理、但流内从未出现的说法(测"只依据材料"纪律)
D类 材料不足    "材料不足,无法判断"(对 no-memory 臂这是诚实选项;对记忆臂选它=读出失败)
```

选项字母顺序按 `(repeat, arm, question)` 以冻结种子确定性打乱,映射入 receipt(防位置偏置)。

### 2.2 题量与分布

```text
总 24 题:主门 20 = T1 义项枚举 ×6 + T2 义项分离 ×6 + T4 抗错并 ×8;辅助 T3 事实检索 ×4(照常评分不进门)。
每题主门价值 5%(v3b 为 8.3%),0.08 边距 ≈ 2 题,不再被单题噪声翻盘。
```

### 2.3 答案与评分

```text
回答 JSON 仅两个必填字段:{"choice":"A|B|C|D","echo":"<校验码>"};可选 "basis" 仅存档不评分。
评分 = 提交字母经私有乱序映射还原为规范选项 id 后,与 answer_key 精确匹配(见 §2.4)。
v3 的全部语言机器(同义词表/正规化/否定窗口/forbidden 扫描)整体删除。
无效 = 非法 JSON / choice 不在 ABCD / 多选 / echo 不匹配;重试一次后计 0(不变)。
答题输出 cap 沿用 v3 的 112 token 不变(四选一下实答远短于 cap,cap 仅防溢出;避免与 oracle 侧 BUDGET=48 混淆)。
```

### 2.4 规范选项 id 与渲染字母分离(防泄漏)

```text
题集 JSONL 用规范 id:options{"o_correct","o_trap","o_absent","o_insufficient"},answer_key=规范 id。
渲染时按 (repeat, arm, question) 以冻结种子将四个规范 id 确定性映射到 A/B/D/C 等字母;
映射表与 answer_key 只进 artifacts/exp2f_option_map_private.json(私有,锁答后才可揭示),
给回答者的 queue 中只有渲染后的字母选项文本,不含任何规范 id / key 痕迹。
评分器:提交字母 → 私有映射还原规范 id → 与 answer_key 比对。
```

## 3. 新增两颗牙

```text
钥匙校准牙(冻结前) Claude 逐题审计,对照两层材料:
                    (a) corpus/drift_multi.jsonl —— 正确项流内可证、陷阱项真属错义、缺席项真不在流内;
                    (b) **渲染后的记忆块**(full 与 rag 各自实际注入文本)—— 正确项必须在 full-readout 渲染块中可证
                        (主张优胜的臂必须真有据);rag 渲染块的可证性**逐题记录但不作要求**——rag 的读出里
                        没保住证据,正是被测的记忆缺陷,该臂如实选 D 计 0 即为行为读出失败,评分解释以此为准。
                    防挑题护栏:题目按 surface 配额分布(苹果/小米/长城均衡,香蕉入 T4),配额冻结于题集头部;
                    rag 可证率入 receipt,供审计员判断题集是否系统性偏袒。审计签字(哈希+日期)入 spec 附录,缺签字不得冻结。
地板牙(升级)       no-memory 主门得分 > 0.40(明显高于服从型 0 与乱猜 0.25)→ questions_not_memory_bound。
                    预期行为:no-memory 多选 D;receipt 须报三臂的选项分布。
```

## 4. 停止规则(预注册,本 spec 的存在理由)

```text
EXP-2f 是 P2 设计族(readout 行为门)的最后一次运行。
- ≥4/5 轮通过           → p2_passed,进 P3/P4 排程。
- 不足                  → p2_failed_final:P2 整体记负,不再重跑、不再改版;
                          同时分项入账:T1 枚举增益(v2+v3b 已八轮全胜)若本次仍全胜,单独记为"已确立子结论";
                          路线图走降级分支:主攻转 EXP-1.5(merge 算子)+ P4 设计复审。
- blocked_engineering   → 修工程性阻塞后可重跑,不计入"最后一跑"(阻塞≠裁决;v1 采集事故同理)。
                          **blocked 类出口枚举(冻结)**:采集错位 / echo 协议失效 / prompt 非机械生成 /
                          记忆块 sha 不符 / questions_not_memory_bound(题集失准属仪器,修题重审后重跑)。
                          只有产生有效裁决(p2_passed / p2_failed_final)才消耗"最后一跑"。
任何对本节的修改均须项目方书面确认并在 receipt 中声明。
```

## 5. 已知局限(如实入 receipt)

```text
- 选择题测的是"辨认"而非"自由回忆",行为增益的表述强度相应下调一档;
- T2/T4 部分可由常识+指令服从作答,地板与陷阱选项只能部分缓解(继承 v3 声明);
- 回答者为黑盒外部模型,系统提示不可知(以会话隔离与 echo 协议兜底)。
```

## 6. 实现边界(冻结后 Codex 建)

```text
specs/exp2f-questions-v1.md      头部:surface 配额表;24 题 JSONL:id/family/surface/question/
                                 options{o_correct,o_trap,o_absent,o_insufficient}/answer_key(规范 id)/
                                 anchor_rows(语料行号)/full_render_anchor(渲染块内证据句)
                                 —— Codex 起草,Claude 按 §3 校准牙审计后随本 spec 一并冻结
artifacts/exp2f_option_map_private.json   (repeat,arm,question)→字母乱序映射 + answer_key;锁答后揭示
src/run_exp2f.py                 队列生成(选项乱序+种子)/echo/配额/精确匹配评分/四检+4/5 门/receipt
artifacts/exp2f_*                queue / arm_map_private / answers / score_report / receipt / collection_audit
RUN_ID = exp2f-v1;REPEATS = r1..r5;180→360 条 prompt(24 题×3 臂×5 轮)
```

## 7. 校准牙审计签字(Claude,2026-07-02)

```text
审计对象   specs/exp2f-questions-v1.md  sha256=4edb804043de2f08a6065fe0759b1500bf4b6de5810643fe3419a48f493e4323
           src/run_exp2f.py             sha256=65156a01248e9566de1d0e606ad78fa566729a76ee3f66e966203e0d150cf9a7
题集(a)层  24/24:anchor_rows 与语料逐字吻合;陷阱项均真属错义;缺席项均不在流内;配额与头部声明一致
题集(b)层  24/24 正确项在 full 渲染块可证;rag 可证 12/24(不可证 12 题全部为苹果/小米公司义——
           rag 糊团读出未保留该义项证据,属被测缺陷;长城/香蕉题 rag 全可证,无系统性挑题痕迹)
记忆块     重建块与 v3b 队列内块逐字节一致(full=667a3297…,rag=5b391a35…前缀);处理零改动断言成立
型号       qwen3-max-2026-01-23 在采集 key 上实测可用(temperature=0 应答正常)
runner     队列不含 answer_key/规范 id/answer_letter;私有映射与钥匙仅入 *_private.json;
           评分=字母→私有映射→规范 id 精确匹配;questions_not_memory_bound 为独立 verdict 不消耗最后一跑;
           4/5 门、严格最高、双边距、T2/T4 不输均与 spec 一致
留观注记   (i) collect 断点续跑时 attempt-1 无效行不会补投 attempt-2(仅整段运行内重试)——建议跳过条件改为
           "最新 attempt 有效或 attempt≥2",不阻塞;(ii) T2 类正确项文本略长于陷阱项,长度线索对三臂等同,
           以地板牙(>0.40)为实证防线;(iii) T4-apple-sweet 的"秋天"细节句不在渲染块,但义项归类不依赖该句,放行。
结论       **通过。缺失项:无。本签字覆盖题集与生成/评分逻辑;冻结后上述两文件不得再改,违者 blocked。**
```

## 8. 交付记录与终审(2026-07-02)

```text
verdict = **p2_passed(5/5 轮,门槛 4/5)** —— P2 行为级闭环通过,铁律 b 兑现。
full    = 主门 1.000 ×5 轮(120/120 全对,temp=0 下对全部选项乱序鲁棒);辅助 T3 亦 1.0。
rag     = 0.750 ×5:33 次诚实选"材料不足"(恰落在其读出丢失公司义的题上)+ 2 次错义陷阱——
          糊团记忆的行为代价以最干净的方式显形。
no-mem  = 0.10-0.25(103/120 选"材料不足",服从纪律),远低于 0.40 地板牙 → 题集记忆绑定成立。
完整性  = 零无效、零 echo 失配、360/360 可解析、1 次协议内重试(p0292 API 瞬断);
          题集/runner/终态哈希与冻结签字吻合;receipt 中 spec 哈希为 prepare 时刻版本
          (冻结状态行 10 分钟后写入所致,实验内容无涉,判定良性;教训:冻结仪式应先于 prepare)。
定性    = v2/v3b 的"不稳定"确证为仪器噪声:同一批记忆、同样门槛,换干净仪器后从 2/5 变 5/5 满分。
          局限照记:四选一测辨认不测回忆;full 的满分部分得益于题型简化。
停止规则兑现:P2 设计族就此关账,裁决为通过。
```

## 9. 预注册摘要

```text
claim  = 同记忆同门槛下,消除仪器噪声后 full 读出行为得分 ≥4/5 轮严格胜出
change = 仅答题形式(四选一+精确匹配);处理/门槛/盲测/预算零改动
nulls  = {rag-readout, no-memory};allow-to-lose;p2_failed_final 为一等出口且不可再跑
teeth  = 钥匙校准(冻结前 Claude 逐题签字)/ 地板>0.40 blocked / echo / 会话隔离 / 5 轮独立随机
stop   = 本设计族最后一跑,输赢都认账
```
