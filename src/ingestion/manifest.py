"""SHA-256 submission manifests: proof that the evidence we scored is the evidence we received.

The manifest is deliberately boring and dependency-free. For every JSON file in
a submission directory we record its size and SHA-256 digest, then hash the
sorted ``digest  name`` lines into one combined digest. That is the same shape
as ``sha256sum`` output, so an examiner can reproduce it with standard tools
while the machine is offline.

The combined digest is what an analysis run should cite: if any byte in the
submission changes, the combined digest changes.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

ALGORITHM = "sha256"
DEFAULT_MANIFEST_NAME = "submission_manifest.json"


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: str | Path) -> str:
    """Hash a file in chunks so large evidence exports do not sit in memory."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _submission_files(
    dataset_dir: Path, exclude: Iterable[str]
) -> list[Path]:
    excluded = set(exclude) | {DEFAULT_MANIFEST_NAME}
    return sorted(
        path for path in dataset_dir.glob("*.json")
        if path.is_file() and path.name not in excluded
    )


def build_manifest(
    dataset_dir: str | Path,
    *,
    exclude: Iterable[str] = (),
) -> dict[str, Any]:
    """Return a manifest for every ``*.json`` file directly inside the directory."""
    root = Path(dataset_dir)
    if not root.is_dir():
        raise FileNotFoundError(f"submission directory not found: {root}")

    entries = []
    for path in _submission_files(root, exclude):
        entries.append({
            "name": path.name,
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })
    if not entries:
        raise ValueError(f"no JSON files found in submission directory: {root}")

    # Same line shape as sha256sum: "<digest>  <name>".
    combined = "\n".join(
        f"{entry['sha256']}  {entry['name']}" for entry in entries
    ) + "\n"
    return {
        "algorithm": ALGORITHM,
        "file_count": len(entries),
        "total_bytes": sum(entry["bytes"] for entry in entries),
        "files": entries,
        "combined_sha256": sha256_bytes(combined.encode("utf-8")),
    }


def verify_manifest(
    dataset_dir: str | Path, manifest: dict[str, Any]
) -> list[dict[str, str]]:
    """Compare a directory against a manifest; return one entry per mismatch."""
    root = Path(dataset_dir)
    if manifest.get("algorithm") != ALGORITHM:
        raise ValueError(f"unsupported manifest algorithm: {manifest.get('algorithm')!r}")
    mismatches: list[dict[str, str]] = []
    for entry in manifest.get("files", []):
        path = root / entry["name"]
        if not path.is_file():
            mismatches.append({"name": entry["name"], "problem": "missing"})
            continue
        actual = sha256_file(path)
        if actual != entry["sha256"]:
            mismatches.append({
                "name": entry["name"],
                "problem": "hash_mismatch",
                "expected": entry["sha256"],
                "actual": actual,
            })
    return mismatches


def write_manifest(
    dataset_dir: str | Path,
    output_path: str | Path,
    *,
    exclude: Iterable[str] = (),
) -> dict[str, Any]:
    manifest = build_manifest(dataset_dir, exclude=exclude)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest
