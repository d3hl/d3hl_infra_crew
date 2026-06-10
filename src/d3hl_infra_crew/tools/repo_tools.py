from __future__ import annotations

from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from d3hl_infra_crew.boundary import evaluate_boundary
from d3hl_infra_crew.repo_state import collect_repo_state


class RepoStateInput(BaseModel):
    target_repo: str = Field(..., description="Repo alias or absolute path under /home/d3/Github.")
    run_static_checks: bool = Field(
        False,
        description=(
            "Ignored for agent safety. Target repo ./init.sh can only be run by "
            "the Flow-controlled pre-inspection path after explicit approval."
        ),
    )


class RepoStateTool(BaseTool):
    name: str = "collect_repo_state"
    description: str = "Read a d3HL repo's harness state, git status, recent commits, and optional static baseline result."
    args_schema: Type[BaseModel] = RepoStateInput

    def _run(self, target_repo: str, run_static_checks: bool = False) -> str:
        return collect_repo_state(target_repo, run_static_checks=False).to_prompt_json()


class BoundaryInput(BaseModel):
    text: str = Field(..., description="Candidate handoff or plan to inspect.")
    allowed_boundary: str = Field("plan_only", description="Allowed authority boundary, normally plan_only.")


class BoundaryPolicyTool(BaseTool):
    name: str = "evaluate_plan_boundary"
    description: str = "Check candidate output for live mutation commands or plaintext secret patterns under the allowed boundary."
    args_schema: Type[BaseModel] = BoundaryInput

    def _run(self, text: str, allowed_boundary: str = "plan_only") -> str:
        return evaluate_boundary(text, allowed_boundary=allowed_boundary).to_text()
