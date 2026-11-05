import tempfile
import unittest
from pathlib import Path

import yaml

from src.core.findings import Capability, Category, SubjectType
from src.core.registry import RuleDefinitionError, load_registry, rule_from_dict


EXPECTED_RULES = {
    "missing_escalation",
    "negative_space_low_activity",
    "repeated_alerts_without_remediation",
    "unusually_short_investigation",
}


def _valid_rule(**overrides):
    raw = dict(
        id="example_rule",
        title="Example",
        version="1.0.0",
        status="experimental",
        level="low",
        capability="escalation",
        category="execution_gap",
        subject_type="case",
        description="Example rule.",
        parameters={"threshold": 1},
        false_positives=["Something benign."],
    )
    raw.update(overrides)
    return raw


class RegistryTests(unittest.TestCase):
    def test_repository_rules_load(self) -> None:
        registry = load_registry()
        self.assertEqual(set(registry.ids()), EXPECTED_RULES)
        for rule in registry:
            self.assertIsInstance(rule.capability, Capability)
            self.assertIsInstance(rule.category, Category)
            self.assertTrue(rule.parameters)
            self.assertTrue(rule.false_positives)
        self.assertIs(registry["negative_space_low_activity"].category, Category.NEGATIVE_SPACE)

    def test_thresholds_live_in_yaml(self) -> None:
        registry = load_registry()
        self.assertEqual(registry["unusually_short_investigation"].param("sigma_multiplier"), 3.5)
        repeated = registry["repeated_alerts_without_remediation"]
        self.assertEqual(repeated.param("sigma_multiplier"), 3.0)
        self.assertEqual(repeated.param("min_case_count"), 3)
        self.assertEqual(repeated.param("max_remediation_coverage"), 0.10)
        self.assertIs(registry["missing_escalation"].subject_type, SubjectType.CASE)

    def test_parameters_are_read_only(self) -> None:
        rule = load_registry()["missing_escalation"]
        with self.assertRaises(TypeError):
            rule.parameters["require_investigation"] = False  # type: ignore[index]

    def test_missing_parameter_fails_loudly(self) -> None:
        rule = rule_from_dict(_valid_rule())
        with self.assertRaises(RuleDefinitionError):
            rule.param("does_not_exist")

    def test_invalid_definitions_are_rejected(self) -> None:
        bad_values = [
            {"capability": "monitoring"},
            {"category": "verdict"},
            {"level": "severe"},
            {"status": "draft"},
            {"version": "v1"},
            {"parameters": [1, 2]},
        ]
        for override in bad_values:
            with self.subTest(override=override), self.assertRaises(RuleDefinitionError):
                rule_from_dict(_valid_rule(**override))
        incomplete = _valid_rule()
        del incomplete["false_positives"]
        with self.assertRaises(RuleDefinitionError):
            rule_from_dict(incomplete)

    def test_id_must_match_file_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "other_name.yaml").write_text(yaml.safe_dump(_valid_rule()), encoding="utf-8")
            with self.assertRaises(RuleDefinitionError):
                load_registry(tmp)

    def test_temporary_registry_loads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "example_rule.yaml").write_text(yaml.safe_dump(_valid_rule()), encoding="utf-8")
            registry = load_registry(tmp)
            self.assertEqual(registry.ids(), ["example_rule"])
            self.assertIn("example_rule", registry)


if __name__ == "__main__":
    unittest.main()
