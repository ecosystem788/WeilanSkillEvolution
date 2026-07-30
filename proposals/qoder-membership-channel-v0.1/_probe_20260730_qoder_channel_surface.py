"""只读探针：Qoder CN 作为"成员通道"的方向裁决与身份归属面。

口径（全部只读，不启动 GUI、不发网络请求、不写任何 Qoder 侧文件）：
  P1 cli.js 的 chat 子命令面：选项名全集 + 两处 help 版本串的取值表达式
  P2 版本字段：package.json / product.json
  P3 配置面：用户 settings.json 里与模型选择相关的键
  P4 模型目录缓存：state.vscdb（mode=ro&immutable=1）里的 modelConfigs.cache.*
  P5 本地会话制品普查：projects / globalStorage / chat 视图态键
  P6 扩展贡献点：aicoding-agent 的 contributes 与 enabledApiProposals

脱敏：账号态键名里的 UUID 一律替换为 <uuid-redacted>；不读取、不输出任何会话正文。

用法： python _probe_20260730_qoder_channel_surface.py [--json out.json]
"""
import io
import json
import os
import re
import sqlite3
import sys

INSTALL = r"C:\Users\zy\AppData\Local\Programs\QoderCN"
APP = os.path.join(INSTALL, "resources", "app")
ROAMING = r"C:\Users\zy\AppData\Roaming\QoderCN"
DOTDIR = r"C:\Users\zy\.qoder-cn"

UUID_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")


def redact(s):
    return UUID_RE.sub("<uuid-redacted>", s)


def read_text(p):
    with io.open(p, encoding="utf-8", errors="replace") as f:
        return f.read()


def p1_cli_chat_surface():
    p = os.path.join(APP, "out", "cli.js")
    s = read_text(p)
    r = {"path": p, "exists": True, "size": len(s)}
    # chat 子命令的定义块：Zt={chat:{type:"subcommand",...options:{...}}
    m = re.search(r'\{chat:\{type:"subcommand",description:"([^"]*)",options:\{', s)
    r["chat_description"] = m.group(1) if m else None
    if m:
        # 必须切到 chat 的 options 块结束处；不切会漏进下一个子命令(serve-web)的选项
        tail = s[m.end():m.end() + 4000]
        cut = tail.find('},"serve-web":')
        r["chat_options_block_terminated"] = cut != -1
        seg = tail[:cut] if cut != -1 else tail
        # 选项名 = 形如  name:{type:  或  "name":{type:
        names = re.findall(r'(?:"([\w-]+)"|(\w+)):\{type:', seg)
        r["chat_option_names"] = [a or b for (a, b) in names]
    r["chat_has_model_option"] = bool(
        r.get("chat_option_names") and any("model" in o for o in r["chat_option_names"]))
    # chat 定义所在的上游构建路径（证明其来源模块）
    idx = s.find('{chat:{type:"subcommand"')
    r["defining_build_module"] = None
    if idx > 0:
        back = s[max(0, idx - 3000):idx]
        mods = re.findall(r'"(out-build/[^"]+\.js)"', back)
        r["defining_build_module"] = mods[-1] if mods else None
    # 两处 help 的版本串取自不同字段——这解释了两条 --help 印出不同版本号
    mtop = re.search(r'if\(t\.help\)\{(.{0,200})', s, re.S)
    r["top_help_snippet"] = mtop.group(1) if mtop else None
    r["top_help_uses_productVersion"] = bool(
        mtop and "productVersion||" in mtop.group(1))
    mchat = re.search(r'else if\(t\.chat\?\.help\)\{(.{0,200})', s, re.S)
    r["chat_help_snippet"] = mchat.group(1) if mchat else None
    r["chat_help_uses_bare_version"] = bool(
        mchat and re.search(r'console\.log\(\w+\(\w+\.nameLong,\w+,\w+\.version,', mchat.group(1)))
    # 全文里唯一把子进程 stdout 回传到本进程的管道，落在哪个子命令路径上
    sites = []
    for mm in re.finditer(r"\w+\.stdout\.pipe\(process\.stdout\)", s):
        ctx = s[max(0, mm.start() - 1200):mm.start()]
        sites.append({
            "in_tunnel_or_serveweb_path": "tunnelApplicationName" in ctx,
            "mentions_chat": "chat" in ctx,
        })
    r["stdout_pipe_sites"] = sites
    r["stdout_pipe_count"] = len(sites)
    r["stdin_dash_becomes_add_file"] = bool(
        re.search(r't\.chat\?pe\(\w+,"--add-file",\w+\)', s))
    return r


