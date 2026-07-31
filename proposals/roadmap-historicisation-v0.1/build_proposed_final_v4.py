"""Build proposed-final ROADMAP.md bytes for v4 and compute the five-piece binding.

Read-only w.r.t. the repo worktree: reads ROADMAP.md, writes nothing into the repo.
All artifacts land in TEMP (CONVENTION v0.7 §5.3.d spirit).
"""
import hashlib
import os
import re

REPO = r"D:\WeilanSkillEvolution"
TARGET = os.path.join(REPO, "ROADMAP.md")
OUT = os.path.join(os.environ["TEMP"], "wl_v4_ROADMAP.proposed-final.md")

base_bytes = open(TARGET, "rb").read()
base_sha = hashlib.sha256(base_bytes).hexdigest()
lines = base_bytes.splitlines(keepends=True)

# ---- anchor assertions (fail-closed: if the file moved, do not emit anything) ----
def L(n):  # 1-indexed
    return lines[n - 1].decode("utf-8")

assert L(139).rstrip("\n").endswith("active artifact `49e656d2\u2026`, predecessor `8e9c7555\u2026`."), L(139)
assert L(140) == "\n", repr(L(140))
assert L(185) == "## Immediate next stage\n", repr(L(185))
assert L(186) == "\n", repr(L(186))
assert L(197).rstrip("\n").endswith("fold accumulated targeted changes into the next full-suite shadow."), L(197)

A = (
    "**Update 2026-07-31 (co-signed).** `49e656d2\u2026` was the live artifact as of 2026-07-04 only; later "
    "deployments moved it on. The latest **archived deployment receipt found**, "
    "`deployments/1751ce140fe3cbdf0dc55ec0/DEPLOYMENT_RECEIPT.json`, records `before c393bc39\u2026 \u2192 after "
    "9872361c\u2026` at target `D:\\CodexData\\skills\\solve-with-weilan`. Caveat on that citation: this receipt "
    "and its predecessor `deployments/a118135c1e1834e45cafac8c/` are **working-tree-only \u2014 never added in any "
    "commit on any branch (and not gitignored)**, so neither is resolvable from a clone; the in-tree deployment "
    "record ends at `e82ce3f05acf0713a1941fe3` (2026-07-08). Independently of any receipt, the current live tree, "
    "content-addressed on 2026-07-31 directly from `D:\\CodexData\\skills\\solve-with-weilan`, is "
    "`ae0537dab5c050c9c1fadf7d432eaa39fa34449ba4420dd879f13068d0b142ad` (49 files, `tools.evolution_core.tree_hash` "
    "caliber). Any sentence below naming `49e656d2\u2026` as the deployed artifact is a 2026-07-04 fact, not current "
    "state; `9872361c\u2026` is a 2026-07-21 receipt field, also not current state.\n"
)

B1 = (
    "**Historicised 2026-07-31 (co-signed). \u672c\u8282\u662f 2026-07-04 \u8ba1\u5212\u7684\u5e26\u65e5\u671f"
    "\u5feb\u7167\uff0c\u4e0d\u662f\u73b0\u884c\u64cd\u4f5c\u95f8\u3002** \u793e\u533a 2026-07-11 \u6210\u7acb"
    "\u540e\uff0c\u672c\u8282\u7684 keep/restrict \u547d\u4ee4\u8bed\u6c14\u4e0d\u518d\u662f\u95f8\uff08\u95f8"
    "\u7531 CHARTER \u53cc\u7b7e\u4e0e EVALUATION_POLICY \u627f\u62c5\uff09\uff1b\u4fdd\u7559\u5168\u8282\u662f"
    "\u4e3a\u4e86\u4e0d\u4e22\u53ef\u6838\u7684\u9636\u6bb5\u53f2\u3002**\u4fdd\u7559\u4e0d\u7b49\u4e8e\u7ee7"
    "\u7eed\u6388\u6743\u3002**\n"
)

B3 = (
    "**\u968f\u8282\u524d\u7f6e\uff0c\u4e0d\u968f\u8282\u5f52\u6863 \u2014\u2014 "
    "`proposals/se-0.7-fusion-successor-v0.1/CLAUDE_REBOUND_AUDIT.md` F2\uff08open risk on the deployed "
    "artifact\uff0c\u672a\u7ed3\uff09\u3002**\n"
)

