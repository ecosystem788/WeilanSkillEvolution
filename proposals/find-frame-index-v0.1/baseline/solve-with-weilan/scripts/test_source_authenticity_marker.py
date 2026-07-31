import copy
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("weilan_trace.py")
SPEC = importlib.util.spec_from_file_location("candidate_weilan_trace", SCRIPT)
TRACE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TRACE)


def run_cli(environment, *arguments, expect_success=True):
    result = subprocess.run(
        [sys.executable, "-X", "utf8", str(SCRIPT), *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=environment,
    )
    if expect_success and result.returncode:
        raise AssertionError(result.stderr)
    return result


def json_result(environment, *arguments):
    return json.loads(run_cli(environment, *arguments).stdout)


def ledger_records(root, *parts):
    base = root.joinpath("memory", *parts)
    if not base.exists():
        return []
    return [
        json.loads(line)
        for path in base.rglob("*.jsonl")
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


class SourceAuthenticityMarkerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()
        self.environment = os.environ.copy()
        self.environment["WEILAN_METHOD_HOME"] = str(self.root / "method-state")
        self.environment["WEILAN_ALLOW_UNRESOLVED_CONVERSATION"] = "1"
        self.environment["WEILAN_SEMANTIC_BUDGET_DEFAULT"] = "20"
        self.common = [
            "--workspace",
            str(self.workspace),
            "--scope",
            "source-authenticity",
        ]

    def tearDown(self):
        self.temp.cleanup()

    def memory_note(self, suffix="note"):
        return json_result(
            self.environment,
            "memory-note",
            *self.common,
            "--signal",
            "verified_result",
            "--claim",
            f"speaker states result {suffix} is verified",
            "--source",
            f"conversation:fixture#{suffix}",
            "--kind",
            "fact",
            "--summary",
            f"result {suffix} is verified",
            "--stable",
            "--reusable",
            "--privacy-reviewed",
        )

    def capture_promote(self, suffix="capture", extra_sources=()):
        captured = json_result(
            self.environment,
            "evidence-capture",
            *self.common,
            "--signal",
            "verified_result",
            "--claim",
            f"speaker states result {suffix} is verified",
            "--source",
            f"conversation:fixture#{suffix}",
            *sum((["--source", source] for source in extra_sources), []),
        )
        promoted = json_result(
            self.environment,
            "evidence-promote",
            *self.common,
            "--evidence-id",
            captured["evidence_id"],
            "--kind",
            "fact",
            "--summary",
            f"result {suffix} is verified",
            "--stable",
            "--reusable",
            "--privacy-reviewed",
        )
        return captured, promoted

    def promoted_markers(self):
        return [
            record["source_authenticity"]
            for record in ledger_records(
                self.root / "method-state", "evidence", "promotions"
            )
            if record.get("decision") == "PROMOTED"
        ]

    def assert_bounded_contract(self, marker):
        self.assertEqual("no_authenticity_conclusion", marker["conclusion"])
        self.assertFalse(marker["observational_derivation"]["present"])
        self.assertEqual(
            "current_capture_contract_has_no_machine-check-proof",
            marker["observational_derivation"]["reason"],
        )
        self.assertNotIn("authentic", marker)
        self.assertNotIn("classification", marker)
        self.assertNotIn("basis", marker)

    def test_matrix_1_same_testimonial_contract_for_both_entrances(self):
        note = self.memory_note("same-note")
        _, promoted = self.capture_promote("same-capture")
        self.assertTrue(note["promoted"])
        self.assertTrue(promoted["promoted"])
        markers = self.promoted_markers()
        self.assertEqual(2, len(markers))
        for marker in markers:
            self.assertTrue(marker["testimonial_attestation"]["present"])
            self.assertEqual([], marker["non_testimonial_anchors"])
            self.assert_bounded_contract(marker)

    def test_matrix_2_mixed_sources_only_via_evidence_capture(self):
        anchor = self.workspace / "machine-result.json"
        anchor.write_text('{"checked": true}', encoding="utf-8")
        _, promoted = self.capture_promote("mixed", (str(anchor),))
        self.assertTrue(promoted["promoted"])
        marker = self.promoted_markers()[0]
        self.assertTrue(marker["testimonial_attestation"]["present"])
        self.assertEqual(
            [{"source_ref": str(anchor), "kind": "file"}],
            marker["non_testimonial_anchors"],
        )
        self.assert_bounded_contract(marker)

    def test_matrix_3_pure_conversation_has_no_observational_route(self):
        self.memory_note("pure-note")
        self.capture_promote("pure-capture")
        for marker in self.promoted_markers():
            self.assertEqual([], marker["non_testimonial_anchors"])
            self.assert_bounded_contract(marker)

    def test_matrix_4_callers_cannot_supply_classification_or_basis(self):
        rejected = run_cli(
            self.environment,
            "evidence-promote",
            *self.common,
            "--evidence-id",
            "missing",
            "--kind",
            "fact",
            "--summary",
            "missing evidence",
            "--stable",
            "--reusable",
            "--privacy-reviewed",
            "--classification",
            "observational_derivation",
            expect_success=False,
        )
        self.assertNotEqual(0, rejected.returncode)
        self.assertIn("unrecognized arguments", rejected.stderr)

        evidence = {
            "evidence_id": "e-1",
            "signal": "verified_result",
            "sources": ["conversation:fixture#turn"],
            "source_snapshots": [{"kind": "conversation_turn", "exists": True}],
        }
        summary_hash = "1" * 64
        marker = TRACE.build_source_authenticity_marker(evidence, summary_hash)
        marker["classification"] = "observational_derivation"
        promotion = {"summary_hash": summary_hash, "source_authenticity": marker}
        self.assertEqual(
            "untrusted", TRACE.interpret_source_authenticity(promotion, evidence)["status"]
        )

    def test_matrix_5_legacy_and_tampering_degrade_without_backfill(self):
        legacy = TRACE.interpret_source_authenticity({})
        self.assertEqual("legacy", legacy["status"])
        self.assertEqual("unclassified", legacy["classification"])
        self.assertEqual("no_authenticity_conclusion", legacy["conclusion"])

        evidence = {
            "evidence_id": "e-2",
            "signal": "verified_result",
            "sources": ["conversation:fixture#turn"],
            "source_snapshots": [{"kind": "conversation_turn", "exists": True}],
        }
        summary_hash = "2" * 64
        marker = TRACE.build_source_authenticity_marker(evidence, summary_hash)
        missing = copy.deepcopy(marker)
        missing.pop("provenance")
        self.assertEqual(
            "untrusted",
            TRACE.interpret_source_authenticity(
                {"summary_hash": summary_hash, "source_authenticity": missing}, evidence
            )["status"],
        )
        tampered = copy.deepcopy(marker)
        tampered["provenance"]["summary_sha256"] = "3" * 64
        self.assertEqual(
            "untrusted",
            TRACE.interpret_source_authenticity(
                {"summary_hash": summary_hash, "source_authenticity": tampered}, evidence
            )["status"],
        )

    def test_matrix_6_old_gate_acceptance_and_reader_output_are_preserved(self):
        captured, promoted = self.capture_promote("old-contract")
        self.assertTrue(promoted["promoted"])
        shown = json_result(self.environment, "evidence-show", *self.common, "--limit", "0")
        item = next(
            entry for entry in shown["results"] if entry["evidence_id"] == captured["evidence_id"]
        )
        self.assertEqual("declared", item["source_authenticity"]["status"])
        self.assertEqual(
            "no_authenticity_conclusion",
            item["source_authenticity"]["conclusion"],
        )


if __name__ == "__main__":
    unittest.main()
