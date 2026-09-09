import unittest

from app.artifacts import generate_completion_artifacts
from app.workflow import create_demo_run, reconcile_demo_run, resolve_demo_event


CLEAN = """Chair: Welcome everyone. Amina is here, John is here, Mary is here and Sarah is here.
Amina: I paid fifty thousand for my savings contribution.
John: I paid thirty thousand.
Mary: I am repaying forty thousand on my loan.
Sarah: I would like to request a loan of one hundred thousand for one month.
John: Actually, correct my contribution. Make that twenty thousand, not thirty.
Chair: Noted. We will review Sarah's request before approving it."""

AMBIGUOUS = """Chair: Mary, can you confirm your contribution?
Mary: Maybe I paid fifty thousand, I am not sure.
Chair: We will check the receipt before recording the final amount."""


class CompletionArtifactTests(unittest.TestCase):
    def test_clean_run_finalizes_receipts_and_follow_up(self):
        state = create_demo_run(CLEAN)
        report = reconcile_demo_run(state)
        artifacts = generate_completion_artifacts(state, report)

        self.assertTrue(artifacts.finalized)
        self.assertEqual(len(artifacts.receipts), 3)
        self.assertEqual(sorted(r.amount for r in artifacts.receipts), [20000, 40000, 50000])
        john = next(r for r in artifacts.receipts if r.member_name == "John")
        self.assertEqual(john.amount, 20000)
        self.assertEqual(john.event_type.value, "contribution")
        self.assertEqual(len(artifacts.follow_up_actions), 1)
        self.assertIn("Sarah", artifacts.follow_up_actions[0].title)
        self.assertEqual(artifacts.follow_up_actions[0].amount, 100000)

    def test_review_run_blocks_final_outputs(self):
        state = create_demo_run(AMBIGUOUS)
        report = reconcile_demo_run(state)
        artifacts = generate_completion_artifacts(state, report)

        self.assertFalse(artifacts.finalized)
        self.assertEqual(artifacts.receipts, [])
        self.assertEqual(artifacts.follow_up_actions, [])
        self.assertEqual(artifacts.audit_log[-1].stage, "outputs_blocked")

    def test_human_resolution_finalizes_and_is_audited(self):
        state = create_demo_run(AMBIGUOUS)
        initial = reconcile_demo_run(state)
        event_id = initial.exceptions[0].event_id
        final = resolve_demo_event(state, event_id=event_id, action="confirm", amount_minor=50000)
        artifacts = generate_completion_artifacts(state, final)

        self.assertTrue(artifacts.finalized)
        self.assertEqual(len(artifacts.receipts), 1)
        self.assertEqual(artifacts.receipts[0].member_name, "Mary")
        self.assertTrue(any(r.actor == "human" and r.event_id == event_id for r in artifacts.audit_log))
        self.assertEqual(artifacts.audit_log[-1].stage, "outputs_finalized")


if __name__ == "__main__":
    unittest.main()
