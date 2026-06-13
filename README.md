# d3hl_infra_crew

A CrewAI orchestrator for the d3HL homelab infrastructure repos that drafts and **writes real files into a target repo**.

This repo contains a CrewAI Flow that wraps one sequential infrastructure Crew. It reads target repo harness state, classifies the request through a consolidated infrastructure provisioning agent, selects an HCP Terraform/Ansible automation path, drafts a candidate, reviews it, and — after human review — writes the generated files into the target repo's working tree.

## Target repos

Default aliases:

| Alias | Path | Purpose |
| --- | --- | --- |
| `bootc` | `/home/d3/Github/d3hl-rhel-bootc-orchestrator` | RHEL image-mode / bootc orchestration |
| `cf-controller` | `/home/d3/Github/cf-controller` | Cloudflare mesh / controller |
| `proxmox` | `/home/d3/Github/d3hl-managed-proxmox` | Homelab network / Proxmox SDN |
| `agent-contract` | `/home/d3/Github/agent-contract-master` | Shared contract reference |

## Write mode

There is no authority/boundary gate. A live crew run writes real files into the target repo via the `write_repo_file` tool, pausing at the `apply_changes` `human_input` checkpoint for review.

- Path containment is retained: target paths resolve under `/home/d3/Github`, and writes that escape the resolved repo are rejected.
- The secrets rule is enforced at write time: `RepoWriteTool` refuses to write content with a plaintext secret. Reference every secret only as a `op://d3HLPRV/...` 1Password path; variable/`${...}`/`{{ ... }}` references are allowed.
- Mutation/teardown commands are not scanned — review changes at the interactive checkpoint and via the target repo's git status.

## HCP Terraform support

Generated handoffs include HCP Terraform planning guidance without contacting HCP Terraform:

- `terraform { cloud { ... } }` for HCP Terraform remote state and execution, not a backend block.
- Explicit organization, project, and workspace naming with placeholders until target repos record approved names.
- Workspace variables and variable sets for provider credentials and deployment inputs; no token values in `.tf` files.
- `.terraformignore` recommendations for CLI-driven uploads.
- For Proxmox, the `bpg/proxmox` provider with a pinned `required_providers` block.

## Run

Install dependencies:

```bash
UV_CACHE_DIR=/tmp/uv-cache crewai install
```

Real crew run (drafts and writes files into the target repo, pausing for human review; needs `OPENROUTER_API_KEY`):

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run run_with_trigger '{"target_repo":"bootc","infrastructure_request":"Design TF-001 Proxmox-first HCP Terraform provisioning"}'
```

LLM-free dry run (trigger parsing, repo-state adapter, handoff rendering, output writing; no target-repo writes):

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run run_with_trigger '{"target_repo":"bootc","infrastructure_request":"Dry-run active feature handoff","dry_run":true}'
```

## HTTP API / Docker (dry-run-only)

```bash
# Local (binds 127.0.0.1:8000; override with D3HL_API_HOST / D3HL_API_PORT)
UV_CACHE_DIR=/tmp/uv-cache uv run serve

# Containerized — reads the workspace read-only, no LLM key needed
docker compose up --build

curl localhost:8000/healthz
curl -X POST localhost:8000/run -H 'content-type: application/json' \
  -d '{"target_repo":"bootc","infrastructure_request":"plan VM provisioning"}'
```

The API exposes only the deterministic dry-run path: `POST /run` returns the rendered handoff and never starts the Crew/LLM or writes into a target repo. `docker-compose.yml` binds localhost and mounts `/home/d3/Github` read-only.

Published image (after merge to `main`): `ghcr.io/d3hl/d3hl_infra_crew:latest`.

## Verify

```bash
./init.sh
```

## CI

GitHub Actions on pull requests and pushes to `main`:

- **static** — installs uv, runs `./init.sh` (compile + unit tests).
- **docker-publish** — builds the Dockerfile, smoke-tests `GET /healthz`, and pushes to `ghcr.io/<owner>/d3hl_infra_crew:latest` on `main` only (PRs build but do not push).

No repo secrets are required for GHCR publish; the workflow uses `GITHUB_TOKEN` with `packages: write`.

No LLM key is required for local unit tests or dry runs. Running the actual Crew requires an LLM provider key in the environment or ignored `.env` file.
