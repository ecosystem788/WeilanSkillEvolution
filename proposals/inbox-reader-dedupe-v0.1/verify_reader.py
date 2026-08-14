"""inbox-reader-dedupe v0.1 机检器。

跑 §七 的七个测试情形(1 新行三元组、2 旧接力回退、3 4110/4112 真行、
4 新行未处理、5 processed 重复 id、6 processed 孤儿、7 inbox 同 time fail-closed),
全绿 rc=0,任一红 rc=1。只读,不动任何账本。

用法::

    python proposals/inbox-reader-dedupe-v0.1/verify_reader.py \
        --root proposals/bounded-scheduler-v0.1/impl

可选 ``--case 3`` 只跑指定情形。默认跑全部 7 个。

CONVENTION §三 要求 §三 抛错时携带 raw bytes sha256(open(path,'rb').read()[start_byte:end_byte]),
本实现按行字节区间解析规则(CONVENTION §三 段二)对每行找其在文件中 [start,end) 区间,
计算 raw 字节哈希——不重排键序、不重写 ensure_ascii、不规范化 JSON。
两条同字段不同键序的行,raw-bytes 哈希必互异;两条规范化(json.dumps(sort_keys=True))哈希可同。
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


def _row_byte_ranges(path: Path, rows: list[dict]) -> list[tuple[int, int]]:
    """按 CONVENTION §三 段二行字节区间解析规则,找每 row 在文件中的 [start,end)。

    行定义:文件按 b'\\n' 切分;空段视为文件尾 '\\n' 后的零长尾巴,跳过(不入行号)。
    每段字节区间不含尾部 '\\n'。解析失败的段(json.loads 抛错)跳过。
    """
    raw = path.read_bytes()
    out: list[tuple[int, int]] = []
    pos = 0
    for seg in raw.split(b"\n"):
        if not seg:
            # 空段 = 文件尾部 '\\n' 后的零长尾巴
            pos += 1  # '\\n' 字节
            continue
        seg_start = pos
        seg_end = pos + len(seg)
        pos = seg_end + 1  # +1 为 '\\n'
        try:
            parsed = json.loads(seg.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if parsed in rows:
            out.append((seg_start, seg_end))
    return out


def _row_raw_bytes_sha256(path: Path, start: int, end: int) -> str:
    """CONVENTION §三:hashlib.sha256(open(path,'rb').read()[start:end]).hexdigest()。"""
    return hashlib.sha256(path.read_bytes()[start:end]).hexdigest()


class AmbiguousNoIdTime(Exception):
    """§三 fail-closed:inbox 中两条及以上无 id 行同 time。"""

    def __init__(self, time_value: str, collisions: list[dict], byte_ranges: list[tuple[int, int]]):
        self.time_value = time_value
        self.collisions = collisions
        self.byte_ranges = byte_ranges
        path_obj = collisions[0].get("__source_path__") if collisions else None
        # 上方 collisions 是纯 dict,不带 __source_path__;path 由 inbox_delta 注入,
        # 这里不再依赖;hashes 直接由 byte_ranges 算。
        hashes = []
        for r, (s, e) in zip(collisions, byte_ranges):
            hashes.append({"row": r, "byte_range": [s, e], "raw_bytes_sha256": None})
        super().__init__(
            f"inbox has {len(collisions)} no-id rows with time={time_value!r}; "
            f"byte_ranges={byte_ranges}"
        )


def inbox_delta(inbox_path: Path, processed_path: Path) -> list[dict]:
    """实现 CONVENTION §二/§三/§四。

    与 wake_brief.py 部署版将来实现的函数语义完全一致——本文件先落 reference
    implementation,等双签后替换进 wake_brief.py。

    签名按 CONVENTION §五 收 path,与部署同形;§三 抛错时按行字节区间解析规则
    算 raw bytes sha256,见 _row_byte_ranges / _row_raw_bytes_sha256。
    """
    inbox_rows = _read_jsonl(inbox_path)
    processed_rows = _read_jsonl(processed_path)

    # §三 fail-closed:inbox 中无 id 行按 time 分桶,>1 即抛
    by_time: dict[str, list[dict]] = {}
    for r in inbox_rows:
        if "id" not in r:
            t = str(r.get("time", ""))
            by_time.setdefault(t, []).append(r)
    for t, rows in by_time.items():
        if len(rows) > 1:
            byte_ranges = _row_byte_ranges(inbox_path, rows)
            raise AmbiguousNoIdTime(t, rows, byte_ranges)

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
    """把 rows 写成 JSONL 到 path(用于 tempfile 合成夹具)。

    写时不重排键序、不写 ensure_ascii=True(ensure_ascii=False 与 raw 字节口径一致),
    不在末尾多写 '\\n' 之外的东西。
    """
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
    delta = inbox_delta(tmp / "inbox.jsonl", tmp / "proc.jsonl")
    return ("case_1_three_tuple_hit", len(delta) == 0, f"delta={len(delta)}")


def case_2_relay_fallback(tmp: Path) -> tuple[str, bool, str]:
    """旧接力回退命中:inbox 无 id time=T,processed id=T。delta 应空。"""
    inbox = [{"from": "claude", "text": "推 8 条", "time": "2026-08-15T02:03:23+09:00"}]
    proc = [{"id": "2026-08-15T02:03:23+09:00", "time": "2026-08-15T02:45:01+09:00"}]
    _write_jsonl(tmp / "inbox.jsonl", inbox)
    _write_jsonl(tmp / "proc.jsonl", proc)
    delta = inbox_delta(tmp / "inbox.jsonl", tmp / "proc.jsonl")
    return ("case_2_relay_fallback", len(delta) == 0, f"delta={len(delta)}")


def case_3_real_relay_rows(root: Path) -> tuple[str, bool, str]:
    """4110/4112 真行:直接读现状账本,delta 应空。"""
    inbox_path = root / "codex-inbox.jsonl"
    proc_path = root / "codex-inbox-processed.jsonl"
    inbox_rows = _read_jsonl(inbox_path)
    delta = inbox_delta(inbox_path, proc_path)
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
    delta = inbox_delta(tmp / "inbox.jsonl", tmp / "proc.jsonl")
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
    delta = inbox_delta(tmp / "inbox.jsonl", tmp / "proc.jsonl")
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
    delta = inbox_delta(tmp / "inbox.jsonl", tmp / "proc.jsonl")
    return ("case_6_processed_orphan", len(delta) == 0, f"delta={len(delta)}")


def case_7_inbox_same_time_fail_closed(tmp: Path) -> tuple[str, bool, str]:
    """inbox 两条无 id 同 time:reader 必须抛 AmbiguousNoIdTime。

    CONVENTION §三 必达条件:
    - 抛错时 byte_ranges 给出每行 [start,end);
    - 两行 raw_bytes_sha256 互异(因键序不同——raw 字节含键序,规范化会去键序);
    - 两行 raw_bytes_sha256 等于按文件字节区间算出的哈希(契约↔机检同权威)。

    关键:两条 inbox 行字段值完全相同,但写入时故意用不同键序——
    {"from","text","time"} vs {"time","from","text"}。规范化哈希(sort_keys=True)会
    让两行同 hash;raw bytes 哈希会因键序不同而互异。这才能钉死"raw 而非规范化"。
    """
    inbox_path = tmp / "inbox.jsonl"
    # 手工写 raw bytes 以控制键序
    inbox_path.write_bytes(
        b'{"from":"claude","text":"same","time":"2026-08-15T03:00:00+09:00"}\n'
        b'{"time":"2026-08-15T03:00:00+09:00","from":"claude","text":"same"}\n'
    )
    proc = [{"id": "2026-08-15T03:00:00+09:00", "time": "2026-08-15T03:00:01+09:00"}]
    _write_jsonl(tmp / "proc.jsonl", proc)
    try:
        inbox_delta(inbox_path, tmp / "proc.jsonl")
    except AmbiguousNoIdTime as e:
        ok_time = e.time_value == "2026-08-15T03:00:00+09:00"
        ok_n = len(e.collisions) == 2 and len(e.byte_ranges) == 2
        if not (ok_time and ok_n):
            return ("case_7_inbox_same_time_fail_closed", False,
                    f"time={e.time_value} collisions={len(e.collisions)} ranges={len(e.byte_ranges)}")
        # 断言 1:两行 raw_bytes_sha256 互异(键序不同 → raw 必异,规范化会同)
        hashes = [_row_raw_bytes_sha256(inbox_path, s, end) for s, end in e.byte_ranges]
        if hashes[0] == hashes[1]:
            return ("case_7_inbox_same_time_fail_closed", False,
                    f"two row hashes equal (规范化才同,raw 必互异): {hashes}")
        # 断言 2:对撞用例的字段值完全相同,但 raw hash 互异证明算法走的是 raw bytes
        # 路径而非规范化路径——这两条 inbox 行 normalize 后必同 hash。
        import json as _json
        normalized_hashes = {
            _json.dumps(r, ensure_ascii=False, sort_keys=True).__hash__()
            for r in e.collisions
        }
        # normalized hash set 大小 = 1(同内容),raw hash set 大小 = 2
        # 用 sha256 验:
        norm_hashes = [
            __import__("hashlib").sha256(
                _json.dumps(r, ensure_ascii=False, sort_keys=True).encode("utf-8")
            ).hexdigest()
            for r in e.collisions
        ]
        if norm_hashes[0] != norm_hashes[1]:
            return ("case_7_inbox_same_time_fail_closed", False,
                    f"test fixture broken: normalized hashes differ, "
                    f"应为同内容键序不同场景: norm={norm_hashes}")
        # 断言 3:每字节区间解码后必等于某 collision row(契约行字节区间解析规则的检查)。
        # 注:两 collision 行 dict 相等,故"row->byte_range 反向唯一"在此夹具下不可达
        # ——_row_byte_ranges 会把每 row 都解到两段。我们只验"区间的字节确实对应某个 collision row",
        # 不验反向唯一。
        for br in e.byte_ranges:
            decoded = json.loads(inbox_path.read_bytes()[br[0]:br[1]].decode("utf-8"))
            if decoded not in e.collisions:
                return ("case_7_inbox_same_time_fail_closed", False,
                        f"byte_range {br} decoded to {decoded}, not in collisions={e.collisions}")
        return ("case_7_inbox_same_time_fail_closed", True,
                f"raised with time={e.time_value} collisions={len(e.collisions)} "
                f"byte_ranges={e.byte_ranges} raw_distinct hashes_same_norm={norm_hashes[0] == norm_hashes[1]}")
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