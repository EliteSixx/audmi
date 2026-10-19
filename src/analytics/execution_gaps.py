"""Explainable execution-gap signals over AudMi's canonical evidence records.

Signals are potential supervisory indicators only. They are not compliance
judgments and require review by a human examiner.

Thresholds are not defined here: each rule reads its parameters from
``rules/<rule_id>.yaml`` through the rule registry, and every finding records
the rule id and version that produced it.
"""

from __future__ import annotations

import json
import math
import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable, TypeVar

from src.core.findings import Finding
from src.core.registry import Rule, RuleRegistry, load_registry
from src.normalization.evidence_model import (
    Alert,
    Asset,
    Case,
    CSE,
    Escalation,
    Investigation,
    Remediation,
)


DEFAULT_DATASET_DIR = (
    Path(__file__).resolve().parents[2] / "data" / "synthetic" / "golden_dataset"
)

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class EvidenceRecords:
    cse: tuple[CSE, ...]
    assets: tuple[Asset, ...]
    alerts: tuple[Alert, ...]
    cases: tuple[Case, ...]
    investigations: tuple[Investigation, ...] = ()
    escalations: tuple[Escalation, ...] = ()
    remediations: tuple[Remediation, ...] = ()


def _new_finding(rule: Rule, *, finding_id: str, cse_id: str, subject_id: str,
                 reason: str, supporting_record_ids: tuple[str, ...],
                 baseline: dict[str, Any],
                 data_quality_notes: tuple[str, ...] = ()) -> Finding:
    """Build a Finding whose rule metadata comes from the registry entry."""
    return Finding(
        finding_id=finding_id,
        rule_id=rule.id,
        rule_version=rule.version,
        capability=rule.capability,
        category=rule.category,
        cse_id=cse_id,
        subject_type=rule.subject_type,
        subject_id=subject_id,
        reason=reason,
        supporting_record_ids=supporting_record_ids,
        baseline=baseline,
        data_quality_notes=data_quality_notes,
    )


def _parse_timestamp_fields(row: dict[str, Any], names: Iterable[str]) -> dict[str, Any]:
    parsed = dict(row)
    for name in names:
        value = parsed.get(name)
        if isinstance(value, str):
            parsed[name] = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed


