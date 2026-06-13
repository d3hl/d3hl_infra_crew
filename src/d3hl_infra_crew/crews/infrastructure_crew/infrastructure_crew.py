from __future__ import annotations

import os

from crewai import Agent, Crew, LLM, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task

# Applied on import: restores the `human_input: true` checkpoint, which crashes
# in the pinned CrewAI 1.14.6. Must run before the crew kicks off and builds the
# experimental AgentExecutor. See d3hl_infra_crew/crewai_compat.py.
from d3hl_infra_crew import crewai_compat as _crewai_compat  # noqa: F401
from d3hl_infra_crew.tools import RepoStateTool, RepoWriteTool


DEFAULT_OPENROUTER_MODEL = "openrouter/deepseek/deepseek-v4-pro"
DEFAULT_MAX_TOKENS = 4096


def configured_llm() -> LLM | None:
    """Return the configured Crew LLM without exposing provider secrets."""
    model = (
        os.getenv("CREWAI_MODEL")
        or os.getenv("MODEL")
        or os.getenv("MODEL_NAME")
        or os.getenv("OPENAI_MODEL_NAME")
    )
    if not model and os.getenv("OPENROUTER_API_KEY"):
        model = DEFAULT_OPENROUTER_MODEL
    if not model:
        return None
    max_tokens = int(os.getenv("CREWAI_MAX_TOKENS", str(DEFAULT_MAX_TOKENS)))
    return LLM(model=model, max_tokens=max_tokens)


@CrewBase
class InfrastructureCrew:
    """d3HL infrastructure crew that drafts and applies real changes to target repos."""

    agents: list[BaseAgent]
    tasks: list[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def repo_state_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["repo_state_analyst"],  # type: ignore[index]
            llm=configured_llm(),
            tools=[RepoStateTool()],
        )

    @agent
    def infrastructure_provisioning_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["infrastructure_provisioning_agent"],  # type: ignore[index]
            llm=configured_llm(),
            tools=[RepoWriteTool()],
        )

    @agent
    def qa_contract_guardian(self) -> Agent:
        return Agent(
            config=self.agents_config["qa_contract_guardian"],  # type: ignore[index]
            llm=configured_llm(),
        )

    @task
    def discover_repo_state(self) -> Task:
        return Task(config=self.tasks_config["discover_repo_state"])  # type: ignore[index]

    @task
    def classify_infra_request(self) -> Task:
        return Task(config=self.tasks_config["classify_infra_request"])  # type: ignore[index]

    @task
    def select_automation_path(self) -> Task:
        return Task(config=self.tasks_config["select_automation_path"])  # type: ignore[index]

    @task
    def draft_candidate_plan(self) -> Task:
        return Task(config=self.tasks_config["draft_candidate_plan"])  # type: ignore[index]

    @task
    def review_candidate_plan(self) -> Task:
        return Task(config=self.tasks_config["review_candidate_plan"])  # type: ignore[index]

    @task
    def apply_changes(self) -> Task:
        return Task(config=self.tasks_config["apply_changes"])  # type: ignore[index]

    @crew
    def crew(self) -> Crew:
        """Create the infrastructure crew."""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
