"""Shared plumbing for AudMi analytics rules.

Every rule works on the same in-memory ``EvidenceRecords`` bundle and emits the
same ``Finding`` shape. Keeping those two things (and the small robust-statistics
helper they share) in one place means a new rule module, such as
``negative_space``, does not have to import the execution-gap runner.

The bundle is deliberately simple: canonical model tuples, already loaded and
validated by the normalisation layer. Nothing here reads files or knows about
thresholds; thresholds belong in ``rules/*.yaml``.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Any

from src.core.findings import Finding
from src.core.registry import Rule
from src.normalization.evidence_model import (
    Alert,
    Asset,
    Case,
    CSE,
    Escalation,
    Investigation,
    Remediation,
)


@dataclass(frozen=True, slots=True)
class EvidenceRecords:
    """Canonical records supplied to every analytical rule."""

    cse: tuple[CSE, ...]
    assets: tuple[Asset, ...]
    alerts: tuple[Alert, ...]
    cases: tuple[Case, ...]
    investigations: tuple[Investigation, ...] = ()
    escalations: tuple[Escalation, ...] = ()
    remediations: tuple[Remediation, ...] = ()


def new_finding(
    rule: Rule,
    *,
    finding_id: str,
    cse_id: str,
    subject_id: str,
    reason: str,
    supporting_record_ids: tuple[str, ...],
    baseline: dict[str, Any],
    data_quality_notes: tuple[str, ...] = (),
) -> Finding:
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


def median_absolute_deviation(values: list[float]) -> tuple[float, float]:
    """Return ``(median, MAD)`` for a non-empty list of numbers."""
    median = statistics.median(values)
    mad = statistics.median(abs(value - median) for value in values)
    return median, mad
