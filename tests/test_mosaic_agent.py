import tempfile
import json
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from src.agent import MosaicSpendIntelligenceAgent
from src.live_agent import make_handler, run_live_request
from src.tools import detect_price_variance, load_data, enrich_purchase_orders


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"


class MosaicSpendIntelligenceTests(unittest.TestCase):
    def test_parser_extracts_category_location_and_threshold(self):
        agent = MosaicSpendIntelligenceAgent(data_dir=str(DATA_DIR))

        constraints = agent.parse_request(
            "Analyze Produce at Remote Campus E for price variance over 15% and disruption risk."
        )

        self.assertEqual(constraints["category"], "Produce")
        self.assertEqual(constraints["location"], "Remote Campus E")
        self.assertEqual(constraints["price_variance_threshold"], 0.15)
        self.assertIn("supplier_risk", constraints["focus"])
        self.assertIn("savings", constraints["focus"])

    def test_load_data_reports_missing_required_files(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            with self.assertRaises(FileNotFoundError) as context:
                load_data(tmp_dir)

        self.assertIn("purchase_orders.csv", str(context.exception))
        self.assertIn("disruptions.csv", str(context.exception))

    def test_price_variance_detector_respects_threshold_and_sort_order(self):
        tables = load_data(str(DATA_DIR))
        enriched = enrich_purchase_orders(tables)
        protein = enriched[enriched["category"] == "Protein"]

        variance = detect_price_variance(protein, threshold=0.20)

        self.assertFalse(variance.empty)
        self.assertTrue((variance["price_variance_pct"] > 0.20).all())
        savings = variance["potential_savings"].tolist()
        self.assertEqual(savings, sorted(savings, reverse=True))

    def test_demo_request_returns_grounded_procurement_recommendation(self):
        agent = MosaicSpendIntelligenceAgent(data_dir=str(DATA_DIR))

        result = agent.run(
            """
            Analyze Protein spend for price variance over 20%, maverick spend,
            supplier risk, and substitution opportunities. Prefer reliable suppliers
            and include diverse supplier opportunities when comparable.
            """,
            use_llm=False,
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["llm_status"], "offline_deterministic_narrative")
        self.assertEqual(result["constraints"]["category"], "Protein")
        self.assertEqual(result["tool_results"]["savings_summary"]["total_spend"], 450111.95)
        self.assertEqual(
            result["tool_results"]["supplier_scorecard_top10"][0]["supplier_name"],
            "Emergency Food Brokerage",
        )
        self.assertIn("synthetic procurement spend", result["operator_summary"])
        self.assertTrue(result["tool_results"]["substitution_recommendations"])

    def test_live_request_rejects_empty_input(self):
        agent = MosaicSpendIntelligenceAgent(data_dir=str(DATA_DIR))

        with self.assertRaises(ValueError):
            run_live_request(agent, "   ")

    def test_http_ask_endpoint_returns_agent_result(self):
        agent = MosaicSpendIntelligenceAgent(data_dir=str(DATA_DIR))
        handler = make_handler(agent)
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            url = f"http://127.0.0.1:{server.server_port}/ask"
            payload = json.dumps({"request": "Analyze Protein spend over 20% price variance."}).encode(
                "utf-8"
            )
            request = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with urllib.request.urlopen(request, timeout=5) as response:
                status = response.status
                body = json.loads(response.read().decode("utf-8"))

            self.assertEqual(status, 200)
            self.assertEqual(body["status"], "success")
            self.assertEqual(body["constraints"]["category"], "Protein")
            self.assertIn("operator_summary", body)
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
