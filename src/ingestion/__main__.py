"""CLI: ``python -m src.ingestion`` validates a submission and writes both artefacts.

Example::

    python -m src.ingestion --dataset-dir data/synthetic/golden_dataset
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.ingestion.manifest import write_manifest
from src.ingestion.quality import write_quality_report

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET_DIR = REPOSITORY_ROOT / "data" / "synthetic" / "golden_dataset"
DEFAULT_QUALITY_OUTPUT = REPOSITORY_ROOT / "data" / "outputs" / "quality_report.json"
DEFAULT_MANIFEST_OUTPUT = REPOSITORY_ROOT / "data" / "outputs" / "submission_manifest.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET_DIR)
    parser.add_argument("--quality-output", type=Path, default=DEFAULT_QUALITY_OUTPUT)
    parser.add_argument("--manifest-output", type=Path, default=DEFAULT_MANIFEST_OUTPUT)
    args = parser.parse_args(argv)

    report = write_quality_report(args.dataset_dir, args.quality_output)
    manifest = write_manifest(args.dataset_dir, args.manifest_output)

    summary = {
        "status": report["status"],
        "errors": report["error_count"],
        "warnings": report["warning_count"],
        "counts": report["counts"],
        "submission_sha256": manifest["combined_sha256"],
        "quality_report": str(args.quality_output),
        "manifest": str(args.manifest_output),
    }
    print(json.dumps(summary, indent=2))
    return 0 if report["status"] == "clean" else 1


if __name__ == "__main__":
    raise SystemExit(main())
