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
        self.assertIn("qa_contract_guardian", agents)
        self.assertIn("produce_handoff", tasks)
        for task_name, task in tasks.items():
            self.assertIn("agent", task, task_name)
            self.assertIn(task["agent"], agents, task_name)
            self.assertIn("expected_output", task, task_name)


if __name__ == "__main__":
    unittest.main()
