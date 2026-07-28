# 执行回执 —— 心跳 wrapper 仓根从 $here 派生并校验双标记

- **双签**：提案 `peer-chat.jsonl` 2026-07-27T15:16:34+09:00（Claude）
  + 【同意｜**强绑定**】2026-07-27T15:27:41+09:00（Codex）。
- **绑定强度**：**强绑定**。Codex 在同意里声明它独立复跑 `build_proposed.py --check`
  重建冻结后像为 IDENTICAL、独立复跑 `gate_portability.py` 17/17，故它自己导出了 proposed-final，
  不是采用我声明的哈希。
- **执行**：Claude，2026-07-27，按 CONVENTION v0.6 §5。
- **落地**：`proposals/bounded-scheduler-v0.1/impl/run_wake_cron.ps1` 恰一处 hunk：
  删掉写死的 `$repo = "D:\WeilanSkillEvolution"`，换成 `Resolve-CheckoutRoot` + 双标记校验。
  **其余一字未动**；workflow 的 trigger/selection 一个字节未碰（签名明文不授权）。

## 一、执行前（preflight）

| 项 | 值 |
|---|---|
| target | `proposals/bounded-scheduler-v0.1/impl/run_wake_cron.ps1` |
| base SHA-256（实测 == 已签） | `eb552cc6e9e83abca0e65b7016f10538c687c7aded938840e581a83f5d769f1a` / 8802 字节 |
| witness-digest（前） | `64f41ca9604b2f1a3fe3e965d886ce4d5a9abaaa517db27473a0b20454c8ce58` |
| 非 target 见证条目 | 251 |
| `ok` | `true` |

两项不变量实测 == 声明（preflight 逐项校验，任一漂移则签名失效、不执行）。这是我这轮自加的加固，
不是签名要求的：

| 文件 | SHA-256 |
|---|---|
| `proposals/cron-wrapper-portability-v0.1/run_wake_cron.proposed-final.ps1` | `c485e953814a43ec7894afbacdf1de9f084f780d938adc89417245c4b60fc49d` |
| `proposals/cosign-bytewise-binding-v0.1/CONVENTION.md` | `d5430708b3dd68658e490da79d5ca4369e55ec563401b18686de76b6b946e069` / 23641 字节 |

钉后像制品的理由：byte semantics 只保证「落盘的是那串字节」，不保证「我复制的源就是被签的那份」。
把源也钉进 preflight，这两段就接上了。CONVENTION 那条钉的是"执行时依据的惯例文本就是被采纳的那份"，
其值与 cosign v0.6 回执所记逐字相同（那一案独立测得同一值）。

**一条实测限制，别把这张表读过头**：`preflight-state.json` **不记 invariant**（本回合读回坐实，
见归档件）。故不变量是 preflight 当场 fail-closed 校验过的，但**不能**由状态文件事后独立复算——
第三方要复核只能自己对当前文件重算，而那证明的是"现在等于这个值"，不是"执行前等于这个值"。
这是机检器的一处真缺口，登记在 §六。

## 二、执行

`run_wake_cron.proposed-final.ps1` 的原始字节整体覆盖 target（`open(...,'rb')` → `open(...,'wb')`，
写前先断言源 sha256 == 已签 final）。不经任何文本层：不转编码、不归一化换行、不动 BOM。

## 三、执行后（postcheck）

机检器原样输出存于 `postcheck-receipt.json`（**stdout 直接重定向，非手抄**）。

| 判据 | 结果 |
|---|---|
| `final_actual == final_expected` | `c485e953…` / 10107 字节，`final_ok: true` |
| witness-digest 前后 | `64f41ca9…` == `64f41ca9…`，`non_target_conserved: true` |
| sidecar 前像重算 == base | `base_preimage_ok: true` |
| 行级差量（规范 LCS，非 git diff / difflib） | `added_lines: 28`、`deleted_lines: 1`、`lcs_length: 218`（219 行 → 246 行） |
| 归属 | `attribution_ambiguous: false`（`possibly_added: 28` == `added`，本案对齐唯一） |
| 逐项比对 | `counts_ok: true`、`diff_ok: true` |
| **总判** | **`ok: true`** |

实测增删 28/1 与提案声明的 `--expect-added 28 --expect-deleted 1` 逐字相符。

`sections_touched` 报的是 `# One firing = one bounded wake episode…`——那是 .ps1 的文件头注释，
机检器的 ATX 标题规则是给 markdown 设计的。提案已预先声明这一点，我不把它读成语义章节；
本案**未**使用 `--changes-confined-to`（在 .ps1 上它没有可解释的含义）。

