"""Tests for the CrewAI human_input compatibility shim.

These guard against the CrewAI 1.14.6 regression where the experimental,
Flow-based AgentExecutor does not expose ``ask_for_human_input`` as the flat
attribute its human-input provider requires, crashing every ``human_input: true``
task (including ``apply_changes``, the only file-writing task).
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from d3hl_infra_crew.crewai_compat import apply_crewai_human_input_patch


class CrewAIHumanInputPatchTests(unittest.TestCase):
    def test_patch_reports_applied(self) -> None:
        # Importing the package already applied it; calling again is idempotent.
        self.assertTrue(apply_crewai_human_input_patch())

    def test_executor_exposes_property(self) -> None:
        from crewai.experimental.agent_executor import AgentExecutor

        self.assertIsInstance(
            AgentExecutor.__dict__.get("ask_for_human_input")
            or getattr(AgentExecutor, "ask_for_human_input"),
            property,
        )

    def test_property_proxies_get_and_set_to_state(self) -> None:
        from crewai.experimental.agent_executor import AgentExecutor

        prop = AgentExecutor.ask_for_human_input
        # Stand-in with the same `.state.ask_for_human_input` shape the provider
        # relies on; avoids constructing a full pydantic executor.
        stub = SimpleNamespace(state=SimpleNamespace(ask_for_human_input=True))

        self.assertTrue(prop.fget(stub))

        prop.fset(stub, False)
        self.assertFalse(stub.state.ask_for_human_input)

        prop.fset(stub, "truthy")  # provider may pass non-bools; we coerce.
        self.assertIs(stub.state.ask_for_human_input, True)


if __name__ == "__main__":
    unittest.main()
