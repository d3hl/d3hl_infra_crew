from __future__ import annotations

HCP_TERRAFORM_SUPPORT_CONTEXT = """HCP Terraform support context:
- Use a `terraform { cloud { ... } }` block for HCP Terraform remote state and remote execution; do not combine it with a backend block.
- Require explicit organization, project, and workspace naming in plans. Use placeholders until the target repo records approved names.
- Keep tokens out of Terraform files. Authentication belongs in operator or workspace credentials after approval, never in repo config or generated handoffs.
- Put sensitive provider credentials in HCP Terraform workspace environment variables or variable sets. Put non-secret deployment inputs in workspace Terraform variables.
- Include a `.terraformignore` recommendation when local-only files, generated output, or secrets-adjacent artifacts should be excluded from CLI-driven uploads.
- Treat HCP Terraform remote runs, speculative runs, saved plans, and applies as credentialed gates outside the default plan_only boundary.
- Default validation remains local static validation only: formatting checks and backend-disabled initialization/validation where target repos define Terraform files.
"""


def hcp_terraform_support_context() -> str:
    return HCP_TERRAFORM_SUPPORT_CONTEXT
