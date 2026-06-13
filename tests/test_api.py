import json
import unittest
from unittest import mock

from fastapi.testclient import TestClient

from d3hl_infra_crew import api


def _fixture_snapshot():
    """A minimal object exposing to_prompt_json(), like RepoStateSnapshot."""
    payload = {
        "active_feature": {"id": "TF-001", "title": "Scaffold provisioning"},
        "baseline_command": "./init.sh",
        "path": "/home/d3/Github/d3hl-rhel-bootc-orchestrator",
        "blockers": [],
    }
    snapshot = mock.Mock()
    snapshot.to_prompt_json.return_value = json.dumps(payload)
    return snapshot


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(api.app)

    def test_healthz(self):
        resp = self.client.get("/healthz")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"status": "ok"})

    def test_run_returns_dry_run_handoff(self):
        with mock.patch.object(api, "collect_repo_state", return_value=_fixture_snapshot()) as collect:
            resp = self.client.post(
                "/run",
                json={"target_repo": "bootc", "infrastructure_request": "smoke"},
            )
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertEqual(body["target_repo"], "bootc")
        self.assertIn("# Infrastructure Handoff Dry Run", body["handoff"])
        self.assertIn("TF-001", body["handoff"])
        # Dry-run path is read-only: static checks are not forced on by the API.
        collect.assert_called_once()

    def test_run_rejects_out_of_workspace_target(self):
        with mock.patch.object(
            api,
            "collect_repo_state",
            side_effect=ValueError("target_repo must resolve under /home/d3/Github: /etc"),
        ):
            resp = self.client.post(
                "/run",
                json={"target_repo": "/etc", "infrastructure_request": "x"},
            )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("/home/d3/Github", resp.json()["detail"])


if __name__ == "__main__":
    unittest.main()