def p2_versions():
    pkg = json.loads(read_text(os.path.join(APP, "package.json")))
    prod = json.loads(read_text(os.path.join(APP, "product.json")))
    return {
        "package.json:version": pkg.get("version"),
        "product.json:productVersion": prod.get("productVersion"),
        "product.json:version": prod.get("version"),
        "product.json:nameLong": prod.get("nameLong"),
    }


def p3_config_surface():
    out = {}
    for label, p in (("user_settings", os.path.join(ROAMING, "User", "settings.json")),
                     ("dotdir_settings", os.path.join(DOTDIR, "settings.json"))):
        if not os.path.exists(p):
            out[label] = {"exists": False}
            continue
        d = json.loads(read_text(p))

        def flat(o, pre=""):
            ks = []
            for k, v in o.items():
                kk = pre + k
                if isinstance(v, dict):
                    ks += flat(v, kk + ".")
                else:
                    ks.append(kk)
            return ks
        keys = flat(d)
        out[label] = {
            "exists": True,
            "key_count": len(keys),
            "keys_matching_model": [k for k in keys if "model" in k.lower()],
        }
    return out


def _db():
    p = os.path.join(ROAMING, "User", "globalStorage", "state.vscdb")
    uri = "file:" + p.replace("\\", "/") + "?mode=ro&immutable=1"
    return sqlite3.connect(uri, uri=True)


def p4_model_catalog():
    out = {}
    con = _db()
    cur = con.cursor()
    cur.execute("select key from ItemTable where key like '%model%'")
    out["model_keys"] = sorted(redact(r[0]) for r in cur.fetchall())
    for surface in ("assistant", "quest", "experts"):
        key = "aicoding.modelConfigs.cache." + surface
        cur.execute("select value from ItemTable where key=?", (key,))
        row = cur.fetchone()
        if not row:
            out[surface] = None
            continue
        v = row[0]
        if isinstance(v, bytes):
            v = v.decode("utf-8", "replace")
        out[surface] = [
            {"name": m.get("name"), "displayName": m.get("displayName"),
             "isDefault": m.get("isDefault"), "enabled": m.get("enabled"),
             "priceFactor": m.get("priceFactor"), "format": m.get("format"),
             "source": m.get("source")}
            for m in json.loads(v)
        ]
    con.close()
    return out


def p5_local_artifacts():
    out = {}
    proj = os.path.join(DOTDIR, "projects")
    n = 0
    for _root, _d, files in os.walk(proj):
        n += len(files)
    out["dotdir_projects_file_count"] = n
    gs = os.path.join(ROAMING, "User", "globalStorage", "aicoding.aicoding-agent")
    n = 0
    for _root, _d, files in os.walk(gs):
        n += len(files)
    out["globalStorage_agent_file_count"] = n
    con = _db()
    cur = con.cursor()
    cur.execute("select key, length(value) from ItemTable where key like 'aicoding-chat-%'")
    rows = cur.fetchall()
    out["chat_session_keys"] = len(rows)
    out["chat_session_value_lengths_distinct"] = sorted({r[1] for r in rows})
    out["chat_session_key_suffixes_distinct"] = sorted(
        {redact(r[0]).split("<uuid-redacted>")[-1] for r in rows})
    con.close()
    return out


def p6_extension_contributions():
    p = os.path.join(APP, "extensions", "aicoding-agent", "package.json")
    d = json.loads(read_text(p))
    c = d.get("contributes", {})
    return {
        "contributes_keys": sorted(c.keys()),
        "languageModelChatProviders": c.get("languageModelChatProviders"),
        "chatParticipant_ids": [x.get("id") for x in c.get("chatParticipants", [])],
        "enabledApiProposals": d.get("enabledApiProposals"),
    }


def main():
    res = {
        "probe": "qoder-channel-surface",
        "read_only": True,
        "P1_cli_chat_surface": p1_cli_chat_surface(),
        "P2_versions": p2_versions(),
        "P3_config_surface": p3_config_surface(),
        "P4_model_catalog": p4_model_catalog(),
        "P5_local_artifacts": p5_local_artifacts(),
        "P6_extension_contributions": p6_extension_contributions(),
    }
    txt = json.dumps(res, ensure_ascii=False, indent=2)
    if "--json" in sys.argv:
        dest = sys.argv[sys.argv.index("--json") + 1]
        with io.open(dest, "w", encoding="utf-8", newline="\n") as f:
            f.write(txt + "\n")
    sys.stdout.buffer.write((txt + "\n").encode("utf-8"))


if __name__ == "__main__":
    main()
