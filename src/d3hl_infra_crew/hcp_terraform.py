from __future__ import annotations

HCP_TERRAFORM_SUPPORT_CONTEXT = """HCP Terraform support context:
- Use a `terraform { cloud { ... } }` block for HCP Terraform remote state and remote execution; do not combine it with a backend block.
- Require explicit organization, project, and workspace naming in plans. Use placeholders until the target repo records approved names.
- Keep tokens out of Terraform files. Authentication belongs in operator or workspace credentials after approval, never in repo config or generated handoffs.
- Put sensitive provider credentials in HCP Terraform workspace environment variables or variable sets. Put non-secret deployment inputs in workspace Terraform variables.
- Include a `.terraformignore` recommendation when local-only files, generated output, or secrets-adjacent artifacts should be excluded from CLI-driven uploads.
- Run HCP Terraform credential setup and remote runs from the operator environment; keep tokens in workspace or operator credentials rather than in repo config.
- Validate locally first with formatting checks and backend-disabled initialization/validation where target repos define Terraform files.
"""

TERRAFORM_PROVIDER_PREFERENCES = """Terraform provider preferences:
- For Proxmox resources, prefer the `bpg/proxmox` provider (registry source `bpg/proxmox`) over `telmate/proxmox` unless a target feature documents otherwise.
- Pin providers pessimistically in a `required_providers` block (e.g. `version = "~> 0.x"`); the target repo records the exact approved version.
- Drive the provider endpoint and credentials through Terraform variables and HCP Terraform workspace variable sets. Never hardcode endpoints, API tokens, or `op://` values in `.tf` files.
- Example shape (no credentials in repo):
    terraform {
      required_providers {
        proxmox = {
          source  = "bpg/proxmox"
          version = "~> 0.x"
        }
      }
    }
- bpg/proxmox `proxmox_virtual_environment_file`: `source_file` and `source_raw`
  are nested blocks, NOT string arguments. `source_file = "path"` is invalid and
  fails `terraform validate`. Use `source_file { path = "..." }` for a static
  file, or `source_raw { data = ..., file_name = "..." }` for generated content.
  `content_type` (e.g. `"snippets"`) is a resource-level argument on
  `proxmox_virtual_environment_file`, not a field inside the `source_raw` /
  `source_file` block — placing it inside the block fails `terraform validate`.
- Inject variables into cloud-init / user-data with Terraform's `templatefile()`;
  do not leave unrendered dollar-brace placeholders in a YAML file that is
  uploaded verbatim, because the Proxmox API never renders them. Render the
  template and upload the result, e.g.
    source_raw {
      data      = templatefile("${path.module}/files/user-data.yaml.tftpl", {
        username       = var.ci_username
        ssh_public_key = var.ci_ssh_public_key
      })
      file_name = "cloud-init-<vm>.yaml"
    }
- Before calling Terraform complete, the plan must pass `terraform fmt` and a
  backend-disabled `terraform validate` against the real provider schema, and
  must avoid resources or data sources the provider marks deprecated (prefer the
  replacement the provider names).
"""


def hcp_terraform_support_context() -> str:
    return HCP_TERRAFORM_SUPPORT_CONTEXT + "\n" + TERRAFORM_PROVIDER_PREFERENCES
