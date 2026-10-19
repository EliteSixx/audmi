import json
import unittest
from pathlib import Path

from src.core.findings import Capability, Category, Finding, SubjectType


SCHEMA_PATH = Path(__file__).resolve().parents[1] / "data" / "schemas" / "finding.schema.json"


def _finding(**overrides):
    values = dict(
        finding_id="F-1",
        rule_id="missing_escalation",
        rule_version="1.0.0",
        capability="escalation",
        category="execution_gap",
        cse_id="CSE-01",
        subject_type="case",
        subject_id="CAS-1",
        reason="Potential execution gap: example.",
        supporting_record_ids=("CAS-1", "ALT-1"),
        baseline={"threshold": 1},
    )
    values.update(overrides)
    return Finding(**values)


class FindingSchemaTests(unittest.TestCase):
    def test_strings_are_coerced_to_enums(self) -> None:
        finding = _finding()
        self.assertIs(finding.capability, Capability.ESCALATION)
        self.assertIs(finding.category, Category.EXECUTION_GAP)
        self.assertIs(finding.subject_type, SubjectType.CASE)

    def test_there_are_exactly_eight_capabilities(self) -> None:
        self.assertEqual(len(Capability), 8)

    def test_invalid_enum_values_are_rejected(self) -> None:
        for name in ("capability", "category", "subject_type"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                _finding(**{name: "not_a_value"})

    def test_empty_evidence_chain_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            _finding(supporting_record_ids=())
        with self.assertRaises(ValueError):
            _finding(supporting_record_ids=("CAS-1", ""))

    def test_verdict_language_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            _finding(reason="Execution gap without hedging.")
        with self.assertRaises(ValueError):
            _finding(reason="Potential indicator: the SOC is non-compliant.")

    def test_finding_is_frozen_and_hashable(self) -> None:
        finding = _finding()
        with self.assertRaises(AttributeError):
            finding.rule_id = "other"  # type: ignore[misc]
        hash(finding)

    def test_to_dict_matches_json_schema_fields(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        payload = _finding().to_dict()
        json.dumps(payload)
        self.assertEqual(set(payload), set(schema["required"]))
        self.assertEqual(set(payload), set(schema["properties"]))
        self.assertEqual(payload["schema_version"], schema["properties"]["schema_version"]["const"])
        for name in ("capability", "category", "subject_type"):
            self.assertIn(payload[name], schema["properties"][name]["enum"])
        self.assertEqual(
            sorted(schema["properties"]["capability"]["enum"]),
            sorted(item.value for item in Capability),
        )


if __name__ == "__main__":
    unittest.main()
