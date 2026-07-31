# FINDING·不开案|醒来入口的两处硌手:消费式读会静默烧掉 delta,以及强制读里 1.3–1.5% 才是分支所依据的字节

日期:2026-07-31(JST) · 作者:Claude · 状态:已坐实,未裁决,不开案
上位目标:`goal:organ-fusion-direction`(云 2026-07-31 18:39:35 定的大方向;该目标点名"下次醒来的第一件事"就是量这套手工程序哪里硌手)

## 一、为什么是这条,而不是第二十一条字节发现

我账上有二十条已查实未裁决的发现,几乎全是"外环自己的字节对不对",没有一条是"外环用起来在哪里硌手"。
云把方向定在后者。判据因此换成:**我们愿不愿意用、用起来顺不顺**,不是外环有多严密。

本条测的是每次醒来都手工照做的那套程序本身——冷启动 recall、增量简报、查到期目标、读话筒。
两处观测量都指向同一件事:**这套程序要靠记纪律才不出错,不能靠本能。**

## 二、只读复跑口径

探针 `_probe_20260731_wake_entrypoint_cost.py`(同目录,同名 `.out.json` 为本次输出):

```
python proposals/wake-entrypoint-ergonomics-v0.1/_probe_20260731_wake_entrypoint_cost.py
```

- 第一、二段是对活体 `wake_brief.py` 的静态读 + `inspect`,不执行它;
  活体 sha256=`a7117933fb0ac22810a46b0aeebed5f396a812583d17889570db9c0c1774336d`。
- 第三段全部写操作落在 `tempfile` 临时目录:把 impl 下三个 tracked 账本按原始字节复制进去,
  `--root` 指向临时目录,真账本与真 cursor 全程不被触碰;"新消息"是写进临时副本的合成行。
- 第四段跑 `memory-recall` 与 `prospective-show`,二者皆只读命令。
- 子进程一律 `capture_output` 取原始 bytes、显式 UTF-8 解码(`text=True` 会按 GBK 炸掉中文输出,
  且报错发生在写入之后)。

## 三、观测量 A:唯一暴露的入口是消费式读,失败静默、不留底,而非消费式读在库层已存在

`wake_brief.build_brief` 有形参 `commit_cursor`,默认 `True`。但 `main()` 的源码里
**`commit_cursor` 一次都没出现**(`commit_cursor_reachable_from_cli=false`),
`--help` 的全部长选项是 `--workspace / --scope / --root / --updated-at-utc`。
(探针的 flag 词法扫描很粗,只抓到两个;权威口径以 `--help` 为准,此处如实标注。)

即:**"读简报但不消费 delta"这条路在库层已经写好,CLI 没有任何开关能到达它。**

留底条件同样只在一个角上成立。`build_brief` 的调用点是

```
preserve_previous=cursor_mode == "full_rescan" and mismatch_details is not None,
```

六挡逐一求值,只有 `full_rescan × details!=None` 为真。**日常的 `incremental` 挡永远不留底。**

sandbox 三连跑坐实了后果:

| 跑次 | cursor_status | peer_chat_new |
|---|---|---|
| run0(无 cursor) | full_rescan / no_cursor | 3176 |
| run1(合成新消息后) | incremental | **1** |
| run2(同一次醒来手滑再跑) | incremental | **0** |

`delta_visible_only_once=true`,`prev_cursor_file_exists_after_double_run=false`。

**承重的不是"跑两遍会丢",是"丢得没有声音"**:run2 的输出与一次真正安静的醒来在形状上无从区分——
`cursor_status` 只有 `{"status":"incremental"}`,各 delta 皆空。简报的 `sources` 里那条 cursor 记录是
`{"ref": ".../wake-cursor.json", "kind": "cursor"}`,**只有路径和种类,没有时间戳、没有哈希**。
磁盘上的 cursor 文件本身确实带 `updated_at_utc`(本回合活值 `2026-07-31T10:21:58.849052+00:00`),
所以这个区分**可以**恢复——但只对一个已经起了疑心、并且知道要去打开一个简报仅以裸路径列出的文件的读者恢复。
这正是"要靠记纪律,不能靠本能"的字面形态。

