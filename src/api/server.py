"""Offline-only JSON API for AudMi (Python standard library, no dependencies).

Why stdlib instead of FastAPI
-----------------------------
AudMi has to run air-gapped. Every extra package is another wheel to carry into
the exam room, so the API uses ``http.server`` and binds to loopback by default.
It never calls out; it only reads the local evidence directory.

Endpoints
---------
``GET /health``                     liveness and rule count
``GET /summary``                    submission digest, record counts, finding counts
``GET /entities``                   one row per CSE with activity and finding counts
``GET /findings``                   findings, filterable by cse_id, rule_id, level
``GET /findings/{id}``              one finding
``GET /findings/{id}/evidence``     the finding plus the records it cites

Run with::

    python -m src.api --port 8000
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import parse_qs, unquote, urlparse

from src.analytics.common import EvidenceRecords
from src.analytics.execution_gaps import (
    DEFAULT_DATASET_DIR,
    analyze_evidence,
    load_evidence,
)
from src.core.findings import Finding
from src.core.registry import RuleRegistry, load_registry
from src.ingestion.manifest import build_manifest
from src.ingestion.quality import inspect_submission

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_LIMIT = 100
MAX_LIMIT = 1_000

EVIDENCE_FILES = (
    ("cse", "cse.json"),
    ("assets", "assets.json"),
    ("alerts", "alerts.json"),
    ("cases", "cases.json"),
    ("investigations", "investigations.json"),
    ("escalations", "escalations.json"),
    ("remediations", "remediations.json"),
)
RECORD_ID_FIELDS = {
    "cse": "cse_id",
    "assets": "asset_id",
    "alerts": "alert_id",
    "cases": "case_id",
    "investigations": "investigation_id",
    "escalations": "escalation_id",
    "remediations": "remediation_id",
}


@dataclass(frozen=True, slots=True)
class ApiState:
    """Everything the API serves, computed once from the local evidence directory."""

    dataset_dir: Path
    evidence: EvidenceRecords
    findings: tuple[Finding, ...]
    registry: RuleRegistry
    manifest: dict[str, Any]
    quality: dict[str, Any]
    ground_truth_sha256: str | None
    record_index: dict[str, tuple[str, dict[str, Any]]]
    findings_by_id: dict[str, Finding]


def _json_record(record: Any) -> dict[str, Any]:
    payload = asdict(record)
    for name, value in payload.items():
        if isinstance(value, datetime):
            payload[name] = value.astimezone(timezone.utc).isoformat(
                timespec="seconds").replace("+00:00", "Z")
    return payload


def build_state(
    dataset_dir: str | Path = DEFAULT_DATASET_DIR,
    registry: RuleRegistry | None = None,
) -> ApiState:
    """Load the evidence and pre-compute findings, manifest and quality report."""
    root = Path(dataset_dir)
    registry = registry if registry is not None else load_registry()
    evidence = load_evidence(root)
    findings = tuple(analyze_evidence(evidence, registry))

    record_index: dict[str, tuple[str, dict[str, Any]]] = {}
    for kind, _filename in EVIDENCE_FILES:
        id_field = RECORD_ID_FIELDS[kind]
        for record in getattr(evidence, kind):
            payload = _json_record(record)
            record_index[payload[id_field]] = (kind, payload)

    truth_path = root / "ground_truth.json"
    ground_truth_sha256 = (
        sha256(truth_path.read_bytes()).hexdigest() if truth_path.is_file() else None
    )
    return ApiState(
        dataset_dir=root,
        evidence=evidence,
        findings=findings,
        registry=registry,
        manifest=build_manifest(root),
        quality=inspect_submission(root),
        ground_truth_sha256=ground_truth_sha256,
        record_index=record_index,
        findings_by_id={item.finding_id: item for item in findings},
    )


def _counts(state: ApiState) -> dict[str, int]:
    return {kind: len(getattr(state.evidence, kind)) for kind, _ in EVIDENCE_FILES}


def _finding_payload(state: ApiState, finding: Finding) -> dict[str, Any]:
    rule = state.registry[finding.rule_id]
    return {**finding.to_dict(), "level": rule.level, "rule_title": rule.title}


def _summary(state: ApiState) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for finding in state.findings:
        counts[finding.rule_id] = counts.get(finding.rule_id, 0) + 1
    return {
        "dataset_dir": str(state.dataset_dir),
        "submission_sha256": state.manifest["combined_sha256"],
        "ground_truth_sha256": state.ground_truth_sha256,
        "quality": {
            "status": state.quality["status"],
            "error_count": state.quality["error_count"],
            "warning_count": state.quality["warning_count"],
        },
        "counts": _counts(state),
        "rules": [
            {
                "rule_id": rule.id,
                "version": rule.version,
                "title": rule.title,
                "level": rule.level,
                "capability": rule.capability.value,
                "category": rule.category.value,
                "subject_type": rule.subject_type.value,
            }
            for rule in state.registry
        ],
        "finding_counts": dict(sorted(counts.items())),
        "total_findings": len(state.findings),
    }


def _entities(state: ApiState) -> list[dict[str, Any]]:
    cse_ids = {item.cse_id: item for item in state.evidence.cse}
    asset_counts: dict[str, int] = {cse_id: 0 for cse_id in cse_ids}
    for asset in state.evidence.assets:
        asset_counts[asset.cse_id] = asset_counts.get(asset.cse_id, 0) + 1
    alert_counts: dict[str, int] = {cse_id: 0 for cse_id in cse_ids}
    for alert in state.evidence.alerts:
        alert_counts[alert.cse_id] = alert_counts.get(alert.cse_id, 0) + 1
    case_counts: dict[str, int] = {cse_id: 0 for cse_id in cse_ids}
    case_to_cse: dict[str, str] = {}
    for case in state.evidence.cases:
        case_counts[case.cse_id] = case_counts.get(case.cse_id, 0) + 1
        case_to_cse[case.case_id] = case.cse_id
    investigation_counts: dict[str, int] = {cse_id: 0 for cse_id in cse_ids}
    for item in state.evidence.investigations:
        cse_id = case_to_cse.get(item.case_id)
        if cse_id is not None:
            investigation_counts[cse_id] = investigation_counts.get(cse_id, 0) + 1
    finding_counts: dict[str, int] = {cse_id: 0 for cse_id in cse_ids}
    for finding in state.findings:
        finding_counts[finding.cse_id] = finding_counts.get(finding.cse_id, 0) + 1

    return [
        {
            "cse_id": cse.cse_id,
            "name": cse.name,
            "peer_group": cse.peer_group,
            "asset_count": asset_counts.get(cse.cse_id, 0),
            "alert_count": alert_counts.get(cse.cse_id, 0),
            "case_count": case_counts.get(cse.cse_id, 0),
            "investigation_count": investigation_counts.get(cse.cse_id, 0),
            "finding_count": finding_counts.get(cse.cse_id, 0),
        }
        for cse in sorted(state.evidence.cse, key=lambda item: item.cse_id)
    ]


def _int_param(query: Mapping[str, str], name: str, default: int) -> int:
    raw = query.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        raise ValueError(f"{name} must be an integer") from None


def _findings(state: ApiState, query: Mapping[str, str]) -> dict[str, Any]:
    limit = _int_param(query, "limit", DEFAULT_LIMIT)
    offset = _int_param(query, "offset", 0)
    if limit < 1 or limit > MAX_LIMIT:
        raise ValueError(f"limit must be between 1 and {MAX_LIMIT}")
    if offset < 0:
        raise ValueError("offset must be zero or greater")

    cse_id = query.get("cse_id")
    rule_id = query.get("rule_id")
    level = query.get("level")
    filtered = [
        finding for finding in state.findings
        if (cse_id is None or finding.cse_id == cse_id)
        and (rule_id is None or finding.rule_id == rule_id)
        and (level is None or state.registry[finding.rule_id].level == level)
    ]
    page = filtered[offset: offset + limit]
    return {
        "total": len(filtered),
        "count": len(page),
        "offset": offset,
        "limit": limit,
        "findings": [_finding_payload(state, finding) for finding in page],
    }


def _evidence(state: ApiState, finding_id: str) -> dict[str, Any] | None:
    finding = state.findings_by_id.get(finding_id)
    if finding is None:
        return None
    grouped: dict[str, list[dict[str, Any]]] = {kind: [] for kind, _ in EVIDENCE_FILES}
    unresolved: list[str] = []
    for record_id in finding.supporting_record_ids:
        entry = state.record_index.get(record_id)
        if entry is None:
            unresolved.append(record_id)
            continue
        kind, payload = entry
        grouped[kind].append(payload)
    return {
        "finding": _finding_payload(state, finding),
        "records": {kind: rows for kind, rows in grouped.items() if rows},
        "unresolved_record_ids": unresolved,
    }


def route(
    state: ApiState, path: str, query: Mapping[str, str] | None = None
) -> tuple[int, dict[str, Any]]:
    """Pure request router; returns ``(http_status, json_payload)``."""
    query = dict(query or {})
    cleaned = "/" + path.strip("/")
    try:
        if cleaned == "/health":
            return 200, {
                "status": "ok",
                "dataset_dir": str(state.dataset_dir),
                "rule_count": len(state.registry),
                "finding_count": len(state.findings),
            }
        if cleaned == "/summary":
            return 200, _summary(state)
        if cleaned == "/entities":
            return 200, {"entities": _entities(state)}
        if cleaned == "/findings":
            return 200, _findings(state, query)
        if cleaned.startswith("/findings/"):
            parts = cleaned.split("/")
            finding_id = unquote(parts[2])
            if len(parts) == 3:
                finding = state.findings_by_id.get(finding_id)
                if finding is None:
                    return 404, {"error": f"finding not found: {finding_id}"}
                return 200, _finding_payload(state, finding)
            if len(parts) == 4 and parts[3] == "evidence":
                payload = _evidence(state, finding_id)
                if payload is None:
                    return 404, {"error": f"finding not found: {finding_id}"}
                return 200, payload
    except ValueError as error:
        return 400, {"error": str(error)}
    return 404, {"error": f"unknown endpoint: {cleaned}"}


class AudMiHTTPServer(ThreadingHTTPServer):
    """Threading loopback server carrying the pre-computed state."""

    daemon_threads = True

    def __init__(self, address: tuple[str, int], state: ApiState, quiet: bool = False):
        super().__init__(address, AudMiRequestHandler)
        self.state = state
        self.quiet = quiet


class AudMiRequestHandler(BaseHTTPRequestHandler):
    server: AudMiHTTPServer

    def do_GET(self) -> None:  # noqa: N802 - http.server naming
        parsed = urlparse(self.path)
        query = {key: values[-1] for key, values in parse_qs(parsed.query).items()}
        status, payload = route(self.server.state, parsed.path, query)
        self._send_json(status, payload)

    def do_OPTIONS(self) -> None:  # noqa: N802 - http.server naming
        self.send_response(204)
        self._send_cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self) -> None:  # noqa: N802 - http.server naming
        status, payload = 405, {"error": "only GET is supported"}
        self._send_json(status, payload)

    do_PUT = do_POST  # type: ignore[assignment]
    do_DELETE = do_POST  # type: ignore[assignment]

    def _send_cors(self) -> None:
        # Loopback-only API; the demo UI may be served from another local port.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._send_cors()
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        if not self.server.quiet:
            super().log_message(format, *args)


def create_server(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    state: ApiState | None = None,
    *,
    quiet: bool = False,
) -> AudMiHTTPServer:
    return AudMiHTTPServer((host, port), state or build_state(), quiet=quiet)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serve the offline AudMi JSON API.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET_DIR)
    parser.add_argument("--quiet", action="store_true", help="suppress request logs")
    args = parser.parse_args(argv)

    server = create_server(
        args.host, args.port, build_state(args.dataset_dir), quiet=args.quiet
    )
    host, port = server.server_address[:2]
    print(f"AudMi API listening on http://{host}:{port} (dataset: {args.dataset_dir})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping AudMi API.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
