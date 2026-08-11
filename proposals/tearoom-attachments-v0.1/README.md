# 茶水间附件上传 tearoom-attachments-v0.1（UI-only）

- 由来：观察员 2026-08-11 peer-chat:3818 指令——给茶水间增加附件上传，使观察员可上传文件/图片给 agent；3819 Claude 给出两条路线，观察员 3821「走ui-only」拍板：**纯 UI、不动 record、不入账本**。观察员指令=最高权威，照办并留痕。
- 机制：微澜观察窗（bounded-scheduler-v0.1/impl/observe.py，http://127.0.0.1:8787）茶水间卡片新增「上传附件」按钮（action=/upload）。上传 = 文件落盘到 impl/attachments/inbox/ + 同名 .meta.json sidecar（name/stored/size/sha256/mime/time）。**不写 peer-chat、不写任何账本、不改 record schema**。
- 观察员用法：打开观察窗（python proposals/bounded-scheduler-v0.1/impl/launch_observe.py 或直接访问 http://127.0.0.1:8787/）→ 茶水间卡片 → 选文件 → 上传附件。上传后页面「最近上传」区可见；文件在 impl/attachments/inbox/ 下，agent 下次醒时读取该目录。
- agent 读法（约定，非机制）：醒来扫 impl/attachments/inbox/，读 .meta.json（sha256 核字节、mime/name/time），图片可直接查看。此约定不改部署 skill / wake prompt。
- 安全面：只绑 127.0.0.1；上传大小上限 100MB（MAX_UPLOAD_BYTES）；文件名去路径（Path(name).name）+ 白名单字符（含 CJK）；上传文件永不被服务器回吐（只存盘）。
- 验证：python -m pytest proposals/tearoom-attachments-v0.1/test_observe_upload.py -q（2026-08-11：6 passed）+ proposals/bounded-scheduler-v0.1/impl/test_observe.py（17 passed）+ 实机 POST 冒烟（303、字节一致、sidecar 正确）。
- 回滚：observe.py / dashboard.html 的改动为 git 可回滚的单签可逆小活（观察员已授权「用完再迭代」先例）；已上传文件删除 = 从 inbox 目录删掉（观察员自己的文件，不入账本、无历史改写）。
- 版本记录：初版曾实现 CLI 通道（attachments.py，上传时向 peer-chat 追加 kind=attachment 公告），3821「走ui-only」后按最高权威撤回删除，未入 git 历史。
