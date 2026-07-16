from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

import release_candidate_hygiene as hygiene


class ReleaseCandidateHygieneTests(unittest.TestCase):
    def make_repo(self, root: Path, payload: dict[str, bytes] | None = None) -> tuple[str, ...]:
        proposal = root / "proposals" / "public-release-consolidation-v0.1"
        proposal.mkdir(parents=True)
        manifest = {
            "schema": "weilan_release_install_manifest_v0.1",
            "payloads": [{"source": "skill/solve-with-weilan", "target": "skills/solve-with-weilan"}],
            "exclude_segments": ["__pycache__", ".pytest_cache"],
            "exclude_suffixes": [".pyc", ".pyo"],
        }
        for relative in hygiene.PROPOSAL_ALLOWLIST:
            path = root.joinpath(*Path(relative).parts)
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.name == "install-manifest.json":
                path.write_text(json.dumps(manifest), encoding="utf-8")
            else:
                path.write_text("safe candidate fixture\n", encoding="utf-8")
        for relative, content in (payload or {"SKILL.md": b"safe payload\n"}).items():
            path = root / "skill" / "solve-with-weilan" / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        return hygiene.expected_candidate_paths(root)

    def test_allowlist_is_proposal_inventory_plus_manifest_payload(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            paths = self.make_repo(root)
            unlisted = root / "proposals/public-release-consolidation-v0.1/peer-chat.jsonl"
            unlisted.write_text('{"private": true}\n', encoding="utf-8")
            self.assertEqual(set(paths), set(hygiene.PROPOSAL_ALLOWLIST) | {"skill/solve-with-weilan/SKILL.md"})
            self.assertNotIn(unlisted.relative_to(root).as_posix(), paths)

    def test_forbidden_runtime_state_paths_are_rejected(self) -> None:
        paths = [
            "skill/solve-with-weilan/wake-agent-runs/run.json",
            "skill/solve-with-weilan/peer-chat.jsonl",
            "skill/solve-with-weilan/wake-cursor.json",
            "skill/solve-with-weilan/wake-cron.log",
            "skill/solve-with-weilan/codex-inbox.jsonl",
        ]
        rules = [finding.rule for finding in hygiene.path_findings(paths)]
        self.assertEqual(rules.count("forbidden_runtime_segment"), 1)
        self.assertEqual(rules.count("forbidden_runtime_state"), 4)

    def test_absolute_paths_credentials_and_private_keys_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            paths = self.make_repo(
                root,
                {
                    "bad.txt": (
                        b"C:\\Users\\alice\\state\n"
                        b"D:\\CodexData\\method-state\n"
                        b"api_" b"key = 'abcdefghijklmno'\n"
                        b"-----BEGIN " b"PRIVATE KEY-----\n"
                    )
                },
            )
            rules = {finding.rule for finding in hygiene.content_findings(root, paths)}
            self.assertEqual(
                rules,
                {
                    "absolute_user_or_machine_path",
                    "credential_assignment",
                    "private_key_material",
                },
            )

    def test_hashes_cover_every_allowlisted_file_and_detect_byte_drift(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            paths = self.make_repo(root)
            before = hygiene.candidate_hashes(root, paths)
            before_tree = hygiene.tree_hash(before)
            changed = root / "skill/solve-with-weilan/SKILL.md"
            changed.write_text("changed\n", encoding="utf-8")
            after = hygiene.candidate_hashes(root, paths)
            self.assertEqual(set(before), set(paths))
            self.assertNotEqual(before["skill/solve-with-weilan/SKILL.md"], after["skill/solve-with-weilan/SKILL.md"])
            self.assertNotEqual(before_tree, hygiene.tree_hash(after))

    def test_escaped_relative_windows_path_is_not_an_absolute_path(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            paths = self.make_repo(
                root,
                {"safe.py": b"Join-Path $PSScriptRoot '..\\\\lib\\\\runner.py'\n"},
            )
            rules = {finding.rule for finding in hygiene.content_findings(root, paths)}
            self.assertNotIn("absolute_user_or_machine_path", rules)

    def test_clean_fixture_passes_without_scanning_unlisted_private_file(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.make_repo(root)
            outside_allowlist = root / "private-home-copy.txt"
            outside_allowlist.write_text("sk-" + "abcdefghijklmnopqrstuvwxyz" + "\n", encoding="utf-8")
            report = hygiene.verify_repository_candidate(root)
            self.assertEqual(report["verdict"], "PASS")
            self.assertNotIn(outside_allowlist.name, report["files"])
            self.assertEqual(report["file_count"], len(report["files"]))


if __name__ == "__main__":
    unittest.main()
