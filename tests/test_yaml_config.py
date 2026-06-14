import unittest
from pathlib import Path

import yaml


class YamlConfigTests(unittest.TestCase):
    def test_agents_and_tasks_yaml_parse(self):
        root = Path(__file__).resolve().parents[1]
        config_dir = root / "src" / "d3hl_infra_crew" / "crews" / "infrastructure_crew" / "config"
        agents = yaml.safe_load((config_dir / "agents.yaml").read_text(encoding="utf-8"))
        tasks = yaml.safe_load((config_dir / "tasks.yaml").read_text(encoding="utf-8"))
        self.assertIn("repo_state_analyst", agents)
        self.assertIn("infrastructure_provisioning_agent", agents)
        self.assertIn("qa_contract_guardian", agents)
        self.assertIn("apply_changes", tasks)
        self.assertNotIn("validate_boundary", tasks)
        self.assertNotIn("terraform_provisioning_architect", agents)
        self.assertNotIn("ansible_configuration_architect", agents)
        self.assertNotIn("platform_lifecycle_specialist", agents)
        for task_name, task in tasks.items():
            self.assertIn("agent", task, task_name)
            self.assertIn(task["agent"], agents, task_name)
            self.assertIn("expected_output", task, task_name)

    def test_provisioning_agent_owns_planning_tasks(self):
        root = Path(__file__).resolve().parents[1]
        config_dir = root / "src" / "d3hl_infra_crew" / "crews" / "infrastructure_crew" / "config"
        tasks = yaml.safe_load((config_dir / "tasks.yaml").read_text(encoding="utf-8"))
        for task_name in ("classify_infra_request", "select_automation_path", "draft_candidate_plan"):
            self.assertEqual(tasks[task_name]["agent"], "infrastructure_provisioning_agent")

    def test_hcp_terraform_context_is_referenced_by_planning_tasks(self):
        root = Path(__file__).resolve().parents[1]
        config_dir = root / "src" / "d3hl_infra_crew" / "crews" / "infrastructure_crew" / "config"
        tasks = yaml.safe_load((config_dir / "tasks.yaml").read_text(encoding="utf-8"))
        for task_name in (
            "classify_infra_request",
            "select_automation_path",
            "draft_candidate_plan",
            "review_candidate_plan",
        ):
            self.assertIn("{hcp_terraform_context}", tasks[task_name]["description"])

    def test_planning_tasks_prefer_bpg_proxmox_provider(self):
        root = Path(__file__).resolve().parents[1]
        config_dir = root / "src" / "d3hl_infra_crew" / "crews" / "infrastructure_crew" / "config"
        tasks = yaml.safe_load((config_dir / "tasks.yaml").read_text(encoding="utf-8"))
        for task_name in ("select_automation_path", "draft_candidate_plan"):
            self.assertIn("bpg/proxmox", tasks[task_name]["description"], task_name)

    def test_apply_task_writes_headless_and_has_no_boundary_language(self):
        root = Path(__file__).resolve().parents[1]
        config_dir = root / "src" / "d3hl_infra_crew" / "crews" / "infrastructure_crew" / "config"
        agents = yaml.safe_load((config_dir / "agents.yaml").read_text(encoding="utf-8"))
        tasks = yaml.safe_load((config_dir / "tasks.yaml").read_text(encoding="utf-8"))
        # apply_changes must run headless: human_input gates the write behind a TTY
        # approval pass that never fires in cloud/headless runs, so the files are
        # never written. The plan is reviewed by review_candidate_plan instead.
        self.assertFalse(tasks["apply_changes"].get("human_input"))
        self.assertIn("write_repo_file", tasks["apply_changes"]["description"])
        combined = yaml.safe_dump(agents) + yaml.safe_dump(tasks)
        for token in ("plan_only", "live_read_check", "live_apply_gated", "allowed_boundary"):
            self.assertNotIn(token, combined)


if __name__ == "__main__":
    unittest.main()
