import json
import unittest

from d3hl_infra_crew.hcp_terraform import hcp_terraform_support_context
from d3hl_infra_crew.main import render_dry_run_handoff


class HcpTerraformTests(unittest.TestCase):
    def test_support_context_prefers_bpg_proxmox_provider(self):
        context = hcp_terraform_support_context()
        self.assertIn("bpg/proxmox", context)

    def test_dry_run_handoff_includes_hcp_terraform_guidance(self):
        repo_state = {
            "active_feature": {
                "id": "TF-001",
                "title": "Scaffold HCP Terraform Proxmox-first provisioning contract",
            },
            "baseline_command": "./init.sh",
            "path": "/home/d3/Github/d3hl-rhel-bootc-orchestrator",
            "blockers": [],
        }
        handoff = render_dry_run_handoff(
            target_repo="bootc",
            infrastructure_request="Dry-run HCP Terraform support",
            repo_state=json.dumps(repo_state),
        )
        self.assertIn("## HCP Terraform Support", handoff)
        self.assertIn("organization, project, and workspace naming", handoff)
        self.assertIn("workspace environment variables or variable sets", handoff)
        self.assertIn(".terraformignore", handoff)
        self.assertIn("bpg/proxmox", handoff)
        self.assertIn("TF-001", handoff)


if __name__ == "__main__":
    unittest.main()