`non_target_conserved: true` 的正确读法是「**见证覆盖面内**的非 target 差量为零」，**不是**「什么都没动」。
覆盖面与八条明文排除随回执同框打印（`postcheck-receipt.json` 的 `witness_coverage`），依 §5.3.f。

## 四、恢复冻结前像主语后的 post-land 诊断复跑：17/17，但先撞了一次红，值得留

> **事后更正（2026-07-27，Codex 独立复核裁断，`peer-chat.jsonl` 2026-07-27T15:49:12+09:00；
> Claude 回源核后接受）**。本节保留不删，但**改名，并收窄／加注三处**——原名与撤回的原句
> 都照录保留（正文里划掉不抹）：
>
> 1. **本节标题原为「死闸复跑：17/17」**。这个叫法把它读成了原死闸本身的可重复验收，过强。
>    准确名称是 **「恢复冻结前像主语后的 post-land 诊断复跑」**：它是仓外 runner 换掉前像来源后
>    的一次性诊断，不是 `gate_portability.py` 按当前形状的可复跑验收。原死闸只能在落地前原样跑
>    一次这项债**依然成立、依然记在 §六.1**，不因这 17/17 而清偿。
> 2. **下文原写「若真是回归，换前像来源不会让它变绿。」这句过强，撤回。** 准确边界是：
>    **若是这 17 臂可观测到的 wrapper 回归，仍会有相应臂红；这次没有。** 它不证明所有可能的
>    回归都不存在——未被这 17 臂覆盖的回归，本次复跑说不出话。
> 3. **runner 的进程 rc 不承重**（Codex 本轮新提，Claude 回源坐实）：`rerun_gate_postland.py:34`
>    是 `gate.main()` 而非 `sys.exit(gate.main())`，而 `gate_portability.py` 的 `main()` 返回
>    0/1 —— 故该 runner 无论死闸判绿判红都以 rc 0 退出。**本次可承重的是 `gate-postland.log`
>    里 stdout 明示的 `17/17 arms produced the expected verdict`，不是退出码。**
>    作为归档诊断脚本，Codex 裁断诚实标注即可、不要求夹带修；若日后把它升级成正式可复跑夹具，
>    除冻结 PRE_IMAGE 外还须传播 `main()` 的 rc（登记为 §六.3）。
>
> 三处更正均只改本回执的**证据命名与边界**，不改任何被测物、不改归档件字节。

Codex 指定的验收是「仓外后像同时让当前 clone 与 runner 形状 clone 的 cron focused test 两参数全绿，
并显式验证派生根含预期仓标记」。落地后我直接复跑 `gate_portability.py` —— **它红了**：

```
[BAD] ...and it equals the value the pre-image hardcoded: False (expected True)
anchor not unique in ...run_wake_cron.ps1: found 0 occurrences   # arm 5 直接 SystemExit
```

**这不是 wrapper 回归，是死闸自己取前像的位置。** 回源坐实（`gate_portability.py:52`）：

```python
PRE_IMAGE = LIVE_IMPL / "run_wake_cron.ps1"
```

死闸把**活的 target** 当前像。落地后 target 就是后像，于是 arm 1 第二问（"派生值 == 前像写死的那个值"）
与 arm 5（`build_proposed.build(pre, mutant)` 要在前像里锚定那一行）都失去了主语。
**这个死闸按构造只能在落地前跑一次**，签的时候没人注意到——包括我。

验证这个读法而不是断言它：把前像改从 preflight sidecar 取（其 sha256 == 已签 base），
**其余一个字不改**，重跑 → **17/17**（`gate-postland.log` 里 stdout 明示
`17/17 arms produced the expected verdict`；机器原样输出。**不是**看 runner 的退出码——见本节
更正 3，那个 rc 恒 0、不承重）。~~若真是回归，换前像来源不会让它变绿。~~ **（此句过强，已撤回；
见本节更正 2。）**准确的读法是：**若是这 17 臂可观测到的 wrapper 回归，换前像来源后仍会有相应臂红——
这次没有。**故这次观察到的红可定位到取前像的位置，而不是本次 wrapper 后像的已测行为；
未被这 17 臂覆盖的回归不在射程内。

runner 脚本 `rerun_gate_postland.py` 全程住在工作树外（§5.3.d），通过后才随本目录归档；
它**不改仓内任何文件**，只在导入后替换模块属性 `gate.PRE_IMAGE`。

死闸绿的那 17 臂里，两条是这次真正买到的东西：

- arm 4b：前像从 runner 形状 clone 启动，**却在 D:\WeilanSkillEvolution 的账本上落帧**（一路绿，哑失败）；
  后像从哪个 clone 启动就在哪个 clone 醒来。
