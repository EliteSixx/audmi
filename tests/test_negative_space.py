import json
import unittest
from datetime import datetime, timezone

from src.analytics.common import EvidenceRecords
from src.analytics.execution_gaps import DEFAULT_DATASET_DIR, load_evidence
from src.analytics.negative_space import find_negative_space_low_activity
from src.core.findings import Capability, Category, SubjectType
from src.core.registry import load_registry
from src.normalization.evidence_model import Alert, Asset, CSE


UTC = timezone.utc
NOW = datetime(2025, 1, 1, tzinfo=UTC)
RULE = load_registry()["negative_space_low_activity"]


def _fixture(
    *,
    target_criticality: str = "critical",
    target_alert_count: int = 0,
    peer_alert_count: int = 10,
    peer_count: int = 20,
) -> tuple[EvidenceRecords, str]:
    """Build one target asset plus ``peer_count`` peers in the same peer group.

    The target lives in CSE-A and all peers live in CSE-B, so a passing test
    also proves the comparison is made across the peer group, not the CSE.
    """
    cse_a = CSE("CSE-A", "Fixture A", "shared-group")
    cse_b = CSE("CSE-B", "Fixture B", "shared-group")
    target = Asset("AST-TARGET", cse_a.cse_id, target_criticality, "server")
    assets = [target]
    alerts = []
    alert_index = 0
    for number in range(peer_count):
        peer = Asset(f"AST-PEER-{number:03d}", cse_b.cse_id, "critical", "server")
        assets.append(peer)
        for _ in range(peer_alert_count):
            alert_index += 1
            alerts.append(
                Alert(
                    f"ALT-{alert_index:05d}",
                    cse_b.cse_id,
                    peer.asset_id,
                    "low",
                    "intrusion",
                    NOW,
                )
            )
    for number in range(target_alert_count):
        alert_index += 1
        alerts.append(
            Alert(
                f"ALT-{alert_index:05d}",
                cse_a.cse_id,
                target.asset_id,
                "low",
                "intrusion",
                NOW,
            )
        )
    records = EvidenceRecords(
        cse=(cse_a, cse_b),
        assets=tuple(assets),
        alerts=tuple(alerts),
        cases=(),
    )
    return records, target.asset_id


class NegativeSpaceRuleTests(unittest.TestCase):
    def test_silent_critical_asset_in_active_peer_group_is_flagged(self) -> None:
        records, target_id = _fixture()
        findings = find_negative_space_low_activity(records, RULE)
        self.assertEqual([item.subject_id for item in findings], [target_id])
        finding = findings[0]
        self.assertIs(finding.category, Category.NEGATIVE_SPACE)
        self.assertIs(finding.capability, Capability.THREAT_DETECTION)
        self.assertIs(finding.subject_type, SubjectType.ASSET)
        self.assertIn("Potential negative-space indicator", finding.reason)
        self.assertIn(target_id, finding.supporting_record_ids)
        self.assertEqual(finding.baseline["peer_group"], "shared-group")
        self.assertEqual(finding.baseline["peer_asset_count"], 20)
        self.assertEqual(finding.baseline["peer_median_alert_count"], 10.0)
        self.assertEqual(finding.baseline["observed_alert_count"], 0)
        self.assertEqual(len(finding.baseline["example_active_peer_asset_ids"]), 5)
        self.assertIn("not evidence that no activity occurred", finding.data_quality_notes[-1])

    def test_low_criticality_asset_is_not_flagged(self) -> None:
        records, _ = _fixture(target_criticality="low")
        self.assertEqual(find_negative_space_low_activity(records, RULE), [])

    def test_high_criticality_asset_is_flagged(self) -> None:
        records, target_id = _fixture(target_criticality="high")
        findings = find_negative_space_low_activity(records, RULE)
        self.assertEqual([item.subject_id for item in findings], [target_id])

    def test_asset_with_alerts_is_not_flagged(self) -> None:
        records, _ = _fixture(target_alert_count=1)
        self.assertEqual(find_negative_space_low_activity(records, RULE), [])

    def test_quiet_peer_group_is_not_evidence_of_negative_space(self) -> None:
        # Every peer has only two alerts, so silence is unremarkable.
        records, _ = _fixture(peer_alert_count=2)
        self.assertEqual(find_negative_space_low_activity(records, RULE), [])

    def test_too_few_peers_are_not_compared(self) -> None:
        records, _ = _fixture(peer_count=3)
        self.assertEqual(find_negative_space_low_activity(records, RULE), [])

    def test_asset_with_unknown_cse_is_skipped(self) -> None:
        records, _ = _fixture()
        records = EvidenceRecords(
            cse=records.cse[1:],
            assets=records.assets,
            alerts=records.alerts,
            cases=records.cases,
        )
        self.assertEqual(find_negative_space_low_activity(records, RULE), [])

    def test_parameters_come_from_the_rule_definition(self) -> None:
        # Raising max_alert_count must bring near-silent assets into scope,
        # proving the thresholds are read from the rule, not hard-coded.
        from src.core.registry import rule_from_dict

        loosened = rule_from_dict(
            {
                **{
                    key: getattr(RULE, key) for key in (
                        "id", "title", "version", "status", "level", "description")
                },
                "capability": RULE.capability.value,
                "category": RULE.category.value,
                "subject_type": RULE.subject_type.value,
                "false_positives": list(RULE.false_positives),
                "parameters": {**dict(RULE.parameters), "max_alert_count": 1},
            }
        )
        records, target_id = _fixture(target_alert_count=1)
        findings = find_negative_space_low_activity(records, loosened)
        self.assertEqual([item.subject_id for item in findings], [target_id])


class NegativeSpaceGoldenDatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.records = load_evidence()
        cls.findings = find_negative_space_low_activity(cls.records, RULE)
        cls.ground_truth = json.loads(
            (DEFAULT_DATASET_DIR / "ground_truth.json").read_text(encoding="utf-8")
        )

    def test_all_seeded_negative_space_assets_are_detected(self) -> None:
        seeded = {
            asset_id
            for condition in self.ground_truth["conditions"]
            if condition["condition_type"] == "negative_space_low_activity"
            for asset_id in condition["asset_ids"]
        }
        flagged = {item.subject_id for item in self.findings}
        self.assertEqual(len(seeded), 8)
        self.assertTrue(seeded.issubset(flagged))
        self.assertEqual(len(flagged), 8)

    def test_findings_use_the_asset_cse_and_peer_group(self) -> None:
        assets = {item.asset_id: item for item in self.records.assets}
        for finding in self.findings:
            self.assertEqual(finding.cse_id, assets[finding.subject_id].cse_id)
            self.assertEqual(finding.baseline["peer_group"], "communications-critical")


if __name__ == "__main__":
    unittest.main()
