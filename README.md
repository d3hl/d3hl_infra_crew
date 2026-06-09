# d3hl_infra_crew

Plan-only CrewAI orchestrator for the d3HL homelab infrastructure repos.

This repo contains a CrewAI Flow that wraps one sequential infrastructure Crew. It reads target repo harness state, classifies the request, selects a Terraform/Ansible automation path, drafts a candidate plan, checks the plan-only boundary, and writes a local handoff under `output/`.

## Target repos

Default aliases:

| Alias | Path | Purpose |
| --- | --- | --- |
| `bootc` | `/home/d3/Github/d3hl-rhel-bootc-orchestrator` | RHEL image-mode / bootc orchestration |
| `cf-controller` | `/home/d3/Github/cf-controller` | Cloudflare mesh / controller |
| `proxmox` | `/home/d3/Github/d3hl-managed-proxmox` | Homelab network / Proxmox SDN |
| `agent-contract` | `/home/d3/Github/agent-contract-master` | Shared contract reference |

Target repos remain authoritative for their own `AGENTS.md`, `feature_list.json`, `claude-progress.md`, `init.sh`, Terraform, and Ansible files.

## Boundary

Default authority is `plan_only`.

Allowed by default:

- Read target repo files and git state.
- Generate plan-only Terraform and Ansible guidance.
- Save local output under `output/`.

Explicitly gated:

- Target repo `./init.sh` execution.
- Credentialed `terraform plan` or Ansible check mode.
- Live reads from Proxmox, Satellite, Cloudflare, registries, or network devices.

Not default:

- `terraform apply`.
- Live Proxmox, Satellite, registry, DNS, tunnel, or network mutation.
- Plaintext secrets.

## Run

Install dependencies:

```bash
UV_CACHE_DIR=/tmp/uv-cache crewai install
```

Run a plan-only handoff with JSON trigger payload:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run run_with_trigger '{"target_repo":"bootc","infrastructure_request":"Design TF-001 Proxmox-first HCP Terraform provisioning","allowed_boundary":"plan_only"}'
```

The Flow writes the final handoff to `output/infrastructure_handoff.md`.

For an LLM-free end-to-end dry run of the Flow and repo-state adapter:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run run_with_trigger '{"target_repo":"bootc","infrastructure_request":"Dry-run active feature handoff","allowed_boundary":"plan_only","dry_run":true}'
```

## Verify

```bash
./init.sh
```

No OpenAI or other LLM key is required for local unit tests. Running the actual Crew requires an LLM provider key in the environment or ignored `.env` file.