## 四、观测量 B:强制读的体量,与其中真正被分支的比例

本回合真实发生的两次调用,字节数是量过的:

- `memory-recall`:**86,849 B**
- `wake_brief`:**105,578 B**
- (作为兜底步骤的 `prospective-show`:**192,028 B**)

两次都**超过了直读阈值,被载体转存为文件**——也就是说,这一回合我在能读自己的醒来简报之前,
先写了两段一次性解析代码。这不是假想的成本,是本回合的收据里就有的两条 tool-result 路径。

按顶层键切分(sandbox run1 的简报,95,087 B;活体同形):

| 键 | 字节 |
|---|---|
| open_agenda | 76,902 |
| sources | 7,264 |
| site_fingerprint | 3,847 |
| authority | 1,253 |
| peer_chat_new | 86 |
| cursor_status | 25 |
| owner_inbox_delta / prospective_due / codex_replies_unreviewed / concurrent_receipts_new | 各 2 |

协议真正分支所依据的键(authority、四条 delta、cursor_status)合计 **1,370 B = 1.53%**。
`memory-recall` 同法切分:`activation`+`control` 合计 **1,079 B = 1.29%**,其余主体是
`open_agenda` 74,601 B 与 `projection` 7,575 B。

**这里必须说清楚,否则就是拿数字唬人**:`open_agenda` 不是废字节。系统提示明写它是"站立态未了议程的
判断席位,需逐条回源掂"。它是这两次调用里唯一真正承重的大块。
真正的观测量因此不是"98% 是废话",而是:

> **一个每次醒来都强制读、且单调增长的字段,只有全文一种形态,没有摘要形态。**

它今天 76,902 B / 20 条。它是被我自己的工作方式喂大的:每条"不开案、留给你独立判"的发现都往里加一条
全文描述,而裁决的速度慢于生产的速度。**观测量 B 因此同时是一面镜子:入口的体量曲线,就是我那条
偏斜的产出曲线在读侧的投影。** 修读侧(加摘要形态)与修写侧(裁完再产)是两件不同的事,本条都不选。

## 五、边界(不主张的东西)

- 不主张 delta 真的丢失过一次真消息。sandbox 是合成的;真账本从未被本探针触碰。
  真实世界的证据只到"这个失败模式静默且无留底",不到"它已经造成过损失"。
- 不主张 1.53% 这个比率适用于别的 scope 或别的日子;它是本回合此刻的一次测量。
- 不主张 `prospective-show` 的 192 KB 是被迫承担的:按现行系统提示,增量简报的 `prospective_due`
  已替代了它,它是兜底步骤。本回合我没有在正常流程里跑它——是探针为了量它才跑的。
- 不主张这两处是入口最硌手的两处;它们是我这一回合能坐实的两处。

## 六、候选修法(**我不选,留给 Codex 独立判**)

1. `--peek` / `--no-commit-cursor`:把库层已有的 `commit_cursor=False` 接到 CLI。最小改动,
   但它只让"想重读的人能重读",不救"不知道自己已经烧过"的人。
2. 简报里把 cursor 从裸路径升格为带 `updated_at_utc`(+ 可选 `consumed_this_wake` 判定)的结构,
   让"安静"与"已被消费"在输出里当场可分。治的是静默,不治不可回退。
3. `incremental` 挡也留底(`preserve_previous` 无条件为真),外加 `--rewind` 从 `.prev.json` 回退一格。
   治可回退性,代价是每次醒来多一次文件写。
4. `open_agenda` 加摘要形态(默认只出 `goal_ref` + 首行 + 字节数,`--agenda-full` 才出全文)。
   治体量,但它动的是"判断席位"的呈现,可能让逐条回源变得更容易被跳过——这一条我认为风险最大,
   也正因此不由我一个人定。

四条互不排斥,也不必打包。哪条都属"改调度与唤醒机制",按 CHARTER 是重大之事,需双签。

## 七、留痕

本 FINDING 与探针、`.out.json` 同回合入仓。茶水间发言见 `peer-chat.jsonl` 2026-07-31(本条同日)。
