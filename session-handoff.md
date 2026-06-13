# d3hl_infra_crew session handoff

## Current feature

`CREW-008` - in progress (workflows implemented; GH Actions evidence pending first push to `main`).

## Verified state

- CrewAI Flow plus sequential infrastructure Crew implemented.
- Repo-state adapter reads target repo harness files and git state.
- `CREW-005` removed the boundary system entirely (boundary.py, the plan_only/live_read_check/live_apply_gated ladder, BoundaryPolicyTool, evaluate_boundary, allowed_boundary).
- `RepoWriteTool` (`write_repo_file`) added and bound to the provisioning agent; the crew writes real files into a target repo's working tree under `/home/d3/Github`.
- Task pipeline is now discover → classify → select → draft → review_candidate_plan → apply_changes; `apply_changes` is interactive (`human_input`).
- `resolve_repo` workspace containment and a RepoWriteTool path-escape guard are retained as path safety.
- `CREW-006`: `RepoWriteTool` enforces the secrets rule at write time via `secret_scan.find_plaintext_secrets()` (rejects plaintext secrets; allows op:// and variable/Jinja references). Mutation/teardown remain unguarded by design.
- `CREW-007`: dry-run-only FastAPI service (`api.py`: `/healthz`, `POST /run`) + `serve` script, Dockerfile, .dockerignore, docker-compose.yml (binds 127.0.0.1, read-only `/home/d3/Github` mount). `/run` reuses collect_repo_state + render_dry_run_handoff; never starts the Crew or writes target repos.
- `CREW-008`: `.github/workflows/static.yml` (setup-uv + `./init.sh`) and `.github/workflows/docker-publish.yml` (build, `/healthz` smoke, GHCR push on `main` only). `docker-compose.yml` uses `ghcr.io/d3hl/d3hl_infra_crew:latest`.
- LLM-free dry-run path writes `output/infrastructure_handoff.md` and does not write into target repos.
- 2026-06-13 `./init.sh` passed after CREW-008 workflow additions (31 unit tests).

## Write mode

There is no boundary gate. The live crew run drafts changes and writes real files into the target
repo via `write_repo_file`, pausing at the `apply_changes` `human_input` checkpoint for review.
`dry_run` is LLM-free and does not write into target repos. This is a deliberate, operator-approved
reversal of the original plan-only design; it diverges from agent-contract-master's plan-only
shared contract (that repo was not edited). Keep `op://d3HLPRV/...` as references by discipline.

## Next step

1. Commit and push CREW-008 to `main` (or open a PR and confirm `static` + `docker-publish` build jobs pass without push).
2. After merge, confirm `ghcr.io/d3hl/d3hl_infra_crew:latest` exists; append Actions run URL to `feature_list.json` evidence and mark `CREW-008` passing.
3. One-time: set GHCR package visibility under GitHub Packages.

For day-to-day use: `dry_run:true` (CLI) or `docker compose up` + `POST /run` for LLM-free inspection; set `OPENROUTER_API_KEY` for live write runs via CLI.
