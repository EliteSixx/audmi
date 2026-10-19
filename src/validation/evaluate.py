"""Evaluation harness: score registry rules against seeded ground truth.

Run with ``python -m src.validation.evaluate``. Prints a table and writes
``data/outputs/eval_report.json``.

How to read the numbers
-----------------------
* **seeded** - records the generator planted for a condition (ground truth).
* **caught** - seeded records the rule flagged.  **missed** - seeded, not flagged.
* **unclassified** - flagged records that ground truth says nothing about. They
  are *not* called false positives: they may be ordinary noise, or real
  conditions the generator produced by accident. Ground truth only labels what
  was planted.
* **precision** = caught / flagged. Because unclassified flags count against it,
  this is a lower bound on true precision.
* **recall** = caught / seeded.

Each condition is scored at the level its rule works at (case, investigation
or asset), so an asset-level rule is never scored against case IDs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.analytics.execution_gaps import DEFAULT_DATASET_DIR, detect_execution_gaps
from src.core.findings import Finding, SubjectType
from src.core.registry import RuleRegistry, load_registry


DEFAULT_OUTPUT_PATH = Path(__file__).resolve().parents[2] / "data" / "outputs" / "eval_report.json"
ALL_COHORTS = "ALL"


@dataclass(frozen=True, slots=True)
class ConditionMapping:
    """Which rule answers a ground-truth condition, and at which record level."""

    rule_id: str | None
    subject_type: SubjectType
    ground_truth_field: str


# Ground-truth condition_type -> detector. rule_id None means no detector exists yet.
CONDITION_MAPPINGS: dict[str, ConditionMapping] = {
    "missing_escalation": ConditionMapping(
        "missing_escalation", SubjectType.CASE, "record_ids"),
    "unusually_short_investigation": ConditionMapping(
        "unusually_short_investigation", SubjectType.INVESTIGATION, "record_ids"),
    # Ground truth also lists case IDs for this condition; the rule flags assets.
    "repeated_alerts_without_remediation": ConditionMapping(
        "repeated_alerts_without_remediation", SubjectType.ASSET, "asset_ids"),
    "negative_space_low_activity": ConditionMapping(
        None, SubjectType.ASSET, "asset_ids"),
}


def _ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def _score(flagged: set[str], seeded: set[str], labelled: set[str]) -> dict[str, Any]:
    """Score one cohort. ``labelled`` is every seeded ID for this rule in any cohort."""
    caught = flagged & seeded
    return {
        "flagged": len(flagged),
        "seeded": len(seeded),
        "caught": len(caught),
        "missed": len(seeded - flagged),
        "unclassified": len(flagged - labelled),
        "precision": _ratio(len(caught), len(flagged)),
        "recall": _ratio(len(caught), len(seeded)),
        "missed_ids": sorted(seeded - flagged),
    }


def evaluate(
    findings: list[Finding],
    ground_truth: dict[str, Any],
    registry: RuleRegistry,
) -> dict[str, Any]:
    """Return per-condition, per-cohort scores. Pure function: no file access."""
    flagged_by_rule_cse: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for finding in findings:
        flagged_by_rule_cse[finding.rule_id][finding.cse_id].add(finding.subject_id)

    conditions_by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for condition in ground_truth.get("conditions", []):
        conditions_by_type[condition["condition_type"]].append(condition)

    results: list[dict[str, Any]] = []
    for condition_type in sorted(conditions_by_type):
        conditions = conditions_by_type[condition_type]
        mapping = CONDITION_MAPPINGS.get(condition_type)
        if mapping is None or mapping.rule_id is None or mapping.rule_id not in registry:
            for condition in sorted(conditions, key=lambda item: item["cse_id"]):
                seeded = condition.get(mapping.ground_truth_field if mapping else "record_ids", [])
                results.append({
                    "condition_type": condition_type,
                    "rule_id": None,
                    "rule_version": None,
                    "subject_type": mapping.subject_type.value if mapping else None,
                    "cohort": condition["cse_id"],
                    "status": "no detector",
                    "seeded": len(seeded),
                })
            continue

        rule = registry[mapping.rule_id]
        flagged_by_cse = flagged_by_rule_cse.get(rule.id, {})
        seeded_by_cse: dict[str, set[str]] = defaultdict(set)
        for condition in conditions:
            seeded_by_cse[condition["cse_id"]].update(condition.get(mapping.ground_truth_field, []))
        labelled = set().union(*seeded_by_cse.values())
        all_flagged = set().union(*flagged_by_cse.values()) if flagged_by_cse else set()

        base = {
            "condition_type": condition_type,
            "rule_id": rule.id,
            "rule_version": rule.version,
            "subject_type": mapping.subject_type.value,
            "status": "scored",
        }
        for cse_id in sorted(seeded_by_cse):
            results.append({
                **base,
                "cohort": cse_id,
                **_score(flagged_by_cse.get(cse_id, set()), seeded_by_cse[cse_id], labelled),
            })
        # ALL also counts flags in CSEs that have no planted condition at all.
        results.append({**base, "cohort": ALL_COHORTS, **_score(all_flagged, labelled, labelled)})
    return {
        "ground_truth_seed": ground_truth.get("seed"),
        "rules": {rule.id: rule.version for rule in registry},
        "results": results,
        "notes": [
            "unclassified = flagged but not in ground truth; not proven false positives.",
            "precision counts unclassified flags against the rule, so it is a lower bound.",
            "Synthetic data: these numbers describe the test data as much as the rules.",
        ],
    }


def format_table(report: dict[str, Any]) -> str:
    headers = ("condition", "rule", "level", "cohort", "flagged", "seeded", "caught",
               "missed", "unclassified", "precision", "recall")
    rows = []
    for item in report["results"]:
        if item["status"] == "no detector":
            rows.append((item["condition_type"], "no detector", item["subject_type"] or "-",
                         item["cohort"], "-", str(item["seeded"]), "-", "-", "-", "-", "-"))
            continue
        rows.append((
            item["condition_type"],
            f"{item['rule_id']}@{item['rule_version']}",
            item["subject_type"],
            item["cohort"],
            *(str(item[key]) for key in ("flagged", "seeded", "caught", "missed", "unclassified")),
            *("-" if item[key] is None else f"{item[key]:.3f}" for key in ("precision", "recall")),
        ))
    widths = [max(len(str(row[i])) for row in (headers, *rows)) for i in range(len(headers))]
    numeric = set(range(4, len(headers)))

    def line(values: tuple[str, ...]) -> str:
        return "  ".join(
            value.rjust(widths[i]) if i in numeric else value.ljust(widths[i])
            for i, value in enumerate(values)
        ).rstrip()

    out = [line(headers), line(tuple("-" * width for width in widths))]
    out.extend(line(row) for row in rows)
    return "\n".join(out)


def run(
    dataset_dir: str | Path = DEFAULT_DATASET_DIR,
    output_path: str | Path | None = DEFAULT_OUTPUT_PATH,
    registry: RuleRegistry | None = None,
) -> dict[str, Any]:
    registry = registry if registry is not None else load_registry()
    dataset_dir = Path(dataset_dir)
    truth_path = dataset_dir / "ground_truth.json"
    truth_bytes = truth_path.read_bytes()
    report = evaluate(
        detect_execution_gaps(dataset_dir, registry),
        json.loads(truth_bytes.decode("utf-8")),
        registry,
    )
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dataset_dir": str(dataset_dir),
        "ground_truth_sha256": hashlib.sha256(truth_bytes).hexdigest(),
        **report,
    }
    if output_path is not None:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Score AudMi rules against ground truth.")
    parser.add_argument("--dataset-dir", default=str(DEFAULT_DATASET_DIR))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    args = parser.parse_args(argv)
    report = run(args.dataset_dir, args.output)
    print(format_table(report))
    print()
    for note in report["notes"]:
        print(f"note: {note}")
    print(f"report written to {args.output}")


if __name__ == "__main__":
    main()
