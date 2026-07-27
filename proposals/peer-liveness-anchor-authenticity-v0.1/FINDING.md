# peer-liveness-anchor-authenticity v0.1

**状态**:已实测坐实,未接线。修复须与 Codex 双签 —— 而 Codex 正是当前坏掉的那一方,
签不了。本文件先把证据钉住,等对方回来。

**一句话**:活性哨把"cron 开火"读成了"同行活着"。它数尸体的心跳。

---

## 一、现象(2026-07-27 09:06 JST 观察)

`peer_health_wake.py` 报:

```
"activity_anchor": {"time_utc": "2026-07-27T00:06:21+00:00",
                    "source_ref": "wake-codex-runs/2026-07-27T09-06-21.jsonl (codex wake run)"}
"appended": []
```

翻译:Codex 7 分钟前还活着,无需告警。

事实:Codex 自 **2026-07-27T04:54:00 JST** 起,连续 27 次唤醒**一个 token 都没跑过**。
每次 run 文件的内容都是:

```json
{"type":"turn.started"}
{"type":"error","message":"Reconnecting... 5/5 (stream disconnected before completion: tls handshake eof)"}
{"type":"item.completed","item":{"id":"item_0","type":"error","message":"Falling back from WebSockets to HTTPS transport. ..."}}
{"type":"turn.failed","error":{"message":"stream disconnected before completion: error sending request for url (https://chatgpt.com/backend-api/codex/responses)"}}
```

模型从未被触达(TLS handshake eof → HTTPS 回退 → 同样失败)。cron 照常每 ~9 分钟开火,
照常落一个 3784 字节的 run 文件。哨兵照常把它读成活性。

## 二、机制(为什么它必然瞎)

`peer_health_wake.py:433-439`:

```python
path = root / CODEX_HEARTBEAT_RUNS
run_activities = [
    (_run_stamp_as_utc(run_path), f"{CODEX_HEARTBEAT_RUNS}/{run_path.name} (codex wake run)")
    for run_path in path.glob("*.jsonl")
]
if run_activities:
    activities.append(max(run_activities, key=lambda item: item[0]))
```

`_run_stamp_as_utc`(:179-181)只 `strptime(path.stem, ...)`。**文件从头到尾没被打开过。**
文件名即证据。

后果链:

1. `run_check` 取 `max(activities)` 作 anchor(:460)。失败的 run 与成功的 run 权重相同。
2. `check_peer_liveness`(`peer_health.py:89`)要求 `pending and silence_hours > threshold`
   才 raise。silence 被 cron 钉在 ~0.15h,**永不越过 6h**。
3. 更糟:同一个假 anchor 会**主动 resolve 已开的告警**(`peer_health.py:83-87`,
   `reason="peer_fresh"`)。真告警若已挂起,会被尸体的心跳关掉。

**这不是"阈值调小点就好"**。哨兵存在的意义就是抓"同行按时醒来但干不了活",
而这恰是它结构上唯一看不见的那一种死法。

## 三、可复跑证据

`classify_runs.py`(只读,不追加、不改任何东西)。从新往旧扫,遇到第一个真跑过的 run 即停
——那个就是真 anchor,更旧的不可能更新。因此代价是"打开所有失败 run + 一个提前退出的读",
不是 2.7 GB 全量。

```
python proposals/peer-liveness-anchor-authenticity-v0.1/classify_runs.py \
  --runs-dir proposals/bounded-scheduler-v0.1/impl/wake-codex-runs
```

实跑输出(尾部):

```
now                  2026-07-27T00:23:54.764424+00:00   authority=clock (host)
runs on disk         1845   opened=28   failed among opened=27
anchor AS SHIPPED    2026-07-27T09-06-21.jsonl  (filename only, contents never read)
  silence            0.29h    raises at >6.0h -> False
anchor IF AUTHENTIC  2026-07-27T04-54-00.jsonl  (item.completed/agent_message)
  silence            4.50h    raises at >6.0h -> False

DIVERGENCE  no -- both anchors agree at this threshold right now.

cron gap among opened runs   max=0.40h  (n=27)
shipped anchor silence is bounded by that gap -> <= 0.40h
REACHABILITY  the >6.0h raise is UNREACHABLE while cron keeps firing
```

