from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task

from d3hl_infra_crew.tools import BoundaryPolicyTool, RepoStateTool


@CrewBase
class InfrastructureCrew:
    """Plan-only d3HL infrastructure crew."""

    agents: list[BaseAgent]
    tasks: list[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def repo_state_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["repo_state_analyst"],  # type: ignore[index]
            tools=[RepoStateTool()],
        )

    @agent
    def infrastructure_provisioning_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["infrastructure_provisioning_agent"],  # type: ignore[index]
        )

    @agent
    def qa_contract_guardian(self) -> Agent:
        return Agent(
            config=self.agents_config["qa_contract_guardian"],  # type: ignore[index]
            tools=[BoundaryPolicyTool()],
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
    def validate_boundary(self) -> Task:
        return Task(config=self.tasks_config["validate_boundary"])  # type: ignore[index]

    @task
    def produce_handoff(self) -> Task:
        return Task(config=self.tasks_config["produce_handoff"])  # type: ignore[index]

    @crew
    def crew(self) -> Crew:
        """Create the infrastructure crew."""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
