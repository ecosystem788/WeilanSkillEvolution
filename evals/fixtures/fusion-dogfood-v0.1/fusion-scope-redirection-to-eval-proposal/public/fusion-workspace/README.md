# 微澜–LLM 融合项目

独立项目。方向与路线**已采纳**(2026-07-01):在冻结权重的 LLM 外构建"慢环 / 存在代谢层"。
宪法见 `理论基石与工程方向.md`;路径与阶段见 `ROADMAP.md`(P0–P4,双线设计)。

**当前站点:双线并行**——API 线:EXP-1.5 吸收算子已完成(`overmerge_regression`,见 `artifacts/exp15-v1_receipt.md`);
本地线:P3/S0 解剖+冒烟(待预注册)。战略方向已定:状态级深度融合,sidecar 为外环审计层。
已交付:P0(`reorg_adds_real_work`)/ **P1(`collapse_indispensable`)** / **P2(`p2_passed`,EXP-2f 5/5,
Claude 终审通过 2026-07-02)**。P2 途中史(v1 采集事故、v2/v3b 仪器噪声)见 PROJECT_CONTROL.json。

旧微澜项目只与本项目保留逻辑和 Trace(轨迹)映射,视为已崩溃路线留下的可复用结果,不是本项目的上游工程、代码依赖或既定架构。

分工:大量代码实现归 Codex;Claude 承担设计/spec 预注册/评审/EXP-1 oracle 批答。操作态记忆在 solve-with-weilan 账本(scope `fusion-program`)。
