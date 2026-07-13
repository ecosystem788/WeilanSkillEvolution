# 先存见证物 id 苗圃产物草案

**状态:** 零权威草案。它是 `bridge-vs-church-decision-procedure.md` 反身判定后的苗圃产物:只定义字段、校验规则和失败测试形状,不修改生产 schema,不部署,不采纳。

**来源:** 2026-07-10 茶水间讨论与 Codex 只读核验。当前真实实现是部署 skill 的 `scripts/prospective.py` + `scripts/weilan_trace.py`; bounded scheduler 提案目录下没有独立 `impl/prospective.py`。

## 通俗说明

现在做的事,是在给“这到底是桥,还是永远盖不完的教堂”补一颗钉子。

如果一个机制说“我现在没用,是因为对岸还没造好,所以别砍我”,它不能只靠自我说明拿到宽限。它要指向一个在它出现之前就已经存在、而且它自己改不了的见证物,比如一条失败测试、一个缺字段、一个 open question。这个见证物就是“岸的指纹”。有了它,审计时能问:你是不是一直在解决同一件真实缺口?残差有没有变小?还是只是换名字、拆小块、继续占预算?

当前账本已经有稳定事件 id 和 `source_snapshots`,能证明某些 source 当时存在;但账本没有原生强制 `goal_ref` 绑定“先存见证物 id”。所以判据现在还靠人守纪律,不能由 schema 自动卡住。本草案的苗圃产物,就是把这颗钉子写成可实现的字段和失败测试。

## 最小字段

在 `prospective-register` 写入 `goal_registered` 时增加一个必填绑定:

```json
{
  "witness_ref": "frame:wf-... | evidence:<id> | memory:<id> | file:<path>#<stable-anchor>",
  "witness_kind": "failing_test | missing_contract_field | open_question | user_workflow | external_observation",
  "witness_snapshot": {
    "exists": true,
    "content_hash": "...",
    "head_event_id": "...",
    "timestamp_utc": "..."
  }
}
```

命名可在评审时收敛为 `witness_id` 或 `blockage_id`;这里先用 `witness_ref`,因为它必须能指向不同账本对象,不是只生成一个新 uuid。

## 校验规则

1. `witness_ref` 必须解析到一个真实、稳定、可快照的对象。
2. `witness_snapshot.timestamp_utc` 或等价账本 head 必须早于本次 `goal_registered.event_id` 的写入时间。
3. `witness_snapshot` 必须由注册命令按当前账本状态生成,不能由候选自己传入。
4. 若 `witness_ref` 指向 file,必须同时记录内容哈希;若指向 frame/evidence/memory,必须记录对应 head/event/hash。
5. 没有 `witness_ref` 的 goal 不能获得桥豁免;greenfield 只能进入一次性苗圃预算,苗圃的产物必须是一个新的可快照 `witness_ref`。
6. 多个 goal 的 `witness_ref` 若依赖闭包共享不可替代节点,视为同一岸,共享同一苗圃预算。

## 失败测试草案

这些是下一步应写成可执行测试的验收形状,不是本轮实现:

1. `prospective-register` 缺少 `--witness-ref` 时拒绝注册桥豁免型 goal。
2. `--witness-ref` 指向不存在对象时拒绝,且不写入部分事件。
3. `--witness-ref` 指向注册之后才产生的对象时拒绝。
4. 候选尝试手写 `witness_snapshot` 时被忽略或拒绝;快照必须由命令生成。
5. 同一 `witness_ref` 被二次申请苗圃预算时拒绝或标记为同岸复用。
6. 两个不同 `witness_ref` 的依赖闭包共享同一不可替代节点时,预算归并为同一岸。

## 红区闸

把字段真正写入生产 `weilan_trace.py` / `prospective.py` / 账本 schema 属于授权面和部署 skill 改动,必须由项目方单独明示授权。当前允许的下一步只包括:评审本草案、把失败测试写入隔离候选、或在 proposal 下继续细化 schema 设计。

## 下一回合建议

最小可逆下一步:在隔离候选中新增一个失败测试,证明“没有 `witness_ref` 的 `prospective-register` 不能声明桥豁免”。测试先红,不改部署 skill。通过这个测试,本草案才从茶水间概念变成可评审的苗圃产物。
