import unittest
from app.demo import correction_demo_request, demo_group
from app.ledger import reconcile
from app.models import EventType, ExtractedEvent, ReconcileRequest

class LedgerTests(unittest.TestCase):
    def test_correction_supersedes_original_amount(self):
        report = reconcile(correction_demo_request())
        self.assertEqual(report.status, "reconciled")
        self.assertEqual(report.superseded_event_ids, ["evt-001"])
        self.assertEqual(len(report.entries), 1)
        self.assertEqual(report.entries[0].event_id, "evt-002")
        self.assertEqual(report.entries[0].amount, 20000)

    def test_low_confidence_requires_review(self):
        req = ReconcileRequest(group=demo_group(), events=[ExtractedEvent(id="evt-low", event_type=EventType.CONTRIBUTION, member_id="m-003", amount_minor=50000, currency="UGX", confidence=0.51, source_text="Mary: I think I paid fifty.")])
        report = reconcile(req)
        self.assertEqual(report.status, "needs_review")
        self.assertEqual(report.entries, [])
        self.assertEqual(report.exceptions[0].code, "low_confidence")

    def test_unknown_member_never_enters_ledger(self):
        req = ReconcileRequest(group=demo_group(), events=[ExtractedEvent(id="evt-unknown", event_type=EventType.CONTRIBUTION, member_id="m-999", amount_minor=40000, currency="UGX", confidence=0.99, source_text="Unknown speaker: forty thousand.")])
        report = reconcile(req)
        self.assertEqual(report.status, "needs_review")
        self.assertEqual(report.entries, [])
        self.assertEqual(report.exceptions[0].code, "unknown_member")

    def test_missing_correction_target_requires_review(self):
        req = ReconcileRequest(group=demo_group(), events=[ExtractedEvent(id="evt-c", event_type=EventType.CORRECTION, member_id="m-002", amount_minor=20000, currency="UGX", confidence=0.99, source_text="John: make that twenty.", supersedes_event_id="missing")])
        report = reconcile(req)
        self.assertEqual(report.status, "needs_review")
        self.assertTrue(any(x.code == "missing_superseded_event" for x in report.exceptions))

    def test_currency_mismatch_is_rejected(self):
        req = ReconcileRequest(group=demo_group(), events=[ExtractedEvent(id="evt-usd", event_type=EventType.CONTRIBUTION, member_id="m-001", amount_minor=20, currency="USD", confidence=0.99, source_text="Amina: twenty dollars.")])
        report = reconcile(req)
        self.assertEqual(report.status, "needs_review")
        self.assertEqual(report.entries, [])
        self.assertEqual(report.exceptions[0].code, "currency_mismatch")

if __name__ == '__main__':
    unittest.main()
