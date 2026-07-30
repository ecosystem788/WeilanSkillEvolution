"""只读探针：Qoder CN 的 proposed-API 闸门到底是不是通开的。

背景：product.json 的 extensionEnabledApiProposals == {"*": ["*"]}。上游 VS Code 里这张表
按 extension id（小写）查，用来把 proposed API 预批给指定扩展。若消费侧真是按 id 查，
那 "*" 这个键永远查不中，等于**空表**（没有任何扩展被预批）；若消费侧认 "*" 通配，
那等于**全通**（任何本地扩展都能用 chatProvider / languageModelSystem 等 proposal）。
两个读法的结论完全相反，所以必须去看消费它的代码，而不是看这个键。

口径：全部只读。不启动 Qoder、不发网络、不写任何 Qoder 侧文件。只读 product.json 与
out/ 下已打包的 JS 文本，按字节切片打印上下文，判断留给读者。

用法： python _probe_20260730_proposed_api_gate.py [--json out.json]
"""
import io
import json
import os
import re
import sys

INSTALL = r"C:\Users\zy\AppData\Local\Programs\QoderCN"
APP = os.path.join(INSTALL, "resources", "app")
PRODUCT = os.path.join(APP, "product.json")
TARGETS = [
    os.path.join(APP, "out", "vs", "workbench", "workbench.desktop.main.js"),
    os.path.join(APP, "out", "vs", "workbench", "api", "node", "extensionHostProcess.js"),
]
NEEDLE = "extensionEnabledApiProposals"
WINDOW = 900


def slices(path, needle, window):
    out = []
    if not os.path.isfile(path):
        return out
    text = io.open(path, encoding="utf-8", errors="replace").read()
    for m in re.finditer(re.escape(needle), text):
        a = max(0, m.start() - window)
        b = min(len(text), m.end() + window)
        out.append({"offset": m.start(), "context": text[a:b]})
    return out


def main():
    result = {
        "probe": "qoder-proposed-api-gate",
        "read_only": True,
        "product_json": PRODUCT,
    }

    prod = json.load(io.open(PRODUCT, encoding="utf-8"))
    ea = prod.get("extensionEnabledApiProposals")
    result["extensionEnabledApiProposals"] = ea
    result["extensionAllowedProposedApi"] = prod.get("extensionAllowedProposedApi")
    result["quality"] = prod.get("quality")
    result["nameShort"] = prod.get("nameShort")
    result["version"] = prod.get("version")
    result["productVersion"] = prod.get("productVersion")

    result["consumers"] = []
    for t in TARGETS:
        hits = slices(t, NEEDLE, WINDOW)
        result["consumers"].append(
            {"file": t, "exists": os.path.isfile(t), "hits": len(hits), "slices": hits}
        )

    if "--json" in sys.argv:
        out = sys.argv[sys.argv.index("--json") + 1]
        io.open(out, "w", encoding="utf-8").write(
            json.dumps(result, ensure_ascii=False, indent=2)
        )
        print("wrote " + out)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