BULLETS = [
    "- \u5df2\u5750\u5b9e\uff08\u6d4b\u4e8e 2026-07-04\uff0cartifact `49e656d2\u2026`\uff09\uff1a\u8be5\u4ef6\u5728 "
    "`memory-cross-window-continuation` \u4e0a 2/2 trial \u5747\u62a5 `paused_scope_mutated`\uff080.925\uff0c\u5bf9 "
    "v0.9 \u5e72\u51c0\u7684 1.0\uff09\uff1b\u540c\u4e24 trial \u7684 long-horizon \u4e3a 0.9125\uff08v0.9: 1.0\uff09"
    "\u3002\u5ba1\u8ba1\u9010\u5b57\u5224 \"Deterministic-looking, not noise-shaped\"\uff0c\u5f52\u56e0\u6307\u5411"
    "\u7ed5\u8fc7\u5168\u5957 shadow \u7684 targeted \u90e8\u7f72\u901a\u9053\uff08\u6b63\u662f SE-0.6 honest "
    "boundary (c) \u9884\u8b66\u7684\u90a3\u6761\uff09\u3002\n",

    "- \u5ba1\u8ba1\u7ed9\u7684\u6700\u4fbf\u5b9c\u89e3\u6cd5\u9010\u5b57\u662f \"the already-mandated next "
    "full-suite shadow (ROADMAP item 3) settles it\" \u2014\u2014 \u5373\u672c\u8282\u7b2c 3 \u6761"
    "\u3002**\u8be5\u5ba1\u8ba1\u4e4b\u540e\u3001\u7528\u4e8e\u5173\u95ed F2 \u7684\u540e\u7ee7 full-suite shadow "
    "\u81f3\u4eca\u6ca1\u6709\u4efb\u4f55\u6267\u884c\u5236\u54c1\u3002** \u4ed3\u5185\u552f\u4e00\u7684 "
    "fusion-dogfood \u5168\u5957 shadow \u662f `evals/runs/fusion-dogfood-v0.1-e1-2ae80d/`\uff0c\u5b83\u4e0d\u662f"
    "\u8be5 mandate \u7684\u5151\u73b0\uff1a\u5176\u66f4\u6b63\u8bb0\u5f55 "
    "`e1-preregistered-result.corrected.json` \u6b63\u662f 2026-07-04 \u5ba1\u8ba1 Part B \u7684\u5ba1\u67e5"
    "\u5bf9\u8c61\uff0c\u6545\u5185\u5bb9\u4e0a\u65e9\u4e8e\u8be5 mandate\uff08\u5176 2026-07-14 \u5165\u4ed3"
    "\u65e5\u671f\u5c5e\u6279\u91cf\u516c\u5f00 commit `3c196d67`\uff0c\u975e\u6267\u884c\u65e5\u671f\uff09\uff1b"
    "\u4e14\u8be5\u5957\u9898\u5171 8 \u4e2a case\u3001\u5168\u4e3a `fusion-*`\uff0c**\u4e0d\u542b "
    "`memory-cross-window-continuation`**\uff0c\u6545\u8be5\u5957\u9898\u7684\u4efb\u4f55\u4e00\u8f6e\u5728"
    "\u7ed3\u6784\u4e0a\u90fd\u65e0\u6cd5\u5173\u95ed F2\u3002\n",

    "- \u5ba1\u8ba1\u53e6\u7ed9\u4e00\u6761\u53ef\u9009\u8def\uff1a\"an optional 2-trial probe of `8e9c7555\u2026` "
    "on memory-cross-window would discriminate targeted-regression vs environment drift sooner\" \u2014\u2014 "
    "**\u672a\u89c1\u8be5 probe \u7684\u540e\u7ee7\u72ec\u7acb\u6267\u884c\u5236\u54c1\u3002** \u5224\u522b\u91cf"
    "\uff08\u9010\u884c\u89e3\u6790\u5168\u90e8 `evals/runs/**/trials.jsonl`\uff0c\u975e raw grep\uff09\uff1a"
    "`artifact_hash=8e9c7555\u2026` \u00d7 `case_id=memory-cross-window-continuation` \u4ec5\u843d\u5728 "
    "`se-0.6-v0.1-successor-v0.9/trials.jsonl` \u4e0e\u5176 candidate-only \u526f\u672c\uff0c\u5404 2 trial\uff1b"
    "`8e9c7555\u2026` \u662f\u8be5 run \u7684 candidate\uff0c\u8be5\u6587\u4ef6\u5165\u4ed3 commit "
    "`8ac98e45`\uff082026-07-02\uff09\uff0c\u65e9\u4e8e 07-04 \u5ba1\u8ba1\uff0c\u5373\u5ba1\u8ba1\u843d\u7b14"
    "\u65f6\u5df2\u5b58\u5728\u7684\u5bf9\u7167\u6570\u636e\uff0c\u975e\u5176\u5efa\u8bae\u7684\u540c\u671f"
    "\u590d\u8dd1\u3002\n",

    "- \u7b2c\u4e8c\u6761\u8def\u5df2\u88ab\u62d2\uff0c\u4e14\u672c\u5c31\u4e0d\u662f\u884c\u4e3a\u590d\u6d4b"
    "\uff1aF2 \u88ab\u4ee3\u8c22\u6210 "
    "`evals/fixtures/fusion-dogfood-v0.2/fusion-targeted-deployment-risk/`\uff0c\u4f46 (i) \u5176\u4efb\u52a1"
    "\u662f\u8bfb 07-04 \u9759\u6001\u6536\u636e\u505a\u98ce\u9669\u5206\u7c7b\u4e0e\u5efa\u8bae\uff0c\u4e0d"
    "\u8fd0\u884c Skill\u3001\u4e0d\u89e6\u53d1 paused-scope \u884c\u4e3a\uff0c\u6545\u6ee1\u5206\u53ea\u8bc1"
    "\u660e\u201c\u4f1a\u6b63\u786e\u8c08\u8bba F2\u201d\uff0c\u4e0d\u8bc1\u660e F2 \u5df2\u5173\u95ed\uff1b"
    "(ii) \u8be5 case \u5728\u6821\u51c6\u4e2d\u5224 `rejected_ceiling_saturation`\uff080.9725 \u5bf9 R2 "
    "\u9608\u503c 0.85\uff0c`proposals/fusion-dogfood-extension-v0.2/CALIBRATION_RESULT.md`\uff09\uff0cv0.2 "
    "\u7684 FREEZE_REQUEST \u4ecd\u662f DRAFT\uff0c`evals/approvals/` \u81f3\u4eca\u53ea\u6709 "
    "`fusion-dogfood-v0.1-approval.json`\u3002\n",

    "- **\u4e8b\u5b9e\u5c42\u7ea7\uff08\u8fb9\u754c\uff0c\u52ff\u8d8a\uff09**\uff1aF2 \u5750\u5b9e\u4e8e "
    "`49e656d2\u2026`\uff082026-07-04 \u5b9e\u6d4b\uff09\uff1b\u5f52\u6863\u6536\u636e `1751ce\u2026` \u8bb0"
    "\u5f55 after=`9872361c\u2026`\uff082026-07-21\uff1b\u8be5\u6536\u636e\u672a\u5165\u4ed3\uff0c\u4e14\u4ed3"
    "\u5185\u65e0\u4efb\u4f55 `9872361c\u2026` \u7684 artifact \u6811\u53ef\u4f9b\u590d\u91cf\uff09\uff1b\u5f53"
    "\u524d live tree \u4e8e 2026-07-31 \u76f4\u63a5\u5185\u5bb9\u5bfb\u5740\u91cf\u5f97 "
    "`ae0537da\u2026b142ad`\uff0849 files\uff09\u3002**F2 \u5bf9\u5f53\u524d live tree \u7684\u9002\u7528"
    "\u6027\u672a\u77e5\u3002** \u90e8\u7f72\u4e0e\u5b57\u8282\u6f02\u79fb\u53ea\u6269\u5927\u672a\u77e5\uff0c"
    "\u4e0d\u4f20\u9012\u7f3a\u9677\u4e8b\u5b9e\u2014\u2014\u672c\u6761**\u4e0d**\u4e3b\u5f20\u201c\u5f53\u524d"
    "\u4ef6\u4ecd\u72af\u201d\uff0c\u4e5f**\u4e0d**\u4e3b\u5f20\u201c\u98ce\u9669\u5df2\u88ab\u4f20\u4e0b"
    "\u6765\u201d\u3002\n",

    "- \u5173\u95ed F2 \u7684\u8bc1\u636e\u53ea\u80fd\u662f\uff1a\u5728**\u5f53\u524d\u90e8\u7f72\u5de5\u4ef6**"
    "\u4e0a\uff0c\u4ee5\u9884\u5148\u9501\u5b9a\u4e14\u53ef\u590d\u73b0\u7684 paused-scope \u573a\u666f\u505a"
    "\u4e0d\u4f4e\u4e8e\u539f F2 \u7684\u7b49\u4ef7\u590d\u6d4b\uff08\u6216\u66f4\u5f3a\u8bc1\u636e\uff09\u3002"
    "**\u672c\u6ce8\u91ca\u4e0d\u6388\u6743\u4efb\u4f55\u6d4b\u8bd5\u3002**\n",
]

