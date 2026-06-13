import tempfile
import unittest
from pathlib import Path
from unittest import mock

from d3hl_infra_crew.tools.repo_tools import RepoWriteTool


class RepoWriteToolTests(unittest.TestCase):
    def test_writes_file_into_target_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "target-repo"
            repo.mkdir()
            with mock.patch(
                "d3hl_infra_crew.tools.repo_tools.resolve_repo",
                return_value=repo,
            ):
                result = RepoWriteTool()._run(
                    target_repo="target-repo",
                    relative_path="terraform/main.tf",
                    content="# generated\n",
                )
            written = repo / "terraform" / "main.tf"
            self.assertTrue(written.exists())
            self.assertEqual(written.read_text(encoding="utf-8"), "# generated\n")
            self.assertIn(str(written), result)

    def test_rejects_path_escaping_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "target-repo"
            repo.mkdir()
            with mock.patch(
                "d3hl_infra_crew.tools.repo_tools.resolve_repo",
                return_value=repo,
            ):
                result = RepoWriteTool()._run(
                    target_repo="target-repo",
                    relative_path="../escape.tf",
                    content="x",
                )
            self.assertIn("rejected", result)
            self.assertFalse((repo.parent / "escape.tf").exists())


if __name__ == "__main__":
    unittest.main()
