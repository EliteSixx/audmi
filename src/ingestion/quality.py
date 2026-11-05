"""Ingestion and data-quality report for an evidence submission.

Before a single rule runs, an examiner needs to know whether the submission is
complete and internally consistent. This module answers that question without
changing the data: it parses each canonical JSON file, validates every row
against the evidence model, checks identifiers and references, checks timestamp
order, and reports what it found.

It never repairs or drops data silently. Malformed rows are counted and listed
so a human can decide what to do, and the report carries the SHA-256 manifest of
the exact files that were inspected.

The report is descriptive, not a compliance judgment.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from src.ingestion.manifest import build_manifest, sha256_file
from src.normalization.evidence_model import (
    Alert,
    Asset,
    Case,
    CSE,
    Escalation,
    Investigation,
    Remediation,
)


REQUIRED_FILES: dict[str, type] = {
    "cse.json": CSE,
    "assets.json": Asset,
    "alerts.json": Alert,
    "cases.json": Case,
}
OPTIONAL_FILES: dict[str, type] = {
    "investigations.json": Investigation,
    "escalations.json": Escalation,
    "remediations.json": Remediation,
}
TIMESTAMP_FIELDS: dict[str, tuple[str, ...]] = {
    "alerts.json": ("created_at", "closed_at"),
    "cases.json": ("opened_at", "closed_at"),
    "investigations.json": ("started_at", "ended_at"),
    "escalations.json": ("escalated_at",),
    "remediations.json": ("completed_at",),
}
ID_FIELDS: dict[str, str] = {
    "cse.json": "cse_id",
    "assets.json": "asset_id",
    "alerts.json": "alert_id",
    "cases.json": "case_id",
    "investigations.json": "investigation_id",
    "escalations.json": "escalation_id",
    "remediations.json": "remediation_id",
}


@dataclass(frozen=True, slots=True)
class Issue:
    code: str
    severity: str
    file: str
    row: int | None
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "file": self.file,
            "row": self.row,
            "message": self.message,
        }


def _issue(
    issues: list[Issue],
    code: str,
    severity: str,
    file: str,
    message: str,
    row: int | None = None,
) -> None:
    issues.append(Issue(code, severity, file, row, message))


def _parse_timestamps(row: dict[str, Any], fields: Iterable[str]) -> dict[str, Any]:
    parsed = dict(row)
    for name in fields:
        value = parsed.get(name)
        if isinstance(value, str):
            parsed[name] = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed


def _load_rows(
    root: Path,
    name: str,
    model: type,
    issues: list[Issue],
) -> list[tuple[int, Any]] | None:
    """Return ``(row_number, record)`` pairs, or ``None`` when the file is absent.

    A malformed row produces an issue and is skipped; it never aborts the file,
    because one bad row should not hide the rest of the submission.
    """
    path = root / name
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as error:
        _issue(issues, "invalid_json", "error", name, f"could not parse JSON: {error}")
        return []
    if not isinstance(raw, list):
        _issue(issues, "not_an_array", "error", name, "file must contain a JSON array")
        return []

    rows: list[tuple[int, Any]] = []
    for row_number, row in enumerate(raw, start=1):
        if not isinstance(row, dict):
            _issue(issues, "invalid_row", "error", name,
                   "row must be a JSON object", row_number)
            continue
        try:
            rows.append((
                row_number,
                model(**_parse_timestamps(row, TIMESTAMP_FIELDS.get(name, ()))),
            ))
        except (KeyError, TypeError, ValueError) as error:
            _issue(issues, "invalid_row", "error", name, str(error), row_number)
    return rows


def _index(
    rows: list[tuple[int, Any]],
    id_field: str,
    name: str,
    issues: list[Issue],
) -> dict[str, tuple[int, Any]]:
    """Index rows by ID and report duplicates instead of overwriting them."""
    indexed: dict[str, tuple[int, Any]] = {}
    for row_number, record in rows:
        record_id = getattr(record, id_field)
        if record_id in indexed:
            first_row = indexed[record_id][0]
            _issue(
                issues,
                "duplicate_id",
                "error",
                name,
                f"identifier {record_id!r} already appears on row {first_row}",
                row_number,
            )
            continue
        indexed[record_id] = (row_number, record)
    return indexed


def _check_references(
    cse_by_id: dict[str, tuple[int, CSE]],
    assets: dict[str, tuple[int, Asset]],
    alerts: dict[str, tuple[int, Alert]],
    cases: dict[str, tuple[int, Case]],
    investigations: dict[str, tuple[int, Investigation]],
    escalations: dict[str, tuple[int, Escalation]],
    remediations: dict[str, tuple[int, Remediation]],
    issues: list[Issue],
) -> None:
    cse_ids = set(cse_by_id)
    for asset_id, (row, asset) in assets.items():
        if asset.cse_id not in cse_ids:
            _issue(issues, "broken_reference", "error", "assets.json",
                   f"asset {asset_id!r} references unknown CSE {asset.cse_id!r}", row)

    for alert_id, (row, alert) in alerts.items():
        if alert.cse_id not in cse_ids:
            _issue(issues, "broken_reference", "error", "alerts.json",
                   f"alert {alert_id!r} references unknown CSE {alert.cse_id!r}", row)
        asset_entry = assets.get(alert.asset_id)
        if asset_entry is None:
            _issue(issues, "broken_reference", "error", "alerts.json",
                   f"alert {alert_id!r} references unknown asset {alert.asset_id!r}", row)
        elif asset_entry[1].cse_id != alert.cse_id:
            _issue(issues, "reference_mismatch", "error", "alerts.json",
                   f"alert {alert_id!r} CSE {alert.cse_id!r} does not match "
                   f"asset {alert.asset_id!r} CSE {asset_entry[1].cse_id!r}", row)

    for case_id, (row, case) in cases.items():
        alert_entry = alerts.get(case.alert_id)
        if alert_entry is None:
            _issue(issues, "broken_reference", "error", "cases.json",
                   f"case {case_id!r} references unknown alert {case.alert_id!r}", row)
            continue
        alert = alert_entry[1]
        if alert.cse_id != case.cse_id:
            _issue(issues, "reference_mismatch", "error", "cases.json",
                   f"case {case_id!r} CSE {case.cse_id!r} does not match "
                   f"alert {alert.alert_id!r} CSE {alert.cse_id!r}", row)
        if case.opened_at < alert.created_at:
            _issue(issues, "timestamp_order", "error", "cases.json",
                   f"case {case_id!r} opens before alert {alert.alert_id!r} was created", row)

    for investigation_id, (row, item) in investigations.items():
        case_entry = cases.get(item.case_id)
        if case_entry is None:
            _issue(issues, "broken_reference", "error", "investigations.json",
                   f"investigation {investigation_id!r} references unknown case {item.case_id!r}", row)
        elif item.started_at < case_entry[1].opened_at:
            _issue(issues, "timestamp_order", "error", "investigations.json",
                   f"investigation {investigation_id!r} starts before case {item.case_id!r} opens", row)

    for escalation_id, (row, item) in escalations.items():
        case_entry = cases.get(item.case_id)
        if case_entry is None:
            _issue(issues, "broken_reference", "error", "escalations.json",
                   f"escalation {escalation_id!r} references unknown case {item.case_id!r}", row)
        elif item.escalated_at < case_entry[1].opened_at:
            _issue(issues, "timestamp_order", "error", "escalations.json",
                   f"escalation {escalation_id!r} occurs before case {item.case_id!r} opens", row)

    for remediation_id, (row, item) in remediations.items():
        case_entry = cases.get(item.case_id)
        if case_entry is None:
            _issue(issues, "broken_reference", "error", "remediations.json",
                   f"remediation {remediation_id!r} references unknown case {item.case_id!r}", row)
        elif item.completed_at is not None and item.completed_at < case_entry[1].opened_at:
            _issue(issues, "timestamp_order", "error", "remediations.json",
                   f"remediation {remediation_id!r} completes before case {item.case_id!r} opens", row)


def inspect_submission(dataset_dir: str | Path = "data/synthetic/golden_dataset") -> dict[str, Any]:
    """Inspect a submission directory and return a deterministic quality report."""
    root = Path(dataset_dir)
    issues: list[Issue] = []
    files: dict[str, dict[str, Any]] = {}

    if not root.is_dir():
        _issue(issues, "missing_directory", "error", ".", f"not a directory: {root}")
        return _report(root, files, {}, issues, submission_sha256=None)

    loaded: dict[str, dict[str, tuple[int, Any]]] = {}
    for name, model in {**REQUIRED_FILES, **OPTIONAL_FILES}.items():
        path = root / name
        rows = _load_rows(root, name, model, issues)
        if rows is None:
            severity = "error" if name in REQUIRED_FILES else "warning"
            code = "missing_file" if name in REQUIRED_FILES else "absent_optional_file"
            _issue(issues, code, severity, name,
                   "required evidence file is missing" if name in REQUIRED_FILES
                   else "optional workflow file is absent")
            loaded[name] = {}
            files[name] = {"status": "missing", "bytes": 0, "sha256": None, "records": 0}
            continue
        indexed = _index(rows, ID_FIELDS[name], name, issues)
        loaded[name] = indexed
        if name in REQUIRED_FILES and not rows:
            _issue(issues, "empty_file", "warning", name,
                   "required evidence file contains no rows")
        file_error_count = sum(
            1 for item in issues if item.file == name and item.severity == "error"
        )
        files[name] = {
            "status": "invalid" if file_error_count else "ok",
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            "records": len(rows),
        }

    _check_references(
        loaded["cse.json"],
        loaded["assets.json"],
        loaded["alerts.json"],
        loaded["cases.json"],
        loaded["investigations.json"],
        loaded["escalations.json"],
        loaded["remediations.json"],
        issues,
    )

    try:
        manifest = build_manifest(root)
        submission_sha256 = manifest["combined_sha256"]
    except (FileNotFoundError, ValueError):
        submission_sha256 = None

    issues.sort(key=lambda item: (item.file, item.row or 0, item.code, item.message))
    counts = {name: info["records"] for name, info in files.items()}
    return _report(root, files, counts, issues, submission_sha256=submission_sha256)


def _report(
    root: Path,
    files: dict[str, dict[str, Any]],
    counts: dict[str, int],
    issues: list[Issue],
    *,
    submission_sha256: str | None,
) -> dict[str, Any]:
    error_count = sum(1 for item in issues if item.severity == "error")
    warning_count = sum(1 for item in issues if item.severity == "warning")
    return {
        "dataset_dir": str(root),
        "algorithm": "sha256",
        "submission_sha256": submission_sha256,
        "files": files,
        "counts": counts,
        "error_count": error_count,
        "warning_count": warning_count,
        "status": "clean" if error_count == 0 else "issues",
        "issues": [item.to_dict() for item in issues],
    }


def write_quality_report(
    dataset_dir: str | Path, output_path: str | Path
) -> dict[str, Any]:
    report = inspect_submission(dataset_dir)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report
