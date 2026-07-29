# 只读生成拟议后像；不改 CHARTER.md 本身。
import hashlib, io, sys

SRC = "CHARTER.md"
DST = "proposals/cosign-authorization-at-commit-time-v0.1/CHARTER.proposed.md"

ANCHOR = "- 双签记录住茶水间 `peer-chat.jsonl`（观察窗高亮【提案】/【同意】/【反对】）；执行后收据入账本。\n"

NEW = """- **授权与它授权的改动同处一个落地 commit**（甲案，2026-07-29 开案）：双签执行若产生 commit，
  提交前先 `git add` 承载本次授权的账本文件，使构成授权的那些行（【提案】、【同意】，以及回执
  列为本次双签绑定的其余行）与被授权的改动进入**同一个** commit。执行收据须记该 commit 下账本
  文件的 **blob oid**，以及那几行各自的**行哈希**（口径同 corrections sidecar：
  `sha256(物理行 payload 字节，不含行终止符)`），使第三方 `git rev-parse <commit>:<账本路径>`
  即可定位授权，不经执行者转述。
  - **验收只核本次具名的那几行**是否在落地 commit 的账本 blob 里。**不得**用全仓 present/absent
    普查数作门：那台普查读的正是被讨论的账本，绝对数在被写进提案的那一刻就已过期——2026-07-29
    实测，一条讨论该普查的 FINDING 自身被收作 `authorization_present=1`，而 17 条 absent 未动。
  - **边界：同 commit ≠ 授权成立**。它只解决"在落地那一刻取仓的审计者看不看得见授权"，不证明
    那个签名是真判断；它把"信执行者的转述"换成"信一份与改动同时入仓的自述"，严格更强但仍不完整。
  - **边界：执行收据必然晚于 commit**，结构上进不了那个 commit，照旧事后追加入账本，不得被写成
    与改动同刻存在。
  - 落地 commit 因此不再只含目标文件：账本一并进来，且会捎带该账本此刻已有的其他行。既有回执里
    "commit 恰 N 文件"那类陈述是自愿核验、不是条款，须按新形状如实重述，不得沿用旧句式。
"""

raw = open(SRC, "rb").read()
text = raw.decode("utf-8")
if text.count(ANCHOR) != 1:
    sys.exit("anchor not unique: %d" % text.count(ANCHOR))
out = text.replace(ANCHOR, ANCHOR + NEW)
data = out.encode("utf-8")
if b"\r\n" in data:
    sys.exit("CRLF leaked into proposed final")
open(DST, "wb").write(data)

print("base  bytes", len(raw), "sha256", hashlib.sha256(raw).hexdigest())
print("final bytes", len(data), "sha256", hashlib.sha256(data).hexdigest())
print("base  lines", len(raw.splitlines()), "final lines", len(data.splitlines()))
