"""只读探针：用被钉为不变量的机检器自己的 line_delta，算 V3 目标对象的第五件（行级形状）。

不猜、不手数：直接 import proposals/cosign-bytewise-binding-v0.1/verify_binding.py 的 line_delta，
base=ABSENT（target 当前不存在）、final=拟议后像原始字节，取它给出的 added/deleted 两数。
同时复算 final 的 sha256 与字节长度，以及 target 当前是否真的不存在。
对本仓、两安装点、一切账本全只读；不写除同名 .out.json 之外的任何文件。
"""
import hashlib
import importlib.util
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(REPO)  # proposals/<pkg>/ -> repo root
CHECKER = os.path.join(REPO, "proposals", "cosign-bytewise-binding-v0.1", "verify_binding.py")
TARGET = os.path.join(REPO, "proposals", "canonical-workspace-cache-v0.1", ".gitattributes")

FINAL_BYTES = b"*.bak -text\n"


def load_checker(path):
    spec = importlib.util.spec_from_file_location("verify_binding_probe", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    mod = load_checker(CHECKER)
    target_exists = os.path.exists(TARGET)
    base_raw = None if not target_exists else open(TARGET, "rb").read()

    shape = mod.line_delta(base_raw, FINAL_BYTES)

    out = {
        "probe": "line_shape_of_v3",
        "read_only": True,
        "checker_path": os.path.relpath(CHECKER, REPO).replace("\\", "/"),
        "checker_sha256": hashlib.sha256(open(CHECKER, "rb").read()).hexdigest(),
        "target_path": os.path.relpath(TARGET, REPO).replace("\\", "/"),
        "target_exists": target_exists,
        "base": "ABSENT" if base_raw is None else hashlib.sha256(base_raw).hexdigest(),
        "final_bytes_len": len(FINAL_BYTES),
        "final_sha256": hashlib.sha256(FINAL_BYTES).hexdigest(),
        "final_repr": repr(FINAL_BYTES.decode("utf-8")),
        "final_has_bom": FINAL_BYTES.startswith(b"\xef\xbb\xbf"),
        "final_has_cr": b"\r" in FINAL_BYTES,
        "line_delta": {k: v for k, v in shape.items()},
        "python": sys.version.split()[0],
    }
    # 承重两数单列，免得读者从嵌套里挑错字段
    out["expected_added"] = shape["added_lines"]
    out["expected_deleted"] = shape["deleted_lines"]
    # 归属歧义与保守超集：若 possibly_* 大于两数，说明最小对齐不唯一，须如实标出
    out["attribution_ambiguous"] = shape["attribution_ambiguous"]
    out["possibly_added_lines"] = shape["possibly_added_lines"]
    out["possibly_deleted_lines"] = shape["possibly_deleted_lines"]

    dest = os.path.splitext(os.path.abspath(__file__))[0] + ".out.json"
    with open(dest, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
