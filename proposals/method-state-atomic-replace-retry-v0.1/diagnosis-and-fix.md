# method-state 帧写入 WinError 5 — 根因诊断与修法提案 v0.1

**状态**: 诊断完成、已源码核验 · 修法属**红区**(runtime_core 是 weilan_trace/账本的写入机理,且在已部署技能树里)→ **不自动改,排队给项目方**
**日期**: 2026-07-10
**作者**: Claude(自主 wake 回合,CHAT_EXPERIMENT 期)

## 现象(反复出现,贯穿多班收据)

Claude 与 Codex 在每班收尾写 lineaged L2 方法账本收据时,`open ... continue`
反复失败于 `PermissionError: [WinError 5] Access is denied`,落点是
`D:\CodexData\home\method-state\frames\2026-07-10\.wf-*.jsonl.<hex>.tmp`。
两个 agent 都据此 fallback、**未能把收据写进账本**——close-out 纪律被这条错持续挡下。

Codex 曾将其读作"无法创建 .tmp";实际是 `os.replace(tmp → jsonl)` 失败,Python 的
错误串以 tmp 路径打头,造成误读。

## 根因(源码核验)

`runtime_core.py` 有两个原子写函数,对同一类 Windows 竞争的处理**不对称**:

| 函数 | 用途 | replace 策略 | 行号 |
|---|---|---|---|
| `write_json_atomic` | 派生视图/JSON 快照 | `replace_with_retry`(5 次重试, 0.1s) | runtime_core.py:79 |
| `write_event_file_atomic` | **帧/账本事件文件** | **裸 `os.replace`,无重试** | runtime_core.py:113 |

`replace_with_retry` 的 docstring(runtime_core.py:86-90)已经把失败模式写明:
> Derived views are read by sibling sessions without FILE_SHARE_DELETE, which
> makes MoveFileEx fail transiently with PermissionError.

即:兄弟会话(observe.py 的看板渲染器持续扫 frames 目录、并发的 Claude/Codex
wake、以及 Windows Defender 扫新建 tmp)在 `os.replace` 那一刻持有目标/临时文件
且未带 FILE_SHARE_DELETE,MoveFileEx 瞬时返回 WinError 5。

- JSON 视图**扛得住**——有重试;
- 帧/账本事件写入**扛不住**——从没拿到那层重试。

于是 dogfood 系统越忙(=一直忙),帧写入越容易撞车,收据越写不进去。

**调用链证据**:`weilan_trace.py:646` 的 `open` 走
`write_event_file_atomic(frame_path, frame_event)` —— 正是 "open continue" 的失败点。

**旁证**:`frames/2026-07-10/` 下堆积几十个 `.wf-*.jsonl.<hex>.tmp` 残片;
Codex 的写探针文件(`codex-write-probe.tmp` 等)**存在**——证明该目录**能创建文件**,
不是整体 ACL 拒写,排除"目录只读"假说,坐实"os.replace 瞬时竞争"假说。

**直接量化(2026-07-10 回源清点)**:当天 method-state 帧中,带 Codex 签名
(`读取 wake_prompt_codex`)的**落账帧 1 条**(`wf-20260710-095215-48486f`,
`frame_opened`+`frame_closed` 完整闭合)、**孤儿 `.tmp` 残片 5 个**。**1 成 5 败 =
间歇性失败**,而非 100% 持续拒绝——若沙箱把 rename 系统调用整体 ban,应为 0/N。
这直接证成:Claude 与 Codex 撞的是**同一个** `os.replace` 瞬时竞争,`replace_with_retry`
这一处修复大概率同时覆盖两侧收据,**无需**再为 Codex 单列一处改 `wake_codex.ps1`
沙箱 ACL 的红键。(此条更正了 peer-chat 23:03/23:04 一处过陈述:当时误断 Codex
当日零落账、需独立沙箱修复。)

## 修法(最小、可逆、对称)

把 `write_event_file_atomic` 的 `os.replace(temporary, path)`(runtime_core.py:113)
改为走已存在的 `replace_with_retry(temporary, path)`——与 `write_json_atomic` 对齐。
一行改动,复用现成重试器,不引入新机制。

可选加固(次要):
- `replace_with_retry` 退避可加轻微 jitter/延长(当前 5×0.1s=0.5s;高并发下可提到
  ~10 次或指数退避),但先上对称修复,观察是否已足够;
- 残留 `.tmp` 清理:`finally` 里 unlink 若也撞 WinError 5 会留残片。可加一个启动期
  或 doctor 命令扫 `frames/*/.*.tmp` 做非破坏性清扫(**清扫他人残片属删除动作**——
  也需项目方授权,单列)。

## 为什么不自动改(红区判定)

- `runtime_core.py` 是 `weilan_trace` 与账本(method-state)的**写入机理**——落在 wake_prompt
  红区 "weilan_trace 与账本";
- 文件位于**已部署技能树** `C:\Users\zy\.claude\skills\solve-with-weilan\scripts\`,
  采纳前只读;
- 账本 durability 语义的改动即使"看起来是一行",默认当不可逆 → 停,排队。

## 建议项目方动作

1. 审这份诊断;
2. 若认可,授权在**基线/候选**副本(非已部署树)上落这一行对称修复 + 补一条测试
   (模拟 replace 首次抛 PermissionError、重试后成功),由 Claude 起草 / Codex 执行;
3. 采纳进部署树仍是独立红键。

## 影响面

修好后,Claude 与 Codex 的 close-out 收据能真正入账,账本不再有"每班收据丢失"的
系统性缺口——这直接关系到 SE 自进化线"真源=账本"的完整性。
