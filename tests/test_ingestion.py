import json
import shutil
import tempfile
import unittest
from pathlib import Path

from src.ingestion.manifest import (
    build_manifest,
    sha256_file,
    verify_manifest,
    write_manifest,
)
from src.ingestion.quality import inspect_submission, write_quality_report

GOLDEN = Path(__file__).resolve().parents[1] / "data" / "synthetic" / "golden_dataset"


def _copy_submission(destination: Path) -> Path:
    shutil.copytree(GOLDEN, destination)
    return destination


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _codes(report):
    return {issue["code"] for issue in report["issues"]}


class GoldenSubmissionReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = inspect_submission(GOLDEN)

    def test_clean_submission_has_no_errors_or_warnings(self) -> None:
        self.assertEqual(self.report["status"], "clean")
        self.assertEqual(self.report["error_count"], 0)
        self.assertEqual(self.report["warning_count"], 0)
        self.assertEqual(self.report["issues"], [])

    def test_counts_come_from_validated_records(self) -> None:
        self.assertEqual(
            self.report["counts"],
            {
                "cse.json": 6,
                "assets.json": 300,
                "alerts.json": 10_000,
                "cases.json": 2_000,
                "investigations.json": 1_500,
                "escalations.json": 664,
                "remediations.json": 260,
            },
        )

    def test_every_file_has_a_hash_and_size(self) -> None:
        for name, info in self.report["files"].items():
            self.assertEqual(info["status"], "ok", name)
            self.assertEqual(len(info["sha256"]), 64, name)
            self.assertEqual(info["bytes"], (GOLDEN / name).stat().st_size, name)
        self.assertEqual(len(self.report["submission_sha256"]), 64)

    def test_report_is_json_serializable_and_deterministic(self) -> None:
        first = json.dumps(self.report, sort_keys=True)
        second = json.dumps(inspect_submission(GOLDEN), sort_keys=True)
        self.assertEqual(first, second)

    def test_write_quality_report_matches_in_memory_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "quality.json"
            written = write_quality_report(GOLDEN, output)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), written)


class DataQualityIssueTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = _copy_submission(Path(self._tmp.name) / "submission")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_missing_required_file_is_an_error(self) -> None:
        (self.root / "cases.json").unlink()
        report = inspect_submission(self.root)
        self.assertEqual(report["status"], "issues")
        self.assertIn("missing_file", _codes(report))
        self.assertEqual(report["files"]["cases.json"]["status"], "missing")

    def test_absent_optional_file_is_a_warning_not_an_error(self) -> None:
        (self.root / "remediations.json").unlink()
        report = inspect_submission(self.root)
        self.assertEqual(report["status"], "clean")
        self.assertEqual(report["warning_count"], 1)
        self.assertIn("absent_optional_file", _codes(report))

    def test_malformed_json_is_reported(self) -> None:
        (self.root / "alerts.json").write_text("{not json", encoding="utf-8")
        report = inspect_submission(self.root)
        self.assertIn("invalid_json", _codes(report))
        self.assertEqual(report["files"]["alerts.json"]["status"], "invalid")

    def test_invalid_row_is_reported_without_losing_other_rows(self) -> None:
        alerts = _read(self.root / "alerts.json")
        alerts.append({"alert_id": "ALT-BROKEN"})
        _write(self.root / "alerts.json", alerts)
        report = inspect_submission(self.root)
        self.assertIn("invalid_row", _codes(report))
        self.assertEqual(report["counts"]["alerts.json"], 10_000)

    def test_duplicate_identifier_is_reported(self) -> None:
        assets = _read(self.root / "assets.json")
        assets.append(dict(assets[0]))
        _write(self.root / "assets.json", assets)
        report = inspect_submission(self.root)
        self.assertIn("duplicate_id", _codes(report))
        self.assertEqual(report["counts"]["assets.json"], 301)
        self.assertEqual(report["files"]["assets.json"]["status"], "invalid")

    def test_broken_reference_is_reported(self) -> None:
        alerts = _read(self.root / "alerts.json")
        alerts[0]["asset_id"] = "AST-DOES-NOT-EXIST"
        _write(self.root / "alerts.json", alerts)
        report = inspect_submission(self.root)
        self.assertIn("broken_reference", _codes(report))

    def test_cross_entity_cse_mismatch_is_reported(self) -> None:
        alerts = _read(self.root / "alerts.json")
        alerts[0]["cse_id"] = "CSE-06" if alerts[0]["cse_id"] != "CSE-06" else "CSE-01"
        _write(self.root / "alerts.json", alerts)
        report = inspect_submission(self.root)
        self.assertIn("reference_mismatch", _codes(report))

    def test_case_opening_before_its_alert_is_reported(self) -> None:
        cases = _read(self.root / "cases.json")
        cases[0]["opened_at"] = "2000-01-01T00:00:00Z"
        _write(self.root / "cases.json", cases)
        report = inspect_submission(self.root)
        self.assertIn("timestamp_order", _codes(report))

    def test_empty_required_file_is_a_warning(self) -> None:
        _write(self.root / "remediations.json", [])
        report = inspect_submission(self.root)
        # Remediations are optional, so an empty file is not itself a warning;
        # clearing a required file must be.
        self.assertEqual(report["status"], "clean")
        _write(self.root / "assets.json", [])
        report = inspect_submission(self.root)
        self.assertIn("empty_file", _codes(report))


class ManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = _copy_submission(Path(self._tmp.name) / "submission")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_manifest_lists_every_json_file_sorted(self) -> None:
        manifest = build_manifest(self.root)
        names = [entry["name"] for entry in manifest["files"]]
        self.assertEqual(names, sorted(names))
        self.assertIn("alerts.json", names)
        self.assertEqual(manifest["file_count"], len(names))
        for entry in manifest["files"]:
            self.assertEqual(entry["sha256"], sha256_file(self.root / entry["name"]))

    def test_combined_digest_is_reproducible_from_the_file_entries(self) -> None:
        manifest = build_manifest(self.root)
        lines = "".join(
            f"{entry['sha256']}  {entry['name']}\n" for entry in manifest["files"]
        )
        import hashlib

        self.assertEqual(
            manifest["combined_sha256"],
            hashlib.sha256(lines.encode("utf-8")).hexdigest(),
        )

    def test_verify_passes_when_files_are_untouched(self) -> None:
        manifest = build_manifest(self.root)
        self.assertEqual(verify_manifest(self.root, manifest), [])

    def test_verify_detects_tampering_and_missing_files(self) -> None:
        manifest = build_manifest(self.root)
        alerts = _read(self.root / "alerts.json")
        alerts[0]["severity"] = "low"
        _write(self.root / "alerts.json", alerts)
        (self.root / "cases.json").unlink()
        problems = {item["name"]: item["problem"] for item in verify_manifest(self.root, manifest)}
        self.assertEqual(problems["alerts.json"], "hash_mismatch")
        self.assertEqual(problems["cases.json"], "missing")

    def test_write_manifest_excludes_the_manifest_itself(self) -> None:
        output = self.root / "submission_manifest.json"
        write_manifest(self.root, output)
        manifest = json.loads(output.read_text(encoding="utf-8"))
        self.assertNotIn(
            "submission_manifest.json", [entry["name"] for entry in manifest["files"]]
        )
        # Writing it again must not change the digest.
        self.assertEqual(write_manifest(self.root, output), manifest)


if __name__ == "__main__":
    unittest.main()
