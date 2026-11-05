"""Offline ingestion: validate a submission, report data quality, hash the files."""

from src.ingestion.manifest import (
    build_manifest,
    sha256_file,
    verify_manifest,
    write_manifest,
)
from src.ingestion.quality import inspect_submission, write_quality_report

__all__ = [
    "build_manifest",
    "inspect_submission",
    "sha256_file",
    "verify_manifest",
    "write_manifest",
    "write_quality_report",
]
