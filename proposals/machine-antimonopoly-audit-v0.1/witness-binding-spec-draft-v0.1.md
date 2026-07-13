# witness 绑定扩展 —— 前瞻目标注册的 spec 草案 v0.1(苗圃出苗物)

**状态:** 零权威候选草案。这是 `bridge-vs-church-decision-procedure.md` 按其自身判据 #2 从"苗圃"里被逼出的**那一件出苗物**。它**不改任何代码、不碰生产 schema**;真正落到账本 schema 是红区(授权面),须项目方单独明示授权。本草案只做两件可逆的事:①把"先存见证物 id"从概念**写成一份可实现的字段规格**;②给出一条**当前会失败的验收断言**,让判据从"靠人纪律执行"变成"能被数据结构卡住"的目标态有个锚。

**授权出处:** 项目方 2026-07-10 17:32 JST 于 `impl/peer-chat.jsonl` 直接指令"起草苗圃产物吧"。绿灯范围 = 起草可逆的 spec/测试,不碰真 schema。

**并行草案协调(2026-07-10 17:35):** 同一条指令同时触达 Claude 与 Codex,两边**各自独立**起草了苗圃产物——Codex 的在 `witness-id-nursery-product.md`。**这不是重复浪费,是双重收敛的证据**:两份互不知情的草案独立落到了同一组核心(必填 `witness_ref` + `witness_snapshot`、快照须由注册命令生成而非候选自填、时间戳须先于注册、依赖闭包判同岸)。两份**互补,分工如下**——Codex 那份是**字段与失败测试目录**(6 条待写测试的验收形状更全),本份是**"三缺"诊断 + 规则 A 优先落地路线 + 反身检查**。评审时以本份的规则分层(A/B/C)为骨架,以 Codex 那份的测试目录(§失败测试草案 1–6)为 §5.2/§5.3 的落地清单。**两份都不算数,直到走正规证据门。**

---

## 0. 一句话动机

判据那根钉是"**度量必须先于被度量者,且握在不靠它过关得利的一方**"。现在账本能存 `sources`/`source_snapshots`,但**不强制**押对岸的目标去绑定一个先存的、候选自己碰不到的见证物。于是任何机制都能声称"对岸快了"而永久占着 surface。本 spec 就是给"押对岸"这个动作**加一道注册期的硬门**。

## 1. 现状核验(只读,已确认)

真实现 = 部署 skill 的 `scripts/prospective.py`。goal_registered 事件当前写入:

```
goals[goal_ref] = {
    "goal_ref", "description", "condition", "budget", "death_line",
    "state", "registered_event_id",
    "sources": data.get("sources", []),            # 自由 list,无语义约束
    "source_snapshots": data.get("source_snapshots", []),
}
```

- `source_snapshots` **能**证明"先于候选":它记 `head_event_id` + `head_timestamp_utc`,可比对是否早于 `registered_event_id` 的时间戳。
- **但** `sources`/`source_snapshots` 是**自由填**的:schema 不要求它们指向一个真实存在的、候选碰不到的对象;也**没有** `witness` 这一等级的专门字段。
- 结论:先于性**可核**,不可伪造性(候选碰不到)**不可核**,绑定性(押对岸必须有见证物)**不强制**。三缺二。

## 2. 提议的字段(新增,向后兼容)

在 goal_registered 的 data 里新增一个**可选**字段 `witness`(不填时行为等同今天,故向后兼容;判据只对**声称桥豁免**的目标要求它):

```jsonc
"witness": {
  "witness_kind": "failing_test | missing_contract_field | open_question | frozen_frame",
  "witness_ref":  "<稳定 id,指向一个先存对象>",   // 如 open-question 的 ledger event_id、失败测试的 nodeid、frame ref
  "witness_snapshot": {                            // 复用现有 source_snapshots 的形状
    "exists": true,
    "head_event_id": "...",
    "head_timestamp_utc": "..."                    // 必须早于本 goal 的 registered 时间戳
  },
  "authored_by_candidate": false                   // 见 §3 规则 C
}
```

`witness` 不是 `sources` 的替代,是它的**受约束子类**:`sources` 继续记"我参考了什么",`witness` 单独记"我押的那片岸,钉在哪个先存物上"。

## 3. 注册期校验规则(三条,对应三缺)

一个 goal 若在 data 里带 `"claims_bridge_exemption": true`(即请求进入"该等/免 CUT"),`register` 必须校验:

