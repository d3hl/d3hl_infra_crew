import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from d3hl_infra_crew.repo_state import collect_repo_state, select_active_feature


class RepoStateTests(unittest.TestCase):
    def test_selects_in_progress_feature_first(self):
        feature_list = {
            "features": [
                {"id": "DONE", "priority": 1, "status": "passing", "title": "done"},
                {"id": "ACTIVE", "priority": 5, "status": "in_progress", "title": "active"},
                {"id": "NEXT", "priority": 2, "status": "not_started", "title": "next"},
            ]
        }
        self.assertEqual(select_active_feature(feature_list).id, "ACTIVE")

    def test_selects_highest_priority_unfinished_when_no_active(self):
        feature_list = {
            "features": [
                {"id": "DONE", "priority": 1, "status": "completed", "name": "done"},
                {"id": "LATER", "priority": 3, "status": "not_started", "name": "later"},
                {"id": "NEXT", "priority": 2, "status": "not_started", "name": "next"},
            ]
        }
        self.assertEqual(select_active_feature(feature_list).id, "NEXT")

    def test_collect_repo_state_reads_fixture(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            repo = Path(tmp)
            (repo / "feature_list.json").write_text(json.dumps({
                "features": [
                    {"id": "F-1", "priority": 1, "status": "not_started", "title": "first"}
                ]
            }), encoding="utf-8")
            (repo / "claude-progress.md").write_text("# progress", encoding="utf-8")
            (repo / "init.sh").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            with patch("d3hl_infra_crew.repo_state.WORKSPACE_ROOT", repo.parent):
                snapshot = collect_repo_state(str(repo), run_static_checks=False)
            self.assertTrue(snapshot.exists)
            self.assertEqual(snapshot.active_feature.id, "F-1")
            self.assertEqual(snapshot.baseline_command, "./init.sh")
            self.assertNotIn("target repo has no", "\n".join(snapshot.blockers))


if __name__ == "__main__":
    unittest.main()
