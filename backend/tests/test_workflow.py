import unittest

from app.workflow import create_demo_run, reconcile_demo_run, resolve_demo_event


AMBIGUOUS = """Chair: Mary, can you confirm your contribution?
Mary: Maybe I paid fifty thousand, I am not sure.
Chair: We will check the receipt before recording the final amount."""


class WorkflowResolutionTests(unittest.TestCase):
    def test_human_confirmation_resumes_and_reconciles(self):
        state = create_demo_run(AMBIGUOUS)
        initial = reconcile_demo_run(state)
        self.assertEqual(initial.status, "needs_review")
        self.assertEqual(len(initial.exceptions), 1)

        event_id = initial.exceptions[0].event_id
        final = resolve_demo_event(
            state,
            event_id=event_id,
            action="confirm",
            amount_minor=50000,
        )

        self.assertEqual(final.status, "reconciled")
        self.assertEqual(len(final.exceptions), 0)
        self.assertEqual(len(final.entries), 1)
        self.assertEqual(final.entries[0].amount, 50000)
        self.assertIn(event_id, state.resolved_event_ids)

    def test_human_can_discard_ambiguous_event(self):
        state = create_demo_run(AMBIGUOUS)
        initial = reconcile_demo_run(state)
        event_id = initial.exceptions[0].event_id

        final = resolve_demo_event(state, event_id=event_id, action="discard")

        self.assertEqual(final.status, "reconciled")
        self.assertEqual(final.entries, [])
        self.assertIn(event_id, state.discarded_event_ids)
        self.assertIn(event_id, state.resolved_event_ids)

    def test_event_without_exception_cannot_be_human_overridden(self):
        state = create_demo_run("Amina: I paid fifty thousand for my savings contribution.")
        report = reconcile_demo_run(state)
        self.assertEqual(report.status, "reconciled")

        event_id = state.extraction.events[0].id
        with self.assertRaisesRegex(ValueError, "does not currently require human review"):
            resolve_demo_event(
                state,
                event_id=event_id,
                action="confirm",
                amount_minor=100000,
            )


if __name__ == "__main__":
    unittest.main()
