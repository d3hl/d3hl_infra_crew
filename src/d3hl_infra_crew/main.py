#!/usr/bin/env python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, ClassVar

from crewai.flow import Flow, listen, start
from pydantic import BaseModel, Field

from d3hl_infra_crew.crews.infrastructure_crew.infrastructure_crew import InfrastructureCrew
from d3hl_infra_crew.boundary import evaluate_boundary
from d3hl_infra_crew.repo_state import collect_repo_state


class InfrastructureState(BaseModel):
    target_repo: str = "bootc"
    infrastructure_request: str = "Produce a plan-only infrastructure handoff for the active feature."
    allowed_boundary: str = "plan_only"
    run_static_checks: bool = False
    repo_state: str = ""
    final_handoff: str = ""
    output_path: str = Field(default="output/infrastructure_handoff.md")
    dry_run: bool = False


class InfrastructureFlow(Flow[InfrastructureState]):
    """Stateful Flow that wraps the sequential d3HL infrastructure crew."""

    tracing: bool | None = False
    suppress_flow_events: bool = True
    _skip_auto_memory: ClassVar[bool] = True

    @start()
    def collect_inputs(self, crewai_trigger_payload: dict[str, Any] | None = None):
        print("Collecting infrastructure crew inputs")
        payload = crewai_trigger_payload or {}
        self.state.target_repo = str(payload.get("target_repo", self.state.target_repo))
        self.state.infrastructure_request = str(
            payload.get("infrastructure_request", payload.get("request", self.state.infrastructure_request))
        )
        self.state.allowed_boundary = str(payload.get("allowed_boundary", self.state.allowed_boundary))
        self.state.run_static_checks = bool(payload.get("run_static_checks", self.state.run_static_checks))
        self.state.dry_run = bool(payload.get("dry_run", self.state.dry_run))
        print(f"Target repo: {self.state.target_repo}")
        print(f"Boundary: {self.state.allowed_boundary}")
        print(f"Run static checks: {self.state.run_static_checks}")
        print(f"Dry run: {self.state.dry_run}")

    @listen(collect_inputs)
    def inspect_repo(self):
        print("Inspecting target repo harness state")
        snapshot = collect_repo_state(
            self.state.target_repo,
            run_static_checks=self.state.run_static_checks,
        )
        self.state.repo_state = snapshot.to_prompt_json()
        print("Repo inspection complete")

    @listen(inspect_repo)
    def run_infrastructure_crew(self):
        if self.state.dry_run:
            print("Rendering deterministic dry-run handoff")
            self.state.final_handoff = render_dry_run_handoff(
                target_repo=self.state.target_repo,
                infrastructure_request=self.state.infrastructure_request,
                allowed_boundary=self.state.allowed_boundary,
                repo_state=self.state.repo_state,
            )
            print("Dry-run handoff complete")
            return

        print("Running infrastructure crew")
        result = InfrastructureCrew().crew().kickoff(
            inputs={
                "target_repo": self.state.target_repo,
                "infrastructure_request": self.state.infrastructure_request,
                "allowed_boundary": self.state.allowed_boundary,
                "repo_state": self.state.repo_state,
            }
        )
        self.state.final_handoff = result.raw
        print("Infrastructure crew complete")

    @listen(run_infrastructure_crew)
    def save_handoff(self):
        output_path = Path(self.state.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.state.final_handoff, encoding="utf-8")
        print(f"Handoff saved to {output_path}")


