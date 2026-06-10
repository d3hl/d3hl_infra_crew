# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A **plan-only CrewAI orchestrator** for the d3HL homelab infrastructure repos. It is a CrewAI Flow wrapping one sequential Crew: it reads a target repo's harness state, classifies an infrastructure request, picks a Terraform/Ansible automation path, drafts a plan-only candidate, runs a boundary check, and writes a handoff to `output/`. The runtime lives here; the target repos stay authoritative for their own files.

## Authority boundary (read before doing anything)

Default authority is `plan_only`. This is the central design constraint, enforced both by the agents' prompts and by deterministic regex in [boundary.py](src/d3hl_infra_crew/boundary.py).

- **Allowed**: read target repo files/git state, run this repo's local static checks (`./init.sh`), generate plan-only Terraform/Ansible guidance, write under `output/`.
- **Gated (needs explicit user approval)**: running a *target* repo's `./init.sh` (the `run_static_checks` flag), credentialed `terraform plan` / Ansible check mode, live reads against Proxmox / Satellite / Cloudflare / registries / network devices.
- **Never by default**: `terraform apply`/`destroy`, any live infra mutation, plaintext secrets. `op://d3HLPRV/...` strings are kept as references only — never resolve them.

`evaluate_boundary()` scans generated text for live-mutation command patterns and plaintext-secret patterns; a failing check appends "Boundary Findings" to the handoff rather than blocking the write. Do not weaken these patterns to make output pass.

## Commands

All commands need `UV_CACHE_DIR=/tmp/uv-cache` (the sandbox default; `init.sh` sets it automatically).

```bash
# Install deps
UV_CACHE_DIR=/tmp/uv-cache crewai install

# Full static baseline: required-files check, python compile, unit tests, git whitespace
./init.sh

# Run unit tests directly (no LLM key needed)
uv run python -m unittest discover -s tests

# Run a single test
uv run python -m unittest tests.test_boundary
uv run python -m unittest tests.test_boundary.BoundaryTests.test_<name>

# LLM provider (required for live Crew runs only — not needed for dry_run or unit tests)
# OPENROUTER_API_KEY=<key>   # place in .env (gitignored)

# Real Crew run (requires OPENROUTER_API_KEY in env or .env)
uv run run_with_trigger '{"target_repo":"bootc","infrastructure_request":"...","allowed_boundary":"plan_only"}'

# LLM-free dry run — exercises trigger parsing, repo-state adapter, handoff render, boundary check, output write
uv run run_with_trigger '{"target_repo":"bootc","infrastructure_request":"...","allowed_boundary":"plan_only","dry_run":true}'
```

`dry_run:true` is the primary way to verify changes without an LLM key. It takes a deterministic code path in `run_with_trigger` (see below) that never starts the CrewAI event loop.

Console-script entry points (`pyproject.toml`): `kickoff` / `run_crew` (aliases to the same function), `plot`, `run_with_trigger`.

## Architecture

The pipeline is a CrewAI **Flow** (orchestration) wrapping a CrewAI **Crew** (the LLM agents). Code path:

1. **[main.py](src/d3hl_infra_crew/main.py)** — `InfrastructureFlow` with four `@listen`-chained steps: `collect_inputs` → `inspect_repo` → `run_infrastructure_crew` → `save_handoff`. State is the `InfrastructureState` pydantic model. Trigger input arrives as `crewai_trigger_payload`.
2. **[repo_state.py](src/d3hl_infra_crew/repo_state.py)** — deterministic, LLM-free adapter. `collect_repo_state()` resolves a target repo, reads `feature_list.json` / `claude-progress.md` / git state, selects the active feature (priority order: active → unfinished → blocked → first), and serializes a `RepoStateSnapshot.to_prompt_json()`. `resolve_repo()` enforces that every target path stays under `/home/d3/Github` — a hard security boundary; preserve it.
3. **[crews/infrastructure_crew/](src/d3hl_infra_crew/crews/infrastructure_crew/)** — `@CrewBase` class wiring three agents and six sequential tasks from YAML. Agents and tasks are defined in `config/agents.yaml` and `config/tasks.yaml`, not in Python; the Python file only binds tools.
4. **[boundary.py](src/d3hl_infra_crew/boundary.py)** — the regex policy gate described above.
5. **[tools/repo_tools.py](src/d3hl_infra_crew/tools/repo_tools.py)** — `RepoStateTool` and `BoundaryPolicyTool` expose the two adapters to agents as CrewAI tools.

**Sequential task pipeline**: `discover_repo_state` → `classify_infra_request` → `select_automation_path` → `draft_candidate_plan` → `validate_boundary` → `produce_handoff`.

**Agent/tool ownership** (intentional separation — tests assert it): `repo_state_analyst` owns `RepoStateTool`; `infrastructure_provisioning_agent` owns the three planning tasks (`classify_infra_request`, `select_automation_path`, `draft_candidate_plan`) and has *no* tools; `qa_contract_guardian` owns `BoundaryPolicyTool` and the final boundary/handoff tasks.

**Two execution paths in `run_with_trigger`**: when `dry_run` is true it inlines `collect_repo_state` + `render_dry_run_handoff` + write, fully bypassing CrewAI/the LLM. Otherwise it kicks off the real Flow. `render_dry_run_handoff()` in main.py is the deterministic template used by the dry-run path.

## Automation-path rules (encoded in tasks.yaml)

These are the rules the provisioning agent must follow, and the rationale for plans you generate: **Terraform owns provisioning** (VMs, Proxmox resources, Cloudflare, DNS, tunnels, networking). **Ansible owns configuration** (OS, packages, services, validation, day-2). **Bash is glue only.** Do not propose Python/custom API wrappers where a Terraform provider or Ansible module exists — Python is allowed in *this* repo only for the CrewAI app and deterministic adapters.

## Target repos

Aliases resolved by `repo_state.py` (`REPO_ALIASES`): `bootc` (d3hl-rhel-bootc-orchestrator), `cf`/`cloudflare` (cf-controller), `proxmox` (d3hl-managed-proxmox), `agent-contract` (agent-contract-master). Each keeps its own `AGENTS.md`, `feature_list.json`, `claude-progress.md`, `init.sh`, and IaC files. **Do not centralize target-repo state here.**

## Harness workflow (from AGENTS.md)

This repo runs its own feature-tracking harness. Before feature work: read `claude-progress.md`, pick the highest-priority unfinished feature in `feature_list.json`, run `./init.sh`, and don't stack work on a failing baseline. Verification evidence is required before marking a feature `passing`.

## Conventions

- Python is pinned to 3.13 via `.python-version`; `requires-python` is `>=3.10,<3.14`. uv and crewai need a supported interpreter.
- `output/` is gitignored — generated handoffs are local artifacts.
- New tasks must reference an existing agent and define `expected_output` (asserted by [tests/test_yaml_config.py](tests/test_yaml_config.py)).
- [scripts/debug_deploy_create.py](scripts/debug_deploy_create.py) logs deployment diagnostics (git origin, GitHub repo state, lockfile staleness) to `.cursor/debug-*.log` — useful when CrewAI deployment setup is failing.
