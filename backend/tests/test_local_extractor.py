import unittest

from app.demo import demo_group
from app.ledger import reconcile
from app.local_extractor import extract_locally
from app.models import EventType, ReconcileRequest


TRANSCRIPT = """Chair: Welcome everyone. Amina is here, John is here, Mary is here and Sarah is here.
Amina: I paid fifty thousand for my savings contribution.
John: I paid thirty thousand.
Mary: I am repaying forty thousand on my loan.
Sarah: I would like to request a loan of one hundred thousand for one month.
John: Actually, correct my contribution. Make that twenty thousand, not thirty.
Chair: Noted. We will review Sarah's request before approving it.
"""


class LocalExtractorTests(unittest.TestCase):
    def test_full_demo_extracts_and_reconciles(self):
        extraction = extract_locally(TRANSCRIPT)
        self.assertGreaterEqual(len(extraction.events), 9)

        report = reconcile(ReconcileRequest(group=demo_group(), events=extraction.events))
        self.assertEqual(report.status, "reconciled")
        self.assertEqual(report.totals_by_type["contribution"], 70000)
        self.assertEqual(report.totals_by_type["loan_repayment"], 40000)
        self.assertNotIn("loan_request", report.totals_by_type)

        contribution_amounts = sorted(
            entry.amount for entry in report.entries
            if entry.event_type == EventType.CONTRIBUTION
        )
        self.assertEqual(contribution_amounts, [20000, 50000])

    def test_uncertain_phrase_is_escalated(self):
        extraction = extract_locally("Mary: Maybe I paid fifty thousand, I am not sure.")
        report = reconcile(ReconcileRequest(group=demo_group(), events=extraction.events))
        self.assertEqual(report.status, "needs_review")
        self.assertEqual(report.exceptions[0].code, "low_confidence")

    def test_chair_question_is_not_extracted_as_member_contribution(self):
        extraction = extract_locally(
            "Chair: Mary, can you confirm your contribution?\n"
            "Mary: Maybe I paid fifty thousand, I am not sure."
        )
        self.assertEqual(len(extraction.events), 1)
        self.assertEqual(extraction.events[0].member_id, "m-003")
        self.assertEqual(extraction.events[0].amount_minor, 50000)



if __name__ == "__main__":
    unittest.main()
