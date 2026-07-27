"""Known-answer and object-closure tests for the daily-push scanner.

Run: python -m pytest test_scan_push_manifest.py -q
"""

import json
import pathlib
import subprocess
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from scan_push_manifest import PATTERNS  # noqa: E402

SCANNER = pathlib.Path(__file__).with_name("scan_push_manifest.py")
SOURCE_FILES = (SCANNER, pathlib.Path(__file__))


def assembled(*parts):
    """Build a synthetic secret shape without storing that shape in source."""
    return b"".join(parts)


# Every value is synthetic and non-resolving. Runtime fragment assembly keeps
# the scanner's own source and test source safe to include in a reviewed push.
POSITIVES = {
    "private_key_block": assembled(
        b"-----BE", b"GIN OPENSSH ", b"PRIVATE KEY-----\n", b"b3Blb\n"),
    "openssh_key_body": assembled(
        b"ssh-ed", b"25519 AA", b"AA",
        b"B3NzaC1lZDI1NTE5AAAAI" * 3, b" u@h"),
    "aws_access_key_id": assembled(b"AK", b"IA", b"QQQQWWWWEEEERRRR"),
    "github_token": assembled(b"gh", b"p_", b"0" * 36),
    "anthropic_key": assembled(b"sk-", b"ant-", b"a" * 24),
    "generic_sk_key": assembled(b"s", b"k-", b"Z" * 40),
    "slack_token": assembled(b"xo", b"xb-", b"1111111111-", b"abcdefghij"),
    "google_api_key": assembled(b"AI", b"za", b"0" * 35),
    "bearer_literal": assembled(
        b"Author", b"ization: Bear", b"er ", b"t" * 24),
    "assigned_credential": assembled(
        b"api_", b'key = "', b"hunter2", b'hunter2"'),
}

NEGATIVES = [
    # prose that mentions credentials without carrying one
    "推送前须做密钥扫描；password 一词本身不是密钥。".encode("utf-8"),
    b"See CONVENTION.md for how the signer rescans the secret findings list.",
    b"sha256 = 413d2ab27709b354e5babb8c3ed2456710317607ab4d4abbf970336809c7c63c",
    b"ssh-ed25519",  # bare algorithm name, no key body
    b"password:",    # empty assignment
]


def test_every_pattern_fires_on_its_planted_secret():
    by_name = dict(PATTERNS)
    assert set(by_name) == set(POSITIVES), "pattern list and fixtures drifted apart"
    for name, sample in POSITIVES.items():
        assert by_name[name].search(sample), f"{name} failed to fire"


def test_benign_text_produces_no_finding():
    for sample in NEGATIVES:
        hits = [n for n, rx in PATTERNS if rx.search(sample)]
        assert not hits, f"false positive {hits} on {sample!r}"


def source_pattern_hits(paths=SOURCE_FILES):
    hits = []
    for path in paths:
        payload = path.read_bytes()
        for name, rx in PATTERNS:
            for match in rx.finditer(payload):
                hits.append((path.name, name, match.start()))
    return hits


def test_scanner_sources_have_no_literal_pattern_hits():
    assert source_pattern_hits() == []


def test_source_hygiene_fails_closed_on_missing_or_unreadable_source(tmp_path):
    with pytest.raises(FileNotFoundError):
        source_pattern_hits((tmp_path / "missing.py",))
    with pytest.raises(OSError):
        source_pattern_hits((tmp_path,))


def git(repo, *args):
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    ).stdout


def write(repo, relative_path, text):
    path = repo / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def commit(repo, message):
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", message)


def initialize_repo(tmp_path, base_text="base\n"):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", ".")
    git(repo, "config", "user.email", "closure-test@local")
    git(repo, "config", "user.name", "closure-test")
    write(repo, "base.txt", base_text)
    commit(repo, "base")
    base = git(repo, "rev-parse", "HEAD").decode().strip()
    return repo, base


def synthetic_aws_key(fill):
    # Runtime assembly keeps new closure fixtures free of a literal key shape.
    prefix = "AK" + "IA"
    return prefix + fill * 16


