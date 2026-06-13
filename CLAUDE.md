# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A **CrewAI orchestrator** for the d3HL homelab infrastructure repos that drafts and **writes real files into a target repo**. It is a CrewAI Flow wrapping one sequential Crew: it reads a target repo's harness state, classifies an infrastructure request, picks a Terraform/Ansible automation path, drafts a candidate, reviews it, and — after human review — writes the generated files into the target repo's working tree. The runtime lives here.

## Target-repo write mode (read before doing anything)

There is **no boundary/authority gate**. The old `plan_only` / `live_read_check` / `live_apply_gated` ladder and the `boundary.py` regex policy were removed deliberately so the crew can apply real changes. Consequences to be aware of:

- The crew writes real files into the target repo via the `write_repo_file` tool ([tools/repo_tools.py](src/d3hl_infra_crew/tools/repo_tools.py)); it can create or overwrite files.
- There is no automated secret-leak or mutation/teardown scanning. **Secrets rule (discipline, not an enforced gate):** reference every secret only as a `op://d3HLPRV/...` 1Password path — the single allowed way to refer to a secret in any prompt, generated file, handoff, output, or log. Never write a plaintext secret value and never resolve/expand an `op://d3HLPRV/...` path. In generated Terraform/Ansible, pass secrets through variables and workspace variable sets that map back to `op://d3HLPRV/...`, never hardcoded values.
- The **interactive checkpoint** is the `apply_changes` task's `human_input: true`: the live crew pauses for human review/approval before finalizing writes.
- The one retained safety is path containment: `resolve_repo()` keeps target paths under `/home/d3/Github` and `RepoWriteTool` rejects paths that escape the resolved repo. This is path-traversal safety, not an authority gate.

The `dry_run` path is LLM-free and **does not write into target repos** — it only renders a handoff to `output/` for inspection.

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
uv run python -m unittest tests.test_repo_write
uv run python -m unittest tests.test_yaml_config

# LLM provider (required for live Crew runs only — not needed for dry_run or unit tests)
# OPENROUTER_API_KEY=<key>   # place in .env (gitignored)

# Real Crew run — drafts and writes real files into the target repo, pausing for human review
uv run run_with_trigger '{"target_repo":"bootc","infrastructure_request":"..."}'

# LLM-free dry run — exercises trigger parsing, repo-state adapter, handoff render, output write.
# Does NOT write into the target repo.
uv run run_with_trigger '{"target_repo":"bootc","infrastructure_request":"...","dry_run":true}'
```

`dry_run:true` is the primary way to verify changes without an LLM key. It takes a deterministic code path in `run_with_trigger` (see below) that never starts the CrewAI event loop and never writes into target repos.

Console-script entry points (`pyproject.toml`): `kickoff` / `run_crew` (aliases to the same function), `plot`, `run_with_trigger`.

## Architecture

The pipeline is a CrewAI **Flow** (orchestration) wrapping a CrewAI **Crew** (the LLM agents). Code path:

1. **[main.py](src/d3hl_infra_crew/main.py)** — `InfrastructureFlow` with four `@listen`-chained steps: `collect_inputs` → `inspect_repo` → `run_infrastructure_crew` → `save_handoff`. State is the `InfrastructureState` pydantic model. Trigger input arrives as `crewai_trigger_payload`.
2. **[repo_state.py](src/d3hl_infra_crew/repo_state.py)** — deterministic, LLM-free adapter. `collect_repo_state()` resolves a target repo, reads `feature_list.json` / `claude-progress.md` / git state, selects the active feature (priority order: active → unfinished → blocked → first), and serializes a `RepoStateSnapshot.to_prompt_json()`. `resolve_repo()` enforces that every target path stays under `/home/d3/Github` — a hard security boundary; preserve it.
3. **[crews/infrastructure_crew/](src/d3hl_infra_crew/crews/infrastructure_crew/)** — `@CrewBase` class wiring three agents and six sequential tasks from YAML. Agents and tasks are defined in `config/agents.yaml` and `config/tasks.yaml`, not in Python; the Python file only binds tools.
4. **[tools/repo_tools.py](src/d3hl_infra_crew/tools/repo_tools.py)** — `RepoStateTool` (read target-repo state) and `RepoWriteTool` (`write_repo_file`: write real files into a target repo under `/home/d3/Github`).

**Sequential task pipeline**: `discover_repo_state` → `classify_infra_request` → `select_automation_path` → `draft_candidate_plan` → `review_candidate_plan` → `apply_changes` (interactive: `human_input: true`).

**Agent/tool ownership** (intentional separation — tests assert it): `repo_state_analyst` owns `RepoStateTool`; `infrastructure_provisioning_agent` owns the planning tasks plus `apply_changes` and holds `RepoWriteTool`; `qa_contract_guardian` is the change-reviewer (`review_candidate_plan`) and has *no* tools.

**Two execution paths in `run_with_trigger`**: when `dry_run` is true it inlines `collect_repo_state` + `render_dry_run_handoff` + write to `output/`, fully bypassing CrewAI/the LLM and never touching target repos. Otherwise it kicks off the real Flow, which runs the Crew and writes generated files into the target repo. `render_dry_run_handoff()` in main.py is the deterministic template used by the dry-run path.

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
