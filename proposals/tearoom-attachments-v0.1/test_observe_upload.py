"""UI-only attachment upload tests (tearoom-attachments-v0.1, observe.py integration)."""

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bounded-scheduler-v0.1" / "impl"))

import observe  # noqa: E402


@pytest.fixture
def upload_dir(tmp_path, monkeypatch):
    target = tmp_path / "attachments" / "inbox"
    monkeypatch.setattr(observe, "UPLOAD_DIR", target)
    return target


def test_sanitize_filename_keeps_cjk_blocks_paths():
    assert observe.sanitize_filename("..\\..\\evil.jpg") == "evil.jpg"
    assert observe.sanitize_filename("照片 2.jpg") == "照片_2.jpg"
    assert observe.sanitize_filename("...") == "attachment"


def test_save_upload_writes_file_and_sidecar(upload_dir):
    raw = b"\xff\xd8\xff\xe0fake-jpeg"
    meta = observe.save_upload(raw, "照片.jpg")
    assert meta["size"] == len(raw)
    assert meta["sha256"] == hashlib.sha256(raw).hexdigest()
    assert meta["mime"] == "image/jpeg"
    assert (upload_dir / meta["stored"]).read_bytes() == raw
    sidecar = upload_dir / (meta["stored"] + ".meta.json")
    assert sidecar.exists()
    assert json.loads(sidecar.read_text(encoding="utf-8"))["name"] == "照片.jpg"


def test_save_upload_rejects_too_large(upload_dir, monkeypatch):
    monkeypatch.setattr(observe, "MAX_UPLOAD_BYTES", 4)
    with pytest.raises(ValueError):
        observe.save_upload(b"12345", "big.txt")


def test_recent_uploads_returns_announced_files(upload_dir):
    observe.save_upload(b"one", "one.txt")
    observe.save_upload(b"two", "two.txt")
    rows = observe.recent_uploads()
    assert len(rows) == 2
    assert {row["name"] for row in rows} == {"one.txt", "two.txt"}


def test_render_contains_upload_form():
    page = observe.render()
    assert 'action="/upload"' in page
    assert 'name="file"' in page
    assert "attachments/inbox" in page
    assert "上传附件" in page


def test_parse_multipart_extracts_file():
    boundary = "----TestBoundary"
    body = (
        "--"
        + boundary
        + "\r\n"
        + 'Content-Disposition: form-data; name="file"; filename="photo.jpg"\r\n'
        + "Content-Type: image/jpeg\r\n\r\n"
        + "abc"
        + "\r\n--"
        + boundary
        + "--\r\n"
    ).encode("utf-8")
    fields = observe._parse_multipart(body, 'multipart/form-data; boundary="' + boundary + '"')
    assert fields["file"] == b"abc"
    assert fields["_filename"] == b"photo.jpg"
