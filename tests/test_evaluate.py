import json
import tempfile
import unittest
from pathlib import Path

from src.core.findings import Finding
from src.core.registry import load_registry
from src.validation.evaluate import ALL_COHORTS, evaluate, format_table, run


REGISTRY = load_registry()


def _finding(rule_id: str, cse_id: str, subject_id: str) -> Finding:
    rule = REGISTRY[rule_id]
    return Finding(
        finding_id=f"F-{subject_id}",
        rule_id=rule.id,
        rule_version=rule.version,
        capability=rule.capability,
        category=rule.category,
        cse_id=cse_id,
        subject_type=rule.subject_type,
        subject_id=subject_id,
        reason="Potential execution gap: fixture.",
        supporting_record_ids=(subject_id,),
    )


def _row(report, condition_type, cohort):
    matches = [
        item for item in report["results"]
        if item["condition_type"] == condition_type and item["cohort"] == cohort
    ]
    assert len(matches) == 1, matches
    return matches[0]


class EvaluateFixtureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.truth = {
            "seed": 1,
            "conditions": [
                {"condition_type": "missing_escalation", "cse_id": "CSE-A",
                 "record_ids": ["CAS-1", "CAS-2", "CAS-3"]},
                {"condition_type": "missing_escalation", "cse_id": "CSE-B",
                 "record_ids": ["CAS-9"]},
                {"condition_type": "repeated_alerts_without_remediation", "cse_id": "CSE-A",
                 "asset_ids": ["AST-1"], "record_ids": ["CAS-1", "CAS-2"]},
                {"condition_type": "negative_space_low_activity", "cse_id": "CSE-C",
                 "asset_ids": ["AST-7", "AST-8"], "record_ids": []},
            ],
        }
        self.findings = [
            _finding("missing_escalation", "CSE-A", "CAS-1"),
            _finding("missing_escalation", "CSE-A", "CAS-2"),
            _finding("missing_escalation", "CSE-A", "CAS-50"),
            _finding("missing_escalation", "CSE-Z", "CAS-60"),
            _finding("repeated_alerts_without_remediation", "CSE-A", "AST-1"),
        ]
        self.report = evaluate(self.findings, self.truth, REGISTRY)

    def test_per_cohort_counts(self) -> None:
        row = _row(self.report, "missing_escalation", "CSE-A")
        self.assertEqual(
            (row["flagged"], row["seeded"], row["caught"], row["missed"], row["unclassified"]),
            (3, 3, 2, 1, 1),
        )
        self.assertEqual(row["missed_ids"], ["CAS-3"])
        self.assertAlmostEqual(row["precision"], 0.6667)
        self.assertAlmostEqual(row["recall"], 0.6667)

    def test_cohort_with_no_flags_has_undefined_precision(self) -> None:
        row = _row(self.report, "missing_escalation", "CSE-B")
        self.assertEqual((row["flagged"], row["caught"], row["missed"]), (0, 0, 1))
        self.assertIsNone(row["precision"])
        self.assertEqual(row["recall"], 0.0)

    def test_all_cohort_includes_flags_from_unseeded_cses(self) -> None:
        row = _row(self.report, "missing_escalation", ALL_COHORTS)
        self.assertEqual((row["flagged"], row["seeded"], row["caught"], row["unclassified"]),
                         (4, 4, 2, 2))

    def test_repeated_alerts_scored_at_asset_level(self) -> None:
        row = _row(self.report, "repeated_alerts_without_remediation", "CSE-A")
        self.assertEqual(row["subject_type"], "asset")
        self.assertEqual((row["seeded"], row["caught"], row["unclassified"]), (1, 1, 0))

    def test_condition_without_detector_is_reported(self) -> None:
        row = _row(self.report, "negative_space_low_activity", "CSE-C")
        self.assertEqual(row["status"], "no detector")
        self.assertEqual(row["seeded"], 2)
        self.assertIn("no detector", format_table(self.report))

    def test_outside_flags_are_never_called_false_positives(self) -> None:
        text = json.dumps(self.report) + format_table(self.report)
        self.assertNotIn("false_positive", text)
        self.assertIn("unclassified", text)


class EvaluateGoldenDatasetTests(unittest.TestCase):
    def test_golden_dataset_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "eval_report.json"
            report = run(output_path=output)
            written = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(written["results"], report["results"])
        self.assertEqual(len(report["ground_truth_sha256"]), 64)

        expected = {
            "missing_escalation": (279, 70, 70, 0, 209),
            "unusually_short_investigation": (127, 105, 105, 0, 22),
            "repeated_alerts_without_remediation": (8, 8, 8, 0, 0),
        }
        for condition_type, numbers in expected.items():
            row = _row(report, condition_type, ALL_COHORTS)
            self.assertEqual(
                (row["flagged"], row["seeded"], row["caught"], row["missed"], row["unclassified"]),
                numbers,
                condition_type,
            )
        self.assertEqual(
            _row(report, "negative_space_low_activity", "CSE-05")["status"], "no detector"
        )


if __name__ == "__main__":
    unittest.main()