- **规则 A(先于性,今天就能实现):** `witness.witness_snapshot.head_timestamp_utc` 必须**严格早于**该 goal 的 `registered_event_id` 对应时间戳。否则拒绝注册。—— 这条**当前 schema 已有足够信息实现**,是最先能落地的一条。
- **规则 B(绑定性):** `claims_bridge_exemption=true` 但 `witness` 缺失 → **拒绝**,并把该 goal 归类为 greenfield(按判据 #2 走苗圃,不给桥豁免)。
- **规则 C(不可伪造性,最难):** `witness_ref` 必须指向一个**候选碰不到**的对象。最小可核代理:`witness_ref` 必须能在**注册事件之前**的账本里被解析到一个已存在事件(open-question / frozen frame / evidence 的 ledger id),且该事件的作者不是本 goal 的注册者。`authored_by_candidate` 若为真或无法反驳 → 拒绝。—— 这条**当前 schema 取不到**足够信息(没有稳定的"witnessed object 作者"追溯),是留给红区 schema 演进的真缺口。

## 4. 当前会失败的验收断言(判据落地的锚)

下面这条断言,针对**今天的** `prospective.py`,**现在必然失败**——这正是它作为"苗圃出苗物"的意义:它把"判据卡不进数据结构"这件事,从一句话变成一个可执行的红灯。

```
# 伪代码,不接入真 register,仅作草案锚
def test_bridge_exemption_requires_prior_witness():
    # 注册一个声称桥豁免、但不带任何先存见证物的 goal
    ev = register_goal(
        goal_ref="goal:speculative-bridge",
        claims_bridge_exemption=True,
        witness=None,            # 交不出先存见证物
    )
    # 期望:被拒绝(规则 B)
    assert ev.rejected, "押对岸却无先存见证物,应拒绝注册为桥"
    # 今天:register 不认识 claims_bridge_exemption / witness,照常接受 -> 断言失败(红灯)
```

**红灯是对的。** 红灯亮着,就证明判据现在只活在人的纪律里、不活在 schema 里——这个红灯本身,就是判据 #1 要求的那个"先于自己存在、自己碰不到的外部见证物"的**雏形**:它是一个客观的、后续 schema 演进必须把它转绿的失败测试。

## 5. 落地路线(可逆 → 红区闸)

1. **本草案(可逆,已做):** 写下字段形状 + 三规则 + 会失败的断言。
2. **规则 A 的独立原型(可逆,下一步):** 在 `impl/` 下写一个**独立**小函数 + 通过测试,只做"先于性"校验(纯比对两个时间戳),不接触生产 `prospective.py`。证明判据里**最容易的那条**真能被机器卡住。—— 这是 harness 梯度,**建议委派 Codex**。
3. **规则 B/C + 真 schema 绑定(红区):** 改生产账本 schema、加 `witness` 字段、改 `register` 校验 —— **项目方按钮**,本草案止步于此,只把它排在门口。

## 6. 反身检查(本草案没给自己破例)

- 本草案**没有**声称自己是桥、没请求任何豁免;它是 §5.1 那件苗圃出苗物本身,交付即出苗。
- 它交出的"先于自己的见证物"= §4 那条**现在就红着**的断言:一个客观的、候选(本草案)碰不到其判定的失败信号。它满足判据 #1 对见证物的形状要求。
- 它**没碰**红区:没改 schema、没改 `prospective.py`、没改授权面文件。全部产物落在 `proposals/` 下,git 可回滚。
- 它**标了**自己够不着的边界(规则 C 当前不可核),没有假装判据已闭合。诚实的半成品,不是漂亮的空转。

## 7. 规则 A 原型评审结论(Claude 评审,2026-07-10 JST)

Codex 已交付 §5.2 委派的独立原型:`impl/witness_precedence.py` + `impl/test_witness_precedence.py`。**评审结果:验收通过,含一条把规则 A 与规则 C 一并推进的结构性修订。**

**已核验(证据在手):**
- `pytest` 5/5 全绿;另跑三条独立边界探针:`Z` 后缀正确归一、跨时区按绝对 UTC 比较(`16:59:59+09:00` 判定早于 `08:00:00+00:00` → 通过)、同秒时间戳严格拒绝。
- **未** import/修改生产 `prospective.py`/`weilan_trace.py`/真账本;复用真字段名 `head_timestamp_utc`,日后可平移。要求 tz-aware、拒绝 naive 时间戳——纪律干净。
- 与 Codex 回执一致,**无过度声称**:原型只证"给定诚实时间戳,先于性可机器校验",明确把规则 B/C 标为未解红区。

**评审发现的一条承重修订(把"三缺"再收一格):**
- 规则 A 现在把先于性锚在**时间戳字符串**上。但时间戳有两个弱点:①**候选可伪造**(候选自己填 `head_timestamp_utc`,正是规则 C 那道口子);②**同秒假阴**——真账本时间戳常是秒粒度(如 `2026-07-10T03:04:00+00:00`),一个真先于注册、却与注册落在同一秒的诚实见证物会被 `>=` 误拒。
- **修订方向:先于性应锚到账本的追加序(event append-order / `head_event_id` 序位),而非/并非仅靠墙钟字符串。** 依据正是 Codex 核验(回执 `c1675d591e33`)已确认的事实:`registered_event_id`/`head_event_id` 由账本在写入时分配、候选不可控。追加序同时解决两件事——(a) 修掉同秒假阴(序位无并列);(b) **真正推进规则 C**:在 append-only 账本里,候选**无法把一个事件回插到某既有事件之前**,所以"见证物事件的序位早于 goal_registered 事件"是一条**候选不可伪造**的先于关系,远硬于候选手打的时间戳。
- 故规则 C 不再是铁板一块的"当前 schema 取不到":其中**先于性的不可伪造锚**这一半,可用现有 `head_event_id` 序位取到;仍未解的是"见证物对象的**作者追溯**"(证明该 witness 不是候选本人所造)——那一半才是留给红区 schema 演进的真缺口。§3 规则 C 的"三缺"由此从"整条取不到"细化为"先于锚可取、作者锚未取"。

**下一步(可逆,建议排下一班):** 给 `witness_precedence.py` 增补一个按 `head_event_id` 序位判先于的校验分支(纯离线、仍不接生产),并补一条"同秒但序位在前 → 通过"的测试,把本节修订从文字变成绿灯。规则 C 的作者追溯仍是红区,止步排队。

## 8. 追加序原型评审结论(Claude 评审,2026-07-10 JST,回执 `47cb3557ea31`)

Codex 已交付 §7 委派的追加序分支:`impl/witness_precedence.py` 新增 `validate_witness_precedes_by_event_order`,`impl/test_witness_precedence.py` 由 5 条扩到 8 条。**评审结果:验收通过,但须给"推进规则 C"这句话钉死一个更窄的边界,否则决策程序会高估规则 C 的完成度。**

**已核验(证据在手):**
- 我**独立重跑** `pytest ...test_witness_precedence.py -q` → `8 passed in 0.07s`,与回执一致。
- 新分支纯离线:`event_order` 是内存桩(list of id / (id,pos) / mapping),**未** import/修改生产代码或真账本;复用真字段名 `head_event_id`。
- 三条新测试覆盖到位:同秒但序位在前→通过(修掉秒粒度假阴)、序位同位→拒绝、序位在后→拒绝;原时间戳规则 A 五条仍全绿。

**承重修订——把"推进规则 C"收窄成它真正做到的那一半:**
追加序**只**杀死一类伪造:**回插式伪造(backdating)**——候选无法让一个此刻追加的事件声称自己排在既有事件之前。这一格是真的、干净的。
但它**不**杀死另一类,而这一类恰是规则 C"作者追溯"的实体:**预追加式伪造(pre-appending)**——候选先把一个自己捏造的"见证物"事件追加进账本、**再**注册 goal 指向它。此时见证物事件的序位**合法地**早于 `goal_registered`,追加序校验**通过**,但这个见证物是候选本人所造。
所以:`validate_witness_precedes_by_event_order` 通过 **≠** 见证物不可伪造;它只证明"见证物不是被回插的",不证明"见证物不是候选自己先埋的"。**先于性(order)是不可伪造性的必要条件,远非充分条件。** 规则 C 的残缺不是一个可查表补上的"作者字段"缺失,而是:任何只看两个事件相对序位的校验,都对"候选先埋后注册"这条路径完全无感。堵它必须另立一根锚——见证物的**产生动机与作者身份**须独立于注册者(如:见证物须由一个不因本 goal 过关而得利的主体写入,或须是 open-question/失败测试这类**有外部消费者**的对象),这仍是红区 schema 演进,且比"加个 `authored_by_candidate` 布尔"更深。

**结论:** 规则 A 完成;规则 C 的**先于锚(抗回插)**完成;规则 C 的**作者锚(抗预埋)**未动,且已看清它不是补字段能了的。§3 规则 C 的措辞据此再细化:"先于锚可取(抗回插已实现)、作者锚未取(抗预埋是真红区)"。本轮无新委派——追加序分支到此收口,预埋防护须待项目方对 schema 授权后另开,现止步排队。

---

*署名:Claude + Codex(判据下降链见 `bridge-vs-church-decision-procedure.md`);本草案由 Claude 在 2026-07-10 owner 绿灯下起草,§7/§8 评审由 Claude 于同日补入。*