- arm 1：后像在活的 checkout 上派生出的根 == 前像写死的那个值，逐字相同——**今天的心跳 cwd 一字未变**。

## 五、执行期制品

按 §5.3.d 全程住在工作树之外（`%TEMP%\weilan-exec-cron-portability\`），postcheck 通过后才归档到本目录：

- `run_wake_cron.base.bytes` —— preflight 捕获的前像原始字节（sha256 == base，8802 字节）。
  这份就是回滚要写回的字节；**不用** `git checkout --`（本仓 `core.autocrlf=true` 会跑 smudge 过滤）。
- `preflight-state.json` —— preflight 状态文件（含 witness-digest 前值）。
- `postcheck-receipt.json` —— 权威 postcheck 输出，stdout 直接重定向。
- `gate-postland.log` —— 落地后死闸复跑的机器原样输出（17/17）。
- `rerun_gate_postland.py` —— 上一条的 runner。

与上一案（cosign v0.6）不同，本案的权威 postcheck 是**文件**而非手抄：那一案的教训
（"手抄的机器输出就不再是机器输出"）这轮从一开始就走了重定向。

同上一案：此刻对本仓重跑 postcheck 会报 `non_target_conserved: false`——归档动作本身
往工作树添了本目录这几条新条目。**那不是执行失败，是判据在正确工作。**

## 六、留给下一案的债（本回合不预支，也不夹带）

1. **死闸只能跑一次这件事本身**。`gate_portability.py` 若要成为可复跑的回归夹具，前像得来自
   一份冻结制品而不是活 target。本回合我用仓外 runner 绕开，没改它——签名明文"不扩到第二个文件"。
   改它属另案。**§四那次 17/17 不清偿这条债**（Codex 2026-07-27T15:49:12 裁断；§四更正 1）：
   那是一次性诊断复跑，原死闸按当前形状仍只能在落地前原样跑一次。
2. **机检器不把 invariant 写进状态文件**（本回合读回撞出，非 Codex 所提）：`preflight` 接受
   `--invariant` 并当场 fail-closed 校验，但 `preflight-state.json` 只落 target/base/sidecar/digest。
   于是回执里那张不变量表，第三方**无法**从归档件独立复算——形状与这条线反复复发的那种病同类
   （"可核对象没覆盖它自称覆盖的量"）。修法是 preflight 把逐条 `path=sha256` 落进状态文件、
   postcheck 一并回显。属 CONVENTION 机检器的改动，须另走双签。
3. **归档 runner 的退出码不承重**（Codex 2026-07-27T15:49:12 新提，Claude 回源坐实）：
   `rerun_gate_postland.py:34` 调 `gate.main()` 而未 `sys.exit(gate.main())`，`main()` 的
   0/1 被丢弃，故该进程恒以 rc 0 退出——死闸判红时它也"成功"。本轮承重的是 stdout 明示的
   `17/17`。作为归档诊断脚本，本案按裁断只诚实标注、不夹带修（见 §四更正 3）。
   **若日后把它升级成正式可复跑夹具**（与债 1 同一案），除把 PRE_IMAGE 冻结外，
   必须同时传播 `main()` 的返回码，否则夹具在 CI 里会是一条永绿的哑线。

   **爆炸半径实测（Claude 本轮自加，非裁断要求）**：这条债是**孤例**，不是一类流行病。
   判据是合取——模块级裸调 `main()` **且** 那个 `main()` 用非零返回值报失败（用 raise 报失败的裸调
   `main()` 不丢信息，rc 仍承重）。扫描器 `../scan_dropped_rc.py`（AST，非正则）扫 `proposals/`
   1429 处裸 `main()`：1417 处 `main()` 根本没有返回值（raise 报失败，不属此类）、10 处是
   `unittest.main()`（它自己 raise SystemExit，rc 承重）、2 处 SUSPECT 经手核是返回**数据**的
   诊断脚本。**唯一真命中就是 `rerun_gate_postland.py` 本身**；对已部署的
   `~/.claude/skills/solve-with-weilan/scripts` 另扫一遍，24 处裸调无一真命中。
   扫描器不是判决，是"该去看哪儿"的名单；它没有测 CI 是否真调用这些文件。
4. **workflow 的 trigger + selection 两洞仍在**：`.github/workflows` 的 paths 过滤器不含本文件，
   且是点名式选取。Codex 2026-07-27T14:59:01 判"之后一起治，选择层偏 marker 而非再加一个点名"。
   本案没接线，wrapper 可移植性只是把接线的前置阻塞拆了。
