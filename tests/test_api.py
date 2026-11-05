import json
import threading
import unittest
from urllib.request import urlopen

from src.api.server import build_state, create_server, route


class ApiRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.state = build_state()
        cls.total = len(cls.state.findings)

    def test_health_is_ok(self) -> None:
        status, body = route(self.state, "/health")
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["rule_count"], 4)
        self.assertEqual(body["finding_count"], self.total)

    def test_summary_reports_counts_rules_and_digest(self) -> None:
        status, body = route(self.state, "/summary")
        self.assertEqual(status, 200)
        self.assertEqual(len(body["submission_sha256"]), 64)
        self.assertEqual(len(body["ground_truth_sha256"]), 64)
        self.assertEqual(body["quality"]["status"], "clean")
        self.assertEqual(body["counts"]["alerts"], 10_000)
        self.assertEqual(len(body["rules"]), 4)
        self.assertEqual(body["total_findings"], self.total)
        self.assertEqual(
            body["finding_counts"],
            {
                "missing_escalation": 279,
                "negative_space_low_activity": 8,
                "repeated_alerts_without_remediation": 8,
                "unusually_short_investigation": 127,
            },
        )

    def test_entities_cover_every_cse_and_sum_findings(self) -> None:
        status, body = route(self.state, "/entities")
        self.assertEqual(status, 200)
        entities = body["entities"]
        self.assertEqual(len(entities), 6)
        self.assertEqual(
            sum(item["finding_count"] for item in entities), self.total
        )
        self.assertEqual(sum(item["asset_count"] for item in entities), 300)
        self.assertEqual(sum(item["alert_count"] for item in entities), 10_000)
        self.assertEqual(entities[0]["cse_id"], "CSE-01")

    def test_findings_can_be_filtered_by_rule_and_cse(self) -> None:
        status, body = route(
            self.state, "/findings", {"rule_id": "negative_space_low_activity"})
        self.assertEqual(status, 200)
        self.assertEqual(body["total"], 8)
        self.assertTrue(all(
            item["rule_id"] == "negative_space_low_activity"
            for item in body["findings"]
        ))

        status, body = route(self.state, "/findings", {"cse_id": "CSE-05"})
        expected = sum(1 for item in self.state.findings if item.cse_id == "CSE-05")
        self.assertEqual(body["total"], expected)

    def test_findings_can_be_filtered_by_rule_level(self) -> None:
        status, body = route(self.state, "/findings", {"level": "high", "limit": "1000"})
        self.assertEqual(status, 200)
        self.assertTrue(body["findings"])
        self.assertTrue(all(item["level"] == "high" for item in body["findings"]))
        self.assertEqual(
            {item["rule_id"] for item in body["findings"]},
            {
                "missing_escalation",
                "negative_space_low_activity",
                "repeated_alerts_without_remediation",
            },
        )

    def test_findings_are_paginated(self) -> None:
        status, body = route(self.state, "/findings", {"limit": "5", "offset": "5"})
        self.assertEqual(status, 200)
        self.assertEqual(body["count"], 5)
        self.assertEqual(body["total"], self.total)
        self.assertEqual(
            [item["finding_id"] for item in body["findings"]],
            [item.finding_id for item in self.state.findings[5:10]],
        )

    def test_bad_pagination_is_a_client_error(self) -> None:
        self.assertEqual(route(self.state, "/findings", {"limit": "abc"})[0], 400)
        self.assertEqual(route(self.state, "/findings", {"limit": "0"})[0], 400)
        self.assertEqual(route(self.state, "/findings", {"limit": "5000"})[0], 400)
        self.assertEqual(route(self.state, "/findings", {"offset": "-1"})[0], 400)

    def test_finding_detail_and_unknown_id(self) -> None:
        finding = self.state.findings[0]
        status, body = route(self.state, f"/findings/{finding.finding_id}")
        self.assertEqual(status, 200)
        self.assertEqual(body, route(self.state, "/findings", {
            "rule_id": finding.rule_id,
        })[1]["findings"][0])
        self.assertEqual(route(self.state, "/findings/DOES-NOT-EXIST")[0], 404)

    def test_evidence_resolves_supporting_records(self) -> None:
        finding = next(
            item for item in self.state.findings
            if item.rule_id == "missing_escalation"
        )
        status, body = route(
            self.state, f"/findings/{finding.finding_id}/evidence")
        self.assertEqual(status, 200)
        self.assertEqual(body["finding"]["finding_id"], finding.finding_id)
        self.assertEqual(body["unresolved_record_ids"], [])
        self.assertIn("cases", body["records"])
        self.assertIn("alerts", body["records"])
        resolved = {
            row[f"{kind[:-1]}_id"]
            for kind, rows in body["records"].items()
            for row in rows
            if kind != "cse"
        }
        self.assertTrue(set(finding.supporting_record_ids).issubset(resolved))

    def test_negative_space_evidence_is_asset_level(self) -> None:
        finding = next(
            item for item in self.state.findings
            if item.rule_id == "negative_space_low_activity"
        )
        status, body = route(
            self.state, f"/findings/{finding.finding_id}/evidence")
        self.assertEqual(status, 200)
        self.assertEqual(set(body["records"]), {"assets"})
        asset_ids = {row["asset_id"] for row in body["records"]["assets"]}
        self.assertEqual(asset_ids, set(finding.supporting_record_ids))

    def test_unknown_endpoint_is_404(self) -> None:
        self.assertEqual(route(self.state, "/nope")[0], 404)
        self.assertEqual(route(self.state, "/findings/x/extra")[0], 404)


class ApiServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = create_server("127.0.0.1", 0, quiet=True)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.thread.join(timeout=5)
        cls.server.server_close()

    def _get(self, path: str) -> tuple[int, dict]:
        with urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=10) as response:
            return response.status, json.loads(response.read().decode("utf-8"))

    def test_health_over_http(self) -> None:
        status, body = self._get("/health")
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")

    def test_findings_over_http_with_query(self) -> None:
        status, body = self._get("/findings?rule_id=negative_space_low_activity")
        self.assertEqual(status, 200)
        self.assertEqual(body["total"], 8)


if __name__ == "__main__":
    unittest.main()