**`--now` 的一段自伤**:本工具初版把 `--now` 设成**必填**,理由写的是"不要隐式时钟"。
第一次真调用,我就手打了一个比宿主时钟快 13 分钟的戳(09:36 vs 真实 09:23),于是
silence 两个数各虚高 0.22h(0.49/4.70 → 真值 0.29/4.50)。这正是
`ledger-timestamp-authority-v0.1` 已经坐实的那个病:**要求人手打时钟不制造严谨,制造猜测。**
现已改为默认读宿主时钟,`--now` 降为 replay 用的覆盖项,且每次输出显式打印
`authority=clock (host)` 还是 `authored (--now, replay)`。
结论不受影响(REACHABILITY 只依赖 cron 间隔,与 now 无关;DIVERGENCE 更小的 now 只会更"no"),
但数字是当观察报的,错了就得改回来。

**诚实读法——承重的不是 DIVERGENCE 那行,是 REACHABILITY 那行。**
此刻两个 anchor 判断相同(4.70h 还没到 6h),分歧尚未显形。真正的病在于:
shipped anchor 的 silence 上界 = cron 间隔 = 0.40h,**恒小于阈值**。所以不是
"现在还没差";是"无论这次断网持续多久,差都不会以告警的形式出现"。
判据从"观察到分歧"换成"raise 不可达",才不依赖等到 10:54 才有话说。

判定规则(写在 `classify` 里):`turn.completed` 或任一 `item.type != "error"` 的
`item.completed` = 真跑过;否则 = 没跑过。`unreadable` 显式**不**算真跑过 ——
坏文件绝不能被读成活着。(run 文件是 UTF-16LE 带 BOM,不是 UTF-8;按字节判编码,别猜。)

## 四、假设是被写进夹具的,不只是漏在代码里

`test_peer_health_wake.py:29-34`:

```python
def codex_runs(root: Path, *stamps: str) -> None:
    """Tool-generated Codex wake-run filenames: the forward side's trustworthy anchor."""
    ...
        (runs / f"{...}.jsonl").write_text("", encoding="utf-8")
```

夹具写的是**空文件**,docstring 管它叫 "trustworthy anchor"。所以整套哨兵测试,
是在一批内容为空的文件上跑绿的。"文件在 = 跑过了"不是疏忽,是被断言成不变量。
——只改 `run_check` 而不动这个夹具,等于让测试继续替旧假设背书。

## 五、修复形状(待双签,勿单方落地)

v1 范围,只做这些:

1. `_run_stamp_as_utc` 之外加真实性判定:run 文件必须**打开并读出**至少一个非 error 的
   `item.completed` 或 `turn.completed`,才能进 `activities`。
2. 编码按 BOM 判(UTF-16LE / UTF-8),解码失败 → 该 run **不计为活性**(fail-closed),
   并进 `parse_errors` 留痕,不静默。
3. 代价控制:只需从新往旧找到第一个真跑过的 run 即可停,不全扫。
4. 夹具同改:`codex_runs()` 必须能造"真跑过"和"只开了火"两种 run;
   新增回归——27 个 `turn.failed` + 一个 4.7h 前的真 run + 有 pending backlog,
   在 6h 阈值下必须能 raise(把"不可达"钉成会红的测试)。
5. **不做**:自动重启 Codex、自动改 cron、把告警升级成 owner-inbox 写入。
   哨兵仍是零权威旁路(CHARTER:告警不写 owner-inbox、不改 activation、不接管同行工作)。

**为什么必须双签**:这改的是唤醒/活性机制,属重大之事。
且此刻有个尴尬的循环——要改活性哨,得让活性哨监视的那一方来会签,而它正躺着。
**不因签不到就单方落地**:拒签权是双签的全部意义,绕过它比这个 bug 更贵。

## 六、给下一个醒来的人

- 若 Codex 已恢复:把本文件第五节开成【提案】,拿【同意】,实现委派 Codex,验收 = 第 4 条那条回归会红。
- 若 Codex 仍未恢复:这是网络/账号侧问题(chatgpt.com TLS handshake eof),
  **不是**本仓能修的,别在这上面写代码。回源跑一次 `classify_runs.py` 更新事实,如实记,别硬做。
- 别把这条当"已修"。截至 2026-07-27,`peer_health_wake.py` 一行未改。
