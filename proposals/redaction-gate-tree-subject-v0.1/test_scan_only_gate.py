import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
GATE_PATH = (
    ROOT / "proposals" / "scaffold-opensource-export-v0.1"
    / "scan_only_gate.py"
)
SPEC = importlib.util.spec_from_file_location("scan_only_gate_under_test", GATE_PATH)
GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)

TOKEN = "fixture-private-token"
OTHER = "fixture-second-token"
HEX_A = "a" * 64
HEX_B = "b" * 64


class GateFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.repo = self.base / "repo"
        self.repo.mkdir()
        self.patterns = self.base / "patterns.txt"
        self.registry = self.base / "registry.jsonl"
        self.patterns.write_text(TOKEN + "\n", encoding="utf-8")
        self.registry.write_bytes(b"")
        self.git("init", "-q")
        self.git("config", "user.email", "gate@example.invalid")
        self.git("config", "user.name", "Gate Fixture")
        self.previous_cwd = os.getcwd()
        os.chdir(self.repo)
        self.previous_registry = GATE.DEFAULT_REGISTRY
        GATE.DEFAULT_REGISTRY = str(self.registry)

    def tearDown(self):
        GATE.DEFAULT_REGISTRY = self.previous_registry
        os.chdir(self.previous_cwd)
        self.temp.cleanup()

    def git(self, *args):
        return subprocess.run(
            ["git", *args], cwd=self.repo, check=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        ).stdout.decode("utf-8", errors="strict").strip()

    def write(self, relative, text, encoding="utf-8"):
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding=encoding)
        return path

    def commit(self, message="fixture"):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)
        return self.git("rev-parse", "HEAD")

    def run_gate(self, *args):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            rc = GATE.main([
                *args,
                "--private-strings", str(self.patterns),
            ])
        payload = json.loads(stdout.getvalue()) if stdout.getvalue() else None
        return rc, payload, stdout.getvalue(), stderr.getvalue()

    def run_commit(self, commit="HEAD"):
        return self.run_gate("--commit", commit)

    def valid_anchor(self, occurrence, **overrides):
        anchor = {
            key: occurrence[key] for key in GATE.IDENTITY_FIELDS
        }
        anchor.update({
            "peer_attestation": "independently recomputed from live remote oid",
            "live_remote_oid": "1" * 40,
            "proposal_line_sha256": HEX_A,
            "consent_line_sha256": HEX_B,
        })
        anchor.update(overrides)
        return anchor

    def set_registry(self, *anchors):
        raw = b"".join(
            json.dumps(anchor, ensure_ascii=False, separators=(",", ":")).encode()
            + b"\n"
            for anchor in anchors
        )
        self.registry.write_bytes(raw)

    def first_occurrence(self):
        rc, payload, _stdout, _stderr = self.run_commit()
        self.assertEqual(2, rc)
        return payload["occurrences"][0]

    def test_01_new_path_same_string_is_new_matches(self):
        self.write("old.txt", TOKEN + "\n")
        self.commit("old path")
        anchor = self.valid_anchor(self.first_occurrence())
        self.set_registry(anchor)
        self.git("mv", "old.txt", "new.txt")
        self.commit("new path")
        rc, payload, _stdout, _stderr = self.run_commit()
        self.assertEqual((2, "NEW_MATCHES"), (rc, payload["state"]))

    def test_02_delete_old_line_add_new_line_same_count_is_new_matches(self):
        self.write("record.txt", "before " + TOKEN + "\n")
        self.commit("old record")
        anchor = self.valid_anchor(self.first_occurrence())
        self.set_registry(anchor)
        self.write("record.txt", "after " + TOKEN + "\n")
        self.commit("new record")
        rc, payload, _stdout, _stderr = self.run_commit()
        self.assertEqual((2, "NEW_MATCHES"), (rc, payload["state"]))

    def test_03_ruleset_reorder_is_new_matches(self):
        self.patterns.write_text(TOKEN + "\n" + OTHER + "\n", encoding="utf-8")
        self.write("record.txt", TOKEN + "\n")
        self.commit("ordered rules")
        anchor = self.valid_anchor(self.first_occurrence())
        self.set_registry(anchor)
        self.patterns.write_text(OTHER + "\n" + TOKEN + "\n", encoding="utf-8")
        rc, payload, _stdout, _stderr = self.run_commit()
        self.assertEqual((2, "NEW_MATCHES"), (rc, payload["state"]))

    def test_04_tail_append_preserves_known_public_only(self):
        self.write("ledger.jsonl", '{"value":"' + TOKEN + '"}\n')
        self.commit("ledger base")
        anchor = self.valid_anchor(self.first_occurrence())
        self.set_registry(anchor)
        with (self.repo / "ledger.jsonl").open("a", encoding="utf-8", newline="") as fh:
            fh.write('{"value":"ordinary"}\n')
        self.commit("ledger append")
        rc, payload, _stdout, _stderr = self.run_commit()
        self.assertEqual((3, "KNOWN_PUBLIC_ONLY"), (rc, payload["state"]))

    def test_05_empty_registry_two_occurrences_is_new_matches(self):
        self.write("two.txt", TOKEN + " " + TOKEN + "\n")
        self.commit("two occurrences")
        rc, payload, _stdout, _stderr = self.run_commit()
        self.assertEqual((2, "NEW_MATCHES", 2),
                         (rc, payload["state"], payload["occurrence_count"]))

    def test_06_tree_output_is_byte_identical_to_legacy_shape(self):
        self.write("plain.txt", "ordinary\n")
        self.commit("tree fixture")
        rc, payload, actual, stderr = self.run_gate("--tree", str(self.repo))
        expected_payload = {
            "tree": os.path.abspath(self.repo),
            "files_scanned": 1,
            "pattern_count": 1,
            "hit_count": 0,
            "hits": [],
            "verdict": "PASS",
        }
        expected = json.dumps(
            expected_payload, ensure_ascii=False, indent=1
        ) + "\n"
        self.assertEqual((0, "", expected), (rc, stderr, actual))
        self.assertEqual(expected_payload, payload)

    def test_07_stale_anchor_and_zero_occurrences_is_clean(self):
        self.write("record.txt", TOKEN + "\n")
        self.commit("old occurrence")
        anchor = self.valid_anchor(self.first_occurrence())
        self.set_registry(anchor)
        self.patterns.write_text(OTHER + "\n", encoding="utf-8")
        self.write("record.txt", "ordinary\n")
        self.commit("no current occurrence")
        rc, payload, _stdout, _stderr = self.run_commit()
        self.assertEqual((0, "CLEAN"), (rc, payload["state"]))

    def test_08_only_old_digest_anchor_is_stale_new_matches(self):
        self.write("record.txt", TOKEN + "\n")
        self.commit("old digest")
        anchor = self.valid_anchor(self.first_occurrence())
        self.set_registry(anchor)
        self.patterns.write_text(TOKEN + "\n" + OTHER + "\n", encoding="utf-8")
        rc, payload, _stdout, _stderr = self.run_commit()
        self.assertEqual((2, "NEW_MATCHES", ["anchor_ruleset_stale"]),
                         (rc, payload["state"], payload["reason_codes"]))

    def test_09_non_commit_rejected_and_short_commit_resolved(self):
        self.write("plain.txt", "ordinary\n")
        parent = self.commit("objects")
        self.git(
            "update-index", "--add", "--cacheinfo",
            f"160000,{parent},vendor/{TOKEN}-submodule",
        )
        self.git("commit", "-q", "-m", "synthetic gitlink")
        full = self.git("rev-parse", "HEAD")
        tree = self.git("rev-parse", "HEAD^{tree}")
        blob = self.git("rev-parse", "HEAD:plain.txt")
        for invalid in (tree, blob, "not-a-revision"):
            rc, payload, stdout, _stderr = self.run_commit(invalid)
            self.assertEqual((1, None, ""), (rc, payload, stdout))
        short = full[:8]
        rc, payload, _stdout, _stderr = self.run_commit(short)
        self.assertEqual(
            (2, short, full, 1, "path"),
            (
                rc,
                payload["commit"],
                payload["resolved_oid"],
                payload["non_blob_entries"],
                payload["occurrences"][0]["where"],
            ),
        )

    def test_10_patterns_file_in_commit_tree_is_usage_fail(self):
        tracked_patterns = self.write("patterns.txt", TOKEN + "\n")
        self.patterns = tracked_patterns
        self.write("plain.txt", "ordinary\n")
        self.commit("tracked patterns")
        rc, payload, stdout, _stderr = self.run_commit()
        self.assertEqual((1, None, ""), (rc, payload, stdout))

    def test_11_all_stale_registry_zero_occurrences_is_clean_and_visible(self):
        self.write("record.txt", TOKEN + "\n")
        self.commit("stale anchors")
        occurrence = self.first_occurrence()
        first = self.valid_anchor(occurrence)
        second = self.valid_anchor(
            occurrence, path="other.txt", occurrence_ordinal=1
        )
        self.set_registry(first, second)
        self.patterns.write_text(OTHER + "\n", encoding="utf-8")
        self.write("record.txt", "ordinary\n")
        self.commit("clean current tree")
        rc, payload, _stdout, _stderr = self.run_commit()
        self.assertEqual((0, "CLEAN", 2),
                         (rc, payload["state"], payload["stale_anchor_count"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
