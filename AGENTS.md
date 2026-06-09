# AGENTS.md - d3hl_infra_crew

CrewAI orchestrator for d3HL infrastructure repos. This repo is application code and keeps its own harness state.

## Startup workflow

1. Confirm cwd with `pwd`; expected `/home/d3/Github/d3hl_infra_crew`.
2. Read `claude-progress.md`.
3. Read `feature_list.json` and pick the highest-priority unfinished feature.
4. Review `git log --oneline -5` when commits exist.
5. Run `./init.sh` before feature work.
6. Do not stack feature work on a failing baseline.

## Authority boundary

Default boundary is `plan_only`.

Allowed by default:
- Read repo harness files and git state.
- Run this repo's local static checks.
- Generate plan-only Terraform and Ansible guidance.
- Write local orchestrator output under `output/`.

Gated by explicit user approval:
- Running target repo `./init.sh` through the Flow.
- Credentialed `terraform plan` or Ansible check mode.
- Live reads against Proxmox, Red Hat Satellite, Cloudflare, registry, or network devices.

Not allowed by default:
- `terraform apply`.
- Live Proxmox mutation.
- Satellite lifecycle mutation.
- Registry/image push.
- Cloudflare DNS/tunnel mutation.
- Plaintext secrets in prompts, files, outputs, or logs.

## Implementation rules

- Use CrewAI Flow plus one sequential Crew first.
- Keep target repos authoritative for their own `AGENTS.md`, `feature_list.json`, `claude-progress.md`, `init.sh`, Terraform, and Ansible files.
- Do not centralize target repo state in this repo.
- Terraform owns provisioning. Ansible owns configuration. Bash is glue only. Python is allowed here only for the CrewAI app and deterministic adapters.
- Preserve `op://d3HLPRV/...` references as references only.

## Verification

Run:

```bash
./init.sh
```

The baseline compiles Python, validates YAML/JSON through unit tests, and runs `git diff --check` when inside a git worktree.