def render_dry_run_handoff(
    target_repo: str,
    infrastructure_request: str,
    allowed_boundary: str,
    repo_state: str,
) -> str:
    state = json.loads(repo_state)
    active_feature = state.get("active_feature") or {}
    blockers = state.get("blockers") or []
    static_check = state.get("static_check")
    verification_status = "static checks were not requested"
    if static_check:
        verification_status = f"static check return code: {static_check.get('returncode')}"

    handoff = f"""# Infrastructure Handoff Dry Run

## Summary
Plan-only dry run for `{target_repo}`. Request: {infrastructure_request}

## Assumptions
- Allowed boundary is `{allowed_boundary}`.
- Target repo remains authoritative for its own harness files and infrastructure code.
- No target repo files were changed by this dry run.
- No live Proxmox, Satellite, Cloudflare, registry, or network mutation was attempted.

## Candidate Config
- Terraform remains the provisioning path for infrastructure, VM, DNS, tunnel, Cloudflare, and Proxmox-resource planning.
- Ansible remains the configuration and validation path for OS, packages, services, day-2 operations, and Satellite-adjacent lifecycle orchestration.
- Bash is limited to wrapper/glue commands.
- Python/custom API wrappers are rejected when Terraform providers or Ansible modules can express the work.

## Validation Commands
- Local orchestrator baseline: `./init.sh` from `/home/d3/Github/d3hl_infra_crew`.
- Target baseline command: `{state.get('baseline_command') or 'not available'}` from `{state.get('path')}`.
- Target verification status in this run: {verification_status}.

## Rollback Hints
- Delete local generated output under `output/` if the dry-run handoff is not needed.
- Do not update target repo `feature_list.json` or `claude-progress.md` until a real implementation and verification pass completes.

## Blockers
{chr(10).join(f'- {blocker}' for blocker in blockers) if blockers else '- None from repo-state adapter.'}

## Next Action
Start from feature `{active_feature.get('id', 'unknown')}` ({active_feature.get('title', 'unknown')}) in `{target_repo}` and keep the next action plan-only unless the user explicitly approves a higher boundary.
"""
    boundary = evaluate_boundary(handoff, allowed_boundary=allowed_boundary)
    if not boundary.passed:
        handoff += "\n## Boundary Findings\n" + "\n".join(f"- {finding}" for finding in boundary.findings) + "\n"
    return handoff


def kickoff():
    flow = InfrastructureFlow()
    flow.kickoff()


def plot():
    flow = InfrastructureFlow()
    flow.plot()


def run_with_trigger():
    import sys

    if len(sys.argv) < 2:
        raise Exception("No trigger payload provided. Provide a JSON object as the first argument.")

    try:
        trigger_payload = json.loads(sys.argv[1])
    except json.JSONDecodeError as exc:
        raise Exception("Invalid JSON trigger payload") from exc

    if bool(trigger_payload.get("dry_run", False)):
        target_repo = str(trigger_payload.get("target_repo", InfrastructureState().target_repo))
        infrastructure_request = str(
            trigger_payload.get(
                "infrastructure_request",
                trigger_payload.get("request", InfrastructureState().infrastructure_request),
            )
        )
        allowed_boundary = str(trigger_payload.get("allowed_boundary", InfrastructureState().allowed_boundary))
        run_static_checks = bool(trigger_payload.get("run_static_checks", False))
        output_path = Path(str(trigger_payload.get("output_path", InfrastructureState().output_path)))

        print("Collecting infrastructure crew inputs")
        print(f"Target repo: {target_repo}")
        print(f"Boundary: {allowed_boundary}")
        print(f"Run static checks: {run_static_checks}")
        print("Dry run: True")
        print("Inspecting target repo harness state")
        snapshot = collect_repo_state(target_repo, run_static_checks=run_static_checks)
        print("Repo inspection complete")
        print("Rendering deterministic dry-run handoff")
        handoff = render_dry_run_handoff(
            target_repo=target_repo,
            infrastructure_request=infrastructure_request,
            allowed_boundary=allowed_boundary,
            repo_state=snapshot.to_prompt_json(),
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(handoff, encoding="utf-8")
        print("Dry-run handoff complete")
        print(f"Handoff saved to {output_path}")
        return None

    flow = InfrastructureFlow()
    flow.kickoff({"crewai_trigger_payload": trigger_payload})
    return None


if __name__ == "__main__":
    kickoff()
