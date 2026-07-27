# -*- coding: utf-8 -*-
"""canonical() 的已知答案(known-answer)契约测试。

**为什么单独有这个文件。**
`lineage-log-append-only-correction-v0.1/test_compile_view.py:23` 造夹具时写的是
`after_hash = sha256_hex(canonical(corrected))` —— 期望值由被测函数自己算出来。
于是「写方口径 ≠ 读方口径」这一整类失效在结构上不可能被它报红:
2026-07-15 起该套件 5/5 全绿,而同一时刻真账本 11 条更正 0 条可应用(applied=0/rejected=11),
两件事同时为真、互不干涉。

本文件的全部期望值都是**手写字面量**:下面的 SPEC_CANONICAL_TEXT / LEGACY_TEXT 是我一个字符
一个字符敲进来的 JSON 文本,不是任何 `json.dumps` 调用的产物;哈希是对这些手写字节取的 sha256。
因此被测函数改了口径,这里必然转红——这正是同义反复测试做不到的那一格。

**它不预判 甲/乙/丙/丁 任何一条补救路线。** 它钉的是「§3 此刻规定的 canonical 是哪一个函数」。
若社区将来采纳甲(把 §3 改成现实中在用的那个函数),本文件**应当先转红**、再被有意识地改掉——
让契约的变更显形,而不是无声漂移。红本身就是它在工作。

来源:同目录 DELEGATION.md §3/§4;
证据与 11 条拒绝全文见 ../correction-view-unwired-v0.1/FINDING.md。
"""

from __future__ import annotations

import hashlib
import json

from compile_view import canonical, sha256_hex


# --- 探针对象:一次性钉住四个旋钮 -------------------------------------------
# 键序故意不是字典序(b, a, c / z, y);值含非 ASCII(β);含嵌套对象、null、true。
PROBE = {"b": "β", "a": 1, "c": {"z": True, "y": None}}

# §3 canonical = json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",",":"))
# 下面这行是手写的期望字节,不是算出来的。
SPEC_CANONICAL_TEXT = '{"a":1,"b":"β","c":{"y":null,"z":true}}'
SPEC_CANONICAL_SHA256 = (
    "2fbdacd536050ea2ec3bad8d1b7e7acb7f1bb04aed7080c26a68bd7568606764"
)

# 真账本 11 条更正里实际在用的那个函数(ensure_ascii=False,不排序,默认分隔符)。
# 同样手写。留在这里是为了让「两端不是同一个函数」成为可执行的事实,而不是一句论断。
LEGACY_TEXT = '{"b": "β", "a": 1, "c": {"z": true, "y": null}}'
LEGACY_SHA256 = "6ff8b75a62ebd147e3242f3f4056a254bbd2aeafcf657dcc3186f9e159ab8a7e"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_frozen_hashes_are_hashes_of_the_handwritten_texts():
    """先自检:两个冻结 hex 确实是上面两串手写文本的 sha256。

    这一条保证后面的断言不是在拿一个来路不明的常数比对。
    """
    assert _sha(SPEC_CANONICAL_TEXT) == SPEC_CANONICAL_SHA256
    assert _sha(LEGACY_TEXT) == LEGACY_SHA256


def test_canonical_emits_exactly_the_handwritten_spec_bytes():
    """canonical() 的输出字节 == 手写的 §3 期望字节。

    一次同时钉住:sort_keys=True、separators=(",",":")、ensure_ascii=False、UTF-8 编码。
    任一旋钮被改动,这里转红。
    """
    assert canonical(PROBE) == SPEC_CANONICAL_TEXT.encode("utf-8")


def test_canonical_sha_matches_frozen_hex():
    """after_hash 的计算链(canonical → utf-8 → sha256)整条钉死到一个冻结 hex。"""
    assert sha256_hex(canonical(PROBE)) == SPEC_CANONICAL_SHA256


def test_spec_and_legacy_writer_conventions_are_different_functions():
    """写方口径与 §3 读方口径不是同一个函数——这就是 0/11 的成因。

    15 天里两端各自演化、各自"全绿",没有任何一个测试同时约束过这两端。
    """
    assert SPEC_CANONICAL_SHA256 != LEGACY_SHA256
    assert canonical(PROBE) != LEGACY_TEXT.encode("utf-8")
    # 现实中的写方口径确实产出 LEGACY_TEXT(此处允许用 json.dumps:它是"被诊断对象",不是期望值来源)
    assert json.dumps(PROBE, ensure_ascii=False) == LEGACY_TEXT


def test_canonical_is_key_order_invariant_but_legacy_is_not():
    """§3 选 sort_keys 的承重理由,做成可执行的。

    语义相同、键序不同的两个对象,在 §3 下必须同哈希(否则 after_hash 会因写方
    构造对象时的插入顺序而变);在写方现用口径下则不同哈希。
    这条是「乙(写方向 §3 靠)」优于「甲(§3 改成现用口径)」的那个具体代价。
    """
    a = {"a": 1, "b": 2}
    b = {"b": 2, "a": 1}
    assert a == b  # 语义上是同一个值

    assert canonical(a) == canonical(b)
    assert sha256_hex(canonical(a)) == (
        "43258cff783fe7036d8a43033f830adfc60ec037382473548ac742b888292777"
    )

    assert json.dumps(a, ensure_ascii=False) != json.dumps(b, ensure_ascii=False)