def run_scanner(repo, remote_ref):
    proc = subprocess.run(
        [sys.executable, str(SCANNER), "--remote-ref", remote_ref],
        cwd=repo,
        capture_output=True,
    )
    return proc, json.loads(proc.stdout.decode("utf-8"))


def aws_findings(receipt):
    return [
        finding for finding in receipt["secret_findings"]
        if finding["pattern"] == "aws_access_key_id"
    ]


def test_intermediate_blob_secret_is_detected_after_head_is_clean(tmp_path):
    repo, base = initialize_repo(tmp_path)
    write(repo, "mid.txt", synthetic_aws_key("M") + "\n")
    commit(repo, "secret intermediate blob")
    write(repo, "mid.txt", "clean at HEAD\n")
    commit(repo, "clean endpoint")

    proc, receipt = run_scanner(repo, base)

    assert proc.returncode == 1
    assert any(
        finding["object_type"] == "blob"
        and finding["excerpt"] == synthetic_aws_key("M")
        for finding in aws_findings(receipt)
    )


def test_added_then_deleted_blob_secret_is_detected(tmp_path):
    repo, base = initialize_repo(tmp_path)
    write(repo, "gone.txt", synthetic_aws_key("D") + "\n")
    commit(repo, "add secret blob")
    git(repo, "rm", "-q", "gone.txt")
    commit(repo, "delete secret blob")

    proc, receipt = run_scanner(repo, base)

    assert proc.returncode == 1
    assert any(
        finding["object_type"] == "blob"
        and finding["excerpt"] == synthetic_aws_key("D")
        for finding in aws_findings(receipt)
    )


def test_commit_message_secret_is_detected(tmp_path):
    repo, base = initialize_repo(tmp_path)
    write(repo, "message.txt", "ordinary content\n")
    commit(repo, "message " + synthetic_aws_key("C"))

    proc, receipt = run_scanner(repo, base)

    assert proc.returncode == 1
    assert any(
        finding["object_type"] == "commit"
        and finding["excerpt"] == synthetic_aws_key("C")
        for finding in aws_findings(receipt)
    )


def test_object_already_reachable_from_base_is_not_rescanned(tmp_path):
    key = synthetic_aws_key("B")
    repo, base = initialize_repo(tmp_path, base_text=key + "\n")
    write(repo, "new.txt", "clean new content\n")
    commit(repo, "clean change")

    proc, receipt = run_scanner(repo, base)

    assert proc.returncode == 0
    assert receipt["clean"] is True
    assert aws_findings(receipt) == []


def test_secret_shaped_filename_is_detected_in_tree_object(tmp_path):
    repo, base = initialize_repo(tmp_path)
    key = synthetic_aws_key("F")
    write(repo, pathlib.Path("sub") / f"{key}.txt", "clean content\n")
    commit(repo, "secret-shaped filename")

    proc, receipt = run_scanner(repo, base)

    assert proc.returncode == 1
    assert any(
        finding["object_type"] == "tree"
        and finding["excerpt"] == key
        for finding in aws_findings(receipt)
    )


def test_receipt_and_manifest_digest_are_byte_stable(tmp_path):
    repo, base = initialize_repo(tmp_path)
    write(repo, "stable.txt", "stable\n")
    commit(repo, "stable change")

    first_proc, first = run_scanner(repo, base)
    second_proc, second = run_scanner(repo, base)

    assert first_proc.returncode == second_proc.returncode == 0
    assert first_proc.stdout == second_proc.stdout
    assert first["manifest_digest"] == second["manifest_digest"]
    assert [entry["object_id"] for entry in first["manifest"]] == sorted(
        entry["object_id"] for entry in first["manifest"]
    )
    assert "not an exact network-transfer set" in first["closure_semantics"]
    assert "relative to remote_ref" in first["closure_semantics"]
    assert "caller must fetch" in first["remote_ref_freshness"]
    assert "not directionally safe" in first["remote_ref_freshness"]
    assert "this new reachable-object closure" in first["scan_semantics"]
    assert (
        "not proof that the repository or published history contains no secret"
        in first["scan_semantics"]
    )
