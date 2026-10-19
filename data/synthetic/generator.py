"""Deterministic synthetic SOC evidence dataset generator for AudMi.

Run from the repository root with ``python data/synthetic/generator.py --seed 42``.
Operational files contain no planted-condition labels; those are written only to
the separate ground-truth file.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from src.normalization.evidence_model import (  # noqa: E402
    Alert,
    Asset,
    Case,
    CSE,
    Escalation,
    Investigation,
    Remediation,
)


DEFAULT_OUTPUT_DIR = REPOSITORY_ROOT / "data" / "synthetic" / "golden_dataset"
BASE_TIME = datetime(2025, 1, 1, tzinfo=timezone.utc)
COUNTS = {
    "cse": 6,
    "assets": 300,
    "alerts": 10_000,
    "cases": 2_000,
    "investigations": 1_500,
    "escalations": 300,
    "remediations": 100,
}
OUTPUT_FILES = (
    "cse.json",
    "assets.json",
    "alerts.json",
    "cases.json",
    "investigations.json",
    "escalations.json",
    "remediations.json",
    "ground_truth.json",
    "dataset_manifest.json",
)
SEVERITIES = ("informational", "low", "medium", "high", "critical")
SEVERITY_WEIGHTS = (0.12, 0.23, 0.34, 0.22, 0.09)
CATEGORIES = ("malware", "intrusion", "policy",
              "availability", "identity", "network")
ASSET_TYPES = ("server", "workstation", "network_device",
               "database", "security_appliance")


@dataclass
class SyntheticDataset:
    cse: list[CSE]
    assets: list[Asset]
    alerts: list[Alert]
    cases: list[Case]
    investigations: list[Investigation]
    escalations: list[Escalation]
    remediations: list[Remediation]
    ground_truth: dict[str, Any]
    dataset_manifest: dict[str, Any]


def _choose(rng: random.Random, values: tuple[str, ...], weights: tuple[float, ...]) -> str:
    return rng.choices(values, weights=weights, k=1)[0]


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def _record_dict(record: Any) -> dict[str, Any]:
    result = asdict(record)
    for name, value in result.items():
        if isinstance(value, datetime):
            result[name] = _iso(value)
    return result


def _status(rng: random.Random, closed_at: datetime | None) -> str:
    if closed_at is None:
        return _choose(rng, ("new", "open", "in_progress"), (0.12, 0.60, 0.28))
    return _choose(rng, ("closed", "resolved"), (0.35, 0.65))


def generate_dataset(seed: int = 42) -> SyntheticDataset:
    """Build all dataset records in memory, validate them, and return them."""
    rng = random.Random(seed)

    cse_records = [
        CSE(f"CSE-{index:02d}",
            f"Regional Cyber Security Entity {index:02d}", "regional")
        for index in range(1, 7)
    ]
    assets: list[Asset] = []
    assets_by_cse: dict[str, list[Asset]] = defaultdict(list)
    critical_assets_by_cse: dict[str, list[Asset]] = defaultdict(list)
    for cse in cse_records:
        for local_index in range(1, 51):
            criticality = "critical" if local_index <= 10 else _choose(
                rng, ("high", "medium", "low"), (0.28, 0.47, 0.25)
            )
            asset = Asset(
                asset_id=f"AST-{int(cse.cse_id[-2:]):02d}-{local_index:03d}",
                cse_id=cse.cse_id,
                criticality=criticality,
                asset_type=_choose(
                    rng, ASSET_TYPES, (0.30, 0.32, 0.16, 0.11, 0.11)),
            )
            assets.append(asset)
            assets_by_cse[cse.cse_id].append(asset)
            if criticality == "critical":
                critical_assets_by_cse[cse.cse_id].append(asset)

    # CSE-03 has repeated alert concentration on a small set of critical assets.
    repeat_assets = critical_assets_by_cse["CSE-03"][:8]
    # CSE-05 has selected critical assets with no generated alerts.
    low_activity_assets = critical_assets_by_cse["CSE-05"][:8]

    alerts: list[Alert] = []
    alerts_by_cse: dict[str, list[Alert]] = defaultdict(list)
    alerts_by_asset: dict[str, list[Alert]] = defaultdict(list)
    cse_alert_counts = (1_700, 1_700, 1_700, 1_700, 1_550, 1_650)
    alert_index = 0
    for cse, cse_count in zip(cse_records, cse_alert_counts):
        cse_number = int(cse.cse_id[-2:])
        regular_assets = [a for a in assets_by_cse[cse.cse_id]
                          if a not in low_activity_assets]
        for local_alert_index in range(cse_count):
            alert_index += 1
            if cse_number == 3 and local_alert_index < 320:
                asset = repeat_assets[local_alert_index % len(repeat_assets)]
            else:
                asset_pool = regular_assets
                if cse_number == 5 and local_alert_index >= 8:
                    # The eight named assets remain at zero activity while other
                    # critical assets in this CSE receive ordinary activity.
                    asset_pool = regular_assets
                asset = rng.choice(asset_pool)

            severity_weights = SEVERITY_WEIGHTS
            if cse_number == 2:
                severity_weights = (0.04, 0.12, 0.28, 0.34, 0.22)
            elif cse_number == 3 and asset in repeat_assets:
                severity_weights = (0.04, 0.12, 0.30, 0.34, 0.20)
            severity = _choose(rng, SEVERITIES, severity_weights)
            created_at = BASE_TIME + timedelta(
                days=rng.randint(0, 364),
                seconds=rng.randint(0, 86_399),
            )
            closed_at = None
            if rng.random() < 0.72:
                closed_at = created_at + timedelta(hours=rng.randint(24, 168))
            alert = Alert(
                alert_id=f"ALT-{alert_index:06d}",
                cse_id=cse.cse_id,
                asset_id=asset.asset_id,
                severity=severity,
                category=rng.choice(CATEGORIES),
                created_at=created_at,
                closed_at=closed_at,
            )
            alerts.append(alert)
            alerts_by_cse[cse.cse_id].append(alert)
            alerts_by_asset[asset.asset_id].append(alert)

    # Make sure at least one critical alert exists for every CSE-02 condition case.
    cse2_critical_alerts = [
        a for a in alerts_by_cse["CSE-02"] if a.severity in {"critical", "high"}
    ]
    rng.shuffle(cse2_critical_alerts)
    repeated_alerts = [a for a in alerts if a.asset_id in {
        x.asset_id for x in repeat_assets}]
    rng.shuffle(repeated_alerts)
    cse4_alerts = list(alerts_by_cse["CSE-04"])
    rng.shuffle(cse4_alerts)

    forced_alerts = (
        cse2_critical_alerts[:140]
        + repeated_alerts[:160]
        + cse4_alerts[:80]
        + [
            a for a in alerts_by_cse["CSE-06"]
            if a.severity in {"critical", "high"}
        ][:20]
    )
    selected_alert_ids: set[str] = set()
    selected_alerts: list[Alert] = []
    for alert in forced_alerts:
        if alert.alert_id not in selected_alert_ids:
            selected_alert_ids.add(alert.alert_id)
            selected_alerts.append(alert)
    remaining = [a for a in alerts if a.alert_id not in selected_alert_ids]
    rng.shuffle(remaining)
    selected_alerts.extend(remaining[: COUNTS["cases"] - len(selected_alerts)])
    selected_alerts = selected_alerts[: COUNTS["cases"]]

    cases: list[Case] = []
    case_by_alert_id: dict[str, Case] = {}
    alert_by_id = {a.alert_id: a for a in alerts}
    for case_index, alert in enumerate(selected_alerts, start=1):
        opened_at = alert.created_at + timedelta(minutes=rng.randint(5, 480))
        closed_at = None
        if rng.random() < 0.69:
            closed_at = opened_at + timedelta(days=rng.randint(2, 35))
        case = Case(
            case_id=f"CAS-{case_index:05d}",
            cse_id=alert.cse_id,
            alert_id=alert.alert_id,
            status=_status(rng, closed_at),
            opened_at=opened_at,
            closed_at=closed_at,
        )
        cases.append(case)
        case_by_alert_id[alert.alert_id] = case

    cases_by_cse: dict[str, list[Case]] = defaultdict(list)
    for case in cases:
        cases_by_cse[case.cse_id].append(case)
    cse2_target_cases = [
        case_by_alert_id[a.alert_id]
        for a in cse2_critical_alerts
        if a.alert_id in case_by_alert_id
    ][:100]
    cse3_repeat_cases = [
        case_by_alert_id[a.alert_id]
        for a in repeated_alerts
        if a.alert_id in case_by_alert_id
    ][:80]
    cse4_investigation_cases = cases_by_cse["CSE-04"][:100]
    cse6_mixed_cases = [
        case
        for alert in alerts_by_cse["CSE-06"]
        if alert.severity in {"critical", "high"}
        and (case := case_by_alert_id.get(alert.alert_id)) is not None
    ][:20]

    # Generate investigations, including a seeded short-duration cohort in CSE-04.
    reserved_investigation_cases = (
        cse2_target_cases
        + cse4_investigation_cases
        + cse6_mixed_cases
    )
    reserved_investigation_ids = {
        c.case_id for c in reserved_investigation_cases}
    investigation_cases = [
        c for c in cases if c.case_id not in reserved_investigation_ids]
    rng.shuffle(investigation_cases)
    investigation_candidates = reserved_investigation_cases + investigation_cases[
        : COUNTS["investigations"] - len(reserved_investigation_cases)
    ]
    investigations: list[Investigation] = []
    for investigation_index, case in enumerate(investigation_candidates, start=1):
        started_at = case.opened_at + timedelta(minutes=rng.randint(1, 90))
        is_cse4_short = case.cse_id == "CSE-04" and case in cse4_investigation_cases
        is_cse6_short = case.cse_id == "CSE-06" and case in cse6_mixed_cases[:5]
        is_seeded_short = is_cse4_short or is_cse6_short
        if is_seeded_short:
            duration = timedelta(seconds=rng.randint(30, 180))
        else:
            duration = timedelta(minutes=rng.randint(30, 900))
        ended_at = started_at + duration
        investigation = Investigation(
            investigation_id=f"INV-{investigation_index:05d}",
            case_id=case.case_id,
            started_at=started_at,
            ended_at=ended_at,
            analyst_id=f"ANL-{rng.randint(1, 120):03d}",
            evidence_count=max(0, int(rng.gauss(5.5, 3.0))),
        )
        investigations.append(investigation)

    # Escalation cases omit the selected critical CSE-02 cases on purpose.
    cse6_missing_escalation_cases = cse6_mixed_cases[:10]
    excluded_escalation_cases = {
        c.case_id for c in cse2_target_cases + cse6_missing_escalation_cases
    }
    escalation_candidates = [
        c for c in cases if c.case_id not in excluded_escalation_cases]
    rng.shuffle(escalation_candidates)
    escalation_cases = escalation_candidates[: COUNTS["escalations"]]
    escalations: list[Escalation] = []
    for escalation_index, case in enumerate(escalation_cases, start=1):
        escalated_at = case.opened_at + \
            timedelta(minutes=rng.randint(10, 1_440))
        if case.closed_at is not None and escalated_at > case.closed_at:
            escalated_at = case.closed_at
        escalations.append(
            Escalation(
                escalation_id=f"ESC-{escalation_index:04d}",
                case_id=case.case_id,
                escalation_type=_choose(
                    rng,
                    ("management", "specialist", "incident_response", "regulatory"),
                    (0.32, 0.28, 0.30, 0.10),
                ),
                escalated_at=escalated_at,
            )
        )

    # CSE-03 repeated-alert cases intentionally have no remediation evidence.
    no_remediation_cases = set(c.case_id for c in cse3_repeat_cases[:60])
    remediation_candidates = [
        c for c in cases if c.case_id not in no_remediation_cases]
    rng.shuffle(remediation_candidates)
    remediation_cases = remediation_candidates[: COUNTS["remediations"]]
    remediations: list[Remediation] = []
    for remediation_index, case in enumerate(remediation_cases, start=1):
        completed_at = None
        if rng.random() < 0.85:
            completed_at = case.opened_at + timedelta(days=rng.randint(1, 20))
            if case.closed_at is not None and completed_at > case.closed_at:
                completed_at = case.closed_at
        remediations.append(
            Remediation(
                remediation_id=f"REM-{remediation_index:04d}",
                case_id=case.case_id,
                action=rng.choice(
                    ("host isolated", "credentials reset",
                     "rule updated", "service restored", "patch applied")
                ),
                completed_at=completed_at,
            )
        )

    # CSE-05 negative-space ground truth uses asset IDs with markedly lower alert
    # activity than peer critical assets. Their zero alert count is intentional.
    truth_conditions = [
        {
            "condition_type": "missing_escalation",
            "cse_id": "CSE-02",
            "record_ids": sorted(c.case_id for c in cse2_target_cases),
            "description": "Selected high/critical alert cases have no escalation record.",
        },
        {
            "condition_type": "repeated_alerts_without_remediation",
            "cse_id": "CSE-03",
            "asset_ids": [a.asset_id for a in repeat_assets],
            "record_ids": sorted(c.case_id for c in cse3_repeat_cases[:60]),
            "description": "Repeated alerts on selected assets include cases without remediation records.",
        },
        {
            "condition_type": "unusually_short_investigation",
            "cse_id": "CSE-04",
            "record_ids": sorted(
                item.investigation_id
                for item in investigations
                if item.case_id in {c.case_id for c in cse4_investigation_cases}
            ),
            "description": "Selected investigations have durations well below the wider cohort.",
        },
        {
            "condition_type": "unusually_short_investigation",
            "cse_id": "CSE-06",
            "record_ids": sorted(
                item.investigation_id
                for item in investigations
                if item.case_id in {c.case_id for c in cse6_mixed_cases[:5]}
            ),
            "description": "A small short-investigation signal is mixed with otherwise varied activity.",
        },
        {
            "condition_type": "missing_escalation",
            "cse_id": "CSE-06",
            "record_ids": sorted(c.case_id for c in cse6_missing_escalation_cases),
            "description": "A small subset of cases has no escalation record amid mixed supervisory activity.",
        },
        {
            "condition_type": "negative_space_low_activity",
            "cse_id": "CSE-05",
            "asset_ids": [a.asset_id for a in low_activity_assets],
            "record_ids": [],
            "description": "Selected critical assets have no alerts while other critical assets have activity.",
        },
    ]
    ground_truth = {"seed": seed, "conditions": truth_conditions}
    dataset = SyntheticDataset(
        cse=cse_records,
        assets=assets,
        alerts=alerts,
        cases=cases,
        investigations=investigations,
        escalations=escalations,
        remediations=remediations,
        ground_truth=ground_truth,
        dataset_manifest={
            "format_version": 1,
            "seed": seed,
            "counts": {
                "cse": len(cse_records),
                "assets": len(assets),
                "alerts": len(alerts),
                "cases": len(cases),
                "investigations": len(investigations),
                "escalations": len(escalations),
                "remediations": len(remediations),
            },
            "ground_truth_file": "ground_truth.json",
            "operational_record_labeling": False,
        },
    )
    validate_dataset(dataset)
    return dataset


def validate_dataset(dataset: SyntheticDataset) -> None:
    """Check canonical model instances, references, IDs, chronology, and truth."""
    entity_lists = {
        "cse": dataset.cse,
        "assets": dataset.assets,
        "alerts": dataset.alerts,
        "cases": dataset.cases,
        "investigations": dataset.investigations,
        "escalations": dataset.escalations,
        "remediations": dataset.remediations,
    }
    id_fields = {
        "cse": "cse_id",
        "assets": "asset_id",
        "alerts": "alert_id",
        "cases": "case_id",
        "investigations": "investigation_id",
        "escalations": "escalation_id",
        "remediations": "remediation_id",
    }
    all_ids: set[str] = set()
    ids_by_type: dict[str, set[str]] = {}
    for entity_type, records in entity_lists.items():
        record_ids = [getattr(record, id_fields[entity_type])
                      for record in records]
        if len(record_ids) != len(set(record_ids)):
            raise ValueError(f"Duplicate {entity_type} identifiers")
        ids_by_type[entity_type] = set(record_ids)
        all_ids.update(record_ids)
        # Re-instantiation exercises the canonical model validation on every row.
        for record in records:
            type(record)(**asdict(record))
    if len(all_ids) != sum(len(records) for records in entity_lists.values()):
        raise ValueError("Entity identifiers must be globally unique")

    assets_by_id = {asset.asset_id: asset for asset in dataset.assets}
    alerts_by_id = {alert.alert_id: alert for alert in dataset.alerts}
    cases_by_id = {case.case_id: case for case in dataset.cases}
    investigations_by_id = {
        item.investigation_id: item for item in dataset.investigations}
    for asset in dataset.assets:
        if asset.cse_id not in ids_by_type["cse"]:
            raise ValueError(
                f"Asset {asset.asset_id} references an unknown CSE")
    for alert in dataset.alerts:
        asset = assets_by_id.get(alert.asset_id)
        if alert.cse_id not in ids_by_type["cse"] or asset is None or asset.cse_id != alert.cse_id:
            raise ValueError(
                f"Alert {alert.alert_id} has invalid CSE/asset references")
    for case in dataset.cases:
        alert = alerts_by_id.get(case.alert_id)
        if alert is None or alert.cse_id != case.cse_id or case.opened_at < alert.created_at:
            raise ValueError(
                f"Case {case.case_id} has invalid alert reference or chronology")
    for item in dataset.investigations:
        case = cases_by_id.get(item.case_id)
        if case is None or item.started_at < case.opened_at:
            raise ValueError(
                f"Investigation {item.investigation_id} has invalid case reference or chronology")
        if case.closed_at is not None and item.ended_at is not None and item.ended_at > case.closed_at:
            raise ValueError(
                f"Investigation {item.investigation_id} ends after its case closes")
    for item in dataset.escalations:
        case = cases_by_id.get(item.case_id)
        if case is None or item.escalated_at < case.opened_at:
            raise ValueError(
                f"Escalation {item.escalation_id} has invalid case reference or chronology")
    for item in dataset.remediations:
        case = cases_by_id.get(item.case_id)
        if case is None or (item.completed_at is not None and item.completed_at < case.opened_at):
            raise ValueError(
                f"Remediation {item.remediation_id} has invalid case reference or chronology")

    escalation_case_ids = {item.case_id for item in dataset.escalations}
    remediation_case_ids = {item.case_id for item in dataset.remediations}
    condition_types = {condition["condition_type"]
                       for condition in dataset.ground_truth["conditions"]}
    required_conditions = {
        "missing_escalation",
        "repeated_alerts_without_remediation",
        "unusually_short_investigation",
        "negative_space_low_activity",
    }

    if not required_conditions.issubset(condition_types):
        raise ValueError(
            "One or more required seeded ground-truth conditions are missing"
        )

    for condition in dataset.ground_truth["conditions"]:
        if condition["cse_id"] not in ids_by_type["cse"]:
            raise ValueError("Ground truth references an unknown CSE")

        for record_id in condition.get("record_ids", []):
            if record_id not in all_ids:
                raise ValueError(
                    f"Ground truth references unknown record {record_id}"
                )

        for asset_id in condition.get("asset_ids", []):
            if asset_id not in ids_by_type["assets"]:
                raise ValueError(
                    f"Ground truth references unknown asset {asset_id}"
                )

        if condition["condition_type"] == "missing_escalation":
            record_ids = condition["record_ids"]

            if not record_ids:
                raise ValueError(
                    "Seeded missing-escalation condition must identify cases"
                )

            if any(x not in cases_by_id for x in record_ids):
                raise ValueError(
                    "Missing-escalation ground truth references unknown cases"
                )

            if any(x in escalation_case_ids for x in record_ids):
                raise ValueError(
                    "Seeded missing-escalation cases must lack escalation records"
                )

            if any(
                cases_by_id[x].cse_id != condition["cse_id"]
                for x in record_ids
            ):
                raise ValueError(
                    "Missing-escalation cases must belong to the specified CSE"
                )

            alert_by_id = {
                item.alert_id: item for item in dataset.alerts
            }
            investigation_case_ids = {
                item.case_id for item in dataset.investigations
            }

            for case_id in record_ids:
                case = cases_by_id[case_id]
                alert = alert_by_id.get(case.alert_id)

                if alert is None or alert.severity not in {"high", "critical"}:
                    raise ValueError(
                        f"Missing-escalation case {case_id} must have a high/critical alert"
                    )

                if case_id not in investigation_case_ids:
                    raise ValueError(
                        f"Missing-escalation case {case_id} must have investigation evidence"
                    )

        elif condition["condition_type"] == "repeated_alerts_without_remediation":
            if not condition["asset_ids"] or not condition["record_ids"]:
                raise ValueError(
                    "Repeated-alert condition must identify assets and cases"
                )
            if any(x in remediation_case_ids for x in condition["record_ids"]):
                raise ValueError(
                    "Seeded repeated-alert cases must lack remediation records"
                )

        elif condition["condition_type"] == "unusually_short_investigation":
            if not condition["record_ids"] or any(
                x not in investigations_by_id for x in condition["record_ids"]
            ):
                raise ValueError(
                    "Short-investigation ground truth must reference investigations"
                )
            if any(
                investigations_by_id[x].ended_at is None
                or investigations_by_id[x].ended_at
                - investigations_by_id[x].started_at > timedelta(minutes=5)
                for x in condition["record_ids"]
            ):
                raise ValueError(
                    "Seeded short investigations must remain under five minutes"
                )

        elif condition["condition_type"] == "negative_space_low_activity":
            asset_ids = condition["asset_ids"]
            if not asset_ids or any(
                len([a for a in dataset.alerts if a.asset_id == x]) > 1
                for x in asset_ids
            ):
                raise ValueError(
                    "Negative-space assets must have very low activity"
                )

        if condition["condition_type"] == "missing_escalation":
            # Your new validation block goes here, indented at this level.
            ...
        if condition["condition_type"] == "missing_escalation":
            if not condition["record_ids"] or any(x in escalation_case_ids for x in condition["record_ids"]):
                raise ValueError(
                    "Seeded missing-escalation cases must lack escalation records")
        elif condition["condition_type"] == "repeated_alerts_without_remediation":
            if not condition["asset_ids"] or not condition["record_ids"]:
                raise ValueError(
                    "Repeated-alert condition must identify assets and cases")
            if any(x in remediation_case_ids for x in condition["record_ids"]):
                raise ValueError(
                    "Seeded repeated-alert cases must lack remediation records")
        elif condition["condition_type"] == "unusually_short_investigation":
            if not condition["record_ids"] or any(x not in investigations_by_id for x in condition["record_ids"]):
                raise ValueError(
                    "Short-investigation ground truth must reference investigations")
            if any(
                investigations_by_id[x].ended_at is None
                or investigations_by_id[x].ended_at - investigations_by_id[x].started_at > timedelta(minutes=5)
                for x in condition["record_ids"]
            ):
                raise ValueError(
                    "Seeded short investigations must remain under five minutes")
        elif condition["condition_type"] == "negative_space_low_activity":
            asset_ids = condition["asset_ids"]
            if not asset_ids or any(len([a for a in dataset.alerts if a.asset_id == x]) > 1 for x in asset_ids):
                raise ValueError(
                    "Negative-space assets must have very low activity")


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2,
                    ensure_ascii=False) + "\n", encoding="utf-8")


def write_dataset(dataset: SyntheticDataset, output_dir: Path | str = DEFAULT_OUTPUT_DIR) -> Path:
    """Validate and write all operational, ground-truth, and manifest files."""
    validate_dataset(dataset)
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    payloads = {
        "cse.json": [_record_dict(x) for x in dataset.cse],
        "assets.json": [_record_dict(x) for x in dataset.assets],
        "alerts.json": [_record_dict(x) for x in dataset.alerts],
        "cases.json": [_record_dict(x) for x in dataset.cases],
        "investigations.json": [_record_dict(x) for x in dataset.investigations],
        "escalations.json": [_record_dict(x) for x in dataset.escalations],
        "remediations.json": [_record_dict(x) for x in dataset.remediations],
        "ground_truth.json": dataset.ground_truth,
        "dataset_manifest.json": dataset.dataset_manifest,
    }
    for filename, payload in payloads.items():
        _write_json(destination / filename, payload)
    missing = [filename for filename in OUTPUT_FILES if not (
        destination / filename).is_file()]
    if missing:
        raise OSError(
            f"Generator failed to create expected output files: {missing}")
    return destination


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42,
                        help="fixed integer random seed (default: 42)")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="output directory (default: data/synthetic/golden_dataset)",
    )
    args = parser.parse_args(argv)
    dataset = generate_dataset(args.seed)
    output_dir = write_dataset(dataset, args.output_dir)
    print(f"Generated deterministic dataset at {output_dir}")
    print(json.dumps(dataset.dataset_manifest["counts"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
