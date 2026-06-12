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

Supported boundaries:
- `plan_only`: local repo-state inspection, plan-only guidance, and local output only.
- `live_read_check`: first live stage after explicit approval; permits live reads,
  target repo static checks, credentialed Terraform plans, and Ansible check mode
  only. It does not permit mutation or target repo state closeout.
- `live_apply_gated`: gated mutation stage. Permits approved create/update/apply
  actions only when each command carries an explicit operator-approved apply gate.
  Explicit teardown (Terraform/OpenTofu destroy, Proxmox/Satellite/Cloudflare/registry
  removal) stays blocked at every boundary, and plaintext secrets stay prohibited.

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
- Target repo state closeout without verified implementation evidence.

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

## Definition of Done

A feature is `passing` only when all of the following hold:

- Every step in the feature's `verification` array in `feature_list.json` passes.
- `./init.sh` is green on a clean tree.
- A dated evidence line (command and outcome) is appended to both the feature's `evidence[]` in `feature_list.json` and `claude-progress.md`.

Do not mark a feature `passing` from inference or a chat summary. `passing_requires_evidence` and `do_not_skip_verification` are enforced rules.

## Scope

One feature at a time. Pick the single highest-priority unfinished feature in `feature_list.json` (`single_active_feature: true`); do not start or stack a second.

Stay in scope: make no edits outside what the active feature needs. Target repos stay authoritative for their own files — do not centralize their state here.

## End of Session

Before ending, leave the tree restartable so the next session resumes from files, not memory:

- Update `claude-progress.md`: Last updated date, Current Verified State, Verification Evidence, and Recommended Next Step.
- Refresh `session-handoff.md`: current feature, verified state, boundary, and next step.
- Update the active feature's `status` and `evidence` in `feature_list.json`.
- Confirm the baseline is green, or record the blocker if it is not.
