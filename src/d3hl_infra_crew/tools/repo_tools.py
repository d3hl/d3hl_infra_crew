from __future__ import annotations

from pathlib import Path
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from d3hl_infra_crew.repo_state import collect_repo_state, resolve_repo
from d3hl_infra_crew.secret_scan import find_plaintext_secrets


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


class RepoWriteInput(BaseModel):
    target_repo: str = Field(..., description="Repo alias or absolute path under /home/d3/Github.")
    relative_path: str = Field(..., description="File path within the target repo, e.g. terraform/main.tf.")
    content: str = Field(..., description="Full file content to write.")


class RepoWriteTool(BaseTool):
    name: str = "write_repo_file"
    description: str = (
        "Write a real file into a target repo's working tree under /home/d3/Github. "
        "Creates parent directories and overwrites existing files. Returns the absolute path written."
    )
    args_schema: Type[BaseModel] = RepoWriteInput

    def _run(self, target_repo: str, relative_path: str, content: str) -> str:
        repo = resolve_repo(target_repo)
        dest = (repo / relative_path).resolve()
        if not dest.is_relative_to(repo):
            return f"rejected: {relative_path} escapes target repo {repo}"
        secrets = find_plaintext_secrets(content)
        if secrets:
            return (
                f"rejected: possible plaintext secret in content for {relative_path}; "
                "reference secrets as op://d3HLPRV/... paths instead. Findings: "
                + "; ".join(secrets)
            )
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        return f"wrote {dest}"
