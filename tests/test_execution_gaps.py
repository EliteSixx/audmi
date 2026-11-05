import json
import unittest
from collections import Counter
from datetime import datetime, timedelta, timezone

from src.core.registry import RuleRegistry, load_registry, rule_from_dict

from src.analytics.execution_gaps import (
    DEFAULT_DATASET_DIR,
    EvidenceRecords,
    analyze_evidence,
    detect_execution_gaps,
    load_evidence,
)
from src.normalization.evidence_model import Alert, Asset, Case, CSE, Escalation, Investigation


UTC = timezone.utc
NOW = datetime(2025, 1, 1, tzinfo=UTC)


class ExecutionGapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.findings = detect_execution_gaps()
        cls.ground_truth = json.loads(
            (DEFAULT_DATASET_DIR / "ground_truth.json").read_text(encoding="utf-8")
        )

    def test_seeded_missing_escalation_cases_are_detected(self) -> None:
        seeded = {
            record_id
            for condition in self.ground_truth["conditions"]
            if condition["condition_type"] == "missing_escalation"
            and condition["cse_id"] == "CSE-02"
            for record_id in condition["record_ids"]
        }
        investigated_cases = {item.case_id for item in load_evidence().investigations}
        seeded_with_investigation = seeded & investigated_cases
        found = {
            item.subject_id
            for item in self.findings
            if item.rule_id == "missing_escalation"
        }
        self.assertTrue(seeded_with_investigation)
        self.assertTrue(seeded_with_investigation.issubset(found))

    def test_seeded_short_investigations_are_detected(self) -> None:
        seeded = {
            record_id
            for condition in self.ground_truth["conditions"]
            if condition["condition_type"] == "unusually_short_investigation"
            and condition["cse_id"] == "CSE-04"
            for record_id in condition["record_ids"]
        }
        found = {
            item.subject_id
            for item in self.findings
            if item.rule_id == "unusually_short_investigation"
        }
        self.assertTrue(seeded)
        self.assertTrue(seeded.issubset(found))
        short_findings = [
            item for item in self.findings
            if item.rule_id == "unusually_short_investigation"
        ]
        self.assertTrue(all(item.baseline and item.baseline["lower_threshold_seconds"] for item in short_findings))
        self.assertLess(
            short_findings[0].baseline["observed_duration_seconds"],
            short_findings[0].baseline["lower_threshold_seconds"],
        )

    def test_seeded_repeated_alert_assets_are_detected(self) -> None:
        seeded = {
            asset_id
            for condition in self.ground_truth["conditions"]
            if condition["condition_type"] == "repeated_alerts_without_remediation"
            for asset_id in condition["asset_ids"]
        }
        found = {
            item.subject_id
            for item in self.findings
            if item.rule_id == "repeated_alerts_without_remediation"
        }
        self.assertTrue(seeded)
        self.assertTrue(seeded.issubset(found))

    def test_normal_profile_assets_are_not_flagged_for_repetition(self) -> None:
        repeated_assets = {
            item.subject_id
            for item in self.findings
            if item.rule_id == "repeated_alerts_without_remediation"
        }
        self.assertFalse(any(asset_id.startswith("AST-01-") for asset_id in repeated_assets))

    def test_every_finding_has_source_record_ids(self) -> None:
        self.assertTrue(self.findings)
        for finding in self.findings:
            self.assertTrue(finding.supporting_record_ids)
            self.assertTrue(all(finding.supporting_record_ids))
            self.assertIn("Potential", finding.reason)

    def test_findings_are_deterministic(self) -> None:
        again = detect_execution_gaps()
        self.assertEqual(
            [item.to_dict() for item in self.findings],
            [item.to_dict() for item in again],
        )

    def test_missing_and_malformed_optional_workflow_records_do_not_crash(self) -> None:
        cse = CSE("CSE-X", "Fixture CSE", "fixture")
        asset = Asset("AST-X", cse.cse_id, "critical", "server")
        alert = Alert("ALT-X", cse.cse_id, asset.asset_id, "critical", "intrusion", NOW)
        case = Case("CAS-X", cse.cse_id, alert.alert_id, "open", NOW + timedelta(minutes=1))
        investigation = Investigation(
            "INV-X", case.case_id, case.opened_at, "ANL-X", 1,
            ended_at=case.opened_at + timedelta(minutes=10),
        )
        partial = EvidenceRecords(
            cse=(cse,),
            assets=(asset,),
            alerts=(alert,),
            cases=(case,),
            investigations=(investigation, {"malformed": True}, None),
            escalations=None,
            remediations=(None,),
        )
        findings = analyze_evidence(partial)
        self.assertEqual([item.rule_id for item in findings], ["missing_escalation"])
        self.assertEqual(findings[0].subject_id, case.case_id)

    def test_escalated_or_uninvestigated_cases_do_not_raise_missing_escalation(self) -> None:
        cse = CSE("CSE-Y", "Fixture CSE", "fixture")
        asset = Asset("AST-Y", cse.cse_id, "critical", "server")
        alert = Alert("ALT-Y", cse.cse_id, asset.asset_id, "high", "intrusion", NOW)
        case = Case("CAS-Y", cse.cse_id, alert.alert_id, "open", NOW + timedelta(minutes=1))
        escalation = Escalation("ESC-Y", case.case_id, "management", case.opened_at)
        evidence = EvidenceRecords(
            cse=(cse,), assets=(asset,), alerts=(alert,), cases=(case,),
            investigations=(), escalations=(escalation,), remediations=(),
        )
        self.assertEqual(analyze_evidence(evidence), [])

    def test_golden_dataset_finding_counts_are_unchanged(self) -> None:
        # Pinned to generator v2 (realistic baselines + overlapping duration
        # distributions). A changed threshold or rule must show up here.
        counts = Counter(item.rule_id for item in self.findings)
        self.assertEqual(
            dict(counts),
            {
                "missing_escalation": 279,
                "unusually_short_investigation": 127,
                "repeated_alerts_without_remediation": 8,
                "negative_space_low_activity": 8,
            },
        )

    def test_findings_carry_registry_metadata(self) -> None:
        registry = load_registry()
        for finding in self.findings:
            rule = registry[finding.rule_id]
            self.assertEqual(finding.rule_version, rule.version)
            self.assertIs(finding.capability, rule.capability)
            self.assertIs(finding.category, rule.category)
            self.assertIs(finding.subject_type, rule.subject_type)
            self.assertTrue(finding.baseline)
            self.assertIn(finding.subject_id, finding.supporting_record_ids)

    def test_parameters_come_from_the_registry(self) -> None:
        cse = CSE("CSE-Z", "Fixture CSE", "fixture")
        asset = Asset("AST-Z", cse.cse_id, "critical", "server")
        alert = Alert("ALT-Z", cse.cse_id, asset.asset_id, "medium", "intrusion", NOW)
        case = Case("CAS-Z", cse.cse_id, alert.alert_id, "open", NOW + timedelta(minutes=1))
        evidence = EvidenceRecords(cse=(cse,), assets=(asset,), alerts=(alert,), cases=(case,))
        self.assertEqual(analyze_evidence(evidence), [])

        rule = load_registry()["missing_escalation"]
        loosened = rule_from_dict(
            {
                **{key: getattr(rule, key) for key in (
                    "id", "title", "version", "status", "level", "description")},
                "capability": rule.capability.value,
                "category": rule.category.value,
                "subject_type": rule.subject_type.value,
                "false_positives": list(rule.false_positives),
                "parameters": {
                    "escalation_required_severities": ["medium", "high", "critical"],
                    "require_investigation": False,
                },
            }
        )
        findings = analyze_evidence(evidence, RuleRegistry({loosened.id: loosened}))
        self.assertEqual([item.subject_id for item in findings], ["CAS-Z"])
        self.assertEqual(findings[0].baseline["observed_investigation_count"], 0)

    def test_rules_missing_from_registry_do_not_run(self) -> None:
        self.assertEqual(
            detect_execution_gaps(registry=RuleRegistry({})),
            [],
        )


if __name__ == "__main__":
    unittest.main()
