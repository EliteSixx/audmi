"""Deterministic synthetic SOC evidence dataset generator for AudMi.

Run from the repository root with ``python data/synthetic/generator.py --seed 42``.
Operational files contain no planted-condition labels; those are written only to
the separate ground-truth file.

Generator v2 goals (see ``docs/TEAM_PLAN.md`` §3, W2):
* realistic escalation baselines (~80% of high/critical cases, one weak CSE)
* overlapping investigation-duration distributions, plus legitimate fast decoys
* repeated-alert assets that *do* have remediation, so the rule must not flag them
* four quarters of activity, sectors and peer groups
"""

from __future__ import annotations

import argparse
import json
import math
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
PERIOD_DAYS = 365
PERIODS = ("2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4")
COUNTS = {
    "cse": 6,
    "assets": 300,
    "alerts": 10_000,
    "cases": 2_000,
    "investigations": 1_500,
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
ELEVATED_SEVERITY_WEIGHTS = (0.02, 0.08, 0.34, 0.34, 0.22)
CATEGORIES = ("malware", "intrusion", "policy",
              "availability", "identity", "network")
ASSET_TYPES = ("server", "workstation", "network_device",
               "database", "security_appliance")

# cse_id, display name, sector, peer group, alert volume
CSE_PROFILES = (
    ("CSE-01", "Energy Sector Cyber Security Entity 01", "energy",
     "energy-large", 1_700),
    ("CSE-02", "Banking Sector Cyber Security Entity 02", "banking",
     "banking-critical", 1_700),
    ("CSE-03", "Telecom Sector Cyber Security Entity 03", "telecom",
     "communications-critical", 1_700),
    ("CSE-04", "Energy Sector Cyber Security Entity 04", "energy",
     "energy-large", 1_700),
    ("CSE-05", "Transport Sector Cyber Security Entity 05", "transport",
     "communications-critical", 1_550),
    ("CSE-06", "Banking Sector Cyber Security Entity 06", "banking",
     "banking-critical", 1_650),
)

# Escalation probability for high/critical cases. CSE-02 is the weak entity.
ESCALATION_RATE_HIGH = 0.80
ESCALATION_RATE_WEAK = 0.50
ESCALATION_RATE_MEDIUM = 0.15
ESCALATION_RATE_LOW = 0.03
ESCALATION_RATE_INFO = 0.01

NORMAL_DURATION_MEDIAN_SECONDS = 4 * 60 * 60
NORMAL_DURATION_SIGMA = 0.85
DECOY_FAST_SECONDS = (180, 720)
SEEDED_SHORT_SECONDS = (120, 290)


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


def _take(rng: random.Random, values: list[Any], count: int) -> list[Any]:
    """Shuffle a copy and take ``count`` items (deterministic for a seed)."""
    pool = list(values)
    rng.shuffle(pool)
    return pool[:count]


def _escalation_probability(cse_id: str, severity: str) -> float:
    if severity in {"high", "critical"}:
        return ESCALATION_RATE_WEAK if cse_id == "CSE-02" else ESCALATION_RATE_HIGH
    if severity == "medium":
        return ESCALATION_RATE_MEDIUM
    if severity == "low":
        return ESCALATION_RATE_LOW
    return ESCALATION_RATE_INFO


def _normal_duration(rng: random.Random) -> timedelta:
    seconds = rng.lognormvariate(
        math.log(NORMAL_DURATION_MEDIAN_SECONDS), NORMAL_DURATION_SIGMA
    )
    return timedelta(seconds=max(300.0, min(seconds, 7 * 86_400.0)))


def generate_dataset(seed: int = 42) -> SyntheticDataset:
    """Build all dataset records in memory, validate them, and return them."""
    rng = random.Random(seed)

    cse_records = [
        CSE(cse_id, name, peer_group)
        for cse_id, name, _sector, peer_group, _alerts in CSE_PROFILES
    ]
    sectors = {cse_id: sector for cse_id, _name, sector, _peer, _alerts in CSE_PROFILES}
    alert_volumes = {cse_id: volume for cse_id, _n, _s, _p, volume in CSE_PROFILES}

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

    # CSE-03: high-volume assets. Eight have no remediation; six look identical
    # in volume but *are* remediated, so they act as decoys for the rule.
    repeat_assets = critical_assets_by_cse["CSE-03"][:8]
    decoy_repeat_assets = assets_by_cse["CSE-03"][10:16]
    # CSE-05: critical assets that produce no alerts at all (negative space).
    low_activity_assets = critical_assets_by_cse["CSE-05"][:8]
    low_activity_ids = {asset.asset_id for asset in low_activity_assets}

    alerts: list[Alert] = []
    alerts_by_cse: dict[str, list[Alert]] = defaultdict(list)
    alerts_by_asset: dict[str, list[Alert]] = defaultdict(list)
    alert_index = 0
    for cse in cse_records:
        cse_number = int(cse.cse_id[-2:])
        cse_count = alert_volumes[cse.cse_id]
        regular_assets = [a for a in assets_by_cse[cse.cse_id]
                          if a.asset_id not in low_activity_ids]
        for local_alert_index in range(cse_count):
            alert_index += 1
            if cse_number == 3 and local_alert_index < 420:
                asset = repeat_assets[local_alert_index % len(repeat_assets)]
            elif cse_number == 3 and local_alert_index < 720:
                asset = decoy_repeat_assets[
                    (local_alert_index - 420) % len(decoy_repeat_assets)
                ]
            else:
                asset = rng.choice(regular_assets)

            severity_weights = SEVERITY_WEIGHTS
            if cse_number == 2:
                severity_weights = ELEVATED_SEVERITY_WEIGHTS
            elif cse_number == 3 and asset in repeat_assets + decoy_repeat_assets:
                severity_weights = ELEVATED_SEVERITY_WEIGHTS
            severity = _choose(rng, SEVERITIES, severity_weights)
            created_at = BASE_TIME + timedelta(
                days=rng.randint(0, PERIOD_DAYS - 1),
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

    alert_by_id = {alert.alert_id: alert for alert in alerts}

    cse2_hc_alerts = [
        a for a in alerts_by_cse["CSE-02"] if a.severity in {"critical", "high"}
    ]
    cse6_hc_alerts = [
        a for a in alerts_by_cse["CSE-06"] if a.severity in {"critical", "high"}
    ]
    repeat_alerts = [a for a in alerts if a.asset_id in {
        x.asset_id for x in repeat_assets}]
    decoy_repeat_alerts = [a for a in alerts if a.asset_id in {
        x.asset_id for x in decoy_repeat_assets}]

    cse2_forced_alerts = _take(rng, cse2_hc_alerts, 170)
    repeat_forced_alerts = _take(rng, repeat_alerts, 160)
    decoy_forced_alerts = _take(rng, decoy_repeat_alerts, 180)
    cse4_forced_alerts = _take(rng, list(alerts_by_cse["CSE-04"]), 120)
    cse6_forced_alerts = _take(rng, cse6_hc_alerts, 20)
    forced_alerts = (
        cse2_forced_alerts
        + repeat_forced_alerts
        + decoy_forced_alerts
        + cse4_forced_alerts
        + cse6_forced_alerts
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

    def cases_for(alerts: list[Alert]) -> list[Case]:
        return [case_by_alert_id[a.alert_id]
                for a in alerts if a.alert_id in case_by_alert_id]

    cse2_target_cases = cases_for(cse2_forced_alerts)
    cse3_repeat_cases = cases_for(repeat_forced_alerts)
    cse3_decoy_cases = cases_for(decoy_forced_alerts)
    cse4_cohort_cases = cases_for(cse4_forced_alerts)
    cse6_mixed_cases = cases_for(cse6_forced_alerts)

    # 60 CSE-02 cases and 10 CSE-06 cases are planted with no escalation.
    rng.shuffle(cse2_target_cases)
    cse2_missing_escalation_cases = cse2_target_cases[:60]
    cse6_missing_escalation_cases = cse6_mixed_cases[:10]
    missing_escalation_case_ids = {
        c.case_id
        for c in cse2_missing_escalation_cases + cse6_missing_escalation_cases
    }

    # 100 CSE-04 investigations and 5 CSE-06 investigations are planted short.
    cse4_short_cases = cse4_cohort_cases[:100]
    cse6_short_cases = cse6_mixed_cases[:5]
    short_case_ids = {c.case_id for c in cse4_short_cases + cse6_short_cases}

    reserved_investigation_cases = (
        cse2_target_cases + cse4_cohort_cases + cse6_mixed_cases
    )
    reserved_ids = {c.case_id for c in reserved_investigation_cases}
    other_cases = [c for c in cases if c.case_id not in reserved_ids]
    rng.shuffle(other_cases)
    # Legitimate automated/playbook investigations: fast but not planted.
    decoy_fast_cases = other_cases[:40]
    decoy_fast_ids = {c.case_id for c in decoy_fast_cases}
    investigation_cases = (
        reserved_investigation_cases
        + decoy_fast_cases
        + other_cases[40: COUNTS["investigations"] - len(reserved_investigation_cases)]
    )
    investigation_cases = investigation_cases[: COUNTS["investigations"]]

    investigations: list[Investigation] = []
    for investigation_index, case in enumerate(investigation_cases, start=1):
        started_at = case.opened_at + timedelta(minutes=rng.randint(1, 90))
        if case.case_id in short_case_ids:
            duration = timedelta(seconds=rng.randint(*SEEDED_SHORT_SECONDS))
        elif case.case_id in decoy_fast_ids:
            duration = timedelta(seconds=rng.randint(*DECOY_FAST_SECONDS))
        else:
            duration = _normal_duration(rng)
        ended_at = started_at + duration
        if case.closed_at is not None and ended_at > case.closed_at:
            ended_at = case.closed_at
        investigations.append(
            Investigation(
                investigation_id=f"INV-{investigation_index:05d}",
                case_id=case.case_id,
                started_at=started_at,
                ended_at=ended_at,
                analyst_id=f"ANL-{rng.randint(1, 120):03d}",
                evidence_count=max(0, int(rng.gauss(5.5, 3.0))),
            )
        )

    # Escalations follow a realistic per-entity baseline, except the planted
    # cases and the intentionally weak CSE-02.
    escalations: list[Escalation] = []
    escalation_index = 0
    for case in cases:
        if case.case_id in missing_escalation_case_ids:
            continue
        alert = alert_by_id[case.alert_id]
        if rng.random() >= _escalation_probability(case.cse_id, alert.severity):
            continue
        escalation_index += 1
        escalated_at = case.opened_at + timedelta(
            minutes=rng.randint(10, 1_440)
        )
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

    # CSE-03 repeat-alert cases have no remediation. The volume-matched decoy
    # assets have remediation on every case, so they must not be flagged.
    no_remediation_case_ids = {c.case_id for c in cse3_repeat_cases}
    decoy_remediated_case_ids = {c.case_id for c in cse3_decoy_cases}
    remediation_candidates = [
        c for c in cases
        if c.case_id not in no_remediation_case_ids
        and c.case_id not in decoy_remediated_case_ids
        and c.closed_at is not None
    ]
    rng.shuffle(remediation_candidates)
    remediation_cases = (
        cse3_decoy_cases
        + remediation_candidates[: max(0, 260 - len(cse3_decoy_cases))]
    )
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

    escalation_case_ids = {item.case_id for item in escalations}
    escalation_rates = {}
    for cse in cse_records:
        hc = [c for c in cases_by_cse[cse.cse_id]
              if alert_by_id[c.alert_id].severity in {"high", "critical"}
              and c.case_id not in missing_escalation_case_ids]
        escalated = sum(1 for c in hc if c.case_id in escalation_case_ids)
        escalation_rates[cse.cse_id] = round(escalated / len(hc), 4) if hc else None

    truth_conditions = [
        {
            "condition_type": "missing_escalation",
            "cse_id": "CSE-02",
            "record_ids": sorted(c.case_id for c in cse2_missing_escalation_cases),
            "description": "Selected high/critical cases have no escalation record.",
        },
        {
            "condition_type": "repeated_alerts_without_remediation",
            "cse_id": "CSE-03",
            "asset_ids": [a.asset_id for a in repeat_assets],
            "record_ids": sorted(c.case_id for c in cse3_repeat_cases),
            "description": "High-volume assets have repeated cases with no remediation records.",
        },
        {
            "condition_type": "unusually_short_investigation",
            "cse_id": "CSE-04",
            "record_ids": sorted(
                item.investigation_id
                for item in investigations
                if item.case_id in {c.case_id for c in cse4_short_cases}
            ),
            "description": "Selected investigations are far below the wider cohort.",
        },
        {
            "condition_type": "unusually_short_investigation",
            "cse_id": "CSE-06",
            "record_ids": sorted(
                item.investigation_id
                for item in investigations
                if item.case_id in {c.case_id for c in cse6_short_cases}
            ),
            "description": "A small short-investigation signal is mixed with varied activity.",
        },
        {
            "condition_type": "missing_escalation",
            "cse_id": "CSE-06",
            "record_ids": sorted(c.case_id for c in cse6_missing_escalation_cases),
            "description": "A small subset of cases has no escalation record amid mixed activity.",
        },
        {
            "condition_type": "negative_space_low_activity",
            "cse_id": "CSE-05",
            "asset_ids": [a.asset_id for a in low_activity_assets],
            "record_ids": [],
            "description": "Selected critical assets have no alerts while peers have activity.",
        },
    ]
    ground_truth = {
        "seed": seed,
        "generator_version": "2.0.0",
        "periods": list(PERIODS),
        "conditions": truth_conditions,
    }
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
            "format_version": 2,
            "generator_version": "2.0.0",
            "seed": seed,
            "periods": list(PERIODS),
            "sectors": sectors,
            "peer_groups": {c.cse_id: c.peer_group for c in cse_records},
            "counts": {
                "cse": len(cse_records),
                "assets": len(assets),
                "alerts": len(alerts),
                "cases": len(cases),
                "investigations": len(investigations),
                "escalations": len(escalations),
                "remediations": len(remediations),
            },
            "high_critical_escalation_rates": escalation_rates,
            "ground_truth_file": "ground_truth.json",
            "operational_record_labeling": False,
        },
    )
    validate_dataset(dataset)
    return dataset


def validate_dataset(dataset: SyntheticDataset) -> None:
    """Check canonical models, references, chronology, and seeded truth."""
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
    investigation_case_ids = {item.case_id for item in dataset.investigations}
    alert_count_by_asset: dict[str, int] = defaultdict(int)
    for alert in dataset.alerts:
        alert_count_by_asset[alert.asset_id] += 1
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
                    f"Ground truth references unknown record {record_id}")
        for asset_id in condition.get("asset_ids", []):
            if asset_id not in ids_by_type["assets"]:
                raise ValueError(
                    f"Ground truth references unknown asset {asset_id}")

        kind = condition["condition_type"]
        if kind == "missing_escalation":
            record_ids = condition["record_ids"]
            if not record_ids:
                raise ValueError(
                    "Seeded missing-escalation condition must identify cases")
            if any(x not in cases_by_id for x in record_ids):
                raise ValueError(
                    "Missing-escalation ground truth references unknown cases")
            if any(x in escalation_case_ids for x in record_ids):
                raise ValueError(
                    "Seeded missing-escalation cases must lack escalation records")
            if any(cases_by_id[x].cse_id != condition["cse_id"] for x in record_ids):
                raise ValueError(
                    "Missing-escalation cases must belong to the specified CSE")
            for case_id in record_ids:
                alert = alerts_by_id[cases_by_id[case_id].alert_id]
                if alert.severity not in {"high", "critical"}:
                    raise ValueError(
                        f"Missing-escalation case {case_id} must have a high/critical alert")
                if case_id not in investigation_case_ids:
                    raise ValueError(
                        f"Missing-escalation case {case_id} must have investigation evidence")
        elif kind == "repeated_alerts_without_remediation":
            if not condition["asset_ids"] or not condition["record_ids"]:
                raise ValueError(
                    "Repeated-alert condition must identify assets and cases")
            if any(x in remediation_case_ids for x in condition["record_ids"]):
                raise ValueError(
                    "Seeded repeated-alert cases must lack remediation records")
        elif kind == "unusually_short_investigation":
            if not condition["record_ids"] or any(
                x not in investigations_by_id for x in condition["record_ids"]
            ):
                raise ValueError(
                    "Short-investigation ground truth must reference investigations")
            if any(
                investigations_by_id[x].ended_at is None
                or investigations_by_id[x].ended_at
                - investigations_by_id[x].started_at > timedelta(minutes=5)
                for x in condition["record_ids"]
            ):
                raise ValueError(
                    "Seeded short investigations must remain under five minutes")
        elif kind == "negative_space_low_activity":
            if not condition["asset_ids"] or any(
                alert_count_by_asset.get(x, 0) > 1 for x in condition["asset_ids"]
            ):
                raise ValueError(
                    "Negative-space assets must have very low activity")

    # Decoy checks: volume-matched assets with remediation must not look like
    # the un-remediated repeated-alert cohort.
    seeded_repeat_assets = {
        asset_id
        for condition in dataset.ground_truth["conditions"]
        if condition["condition_type"] == "repeated_alerts_without_remediation"
        for asset_id in condition["asset_ids"]
    }
    decoy_assets = [a for a in dataset.assets
                    if a.cse_id == "CSE-03" and a.asset_id not in seeded_repeat_assets]
    decoy_cases: dict[str, list[str]] = defaultdict(list)
    for case in dataset.cases:
        asset_id = alerts_by_id[case.alert_id].asset_id
        if asset_id in {a.asset_id for a in decoy_assets}:
            decoy_cases[asset_id].append(case.case_id)
    for asset in decoy_assets:
        cases = decoy_cases.get(asset.asset_id, [])
        if len(cases) >= 3:
            covered = sum(1 for x in cases if x in remediation_case_ids)
            if covered / len(cases) <= 0.10:
                # Only the deliberately volume-matched decoys need coverage.
                if alert_count_by_asset.get(asset.asset_id, 0) > 40:
                    raise ValueError(
                        "Volume-matched decoy assets must have remediation coverage")


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
