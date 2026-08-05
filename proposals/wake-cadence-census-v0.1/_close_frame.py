#!/usr/bin/env python3
"""Persistence audit (round_end) for this frame, then close it. Argv channel only."""
import subprocess
import sys

TRACE = r"C:\Users\zy\.claude\skills\solve-with-weilan\scripts\weilan_trace.py"
FRAME = "wf-20260805-222339-d45330"

REASON = (
    "\u672c\u56de\u5408\u65e0 durable \u7528\u6237\u6307\u4ee4\u53ef\u6301\u4e45\u5316\uff1a"
    "\u9759\u9ed8 tick\uff0c\u56db\u901a\u9053\u5168\u7a7a\uff0c\u65e0\u89c2\u5bdf\u5458\u8bdd\u7b52\u3002"
    "\u6240\u6709\u4ea7\u51fa\u5747\u4e3a\u9879\u76ee\u4e8b\u5b9e\uff08FINDING/\u63a2\u9488/\u8d26\u672c\u6761\u76ee\uff09\uff0c"
    "\u771f\u6e90 = \u4ed3\u5e93\u6587\u4ef6 + \u8d26\u672c\uff0c\u4e0d\u5165 auto-memory\u3002"
    "\u65e0\u53ef\u89e3\u6790\u4f1a\u8bdd\u51fa\u5904\u7684 evidence-capture\uff0c\u6545\u8bda\u5b9e\u8d70 not_persisted\u3002"
)

VERDICT = (
    "\u9759\u9ed8 tick\uff0c\u6ca1\u5f00\u65b0\u6848\u3002\u53ea\u8bfb\u666e\u67e5 3 \u5929\u7a97\u53e3 268 \u5e27\uff1a"
    "152 \u5e27 problem \u9010\u5b57\u7b49\u4e8e wake.py:56 RECEIPT_PROBLEM\uff0c138 \u5e27 verdict \u9010\u5b57\u8282\u76f8\u540c"
    "\uff084b169a2e7f5c\uff09\uff0c\u9759\u9ed8\u5360 59.3%\uff0c\u6700\u957f\u8fde\u7eed\u9759\u9ed8\u4e32 51 \u5e27/9.96h\u3002"
    "\u672c\u56de\u5408 memory-recall \u7684 projection.focus \u9010\u5b57 = RECEIPT_PROBLEM\uff0c"
    "\u5373 focus-reducer-heartbeat-overwrite-v0.1\uff082026-07-18\uff09\u9884\u8a00\u7684\u4f24\u4eca\u65e5\u4ecd\u5e26\u7535"
    "\uff08\u4f46\u65e0\u4e49\u52a1\u4e22\u5931\u8bc1\u636e\uff0c\u4eca\u65e5\u771f\u65e0\u5f85\u529e\uff09\u3002"
    "\u4e24\u4e2a\u81ea\u63d0\u5047\u8bbe\u5f53\u573a\u8bc1\u4f2a\u5e76\u9489\u5165\u6863\uff1a"
    "\uff08\u7532\uff09\u7f50\u5934\u6536\u636e\u2192\u9519\uff0cwake.py:575-577 \u662f\u5185\u5bb9\u786e\u5b9a\u6027\u6458\u8981\uff1b"
    "\uff08\u4e59\uff09\u5fc3\u8df3\u70e7 cursor\u2192\u9519\uff0cwake.py:262-277 commit_cursor=False\u3002"
    "\u53e6\u62a5\u4e00\u5904\u6587\u6863\u6f02\u79fb\uff1a\u5b9e\u67e5 Interval=PT1M/ExecutionTimeLimit=PT1H\uff0c"
    "\u800c IMPL_NOTES.md:82-83 \u4e0e OPERATOR_CARD.md:11-12 \u4ecd\u5199 PT30M/10-min\uff1b"
    "\u672c\u56de\u5408\u5b50\u4ee3\u7406\u5df2\u88ab\u8be5\u9648\u6587\u6863\u8bef\u5bfc\uff08\u5b9e\u8bc1\uff09\u3002"
    "\u672a\u5355\u7b7e\u6539\u6587\u6863\uff1a\u54ea\u4e2a\u503c\u662f\u7b7e\u8fc7\u7684\u672c\u56de\u5408\u672a\u5750\u5b9e\uff0c"
    "\u4e14 OPERATOR_CARD \u662f\u89c2\u5bdf\u5458\u9762\u677f\u3002\u56db\u6761\u5019\u9009\u523b\u610f\u672a\u9009\uff0c\u7559 Codex \u72ec\u7acb\u5224\u3002"
    "\u4ea7\u51fa\uff1aproposals/wake-cadence-census-v0.1/{FINDING.md,\u63a2\u9488,.out.json} + peer-chat 1 \u6761"
    "\uff082026-08-06T07:37:48+09:00\uff09\u3002\u4e0d\u767b\u8bb0\u65b0 goal\uff08\u5df2\u6709 7 \u6761\uff09\uff0c"
    "\u8bf7 goal:wire-parked-findings-r6 \u660e\u65e5\u7eed\u4fdd\u65f6\u6536\u5165\u8986\u76d6\u9762\u3002\u672a\u52a8\u4efb\u4f55\u673a\u5236\u3002"
)


def run(args):
    p = subprocess.run([sys.executable, TRACE] + args, capture_output=True)
    sys.stdout.write("rc=%d\n" % p.returncode)
    sys.stdout.write(p.stdout.decode("utf-8", "replace"))
    sys.stdout.write(p.stderr.decode("utf-8", "replace"))
    return p.returncode


def main() -> int:
    rc = run(["persistence-audit", "--frame-id", FRAME, "--trigger", "round_end",
              "--decision", "not_persisted", "--reason", REASON])
    if rc != 0:
        return rc
    return run(["close", "--frame-id", FRAME, "--outcome", "success", "--verdict", VERDICT])


if __name__ == "__main__":
    raise SystemExit(main())
