import tempfile
import time
import unittest
from pathlib import Path

from app.workflow import create_demo_run, resolve_demo_event
from app.store import LocalRunStore


AMBIGUOUS = """Chair: Mary, can you confirm your contribution?
Mary: Maybe I paid fifty thousand, I am not sure.
Chair: We will check the receipt before recording the final amount."""

CLEAN = """Amina: I paid fifty thousand for my savings contribution.
John: I paid thirty thousand.
John: Actually, correct my contribution. Make that twenty thousand, not thirty."""


class LocalRunStoreTests(unittest.TestCase):
    def make_store(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        return LocalRunStore(Path(temp.name) / "runs.sqlite3")

    def test_round_trip_preserves_structured_state(self):
        store = self.make_store()
        state = create_demo_run(CLEAN)
        store.save("run-1", state)

        restored = store.get("run-1")
        self.assertIsNotNone(restored)
        assert restored is not None
        self.assertEqual(restored.state.extraction.model_dump(), state.extraction.model_dump())
        self.assertEqual(restored.state.group.model_dump(), state.group.model_dump())

    def test_human_resolution_survives_reload(self):
        store = self.make_store()
        state = create_demo_run(AMBIGUOUS)
        store.save("run-review", state)

        loaded = store.get("run-review")
        assert loaded is not None
        event_id = loaded.state.extraction.events[0].id
        resolve_demo_event(
            loaded.state,
            event_id=event_id,
            action="confirm",
            amount_minor=50000,
        )
        store.save("run-review", loaded.state)

        restored = store.get("run-review")
        assert restored is not None
        self.assertIn(event_id, restored.state.resolved_event_ids)
        self.assertEqual(restored.state.extraction.events[0].confidence, 1.0)

    def test_recent_runs_are_ordered_by_latest_update(self):
        store = self.make_store()
        store.save("older", create_demo_run(CLEAN))
        time.sleep(0.002)
        store.save("newer", create_demo_run(AMBIGUOUS))

        records = store.list_runs()
        self.assertEqual([record.run_id for record in records[:2]], ["newer", "older"])


if __name__ == "__main__":
    unittest.main()
