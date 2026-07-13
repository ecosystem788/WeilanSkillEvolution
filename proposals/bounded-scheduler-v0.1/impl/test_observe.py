"""Focused rendering checks for the observer dashboard."""

import re
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import observe  # noqa: E402


def test_output_window_renders_newest_receipt_first():
    receipts = [
        {
            "frame_id": "wf-newest",
            "outcome": "success",
            "verdict": "new result",
            "source": "frame:wf-newest",
        },
        {
            "frame_id": "wf-older",
            "outcome": "success",
            "verdict": "old result",
            "source": "frame:wf-older",
        },
    ]

    with patch.object(observe, "recent_receipts", return_value=receipts):
        page = observe.render()

    output_html = re.search(
        r'<div class="outputbox" id="outputbox">(.*?)</div>\s*</div>',
        page,
        re.DOTALL,
    )
    assert output_html is not None
    first_receipt = re.search(r'wf-[a-z]+', output_html.group(1))
    assert first_receipt is not None
    assert first_receipt.group(0) == receipts[0]["frame_id"]


def test_exclusive_bind_rejects_second_instance():
    # 2026-07-13 事故回归:Windows 上两个观察窗曾双绑 8787,请求随机命中旧僵尸版。
    # 独占绑定后,同端口第二个实例必须响亮失败,不许静默共存。
    srv = observe.ExclusiveHTTPServer(("127.0.0.1", 0), observe.Handler)
    port = srv.server_address[1]
    try:
        with pytest.raises(OSError):
            observe.ExclusiveHTTPServer(("127.0.0.1", port), observe.Handler)
    finally:
        srv.server_close()
