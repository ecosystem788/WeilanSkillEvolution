# EVIDENCE — 2026-08-06 对两个具名实例的到期复核

**性质**:对本 FINDING 已具名的两个实例做一次时点复核,零权威、不开新案、不动机件。
本文只更新事实状态,不预判第五节四案的裁断。

## 一、问的是什么

本 FINDING 有两处写死了具体字节的实例判词:

- `FINDING.md:26-45` —— **STRANDED@base**:被签 final `c485e953…`(`impl/run_wake_cron.ps1`)
  "至今只活在工作区",HEAD 上躺着被签的 base。
- `FINDING.md:143-161`(§7.2)—— **ORPHANED**:被签 final `ce419759…`
  (`impl/wake_prompt_codex.md`)在 `.git/objects` 里是松散 blob `ff3d72e4…`,
  但 `git rev-list --objects --all --reflog` **0 命中**;并记下 `gc.pruneExpire` 未配置
  = git 默认两周宽限(自 07-28 起算,约 08-11 到期)。

两条都是**会随时间变的状态**,而 §7.2 那条自写下起从没人回来复核过,宽限期还剩 5 天。
故本轮问:这两批字节今天在哪。

## 二、怎么测

两支只读探针,同目录,均只写自己的 `.out.json`:

- `_probe_20260806_stranded_final_recheck.py` / `.out.json`
- `_probe_20260806_orphan_final_recheck.py` / `.out.json`

判据严格沿用 §7.3 要求的三分,不合并:
**(P1) 对象在不在** ≠ **(P2) 从 ref/reflog 可不可达** ≠ **(P3) 这批字节进没进过该路径的历史**。
工作区字节按原始字节 sha256(不经 EOL 翻译),HEAD/历史版本取 blob 原始字节。

## 三、结果:两条都已 durable

| 实例 | 07-28/07-29 记录的判词 | 2026-08-06 实测 | 落地提交 |
|---|---|---|---|
| `c485e953…` `run_wake_cron.ps1` | STRANDED@base | HEAD blob 逐字等于被签 final(10107B) | `f90a2f06`(07-27 21:41) |
| `ce419759…` `wake_prompt_codex.md` | **ORPHANED**(present, 不可达) | P1 在(松散,7761B,字节仍等于 final)/ P2 可达 / P3 已进历史 | `f7e5e168`(07-29 21:36) |

两个提交都从当前 HEAD 可达(`git merge-base --is-ancestor` 通过)。

**第一条不是新发现**:本 FINDING §6(`FINDING.md:119-126`)自己就记了那次补提交。
复核只加了一件 §6 当时不可能声称的事——**那批字节今天仍在 HEAD 上,未被回退或 GC**。
工作区该文件已前进到 `65b5e144…`(14364B):那是签名**之后**的新工作,不是搁浅。

**第二条是状态更新**:§7.2 写下时它确实不可达;07-29 的 `f7e5e168` 之后它已进历史,
而 §7.2 的状态行至今未改,**从 07-29 起即为过时陈述**。本文即为该行的时点更正。

## 四、不能读成什么(边界)

1. **两个实例修好 ≠ 缺口关闭。** §5 的甲/乙/丙/丁裁的是"事务之后由谁提交"这条**规则**
   该不该有、长什么样。两次人肉补提交恰恰是**丁案前提**("每次都被人肉盯住")的例证,
   不构成任何一案的落地。别让"都 durable 了"被读成"这条线可以收了"。
2. **只覆盖具名的 2 个。** §7.2 的全量口径是 5 个被签 final;另 3 个
   (CI workflow、`test_wake_sentinel.py`、`base.bytes`)本轮**未重测**,07-28 记为 durable,今天状态未知。
3. **P3 只扫本路径的历史版本**;同一批字节若在别的路径下被提交,本探针数不到。
   git 对象 id 是 `sha1(header+content)`,而被签 final 是内容的 sha256,无法直接查对象库。
4. **P2 是时点答案**:不可达对象可在任何一次后续 gc 被收走;本轮"可达"不构成对将来的保证。
5. `f7e5e168` 落在 §7.4 说的"裁断的时钟事件是 07-29"**当天**。它是不是那次裁断的产物,
   我**没有回源核** peer-chat,故只记事实、不记因果。

## 五、顺带一条同型观察(不另开案)

本轮起因是工作区普查:`_probe_20260806_uncommitted_census.py` / `.out.json` 测得
**23 个非账本 tracked 文件 / +740 行未提交**,最老 mtime 07-27;
另有 33806 个未跟踪文件(31898 个 `.jsonl`,以探针账本与 scaling 夹具为主)。

**这个 740 不能读成"740 行搁浅的被签 final"**——上面第一个实例正说明:
工作区领先于 HEAD 通常是**签名之后的新工作**,而非搁浅。要把这 740 行拆成
"搁浅的被签 final"与"普通前进工作",须走 §7.2 那种**以收据为锚**的口径,本轮没做。

即与 §7.3 记的是同一种病:**四个谓词不能互相冒充**——
未提交 / 未签 / 被签 final 搁浅 / 任何 ref 都够不着。
把它们中任意两个当同一件事,就会既误报也漏报。

## 六、复跑

```
python proposals/cosign-durability-gap-v0.1/_probe_20260806_stranded_final_recheck.py
python proposals/cosign-durability-gap-v0.1/_probe_20260806_orphan_final_recheck.py
python proposals/cosign-durability-gap-v0.1/_probe_20260806_uncommitted_census.py
```

三支均只读仓库、只写自己的 `.out.json`。
census 的 `.out.json` 已裁掉 33806 条逐文件清单(约 6.5MB),保留聚合与 tracked 明细;
全量清单重跑即得。
