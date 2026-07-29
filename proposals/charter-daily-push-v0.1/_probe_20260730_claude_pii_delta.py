"""Is the observer-privacy content in this push NEW to the public tree, or was
it already published before base?

Method: compare the base commit's version of each hit-carrying path against the
HEAD version, on JSON-decoded text (the ledger stores backslashes escaped, so a
raw-byte search for a Windows path under-reports). Read-only.
"""
import json
import subprocess

REPO = "D:/WeilanSkillEvolution"
BASE = "0c3d9b25ddb86010837a0930c40accad3c78189a"
HEAD = "310e57546dd51742fc8f38c403c3df3fcdeb375f"
PATH = "proposals/bounded-scheduler-v0.1/impl/peer-chat.jsonl"

NEEDLES = {
    "id_photo_word": "\u767b\u8bb0\u7167",
    "photo_dir": "\u4e2d\u56fd\u519c\u5927",
    "chorus": "\u7267\u6b4c\u5408\u5531\u56e2",
    "photo_path_decoded": "D:\\\u8f6c\u79fb",
    "photo_filename": "\u767b\u8bb0\u7167.jpg",
}


def show(rev, path):
    return subprocess.run(["git", "-C", REPO, "show", f"{rev}:{path}"],
                          capture_output=True).stdout.decode("utf-8", "replace")


def scan(text, label):
    out = {}
    lines = text.splitlines()
    for name, needle in NEEDLES.items():
        found = []
        for i, line in enumerate(lines, 1):
            # search both the raw line and, when parseable, its decoded text
            hay = line
            try:
                obj = json.loads(line)
                hay = line + "\n" + json.dumps(obj, ensure_ascii=False)
                if isinstance(obj, dict):
                    hay += "\n" + str(obj.get("text", ""))
            except Exception:
                pass
            if needle in hay:
                found.append(i)
        out[name] = found
    out["line_count"] = len(lines)
    out["label"] = label
    return out


def main():
    base_text = show(BASE, PATH)
    head_text = show(HEAD, PATH)
    b = scan(base_text, "base")
    h = scan(HEAD and head_text, "head")
    delta = {}
    for name in NEEDLES:
        already = set(b[name])
        now = set(h[name])
        delta[name] = {
            "base_lines": sorted(already),
            "head_lines": sorted(now),
            "new_lines_not_in_base": sorted(now - already),
        }
    print(json.dumps({
        "path": PATH,
        "base_line_count": b["line_count"],
        "head_line_count": h["line_count"],
        "delta": delta,
    }, ensure_ascii=False, indent=2))

    # print the offending head lines' text so a human can judge, truncated
    lines = head_text.splitlines()
    seen = set()
    for name in NEEDLES:
        for ln in delta[name]["head_lines"]:
            if ln in seen:
                continue
            seen.add(ln)
            try:
                obj = json.loads(lines[ln - 1])
                txt = obj.get("text", "")
            except Exception:
                txt = lines[ln - 1]
            print(f"\n--- head line {ln} ---")
            print(txt[:600])


if __name__ == "__main__":
    main()
