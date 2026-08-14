"""inbox-reader-dedupe v0.1 机检器。

跑 §七 的七个测试情形(1 新行三元组、2 旧接力回退、3 4110/4112 真行、
4 新行未处理、5 processed 重复 id、6 processed 孤儿、7 inbox 同 time fail-closed),
全绿 rc=0,任一红 rc=1。只读,不动任何账本。

用法::

    python proposals/inbox-reader-dedupe-v0.1/verify_reader.py \
        --root proposals/bounded-scheduler-v0.1/impl

可选 ``--case 3`` 只跑指定情形。默认跑全部 7 个。
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import tempfile
from pathlib import Path


def _read_jsonl(path: Path) -> list[dict]:
    """只读解析。空文件返回 []。坏 JSON 让 json.JSONDecodeError 自然抛出。"""
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(ln) for ln in f if ln.strip()]


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _row_raw_sha256(row: dict) -> str:
    """对 row 序列化后的 bytes 算 sha256(用于 §三 fail-closed 报错)。"""
    return _sha256_bytes(json.dumps(row, ensure_ascii=False, sort_keys=True).encode("utf-8"))


class AmbiguousNoIdTime(Exception):
    """§三 fail-closed:inbox 中两条及以上无 id 行同 time。"""

    def __init__(self, time_value: str, collisions: list[dict]):
        self.time_value = time_value
        self.collisions = collisions
        hashes = [_row_raw_sha256(r) for r in collisions]
        super().__init__(
            f"inbox has {len(collisions)} no-id rows with time={time_value!r}; "
            f"row sha256s={hashes}"
        )


def inbox_delta(inbox_rows: list[dict], processed_rows: list[dict]) -> list[dict]:
    """实现 CONVENTION §二/§三/§四。

    与 wake_brief.py 部署版将来实现的函数语义完全一致——本文件先落 reference
    implementation,等双签后替换进 wake_brief.py。
    """
    # §三 fail-closed:inbox 中无 id 行按 time 分桶,>1 即抛
    by_time: dict[str, list[dict]] = {}
    for r in inbox_rows:
        if "id" not in r:
            t = str(r.get("time", ""))
            by_time.setdefault(t, []).append(r)
    for t, rows in by_time.items():
        if len(rows) > 1:
            raise AmbiguousNoIdTime(t, rows)

    # §四 processed 幂等:同 id 多行视为一条(集合)
    processed_ids: set[str] = {str(r["id"]) for r in processed_rows if "id" in r}

    # §二 双键命中
    out: list[dict] = []
    for r in inbox_rows:
        if "id" in r:
            key = str(r["id"])
        else:
            # §二条件 2:无 id 行必有 time,空 time 让 key="" 不命中(防御)
            key = str(r.get("time", ""))
        if key in processed_ids:
            continue
        out.append(r)
    return out


# ---------------- §七 七个测试情形 ----------------

def _write_jsonl(path: Path, rows: list[dict]) -> None:
    """把 rows 写成 JSONL 到 path(用于 tempfile 合成夹具)。"""
    buf = io.StringIO()
    for r in rows:
        buf.write(json.dumps(r, ensure_ascii=False) + "\n")
    path.write_text(buf.getvalue(), encoding="utf-8")


def case_1_three_tuple_hit(tmp: Path) -> tuple[str, bool, str]:
    """新行三元组命中:inbox 带 id=X,processed 也带 id=X。delta 应空。"""
    inbox = [{"id": "X", "from": "claude", "text": "hi", "time": "2026-08-15T00:00:00+09:00"}]
    proc = [{"id": "X", "time": "2026-08-15T00:00:01+09:00"}]
    _write_jsonl(tmp / "inbox.jsonl", inbox)
    _write_jsonl(tmp / "proc.jsonl", proc)
    delta = inbox_delta(_read_jsonl(tmp / "inbox.jsonl"), _read_jsonl(tmp / "proc.jsonl"))
    return ("case_1_three_tuple_hit", len(delta) == 0, f"delta={len(delta)}")


def case_2_relay_fallback(tmp: Path) -> tuple[str, bool, str]:
    """旧接力回退命中:inbox 无 id time=T,processed id=T。delta 应空。"""
    inbox = [{"from": "claude", "text": "推 8 条", "time": "2026-08-15T02:03:23+09:00"}]
    proc = [{"id": "2026-08-15T02:03:23+09:00", "time": "2026-08-15T02:45:01+09:00"}]
    _write_jsonl(tmp / "inbox.jsonl", inbox)
    _write_jsonl(tmp / "proc.jsonl", proc)
    delta = inbox_delta(_read_jsonl(tmp / "inbox.jsonl"), _read_jsonl(tmp / "proc.jsonl"))
    return ("case_2_relay_fallback", len(delta) == 0, f"delta={len(delta)}")


def case_3_real_relay_rows(root: Path) -> tuple[str, bool, str]:
    """4110/4112 真行:直接读现状账本,delta 应空。"""
    inbox_rows = _read_jsonl(root / "codex-inbox.jsonl")
    proc_rows = _read_jsonl(root / "codex-inbox-processed.jsonl")
    delta = inbox_delta(inbox_rows, proc_rows)
    no_id_in_delta = [r for r in delta if "id" not in r]
    return (
        "case_3_real_relay_rows",
        len(no_id_in_delta) == 0,
        f"delta_total={len(delta)} no_id_in_delta={len(no_id_in_delta)} "
        f"inbox_no_id_total={sum(1 for r in inbox_rows if 'id' not in r)}",
    )


def case_4_new_row_pending(tmp: Path) -> tuple[str, bool, str]:
    """新行未处理:inbox id=Y(Y 不在 processed),delta 应含该行。"""
    inbox = [{"id": "Y", "from": "claude", "text": "新", "time": "2026-08-15T00:00:00+09:00"}]
    proc = [{"id": "X", "time": "2026-08-15T00:00:01+09:00"}]
    _write_jsonl(tmp / "inbox.jsonl", inbox)
    _write_jsonl(tmp / "proc.jsonl", proc)
    delta = inbox_delta(_read_jsonl(tmp / "inbox.jsonl"), _read_jsonl(tmp / "proc.jsonl"))
    ok = len(delta) == 1 and str(delta[0].get("id")) == "Y"
    return ("case_4_new_row_pending", ok, f"delta={delta}")


def case_5_processed_dup_id(tmp: Path) -> tuple[str, bool, str]:
    """processed 重复 id:inbox id=X,processed id=X × 2(去重视为同一条),delta 应空。"""
    inbox = [{"id": "X", "from": "claude", "text": "hi", "time": "2026-08-15T00:00:00+09:00"}]
    proc = [
        {"id": "X", "time": "2026-08-15T00:00:01+09:00"},
        {"id": "X", "time": "2026-08-15T00:00:02+09:00"},  # helper 重跑产物
    ]
    _write_jsonl(tmp / "inbox.jsonl", inbox)
    _write_jsonl(tmp / "proc.jsonl", proc)
    delta = inbox_delta(_read_jsonl(tmp / "inbox.jsonl"), _read_jsonl(tmp / "proc.jsonl"))
    return ("case_5_processed_dup_id", len(delta) == 0, f"delta={len(delta)}")


def case_6_processed_orphan(tmp: Path) -> tuple[str, bool, str]:
    """processed 孤儿行:inbox id=X,processed id=X + id=Z(Z 在 inbox 不存在),delta 应空。"""
    inbox = [{"id": "X", "from": "claude", "text": "hi", "time": "2026-08-15T00:00:00+09:00"}]
    proc = [
        {"id": "X", "time": "2026-08-15T00:00:01+09:00"},
        {"id": "Z", "time": "2026-07-01T00:00:00+09:00"},  # 早期手工 processed,对应 inbox 已不存在
    ]
    _write_jsonl(tmp / "inbox.jsonl", inbox)
    _write_jsonl(tmp / "proc.jsonl", proc)
    delta = inbox_delta(_read_jsonl(tmp / "inbox.jsonl"), _read_jsonl(tmp / "proc.jsonl"))
    return ("case_6_processed_orphan", len(delta) == 0, f"delta={len(delta)}")


def case_7_inbox_same_time_fail_closed(tmp: Path) -> tuple[str, bool, str]:
    """inbox 两条无 id 同 time:reader 必须抛 AmbiguousNoIdTime,delta 不应被静默返回。"""
    inbox = [
        {"from": "claude", "text": "第一条", "time": "2026-08-15T03:00:00+09:00"},
        {"from": "claude", "text": "第二条", "time": "2026-08-15T03:00:00+09:00"},
    ]
    proc = [{"id": "2026-08-15T03:00:00+09:00", "time": "2026-08-15T03:00:01+09:00"}]
    _write_jsonl(tmp / "inbox.jsonl", inbox)
    _write_jsonl(tmp / "proc.jsonl", proc)
    try:
        inbox_delta(_read_jsonl(tmp / "inbox.jsonl"), _read_jsonl(tmp / "proc.jsonl"))
    except AmbiguousNoIdTime as e:
        ok = e.time_value == "2026-08-15T03:00:00+09:00" and len(e.collisions) == 2
        return ("case_7_inbox_same_time_fail_closed", ok, f"raised with time={e.time_value} collisions={len(e.collisions)}")
    return ("case_7_inbox_same_time_fail_closed", False, "reader did NOT raise")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", required=True, help="impl 目录(账本所在家)")
    ap.add_argument("--case", default="all", help="指定 case 名(all/case_N_*)")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not (root / "codex-inbox.jsonl").exists():
        print(f"error: {root}/codex-inbox.jsonl 不存在", file=sys.stderr)
        return 2

    cases = [
        ("case_1_three_tuple_hit", lambda tmp: case_1_three_tuple_hit(tmp)),
        ("case_2_relay_fallback", lambda tmp: case_2_relay_fallback(tmp)),
        ("case_3_real_relay_rows", lambda tmp: case_3_real_relay_rows(root)),
        ("case_4_new_row_pending", lambda tmp: case_4_new_row_pending(tmp)),
        ("case_5_processed_dup_id", lambda tmp: case_5_processed_dup_id(tmp)),
        ("case_6_processed_orphan", lambda tmp: case_6_processed_orphan(tmp)),
        ("case_7_inbox_same_time_fail_closed", lambda tmp: case_7_inbox_same_time_fail_closed(tmp)),
    ]

    selected = [c for c in cases if args.case == "all" or c[0] == args.case]
    if not selected:
        print(f"error: unknown case {args.case!r}", file=sys.stderr)
        return 2

    results: list[tuple[str, bool, str]] = []
    with tempfile.TemporaryDirectory(prefix="inbox_reader_v01_") as td:
        tmp = Path(td)
        for name, fn in selected:
            try:
                r = fn(tmp)
            except Exception as e:  # noqa: BLE001
                r = (name, False, f"case raised: {type(e).__name__}: {e}")
            results.append(r)

    n_pass = sum(1 for _, ok, _ in results if ok)
    n_total = len(results)
    for name, ok, detail in results:
        marker = "PASS" if ok else "FAIL"
        print(f"[{marker}] {name}: {detail}")
    print(f"\n{n_pass}/{n_total} cases passed")
    return 0 if n_pass == n_total else 1


if __name__ == "__main__":
    sys.exit(main())