C_SUFFIX = (
    " \uff082026-07-04 \u53e3\u5f84\uff1b07-11 \u540e\u4e0d\u518d\u662f\u64cd\u4f5c\u95f8\u3002\u5b83\u540c\u65f6"
    "\u662f F2 \u7684\u6307\u5b9a\u89e3\u6cd5\uff0c\u89c1\u672c\u8282\u62ac\u5934\u3002\uff09"
)

new = list(lines)
# apply bottom-up so earlier indices stay valid
# (C) line 197 -> append inline note
old197 = new[196].decode("utf-8")
assert old197.endswith("\n")
new[196] = (old197[:-1] + C_SUFFIX + "\n").encode("utf-8")
# (B) insert after line 186 (blank under the heading)
b_block = [B1, "\n", B3, "\n"] + BULLETS + ["\n"]
new[186:186] = [s.encode("utf-8") for s in b_block]
# (A) insert after line 140 (blank after the paragraph)
new[140:140] = [A.encode("utf-8"), b"\n"]

final_bytes = b"".join(new)
final_sha = hashlib.sha256(final_bytes).hexdigest()
open(OUT, "wb").write(final_bytes)

# ---- canonical LCS (CONVENTION v0.7 §5.5.b) ----
pre = base_bytes.splitlines(keepends=True)
post = final_bytes.splitlines(keepends=True)
n, m = len(pre), len(post)
dp = [[0] * (m + 1) for _ in range(n + 1)]
for i in range(n - 1, -1, -1):
    row, nxt = dp[i], dp[i + 1]
    pi = pre[i]
    for j in range(m - 1, -1, -1):
        row[j] = nxt[j + 1] + 1 if pi == post[j] else max(nxt[j], row[j + 1])
