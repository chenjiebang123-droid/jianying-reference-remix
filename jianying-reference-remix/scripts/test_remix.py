"""Exercise source uniqueness, window/speed constraints and microsecond timing."""
import json
from pathlib import Path
import tempfile
import unittest

import remix


class ReviewedPlanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for name in ("a.mp4", "b.mp4"):
            (self.root/name).touch()

    def tearDown(self):
        self.tmp.cleanup()

    def prepare(self, shots):
        path = self.root/"plan.json"
        path.write_text(json.dumps({"projects":[{"name":"reference_1", "shots":shots}]}), encoding="utf-8")
        return remix.load_plan(path, "unused", probe_fn=lambda _: {"duration":4.0})[1][0]

    def shot(self, name="a.mp4", **extra):
        return {"source":name, "role":"demo", "reviewed":True, "action_complete":True,
                "action_notes":"Reviewed one complete wipe", **extra}

    def test_alias_of_same_source_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "repeated source"):
            self.prepare([self.shot(), self.shot("./a.mp4")])

    def test_action_review_and_source_bounds_are_required(self):
        with self.assertRaisesRegex(ValueError, "review"):
            self.prepare([self.shot(action_complete=False)])
        with self.assertRaisesRegex(ValueError, "Invalid source window"):
            self.prepare([self.shot(source_end=4.2)])
        with self.assertRaisesRegex(ValueError, "Speed"):
            self.prepare([self.shot(target_duration=1)])

    def test_reviewed_window_and_adjacent_timing(self):
        project = self.prepare([self.shot(source_start=0.2, source_end=3.2, target_duration=3.3333334),
                                self.shot("b.mp4", target_duration=3.3333334)])
        first, second = project["shots"]
        self.assertEqual(second["target_start_us"], first["target_duration_us"])
        self.assertEqual(project["duration_us"], 6666666)
        self.assertEqual(first["source_start"], 0.2)


if __name__ == "__main__":
    unittest.main()
