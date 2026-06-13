"""FastAPI service exposing the orchestrator's deterministic dry-run path.

Dry-run only by design: this endpoint reads a target repo's state and returns the
rendered handoff. It never starts the Crew/LLM and never writes into a target repo.
Live, writing runs stay on the CLI (`run_with_trigger`) where the `apply_changes`
human-review checkpoint can prompt on a TTY.
"""

from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from d3hl_infra_crew.main import render_dry_run_handoff
from d3hl_infra_crew.repo_state import collect_repo_state


class RunRequest(BaseModel):
    target_repo: str = Field(..., description="Repo alias or absolute path under /home/d3/Github.")
    infrastructure_request: str = Field(
        "Produce a dry-run infrastructure handoff for the active feature.",
        description="The infrastructure request to classify and plan.",
    )
    run_static_checks: bool = Field(
        False,
        description="Run the target repo ./init.sh during inspection (read-only build/test baseline).",
    )


class RunResponse(BaseModel):
    target_repo: str
    handoff: str


def create_app() -> FastAPI:
    app = FastAPI(
        title="d3hl_infra_crew",
        description="Dry-run-only HTTP surface for the d3HL infrastructure orchestrator.",
        version="0.1.0",
    )

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/run", response_model=RunResponse)
    def run(request: RunRequest) -> RunResponse:
        try:
            snapshot = collect_repo_state(
                request.target_repo,
                run_static_checks=request.run_static_checks,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        handoff = render_dry_run_handoff(
            target_repo=request.target_repo,
            infrastructure_request=request.infrastructure_request,
            repo_state=snapshot.to_prompt_json(),
        )
        return RunResponse(target_repo=request.target_repo, handoff=handoff)

    return app


app = create_app()


def serve() -> None:
    import uvicorn

    uvicorn.run(
        app,
        host=os.getenv("D3HL_API_HOST", "127.0.0.1"),
        port=int(os.getenv("D3HL_API_PORT", "8000")),
    )