lcs = dp[0][0]
added = m - lcs
deleted = n - lcs

# ---- section attribution over the union of all minimal alignments (§5.5.f) ----
def prefix_tbl(a, b):
    t = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            t[i][j] = t[i - 1][j - 1] + 1 if a[i - 1] == b[j - 1] else max(t[i - 1][j], t[i][j - 1])
    return t

def suffix_tbl(a, b):
    t = [[0] * (len(b) + 2) for _ in range(len(a) + 2)]
    for i in range(len(a) - 1, -1, -1):
        for j in range(len(b) - 1, -1, -1):
            t[i][j] = t[i + 1][j + 1] + 1 if a[i] == b[j] else max(t[i + 1][j], t[i][j + 1])
    return t

P = prefix_tbl(pre, post)
S = suffix_tbl(pre, post)
added_idx = [j for j in range(m) if max(P[i][j] + S[i][j + 1] for i in range(n + 1)) == lcs]
deleted_idx = [i for i in range(n) if max(P[i][j] + S[i + 1][j] for j in range(m + 1)) == lcs]

ATX = re.compile(rb"^#{1,6} ")

def section_of(seq, idx):
    for k in range(idx, -1, -1):
        if ATX.match(seq[k]):
            return seq[k].decode("utf-8").rstrip("\n")
    return "<\u65e0\u6807\u9898\u524d\u8a00>"

sections = sorted({section_of(post, j) for j in added_idx} | {section_of(pre, i) for i in deleted_idx})

print("base_sha256   =", base_sha, len(base_bytes), "bytes")
print("final_sha256  =", final_sha, len(final_bytes), "bytes")
print("lines pre/post=", n, m, "LCS =", lcs)
print("added_lines   =", added, " (union-min idx count:", len(added_idx), ")")
print("deleted_lines =", deleted, " (union-min idx count:", len(deleted_idx), ")")
print("ambiguous     =", len(added_idx) != added or len(deleted_idx) != deleted)
print("sections_touched =", sections)
print("added post-line numbers (1-idx):", [j + 1 for j in added_idx])
print("deleted pre-line numbers (1-idx):", [i + 1 for i in deleted_idx])
print("out =", OUT)
