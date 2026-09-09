import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app import main
from app.store import LocalRunStore


CORRECTION_TRANSCRIPT = """Chair: Welcome everyone. Amina is here, John is here, Mary is here and Sarah is here.
Amina: I paid fifty thousand for my savings contribution.
John: I paid thirty thousand.
Mary: I am repaying forty thousand on my loan.
Sarah: I would like to request a loan of one hundred thousand for one month.
John: Actually, correct my contribution. Make that twenty thousand, not thirty.
Chair: Noted. We will review Sarah's request before approving it."""

AMBIGUOUS_TRANSCRIPT = """Chair: Mary, can you confirm your contribution?
Mary: Maybe I paid fifty thousand, I am not sure.
Chair: We will check the receipt before recording the final amount."""


class ApiIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "runs.sqlite3"
        main._demo_store = LocalRunStore(self.db_path)
        self.client = TestClient(main.app)

    def tearDown(self):
        self.client.close()
        self.tempdir.cleanup()

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_correction_meeting_completes_end_to_end(self):
        response = self.client.post(
            "/api/v1/demo/process",
            json={"transcript": CORRECTION_TRANSCRIPT},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["reconciliation"]["status"], "reconciled")
        self.assertTrue(data["artifacts_finalized"])
        self.assertEqual(len(data["reconciliation"]["exceptions"]), 0)

        entries = data["reconciliation"]["entries"]
        accepted = {
            (entry["member_id"], entry["event_type"], entry["amount"])
            for entry in entries
        }
        self.assertIn(("m-001", "contribution", 50000), accepted)
        self.assertIn(("m-002", "contribution", 20000), accepted)
        self.assertIn(("m-003", "loan_repayment", 40000), accepted)
        self.assertFalse(any(entry["event_type"] == "loan_request" for entry in entries))

        self.assertEqual(len(data["receipts"]), 3)
        self.assertEqual(len(data["follow_up_actions"]), 1)
        self.assertEqual(data["follow_up_actions"][0]["amount"], 100000)
        self.assertGreaterEqual(len(data["reconciliation"]["superseded_event_ids"]), 1)

        run_id = data["run_id"]

        listed = self.client.get("/api/v1/demo/runs")
        self.assertEqual(listed.status_code, 200)
        self.assertTrue(any(item["run_id"] == run_id for item in listed.json()))

        reopened = self.client.get(f"/api/v1/demo/runs/{run_id}")
        self.assertEqual(reopened.status_code, 200)
        self.assertTrue(reopened.json()["artifacts_finalized"])

    def test_ambiguous_meeting_blocks_then_resumes_and_survives_restart(self):
        response = self.client.post(
            "/api/v1/demo/process",
            json={"transcript": AMBIGUOUS_TRANSCRIPT},
        )
        self.assertEqual(response.status_code, 200)
        blocked = response.json()

        self.assertEqual(blocked["reconciliation"]["status"], "needs_review")
        self.assertFalse(blocked["artifacts_finalized"])
        self.assertEqual(blocked["receipts"], [])
        self.assertEqual(len(blocked["reconciliation"]["exceptions"]), 1)

        run_id = blocked["run_id"]
        event_id = blocked["reconciliation"]["exceptions"][0]["event_id"]

        resolved_response = self.client.post(
            "/api/v1/demo/resolve",
            json={
                "run_id": run_id,
                "event_id": event_id,
                "action": "confirm",
                "amount_minor": 50000,
            },
        )
        self.assertEqual(resolved_response.status_code, 200)
        resolved = resolved_response.json()

        self.assertEqual(resolved["reconciliation"]["status"], "reconciled")
        self.assertTrue(resolved["artifacts_finalized"])
        self.assertEqual(len(resolved["reconciliation"]["exceptions"]), 0)
        self.assertIn(event_id, resolved["resolved_event_ids"])
        self.assertEqual(len(resolved["receipts"]), 1)
        self.assertEqual(resolved["receipts"][0]["amount"], 50000)

        # Simulate a backend restart by constructing a new store over the same DB.
        main._demo_store = LocalRunStore(self.db_path)
        reopened = self.client.get(f"/api/v1/demo/runs/{run_id}")
        self.assertEqual(reopened.status_code, 200)
        after_restart = reopened.json()

        self.assertEqual(after_restart["reconciliation"]["status"], "reconciled")
        self.assertTrue(after_restart["artifacts_finalized"])
        self.assertIn(event_id, after_restart["resolved_event_ids"])
        self.assertEqual(after_restart["receipts"][0]["amount"], 50000)

    def test_recent_runs_limit_is_validated(self):
        response = self.client.get("/api/v1/demo/runs?limit=0")
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