def _read_model_records(
    dataset_dir: Path,
    filename: str,
    model: type[T],
    timestamp_fields: tuple[str, ...] = (),
    *,
    optional: bool = False,
) -> tuple[T, ...]:
    path = dataset_dir / filename
    if not path.exists():
        if optional:
            return ()
        raise FileNotFoundError(f"Required evidence file is missing: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        if optional:
            return ()
        raise ValueError(f"Could not read required evidence file: {path}") from None
    if not isinstance(raw, list):
        if optional:
            return ()
        raise ValueError(f"Evidence file must contain a JSON array: {path}")

    records: list[T] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        try:
            records.append(model(**_parse_timestamp_fields(row, timestamp_fields)))
        except (KeyError, TypeError, ValueError):
            # A malformed optional workflow row cannot invalidate other records.
            continue
    return tuple(records)


def load_evidence(dataset_dir: str | Path = DEFAULT_DATASET_DIR) -> EvidenceRecords:
    """Load canonical JSON evidence; absent or malformed workflow files are empty."""
    root = Path(dataset_dir)
    return EvidenceRecords(
        cse=_read_model_records(root, "cse.json", CSE),
        assets=_read_model_records(root, "assets.json", Asset),
        alerts=_read_model_records(
            root, "alerts.json", Alert, ("created_at", "closed_at")
        ),
        cases=_read_model_records(root, "cases.json", Case, ("opened_at", "closed_at")),
        investigations=_read_model_records(
            root,
            "investigations.json",
            Investigation,
            ("started_at", "ended_at"),
            optional=True,
        ),
        escalations=_read_model_records(
            root, "escalations.json", Escalation, ("escalated_at",), optional=True
        ),
        remediations=_read_model_records(
            root, "remediations.json", Remediation, ("completed_at",), optional=True
        ),
    )


def _median_absolute_deviation(values: list[float]) -> tuple[float, float]:
    median = statistics.median(values)
    mad = statistics.median(abs(value - median) for value in values)
    return median, mad


def _duration_baseline(
    investigations: tuple[Investigation, ...], rule: Rule
) -> tuple[float, dict[str, Any]] | None:
    sigma_multiplier = rule.param("sigma_multiplier")
    mad_scale = rule.param("mad_scale")
    durations = [
        (item.ended_at - item.started_at).total_seconds()
        for item in investigations
        if item.ended_at is not None
        and item.ended_at > item.started_at
    ]
    if len(durations) < rule.param("min_baseline_size"):
        return None

    # Log duration makes multiplicative differences comparable. The lower
    # robust fence is derived from the cohort's median and MAD, not a fixed time.
    log_durations = [math.log(value) for value in durations]
    log_median, log_mad = _median_absolute_deviation(log_durations)
    robust_sigma = mad_scale * log_mad
    lower_log_fence = log_median - sigma_multiplier * robust_sigma
    threshold_seconds = math.exp(lower_log_fence)
    baseline = {
        "method": (
            f"lower robust fence on log duration: median - {sigma_multiplier} "
            f"* {mad_scale} * MAD"
        ),
        "population": "all completed investigations in the supplied evidence",
        "sample_count": len(durations),
        "geometric_median_seconds": round(math.exp(log_median), 3),
        "log_duration_mad": round(log_mad, 6),
        "sigma_multiplier": sigma_multiplier,
        "lower_threshold_seconds": round(threshold_seconds, 3),
    }
    return threshold_seconds, baseline


def find_missing_escalations(records: EvidenceRecords, rule: Rule) -> list[Finding]:
    required_severities = set(rule.param("escalation_required_severities"))
    require_investigation = bool(rule.param("require_investigation"))
    alerts = {item.alert_id: item for item in records.alerts}
    investigations_by_case: dict[str, list[Investigation]] = defaultdict(list)
    for item in records.investigations:
        investigations_by_case[item.case_id].append(item)
    escalated_cases = {item.case_id for item in records.escalations}

    findings: list[Finding] = []
    for case in records.cases:
        alert = alerts.get(case.alert_id)
        investigations = investigations_by_case.get(case.case_id, [])
        if (
            alert is None
            or case.cse_id != alert.cse_id
            or alert.severity not in required_severities
            or (require_investigation and not investigations)
            or case.case_id in escalated_cases
        ):
            continue
        supporting = (case.case_id, alert.alert_id) + tuple(
            item.investigation_id
            for item in sorted(investigations, key=lambda value: value.investigation_id)
        )
        findings.append(
            _new_finding(
                rule,
                finding_id=f"EXG-MISSING-ESCALATION-{case.case_id}",
                cse_id=case.cse_id,
                subject_id=case.case_id,
                reason=(
                    "Potential execution gap: high-severity case has investigation "
                    "evidence but no corresponding escalation record."
                ),
                supporting_record_ids=supporting,
                baseline={
                    "expectation": "an escalation record exists for this case",
                    "escalation_required_severities": sorted(required_severities),
                    "observed_alert_severity": alert.severity,
                    "observed_investigation_count": len(investigations),
                    "observed_escalation_count": 0,
                },
                data_quality_notes=(
                    "No escalation record was found in the submission; the "
                    "escalation may exist outside the submitted evidence.",
                ),
            )
        )
    return findings


def find_short_investigations(records: EvidenceRecords, rule: Rule) -> list[Finding]:
    computed = _duration_baseline(records.investigations, rule)
    if computed is None:
        return []
    threshold_seconds, shared_baseline = computed
    cases = {item.case_id: item for item in records.cases}
    alerts = {item.alert_id: item for item in records.alerts}

    findings: list[Finding] = []
    for investigation in records.investigations:
        if investigation.ended_at is None:
            continue
        duration = (investigation.ended_at - investigation.started_at).total_seconds()
        case = cases.get(investigation.case_id)
        alert = alerts.get(case.alert_id) if case is not None else None
        if case is None or alert is None or case.cse_id != alert.cse_id:
            continue
        if duration >= threshold_seconds:
            continue
        supporting = (investigation.investigation_id, case.case_id, alert.alert_id)
        baseline = dict(shared_baseline)
        baseline["observed_duration_seconds"] = round(duration, 3)
        baseline["observed_alert_severity"] = alert.severity
        findings.append(
            _new_finding(
                rule,
                finding_id=f"EXG-SHORT-INVESTIGATION-{investigation.investigation_id}",
                cse_id=case.cse_id,
                subject_id=investigation.investigation_id,
                reason=(
                    "Potential execution gap: investigation duration is substantially "
                    "below the observed contextual baseline."
                ),
                supporting_record_ids=supporting,
                baseline=baseline,
            )
        )
    return findings


def find_repeated_alerts_without_remediation(
    records: EvidenceRecords, rule: Rule
) -> list[Finding]:
    sigma_multiplier = rule.param("sigma_multiplier")
    mad_scale = rule.param("mad_scale")
    min_multiple = rule.param("min_multiple_of_median")
    min_cases = rule.param("min_case_count")
    max_coverage = rule.param("max_remediation_coverage")
    min_assets = rule.param("min_assets_per_cse")

    assets_by_id = {item.asset_id: item for item in records.assets}
    alerts_by_id = {item.alert_id: item for item in records.alerts}
    alerts_by_asset: dict[str, list[Alert]] = defaultdict(list)
    assets_by_cse: dict[str, list[Asset]] = defaultdict(list)
    for asset in records.assets:
        assets_by_cse[asset.cse_id].append(asset)
    for alert in records.alerts:
        asset = assets_by_id.get(alert.asset_id)
        if asset is None or asset.cse_id != alert.cse_id:
            continue
        alerts_by_asset[asset.asset_id].append(alert)

    cases_by_asset: dict[str, list[Case]] = defaultdict(list)
    for case in records.cases:
        alert = alerts_by_id.get(case.alert_id)
        if alert is None or alert.cse_id != case.cse_id:
            continue
        cases_by_asset[alert.asset_id].append(case)
    remediations_by_case: dict[str, list[Remediation]] = defaultdict(list)
    for item in records.remediations:
        remediations_by_case[item.case_id].append(item)

    upper_fences: dict[str, tuple[float, float, float]] = {}
    for cse_id, assets in assets_by_cse.items():
        counts = [float(len(alerts_by_asset[asset.asset_id])) for asset in assets]
        if len(counts) < min_assets:
            continue
        median, mad = _median_absolute_deviation(counts)
        statistical_fence = median + sigma_multiplier * mad_scale * mad
        # Require both a robust upper-tail outlier and a minimum multiple of the
        # CSE's typical asset volume, reducing flags from ordinary count variation.
        upper_fences[cse_id] = (max(statistical_fence, median * min_multiple), median, mad)

    findings: list[Finding] = []
    for asset in sorted(records.assets, key=lambda value: value.asset_id):
        fence_data = upper_fences.get(asset.cse_id)
        if fence_data is None:
            continue
        upper_fence, median_count, mad_count = fence_data
        asset_alerts = sorted(alerts_by_asset[asset.asset_id], key=lambda value: value.alert_id)
        asset_cases = sorted(cases_by_asset[asset.asset_id], key=lambda value: value.case_id)
        if len(asset_alerts) <= upper_fence or len(asset_cases) < min_cases:
            continue

        covered_cases = [case for case in asset_cases if remediations_by_case.get(case.case_id)]
        coverage = len(covered_cases) / len(asset_cases)
        if coverage > max_coverage:
            continue

        remediation_records = sorted(
            (item for case in asset_cases for item in remediations_by_case.get(case.case_id, [])),
            key=lambda value: value.remediation_id,
        )
        alert_ids = tuple(item.alert_id for item in asset_alerts)
        case_ids = tuple(item.case_id for item in asset_cases)
        remediation_ids = tuple(item.remediation_id for item in remediation_records)
        supporting = (asset.asset_id,) + alert_ids + case_ids + remediation_ids
        baseline = {
            "alert_count_method": (
                f"per-CSE median + {sigma_multiplier} * {mad_scale} * MAD across assets"
            ),
            "asset_alert_count_median": median_count,
            "asset_alert_count_mad": mad_count,
            "repeated_alert_upper_fence": round(upper_fence, 3),
            "minimum_multiple_of_cse_median": min_multiple,
            "observed_alert_count": len(asset_alerts),
            "minimum_case_count": min_cases,
            "observed_case_count": len(asset_cases),
            "observed_remediation_count": len(remediation_ids),
            "remediation_coverage": round(coverage, 4),
            "maximum_coverage_for_signal": max_coverage,
        }
        findings.append(
            _new_finding(
                rule,
                finding_id=f"EXG-REPEATED-LOW-REMEDIATION-{asset.asset_id}",
                cse_id=asset.cse_id,
                subject_id=asset.asset_id,
                reason=(
                    "Potential execution gap: this asset has alert volume above the "
                    "CSE's robust asset-level baseline, while remediation evidence "
                    f"covers no more than {max_coverage:.0%} of its associated cases."
                ),
                supporting_record_ids=supporting,
                baseline=baseline,
                data_quality_notes=(
                    "Remediation coverage counts only remediation records in the "
                    "submission; remediation tracked elsewhere is not visible.",
                ),
            )
        )
    return findings


RuleFunction = Callable[[EvidenceRecords, Rule], list[Finding]]

# Maps a registry rule id to the Python function that evaluates it.
RULE_FUNCTIONS: dict[str, RuleFunction] = {
    "missing_escalation": find_missing_escalations,
    "unusually_short_investigation": find_short_investigations,
    "repeated_alerts_without_remediation": find_repeated_alerts_without_remediation,
}


def _clean_records(records: EvidenceRecords) -> EvidenceRecords:
    # Keep valid canonical records and tolerate missing or malformed optional
    # workflow entries in partial hand-built inputs.
    return EvidenceRecords(
        cse=tuple(item for item in (records.cse or ()) if isinstance(item, CSE)),
        assets=tuple(item for item in (records.assets or ()) if isinstance(item, Asset)),
        alerts=tuple(item for item in (records.alerts or ()) if isinstance(item, Alert)),
        cases=tuple(item for item in (records.cases or ()) if isinstance(item, Case)),
        investigations=tuple(
            item for item in (records.investigations or ()) if isinstance(item, Investigation)
        ),
        escalations=tuple(
            item for item in (records.escalations or ()) if isinstance(item, Escalation)
        ),
        remediations=tuple(
            item for item in (records.remediations or ()) if isinstance(item, Remediation)
        ),
    )


def analyze_evidence(
    records: EvidenceRecords, registry: RuleRegistry | None = None
) -> list[Finding]:
    """Return stable, evidence-backed execution-gap findings for supplied records.

    Only rules that are both in the registry and implemented in RULE_FUNCTIONS
    run, so removing a rule's YAML file switches that rule off.
    """
    registry = registry if registry is not None else load_registry()
    records = _clean_records(records)
    findings: list[Finding] = []
    for rule_id, function in RULE_FUNCTIONS.items():
        if rule_id in registry:
            findings.extend(function(records, registry[rule_id]))
    return sorted(findings, key=lambda item: (item.rule_id, item.cse_id, item.finding_id))


def detect_execution_gaps(
    dataset_dir: str | Path = DEFAULT_DATASET_DIR,
    registry: RuleRegistry | None = None,
) -> list[Finding]:
    """Load canonical JSON records and detect potential execution gaps."""
    return analyze_evidence(load_evidence(dataset_dir), registry)


if __name__ == "__main__":
    findings = detect_execution_gaps()
    counts: dict[str, int] = defaultdict(int)
    for finding in findings:
        counts[finding.rule_id] += 1
    print(json.dumps({"finding_counts": dict(sorted(counts.items()))}, indent=2))


