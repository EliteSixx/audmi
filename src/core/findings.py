"""Finding schema v1: the one output shape every AudMi rule must produce.

A finding is a *potential* supervisory indicator for human review. It is not a
compliance judgment, and missing evidence is not proof of missing activity.

The JSON mirror of this contract lives at ``data/schemas/finding.schema.json``.
Change both together and bump ``FINDING_SCHEMA_VERSION``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


FINDING_SCHEMA_VERSION = "1.0.0"

# Words AGENTS.md rule 3 forbids in finding text: a finding never states a verdict.
FORBIDDEN_REASON_TERMS = ("non-compliant", "noncompliant", "negligent", "failed")


class Capability(str, Enum):
    """The eight NCIIPC SOC capabilities a finding can be tagged with."""

    THREAT_DETECTION = "threat_detection"
    INVESTIGATION = "investigation"
    ESCALATION = "escalation"
    INCIDENT_RESPONSE = "incident_response"
    SECURITY_OPERATIONS = "security_operations"
    GOVERNANCE_OVERSIGHT = "governance_oversight"
    OPERATIONAL_DISCIPLINE = "operational_discipline"
    CYBER_RESILIENCE = "cyber_resilience"


class Category(str, Enum):
    EXECUTION_GAP = "execution_gap"
    NEGATIVE_SPACE = "negative_space"
    ANOMALY = "anomaly"


class SubjectType(str, Enum):
    """The record level a finding is about; evaluation scores at this level."""

    CASE = "case"
    ASSET = "asset"
    INVESTIGATION = "investigation"
    ENTITY = "entity"


def _required_text(value: Any, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


@dataclass(frozen=True, slots=True)
class Finding:
    finding_id: str
    rule_id: str
    rule_version: str
    capability: Capability
    category: Category
    cse_id: str
    subject_type: SubjectType
    subject_id: str
    reason: str
    supporting_record_ids: tuple[str, ...]
    # Numbers (and expectations) the rule used to decide. Dicts are unhashable,
    # so the field is excluded from the generated __hash__.
    baseline: dict[str, Any] = field(default_factory=dict, hash=False)
    data_quality_notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("finding_id", "rule_id", "rule_version", "cse_id", "subject_id", "reason"):
            _required_text(getattr(self, name), name)
        # Accept plain strings (e.g. from YAML) and store the enum member.
        object.__setattr__(self, "capability", Capability(self.capability))
        object.__setattr__(self, "category", Category(self.category))
        object.__setattr__(self, "subject_type", SubjectType(self.subject_type))
        object.__setattr__(self, "supporting_record_ids", tuple(self.supporting_record_ids))
        object.__setattr__(self, "data_quality_notes", tuple(self.data_quality_notes))
        if not self.supporting_record_ids or not all(
            isinstance(item, str) and item for item in self.supporting_record_ids
        ):
            raise ValueError("supporting_record_ids must be a non-empty list of record IDs")
        if not isinstance(self.baseline, dict):
            raise TypeError("baseline must be a dict")
        lowered = self.reason.lower()
        if "potential" not in lowered:
            raise ValueError("reason must describe a 'potential' indicator")
        for term in FORBIDDEN_REASON_TERMS:
            if term in lowered:
                raise ValueError(f"reason must not use verdict language: {term!r}")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly dict matching data/schemas/finding.schema.json."""
        return {
            "schema_version": FINDING_SCHEMA_VERSION,
            "finding_id": self.finding_id,
            "rule_id": self.rule_id,
            "rule_version": self.rule_version,
            "capability": self.capability.value,
            "category": self.category.value,
            "cse_id": self.cse_id,
            "subject_type": self.subject_type.value,
            "subject_id": self.subject_id,
            "reason": self.reason,
            "supporting_record_ids": list(self.supporting_record_ids),
            "baseline": dict(self.baseline),
            "data_quality_notes": list(self.data_quality_notes),
        }
