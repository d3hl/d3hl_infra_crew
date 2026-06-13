# AGENTS.md - d3hl_infra_crew

## What this repo is

A CrewAI orchestrator for the d3HL homelab infrastructure repos that drafts and writes real files into a target repo. It is a CrewAI Flow wrapping one sequential Crew: it reads a target repo's harness state, classifies an infrastructure request, picks a Terraform/Ansible automation path, drafts a candidate, reviews it, and — after human review — writes the generated files into the target repo's working tree. The runtime lives here.

## Startup workflow

1. Confirm cwd with `pwd`; expected `/home/d3/Github/d3hl_infra_crew`.
2. Read `claude-progress.md`.
3. Read `feature_list.json` and pick the highest-priority unfinished feature.
4. Review `git log --oneline -5` when commits exist.
5. Run `./init.sh` before feature work.
6. Do not stack feature work on a failing baseline.

## Target-repo write mode

There is no authority/boundary gate. The crew drafts changes and **writes real files into
the target repo** via the `write_repo_file` tool.

- The live crew run writes generated files into the target repo's working tree; it can create
  or overwrite files.
- The interactive checkpoint is the `apply_changes` task's `human_input: true`: the run pauses
  for human review/approval before writes are finalized.
- The `dry_run` path is LLM-free and does not write into target repos; it only renders a handoff
  to `output/`.
- Path containment is retained: target paths resolve under `/home/d3/Github` (`resolve_repo`) and
  `RepoWriteTool` rejects paths that escape the resolved repo. This is path safety, not an
  authority gate.
- No automated secret scanning remains. Keep `op://d3HLPRV/...` as references and avoid plaintext
  secrets by discipline.

## Implementation rules

- Use CrewAI Flow plus one sequential Crew first.
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
